"""Akşam planı motoru: saf yerleştirme (dosya, saat, ağ yok)."""
from datetime import date, datetime

from src.aksam_duzeni import VARSAYILAN
from src.aksam_plani import Blok, plan_kur, planlanacak
from src.odev_tahmini import OdevTahmini


def dt(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M")


def satir(anahtar, ders, baslik, teslim, talimat="", **ek):
    return {"homework_key": anahtar, "Ders Adı": ders, "Ödev Başlığı": baslik,
            "Ödev Son Teslim Tarihi": teslim, "detail": {"description": talimat, "attachments": []},
            "teacher_resolved": False, "student_marked_done": False, **ek}


YARIN, IKI_GUN, BES_GUN = "20.10.2026 23:59", "21.10.2026 23:59", "24.10.2026 23:59"

DORT_ODEV = [
    satir("yarin-zor", "Matematik", "Problemler Çalışma Kâğıdı", YARIN, "Sayfa 42'deki soruları çöz"),
    satir("iki-gun-orta", "Fen Bilimleri", "Hücre Özeti", IKI_GUN),
    satir("yarin-kolay", "İngilizce", "Kelime Listesi", YARIN),
    satir("bes-gun-kolay", "Türkçe", "Kitap Notu", BES_GUN),
]

TAHMINLER = {
    "yarin-zor": OdevTahmini(40, "zor", "Defterini aç ve ilk soruyu oku", ["Soru 1-3", "Soru 4-6"], "model"),
    "iki-gun-orta": OdevTahmini(30, "orta", "Ders kitabını aç", [], "model"),
    "yarin-kolay": OdevTahmini(10, "kolay", "Listeyi oku", [], "model"),
    "bes-gun-kolay": OdevTahmini(10, "kolay", "Notları aç", [], "model"),
}


def T(s):
    return TAHMINLER.get(s["homework_key"], OdevTahmini(30, "orta", "Başla", [], "yedek"))


def kur(simdi="2026-10-19 16:30", satirlar=None, olaylar=None, gunluk=None, okul=True, tatil=False, **kw):
    return plan_kur(DORT_ODEV if satirlar is None else satirlar, T, VARSAYILAN, dt(simdi),
                    olaylar or [], gunluk or {}, okul, tatil, **kw)


def calisma(p):
    return [b for b in p.bloklar if b.tur == "calisma"]


def test_kabul_1_aksam_dizilimi():
    p = plan_kur(DORT_ODEV, T, VARSAYILAN, dt("2026-10-19 16:30"), [], {}, True)
    c = calisma(p)
    assert c[0].bas == 17 * 60 and c[0].odev_anahtari == "yarin-zor"
    assert any(b.tur == "yemek" and b.bas == 18 * 60 + 30 for b in p.bloklar)
    assert sum(1 for b in c if b.bas >= 19 * 60 + 30) <= 1
    assert all(b.bit <= 20 * 60 + 15 for b in c)
    assert p.durum == "onizleme"


def test_bloklar_20_dk_mola_5_ve_10():
    p = kur()
    c = calisma(p)
    assert c[0].bit - c[0].bas == 20 and c[0].tahmin_dk == 20
    molalar = [b for b in p.bloklar if b.tur == "mola"]
    assert molalar[0].bit - molalar[0].bas == 5      # ilk parçadan sonra
    assert molalar[1].bit - molalar[1].bas == 10     # ikinci parçadan sonra
    assert (c[0].parca, c[0].parca_sayisi) == (0, 3)
    assert c[0].adim == "Defterini aç ve ilk soruyu oku"
    assert c[1].adim == "Soru 4-6"                   # parcalar[i] (i >= 1)
    assert c[2].adim == "Kaldığın yerden devam et"


def test_yaptim_planlanacaktan_cikarir():
    satirlar = [{**DORT_ODEV[0], "student_marked_done": True}, DORT_ODEV[1]]
    secilen, disarida = planlanacak(satirlar, date(2026, 10, 19))
    assert [s["homework_key"] for s in secilen] == ["iki-gun-orta"] and disarida == 0
    secilen, _ = planlanacak([{**DORT_ODEV[0], "teacher_resolved": True}], date(2026, 10, 19))
    assert secilen == []


def test_eski_odev_sayilir_ama_planlanmaz():
    eski = satir("eski", "Fen Bilimleri", "Eski", "09.10.2026 23:59")
    cok_uzak = satir("uzak", "Fen Bilimleri", "Uzak", "01.11.2026 23:59")
    secilen, disarida = planlanacak([eski, cok_uzak, DORT_ODEV[0]], date(2026, 10, 19))
    assert [s["homework_key"] for s in secilen] == ["yarin-zor"]
    assert disarida == 1        # 10 gün geçmiş sayılır, 13 gün sonrası ne seçilir ne sayılır
    p = kur(satirlar=[eski, DORT_ODEV[0]])
    assert p.planda_olmayan == 1 and all(b.odev_anahtari != "eski" for b in p.bloklar)


def test_pencere_sinirlari_ve_okunamayan_teslim():
    bugun = date(2026, 10, 19)
    sinir_geri = satir("g3", "Fen Bilimleri", "a", "16.10.2026 10:00")
    sinir_ileri = satir("i7", "Fen Bilimleri", "b", "26.10.2026 10:00")
    bozuk = satir("bozuk", "Fen Bilimleri", "c", "yakında")
    secilen, disarida = planlanacak([sinir_geri, sinir_ileri, bozuk], bugun)
    assert {s["homework_key"] for s in secilen} == {"g3", "i7", "bozuk"} and disarida == 0


def test_okunamayan_teslim_en_sona_ve_en_az_orta():
    bozuk = satir("bozuk", "Türkçe", "Teslimi yok", "")
    TAHMINLER["bozuk"] = OdevTahmini(10, "kolay", "Başla", [], "yedek")
    try:
        p = kur(satirlar=[bozuk, DORT_ODEV[0]])
        c = calisma(p)
        assert c[0].odev_anahtari == "yarin-zor" and c[-1].odev_anahtari == "bozuk"
        assert [b for b in c if b.odev_anahtari == "bozuk"][0].zorluk == "orta"
    finally:
        del TAHMINLER["bozuk"]


def test_sigmayan_uzak_teslim_yarina():
    TAHMINLER["yarin-uzun"] = OdevTahmini(60, "zor", "Başla", [], "model")
    TAHMINLER["uzak-1"] = OdevTahmini(60, "zor", "Başla", [], "model")
    try:
        satirlar = [satir("yarin-uzun", "Matematik", "Büyük", YARIN)] + [
            satir(f"uzak-{i}", "Fen Bilimleri", f"Uzak {i}", BES_GUN) for i in range(1, 6)]
        for i in range(2, 6):
            TAHMINLER[f"uzak-{i}"] = OdevTahmini(60, "zor", "Başla", [], "model")
        p = kur(satirlar=satirlar)
        assert p.tasinan and {t["odev_anahtari"] for t in p.tasinan} <= {f"uzak-{i}" for i in range(1, 6)}
        assert [s["odev_anahtari"] for s in p.sigmayan] == ["yarin-uzun"]
        assert p.sigmayan[0]["kalan_dk"] > 0
    finally:
        for k in [k for k in TAHMINLER if k.startswith(("uzak-", "yarin-uzun"))]:
            del TAHMINLER[k]


def test_takvim_olayi_bloklari_boler():
    olay = (17 * 60 + 30, 18 * 60 + 20, "Özel ders")
    p = kur(olaylar=[olay])
    for b in p.bloklar:
        if b.tur in ("calisma", "mola"):
            assert b.bit <= olay[0] or b.bas >= olay[1], b
    assert any(b.tur == "olay" and b.baslik == "Özel ders" for b in p.bloklar)
    assert calisma(p)  # plan yine de kurulur


def test_ertelenen_bir_kez_sona_gider():
    TAHMINLER["a"] = OdevTahmini(15, "zor", "A'ya başla", [], "model")
    TAHMINLER["b"] = OdevTahmini(15, "orta", "B'ye başla", [], "model")
    try:
        satirlar = [satir("a", "Matematik", "A", YARIN), satir("b", "Fen Bilimleri", "B", YARIN)]
        ilk = kur(satirlar=satirlar)
        assert [b.odev_anahtari for b in calisma(ilk)] == ["a", "b"]
        a_id = calisma(ilk)[0].id
        p = kur(satirlar=satirlar, gunluk={"ertelenen": [a_id]})
        c = calisma(p)
        assert [b.odev_anahtari for b in c] == ["b", "a"]
        assert c[-1].durum == "ertelendi" and c[0].durum == "bekliyor"
    finally:
        del TAHMINLER["a"], TAHMINLER["b"]


def test_suren_blok_korunur_yeniden_dizmede():
    ilk = kur()
    b0 = calisma(ilk)[0]
    gunluk = {b0.id: {"durum": "suruyor", "basla": 17 * 60 + 5}}
    p = kur(simdi="2026-10-19 17:10", gunluk=gunluk)
    s = [b for b in p.bloklar if b.id == b0.id][0]
    assert (s.bas, s.bit, s.durum) == (17 * 60 + 5, 17 * 60 + 25, "suruyor")
    sonraki = [b for b in calisma(p) if b.id != b0.id][0]
    assert sonraki.bas >= s.bit
    assert p.durum == "akis"


def test_biten_blok_aynen_kalir_ve_tekrar_dizilmez():
    ilk = kur()
    b0 = calisma(ilk)[0]
    p = kur(simdi="2026-10-19 17:30",
            gunluk={b0.id: {"durum": "bitti", "basla": "17:02", "bitti": "17:18"}})
    s = [b for b in p.bloklar if b.id == b0.id]
    assert len(s) == 1 and (s[0].bas, s[0].bit, s[0].durum) == (17 * 60 + 2, 17 * 60 + 18, "bitti")
    assert [b for b in calisma(p) if b.durum == "bekliyor" and b.bas < 17 * 60 + 30] == []


def test_ayni_parca_ayni_kimlik():
    a = kur()
    b = kur(simdi="2026-10-19 17:40")
    kimlikler_a = {(x.odev_anahtari, x.parca): x.id for x in calisma(a)}
    kimlikler_b = {(x.odev_anahtari, x.parca): x.id for x in calisma(b)}
    ortak = kimlikler_a.keys() & kimlikler_b.keys()
    assert ortak and all(kimlikler_a[k] == kimlikler_b[k] for k in ortak)
    assert len({x.id for x in a.bloklar}) == len(a.bloklar)
    assert kur().bloklar == a.bloklar


def test_yatma_sonrasi_blok_yok():
    p = kur(simdi="2026-10-19 22:40")
    assert p.durum == "bitti" and p.bloklar == []
    assert kur(simdi="2026-10-19 20:30").durum == "bitti"


def test_aksam_yok_kapali():
    p = kur(gunluk={"aksam_yok": True})
    assert p.durum == "kapali" and p.bloklar == []


def test_tatil_gunu_kapali():
    p = kur(tatil=True)
    assert p.durum == "kapali" and p.bloklar == []


def test_okulsuz_gun():
    p = kur(okul=False)
    assert p.durum == "okulsuz" and p.bloklar == []


def test_gec_baslama_imleci_simdiden():
    p = kur(simdi="2026-10-19 17:40")
    assert calisma(p)[0].bas == 17 * 60 + 40 and p.durum == "akis"


def test_odev_yoksa_plansiz():
    p = kur(satirlar=[])
    assert p.durum == "plansiz" and calisma(p) == []


def test_kalibrasyon_ve_tampon():
    # 40 dk * 1.25 = 50 -> 20+20+10 ; kalibrasyon 2.0 -> 100 dk
    tek = [DORT_ODEV[0]]
    assert sum(b.tahmin_dk for b in calisma(kur(satirlar=tek))) == 50
    p = kur(satirlar=tek, kalibrasyon=lambda ders: 2.0)
    assert sum(b.tahmin_dk for b in calisma(p)) + sum(t.get("kalan_dk", 0) for t in p.sigmayan) == 100


def test_son_parca_en_az_5_dk():
    TAHMINLER["k"] = OdevTahmini(34, "orta", "Başla", [], "model")   # ceil(42.5) = 43 -> 20+23? hayır: 20+20+3 -> 20+23
    try:
        p = kur(satirlar=[satir("k", "Fen Bilimleri", "k", BES_GUN)])
        boyler = [b.tahmin_dk for b in calisma(p)] + [t["kalan_dk"] for t in p.tasinan]
        assert all(d >= 5 for d in boyler)
        assert sum(boyler) == 43
    finally:
        del TAHMINLER["k"]


def test_sinavi_olan_ders_bir_kademe_yukari():
    TAHMINLER["x"] = OdevTahmini(20, "orta", "Başla", [], "model")
    TAHMINLER["y"] = OdevTahmini(20, "orta", "Başla", [], "model")
    try:
        satirlar = [satir("x", "Türkçe", "x", BES_GUN), satir("y", "Fen Bilimleri", "y", BES_GUN)]
        assert calisma(kur(satirlar=satirlar))[0].odev_anahtari == "x"
        p = kur(satirlar=satirlar, sinav_dersleri=frozenset({"Fen Bilimleri"}))
        assert calisma(p)[0].odev_anahtari == "y"
    finally:
        del TAHMINLER["x"], TAHMINLER["y"]


def test_esitlikte_talimatli_once():
    TAHMINLER["x"] = OdevTahmini(20, "orta", "Başla", [], "model")
    TAHMINLER["y"] = OdevTahmini(20, "orta", "Başla", [], "model")
    try:
        satirlar = [satir("x", "Türkçe", "x", BES_GUN), satir("y", "Fen Bilimleri", "y", BES_GUN, "Sayfa 3")]
        assert calisma(kur(satirlar=satirlar))[0].odev_anahtari == "y"
    finally:
        del TAHMINLER["x"], TAHMINLER["y"]


def test_ek_parca_son_parcadan_sonra_gelir():
    TAHMINLER["e"] = OdevTahmini(10, "kolay", "Başla", [], "model")
    try:
        satirlar = [satir("e", "Türkçe", "e", YARIN)]
        p = kur(satirlar=satirlar, gunluk={"ek_parca": {"e": 2}})
        c = calisma(p)
        assert [b.odev_anahtari for b in c] == ["e", "e", "e"]
        assert [b.tahmin_dk for b in c][1:] == [10, 10]
        assert all(b.adim == "Kaldığın yerden devam et" for b in c[1:])
        assert c[0].parca_sayisi == 3
    finally:
        del TAHMINLER["e"]


def test_blok_tipi_alanlari():
    b = calisma(kur())[0]
    assert isinstance(b, Blok) and b.ders == "Matematik" and b.baslik == "Problemler Çalışma Kâğıdı"
    assert b.zorluk == "zor" and b.durum == "bekliyor" and len(b.id) == 10


def _goruntu(b, durum, **ek):
    """Task 5'in yazacağı anlık görüntü: bloğun kendisi + dokunuş zamanları."""
    return {"durum": durum, "odev_anahtari": b.odev_anahtari, "ders": b.ders, "baslik": b.baslik,
            "parca": b.parca, "parca_sayisi": b.parca_sayisi, "tahmin_dk": b.tahmin_dk,
            "zorluk": b.zorluk, "adim": b.adim, "bas": b.bas, "bit": b.bit, **ek}


def test_yaptim_sonrasi_biten_blok_kalir_ve_plansiz_olmaz():
    b0 = calisma(kur())[0]
    gunluk = {b0.id: _goruntu(b0, "bitti", basla=17 * 60 + 2, bitti=17 * 60 + 18, bas=17 * 60 + 2, bit=17 * 60 + 18)}
    biten = {**DORT_ODEV[0], "student_marked_done": True}
    p = kur(simdi="2026-10-19 17:30", satirlar=[biten], gunluk=gunluk)
    s = [b for b in p.bloklar if b.id == b0.id]
    assert len(s) == 1 and (s[0].bas, s[0].bit, s[0].durum) == (17 * 60 + 2, 17 * 60 + 18, "bitti")
    assert s[0].odev_anahtari == "yarin-zor" and s[0].ders == "Matematik" and s[0].parca_sayisi == 3
    assert p.durum == "akis" and p.durum != "plansiz"
    assert [b for b in calisma(p) if b.durum == "bekliyor"] == []


def test_secilmeyen_odevin_suren_blogu_korunur_ve_imleci_ilerletir():
    b0 = calisma(kur())[0]
    gunluk = {b0.id: _goruntu(b0, "suruyor", basla=17 * 60 + 5, bas=17 * 60 + 5, bit=17 * 60 + 25)}
    biten = {**DORT_ODEV[0], "teacher_resolved": True}
    p = kur(simdi="2026-10-19 17:10", satirlar=[biten, DORT_ODEV[1]], gunluk=gunluk)
    s = [b for b in p.bloklar if b.id == b0.id][0]
    assert (s.bas, s.bit, s.durum) == (17 * 60 + 5, 17 * 60 + 25, "suruyor")
    sonraki = [b for b in calisma(p) if b.id != b0.id][0]
    assert sonraki.odev_anahtari == "iki-gun-orta" and sonraki.bas >= 17 * 60 + 30   # bit + 5 dk mola


def test_secili_odevin_goruntulu_parcasi_iki_kez_planlanmaz():
    b0 = calisma(kur())[0]
    gunluk = {b0.id: _goruntu(b0, "bitti", basla=17 * 60 + 2, bitti=17 * 60 + 18, bas=17 * 60 + 2, bit=17 * 60 + 18)}
    p = kur(simdi="2026-10-19 17:30", gunluk=gunluk)
    ilk_parcalar = [b for b in calisma(p) if b.odev_anahtari == "yarin-zor" and b.parca == 0]
    assert len(ilk_parcalar) == 1 and ilk_parcalar[0].durum == "bitti"
    assert len({b.id for b in p.bloklar}) == len(p.bloklar)


def test_biten_bloktan_sonra_mola_kadar_beklenir():
    b0 = calisma(kur())[0]
    gunluk = {b0.id: {"durum": "bitti", "basla": "17:02", "bitti": "17:18"}}
    p = kur(simdi="2026-10-19 17:19", gunluk=gunluk)
    sonraki = [b for b in calisma(p) if b.durum == "bekliyor"][0]
    assert sonraki.bas == 17 * 60 + 23          # 17:18 + 5 dk mola
    mola = [b for b in p.bloklar if b.tur == "mola"][0]
    assert (mola.bas, mola.bit) == (17 * 60 + 18, 17 * 60 + 23)


def test_mola_sabit_blogun_ustune_binmez():
    olay = (17 * 60 + 21, 17 * 60 + 23, "Kısa ziyaret")
    p = kur(olaylar=[olay])
    for b in p.bloklar:
        if b.tur == "mola":
            assert b.bit <= olay[0] or b.bas >= olay[1], b
            assert b.bit <= 18 * 60 + 30 or b.bas >= 19 * 60
    assert [b for b in calisma(p)][1].bas >= 17 * 60 + 25


import pytest


@pytest.mark.parametrize("ad,degisiklik", [
    ("tahmin_yazi", {"tahmin_dk": "abc"}),
    ("tahmin_nan", {"tahmin_dk": float("nan")}),
    ("tahmin_liste", {"tahmin_dk": [20]}),
    ("tahmin_none", {"tahmin_dk": None}),
    ("parca_yazi", {"parca": "x"}),
    ("parca_nan", {"parca": float("nan")}),
    ("sayi_liste", {"parca_sayisi": [3]}),
    ("sayi_none", {"parca_sayisi": None}),
    ("bas_yazi", {"bas": "abc"}),
    ("bas_nan", {"bas": float("nan")}),
    ("bit_none", {"bit": None}),
    ("bit_liste", {"bit": [1, 2]}),
    ("bit_bastan_once", {"bas": 17 * 60 + 20, "bit": 17 * 60}),
])
def test_bozuk_goruntu_plan_kurmayi_dusurmez(ad, degisiklik):
    b0 = calisma(kur())[0]
    kayit = {**_goruntu(b0, "bitti", basla=17 * 60 + 2, bitti=17 * 60 + 18), **degisiklik}
    biten = {**DORT_ODEV[0], "student_marked_done": True}
    p = kur(simdi="2026-10-19 17:30", satirlar=[biten, DORT_ODEV[1]], gunluk={b0.id: kayit})
    assert all(b.bit >= b.bas for b in p.bloklar)
    assert all(b.tahmin_dk >= 0 and b.parca >= 0 and b.parca_sayisi >= 1 for b in calisma(p))


def test_bozuk_ertelenen_ve_ek_parca_dusurmez():
    p = kur(gunluk={"ertelenen": [["x"], 5, None], "ek_parca": {"yarin-zor": "abc"}})
    assert calisma(p)
    assert kur(gunluk={"ertelenen": "yok", "ek_parca": [1]}).bloklar


def test_son_blok_zamana_gore_secilir():
    # ikinci parça (bas 17:30, bit 17:50) ile uzun ilk parça (bas 17:00, bit 18:00): zamanca sonuncu ikincisi
    ilk, ikinci = calisma(kur())[:2]
    gunluk = {ilk.id: _goruntu(ilk, "bitti", bas=17 * 60, bit=18 * 60),
              ikinci.id: _goruntu(ikinci, "bitti", bas=17 * 60 + 30, bit=17 * 60 + 50)}
    p = kur(simdi="2026-10-19 17:51", gunluk=gunluk)
    sonraki = [b for b in calisma(p) if b.durum == "bekliyor"][0]
    assert sonraki.bas == 17 * 60 + 50 + 10     # iki bitmiş blok -> 10 dk mola, son = 17:50


def test_yarina_listesi_odevi_yerlesimden_cikarir_ve_tasinana_yazar():
    p = kur(gunluk={"yarina": ["iki-gun-orta"]})
    assert any(b.odev_anahtari == "iki-gun-orta" for b in calisma(kur())) and all(b.odev_anahtari != "iki-gun-orta" for b in calisma(p))
    assert any(t["odev_anahtari"] == "iki-gun-orta" for t in p.tasinan)


def test_yarina_bozuk_deger_motoru_dusurmez():
    p = kur(gunluk={"yarina": "yok", "one_al": [3, None]})
    assert calisma(p)


def test_one_al_odevi_baslamamis_isin_en_basina_koyar():
    onceki = [b.odev_anahtari for b in calisma(kur())]
    assert onceki[0] != "iki-gun-orta"
    p = kur(gunluk={"one_al": ["iki-gun-orta"]})
    assert calisma(p)[0].odev_anahtari == "iki-gun-orta"


# ── R28 düzeltme turu ────────────────────────────────────────────────────────────

def test_zor_dilime_once_zor_ve_orta_isler_kolay_is_zor_isi_yarina_itmez():
    """§6.3 (R28 küçük 5): zor dilime puan sırasıyla zor/orta işler, kolaylar sonra. Yarın teslim kolay
    iş (puan 3) ile 5 gün sonra teslim zor iş (puan 3) eşit; tarih bağı eskiden kolayı öne alıyordu:
    17:40'ta başlayan akşamda kolay iş 17:40'ı, zor işin ikinci parçası yemeğe çarpıp 19:00'u aşıyor ve
    zor iş yarına taşınıyordu. Şimdi zor iş zor dilime sığar, kolay iş yemekten sonra hafif dilimde."""
    TAHMINLER["z"] = OdevTahmini(32, "zor", "Başla", ["a", "b"], "model")    # 32 × 1,25 = 40 → 20 + 20
    TAHMINLER["k"] = OdevTahmini(10, "kolay", "Listeyi oku", [], "model")    # 13 dk
    try:
        satirlar = [satir("z", "Matematik", "Problemler", BES_GUN), satir("k", "İngilizce", "Kelimeler", YARIN)]
        p = kur(simdi="2026-10-19 17:40", satirlar=satirlar)
        c = calisma(p)
        assert [b.odev_anahtari for b in c] == ["z", "z", "k"]
        assert all(b.bit <= 19 * 60 for b in c if b.odev_anahtari == "z")
        k = c[-1]
        assert k.bas >= 19 * 60 and k.bit <= 19 * 60 + 30                 # yemekten sonra, hafif dilimde
        assert p.tasinan == [] and p.sigmayan == []
    finally:
        del TAHMINLER["z"], TAHMINLER["k"]


def test_kolay_is_zor_dilimdeki_bosluga_yalniz_zor_is_sigmayinca_girer():
    """18:12'de 20 dk'lık orta parça yemekten (18:30) önce sığmaz, yemekten sonra 19:00'u aşar: taşınır.
    Önündeki boşluğa 13 dk'lık kolay iş girer (hiçbir zor/orta parça sığmadığında)."""
    TAHMINLER["o"] = OdevTahmini(16, "orta", "Başla", [], "model")           # 20 dk
    TAHMINLER["k"] = OdevTahmini(10, "kolay", "Listeyi oku", [], "model")    # 13 dk
    try:
        satirlar = [satir("o", "Fen Bilimleri", "Özet", BES_GUN), satir("k", "İngilizce", "Kelimeler", BES_GUN)]
        p = kur(simdi="2026-10-19 18:12", satirlar=satirlar)
        c = calisma(p)
        assert [(b.odev_anahtari, b.bas) for b in c] == [("k", 18 * 60 + 12)]
        assert [t["odev_anahtari"] for t in p.tasinan] == ["o"]
    finally:
        del TAHMINLER["o"], TAHMINLER["k"]


def test_one_alinan_kolay_is_zor_islerden_once_gelir():
    """Aile ya da asistan öne aldıysa (one_al) kolay iş de en başa gelir: aşma, zor dilim kuralından üstündür."""
    p = kur(gunluk={"one_al": ["yarin-kolay"]})
    assert calisma(p)[0].odev_anahtari == "yarin-kolay"


def test_hazirliktan_sonra_suren_ve_biten_bloklar_planda_kalir():
    """R28 küçük 1: 20:30'dan sonra yeni iş yerleşmez, durum "bitti"; ama anlık görüntüsü olan süren ve
    biten bloklar planda kalır (süren blok "Bitti" ile kapanabilsin)."""
    b0, b1 = calisma(kur())[:2]
    gunluk = {b0.id: _goruntu(b0, "bitti", basla="20:00", bitti="20:15", bas=20 * 60, bit=20 * 60 + 15),
              b1.id: _goruntu(b1, "suruyor", basla="20:20", bas=20 * 60 + 20, bit=20 * 60 + 40)}
    p = kur(simdi="2026-10-19 20:35", gunluk=gunluk)
    assert p.durum == "bitti"
    assert [(b.id, b.durum) for b in p.bloklar] == [(b0.id, "bitti"), (b1.id, "suruyor")]
    assert p.tasinan == [] and p.sigmayan == []
    assert kur(simdi="2026-10-19 20:35").bloklar == []               # dokunuş yoksa eskisi gibi boş
