"""Catalog writer and publish tools (spec §5.3; plan K-P10, K-P17, K-P18). ted-mcp is the only writer.

Tool bodies run in worker threads, so every catalog read-modify-write holds fcntl.flock on
output/modules/.lock (separate open() calls contend across threads and processes alike).
Versions are immutable: the HTML is created with O_EXCL and the next version skips any
orphan directory left by an interrupted publish.
"""
from __future__ import annotations

import fcntl
import hashlib
import os
import re
import time
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from src import module_store as ms
from src.json_utils import atomic_json_dump
from src.mcp_server.taslak import DraftStore

_ABBREVIATIONS = (
    ("fen bilimleri", "fen"), ("matematik", "mat"), ("turkce", "tr"), ("sosyal bilgiler", "sos"),
    ("ingilizce", "ing"), ("hayat bilgisi", "hayat"), ("din kulturu", "din"), ("bilisim", "bil"),
)
_CARD_FIELDS = ("slug", "version", "status", "title", "subject", "gradeLevel", "mode", "outcomes",
                "ted_link", "gates", "created_at")
DURUMLAR = ("active", "removed", "hepsi")


def _fold(text: str) -> str:
    text = (text or "").replace("İ", "i").replace("I", "ı").replace("ı", "i").lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def slug_turet(subject: str | None, grade_level: str | None, title: str | None) -> str:
    folded = _fold(subject or "")
    short = next((abbr for name, abbr in _ABBREVIATIONS if folded.startswith(name)),
                 re.sub(r"[^a-z0-9]+", "", folded)[:6] or "modul")
    grade = re.search(r"\d+", grade_level or "")
    head = short + (grade.group(0) if grade else "")
    words = re.sub(r"[^a-z0-9]+", "-", _fold(title or "")).strip("-")
    slug = re.sub(r"-{2,}", "-", f"{head}-{words}".strip("-"))[: ms.SLUG_MAX].rstrip("-")
    return slug if ms.publishable_slug(slug) else "modul"


def _iso(now: float) -> str:
    return datetime.fromtimestamp(now, timezone.utc).isoformat(timespec="seconds")


def _valid_ted_link(link: Any) -> bool:
    return (isinstance(link, dict) and set(link) == {"kind", "id"} and link["kind"] in ("exam", "homework")
            and isinstance(link["id"], str) and 0 < len(link["id"]) <= 128)


class CatalogWriter:
    def __init__(self, data_dir: Path | str, clock: Callable[[], float] = time.time) -> None:
        self.data_dir = Path(data_dir)
        self.clock = clock
        self.lock_path = ms.modules_root(self.data_dir) / ".lock"

    @contextmanager
    def _locked(self) -> Iterator[None]:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _write(self, rows: list[dict[str, Any]]) -> None:
        atomic_json_dump({"surum": 1, "moduller": rows}, str(ms.catalog_path(self.data_dir)))

    def _next_version(self, rows: list[dict[str, Any]], slug: str) -> int:
        known = [int(r.get("version") or 0) for r in rows if r.get("slug") == slug]
        folder = ms.modules_root(self.data_dir) / slug
        on_disk = [ms.parse_version_segment(p.name) or 0 for p in folder.iterdir()] if folder.is_dir() else []
        return max(known + on_disk + [0]) + 1

    def yayinla(self, email: str, draft: dict[str, Any], html: bytes, slug: str,
                ted_link: dict[str, str] | None) -> dict[str, Any]:
        if not ms.publishable_slug(slug):
            raise ValueError("gecersiz_slug")
        with self._locked():
            rows = ms.read_catalog(self.data_dir)
            version = self._next_version(rows, slug)
            path = ms.module_html_path(self.data_dir, slug, version)
            if path is None:
                raise ValueError("surum_siniri")
            path.parent.mkdir(parents=True, exist_ok=False)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(fd, "wb") as handle:
                handle.write(html)
            meta, gates, frame = draft.get("meta") or {}, draft.get("gates") or {}, draft.get("frame_source") or {}
            record = {
                "slug": slug, "version": version, "status": "active",
                "title": meta.get("title"), "subject": meta.get("subject"), "gradeLevel": meta.get("gradeLevel"),
                "mode": meta.get("mode"), "outcomes": list(draft.get("outcomes") or []),
                "frame_source": {"kind": frame.get("kind"), "document_id": frame.get("document_id"),
                                 "pages": frame.get("pages")},
                "gates": {"pass": gates.get("pass", 0), "warn": gates.get("warn", 0), "fail": gates.get("fail", 0)},
                "coverage": dict(draft.get("coverage") or {}), "ted_link": ted_link,
                "run_id": draft.get("run_id"), "taslak_id": draft.get("taslak_id"),
                "bytes": len(html), "sha256": hashlib.sha256(html).hexdigest(),
                "created_by": email, "created_at": _iso(self.clock()),
            }
            rows.append(record)
            self._write(rows)
            return record

    def kaldir(self, email: str, slug: str) -> int:
        with self._locked():
            rows = ms.read_catalog(self.data_dir)
            count = 0
            for row in rows:
                if row.get("slug") == slug and row.get("status") == "active":
                    row.update(status="removed", removed_at=_iso(self.clock()), removed_by=email)
                    count += 1
            if count:
                self._write(rows)
            return count

    def listele(self, ders: str | None = None, sinif: str | None = None, durum: str = "active") -> list[dict[str, Any]]:
        wanted_grade = re.search(r"\d+", sinif or "")
        out = []
        for row in ms.read_catalog(self.data_dir):
            if durum != "hepsi" and row.get("status") != durum:
                continue
            if ders and _fold(ders) not in _fold(str(row.get("subject") or "")):
                continue
            if wanted_grade:
                have = re.search(r"\d+", str(row.get("gradeLevel") or ""))
                if not have or have.group(0) != wanted_grade.group(0):
                    continue
            out.append(row)
        return out


class Yayinci:
    def __init__(self, drafts: DraftStore, catalog: CatalogWriter, dashboard_public_url: str) -> None:
        self.drafts = drafts
        self.catalog = catalog
        self.base = dashboard_public_url.rstrip("/")

    def _url(self, row: dict[str, Any]) -> str:
        return f"{self.base}/moduller/{row['slug']}/v{row['version']}"

    def yayinla(self, email: str, taslak_id: str, ted_link: dict[str, str] | None = None,
                slug: str | None = None) -> dict[str, Any]:
        base = {"taslak_id": taslak_id, "mcp_verified": False}
        draft = self.drafts.load(taslak_id) if ms.valid_taslak_id(taslak_id) else None
        if draft is None:
            return {**base, "status": "taslak_bulunamadi"}
        if int((draft.get("gates") or {}).get("fail", 1)) != 0:
            fails = sorted(g for g, v in (draft.get("kapilar") or {}).items() if v.get("status") == "FAIL")
            return {**base, "status": "kapi_fail", "fail_kapilari": fails,
                    "not": "Yayın yalnız FAIL'siz taslaktan yapılır; edupedia_derle ile düzelt."}
        meta = draft.get("meta") or {}
        if meta.get("mode") == "EXAM":
            return {**base, "status": "yayin_yok_exam_modu",
                    "not": "EXAM modu telif nedeniyle yayınlanmaz; önizleme serbesttir."}
        link = ted_link if ted_link is not None else draft.get("ted_link")
        if link is not None and not _valid_ted_link(link):
            return {**base, "status": "gecersiz_ted_link", "kural": "{kind: exam|homework, id}"}
        if slug is not None and not ms.publishable_slug(slug):
            return {**base, "status": "gecersiz_slug",
                    "kural": "^[a-z0-9]+(?:-[a-z0-9]+)*$, en fazla 60 karakter, 'taslak' ayrılmış"}
        chosen = slug if slug is not None else slug_turet(meta.get("subject"), meta.get("gradeLevel"), meta.get("title"))
        html = self.drafts.html_bytes(taslak_id)
        if html is None or hashlib.sha256(html).hexdigest() != draft.get("sha256"):
            return {**base, "status": "taslak_bozuk"}
        record = self.catalog.yayinla(email, draft, html, chosen, link)
        return {"status": "ok", "slug": record["slug"], "version": record["version"], "url": self._url(record),
                "mcp_verified": False}

    def katalog(self, ders: str | None = None, sinif: str | None = None, durum: str | None = None) -> dict[str, Any]:
        durum = durum or "active"
        if durum not in DURUMLAR:
            return {"status": "gecersiz_durum", "izinli": list(DURUMLAR), "mcp_verified": False}
        rows = self.catalog.listele(ders, sinif, durum)
        cards = [{**{k: row.get(k) for k in _CARD_FIELDS}, "url": self._url(row)} for row in rows]
        return {"status": "ok", "sayi": len(cards), "moduller": cards, "mcp_verified": False}

    def kaldir(self, email: str, slug: str) -> dict[str, Any]:
        if not ms.valid_slug(slug):
            return {"status": "gecersiz_slug", "slug": slug, "mcp_verified": False}
        count = self.catalog.kaldir(email, slug)
        if not count:
            return {"status": "bulunamadi", "slug": slug, "mcp_verified": False}
        return {"status": "ok", "slug": slug, "kaldirilan_surum_sayisi": count,
                "not": "Dosyalar silinmez; sürümler removed işaretlenir ve katalogdan düşer.", "mcp_verified": False}
