"""edupedia_baglam: upcoming exams/homework from the dashboard loopback API, privacy-filtered."""
from datetime import datetime

import pytest
import requests

from src.mcp_server import tools as tools_mod
from src.mcp_server.config import load_settings
from src.mcp_server.dashboard_context import DashboardContext, DashboardUnavailable

NOW = datetime(2026, 9, 14, 9, 0).timestamp()  # Monday
FULL = "drmahirkurt@gmail.com"

EXAMS = {"exams": [
    {"id": "e1", "course": "Fen Bilimleri", "title": "1. Yazılı", "examNumber": 1, "date": "2026-09-18T00:00:00", "status": "upcoming"},
    {"id": "e2", "course": "Matematik", "title": "2. Yazılı", "examNumber": 2, "date": "2026-10-20T00:00:00Z", "status": "upcoming"},
    {"id": "e3", "course": "Türkçe", "title": "Sınav", "examNumber": None, "date": None, "status": "upcoming"},
    {"id": "e4", "course": "Fen Bilimleri", "title": "Eski", "examNumber": 1, "date": "2026-09-01T00:00:00", "status": "past"},
], "stats": {}}
HOMEWORK = {"summary": "", "homework": [
    {"Ders Adı": "FEN BİLİMLERİ", "normalized_course": "Fen Bilimleri", "Ödev Başlığı": "Madde döngüsü",
     "Ödev Son Teslim Tarihi": "16.09.2026 23:59", "Ödev Durumu": "Teslim edilmedi", "student_marked_done": False},
    {"Ders Adı": "MATEMATİK", "Ödev Başlığı": "Kesirler", "Ödev Son Teslim Tarihi": "2026-09-15T18:00:00",
     "Ödev Durumu": "Teslim edilmedi", "student_marked_done": True},
    {"Ders Adı": "TÜRKÇE", "Ödev Başlığı": "Okuma", "Ödev Son Teslim Tarihi": "30.10.2026", "Ödev Durumu": "", "student_marked_done": False},
]}
PROFILE = {"name": "Işık Kurt", "student_no": "123", "class_name": "5-A", "branch": "A",
           "photo_data_url": "data:image/png;base64,xx", "fields": {"TC": "1"}, "scraped_at": "", "auth": {}}


class Resp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, routes=None, error=None):
        self.routes = routes or {"/api/exams": Resp(200, EXAMS), "/api/homework": Resp(200, HOMEWORK),
                                 "/api/student/profile": Resp(200, PROFILE)}
        self.error = error
        self.seen = []

    def get(self, url, headers=None, timeout=None):
        self.seen.append((url, headers, timeout))
        if self.error:
            raise self.error
        return self.routes[url.split("127.0.0.1:8085", 1)[1]]


def _ctx(session):
    return DashboardContext("http://127.0.0.1:8085", "tdyK_test", session=session, clock=lambda: NOW)


def test_upcoming_filters_window_and_done_items():
    body = _ctx(FakeSession()).upcoming(7)
    assert [e["id"] for e in body["sinavlar"]] == ["e1"]
    assert body["sinavlar"][0] == {"id": "e1", "ders": "Fen Bilimleri", "baslik": "1. Yazılı", "sinav_no": 1, "tarih": "2026-09-18"}
    assert body["tarihsiz_sinav_sayisi"] == 1
    assert [o["baslik"] for o in body["odevler"]] == ["Madde döngüsü"]
    assert body["odevler"][0]["ders"] == "Fen Bilimleri"
    assert body["odevler"][0]["son_teslim"] == "2026-09-16T23:59"
    assert len(body["odevler"][0]["id"]) == 12


def test_upcoming_longer_window_includes_later_items():
    body = _ctx(FakeSession()).upcoming(60)
    assert {e["id"] for e in body["sinavlar"]} == {"e1", "e2"}
    assert {o["baslik"] for o in body["odevler"]} == {"Madde döngüsü", "Okuma"}


def test_profile_is_reduced_to_grade_and_branch():
    body = _ctx(FakeSession()).upcoming(7)
    assert body["sinif_adi"] == "5-A" and body["sinif_duzeyi"] == 5 and body["sube"] == "A"
    flat = repr(body)
    for secret in ("Işık Kurt", "123", "base64", "TC"):
        assert secret not in flat


def test_sends_bearer_to_loopback_with_timeout():
    session = FakeSession()
    _ctx(session).upcoming(7)
    url, headers, timeout = session.seen[0]
    assert url.startswith("http://127.0.0.1:8085/api/")
    assert headers["Authorization"] == "Bearer tdyK_test"
    assert timeout == 10.0


def test_http_error_and_network_error_are_unavailable():
    with pytest.raises(DashboardUnavailable) as exc:
        _ctx(FakeSession(routes={"/api/exams": Resp(401, {}), "/api/homework": Resp(200, HOMEWORK),
                                 "/api/student/profile": Resp(200, PROFILE)})).upcoming(7)
    assert exc.value.reason == "http_401"
    with pytest.raises(DashboardUnavailable) as exc:
        _ctx(FakeSession(error=requests.ConnectionError("down"))).upcoming(7)
    assert exc.value.reason == "unreachable"


class NoFed:
    def configured(self, server):
        return False


def test_tools_baglam_degrades_without_key_and_clamps_window(tmp_path):
    settings = load_settings({}, project_root=tmp_path)
    t = tools_mod.Tools(settings, NoFed(), dashboard=None)
    body = t.baglam(FULL, gun=7)
    assert body["status"] == "degraded" and body["coverage"] == {"tedy-dashboard": "skipped:anahtar yok"}

    settings = load_settings({"TED_DASHBOARD_API_KEY": "tdyK_test"}, project_root=tmp_path)
    t = tools_mod.Tools(settings, NoFed(), dashboard=_ctx(FakeSession()))
    body = t.baglam(FULL, gun=500)
    assert body["status"] == "ok" and body["gun"] == 60
    assert body["coverage"] == {"tedy-dashboard": "hit"}
    assert body["mcp_verified"] is False and body["caveat"]

    t = tools_mod.Tools(settings, NoFed(), dashboard=_ctx(FakeSession(error=requests.Timeout("slow"))))
    body = t.baglam(FULL)
    assert body["status"] == "degraded" and body["coverage"] == {"tedy-dashboard": "degraded:unreachable"}
