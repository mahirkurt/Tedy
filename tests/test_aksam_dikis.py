"""Akşam planı dikişleri (son inceleme, R28): kart (`/api/plan/*`), motor (`bugunku_plan`) ve bildirim turu
(`aksam_bildirim.olaylar`) aynı gün dosyası üzerinde aynı saati söyler.

C1: kartın "…'e kadar başlamazsan ailene haber gider." saati bildirimin "başlamadı" eşiğidir
(`aksam_plani.baslamadi_esigi`) ve şimdiye göre kaymaz; eşikten sonra kart söz vermez.
C2: "Başla" anlık görüntüyü basma anına çapalar (bas = şimdi, bit = şimdi + tahmin); kartın geri sayımı,
motorun dizişi ve bildirimin "süre doldu"su aynı dakikadan sayar.
I1: "mola bitti" planın sıradaki iş için verdiği başlangıçta gider; yemek sürerken gitmez.
Küçük 1: hazırlıktan sonra süren blok planda kalır ve "Bitti" ile kapanır.
Küçük 11: bütün bir akşam dakika dakika uçlardan sürülür ve üç taraf her dakika uyuşur."""
import json
import os
from datetime import datetime, timedelta

import pytest

os.environ.setdefault("TEST_AUTH_BYPASS", "1")
import src.dashboard_api as api  # noqa: E402
from src import aksam_bildirim as ab  # noqa: E402
from src.aksam_duzeni import VARSAYILAN  # noqa: E402
from src.aksam_plani import baslamadi_esigi  # noqa: E402
from tests.test_aksam_plani_api import AILE, OGRENCI, odev, ortam  # noqa: E402,F401  (fikstür)

GUN = datetime(2026, 10, 19)            # Pazartesi, okul günü


def saat(s):
    h, m = (int(x) for x in s.split(":"))
    return GUN.replace(hour=h, minute=m)


def dk(s):
    h, m = (int(x) for x in s.split(":"))
    return h * 60 + m


def duzen_yaz(o, **ek):
    (o.out / "aksam_duzeni.json").write_text(
        json.dumps({**VARSAYILAN, "haber_alacaklar": [AILE], **ek}), encoding="utf-8")


def olaylar(o):
    """Bildirim turunun o dakika gördüğü olaylar: aynı plan kaynağı, aynı gün dosyası, aynı düzen."""
    return ab.olaylar(api.bugunku_plan(o.saat), o.gunluk(), api._aksam_duzeni_oku(), o.saat)


def turler(o):
    return sorted(e.tur for e in olaylar(o))


@pytest.fixture
def aksam(ortam, monkeypatch):
    """Bildirim bayrağı açık, haber alacak aile var, kartı Işık okuyor."""
    monkeypatch.setenv("TEDY_AKSAM_BILDIRIM", "1")
    duzen_yaz(ortam)
    ortam.giris(OGRENCI)
    return ortam


# ── C1: "başlamadı" eşiği tek yerden ─────────────────────────────────────────────────────────

def test_baslamadi_esigi_ilk_bos_dakikadan():
    d = {**VARSAYILAN}
    assert baslamadi_esigi(d, []) == dk("17:15")
    assert baslamadi_esigi({**d, "yemek": "17:00"}, []) == dk("17:45")            # yemek hazır saatini kaplar
    assert baslamadi_esigi(d, [(dk("17:00"), dk("18:00"))]) == dk("18:15")         # özel ders
    assert baslamadi_esigi(d, [(dk("17:00"), dk("18:30"))]) == dk("19:15")         # ders + ardından yemek
    assert baslamadi_esigi(d, [(dk("16:00"), dk("17:10"))]) == dk("17:25")         # hazırdan önce başlayan olay
    assert baslamadi_esigi(d, [(dk("17:30"), dk("18:00"))]) == dk("17:15")         # sonraki olay eşiği itmez
    assert baslamadi_esigi(d, [(dk("16:00"), dk("21:00"))]) is None                # akşamda boş dakika yok
    # Son inceleme: boş aralık eşik kadar uzun olmalı; 10 dakikada başlanmaz, haber yemekte/derste gitmez
    assert baslamadi_esigi({**d, "yemek": "17:10"}, []) == dk("17:55")             # yemek 17:10–17:40
    assert baslamadi_esigi(d, [(dk("17:10"), dk("18:00"))]) == dk("18:15")         # olay 17:10–18:00
    assert baslamadi_esigi({**d, "baslamadi_esik_dk": 30}, []) == dk("17:30")


def test_haber_saati_kaymaz_ve_esikte_susar(aksam):
    """Eskiden kart ilk bloğun öngörülen saatini (şimdiyle kayan) kullanıyordu: 17:15'te aile haber
    almışken 17:40'ta kart hâlâ "17:55'e kadar" diyordu."""
    beklenen = "17:15'e kadar başlamazsan ailene haber gider."
    for s in ("16:30", "17:00", "17:10", "17:14"):
        aksam.saat = saat(s)
        assert aksam.plan()["haber_metni"] == beklenen, s
        assert "baslamadi" not in turler(aksam), s
    for s in ("17:15", "17:40", "18:05"):
        aksam.saat = saat(s)
        assert aksam.plan()["haber_metni"] is None, s
        assert "baslamadi" in turler(aksam), s
    aksam.giris(AILE)
    aksam.saat = saat("17:10")
    assert aksam.plan()["haber_metni"] == "17:15'e kadar başlanmazsa haber gider."


@pytest.mark.parametrize("kaynak", ["takvim", "ozel_ders"])
def test_ozel_ders_esigi_ikisi_icin_de_18_15(aksam, monkeypatch, kaynak):
    """17:00–18:00 bir özel ders (ya da saatli takvim olayı) hazır saatini kaplar: kartın cümlesi ve
    ailenin "başlamadı" haberi ikisi de 18:15. Eskiden kart 18:15, bildirim 17:15 diyordu."""
    if kaynak == "takvim":
        aksam.veri["takvim"] = [{"title": "Piyano", "start": "2026-10-19T17:00:00",
                                 "end": "2026-10-19T18:00:00", "allDay": False}]
    else:
        monkeypatch.setattr(api, "_private_lessons_for_day", lambda gun: [
            {"title": "Özel ders", "start": "2026-10-19T17:00:00", "end": "2026-10-19T18:00:00"}])
    for s in ("16:30", "17:15", "18:14"):
        aksam.saat = saat(s)
        assert aksam.plan()["haber_metni"] == "18:15'e kadar başlamazsan ailene haber gider.", s
        assert "baslamadi" not in turler(aksam), s
    aksam.saat = saat("18:15")
    assert aksam.plan()["haber_metni"] is None
    assert "baslamadi" in turler(aksam)


def test_haber_metni_alicisi_aileden_cikmissa_yok(aksam):
    """Ayardaki adres artık aileden değilse tur kimseye göndermez; kart da haber gideceğini söylemez (D4)."""
    duzen_yaz(aksam, haber_alacaklar=["eski@x.com"])
    aksam.saat = saat("16:30")
    assert aksam.plan()["haber_metni"] is None


# ── C2: Başla anı çapadır ───────────────────────────────────────────────────────────────────

def test_moladan_erken_donus_kart_ve_bildirim_ayni_dakika(aksam):
    """17:21'de moladan erken dönüp Başla: kart 20 dk kaldı der, "süre doldu" 17:41'de gider. Eskiden
    görüntü öngörülen 17:25–17:45'i taşıyordu: kart 17:41'de "4 dk kaldı" derken bildirim gitmişti."""
    aksam.depo.dakika = 16                                         # 16 × 1,25 = 20 dk
    aksam.veri["odevlerim"]["homework"]["rows"].append(odev("Okuma", "Türkçe"))
    aksam.saat = saat("17:00")
    a = aksam.plan()["siradaki"]
    aksam.c.post(f"/api/plan/blok/{a['id']}/basla")
    aksam.saat = saat("17:20")
    b = aksam.c.post(f"/api/plan/blok/{a['id']}/bitti", json={"tamamlandi": True}).get_json()["siradaki"]
    assert b["bas_saat"] == "17:25"
    aksam.saat = saat("17:21")
    sim = aksam.c.post(f"/api/plan/blok/{b['id']}/basla").get_json()["simdiki"]
    assert (sim["bas_saat"], sim["bit_saat"]) == ("17:21", "17:41")
    assert sim["bit"] - dk("17:21") == 20                          # kartın geri sayımı
    # Bu akşamın tamamı: sonraki iş gerçek bitişten (17:41) ve molasından sonra.
    sonraki = aksam.plan()["siradaki"]
    assert sonraki["bas"] >= dk("17:41") + 5
    aksam.saat = saat("17:40")
    assert aksam.plan()["simdiki"]["bit"] - dk("17:40") == 1 and "sure_doldu" not in turler(aksam)
    aksam.saat = saat("17:41")
    assert aksam.plan()["simdiki"]["bit"] - dk("17:41") == 0 and "sure_doldu" in turler(aksam)
    assert "takildi" not in turler(aksam)
    aksam.saat = saat("17:57")
    assert "takildi" in turler(aksam)                              # 17:41 + 15 dk geçti


def test_yemekten_once_basla_kart_motor_ve_bildirim_uyusur(aksam):
    """18:15'te sıradaki iş yemekten sonra (19:00) planlanmış; Işık hemen Başla'ya basar. Kart, motor ve
    bildirim 18:15'ten sayar; sonraki iş gerçek bitişten sonra yemeği atlayıp 19:00'da."""
    aksam.depo.dakika, aksam.depo.zorluk = 16, "kolay"
    aksam.saat = saat("18:15")
    s = aksam.plan()["siradaki"]
    assert s["bas_saat"] == "19:00"                                # 18:15 + 20 dk yemeğe çarpar
    r = aksam.c.post(f"/api/plan/blok/{s['id']}/basla").get_json()
    sim = r["simdiki"]
    assert (sim["bas_saat"], sim["bit_saat"]) == ("18:15", "18:35")
    assert aksam.gunluk()[s["id"]]["bas"] == dk("18:15") and aksam.gunluk()[s["id"]]["bit"] == dk("18:35")
    sonraki = r["siradaki"]
    assert sonraki["bas"] >= dk("19:00")
    for an, kalan, beklenen in (("18:34", 1, []), ("18:35", 0, ["sure_doldu"]),
                                ("18:50", 0, ["sure_doldu"]), ("18:51", 0, ["sure_doldu", "takildi"])):
        aksam.saat = saat(an)
        p = aksam.plan()
        assert max(0, p["simdiki"]["bit"] - dk(an)) == kalan, an       # kartın "kalan"ı (kartDurumu)
        assert [t for t in turler(aksam) if t != "sigmiyor"] == beklenen, an


# ── I1: mola, planın sıradaki başlangıcında biter ───────────────────────────────────────────

def test_mola_bitti_yemek_surerken_gitmez(aksam):
    """18:28'de biten bloktan sonra yemek 18:30–19:00: sıradaki iş 19:00'da. Eskiden "mola bitti" 18:33'te,
    yemeğin ortasında gidiyordu."""
    aksam.depo.dakika, aksam.depo.zorluk = 16, "kolay"
    aksam.saat = saat("18:08")
    a = aksam.plan()["siradaki"]
    aksam.c.post(f"/api/plan/blok/{a['id']}/basla")
    aksam.saat = saat("18:28")
    aksam.c.post(f"/api/plan/blok/{a['id']}/bitti", json={"tamamlandi": True})
    an = saat("18:28")
    while an < saat("19:00"):
        aksam.saat = an
        assert aksam.plan()["siradaki"]["bas_saat"] == "19:00"
        assert "mola_bitti" not in turler(aksam), f"{an:%H:%M}"
        an += timedelta(minutes=1)
    aksam.saat = saat("19:00")
    (m,) = [e for e in olaylar(aksam) if e.tur == "mola_bitti"]
    assert m.blok_id == a["id"] and m.alici == "ogrenci"


# ── Küçük 1: hazırlıktan sonra süren blok ───────────────────────────────────────────────────

def test_hazirliktan_sonra_suren_blok_bitti_ile_kapanir(aksam):
    aksam.depo.dakika, aksam.depo.zorluk = 8, "kolay"             # 10 dk: 19:30'dan sonraki tek kısa iş
    aksam.saat = saat("20:00")
    s = aksam.plan()["siradaki"]
    assert s["bas_saat"] == "20:00"
    aksam.c.post(f"/api/plan/blok/{s['id']}/basla")
    aksam.saat = saat("20:31")
    p = aksam.plan()
    assert p["durum"] == "bitti" and p["simdiki"]["id"] == s["id"] and p["siradaki"] is None
    assert [b["id"] for b in p["bloklar"]] == [s["id"]]
    r = aksam.c.post(f"/api/plan/blok/{s['id']}/bitti")           # son parça: soru sorulur
    assert r.status_code == 400
    r = aksam.c.post(f"/api/plan/blok/{s['id']}/bitti", json={"tamamlandi": True})
    assert r.status_code == 200
    p = r.get_json()
    assert p["simdiki"] is None and [(b["id"], b["durum"]) for b in p["bloklar"]] == [(s["id"], "bitti")]
    marks = json.loads((aksam.out / "homework_student_done.json").read_text())["marks"]
    assert s["odev_anahtari"] in marks


# ── Küçük 11: bütün bir akşam, dakika dakika ────────────────────────────────────────────────

def _uyusur(o):
    """Bir dakikada kart (GET /api/plan/bugun) ile bildirim turunun olayları aynı şeyi söyler."""
    p = o.plan()
    t = turler(o)
    an = o.saat.hour * 60 + o.saat.minute
    calisma = [b for b in p["bloklar"] if b["tur"] == "calisma"]
    basladi = any(b["durum"] in ("suruyor", "bitti") for b in calisma)
    akar = p["durum"] in ("onizleme", "akis") and calisma and not basladi
    # C1: kart söz veriyorsa haber henüz gitmemiştir; eşik geçince söz biter ve haber vadesindedir.
    if akar and an < dk("17:15"):
        assert p["haber_metni"] == "17:15'e kadar başlamazsan ailene haber gider.", an
    else:
        assert p["haber_metni"] is None, an
    assert ("baslamadi" in t) == (p["durum"] == "akis" and bool(calisma) and not basladi and an >= dk("17:15")), an
    # C2: kartın geri sayımı sıfıra indiği dakika "süre doldu"nun dakikasıdır; takıldı eşikten sonra.
    s = p["simdiki"]
    if s:
        assert ("sure_doldu" in t) == (an >= s["bit"]), an
        assert ("takildi" in t) == (an > s["bit"] + 15), an
    else:
        assert "sure_doldu" not in t and "takildi" not in t, an
    # I1: mola, kartın "Planda HH:MM" dediği dakikada biter.
    siradaki = p["siradaki"]
    if not s and siradaki and any(b["durum"] == "bitti" for b in calisma):
        assert ("mola_bitti" in t) == (an >= siradaki["bas"]), an
    else:
        assert "mola_bitti" not in t, an
    return p, t


def test_butun_aksam_kart_motor_ve_bildirim_her_dakika_uyusur(aksam):
    """Matematik 32 dk tahmin → 40 dk, iki parça (20 + 20); "Biraz kaldı" 10 dk'lık ek parça açar.
    16:30 önizleme · 17:10 akış · 17:15 başlamadı · 17:16 Başla · 17:30 Bitti · mola · 17:33 moladan erken
    Başla · 18:09 takıldı · 18:20 son parça "Biraz kaldı" · yemek 18:30–19:00 · 19:00 mola bitti ·
    19:02 ek parça Başla · 19:10 son parça "Evet" (Yaptım) · 19:30'a kadar."""
    aksam.depo.dakika, aksam.depo.zorluk = 32, "kolay"
    aksam.veri["odevlerim"]["homework"]["rows"] = [odev("Problemler")]

    def bas(blok_id):
        r = aksam.c.post(f"/api/plan/blok/{blok_id}/basla")
        assert r.status_code == 200, r.get_json()
        return r.get_json()

    def bitir(blok_id, **govde):
        r = aksam.c.post(f"/api/plan/blok/{blok_id}/bitti", json=govde)
        assert r.status_code == 200, r.get_json()
        return r.get_json()

    dokunuslar = {}
    kimlik = {}

    def p0_basla():
        r = bas(kimlik["p0"])
        assert (r["simdiki"]["bas_saat"], r["simdiki"]["bit_saat"]) == ("17:16", "17:36")

    def p0_bitti():
        r = bitir(kimlik["p0"])                                    # ara parça: soru yok
        assert r["simdiki"] is None and r["siradaki"]["bas_saat"] == "17:35"
        kimlik["p1"] = r["siradaki"]["id"]

    def p1_erken_basla():
        r = bas(kimlik["p1"])                                      # planda 17:35, basılan 17:33
        assert (r["simdiki"]["bas_saat"], r["simdiki"]["bit_saat"]) == ("17:33", "17:53")

    def p1_biraz_kaldi():
        r = bitir(kimlik["p1"], tamamlandi=False)
        e = r["siradaki"]
        assert e["bas_saat"] == "19:00" and e["tahmin_dk"] == 10 and (e["parca"], e["parca_sayisi"]) == (2, 3)
        kimlik["ek"] = e["id"]

    def ek_basla():
        r = bas(kimlik["ek"])
        assert (r["simdiki"]["bas_saat"], r["simdiki"]["bit_saat"]) == ("19:02", "19:12")

    def ek_evet():
        r = bitir(kimlik["ek"], tamamlandi=True)
        assert r["simdiki"] is None and r["siradaki"] is None
        marks = json.loads((aksam.out / "homework_student_done.json").read_text())["marks"]
        assert len(marks) == 1

    dokunuslar.update({"17:16": p0_basla, "17:30": p0_bitti, "17:33": p1_erken_basla,
                       "18:20": p1_biraz_kaldi, "19:02": ek_basla, "19:10": ek_evet})
    beklenen = {                                                   # o dakikanın olayları (dokunuştan sonra)
        "16:30": [], "17:10": [], "17:14": [], "17:15": ["baslamadi"], "17:16": [], "17:35": [],
        "17:53": ["sure_doldu"], "18:08": ["sure_doldu"], "18:09": ["sure_doldu", "takildi"],
        "18:20": [], "18:45": [], "18:59": [], "19:00": ["mola_bitti"], "19:02": [],
        "19:11": [], "19:30": [],
    }
    an = saat("16:30")
    while an <= saat("19:30"):
        aksam.saat = an
        anahtar = f"{an:%H:%M}"
        if anahtar == "16:30":
            p = aksam.plan()
            assert p["durum"] == "onizleme"
            kimlik["p0"] = p["siradaki"]["id"]
        if anahtar in dokunuslar:
            dokunuslar[anahtar]()
        p, t = _uyusur(aksam)
        if anahtar in beklenen:
            assert t == beklenen[anahtar], (anahtar, t)
        if anahtar == "17:31":
            # Mola kartı: sıradaki 17:35'te, kart onu "Planda" diye gösterir; mola bitmedi.
            assert any(b["tur"] == "mola" and b["bas"] <= dk("17:31") < b["bit"] for b in p["bloklar"])
        an += timedelta(minutes=1)
