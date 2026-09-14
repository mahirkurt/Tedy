"""End-to-end OAuth: consent page -> Google identity -> code -> tokens -> MCP tool with identity."""
import base64
import hashlib
import json
import re
import threading
from urllib.parse import parse_qs, urlparse

import anyio
import pytest
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.testclient import TestClient

from src.mcp_server import http_app
from src.mcp_server.config import load_settings
from src.mcp_server.google_identity import IdentityError
from src.mcp_server.oauth_store import OAuthStore

BASE = "https://mcp.tedy.online"
FULL = "drmahirkurt@gmail.com"
READER = "murzogluhulya@gmail.com"
REDIRECT = "https://claude.ai/api/mcp/auth_callback"
VERIFIER = "v" * 64
MCP_HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json"}


def _challenge(v: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b"=").decode()


def _test_mcp() -> FastMCP:
    mcp = FastMCP("test", stateless_http=True, json_response=True,
                  transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))

    @mcp.tool()
    def kimim(ctx: Context) -> dict:
        return {"email": ctx.request_context.request.state.ted_email}

    return mcp


class Clock:
    def __init__(self):
        self.now = 1_800_000_000.0

    def __call__(self):
        return self.now


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _credential(email: str) -> str:
    """JWT-shaped stand-in for a Google credential that carries the email in its middle segment."""
    return f"{_b64u(b'{}')}.{_b64u(email.encode())}.{_b64u(b'sig')}"


class Verifier:
    """Test double: the credential carries the email; asserts the nonce binds to form_state."""

    def __init__(self, park=None):
        self.expected_nonce = None
        self.error = None
        self.calls = 0
        self.park = park or (lambda name: None)

    def __call__(self, credential, nonce):
        self.calls += 1
        self.park("verify_identity")
        assert nonce == self.expected_nonce
        if self.error:
            raise IdentityError(self.error)
        try:
            middle = credential.split(".")[1]
            return base64.urlsafe_b64decode(middle + "=" * (-len(middle) % 4)).decode()
        except (IndexError, ValueError):
            return credential


class ParkingStore(OAuthStore):
    """OAuthStore whose methods can park their worker until the test releases it."""

    def __init__(self, path, clock, park):
        super().__init__(path, clock=clock)
        self.park = park

    def principal(self, bearer):
        self.park("principal")
        return super().principal(bearer)

    def issue_code(self, *args, **kwargs):
        self.park("issue_code")
        return super().issue_code(*args, **kwargs)

    def redeem_code(self, *args, **kwargs):
        self.park("redeem_code")
        return super().redeem_code(*args, **kwargs)

    def refresh(self, *args, **kwargs):
        self.park("refresh")
        return super().refresh(*args, **kwargs)


@pytest.fixture
def ctx(tmp_path):
    clock, verifier = Clock(), Verifier()
    store = OAuthStore(tmp_path / "oauth.sqlite3", clock=clock)
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE}, project_root=tmp_path)
    app = http_app.build_app(settings, store, _test_mcp(), verify_identity=verifier,
                             form_secret=b"s" * 32, clock=clock)
    with TestClient(app, base_url=BASE, follow_redirects=False) as client:
        yield client, verifier, clock, store


def _authorize_params(**over):
    params = {"response_type": "code", "client_id": http_app.CLIENT_ID, "redirect_uri": REDIRECT,
              "state": "st-123", "code_challenge": _challenge(VERIFIER), "code_challenge_method": "S256"}
    params.update(over)
    return params


def _start(client, verifier, **over):
    r = client.get("/oauth/authorize", params=_authorize_params(**over))
    assert r.status_code == 200
    form_state = re.search(r'name="form_state" value="([^"]+)"', r.text).group(1)
    verifier.expected_nonce = http_app.nonce_for(form_state)
    return form_state


def test_consent_page_embeds_google_signin_and_nonce(ctx):
    client, verifier, _, _ = ctx
    form_state = _start(client, verifier)
    page = client.get("/oauth/authorize", params=_authorize_params()).text
    assert "accounts.google.com/gsi/client" in page
    assert http_app.roles.GOOGLE_CLIENT_ID in page
    assert "claude.ai" in page
    assert form_state


@pytest.mark.parametrize("over,reason", [
    ({"redirect_uri": "https://claude.ai.evil.com/cb"}, "redirect_uri"),
    ({"code_challenge_method": "plain"}, "S256"),
    ({"code_challenge": ""}, "code_challenge"),
    ({"response_type": "token"}, "response_type"),
    ({"client_id": "someone-else"}, "client_id"),
])
def test_authorize_get_rejects_bad_requests(ctx, over, reason):
    client, _, _, _ = ctx
    r = client.get("/oauth/authorize", params=_authorize_params(**over))
    assert r.status_code == 400
    assert reason in r.text


def test_full_round_trip_to_mcp_and_refresh(ctx):
    client, verifier, _, _ = ctx
    form_state = _start(client, verifier)
    r = client.post("/oauth/authorize", data={"form_state": form_state, "credential": _credential(FULL)})
    assert r.status_code == 302
    loc = urlparse(r.headers["location"])
    assert f"{loc.scheme}://{loc.netloc}{loc.path}" == REDIRECT
    query = parse_qs(loc.query)
    assert query["state"] == ["st-123"]

    tok = client.post("/oauth/token", data={
        "grant_type": "authorization_code", "code": query["code"][0], "redirect_uri": REDIRECT,
        "client_id": http_app.CLIENT_ID, "code_verifier": VERIFIER})
    assert tok.status_code == 200
    assert tok.headers["cache-control"] == "no-store"
    body = tok.json()
    assert body["token_type"] == "Bearer" and body["expires_in"] == 3600 and body["refresh_token"]

    call = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                     "params": {"name": "kimim", "arguments": {}}},
                       headers={**MCP_HEADERS, "authorization": f"Bearer {body['access_token']}"})
    assert call.status_code == 200
    assert json.loads(call.json()["result"]["content"][0]["text"]) == {"email": FULL}

    again = client.post("/oauth/token", data={"grant_type": "refresh_token", "refresh_token": body["refresh_token"],
                                              "client_id": http_app.CLIENT_ID})
    assert again.status_code == 200
    assert again.json()["access_token"] != body["access_token"]


def test_reader_role_is_refused_without_code(ctx):
    client, verifier, _, _ = ctx
    form_state = _start(client, verifier)
    r = client.post("/oauth/authorize", data={"form_state": form_state, "credential": _credential(READER)})
    assert r.status_code == 403
    assert "location" not in r.headers


def test_identity_failure_is_401(ctx):
    client, verifier, _, _ = ctx
    form_state = _start(client, verifier)
    verifier.error = "nonce_mismatch"
    r = client.post("/oauth/authorize", data={"form_state": form_state, "credential": _credential(FULL)})
    assert r.status_code == 401


def test_tampered_and_expired_form_state(ctx):
    client, verifier, clock, _ = ctx
    form_state = _start(client, verifier)
    payload, sig = form_state.split(".")
    tampered = payload[:-2] + ("AA" if payload[-2:] != "AA" else "BB") + "." + sig
    assert client.post("/oauth/authorize", data={"form_state": tampered, "credential": _credential(FULL)}).status_code == 400
    clock.now += http_app.FORM_TTL_SECONDS + 1
    r = client.post("/oauth/authorize", data={"form_state": form_state, "credential": _credential(FULL)})
    assert r.status_code == 400
    assert "form_state_expired" in r.text


def test_token_endpoint_errors(ctx):
    client, _, _, _ = ctx
    bad = client.post("/oauth/token", data={"grant_type": "authorization_code", "code": "nope", "redirect_uri": REDIRECT,
                                            "client_id": http_app.CLIENT_ID, "code_verifier": VERIFIER})
    assert bad.status_code == 400 and bad.json()["error"] == "invalid_grant"
    evil = client.post("/oauth/token", data={"grant_type": "authorization_code", "code": "x",
                                             "redirect_uri": "https://evil.example/cb",
                                             "client_id": http_app.CLIENT_ID, "code_verifier": VERIFIER})
    assert evil.status_code == 400 and evil.json()["error"] == "invalid_grant"
    other = client.post("/oauth/token", data={"grant_type": "client_credentials"})
    assert other.status_code == 400 and other.json()["error"] == "unsupported_grant_type"


def test_state_is_escaped_on_the_consent_page(ctx):
    client, _, _, _ = ctx
    r = client.get("/oauth/authorize", params=_authorize_params(state='"><script>alert(1)</script>'))
    assert r.status_code == 200
    assert "<script>alert(1)</script>" not in r.text


def test_form_state_helpers_round_trip():
    token = http_app.sign_form_state({"a": "1"}, b"k" * 32, now=100.0)
    assert http_app.read_form_state(token, b"k" * 32, now=100.0 + 10) == {"a": "1"}
    with pytest.raises(ValueError, match="form_state_invalid"):
        http_app.read_form_state(token, b"x" * 32, now=110.0)
    with pytest.raises(ValueError, match="form_state_invalid"):
        http_app.read_form_state(token.split(".")[0] + ".ü" + "0" * 63, b"k" * 32, now=110.0)
    with pytest.raises(ValueError, match="form_state_expired"):
        http_app.read_form_state(token, b"k" * 32, now=100.0 + http_app.FORM_TTL_SECONDS + 1)


def test_build_app_requires_form_secret(tmp_path):
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE}, project_root=tmp_path)
    with pytest.raises(ValueError):
        http_app.build_app(settings, OAuthStore(tmp_path / "o.sqlite3"), _test_mcp(), form_secret=b"short")


# -- S1a / F1: malformed credentials never reach the verifier ---------------------------

@pytest.mark.parametrize("credential", [
    "not-a-jwt", "a.b.c.d", pytest.param("a" * 4093 + ".b.c", id="4097-bytes"), "a.b+c.d", "a..c", "",
])
def test_malformed_credential_is_invalid_token_without_calling_the_verifier(ctx, credential):
    client, verifier, _, _ = ctx
    form_state = _start(client, verifier)
    r = client.post("/oauth/authorize", data={"form_state": form_state, "credential": credential})
    assert r.status_code == 401
    assert r.text == "Google kimliği doğrulanamadı: invalid_token"
    assert "location" not in r.headers
    assert verifier.calls == 0


def test_missing_credential_is_invalid_token_without_calling_the_verifier(ctx):
    client, verifier, _, _ = ctx
    form_state = _start(client, verifier)
    r = client.post("/oauth/authorize", data={"form_state": form_state})
    assert r.status_code == 401
    assert r.text == "Google kimliği doğrulanamadı: invalid_token"
    assert verifier.calls == 0


# -- S1a / F1: blocking auth work runs off the event loop -------------------------------

LOOP_FREE_WITHIN_SECONDS = 2.0


@pytest.mark.parametrize("blocked", ["verify_identity", "issue_code", "redeem_code", "refresh", "principal"])
def test_blocked_auth_work_leaves_the_event_loop_free(tmp_path, blocked):
    entered, release = threading.Event(), threading.Event()

    def park(name):
        if name == blocked:
            entered.set()
            release.wait(10)

    clock = Clock()
    store = ParkingStore(tmp_path / "oauth.sqlite3", clock, park)
    verifier = Verifier(park=park)
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE}, project_root=tmp_path)
    app = http_app.build_app(settings, store, _test_mcp(), verify_identity=verifier,
                             form_secret=b"s" * 32, clock=clock)
    with TestClient(app, base_url=BASE, follow_redirects=False) as client:
        form_state = _start(client, verifier)
        consent = {"form_state": form_state, "credential": _credential(FULL)}
        calls = {
            "verify_identity": lambda: client.post("/oauth/authorize", data=consent),
            "issue_code": lambda: client.post("/oauth/authorize", data=consent),
            "redeem_code": lambda: client.post("/oauth/token", data={
                "grant_type": "authorization_code", "code": "nope", "redirect_uri": REDIRECT,
                "client_id": http_app.CLIENT_ID, "code_verifier": VERIFIER}),
            "refresh": lambda: client.post("/oauth/token", data={
                "grant_type": "refresh_token", "refresh_token": "nope", "client_id": http_app.CLIENT_ID}),
            "principal": lambda: client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
                                             headers={**MCP_HEADERS, "authorization": "Bearer nope"}),
        }
        outcome = {}

        def run(key, call):
            try:
                outcome[key] = call()
            except Exception as exc:  # surfaced by the assertions below
                outcome[key] = exc

        worker = threading.Thread(target=run, args=("blocked", calls[blocked]))
        probe = threading.Thread(target=run, args=("health", lambda: client.get("/health")))
        worker.start()
        try:
            assert entered.wait(5), f"{blocked} was never reached"
            probe.start()
            probe.join(LOOP_FREE_WITHIN_SECONDS)
            assert not probe.is_alive(), f"/health stalled while {blocked} was blocked: it runs on the event loop"
            assert outcome["health"].status_code == 200
        finally:
            release.set()
            worker.join(10)
            if probe.ident is not None:
                probe.join(10)
    assert not worker.is_alive()
    assert not isinstance(outcome.get("blocked"), Exception), outcome.get("blocked")
    assert outcome["blocked"].status_code in {302, 400, 401}


# -- S1b / T4: an unexpected cert-fetch failure is 401 google_unreachable, not 500 ------------

def test_unexpected_cert_fetch_error_is_401_google_unreachable_with_backoff(tmp_path):
    import functools

    from src.mcp_server import google_identity

    fetch_calls = []

    def broken_fetch():
        fetch_calls.append(1)
        raise RuntimeError("bug in the fetcher")

    clock = Clock()
    cache = google_identity.GoogleCertCache(fetch=broken_fetch, clock=clock)
    verify = functools.partial(google_identity.verify_google_credential, cert_cache=cache)
    store = OAuthStore(tmp_path / "oauth.sqlite3", clock=clock)
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE}, project_root=tmp_path)
    app = http_app.build_app(settings, store, _test_mcp(), verify_identity=verify,
                             form_secret=b"s" * 32, clock=clock)
    with TestClient(app, base_url=BASE, follow_redirects=False, raise_server_exceptions=False) as client:
        for _ in range(2):
            form_state = _start(client, Verifier())
            r = client.post("/oauth/authorize", data={"form_state": form_state, "credential": _credential(FULL)})
            assert r.status_code == 401
            assert r.text == "Google kimliği doğrulanamadı: google_unreachable"
            assert "location" not in r.headers
    assert len(fetch_calls) == 1  # the second consent is inside the backoff window


# -- S1b / T2: verification has its own limiter; a full one never starves the bearer gate ------

def test_full_verification_limiter_does_not_delay_the_bearer_gate(tmp_path):
    parked_count = http_app.VERIFY_LIMITER_TOKENS + 1
    lock, entered_all, release = threading.Lock(), threading.Event(), threading.Event()
    entered = []

    def parking_verifier(credential, nonce):
        with lock:
            entered.append(1)
            if len(entered) >= http_app.VERIFY_LIMITER_TOKENS:
                entered_all.set()
        release.wait(10)
        raise IdentityError("invalid_token")

    clock = Clock()
    store = OAuthStore(tmp_path / "oauth.sqlite3", clock=clock)
    key = store.create_static_key("gate", FULL)
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE}, project_root=tmp_path)
    app = http_app.build_app(settings, store, _test_mcp(), verify_identity=parking_verifier,
                             form_secret=b"s" * 32, clock=clock)
    with TestClient(app, base_url=BASE, follow_redirects=False) as client:
        async def shrink_default_thread_limiter():
            # As many worker threads as parked verifications: if verification borrowed from the
            # default limiter, the bearer gate's principal() lookup would have no thread left.
            anyio.to_thread.current_default_thread_limiter().total_tokens = parked_count

        client.portal.call(shrink_default_thread_limiter)
        form_state = _start(client, Verifier())
        consent = {"form_state": form_state, "credential": _credential(FULL)}
        outcome = {}

        def run(key_, call):
            try:
                outcome[key_] = call()
            except Exception as exc:  # surfaced by the assertions below
                outcome[key_] = exc

        workers = [threading.Thread(target=run, args=(i, lambda: client.post("/oauth/authorize", data=consent)))
                   for i in range(parked_count)]
        probe = threading.Thread(target=run, args=("gate", lambda: client.post(
            "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                          "params": {"name": "kimim", "arguments": {}}},
            headers={**MCP_HEADERS, "authorization": f"Bearer {key}"})))
        for w in workers:
            w.start()
        try:
            assert entered_all.wait(5), "verification limiter never filled"
            probe.start()
            probe.join(LOOP_FREE_WITHIN_SECONDS)
            assert not probe.is_alive(), "bearer gate waited behind blocked verifications"
            assert outcome["gate"].status_code == 200
        finally:
            release.set()
            for w in workers:
                w.join(10)
            if probe.ident is not None:
                probe.join(10)
    assert not any(w.is_alive() for w in workers)
    for i in range(parked_count):
        assert not isinstance(outcome[i], Exception), outcome[i]
        assert outcome[i].status_code == 401
