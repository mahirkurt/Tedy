"""Rollover archives the old year before any new-year data is written."""
import json
import os

import pytest

import src.run_sync as run_sync
from src.run_sync import run_year_rollover


@pytest.fixture(autouse=True)
def _kendi_kilidi(tmp_path, monkeypatch):
    """Keep these tests off the machine's live sync lock.

    `main()` now refuses to start while another sync holds
    `output/.sync.lock`, so a cron run firing mid-suite made
    test_archive_failure_in_main_does_not_abort_the_sync return before it did
    anything — green alone, red in the suite, for a reason that had nothing
    to do with rollover.
    """
    monkeypatch.setattr(run_sync, "SYNC_LOCK_PATH",
                        str(tmp_path / ".sync.lock"))

BASE = "https://portal.tedronesans.k12.tr"


class StubDriver:
    def __init__(self, year):
        self.year = year

    def get(self, url):
        pass

    def quit(self):
        pass


def _patch_detect(monkeypatch, year, source="week_selector"):
    monkeypatch.setattr("src.run_sync.detect_academic_year",
                        lambda d, b: (year, source))


def _seed(out, scraped_at="2026-08-22T10:00:08"):
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "scraped_data.json"), "w", encoding="utf-8") as f:
        json.dump({"scraped_at": scraped_at}, f)


def test_first_run_records_the_year_without_archiving(tmp_path, monkeypatch):
    out = str(tmp_path); _seed(out)
    _patch_detect(monkeypatch, "2026-2027")
    r = run_year_rollover(StubDriver("x"), out, BASE)
    assert r["status"] == "initialized"
    assert r["archived"] is False
    assert not os.path.exists(os.path.join(out, "archive"))
    with open(os.path.join(out, "academic_year.json"), encoding="utf-8") as f:
        assert json.load(f)["year"] == "2026-2027"


def test_rollover_archives_the_previous_year(tmp_path, monkeypatch):
    out = str(tmp_path); _seed(out)
    with open(os.path.join(out, "academic_year.json"), "w", encoding="utf-8") as f:
        json.dump({"year": "2025-2026"}, f)
    _patch_detect(monkeypatch, "2026-2027")

    r = run_year_rollover(StubDriver("x"), out, BASE)
    assert r["status"] == "rollover"
    assert r["archived"] is True
    snap = os.path.join(out, "archive", "2025-2026", "scraped_data.json")
    with open(snap, encoding="utf-8") as f:
        assert json.load(f)["scraped_at"] == "2026-08-22T10:00:08"
    with open(os.path.join(out, "academic_year.json"), encoding="utf-8") as f:
        assert json.load(f)["year"] == "2026-2027"


def test_same_year_does_not_archive(tmp_path, monkeypatch):
    out = str(tmp_path); _seed(out)
    with open(os.path.join(out, "academic_year.json"), "w", encoding="utf-8") as f:
        json.dump({"year": "2026-2027"}, f)
    _patch_detect(monkeypatch, "2026-2027")
    r = run_year_rollover(StubDriver("x"), out, BASE)
    assert r["status"] == "current"
    assert r["archived"] is False


def test_undetected_year_holds_and_does_not_archive(tmp_path, monkeypatch):
    out = str(tmp_path); _seed(out)
    state_path = os.path.join(out, "academic_year.json")
    seeded = {"year": "2026-2027"}
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(seeded, f)
    _patch_detect(monkeypatch, None, "none")
    r = run_year_rollover(StubDriver("x"), out, BASE)
    assert r["status"] == "held"
    assert r["year"] == "2026-2027"
    assert r["archived"] is False
    with open(state_path, encoding="utf-8") as f:
        assert json.load(f) == seeded


def test_regression_is_ignored_and_never_archives(tmp_path, monkeypatch):
    out = str(tmp_path); _seed(out)
    with open(os.path.join(out, "academic_year.json"), "w", encoding="utf-8") as f:
        json.dump({"year": "2026-2027"}, f)
    _patch_detect(monkeypatch, "2025-2026")
    r = run_year_rollover(StubDriver("x"), out, BASE)
    assert r["status"] == "ignored_regression"
    assert r["archived"] is False
    assert not os.path.exists(os.path.join(out, "archive"))


def test_second_rollover_leaves_the_first_years_archive_untouched(
        tmp_path, monkeypatch):
    out = str(tmp_path); _seed(out)
    with open(os.path.join(out, "academic_year.json"), "w", encoding="utf-8") as f:
        json.dump({"year": "2025-2026"}, f)

    _patch_detect(monkeypatch, "2026-2027")
    first = run_year_rollover(StubDriver("x"), out, BASE)
    assert first["status"] == "rollover"
    first_snap = os.path.join(out, "archive", "2025-2026", "scraped_data.json")
    with open(first_snap, encoding="utf-8") as f:
        assert json.load(f)["scraped_at"] == "2026-08-22T10:00:08"

    with open(os.path.join(out, "scraped_data.json"), "w", encoding="utf-8") as f:
        json.dump({"scraped_at": "2027-08-22T10:00:00"}, f)
    _patch_detect(monkeypatch, "2027-2028")
    second = run_year_rollover(StubDriver("x"), out, BASE)
    assert second["status"] == "rollover"

    with open(first_snap, encoding="utf-8") as f:
        assert json.load(f)["scraped_at"] == "2026-08-22T10:00:08"


def test_malformed_stored_year_skips_archive_and_state_write(tmp_path, monkeypatch):
    out = str(tmp_path); _seed(out)
    with open(os.path.join(out, "academic_year.json"), "w", encoding="utf-8") as f:
        json.dump({"year": "2025"}, f)
    _patch_detect(monkeypatch, "2026-2027")

    r = run_year_rollover(StubDriver("x"), out, BASE)
    assert r["status"] == "rollover"
    assert r["archived"] is False
    assert not os.path.exists(os.path.join(out, "archive"))
    with open(os.path.join(out, "academic_year.json"), encoding="utf-8") as f:
        assert json.load(f)["year"] == "2025"


def test_archive_failure_in_main_does_not_abort_the_sync(tmp_path, monkeypatch):
    out = str(tmp_path)
    monkeypatch.setattr("src.run_sync.OUTPUT_DIR", out)
    monkeypatch.setenv("ASSISTANT_AUTO_REINDEX", "0")
    monkeypatch.setattr("src.run_sync.perform_incremental_reindex",
                        lambda project_root: {})

    monkeypatch.setattr("src.run_sync.create_driver", lambda: StubDriver("x"))
    monkeypatch.setattr(
        "src.run_sync.login",
        lambda d: {"method": "cached_session", "captcha_attempts": 0})

    def boom(*a, **kw):
        raise OSError("disk full")

    monkeypatch.setattr("src.run_sync.run_year_rollover", boom)

    for name in (
        "scrape_ogrenci_profili", "scrape_ders_programi", "scrape_odevlerim",
        "scrape_takim_calismalari", "scrape_takvim", "scrape_ders_icerikleri",
        "scrape_ogep", "scrape_gelisim_raporu", "scrape_duyurular",
    ):
        monkeypatch.setattr(f"src.run_sync.{name}", lambda d: {})

    monkeypatch.setattr("src.scrape_englishcentral.scrape", lambda: None)
    monkeypatch.setattr("src.scrape_achieve3000.scrape", lambda: None)
    monkeypatch.setattr("src.scrape_sebit_homework.scrape", lambda: None)

    from src.run_sync import main
    main()

    with open(os.path.join(out, "health.json"), encoding="utf-8") as f:
        health = json.load(f)
    assert health["academic_year"] is None
    assert health["year_detection"] == "unknown"
    assert health["year_archived"] is False
    assert any(e.startswith("year_rollover:") for e in health["scrape_errors"])
    assert not os.path.exists(os.path.join(out, "academic_year.json"))
    assert os.path.exists(os.path.join(out, "scraped_data.json"))
