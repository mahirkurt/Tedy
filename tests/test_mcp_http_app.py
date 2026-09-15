"""HTTP surface: metadata, DCR, CORS, host guard, bearer gate and identity passthrough."""
import asyncio
import json
import logging

import pytest
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.testclient import TestClient

from src.mcp_server import google_identity, http_app, oauth_store
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


REDIRECT = "https://claude.ai/api/mcp/auth_callback"


def test_register_persists_a_random_client_per_registration(client, store):
    first = client.post("/oauth/register", json={"redirect_uris": [REDIRECT], "client_name": "Claude"})
    second = client.post("/oauth/register", json={"redirect_uris": [REDIRECT, "http://127.0.0.1/callback"]})
    assert first.status_code == 201 and second.status_code == 201
    body = first.json()
    assert body["redirect_uris"] == [REDIRECT]
    assert body["client_name"] == "Claude"
    assert body["token_endpoint_auth_method"] == "none"
    assert isinstance(body["client_id_issued_at"], int)
    ids = {first.json()["client_id"], second.json()["client_id"]}
    assert len(ids) == 2 and "ted-mcp-public" not in ids
    assert all(isinstance(i, str) and len(i) >= 20 for i in ids)
    stored = store.get_client(body["client_id"])
    assert (stored.client_name, stored.redirect_uris) == ("Claude", (REDIRECT,))
    other = store.get_client(second.json()["client_id"])
    assert (other.client_name, other.redirect_uris) == ("", (REDIRECT, "http://127.0.0.1/callback"))
    assert store.get_client("ted-mcp-public") is None


@pytest.mark.parametrize("uris", [[], [REDIRECT] * 6, REDIRECT, [REDIRECT, 7], None])
def test_register_needs_one_to_five_redirect_uris(client, store, uris):
    body = {"client_name": "x"} if uris is None else {"redirect_uris": uris}
    r = client.post("/oauth/register", json=body)
    assert r.status_code == 400
    assert r.json() == {"error": "invalid_redirect_uri"}


def test_register_accepts_five_redirect_uris(client):
    uris = [REDIRECT, "http://127.0.0.1/a", "http://127.0.0.1/b", "http://localhost/c", "http://[::1]/d"]
    r = client.post("/oauth/register", json={"redirect_uris": uris})
    assert r.status_code == 201
    assert r.json()["redirect_uris"] == uris


@pytest.mark.parametrize("name", ["x" * 101, "a\x00b", "a\nb", "a\tb", "\x7f", "\x85", "\u202eClaude", "a\u2028b", 7, ["x"]])
def test_register_refuses_unsafe_client_names(client, name):
    r = client.post("/oauth/register", json={"redirect_uris": [REDIRECT], "client_name": name})
    assert r.status_code == 400
    assert r.json() == {"error": "invalid_client_metadata"}


@pytest.mark.parametrize("name", ["x" * 100, "Işık'ın Claude'u <b>", ""])
def test_register_accepts_plain_client_names(client, store, name):
    r = client.post("/oauth/register", json={"redirect_uris": [REDIRECT], "client_name": name})
    assert r.status_code == 201
    assert store.get_client(r.json()["client_id"]).client_name == name


@pytest.mark.parametrize("body", [b"[]", b"not json", b'"x"'])
def test_register_refuses_non_object_metadata(client, body):
    r = client.post("/oauth/register", content=body, headers={"content-type": "application/json"})
    assert r.status_code == 400
    assert r.json()["error"] in {"invalid_client_metadata"}


def test_register_is_refused_when_the_client_table_is_full_of_fresh_clients(client, store, tmp_path, monkeypatch):
    import sqlite3
    import time as _time

    monkeypatch.setattr(oauth_store, "MAX_CLIENTS", 10)  # the real cap is asserted in the store tests
    now = int(_time.time())
    with sqlite3.connect(tmp_path / "oauth.sqlite3") as conn:
        conn.executemany(
            "INSERT INTO oauth_client (client_id, client_name, redirect_uris, created_at) VALUES (?, '', ?, ?)",
            [(f"prefill-{i}", json.dumps([REDIRECT]), now) for i in range(oauth_store.MAX_CLIENTS)])
    r = client.post("/oauth/register", json={"redirect_uris": [REDIRECT]})
    assert r.status_code == 400
    assert r.json() == {"error": "invalid_client_metadata"}


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


def test_well_known_metadata_ignores_the_host_header(tmp_path, store):
    """SP3 deployment-gate followup, gap L3: HostGuardMiddleware only guards paths starting with
    /mcp (by design — see HostGuardMiddleware), so /.well-known/* answers any Host at all. The
    metadata those endpoints emit must still be built from the configured public base URL, never
    from whatever Host header a client happens to send — otherwise a spoofed or DNS-rebound Host
    could forge the issuer/endpoint URLs a client's authorization flow trusts."""
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE}, project_root=tmp_path)
    # Two separate build_app() calls: each FastMCP session manager may only be .run() once, so the
    # same app instance cannot be entered by two TestClient `with` blocks.
    evil_app = build_app(settings, store, _test_mcp(), form_secret=b"s" * 32)
    with TestClient(evil_app, base_url="https://evil.example") as evil:
        auth_meta = evil.get("/.well-known/oauth-authorization-server").json()
        res_meta = evil.get("/.well-known/oauth-protected-resource").json()
    assert auth_meta["issuer"] == BASE
    assert auth_meta["authorization_endpoint"] == f"{BASE}/oauth/authorize"
    assert auth_meta["token_endpoint"] == f"{BASE}/oauth/token"
    assert auth_meta["registration_endpoint"] == f"{BASE}/oauth/register"
    assert res_meta["resource"] == f"{BASE}/mcp"
    assert res_meta["authorization_servers"] == [BASE]
    allowed_app = build_app(settings, store, _test_mcp(), form_secret=b"s" * 32)
    with TestClient(allowed_app, base_url=BASE) as allowed:
        r = allowed.post("/mcp", json=_rpc("initialize"), headers=MCP_HEADERS)
    assert f'resource_metadata="{BASE}/.well-known/oauth-protected-resource"' in r.headers["www-authenticate"]


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


def test_register_json_under_the_limit_is_served(client, store):
    compact = json.dumps({"redirect_uris": ["https://claude.ai/api/mcp/auth_callback"], "client_name": "x"})
    body = compact[:-1] + " " * 12_000 + "}"  # insignificant whitespace pads a valid document
    assert 10_000 < len(body) < 16_384
    r = client.post("/oauth/register", content=body.encode(), headers={"content-type": "application/json"})
    assert r.status_code == 201
    assert store.get_client(r.json()["client_id"]).redirect_uris == ("https://claude.ai/api/mcp/auth_callback",)


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


# -- S1b / F8 + T1: expired rows are purged at startup, off the event loop -----------------------

def test_startup_purges_expired_rows_in_a_worker_thread(tmp_path):
    import base64
    import hashlib
    import sqlite3
    import threading

    class Clock:
        now = 1_800_000_000.0

        def __call__(self):
            return self.now

    purge_threads = []

    class RecordingStore(OAuthStore):
        def purge_expired(self):
            purge_threads.append(threading.get_ident())
            return super().purge_expired()

    clock = Clock()
    store = RecordingStore(tmp_path / "oauth.sqlite3", clock=clock)
    client_id = store.register_client("Claude", ["https://claude.ai/api/mcp/auth_callback"]).client_id
    challenge = base64.urlsafe_b64encode(hashlib.sha256(b"v" * 64).digest()).rstrip(b"=").decode()
    store.issue_code(FULL, client_id, "https://claude.ai/api/mcp/auth_callback", challenge, "S256")
    clock.now += 2 * 24 * 3600  # the code expired well over a day ago

    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE}, project_root=tmp_path)
    app = build_app(settings, store, _test_mcp(), form_secret=b"s" * 32)
    assert purge_threads == []  # building the app does not touch the database
    with TestClient(app, base_url=BASE) as c:
        async def loop_thread():
            return threading.get_ident()

        loop_ident = c.portal.call(loop_thread)
        assert c.get("/health").status_code == 200
    assert len(purge_threads) == 1, "startup did not purge expired rows"
    assert purge_threads[0] not in {threading.get_ident(), loop_ident}, "purge ran on the event loop"
    with sqlite3.connect(tmp_path / "oauth.sqlite3") as conn:
        assert conn.execute("SELECT COUNT(*) FROM oauth_code").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM oauth_client").fetchone()[0] == 1


# -- S1b fix round 1 / R-1: vscode.dev web redirects are refused unless explicitly listed --------------

@pytest.mark.parametrize("uri", ["https://vscode.dev/redirect", "https://insiders.vscode.dev/redirect"])
def test_vscode_web_redirect_is_refused_at_registration_by_default(client, uri):
    assert client.post("/oauth/register", json={"redirect_uris": [REDIRECT]}).status_code == 201
    r = client.post("/oauth/register", json={"redirect_uris": [uri], "client_name": "Visual Studio Code"})
    assert r.status_code == 400
    assert r.json() == {"error": "invalid_redirect_uri"}


def test_vscode_web_redirect_is_accepted_when_listed_in_extra_redirect_uris(tmp_path, store):
    extra = ("https://vscode.dev/redirect", "https://insiders.vscode.dev/redirect")
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE, "TED_MCP_EXTRA_REDIRECT_URIS": ",".join(extra)},
                             project_root=tmp_path)
    with TestClient(build_app(settings, store, _test_mcp(), form_secret=b"s" * 32), base_url=BASE) as c:
        for uri in extra:
            r = c.post("/oauth/register", json={"redirect_uris": [uri], "client_name": "Visual Studio Code"})
            assert r.status_code == 201, r.text
            page = c.get("/oauth/authorize", params={
                "response_type": "code", "client_id": r.json()["client_id"], "redirect_uri": uri,
                "code_challenge": "A" * 43, "code_challenge_method": "S256"})
            assert page.status_code == 200


# -- S1b fix round 1 / R-2 (revised): a registration burst no longer blocks new connectors for a day -----

def test_a_registration_burst_stops_blocking_new_connectors_after_the_eviction_floor(tmp_path, monkeypatch):
    import sqlite3

    class Clock:
        now = 1_800_000_000.0

        def __call__(self):
            return self.now

    monkeypatch.setattr(oauth_store, "MAX_CLIENTS", 10)  # the real cap (50000) is asserted in the store tests
    clock = Clock()
    store = OAuthStore(tmp_path / "oauth.sqlite3", clock=clock)
    t0 = int(clock.now)
    with sqlite3.connect(tmp_path / "oauth.sqlite3") as conn:  # an anonymous burst filled the table at t0
        conn.executemany(
            "INSERT INTO oauth_client (client_id, client_name, redirect_uris, created_at) VALUES (?, '', ?, ?)",
            [(f"burst-{i}", json.dumps(["http://127.0.0.1/x"]), t0) for i in range(oauth_store.MAX_CLIENTS)])
    floor = 2 * http_app.FORM_TTL_SECONDS  # a whole two-step consent
    body = {"redirect_uris": [REDIRECT], "client_name": "Claude"}
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE}, project_root=tmp_path)
    with TestClient(build_app(settings, store, _test_mcp(), form_secret=b"s" * 32), base_url=BASE) as c:
        # Inside the floor, including past sign-in form + code lifetime: those clients may still be mid-consent.
        for now in (t0, t0 + http_app.FORM_TTL_SECONDS + oauth_store.CODE_TTL_SECONDS + 1, t0 + floor):
            clock.now = now
            refused = c.post("/oauth/register", json=body)
            assert refused.status_code == 400, now - t0
            assert refused.json() == {"error": "invalid_client_metadata"}
        clock.now = t0 + floor + 1
        r = c.post("/oauth/register", json=body)
        assert r.status_code == 201, r.text
        assert store.get_client(r.json()["client_id"]).client_name == "Claude"


# -- SP4 Task 20 fix round 1 / X1 (Medium): viewer ticket must never reach the access log -----

# Uvicorn's default AccessFormatter: record.args = (client_addr, method, full_path, http_version, status_code).
_UVICORN_ACCESS_FMT = '%s - "%s %s HTTP/%s" %d'


def _access_record(full_path, *, args=None):
    if args is None:
        args = ("127.0.0.1:12345", "GET", full_path, "1.1", 200)
    return logging.LogRecord("uvicorn.access", logging.INFO, "h11_impl.py", 1, _UVICORN_ACCESS_FMT, args, None)


def test_module_ticket_query_string_is_redacted_from_the_access_log():
    record = _access_record("/m/fen5-su/v1?t=aaaa&e=1&u=bbbb")
    assert http_app._AccessLogQueryRedactor().filter(record) is True
    message = record.getMessage()
    assert "/m/fen5-su/v1" in message
    for leaked in ("t=aaaa", "e=1", "u=bbbb", "?t="):
        assert leaked not in message


def test_draft_ticket_query_string_is_redacted_the_same_way():
    record = _access_record("/taslak/0123456789abcdef?t=cccc&e=2&u=dddd")
    assert http_app._AccessLogQueryRedactor().filter(record) is True
    message = record.getMessage()
    assert "/taslak/0123456789abcdef" in message
    for leaked in ("t=cccc", "e=2", "u=dddd", "?t="):
        assert leaked not in message


def test_a_request_with_no_query_string_is_left_unchanged():
    record = _access_record("/health")
    original_args = tuple(record.args)
    assert http_app._AccessLogQueryRedactor().filter(record) is True
    assert record.args == original_args
    assert record.getMessage() == _UVICORN_ACCESS_FMT % original_args


@pytest.mark.parametrize("record", [
    logging.LogRecord("uvicorn.access", logging.INFO, "x", 1, "plain message, no args", None, None),
    _access_record("/m/x/v1", args=("only", "two")),
    _access_record("/m/x/v1", args=(1, 2, 3, 4, 5)),
    _access_record("/m/x/v1", args="not-a-tuple-or-list"),
])
def test_an_unrecognised_record_shape_passes_through_with_no_exception(record):
    assert http_app._AccessLogQueryRedactor().filter(record) is True


# -- SP4 Task 20 fix round 2 / two Low residuals from the round-1 re-review -------------------

def test_absolute_form_request_target_query_string_is_redacted():
    # RFC 7230 §5.3.2 absolute-form target: uvicorn's full_path does not start with "/", so the
    # round-1 leading-"/" shape check let the ticket through. The broadened "?"-only check redacts it.
    record = _access_record("http://modul.tedy.online/m/fen5-su/v1?t=SECRETTICKET&e=999&u=EMAILHASH")
    assert http_app._AccessLogQueryRedactor().filter(record) is True
    message = record.getMessage()
    assert "http://modul.tedy.online/m/fen5-su/v1" in message
    for leaked in ("t=SECRETTICKET", "e=999", "u=EMAILHASH", "?t="):
        assert leaked not in message


def test_install_access_log_redactor_wires_exactly_one_filter_onto_the_target_logger():
    # Low 2: assert main()'s wiring helper actually attaches the redactor, so a future refactor
    # that drops the install turns a test red instead of silently regressing X1.
    logger = logging.getLogger("test.uvicorn.access.wiring")
    logger.filters = []
    returned = http_app._install_access_log_redactor(logger)
    installed = [f for f in logger.filters if isinstance(f, http_app._AccessLogQueryRedactor)]
    assert len(installed) == 1
    assert returned is installed[0]
    # and the wired filter actually redacts a ticket end-to-end through the logger's filter chain
    record = _access_record("/m/fen5-su/v1?t=aaaa&e=1&u=bbbb")
    assert all(f.filter(record) for f in logger.filters)
    assert "t=aaaa" not in record.getMessage()
    logger.filters = []
