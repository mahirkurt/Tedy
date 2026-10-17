"""src/sinav_tespiti: merging takvim + grade-table exams with text findings into
output/sinavlar.json — ids, content versions, first-seen and retention."""
import hashlib
import json
from datetime import date, datetime

import pytest

from src.sinav_cikarimi import Bulgu
from src.sinav_kaynaklari import Aday
from src.sinav_tespiti import SURUM, birlestir, gecerli_belge, oku, takvim_turu, yaz

SIMDI = datetime(2026, 10, 16, 10, 0)


def taban(id_, course, title, date_, all_day=False):
    return {"id": id_, "course": course, "title": title, "rawTitle": title, "courseColor": "#000",
            "courseFamily": "blue", "examNumber": None, "date": date_, "endDate": None, "allDay": all_day,
            "status": "upcoming", "grade": None, "relatedHomework": [], "relatedContent": []}


def bulgu(ders="Matematik", tur="konu_tarama", tarih=None, hafta=None, konular=(), baslik=None,
          yayin=date(2026, 10, 5), konum=None, metin="metin", aday_tur="ders_karti"):
    aday = Aday(metin, ders, yayin, aday_tur, [konum or {"bolum": "ders_icerikleri_haftalar", "hafta": "4. Hafta",
                                                         "ders": ders, "sira": 1}])
    return Bulgu(ders, tur, baslik or f"{ders} KTT", tarih, hafta, None, list(konular), "alıntı", aday)


GIS = taban("gis1", "Özdebir GİS", "Özdebir GİS · İzleme Sınavı", "2026-10-23T09:00:00")
TR = taban("tr1", "Türkçe", "Türkçe · Ortak Yazılı", "2027-01-05T10:30:00")
NOTLU = dict(taban("not1", "Matematik", "Matematik · 1. Sınav", None), status="past", grade="85")


@pytest.mark.parametrize("baslik,tur", [
    ("Özdebir GİS · İzleme Sınavı", "deneme"), ("Türkçe · Ortak Yazılı", "ortak_sinav"),
    ("Matematik KTT", "konu_tarama"), ("Fen · Yazılı", "yazili"), ("Irregular Verbs Quiz", "kisa_sinav"),
    ("Sebit Vcloud Kazanım Değerlendirme Uygulaması-1_TM", "deneme"), ("Okul gezisi", "diger"),
    ("Bilgisayar Yazılı", "yazili"), ("GİS-1", "deneme"), ("Özdebir GİS-2 Sınavı", "deneme"),
    ("Deneme Sınavı", "deneme"), ("Bilişim KTT-2", "konu_tarama"),
])
def test_takvim_turu(baslik, tur):
    assert takvim_turu(baslik) == tur


def test_takvim_kaydi_kimligini_ve_tabanini_korur():
    [k] = birlestir([GIS], [], None, SIMDI)
    assert (k["id"], k["ders"], k["tur"], k["tarih"], k["saat"], k["sentetik"]) == \
        ("gis1", "Özdebir GİS", "deneme", "2026-10-23", "09:00", False)
    assert k["kaynaklar"] == [{"tur": "takvim", "konum": {"id": "gis1"}, "alinti": GIS["rawTitle"]}]
    assert k["taban"] == GIS and k["ilk_tespit"] is None and k["degisti"] is None


def test_notlu_sentetik_kayit():
    [k] = birlestir([NOTLU], [], None, SIMDI)
    assert (k["sentetik"], k["tarih"], k["kaynaklar"][0]["tur"]) == (True, None, "not_tablosu")


def test_bulgu_ayni_ders_ayni_gun_takvime_baglanir():
    tr_bulgu = bulgu("Türkçe", "ortak_sinav", tarih=date(2027, 1, 5), konular=["Fiilimsiler"])
    [k, _] = sorted(birlestir([TR, GIS], [tr_bulgu], None, SIMDI), key=lambda k: k["id"] != "tr1")
    assert k["id"] == "tr1" and k["konular"] == ["Fiilimsiler"]
    assert [x["tur"] for x in k["kaynaklar"]] == ["takvim", "ders_karti"]


def test_genel_bulgu_ayni_gundeki_takvime_baglanir():
    kayitlar = birlestir([GIS], [bulgu("Genel", "deneme", tarih=date(2026, 10, 23), konular=["Tüm konular"])],
                         None, SIMDI)
    assert len(kayitlar) == 1 and kayitlar[0]["konular"] == ["Tüm konular"]


def test_ayni_ders_ayni_gun_iki_bulgu_tek_kayit():
    b1 = bulgu(tarih=date(2026, 10, 15), konular=["Mutlak değer"])
    b2 = bulgu(tarih=date(2026, 10, 15), konular=["Mutlak değer", "Tam sayılar"],
               konum={"bolum": "odev", "baslik": "KTT", "teslim": None}, aday_tur="odev")
    [k] = birlestir([], [b1, b2], None, SIMDI)
    assert k["id"] == hashlib.md5("Matematik|2026-10-15".encode()).hexdigest()[:12]
    assert k["konular"] == ["Mutlak değer", "Tam sayılar"]
    assert [x["tur"] for x in k["kaynaklar"]] == ["ders_karti", "odev"]
    assert (k["tarih"], k["saat"], k["baslik"]) == ("2026-10-15", None, "Matematik KTT")


def test_hafta_yalniz_bulgu_haftadaki_tek_sinava_baglanir():
    fen = taban("fen1", "Fen Bilimleri", "Fen · Yazılı", "2026-10-21T09:00:00")
    [k] = birlestir([fen], [bulgu("Fen Bilimleri", "kisa_sinav", hafta=date(2026, 10, 19), konular=["Uzay"])],
                    None, SIMDI)
    assert k["id"] == "fen1" and k["konular"] == ["Uzay"]


def test_hafta_yalniz_bulgu_eslesme_yoksa_ayri_kayit():
    [k] = birlestir([], [bulgu("İngilizce", "kisa_sinav", hafta=date(2026, 10, 19))], None, SIMDI)
    assert (k["tarih"], k["hafta"]) == (None, "2026-10-19")
    assert k["id"] == hashlib.md5("İngilizce|hafta:2026-10-19".encode()).hexdigest()[:12]


def test_tarihsiz_bulgu_konu_ortusmesiyle_baglanir():
    tarihli = bulgu(tarih=date(2026, 10, 20), konular=["Mutlak değer"])
    tarihsiz = bulgu(konular=["mutlak değer", "Oran"], yayin=date(2026, 10, 12), metin="başka")
    [k] = birlestir([], [tarihli, tarihsiz], None, SIMDI)
    assert k["konular"] == ["Mutlak değer", "Oran"]


def test_tarihsiz_bulgu_ortusme_yoksa_tarih_belirsiz_kayit():
    kayitlar = birlestir([], [bulgu(tarih=date(2026, 10, 20), konular=["Mutlak değer"]),
                              bulgu(konular=["Oran"], yayin=date(2026, 10, 12), metin="başka")], None, SIMDI)
    assert [k["tarih"] for k in kayitlar] == ["2026-10-20", None]


def test_icerik_surumu_degisince_degisti_ilk_tespit_korunur():
    onceki = {"surum": SURUM, "sinavlar": birlestir([], [bulgu(tarih=date(2026, 10, 20), konular=["A"])],
                                                    {"surum": SURUM, "sinavlar": []}, datetime(2026, 10, 10, 9))}
    assert onceki["sinavlar"][0]["ilk_tespit"] == "2026-10-10T09:00:00"
    ayni = birlestir([], [bulgu(tarih=date(2026, 10, 20), konular=["A"])], onceki, SIMDI)[0]
    assert (ayni["ilk_tespit"], ayni["degisti"]) == ("2026-10-10T09:00:00", None)
    yeni = birlestir([], [bulgu(tarih=date(2026, 10, 20), konular=["A", "B"])], onceki, SIMDI)[0]
    assert (yeni["ilk_tespit"], yeni["degisti"]) == ("2026-10-10T09:00:00", "2026-10-16T10:00:00")
    assert yeni["icerik_surumu"] != ayni["icerik_surumu"] and len(yeni["icerik_surumu"]) == 12


def test_ilk_kurulumda_ilk_tespit_bos_sonra_simdi():
    assert birlestir([GIS], [], None, SIMDI)[0]["ilk_tespit"] is None
    assert birlestir([GIS], [], {"surum": SURUM, "sinavlar": []}, SIMDI)[0]["ilk_tespit"] == "2026-10-16T10:00:00"


def test_saklama_suresi():
    eski = taban("eski", "Fen", "Fen · Yazılı", "2026-09-15T09:00:00")
    yakin = taban("yakin", "Fen", "Fen · Yazılı", "2026-09-17T09:00:00")
    tarihsiz_eski = bulgu("Fen", "diger", konular=["X"], yayin=date(2026, 9, 24), metin="eski")
    tarihsiz_taze = bulgu("Fen", "diger", konular=["Y"], yayin=date(2026, 9, 26), metin="taze")
    idler = [k["id"] for k in birlestir([eski, yakin, NOTLU], [tarihsiz_eski, tarihsiz_taze], None, SIMDI)]
    assert "eski" not in idler and "yakin" in idler and "not1" in idler
    assert len(idler) == 3   # yakin, taze, not1 — eski takvim (31 gün) ve eski tarihsiz (22 gün) düştü


def test_siralama_tarihli_tarihsiz_sentetik():
    kayitlar = birlestir([NOTLU, TR, GIS], [bulgu("Fen", "diger", konular=["Y"])], None, SIMDI)
    assert [k["id"] for k in kayitlar][:2] == ["gis1", "tr1"]
    assert kayitlar[2]["tarih"] is None and not kayitlar[2]["sentetik"]
    assert kayitlar[3]["id"] == "not1"


def test_yaz_oku_ve_gecersiz_belge(tmp_path):
    belge = {"uretildi": "2026-10-16T10:00:00", "surum": SURUM, "sinavlar": [], "ozet": {}}
    yaz(tmp_path, belge)
    assert oku(tmp_path) == belge
    assert gecerli_belge({"surum": SURUM + 1, "sinavlar": []}) is None
    assert gecerli_belge({"surum": SURUM, "sinavlar": "x"}) is None
    (tmp_path / "output/sinavlar.json").write_text("{bozuk", encoding="utf-8")
    assert oku(tmp_path) is None


def test_bozuk_takvim_tarihi_birlestirmeyi_dusurmez():
    bozuk = taban("bozuk1", "Fen", "Fen · Yazılı", "23.10.2026")
    kayitlar = birlestir([bozuk, GIS], [], None, SIMDI)
    assert {k["id"] for k in kayitlar} == {"bozuk1", "gis1"}
    k = next(k for k in kayitlar if k["id"] == "bozuk1")
    assert (k["tarih"], k["saat"], k["sentetik"], k["kaynaklar"][0]["tur"]) == (None, None, False, "takvim")
    assert k["taban"] == bozuk


def test_yayin_tarihsiz_tarihsiz_haftasiz_bulgu_ayni_cagrida_dusmez():
    [k] = birlestir([], [bulgu("Fen", "diger", konular=["Hücre"], yayin=None)], None, SIMDI)
    assert (k["tarih"], k["hafta"], k["son_yayin"]) == (None, None, "2026-10-16")


def test_konu_sirasi_icerik_surumunu_degistirmez():
    def surum(*konular):
        return birlestir([], [bulgu(tarih=date(2026, 10, 20), konular=list(konular))], None, SIMDI)[0]["icerik_surumu"]
    assert surum("Mutlak değer", "Oran", "Tam sayılar") == surum("Tam sayılar", "Mutlak değer", "Oran")
    assert surum("Mutlak değer", "Oran") != surum("Mutlak değer", "Oran", "Tam sayılar")


@pytest.mark.parametrize("ters", [False, True])
def test_bulgu_turu_metin_kaydi_kimligini_degistirmez(ters):
    b1 = bulgu(tur="konu_tarama", tarih=date(2026, 10, 15), konular=["Oran"])
    b2 = bulgu(tur="kisa_sinav", tarih=date(2026, 10, 15), konular=["Tam sayılar"], metin="başka")
    [k] = birlestir([], [b2, b1] if ters else [b1, b2], None, SIMDI)
    assert k["id"] == hashlib.md5("Matematik|2026-10-15".encode()).hexdigest()[:12]


def test_tarihsiz_kayit_kimligi_turden_bagimsiz():
    a = birlestir([], [bulgu("Fen", "diger", konular=["Hücre"])], None, SIMDI)[0]["id"]
    b = birlestir([], [bulgu("Fen", "kisa_sinav", konular=["Hücre"])], None, SIMDI)[0]["id"]
    assert a == b


def test_kisa_konular_baglamayi_tetiklemez():
    tarihli = bulgu(tarih=date(2026, 10, 20), konular=["A"])
    tarihsiz = bulgu(konular=["a"], yayin=date(2026, 10, 12), metin="başka")
    assert [k["tarih"] for k in birlestir([], [tarihli, tarihsiz], None, SIMDI)] == ["2026-10-20", None]


# --- ortak sınav ders kartında da takvime bağlanır (son inceleme, Minor 3) ---------------

@pytest.mark.parametrize("tur", ["deneme", "ortak_sinav"])
def test_ortak_sinavin_ders_karti_bulgusu_ayni_gundeki_takvime_baglanir(tur):
    """The GİS is announced in the Fen tab ("Fen Bilimleri" ≠ "Özdebir GİS"): still one exam."""
    fen = bulgu("Fen Bilimleri", tur, tarih=date(2026, 10, 23), konular=["Uzay Çağı"])
    kayitlar = birlestir([GIS], [fen], None, SIMDI)
    assert len(kayitlar) == 1
    assert kayitlar[0]["id"] == "gis1" and kayitlar[0]["konular"] == ["Uzay Çağı"]


def test_ortak_sinav_once_ayni_dersin_sonra_ortak_turun_takvimine():
    mat = taban("mat1", "Matematik", "Matematik · Yazılı", "2026-10-23T11:00:00")
    fen = bulgu("Fen Bilimleri", "deneme", tarih=date(2026, 10, 23), konular=["Uzay Çağı"])
    kayitlar = {k["id"]: k for k in birlestir([mat, GIS], [fen], None, SIMDI)}
    assert set(kayitlar) == {"mat1", "gis1"}
    assert kayitlar["gis1"]["konular"] == ["Uzay Çağı"] and kayitlar["mat1"]["konular"] == []


def test_ders_yazilisi_baska_dersin_takvimine_baglanmaz():
    fen = bulgu("Fen Bilimleri", "yazili", tarih=date(2026, 10, 23), konular=["Uzay Çağı"])
    assert len(birlestir([GIS], [fen], None, SIMDI)) == 2


# --- temizlik A (2026-10-17) -------------------------------------------------------

def test_a7_tarihsiz_kayit_kimligi_metin_ozetinden_degismedi():
    """Aday.anahtar took the course in (A7); an undated record's id still hashes the text
    alone beside the course, so no id moved and no alert fires twice."""
    from src.sinav_tarihi import katla
    [k] = birlestir([], [bulgu("Fen", "diger", konular=["Hücre"], metin="Fen quiz yakında")], None, SIMDI)
    metin_ozeti = hashlib.sha256(katla("Fen quiz yakında").encode()).hexdigest()
    assert k["id"] == hashlib.md5(f"Fen|{metin_ozeti[:12]}".encode()).hexdigest()[:12]


TR_ORTAK_HAM = ("7. Sınıf MEB Ülke Geneli Türkçe 1. Dönem 2. Ortak Yazılı Sınavı / 7th Grade MEB "
                "Nationwide Turkish 1st Term 2nd Common Written Exam")


def test_a2_taban_turu_ham_basliktan():
    e = dict(taban("trm", "Türkçe", "Türkçe · 2. Yazılı", "2027-01-05T10:30:00"), rawTitle=TR_ORTAK_HAM)
    [k] = birlestir([e], [], None, SIMDI)
    assert k["tur"] == "ortak_sinav"
    assert birlestir([dict(e, rawTitle="")], [], None, SIMDI)[0]["tur"] == "yazili"   # no raw: title


@pytest.mark.parametrize("baslik,tur", [
    ("KTT2", "konu_tarama"), ("GİS2 Sınavı", "deneme"), ("Quiz3", "kisa_sinav"),
    ("Ortaklık Haftası", "diger"), ("Okul ortaklığı semineri", "diger"), ("Ortak sınav", "ortak_sinav"),
])
def test_a15_kisa_anahtar_rakamla_ortak_tam_sozcuk(baslik, tur):
    assert takvim_turu(baslik) == tur


@pytest.mark.parametrize("bozuk", ["20261023", "2026-W43-5", "2026-10-23T25:00:00", "2026-10-23 sabah"])
def test_a16_taban_tarihi_kati_bicim(bozuk):
    [k] = birlestir([taban("b1", "Fen", "Fen · Yazılı", bozuk)], [], None, SIMDI)
    assert (k["tarih"], k["saat"], k["sentetik"]) == (None, None, False)


def test_a16_taban_tarihi_gecerli_bicimler():
    saatli = birlestir([taban("s1", "Fen", "Fen · Yazılı", "2026-10-23T09:05:00")], [], None, SIMDI)[0]
    gunluk = birlestir([taban("g1", "Fen", "Fen · Yazılı", "2026-10-23", all_day=True)], [], None, SIMDI)[0]
    assert (saatli["tarih"], saatli["saat"]) == ("2026-10-23", "09:05")
    assert (gunluk["tarih"], gunluk["saat"]) == ("2026-10-23", None)


def test_a17_ortak_sinav_gunde_birden_cok_takvim_kaydi_varsa_ayri_kayit():
    mat = taban("mat1", "Matematik", "Matematik · Yazılı", "2026-10-23T09:00:00")
    tr = taban("tr2", "Türkçe", "Türkçe · Yazılı", "2026-10-23T11:00:00")
    fen = bulgu("Fen Bilimleri", "deneme", tarih=date(2026, 10, 23), konular=["Uzay Çağı"])
    kayitlar = {k["id"]: k for k in birlestir([mat, tr], [fen], None, SIMDI)}
    assert len(kayitlar) == 3
    assert kayitlar["mat1"]["konular"] == [] and kayitlar["tr2"]["konular"] == []
    # With a single takvim record that day it still binds (the GİS case).
    assert len(birlestir([mat], [fen], None, SIMDI)) == 1


def test_a18_tarihi_degisen_metin_sinavi_ilk_tespiti_tasir():
    konum = {"bolum": "ders_icerikleri_haftalar", "hafta": "5. Hafta", "ders": "Matematik", "sira": 2}
    onceki = {"surum": SURUM, "sinavlar": birlestir(
        [], [bulgu(tarih=date(2026, 10, 20), konular=["Oran"], konum=konum)],
        {"surum": SURUM, "sinavlar": []}, datetime(2026, 10, 10, 9))}
    eski_id = onceki["sinavlar"][0]["id"]
    [k] = birlestir([], [bulgu(tarih=date(2026, 10, 22), konular=["Oran"], konum=konum)], onceki, SIMDI)
    assert k["id"] != eski_id
    assert (k["ilk_tespit"], k["degisti"]) == ("2026-10-10T09:00:00", "2026-10-16T10:00:00")


def test_a18_hala_uretilen_kaydin_konumu_tasinmaz():
    konum = {"bolum": "odev", "baslik": "KTT", "teslim": None}
    onceki = {"surum": SURUM, "sinavlar": birlestir(
        [], [bulgu(tarih=date(2026, 10, 20), konular=["Oran"], konum=konum)],
        {"surum": SURUM, "sinavlar": []}, datetime(2026, 10, 10, 9))}
    # The same post now names two exams: the old one is still produced, the new one is new.
    kayitlar = birlestir([], [bulgu(tarih=date(2026, 10, 20), konular=["Oran"], konum=konum),
                              bulgu(tarih=date(2026, 10, 27), konular=["Kesir"], konum=konum)], onceki, SIMDI)
    yeni = next(k for k in kayitlar if k["tarih"] == "2026-10-27")
    assert (yeni["ilk_tespit"], yeni["degisti"]) == ("2026-10-16T10:00:00", None)


def test_a19_tur_ve_baslik_ilk_bulguya_bagli_degil():
    diger = bulgu(tur="diger", tarih=date(2026, 10, 20), baslik="Matematik Sınav")
    yazili = bulgu(tur="yazili", tarih=date(2026, 10, 20), baslik="Matematik yazılısı", metin="başka")
    kisa = bulgu(tur="kisa_sinav", tarih=date(2026, 10, 20), baslik="Matematik quiz", metin="üçüncü")
    [k] = birlestir([], [diger, yazili, kisa], None, SIMDI)
    assert (k["tur"], k["baslik"]) == ("yazili", "Matematik yazılısı")
    # A takvim base keeps its own kind and title whatever the text says.
    fen = taban("fen9", "Fen Bilimleri", "Fen · Yazılı", "2026-10-21T09:00:00")
    [k] = birlestir([fen], [bulgu("Fen Bilimleri", "kisa_sinav", tarih=date(2026, 10, 21), baslik="Fen quiz")],
                    None, SIMDI)
    assert (k["tur"], k["baslik"]) == ("yazili", "Fen · Yazılı")


def test_a20_konu_ve_kaynak_siniri():
    from src.sinav_tespiti import KAYNAK_SINIRI, KONU_SINIRI
    bulgular = [bulgu(tarih=date(2026, 10, 20), konular=[f"Konu numarası {i}"], metin=f"metin {i}",
                      konum={"bolum": "odev", "baslik": f"Ödev {i}", "teslim": None}) for i in range(20)]
    [k] = birlestir([], bulgular, None, SIMDI)
    assert len(k["konular"]) == KONU_SINIRI and k["konular"][0] == "Konu numarası 0"
    assert len(k["kaynaklar"]) == KAYNAK_SINIRI and k["kaynaklar"][0]["konum"]["baslik"] == "Ödev 0"


def test_a20_genel_bulgu_takvimsiz_gunde_ayri_kayit():
    mat = bulgu(tarih=date(2026, 10, 20), konular=["Oran"])
    genel = bulgu("Genel", "deneme", tarih=date(2026, 10, 20), konular=["Tüm konular"], metin="genel")
    kayitlar = birlestir([], [mat, genel], None, SIMDI)
    assert sorted(k["ders"] for k in kayitlar) == ["Genel", "Matematik"]
