# Crontab + Smart Sync Design

**Date:** 2026-02-16
**Status:** Approved

## Problem

The TED portal scraping scripts run manually and create duplicate events on every run.
Need automated 15-minute interval execution with intelligent deduplication.

## Solution

Crontab on the pi machine + smart upsert logic in sync functions.

## Architecture

```
crontab (*/15 * * * *)
  └── src/run_sync.py
        ├── 1. Login (Selenium + captcha OCR)
        ├── 2. Scrape (5 sources + ÖGEP)
        ├── 3. Smart Sync (upsert, no delete)
        └── 4. Log summary to output/sync.log
```

## Smart Sync Logic

Each event gets `extendedProperties.private.source = "ted-portal"` metadata.

Matching key: `(summary, start_datetime)`

For each scraped event:
- No match in Google → `insert`
- Match exists, content differs → `update`
- Match exists, content same → skip

No deletion of events that disappear from portal.

## Files Changed

1. `src/run_sync.py` (NEW) — orchestrator: login → scrape → smart sync → log
2. `src/sync_to_google.py` (MODIFY) — convert insert-only to upsert with dedup
3. `src/scrape_all.py` (MODIFY) — add ÖGEP scraping, make functions importable
4. Crontab entry on the pi

## Crontab

```
*/15 * * * * cd /mnt/pi-shared/projects/TED && .venv/bin/python src/run_sync.py >> output/sync.log 2>&1
```

## Logging

Each run logs: timestamp, events added/updated/skipped counts per category.
Log file: `output/sync.log`
