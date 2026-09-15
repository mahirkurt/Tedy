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


# -- SP2 residual B: the shared session-bootstrap critical section is synchronized --------------

import threading  # noqa: E402
import time  # noqa: E402


class _ObservableLock:
    """Wraps a real lock so a test can PROVE a second thread is genuinely contending for it
    (fix round 1 Minor M2), instead of inferring that from timing: a contended acquire (the
    non-blocking probe fails) sets `waiting_event` before really blocking."""

    def __init__(self, waiting_event: threading.Event) -> None:
        self._real = threading.Lock()
        self._waiting_event = waiting_event

    def acquire(self, timeout: float = -1) -> bool:
        if self._real.acquire(timeout=0):
            return True
        self._waiting_event.set()
        return self._real.acquire(timeout=timeout)

    def release(self) -> None:
        self._real.release()

    def locked(self) -> bool:
        return self._real.locked()


def test_concurrent_cold_start_initializes_exactly_once():
    """Two tool threads racing a cold client must not both run _initialize: only one
    'initialize' and one 'notifications/initialized' reach the transport, and both callers'
    tools/call posts carry the single session id that one initialize established — never a call
    going out under another thread's half-initialized session."""
    entered_init = threading.Event()
    release_init = threading.Event()
    t2_waiting = threading.Event()
    calls_lock = threading.Lock()
    calls: list[tuple[str, str | None]] = []  # (method, session-id header)

    class _GatedSession:
        def post(self, url, headers=None, data=None, timeout=None):
            body = json.loads(data)
            method = body.get("method")
            with calls_lock:
                calls.append((method, (headers or {}).get("mcp-session-id")))
            if method == "initialize":
                entered_init.set()
                release_init.wait(5)  # generous safety timeout; the test below sets this itself
                return _init_resp("sid-shared")
            if method == "notifications/initialized":
                return _Resp("", headers={})
            return _Resp(json.dumps({"jsonrpc": "2.0", "id": body.get("id"),
                                     "result": {"content": [{"type": "text", "text": f"ok-{body.get('id')}"}]}}))

    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=_GatedSession())
    # M2: prove thread 2 actually contends for the SAME lock thread 1 holds, rather than just
    # asserting a release that happened to come after — without this wrapper the fix round 1
    # reviewer found the test could pass even with the lock removed.
    c._lock = _ObservableLock(t2_waiting)
    results = {}

    def call(slot):
        results[slot] = c.call_tool("t", {})

    t1 = threading.Thread(target=call, args=(1,))
    t1.start()
    assert entered_init.wait(5), "thread 1 never reached initialize"

    # Guaranteed at this point: thread 1 is blocked *inside* the transport's "initialize" post
    # (release_init is still unset), so c._sid is still None — thread 2 necessarily observes a
    # cold session too and must contend for the same lock, exercising the race this fix closes.
    t2 = threading.Thread(target=call, args=(2,))
    t2.start()

    assert t2_waiting.wait(5), "thread 2 never contended for the session lock"

    release_init.set()
    t1.join(5)
    t2.join(5)
    assert not t1.is_alive() and not t2.is_alive()

    methods = [m for m, _ in calls]
    assert methods.count("initialize") == 1
    assert methods.count("notifications/initialized") == 1
    tool_call_sids = [sid for m, sid in calls if m == "tools/call"]
    assert tool_call_sids == ["sid-shared", "sid-shared"]
    assert results[1].ok and results[2].ok
    assert c._sid == "sid-shared"


def test_deadline_expiring_while_waiting_for_the_session_lock_times_out_without_posting(monkeypatch):
    """A call whose deadline elapses while blocked on the session lock — held elsewhere by a
    slow cold-start init — must fail the same way an exhausted budget already does for a slow
    HTTP round trip: ok=False, error='timeout', with no post of its own."""
    monkeypatch.setattr(mcp_client, "_monotonic", lambda: 0.0)
    session = _FakeSession([])
    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=session)
    holder_grabbed = threading.Event()
    holder_release = threading.Event()

    def hold_lock():
        c._lock.acquire()
        holder_grabbed.set()
        holder_release.wait(5)
        c._lock.release()

    holder = threading.Thread(target=hold_lock)
    holder.start()
    assert holder_grabbed.wait(5), "holder thread never grabbed the session lock"

    out = c.call_tool("t", {}, timeout=0.1)

    assert out.ok is False and out.error == "timeout"
    assert session.requests == []  # the deadline elapsed waiting for the lock itself; no post at all

    holder_release.set()
    holder.join(5)
    assert not holder.is_alive()


def _hold_lock_then_release_on(lock: threading.Lock, grabbed: threading.Event, release: threading.Event) -> threading.Thread:
    def run():
        lock.acquire()
        grabbed.set()
        release.wait(5)
        lock.release()

    t = threading.Thread(target=run)
    t.start()
    assert grabbed.wait(5), "holder thread never grabbed the lock"
    return t


def test_lock_timeout_at_the_next_id_step_returns_timeout_without_posting(monkeypatch):
    """fix round 1 Important #1 (updated for fix round 2 Ruling R2-1(c)): _next_id's own lock
    acquisition takes the deadline too. With an already-warm session, _ensure_session never
    touches any lock at all — only building the request id does, on self._id_lock (its own
    dedicated lock since round 2, independent of the session lock) — so a thread blocked there
    past its deadline must time out rather than wait unboundedly behind another thread holding
    that lock (e.g. mid id-build elsewhere)."""
    monkeypatch.setattr(mcp_client, "_monotonic", lambda: 0.0)
    session = _FakeSession([])
    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=session)
    c._sid, c._sid_at = "sid-warm", time.time()
    grabbed, release = threading.Event(), threading.Event()
    holder = _hold_lock_then_release_on(c._id_lock, grabbed, release)

    out = c.call_tool("t", {}, timeout=0.1)

    assert out.ok is False and out.error == "timeout"
    assert session.requests == []

    release.set()
    holder.join(5)
    assert not holder.is_alive()


def test_lock_timeout_at_the_session_error_reset_step_returns_timeout(monkeypatch):
    """fix round 1 Important #1: the session-error reset's lock acquisition takes the deadline
    too. With an already-warm session, _ensure_session skips the lock and the post itself
    succeeds in getting a (session-error) response; only the reset that follows needs the lock —
    held elsewhere the whole time — so it must time out rather than block unboundedly.

    The holder must not grab the lock before the failing post returns (that would also starve
    _next_id's own lock acquisition earlier in the same call, testing the wrong step) — a
    two-event handshake makes the ordering exact instead of timing-dependent."""
    monkeypatch.setattr(mcp_client, "_monotonic", lambda: 0.0)
    about_to_return_error = threading.Event()
    holder_ready = threading.Event()
    holder_release = threading.Event()

    class _StallingSession(_FakeSession):
        def post(self, url, headers=None, data=None, timeout=None):
            method = (json.loads(data) if data else {}).get("method")
            if method == "tools/call":
                about_to_return_error.set()
                assert holder_ready.wait(5), "holder never grabbed the lock before the error returned"
            return super().post(url, headers=headers, data=data, timeout=timeout)

    session = _StallingSession([
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 1, "error": {"code": -32001, "message": "session not found"}})),
    ])
    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=session)
    c._sid, c._sid_at = "sid-warm", time.time()

    def hold_after_signal():
        assert about_to_return_error.wait(5), "the tools/call post never happened"
        c._lock.acquire()
        holder_ready.set()
        holder_release.wait(5)
        c._lock.release()

    holder = threading.Thread(target=hold_after_signal)
    holder.start()

    out = c.call_tool("t", {}, timeout=0.1)

    assert out.ok is False and out.error == "timeout"
    assert len(session.requests) == 1  # the one failing tools/call post; no replay was ever sent

    holder_release.set()
    holder.join(5)
    assert not holder.is_alive()


def test_sessionless_server_runs_concurrent_handshakes_unlocked():
    """fix round 1 Important #2: a stateless_http fleet server (egitim-kaynak convention) never
    returns mcp-session-id, so every call needs its own private handshake — once the client has
    recognized this (the steady-state case; see the transition test below for discovery), that
    handshake must run WITHOUT the lock, so concurrent tool threads' initialize posts are in
    flight at the same time instead of serializing behind each other."""
    both_entered = threading.Event()
    release_all = threading.Event()
    entered = {"n": 0}
    entered_lock = threading.Lock()

    class _StatelessSession:
        def post(self, url, headers=None, data=None, timeout=None):
            body = json.loads(data)
            method = body.get("method")
            if method == "initialize":
                with entered_lock:
                    entered["n"] += 1
                    if entered["n"] == 2:
                        both_entered.set()
                release_all.wait(5)
                # Never returns mcp-session-id: this server is stateless_http.
                return _Resp(json.dumps({"jsonrpc": "2.0", "id": body.get("id"), "result": {
                    "protocolVersion": "2025-06-18", "serverInfo": {"name": "fake", "version": "1"}}}))
            if method == "notifications/initialized":
                return _Resp("", headers={})
            return _Resp(json.dumps({"jsonrpc": "2.0", "id": body.get("id"),
                                     "result": {"content": [{"type": "text", "text": "ok"}]}}))

    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=_StatelessSession())
    # Steady-state precondition: a prior call already discovered this server is sessionless.
    c._sessionless = True
    results = {}

    def call(slot):
        results[slot] = c.call_tool("t", {})

    t1 = threading.Thread(target=call, args=(1,))
    t2 = threading.Thread(target=call, args=(2,))
    t1.start()
    t2.start()

    assert both_entered.wait(5), "both threads' initialize posts were never simultaneously in flight"

    release_all.set()
    t1.join(5)
    t2.join(5)
    assert not t1.is_alive() and not t2.is_alive()
    assert results[1].ok and results[2].ok
    assert c._sid is None
    assert c._sessionless is True


def test_sessionless_client_returns_to_the_locked_path_if_a_session_id_appears():
    """If a server previously discovered sessionless suddenly returns a session id, the client
    must stop treating it as sessionless — and (fix round 3 Ruling R3-1, correcting round 2's
    R2-1(d): the captured id must not simply be discarded) this call's own tools/call must carry
    that id, and it is published to self._sid (self._sid was None here, so there is nothing to
    protect against overwriting)."""

    class _FlipSession(_FakeSession):
        def __init__(self):
            super().__init__([])

        def post(self, url, headers=None, data=None, timeout=None):
            body = json.loads(data)
            method = body.get("method")
            if method == "initialize":
                resp = _init_resp("sid-appeared")
            elif method == "notifications/initialized":
                resp = _Resp("", headers={})
            else:
                resp = _Resp(json.dumps({"jsonrpc": "2.0", "id": body.get("id"),
                                         "result": {"content": [{"type": "text", "text": "ok"}]}}))
            self.requests.append({"url": url, "headers": dict(headers or {}), "body": body})
            return resp

    session = _FlipSession()
    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=session)
    c._sessionless = True

    out = c.call_tool("t", {})

    assert out.ok is True
    assert c._sessionless is False
    assert c._sid == "sid-appeared"
    tool_call = next(r for r in session.requests if r["body"]["method"] == "tools/call")
    assert tool_call["headers"].get("mcp-session-id") == "sid-appeared"


def test_stale_session_error_reset_does_not_clear_a_newer_session_id():
    """A session-error reply for the OLD session id — arriving after another thread has already
    re-established a NEWER one — must not wipe that newer session out from under it (Ruling B):
    the reset only clears self._sid when it still equals the id THIS call actually used."""

    class _RaceSession(_FakeSession):
        def __init__(self, responses, client):
            super().__init__(responses)
            self._client = client
            self._raced = False

        def post(self, url, headers=None, data=None, timeout=None):
            resp = super().post(url, headers=headers, data=data, timeout=timeout)
            body = json.loads(data)
            if not self._raced and body.get("method") == "tools/call":
                # Simulate another thread concurrently finishing its own re-initialize right
                # after this call's request went out under the old (about to fail) session.
                self._raced = True
                self._client._sid = "sid-new-from-another-thread"
            return resp

    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=None)
    session = _RaceSession([
        _init_resp("sid-old"),
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 3, "error": {"code": -32001, "message": "session not found"}})),
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 4, "result": {"content": [{"type": "text", "text": "ok"}]}})),
    ], c)
    c._session = session

    out = c.call_tool("t", {})

    assert out.ok is True and out.text == "ok"
    # The stale reset never fired: the session id preserved through the whole retry is the NEWER
    # one another thread established while this call's error was in flight, not None.
    assert c._sid == "sid-new-from-another-thread"
    tool_call_requests = [r for r in session.requests if r["body"]["method"] == "tools/call"]
    assert [r["headers"].get("mcp-session-id") for r in tool_call_requests] == \
        ["sid-old", "sid-new-from-another-thread"]


# -- SP2 residual fix round 2: R2-1 — discovery-burst unlocking; sessionless misclassification --

def test_discovery_burst_unlocks_after_first_thread_learns_sessionless():
    """R2-1 test 1: a discovery burst — multiple threads racing a cold, stateless client — must
    not all serialize behind the lock. Thread 1 wins the lock and discovers sessionless (its
    initialize deliberately blocks so we can control timing); thread 2 queues behind the SAME
    lock (proven via the observable-lock pattern, not timing). Once thread 1 discovers
    sessionless and releases, thread 2 must re-check the flag (Ruling R2-1(b)), release, and
    post its OWN initialize with the lock NOT held — never running its own redundant locked
    handshake.

    Mutation guard: removing the `self._sessionless = True` write in _ensure_session's locked
    branch makes this red — thread 2 then never sees the flag and runs its own handshake WHILE
    still holding the lock, so `second_init_lock_state` observes `True` instead of `False`."""
    first_entered = threading.Event()
    release_first = threading.Event()
    t2_waiting = threading.Event()
    second_init_lock_state = []
    c_holder: dict[str, McpClient] = {}

    class _StatelessBurstSession:
        def __init__(self):
            self._first = True

        def post(self, url, headers=None, data=None, timeout=None):
            body = json.loads(data)
            method = body.get("method")
            if method == "initialize":
                if self._first:
                    self._first = False
                    first_entered.set()
                    release_first.wait(5)
                else:
                    second_init_lock_state.append(c_holder["c"]._lock.locked())
                return _Resp(json.dumps({"jsonrpc": "2.0", "id": body.get("id"), "result": {
                    "protocolVersion": "2025-06-18", "serverInfo": {"name": "fake", "version": "1"}}}))
            if method == "notifications/initialized":
                return _Resp("", headers={})
            return _Resp(json.dumps({"jsonrpc": "2.0", "id": body.get("id"),
                                     "result": {"content": [{"type": "text", "text": "ok"}]}}))

    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=_StatelessBurstSession())
    c._lock = _ObservableLock(t2_waiting)
    c_holder["c"] = c
    results = {}

    def call(slot):
        results[slot] = c.call_tool("t", {})

    t1 = threading.Thread(target=call, args=(1,))
    t1.start()
    assert first_entered.wait(5), "thread 1 never reached its initialize"

    t2 = threading.Thread(target=call, args=(2,))
    t2.start()
    assert t2_waiting.wait(5), "thread 2 never contended for the session lock"

    release_first.set()
    t1.join(5)
    t2.join(5)
    assert not t1.is_alive() and not t2.is_alive()

    assert results[1].ok and results[2].ok
    assert c._sessionless is True
    # Thread 2's own initialize posted with the session lock free — it took the fast unlocked
    # path instead of running its own redundant locked handshake.
    assert second_init_lock_state == [False]


def test_next_id_does_not_wait_behind_an_in_flight_handshake(monkeypatch):
    """R2-1 test 2 (Ruling R2-1(c)): the id counter has its own lock, independent of the session
    lock — a thread building an id must not wait behind another thread's in-flight handshake
    (simulated here directly by holding self._lock, whether that lock would otherwise be held by
    a locked or an unlocked handshake makes no difference to _next_id)."""
    monkeypatch.setattr(mcp_client, "_monotonic", lambda: 0.0)
    session = _FakeSession([])
    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=session)
    c._sid, c._sid_at = "sid-warm", time.time()  # _ensure_session will be a no-op

    grabbed = threading.Event()
    release = threading.Event()
    holder = _hold_lock_then_release_on(c._lock, grabbed, release)

    completed = threading.Event()
    got_id = {}

    def build_id():
        got_id["value"] = c._next_id(None)
        completed.set()

    worker = threading.Thread(target=build_id)
    worker.start()
    assert completed.wait(2), "_next_id waited behind the session lock instead of its own"

    release.set()
    holder.join(5)
    worker.join(5)
    assert got_id["value"] == 1


def test_error_initialize_without_session_header_leaves_sessionless_flag_unset():
    """R2-1 test 3 (Ruling R2-1(a)): only a genuine successful JSON-RPC result (has "result", no
    "error") with no session id marks the server sessionless. An error response — e.g. a proxy
    rate-limit page returned as JSON — must never flip the flag; a mutation removing the
    `init_ok` check (treating any header-less initialize as sessionless) would make this red."""

    class _RateLimitedSession:
        def post(self, url, headers=None, data=None, timeout=None):
            body = json.loads(data)
            method = body.get("method")
            if method == "initialize":
                return _Resp(json.dumps({"jsonrpc": "2.0", "id": body.get("id"),
                                         "error": {"code": -32000, "message": "rate limited"}}))
            if method == "notifications/initialized":
                return _Resp("", headers={})
            return _Resp(json.dumps({"jsonrpc": "2.0", "id": body.get("id"),
                                     "result": {"content": [{"type": "text", "text": "ok"}]}}))

    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=_RateLimitedSession())

    out = c.call_tool("t", {})

    assert out.ok is True  # the tools/call itself still went through on our fake, unrelated
    assert c._sessionless is False


def test_unlocked_handshake_never_touches_a_published_session_id():
    """R2-1 test 4 (Ruling R2-1(d)), refined by fix round 3 Ruling R3-1: the unlocked
    (sessionless) handshake must never NULL self._sid at the start, and must never OVERWRITE an
    already-published (non-None) id even with its own discovered one — a concurrent locked
    handshake elsewhere could be publishing a fresh id at the exact same moment. (It DOES
    publish its own id when self._sid is still None — see the R3-1 tests below.)"""

    class _SurpriseSession:
        def post(self, url, headers=None, data=None, timeout=None):
            body = json.loads(data)
            method = body.get("method")
            if method == "initialize":
                # Surprises the unlocked path with an actual session id.
                return _init_resp("sid-surprise")
            if method == "notifications/initialized":
                return _Resp("", headers={})
            return _Resp(json.dumps({"jsonrpc": "2.0", "id": body.get("id"),
                                     "result": {"content": [{"type": "text", "text": "ok"}]}}))

    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=_SurpriseSession())
    c._sessionless = True
    c._sid = "sid-from-a-locked-handshake"  # simulates a fresh publish by another thread

    c._run_sessionless_handshake(None)

    assert c._sid == "sid-from-a-locked-handshake"  # untouched despite a session id appearing
    assert c._sessionless is False  # the flag still flips so future calls take the locked path


# -- SP2 residual fix round 3: R3-1/R3-2 — the unlocked handshake's captured id is actually used --

class _StrictStatefulThenStatelessSession:
    """Mirrors a real stateful MCP server closely enough to catch R3-1 regressions: starts
    issuing no session id at all (stateless), then — from the point `start_issuing_sessions()`
    is called — issues one on the next `initialize` and, from then on, REJECTS any `tools/call`
    arriving without the matching header with a session error. That is exactly what a genuinely
    stateful server does once it starts tracking sessions; a client that discards the id its own
    handshake just received (fix round 2's bug) sends its very next tools/call header-less and
    gets rejected."""

    def __init__(self):
        self.posts: list[tuple[str, int | None, str | None]] = []  # (method, id, sid header)
        self._issue_from_now = False
        self._active_session: str | None = None
        self._next_session_id = 1

    def start_issuing_sessions(self) -> None:
        self._issue_from_now = True

    def post(self, url, headers=None, data=None, timeout=None):
        body = json.loads(data)
        method = body.get("method")
        sid_header = (headers or {}).get("mcp-session-id")
        self.posts.append((method, body.get("id"), sid_header))
        if method == "initialize":
            if self._issue_from_now and self._active_session is None:
                self._active_session = f"s{self._next_session_id}"
                self._next_session_id += 1
                return _Resp(json.dumps({"jsonrpc": "2.0", "id": body.get("id"), "result": {
                    "protocolVersion": "2025-06-18", "serverInfo": {"name": "fake", "version": "1"}}}),
                    headers={"content-type": "application/json", "mcp-session-id": self._active_session})
            return _Resp(json.dumps({"jsonrpc": "2.0", "id": body.get("id"), "result": {
                "protocolVersion": "2025-06-18", "serverInfo": {"name": "fake", "version": "1"}}}))
        if method == "notifications/initialized":
            return _Resp("", headers={})
        # tools/call: a strict stateful server rejects a header-less request once it has a
        # session of its own to enforce.
        if self._active_session is not None and sid_header != self._active_session:
            return _Resp(json.dumps({"jsonrpc": "2.0", "id": body.get("id"),
                                     "error": {"code": -32001, "message": "session required"}}))
        return _Resp(json.dumps({"jsonrpc": "2.0", "id": body.get("id"),
                                 "result": {"content": [{"type": "text", "text": "ok"}]}}))


def test_stateless_then_stateful_matches_8eb51e4_single_threaded():
    """R3-2(i): a STRICT fake server starts stateless (call A), then starts issuing real session
    ids and rejecting header-less tools/call (call B), then stays warm (call C). The
    single-threaded POST sequence must match 8eb51e4's own behaviour in this exact scenario
    byte-for-byte: 7 POSTs total, one session ever established, both later tools/call posts
    carry it, and the same 1..5 JSON-RPC id sequence 8eb51e4 would produce (notifications carry
    no id). Mutation: reverting _run_sessionless_handshake to discard its captured id (fix round
    2's behaviour) makes this red — the strict fake's rejection of call B's now-header-less
    tools/call forces a second, redundant handshake and a different post/id/session count."""
    session = _StrictStatefulThenStatelessSession()
    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=session)

    out_a = c.call_tool("t", {})           # call A: still stateless
    session.start_issuing_sessions()
    out_b = c.call_tool("t", {})           # call B: server starts issuing/enforcing session ids
    out_c = c.call_tool("t", {})           # call C: warm session reused

    assert out_a.ok and out_b.ok and out_c.ok
    assert session.posts == [
        ("initialize", 1, None),
        ("notifications/initialized", None, None),
        ("tools/call", 2, None),
        ("initialize", 3, None),
        ("notifications/initialized", None, "s1"),
        ("tools/call", 4, "s1"),
        ("tools/call", 5, "s1"),
    ]
    assert c._sid == "s1"


def test_published_sid_survives_a_concurrent_sessionless_call():
    """R3-2(ii), end-to-end through call_tool (not the helper directly): once a session id has
    been published, a second sessionless-path call must not wipe it out even though its own
    handshake receives a DIFFERENT id.

    Why this is sequential rather than thread-interleaved: _run_sessionless_handshake's
    (hypothetical, mutated) null-out would execute at the very start of a call's own handshake —
    before any network I/O — and the real publish + sessionless-flag-clear happen atomically
    under the lock (verified deadlock/race-free in the round 2/3 reviews). So the ONLY way a
    second call's entry can observe an ALREADY-published id from a prior one is for that prior
    call to have completed first; genuine thread overlap cannot make a single one-shot null-out
    fire after a publish it raced with, since _sessionless would already read False by the time
    such a race could resolve. This test reproduces the state a real race could leave behind
    directly (call A completes and publishes; the second call's precondition — expired-looking
    session, still sessionless — is then forced, exactly as an actual race could leave it) and
    drives the outcome through two REAL call_tool() invocations, never the private helper.

    Mutation M-D: inserting `self._sid = None` at the very start of the unlocked branch (as if
    fix round 1's unconditional null-out were still there) makes this red — call B would wipe
    "sid-A" and then publish its own "sid-B" over it."""

    class _TwoIdSession:
        def __init__(self):
            self._calls = 0

        def post(self, url, headers=None, data=None, timeout=None):
            body = json.loads(data)
            method = body.get("method")
            if method == "initialize":
                self._calls += 1
                sid = "sid-A" if self._calls == 1 else "sid-B"
                return _init_resp(sid)
            if method == "notifications/initialized":
                return _Resp("", headers={})
            return _Resp(json.dumps({"jsonrpc": "2.0", "id": body.get("id"),
                                     "result": {"content": [{"type": "text", "text": "ok"}]}}))

    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=_TwoIdSession())
    c._sessionless = True

    out_a = c.call_tool("t", {})
    assert out_a.ok
    assert c._sid == "sid-A"

    # Force exactly the precondition a real race could leave: the session looks expired again
    # (TTL lapsed) but self._sid itself is still the published value, and the client is (for
    # whatever reason) still treating the server as sessionless — so the next call_tool() takes
    # the unlocked branch again instead of the warm fast path.
    c._sid_at = time.time() - (mcp_client.SESSION_TTL_SECONDS + 1)
    c._sessionless = True

    out_b = c.call_tool("t", {})

    assert out_b.ok
    assert c._sid == "sid-A"  # B's own handshake got "sid-B" but must not have overwritten this


def test_two_sessionless_threads_against_an_id_issuing_server_all_succeed():
    """R3-2(iii): two threads both take the (already-known) sessionless path against a server
    that, this time, issues a real session id on every initialize — the concurrent extreme of
    R3-1's scenario. Each thread's OWN captured id must be used for its OWN tools/call (a strict
    server would reject a header-less one), both calls must succeed, and the client ends up
    publishing exactly one of the two captured ids (whichever thread's own conditional
    publish-check won)."""
    both_entered = threading.Event()
    release_all = threading.Event()
    entered = {"n": 0}
    entered_lock = threading.Lock()
    tools_call_headers: list[str | None] = []
    headers_lock = threading.Lock()

    class _IdIssuingStrictSession:
        def __init__(self):
            self._next_id = 1
            self.issued: list[str] = []
            self._issued_lock = threading.Lock()

        def post(self, url, headers=None, data=None, timeout=None):
            body = json.loads(data)
            method = body.get("method")
            if method == "initialize":
                with self._issued_lock:
                    sid = f"sid-{self._next_id}"
                    self._next_id += 1
                    self.issued.append(sid)
                with entered_lock:
                    entered["n"] += 1
                    if entered["n"] == 2:
                        both_entered.set()
                release_all.wait(5)
                return _init_resp(sid)
            if method == "notifications/initialized":
                return _Resp("", headers={})
            sid_header = (headers or {}).get("mcp-session-id")
            with headers_lock:
                tools_call_headers.append(sid_header)
            if not sid_header:
                return _Resp(json.dumps({"jsonrpc": "2.0", "id": body.get("id"),
                                         "error": {"code": -32001, "message": "session required"}}))
            return _Resp(json.dumps({"jsonrpc": "2.0", "id": body.get("id"),
                                     "result": {"content": [{"type": "text", "text": "ok"}]}}))

    session = _IdIssuingStrictSession()
    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=session)
    c._sessionless = True
    results = {}

    def call(slot):
        results[slot] = c.call_tool("t", {})

    t1 = threading.Thread(target=call, args=(1,))
    t2 = threading.Thread(target=call, args=(2,))
    t1.start()
    t2.start()

    assert both_entered.wait(5), "both threads' initialize posts were never simultaneously in flight"
    release_all.set()
    t1.join(5)
    t2.join(5)
    assert not t1.is_alive() and not t2.is_alive()

    assert results[1].ok and results[2].ok
    assert None not in tools_call_headers  # no tools/call ever went out header-less
    assert c._sid in session.issued


# -- SP4 Task 18b Item 5: _ensure_session's fast path reads self._sid ONCE (SP2 park 5) ----------

def test_ensure_session_fast_path_reads_sid_once(monkeypatch):
    """A concurrent reset landing between _session_expired()'s own read of _sid and a SEPARATE
    later read of self._sid used to return None from the fast path — costing an extra session
    error plus a replay. Simulated here by monkeypatching _session_expired itself to clear _sid as
    a side effect (mimicking the race) and return False — exactly the value the OLD fast path's
    `if not self._session_expired(): return self._sid` needed to take the branch and then observe
    the now-cleared self._sid."""
    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=_FakeSession([]))
    c._sid, c._sid_at = "warm-sid", time.time()

    def racy_session_expired():
        c._sid = None
        return False

    monkeypatch.setattr(c, "_session_expired", racy_session_expired)

    result = c._ensure_session(None)

    assert result == "warm-sid"


# -- SP4 Task 18b Item 4: response-header sid published under the lock with CAS (SP2 park 4) -----

def _warm_client(session_responses, sid="sid-1"):
    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=_FakeSession(session_responses))
    c._sid, c._sid_at = sid, time.time()
    return c


def test_same_session_id_echoed_never_acquires_the_session_lock(monkeypatch):
    """(i): a response echoing the same session id this call used must never take self._lock —
    only self._id_lock (via _next_id) may be acquired."""
    c = _warm_client([
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "ok"}]}}),
              headers={"content-type": "application/json", "mcp-session-id": "sid-1"}),
    ], sid="sid-1")
    calls = []
    orig_acquire = c._acquire

    def spy_acquire(deadline, lock):
        calls.append(lock)
        return orig_acquire(deadline, lock)

    monkeypatch.setattr(c, "_acquire", spy_acquire)

    out = c.call_tool("t", {})

    assert out.ok is True
    assert c._lock not in calls  # the session lock itself was never acquired
    assert c._sid == "sid-1"


def test_rotated_id_never_overwrites_a_newer_id_another_thread_already_set():
    """(ii): a rotated id arriving while another thread has already set _sid = "newer" (simulated
    inside the fake session's post, before it returns) must not resurrect the old/rotated id over
    it — the CAS only publishes when self._sid is still None or still equal to sid_used."""

    class _RotateThenRaceSession(_FakeSession):
        def __init__(self, client):
            super().__init__([])
            self._client = client

        def post(self, url, headers=None, data=None, timeout=None):
            body = json.loads(data) if data else {}
            self.requests.append({"url": url, "headers": dict(headers or {}), "body": body})
            if body.get("method") == "tools/call":
                # Another thread rotates the session out from under this call, between the post
                # being sent and this response being read.
                self._client._sid = "newer"
                return _Resp(json.dumps({"jsonrpc": "2.0", "id": body.get("id"),
                                         "result": {"content": [{"type": "text", "text": "ok"}]}}),
                             headers={"content-type": "application/json", "mcp-session-id": "sid-rotated"})
            return _Resp("", headers={})

    c = McpClient(name="fake", url="https://x/mcp", api_key="k", session=None)
    c._session = _RotateThenRaceSession(c)
    c._sid, c._sid_at = "sid-old", time.time()

    out = c.call_tool("t", {})

    assert out.ok is True
    assert c._sid == "newer"  # the rotated response id must NOT resurrect over the newer one


def test_rotated_id_is_published_when_sid_still_matches_what_this_call_used():
    """(iii): a rotated id while self._sid is still exactly sid_used (no other thread touched it)
    must be published."""
    c = _warm_client([
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "ok"}]}}),
              headers={"content-type": "application/json", "mcp-session-id": "sid-new"}),
    ], sid="sid-old")

    out = c.call_tool("t", {})

    assert out.ok is True
    assert c._sid == "sid-new"


def test_lock_budget_exhausted_during_rotation_still_returns_ok(monkeypatch):
    """(iv): _acquire raising the budget-exhausted exception while publishing a rotated id must
    not fail the call — publishing is best effort, the successful rpc is still returned."""
    c = _warm_client([
        _Resp(json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "ok"}]}}),
              headers={"content-type": "application/json", "mcp-session-id": "sid-rotated"}),
    ], sid="sid-old")
    orig_acquire = c._acquire

    def flaky_acquire(deadline, lock):
        if lock is c._lock:
            raise mcp_client._BudgetExhausted()
        return orig_acquire(deadline, lock)

    monkeypatch.setattr(c, "_acquire", flaky_acquire)

    out = c.call_tool("t", {})

    assert out.ok is True
    assert c._sid == "sid-old"  # publish skipped (best effort); old value untouched
