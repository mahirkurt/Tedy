"""Documents attached to one homework row, embedded on mbp-node.

Portal scrapes overwrite homework rows. A file a person attaches lives
here, under the same homework key İşler uses, and is retrieved only for
that homework. Vectors come from Ollama on mbp-node (`bge-m3`); this
machine stores them and does not compute them.
"""
from __future__ import annotations

import fcntl
import hashlib
import math
import os
import re
import secrets
from datetime import datetime
from pathlib import Path

import requests as http_requests

from src.json_utils import atomic_json_dump

# Tailscale name of the machine that holds the embedding model. Override
# with HOMEWORK_EMBED_URL when that host is not the one to call.
EMBED_URL = os.environ.get(
    "HOMEWORK_EMBED_URL", "http://mbp-node.tail67843b.ts.net:11434"
).rstrip("/")
EMBED_MODEL = os.environ.get("HOMEWORK_EMBED_MODEL", "bge-m3").strip() or "bge-m3"

ALLOWED_EXT = {".pdf", ".txt", ".md", ".docx"}
MAX_BYTES = 8 * 1024 * 1024
MAX_PER_HOMEWORK = 6
MAX_METIN = 80_000
CHUNK = 800
OVERLAP = 120
MAX_CHUNK = 16
# bge-m3 cosine: related Turkish passages sit well above this; unrelated
# ones do not. Below it the assistant is told the document has no passage,
# rather than a weak neighbour it would quote as if it answered.
MIN_SCORE = 0.35
TOP_K = 4

MIME = {
    ".pdf": "application/pdf",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class BelgeReddedildi(ValueError):
    """The upload cannot be stored. The message is safe to show."""


class EmbedHatasi(RuntimeError):
    """mbp-node did not return vectors. The message stays internal."""


def ollama_embed(texts: list[str]) -> list[list[float]]:
    """Embed `texts` with the configured model on mbp-node."""
    if not texts:
        return []
    try:
        resp = http_requests.post(
            f"{EMBED_URL}/api/embed",
            json={"model": EMBED_MODEL, "input": texts},
            timeout=90,
        )
    except http_requests.RequestException as exc:
        raise EmbedHatasi("bağlantı") from exc
    if resp.status_code != 200:
        raise EmbedHatasi("http")
    try:
        vectors = resp.json().get("embeddings")
    except ValueError as exc:
        raise EmbedHatasi("json") from exc
    if not isinstance(vectors, list) or len(vectors) != len(texts):
        raise EmbedHatasi("adet")
    out: list[list[float]] = []
    for vec in vectors:
        if not isinstance(vec, list) or not vec:
            raise EmbedHatasi("biçim")
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in vec):
            raise EmbedHatasi("biçim")
        out.append([float(x) for x in vec])
    if any(len(v) != len(out[0]) for v in out):
        raise EmbedHatasi("boy")
    return out


def _koku(kok: Path) -> tuple[Path, Path, Path]:
    kok = Path(kok)
    files = kok / "files"
    index = kok / "index.json"
    return kok, files, index


def _yukle(index: Path) -> list[dict]:
    if not index.is_file():
        return []
    try:
        import json
        with index.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return []
    rows = data.get("documents") if isinstance(data, dict) else None
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def _kaydet(index: Path, rows: list[dict]) -> None:
    atomic_json_dump({"documents": rows}, str(index))


def _kilit(kok: Path):
    kok.mkdir(parents=True, exist_ok=True)
    fh = open(kok / ".lock", "a+", encoding="utf-8")
    fcntl.flock(fh, fcntl.LOCK_EX)
    return fh


def _guvenli_ad(name: str) -> str:
    base = Path(str(name or "")).name.strip()
    base = re.sub(r"[^\w.\- ]+", "_", base, flags=re.UNICODE)
    base = base.strip(" .")[:120]
    return base or "belge"


def _parcala(text: str) -> list[str]:
    text = text.strip()[:MAX_METIN]
    if not text:
        return []
    parcalar: list[str] = []
    buf = ""
    for para in re.split(r"\n\s*\n", text):
        para = " ".join(para.split())
        if not para:
            continue
        if buf and len(buf) + 1 + len(para) <= CHUNK:
            buf = f"{buf}\n{para}"
            continue
        if buf:
            parcalar.append(buf)
        while len(para) > CHUNK:
            parcalar.append(para[:CHUNK])
            para = para[CHUNK - OVERLAP:]
        buf = para
    if buf:
        parcalar.append(buf)
    return parcalar[:MAX_CHUNK]


def _metin(path: Path) -> tuple[str, str]:
    """(text, error). An empty text with an error means nothing to embed."""
    from src.assistant_core import AssistantConfig, FileAdapters

    root = Path(__file__).resolve().parents[1]
    extracted = FileAdapters(AssistantConfig.from_project_root(root)).extract(path, path.name)
    if extracted.get("extraction_error"):
        return "", "Bu belgeden metin çıkmadı."
    if str(extracted.get("source_kind") or "") == "metadata":
        return "", "Bu belgeden metin çıkmadı."
    text = str(extracted.get("text") or "").strip()
    if not text:
        return "", "Bu belgeden metin çıkmadı."
    return text, ""


def herkese(doc: dict) -> dict:
    """The fields a reader may see. Embeddings stay in the index."""
    return {
        "id": doc.get("id", ""),
        "name": doc.get("name", ""),
        "ready": bool(doc.get("chunks")) and not doc.get("error") and all(
            isinstance(c, dict) and c.get("embedding") for c in doc.get("chunks") or []
        ),
        "error": str(doc.get("error") or ""),
    }


def hepsi(kok: Path) -> dict[str, list[dict]]:
    """homework_key -> public document list, embeddings omitted."""
    _, _, index = _koku(kok)
    grup: dict[str, list[dict]] = {}
    for doc in _yukle(index):
        key = str(doc.get("homework_key") or "")
        if not key:
            continue
        grup.setdefault(key, []).append(herkese(doc))
    return grup


def ekle(kok: Path, homework_key: str, filename: str, data: bytes,
         embed=None) -> dict:
    """Store one file and embed its text. Returns the public document."""
    if embed is None:
        embed = ollama_embed
    key = str(homework_key or "").strip()
    if not key or len(key) > 400:
        raise BelgeReddedildi("Ödev bulunamadı.")
    if not data:
        raise BelgeReddedildi("Boş dosya gönderildi.")
    if len(data) > MAX_BYTES:
        raise BelgeReddedildi("Belge çok büyük (en fazla 8 MB).")
    name = _guvenli_ad(filename)
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise BelgeReddedildi("PDF, Word, metin veya Markdown dosyası ekleyebilirsin.")

    kok, files, index = _koku(kok)
    lock = _kilit(kok)
    try:
        rows = _yukle(index)
        ayni = [r for r in rows if r.get("homework_key") == key]
        if len(ayni) >= MAX_PER_HOMEWORK:
            raise BelgeReddedildi("Bu ödeve en fazla 6 belge eklenebilir.")
        sha = hashlib.sha256(data).hexdigest()
        for row in ayni:
            if row.get("sha256") == sha:
                return herkese(row)

        doc_id = secrets.token_hex(8)
        files.mkdir(parents=True, exist_ok=True)
        stored = files / f"{doc_id}{ext}"
        stored.write_bytes(data)
        try:
            text, read_error = _metin(stored)
        except Exception:
            text, read_error = "", "Bu belgeden metin çıkmadı."
        chunks: list[dict] = []
        error = read_error
        if text and not read_error:
            pieces = _parcala(text)
            try:
                vectors = embed(pieces)
                if len(vectors) != len(pieces):
                    raise EmbedHatasi("adet")
                chunks = [
                    {"text": piece, "embedding": vector}
                    for piece, vector in zip(pieces, vectors)
                ]
            except EmbedHatasi:
                chunks = [{"text": piece, "embedding": None} for piece in pieces]
                error = "Belge duruyor; vektörü yazılamadı."
        doc = {
            "id": doc_id,
            "homework_key": key,
            "name": name,
            "ext": ext,
            "bytes": len(data),
            "sha256": sha,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "embed_model": EMBED_MODEL,
            "error": error,
            "chunks": chunks,
        }
        rows.append(doc)
        _kaydet(index, rows)
        return herkese(doc)
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def sil(kok: Path, doc_id: str) -> bool:
    doc_id = str(doc_id or "").strip()
    if not re.fullmatch(r"[0-9a-f]{16}", doc_id):
        return False
    kok, files, index = _koku(kok)
    lock = _kilit(kok)
    try:
        rows = _yukle(index)
        hedef = next((r for r in rows if r.get("id") == doc_id), None)
        if hedef is None:
            return False
        path = files / f"{doc_id}{hedef.get('ext') or ''}"
        rows = [r for r in rows if r.get("id") != doc_id]
        _kaydet(index, rows)
        try:
            path.unlink()
        except OSError:
            pass
        return True
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def dosya(kok: Path, doc_id: str) -> tuple[Path, str, str] | None:
    """(path, download name, mime) for one stored file, or None."""
    doc_id = str(doc_id or "").strip()
    if not re.fullmatch(r"[0-9a-f]{16}", doc_id):
        return None
    kok, files, index = _koku(kok)
    hedef = next((r for r in _yukle(index) if r.get("id") == doc_id), None)
    if hedef is None:
        return None
    ext = str(hedef.get("ext") or "")
    path = (files / f"{doc_id}{ext}").resolve()
    try:
        path.relative_to(files.resolve())
    except ValueError:
        return None
    if not path.is_file():
        return None
    return path, str(hedef.get("name") or "belge"), MIME.get(ext, "application/octet-stream")


def _kos(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def ara(kok: Path, homework_key: str, sorgu: str, embed=None) -> str:
    """Passages of one homework's documents, for the assistant.

    Other homework keys are never searched. A missing vector is said, not
    filled in from a neighbouring document."""
    if embed is None:
        embed = ollama_embed
    key = str(homework_key or "").strip()
    sorgu = " ".join(str(sorgu or "").split())
    if not key:
        return "Önce asistan ekranından bir ödev seç."
    if not sorgu:
        return "Aranacak bir soru yok."
    _, _, index = _koku(kok)
    docs = [d for d in _yukle(index) if d.get("homework_key") == key]
    if not docs:
        return "Bu ödeve eklenmiş belge yok."
    hazir = []
    bozuk = []
    for doc in docs:
        if doc.get("error") or not any(
            isinstance(c, dict) and c.get("embedding") for c in doc.get("chunks") or []
        ):
            bozuk.append(str(doc.get("name") or "belge"))
            continue
        hazir.append(doc)
    if not hazir:
        ad = ", ".join(bozuk)
        return f"{ad} duruyor ama vektörü yok. İçinde ne yazdığını uydurma."
    try:
        sorgu_vec = embed([sorgu])[0]
    except (EmbedHatasi, IndexError):
        return "Belge vektörüne şu an ulaşılamadı. Belgede ne yazdığını uydurma."
    aday: list[tuple[float, str, str]] = []
    for doc in hazir:
        ad = str(doc.get("name") or "belge")
        for chunk in doc.get("chunks") or []:
            if not isinstance(chunk, dict) or not chunk.get("embedding"):
                continue
            skor = _kos(sorgu_vec, chunk["embedding"])
            if skor >= MIN_SCORE:
                aday.append((skor, ad, str(chunk.get("text") or "").strip()))
    aday.sort(key=lambda x: x[0], reverse=True)
    if not aday:
        return "Bu ödevin belgelerinde bu soruya karşılık gelen bir parça yok. Belgede olmayanı yazma."
    satirlar = []
    for skor, ad, metin in aday[:TOP_K]:
        kisa = metin if len(metin) <= 700 else metin[:700].rsplit(" ", 1)[0] + " …"
        satirlar.append(f"Belge: {ad}\n{kisa}")
    return "\n\n".join(satirlar)
