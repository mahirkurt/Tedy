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
