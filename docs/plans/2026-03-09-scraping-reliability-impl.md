# Scraping Reliability Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Raise scraping reliability from ~70-75% to ~90-95% through five defense layers: session persistence, explicit waits, data validation, rich health metrics, and dashboard health banner.

**Architecture:** Five independent layers, each testable and deployable alone. Session persistence reduces CAPTCHA dependency. Explicit waits replace brittle `time.sleep()`. Data validation prevents saving empty/degraded data. Rich health metrics expose per-section quality. Dashboard banner makes it visible to the user.

**Tech Stack:** Python (Selenium, requests, ddddocr), React + TypeScript + Carbon Design System

**Design doc:** `docs/plans/2026-03-09-scraping-reliability-design.md`

---

### Task 1: Session Manager — Cookie Persistence

**Files:**
- Create: `src/session_manager.py`
- Create: `tests/test_session_manager.py`

**Step 1: Write the tests**

```python
# tests/test_session_manager.py
import json
import os
import pytest
from unittest.mock import MagicMock, patch

from src.session_manager import save_cookies, load_cookies, test_session_valid

COOKIE_PATH = "output/portal_cookies.json"


def test_save_cookies_writes_json(tmp_path):
    path = str(tmp_path / "cookies.json")
    cookies = [{"name": "sid", "value": "abc123", "domain": ".example.com"}]
    save_cookies(cookies, path)
    with open(path) as f:
        saved = json.load(f)
    assert saved == cookies


def test_load_cookies_returns_list(tmp_path):
    path = str(tmp_path / "cookies.json")
    data = [{"name": "sid", "value": "abc123"}]
    with open(path, "w") as f:
        json.dump(data, f)
    result = load_cookies(path)
    assert result == data


def test_load_cookies_returns_none_if_missing(tmp_path):
    path = str(tmp_path / "cookies.json")
    result = load_cookies(path)
    assert result is None


def test_load_cookies_returns_none_if_corrupted(tmp_path):
    path = str(tmp_path / "cookies.json")
    with open(path, "w") as f:
        f.write("not json {{{")
    result = load_cookies(path)
    assert result is None


def test_session_valid_returns_true_on_200():
    cookies = [{"name": "sid", "value": "abc"}]
    with patch("src.session_manager.requests") as mock_req:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://portal.tedronesans.k12.tr/dashboard"
        mock_req.Session.return_value.get.return_value = mock_resp
        assert test_session_valid(cookies) is True


def test_session_valid_returns_false_on_redirect_to_login():
    cookies = [{"name": "sid", "value": "abc"}]
    with patch("src.session_manager.requests") as mock_req:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://portal.tedronesans.k12.tr/login"
        mock_req.Session.return_value.get.return_value = mock_resp
        assert test_session_valid(cookies) is False
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_session_manager.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.session_manager'`

**Step 3: Write the implementation**

```python
# src/session_manager.py
"""Cookie-based session persistence for TED portal login."""
import json
import os

import requests

PORTAL_BASE = "https://portal.tedronesans.k12.tr"
PROFILE_URL = f"{PORTAL_BASE}/pages/ogrenci_istekler/p_ogrenci_bilgilerim"
DEFAULT_COOKIE_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "portal_cookies.json")


def save_cookies(cookies: list[dict], path: str = DEFAULT_COOKIE_PATH) -> None:
    """Save browser cookies to disk as JSON."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False)


def load_cookies(path: str = DEFAULT_COOKIE_PATH) -> list[dict] | None:
    """Load cookies from disk. Returns None if file missing or corrupted."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def test_session_valid(cookies: list[dict]) -> bool:
    """Test if cached cookies still represent a valid session."""
    session = requests.Session()
    for c in cookies:
        session.cookies.set(c["name"], c["value"], domain=c.get("domain", ""))
    try:
        resp = session.get(PROFILE_URL, timeout=10, allow_redirects=True)
        return resp.status_code == 200 and "/login" not in resp.url
    except requests.RequestException:
        return False


def apply_cookies_to_driver(driver, cookies: list[dict]) -> None:
    """Load cookies into Selenium driver. Must navigate to domain first."""
    driver.get(PORTAL_BASE)
    for c in cookies:
        cookie = {"name": c["name"], "value": c["value"]}
        if "domain" in c:
            cookie["domain"] = c["domain"]
        try:
            driver.add_cookie(cookie)
        except Exception:
            pass  # Skip cookies that Selenium rejects
    driver.refresh()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_session_manager.py -v`
Expected: All 6 PASS

**Step 5: Commit**

```bash
git add src/session_manager.py tests/test_session_manager.py
git commit -m "feat: add session manager for cookie persistence"
```

---

### Task 2: Integrate Session Manager into Login Flow

**Files:**
- Modify: `src/scrape_all.py:36-56` (login function)
- Modify: `src/run_sync.py:46` (login call)

**Step 1: Modify `scrape_all.py` login function**

Replace `src/scrape_all.py:36-56`:

```python
def login(driver):
    from src.session_manager import load_cookies, save_cookies, test_session_valid, apply_cookies_to_driver

    # Try cached session first
    cached = load_cookies()
    if cached and test_session_valid(cached):
        print("[LOGIN] Using cached session")
        apply_cookies_to_driver(driver, cached)
        # Verify driver is logged in
        driver.get(f"{BASE_URL}/pages/ogrenci_istekler/p_ogrenci_bilgilerim")
        time.sleep(2)
        if "/login" not in driver.current_url:
            print(f"[LOGIN] Cached session OK -> {driver.current_url}")
            return {"method": "cached_session", "captcha_attempts": 0}
        print("[LOGIN] Cached session expired in browser, falling back to CAPTCHA")

    # CAPTCHA login
    ocr = ddddocr.DdddOcr(show_ad=False)
    for attempt in range(5):
        driver.get(LOGIN_URL)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "tx_kullanici_adi"))
        )
        driver.find_element(By.ID, "tx_kullanici_adi").send_keys(os.environ.get("PORTAL_USERNAME", ""))
        driver.find_element(By.ID, "tx_kullanici_sifre").send_keys(os.environ.get("PORTAL_PASSWORD", ""))

        # CAPTCHA with preprocessing
        captcha_img = driver.find_element(By.CSS_SELECTOR, 'img[src*="CaptchaHandler"]')
        captcha_text = ocr.classification(captcha_img.screenshot_as_png).strip()
        # Validate: only accept 4-6 digit numbers
        if not captcha_text or not captcha_text.isdigit() or len(captcha_text) < 4:
            print(f"[LOGIN] OCR '{captcha_text}' invalid, refreshing CAPTCHA...")
            continue

        driver.find_element(By.ID, "txtKod").send_keys(captcha_text)
        driver.find_element(By.ID, "btn_ogrenci").click()
        time.sleep(3)
        if "/login" not in driver.current_url:
            print(f"[LOGIN] OK -> {driver.current_url}")
            # Save cookies for next run
            save_cookies(driver.get_cookies())
            return {"method": "captcha_login", "captcha_attempts": attempt + 1}

    print("[LOGIN] FAILED after 5 attempts")
    return None
```

**Step 2: Update `run_sync.py` to capture login info**

Modify `src/run_sync.py:44-58`:

```python
    try:
        # 1. Login
        login_info = login(driver)
        if not login_info:
            print("[ERROR] Login failed, aborting")
            scrape_errors.append("login: Login failed")
            health = {
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "scrape_errors": scrape_errors,
                "duration_seconds": round(time.time() - start_time),
                "login": {"method": "failed", "captcha_attempts": 5},
            }
            from src.json_utils import atomic_json_dump
            atomic_json_dump(health, os.path.join(OUTPUT_DIR, "health.json"))
            print(f"\nHealth: ERRORS ({health['duration_seconds']}s)")
            return
```

And save `login_info` for health output at the end (line 149-155):

```python
    health = {
        "timestamp": datetime.now().isoformat(),
        "success": len(scrape_errors) == 0,
        "scrape_errors": scrape_errors,
        "duration_seconds": round(time.time() - start_time),
        "login": login_info or {"method": "failed", "captcha_attempts": 0},
    }
```

**Step 3: Run existing tests**

Run: `pytest tests/ -v`
Expected: All pass (login function signature unchanged — returns truthy on success, None on failure)

**Step 4: Commit**

```bash
git add src/scrape_all.py src/run_sync.py
git commit -m "feat: integrate session persistence into login flow"
```

---

### Task 3: Scrape Helpers — Explicit Waits + Retry

**Files:**
- Create: `src/scrape_helpers.py`
- Create: `tests/test_scrape_helpers.py`

**Step 1: Write the tests**

```python
# tests/test_scrape_helpers.py
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException

from src.scrape_helpers import wait_for, wait_for_js, retry_on_stale


def test_wait_for_returns_element():
    mock_driver = MagicMock()
    mock_element = MagicMock()
    with patch("src.scrape_helpers.WebDriverWait") as mock_wait:
        mock_wait.return_value.until.return_value = mock_element
        result = wait_for(mock_driver, ("id", "myElement"), timeout=5)
    assert result == mock_element


def test_wait_for_raises_on_timeout():
    from selenium.common.exceptions import TimeoutException
    mock_driver = MagicMock()
    with patch("src.scrape_helpers.WebDriverWait") as mock_wait:
        mock_wait.return_value.until.side_effect = TimeoutException()
        with pytest.raises(TimeoutException):
            wait_for(mock_driver, ("id", "myElement"), timeout=1)


def test_wait_for_js_returns_truthy_result():
    mock_driver = MagicMock()
    mock_driver.execute_script.return_value = [{"title": "Event"}]
    with patch("src.scrape_helpers.WebDriverWait") as mock_wait:
        mock_wait.return_value.until.side_effect = lambda fn: fn(mock_driver)
        result = wait_for_js(mock_driver, "return window.calendar.getEvents()", timeout=5)
    assert result == [{"title": "Event"}]


def test_retry_on_stale_retries_and_succeeds():
    call_count = 0

    @retry_on_stale(max_retries=3)
    def flaky_fn():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise StaleElementReferenceException()
        return "success"

    assert flaky_fn() == "success"
    assert call_count == 3


def test_retry_on_stale_raises_after_max():
    @retry_on_stale(max_retries=2)
    def always_fails():
        raise StaleElementReferenceException()

    with pytest.raises(StaleElementReferenceException):
        always_fails()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scrape_helpers.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write the implementation**

```python
# src/scrape_helpers.py
"""Shared Selenium wait and retry utilities for scrapers."""
import functools
import time

from selenium.common.exceptions import (
    StaleElementReferenceException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def wait_for(driver, locator: tuple, timeout: int = 15):
    """Wait for an element to be present. Returns the element or raises TimeoutException."""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(locator)
    )


def wait_for_js(driver, js_expression: str, timeout: int = 15):
    """Wait for a JS expression to return a truthy value. Returns the value."""
    def check(d):
        result = d.execute_script(js_expression)
        return result if result else False
    return WebDriverWait(driver, timeout).until(check)


def retry_on_stale(max_retries: int = 3, delay: float = 1.0):
    """Decorator: retry a function on StaleElementReferenceException or NoSuchElementException."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries):
                try:
                    return fn(*args, **kwargs)
                except (StaleElementReferenceException, NoSuchElementException) as e:
                    last_exc = e
                    if attempt < max_retries - 1:
                        time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scrape_helpers.py -v`
Expected: All 5 PASS

**Step 5: Commit**

```bash
git add src/scrape_helpers.py tests/test_scrape_helpers.py
git commit -m "feat: add scrape helpers — explicit waits and retry decorator"
```

---

### Task 4: Migrate scrape_takvim to Explicit Waits

**Files:**
- Modify: `src/scrape_all.py:325-395` (scrape_takvim function)

**Step 1: Replace sleep-based waits in scrape_takvim**

Key changes in `scrape_takvim()`:

1. Line 334: `time.sleep(3)` → `wait_for(driver, (By.ID, "select-all"), timeout=15)`
2. Line 342: `time.sleep(1)` → `time.sleep(0.5)` (short UI settle, acceptable)
3. Line 354: `time.sleep(2)` → `time.sleep(1)` (filter settle)
4. Lines 380-392: Before `JS_GET_EVENTS`, add:
```python
wait_for_js(driver, "return typeof window.calendar !== 'undefined' && window.calendar.getEvents().length >= 0", timeout=15)
```

Add import at top of `scrape_all.py`:
```python
from src.scrape_helpers import wait_for, wait_for_js, retry_on_stale
```

**Step 2: Run full test suite**

Run: `pytest tests/ -v`
Expected: All pass

**Step 3: Commit**

```bash
git add src/scrape_all.py
git commit -m "fix: replace time.sleep with explicit waits in scrape_takvim"
```

---

### Task 5: Migrate scrape_odevlerim to Explicit Waits

**Files:**
- Modify: `src/scrape_all.py` (scrape_odevlerim function)

**Step 1: Replace sleep-based waits**

Key changes:
1. After navigating to homework page: `time.sleep(3)` → `wait_for(driver, (By.CSS_SELECTOR, "#tblOdevlerim"), timeout=15)`
2. After "Tamamı" select: `time.sleep(2)` → `wait_for(driver, (By.CSS_SELECTOR, "#tblOdevlerim tbody tr"), timeout=10)`
3. Detail page loads: `time.sleep(2)` → `wait_for(driver, (By.CSS_SELECTOR, ".odev-detay, #odev-detay-modal"), timeout=10)`

**Step 2: Run tests**

Run: `pytest tests/ -v`
Expected: All pass

**Step 3: Commit**

```bash
git add src/scrape_all.py
git commit -m "fix: replace time.sleep with explicit waits in scrape_odevlerim"
```

---

### Task 6: Data Validator

**Files:**
- Create: `src/data_validator.py`
- Create: `tests/test_data_validator.py`

**Step 1: Write the tests**

```python
# tests/test_data_validator.py
import pytest
from src.data_validator import validate_scraped_data


def test_valid_data_passes():
    data = {
        "odevlerim": {"homework": {"rows": [{"Ders Adı": "Mat", "Ödev Başlığı": "HW"} for _ in range(10)]}},
        "ders_programi": [{"schedule": {"rows": [["", "Mon"]]}}],
        "takvim": [{"title": "E1"}, {"title": "E2"}],
        "gelisim_raporu": {"grades": [{"Ders": f"D{i}"} for i in range(11)]},
        "ders_icerikleri": {"T": [1]},
        "takim_calismalari": {"activities": [1]},
        "ogep": {"sessions": {"rows": [1]}},
        "duyurular": {"announcements": [1, 2]},
    }
    result = validate_scraped_data(data, previous_data=None)
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_empty_odevlerim_fails():
    data = {
        "odevlerim": {"homework": {"rows": []}},
    }
    result = validate_scraped_data(data, previous_data=None)
    assert result["valid"] is False
    assert any("odevlerim" in e for e in result["errors"])


def test_large_drop_warns():
    prev = {
        "takvim": [{"title": f"E{i}"} for i in range(20)],
    }
    new = {
        "takvim": [{"title": "E1"}],
    }
    result = validate_scraped_data(new, previous_data=prev)
    assert any("takvim" in w for w in result["warnings"])


def test_missing_section_counted():
    data = {}
    result = validate_scraped_data(data, previous_data=None)
    # Missing critical sections should be errors
    assert result["valid"] is False


def test_section_counts_returned():
    data = {
        "odevlerim": {"homework": {"rows": [{"Ders Adı": "M", "Ödev Başlığı": "H"} for _ in range(10)]}},
        "takvim": [{"title": "E1"}, {"title": "E2"}, {"title": "E3"}],
    }
    result = validate_scraped_data(data, previous_data=None)
    assert result["section_counts"]["odevlerim"] == 10
    assert result["section_counts"]["takvim"] == 3
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_data_validator.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write the implementation**

```python
# src/data_validator.py
"""Validate scraped data quality before saving."""

# How to count items in each section
def _count_section(key, data):
    """Return the item count for a section, or 0 if missing/empty."""
    val = data.get(key)
    if val is None:
        return 0
    if key == "odevlerim":
        return len(val.get("homework", {}).get("rows", []))
    if key == "ders_programi":
        return len(val) if isinstance(val, list) else (1 if val else 0)
    if key == "takvim":
        return len(val) if isinstance(val, list) else 0
    if key == "gelisim_raporu":
        return len(val.get("grades", []))
    if key == "ders_icerikleri":
        if isinstance(val, dict):
            return sum(len(v) if isinstance(v, list) else 1 for v in val.values())
        return 0
    if key == "takim_calismalari":
        return len(val.get("activities", []))
    if key == "ogep":
        return len(val.get("sessions", {}).get("rows", []))
    if key == "duyurular":
        return len(val.get("announcements", []))
    return 0


# Minimum thresholds (0 = no minimum, section can be empty)
SECTION_RULES = {
    "odevlerim":         {"min": 5,  "critical": True},
    "ders_programi":     {"min": 1,  "critical": True},
    "takvim":            {"min": 1,  "critical": False},
    "gelisim_raporu":    {"min": 5,  "critical": True},
    "ders_icerikleri":   {"min": 1,  "critical": False},
    "takim_calismalari": {"min": 0,  "critical": False},
    "ogep":              {"min": 0,  "critical": False},
    "duyurular":         {"min": 1,  "critical": False},
}

DROP_THRESHOLD = 0.5  # Warn if count drops by more than 50%


def validate_scraped_data(new_data: dict, previous_data: dict | None) -> dict:
    """
    Validate scraped data. Returns:
    {
        "valid": bool,
        "errors": [str],
        "warnings": [str],
        "section_counts": {section: count},
    }
    """
    errors = []
    warnings = []
    section_counts = {}

    for section, rules in SECTION_RULES.items():
        count = _count_section(section, new_data)
        section_counts[section] = count

        # Check minimum threshold
        if count < rules["min"] and rules["critical"]:
            errors.append(f"{section}: {count} items (minimum {rules['min']})")
        elif count < rules["min"]:
            warnings.append(f"{section}: {count} items (expected >= {rules['min']})")

        # Compare with previous data
        if previous_data:
            prev_count = _count_section(section, previous_data)
            if prev_count > 0 and count < prev_count * DROP_THRESHOLD:
                pct = round((1 - count / prev_count) * 100)
                warnings.append(f"{section}: {prev_count}→{count}, %{pct} düşüş")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "section_counts": section_counts,
    }
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_data_validator.py -v`
Expected: All 5 PASS

**Step 5: Commit**

```bash
git add src/data_validator.py tests/test_data_validator.py
git commit -m "feat: add data validator with threshold and drop detection"
```

---

### Task 7: Integrate Validator into run_sync.py

**Files:**
- Modify: `src/run_sync.py:80-83` (after scraping, before save)

**Step 1: Add validation between scrape and save**

After `src/run_sync.py:78` (end of scraper loop), before the save at line 82:

```python
        # Validate scraped data
        from src.data_validator import validate_scraped_data
        prev_data = {}
        prev_path = os.path.join(OUTPUT_DIR, "scraped_data.json")
        if os.path.exists(prev_path):
            try:
                import json
                with open(prev_path) as f:
                    prev_data = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        validation = validate_scraped_data(data, prev_data)
        if validation["errors"]:
            scrape_errors.extend(validation["errors"])
        if validation["warnings"]:
            for w in validation["warnings"]:
                print(f"[WARN] Validation: {w}")
```

The `validation` dict will also be used in the health output (Task 8).

**Step 2: Run existing tests**

Run: `pytest tests/ -v`
Expected: All pass

**Step 3: Commit**

```bash
git add src/run_sync.py
git commit -m "feat: integrate data validation into sync pipeline"
```

---

### Task 8: Rich Health Metrics

**Files:**
- Modify: `src/run_sync.py:147-155` (health output section)

**Step 1: Expand health.json output**

Replace `src/run_sync.py:147-155`:

```python
    # 6. Write health check
    from src.json_utils import atomic_json_dump

    # Build per-section status from validation
    sections_health = {}
    for section, count in validation.get("section_counts", {}).items():
        prev_count = 0
        if prev_data:
            from src.data_validator import _count_section
            prev_count = _count_section(section, prev_data)

        status = "ok"
        if any(section in e for e in validation.get("errors", [])):
            status = "error"
        elif any(section in w for w in validation.get("warnings", [])):
            status = "warning"
        elif section in [e.split(":")[0] for e in scrape_errors if ":" in e]:
            status = "skipped"

        sections_health[section] = {
            "count": count,
            "prev_count": prev_count,
            "status": status,
        }

    health = {
        "timestamp": datetime.now().isoformat(),
        "success": len(scrape_errors) == 0,
        "duration_seconds": round(time.time() - start_time),
        "scrape_errors": scrape_errors,
        "validation_warnings": validation.get("warnings", []),
        "login": login_info or {"method": "failed", "captcha_attempts": 0},
        "sections": sections_health,
        "staleness": {
            "last_successful_full_scrape": datetime.now().isoformat() if not scrape_errors else (
                prev_data.get("scraped_at", "") if prev_data else ""
            ),
            "stale_sections": [s for s, info in sections_health.items() if info["status"] in ("error", "skipped")],
        },
    }
    atomic_json_dump(health, os.path.join(OUTPUT_DIR, "health.json"))

    elapsed = time.time() - start_time
    print(f"\nHealth: {'OK' if health['success'] else 'ERRORS'} ({health['duration_seconds']}s)")
    print(f"[DONE] Completed in {elapsed:.0f}s")
```

Note: `validation` and `login_info` variables must be accessible at this scope. Move their declarations to top of `main()` function:

```python
    login_info = None
    validation = {"section_counts": {}, "errors": [], "warnings": []}
```

**Step 2: Run tests**

Run: `pytest tests/ -v`
Expected: All pass

**Step 3: Commit**

```bash
git add src/run_sync.py
git commit -m "feat: rich health metrics with per-section status"
```

---

### Task 9: Dashboard Health Banner — TypeScript Types

**Files:**
- Modify: `dashboard/src/types.ts:71-76` (HealthData interface)

**Step 1: Expand HealthData interface**

Replace `dashboard/src/types.ts:71-76`:

```typescript
export interface SectionHealth {
  count: number
  prev_count: number
  status: 'ok' | 'warning' | 'error' | 'skipped'
}

export interface HealthData {
  timestamp: string
  success: boolean
  scrape_errors: string[]
  duration_seconds: number
  validation_warnings?: string[]
  login?: {
    method: 'cached_session' | 'captcha_login' | 'failed'
    captcha_attempts: number
  }
  sections?: Record<string, SectionHealth>
  staleness?: {
    last_successful_full_scrape: string
    stale_sections: string[]
  }
}
```

**Step 2: Commit**

```bash
git add dashboard/src/types.ts
git commit -m "feat: expand HealthData types for rich health metrics"
```

---

### Task 10: Dashboard Health Banner — Popover UI

**Files:**
- Modify: `dashboard/src/components/DashboardHeader.tsx`

**Step 1: Add Popover with section details**

Add imports:
```typescript
import { Popover, PopoverContent } from '@carbon/react'
import { CheckmarkFilled, WarningFilled, ErrorFilled, SkipForwardFilled } from '@carbon/icons-react'
```

Add state:
```typescript
const [healthOpen, setHealthOpen] = useState(false)
```

Compute tag type:
```typescript
const warningCount = (health.validation_warnings?.length || 0) + (health.scrape_errors?.length || 0)
const tagType = !health.timestamp ? 'gray' : health.success ? (warningCount > 0 ? 'warm-gray' : 'green') : 'red'
const tagText = warningCount > 0 ? `${syncAgo} · ${warningCount} uyarı` : syncAgo
```

Replace the existing Tag in the header with a clickable Popover version:
```tsx
<Popover open={healthOpen} align="bottom-right" onRequestClose={() => setHealthOpen(false)}>
  <button type="button" onClick={() => setHealthOpen(!healthOpen)}
    style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
    <Tag type={tagType} size="sm">{loading ? '...' : tagText}</Tag>
  </button>
  <PopoverContent>
    <div style={{ padding: '1rem', fontSize: '0.8125rem', minWidth: 280 }}>
      <p style={{ fontWeight: 600, marginBottom: '0.5rem' }}>
        Son Sync: {health.timestamp ? new Date(health.timestamp).toLocaleString('tr-TR') : '—'}
      </p>
      {health.login && (
        <p style={{ color: '#525252', marginBottom: '0.5rem' }}>
          Login: {health.login.method === 'cached_session' ? 'Kayıtlı oturum' :
                  health.login.method === 'captcha_login' ? `CAPTCHA (${health.login.captcha_attempts} deneme)` : 'Başarısız'}
        </p>
      )}
      <p style={{ color: '#525252', marginBottom: '0.75rem' }}>
        Süre: {health.duration_seconds}s
      </p>
      {health.sections && Object.entries(health.sections).map(([key, sec]) => (
        <div key={key} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0' }}>
          <span>{SECTION_LABELS[key] || key}</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            {sec.count} öğe
            {sec.status === 'ok' && <CheckmarkFilled size={14} style={{ color: 'var(--status-success)' }} />}
            {sec.status === 'warning' && <WarningFilled size={14} style={{ color: 'var(--status-warning)' }} />}
            {sec.status === 'error' && <ErrorFilled size={14} style={{ color: 'var(--status-error)' }} />}
            {sec.status === 'skipped' && <SkipForwardFilled size={14} style={{ color: '#A8A8A8' }} />}
          </span>
        </div>
      ))}
    </div>
  </PopoverContent>
</Popover>
```

Add section label map:
```typescript
const SECTION_LABELS: Record<string, string> = {
  odevlerim: 'Ödevler',
  ders_programi: 'Ders Programı',
  takvim: 'Takvim',
  gelisim_raporu: 'Notlar',
  ders_icerikleri: 'Ders İçerikleri',
  takim_calismalari: 'Takımlar',
  ogep: 'ÖGEP',
  duyurular: 'Duyurular',
}
```

**Step 2: Build to verify TypeScript compiles**

Run: `cd dashboard && npm run build`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add dashboard/src/components/DashboardHeader.tsx
git commit -m "feat: add health popover with per-section status"
```

---

### Task 11: Build, Deploy, Verify

**Step 1: Build dashboard**

Run: `cd dashboard && npm run build`
Expected: Build succeeds

**Step 2: Run all Python tests**

Run: `pytest tests/ -v`
Expected: All pass

**Step 3: Deploy**

Run: `systemctl --user restart ted-dashboard`

**Step 4: Verify**

- Navigate to tedy.online — header health tag clickable, popover shows section details
- Run: `python src/run_sync.py` — verify health.json has new fields
- Check `output/health.json` — has `sections`, `login`, `staleness` fields

**Step 5: Final commit**

```bash
git add -A && git commit -m "chore: build dashboard for scraping reliability release"
```

---

## Files Summary

| File | Action | Task |
|------|--------|------|
| `src/session_manager.py` | Create | 1 |
| `tests/test_session_manager.py` | Create | 1 |
| `src/scrape_all.py` | Modify | 2, 4, 5 |
| `src/run_sync.py` | Modify | 2, 7, 8 |
| `src/scrape_helpers.py` | Create | 3 |
| `tests/test_scrape_helpers.py` | Create | 3 |
| `src/data_validator.py` | Create | 6 |
| `tests/test_data_validator.py` | Create | 6 |
| `dashboard/src/types.ts` | Modify | 9 |
| `dashboard/src/components/DashboardHeader.tsx` | Modify | 10 |
