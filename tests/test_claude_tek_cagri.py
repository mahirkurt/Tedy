"""Homework photo and book translation on Claude — no network.

Both moved off Gemini on 2026-09-24 (the Gemini API terms forbid services
likely to be used by under-18s). The photo path also changed shape: Gemini
took any image/* up to 12 MB inline; Claude takes JPEG/PNG/GIF/WebP and at
most 5 MB per image, so every photo is normalised first — orientation from
EXIF, long edge at most 2000 px, JPEG — and a format Pillow cannot read is
refused with a sentence, not a stack trace.
"""
import base64
import io
import json
import os
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest
from PIL import Image

os.environ["TEST_AUTH_BYPASS"] = "1"
import src.dashboard_api as api  # noqa: E402


class _Sahte:
    def __init__(self, *cevaplar):
        self.cevaplar = list(cevaplar)
        self.istekler = []
        self.messages = self

    def create(self, **kw):
        self.istekler.append(kw)
        c = self.cevaplar.pop(0)
        if isinstance(c, Exception):
            raise c
        return c


def _cevap(metin, stop="end_turn"):
    return NS(content=[NS(type="thinking", thinking=""), NS(type="text", text=metin)], stop_reason=stop)


ODEV = {"homework": [{"ders_adi": "Matematik", "odev_basligi": "Test 2", "odev_kaynagi": "Fasikül",
                      "son_teslim_tarihi": "25.09.2026 12:00", "odev_durumu": "Değerlendirilmemiş",
                      "aciklama": "sayfa 11-12"}]}


def _gorsel(w, h, bicim="PNG", exif_yonu=None):
    img = Image.new("RGB", (w, h), "white")
    buf = io.BytesIO()
    if exif_yonu:
        exif = img.getexif()
        exif[0x0112] = exif_yonu
        img.save(buf, bicim, exif=exif)
    else:
        img.save(buf, bicim)
    return buf.getvalue()


def _gonderilen_gorsel(sahte):
    blok = sahte.istekler[0]["messages"][0]["content"][0]
    assert blok["type"] == "image"
    return blok, Image.open(io.BytesIO(base64.b64decode(blok["source"]["data"])))


@pytest.fixture
def sahte_claude(monkeypatch):
    def kur(*cevaplar):
        s = _Sahte(*cevaplar)
        monkeypatch.setattr(api.claude_api, "istemci", lambda **k: s)
        return s
    return kur


# ── homework photo ────────────────────────────────────────────────────────────

def test_foto_claude_ile_yapilandirilmis_cikti(sahte_claude):
    s = sahte_claude(_cevap(json.dumps(ODEV)))
    rows = api._extract_homework_candidates_from_photo(_gorsel(3000, 1000), "image/png")
    assert rows[0]["ders_adi"] == "Matematik" and rows[0]["son_teslim_tarihi"] == "25.09.2026 12:00"

    istek = s.istekler[0]
    assert istek["model"] == "claude-sonnet-5"
    assert istek["output_config"]["format"]["type"] == "json_schema"
    assert not {"temperature", "top_p", "top_k"} & set(istek)
    blok, gorsel = _gonderilen_gorsel(s)
    assert blok["source"]["media_type"] == "image/jpeg" and gorsel.format == "JPEG"
    assert max(gorsel.size) <= 2000
    # Image first, then the instruction.
    assert istek["messages"][0]["content"][1]["type"] == "text"


def test_foto_exif_yonu_duzeltilir(sahte_claude):
    # A phone photo taken sideways arrives with EXIF orientation 6; sent as-is
    # the worksheet would be read on its side.
    s = sahte_claude(_cevap(json.dumps(ODEV)))
    api._extract_homework_candidates_from_photo(_gorsel(300, 100, "JPEG", exif_yonu=6), "image/jpeg")
    _, gorsel = _gonderilen_gorsel(s)
    assert gorsel.size == (100, 300)


def test_foto_okunamayan_bicim_cumleyle_reddedilir():
    with pytest.raises(api.GorselOkunamadi, match="JPEG ya da PNG"):
        api._extract_homework_candidates_from_photo(b"not-an-image", "image/heic")


def test_foto_uc_noktasi_okunamayan_gorselde_415_doner():
    api.app.config["TESTING"] = True
    with api.app.test_client() as c:
        res = c.post("/api/homework/photo", data={
            "photo": (io.BytesIO(b"not-an-image"), "odev.heic", "image/heic")},
            content_type="multipart/form-data")
    assert res.status_code == 415
    assert "okunamadı" in res.get_json()["error"]


def test_foto_servis_hatasi_ic_ayrinti_sizdirmaz(sahte_claude):
    import anthropic
    sahte_claude(anthropic.APIConnectionError(request=Mock()))
    with pytest.raises(RuntimeError, match="ulaşılamadı"):
        api._extract_homework_candidates_from_photo(_gorsel(100, 100), "image/png")


def test_foto_reddetme_bos_liste_sayilmaz(sahte_claude):
    sahte_claude(_cevap("", stop="refusal"))
    with pytest.raises(RuntimeError, match="işlemedi"):
        api._extract_homework_candidates_from_photo(_gorsel(100, 100), "image/png")


def test_foto_anahtar_yoksa_acik_hata():
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        api._extract_homework_candidates_from_photo(_gorsel(100, 100), "image/png")
