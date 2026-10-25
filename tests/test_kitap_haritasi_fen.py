"""Fen 7-1 kitap haritasının değişmezleri (spec §2.2, Kanun K1): gerçek dosya, betiğin kendi denetimi ve ölçülmüş
bölümler. Harita yeniden üretilirse bu test neyin değiştiğini söyler."""
import json
import re
from pathlib import Path

from scripts.meb_kitap_haritasi import KITAPLAR, yapi_denetimi
from src.sinav_senaryo import tablo_oku

KOK = Path(__file__).resolve().parents[1]
HARITA = json.loads((KOK / "src" / "kitap_haritalari" / "fen-bilimleri.json").read_text(encoding="utf-8"))
TABLO = tablo_oku()
CIKTILAR = TABLO["dersler"]["Fen Bilimleri"]["ciktilar"]
KITAP = HARITA["kitaplar"][0]


def _konu(ad):
    return next(k for u in KITAP["uniteler"] for c in u["cerceveler"] for k in c["konular"] if k["ad"] == ad)


def test_betigin_kendi_denetimi_gecer_ve_her_cikti_bagli():
    ayar = KITAPLAR["fen-bilimleri"]
    assert yapi_denetimi(HARITA, CIKTILAR, ayar["beklenen_eslesmeyen"], ayar["basliksiz_konular"]) == []
    assert set(HARITA["eslesme"]) == {c["kod"] for c in CIKTILAR}
    assert HARITA["eslesmedi"] == []


def test_olculen_bolumler():
    assert HARITA["eslesme"]["FB.7.2.1"] == [{"kitap": 0, "unite": 2, "cerceve": 1, "konu": "Fiziksel Anlamda İş"}]
    assert {e["konu"] for e in HARITA["eslesme"]["FB.7.1.1"]} == {
        "Uzay Teknolojileri", "Teknoloji ile Uzay Araştırmaları Arasındaki İlişki"}
    assert (_konu("Fiziksel Anlamda İş")["sayfa"], _konu("Fiziksel Anlamda İş")["son_sayfa"]) == (60, 63)
    assert (_konu("Enerji ve Enerji Çeşitleri")["sayfa"], _konu("Enerji ve Enerji Çeşitleri")["son_sayfa"]) == (64, 70)


def test_fiziksel_anlamda_is_basliklari_kitaptaki_gibi():
    b = _konu("Fiziksel Anlamda İş")["basliklar"]
    assert [(x["tur"], x["ad"], x["sayfa"]) for x in b] == [
        ("etkinlik", "Etkinlik Noktası-1", 60), ("etkinlik", "Etkinlik Noktası-2", 60),
        ("baglanti", "Bağlantı Noktası", 62), ("kontrol", "Kontrol Noktası", 63)]
    assert b[0]["amac"] == "Fiziksel anlamda yapılan işin niteliklerini tanımlama"
    assert b[1]["amac"] == "Fiziksel anlamda iş yapma durumuna göre günlük yaşam örneklerini değerlendirme"


def test_tanimlar_var_gurultu_yok():
    enerji = [(x["tur"], x["ad"], x["sayfa"]) for x in _konu("Enerji ve Enerji Çeşitleri")["basliklar"]]
    assert ("tanim", "Potansiyel Enerji", 68) in enerji
    tum = [x["ad"] for u in KITAP["uniteler"] for c in u["cerceveler"]
           for x in c["basliklar"] + [y for k in c["konular"] for y in k["basliklar"]]]
    assert not set(tum) & {"KUZEY", "DOĞU", "GÜNEY", "4,24 ışık yılı", "Bulutsu", "Haber", "Bilgi Bankası"}


def test_iki_satirlik_ad_ve_konu_basligi_yinelenmez():
    """Basılı s. 127: performans görevinin adı kitapta iki satır; s. 123'teki "Solunum Sistemi Sağlığı" konunun kendi
    başlığının sayfadaki yazımıdır, konunun altında ikinci kez görünmez (atla)."""
    b = [(x["tur"], x["ad"], x["sayfa"]) for x in _konu("Solunum Sisteminin Sağlığı")["basliklar"]]
    assert ("etkinlik", "Performans Görevi: Solunum Sisteminin Sağlığı İçin Neler Yapabiliriz?", 127) in b
    assert not {x[1] for x in b} & {"Performans Görevi: Neler Yapabiliriz?", "Solunum Sistemi Sağlığı"}
    assert "Boşaltım Sistemi Sağlığı" not in [x["ad"] for x in _konu("Boşaltım Sisteminin Sağlığı")["basliklar"]]


def test_onay_damgalar_ve_kaynak():
    assert HARITA["denetim"]["kim"] and re.fullmatch(r"\d{4}-\d{2}-\d{2}", HARITA["denetim"]["tarih"])
    assert re.fullmatch(r"[0-9a-f]{64}", KITAP["sha256"])
    assert (KITAP["toplam_sayfa"], KITAP["sayfa_kaymasi"], KITAP["baski"]) == (153, 1, "2026-2027")
    assert KITAP["pdf_url"] == "https://cdn.eba.gov.tr/temel-egitim/yayin/2026-2027/ktp/fenbilimleri7-1_v3.pdf"
    assert HARITA["senaryo_tablosu"]["ders_sha256"] == TABLO["dersler"]["Fen Bilimleri"]["sha256"]
