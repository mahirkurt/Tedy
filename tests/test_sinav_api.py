"""/api/exams reads output/sinavlar.json (spec §4): status per request on the
Istanbul clock, the new fields, and the fallback to the takvim computation."""
import os
from datetime import datetime

import pytest

os.environ["TEST_AUTH_BYPASS"] = "1"
import src.dashboard_api as api  # noqa: E402
from src.assistant_tools import sinavlar_metni  # noqa: E402
from src.sinav_tespiti import SURUM  # noqa: E402

SIMDI = datetime(2026, 10, 16, 10, 0)


def kayit(**kw):
    k = {"id": "k1", "ders": "Matematik", "tur": "konu_tarama", "baslik": "Matematik KTT", "tarih": "2026-10-20",
         "saat": None, "hafta": None, "konular": ["Mutlak değer"],
         "kaynaklar": [{"tur": "ders_karti", "konum": {"bolum": "ders_icerikleri_haftalar",
                                                        "hafta": "4. Hafta 05 Eki. - 11 Eki.", "ders": "Matematik",
                                                        "sira": 1}, "alinti": "15 EKİM … KTT"}],
         "ilk_tespit": "2026-10-15T09:00:00", "icerik_surumu": "abc", "degisti": None, "sentetik": False,
         "taban": None, "son_yayin": "2026-10-05"}
    k.update(kw)
    return k


# Taken at collection: conftest replaces api._sinavlar_belgesi with "no file" for every test.
GERCEK_BELGE = api._sinavlar_belgesi


def _dosya(monkeypatch, belge, scraped=None):
    from src.sinav_tespiti import gecerli_belge
    monkeypatch.setattr(api, "_sinavlar_belgesi", lambda: gecerli_belge(belge))
    monkeypatch.setattr(api, "_scraped", lambda: scraped if scraped is not None else {"takvim": []})


def _belge(*kayitlar, incelenmedi=0):
    return {"uretildi": "2026-10-16T09:45:00", "surum": SURUM, "sinavlar": list(kayitlar),
            "ozet": {"aday": 1, "incelenen": 1, "incelenmedi": incelenmedi, "butce_usd": 0.0}}


def test_metin_kaydi_examitem_olur(monkeypatch):
    _dosya(monkeypatch, _belge(kayit(), incelenmedi=2))
    sonuc = api._sinav_api_listesi(api._scraped(), SIMDI)
    [e] = sonuc["exams"]
    assert (e["id"], e["course"], e["title"], e["date"], e["allDay"], e["status"]) == \
        ("k1", "Matematik", "Matematik KTT", "2026-10-20", True, "upcoming")
    assert (e["tur"], e["konular"], e["ilkTespit"], e["degisti"], e["hafta"], e["tarihBelirsiz"]) == \
        ("konu_tarama", ["Mutlak değer"], "2026-10-15T09:00:00", None, None, False)
    assert e["kaynaklar"] == [{"tur": "ders_karti", "etiket": "Matematik ders içeriği · 4. Hafta 05 Eki. - 11 Eki.",
                               "alinti": "15 EKİM … KTT",
                               "baglanti": "/dersler?hafta=4.%20Hafta%2005%20Eki.%20-%2011%20Eki."}]
    assert "aiSummary" not in e and "studyGuide" not in e
    assert e["relatedHomework"] == [] and e["relatedContent"] == []
    assert sonuc["tespit"] == {"uretildi": "2026-10-16T09:45:00", "incelenmedi": 2}
    assert sonuc["stats"] == {"upcoming": 1, "past": 0, "averageGrade": None}


@pytest.mark.parametrize("kw,durum", [
    ({"tarih": "2026-10-15"}, "past"),
    ({"tarih": "2026-10-16"}, "upcoming"),
    ({"tarih": "2026-10-16", "saat": "09:00"}, "past"),
    ({"tarih": None, "hafta": "2026-10-12"}, "upcoming"),
    ({"tarih": None, "hafta": "2026-10-05"}, "past"),
    ({"tarih": None}, "upcoming"),
])
def test_durum_istek_aninda(monkeypatch, kw, durum):
    _dosya(monkeypatch, _belge(kayit(**kw)))
    [e] = api._sinav_api_listesi(api._scraped(), SIMDI)["exams"]
    assert e["status"] == durum


def test_tarih_belirsiz_ve_hafta(monkeypatch):
    _dosya(monkeypatch, _belge(kayit(tarih=None, hafta="2026-10-19")))
    [e] = api._sinav_api_listesi(api._scraped(), SIMDI)["exams"]
    assert (e["date"], e["hafta"], e["tarihBelirsiz"]) == (None, "2026-10-19", True)


def test_takvim_tabanli_kayit_tabani_korur(monkeypatch):
    taban = {"id": "gis1", "course": "Özdebir GİS", "title": "Özdebir GİS · İzleme Sınavı", "rawTitle": "GİS-1",
             "courseColor": "#123456", "courseFamily": "teal", "examNumber": 1, "date": "2026-10-23T09:00:00",
             "endDate": "2026-10-23T12:10:00", "allDay": False, "status": "upcoming", "grade": None,
             "relatedHomework": [{"title": "Deneme", "deadline": "", "status": ""}], "relatedContent": []}
    _dosya(monkeypatch, _belge(kayit(id="gis1", taban=taban, tarih="2026-10-23", saat="09:00",
                                     kaynaklar=[{"tur": "takvim", "konum": {"id": "gis1"}, "alinti": "GİS-1"}])))
    [e] = api._sinav_api_listesi(api._scraped(), SIMDI)["exams"]
    assert (e["courseColor"], e["rawTitle"], e["endDate"], e["examNumber"]) == ("#123456", "GİS-1", "2026-10-23T12:10:00", 1)
    assert e["relatedHomework"] == taban["relatedHomework"]
    assert e["kaynaklar"] == [{"tur": "takvim", "etiket": "Okul takvimi", "alinti": "GİS-1", "baglanti": "/takvim"}]


def test_kaynak_baglantilari(monkeypatch):
    kaynaklar = [{"tur": "odev", "konum": {"bolum": "odev", "baslik": "KTT"}, "alinti": "a"},
                 {"tur": "duyuru", "konum": {"bolum": "duyuru", "sira": 0}, "alinti": "b"},
                 {"tur": "ek", "konum": {"bolum": "ek", "id": "abc123"}, "alinti": "c"},
                 {"tur": "not_tablosu", "konum": {"id": "n"}, "alinti": "d"}]
    _dosya(monkeypatch, _belge(kayit(kaynaklar=kaynaklar)))
    [e] = api._sinav_api_listesi(api._scraped(), SIMDI)["exams"]
    assert [(k["etiket"], k["baglanti"]) for k in e["kaynaklar"]] == [
        ("Ödev · KTT", "/isler"), ("Okul duyurusu", "/duyurular"), ("Portal eki", "/api/ekler/abc123"),
        ("Not tablosu", "/notlar")]


def test_bozuk_dosyada_eski_hesaba_duser(monkeypatch):
    from tests.sinav_fikstur import TAKVIM_SINAV
    _dosya(monkeypatch, "bozuk", scraped={"takvim": TAKVIM_SINAV})
    sonuc = api._sinav_api_listesi(api._scraped(), SIMDI)
    assert sonuc["tespit"] is None and len(sonuc["exams"]) == 2
    assert all(e["konular"] == [] and e["kaynaklar"] == [] and e["tarihBelirsiz"] is False for e in sonuc["exams"])


def test_bozuk_dosya_okunurken_500_degil_none(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "OUTPUT_DIR", str(tmp_path))
    assert GERCEK_BELGE() is None                                  # dosya yok
    (tmp_path / "sinavlar.json").write_text("{bozuk", encoding="utf-8")
    assert GERCEK_BELGE() is None                                  # JSONDecodeError yutulur
    (tmp_path / "sinavlar.json").write_text(
        '{"surum": %d, "sinavlar": [], "uretildi": "x", "ozet": {}}' % SURUM, encoding="utf-8")
    assert GERCEK_BELGE()["sinavlar"] == []


def test_eski_surumde_eski_hesaba_duser(monkeypatch):
    from tests.sinav_fikstur import TAKVIM_SINAV
    _dosya(monkeypatch, {**_belge(kayit()), "surum": SURUM + 1}, scraped={"takvim": TAKVIM_SINAV})
    assert api._sinav_api_listesi(api._scraped(), SIMDI)["tespit"] is None


def test_rota_dosyayi_okur(monkeypatch):
    _dosya(monkeypatch, _belge(kayit()))
    api.app.config["TESTING"] = True
    with api.app.test_client() as c:
        veri = c.get("/api/exams").get_json()
    assert veri["exams"][0]["konular"] == ["Mutlak değer"] and "tespit" in veri


def test_asistan_gercek_konulari_yazar():
    e = {"course": "Matematik", "title": "Matematik KTT", "rawTitle": "Matematik KTT", "date": "2026-10-20",
         "allDay": True, "status": "upcoming", "konular": ["Mutlak değer", "Tam sayılar"],
         "kaynaklar": [{"tur": "ders_karti", "etiket": "Matematik ders içeriği · 4. Hafta", "alinti": "KTT konuları",
                        "baglanti": "/dersler"}], "relatedContent": [{"title": "Haftanın kartı"}]}
    metin = sinavlar_metni([e], SIMDI)
    assert "Konular: Mutlak değer; Tam sayılar" in metin
    assert "Haftanın kartı" not in metin
    assert "Kaynak: Matematik ders içeriği · 4. Hafta — “KTT konuları”" in metin


def test_asistan_tarih_belirsiz():
    e = {"course": "İngilizce", "title": "Irregular Verbs Quiz", "rawTitle": "Irregular Verbs Quiz", "date": None,
         "allDay": False, "status": "upcoming", "konular": [], "kaynaklar": [], "hafta": "2026-10-19",
         "tarihBelirsiz": True}
    metin = sinavlar_metni([e], SIMDI)
    assert "tarih belirsiz (19.10 haftası)" in metin and "Konular: yok" in metin


# --- Fix round 1: sinavlar.json is data; nothing in it may turn /api/exams into a 500 ---

def _ders_karti(**konum):
    return {"tur": "ders_karti", "konum": konum, "alinti": "x"}


def test_bozuk_kayitlar_500_vermez(monkeypatch, caplog):
    kotu = [
        kayit(id="b1", tarih="abc"),
        kayit(id="b2", tarih="2026-10-20", saat="9:00"),
        kayit(id="b3", tarih=None, hafta="xx"),
        kayit(id="b4", tarih=None, hafta=5),
        kayit(id="b5", kaynaklar=[_ders_karti(hafta=3, ders="Matematik")]),
        kayit(id="b6", kaynaklar=[_ders_karti(hafta="1. Hafta", ders=5)]),
        kayit(id="b7", konular="metin", kaynaklar=7),
        kayit(id="b8", kaynaklar=[{"tur": "ek", "konum": {"id": 5}, "alinti": 3}]),
        kayit(id="b9", kaynaklar=[{"tur": "patla", "konum": {}, "alinti": "patla"}]),
    ]
    belge = _belge(*kotu, kayit(id="iyi"))
    belge["ozet"]["incelenmedi"] = "x"
    _dosya(monkeypatch, belge)

    gercek = api._sinav_kaynagi

    def _kaynak(k):
        if k.get("alinti") == "patla":
            raise RuntimeError("beklenmedik")
        return gercek(k)
    monkeypatch.setattr(api, "_sinav_kaynagi", _kaynak)
    # The route reads the real clock; "iyi" is dated 2026-10-20, so pin the dashboard's "now" to SIMDI as the
    # rest of this file does — otherwise the test turns red the day after (it did, 2026-10-21).
    gercek_liste = api._sinav_api_listesi
    monkeypatch.setattr(api, "_sinav_api_listesi", lambda data, now=None: gercek_liste(data, now or SIMDI))

    api.app.config["TESTING"] = True
    with caplog.at_level("WARNING"), api.app.test_client() as c:
        yanit = c.get("/api/exams")
    assert yanit.status_code == 200
    veri = yanit.get_json()
    kimlikler = {e["id"]: e for e in veri["exams"]}
    assert "iyi" in kimlikler and kimlikler["iyi"]["status"] == "upcoming"
    assert "b9" not in kimlikler and "b9" in caplog.text           # skipped and logged, not fatal
    assert veri["tespit"]["incelenmedi"] == 0
    for kimlik in ("b1", "b3", "b4"):                              # unreadable day/week = no day/week
        assert (kimlikler[kimlik]["date"], kimlikler[kimlik]["tarihBelirsiz"], kimlikler[kimlik]["status"]) == \
            (None, True, "upcoming")
        assert kimlikler[kimlik]["hafta"] is None
    assert kimlikler["b2"]["date"] == "2026-10-20" and kimlikler["b2"]["allDay"] is True
    assert kimlikler["b7"]["konular"] == [] and kimlikler["b7"]["kaynaklar"] == []


def test_okunamayan_taban_tarihi_tarihsiz_olur(monkeypatch):
    taban = {"id": "t1", "course": "Matematik", "title": "Matematik KTT", "rawTitle": "KTT", "courseColor": "#111",
             "courseFamily": "blue", "examNumber": None, "date": "bozuk", "endDate": "bozuk2", "allDay": False,
             "status": "past", "grade": None, "relatedHomework": [], "relatedContent": []}
    _dosya(monkeypatch, _belge(kayit(id="t1", taban=taban, tarih=None, saat=None,
                                     kaynaklar=[{"tur": "takvim", "konum": {"id": "t1"}, "alinti": "KTT"}])))
    [e] = api._sinav_api_listesi(api._scraped(), SIMDI)["exams"]
    assert (e["status"], e["date"], e["tarihBelirsiz"]) == ("upcoming", None, True)
    assert e["endDate"] is None


def test_gecmis_siralama_haftaya_bakar(monkeypatch):
    _dosya(monkeypatch, _belge(
        kayit(id="a", tarih=None, hafta="2026-09-21"),
        kayit(id="b", tarih="2026-10-01"),
        kayit(id="c", tarih=None, hafta="2026-09-28")))
    sonuc = api._sinav_api_listesi(api._scraped(), SIMDI)["exams"]
    assert [e["id"] for e in sonuc] == ["b", "c", "a"]


def test_asistan_dipnotu_haftali_gecmiste_yok_sentetikte_var():
    haftali = {"course": "Fen", "title": "Fen KTT", "status": "past", "date": None, "hafta": "2026-10-05",
               "tarihBelirsiz": False, "konular": [], "kaynaklar": []}
    sentetik = {"course": "Türkçe", "title": "Türkçe · 1. Sınav", "status": "past", "date": None, "hafta": None,
                "tarihBelirsiz": False, "grade": "80"}
    assert "not tablosundan türetildi" not in sinavlar_metni([haftali], SIMDI)
    assert "not tablosundan türetildi" in sinavlar_metni([haftali, sentetik], SIMDI)


# --- temizlik A (2026-10-17) -------------------------------------------------------

def test_a24_atlanan_kayit_uyarisi_istisnayi_tasir(monkeypatch, caplog):
    _dosya(monkeypatch, _belge(kayit(id="patlak"), kayit(id="iyi")))
    gercek = api._kayittan_sinav

    def _kayit(k, now):
        if k.get("id") == "patlak":
            raise RuntimeError("beklenmedik")
        return gercek(k, now)
    monkeypatch.setattr(api, "_kayittan_sinav", _kayit)
    with caplog.at_level("WARNING"):
        [e] = api._sinav_api_listesi(api._scraped(), SIMDI)["exams"]
    assert e["id"] == "iyi"
    [kayitli] = [r for r in caplog.records if "patlak" in r.getMessage()]
    assert kayitli.exc_info is not None and kayitli.exc_info[0] is RuntimeError


@pytest.mark.parametrize("kw", [{"tarih": "2026-W43-5"}, {"tarih": None, "hafta": "2026-W43-1"},
                                {"tarih": "20261023xx"}])
def test_a24_sinav_gunu_kati_bicim(monkeypatch, kw):
    _dosya(monkeypatch, _belge(kayit(**kw)))
    [e] = api._sinav_api_listesi(api._scraped(), SIMDI)["exams"]
    assert (e["date"], e["hafta"], e["tarihBelirsiz"], e["status"]) == (None, None, True, "upcoming")


def _tabanli(date_, end=None, all_day=False):
    taban = {"id": "t9", "course": "Matematik", "title": "Matematik Yazılı", "rawTitle": "Yazılı",
             "courseColor": "#111", "courseFamily": "blue", "examNumber": None, "date": date_, "endDate": end,
             "allDay": all_day, "status": "upcoming", "grade": None, "relatedHomework": [], "relatedContent": []}
    return kayit(id="t9", taban=taban, tarih=None, saat=None,
                 kaynaklar=[{"tur": "takvim", "konum": {"id": "t9"}, "alinti": "Yazılı"}])


@pytest.mark.parametrize("ham,kanonik", [
    ("2026-10-23T09:00:00", "2026-10-23T09:00:00"),
    ("2026-10-23T09:00", "2026-10-23T09:00:00"),
    ("2026-10-23T09:00:00Z", "2026-10-23T09:00:00"),
    ("2026-10-23T06:00:00+00:00", "2026-10-23T09:00:00"),
    ("2026-10-23T09:00:00.250000", "2026-10-23T09:00:00"),
    ("2026-10-23", "2026-10-23"),
])
def test_a24_taban_tarihi_kanonik_cikar(monkeypatch, ham, kanonik):
    _dosya(monkeypatch, _belge(_tabanli(ham, end=ham)))
    [e] = api._sinav_api_listesi(api._scraped(), SIMDI)["exams"]
    assert (e["date"], e["endDate"], e["status"]) == (kanonik, kanonik, "upcoming")


@pytest.mark.parametrize("ham", ["2026-W43-5", "20261023", "2026-10-23T25:00:00"])
def test_a24_taban_tarihi_kati_degilse_tarihsiz(monkeypatch, ham):
    _dosya(monkeypatch, _belge(_tabanli(ham, end=ham)))
    [e] = api._sinav_api_listesi(api._scraped(), SIMDI)["exams"]
    assert (e["date"], e["endDate"], e["tarihBelirsiz"], e["status"]) == (None, None, True, "upcoming")


# --- temizlik B düzeltme 1: tüm gün takvim sınavı sinavlar.json yolunda da gün sonuna dek yaklaşan ---

def _tum_gun_tabani(tarih):
    from src.sinav_tespiti import _tabandan
    veri = {"takvim": [{"title": "Matematik 1. Yazılı", "start": tarih, "end": "", "allDay": True,
                        "backgroundColor": "", "extendedProps": {}}]}
    [e] = api._sinav_listesi(veri, now=datetime(2026, 10, 1, 9, 0))["exams"]
    k = _tabandan(e)
    k.update({"ilk_tespit": None, "icerik_surumu": "t", "degisti": None})
    return k


@pytest.mark.parametrize("tarih", ["2026-10-20", "2026-10-20T00:00:00"])
@pytest.mark.parametrize("simdi,durum", [
    (datetime(2026, 10, 20, 0, 1), "upcoming"),
    (datetime(2026, 10, 20, 23, 0), "upcoming"),
    (datetime(2026, 10, 21, 0, 1), "past"),
])
def test_b16_tum_gun_takvim_sinavi_dosya_yolunda(monkeypatch, tarih, simdi, durum):
    _dosya(monkeypatch, _belge(_tum_gun_tabani(tarih)))
    [e] = api._sinav_api_listesi(api._scraped(), simdi)["exams"]
    assert e["allDay"] is True and e["status"] == durum


def test_b16_saatli_takvim_sinavi_dosya_yolunda_saatinde_gecer(monkeypatch):
    from src.sinav_tespiti import _tabandan
    veri = {"takvim": [{"title": "Matematik 1. Yazılı", "start": "2026-10-20T09:00:00", "end": "",
                        "allDay": False, "backgroundColor": "", "extendedProps": {}}]}
    [e] = api._sinav_listesi(veri, now=datetime(2026, 10, 1, 9, 0))["exams"]
    k = _tabandan(e)
    k.update({"ilk_tespit": None, "icerik_surumu": "t", "degisti": None})
    _dosya(monkeypatch, _belge(k))
    [e] = api._sinav_api_listesi(api._scraped(), datetime(2026, 10, 20, 9, 30))["exams"]
    assert e["status"] == "past"


def test_b16_tarihli_saatsiz_metin_kaydi_gun_boyu_yaklasan(monkeypatch):
    _dosya(monkeypatch, _belge(kayit()))
    [e] = api._sinav_api_listesi(api._scraped(), datetime(2026, 10, 20, 23, 0))["exams"]
    assert e["status"] == "upcoming"
