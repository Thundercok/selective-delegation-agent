"""
tests/test_web_reader.py — Behavioral tests for RAT's unified native web reader,
including SSRF validation, per-hop redirect checks, bounded DNS, HTML extraction,
and RAT kernel read_web_page capability integration.
"""
from __future__ import annotations

import hashlib
import socket
import time
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch
from urllib.parse import urlparse

import pytest

from rat.engine.web_reader import (
    WebEmptyContentError,
    WebHTTPError,
    WebReaderError,
    WebSSRFBlockedError,
    WebTimeoutError,
    extract_url,
    fetch_web_summary,
    scrape_web_page,
    validate_public_url,
)
from rat.kernel.capabilities import build_default_registry
from rat.kernel.capabilities.views import view_web_page_snapshot
from rat.kernel.capabilities.web import create_web_capability
from rat.kernel.contracts import ArtifactStore
from rat.kernel.dispatcher import ActionDispatcher


class _FakeStreamResponse:
    def __init__(
        self,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        chunks: Optional[List[bytes]] = None,
        encoding: str = "utf-8",
    ) -> None:
        self.status_code = status_code
        self.headers = headers or {}
        self._chunks = chunks if chunks is not None else []
        self.encoding = encoding

    def iter_bytes(self, chunk_size: int = 16384):
        for chunk in self._chunks:
            yield chunk

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeHttpxClientFactory:
    """Stands in for httpx.Client. ``calls`` holds the logical URL (rebuilt from the
    Host header); ``wire`` holds what was really dialled, to check IP pinning."""

    def __init__(self, handler) -> None:
        self._handler = handler
        self.calls: List[Tuple[str, str]] = []
        self.wire: List[Dict[str, Any]] = []
        self.client_kwargs: List[Dict[str, Any]] = []

    def __call__(self, *args, **kwargs):
        factory = self
        factory.client_kwargs.append(kwargs)

        class _Client:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, exc_type, exc, tb):
                return False

            def stream(self_inner, method: str, url: str, headers=None, extensions=None):
                headers, extensions = headers or {}, extensions or {}
                logical = url
                if "Host" in headers:
                    logical = urlparse(url)._replace(netloc=headers["Host"]).geturl()
                factory.wire.append({"url": url, "host": headers.get("Host"),
                                     "sni": extensions.get("sni_hostname")})
                factory.calls.append((method, logical))
                return factory._handler(method, logical)

        return _Client()


# =============================================================================
# 1. URL & SSRF Preflight Validation
# =============================================================================


def test_validate_public_url_allows_public_http_and_https():
    with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 80))]):
        validate_public_url("https://example.com/test")
        validate_public_url("http://example.org:8080/path?q=1")


@pytest.mark.parametrize(
    "bad_url",
    [
        "",
        "ftp://example.com/file",
        "file:///etc/passwd",
        "gopher://example.com",
        "javascript:alert(1)",
        "http:///no-host",
    ],
)
def test_validate_public_url_rejects_invalid_schemes_or_empty(bad_url: str):
    with pytest.raises(WebSSRFBlockedError):
        validate_public_url(bad_url)


@pytest.mark.parametrize(
    "bad_host_url",
    [
        "http://localhost/admin",
        "http://LOCALHOST:8080/",
        "https://printer.local/status",
        "http://sub.localhost/test",
        "http://db.internal/metrics",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://169.254.169.254/latest/meta-data/",
    ],
)
def test_validate_public_url_blocks_internal_hostnames(bad_host_url: str):
    with pytest.raises(WebSSRFBlockedError):
        validate_public_url(bad_host_url)


@pytest.mark.parametrize(
    "bad_ip",
    [
        "127.0.0.1",
        "::1",
        "10.0.0.5",
        "172.16.4.2",
        "192.168.1.10",
        "169.254.169.254",
        "fe80::1",
        "224.0.0.1",
        "0.0.0.0",
        "::ffff:127.0.0.1",
        "100.64.0.1",        # carrier-grade NAT: not private, not public either
        "198.18.0.1",        # benchmarking range
        "64:ff9b::7f00:1",   # NAT64 wrapper around 127.0.0.1
        "64:ff9b::a00:5",    # NAT64 wrapper around 10.0.0.5
    ],
)
def test_validate_public_url_blocks_non_public_dns_ips(bad_ip: str):
    with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", (bad_ip, 80))]):
        with pytest.raises(WebSSRFBlockedError):
            validate_public_url("https://spoofed.example.com/")


# =============================================================================
# 2. Bounded DNS Timeout & Cancellation
# =============================================================================


def test_dns_timeout_bounded_without_mutating_global_socket():
    orig_global = socket.getdefaulttimeout()
    observed_globals: List[Optional[float]] = []

    def slow_dns(*args):
        observed_globals.append(socket.getdefaulttimeout())
        time.sleep(0.3)
        return [(2, 1, 6, "", ("93.184.216.34", 443))]

    start = time.monotonic()
    with patch("socket.getaddrinfo", side_effect=slow_dns):
        with pytest.raises(WebTimeoutError, match="Quá thời gian chờ"):
            scrape_web_page("https://example.com", timeout=0.05)
    elapsed = time.monotonic() - start

    assert elapsed < 0.25
    assert socket.getdefaulttimeout() == orig_global
    assert observed_globals and all(val == orig_global for val in observed_globals)


def test_dns_cancellation():
    def blocking_dns(*args):
        time.sleep(0.5)
        return [(2, 1, 6, "", ("93.184.216.34", 443))]

    with patch("socket.getaddrinfo", side_effect=blocking_dns):
        with pytest.raises(WebTimeoutError, match="cancelled:operation_cancelled"):
            scrape_web_page("https://example.com", timeout=5.0, should_cancel=lambda: True)


# =============================================================================
# 3. Per-Hop Redirect SSRF Enforcement
# =============================================================================


@pytest.mark.parametrize(
    "redirect_target",
    [
        "http://127.0.0.1/secret",
        "http://169.254.169.254/latest/meta-data/",
        "https://metadata.internal/token",
        "file:///etc/passwd",
    ],
)
def test_per_hop_redirect_blocks_ssrf_before_connecting(redirect_target: str):
    fake_client = _FakeHttpxClientFactory(
        lambda _method, _url: _FakeStreamResponse(
            status_code=302,
            headers={"location": redirect_target},
        )
    )

    def dns_stub(host, port, *args, **kwargs):
        if host == "public.example":
            return [(2, 1, 6, "", ("93.184.216.34", port))]
        return [(2, 1, 6, "", ("127.0.0.1", port))]

    with patch("socket.getaddrinfo", side_effect=dns_stub), patch("httpx.Client", fake_client):
        with pytest.raises(WebSSRFBlockedError):
            scrape_web_page("https://public.example/start")

    assert fake_client.calls == [("GET", "https://public.example/start")]


def test_per_hop_redirect_follows_safe_public_target():
    def handler(_method: str, url: str) -> _FakeStreamResponse:
        if url == "https://public.example/old":
            return _FakeStreamResponse(status_code=301, headers={"location": "/new"})
        return _FakeStreamResponse(
            status_code=200,
            headers={"content-type": "text/html; charset=utf-8"},
            chunks=[
                b"<html><head><title>New Page</title></head>"
                b"<body><p>Moved safely to the new destination article.</p></body></html>"
            ],
        )

    fake_client = _FakeHttpxClientFactory(handler)
    with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
        with patch("httpx.Client", fake_client):
            res = scrape_web_page("https://public.example/old")

    assert res.requested_url == "https://public.example/old"
    assert res.final_url == "https://public.example/new"
    assert res.title == "New Page"
    assert "Moved safely" in res.content
    assert fake_client.calls == [
        ("GET", "https://public.example/old"),
        ("GET", "https://public.example/new"),
    ]


def test_excessive_redirects_raises_http_error():
    fake_client = _FakeHttpxClientFactory(
        lambda _method, url: _FakeStreamResponse(
            status_code=302,
            headers={"location": "https://public.example/loop"},
        )
    )
    with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
        with patch("httpx.Client", fake_client):
            with pytest.raises(WebHTTPError, match="chuyển hướng"):
                scrape_web_page("https://public.example/loop", max_redirects=2)


# =============================================================================
# 4. HTML Extraction, Truncation, Error Handling & Byte Cap
# =============================================================================


def test_scrape_web_page_extracts_metadata_links_and_truncates():
    long_para = "A" * 800
    sample_html = f"""
    <html>
      <head>
        <title>Docs &amp; Guide</title>
        <meta name="description" content="Official Python documentation guide for local workflows.">
      </head>
      <body>
        <script>console.log("ignore me");</script>
        <p>{long_para}</p>
        <a href="/tutorial">Tutorial</a>
        <a href="https://example.org/ref">External</a>
        <a href="javascript:void(0)">Ignore JS</a>
      </body>
    </html>
    """.encode("utf-8")

    fake_client = _FakeHttpxClientFactory(
        lambda _m, _u: _FakeStreamResponse(status_code=200, chunks=[sample_html])
    )
    with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("151.101.0.223", 443))]):
        with patch("httpx.Client", fake_client):
            res = scrape_web_page("https://docs.python.org/3/", max_chars=200)

    assert res.title == "Docs & Guide"
    assert res.truncated is True
    assert len(res.content) == 200
    assert res.content_hash == hashlib.sha256(res.content.encode("utf-8")).hexdigest()
    assert res.links == ["https://docs.python.org/tutorial", "https://example.org/ref"]
    assert res.engine == "rat.web_reader"


def test_scrape_web_page_http_error_and_empty_content_and_byte_cap():
    with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
        err_client = _FakeHttpxClientFactory(lambda _m, _u: _FakeStreamResponse(status_code=404))
        with patch("httpx.Client", err_client):
            with pytest.raises(WebHTTPError, match="HTTP 404"):
                scrape_web_page("https://public.example/missing")

        empty_client = _FakeHttpxClientFactory(
            lambda _m, _u: _FakeStreamResponse(
                status_code=200,
                chunks=[b"<html><head><style>body{}</style></head><body><script>var a=1;</script></body></html>"],
            )
        )
        with patch("httpx.Client", empty_client):
            with pytest.raises(WebEmptyContentError):
                scrape_web_page("https://public.example/empty")

        huge_client = _FakeHttpxClientFactory(
            lambda _m, _u: _FakeStreamResponse(
                status_code=200,
                chunks=[b"x" * 2048, b"y" * 2048],
            )
        )
        with patch("httpx.Client", huge_client):
            with pytest.raises(WebReaderError, match="vượt quá giới hạn an toàn"):
                scrape_web_page("https://public.example/huge", max_bytes=3000)


# =============================================================================
# 5. Desk Quick Summary & RAT Kernel Integration
# =============================================================================


def test_fetch_web_summary_success_and_error():
    assert extract_url("đọc https://example.org/post?a=1 nhé") == "https://example.org/post?a=1"
    bad = fetch_web_summary("ftp://example.org/file")
    assert bad["status"] == "error"
    assert bad["error_message"] == "invalid_url"

    html_bytes = (
        b"<html><head><title>Native RAT</title>"
        b'<meta name="description" content="Pure Python SSRF-safe reader integrated into RAT.">'
        b"</head><body><p>First long informative paragraph from page content for verification.</p></body></html>"
    )
    fake_client = _FakeHttpxClientFactory(lambda _m, _u: _FakeStreamResponse(200, chunks=[html_bytes]))
    with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
        with patch("httpx.Client", fake_client):
            ok = fetch_web_summary("https://example.org/rat")

    assert ok["status"] == "success"
    assert ok["visual_type"] == "web"
    assert ok["title"] == "Native RAT"
    assert ok["domain"] == "example.org"
    assert ok["bullets"]


def test_default_registry_enables_web_by_default_and_respects_disable():
    default_reg = build_default_registry()
    assert default_reg.get_capability("web") is not None
    assert default_reg.has_operation("read_web_page") is True

    no_web_reg = build_default_registry(enable_web=False)
    assert no_web_reg.get_capability("web") is None
    assert no_web_reg.has_operation("read_web_page") is False


def test_dispatch_read_web_page_success_and_ssrf_and_disabled():
    disabled_cap = create_web_capability(enabled=False)
    reg_disabled = build_default_registry(enable_web=False)
    reg_disabled.register_capability(disabled_cap)
    disp_disabled = ActionDispatcher(reg_disabled, ArtifactStore())
    res_disabled = disp_disabled.execute_operation("read_web_page", {"url": "https://example.com"})
    assert res_disabled.status == "error"
    assert res_disabled.artifact is None

    html_bytes = (
        b"<html><head><title>Python Docs</title></head>"
        b'<body><p>Welcome to Python documentation on clean web fetching.</p>'
        b'<a href="/3/tutorial/">Tutorial</a></body></html>'
    )
    fake_client = _FakeHttpxClientFactory(lambda _m, _u: _FakeStreamResponse(200, chunks=[html_bytes]))

    reg = build_default_registry(enable_web=True)
    store = ArtifactStore()
    dispatcher = ActionDispatcher(reg, store)

    with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("151.101.0.223", 443))]):
        with patch("httpx.Client", fake_client):
            res = dispatcher.execute_operation("read_web_page", {"url": "https://docs.python.org/3/"})

    assert res.status == "success"
    assert res.artifact is not None
    art = res.artifact
    assert art.kind == "web_page_snapshot"
    assert art.payload["engine"] == "rat.web_reader"
    assert art.payload["status_code"] == 200
    assert "Welcome to Python documentation" in art.payload["content"]
    assert art.payload["content_hash"] == hashlib.sha256(art.payload["content"].encode("utf-8")).hexdigest()

    spec = view_web_page_snapshot(art, {})
    assert spec.schema_version == 1
    assert len(spec.blocks) == 3

    blocked = dispatcher.execute_operation("read_web_page", {"url": "http://127.0.0.1:8080/secret"})
    assert blocked.status == "error"
    assert blocked.artifact is None


# =============================================================================
# 7. DNS rebinding: the connection must go to the address that was checked
# =============================================================================


def _page(chunks=(b"<html><title>Public</title><p>A public page with enough readable text.</p></html>",)):
    return _FakeStreamResponse(status_code=200, headers={"content-type": "text/html"}, chunks=list(chunks))


def test_connection_is_pinned_to_the_checked_ip_when_dns_rebinds():
    """First lookup says public, any later lookup says loopback. Only one lookup may happen,
    and the request must be dialled at that first answer."""
    answers = []

    def rebinding_dns(host, port, *args, **kwargs):
        answers.append(host)
        ip = "93.184.216.34" if len(answers) == 1 else "127.0.0.1"
        return [(2, 1, 6, "", (ip, port))]

    fake_client = _FakeHttpxClientFactory(lambda _m, _u: _page())
    with patch("socket.getaddrinfo", side_effect=rebinding_dns), patch("httpx.Client", fake_client):
        res = scrape_web_page("https://rebind.example/a")

    assert res.title == "Public"
    assert answers == ["rebind.example"]
    assert fake_client.wire == [{"url": "https://93.184.216.34/a", "host": "rebind.example",
                                 "sni": "rebind.example"}]
    assert fake_client.client_kwargs[0]["trust_env"] is False


def test_each_redirect_hop_is_pinned_to_its_own_checked_ip():
    def dns(host, port, *args, **kwargs):
        return [(2, 1, 6, "", ({"a.example": "93.184.216.34", "b.example": "2606:4700::6810:84e5"}[host], port))]

    def handler(_m, url):
        if url == "https://a.example/start":
            return _FakeStreamResponse(status_code=302, headers={"location": "https://b.example:8443/next?q=1"})
        return _page()

    fake_client = _FakeHttpxClientFactory(handler)
    with patch("socket.getaddrinfo", side_effect=dns), patch("httpx.Client", fake_client):
        res = scrape_web_page("https://a.example/start")

    assert res.final_url == "https://b.example:8443/next?q=1"
    assert fake_client.wire == [
        {"url": "https://93.184.216.34/start", "host": "a.example", "sni": "a.example"},
        {"url": "https://[2606:4700::6810:84e5]:8443/next?q=1", "host": "b.example:8443", "sni": "b.example"},
    ]


def test_userinfo_is_not_sent_in_the_host_header():
    fake_client = _FakeHttpxClientFactory(lambda _m, _u: _page())
    with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 80))]), \
            patch("httpx.Client", fake_client):
        scrape_web_page("http://user:pw@public.example/x")
    assert fake_client.wire[0]["host"] == "public.example"
    assert "user" not in fake_client.wire[0]["url"]
