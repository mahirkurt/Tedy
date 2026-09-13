"""HTTP surface: metadata, DCR, CORS, host guard, bearer gate and identity passthrough."""
import json

import pytest
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.testclient import TestClient

from src.mcp_server import google_identity, oauth_redirect
from src.mcp_server.config import load_settings
from src.mcp_server.http_app import build_app
from src.mcp_server.oauth_store import OAuthStore

BASE = "https://mcp.tedy.online"
FULL = "drmahirkurt@gmail.com"


def _test_mcp() -> FastMCP:
    mcp = FastMCP(
        "test",
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    @mcp.tool()
    def kimim(ctx: Context) -> dict:
        return {"email": ctx.request_context.request.state.ted_email}

    return mcp


@pytest.fixture
def store(tmp_path):
    return OAuthStore(tmp_path / "oauth.sqlite3")


@pytest.fixture
def client(tmp_path, store):
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE}, project_root=tmp_path)
    app = build_app(settings, store, _test_mcp(), form_secret=b"s" * 32)
    with TestClient(app, base_url=BASE) as c:
        yield c


def _rpc(method, params=None, id_=1):
    return {"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}}


MCP_HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json"}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.parametrize("path", ["/.well-known/oauth-protected-resource", "/.well-known/oauth-protected-resource/mcp"])
def test_protected_resource_metadata(client, path):
    body = client.get(path).json()
    assert body["resource"] == f"{BASE}/mcp"
    assert body["authorization_servers"] == [BASE]
    assert body["bearer_methods_supported"] == ["header"]


def test_authorization_server_metadata_is_s256_only(client):
    body = client.get("/.well-known/oauth-authorization-server").json()
    assert body["issuer"] == BASE
    assert body["authorization_endpoint"] == f"{BASE}/oauth/authorize"
    assert body["token_endpoint"] == f"{BASE}/oauth/token"
    assert body["registration_endpoint"] == f"{BASE}/oauth/register"
    assert body["code_challenge_methods_supported"] == ["S256"]
    assert body["grant_types_supported"] == ["authorization_code", "refresh_token"]


def test_register_echoes_allowed_redirect_uris(client):
    r = client.post("/oauth/register", json={"redirect_uris": ["https://claude.ai/api/mcp/auth_callback"]})
    assert r.status_code == 201
    assert r.json()["client_id"] == "ted-mcp-public"
    assert r.json()["redirect_uris"] == ["https://claude.ai/api/mcp/auth_callback"]


def test_register_rejects_disallowed_redirect(client):
    r = client.post("/oauth/register", json={"redirect_uris": ["https://claude.ai.evil.com/cb"]})
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_redirect_uri"


def test_mcp_without_bearer_is_401_with_resource_metadata(client):
    r = client.post("/mcp", json=_rpc("initialize"), headers={**MCP_HEADERS, "origin": "https://claude.ai"})
    assert r.status_code == 401
    challenge = r.headers["www-authenticate"]
    assert 'realm="ted-mcp"' in challenge
    assert f'resource_metadata="{BASE}/.well-known/oauth-protected-resource"' in challenge
    assert r.headers["access-control-allow-origin"] == "https://claude.ai"
    assert "www-authenticate" in r.headers["access-control-expose-headers"]


@pytest.mark.parametrize("bearer", ["tdyK_" + "a" * 40, "garbage", "ünicode"])
def test_unknown_bearers_are_401_not_500(client, bearer):
    r = client.post("/mcp", json=_rpc("initialize"), headers={**MCP_HEADERS, "authorization": f"Bearer {bearer}".encode("utf-8")})
    assert r.status_code == 401


def test_preflight_short_circuits_before_auth(client):
    ok = client.options("/mcp", headers={"origin": "https://grok.com", "access-control-request-method": "POST"})
    assert ok.status_code == 204
    assert ok.headers["access-control-allow-origin"] == "https://grok.com"
    bad = client.options("/mcp", headers={"origin": "https://evil.example", "access-control-request-method": "POST"})
    assert bad.status_code == 204
    assert "access-control-allow-origin" not in bad.headers


def test_host_guard_rejects_foreign_host(tmp_path, store):
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE}, project_root=tmp_path)
    app = build_app(settings, store, _test_mcp(), form_secret=b"s" * 32)
    with TestClient(app, base_url="https://evil.example") as c:
        r = c.post("/mcp", json=_rpc("initialize"), headers=MCP_HEADERS)
    assert r.status_code == 400
    assert r.json()["error"] == "host_not_allowed"


def test_static_key_reaches_tool_with_identity(client, store):
    key = store.create_static_key("test", FULL)
    r = client.post(
        "/mcp",
        json=_rpc("tools/call", {"name": "kimim", "arguments": {}}),
        headers={**MCP_HEADERS, "authorization": f"Bearer {key}"},
    )
    assert r.status_code == 200
    content = r.json()["result"]["content"][0]["text"]
    assert json.loads(content) == {"email": FULL}


def test_redirect_policy():
    assert oauth_redirect.is_allowed_redirect("https://chatgpt.com/connector_platform_oauth_redirect")
    assert oauth_redirect.is_allowed_redirect("https://oauth-redirect.googleusercontent.com/r/abc")
    assert oauth_redirect.is_allowed_redirect("http://127.0.0.1:53712/callback")
    assert oauth_redirect.is_allowed_redirect("http://localhost:33418/")
    assert not oauth_redirect.is_allowed_redirect("http://claude.ai/cb")
    assert not oauth_redirect.is_allowed_redirect("https://claude.ai.evil.com/cb")
    assert not oauth_redirect.is_allowed_redirect("https://claude.ai/cb#frag")
    assert not oauth_redirect.is_allowed_redirect("http://192.168.1.5:8080/cb")
    assert not oauth_redirect.is_allowed_redirect("not a url")


def test_google_identity_checks_nonce_and_verified_email(monkeypatch):
    def fake_verify(token, request, audience):
        assert audience == google_identity.roles.GOOGLE_CLIENT_ID
        return {"email": "DrMahirKurt@gmail.com", "email_verified": True, "nonce": token}

    monkeypatch.setattr(google_identity.id_token, "verify_oauth2_token", fake_verify)
    assert google_identity.verify_google_credential("n1", "n1") == FULL
    with pytest.raises(google_identity.IdentityError) as exc:
        google_identity.verify_google_credential("n1", "other")
    assert exc.value.reason == "nonce_mismatch"

    monkeypatch.setattr(google_identity.id_token, "verify_oauth2_token",
                        lambda t, r, a: {"email": FULL, "email_verified": False, "nonce": t})
    with pytest.raises(google_identity.IdentityError) as exc:
        google_identity.verify_google_credential("n1", "n1")
    assert exc.value.reason == "email_not_verified"

    def raises(t, r, a):
        raise ValueError("bad signature")

    monkeypatch.setattr(google_identity.id_token, "verify_oauth2_token", raises)
    with pytest.raises(google_identity.IdentityError) as exc:
        google_identity.verify_google_credential("n1", "n1")
    assert exc.value.reason == "invalid_token"
