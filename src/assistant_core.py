"""Local pedagogical assistant runtime for TEDY.

This module provides:
- Incremental repository indexing (full repo + output artefacts)
- File adapters (json/html/md/txt/code/pdf/image)
- Hybrid retrieval (BM25 + Ollama embeddings)
- Safety policy for educational psychology answers
- Chat + study plan generation
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import subprocess
import time
import fnmatch
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests as http_requests

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

DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".claude",
    ".roo",
    ".superpowers",
    ".vscode",
    ".venv",
    ".ollama-models",
    ".mypy_cache",
    ".pytest_cache",
    ".playwright-mcp",
    ".worktrees",
    "dashboard/node_modules",
    "dashboard/src",
    "dashboard/tests",
    "dashboard-dist",
    "__pycache__",
}

DEFAULT_EXCLUDED_FILE_PATTERNS = {
    ".env",
    ".env.*",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "Pipfile.lock",
    "*.pem",
    "*.key",
    "*.p12",
    "*.map",
    "*service-account*.json",
    "credentials.json",
    "token.json",
    "token_*.json",
    "output/*.jsonl",
}


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
    ollama_base_url: str
    ollama_chat_model: str
    ollama_chat_fallback_model: str
    ollama_embed_model: str
    ollama_chat_timeout_seconds: int
    ollama_embed_timeout_seconds: int
    ollama_embed_max_chars: int
    ollama_keep_alive: str
    enable_embeddings: bool
    enable_ocr: bool
    max_file_size_mb: int
    max_chunks: int
    chunk_size: int
    chunk_overlap: int
    retrieval_k: int
    vector_weight: float
    stale_after_minutes: int
    excluded_dirs: set[str]
    excluded_file_patterns: set[str]

    @classmethod
    def from_project_root(cls, project_root: str | os.PathLike[str]) -> "AssistantConfig":
        root = Path(project_root).resolve()
        output_dir = root / "output"
        index_dir = output_dir / "assistant_index"
        index_dir.mkdir(parents=True, exist_ok=True)

        max_file_size_mb = int(os.environ.get("ASSISTANT_MAX_FILE_SIZE_MB", "20"))
        max_chunks = int(os.environ.get("ASSISTANT_MAX_CHUNKS", "2000"))

        excluded = set(DEFAULT_EXCLUDED_DIRS)
        custom_excluded = os.environ.get("ASSISTANT_EXCLUDED_DIRS", "").strip()
        if custom_excluded:
            excluded.update(x.strip() for x in custom_excluded.split(",") if x.strip())
        excluded_files = set(DEFAULT_EXCLUDED_FILE_PATTERNS)
        custom_excluded_files = os.environ.get("ASSISTANT_EXCLUDED_FILES", "").strip()
        if custom_excluded_files:
            excluded_files.update(x.strip() for x in custom_excluded_files.split(",") if x.strip())

        return cls(
            project_root=root,
            output_dir=output_dir,
            index_dir=index_dir,
            manifest_path=index_dir / "manifest.json",
            chunks_path=index_dir / "chunks.json",
            embeddings_path=index_dir / "embeddings.json",
            meta_path=index_dir / "meta.json",
            metrics_path=output_dir / "assistant_metrics.jsonl",
            ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_chat_model=os.environ.get("ASSISTANT_CHAT_MODEL", "qwen2.5-coder:7b"),
            ollama_chat_fallback_model=os.environ.get("ASSISTANT_CHAT_FALLBACK_MODEL", "qwen2.5:14b"),
            ollama_embed_model=os.environ.get("ASSISTANT_EMBED_MODEL", "mxbai-embed-large"),
            ollama_chat_timeout_seconds=int(os.environ.get("ASSISTANT_OLLAMA_CHAT_TIMEOUT_SECONDS", "90")),
            ollama_embed_timeout_seconds=int(os.environ.get("ASSISTANT_OLLAMA_EMBED_TIMEOUT_SECONDS", "60")),
            ollama_embed_max_chars=int(os.environ.get("ASSISTANT_EMBED_MAX_CHARS", "1200")),
            ollama_keep_alive=os.environ.get("ASSISTANT_OLLAMA_KEEP_ALIVE", "30m").strip(),
            enable_embeddings=os.environ.get("ASSISTANT_ENABLE_EMBEDDINGS", "1") == "1",
            enable_ocr=os.environ.get("ASSISTANT_ENABLE_OCR", "0") == "1",
            max_file_size_mb=max_file_size_mb,
            max_chunks=max_chunks,
            chunk_size=int(os.environ.get("ASSISTANT_CHUNK_SIZE", "1400")),
            chunk_overlap=int(os.environ.get("ASSISTANT_CHUNK_OVERLAP", "220")),
            retrieval_k=int(os.environ.get("ASSISTANT_RETRIEVAL_K", "8")),
            vector_weight=float(os.environ.get("ASSISTANT_VECTOR_WEIGHT", "0.55")),
            stale_after_minutes=int(os.environ.get("ASSISTANT_STALE_AFTER_MINUTES", "90")),
            excluded_dirs=excluded,
            excluded_file_patterns=excluded_files,
        )


class OllamaClient:
    """Thin Ollama client with graceful failures."""

    def __init__(
        self,
        base_url: str,
        chat_model: str,
        fallback_chat_model: str,
        embed_model: str,
        chat_timeout_seconds: int = 25,
        embed_timeout_seconds: int = 60,
        embed_max_chars: int = 1200,
        keep_alive: str = "30m",
    ):
        self.base_url = base_url.rstrip("/")
        self.chat_model = chat_model
        self.fallback_chat_model = fallback_chat_model.strip()
        self.embed_model = embed_model
        self.chat_timeout_seconds = max(5, int(chat_timeout_seconds))
        self.embed_timeout_seconds = max(5, int(embed_timeout_seconds))
        self.embed_max_chars = max(300, int(embed_max_chars))
        self.keep_alive = keep_alive.strip()
        self.last_model_used = chat_model

    def available_models(self) -> list[str]:
        try:
            r = http_requests.get(f"{self.base_url}/api/tags", timeout=10)
            r.raise_for_status()
            payload = r.json()
            return [m.get("name", "") for m in payload.get("models", []) if m.get("name")]
        except Exception:
            models = [self.chat_model]
            if self.fallback_chat_model and self.fallback_chat_model != self.chat_model:
                models.append(self.fallback_chat_model)
            models.append(self.embed_model)
            return models

    def embed(self, text: str) -> list[float] | None:
        if not text.strip():
            return None
        text = self._sanitize_embedding_text(text)
        # mxbai-embed-large has limited context; keep payload bounded and retry shorter once.
        prompt = re.sub(r"\s+", " ", text).strip()[: self.embed_max_chars]
        for _attempt in range(2):
            payload = {"model": self.embed_model, "input": prompt, "truncate": True}
            try:
                proc = subprocess.run(
                    [
                        "curl",
                        "-sS",
                        "--max-time",
                        str(self.embed_timeout_seconds),
                        "-H",
                        "Content-Type: application/json",
                        "-d",
                        json.dumps(payload, ensure_ascii=False),
                        f"{self.base_url}/api/embed",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=self.embed_timeout_seconds + 2,
                )
                if proc.returncode != 0:
                    raise RuntimeError(proc.stderr.strip() or f"curl_exit_{proc.returncode}")
                data = json.loads(proc.stdout) if proc.stdout else {}
                emb = None
                embs = data.get("embeddings")
                if isinstance(embs, list) and embs and isinstance(embs[0], list):
                    emb = embs[0]
                if emb is None:
                    emb = data.get("embedding")
                if isinstance(emb, list) and emb:
                    return [float(x) for x in emb]
                err = str(data.get("error", "")).lower()
                if "input length exceeds the context length" in err and len(prompt) > 400:
                    prompt = prompt[: max(400, int(len(prompt) * 0.6))]
                    continue
            except Exception:
                # Backward compatibility with old Ollama endpoints.
                try:
                    proc = subprocess.run(
                        [
                            "curl",
                            "-sS",
                            "--max-time",
                            str(self.embed_timeout_seconds),
                            "-H",
                            "Content-Type: application/json",
                            "-d",
                            json.dumps({"model": self.embed_model, "prompt": prompt}, ensure_ascii=False),
                            f"{self.base_url}/api/embeddings",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=self.embed_timeout_seconds + 2,
                    )
                    if proc.returncode != 0:
                        return None
                    data = json.loads(proc.stdout) if proc.stdout else {}
                    emb = data.get("embedding")
                    if isinstance(emb, list) and emb:
                        return [float(x) for x in emb]
                    err = str(data.get("error", "")).lower()
                    if "input length exceeds the context length" in err and len(prompt) > 400:
                        prompt = prompt[: max(400, int(len(prompt) * 0.6))]
                        continue
                except Exception:
                    return None
            break
        return None

    def _sanitize_embedding_text(self, text: str) -> str:
        secret_line = re.compile(
            r"(password|pass|api[_-]?key|secret|token|private[_-]?key|client[_-]?secret|bearer)",
            re.IGNORECASE,
        )
        sanitized: list[str] = []
        for line in text.splitlines():
            if secret_line.search(line) and ("=" in line or ":" in line):
                if "=" in line:
                    key = line.split("=", 1)[0].strip()
                    sanitized.append(f"{key}=[REDACTED]")
                else:
                    key = line.split(":", 1)[0].strip()
                    sanitized.append(f"{key}: [REDACTED]")
            else:
                sanitized.append(line)
        return "\n".join(sanitized)

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        num_predict = max(64, min(2000, int(os.environ.get("ASSISTANT_OLLAMA_CHAT_NUM_PREDICT", "800"))))
        base_payload = {
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
            },
        }
        if self.keep_alive:
            base_payload["keep_alive"] = self.keep_alive
        models = [self.chat_model]
        if self.fallback_chat_model and self.fallback_chat_model != self.chat_model:
            models.append(self.fallback_chat_model)

        last_error = ""
        for model in models:
            payload = dict(base_payload)
            payload["model"] = model
            self.last_model_used = model
            try:
                r = http_requests.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=self.chat_timeout_seconds,
                )
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                last_error = str(e)
                continue

            err = str(data.get("error", "")).strip()
            if err:
                last_error = err
                continue

            msg = data.get("message", {})
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                self.last_model_used = model
                return content.strip()
            last_error = "empty_model_response"

        raise RuntimeError(last_error or "chat_failed")


class GeminiClient:
    """Gemini API chat client — fast cloud inference, no local memory cost."""

    MODELS = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
    ]

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
        self._client: Any = None
        self.last_model_used = ""
        self._exhausted: set[str] = set()

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self) -> Any:
        if self._client is None:
            from google import genai  # lazy import
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        if not self.available:
            raise RuntimeError("gemini_no_api_key")

        client = self._get_client()
        from google.genai import errors as genai_errors

        # Build Gemini-compatible prompt from messages
        system_parts = []
        contents = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system_parts.append(content)
            else:
                contents.append(content)

        prompt = ""
        if system_parts:
            prompt = "\n".join(system_parts) + "\n\n"
        prompt += "\n\n".join(contents)

        models_to_try = [m for m in self.MODELS if m not in self._exhausted]
        if not models_to_try:
            self._exhausted.clear()
            models_to_try = list(self.MODELS)

        last_error = ""
        for model in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={
                        "temperature": temperature,
                        "max_output_tokens": 1200,
                    },
                )
                text = (response.text or "").strip()
                if text:
                    self.last_model_used = model
                    return text
                last_error = "empty_gemini_response"
            except genai_errors.ClientError as e:
                err_str = str(e)
                if "RESOURCE_EXHAUSTED" in err_str:
                    self._exhausted.add(model)
                    logger.warning("Gemini model %s quota exhausted", model)
                    last_error = f"quota_exhausted:{model}"
                    continue
                last_error = err_str
                logger.error("Gemini ClientError (%s): %s", model, err_str)
            except Exception as e:
                last_error = str(e)
                logger.error("Gemini error (%s): %s", model, e)
                continue

        raise RuntimeError(last_error or "gemini_all_models_failed")


class HybridChatRouter:
    """Routes chat: Gemini (fast) → Pi Ollama (reliable) → HP Ollama (last resort)."""

    def __init__(self, gemini: GeminiClient, ollama: OllamaClient):
        self.gemini = gemini
        self.ollama = ollama  # local HP Ollama
        self.pi_ollama = self._make_pi_ollama()
        self.last_provider = ""
        self.last_model_used = ""

    @staticmethod
    def _make_pi_ollama() -> OllamaClient | None:
        pi_url = os.environ.get("PI_OLLAMA_URL", "").strip()
        if not pi_url:
            return None
        pi_model = os.environ.get("PI_OLLAMA_MODEL", "llama3.1:8b").strip()
        return OllamaClient(
            base_url=pi_url,
            chat_model=pi_model,
            fallback_chat_model=pi_model,
            embed_model="nomic-embed-text",
            chat_timeout_seconds=90,
            keep_alive="30m",
        )

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        # 1. Try Gemini first (fastest, 2-6s)
        if self.gemini.available:
            try:
                result = self.gemini.chat(messages, temperature=temperature)
                self.last_provider = "gemini"
                self.last_model_used = self.gemini.last_model_used
                return result
            except Exception as e:
                logger.warning("Gemini failed, trying Pi Ollama: %s", e)

        # 2. Try Pi Ollama (reliable, 30-50s)
        if self.pi_ollama:
            try:
                result = self.pi_ollama.chat(messages, temperature=temperature)
                self.last_provider = "pi-ollama"
                self.last_model_used = self.pi_ollama.last_model_used
                return result
            except Exception as e:
                logger.warning("Pi Ollama failed, trying local Ollama: %s", e)

        # 3. Local HP Ollama (last resort, slow under memory pressure)
        try:
            result = self.ollama.chat(messages, temperature=temperature)
            self.last_provider = "ollama"
            self.last_model_used = self.ollama.last_model_used
            return result
        except Exception as e:
            logger.error("All providers failed (gemini+pi+local): %s", e)
            raise


class FileAdapters:
    def __init__(self, config: AssistantConfig):
        self.config = config

    def extract(self, file_path: Path, rel_path: str) -> dict[str, Any]:
        ext = file_path.suffix.lower()
        result = {
            "text": "",
            "source_kind": "text",
            "confidence": 0.7,
            "warnings": [],
        }

        size_bytes = file_path.stat().st_size
        max_bytes = self.config.max_file_size_mb * 1024 * 1024

        if size_bytes > max_bytes:
            return {
                "text": self._metadata_only_text(rel_path, file_path, reason=f"file_too_large>{self.config.max_file_size_mb}MB"),
                "source_kind": "metadata",
                "confidence": 0.2,
                "warnings": ["too_large"],
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
    def __init__(self, config: AssistantConfig, ollama: OllamaClient):
        self.config = config
        self.ollama = ollama
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

                should_embed = (
                    self.config.enable_embeddings
                    and source_kind != "metadata"
                    and len(chunk_text.strip()) >= 40
                    and self._is_embedding_target(rel_path, ext)
                )
                if should_embed:
                    emb = self.ollama.embed(chunk_text)
                    if emb:
                        new_embeddings[chunk_id] = emb
                        embedded += 1
                    else:
                        skipped_embeddings += 1
                else:
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
            "embeddings_enabled": self.config.enable_embeddings,
            "chat_model": self.config.ollama_chat_model,
            "chat_fallback_model": self.config.ollama_chat_fallback_model or None,
            "embed_model": self.config.ollama_embed_model if self.config.enable_embeddings else None,
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
        files: list[Path] = []
        root = self.config.project_root
        idx_dir = self.config.index_dir.resolve()

        for dirpath, dirnames, filenames in os.walk(root):
            dir_path = Path(dirpath)
            rel_dir = dir_path.relative_to(root).as_posix() if dir_path != root else ""

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
                rel_file = f"{rel_dir}/{name}".strip("/")
                if self._is_excluded_file(rel_file):
                    continue
                try:
                    if not file_path.is_file():
                        continue
                    files.append(file_path)
                except Exception:
                    continue

        files.sort(key=lambda p: p.relative_to(root).as_posix())
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
    def __init__(self, chunks: list[dict[str, Any]], embeddings: dict[str, list[float]], ollama: OllamaClient, vector_weight: float = 0.55):
        self.chunks = chunks
        self.embeddings = embeddings
        self.ollama = ollama
        self.vector_weight = max(0.0, min(1.0, vector_weight))

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

        bm25_scores = self._bm25_scores(query_tokens, path_prefixes)

        vector_scores: dict[int, float] = {}
        q_emb = self.ollama.embed(query)
        if q_emb:
            q_norm = self._norm(q_emb)
            for i, ch in enumerate(self.chunks):
                if path_prefixes and not self._path_allowed(str(ch.get("path", "")), path_prefixes):
                    continue
                cid = str(ch.get("chunk_id", ""))
                emb = self.embeddings.get(cid)
                if not emb:
                    continue
                den = q_norm * self._norm(emb)
                if den == 0:
                    continue
                vector_scores[i] = self._dot(q_emb, emb) / den

        max_bm25 = max(bm25_scores.values()) if bm25_scores else 0.0
        if max_bm25 <= 0:
            max_bm25 = 1.0

        combined: list[tuple[int, float, float, float]] = []
        all_idxs = set(bm25_scores.keys()) | set(vector_scores.keys())
        for idx in all_idxs:
            b = bm25_scores.get(idx, 0.0) / max_bm25
            v = max(0.0, vector_scores.get(idx, 0.0))
            score = (1.0 - self.vector_weight) * b + self.vector_weight * v
            combined.append((idx, score, b, v))

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

    def __init__(self, project_root: str | os.PathLike[str]):
        self.config = AssistantConfig.from_project_root(project_root)
        self.ollama = OllamaClient(
            base_url=self.config.ollama_base_url,
            chat_model=self.config.ollama_chat_model,
            fallback_chat_model=self.config.ollama_chat_fallback_model,
            embed_model=self.config.ollama_embed_model,
            chat_timeout_seconds=self.config.ollama_chat_timeout_seconds,
            embed_timeout_seconds=self.config.ollama_embed_timeout_seconds,
            embed_max_chars=self.config.ollama_embed_max_chars,
            keep_alive=self.config.ollama_keep_alive,
        )
        self.gemini = GeminiClient()
        self.router = HybridChatRouter(self.gemini, self.ollama)
        self.indexer = AssistantIndexer(self.config, self.ollama)
        self.policy = SafetyPolicy()

        self._retriever: HybridRetriever | None = None
        self._retriever_cache_mtime: float = 0.0

    def reindex(self, incremental: bool = True) -> dict[str, Any]:
        return self.indexer.reindex(incremental=incremental)

    def chat(
        self,
        messages: list[dict[str, Any]],
        session_id: str = "",
        context_filters: dict[str, Any] | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        start = time.perf_counter()

        user_query = self._latest_user_message(messages)
        safety_flags = self.policy.evaluate(user_query)
        intent = self._classify_intent(user_query)

        retriever = self._load_retriever()
        top_k = self.config.retrieval_k
        results = retriever.search(user_query, top_k=top_k, context_filters=context_filters)

        strong_support = self._has_strong_retrieval_support(results)
        citations = self._citations_from_results(results) if strong_support else []
        stale = self._is_context_stale()
        if stale:
            safety_flags.append("warning:stale_context")

        answer = self._generate_answer(
            user_query=user_query,
            intent=intent,
            citations=citations,
            safety_flags=safety_flags,
            messages=messages,
            temperature=temperature,
        )

        if not strong_support:
            safety_flags.append("warning:limited_confidence")
            answer = (
                "Sınırlı güven: Yerel kaynaklarda bu soruyu güçlü biçimde destekleyen kayıt bulamadım. "
                "Genel pedagojik çerçevede yanıtlıyorum.\n\n" + answer
            )

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
                "model": self.router.last_model_used or self.config.ollama_chat_model,
                    "provider": self.router.last_provider or "unknown",
                "retrieval_count": len(results),
                "latency_ms": latency_ms,
                "index_generated_at": self._meta_generated_at(),
            },
        }

        self._write_metric({
            "type": "chat",
            "session_id": session_id,
            "intent": intent,
            "latency_ms": latency_ms,
            "citations": len(citations),
            "safety_flags": payload["safety_flags"],
                "timestamp": _utcnow_naive().isoformat() + "Z",
        })

        return payload

    def study_plan(
        self,
        messages: list[dict[str, Any]],
        session_id: str = "",
        context_filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        start = time.perf_counter()
        user_query = self._latest_user_message(messages)

        retriever = self._load_retriever()
        results = retriever.search(user_query, top_k=max(10, self.config.retrieval_k), context_filters=context_filters)
        citations = self._citations_from_results(results)

        plan_blocks = self._build_rule_based_plan(user_query)

        # If Ollama is available, ask model to refine the plan text with context.
        llm_summary = self._generate_plan_summary(user_query, plan_blocks, citations)

        latency_ms = int((time.perf_counter() - start) * 1000)
        payload = {
            "answer": llm_summary,
            "citations": citations,
            "safety_flags": [],
            "plan_blocks": plan_blocks,
            "intent": "study_plan",
            "session_id": session_id,
            "meta": {
                "model": self.router.last_model_used or self.config.ollama_chat_model,
                    "provider": self.router.last_provider or "unknown",
                "latency_ms": latency_ms,
                "retrieval_count": len(results),
                "index_generated_at": self._meta_generated_at(),
            },
        }

        self._write_metric({
            "type": "plan",
            "session_id": session_id,
            "latency_ms": latency_ms,
            "citations": len(citations),
            "blocks": len(plan_blocks),
                "timestamp": _utcnow_naive().isoformat() + "Z",
        })

        return payload

    def models(self) -> list[dict[str, Any]]:
        names = self.ollama.available_models()
        uniq = []
        seen = set()
        for n in names:
            if n in seen:
                continue
            seen.add(n)
            uniq.append({
                "id": n,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "ollama-local",
            })
        return uniq

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

        used_model = str(out.get("meta", {}).get("model") or self.config.ollama_chat_model)
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

    def _generate_answer(
        self,
        user_query: str,
        intent: str,
        citations: list[dict[str, Any]],
        safety_flags: list[str],
        messages: list[dict[str, Any]],
        temperature: float,
    ) -> str:
        prompt_citations = citations[:6]
        context_blocks = []
        for i, c in enumerate(prompt_citations, start=1):
            snippet = str(c.get("snippet", "")).replace("\n", " ").strip()
            if len(snippet) > 400:
                snippet = snippet[:397] + "..."
            context_blocks.append(
                f"[S{i}] path={c.get('path','')} confidence={c.get('confidence',0.0)} snippet={snippet}"
            )

        context_text = "\n".join(context_blocks) if context_blocks else "[Kaynak bulunamadı]"

        system_prompt = (
            "Sen TEDY Eğitim Asistanısın — ortaokul öğrencisi Işık ve ailesi için kişisel eğitim danışmanısın.\n\n"
            "## Kimlik\n"
            "- Hedef kitle: 7. sınıf öğrencisi + veliler. Varsayılan dil Türkçe.\n"
            "- Işık'ın ders programı, ödevleri, sınav sonuçları, takvimi ve ders içerikleri sana kaynak olarak verilir.\n\n"
            "## Yanıt Formatı\n"
            "- Kısa ve öz başla: İlk cümlede sorunun doğrudan cevabını ver.\n"
            "- Madde işaretleri kullan, uzun paragraflardan kaçın.\n"
            "- Somut ve uygulanabilir öneriler sun (ne yapılacak, ne zaman, nasıl).\n"
            "- Ödev/sınav sorularında: öncelik sırası belirt, tahmini süre ver, çalışma stratejisi öner.\n"
            "- Not analizi sorularında: güçlü/zayıf alanları belirle, iyileştirme adımları sun.\n\n"
            "## Pedagojik İlkeler\n"
            "- Bloom taksonomisine göre bilgi → anlama → uygulama basamaklarını kullan.\n"
            "- Aralıklı tekrar (spaced repetition) ve aktif öğrenme stratejilerini öner.\n"
            "- Motivasyonu destekle: başarıları vurgula, yapıcı geri bildirim ver.\n"
            "- Veli sorularında: eyleme dönüştürülebilir somut adımlar ver, jargondan kaçın.\n\n"
            "## Kurallar\n"
            "- Kaynak dışı kesin iddia kurma. Kaynak varsa metin içinde [S1], [S2] gibi atıf ver.\n"
            "- Kaynak referanslarını satır içinde doğal biçimde kullan, ayrı liste yapma.\n"
            "- Klinik tanı/tedavi önerme. Riskli psikolojik durumda profesyonel destek yönlendirmesi yap.\n"
            "- Yanıtı asla 'Kaynaklar:' listesiyle bitirme — atıflar zaten metin içinde."
        )

        user_payload = (
            f"Soru türü: {intent}\n"
            f"Güvenlik: {', '.join(safety_flags) if safety_flags else 'yok'}\n\n"
            f"Soru: {user_query}\n\n"
            f"Işık'ın verileri:\n{context_text}\n\n"
            "Bu verileri kullanarak Işık'a özel, somut ve pedagojik bir yanıt ver."
        )

        convo = [
            {"role": "system", "content": system_prompt},
            *[
                {
                    "role": str(m.get("role", "user")),
                    "content": str(m.get("content", ""))[:2000],
                }
                for m in messages[-3:]
                if isinstance(m, dict)
            ],
            {"role": "user", "content": user_payload},
        ]

        try:
            out = self.router.chat(convo, temperature=temperature)
            if out:
                return out
            logger.warning("Chat router returned empty response")
        except Exception as exc:
            logger.error("Chat router failed (gemini+ollama): %s", exc)

        # Fail-safe fallback.
        if citations:
            refs = ", ".join(f"[{i+1}] {c['path']}" for i, c in enumerate(citations[:3]))
            return (
                f"Yerel kaynaklara göre kısa değerlendirme: {user_query}\n"
                f"Kaynaklar: {refs}.\n"
                "Model yanıtı üretilemediği için özet modunda döndüm."
            )
        return (
            "Model şu anda erişilebilir değil ve yeterli kaynak eşleşmesi bulunamadı. "
            "Lütfen soruyu daha spesifik (ders/konu/tarih) biçimde tekrar gönderin."
        )

    def _generate_plan_summary(
        self,
        user_query: str,
        plan_blocks: list[dict[str, Any]],
        citations: list[dict[str, Any]],
    ) -> str:
        if os.environ.get("ASSISTANT_ENABLE_LLM_PLAN_SUMMARY", "0") != "1":
            return self._deterministic_plan_summary(plan_blocks, citations)

        blocks_text = json.dumps(plan_blocks, ensure_ascii=False, indent=2)
        cites_text = "\n".join(
            f"[S{i+1}] {c['path']} :: {c['snippet']}" for i, c in enumerate(citations[:5])
        )

        prompt = (
            "Aşağıdaki plan bloklarını Işık (7. sınıf) ve ailesi için haftalık çalışma planına dönüştür.\n\n"
            "## Format Kuralları\n"
            "- 4 bölüm kullan: **Öncelikler**, **Günlük Akış**, **Ölçme-Değerlendirme**, **Veli Kontrol Listesi**\n"
            "- Her gün için somut adımlar ve tahmini süreler yaz.\n"
            "- Yakın tarihli ödevleri/sınavları acil olarak işaretle.\n"
            "- Bloom taksonomisine göre: önce hatırla/anla, sonra uygula/analiz et basamaklarını öner.\n"
            "- Aralıklı tekrar: önceki haftanın konularını kısa tekrar blokları olarak ekle.\n"
            "- Motivasyon: 'Bunu başarabilirsin' gibi destekleyici ifadeler ekle.\n"
            "- Kaynak varsa [S1] formatında atıf ver. Ayrı kaynak listesi yapma.\n\n"
            f"Soru: {user_query}\n\n"
            f"Plan blokları:\n{blocks_text}\n\n"
            f"Kaynaklar:\n{cites_text if cites_text else '[yok]'}"
        )

        try:
            out = self.router.chat(
                messages=[
                    {"role": "system", "content": (
                        "Sen Işık'ın kişisel pedagojik planlama asistanısın. "
                        "Öğrencinin güncel ödev, sınav ve ders verilerini kullanarak "
                        "uygulanabilir, motive edici çalışma planları oluşturursun."
                    )},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.15,
            )
            if out:
                return out
        except Exception:
            pass

        return self._deterministic_plan_summary(plan_blocks, citations)

    def _deterministic_plan_summary(
        self,
        plan_blocks: list[dict[str, Any]],
        citations: list[dict[str, Any]],
    ) -> str:
        lines = ["Haftalık Çalışma Planı (Özet)"]
        for block in plan_blocks[:7]:
            title = block.get("title", "Görev")
            day = block.get("day", "")
            mins = block.get("estimated_minutes", 40)
            lines.append(f"- {day}: {title} ({mins} dk)")
        if citations:
            lines.append("Kaynaklar: " + ", ".join(f"[S{i+1}]" for i in range(min(3, len(citations)))))
        return "\n".join(lines)

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

    def _citations_from_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cites: list[dict[str, Any]] = []
        for i, r in enumerate(results[:8], start=1):
            cites.append({
                "id": f"S{i}",
                "path": r.get("path", ""),
                "chunk_index": r.get("chunk_index", 0),
                "score": r.get("score", 0.0),
                "bm25": r.get("bm25", 0.0),
                "vector": r.get("vector", 0.0),
                "confidence": r.get("confidence", 0.0),
                "snippet": r.get("snippet", ""),
                "source_kind": r.get("source_kind", "text"),
            })
        return cites

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
                ref = datetime.fromisoformat(health_ts.replace("Z", "+00:00").replace("+00:00", ""))
                if idx_dt < ref:
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
            embeddings=embeddings,
            ollama=self.ollama,
            vector_weight=self.config.vector_weight,
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


def perform_incremental_reindex(project_root: str | os.PathLike[str]) -> dict[str, Any]:
    """Convenience function for sync pipeline hooks."""
    runtime = AssistantRuntime(project_root)
    return runtime.reindex(incremental=True)
