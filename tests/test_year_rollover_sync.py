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
    r = run_year_rollover(StubDriver("x"), out, BASE, lambda: None)
    assert r["status"] == "initialized"
    assert r["archived"] is False
    assert not os.path.exists(os.path.join(out, "archive"))
    # the whole point of "initialized" is that the year gets recorded -
    # prove the state file actually holds it, not just the return value
    with open(os.path.join(out, "academic_year.json"), encoding="utf-8") as f:
        assert json.load(f)["year"] == "2026-2027"


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
    state_path = os.path.join(out, "academic_year.json")
    seeded = {"year": "2026-2027"}
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(seeded, f)
    _patch_detect(monkeypatch, None, "none")
    r = run_year_rollover(StubDriver("x"), out, BASE, lambda: None)
    assert r["status"] == "held"
    assert r["year"] == "2026-2027"
    assert r["archived"] is False
    # hold-last-known means the state file itself must be left untouched -
    # not just the returned year. save_year_state() would add "previous",
    # "detected_at", "source" and "grade" keys, so an exact-equality check
    # against the originally seeded content catches a spurious rewrite.
    with open(state_path, encoding="utf-8") as f:
        assert json.load(f) == seeded


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


def test_current_run_repairs_a_pending_drive_archive(tmp_path, monkeypatch):
    """The rollover branch runs exactly once, the sync after it. If the
    Drive half of that one rollover deferred (e.g. an expired token), the
    manifest is left with drive_folder=None and nothing will ever call
    archive_year_drive again unless a later "current" run retries it."""
    out = str(tmp_path); _seed(out)
    with open(os.path.join(out, "academic_year.json"), "w", encoding="utf-8") as f:
        json.dump({"year": "2026-2027"}, f)
    archive_dir = os.path.join(out, "archive", "2026-2027")
    os.makedirs(archive_dir)
    with open(os.path.join(archive_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"year": "2026-2027", "drive_folder": None}, f)
    _patch_detect(monkeypatch, "2026-2027")

    calls = []

    def fake_archive_year_drive(year, output_dir, drive_service):
        calls.append((year, output_dir, drive_service))
        return {"year": year, "drive_folder": "folder123", "counts": {}}

    monkeypatch.setattr("src.run_sync.archive_year_drive", fake_archive_year_drive)
    sentinel = object()

    r = run_year_rollover(StubDriver("x"), out, BASE, lambda: sentinel)

    assert r["status"] == "current"
    assert r["archived"] is True
    assert r["manifest"]["drive_folder"] == "folder123"
    assert calls == [("2026-2027", out, sentinel)]


def test_current_run_does_not_repeat_a_completed_drive_archive(tmp_path, monkeypatch):
    """Once drive_folder is recorded, a "current" run must not re-call
    archive_year_drive on every sync - that would re-run the Drive move
    every 15 minutes forever."""
    out = str(tmp_path); _seed(out)
    with open(os.path.join(out, "academic_year.json"), "w", encoding="utf-8") as f:
        json.dump({"year": "2026-2027"}, f)
    archive_dir = os.path.join(out, "archive", "2026-2027")
    os.makedirs(archive_dir)
    with open(os.path.join(archive_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"year": "2026-2027", "drive_folder": "already_set"}, f)
    _patch_detect(monkeypatch, "2026-2027")

    def fail_if_called(*a, **kw):
        raise AssertionError("archive_year_drive must not be re-called")

    monkeypatch.setattr("src.run_sync.archive_year_drive", fail_if_called)

    r = run_year_rollover(StubDriver("x"), out, BASE, lambda: None)

    assert r["status"] == "current"
    assert r["archived"] is False


def test_archive_failure_in_main_does_not_abort_the_sync(tmp_path, monkeypatch):
    """run_year_rollover() runs unwrapped at its call site in main() would
    mean an OSError from shutil.copy2 mid-archive (e.g. disk full) kills the
    entire sync before health.json is ever written - nothing monitoring
    health would see the run happened at all. It must instead be recorded
    and the run must continue: year_info stays at its safe default (no
    state advances), but scraping and health.json still happen."""
    out = str(tmp_path)
    monkeypatch.setattr("src.run_sync.OUTPUT_DIR", out)
    # Belt-and-braces: the env-var gate alone is not reliable here because
    # scrape_all.py (and the three side-session scraper modules imported
    # below) call load_env() at *module import time*, which can reload
    # .env's ASSISTANT_AUTO_REINDEX=1 over this setenv the moment one of
    # those modules is first imported (as monkeypatch.setattr below does).
    # Patching the function itself removes that ordering trap entirely -
    # this must never touch the real project's assistant index.
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

    # Post-scrape side-session scrapers - main() imports these locally at
    # call time, so patching the source module's attribute is what's seen.
    monkeypatch.setattr("src.scrape_englishcentral.scrape", lambda: None)
    monkeypatch.setattr("src.scrape_achieve3000.scrape", lambda: None)
    monkeypatch.setattr("src.scrape_sebit_homework.scrape", lambda: None)

    from src.run_sync import main
    main()  # must not raise

    with open(os.path.join(out, "health.json"), encoding="utf-8") as f:
        health = json.load(f)
    # the fail-safe default - no state advanced, nothing trusted as a new year
    assert health["academic_year"] is None
    assert health["year_detection"] == "unknown"
    assert health["year_archived"] is False
    # but the failure is visible, not swallowed
    assert any(e.startswith("year_rollover:") for e in health["scrape_errors"])
    # and the state file was never touched
    assert not os.path.exists(os.path.join(out, "academic_year.json"))
    # the run continued past the failure and still produced output
    assert os.path.exists(os.path.join(out, "scraped_data.json"))
