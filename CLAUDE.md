# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TED is a Python web scraping and automation system that extracts educational data from Turkish school platforms (TED Rönesans Portal, EBA, MEBI, SEBİTV) and syncs it to Google Workspace (Calendar, Tasks, Sheets, Drive). It runs as a scheduled cron job every 15 minutes.

## Commands

```bash
# Run full sync (scrape portal + sync to Google) — the primary operation
python src/run_sync.py

# Run individual scrapers
python src/scrape_all.py                # TED portal data (schedule, homework, grades, etc.)
python src/scrape_eba_textbooks.py      # EBA textbook PDFs → Drive
python src/scrape_mebi_videos.py        # MEBI course videos → Drive
python src/scrape_sebitv.py             # SEBİTV videos/PDFs → Drive
python src/scrape_sebitv_interactive.py  # SEBİTV interactive content (ZIPs) → Drive

# Tests
pytest                    # Run all tests
pytest tests/test_main.py # Single test file

# Google OAuth setup (first-time only)
python src/google_auth.py
```

## Architecture

### Two-Phase Pattern: Discovery → Download

All scrapers follow a consistent two-phase approach:

1. **Selenium Discovery** — Headless Chrome logs in (CAPTCHA solved via `ddddocr` OCR), navigates the SPA, extracts metadata/URLs, saves to `output/*_discovered.json`
2. **Download & Upload** — Selenium cookies are transferred to a `requests.Session` for faster downloads, content is uploaded to Google Drive, progress tracked in `output/*_uploaded.json`

### Core Modules

| Module | Role |
|--------|------|
| `src/run_sync.py` | Orchestrator: login → scrape all sections → sync to Google |
| `src/scrape_all.py` | Main portal scraper (8 data sources: schedule, homework, exams, calendar, course content, ÖGEP, progress reports, announcements) |
| `src/sync_to_google.py` | Classifies scraped data and syncs to Calendar (color-coded), Tasks (deadlines), Sheets (grades), Drive (attachments) |
| `src/login.py` | Reusable login with CAPTCHA OCR (returns driver + cookies) |
| `src/google_auth.py` | OAuth2 token management for Google APIs |
| `src/scrape_eba_textbooks.py` | EBA textbook PDF downloader |
| `src/scrape_mebi_videos.py` | MEBI video scraper with course/unit/topic hierarchy |
| `src/scrape_sebitv.py` | SEBİTV video and PDF content |
| `src/scrape_sebitv_interactive.py` | SEBİTV interactive resources (ZIP archives + question banks) |

The `src/discover_*.py` files (30+) are exploratory/investigative scripts used during development — not part of the production pipeline.

### Data Flow

```
TED Portal → scrape_all.py → output/scraped_data.json → sync_to_google.py → Google Calendar/Tasks/Sheets/Drive
EBA        → scrape_eba_textbooks.py ──────────────────────────────────────→ Google Drive
MEBI       → scrape_mebi_videos.py ────────────────────────────────────────→ Google Drive
SEBİTV     → scrape_sebitv.py / scrape_sebitv_interactive.py ──────────────→ Google Drive
```

### Key Patterns

- **Import bootstrap**: Scripts use `sys.path.insert(0, PROJECT_ROOT)` and `os.chdir(PROJECT_ROOT)` at the top to ensure project-root-relative paths work
- **Cookie transfer**: Selenium authenticates, then cookies are transferred to `requests.Session` for efficient downloading
- **Idempotent uploads**: JSON tracker files (`*_uploaded.json`) prevent re-uploading already-processed content
- **Calendar color coding**: Events are color-coded by type — `ders` (lavender), `odev` (red), `sinav` (flamingo), `takim` (purple), `ogep` (tangerine), `etkinlik` (sage)
- **Course name normalization**: `normalize_course()` in `sync_to_google.py` maps portal-variant names to canonical forms (e.g. "DKAB" → "Din Kültürü", "Bilişim Teknolojileri" → "Bilişim"). Always call it when a course name flows into any Google Workspace output. Aliases are defined in `COURSE_ALIASES`. Scraper output uses portal-native names — normalization happens only at sync time.
- **Double-paren course names**: Portal schedule cells contain names like `İngilizce (Literature) (i-403 (İngilizce))`. The normalizer uses prefix-matching (longest-first) to correctly resolve these before the greedy paren-strip fallback.

## Dependencies

Runtime dependencies are installed via pip but not fully listed in `requirements.txt`. Key packages: `selenium`, `beautifulsoup4`, `ddddocr`, `requests`, `google-api-python-client`, `google-auth-oauthlib`, `pillow`, `numpy`, `opencv-python-headless`.

## Required Credentials (gitignored)

- `credentials.json` — Google OAuth2 client credentials
- `token.json` — Generated after first Google auth
- Portal credentials are currently hardcoded in scraper scripts

## Output

All runtime output goes to `output/` (gitignored): screenshots, HTML dumps, JSON data files, and upload trackers.
