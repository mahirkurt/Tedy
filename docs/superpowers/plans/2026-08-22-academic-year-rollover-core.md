# Academic Year Rollover (Core) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect the academic year from the portal automatically, archive 2025-2026 before any new-year data overwrites it, and namespace Google Drive by year so the two never mix.

**Architecture:** A new `src/academic_year.py` resolves the current year from the portal's own selectors and persists it to `output/academic_year.json`, with hold-last-known and forward-only guards so a blocked page can never misfile a year. A new `src/archive_year.py` snapshots the previous year's JSON locally and moves its Drive folders under `TEDY/<year>/`. `run_sync.py` runs detection immediately after login and archives *before any scraper runs* — the ordering that makes the whole thing safe.

**Tech Stack:** Python 3, Selenium (read-only), Google Drive API v3, pytest, BeautifulSoup (already vendored in `scrape_all.py`).

**Spec:** `docs/superpowers/specs/2026-08-22-academic-year-rollover-design.md`

## Global Constraints

- All JSON writes use `atomic_json_dump()` from `src/json_utils.py` (write `.tmp`, then rename).
- No test may touch the live portal or live Google APIs. Use fakes/mocks.
- Academic year string format is exactly `YYYY-YYYY`, e.g. `2026-2027`.
- Dönem code format is `YYYY0Q` where `YYYY` is the year the term started, `Q` is 1–4.
- The portal is read-only. Never submit a form.
- Turkish field names in scraped data are preserved verbatim.
- Scripts import as `from src.<module> import <name>` (project root on `sys.path`).

---

### Task 1: Academic year parsing and resolution

Pure functions — no Selenium, no network. This is where the two safety
properties from the spec live.

**Files:**
- Create: `src/academic_year.py`
- Test: `tests/test_academic_year.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `year_from_week_option(value: str) -> str | None`
  - `year_from_donem_code(code: str) -> str | None`
  - `YearResolution` — `NamedTuple(year: str | None, status: str)`
  - `resolve_year(detected: str | None, stored: str | None) -> YearResolution`
  - `load_year_state(path: str) -> dict`
  - `save_year_state(path: str, year: str, previous: str | None, source: str) -> dict`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_academic_year.py
"""The academic year is derived from the portal's own selectors."""
import json
import pytest

from src.academic_year import (
    YearResolution,
    load_year_state,
    resolve_year,
    save_year_state,
    year_from_donem_code,
    year_from_week_option,
)


class TestYearFromWeekOption:
    def test_autumn_week_starts_the_year(self):
        # observed 2026-08-22: first option of #dp_icerik_secili_hafta
        assert year_from_week_option("14.09.2026 00:00:00") == "2026-2027"

    def test_single_digit_day_parses(self):
        assert year_from_week_option("5.10.2026 00:00:00") == "2026-2027"

    def test_spring_week_belongs_to_the_year_that_began_in_autumn(self):
        assert year_from_week_option("11.01.2027 00:00:00") == "2026-2027"

    def test_august_counts_as_the_new_year(self):
        assert year_from_week_option("31.08.2026 00:00:00") == "2026-2027"

    def test_july_still_belongs_to_the_previous_year(self):
        assert year_from_week_option("15.07.2026 00:00:00") == "2025-2026"

    def test_unparseable_value_returns_none(self):
        assert year_from_week_option("Tamamı") is None
        assert year_from_week_option("") is None


class TestYearFromDonemCode:
    def test_code_start_year_becomes_the_span(self):
        assert year_from_donem_code("202504") == "2025-2026"
        assert year_from_donem_code("202401") == "2024-2025"

    def test_rejects_malformed_codes(self):
        for bad in ("2025", "20250", "abcdef", "", "202500", "202505"):
            assert year_from_donem_code(bad) is None


class TestResolveYear:
    def test_first_detection_initialises(self):
        assert resolve_year("2026-2027", None) == \
            YearResolution("2026-2027", "initialized")

    def test_same_year_is_current(self):
        assert resolve_year("2026-2027", "2026-2027") == \
            YearResolution("2026-2027", "current")

    def test_later_year_is_a_rollover(self):
        assert resolve_year("2026-2027", "2025-2026") == \
            YearResolution("2026-2027", "rollover")

    def test_undetected_holds_the_stored_year(self):
        """A blocked page must never reset the year."""
        assert resolve_year(None, "2026-2027") == \
            YearResolution("2026-2027", "held")

    def test_earlier_year_is_ignored(self):
        """A year cannot un-happen; a stale page must not roll us back."""
        assert resolve_year("2025-2026", "2026-2027") == \
            YearResolution("2026-2027", "ignored_regression")

    def test_nothing_known_at_all(self):
        assert resolve_year(None, None) == YearResolution(None, "unknown")


class TestYearState:
    def test_missing_file_is_empty(self, tmp_path):
        assert load_year_state(str(tmp_path / "nope.json")) == {}

    def test_round_trip(self, tmp_path):
        p = str(tmp_path / "academic_year.json")
        saved = save_year_state(p, "2026-2027", "2025-2026", "week_selector")
        assert saved["year"] == "2026-2027"
        assert saved["previous"] == "2025-2026"
        assert saved["source"] == "week_selector"
        assert saved["grade"] is None
        assert "detected_at" in saved
        assert load_year_state(p) == saved

    def test_corrupted_state_is_empty_not_an_exception(self, tmp_path):
        p = tmp_path / "academic_year.json"
        p.write_text("{not json", encoding="utf-8")
        assert load_year_state(str(p)) == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_academic_year.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.academic_year'`

- [ ] **Step 3: Write the implementation**

```python
# src/academic_year.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_academic_year.py -q`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add src/academic_year.py tests/test_academic_year.py
git commit -m "feat: add academic year parsing and resolution"
```

---

### Task 2: Detect the year from the portal

Adds the Selenium reader. Tested with a fake driver — the same fake-element
pattern already used by `tests/test_extract_table.py`.

**Files:**
- Modify: `src/academic_year.py`
- Test: `tests/test_academic_year.py`

**Interfaces:**
- Consumes: `year_from_week_option`, `year_from_donem_code` (Task 1)
- Produces: `detect_academic_year(driver, base_url: str) -> tuple[str | None, str]`
  returning `(year, source)` where source is `"week_selector"`,
  `"donem_selector"` or `"none"`.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_academic_year.py
from src.academic_year import detect_academic_year


class FakeOption:
    def __init__(self, value, text=""):
        self._value, self.text = value, text

    def get_attribute(self, name):
        return self._value if name == "value" else None


class FakeSelect:
    def __init__(self, el_id, options):
        self.el_id, self._options = el_id, options

    def find_elements(self, _by, tag):
        return self._options if tag == "option" else []


class FakeDriver:
    """Serves selects per URL, the way the portal serves pages."""

    def __init__(self, pages):
        self.pages, self.current_url, self.visited = pages, "", []

    def get(self, url):
        self.current_url = url
        self.visited.append(url)

    def find_elements(self, _by, value):
        for sel in self.pages.get(self.current_url, []):
            if sel.el_id == value:
                return [sel]
        return []


BASE = "https://portal.tedronesans.k12.tr"
HOME = f"{BASE}/pages/ogrenci/"
GELISIM = f"{BASE}/pages/ogrenci_istekler/p_gelisim_raporum"

WEEKS = FakeSelect("dp_icerik_secili_hafta", [
    FakeOption("21.09.2026 00:00:00"),
    FakeOption("14.09.2026 00:00:00"),   # earliest, deliberately not first
    FakeOption("28.09.2026 00:00:00"),
])
DONEMS = FakeSelect("genel_icerik_dp_ilgili_donem", [
    FakeOption("202401"), FakeOption("202504"), FakeOption("202502"),
])


class TestDetectAcademicYear:
    def test_week_selector_wins(self):
        d = FakeDriver({HOME: [WEEKS], GELISIM: [DONEMS]})
        assert detect_academic_year(d, BASE) == ("2026-2027", "week_selector")

    def test_earliest_week_defines_the_year_regardless_of_order(self):
        d = FakeDriver({HOME: [WEEKS]})
        year, _ = detect_academic_year(d, BASE)
        assert year == "2026-2027"

    def test_falls_back_to_highest_donem_code(self):
        d = FakeDriver({HOME: [], GELISIM: [DONEMS]})
        assert detect_academic_year(d, BASE) == ("2025-2026", "donem_selector")

    def test_no_signal_returns_none(self):
        d = FakeDriver({HOME: [], GELISIM: []})
        assert detect_academic_year(d, BASE) == (None, "none")

    def test_does_not_visit_gelisim_when_home_answers(self):
        """Detection runs every sync; don't load a page we don't need."""
        d = FakeDriver({HOME: [WEEKS], GELISIM: [DONEMS]})
        detect_academic_year(d, BASE)
        assert GELISIM not in d.visited

    def test_a_thrown_driver_error_is_not_fatal(self):
        class Boom(FakeDriver):
            def find_elements(self, _by, value):
                raise RuntimeError("stale element")
        assert detect_academic_year(Boom({}), BASE) == (None, "none")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_academic_year.py -k Detect -q`
Expected: FAIL — `ImportError: cannot import name 'detect_academic_year'`

- [ ] **Step 3: Write the implementation**

```python
# append to src/academic_year.py
from selenium.webdriver.common.by import By

WEEK_SELECT_ID = "dp_icerik_secili_hafta"
DONEM_SELECT_ID = "genel_icerik_dp_ilgili_donem"


def _option_values(driver, element_id):
    try:
        els = driver.find_elements(By.ID, element_id)
    except Exception:
        return []
    values = []
    for el in els:
        try:
            for opt in el.find_elements(By.TAG_NAME, "option"):
                v = opt.get_attribute("value")
                if v:
                    values.append(v)
        except Exception:
            continue
    return values


def detect_academic_year(driver, base_url: str):
    """Ask the portal which year it is serving.

    Returns (year, source). Never raises - an undetectable year is reported
    as None so the caller can hold the last known value.
    """
    try:
        driver.get(f"{base_url}/pages/ogrenci/")
        weeks = [year_from_week_option(v)
                 for v in _option_values(driver, WEEK_SELECT_ID)]
        weeks = [w for w in weeks if w]
        if weeks:
            return min(weeks), "week_selector"

        driver.get(f"{base_url}/pages/ogrenci_istekler/p_gelisim_raporum")
        donems = [year_from_donem_code(v)
                  for v in _option_values(driver, DONEM_SELECT_ID)]
        donems = [d for d in donems if d]
        if donems:
            return max(donems), "donem_selector"
    except Exception:
        pass
    return None, "none"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_academic_year.py -q`
Expected: PASS (all tests, Task 1 and Task 2)

- [ ] **Step 5: Commit**

```bash
git add src/academic_year.py tests/test_academic_year.py
git commit -m "feat: detect academic year from portal selectors"
```

---

### Task 3: Local archive with manifest

**Files:**
- Create: `src/archive_year.py`
- Test: `tests/test_archive_year.py`

**Interfaces:**
- Consumes: `_count_section` from `src/data_validator.py`
- Produces:
  - `archive_dir(output_dir: str, year: str) -> str`
  - `archive_year_local(year: str, output_dir: str) -> dict` (the manifest)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_archive_year.py
"""A finished year is snapshotted before the next one overwrites it."""
import json
import os

from src.archive_year import archive_dir, archive_year_local

SCRAPED = {
    "scraped_at": "2026-08-22T10:00:08",
    "odevlerim": {"homework": {"rows": [{"Ders Adı": "Matematik"}]}},
    "gelisim_raporu": {"grades": [], "rubrics": [{"ders": "Müzik"}] * 24},
    "ders_icerikleri": {"Türkçe": [1, 2]},
    "takim_calismalari": {"activities": {"rows": []}},
    "ogep": {"sessions": {"rows": []}},
    "duyurular": {"announcements": []},
    "ders_programi": [],
    "takvim": [],
}


def _seed(out):
    os.makedirs(out, exist_ok=True)
    for name, payload in (
        ("scraped_data.json", SCRAPED),
        ("health.json", {"success": True}),
        ("classroom_sync.json", {"cw:1": {"last_hash": "abc"}}),
        ("eba_textbooks_uploaded.json", {"a": 1}),
        ("mebi_videos_uploaded.json", {}),
    ):
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            json.dump(payload, f)


def test_archive_copies_the_year_and_writes_a_manifest(tmp_path):
    out = str(tmp_path / "output")
    _seed(out)
    manifest = archive_year_local("2025-2026", out)

    d = archive_dir(out, "2025-2026")
    for name in ("scraped_data.json", "health.json", "classroom_sync.json",
                 "eba_textbooks_uploaded.json", "mebi_videos_uploaded.json",
                 "manifest.json"):
        assert os.path.exists(os.path.join(d, name)), name

    assert manifest["year"] == "2025-2026"
    assert manifest["grade"] is None
    assert manifest["source_scraped_at"] == "2026-08-22T10:00:08"
    assert manifest["drive_folder"] is None
    assert "archived_at" in manifest


def test_counts_come_from_the_shared_validator(tmp_path):
    out = str(tmp_path / "output")
    _seed(out)
    counts = archive_year_local("2025-2026", out)["counts"]
    assert counts["gelisim_raporu"] == 24   # grades + rubrics
    assert counts["odevlerim"] == 1
    assert counts["takim_calismalari"] == 0  # rows, not dict keys


def test_the_snapshot_is_a_copy_not_a_move(tmp_path):
    out = str(tmp_path / "output")
    _seed(out)
    archive_year_local("2025-2026", out)
    assert os.path.exists(os.path.join(out, "scraped_data.json"))


def test_archiving_twice_changes_nothing(tmp_path):
    out = str(tmp_path / "output")
    _seed(out)
    first = archive_year_local("2025-2026", out)

    # the live file moves on to the new year
    with open(os.path.join(out, "scraped_data.json"), "w", encoding="utf-8") as f:
        json.dump({"scraped_at": "2026-09-14T08:00:00"}, f)

    second = archive_year_local("2025-2026", out)
    assert second == first
    with open(os.path.join(archive_dir(out, "2025-2026"),
                           "scraped_data.json"), encoding="utf-8") as f:
        assert json.load(f)["scraped_at"] == "2026-08-22T10:00:08"


def test_missing_optional_files_are_skipped_not_fatal(tmp_path):
    out = str(tmp_path / "output")
    os.makedirs(out)
    with open(os.path.join(out, "scraped_data.json"), "w", encoding="utf-8") as f:
        json.dump(SCRAPED, f)
    manifest = archive_year_local("2025-2026", out)
    assert manifest["year"] == "2025-2026"
    assert not os.path.exists(
        os.path.join(archive_dir(out, "2025-2026"), "health.json"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_archive_year.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.archive_year'`

- [ ] **Step 3: Write the implementation**

```python
# src/archive_year.py
"""Snapshot a finished academic year before the next one overwrites it."""
import glob
import json
import os
import shutil
from datetime import datetime

from src.data_validator import SECTION_RULES, _count_section
from src.json_utils import atomic_json_dump

# Copied verbatim into the archive. Missing files are skipped.
ARCHIVED_FILES = ("scraped_data.json", "health.json", "classroom_sync.json")
ARCHIVED_GLOBS = ("*_uploaded.json",)


def archive_dir(output_dir: str, year: str) -> str:
    return os.path.join(output_dir, "archive", year)


def archive_year_local(year: str, output_dir: str) -> dict:
    """Copy the year's JSON into output/archive/<year>/ and describe it.

    Idempotent: once manifest.json exists the archive is sealed and this
    returns it untouched, so a repeated sync cannot overwrite a good
    snapshot with new-year data.
    """
    target = archive_dir(output_dir, year)
    manifest_path = os.path.join(target, "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            return json.load(f)

    os.makedirs(target, exist_ok=True)

    names = list(ARCHIVED_FILES)
    for pattern in ARCHIVED_GLOBS:
        names += [os.path.basename(p)
                  for p in glob.glob(os.path.join(output_dir, pattern))]

    for name in names:
        src_path = os.path.join(output_dir, name)
        if os.path.exists(src_path):
            shutil.copy2(src_path, os.path.join(target, name))

    scraped = {}
    scraped_path = os.path.join(target, "scraped_data.json")
    if os.path.exists(scraped_path):
        try:
            with open(scraped_path, encoding="utf-8") as f:
                scraped = json.load(f)
        except (json.JSONDecodeError, OSError):
            scraped = {}

    manifest = {
        "year": year,
        "grade": None,
        "archived_at": datetime.now().isoformat(),
        "counts": {s: _count_section(s, scraped) for s in SECTION_RULES},
        "drive_folder": None,
        "source_scraped_at": scraped.get("scraped_at", ""),
    }
    # written last: an interrupted archive is retried, never half-trusted
    atomic_json_dump(manifest, manifest_path)
    return manifest
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_archive_year.py -q`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add src/archive_year.py tests/test_archive_year.py
git commit -m "feat: snapshot a finished academic year locally"
```

---

### Task 4: Drive year root and folder move

**Files:**
- Modify: `src/sync_to_google.py` (add after `_get_or_create_folder`, line ~622)
- Modify: `src/archive_year.py`
- Test: `tests/test_drive_year_layout.py`

**Interfaces:**
- Consumes: `_get_or_create_folder(drive_service, name, parent_id=None)` (existing),
  `archive_year_local` (Task 3), `load_year_state` (Task 1)
- Produces:
  - `UnknownAcademicYear(RuntimeError)` in `src/sync_to_google.py`
  - `get_year_root(drive_service, year: str | None = None) -> str`
  - `move_root_folders(drive_service, names: list[str], parent_id: str) -> list[str]`
  - `archive_year_drive(year, output_dir, drive_service) -> dict`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_drive_year_layout.py
"""Drive is namespaced by academic year so two years never share a folder."""
import json
import os
import pytest

from src.sync_to_google import (
    UnknownAcademicYear, get_year_root, move_root_folders,
)
from src.archive_year import archive_year_drive


class FakeFiles:
    """Minimal stand-in for drive.files() with parent tracking."""

    def __init__(self, existing=None):
        self.store = dict(existing or {})   # id -> {name, parents}
        self._next = 100

    class _Req:
        def __init__(self, result):
            self._result = result

        def execute(self):
            return self._result

    def list(self, q="", **kw):
        name = q.split("name='", 1)[1].split("'", 1)[0] if "name='" in q else None
        parent = q.split("and '", 1)[1].split("' in parents", 1)[0] \
            if "' in parents" in q else None
        hits = [{"id": i, "parents": v.get("parents", [])}
                for i, v in self.store.items()
                if v["name"] == name
                and (parent in v.get("parents", []) if parent else
                     not v.get("parents"))]
        return self._Req({"files": hits})

    def create(self, body=None, **kw):
        self._next += 1
        fid = f"f{self._next}"
        self.store[fid] = {"name": body["name"],
                           "parents": body.get("parents", [])}
        return self._Req({"id": fid})

    def update(self, fileId=None, addParents=None, removeParents=None, **kw):
        self.store[fileId]["parents"] = [addParents]
        return self._Req({"id": fileId, "parents": [addParents]})


class FakeDrive:
    def __init__(self, existing=None):
        self._files = FakeFiles(existing)

    def files(self):
        return self._files


def test_year_root_is_tedy_slash_year():
    drive = FakeDrive()
    root = get_year_root(drive, "2026-2027")
    names = {v["name"] for v in drive._files.store.values()}
    assert names == {"TEDY", "2026-2027"}
    assert drive._files.store[root]["name"] == "2026-2027"


def test_year_root_is_reused_not_duplicated():
    drive = FakeDrive()
    assert get_year_root(drive, "2026-2027") == get_year_root(drive, "2026-2027")
    assert len(drive._files.store) == 2


def test_unknown_year_refuses_rather_than_misfiling(tmp_path, monkeypatch):
    """Better to skip an upload than to file it under the wrong year."""
    monkeypatch.setattr("src.sync_to_google.OUTPUT_DIR", str(tmp_path))
    with pytest.raises(UnknownAcademicYear):
        get_year_root(FakeDrive(), None)


def test_year_root_reads_stored_state_when_year_omitted(tmp_path, monkeypatch):
    monkeypatch.setattr("src.sync_to_google.OUTPUT_DIR", str(tmp_path))
    with open(tmp_path / "academic_year.json", "w", encoding="utf-8") as f:
        json.dump({"year": "2026-2027"}, f)
    drive = FakeDrive()
    root = get_year_root(drive, None)
    assert drive._files.store[root]["name"] == "2026-2027"


def test_move_reparents_existing_root_folders():
    drive = FakeDrive({
        "a": {"name": "Ödevler", "parents": []},
        "b": {"name": "Ders Kitapları", "parents": []},
    })
    parent = get_year_root(drive, "2025-2026")
    moved = move_root_folders(drive, ["Ödevler", "Ders Kitapları", "Yok"], parent)
    assert sorted(moved) == ["a", "b"]
    assert drive._files.store["a"]["parents"] == [parent]
    assert drive._files.store["b"]["parents"] == [parent]


def test_drive_archive_records_the_folder_id(tmp_path):
    out = str(tmp_path / "output")
    os.makedirs(out)
    with open(os.path.join(out, "scraped_data.json"), "w", encoding="utf-8") as f:
        json.dump({"scraped_at": "x"}, f)
    drive = FakeDrive({"a": {"name": "Ödevler", "parents": []}})
    manifest = archive_year_drive("2025-2026", out, drive)
    assert manifest["drive_folder"] is not None
    assert drive._files.store["a"]["parents"] == [manifest["drive_folder"]]


def test_drive_failure_still_leaves_a_local_archive(tmp_path):
    class Broken(FakeDrive):
        def files(self):
            raise RuntimeError("drive down")

    out = str(tmp_path / "output")
    os.makedirs(out)
    with open(os.path.join(out, "scraped_data.json"), "w", encoding="utf-8") as f:
        json.dump({"scraped_at": "x"}, f)
    manifest = archive_year_drive("2025-2026", out, Broken())
    assert manifest["year"] == "2025-2026"
    assert manifest["drive_folder"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_drive_year_layout.py -q`
Expected: FAIL — `ImportError: cannot import name 'UnknownAcademicYear'`

- [ ] **Step 3: Write the implementation**

Add to `src/sync_to_google.py`, immediately after `_get_or_create_folder`:

```python
DRIVE_ROOT_NAME = "TEDY"
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")


class UnknownAcademicYear(RuntimeError):
    """Refuse to upload rather than file content under the wrong year."""


def get_year_root(drive_service, year=None):
    """Return the id of TEDY/<year>/, creating it if needed."""
    if year is None:
        from src.academic_year import STATE_FILENAME, load_year_state
        year = load_year_state(
            os.path.join(OUTPUT_DIR, STATE_FILENAME)).get("year")
    if not year:
        raise UnknownAcademicYear(
            "academic year unknown - refusing to upload to Drive")
    tedy = _get_or_create_folder(drive_service, DRIVE_ROOT_NAME)
    return _get_or_create_folder(drive_service, year, parent_id=tedy)


def move_root_folders(drive_service, names, parent_id):
    """Re-parent existing Drive-root folders under parent_id. Returns moved ids."""
    moved = []
    for name in names:
        q = (f"name='{name}' and "
             f"mimeType='application/vnd.google-apps.folder' and "
             f"trashed=false")
        found = drive_service.files().list(
            q=q, spaces="drive", fields="files(id,parents)",
        ).execute().get("files", [])
        for f in found:
            if parent_id in (f.get("parents") or []):
                continue
            drive_service.files().update(
                fileId=f["id"], addParents=parent_id,
                removeParents=",".join(f.get("parents") or []),
                fields="id,parents",
            ).execute()
            moved.append(f["id"])
    return moved
```

Add to `src/archive_year.py`:

```python
# folders that lived at Drive root before year namespacing.
# The last two are created by scrape_sebitv_interactive.py; they do not exist
# yet (its tracker is empty) but are listed so a later run is still tidied.
# move_root_folders skips names it cannot find.
LEGACY_ROOT_FOLDERS = [
    "Ödevler", "Ders Kitapları", "MEBI Videolar",
    "SEBİTV Videolar", "TED Portal Ödevler",
    "SEBİTV Etkileşimli", "SEBİTV Soru Bankaları",
]


def archive_year_drive(year: str, output_dir: str, drive_service) -> dict:
    """Archive locally, then move the year's Drive folders under TEDY/<year>/.

    A Drive outage degrades to a local-only archive; the manifest records
    drive_folder=None and the next sync retries.
    """
    manifest = archive_year_local(year, output_dir)
    if manifest.get("drive_folder"):
        return manifest

    from src.sync_to_google import get_year_root, move_root_folders
    try:
        parent = get_year_root(drive_service, year)
        move_root_folders(drive_service, LEGACY_ROOT_FOLDERS, parent)
        manifest["drive_folder"] = parent
        atomic_json_dump(
            manifest, os.path.join(archive_dir(output_dir, year),
                                   "manifest.json"))
    except Exception as e:
        print(f"  [ARCHIVE] Drive step deferred: {type(e).__name__}: {e}")
    return manifest
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_drive_year_layout.py tests/test_archive_year.py -q`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add src/sync_to_google.py src/archive_year.py tests/test_drive_year_layout.py
git commit -m "feat: namespace Drive by academic year and move legacy folders"
```

---

### Task 5: Route every Drive upload through the year root

Six root-level `_get_or_create_folder` calls currently write to Drive root.
Each gains the year folder as its parent. Subject/unit subfolder calls already
pass an explicit `parent_id` and are left alone.

**Files:**
- Modify: `src/sync_to_google.py:540-542` — `"Ödevler"`
- Modify: `src/scrape_eba_textbooks.py:19,354` — `"Ders Kitapları"`
- Modify: `src/scrape_mebi_videos.py:21,261` — `"MEBI Videolar"`
- Modify: `src/scrape_sebitv.py:21,408` — `"SEBİTV Videolar"`
- Modify: `src/scrape_sebitv_interactive.py:22,449-455` — `"SEBİTV Etkileşimli"`
  and `"SEBİTV Soru Bankaları"`
- Test: `tests/test_drive_year_layout.py`

**Interfaces:**
- Consumes: `get_year_root` (Task 4)
- Produces: no new symbols

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_drive_year_layout.py
import inspect

import src.scrape_eba_textbooks as eba
import src.scrape_mebi_videos as mebi
import src.scrape_sebitv as sebitv
import src.scrape_sebitv_interactive as sebitv_i
import src.sync_to_google as stg


def test_no_content_root_is_created_at_drive_root():
    """Every content root must hang off TEDY/<year>/, never Drive root."""
    roots = [
        (stg, '"Ödevler"'),
        (eba, '"Ders Kitapları"'),
        (mebi, '"MEBI Videolar"'),
        (sebitv, '"SEBİTV Videolar"'),
        (sebitv_i, '"SEBİTV Etkileşimli"'),
        (sebitv_i, '"SEBİTV Soru Bankaları"'),
    ]
    for module, literal in roots:
        src = inspect.getsource(module)
        idx = src.find(literal)
        assert idx != -1, f"{module.__name__}: {literal} not found"
        window = src[max(0, idx - 300): idx + 200]
        assert ("parent_id" in window and
                ("get_year_root" in window or "year_root" in window)), (
            f"{module.__name__}: {literal} root folder is not year-scoped")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_drive_year_layout.py::test_no_content_root_is_created_at_drive_root -q`
Expected: FAIL — `sync_to_google: "Ödevler" root folder is not year-scoped`

- [ ] **Step 3: Update each call site**

In `src/sync_to_google.py` (~line 540) replace:

```python
    folder_id = _get_or_create_folder(
        drive_service, "Ödevler"
    )
```

with:

```python
    folder_id = _get_or_create_folder(
        drive_service, "Ödevler",
        parent_id=get_year_root(drive_service)
    )
```

In `src/scrape_eba_textbooks.py` line 354 replace:

```python
    root_id = _get_or_create_folder(drive_service, "Ders Kitapları")
```

with:

```python
    root_id = _get_or_create_folder(
        drive_service, "Ders Kitapları",
        parent_id=get_year_root(drive_service))
```

and extend its import on line 19 to:

```python
from src.sync_to_google import get_services, _get_or_create_folder, get_year_root
```

In `src/scrape_mebi_videos.py` line 261 replace:

```python
    root_id = _get_or_create_folder(drive_service, "MEBI Videolar")
```

with:

```python
    root_id = _get_or_create_folder(
        drive_service, "MEBI Videolar",
        parent_id=get_year_root(drive_service))
```

and extend its import on line 21 the same way.

In `src/scrape_sebitv.py` line 21 replace the import with:

```python
from src.sync_to_google import get_services, _get_or_create_folder, get_year_root
```

and at line ~408 replace (note the variable is `drive`, not `drive_service`):

```python
    root_id = _get_or_create_folder(
        drive, "SEBİTV Videolar"
    )
```

with:

```python
    root_id = _get_or_create_folder(
        drive, "SEBİTV Videolar",
        parent_id=get_year_root(drive)
    )
```

In `src/scrape_sebitv_interactive.py` line 22 replace the import with:

```python
from src.sync_to_google import get_services, _get_or_create_folder, get_year_root
```

then at line ~449 replace **both** root calls:

```python
    # Drive folders for archives
    archive_root_id = _get_or_create_folder(
        drive, "SEBİTV Etkileşimli"
    )
    # Drive folders for question banks
    qbank_root_id = _get_or_create_folder(
        drive, "SEBİTV Soru Bankaları"
    )
```

with:

```python
    year_root = get_year_root(drive)
    # Drive folders for archives
    archive_root_id = _get_or_create_folder(
        drive, "SEBİTV Etkileşimli", parent_id=year_root
    )
    # Drive folders for question banks
    qbank_root_id = _get_or_create_folder(
        drive, "SEBİTV Soru Bankaları", parent_id=year_root
    )
```

The other `_get_or_create_folder` calls in that file (lines ~534, ~542, ~577,
~586) already pass an explicit `parent_id` and must not be changed.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_drive_year_layout.py -q && python3 -m pytest -q`
Expected: PASS (new test passes, full suite still green)

- [ ] **Step 5: Commit**

```bash
git add src/sync_to_google.py src/scrape_eba_textbooks.py \
        src/scrape_mebi_videos.py src/scrape_sebitv.py \
        src/scrape_sebitv_interactive.py tests/test_drive_year_layout.py
git commit -m "feat: route all Drive uploads through the year root"
```

---

### Task 6: Wire detection and archiving into the sync

The ordering constraint from the spec: detect after login, archive **before any
scraper runs**. Archiving later would snapshot new-year data under the old
year's name and lose the old year for good.

**Files:**
- Modify: `src/run_sync.py`
- Test: `tests/test_year_rollover_sync.py`

**Interfaces:**
- Consumes: `detect_academic_year`, `resolve_year`, `load_year_state`,
  `save_year_state` (Tasks 1-2); `archive_year_drive` (Task 4)
- Produces: `run_year_rollover(driver, output_dir, base_url, drive_factory) -> dict`
  in `src/run_sync.py`, returning
  `{"year", "status", "source", "archived": bool, "manifest": dict | None}`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_year_rollover_sync.py
"""Rollover archives the old year before any new-year data is written."""
import json
import os

from src.run_sync import run_year_rollover

BASE = "https://portal.tedronesans.k12.tr"


class StubDriver:
    def __init__(self, year):
        self.year = year

    def get(self, url):
        pass


def _patch_detect(monkeypatch, year, source="week_selector"):
    monkeypatch.setattr("src.run_sync.detect_academic_year",
                        lambda d, b: (year, source))


def _seed(out, scraped_at="2026-08-22T10:00:08"):
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "scraped_data.json"), "w", encoding="utf-8") as f:
        json.dump({"scraped_at": scraped_at}, f)


def test_first_run_records_the_year_without_archiving(tmp_path, monkeypatch):
    out = str(tmp_path); _seed(out)
    _patch_detect(monkeypatch, "2026-2027")
    r = run_year_rollover(StubDriver("x"), out, BASE, lambda: None)
    assert r["status"] == "initialized"
    assert r["archived"] is False
    assert not os.path.exists(os.path.join(out, "archive"))


def test_rollover_archives_the_previous_year(tmp_path, monkeypatch):
    out = str(tmp_path); _seed(out)
    with open(os.path.join(out, "academic_year.json"), "w", encoding="utf-8") as f:
        json.dump({"year": "2025-2026"}, f)
    _patch_detect(monkeypatch, "2026-2027")

    r = run_year_rollover(StubDriver("x"), out, BASE, lambda: None)
    assert r["status"] == "rollover"
    assert r["archived"] is True
    snap = os.path.join(out, "archive", "2025-2026", "scraped_data.json")
    with open(snap, encoding="utf-8") as f:
        assert json.load(f)["scraped_at"] == "2026-08-22T10:00:08"
    with open(os.path.join(out, "academic_year.json"), encoding="utf-8") as f:
        assert json.load(f)["year"] == "2026-2027"


def test_same_year_does_not_archive(tmp_path, monkeypatch):
    out = str(tmp_path); _seed(out)
    with open(os.path.join(out, "academic_year.json"), "w", encoding="utf-8") as f:
        json.dump({"year": "2026-2027"}, f)
    _patch_detect(monkeypatch, "2026-2027")
    r = run_year_rollover(StubDriver("x"), out, BASE, lambda: None)
    assert r["status"] == "current"
    assert r["archived"] is False


def test_undetected_year_holds_and_does_not_archive(tmp_path, monkeypatch):
    out = str(tmp_path); _seed(out)
    with open(os.path.join(out, "academic_year.json"), "w", encoding="utf-8") as f:
        json.dump({"year": "2026-2027"}, f)
    _patch_detect(monkeypatch, None, "none")
    r = run_year_rollover(StubDriver("x"), out, BASE, lambda: None)
    assert r["status"] == "held"
    assert r["year"] == "2026-2027"
    assert r["archived"] is False


def test_regression_is_ignored_and_never_archives(tmp_path, monkeypatch):
    out = str(tmp_path); _seed(out)
    with open(os.path.join(out, "academic_year.json"), "w", encoding="utf-8") as f:
        json.dump({"year": "2026-2027"}, f)
    _patch_detect(monkeypatch, "2025-2026")
    r = run_year_rollover(StubDriver("x"), out, BASE, lambda: None)
    assert r["status"] == "ignored_regression"
    assert r["archived"] is False
    assert not os.path.exists(os.path.join(out, "archive"))


def test_drive_unavailable_still_archives_locally(tmp_path, monkeypatch):
    out = str(tmp_path); _seed(out)
    with open(os.path.join(out, "academic_year.json"), "w", encoding="utf-8") as f:
        json.dump({"year": "2025-2026"}, f)
    _patch_detect(monkeypatch, "2026-2027")

    def boom():
        raise RuntimeError("no credentials")

    r = run_year_rollover(StubDriver("x"), out, BASE, boom)
    assert r["archived"] is True
    assert r["manifest"]["drive_folder"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_year_rollover_sync.py -q`
Expected: FAIL — `ImportError: cannot import name 'run_year_rollover'`

- [ ] **Step 3: Add the function to `src/run_sync.py`**

Extend the imports at the top of the file:

```python
from src.academic_year import (  # noqa: E402
    STATE_FILENAME,
    detect_academic_year,
    load_year_state,
    resolve_year,
    save_year_state,
)
from src.archive_year import archive_year_drive  # noqa: E402
```

Add above `def main():`:

```python
BASE_URL = "https://portal.tedronesans.k12.tr"


def run_year_rollover(driver, output_dir, base_url, drive_factory):
    """Resolve the academic year and archive the previous one if it changed.

    MUST run before any scraper: archiving afterwards would snapshot
    new-year data under the old year's name and lose the old year.
    """
    state_path = os.path.join(output_dir, STATE_FILENAME)
    stored = load_year_state(state_path).get("year")
    detected, source = detect_academic_year(driver, base_url)
    resolution = resolve_year(detected, stored)

    result = {"year": resolution.year, "status": resolution.status,
              "source": source, "archived": False, "manifest": None}
    print(f"[YEAR] {resolution.status}: {stored or '-'} -> {resolution.year} "
          f"(source: {source})")

    if resolution.status == "rollover":
        try:
            drive_service = drive_factory()
        except Exception as e:
            print(f"  [ARCHIVE] Drive unavailable: {type(e).__name__}: {e}")
            drive_service = None
        result["manifest"] = archive_year_drive(stored, output_dir, drive_service)
        result["archived"] = True
        print(f"  [ARCHIVE] {stored} sealed "
              f"({result['manifest'].get('counts', {})})")

    if resolution.year and resolution.status in (
            "initialized", "rollover", "current"):
        save_year_state(state_path, resolution.year,
                        stored if resolution.status == "rollover" else
                        load_year_state(state_path).get("previous"),
                        source)
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_year_rollover_sync.py -q`
Expected: PASS (all tests)

- [ ] **Step 5: Call it from `main()` and record it in health**

In `src/run_sync.py`, immediately after the successful-login block and
**before** `data = {"scraped_at": ...}`, insert:

```python
        def _drive_factory():
            from src.sync_to_google import get_services
            return get_services()[1]

        year_info = run_year_rollover(
            driver, OUTPUT_DIR, BASE_URL, _drive_factory)
```

Initialise `year_info` next to `unavailable = {}` so it exists on the
login-failure path:

```python
    year_info = {"year": None, "status": "unknown",
                 "source": "none", "archived": False, "manifest": None}
```

Add to the `health` dict, after `"unavailable": unavailable,`:

```python
        "academic_year": year_info["year"],
        "year_detection": year_info["status"],
        "year_archived": year_info["archived"],
```

- [ ] **Step 6: Run the full suite**

Run: `python3 -m pytest -q`
Expected: PASS — no regressions

- [ ] **Step 7: Verify the module still imports under the cron venv**

Run: `.venv/bin/python -c "import src.run_sync; print('ok')"`
Expected: `ok`

This guards the failure seen on 2026-08-22, where `py_compile` passed but the
import graph was only proven separately. Cron uses `.venv/bin/python`, not the
system interpreter.

- [ ] **Step 8: Commit**

```bash
git add src/run_sync.py tests/test_year_rollover_sync.py
git commit -m "feat: detect and archive academic year rollover during sync"
```

---

## Post-plan verification

After Task 6, before considering this done:

- [ ] `python3 -m pytest -q` — full suite green
- [ ] `.venv/bin/python -c "import src.run_sync"` — cron interpreter can load it
- [ ] Confirm `output/academic_year.json` appears after the next cron sync and
      reads `"year": "2026-2027"`, `"previous": "2025-2026"`
- [ ] Confirm `output/archive/2025-2026/manifest.json` exists with non-zero
      `counts.gelisim_raporu`
- [ ] Confirm Drive root now holds `TEDY/` and that `TEDY/2025-2026/` contains
      the five former root folders
- [ ] Confirm `health.json` reports `academic_year`, `year_detection`,
      `year_archived`

**Do not edit `src/run_sync.py` while a cron sync is in flight.** On
2026-08-22 an edit landed 7 seconds after cron started and the run used a
half-old module. Check `stat -c %y output/health.json` and the `*/15` schedule
before the final verification run.
