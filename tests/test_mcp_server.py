"""FastMCP server wiring: identity-aware edupedia_durum, version single source, env entry."""
import json
import threading
import time

import pytest
from starlette.testclient import TestClient

from src.mcp_server import __version__, http_app, server, tools
from src.mcp_server.config import load_settings
from src.mcp_server.federation import Federation, FederationError
from src.mcp_server.oauth_store import OAuthStore

BASE = "https://mcp.tedy.online"
FULL = "drmahirkurt@gmail.com"
MCP_HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json"}


class FakeFederation:
    def __init__(self, configured=("maarif-mufredat",), fail=()):
        self._configured = set(configured)
        self._fail = set(fail)
        self.calls = []

    def configured(self, server):
        return server in self._configured

    def call(self, server, tool, args, beklenen):
        self.calls.append((server, tool))
        if server in self._fail:
            raise FederationError(server, tool, "timeout")
        return {"status": "ok"}


def _settings(tmp_path, **env):
    base = {"TED_MCP_PUBLIC_BASE_URL": BASE, "MUFREDAT_MCP_API_KEY": "k"}
    base.update(env)
    return load_settings(base, project_root=tmp_path)


def _sse_json(response):
    for line in response.text.splitlines():
        if line.startswith("data:"):
            return json.loads(line[5:].strip())
    return response.json()


def test_app_revision_reads_revision_file(tmp_path):
    assert tools.app_revision(tmp_path) is None
    (tmp_path / "REVISION").write_text("  \n", encoding="utf-8")
    assert tools.app_revision(tmp_path) is None
    (tmp_path / "REVISION").write_text("abc1234\n", encoding="utf-8")
    assert tools.app_revision(tmp_path) == "abc1234"


def test_durum_reports_identity_fleet_and_gates(tmp_path):
    t = tools.Tools(_settings(tmp_path, TED_DASHBOARD_API_KEY="tdyK_x"), FakeFederation())
    body = t.durum(FULL)
    assert body["status"] == "ok"
    assert body["surum"] == __version__
    assert body["kullanici"] == {"email": FULL, "rol": "full"}
    assert body["kapi_sayisi"] == 16
    assert body["filo"]["maarif-mufredat"] == "yapılandırılmış"
    assert body["filo"]["anamnesis"] == "anahtar yok"
    assert body["dashboard_anahtari"] is True
    assert body["medya_butcesi"] is None
    assert body["mcp_verified"] is False
    assert body["vendor"]["kaynak_commit"]
    assert "coverage" not in body


def test_durum_live_probe_builds_coverage(tmp_path):
    fed = FakeFederation(configured=("maarif-mufredat", "egitim-kaynak"), fail=("egitim-kaynak",))
    body = tools.Tools(_settings(tmp_path), fed).durum(FULL, canli=True)
    assert body["coverage"]["maarif-mufredat"] == "hit"
    assert body["coverage"]["egitim-kaynak"] == "degraded:timeout"
    assert body["coverage"]["anamnesis"] == "skipped:anahtar yok"


def _client(tmp_path, store):
    settings = _settings(tmp_path)
    mcp = server.build_server(tools.Tools(settings, FakeFederation()))
    app = http_app.build_app(settings, store, mcp, form_secret=b"s" * 32)
    return TestClient(app, base_url=BASE)


def test_initialize_reports_app_version_and_tool_list(tmp_path):
    store = OAuthStore(tmp_path / "o.sqlite3")
    key = store.create_static_key("t", FULL)
    auth = {**MCP_HEADERS, "authorization": f"Bearer {key}"}
    with _client(tmp_path, store) as c:
        init = _sse_json(c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}}, headers=auth))
        assert init["result"]["serverInfo"]["version"] == __version__
        listed = _sse_json(c.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, headers=auth))
        names = {t["name"] for t in listed["result"]["tools"]}
        assert "edupedia_durum" in names
        durum = next(t for t in listed["result"]["tools"] if t["name"] == "edupedia_durum")
        assert durum["annotations"]["readOnlyHint"] is True


def test_tool_call_carries_caller_identity(tmp_path):
    store = OAuthStore(tmp_path / "o.sqlite3")
    key = store.create_static_key("t", FULL)
    with _client(tmp_path, store) as c:
        r = _sse_json(c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                           "params": {"name": "edupedia_durum", "arguments": {}}},
                             headers={**MCP_HEADERS, "authorization": f"Bearer {key}"}))
    body = json.loads(r["result"]["content"][0]["text"])
    assert body["kullanici"]["email"] == FULL


def test_create_app_from_env_requires_form_secret(tmp_path):
    with pytest.raises(ValueError):
        http_app.create_app_from_env({"TED_MCP_PUBLIC_BASE_URL": BASE, "TED_MCP_PROJECT_ROOT": str(tmp_path)})
    app = http_app.create_app_from_env({"TED_MCP_PUBLIC_BASE_URL": BASE, "TED_MCP_PROJECT_ROOT": str(tmp_path),
                                        "TED_MCP_FORM_SECRET": "f" * 40})
    assert app is not None


def test_rehber_tool_is_registered_and_returns_akis(tmp_path):
    store = OAuthStore(tmp_path / "o.sqlite3")
    key = store.create_static_key("t", FULL)
    with _client(tmp_path, store) as c:
        r = _sse_json(c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                           "params": {"name": "edupedia_rehber", "arguments": {"bolum": "akis"}}},
                             headers={**MCP_HEADERS, "authorization": f"Bearer {key}"}))
    body = json.loads(r["result"]["content"][0]["text"])
    assert body["bolum"] == "akis" and body["status"] == "ok"


def test_slow_tool_does_not_block_concurrent_requests(tmp_path):
    """One slow tool call must not freeze the event loop for other concurrent requests.

    Regression guard for the fix that runs each tool body in a worker thread
    (anyio.to_thread.run_sync) instead of calling it directly on the event loop.
    """
    entered = threading.Event()
    release = threading.Event()

    class BlockingTools(tools.Tools):
        def durum(self, email, canli=False):
            entered.set()
            release.wait(10)  # generous safety timeout; normally cleared by the main thread below
            return super().durum(email, canli=canli)

    settings = _settings(tmp_path)
    store = OAuthStore(tmp_path / "o.sqlite3")
    key = store.create_static_key("t", FULL)
    mcp = server.build_server(BlockingTools(settings, FakeFederation()))
    app = http_app.build_app(settings, store, mcp, form_secret=b"s" * 32)
    auth = {**MCP_HEADERS, "authorization": f"Bearer {key}"}

    durum_result: dict = {}

    with TestClient(app, base_url=BASE) as c:

        def call_durum():
            durum_result["body"] = _sse_json(c.post("/mcp", json={
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "edupedia_durum", "arguments": {}}}, headers=auth))

        thread = threading.Thread(target=call_durum, daemon=True)
        thread.start()
        assert entered.wait(5), "durum call never entered its blocking section"

        start = time.monotonic()
        rehber_raw = _sse_json(c.post("/mcp", json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "edupedia_rehber", "arguments": {"bolum": "akis"}}}, headers=auth))
        elapsed = time.monotonic() - start

        rehber_body = json.loads(rehber_raw["result"]["content"][0]["text"])
        # The durum call must still be blocked (release not yet set) when rehber returns,
        # and it must have returned fast rather than waiting out durum's 10s safety timeout.
        assert not release.is_set()
        assert elapsed < 5, f"edupedia_rehber took {elapsed:.1f}s — event loop was blocked by edupedia_durum"
        assert rehber_body["status"] == "ok"

        release.set()
        thread.join(timeout=10)
        assert not thread.is_alive(), "durum call thread did not finish after release"

    durum_body = json.loads(durum_result["body"]["result"]["content"][0]["text"])
    assert durum_body["status"] == "ok"
