"""Catalog writer and publish tools (spec §5.3; plan K-P10, K-P17, K-P18). ted-mcp is the only writer.

Tool bodies run in worker threads, so every catalog read-modify-write holds fcntl.flock on
output/modules/.lock (separate open() calls contend across threads and processes alike).
Versions are immutable: the HTML is created with O_EXCL and the next version skips any
orphan directory left by an interrupted publish.
"""
from __future__ import annotations

import fcntl
import hashlib
import logging
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

logger = logging.getLogger(__name__)

_ABBREVIATIONS = (
    ("fen bilimleri", "fen"), ("matematik", "mat"), ("turkce", "tr"), ("sosyal bilgiler", "sos"),
    ("ingilizce", "ing"), ("hayat bilgisi", "hayat"), ("din kulturu", "din"), ("bilisim", "bil"),
)
_CARD_FIELDS = ("slug", "version", "status", "title", "subject", "gradeLevel", "mode", "outcomes",
                "ted_link", "gates", "created_at")
DURUMLAR = ("active", "removed", "hepsi")
# Closed statuses Yayinci.yayinla raises itself and must pass through verbatim (fix round 1, F3);
# any other ValueError (or any other Exception at all) is an unclosed internal failure and must
# be mapped to sunucu_hatasi instead of letting its Python text reach the tool caller.
_KNOWN_REASONS = ("gecersiz_slug", "surum_siniri", "yol_reddedildi")
_SUNUCU_HATASI_MESAJ = "Katalog işlemi sunucu tarafında tamamlanamadı; yöneticiye bildir."


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


def _sunucu_hatasi(base: dict[str, Any]) -> dict[str, Any]:
    """Closed catch-all (fix round 1, F3): call only from inside an `except` block so
    `logger.exception` captures the real traceback. Never interpolates the exception's own
    text or type into the returned body — that text is exactly what must not reach the tool
    caller (matches derle_araci.derle's `sunucu_hatasi` pattern)."""
    logger.exception("katalog işlemi sunucu tarafında tamamlanamadı")
    return {**base, "status": "sunucu_hatasi", "not": _SUNUCU_HATASI_MESAJ}


def _refuses_for_fail(draft: dict[str, Any]) -> bool:
    """Fail-closed FAIL check (fix round 1, F4): re-derived from `kapilar` itself, not just the
    pre-computed `gates.fail` count, so a hand-tampered or malformed draft record refuses
    publication rather than trusting a summary field that could have drifted from its detail."""
    fail_count = (draft.get("gates") or {}).get("fail")
    if not (isinstance(fail_count, int) and not isinstance(fail_count, bool) and fail_count == 0):
        return True
    kapilar = draft.get("kapilar")
    if not isinstance(kapilar, dict) or not kapilar:
        return True
    return any(not isinstance(entry, dict) or entry.get("status") == "FAIL" for entry in kapilar.values())


def _fail_gate_names(draft: dict[str, Any]) -> list[str]:
    kapilar = draft.get("kapilar")
    if not isinstance(kapilar, dict):
        return []
    return sorted(g for g, v in kapilar.items() if isinstance(v, dict) and v.get("status") == "FAIL")


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
        # Fix round 1, F1: a row whose `version` fails `valid_version` (wrong type, out of
        # range, or missing) is invisible to version selection instead of crashing an
        # unguarded `int(...)` coercion on disk corruption or an out-of-band edit. The on-disk
        # scan is unchanged — `parse_version_segment` already returns None for bad directory
        # names, which the `or 0` below folds into the same "ignore it" behavior.
        known = [r["version"] for r in rows if r.get("slug") == slug and ms.valid_version(r.get("version"))]
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
            # Fix round 1, F2: two different failure modes used to share one raw ValueError
            # message. Check the version ceiling explicitly first (a real "no versions left"
            # condition); only once that has passed does a None path mean module_html_path's
            # own containment check rejected a symlinked/escaping slug directory — a different
            # failure that deserves its own status rather than a mislabeled "surum_siniri".
            if version > ms.VERSION_MAX:
                raise ValueError("surum_siniri")
            path = ms.module_html_path(self.data_dir, slug, version)
            if path is None:
                raise ValueError("yol_reddedildi")
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
        try:
            draft = self.drafts.load(taslak_id) if ms.valid_taslak_id(taslak_id) else None
            if draft is None:
                return {**base, "status": "taslak_bulunamadi"}
            if _refuses_for_fail(draft):
                return {**base, "status": "kapi_fail", "fail_kapilari": _fail_gate_names(draft),
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
            chosen = slug if slug is not None else slug_turet(meta.get("subject"), meta.get("gradeLevel"),
                                                              meta.get("title"))
            html = self.drafts.html_bytes(taslak_id)
            if html is None or hashlib.sha256(html).hexdigest() != draft.get("sha256"):
                return {**base, "status": "taslak_bozuk"}
            record = self.catalog.yayinla(email, draft, html, chosen, link)
        except ValueError as exc:
            # Fix round 1, F3: the three closed reasons CatalogWriter.yayinla itself raises
            # pass through verbatim (surum_siniri also carries the current limit); anything
            # else — including a ValueError this function never documented — is an unclosed
            # internal failure and falls through to the same sunucu_hatasi as any other
            # exception, never the raw exception text.
            reason = str(exc)
            if reason not in _KNOWN_REASONS:
                return _sunucu_hatasi(base)
            body = {**base, "status": reason}
            if reason == "surum_siniri":
                body["sinir"] = ms.VERSION_MAX
            return body
        except Exception:
            return _sunucu_hatasi(base)
        return {"status": "ok", "slug": record["slug"], "version": record["version"], "url": self._url(record),
                "mcp_verified": False}

    def katalog(self, ders: str | None = None, sinif: str | None = None, durum: str | None = None) -> dict[str, Any]:
        durum = durum or "active"
        if durum not in DURUMLAR:
            return {"status": "gecersiz_durum", "izinli": list(DURUMLAR), "mcp_verified": False}
        try:
            rows = self.catalog.listele(ders, sinif, durum)
            cards = [{**{k: row.get(k) for k in _CARD_FIELDS}, "url": self._url(row)} for row in rows]
        except Exception:
            return _sunucu_hatasi({"mcp_verified": False})
        return {"status": "ok", "sayi": len(cards), "moduller": cards, "mcp_verified": False}

    def kaldir(self, email: str, slug: str) -> dict[str, Any]:
        if not ms.valid_slug(slug):
            return {"status": "gecersiz_slug", "slug": slug, "mcp_verified": False}
        base = {"slug": slug, "mcp_verified": False}
        try:
            count = self.catalog.kaldir(email, slug)
        except Exception:
            return _sunucu_hatasi(base)
        if not count:
            return {**base, "status": "bulunamadi"}
        return {**base, "status": "ok", "kaldirilan_surum_sayisi": count,
                "not": "Dosyalar silinmez; sürümler removed işaretlenir ve katalogdan düşer."}
