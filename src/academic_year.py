"""Which academic year is the portal serving?

The portal is the authority. Its home-page week selector names the year it is
actively serving; the gelişim raporu dönem list lags during the preparation
phase and is only a fallback.
"""
import json
import os
import re
from datetime import datetime
from typing import NamedTuple

from src.json_utils import atomic_json_dump

STATE_FILENAME = "academic_year.json"

# Academic years turn over in August: a week in Sep-Dec belongs to the year
# that just began, a week in Jan-Jul to the year that began the previous autumn.
YEAR_START_MONTH = 8

_DATE_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")
_DONEM_RE = re.compile(r"^(\d{4})0([1-4])$")


def _span(start_year: int) -> str:
    return f"{start_year}-{start_year + 1}"


def year_from_week_option(value: str) -> str | None:
    """'14.09.2026 00:00:00' -> '2026-2027'."""
    m = _DATE_RE.search(value or "")
    if not m:
        return None
    month, year = int(m.group(2)), int(m.group(3))
    return _span(year if month >= YEAR_START_MONTH else year - 1)


def year_from_donem_code(code: str) -> str | None:
    """'202504' -> '2025-2026'."""
    m = _DONEM_RE.match((code or "").strip())
    if not m:
        return None
    return _span(int(m.group(1)))


class YearResolution(NamedTuple):
    year: str | None
    status: str


def resolve_year(detected: str | None, stored: str | None) -> YearResolution:
    """Apply the two safety properties to a detection result.

    hold-last-known: an undetected year never overwrites what we know.
    forward-only:    a year earlier than the stored one is a glitch, not news.
    """
    if detected is None:
        if stored is None:
            return YearResolution(None, "unknown")
        return YearResolution(stored, "held")
    if stored is None:
        return YearResolution(detected, "initialized")
    if detected == stored:
        return YearResolution(stored, "current")
    if detected > stored:  # 'YYYY-YYYY' sorts chronologically as a string
        return YearResolution(detected, "rollover")
    return YearResolution(stored, "ignored_regression")


def load_year_state(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    return state if isinstance(state, dict) else {}


def save_year_state(path: str, year: str, previous: str | None,
                    source: str) -> dict:
    state = {
        "year": year,
        "previous": previous,
        "detected_at": datetime.now().isoformat(),
        "source": source,
        "grade": None,
    }
    atomic_json_dump(state, path)
    return state
