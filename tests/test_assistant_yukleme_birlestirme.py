"""Ortak yükleme sınırları, kota ve ödeve bağlama; ağ kullanılmaz."""
import io
import json
import os
os.environ["TEST_AUTH_BYPASS"] = "1"
import subprocess
import zipfile
from datetime import timedelta

import pytest

from src import assistant_uploads as uploads, dashboard_api, homework_docs
from tests.test_assistant_sohbet_api import ISIK, AILE, SIMDI, _giris, istemci


def _zip(xml, extra=b""):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml", xml)
        if extra:
            z.writestr("media/blob", extra)
    return buf.getvalue()


def test_binary_nul_ve_bos_dosya_reddedilir():
    for data in (b"", b"text\x00payload", b"\x01binary"):
        with pytest.raises(uploads.YuklemeHatasi) as exc:
            uploads.tur_tespit(data)
        assert exc.value.status in (400, 415)


def test_docx_genisleme_ve_dtd_siniri(monkeypatch):
    monkeypatch.setattr(uploads, "DOCX_XML_SINIRI", 1000)
    for data in (_zip(b"<x>" + b"a" * 2000 + b"</x>"),
                 _zip(b"<x/>", b"a" * 2000)):
        with pytest.raises(uploads.YuklemeHatasi) as exc:
            uploads.docx_metni(data)
        assert exc.value.status == 413
    for xml in ('<!DOCTYPE x [<!ENTITY a "boom">]><x>&a;</x>',):
        for encoding in ("utf-8", "utf-16"):
            with pytest.raises(uploads.YuklemeHatasi) as exc:
                uploads.docx_metni(_zip(xml.encode(encoding)))
            assert exc.value.status == 415


def test_pdfinfo_sureli_ve_bozuk_pdf_reddi(monkeypatch):
    def gec(*args, **kwargs):
        assert kwargs["timeout"] == 10
        raise subprocess.TimeoutExpired("pdfinfo", 10)
    monkeypatch.setattr(uploads.subprocess, "run", gec)
    with pytest.raises(uploads.YuklemeHatasi) as exc:
        uploads.pdf_sayfa_sayisi(b"%PDF-1.4")
    assert exc.value.status == 415


def test_kota_sahibe_ozel_silme_ve_son_kullanim(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "KISI_KOTASI", 4)
    depo = uploads.EkDeposu(tmp_path)
    eski = SIMDI - timedelta(days=29)
    kayit = depo.kaydet(ISIK, "a.txt", "txt", 3, b"abc", eski)
    with pytest.raises(uploads.YuklemeHatasi) as exc:
        depo.kaydet(ISIK, "b.txt", "txt", 2, b"bb", eski)
    assert exc.value.status == 507
    assert depo.kaydet(AILE, "x.txt", "txt", 4, b"xxxx", eski)
    depo.dokun(ISIK, kayit["id"], SIMDI)
    assert depo.temizlik(SIMDI + timedelta(days=2)) == 1
    assert depo.oku(ISIK, kayit["id"]) is not None
    assert not depo.sil(AILE, kayit["id"])
    assert depo.sil(ISIK, kayit["id"])
    assert depo.oku(ISIK, kayit["id"]) is None


def test_ayni_andaki_kota_asimi_engellenir(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    monkeypatch.setattr(uploads, "KISI_KOTASI", 3)
    depo = uploads.EkDeposu(tmp_path)
    def yaz(_):
        try:
            depo.kaydet(ISIK, "a.txt", "txt", 3, b"abc", SIMDI)
            return 200
        except uploads.YuklemeHatasi as exc:
            return exc.status
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sorted(pool.map(yaz, range(4))) == [200, 507, 507, 507]


def _odev(monkeypatch):
    row = {"Ders Adı": "Matematik", "Ödev Başlığı": "Kesirler", "Ödev Son Teslim Tarihi": ""}
    monkeypatch.setattr(dashboard_api, "_scraped", lambda: {"odevlerim": {"homework": {"rows": [row]}}})
    monkeypatch.setattr(dashboard_api, "_load_photo_homework_rows", lambda: [])
    monkeypatch.setattr(homework_docs, "ollama_embed", lambda texts: [[1., 0.] for _ in texts])
    return dashboard_api._homework_row_key(row)


def test_belge_baglama_ve_sahip_silme(istemci, monkeypatch):
    key = _odev(monkeypatch)
    _giris(istemci, ISIK)
    kayit = istemci.post("/api/assistant/uploads", data={"dosya": (io.BytesIO(b"Kesirler."), "yalanci.pdf")}).get_json()
    url = f"/api/assistant/uploads/{kayit['id']}"
    _giris(istemci, AILE)
    assert istemci.post(url + "/odeve-bagla", json={"anahtar": key}).status_code == 404
    assert istemci.delete(url).status_code == 404
    _giris(istemci, ISIK)
    sonuc = istemci.post(url + "/odeve-bagla", json={"anahtar": key})
    assert sonuc.status_code == 200 and sonuc.get_json()["documents"][0]["ready"]
    assert istemci.delete(url).status_code == 204
    assert istemci.get(url).status_code == 404


def test_baglama_gorsel_ve_vektor_hatasi(istemci, monkeypatch):
    key = _odev(monkeypatch)
    _giris(istemci, ISIK)
    depo = uploads.EkDeposu(dashboard_api.OUTPUT_DIR)
    gorsel = depo.kaydet(ISIK, "a.jpg", "gorsel", 4, b"jpeg", SIMDI)
    assert istemci.post(f"/api/assistant/uploads/{gorsel['id']}/odeve-bagla", json={"anahtar": key}).status_code == 415
    metin = depo.kaydet(ISIK, "a.txt", "txt", 9, b"Kesirler.", SIMDI)
    def patlak(_):
        raise homework_docs.EmbedHatasi("private endpoint")
    monkeypatch.setattr(homework_docs, "ollama_embed", patlak)
    yanit = istemci.post(f"/api/assistant/uploads/{metin['id']}/odeve-bagla", json={"anahtar": key})
    assert yanit.status_code == 503 and "private" not in str(yanit.get_json())
    assert depo.oku(ISIK, metin["id"]) is not None
    monkeypatch.setattr(homework_docs, "ollama_embed", lambda texts: [[1., 0.] for _ in texts])
    tekrar = istemci.post(f"/api/assistant/uploads/{metin['id']}/odeve-bagla", json={"anahtar": key})
    assert tekrar.status_code == 200
    assert len(tekrar.get_json()["documents"]) == 1
    assert tekrar.get_json()["documents"][0]["ready"]


def test_homework_intake_turu_bayttan_ve_docx_guvenli(tmp_path):
    doc = homework_docs.ekle(tmp_path, "m|k|", "yanlis.pdf", b"Kesirler.", embed=lambda ts: [[1.] for _ in ts])
    assert doc["ready"]
    path, _, mime = homework_docs.dosya(tmp_path, doc["id"])
    assert path.suffix == ".txt" and mime.startswith("text/plain")
    with pytest.raises(homework_docs.BelgeReddedildi):
        homework_docs.ekle(tmp_path, "m|k|", "a.docx", _zip(b'<!DOCTYPE x [<!ENTITY a "x">]><x>&a;</x>'), embed=lambda ts: [[1.] for _ in ts])


def test_gecmis_ek_ozeti_bayt_okumadan_doner(istemci, monkeypatch):
    _giris(istemci, ISIK)
    sid = istemci.post("/api/assistant/sohbetler", json={}).get_json()["id"]
    ek = {"id": "ab" * 16, "ad": "Not.txt", "tur": "txt"}
    dashboard_api._sohbet_deposu().mesaj_ekle(sid, "user", "Oku", "genel", [ek], SIMDI)
    monkeypatch.setattr(uploads.EkDeposu, "oku", lambda *args: pytest.fail("GET history must not load file bytes"))
    body = istemci.get(f"/api/assistant/sohbetler/{sid}").get_json()
    assert body["mesajlar"][0]["yuklemeler"] == [ek]


def test_word_baglantisi_saklanan_utf8_ile_calisir(istemci, monkeypatch):
    from tests.test_assistant_uploads import _docx
    key = _odev(monkeypatch)
    _giris(istemci, ISIK)
    kayit = istemci.post("/api/assistant/uploads", data={"dosya": (io.BytesIO(_docx("Kesirler.")), "a.docx")}).get_json()
    yanit = istemci.post(f"/api/assistant/uploads/{kayit['id']}/odeve-bagla", json={"anahtar": key})
    assert yanit.status_code == 200
    assert yanit.get_json()["documents"][0]["name"] == "a.txt"
