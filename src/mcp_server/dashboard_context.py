"""Read Işık's upcoming exams and homework through the dashboard's own loopback API.

The exam list is derived inside /api/exams (calendar + grade table + content map), so the
orchestrator reuses that endpoint instead of duplicating ~200 lines (spec §12b). Output is
privacy-reduced: no name, student number, photo or raw portal fields.
"""
from __future__ import annotations

import hashlib
import re
import time
from datetime import date, datetime, timedelta
from typing import Any, Callable

import requests


class DashboardUnavailable(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


_DUE_FORMATS = ("%d.%m.%Y %H:%M", "%d.%m.%Y")


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _parse_due(value: Any) -> datetime | None:
    text = str(value or "").strip()
    for fmt in _DUE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return _parse_iso(text)


def _grade_level(class_name: str) -> int | None:
    m = re.search(r"\b(1[0-2]|[1-9])\b", class_name or "")
    return int(m.group(1)) if m else None


class DashboardContext:
    def __init__(self, base_url: str, api_key: str, session: Any = None, timeout: float = 10.0,
                 clock: Callable[[], float] = time.time) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = session if session is not None else requests.Session()
        self.timeout = timeout
        self.clock = clock

    def _get(self, path: str) -> dict[str, Any]:
        try:
            resp = self.session.get(
                f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {self.api_key}", "User-Agent": "ted-mcp/0.1"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise DashboardUnavailable("unreachable") from exc
        if resp.status_code != 200:
            raise DashboardUnavailable(f"http_{resp.status_code}")
        try:
            body = resp.json()
        except ValueError as exc:
            raise DashboardUnavailable("undecodable") from exc
        if not isinstance(body, dict):
            raise DashboardUnavailable("unexpected_shape")
        return body

    def upcoming(self, gun: int) -> dict[str, Any]:
        today = datetime.fromtimestamp(self.clock()).date()
        until = today + timedelta(days=gun)
        exams = self._get("/api/exams").get("exams") or []
        homework = self._get("/api/homework").get("homework") or []
        profile = self._get("/api/student/profile")

        sinavlar, undated = [], 0
        for exam in exams:
            if not isinstance(exam, dict) or exam.get("status") != "upcoming":
                continue
            when = _parse_iso(exam.get("date"))
            if when is None:
                undated += 1
                continue
            if today <= when.date() <= until:
                sinavlar.append({"id": exam.get("id"), "ders": exam.get("course"), "baslik": exam.get("title"),
                                 "sinav_no": exam.get("examNumber"), "tarih": when.date().isoformat()})
        sinavlar.sort(key=lambda e: e["tarih"])

        odevler = []
        for row in homework:
            if not isinstance(row, dict) or row.get("student_marked_done"):
                continue
            due = _parse_due(row.get("Ödev Son Teslim Tarihi"))
            if due is None or not (today <= due.date() <= until):
                continue
            ders = row.get("normalized_course") or row.get("Ders Adı") or ""
            baslik = row.get("Ödev Başlığı") or ""
            son = due.strftime("%Y-%m-%dT%H:%M")
            odevler.append({
                "id": hashlib.sha1(f"{ders}|{baslik}|{son}".encode("utf-8")).hexdigest()[:12],
                "ders": ders, "baslik": baslik, "son_teslim": son, "durum": row.get("Ödev Durumu") or "",
            })
        odevler.sort(key=lambda o: o["son_teslim"])

        class_name = str(profile.get("class_name") or "")
        return {
            "sinif_adi": class_name,
            "sinif_duzeyi": _grade_level(class_name),
            "sube": profile.get("branch") or "",
            "sinavlar": sinavlar,
            "odevler": odevler,
            "tarihsiz_sinav_sayisi": undated,
        }
