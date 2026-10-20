"""Asistanın MEB senaryo aracı (spec 2026-10-19 §6)."""
from datetime import date, timedelta

from src import sinav_senaryo
from src.assistant_core import AssistantRuntime
from src.assistant_tools import SENARYO_TOOL, build_registry

TABLO = sinav_senaryo.tablo_oku()
BUGUN = date(2026, 10, 19)
_DUYURU = ("22 Ekim Perşembe Günü 1.1 Ara Değerlendirme Sınavınızı gerçekleştireceğiz. Sınavınızın içeriği, "
           "MEB konu soru dağılım tablosu 4. senaryo ağırlıklı olacaktır.")
_KONULAR = ["Metnin yüzey anlamını belirleyebilme",
            "Metinde geçen anlamını bilmediği söz varlığı unsurlarının anlamını tahmin edebilme"]


def _yaklasan_turkce_sinavi(blok=None):
    """/api/exams'in verdiği şekilde yaklaşan bir Türkçe 1. yazılı; `senaryo` bloğu eşleştiriciden."""
    if blok is None:
        kayit = {"id": "x", "ders": "Türkçe", "tur": "ortak_sinav", "baslik": "1.1 Ara Değerlendirme Sınavı",
                 "tarih": "2026-10-22", "hafta": None, "konular": _KONULAR}
        blok = sinav_senaryo.senaryo_blogu(kayit, [(_DUYURU, _DUYURU, True)], TABLO, BUGUN)
        assert blok is not None and blok["durum"] == "dogrulandi" and blok["senaryo"] == 4
    return {"id": "x", "course": "Türkçe", "title": "1.1 Ara Değerlendirme Sınavı",
            "date": (date.today() + timedelta(days=7)).isoformat() + "T08:00:00", "status": "upcoming",
            "senaryo": blok}


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


def test_sayi_metin_olarak_gelirse_yaklasan_sinav_yine_bulunur():
    # Bir JSON araç çağrısı sayıyı "1" diye gönderebilir. Dönüşüm olmazsa `e["senaryo"]["sinav_no"] == "1"`
    # yaklaşan sınavı bulamaz ve Sınav/Durum satırları ile "(duyuruda)" işaretleri kaybolur.
    kayit = _kayit([_yaklasan_turkce_sinavi()])
    sayi = kayit.dispatch(SENARYO_TOOL, {"ders": "Türkçe", "sinav_no": 1})
    metin = kayit.dispatch(SENARYO_TOOL, {"ders": "Türkçe", "sinav_no": "1", "senaryo": "4"})
    assert sayi.ok and metin.ok
    assert "Sınav:" in metin.text and "Durum:" in metin.text and "(duyuruda)" in metin.text
    assert metin.text == sayi.text
    yer = metin.citations[0]["locator"]["args"]
    assert yer["sinav_no"] == 1 and yer["senaryo"] == 4
    assert isinstance(yer["sinav_no"], int) and isinstance(yer["senaryo"], int)


def test_sayi_olmayan_deger_modele_kisa_hata_olarak_doner():
    for args, alan in (({"ders": "Türkçe", "sinav_no": "birinci"}, "sinav_no"),
                       ({"ders": "Türkçe", "sinav_no": 1, "senaryo": "dördüncü"}, "senaryo")):
        sonuc = _kayit().dispatch(SENARYO_TOOL, args)
        assert not sonuc.ok and alan in sonuc.error and "tam sayı" in sonuc.error, sonuc.error


def test_bozuk_senaryo_blogu_dispatchi_patlatmaz():
    # {"durum": "dogrulandi", "sinav_no": 1} `senaryo` anahtarını taşımaz: ozet() KeyError verir.
    # Araç döngüsü dispatch'i sarmaz; istisna cevabın tamamını düşürürdü.
    bozuk = _yaklasan_turkce_sinavi({"durum": "dogrulandi", "sinav_no": 1})
    sonuc = _kayit([bozuk]).dispatch(SENARYO_TOOL, {"ders": "Türkçe", "sinav_no": 1})
    assert not sonuc.ok and "okunamadı" in sonuc.error


def test_istem_ornek_sinav_kurali():
    p = AssistantRuntime.SYSTEM_PROMPT
    assert "## Örnek sınav" in p
    bolum = p.split("## Örnek sınav", 1)[1]
    for parca in ("`sinav_senaryosu`", "cevap anahtarını", "`alistirma_olustur`", "`netlestir`", "MEB senaryosu ayrıca"):
        assert parca in bolum, parca


def test_istem_ulke_geneli_sinavda_konulardan_hazirlar_ve_senaryo_olmadigini_soyler():
    bolum = AssistantRuntime.SYSTEM_PROMPT.split("## Örnek sınav", 1)[1].split("\n## ", 1)[0]
    ulke = next(b for b in bolum.splitlines() if "ülke genelinde" in b)
    assert "duyurudaki konulardan" in ulke and "güncel ünite" in ulke
    assert "MEB senaryosu olmadığını" in ulke
