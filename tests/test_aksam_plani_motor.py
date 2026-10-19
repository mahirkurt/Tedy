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
    assert c[2].adim in ("Kaldığın yerden devam et", "Soru 4-6", "Soru 1-3")


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
