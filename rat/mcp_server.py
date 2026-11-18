"""
rat.mcp_server — Minimal MCP (Model Context Protocol) stdio server for RAT core tools.

Exposes RAT's CapabilityRegistry operations over newline-delimited JSON-RPC 2.0
on stdin/stdout so external agents (Claude Code, Cursor, Native) can invoke
local search, document reading, verification, and utilities directly.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import logging
import sys
from typing import Any, Dict, Iterable, Optional, TextIO

from rat.kernel.capabilities import build_core_registry
from rat.kernel.contracts import ArtifactStore
from rat.kernel.dispatcher import ActionDispatcher
from rat.kernel.registry import CapabilityRegistry

logger = logging.getLogger("rat.mcp")

SUPPORTED_PROTOCOL_VERSIONS = ("2025-03-26", "2024-11-05")
SERVER_INFO = {"name": "rat", "version": "0.1.0"}


def _jsonrpc_result(req_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _jsonrpc_error(req_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _normalize_schema(schema: Any) -> Dict[str, Any]:
    if isinstance(schema, dict) and schema.get("type") == "object":
        return schema
    return {"type": "object", "properties": {}}


def _serialize_dispatch(operation: str, result: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "operation": operation,
        "status": result.status,
    }
    if result.artifact is not None:
        payload["artifact_id"] = result.artifact.id
        payload["revision"] = result.artifact.revision
    if result.status == "needs_input" and result.input_request is not None:
        payload["request_id"] = result.input_request.id
        payload["prompt"] = result.input_request.prompt
        payload["missing_fields"] = list(result.input_request.missing_fields or [])
    if result.result is not None:
        payload["result"] = result.result
    if result.error:
        payload["error"] = result.error
    if getattr(result, "verification", None) is not None:
        v = result.verification
        payload["verification"] = {
            "status": getattr(v.status, "value", str(v.status)),
            "summary": getattr(v, "summary", ""),
        }
    return payload


class RatMCPServer:
    """Stateful MCP JSON-RPC handler backed by a RAT CapabilityRegistry and ActionDispatcher."""

    def __init__(
        self,
        registry: Optional[CapabilityRegistry] = None,
        store: Optional[ArtifactStore] = None,
    ) -> None:
        self.registry = registry or build_core_registry()
        self.store = store or ArtifactStore()
        self.dispatcher = ActionDispatcher(self.registry, self.store)

    def list_tools(self) -> list[Dict[str, Any]]:
        tools = []
        for td in self.registry.to_tool_definitions():
            tools.append({
                "name": td.name,
                "description": td.description,
                "inputSchema": _normalize_schema(td.parameters),
            })
        return tools

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.registry.has_operation(name):
            return {
                "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
                "isError": True,
            }
        args = arguments if isinstance(arguments, dict) else {}
        try:
            # Keep stdout strictly reserved for JSON-RPC frames even if a tool prints.
            with contextlib.redirect_stdout(sys.stderr):
                dispatch_result = self.dispatcher.execute_operation(name, args)
        except Exception as exc:
            logger.exception("MCP tool execution failed: %s", name)
            return {
                "content": [{"type": "text", "text": f"{name} failed: {exc}"}],
                "isError": True,
            }

        if dispatch_result.status in ("error", "cancelled"):
            return {
                "content": [{"type": "text", "text": dispatch_result.error or dispatch_result.status}],
                "isError": True,
            }

        payload = _serialize_dispatch(name, dispatch_result)
        return {
            "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, default=str)}],
            "structuredContent": payload,
            "isError": False,
        }

    def handle_message(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(msg, dict):
            return _jsonrpc_error(None, -32600, "Invalid Request")

        req_id = msg.get("id")
        method = msg.get("method")
        params = msg.get("params") or {}

        # JSON-RPC notifications have no id and must not receive a response.
        if "id" not in msg:
            return None

        if not isinstance(method, str):
            return _jsonrpc_error(req_id, -32600, "Invalid Request: missing method")

        if method == "initialize":
            client_version = params.get("protocolVersion") if isinstance(params, dict) else None
            version = (
                client_version
                if client_version in SUPPORTED_PROTOCOL_VERSIONS
                else SUPPORTED_PROTOCOL_VERSIONS[0]
            )
            return _jsonrpc_result(req_id, {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
            })

        if method == "ping":
            return _jsonrpc_result(req_id, {})

        if method == "tools/list":
            return _jsonrpc_result(req_id, {"tools": self.list_tools()})

        if method == "tools/call":
            if not isinstance(params, dict) or not isinstance(params.get("name"), str):
                return _jsonrpc_error(req_id, -32602, "Invalid params: 'name' string required")
            raw_args = params.get("arguments")
            if raw_args is not None and not isinstance(raw_args, dict):
                return _jsonrpc_error(req_id, -32602, "Invalid params: 'arguments' must be an object")
            return _jsonrpc_result(req_id, self.call_tool(params["name"], raw_args))

        return _jsonrpc_error(req_id, -32601, f"Method not found: {method}")

    def serve_streams(self, stdin: Iterable[str], stdout: TextIO) -> int:
        for raw_line in stdin:
            line = raw_line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError as exc:
                reply = _jsonrpc_error(None, -32700, f"Parse error: {exc.msg}")
            else:
                reply = self.handle_message(msg)
            if reply is not None:
                stdout.write(json.dumps(reply, ensure_ascii=False, default=str) + "\n")
                stdout.flush()
        return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="rat mcp", description="Run RAT as an MCP stdio server.")
    parser.add_argument("--db", default=None, help="Path to rat_index.db (default from config)")
    parser.add_argument("--no-web", action="store_true", help="Disable web reading tool")
    args = parser.parse_args(argv)

    real_stdout = sys.stdout
    db = None
    with contextlib.redirect_stdout(sys.stderr):
        from pathlib import Path
        from rat.crawler.db import Database
        from rat.config import config

        db_target = args.db or config.db_path
        if db_target:
            db = Database(db_target, read_only=Path(db_target).is_file())
        registry = build_core_registry(db=db, enable_web=not args.no_web)
        server = RatMCPServer(registry=registry)

    try:
        return server.serve_streams(sys.stdin, real_stdout)
    finally:
        if db is not None:
            conn = getattr(getattr(db, "_local", None), "conn", None)
            if conn is not None:
                conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
