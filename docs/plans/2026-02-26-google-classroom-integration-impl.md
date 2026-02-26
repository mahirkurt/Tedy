# Google Classroom Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Write TED portal data (homework, materials, grades, announcements) to Google Classroom as a standalone sync module.

**Architecture:** Separate `src/sync_to_classroom.py` module that reads `output/scraped_data.json`, manages per-course Classroom resources, and tracks sync state in `output/classroom_*.json` files. Imports `normalize_course` and `_api_call_with_retry` from existing `sync_to_google.py`. Integrates into `run_sync.py` as Phase 4.

**Tech Stack:** `google-api-python-client` (Classroom API v1), existing OAuth infrastructure, pytest for tests.

---

### Task 1: Add Classroom OAuth Scopes

**Files:**
- Modify: `src/google_auth.py:18-23` (SCOPES array)

**Step 1: Write the failing test**

Create `tests/test_classroom_auth.py`:

```python
"""Tests for Classroom OAuth scopes."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.google_auth import SCOPES


class TestClassroomScopes:
    def test_classroom_courses_scope(self):
        assert "https://www.googleapis.com/auth/classroom.courses" in SCOPES

    def test_classroom_coursework_scope(self):
        assert "https://www.googleapis.com/auth/classroom.coursework.students" in SCOPES

    def test_classroom_announcements_scope(self):
        assert "https://www.googleapis.com/auth/classroom.announcements" in SCOPES

    def test_classroom_rosters_scope(self):
        assert "https://www.googleapis.com/auth/classroom.rosters" in SCOPES

    def test_classroom_profile_scope(self):
        assert "https://www.googleapis.com/auth/classroom.profile.emails" in SCOPES
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_classroom_auth.py -v`
Expected: 5 FAILED — scopes not yet added.

**Step 3: Add scopes to google_auth.py**

In `src/google_auth.py`, change the SCOPES list (line 18-23) to:

```python
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/classroom.courses",
    "https://www.googleapis.com/auth/classroom.coursework.students",
    "https://www.googleapis.com/auth/classroom.announcements",
    "https://www.googleapis.com/auth/classroom.rosters",
    "https://www.googleapis.com/auth/classroom.profile.emails",
]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_classroom_auth.py -v`
Expected: 5 PASSED

**Step 5: Run all existing tests**

Run: `pytest -v`
Expected: All pass (no regressions).

**Step 6: Commit**

```bash
git add src/google_auth.py tests/test_classroom_auth.py
git commit -m "feat: add Google Classroom OAuth scopes"
```

**Note:** After this change, users must re-authenticate (`python src/google_auth.py`) to grant the new Classroom scopes. The existing `token.json` will need to be deleted and regenerated.

---

### Task 2: Core Module Skeleton — `compute_hash`, State Load/Save

**Files:**
- Create: `src/sync_to_classroom.py`
- Create: `tests/test_classroom_sync.py`

**Step 1: Write the failing tests**

Create `tests/test_classroom_sync.py`:

```python
"""Tests for Google Classroom sync module."""
import sys
import os
import json
import hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestComputeHash:
    def test_same_input_same_hash(self):
        from src.sync_to_classroom import compute_hash
        item = {"title": "Test", "description": "Desc"}
        assert compute_hash(item) == compute_hash(item)

    def test_different_input_different_hash(self):
        from src.sync_to_classroom import compute_hash
        a = {"title": "Test A"}
        b = {"title": "Test B"}
        assert compute_hash(a) != compute_hash(b)

    def test_order_independent(self):
        from src.sync_to_classroom import compute_hash
        a = {"b": 2, "a": 1}
        b = {"a": 1, "b": 2}
        assert compute_hash(a) == compute_hash(b)

    def test_string_input(self):
        from src.sync_to_classroom import compute_hash
        h = compute_hash("simple string")
        assert isinstance(h, str) and len(h) == 16


class TestSyncState:
    def test_load_missing_file(self, tmp_path):
        from src.sync_to_classroom import load_sync_state
        state = load_sync_state(str(tmp_path / "nonexistent.json"))
        assert state == {}

    def test_save_and_load(self, tmp_path):
        from src.sync_to_classroom import load_sync_state, save_sync_state
        path = str(tmp_path / "state.json")
        data = {"key1": {"classroom_id": "abc", "last_hash": "def"}}
        save_sync_state(data, path)
        loaded = load_sync_state(path)
        assert loaded == data
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_classroom_sync.py -v`
Expected: FAIL — module does not exist.

**Step 3: Create the module with core utilities**

Create `src/sync_to_classroom.py`:

```python
"""Sync TED portal data to Google Classroom.

Standalone module: python src/sync_to_classroom.py
Integrated via run_sync.py as Phase 4.
"""
import hashlib
import json
import os
import sys
import time
from datetime import datetime

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src.json_utils import atomic_json_dump
from src.sync_to_google import normalize_course, _api_call_with_retry

TOKEN_FILE = os.path.join(PROJECT_ROOT, "token.json")
DATA_FILE = os.path.join(PROJECT_ROOT, "output", "scraped_data.json")
COURSES_FILE = os.path.join(PROJECT_ROOT, "output", "classroom_courses.json")
SYNC_STATE_FILE = os.path.join(PROJECT_ROOT, "output", "classroom_sync.json")

STUDENT_EMAIL = "isikkurtx@gmail.com"
COURSE_SECTION = "TED Rönesans 2025-26"
GENERAL_COURSE = "TED Genel"


def compute_hash(item):
    """Compute a short hash of an item for change detection."""
    if isinstance(item, str):
        raw = item
    else:
        raw = json.dumps(item, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def load_sync_state(path=None):
    """Load sync state from JSON file. Returns empty dict if missing."""
    path = path or SYNC_STATE_FILE
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_sync_state(state, path=None):
    """Save sync state atomically."""
    path = path or SYNC_STATE_FILE
    atomic_json_dump(state, path)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_classroom_sync.py -v`
Expected: All 6 PASSED.

**Step 5: Commit**

```bash
git add src/sync_to_classroom.py tests/test_classroom_sync.py
git commit -m "feat: add classroom sync module skeleton with hash and state utils"
```

---

### Task 3: Course Management — `ensure_courses`

**Files:**
- Modify: `src/sync_to_classroom.py`
- Modify: `tests/test_classroom_sync.py`

**Step 1: Write the failing tests**

Add to `tests/test_classroom_sync.py`:

```python
from unittest.mock import MagicMock, patch, call


class TestEnsureCourses:
    def _mock_service(self, existing_courses=None):
        """Build a mock Classroom service with optional existing courses."""
        svc = MagicMock()
        # courses().list()
        courses_list = existing_courses or []
        svc.courses().list().execute.return_value = {
            "courses": courses_list
        }
        # courses().create()
        svc.courses().create.return_value.execute.side_effect = lambda: {
            "id": f"new_{time.time()}",
            "name": "mock",
            "courseState": "ACTIVE",
        }
        # invitations().create()
        svc.invitations().create.return_value.execute.return_value = {}
        return svc

    def test_creates_missing_courses(self):
        import time
        from src.sync_to_classroom import ensure_courses, STUDENT_EMAIL
        svc = self._mock_service(existing_courses=[])
        ders_listesi = ["Matematik", "Türkçe"]

        courses = ensure_courses(svc, ders_listesi)

        assert "Matematik" in courses
        assert "Türkçe" in courses
        assert GENERAL_COURSE in courses
        assert svc.courses().create.call_count == 3  # 2 courses + TED Genel

    def test_reuses_existing_courses(self):
        from src.sync_to_classroom import ensure_courses, COURSE_SECTION
        existing = [
            {"id": "c1", "name": "Matematik", "section": COURSE_SECTION, "courseState": "ACTIVE"},
            {"id": "c2", "name": GENERAL_COURSE, "section": COURSE_SECTION, "courseState": "ACTIVE"},
        ]
        svc = self._mock_service(existing_courses=existing)

        courses = ensure_courses(svc, ["Matematik"])

        assert courses["Matematik"] == "c1"
        assert svc.courses().create.call_count == 0  # nothing new

    def test_invites_student(self):
        import time
        from src.sync_to_classroom import ensure_courses, STUDENT_EMAIL
        svc = self._mock_service(existing_courses=[])

        ensure_courses(svc, ["Matematik"])

        # Should have invited student to each new course
        inv_calls = svc.invitations().create.call_args_list
        assert len(inv_calls) >= 2  # Matematik + TED Genel
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_classroom_sync.py::TestEnsureCourses -v`
Expected: FAIL — `ensure_courses` not defined.

**Step 3: Implement `ensure_courses`**

Add to `src/sync_to_classroom.py`:

```python
def get_classroom_service(token_file=None):
    """Build a Classroom API service client."""
    token_file = token_file or TOKEN_FILE
    creds = Credentials.from_authorized_user_file(token_file)
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_file, "w") as f:
            f.write(creds.to_json())
    return build("classroom", "v1", credentials=creds)


def _load_courses_mapping():
    """Load course name -> id mapping from file."""
    if os.path.exists(COURSES_FILE):
        with open(COURSES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_courses_mapping(mapping):
    """Save course name -> id mapping atomically."""
    atomic_json_dump(mapping, COURSES_FILE)


def ensure_courses(service, ders_listesi):
    """Ensure a Classroom course exists for each ders + TED Genel.

    Returns dict: {normalized_name: course_id}
    """
    # Fetch existing courses from API
    result = _api_call_with_retry(
        lambda: service.courses().list(courseStates=["ACTIVE"]).execute()
    ) or {}
    existing = {}
    for c in result.get("courses", []):
        if c.get("section") == COURSE_SECTION:
            existing[c["name"]] = c["id"]

    # Ensure TED Genel is always in the list
    all_courses = list(set(ders_listesi)) + [GENERAL_COURSE]
    mapping = {}

    for name in all_courses:
        if name in existing:
            mapping[name] = existing[name]
            print(f"  Classroom course exists: {name}")
        else:
            body = {
                "name": name,
                "section": COURSE_SECTION,
                "ownerId": "me",
                "courseState": "ACTIVE",
            }
            created = _api_call_with_retry(
                lambda b=body: service.courses().create(body=b).execute()
            )
            if created:
                mapping[name] = created["id"]
                print(f"  Classroom course created: {name}")
                _invite_student(service, created["id"])
            else:
                print(f"  [ERROR] Failed to create course: {name}")

    _save_courses_mapping(mapping)
    return mapping


def _invite_student(service, course_id):
    """Invite STUDENT_EMAIL to a course. Ignores 409 (already enrolled)."""
    body = {
        "courseId": course_id,
        "userId": STUDENT_EMAIL,
        "role": "STUDENT",
    }
    try:
        _api_call_with_retry(
            lambda: service.invitations().create(body=body).execute()
        )
        print(f"    Invited {STUDENT_EMAIL}")
    except Exception as e:
        status = getattr(getattr(e, "resp", None), "status", 0)
        if status == 409:
            pass  # already enrolled
        else:
            print(f"    [WARN] Invite failed: {e}")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_classroom_sync.py::TestEnsureCourses -v`
Expected: 3 PASSED.

**Step 5: Commit**

```bash
git add src/sync_to_classroom.py tests/test_classroom_sync.py
git commit -m "feat: add course management with ensure_courses and student invitation"
```

---

### Task 4: Sync Homework — `sync_odevler`

**Files:**
- Modify: `src/sync_to_classroom.py`
- Modify: `tests/test_classroom_sync.py`

**Step 1: Write the failing tests**

Add to `tests/test_classroom_sync.py`:

```python
class TestSyncOdevler:
    def _mock_service(self):
        svc = MagicMock()
        svc.courses().courseWork().list().execute.return_value = {"courseWork": []}
        svc.courses().courseWork().create.return_value.execute.return_value = {"id": "cw1"}
        svc.courses().courseWork().patch.return_value.execute.return_value = {"id": "cw1"}
        return svc

    def test_creates_new_homework(self):
        from src.sync_to_classroom import sync_odevler
        svc = self._mock_service()
        courses = {"Matematik": "c1", "TED Genel": "cg"}
        data = {
            "odevlerim": {
                "homework": {
                    "headers": ["Ders Adı", "Ödev Başlığı", "Ödev Kaynağı",
                                "Ödev Son Teslim Tarihi", "Ödev Durumu", "Ödev Görüntüle"],
                    "rows": [{
                        "Ders Adı": "Matematik",
                        "Ödev Başlığı": "Test Ödevi",
                        "Ödev Kaynağı": "portal",
                        "Ödev Son Teslim Tarihi": "27.02.2026 12:00",
                        "Ödev Durumu": "Değerlendirilmemiş",
                        "detail": {"description": "Sayfa 10-15", "attachments": []}
                    }]
                }
            }
        }
        state = {}

        result = sync_odevler(svc, courses, data, state)

        assert result["added"] == 1
        assert result["errors"] == 0

    def test_skips_unchanged_homework(self):
        from src.sync_to_classroom import sync_odevler, compute_hash
        svc = self._mock_service()
        courses = {"Matematik": "c1", "TED Genel": "cg"}
        row = {
            "Ders Adı": "Matematik",
            "Ödev Başlığı": "Test Ödevi",
            "Ödev Kaynağı": "portal",
            "Ödev Son Teslim Tarihi": "27.02.2026 12:00",
            "Ödev Durumu": "Değerlendirilmemiş",
            "detail": {"description": "Sayfa 10-15", "attachments": []}
        }
        data = {"odevlerim": {"homework": {"headers": [], "rows": [row]}}}
        key = "cw:c1:Test Ödevi"
        state = {key: {"classroom_id": "existing1", "last_hash": compute_hash(row)}}

        result = sync_odevler(svc, courses, data, state)

        assert result["added"] == 0
        assert result["skipped"] == 1

    def test_unmapped_course_goes_to_genel(self):
        from src.sync_to_classroom import sync_odevler
        svc = self._mock_service()
        courses = {"TED Genel": "cg"}  # no Matematik course
        data = {
            "odevlerim": {
                "homework": {
                    "headers": [],
                    "rows": [{
                        "Ders Adı": "Matematik",
                        "Ödev Başlığı": "Ödev X",
                        "Ödev Son Teslim Tarihi": "27.02.2026 12:00",
                        "Ödev Durumu": "",
                        "detail": {"description": "Desc", "attachments": []}
                    }]
                }
            }
        }
        state = {}

        result = sync_odevler(svc, courses, data, state)

        assert result["added"] == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_classroom_sync.py::TestSyncOdevler -v`
Expected: FAIL — `sync_odevler` not defined.

**Step 3: Implement `sync_odevler`**

Add to `src/sync_to_classroom.py`:

```python
def _parse_turkish_datetime(s):
    """Parse '27.02.2026 12:00' to (date_dict, time_dict) for Classroom API."""
    try:
        dt = datetime.strptime(s.strip(), "%d.%m.%Y %H:%M")
        date_dict = {"year": dt.year, "month": dt.month, "day": dt.day}
        time_dict = {"hours": dt.hour, "minutes": dt.minute}
        return date_dict, time_dict
    except (ValueError, AttributeError):
        return None, None


def _resolve_course_id(courses, ders_adi):
    """Map a course name to its Classroom course ID, falling back to TED Genel."""
    normalized = normalize_course(ders_adi)
    return courses.get(normalized, courses.get(GENERAL_COURSE))


def sync_odevler(service, courses, data, state):
    """Sync homework to Classroom as courseWork (ASSIGNMENT).

    Returns dict: {added, updated, skipped, errors}
    """
    result = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
    rows = (data.get("odevlerim", {})
                .get("homework", {})
                .get("rows", []))

    for row in rows:
        ders = row.get("Ders Adı", "")
        baslik = row.get("Ödev Başlığı", "")
        course_id = _resolve_course_id(courses, ders)
        if not course_id:
            result["errors"] += 1
            continue

        dedup_key = f"cw:{course_id}:{baslik}"
        current_hash = compute_hash(row)

        # Check state for existing entry
        existing = state.get(dedup_key)
        if existing and existing["last_hash"] == current_hash:
            result["skipped"] += 1
            continue

        # Build courseWork body
        description = row.get("detail", {}).get("description", "")
        durum = row.get("Ödev Durumu", "")
        if durum:
            description = f"Durum: {durum}\n\n{description}"

        body = {
            "title": baslik,
            "description": description[:2000],  # API limit
            "workType": "ASSIGNMENT",
            "state": "PUBLISHED",
        }

        # Add due date if available
        due_str = row.get("Ödev Son Teslim Tarihi", "")
        due_date, due_time = _parse_turkish_datetime(due_str)
        if due_date:
            body["dueDate"] = due_date
            body["dueTime"] = due_time

        # Add attachment links
        attachments = row.get("detail", {}).get("attachments", [])
        if attachments:
            body["materials"] = [
                {"link": {"url": att["url"], "title": att.get("name", "Ek")}}
                for att in attachments if att.get("url")
            ]

        if existing:
            # Update existing
            cw_id = existing["classroom_id"]
            updated = _api_call_with_retry(
                lambda: service.courses().courseWork().patch(
                    courseId=course_id, id=cw_id,
                    updateMask="title,description,dueDate,dueTime,materials",
                    body=body,
                ).execute()
            )
            if updated:
                state[dedup_key] = {"classroom_id": cw_id, "last_hash": current_hash}
                result["updated"] += 1
            else:
                result["errors"] += 1
        else:
            # Create new
            created = _api_call_with_retry(
                lambda: service.courses().courseWork().create(
                    courseId=course_id, body=body,
                ).execute()
            )
            if created:
                state[dedup_key] = {"classroom_id": created["id"], "last_hash": current_hash}
                result["added"] += 1
            else:
                result["errors"] += 1

    print(f"  Ödevler: +{result['added']} ~{result['updated']} "
          f"={result['skipped']} !{result['errors']}")
    return result
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_classroom_sync.py::TestSyncOdevler -v`
Expected: 3 PASSED.

**Step 5: Commit**

```bash
git add src/sync_to_classroom.py tests/test_classroom_sync.py
git commit -m "feat: add homework sync to Classroom as coursework assignments"
```

---

### Task 5: Sync Course Materials — `sync_ders_icerikleri`

**Files:**
- Modify: `src/sync_to_classroom.py`
- Modify: `tests/test_classroom_sync.py`

**Step 1: Write the failing tests**

Add to `tests/test_classroom_sync.py`:

```python
class TestSyncDersIcerikleri:
    def _mock_service(self):
        svc = MagicMock()
        svc.courses().courseWorkMaterials().list().execute.return_value = {"courseWorkMaterial": []}
        svc.courses().courseWorkMaterials().create.return_value.execute.return_value = {"id": "m1"}
        svc.courses().courseWorkMaterials().patch.return_value.execute.return_value = {"id": "m1"}
        return svc

    def test_creates_material_for_course(self):
        from src.sync_to_classroom import sync_ders_icerikleri
        svc = self._mock_service()
        courses = {"Türkçe": "ct", "TED Genel": "cg"}
        data = {
            "ders_icerikleri": {
                "Türkçe": {
                    "tab_id": "ders_1",
                    "text": "23. HAFTA\nBu hafta cümle analizi yapacağız."
                }
            }
        }
        state = {}

        result = sync_ders_icerikleri(svc, courses, data, state)

        assert result["added"] == 1

    def test_skips_genel_tab(self):
        from src.sync_to_classroom import sync_ders_icerikleri
        svc = self._mock_service()
        courses = {"TED Genel": "cg"}
        data = {
            "ders_icerikleri": {
                "Genel": {"tab_id": "tab_genel", "text": "Genel duyuru"}
            }
        }
        state = {}

        result = sync_ders_icerikleri(svc, courses, data, state)

        # Genel content goes to TED Genel as material
        assert result["added"] == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_classroom_sync.py::TestSyncDersIcerikleri -v`
Expected: FAIL — `sync_ders_icerikleri` not defined.

**Step 3: Implement `sync_ders_icerikleri`**

Add to `src/sync_to_classroom.py`:

```python
def sync_ders_icerikleri(service, courses, data, state):
    """Sync course content as courseWorkMaterials.

    Returns dict: {added, updated, skipped, errors}
    """
    result = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
    ders_data = data.get("ders_icerikleri", {})

    for ders_name, content in ders_data.items():
        if not isinstance(content, dict) or not content.get("text"):
            continue

        text = content["text"].strip()
        if not text:
            continue

        # Map course name
        if ders_name == "Genel":
            course_id = courses.get(GENERAL_COURSE)
            title = "Genel Duyuru"
        else:
            normalized = normalize_course(ders_name)
            course_id = courses.get(normalized, courses.get(GENERAL_COURSE))
            title = f"{normalized} - Haftalık İçerik"

        if not course_id:
            result["errors"] += 1
            continue

        dedup_key = f"mat:{course_id}:{title}"
        current_hash = compute_hash(text)

        existing = state.get(dedup_key)
        if existing and existing["last_hash"] == current_hash:
            result["skipped"] += 1
            continue

        body = {
            "title": title,
            "description": text[:2000],
            "state": "PUBLISHED",
        }

        if existing:
            mat_id = existing["classroom_id"]
            updated = _api_call_with_retry(
                lambda: service.courses().courseWorkMaterials().patch(
                    courseId=course_id, id=mat_id,
                    updateMask="title,description",
                    body=body,
                ).execute()
            )
            if updated:
                state[dedup_key] = {"classroom_id": mat_id, "last_hash": current_hash}
                result["updated"] += 1
            else:
                result["errors"] += 1
        else:
            created = _api_call_with_retry(
                lambda: service.courses().courseWorkMaterials().create(
                    courseId=course_id, body=body,
                ).execute()
            )
            if created:
                state[dedup_key] = {"classroom_id": created["id"], "last_hash": current_hash}
                result["added"] += 1
            else:
                result["errors"] += 1

    print(f"  Ders içerikleri: +{result['added']} ~{result['updated']} "
          f"={result['skipped']} !{result['errors']}")
    return result
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_classroom_sync.py::TestSyncDersIcerikleri -v`
Expected: 2 PASSED.

**Step 5: Commit**

```bash
git add src/sync_to_classroom.py tests/test_classroom_sync.py
git commit -m "feat: add course materials sync to Classroom"
```

---

### Task 6: Sync Grades — `sync_notlar`

**Files:**
- Modify: `src/sync_to_classroom.py`
- Modify: `tests/test_classroom_sync.py`

**Step 1: Write the failing tests**

Add to `tests/test_classroom_sync.py`:

```python
class TestSyncNotlar:
    def _mock_service(self):
        svc = MagicMock()
        svc.courses().courseWork().list().execute.return_value = {"courseWork": []}
        svc.courses().courseWork().create.return_value.execute.return_value = {"id": "cw_grade1"}
        svc.courses().courseWork().patch.return_value.execute.return_value = {"id": "cw_grade1"}
        return svc

    def test_creates_grade_coursework(self):
        from src.sync_to_classroom import sync_notlar
        svc = self._mock_service()
        courses = {"Bilişim": "cb", "TED Genel": "cg"}
        data = {
            "gelisim_raporu": {
                "grades": [
                    {
                        "Ders": "Bilişim Teknolojileri",
                        "1. Sınav": "100",
                        "2. Sınav": "98",
                        "3. Sınav": "-",
                        "DİKP/Performans-1": "100",
                    }
                ]
            }
        }
        state = {}

        result = sync_notlar(svc, courses, data, state)

        # Should create coursework for each exam with a numeric grade
        assert result["added"] >= 2  # 1. Sınav=100, 2. Sınav=98

    def test_skips_dash_grades(self):
        from src.sync_to_classroom import sync_notlar
        svc = self._mock_service()
        courses = {"Matematik": "cm", "TED Genel": "cg"}
        data = {
            "gelisim_raporu": {
                "grades": [{"Ders": "Matematik", "1. Sınav": "-"}]
            }
        }
        state = {}

        result = sync_notlar(svc, courses, data, state)

        assert result["added"] == 0
        assert result["skipped"] == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_classroom_sync.py::TestSyncNotlar -v`
Expected: FAIL — `sync_notlar` not defined.

**Step 3: Implement `sync_notlar`**

Add to `src/sync_to_classroom.py`:

```python
def sync_notlar(service, courses, data, state):
    """Sync grade report as courseWork entries with maxPoints.

    Each exam/performance column becomes a separate SHORT_ANSWER_QUESTION
    courseWork with the grade recorded in the title.

    Returns dict: {added, updated, skipped, errors}
    """
    result = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
    grades = data.get("gelisim_raporu", {}).get("grades", [])

    for entry in grades:
        ders = entry.get("Ders", "")
        normalized = normalize_course(ders)
        course_id = courses.get(normalized, courses.get(GENERAL_COURSE))
        if not course_id:
            result["errors"] += 1
            continue

        # Iterate over exam/performance columns
        for col, value in entry.items():
            if col == "Ders":
                continue

            # Skip non-numeric grades
            try:
                score = float(value)
            except (ValueError, TypeError):
                result["skipped"] += 1
                continue

            title = f"Not: {normalized} - {col}"
            dedup_key = f"grade:{course_id}:{col}"
            current_hash = compute_hash({"score": score})

            existing = state.get(dedup_key)
            if existing and existing["last_hash"] == current_hash:
                result["skipped"] += 1
                continue

            body = {
                "title": title,
                "description": f"{normalized} dersi {col} notu: {score:.0f}/100",
                "workType": "SHORT_ANSWER_QUESTION",
                "maxPoints": 100,
                "state": "PUBLISHED",
            }

            if existing:
                cw_id = existing["classroom_id"]
                updated = _api_call_with_retry(
                    lambda: service.courses().courseWork().patch(
                        courseId=course_id, id=cw_id,
                        updateMask="title,description,maxPoints",
                        body=body,
                    ).execute()
                )
                if updated:
                    state[dedup_key] = {"classroom_id": cw_id, "last_hash": current_hash}
                    result["updated"] += 1
                else:
                    result["errors"] += 1
            else:
                created = _api_call_with_retry(
                    lambda: service.courses().courseWork().create(
                        courseId=course_id, body=body,
                    ).execute()
                )
                if created:
                    state[dedup_key] = {"classroom_id": created["id"], "last_hash": current_hash}
                    result["added"] += 1
                else:
                    result["errors"] += 1

    print(f"  Notlar: +{result['added']} ~{result['updated']} "
          f"={result['skipped']} !{result['errors']}")
    return result
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_classroom_sync.py::TestSyncNotlar -v`
Expected: 2 PASSED.

**Step 5: Commit**

```bash
git add src/sync_to_classroom.py tests/test_classroom_sync.py
git commit -m "feat: add grade sync to Classroom as coursework with scores"
```

---

### Task 7: Sync Announcements — `sync_duyurular`

**Files:**
- Modify: `src/sync_to_classroom.py`
- Modify: `tests/test_classroom_sync.py`

**Step 1: Write the failing tests**

Add to `tests/test_classroom_sync.py`:

```python
class TestSyncDuyurular:
    def _mock_service(self):
        svc = MagicMock()
        svc.courses().announcements().list().execute.return_value = {"announcements": []}
        svc.courses().announcements().create.return_value.execute.return_value = {"id": "a1"}
        svc.courses().announcements().patch.return_value.execute.return_value = {"id": "a1"}
        return svc

    def test_creates_announcement(self):
        from src.sync_to_classroom import sync_duyurular
        svc = self._mock_service()
        courses = {"TED Genel": "cg", "Matematik": "cm"}
        data = {
            "duyurular": {
                "announcements": [
                    {
                        "e-Posta Başlık": "Sınav Haftası Duyurusu",
                        "Yayın Tarihi": "01.02.2026 19:00",
                        "Ekleri": "",
                    }
                ]
            }
        }
        state = {}

        result = sync_duyurular(svc, courses, data, state)

        assert result["added"] >= 1

    def test_creates_takvim_announcements(self):
        from src.sync_to_classroom import sync_duyurular
        svc = self._mock_service()
        courses = {"TED Genel": "cg"}
        data = {
            "duyurular": {"announcements": []},
            "takvim": [
                {
                    "title": "Satranç Turnuvası",
                    "start": "2026-01-19T11:00:00Z",
                    "end": "2026-01-19T13:00:00Z",
                }
            ],
        }
        state = {}

        result = sync_duyurular(svc, courses, data, state)

        assert result["added"] >= 1

    def test_takim_as_announcement(self):
        from src.sync_to_classroom import sync_duyurular
        svc = self._mock_service()
        courses = {"TED Genel": "cg"}
        data = {
            "duyurular": {"announcements": []},
            "takvim": [],
            "takim_calismalari": {
                "activities": {
                    "headers": [],
                    "rows": [{
                        "Academy+": "Ortaokul-Koro",
                        "Çalışma Başlangıç": "05.03.2026 15:50",
                        "Çalışma Bitiş": "05.03.2026 16:40",
                        "Katılım Durumu": "",
                        "Teams Link": "Yüz Yüze",
                    }]
                }
            },
            "ogep": {"sessions": {"headers": [], "rows": []}},
        }
        state = {}

        result = sync_duyurular(svc, courses, data, state)

        assert result["added"] >= 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_classroom_sync.py::TestSyncDuyurular -v`
Expected: FAIL — `sync_duyurular` not defined.

**Step 3: Implement `sync_duyurular`**

Add to `src/sync_to_classroom.py`:

```python
def sync_duyurular(service, courses, data, state):
    """Sync announcements, calendar events, team activities, and ÖGEP as announcements.

    Returns dict: {added, updated, skipped, errors}
    """
    result = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
    genel_id = courses.get(GENERAL_COURSE)

    # 1. School announcements -> TED Genel
    for ann in data.get("duyurular", {}).get("announcements", []):
        baslik = ann.get("e-Posta Başlık", "")
        tarih = ann.get("Yayın Tarihi", "")
        text = f"{baslik}\n\nYayın: {tarih}"
        _upsert_announcement(service, genel_id, text, state, result)

    # 2. Calendar events -> relevant course or TED Genel
    for ev in data.get("takvim", []):
        title = ev.get("title", "")
        start = ev.get("start", "")
        text = f"Takvim: {title}\nTarih: {start}"
        _upsert_announcement(service, genel_id, text, state, result)

    # 3. Team activities -> TED Genel
    rows = (data.get("takim_calismalari", {})
                .get("activities", {})
                .get("rows", []))
    for row in rows:
        name = row.get("Academy+", "")
        baslangic = row.get("Çalışma Başlangıç", "")
        bitis = row.get("Çalışma Bitiş", "")
        durum = row.get("Katılım Durumu", "")
        text = f"Takım: {name}\nBaşlangıç: {baslangic}\nBitiş: {bitis}"
        if durum:
            text += f"\nKatılım: {durum}"
        _upsert_announcement(service, genel_id, text, state, result)

    # 4. ÖGEP sessions -> TED Genel
    ogep_rows = (data.get("ogep", {})
                     .get("sessions", {})
                     .get("rows", []))
    for row in ogep_rows:
        name = row.get("ÖGEP (Öğrenci Gelişim Programı)", "")
        baslangic = row.get("Çalışma Başlangıç", "")
        text = f"ÖGEP: {name}\nTarih: {baslangic}"
        _upsert_announcement(service, genel_id, text, state, result)

    print(f"  Duyurular: +{result['added']} ~{result['updated']} "
          f"={result['skipped']} !{result['errors']}")
    return result


def _upsert_announcement(service, course_id, text, state, result):
    """Create or update a single announcement."""
    if not course_id or not text.strip():
        result["errors"] += 1
        return

    dedup_key = f"ann:{course_id}:{text[:100]}"
    current_hash = compute_hash(text)

    existing = state.get(dedup_key)
    if existing and existing["last_hash"] == current_hash:
        result["skipped"] += 1
        return

    body = {"text": text[:2000], "state": "PUBLISHED"}

    if existing:
        ann_id = existing["classroom_id"]
        updated = _api_call_with_retry(
            lambda: service.courses().announcements().patch(
                courseId=course_id, id=ann_id,
                updateMask="text",
                body=body,
            ).execute()
        )
        if updated:
            state[dedup_key] = {"classroom_id": ann_id, "last_hash": current_hash}
            result["updated"] += 1
        else:
            result["errors"] += 1
    else:
        created = _api_call_with_retry(
            lambda: service.courses().announcements().create(
                courseId=course_id, body=body,
            ).execute()
        )
        if created:
            state[dedup_key] = {"classroom_id": created["id"], "last_hash": current_hash}
            result["added"] += 1
        else:
            result["errors"] += 1
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_classroom_sync.py::TestSyncDuyurular -v`
Expected: 3 PASSED.

**Step 5: Commit**

```bash
git add src/sync_to_classroom.py tests/test_classroom_sync.py
git commit -m "feat: add announcement sync for duyurular, takvim, takim, and ogep"
```

---

### Task 8: Main Entry Point and `--reset-courses`

**Files:**
- Modify: `src/sync_to_classroom.py`
- Modify: `tests/test_classroom_sync.py`

**Step 1: Write the failing tests**

Add to `tests/test_classroom_sync.py`:

```python
class TestMain:
    @patch("src.sync_to_classroom.get_classroom_service")
    @patch("src.sync_to_classroom.ensure_courses")
    @patch("src.sync_to_classroom.sync_odevler")
    @patch("src.sync_to_classroom.sync_ders_icerikleri")
    @patch("src.sync_to_classroom.sync_notlar")
    @patch("src.sync_to_classroom.sync_duyurular")
    @patch("src.sync_to_classroom.save_sync_state")
    def test_main_orchestrates_all_syncs(self, mock_save, mock_duyuru,
                                          mock_notlar, mock_ders, mock_odev,
                                          mock_ensure, mock_svc):
        from src.sync_to_classroom import main
        import json

        # Setup
        mock_svc.return_value = MagicMock()
        mock_ensure.return_value = {"Matematik": "c1", "TED Genel": "cg"}
        mock_odev.return_value = {"added": 1, "updated": 0, "skipped": 0, "errors": 0}
        mock_ders.return_value = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
        mock_notlar.return_value = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
        mock_duyuru.return_value = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}

        # Provide scraped_data
        test_data = {
            "ders_programi": [{"schedule": {"rows": [
                ["", "Pazartesi"], ["1. Ders", "Matematik"]
            ]}}],
            "odevlerim": {"homework": {"rows": []}},
            "ders_icerikleri": {},
            "gelisim_raporu": {"grades": []},
            "duyurular": {"announcements": []},
            "takvim": [],
            "takim_calismalari": {"activities": {"rows": []}},
            "ogep": {"sessions": {"rows": []}},
        }

        main(scraped_data=test_data)

        mock_ensure.assert_called_once()
        mock_odev.assert_called_once()
        mock_ders.assert_called_once()
        mock_notlar.assert_called_once()
        mock_duyuru.assert_called_once()
        mock_save.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_classroom_sync.py::TestMain -v`
Expected: FAIL — `main` not defined.

**Step 3: Implement `main`**

Add to `src/sync_to_classroom.py`:

```python
def _extract_course_names(data):
    """Extract unique course names from ders_programi schedule."""
    names = set()
    for week in data.get("ders_programi", []):
        rows = week.get("schedule", {}).get("rows", [])
        for row in rows[1:]:  # skip header row
            for cell in row[1:]:  # skip time column
                if cell and "\n" in cell:
                    raw_name = cell.split("\n")[0].strip()
                    if raw_name:
                        names.add(normalize_course(raw_name))
    return sorted(names)


def main(scraped_data=None, token_file=None, reset_courses=False):
    """Main entry point for Classroom sync.

    Args:
        scraped_data: Pre-loaded data dict. If None, reads from DATA_FILE.
        token_file: OAuth token file path.
        reset_courses: If True, delete and recreate all courses.
    """
    print("\n--- Classroom Sync ---")

    # Load data
    if scraped_data is None:
        if not os.path.exists(DATA_FILE):
            print("  [SKIP] No scraped data found")
            return
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            scraped_data = json.load(f)

    # Build service
    service = get_classroom_service(token_file)

    # Reset courses if requested
    if reset_courses:
        print("  Resetting courses...")
        mapping = _load_courses_mapping()
        for name, cid in mapping.items():
            _api_call_with_retry(
                lambda c=cid: service.courses().patch(
                    id=c, updateMask="courseState",
                    body={"courseState": "ARCHIVED"},
                ).execute()
            )
            print(f"    Archived: {name}")
        _save_courses_mapping({})

    # Extract course list and ensure courses exist
    ders_listesi = _extract_course_names(scraped_data)
    courses = ensure_courses(service, ders_listesi)

    # Load sync state
    state = load_sync_state()

    # Run all sync functions
    sync_odevler(service, courses, scraped_data, state)
    sync_ders_icerikleri(service, courses, scraped_data, state)
    sync_notlar(service, courses, scraped_data, state)
    sync_duyurular(service, courses, scraped_data, state)

    # Save state
    save_sync_state(state)
    print("  Classroom sync complete.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sync TED data to Google Classroom")
    parser.add_argument("--reset-courses", action="store_true",
                        help="Archive and recreate all courses")
    parser.add_argument("--token", default=None,
                        help="Path to OAuth token file")
    args = parser.parse_args()
    main(token_file=args.token, reset_courses=args.reset_courses)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_classroom_sync.py::TestMain -v`
Expected: 1 PASSED.

**Step 5: Run all tests**

Run: `pytest -v`
Expected: All pass.

**Step 6: Commit**

```bash
git add src/sync_to_classroom.py tests/test_classroom_sync.py
git commit -m "feat: add main entry point with standalone CLI and --reset-courses"
```

---

### Task 9: Integrate into `run_sync.py`

**Files:**
- Modify: `src/run_sync.py:120-131` (between AI enrichment and health check)

**Step 1: Write the failing test**

Add to `tests/test_classroom_sync.py`:

```python
class TestRunSyncIntegration:
    def test_run_sync_imports_classroom(self):
        """Verify run_sync.py can import the classroom sync function."""
        from src.sync_to_classroom import main as sync_classroom
        assert callable(sync_classroom)
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/test_classroom_sync.py::TestRunSyncIntegration -v`
Expected: PASS (already importable from previous tasks).

**Step 3: Add Classroom phase to run_sync.py**

In `src/run_sync.py`, add Phase 5 between AI Enrichment (line 130) and Health Check (line 132):

```python
    # 5. Classroom sync
    print("\n--- Classroom Sync ---")
    try:
        from src.sync_to_classroom import main as sync_classroom
        sync_classroom(scraped_data=data)
    except Exception as e:
        scrape_errors.append(f"classroom_sync: {e}")
        print(f"[WARN] Classroom sync failed: {e}")
```

**Step 4: Add classroom fields to health check**

No code change needed — errors already flow into `scrape_errors` and get written to `health.json`.

**Step 5: Run all tests**

Run: `pytest -v`
Expected: All pass.

**Step 6: Commit**

```bash
git add src/run_sync.py tests/test_classroom_sync.py
git commit -m "feat: integrate Classroom sync into run_sync.py pipeline"
```

---

### Task 10: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add Classroom entries**

Add to the Commands section:
```
python src/sync_to_classroom.py              # Sync to Google Classroom (standalone)
python src/sync_to_classroom.py --reset-courses  # Archive and recreate all courses
```

Add to the Core Modules table:
```
| `src/sync_to_classroom.py` | Syncs TED data to Google Classroom (courses, assignments, materials, grades, announcements) |
```

Add to the Data Flow diagram:
```
TED Portal → scraped_data.json → sync_to_classroom.py → Google Classroom
```

Add to Key Patterns:
```
- **Classroom sync**: `sync_to_classroom.py` creates per-course Classroom courses, syncs homework as courseWork (ASSIGNMENT), course content as courseWorkMaterial, grades as SHORT_ANSWER courseWork with scores, and announcements/calendar/team/ÖGEP as announcements. Uses hash-based change detection in `output/classroom_sync.json` to skip unchanged items and update modified ones. Student `isikkurtx@gmail.com` is auto-invited to all courses.
```

Add to Required Credentials note:
```
After adding Classroom scopes, existing tokens must be regenerated: delete `token.json` and run `python src/google_auth.py`.
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add Classroom sync to CLAUDE.md"
```
