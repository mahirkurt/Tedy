"""Tool registry: schema sanitisation, allowlist, dispatch, degradation."""
import pytest
from src.assistant_tools import (
    MCP_SERVERS, TOOL_ALLOWLIST, McpRegistry, build_registry, sanitize_schema,
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


def test_missing_api_key_makes_the_server_absent_and_degraded(monkeypatch):
    """Regression: a keyless server used to vanish from clients() and stay
    silent in degraded() too, so a dropped .env var looked healthy. Now
    build_registry() must still name it."""
    for _, (_, env_key) in MCP_SERVERS.items():
        monkeypatch.delenv(env_key, raising=False)

    reg = build_registry(local_search=lambda q, k: [])

    assert reg.clients == {}
    assert set(MCP_SERVERS) <= set(reg.degraded())


def test_local_search_exception_is_reported_not_raised():
    def boom(q, k):
        raise RuntimeError("index is down")

    reg = _registry(local_search=boom)
    out = reg.dispatch("ogrenci_verisi_ara", {"query": "ödev"})

    assert out.ok is False
    assert "index is down" in (out.error or "")


def test_non_numeric_confidence_does_not_raise():
    rows = [{"path": "output/scraped_data.json", "snippet": "Ödev: kesirler",
             "chunk_index": 3, "confidence": "yuksek"}]
    reg = _registry(local_search=lambda q, k: rows)
    out = reg.dispatch("ogrenci_verisi_ara", {"query": "ödev"})

    assert out.ok is True
    assert out.citations[0]["confidence"] == 0.0


def test_non_dict_row_is_skipped_not_raised():
    rows = [None, {"path": "output/scraped_data.json", "snippet": "Ödev: kesirler",
                    "chunk_index": 3, "confidence": 0.5}]
    reg = _registry(local_search=lambda q, k: rows)
    out = reg.dispatch("ogrenci_verisi_ara", {"query": "ödev"})

    assert out.ok is True
    assert len(out.citations) == 1
    assert out.citations[0]["locator"]["path"] == "output/scraped_data.json"


def test_dizi_parametresi_eleman_tipini_korur():
    # Live, 2026-09-22 17:27: every model returned 400 INVALID_ARGUMENT
    # "…[include_fragments].items: missing field" and the reader got the
    # fallback answer — the sanitiser dropped `items` from array parameters.
    out = sanitize_schema({"type": "object", "properties": {
        "include_fragments": {"type": "array", "items": {"type": "string", "enum": ["a", "b"]},
                              "description": "parçalar"},
        "etiketler": {"anyOf": [{"type": "array", "items": {"type": "integer"}}, {"type": "null"}]},
        "ciplak": {"type": "array"},
    }})
    props = out["properties"]
    assert props["include_fragments"]["items"] == {"type": "string", "enum": ["a", "b"]}
    assert props["etiketler"]["items"] == {"type": "integer"}
    assert props["ciplak"]["items"] == {"type": "string"}


# ── the student's grade, dead links, book titles (2026-09-25) ───────────────

def _sinifli(**over):
    reg = _registry(**over)
    reg.sinif = lambda: "7.Sınıf"
    return reg


def test_curriculum_search_defaults_to_the_students_grade():
    """Live 2026-09-25 the model searched outcomes with no grade and got every
    year's results mixed together. A search Işık did not scope is scoped to her
    own grade; the model can still ask for another one explicitly."""
    reg = _sinifli()
    reg.dispatch("kazanim_ara", {"q": "kesir"})
    reg.dispatch("kazanim_ara", {"q": "kesir", "grade": "6.Sınıf"})
    reg.dispatch("kazanim_ara", {"q": "kesir", "grade": None})
    calls = [args for _, args in reg.clients["maarif-mufredat"].calls]
    assert calls == [{"q": "kesir", "grade": "7.Sınıf"},
                     {"q": "kesir", "grade": "6.Sınıf"},
                     {"q": "kesir", "grade": "7.Sınıf"}]


def test_the_grade_default_is_declared_to_the_model():
    decl = next(d for d in _sinifli().declarations() if d["name"] == "kazanim_ara")
    assert "7.Sınıf" in decl["description"]


def test_no_grade_is_invented_when_the_class_is_unknown():
    reg = _registry()
    reg.dispatch("kazanim_ara", {"q": "kesir"})
    assert reg.clients["maarif-mufredat"].calls == [("search_learning_outcomes", {"q": "kesir"})]


def test_dead_pdf_links_never_reach_the_model():
    """Every pdf_url/source_url in the corpus answers HTTP 500 since MEB moved
    its files (CureoHub DISCOVERY-UPSTREAM-2026-09.md §2). A link the model
    repeats would be a broken promise to the reader."""
    body = ('{\n  "document_id": 233,\n  "title": "Multi English 7.Sınıf Ders Kitabı",\n'
            '  "pdf_url": "https://tymm.meb.gov.tr/upload/kitap/x.pdf",\n'
            '  "source_url": "https://tymm.meb.gov.tr/ders-kitaplari"\n}\n'
            '{\n  "document_id": 234,\n  "pdf_url": "https://tymm.meb.gov.tr/upload/kitap/y.pdf"\n}')
    tools = [{"name": "list_textbooks", "description": "Kitaplar.",
              "inputSchema": {"type": "object", "properties": {}}}]
    client = _FakeClient("maarif-mufredat", tools, McpToolResult(ok=True, text=body))
    out = _registry(clients={"maarif-mufredat": client}).dispatch("kitap_listele", {})
    assert "tymm.meb.gov.tr" not in out.text
    assert "Multi English 7.Sınıf Ders Kitabı" in out.text and '"document_id": 234' in out.text


def test_a_textbook_page_is_labelled_with_the_book_title():
    body = ('{"document": {"document_id": 213, "title": "Matematik 6.Sınıf Ders Kitabı", '
            '"pdf_url": "https://tymm.meb.gov.tr/upload/kitap/m.pdf"}, "pages": '
            '[{"page_no": 84, "text": "Oran"}]}')
    tools = [{"name": "get_document_text", "description": "Sayfa metni.",
              "inputSchema": {"type": "object", "properties": {}}}]
    client = _FakeClient("maarif-mufredat", tools, McpToolResult(ok=True, text=body))
    out = _registry(clients={"maarif-mufredat": client}).dispatch(
        "kitap_sayfa", {"document_id": 213, "page": 84})
    assert out.citations[0]["label"] == "Matematik 6.Sınıf Ders Kitabı · s.84"
