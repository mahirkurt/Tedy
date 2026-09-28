"""Panonun bilinen dört sorunu (plan docs/superpowers/plans/2026-09-28-pano-eksiklikleri.md).

The assistant's live tools already read the portal's real shapes; the
dashboard's own routes did not. Every fixture here has the real shape of
output/scraped_data.json and invented values — no real names or grades.
"""
import json
import os
import sys
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TEST_AUTH_BYPASS"] = "1"

from src import assistant_tools as at  # noqa: E402
# The portal's weekly grid in its real shape: headers empty, upper-case
# dotless day names in rows[0], Mon–Thu and Fri–Sun as two blocks, each with
# its own time column (Friday's later bell). Invented lessons and teachers.
from tests.test_assistant_ogrenci_araclari import HAFTA, SATIRLAR  # noqa: E402

PAZARTESI = date(2026, 9, 21)


def _kopya(x):
    return json.loads(json.dumps(x))


@pytest.fixture
def api(monkeypatch):
    import src.dashboard_api as api
    monkeypatch.setattr(api, "_load_photo_homework_rows", lambda: [])
    monkeypatch.setattr(api, "_load_private_lessons", lambda: [])
    api.app.config["TESTING"] = True
    return api


def _haftayi_sabitle(api, monkeypatch):
    """Pin the unified calendar's week to Mon 21.09.2026 – Sun 27.09.2026."""
    gunler = [PAZARTESI + timedelta(days=i) for i in range(7)]
    monkeypatch.setattr(api, "_current_week_dates", lambda: gunler)
    return gunler


def _birlesik(api):
    with api.app.test_client() as c:
        return c.get("/api/calendar/unified").get_json()["events"]


# ── 1. Lessons: the real two-block grid ──────────────────────────────────────

def test_birlesik_takvim_gercek_iki_bloklu_tablodan_ders_cizer(api, monkeypatch):
    _haftayi_sabitle(api, monkeypatch)
    monkeypatch.setattr(api, "_scraped", lambda: {"ders_programi": [_kopya(HAFTA)]})
    dersler = [e for e in _birlesik(api) if e["type"] == "lesson"]
    # Before: "Pazartesi" in "PAZARTESI" never matched — zero lessons, always.
    assert dersler
    cuma = [(e["start"], e["end"], e["title"]) for e in dersler if e["start"].startswith("2026-09-25")]
    # Friday reads its own block's bell (09:00, not Monday's 08:55).
    assert cuma == [
        ("2026-09-25T08:00:00", "2026-09-25T08:40:00", "Sosyal Bilgiler"),
        ("2026-09-25T09:00:00", "2026-09-25T09:40:00", "Fen Bilimleri"),
        ("2026-09-25T09:50:00", "2026-09-25T10:30:00", "Matematik"),
    ]
    pazartesi = sorted((e["start"], e["title"], e["subtitle"]) for e in dersler
                       if e["start"].startswith("2026-09-21"))
    assert pazartesi[0] == ("2026-09-21T08:00:00", "Türkçe", "Deneme Öğretmen")
    assert pazartesi[1][:2] == ("2026-09-21T08:55:00", "Fransızca")      # normalised name
    assert not any(e["title"] in ("Kahvaltı", "Öğle yemeği", "Çıkış") for e in dersler)
    assert all(e["courseFamily"] for e in dersler)                        # coloured by course


def test_birlesik_takvim_ders_programi_araciyla_ayni_dersleri_verir(api, monkeypatch):
    gunler = _haftayi_sabitle(api, monkeypatch)
    monkeypatch.setattr(api, "_scraped", lambda: {"ders_programi": [_kopya(HAFTA)]})
    dersler = [e for e in _birlesik(api) if e["type"] == "lesson"]
    for i, gun in enumerate(("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma")):
        tarih = gunler[i].isoformat()
        rota = sorted((e["start"][11:16], e["title"]) for e in dersler if e["start"].startswith(tarih))
        arac = sorted((d["baslangic"], d["ders"]) for d in at.gunun_dersleri(SATIRLAR, gun))
        assert rota == arac, gun


def test_programsiz_birlesik_takvim_ders_uydurmaz(api, monkeypatch):
    _haftayi_sabitle(api, monkeypatch)
    monkeypatch.setattr(api, "_scraped", lambda: {"ders_programi": []})
    assert not [e for e in _birlesik(api) if e["type"] == "lesson"]


# ── 2. Private lessons: the weekend is part of the week ──────────────────────

def _ozel_ders(**kw):
    ders = {"id": "pl1", "course": "Matematik", "teacher": "Deneme Hoca", "is_recurring": True,
            "weekday": "Pazartesi", "date": "", "start_time": "17:00", "end_time": "18:00",
            "active": True}
    ders.update(kw)
    return ders


def test_birlesik_takvim_cumartesi_ve_pazar_ozel_derslerini_verir(api, monkeypatch):
    _haftayi_sabitle(api, monkeypatch)
    monkeypatch.setattr(api, "_scraped", lambda: {})
    monkeypatch.setattr(api, "_load_private_lessons", lambda: [
        _ozel_ders(),
        # Measured 2026-09-25: both of Işık's real private lessons are on Saturday.
        _ozel_ders(id="pl2", course="Fen Bilimleri", weekday="Cumartesi",
                   start_time="12:00", end_time="13:00"),
        _ozel_ders(id="pl3", course="Türkçe", is_recurring=False, weekday="",
                   date="2026-09-27", start_time="10:00", end_time="11:00"),
        # A one-off lesson next Monday is outside this week.
        _ozel_ders(id="pl4", course="İngilizce", is_recurring=False, weekday="",
                   date="2026-09-28", start_time="10:00", end_time="11:00"),
    ])
    ozel = sorted((e["start"], e["course"]) for e in _birlesik(api) if e["type"] == "private_lesson")
    assert ozel == [
        ("2026-09-21T17:00:00", "Matematik"),
        ("2026-09-26T12:00:00", "Fen Bilimleri"),
        ("2026-09-27T10:00:00", "Türkçe"),
    ]


def test_bu_haftanin_tarihleri_pazartesiden_pazara(api):
    gunler = api._current_week_dates()
    assert len(gunler) == 7
    assert gunler[0].weekday() == 0 and gunler[-1].weekday() == 6
    assert all((b - a).days == 1 for a, b in zip(gunler, gunler[1:]))


# ── 4. A report on an earlier school year is not this year's exams ───────────

@pytest.mark.parametrize("donem, yil, beklenen", [
    ("2025-2026 4. Arakarne", "2026-2027", True),
    ("2026-2027 1. Dönem", "2026-2027", False),
    ("2025 - 2026 2. Dönem", "2026-2027", True),
    ("2. Dönem", "2026-2027", False),          # the term names no year
    ("2025-2026 4. Arakarne", None, False),    # the current year is unknown
    ("", "", False),
])
def test_onceki_yil_raporu_mu(donem, yil, beklenen):
    assert at.onceki_yil_raporu_mu(donem, yil) is beklenen


def test_rapor_yili():
    assert at.rapor_yili("2025-2026 4. Arakarne") == "2025-2026"
    assert at.rapor_yili("2. Dönem") is None


def test_guncel_ogretim_yili_dosyadan_okunur(api, monkeypatch):
    monkeypatch.setattr(api, "_load_json",
                        lambda ad: {"year": "2026-2027"} if ad == "academic_year.json" else {})
    assert api._guncel_ogretim_yili() == "2026-2027"
    monkeypatch.setattr(api, "_load_json", lambda ad: {})
    assert api._guncel_ogretim_yili() is None


# ── 8b. The unified calendar reads the week /api/schedule serves ─────────────

from tests.test_assistant_ogrenci_araclari import BASLIK  # noqa: E402


def _baska_hafta(is_current=False):
    """A later week whose Monday starts with Müzik (invented), so reading it
    instead of the current one shows."""
    return {"week_label": "36. Hafta 15 Haz. - 21 Haz.", "week_index": 35, "is_current": is_current,
            "schedule": {"headers": [], "empty_state": False, "rows": [
                BASLIK,
                ["1. Ders\n\n08:00 - 08:40", "Müzik (i-908)\nHayali Müzisyen",
                 "", "", "", "1. Ders\n\n08:00 - 08:40", "", "", ""],
            ]},
            "screenshot": ""}


def test_birlesik_takvim_is_current_haftasini_okur(api, monkeypatch):
    _haftayi_sabitle(api, monkeypatch)
    # The scraper can keep the whole year: the last element is a June week.
    monkeypatch.setattr(api, "_scraped", lambda: {"ders_programi": [_kopya(HAFTA), _baska_hafta()]})
    pazartesi = sorted((e["start"], e["title"]) for e in _birlesik(api)
                       if e["type"] == "lesson" and e["start"].startswith("2026-09-21"))
    assert pazartesi[0] == ("2026-09-21T08:00:00", "Türkçe")
    assert "Müzik" not in [t for s, t in pazartesi if s.endswith("08:00:00")]
    with api.app.test_client() as c:
        latest = c.get("/api/schedule").get_json()["latest"]
    assert latest["week_label"] == HAFTA["week_label"]        # the same week both ways


def test_is_current_yoksa_son_hafta(api):
    eski = dict(_kopya(HAFTA), is_current=False)
    assert api._guncel_hafta([eski, _baska_hafta()])["week_index"] == 35
    assert api._guncel_hafta([eski, _baska_hafta(is_current=False), dict(eski, is_current=True)]) \
        ["week_label"] == HAFTA["week_label"]
    assert api._guncel_hafta([]) == {}
    assert api._guncel_hafta(None) == {}


# ── 8c. Bugün's /api/calendar keeps the weekend's private lessons ────────────

def test_bugun_takvimi_cumartesi_ve_pazar_ozel_derslerini_verir(api, monkeypatch):
    monkeypatch.setattr(api, "_scraped", lambda: {"takvim": []})
    bugun = date.today()
    pazar = bugun + timedelta(days=(6 - bugun.weekday()) or 7)
    monkeypatch.setattr(api, "_load_private_lessons", lambda: [
        _ozel_ders(id="pl2", course="Fen Bilimleri", weekday="Cumartesi",
                   start_time="12:00", end_time="13:00"),
        _ozel_ders(id="pl3", course="Türkçe", is_recurring=False, weekday="",
                   date=pazar.isoformat(), start_time="10:00", end_time="11:00"),
    ])
    with api.app.test_client() as c:
        olaylar = c.get("/api/calendar").get_json()["events"]
    ozel = [e for e in olaylar if e["extendedProps"]["kind"] == "private_lesson"]
    cumartesi = [e for e in ozel if e["extendedProps"]["course"] == "Fen Bilimleri"]
    # Before: _private_lessons_for_day built a Mon–Fri week — zero of these.
    assert cumartesi
    assert all(date.fromisoformat(e["start"][:10]).weekday() == 5 for e in cumartesi)
    assert all(e["start"][11:16] == "12:00" for e in cumartesi)
    assert len({e["start"] for e in cumartesi}) == len(cumartesi)      # each Saturday once
    assert [e["start"][:10] for e in ozel
            if e["extendedProps"]["course"] == "Türkçe"] == [pazar.isoformat()]


# ── 8d. /api/grades says whether its report is last year's ───────────────────

@pytest.mark.parametrize("donem, yil, beklenen", [
    ("2025-2026 4. Arakarne", "2026-2027", True),
    ("2026-2027 1. Dönem", "2026-2027", False),
    ("2025-2026 4. Arakarne", None, False),
])
def test_notlar_rotasi_onceki_yili_bildirir(api, monkeypatch, donem, yil, beklenen):
    rapor = {"semester": donem, "grades": [], "physical": {}, "rubrics": []}
    monkeypatch.setattr(api, "_scraped", lambda: {"gelisim_raporu": dict(rapor)})
    monkeypatch.setattr(api, "_guncel_ogretim_yili", lambda: yil)
    with api.app.test_client() as c:
        yanit = c.get("/api/grades").get_json()
    assert yanit["priorYear"] is beklenen
    assert {k: v for k, v in yanit.items() if k != "priorYear"} == rapor   # the report itself unchanged


def test_notlar_rotasi_sozluk_olmayan_raporu_oldugu_gibi_dondurur(api, monkeypatch):
    """A non-dict gelisim_raporu (portal read failure, or a shape the scraper
    hasn't normalised yet) is served as-is — no priorYear key invented on it,
    and no crash from calling .get() on it."""
    monkeypatch.setattr(api, "_scraped", lambda: {"gelisim_raporu": "invalid"})
    with api.app.test_client() as c:
        yanit = c.get("/api/grades").get_json()
    assert yanit == "invalid"
