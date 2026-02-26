# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TED is a Python web scraping and automation system that extracts educational data from Turkish school platforms (TED Rönesans Portal, EBA, MEBI, SEBİTV) and syncs it to Google Workspace (Calendar, Tasks, Sheets, Drive, Classroom). It runs as a scheduled cron job every 15 minutes.

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
python src/google_auth.py huriye     # OAuth for secondary account
python src/auth_finish.py huriye "<redirect_url>"  # Complete OAuth manually

# AI enrichment (ödev notes, sınav guides, ders summaries, performans analysis)
python src/enrich_gemini.py         # Enrich new events only
python src/enrich_gemini.py --force # Regenerate all notes

# Google Classroom sync
python src/sync_to_classroom.py                  # Sync to Google Classroom (standalone)
python src/sync_to_classroom.py --reset-courses   # Archive and recreate all courses
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
| `src/enrich_gemini.py` | AI enrichment: ödev notes, sınav study guides, ders içerikleri summaries, performans analysis (Gemini + Ollama fallback) |
| `src/env_loader.py` | Shared .env file loader utility |
| `src/json_utils.py` | Atomic JSON write utility (write to .tmp then rename) |
| `src/sync_to_classroom.py` | Syncs TED data to Google Classroom (courses, assignments, materials, grades, announcements) |
| `src/auth_finish.py` | Manual OAuth completion for multi-account setup |

The `src/discover_*.py` files (30+) are exploratory/investigative scripts used during development — not part of the production pipeline.

### Data Flow

```
TED Portal → scrape_all.py → output/scraped_data.json → sync_to_google.py → Google Calendar/Tasks/Sheets/Drive
EBA        → scrape_eba_textbooks.py ──────────────────────────────────────→ Google Drive
MEBI       → scrape_mebi_videos.py ────────────────────────────────────────→ Google Drive
SEBİTV     → scrape_sebitv.py / scrape_sebitv_interactive.py ──────────────→ Google Drive
TED Portal → scraped_data.json → sync_to_classroom.py ────────────────────→ Google Classroom
```

### Key Patterns

- **Import bootstrap**: Scripts use `sys.path.insert(0, PROJECT_ROOT)` and `os.chdir(PROJECT_ROOT)` at the top to ensure project-root-relative paths work
- **Cookie transfer**: Selenium authenticates, then cookies are transferred to `requests.Session` for efficient downloading
- **Idempotent uploads**: JSON tracker files (`*_uploaded.json`) prevent re-uploading already-processed content
- **Calendar color coding**: Events are color-coded by type — `ders` (lavender), `odev` (red), `sinav` (flamingo), `takim` (purple), `ogep` (tangerine), `etkinlik` (sage)
- **Course name normalization**: `normalize_course()` in `sync_to_google.py` maps portal-variant names to canonical forms (e.g. "DKAB" → "Din Kültürü", "Bilişim Teknolojileri" → "Bilişim"). Always call it when a course name flows into any Google Workspace output. Aliases are defined in `COURSE_ALIASES`. Scraper output uses portal-native names — normalization happens only at sync time.
- **Double-paren course names**: Portal schedule cells contain names like `İngilizce (Literature) (i-403 (İngilizce))`. The normalizer uses prefix-matching (longest-first) to correctly resolve these before the greedy paren-strip fallback.
- **Multi-account sync**: `sync_to_google.py` syncs to both primary (`token.json`) and secondary (`token_huriye.json`) accounts. If the secondary token doesn't exist, it's skipped gracefully.
- **AI enrichment**: `enrich_gemini.py` enriches 4 types of data: ödev notes (`🤖 Gemini Notu`), sınav study guides (`🤖 Sınav Rehberi`), ders içerikleri summaries (`🤖 Haftalık Özet`), and performans analysis (`🤖 Performans Analizi`). Uses `ModelRouter` to cycle through Gemini cloud models then falls back to local Ollama. Idempotent via marker strings in descriptions. Runs automatically as post-sync step in `run_sync.py`.
- **Environment variables**: `.env` at project root (gitignored) holds `GEMINI_API_KEY`, `PORTAL_USERNAME`, `PORTAL_PASSWORD`. Loaded via `src/env_loader.py` (no python-dotenv dependency).
- **Error isolation**: Each scraper in `run_sync.py` is wrapped in try-except. Partial data is saved and synced even if one scraper fails.
- **API retry**: `_api_call_with_retry()` retries transient Google API errors (429/500/503) up to 5x with exponential backoff (base_delay=3s). Used by both `sync_to_google.py` and `sync_to_classroom.py`.
- **Health check**: `output/health.json` is written after each sync with success status, errors, and duration.
- **Classroom sync**: `sync_to_classroom.py` uses `token_huriye.json` (huriye.murzoglu@gmail.com) as teacher/owner. Courses are created in PROVISIONED state (personal Gmail limitation — cannot create ACTIVE courses). Syncs homework as courseWork (ASSIGNMENT), course content as announcements (avoids needing `courseworkmaterials` scope), grades as SHORT_ANSWER courseWork with scores, and duyurular/calendar/team/ÖGEP as announcements. `ALLOWED_COURSES` whitelist restricts creation to 11 specific courses. Uses hash-based change detection in `output/classroom_sync.json`. Student `isikkurtx@gmail.com` is auto-invited to all courses.
- **Atomic JSON writes**: All critical JSON output uses `atomic_json_dump()` from `src/json_utils.py` — writes to `.tmp` then renames to prevent corruption.

## Dependencies

Runtime dependencies are installed via pip but not fully listed in `requirements.txt`. Key packages: `selenium`, `beautifulsoup4`, `ddddocr`, `requests`, `google-api-python-client`, `google-auth-oauthlib`, `google-genai`, `pillow`, `numpy`, `opencv-python-headless`. Optional: local Ollama server for AI fallback.

## Required Credentials (gitignored)

- `credentials.json` — Google OAuth2 client credentials
- `token.json` — Generated after first Google auth (primary/student account)
- `token_huriye.json` — OAuth token for huriye.murzoglu@gmail.com (Classroom teacher/owner + Calendar/Tasks secondary sync)
- `token_mahirkurt.json` — OAuth token for drmahirkurt@gmail.com (optional)
- `.env` — Contains `GEMINI_API_KEY`, `PORTAL_USERNAME`, `PORTAL_PASSWORD`

**Note:** `google_auth.py` always uses `run_local_server(port=8090)`. After adding new scopes, delete the token file and re-run auth. Classroom scopes are included by default.

## Output

All runtime output goes to `output/` (gitignored): screenshots, HTML dumps, JSON data files, and upload trackers.
