"""MCP client protocol behaviour. No network: a fake session replays responses."""
import json
import pytest
from src.mcp_client import McpClient, McpToolResult


class _Resp:
    def __init__(self, body, headers=None, status=200):
        self._body = body
        self.headers = headers or {"content-type": "application/json"}
        self.status_code = status

    @property
    def text(self):
        return self._body


class _FakeSession:
    """Replays a scripted list of responses and records the requests made."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def post(self, url, headers=None, data=None, timeout=None):
        body = json.loads(data) if data else None
        self.requests.append({
            "url": url,
            "headers": dict(headers or {}),
            "body": body,
        })
        # A notification is fire-and-forget: the real transport answers with no
        # body, so consuming a scripted response here would model it wrongly —
        # and would silently shift every later response by one.
        if str((body or {}).get("method", "")).startswith("notifications/"):
            return _Resp("", headers={})
        return self.responses.pop(0)


def _init_resp(session_id="sid-1"):
    return _Resp(
        json.dumps({"jsonrpc": "2.0", "id": 1, "result": {
            "protocolVersion": "2025-06-18",
            "serverInfo": {"name": "fake", "version": "1"}}}),
        headers={"content-type": "application/json", "mcp-session-id": session_id},
    )


def _client(responses):
    return McpClient(name="fake", url="https://x/mcp", api_key="k",
                     session=_FakeSession(responses))


def test_initialize_sends_bearer_and_captures_session_id():
    c = _client([
        _init_resp(),
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 3,
                          "result": {"tools": [
                              {"name": "t", "description": "d",
                               "inputSchema": {"type": "object"}}]}})),
    ])
    tools = c.list_tools()

    assert [t["name"] for t in tools] == ["t"]
    first = c._session.requests[0]
    assert first["headers"]["Authorization"] == "Bearer k"
    assert first["body"]["method"] == "initialize"
    # Every request after initialize must carry the session id.
    assert c._session.requests[-1]["headers"]["mcp-session-id"] == "sid-1"


def test_sse_framed_response_is_parsed():
    """egitim-kaynak answers in text/event-stream; mufredat in plain JSON."""
    sse = ("event: message\n"
           'data: {"jsonrpc":"2.0","id":3,"result":{"tools":[]}}\n\n')
    c = _client([
        _init_resp(),
        _Resp(sse, headers={"content-type": "text/event-stream"}),
    ])
    assert c.list_tools() == []


def test_list_tools_is_cached_after_first_call():
    c = _client([
        _init_resp(),
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 3, "result": {"tools": [
            {"name": "t", "description": "d", "inputSchema": {}}]}})),
    ])
    c.list_tools()
    before = len(c._session.requests)
    c.list_tools()
    assert len(c._session.requests) == before, "schema must not be refetched"


def test_call_tool_extracts_text_and_image_blocks():
    c = _client([
        _init_resp(),
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 3, "result": {"content": [
            {"type": "text", "text": "birinci"},
            {"type": "text", "text": "ikinci"},
            {"type": "image", "data": "AAA", "mimeType": "image/png"},
        ]}})),
    ])
    out = c.call_tool("t", {"q": "x"})

    assert out.ok is True
    assert out.text == "birinci\nikinci"
    assert out.images == [{"data": "AAA", "mimeType": "image/png"}]


def test_dropped_session_is_reinitialised_once_then_the_call_retried():
    c = _client([
        _init_resp("sid-1"),
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 3, "error": {
            "code": -32001, "message": "session not found"}})),
        _init_resp("sid-2"),
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 4,
                          "result": {"content": [{"type": "text", "text": "ok"}]}})),
    ])
    out = c.call_tool("t", {})

    assert out.ok is True and out.text == "ok"
    assert c._session.requests[-1]["headers"]["mcp-session-id"] == "sid-2"


def test_second_session_failure_gives_up_without_raising():
    c = _client([
        _init_resp("sid-1"),
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 3, "error": {
            "code": -32001, "message": "session not found"}})),
        _init_resp("sid-2"),
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 4, "error": {
            "code": -32001, "message": "session not found"}})),
    ])
    out = c.call_tool("t", {})

    assert out.ok is False
    assert "session" in (out.error or "")
    assert c.healthy is False


def test_tool_error_surfaces_as_not_ok_never_raises():
    """A schema rejection must reach the caller as data, so the model can be
    told what it got wrong instead of the request dying."""
    c = _client([
        _init_resp(),
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 3, "result": {
            "isError": True,
            "content": [{"type": "text", "text": "validation error: q required"}]}})),
    ])
    out = c.call_tool("t", {})

    assert out.ok is False
    assert "q required" in (out.error or "")


def test_transport_exception_is_contained():
    class _Boom:
        requests = []

        def post(self, *a, **k):
            raise OSError("connection refused")

    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=_Boom())
    out = c.call_tool("t", {})

    assert out.ok is False and c.healthy is False
