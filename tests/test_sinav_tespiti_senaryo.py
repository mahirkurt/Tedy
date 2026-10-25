"""Tespit, sınav kaydına MEB senaryo bloğunu yazar (spec §3.5)."""
from datetime import date, datetime

from src import sinav_senaryo
from src.sinav_cikarimi import Bulgu
from src.sinav_kaynaklari import Aday
from src.sinav_tespiti import birlestir, kuru_rapor
# Taken at collection, before conftest's autouse fixture replaces sinav_tespiti.tespit_et with a refusal.
from src.sinav_tespiti import tespit_et as GERCEK_TESPIT

SIMDI = datetime(2026, 10, 19, 10, 0)
TABLO = sinav_senaryo.tablo_oku()
METIN = ("22 Ekim Perşembe Günü 1.1 Ara Değerlendirme Sınavınızı gerçekleştireceğiz. Sınavınızın içeriği, "
         "MEB konu soru dağılım tablosu 4. senaryo ağırlıklı olacaktır. Konu başlıklarınız:\n"
         "Metnin yüzey anlamını belirleyebilme")
ALINTI = "22 Ekim Perşembe Günü 1.1 Ara Değerlendirme Sınavınızı gerçekleştireceğiz."


def _bulgu():
    aday = Aday(METIN, "Türkçe", date(2026, 10, 19), "ders_karti",
                [{"bolum": "ders_icerikleri_haftalar", "hafta": "6. Hafta", "ders": "Türkçe", "sira": 1}])
    return Bulgu("Türkçe", "ortak_sinav", "1.1 Ara Değerlendirme Sınavı", date(2026, 10, 22), None, None,
                 ["Metnin yüzey anlamını belirleyebilme"], ALINTI, aday)


def test_blok_yazilir_ve_icerik_surumu_degismez():
    duz = birlestir([], [_bulgu()], None, SIMDI)
    ile = birlestir([], [_bulgu()], None, SIMDI, senaryolar=TABLO)
    assert "senaryo" not in duz[0]
    assert ile[0]["senaryo"]["durum"] == "dogrulandi" and ile[0]["senaryo"]["senaryo"] == 4
    assert ile[0]["icerik_surumu"] == duz[0]["icerik_surumu"]


def test_sutun_cozulmezse_anahtar_yazilmaz():
    b = _bulgu()
    b = Bulgu(b.ders, "kisa_sinav", "Büyük Quiz", b.tarih, None, None, [], b.alinti, b.aday)
    assert "senaryo" not in birlestir([], [b], None, SIMDI, senaryolar=TABLO)[0]


def test_tablo_yoksa_not_duser(tmp_path, monkeypatch):
    class Okuyucu:
        def oku(self, *a, **k):
            raise AssertionError("model çağrılmamalı")
    monkeypatch.setattr(sinav_senaryo, "tablo_oku", lambda yol=None: None)
    belge = GERCEK_TESPIT(tmp_path, {}, [], SIMDI, bitis=0.0, okuyucu=Okuyucu())
    assert belge["ozet"]["hatalar"][0] == "senaryo tablosu okunamadı"


def test_kuru_rapor_senaryo_satiri():
    belge = {"sinavlar": birlestir([], [_bulgu()], None, SIMDI, senaryolar=TABLO), "ozet": {}}
    assert "  Senaryo: dogrulandi · Türkçe 1. yazılı · 4. senaryo · 7 soru" in kuru_rapor(belge).splitlines()


# --- Son düzeltme turu -------------------------------------------------------------------------

def _fen_bulgusu():
    metin = "23 Ekim Cuma günü Fen 1.1 Ara Değerlendirme Sınavı olacak. Sınav 2. senaryo ağırlıklı."
    aday = Aday(metin, "Fen Bilimleri", date(2026, 10, 19), "ders_karti",
                [{"bolum": "ders_icerikleri_haftalar", "hafta": "6. Hafta", "ders": "Fen Bilimleri", "sira": 2}])
    return Bulgu("Fen Bilimleri", "yazili", "1.1 Ara Değerlendirme Sınavı", date(2026, 10, 23), None, None, [],
                 "23 Ekim Cuma günü Fen 1.1 Ara Değerlendirme Sınavı olacak.", aday)


def test_i7_bir_kaydin_eslestirmesi_patlarsa_digerleri_blok_alir(monkeypatch):
    gercek = sinav_senaryo.senaryo_blogu

    def sahte(kayit, *a, **k):
        if kayit["ders"] == "Fen Bilimleri":
            raise RuntimeError("beklenmeyen tablo yapısı")
        return gercek(kayit, *a, **k)

    monkeypatch.setattr(sinav_senaryo, "senaryo_blogu", sahte)
    hatalar = []
    kayitlar = birlestir([], [_bulgu(), _fen_bulgusu()], None, SIMDI, senaryolar=TABLO, senaryo_hatalari=hatalar)
    by = {k["ders"]: k for k in kayitlar}
    assert set(by) == {"Türkçe", "Fen Bilimleri"}                   # belge yine üretilir, kayıt düşmez
    assert by["Türkçe"]["senaryo"]["durum"] == "dogrulandi"
    assert "senaryo" not in by["Fen Bilimleri"]
    assert hatalar == ["senaryo eşleştirilemedi: Fen Bilimleri 1.1 Ara Değerlendirme Sınavı"]
    # hata listesi verilmese de patlamaz
    kayitlar = birlestir([], [_bulgu(), _fen_bulgusu()], None, SIMDI, senaryolar=TABLO)
    assert len(kayitlar) == 2


def test_i7_tespit_ozeti_hataya_senaryo_notunu_yazar(tmp_path, monkeypatch):
    class Okuyucu:
        def oku(self, *a, **k):
            raise AssertionError("model çağrılmamalı")

    def patlar(*a, **k):
        raise RuntimeError("beklenmeyen tablo yapısı")

    monkeypatch.setattr(sinav_senaryo, "senaryo_blogu", patlar)
    taban = [{"id": "t1", "course": "Türkçe", "title": "1.1 Ara Değerlendirme Sınavı",
              "rawTitle": "1.1 Ara Değerlendirme Sınavı", "date": "2026-10-22T08:00:00", "allDay": False}]
    belge = GERCEK_TESPIT(tmp_path, {}, taban, SIMDI, bitis=0.0, okuyucu=Okuyucu())
    assert "senaryo eşleştirilemedi: Türkçe 1.1 Ara Değerlendirme Sınavı" in belge["ozet"]["hatalar"]
    assert [k["ders"] for k in belge["sinavlar"]] == ["Türkçe"] and "senaryo" not in belge["sinavlar"][0]


def test_m1_not_tablosundan_turetilen_kayit_blok_almaz():
    # Notlandırılmış geçmiş "1. Yazılı" kartında "Duyuruda senaryo belirtilmedi" yazmasın.
    taban = [{"id": "n1", "course": "Türkçe", "title": "1. Yazılı", "rawTitle": "1. Yazılı", "date": None,
              "grade": 90}]
    kayit = birlestir(taban, [], None, SIMDI, senaryolar=TABLO)[0]
    assert kayit["sentetik"] is True and "senaryo" not in kayit


def test_ozet_hatalari_cikarim_hatasini_senaryo_notlarina_gommez():
    # Tablo yapısı surum artmadan değişirse her kayıt patlar; özet (5 satır) çıkarım ve bütçe hatalarını yine taşımalı.
    from src.sinav_tespiti import ozet_hatalari

    senaryo = [f"senaryo eşleştirilemedi: Türkçe {n}. Yazılı" for n in range(1, 7)]
    hatalar = ozet_hatalari(tablo_okundu=True, senaryo_hatalari=senaryo, cikarim_hatalari=["aylık bütçe doldu"])
    assert "aylık bütçe doldu" in hatalar and len(hatalar) <= 5
    assert sum(h.startswith("senaryo eşleştirilemedi") for h in hatalar) == 1
    assert hatalar[-1] == "senaryo eşleştirilemedi: Türkçe 1. Yazılı (+5 kayıt daha)"
    assert ozet_hatalari(tablo_okundu=False, senaryo_hatalari=[], cikarim_hatalari=["x"]) == [
        "senaryo tablosu okunamadı", "x"]
    assert ozet_hatalari(tablo_okundu=True, senaryo_hatalari=senaryo[:1], cikarim_hatalari=[]) == senaryo[:1]


def test_alintidan_sinav_no_tespitte_blok_yazar():
    # Canlı 0e885076d71c: başlık "Fen Bilimleri Yazılı" (numarasız), takvim tabanı yok; "1.Dönem 1. Fen yazılınız"
    # yalnız ders kartı alıntısında. Uygulama kararı 2026-10-25: numara alıntıdan okunur.
    alinti = ("1.Dönem 1. Fen yazılınız 3 Kasım 2026 tarihinde İstanbul İl MEB tarafından belirlenen "
              "2. senaryoya göre uygulanacaktır.")
    aday = Aday("Sevgili öğrenciler,\n" + alinti + "\nKonular: uzay araştırmaları.", "Fen Bilimleri",
                date(2026, 10, 19), "ders_karti",
                [{"bolum": "ders_icerikleri_haftalar", "hafta": "6. Hafta", "ders": "Fen Bilimleri", "sira": 0}])
    b = Bulgu("Fen Bilimleri", "yazili", "Fen Bilimleri Yazılı", date(2026, 11, 3), None, None,
              ["Uzay araştırmaları için geliştirilen teknolojiler",
               "Uzay araştırmalarının yol açabileceği problemler",
               "Yıldız, galaksi ve evren kavramları"], alinti, aday)
    kayit = birlestir([], [b], None, SIMDI, senaryolar=TABLO)[0]
    assert kayit["baslik"] == "Fen Bilimleri Yazılı" and kayit["taban"] is None
    s = kayit["senaryo"]
    assert (s["durum"], s["sinav_no"], s["senaryo"], s["toplam"]) == ("dogrulandi", 1, 2, 7)
