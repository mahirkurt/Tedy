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
