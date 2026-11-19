"""Tests for standalone SmartNoteCoordinator and generic MCPStdioClient."""

from __future__ import annotations

import sys

from rat.engine.mcp_client import MCPServerConfig, MCPStdioClient


def test_mcp_stdio_client_roundtrips_with_rat_mcp_server():
    """Verify RAT's generic MCPStdioClient speaks JSON-RPC 2.0 to any compliant stdio MCP server."""
    client = MCPStdioClient(
        MCPServerConfig(
            name="rat-self-test",
            command=[sys.executable, "-m", "rat.mcp_server"],
            timeout=15.0,
        )
    )
    tools = client.list_tools()
    names = {t["name"] for t in tools}
    assert "calculate" in names

    result = client.call_tool("calculate", {"expression": "2 + 40"})
    assert result["status"] == "success"
    assert str(result["result"]["result"]) == "42"


def test_smart_note_coordinator_standalone_lifecycle():
    """Verify SmartNotes work independently of any domain plugin."""
    from rat.ui.quick_pdf_controller import QuickPDFController

    ctrl = QuickPDFController(auto_init_finder=False)
    ctrl.ready()
    try:
        note_id = ctrl.synthesizeSmartNote(
            "Họp nhóm chốt kiến trúc plugin: cần hoàn thiện MCP client trước thứ Sáu.",
            "decision",
            "Kiến trúc Plugin",
        )
        assert note_id
        active = ctrl.snapshot["activeNote"]
        assert active is not None
        assert active["title"] == "Kiến trúc Plugin"

        expanded = ctrl.expandNoteSection("Tóm tắt", "Bổ sung tiêu chí kiểm thử CI.")
        assert expanded is True
    finally:
        ctrl.close()
