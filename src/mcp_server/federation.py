"""Server-side calls to fleet MCP servers with an explicit expected result shape."""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Literal

from src.mcp_client import McpClient
from src.mcp_server.config import Settings

logger = logging.getLogger(__name__)

MUFREDAT = "maarif-mufredat"
EGITIM_KAYNAK = "egitim-kaynak"
ANAMNESIS = "anamnesis"

# Spec §7 time budget: 25 s per call, 60 s per tool. A tool fixes its deadline (monotonic seconds) once
# at entry and passes it to every call; a call the remaining budget cannot cover is not made.
CALL_TIMEOUT_SECONDS = 25.0
TOOL_BUDGET_SECONDS = 60.0
MIN_CALL_SECONDS = 1.0
ZAMAN_ASIMI = "zaman_asimi"

_DECODER = json.JSONDecoder()


class FederationError(Exception):
    def __init__(self, server: str, tool: str, reason: str) -> None:
        super().__init__(f"{server}.{tool}: {reason}")
        self.server = server
        self.tool = tool
        self.reason = reason


def decode_json_stream(text: str) -> list[Any]:
    """Decode concatenated JSON values (FastMCP emits one text block per list item)."""
    values: list[Any] = []
    idx, end = 0, len(text)
    while True:
        while idx < end and text[idx].isspace():
            idx += 1
        if idx >= end:
            return values
        value, idx = _DECODER.raw_decode(text, idx)
        values.append(value)


class Federation:
    def __init__(self, settings: Settings, client_factory: Callable[..., Any] = McpClient,
                 monotonic: Callable[[], float] = time.monotonic) -> None:
        self._settings = settings
        self._factory = client_factory
        self._monotonic = monotonic
        self._clients: dict[str, Any] = {}

    def configured(self, server: str) -> bool:
        cfg = self._settings.servers.get(server)
        return bool(cfg and cfg.api_key)

    def _client(self, server: str) -> Any:
        if server not in self._clients:
            cfg = self._settings.servers[server]
            self._clients[server] = self._factory(name=cfg.name, url=cfg.url, api_key=cfg.api_key)
        return self._clients[server]

    def call(self, server: str, tool: str, args: dict[str, Any], beklenen: Literal["liste", "nesne"],
             deadline: float | None = None) -> Any:
        if not self.configured(server):
            raise FederationError(server, tool, "not_configured")
        if deadline is None:
            result = self._client(server).call_tool(tool, args)
        else:
            remaining = deadline - self._monotonic()
            if remaining < MIN_CALL_SECONDS:
                raise FederationError(server, tool, ZAMAN_ASIMI)
            result = self._client(server).call_tool(tool, args, timeout=min(CALL_TIMEOUT_SECONDS, remaining))
        if not result.ok:
            if deadline is not None and deadline - self._monotonic() < MIN_CALL_SECONDS:
                # Cut off by the budget-capped timeout (or failed with no budget left for anything
                # else): the honest reason is the tool budget, not whatever the transport said.
                raise FederationError(server, tool, ZAMAN_ASIMI)
            raise FederationError(server, tool, f"tool_error: {result.error}")
        try:
            values = decode_json_stream(result.text)
        except ValueError as exc:
            logger.warning("undecodable %s.%s response: %s", server, tool, exc)
            raise FederationError(server, tool, "undecodable_json") from exc
        if beklenen == "liste":
            if len(values) == 1 and isinstance(values[0], list):
                return values[0]
            return values
        if len(values) == 1 and isinstance(values[0], dict):
            return values[0]
        raise FederationError(server, tool, "unexpected_shape")
