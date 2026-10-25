"""Kılavuz modeli (plan Görev 6–7): ders anahtarları, sınav durumu (K8), genel bakış, ders özeti, güncellik (K12)."""
from datetime import date

import pytest

from src import sinav_kilavuzu as sk
from tests.hazirlik_fikstur import BUGUN, TABLO, fen_haritasi, girdiler, sinav_kaydi

TR_GECTI = dict(senaryo=4, tarih="2026-10-22", status="past", sid="tr11")
TR_ULKE = dict(durum="ulke_geneli", senaryo=None, tarih="2027-01-05", sid="tr12")


def test_ders_anahtarlari_alti_ders_ve_tablo_ile_ayni():
    assert list(sk.ANAHTAR_DERSLERI) == ["turkce", "matematik", "fen-bilimleri", "sosyal-bilgiler", "ingilizce",
                                         "din-kulturu"]
    assert set(sk.ANAHTAR_DERSLERI.values()) == set(TABLO["dersler"])


def test_tablo_durumu_yil_ve_donem():
    assert sk.tablo_durumu(TABLO, BUGUN) is None
    assert sk.tablo_durumu(TABLO, date(2027, 1, 20)) is None      # Ocak hâlâ 1. dönem
    assert sk.tablo_durumu(TABLO, date(2027, 2, 10)) == "tablo_eski"
    assert sk.tablo_durumu(TABLO, date(2027, 10, 1)) == "tablo_eski"
    assert sk.tablo_durumu(None, BUGUN) == "tablo_yok"


def test_harita_oku_bozuk_ya_da_eski_surum_none(tmp_path):
    (tmp_path / "fen-bilimleri.json").write_text("{", encoding="utf-8")
    assert sk.harita_oku("fen-bilimleri", tmp_path) is None
    (tmp_path / "fen-bilimleri.json").write_text('{"surum": 2, "kitaplar": [], "eslesme": {}}', encoding="utf-8")
    assert sk.harita_oku("fen-bilimleri", tmp_path) is None
    assert sk.harita_oku("matematik", tmp_path) is None


def test_sinav_durumu_kesin_tarih_ve_geri_sayim():
    d = sk.sinav_durumu(girdiler(), "Fen Bilimleri", 1)
    assert (d["tur"], d["senaryo"], d["senaryo_sayisi"], d["tarih"], d["kalan_gun"]) == ("kesin", 2, 4, "2026-11-03", 9)
    assert d["duyuru"].startswith("Sınav, İstanbul İl MEB") and d["sinav_id"] == "fen11"
    assert (d["duyurulan_konu"], d["uyari"]) == (3, None)


def test_sinav_durumu_kismen_uyari_tasir():
    g = girdiler(sinavlar=[sinav_kaydi(durum="kismen", konular=("a", "b"), senaryo_disi=("b",))])
    d = sk.sinav_durumu(g, "Fen Bilimleri", 1)
    assert (d["tur"], d["senaryo"], d["uyari"]) == ("kesin", 2, "kismen")


@pytest.mark.parametrize("kayitlar", [[], [sinav_kaydi(durum="belirtilmedi", senaryo=None)]])
def test_sinav_durumu_olasi_tek_senaryo_tasimaz(kayitlar):
    d = sk.sinav_durumu(girdiler(sinavlar=kayitlar), "Fen Bilimleri", 1)
    assert (d["tur"], d["senaryo"], d["senaryo_sayisi"]) == ("olasi", None, 4)


def test_sinav_durumu_senaryo_yok_uyarisi():
    g = girdiler(sinavlar=[sinav_kaydi(durum="senaryo_yok", senaryo=None, anilan=[9])])
    d = sk.sinav_durumu(g, "Fen Bilimleri", 1)
    assert (d["tur"], d["senaryo"], d["uyari"], d["anilan"]) == ("olasi", None, "senaryo_yok", [9])


def test_sinav_durumu_gecti_ve_ulke_geneli():
    g = girdiler(sinavlar=[sinav_kaydi("Türkçe", 1, **TR_GECTI), sinav_kaydi("Türkçe", 2, **TR_ULKE)])
    gecti = sk.sinav_durumu(g, "Türkçe", 1)
    assert (gecti["tur"], gecti["senaryo"], gecti["kalan_gun"]) == ("gecti", 4, None)
    ulke = sk.sinav_durumu(g, "Türkçe", 2)
    assert (ulke["tur"], ulke["senaryo_sayisi"], ulke["kalan_gun"]) == ("ulke_geneli", 0, 72)


def test_genel_bakis_once_zaman_sonra_alti_ders():
    g = girdiler(sinavlar=[sinav_kaydi(konular=("a", "b", "c")), sinav_kaydi("Türkçe", 1, **TR_GECTI),
                           sinav_kaydi("Türkçe", 2, **TR_ULKE)])
    gb = sk.genel_bakis(g)
    assert gb["durum"] == "hazir" and gb["kaynak"]["meb_guncelleme"] == "2026-09-10T17:27"
    assert [(y["anahtar"], y["sinav_no"], y["durum"]["tur"], y["soru"]) for y in gb["yaklasan"]] == [
        ("fen-bilimleri", 1, "kesin", 7), ("turkce", 2, "ulke_geneli", None)]
    assert [d["anahtar"] for d in gb["dersler"]] == list(sk.ANAHTAR_DERSLERI)
    fen = next(d for d in gb["dersler"] if d["anahtar"] == "fen-bilimleri")
    assert fen["kitap_bolumleri"] is True
    assert [(s["sinav_no"], s["durum"]["tur"], s["soru"]) for s in fen["sinavlar"]] == [(1, "kesin", 7), (2, "olasi", None)]
    tr = next(d for d in gb["dersler"] if d["anahtar"] == "turkce")
    assert [(s["durum"]["tur"], s["soru"]) for s in tr["sinavlar"]] == [("gecti", 7), ("ulke_geneli", None)]
    mat = next(d for d in gb["dersler"] if d["anahtar"] == "matematik")
    assert mat["kitap_bolumleri"] is False and mat["sinavlar"][0]["durum"]["tarih"] is None


def test_genel_bakis_tablo_eski_ders_listelemez():
    gb = sk.genel_bakis(girdiler(bugun=date(2027, 2, 10)))
    assert (gb["durum"], gb["yaklasan"], gb["dersler"]) == ("tablo_eski", [], [])
    assert sk.genel_bakis(girdiler(tablo=None))["durum"] == "tablo_yok"


def test_ders_ozeti_matris_fen_1():
    oz = sk.ders_ozeti(girdiler(), "fen-bilimleri", 1)
    assert (oz["ders"], oz["tur"], oz["senaryolar"], oz["duyurulan"]) == ("Fen Bilimleri", "senaryolu", [1, 2, 3, 4], 2)
    assert oz["toplamlar"] == {"1": 9, "2": 7, "3": 8, "4": 6}
    assert [g["baslik"] for g in oz["gruplar"]] == ["1. Ünite · Uzay Çağı", "2. Ünite · Kuvvet ve Enerjiyi Keşfedelim"]
    satirlar = {s["kod"]: s for g in oz["gruplar"] for s in g["satirlar"]}
    # FB.7.1.2 1. yazılının hiçbir senaryosunda yok: satır olmaz.
    assert list(satirlar) == ["FB.7.1.1", "FB.7.1.3", "FB.7.1.4", "FB.7.1.5", "FB.7.2.1", "FB.7.2.2"]
    is_ = satirlar["FB.7.2.1"]
    assert (is_["kisa_ad"], is_["sayilar"], is_["her_senaryoda"], is_["kitap_durumu"]) == (
        "Fiziksel anlamda yapılan işin bağlı olduğu faktörlere ilişkin bilimsel çıkarım yapabilme",
        {"1": 3, "2": 3, "3": 2, "4": 2}, True, "var")
    assert is_["kitapta"] == [{
        "kitap": "Fen Bilimleri 7 (1. Kitap)", "unite": "2. Ünite", "unite_no": 2,
        "unite_ad": "Kuvvet ve Enerjiyi Keşfedelim", "cerceve": "1. Kuvvet, İş ve Enerji İlişkisi", "cerceve_no": 1,
        "konu": "Fiziksel Anlamda İş", "sayfa": 60, "son_sayfa": 63,
        "baglanti": "https://cdn.eba.gov.tr/temel-egitim/yayin/2026-2027/ktp/fenbilimleri7-1_v3.pdf#page=61"}]
    assert satirlar["FB.7.1.1"]["kisa_ad"] == "Uzay araştırmaları için geliştirilen teknolojileri karşılaştırabilme"
    assert satirlar["FB.7.1.1"]["her_senaryoda"] is False
    assert [s["sinav_no"] for s in oz["sinavlar"]] == [1, 2]
    assert (oz["kitap_bolumleri"], oz["harita_onayli"]) == (True, True)
    assert oz["guncellik"] == {"tablo_degisti": False, "kitap_degisti": False}


def test_ders_ozeti_haritasiz_ders_kitap_bolumu_yok():
    oz = sk.ders_ozeti(girdiler(), "matematik", 1)
    assert oz["kitap_bolumleri"] is False and oz["gruplar"][0]["baslik"] == "1. Ünite"
    assert all(s["kitap_durumu"] == "harita_yok" and s["kitapta"] == [] for g in oz["gruplar"] for s in g["satirlar"])


def test_ders_ozeti_turkce_alan_grubu_ve_ulke_geneli():
    oz = sk.ders_ozeti(girdiler(), "turkce", 1)
    assert [g["baslik"] for g in oz["gruplar"]] == ["Okuma", "Yazma"]
    ulke = sk.ders_ozeti(girdiler(), "turkce", 2)
    assert (ulke["tur"], ulke["senaryolar"], ulke["gruplar"], ulke["toplamlar"]) == ("ulke_geneli", [], [], {})
    assert ulke["not"].startswith("1. Dönem 2. Ortak Yazılı")


def test_ders_ozeti_kitapta_karsiligi_bulunamadi():
    """Review Focus: haritada eşleşmeyen çıktı 'bulunamadi' — 'yok' değil; kodundaki ünite numarasıyla aynı ünite
    grubunda kalır."""
    h = fen_haritasi()
    h["eslesme"].pop("FB.7.1.3")
    h["eslesmedi"] = ["FB.7.1.3"]
    oz = sk.ders_ozeti(girdiler(haritalar={"fen-bilimleri": h}), "fen-bilimleri", 1)
    s = next(s for g in oz["gruplar"] for s in g["satirlar"] if s["kod"] == "FB.7.1.3")
    assert (s["kitap_durumu"], s["kitapta"]) == ("bulunamadi", [])
    uzay = next(g for g in oz["gruplar"] if g["baslik"] == "1. Ünite · Uzay Çağı")
    assert "FB.7.1.3" in [s["kod"] for s in uzay["satirlar"]]


def test_guncellik_tablo_ve_kitap_degisti():
    """Review Focus (K12): harita eski tabloya göre kurulmuşsa ya da kitap PDF'i değiştiyse güncel değil."""
    h = fen_haritasi()
    h["senaryo_tablosu"]["ders_sha256"] = "0" * 64
    oz = sk.ders_ozeti(girdiler(haritalar={"fen-bilimleri": h}), "fen-bilimleri", 1)
    assert oz["guncellik"] == {"tablo_degisti": True, "kitap_degisti": False}

    def denetim(sha):
        return {"fen-bilimleri": {"denetlendi": "2026-10-26", "kitaplar": [{"pdf_url": h["kitaplar"][0]["pdf_url"],
                                                                             "sha256": sha}]}}
    oz = sk.ders_ozeti(girdiler(kitap_denetimi=denetim("b" * 64)), "fen-bilimleri", 1)
    assert oz["guncellik"] == {"tablo_degisti": False, "kitap_degisti": True}
    assert sk.ders_ozeti(girdiler(kitap_denetimi=denetim("a" * 64)), "fen-bilimleri", 1)["guncellik"]["kitap_degisti"] is False


def test_onaysiz_harita():
    h = fen_haritasi()
    h["denetim"] = {"kim": None, "tarih": None}
    assert sk.ders_ozeti(girdiler(haritalar={"fen-bilimleri": h}), "fen-bilimleri", 1)["harita_onayli"] is False


@pytest.mark.parametrize("anahtar,no,kod", [("fizik", 1, "bilinmeyen_ders"), ("fen-bilimleri", 3, "bilinmeyen_sinav")])
def test_ders_ozeti_bilinmeyen(anahtar, no, kod):
    with pytest.raises(sk.KilavuzHatasi) as h:
        sk.ders_ozeti(girdiler(), anahtar, no)
    assert h.value.kod == kod


@pytest.mark.parametrize("degisiklik,kod", [({"bugun": date(2027, 2, 10)}, "tablo_eski"), ({"tablo": None}, "tablo_yok")])
def test_ders_ozeti_tablo_eski_ve_yok(degisiklik, kod):
    with pytest.raises(sk.KilavuzHatasi) as h:
        sk.ders_ozeti(girdiler(**degisiklik), "fen-bilimleri", 1)
    assert h.value.kod == kod


# --- Görev 6 ek testleri (kontrolcü kararları U4/D19, D22, K8; konu=None) ---------------------------------------

def _gruplar(oz):
    return {g["baslik"]: [s["kod"] for s in g["satirlar"]] for g in oz["gruplar"]}


@pytest.mark.parametrize("cikar", [["FB.7.1.1"], ["FB.7.1.1", "FB.7.1.3", "FB.7.1.4", "FB.7.1.5"]])
def test_unite_basligi_haritanin_unitesinden_ilk_cikti_bulunamasa_da(cikar):
    """U4/D19: grup başlığı gruba ilk giren çıktıdan değil haritanın ünitesinden çözülür — bir ünitenin ilk çıktısı
    (ya da hepsi) haritada bulunamasa da başlık "1. Ünite" diye kalmaz, çıktılar kendi ünitesinde durur."""
    h = fen_haritasi()
    for kod in cikar:
        h["eslesme"].pop(kod)
        h["eslesmedi"].append(kod)
    oz = sk.ders_ozeti(girdiler(haritalar={"fen-bilimleri": h}), "fen-bilimleri", 1)
    gruplar = _gruplar(oz)
    assert list(gruplar) == ["1. Ünite · Uzay Çağı", "2. Ünite · Kuvvet ve Enerjiyi Keşfedelim"]
    assert "FB.7.1.1" in gruplar["1. Ünite · Uzay Çağı"] or "FB.7.1.3" in gruplar["1. Ünite · Uzay Çağı"]
    for kod in cikar:
        assert kod in gruplar["1. Ünite · Uzay Çağı"]


def test_unite_basligi_haritada_olmayan_unite_numarayla_kalir():
    h = fen_haritasi()
    h["kitaplar"][0]["uniteler"] = [u for u in h["kitaplar"][0]["uniteler"] if u["no"] != 1]
    for kod in ("FB.7.1.1", "FB.7.1.3", "FB.7.1.4", "FB.7.1.5"):
        h["eslesme"].pop(kod)
    oz = sk.ders_ozeti(girdiler(haritalar={"fen-bilimleri": h}), "fen-bilimleri", 1)
    assert list(_gruplar(oz)) == ["1. Ünite", "2. Ünite · Kuvvet ve Enerjiyi Keşfedelim"]


def test_unite_grubu_yardimcisi_tek_anahtar_ve_baslik():
    h = fen_haritasi()
    assert sk.unite_grubu(h, 2) == ((0, 2, ""), "2. Ünite · Kuvvet ve Enerjiyi Keşfedelim")
    assert sk.unite_grubu(h, 7) == ((0, 7, ""), "7. Ünite")
    assert sk.unite_grubu(None, 1) == ((0, 1, ""), "1. Ünite")


def test_kitapta_konusuz_cerceve_baglantisi_cokmez():
    """Çıktı çerçeveye bağlı ama hiçbir konuya benzemiyorsa (`konu: None`) çerçeve düzeyinde bağlı sayılır."""
    h = fen_haritasi()
    h["eslesme"]["FB.7.2.1"] = [{"kitap": 0, "unite": 2, "cerceve": 1, "konu": None}]
    oz = sk.ders_ozeti(girdiler(haritalar={"fen-bilimleri": h}), "fen-bilimleri", 1)
    s = next(s for g in oz["gruplar"] for s in g["satirlar"] if s["kod"] == "FB.7.2.1")
    assert s["kitap_durumu"] == "var"
    assert s["kitapta"][0]["konu"] is None
    assert (s["kitapta"][0]["cerceve"], s["kitapta"][0]["sayfa"], s["kitapta"][0]["son_sayfa"]) == (
        "1. Kuvvet, İş ve Enerji İlişkisi", 59, 70)
    assert s["kitapta"][0]["baglanti"].endswith("#page=60")
    assert s["kisa_ad"] == s["metin"]                       # konu adı yok: yine MEB metninin kendisi


def test_cikti_etiketi_meb_metninin_kendisi_kisaltma_ve_konu_adi_yok():
    """Karar (düzeltme turu 1, K1/K6): satırın etiketi MEB çıktı metni, kısaltmasız ve "…"sız; kitap konusunun adı yalnız
    `kitapta` yollarında görünür."""
    oz = sk.ders_ozeti(girdiler(), "fen-bilimleri", 1)
    satirlar = [s for g in oz["gruplar"] for s in g["satirlar"]]
    assert satirlar
    for s in satirlar:
        assert s["kisa_ad"] == s["metin"], s["kod"]
        assert "…" not in s["kisa_ad"], s["kod"]
    is_ = next(s for s in satirlar if s["kod"] == "FB.7.2.1")
    assert is_["kitapta"][0]["konu"] == "Fiziksel Anlamda İş" and is_["kisa_ad"] != "Fiziksel Anlamda İş"


def test_gecti_senaryoyu_tasir_duyurulmamissa_tasimaz():
    """D22: geçmiş sınavda duyurulan senaryo durumda ve özette durur; duyurulmamışsa hiçbir senaryo uydurulmaz (K8)."""
    bilinen = girdiler(sinavlar=[sinav_kaydi(**{**TR_GECTI, "ders": "Fen Bilimleri"})])
    d = sk.sinav_durumu(bilinen, "Fen Bilimleri", 1)
    assert (d["tur"], d["senaryo"], d["kalan_gun"]) == ("gecti", 4, None)
    assert sk.ders_ozeti(bilinen, "fen-bilimleri", 1)["duyurulan"] == 4
    bilinmeyen = girdiler(sinavlar=[sinav_kaydi(durum="belirtilmedi", senaryo=None, tarih="2026-10-22", status="past")])
    d = sk.sinav_durumu(bilinmeyen, "Fen Bilimleri", 1)
    assert (d["tur"], d["senaryo"]) == ("gecti", None)
    assert sk.ders_ozeti(bilinmeyen, "fen-bilimleri", 1)["duyurulan"] is None


def test_gecti_tabloda_olmayan_senaryoyu_tasimaz():
    g = girdiler(sinavlar=[sinav_kaydi(durum="senaryo_yok", senaryo=None, anilan=[9], tarih="2026-10-22", status="past")])
    d = sk.sinav_durumu(g, "Fen Bilimleri", 1)
    assert (d["tur"], d["senaryo"], d["anilan"]) == ("gecti", None, [9])


@pytest.mark.parametrize("kayitlar", [[], [sinav_kaydi(durum="belirtilmedi", senaryo=None)],
                                      [sinav_kaydi(durum="senaryo_yok", senaryo=None, anilan=[9])]])
def test_ders_ozeti_olasi_durumda_duyurulan_senaryo_yok(kayitlar):
    """K8: senaryo duyurulmamışsa özet hiçbir senaryoyu "duyurulan" diye sunmaz."""
    oz = sk.ders_ozeti(girdiler(sinavlar=kayitlar), "fen-bilimleri", 1)
    assert (oz["durum"]["tur"], oz["durum"]["senaryo"], oz["duyurulan"]) == ("olasi", None, None)
    assert oz["senaryolar"] == [1, 2, 3, 4]
