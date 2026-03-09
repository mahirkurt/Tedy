# Reliability & AI Enrichment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden the TED sync pipeline against failures and expand AI enrichment to cover sınav, ders içerikleri, and performans data.

**Architecture:** Phase 1 wraps scrapers in try-except, adds retry to Google API calls, writes health status, and moves credentials to .env. Phase 2 renames `enrich_odev_gemini.py` to `enrich_gemini.py` and adds three new enrichment functions reusing the existing ModelRouter. Phase 3 integrates enrichment into `run_sync.py` as a post-sync step.

**Tech Stack:** Python 3, Google Calendar/Tasks API, Gemini API, Ollama (local), pytest

---

### Task 1: Shared .env Loader Utility

**Files:**
- Create: `src/env_loader.py`
- Test: `tests/test_env_loader.py`

**Step 1: Write the failing test**

```python
# tests/test_env_loader.py
"""Tests for .env loader utility."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.env_loader import load_env


class TestLoadEnv:
    def test_loads_key_value(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("FOO=bar\nBAZ=qux\n")
        load_env(str(env_file))
        assert os.environ.get("FOO") == "bar"
        assert os.environ.get("BAZ") == "qux"

    def test_skips_comments_and_blanks(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\n\nKEY1=val1\n")
        load_env(str(env_file))
        assert os.environ.get("KEY1") == "val1"

    def test_handles_equals_in_value(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=abc=def=ghi\n")
        load_env(str(env_file))
        assert os.environ.get("API_KEY") == "abc=def=ghi"

    def test_missing_file_no_error(self):
        load_env("/nonexistent/.env")  # should not raise
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_env_loader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.env_loader'`

**Step 3: Write minimal implementation**

```python
# src/env_loader.py
"""Load environment variables from a .env file."""
import os


def load_env(path=None):
    """Load key=value pairs from a .env file into os.environ.

    Skips comments (#) and blank lines. Safe if file doesn't exist.
    """
    if path is None:
        path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", ".env",
        )
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_env_loader.py -v`
Expected: 4 PASSED

**Step 5: Commit**

```bash
git add src/env_loader.py tests/test_env_loader.py
git commit -m "feat: add shared .env loader utility"
```

---

### Task 2: Move Portal Credentials to .env

**Files:**
- Modify: `src/login.py:37,123-128`
- Modify: `.env`
- Modify: `src/scrape_all.py` (find hardcoded credentials call)

**Step 1: Add credentials to .env**

Append to `.env`:
```
PORTAL_USERNAME=isik.kurt
PORTAL_PASSWORD=Mkhu7979
```

**Step 2: Update login() to accept credentials from caller (not hardcoded)**

In `src/login.py`, the function signature already accepts `username` and `password` parameters. The hardcoded values are only in `__main__` block (lines 124-125). Update `__main__`:

```python
# src/login.py __main__ block (replace lines 123-137)
if __name__ == "__main__":
    from src.env_loader import load_env
    load_env()

    driver, cookies = login(
        username=os.environ.get("PORTAL_USERNAME", ""),
        password=os.environ.get("PORTAL_PASSWORD", ""),
        role="ogrenci",
    )

    if driver:
        print("\n=== Login successful ===")
        print(f"Page title: {driver.title}")
        print(f"URL: {driver.current_url}")
        driver.quit()
    else:
        print("\n=== Login failed ===")
```

**Step 3: Update scrape_all.py to load credentials from .env**

Find where `login()` is called in `src/scrape_all.py` with hardcoded username/password and replace with env vars. In `src/scrape_all.py`, find the login call and change to:

```python
from src.env_loader import load_env
load_env()

# In the login call:
username=os.environ.get("PORTAL_USERNAME", "")
password=os.environ.get("PORTAL_PASSWORD", "")
```

**Step 4: Verify login still works**

Run: `python -c "from src.env_loader import load_env; load_env(); import os; print(os.environ.get('PORTAL_USERNAME'))"`
Expected: `isik.kurt`

**Step 5: Commit**

```bash
git add src/login.py src/scrape_all.py .env src/env_loader.py
git commit -m "security: move portal credentials from hardcoded to .env"
```

---

### Task 3: Atomic JSON Writes

**Files:**
- Create: `src/json_utils.py`
- Test: `tests/test_json_utils.py`

**Step 1: Write the failing test**

```python
# tests/test_json_utils.py
"""Tests for atomic JSON write utility."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.json_utils import atomic_json_dump


class TestAtomicJsonDump:
    def test_writes_valid_json(self, tmp_path):
        path = str(tmp_path / "data.json")
        atomic_json_dump({"key": "value"}, path)
        with open(path) as f:
            assert json.load(f) == {"key": "value"}

    def test_no_tmp_file_left(self, tmp_path):
        path = str(tmp_path / "data.json")
        atomic_json_dump({"a": 1}, path)
        assert not os.path.exists(path + ".tmp")

    def test_overwrites_existing(self, tmp_path):
        path = str(tmp_path / "data.json")
        atomic_json_dump({"v": 1}, path)
        atomic_json_dump({"v": 2}, path)
        with open(path) as f:
            assert json.load(f)["v"] == 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_json_utils.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# src/json_utils.py
"""Atomic JSON file operations."""
import json
import os


def atomic_json_dump(data, path, **kwargs):
    """Write JSON atomically: write to .tmp then rename.

    Prevents corrupted JSON from partial writes on crash.
    """
    kwargs.setdefault("indent", 2)
    kwargs.setdefault("ensure_ascii", False)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, **kwargs)
    os.replace(tmp, path)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_json_utils.py -v`
Expected: 3 PASSED

**Step 5: Commit**

```bash
git add src/json_utils.py tests/test_json_utils.py
git commit -m "feat: add atomic JSON write utility"
```

---

### Task 4: API Retry Logic in sync_to_google.py

**Files:**
- Modify: `src/sync_to_google.py:221-238,240-277`
- Test: `tests/test_retry.py`

**Step 1: Write the failing test**

```python
# tests/test_retry.py
"""Tests for Google API retry logic."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.sync_to_google import _api_call_with_retry


class _FakeHttpError(Exception):
    def __init__(self, status):
        self.resp = type("R", (), {"status": status})()
        super().__init__(f"HTTP {status}")


class TestApiRetry:
    def test_success_on_first_try(self):
        calls = []
        def fn():
            calls.append(1)
            return "ok"
        assert _api_call_with_retry(fn) == "ok"
        assert len(calls) == 1

    def test_retries_on_503(self):
        attempts = []
        def fn():
            attempts.append(1)
            if len(attempts) < 3:
                raise _FakeHttpError(503)
            return "ok"
        assert _api_call_with_retry(fn, max_retries=3, base_delay=0) == "ok"
        assert len(attempts) == 3

    def test_gives_up_after_max_retries(self):
        def fn():
            raise _FakeHttpError(503)
        result = _api_call_with_retry(fn, max_retries=2, base_delay=0)
        assert result is None

    def test_no_retry_on_400(self):
        attempts = []
        def fn():
            attempts.append(1)
            raise _FakeHttpError(400)
        result = _api_call_with_retry(fn, max_retries=3, base_delay=0)
        assert result is None
        assert len(attempts) == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_retry.py -v`
Expected: FAIL with `ImportError: cannot import name '_api_call_with_retry'`

**Step 3: Add retry helper to sync_to_google.py**

Add after the `_normalize_dt` function (around line 218):

```python
def _api_call_with_retry(fn, max_retries=3, base_delay=1):
    """Call fn() with retry on transient HTTP errors (429, 500, 503)."""
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            status = getattr(getattr(e, "resp", None), "status", 0)
            if status in (429, 500, 503) and attempt < max_retries - 1:
                time.sleep(base_delay * (2 ** attempt))
                continue
            return None
    return None
```

**Step 4: Update upsert_event to use retry**

Replace the try/except in `upsert_event()` (around line 233-237):

```python
    result = _api_call_with_retry(
        lambda: cal_service.events().insert(
            calendarId=cal_id, body=event_body,
        ).execute()
    )
    return "added" if result else "error"
```

Similarly update `upsert_task()` insert call.

**Step 5: Run all tests**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add src/sync_to_google.py tests/test_retry.py
git commit -m "feat: add retry with backoff for Google API calls"
```

---

### Task 5: Scraper Error Isolation in run_sync.py

**Files:**
- Modify: `src/run_sync.py:51-65`

**Step 1: Wrap scrapers in try-except**

Replace lines 51-65 in `run_sync.py`:

```python
        # 2. Scrape all sources
        data = {"scraped_at": datetime.now().isoformat()}
        scrapers = [
            ("ders_programi", lambda d: scrape_ders_programi(d)),
            ("odevlerim", lambda d: scrape_odevlerim(d)),
            ("takim_calismalari", lambda d: scrape_takim_calismalari(d)),
            ("takvim", lambda d: scrape_takvim(d)),
            ("ders_icerikleri", lambda d: scrape_ders_icerikleri(d)),
            ("ogep", lambda d: scrape_ogep(d)),
            ("gelisim_raporu", lambda d: scrape_gelisim_raporu(d)),
            ("duyurular", lambda d: scrape_duyurular(d)),
        ]
        scrape_errors = []
        for name, fn in scrapers:
            try:
                data[name] = fn(driver)
            except Exception as e:
                scrape_errors.append(f"{name}: {e}")
                data[name] = {} if name != "takvim" and name != "ders_programi" else []
                print(f"[ERROR] {name} failed: {e}")

        # Save scraped data (atomic write)
        from src.json_utils import atomic_json_dump
        out_path = os.path.join(OUTPUT_DIR, "scraped_data.json")
        atomic_json_dump(data, out_path)
```

**Step 2: Run sync dry test**

Run: `python -c "from src.run_sync import main; print('import ok')"`
Expected: `import ok`

**Step 3: Commit**

```bash
git add src/run_sync.py
git commit -m "feat: isolate scraper errors so partial data is saved"
```

---

### Task 6: Health Check Output

**Files:**
- Modify: `src/run_sync.py` (end of main)

**Step 1: Add health check write at end of main()**

After the sync phase in `run_sync.py`, add:

```python
    # 4. Write health check
    from src.json_utils import atomic_json_dump
    health = {
        "timestamp": datetime.now().isoformat(),
        "success": len(scrape_errors) == 0,
        "scrape_errors": scrape_errors,
        "duration_seconds": round(time.time() - start_time),
    }
    atomic_json_dump(health, os.path.join(OUTPUT_DIR, "health.json"))
```

Note: `scrape_errors` needs to be accessible outside the try block. Move its declaration before the try block and pass it through.

**Step 2: Verify health.json would be created**

Run: `python -c "from src.json_utils import atomic_json_dump; atomic_json_dump({'test': True}, 'output/health_test.json'); print('ok')"`
Expected: `ok` and `output/health_test.json` exists

**Step 3: Clean up test file and commit**

```bash
rm -f output/health_test.json
git add src/run_sync.py
git commit -m "feat: write output/health.json after each sync"
```

---

### Task 7: Rename and Extend enrich_gemini.py — Sinav Enrichment

**Files:**
- Rename: `src/enrich_odev_gemini.py` → `src/enrich_gemini.py`
- Test: `tests/test_enrich.py`

**Step 1: Rename file**

```bash
git mv src/enrich_odev_gemini.py src/enrich_gemini.py
```

**Step 2: Write test for sinav prompt builder**

```python
# tests/test_enrich.py
"""Tests for AI enrichment functions."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.enrich_gemini import build_prompt, build_sinav_prompt, SINAV_MARKER


class TestBuildPrompt:
    def test_basic_prompt(self):
        p = build_prompt("Matematik", "Haftalık Ödev", "sayfa 24-25", [], "2026-02-27")
        assert "Matematik" in p
        assert "sayfa 24-25" in p
        assert "2026-02-27" in p

    def test_empty_description(self):
        p = build_prompt("Fen", "Lab Raporu", "", [], "2026-03-01")
        assert "(açıklama yok)" in p


class TestBuildSinavPrompt:
    def test_includes_course_and_date(self):
        p = build_sinav_prompt("Matematik Yazılısı", "2026-03-15", "Matematik", "85")
        assert "Matematik" in p
        assert "2026-03-15" in p
        assert "85" in p

    def test_no_grade_info(self):
        p = build_sinav_prompt("Fen Sınavı", "2026-03-20", "Fen Bilimleri", None)
        assert "not bilgisi yok" in p.lower() or "Fen" in p


class TestSinavMarker:
    def test_marker_exists(self):
        assert "Sınav" in SINAV_MARKER or "sinav" in SINAV_MARKER.lower()
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/test_enrich.py -v`
Expected: FAIL with `ImportError: cannot import name 'build_sinav_prompt'`

**Step 4: Add sinav prompt builder to enrich_gemini.py**

Add after `build_prompt()` function:

```python
SINAV_MARKER = "\n\n🤖 Sınav Rehberi\n"


def build_sinav_prompt(title, date, course, last_grade):
    """Build prompt for exam preparation study guide."""
    grade_info = f"Bu dersteki son sınav notu: {last_grade}" if last_grade else "Bu ders için henüz not bilgisi yok"

    return f"""Sen bir ortaokul öğrencisine yardımcı olan eğitim asistanısın.

Aşağıdaki sınav için kısa bir çalışma rehberi hazırla:
- Sınava nasıl hazırlanılmalı (3-4 madde)
- Dikkat edilmesi gereken konular
- Çalışma önerileri

Sınav: {title}
Ders: {course}
Tarih: {date}
{grade_info}

KRİTİK KURALLAR:
- Türkçe yaz
- Kısa tut (en fazla 120 kelime)
- Sadece rehberi yaz, başka bir şey ekleme
- Markdown kullanma, düz metin yaz
- Genel çalışma tavsiyeleri ver (konu detayı bilinmiyorsa)"""
```

**Step 5: Add `enrich_sinav()` function**

Add after the new prompt builder:

```python
def enrich_sinav(cal_service, cal_id, router, grades_data):
    """Enrich sınav calendar events with AI study guides."""
    # Fetch all events
    events = _fetch_all_events(cal_service, cal_id)

    # Build grades lookup: course -> last grade
    grade_lookup = {}
    for row in grades_data:
        course = row.get("Ders", "")
        for key in ["3. Sınav", "2. Sınav", "1. Sınav"]:
            val = row.get(key, "-")
            if val and val != "-":
                grade_lookup[course] = val
                break

    sinav_keywords = ("sınav", "test", "exam", "yazılı")
    sinav_events = [
        e for e in events
        if any(k in e.get("summary", "").lower() for k in sinav_keywords)
        and not e.get("summary", "").startswith("📝 Ödev:")
    ]

    print(f"\nSınav events found: {len(sinav_events)}")
    enriched = 0
    skipped = 0

    for ev in sinav_events:
        desc = ev.get("description", "") or ""
        if SINAV_MARKER in desc:
            skipped += 1
            continue

        title = ev.get("summary", "")
        date = ev.get("start", {}).get("date", ev.get("start", {}).get("dateTime", ""))

        # Try to match course name from title
        from src.sync_to_google import normalize_course, _ALIAS_LOOKUP
        course = ""
        for alias in _ALIAS_LOOKUP:
            if alias.lower() in title.lower():
                course = _ALIAS_LOOKUP[alias]
                break

        last_grade = grade_lookup.get(course)
        prompt = build_sinav_prompt(title, date, course or "Bilinmiyor", last_grade)

        try:
            note = router.generate(prompt)
            ev["description"] = desc + SINAV_MARKER + note
            cal_service.events().update(
                calendarId=cal_id, eventId=ev["id"], body=ev,
            ).execute()
            enriched += 1
            print(f"  ✓ {title}")
        except Exception as e:
            print(f"  ✗ {title}: {e}")

        time.sleep(router.delay)

    print(f"  Sınav: +{enriched} enriched, ={skipped} skipped")
```

Also extract a shared helper:

```python
def _fetch_all_events(cal_service, cal_id):
    """Fetch all TED portal events from calendar."""
    events = []
    page_token = None
    while True:
        result = cal_service.events().list(
            calendarId=cal_id,
            privateExtendedProperty="source=ted-portal",
            maxResults=2500,
            pageToken=page_token,
            singleEvents=True,
        ).execute()
        events.extend(result.get("items", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return events
```

**Step 6: Run tests**

Run: `pytest tests/test_enrich.py -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add src/enrich_gemini.py tests/test_enrich.py
git commit -m "feat: add sınav exam prep enrichment to enrich_gemini.py"
```

---

### Task 8: Ders İçerikleri Enrichment

**Files:**
- Modify: `src/enrich_gemini.py`
- Modify: `tests/test_enrich.py`

**Step 1: Add test for ders icerikleri prompt**

Append to `tests/test_enrich.py`:

```python
from src.enrich_gemini import build_ders_icerikleri_prompt, DERS_MARKER


class TestBuildDersIcerikleriPrompt:
    def test_includes_course_and_content(self):
        p = build_ders_icerikleri_prompt("Matematik", "Denklemler ve eşitsizlikler konusu işlendi.")
        assert "Matematik" in p
        assert "Denklemler" in p

    def test_truncates_long_content(self):
        long_text = "x" * 2000
        p = build_ders_icerikleri_prompt("Fen", long_text)
        assert len(p) < 3000
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_enrich.py::TestBuildDersIcerikleriPrompt -v`
Expected: FAIL

**Step 3: Implement ders icerikleri enrichment**

Add to `src/enrich_gemini.py`:

```python
DERS_MARKER = "\n\n🤖 Haftalık Özet\n"


def build_ders_icerikleri_prompt(course, raw_content):
    """Build prompt for weekly course content summary."""
    content = raw_content[:1500] if raw_content else "(içerik yok)"
    return f"""Sen bir ortaokul öğrencisine yardımcı olan eğitim asistanısın.

Bu haftanın ders içeriğini kısaca özetle:
- Temel kavramlar (madde işaretleriyle)
- Önemli noktalar
- Varsa önceki konularla bağlantılar

Ders: {course}
İçerik: {content}

KRİTİK KURALLAR:
- Türkçe yaz
- Kısa tut (en fazla 100 kelime)
- Sadece özeti yaz, başka bir şey ekleme
- Markdown kullanma, düz metin yaz
- SADECE verilen içerikten bilgi kullan, bilgi UYDURMA"""


def enrich_ders_icerikleri(tasks_service, task_list_id, router, ders_data):
    """Enrich ders içerikleri tasks with AI summaries."""
    from src.sync_to_google import normalize_course, fetch_existing_tasks

    existing = fetch_existing_tasks(tasks_service, task_list_id)
    enriched = 0
    skipped = 0

    for raw_name, info in ders_data.items():
        course = normalize_course(raw_name)
        text = info.get("text", "").strip()
        cards = info.get("cards", [])
        if not text and not cards:
            continue

        content = text
        if cards:
            content += "\n" + "\n".join(c[:300] for c in cards[:5])

        task_title = f"📖 {course} - Haftalık İçerik"

        # Find existing task
        task_id = None
        for (title, due), tid in existing.items():
            if title == task_title:
                task_id = tid
                break

        if not task_id:
            skipped += 1
            continue

        # Check if already enriched
        try:
            task = tasks_service.tasks().get(
                tasklist=task_list_id, task=task_id,
            ).execute()
        except Exception:
            skipped += 1
            continue

        notes = task.get("notes", "") or ""
        if DERS_MARKER in notes:
            skipped += 1
            continue

        prompt = build_ders_icerikleri_prompt(course, content)
        try:
            summary = router.generate(prompt)
            task["notes"] = notes + DERS_MARKER + summary
            tasks_service.tasks().update(
                tasklist=task_list_id, task=task_id, body=task,
            ).execute()
            enriched += 1
            print(f"  ✓ {task_title}")
        except Exception as e:
            print(f"  ✗ {task_title}: {e}")

        time.sleep(router.delay)

    print(f"  Ders İçerikleri: +{enriched} enriched, ={skipped} skipped")
```

**Step 4: Run tests**

Run: `pytest tests/test_enrich.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/enrich_gemini.py tests/test_enrich.py
git commit -m "feat: add ders içerikleri weekly summary enrichment"
```

---

### Task 9: Performans Analizi Enrichment

**Files:**
- Modify: `src/enrich_gemini.py`
- Modify: `tests/test_enrich.py`

**Step 1: Add test**

Append to `tests/test_enrich.py`:

```python
from src.enrich_gemini import build_performans_prompt, PERFORMANS_MARKER


class TestBuildPerformansPrompt:
    def test_includes_grades(self):
        grades = [
            {"Ders": "Matematik", "1. Sınav": "85", "2. Sınav": "92"},
            {"Ders": "Fen", "1. Sınav": "70", "2. Sınav": "65"},
        ]
        p = build_performans_prompt(grades)
        assert "Matematik" in p
        assert "85" in p
        assert "Fen" in p
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_enrich.py::TestBuildPerformansPrompt -v`
Expected: FAIL

**Step 3: Implement performans enrichment**

Add to `src/enrich_gemini.py`:

```python
PERFORMANS_MARKER = "\n\n🤖 Performans Analizi\n"


def build_performans_prompt(grades):
    """Build prompt for grade performance analysis."""
    lines = []
    for g in grades:
        ders = g.get("Ders", "?")
        scores = []
        for k in ["1. Sınav", "2. Sınav", "3. Sınav",
                   "DİKP/Performans-1", "DİKP/Performans-2"]:
            v = g.get(k, "-")
            if v and v != "-":
                scores.append(f"{k}: {v}")
        lines.append(f"  {ders}: {', '.join(scores) or 'not yok'}")

    grades_text = "\n".join(lines)
    return f"""Sen bir ortaokul öğrencisine yardımcı olan eğitim asistanısın.

Bu öğrencinin sınav notlarını analiz et ve kısa bir performans özeti yaz:
- En iyi 3 ders (ve neden)
- İyileştirme gereken 2 ders (ve tavsiye)
- Genel eğilim (yükseliyor/düşüyor/stabil)

Notlar:
{grades_text}

KRİTİK KURALLAR:
- Türkçe yaz
- Kısa tut (en fazla 150 kelime)
- Sadece analizi yaz, başka bir şey ekleme
- Markdown kullanma, düz metin yaz
- Motive edici ve yapıcı bir ton kullan"""


def enrich_performans(tasks_service, task_list_id, router, grades):
    """Create or update a performance analysis task."""
    from src.sync_to_google import fetch_existing_tasks

    if not grades:
        print("  No grades data, skipping performans")
        return

    existing = fetch_existing_tasks(tasks_service, task_list_id)
    task_title = "📊 Performans Analizi"

    # Find or create the task
    task_id = None
    for (title, due), tid in existing.items():
        if title == task_title:
            task_id = tid
            break

    prompt = build_performans_prompt(grades)
    try:
        note = router.generate(prompt)
    except Exception as e:
        print(f"  ✗ Performans: {e}")
        return

    if task_id:
        try:
            task = tasks_service.tasks().get(
                tasklist=task_list_id, task=task_id,
            ).execute()
            task["notes"] = note  # Always overwrite with latest
            tasks_service.tasks().update(
                tasklist=task_list_id, task=task_id, body=task,
            ).execute()
            print(f"  ✓ {task_title} (updated)")
        except Exception as e:
            print(f"  ✗ {task_title}: {e}")
    else:
        try:
            tasks_service.tasks().insert(
                tasklist=task_list_id,
                body={"title": task_title, "notes": note},
            ).execute()
            print(f"  ✓ {task_title} (created)")
        except Exception as e:
            print(f"  ✗ {task_title}: {e}")
```

**Step 4: Run tests**

Run: `pytest tests/test_enrich.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/enrich_gemini.py tests/test_enrich.py
git commit -m "feat: add performans grade analysis enrichment"
```

---

### Task 10: Add enrich_all() Entry Point

**Files:**
- Modify: `src/enrich_gemini.py`

**Step 1: Add enrich_all function**

Add at end of file (before `if __name__`):

```python
def enrich_all(token_file=None, force=False):
    """Run all enrichment functions for a given account."""
    from src.env_loader import load_env
    load_env()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found, skipping enrichment")
        return

    gemini = genai.Client(api_key=api_key)
    router = ModelRouter(gemini)
    print(f"\n[Enrich] Model: {router.current}")

    cal, tasks_svc, _, _ = get_services(token_file=token_file)
    cal_id = get_or_create_calendar(cal, "TED Rönesans")

    from src.sync_to_google import get_or_create_task_list
    task_list_id = get_or_create_task_list(tasks_svc, "TED Ödevler")

    # Load scraped data
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    # 1. Ödev enrichment (existing)
    print("\n[Enrich] Ödev notları...")
    # Call existing main logic (refactored into function)
    _enrich_odev(cal, cal_id, router, force)

    # 2. Sınav enrichment
    print("\n[Enrich] Sınav rehberleri...")
    grades = data.get("gelisim_raporu", {}).get("grades", [])
    enrich_sinav(cal, cal_id, router, grades)

    # 3. Ders içerikleri enrichment
    print("\n[Enrich] Ders özerleri...")
    ders_data = data.get("ders_icerikleri", {})
    enrich_ders_icerikleri(tasks_svc, task_list_id, router, ders_data)

    # 4. Performans enrichment
    print("\n[Enrich] Performans analizi...")
    enrich_performans(tasks_svc, task_list_id, router, grades)
```

Also refactor existing `main()` ödev logic into `_enrich_odev(cal, cal_id, router, force)` function (extract lines 270-369).

**Step 2: Update `__main__` block**

```python
if __name__ == "__main__":
    force = "--force" in sys.argv
    enrich_all(force=force)
```

**Step 3: Verify import works**

Run: `python -c "from src.enrich_gemini import enrich_all; print('ok')"`
Expected: `ok`

**Step 4: Commit**

```bash
git add src/enrich_gemini.py
git commit -m "feat: add enrich_all() entry point combining all enrichments"
```

---

### Task 11: Integrate Enrichment into run_sync.py

**Files:**
- Modify: `src/run_sync.py:70-95`

**Step 1: Add enrichment phase after sync**

After the Google sync block in `run_sync.py`, add:

```python
    # 4. AI Enrichment (post-sync)
    print("\n--- AI Enrichment ---")
    try:
        from src.enrich_gemini import enrich_all
        from src.sync_to_google import TOKEN_FILE, TOKEN_HURIYE
        enrich_all(token_file=TOKEN_FILE)
        if os.path.exists(TOKEN_HURIYE):
            enrich_all(token_file=TOKEN_HURIYE)
    except Exception as e:
        print(f"[WARN] Enrichment failed: {e}")
        # Non-fatal: sync succeeded even if enrichment fails
```

**Step 2: Verify run_sync still imports cleanly**

Run: `python -c "from src.run_sync import main; print('ok')"`
Expected: `ok`

**Step 3: Commit**

```bash
git add src/run_sync.py
git commit -m "feat: integrate AI enrichment into sync pipeline"
```

---

### Task 12: Update CLAUDE.md and Final Verification

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update CLAUDE.md**

Update the Commands section:
- Replace `python src/enrich_odev_gemini.py` → `python src/enrich_gemini.py`
- Update module table: `enrich_odev_gemini.py` → `enrich_gemini.py`
- Add `src/env_loader.py` and `src/json_utils.py` to module table

Update Key Patterns:
- Add: "**Error isolation**: Each scraper in `run_sync.py` is wrapped in try-except. Partial data is saved and synced even if one scraper fails."
- Add: "**API retry**: `upsert_event()/upsert_task()` retry transient Google API errors (429/500/503) up to 3x with exponential backoff."
- Add: "**Health check**: `output/health.json` is written after each sync with success status, errors, and duration."

**Step 2: Run full test suite**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for reliability hardening and enrichment expansion"
```
