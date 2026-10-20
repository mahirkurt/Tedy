"""Akşam planı (Görev 5): gün durumu, çalışma kayıtları, kalibrasyon ve /api/plan/* uçları.

Uçlar oturum + tam rol ister (okuyucu default-deny), bayrak kapalıyken 404 {"kapali": true};
saat `_simdi()` üzerinden gelir, tahmin deposu `_tahmin_deposu()` ile değiştirilir (model yok)."""
import json
import os
from datetime import date, datetime, timedelta

import pytest

os.environ.setdefault("TEST_AUTH_BYPASS", "1")
import src.dashboard_api as api  # noqa: E402
import fnmatch
from src.aksam_plani import Blok, CalismaKayitlari, PlanDeposu, anlik_goruntu, saat_hali  # noqa: E402
from src.odev_tahmini import OdevTahmini  # noqa: E402

AILE = "drmahirkurt@gmail.com"
OGRENCI = "isikkurtx@gmail.com"
OKUYUCU = next(e for e, r in api.USER_ROLES.items() if r == api.ROLE_READER)

SIMDI_1710 = datetime(2026, 10, 19, 17, 10)   # Pazartesi, okul günü, ödeve hazır saatinden sonra
SIMDI_1630 = datetime(2026, 10, 19, 16, 30)

YARIN = "20.10.2026 23:59"


def odev(baslik, ders="Matematik", teslim=YARIN):
    return {"Ders Adı": ders, "Ödev Başlığı": baslik, "Ödev Son Teslim Tarihi": teslim,
            "Ödev Durumu": "", "detail": {"description": "Sayfa 42'deki soruları çöz", "attachments": []}}


def anahtar(ders, baslik, teslim=YARIN):
    return f"{ders.lower()}|{baslik.lower()}|{teslim}"


class SahteDepo:
    """TahminDeposu yerine: sabit dakika, model yok. Okur süresini kaydeder."""

    def __init__(self, dakika=10, zorluk="orta"):
        self.dakika, self.zorluk, self.yazilan = dakika, zorluk, {}

    def tahmin(self, satir, bugun):
        parcalar = ["Soru 1-3", "Soru 4-6"] if self.dakika > 20 else []
        return OdevTahmini(self.dakika, self.zorluk, "Defterini aç ve ilk soruyu oku", parcalar, "model")

    def okur_suresi_yaz(self, k, dakika):
        self.yazilan[k] = dakika


class Ortam:
    def __init__(self, c, out, veri, depo):
        self.c, self.out, self.veri, self.depo = c, out, veri, depo
        self.saat = SIMDI_1710

    def giris(self, email):
        with self.c.session_transaction() as s:
            s["user_email"] = email

    def plan(self):
        return self.c.get("/api/plan/bugun").get_json()

    def calisma(self):
        return [b for b in self.plan()["bloklar"] if b["tur"] == "calisma"]

    def gunluk(self):
        return PlanDeposu(self.out.parent).gunluk(self.saat.date().isoformat())


@pytest.fixture
def ortam(tmp_path, monkeypatch):
    out = tmp_path / "output"
    out.mkdir()
    monkeypatch.setattr(api, "TEST_AUTH_BYPASS", False)
    monkeypatch.setattr(api, "OUTPUT_DIR", str(out))
    monkeypatch.setattr(api, "STUDENT_DONE_FILE", str(out / "homework_student_done.json"))
    monkeypatch.setattr(api, "PHOTO_HOMEWORK_FILE", str(out / "photo_homework.json"))
    monkeypatch.setattr(api, "PRIVATE_LESSON_FILE", str(out / "private_lessons.json"))
    monkeypatch.setattr(api, "_ek_kayitlari", lambda: {})
    monkeypatch.setenv("TEDY_AKSAM_PLANI", "1")
    monkeypatch.delenv("TEDY_AKSAM_BILDIRIM", raising=False)
    veri = {"takvim": [], "ders_programi": [],
            "odevlerim": {"homework": {"rows": [odev("Problemler"), odev("Hücre Özeti", "Fen Bilimleri")]}}}
    monkeypatch.setattr(api, "_scraped", lambda: veri)
    depo = SahteDepo(10)
    monkeypatch.setattr(api, "_tahmin_deposu", lambda: depo)
    api.app.config["TESTING"] = True
    with api.app.test_client() as c:
        o = Ortam(c, out, veri, depo)
        monkeypatch.setattr(api, "_simdi", lambda: o.saat)
        o.giris(AILE)
        yield o


# ── yardımcı birimler ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("saat, beklenen", [
    ("17:15", "17:15'e"), ("17:30", "17:30'a"), ("17:20", "17:20'ye"), ("17:10", "17:10'a"),
    ("17:45", "17:45'e"), ("17:00", "17:00'ye"), ("17:40", "17:40'a"), ("17:50", "17:50'ye"),
    ("17:25", "17:25'e"), ("17:35", "17:35'e"), ("17:05", "17:05'e"), ("17:07", "17:07'ye"),
    ("17:08", "17:08'e"), ("17:09", "17:09'a"), ("17:06", "17:06'ya"), ("17:04", "17:04'e"),
    ("18:00", "18:00'e"), ("20:00", "20:00'ye"), ("19:00", "19:00'a"), ("16:00", "16:00'ya"),
])
def test_saat_hali_son_okunan_sozcuge_gore(saat, beklenen):
    assert saat_hali(saat) == beklenen


def test_kayit_ve_kalibrasyon(tmp_path):
    k = CalismaKayitlari(tmp_path)

    def satir(gun, ders, dk, durum="bitti"):
        return {"gun": gun, "odev_anahtari": f"{ders}-{gun}", "ders": ders, "tahmin_dk": 25, "ham_dk": 20,
                "basla": f"2026-10-{gun}T17:00:00", "bitti": f"2026-10-{gun}T17:{dk:02d}:00", "durum": durum}
    assert k.kalibrasyon("Matematik") == 1.0                      # kayıt yok
    k.ekle(satir("12", "Matematik", 50))
    assert k.kalibrasyon("Matematik") == 1.0                      # 1 kayıt < 3
    k.ekle(satir("13", "Matematik", 50))
    k.ekle(satir("14", "Matematik", 50))
    assert k.kalibrasyon("Matematik") == 2.0                      # gerçek = 2 × (ham × tampon)
    k.ekle(satir("15", "Fen Bilimleri", 59))                      # başka ders etkilemez
    assert k.kalibrasyon("Fen Bilimleri") == 1.0
    k.ekle(satir("16", "Matematik", 5, durum="suruyor"))          # yalnız bitti satırları
    assert k.kalibrasyon("Matematik") == 2.0
    satirlar = (tmp_path / "output/calisma_kayitlari.jsonl").read_text().splitlines()
    assert len(satirlar) == 5 and json.loads(satirlar[0])["ders"] == "Matematik"


def test_kalibrasyon_istenen_surede_biten_is_sabit_noktadir(tmp_path):
    """R28 küçük 7: oran gerçek / (ham × tampon). Çarpan c iken plan ham × c × tampon dakika ister;
    tam o sürede biten iş c'yi kaydeder: çarpan kendini büyütmez (eski gerçek/ham paydası onu her akşam
    %25 artırıyordu: 1,0 → 1,25 → 1,56 …)."""
    for c in (1.0, 1.3, 0.8):
        k = CalismaKayitlari(tmp_path / str(c))
        for i in range(5):
            istenen = 16 * c * 1.25                               # ham 16 dk'nın istenen süresi
            k.ekle({"gun": "g", "odev_anahtari": f"a{i}", "ders": "Matematik", "tahmin_dk": round(istenen),
                    "ham_dk": 16, "basla": "2026-10-12T17:00:00",
                    "bitti": (datetime(2026, 10, 12, 17, 0) + timedelta(minutes=istenen)).isoformat(), "durum": "bitti"})
        assert k.kalibrasyon("Matematik") == pytest.approx(c, abs=1e-6)


def test_kalibrasyon_sinirli_ve_hizli_bitirmeyi_bilir(tmp_path):
    k = CalismaKayitlari(tmp_path)
    for g in range(3):
        k.ekle({"gun": f"2026-10-{g + 10}", "odev_anahtari": f"a{g}", "ders": "Türkçe", "tahmin_dk": 20, "ham_dk": 20,
                "basla": "2026-10-12T17:00:00", "bitti": "2026-10-12T17:02:00", "durum": "bitti"})
    assert k.kalibrasyon("Türkçe") == 0.5                         # 0,1 → 0,5'e kıstırılır
    for g in range(3):
        k.ekle({"gun": "x", "odev_anahtari": f"b{g}", "ders": "Fen Bilimleri", "tahmin_dk": 20, "ham_dk": 20,
                "basla": "2026-10-12T17:00:00", "bitti": "2026-10-12T19:00:00", "durum": "bitti"})
    assert k.kalibrasyon("Fen Bilimleri") == 2.0                  # 6,0 → 2,0
    # bozuk satır turu düşürmez
    (tmp_path / "output/calisma_kayitlari.jsonl").write_text("not json\n", encoding="utf-8")
    assert k.kalibrasyon("Türkçe") == 1.0


def test_kalibrasyon_son_on_kayda_bakar(tmp_path):
    k = CalismaKayitlari(tmp_path)
    for i in range(10):                                           # eskiler 2×
        k.ekle({"gun": "g", "odev_anahtari": f"e{i}", "ders": "Matematik", "tahmin_dk": 20, "ham_dk": 20,
                "basla": "2026-10-12T17:00:00", "bitti": "2026-10-12T17:40:00", "durum": "bitti"})
    for i in range(10):                                           # son 10'u tam istenen süre (20 × 1,25)
        k.ekle({"gun": "g", "odev_anahtari": f"y{i}", "ders": "Matematik", "tahmin_dk": 25, "ham_dk": 20,
                "basla": "2026-10-12T17:00:00", "bitti": "2026-10-12T17:25:00", "durum": "bitti"})
    assert k.kalibrasyon("Matematik") == 1.0


def test_plan_deposu_gunluk_ve_budama(tmp_path):
    d = PlanDeposu(tmp_path)
    assert d.gunluk("2026-10-19") == {}
    sonuc = d.degistir("2026-10-19", lambda g: g.setdefault("ertelenen", []).append("b1"))
    assert sonuc == {"ertelenen": ["b1"]} and d.gunluk("2026-10-19") == {"ertelenen": ["b1"]}
    d.degistir("2026-10-01", lambda g: g.update(aksam_yok=True))
    d.degistir("2026-10-19", lambda g: None)                      # 18 gün eski gün budanır
    ham = json.loads((tmp_path / "output/aksam_plani.json").read_text())
    assert "2026-10-01" not in ham and "2026-10-19" in ham
    d.gunluk("2026-10-19")["ertelenen"].append("sızıntı")          # kopya verir
    assert d.gunluk("2026-10-19") == {"ertelenen": ["b1"]}


def test_plan_deposu_bozuk_dosya_kenara_alinir(tmp_path):
    (tmp_path / "output").mkdir()
    (tmp_path / "output/aksam_plani.json").write_text("{bozuk", encoding="utf-8")
    d = PlanDeposu(tmp_path)
    assert d.gunluk("2026-10-19") == {}
    d.degistir("2026-10-19", lambda g: g.update(aksam_yok=True))
    assert d.gunluk("2026-10-19") == {"aksam_yok": True}
    assert any(p.name.startswith("aksam_plani.json.bozuk") for p in (tmp_path / "output").iterdir())


@pytest.mark.parametrize("bas, bit, gecerli", [(1020, 1040, True), (0, 1440, True), (-1, 10, False),
                                               (1040, 1020, False), (1430, 1441, False)])
def test_anlik_goruntu_sinir_denetimi(bas, bit, gecerli):
    b = Blok("id1", "calisma", bas, bit, "k", "Matematik", "Problemler", "Başla", 0, 2, 20, "zor", "bekliyor")
    g = anlik_goruntu(b)
    if not gecerli:
        assert g is None
    else:
        assert g == {"odev_anahtari": "k", "ders": "Matematik", "baslik": "Problemler", "parca": 0,
                     "parca_sayisi": 2, "tahmin_dk": 20, "ham_dk": 0.0, "zorluk": "zor", "adim": "Başla", "bas": bas, "bit": bit}


# ── uçlar ────────────────────────────────────────────────────────────────────────

def test_bayrak_kapali_404(ortam, monkeypatch):
    monkeypatch.delenv("TEDY_AKSAM_PLANI")
    r = ortam.c.get("/api/plan/bugun")
    assert r.status_code == 404 and r.get_json() == {"kapali": True}
    assert ortam.c.post("/api/plan/aksam-yok", json={"aktif": True}).status_code == 404
    monkeypatch.setenv("TEDY_AKSAM_PLANI", "0")
    assert ortam.c.get("/api/plan/bugun").status_code == 404


@pytest.mark.parametrize("yontem, yol", [
    ("get", "/api/plan/bugun"), ("post", "/api/plan/blok/x/basla"), ("post", "/api/plan/blok/x/bitti"),
    ("post", "/api/plan/blok/x/simdi-degil"), ("put", "/api/plan/odev/k/sure"), ("post", "/api/plan/aksam-yok"),
])
def test_okuyucu_reddedilir(ortam, yontem, yol):
    ortam.giris(OKUYUCU)
    r = getattr(ortam.c, yontem)(yol, json={})
    assert r.status_code == 403
    assert PlanDeposu(ortam.out.parent).gunluk("2026-10-19") == {}


def test_oturumsuz_401(ortam):
    with api.app.test_client() as anonim:
        assert anonim.get("/api/plan/bugun").status_code == 401


def test_get_plan_sekli(ortam):
    p = ortam.plan()
    assert set(p) == {"gun", "durum", "bloklar", "simdiki", "siradaki", "tasinan", "sigmayan",
                      "planda_olmayan", "haber_metni", "aksam_yok"}
    assert p["gun"] == "2026-10-19" and p["durum"] == "akis" and p["simdiki"] is None
    c = [b for b in p["bloklar"] if b["tur"] == "calisma"]
    assert len(c) == 2 and p["siradaki"]["id"] == c[0]["id"]
    assert c[0]["bas_saat"] == "17:10" and c[0]["durum"] == "bekliyor"
    assert p["haber_metni"] is None                                # bildirim bayrağı kapalı


def test_basla_iki_kez_idempotent(ortam):
    ilk = ortam.calisma()[0]
    r1 = ortam.c.post(f"/api/plan/blok/{ilk['id']}/basla")
    assert r1.status_code == 200
    basla = ortam.gunluk()[ilk["id"]]["basla"]
    assert ortam.gunluk()["basladi"] == basla
    ortam.saat = datetime(2026, 10, 19, 17, 20)
    r2 = ortam.c.post(f"/api/plan/blok/{ilk['id']}/basla")
    assert r2.status_code == 200
    g = ortam.gunluk()
    assert g[ilk["id"]]["basla"] == basla and g[ilk["id"]]["durum"] == "suruyor"
    assert [b["durum"] for b in ortam.calisma()].count("suruyor") == 1
    assert r2.get_json()["simdiki"]["id"] == ilk["id"]
    satirlar = (ortam.out / "calisma_kayitlari.jsonl").read_text().splitlines()
    assert len(satirlar) == 1 and json.loads(satirlar[0])["durum"] == "suruyor"


def test_basla_anlik_goruntu_yazar(ortam):
    ilk = ortam.calisma()[0]
    ortam.c.post(f"/api/plan/blok/{ilk['id']}/basla")
    k = ortam.gunluk()[ilk["id"]]
    assert {a: k[a] for a in ("odev_anahtari", "ders", "baslik", "parca", "parca_sayisi", "tahmin_dk",
                              "zorluk", "adim", "bas", "bit")} == {
        "odev_anahtari": ilk["odev_anahtari"], "ders": ilk["ders"], "baslik": ilk["baslik"], "parca": 0,
        "parca_sayisi": 1, "tahmin_dk": ilk["tahmin_dk"], "zorluk": ilk["zorluk"], "adim": ilk["adim"],
        "bas": ilk["bas"], "bit": ilk["bit"]}
    assert 0 <= k["bas"] <= k["bit"] <= 1440


def test_bilinmeyen_blok_404(ortam):
    for yol in ("basla", "bitti", "simdi-degil"):
        r = ortam.c.post(f"/api/plan/blok/yok123/{yol}", json={"tamamlandi": True})
        assert r.status_code == 404 and r.get_json()["error"] == "Bu blok bulunamadı."
    assert ortam.gunluk() == {}


def test_mola_ve_yemek_baslatilamaz(ortam):
    yemek = next(b for b in ortam.plan()["bloklar"] if b["tur"] == "yemek")
    assert ortam.c.post(f"/api/plan/blok/{yemek['id']}/basla").status_code == 404


def test_bitti_tamamlandi_yaptim_yazar(ortam):
    ilk = ortam.calisma()[0]
    ortam.c.post(f"/api/plan/blok/{ilk['id']}/basla")
    ortam.saat = datetime(2026, 10, 19, 17, 25)
    r = ortam.c.post(f"/api/plan/blok/{ilk['id']}/bitti", json={"tamamlandi": True})
    assert r.status_code == 200
    marks = json.loads((ortam.out / "homework_student_done.json").read_text())["marks"]
    assert ilk["odev_anahtari"] in marks
    # Yaptım sonrası bitmiş blok planda yerinde kalır (anlık görüntü), ödev yeniden dizilmez
    kalan = [b for b in ortam.calisma() if b["id"] == ilk["id"]]
    assert kalan and kalan[0]["durum"] == "bitti" and kalan[0]["bit"] == 17 * 60 + 25
    kayit = [json.loads(s) for s in (ortam.out / "calisma_kayitlari.jsonl").read_text().splitlines()]
    assert kayit[-1]["durum"] == "bitti" and kayit[-1]["odev_anahtari"] == ilk["odev_anahtari"]
    # ikinci bitti: yan etki yok
    n = len(kayit)
    assert ortam.c.post(f"/api/plan/blok/{ilk['id']}/bitti", json={"tamamlandi": True}).status_code == 200
    assert len((ortam.out / "calisma_kayitlari.jsonl").read_text().splitlines()) == n


def test_bitti_tamamlanmadi_ek_parca(ortam):
    ilk = ortam.calisma()[0]
    ortam.c.post(f"/api/plan/blok/{ilk['id']}/basla")
    ortam.saat = datetime(2026, 10, 19, 17, 25)
    r = ortam.c.post(f"/api/plan/blok/{ilk['id']}/bitti", json={"tamamlandi": False})
    assert r.status_code == 200
    assert ortam.gunluk()["ek_parca"] == {ilk["odev_anahtari"]: 1}
    assert not (ortam.out / "homework_student_done.json").exists()
    ayni = [b for b in ortam.calisma() if b["odev_anahtari"] == ilk["odev_anahtari"]]
    assert [(b["parca"], b["parca_sayisi"], b["tahmin_dk"]) for b in ayni] == [(0, 2, 13), (1, 2, 10)]
    # tekrar gönderim ek parçayı çoğaltmaz
    ortam.c.post(f"/api/plan/blok/{ilk['id']}/bitti", json={"tamamlandi": False})
    assert ortam.gunluk()["ek_parca"] == {ilk["odev_anahtari"]: 1}


def test_bitti_son_parcada_tamamlandi_zorunlu(ortam):
    ilk = ortam.calisma()[0]
    for govde in (None, {}, {"tamamlandi": "evet"}):
        r = ortam.c.post(f"/api/plan/blok/{ilk['id']}/bitti", **({"json": govde} if govde is not None else {}))
        assert r.status_code == 400 and r.get_json()["error"].endswith(".")
    assert ortam.gunluk() == {}


def test_bitti_ara_parcada_isaret_yazmaz(ortam):
    ortam.depo.dakika = 40                                        # 40×1,25 = 50 → 20+20+10
    ilk, ikinci = ortam.calisma()[0], ortam.calisma()[1]
    assert (ilk["parca"], ilk["parca_sayisi"]) == (0, 3) and ikinci["odev_anahtari"] == ilk["odev_anahtari"]
    r = ortam.c.post(f"/api/plan/blok/{ilk['id']}/bitti", json={"tamamlandi": True})   # ara parçada yok sayılır
    assert r.status_code == 200
    assert not (ortam.out / "homework_student_done.json").exists()
    assert "ek_parca" not in ortam.gunluk()


def test_simdi_degil_ikinci_kez_409(ortam):
    a, b = ortam.calisma()
    r1 = ortam.c.post(f"/api/plan/blok/{a['id']}/simdi-degil")
    assert r1.status_code == 200
    ilk = ortam.calisma()[0]
    assert ilk["odev_anahtari"] == b["odev_anahtari"]              # ertelenen sona gitti
    assert ortam.gunluk()["ertelenen"] == [a["id"]]
    r2 = ortam.c.post(f"/api/plan/blok/{a['id']}/simdi-degil")
    assert r2.status_code == 409 and r2.get_json()["error"] == "Bu bloğu bir kez erteledin."
    assert ortam.gunluk()["ertelenen"] == [a["id"]]


def test_surmekte_blok_ertelenemez(ortam):
    a = ortam.calisma()[0]
    ortam.c.post(f"/api/plan/blok/{a['id']}/basla")
    r = ortam.c.post(f"/api/plan/blok/{a['id']}/simdi-degil")
    assert r.status_code == 409 and "ertelen" in r.get_json()["error"]
    assert "ertelenen" not in ortam.gunluk()


def test_kabul_2_yaptim_yeniden_dizer(ortam):
    a, b = ortam.calisma()
    ortam.c.post(f"/api/plan/blok/{a['id']}/basla")
    onceki = [x for x in ortam.calisma() if x["id"] == a["id"]][0]
    r = ortam.c.post("/api/homework/mark-done", json={"homework_key": b["odev_anahtari"]})
    assert r.status_code == 200
    p = ortam.plan()
    c = [x for x in p["bloklar"] if x["tur"] == "calisma"]
    assert [x["id"] for x in c] == [a["id"]]                       # b yok, süren blok aynı
    assert c[0]["bas"] == onceki["bas"] and c[0]["bit"] == onceki["bit"] and c[0]["durum"] == "suruyor"
    assert p["simdiki"]["id"] == a["id"] and p["siradaki"] is None
    # süren bloğun kendi ödevi de Yaptım olursa blok yine yerinde kalır
    ortam.c.post("/api/homework/mark-done", json={"homework_key": a["odev_anahtari"]})
    c2 = [x for x in ortam.plan()["bloklar"] if x["tur"] == "calisma"]
    assert [x["id"] for x in c2] == [a["id"]] and c2[0]["durum"] == "suruyor"


def test_aksam_yok_ogrenci_403(ortam):
    ortam.giris(OGRENCI)
    r = ortam.c.post("/api/plan/aksam-yok", json={"aktif": True})
    assert r.status_code == 403 and r.get_json()["error"] == "Bunu yalnız aile değiştirebilir."
    assert "aksam_yok" not in ortam.gunluk()


def test_aksam_yok_aile_kapatir_ve_acar(ortam):
    r = ortam.c.post("/api/plan/aksam-yok", json={"aktif": True})
    assert r.status_code == 200 and r.get_json()["durum"] == "kapali"
    assert ortam.plan()["bloklar"] == []
    assert ortam.c.post("/api/plan/aksam-yok", json={"aktif": False}).get_json()["durum"] == "akis"
    assert ortam.c.post("/api/plan/aksam-yok", json={"aktif": "evet"}).status_code == 400


def test_aksam_yok_anahtari_yanitta(ortam):
    # R18: kart anahtarı `durum`dan değil bu alandan okur; tatil `kapali` ama anahtar kapalı.
    assert ortam.plan()["aksam_yok"] is False
    r = ortam.c.post("/api/plan/aksam-yok", json={"aktif": True}).get_json()
    assert r["aksam_yok"] is True and r["durum"] == "kapali"
    assert ortam.plan()["aksam_yok"] is True
    ortam.c.post("/api/plan/aksam-yok", json={"aktif": False})
    ortam.veri["takvim"] = [{"title": "Cumhuriyet Bayramı Tatili", "start": "2026-10-19", "end": "2026-10-20",
                             "allDay": True}]
    p = ortam.plan()
    assert p["durum"] == "kapali" and p["aksam_yok"] is False


def test_takvim_tatili_plani_kapatir(ortam):
    ortam.veri["takvim"] = [{"title": "Cumhuriyet Bayramı Tatili", "start": "2026-10-19", "end": "2026-10-20",
                             "allDay": True}]
    assert ortam.plan()["durum"] == "kapali"
    assert api._tatil_mi(date(2026, 10, 19), ortam.veri["takvim"]) is True
    assert api._tatil_mi(date(2026, 10, 20), ortam.veri["takvim"]) is False   # bitiş dışlayıcı
    assert api._tatil_mi(date(2026, 10, 19), [{"title": "Veli semineri", "start": "2026-10-19", "allDay": True}]) is False
    assert api._tatil_mi(date(2026, 10, 19), [{"title": "Bayram ziyareti", "start": "2026-10-19T19:00:00",
                                                "end": "2026-10-19T20:00:00", "allDay": False}]) is False


def test_okulsuz_gun_plan_yok(ortam):
    ortam.saat = datetime(2026, 10, 24, 17, 10)                    # Cumartesi, programsız → Pzt–Cum
    assert ortam.plan()["durum"] == "okulsuz"


def test_olaylar_yemegin_ustune_binmez(ortam):
    ortam.veri["takvim"] = [{"title": "Futbol", "start": "2026-10-19T17:10:00+03:00",
                             "end": "2026-10-19T18:00:00+03:00", "allDay": False},
                            {"title": "Okul gezisi", "start": "2026-10-19", "end": "2026-10-20", "allDay": True}]
    p = ortam.plan()
    olay = [b for b in p["bloklar"] if b["tur"] == "olay"]
    assert [(b["baslik"], b["bas"], b["bit"]) for b in olay] == [("Futbol", 17 * 60 + 10, 18 * 60)]
    assert min(b["bas"] for b in p["bloklar"] if b["tur"] == "calisma") >= 18 * 60


def test_sinav_dersi_one_alinir(ortam, monkeypatch):
    gorulen = {}
    gercek = api.plan_kur

    def gozle(*a, **k):
        gorulen.update(k)
        return gercek(*a, **k)
    monkeypatch.setattr(api, "plan_kur", gozle)
    monkeypatch.setattr(api, "_sinav_api_listesi", lambda data, now=None: {"exams": [
        {"course": "Fen Bilimleri", "date": "2026-10-23T09:00:00", "status": "upcoming"},
        {"course": "Türkçe", "date": "2026-11-20", "status": "upcoming"},
        {"course": "Matematik", "date": "2026-10-10", "status": "past"}]})
    ortam.plan()
    assert gorulen["sinav_dersleri"] == frozenset({"Fen Bilimleri"})
    assert callable(gorulen["kalibrasyon"])


def test_haber_metni_kosullari(ortam, monkeypatch):
    (ortam.out / "aksam_duzeni.json").write_text(json.dumps({"haber_alacaklar": [AILE]}), encoding="utf-8")
    ortam.saat = SIMDI_1630
    assert ortam.plan()["haber_metni"] is None                     # bildirim bayrağı yok
    monkeypatch.setenv("TEDY_AKSAM_BILDIRIM", "1")
    p = ortam.plan()
    # Aile okurken kişisiz cümle; Işık okurken "sen" (R19).
    assert p["durum"] == "onizleme" and p["haber_metni"] == "17:15'e kadar başlanmazsa haber gider."
    ortam.giris(OGRENCI)
    assert ortam.plan()["haber_metni"] == "17:15'e kadar başlamazsan ailene haber gider."
    ortam.giris(AILE)
    (ortam.out / "aksam_duzeni.json").write_text(json.dumps({"haber_alacaklar": []}), encoding="utf-8")
    assert ortam.plan()["haber_metni"] is None                     # alıcı yok
    (ortam.out / "aksam_duzeni.json").write_text(json.dumps({"haber_alacaklar": [AILE]}), encoding="utf-8")
    ilk = ortam.calisma()[0]
    ortam.c.post(f"/api/plan/blok/{ilk['id']}/basla")
    assert ortam.plan()["haber_metni"] is None                     # ilk blok başladı
    ortam.c.post("/api/plan/aksam-yok", json={"aktif": True})
    assert ortam.plan()["haber_metni"] is None                     # plan kapalı


def test_sure_yaz_ve_dogrula(ortam):
    k = ortam.calisma()[0]["odev_anahtari"]
    r = ortam.c.put(f"/api/plan/odev/{k}/sure", json={"dakika": 45})
    assert r.status_code == 200 and ortam.depo.yazilan == {k: 45}
    for kotu in (4, 121, "45", True, None, 4.5):
        r = ortam.c.put(f"/api/plan/odev/{k}/sure", json={"dakika": kotu})
        assert r.status_code == 400 and r.get_json()["error"] == "Süre 5 ile 120 dakika arasında olmalı."
    assert ortam.depo.yazilan == {k: 45}
    r = ortam.c.put("/api/plan/odev/yok|yok|yok/sure", json={"dakika": 30})
    assert r.status_code == 404 and r.get_json()["error"] == "Ödev bulunamadı."


def test_bozuk_anlik_goruntu_plani_dusurmez(ortam):
    PlanDeposu(ortam.out.parent).degistir("2026-10-19", lambda g: g.update(
        {"bozuk": {"durum": "suruyor", "odev_anahtari": "x", "bas": "yok", "bit": None}}))
    assert ortam.c.get("/api/plan/bugun").status_code == 200


# ── düzeltme turu 1 ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("carpan", [1.0, 1.6])
@pytest.mark.parametrize("dakika", [7, 8, 13, 25])
def test_ham_pay_kalibrasyondan_bagimsiz_ve_kalibrasyon_oranini_verir(tmp_path, dakika, carpan):
    """R12: normal parçaların ham payları toplamı tahmindir, çarpan ne olursa olsun; kayıtlardan
    kalibrasyon gerçek / (ham × tampon) oranını verir (R28); ek parça ölçüme girmez."""
    from datetime import timedelta
    from src.aksam_duzeni import VARSAYILAN
    from src.aksam_plani import plan_kur
    satir = {"homework_key": "k", "Ders Adı": "Matematik", "Ödev Başlığı": "P", "Ödev Son Teslim Tarihi": YARIN,
             "detail": {"description": "x", "attachments": []}, "teacher_resolved": False,
             "student_marked_done": False}
    tahmin = lambda s: OdevTahmini(dakika, "orta", "Başla", ["a", "b"], "model")  # noqa: E731
    p = plan_kur([satir], tahmin, VARSAYILAN, SIMDI_1630, [], {"ek_parca": {"k": 2}}, True,
                 kalibrasyon=lambda d: carpan)
    parcalar = [b for b in p.bloklar if b.tur == "calisma"]
    normal, ek = parcalar[:-2], parcalar[-2:]
    assert sum(b.ham_dk for b in normal) == pytest.approx(dakika, abs=1e-6)
    assert [b.ham_dk for b in ek] == [0.0, 0.0]
    k = CalismaKayitlari(tmp_path)
    basla = datetime(2026, 10, 19, 17, 0)
    for b in parcalar:                                            # her parça ham × tampon payının 1,5 katı sürdü
        for _ in range(3):
            k.ekle({"gun": "g", "odev_anahtari": "k", "ders": "Matematik", "tahmin_dk": b.tahmin_dk,
                    "ham_dk": b.ham_dk, "basla": basla.isoformat(),
                    "bitti": (basla + timedelta(seconds=90 * 1.25 * b.ham_dk + 900 * (b.ham_dk == 0))).isoformat(),
                    "durum": "bitti"})
    assert k.kalibrasyon("Matematik") == pytest.approx(1.5, abs=1e-6)


def test_ham_pay_sureyle_ayni_gerceginde_ayni_oran(tmp_path):
    """Aynı gerçek süre, 1,0 ve 1,6 çarpanıyla aynı oranı kaydeder (tek parçalı 8 dk)."""
    from src.aksam_duzeni import VARSAYILAN
    from src.aksam_plani import plan_kur
    satir = {"homework_key": "k", "Ders Adı": "Matematik", "Ödev Başlığı": "P", "Ödev Son Teslim Tarihi": YARIN,
             "detail": {"description": "x", "attachments": []}, "teacher_resolved": False,
             "student_marked_done": False}
    ham = []
    for c in (1.0, 1.6):
        p = plan_kur([satir], lambda s: OdevTahmini(8, "orta", "Başla", [], "model"), VARSAYILAN, SIMDI_1630,
                     [], {}, True, kalibrasyon=lambda d, c=c: c)
        [b] = [x for x in p.bloklar if x.tur == "calisma"]
        ham.append(b.ham_dk)
    assert ham[0] == pytest.approx(ham[1], abs=1e-9) == pytest.approx(8.0)


def test_kayit_ham_pay_api_ucunda(ortam):
    ortam.depo.dakika = 8
    ilk = ortam.calisma()[0]
    ortam.c.post(f"/api/plan/blok/{ilk['id']}/basla")
    ortam.saat = datetime(2026, 10, 19, 17, 22)
    ortam.c.post(f"/api/plan/blok/{ilk['id']}/bitti", json={"tamamlandi": False})
    satir = json.loads((ortam.out / "calisma_kayitlari.jsonl").read_text().splitlines()[-1])
    assert satir["tahmin_dk"] == 10 and satir["ham_dk"] == pytest.approx(8.0)


def test_listeden_dusen_suren_blok_simdiki_olur_ve_bitirilebilir(ortam):
    a, b = ortam.calisma()
    ortam.c.post(f"/api/plan/blok/{a['id']}/basla")
    ortam.veri["odevlerim"]["homework"]["rows"] = [r for r in ortam.veri["odevlerim"]["homework"]["rows"]
                                                   if a["baslik"] != r["Ödev Başlığı"]]
    p = ortam.plan()
    assert p["simdiki"]["id"] == a["id"] and p["simdiki"]["durum"] == "suruyor"
    r = ortam.c.post(f"/api/plan/blok/{a['id']}/bitti", json={"tamamlandi": True})
    assert r.status_code == 200 and ortam.plan()["simdiki"] is None
    assert ortam.c.post(f"/api/plan/blok/{b['id']}/basla").status_code == 200


def test_baslamadan_bitti_kalibrasyona_girmez(ortam):
    ilk = ortam.calisma()[0]
    r = ortam.c.post(f"/api/plan/blok/{ilk['id']}/bitti", json={"tamamlandi": False})
    assert r.status_code == 200
    satir = json.loads((ortam.out / "calisma_kayitlari.jsonl").read_text().splitlines()[-1])
    assert satir["durum"] == "bitti" and satir["basla"] is None
    assert "basladi" not in ortam.gunluk()
    k = CalismaKayitlari(ortam.out.parent)
    for _ in range(2):
        k.ekle(satir)
    assert k.kalibrasyon(satir["ders"]) == 1.0                # 3 başlatılmamış kayıt 0,5'e çekmez


def test_basla_baska_blok_surerken_409(ortam):
    a, b = ortam.calisma()
    ortam.c.post(f"/api/plan/blok/{a['id']}/basla")
    r = ortam.c.post(f"/api/plan/blok/{b['id']}/basla")
    assert r.status_code == 409 and r.get_json()["error"] == "Önce süren bloğu bitir."
    assert ortam.gunluk().get(b["id"]) is None
    assert ortam.c.post(f"/api/plan/blok/{a['id']}/basla").status_code == 200   # aynı blok: idempotent


def test_yeni_dosyalar_bm25_disinda():
    from src.assistant_core import DEFAULT_EXCLUDED_FILE_PATTERNS as P
    for ad in ("aksam_plani.json", "aksam_plani.json.bozuk-20261019170000", "aksam_plani.json.lock",
               "calisma_kayitlari.jsonl", "calisma_kayitlari.jsonl.lock"):
        assert any(fnmatch.fnmatch(ad, d) for d in P), ad


def test_api_anahtari_plan_post_403(ortam, monkeypatch):
    monkeypatch.setattr(api, "_validate_api_key", lambda k: "etiket")
    with api.app.test_client() as anahtarli:
        r = anahtarli.post("/api/plan/aksam-yok", json={"aktif": True},
                           headers={"Authorization": "Bearer tdyK_x"})
        assert r.status_code == 403
        assert anahtarli.get("/api/plan/bugun", headers={"Authorization": "Bearer tdyK_x"}).status_code == 403
    assert "aksam_yok" not in ortam.gunluk()


def test_aksam_ozel_dersi_engel_olur():
    ev = [{"start": "2026-10-19T18:00:00", "end": "2026-10-19T19:00:00", "title": "Özel ders"},
          {"start": "2026-10-19T10:00:00", "end": "2026-10-19T11:00:00", "title": "Sabah dersi"},
          {"start": "2026-10-20T18:00:00", "end": "2026-10-20T19:00:00", "title": "Yarın"}]
    o = api._plan_olaylari({"takvim": []}, date(2026, 10, 19), ev, 17 * 60, 21 * 60)
    assert o == [(18 * 60, 19 * 60, "Özel ders")]


def test_kartin_ret_listesi_arka_ucun_cumleleriyle_ayni():
    # The card shows a refusal only when it is on BILINEN_RETLER (D3, D4). Pinned to the plan routes'
    # own sentences: a reworded route sentence must not silently fall back to "Kaydedilemedi".
    from pathlib import Path
    import re
    kok = Path(__file__).resolve().parents[1]
    ts = (kok / "dashboard" / "src" / "utils" / "aksamPlani.ts").read_text(encoding="utf-8")
    blok = re.search(r"const BILINEN_RETLER[^{]*\{(.*?)\n\}", ts, re.S)
    assert blok, "BILINEN_RETLER bulunamadı"
    satirlar = dict(re.findall(r"(\d{3}):\s*\[([^\]]*)\]", blok.group(1)))
    assert set(satirlar) == {"409", "403"}
    py = (kok / "src" / "dashboard_api.py").read_text(encoding="utf-8")
    for durum, liste in satirlar.items():
        cumleler = re.findall(r"'([^']+)'", liste)
        assert cumleler, durum
        for c in cumleler:
            assert re.search(r'jsonify\(\{"error": "' + re.escape(c) + r'"\}\), ' + durum, py), (durum, c)
