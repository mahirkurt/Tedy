"""Asistanın MEB senaryo aracı (spec 2026-10-19 §6)."""
import copy
from datetime import date, datetime, timedelta

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


# Araç yalnız tablonun öğretim yılı içinde bildirilir (I4): testler gerçek saate değil, sabit bir güne bağlanır.
SIMDI = datetime(2026, 10, 20, 12, 0)


def _kayit(sinavlar=(), tablo=TABLO, simdi=SIMDI):
    return build_registry(lambda q, k: [], sinav_kaynagi=lambda: list(sinavlar), senaryo_tablosu=lambda: tablo,
                          saat=lambda: simdi)


def _adlar(reg, **kw):
    return {d["name"] for d in reg.declarations(**kw)}


def test_genel_ve_ogretmen_modunda_bildirilir():
    reg = _kayit()
    assert SENARYO_TOOL in _adlar(reg)
    assert SENARYO_TOOL in _adlar(reg, ogretmen="turkce")


def test_tablo_yoksa_arac_bildirilmez():
    assert SENARYO_TOOL not in _adlar(_kayit(tablo=None))
    assert SENARYO_TOOL not in _adlar(build_registry(lambda q, k: [], senaryo_tablosu=lambda: TABLO,
                                                     saat=lambda: SIMDI))  # sinavlar yok


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


# --- Son düzeltme turu ------------------------------------------------------------------------

BEKLENEN_YENIDEN_CAGRI = ("Senaryo seçilince sinav_senaryosu'nu senaryo=N ile yeniden çağır; "
                          "kontrol listesi ve çıktı adları o çağrıda gelir.")


def test_i2_istem_deneme_sinavi_yazili_provasi_der_ve_cok_secmeliyi_disarida_birakir():
    p = AssistantRuntime.SYSTEM_PROMPT
    bolum = p.split("## Örnek sınav", 1)[1].split("\n## ", 1)[0]
    tetik = next(b for b in bolum.splitlines() if "önce `sinav_senaryosu`" in b)
    assert "'deneme sınavı'" in tetik and "'yazılı provası'" in tetik
    assert "'deneme'," not in tetik and "'deneme' " not in tetik        # yalın "deneme" tetikleyici değil
    assert any("LGS" in b and "GİS" in b and "çoktan seçmeli" in b and "kapsam dışı" in b
               for b in bolum.splitlines())
    hangi = p.split("## Hangi araca ne zaman uzanırsın\n", 1)[1].split("## Uydurma yasağı", 1)[0]
    assert "deneme sınavı / yazılı provası" in hangi and "örnek sınav ve deneme →" not in hangi
    assert "LGS/GİS" in hangi and "çoktan seçmeli" in hangi


def test_i2_arac_aciklamasi_deneme_sinavi_der_ve_cok_secmeliyi_disarida_birakir():
    bildirim = next(d for d in _kayit().declarations() if d["name"] == SENARYO_TOOL)
    a = bildirim["description"]
    assert "deneme sınavı" in a and "yazılı provası" in a and "deneme ya da" not in a
    assert "LGS" in a and "GİS" in a and "çoktan seçmeli" in a and "kapsam dışı" in a


def test_i5_senaryo_secilmemisse_yeniden_cagri_satiri_vardir():
    govde, _ = sinav_senaryo.arac_metni(TABLO, [], {"ders": "Fen Bilimleri", "sinav_no": 1})
    assert BEKLENEN_YENIDEN_CAGRI in govde.splitlines()
    assert len(govde) <= 3900
    # aday yolu: duyurudaki konulardan uyumlu senaryolar çıkmış, ama senaryo yine seçilmemiş
    kayit = {"id": "x", "ders": "Türkçe", "tur": "ortak_sinav", "baslik": "1.1 Ara Değerlendirme Sınavı",
             "tarih": "2026-10-22", "hafta": None,
             "konular": ["Metnin derin anlamını belirlemeye yönelik basit çıkarımlar yapabilme"]}
    blok = sinav_senaryo.senaryo_blogu(kayit, [], TABLO, BUGUN)
    assert blok["durum"] == "belirtilmedi" and blok["adaylar"]
    sinav = {"id": "x", "course": "Türkçe", "title": "1.1 Ara Değerlendirme Sınavı", "date": "2026-10-22",
             "status": "upcoming", "senaryo": blok}
    govde, _ = sinav_senaryo.arac_metni(TABLO, [sinav], {"ders": "Türkçe"})
    assert "Duyurudaki konularla uyumlu senaryolar" in govde and BEKLENEN_YENIDEN_CAGRI in govde.splitlines()


def test_i5_senaryo_secilmisse_yeniden_cagri_satiri_yok():
    govde, _ = sinav_senaryo.arac_metni(TABLO, [], {"ders": "Fen Bilimleri", "sinav_no": 1, "senaryo": 2})
    assert BEKLENEN_YENIDEN_CAGRI not in govde


def test_m4_ders_adi_buyuk_kucuk_harf_ve_aksan_duyarsiz():
    for ham, beklenen in (("türkçe", "Türkçe"), ("TÜRKÇE", "Türkçe"), ("fen bilimleri", "Fen Bilimleri"),
                          ("FEN BİLİMLERİ", "Fen Bilimleri"), ("Fen", "Fen Bilimleri"), ("fen", "Fen Bilimleri"),
                          ("sosyal bilgiler", "Sosyal Bilgiler"), ("Sosyal", "Sosyal Bilgiler"),
                          ("din kültürü", "Din Kültürü"), ("matematik", "Matematik"), ("ingilizce", "İngilizce")):
        govde, etiket = sinav_senaryo.arac_metni(TABLO, [], {"ders": ham, "sinav_no": 1, "senaryo": 1})
        assert govde.startswith(beklenen + " · "), (ham, govde[:60])
        assert etiket == f"MEB konu-soru dağılım tablosu · {beklenen} 7 · 1. yazılı"


def test_m4_bilinmeyen_ders_yine_hata_verir():
    import pytest
    with pytest.raises(ValueError, match="tablosunda yok"):
        sinav_senaryo.arac_metni(TABLO, [], {"ders": "Bilişim", "sinav_no": 1})
    with pytest.raises(ValueError, match="tablosunda yok"):
        sinav_senaryo.arac_metni(TABLO, [], {"ders": "", "sinav_no": 1})


def test_m4_yaklasan_sinav_buyuk_kucuk_harfe_bakmadan_bulunur():
    sinav = _yaklasan_turkce_sinavi()
    govde, _ = sinav_senaryo.arac_metni(TABLO, [sinav], {"ders": "türkçe"})
    assert "Durum: 4. senaryo doğrulandı" in govde


# I4: araç yalnız bugün tablonun öğretim yılı içindeyken bildirilir; gövde tablonun hangi yıl/dönem için olduğunu
# söyler, bugün öbür dönemdeyse bunu açıkça belirtir; sınıf tablodan okunur.
def test_i4_arac_ogretim_yili_disinda_bildirilmez():
    for gun, bildirilir in ((datetime(2026, 9, 1, 9, 0), True), (datetime(2027, 8, 31, 23, 0), True),
                            (datetime(2027, 9, 1, 9, 0), False), (datetime(2026, 8, 31, 23, 0), False)):
        assert (SENARYO_TOOL in _adlar(_kayit(simdi=gun))) is bildirilir, gun
    sonuc = _kayit(simdi=datetime(2027, 9, 5, 9, 0)).dispatch(SENARYO_TOOL, {"ders": "Türkçe", "sinav_no": 1})
    assert not sonuc.ok          # bildirilmeyen araç çağrılsa da çalışmaz


def test_i4_govde_tablonun_yil_ve_donemini_soyler():
    sonuc = _kayit().dispatch(SENARYO_TOOL, {"ders": "Türkçe", "sinav_no": 1, "senaryo": 4})
    satirlar = sonuc.text.splitlines()
    assert "Bu tablo 2026-2027 1. dönem ortak yazılıları içindir." in satirlar
    assert not any("kapsamaz" in s for s in satirlar)          # bugün 1. dönemde: öbür dönem uyarısı yok


def test_i4_bugun_ikinci_donemdeyse_govde_bunu_acikca_soyler():
    sonuc = _kayit(simdi=datetime(2027, 2, 15, 9, 0)).dispatch(SENARYO_TOOL, {"ders": "Türkçe", "sinav_no": 1, "senaryo": 4})
    assert sonuc.ok
    satirlar = sonuc.text.splitlines()
    assert "Bu tablo 2026-2027 1. dönem ortak yazılıları içindir." in satirlar
    assert ("Şu an 2. dönemdeyiz; bu tablo yalnız 1. dönem ortak yazılılarını kapsar, "
            "bugünkü dönemin sınavları için dağılım vermez.") in satirlar


def test_i4_sinif_tablodan_okunur():
    tablo = copy.deepcopy(TABLO)
    tablo["kaynak"]["sinif"] = 8
    govde, etiket = sinav_senaryo.arac_metni(tablo, [], {"ders": "Türkçe", "sinav_no": 1, "senaryo": 4})
    assert govde.splitlines()[0].startswith("Türkçe · 8. sınıf · 1. Dönem 1. Ortak Yazılı")
    assert "7. sınıf" not in govde and etiket == "MEB konu-soru dağılım tablosu · Türkçe 8 · 1. yazılı"
    bildirim = next(d for d in _kayit(tablo=tablo).declarations() if d["name"] == SENARYO_TOOL)
    assert "8. sınıf" in bildirim["description"] and "7. sınıf" not in bildirim["description"]
