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
    assert k["id"] == hashlib.md5("Matematik|konu_tarama|2026-10-15".encode()).hexdigest()[:12]
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
    assert k["id"] == hashlib.md5("İngilizce|kisa_sinav|hafta:2026-10-19".encode()).hexdigest()[:12]


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
