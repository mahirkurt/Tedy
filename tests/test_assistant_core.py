import json
import os
from pathlib import Path

from src.assistant_core import AssistantRuntime


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
    # Mock the chat router to avoid network calls
    runtime.router = type(
        "MockRouter", (), {
            "chat": lambda self, msgs, **kw: (
                "TEST_ANSWER::" + msgs[-1].get(
                    "content", "")[:40]),
            "last_provider": "mock",
            "last_model_used": "mock-model",
        })()

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
    assert response.get("intent") in {
        "data_query", "general",
        "expert_guidance", "study_plan"}


def test_chat_marks_limited_confidence_when_retrieval_weak(tmp_path: Path, monkeypatch):
    _prepare_project(tmp_path)
    monkeypatch.setenv("ASSISTANT_ENABLE_EMBEDDINGS", "0")

    runtime = AssistantRuntime(tmp_path)
    runtime.router = type(
        "MockRouter", (), {
            "chat": lambda self, msgs, **kw: "TEST",
            "last_model_used": "mock",
        })()

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
    assert [model["id"] for model in runtime.models()] == [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
    ]
    assert all(model["owned_by"] == "google" for model in runtime.models())


def test_openai_completion_uses_gemini_default_model(tmp_path: Path):
    runtime = AssistantRuntime(tmp_path)
    runtime.chat = lambda **_kwargs: {"answer": "ok"}

    completion = runtime.openai_chat_completion({
        "messages": [{"role": "user", "content": "test"}],
    })

    assert completion["model"] == "gemini-2.5-flash"
