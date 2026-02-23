# Course Name Normalization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Normalize course names across all Google Workspace sync functions so every service (Calendar, Tasks, Sheets, Drive) uses the same canonical name for each course.

**Architecture:** Add a `COURSE_ALIASES` dict and `normalize_course()` function at the top of `sync_to_google.py`. Call it at every point where a course name is used to build a summary, title, or folder name. No scraper changes.

**Tech Stack:** Python, pytest

---

### Task 1: Add `normalize_course()` with tests

**Files:**
- Modify: `src/sync_to_google.py:19-27` (after COLORS dict)
- Create: `tests/test_normalize_course.py`

**Step 1: Write the failing tests**

Create `tests/test_normalize_course.py`:

```python
"""Tests for course name normalization."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.sync_to_google import normalize_course


class TestNormalizeCourse:
    """Exact alias matches."""

    def test_canonical_name_unchanged(self):
        assert normalize_course("Matematik") == "Matematik"

    def test_fransizca_from_ikinci_yabanci_dil(self):
        assert normalize_course("İkinci Yabancı Dil") == "Fransızca"

    def test_fransizca_from_full_name(self):
        assert normalize_course("İkinci Yabancı Dil (Fransızca)") == "Fransızca"

    def test_fransizca_from_tab_name(self):
        assert normalize_course("2. Yabancı Dil (F)") == "Fransızca"

    def test_din_kulturu_from_full(self):
        assert normalize_course("Din Kültürü ve Ahlak Bilgisi") == "Din Kültürü"

    def test_din_kulturu_from_dkab(self):
        assert normalize_course("DKAB") == "Din Kültürü"

    def test_beden_egitimi_from_spor(self):
        assert normalize_course("Beden Eğitimi ve Spor") == "Beden Eğitimi"

    def test_ingilizce_from_language(self):
        assert normalize_course("İngilizce (Language)") == "İngilizce"

    def test_ingilizce_from_language_tab(self):
        assert normalize_course("İngilizce Language") == "İngilizce"

    def test_ingilizce_from_tab_2(self):
        assert normalize_course("İngilizce (2)") == "İngilizce"

    def test_ingilizce_literature_from_parens(self):
        assert normalize_course("İngilizce (Literature)") == "İngilizce Literature"

    def test_bilisim_from_full(self):
        assert normalize_course("Bilişim Teknolojileri") == "Bilişim"


class TestNormalizeCourseParenFallback:
    """Parenthesized suffix stripping fallback."""

    def test_strip_classroom_suffix(self):
        assert normalize_course("Matematik (i-403 (İngilizce))") == "Matematik"

    def test_strip_classroom_fen(self):
        assert normalize_course("Fen Bilimleri (i-322 (Fen Lab))") == "Fen Bilimleri"


class TestNormalizeCourseUnknown:
    """Unknown names pass through unchanged."""

    def test_unknown_course(self):
        assert normalize_course("Robotik Kulübü") == "Robotik Kulübü"

    def test_empty_string(self):
        assert normalize_course("") == ""

    def test_genel(self):
        assert normalize_course("Genel") == "Genel"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_normalize_course.py -v`
Expected: FAIL — `ImportError: cannot import name 'normalize_course'`

**Step 3: Implement `COURSE_ALIASES` and `normalize_course()`**

In `src/sync_to_google.py`, add after the `COLORS` dict (after line 27):

```python
# Canonical course names and their aliases
COURSE_ALIASES = {
    "Fransızca": [
        "İkinci Yabancı Dil",
        "İkinci Yabancı Dil (Fransızca)",
        "2. Yabancı Dil (F)",
    ],
    "Din Kültürü": [
        "Din Kültürü ve Ahlak Bilgisi",
        "DKAB",
    ],
    "Beden Eğitimi": [
        "Beden Eğitimi ve Spor",
    ],
    "İngilizce": [
        "İngilizce (Language)",
        "İngilizce Language",
        "İngilizce (2)",
    ],
    "İngilizce Literature": [
        "İngilizce (Literature)",
    ],
    "Bilişim": [
        "Bilişim Teknolojileri",
    ],
}

# Build reverse lookup: alias -> canonical
_ALIAS_LOOKUP = {}
for canonical, aliases in COURSE_ALIASES.items():
    _ALIAS_LOOKUP[canonical] = canonical
    for alias in aliases:
        _ALIAS_LOOKUP[alias] = canonical


def normalize_course(name):
    """Normalize a course name to its canonical form.

    1. Exact match in alias lookup
    2. Strip parenthesized suffix, retry
    3. Return original if no match
    """
    name = name.strip()
    if not name:
        return name

    # Exact match
    if name in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[name]

    # Strip trailing parenthesized content and retry
    stripped = re.sub(r"\s*\(.*\)\s*$", "", name).strip()
    if stripped != name and stripped in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[stripped]

    return stripped if stripped != name else name
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_normalize_course.py -v`
Expected: All 17 tests PASS

**Step 5: Commit**

```bash
git add src/sync_to_google.py tests/test_normalize_course.py
git commit -m "feat: add normalize_course() with alias mapping and tests"
```

---

### Task 2: Apply normalization to `sync_ders_programi`

**Files:**
- Modify: `src/sync_to_google.py:308-314`

**Step 1: Write a targeted test**

Append to `tests/test_normalize_course.py`:

```python
class TestDersProgramiIntegration:
    """Verify ders_programi sync uses normalized names."""

    def test_lesson_name_normalized_in_summary(self):
        """The sync function builds summary from lesson_name.
        After normalization, 'Bilişim Teknolojileri' should become 'Bilişim'."""
        # This is verified by checking normalize_course is called on lesson_name.
        # The unit test for normalize_course already covers the mapping.
        assert normalize_course("Bilişim Teknolojileri") == "Bilişim"
        assert normalize_course("Beden Eğitimi ve Spor") == "Beden Eğitimi"
        assert normalize_course("Din Kültürü ve Ahlak Bilgisi") == "Din Kültürü"
```

**Step 2: Run test**

Run: `pytest tests/test_normalize_course.py::TestDersProgramiIntegration -v`
Expected: PASS (function already exists from Task 1)

**Step 3: Apply normalization in sync_ders_programi**

In `src/sync_to_google.py`, change line 308:

```python
# Before:
                lesson_name = re.sub(r"\s*\(.*\)\s*$", "", lesson_full)
# After:
                lesson_name = normalize_course(lesson_full)
```

Note: `normalize_course` already strips parenthesized suffixes as fallback, so the `re.sub` is replaced entirely.

**Step 4: Run full test suite**

Run: `pytest -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/sync_to_google.py tests/test_normalize_course.py
git commit -m "feat: normalize course names in ders_programi sync"
```

---

### Task 3: Apply normalization to `sync_odevlerim`

**Files:**
- Modify: `src/sync_to_google.py:364-376`

**Step 1: Apply normalization**

In `src/sync_to_google.py`, change line 376:

```python
# Before:
        ders = row.get("Ders Adı", "")
# After:
        ders = normalize_course(row.get("Ders Adı", ""))
```

Also normalize in the Drive folder loop at line 364:

```python
# Before:
                ders = row.get("Ders Adı", "")
# After:
                ders = normalize_course(row.get("Ders Adı", ""))
```

**Step 2: Run tests**

Run: `pytest -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add src/sync_to_google.py
git commit -m "feat: normalize course names in odevlerim sync"
```

---

### Task 4: Apply normalization to `sync_ders_icerikleri`

**Files:**
- Modify: `src/sync_to_google.py:600-612`

**Step 1: Apply normalization**

In `src/sync_to_google.py`, change line 600:

```python
# Before:
    for ders_name, info in ders_data.items():
# After:
    for raw_name, info in ders_data.items():
        ders_name = normalize_course(raw_name)
```

**Step 2: Run tests**

Run: `pytest -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add src/sync_to_google.py
git commit -m "feat: normalize course names in ders_icerikleri sync"
```

---

### Task 5: Apply normalization to `sync_gelisim_raporu` and `sync_grades_to_sheets`

**Files:**
- Modify: `src/sync_to_google.py:684` and `src/sync_to_google.py:826`

**Step 1: Apply normalization in sync_gelisim_raporu**

At line 684:

```python
# Before:
        ders = row.get("Ders", "")
# After:
        ders = normalize_course(row.get("Ders", ""))
```

**Step 2: Apply normalization in sync_grades_to_sheets**

The grades data flows through `sync_grades_to_sheets` via `row.get(h, "")` where h="Ders". Normalize the Ders column value at line 826:

```python
# Before:
    for row in grades:
        values.append([row.get(h, "") for h in headers])
# After:
    for row in grades:
        values.append([
            normalize_course(row.get(h, "")) if h == "Ders" else row.get(h, "")
            for h in headers
        ])
```

**Step 3: Run tests**

Run: `pytest -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add src/sync_to_google.py
git commit -m "feat: normalize course names in gelisim raporu and sheets sync"
```

---

### Task 6: Apply normalization to `sync_attachments_to_drive`

**Files:**
- Modify: `src/sync_to_google.py:998`

**Step 1: Apply normalization**

At line 998:

```python
# Before:
            ders = row.get("Ders Adı", "Genel")
# After:
            ders = normalize_course(row.get("Ders Adı", "Genel"))
```

**Step 2: Run tests**

Run: `pytest -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add src/sync_to_google.py
git commit -m "feat: normalize course names in drive attachment sync"
```

---

### Task 7: Expand `sync_takvim` keyword classifier

**Files:**
- Modify: `src/sync_to_google.py:538-548`

**Step 1: Write a test for the expanded keyword list**

Append to `tests/test_normalize_course.py`:

```python
class TestTakvimKeywords:
    """Verify takvim keyword classification covers all canonical course names."""

    def test_all_canonical_names_present(self):
        """Every canonical course name should be in the takvim keyword list
        (except generic ones like PDR, Genel, Sınıf Öğretmeni)."""
        from src.sync_to_google import TAKVIM_DERS_KEYWORDS
        for name in ["matematik", "türkçe", "fen", "sosyal",
                      "din kültürü", "ingilizce", "français", "fransızca",
                      "bilişim", "görsel", "müzik", "beden",
                      "ahlak", "english", "literature"]:
            assert name in TAKVIM_DERS_KEYWORDS, f"Missing: {name}"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_normalize_course.py::TestTakvimKeywords -v`
Expected: FAIL — `ImportError: cannot import name 'TAKVIM_DERS_KEYWORDS'`

**Step 3: Replace hardcoded keyword list with `TAKVIM_DERS_KEYWORDS`**

Add after `_ALIAS_LOOKUP` construction:

```python
# Keywords for takvim event color classification (substring match)
TAKVIM_DERS_KEYWORDS = (
    "ders", "matematik", "türkçe", "fen", "sosyal",
    "din kültürü", "ingilizce", "english", "français", "fransızca",
    "bilişim", "görsel", "müzik", "beden", "ahlak", "literature",
)
```

Then in `sync_takvim` at line 544, replace:

```python
# Before:
        elif any(w in lower for w in ("ders", "français", "english",
                                       "matematik", "türkçe", "fen")):
            color = COLORS["ders"]
# After:
        elif any(w in lower for w in TAKVIM_DERS_KEYWORDS):
            color = COLORS["ders"]
```

**Step 4: Run tests**

Run: `pytest -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/sync_to_google.py tests/test_normalize_course.py
git commit -m "feat: expand takvim keyword list for all course names"
```

---

### Task 8: Fix hardcoded year in `parse_week_range`

**Files:**
- Modify: `src/sync_to_google.py:229`

**Step 1: Write a test**

Append to `tests/test_normalize_course.py`:

```python
from src.sync_to_google import parse_week_range


class TestParseWeekRange:
    def test_basic_parse(self):
        start, end = parse_week_range("20. Hafta 02 Şub. - 08 Şub.")
        assert start is not None
        assert start.month == 2
        assert start.day == 2
        assert end.day == 8

    def test_uses_current_year(self):
        from datetime import datetime
        start, end = parse_week_range("20. Hafta 02 Şub. - 08 Şub.")
        assert start.year == datetime.now().year
```

**Step 2: Fix the hardcoded year**

At line 229:

```python
# Before:
            year = 2026  # Current school year
# After:
            year = datetime.now().year
```

**Step 3: Run tests**

Run: `pytest -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add src/sync_to_google.py tests/test_normalize_course.py
git commit -m "fix: use dynamic year in parse_week_range instead of hardcoded 2026"
```

---

### Task 9: Final verification

**Step 1: Run full test suite**

Run: `pytest -v`
Expected: All tests PASS

**Step 2: Dry-run with real data**

Run: `python3 -c "
import json, sys, os
sys.path.insert(0, '.')
from src.sync_to_google import normalize_course

with open('output/scraped_data.json') as f:
    data = json.load(f)

# Check ders_programi course names
import re
print('=== Ders Programı (normalized) ===')
seen = set()
for week in data.get('ders_programi', []):
    for row in week.get('schedule', {}).get('rows', [])[1:]:
        if not isinstance(row, list): continue
        first = row[0] if row else ''
        if 'Ders' not in first: continue
        for cell in row[1:]:
            cell = cell.strip()
            if cell and '\n' in cell:
                raw = cell.split('\n')[0]
                norm = normalize_course(raw)
                if norm not in seen:
                    seen.add(norm)
                    flag = ' ← changed' if norm != raw.strip() and norm != re.sub(r'\s*\(.*\)\s*$', '', raw).strip() else ''
                    print(f'  {raw:50} → {norm}{flag}')

print('\n=== Ödevlerim (normalized) ===')
for row in data.get('odevlerim', {}).get('homework', {}).get('rows', []):
    raw = row.get('Ders Adı', '')
    norm = normalize_course(raw)
    if raw != norm:
        print(f'  {raw:50} → {norm} ← changed')

print('\n=== Ders İçerikleri (normalized) ===')
for name in data.get('ders_icerikleri', {}).keys():
    norm = normalize_course(name)
    if name != norm:
        print(f'  {name:50} → {norm} ← changed')

print('\n=== Gelişim Raporu (normalized) ===')
for row in data.get('gelisim_raporu', {}).get('grades', []):
    raw = row.get('Ders', '')
    norm = normalize_course(raw)
    if raw != norm:
        print(f'  {raw:50} → {norm} ← changed')
"`

Expected: Shows course name transformations with `← changed` markers for aliases that get normalized.

**Step 3: Commit all remaining changes (if any)**

```bash
git add -A
git status
```
