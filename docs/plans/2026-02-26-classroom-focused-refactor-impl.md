# Classroom-Focused Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor sync pipeline so Classroom is primary target, Calendar kept only for timed events, Tasks/Sheets removed entirely.

**Architecture:** Slim `sync_to_google.py` to Calendar+Drive only (ders programı, ögep, timed takvim, attachments). Expand `sync_to_classroom.py` with Drive materials links. Adapt `enrich_gemini.py` to write to Classroom API instead of Calendar/Tasks. Update `run_sync.py` pipeline and `google_auth.py` scopes.

**Tech Stack:** Python, Google API (Calendar v3, Classroom v1, Drive v3), pytest

---

### Task 1: Slim sync_to_google.py — Remove Tasks/Sheets Functions and Exports

This is the biggest change. Remove all Tasks, Sheets, and Classroom-moved sync functions from `sync_to_google.py`.

**Files:**
- Modify: `src/sync_to_google.py`
- Test: `pytest tests/ -v` (existing tests should still pass after cleanup)

**Step 1: Remove Tasks-related functions**

Delete these functions entirely from `src/sync_to_google.py`:
- `get_or_create_task_list()` (lines 135-145)
- `fetch_existing_tasks()` (lines 174-196)
- `upsert_task()` (lines 259-297)

**Step 2: Remove sync functions that moved to Classroom**

Delete these functions entirely:
- `sync_odevlerim()` (lines 440-556) — moved to Classroom courseWork
- `sync_takim_calismalari()` (lines 562-605) — moved to Classroom announcements
- `sync_ders_icerikleri()` (lines 686-716) — already in Classroom
- `sync_gelisim_raporu()` (lines 765-807) — moved to Classroom grades
- `sync_duyurular()` (lines 813-860) — moved to Classroom announcements

**Step 3: Remove Sheets-related functions**

Delete everything from line 863 to line 1070:
- `SHEETS_ID_FILE` constant
- `_get_or_create_spreadsheet()`
- `sync_grades_to_sheets()`
- `_apply_grade_formatting()`

**Step 4: Update `get_services()` to return only (calendar, drive)**

Change `get_services()` at line 106-118:

```python
def get_services(token_file=None):
    """Build Google API service clients from token file."""
    token_file = token_file or TOKEN_FILE
    creds = Credentials.from_authorized_user_file(token_file)
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_file, "w") as f:
            f.write(creds.to_json())
    cal = build("calendar", "v3", credentials=creds)
    drive = build("drive", "v3", credentials=creds)
    return cal, drive
```

**Step 5: Remove TOKEN_HURIYE constant and multi-account from standalone main**

Remove `TOKEN_HURIYE` constant (line 16). Update `_sync_account()` to only use calendar and drive. Remove the huriye account section from `main()`.

Rewrite `_sync_account()`:

```python
def _sync_account(data, token_file, label):
    """Run Calendar + Drive sync for a single Google account."""
    print(f"\n{'=' * 50}")
    print(f"SYNC: {label}")
    print(f"{'=' * 50}")

    print("Connecting to Google APIs...")
    cal_svc, drive_svc = get_services(token_file=token_file)

    print("\nSetting up Google Calendar...")
    cal_id = get_or_create_calendar(cal_svc, "TED Rönesans")

    print("Fetching existing events for dedup...")
    existing_events = fetch_existing_events(cal_svc, cal_id)
    print(f"  Found {len(existing_events)} existing events")

    sync_ders_programi(cal_svc, data, cal_id, existing_events)
    sync_takvim(cal_svc, data, cal_id, existing_events)
    sync_ogep(cal_svc, data, cal_id, existing_events)
    sync_attachments_to_drive(drive_svc, data)
```

Rewrite `main()`:

```python
def main():
    print("Loading scraped data...")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    _sync_account(data, TOKEN_FILE, "Primary Account")

    print("\n" + "=" * 50)
    print("SYNC COMPLETE!")
    print("=" * 50)
```

**Step 6: Update sync_takvim to only sync timed events**

In `sync_takvim()`, skip all-day events (they go to Classroom announcements now). Change the function to filter out `allDay` events:

```python
def sync_takvim(cal_service, data, cal_id, existing_events):
    """Sync timed calendar events to Google Calendar.

    All-day events are handled by Classroom announcements.
    Only events with specific start/end times are synced here.
    """
    print("\n[2/3] Akademik Takvim (saatli) -> Calendar")
    events = data.get("takvim", [])
    events_added = 0
    events_skipped = 0
    all_day_skipped = 0

    for ev in events:
        title = ev.get("title", "").strip()
        start = ev.get("start", "")
        end = ev.get("end", "")
        all_day = ev.get("allDay", False)

        if not title or not start:
            continue

        # Skip all-day events — they go to Classroom announcements
        if all_day:
            all_day_skipped += 1
            continue

        # Determine color by keyword
        color = COLORS["etkinlik"]
        lower = title.lower()
        if "sınav" in lower or "test" in lower or "exam" in lower:
            color = COLORS["sinav"]
        elif "ögep" in lower or "ogep" in lower:
            color = COLORS["ogep"]
        elif any(w in lower for w in TAKVIM_DERS_KEYWORDS):
            color = COLORS["ders"]
        elif "gezi" in lower or "müze" in lower or "trip" in lower:
            color = COLORS["takim"]

        event = {
            "summary": title,
            "colorId": color,
            "start": {
                "dateTime": start,
                "timeZone": TIMEZONE,
            },
            "end": {
                "dateTime": end if end else start,
                "timeZone": TIMEZONE,
            },
        }

        result = upsert_event(cal_service, cal_id, event, existing_events)
        if result == "added":
            events_added += 1
        elif result == "exists":
            events_skipped += 1

    print(f"  Takvim: +{events_added} added, ={events_skipped} skipped, "
          f"~{all_day_skipped} all-day -> Classroom")
    return events_added
```

**Step 7: Simplify sync_attachments_to_drive signature**

Remove `cal_service` and `cal_id` params (no longer updates calendar events). Return the `uploaded` dict so Classroom can use Drive links:

```python
def sync_attachments_to_drive(drive_service, data):
    """Download homework attachments and upload to Google Drive.

    Returns dict: {url: {"id": drive_id, "link": web_link, "ders": course}}
    """
    print("\n[Drive] Attachments -> Google Drive")

    hw_data = data.get("odevlerim", {})
    rows = hw_data.get("homework", {}).get("rows", [])

    # Collect all attachments
    attachments = []
    for row in rows:
        detail = row.get("detail", {})
        for att in detail.get("attachments", []):
            url = att.get("url", "")
            name = att.get("name", "")
            ders = normalize_course(row.get("Ders Adı", "Genel"))
            if url and name:
                attachments.append({
                    "url": url, "name": name, "ders": ders,
                })

    if not attachments:
        print("  No attachments found, skipping")
        return {}

    # Load already-uploaded files
    uploaded = {}
    if os.path.exists(UPLOADED_FILES):
        with open(UPLOADED_FILES) as f:
            uploaded = json.load(f)

    # Get or create root folder
    folder_id = _get_or_create_folder(drive_service, "Ödevler")

    added = 0
    skipped = 0
    for att in attachments:
        if att["url"] in uploaded:
            skipped += 1
            continue

        try:
            import requests as req
            resp = req.get(att["url"], timeout=30)
            if resp.status_code != 200:
                continue

            subj_folder = _get_or_create_folder(
                drive_service, att["ders"], parent_id=folder_id
            )

            from googleapiclient.http import MediaInMemoryUpload
            media = MediaInMemoryUpload(
                resp.content,
                mimetype=resp.headers.get(
                    "Content-Type", "application/octet-stream"
                ),
            )
            file_meta = {
                "name": att["name"],
                "parents": [subj_folder],
            }
            result = drive_service.files().create(
                body=file_meta, media_body=media,
                fields="id,webViewLink",
            ).execute()

            uploaded[att["url"]] = {
                "id": result["id"],
                "link": result.get("webViewLink", ""),
                "ders": att["ders"],
            }
            added += 1
        except Exception as e:
            print(f"  Error uploading {att['name']}: {e}")

    from src.json_utils import atomic_json_dump
    atomic_json_dump(uploaded, UPLOADED_FILES)

    print(f"  Drive: +{added} uploaded, ={skipped} skipped")
    return uploaded
```

**Step 8: Update print labels**

Renumber sync function labels:
- `sync_ders_programi`: `[1/3]`
- `sync_takvim`: `[2/3]`
- `sync_ogep`: `[3/3]`

**Step 9: Remove unused COLORS**

Remove `"odev"` from COLORS dict (no longer creating ödev calendar events). Keep: `ders`, `takim`, `sinav`, `etkinlik`, `ogep`.

**Step 10: Run tests**

Run: `pytest tests/ -v`
Expected: Some tests may fail due to removed functions — that's expected and will be fixed in Task 5.

**Step 11: Commit**

```bash
git add src/sync_to_google.py
git commit -m "refactor: slim sync_to_google.py to Calendar+Drive only

Remove Tasks, Sheets, and Classroom-bound sync functions.
Keep: ders_programi, timed takvim, ogep, attachments_to_drive.
sync_takvim now skips all-day events (handled by Classroom).
get_services returns (calendar, drive) instead of 4 services."
```

---

### Task 2: Update sync_to_classroom.py — Add Drive Materials Links

**Files:**
- Modify: `src/sync_to_classroom.py`
- Test: `tests/test_classroom_sync.py`

**Step 1: Write failing test for Drive materials in courseWork**

Add to `tests/test_classroom_sync.py`:

```python
class TestSyncOdevlerWithDrive:
    def _mock_service(self):
        svc = MagicMock()
        svc.courses().courseWork().create.return_value.execute.return_value = {"id": "cw1"}
        return svc

    def test_adds_drive_materials_to_coursework(self):
        from src.sync_to_classroom import sync_odevler
        svc = self._mock_service()
        courses = {"Matematik": "c1", "TED Genel": "cg"}
        data = {
            "odevlerim": {
                "homework": {
                    "headers": [],
                    "rows": [{
                        "Ders Adı": "Matematik",
                        "Ödev Başlığı": "Test Ödevi",
                        "Ödev Son Teslim Tarihi": "27.02.2026 12:00",
                        "Ödev Durumu": "",
                        "detail": {
                            "description": "Sayfa 10",
                            "attachments": [
                                {"url": "http://example.com/file.pdf", "name": "dosya.pdf"}
                            ]
                        }
                    }]
                }
            }
        }
        # Simulate uploaded Drive files
        drive_uploads = {
            "http://example.com/file.pdf": {
                "id": "drv_123",
                "link": "https://drive.google.com/file/d/drv_123/view",
                "ders": "Matematik",
            }
        }
        state = {}
        result = sync_odevler(svc, courses, data, state, drive_uploads=drive_uploads)
        assert result["added"] == 1

        # Verify materials were included in the body
        create_call = svc.courses().courseWork().create
        call_args = create_call.call_args
        # The body is passed via lambda, check the state instead
        assert "cw:c1:Test Ödevi" in state
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_classroom_sync.py::TestSyncOdevlerWithDrive -v`
Expected: FAIL — `sync_odevler` doesn't accept `drive_uploads` parameter yet.

**Step 3: Update sync_odevler to accept and use drive_uploads**

Modify `sync_odevler()` signature and body in `src/sync_to_classroom.py`:

```python
def sync_odevler(service, courses, data, state, drive_uploads=None):
    """Sync homework to Classroom as courseWork (ASSIGNMENT).

    Args:
        drive_uploads: Dict from sync_attachments_to_drive, mapping
            attachment URLs to Drive file info {id, link, ders}.

    Returns dict: {added, updated, skipped, errors}
    """
    drive_uploads = drive_uploads or {}
    result = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
    rows = (data.get("odevlerim", {})
                .get("homework", {})
                .get("rows", []))

    for row in rows:
        ders = row.get("Ders Adı", "")
        baslik = row.get("Ödev Başlığı", "")
        course_id = _resolve_course_id(courses, ders)
        if not course_id:
            result["errors"] += 1
            continue

        dedup_key = f"cw:{course_id}:{baslik}"
        current_hash = compute_hash(row)

        existing = state.get(dedup_key)
        if existing and existing["last_hash"] == current_hash:
            result["skipped"] += 1
            continue

        description = row.get("detail", {}).get("description", "")
        durum = row.get("Ödev Durumu", "")
        if durum:
            description = f"Durum: {durum}\n\n{description}"

        body = {
            "title": baslik,
            "description": description[:2000],
            "workType": "ASSIGNMENT",
            "state": "PUBLISHED",
        }

        due_str = row.get("Ödev Son Teslim Tarihi", "")
        due_date, due_time = _parse_turkish_datetime(due_str)
        if due_date:
            body["dueDate"] = due_date
            body["dueTime"] = due_time

        # Build materials list: portal links + Drive uploads
        materials = []
        attachments = row.get("detail", {}).get("attachments", [])
        for att in attachments:
            url = att.get("url", "")
            name = att.get("name", "Ek")
            # Prefer Drive link if uploaded, otherwise use original URL
            drive_info = drive_uploads.get(url)
            if drive_info and drive_info.get("link"):
                materials.append({
                    "link": {"url": drive_info["link"], "title": f"📁 {name}"}
                })
            elif url:
                materials.append({
                    "link": {"url": url, "title": name}
                })
        if materials:
            body["materials"] = materials

        if existing:
            cw_id = existing["classroom_id"]
            updated = _api_call_with_retry(
                lambda cid=course_id, cwid=cw_id, b=body: (
                    service.courses().courseWork().patch(
                        courseId=cid, id=cwid,
                        updateMask="title,description,dueDate,dueTime,materials",
                        body=b,
                    ).execute()
                )
            )
            if updated:
                state[dedup_key] = {"classroom_id": cw_id, "last_hash": current_hash}
                result["updated"] += 1
            else:
                result["errors"] += 1
        else:
            created = _api_call_with_retry(
                lambda cid=course_id, b=body: (
                    service.courses().courseWork().create(
                        courseId=cid, body=b,
                    ).execute()
                )
            )
            if created:
                state[dedup_key] = {"classroom_id": created["id"], "last_hash": current_hash}
                result["added"] += 1
            else:
                result["errors"] += 1

    print(f"  Ödevler: +{result['added']} ~{result['updated']} "
          f"={result['skipped']} !{result['errors']}")
    return result
```

**Step 4: Run tests**

Run: `pytest tests/test_classroom_sync.py -v`
Expected: All pass including new test.

**Step 5: Commit**

```bash
git add src/sync_to_classroom.py tests/test_classroom_sync.py
git commit -m "feat: add Drive materials links to Classroom courseWork"
```

---

### Task 3: Update run_sync.py Pipeline

**Files:**
- Modify: `src/run_sync.py`

**Step 1: Update imports**

Replace current imports from `sync_to_google`:

```python
from src.sync_to_google import (
    get_services, get_or_create_calendar,
    fetch_existing_events,
    sync_ders_programi, sync_takvim, sync_ogep,
    sync_attachments_to_drive,
)
```

**Step 2: Rewrite the Google sync section (step 3 in pipeline)**

```python
    # 3. Calendar + Drive sync (isikkurtx only)
    try:
        print("\n--- Google Calendar + Drive Sync ---")
        cal_svc, drive_svc = get_services()
        cal_id = get_or_create_calendar(cal_svc, "TED Rönesans")
        existing_events = fetch_existing_events(cal_svc, cal_id)
        print(f"  Existing: {len(existing_events)} events")

        sync_ders_programi(cal_svc, data, cal_id, existing_events)
        sync_takvim(cal_svc, data, cal_id, existing_events)
        sync_ogep(cal_svc, data, cal_id, existing_events)
        drive_uploads = sync_attachments_to_drive(drive_svc, data)
    except Exception as e:
        scrape_errors.append(f"google_sync: {e}")
        print(f"[ERROR] Google sync failed: {e}")
        drive_uploads = {}
```

**Step 3: Update Classroom sync to pass drive_uploads**

```python
    # 4. Classroom sync (huriye account)
    try:
        from src.sync_to_classroom import main as sync_classroom
        sync_classroom(scraped_data=data, drive_uploads=drive_uploads)
    except Exception as e:
        scrape_errors.append(f"classroom_sync: {e}")
        print(f"[WARN] Classroom sync failed: {e}")
```

**Step 4: Update enrichment section — remove Calendar/Tasks enrichment**

The enrichment section will be rewritten in Task 4. For now, comment it out or make it a no-op to avoid import errors:

```python
    # 5. AI Enrichment (adapted to Classroom — will be updated in Task 4)
    print("\n--- AI Enrichment ---")
    try:
        from src.enrich_gemini import enrich_all
        enrich_all()
    except Exception as e:
        print(f"[WARN] Enrichment failed: {e}")
```

**Step 5: Update sync_to_classroom.main() to accept drive_uploads**

In `src/sync_to_classroom.py`, update `main()`:

```python
def main(scraped_data=None, token_file=None, reset_courses=False,
         drive_uploads=None):
    """Main entry point for Classroom sync.

    Args:
        scraped_data: Pre-loaded data dict. If None, reads from DATA_FILE.
        token_file: OAuth token file path.
        reset_courses: If True, delete and recreate all courses.
        drive_uploads: Dict from sync_attachments_to_drive for materials links.
    """
```

And pass `drive_uploads` to `sync_odevler`:

```python
    sync_odevler(service, courses, scraped_data, state,
                 drive_uploads=drive_uploads)
```

**Step 6: Run tests**

Run: `pytest tests/ -v`
Expected: PASS (test_main.py may need adjustment)

**Step 7: Commit**

```bash
git add src/run_sync.py src/sync_to_classroom.py
git commit -m "refactor: update run_sync.py pipeline for Classroom-first sync

Calendar+Drive sync only creates timed events and uploads attachments.
Classroom sync receives drive_uploads for materials linking.
Removed Tasks/Sheets/huriye Calendar sync from pipeline."
```

---

### Task 4: Adapt enrich_gemini.py to Write to Classroom

This is the most complex task — rewriting 4 enrichment functions to target Classroom instead of Calendar/Tasks.

**Files:**
- Modify: `src/enrich_gemini.py`
- Modify: `tests/test_enrich.py`

**Step 1: Write failing tests for Classroom enrichment**

Add to `tests/test_enrich.py`:

```python
class TestClassroomEnrichmentTargets:
    """Verify enrichment functions target Classroom API."""

    def test_enrich_all_uses_classroom_service(self):
        """enrich_all should build a Classroom service, not Calendar/Tasks."""
        from unittest.mock import patch, MagicMock
        with patch("src.enrich_gemini.get_classroom_service") as mock_cls, \
             patch("src.enrich_gemini.get_services") as mock_svc, \
             patch("src.enrich_gemini.load_sync_state", return_value={}), \
             patch("src.enrich_gemini.ModelRouter") as mock_router, \
             patch("src.enrich_gemini.genai") as mock_genai, \
             patch("src.enrich_gemini.load_env"), \
             patch.dict("os.environ", {"GEMINI_API_KEY": "test"}), \
             patch("builtins.open", side_effect=FileNotFoundError):
            try:
                from src.enrich_gemini import enrich_all
                enrich_all()
            except Exception:
                pass
            # Should attempt to use Classroom service
            mock_cls.assert_called()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_enrich.py::TestClassroomEnrichmentTargets -v`
Expected: FAIL — `enrich_gemini` currently uses `get_services()` for Calendar/Tasks.

**Step 3: Rewrite enrich_gemini.py**

Replace Calendar/Tasks targeting with Classroom API:

**Imports section** — replace `get_services, get_or_create_calendar` with Classroom imports:

```python
from src.sync_to_classroom import (
    get_classroom_service, load_sync_state, save_sync_state,
    _api_call_with_retry,
)
from src.sync_to_google import normalize_course, _ALIAS_LONGEST_FIRST, _ALIAS_LOOKUP
```

**Rewrite `_enrich_odev()`** to patch Classroom courseWork descriptions:

```python
def _enrich_odev(classroom_service, sync_state, router, force=False):
    """Enrich ödev courseWork with AI study notes via Classroom API."""
    hw_lookup = load_homework_details()
    total_hw = sum(len(v) for v in hw_lookup.values())
    print(f"Scraped homework items loaded: {total_hw}")

    enriched = 0
    skipped = 0
    errors = 0

    for key, info in sync_state.items():
        if not key.startswith("cw:"):
            continue
        # key format: "cw:{course_id}:{baslik}"
        parts = key.split(":", 2)
        if len(parts) < 3:
            continue
        course_id = parts[1]
        baslik = parts[2]

        classroom_id = info.get("classroom_id")
        if not classroom_id:
            continue

        # Fetch current courseWork to check description
        try:
            cw = _api_call_with_retry(
                lambda cid=course_id, cwid=classroom_id: (
                    classroom_service.courses().courseWork().get(
                        courseId=cid, id=cwid,
                    ).execute()
                )
            )
        except Exception:
            skipped += 1
            continue

        if not cw:
            skipped += 1
            continue

        desc = cw.get("description", "") or ""
        if GEMINI_MARKER in desc:
            if not force:
                skipped += 1
                continue
            desc = desc.split(GEMINI_MARKER)[0]

        # Find matching homework for context
        hw_row = find_matching_hw(hw_lookup, baslik, "")
        hw_desc = ""
        hw_attachments = []
        if hw_row:
            detail = hw_row.get("detail", {})
            hw_desc = detail.get("description", "")
            hw_attachments = detail.get("attachments", [])

        # Guess course from courseWork title or baslik
        ders = cw.get("title", baslik)

        prompt = build_prompt(ders, baslik, hw_desc, hw_attachments, "")
        try:
            note = router.generate(prompt)
        except RuntimeError as e:
            print(f"  ✗ {e}")
            break
        except Exception as e:
            print(f"  ✗ {baslik}: {e}")
            errors += 1
            continue

        new_desc = desc + GEMINI_MARKER + note
        updated = _api_call_with_retry(
            lambda cid=course_id, cwid=classroom_id, d=new_desc: (
                classroom_service.courses().courseWork().patch(
                    courseId=cid, id=cwid,
                    updateMask="description",
                    body={"description": d[:2000]},
                ).execute()
            )
        )
        if updated:
            enriched += 1
            print(f"  ✓ {baslik}")
        else:
            errors += 1

        time.sleep(router.delay)

    print(f"\n  Ödev: +{enriched} enriched, ={skipped} skipped, !{errors} errors")
```

**Rewrite `enrich_sinav()`** to patch Classroom courseWork descriptions for grade entries:

```python
def enrich_sinav(classroom_service, sync_state, router, grades_data):
    """Enrich grade courseWork entries with AI study guides."""
    grade_lookup = {}
    for row in grades_data:
        course = row.get("Ders", "")
        for key in ["3. Sınav", "2. Sınav", "1. Sınav"]:
            val = row.get(key, "-")
            if val and val != "-":
                grade_lookup[course] = val
                break

    enriched = 0
    skipped = 0

    for key, info in sync_state.items():
        if not key.startswith("grade:"):
            continue
        parts = key.split(":", 2)
        if len(parts) < 3:
            continue
        course_id = parts[1]
        col_name = parts[2]
        classroom_id = info.get("classroom_id")
        if not classroom_id:
            continue

        # Skip non-sınav grade columns
        if "Sınav" not in col_name:
            skipped += 1
            continue

        try:
            cw = _api_call_with_retry(
                lambda cid=course_id, cwid=classroom_id: (
                    classroom_service.courses().courseWork().get(
                        courseId=cid, id=cwid,
                    ).execute()
                )
            )
        except Exception:
            skipped += 1
            continue

        if not cw:
            skipped += 1
            continue

        desc = cw.get("description", "") or ""
        if SINAV_MARKER in desc:
            skipped += 1
            continue

        title = cw.get("title", "")
        # Extract course name from title "Not: Matematik - 1. Sınav"
        course = ""
        for alias in _ALIAS_LONGEST_FIRST:
            if alias.lower() in title.lower():
                course = _ALIAS_LOOKUP[alias]
                break

        last_grade = grade_lookup.get(course)
        prompt = build_sinav_prompt(title, "", course or "Bilinmiyor", last_grade)

        try:
            note = router.generate(prompt)
            new_desc = desc + SINAV_MARKER + note
            _api_call_with_retry(
                lambda cid=course_id, cwid=classroom_id, d=new_desc: (
                    classroom_service.courses().courseWork().patch(
                        courseId=cid, id=cwid,
                        updateMask="description",
                        body={"description": d[:2000]},
                    ).execute()
                )
            )
            enriched += 1
            print(f"  ✓ {title}")
        except Exception as e:
            print(f"  ✗ {title}: {e}")

        time.sleep(router.delay)

    print(f"  Sınav: +{enriched} enriched, ={skipped} skipped")
```

**Rewrite `enrich_ders_icerikleri()`** to patch Classroom announcement text:

```python
def enrich_ders_icerikleri(classroom_service, sync_state, router, ders_data):
    """Enrich ders içerikleri announcements with AI summaries."""
    enriched = 0
    skipped = 0

    for key, info in sync_state.items():
        if not key.startswith("mat:"):
            continue
        classroom_id = info.get("classroom_id")
        if not classroom_id:
            continue

        # Extract course_id from key "mat:{course_id}:{title}"
        parts = key.split(":", 2)
        if len(parts) < 3:
            continue
        course_id = parts[1]
        mat_title = parts[2]

        # Find matching ders content
        course_name = mat_title.replace(" - Haftalık İçerik", "")
        content = ""
        for raw_name, cinfo in ders_data.items():
            normalized = normalize_course(raw_name)
            if normalized == course_name:
                content = cinfo.get("text", "") if isinstance(cinfo, dict) else ""
                cards = cinfo.get("cards", []) if isinstance(cinfo, dict) else []
                if cards:
                    content += "\n" + "\n".join(str(c)[:300] for c in cards[:5])
                break

        if not content:
            skipped += 1
            continue

        # Fetch current announcement
        try:
            ann = _api_call_with_retry(
                lambda cid=course_id, aid=classroom_id: (
                    classroom_service.courses().announcements().get(
                        courseId=cid, id=aid,
                    ).execute()
                )
            )
        except Exception:
            skipped += 1
            continue

        if not ann:
            skipped += 1
            continue

        text = ann.get("text", "") or ""
        if DERS_MARKER in text:
            skipped += 1
            continue

        prompt = build_ders_icerikleri_prompt(course_name, content)
        try:
            summary = router.generate(prompt)
            new_text = text + DERS_MARKER + summary
            _api_call_with_retry(
                lambda cid=course_id, aid=classroom_id, t=new_text: (
                    classroom_service.courses().announcements().patch(
                        courseId=cid, id=aid,
                        updateMask="text",
                        body={"text": t[:2000]},
                    ).execute()
                )
            )
            enriched += 1
            print(f"  ✓ {mat_title}")
        except Exception as e:
            print(f"  ✗ {mat_title}: {e}")

        time.sleep(router.delay)

    print(f"  Ders İçerikleri: +{enriched} enriched, ={skipped} skipped")
```

**Rewrite `enrich_performans()`** to create Classroom announcement:

```python
def enrich_performans(classroom_service, courses_mapping, router, grades):
    """Create or update a performance analysis announcement in TED Genel."""
    if not grades:
        print("  No grades data, skipping performans")
        return

    genel_id = courses_mapping.get("TED Genel")
    if not genel_id:
        print("  No TED Genel course, skipping performans")
        return

    prompt = build_performans_prompt(grades)
    try:
        note = router.generate(prompt)
    except Exception as e:
        print(f"  ✗ Performans: {e}")
        return

    text = f"📊 Performans Analizi\n\n{note}"

    # Create as new announcement (idempotent check via text prefix)
    try:
        # Check if already exists
        result = _api_call_with_retry(
            lambda cid=genel_id: (
                classroom_service.courses().announcements().list(
                    courseId=cid,
                ).execute()
            )
        )
        for ann in (result or {}).get("announcements", []):
            if ann.get("text", "").startswith("📊 Performans Analizi"):
                # Update existing
                _api_call_with_retry(
                    lambda cid=genel_id, aid=ann["id"], t=text: (
                        classroom_service.courses().announcements().patch(
                            courseId=cid, id=aid,
                            updateMask="text",
                            body={"text": t[:2000], "state": "PUBLISHED"},
                        ).execute()
                    )
                )
                print(f"  ✓ Performans Analizi (updated)")
                return

        # Create new
        _api_call_with_retry(
            lambda cid=genel_id, t=text: (
                classroom_service.courses().announcements().create(
                    courseId=cid,
                    body={"text": t[:2000], "state": "PUBLISHED"},
                ).execute()
            )
        )
        print(f"  ✓ Performans Analizi (created)")
    except Exception as e:
        print(f"  ✗ Performans: {e}")
```

**Rewrite `enrich_all()`:**

```python
def enrich_all(token_file=None, force=False):
    """Run all enrichment functions targeting Classroom API."""
    from src.env_loader import load_env
    load_env()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found, skipping enrichment")
        return

    gemini = genai.Client(api_key=api_key)
    router = ModelRouter(gemini)
    print(f"\n[Enrich] Model: {router.current}")

    classroom_service = get_classroom_service(token_file)
    sync_state = load_sync_state()

    # Load scraped data
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    # Load courses mapping
    from src.sync_to_classroom import _load_courses_mapping
    courses_mapping = _load_courses_mapping()

    # 1. Ödev enrichment -> Classroom courseWork
    print("\n[Enrich] Ödev notları...")
    _enrich_odev(classroom_service, sync_state, router, force)

    # 2. Sınav enrichment -> Classroom courseWork
    print("\n[Enrich] Sınav rehberleri...")
    gelisim = data.get("gelisim_raporu", {})
    grades = gelisim.get("grades", []) if isinstance(gelisim, dict) else []
    enrich_sinav(classroom_service, sync_state, router, grades)

    # 3. Ders içerikleri enrichment -> Classroom announcements
    print("\n[Enrich] Ders özetleri...")
    ders_data = data.get("ders_icerikleri", {})
    enrich_ders_icerikleri(classroom_service, sync_state, router, ders_data)

    # 4. Performans enrichment -> Classroom announcement
    print("\n[Enrich] Performans analizi...")
    enrich_performans(classroom_service, courses_mapping, router, grades)
```

**Step 4: Update existing prompt tests to still pass**

The prompt builder functions (`build_prompt`, `build_sinav_prompt`, etc.) are unchanged — they're pure functions. The existing tests in `test_enrich.py` should still pass.

**Step 5: Run tests**

Run: `pytest tests/test_enrich.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/enrich_gemini.py tests/test_enrich.py
git commit -m "feat: adapt AI enrichment to write to Classroom API

Ödev notes -> Classroom courseWork description
Sınav guides -> Classroom grade courseWork description
Ders summaries -> Classroom announcement text
Performans analysis -> TED Genel announcement
Removed Calendar/Tasks dependencies from enrichment."
```

---

### Task 5: Update google_auth.py — Remove Tasks/Sheets Scopes

**Files:**
- Modify: `src/google_auth.py`
- Modify: `src/auth_finish.py`

**Step 1: Remove Tasks and Sheets scopes**

In `src/google_auth.py`, update SCOPES:

```python
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive.file",
    # Google Classroom scopes
    "https://www.googleapis.com/auth/classroom.courses",
    "https://www.googleapis.com/auth/classroom.coursework.students",
    "https://www.googleapis.com/auth/classroom.announcements",
    "https://www.googleapis.com/auth/classroom.rosters",
    "https://www.googleapis.com/auth/classroom.profile.emails",
]
```

**Step 2: Remove get_tasks_service function**

Delete `get_tasks_service()` (lines 82-85).

**Step 3: Remove Tasks test from __main__ block**

In the `__main__` block, remove the Tasks list test (lines 121-126). Keep only Calendar test.

**Step 4: Update auth_finish.py scopes**

In `src/auth_finish.py`, update SCOPES to match (remove tasks/spreadsheets).

**Step 5: Commit**

```bash
git add src/google_auth.py src/auth_finish.py
git commit -m "refactor: remove Tasks/Sheets scopes from OAuth config

Only Calendar, Drive, and Classroom scopes remain.
Tokens must be regenerated after this change."
```

---

### Task 6: Fix Tests — Remove Obsolete Tests, Update Remaining

**Files:**
- Modify: `tests/test_classroom_sync.py`
- Delete obsolete test expectations

**Step 1: Update TestSyncDersIcerikleri mock**

The `TestSyncDersIcerikleri` class mocks `courseWorkMaterials` (line 192-197) but `sync_ders_icerikleri` now uses `announcements`. Update:

```python
class TestSyncDersIcerikleri:
    def _mock_service(self):
        svc = MagicMock()
        svc.courses().announcements().create.return_value.execute.return_value = {"id": "a1"}
        svc.courses().announcements().patch.return_value.execute.return_value = {"id": "a1"}
        return svc
```

**Step 2: Run full test suite**

Run: `pytest tests/ -v`
Expected: All pass.

**Step 3: Commit**

```bash
git add tests/
git commit -m "test: fix test mocks for Classroom-focused refactor"
```

---

### Task 7: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update Architecture section**

Update the Core Modules table, Data Flow diagram, Key Patterns, and Required Credentials sections to reflect:
- `sync_to_google.py` now only handles Calendar + Drive
- Tasks/Sheets removed
- `enrich_gemini.py` targets Classroom
- `token_huriye.json` is only used for Classroom (not Calendar)
- Scopes no longer include tasks/spreadsheets

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for Classroom-focused architecture"
```

---

### Task 8: Final Integration Test

**Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: All pass.

**Step 2: Verify no import errors in pipeline**

Run: `python -c "from src.run_sync import main; print('Pipeline imports OK')"`
Run: `python -c "from src.sync_to_google import get_services, sync_ders_programi, sync_takvim, sync_ogep, sync_attachments_to_drive; print('sync_to_google OK')"`
Run: `python -c "from src.sync_to_classroom import main; print('sync_to_classroom OK')"`
Run: `python -c "from src.enrich_gemini import enrich_all; print('enrich_gemini OK')"`

Expected: All print OK with no ImportError.

**Step 3: Commit if any fixes needed**

```bash
git add -A
git commit -m "fix: resolve integration issues from refactor"
```
