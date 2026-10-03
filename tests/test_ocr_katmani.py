"""OCR layer (plan 2026-09-28-portal-ekleri, Görev 14): Claude Haiku 4.5 vision per
textless page, a per-page cache, a monthly USD cap and the Tesseract fallback.
The paid API is never called: the reader is tests/sahte_ocr.SahteOkuyucu, and
ClaudeGorselOkuyucu's own test runs against a fake Anthropic client."""
from datetime import datetime
from types import SimpleNamespace

import pytest

import src.ocr_katmani as ocr
from src.ocr_katmani import (AYLIK_TAVAN_USD, SAYFA_TAHMINI_USD, ClaudeGorselOkuyucu, OcrDefteri,
                             OcrKatmani, pdf_sayfa_metinleri, tesseract_verisinden)
from tests.sahte_ocr import MARKDOWN, Saat, SahteOkuyucu, SahteTesseract, taranmis_pdf

EYLUL = datetime(2026, 9, 28, 10, 0)
EKIM = datetime(2026, 10, 1, 9, 0)
FF = chr(12)


def _katman(kok, okuyucu, tesseract=None, simdi=lambda: EYLUL, **kw):
    return OcrKatmani(kok, okuyucu=okuyucu, tesseract=tesseract or SahteTesseract(), simdi=simdi, **kw)


def test_taranmis_pdf_metin_katmani_tasimaz(tmp_path):
    pdf = taranmis_pdf(tmp_path / "t.pdf", icerikli=2, bos=1)
    assert [s.strip() for s in pdf_sayfa_metinleri(pdf, 30)] == ["", "", ""]


def test_metinsiz_sayfa_claude_ile_okunur_bos_sayfa_para_harcamaz(tmp_path):
    pdf = taranmis_pdf(tmp_path / "t.pdf", icerikli=1, bos=1)
    okuyucu = SahteOkuyucu()
    katman = _katman(tmp_path, okuyucu)
    sonuc = katman.pdf_oku(pdf, katman.saat() + 60)
    assert len(okuyucu.cagrilar) == 1                    # the white page cost nothing
    assert (sonuc.ocr_sayfalari, sonuc.eksik, sonuc.metinsiz, sonuc.ilerleme) == ([1], [], 2, "2/2")
    ilk, ikinci = sonuc.metin.split(FF)
    assert ilk == "[PDF s.1 · OCR · Claude Haiku 4.5 · güven %90]\n" + MARKDOWN
    assert ikinci == ""
    assert katman.defter.harcanan() == pytest.approx((2400 * 1.0 + 300 * 5.0) / 1_000_000)


def test_bir_sayfa_bir_kez_okunur(tmp_path):
    pdf = taranmis_pdf(tmp_path / "t.pdf")
    okuyucu = SahteOkuyucu()
    katman = _katman(tmp_path, okuyucu)
    katman.pdf_oku(pdf, katman.saat() + 60)
    harcanan = katman.defter.harcanan()
    ikinci = katman.pdf_oku(pdf, katman.saat() + 60)
    assert len(okuyucu.cagrilar) == 1 and katman.defter.harcanan() == harcanan
    assert MARKDOWN in ikinci.metin


def test_istem_surumu_degisince_yeniden_okunur(tmp_path, monkeypatch):
    pdf = taranmis_pdf(tmp_path / "t.pdf")
    okuyucu = SahteOkuyucu()
    katman = _katman(tmp_path, okuyucu)
    katman.pdf_oku(pdf, katman.saat() + 60)
    monkeypatch.setattr(ocr, "ISTEM_SURUMU", "2")
    katman.pdf_oku(pdf, katman.saat() + 60)
    assert len(okuyucu.cagrilar) == 2


def test_aylik_tavanda_tesseract_a_duser_defter_degismez(tmp_path):
    assert AYLIK_TAVAN_USD == 10.0
    pdf = taranmis_pdf(tmp_path / "t.pdf")
    okuyucu, tesseract = SahteOkuyucu(), SahteTesseract()
    katman = _katman(tmp_path, okuyucu, tesseract)
    katman.defter.yaz("claude:claude-haiku-4-5", 10_000_000, 0)      # 10.00 USD spent this month
    assert not katman.defter.izin_var()
    sonuc = katman.pdf_oku(pdf, katman.saat() + 60)
    assert okuyucu.cagrilar == [] and tesseract.cagrilar == 1
    assert sonuc.metin.startswith("[PDF s.1 · OCR, güven düşük · Tesseract]\n")
    assert sonuc.dusuk_guvenli == [1]
    assert katman.defter.harcanan() == pytest.approx(10.0)


def test_tavan_bir_sayfanin_en_kotu_maliyetine_yer_birakir(tmp_path):
    defter = OcrDefteri(tmp_path / "d.json", tavan=10.0, simdi=lambda: EYLUL)
    defter.yaz("m", int((10.0 - SAYFA_TAHMINI_USD) * 1_000_000) + 1, 0)
    assert not defter.izin_var()
    assert OcrDefteri(tmp_path / "d.json", tavan=10.0, simdi=lambda: EKIM).izin_var()   # a new month


def test_defter_olcumu_ay_ay_kaydeder(tmp_path):
    defter = OcrDefteri(tmp_path / "ocr_defteri.json", simdi=lambda: EYLUL)
    assert defter.yaz("claude:claude-haiku-4-5", 2400, 300) == pytest.approx(0.0039)
    import json
    ay = json.loads((tmp_path / "ocr_defteri.json").read_text(encoding="utf-8"))["aylar"]["2026-09"]
    assert ay == {"usd": pytest.approx(0.0039), "sayfa": 1, "girdi_token": 2400, "cikti_token": 300}


def test_api_hatasinda_tesseract_a_duser_para_yazilmaz(tmp_path):
    pdf = taranmis_pdf(tmp_path / "t.pdf")
    okuyucu, tesseract = SahteOkuyucu(hata=RuntimeError("529 overloaded")), SahteTesseract(guven=0.8)
    katman = _katman(tmp_path, okuyucu, tesseract)
    sonuc = katman.pdf_oku(pdf, katman.saat() + 60)
    assert len(okuyucu.cagrilar) == 1 and tesseract.cagrilar == 1
    assert sonuc.metin.startswith("[PDF s.1 · OCR · Tesseract · güven %80]\n")
    assert katman.defter.harcanan() == 0.0


def test_ret_kullanimini_yazar_ve_tesseract_a_duser(tmp_path):
    pdf = taranmis_pdf(tmp_path / "t.pdf")
    okuyucu, tesseract = SahteOkuyucu(reddet=True), SahteTesseract()
    katman = _katman(tmp_path, okuyucu, tesseract)
    katman.pdf_oku(pdf, katman.saat() + 60)
    assert tesseract.cagrilar == 1 and katman.defter.harcanan() > 0


def test_yeni_ay_dusuk_guvenli_tesseract_sayfasini_claude_ile_yeniler(tmp_path):
    pdf = taranmis_pdf(tmp_path / "t.pdf")
    an = {"t": EYLUL}
    okuyucu, tesseract = SahteOkuyucu(), SahteTesseract(guven=0.45)
    katman = _katman(tmp_path, okuyucu, tesseract, simdi=lambda: an["t"])
    katman.defter.yaz("claude:claude-haiku-4-5", 10_000_000, 0)
    katman.pdf_oku(pdf, katman.saat() + 60)
    an["t"] = EKIM
    sonuc = katman.pdf_oku(pdf, katman.saat() + 60)
    assert len(okuyucu.cagrilar) == 1 and tesseract.cagrilar == 1
    assert "Claude Haiku 4.5" in sonuc.metin and sonuc.dusuk_guvenli == []


def test_yuksek_guvenli_tesseract_sonucu_kalir(tmp_path):
    pdf = taranmis_pdf(tmp_path / "t.pdf")
    an = {"t": EYLUL}
    okuyucu, tesseract = SahteOkuyucu(), SahteTesseract(guven=0.85)
    katman = _katman(tmp_path, okuyucu, tesseract, simdi=lambda: an["t"])
    katman.defter.yaz("claude:claude-haiku-4-5", 10_000_000, 0)
    katman.pdf_oku(pdf, katman.saat() + 60)
    an["t"] = EKIM
    katman.pdf_oku(pdf, katman.saat() + 60)
    assert okuyucu.cagrilar == [] and tesseract.cagrilar == 1


def test_sure_dolunca_kalan_sayfa_sonraki_turda_surer(tmp_path):
    pdf = taranmis_pdf(tmp_path / "t.pdf", icerikli=3)
    saat = Saat()
    okuyucu, tesseract = SahteOkuyucu(saat=saat, adim=10.0), SahteTesseract()
    katman = _katman(tmp_path, okuyucu, tesseract, saat=saat)
    sonuc = katman.pdf_oku(pdf, son_an=25.0)              # pages 1–2 fit; 5 s left for page 3
    assert sonuc.eksik == [3] and sonuc.ilerleme == "2/3" and tesseract.cagrilar == 0
    sonuc = katman.pdf_oku(pdf, son_an=saat() + 100)
    assert sonuc.eksik == [] and len(okuyucu.cagrilar) == 3   # pages 1–2 came from the cache


def test_claude_okuyucusu_istegi_ve_okunabilirligi(monkeypatch):
    gonderilen, alinan = {}, {}

    def yanit(stop="end_turn", metin=MARKDOWN + "\n<!-- okunabilirlik: yuksek -->"):
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=metin)], stop_reason=stop,
                               usage=SimpleNamespace(input_tokens=2412, output_tokens=180))
    cevaplar = [yanit(), yanit(stop="max_tokens", metin="# Yarım"), yanit(stop="refusal", metin="")]

    class Istemci:
        def __init__(self):
            self.messages = SimpleNamespace(create=self.create)

        def create(self, **kw):
            gonderilen.update(kw)
            return cevaplar.pop(0)

    def istemci(timeout, max_retries=1):
        alinan.update(timeout=timeout, max_retries=max_retries)
        return Istemci()
    monkeypatch.setattr("src.claude_api.istemci", istemci)
    monkeypatch.delenv("OCR_CLAUDE_MODEL", raising=False)
    okuyucu = ClaudeGorselOkuyucu()
    bir = okuyucu.oku(b"jpeg-baytlari", 40.0)
    assert (bir.markdown, bir.okunabilirlik, bir.girdi_token, bir.cikti_token) == (MARKDOWN, "yuksek", 2412, 180)
    assert gonderilen["model"] == "claude-haiku-4-5" and okuyucu.motor == "claude:claude-haiku-4-5"
    gorsel = gonderilen["messages"][0]["content"][0]
    assert gorsel["type"] == "image" and gorsel["source"]["media_type"] == "image/jpeg"
    assert "thinking" not in gonderilen and "temperature" not in gonderilen
    assert gonderilen["max_tokens"] == ocr.CIKTI_SINIRI
    assert alinan == {"timeout": 40.0, "max_retries": 0}
    iki = okuyucu.oku(b"x", 40.0)
    assert iki.kesildi and iki.okunabilirlik == "dusuk" and iki.markdown == "# Yarım"
    assert okuyucu.oku(b"x", 40.0).reddedildi


def test_tesseract_verisinden_satirlar_ve_guven():
    veri = {"text": ["", "Soru", "1", "", "Kesirleri", "topla"],
            "conf": ["-1", "90", "80", "-1", "40", "30"],
            "block_num": [1, 1, 1, 2, 2, 2], "par_num": [1, 1, 1, 1, 1, 1],
            "line_num": [0, 1, 1, 0, 1, 1]}
    metin, guven = tesseract_verisinden(veri)
    assert metin == "Soru 1\n\nKesirleri topla"
    assert guven == pytest.approx(0.6)
