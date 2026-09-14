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


def test_call_tool_rejects_a_truthy_non_dict_result():
    """A JSON-RPC response with no error but a non-dict result (e.g. a gateway
    that returns HTTP 200 with a JSON-shaped error envelope) must not be
    treated as an empty success — that would hide a broken server behind a
    tool call that looks like it simply found nothing."""
    c = _client([
        _init_resp(),
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 3,
                          "result": "unexpected string"})),
    ])
    out = c.call_tool("t", {})

    assert out.ok is False
    assert out.text == ""
    assert out.error
    assert c.healthy is False


def test_list_tools_rejects_a_truthy_non_dict_result():
    c = _client([
        _init_resp(),
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 3, "result": 7})),
    ])
    tools = c.list_tools()

    assert tools == []
    assert c.healthy is False


# -- SP2 final review F1: opt-in per-call total budget (`timeout=`) -----------------------------

from src import mcp_client  # noqa: E402


class _Clock:
    def __init__(self, now=100.0):
        self.now = now

    def __call__(self):
        return self.now


class _TimedSession(_FakeSession):
    """_FakeSession on a fake monotonic clock: every post takes `took` seconds and records the
    timeout it was given and the moment it started."""

    def __init__(self, responses, clock, took):
        super().__init__(responses)
        self.clock, self.took, self.posts = clock, took, []

    def post(self, url, headers=None, data=None, timeout=None):
        self.posts.append({"method": json.loads(data).get("method"), "timeout": timeout, "at": self.clock.now})
        resp = super().post(url, headers=headers, data=data, timeout=timeout)
        self.clock.now += self.took
        return resp


def _session_error(rpc_id):
    return _Resp(json.dumps({"jsonrpc": "2.0", "id": rpc_id, "error": {"code": -32001, "message": "session not found"}}))


def _ok(rpc_id, text="ok"):
    return _Resp(json.dumps({"jsonrpc": "2.0", "id": rpc_id, "result": {"content": [{"type": "text", "text": text}]}}))


def test_call_timeout_caps_every_post_at_the_remaining_budget(monkeypatch):
    clock = _Clock()
    monkeypatch.setattr(mcp_client, "_monotonic", clock)
    session = _TimedSession([_init_resp("sid-1"), _session_error(2), _init_resp("sid-2"), _ok(4)], clock, took=3.0)
    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=session)

    out = c.call_tool("t", {}, timeout=20.0)

    assert out.ok is True and out.text == "ok"
    assert [p["method"] for p in session.posts] == [
        "initialize", "notifications/initialized", "tools/call",
        "initialize", "notifications/initialized", "tools/call"]
    deadline = 100.0 + 20.0
    for post in session.posts:
        remaining = deadline - post["at"]
        assert 0 < post["timeout"] <= remaining and post["timeout"] <= c.timeout
        assert post["timeout"] == min(c.timeout, remaining)


def test_budget_running_out_mid_call_returns_timeout_without_posting_again(monkeypatch):
    clock = _Clock()
    monkeypatch.setattr(mcp_client, "_monotonic", clock)
    session = _TimedSession([_init_resp("sid-1"), _session_error(2), _init_resp("sid-2"),
                             _init_resp("sid-3"), _ok(6)], clock, took=5.0)
    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=session)

    out = c.call_tool("t", {}, timeout=20.0)

    assert out.ok is False and out.error == "timeout"
    # initialize@0, initialized@5, call@10 (session error), re-initialize@15; at 20 nothing is left
    # for notifications/initialized, so it is never posted.
    assert [p["method"] for p in session.posts] == [
        "initialize", "notifications/initialized", "tools/call", "initialize"]
    assert all(p["timeout"] <= 120.0 - p["at"] for p in session.posts)
    # A session the server never saw initialized is not reused: the next call starts over.
    assert c._sid is None
    assert c.call_tool("t", {}).ok is True
    assert session.posts[4]["method"] == "initialize"


def test_exhausted_budget_returns_timeout_without_posting(monkeypatch):
    monkeypatch.setattr(mcp_client, "_monotonic", _Clock())
    session = _TimedSession([_init_resp(), _ok(2)], _Clock(), took=0.0)
    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=session)

    out = c.call_tool("t", {}, timeout=0.0)

    assert out.ok is False and out.error == "timeout"
    assert session.posts == [] and session.requests == []


def test_without_timeout_every_post_uses_the_client_timeout_and_no_clock(monkeypatch):
    def no_clock():
        raise AssertionError("the default path must not consult the budget clock")

    monkeypatch.setattr(mcp_client, "_monotonic", no_clock)
    session = _TimedSession([_init_resp("sid-1"), _session_error(2), _init_resp("sid-2"), _ok(4)], _Clock(), took=1.0)
    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=session)

    assert c.call_tool("t", {}).ok is True
    assert len(session.posts) == 6
    assert {p["timeout"] for p in session.posts} == {25.0}
