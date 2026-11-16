"""
rat.engine.web_reader — Unified native web reader & summarizer for RAT.
Zero external browser/crawler binaries; pure Python with per-hop SSRF validation,
bounded cancellable DNS resolution, connections pinned to the checked IP,
response size caps, and httpx streaming.
"""
from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass, field
import hashlib
import html
import ipaddress
import re
import socket
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)

DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_MAX_CHARS = 6000
DEFAULT_MAX_BYTES = 2 * 1024 * 1024  # 2 MB response cap
DEFAULT_MAX_REDIRECTS = 5

_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "instance-data",
    "169.254.169.254",
}

_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi,en-US;q=0.9,en;q=0.8",
}


class WebReaderError(RuntimeError):
    """Base exception for RAT native web reader."""


class WebSSRFBlockedError(WebReaderError):
    """Raised when URL scheme, host, resolved IP, or redirect hop violates SSRF policy."""


class WebTimeoutError(WebReaderError):
    """Raised when DNS resolution or HTTP fetch exceeds deadline or is cancelled."""


class WebHTTPError(WebReaderError):
    """Raised on HTTP >= 400 responses or excessive redirects."""


class WebEmptyContentError(WebReaderError):
    """Raised when fetched page contains no usable text content."""


@dataclass
class WebPageResult:
    """Verified, provenance-backed extraction result for a single public web page."""

    requested_url: str
    final_url: str
    status_code: int
    title: str
    summary: str
    bullets: List[str] = field(default_factory=list)
    content: str = ""
    content_hash: str = ""
    truncated: bool = False
    links: List[str] = field(default_factory=list)
    headers: Dict[str, Any] = field(default_factory=dict)
    fetched_at: float = field(default_factory=time.time)
    engine: str = "rat.web_reader"
    engine_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requested_url": self.requested_url,
            "final_url": self.final_url,
            "status_code": self.status_code,
            "title": self.title,
            "summary": self.summary,
            "bullets": list(self.bullets),
            "content": self.content,
            "content_hash": self.content_hash,
            "truncated": self.truncated,
            "links": list(self.links),
            "headers": dict(self.headers),
            "fetched_at": self.fetched_at,
            "engine": self.engine,
            "engine_version": self.engine_version,
        }


def extract_url(text: str) -> Optional[str]:
    """Extract the first HTTP/HTTPS URL found in text."""
    match = URL_PATTERN.search(text.strip())
    if match:
        return match.group(0).rstrip(".,;!?:)")
    return None


def resolve_dns_bounded(
    hostname: str,
    port: int,
    deadline: float,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> List[Any]:
    """Resolve DNS bounded by monotonic deadline and cancellation without mutating global socket timeout."""
    if callable(should_cancel) and should_cancel():
        raise WebTimeoutError("cancelled:operation_cancelled")

    if deadline - time.monotonic() <= 0:
        raise WebTimeoutError(f"Hết thời gian chờ trước khi phân giải DNS cho '{hostname}'.")

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(
            socket.getaddrinfo,
            hostname,
            port,
            socket.AF_UNSPEC,
            socket.SOCK_STREAM,
        )
        while True:
            if callable(should_cancel) and should_cancel():
                raise WebTimeoutError("cancelled:operation_cancelled")
            rem = deadline - time.monotonic()
            if rem <= 0:
                raise WebTimeoutError(f"Quá thời gian chờ khi phân giải DNS cho '{hostname}'.")
            try:
                return future.result(timeout=min(0.005, max(0.001, rem)))
            except concurrent.futures.TimeoutError:
                continue
    except concurrent.futures.TimeoutError:
        raise WebTimeoutError(f"Quá thời gian chờ khi phân giải DNS cho '{hostname}'.")
    except socket.gaierror as exc:
        raise WebSSRFBlockedError(f"Không thể phân giải tên miền '{hostname}': {exc}")
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


_NAT64 = ipaddress.ip_network("64:ff9b::/96")


def _check_public_ip(ip_obj: ipaddress._BaseAddress, raw_ip: str) -> None:
    """Allow only globally routable addresses; IPv6 wrappers are judged by the IPv4 inside."""
    if isinstance(ip_obj, ipaddress.IPv6Address):
        if ip_obj.ipv4_mapped is not None:
            return _check_public_ip(ip_obj.ipv4_mapped, raw_ip)
        if ip_obj in _NAT64:  # 64:ff9b::7f00:1 reaches 127.0.0.1 on a NAT64 network
            return _check_public_ip(ipaddress.IPv4Address(int(ip_obj) & 0xFFFFFFFF), raw_ip)
    if str(ip_obj) == "169.254.169.254":
        raise WebSSRFBlockedError("Địa chỉ Cloud Metadata (169.254.169.254) bị chặn.")
    if ip_obj.is_loopback:
        raise WebSSRFBlockedError(f"Địa chỉ IP loopback bị chặn: {raw_ip}")
    if ip_obj.is_link_local:
        raise WebSSRFBlockedError(f"Địa chỉ IP link-local bị chặn: {raw_ip}")
    if ip_obj.is_private:
        raise WebSSRFBlockedError(f"Địa chỉ IP mạng nội bộ (private) bị chặn: {raw_ip}")
    if ip_obj.is_multicast:
        raise WebSSRFBlockedError(f"Địa chỉ IP multicast bị chặn: {raw_ip}")
    if ip_obj.is_unspecified:
        raise WebSSRFBlockedError(f"Địa chỉ IP unspecified bị chặn: {raw_ip}")
    if not ip_obj.is_global:  # CGNAT 100.64/10, benchmarking, reserved, documentation ranges...
        raise WebSSRFBlockedError(f"Địa chỉ IP không phải địa chỉ công khai: {raw_ip}")


def validate_public_url(
    url: str,
    deadline: Optional[float] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> List[str]:
    """Validate scheme, hostname, and resolved IP addresses for SSRF safety.

    Returns the checked addresses. The caller must connect to one of them rather
    than resolving the name again: a second lookup can answer differently (DNS
    rebinding), and then the check would not cover the connection.
    """
    if not url or not isinstance(url, str):
        raise WebSSRFBlockedError("URL không hợp lệ hoặc để trống.")

    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise WebSSRFBlockedError(
            f"Giao thức '{scheme}' không được hỗ trợ. Chỉ hỗ trợ URL công khai HTTP hoặc HTTPS."
        )

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise WebSSRFBlockedError("URL thiếu hostname hợp lệ.")

    if (
        hostname in _BLOCKED_HOSTNAMES
        or hostname.endswith(".local")
        or hostname.endswith(".internal")
        or hostname.endswith(".localhost")
    ):
        raise WebSSRFBlockedError(
            f"Truy cập vào hostname nội bộ/metadata '{hostname}' bị chặn bởi chính sách bảo mật SSRF."
        )

    port = parsed.port or (443 if scheme == "https" else 80)
    eff_deadline = deadline if deadline is not None else (time.monotonic() + 5.0)
    addr_info = resolve_dns_bounded(
        hostname,
        port,
        deadline=eff_deadline,
        should_cancel=should_cancel,
    )
    if not addr_info:
        raise WebSSRFBlockedError(f"Không tìm thấy địa chỉ IP cho tên miền '{hostname}'.")

    checked: List[str] = []
    for _, _, _, _, sockaddr in addr_info:
        raw_ip = str(sockaddr[0])
        clean_ip = raw_ip.split("%", 1)[0]
        try:
            ip_obj = ipaddress.ip_address(clean_ip)
        except ValueError:
            raise WebSSRFBlockedError(f"Địa chỉ IP không hợp lệ từ DNS: {raw_ip}")
        _check_public_ip(ip_obj, raw_ip)
        checked.append(str(ip_obj))
    return checked


def _pinned_request(url: str, ip: str) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    """Point the request at an already-checked IP, keeping Host and TLS SNI on the real name.

    With an IP literal in the URL nothing resolves the name again, and the
    certificate is still verified against the hostname via ``sni_hostname``.
    """
    parsed = urlparse(url)
    host = parsed.hostname or ""
    literal = f"[{ip}]" if ":" in ip else ip
    netloc = f"{literal}:{parsed.port}" if parsed.port else literal
    host_header = f"{host}:{parsed.port}" if parsed.port else host
    return parsed._replace(netloc=netloc).geturl(), {"Host": host_header}, {"sni_hostname": host}


def _single_hop_httpx(
    url: str,
    deadline: float,
    max_bytes: int,
    should_cancel: Optional[Callable[[], bool]],
    pinned_ip: Optional[str] = None,
) -> Tuple[int, Dict[str, str], Optional[str]]:
    """Perform one non-redirecting GET request with httpx. Returns (status, headers, body_or_None_on_redirect)."""
    import httpx

    rem = max(0.05, deadline - time.monotonic())
    wire_url, headers, extensions = (url, {}, {}) if pinned_ip is None else _pinned_request(url, pinned_ip)
    try:
        # trust_env=False: a proxy from HTTP(S)_PROXY would connect on our behalf and undo the pin.
        with httpx.Client(timeout=rem, follow_redirects=False, headers=_REQUEST_HEADERS,
                          trust_env=False) as client:
            with client.stream("GET", wire_url, headers=headers, extensions=extensions) as resp:
                status_code = int(resp.status_code)
                resp_headers = {str(k).lower(): str(v) for k, v in resp.headers.items()}
                if status_code in _REDIRECT_STATUSES and resp_headers.get("location"):
                    return status_code, resp_headers, None
                if status_code >= 400:
                    raise WebHTTPError(f"Trang web trả về mã lỗi HTTP {status_code} ({url}).")

                chunks: List[bytes] = []
                total = 0
                for chunk in resp.iter_bytes(chunk_size=16384):
                    if callable(should_cancel) and should_cancel():
                        raise WebTimeoutError("cancelled:operation_cancelled")
                    if time.monotonic() > deadline:
                        raise WebTimeoutError(f"Quá thời gian chờ khi tải nội dung từ '{url}'.")
                    total += len(chunk)
                    if total > max_bytes:
                        raise WebReaderError("Dung lượng trang vượt quá giới hạn an toàn.")
                    chunks.append(chunk)

                encoding = resp.encoding or "utf-8"
                return status_code, resp_headers, b"".join(chunks).decode(encoding, errors="replace")
    except (WebReaderError, WebTimeoutError, WebHTTPError):
        raise
    except httpx.TimeoutException as exc:
        raise WebTimeoutError(f"Quá thời gian chờ khi tải trang '{url}': {exc}") from exc
    except httpx.RequestError as exc:
        raise WebReaderError(f"Không thể kết nối tới '{url}': {exc}") from exc


def _fetch_html_per_hop(
    url: str,
    deadline: float,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> Tuple[str, int, str, Dict[str, str]]:
    """Fetch URL with explicit per-hop redirect SSRF validation."""
    current_url = url.strip()
    for hop in range(max_redirects + 1):
        if callable(should_cancel) and should_cancel():
            raise WebTimeoutError("cancelled:operation_cancelled")
        if time.monotonic() > deadline:
            raise WebTimeoutError(f"Hết thời gian chờ khi tải '{current_url}'.")

        checked_ips = validate_public_url(current_url, deadline=deadline, should_cancel=should_cancel)
        status_code, resp_headers, body = _single_hop_httpx(
            current_url, deadline, max_bytes, should_cancel, pinned_ip=checked_ips[0])

        if status_code in _REDIRECT_STATUSES and resp_headers.get("location"):
            if hop >= max_redirects:
                raise WebHTTPError(f"Quá nhiều lần chuyển hướng (> {max_redirects}) tại '{current_url}'.")
            current_url = urljoin(current_url, resp_headers["location"].strip())
            continue

        return current_url, status_code, body or "", resp_headers

    raise WebHTTPError(f"Quá nhiều lần chuyển hướng tại '{url}'.")


def _extract_links(raw_html: str, base_url: str, limit: int = 50) -> List[str]:
    """Extract deduplicated public HTTP(S) links from HTML anchor tags."""
    seen = set()
    links: List[str] = []
    for raw_href in re.findall(r'<a\b[^>]*\bhref=["\']([^"\']+)["\']', raw_html, re.IGNORECASE):
        resolved = urljoin(base_url, html.unescape(raw_href.strip()))
        parsed = urlparse(resolved)
        if parsed.scheme in ("http", "https") and resolved not in seen:
            seen.add(resolved)
            links.append(resolved)
            if len(links) >= limit:
                break
    return links


def _extract_readable_text(raw_html: str, final_url: str, domain: str) -> Tuple[str, str, List[str], str]:
    """Extract (title, meta_desc, lines, clean_content) from HTML or plain text."""
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, re.IGNORECASE | re.DOTALL)
    title = html.unescape(re.sub(r"\s+", " ", title_match.group(1)).strip()) if title_match else domain
    if not title:
        title = domain

    meta_desc = ""
    for attr in ('name=["\']description["\']', 'property=["\']og:description["\']'):
        m = re.search(
            rf'<meta[^>]+{attr}[^>]+content=["\']([^"\']*)["\']',
            raw_html,
            re.IGNORECASE,
        )
        if not m:
            m = re.search(
                rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+{attr}',
                raw_html,
                re.IGNORECASE,
            )
        if m:
            meta_desc = html.unescape(re.sub(r"\s+", " ", m.group(1)).strip())
            break

    cleaned = re.sub(
        r"<(script|style|noscript|svg|header|footer|nav)[^>]*>.*?</\1>",
        "\n",
        raw_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    cleaned = re.sub(r"<!--.*?-->", " ", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"</(?:p|div|li|h[1-6]|tr|section|article|blockquote)>|<br\s*/?>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)

    lines = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in cleaned.splitlines()]
    non_empty_lines = [line for line in lines if line]
    clean_content = "\n".join(non_empty_lines).strip()
    if not clean_content and meta_desc:
        clean_content = meta_desc

    if not clean_content:
        raise WebEmptyContentError(f"Trang web '{final_url}' không có nội dung văn bản usable.")

    return title, meta_desc, non_empty_lines, clean_content


def scrape_web_page(
    url: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> WebPageResult:
    """Fetch a public HTTP(S) page with per-hop SSRF validation and extract text/metadata."""
    clean_url = (url or "").strip()
    deadline = time.monotonic() + max(0.05, timeout)

    final_url, status_code, raw_html, resp_headers = _fetch_html_per_hop(
        clean_url,
        deadline=deadline,
        max_redirects=max_redirects,
        max_bytes=max_bytes,
        should_cancel=should_cancel,
    )

    parsed_final = urlparse(final_url)
    domain = parsed_final.netloc or parsed_final.path or "web"
    title, meta_desc, non_empty_lines, clean_content = _extract_readable_text(
        raw_html,
        final_url,
        domain,
    )

    meaningful_paras = [
        line for line in non_empty_lines
        if len(line) > 40 and not line.startswith("{") and not line.startswith("function")
    ]

    bullets: List[str] = []
    if meta_desc and len(meta_desc) > 20:
        bullets.append(meta_desc)

    for para in meaningful_paras:
        if len(bullets) >= 3:
            break
        if para not in bullets and not any(para in b or b in para for b in bullets):
            bullets.append(para[:240] + ("…" if len(para) > 240 else ""))

    if not bullets and non_empty_lines:
        bullets = [non_empty_lines[0][:250]]

    summary_text = (
        "\n".join(f"• {b}" for b in bullets)
        if bullets
        else (meta_desc or "Đã tải trang thành công.")
    )

    truncated = False
    if max_chars and len(clean_content) > max_chars:
        content = clean_content[:max_chars]
        truncated = True
    else:
        content = clean_content

    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    links = _extract_links(raw_html, final_url)

    return WebPageResult(
        requested_url=clean_url,
        final_url=final_url,
        status_code=status_code,
        title=title,
        summary=summary_text,
        bullets=bullets,
        content=content,
        content_hash=content_hash,
        truncated=truncated,
        links=links,
        headers=resp_headers,
    )


def fetch_web_summary(url_or_text: str, timeout: float = 6.0) -> Dict[str, Any]:
    """Fetch URL and extract title, domain, meta description, and clean bullet summary."""
    target_url = extract_url(url_or_text) or url_or_text.strip()
    if not (target_url.startswith("http://") or target_url.startswith("https://")):
        return {
            "visual_type": "web",
            "url": target_url,
            "domain": "",
            "title": "URL không hợp lệ",
            "summary": "Vui lòng nhập đường dẫn web bắt đầu bằng http:// hoặc https://",
            "bullets": [],
            "status": "error",
            "error_message": "invalid_url",
        }

    parsed = urlparse(target_url)
    domain = parsed.netloc or parsed.path

    try:
        page = scrape_web_page(target_url, timeout=timeout)
    except Exception as exc:
        return {
            "visual_type": "web",
            "url": target_url,
            "domain": domain,
            "title": f"Không thể tải trang ({domain})",
            "summary": f"Chuột không mở được liên kết này: {exc}",
            "bullets": [],
            "status": "error",
            "error_message": str(exc),
        }

    final_domain = urlparse(page.final_url).netloc or domain
    return {
        "visual_type": "web",
        "url": page.final_url,
        "domain": final_domain,
        "title": page.title,
        "summary": page.summary,
        "bullets": page.bullets,
        "status": "success",
        "error_message": "",
    }
