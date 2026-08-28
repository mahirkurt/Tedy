import json
import os
from pathlib import Path

from src.assistant_core import AssistantRuntime, GeminiClient


class _DummyOllama:
    def __init__(self):
        self.chat_model = "dummy-chat"
        self.embed_model = "dummy-embed"

    def available_models(self):
        return [self.chat_model, self.embed_model]

    def embed(self, text: str):
        if not text.strip():
            return None
        # Deterministic tiny embedding for tests
        s = sum(ord(c) for c in text[:64])
        return [float((s % 97) / 97.0), float(len(text) % 13), 1.0]

    def chat(self, messages, temperature=0.2):
        last_user = ""
        for m in messages[::-1]:
            if m.get("role") == "user":
                last_user = m.get("content", "")
                break
        return f"TEST_ANSWER::{last_user[:40]}"


def _write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _prepare_project(tmp_path: Path):
    # Only output/ is indexed (whitelist approach)
    _write(
        tmp_path / "output" / "scraped_data.json",
        json.dumps(
            {
                "scraped_at": "2026-03-14T17:00:00",
                "odevlerim": {
                    "homework": {
                        "rows": [
                            {
                                "Ders Adı": "Matematik",
                                "Ödev Başlığı": "Kesirler Tekrar",
                                "Ödev Son Teslim Tarihi": "16.03.2026 18:00",
                                "Ödev Durumu": "Değerlendirilmemiş",
                            }
                        ]
                    }
                },
                "gelisim_raporu": {"grades": []},
                "takvim": [],
                "ders_programi": [],
            },
            ensure_ascii=False,
        ),
    )
    _write(
        tmp_path / "output" / "enrichment_cache.json",
        json.dumps(
            {"hw:mat:1": {"type": "odev", "note": "Kesirler çalışma notu"}},
            ensure_ascii=False,
        ),
    )
    _write(
        tmp_path / "output" / "eba_textbooks_uploaded.json",
        json.dumps(
            {"mat_7": {"title": "Matematik 7", "course": "Matematik"}},
            ensure_ascii=False,
        ),
    )
    # These should NOT be indexed
    _write(tmp_path / "src" / "module.py", "def add(a,b): return a+b\n")
    _write(tmp_path / "docs" / "note.md", "# Dev docs\n")
    _write(tmp_path / "CLAUDE.md", "# Project instructions\n")


def test_reindex_creates_manifest_and_chunks(tmp_path: Path, monkeypatch):
    _prepare_project(tmp_path)
    monkeypatch.setenv("ASSISTANT_ENABLE_EMBEDDINGS", "0")

    runtime = AssistantRuntime(tmp_path)

    stats = runtime.reindex(incremental=False)

    assert stats["files_indexed"] >= 3
    assert stats["chunks_indexed"] >= 3
    assert runtime.config.manifest_path.exists()
    assert runtime.config.chunks_path.exists()
    # Verify no project docs/src/root files indexed
    manifest = json.loads(
        runtime.config.manifest_path.read_text())
    for path in manifest:
        assert not path.startswith("src/"), \
            f"Source file indexed: {path}"
        assert not path.startswith("docs/"), \
            f"Docs file indexed: {path}"
        assert path != "CLAUDE.md", \
            "CLAUDE.md should not be indexed"


def test_incremental_reindex_detects_changes(tmp_path: Path, monkeypatch):
    _prepare_project(tmp_path)
    monkeypatch.setenv("ASSISTANT_ENABLE_EMBEDDINGS", "0")

    runtime = AssistantRuntime(tmp_path)

    first = runtime.reindex(incremental=False)
    assert first["files_indexed"] == 3

    # Modify an indexed output file
    _write(
        tmp_path / "output" / "enrichment_cache.json",
        json.dumps(
            {"hw:mat:1": {"type": "odev", "note": "Güncellenmiş not"}},
            ensure_ascii=False,
        ),
    )

    second = runtime.reindex(incremental=True)
    assert second["changed_files"] >= 1
    assert second["unchanged_files"] >= 1


def test_chat_returns_citations_and_answer(tmp_path: Path, monkeypatch):
    _prepare_project(tmp_path)
    monkeypatch.setenv("ASSISTANT_ENABLE_EMBEDDINGS", "0")

    runtime = AssistantRuntime(tmp_path)
    # runtime.router IS runtime.gemini (same object) — patching a fresh object
    # onto runtime.router leaves runtime.gemini untouched and chat() would hit
    # the real Gemini API over the network. Patch the method on the real
    # object instead.
    monkeypatch.setattr(
        runtime.gemini, "chat_with_tools",
        lambda *a, **k: ToolLoopResult(
            text="TEST_ANSWER::kesir çalışması [S1]",
            citations=[{"kind": "ogrenci", "label": "scraped_data.json",
                        "locator": {}, "snippet": "s", "confidence": 0.9}]))

    runtime.reindex(incremental=False)

    response = runtime.chat(
        messages=[
            {"role": "user",
             "content": "Matematik ödevim ne?"}
        ],
        session_id="test-session",
        context_filters={},
    )

    assert "answer" in response
    assert response["answer"].startswith(
        "TEST_ANSWER::")
    assert isinstance(response.get("citations"), list)
    assert len(response["citations"]) == 1
    assert response.get("intent") in {
        "data_query", "general",
        "expert_guidance", "study_plan"}


def test_chat_marks_limited_confidence_when_retrieval_weak(tmp_path: Path, monkeypatch):
    """The flag's source changed in Task 6: chat() no longer runs retrieval
    ahead of the prompt, so "weak retrieval" no longer exists as a signal.
    Its honest replacement is an empty *resolved* citation list — the model
    answered but nothing it said was backed by a tool-returned source. The
    flag must still fire; only the mechanism producing an empty citation
    list changed (here: the model emits no [S] markers at all)."""
    _prepare_project(tmp_path)
    monkeypatch.setenv("ASSISTANT_ENABLE_EMBEDDINGS", "0")

    runtime = AssistantRuntime(tmp_path)
    monkeypatch.setattr(
        runtime.gemini, "chat_with_tools",
        lambda *a, **k: ToolLoopResult(text="TEST", citations=[]))

    runtime.reindex(incremental=False)

    response = runtime.chat(
        messages=[{"role": "user",
                   "content": "no_source_probe_abcdef"}],
        session_id="test-limited",
        context_filters={},
    )

    assert "warning:limited_confidence" in response.get("safety_flags", [])
    assert response.get("citations") == []


def test_gemini_only_no_ollama(tmp_path: Path):
    """Verify Ollama is fully removed."""
    runtime = AssistantRuntime(tmp_path)
    assert not hasattr(runtime, "ollama")
    assert not hasattr(runtime.config, "ollama_base_url")
    assert [model["id"] for model in runtime.models()] == GeminiClient.FAST_MODELS
    assert all(model["owned_by"] == "google" for model in runtime.models())


def test_openai_completion_uses_gemini_default_model(tmp_path: Path):
    """When chat() reports no explicit model, the OpenAI-compatible endpoint
    must still report a real, current model — not a stale/retired literal."""
    runtime = AssistantRuntime(tmp_path)
    runtime.chat = lambda **_kwargs: {"answer": "ok"}

    completion = runtime.openai_chat_completion({
        "messages": [{"role": "user", "content": "test"}],
    })

    assert completion["model"] == GeminiClient.FAST_MODELS[0]


from src.assistant_core import AssistantRuntime, ToolLoopResult


DEEP_INTENTS = ("study_plan", "grade_analysis", "exam_solving")


def test_deep_tier_is_chosen_by_intent_not_by_the_model():
    """Tier selection is deterministic so cost and latency stay predictable."""
    for intent in DEEP_INTENTS:
        assert AssistantRuntime._tier_for(intent, force_deep=False) == "deep"
    assert AssistantRuntime._tier_for("qa", force_deep=False) == "fast"


def test_explicit_user_request_forces_the_deep_tier():
    assert AssistantRuntime._tier_for("qa", force_deep=True) == "deep"


def test_chat_reports_degraded_servers_in_meta(tmp_path, monkeypatch):
    (tmp_path / "output").mkdir()
    rt = AssistantRuntime(tmp_path)

    monkeypatch.setattr(rt.registry, "degraded", lambda: ["maarif-mufredat"])
    monkeypatch.setattr(rt.registry, "declarations", lambda: [])
    monkeypatch.setattr(
        rt.gemini, "chat_with_tools",
        lambda *a, **k: ToolLoopResult(text="cevap", citations=[]))

    out = rt.chat([{"role": "user", "content": "merhaba"}])
    assert out["meta"]["degraded"] == ["maarif-mufredat"]


def test_empty_model_output_becomes_an_honest_message_not_a_blank_reply(tmp_path, monkeypatch):
    """A budget-exhausted loop can return text="" — measured in Task 4. The
    reader must never receive a blank answer."""
    (tmp_path / "output").mkdir()
    rt = AssistantRuntime(tmp_path)

    monkeypatch.setattr(rt.registry, "declarations", lambda: [])
    monkeypatch.setattr(rt.registry, "degraded", lambda: [])
    monkeypatch.setattr(rt.gemini, "chat_with_tools",
                        lambda *a, **k: ToolLoopResult(text="   ", budget_exhausted=True))

    out = rt.chat([{"role": "user", "content": "kesir nedir"}])
    assert out["answer"].strip()
    assert "kesir nedir" in out["answer"]


def test_chat_meta_carries_the_tool_ledger_and_dropped_count(tmp_path, monkeypatch):
    (tmp_path / "output").mkdir()
    rt = AssistantRuntime(tmp_path)

    monkeypatch.setattr(rt.registry, "declarations", lambda: [])
    monkeypatch.setattr(rt.registry, "degraded", lambda: [])
    monkeypatch.setattr(rt.gemini, "chat_with_tools", lambda *a, **k: ToolLoopResult(
        text="Kaynaklı [S1] ve uydurma [S5].",
        citations=[{"kind": "mufredat", "label": "MEB", "locator": {},
                    "snippet": "s", "confidence": 0.9}],
        tool_calls=[{"name": "kazanim_ara", "ms": 40, "ok": True}]))

    out = rt.chat([{"role": "user", "content": "kesir"}])

    assert out["meta"]["dropped_citations"] == 1
    assert out["meta"]["tool_calls"][0]["name"] == "kazanim_ara"
    assert "[S5]" not in out["answer"]
    assert len(out["citations"]) == 1


def test_system_prompt_forbids_inventing_locators():
    p = AssistantRuntime.SYSTEM_PROMPT
    assert "uydurma" in p.lower()
    for token in ("kazanım kodu", "sayfa numarası"):
        assert token in p.lower()


def test_system_prompt_names_the_authority_split():
    p = AssistantRuntime.SYSTEM_PROMPT
    assert "ogrenci_verisi_ara" in p
    assert "kazanim_ara" in p


def test_system_prompt_keeps_the_citation_contract():
    assert "[S1]" in AssistantRuntime.SYSTEM_PROMPT


def test_system_prompt_no_longer_bans_citation_markers():
    """The old prompt ended with 'never finish with a Kaynaklar list' AND the
    frontend stripped markers — together they made citation impossible."""
    assert "Kaynaklar:' listesiyle bitirme" not in AssistantRuntime.SYSTEM_PROMPT


def test_system_prompt_calls_both_tools_for_hybrid_questions():
    """A question like 'ödevimdeki kesir konusunu anlat' touches both Işık's
    own record and a curriculum topic — the prompt must say to call both
    tools in sequence, not silently pick one bucket."""
    p = AssistantRuntime.SYSTEM_PROMPT
    assert "iki aracı da çağır" in p
    assert "kaynakların karışmaması demektir, aracın tekliği değil" in p


def test_system_prompt_allows_general_knowledge_without_fabricated_citation():
    """Out-of-scope general-knowledge questions must be answerable, but the
    answer must not carry a [S] marker implying it came from a tool."""
    p = AssistantRuntime.SYSTEM_PROMPT
    assert "genel bilgi sorulursa yanıtla" in p
    assert "o cümleye [S] atıfı ekleme" in p
