"""Tool registry: schema sanitisation, allowlist, dispatch, degradation."""
import pytest
from src.assistant_tools import (
    TOOL_ALLOWLIST, McpRegistry, sanitize_schema,
)
from src.mcp_client import McpToolResult


# The real inputSchema of maarif-mufredat's search_learning_outcomes, verbatim
# as returned by tools/list on 2026-08-23. Pydantic emits anyOf[T, null] for
# optionals and a title on every field.
REAL_SCHEMA = {
    "type": "object",
    "title": "tool_search_learning_outcomesArguments",
    "properties": {
        "q": {"description": "Arama sorgusu (örn. 'kesir', 'türev').",
              "title": "Q", "type": "string"},
        "grade": {"anyOf": [{"type": "string"}, {"type": "null"}],
                  "default": None,
                  "description": "Sınıf filtresi.", "title": "Grade"},
        "limit": {"default": 20, "maximum": 200, "minimum": 1,
                  "title": "Limit", "type": "integer"},
    },
    "required": ["q"],
}


def test_optional_anyof_collapses_to_the_non_null_type():
    out = sanitize_schema(REAL_SCHEMA)
    assert out["properties"]["grade"]["type"] == "string"
    assert "anyOf" not in out["properties"]["grade"]


def test_descriptions_survive_verbatim():
    """Measured: passing the schema WITH descriptions made the model send the
    canonical grade '5.Sınıf'; a hand-written declaration made it send '6'."""
    out = sanitize_schema(REAL_SCHEMA)
    assert out["properties"]["q"]["description"] == \
        "Arama sorgusu (örn. 'kesir', 'türev')."


def test_pydantic_title_noise_is_stripped():
    out = sanitize_schema(REAL_SCHEMA)
    assert "title" not in out
    assert all("title" not in p for p in out["properties"].values())


def test_required_list_is_preserved():
    assert sanitize_schema(REAL_SCHEMA)["required"] == ["q"]


def test_parameterless_tool_yields_empty_properties():
    out = sanitize_schema({"type": "object", "properties": {},
                           "title": "tool_server_infoArguments"})
    assert out["properties"] == {}
    assert out["required"] == []


class _FakeClient:
    def __init__(self, name, tools, result=None, healthy=True):
        self.name = name
        self._tools = tools
        self._result = result or McpToolResult(ok=True, text="sonuç")
        self.healthy = healthy
        self.calls = []

    def list_tools(self):
        return self._tools

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return self._result


def _registry(**over):
    tools = [{"name": "search_learning_outcomes",
              "description": "Kazanım araması.", "inputSchema": REAL_SCHEMA}]
    clients = {"maarif-mufredat": _FakeClient("maarif-mufredat", tools)}
    clients.update(over.pop("clients", {}))
    return McpRegistry(clients=clients,
                       local_search=over.pop("local_search", lambda q, k: []))


def test_declarations_expose_only_allowlisted_tools_under_local_names():
    reg = _registry()
    names = {d["name"] for d in reg.declarations()}
    assert "kazanim_ara" in names
    assert "search_learning_outcomes" not in names
    assert names <= set(TOOL_ALLOWLIST) | {"ogrenci_verisi_ara"}


def test_dispatch_maps_local_name_to_the_mcp_tool_name():
    reg = _registry()
    reg.dispatch("kazanim_ara", {"q": "kesir"})
    client = reg.clients["maarif-mufredat"]
    assert client.calls == [("search_learning_outcomes", {"q": "kesir"})]


def test_local_search_tool_returns_student_citations():
    rows = [{"path": "output/scraped_data.json", "snippet": "Ödev: kesirler",
             "chunk_index": 3, "confidence": 0.8}]
    reg = _registry(local_search=lambda q, k: rows)
    out = reg.dispatch("ogrenci_verisi_ara", {"query": "ödev"})

    assert out.ok is True
    assert out.citations[0]["kind"] == "ogrenci"
    assert out.citations[0]["locator"]["path"] == "output/scraped_data.json"


def test_curriculum_dispatch_tags_citations_as_mufredat():
    reg = _registry()
    out = reg.dispatch("kazanim_ara", {"q": "kesir"})
    assert out.citations[0]["kind"] == "mufredat"


def test_unknown_tool_name_is_reported_not_raised():
    out = _registry().dispatch("uydurma_arac", {})
    assert out.ok is False and "uydurma_arac" in (out.error or "")


def test_unhealthy_server_is_reported_as_degraded():
    tools = [{"name": "kb_search", "description": "OER.", "inputSchema": {}}]
    down = _FakeClient("egitim-kaynak", tools, healthy=False)
    reg = _registry(clients={"egitim-kaynak": down})
    assert "egitim-kaynak" in reg.degraded()


def test_tool_error_text_is_passed_back_for_the_model_to_correct():
    tools = [{"name": "search_learning_outcomes", "description": "d",
              "inputSchema": REAL_SCHEMA}]
    bad = _FakeClient("maarif-mufredat", tools,
                      result=McpToolResult(ok=False, error="Field required: q"))
    reg = McpRegistry(clients={"maarif-mufredat": bad}, local_search=lambda q, k: [])
    out = reg.dispatch("kazanim_ara", {})

    assert out.ok is False
    assert "Field required: q" in (out.error or "")
