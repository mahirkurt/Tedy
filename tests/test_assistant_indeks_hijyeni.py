"""Task 1 — BM25 index hygiene, security exclusions and search quality.

Covers docs/superpowers/sdd/2026-09-25-asistan-tam-baglam/task-1-brief.md items 1-6:
security/noise exclusions, output-before-content discovery order with an honest
dropped-file report at the chunk cap, the PDF page cap env override, Turkish-aware
tokenization shared by index and query, full chunk text handed to the model (vs. the
260-char citation snippet), and eba/sebitv grade-label extraction.

Fixtures hold only invented content — never real personal data.
"""
import json
import logging
import sys
import types

from src.assistant_core import (
    AssistantConfig,
    AssistantRuntime,
    FileAdapters,
    HybridRetriever,
    INDEX_FORMAT_VERSION,
    turkce_kucult_katla,
)
from src.assistant_tools import McpRegistry


def _write(root, rel, text="veri"):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _project(tmp_path, monkeypatch, **env):
    for key in ("ASSISTANT_MAX_CHUNKS", "ASSISTANT_PDF_MAX_PAGES", "ASSISTANT_INCLUDE_DIRS",
                "ASSISTANT_EXCLUDED_DIRS", "ASSISTANT_EXCLUDED_FILES",
                "MUFREDAT_MCP_API_KEY", "EGITIM_KAYNAK_MCP_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return tmp_path


def _reg(rows):
    return McpRegistry(clients={}, local_search=lambda q, k: rows)


# ── 1. Dışlananlar (brief item 1) ──────────────────────────────────────────

FORBIDDEN_FILES = (
    "output/sync.log",
    "output/sync.log.1",
    "output/portal_cookies.json",
    "output/session_cookie_backup.json",
    "output/portal_architecture.json",
    "output/book_progress.json",
    "output/homework_first_seen.json",
    "output/run_sync.pid",
    "output/crontab",
    "output/crontab.bak",
    "output/.sync_zamanlama.json",
    # Fix round 1 (controller, Görev 6): raw per-platform progress JSON,
    # readable only through `platform_ilerlemesi` (Görev 3) now — the audit
    # named these "raw JSON in the index" as noise (§1).
    "output/englishcentral_progress.json",
    "output/achieve3000_progress.json",
)


def test_excluded_files_are_never_discovered(tmp_path, monkeypatch):
    _project(tmp_path, monkeypatch)
    _write(tmp_path, "output/notlar.txt", "gerçek okul verisi")
    for rel in FORBIDDEN_FILES:
        _write(tmp_path, rel)
    runtime = AssistantRuntime(tmp_path)

    found = {p.relative_to(tmp_path).as_posix() for p in runtime.indexer._discover_files()}

    assert "output/notlar.txt" in found
    assert found & set(FORBIDDEN_FILES) == set()


FORBIDDEN_DIRS = (
    "output/saat_dilimi_gocu_yedek/eski.json",
    "output/crontab_yedek/eski_crontab",
    "output/mebi_quiz_discovery/quiz.json",
    "output/archive/2025-2026/manifest.json",
    "content/pedagoji/woolfolk.md",
    "content/eba_backup/eski.pdf",       # generic 'backup' substring, non-literal dir
    "output/2026_yedek_kopya/eski.json",  # generic 'yedek' substring, non-literal dir
)


def test_excluded_and_backup_dirs_are_never_discovered(tmp_path, monkeypatch):
    _project(tmp_path, monkeypatch)
    _write(tmp_path, "output/notlar.txt", "gerçek okul verisi")
    for rel in FORBIDDEN_DIRS:
        _write(tmp_path, rel)
    runtime = AssistantRuntime(tmp_path)

    found = {p.relative_to(tmp_path).as_posix() for p in runtime.indexer._discover_files()}

    assert "output/notlar.txt" in found
    assert found & set(FORBIDDEN_DIRS) == set()


# ── 2. Keşif sırası + tavanda düşen dosyalar ────────────────────────────────

def test_output_discovered_before_content_and_cap_drops_are_reported(tmp_path, monkeypatch, caplog):
    _project(tmp_path, monkeypatch, ASSISTANT_MAX_CHUNKS="2")
    _write(tmp_path, "output/aaa_first.txt", "kısa metin bir")
    _write(tmp_path, "output/zzz_second.txt", "kısa metin iki")
    _write(tmp_path, "content/aaa_third.txt", "kısa metin uc")
    _write(tmp_path, "content/bbb_fourth.txt", "kısa metin dort")
    runtime = AssistantRuntime(tmp_path)

    with caplog.at_level(logging.WARNING):
        stats = runtime.reindex(incremental=False)

    chunks = json.loads(runtime.config.chunks_path.read_text(encoding="utf-8"))
    indexed_paths = {c["path"] for c in chunks}
    # Both output/ files survive the cap — they are discovered first.
    assert "output/aaa_first.txt" in indexed_paths
    assert "output/zzz_second.txt" in indexed_paths
    assert not any(p.startswith("content/") for p in indexed_paths)

    # No silent drop: the summary and the log both name the dropped files.
    assert stats["dusen_dosyalar"]
    assert all(p.startswith("content/") for p in stats["dusen_dosyalar"])
    assert any(
        "content/aaa_third.txt" in rec.message or "content/bbb_fourth.txt" in rec.message
        for rec in caplog.records
    )


# ── 3. PDF sayfa sınırı ─────────────────────────────────────────────────────

class _FakePage:
    def __init__(self, i):
        self.i = i

    def extract_text(self):
        return f"sayfa {self.i}"


class _FakePdfReader:
    def __init__(self, path):
        self.pages = [_FakePage(i) for i in range(500)]


def _install_fake_pypdf(monkeypatch):
    fake = types.ModuleType("pypdf")
    fake.PdfReader = _FakePdfReader
    monkeypatch.setitem(sys.modules, "pypdf", fake)


def test_pdf_max_pages_defaults_to_400(monkeypatch, tmp_path):
    monkeypatch.delenv("ASSISTANT_PDF_MAX_PAGES", raising=False)
    config = AssistantConfig.from_project_root(tmp_path)
    assert config.pdf_max_pages == 400


def test_pdf_max_pages_env_override_bounds_extraction(tmp_path, monkeypatch):
    _install_fake_pypdf(monkeypatch)
    monkeypatch.setenv("ASSISTANT_PDF_MAX_PAGES", "7")

    config = AssistantConfig.from_project_root(tmp_path)
    assert config.pdf_max_pages == 7

    adapters = FileAdapters(config)
    pdf_path = tmp_path / "kitap.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")
    text = adapters._extract_pdf_text(pdf_path)

    assert text.count("sayfa ") == 7


# ── 4. Türkçe belirteçleme ───────────────────────────────────────────────────

def test_turkce_kucult_katla_folds_capital_i_variants_and_diacritics():
    assert turkce_kucult_katla("İngilizce") == turkce_kucult_katla("ingilizce") == "ingilizce"
    assert turkce_kucult_katla("Isı") == turkce_kucult_katla("ısı") == turkce_kucult_katla("isi") == "isi"
    assert turkce_kucult_katla("Öğretmen") == "ogretmen"


def test_index_and_query_share_the_turkish_aware_tokenizer():
    chunks = [
        {"chunk_id": "c1", "path": "output/a.txt", "chunk_index": 0,
         "text": "İngilizce ödevi bu hafta var.", "confidence": 0.9},
        {"chunk_id": "c2", "path": "output/b.txt", "chunk_index": 0,
         "text": "Isı ve sıcaklık konusu anlatılıyor.", "confidence": 0.9},
    ]
    retriever = HybridRetriever(chunks=chunks)

    assert any(h["chunk_id"] == "c1" for h in retriever.search("ingilizce", top_k=5))
    assert any(h["chunk_id"] == "c2" for h in retriever.search("isi", top_k=5))


# ── 5. Tam metin ─────────────────────────────────────────────────────────────

def test_local_tool_returns_full_chunk_text_not_just_the_260_char_snippet():
    full = "Kesirler konusu tekrar çalışması. " * 60  # well over 1200 chars
    snippet = full[:257] + "..."
    rows = [{"path": "output/notlar.txt", "chunk_index": 0, "confidence": 0.9,
             "snippet": snippet, "text": full}]
    reg = _reg(rows)

    out = reg.dispatch("ogrenci_verisi_ara", {"query": "kesir"})

    assert out.ok
    assert len(out.text) > 260
    assert len(out.text) <= 1200
    assert out.citations[0]["snippet"] == snippet
    assert len(out.citations[0]["snippet"]) <= 260


def test_local_tool_body_is_capped_at_3900_chars_total():
    full = "x" * 1200
    rows = [{"path": f"output/n{i}.txt", "chunk_index": 0, "confidence": 0.9,
             "snippet": "s", "text": full} for i in range(8)]
    reg = _reg(rows)

    out = reg.dispatch("ogrenci_verisi_ara", {"query": "kesir"})

    assert out.ok
    assert len(out.text) <= 3900


# ── 6. Sınıf etiketi ─────────────────────────────────────────────────────────

def test_class_label_extracted_from_eba_filename():
    rows = [{"path": "content/eba/Matematik 6 1. Kitap.pdf", "chunk_index": 0,
             "confidence": 0.9, "snippet": "s", "text": "içerik"}]
    reg = _reg(rows)

    out = reg.dispatch("ogrenci_verisi_ara", {"query": "matematik"})

    assert out.citations[0]["label"] == "6. sınıf · Matematik 6 1. Kitap"


def test_class_label_extracted_from_sebitv_filename():
    rows = [{"path": "content/sebitv/Fen Bilimleri 7 Konu Ozeti.pdf", "chunk_index": 0,
             "confidence": 0.9, "snippet": "s", "text": "içerik"}]
    reg = _reg(rows)

    out = reg.dispatch("ogrenci_verisi_ara", {"query": "fen"})

    assert out.citations[0]["label"] == "7. sınıf · Fen Bilimleri 7 Konu Ozeti"


def test_class_label_unchanged_when_grade_cannot_be_extracted():
    rows = [{"path": "content/eba/Fen Bilimleri.pdf", "chunk_index": 0,
             "confidence": 0.9, "snippet": "s", "text": "içerik"}]
    reg = _reg(rows)

    out = reg.dispatch("ogrenci_verisi_ara", {"query": "fen"})

    assert out.citations[0]["label"] == "Fen Bilimleri.pdf"


def test_class_label_only_applies_to_eba_and_sebitv_paths():
    rows = [{"path": "output/6.json", "chunk_index": 0, "confidence": 0.9,
             "snippet": "s", "text": "içerik"}]
    reg = _reg(rows)

    out = reg.dispatch("ogrenci_verisi_ara", {"query": "x"})

    assert out.citations[0]["label"] == "6.json"


# ── Persisted index format version ──────────────────────────────────────────

def test_index_format_version_bump_forces_a_full_rebuild(tmp_path, monkeypatch):
    _project(tmp_path, monkeypatch)
    _write(tmp_path, "output/notlar.txt", "kesirler tekrar")
    runtime = AssistantRuntime(tmp_path)

    first = runtime.reindex(incremental=False)
    assert first["files_indexed"] == 1
    manifest = json.loads(runtime.config.manifest_path.read_text(encoding="utf-8"))
    assert manifest["version"] == INDEX_FORMAT_VERSION

    # Simulate a pre-migration index: same file, same sha256, older version.
    manifest["version"] = 1
    runtime.config.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    second = runtime.reindex(incremental=True)

    assert second["changed_files"] == 1
    assert second["unchanged_files"] == 0
    manifest2 = json.loads(runtime.config.manifest_path.read_text(encoding="utf-8"))
    assert manifest2["version"] == INDEX_FORMAT_VERSION


# ── Fix round 1 ──────────────────────────────────────────────────────────────

def test_max_chunks_default_is_30000(tmp_path, monkeypatch):
    """Brief item 2, verbatim: "Tavan varsayılanı 30.000 parça."."""
    monkeypatch.delenv("ASSISTANT_MAX_CHUNKS", raising=False)
    config = AssistantConfig.from_project_root(tmp_path)
    assert config.max_chunks == 30000


# A single file whose own chunk_text() output is several chunks — long enough
# that a small cap falls strictly inside it, not at a file boundary.
_UZUN_PARA = "Bu cümle test içeriği doldurmak için tekrar tekrar yazılır. " * 8
_UZUN_METIN = "\n\n".join([_UZUN_PARA] * 12)


def test_file_truncated_mid_chunking_is_not_recorded_as_fully_indexed(tmp_path, monkeypatch):
    """A file the cap would only partially chunk must never get a manifest
    entry claiming it is complete: with sha256 unchanged, an incremental run
    would reuse that partial slice forever and no more of the file would ever
    be indexed. It must instead be treated exactly like any other cut-off
    file — absent from the manifest, named in dusen_dosyalar, logged — so the
    next reindex (which sees no old record for it) reprocesses it in full."""
    _project(tmp_path, monkeypatch, ASSISTANT_MAX_CHUNKS="3")
    _write(tmp_path, "output/uzun.txt", _UZUN_METIN)
    runtime = AssistantRuntime(tmp_path)

    # This file alone produces more than 3 chunks (verified below via the
    # uncapped rerun), so the cap cuts it strictly mid-file.
    stats = runtime.reindex(incremental=False)

    manifest = json.loads(runtime.config.manifest_path.read_text(encoding="utf-8"))
    chunks = json.loads(runtime.config.chunks_path.read_text(encoding="utf-8"))

    assert "output/uzun.txt" not in manifest["files"]
    assert [c for c in chunks if c["path"] == "output/uzun.txt"] == []
    assert "output/uzun.txt" in stats["dusen_dosyalar"]

    # A later run with room enough must reprocess it in full — not skip it
    # forever because some prior sha256 "matches" a record that never existed.
    monkeypatch.delenv("ASSISTANT_MAX_CHUNKS", raising=False)
    runtime2 = AssistantRuntime(tmp_path)
    second = runtime2.reindex(incremental=True)

    manifest2 = json.loads(runtime2.config.manifest_path.read_text(encoding="utf-8"))
    chunks2 = json.loads(runtime2.config.chunks_path.read_text(encoding="utf-8"))
    file_chunks2 = [c for c in chunks2 if c["path"] == "output/uzun.txt"]

    assert "output/uzun.txt" in manifest2["files"]
    assert len(file_chunks2) > 3  # proves the cap really did cut it short above
    assert second["changed_files"] >= 1  # reprocessed, not silently "unchanged"


def test_file_truncated_mid_chunking_logs_a_warning(tmp_path, monkeypatch, caplog):
    _project(tmp_path, monkeypatch, ASSISTANT_MAX_CHUNKS="3")
    _write(tmp_path, "output/uzun.txt", _UZUN_METIN)
    runtime = AssistantRuntime(tmp_path)

    with caplog.at_level(logging.WARNING):
        runtime.reindex(incremental=False)

    assert any("output/uzun.txt" in rec.message for rec in caplog.records)
