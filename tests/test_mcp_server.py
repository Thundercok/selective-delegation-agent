"""Tests for RAT's stdio MCP server over core CapabilityRegistry operations."""
from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

from rat.crawler.db import Database
from rat.kernel.capabilities import build_core_registry
from rat.kernel.registry import OperationDefinition
from rat.mcp_server import RatMCPServer


ROOT = Path(__file__).resolve().parents[1]


def test_initialize_tools_list_and_notifications(tmp_path):
    db = Database(str(tmp_path / "index.db"))
    try:
        server = RatMCPServer(registry=build_core_registry(db=db, enable_web=False))

        init = server.handle_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test"}},
        })
        assert init["result"]["protocolVersion"] == "2024-11-05"
        assert init["result"]["serverInfo"]["name"] == "rat"
        assert "tools" in init["result"]["capabilities"]

        # Notifications carry no id and must produce no response.
        assert server.handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None

        listed = server.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = listed["result"]["tools"]
        names = {t["name"] for t in tools}
        assert {"search_documents", "read_document", "calculate", "inspect_artifact"} <= names
        assert "prepare_reading_spread" not in names
        assert "get_schedule" not in names
        assert all(t["inputSchema"]["type"] == "object" for t in tools)
    finally:
        db.get_connection().close()


def test_tools_call_executes_core_tool_and_handles_needs_input_and_errors(tmp_path):
    db = Database(str(tmp_path / "index.db"))
    try:
        server = RatMCPServer(registry=build_core_registry(db=db, enable_web=False))

        calc = server.handle_message({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "calculate", "arguments": {"expression": "45 * 3 / 2"}},
        })
        assert calc["result"]["isError"] is False
        structured = calc["result"]["structuredContent"]
        assert structured["status"] == "success"
        assert structured["result"]["result"] == "67.5"
        assert structured["artifact_id"]

        # Stateful artifact lookup within the same MCP session
        inspected = server.handle_message({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "inspect_artifact", "arguments": {"artifact_id": structured["artifact_id"]}},
        })
        assert inspected["result"]["isError"] is False
        assert inspected["result"]["structuredContent"]["result"]["result"] == "67.5"

        # Missing required input surfaces structured InputRequest without failing protocol
        needs = server.handle_message({
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "translate_text", "arguments": {}},
        })
        assert needs["result"]["isError"] is False
        assert needs["result"]["structuredContent"]["status"] == "needs_input"
        assert needs["result"]["structuredContent"]["missing_fields"]

        unknown = server.handle_message({
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "nonexistent_tool", "arguments": {}},
        })
        assert unknown["result"]["isError"] is True
    finally:
        db.get_connection().close()


def test_serve_streams_isolates_stdout_and_handles_parse_and_method_errors(tmp_path):
    db = Database(str(tmp_path / "index.db"))
    try:
        registry = build_core_registry(db=db, enable_web=False)

        def noisy_handler(args, **context):
            print("NOISY_STDOUT_SHOULD_NOT_BREAK_JSONRPC")
            return {"echo": args.get("value", "")}

        registry.register_operation(OperationDefinition(
            name="noisy_echo",
            description="Test noisy print redirection",
            parameters={"type": "object", "properties": {"value": {"type": "string"}}, "required": ["value"]},
            handler=noisy_handler,
        ))
        server = RatMCPServer(registry=registry)

        stdin = io.StringIO("\n".join([
            "{not-json",
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "unknown/method"}),
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                        "params": {"name": "noisy_echo", "arguments": {"value": "ok"}}}),
        ]) + "\n")
        stdout = io.StringIO()
        assert server.serve_streams(stdin, stdout) == 0

        lines = [json.loads(line) for line in stdout.getvalue().splitlines() if line.strip()]
        assert [line["id"] for line in lines] == [None, 1, 2]
        assert lines[0]["error"]["code"] == -32700
        assert lines[1]["error"]["code"] == -32601
        assert lines[2]["result"]["structuredContent"]["result"]["echo"] == "ok"
    finally:
        db.get_connection().close()


def test_main_mcp_subprocess_end_to_end(tmp_path):
    db_path = tmp_path / "empty_index.db"
    requests = "\n".join([
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": "2025-03-26", "capabilities": {}}}),
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
        json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                    "params": {"name": "calculate", "arguments": {"expression": "18 * 7"}}}),
    ]) + "\n"

    proc = subprocess.run(
        [sys.executable, "main.py", "mcp", "--db", str(db_path), "--no-web"],
        cwd=ROOT,
        input=requests,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    responses = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    assert [r["id"] for r in responses] == [1, 2, 3]
    assert responses[0]["result"]["protocolVersion"] == "2025-03-26"
    assert any(t["name"] == "search_documents" for t in responses[1]["result"]["tools"])
    assert responses[2]["result"]["structuredContent"]["result"]["result"] == "126"
