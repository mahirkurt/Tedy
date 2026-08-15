# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TEDY is a Python web scraping and automation system that extracts educational data from Turkish school platforms (TED Rönesans Portal, EBA, MEBI, SEBİTV) and syncs it to Google Workspace (Calendar, Drive, Classroom). It runs as a scheduled cron job every 15 minutes on a local server, with a dashboard served at `tedy.online`. Google Classroom is the primary sync target — Calendar is used only for timed schedule events.

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
pytest                                                # Run all Python tests (unit + schema + API)
pytest tests/test_main.py                             # Single test file
TEST_AUTH_BYPASS=1 pytest tests/test_dashboard_api.py  # API integration tests with auth bypass
cd dashboard && npx playwright test                    # Playwright e2e tests (uses port 8086)

# Dashboard
python src/dashboard_api.py   # Start dashboard server on port 8085
cd dashboard && npm run dev   # Dev mode with hot reload on port 3000
cd dashboard && npm run build # Build production bundle to dashboard-dist/
cd dashboard && npm run lint  # ESLint check (TypeScript + React hooks)
python src/dashboard_api.py --generate-key  # Generate a new API key for third-party access

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

# Maintenance (destructive)
python src/purge_google_data.py   # ⚠️ Delete ALL synced Google data + clear local trackers
```

## Deployment

The dashboard runs in production as a Gunicorn WSGI server managed by a systemd user service, exposed publicly via Cloudflare Tunnel.

```bash
# Service management (systemd user service, no sudo needed)
systemctl --user status ted-dashboard
systemctl --user restart ted-dashboard
journalctl --user -u ted-dashboard -f   # View logs

# Rebuild and deploy dashboard
cd dashboard && npm run build            # Builds to dashboard-dist/
systemctl --user restart ted-dashboard   # Pick up new static files
```

- **Service file**: `~/.config/systemd/user/ted-dashboard.service`
- **Gunicorn**: binds `0.0.0.0:8085`, 2 workers, WSGI entry `src.dashboard_api:app`
- **Public URL**: `tedy.online` via Cloudflare Tunnel (`hp-ai-node` tunnel)
- **Cron**: `*/15 * * * *` runs `run_sync.py` with 600s timeout, logs to `output/sync.log`

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
| `src/sync_to_google.py` | Syncs timed events to Calendar (ders programı, timed takvim, ÖGEP) and uploads attachments to Drive |
| `src/login.py` | Reusable login with CAPTCHA OCR (returns driver + cookies) |
| `src/google_auth.py` | OAuth2 token management for Google APIs |
| `src/scrape_eba_textbooks.py` | EBA textbook PDF downloader |
| `src/scrape_mebi_videos.py` | MEBI video scraper with course/unit/topic hierarchy |
| `src/scrape_sebitv.py` | SEBİTV video and PDF content |
| `src/scrape_sebitv_interactive.py` | SEBİTV interactive resources (ZIP archives + question banks) |
| `src/enrich_gemini.py` | AI enrichment targeting Classroom: ödev courseWork notes, sınav study guides, ders announcement summaries, performans analysis (Gemini + Ollama fallback) |
| `src/env_loader.py` | Shared .env file loader utility |
| `src/json_utils.py` | Atomic JSON write utility (write to .tmp then rename) |
| `src/sync_to_classroom.py` | Syncs TED data to Google Classroom (courses, assignments, materials, grades, announcements, EBA/MEBI/SEBİTV content) |
| `src/auth_finish.py` | Manual OAuth completion for multi-account setup |
| `src/dashboard_api.py` | Flask API server + SPA hosting for dashboard (port 8085) |
| `src/data_validator.py` | Schema validation for scraped data |
| `src/session_manager.py` | Selenium session lifecycle management |
| `src/scrape_helpers.py` | Shared scraper utilities (waits, extraction, error handling) |
| `src/scrape_achieve3000.py` | Achieve3000 reading platform scraper |
| `src/scrape_englishcentral.py` | EnglishCentral language platform scraper |
| `src/scrape_sebit_homework.py` | SEBİT homework content scraper |
| `src/purge_google_data.py` | Purge all synced Google data (Classroom courses, Calendar events, Drive files) and clear local trackers |
| `src/migrate_course_names.py` | One-time migration: rename old course names to canonical forms across Calendar, Drive, etc. |
| `src/ocr_pdf_to_md.py` | PDF→Markdown OCR converter using Hailo AI accelerator + Tesseract |
| `dashboard/` | React 19 + Vite + Carbon Design System SPA — Işık's school dashboard (TEDY branding, multi-page with react-router-dom, focus mode, IBM Plex Sans via Google Fonts CDN, Google Sign-In auth) |

The `src/discover_*.py` files (30+) are exploratory/investigative scripts used during development — not part of the production pipeline.

### Data Flow

```
TED Portal → scrape_all.py → output/scraped_data.json ─┬→ sync_to_google.py ────→ Calendar (timed events) + Drive (attachments)
                                                        └→ sync_to_classroom.py ─→ Classroom (ödev, notlar, ders içerikleri, duyurular)
                                                         └→ enrich_gemini.py ────→ Classroom (AI notes on courseWork + announcements)
EBA        → scrape_eba_textbooks.py → output/eba_textbooks_uploaded.json ──────→ Drive + Classroom (via sync_to_classroom.py)
MEBI       → scrape_mebi_videos.py → output/mebi_videos_uploaded.json ───────────→ Drive + Classroom (via sync_to_classroom.py)
SEBİTV     → scrape_sebitv.py / scrape_sebitv_interactive.py → output/sebitv_*_uploaded.json → Drive + Classroom (via sync_to_classroom.py)
```

### Key Patterns

#### Scraping & Data

- **Import bootstrap**: Scripts use `sys.path.insert(0, PROJECT_ROOT)` and `os.chdir(PROJECT_ROOT)` at the top to ensure project-root-relative paths work
- **Cookie transfer**: Selenium authenticates, then cookies are transferred to `requests.Session` for efficient downloading
- **Idempotent uploads**: JSON tracker files (`*_uploaded.json`) prevent re-uploading already-processed content
- **Atomic JSON writes**: All critical JSON output uses `atomic_json_dump()` from `src/json_utils.py` — writes to `.tmp` then renames to prevent corruption
- **Environment variables**: `.env` at project root (gitignored) holds `GEMINI_API_KEY`, `PORTAL_USERNAME`, `PORTAL_PASSWORD`. Loaded via `src/env_loader.py` (no python-dotenv dependency)
- **Error isolation**: Each scraper in `run_sync.py` is wrapped in try-except. Partial data is saved and synced even if one scraper fails
- **Health check**: `output/health.json` is written after each sync with success status, errors, and duration

#### Google Sync

- **Course name normalization**: `normalize_course()` in `sync_to_google.py` maps portal-variant names to canonical forms (e.g. "DKAB" → "Din Kültürü", "Bilişim Teknolojileri" → "Bilişim"). Always call it when a course name flows into any Google Workspace output. Aliases are defined in `COURSE_ALIASES`. Scraper output uses portal-native names — normalization happens only at sync time.
- **Double-paren course names**: Portal schedule cells contain names like `İngilizce (Literature) (i-403 (İngilizce))`. The normalizer uses prefix-matching (longest-first) to correctly resolve these before the greedy paren-strip fallback.
- **Calendar color coding**: Events are color-coded by type — `ders` (lavender), `sinav` (flamingo), `takim` (purple), `ogep` (tangerine), `etkinlik` (sage). Only timed events go to Calendar; all-day events and ödev go to Classroom.
- **Single-account Calendar**: `sync_to_google.py` syncs only to primary account (`token.json`). `get_services()` returns `(calendar, drive)`.
- **ÖGEP dedup in Calendar**: `sync_takvim()` builds a set of ÖGEP session titles and skips any takvim events that match, to avoid duplication with `sync_ogep()`. Both functions sync to Calendar — takvim handles general calendar events, ogep handles ÖGEP-specific sessions.
- **Calendar retention**: Events older than 2 weeks are cleaned up except sınav (exam) records, which are kept permanently as grade references.
- **API retry**: `_api_call_with_retry()` retries transient Google API errors (429/500/503) up to 5x with exponential backoff (base_delay=3s). Used by both `sync_to_google.py` and `sync_to_classroom.py`.

#### Classroom

- **Classroom sync**: `sync_to_classroom.py` uses `token_huriye.json` (huriye.murzoglu@gmail.com) as teacher/owner. Courses are created in PROVISIONED state (personal Gmail limitation — cannot create ACTIVE courses). Syncs homework as courseWork (ASSIGNMENT), course content as announcements (avoids needing `courseworkmaterials` scope), grades as SHORT_ANSWER courseWork with scores, and duyurular/calendar/team/ÖGEP as announcements. Also syncs EBA textbooks (per-course), MEBI videos (per-unit), and SEBİTV resources (per-unit) as announcements with Drive material links — reads `*_uploaded.json` tracker files. `ALLOWED_COURSES` whitelist restricts creation to 11 specific courses. Uses hash-based change detection in `output/classroom_sync.json`. Student `isikkurtx@gmail.com` is auto-invited to all courses.
- **Drive → Classroom materials**: `sync_attachments_to_drive()` uploads homework attachments to Drive and returns a `drive_uploads` dict. This is passed to `sync_to_classroom.py` which links Drive files as `materials[].link` in courseWork.
- **AI enrichment**: `enrich_gemini.py` enriches 4 types of Classroom data: ödev courseWork notes (`🤖 Gemini Notu`), sınav courseWork study guides (`🤖 Sınav Rehberi`), ders announcement summaries (`🤖 Haftalık Özet`), and performans announcement analysis (`🤖 Performans Analizi`). Uses `ModelRouter` to cycle through Gemini cloud models then falls back to local Ollama. Idempotent via marker strings in descriptions. Reads `classroom_sync.json` state to find courseWork/announcement IDs. Runs automatically as post-sync step in `run_sync.py`.

#### Dashboard

- **Authentication**: Google Sign-In (GSI) with a hardcoded client_id. `LoginPage` sends the JWT credential to the API, which validates the `sub` claim against an allowlist. Auth token stored in localStorage.
- **Multi-page routing**: `react-router-dom` with routes defined in `dashboard/src/routes.ts`. Pages: Bugün (today), Program, Ödevler, Notlar, Takvim, Takımlar, Dersler, Tedy Books, İlerleme, Duyurular, Profil. Carbon `SideNav` for navigation, built from `navRoutes` — routes flagged `showInNav: false` (the book/reader detail routes) are routable but hidden.
- **Focus mode**: `FocusModeContext` toggles a distraction-free view. State persisted to localStorage (`tedy-focus-mode` key).
- **Homework tracker policy**: Shows all homework (no time filter), sorted by deadline descending (furthest first). Teacher-assigned statuses (Yaptı/Yapmadı) are shown as colored badges. Expired deadlines show a neutral "Süresi doldu" tag. Countdown bars visualize time remaining.
- **Data fetching**: `useApi<T>` hook polls the Flask API every 5 minutes. Custom event `tedy:homework-updated` triggers cross-component refresh.

#### Tedy Books

- **Content source**: `books/<slug>/` holds one Markdown file per chapter plus an optional `book.json` manifest declaring the full table of contents (including unwritten chapters, shown as "Yakında"). See `books/README.md` for the chapter-file naming rule and manifest schema.
- **Publishing a chapter**: drop the `.md` file into the book directory — nothing else. `python src/check_books.py [slug]` walks the shelf through the API's own functions and exits non-zero on an unmatched filename, an unrecognised title preamble, or an empty body. `_book_chapters()` in `dashboard_api.py` re-scans on every request and matches files to manifest entries by id prefix, so no rebuild or restart is needed. Files matching no manifest entry are appended rather than dropped.
- **API**: `/api/books`, `/api/books/<slug>`, `/api/books/<slug>/chapters/<id>` — all `@require_auth`. Slugs and chapter ids are regex-validated and the resolved path is checked against `BOOKS_DIR` to block traversal.
- **Front matter**: `_book_split_front_matter()` strips a chapter's title preamble so the reader can typeset its own title page from manifest metadata instead of repeating the source headings. Chapter files disagree on the shape (`# Part / ## Chapter / *credit* / ---` in B01–B02, `### BÖLÜM III` plus a bare shouted title and no rule from B03 on), so it consumes the leading run of heading-like lines and stops at the first line of prose; a horizontal rule still terminates it explicitly. `partHeading` falls back to the manifest's `part` when the file does not name its volume.
- **Reader**: `BookReader.tsx` is a fixed full-viewport overlay (z-index above the Carbon header). Markdown is rendered to React elements by `utils/markdown.tsx` (no HTML injection); `>` blockquotes render as verse with line breaks preserved.
- **Loose verse**: chapter files often write songs and inscriptions as plain blank-line-separated lines instead of `>` blocks. `foldLooseVerse()` in `utils/markdown.tsx` folds runs of 2+ short (<80 char) single-line paragraphs that do not open with a quote or dash into a verse block, so they do not set as indented prose. An explicit `>` block always wins.
- **Reader state**: theme/font/size/line-height/measure in localStorage `tedy-books-settings`; reading position in `tedy-books-progress`, read via `useSyncExternalStore` so open screens stay in sync. Device-local by design — nothing is written server-side.
- **Typography**: Cormorant Garamond (display) + Literata (body) loaded from Google Fonts in `index.html`. Ornaments are inline SVG (`Ornament.tsx`), not ❦ characters, which fall back to the colour-emoji font.

## Dependencies

Runtime dependencies are installed via pip but not fully listed in `requirements.txt`. Key packages: `selenium`, `beautifulsoup4`, `ddddocr`, `requests`, `google-api-python-client`, `google-auth-oauthlib`, `google-genai`, `pillow`, `numpy`, `opencv-python-headless`, `flask`, `gunicorn`. Optional: local Ollama server for AI fallback.

## Required Credentials (gitignored)

- `credentials.json` — Google OAuth2 client credentials
- `token.json` — Generated after first Google auth (primary/student account)
- `token_huriye.json` — OAuth token for huriye.murzoglu@gmail.com (Classroom teacher/owner + AI enrichment target)
- `token_mahirkurt.json` — OAuth token for drmahirkurt@gmail.com (optional)
- `.env` — Contains `GEMINI_API_KEY`, `PORTAL_USERNAME`, `PORTAL_PASSWORD`, `API_KEYS` (third-party API keys, format: `label:tdyK_...`). Generate with `python src/dashboard_api.py --generate-key`

**Note:** `google_auth.py` always uses `run_local_server(port=8090)`. After adding new scopes, delete the token file and re-run auth. Classroom scopes are included by default.

## Output

All runtime output goes to `output/` (gitignored): screenshots, HTML dumps, JSON data files, and upload trackers.
