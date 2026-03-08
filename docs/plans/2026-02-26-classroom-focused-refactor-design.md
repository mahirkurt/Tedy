# Classroom-Focused Refactor Design

## Goal

Refactor the TED sync pipeline so Google Classroom is the primary destination for educational data (homework, grades, course content, announcements), keeping Calendar only for timed events (schedule, ÖGEP, calendar activities with start/end times). Remove Tasks and Sheets entirely.

## Approach: A — Slim sync_to_google.py + Expand sync_to_classroom.py

Two modules, two responsibilities: Calendar vs Classroom. Shared utilities stay in sync_to_google.py.

## Architecture

### New Data Flow

```
TED Portal → scrape_all.py → scraped_data.json
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            sync_to_google.py  sync_to_classroom.py  enrich_gemini.py
            (Calendar + Drive)  (Classroom)          (→ Classroom)
                    │               │
                    ▼               ▼
            isikkurtx Calendar  huriye Classroom
            (ders programı,     (ödev, not, ders
             ögep, saatli        içeriği, duyuru,
             takvim)             takım, all-day
                                 takvim, Drive links)
```

### sync_to_google.py — Slim (Calendar + Drive only)

**Stays:**
- `normalize_course()` + `COURSE_ALIASES` (shared by both modules)
- `_api_call_with_retry()` (shared by both modules)
- `get_services()` → returns `(calendar, drive)` only — no tasks/sheets
- `sync_ders_programi()` → Calendar events (lavender)
- `sync_ogep()` → Calendar events (tangerine)
- `sync_takvim()` → Calendar events — **only events with start/end times** (filter out all-day)
- `sync_attachments_to_drive()` → upload homework attachments, return Drive URLs
- `fetch_existing_events()`, `upsert_event()` — Calendar CRUD
- `get_or_create_calendar()` — "TED Rönesans" calendar management

**Removed:**
- `sync_odevlerim()` — moved to Classroom courseWork
- `sync_takim_calismalari()` — moved to Classroom announcement
- `sync_ders_icerikleri()` — already in Classroom
- `sync_duyurular()` — moved to Classroom announcement
- `sync_gelisim_raporu()` — moved to Classroom grade
- `sync_grades_to_sheets()` — Sheets removed entirely
- All Tasks functions (`get_or_create_task_list`, `fetch_existing_tasks`, `upsert_task`)
- All Sheets functions
- Huriye account Calendar sync (only isikkurtx)

**Token:** `token.json` (isikkurtx) only.

### sync_to_classroom.py — Expanded

**Existing (unchanged):**
- `ensure_courses()` — course creation with ALLOWED_COURSES whitelist
- `sync_odevler()` → courseWork ASSIGNMENT
- `sync_ders_icerikleri()` → announcement per course
- `sync_notlar()` → courseWork SHORT_ANSWER with grades
- `sync_duyurular()` → announcement (duyurular + takvim + takım + ögep)
- Hash-based dedup via `classroom_sync.json`
- Student invitation (`isikkurtx@gmail.com`)

**New:**
1. **Drive materials links in courseWork:**
   - `sync_odevler()` calls `sync_to_google.sync_attachments_to_drive()` first
   - Adds `materials: [{link: {url, title}}]` to courseWork body
   - Tracks upload state to avoid re-uploading

2. **All-day takvim events as Classroom announcements:**
   - `sync_duyurular()` already handles takvim data
   - sync_to_google.py's `sync_takvim()` will filter to only timed events
   - All-day events flow to Classroom via existing duyurular sync

**Token:** `token_huriye.json` (huriye.murzoglu@gmail.com) — unchanged.

### enrich_gemini.py — Adapted to Classroom

**Current targets → New targets:**
- Ödev notları (`🤖 Gemini Notu`) → Classroom courseWork description (append)
- Sınav rehberleri (`🤖 Sınav Rehberi`) → Classroom courseWork description (append)
- Ders özetleri (`🤖 Haftalık Özet`) → Classroom announcement text (append)
- Performans analizi (`🤖 Performans Analizi`) → Classroom course announcement (new)

**Mechanism:** Read `classroom_sync.json` to find Classroom IDs, patch via Classroom API.
**Idempotency:** Same marker string approach — check if `🤖` marker already present in text.

### run_sync.py — Updated Pipeline

```
1. Login
2. Scrape all (8 sources — unchanged)
3. Save scraped_data.json
4. sync_to_google → Calendar (ders programı, ögep, timed takvim) + Drive (attachments)
5. sync_to_classroom → Classroom (ödev+drive links, notlar, ders içeriği, duyuru, takım, all-day takvim)
6. enrich_gemini → Classroom (patch descriptions)
7. Health check
```

### google_auth.py — Scope Cleanup

**Remove:** `tasks`, `spreadsheets`
**Keep:** `calendar`, `drive.file`, `classroom.*`

### Test Changes

- Remove: Tasks/Sheets test cases from `test_main.py`
- Narrow: Calendar tests to ders_programi, ogep, timed takvim only
- Add: Drive materials link tests in `test_sync_to_classroom.py`
- Add: Enrichment → Classroom tests in `test_enrich_gemini.py`

## Decisions Log

| Question | Decision |
|----------|----------|
| Calendar scope | Keep for timed events only (ders programı, ÖGEP, timed takvim) |
| AI enrichment | Adapt to write to Classroom instead of Calendar/Tasks |
| Calendar accounts | isikkurtx only |
| Drive | Keep — upload attachments, link as Classroom materials |
| Tasks | Remove entirely |
| Sheets | Remove entirely |
| Approach | A — slim sync_to_google + expand sync_to_classroom |
