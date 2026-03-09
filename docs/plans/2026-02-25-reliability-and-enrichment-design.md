# TED System Hardening & AI Enrichment Expansion

**Date:** 2026-02-25
**Status:** Approved

## Problem

The TED sync system has critical reliability gaps (silent failures, no retry, no monitoring) and untapped AI enrichment potential (only ödev events enriched; sınav, ders içerikleri, performans data ignored).

## Design

### Phase 1: Reliability Foundation

#### 1a. Scraper Error Isolation (`run_sync.py`)
Wrap each of the 8 scraper calls in try-except. On failure: log error, continue with remaining scrapers, save partial data.

```python
errors = []
for name, fn in scrapers:
    try:
        fn(driver, data)
    except Exception as e:
        errors.append(f"{name}: {e}")
        print(f"[ERROR] {name} failed: {e}")
# Save partial data regardless
save_json(data)
```

#### 1b. API Retry (`sync_to_google.py`)
Add retry with exponential backoff to `upsert_event()` and `upsert_task()`. 3 attempts, 1s/2s/4s delays. Only retry on transient errors (5xx, timeout, rate limit).

```python
for attempt in range(3):
    try:
        cal_service.events().insert(...).execute()
        return "added"
    except HttpError as e:
        if e.resp.status in (429, 500, 503) and attempt < 2:
            time.sleep(2 ** attempt)
            continue
        return "error"
```

#### 1c. Health Check (`output/health.json`)
After each sync, write status file:

```json
{
  "timestamp": "2026-02-25T14:30:00",
  "success": true,
  "scrape_errors": [],
  "sync_errors": 0,
  "events_added": 12,
  "tasks_added": 3,
  "duration_seconds": 161
}
```

#### 1d. Atomic JSON Writes
All JSON output (scraped_data.json, tracker files) written to `.tmp` then renamed:

```python
with open(path + ".tmp", "w") as f:
    json.dump(data, f)
os.replace(path + ".tmp", path)
```

#### 1e. Credentials to .env
Move portal username/password from hardcoded `login.py` to `.env`:

```
PORTAL_USERNAME=isik.kurt
PORTAL_PASSWORD=...
GEMINI_API_KEY=...
```

Shared `.env` loader extracted to small utility used by both `login.py` and `enrich_gemini.py`.

### Phase 2: AI Enrichment Expansion

#### 2a. Rename & Extend Script
`enrich_odev_gemini.py` → `enrich_gemini.py` with new functions:

**`enrich_sinav()`** — Exam prep notes for sınav calendar events:
- Source: takvim events with "sınav"/"test"/"exam" keywords + gelisim_raporu grades
- Prompt: "Bu sınav için çalışma rehberi hazırla. Önceki not: {grade}. Zayıf alanları belirle, 3 günlük çalışma planı yaz."
- Marker: `🤖 Sınav Rehberi`
- Target: Calendar event descriptions (same as ödev enrichment)

**`enrich_ders_icerikleri()`** — Weekly course content summaries:
- Source: ders_icerikleri from scraped_data.json (text + cards, 17 courses)
- Prompt: "Bu haftanın {ders} konularını özetle. Temel kavramlar, önemli noktalar, bağlantılar."
- Marker: `🤖 Haftalık Özet`
- Target: Tasks descriptions (update existing "📖 X - Haftalık İçerik" tasks)

**`enrich_performans()`** — Grade performance narrative:
- Source: gelisim_raporu grades (11 courses, 3 exams + 3 performance)
- Prompt: "Bu öğrencinin sınav notlarını analiz et. En iyi 3 ders, iyileştirme gereken 2 ders, genel eğilim, tavsiyeler."
- Marker: `🤖 Performans Analizi`
- Target: Single task in "TED Ödevler" list (created/updated)
- Frequency: Once per sync (not per-event)

#### 2b. Shared Infrastructure
Extract from current `enrich_odev_gemini.py`:
- `ModelRouter` class (Gemini + Ollama fallback)
- `.env` loader
- Rate limiting logic
- Calendar/Tasks API helpers

Keep in single file (`enrich_gemini.py`) — no need for separate base module.

### Phase 3: Pipeline Integration

Add to `run_sync.py` after Google sync:

```python
# Phase 3: AI Enrichment (optional)
if not args.no_enrich:
    from enrich_gemini import enrich_all
    enrich_all(token_file=TOKEN_FILE)
    if os.path.exists(TOKEN_HURIYE):
        enrich_all(token_file=TOKEN_HURIYE)
```

`enrich_all()` calls each enrichment function in sequence, respecting rate limits and model quotas.

## Non-Goals

- Structured logging migration (future work)
- Email/push notifications (future work)
- Textbook content integration (OCR quality too low currently)
- Per-scraper subprocess isolation (over-engineering)

## File Changes

| File | Change |
|------|--------|
| `src/run_sync.py` | Try-except per scraper, health check, enrich phase |
| `src/sync_to_google.py` | Retry logic in upsert_event/task, atomic JSON |
| `src/login.py` | Read credentials from .env |
| `src/enrich_odev_gemini.py` → `src/enrich_gemini.py` | Rename, add sinav/ders/performans enrichment |
| `.env` | Add PORTAL_USERNAME, PORTAL_PASSWORD |

## Success Criteria

- A single scraper failure does NOT crash the entire sync
- Google API transient errors are retried (up to 3x)
- `output/health.json` shows last sync status
- Sınav events have AI study guides
- Ders içerikleri tasks have AI summaries
- A performance narrative task exists with grade analysis
- Enrichment runs automatically as part of sync pipeline
