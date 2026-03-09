# Crontab + Smart Sync Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automate TED portal scraping every 15 minutes with intelligent deduplication (upsert, no duplicates).

**Architecture:** A `run_sync.py` orchestrator calls existing scrape functions, then smart-syncs to Google Calendar/Tasks using `extendedProperties.private.source=ted-portal` to identify our events. Matching key is `(summary, start)` for calendar and `(title, due)` for tasks. Crontab runs every 15 min.

**Tech Stack:** Python 3.12, Selenium, ddddocr, Google Calendar API v3, Google Tasks API v1

---

### Task 1: Add upsert helpers to sync_to_google.py

**Files:**
- Modify: `src/sync_to_google.py:30-65`

**Step 1: Add `fetch_existing_events` function after `get_or_create_task_list` (line 65)**

Add this function to fetch all TED-portal-created events:

```python
def fetch_existing_events(cal_service, cal_id):
    """Fetch all events created by this script (source=ted-portal).

    Returns dict: {(summary, start_str): event_id}
    """
    existing = {}
    page_token = None
    while True:
        result = cal_service.events().list(
            calendarId=cal_id,
            privateExtendedProperty="source=ted-portal",
            maxResults=2500,
            pageToken=page_token,
            singleEvents=True,
        ).execute()
        for ev in result.get("items", []):
            summary = ev.get("summary", "")
            start = ev.get("start", {})
            start_str = start.get("dateTime", start.get("date", ""))
            existing[(summary, start_str)] = ev["id"]
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return existing
```

**Step 2: Add `fetch_existing_tasks` function right after**

```python
def fetch_existing_tasks(tasks_service, task_list_id):
    """Fetch all tasks from the TED task list.

    Returns dict: {(title, due): task_id}
    """
    existing = {}
    page_token = None
    while True:
        result = tasks_service.tasks().list(
            tasklist=task_list_id,
            maxResults=100,
            pageToken=page_token,
            showCompleted=True,
            showHidden=True,
        ).execute()
        for t in result.get("items", []):
            title = t.get("title", "")
            due = t.get("due", "")
            existing[(title, due)] = t["id"]
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return existing
```

**Step 3: Add `upsert_event` helper function right after**

```python
SOURCE_TAG = {"private": {"source": "ted-portal"}}


def upsert_event(cal_service, cal_id, event_body, existing_events):
    """Insert or skip a calendar event. Returns 'added', 'exists', or 'error'."""
    summary = event_body.get("summary", "")
    start = event_body.get("start", {})
    start_str = start.get("dateTime", start.get("date", ""))
    key = (summary, start_str)

    event_body["extendedProperties"] = SOURCE_TAG

    if key in existing_events:
        return "exists"

    try:
        cal_service.events().insert(calendarId=cal_id, body=event_body).execute()
        return "added"
    except Exception:
        return "error"


def upsert_task(tasks_service, task_list_id, task_body, existing_tasks):
    """Insert or skip a task. Returns 'added', 'exists', or 'error'."""
    title = task_body.get("title", "")
    due = task_body.get("due", "")
    key = (title, due)

    if key in existing_tasks:
        return "exists"

    try:
        tasks_service.tasks().insert(tasklist=task_list_id, body=task_body).execute()
        return "added"
    except Exception:
        return "error"
```

**Step 4: Verify syntax**

Run: `cd /mnt/pi-shared/projects/TED && .venv/bin/python -c "import src.sync_to_google"`
Expected: no errors

---

### Task 2: Refactor all sync functions to use upsert

**Files:**
- Modify: `src/sync_to_google.py:101-422` (all 5 sync functions)
- Modify: `src/sync_to_google.py:428-452` (main function)

**Step 1: Refactor `sync_ders_programi` (lines 101-195)**

Replace the `cal_service.events().insert(...)` call (line 189) with:

```python
result = upsert_event(cal_service, cal_id, event, existing_events)
if result == "added":
    events_added += 1
elif result == "exists":
    events_skipped += 1
```

Change function signature to accept `existing_events` parameter:
```python
def sync_ders_programi(cal_service, data, cal_id, existing_events):
```

Change counter from `events_created = 0` to `events_added = 0` and add `events_skipped = 0`.
Update print at end: `print(f"  Ders: +{events_added} added, ={events_skipped} skipped")`

**Step 2: Refactor `sync_odevlerim` (lines 201-263)**

Change signature:
```python
def sync_odevlerim(cal_service, tasks_service, data, cal_id, task_list_id, existing_events, existing_tasks):
```

Replace `cal_service.events().insert(...)` (line 257) with `upsert_event(...)`.
Replace `tasks_service.tasks().insert(...)` (line 230) with `upsert_task(...)`.
Track added/skipped counts for both.

**Step 3: Refactor `sync_takim_calismalari` (lines 269-311)**

Change signature:
```python
def sync_takim_calismalari(cal_service, data, cal_id, existing_events):
```

Replace insert with `upsert_event(...)`.

**Step 4: Refactor `sync_takvim` (lines 317-388)**

Change signature:
```python
def sync_takvim(cal_service, data, cal_id, existing_events):
```

Replace insert with `upsert_event(...)`.

**Step 5: Refactor `sync_ders_icerikleri` (lines 394-422)**

Change signature:
```python
def sync_ders_icerikleri(tasks_service, data, task_list_id, existing_tasks):
```

Replace insert with `upsert_task(...)`.

**Step 6: Update `main()` (lines 428-452)**

After getting cal_id and task_list_id, add:

```python
print("Fetching existing events/tasks for dedup...")
existing_events = fetch_existing_events(cal_service, cal_id)
existing_tasks = fetch_existing_tasks(tasks_service, task_list_id)
print(f"  Found {len(existing_events)} existing events, {len(existing_tasks)} existing tasks")
```

Update all sync calls to pass `existing_events`/`existing_tasks`.

**Step 7: Verify syntax**

Run: `cd /mnt/pi-shared/projects/TED && .venv/bin/python -c "import src.sync_to_google"`
Expected: no errors

**Step 8: Test idempotency**

Run sync twice:
```bash
cd /mnt/pi-shared/projects/TED && .venv/bin/python src/sync_to_google.py
```

First run: events added (old events without source tag won't match — that's OK, they become "new").
Second run: all events should show "skipped" (0 added).

---

### Task 3: Add ÖGEP scraping to scrape_all.py

**Files:**
- Modify: `src/scrape_all.py:336-457`

**Step 1: Add `scrape_ogep` function after `scrape_takvim` (line 335)**

```python
def scrape_ogep(driver):
    """Scrape ÖGEP (Öğrenci Gelişim Programı) sessions."""
    print("\n[6/6] ÖGEP'lerim")
    url = f"{BASE_URL}/pages/ogrenci_istekler/p_etutlerim"
    driver.get(url)
    time.sleep(3)

    # Select "Tamamı" to show all rows
    try:
        length_select = driver.find_element(
            By.CSS_SELECTOR, "select[name='t_etutlerim_length']"
        )
        Select(length_select).select_by_value("-1")
        time.sleep(2)
        print("  DataTables: selected 'Tamamı'")
    except Exception as e:
        print(f"  Could not select Tamamı: {e}")

    result = {"sessions": []}
    tables = driver.find_elements(By.TAG_NAME, "table")
    for tbl in tables:
        headers = [th.text.strip() for th in tbl.find_elements(By.TAG_NAME, "th")]
        if any("ÖGEP" in h for h in headers):
            result["sessions"] = extract_table(driver, tbl)
            break

    driver.save_screenshot(os.path.join(OUTPUT_DIR, "ogep.png"))
    print(f"  Found {len(result['sessions'].get('rows', []))} ÖGEP sessions")
    return result
```

**Step 2: Update main() to call scrape_ogep and number prints**

In `main()`, after line 443 (`data["ders_icerikleri"] = ...`), add:
```python
data["ogep"] = scrape_ogep(driver)
```

Also update the section header prints from `[1/5]`...`[5/5]` to `[1/6]`...`[6/6]`.

**Step 3: Verify syntax**

Run: `cd /mnt/pi-shared/projects/TED && .venv/bin/python -c "import src.scrape_all"`
Expected: no errors

---

### Task 4: Add ÖGEP sync to sync_to_google.py

**Files:**
- Modify: `src/sync_to_google.py` (add new function + call in main)

**Step 1: Add `sync_ogep` function after `sync_ders_icerikleri`**

```python
def sync_ogep(cal_service, data, cal_id, existing_events):
    """Sync ÖGEP sessions to Google Calendar."""
    print("\n[6/6] ÖGEP -> Calendar")
    rows = data.get("ogep", {}).get("sessions", {}).get("rows", [])
    added = 0
    skipped = 0

    for row in rows:
        name = row.get("ÖGEP (Öğrenci Gelişim Programı)", "")
        start_str = row.get("Çalışma Başlangıç", "")
        end_str = row.get("Çalışma Bitiş", "")
        katilim = row.get("Katılım Durumu", "")
        link = row.get("Teams Link", "")

        start_dt = parse_tr_datetime(start_str)
        end_dt = parse_tr_datetime(end_str)
        if not start_dt or not end_dt:
            continue

        desc = f"Katılım: {katilim}" if katilim else ""
        location = "TED Rönesans Koleji" if link == "Yüz Yüze" else (link if link else "")

        event = {
            "summary": f"ÖGEP: {name}",
            "description": desc,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": TIMEZONE},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": TIMEZONE},
            "colorId": COLORS["ogep"],
            "location": location,
        }
        result = upsert_event(cal_service, cal_id, event, existing_events)
        if result == "added":
            added += 1
        elif result == "exists":
            skipped += 1

    print(f"  ÖGEP: +{added} added, ={skipped} skipped")
    return added
```

**Step 2: Update main() to call sync_ogep**

After the `sync_ders_icerikleri(...)` call, add:
```python
sync_ogep(cal_service, data, cal_id, existing_events)
```

Update `[1/5]`...`[5/5]` prints in each function to `[1/6]`...`[6/6]`.

**Step 3: Verify syntax**

Run: `cd /mnt/pi-shared/projects/TED && .venv/bin/python -c "import src.sync_to_google"`
Expected: no errors

---

### Task 5: Create run_sync.py orchestrator

**Files:**
- Create: `src/run_sync.py`

**Step 1: Write the orchestrator script**

```python
#!/usr/bin/env python3
"""TED Portal auto-sync: scrape all data and smart-sync to Google.

Designed to run via crontab every 15 minutes.
"""
import json
import os
import sys
import time
import traceback
from datetime import datetime

# Ensure project root for imports
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from src.scrape_all import (
    create_driver, login, scrape_ders_programi, scrape_odevlerim,
    scrape_takim_calismalari, scrape_takvim, scrape_ders_icerikleri,
    scrape_ogep, OUTPUT_DIR,
)
from src.sync_to_google import (
    get_services, get_or_create_calendar, get_or_create_task_list,
    fetch_existing_events, fetch_existing_tasks,
    sync_ders_programi, sync_odevlerim, sync_takim_calismalari,
    sync_takvim, sync_ders_icerikleri, sync_ogep,
)


def main():
    start_time = time.time()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"[{ts}] TED Portal Auto-Sync started")
    print(f"{'='*60}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    driver = create_driver()

    try:
        # 1. Login
        if not login(driver):
            print("[ERROR] Login failed, aborting")
            return

        # 2. Scrape all sources
        data = {"scraped_at": datetime.now().isoformat()}
        data["ders_programi"] = scrape_ders_programi(driver)
        data["odevlerim"] = scrape_odevlerim(driver)
        data["takim_calismalari"] = scrape_takim_calismalari(driver)
        data["takvim"] = scrape_takvim(driver)
        data["ders_icerikleri"] = scrape_ders_icerikleri(driver)
        data["ogep"] = scrape_ogep(driver)

        # Save scraped data
        out_path = os.path.join(OUTPUT_DIR, "scraped_data.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    finally:
        driver.quit()

    # 3. Smart sync to Google
    print("\n--- Google Sync ---")
    cal_service, tasks_service = get_services()
    cal_id = get_or_create_calendar(cal_service, "TED Rönesans")
    task_list_id = get_or_create_task_list(tasks_service, "TED Ödevler")

    existing_events = fetch_existing_events(cal_service, cal_id)
    existing_tasks = fetch_existing_tasks(tasks_service, task_list_id)
    print(f"  Existing: {len(existing_events)} events, {len(existing_tasks)} tasks")

    sync_ders_programi(cal_service, data, cal_id, existing_events)
    sync_odevlerim(cal_service, tasks_service, data, cal_id, task_list_id,
                   existing_events, existing_tasks)
    sync_takim_calismalari(cal_service, data, cal_id, existing_events)
    sync_takvim(cal_service, data, cal_id, existing_events)
    sync_ders_icerikleri(tasks_service, data, task_list_id, existing_tasks)
    sync_ogep(cal_service, data, cal_id, existing_events)

    elapsed = time.time() - start_time
    print(f"\n[DONE] Completed in {elapsed:.0f}s")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
```

**Step 2: Test manually**

Run: `cd /mnt/pi-shared/projects/TED && .venv/bin/python src/run_sync.py`
Expected: Scrapes all 6 sources, syncs with upsert, shows added/skipped counts.

**Step 3: Run again to confirm idempotency**

Run same command again.
Expected: All events show "skipped", 0 "added".

---

### Task 6: Clear old events (one-time) and re-sync with source tags

**Step 1: Delete all existing TED Rönesans events (they lack source tag)**

Run a one-time cleanup script:
```python
# Inline script to clear all events from TED Rönesans calendar
# Then run_sync.py will re-create them with source=ted-portal tags
```

Run: `cd /mnt/pi-shared/projects/TED && .venv/bin/python -c "<cleanup_script>"`

**Step 2: Delete all existing TED Ödevler tasks (they lack identification)**

Same approach for tasks.

**Step 3: Run run_sync.py to recreate everything with source tags**

Run: `cd /mnt/pi-shared/projects/TED && .venv/bin/python src/run_sync.py`
Expected: All events created fresh with `extendedProperties.private.source=ted-portal`

**Step 4: Run again to verify idempotency**

Run: `cd /mnt/pi-shared/projects/TED && .venv/bin/python src/run_sync.py`
Expected: 0 added, all skipped

---

### Task 7: Set up crontab

**Step 1: Install the crontab entry**

```bash
(crontab -l 2>/dev/null; echo "*/15 * * * * cd /mnt/pi-shared/projects/TED && .venv/bin/python src/run_sync.py >> output/sync.log 2>&1") | crontab -
```

**Step 2: Verify crontab is installed**

Run: `crontab -l`
Expected: Shows the `*/15 * * * *` entry.

**Step 3: Wait ~15 minutes and check the log**

Run: `tail -30 /mnt/pi-shared/projects/TED/output/sync.log`
Expected: One complete run logged with timestamp and summary.

**Step 4: Commit all changes**

```bash
cd /mnt/pi-shared/projects/TED
git add src/run_sync.py src/scrape_all.py src/sync_to_google.py docs/plans/
git commit -m "feat: add crontab auto-sync with smart deduplication

- Add run_sync.py orchestrator for 15-min cron automation
- Add upsert logic to sync_to_google.py (extendedProperties source tag)
- Add ÖGEP scraping to scrape_all.py
- No duplicate events on repeated runs"
```
