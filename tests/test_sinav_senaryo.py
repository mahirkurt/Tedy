"""Sınav ↔ MEB senaryosu eşleştirici (spec 2026-10-19 §3, §6.1). Gerçek tablo dosyasıyla."""
from datetime import date

import pytest

from src import sinav_senaryo as ss

TABLO = ss.tablo_oku()
BUGUN = date(2026, 10, 19)
TR_METIN = (
    "6. Hafta Planımız\nEda Şen | 19.10.2026\nSevgili Öğrencilerimiz,\n\nDerslerimize, geçtiğimiz hafta "
    "kontrol edemediğimiz ödevlerinizin kontrolü ile başlıyoruz. Ardından MEB kitabımızda yer alan "
    "\"Gençliğin Kıymeti\" metni üzerinden söz varlığı ve düşünceyi geliştirme yolları çalışmalarımızı "
    "tamamlayacağız. 22 Ekim Perşembe Günü 1.1 Ara Değerlendirme Sınavınızı gerçekleştireceğiz. "
    "Sınavınızın içeriği, MEB konu soru dağılım tablosu 4. senaryo ağırlıklı olacaktır. Konu "
    "başlıklarınız aşağıdaki gibidir:\n\nMetnin yüzey anlamını belirleyebilme\nMetinde geçen anlamını "
    "bilmediği söz varlığı unsurlarının anlamını tahmin edebilme")
TR_ALINTI = ("22 Ekim Perşembe Günü 1.1 Ara Değerlendirme Sınavınızı gerçekleştireceğiz. Sınavınızın "
             "içeriği, MEB konu soru dağılım tablosu 4. senaryo ağırlıklı olacaktır.")
TR_KONULAR = ["Metnin yüzey anlamını belirleyebilme",
              "Metinde geçen anlamını bilmediği söz varlığı unsurlarının anlamını tahmin edebilme"]


def kayit(ders="Türkçe", tur="ortak_sinav", baslik="1.1 Ara Değerlendirme Sınavı", tarih="2026-10-22",
          konular=()):
    return {"id": "x", "ders": ders, "tur": tur, "baslik": baslik, "tarih": tarih, "hafta": None,
            "konular": list(konular)}


def test_tablo_okunur_ve_bozuk_dosya_none(tmp_path):
    assert TABLO is not None and "Türkçe" in TABLO["dersler"]
    bozuk = tmp_path / "t.json"
    bozuk.write_text("{", encoding="utf-8")
    assert ss.tablo_oku(bozuk) is None
    bozuk.write_text('{"surum": 2, "dersler": {}}', encoding="utf-8")
    assert ss.tablo_oku(bozuk) is None


@pytest.mark.parametrize("baslik,tarih,beklenen", [
    ("1.1 Ara Değerlendirme Sınavı", "2026-10-22", ("Türkçe", 1)),
    ("1.2 Ara Değerlendirme Sınavı", "2026-12-10", ("Türkçe", 2)),
    ("Türkçe 2. Yazılı", "2026-12-10", ("Türkçe", 2)),
    ("Birinci ortak sınav", "2026-11-03", ("Türkçe", 1)),
    ("1. Dönem 1. Yazılı", "2026-11-03", ("Türkçe", 1)),
    ("2.1 Ara Değerlendirme Sınavı", "2027-03-10", None),     # 2. dönem: tablo 1. dönem
    ("1. Yazılı", "2027-03-10", None),                         # tarihten 2. dönem
])
def test_sutun_cozumu(baslik, tarih, beklenen):
    assert ss.sutun_coz(kayit(baslik=baslik, tarih=tarih), TABLO, BUGUN) == beklenen


def test_sinav_no_cozulmezse_blok_yok():
    k = kayit(baslik="Türkçe · 1. Dönem Yazılı", tarih="2027-01-05")
    assert ss.sutun_coz(k, TABLO, BUGUN) is None
    assert ss.senaryo_blogu(k, [], TABLO, BUGUN) is None


def test_kisa_sinav_ve_konu_tarama_eslesmez():
    assert ss.sutun_coz(kayit(tur="kisa_sinav"), TABLO, BUGUN) is None
    assert ss.sutun_coz(kayit(tur="konu_tarama"), TABLO, BUGUN) is None
    assert ss.sutun_coz(kayit(ders="Bilişim"), TABLO, BUGUN) is None


@pytest.mark.parametrize("metin,beklenen", [
    ("Sınavınız MEB tablosu 4. senaryo ağırlıklı olacaktır.", [4]),
    ("Sınav senaryo 3 üzerinden yapılacak.", [3]),
    ("Sınav dördüncü senaryoya göre hazırlanacak.", [4]),
    ("3. ve 4. senaryolardan sorular gelecek.", [3, 4]),
    ("Sınav 4.senaryo ile yapılacak.", [4]),
    ("Sınavda 22 soru olacak, senaryo yok.", []),
])
def test_senaryo_kaliplari(metin, beklenen):
    assert ss.senaryo_cumlesi(metin, metin, True)[0] == beklenen


def test_buyuk_harfli_senaryo_bolunmez():
    metin = "Yarın sınav var. Sınavın içeriği MEB tablosu 4. Senaryo ağırlıklı olacaktır."
    sayilar, cumle = ss.senaryo_cumlesi(metin, "Yarın sınav var.", False)
    assert sayilar == [4]
    assert cumle == "Sınavın içeriği MEB tablosu 4. Senaryo ağırlıklı olacaktır."


def test_baska_sinavin_senaryosu_alinmaz():
    metin = ("12 Kasım'da Fen kısa sınavı var. 22 Ekim Perşembe günü 1.1 Ara Değerlendirme Sınavınızı "
             "yapacağız. Sınav 3. senaryo ağırlıklı olacaktır.")
    assert ss.senaryo_cumlesi(metin, "12 Kasım'da Fen kısa sınavı var.", False) == ([], None)
    sayilar, cumle = ss.senaryo_cumlesi(metin, "22 Ekim Perşembe günü 1.1 Ara Değerlendirme", False)
    assert sayilar == [3] and cumle == "Sınav 3. senaryo ağırlıklı olacaktır."


def test_konu_eslestirme():
    tr = TABLO["dersler"]["Türkçe"]["ciktilar"]
    assert ss.konu_eslestir("Metnin yüzey anlamını belirleyebilme", tr) == ["T.O.7.5"]
    assert ss.konu_eslestir("T.O.7.21 söz varlığı", tr) == ["T.O.7.21"]
    assert ss.konu_eslestir("Osmanlı Devleti'nin kuruluşu", tr) == []
    fen = TABLO["dersler"]["Fen Bilimleri"]["ciktilar"]
    # çıktı metni değil konu adı: o konunun bütün çıktıları
    assert set(ss.konu_eslestir("Uzayda Neler Var?", fen)) == {"FB.7.1.4", "FB.7.1.5"}


def test_gercek_turkce_vakasi_dogrulandi():
    blok = ss.senaryo_blogu(kayit(konular=TR_KONULAR), [(TR_METIN, TR_ALINTI, True)], TABLO, BUGUN)
    assert blok["durum"] == "dogrulandi"
    assert (blok["senaryo"], blok["toplam"], blok["anilan"]) == (4, 7, [4])
    assert blok["cumle"] == "Sınavınızın içeriği, MEB konu soru dağılım tablosu 4. senaryo ağırlıklı olacaktır."
    assert blok["eslesen_konu_sayisi"] == 2 and blok["eslesmeyen_konular"] == []
    duyuruda = {d["kod"] for d in blok["dagilim"] if d["duyuruda"]}
    assert duyuruda == {"T.O.7.4", "T.O.7.5"}
    assert {d["kod"] for d in blok["dagilim"]} == {"T.O.7.4", "T.O.7.5", "T.O.7.7", "T.O.7.21", "T.Y.7.18", "T.Y.7.21"}
    assert blok["kaynak"].startswith("https://odsgm.meb.gov.tr/") and blok["meb_guncelleme"]


def test_kismen():
    blok = ss.senaryo_blogu(kayit(konular=TR_KONULAR + ["Metnin derin anlamını belirlemeye yönelik üst düzey çıkarımlar yapabilme"]),
                            [(TR_METIN, TR_ALINTI, True)], TABLO, BUGUN)
    assert blok["durum"] == "kismen"
    assert blok["senaryo_disi_konular"] == ["Metnin derin anlamını belirlemeye yönelik üst düzey çıkarımlar yapabilme"]


def test_senaryo_yok():
    metin = "1.1 sınavı 9. senaryo ağırlıklı olacaktır."
    blok = ss.senaryo_blogu(kayit(), [(metin, metin, True)], TABLO, BUGUN)
    assert blok["durum"] == "senaryo_yok" and blok["anilan"] == [9] and blok["senaryo_sayisi"] == 6
    assert blok["senaryo"] is None and blok["dagilim"] == []


def test_ulke_geneli():
    blok = ss.senaryo_blogu(kayit(baslik="1.2 Ara Değerlendirme", tarih="2026-12-10"), [], TABLO, BUGUN)
    assert blok["durum"] == "ulke_geneli" and "Ülke Geneli" in blok["not"]


def test_belirtilmedi_adaylarla_ve_adaysiz():
    blok = ss.senaryo_blogu(kayit(konular=["Metnin derin anlamını belirlemeye yönelik basit çıkarımlar yapabilme"]),
                            [], TABLO, BUGUN)
    assert blok["durum"] == "belirtilmedi" and blok["senaryo_sayisi"] == 6
    s = TABLO["dersler"]["Türkçe"]["sinavlar"]["1"]["senaryolar"]
    assert blok["adaylar"] == sorted(int(n) for n, d in s.items() if "T.O.7.7" in d)
    blok = ss.senaryo_blogu(kayit(konular=["Osmanlı'nın kuruluşu"]), [], TABLO, BUGUN)
    assert blok["adaylar"] == [] and blok["eslesmeyen_konular"] == ["Osmanlı'nın kuruluşu"]


def test_ozet_ve_arac_metni():
    blok = ss.senaryo_blogu(kayit(konular=TR_KONULAR), [(TR_METIN, TR_ALINTI, True)], TABLO, BUGUN)
    assert ss.ozet(blok) == "4. senaryo doğrulandı · 7 soru"
    sinav = {"id": "x", "course": "Türkçe", "title": "1.1 Ara Değerlendirme Sınavı", "date": "2026-10-22",
             "status": "upcoming", "senaryo": blok}
    govde, etiket = ss.arac_metni(TABLO, [sinav], {"ders": "Türkçe"})
    assert "T.O.7.5 → 2 soru" in govde and "Toplam 7 soru" in govde and "(duyuruda)" in govde
    assert etiket == "MEB konu-soru dağılım tablosu · Türkçe 7 · 1. yazılı"
    govde, _ = ss.arac_metni(TABLO, [], {"ders": "Fen", "sinav_no": 1, "senaryo": 2})
    assert "Senaryo 2" in govde and "Toplam" in govde
    govde, _ = ss.arac_metni(TABLO, [], {"ders": "Fen Bilimleri", "sinav_no": 1})
    assert govde.count("Senaryo ") >= 5
    assert len(govde) <= 3900
    with pytest.raises(ValueError, match="sinav_no"):
        ss.arac_metni(TABLO, [], {"ders": "Fen Bilimleri"})
    with pytest.raises(ValueError, match="tablosunda yok"):
        ss.arac_metni(TABLO, [], {"ders": "Bilişim", "sinav_no": 1})
