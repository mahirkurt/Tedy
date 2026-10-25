"""Kılavuz modeli II (plan Görev 7): kılavuz blokları, olası kip (K8), bağlam, doğrulama, plan, ebeveyn, damgalar."""
from datetime import date

import pytest

from src import sinav_kilavuzu as sk
from tests.hazirlik_fikstur import FEN_KONULARI, fen_haritasi, girdiler, sinav_kaydi

SEC = {"ebeveyn": False, "isaret": True}


def _bloklar(model):
    return {b["kod"]: b for u in model["uniteler"] for c in u["cerceveler"] for b in c["bloklar"]}


def test_kilavuz_kesin_bloklar_ve_soru():
    m = sk.kilavuz(girdiler(), "fen-bilimleri", 1, None, SEC)
    assert (m["kip"], m["senaryo"], m["duyurulan"], m["secilen_duyurulan_degil"]) == ("kesin", 2, 2, False)
    assert m["ozet"] == {"toplam_soru": 7, "soru_araligi": None, "cikti_sayisi": 4, "her_senaryoda": ["FB.7.2.1"]}
    b = _bloklar(m)
    assert (b["FB.7.2.1"]["soru"], b["FB.7.2.1"]["senaryoda"], b["FB.7.2.1"]["aralik"]) == (3, True, None)
    assert (b["FB.7.2.2"]["soru"], b["FB.7.2.2"]["senaryoda"]) == (0, False)    # 2. senaryoda yok: soluk satır
    assert [u["baslik"] for u in m["uniteler"]] == ["1. Ünite · Uzay Çağı", "2. Ünite · Kuvvet ve Enerjiyi Keşfedelim"]
    kuvvet = m["uniteler"][1]["cerceveler"][0]
    assert (kuvvet["baslik"], kuvvet["sayfa"], kuvvet["son_sayfa"]) == ("1. Kuvvet, İş ve Enerji İlişkisi", 59, 70)
    assert [x["kod"] for x in kuvvet["bloklar"]] == ["FB.7.2.1", "FB.7.2.2"]
    assert m["yz"] == {"durum": "kapali"} and m["surum"] == 1


def test_kilavuz_olasi_kip_tek_senaryo_sunmaz():
    """Review Focus (K8): duyuru yokken hiçbir blok tek soru sayısı, özet tek toplam taşımaz."""
    m = sk.kilavuz(girdiler(sinavlar=[]), "fen-bilimleri", 1, None, SEC)
    assert (m["kip"], m["senaryo"], m["duyurulan"], m["durum"]["tur"]) == ("olasi", None, None, "olasi")
    assert m["ozet"]["toplam_soru"] is None and m["ozet"]["soru_araligi"] == [6, 9]
    b = _bloklar(m)
    assert all(x["soru"] is None and x["senaryoda"] for x in b.values())
    assert b["FB.7.2.1"]["aralik"] == [2, 3] and b["FB.7.1.1"]["aralik"] == [0, 2]


def test_kilavuz_secilen_senaryo_duyurulan_degil():
    m = sk.kilavuz(girdiler(), "fen-bilimleri", 1, 3, SEC)
    assert (m["kip"], m["senaryo"], m["duyurulan"], m["secilen_duyurulan_degil"]) == ("olasi", 3, 2, True)
    assert m["ozet"]["toplam_soru"] == 8


def test_kilavuz_bilinmeyen_senaryo_hata():
    with pytest.raises(sk.KilavuzHatasi) as h:
        sk.kilavuz(girdiler(), "fen-bilimleri", 1, 9, SEC)
    assert h.value.kod == "bilinmeyen_senaryo"


def test_kilavuz_kitapta_ve_bolum_basliklari():
    b = _bloklar(sk.kilavuz(girdiler(), "fen-bilimleri", 1, None, SEC))
    assert b["FB.7.2.1"]["kitapta"][0]["baglanti"].endswith("#page=61")
    assert [(x["tur"], x["ad"], x["sayfa"]) for x in b["FB.7.2.1"]["basliklar"]] == [
        ("etkinlik", "Etkinlik Noktası-1", 60), ("etkinlik", "Etkinlik Noktası-2", 60),
        ("baglanti", "Bağlantı Noktası", 62), ("kontrol", "Kontrol Noktası", 63)]
    # İki konuya bağlı çıktı: iki konunun başlıkları sırayla.
    assert [x["ad"] for x in b["FB.7.1.1"]["basliklar"]][:2] == ["Keşif Noktası: Uzay Teknolojileri", "Kontrol Noktası"]
    assert "Neler Öğrendik?" in [x["ad"] for x in b["FB.7.1.1"]["basliklar"]]


def test_cerceveye_bagli_cikti_cercevenin_butun_basliklarini_alir():
    h = fen_haritasi()
    h["eslesme"]["FB.7.2.1"] = [{"kitap": 0, "unite": 2, "cerceve": 1, "konu": None}]
    b = _bloklar(sk.kilavuz(girdiler(haritalar={"fen-bilimleri": h}), "fen-bilimleri", 1, None, SEC))
    adlar = [x["ad"] for x in b["FB.7.2.1"]["basliklar"]]
    assert adlar[0] == "Bağlantı Noktası" and "Potansiyel Enerji" in adlar
    assert b["FB.7.2.1"]["kitapta"][0]["konu"] is None and b["FB.7.2.1"]["kitapta"][0]["sayfa"] == 59


def test_kilavuz_bulunamayan_cikti_blokta_bulunamadi():
    h = fen_haritasi()
    h["eslesme"].pop("FB.7.1.3")
    h["eslesmedi"] = ["FB.7.1.3"]
    m = sk.kilavuz(girdiler(haritalar={"fen-bilimleri": h}), "fen-bilimleri", 1, None, SEC)
    b = _bloklar(m)["FB.7.1.3"]
    assert (b["kitap_durumu"], b["kitapta"], b["basliklar"]) == ("bulunamadi", [], [])


def test_kilavuz_haritasiz_ders_kitap_bolumleri_yok():
    m = sk.kilavuz(girdiler(), "matematik", 1, None, SEC)
    assert (m["kitap_bolumleri"], m["kip"]) == (False, "olasi")
    assert [u["baslik"] for u in m["uniteler"]] == ["1. Ünite"]
    assert m["uniteler"][0]["cerceveler"][0]["baslik"] is None
    assert all(b["kitap_durumu"] == "harita_yok" for b in _bloklar(m).values())
    assert m["damgalar"]["kitaplar"] == [] and len(m["kaynaklar"]) == 2


def test_okulda_odev_ve_modul_baglami():
    haftalar = {"4. Hafta 05 Eki. - 11 Eki.": {"Fen Bilimleri": {"cards": ["Bu hafta fiziksel anlamda iş konusunu işledik."]}},
                "2. Hafta 21 Eyl. - 27 Eyl.": {"Fen Bilimleri": {"cards": ["Uzay teknolojileri sunumları"]}},
                "3. Hafta 28 Eyl. - 04 Eki.": {"Matematik": {"cards": ["Fiziksel anlamda iş"]}}}
    odevler = [{"Ders Adı": "Fen Bilimleri", "Ödev Başlığı": "İş ve enerji", "Ödev Son Teslim Tarihi": "30.10.2026 23:59",
                "detail": {"description": "Fiziksel anlamda iş sorularını çöz"}},
               {"Ders Adı": "Matematik", "Ödev Başlığı": "Fiziksel anlamda iş", "detail": {}}]
    moduller = [{"slug": "fen7-is", "version": 2, "title": "İş ve Enerji", "outcomes": ["FB.7.2.1"]},
                {"slug": "fen7-uzay", "version": 1, "title": "Uzay", "outcomes": ["FB.7.1.1"]}]
    b = _bloklar(sk.kilavuz(girdiler(haftalar=haftalar, odevler=odevler, moduller=moduller), "fen-bilimleri", 1, None, SEC))
    assert b["FB.7.2.1"]["okulda"] == [{"hafta": "4. Hafta 05 Eki. - 11 Eki."}]
    assert b["FB.7.1.1"]["okulda"] == [{"hafta": "2. Hafta 21 Eyl. - 27 Eyl."}]
    assert b["FB.7.2.1"]["odevler"] == [{"baslik": "İş ve enerji", "teslim": "30.10.2026 23:59"}]
    assert b["FB.7.2.1"]["moduller"] == [{"baslik": "İş ve Enerji", "yol": "/moduller/fen7-is/v2"}]
    assert b["FB.7.2.2"]["okulda"] == [] and b["FB.7.2.2"]["moduller"] == []


def test_dogrulama_duyuru_konulari():
    is_ = "Fiziksel anlamda yapılan işin bağlı olduğu faktörlere ilişkin bilimsel çıkarım yapabilme"
    g = girdiler(sinavlar=[sinav_kaydi(durum="kismen", konular=(is_, "Mısır tarihi"),
                                       eslesmeyen=("Mısır tarihi",), senaryo_disi=(), duyuruda=("FB.7.2.1",))])
    d = sk.kilavuz(g, "fen-bilimleri", 1, None, SEC)["dogrulama"]
    assert d["duyurulan_konular"][0] == {"konu": is_, "kodlar": ["FB.7.2.1"]}
    assert d["duyurulan_konular"][1] == {"konu": "Mısır tarihi", "kodlar": []}
    assert d["karsiligi_yok"] == ["Mısır tarihi"]
    assert d["duyurunun_saymadigi"] == ["FB.7.1.1", "FB.7.1.3", "FB.7.1.5"]
    assert sk.kilavuz(girdiler(sinavlar=[sinav_kaydi()]), "fen-bilimleri", 1, None, SEC)["dogrulama"] is None


def test_calisma_plani_dagilimi_ve_isaret_onceligi():
    g = girdiler(bugun=date(2026, 10, 30), isaretler={"fen-bilimleri": {"FB.7.1.5": "tekrar", "FB.7.2.1": "hazirim"}})
    plan = sk.kilavuz(g, "fen-bilimleri", 1, None, SEC)["plan"]
    # 30.10–02.11 dört gün: ilk üçü çalışma, 02.11 genel tekrar. Sıra: tekrar, işaretsizler (ağırlık), hazırım.
    assert plan["gunler"] == [
        {"tarih": "2026-10-30", "ciktilar": ["FB.7.1.5", "FB.7.2.1"], "genel_tekrar": False},
        {"tarih": "2026-10-31", "ciktilar": ["FB.7.1.1"], "genel_tekrar": False},
        {"tarih": "2026-11-01", "ciktilar": ["FB.7.1.3"], "genel_tekrar": False},
        {"tarih": "2026-11-02", "ciktilar": ["FB.7.1.5", "FB.7.1.1", "FB.7.1.3", "FB.7.2.1"], "genel_tekrar": True}]
    assert sk.calisma_plani([], date(2026, 11, 3), date(2026, 11, 3)) is None
    assert sk.kilavuz(girdiler(sinavlar=[]), "fen-bilimleri", 1, None, SEC)["plan"] is None   # tarih yok


def test_ebeveyn_ozeti_ve_isaret_secenegi():
    g = girdiler(isaretler={"fen-bilimleri": {"FB.7.2.1": "tekrar", "FB.7.1.1": "hazirim"}})
    m = sk.kilavuz(g, "fen-bilimleri", 1, None, {"ebeveyn": True, "isaret": True})
    assert m["ebeveyn"] == {"cikti_sayisi": 4, "toplam_soru": 7, "soru_araligi": None, "hazirim": 1, "tekrar": 1,
                            "isaretsiz": 2, "en_agir": ["FB.7.2.1", "FB.7.1.1", "FB.7.1.3"]}
    assert _bloklar(m)["FB.7.2.1"]["isaret"] == "tekrar"
    kapali = sk.kilavuz(g, "fen-bilimleri", 1, None, {"ebeveyn": False, "isaret": False})
    assert kapali["ebeveyn"] is None and all(b["isaret"] is None for b in _bloklar(kapali).values())
    assert kapali["secenekler"] == {"ebeveyn": False, "isaret": False}


def test_damgalar_kaynaklar_ve_icerik_ozeti():
    m = sk.kilavuz(girdiler(), "fen-bilimleri", 1, None, SEC)
    assert m["damgalar"] == {"meb_guncelleme": "2026-09-10T17:27", "tablo_alindi": "2026-10-20",
                             "kitaplar": [{"baslik": "Fen Bilimleri 7 (1. Kitap)", "baski": "2026-2027",
                                           "sha256_kisa": "a" * 12}], "uretim": "2026-10-25"}
    assert [k["etiket"] for k in m["kaynaklar"]] == [
        "MEB ÖDSGM · 1. Dönem Konu Soru Dağılım Tabloları (2026-2027)", "Fen Bilimleri konu-soru dağılım tablosu",
        "Fen Bilimleri 7 (1. Kitap) (EBA PDF)"]
    assert m["icerik_ozeti"] == sk.icerik_ozeti(m) == sk.kilavuz(girdiler(), "fen-bilimleri", 1, None, SEC)["icerik_ozeti"]
    isaretli = sk.kilavuz(girdiler(isaretler={"fen-bilimleri": {"FB.7.2.1": "tekrar"}}), "fen-bilimleri", 1, None, SEC)
    assert isaretli["icerik_ozeti"] != m["icerik_ozeti"]


def test_ulke_geneli_kilavuz_ve_tablo_eski():
    m = sk.kilavuz(girdiler(sinavlar=[sinav_kaydi("Türkçe", 2, durum="ulke_geneli", senaryo=None, tarih="2027-01-05")]),
                   "turkce", 2, None, SEC)
    assert (m["kip"], m["uniteler"], m["plan"], m["ozet"]["cikti_sayisi"]) == ("ulke_geneli", [], None, 0)
    assert m["not"].startswith("1. Dönem 2. Ortak Yazılı")
    with pytest.raises(sk.KilavuzHatasi) as h:
        sk.kilavuz(girdiler(bugun=date(2027, 2, 10)), "fen-bilimleri", 1, None, SEC)
    assert h.value.kod == "tablo_eski"


def test_gercek_fen_haritasiyla_kilavuz_kurulur():
    """Görev 5'in gerçek haritası modelin şemasına uyar (harita yeniden üretilirse burada düşer)."""
    h = sk.harita_oku("fen-bilimleri")
    assert h is not None
    m = sk.kilavuz(girdiler(haritalar={"fen-bilimleri": h}), "fen-bilimleri", 1, None, SEC)
    b = _bloklar(m)
    assert all(x["kitap_durumu"] == "var" and x["basliklar"] for x in b.values())
    assert b["FB.7.2.1"]["kitapta"][0]["konu"] == "Fiziksel Anlamda İş"


# ── Kontrolcü kararları (U4/D4, D16, K8) ───────────────────────────────────────────────────────────────────────

def _dugumler(model):
    """(üst düzey, düğüm düzeyi, ad) üçlüleri: ünite › çerçeve (varsa) › çıktı."""
    for u in model["uniteler"]:
        yield 0, u["duzey"], u["baslik"]
        for c in u["cerceveler"]:
            ust = u["duzey"]
            if c["baslik"] is not None:
                yield ust, c["duzey"], c["baslik"]
                ust = c["duzey"]
            for b in c["bloklar"]:
                yield ust, b["duzey"], b["kod"]


def test_uniteler_ve_bolumler_tekil_bulunamayan_kendi_unitesinde():
    """U4: eşleşmeyen çıktı kendi ünitesinin bölümünde "bulunamadı" bloğu olur; aynı adla ikinci ünite açılmaz."""
    h = fen_haritasi()
    h["eslesme"].pop("FB.7.1.3")
    h["eslesmedi"] = ["FB.7.1.3"]
    m = sk.kilavuz(girdiler(haritalar={"fen-bilimleri": h}, sinavlar=[]), "fen-bilimleri", 1, None, SEC)
    basliklar = [u["baslik"] for u in m["uniteler"]]
    assert len(basliklar) == len(set(basliklar))
    for u in m["uniteler"]:
        cer = [c["baslik"] for c in u["cerceveler"]]
        assert len(cer) == len(set(cer))
    birinci = next(u for u in m["uniteler"] if u["baslik"] == "1. Ünite · Uzay Çağı")
    yok = [c for c in birinci["cerceveler"] if c["baslik"] is None]
    assert len(yok) == 1 and [b["kod"] for b in yok[0]["bloklar"]] == ["FB.7.1.3"]
    assert yok[0]["bloklar"][0]["kitap_durumu"] == "bulunamadi"
    assert [c["baslik"] for c in birinci["cerceveler"]][-1] is None      # numaralı çerçevelerden sonra


def test_butun_unitesi_bulunamayan_unite_adini_haritadan_alir():
    h = fen_haritasi()
    for kod in ("FB.7.2.1", "FB.7.2.2", "FB.7.2.3"):
        h["eslesme"].pop(kod)
    m = sk.kilavuz(girdiler(haritalar={"fen-bilimleri": h}, sinavlar=[]), "fen-bilimleri", 1, None, SEC)
    ikinci = [u for u in m["uniteler"] if u["baslik"].startswith("2. Ünite")]
    assert [u["baslik"] for u in ikinci] == ["2. Ünite · Kuvvet ve Enerjiyi Keşfedelim"]
    assert [c["baslik"] for c in ikinci[0]["cerceveler"]] == [None]


def test_ders_ozeti_ile_ayni_unite_basliklari_ve_sirasi():
    g = girdiler()
    m = sk.kilavuz(g, "fen-bilimleri", 1, None, SEC)
    assert [u["baslik"] for u in m["uniteler"]] == [x["baslik"] for x in sk.ders_ozeti(g, "fen-bilimleri", 1)["gruplar"]]


def test_baslik_duzeyi_sicramaz():
    """D4: çerçeve başlığı yoksa çıktı başlığı bir basamak yukarıda; hiçbir düzey atlanmaz."""
    h = fen_haritasi()
    h["eslesme"].pop("FB.7.1.3")
    h["eslesmedi"] = ["FB.7.1.3"]
    for model in (sk.kilavuz(girdiler(haritalar={"fen-bilimleri": h}), "fen-bilimleri", 1, None, SEC),
                  sk.kilavuz(girdiler(), "matematik", 1, None, SEC)):
        dugumler = list(_dugumler(model))
        assert dugumler and all(d == ust + 1 for ust, d, _ in dugumler)
    cer = sk.kilavuz(girdiler(), "fen-bilimleri", 1, None, SEC)["uniteler"][0]["cerceveler"][0]
    assert cer["duzey"] == 2 and cer["bloklar"][0]["duzey"] == 3
    mat = sk.kilavuz(girdiler(), "matematik", 1, None, SEC)["uniteler"][0]["cerceveler"][0]
    assert mat["duzey"] is None and mat["bloklar"][0]["duzey"] == 2


def test_olasi_kip_senaryo_yok_duyurusu_tek_senaryo_sunmaz():
    """K8: duyuru senaryo vermiyorsa (senaryo_yok, birden çok anılan) hiçbir yerde tek sayı ya da tek senaryo yok."""
    kayit = sinav_kaydi(durum="senaryo_yok", senaryo=None, anilan=[2, 3], konular=("Fiziksel anlamda iş",))
    m = sk.kilavuz(girdiler(sinavlar=[kayit]), "fen-bilimleri", 1, None, SEC)
    assert (m["kip"], m["senaryo"], m["duyurulan"], m["durum"]["senaryo"]) == ("olasi", None, None, None)
    assert m["durum"]["uyari"] == "senaryo_yok"
    assert m["ozet"]["toplam_soru"] is None and m["ozet"]["soru_araligi"] is not None
    assert all(b["soru"] is None and b["aralik"] is not None for b in _bloklar(m).values())
    e = sk.kilavuz(girdiler(sinavlar=[kayit]), "fen-bilimleri", 1, None, {"ebeveyn": True, "isaret": True})["ebeveyn"]
    assert e["toplam_soru"] is None and e["soru_araligi"] == m["ozet"]["soru_araligi"]
    assert m["dogrulama"]["duyurunun_saymadigi"] == []


def test_olasi_kipte_secilen_senaryo_duyurulan_sayilmaz():
    """Duyuru yokken kullanıcının seçtiği senaryo "duyurulan" değildir; yüzey bunu duyurulmuş diye sunmasın."""
    m = sk.kilavuz(girdiler(sinavlar=[]), "fen-bilimleri", 1, 2, SEC)
    assert (m["kip"], m["senaryo"], m["duyurulan"], m["secilen_duyurulan_degil"]) == ("olasi", 2, None, True)
    assert m["ozet"]["toplam_soru"] == 7
    assert sk.kilavuz(girdiler(), "fen-bilimleri", 1, 2, SEC)["secilen_duyurulan_degil"] is False
    assert sk.kilavuz(girdiler(sinavlar=[]), "fen-bilimleri", 1, None, SEC)["secilen_duyurulan_degil"] is False


def test_gecmis_sinav_duyurulan_senaryoyla_acilir():
    """D22: geçmiş sınavın kılavuzu duyurulan senaryoyla (kesin kip) açılır; duyurulmamışsa olası kalır."""
    g = girdiler(bugun=date(2026, 11, 5), sinavlar=[sinav_kaydi(status="past", konular=FEN_KONULARI)])
    m = sk.kilavuz(g, "fen-bilimleri", 1, None, SEC)
    assert (m["kip"], m["senaryo"], m["plan"]) == ("kesin", 2, None)
    g = girdiler(bugun=date(2026, 11, 5), sinavlar=[sinav_kaydi(durum="senaryo_yok", senaryo=None, status="past")])
    assert sk.kilavuz(g, "fen-bilimleri", 1, None, SEC)["kip"] == "olasi"


def test_isaret_sahibi_modelde_tasinir():
    """D16: işaretlerin kime ait olduğu modelde yazılıdır (kâğıtta yazılabilsin); işaret kapalıysa sahip de yoktur."""
    isaretler = {"fen-bilimleri": {"FB.7.2.1": "tekrar"}}
    m = sk.kilavuz(girdiler(isaretler=isaretler, isaret_sahibi="Öğrenci"), "fen-bilimleri", 1, None, SEC)
    assert m["isaret_sahibi"] == "Öğrenci"
    assert sk.kilavuz(girdiler(isaretler=isaretler), "fen-bilimleri", 1, None, SEC)["isaret_sahibi"] is None
    kapali = sk.kilavuz(girdiler(isaretler=isaretler, isaret_sahibi="Öğrenci"), "fen-bilimleri", 1, None,
                        {"ebeveyn": False, "isaret": False})
    assert kapali["isaret_sahibi"] is None
    ayri = sk.kilavuz(girdiler(isaretler=isaretler, isaret_sahibi="Ebeveyn"), "fen-bilimleri", 1, None, SEC)
    assert ayri["icerik_ozeti"] != m["icerik_ozeti"]          # PDF önbelleği sahibe göre ayrılır


def test_gecersiz_isaret_degeri_yok_sayilir():
    g = girdiler(isaretler={"fen-bilimleri": {"FB.7.2.1": "belki", "FB.7.1.1": "tekrar"}}, bugun=date(2026, 10, 30))
    m = sk.kilavuz(g, "fen-bilimleri", 1, None, {"ebeveyn": True, "isaret": True})
    assert _bloklar(m)["FB.7.2.1"]["isaret"] is None and _bloklar(m)["FB.7.1.1"]["isaret"] == "tekrar"
    assert m["ebeveyn"]["tekrar"] == 1 and m["ebeveyn"]["isaretsiz"] == 3


def test_model_json_uyumlu_ve_degismez_girdiyi_bozmaz():
    import json
    g = girdiler()
    once = json.dumps(g.haritalar, sort_keys=True)
    m = sk.kilavuz(g, "fen-bilimleri", 1, None, SEC)
    json.dumps(m)
    assert json.dumps(g.haritalar, sort_keys=True) == once
