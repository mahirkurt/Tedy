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
    _write(tmp_path / "src" / "module.py", "def add(a,b):\n    return a+b\n")
    _write(tmp_path / "docs" / "note.md", "# Matematik\nKesirler ve oran konusu")
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
                            }
                        ]
                    }
                },
                "gelisim_raporu": {"grades": []},
            },
            ensure_ascii=False,
        ),
    )


def test_reindex_creates_manifest_and_chunks(tmp_path: Path, monkeypatch):
    _prepare_project(tmp_path)
    monkeypatch.setenv("ASSISTANT_ENABLE_EMBEDDINGS", "0")

    runtime = AssistantRuntime(tmp_path)
    runtime.ollama = _DummyOllama()
    runtime.indexer.ollama = runtime.ollama

    stats = runtime.reindex(incremental=False)

    assert stats["files_indexed"] >= 3
    assert stats["chunks_indexed"] >= 3
    assert runtime.config.manifest_path.exists()
    assert runtime.config.chunks_path.exists()


def test_incremental_reindex_detects_changes(tmp_path: Path, monkeypatch):
    _prepare_project(tmp_path)
    monkeypatch.setenv("ASSISTANT_ENABLE_EMBEDDINGS", "0")

    runtime = AssistantRuntime(tmp_path)
    runtime.ollama = _DummyOllama()
    runtime.indexer.ollama = runtime.ollama

    first = runtime.reindex(incremental=False)
    assert first["files_indexed"] >= 3

    # Modify one file
    _write(tmp_path / "docs" / "note.md", "# Matematik\nKesirler, oran ve problem çözümü")

    second = runtime.reindex(incremental=True)
    assert second["changed_files"] >= 1
    assert second["unchanged_files"] >= 1


def test_chat_returns_citations_and_answer(tmp_path: Path, monkeypatch):
    _prepare_project(tmp_path)
    monkeypatch.setenv("ASSISTANT_ENABLE_EMBEDDINGS", "0")

    runtime = AssistantRuntime(tmp_path)
    runtime.ollama = _DummyOllama()
    runtime.indexer.ollama = runtime.ollama

    runtime.reindex(incremental=False)

    response = runtime.chat(
        messages=[
            {"role": "user", "content": "Matematik ödevim için ne önerirsin?"}
        ],
        session_id="test-session",
        context_filters={},
    )

    assert "answer" in response
    assert response["answer"].startswith("TEST_ANSWER::")
    assert isinstance(response.get("citations"), list)
    assert response.get("intent") in {"data_query", "general", "expert_guidance", "study_plan"}


def test_chat_marks_limited_confidence_when_retrieval_weak(tmp_path: Path, monkeypatch):
    _prepare_project(tmp_path)
    monkeypatch.setenv("ASSISTANT_ENABLE_EMBEDDINGS", "0")

    runtime = AssistantRuntime(tmp_path)
    runtime.ollama = _DummyOllama()
    runtime.indexer.ollama = runtime.ollama

    runtime.reindex(incremental=False)

    response = runtime.chat(
        messages=[{"role": "user", "content": "no_source_probe_abcdef"}],
        session_id="test-limited",
        context_filters={},
    )

    assert "warning:limited_confidence" in response.get("safety_flags", [])
    assert response.get("citations") == []


def test_default_embed_model_is_mxbai(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("ASSISTANT_EMBED_MODEL", raising=False)
    runtime = AssistantRuntime(tmp_path)
    assert runtime.config.ollama_embed_model == "mxbai-embed-large"
