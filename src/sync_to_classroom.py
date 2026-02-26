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
    result = _api_call_with_retry(
        lambda: service.courses().list(courseStates=["ACTIVE"]).execute()
    ) or {}
    existing = {}
    for c in result.get("courses", []):
        if c.get("section") == COURSE_SECTION:
            existing[c["name"]] = c["id"]

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
            pass
        else:
            print(f"    [WARN] Invite failed: {e}")
