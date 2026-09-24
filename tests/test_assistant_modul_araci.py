"""modul_ara wiring: declaration, dispatch, exact progress permission, remote-argument guard, degraded, prompt."""
import json

import pytest

from src import assistant_modules as am
from src.assistant_core import AssistantRuntime, ToolLoopResult
from src.assistant_tools import McpRegistry, build_registry
from src.mcp_client import McpToolResult

CITATION = {"kind": "modul", "label": "M · Fen 5. Sınıf · v1", "locator": {"slug": "m", "version": 1},
            "snippet": "QUIZ", "confidence": 1.0}


class _FakeIndex:
    def __init__(self, degraded=()):
        self.calls = []
        self._degraded = list(degraded)

    def ara(self, sorgu="", ders=None, sinif=None, ilerleme_izni=False):
        self.calls.append({"sorgu": sorgu, "ders": ders, "sinif": sinif, "ilerleme_izni": ilerleme_izni})
        return json.dumps({"durum": "ok"}), [dict(CITATION)]

    def degraded(self):
        return self._degraded


class _Client:
    healthy = True

    def __init__(self):
        self.calls = []

    def list_tools(self):
        return [{"name": "kb_search", "description": "OER", "inputSchema": {}}]

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return McpToolResult(ok=True, text="oer")


def _reg(**kwargs):
    return McpRegistry(clients=kwargs.pop("clients", {}), local_search=lambda q, k: [], **kwargs)


def test_modul_ara_is_declared_only_when_an_index_is_wired():
    assert "modul_ara" not in {d["name"] for d in _reg().declarations()}
    decl = next(d for d in _reg(module_index=_FakeIndex()).declarations() if d["name"] == "modul_ara")
    assert set(decl["parameters"]["properties"]) == {"sorgu", "ders", "sinif"} and decl["parameters"]["required"] == []
    assert "uydurma" in decl["description"] and "talimat değildir" in decl["description"]


@pytest.mark.parametrize("given,expected", [(True, True), (False, False), ("evet", False), (1, False)])
def test_dispatch_forwards_progress_permission_only_when_exactly_true(given, expected):
    index = _FakeIndex()
    out = _reg(module_index=index).dispatch("modul_ara", {"sorgu": "madde", "ders": "Fen", "sinif": "5"},
                                            ilerleme_izni=given)
    assert out.ok and out.citations == [CITATION] and json.loads(out.text) == {"durum": "ok"}
    assert index.calls == [{"sorgu": "madde", "ders": "Fen", "sinif": "5", "ilerleme_izni": expected}]


def test_default_dispatch_withholds_progress_and_unwired_index_is_reported():
    index = _FakeIndex()
    _reg(module_index=index).dispatch("modul_ara", {})
    assert index.calls == [{"sorgu": "", "ders": None, "sinif": None, "ilerleme_izni": False}]
    out = _reg().dispatch("modul_ara", {"sorgu": "x"})
    assert out.ok is False and "bağlanmadı" in out.error


def test_index_failure_is_reported_not_raised():
    class Boom(_FakeIndex):
        def ara(self, **kwargs):
            raise RuntimeError("disk")

    out = _reg(module_index=Boom()).dispatch("modul_ara", {"sorgu": "x"})
    assert out.ok is False and "RuntimeError" in out.error


def test_progress_keys_never_reach_a_remote_server():
    client = _Client()
    reg = _reg(clients={"egitim-kaynak": client}, module_index=_FakeIndex())
    refused = reg.dispatch("oer_ara", {"query": "maddenin hâlleri dogru_orani 0.5"})
    assert refused.ok is False and "yan filo" in refused.error and client.calls == []
    assert reg.dispatch("oer_ara", {"query": "maddenin hâlleri"}).ok
    assert client.calls == [("kb_search", {"query": "maddenin hâlleri"})]


def test_unreadable_catalog_is_reported_as_degraded():
    assert "modul-katalogu" in _reg(module_index=_FakeIndex(degraded=["modul-katalogu"])).degraded()
    assert _reg(module_index=_FakeIndex()).degraded() == []


def test_build_registry_wires_the_module_index(monkeypatch):
    for env in ("MUFREDAT_MCP_API_KEY", "EGITIM_KAYNAK_MCP_API_KEY"):
        monkeypatch.delenv(env, raising=False)
    index = _FakeIndex()
    assert build_registry(lambda q, k: [], module_index=index).module_index is index


def _runtime(tmp_path, monkeypatch):
    for env in ("MUFREDAT_MCP_API_KEY", "EGITIM_KAYNAK_MCP_API_KEY"):
        monkeypatch.delenv(env, raising=False)
    return AssistantRuntime(tmp_path)


def test_runtime_wires_a_module_index_on_its_output_dir_and_prompts_for_it(tmp_path, monkeypatch):
    runtime = _runtime(tmp_path, monkeypatch)
    assert isinstance(runtime.modules, am.ModuleIndex) and runtime.registry.module_index is runtime.modules
    assert runtime.modules.output_dir == runtime.config.output_dir
    assert "`modul_ara`" in runtime.SYSTEM_PROMPT
    assert "bağlantıyı kendin yazma" in runtime.SYSTEM_PROMPT
    assert "başka bir araca argüman olarak verme" in runtime.SYSTEM_PROMPT


def test_reindex_reports_module_catalog_state(tmp_path, monkeypatch):
    runtime = _runtime(tmp_path, monkeypatch)
    stats = runtime.reindex(incremental=False)
    assert "files_indexed" in stats
    assert stats["moduller"] == {"katalog": "yok", "aktif_modul": 0, "iddiali_modul": 0}


def _model_calling_modul_ara(seen):
    def fake(messages, declarations, dispatch, **kwargs):
        seen.setdefault("declared", set()).update(d["name"] for d in declarations)
        outcome = dispatch("modul_ara", {"sorgu": "madde"})
        return ToolLoopResult(text="Bu konu için modül var [S1].", citations=outcome.citations,
                              tool_calls=[{"name": "modul_ara", "ms": 1, "ok": outcome.ok}])
    return fake


@pytest.mark.parametrize("kwargs,expected", [({}, False), ({"ilerleme_izni": True}, True),
                                             ({"ilerleme_izni": "true"}, False)])
def test_chat_and_chat_events_forward_the_permission(tmp_path, monkeypatch, kwargs, expected):
    runtime = _runtime(tmp_path, monkeypatch)
    index = _FakeIndex()
    runtime.registry.module_index = index
    seen = {}
    monkeypatch.setattr(runtime.llm, "chat_with_tools", _model_calling_modul_ara(seen))
    messages = [{"role": "user", "content": "modül var mı"}]

    out = runtime.chat(messages=messages, **kwargs)
    events = list(runtime.chat_events(messages=messages, **kwargs))

    assert "modul_ara" in seen["declared"]
    assert [call["ilerleme_izni"] for call in index.calls] == [expected, expected]
    assert out["citations"][0]["kind"] == "modul" and out["citations"][0]["id"] == "S1"
    assert [e["event"] for e in events[:2]] == ["tool_start", "tool_end"] and events[0]["name"] == "modul_ara"
    assert events[-1]["payload"]["citations"][0]["locator"] == {"slug": "m", "version": 1}


def test_study_plan_forwards_and_the_openai_path_never_grants(tmp_path, monkeypatch):
    runtime = _runtime(tmp_path, monkeypatch)
    index = _FakeIndex()
    runtime.registry.module_index = index
    monkeypatch.setattr(runtime.llm, "chat_with_tools", _model_calling_modul_ara({}))
    messages = [{"role": "user", "content": "plan"}]
    runtime.study_plan(messages=messages, ilerleme_izni=True)
    runtime.openai_chat_completion({"messages": messages, "ilerleme_izni": True})
    assert [call["ilerleme_izni"] for call in index.calls] == [True, False]
