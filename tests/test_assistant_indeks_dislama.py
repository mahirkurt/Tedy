"""The generic assistant file index must not ingest edupedia catalog, drafts, runs, progress or ted-mcp stores."""
import json

from src.assistant_core import AssistantRuntime

MARKER = "gizliilerlemeisareti"
FORBIDDEN = (
    "output/modules/index.json",
    "output/modules/fen5-su/v1/notlar.txt",
    "output/modules/.lock",
    "output/edupedia_drafts/0123456789abcdef/taslak.json",
    "output/edupedia_runs/abcdef012345/run.json",
    "output/edupedia_runs/abcdef012345/sayfalar/112.md",
    "output/module_progress.json",
    "output/module_progress.json.lock",
    "output/edupedia_media_ledger.json",
    "output/ted_mcp_oauth.sqlite3",
    "output/ted_mcp_oauth.sqlite3-wal",
)


def _write(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _project(tmp_path, monkeypatch):
    for env in ("MUFREDAT_MCP_API_KEY", "EGITIM_KAYNAK_MCP_API_KEY", "ASSISTANT_EXCLUDED_DIRS",
                "ASSISTANT_EXCLUDED_FILES", "ASSISTANT_INCLUDE_DIRS"):
        monkeypatch.delenv(env, raising=False)
    _write(tmp_path, "output/notlar.txt", "okul verisi kesirler tekrar")
    for rel in FORBIDDEN:
        _write(tmp_path, rel, f"{MARKER} {rel}")
    return AssistantRuntime(tmp_path)


def test_discovery_keeps_school_data_and_skips_edupedia_and_progress(tmp_path, monkeypatch):
    runtime = _project(tmp_path, monkeypatch)
    found = {p.relative_to(tmp_path).as_posix() for p in runtime.indexer._discover_files()}
    assert "output/notlar.txt" in found
    assert sorted(found & set(FORBIDDEN)) == []


def test_full_reindex_puts_no_forbidden_text_into_chunks(tmp_path, monkeypatch):
    runtime = _project(tmp_path, monkeypatch)
    runtime.reindex(incremental=False)
    chunks = json.loads(runtime.config.chunks_path.read_text(encoding="utf-8"))
    assert any(c["path"] == "output/notlar.txt" for c in chunks)
    assert [c["path"] for c in chunks if MARKER in c["text"]] == []


def test_incremental_reindex_purges_chunks_indexed_before_the_exclusion(tmp_path, monkeypatch):
    runtime = _project(tmp_path, monkeypatch)
    runtime.reindex(incremental=False)
    stale = {"chunk_id": "eski", "path": "output/module_progress.json", "chunk_index": 0,
             "text": f"{MARKER} eski", "source_kind": "text", "confidence": 0.9, "warnings": [],
             "mtime": 0, "size": 1, "sha256": "x"}
    chunks = json.loads(runtime.config.chunks_path.read_text(encoding="utf-8"))
    runtime.config.chunks_path.write_text(json.dumps(chunks + [stale]), encoding="utf-8")
    manifest = json.loads(runtime.config.manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["output/module_progress.json"] = {"sha256": "x", "size": 1, "mtime": 0, "ext": ".json"}
    runtime.config.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    stats = runtime.reindex(incremental=True)

    after = json.loads(runtime.config.chunks_path.read_text(encoding="utf-8"))
    assert stats["deleted_files"] >= 1
    assert [c["path"] for c in after if MARKER in c["text"]] == []


def test_local_search_cannot_surface_progress_text(tmp_path, monkeypatch):
    runtime = _project(tmp_path, monkeypatch)
    runtime.reindex(incremental=False)
    assert runtime._local_search("kesirler", 8)  # the index is live, so the next absence means something
    assert runtime._local_search(MARKER, 8) == []


def test_env_overrides_cannot_remove_the_exclusions(tmp_path, monkeypatch):
    runtime = _project(tmp_path, monkeypatch)
    monkeypatch.setenv("ASSISTANT_INCLUDE_DIRS", "output")
    monkeypatch.setenv("ASSISTANT_EXCLUDED_DIRS", "")
    monkeypatch.setenv("ASSISTANT_EXCLUDED_FILES", "")
    overridden = AssistantRuntime(tmp_path)
    found = {p.relative_to(tmp_path).as_posix() for p in overridden.indexer._discover_files()}
    assert "output/notlar.txt" in found and sorted(found & set(FORBIDDEN)) == []
    assert runtime.config.excluded_dirs <= overridden.config.excluded_dirs
