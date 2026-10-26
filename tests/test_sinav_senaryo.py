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
          konular=(), hafta=None):
    return {"id": "x", "ders": ders, "tur": tur, "baslik": baslik, "tarih": tarih, "hafta": hafta,
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


def test_ulke_geneli_arac_metni_konulardan_hazirlamayi_ve_senaryo_olmadigini_soyletir():
    govde, etiket = ss.arac_metni(TABLO, [], {"ders": "Türkçe", "sinav_no": 2})
    assert "ülke genelinde ortak" in govde and "senaryo vermiyor" in govde
    assert "duyurudaki konulardan" in govde and "MEB senaryosu olmadığını" in govde
    assert "Toplam" not in govde and "Senaryo " not in govde        # dağılım yok, uydurulmaz
    assert etiket == "MEB konu-soru dağılım tablosu · Türkçe 7 · 2. yazılı"


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


# --- Düzeltme turu 1 ---------------------------------------------------------------------------

# Bulgu 1: pencere alıntıdan başlar, alıntıdan sonraki ilk sınır (tarih ya da başka sınav no) ya da
# 400 karakterde biter; başka sınavın senaryosu bu sınava yazılmaz.
@pytest.mark.parametrize("metin,alinti,tek,beklenen", [
    ("12 Kasım'da Matematik 1.1 sınavı 3. senaryodan, 14 Kasım'da Fen 1.1 sınavı 2. senaryodan yapılacaktır.",
     "12 Kasım'da Matematik 1.1 sınavı 3. senaryodan", False, [3]),
    ("Türkçe 1.1 sınavı 22.10'da yapılacak. Matematik 1.1 sınavı 24.10'da yapılacak, 3. senaryo ağırlıklı olacak.",
     "Türkçe 1.1 sınavı 22.10'da yapılacak.", False, []),
    ("Türkçe 1.1 sınavı 22.10'da yapılacak. Matematik 1.1 sınavı 24 Ekimde yapılacak, 3. senaryo ağırlıklı olacak.",
     "Türkçe 1.1 sınavı 22.10'da yapılacak.", False, []),
    ("Perşembe günü Türkçe 1.1 sınavı var. Perşembe günü de Matematik 1.1 sınavı var, 2. senaryo ağırlıklı.",
     "Perşembe günü Türkçe 1.1 sınavı var.", False, []),
    ("Geçen haftaki Fen sınavı 2. senaryodan yapılmıştı. Bu hafta Türkçe 1.1 sınavımız 22 Ekim Perşembe günü.",
     "Bu hafta Türkçe 1.1 sınavımız 22 Ekim Perşembe günü.", True, []),
    # alıntıdan sonraki, tarihe kadarki cümle pencerededir
    ("Türkçe 1.1 sınavı 22 Ekim'de yapılacak. Sınav 4. senaryo ağırlıklı olacak, telafisi 29 Ekim'de.",
     "Türkçe 1.1 sınavı 22 Ekim'de yapılacak.", False, [4]),
])
def test_pencere_baska_sinavin_senaryosunu_almaz(metin, alinti, tek, beklenen):
    sayilar, cumle = ss.senaryo_cumlesi(metin, alinti, tek)
    assert sayilar == beklenen
    assert (cumle is None) == (not beklenen)


def test_pencere_alinti_bulunamazsa():
    metin = "Sınav 3. senaryo ağırlıklı olacak. Başka bir şey."
    # tek bulgu: alıntı metinde yoksa tüm metin; çok bulgu: yalnız alıntının kendisi
    assert ss.senaryo_cumlesi(metin, "Metinde olmayan bir cümle.", True)[0] == [3]
    assert ss.senaryo_cumlesi(metin, "Metinde olmayan bir cümle.", False) == ([], None)
    assert ss.senaryo_cumlesi(metin, "Sınav 3. senaryo olacak.", False)[0] == [3]


def test_pencere_400_karakterde_biter():
    uzun = " ".join(["Bu cümle dolgudur ve hiçbir sınır içermez."] * 12)        # > 400 karakter
    metin = f"Türkçe 1.1 sınavı yapılacak. {uzun} Sınav 3. senaryo olacak."
    assert ss.senaryo_cumlesi(metin, "Türkçe 1.1 sınavı yapılacak.", False) == ([], None)
    kisa = "Türkçe 1.1 sınavı yapılacak. Sınav 3. senaryo olacak."
    assert ss.senaryo_cumlesi(kisa, "Türkçe 1.1 sınavı yapılacak.", False)[0] == [3]


# Bulgu 2: "senaryo"dan önce yalnız noktalı sıra sayısı, sonra yalnız "senaryo N" bitişik biçimi.
@pytest.mark.parametrize("metin,beklenen", [
    ("Sınavınız 4. senaryo ağırlıklı olacaktır. Bu senaryoda 3 açık uçlu soru yer alacak.", [4]),
    ("Sınav, tablodaki senaryolardan 2 tanesinin karışımı olacak.", []),
    ("Sınavınız MEB'in yayımladığı 6 senaryodan birine göre hazırlanacak.", []),
    ("Sınav 3., 4. senaryolardan olacak.", [3, 4]),
    ("Sınav 3. ve 4. senaryolardan olacak.", [3, 4]),
    ("Sınav senaryo 3 ile yapılacak.", [3]),
    ("Sınav senaryoda 3 soru içerecek.", []),
])
def test_senaryo_sayisi_ile_sira_sayisi_karismaz(metin, beklenen):
    assert ss.senaryo_cumlesi(metin, metin, True)[0] == beklenen


# Bulgu 3: birden çok numara anılınca blok ilk geçerliyi kurar ve cümle o numarayı anar; ozet/arac_metni söyler.
IKI_KAYNAK = [("Türkçe 1.1 sınavı 22 Ekim'de. Sınav 4. senaryo ağırlıklı olacak.",
               "Türkçe 1.1 sınavı 22 Ekim'de. Sınav 4. senaryo ağırlıklı olacak.", True),
              ("Veli notu: 2. senaryo da olabilir.", "Veli notu: 2. senaryo da olabilir.", True)]


def test_cok_numara_cumle_secilen_numarayi_anar():
    blok = ss.senaryo_blogu(kayit(), IKI_KAYNAK, TABLO, BUGUN)
    assert blok["anilan"] == [2, 4] and blok["senaryo"] == 2 and blok["durum"] == "dogrulandi"
    assert "2. senaryo" in blok["cumle"] and "4. senaryo" not in blok["cumle"]
    assert blok["toplam"] == 6


def test_cok_numara_ozet_ve_arac_metni():
    blok = ss.senaryo_blogu(kayit(), IKI_KAYNAK, TABLO, BUGUN)
    assert ss.ozet(blok) == "duyuru 2. ve 4. senaryo diyor; 2. senaryo tabloda var · 6 soru"
    assert ss.ozet({**blok, "durum": "kismen"}) == \
        "duyuru 2. ve 4. senaryo diyor; 2. senaryo tabloda var · 6 soru · bazı konular senaryoda yok"
    sinav = {"id": "x", "course": "Türkçe", "title": "1.1 Ara Değerlendirme Sınavı", "date": "2026-10-22",
             "status": "upcoming", "senaryo": blok}
    govde, _ = ss.arac_metni(TABLO, [sinav], {"ders": "Türkçe"})
    satirlar = govde.split("\n")
    i = next(n for n, s in enumerate(satirlar) if s.startswith("Durum:"))
    assert satirlar[i] == "Durum: duyuru 2. ve 4. senaryo diyor; 2. senaryo tabloda var · 6 soru."
    assert satirlar[i + 1] == ("Duyuru birden çok senaryo anıyor (2. ve 4.); örnek sınav yazmadan önce "
                               "hangisiyle hazırlanacağını sor.")
    tek = ss.senaryo_blogu(kayit(konular=TR_KONULAR), [(TR_METIN, TR_ALINTI, True)], TABLO, BUGUN)
    govde, _ = ss.arac_metni(TABLO, [{**sinav, "senaryo": tek}], {"ders": "Türkçe"})
    assert "birden çok senaryo" not in govde


# Bulgu 4: eşit puanlı çıktıların hepsi; konu adı çıktı eşleşmesinden önce gelir (≥ eşik ve ≥ çıktı puanı).
def _konu_kodlari(ders, konu):
    return {c["kod"] for c in TABLO["dersler"][ders]["ciktilar"] if c.get("konu") == konu}


def _kodlar_metinde(ders, parca):
    return {c["kod"] for c in TABLO["dersler"][ders]["ciktilar"] if parca in ss.katla(c["metin"])}


def test_konu_adi_butun_cikti_kodlarini_dondurur():
    fen = _konu_kodlari("Fen Bilimleri", "Dolaşım Sistemi")
    assert fen == {"FB.7.3.3", "FB.7.3.4", "FB.7.3.5"}
    assert set(ss.konu_eslestir("Dolaşım Sistemi", TABLO["dersler"]["Fen Bilimleri"]["ciktilar"])) == fen
    ad = "Dikdörtgenler Prizmasının Hacmi ve Yüzey Alanı"
    mat = _konu_kodlari("Matematik", ad)
    assert {"MAT.7.4.2", "MAT.7.4.3", "MAT.7.4.4", "MAT.7.4.6"} == mat
    assert set(ss.konu_eslestir(ad, TABLO["dersler"]["Matematik"]["ciktilar"])) == mat


def test_esit_puanli_cikti_kodlari_birlikte_gelir():
    tr = TABLO["dersler"]["Türkçe"]["ciktilar"]
    derin = _kodlar_metinde("Türkçe", "metnin derin anlami")
    assert derin == {"T.O.7.7", "T.O.7.8"}
    assert set(ss.konu_eslestir("Metnin derin anlamı", tr)) == derin
    soz = _kodlar_metinde("Türkçe", "soz varligi")
    assert soz == {"T.O.7.4", "T.O.7.21", "T.Y.7.18"}
    assert set(ss.konu_eslestir("Söz varlığı", tr)) == soz


def test_esit_puanli_konu_gruplari_birlikte_gelir():
    # konu iki grup adını da içeriyor (ikisi de 1.0): hangisinin olduğu bilinemez, ikisi de döner
    ciktilar = [{"kod": "A.1", "metin": "Kuvvet ve hareket ilişkisini çözümleyebilme", "konu": "Madde ve Isı"},
                {"kod": "A.2", "metin": "Elektrik devresini tasarlayabilme", "konu": "Madde ve Isı"},
                {"kod": "B.1", "metin": "Gezegenlerin özelliklerini karşılaştırabilme", "konu": "Isı Etkileşimi"}]
    assert set(ss.konu_eslestir("Madde ve Isı Etkileşimi", ciktilar)) == {"A.1", "A.2", "B.1"}


@pytest.mark.parametrize("ders,baslik,sen,konu", [
    ("Fen Bilimleri", "1.2 Ara Değerlendirme", 3, "Dolaşım Sistemi"),
    ("Matematik", "1.2 Ara Değerlendirme", 4, "Dikdörtgenler Prizmasının Hacmi ve Yüzey Alanı"),
    ("Matematik", "1.2 Ara Değerlendirme", 5, "Dikdörtgenler Prizmasının Hacmi ve Yüzey Alanı"),
    ("Türkçe", "1.1 Ara Değerlendirme", 1, "Metnin derin anlamı"),
    ("Türkçe", "1.1 Ara Değerlendirme", 1, "Söz varlığı"),
])
def test_konu_adiyla_duyuru_senaryoda_yok_denmez(ders, baslik, sen, konu):
    metin = f"{baslik} sınavı {sen}. senaryo ağırlıklı olacak."
    k = kayit(ders=ders, baslik=baslik, tarih="2026-12-10" if baslik.startswith("1.2") else "2026-10-22",
              konular=[konu])
    blok = ss.senaryo_blogu(k, [(metin, metin, True)], TABLO, BUGUN)
    assert blok["senaryo"] == sen
    assert blok["durum"] == "dogrulandi" and blok["senaryo_disi_konular"] == []


def test_soz_varligi_senaryo_2_gercekten_yok():
    # T.O.7.4, T.O.7.21 ve T.Y.7.18'in üçü de Senaryo 2'de yok: "kismen" doğru ve kalır.
    metin = "1.1 sınavı 2. senaryo ağırlıklı olacak."
    blok = ss.senaryo_blogu(kayit(konular=["Söz varlığı"]), [(metin, metin, True)], TABLO, BUGUN)
    assert blok["durum"] == "kismen" and blok["senaryo_disi_konular"] == ["Söz varlığı"]


# Bulgu 5: sınav no başlıktan yalnız noktalı "N. yazılı/sınav" biçiminde okunur.
@pytest.mark.parametrize("baslik", ["Tema 1 Sınavı", "Ünite 2 Sınavı", "Bölüm 1 Yazılısı", "Hafta 2 sınav"])
@pytest.mark.parametrize("tur", ["yazili", "diger"])
def test_noktasiz_numara_sinav_no_sayilmaz(baslik, tur):
    assert ss.sutun_coz(kayit(tur=tur, baslik=baslik, tarih="2026-11-03"), TABLO, BUGUN) is None


def test_proje_sinavi_diger_sinav_no_sayilmaz():
    assert ss.sutun_coz(kayit(tur="diger", baslik="Proje 1 sınavı", tarih="2026-11-03"), TABLO, BUGUN) is None


# --- Düzeltme turu 2 ---------------------------------------------------------------------------

# Konu çıktının tam ifadesini içeriyorsa (duyuru çıktıyı birebir anıyor) yalnız o çıktılar döner; konu grubuna
# genişletilmez. Önceki tur kuralı (konu adı / eşit puanlı çıktılar) bunun dışında aynen geçerlidir.
BES_DERS = ("Fen Bilimleri", "Türkçe", "Matematik", "Sosyal Bilgiler", "Din Kültürü")
GENISLEYENLER = [("Fen Bilimleri", "FB.7.3.1"), ("Fen Bilimleri", "FB.7.3.2"), ("Fen Bilimleri", "FB.7.3.3"),
                 ("Fen Bilimleri", "FB.7.3.5"), ("Din Kültürü", "DKAB.7.2.3")]


def test_cikti_ifadesi_konuya_genisletilmez():
    sorunlar = []
    for ders in BES_DERS:
        ciktilar = TABLO["dersler"][ders]["ciktilar"]
        for c in ciktilar:
            beklenen = [o["kod"] for o in ciktilar if ss.katla(o["metin"]) in ss.katla(c["metin"])]
            sonuc = ss.konu_eslestir(c["metin"], ciktilar)
            if c["kod"] not in sonuc or sonuc != beklenen:
                sorunlar.append(f"{ders} {c['kod']}: {sonuc} (beklenen {beklenen})")
    assert not sorunlar, "çıktı ifadesi kendi koduna eşleşmeli:\n" + "\n".join(sorunlar)


@pytest.mark.parametrize("ders,kod", GENISLEYENLER)
def test_cikti_ifadesi_tam_olarak_kendi_kodu(ders, kod):
    ciktilar = TABLO["dersler"][ders]["ciktilar"]
    metin = next(c["metin"] for c in ciktilar if c["kod"] == kod)
    assert ss.konu_eslestir(metin, ciktilar) == [kod]


def test_birden_cok_cikti_ifadesi_hepsi_doner():
    fen = TABLO["dersler"]["Fen Bilimleri"]["ciktilar"]
    metinler = {c["kod"]: c["metin"] for c in fen}
    konu = f"{metinler['FB.7.3.3']} ve {metinler['FB.7.3.5']}"
    assert ss.konu_eslestir(konu, fen) == ["FB.7.3.3", "FB.7.3.5"]


def test_cikti_ifadesi_kural_onceki_tur_kararlarini_bozmaz():
    fen = TABLO["dersler"]["Fen Bilimleri"]["ciktilar"]
    assert set(ss.konu_eslestir("Dolaşım Sistemi", fen)) == _konu_kodlari("Fen Bilimleri", "Dolaşım Sistemi")
    ad = "Dikdörtgenler Prizmasının Hacmi ve Yüzey Alanı"
    assert set(ss.konu_eslestir(ad, TABLO["dersler"]["Matematik"]["ciktilar"])) == _konu_kodlari("Matematik", ad)
    tr = TABLO["dersler"]["Türkçe"]["ciktilar"]
    assert set(ss.konu_eslestir("Metnin derin anlamı", tr)) == {"T.O.7.7", "T.O.7.8"}
    assert set(ss.konu_eslestir("Söz varlığı", tr)) == {"T.O.7.4", "T.O.7.21", "T.Y.7.18"}


# --- Son düzeltme turu -------------------------------------------------------------------------

# C1: bir "senaryo" sözcüğü tek numara taşır. "N. senaryo M soru" ya da "N. Senaryo M. kısım" cümlesinde
# öndeki sıra sayısı numaradır; sondaki sayı soru adedi/kısım numarasıdır, ikinci bir senaryo değildir.
@pytest.mark.parametrize("metin,beklenen", [
    ("Sınav 5. senaryo 3 açık uçlu sorudan oluşacak.", [5]),
    ("Sınavımız 4. senaryo 7 sorudan oluşacaktır.", [4]),
    ("Sınav 3. Senaryo 2. kısım.", [3]),
    ("Sınav dördüncü senaryo 2 soru içerir.", [4]),
    ("Sınav 3., 4. senaryolar 2 kısım.", [3, 4]),
    ("Senaryo 4 ve senaryo 5 olabilir.", [4, 5]),
    ("Sınav senaryo 3 ile 4. senaryo arasında seçilecek.", [3, 4]),
])
def test_senaryo_sozcugu_tek_numara_tasir(metin, beklenen):
    assert ss.senaryo_cumlesi(metin, metin, True)[0] == beklenen


def test_c1_blok_yanlis_senaryoyu_dogrulamaz():
    metin = "1.1 sınavı yapılacak. Sınav 5. senaryo 3 açık uçlu sorudan oluşacak."
    blok = ss.senaryo_blogu(kayit(), [(metin, metin, True)], TABLO, BUGUN)
    assert blok["anilan"] == [5] and blok["senaryo"] == 5


# I1: takvim kaydının temiz başlığı numara taşımıyorsa ham başlık (taban.rawTitle) okunur. Gerçek kayıt
# ef69baff7d96 (canlı output/sinavlar.json, 2026-10-20) bu biçimdedir. Alıntıdan (kaynaklar[].alinti) numara okunmaz.
EF69_HAM = ("7. Sınıf MEB Ülke Geneli Türkçe 1. Dönem 2. Ortak Yazılı Sınavı / "
            "7th Grade MEB Türkiye-wide Turkish 1st Term 2nd Common Written Exam")


def ef69(**degisen):
    k = {"id": "ef69baff7d96", "ders": "Türkçe", "tur": "ortak_sinav", "baslik": "Türkçe · 1. Dönem Yazılı",
         "tarih": "2027-01-05", "saat": "10:30", "hafta": None, "konular": [], "sentetik": False,
         "kaynaklar": [{"tur": "takvim", "konum": {"id": "ef69baff7d96"}, "alinti": EF69_HAM}],
         "taban": {"id": "ef69baff7d96", "course": "Türkçe", "title": "Türkçe · 1. Dönem Yazılı",
                   "rawTitle": EF69_HAM, "examNumber": None, "date": "2027-01-05T10:30:00",
                   "endDate": "2027-01-05T11:10:00", "allDay": False, "status": "upcoming"}}
    k.update(degisen)
    return k


def test_i1_temiz_baslikta_numara_yoksa_ham_baslik_okunur():
    assert ss.sutun_coz(ef69(), TABLO, BUGUN) == ("Türkçe", 2)
    blok = ss.senaryo_blogu(ef69(), [], TABLO, BUGUN)
    assert blok["durum"] == "ulke_geneli" and blok["sinav_no"] == 2


def test_i1_temiz_baslik_cozulurse_o_kazanir():
    k = ef69(baslik="1.1 Ara Değerlendirme Sınavı", tarih="2026-10-22")
    k["taban"]["rawTitle"] = EF69_HAM       # ham başlık 2 diyor ama ilk çözülen temiz başlıktır
    assert ss.sutun_coz(k, TABLO, BUGUN) == ("Türkçe", 1)


def test_i1_alintidan_numara_okunmaz():
    # Birleşen duyurunun "1.1"i kaynaklar[].alinti'de kalır; oradan sütun seçmek C1 sınıfı yanlış eşleşmedir.
    k = ef69()
    k["taban"] = None
    k["kaynaklar"] = [{"tur": "ders_karti", "konum": {}, "alinti": "22 Ekim 1.1 Ara Değerlendirme Sınavı"}]
    assert ss.sutun_coz(k, TABLO, BUGUN) is None
    k = ef69()
    k["taban"] = {"rawTitle": ""}
    assert ss.sutun_coz(k, TABLO, BUGUN) is None


# I4: sınav tarihinin (yoksa haftanın, yoksa bugünün) öğretim yılı tablonunkiyle, dönemi tablonun dönemiyle
# eşleşmeli. Öğretim yılı Eylül'de başlar; Eylül–Ocak 1. dönem, Şubat–Ağustos 2. dönem.
@pytest.mark.parametrize("baslik,tarih,beklenen", [
    ("1.1 Ara Değerlendirme Sınavı", "2027-10-21", None),          # gelecek yılın 1. dönemi
    ("1.1 Ara Değerlendirme Sınavı", "2025-10-21", None),          # geçen yıl
    ("1.1 Ara Değerlendirme Sınavı", "2027-02-15", None),          # başlık 1. dönem ama tarih 2. dönemde
    ("2. Yazılı", "2027-02-15", None),                              # tarihten 2. dönem
    ("1. Yazılı", "2027-07-01", None),                              # Temmuz 2. dönemdir
    ("Türkçe 2. Yazılı", "2027-01-05", ("Türkçe", 2)),              # Ocak 1. dönem, 2026-2027
    ("1.1 Ara Değerlendirme Sınavı", "2026-09-01", ("Türkçe", 1)),  # öğretim yılının ilk günleri
    ("1.1 Ara Değerlendirme Sınavı", "2026-08-31", None),           # önceki öğretim yılı
])
def test_i4_ogretim_yili_ve_donem_tabloyla_eslesmeli(baslik, tarih, beklenen):
    assert ss.sutun_coz(kayit(baslik=baslik, tarih=tarih), TABLO, BUGUN) == beklenen


def test_i4_tarih_yoksa_hafta_sonra_bugun_belirler():
    b = "1.1 Ara Değerlendirme Sınavı"
    assert ss.sutun_coz(kayit(baslik=b, tarih=None, hafta="2027-10-18"), TABLO, BUGUN) is None
    assert ss.sutun_coz(kayit(baslik=b, tarih=None, hafta="2026-10-19"), TABLO, BUGUN) == ("Türkçe", 1)
    assert ss.sutun_coz(kayit(baslik=b, tarih=None), TABLO, date(2027, 10, 19)) is None
    assert ss.sutun_coz(kayit(baslik=b, tarih=None), TABLO, date(2027, 2, 15)) is None
    assert ss.sutun_coz(kayit(baslik=b, tarih=None), TABLO, BUGUN) == ("Türkçe", 1)


def test_i4_blok_gelecek_yilin_sinavina_yazilmaz():
    metin = "1.1 sınavı 4. senaryo ağırlıklı olacak."
    k = kayit(tarih="2027-10-21")
    assert ss.senaryo_blogu(k, [(metin, metin, True)], TABLO, BUGUN) is None


# M1: not tablosundan türeyen (sentetik) kayıt MEB senaryo bloğu almaz.
def test_m1_sentetik_kayit_blok_almaz():
    k = {**kayit(), "sentetik": True}
    metin = "1.1 sınavı 4. senaryo ağırlıklı olacak."
    assert ss.sutun_coz(k, TABLO, BUGUN) is None
    assert ss.senaryo_blogu(k, [(metin, metin, True)], TABLO, BUGUN) is None
    assert ss.senaryo_blogu({**k, "sentetik": False}, [(metin, metin, True)], TABLO, BUGUN) is not None


# I3: konu kapsamı (senaryo dışı kararı ve aday süzgeci) eşiği geçen bütün çıktı ve konu gruplarının
# birleşimiyle verilir; "duyuruda" etiketi en iyi eşleşmede kalır.
DOLASIM_SOLUNUM = "Dolaşım ve solunum sistemi"


def _fen_12(konu, senaryo=None):
    metin = f"1.2 sınavı {senaryo}. senaryo ağırlıklı olacak." if senaryo else "1.2 sınavı yapılacak."
    k = kayit(ders="Fen Bilimleri", baslik="1.2 Ara Değerlendirme", tarih="2026-12-10", konular=[konu])
    return ss.senaryo_blogu(k, [(metin, metin, True)], TABLO, BUGUN)


def test_i3_baglacli_konu_dolasim_senaryo_4te_kismen_degil():
    # FB.7.3.3 (Dolaşım Sistemi) senaryo 4'te var; yalnız en iyi grup (Solunum → FB.7.3.6) bakılınca "kismen" çıkıyordu.
    fen = TABLO["dersler"]["Fen Bilimleri"]
    assert "FB.7.3.3" in fen["sinavlar"]["2"]["senaryolar"]["4"]
    blok = _fen_12(DOLASIM_SOLUNUM, senaryo=4)
    assert blok["senaryo"] == 4
    assert blok["durum"] == "dogrulandi" and blok["senaryo_disi_konular"] == []


def test_i3_duyuruda_etiketi_en_iyi_eslesmede_kalir():
    blok = _fen_12(DOLASIM_SOLUNUM, senaryo=3)
    assert blok["durum"] == "dogrulandi"
    assert {d["kod"] for d in blok["dagilim"] if d["duyuruda"]} == {"FB.7.3.6"}


def test_i3_en_iyi_eslesme_senaryoda_yoksa_etiket_kapsamdaki_satira_gecer():
    # Senaryo 4'te Solunum (FB.7.3.6) yok, Dolaşım (FB.7.3.3) var: konu "senaryoda" sayılıyorsa kart onu taşıyan
    # satırı da "duyuruda" diye göstermeli; yoksa "1 konu bu senaryoda" yazıp hiçbir satırı işaretlemez.
    blok = _fen_12(DOLASIM_SOLUNUM, senaryo=4)
    assert {d["kod"] for d in blok["dagilim"] if d["duyuruda"]} == {"FB.7.3.3"}


def test_i3_gercekten_olmayan_konu_yine_kismen():
    # Sindirim (FB.7.3.1/2) ve Solunum senaryo 4'te: Uzay konusunun hiçbir çıktısı senaryo 4'te yok.
    blok = _fen_12("Uzayda Neler Var?", senaryo=4)
    fen = TABLO["dersler"]["Fen Bilimleri"]["sinavlar"]["2"]["senaryolar"]["4"]
    assert not ({"FB.7.1.4", "FB.7.1.5"} & set(fen))
    assert blok["durum"] == "kismen" and blok["senaryo_disi_konular"] == ["Uzayda Neler Var?"]


def test_i3_adaylar_birlesimle_suzulur():
    blok = _fen_12(DOLASIM_SOLUNUM)
    senaryolar = TABLO["dersler"]["Fen Bilimleri"]["sinavlar"]["2"]["senaryolar"]
    umulan = sorted(int(n) for n, d in senaryolar.items() if set(d) & {"FB.7.3.3", "FB.7.3.4", "FB.7.3.5", "FB.7.3.6"})
    assert blok["durum"] == "belirtilmedi" and blok["adaylar"] == umulan
    assert 4 in blok["adaylar"] and 5 in blok["adaylar"]


def test_i3_konu_kapsami_birlesimdir_en_iyi_kume_degil():
    fen = TABLO["dersler"]["Fen Bilimleri"]["ciktilar"]
    assert ss.konu_eslestir(DOLASIM_SOLUNUM, fen) == ["FB.7.3.6"]                  # en iyi: Solunum (1.0)
    assert set(ss.konu_kapsami(DOLASIM_SOLUNUM, fen)) == {"FB.7.3.3", "FB.7.3.4", "FB.7.3.5", "FB.7.3.6"}
    tr = TABLO["dersler"]["Türkçe"]["ciktilar"]
    assert ss.konu_kapsami("T.O.7.21 söz varlığı", tr) == ["T.O.7.21"]               # kod eşleşmesi daralmaz
    assert ss.konu_kapsami("Osmanlı Devleti'nin kuruluşu", tr) == []


def test_arac_metni_kapsam_kilavuzunun_yerini_soyler():
    """Sınav Hazırlığı girişi (spec 2026-10-25 §3.4, plan Görev 12)."""
    govde, _ = ss.arac_metni(TABLO, [], {"ders": "Fen", "sinav_no": 1}, BUGUN)
    assert "Kapsam kılavuzu panoda: Sınav Hazırlığı › Fen Bilimleri › 1. yazılı (/hazirlik/fen-bilimleri/1)." in govde
    govde, _ = ss.arac_metni(TABLO, [], {"ders": "Türkçe", "sinav_no": 2}, BUGUN)
    assert "(/hazirlik/turkce/2)" in govde
