"""redirect_uri policy (S1b / F2.1, F9, F10): exact callbacks, canonical form, no reserved query keys."""
import pytest

from src.mcp_server import http_app
from src.mcp_server import oauth_redirect
from src.mcp_server.config import load_settings
from src.mcp_server.oauth_redirect import RedirectPolicy, parse_extra_redirect_uris, redirect_matches
from src.mcp_server.oauth_redirect import (EXTRA_FORM_ACTION_ORIGINS_ENV, form_action_origin_problem,
                                           parse_extra_form_action_origins)

BASE = "https://mcp.tedy.online"
GEMINI = "https://oauth-redirect.googleusercontent.com/r/user_bound_custom-mcp-{}-mcp_tedy_online"


@pytest.fixture
def policy():
    return RedirectPolicy(BASE)


# -- F2.1 exact callback allowlist ----------------------------------------------------------

@pytest.mark.parametrize("uri", [
    "https://claude.ai/api/mcp/auth_callback",
    "https://claude.com/api/mcp/auth_callback",
    "https://chatgpt.com/connector_platform_oauth_redirect",
    "https://grok.com/connectors/oauth/callback",
    GEMINI.format("123456789"),
    GEMINI.format("0"),
    "http://127.0.0.1:53712/callback",
    "http://localhost:33418/",
    "http://localhost/cb",
    "http://[::1]:9/cb",
    "http://127.0.0.1:65535/any/path?x=1",
    "http://localhost:1/cb?codes=1&states=2",
])
def test_exact_callbacks_and_loopback_are_allowed(policy, uri):
    assert policy.allows(uri)


@pytest.mark.parametrize("uri", [
    # vscode.dev forwards the code to a host chosen by `state` (measured 2026-09-14): never by default
    "https://vscode.dev/redirect",
    "https://insiders.vscode.dev/redirect",
    # every other path on a trusted origin (probe_inproc.py §1)
    "https://claude.ai/any/other/path?x=1",
    "https://chatgpt.com/share/anything",
    "https://vscode.dev/redirect/x",
    "https://claude.ai/api/mcp/auth_callback/",
    "https://claude.ai/api/mcp/auth_callback?x=1",
    "https://claude.ai/api/mcp/auth_callbac",
    "https://grok.com/",
    # Google's /r/ path: only the Gemini connector shape for this server's own host
    "https://oauth-redirect.googleusercontent.com/r/any-attacker-project",
    "https://oauth-redirect.googleusercontent.com/r/user_bound_custom-mcp-123-other_host",
    "https://oauth-redirect.googleusercontent.com/r/user_bound_custom-mcp--mcp_tedy_online",
    "https://oauth-redirect.googleusercontent.com/r/user_bound_custom-mcp-12a-mcp_tedy_online",
    "https://oauth-redirect.googleusercontent.com/r/user_bound_custom-mcp-123-mcp_tedy_online/x",
    "https://oauth-redirect.googleusercontent.com/r/user_bound_custom-mcp-123-mcp.tedy.online",
    "https://oauth-redirect.googleusercontent.com/r/user_bound_custom-mcp-123-mcp_tedy_onlinex",
    "https://oauth-redirect.googleusercontent.com/r/user_bound_custom-mcp-١٢٣-mcp_tedy_online",
    GEMINI.format("123") + "?x=1",
    # lookalikes and downgrades still refused
    "https://claude.ai.evil.com/api/mcp/auth_callback",
    "http://claude.ai/api/mcp/auth_callback",
    "http://192.168.1.5:8080/cb",
    "http://127.1/cb",
    "http://localhost./cb",
    "not a url",
    "",
])
def test_everything_else_is_refused(policy, uri):
    assert not policy.allows(uri)


def test_gemini_host_segment_follows_the_public_base_url():
    other = RedirectPolicy("https://ted-mcp.example.org")
    assert other.allows("https://oauth-redirect.googleusercontent.com/r/user_bound_custom-mcp-42-ted-mcp_example_org")
    assert not other.allows(GEMINI.format("42"))


# -- F9 canonical form ----------------------------------------------------------------------

@pytest.mark.parametrize("uri", [
    "http://localhost:notaport/cb",
    "http://localhost:claude.ai-resmi-baglayici/cb",
    "http://local\thost:80/cb",
    " https://claude.ai/api/mcp/auth_callback",
    "https://claude.ai/api/mcp/auth_callback ",
    "https://claude.ai/api/mcp/auth_callback\n",
    "http://@localhost/cb",
    "http://user:pw@localhost/cb",
    "HTTPS://claude.ai/api/mcp/auth_callback",
    "https://CLAUDE.AI/api/mcp/auth_callback",
    "http://LOCALHOST:1234/cb",
    "http://localhost:0/cb",
    "http://localhost:65536/cb",
    "http://localhost:/cb",
    "http://localhost:+80/cb",
    "https://claude.ai:443/api/mcp/auth_callback",
    "http://localhost/cb#frag",
    "http://localhost/cb#",
    "http://localhost/cb?",
    "http://localhost/c\x00b",
    "http://localhost/c\x1fb",
    "http://localhost/c\x7fb",
    "http://localhost/c b",
    "http://localhost/c b",
    "http://localhost/çb",
    "http:/localhost/cb",
    "http:///localhost/cb",
    "javascript://localhost/%0aalert(1)",
])
def test_non_canonical_redirect_uris_are_refused(policy, uri):
    assert not policy.allows(uri)
    assert oauth_redirect.redirect_uri_problem(uri) is not None


# -- F10 reserved query keys ----------------------------------------------------------------

@pytest.mark.parametrize("query", [
    "code=x", "state=x", "iss=x", "error=x", "error_description=x", "error_uri=x",
    "code=", "a=1&state=2", "%63ode=x", "error_uri",
])
def test_reserved_response_keys_in_the_query_are_refused(policy, query):
    uri = f"http://127.0.0.1:8080/cb?{query}"
    assert not policy.allows(uri)
    assert oauth_redirect.redirect_uri_problem(uri) is not None


# -- TED_MCP_EXTRA_REDIRECT_URIS --------------------------------------------------------------

def test_extra_redirect_uris_are_exact_and_validated():
    extras = parse_extra_redirect_uris(" https://agent.example.org/oauth/cb ,http://127.0.0.1:9/cb,, ")
    assert extras == ("https://agent.example.org/oauth/cb", "http://127.0.0.1:9/cb")
    policy = RedirectPolicy(BASE, extras)
    assert policy.allows("https://agent.example.org/oauth/cb")
    assert not policy.allows("https://agent.example.org/oauth/cb2")
    assert not policy.allows("https://agent.example.org/oauth/cb?x=1")
    assert parse_extra_redirect_uris("") == ()


@pytest.mark.parametrize("raw", [
    "http://agent.example.org/cb",            # https only off loopback
    "https://agent.example.org/cb?state=x",   # F10
    "https://Agent.example.org/cb",           # F9: host case
    "https://agent.example.org:8443/cb",      # F9: explicit port off loopback
    "https://agent.example.org/cb#x",         # F9: fragment
    "ftp://agent.example.org/cb",
    "https://ok.example.org/cb,https://agent.example.org/c b",
])
def test_invalid_extra_redirect_uris_fail_at_startup(tmp_path, raw):
    with pytest.raises(ValueError, match="TED_MCP_EXTRA_REDIRECT_URIS"):
        parse_extra_redirect_uris(raw)
    with pytest.raises(ValueError, match="TED_MCP_EXTRA_REDIRECT_URIS"):
        load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE, "TED_MCP_EXTRA_REDIRECT_URIS": raw}, project_root=tmp_path)


def test_settings_carry_extra_redirect_uris(tmp_path):
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE,
                              "TED_MCP_EXTRA_REDIRECT_URIS": "https://agent.example.org/cb"}, project_root=tmp_path)
    assert settings.extra_redirect_uris == ("https://agent.example.org/cb",)
    assert load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE}, project_root=tmp_path).extra_redirect_uris == ()


# -- TED_MCP_EXTRA_FORM_ACTION_ORIGINS (alt proje 3, Task 5a) ------------------------------------

def test_extra_form_action_origins_are_exact_https_origins(tmp_path):
    raw = " https://auth.example.org ,https://login.example.net:8443,, https://auth.example.org"
    assert parse_extra_form_action_origins(raw) == ("https://auth.example.org", "https://login.example.net:8443")
    assert parse_extra_form_action_origins("") == () and parse_extra_form_action_origins(None) == ()
    settings = load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE, EXTRA_FORM_ACTION_ORIGINS_ENV: raw}, project_root=tmp_path)
    assert settings.extra_form_action_origins == ("https://auth.example.org", "https://login.example.net:8443")
    assert load_settings({"TED_MCP_PUBLIC_BASE_URL": BASE}, project_root=tmp_path).extra_form_action_origins == ()


@pytest.mark.parametrize("value,problem", [
    ("http://auth.example.org", "https_required"),
    ("https://127.0.0.1", "loopback"),
    ("https://localhost:8443", "loopback"),
    ("https://auth.example.org/callback", "path"),
    ("https://auth.example.org?x=1", "query"),
    ("https://*.example.org", "wildcard"),
    ("https://auth.example.org/", "trailing_slash"),
    ("https://Auth.example.org", "uppercase"),
    ("https://user@auth.example.org", "userinfo"),
    ("https://auth.example.org#x", "fragment"),
    ("https://auth.example.org:443", "default_port"),
])
def test_invalid_extra_form_action_origin_stops_startup(tmp_path, value, problem):
    assert form_action_origin_problem(value) == problem
    raw = f"https://ok.example.org,{value}"
    with pytest.raises(ValueError, match=EXTRA_FORM_ACTION_ORIGINS_ENV):
        parse_extra_form_action_origins(raw)
    with pytest.raises(ValueError, match=EXTRA_FORM_ACTION_ORIGINS_ENV):
        http_app.create_app_from_env({"TED_MCP_PUBLIC_BASE_URL": BASE, "TED_MCP_FORM_SECRET": "f" * 40,
                                      "TED_MCP_PROJECT_ROOT": str(tmp_path), EXTRA_FORM_ACTION_ORIGINS_ENV: raw})


# -- F2.3 registered-URI matching --------------------------------------------------------------

@pytest.mark.parametrize("registered,requested,matches", [
    ("https://claude.ai/api/mcp/auth_callback", "https://claude.ai/api/mcp/auth_callback", True),
    ("https://claude.ai/api/mcp/auth_callback", "https://claude.ai/api/mcp/auth_callback/", False),
    ("https://claude.ai/api/mcp/auth_callback", "https://claude.com/api/mcp/auth_callback", False),
    ("http://127.0.0.1/callback", "http://127.0.0.1:53712/callback", True),
    ("http://127.0.0.1:1111/callback", "http://127.0.0.1:53712/callback", True),
    ("http://127.0.0.1:1111/callback", "http://127.0.0.1/callback", True),
    ("http://127.0.0.1/callback", "http://localhost:53712/callback", False),
    ("http://127.0.0.1/callback", "http://127.0.0.1:53712/callback2", False),
    ("http://127.0.0.1/callback?a=1", "http://127.0.0.1:9/callback?a=1", True),
    ("http://127.0.0.1/callback?a=1", "http://127.0.0.1:9/callback?a=2", False),
    ("http://127.0.0.1/callback", "http://127.0.0.1:9/callback?a=1", False),
    ("http://[::1]/cb", "http://[::1]:9/cb", True),
])
def test_redirect_matches_exactly_except_the_loopback_port(registered, requested, matches):
    assert redirect_matches(registered, requested) is matches


def test_cors_origins_are_unchanged():
    assert oauth_redirect.is_allowed_cors_origin("https://claude.ai")
    assert oauth_redirect.is_allowed_cors_origin("https://grok.com")
    assert not oauth_redirect.is_allowed_cors_origin("https://claude.ai.evil.com")


# -- S1b fix round 1 / R-1: vscode.dev is opt-in only ----------------------------------------------

def test_vscode_web_redirects_are_not_default_but_can_be_added_explicitly():
    vscode = ("https://vscode.dev/redirect", "https://insiders.vscode.dev/redirect")
    assert RedirectPolicy(BASE).allows("https://claude.ai/api/mcp/auth_callback")  # the policy does accept defaults
    for uri in vscode:
        assert uri not in oauth_redirect.DEFAULT_REDIRECT_URIS
        assert not RedirectPolicy(BASE).allows(uri)
    policy = RedirectPolicy(BASE, parse_extra_redirect_uris(",".join(vscode)))
    for uri in vscode:
        assert policy.allows(uri)
    assert not policy.allows("https://vscode.dev/redirect/x")
