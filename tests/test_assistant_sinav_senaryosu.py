"""Asistanın MEB senaryo aracı (spec 2026-10-19 §6)."""
from src import sinav_senaryo
from src.assistant_core import AssistantRuntime
from src.assistant_tools import SENARYO_TOOL, build_registry

TABLO = sinav_senaryo.tablo_oku()


def _kayit(sinavlar=(), tablo=TABLO):
    return build_registry(lambda q, k: [], sinav_kaynagi=lambda: list(sinavlar), senaryo_tablosu=lambda: tablo)


def _adlar(reg, **kw):
    return {d["name"] for d in reg.declarations(**kw)}


def test_genel_ve_ogretmen_modunda_bildirilir():
    reg = _kayit()
    assert SENARYO_TOOL in _adlar(reg)
    assert SENARYO_TOOL in _adlar(reg, ogretmen="turkce")


def test_tablo_yoksa_arac_bildirilmez():
    assert SENARYO_TOOL not in _adlar(_kayit(tablo=None))
    assert SENARYO_TOOL not in _adlar(build_registry(lambda q, k: [], senaryo_tablosu=lambda: TABLO))  # sinavlar yok


def test_arac_kontrol_listesi_ve_atif():
    sonuc = _kayit().dispatch(SENARYO_TOOL, {"ders": "Türkçe", "sinav_no": 1, "senaryo": 4})
    assert sonuc.ok
    assert "T.O.7.5 → 2 soru" in sonuc.text and "Toplam 7 soru" in sonuc.text
    assert sonuc.citations[0]["kind"] == "meb-tablo"
    assert sonuc.citations[0]["label"] == "MEB konu-soru dağılım tablosu · Türkçe 7 · 1. yazılı"


def test_gecersiz_girdi_modele_hata_olarak_doner():
    sonuc = _kayit().dispatch(SENARYO_TOOL, {"ders": "Fen Bilimleri"})
    assert not sonuc.ok and "sinav_no" in sonuc.error


def test_sayi_metin_olarak_gelirse_sayiya_cevrilir():
    # Bir JSON araç çağrısı sayıyı "1" diye gönderebilir; "1" ile 1 aynı davranmalı.
    sayi = _kayit().dispatch(SENARYO_TOOL, {"ders": "Türkçe", "sinav_no": 1, "senaryo": 4})
    metin = _kayit().dispatch(SENARYO_TOOL, {"ders": "Türkçe", "sinav_no": "1", "senaryo": "4"})
    assert metin.ok and metin.text == sayi.text
    assert metin.citations[0]["label"] == sayi.citations[0]["label"]


def test_sayi_olmayan_deger_modele_kisa_hata_olarak_doner():
    sonuc = _kayit().dispatch(SENARYO_TOOL, {"ders": "Türkçe", "sinav_no": "birinci"})
    assert not sonuc.ok and "sinav_no" in sonuc.error
    sonuc = _kayit().dispatch(SENARYO_TOOL, {"ders": "Türkçe", "sinav_no": 1, "senaryo": "dördüncü"})
    assert not sonuc.ok and "senaryo" in sonuc.error


def test_istem_ornek_sinav_kurali():
    p = AssistantRuntime.SYSTEM_PROMPT
    assert "## Örnek sınav" in p
    bolum = p.split("## Örnek sınav", 1)[1]
    for parca in ("`sinav_senaryosu`", "cevap anahtarını", "`alistirma_olustur`", "`netlestir`", "MEB senaryosu ayrıca"):
        assert parca in bolum, parca
