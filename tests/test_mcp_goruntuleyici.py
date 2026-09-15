"""modul.tedy.online: ticket gate before existence, exact spec headers, traversal, removal, host isolation."""
import os

import pytest
from starlette.testclient import TestClient

from src import module_store as ms
from src import module_ticket as mt
from src.mcp_server import http_app
from src.mcp_server.config import load_settings
from src.mcp_server.federation import Federation
from src.mcp_server.goruntuleyici import CSP, NOT_FOUND_TEXT, build_viewer
from src.mcp_server.katalog import CatalogWriter
from src.mcp_server.oauth_store import OAuthStore
from src.mcp_server.server import build_server
from src.mcp_server.taslak import DraftStore
from src.mcp_server.tools import Tools

SECRET = b"t" * 40
NOW = 1_800_000_000
FULL = "isikkurtx@gmail.com"
READER = "murzogluhulya@gmail.com"
VIEWER = "https://modul.tedy.online"
MCP_BASE = "https://mcp.tedy.online"
SPEC_CSP = ("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; "
            "font-src data:; media-src data:; connect-src 'none'; frame-ancestors https://tedy.online; "
            "base-uri 'none'; form-action 'none'")
HTML = b"<!doctype html><title>modul</title>"
TASLAK = "0123456789abcdef"


@pytest.fixture
def root(tmp_path):
    data_dir = tmp_path / "output"
    writer = CatalogWriter(data_dir, clock=lambda: NOW)
    draft = {"taslak_id": TASLAK, "meta": {"title": "t", "subject": "Fen Bilimleri", "gradeLevel": "5. Sınıf",
                                           "mode": "QUIZ"}, "gates": {"pass": 18, "warn": 0, "fail": 0}}
    writer.yayinla(FULL, draft, HTML, "fen5-su", None)
    writer.yayinla(FULL, draft, HTML, "fen5-kaldirilan", None)
    writer.kaldir(FULL, "fen5-kaldirilan")
    DraftStore(data_dir).save(TASLAK, "<!doctype html><title>taslak</title>", {"run_id": "abcdef012345"})
    return tmp_path


def _app(root, now=NOW):
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": MCP_BASE}, project_root=root)
    store = OAuthStore(root / "output" / "o.sqlite3")
    mcp = build_server(Tools(settings, Federation(settings)))
    viewer = build_viewer(settings.data_dir, SECRET, clock=lambda: now)
    return http_app.build_app(settings, store, mcp, form_secret=b"s" * 32, viewer=viewer)


def _module_path(email=FULL, slug="fen5-su", version=1):
    return mt.issue_module(SECRET, VIEWER, email, slug, version, NOW)["url"].removeprefix(VIEWER)


def _request(root, method, path, base=VIEWER, now=NOW, **kwargs):
    with TestClient(_app(root, now), base_url=base) as client:
        return client.request(method, path, **kwargs)


def test_valid_ticket_serves_the_exact_bytes_with_the_spec_headers(root):
    r = _request(root, "GET", _module_path())
    assert r.status_code == 200 and r.content == HTML
    assert CSP == SPEC_CSP and r.headers["content-security-policy"] == SPEC_CSP
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["cache-control"] == "private, no-store"
    assert r.headers["x-robots-tag"] == "noindex"
    assert r.headers["content-type"].startswith("text/html")


@pytest.mark.parametrize("path_of,now", [
    (lambda: _module_path(), NOW + 601),
    (lambda: _module_path().replace("t=", "t=0"), NOW),
    (lambda: _module_path(email=READER), NOW),
    (lambda: _module_path().replace("/v1?", "/v2?"), NOW),
    (lambda: "/m/fen5-su/v1", NOW),
])
def test_bad_tickets_get_only_the_expiry_sentence(root, path_of, now):
    r = _request(root, "GET", path_of(), now=now)
    assert r.status_code == 403 and r.text == mt.EXPIRED_TEXT
    assert r.headers["content-security-policy"] == SPEC_CSP


@pytest.mark.parametrize("path", ["/m/..%2F..%2Fetc/v1", "/m/fen5-su/v0", "/m/fen5-su/v01", "/m/FEN5/v1",
                                  "/m/fen5-su", "/m/fen5-su/v1/fazla", "/taslak/zz"])
def test_malformed_paths_are_not_found(root, path):
    r = _request(root, "GET", path)
    assert r.status_code == 404 and HTML not in r.content
    assert r.headers["content-security-policy"] == SPEC_CSP


def test_removed_module_is_not_found_even_with_a_valid_ticket(root):
    r = _request(root, "GET", _module_path(slug="fen5-kaldirilan"))
    assert r.status_code == 404 and r.text == NOT_FOUND_TEXT


def test_symlinked_version_directory_is_refused(root, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "index.html").write_bytes(b"SIZINTI")
    version_dir = ms.modules_root(root / "output") / "fen5-su" / "v1"
    (version_dir / "index.html").unlink()
    version_dir.rmdir()
    os.symlink(outside, version_dir)
    r = _request(root, "GET", _module_path())
    assert r.status_code == 404 and b"SIZINTI" not in r.content


def test_draft_tickets_are_domain_separated(root):
    draft_path = mt.issue_draft(SECRET, VIEWER, FULL, TASLAK, NOW)["url"].removeprefix(VIEWER)
    r = _request(root, "GET", draft_path)
    assert r.status_code == 200 and b"taslak" in r.content and r.headers["content-security-policy"] == SPEC_CSP
    module_ticket_on_draft = _module_path().replace("/m/fen5-su/v1", f"/taslak/{TASLAK}")
    assert _request(root, "GET", module_ticket_on_draft).status_code == 403
    unknown = mt.issue_draft(SECRET, VIEWER, FULL, "ffffffffffffffff", NOW)["url"].removeprefix(VIEWER)
    assert _request(root, "GET", unknown).status_code == 404


def test_viewer_and_mcp_hosts_are_isolated(root):
    r = _request(root, "GET", _module_path(), base=MCP_BASE)
    assert r.status_code == 404 and "content-security-policy" not in r.headers
    r = _request(root, "POST", "/mcp", base=VIEWER, json={})
    assert r.status_code in (404, 405) and "www-authenticate" not in r.headers
    assert _request(root, "GET", "/.well-known/oauth-authorization-server", base=VIEWER).status_code == 404


def test_other_methods_and_origins_keep_headers_and_get_no_cors(root):
    r = _request(root, "POST", _module_path())
    assert r.status_code == 405 and r.headers["content-security-policy"] == SPEC_CSP
    r = _request(root, "GET", _module_path(), headers={"origin": "https://claude.ai"})
    assert r.status_code == 200 and "access-control-allow-origin" not in r.headers


def test_create_app_from_env_requires_ticket_secret(tmp_path):
    env = {"TED_MCP_PUBLIC_BASE_URL": MCP_BASE, "TED_MCP_PROJECT_ROOT": str(tmp_path), "TED_MCP_FORM_SECRET": "f" * 40}
    with pytest.raises(ValueError, match="EDUPEDIA_TICKET_SECRET"):
        http_app.create_app_from_env(env)
    assert http_app.create_app_from_env({**env, "EDUPEDIA_TICKET_SECRET": "t" * 40}) is not None


# -- SP4 Task 20 fix round 1 / X2 (Low): a trailing-dot viewer host still reaches the viewer -----

def test_trailing_dot_viewer_host_still_reaches_the_viewer(root):
    r = _request(root, "GET", _module_path(), base="https://modul.tedy.online.")
    assert r.status_code == 200 and r.content == HTML
    assert r.headers["content-security-policy"] == SPEC_CSP


def test_trailing_dot_mcp_host_still_does_not_reach_the_viewer(root):
    r = _request(root, "GET", _module_path(), base="https://mcp.tedy.online.")
    assert r.status_code == 404 and "content-security-policy" not in r.headers
