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
cd dashboard && npx playwright test                    # Playwright e2e tests (port 8286, override with TEDY_E2E_PORT)

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
| `src/env_loader.py` | Shared .env file loader utility (fills gaps only — the real environment wins) |
| `src/academic_year.py` | Detects the academic year from the portal; hold-last-known + forward-only guards |
| `src/archive_year.py` | Seals a finished year locally and moves its Drive folders under `TEDY/<year>/` |
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
- **Environment variables**: `.env` at project root (gitignored, mode 600) holds `GEMINI_API_KEY`, `PORTAL_USERNAME`, `PORTAL_PASSWORD`, `DASHBOARD_SECRET_KEY`. Loaded via `src/env_loader.py` (no python-dotenv dependency), which uses `setdefault` — a real environment variable always beats the `.env` value, so `FOO=x python …` and systemd `Environment=` work as expected
- **Required secrets**: `DASHBOARD_SECRET_KEY` is mandatory. The API raises at import when it is missing rather than generating a per-process random key, because with 2 gunicorn workers that silently signs sessions with two different keys and logs users out at random. OAuth token files (`token*.json`, `credentials.json`) are mode 600
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
- **Drive is namespaced by academic year**: every content root resolves under `TEDY/<year>/` via `get_year_root()`, so 2025-2026 and 2026-2027 files never share a folder. All six root-level `_get_or_create_folder` calls (Ödevler, Ders Kitapları, MEBI Videolar, SEBİTV Videolar, SEBİTV Etkileşimli, SEBİTV Soru Bankaları) pass it as `parent_id`; subject/unit folders already carry their own parent. Root lookups are scoped with `'root' in parents` — without that, a later rollover would find the previous year's folder by name and drag it into the new year.
- **Unknown year refuses to upload**: `get_year_root()` raises `UnknownAcademicYear` rather than guessing. Skipping an upload is harmless (uploads are idempotent and retried every 15 min); filing content under the wrong year is permanent and silent.

#### Academic year rollover

- **Detection is automatic**, with no human step: `detect_academic_year()` reads the portal's home week selector (`#dp_icerik_secili_hafta`) and takes `max()` of the years its option dates fall in; the gelişim dönem selector (`YYYY0Q` codes) is a fallback because it lags during the school's preparation phase. `max()` rather than the earliest date, because a single stale previous-year option would otherwise peg detection to last year forever and no rollover would ever fire.
- **Two safety properties** make automatic detection safe, both in `resolve_year()`: *hold-last-known* (an undetected year never overwrites the stored one — a blocked page cannot reset the year) and *forward-only* (a detected year earlier than the stored one is ignored — a year cannot un-happen). State lives in `output/academic_year.json`.
- **Ordering is the whole point**: `run_year_rollover()` runs immediately after login and archives **before any scraper executes**. Archiving afterwards would snapshot new-year data under the old year's name and lose the old year permanently.
- **The archive is sealed**: once `output/archive/<year>/manifest.json` exists the year is immutable, and the manifest is written last so an interrupted archive is retried rather than half-trusted. Upload trackers are reset on a genuine seal so the new year re-uploads into its own Drive folder.
- **Deferred Drive moves are repaired**: if Drive is unreachable during the flip, the local archive still seals with `drive_folder: null`, and later `current` runs scan `output/archive/*/manifest.json` and complete the move. Health reports `academic_year`, `year_detection` and `year_archived`.

#### Classroom

- **Classroom sync**: `sync_to_classroom.py` uses `token_huriye.json` (huriye.murzoglu@gmail.com) as teacher/owner. Courses are created in PROVISIONED state (personal Gmail limitation — cannot create ACTIVE courses). Syncs homework as courseWork (ASSIGNMENT), course content as announcements (avoids needing `courseworkmaterials` scope), grades as SHORT_ANSWER courseWork with scores, and duyurular/calendar/team/ÖGEP as announcements. Also syncs EBA textbooks (per-course), MEBI videos (per-unit), and SEBİTV resources (per-unit) as announcements with Drive material links — reads `*_uploaded.json` tracker files. `ALLOWED_COURSES` whitelist restricts creation to 11 specific courses. Uses hash-based change detection in `output/classroom_sync.json`. Student `isikkurtx@gmail.com` is auto-invited to all courses.
- **Drive → Classroom materials**: `sync_attachments_to_drive()` uploads homework attachments to Drive and returns a `drive_uploads` dict. This is passed to `sync_to_classroom.py` which links Drive files as `materials[].link` in courseWork.
- **AI enrichment**: `enrich_gemini.py` enriches 4 types of Classroom data: ödev courseWork notes (`🤖 Gemini Notu`), sınav courseWork study guides (`🤖 Sınav Rehberi`), ders announcement summaries (`🤖 Haftalık Özet`), and performans announcement analysis (`🤖 Performans Analizi`). Uses `ModelRouter` to cycle through Gemini cloud models then falls back to local Ollama. Idempotent via marker strings in descriptions. Reads `classroom_sync.json` state to find courseWork/announcement IDs. Runs automatically as post-sync step in `run_sync.py`.

#### Dashboard

- **Authentication**: Google Sign-In (GSI) with a hardcoded client_id. `LoginPage` sends the JWT credential to the API, which validates the `sub` claim against an allowlist. Auth token stored in localStorage.
- **Roles**: `USER_ROLES` in `dashboard_api.py` maps each allowed email to `full` or `reader`. `reader` (currently `murzogluhulya@gmail.com`) reaches Tedy Books and nothing else. The gate lives in `require_auth`, which refuses any endpoint not named in `READER_ENDPOINTS` — default-deny, so a new route never leaks by omission. The role is re-derived from the roster on every request rather than trusted from the session, and an email that has fallen off the roster gets the least privilege. `_require_assistant_access()` blocks readers too. The frontend mirrors this with `readerAccess` flags in `routes.ts`; hiding pages is presentation, the API gate is the control.
- **Reader shell**: a reader gets `ReaderChrome.tsx` (cloth masthead + colophon) instead of `DashboardHeader`/`DashboardFooter`, no `SideNav`, and a paper ground driven by `html[data-role='reader']`. This matters functionally, not just visually: the dashboard header fetches `/api/health` and `/api/private-lessons`, which a reader is refused. Unroutable paths resolve to `ROLE_HOME[role]`.
- **Multi-page routing**: `react-router-dom` with routes defined in `dashboard/src/routes.ts`. Pages: Bugün, İşler, Asistan, Dersler, Tedy Books (primary) and Notlar, Takvim, Takımlar, İlerleme, Duyurular, Profil (`secondary: true`). Carbon `SideNav` is built from `navRoutesFor(role)`; the five primary items sit at the top level and the six secondary ones under a `SideNavMenu` titled "Daha fazla", because a reader who has to choose between eleven equal items before doing anything is paying the focus window for navigation (İ1). Routes flagged `showInNav: false` (Sınavlar, the book/reader detail routes) are routable but hidden — Sınavlar because exams now surface inside İşler.
- **Merged and renamed surfaces**: Ödevler + Sınavlar → `/isler` (İşler: everything owed with a date on it), Program + Ders İçerikleri → `/dersler` (Lessons). `redirects` in `routes.ts` keeps the old paths alive as `<Navigate replace/>` — `/odevler` → `/isler`, `/program` → `/dersler`.
- **Focus mode**: `FocusModeContext` toggles a distraction-free view. State persisted to localStorage (`tedy-focus-mode` key).
- **Homework tracker policy**: Shows all homework (no time filter). Sorted per group, not globally: `aktif` is nearest-deadline-first so the most urgent work is reachable without scrolling, while the settled groups (`yapilan`/`tamamlanan`/`yapilmayan`) are newest-first because they read as history. A row whose deadline will not parse sinks in both orders rather than sorting as 1970. The list used to be furthest-first everywhere; that put the least urgent item at the top for a reader who overestimates how long work takes. `nextHw` is simply `aktif[0]`. Teacher-assigned statuses (Yaptı/Yapmadı) are shown as colored badges. "Süresi doldu" is suppressed when `student_marked_done` — telling someone their deadline expired for work they already reported doing is a false alarm. Finished groups are collapsed by default (İ7).
- **Design constitution**: `docs/frontend-design-principles.md` states the rules every surface is judged against — four non-negotiables (Carbon tokens mandatory, accessibility floor, no silent failure, internal representation never reaches the reader) and nine ADHD principles (İ1–İ9), each with a falsifiable test. `docs/frontend-surface-designs.md` applies them surface by surface and lists the shared patterns. Change a surface, check it against both; they are the reason the code looks the way it does.
- **The signature components**: `DayStrip` draws only the *remaining* span of the day to scale, shading the focus window that closes at 16:00 — so time is a place rather than a number, and the strip shortens by itself (İ2, İ7). `NextThing` names one step and offers a time box ("10 dakikayla başla"), never a duration: nothing in the portal says how long homework takes, so an estimate would be an invention (İ3, D4).
- **Empty is never blank**: `EmptyLine` and `PortalStatusBanner` in `components/patterns/`. A surface with nothing on it says so in the portal's own words; a blank page is indistinguishable from a broken one (D3). `formatTurkishDate` returns `''` rather than echoing an unparsed input — returning the input on failure is how internal text reaches a reader (D4).
- **Data fetching**: `useApi<T>` hook polls the Flask API every 5 minutes. Custom event `tedy:homework-updated` triggers cross-component refresh.

#### Tedy Books

- **Content source**: `books/<slug>/` holds one Markdown file per chapter plus an optional `book.json` manifest declaring the full table of contents (including unwritten chapters, shown as "Yakında"). See `books/README.md` for the chapter-file naming rule and manifest schema.
- **Publishing a chapter**: drop the `.md` file into the book directory — nothing else. `python src/check_books.py [slug]` walks the shelf through the API's own functions and exits non-zero on an unmatched filename, an unrecognised title preamble, or an empty body. `_book_chapters()` in `dashboard_api.py` re-scans on every request and matches files to manifest entries by id prefix, so no rebuild or restart is needed. Files matching no manifest entry are appended rather than dropped.
- **API**: `/api/books`, `/api/books/<slug>`, `/api/books/<slug>/chapters/<id>`, `/api/books/translate`, `/api/books/progress` — all `@require_auth`, and all named in `READER_ENDPOINTS` so readers may reach them. Slugs and chapter ids are regex-validated and the resolved path is checked against `BOOKS_DIR` to block traversal.
- **Front matter**: `_book_split_front_matter()` strips a chapter's title preamble so the reader can typeset its own title page from manifest metadata instead of repeating the source headings. Chapter files disagree on the shape (`# Part / ## Chapter / *credit* / ---` in B01–B02, `### BÖLÜM III` plus a bare shouted title and no rule from B03 on), so it consumes the leading run of heading-like lines and stops at the first line of prose; a horizontal rule still terminates it explicitly. `partHeading` falls back to the manifest's `part` when the file does not name its volume.
- **Reader**: `BookReader.tsx` is a fixed full-viewport overlay (z-index above the Carbon header). Markdown is rendered to React elements by `utils/markdown.tsx` (no HTML injection); `>` blockquotes render as verse with line breaks preserved.
- **Loose verse**: chapter files often write songs and inscriptions as plain blank-line-separated lines instead of `>` blocks. `foldLooseVerse()` in `utils/markdown.tsx` folds runs of 2+ short (<80 char) single-line paragraphs that do not open with a quote or dash into a verse block, so they do not set as indented prose. An explicit `>` block always wins.
- **Reader state**: theme/font/size/line-height/measure in `tedy-books-settings::<email>`; reading position in `tedy-books-progress::<email>`, read via `useSyncExternalStore` so open screens stay in sync. Keys are namespaced per profile (`activateReaderProfile()`), so two people sharing a device never see each other's bookmarks. The pre-namespacing keys are inherited only by full-access accounts — a reader adopting them would be exactly the bleed the namespacing prevents.
- **Reading position sync**: localStorage is the working copy (reading survives offline); `useBookProgressSync()` pulls once on sign-in and pushes local movement on a lazy timer, so a bookmark follows the account across devices. Server side: `GET`/`POST /api/books/progress`, stored per email in `output/book_progress.json` via `atomic_json_dump`. Merges per book by `updatedAt` — a stale device cannot roll a reader back. The client payload is untrusted, so slugs/chapter ids go through the same regexes the book routes use and anything else is dropped. API-key callers get 403: progress is per-person, not per-integration.
- **Resume band**: `ResumeBand` on the shelf surfaces the most recently touched book — chapter name, ratio, "Devam et" — from the profile's own bookmark.
- **Type controls on mobile**: below 34rem the type panel is a bottom sheet — anchored top-right it covered the very text being resized, so every change looked like no change. Column width is applied twice: `--reader-measure` as a `max-width` (binds on wide screens) and `--reader-gutter` as `.reader__scroll` side padding (binds on phones, where the viewport is always narrower than the narrowest measure and `max-width` is inert). `html { text-size-adjust: 100% }` stops Chrome on Android auto-scaling body text over the reader's chosen punto.
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
