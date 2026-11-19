"""Tests for RAT -> Native (`withnative/native`) MCP bridge."""
from __future__ import annotations

from pathlib import Path

import pytest

from rat.native_bridge import (
    NativeMCPClient,
    default_native_binary,
    sync_items_to_native,
)


class _FakeNativeClient:
    def __init__(self) -> None:
        self.server_info = {"name": "native-ce", "version": "test"}
        self.run_key = "test-run-key"
        self.created: list[dict] = []
        self.links: list[dict] = []
        self._by_key: dict[str, dict] = {}

    def create_document(self, *, name, summary, body, reason, idempotency_key):
        if idempotency_key in self._by_key:
            return self._by_key[idempotency_key]
        rec = {
            "id": f"rec-{len(self.created) + 1}",
            "name": name,
            "summary": summary,
            "body": body,
            "reason": reason,
            "idempotency_key": idempotency_key,
        }
        self.created.append(rec)
        self._by_key[idempotency_key] = rec
        return rec

    def add_link(self, *, source_id, target_id, relationship, note=None):
        link = {
            "source_id": source_id,
            "target_id": target_id,
            "relationship": relationship,
            "note": note,
            "status": "added",
        }
        self.links.append(link)
        return link

    def search(self, query, limit=10):
        hits = [r for r in self.created if query.lower() in (r["name"] + " " + r["body"]).lower()]
        return {"hits": hits[:limit]}


def test_sync_items_creates_records_and_supersedes_link_for_stale_files():
    client = _FakeNativeClient()
    items = [
        {
            "file_path": "/docs/vrptw_v11.py",
            "file_name": "vrptw_v11.py",
            "score": 88.5,
            "explanation": "Older version",
            "snippet": "solver\x00\x01 excerpt",
            "version_info": {
                "total_versions": 2,
                "is_latest": False,
                "latest_file_name": "vrptw.py",
                "latest_file_path": "/docs/vrptw.py",
            },
        },
    ]

    summary = sync_items_to_native(client, "vrptw", items)
    assert summary["synced_count"] == 2
    assert len(summary["supersedes_links"]) == 1
    link = summary["supersedes_links"][0]
    assert link["source_name"] == "vrptw.py"
    assert link["target_name"] == "vrptw_v11.py"
    assert link["relationship"] == "supersedes"
    assert "\x00" not in client.created[0]["body"]
    assert summary["native_search_hits"] == 2


def test_sync_items_disambiguates_same_basename_supersedes_links():
    client = _FakeNativeClient()
    items = [
        {
            "file_path": "/archive_v1/vrptw.py",
            "file_name": "vrptw.py",
            "score": 90.0,
            "explanation": "Older copy",
            "snippet": "vrptw old",
            "version_info": {
                "total_versions": 2,
                "is_latest": False,
                "latest_file_name": "vrptw.py",
                "latest_file_path": "/main_repo/vrptw.py",
            },
        },
    ]

    summary = sync_items_to_native(client, "vrptw", items)
    assert len(summary["supersedes_links"]) == 1
    link = summary["supersedes_links"][0]
    assert link["source_name"] == "main_repo/vrptw.py"
    assert link["target_name"] == "archive_v1/vrptw.py"


@pytest.mark.skipif(
    not default_native_binary().is_file(),
    reason="Local withnative/native mcp-stdio binary not built",
)
def test_live_native_mcp_sync_persists_across_restarts(tmp_path):
    native_bin = default_native_binary()
    native_db = tmp_path / "native.db"
    items = [
        {
            "file_path": "/tmp/demo/vrptw.py",
            "file_name": "vrptw.py",
            "score": 98.0,
            "explanation": "Exact match + latest version",
            "snippet": "Hybrid DDQN-ALNS VRPTW solver",
            "version_info": {"total_versions": 2, "is_latest": True, "latest_file_name": "vrptw.py"},
            "verified": True,
            "page_num": 1,
        },
        {
            "file_path": "/tmp/demo/vrptw_v11.py",
            "file_name": "vrptw_v11.py",
            "score": 82.0,
            "explanation": "Older revision",
            "snippet": "Legacy VRPTW draft",
            "version_info": {
                "total_versions": 2,
                "is_latest": False,
                "latest_file_name": "vrptw.py",
                "latest_file_path": "/tmp/demo/vrptw.py",
            },
            "verified": False,
            "page_num": 1,
        },
    ]

    with NativeMCPClient(native_bin, native_db) as client:
        info = client.engine_info()
        assert info
        summary = sync_items_to_native(client, "VRPTW", items)
        assert summary["synced_count"] == 2
        assert len(summary["supersedes_links"]) == 1
        assert summary["supersedes_links"][0]["relationship"] == "supersedes"
        assert summary["native_search_hits"] >= 2
        first_ids = {r["record_id"] for r in summary["synced_records"]}

    # Restart client on the same SQLite DB: records must survive and re-sync must be idempotent.
    with NativeMCPClient(native_bin, native_db) as client2:
        found = client2.search("VRPTW", limit=10)
        found_ids = {h["id"] for h in found.get("hits", [])}
        assert first_ids <= found_ids
        resync = sync_items_to_native(client2, "VRPTW", items)
        assert {r["record_id"] for r in resync["synced_records"]} == first_ids
