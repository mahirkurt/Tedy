"""The portal renews its ticket during a run; the sync must keep the renewed one.

Measured 2026-10-19: `.AUTH` is an ASP.NET forms ticket with a 30-minute
sliding expiry. A request carrying a ticket older than half that is answered
with a new `.AUTH` (probe with the stored cookies at 20.1 min: Set-Cookie
`.AUTH`, value changed; at 5.9 min: none). Only the CAPTCHA login wrote
`output/portal_cookies.json`, so the stored ticket stayed the login's own and
died exactly 30 minutes after it: the cookie file was written at 23:20:10 and
the 23:50:02 run passed the cached-session check, read the year, and found the
login page on the very next page — then lost every section after it. With a
run every 15 minutes that is every third run, about 25 a day since at least
2026-10-05, each one keeping the last reading of all ten portal sections.
"""
import json
import os

import pytest

import src.run_sync as run_sync
from src.session_manager import oturumu_tazele

PROFIL = "https://portal.tedronesans.k12.tr/pages/ogrenci_istekler/p_temel_bilgiler"
GIRIS = "https://portal.tedronesans.k12.tr/login"


def _cerezler(bilet):
    return [
        {"name": "ASP.NET_SessionId", "value": "oturum", "domain": "portal.tedronesans.k12.tr"},
        {"name": ".AUTH", "value": bilet, "domain": "portal.tedronesans.k12.tr"},
    ]


def _yaz(yol, cerezler):
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(cerezler, f)


def _oku(yol):
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


def test_yenilenmis_bilet_diske_yazilir(tmp_path):
    yol = str(tmp_path / "portal_cookies.json")
    _yaz(yol, _cerezler("girisin-bileti"))
    assert oturumu_tazele(_cerezler("yenilenmis-bilet"), PROFIL, yol) is True
    assert _oku(yol) == _cerezler("yenilenmis-bilet")


def test_oturum_dusmusse_eski_kayit_korunur(tmp_path):
    # On the login page the browser holds an anonymous session; writing it would
    # only replace one dead ticket with another, and hide what happened.
    yol = str(tmp_path / "portal_cookies.json")
    _yaz(yol, _cerezler("girisin-bileti"))
    assert oturumu_tazele(_cerezler("anonim"), GIRIS, yol) is False
    assert _oku(yol) == _cerezler("girisin-bileti")


def test_bilet_yoksa_yazilmaz(tmp_path):
    yol = str(tmp_path / "portal_cookies.json")
    _yaz(yol, _cerezler("girisin-bileti"))
    biletsiz = [{"name": "ASP.NET_SessionId", "value": "oturum"}]
    assert oturumu_tazele(biletsiz, PROFIL, yol) is False
    assert oturumu_tazele([], PROFIL, yol) is False
    assert _oku(yol) == _cerezler("girisin-bileti")


class _OturumSurucusu:
    def __init__(self, adres, cerezler):
        self.current_url = adres
        self._cerezler = cerezler

    def get(self, url):
        pass

    def get_cookies(self):
        return self._cerezler

    def quit(self):
        pass


@pytest.fixture
def senkron(tmp_path, monkeypatch):
    """main() against stubs, every write under tmp_path (as in test_year_rollover_sync)."""
    out = str(tmp_path)
    monkeypatch.setattr(run_sync, "OUTPUT_DIR", out)
    monkeypatch.setattr(run_sync, "SYNC_LOCK_PATH", str(tmp_path / ".sync.lock"))
    monkeypatch.setenv("ASSISTANT_AUTO_REINDEX", "0")
    monkeypatch.setattr(run_sync, "perform_incremental_reindex", lambda project_root: {})
    monkeypatch.setattr(run_sync, "login",
                        lambda d: {"method": "cached_session", "captcha_attempts": 0})
    monkeypatch.setattr(run_sync, "run_year_rollover", lambda *a, **kw: {
        "year": None, "status": "unknown", "source": "none", "archived": False, "manifest": None})
    for ad in ("scrape_ogrenci_profili", "scrape_ders_programi", "scrape_odevlerim",
               "scrape_takim_calismalari", "scrape_takvim", "scrape_ders_icerikleri",
               "scrape_ogep", "scrape_gelisim_raporu", "scrape_duyurular", "scrape_ek_sayfalar"):
        monkeypatch.setattr(run_sync, ad, lambda d, *a: {})
    monkeypatch.setattr("src.scrape_englishcentral.scrape", lambda: None)
    monkeypatch.setattr("src.scrape_achieve3000.scrape", lambda: None)
    monkeypatch.setattr("src.scrape_sebit_homework.scrape", lambda: None)
    proje = os.path.join(out, "proje")
    os.makedirs(proje)
    monkeypatch.setattr(run_sync, "PROJECT_ROOT", proje)

    def kos(surucu):
        monkeypatch.setattr(run_sync, "create_driver", lambda: surucu)
        cwd = os.getcwd()
        try:
            run_sync.main()
        finally:
            os.chdir(cwd)

    return out, kos


def test_senkron_sonunda_yenilenmis_bilet_saklanir(senkron):
    out, kos = senkron
    yol = os.path.join(out, "portal_cookies.json")
    _yaz(yol, _cerezler("girisin-bileti"))
    kos(_OturumSurucusu(PROFIL, _cerezler("yenilenmis-bilet")))
    assert _oku(yol) == _cerezler("yenilenmis-bilet")


def test_senkron_oturumu_dusmusse_kayda_dokunmaz(senkron):
    out, kos = senkron
    yol = os.path.join(out, "portal_cookies.json")
    _yaz(yol, _cerezler("girisin-bileti"))
    kos(_OturumSurucusu(GIRIS, _cerezler("anonim")))
    assert _oku(yol) == _cerezler("girisin-bileti")


# Measured 2026-10-19 01:20: the fix above kept the renewed ticket, and the run
# still died. The browser had held two `.AUTH` cookies: the one the server
# renewed (host-only, as the portal sets every cookie) and the one the sync had
# injected — `add_cookie` with a `domain` makes a separate `.portal…` domain
# cookie, which the server's Set-Cookie never overwrites. Both were saved; on
# the next load the file order let the login's own ticket win, and it expired
# exactly 30 minutes after that login.
from src.session_manager import apply_cookies_to_driver, load_cookies  # noqa: E402


def _ciftli():
    return [
        {"name": ".AUTH", "value": "yenilenmis", "domain": "portal.tedronesans.k12.tr", "path": "/"},
        {"name": "ASP.NET_SessionId", "value": "eski-oturum", "domain": ".portal.tedronesans.k12.tr", "path": "/"},
        {"name": "ASP.NET_SessionId", "value": "oturum", "domain": "portal.tedronesans.k12.tr", "path": "/"},
        {"name": ".AUTH", "value": "girisin-bileti", "domain": ".portal.tedronesans.k12.tr", "path": "/"},
    ]


def test_kayitli_cift_bilet_tekillesir_sunucununki_kazanir(tmp_path):
    yol = str(tmp_path / "portal_cookies.json")
    _yaz(yol, _ciftli())
    cerezler = {c["name"]: c["value"] for c in load_cookies(yol)}
    assert len(load_cookies(yol)) == 2
    assert cerezler == {".AUTH": "yenilenmis", "ASP.NET_SessionId": "oturum"}


class _CerezKaydedici:
    def __init__(self):
        self.eklenen = []

    def get(self, url):
        pass

    def add_cookie(self, cerez):
        self.eklenen.append(dict(cerez))

    def refresh(self):
        pass


def test_cerezler_tarayiciya_alan_adi_verilmeden_eklenir():
    # Without a domain the cookie is host-only — the same cookie the server's
    # renewal replaces in place, so the browser never holds two tickets.
    surucu = _CerezKaydedici()
    apply_cookies_to_driver(surucu, _cerezler("bilet"))
    assert surucu.eklenen and all("domain" not in c for c in surucu.eklenen)


def test_tarayiciya_her_addan_tek_cerez_gider():
    surucu = _CerezKaydedici()
    apply_cookies_to_driver(surucu, _ciftli())
    assert {c["name"]: c["value"] for c in surucu.eklenen} == {".AUTH": "yenilenmis", "ASP.NET_SessionId": "oturum"}
    assert len(surucu.eklenen) == 2


def test_tazelenen_kayitta_tek_bilet_kalir(tmp_path):
    yol = str(tmp_path / "portal_cookies.json")
    assert oturumu_tazele(_ciftli(), PROFIL, yol) is True
    assert [c["value"] for c in _oku(yol) if c["name"] == ".AUTH"] == ["yenilenmis"]
