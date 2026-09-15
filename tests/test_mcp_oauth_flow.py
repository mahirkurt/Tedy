"""End-to-end OAuth: DCR -> consent page -> Google identity -> code -> tokens -> MCP tool with identity."""
import base64
import functools
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

from src.mcp_server import google_identity, http_app
from src.mcp_server.config import load_settings
from src.mcp_server.google_identity import IdentityError
from src.mcp_server.oauth_store import OAuthStore

BASE = "https://mcp.tedy.online"
FULL = "drmahirkurt@gmail.com"
READER = "murzogluhulya@gmail.com"
REDIRECT = "https://claude.ai/api/mcp/auth_callback"
LOOPBACK = "http://127.0.0.1/callback"
VERIFIER = "v" * 64
MCP_HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json"}
LOOP_FREE_WITHIN_SECONDS = 2.0


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

    def register_client(self, *args, **kwargs):
        self.park("register_client")
        return super().register_client(*args, **kwargs)

    def get_client(self, *args, **kwargs):
        self.park("get_client")
        return super().get_client(*args, **kwargs)

    def consume_form_state(self, *args, **kwargs):
        self.park("consume_form_state")
        return super().consume_form_state(*args, **kwargs)


def _app(tmp_path, store, verifier, clock, **settings_env):
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE, **settings_env}, project_root=tmp_path)
    return http_app.build_app(settings, store, _test_mcp(), verify_identity=verifier,
                              form_secret=b"s" * 32, clock=clock)


def _register(client, uris=(REDIRECT, LOOPBACK), name="Claude") -> str:
    r = client.post("/oauth/register", json={"redirect_uris": list(uris), "client_name": name})
    assert r.status_code == 201, r.text
    return r.json()["client_id"]


@pytest.fixture
def ctx(tmp_path):
    clock, verifier = Clock(), Verifier()
    store = OAuthStore(tmp_path / "oauth.sqlite3", clock=clock)
    with TestClient(_app(tmp_path, store, verifier, clock), base_url=BASE, follow_redirects=False) as client:
        yield client, verifier, clock, store, _register(client)


def _authorize_params(registered_id, **over):
    params = {"response_type": "code", "client_id": registered_id, "redirect_uri": REDIRECT,
              "state": "st-123", "code_challenge": _challenge(VERIFIER), "code_challenge_method": "S256"}
    params.update(over)
    return params


def _start(client, verifier, registered_id, **over):
    r = client.get("/oauth/authorize", params=_authorize_params(registered_id, **over))
    assert r.status_code == 200, r.text
    form_state = re.search(r'name="form_state" value="([^"]+)"', r.text).group(1)
    verifier.expected_nonce = http_app.nonce_for(form_state)
    return form_state


def _consent_state(page) -> str:
    return re.search(r'name="consent_state" value="([^"]+)"', page.text).group(1)


def _approve(client, form_state, credential, karar="onayla"):
    """Google sign-in, then the explicit decision; returns the response carrying the code (or error)."""
    login = client.post("/oauth/authorize", data={"form_state": form_state, "credential": credential})
    if login.status_code != 200:
        return login
    return client.post("/oauth/authorize", data={"consent_state": _consent_state(login), "karar": karar})


def _code_from(response) -> str:
    assert response.status_code == 302, response.text
    return parse_qs(urlparse(response.headers["location"]).query)["code"][0]


def _redeem(client, client_id, code, redirect_uri=REDIRECT, code_verifier=VERIFIER, **extra):
    return client.post("/oauth/token", data={"grant_type": "authorization_code", "code": code,
                                             "redirect_uri": redirect_uri, "client_id": client_id,
                                             "code_verifier": code_verifier, **extra})


def _tool_call(client, access_token):
    return client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                     "params": {"name": "kimim", "arguments": {}}},
                       headers={**MCP_HEADERS, "authorization": f"Bearer {access_token}"})


SIGN_IN_CSP = (
    "default-src 'none'; script-src https://accounts.google.com/gsi/client {script_hash}; "
    "frame-src https://accounts.google.com/gsi/; connect-src https://accounts.google.com/gsi/; "
    "style-src 'unsafe-inline' https://accounts.google.com/gsi/style; "
    "form-action 'self' https://mcp.tedy.online https://claude.ai{extra}; frame-ancestors 'none'; base-uri 'none'"
)
DECISION_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; "
    "form-action 'self' https://mcp.tedy.online https://claude.ai{extra}; frame-ancestors 'none'; base-uri 'none'"
)


def _consent_pages(client, verifier, registered_id):
    """The Google sign-in page and the Onayla/Reddet page for one authorization request."""
    sign_in = client.get("/oauth/authorize", params=_authorize_params(registered_id))
    assert sign_in.status_code == 200, sign_in.text
    form_state = re.search(r'name="form_state" value="([^"]+)"', sign_in.text).group(1)
    verifier.expected_nonce = http_app.nonce_for(form_state)
    decision = client.post("/oauth/authorize", data={"form_state": form_state, "credential": _credential(FULL)})
    assert decision.status_code == 200, decision.text
    return sign_in, decision


def test_default_consent_csp_is_byte_identical(ctx):
    client, verifier, _, _, client_id = ctx
    sign_in, decision = _consent_pages(client, verifier, client_id)
    assert sign_in.headers["content-security-policy"] == SIGN_IN_CSP.format(
        script_hash=http_app._CONSENT_SCRIPT_HASH, extra="")
    assert decision.headers["content-security-policy"] == DECISION_CSP.format(extra="")


def test_extra_form_action_origins_are_named_on_both_consent_pages(tmp_path):
    clock, verifier = Clock(), Verifier()
    store = OAuthStore(tmp_path / "oauth.sqlite3", clock=clock)
    app = _app(tmp_path, store, verifier, clock,
               TED_MCP_EXTRA_FORM_ACTION_ORIGINS="https://auth.example.org,https://login.example.net:8443")
    with TestClient(app, base_url=BASE, follow_redirects=False) as client:
        sign_in, decision = _consent_pages(client, verifier, _register(client))
    extra = " https://auth.example.org https://login.example.net:8443"
    assert sign_in.headers["content-security-policy"] == SIGN_IN_CSP.format(
        script_hash=http_app._CONSENT_SCRIPT_HASH, extra=extra)
    assert decision.headers["content-security-policy"] == DECISION_CSP.format(extra=extra)


def test_consent_page_embeds_google_signin_and_nonce(ctx):
    client, verifier, _, _, client_id = ctx
    form_state = _start(client, verifier, client_id)
    page = client.get("/oauth/authorize", params=_authorize_params(client_id)).text
    assert "accounts.google.com/gsi/client" in page
    assert http_app.roles.GOOGLE_CLIENT_ID in page
    assert "claude.ai" in page
    assert form_state


@pytest.mark.parametrize("over,reason", [
    ({"redirect_uri": "https://claude.ai.evil.com/cb"}, "redirect_uri"),
    ({"code_challenge_method": "plain"}, "S256"),
    ({"code_challenge": ""}, "code_challenge"),
    ({"response_type": "token"}, "response_type"),
    ({"client_id": "someone-else"}, "invalid_client"),
    # S1b / F2.1: only the exact callback, never another path on the same origin
    ({"redirect_uri": "https://claude.ai/any/other/path?x=1"}, "redirect_uri"),
    # S1b / F9: non-canonical forms (the consent page used to echo the fake "origin")
    ({"redirect_uri": "http://localhost:claude.ai-resmi-baglayici/cb"}, "redirect_uri"),
    ({"redirect_uri": " https://claude.ai/api/mcp/auth_callback"}, "redirect_uri"),
    ({"redirect_uri": "HTTPS://claude.ai/api/mcp/auth_callback"}, "redirect_uri"),
    # S1b / F10: a redirect_uri that already carries code/state
    ({"redirect_uri": "https://claude.ai/api/mcp/auth_callback?code=ATTACKER&state=ATTACKER"}, "redirect_uri"),
])
def test_authorize_get_rejects_bad_requests(ctx, over, reason):
    client, _, _, _, client_id = ctx
    r = client.get("/oauth/authorize", params=_authorize_params(client_id, **over))
    assert r.status_code == 400
    assert reason in r.text
    assert "location" not in r.headers
    assert "form_state" not in r.text


def test_full_round_trip_to_mcp_and_refresh(ctx):
    client, verifier, _, _, client_id = ctx
    form_state = _start(client, verifier, client_id)
    r = _approve(client, form_state, _credential(FULL))
    assert r.status_code == 302
    loc = urlparse(r.headers["location"])
    assert f"{loc.scheme}://{loc.netloc}{loc.path}" == REDIRECT
    query = parse_qs(loc.query)
    assert query["state"] == ["st-123"]

    tok = _redeem(client, client_id, query["code"][0])
    assert tok.status_code == 200
    assert tok.headers["cache-control"] == "no-store"
    body = tok.json()
    assert body["token_type"] == "Bearer" and body["expires_in"] == 3600 and body["refresh_token"]

    call = _tool_call(client, body["access_token"])
    assert call.status_code == 200
    assert json.loads(call.json()["result"]["content"][0]["text"]) == {"email": FULL}

    again = client.post("/oauth/token", data={"grant_type": "refresh_token", "refresh_token": body["refresh_token"],
                                              "client_id": client_id})
    assert again.status_code == 200
    assert again.json()["access_token"] != body["access_token"]


def test_reader_role_is_refused_without_code(ctx):
    client, verifier, _, _, client_id = ctx
    form_state = _start(client, verifier, client_id)
    r = client.post("/oauth/authorize", data={"form_state": form_state, "credential": _credential(READER)})
    assert r.status_code == 403
    assert "location" not in r.headers


def test_identity_failure_is_401(ctx):
    client, verifier, _, _, client_id = ctx
    form_state = _start(client, verifier, client_id)
    verifier.error = "nonce_mismatch"
    r = client.post("/oauth/authorize", data={"form_state": form_state, "credential": _credential(FULL)})
    assert r.status_code == 401


def test_tampered_and_expired_form_state(ctx):
    client, verifier, clock, _, client_id = ctx
    form_state = _start(client, verifier, client_id)
    payload, sig = form_state.split(".")
    tampered = payload[:-2] + ("AA" if payload[-2:] != "AA" else "BB") + "." + sig
    assert client.post("/oauth/authorize", data={"form_state": tampered, "credential": _credential(FULL)}).status_code == 400
    clock.now += http_app.FORM_TTL_SECONDS + 1
    r = client.post("/oauth/authorize", data={"form_state": form_state, "credential": _credential(FULL)})
    assert r.status_code == 400
    assert "form_state_expired" in r.text


def test_token_endpoint_errors(ctx):
    client, _, _, _, client_id = ctx
    bad = _redeem(client, client_id, "nope")
    assert bad.status_code == 400 and bad.json()["error"] == "invalid_grant"
    evil = _redeem(client, client_id, "x", redirect_uri="https://evil.example/cb")
    assert evil.status_code == 400 and evil.json()["error"] == "invalid_grant"
    other = client.post("/oauth/token", data={"grant_type": "client_credentials"})
    assert other.status_code == 400 and other.json()["error"] == "unsupported_grant_type"


def test_state_is_escaped_on_the_consent_page(ctx):
    client, _, _, _, client_id = ctx
    r = client.get("/oauth/authorize", params=_authorize_params(client_id, state='"><script>alert(1)</script>'))
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
    client, verifier, _, _, client_id = ctx
    form_state = _start(client, verifier, client_id)
    r = client.post("/oauth/authorize", data={"form_state": form_state, "credential": credential})
    assert r.status_code == 401
    assert r.text == "Google kimliği doğrulanamadı: invalid_token"
    assert "location" not in r.headers
    assert verifier.calls == 0


def test_missing_credential_is_invalid_token_without_calling_the_verifier(ctx):
    client, verifier, _, _, client_id = ctx
    form_state = _start(client, verifier, client_id)
    r = client.post("/oauth/authorize", data={"form_state": form_state})
    assert r.status_code == 401
    assert r.text == "Google kimliği doğrulanamadı: invalid_token"
    assert verifier.calls == 0


# -- S1a / F1 + S1b / T1: blocking auth work runs off the event loop --------------------

@pytest.mark.parametrize("blocked,expected_status", [
    ("verify_identity", 302),     # sign-in, then Onayla
    ("issue_code", 302),
    ("redeem_code", 400),         # unknown code: invalid_grant
    ("refresh", 400),             # unknown refresh token: invalid_grant
    ("principal", 401),
    ("register_client", 201),
    ("get_client", 200),          # the sign-in page
    ("consume_form_state", 302),  # sign-in, then Onayla
])
def test_blocked_auth_work_leaves_the_event_loop_free(tmp_path, blocked, expected_status):
    armed, entered, release = threading.Event(), threading.Event(), threading.Event()

    def park(name):
        if name == blocked and armed.is_set():
            entered.set()
            release.wait(10)

    clock = Clock()
    store = ParkingStore(tmp_path / "oauth.sqlite3", clock, park)
    verifier = Verifier(park=park)
    with TestClient(_app(tmp_path, store, verifier, clock), base_url=BASE, follow_redirects=False) as client:
        client_id = _register(client)
        form_state = _start(client, verifier, client_id)
        calls = {
            "verify_identity": lambda: _approve(client, form_state, _credential(FULL)),
            "issue_code": lambda: _approve(client, form_state, _credential(FULL)),
            "redeem_code": lambda: _redeem(client, client_id, "nope"),
            "refresh": lambda: client.post("/oauth/token", data={
                "grant_type": "refresh_token", "refresh_token": "nope", "client_id": client_id}),
            "principal": lambda: client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
                                             headers={**MCP_HEADERS, "authorization": "Bearer nope"}),
            "register_client": lambda: client.post("/oauth/register", json={"redirect_uris": [REDIRECT]}),
            "get_client": lambda: client.get("/oauth/authorize", params=_authorize_params(client_id)),
            "consume_form_state": lambda: _approve(client, form_state, _credential(FULL)),
        }
        outcome = {}

        def run(key, call):
            try:
                outcome[key] = call()
            except Exception as exc:  # surfaced by the assertions below
                outcome[key] = exc

        worker = threading.Thread(target=run, args=("blocked", calls[blocked]))
        probe = threading.Thread(target=run, args=("health", lambda: client.get("/health")))
        armed.set()
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
    assert outcome["blocked"].status_code == expected_status


# -- S1b / T4: an unexpected cert-fetch failure is 401 google_unreachable, not 500 ------------

def test_unexpected_cert_fetch_error_is_401_google_unreachable_with_backoff(tmp_path):
    fetch_calls = []

    def broken_fetch():
        fetch_calls.append(1)
        raise RuntimeError("bug in the fetcher")

    clock = Clock()
    cache = google_identity.GoogleCertCache(fetch=broken_fetch, clock=clock)
    verify = functools.partial(google_identity.verify_google_credential, cert_cache=cache)
    store = OAuthStore(tmp_path / "oauth.sqlite3", clock=clock)
    with TestClient(_app(tmp_path, store, verify, clock), base_url=BASE, follow_redirects=False,
                    raise_server_exceptions=False) as client:
        client_id = _register(client)
        for _ in range(2):
            form_state = _start(client, Verifier(), client_id)
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
    with TestClient(_app(tmp_path, store, parking_verifier, clock), base_url=BASE, follow_redirects=False) as client:
        async def shrink_default_thread_limiter():
            # As many worker threads as parked verifications: if verification borrowed from the
            # default limiter, the bearer gate's principal() lookup would have no thread left.
            anyio.to_thread.current_default_thread_limiter().total_tokens = parked_count

        form_state = _start(client, Verifier(), _register(client))
        client.portal.call(shrink_default_thread_limiter)
        consent = {"form_state": form_state, "credential": _credential(FULL)}
        outcome = {}

        def run(key_, call):
            try:
                outcome[key_] = call()
            except Exception as exc:  # surfaced by the assertions below
                outcome[key_] = exc

        workers = [threading.Thread(target=run, args=(i, lambda: client.post("/oauth/authorize", data=consent)))
                   for i in range(parked_count)]
        probe = threading.Thread(target=run, args=("gate", lambda: _tool_call(client, key)))
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


# -- S1b / F5: PKCE bounds at the HTTP surface -----------------------------------------------

@pytest.mark.parametrize("over", [
    {"code_challenge_method": "s256"},
    {"code_challenge": "x"},
    {"code_challenge": _challenge(VERIFIER)[:42]},
    {"code_challenge": _challenge(VERIFIER) + "A"},
    {"code_challenge": _challenge(VERIFIER)[:42] + "="},
])
def test_authorize_get_enforces_pkce_bounds(ctx, over):
    client, _, _, _, client_id = ctx
    r = client.get("/oauth/authorize", params=_authorize_params(client_id, **over))
    assert r.status_code == 400
    assert "code_challenge" in r.text
    assert "form_state" not in r.text


def _code_for(client, verifier, client_id, pkce_verifier=VERIFIER, **over):
    form_state = _start(client, verifier, client_id, code_challenge=_challenge(pkce_verifier), **over)
    return _code_from(_approve(client, form_state, _credential(FULL)))


def test_one_character_code_verifier_is_refused_at_the_token_endpoint(ctx):
    client, verifier, _, _, client_id = ctx
    code = _code_for(client, verifier, client_id, "a")  # S256("a") is a well-formed 43-character challenge
    tok = _redeem(client, client_id, code, code_verifier="a")
    assert tok.status_code == 400
    assert tok.json() == {"error": "invalid_grant"}


# -- S1b / F6: a replayed code revokes the access token from its first redemption ----------------

def test_code_replay_revokes_the_first_access_token(ctx):
    client, verifier, _, _, client_id = ctx
    code = _code_for(client, verifier, client_id)
    first = _redeem(client, client_id, code)
    assert first.status_code == 200
    assert _tool_call(client, first.json()["access_token"]).status_code == 200
    replay = _redeem(client, client_id, code)
    assert replay.status_code == 400
    assert replay.json() == {"error": "invalid_grant"}
    assert _tool_call(client, first.json()["access_token"]).status_code == 401
    refreshed = client.post("/oauth/token", data={"grant_type": "refresh_token", "client_id": client_id,
                                                  "refresh_token": first.json()["refresh_token"]})
    assert refreshed.status_code == 400


# -- S1b / F2.3: registered client and exact registered redirect_uri ------------------------------

def test_unregistered_client_id_is_invalid_client_at_authorize_and_token(ctx):
    client, verifier, _, _, client_id = ctx
    page = client.get("/oauth/authorize", params=_authorize_params("ted-mcp-public"))
    assert page.status_code == 400
    assert "invalid_client" in page.text
    assert "location" not in page.headers and "form_state" not in page.text
    code = _code_for(client, verifier, client_id)
    refused = _redeem(client, "ted-mcp-public", code)
    assert refused.status_code == 400
    assert refused.json() == {"error": "invalid_client"}
    good = _redeem(client, client_id, code)  # the refused request did not consume the code
    assert good.status_code == 200
    refresh = client.post("/oauth/token", data={"grant_type": "refresh_token", "client_id": "ted-mcp-public",
                                                "refresh_token": good.json()["refresh_token"]})
    assert refresh.status_code == 400
    assert refresh.json() == {"error": "invalid_client"}


def test_authorize_needs_a_redirect_uri_registered_by_that_client(ctx):
    client, _, _, _, _ = ctx
    only_claude = _register(client, uris=(REDIRECT,))
    for uri in ["https://claude.com/api/mcp/auth_callback", LOOPBACK, "http://127.0.0.1:5000/callback"]:
        r = client.get("/oauth/authorize", params=_authorize_params(only_claude, redirect_uri=uri))
        assert r.status_code == 400, uri
        assert "redirect_uri" in r.text and "location" not in r.headers
    missing = _authorize_params(only_claude)
    del missing["redirect_uri"]
    assert client.get("/oauth/authorize", params=missing).status_code == 400


@pytest.mark.parametrize("requested,allowed", [
    ("http://127.0.0.1:53712/callback", True),
    ("http://127.0.0.1/callback", True),
    ("http://127.0.0.1:53712/callback2", False),
    ("http://localhost:53712/callback", False),
    ("http://127.0.0.1:53712/callback?x=1", False),
    ("http://127.0.0.1:notaport/callback", False),
    ("http://127.0.0.1:0/callback", False),
])
def test_loopback_redirect_matches_its_registration_on_any_port(ctx, requested, allowed):
    client, _, _, _, client_id = ctx
    r = client.get("/oauth/authorize", params=_authorize_params(client_id, redirect_uri=requested))
    assert r.status_code == (200 if allowed else 400)


def test_token_redirect_uri_must_equal_the_one_the_code_is_bound_to(ctx):
    client, verifier, _, _, client_id = ctx
    bound = "http://127.0.0.1:53712/callback"
    code = _code_for(client, verifier, client_id, redirect_uri=bound)
    for other in ["http://127.0.0.1:1111/callback", LOOPBACK]:
        assert _redeem(client, client_id, code, redirect_uri=other).json() == {"error": "invalid_grant"}
    assert _redeem(client, client_id, code, redirect_uri=bound).status_code == 200


def test_code_is_bound_to_the_client_that_requested_it(ctx):
    client, verifier, _, _, client_id = ctx
    other = _register(client)
    code = _code_for(client, verifier, client_id)
    assert _redeem(client, other, code).json() == {"error": "invalid_grant"}
    assert _redeem(client, client_id, code).status_code == 200


# -- S1b / F2.4: Google sign-in leads to an explicit Onayla / Reddet step ------------------------

def _login(client, verifier, client_id, **over):
    form_state = _start(client, verifier, client_id, **over)
    return client.post("/oauth/authorize", data={"form_state": form_state, "credential": _credential(FULL)})


def test_sign_in_shows_a_decision_page_instead_of_issuing_a_code(ctx, tmp_path):
    client, verifier, _, _, client_id = ctx
    page = _login(client, verifier, client_id)
    assert page.status_code == 200
    assert "location" not in page.headers
    assert "Claude" in page.text
    assert REDIRECT in page.text
    assert FULL in page.text
    assert re.search(r'<button[^>]*name="karar"[^>]*value="onayla"', page.text)
    assert re.search(r'<button[^>]*name="karar"[^>]*value="reddet"', page.text)
    import sqlite3
    with sqlite3.connect(tmp_path / "oauth.sqlite3") as conn:
        assert conn.execute("SELECT COUNT(*) FROM oauth_code").fetchone()[0] == 0


def test_onayla_issues_the_code_and_reddet_returns_access_denied(ctx):
    client, verifier, _, _, client_id = ctx
    approved = client.post("/oauth/authorize", data={"consent_state": _consent_state(_login(client, verifier, client_id)),
                                                     "karar": "onayla"})
    loc = urlparse(approved.headers["location"])
    assert approved.status_code == 302
    assert f"{loc.scheme}://{loc.netloc}{loc.path}" == REDIRECT
    assert set(parse_qs(loc.query)) == {"code", "state"}
    assert approved.headers["cache-control"] == "no-store"
    assert approved.headers["referrer-policy"] == "no-referrer"

    denied = client.post("/oauth/authorize", data={"consent_state": _consent_state(_login(client, verifier, client_id)),
                                                   "karar": "reddet"})
    loc = urlparse(denied.headers["location"])
    assert denied.status_code == 302
    assert f"{loc.scheme}://{loc.netloc}{loc.path}" == REDIRECT
    assert parse_qs(loc.query) == {"error": ["access_denied"], "state": ["st-123"]}


def test_reddet_without_state_carries_only_the_error(ctx):
    client, verifier, _, _, client_id = ctx
    page = _login(client, verifier, client_id, state="")
    denied = client.post("/oauth/authorize", data={"consent_state": _consent_state(page), "karar": "reddet"})
    assert parse_qs(urlparse(denied.headers["location"]).query) == {"error": ["access_denied"]}


def test_role_is_checked_again_at_onayla(ctx, monkeypatch):
    client, verifier, _, _, client_id = ctx
    page = _login(client, verifier, client_id)
    monkeypatch.setattr(http_app.roles, "is_full", lambda email: False)  # demoted between the two steps
    r = client.post("/oauth/authorize", data={"consent_state": _consent_state(page), "karar": "onayla"})
    assert r.status_code == 403
    assert "location" not in r.headers


@pytest.mark.parametrize("karar", ["", "ONAYLA", "evet", "onayla "])
def test_unknown_decision_is_refused_without_consuming_the_consent(ctx, karar):
    client, verifier, _, _, client_id = ctx
    state = _consent_state(_login(client, verifier, client_id))
    r = client.post("/oauth/authorize", data={"consent_state": state, "karar": karar})
    assert r.status_code == 400
    assert "location" not in r.headers
    assert client.post("/oauth/authorize", data={"consent_state": state, "karar": "onayla"}).status_code == 302


def test_client_name_is_escaped_on_both_pages(ctx):
    client, verifier, _, _, _ = ctx
    hostile = _register(client, name='<img src=x onerror=alert(1)>"')
    first = client.get("/oauth/authorize", params=_authorize_params(hostile))
    assert first.status_code == 200
    second = _login(client, verifier, hostile)
    assert second.status_code == 200
    for page in (first, second):
        assert "<img src=x" not in page.text
        assert "&lt;img src=x onerror=alert(1)&gt;&quot;" in page.text


def test_first_page_names_the_client_and_shows_the_full_redirect_uri(ctx):
    client, _, _, _, client_id = ctx
    loopback = "http://127.0.0.1:53712/callback"
    page = client.get("/oauth/authorize", params=_authorize_params(client_id, redirect_uri=loopback))
    assert page.status_code == 200
    assert "Claude" in page.text
    assert loopback in page.text


# -- S1b / F7: both consent POSTs are single use ------------------------------------------------

def test_the_same_sign_in_post_is_refused_the_second_time(ctx):
    client, verifier, _, _, client_id = ctx
    form_state = _start(client, verifier, client_id)
    consent = {"form_state": form_state, "credential": _credential(FULL)}
    assert client.post("/oauth/authorize", data=consent).status_code == 200
    again = client.post("/oauth/authorize", data=consent)
    assert again.status_code == 400
    assert "consent_state" not in again.text and "location" not in again.headers


def test_the_same_decision_post_is_refused_the_second_time(ctx):
    client, verifier, _, _, client_id = ctx
    decision = {"consent_state": _consent_state(_login(client, verifier, client_id)), "karar": "onayla"}
    assert client.post("/oauth/authorize", data=decision).status_code == 302
    again = client.post("/oauth/authorize", data=decision)
    assert again.status_code == 400
    assert "location" not in again.headers
    denied = client.post("/oauth/authorize", data={**decision, "karar": "reddet"})
    assert denied.status_code == 400 and "location" not in denied.headers


def test_a_failed_sign_in_does_not_burn_the_form_state(ctx):
    client, verifier, _, _, client_id = ctx
    form_state = _start(client, verifier, client_id)
    verifier.error = "google_unreachable"
    assert client.post("/oauth/authorize", data={"form_state": form_state, "credential": _credential(FULL)}).status_code == 401
    verifier.error = None
    assert client.post("/oauth/authorize", data={"form_state": form_state, "credential": _credential(FULL)}).status_code == 200


def test_form_state_and_consent_state_are_not_interchangeable(ctx):
    client, verifier, _, _, client_id = ctx
    form_state = _start(client, verifier, client_id)
    as_decision = client.post("/oauth/authorize", data={"consent_state": form_state, "karar": "onayla"})
    assert as_decision.status_code == 400 and "location" not in as_decision.headers
    state = _consent_state(_login(client, verifier, client_id))
    verifier.expected_nonce = http_app.nonce_for(state)
    as_sign_in = client.post("/oauth/authorize", data={"form_state": state, "credential": _credential(FULL)})
    assert as_sign_in.status_code == 400 and "consent_state" not in as_sign_in.text


# -- S1b / R2: consent page security headers ------------------------------------------------------

def _csp(response) -> dict[str, list[str]]:
    directives = {}
    for part in response.headers["content-security-policy"].split(";"):
        tokens = part.split()
        if tokens:
            directives[tokens[0]] = tokens[1:]
    return directives


def _assert_page_headers(response):
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"
    csp = _csp(response)
    assert csp["default-src"] == ["'none'"]
    assert csp["frame-ancestors"] == ["'none'"]
    hosts = {t for values in csp.values() for t in values if t.startswith(("http:", "https:"))}
    return csp, hosts


@pytest.mark.parametrize("redirect_uri,redirect_origin", [
    (REDIRECT, "https://claude.ai"),
    ("http://127.0.0.1:53712/callback", "http://127.0.0.1:53712"),
])
def test_consent_pages_send_a_per_request_csp(ctx, redirect_uri, redirect_origin):
    client, verifier, _, _, client_id = ctx
    first = client.get("/oauth/authorize", params=_authorize_params(client_id, redirect_uri=redirect_uri))
    second = _login(client, verifier, client_id, redirect_uri=redirect_uri)
    for page in (first, second):
        assert page.status_code == 200
        csp, hosts = _assert_page_headers(page)
        # Measured pitfall: 'self' alone breaks when the page is in an opaque origin and Chrome applies
        # form-action along the redirect chain, so the issuer and the validated redirect origin are named.
        assert csp["form-action"] == ["'self'", BASE, redirect_origin]
        assert hosts <= {BASE, redirect_origin} | {h for h in hosts if h.startswith("https://accounts.google.com/")}
    csp = _csp(first)
    inline = re.search(r"<script>(.*?)</script>", first.text, re.S).group(1)
    digest = base64.b64encode(hashlib.sha256(inline.encode()).digest()).decode()
    assert f"'sha256-{digest}'" in csp["script-src"]
    assert "https://accounts.google.com/gsi/client" in csp["script-src"]
    assert csp["frame-src"] == ["https://accounts.google.com/gsi/"]
    assert csp["connect-src"] == ["https://accounts.google.com/gsi/"]
    assert "script-src" not in _csp(second)  # the decision page runs no script at all


def test_ipv6_loopback_form_action_falls_back_to_the_http_scheme(ctx):
    client, _, _, _, _ = ctx
    v6 = _register(client, uris=("http://[::1]/cb",))
    page = client.get("/oauth/authorize", params=_authorize_params(v6, redirect_uri="http://[::1]:8080/cb"))
    assert page.status_code == 200
    assert _csp(page)["form-action"] == ["'self'", BASE, "http:"]


def test_identical_authorizations_in_the_same_second_are_independent(ctx):
    # A signed state must be unique per issue: single use is keyed on it, so two identical requests
    # (a client retry, a reloaded page) must not collide and refuse each other.
    client, verifier, _, _, client_id = ctx
    first = _start(client, verifier, client_id)
    second = _start(client, verifier, client_id)
    assert first != second
    for form_state in (first, second):
        verifier.expected_nonce = http_app.nonce_for(form_state)
        page = client.post("/oauth/authorize", data={"form_state": form_state, "credential": _credential(FULL)})
        assert page.status_code == 200, page.text
        assert _consent_state(page)


# -- S1b / R1: audience binding to this server's canonical resource ------------------------------

CANONICAL_RESOURCE = f"{BASE}/mcp"


def _db_values(tmp_path, sql):
    import sqlite3

    with sqlite3.connect(tmp_path / "oauth.sqlite3") as conn:
        return {row[0] for row in conn.execute(sql)}


@pytest.mark.parametrize("resource", ["https://evil.example/other-rs", BASE, f"{BASE}/mcp/", f"{BASE}/MCP", ""])
def test_authorize_refuses_a_resource_other_than_the_one_prm_advertises(ctx, resource):
    client, _, _, _, client_id = ctx
    r = client.get("/oauth/authorize", params=_authorize_params(client_id, resource=resource))
    assert r.status_code == 400
    assert "invalid_target" in r.text
    assert "location" not in r.headers and "form_state" not in r.text


def test_canonical_resource_is_bound_to_the_code_and_the_tokens(ctx, tmp_path):
    client, verifier, _, _, client_id = ctx
    assert client.get("/.well-known/oauth-protected-resource").json()["resource"] == CANONICAL_RESOURCE
    code = _code_for(client, verifier, client_id, resource=CANONICAL_RESOURCE)
    assert _db_values(tmp_path, "SELECT resource FROM oauth_code") == {CANONICAL_RESOURCE}
    tok = _redeem(client, client_id, code, resource=CANONICAL_RESOURCE)
    assert tok.status_code == 200
    assert _db_values(tmp_path, "SELECT resource FROM oauth_access") == {CANONICAL_RESOURCE}
    assert _db_values(tmp_path, "SELECT resource FROM oauth_refresh") == {CANONICAL_RESOURCE}


def test_a_code_requested_without_resource_is_still_bound_to_this_server(ctx, tmp_path):
    client, verifier, _, _, client_id = ctx
    code = _code_for(client, verifier, client_id)
    assert _db_values(tmp_path, "SELECT resource FROM oauth_code") == {CANONICAL_RESOURCE}
    assert _redeem(client, client_id, code, resource=CANONICAL_RESOURCE).status_code == 200


def test_token_endpoint_refuses_a_foreign_resource_without_consuming_anything(ctx):
    client, verifier, _, _, client_id = ctx
    code = _code_for(client, verifier, client_id, resource=CANONICAL_RESOURCE)
    for foreign in ["https://evil.example/other-rs", ""]:
        bad = _redeem(client, client_id, code, resource=foreign)
        assert bad.status_code == 400
        assert bad.json() == {"error": "invalid_target"}
    good = _redeem(client, client_id, code)  # the code's own binding applies when resource is omitted
    assert good.status_code == 200
    refresh = {"grant_type": "refresh_token", "client_id": client_id, "refresh_token": good.json()["refresh_token"]}
    foreign = client.post("/oauth/token", data={**refresh, "resource": "https://evil.example/other-rs"})
    assert foreign.status_code == 400
    assert foreign.json() == {"error": "invalid_target"}
    assert client.post("/oauth/token", data={**refresh, "resource": CANONICAL_RESOURCE}).status_code == 200


# -- SP2 final review F4: the registered redirect's own query survives (RFC 6749 §3.1.2) ----------

QUERY_LOOPBACK = "http://127.0.0.1:53712/cb?a=b%20c&x"


@pytest.mark.parametrize("karar,expected", [("onayla", {"code", "state"}), ("reddet", {"error", "state"})])
def test_redirect_keeps_the_registered_query_byte_for_byte(ctx, karar, expected):
    client, verifier, _, _, _ = ctx
    client_id = _register(client, uris=(QUERY_LOOPBACK,))
    page = _login(client, verifier, client_id, redirect_uri=QUERY_LOOPBACK)
    assert page.status_code == 200, page.text
    r = client.post("/oauth/authorize", data={"consent_state": _consent_state(page), "karar": karar})
    assert r.status_code == 302
    location = r.headers["location"]
    prefix = QUERY_LOOPBACK + "&"
    assert location.startswith(prefix), location
    added = parse_qs(location[len(prefix):])
    assert set(added) == expected and added["state"] == ["st-123"]
    if karar == "reddet":
        assert added["error"] == ["access_denied"]
    else:
        assert _redeem(client, client_id, added["code"][0], redirect_uri=QUERY_LOOPBACK).status_code == 200


# -- SP2 final review F7: the decision page tells a user who did not start it to refuse -----------

CONSENT_WARNING = "Bu bağlantıyı az önce siz başlatmadıysanız Reddet'e basın."


def test_decision_page_warns_above_the_buttons(ctx):
    client, verifier, _, _, client_id = ctx
    page = _login(client, verifier, client_id)
    assert page.status_code == 200
    assert re.search(r'<button[^>]*name="karar"[^>]*value="reddet"', page.text)
    assert f"<p>{CONSENT_WARNING}</p>" in page.text
    assert page.text.index(CONSENT_WARNING) < page.text.index('name="karar"')
