# Academic Year Rollover — 2025-2026 → 2026-2027

**Date:** 2026-08-22
**Status:** Approved design, not yet implemented

## Problem

TEDY was built for a single academic year and hardcodes it. The 2026-2027 year
is already staged on the TED portal (home page banner "2026-2027 Hazırlıkları",
week selector starting 14.09.2026), so new-year data will begin arriving within
weeks. Today nothing separates it from 2025-2026:

- **Drive folders are flat and course-named** — `Ödevler/Matematik`,
  `Ders Kitapları/Türkçe`, `MEBI Videolar/Fen Bilimleri`. New-year files would
  merge into the same folders with no way to tell the years apart afterwards.
- **`output/scraped_data.json` is overwritten in place** every 15 minutes. The
  moment the portal serves 2026-2027 data, the 2025-2026 record is gone.
- **Grade-6 constants are scattered** through the code (see Evidence).

## Goals

1. Detect the academic year automatically from the portal.
2. Archive 2025-2026 — locally and in Drive — before any new-year data lands.
3. Namespace Drive by year so the two never mix again.
4. Repair scrapers broken by portal changes.
5. Scrape the portal pages no scraper currently touches.
6. Let the dashboard browse the archived year.

## Non-goals

- **Rebuilding Google Classroom for 7th grade.** Explicitly excluded by the
  user. `ALLOWED_COURSES` stays as-is. See §G for the one consequence handled.
- **Writing anything to the portal.** Club selection is Işık's personal choice
  and a write to the school's system; TEDY reads it and reports, never sets it.
- Backfilling years before 2025-2026. TEDY holds no data for them. The portal
  does expose 2024-2025 dönem codes (`202401`–`202404`), so a backfill is
  technically possible later, but it is out of scope here.

## Evidence (observed 2026-08-22)

Portal, via authenticated inspection:

| Fact | Value |
|---|---|
| Home week selector | `select#dp_icerik_secili_hafta`, first option `14.09.2026 00:00:00` = "1. Hafta 14 Eyl. - 20 Eyl." |
| Dönem selector | `select#genel_icerik_dp_ilgili_donem`, codes `202401`–`202504`, format `YYYY0Q` where `YYYY` is the year the term started |
| Home banner | "2026-2027 Hazırlıkları" |
| Profile page | `p_ogrenci_bilgilerim` returns **404**; the working URL is `p_temel_bilgiler` |
| Akademi Modülü | closed — "Akademi Modülü kısa bir süre erişime kapalıdır." |
| Akademik Takvim | redirects to `/hata/yetkisiz_giris` |
| Kulüp Seçimi | open, 5 preference dropdowns, none selected |
| Kulüp Kategori Puanlama | open, 6 categories to rank 1–6, none set |
| Rehberlik Formları | reachable, table renders, 0 records |

The Akademi Modülü closure and takvim `yetkisiz` are understood as
preparation-phase states (no active enrollment yet), not permanent revocations.
Both are already handled by the `PortalUnavailable` mechanism and need no
further work here.

Repo, grade-6 assumptions:

| Location | Assumption |
|---|---|
| `src/scrape_all.py` | `OGRENCI_ID = "13240"` |
| `src/scrape_all.py` | takvim level filter hardcoded to `"60"` (6. Sınıf) |
| `src/sync_to_classroom.py` | `ALLOWED_COURSES` — 10 sixth-grade course names |
| `src/assistant_core.py:1339` | prompt says "Hedef kitle: 6. sınıf öğrencisi" |

Google state: Classroom holds 0 TEDY courses (already purged; the 15 `DECLINED`
entries are the school's own). All four `*_uploaded.json` trackers are `{}`.
Drive root holds `Ödevler`, `Ders Kitapları`, `MEBI Videolar`,
`SEBİTV Videolar`, `TED Portal Ödevler`.

## A. Academic year model

New module `src/academic_year.py`.

**Authority:** the home page week selector. Its first option's date is the start
of the year the portal is actively serving; `14.09.2026` yields `2026-2027`. The
dönem selector is a cross-check only — during preparation it still reads
`2025-2026`, because the new term's dönem codes do not exist yet.

```python
detect_academic_year(driver) -> str | None   # "2026-2027", or None if unknown
```

Resolution order:
1. Parse the week selector's earliest option date → `YYYY-(YYYY+1)`.
2. If unavailable, parse the highest dönem code (`202504` → `2025-2026`).
3. If neither parses, return `None`.

**State file** `output/academic_year.json`:

```json
{
  "year": "2026-2027",
  "previous": "2025-2026",
  "detected_at": "2026-08-22T10:00:00",
  "source": "week_selector",
  "grade": null
}
```

`grade` stays `null` until the portal exposes it, then is recorded for display.
It is never used in folder names.

**Two safety properties.** Detection is fully automatic with no human step, so
these guard the failure modes:

- **Hold-last-known.** `None` never overwrites a stored year. The stored value
  stands and `health.json` records `year_detection: "held"`. A blocked or
  redirected page cannot reset the year.
- **Forward-only.** A detected year earlier than the stored one is ignored and
  flagged. A year cannot un-happen, so a stale page cannot roll the system back
  and re-archive over good data.

## B. Archive

New module `src/archive_year.py`.

```python
archive_year(year: str, drive_service=None) -> dict   # returns a manifest
```

**Local** — copies into `output/archive/<year>/`:
`scraped_data.json`, `health.json`, `classroom_sync.json`, every
`*_uploaded.json`, plus a generated `manifest.json`:

```json
{
  "year": "2025-2026",
  "grade": null,
  "archived_at": "2026-08-22T10:30:00",
  "counts": {"homework": 0, "rubrics": 24, "ders_icerikleri": 17},
  "drive_folder": "<id>",
  "source_scraped_at": "2026-08-22T10:00:08"
}
```

**Drive** — creates a single `TEDY` folder at Drive root (if absent), then
`TEDY/<year>/` inside it, and moves the five existing root folders under that by
patching each folder's `parents` (a move, not a copy — no file duplication, no
re-upload). After this, Drive root holds `TEDY` instead of the five loose
folders.

**Idempotent.** If `output/archive/<year>/manifest.json` exists, the function
returns that manifest and changes nothing. Re-running a sync cannot double
archive or re-move folders.

**Ordering — the critical constraint.** `run_sync.py` calls detection
immediately after login, and if the detected year differs from the stored one it
archives *before any scraper runs*. Archiving after scraping would snapshot
new-year data under the old year's name and lose the old year permanently.

## C. Drive year namespacing

All five Drive roots resolve through one helper, `_get_or_create_folder` in
`src/sync_to_google.py`, imported by `scrape_eba_textbooks.py`,
`scrape_mebi_videos.py`, `scrape_sebitv.py` and `scrape_sebitv_interactive.py`.
That single choke point is the change:

```python
get_year_root(drive_service) -> str   # id of TEDY/<current year>/
```

The five root-level calls pass `parent_id=get_year_root(...)`. Layout becomes:

```
TEDY/
  2025-2026/
    Ödevler/Matematik/…      ← moved here by the archive
    Ders Kitapları/…
    MEBI Videolar/…
    SEBİTV Videolar/…
  2026-2027/
    Ödevler/…                ← created on demand by the new year
```

Subject subfolders are unchanged — they are already created with an explicit
`parent_id`.

## D. Scraper repairs

- **Profile.** Point `scrape_ogrenci_profili` at `p_temel_bilgiler` and parse the
  fields it actually serves: okul no, doğum tarihi, veli, telefon, ikinci
  yabancı dil, servis no/sürücü/plaka, ÖGEP katılım counts.
- **404 guard.** A page whose body contains
  `404 - File or directory not found` raises a distinct error. Unlike
  `PortalUnavailable` — which means the portal deliberately refused — a 404 is
  URL drift on our side and must stay a loud failure. Silent 0-field scraping is
  what hid this bug for months.

## E. New pages

- `scrape_rehberlik_formlari(driver)` → `p_ogrenci_rehberlik_formlari`, a table
  extracted with the existing `extract_table` (so it inherits empty-state
  handling).
- `scrape_kulup(driver)` → reads `p_kulup_secimi` and
  `p_kulup_kategori_puanlama`, returning current selections, the available
  options, and a `pending` flag when preferences or rankings are incomplete.
  **Read-only. No form is ever submitted.**

Both are registered in `run_sync.py` with `min: 0` validator rules — they are
informational, and an empty result is not a failure.

## F. Dashboard archive browsing

- `GET /api/archive/years` → `[{"year": "2025-2026", "grade": null, "counts": {…}}]`
- `GET /api/archive/<year>` → that year's snapshot

Both `@require_auth` and **absent from `READER_ENDPOINTS`**, so the reader role
is refused by the existing default-deny gate. `<year>` is validated against
`^\d{4}-\d{4}$` and the resolved path checked against the archive directory, the
same traversal defence the book routes use.

UI: a year switcher; selecting an archived year renders its snapshot read-only.

## G. Classroom consequence

With the whitelist frozen at 6th grade, an unrecognised 7th-grade course makes
`_resolve_course_id` return `None`, which today increments `result["errors"]`.
That would report a permanent false failure every 15 minutes — the exact noise
just removed from the health check. Unrecognised courses become a **skip**, not
an error. No course is created; nothing else about Classroom sync changes.

## Failure modes

| Scenario | Behaviour |
|---|---|
| Portal blocked at detection time | Hold last known year; `health.json` flags `held`; no archive, no rollover |
| Week selector present but unparseable | Fall through to dönem selector; then `None` → hold |
| Detected year < stored year | Ignored and flagged; no archive |
| Archive interrupted midway | Manifest is written last, so the archive is retried on the next sync |
| Drive unavailable during archive | Local archive still completes; Drive move retried next sync; manifest records `drive_folder: null` |

## Testing

- **Year detection** — against the real page HTML captured 2026-08-22, plus
  synthetic cases for hold-last-known and forward-only.
- **Archive** — idempotency, ordering (old data archived before overwrite), and
  manifest contents, in `tmp_path`.
- **Drive namespacing** — `get_year_root` with a mocked Drive service; assert
  the five roots request the year folder as parent.
- **Scraper repairs** — 404 guard and profile parsing against saved fixtures.
- **Archive API** — reader refused, traversal rejected, unknown year 404s.

No test touches the live portal or live Google APIs.

## Sequencing

1. `academic_year.py` + detection tests
2. `archive_year.py` + archive tests
3. Wire detection/archive into `run_sync.py` (before scrapers)
4. Drive year namespacing
5. Scraper repairs (profile, 404 guard)
6. New pages (rehberlik, kulüp)
7. Archive API + dashboard year switcher
8. Classroom skip guard

Steps 1–4 must land together: they are what protect the 2025-2026 data. Steps
5–8 are independent and can follow.

## Requires human action — not automatable

**Kulüp Seçimi is open and incomplete.** Five preferences unselected, six
categories unranked, with a deadline before term start. TEDY will surface this
as pending on the dashboard, but Işık must make the choices.
