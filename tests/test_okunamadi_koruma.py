"""An unread section keeps its last reading; an empty timetable page raises.

Measured 2026-09-23: the 18:30 run read the full week, the 18:45 run landed
on a page with neither the week selector nor a table, returned [] without
complaint, and run_sync wrote `ders_programi: []` over the good reading while
health.json listed the section as fine. Bugün then said there was no
timetable. Two things were wrong: the scraper called the wrong page an empty
one, and the orchestrator let an unread section erase a read one.
"""
import types

import pytest
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

import src.run_sync as run_sync
import src.scrape_all as scrape_all


ONCEKI = {
    "scraped_at": "2026-09-23T18:30:15",
    "ders_programi": [{"week_label": "2. Hafta", "is_current": True,
                       "schedule": {"headers": [], "rows": [["", "PAZARTESI"]]}}],
    "odevlerim": [{"Ders Adı": "Matematik"}],
    "takvim": [],
}


class TestSonOkuma:
    def test_okunan_bolum_onceki_okumayi_korur(self):
        assert run_sync._son_okuma("ders_programi", ONCEKI) == ONCEKI["ders_programi"]
        assert run_sync._son_okuma("odevlerim", ONCEKI) == ONCEKI["odevlerim"]

    def test_onceki_de_bossa_bos_kalir(self):
        # A section that has never been read has nothing to hold on to; the
        # empty shape still has to match what the API expects.
        assert run_sync._son_okuma("takvim", ONCEKI) == []
        assert run_sync._son_okuma("duyurular", ONCEKI) == {}
        assert run_sync._son_okuma("ders_programi", {}) == []

    def test_kayit_ne_zamandan_oldugunu_soyler(self):
        kayit = run_sync._okunamadi_kaydi(
            "ders_programi", RuntimeError("ders programı tablosu sayfada yok"), ONCEKI)
        assert kayit == {"detail": "ders programı tablosu sayfada yok",
                         "son_okuma": "2026-09-23T18:30:15"}

    def test_tutulacak_okuma_yoksa_zaman_da_yok(self):
        # Saying "showing the reading from 18:30" over an empty list would be
        # the same lie in a new coat.
        kayit = run_sync._okunamadi_kaydi("takvim", RuntimeError("x"), ONCEKI)
        assert "son_okuma" not in kayit
        assert run_sync._okunamadi_kaydi("odevlerim", RuntimeError("x"), {}) == {"detail": "x"}


class _YanlisSayfa:
    """A page with no week selector and no table — what 18:45 actually got."""
    current_url = ("https://portal.tedronesans.k12.tr/pages/ogrenci_istekler/"
                   "p_haftalik_ders_hazirlik_programim")

    def __init__(self, tablolar=()):
        self._tablolar = list(tablolar)

    def get(self, url):
        pass

    def find_element(self, by, sel):
        if by == By.TAG_NAME and sel == "body":
            return types.SimpleNamespace(text="")
        raise NoSuchElementException(sel)

    def find_elements(self, by, sel):
        return self._tablolar if (by == By.TAG_NAME and sel == "table") else []

    def save_screenshot(self, path):
        pass


@pytest.fixture(autouse=True)
def _beklemeden(monkeypatch):
    monkeypatch.setattr(scrape_all.time, "sleep", lambda *_: None)


def test_secici_ve_tablo_yoksa_bos_donmez_hata_verir():
    with pytest.raises(RuntimeError, match="tablosu sayfada yok"):
        scrape_all.scrape_ders_programi(_YanlisSayfa())


def test_secici_yok_ama_tablo_varsa_eski_yedek_yol_hala_calisir(monkeypatch):
    # The fallback that reads the open view without a selector predates this
    # and must keep working: the raise is for the page with nothing on it.
    monkeypatch.setattr(scrape_all, "extract_table",
                        lambda d, t: {"headers": [], "rows": [["", "PAZARTESI"]]})
    haftalar = scrape_all.scrape_ders_programi(_YanlisSayfa(tablolar=[object()]))
    assert len(haftalar) == 1
    assert haftalar[0]["is_current"] is True
