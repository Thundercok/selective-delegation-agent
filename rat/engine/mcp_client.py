"""
rat.engine.mcp_client — Minimal zero-dependency MCP stdio JSON-RPC 2.0 client.

Allows RAT and external ToolPacks to discover and invoke tools exposed by any
local MCP stdio server (e.g., `archetype-mcp`, custom research servers) without
coupling domain logic into RAT's core codebase.
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence


@dataclass(frozen=True)
class MCPServerConfig:
    """Command specification for spawning a local MCP stdio server."""

    name: str
    command: Sequence[str]
    env: Optional[Dict[str, str]] = None
    timeout: float = 15.0


class MCPStdioClient:
    """Stateless one-shot JSON-RPC 2.0 MCP stdio client."""

    PROTOCOL_VERSION = "2025-03-26"

    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config

    def _run_exchange(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        env = dict(os.environ)
        if self.config.env:
            env.update(self.config.env)

        proc = subprocess.run(
            list(self.config.command),
            input="\n".join(json.dumps(r, ensure_ascii=False) for r in requests) + "\n",
            text=True,
            capture_output=True,
            timeout=self.config.timeout,
            env=env,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"MCP server '{self.config.name}' exited with code {proc.returncode}: "
                f"{proc.stderr.strip()}"
            )
        return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]

    def list_tools(self) -> List[Dict[str, Any]]:
        """Negotiate MCP handshake and return the server's declared tool specifications."""
        responses = self._run_exchange(
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": self.PROTOCOL_VERSION},
                },
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            ]
        )
        list_resp = next((r for r in responses if r.get("id") == 2), None)
        if list_resp is None or "error" in list_resp:
            err = (list_resp or {}).get("error", {}).get("message", "Missing tools/list response")
            raise RuntimeError(f"MCP tools/list failed on '{self.config.name}': {err}")
        return list((list_resp.get("result") or {}).get("tools") or [])

    def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Invoke a named MCP tool and return its structured JSON payload."""
        responses = self._run_exchange(
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": self.PROTOCOL_VERSION},
                },
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments or {}},
                },
            ]
        )
        call_resp = next((r for r in responses if r.get("id") == 2), None)
        if call_resp is None:
            raise RuntimeError(f"MCP protocol error on '{self.config.name}': missing response.")
        if "error" in call_resp:
            raise RuntimeError(
                f"MCP error on '{self.config.name}': {call_resp['error'].get('message')}"
            )

        result = call_resp.get("result") or {}
        payload = result.get("structuredContent")
        if payload is None:
            text_items = [
                c.get("text", "")
                for c in result.get("content", [])
                if isinstance(c, dict) and c.get("type") == "text"
            ]
            payload = json.loads(text_items[0]) if text_items else {}
        if result.get("isError"):
            err_msg = payload.get("error") if isinstance(payload, dict) else str(payload)
            raise ValueError(err_msg or f"MCP tool '{tool_name}' returned an error.")
        return payload if isinstance(payload, dict) else {"result": payload}
