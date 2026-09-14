"""HTTP surface: metadata, DCR, CORS, host guard, bearer gate and identity passthrough."""
import asyncio
import json

import pytest
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.testclient import TestClient

from src.mcp_server import google_identity
from src.mcp_server.config import load_settings
from src.mcp_server.http_app import HostGuardMiddleware, build_app
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


@pytest.mark.parametrize("uri", [
    "https://claude.ai.evil.com/cb",
    "https://claude.ai/any/other/path",                      # S1b / F2.1
    "https://oauth-redirect.googleusercontent.com/r/abc",    # S1b / F2.1
    "http://localhost:notaport/cb",                          # S1b / F9
    "http://127.0.0.1:9/cb?state=x",                         # S1b / F10
])
def test_register_rejects_disallowed_redirect(client, uri):
    r = client.post("/oauth/register", json={"redirect_uris": [uri]})
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


# JWT-shaped (three base64url segments); the shape gate runs before google-auth is reached.
SHAPED = "aGVhZGVy.cGF5bG9hZA.c2lnbmF0dXJl"


def test_google_identity_checks_nonce_and_verified_email(monkeypatch):
    def fake_verify(token, request, audience):
        assert audience == google_identity.roles.GOOGLE_CLIENT_ID
        return {"email": "DrMahirKurt@gmail.com", "email_verified": True, "nonce": token}

    monkeypatch.setattr(google_identity.id_token, "verify_oauth2_token", fake_verify)
    assert google_identity.verify_google_credential(SHAPED, SHAPED) == FULL
    with pytest.raises(google_identity.IdentityError) as exc:
        google_identity.verify_google_credential(SHAPED, "other")
    assert exc.value.reason == "nonce_mismatch"

    monkeypatch.setattr(google_identity.id_token, "verify_oauth2_token",
                        lambda t, r, a: {"email": FULL, "email_verified": False, "nonce": t})
    with pytest.raises(google_identity.IdentityError) as exc:
        google_identity.verify_google_credential(SHAPED, SHAPED)
    assert exc.value.reason == "email_not_verified"

    def raises(t, r, a):
        raise ValueError("bad signature")

    monkeypatch.setattr(google_identity.id_token, "verify_oauth2_token", raises)
    with pytest.raises(google_identity.IdentityError) as exc:
        google_identity.verify_google_credential(SHAPED, SHAPED)
    assert exc.value.reason == "invalid_token"


def test_google_identity_maps_google_auth_errors(monkeypatch):
    calls = []

    def transport_error(t, r, a):
        calls.append(t)
        raise google_identity.google_exceptions.TransportError("certs unreachable")

    monkeypatch.setattr(google_identity.id_token, "verify_oauth2_token", transport_error)
    with pytest.raises(google_identity.IdentityError) as exc:
        google_identity.verify_google_credential(SHAPED, SHAPED)
    assert exc.value.reason == "google_unreachable"

    # S1a/F1: a malformed credential used to reach the cert fetch and report google_unreachable;
    # it is now refused as invalid_token before google-auth (and the network) is touched.
    calls.clear()
    with pytest.raises(google_identity.IdentityError) as exc:
        google_identity.verify_google_credential("n1", "n1")
    assert exc.value.reason == "invalid_token"
    assert calls == []

    def auth_error(t, r, a):
        raise google_identity.google_exceptions.GoogleAuthError("wrong issuer")

    monkeypatch.setattr(google_identity.id_token, "verify_oauth2_token", auth_error)
    with pytest.raises(google_identity.IdentityError) as exc:
        google_identity.verify_google_credential(SHAPED, SHAPED)
    assert exc.value.reason == "invalid_token"


# -- S1a / F3: request body and form limits ---------------------------------------------

FORM = {"content-type": "application/x-www-form-urlencoded"}


def test_oauth_body_one_byte_over_16_kib_is_413(client):
    r = client.post("/oauth/token", content=b"a" * (16_384 + 1), headers=FORM)
    assert r.status_code == 413
    assert r.json() == {"error": "payload_too_large"}


def test_oauth_body_of_exactly_16_kib_reaches_the_endpoint(client):
    body = b"grant_type=client_credentials&a=" + b"x" * 8000 + b"&b=" + b"x" * 8000 + b"&c="
    body += b"x" * (16_384 - len(body))
    assert len(body) == 16_384
    r = client.post("/oauth/token", content=body, headers=FORM)
    assert r.status_code == 400
    assert r.json() == {"error": "unsupported_grant_type"}


def test_streamed_oauth_body_without_content_length_is_413(client):
    def chunks():
        for _ in range(4):
            yield b"a" * 8192

    r = client.post("/oauth/register", content=chunks(), headers={"content-type": "application/json"})
    assert "content-length" not in r.request.headers
    assert r.status_code == 413


def test_body_limit_counts_streamed_bytes_when_content_length_understates():
    import asyncio

    from src.mcp_server.http_app import BodyLimitMiddleware

    seen = {"bytes": 0, "disconnected": False}

    async def reading_app(scope, receive, send):
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                seen["disconnected"] = True
                return
            seen["bytes"] += len(message.get("body", b""))
            if not message.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def run():
        pending = [b"a" * 10_000] * 3
        sent = []

        async def receive():
            body = pending.pop(0) if pending else b""
            return {"type": "http.request", "body": body, "more_body": bool(pending)}

        async def send(message):
            sent.append(message)

        scope = {"type": "http", "method": "POST", "path": "/oauth/token", "headers": [(b"content-length", b"10")]}
        await BodyLimitMiddleware(reading_app, mcp_max_body_bytes=2_097_152)(scope, receive, send)
        return sent

    sent = asyncio.run(run())
    assert [m["status"] for m in sent if m["type"] == "http.response.start"] == [413]
    assert seen["disconnected"] is True
    assert seen["bytes"] <= 16_384


def test_register_json_under_the_limit_is_served(client):
    body = {"redirect_uris": ["https://claude.ai/api/mcp/auth_callback"] * 100, "client_name": "x" * 8000}
    assert 10_000 < len(json.dumps(body)) < 16_384
    r = client.post("/oauth/register", json=body)
    assert r.status_code == 201
    assert r.json()["client_id"] == "ted-mcp-public"


def test_413_carries_cors_headers_for_an_allowed_origin(client):
    r = client.post("/oauth/token", content=b"a" * 20_000, headers={**FORM, "origin": "https://claude.ai"})
    assert r.status_code == 413
    assert r.headers["access-control-allow-origin"] == "https://claude.ai"
    assert "www-authenticate" in r.headers["access-control-expose-headers"]


def test_mcp_body_limit_is_read_from_the_environment(tmp_path, store):
    key = store.create_static_key("limit", FULL)
    call = _rpc("tools/call", {"name": "kimim", "arguments": {}, "_meta": {"pad": "x" * 600}})
    headers = {**MCP_HEADERS, "authorization": f"Bearer {key}"}
    small = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE, "TED_MCP_MAX_BODY_BYTES": "512"}, project_root=tmp_path)
    with TestClient(build_app(small, store, _test_mcp(), form_secret=b"s" * 32), base_url=BASE) as c:
        assert c.post("/mcp", json=call, headers=headers).status_code == 413

        def chunks():
            for _ in range(3):
                yield b" " * 400

        streamed = c.post("/mcp", content=chunks(), headers=headers)
        assert streamed.status_code == 413  # not the transport's 500, even though it catches the abort
    default = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE}, project_root=tmp_path)
    assert default.mcp_max_body_bytes == 2_097_152
    with TestClient(build_app(default, store, _test_mcp(), form_secret=b"s" * 32), base_url=BASE) as c:
        r = c.post("/mcp", json=call, headers=headers)
    assert r.status_code == 200
    assert json.loads(r.json()["result"]["content"][0]["text"]) == {"email": FULL}


@pytest.mark.parametrize("path", ["/oauth/token", "/oauth/authorize"])
def test_forms_with_21_fields_are_rejected_with_400(client, path):
    fields = {"grant_type": "client_credentials", **{f"f{i}": "x" for i in range(20)}}
    r = client.post(path, data=fields)
    assert r.status_code == 400
    assert "Too many fields" in r.text


def test_form_with_20_fields_is_parsed(client):
    fields = {"grant_type": "client_credentials", **{f"f{i}": "x" for i in range(19)}}
    r = client.post("/oauth/token", data=fields)
    assert r.status_code == 400
    assert r.json() == {"error": "unsupported_grant_type"}


def test_form_field_over_8_kib_and_file_parts_are_rejected(client):
    big = client.post("/oauth/token", data={"grant_type": "client_credentials", "pad": "x" * 8193})
    assert big.status_code == 400
    assert "maximum size" in big.text
    upload = client.post("/oauth/token", data={"grant_type": "client_credentials"}, files={"f": ("a.txt", b"hi")})
    assert upload.status_code == 400
    assert "Too many files" in upload.text


# -- S1a / R5: HostGuard parses the Host header exactly ---------------------------------

def _host_guard_status(host, allowed=("mcp.tedy.online",)):
    reached = []

    async def inner(scope, receive, send):
        reached.append(scope["path"])
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def run():
        sent = []

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            sent.append(message)

        headers = [] if host is None else [(b"host", host)]
        scope = {"type": "http", "method": "POST", "path": "/mcp", "headers": headers}
        await HostGuardMiddleware(inner, allowed_hosts=allowed)(scope, receive, send)
        return sent

    sent = asyncio.run(run())
    status = sent[0]["status"]
    assert (status == 204) == bool(reached)
    if status == 400:
        assert json.loads(sent[1]["body"]) == {"error": "host_not_allowed"}
    return status


@pytest.mark.parametrize("host", [
    b"mcp.tedy.online", b"MCP.Tedy.Online", b"mcp.tedy.online:443", b"mcp.tedy.online:1", b"mcp.tedy.online:65535",
    b"localhost", b"localhost:8087", b"127.0.0.1:8087", b"[::1]", b"[::1]:8087",
])
def test_host_guard_accepts_allowed_hosts_with_or_without_a_valid_port(host):
    assert _host_guard_status(host) == 204


@pytest.mark.parametrize("host", [
    b"mcp.tedy.online:evil", b"mcp.tedy.online:0", b"mcp.tedy.online:65536", b"mcp.tedy.online:", b"mcp.tedy.online:+443",
    b"mcp.tedy.online:443:443", b"::1", b"[::1", b"[::1]:evil", b"user@mcp.tedy.online", b"mcp.tedy.online/x",
    b"mcp.tedy.online?x", b"mcp.tedy.online#x", b"mcp.tedy\t.online", b" mcp.tedy.online", b"mcp.tedy.online.",
    b"evil.example", b"evil.example:443", b"", None,
])
def test_host_guard_rejects_malformed_or_foreign_hosts(host):
    assert _host_guard_status(host) == 400


def test_host_guard_compares_configured_hosts_case_insensitively(tmp_path, store):
    assert _host_guard_status(b"mcp.tedy.online", allowed=("MCP.TEDY.ONLINE",)) == 204
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE, "TED_MCP_ALLOWED_HOSTS": "MCP.Tedy.Online"},
                             project_root=tmp_path)
    with TestClient(build_app(settings, store, _test_mcp(), form_secret=b"s" * 32), base_url=BASE) as c:
        r = c.post("/mcp", json=_rpc("initialize"), headers=MCP_HEADERS)
    assert r.status_code == 401  # passed the host guard, stopped at the bearer gate
