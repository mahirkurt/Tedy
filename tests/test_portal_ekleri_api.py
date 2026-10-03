"""Serving portal attachments (plan 2026-09-28-portal-ekleri, Görev 8): the file,
with Range, for the full role only; and tedyUrl/status in every payload."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TEST_AUTH_BYPASS"] = "1"

from src.portal_ekleri import EkDeposu, ek_kimligi  # noqa: E402
from tests.sahte_http import DRIVE_URL, PDF, SP_DUVAR_URL, SP_URL, YOUTUBE  # noqa: E402

KIMLIK = ek_kimligi(SP_URL)
DUVAR = ek_kimligi(SP_DUVAR_URL)
DRIVE = ek_kimligi(DRIVE_URL)

VERI = {
    "odevlerim": {"summary": "", "homework": {"headers": [], "rows": [{
        "Ders Adı": "Sosyal Bilgiler", "Ödev Başlığı": "Kitap okuma ödevi",
        "Ödev Son Teslim Tarihi": "30.09.2026 12:00", "Ödev Durumu": "Değerlendirilmemiş",
        "detail": {"description": "Sayfa 12-13", "attachments": [
            {"name": "Sayfa 12-13.pdf", "url": SP_URL},
            {"name": "Kitap sayfaları", "url": SP_DUVAR_URL},
            {"name": "Konu videosu", "url": YOUTUBE}]}}]}},
    "ek_sayfalar": {"mla_kaynakca": {"title": "MLA Kaynakça Hazırlama Rehberi", "empty": False,
                                     "text": "Rehber", "documents": [DRIVE_URL]}},
    "duyurular": {"announcements": [{"e-Posta Başlık": "Gezi izni", "Yayın Tarihi": "22.09.2026",
                                     "Ekleri": "izin-formu.pdf", "Ekleri_url": SP_URL}]},
}


@pytest.fixture
def api(tmp_path, monkeypatch):
    import src.dashboard_api as api
    depo = EkDeposu(tmp_path)
    depo.dizin.mkdir(parents=True)
    (depo.dizin / f"{KIMLIK}.pdf").write_bytes(PDF)
    (depo.dizin / f"{DRIVE}.bin").write_bytes(b"bilinmeyen")
    depo.yaz({
        KIMLIK: {"id": KIMLIK, "status": "indirildi", "file": f"{KIMLIK}.pdf", "ext": ".pdf",
                 "mime": "application/pdf", "name": "Sayfa 12-13.pdf"},
        DUVAR: {"id": DUVAR, "status": "erisilemedi", "reason": "kaynak giriş istiyor; paylaşım herkese açık değil"},
        DRIVE: {"id": DRIVE, "status": "indirildi", "file": f"{DRIVE}.bin", "ext": ".bin",
                "mime": "application/octet-stream", "name": "MLA Kaynakça Hazırlama Rehberi"},
    })
    monkeypatch.setattr(api, "EK_PROJE_KOKU", str(tmp_path))
    monkeypatch.setattr(api, "OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setattr(api, "_scraped", lambda: json.loads(json.dumps(VERI)))
    monkeypatch.setattr(api, "_load_photo_homework_rows", lambda: [])
    api.app.config["TESTING"] = True
    return api


def test_dosyayi_satir_ici_ve_dogru_turle_sunar(api):
    with api.app.test_client() as c:
        cevap = c.get(f"/api/ekler/{KIMLIK}")
    assert cevap.status_code == 200 and cevap.data == PDF
    assert cevap.mimetype == "application/pdf"
    assert cevap.headers["Content-Disposition"].startswith("inline")
    assert "Sayfa" in cevap.headers["Content-Disposition"]
    assert cevap.headers["X-Content-Type-Options"] == "nosniff"
    assert cevap.headers["Cache-Control"] == "private, max-age=3600"


def test_range_ile_parca_sunar(api):
    with api.app.test_client() as c:
        cevap = c.get(f"/api/ekler/{KIMLIK}", headers={"Range": "bytes=0-3"})
    assert cevap.status_code == 206 and cevap.data == b"%PDF"
    assert cevap.headers["Content-Range"] == f"bytes 0-3/{len(PDF)}"


def test_bilinmeyen_tur_indirme_olarak_sunulur(api):
    with api.app.test_client() as c:
        cevap = c.get(f"/api/ekler/{DRIVE}")
    assert cevap.status_code == 200
    assert cevap.headers["Content-Disposition"].startswith("attachment")


@pytest.mark.parametrize("ek_id", [DUVAR, "0123456789abcdef", "ABCDEF0123456789"])
def test_olmayan_ya_da_indirilmemis_ek_404(api, ek_id):
    with api.app.test_client() as c:
        cevap = c.get(f"/api/ekler/{ek_id}")
    assert cevap.status_code == 404 and cevap.get_json()["error"] == api.EK_YOK


def test_okur_reddedilir_full_rol_alir(api, monkeypatch):
    monkeypatch.setattr(api, "TEST_AUTH_BYPASS", False)
    okur = next(e for e, r in api.USER_ROLES.items() if r == api.ROLE_READER)
    tam = next(e for e, r in api.USER_ROLES.items() if r == api.ROLE_FULL)
    with api.app.test_client() as c:
        assert c.get(f"/api/ekler/{KIMLIK}").status_code == 401
        with c.session_transaction() as s:
            s["user_email"] = okur
        assert c.get(f"/api/ekler/{KIMLIK}").status_code == 403
        with c.session_transaction() as s:
            s["user_email"] = tam
        assert c.get(f"/api/ekler/{KIMLIK}").status_code == 200
    assert "portal_eki" not in api.READER_ENDPOINTS


def test_odev_yuku_ek_durumunu_tasir(api):
    with api.app.test_client() as c:
        ekler = c.get("/api/homework").get_json()["homework"][0]["detail"]["attachments"]
    assert ekler[0] == {"name": "Sayfa 12-13.pdf", "url": SP_URL, "id": KIMLIK,
                        "tedyUrl": f"/api/ekler/{KIMLIK}", "status": "indirildi"}
    assert ekler[1]["tedyUrl"] is None and ekler[1]["status"] == "erisilemedi"
    assert "giriş istiyor" in ekler[1]["reason"]
    assert ekler[2]["status"] == "baglanti" and ekler[2]["id"] is None


def test_sayfa_ve_duyuru_yukleri(api):
    with api.app.test_client() as c:
        sayfa = c.get("/api/pages").get_json()["pages"]["mla_kaynakca"]
        duyuru = c.get("/api/announcements").get_json()["announcements"][0]
    assert sayfa["documents"] == [DRIVE_URL]                      # unchanged for old readers
    assert sayfa["attachments"][0]["tedyUrl"] == f"/api/ekler/{DRIVE}"
    assert sayfa["attachments"][0]["name"] == "MLA Kaynakça Hazırlama Rehberi"
    assert duyuru["Ekleri_url"] == SP_URL
    assert duyuru["ekler"] == [{"name": "izin-formu.pdf", "url": SP_URL, "id": KIMLIK,
                                "tedyUrl": f"/api/ekler/{KIMLIK}", "status": "indirildi"}]


def test_asistanin_odev_kaynagi_da_ek_kimligini_tasir(api):
    ekler = api._canli_odevler()[0]["detail"]["attachments"]
    assert [e["id"] for e in ekler] == [KIMLIK, DUVAR, None]


def test_izleyici_bozuksa_yuk_bozulmaz(api, tmp_path):
    EkDeposu(tmp_path).izleyici_yolu.write_text("{bozuk", encoding="utf-8")
    with api.app.test_client() as c:
        ekler = c.get("/api/homework").get_json()["homework"][0]["detail"]["attachments"]
    assert ekler[0]["status"] == "bekliyor" and ekler[0]["tedyUrl"] is None
