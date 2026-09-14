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
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import requests

logger = logging.getLogger(__name__)

SESSION_TTL_SECONDS = 600
# Clock for the optional per-call budget of call_tool(timeout=...); a module attribute so tests can
# substitute it. The default path (no timeout) never reads it.
_monotonic = time.monotonic


class _BudgetExhausted(Exception):
    """A call_tool(timeout=...) budget ran out before the next HTTP post."""


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
        # One client per fleet server is shared by up to 16 concurrent tool threads (Ruling B):
        # this lock serializes only the cold-start/expiry _initialize race between them, never
        # the tools/call post itself.
        self._lock = threading.Lock()
        # Fix round 1 Important #2: a stateless_http fleet server (egitim-kaynak convention)
        # never returns mcp-session-id, so _session_expired() is permanently True and every call
        # needs its own private handshake anyway — once discovered, that handshake runs WITHOUT
        # the lock, per thread, in parallel, instead of serializing behind other tool threads.
        self._sessionless = False

    @property
    def healthy(self) -> bool:
        return self._healthy

    # ── transport ────────────────────────────────────────────────────────

    def _headers(self, sid: str | None) -> dict[str, str]:
        """`sid` is the explicit session id THIS request carries (fix round 1 Minor M1): the
        caller captures it once and passes it in, rather than this reading self._sid fresh —
        which could observe a value a concurrent thread changed in between the two reads."""
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        if sid:
            h["mcp-session-id"] = sid
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

    def _post(self, payload: dict[str, Any], deadline: float | None = None,
              sid: str | None = None) -> tuple[dict[str, Any], str | None]:
        """POSTs one JSON-RPC message; returns (decoded_body, session_id_from_response_headers).

        `sid` is the explicit id this request's own headers carry (fix round 1 Minor M1). This
        method never touches self._sid/self._sid_at itself any more — publishing a session id is
        entirely the caller's job, so the handshake in _initialize can defer it until
        notifications/initialized has actually been sent.
        """
        timeout = self.timeout
        if deadline is not None:
            remaining = deadline - _monotonic()
            if remaining <= 0:
                raise _BudgetExhausted()
            timeout = min(self.timeout, remaining)
        resp = self._session.post(
            self.url,
            headers=self._headers(sid),
            data=json.dumps(payload),
            timeout=timeout,
        )
        resp_sid = (resp.headers or {}).get("mcp-session-id")
        if not str(payload.get("method", "")).startswith("notifications/"):
            return self._decode(resp), resp_sid
        return {}, resp_sid

    def _acquire(self, deadline: float | None) -> None:
        """Acquire self._lock, respecting an optional call budget. EVERY lock acquisition in
        this class goes through this one helper (fix round 1 Important #1) — _next_id, the
        session-error reset in _rpc, and _ensure_session's own critical section — so a thread
        blocked behind another thread's re-initialize can no longer overrun its own budget by
        waiting unboundedly. With no deadline (the dashboard's single-threaded default path) this
        blocks exactly as an unsynchronized attribute write would have; with a deadline, failing
        to acquire before it elapses is the same budget exhaustion `_post` already raises for a
        slow HTTP round trip."""
        if deadline is None:
            self._lock.acquire()
            return
        remaining = deadline - _monotonic()
        if not self._lock.acquire(timeout=max(0.0, remaining)):
            raise _BudgetExhausted()

    def _next_id(self, deadline: float | None = None) -> int:
        """Thread-safe RPC id counter: acquires (and respects the deadline of) the shared lock
        itself. _initialize does not call this when it already holds the lock (self._lock is not
        reentrant) — it uses _next_id_locked instead; see _initialize."""
        self._acquire(deadline)
        try:
            return self._next_id_locked()
        finally:
            self._lock.release()

    def _next_id_locked(self) -> int:
        """Same counter for a caller that already holds self._lock; see _next_id."""
        self._rpc_id += 1
        return self._rpc_id

    # ── session ──────────────────────────────────────────────────────────

    def _session_expired(self) -> bool:
        return (not self._sid) or (time.time() - self._sid_at > SESSION_TTL_SECONDS)

    def _ensure_session(self, deadline: float | None) -> None:
        """Double-checked critical section for a STATEFUL (or not-yet-classified) server: only
        the cold-start/expiry _initialize race is serialized, never the tools/call post itself,
        which always runs unlocked.

        A known-sessionless server (fix round 1 Important #2 — e.g. egitim-kaynak's
        stateless_http fleet convention: the SDK never sends mcp-session-id, so _sid stays None
        and _session_expired() is permanently True) skips the lock entirely instead: every call
        needs its own private handshake regardless, so serializing it behind other tool threads
        would only add unbounded latency for no correctness benefit. If a later handshake
        surprises us with an actual session id, we stop treating the server as sessionless.
        """
        if not self._session_expired():
            return
        if self._sessionless:
            self._initialize(deadline, already_locked=False)
            if self._sid is not None:
                self._sessionless = False
            return
        self._acquire(deadline)
        try:
            if self._session_expired():
                self._initialize(deadline, already_locked=True)
                if self._sid is None:
                    self._sessionless = True
        finally:
            self._lock.release()

    def _initialize(self, deadline: float | None, already_locked: bool) -> None:
        """Runs the initialize + notifications/initialized handshake.

        already_locked=True: the caller (_ensure_session's not-yet-classified-server branch)
        already holds self._lock, so the id is fetched via _next_id_locked (self._lock is not
        reentrant). already_locked=False: a known-sessionless server's handshake (fix round 1
        Important #2) runs with no lock held at all, so the id still goes through the
        thread-safe _next_id — the shared rpc id counter needs its own protection regardless of
        whether the session part is locked.

        The new session id (if any) is captured locally and is not published to
        self._sid/self._sid_at until AFTER notifications/initialized has been sent successfully
        (fix round 1 Minor M1) — that notification carries the new id explicitly via `sid=`,
        even though it is not yet "self._sid". If it raises _BudgetExhausted, self._sid is simply
        left at None (set at the top of this method): the server never having seen the
        notification means that id must not be reused.
        """
        self._sid = None
        init_id = self._next_id_locked() if already_locked else self._next_id(deadline)
        _, new_sid = self._post({
            "jsonrpc": "2.0", "id": init_id, "method": "initialize",
            "params": {
                "protocolVersion": self.PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "tedy-assistant", "version": "1.0"},
            },
        }, deadline, sid=None)
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"}, deadline, sid=new_sid)
        if new_sid:
            self._sid = new_sid
            self._sid_at = time.time()

    @staticmethod
    def _is_session_error(rpc: dict[str, Any]) -> bool:
        err = rpc.get("error") or {}
        return "session" in str(err.get("message", "")).lower()

    def _rpc(self, method: str, params: dict[str, Any], deadline: float | None = None) -> dict[str, Any]:
        """One JSON-RPC round trip, re-initialising once if the session died.

        _ensure_session serializes only session bootstrap between tool threads sharing this
        client (Ruling B); the post below and its response decoding always run unlocked, so
        calls on an already-live session are never serialized against each other.
        """
        for attempt in (1, 2):
            self._ensure_session(deadline)
            sid_used = self._sid
            rpc, resp_sid = self._post({
                "jsonrpc": "2.0", "id": self._next_id(deadline),
                "method": method, "params": params,
            }, deadline, sid=sid_used)
            if resp_sid:
                self._sid = resp_sid
                self._sid_at = time.time()
            if not self._is_session_error(rpc):
                return rpc
            # Server forgot us. Re-initialise and replay — but only once, so a server that
            # always rejects cannot spin here. Only clear the session id THIS call actually
            # used: another thread may already have re-established (and be using) a newer one
            # by the time we get here, and wiping that out from under it would be its own race.
            # This lock acquisition takes the deadline too (fix round 1 Important #1): a thread
            # blocked here past its budget must time out, not wait unboundedly.
            self._acquire(deadline)
            try:
                if self._sid == sid_used:
                    self._sid = None
            finally:
                self._lock.release()
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
        # `or {}` only substitutes on a falsy result; a truthy non-dict
        # (str/int/list) would otherwise sail through to `.get("tools")`
        # and raise. Treat any non-dict result as equivalent to a missing one.
        result = rpc.get("result")
        result = result if isinstance(result, dict) else {}
        tools = result.get("tools")
        if not isinstance(tools, list):
            self._healthy = False
            logger.error("MCP %s tools/list returned a malformed result: %r",
                          self.name, rpc.get("result"))
            return []
        self._tools = tools
        self._healthy = True
        return tools

    def call_tool(self, name: str, arguments: dict[str, Any],
                  timeout: float | None = None) -> McpToolResult:
        """timeout, when given, is a total budget for this call: every post inside it (re-initialise,
        notifications/initialized, the call, the one replay) is capped at what is left, and a post the
        budget can no longer cover is not sent. Without it every post uses self.timeout, as before."""
        deadline = None if timeout is None else _monotonic() + timeout
        try:
            rpc = self._rpc("tools/call",
                            {"name": name, "arguments": arguments}, deadline)
        except _BudgetExhausted:
            return McpToolResult(ok=False, error="timeout")
        except Exception as exc:
            self._healthy = False
            logger.error("MCP %s call %s failed: %s", self.name, name, exc)
            return McpToolResult(ok=False, error=str(exc))

        if rpc.get("error"):
            msg = str(rpc["error"].get("message", "rpc_error"))
            return McpToolResult(ok=False, error=msg)

        # A JSON-RPC response with no error but a truthy non-dict result (a
        # gateway that returns HTTP 200 with a JSON-shaped error envelope
        # produces exactly this) must not be treated as an empty success —
        # that would let a broken server masquerade as a tool that simply
        # found nothing.
        result = rpc.get("result")
        if not isinstance(result, dict):
            self._healthy = False
            logger.error("MCP %s call %s returned a malformed result: %r",
                          self.name, name, result)
            return McpToolResult(ok=False, error=f"malformed_result: {result!r}")

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
