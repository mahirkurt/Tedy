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

        existing = state.get(dedup_key)
        if existing and existing["last_hash"] == current_hash:
            result["skipped"] += 1
            continue

        description = row.get("detail", {}).get("description", "")
        durum = row.get("Ödev Durumu", "")
        if durum:
            description = f"Durum: {durum}\n\n{description}"

        body = {
            "title": baslik,
            "description": description[:2000],
            "workType": "ASSIGNMENT",
            "state": "PUBLISHED",
        }

        due_str = row.get("Ödev Son Teslim Tarihi", "")
        due_date, due_time = _parse_turkish_datetime(due_str)
        if due_date:
            body["dueDate"] = due_date
            body["dueTime"] = due_time

        attachments = row.get("detail", {}).get("attachments", [])
        if attachments:
            body["materials"] = [
                {"link": {"url": att["url"], "title": att.get("name", "Ek")}}
                for att in attachments if att.get("url")
            ]

        if existing:
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

        for col, value in entry.items():
            if col == "Ders":
                continue

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
                "description": (
                    f"{normalized} dersi {col} notu:"
                    f" {score:.0f}/100"
                ),
                "workType": "SHORT_ANSWER_QUESTION",
                "maxPoints": 100,
                "state": "PUBLISHED",
            }

            if existing:
                cw_id = existing["classroom_id"]
                updated = _api_call_with_retry(
                    lambda cid=course_id, cwid=cw_id, b=body: (
                        service.courses().courseWork().patch(
                            courseId=cid, id=cwid,
                            updateMask="title,description,maxPoints",
                            body=b,
                        ).execute()
                    )
                )
                if updated:
                    state[dedup_key] = {
                        "classroom_id": cw_id,
                        "last_hash": current_hash,
                    }
                    result["updated"] += 1
                else:
                    result["errors"] += 1
            else:
                created = _api_call_with_retry(
                    lambda cid=course_id, b=body: (
                        service.courses().courseWork().create(
                            courseId=cid, body=b,
                        ).execute()
                    )
                )
                if created:
                    state[dedup_key] = {
                        "classroom_id": created["id"],
                        "last_hash": current_hash,
                    }
                    result["added"] += 1
                else:
                    result["errors"] += 1

    print(f"  Notlar: +{result['added']} ~{result['updated']} "
          f"={result['skipped']} !{result['errors']}")
    return result


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
