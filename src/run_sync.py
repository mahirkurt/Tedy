#!/usr/bin/env python3
"""TED Portal auto-sync: scrape all data and write local outputs.

Designed to run via crontab every 15 minutes.
"""
import os
import sys
import time
import traceback
from datetime import datetime

# Ensure project root for imports
PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, PROJECT_ROOT)

from src.scrape_all import (  # noqa: E402
    OUTPUT_DIR,
    create_driver,
    login,
    scrape_ders_icerikleri,
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


def main():
    os.chdir(PROJECT_ROOT)

    start_time = time.time()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"[{ts}] TED Portal Auto-Sync started")
    print(f"{'='*60}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    driver = create_driver()

    scrape_errors = []

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

        validation = validate_scraped_data(data, prev_data)
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
        if any(section in e for e in validation.get("errors", [])):
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
