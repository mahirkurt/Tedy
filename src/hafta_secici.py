"""Shared "which week is now" resolver for the weekly timetable.

`dashboard_api` and `assistant_core` each used to implement their own
version of "the `is_current` week, else the last one" — `assistant_core`'s
copy dropped non-dict weeks before falling back to the last one, which is
not quite what `dashboard_api` did, and the two silently drifted apart
(final review of `docs/superpowers/plans/2026-09-28-pano-eksiklikleri.md`,
Minor 4). This module has no other TEDY dependency — not Flask, not
`DASHBOARD_SECRET_KEY` — so `assistant_core` (used standalone by
`reindex_assistant.py`/`run_sync.py`, without a dashboard secret key) can
import it without pulling `dashboard_api` (and Flask) in.
"""


def guncel_hafta(weeks):
    """The week the scraper saw selected (`is_current`), else the last one
    (data written before that mark existed), else {}. `/api/schedule`'s
    `latest`, the assistant's `ders_programi` tool, its BM25 timetable
    paragraph (`assistant_core._fmt_scraped_data`) and the unified calendar
    (`dashboard_api._birlesik_takvim`) all read this one week. The scraper
    may keep the whole published year, so the last element can be a week in
    June."""
    if not isinstance(weeks, list) or not weeks:
        return {}
    son = weeks[-1] if isinstance(weeks[-1], dict) else {}
    return next((w for w in weeks if isinstance(w, dict) and w.get("is_current")), son)
