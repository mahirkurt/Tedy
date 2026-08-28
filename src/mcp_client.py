"""Minimal Streamable-HTTP MCP client.

The official `mcp` Python SDK is async-first and would fight Flask's sync
workers, and the protocol surface this project needs is small: initialize,
notifications/initialized, tools/list, tools/call. So this speaks it directly
over `requests` with no new dependency.

Two response encodings are supported because the two servers differ — the
curriculum server answers in plain JSON, the OER server in text/event-stream.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import requests

logger = logging.getLogger(__name__)

SESSION_TTL_SECONDS = 600


@dataclass
class McpToolResult:
    ok: bool
    text: str = ""
    images: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


class McpClient:
    PROTOCOL_VERSION = "2025-06-18"

    def __init__(self, name: str, url: str, api_key: str,
                 timeout: float = 25.0, session: Any = None) -> None:
        self.name = name
        self.url = url
        self.api_key = api_key
        self.timeout = timeout
        self._session = session if session is not None else requests.Session()
        self._sid: str | None = None
        self._sid_at: float = 0.0
        self._tools: list[dict[str, Any]] | None = None
        self._healthy = True
        self._rpc_id = 0

    @property
    def healthy(self) -> bool:
        return self._healthy

    # ── transport ────────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        if self._sid:
            h["mcp-session-id"] = self._sid
        return h

    @staticmethod
    def _decode(resp: Any) -> dict[str, Any]:
        ctype = (resp.headers or {}).get("content-type", "")
        body = resp.text
        if "text/event-stream" in ctype:
            for line in body.splitlines():
                if line.startswith("data:"):
                    payload = line[5:].strip()
                    if payload.startswith("{"):
                        return json.loads(payload)
            raise ValueError("sse_no_data_frame")
        return json.loads(body)

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        resp = self._session.post(
            self.url,
            headers=self._headers(),
            data=json.dumps(payload),
            timeout=self.timeout,
        )
        sid = (resp.headers or {}).get("mcp-session-id")
        if sid:
            self._sid = sid
            self._sid_at = time.time()
        if not str(payload.get("method", "")).startswith("notifications/"):
            return self._decode(resp)
        return {}

    def _next_id(self) -> int:
        self._rpc_id += 1
        return self._rpc_id

    # ── session ──────────────────────────────────────────────────────────

    def _session_expired(self) -> bool:
        return (not self._sid) or (time.time() - self._sid_at > SESSION_TTL_SECONDS)

    def _initialize(self) -> None:
        self._sid = None
        self._post({
            "jsonrpc": "2.0", "id": self._next_id(), "method": "initialize",
            "params": {
                "protocolVersion": self.PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "tedy-assistant", "version": "1.0"},
            },
        })
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    @staticmethod
    def _is_session_error(rpc: dict[str, Any]) -> bool:
        err = rpc.get("error") or {}
        return "session" in str(err.get("message", "")).lower()

    def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """One JSON-RPC round trip, re-initialising once if the session died."""
        for attempt in (1, 2):
            if self._session_expired():
                self._initialize()
            rpc = self._post({
                "jsonrpc": "2.0", "id": self._next_id(),
                "method": method, "params": params,
            })
            if not self._is_session_error(rpc):
                return rpc
            # Server forgot us. Re-initialise and replay — but only once, so a
            # server that always rejects cannot spin here.
            self._sid = None
            if attempt == 2:
                self._healthy = False
                return rpc
        return {}

    # ── public API ───────────────────────────────────────────────────────

    def list_tools(self) -> list[dict[str, Any]]:
        if self._tools is not None:
            return self._tools
        try:
            rpc = self._rpc("tools/list", {})
        except Exception as exc:
            self._healthy = False
            logger.error("MCP %s tools/list failed: %s", self.name, exc)
            return []
        tools = (rpc.get("result") or {}).get("tools")
        if tools is None:
            self._healthy = False
            return []
        self._tools = tools
        self._healthy = True
        return tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> McpToolResult:
        try:
            rpc = self._rpc("tools/call",
                            {"name": name, "arguments": arguments})
        except Exception as exc:
            self._healthy = False
            logger.error("MCP %s call %s failed: %s", self.name, name, exc)
            return McpToolResult(ok=False, error=str(exc))

        if rpc.get("error"):
            msg = str(rpc["error"].get("message", "rpc_error"))
            return McpToolResult(ok=False, error=msg)

        result = rpc.get("result") or {}
        texts, images = [], []
        for block in result.get("content") or []:
            if block.get("type") == "text":
                texts.append(block.get("text", ""))
            elif block.get("type") == "image":
                images.append({"data": block.get("data", ""),
                               "mimeType": block.get("mimeType", "image/png")})
        joined = "\n".join(t for t in texts if t)

        if result.get("isError"):
            # Tool-level failure (bad arguments, not found). Data, not an
            # exception: the caller feeds it back to the model to correct.
            return McpToolResult(ok=False, error=joined or "tool_error")

        self._healthy = True
        return McpToolResult(ok=True, text=joined, images=images)
