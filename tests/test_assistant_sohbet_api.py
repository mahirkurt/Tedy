"""Session-owned conversations and family read access; no model network calls."""
import io
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src import dashboard_api
from src.assistant_sohbet import SohbetDeposu

ISIK = "student@example.test"
AILE = "parent@example.test"
DIGER = "other-parent@example.test"
OKUR = "reader@example.test"
SIMDI = datetime(2026, 10, 3, 8, 0, tzinfo=timezone.utc)


@pytest.fixture
def istemci(monkeypatch, tmp_path):
    monkeypatch.setattr(dashboard_api, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", True)
    monkeypatch.setattr(dashboard_api, "USER_ROLES", {
        ISIK: "full", AILE: "full", DIGER: "full", OKUR: "reader",
    })
    monkeypatch.setattr(dashboard_api, "OGRENCI_EMAILS", {ISIK}, raising=False)
    monkeypatch.setattr(dashboard_api, "okur_turu", lambda e:
        "ogrenci" if e == ISIK else "aile" if e in {AILE, DIGER} else "bilinmiyor")
    monkeypatch.setattr(dashboard_api, "_asistan_simdi", lambda: SIMDI, raising=False)
    dashboard_api.app.config["TESTING"] = True
    with dashboard_api.app.test_client() as c:
        yield c


def _giris(c, email):
    with c.session_transaction() as ses:
        ses["user_email"] = email


def _sohbet_deposu():
    return SohbetDeposu(Path(dashboard_api.OUTPUT_DIR) / "assistant_sohbetler.sqlite")


def test_sahip_yazar_aile_okur_yazamaz(istemci):
    _giris(istemci, ISIK)
    yarat = istemci.post("/api/assistant/sohbetler", json={"ogretmen": "matematik"})
    assert yarat.status_code == 200
    sid = yarat.get_json()["id"]
    assert "sahip_email" not in yarat.get_json()
    mesaj = istemci.post("/api/assistant/sohbetler/" + sid + "/mesaj",
                         json={"icerik": "Payda eşitle", "ogretmen": "matematik"})
    assert mesaj.status_code == 200
    liste = istemci.get("/api/assistant/sohbetler").get_json()["sohbetler"]
    assert liste[0]["baslik"] == "Payda eşitle"
    _giris(istemci, AILE)
    assert istemci.get("/api/assistant/sohbetler").get_json()["sohbetler"] == []
    aile = istemci.get("/api/assistant/sohbetler?kisi=ogrenci")
    assert aile.status_code == 200
    assert aile.get_json()["sohbetler"][0]["id"] == sid
    oku = istemci.get("/api/assistant/sohbetler/" + sid)
    assert oku.status_code == 200
    assert "sahip_email" not in oku.get_json()["sohbet"]
    yaz = istemci.patch("/api/assistant/sohbetler/" + sid, json={"baslik": "X"})
    assert yaz.status_code == 403
    assert yaz.get_json()["error"] == "Bu sohbet salt okunur."
    assert istemci.delete("/api/assistant/sohbetler/" + sid).status_code == 403


def test_yabanci_ve_yok_ayni_404(istemci):
    _giris(istemci, AILE)
    sid = istemci.post("/api/assistant/sohbetler", json={}).get_json()["id"]
    _giris(istemci, "other-parent@example.test")
    diger = istemci.get("/api/assistant/sohbetler/" + sid)
    _giris(istemci, ISIK)
    yok = istemci.get("/api/assistant/sohbetler/" + "ab" * 16)
    yabanci = istemci.get("/api/assistant/sohbetler/" + sid)
    assert yok.status_code == yabanci.status_code == diger.status_code == 404
    assert yok.get_json() == yabanci.get_json() == diger.get_json() == {"error": "Sohbet bulunamadı."}


def test_okur_403(istemci, monkeypatch):
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)
    _giris(istemci, OKUR)
    assert istemci.get("/api/assistant/sohbetler").status_code == 403


def test_bilinmeyen_kisi_400(istemci):
    _giris(istemci, AILE)
    res = istemci.get("/api/assistant/sohbetler?kisi=aile")
    assert res.status_code == 400
    assert res.get_json()["error"] == "Bilinmeyen kişi."
