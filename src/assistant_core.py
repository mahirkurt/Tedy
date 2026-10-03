"""Local pedagogical assistant runtime for TEDY.

This module provides:
- Incremental repository indexing (full repo + output artefacts)
- File adapters (json/html/md/txt/code/pdf/image)
- Hybrid retrieval over indexed course content
- Safety policy for educational psychology answers
- Chat + study plan generation
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import queue
import re
import subprocess
import threading
import time
import fnmatch
import functools
import zipfile
from xml.etree import ElementTree
from xml.parsers import expat as _expat
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests as http_requests

from src import assistant_skills, claude_api
from src.hafta_secici import guncel_hafta
from src.json_utils import atomic_json_dump


logger = logging.getLogger(__name__)


def _utcnow_naive() -> datetime:
    """Return a naive UTC datetime without using deprecated utcnow()."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


TEXT_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md", ".txt",
    ".csv", ".yml", ".yaml", ".toml", ".ini", ".env", ".scss", ".css",
    ".html", ".htm", ".xml", ".sql", ".sh", ".rst", ".log", ".svg",
}
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif"}
DOCX_EXTENSIONS = {".docx"}
# word/document.xml is read whole; a real homework sheet is kilobytes. The cap
# keeps a hostile or broken archive (a zip bomb) from ballooning in memory.
DOCX_XML_SINIRI = 50 * 1024 * 1024
_WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
EMBED_TARGET_EXTENSIONS = {".md", ".txt", ".json", ".csv", ".html", ".htm", ".pdf"}


class _DocxDtdSinyali(Exception):
    """Internal signal only: expat's own DOCTYPE/entity handler fired."""


def _docx_declares_dtd_or_entity(veri: bytes) -> bool:
    """Whether `veri` declares a DTD or an entity, decided by expat's own
    declaration handlers rather than a byte-level scan.

    Fix round 2 (coordinator-verified): a byte scan cannot be made
    encoding-proof. A UTF-16-encoded document.xml puts a NUL byte between
    every ASCII letter, so the literal bytes "<!DOCTYPE"/"<!ENTITY" never
    occur in the raw byte string even though the decoded document declares
    both — and ElementTree.fromstring, which does decode it, still expands
    the entity. expat is the same underlying parser ElementTree uses, so it
    decodes `veri` exactly the same way; asking it directly, instead of
    grepping the undecoded bytes, is not fooled by any encoding it
    understands."""
    parser = _expat.ParserCreate()

    def _isaretle(*_args, **_kwargs):
        raise _DocxDtdSinyali()

    parser.StartDoctypeDeclHandler = _isaretle
    parser.EntityDeclHandler = _isaretle
    try:
        parser.Parse(veri, True)
    except _DocxDtdSinyali:
        return True
    except _expat.ExpatError:
        # Any other parse failure here is not this gate's business: the
        # ElementTree.fromstring parse below raises its own error (caught
        # by _extract_docx_text's broad except), or this document was
        # never going to declare anything anyway.
        return False
    return False

# Whitelist: scrape data + downloaded educational content
DEFAULT_INCLUDE_DIRS = {"output", "content"}

# Discovery order (task-1 brief §2): output/ first, then content/, so a chunk-cap
# overrun drops the far larger content/ textbook corpus before it ever touches
# Işık's own scraped data. Any include dir not named here (a custom
# ASSISTANT_INCLUDE_DIRS entry) is scanned last, alphabetically.
_DISCOVERY_PRIORITY = ("output", "content")

# Portal attachments (src/portal_ekleri.py): only the text TEDY extracted at
# download time, content/portal-ekleri/<id>.txt, is indexed. The binaries
# would be re-extracted here outside the sync's attachment budget (a 112 MB
# PDF, measured 2026-09-28); the .meta.json sidecars and .parca/ part files
# are bookkeeping. The citation label comes from the sidecar
# (assistant_tools.McpRegistry._yerel_etiket), never from this path.
PORTAL_EKLERI_DIZINI = "content/portal-ekleri"

DEFAULT_EXCLUDED_DIRS = {
    "__pycache__",
    "assistant_index",
    # Görev 5's separate content/pedagoji index directory. Without this, the main
    # indexer's own "output/" walk discovers it as ordinary output content (its
    # manifest/chunks/embeddings/meta JSON) the moment it exists on disk — the
    # `full == idx_dir` guard in _discover_files only ever knows about *this*
    # config's own index_dir, not a sibling one built from a second AssistantConfig.
    "output/assistant_index_aile",
    # edupedia (spec §4.2): ted-mcp's catalog, immutable drafts and run pages. Published modules
    # reach the model only through modul_ara (src/assistant_modules.py); run pages carry
    # third-party textbook and OER text that must not enter a prompt without kaynak_verisi.
    "output/modules",
    "output/edupedia_drafts",
    "output/edupedia_runs",
    # Migration/rollover backups and a sealed prior-year archive: historical
    # copies, not current school data (docs/superpowers/notes/2026-09-25-asistan-veri-denetimi.md §1-2).
    "output/saat_dilimi_gocu_yedek",
    "output/crontab_yedek",
    "output/mebi_quiz_discovery",
    "output/archive",
    # Adult-facing pedagogy notes — Görev 5 indexes this separately.
    "content/pedagoji",
}

DEFAULT_EXCLUDED_FILE_PATTERNS = {
    "*.png",
    "*.html",
    "*.jsonl",
    "*.log",
    "*.log.*",
    "sync.log",
    "classroom_sync.json",
    "homework_student_done.json",
    "homework_first_seen.json",
    "health.json",
    "photo_homework.json",
    "private_lessons.json",
    # Per-person module progress (spec §6.4), lock sidecars, the media ledger and the ted-mcp
    # OAuth store: none of it is school data, and raw progress must never reach a prompt.
    "module_progress.json",
    # Portal session cookies, whatever their exact name, and the portal's own
    # scraped page-structure map — session state and scraper internals, not
    # school content (audit §2c).
    "*cookie*",
    "portal_architecture.json",
    # Final review, finding 5: same class as portal_architecture.json —
    # scraper-internal page structure map and a Google Sheets id, not school
    # content.
    "page_structure.json",
    "sheets_id.txt",
    # Per-person Tedy Books reading position (emails, reading location).
    "book_progress.json",
    # Process/cron bookkeeping: pid files, crontab dumps, the sync scheduler state.
    "*.pid",
    "crontab*",
    ".sync_zamanlama.json",
    "*.lock",
    "edupedia_media_ledger.json",
    "ted_mcp_oauth.sqlite3*",
    # Discovery/metadata JSONs — too noisy for BM25
    "*_discovered.json",
    "sebitv_*.json",
    "sebit_*.json",
    "eba_*.json",
    "a3k_*.json",
    "ec_*.json",
    "mebi_*.json",
    # Raw platform-progress JSON: readable only through `platform_ilerlemesi`
    # (Görev 3), which reads these two files directly. Named "noise" in the
    # audit's BM25 findings before that tool existed (§1); fix round 1
    # (controller) closes the gap by excluding them from the shared index
    # too, so the model no longer sees the raw per-dialogue JSON alongside
    # the readable summary.
    "englishcentral_progress.json",
    "achieve3000_progress.json",
    # The attachment tracker: URLs (teachers' SharePoint paths), statuses and
    # hashes — bookkeeping, readable through the attachments themselves.
    # atomic_json_dump writes path + ".tmp" and renames; a killed run leaves
    # portal_ekleri.json.tmp, and an unknown extension is read as text.
    "portal_ekleri.json",
    "portal_ekleri.json.*",
}

# Bumped whenever a change to discovery, exclusion or tokenization would leave
# a stale on-disk index silently wrong (task-1 brief §4: index and query must
# tokenize identically, which only holds once every persisted chunk was
# produced under the current rules). AssistantIndexer.reindex() treats a
# manifest whose version does not match this constant as fully stale and
# rebuilds from scratch, regardless of the incremental flag or matching sha256s.
INDEX_FORMAT_VERSION = 2

# Files with structured student data — get semantic chunking
_SEMANTIC_JSON_FILES = {
    "scraped_data.json",
    "enrichment_cache.json",
    "eba_textbooks_uploaded.json",
    "mebi_videos_uploaded.json",
    "sebitv_uploaded.json",
    "sebitv_interactive_uploaded.json",
    "exam_content_map.json",
}


class _StreamAbandoned(Exception):
    """Raised inside a chat_events() worker when the consumer has gone away.

    Cancellation is cooperative and can only be checked where chat_events()
    has a hook: the dispatch wrapper (tool boundaries) and, since the answer
    is streamed, every piece of text. A tool call already in flight still runs
    to completion, and a model call stops at its next piece of text.
    chat() re-raises it rather than treating it as a model failure.
    """


@dataclass
class AssistantConfig:
    project_root: Path
    output_dir: Path
    index_dir: Path
    manifest_path: Path
    chunks_path: Path
    embeddings_path: Path
    meta_path: Path
    metrics_path: Path
    enable_ocr: bool
    max_file_size_mb: int
    max_chunks: int
    pdf_max_pages: int
    pdf_timeout: int
    chunk_size: int
    chunk_overlap: int
    retrieval_k: int
    stale_after_minutes: int
    include_dirs: set[str]
    excluded_dirs: set[str]
    excluded_file_patterns: set[str]

    @classmethod
    def from_project_root(cls, project_root: str | os.PathLike[str],
                          index_subdir: str = "assistant_index",
                          include_dirs: set[str] | None = None,
                          excluded_dirs: set[str] | None = None) -> "AssistantConfig":
        """Build a config rooted at `project_root`.

        `index_subdir`/`include_dirs`/`excluded_dirs` let a caller build a
        second, isolated index over a different slice of the tree (Görev 5:
        content/pedagoji, aile_kaynak_ara) without touching the main one —
        same retriever and indexer classes, a different AssistantConfig.
        Passing `include_dirs`/`excluded_dirs` explicitly bypasses the
        ASSISTANT_INCLUDE_DIRS/ASSISTANT_EXCLUDED_DIRS env overrides (those
        are the main index's operator knobs); the file-level safety patterns
        below always apply, so no secret pattern is ever skipped for a
        second index.
        """
        root = Path(project_root).resolve()
        output_dir = root / "output"
        index_dir = output_dir / index_subdir
        index_dir.mkdir(parents=True, exist_ok=True)

        max_file_size_mb = int(os.environ.get(
            "ASSISTANT_MAX_FILE_SIZE_MB", "250"))
        max_chunks = int(os.environ.get(
            "ASSISTANT_MAX_CHUNKS", "30000"))
        # 120 lost 8 of the 10 EBA books (131-222 pages each; audit §2b) —
        # but this cap only ever applies when pypdf is installed. Production
        # has no pypdf (final review, finding 3): _extract_pdf_text always
        # falls back to pdftotext there, which reads every page uncapped,
        # bounded only by ASSISTANT_PDF_TIMEOUT below.
        pdf_max_pages = int(os.environ.get(
            "ASSISTANT_PDF_MAX_PAGES", "400"))
        # The pdftotext fallback's timeout (final review, finding 1). A hard
        # 40s used to be baked in; measured at load 7.8 real textbooks took
        # 38.6s/34.1s/29.9s — close enough to trip it, and a timeout used to
        # be indistinguishable from "this PDF genuinely has no text layer"
        # (see PdfExtractionError). 180s covers the measured worst case with
        # headroom.
        pdf_timeout = int(os.environ.get(
            "ASSISTANT_PDF_TIMEOUT", "180"))

        if include_dirs is not None:
            includes = set(include_dirs)
        else:
            includes = set(DEFAULT_INCLUDE_DIRS)
            custom_includes = os.environ.get(
                "ASSISTANT_INCLUDE_DIRS", "").strip()
            if custom_includes:
                includes = {x.strip() for x in
                            custom_includes.split(",") if x.strip()}
        if excluded_dirs is not None:
            excluded = set(excluded_dirs)
        else:
            excluded = set(DEFAULT_EXCLUDED_DIRS)
            custom_excluded = os.environ.get(
                "ASSISTANT_EXCLUDED_DIRS", "").strip()
            if custom_excluded:
                excluded.update(
                    x.strip() for x in
                    custom_excluded.split(",") if x.strip())
        excluded_files = set(DEFAULT_EXCLUDED_FILE_PATTERNS)
        custom_excluded_files = os.environ.get(
            "ASSISTANT_EXCLUDED_FILES", "").strip()
        if custom_excluded_files:
            excluded_files.update(
                x.strip() for x in
                custom_excluded_files.split(",") if x.strip())

        return cls(
            project_root=root,
            output_dir=output_dir,
            index_dir=index_dir,
            manifest_path=index_dir / "manifest.json",
            chunks_path=index_dir / "chunks.json",
            embeddings_path=index_dir / "embeddings.json",
            meta_path=index_dir / "meta.json",
            metrics_path=output_dir / "assistant_metrics.jsonl",
            enable_ocr=os.environ.get(
                "ASSISTANT_ENABLE_OCR", "0") == "1",
            max_file_size_mb=max_file_size_mb,
            max_chunks=max_chunks,
            pdf_max_pages=pdf_max_pages,
            pdf_timeout=pdf_timeout,
            chunk_size=int(os.environ.get("ASSISTANT_CHUNK_SIZE", "1400")),
            chunk_overlap=int(os.environ.get("ASSISTANT_CHUNK_OVERLAP", "220")),
            retrieval_k=int(os.environ.get("ASSISTANT_RETRIEVAL_K", "8")),
            stale_after_minutes=int(os.environ.get(
                "ASSISTANT_STALE_AFTER_MINUTES", "90")),
            include_dirs=includes,
            excluded_dirs=excluded,
            excluded_file_patterns=excluded_files,
        )


@dataclass
class ToolLoopResult:
    text: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    budget_exhausted: bool = False
    # Summed over every request of one answer: input, output, cache reads and
    # writes. Cost was never logged under Gemini; this is what makes it visible.
    usage: dict[str, int] = field(default_factory=dict)
    # Reader-stream events tools left behind (ToolOutcome.olay), in call order:
    # mod_oner's mode_suggestion. /chat, which has no stream, reads them here.
    olaylar: list[dict[str, Any]] = field(default_factory=list)


class ClaudeClient:
    """The assistant's model: Claude on the Anthropic Messages API.

    Replaced the Gemini chain on 2026-09-24. The Gemini API terms say "You must
    be 18 years of age or older" and forbid services "likely to be accessed by
    individuals under the age of 18"; this assistant is used by a 12-year-old.
    Anthropic permits organisations serving minors with safeguards (see
    docs/frontend-design-principles.md and the AI label on every answer).

    One model at two depths: `effort` (medium for a normal question, high for
    "Daha derine in" and the deep intents) replaces the old fast/deep model
    chain. Tool results go back as native tool_result blocks tied to their call
    id instead of text pasted into one flattened prompt. No sampling
    parameters: Sonnet 5 rejects them and SDK 1.x no longer has them.
    """

    DEFAULT_MODEL = claude_api.VARSAYILAN_MODEL
    # medium, not low, for a normal question. Measured 2026-09-24 on a live
    # curriculum question: low answered in ~10 s from memory, no tool called,
    # no citation — the fabrication ban unenforced; medium called mufredat_ara
    # and cited it, in ~17 s. The seconds are paid for with streaming.
    EFFORT = {"fast": "medium", "deep": "high"}
    # Thinking counts toward max_tokens; a low cap truncates mid-thought. The
    # length of an answer is the prompt's job, not this ceiling's.
    MAX_TOKENS = 16000
    # Per request. The tool loop makes at most max_rounds + 1 requests inside
    # one gunicorn worker (timeout 360 s), so one call must not own it.
    TIMEOUT_S = 100.0

    def __init__(self, api_key: str = "", model: str = "", client: Any = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "").strip()
        self.model = (model or os.environ.get("ASSISTANT_CLAUDE_MODEL", "").strip()
                      or self.DEFAULT_MODEL)
        self._client: Any = client
        self.last_model_used = ""

    @property
    def available(self) -> bool:
        return bool(self.api_key) or self._client is not None

    def _get_client(self) -> Any:
        if self._client is None:
            import anthropic  # lazy: tests and tools that never chat don't need it
            self._client = anthropic.Anthropic(
                api_key=self.api_key, timeout=self.TIMEOUT_S, max_retries=1,
                **claude_api.basliklar())
        return self._client

    @staticmethod
    def _split(messages: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
        """System blocks apart, one per system message; turns as the Messages API wants them.

        The API rejects a conversation that opens on the assistant and any
        empty text block. The runtime keeps the last three turns of history,
        which can start mid-dialogue, so leading assistant turns are dropped.

        One block per system message, not one joined text: a teacher mode adds
        its own block after the base prompt, and each is cached on its own
        (spec §1 "Modele bağlama").
        """
        system = [str(m.get("content", "")) for m in messages
                  if m.get("role") == "system" and str(m.get("content", "")).strip()]
        turns: list[dict[str, Any]] = []
        for m in messages:
            role = m.get("role", "user")
            if role == "system":
                continue
            content = str(m.get("content", "")).strip()
            if not content:
                continue
            role = "assistant" if role == "assistant" else "user"
            if not turns and role == "assistant":
                continue
            turns.append({"role": role, "content": content})
        return system, turns

    def _request(self, system: str | list[str], turns: list[dict[str, Any]], tier: str,
                 usage: dict[str, int], tools: list[dict[str, Any]] | None = None,
                 tool_choice: dict[str, Any] | None = None,
                 on_delta: Callable[[str], None] | None = None) -> Any:
        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.MAX_TOKENS,
            "messages": turns,
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": self.EFFORT.get(tier, "medium")},
        }
        bloklar = [b for b in ([system] if isinstance(system, str) else system) if b]
        if bloklar:
            # Render order is tools -> system -> messages, so a breakpoint on
            # the system blocks caches the tool list and the prompt together:
            # every round of a tool loop re-sends exactly that prefix. One
            # breakpoint per block: the base prompt (byte-identical in every
            # mode) and, in a teacher mode, that teacher's block after it.
            params["system"] = [{"type": "text", "text": b,
                                 "cache_control": {"type": "ephemeral"}} for b in bloklar]
        if tools:
            params["tools"] = tools
        if tool_choice:
            params["tool_choice"] = tool_choice
        if on_delta is None:
            resp = self._get_client().messages.create(**params)
        else:
            # Streamed so the reader watches the answer being written: at
            # medium effort a normal question takes ~17 s, and for this reader
            # a blank wait that long is where attention leaves. The final
            # message is the same object create() would have returned.
            with self._get_client().messages.stream(**params) as akis:
                for parca in akis.text_stream:
                    if parca:
                        on_delta(parca)
                resp = akis.get_final_message()
        self.last_model_used = getattr(resp, "model", "") or self.model
        u = getattr(resp, "usage", None)
        for key in ("input_tokens", "output_tokens",
                    "cache_read_input_tokens", "cache_creation_input_tokens"):
            usage[key] = usage.get(key, 0) + int(getattr(u, key, 0) or 0)
        if getattr(resp, "stop_reason", "") == "refusal":
            # Not an empty answer to show as if it were one: the runtime turns
            # this into its honest fallback.
            raise RuntimeError("claude_refusal")
        return resp

    @staticmethod
    def _text(resp: Any) -> str:
        return "".join(getattr(b, "text", "") for b in (getattr(resp, "content", None) or [])
                       if getattr(b, "type", "") == "text").strip()

    def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        declarations: list[dict[str, Any]],
        dispatch: Any,
        tier: str = "fast",
        max_rounds: int = 4,
        on_delta: Callable[[str], None] | None = None,
        on_reset: Callable[[], None] | None = None,
        max_calls: int = 8,
    ) -> ToolLoopResult:
        """Run the model until it answers, dispatching tools it asks for.

        With `on_delta` every request is streamed and its text handed over as
        it arrives. Text a round writes before calling a tool is not part of
        the answer (the answer is the last round's text), so `on_reset` is
        called when such a round ends — the reader drops what was shown.

        Two budgets are hard stops: a model that keeps calling tools would
        otherwise hold a worker open indefinitely. `max_rounds` counts model
        turns that call tools — two tools asked for at once are one round;
        until 2026-09-25 it counted calls, so a model working in parallel ran
        out at four and its fifth call never happened. `max_calls` caps the
        calls themselves and is checked before each dispatch: a call past it
        is never run but still answered, so the model knows what did not
        happen (the API requires a result for every call anyway). Once either
        is spent the model is asked once more with tool_choice none — tools
        withdrawn, tool list kept so the cached prefix survives — and told in
        words to answer from what it has, because withdrawing the tools alone
        was measured to produce a thinking block and no text.
        """
        from src.assistant_tools import OLAY_ARACLARI, ToolOutcome

        if not self.available:
            raise RuntimeError("anthropic_no_api_key")

        system, turns = self._split(messages)
        out = ToolLoopResult()
        tools = [{
            "name": d["name"],
            "description": d.get("description", ""),
            "input_schema": d.get("parameters") or {"type": "object", "properties": {}},
        } for d in declarations]

        if max_rounds <= 0 or not tools:
            out.text = self._text(self._request(system, turns, tier, out.usage,
                                                on_delta=on_delta))
            return out

        kept_text = ""  # text an earlier event-only round wrote, carried into the final answer
        for _round in range(max_rounds):
            round_on_delta = on_delta
            if on_delta is not None and kept_text:
                # This round continues text a round already put on the stream
                # (kept_text is non-empty going in) — `_birlestir` puts a
                # blank line between kept_text and what follows in the final
                # joined answer, but the stream itself had no such break
                # before this: the draft ran the two straight together
                # ("…bakayım.Oran…"). Backend-only, cosmetic (review round 3,
                # finding 4): one leading "\n\n" delta before this round's
                # first non-empty chunk, so the draft matches the final text.
                round_on_delta = self._ayracli_delta(on_delta)
            resp = self._request(system, turns, tier, out.usage, tools=tools,
                                 on_delta=round_on_delta)
            uses = [b for b in (resp.content or []) if getattr(b, "type", "") == "tool_use"]
            round_text = self._text(resp)
            if not uses:
                out.text = self._birlestir(kept_text, round_text)
                return out
            # A round whose only tool calls are event-only (mod_oner) may carry
            # real answer text: the prompt now invites the model to call
            # mod_oner "ilk içerik aracınla birlikte ya da tam cevapla
            # birlikte", so a bare lead-in ("Önce müfredata bakayım.") is
            # expected too, not just a finished answer. Either way this text is
            # kept rather than thrown away by on_reset, and the loop keeps
            # going so a lead-in gets its follow-up round (review round 2,
            # finding NB1) — a genuinely complete answer simply gets an empty
            # follow-up round merged onto it, unchanged.
            son_tur = bool(round_text) and all(
                getattr(use, "name", "") in OLAY_ARACLARI for use in uses)
            if son_tur:
                kept_text = self._birlestir(kept_text, round_text)
            elif round_text:
                # A real tool call reasserts ordinary reset semantics for THIS
                # round's text; any text kept from an earlier event-only round
                # is discarded with it rather than left as an unlabelled prefix
                # ahead of a retry the model may frame completely differently
                # — the simpler of the two correct options the review offered
                # (see the fix report). Cleared whether or not on_reset is
                # given: /chat and /v1 pass on_reset=None (nothing to stream a
                # reset to), but kept_text must still be dropped there too, or
                # those endpoints answer differently from /stream (review
                # round 3, finding 2).
                if on_reset is not None:
                    on_reset()
                kept_text = ""

            # Back exactly as received: thinking blocks are signed and must not
            # be edited, and the tool_result ids must match these tool_use ids.
            turns.append({"role": "assistant", "content": resp.content})
            results: list[dict[str, Any]] = []
            for use in uses:
                if len(out.tool_calls) >= max_calls:
                    out.budget_exhausted = True
                    results.append({"type": "tool_result", "tool_use_id": use.id,
                                    "is_error": True,
                                    "content": "Çalıştırılmadı — tur bütçesi doldu."})
                    continue

                raw = use.input
                if isinstance(raw, dict):
                    args, dispatchable = dict(raw), True
                elif not raw:
                    # None / {}: an ordinary zero-argument call, not malformed.
                    args, dispatchable = {}, True
                else:
                    # Model-supplied and outside our tested contracts: a truthy
                    # non-mapping is unusable. Never coerce it and run a call
                    # the model did not actually make.
                    args, dispatchable = {}, False

                if dispatchable:
                    started = time.perf_counter()
                    outcome = dispatch(use.name, args)
                    elapsed = int((time.perf_counter() - started) * 1000)
                else:
                    elapsed = 0
                    outcome = ToolOutcome(
                        ok=False,
                        error=f"Model geçersiz argüman gönderdi (sözlük bekleniyor): {raw!r}")

                out.tool_calls.append({"name": use.name, "ms": elapsed, "ok": bool(outcome.ok)})
                if outcome.ok and outcome.olay and not any(
                        o.get("event") == outcome.olay.get("event") for o in out.olaylar):
                    # First suggestion wins: a model that calls mod_oner twice in
                    # one answer (it is told not to, but nothing enforced it)
                    # must not leave two competing "geçelim mi?" buttons behind.
                    out.olaylar.append(dict(outcome.olay))
                if son_tur:
                    if outcome.ok:
                        # The model already knows mod_oner ran (it just called
                        # it); what it needs is confirmation that this round's
                        # own text already reached the reader, so it neither
                        # repeats itself nor stalls waiting for a "result" to
                        # react to.
                        body = f"Öneri iletildi. {self.MOD_ONER_TUR_NOTU}"
                    else:
                        # mod_oner itself failed (a bad ogretmen argument, say)
                        # but the round's text was kept regardless — it was
                        # already added to kept_text before this dispatch loop
                        # ran, unconditionally on son_tur, not on the call
                        # succeeding. Without this the model saw only "HATA:
                        # …" and, not knowing its text had already been shown,
                        # repeated it while retrying the call (review round 3,
                        # finding 3).
                        body = f"HATA: {outcome.error}\n\n{self.MOD_ONER_TUR_NOTU}"
                elif outcome.ok:
                    first = len(out.citations) + 1
                    out.citations.extend(outcome.citations)
                    # The numbers the model sees and the ones
                    # _finalize_citations resolves come from the same counter
                    # (it renumbers only afterwards, in reading order);
                    # otherwise the right sentence cites the wrong source and it
                    # looks verified in the panel.
                    marks = "\n".join(f"[S{first + j}] {c.get('label', '')}"
                                      for j, c in enumerate(outcome.citations))
                    body = f"{marks}\n{outcome.text}" if marks else outcome.text
                else:
                    # Verbatim: the message names the offending field, so the
                    # model can usually fix its own call next round.
                    body = f"HATA: {outcome.error}"
                results.append({"type": "tool_result", "tool_use_id": use.id,
                                "is_error": not outcome.ok,
                                "content": self._sonuc_icerigi(
                                    body, outcome.images if outcome.ok else None)})
            turns.append({"role": "user", "content": results})

            if out.budget_exhausted or len(out.tool_calls) >= max_calls \
                    or _round == max_rounds - 1:
                if son_tur:
                    # The round that just hit a budget boundary (the last
                    # round, or a mod_oner call that itself reached max_calls)
                    # was event-only-with-text — kept_text already holds a
                    # complete answer. Sending SON_TUR_NOTU on top of the
                    # tool_result's own MOD_ONER_TUR_NOTU asked the model to
                    # both "say nothing, your text was shown" and "answer now"
                    # in the same turn, producing a duplicated or wasted
                    # re-ask. There is nothing left to ask for: return the
                    # kept text directly, with no further request, and do not
                    # count a complete answer as exhausted unless a call was
                    # genuinely dropped this round (out.budget_exhausted was
                    # already set True by the max_calls skip above, if so;
                    # review round 3, finding 1).
                    out.text = kept_text
                    return out
                out.budget_exhausted = True
                # After the tool results, in the same user turn: the API wants
                # every tool_result first.
                results.append({"type": "text", "text": self.SON_TUR_NOTU})
                out.text = ""
                # P7b: this re-ask continues kept_text from an earlier
                # event-only round exactly as an ordinary round does — the
                # same "\n\n" separator wrapping applies, or the streamed
                # draft glues the continuation onto kept_text with no break
                # while the final joined text (_birlestir, below) has one.
                son_tur_on_delta = on_delta
                if on_delta is not None and kept_text:
                    son_tur_on_delta = self._ayracli_delta(on_delta)
                for _ in range(2):
                    final = self._request(system, turns, tier, out.usage, tools=tools,
                                          tool_choice={"type": "none"}, on_delta=son_tur_on_delta)
                    out.text = self._text(final)
                    if out.text:
                        break
                out.text = self._birlestir(kept_text, out.text)
                return out

        out.text = self._birlestir(kept_text, out.text)
        return out

    # A tool_result carries at most this many images, and none whose base64
    # exceeds GORSEL_SINIRI characters: get_figure's are ≤ ~110 KB (≈150 K
    # base64), so the cap only ever trips on something that is not a textbook
    # figure — and an image block counts against the request's size limit.
    EN_COK_GORSEL = 2
    GORSEL_SINIRI = 1_500_000

    # Final review, finding 4: `ogrenci_verisi_ara`/`kitap_ara`/`aile_kaynak_ara`
    # size their own body to ~3,900 chars, but the `[S#] label` marks
    # `chat_with_tools` prefixes onto it are not counted against that budget —
    # with >=8 citations the marks alone add well over 100 chars, and a plain
    # `[:4000]` used to cut the tail of the last hit's text with no visible
    # sign. Any actual cut now leaves this marker instead.
    KESME_ISARETI = "…[kesildi]"
    TOOL_RESULT_SINIRI = 4000

    @classmethod
    def _sonuc_icerigi(cls, body: str | None,
                       images: list[dict[str, Any]] | None) -> str | list[dict[str, Any]]:
        """A tool_result's content: the text as before, or — when the tool
        returned images (figur_getir) — a list of a text block and up to two
        image blocks, so the model sees the figure it is asked to explain.
        An image left out is named in the text; a silent drop would let the
        model describe a picture it never saw.

        The 4,000-char budget is shared between the body (marks + tool text)
        and any image-overflow notes: notes are reserved first (they are
        short and load-bearing — an image the model was not actually sent
        must always be named), then the body is truncated to what remains,
        with a visible marker if it did not already fit — never a silent
        `[:4000]` that could land inside the last citation's text."""
        raw = (body or "").strip()

        bloklar: list[dict[str, Any]] = []
        notlar: list[str] = []
        if images:
            from src.assistant_tools import GORSEL_BICIMLERI

            for g in images:
                data = str(g.get("data") or "")
                mime = str(g.get("mimeType") or "")
                if len(bloklar) >= cls.EN_COK_GORSEL:
                    notlar.append("(bir görsel daha var; en çok iki görsel gönderilir)")
                elif len(data) > cls.GORSEL_SINIRI:
                    notlar.append("(görsel çok büyük; gönderilmedi)")
                elif mime not in GORSEL_BICIMLERI or not data:
                    notlar.append("(görsel biçimi desteklenmiyor; gönderilmedi)")
                else:
                    bloklar.append({"type": "image", "source": {
                        "type": "base64", "media_type": mime, "data": data}})

        ek = ("\n" + "\n".join(dict.fromkeys(notlar))) if notlar else ""
        limit = max(cls.TOOL_RESULT_SINIRI - len(ek), 0)
        if len(raw) > limit:
            cut_at = max(limit - len(cls.KESME_ISARETI), 0)
            metin = raw[:cut_at] + cls.KESME_ISARETI
        else:
            metin = raw
        metin = (metin or "(sonuç boş)") + ek

        if not images:
            return metin
        return [{"type": "text", "text": metin}, *bloklar]

    SON_TUR_NOTU = ("Araç bütçesi doldu; yeni araç çağıramazsın. Topladığın sonuçlarla "
                    "cevabı şimdi yaz. Bulamadığın bir şey varsa bulunamadığını açıkça söyle.")

    # Told to the model in the tool_result of an event-only round (mod_oner):
    # its lead-in or answer already reached the reader (chat_with_tools kept
    # it rather than resetting it), so it should continue from there instead
    # of repeating itself or waiting for a "result" that has nothing to add.
    # Split in two (final-fix item P7a): "Öneri iletildi." is true only when
    # mod_oner itself succeeded — a FAILED call must not claim the suggestion
    # reached the reader, only that the round's own text did.
    MOD_ONER_TUR_NOTU = ("Bu turda yazdığın metin okura gösterildi; tekrarlama. "
                        "Cevabın tamamsa hiçbir şey yazma; eksikse kaldığın yerden devam et.")

    @staticmethod
    def _birlestir(onceki: str, sonraki: str) -> str:
        """Join two answer fragments with a blank line; either may be empty.

        Carries a lead-in an event-only round wrote (mod_oner) into the final
        answer instead of losing it — the reader already saw it stream in, so
        it becomes the start of the answer, not a discarded draft (review
        round 2, finding NB1).
        """
        onceki, sonraki = onceki.strip(), sonraki.strip()
        if not onceki:
            return sonraki
        if not sonraki:
            return onceki
        return f"{onceki}\n\n{sonraki}"

    @staticmethod
    def _ayracli_delta(on_delta: Callable[[str], None]) -> Callable[[str], None]:
        """Wrap on_delta so the round's first non-empty chunk is preceded by
        one "\n\n" delta — used only for a round that continues kept_text, so
        the streamed draft gets the same blank-line break `_birlestir` puts in
        the final joined answer (review round 3, finding 4; backend-only, the
        UI is unchanged).

        A whitespace-only chunk before the first real content is dropped
        outright (not forwarded) rather than becoming visible text stuck
        right after the separator, and that first real chunk is itself
        lstripped — otherwise a model that streams a leading space ("Oran"
        arriving as " " then "Oran…") would leave a visible gap ("\n\n
        Oran…") that `_birlestir`'s equivalent join never has, since
        `_birlestir` strips both fragments before joining them (final-fix
        item P7c)."""
        yazildi = False

        def sarici(parca: str) -> None:
            nonlocal yazildi
            if not yazildi:
                if not parca.strip():
                    return  # whitespace-only chunk before real content: dropped
                on_delta("\n\n")
                yazildi = True
                on_delta(parca.lstrip())
                return
            on_delta(parca)
        return sarici


HybridChatRouter = None  # Removed — Gemini-only


# ── Semantic JSON → readable text ──────────────────────────

def _guncel_ogretim_yili_dosyadan(klasor: Path) -> str | None:
    """The school year TEDY believes it is in (`academic_year.json`'s
    `year`), read from the same directory as `scraped_data.json`. None when
    unknown or unreadable — an unknown year must label nothing "old"
    (`assistant_tools.onceki_yil_raporu_mu`'s own rule). Mirrors
    `dashboard_api._guncel_ogretim_yili`, which reads through Flask's own
    `_load_json`; this one has no Flask app to read through."""
    try:
        with (klasor / "academic_year.json").open("r", encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError):
        return None
    return veri.get("year") if isinstance(veri, dict) else None


def _semantic_json_text(path: Path, basename: str) -> str:
    """Convert known student-data JSON files into
    human-readable, search-friendly text blocks."""
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return ""
    if not isinstance(data, (dict, list)):
        return ""

    if basename == "scraped_data.json":
        return _fmt_scraped_data(data, _guncel_ogretim_yili_dosyadan(path.parent))
    if basename == "enrichment_cache.json":
        return _fmt_enrichment(data)
    if basename in ("eba_textbooks_uploaded.json",
                     "mebi_videos_uploaded.json",
                     "sebitv_uploaded.json",
                     "sebitv_interactive_uploaded.json"):
        return _fmt_uploaded_tracker(data, basename)
    if basename == "exam_content_map.json":
        return _fmt_exam_map(data)
    # Fallback: pretty-print
    return json.dumps(data, ensure_ascii=False, indent=1)


# The profile names no school; TEDY reads one school's portal.
_OKUL_ADI = "TED Rönesans Koleji"


def _tablo_satirlari(tablo: Any) -> list[str]:
    satirlar = tablo.get("rows") if isinstance(tablo, dict) else tablo
    out = []
    for r in satirlar or []:
        if isinstance(r, list):
            hucre = [str(c).strip() for c in r if str(c or "").strip()]
            if hucre:
                out.append(" | ".join(hucre))
    return out


def _fmt_scraped_data(data: dict, ogretim_yili: str | None = None) -> str:
    """scraped_data.json as the BM25 index reads it.

    Rewritten 2026-09-25 against the shapes on disk (audit §2a): the old
    formatter wanted the timetable as day -> slots and course content as
    lists, got `{headers, rows}` and `{tab_id, text, cards, …}`, and wrote
    only a week label and an empty heading — so neither ever reached the
    index. Records are separated by blank lines (the chunker's paragraph
    boundary) and each opens with what it is ("DERS PROGRAMI · Cuma",
    "DERS İÇERİĞİ · Matematik · 3. Hafta …"), so a hit names itself.
    The profile gives class, section and school only: no name, e-mail,
    national id, student number or the contact fields.

    `ogretim_yili` is the school year TEDY believes it is in
    (`output/academic_year.json`'s `year`, read by the caller since this
    function only ever sees `scraped_data.json`'s own content): when the
    gelişim report names an earlier year, the NOTLAR paragraph says so,
    exactly as `assistant_tools.notlar_metni` (the `notlar` tool) already
    does — before this it was the one of the three surfaces reading this
    report that stayed silent (final review, Minor 5)."""
    from src.assistant_tools import (_GUNLER, aciklama_metni, guncel_hafta_dersleri,
                                     gunun_dersleri, html_metne, icerik_ozeti,
                                     onceki_yil_raporu_mu, rapor_yili)
    from src.course_names import normalize_course
    from src.portal_susu import temiz_metin

    parts: list[str] = []

    # Profil
    profil = data.get("ogrenci_profili")
    if isinstance(profil, dict) and profil:
        alanlar = []
        sinif = str(profil.get("class_name") or "").strip()
        sube = str(profil.get("branch") or "").strip()
        if sinif:
            alanlar.append(f"Sınıf: {sinif}")
        if sube:
            alanlar.append(f"Şube: {sube}")
        alanlar.append(f"Okul: {str(profil.get('school') or '').strip() or _OKUL_ADI}")
        parts.append("ÖĞRENCİ PROFİLİ\n" + " · ".join(alanlar))

    # Ödevler
    hw_rows = (data.get("odevlerim", {})
               .get("homework", {})
               .get("rows", []))
    if hw_rows:
        satirlar = ["=== ÖDEVLER ==="]
        for r in hw_rows:
            if not isinstance(r, dict):
                continue
            ders = r.get("Ders Adı", "")
            baslik = r.get("Ödev Başlığı", "")
            tarih = r.get("Ödev Son Teslim Tarihi", "")
            durum = r.get("Ödev Durumu", "")
            desc = ""
            detail = r.get("detail")
            if isinstance(detail, dict):
                desc = temiz_metin(detail.get("description", ""))
            line = f"{ders} | {baslik}"
            if tarih:
                line += f" | Son teslim: {tarih}"
            if durum:
                line += f" | Durum: {durum}"
            ek_adlari = [" ".join(str(a.get("name") or "").split())
                         for a in (detail.get("attachments") or [] if isinstance(detail, dict) else [])
                         if isinstance(a, dict) and str(a.get("name") or "").strip()]
            if ek_adlari:
                line += " | Ekler: " + "; ".join(ek_adlari)
            if desc:
                line += f" | {desc[:200]}"
            satirlar.append(line)
        parts.append("\n".join(satirlar))

    # Ders programı: the current week (it repeats), one paragraph per day,
    # read through the dashboard's two-block parser. `guncel_hafta` is the
    # same "is_current, else the last one" resolver dashboard_api._guncel_hafta
    # and the unified calendar use (src/hafta_secici.py) — this paragraph
    # used to re-implement it slightly differently (final review, Minor 4).
    hafta = guncel_hafta(data.get("ders_programi") or [])
    guncel_etiket = str((hafta or {}).get("week_label") or "")
    rows = ((hafta or {}).get("schedule") or {}).get("rows") or []
    for gun in _GUNLER:
        dersler = gunun_dersleri(rows, gun)
        if dersler:
            parts.append(f"DERS PROGRAMI · {gun}" + (f" ({guncel_etiket})" if guncel_etiket else "")
                         + "\n" + "\n".join(
                             f"{gun} · {d['ders_no']}. ders {d['baslangic']}–{d['bitis']} {d['ders']}"
                             for d in dersler))

    # Takvim etkinlikleri, with their description (not when it only repeats
    # the title) and place.
    takvim = data.get("takvim", [])
    if isinstance(takvim, list) and takvim:
        satirlar = ["=== TAKVİM ==="]
        for ev in takvim:
            if not isinstance(ev, dict):
                continue
            t = ev.get("title", "")
            satir = f"{str(ev.get('start') or '')[:16]} | {t}"
            ek = ev.get("extendedProps") if isinstance(ev.get("extendedProps"), dict) else {}
            aciklama = aciklama_metni(ek.get("description"), t)
            if aciklama:
                satir += f" | {aciklama[:400]}"
            yer = html_metne(ek.get("location"))
            if yer:
                satir += f" | Yer: {yer}"
            satirlar.append(satir)
        parts.append("\n".join(satirlar))

    # Notlar ve kazanım düzeyleri
    gelisim = data.get("gelisim_raporu", {})
    gelisim = gelisim if isinstance(gelisim, dict) else {}
    semester = str(gelisim.get("semester") or "")
    grades = gelisim.get("grades", []) or []
    if grades:
        satirlar = ["=== NOTLAR ==="]
        if semester:
            satirlar.append(f"Dönem: {semester}")
        if onceki_yil_raporu_mu(semester, ogretim_yili):
            satirlar.append(f"ÖNCEKİ ÖĞRETİM YILI: portalın gelişim raporu {rapor_yili(semester)} "
                            f"yılını gösteriyor; şu an {ogretim_yili} öğretim yılı ve bu yıl için "
                            "not girilmemiş. Bu notları bu yılın notu gibi sunma.")
        for g in grades:
            if not isinstance(g, dict):
                continue
            ders = g.get("Ders", "")
            cols = []
            for k, v in g.items():
                if k != "Ders" and v and v != "-":
                    cols.append(f"{k}: {v}")
            if cols:
                satirlar.append(f"{ders} | {' | '.join(cols)}")
        parts.append("\n".join(satirlar))
    rubrikler = [r for r in (gelisim.get("rubrics") or []) if isinstance(r, dict)]
    if rubrikler:
        satirlar = ["=== KAZANIM DÜZEYLERİ ===" + (f" ({semester})" if semester else "")]
        for r in rubrikler:
            satirlar.append(" | ".join(str(r.get(k) or "").strip()
                                       for k in ("ders", "alan", "kazanim", "duzey")))
        parts.append("\n".join(satirlar))

    # Ders içerikleri: the open week first, then every other collected week,
    # one paragraph per course. The current label follows /api/content/weeks
    # (dashboard_api._icerik_haftalari): the week the timetable marks current.
    haftalar = data.get("ders_icerikleri_haftalar")
    haftalar = haftalar if isinstance(haftalar, dict) else {}
    if guncel_etiket not in haftalar:
        guncel_etiket = next(iter(haftalar), "") if not guncel_etiket else guncel_etiket

    def icerik_paragraflari(dersler: Any, etiket: str) -> None:
        for ad, kayit in (dersler.items() if isinstance(dersler, dict) else []):
            # One paragraph per course-week: a blank line inside would let
            # the chunker cut the record away from the heading that names it.
            ozet = re.sub(r"\n\s*\n", "\n", icerik_ozeti(kayit))
            if not ozet:
                continue
            kanon = normalize_course(str(ad)) or str(ad)
            adi = kanon if kanon == ad else f"{kanon} ({ad})"
            parts.append(f"DERS İÇERİĞİ · {adi}" + (f" · {etiket}" if etiket else "") + f"\n{ozet}")

    icerik_paragraflari(guncel_hafta_dersleri(data.get("ders_icerikleri"), haftalar.get(guncel_etiket)),
                        f"{guncel_etiket} (güncel hafta)" if guncel_etiket else "güncel hafta")
    for etiket, dersler in haftalar.items():
        if etiket != guncel_etiket:
            icerik_paragraflari(dersler, etiket)

    # ÖGEP and team work: `{headers, rows}` tables, keyed as the unified
    # calendar reads them.
    for bolum, anahtar, ad_alani, baslik in (
            ("ogep", "sessions", "ÖGEP (Öğrenci Gelişim Programı)", "ÖGEP"),
            ("takim_calismalari", "activities", "Academy+", "TAKIM ÇALIŞMALARI")):
        tablo = (data.get(bolum) or {}).get(anahtar) if isinstance(data.get(bolum), dict) else None
        satirlar_ham = tablo.get("rows") if isinstance(tablo, dict) else tablo
        satirlar = [f"=== {baslik} ==="]
        for r in satirlar_ham or []:
            if isinstance(r, dict):
                satirlar.append(" | ".join(str(r.get(k) or "").strip() for k in (
                    ad_alani, "Çalışma Başlangıç", "Çalışma Bitiş", "Katılım Durumu")))
        if len(satirlar) > 1:
            parts.append("\n".join(satirlar))

    # Duyurular
    duyuru = data.get("duyurular", {})
    items = (duyuru.get("announcements", [])
             if isinstance(duyuru, dict) else [])
    if items:
        satirlar = ["=== DUYURULAR ==="]
        for d in items:
            if isinstance(d, dict):
                title = d.get("title", d.get("başlık", ""))
                date = d.get("date", d.get("tarih", ""))
                satirlar.append(f"{date} | {title}")
        parts.append("\n".join(satirlar))

    # Portalın ek sayfaları: only those with something in them — an empty
    # page's `text` is whatever the portal rendered instead (measured: the
    # login form), exactly what /api/pages keeps off the dashboard.
    sayfalar = data.get("ek_sayfalar")
    for kayit in (sayfalar.values() if isinstance(sayfalar, dict) else []):
        if not isinstance(kayit, dict) or kayit.get("empty"):
            continue
        satirlar = [f"PORTAL SAYFASI · {str(kayit.get('title') or '').strip()}"]
        if str(kayit.get("text") or "").strip():
            satirlar.append(temiz_metin(kayit["text"]))
        for tablo in kayit.get("tables") or []:
            satirlar.extend(_tablo_satirlari(tablo))
        for secenek in kayit.get("options") or []:
            if isinstance(secenek, dict) and secenek.get("degerler"):
                satirlar.append("Seçenekler: " + ", ".join(map(str, secenek["degerler"])))
        if kayit.get("documents"):
            satirlar.append(f"Belge sayısı: {len(kayit['documents'])}")
        parts.append("\n".join(satirlar))

    return "\n\n".join(parts)


def _fmt_enrichment(data: dict) -> str:
    parts = ["=== AI ZENGİNLEŞTİRME NOTLARI ==="]
    for key, val in data.items():
        if not isinstance(val, dict):
            continue
        note_type = val.get("type", "")
        note = val.get("note", "")
        if note:
            parts.append(f"{note_type} | {key} | {note[:300]}")
    return "\n".join(parts)


def _fmt_uploaded_tracker(data: dict, basename: str) -> str:
    prefix = basename.replace("_uploaded.json", "").upper()
    parts = [f"=== {prefix} KAYNAKLAR ==="]
    for key, val in data.items():
        if isinstance(val, dict):
            title = val.get("title", val.get("name", key))
            course = val.get("course", "")
            line = f"{prefix}: {course} | {title}" if course \
                else f"{prefix}: {title}"
            parts.append(line)
        elif isinstance(val, str):
            parts.append(f"{prefix}: {key}")
    return "\n".join(parts)


def _fmt_exam_map(data: dict) -> str:
    parts = ["=== SINAV İÇERİK EŞLEŞTİRMELERİ ==="]
    for key, val in data.items():
        if isinstance(val, dict):
            summary = val.get("summary", "")
            parts.append(f"Sınav: {key} | {summary[:200]}")
    return "\n".join(parts)


class PdfExtractionError(Exception):
    """Raised by `FileAdapters._extract_pdf_text` when extraction genuinely
    failed or timed out — never for a PDF that ran cleanly and simply has no
    text layer (a scanned page). `extract()`/`reindex()` must not create a
    manifest entry for a file that raises this: it needs to be retried, not
    permanently recorded as "indexed, no text" (final review, finding 1)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class DocxExtractionError(Exception):
    """Raised by `FileAdapters._extract_docx_text(..., hata_bildir=True)` when
    the archive could not be read — "bozuk" (not a zip, no
    word/document.xml, malformed XML), "dtd" (a DTD or entity declaration,
    refused) or "sinir" (document.xml larger than the cap) — as opposed to a
    real document that simply has no text. The default call keeps returning
    "" for all of these, as the index has always relied on."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class FileAdapters:
    def __init__(self, config: AssistantConfig):
        self.config = config

    def extract(self, file_path: Path, rel_path: str) -> dict[str, Any]:
        ext = file_path.suffix.lower()

        size_bytes = file_path.stat().st_size
        max_bytes = self.config.max_file_size_mb * 1024 * 1024

        if size_bytes > max_bytes:
            return {
                "text": self._metadata_only_text(
                    rel_path, file_path,
                    reason="file_too_large"),
                "source_kind": "metadata",
                "confidence": 0.2,
                "warnings": ["too_large"],
            }

        # Semantic chunking for known student data files
        basename = file_path.name
        if basename in _SEMANTIC_JSON_FILES:
            text = _semantic_json_text(file_path, basename)
            if text:
                return {
                    "text": text,
                    "source_kind": "text",
                    "confidence": 0.95,
                    "warnings": [],
                }

        if ext in TEXT_EXTENSIONS:
            text = self._extract_text_like(file_path, ext)
            return {
                "text": text or self._metadata_only_text(rel_path, file_path, reason="empty_text"),
                "source_kind": "text" if text else "metadata",
                "confidence": 0.9 if text else 0.25,
                "warnings": [] if text else ["empty_text"],
            }

        if ext in PDF_EXTENSIONS:
            try:
                text = self._extract_pdf_text(file_path)
            except PdfExtractionError as exc:
                # Not "no text layer" — a timeout or a real extraction
                # failure. The caller (reindex()) must not persist a
                # manifest entry for this: it needs to be retried, and named
                # with its reason, not silently indexed as blank forever.
                return {
                    "text": "",
                    "source_kind": "metadata",
                    "confidence": 0.0,
                    "warnings": [f"pdf_extraction_{exc.reason}"],
                    "extraction_error": exc.reason,
                }
            return {
                "text": text or self._metadata_only_text(rel_path, file_path, reason="pdf_no_text"),
                "source_kind": "pdf" if text else "metadata",
                "confidence": 0.8 if text else 0.2,
                "warnings": [] if text else ["pdf_no_text"],
            }

        if ext in DOCX_EXTENSIONS:
            text = self._extract_docx_text(file_path)
            return {
                "text": text or self._metadata_only_text(rel_path, file_path, reason="docx_no_text"),
                "source_kind": "docx" if text else "metadata",
                "confidence": 0.8 if text else 0.2,
                "warnings": [] if text else ["docx_no_text"],
            }

        if ext in IMAGE_EXTENSIONS:
            text = self._extract_image_text(file_path)
            if text:
                return {
                    "text": text,
                    "source_kind": "image_ocr",
                    "confidence": 0.45,
                    "warnings": [],
                }
            return {
                "text": self._metadata_only_text(rel_path, file_path, reason="image_metadata_only"),
                "source_kind": "metadata",
                "confidence": 0.15,
                "warnings": ["image_metadata_only"],
            }

        # Unknown extension: try reading as text, else metadata only.
        text = self._extract_text_like(file_path, ext)
        if text:
            return {
                "text": text,
                "source_kind": "text",
                "confidence": 0.55,
                "warnings": ["unknown_extension_text_read"],
            }
        return {
            "text": self._metadata_only_text(rel_path, file_path, reason="binary_metadata_only"),
            "source_kind": "metadata",
            "confidence": 0.1,
            "warnings": ["binary_metadata_only"],
        }

    def _extract_text_like(self, file_path: Path, ext: str) -> str:
        # JSON: canonical pretty text gives stronger lexical recall.
        if ext == ".json":
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    payload = json.load(f)
                return json.dumps(payload, ensure_ascii=False, indent=2)
            except Exception:
                pass

        for enc in ("utf-8", "latin-1"):
            try:
                with file_path.open("r", encoding=enc, errors="ignore") as f:
                    raw = f.read()
                if ext in {".html", ".htm", ".xml", ".svg"}:
                    return self._strip_markup(raw)
                return raw
            except Exception:
                continue
        return ""

    def _strip_markup(self, raw: str) -> str:
        no_script = re.sub(r"<script[^>]*>[\\s\\S]*?</script>", " ", raw, flags=re.IGNORECASE)
        no_style = re.sub(r"<style[^>]*>[\\s\\S]*?</style>", " ", no_script, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", no_style)
        text = re.sub(r"\\s+", " ", text)
        return text.strip()

    def _extract_pdf_text(self, file_path: Path) -> str:
        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(str(file_path))
            pages = []
            for page in reader.pages[: self.config.pdf_max_pages]:
                t = page.extract_text() or ""
                if t.strip():
                    pages.append(t)
            if pages:
                return "\n\n".join(pages)
        except Exception:
            pass

        # Fallback to pdftotext — the only path that actually runs in
        # production, which has no pypdf installed (final review, finding
        # 3). Uncapped: pdftotext reads every page, bounded only by the
        # configurable timeout below, not by pdf_max_pages.
        try:
            proc = subprocess.run(
                ["pdftotext", "-layout", str(file_path), "-"],
                capture_output=True,
                text=True,
                timeout=self.config.pdf_timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise PdfExtractionError("timeout") from exc
        except Exception as exc:
            # pdftotext missing, permission denied, etc. — a deployment/
            # environment problem, not a fact about this PDF's content.
            raise PdfExtractionError("error") from exc

        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout

        # pdftotext ran to completion and produced nothing: a genuinely
        # scanned PDF with no text layer. A real fact about the file, not an
        # extraction failure — return "" normally rather than raising.
        return ""

    def _extract_docx_text(self, file_path: Path, sinir: int | None = None,
                           hata_bildir: bool = False) -> str:
        """A .docx's paragraphs, from word/document.xml, with the stdlib only.

        Teachers attach Word sheets as often as PDFs (plan 2026-09-28
        portal-ekleri). Before this a .docx fell through to the unknown-
        extension branch and its zip bytes were read as text. Tabs and line
        breaks inside a paragraph are kept; paragraphs are blank-line
        separated so the chunker keeps them apart. An unreadable archive is
        "" (metadata only), never garbage.

        Fix round 1 (reviewer-verified defects, see tests/test_assistant_docx.py):
        the DTD/entity scan now covers the whole (already size-bounded) byte
        string instead of a fixed 4096-byte prefix a padded leading comment
        could push the real marker past; the size cap is enforced by a
        bounded chunked read rather than trusting the archive's own declared
        (forgeable) ZipInfo.file_size; and the except clause is broadened so
        no parsing exception — e.g. LookupError from an XML-declared
        encoding name Python's codec registry does not know — escapes and
        aborts a whole reindex over one bad attachment.

        Fix round 2 (coordinator-verified): a byte-level regex cannot be
        made encoding-proof (see _docx_declares_dtd_or_entity's docstring),
        so the real DTD/entity gate now runs at the parser (expat) rather
        than on undecoded bytes; the regex is kept only as a cheap first
        filter for the common ASCII/UTF-8 case.

        `sinir` overrides DOCX_XML_SINIRI for one call (the portal
        attachment sync reads at most 8 MiB: measured on f29062c, 49 MB of
        XML cost 554 MB RSS). With `hata_bildir` an unreadable archive raises
        DocxExtractionError with its reason instead of returning ""."""
        sinir = DOCX_XML_SINIRI if sinir is None else sinir
        try:
            with zipfile.ZipFile(file_path) as arsiv:
                bilgi = arsiv.getinfo("word/document.xml")
                # Fast pre-filter only: ZipInfo.file_size is declared by the
                # archive's own central directory and is not a fact about
                # the entry — a crafted zip can declare a tiny size whose
                # real deflate stream decompresses to something far larger
                # (a zip bomb). A size already over the cap short-circuits
                # here without opening a read stream at all; the real
                # enforcement is the bounded read below.
                if bilgi.file_size > sinir:
                    raise DocxExtractionError("sinir")
                parcalar: list[bytes] = []
                toplam = 0
                with arsiv.open(bilgi) as akis:
                    while True:
                        parca = akis.read(65536)
                        if not parca:
                            break
                        toplam += len(parca)
                        if toplam > sinir:
                            # The real decompressed size exceeds the cap
                            # regardless of what file_size claimed. Stop
                            # reading immediately — never materialise the
                            # rest of the stream just to throw it away.
                            raise DocxExtractionError("sinir")
                        parcalar.append(parca)
                veri = b"".join(parcalar)
            # No defusedxml (not installed; the design allows no new
            # dependency). A real document.xml never declares a DTD or an
            # entity, so either one refuses parsing outright. The regex is
            # a cheap first filter for the common ASCII/UTF-8 case, scanned
            # across the whole (already size-bounded) byte string rather
            # than a fixed prefix a large leading comment could push the
            # real marker past — but it is not the real gate: a byte scan
            # cannot be made encoding-proof (a UTF-16-encoded document puts
            # a NUL byte between every ASCII letter, so these literal bytes
            # never occur even though the decoded document declares both).
            # The actual gate is _docx_declares_dtd_or_entity, which asks
            # expat — the same parser ElementTree uses — directly, so no
            # encoding it understands gets past it.
            if re.search(rb"<!DOCTYPE|<!ENTITY", veri, re.IGNORECASE):
                raise DocxExtractionError("dtd")
            if _docx_declares_dtd_or_entity(veri):
                raise DocxExtractionError("dtd")
            kok = ElementTree.fromstring(veri)
        except Exception as exc:
            # Anything reading or parsing this archive can raise: a bad
            # zip, a missing word/document.xml, malformed XML, or an
            # XML-declared encoding name Python's codec registry does not
            # know (LookupError, not a subclass of any of the narrower
            # exceptions this used to catch). One bad .docx must never
            # raise out of here and abort a whole index update — unless
            # the caller asked for the reason (hata_bildir).
            if hata_bildir:
                neden = exc.reason if isinstance(exc, DocxExtractionError) else "bozuk"
                raise DocxExtractionError(neden) from exc
            return ""
        paragraflar: list[str] = []
        for p in kok.iter(f"{_WORD_NS}p"):
            parcalar: list[str] = []
            for el in p.iter():
                if el.tag == f"{_WORD_NS}t" and el.text:
                    parcalar.append(el.text)
                elif el.tag == f"{_WORD_NS}tab":
                    parcalar.append("\t")
                elif el.tag in (f"{_WORD_NS}br", f"{_WORD_NS}cr"):
                    parcalar.append("\n")
            satir = "".join(parcalar).strip()
            if satir:
                paragraflar.append(satir)
        return "\n\n".join(paragraflar)

    def _extract_image_text(self, file_path: Path) -> str:
        if not self.config.enable_ocr:
            return ""
        try:
            from PIL import Image  # type: ignore
            import pytesseract  # type: ignore

            image = Image.open(file_path)
            text = pytesseract.image_to_string(image, lang=os.environ.get("ASSISTANT_OCR_LANG", "tur+eng"))
            return text.strip()
        except Exception:
            return ""

    def _metadata_only_text(self, rel_path: str, file_path: Path, reason: str) -> str:
        stat = file_path.stat()
        return (
            f"[metadata_only] path={rel_path} reason={reason} "
            f"size_bytes={stat.st_size} mtime={datetime.fromtimestamp(stat.st_mtime).isoformat()}"
        )


class AssistantIndexer:
    def __init__(self, config: AssistantConfig):
        self.config = config
        self.adapters = FileAdapters(config)

    def reindex(self, incremental: bool = True) -> dict[str, Any]:
        start = time.perf_counter()

        old_manifest = self._load_json(self.config.manifest_path, {"files": {}})
        # A manifest built under an older index format (different discovery,
        # exclusion or tokenization rules) must not be trusted for reuse: a
        # matching sha256 says the *file* did not change, not that the chunk
        # it produced still reflects the current rules. Treat it as absent —
        # every file is reprocessed — regardless of the incremental flag.
        manifest_is_current = (
            isinstance(old_manifest, dict)
            and old_manifest.get("version") == INDEX_FORMAT_VERSION
        )
        if not manifest_is_current and isinstance(old_manifest, dict) and old_manifest.get("files"):
            logger.warning(
                "assistant index format changed (persisted v%r -> v%d): full rebuild",
                old_manifest.get("version"), INDEX_FORMAT_VERSION)
        old_files = (old_manifest.get("files", {})
                     if manifest_is_current and isinstance(old_manifest, dict) else {})

        old_chunks = self._load_json(self.config.chunks_path, []) if manifest_is_current else []
        if not isinstance(old_chunks, list):
            old_chunks = []
        old_embeddings = self._load_json(self.config.embeddings_path, {}) if manifest_is_current else {}
        if not isinstance(old_embeddings, dict):
            old_embeddings = {}

        old_chunks_by_path: dict[str, list[dict[str, Any]]] = {}
        for ch in old_chunks:
            path = str(ch.get("path", ""))
            if not path:
                continue
            old_chunks_by_path.setdefault(path, []).append(ch)

        discovered = self._discover_files()

        new_manifest_files: dict[str, dict[str, Any]] = {}
        new_chunks: list[dict[str, Any]] = []
        new_embeddings: dict[str, list[float]] = {}
        # Final review, finding 1: files whose extraction failed or timed
        # out (PdfExtractionError) rather than being cut by the chunk cap —
        # named with a reason, on top of the plain dusen_dosyalar listing
        # both share (dropped_files below is "discovered minus manifest",
        # which already includes these with no extra bookkeeping).
        failed_extractions: dict[str, str] = {}

        changed = 0
        unchanged = 0
        deleted = 0
        embedded = 0
        skipped_embeddings = 0

        max_chunks = max(1, self.config.max_chunks)

        for idx, file_path in enumerate(discovered):
            rel_path = file_path.relative_to(self.config.project_root).as_posix()
            stat = file_path.stat()
            sha = self._file_sha256(file_path)
            ext = file_path.suffix.lower()

            file_record = {
                "sha256": sha,
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "ext": ext,
            }

            old_rec = old_files.get(rel_path) if isinstance(old_files, dict) else None
            can_reuse = bool(
                incremental
                and old_rec
                and old_rec.get("sha256") == sha
                and rel_path in old_chunks_by_path
            )

            if can_reuse:
                file_chunks = old_chunks_by_path.get(rel_path, [])
                # A file's chunks are all-or-nothing (fix round 1, item 2): a
                # manifest entry must never claim a file is indexed when only
                # some of its chunks fit under the cap — that reads as
                # complete forever (sha256 unchanged) and the rest is gone
                # with no record. If it does not fully fit, stop here; it
                # lands in dusen_dosyalar below like any other cut-off file.
                if len(file_chunks) > max_chunks - len(new_chunks):
                    break
                new_manifest_files[rel_path] = file_record
                unchanged += 1
                for chunk in file_chunks:
                    new_chunks.append(chunk)
                    chunk_id = str(chunk.get("chunk_id", ""))
                    if chunk_id and chunk_id in old_embeddings:
                        emb = old_embeddings[chunk_id]
                        if isinstance(emb, list):
                            new_embeddings[chunk_id] = emb
                if len(new_chunks) >= max_chunks:
                    break
                continue

            extracted = self.adapters.extract(file_path, rel_path)

            extraction_error = extracted.get("extraction_error")
            if extraction_error:
                # No manifest entry, no chunks: sha256 stays unmatched next
                # run, so this file is retried in full rather than being
                # recorded as "indexed, no text" forever (final review,
                # finding 1).
                failed_extractions[rel_path] = str(extraction_error)
                logger.warning(
                    "assistant index: extraction failed for %s (%s) — "
                    "no manifest entry written, will retry next run",
                    rel_path, extraction_error)
                continue

            text = str(extracted.get("text", ""))
            source_kind = str(extracted.get("source_kind", "text"))
            confidence = float(extracted.get("confidence", 0.5))
            warnings = extracted.get("warnings", [])
            if not isinstance(warnings, list):
                warnings = []

            chunks = self._chunk_text(text)
            if not chunks:
                chunks = [text[: self.config.chunk_size] if text else ""]

            # Same all-or-nothing rule for freshly extracted files: decide
            # before writing anything, so a file the cap would cut in the
            # middle is never partially persisted under a manifest entry
            # that claims it is complete.
            if len(chunks) > max_chunks - len(new_chunks):
                break

            new_manifest_files[rel_path] = file_record
            changed += 1
            for chunk_index, chunk_text in enumerate(chunks):
                chunk_id = self._chunk_id(rel_path, sha, chunk_index)
                chunk_obj = {
                    "chunk_id": chunk_id,
                    "path": rel_path,
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                    "source_kind": source_kind,
                    "confidence": confidence,
                    "warnings": warnings,
                    "mtime": stat.st_mtime,
                    "size": stat.st_size,
                    "sha256": sha,
                    "updated_at": _utcnow_naive().isoformat() + "Z",
                }
                new_chunks.append(chunk_obj)

                # Embeddings disabled (Gemini-only, BM25 search)
                skipped_embeddings += 1

            if len(new_chunks) >= max_chunks:
                break

        # Deleted files in incremental mode
        if incremental and isinstance(old_files, dict):
            old_paths = set(old_files.keys())
            new_paths = set(new_manifest_files.keys())
            deleted = len(old_paths - new_paths)

        # Files the chunk cap cut off before they were ever processed: no
        # manifest entry was created for them (task-1 brief §2 — "sessiz
        # düşme yok"). Discovery order (output/ before content/) means these
        # are, in practice, the tail of content/.
        dropped_files = sorted(
            {file_path.relative_to(self.config.project_root).as_posix() for file_path in discovered}
            - set(new_manifest_files.keys())
        )
        # Extraction failures already logged their own reason above; this
        # message is specifically about the chunk cap, so it only names the
        # files that landed here because of it.
        cap_dropped = [p for p in dropped_files if p not in failed_extractions]
        if cap_dropped:
            logger.warning(
                "assistant index: chunk cap (%d) reached — %d file(s) dropped: %s",
                max_chunks, len(cap_dropped), ", ".join(cap_dropped))

        total_embedded = len(new_embeddings)
        meta = {
            "generated_at": _utcnow_naive().isoformat() + "Z",
            "incremental": incremental,
            "files_indexed": len(new_manifest_files),
            "chunks_indexed": len(new_chunks),
            "changed_files": changed,
            "unchanged_files": unchanged,
            "deleted_files": deleted,
            "dusen_dosyalar": dropped_files,
            # Final review, finding 1: a reason for the subset of
            # dusen_dosyalar that failed extraction (timeout/error) rather
            # than being cut by the chunk cap — path -> reason ("timeout"/
            # "error"). Cap-dropped files have no entry here.
            "dusen_dosyalar_nedenleri": failed_extractions,
            # Report total persisted embeddings so incremental runs keep stable visibility.
            "embedded_chunks": total_embedded,
            "embedded_chunks_new": embedded,
            "skipped_embeddings": skipped_embeddings,
            "embeddings_enabled": False,
            "chat_model": os.environ.get("ASSISTANT_CLAUDE_MODEL", "").strip() or ClaudeClient.DEFAULT_MODEL,
            "chat_fallback_model": None,
            "embed_model": None,
            "duration_ms": int((time.perf_counter() - start) * 1000),
        }

        manifest_payload = {
            "version": INDEX_FORMAT_VERSION,
            "generated_at": meta["generated_at"],
            "files": new_manifest_files,
            "stats": {
                "files": len(new_manifest_files),
                "chunks": len(new_chunks),
            },
        }

        atomic_json_dump(manifest_payload, str(self.config.manifest_path))
        atomic_json_dump(new_chunks, str(self.config.chunks_path))
        atomic_json_dump(new_embeddings, str(self.config.embeddings_path))
        atomic_json_dump(meta, str(self.config.meta_path))

        return meta

    def _ordered_include_dirs(self) -> list[str]:
        """output/ before content/ (task-1 brief §2): if the chunk cap cuts
        the run short, the far larger content/ textbook corpus is what gets
        dropped, never Işık's own scraped data. Any other configured include
        dir (a custom ASSISTANT_INCLUDE_DIRS entry) is scanned last."""
        priority = [d for d in _DISCOVERY_PRIORITY if d in self.config.include_dirs]
        rest = sorted(self.config.include_dirs - set(priority))
        return priority + rest

    def _discover_files(self) -> list[Path]:
        """Discover files from whitelisted directories only, output/ first."""
        files: list[Path] = []
        root = self.config.project_root
        idx_dir = self.config.index_dir.resolve()

        for inc_dir in self._ordered_include_dirs():
            scan_root = root / inc_dir
            if not scan_root.is_dir():
                continue
            group: list[Path] = []
            for dirpath, dirnames, filenames in os.walk(
                    scan_root):
                dir_path = Path(dirpath)
                rel_dir = dir_path.relative_to(
                    root).as_posix()

                filtered_dirs: list[str] = []
                for d in dirnames:
                    rel = f"{rel_dir}/{d}".strip("/")
                    if self._is_excluded_dir(rel):
                        continue
                    full = (dir_path / d).resolve()
                    if full == idx_dir:
                        continue
                    filtered_dirs.append(d)
                dirnames[:] = filtered_dirs

                for name in filenames:
                    file_path = dir_path / name
                    rel_file = f"{rel_dir}/{name}"
                    if self._is_excluded_file(rel_file):
                        continue
                    try:
                        if not file_path.is_file():
                            continue
                        group.append(file_path)
                    except Exception:
                        continue

            # Sort within this include dir only — a global re-sort across all
            # groups would put "content/..." back ahead of "output/..."
            # alphabetically and silently undo the priority above.
            # Işık's own school attachments lead content/, as output/ leads the
            # whole walk: a chunk-cap overrun then drops textbooks first.
            group.sort(key=lambda p: (
                not p.relative_to(root).as_posix().startswith(PORTAL_EKLERI_DIZINI + "/"),
                p.relative_to(root).as_posix()))
            files.extend(group)

        return files

    def is_path_currently_included(self, rel_path: str) -> bool:
        """Whether `rel_path` would be discovered under this indexer's
        CURRENT include/exclude rules (final review, finding 2).

        `_load_retriever`/`_load_aile_retriever` load `chunks.json` straight
        off disk; until the next successful `reindex()`, that file can still
        hold chunks a rule change (a new excluded dir/pattern, or an
        include_dirs change like Görev 5's separate content/pedagoji index)
        would no longer produce — e.g. a v1-shaped main index still carrying
        content/pedagoji or a session-cookie chunk. Re-checking each
        persisted chunk's path against the live rules at load time closes
        that window instead of waiting for a rebuild."""
        normalized = rel_path.strip("/")
        if not normalized:
            return False
        if not any(normalized == d or normalized.startswith(d + "/")
                   for d in self.config.include_dirs):
            return False
        parent = str(Path(normalized).parent).replace("\\", "/")
        if parent == ".":
            parent = ""
        if self._is_excluded_dir(parent):
            return False
        if self._is_excluded_file(normalized):
            return False
        return True

    def _is_excluded_dir(self, rel_dir: str) -> bool:
        normalized = rel_dir.strip("/")
        if not normalized:
            return False
        for ex in self.config.excluded_dirs:
            ex_norm = ex.strip("/")
            if normalized == ex_norm or normalized.startswith(ex_norm + "/"):
                return True
        # Any path segment naming itself a backup — "saat_dilimi_gocu_yedek",
        # "eba_backup", "2026_yedek_kopya" — is a copy of something already
        # indexed under its real name, wherever in the tree it sits.
        for segment in normalized.split("/"):
            low = segment.lower()
            if "yedek" in low or "backup" in low:
                return True
        return False

    def _is_excluded_file(self, rel_file: str) -> bool:
        normalized = rel_file.strip("/")
        if not normalized:
            return False
        base = Path(normalized).name
        if normalized.startswith(PORTAL_EKLERI_DIZINI + "/"):
            ic = normalized[len(PORTAL_EKLERI_DIZINI) + 1:]
            return "/" in ic or not ic.endswith(".txt")
        # The noise filters below are broad globs (eba_*.json, mebi_*.json,
        # sebitv_*.json) aimed at discovery dumps. They would also swallow the
        # upload trackers, which have purpose-built semantic chunkers — an
        # explicit allow-list entry outranks a pattern.
        if base in _SEMANTIC_JSON_FILES:
            return False
        for pat in self.config.excluded_file_patterns:
            p = pat.strip()
            if not p:
                continue
            if "/" in p:
                if fnmatch.fnmatch(normalized, p):
                    return True
            elif fnmatch.fnmatch(base, p):
                return True
        return False

    def _is_embedding_target(self, rel_path: str, ext: str) -> bool:
        path = rel_path.strip().lower()
        ext = ext.lower()
        if ext not in EMBED_TARGET_EXTENSIONS:
            return False
        if path == "readme.md" or path == "claude.md":
            return True
        return path.startswith("docs/") or path.startswith("output/")

    def _chunk_text(self, text: str) -> list[str]:
        raw = text.strip()
        if not raw:
            return []

        # Normalize long whitespace while preserving paragraph boundaries.
        paras = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
        if not paras:
            paras = [raw]

        chunks: list[str] = []
        cur = ""
        size = max(200, self.config.chunk_size)
        overlap = max(0, min(self.config.chunk_overlap, size // 2))

        for para in paras:
            para = re.sub(r"\s+", " ", para)
            if len(para) > size * 2:
                # Hard split very long paragraphs.
                start = 0
                while start < len(para):
                    part = para[start:start + size]
                    if cur:
                        chunks.append(cur)
                        cur = ""
                    chunks.append(part)
                    start += size - overlap if overlap > 0 else size
                continue

            candidate = f"{cur}\n\n{para}".strip() if cur else para
            if len(candidate) <= size:
                cur = candidate
                continue

            if cur:
                chunks.append(cur)

            if overlap > 0 and chunks:
                prev_tail = chunks[-1][-overlap:]
                cur = f"{prev_tail} {para}".strip()
            else:
                cur = para

            if len(cur) > size:
                chunks.append(cur[:size])
                cur = cur[size - overlap:] if overlap > 0 else ""

        if cur:
            chunks.append(cur)

        return [c[: size * 2] for c in chunks if c.strip()]

    def _chunk_id(self, rel_path: str, sha: str, index: int) -> str:
        src = f"{rel_path}|{sha}|{index}"
        return hashlib.sha1(src.encode("utf-8")).hexdigest()[:20]

    def _file_sha256(self, file_path: Path) -> str:
        h = hashlib.sha256()
        with file_path.open("rb") as f:
            while True:
                buf = f.read(1024 * 1024)
                if not buf:
                    break
                h.update(buf)
        return h.hexdigest()

    def _load_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default


# Turkish-aware casefold + accent folding, shared by index-time and
# query-time tokenization (task-1 brief §4). Order matters: Python's plain
# str.lower() turns 'İ' into 'i' plus a COMBINING DOT ABOVE (U+0307) — a
# character outside any plain-ASCII token pattern — which silently split
# "İngilizce" into the tokens ['i', 'ngilizce'] (measured, audit §2d). The
# İ/I translation must run before .lower() touches the rest of the string;
# the accent fold then runs last so 'ısı' and 'isi' tokenize identically.
_TR_UPPER_MAP = str.maketrans({"İ": "i", "I": "ı"})
_TR_FOLD_MAP = str.maketrans({"ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c"})


def turkce_kucult_katla(text: str) -> str:
    """Turkish-aware lowercase, then accent fold: 'İngilizce'/'ingilizce' and
    'ısı'/'isi' become the same string. Used for both indexed chunk text and
    the search query, so the two can never tokenize differently."""
    return text.translate(_TR_UPPER_MAP).lower().translate(_TR_FOLD_MAP)


class HybridRetriever:
    def __init__(self, chunks: list[dict[str, Any]],
                 embeddings: dict[str, list[float]] | None = None,
                 ollama: Any = None,
                 vector_weight: float = 0.0):
        self.chunks = chunks
        self.embeddings = embeddings or {}
        self.vector_weight = 0.0  # BM25 only

        self._tokens_per_doc: list[list[str]] = []
        self._doc_freq: dict[str, int] = {}
        self._doc_len: list[int] = []
        self._avg_doc_len = 1.0
        self._build_lexical_index()

    def _build_lexical_index(self) -> None:
        for ch in self.chunks:
            text = str(ch.get("text", ""))
            tokens = self._tokenize(text)
            self._tokens_per_doc.append(tokens)
            self._doc_len.append(len(tokens))
            unique = set(tokens)
            for t in unique:
                self._doc_freq[t] = self._doc_freq.get(t, 0) + 1
        if self._doc_len:
            self._avg_doc_len = sum(self._doc_len) / len(self._doc_len)

    def search(self, query: str, top_k: int = 8, context_filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        query = query.strip()
        if not query:
            return []

        context_filters = context_filters or {}
        path_prefixes = context_filters.get("path_prefixes")
        if not isinstance(path_prefixes, list):
            path_prefixes = []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            query_tokens = [query.lower()]

        bm25_scores = self._bm25_scores(
            query_tokens, path_prefixes)

        max_bm25 = max(bm25_scores.values()) if bm25_scores else 1.0
        if max_bm25 <= 0:
            max_bm25 = 1.0

        combined: list[tuple[int, float, float, float]] = []
        for idx, raw in bm25_scores.items():
            b = raw / max_bm25
            combined.append((idx, b, b, 0.0))

        combined.sort(key=lambda x: x[1], reverse=True)

        results: list[dict[str, Any]] = []
        for idx, score, b, v in combined[: max(1, top_k)]:
            ch = self.chunks[idx]
            snippet = str(ch.get("text", "")).strip().replace("\n", " ")
            if len(snippet) > 260:
                snippet = snippet[:257] + "..."
            results.append({
                "chunk_id": ch.get("chunk_id"),
                "path": ch.get("path"),
                "chunk_index": ch.get("chunk_index"),
                "score": round(float(score), 5),
                "bm25": round(float(b), 5),
                "vector": round(float(v), 5),
                "confidence": ch.get("confidence", 0.0),
                "snippet": snippet,
                "text": ch.get("text", ""),
                "source_kind": ch.get("source_kind", "text"),
            })
        return results

    def _bm25_scores(self, query_tokens: list[str], path_prefixes: list[str]) -> dict[int, float]:
        k1 = 1.2
        b = 0.75
        n_docs = max(1, len(self.chunks))
        scores: dict[int, float] = {}

        for i, tokens in enumerate(self._tokens_per_doc):
            if path_prefixes and not self._path_allowed(str(self.chunks[i].get("path", "")), path_prefixes):
                continue
            tf: dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1

            doc_len = self._doc_len[i] if i < len(self._doc_len) else len(tokens)
            score = 0.0
            for q in query_tokens:
                fq = tf.get(q, 0)
                if fq == 0:
                    continue
                df = self._doc_freq.get(q, 0)
                idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
                denom = fq + k1 * (1 - b + b * (doc_len / self._avg_doc_len))
                score += idf * ((fq * (k1 + 1)) / denom)
            if score > 0:
                scores[i] = score
        return scores

    def _path_allowed(self, path: str, prefixes: list[str]) -> bool:
        if not prefixes:
            return True
        for p in prefixes:
            p = str(p).strip().strip("/")
            if not p:
                continue
            if path == p or path.startswith(p + "/"):
                return True
        return False

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-z0-9_]+", turkce_kucult_katla(text))

    def _dot(self, a: list[float], b: list[float]) -> float:
        m = min(len(a), len(b))
        if m == 0:
            return 0.0
        return sum(a[i] * b[i] for i in range(m))

    def _norm(self, v: list[float]) -> float:
        return math.sqrt(sum(x * x for x in v))


class SafetyPolicy:
    HIGH_RISK_PATTERNS = [
        r"intihar",
        r"kendime zarar",
        r"kendine zarar",
        r"ölmek istiyorum",
        r"yaşamak istemiyorum",
    ]

    CLINICAL_PATTERNS = [
        r"tanı koy",
        r"teşhis",
        r"ilaç",
        r"doz",
        r"tedavi planı",
        r"depresyon testi",
    ]

    def evaluate(self, text: str) -> list[str]:
        flags: list[str] = []
        low = text.lower()

        for pat in self.HIGH_RISK_PATTERNS:
            if re.search(pat, low):
                flags.append("risk:mental_health_crisis")
                break

        for pat in self.CLINICAL_PATTERNS:
            if re.search(pat, low):
                flags.append("risk:clinical_request")
                break

        return flags

    def guidance_suffix(self, flags: list[str]) -> str:
        if not flags:
            return ""
        if "risk:mental_health_crisis" in flags:
            return (
                "\n\nÖnemli: Bu konuda acil güvenlik riski olabilir. "
                "Güvendiğiniz bir yetişkin, okul rehberlik servisi veya yerel acil destek hattıyla hemen iletişim kurun."
            )
        if "risk:clinical_request" in flags:
            return (
                "\n\nNot: Klinik tanı/tedavi önerisi veremem. "
                "Bu konuyu okul psikolojik danışmanı veya lisanslı uzmanla değerlendirin."
            )
        return ""


class AssistantRuntime:
    """High-level assistant runtime used by API endpoints and sync hooks."""

    def __init__(self, project_root: str | os.PathLike[str],
                 odev_kaynagi: Callable[[], list[dict[str, Any]]] | None = None,
                 program_kaynagi: Callable[[], Any] | None = None,
                 sinav_kaynagi: Callable[[], Any] | None = None,
                 takvim_kaynagi: Callable[[], Any] | None = None,
                 icerik_kaynagi: Callable[[], Any] | None = None,
                 not_kaynagi: Callable[[], Any] | None = None,
                 sebit_kaynagi: Callable[[], Any] | None = None,
                 platform_kaynagi: Callable[[], Any] | None = None,
                 kitap_kaynagi: Callable[[], list[dict[str, Any]]] | None = None,
                 video_kaynagi: Callable[[], Any] | None = None,
                 skills: dict[str, Any] | None = None):
        # First, before anything else is built: a broken teacher skill stops the
        # assistant from opening at all (spec "Hata ve boşluk durumları"), with
        # the skill and the reason in the error — never a silent fallback.
        # `skills` lets tests bring their own; production reads the repo's.
        self.skills: dict[str, Any] = (assistant_skills.varsayilan() if skills is None
                                       else dict(skills))
        self.config = AssistantConfig.from_project_root(
            project_root)
        self.llm = ClaudeClient()
        self.router = self.llm
        self._sinif_cache: tuple[float, str] = (-1.0, "")
        self.indexer = AssistantIndexer(self.config)
        self.policy = SafetyPolicy()

        self._retriever: HybridRetriever | None = None
        self._retriever_cache_mtime: float = 0.0

        # Görev 5: content/pedagoji (adult parenting/learning-science notes) as its
        # own BM25 section — a separate AssistantConfig/AssistantIndexer pointed at
        # a second index directory, never mixed into the main one (which excludes
        # content/pedagoji outright; see DEFAULT_EXCLUDED_DIRS). Built unconditionally
        # here — the tool's gate is the reader (`aile_kaynak_ara` declared only for
        # okur == "aile"; see McpRegistry), not whether this directory has content.
        self.aile_config = AssistantConfig.from_project_root(
            project_root,
            index_subdir="assistant_index_aile",
            include_dirs={"content/pedagoji"},
            excluded_dirs=set(),
        )
        self.aile_indexer = AssistantIndexer(self.aile_config)
        self._aile_retriever: HybridRetriever | None = None
        self._aile_retriever_cache_mtime: float = 0.0

        from src.assistant_modules import ModuleIndex
        from src.assistant_tools import build_registry
        # Published edupedia modules (plan SP5 K-S1): read-only, per process, no index file.
        self.modules = ModuleIndex(self.config.output_dir)
        # odev_kaynagi: the homework rows Bugün shows (dashboard_api._canli_odevler).
        # The other *_kaynagi are the live student-data sources (dashboard_api
        # ._canli_*); each one absent leaves its tool undeclared.
        self.registry = build_registry(self._local_search, module_index=self.modules,
                                       odev_kaynagi=odev_kaynagi,
                                       sinif=self._mufredat_sinifi,
                                       program_kaynagi=program_kaynagi,
                                       sinav_kaynagi=sinav_kaynagi,
                                       takvim_kaynagi=takvim_kaynagi,
                                       icerik_kaynagi=icerik_kaynagi,
                                       not_kaynagi=not_kaynagi,
                                       sebit_kaynagi=sebit_kaynagi,
                                       platform_kaynagi=platform_kaynagi,
                                       kitap_kaynagi=kitap_kaynagi,
                                       video_kaynagi=video_kaynagi,
                                       aile_kaynak_arama=self._aile_search,
                                       skills=self.skills)

    def _local_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """The retriever, shaped as a tool the model can choose to call."""
        return self._load_retriever().search(query, top_k=top_k)

    def _aile_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """content/pedagoji's own retriever (Görev 5). Wired unconditionally;
        `aile_kaynak_ara` is declared only when the reader is `aile` (McpRegistry.declarations)."""
        return self._load_aile_retriever().search(query, top_k=top_k)

    DEEP_INTENTS = frozenset({"study_plan", "grade_analysis", "exam_solving"})

    @classmethod
    def _tier_for(cls, intent: str, force_deep: bool) -> str:
        # Deterministic on purpose: the same question must pick the same tier,
        # so latency and quota use stay predictable.
        return "deep" if (force_deep or intent in cls.DEEP_INTENTS) else "fast"

    SYSTEM_PROMPT = (
        "Sen TEDY Eğitim Asistanısın — {SINIF} öğrencisi Işık ve ailesi için "
        "kişisel eğitim danışmanısın. Varsayılan dil Türkçe.\n\n"

        "## Hangi araca ne zaman uzanırsın\n"
        "- Aşağıdaki araçların bir kısmı çalışma zamanına göre ilan edilir: kaynağı "
        "verilmemişse araç listende hiç görünmez. Listende görmediğin bir aracı çağırma; "
        "onun yerine eksikliği açıkça söyle.\n"
        "- Ders programı (bugün/yarın hangi dersler, kaçta) → `ders_programi`. "
        "Sınav tarihleri → `sinavlar`. Okul etkinliği, tatil, özel ders → `takvim`. "
        "Bir dersin haftalık içeriği → `ders_icerigi`. Notlar ve kazanım düzeyleri → "
        "`notlar`; rapor önceki öğretim yılına aitse bunu söyle, eski yılın notunu bu "
        "yılınki gibi sunma.\n"
        "- Ödev sorusu (hangi ödevler var, ne zaman teslim, neyi yaptı, ne kaldı) → "
        "önce `odev_listesi`. Ödevin durumu için tek güvenilir kaynak odur: Bugün "
        "sayfasının gösterdiği listeyi, Işık'ın 'Yaptım' işaretleriyle verir. "
        "Işık'ın 'Yaptım' dediği bir ödevi yapılacak diye sunma. Teslim zamanını "
        "söylerken listedeki gün ve saati kullan; 'bu hafta', 'yarın' gibi sözleri "
        "sorudaki 'Bugün:' satırına göre çöz.\n"
        "- Işık'a özel diğer sorular (duyuru, eski ödev, portalın ek sayfaları) ve bir "
        "ödevin ayrıntısı → `ogrenci_verisi_ara`.\n"
        "- Konu, kavram, müfredat, kazanım sorusu → `kazanim_ara`, `mufredat_ara`. MEB "
        "korpusu bu konularda tek otoritedir. Ders kitabı sayfası isteniyorsa kitabı "
        "`kitap_listele` ile, sayfayı mufredat_ara (kind='textbook') ile bul, metnini "
        "`kitap_sayfa` ile oku. MEB korpusunda Işık'ın sınıfının o dersteki kitabı "
        "yoksa bunu açıkça söyle ve kazanımla, öğretim programıyla devam et; başka "
        "bir sınıfın kitabını onun kitabıymış gibi sunma. Kitap bağlantısı verme.\n"
        "- Bir dersin TÜM kazanımlarının dökümü isteniyorsa (tek bir kazanımı değil, "
        "dersin kazanım listesi) → `kazanim_listele`; Işık'ın sınıfı için.\n"
        "- Bir dersin öğretim programındaki ünite/tema sırası → `program_getir`; dersin "
        "programı ve kitabı korpusta var mı → `ders_bilgisi`. İkisi de ders slug'ı ister "
        "(ör. 'ortaokul-matematik-dersi'); slug'ı ders/kazanım aramalarının sonucundaki "
        "`subject` alanından al.\n"
        "- Görsel/şema açıklaman gerekiyorsa → `figur_ara` ile bul, `figur_getir` ile aç; "
        "bu araç görseli sana da gösterir; anlattığın cümleye [S] koy — okur aynı "
        "görseli Kaynaklar panelinde küçük resim olarak görür. Sana gösterilmeyen bir görseli "
        "gördün gibi anlatma.\n"
        "- MEB'in program tanıtım ve sınıf içi etkinlik videoları → `video_listele` "
        "(`category` ile daralt); bir videonun bağlantısı → `video_getir`.\n"
        "- `oer_ara` bir belgeden tek pasaj verir; devamı gerekiyorsa → `oer_getir` (doc_id). "
        "Kazanım kodun elindeyse, tam o kazanıma hizalanmış OER için → `oer_kazanima_gore`.\n"
        "- Etkileşimli çalışma, yayınlanmış modül ya da 'bu konu/sınav için modül var mı' sorusu → "
        "`modul_ara`. Modül adı ve künyesi YALNIZ bu aracın sonucundan gelir; araç modül bulamadıysa "
        "bunu söyle, modül ya da bağlantı uydurma. Modülü önerdiğin cümleye aracın [S] numarasını koy; "
        "bağlantıyı kendin yazma — okur modülü Kaynaklar panelinden açar.\n"
        "- Tedy Books'taki bir kitabın metninde geçen olay, karakter ya da alıntı "
        "için → `kitap_ara`. Bu, MEB ders kitabından ayrı, Işık'ın okuduğu bir "
        "kitap rafıdır; ders kitabı sayfası aracıyla karıştırma.\n"
        "- EnglishCentral/Achieve3000'deki ilerlemesi → `platform_ilerlemesi`.\n"
        "- Bir konuda video/konu anlatımı önerisi (MEBİ, SEBİTV) → `video_oner`. "
        "Kataloğun sınıf bilgisi yoksa bunu açıkça söyle, sınıf uydurma.\n"
        "- Soran aileden biri ise ve sorusu ebeveynlik ya da öğrenme bilimiyle ilgiliyse "
        "(motivasyon, sınav kaygısı, üstbiliş/öz-düzenleme, ölçme-değerlendirme, gelişim "
        "psikolojisi) → `aile_kaynak_ara`. Bu araç yalnız aile için vardır: "
        "Işık'la konuşurken bu araçtan hiç söz etme ve çağırma.\n"
        "- Soru hem Işık'ın kaydına hem bir konuya dokunuyorsa (örn. "
        "'ödevimdeki kesir konusunu anlat') iki aracı da çağır: önce Işık'ın kendi "
        "kaydını arayan araçla somut kaydı al (hangi ödev, hangi konu, "
        "ne zaman), sonra oradan çıkan konuyla müfredat aracını "
        "çağır; cevabı ikisini birleştirerek kur.\n"
        "- 'İkisini karıştırma' burada kaynakların karışmaması demektir, "
        "aracın tekliği değil: Işık'ın notunu müfredattan, kazanımı yerel "
        "dosyadan çıkarma.\n"
        "- Araç listende `mod_oner` varsa ve soru açıkça Türkçe, Fen Bilimleri, Sosyal "
        "Bilgiler ya da Matematik dersinde bir konuyu, kavramı ya da soru çözmeyi öğrenmekle "
        "ilgiliyse `mod_oner`'i ilk içerik aracınla birlikte ya da tam cevapla birlikte çağır; "
        "yalnız `mod_oner` çağırdığın bir turda yazdığın metin cevabın başı olarak okura "
        "gösterilir. Soruyu eksiksiz cevapla: o dersin öğretmeni ve okura gösterilecek tek kısa "
        "gerekçe. Ödev listesi, sınav tarihi, ders programı gibi sorular bir ders adı taşısa da "
        "konu öğrenmek değildir; onlarda çağırma. Öneriyi cevap metninde tekrar etme; okur onu "
        "ayrı bir düğme olarak görür.\n"
        "- Bu istemden sonra ikinci bir sistem bölümü olarak 'Öğretmen modu' geliyorsa o dersin "
        "öğretmenisin: o bölüme uy. Bu istemin Hitap, Uydurma yasağı, Atıf ve Biçim kuralları "
        "orada da geçerlidir; o bölüm açıkça bir istisna koymadıkça.\n\n"

        "## Uydurma yasağı\n"
        "- Kazanım kodu, ders kitabı adı ve sayfa numarası YALNIZ araç "
        "çıktısından gelir. Hiçbirini hatırlayarak veya tahmin ederek yazma.\n"
        "- Araç sonuç döndürmediyse eksikliği açıkça söyle. Boşluğu doldurma.\n"
        "- Bir araca dayandırdığın cümlede, o kaynağı çürüten veya kaynakta olmayan bir olgu ekleme. Bu madde araç çıktısına dayanan cümleler içindir; kapsam dışı genel bilgi sorusunu yanıtlamanı yasaklamaz (bkz. Atıf).\n\n"

        "## Atıf\n"
        "- Araçtan gelen her bilgiyi kullandığın cümlede [S1], [S2] biçiminde "
        "işaretle. Bu numaralar araç sonucunda sana zaten gösterilir — yalnız "
        "gösterilen numarayı kullan, numara uydurma, kendin saymaya çalışma.\n"
        "- İşaretler kullanıcıya tıklanabilir kaynak olarak gösterilir.\n"
        "- Bir liste ya da ardışık cümleler aynı kaynaktan geliyorsa işareti bir "
        "kez, girişine koy; her maddeye tekrar etme. Art arda aynı numara okur "
        "için gürültüdür.\n"
        "- Yanıtın sonuna ayrı kaynak listesi ekleme; atıf satır içindedir.\n"
        "- Işık'ın kaydı veya müfredat dışında genel bilgi sorulursa yanıtla ve "
        "o cümleye [S] atıfı ekleme; atıf yalnız araç çıktısına aittir. Kaynaksız "
        "anlattığını bir kez, sade ve hitaba uygun bir cümleyle söyle (örn. "
        "'Tanımı ders kitabından değil, genel bilgiden veriyorum.'). Resmî kalıp "
        "('… alınmamıştır', 'kaynak satırı') kullanma; bu cümleyi kaynaklı bir "
        "cümlenin hemen önüne koyup onunla çeliştirme.\n\n"

        "## Hitap\n"
        "Sorunun başındaki 'Soran:' satırı kiminle konuştuğunu söyler. Bir cevap "
        "boyunca hitabı değiştirme.\n"
        "- Soran Işık ise ona 'sen' diye doğrudan konuş ('yaptın', 'ödevin', "
        "'başlayabilirsin'). Kendisinden üçüncü şahısla söz etme: 'Işık yaptı', "
        "'Işık'ın ödevi' yazma. Adıyla seslenmen gerekmez.\n"
        "- Soran Işık'ın ailesinden biriyse ona 'siz' diye konuş ve Işık'tan "
        "adıyla, üçüncü şahısla söz et ('Işık Yaptım demiş', 'Işık'ın ödevi'). "
        "Işık'a seslenme; öneriyi soran kişiye yönelt ('Işık'la birlikte "
        "bakabilirsiniz').\n"
        "- Soran bilinmiyorsa aileye konuşur gibi konuş: okura 'siz', Işık'a "
        "üçüncü şahıs.\n"
        "- Araç çıktıları Işık'tan üçüncü şahısla söz eder. Onları olduğu gibi "
        "aktarma, hitaba çevir.\n\n"

        "## Nasıl anlatırsın (DEHB-dostu)\n"
        "- İlk cümlede doğrudan cevabı ver.\n"
        "- Anlatımı 3–6 dakikada tüketilebilir parçalara böl; birden çok "
        "parçası olan cevapta her parçanın kendi başlığı olsun (bkz. Biçim).\n"
        "- Adımları numaralandır — 'neredeyim' sorusunun cevabı görünür olsun.\n"
        "- Bir ödevin ya da çalışmanın ne kadar süreceğini tahmin etme: portal "
        "bunu söylemez, tahmin uydurma olur, ve süreyi fazla tahmin eden bir "
        "okurda '3 ödev, 2 saat' başlamayı engelleyen bir duvardır. Süre yerine "
        "küçük bir başlangıç öner ('10 dakikayla başla', 'önce ilk sayfa'). "
        "'Matematiğe 10 dakika ayır' bir kutudur, 'matematik 30 dakika sürer' "
        "bir tahmindir.\n"
        "- Somut ol: ne yapılacak, ne zaman.\n"
        "- Başarıyı önce söyle, eksiği sonra ve yapıcı biçimde.\n"
        "- Uzun paragraf yazma; madde işareti ve kısa cümle kullan.\n\n"

        "## Biçim\n"
        "Cevabın sohbet penceresinde Markdown olarak dizilir; her cevap aynı "
        "iskeleti izlesin ki okur neyin nerede olduğunu aramasın.\n"
        "- Açılış: bir iki cümlelik doğrudan cevap. Üstüne başlık koyma.\n"
        "- Bölümler: cevap birden çok parçaysa her parçaya `### ` ile kısa bir "
        "başlık ver — 2–5 kelime; iki nokta, parantez, emoji yok (\"Pazartesiye "
        "üç ödev\", \"Sonra\"). Kısa bir cevapta başlık kullanma. Başlık yerine "
        "kalın bir satır yazma; başlık gerekiyorsa `###` yaz.\n"
        "- Listeler: sıra ya da öncelik bildiriyorsa numaralı, değilse madde "
        "işaretli. Her madde tek satır: kalın ad, ' — ', kısa açıklama "
        "(\"**Matematik** — Test 1 s.5-6; işlemsiz kabul edilmiyor\"). Alt madde "
        "en çok bir düzey.\n"
        "- Kalın yazıyı yalnız bir maddenin adı ve kilit bir tarih için kullan; "
        "cümleyi kalın yazma.\n"
        "- Kapanış: gerekiyorsa tek satır `**Şimdi:** …` — atılacak ilk küçük "
        "adım. Okurun bilmesi gereken bir çekince varsa `**Not:** …`. Başka "
        "etiket (\"Öneri:\", \"Bugün için not:\") uydurma; bu iki satır cevapta "
        "ayrı kutu olarak gösterilir.\n"
        "- Tablo, yatay çizgi (---), alıntı bloğu ve emoji kullanma.\n\n"

        "## Sınırlar\n"
        "- Modül ilerleme özetini yalnız soran kişiye aktar; ilerleme bilgisini (cevaplanan soru, "
        "doğru oranı, tamamlanma, son erişim) hiçbir zaman başka bir araca argüman olarak verme.\n"
        "- Klinik tanı koyma, tedavi önerme.\n"
        "- Riskli psikolojik durumda profesyonel destek yönlendirmesi yap."
    )

    def _mufredat_sinifi(self) -> str | None:
        """The grade in the maarif corpus's form: "7. sınıf" -> "7.Sınıf"."""
        m = re.match(r"(\d+)\. sınıf$", self._sinif())
        return f"{m.group(1)}.Sınıf" if m else None

    def _sinif(self) -> str:
        """"7. sınıf", from the class the portal profile shows ("7-D").

        The prompt said "6. sınıf" as a literal for a year after Işık moved up.
        Read once per change of the scrape file, not per request: it is large.
        """
        yol = self.config.output_dir / "scraped_data.json"
        try:
            mtime = yol.stat().st_mtime
        except OSError:
            return "ortaokul"
        if self._sinif_cache[0] != mtime:
            sinif = ""
            try:
                with yol.open(encoding="utf-8") as fh:
                    profil = (json.load(fh) or {}).get("ogrenci_profili") or {}
                m = re.match(r"\s*(\d{1,2})", str(profil.get("class_name") or ""))
                sinif = f"{m.group(1)}. sınıf" if m else ""
            except (OSError, ValueError, AttributeError):
                sinif = ""
            self._sinif_cache = (mtime, sinif)
        return self._sinif_cache[1] or "ortaokul"

    def _system_prompt(self) -> str:
        return self.SYSTEM_PROMPT.replace("{SINIF}", self._sinif())

    def reindex(self, incremental: bool = True) -> dict[str, Any]:
        stats = self.indexer.reindex(incremental=incremental)
        # Görev 5: the family pedagogy index is a second, independent run over
        # its own directory — same command path, its own summary, reported
        # alongside the main index rather than folded into it.
        aile_stats = self.aile_indexer.reindex(incremental=incremental)
        try:
            moduller = self.modules.durum(yenile=True)
        except Exception as exc:  # noqa: BLE001 — the file index already succeeded; say what failed
            logger.error("module index rebuild failed: %s", type(exc).__name__)
            moduller = {"katalog": "hata", "hata": type(exc).__name__}
        return {**stats, "moduller": moduller, "aile_kaynagi": aile_stats}

    def chat(
        self,
        messages: list[dict[str, Any]],
        session_id: str = "",
        context_filters: dict[str, Any] | None = None,
        temperature: float = 0.2,
        force_deep: bool = False,
        dispatch: Callable[[str, dict[str, Any]], Any] | None = None,
        ilerleme_izni: bool = False,
        on_delta: Callable[[str], None] | None = None,
        on_reset: Callable[[], None] | None = None,
        okur: str = "bilinmiyor",
        ogretmen: str = assistant_skills.GENEL,
        mod_onerisi: bool = True,
    ) -> dict[str, Any]:
        # `dispatch`, if given, replaces self.registry.dispatch for this
        # call only. chat_events() (below) uses this to wrap tool calls
        # with per-call progress narration WITHOUT mutating shared state:
        # the registry is a per-process singleton, and gthread workers
        # (this task) mean two chat() calls can now genuinely overlap.
        # Passing the wrapper in as an argument keeps each call's
        # narration local to its own stack frame instead of racing
        # another call's over one shared attribute.
        if ogretmen != assistant_skills.GENEL and ogretmen not in self.skills:
            # The API answers 400 before this; reaching here is a caller's bug.
            raise ValueError(f"bilinmeyen öğretmen: {ogretmen}")
        start = time.perf_counter()

        user_query = self._latest_user_message(messages)
        safety_flags = self.policy.evaluate(user_query)
        intent = self._classify_intent(user_query)
        tier = self._tier_for(intent, force_deep)

        if self._is_context_stale():
            safety_flags.append("warning:stale_context")

        convo = self._build_conversation(messages, user_query, intent, safety_flags,
                                         okur=okur, ogretmen=ogretmen)

        try:
            # `temperature` stays in chat()'s signature for /v1 callers but is
            # not forwarded: Sonnet 5 rejects sampling parameters (400).
            loop = self.llm.chat_with_tools(
                messages=convo,
                # aile_kaynak_ara (Görev 5) is declared only for okur == "aile" —
                # the reader decides the tool list, not a per-call opt-in.
                # The teacher decides the rest: mod_oner in genel, skill_kaynagi in a
                # teacher mode (B1). mod_onerisi=False (/v1, /plan) withholds
                # mod_oner even in genel — those endpoints have no switch button.
                declarations=self.registry.declarations(
                    okur, ogretmen=ogretmen, mod_onerisi=mod_onerisi),
                # Module progress enters the model context only for a signed-in person (plan K-S6);
                # the caller decides, and only an exact True counts.
                dispatch=dispatch or functools.partial(
                    self.registry.dispatch, ilerleme_izni=ilerleme_izni is True, okur=okur,
                    ogretmen=ogretmen, mod_onerisi=mod_onerisi),
                tier=tier,
                on_delta=on_delta,
                on_reset=on_reset,
            )
        except _StreamAbandoned:
            # The reader left; the model did not fail. Answering "şu an yanıt
            # veremiyor" and logging an error here would count every closed
            # tab as an outage.
            raise
        except Exception as exc:
            logger.error("Assistant tool loop failed: %s", exc)
            # Not the reader's fault, so not "rephrase your question": from
            # 2026-09-22 every request failed with a 400 from the model and
            # that is exactly what she was told (D3).
            loop = ToolLoopResult(text=self._model_hata_cevabi())
            safety_flags.append("error:model_unavailable")

        if not loop.text.strip():
            # The loop can legitimately return empty text — a model asked with
            # its tools withdrawn is not obliged to say anything. Without this
            # the reader gets a blank reply, which is worse than an honest one:
            # measured during Task 4, a budget-exhausted loop yields text="".
            logger.warning("Assistant produced no text (budget_exhausted=%s)",
                           loop.budget_exhausted)
            loop.text = self._fallback_answer(user_query)

        answer, citations, dropped = self._finalize_citations(
            loop.text, loop.citations)

        # Eski chat() bu bayrağı zayıf retrieval'dan set ediyordu. Retrieval ön
        # adımı kalkıyor ama bayrağın anlamı kalkmıyor: cevabın arkasında kaynak
        # yoksa okur bunu bilmeli. Yeni mimarideki karşılığı, çözülmüş atıf
        # listesinin boş olmasıdır.
        if not citations:
            safety_flags.append("warning:limited_confidence")

        answer += self.policy.guidance_suffix(safety_flags)

        latency_ms = int((time.perf_counter() - start) * 1000)
        payload = {
            "answer": answer,
            "citations": citations,
            "safety_flags": sorted(set(safety_flags)),
            "plan_blocks": [],
            "intent": intent,
            "session_id": session_id,
            # The last switch suggestion mod_oner made, without its event name;
            # the stream also sends it as it happens. None when there was none.
            "mode_suggestion": next(
                ({k: v for k, v in o.items() if k != "event"} for o in reversed(loop.olaylar)
                 if o.get("event") == "mode_suggestion"), None),
            "meta": {
                "model": self.llm.last_model_used or self.llm.model,
                "provider": "anthropic",
                "usage": dict(loop.usage),
                "tier": tier,
                "ogretmen": ogretmen,
                "tool_calls": loop.tool_calls,
                "dropped_citations": dropped,
                "degraded": self.registry.degraded(),
                "budget_exhausted": loop.budget_exhausted,
                "retrieval_count": len(citations),
                "latency_ms": latency_ms,
                "index_generated_at": self._meta_generated_at(),
            },
        }

        self._write_metric({
            "type": "chat", "session_id": session_id, "intent": intent,
            "tier": tier, "ogretmen": ogretmen, "latency_ms": latency_ms,
            "citations": len(citations),
            "tool_calls": len(loop.tool_calls),
            "model": payload["meta"]["model"],
            "usage": dict(loop.usage),
            "safety_flags": payload["safety_flags"],
            "timestamp": _utcnow_naive().isoformat() + "Z",
        })
        return payload

    def chat_events(self, **kwargs: Any) -> Iterator[dict[str, Any]]:
        """chat(), but announcing each tool as it runs, in real time.

        The tool loop can hold the request open for several seconds. Saying
        which source is being consulted is both a trust signal and, for this
        reader, the visible-time cue the interface is meant to provide — and
        that only holds if the event actually reaches the reader while the
        tool is running, not after chat() has already returned and the
        answer is sitting there waiting to be replayed alongside it.

        chat() is synchronous by design (it has other callers outside the
        stream), so it runs here on a dedicated worker thread. Its dispatch
        wrapper puts a {"event": ...} dict on a queue.Queue immediately
        before and after each real tool call; this generator drains that
        queue and yields each item the moment it arrives, `queue.Queue.get`
        blocking (without holding the GIL) between them. That is the whole
        mechanism — no polling, no fixed delay.

        Per-call, not shared: the dispatch wrapper is passed to chat() as an
        argument (see chat()'s `dispatch` parameter) rather than assigned
        onto self.registry.dispatch. AssistantRuntime is a per-process
        singleton and gthread workers (this task) make concurrent
        chat_events() calls genuinely possible; a shared, mutated
        self.registry.dispatch would let one caller's tool names leak into
        another caller's stream, or leave the registry permanently wrapped
        in a stale closure if two calls' try/finally blocks interleave.
        Passing the wrapper as a plain local closure, read from
        self.registry.dispatch but never written back to it, means every
        concurrent call gets its own — nothing shared, nothing to race.
        """
        events: "queue.Queue[dict[str, Any] | object]" = queue.Queue()
        _DONE = object()

        # Set when the consumer stops reading — either normally, or because
        # the SSE client went away and the generator was closed. See the
        # try/finally around the drain loop below.
        cancelled = threading.Event()

        # Read once, per call — never assigned back onto the registry.
        real_dispatch = functools.partial(
            self.registry.dispatch, ilerleme_izni=kwargs.get("ilerleme_izni") is True,
            okur=kwargs.get("okur", "bilinmiyor"),
            ogretmen=kwargs.get("ogretmen", assistant_skills.GENEL),
            mod_onerisi=kwargs.get("mod_onerisi", True))

        # First suggestion wins here too (review round 2, finding NB2): without
        # this, a model calling mod_oner twice in one answer put two
        # mode_suggestion events on the SSE stream, while chat()'s own payload
        # (deduped in chat_with_tools) carried only one — the stream and the
        # final /chat-shaped payload must agree.
        yayinlanan_olaylar: set[str] = set()

        def announcing(name: str, args: dict[str, Any]) -> Any:
            if cancelled.is_set():
                raise _StreamAbandoned()
            events.put({"event": "tool_start", "name": name})
            outcome = real_dispatch(name, args)
            events.put({"event": "tool_end", "name": name,
                        "ok": bool(outcome.ok)})
            if outcome.ok and outcome.olay:
                ad = outcome.olay.get("event")
                if ad not in yayinlanan_olaylar:
                    # mod_oner's suggestion reaches the reader as it happens.
                    yayinlanan_olaylar.add(ad)
                    events.put(dict(outcome.olay))
            if cancelled.is_set():
                raise _StreamAbandoned()
            return outcome

        def writing(parca: str) -> None:
            # Also a cancellation point: with the text streamed, a closed tab
            # stops a long answer mid-sentence, not only at a tool boundary.
            if cancelled.is_set():
                raise _StreamAbandoned()
            events.put({"event": "answer_delta", "text": parca})

        def reset() -> None:
            events.put({"event": "answer_reset"})

        outcome_box: dict[str, Any] = {}

        def run() -> None:
            try:
                outcome_box["payload"] = self.chat(
                    dispatch=announcing, on_delta=writing, on_reset=reset, **kwargs)
            except _StreamAbandoned:
                # Nobody is listening. Not an error, and deliberately not
                # recorded in outcome_box — there is no caller left to
                # re-raise it to.
                pass
            except BaseException as exc:  # noqa: BLE001 — re-raised on the caller's thread below
                outcome_box["error"] = exc
            finally:
                events.put(_DONE)

        worker = threading.Thread(
            target=run, name="assistant-chat-events", daemon=True)
        worker.start()

        try:
            while True:
                item = events.get()
                if item is _DONE:
                    break
                yield item
        finally:
            # Runs on the normal path (where the worker has already
            # finished and this is a no-op) and on GeneratorExit, which is
            # what a disconnected SSE client raises at the yield above.
            # Without it the worker kept running the whole remaining tool
            # loop for an answer nobody would read.
            cancelled.set()

        worker.join()

        if "error" in outcome_box:
            raise outcome_box["error"]

        yield {"event": "answer", "payload": outcome_box["payload"]}

    def _build_conversation(
        self,
        messages: list[dict[str, Any]],
        user_query: str,
        intent: str,
        safety_flags: list[str],
        okur: str = "bilinmiyor",
        ogretmen: str = assistant_skills.GENEL,
    ) -> list[dict[str, str]]:
        """System prompt plus recent turns.

        Retrieved context is deliberately absent: it used to be pasted in here
        whether or not the question called for it, which is how raw EBA OCR
        ended up under every answer. Evidence now enters through the tools.

        Today's date goes in the user turn, not the system prompt: the system
        block is cached, and a clock in it would miss the cache every minute.
        """
        from src.assistant_tools import bugun_satiri
        sistem = [{"role": "system", "content": self._system_prompt()}]
        skill = self.skills.get(ogretmen)
        if skill is not None:
            # A second block after the base prompt, which stays byte-identical
            # in every mode (spec §1 "Modele bağlama").
            sistem.append({"role": "system", "content": skill.sistem_blogu()})
        return [
            *sistem,
            *[
                # Only "assistant" stays itself. A client-sent "system" turn
                # must never become a system block of ours.
                {"role": "assistant" if m.get("role") == "assistant" else "user",
                 "content": str(m.get("content", ""))[:2000]}
                for m in messages[-3:] if isinstance(m, dict)
            ],
            {"role": "user", "content": (
                f"{bugun_satiri(datetime.now())}\n"
                f"Soran: {self._SORAN.get(okur, self._SORAN['bilinmiyor'])}\n"
                f"Soru türü: {intent}\n"
                f"Güvenlik: {', '.join(safety_flags) if safety_flags else 'yok'}\n\n"
                f"Soru: {user_query}"
            )},
        ]

    # The "Soran:" line of the user turn; the prompt's "## Hitap" reads it.
    # In the user turn rather than the system prompt, which is cached.
    _SORAN = {
        "ogrenci": "Işık",
        "aile": "Işık'ın ailesinden biri",
        "bilinmiyor": "bilinmiyor",
    }

    @staticmethod
    def _model_hata_cevabi() -> str:
        return (
            "TEDY Asistanı şu an yanıt veremiyor. Sorun senin sorunda değil; "
            "bağlantıda ya da ayarlarda. Biraz sonra yeniden dene, sürerse "
            "ailene haber ver."
        )

    @staticmethod
    def _fallback_answer(user_query: str) -> str:
        return (
            "Şu anda bu soruya cevap üretemedim. Soruyu biraz daha belirgin "
            f"(ders/konu/tarih) biçimde tekrar gönderir misin?\n\n"
            f"Sorduğun: {user_query}"
        )

    def study_plan(
        self,
        messages: list[dict[str, Any]],
        session_id: str = "",
        context_filters: dict[str, Any] | None = None,
        ilerleme_izni: bool = False,
        okur: str = "bilinmiyor",
    ) -> dict[str, Any]:
        out = self.chat(
            messages=messages,
            session_id=session_id,
            context_filters=context_filters,
            force_deep=True,
            ilerleme_izni=ilerleme_izni,
            okur=okur,
            mod_onerisi=False,  # /plan has no switch button (spec: B1 is /stream and /chat only)
        )
        out["intent"] = "study_plan"
        out["plan_blocks"] = self._build_rule_based_plan(
            self._latest_user_message(messages))
        return out

    def models(self) -> list[dict[str, Any]]:
        return [
            {
                "id": name,
                "object": "model",
                "created": 0,
                "owned_by": "anthropic",
            }
            for name in [self.llm.model]
        ]

    def openai_chat_completion(
        self,
        request_data: dict[str, Any],
    ) -> dict[str, Any]:
        messages = request_data.get("messages", [])
        if not isinstance(messages, list):
            messages = []

        session_id = str(request_data.get("session_id", "")).strip()
        context_filters = request_data.get("context_filters")
        if not isinstance(context_filters, dict):
            context_filters = {}

        temperature = float(request_data.get("temperature", 0.2) or 0.2)
        stream = bool(request_data.get("stream", False))
        if stream:
            raise ValueError("stream=true desteklenmiyor")

        # API-key callers are integrations, not people: this path never passes ilerleme_izni,
        # so module progress never reaches it, whatever the request body says (plan K-S6).
        plan_mode = bool(request_data.get("plan", False))
        if plan_mode:
            out = self.study_plan(messages=messages, session_id=session_id, context_filters=context_filters)
        else:
            out = self.chat(
                messages=messages,
                session_id=session_id,
                context_filters=context_filters,
                temperature=temperature,
                mod_onerisi=False,  # /v1 is an API-key client: no switch button either
            )

        answer = out.get("answer", "")
        prompt_tokens = self._estimate_tokens(str(messages))
        completion_tokens = self._estimate_tokens(answer)

        used_model = str(
            out.get("meta", {}).get("model") or self.llm.model
        )
        return {
            "id": f"chatcmpl-{hashlib.md5((session_id + str(time.time())).encode()).hexdigest()[:16]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": used_model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": answer,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            "citations": out.get("citations", []),
            "safety_flags": out.get("safety_flags", []),
            "plan_blocks": out.get("plan_blocks", []),
            "intent": out.get("intent", "qa"),
            "meta": out.get("meta", {}),
        }

    def _build_rule_based_plan(self, user_query: str) -> list[dict[str, Any]]:
        scraped = self._load_scraped_data()
        homework_rows = (
            scraped.get("odevlerim", {})
            .get("homework", {})
            .get("rows", [])
        )
        if not isinstance(homework_rows, list):
            homework_rows = []

        due_items: list[tuple[datetime, dict[str, Any]]] = []
        for row in homework_rows:
            if not isinstance(row, dict):
                continue
            due_raw = str(row.get("Ödev Son Teslim Tarihi", "")).strip()
            due_dt = self._parse_tr_datetime(due_raw)
            if due_dt is None:
                continue
            due_items.append((due_dt, row))

        due_items.sort(key=lambda x: x[0])

        now = datetime.now()
        seven_days = now + timedelta(days=7)
        picked = [x for x in due_items if x[0] <= seven_days][:10]

        blocks: list[dict[str, Any]] = []
        for due_dt, row in picked:
            ders = str(row.get("Ders Adı", "Genel")).strip() or "Genel"
            title = str(row.get("Ödev Başlığı", "Ödev")).strip() or "Ödev"
            days_left = max(0, (due_dt.date() - now.date()).days)
            mins = 30 if days_left >= 5 else 45 if days_left >= 2 else 60
            blocks.append({
                "type": "homework",
                "title": f"{ders}: {title}",
                "day": due_dt.strftime("%Y-%m-%d"),
                "estimated_minutes": mins,
                "actions": [
                    "Konu tekrarını tamamla",
                    "Ödev çözümünü bitir",
                    "Son 10 dk öz-kontrol yap",
                ],
                "rationale": "Teslim tarihine göre önceliklendirildi",
            })

        # Add practice blocks when grades exist, but never inferred from a
        # gelişim report still on an earlier school year (final review of
        # docs/superpowers/plans/2026-09-28-pano-eksiklikleri.md, Minor 5):
        # such a report's "1. Sınav"/"DİKP" columns are last year's, not a
        # weakness to build this week's plan around. `notlar`, `/api/exams`
        # and the BM25 NOTLAR paragraph already share this same check.
        from src.assistant_tools import onceki_yil_raporu_mu
        gelisim = scraped.get("gelisim_raporu", {})
        gelisim = gelisim if isinstance(gelisim, dict) else {}
        grades = gelisim.get("grades", [])
        onceki_yil = onceki_yil_raporu_mu(
            gelisim.get("semester"), _guncel_ogretim_yili_dosyadan(self.config.output_dir))
        if isinstance(grades, list) and grades and not onceki_yil:
            weak_courses = self._infer_weak_courses(grades)
            for course in weak_courses[:2]:
                blocks.append({
                    "type": "assessment",
                    "title": f"{course} kısa ölçme-değerlendirme",
                    "day": (now + timedelta(days=2)).strftime("%Y-%m-%d"),
                    "estimated_minutes": 35,
                    "actions": [
                        "10 soru mini deneme çöz",
                        "Yanlış analizini deftere çıkar",
                        "Eksik kazanımı tekrar et",
                    ],
                    "rationale": "Not trendinde iyileştirme hedefi",
                })

        if not blocks:
            # Fallback generic schedule.
            for i in range(5):
                d = now + timedelta(days=i)
                blocks.append({
                    "type": "generic",
                    "title": "Günlük odak çalışma",
                    "day": d.strftime("%Y-%m-%d"),
                    "estimated_minutes": 45,
                    "actions": [
                        "20 dk konu tekrarı",
                        "20 dk soru çözümü",
                        "5 dk öz değerlendirme",
                    ],
                    "rationale": "Veri yetersizliğinde standart plan",
                })

        # Basic personalization from user query.
        if "sınav" in user_query.lower() or "yazılı" in user_query.lower():
            for b in blocks[:3]:
                b["actions"].append("Günün sonunda 10 dk sınav provası yap")

        return blocks[:12]

    def _infer_weak_courses(self, grades: list[dict[str, Any]]) -> list[str]:
        scored: list[tuple[str, float]] = []
        for row in grades:
            if not isinstance(row, dict):
                continue
            course = str(row.get("Ders", "")).strip()
            if not course:
                continue
            vals: list[float] = []
            for k in ["1. Sınav", "2. Sınav", "3. Sınav", "DİKP/Performans-1", "DİKP/Performans-2", "DİKP/Performans-3"]:
                v = str(row.get(k, "")).strip().replace(",", ".")
                if not v or v == "-":
                    continue
                try:
                    vals.append(float(v))
                except ValueError:
                    continue
            if vals:
                scored.append((course, sum(vals) / len(vals)))
        scored.sort(key=lambda x: x[1])
        return [c for c, _ in scored]

    def _latest_user_message(self, messages: list[dict[str, Any]]) -> str:
        for msg in reversed(messages):
            if not isinstance(msg, dict):
                continue
            if str(msg.get("role", "")).lower() == "user":
                return str(msg.get("content", "")).strip()
        return ""

    def _classify_intent(self, query: str) -> str:
        q = query.lower()
        if any(k in q for k in ("çalışma plan", "haftalık plan", "günlük plan", "program hazırla")):
            return "study_plan"
        if any(k in q for k in ("ödev", "sınav", "program", "not", "duyuru")):
            return "data_query"
        if any(k in q for k in ("pedagoji", "öğrenme psikolojisi", "motivasyon", "ölçme", "değerlendirme")):
            return "expert_guidance"
        return "general"

    def _has_strong_retrieval_support(self, results: list[dict[str, Any]]) -> bool:
        if not results:
            return False

        min_bm25 = float(os.environ.get("ASSISTANT_MIN_SUPPORT_BM25", "0.05"))
        min_score = float(os.environ.get("ASSISTANT_MIN_SUPPORT_SCORE", "0.45"))
        min_vector = float(os.environ.get("ASSISTANT_MIN_SUPPORT_VECTOR", "0.72"))

        max_bm25 = 0.0
        max_score = 0.0
        max_vector = 0.0
        for r in results:
            try:
                max_bm25 = max(max_bm25, float(r.get("bm25", 0.0) or 0.0))
            except (TypeError, ValueError):
                pass
            try:
                max_score = max(max_score, float(r.get("score", 0.0) or 0.0))
            except (TypeError, ValueError):
                pass
            try:
                max_vector = max(max_vector, float(r.get("vector", 0.0) or 0.0))
            except (TypeError, ValueError):
                pass

        if max_bm25 >= min_bm25:
            return True
        if max_score >= min_score and max_vector >= min_vector:
            return True
        return False

    def _meta_generated_at(self) -> str:
        meta = self._load_json(self.config.meta_path, {})
        if isinstance(meta, dict):
            return str(meta.get("generated_at", ""))
        return ""

    def _is_context_stale(self) -> bool:
        meta = self._load_json(self.config.meta_path, {})
        generated_at = ""
        if isinstance(meta, dict):
            generated_at = str(meta.get("generated_at", "")).strip()
        if not generated_at:
            return True

        try:
            if generated_at.endswith("Z"):
                generated_at = generated_at[:-1]
            idx_dt = datetime.fromisoformat(generated_at)
        except ValueError:
            return True

        health = self._load_json(self.config.output_dir / "health.json", {})
        health_ts = ""
        if isinstance(health, dict):
            health_ts = str(health.get("timestamp", "")).strip()
        if health_ts:
            try:
                # Compare instants, not wall clocks. The index stamp is UTC
                # ("…Z"); health.json's is naive local time, which since
                # 2026-09-24 is Istanbul (src/env_loader.py). Stripping the zone
                # off both made every index look three hours older than the
                # sync, and every answer said "Veriler güncel olmayabilir".
                ref = datetime.fromisoformat(health_ts.replace("Z", "+00:00"))
                ref = ref.astimezone(timezone.utc) if ref.tzinfo else ref.astimezone().astimezone(timezone.utc)
                if idx_dt.replace(tzinfo=timezone.utc) < ref:
                    return True
            except ValueError:
                pass

        delta = _utcnow_naive() - idx_dt
        return delta.total_seconds() > self.config.stale_after_minutes * 60

    def _estimate_tokens(self, text: str) -> int:
        # Rough token estimator for reporting.
        if not text:
            return 0
        return max(1, int(len(text) / 4))

    def _parse_tr_datetime(self, value: str) -> datetime | None:
        value = value.strip()
        for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(value, fmt)
                if fmt in ("%d.%m.%Y", "%Y-%m-%d"):
                    dt = dt.replace(hour=23, minute=59)
                return dt
            except ValueError:
                continue
        return None

    def _load_retriever(self) -> HybridRetriever:
        chunks_mtime = self.config.chunks_path.stat().st_mtime if self.config.chunks_path.exists() else 0.0
        if self._retriever and chunks_mtime == self._retriever_cache_mtime:
            return self._retriever

        chunks = self._load_json(self.config.chunks_path, [])
        if not isinstance(chunks, list):
            chunks = []
        # Final review, finding 2: a persisted chunk whose path a rule change
        # (or a stale pre-migration index) would no longer discover must
        # never be served, even for the one request window before the next
        # reindex() — see AssistantIndexer.is_path_currently_included.
        chunks = [c for c in chunks if isinstance(c, dict)
                  and self.indexer.is_path_currently_included(str(c.get("path", "")))]
        embeddings = self._load_json(self.config.embeddings_path, {})
        if not isinstance(embeddings, dict):
            embeddings = {}

        self._retriever = HybridRetriever(
            chunks=chunks,
        )
        self._retriever_cache_mtime = chunks_mtime
        return self._retriever

    def _load_aile_retriever(self) -> HybridRetriever:
        """Same lazy, mtime-cached load as `_load_retriever`, over the
        separate content/pedagoji index (Görev 5) — filtered the same way,
        symmetrically, against the family index's own (narrower) rules."""
        chunks_mtime = (self.aile_config.chunks_path.stat().st_mtime
                        if self.aile_config.chunks_path.exists() else 0.0)
        if self._aile_retriever and chunks_mtime == self._aile_retriever_cache_mtime:
            return self._aile_retriever

        chunks = self._load_json(self.aile_config.chunks_path, [])
        if not isinstance(chunks, list):
            chunks = []
        chunks = [c for c in chunks if isinstance(c, dict)
                  and self.aile_indexer.is_path_currently_included(str(c.get("path", "")))]

        self._aile_retriever = HybridRetriever(chunks=chunks)
        self._aile_retriever_cache_mtime = chunks_mtime
        return self._aile_retriever

    def _load_scraped_data(self) -> dict[str, Any]:
        return self._load_json(self.config.output_dir / "scraped_data.json", {})

    def _load_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def _write_metric(self, payload: dict[str, Any]) -> None:
        try:
            self.config.metrics_path.parent.mkdir(parents=True, exist_ok=True)
            with self.config.metrics_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            pass

    _MARKER_RE = re.compile(r"\[S(\d+)\]")
    # A section starts at a Markdown heading or at a line that is nothing but
    # bold text — the chat renders both as headings.
    _BOLUM_RE = re.compile(r"^\s*(#{1,6}\s|\*\*[^*]+\*\*:?\s*$)")

    @classmethod
    def _tekrari_topla(cls, text: str) -> str:
        """Drop a marker that repeats the one just before it in its section.

        Live 2026-09-25: an answer drawn wholly from `odev_listesi` put a chip
        reading "1" after every sentence and list item. The first marker
        already ties the section to its source — the prompt asks for exactly
        that, and the model did not comply. A different source in between, or
        a new section, brings the marker back.
        """
        son: str | None = None
        satirlar = []
        for satir in text.split("\n"):
            if cls._BOLUM_RE.match(satir):
                son = None

            def ele(m: "re.Match[str]") -> str:
                nonlocal son
                if m.group(0) == son:
                    return ""
                son = m.group(0)
                return son

            satirlar.append(cls._MARKER_RE.sub(ele, satir))
        return "\n".join(satirlar)

    def _finalize_citations(
        self,
        text: str,
        citations: list[dict[str, Any]],
    ) -> tuple[str, list[dict[str, Any]], int]:
        """Resolve the model's [S1] markers against the sources tools returned.

        The model's markers are resolved in tool-return order — the numbers it
        was shown — and then renumbered in the order the reader meets them.
        Live 2026-09-24: three tools returned sources, the answer cited only
        the third, and the reader saw a lone chip reading "3". A marker
        pointing at nothing is removed from the prose and counted, rather than
        left to imply evidence that does not exist — and rather than being
        stripped wholesale in the frontend, which is what previously severed
        text from sources.
        """
        indexed = {i: dict(c) for i, c in enumerate(citations, start=1)}
        renumbered: dict[int, int] = {}
        dropped = 0

        def replace(match: "re.Match[str]") -> str:
            nonlocal dropped
            n = int(match.group(1))
            if n in indexed:
                if n not in renumbered:
                    renumbered[n] = len(renumbered) + 1
                return f"[S{renumbered[n]}]"
            dropped += 1
            return ""

        cleaned = self._tekrari_topla(self._MARKER_RE.sub(replace, text))
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r" +([,.;:!?])", r"\1", cleaned).strip()

        kept = []
        for n, k in renumbered.items():
            indexed[n]["id"] = f"S{k}"
            kept.append(indexed[n])
        return cleaned, kept, dropped


def perform_incremental_reindex(project_root: str | os.PathLike[str]) -> dict[str, Any]:
    """Convenience function for sync pipeline hooks.

    `skills={}` on purpose (review round 2, finding 4): reindexing the BM25
    file index needs no teacher skill loaded, and this is cron's own path —
    a broken SKILL.md must not freeze every sync's index refresh until
    someone notices and fixes the skill file. The dashboard's own runtime
    (`_assistant_runtime` in dashboard_api.py) is unaffected and still loads
    the real skills, so a broken one still blocks the chat surface itself.
    """
    runtime = AssistantRuntime(project_root, skills={})
    return runtime.reindex(incremental=True)
