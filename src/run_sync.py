#!/usr/bin/env python3
"""TED Portal auto-sync: scrape all data and write local outputs.

Designed to run via crontab every 15 minutes.
"""
import os
import re
import sys
import time
import traceback
from datetime import datetime

# Ensure project root for imports
PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, PROJECT_ROOT)

from src.scrape_all import (  # noqa: E402
    BASE_URL,
    OUTPUT_DIR,
    create_driver,
    login,
    scrape_ders_icerikleri,
    PortalUnavailable,
    scrape_ders_programi,
    scrape_duyurular,
    scrape_gelisim_raporu,
    scrape_odevlerim,
    scrape_ogep,
    scrape_ogrenci_profili,
    scrape_takim_calismalari,
    scrape_takvim,
)
from src.assistant_core import perform_incremental_reindex  # noqa: E402
from src.academic_year import (  # noqa: E402
    STATE_FILENAME,
    detect_academic_year,
    load_year_state,
    resolve_year,
    save_year_state,
)
from src.archive_year import archive_year_drive  # noqa: E402

_YEAR_RE = re.compile(r"^\d{4}-\d{4}$")


def run_year_rollover(driver, output_dir, base_url, drive_factory):
    """Resolve the academic year and archive the previous one if it changed.

    MUST run before any scraper: archiving afterwards would snapshot
    new-year data under the old year's name and lose the old year.
    """
    state_path = os.path.join(output_dir, STATE_FILENAME)
    stored = load_year_state(state_path).get("year")
    detected, source = detect_academic_year(driver, base_url)
    resolution = resolve_year(detected, stored)

    result = {"year": resolution.year, "status": resolution.status,
              "source": source, "archived": False, "manifest": None}
    print(f"[YEAR] {resolution.status}: {stored or '-'} -> {resolution.year} "
          f"(source: {source})")

    if resolution.status == "rollover":
        if not _YEAR_RE.match(stored or ""):
            print(f"  [ARCHIVE] Skipped: stored year {stored!r} is not a "
                  f"valid YYYY-YYYY academic year")
            return result
        try:
            drive_service = drive_factory()
        except Exception as e:
            print(f"  [ARCHIVE] Drive unavailable: {type(e).__name__}: {e}")
            drive_service = None
        result["manifest"] = archive_year_drive(stored, output_dir, drive_service)
        result["archived"] = True
        print(f"  [ARCHIVE] {stored} sealed "
              f"({result['manifest'].get('counts', {})})")

    elif resolution.status == "current":
        # The Drive half of a rollover may defer while the local half
        # seals (e.g. an expired token during the one sync that flips the
        # year). That deferred manifest lives under the *previous* year's
        # archive directory - the rollover branch above archives `stored`,
        # then the state advances - never under resolution.year, which is
        # the currently active year. So this cannot look up a single
        # guessed year; it must scan for any manifest still missing its
        # drive_folder. That's also self-healing if `previous` was ever
        # lost, and correct no matter how many syncs back the deferred
        # repair is.
        import glob
        import json
        pending_years = []
        for manifest_path in sorted(glob.glob(os.path.join(
                output_dir, "archive", "*", "manifest.json"))):
            year = os.path.basename(os.path.dirname(manifest_path))
            if not _YEAR_RE.match(year):
                continue
            try:
                with open(manifest_path, encoding="utf-8") as f:
                    manifest = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"  [ARCHIVE] Skipped unreadable manifest "
                      f"{manifest_path}: {type(e).__name__}: {e}")
                continue
            if not manifest.get("drive_folder"):
                pending_years.append(year)

        if pending_years:
            try:
                drive_service = drive_factory()
            except Exception as e:
                print(f"  [ARCHIVE] Drive unavailable: "
                      f"{type(e).__name__}: {e}")
                drive_service = None
            for year in pending_years:
                result["manifest"] = archive_year_drive(
                    year, output_dir, drive_service)
                result["archived"] = True
                print(f"  [ARCHIVE] {year} Drive repair retried "
                      f"(drive_folder="
                      f"{result['manifest'].get('drive_folder')})")

    if resolution.year and resolution.status in (
            "initialized", "rollover", "current"):
        save_year_state(state_path, resolution.year,
                        stored if resolution.status == "rollover" else
                        load_year_state(state_path).get("previous"),
                        source)
    return result


SYNC_LOG_MAX_BYTES = 20 * 1024 * 1024  # 20 MB (H6): ~3.3 KB/run * 96 runs/day


def rotate_sync_log(log_path=None, max_bytes=SYNC_LOG_MAX_BYTES):
    """Rotate output/sync.log to sync.log.1 once it exceeds max_bytes.

    No logrotate config exists for this file (cron appends to it forever),
    so left alone it grows unbounded (~108 MB/year at current run size).
    This keeps exactly one previous generation: an existing sync.log.1 is
    replaced, not appended to.

    Subtlety: cron invokes this script as `>> output/sync.log`, so the
    shell already holds an open, append-mode file descriptor for the
    *whole* run before this function ever runs. Renaming the file here
    does not redirect that descriptor — it points at the underlying inode,
    not the path — so the rest of *this* run's output keeps landing in the
    newly-renamed sync.log.1, and only the *next* cron invocation's fresh
    `>>` open sees an empty sync.log. That is expected and harmless (the
    rotation boundary just lands one run later than the byte count alone
    suggests); do not try to defeat it, e.g. by reopening stdout here.

    log_path defaults to the module-level OUTPUT_DIR at *call* time (not
    baked into the signature), so tests and callers can point it elsewhere
    without touching the real output/ directory.
    """
    if log_path is None:
        log_path = os.path.join(OUTPUT_DIR, "sync.log")
    if not os.path.exists(log_path):
        return
    if os.path.getsize(log_path) <= max_bytes:
        return
    rotated_path = log_path + ".1"
    if os.path.exists(rotated_path):
        os.remove(rotated_path)
    os.rename(log_path, rotated_path)


def main():
    os.chdir(PROJECT_ROOT)
    rotate_sync_log()

    start_time = time.time()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"[{ts}] TED Portal Auto-Sync started")
    print(f"{'='*60}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    driver = create_driver()

    scrape_errors = []
    unavailable = {}
    year_info = {"year": None, "status": "unknown",
                 "source": "none", "archived": False, "manifest": None}

    login_info = None
    validation = {"section_counts": {}, "errors": [], "warnings": []}
    prev_data = {}

    try:
        # 1. Login
        login_info = login(driver)
        if not login_info:
            print("[ERROR] Login failed, aborting")
            scrape_errors.append("login: Login failed")
            health = {
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "scrape_errors": scrape_errors,
                "duration_seconds": round(time.time() - start_time),
                "login": {"method": "failed", "captcha_attempts": 5},
            }
            from src.json_utils import atomic_json_dump
            atomic_json_dump(health, os.path.join(OUTPUT_DIR, "health.json"))
            print(f"\nHealth: ERRORS ({health['duration_seconds']}s)")
            return

        def _drive_factory():
            from src.sync_to_google import get_services
            return get_services()[1]

        try:
            year_info = run_year_rollover(
                driver, OUTPUT_DIR, BASE_URL, _drive_factory)
        except Exception as e:
            # A failure here (e.g. an OSError from shutil.copy2 mid-archive)
            # must not kill the whole run: year_info stays at its safe
            # default (set above), so no state advances and no scraper
            # data below gets trusted as belonging to a new year - but the
            # run continues and still writes health.json.
            scrape_errors.append(f"year_rollover: {e}")
            print(f"[ERROR] Year rollover failed: {e}")

        # 2. Scrape all sources
        data = {"scraped_at": datetime.now().isoformat()}
        scrapers = [
            ("ogrenci_profili", lambda d: scrape_ogrenci_profili(d)),
            ("ders_programi", lambda d: scrape_ders_programi(d)),
            ("odevlerim", lambda d: scrape_odevlerim(d)),
            ("takim_calismalari", lambda d: scrape_takim_calismalari(d)),
            ("takvim", lambda d: scrape_takvim(d)),
            ("ders_icerikleri", lambda d: scrape_ders_icerikleri(d)),
            ("ogep", lambda d: scrape_ogep(d)),
            ("gelisim_raporu", lambda d: scrape_gelisim_raporu(d)),
            ("duyurular", lambda d: scrape_duyurular(d)),
        ]
        for name, fn in scrapers:
            try:
                data[name] = fn(driver)
            except PortalUnavailable as e:
                # The portal explained the absence - record it, don't
                # report it as a scrape failure.
                unavailable[name] = {"reason": e.reason, "detail": str(e)}
                data[name] = [] if name in ("takvim", "ders_programi") else {}
                print(f"[UNAVAILABLE] {name}: {e}")
            except Exception as e:
                scrape_errors.append(f"{name}: {e}")
                data[name] = [] if name in ("takvim", "ders_programi") else {}
                print(f"[ERROR] {name} failed: {e}")

        # Validate scraped data
        from src.data_validator import validate_scraped_data
        prev_data = {}
        prev_path = os.path.join(OUTPUT_DIR, "scraped_data.json")
        if os.path.exists(prev_path):
            try:
                import json
                with open(prev_path) as f:
                    prev_data = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        validation = validate_scraped_data(data, prev_data, unavailable)
        if validation["errors"]:
            scrape_errors.extend(validation["errors"])
        if validation["warnings"]:
            for w in validation["warnings"]:
                print(f"[WARN] Validation: {w}")

        # Save scraped data
        from src.json_utils import atomic_json_dump
        out_path = os.path.join(OUTPUT_DIR, "scraped_data.json")
        atomic_json_dump(data, out_path)

    finally:
        driver.quit()

    # 3. English Central scrape (separate Selenium session)
    try:
        from src.scrape_englishcentral import scrape as scrape_ec
        scrape_ec()
    except Exception as e:
        scrape_errors.append(f"englishcentral: {e}")
        print(f"[WARN] English Central scrape failed: {e}")

    # 4. Achieve3000 scrape (separate Selenium session)
    try:
        from src.scrape_achieve3000 import scrape as scrape_a3k
        scrape_a3k()
    except Exception as e:
        scrape_errors.append(f"achieve3000: {e}")
        print(f"[WARN] Achieve3000 scrape failed: {e}")

    # 5. SEBİT homework scrape (separate Selenium session)
    try:
        from src.scrape_sebit_homework import scrape as scrape_sebit_hw
        scrape_sebit_hw()
    except Exception as e:
        scrape_errors.append(f"sebit_homework: {e}")
        print(f"[WARN] SEBİT homework scrape failed: {e}")

    # 6. Write health check
    from src.json_utils import atomic_json_dump
    from src.data_validator import _count_section

    # Build per-section status
    sections_health = {}
    for section, count in validation.get("section_counts", {}).items():
        prev_count = _count_section(section, prev_data) if prev_data else 0

        status = "ok"
        if section in unavailable:
            status = "unavailable"
        elif any(section in e for e in validation.get("errors", [])):
            status = "error"
        elif any(section in w for w in validation.get("warnings", [])):
            status = "warning"
        elif any(e.startswith(f"{section}:") for e in scrape_errors):
            status = "skipped"

        sections_health[section] = {
            "count": count,
            "prev_count": prev_count,
            "status": status,
        }

    health = {
        "timestamp": datetime.now().isoformat(),
        "success": len(scrape_errors) == 0,
        "scrape_errors": scrape_errors,
        "duration_seconds": round(time.time() - start_time),
        "validation_warnings": validation.get("warnings", []),
        "unavailable": unavailable,
        "academic_year": year_info["year"],
        "year_detection": year_info["status"],
        "year_archived": year_info["archived"],
        "login": login_info or {"method": "failed", "captcha_attempts": 0},
        "sections": sections_health,
        "staleness": {
            "last_successful_full_scrape": (
                datetime.now().isoformat() if not scrape_errors
                else prev_data.get("scraped_at", "")
            ),
            "stale_sections": [
                s for s, info in sections_health.items()
                if info["status"] in ("error", "skipped")
            ],
        },
    }
    atomic_json_dump(health, os.path.join(OUTPUT_DIR, "health.json"))

    # 7. Incremental assistant index refresh (best-effort)
    if os.environ.get("ASSISTANT_AUTO_REINDEX", "1") == "1":
        try:
            idx_stats = perform_incremental_reindex(PROJECT_ROOT)
            print(
                "[Assistant] Reindex:"
                f" files={idx_stats.get('files_indexed', 0)}"
                f" chunks={idx_stats.get('chunks_indexed', 0)}"
                f" changed={idx_stats.get('changed_files', 0)}"
                f" unchanged={idx_stats.get('unchanged_files', 0)}"
            )
        except Exception as e:
            print(f"[WARN] Assistant reindex failed: {e}")

    elapsed = time.time() - start_time
    print(f"\nHealth: {'OK' if health['success'] else 'ERRORS'} "
          f"({health['duration_seconds']}s)")
    print(f"[DONE] Completed in {elapsed:.0f}s")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
