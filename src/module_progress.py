"""Per-version module progress (spec §5.5): event validation, aggregation, locked single writer.

The dashboard is the only writer (spec §4.2), but gunicorn runs it as two worker processes
with four threads each, so every read-modify-write holds fcntl.flock on a sidecar lock file.
The JSON itself is still replaced atomically, so readers (ted-mcp) never see a partial file
and never need the lock.
"""
from __future__ import annotations

import fcntl
import json
import os
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from src.json_utils import atomic_json_dump
from src.module_store import valid_slug, valid_version

EVENTS = frozenset({"answer", "segment_complete", "module_complete", "ready"})
SEGMENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
USER_HASH_RE = re.compile(r"^[0-9a-f]{32}$")
_ALLOWED_KEYS = frozenset({"type", "v", "slug", "version", "event", "segmentId", "item",
                           "correct", "attempts", "xp", "ts"})
MAX_ANSWERS = 1000
MAX_DONE = 500
XP_MAX = 1_000_000
EMPTY_STATE = {"answers": [], "done": [], "xp": 0}


class ProgressEventError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _int(value: Any, lo: int, hi: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and lo <= value <= hi


def validate_event(payload: Any, slug: str, version: int) -> dict[str, Any]:
    """Normalise an untrusted progress message or raise ProgressEventError(reason)."""
    if not isinstance(payload, dict):
        raise ProgressEventError("nesne_degil")
    if set(payload) - _ALLOWED_KEYS:
        raise ProgressEventError("bilinmeyen_alan")
    if payload.get("type") != "edupedia:progress" or payload.get("v") != 1:
        raise ProgressEventError("tip")
    if payload.get("slug") != slug or payload.get("version") != version:
        raise ProgressEventError("modul_uyusmazligi")
    event = payload.get("event")
    if event not in EVENTS:
        raise ProgressEventError("olay")
    if not _int(payload.get("xp"), 0, XP_MAX):
        raise ProgressEventError("xp")
    if not _int(payload.get("ts"), 1, 10**14):
        raise ProgressEventError("ts")
    out: dict[str, Any] = {"event": event, "xp": payload["xp"]}
    if event in ("answer", "segment_complete"):
        segment = payload.get("segmentId")
        if not isinstance(segment, str) or not SEGMENT_ID_RE.fullmatch(segment):
            raise ProgressEventError("segmentId")
        out["segmentId"] = segment
    if event == "answer":
        if not _int(payload.get("item"), 0, 999):
            raise ProgressEventError("item")
        if not isinstance(payload.get("correct"), bool):
            raise ProgressEventError("correct")
        if not _int(payload.get("attempts"), 1, 99):
            raise ProgressEventError("attempts")
        out.update(item=payload["item"], correct=payload["correct"], attempts=payload["attempts"])
    return out


def _iso(now: float) -> str:
    return datetime.fromtimestamp(now, timezone.utc).isoformat(timespec="seconds")


def _restore_view(person: dict[str, Any]) -> dict[str, Any]:
    answers = [key for key, row in (person.get("cevaplar") or {}).items() if row.get("dogru")]
    return {"answers": answers, "done": list(person.get("tamamlanan") or []), "xp": int(person.get("xp") or 0)}


class ProgressStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.lock_path = self.path.with_name(self.path.name + ".lock")

    @contextmanager
    def _locked(self) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"surum": 1, "moduller": {}}
        if not isinstance(data, dict) or not isinstance(data.get("moduller"), dict):
            return {"surum": 1, "moduller": {}}
        return data

    def record(self, user_hash: str, slug: str, version: int, event: dict[str, Any], now: float) -> dict[str, Any]:
        if not valid_slug(slug) or not valid_version(version) or not USER_HASH_RE.fullmatch(user_hash or ""):
            raise ValueError("gecersiz_kimlik")
        with self._locked():
            data = self.read()
            people = data["moduller"].setdefault(slug, {}).setdefault(f"v{version}", {}).setdefault("kisiler", {})
            person = people.setdefault(user_hash, {"cevaplar": {}, "tamamlanan": [], "xp": 0, "bitti": False,
                                                   "ilk_erisim": _iso(now)})
            kind = event["event"]
            if kind == "answer":
                key = f"{event['segmentId']}#{event['item']}"
                answers = person["cevaplar"]
                if key in answers or len(answers) < MAX_ANSWERS:
                    row = answers.setdefault(key, {"deneme": 0, "dogru": False})
                    row["deneme"] = max(int(row["deneme"]), event["attempts"])
                    row["dogru"] = bool(row["dogru"]) or event["correct"]
            elif kind == "segment_complete":
                done = person["tamamlanan"]
                if event["segmentId"] not in done and len(done) < MAX_DONE:
                    done.append(event["segmentId"])
            elif kind == "module_complete":
                person["bitti"] = True
            person["xp"] = max(int(person.get("xp") or 0), event["xp"])
            person["son_erisim"] = _iso(now)
            atomic_json_dump(data, str(self.path))
            return _restore_view(person)

    def state_for(self, user_hash: str, slug: str, version: int) -> dict[str, Any]:
        people = ((self.read()["moduller"].get(slug) or {}).get(f"v{version}") or {}).get("kisiler") or {}
        person = people.get(user_hash)
        return _restore_view(person) if isinstance(person, dict) else dict(EMPTY_STATE, answers=[], done=[])

    def summary(self, slug: str, version: int | None = None) -> dict[str, Any]:
        versions = self.read()["moduller"].get(slug) or {}
        rows = []
        for key, entry in versions.items():
            if not (isinstance(key, str) and key.startswith("v") and key[1:].isdigit()):
                continue
            number = int(key[1:])
            if version is not None and number != version:
                continue
            people = (entry or {}).get("kisiler") or {}
            answered = correct = attempts = finished = 0
            last = ""
            for person in people.values():
                for row in (person.get("cevaplar") or {}).values():
                    answered += 1
                    correct += 1 if row.get("dogru") else 0
                    attempts += int(row.get("deneme") or 0)
                finished += 1 if person.get("bitti") else 0
                last = max(last, str(person.get("son_erisim") or ""))
            rows.append({
                "version": number, "kisi_sayisi": len(people), "cevaplanan_soru": answered,
                "dogru_orani": round(correct / answered, 3) if answered else None,
                "deneme_toplam": attempts, "tamamlayan": finished, "son_erisim": last or None,
            })
        return {"slug": slug, "surumler": sorted(rows, key=lambda r: r["version"])}
