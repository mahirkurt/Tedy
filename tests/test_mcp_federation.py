"""Config loading, coverage manifest and the federation JSON decoding contract."""
import json
from pathlib import Path

import pytest

from src.mcp_client import McpToolResult
from src.mcp_server import config, coverage, federation


def _env(**over):
    base = {
        "TED_MCP_PUBLIC_BASE_URL": "https://mcp.tedy.online",
        "MUFREDAT_MCP_API_KEY": "k-muf",
        "EGITIM_KAYNAK_MCP_API_KEY": "k-egi",
        "ANAMNESIS_MCP_API_KEY": "",
        "TED_DASHBOARD_API_KEY": "tdyK_x",
    }
    base.update(over)
    return base


def test_load_settings_defaults(tmp_path):
    s = config.load_settings(_env(), project_root=tmp_path)
    assert s.public_base_url == "https://mcp.tedy.online"
    assert s.allowed_hosts == ("mcp.tedy.online",)
    assert s.data_dir == tmp_path / "output"
    assert s.oauth_db_path == tmp_path / "output" / "ted_mcp_oauth.sqlite3"
    assert s.dashboard_api_url == "http://127.0.0.1:8085"
    assert s.servers["maarif-mufredat"].url == "https://mufredat.cureonics.com/mcp"
    assert s.servers["egitim-kaynak"].api_key == "k-egi"
    assert s.servers["anamnesis"].url == "https://anamnesis-mcp.cureonics.workers.dev/mcp"


def test_load_settings_overrides_and_strips_trailing_slash(tmp_path):
    s = config.load_settings(
        _env(TED_MCP_PUBLIC_BASE_URL="https://x.example/", TED_MCP_ALLOWED_HOSTS="a.example, b.example"),
        project_root=tmp_path,
    )
    assert s.public_base_url == "https://x.example"
    assert s.allowed_hosts == ("a.example", "b.example")


def test_coverage_manifest_records_each_state():
    c = coverage.Coverage()
    c.hit("maarif-mufredat")
    c.empty("egitim-kaynak")
    c.degraded("anamnesis", "timeout")
    c.skipped("pexels", "alt proje 4")
    assert c.as_dict() == {
        "maarif-mufredat": "hit",
        "egitim-kaynak": "empty",
        "anamnesis": "degraded:timeout",
        "pexels": "skipped:alt proje 4",
    }


def test_decode_json_stream_handles_concatenated_pretty_objects():
    text = json.dumps({"a": 1}, indent=2) + "\n" + json.dumps({"b": 2}, indent=2)
    assert federation.decode_json_stream(text) == [{"a": 1}, {"b": 2}]
    assert federation.decode_json_stream("") == []
    assert federation.decode_json_stream("  \n ") == []


def test_decode_json_stream_rejects_garbage():
    with pytest.raises(ValueError):
        federation.decode_json_stream('{"a": 1} not-json')


class _FakeClient:
    calls = []

    def __init__(self, name, url, api_key, timeout=25.0, session=None):
        self.name = name

    def call_tool(self, name, arguments):
        _FakeClient.calls.append((self.name, name, arguments))
        return _FakeClient.responses[(self.name, name)]


def _fed(tmp_path, responses):
    _FakeClient.responses = responses
    _FakeClient.calls = []
    return federation.Federation(config.load_settings(_env(), project_root=tmp_path), client_factory=_FakeClient)


def test_call_liste_single_item_stays_a_list(tmp_path):
    item = {"slug": "fen-bilimleri-dersi"}
    fed = _fed(tmp_path, {("maarif-mufredat", "list_subjects"): McpToolResult(ok=True, text=json.dumps(item, indent=2))})
    assert fed.call("maarif-mufredat", "list_subjects", {"q": "fen"}, beklenen="liste") == [item]


def test_call_liste_empty_text_is_empty_list(tmp_path):
    fed = _fed(tmp_path, {("maarif-mufredat", "list_subjects"): McpToolResult(ok=True, text="")})
    assert fed.call("maarif-mufredat", "list_subjects", {}, beklenen="liste") == []


def test_call_nesne_requires_exactly_one_object(tmp_path):
    two = json.dumps({"a": 1}) + "\n" + json.dumps({"b": 2})
    fed = _fed(tmp_path, {
        ("maarif-mufredat", "search_learning_outcomes"): McpToolResult(ok=True, text=json.dumps({"results": []})),
        ("maarif-mufredat", "server_info"): McpToolResult(ok=True, text=two),
    })
    assert fed.call("maarif-mufredat", "search_learning_outcomes", {"q": "x"}, beklenen="nesne") == {"results": []}
    with pytest.raises(federation.FederationError) as exc:
        fed.call("maarif-mufredat", "server_info", {}, beklenen="nesne")
    assert exc.value.reason == "unexpected_shape"


def test_call_tool_error_raises_with_reason(tmp_path):
    fed = _fed(tmp_path, {("egitim-kaynak", "kb_search"): McpToolResult(ok=False, error="boom")})
    with pytest.raises(federation.FederationError) as exc:
        fed.call("egitim-kaynak", "kb_search", {"q": "x"}, beklenen="nesne")
    assert exc.value.server == "egitim-kaynak"
    assert exc.value.reason == "tool_error: boom"


def test_unconfigured_server_raises_without_calling(tmp_path):
    fed = _fed(tmp_path, {})
    assert fed.configured("anamnesis") is False
    with pytest.raises(federation.FederationError) as exc:
        fed.call("anamnesis", "hybrid_query", {}, beklenen="nesne")
    assert exc.value.reason == "not_configured"
    assert _FakeClient.calls == []


def test_clients_are_reused_per_server(tmp_path):
    fed = _fed(tmp_path, {("maarif-mufredat", "list_subjects"): McpToolResult(ok=True, text="")})
    fed.call("maarif-mufredat", "list_subjects", {}, beklenen="liste")
    fed.call("maarif-mufredat", "list_subjects", {}, beklenen="liste")
    assert fed._client("maarif-mufredat") is fed._client("maarif-mufredat")


def test_mcp_max_body_bytes_defaults_to_2_mib_and_reads_the_environment(tmp_path):
    assert config.load_settings(_env(), project_root=tmp_path).mcp_max_body_bytes == 2_097_152
    assert config.load_settings(_env(TED_MCP_MAX_BODY_BYTES=""), project_root=tmp_path).mcp_max_body_bytes == 2_097_152
    got = config.load_settings(_env(TED_MCP_MAX_BODY_BYTES=" 65536 "), project_root=tmp_path)
    assert got.mcp_max_body_bytes == 65_536


@pytest.mark.parametrize("raw", ["abc", "0", "-1", "1.5", "2MB"])
def test_mcp_max_body_bytes_rejects_anything_but_a_positive_integer(tmp_path, raw):
    with pytest.raises(ValueError, match="TED_MCP_MAX_BODY_BYTES"):
        config.load_settings(_env(TED_MCP_MAX_BODY_BYTES=raw), project_root=tmp_path)


# -- SP2 final review F1: spec §7 time budget (25 s per call, 60 s per tool) ---------------------

class _Clock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now


def _timed_fed(tmp_path, clock, took=0.0, result=None):
    """Real Federation over a fake client that records the timeout it was given and takes `took`
    seconds on the shared fake monotonic clock."""
    calls = []

    class Client:
        def __init__(self, name, url, api_key, **kw):
            self.name = name

        def call_tool(self, name, arguments, timeout=None):
            calls.append({"tool": name, "timeout": timeout, "at": clock.now})
            clock.now += took
            return result or McpToolResult(ok=True, text="{}")

    settings = config.load_settings(_env(), project_root=tmp_path)
    return federation.Federation(settings, client_factory=Client, monotonic=clock), calls


def test_budget_constants_match_spec_section_7():
    assert federation.CALL_TIMEOUT_SECONDS == 25.0
    assert federation.TOOL_BUDGET_SECONDS == 60.0
    assert federation.MIN_CALL_SECONDS == 1.0


def test_deadline_caps_the_client_timeout_at_the_remaining_budget(tmp_path):
    clock = _Clock()
    fed, calls = _timed_fed(tmp_path, clock)
    fed.call("maarif-mufredat", "server_info", {}, beklenen="nesne", deadline=clock.now + 60.0)
    fed.call("maarif-mufredat", "server_info", {}, beklenen="nesne", deadline=clock.now + 10.0)
    assert [c["timeout"] for c in calls] == [25.0, 10.0]


def test_no_deadline_passes_no_client_timeout(tmp_path):
    fed, calls = _timed_fed(tmp_path, _Clock())
    fed.call("maarif-mufredat", "server_info", {}, beklenen="nesne")
    assert calls == [{"tool": "server_info", "timeout": None, "at": 1000.0}]


@pytest.mark.parametrize("left", [0.99, 0.0, -5.0])
def test_a_call_the_budget_cannot_cover_is_zaman_asimi_without_calling(tmp_path, left):
    clock = _Clock()
    fed, calls = _timed_fed(tmp_path, clock)
    with pytest.raises(federation.FederationError) as exc:
        fed.call("egitim-kaynak", "kb_search", {"q": "x"}, beklenen="nesne", deadline=clock.now + left)
    assert exc.value.reason == "zaman_asimi"
    assert calls == []


def test_a_failure_that_spent_the_budget_is_zaman_asimi(tmp_path):
    clock = _Clock()
    fed, calls = _timed_fed(tmp_path, clock, took=10.0,
                            result=McpToolResult(ok=False, error="Read timed out. (read timeout=10.0)"))
    with pytest.raises(federation.FederationError) as exc:
        fed.call("egitim-kaynak", "kb_search", {}, beklenen="nesne", deadline=clock.now + 10.0)
    assert calls[0]["timeout"] == 10.0
    assert exc.value.reason == "zaman_asimi"


def test_a_failure_with_budget_left_is_not_blamed_on_the_budget(tmp_path):
    clock = _Clock()
    fed, _ = _timed_fed(tmp_path, clock, took=2.0, result=McpToolResult(ok=False, error="boom"))
    with pytest.raises(federation.FederationError) as exc:
        fed.call("egitim-kaynak", "kb_search", {}, beklenen="nesne", deadline=clock.now + 60.0)
    assert exc.value.reason.startswith("tool_error")
