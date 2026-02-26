#!/usr/bin/env python3
"""TED Portal auto-sync: scrape all data and smart-sync to Google.

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
os.chdir(PROJECT_ROOT)

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from src.scrape_all import (
    create_driver, login, scrape_ders_programi, scrape_odevlerim,
    scrape_takim_calismalari, scrape_takvim, scrape_ders_icerikleri,
    scrape_ogep, scrape_gelisim_raporu, scrape_duyurular, OUTPUT_DIR,
)
from src.sync_to_google import (
    get_services, get_or_create_calendar, get_or_create_task_list,
    fetch_existing_events, fetch_existing_tasks,
    sync_ders_programi, sync_odevlerim, sync_takim_calismalari,
    sync_takvim, sync_ders_icerikleri, sync_ogep,
    sync_gelisim_raporu, sync_duyurular,
    sync_grades_to_sheets, sync_attachments_to_drive,
)


def main():
    start_time = time.time()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"[{ts}] TED Portal Auto-Sync started")
    print(f"{'='*60}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    driver = create_driver()

    scrape_errors = []

    try:
        # 1. Login
        if not login(driver):
            print("[ERROR] Login failed, aborting")
            scrape_errors.append("login: Login failed")
            health = {
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "scrape_errors": scrape_errors,
                "duration_seconds": round(time.time() - start_time),
            }
            from src.json_utils import atomic_json_dump
            atomic_json_dump(health, os.path.join(OUTPUT_DIR, "health.json"))
            print(f"\nHealth: ERRORS ({health['duration_seconds']}s)")
            return

        # 2. Scrape all sources
        data = {"scraped_at": datetime.now().isoformat()}
        scrapers = [
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

        # Save scraped data
        from src.json_utils import atomic_json_dump
        out_path = os.path.join(OUTPUT_DIR, "scraped_data.json")
        atomic_json_dump(data, out_path)

    finally:
        driver.quit()

    # 3. Smart sync to Google
    try:
        print("\n--- Google Sync ---")
        cal_svc, tasks_svc, sheets_svc, drive_svc = get_services()
        cal_id = get_or_create_calendar(cal_svc, "TED Rönesans")
        task_list_id = get_or_create_task_list(tasks_svc, "TED Ödevler")

        existing_events = fetch_existing_events(cal_svc, cal_id)
        existing_tasks = fetch_existing_tasks(tasks_svc, task_list_id)
        print(f"  Existing: {len(existing_events)} events, "
              f"{len(existing_tasks)} tasks")

        sync_ders_programi(cal_svc, data, cal_id, existing_events)
        sync_odevlerim(cal_svc, tasks_svc, data, cal_id,
                       task_list_id, existing_events, existing_tasks,
                       drive_service=drive_svc)
        sync_takim_calismalari(cal_svc, data, cal_id, existing_events)
        sync_takvim(cal_svc, data, cal_id, existing_events)
        sync_ders_icerikleri(tasks_svc, data, task_list_id,
                             existing_tasks)
        sync_ogep(cal_svc, data, cal_id, existing_events)
        sync_gelisim_raporu(tasks_svc, data, task_list_id,
                            existing_tasks)
        sync_duyurular(cal_svc, data, cal_id, existing_events)
        sync_grades_to_sheets(sheets_svc, data)
        sync_attachments_to_drive(drive_svc, cal_svc, data, cal_id)
    except Exception as e:
        scrape_errors.append(f"google_sync: {e}")
        print(f"[ERROR] Google sync failed: {e}")

    # 4. AI Enrichment (post-sync)
    print("\n--- AI Enrichment ---")
    try:
        from src.enrich_gemini import enrich_all
        from src.sync_to_google import TOKEN_FILE, TOKEN_HURIYE
        enrich_all(token_file=TOKEN_FILE)
        if os.path.exists(TOKEN_HURIYE):
            enrich_all(token_file=TOKEN_HURIYE)
    except Exception as e:
        print(f"[WARN] Enrichment failed: {e}")
        # Non-fatal: sync succeeded even if enrichment fails

    # 5. Classroom sync
    print("\n--- Classroom Sync ---")
    try:
        from src.sync_to_classroom import main as sync_classroom
        sync_classroom(scraped_data=data)
    except Exception as e:
        scrape_errors.append(f"classroom_sync: {e}")
        print(f"[WARN] Classroom sync failed: {e}")

    # 6. Write health check
    from src.json_utils import atomic_json_dump
    health = {
        "timestamp": datetime.now().isoformat(),
        "success": len(scrape_errors) == 0,
        "scrape_errors": scrape_errors,
        "duration_seconds": round(time.time() - start_time),
    }
    atomic_json_dump(health, os.path.join(OUTPUT_DIR, "health.json"))

    elapsed = time.time() - start_time
    print(f"\nHealth: {'OK' if health['success'] else 'ERRORS'} ({health['duration_seconds']}s)")
    print(f"[DONE] Completed in {elapsed:.0f}s")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
