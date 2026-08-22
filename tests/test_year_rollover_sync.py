"""Rollover archives the old year before any new-year data is written."""
import json
import os

from src.run_sync import run_year_rollover

BASE = "https://portal.tedronesans.k12.tr"


class StubDriver:
    def __init__(self, year):
        self.year = year

    def get(self, url):
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
    r = run_year_rollover(StubDriver("x"), out, BASE, lambda: None)
    assert r["status"] == "initialized"
    assert r["archived"] is False
    assert not os.path.exists(os.path.join(out, "archive"))


def test_rollover_archives_the_previous_year(tmp_path, monkeypatch):
    out = str(tmp_path); _seed(out)
    with open(os.path.join(out, "academic_year.json"), "w", encoding="utf-8") as f:
        json.dump({"year": "2025-2026"}, f)
    _patch_detect(monkeypatch, "2026-2027")

    r = run_year_rollover(StubDriver("x"), out, BASE, lambda: None)
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
    r = run_year_rollover(StubDriver("x"), out, BASE, lambda: None)
    assert r["status"] == "current"
    assert r["archived"] is False


def test_undetected_year_holds_and_does_not_archive(tmp_path, monkeypatch):
    out = str(tmp_path); _seed(out)
    with open(os.path.join(out, "academic_year.json"), "w", encoding="utf-8") as f:
        json.dump({"year": "2026-2027"}, f)
    _patch_detect(monkeypatch, None, "none")
    r = run_year_rollover(StubDriver("x"), out, BASE, lambda: None)
    assert r["status"] == "held"
    assert r["year"] == "2026-2027"
    assert r["archived"] is False


def test_regression_is_ignored_and_never_archives(tmp_path, monkeypatch):
    out = str(tmp_path); _seed(out)
    with open(os.path.join(out, "academic_year.json"), "w", encoding="utf-8") as f:
        json.dump({"year": "2026-2027"}, f)
    _patch_detect(monkeypatch, "2025-2026")
    r = run_year_rollover(StubDriver("x"), out, BASE, lambda: None)
    assert r["status"] == "ignored_regression"
    assert r["archived"] is False
    assert not os.path.exists(os.path.join(out, "archive"))


def test_drive_unavailable_still_archives_locally(tmp_path, monkeypatch):
    out = str(tmp_path); _seed(out)
    with open(os.path.join(out, "academic_year.json"), "w", encoding="utf-8") as f:
        json.dump({"year": "2025-2026"}, f)
    _patch_detect(monkeypatch, "2026-2027")

    def boom():
        raise RuntimeError("no credentials")

    r = run_year_rollover(StubDriver("x"), out, BASE, boom)
    assert r["archived"] is True
    assert r["manifest"]["drive_folder"] is None


def test_malformed_stored_year_skips_archive_and_state_write(tmp_path, monkeypatch):
    """A stored year that is not YYYY-YYYY must never be turned into a
    filesystem path or Drive folder name - skip the archive, leave the
    state file untouched, and warn.

    "2025" (truncated, missing the second half) still sorts lexicographically
    before "2026-2027", so resolve_year still classifies this as a rollover
    (unlike e.g. "not-a-year", which would sort after and hit the unrelated
    ignored_regression path instead) - this is what actually exercises the
    new format-validation branch rather than the pre-existing regression
    guard.
    """
    out = str(tmp_path); _seed(out)
    with open(os.path.join(out, "academic_year.json"), "w", encoding="utf-8") as f:
        json.dump({"year": "2025"}, f)
    _patch_detect(monkeypatch, "2026-2027")

    r = run_year_rollover(StubDriver("x"), out, BASE, lambda: None)
    assert r["status"] == "rollover"
    assert r["archived"] is False
    assert not os.path.exists(os.path.join(out, "archive"))
    # state file must be left exactly as it was - not overwritten with the
    # new detected year, since we never completed the archive of the old one
    with open(os.path.join(out, "academic_year.json"), encoding="utf-8") as f:
        assert json.load(f)["year"] == "2025"
