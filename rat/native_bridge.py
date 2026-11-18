"""
rat.native_bridge — Bridge syncing RAT local search results & stale-revision links
into a local Native (`withnative/native`) SQLite node via Native's MCP stdio protocol.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

PROTOCOL_VERSION = "2025-03-26"
CLIENT_INFO = {"name": "rat-native-bridge", "version": "0.1.0"}


def _clean_text(text: str, max_chars: int = 800) -> str:
    if not text:
        return ""
    # Strip control/binary bytes so Native records stay readable Markdown/text.
    cleaned = "".join(ch if (ch >= " " or ch in "\n\t") else " " for ch in text)
    cleaned = " ".join(cleaned.split())
    return cleaned[:max_chars]


def _doc_idempotency_key(file_path: str) -> str:
    digest = hashlib.sha256(file_path.encode("utf-8", errors="ignore")).hexdigest()[:24]
    return f"rat:doc:{digest}"


def _link_idempotency_key(source_id: str, target_id: str, relationship: str) -> str:
    raw = f"{source_id}:{relationship}:{target_id}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"rat:link:{digest}"


class NativeMCPClient:
    """Minimal stdio JSON-RPC 2.0 client for Native's `mcp-stdio` binary."""

    def __init__(self, native_bin: str | Path, native_db: str | Path) -> None:
        self.native_bin = str(Path(native_bin).expanduser())
        self.native_db = str(Path(native_db).expanduser())
        self._proc: Optional[subprocess.Popen[str]] = None
        self._next_id = 1
        self.server_info: Dict[str, Any] = {}
        self.run_key: Optional[str] = None

    def __enter__(self) -> "NativeMCPClient":
        Path(self.native_db).parent.mkdir(parents=True, exist_ok=True)
        self._proc = subprocess.Popen(
            [self.native_bin, self.native_db],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        init = self._request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": CLIENT_INFO,
        })
        self.server_info = init.get("serverInfo", {})
        self._notify("notifications/initialized")
        boot = self.call_tool("bootstrap", {"format": "json"})
        self.run_key = (boot.get("run") or {}).get("run_key")
        if not self.run_key:
            raise RuntimeError("Native bootstrap did not return a run_key")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._proc is None:
            return
        try:
            if self._proc.stdin:
                self._proc.stdin.close()
            self._proc.wait(timeout=10)
        except Exception:
            self._proc.kill()
        finally:
            self._proc = None

    def _notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        assert self._proc is not None and self._proc.stdin is not None
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        self._proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self._proc.stdin.flush()

    def _request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        assert self._proc is not None and self._proc.stdin is not None and self._proc.stdout is not None
        req_id = self._next_id
        self._next_id += 1
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            payload["params"] = params
        self._proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self._proc.stdin.flush()
        line = self._proc.stdout.readline()
        if not line:
            stderr = self._proc.stderr.read() if self._proc.stderr else ""
            raise RuntimeError(f"Native mcp-stdio closed unexpectedly: {stderr.strip()}")
        resp = json.loads(line)
        if "error" in resp:
            raise RuntimeError(f"Native JSON-RPC error: {resp['error']}")
        return resp["result"]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            text = (result.get("content") or [{}])[0].get("text", "unknown error")
            raise RuntimeError(f"Native tool '{name}' failed: {text}")
        if isinstance(result.get("structuredContent"), dict):
            return result["structuredContent"]
        content = result.get("content") or []
        if content and isinstance(content[0].get("text"), str):
            text = content[0]["text"]
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"text": text}
        return {}

    def engine_info(self) -> Dict[str, Any]:
        return self.call_tool("system_read", {
            "operation": "engine_info",
            "run_key": self.run_key,
            "format": "json",
            "arguments": {},
        })

    def create_document(
        self,
        *,
        name: str,
        summary: str,
        body: str,
        reason: str,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        return self.call_tool("records_write", {
            "operation": "create_record",
            "run_key": self.run_key,
            "format": "json",
            "arguments": {
                "type": "Document",
                "kind": "local_document",
                "name": name,
                "summary": summary,
                "body": body,
                "reason": reason,
                "idempotency_key": idempotency_key,
            },
        })

    def add_link(
        self,
        *,
        source_id: str,
        target_id: str,
        relationship: str,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        args: Dict[str, Any] = {
            "source_id": source_id,
            "target_id": target_id,
            "relationship": relationship,
            "idempotency_key": _link_idempotency_key(source_id, target_id, relationship),
        }
        if note:
            args["note"] = note
        return self.call_tool("records_write", {
            "operation": "manage_links.add",
            "run_key": self.run_key,
            "format": "json",
            "arguments": args,
        })

    def search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        return self.call_tool("records_read", {
            "operation": "search",
            "run_key": self.run_key,
            "format": "json",
            "arguments": {"query": query, "limit": limit},
        })


def _item_to_dict(item: Any) -> Dict[str, Any]:
    if isinstance(item, dict):
        return item
    return {
        "file_path": getattr(item, "file_path", ""),
        "file_name": getattr(item, "file_name", ""),
        "file_ext": getattr(item, "file_ext", ""),
        "modified_formatted": getattr(item, "modified_formatted", ""),
        "score": getattr(item, "score", 0.0),
        "explanation": getattr(item, "explanation", ""),
        "snippet": getattr(item, "snippet", ""),
        "version_info": getattr(item, "version_info", None),
        "verified": getattr(item, "verified", False),
        "page_num": getattr(item, "page_num", None),
    }


def _format_document_body(item: Dict[str, Any], query: str) -> str:
    lines = [
        f"Source path: `{item['file_path']}`",
        f"Query: `{query}` · RAT score: `{item.get('score', 0.0):.1f}`",
    ]
    if item.get("page_num"):
        lines.append(f"Page: `{item['page_num']}` · Grounded verified: `{bool(item.get('verified'))}`")
    if item.get("explanation"):
        lines.append(f"Match reasons: {item['explanation']}")
    vinfo = item.get("version_info") or {}
    if vinfo.get("total_versions", 0) > 1:
        if vinfo.get("is_latest"):
            lines.append(f"Revision status: latest ({vinfo['total_versions']} local versions detected)")
        else:
            lines.append(
                f"Revision status: STALE (superseded by `{vinfo.get('latest_file_name', 'newer file')}`)"
            )
    snippet = _clean_text(item.get("snippet") or "")
    if snippet:
        lines.extend(["", "### Grounded Excerpt", snippet])
    return "\n".join(lines)


def sync_items_to_native(
    client: NativeMCPClient,
    query: str,
    items: Sequence[Any],
) -> Dict[str, Any]:
    """Sync RAT search result items into Native as Document records with supersedes links."""
    synced_by_path: Dict[str, Dict[str, Any]] = {}
    synced_records: List[Dict[str, Any]] = []
    pending_supersedes: List[Dict[str, str]] = []

    for raw_item in items:
        item = _item_to_dict(raw_item)
        file_path = item["file_path"]
        if not file_path or file_path in synced_by_path:
            continue
        file_name = item["file_name"] or Path(file_path).name
        vinfo = item.get("version_info") or {}
        is_stale = bool(vinfo.get("total_versions", 0) > 1 and not vinfo.get("is_latest"))
        title = f"{file_name} (stale)" if is_stale else file_name
        summary = (
            f"Stale local file superseded by {vinfo.get('latest_file_name')} · synced by RAT for '{query}'"
            if is_stale
            else f"Local file synced by RAT for '{query}' ({item.get('modified_formatted') or 'indexed'})"
        )
        rec = client.create_document(
            name=title,
            summary=summary,
            body=_format_document_body(item, query),
            reason=f"Grounded local document synced from RAT hybrid search for query '{query}'",
            idempotency_key=_doc_idempotency_key(file_path),
        )
        rec_id = rec.get("id")
        entry = {
            "record_id": rec_id,
            "name": title,
            "file_path": file_path,
            "is_stale": is_stale,
        }
        synced_by_path[file_path] = entry
        synced_records.append(entry)

        if is_stale and rec_id:
            latest_path = vinfo.get("latest_file_path") or ""
            latest_name = vinfo.get("latest_file_name") or (Path(latest_path).name if latest_path else "")
            if latest_name:
                pending_supersedes.append({
                    "stale_id": rec_id,
                    "stale_name": file_name,
                    "latest_path": latest_path or f"latest://{latest_name}",
                    "latest_name": latest_name,
                })

    supersedes_links: List[Dict[str, Any]] = []
    for rel in pending_supersedes:
        latest_entry = synced_by_path.get(rel["latest_path"])
        if latest_entry is None:
            latest_rec = client.create_document(
                name=rel["latest_name"],
                summary=f"Latest local revision superseding {rel['stale_name']} · synced by RAT",
                body=f"Source path: `{rel['latest_path']}`\n\nIdentified by RAT revision detector as the latest version superseding `{rel['stale_name']}`.",
                reason=f"Ensure latest local revision exists in Native before linking stale file '{rel['stale_name']}'",
                idempotency_key=_doc_idempotency_key(rel["latest_path"]),
            )
            latest_entry = {
                "record_id": latest_rec.get("id"),
                "name": rel["latest_name"],
                "file_path": rel["latest_path"],
                "is_stale": False,
            }
            synced_by_path[rel["latest_path"]] = latest_entry
            synced_records.append(latest_entry)

        if latest_entry.get("record_id") and latest_entry["record_id"] != rel["stale_id"]:
            link_resp = client.add_link(
                source_id=latest_entry["record_id"],
                target_id=rel["stale_id"],
                relationship="supersedes",
                note=f"RAT revision detector flagged '{rel['stale_name']}' as older than '{rel['latest_name']}'",
            )
            supersedes_links.append({
                "source_id": latest_entry["record_id"],
                "source_name": rel["latest_name"],
                "target_id": rel["stale_id"],
                "target_name": rel["stale_name"],
                "relationship": "supersedes",
                "status": link_resp.get("status", "added"),
            })

    search_resp = client.search(query, limit=max(5, len(synced_records)))
    hits = search_resp.get("hits") or []
    return {
        "native_server": client.server_info,
        "run_key": client.run_key,
        "query": query,
        "synced_count": len(synced_records),
        "synced_records": synced_records,
        "supersedes_links": supersedes_links,
        "native_search_hits": len(hits),
    }


def default_native_binary() -> Path:
    env_bin = os.environ.get("NATIVE_MCP_BIN")
    if env_bin:
        return Path(env_bin).expanduser()
    return Path(__file__).resolve().parents[2] / "native" / "target" / "debug" / "mcp-stdio"


def default_native_db() -> Path:
    env_db = os.environ.get("NATIVE_DB_PATH")
    if env_db:
        return Path(env_db).expanduser()
    return Path.home() / "native-data" / "native.db"


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="rat native-sync",
        description="Sync RAT local hybrid-search hits & stale-revision links into a local Native SQLite node via MCP.",
    )
    parser.add_argument("query", help="Local search query to sync into Native")
    parser.add_argument("--native-bin", default=str(default_native_binary()), help="Path to Native mcp-stdio binary")
    parser.add_argument("--native-db", default=str(default_native_db()), help="Path to Native SQLite database")
    parser.add_argument("--db", default=None, help="Path to RAT rat_index.db")
    parser.add_argument("--limit", type=int, default=5, help="Max RAT search hits to sync")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Print structured JSON summary")
    args = parser.parse_args(argv)

    native_bin = Path(args.native_bin).expanduser()
    if not native_bin.is_file():
        print(f"Native mcp-stdio binary not found at: {native_bin}", file=sys.stderr)
        return 2

    from rat.config import config
    from rat.crawler.db import Database
    from rat.engine.hybrid_search import SearchEngine

    db = Database(args.db or config.db_path, read_only=Path(args.db or config.db_path).is_file())
    try:
        search_res = SearchEngine(db=db).search(args.query, limit=args.limit)
        items = search_res.get("results", [])
    finally:
        conn = getattr(getattr(db, "_local", None), "conn", None)
        if conn is not None:
            conn.close()

    with NativeMCPClient(native_bin, args.native_db) as client:
        summary = sync_items_to_native(client, args.query, items)

    if args.as_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Native node: {summary['native_server'].get('name', 'native')} (run_key={summary['run_key']})")
        print(f"Synced {summary['synced_count']} records for query '{args.query}' → {args.native_db}")
        for rec in summary["synced_records"]:
            tag = " [STALE]" if rec["is_stale"] else ""
            print(f"  - {rec['record_id'][:8]}  {rec['name']}{tag}")
        if summary["supersedes_links"]:
            print(f"Created {len(summary['supersedes_links'])} supersedes link(s):")
            for lk in summary["supersedes_links"]:
                print(f"  - {lk['source_name']} --[supersedes]--> {lk['target_name']}")
        print(f"Verified via Native records_read(search): {summary['native_search_hits']} hit(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
