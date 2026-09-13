"""End-to-end OAuth: consent page -> Google identity -> code -> tokens -> MCP tool with identity."""
import base64
import hashlib
import json
import re
from urllib.parse import parse_qs, urlparse

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


class Verifier:
    """Test double: the 'credential' is the email; asserts the nonce binds to form_state."""

    def __init__(self):
        self.expected_nonce = None
        self.error = None

    def __call__(self, credential, nonce):
        assert nonce == self.expected_nonce
        if self.error:
            raise IdentityError(self.error)
        return credential


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
    r = client.post("/oauth/authorize", data={"form_state": form_state, "credential": FULL})
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
    r = client.post("/oauth/authorize", data={"form_state": form_state, "credential": READER})
    assert r.status_code == 403
    assert "location" not in r.headers


def test_identity_failure_is_401(ctx):
    client, verifier, _, _ = ctx
    form_state = _start(client, verifier)
    verifier.error = "nonce_mismatch"
    r = client.post("/oauth/authorize", data={"form_state": form_state, "credential": FULL})
    assert r.status_code == 401


def test_tampered_and_expired_form_state(ctx):
    client, verifier, clock, _ = ctx
    form_state = _start(client, verifier)
    payload, sig = form_state.split(".")
    tampered = payload[:-2] + ("AA" if payload[-2:] != "AA" else "BB") + "." + sig
    assert client.post("/oauth/authorize", data={"form_state": tampered, "credential": FULL}).status_code == 400
    clock.now += http_app.FORM_TTL_SECONDS + 1
    r = client.post("/oauth/authorize", data={"form_state": form_state, "credential": FULL})
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
