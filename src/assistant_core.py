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
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests as http_requests

from src import claude_api
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
EMBED_TARGET_EXTENSIONS = {".md", ".txt", ".json", ".csv", ".html", ".htm", ".pdf"}

# Whitelist: scrape data + downloaded educational content
DEFAULT_INCLUDE_DIRS = {"output", "content"}

DEFAULT_EXCLUDED_DIRS = {
    "__pycache__",
    "assistant_index",
    # edupedia (spec §4.2): ted-mcp's catalog, immutable drafts and run pages. Published modules
    # reach the model only through modul_ara (src/assistant_modules.py); run pages carry
    # third-party textbook and OER text that must not enter a prompt without kaynak_verisi.
    "output/modules",
    "output/edupedia_drafts",
    "output/edupedia_runs",
}

DEFAULT_EXCLUDED_FILE_PATTERNS = {
    "*.png",
    "*.html",
    "*.jsonl",
    "*.log",
    "sync.log",
    "classroom_sync.json",
    "homework_student_done.json",
    "health.json",
    "photo_homework.json",
    "private_lessons.json",
    # Per-person module progress (spec §6.4), lock sidecars, the media ledger and the ted-mcp
    # OAuth store: none of it is school data, and raw progress must never reach a prompt.
    "module_progress.json",
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
}

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
    chunk_size: int
    chunk_overlap: int
    retrieval_k: int
    stale_after_minutes: int
    include_dirs: set[str]
    excluded_dirs: set[str]
    excluded_file_patterns: set[str]

    @classmethod
    def from_project_root(cls, project_root: str | os.PathLike[str]) -> "AssistantConfig":
        root = Path(project_root).resolve()
        output_dir = root / "output"
        index_dir = output_dir / "assistant_index"
        index_dir.mkdir(parents=True, exist_ok=True)

        max_file_size_mb = int(os.environ.get(
            "ASSISTANT_MAX_FILE_SIZE_MB", "250"))
        max_chunks = int(os.environ.get(
            "ASSISTANT_MAX_CHUNKS", "15000"))

        includes = set(DEFAULT_INCLUDE_DIRS)
        custom_includes = os.environ.get(
            "ASSISTANT_INCLUDE_DIRS", "").strip()
        if custom_includes:
            includes = {x.strip() for x in
                        custom_includes.split(",") if x.strip()}
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
    def _split(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
        """System text apart; turns as the Messages API wants them.

        The API rejects a conversation that opens on the assistant and any
        empty text block. The runtime keeps the last three turns of history,
        which can start mid-dialogue, so leading assistant turns are dropped.
        """
        system = "\n".join(str(m.get("content", "")) for m in messages
                           if m.get("role") == "system" and m.get("content"))
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

    def _request(self, system: str, turns: list[dict[str, Any]], tier: str,
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
        if system:
            # Render order is tools -> system -> messages, so one breakpoint on
            # the system block caches the tool list and the prompt together:
            # every round of a tool loop re-sends exactly that prefix.
            params["system"] = [{"type": "text", "text": system,
                                 "cache_control": {"type": "ephemeral"}}]
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
    ) -> ToolLoopResult:
        """Run the model until it answers, dispatching tools it asks for.

        With `on_delta` every request is streamed and its text handed over as
        it arrives. Text a round writes before calling a tool is not part of
        the answer (the answer is the last round's text), so `on_reset` is
        called when such a round ends — the reader drops what was shown.

        The round budget is a hard stop: a model that keeps calling tools would
        otherwise hold a worker open indefinitely. It is checked before each
        dispatch, not after — one turn can ask for more calls than remain, and
        a call past the limit is never run but still answered, so the model
        knows what did not happen (the API requires a result for every call
        anyway). Once the budget is spent the model is asked once more with
        tool_choice none — tools withdrawn, tool list kept so the cached prefix
        survives — and answers from the evidence already gathered.
        """
        from src.assistant_tools import ToolOutcome

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

        for _round in range(max_rounds):
            resp = self._request(system, turns, tier, out.usage, tools=tools,
                                 on_delta=on_delta)
            uses = [b for b in (resp.content or []) if getattr(b, "type", "") == "tool_use"]
            if not uses:
                out.text = self._text(resp)
                return out
            if on_reset is not None and self._text(resp):
                on_reset()

            # Back exactly as received: thinking blocks are signed and must not
            # be edited, and the tool_result ids must match these tool_use ids.
            turns.append({"role": "assistant", "content": resp.content})
            results: list[dict[str, Any]] = []
            for use in uses:
                if len(out.tool_calls) >= max_rounds:
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
                if outcome.ok:
                    first = len(out.citations) + 1
                    out.citations.extend(outcome.citations)
                    # The numbers the model sees and the ones
                    # _finalize_citations assigns come from the same counter;
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
                                "content": (body or "").strip()[:4000] or "(sonuç boş)"})
            turns.append({"role": "user", "content": results})

            if len(out.tool_calls) >= max_rounds:
                out.budget_exhausted = True
                final = self._request(system, turns, tier, out.usage, tools=tools,
                                      tool_choice={"type": "none"}, on_delta=on_delta)
                out.text = self._text(final)
                return out

        return out


HybridChatRouter = None  # Removed — Gemini-only


# ── Semantic JSON → readable text ──────────────────────────

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
        return _fmt_scraped_data(data)
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


def _fmt_scraped_data(data: dict) -> str:
    parts: list[str] = []

    # Ödevler
    hw_rows = (data.get("odevlerim", {})
               .get("homework", {})
               .get("rows", []))
    if hw_rows:
        parts.append("=== ÖDEVLER ===")
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
                desc = detail.get("description", "")
            line = f"{ders} | {baslik}"
            if tarih:
                line += f" | Son teslim: {tarih}"
            if durum:
                line += f" | Durum: {durum}"
            if desc:
                line += f" | {desc[:200]}"
            parts.append(line)

    # Ders programı
    prog = data.get("ders_programi", [])
    if isinstance(prog, list) and prog:
        parts.append("\n=== DERS PROGRAMI ===")
        for week in prog:
            if not isinstance(week, dict):
                continue
            label = week.get("week_label", "")
            sched = week.get("schedule", {})
            if not isinstance(sched, dict):
                continue
            parts.append(f"Hafta: {label}")
            for day, slots in sched.items():
                if isinstance(slots, list):
                    for s in slots:
                        if isinstance(s, dict):
                            parts.append(
                                f"  {day} {s.get('saat','')} "
                                f"{s.get('ders','')}")

    # Takvim etkinlikleri
    takvim = data.get("takvim", [])
    if isinstance(takvim, list) and takvim:
        parts.append("\n=== TAKVİM ===")
        for ev in takvim:
            if not isinstance(ev, dict):
                continue
            t = ev.get("title", "")
            s = ev.get("start", "")[:16]
            parts.append(f"{s} | {t}")

    # Notlar
    gelisim = data.get("gelisim_raporu", {})
    grades = (gelisim.get("grades", [])
              if isinstance(gelisim, dict) else [])
    if grades:
        parts.append("\n=== NOTLAR ===")
        semester = gelisim.get("semester", "")
        if semester:
            parts.append(f"Dönem: {semester}")
        for g in grades:
            if not isinstance(g, dict):
                continue
            ders = g.get("Ders", "")
            cols = []
            for k, v in g.items():
                if k != "Ders" and v and v != "-":
                    cols.append(f"{k}: {v}")
            if cols:
                parts.append(f"{ders} | {' | '.join(cols)}")

    # Ders içerikleri
    ders_ic = data.get("ders_icerikleri", {})
    if isinstance(ders_ic, dict) and ders_ic:
        parts.append("\n=== DERS İÇERİKLERİ ===")
        for course, items in ders_ic.items():
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict):
                    title = item.get(
                        "title", item.get("konu", ""))
                    parts.append(f"{course} | {title}")
                elif isinstance(item, str):
                    parts.append(f"{course} | {item}")

    # ÖGEP
    ogep = data.get("ogep", {})
    sessions = (ogep.get("sessions", [])
                if isinstance(ogep, dict) else [])
    if sessions:
        parts.append("\n=== ÖGEP ===")
        for s in sessions:
            if isinstance(s, dict):
                name = s.get("ÖGEP Adı", "")
                date = s.get("Başlangıç", "")
                parts.append(f"{name} | {date}")

    # Takım çalışmaları
    takim = data.get("takim_calismalari", {})
    activities = (takim.get("activities", [])
                  if isinstance(takim, dict) else [])
    if activities:
        parts.append("\n=== TAKIM ÇALIŞMALARI ===")
        for a in activities:
            if isinstance(a, dict):
                name = a.get("Takım Adı", "")
                parts.append(name)

    # Duyurular
    duyuru = data.get("duyurular", {})
    items = (duyuru.get("announcements", [])
             if isinstance(duyuru, dict) else [])
    if items:
        parts.append("\n=== DUYURULAR ===")
        for d in items:
            if isinstance(d, dict):
                title = d.get("title", d.get("başlık", ""))
                date = d.get("date", d.get("tarih", ""))
                parts.append(f"{date} | {title}")

    return "\n".join(parts)


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
            text = self._extract_pdf_text(file_path)
            return {
                "text": text or self._metadata_only_text(rel_path, file_path, reason="pdf_no_text"),
                "source_kind": "pdf" if text else "metadata",
                "confidence": 0.8 if text else 0.2,
                "warnings": [] if text else ["pdf_no_text"],
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
            for page in reader.pages[:120]:
                t = page.extract_text() or ""
                if t.strip():
                    pages.append(t)
            if pages:
                return "\n\n".join(pages)
        except Exception:
            pass

        # Optional fallback to pdftotext if present.
        try:
            proc = subprocess.run(
                ["pdftotext", "-layout", str(file_path), "-"],
                capture_output=True,
                text=True,
                timeout=40,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout
        except Exception:
            pass

        return ""

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
        old_files = old_manifest.get("files", {}) if isinstance(old_manifest, dict) else {}

        old_chunks = self._load_json(self.config.chunks_path, [])
        if not isinstance(old_chunks, list):
            old_chunks = []
        old_embeddings = self._load_json(self.config.embeddings_path, {})
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
            new_manifest_files[rel_path] = file_record

            old_rec = old_files.get(rel_path) if isinstance(old_files, dict) else None
            can_reuse = bool(
                incremental
                and old_rec
                and old_rec.get("sha256") == sha
                and rel_path in old_chunks_by_path
            )

            if can_reuse:
                unchanged += 1
                file_chunks = old_chunks_by_path.get(rel_path, [])
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

            changed += 1
            extracted = self.adapters.extract(file_path, rel_path)
            text = str(extracted.get("text", ""))
            source_kind = str(extracted.get("source_kind", "text"))
            confidence = float(extracted.get("confidence", 0.5))
            warnings = extracted.get("warnings", [])
            if not isinstance(warnings, list):
                warnings = []

            chunks = self._chunk_text(text)
            if not chunks:
                chunks = [text[: self.config.chunk_size] if text else ""]

            for chunk_index, chunk_text in enumerate(chunks):
                if len(new_chunks) >= max_chunks:
                    break
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

        total_embedded = len(new_embeddings)
        meta = {
            "generated_at": _utcnow_naive().isoformat() + "Z",
            "incremental": incremental,
            "files_indexed": len(new_manifest_files),
            "chunks_indexed": len(new_chunks),
            "changed_files": changed,
            "unchanged_files": unchanged,
            "deleted_files": deleted,
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
            "version": 1,
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

    def _discover_files(self) -> list[Path]:
        """Discover files from whitelisted directories only."""
        files: list[Path] = []
        root = self.config.project_root
        idx_dir = self.config.index_dir.resolve()

        for inc_dir in sorted(self.config.include_dirs):
            scan_root = root / inc_dir
            if not scan_root.is_dir():
                continue
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
                        files.append(file_path)
                    except Exception:
                        continue

        files.sort(
            key=lambda p: p.relative_to(root).as_posix())
        return files

    def _is_excluded_dir(self, rel_dir: str) -> bool:
        normalized = rel_dir.strip("/")
        if not normalized:
            return False
        for ex in self.config.excluded_dirs:
            ex_norm = ex.strip("/")
            if normalized == ex_norm or normalized.startswith(ex_norm + "/"):
                return True
        return False

    def _is_excluded_file(self, rel_file: str) -> bool:
        normalized = rel_file.strip("/")
        if not normalized:
            return False
        base = Path(normalized).name
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
        return re.findall(r"[A-Za-z0-9ÇĞİÖŞÜçğıöşü_]+", text.lower())

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
                 odev_kaynagi: Callable[[], list[dict[str, Any]]] | None = None):
        self.config = AssistantConfig.from_project_root(
            project_root)
        self.llm = ClaudeClient()
        self.router = self.llm
        self._sinif_cache: tuple[float, str] = (-1.0, "")
        self.indexer = AssistantIndexer(self.config)
        self.policy = SafetyPolicy()

        self._retriever: HybridRetriever | None = None
        self._retriever_cache_mtime: float = 0.0

        from src.assistant_modules import ModuleIndex
        from src.assistant_tools import build_registry
        # Published edupedia modules (plan SP5 K-S1): read-only, per process, no index file.
        self.modules = ModuleIndex(self.config.output_dir)
        # odev_kaynagi: the homework rows Bugün shows (dashboard_api._canli_odevler).
        self.registry = build_registry(self._local_search, module_index=self.modules,
                                       odev_kaynagi=odev_kaynagi)

    def _local_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """The retriever, shaped as a tool the model can choose to call."""
        return self._load_retriever().search(query, top_k=top_k)

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
        "- Ödev sorusu (hangi ödevler var, ne zaman teslim, neyi yaptı, ne kaldı) → "
        "önce `odev_listesi`. Ödevin durumu için tek güvenilir kaynak odur: Bugün "
        "sayfasının gösterdiği listeyi, Işık'ın 'Yaptım' işaretleriyle verir. "
        "Işık'ın 'Yaptım' dediği bir ödevi yapılacak diye sunma. Teslim zamanını "
        "söylerken listedeki gün ve saati kullan; 'bu hafta', 'yarın' gibi sözleri "
        "sorudaki 'Bugün:' satırına göre çöz.\n"
        "- Işık'a özel diğer sorular (sınav, not, ders programı, duyuru) ve bir "
        "ödevin ayrıntısı → `ogrenci_verisi_ara`. Bu veriler yalnız orada bulunur.\n"
        "- Konu, kavram, müfredat, kazanım sorusu → `kazanim_ara`, "
        "`mufredat_ara`, `kitap_listele` + `kitap_sayfa`. MEB korpusu bu "
        "konularda tek otoritedir.\n"
        "- Görsel/şema açıklaman gerekiyorsa → `figur_ara`, sonra `figur_getir`.\n"
        "- Etkileşimli çalışma, yayınlanmış modül ya da 'bu konu/sınav için modül var mı' sorusu → "
        "`modul_ara`. Modül adı ve künyesi YALNIZ bu aracın sonucundan gelir; araç modül bulamadıysa "
        "bunu söyle, modül ya da bağlantı uydurma. Modülü önerdiğin cümleye aracın [S] numarasını koy; "
        "bağlantıyı kendin yazma — okur modülü Kaynaklar panelinden açar.\n"
        "- Soru hem Işık'ın kaydına hem bir konuya dokunuyorsa (örn. "
        "'ödevimdeki kesir konusunu anlat') iki aracı da çağır: önce "
        "`ogrenci_verisi_ara` ile somut kaydı al (hangi ödev, hangi konu, "
        "ne zaman), sonra oradan çıkan konuyla `kazanim_ara`/`mufredat_ara`'yı "
        "çağır; cevabı ikisini birleştirerek kur.\n"
        "- 'İkisini karıştırma' burada kaynakların karışmaması demektir, "
        "aracın tekliği değil: Işık'ın notunu müfredattan, kazanımı yerel "
        "dosyadan çıkarma.\n\n"

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
        "- Yanıtın sonuna ayrı kaynak listesi ekleme; atıf satır içindedir.\n"
        "- Işık'ın kaydı veya müfredat dışında genel bilgi sorulursa yanıtla, "
        "ama bunun Işık'ın kaydından veya müfredat kaynağından gelmediğini "
        "belirt ve o cümleye [S] atıfı ekleme; atıf yalnız araç çıktısına "
        "aittir.\n\n"

        "## Nasıl anlatırsın (DEHB-dostu)\n"
        "- İlk cümlede doğrudan cevabı ver.\n"
        "- Anlatımı 3–6 dakikada tüketilebilir parçalara böl; her parçanın "
        "kendi başlığı olsun.\n"
        "- Adımları numaralandır ve her adıma tahmini süre yaz — 'neredeyim' "
        "sorusunun cevabı görünür olsun.\n"
        "- Somut ol: ne yapılacak, ne zaman, ne kadar sürede.\n"
        "- Başarıyı önce söyle, eksiği sonra ve yapıcı biçimde.\n"
        "- Uzun paragraf yazma; madde işareti ve kısa cümle kullan.\n\n"

        "## Sınırlar\n"
        "- Modül ilerleme özetini yalnız soran kişiye aktar; ilerleme bilgisini (cevaplanan soru, "
        "doğru oranı, tamamlanma, son erişim) hiçbir zaman başka bir araca argüman olarak verme.\n"
        "- Klinik tanı koyma, tedavi önerme.\n"
        "- Riskli psikolojik durumda profesyonel destek yönlendirmesi yap."
    )

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
        try:
            moduller = self.modules.durum(yenile=True)
        except Exception as exc:  # noqa: BLE001 — the file index already succeeded; say what failed
            logger.error("module index rebuild failed: %s", type(exc).__name__)
            moduller = {"katalog": "hata", "hata": type(exc).__name__}
        return {**stats, "moduller": moduller}

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
    ) -> dict[str, Any]:
        # `dispatch`, if given, replaces self.registry.dispatch for this
        # call only. chat_events() (below) uses this to wrap tool calls
        # with per-call progress narration WITHOUT mutating shared state:
        # the registry is a per-process singleton, and gthread workers
        # (this task) mean two chat() calls can now genuinely overlap.
        # Passing the wrapper in as an argument keeps each call's
        # narration local to its own stack frame instead of racing
        # another call's over one shared attribute.
        start = time.perf_counter()

        user_query = self._latest_user_message(messages)
        safety_flags = self.policy.evaluate(user_query)
        intent = self._classify_intent(user_query)
        tier = self._tier_for(intent, force_deep)

        if self._is_context_stale():
            safety_flags.append("warning:stale_context")

        convo = self._build_conversation(messages, user_query, intent, safety_flags)

        try:
            # `temperature` stays in chat()'s signature for /v1 callers but is
            # not forwarded: Sonnet 5 rejects sampling parameters (400).
            loop = self.llm.chat_with_tools(
                messages=convo,
                declarations=self.registry.declarations(),
                # Module progress enters the model context only for a signed-in person (plan K-S6);
                # the caller decides, and only an exact True counts.
                dispatch=dispatch or functools.partial(
                    self.registry.dispatch, ilerleme_izni=ilerleme_izni is True),
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
            "meta": {
                "model": self.llm.last_model_used or self.llm.model,
                "provider": "anthropic",
                "usage": dict(loop.usage),
                "tier": tier,
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
            "tier": tier, "latency_ms": latency_ms, "citations": len(citations),
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
            self.registry.dispatch, ilerleme_izni=kwargs.get("ilerleme_izni") is True)

        def announcing(name: str, args: dict[str, Any]) -> Any:
            if cancelled.is_set():
                raise _StreamAbandoned()
            events.put({"event": "tool_start", "name": name})
            outcome = real_dispatch(name, args)
            events.put({"event": "tool_end", "name": name,
                        "ok": bool(outcome.ok)})
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
    ) -> list[dict[str, str]]:
        """System prompt plus recent turns.

        Retrieved context is deliberately absent: it used to be pasted in here
        whether or not the question called for it, which is how raw EBA OCR
        ended up under every answer. Evidence now enters through the tools.

        Today's date goes in the user turn, not the system prompt: the system
        block is cached, and a clock in it would miss the cache every minute.
        """
        from src.assistant_tools import bugun_satiri
        return [
            {"role": "system", "content": self._system_prompt()},
            *[
                {"role": str(m.get("role", "user")),
                 "content": str(m.get("content", ""))[:2000]}
                for m in messages[-3:] if isinstance(m, dict)
            ],
            {"role": "user", "content": (
                f"{bugun_satiri(datetime.now())}\n"
                f"Soru türü: {intent}\n"
                f"Güvenlik: {', '.join(safety_flags) if safety_flags else 'yok'}\n\n"
                f"Soru: {user_query}"
            )},
        ]

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
    ) -> dict[str, Any]:
        out = self.chat(
            messages=messages,
            session_id=session_id,
            context_filters=context_filters,
            force_deep=True,
            ilerleme_izni=ilerleme_izni,
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

        # Add practice blocks when grades exist.
        grades = scraped.get("gelisim_raporu", {}).get("grades", [])
        if isinstance(grades, list) and grades:
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
        embeddings = self._load_json(self.config.embeddings_path, {})
        if not isinstance(embeddings, dict):
            embeddings = {}

        self._retriever = HybridRetriever(
            chunks=chunks,
        )
        self._retriever_cache_mtime = chunks_mtime
        return self._retriever

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

    def _finalize_citations(
        self,
        text: str,
        citations: list[dict[str, Any]],
    ) -> tuple[str, list[dict[str, Any]], int]:
        """Resolve the model's [S1] markers against the sources tools returned.

        Markers are assigned in tool-return order. A marker pointing at nothing
        is removed from the prose and counted, rather than left to imply
        evidence that does not exist — and rather than being stripped wholesale
        in the frontend, which is what previously severed text from sources.
        """
        indexed = {i: dict(c) for i, c in enumerate(citations, start=1)}
        for i, c in indexed.items():
            c["id"] = f"S{i}"

        used: list[int] = []
        dropped = 0

        def replace(match: "re.Match[str]") -> str:
            nonlocal dropped
            n = int(match.group(1))
            if n in indexed:
                if n not in used:
                    used.append(n)
                return match.group(0)
            dropped += 1
            return ""

        cleaned = self._MARKER_RE.sub(replace, text)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r" +([,.;:!?])", r"\1", cleaned).strip()

        return cleaned, [indexed[n] for n in used], dropped


def perform_incremental_reindex(project_root: str | os.PathLike[str]) -> dict[str, Any]:
    """Convenience function for sync pipeline hooks."""
    runtime = AssistantRuntime(project_root)
    return runtime.reindex(incremental=True)
