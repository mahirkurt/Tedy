"""EnglishCentral's login: the redirect chain, and whose class gets scraped.

Measured 2026-10-10 with the renewed credentials. After the login form is
submitted the SPA walks three addresses:

    t+0.0s  tr.englishcentral.com/browse/videos
    t+3.6s  www.englishcentral.com/browse/videos?enableInitialSteps=1&setLanguage=en
    t+6.7s  www.englishcentral.com/myclass/239635/0

`ec_login` read `current_url` once after a fixed `time.sleep(5)`, so it saw
the middle hop and reported a failed login — on all 94 consecutive cron runs
in output/sync.log, while the credentials were in fact fine and the progress
file stayed frozen at its 2026-09-02 reading.

The class id in that landing URL is also not the one the scraper asked for:
`EC_CLASS_ID` is unset and the hardcoded fallback 204944 is last year's 6C
class, which now redirects to /dashboard/myfeed where the class video API is
never called — measured 0 video ids against 2 for 239635. So the class is
read from the URL the portal itself lands on.

And a scraper that gives up returns None, which run_sync recorded as nothing
at all: `health.json` said "success": true, "errors": null for five weeks.
"""
import json
import os

import pytest
from selenium.common.exceptions import NoSuchElementException


class _SahteOge:
    """Selenium element stand-in: children keyed by selector, text, clicks."""

    def __init__(self, cocuklar=None, metin=""):
        self._cocuklar = cocuklar or {}
        self.text = metin
        self.tiklandi = False
        self.yazilanlar = []

    def find_element(self, by, secici):
        bulunan = self.find_elements(by, secici)
        if not bulunan:
            raise NoSuchElementException(secici)
        return bulunan[0]

    def find_elements(self, by, secici):
        c = self._cocuklar.get(secici, [])
        return c if isinstance(c, list) else [c]

    def click(self):
        self.tiklandi = True

    def send_keys(self, deger):
        self.yazilanlar.append(deger)


class _SahteSurucu(_SahteOge):
    """Driver stand-in whose current_url walks a measured redirect chain."""

    def __init__(self, url_zinciri, cocuklar=None, cevaplar=None):
        super().__init__(cocuklar if cocuklar is not None else _giris_ogeleri())
        self._zincir = list(url_zinciri)
        self.gidilenler = []
        self.ekran_goruntuleri = []
        self._cevaplar = cevaplar or {}

    @property
    def current_url(self):
        if len(self._zincir) > 1:
            return self._zincir.pop(0)
        return self._zincir[0]

    def get(self, url):
        self.gidilenler.append(url)

    def save_screenshot(self, yol):
        self.ekran_goruntuleri.append(yol)
        return True

    def execute_script(self, *a, **k):
        return self._cevaplar

    def execute_cdp_cmd(self, *a, **k):
        return {}

    def quit(self):
        self.kapandi = True


def _giris_ogeleri():
    modal = _SahteOge({
        "login-username-input-box": _SahteOge(),
        "login-password-input-box": _SahteOge(),
        "button": [_SahteOge(metin=""), _SahteOge(metin="Giriş Yap")],
    })
    return {"sign-in-button": _SahteOge(), "ngb-modal-window": modal}


ARA_ADRES = ("https://www.englishcentral.com/browse/videos"
             "?enableInitialSteps=1&setLanguage=en")
INIS_ADRESI = "https://www.englishcentral.com/myclass/239635/0"


@pytest.fixture
def ec(monkeypatch):
    import src.scrape_englishcentral as ec

    monkeypatch.setattr(ec, "EC_EMAIL", "ogrenci@example.com")
    monkeypatch.setattr(ec, "EC_PASSWORD", "sifre")
    monkeypatch.setattr(ec, "LOGIN_TIMEOUT", 3)
    # the module's own fixed waits (3+2s per login, 8s per class page) are
    # not what these tests measure; WebDriverWait still polls in real time
    monkeypatch.setattr(ec.time, "sleep", lambda *_: None)
    return ec


def test_ec_login_yonlendirme_zinciri_bitene_kadar_bekler(ec):
    """The middle hop is not a failure: wait for the class address."""
    surucu = _SahteSurucu([ARA_ADRES] * 4 + [INIS_ADRESI])

    assert ec.ec_login(surucu) == "239635"
    assert surucu.ekran_goruntuleri == []


def test_ec_login_sinif_kimligini_inis_adresinden_okur(ec):
    """The class id is whatever the portal lands on, not a stored one."""
    surucu = _SahteSurucu(
        ["https://www.englishcentral.com/myclass/987654/0/videos"])

    assert ec.ec_login(surucu) == "987654"


def test_ec_login_sinifa_hic_varmazsa_basarisiz(ec):
    """Never reaching a class is a failed login, with a screenshot."""
    surucu = _SahteSurucu([ARA_ADRES])

    assert ec.ec_login(surucu) is None
    assert surucu.ekran_goruntuleri


def test_scrape_girilen_sinifi_okur_kodda_yazili_olani_degil(ec, tmp_path, monkeypatch):
    """The scrape visits the class the login landed on — 204944 is last
    year's and reads as empty."""
    surucu = _SahteSurucu([ARA_ADRES, INIS_ADRESI], cevaplar={})
    monkeypatch.setattr(ec, "create_driver", lambda: surucu)
    monkeypatch.setattr(ec, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(ec, "PROGRESS_FILE", str(tmp_path / "ec.json"))
    monkeypatch.delenv("EC_CLASS_ID", raising=False)

    sonuc = ec.scrape()

    assert sonuc is not None
    assert any("/myclass/239635/0/videos" in u for u in surucu.gidilenler)
    assert not any("204944" in u for u in surucu.gidilenler)
    assert sonuc["class_id"] == 239635
    kayit = json.loads((tmp_path / "ec.json").read_text())
    assert kayit["class_id"] == 239635


def _sahte_platform(monkeypatch, scrape):
    import sys
    import types

    modul = types.ModuleType("sahte_platform")
    modul.scrape = scrape
    monkeypatch.setitem(sys.modules, "sahte_platform", modul)
    return "sahte_platform"


def test_platform_adimi_veri_gelmemesini_hata_sayar(monkeypatch):
    """A scraper that returns None has failed — health.json must say so."""
    from src.run_sync import _platform_adimi

    hatalar = []
    _platform_adimi("englishcentral", _sahte_platform(monkeypatch, lambda: None), hatalar)

    assert hatalar and hatalar[0].startswith("englishcentral:")


def test_platform_adimi_istisnayi_da_hata_sayar(monkeypatch):
    from src.run_sync import _platform_adimi

    def patlat():
        raise RuntimeError("kapı")

    hatalar = []
    _platform_adimi("achieve3000", _sahte_platform(monkeypatch, patlat), hatalar)

    assert hatalar == ["achieve3000: kapı"]


def test_platform_adimi_ice_aktarma_hatasi_senkronu_dusurmez(monkeypatch):
    """Importing a scraper is that platform's business: these modules import
    Selenium at import time, and the whole sync must not fall with it."""
    from src.run_sync import _platform_adimi

    hatalar = []
    _platform_adimi("englishcentral", "src.boyle_bir_modul_yok", hatalar)

    assert len(hatalar) == 1 and hatalar[0].startswith("englishcentral:")


def test_platform_adimi_veri_gelince_sessiz(monkeypatch):
    from src.run_sync import _platform_adimi

    hatalar = []
    _platform_adimi(
        "englishcentral",
        _sahte_platform(monkeypatch, lambda: {"total_videos": 2}),
        hatalar,
    )

    assert hatalar == []


def _a3k_ogeleri():
    return {
        "login_name1": _SahteOge(),
        "password1": _SahteOge(),
        "loginButton": _SahteOge(),
        "inSchoolFormRadioButton": _SahteOge(),
    }


@pytest.fixture
def a3k(monkeypatch):
    import src.scrape_achieve3000 as a3k

    monkeypatch.setattr(a3k, "A3K_USERNAME", "ogrenci")
    monkeypatch.setattr(a3k, "A3K_PASSWORD", "sifre")
    monkeypatch.setattr(a3k.time, "sleep", lambda *_: None)
    return a3k


def test_a3k_levelset_kapisi_giris_hatasi_degildir(a3k, tmp_path, monkeypatch):
    """The LevelSet gate is a half-finished reading test, not a bad password.

    Measured 2026-10-10 with the renewed credentials: the login completes and
    the portal parks the account on /kb/levelset/welcome ("We need you to
    complete the reading test you started…"), and from there
    /api/v1/student/my-lessons answers 200 with the login page's HTML. The old
    message, "Login may have failed", sent the reader looking at the password.
    """
    monkeypatch.setattr(a3k, "OUTPUT_DIR", str(tmp_path))
    surucu = _SahteSurucu(
        ["https://portal.achieve3000.com/kb/levelset/welcome"], _a3k_ogeleri())

    with pytest.raises(a3k.LevelSetBekliyor) as hata:
        a3k.a3k_login(surucu)

    assert "LevelSet" in str(hata.value)


def test_a3k_ev_sayfasi_basarili_giris(a3k, tmp_path, monkeypatch):
    monkeypatch.setattr(a3k, "OUTPUT_DIR", str(tmp_path))
    surucu = _SahteSurucu(["https://portal.achieve3000.com/home"], _a3k_ogeleri())

    assert a3k.a3k_login(surucu) is True


def test_a3k_baska_bir_adres_hala_basarisiz(a3k, tmp_path, monkeypatch):
    monkeypatch.setattr(a3k, "OUTPUT_DIR", str(tmp_path))
    surucu = _SahteSurucu(["https://portal.achieve3000.com/index"], _a3k_ogeleri())

    assert a3k.a3k_login(surucu) is False
    assert surucu.ekran_goruntuleri


def test_a3k_cli_levelset_durumunu_cumleyle_bildirir(a3k, monkeypatch, capsys):
    """Run by hand, the LevelSet state reads as a sentence, not a traceback."""
    def patlat():
        raise a3k.LevelSetBekliyor("LevelSet okuma testi yarım kalmış")

    monkeypatch.setattr(a3k, "scrape", patlat)

    with pytest.raises(SystemExit) as cikis:
        a3k.main()

    assert cikis.value.code == 1
    assert "LevelSet" in capsys.readouterr().out
