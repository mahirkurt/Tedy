"""SP4 security gate probes: cross-process ticket contract, traversal fuzz, secret hygiene, authorisation, served bytes."""
import re

import pytest
from mcp.server.fastmcp.exceptions import ToolError
from starlette.testclient import TestClient

from src import module_store as ms
from src import module_ticket as mt
from src.mcp_server import derleme, ornekler, sablon, server
from src.mcp_server.config import load_settings
from src.mcp_server.goruntuleyici import CSP, build_viewer
from src.mcp_server.katalog import CatalogWriter

SECRET = b"g" * 40
NOW = 1_800_000_000
VIEWER = "https://modul.tedy.online"
FULL = "isikkurtx@gmail.com"


@pytest.fixture
def served(tmp_path):
    html = derleme.derle(ornekler.ornek("QUIZ"), {}, "https://tedy.online").encode("utf-8")
    CatalogWriter(tmp_path, clock=lambda: NOW).yayinla(FULL, {"meta": {"mode": "QUIZ"}, "gates": {"fail": 0}},
                                                      html, "fen5-su", None)
    return tmp_path, html


def _client(data_dir):
    return TestClient(build_viewer(data_dir, SECRET, clock=lambda: NOW), base_url=VIEWER)


def _url():
    return mt.issue_module(SECRET, VIEWER, FULL, "fen5-su", 1, NOW)["url"].removeprefix(VIEWER)


def test_dashboard_ticket_opens_the_viewer_and_any_changed_signature_character_closes_it(served):
    data_dir, html = served
    url = _url()
    start = url.index("t=") + 2
    with _client(data_dir) as client:
        assert client.get(url).content == html
        for i in range(start, start + 64, 7):
            flipped = url[:i] + ("0" if url[i] != "0" else "1") + url[i + 1:]
            assert client.get(flipped).status_code == 403


def test_served_module_has_no_remote_resource_and_the_spec_csp(served):
    data_dir, _ = served
    with _client(data_dir) as client:
        response = client.get(_url())
    assert response.headers["content-security-policy"] == CSP and "connect-src 'none'" in CSP
    assert not re.search(r"""\b(?:src|srcset|poster|action)\s*=\s*["']\s*(?:https?:)?//""", response.text)
    assert response.text.count("postMessage(") == 1


@pytest.mark.parametrize("path", ["/m/%2e%2e/v1", "/m/..%2f..%2foutput/v1", "/m/fen5-su/v1%00", "/m/fen5-su/v1/",
                                  "/m/fen5-su//v1", "/taslak/..%2f..", "/m/fen5-su/v1?t=&e=&u=", "/m/fen5-su/V1"])
def test_viewer_path_fuzz_never_serves_the_module(served, path):
    data_dir, html = served
    with _client(data_dir) as client:
        response = client.get(path)
    assert response.status_code in (403, 404) and html not in response.content


def test_identifier_fuzz_never_resolves_a_path(tmp_path):
    for slug in ["..", "../fen5-su", "fen5-su/..", "%2e%2e", "fen5-su\x00", "FEN5-SU", "fen5_su", "fen5-su ",
                 " fen5-su", "fen5--su", "-fen5", "a" * 61, "ş", "fen5-su/v1", "fen5-su\\x"]:
        assert ms.module_html_path(tmp_path, slug, 1) is None, slug
    for version in [0, -1, 10000, True, "1", 1.0, None]:
        assert ms.module_html_path(tmp_path, "fen5-su", version) is None, version
    for taslak_id in ["../0123456789abcdef", "0123456789ABCDEF", "0123456789abcdeg", "", None]:
        assert ms.draft_dir(tmp_path, taslak_id) is None, taslak_id


def test_settings_repr_never_contains_secrets(tmp_path):
    env = {"EDUPEDIA_TICKET_SECRET": "ticket-" + "x" * 40, "TED_DASHBOARD_API_KEY": "tdyK_gizli"}
    env.update({k: f"key-{k}" for k in ("MUFREDAT_MCP_API_KEY", "EGITIM_KAYNAK_MCP_API_KEY", "ANAMNESIS_MCP_API_KEY",
                                         "PEXELS_MCP_API_KEY", "MINIMAX_MCP_API_KEY", "COMFYUI_MCP_API_KEY",
                                         "TR_LITERATUR_MCP_API_KEY", "OPENALEX_MCP_API_KEY")})
    text = repr(load_settings(env, project_root=tmp_path))
    for value in env.values():
        assert value not in text


class _Ctx:
    def __init__(self, email):
        state = type("State", (), {"ted_email": email})()
        request = type("Request", (), {"state": state})()
        self.request_context = type("RequestContext", (), {"request": request})()


@pytest.mark.parametrize("email", [None, "", "murzogluhulya@gmail.com", "stranger@example.com"])
def test_only_full_role_identities_reach_any_tool(email):
    with pytest.raises(ToolError):
        server.caller_email(_Ctx(email))
    assert server.caller_email(_Ctx(FULL)) == FULL


def test_engine_only_embeds_prefixed_data_uris():
    engine = sablon.engine_template("https://tedy.online")
    for prefix in ('"data:image/"', '"data:video/"', '"data:audio/"'):
        assert prefix in engine
    assert "uri.indexOf(prefix) === 0 ? uri : \"\"" in engine


def test_dashboard_session_cookie_resists_cross_site_posts(monkeypatch):
    monkeypatch.setenv("TEST_AUTH_BYPASS", "1")
    import src.dashboard_api as dashboard_api

    assert dashboard_api.app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert dashboard_api.app.config["SESSION_COOKIE_HTTPONLY"] is True
