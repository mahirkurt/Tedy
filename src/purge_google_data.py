#!/usr/bin/env python3
"""Purge Google Workspace data previously synced by this project.

Deletes:
- Classroom courses listed in output/classroom_courses.json
- Calendar events tagged with privateExtendedProperty source=ted-portal
- Drive files referenced by local upload trackers

Then clears local Google-related state tracker files in output/.
"""

from __future__ import annotations

import json
import os
import socket
import sys
from typing import Any

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, PROJECT_ROOT)

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
socket.setdefaulttimeout(20)

from src.json_utils import atomic_json_dump  # noqa: E402
from src.sync_to_classroom import get_classroom_service  # noqa: E402
from src.sync_to_google import get_services  # noqa: E402


OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

CLASSROOM_COURSES_FILE = os.path.join(OUTPUT_DIR, "classroom_courses.json")
CLASSROOM_SYNC_FILE = os.path.join(OUTPUT_DIR, "classroom_sync.json")
CALENDAR_NAME = "TED Rönesans"
CLASSROOM_SECTION = "TED Rönesans 2025-26"

DRIVE_TRACKERS = (
    os.path.join(OUTPUT_DIR, "uploaded_files.json"),
    os.path.join(OUTPUT_DIR, "eba_textbooks_uploaded.json"),
    os.path.join(OUTPUT_DIR, "mebi_videos_uploaded.json"),
    os.path.join(OUTPUT_DIR, "sebitv_uploaded.json"),
    os.path.join(OUTPUT_DIR, "sebitv_interactive_uploaded.json"),
)


def _load_json(path: str) -> Any:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _iter_drive_ids(payload: Any):
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, dict):
                drive_id = value.get("driveId") or value.get("id")
                if isinstance(drive_id, str) and drive_id.strip():
                    yield drive_id.strip()
                qbank_id = value.get("qbankDriveId")
                if isinstance(qbank_id, str) and qbank_id.strip():
                    yield qbank_id.strip()


def _status_code(exc: Exception) -> int | None:
    return getattr(getattr(exc, "resp", None), "status", None)


def _discover_course_ids(service) -> set[str]:
    discovered: set[str] = set()
    for state in ("ACTIVE", "PROVISIONED", "ARCHIVED"):
        page_token = None
        seen_tokens: set[str | None] = set()
        while True:
            if page_token in seen_tokens:
                break
            seen_tokens.add(page_token)
            try:
                result = service.courses().list(
                    courseStates=[state],
                    pageToken=page_token,
                ).execute()
            except Exception:
                break

            for item in result.get("courses", []):
                section = str(item.get("section", "")).strip()
                course_id = str(item.get("id", "")).strip()
                if section == CLASSROOM_SECTION and course_id:
                    discovered.add(course_id)

            page_token = result.get("nextPageToken")
            if not page_token:
                break
    return discovered


def _find_calendar_id(cal_service, summary: str) -> str | None:
    page_token = None
    seen_tokens: set[str | None] = set()
    while True:
        if page_token in seen_tokens:
            break
        seen_tokens.add(page_token)
        result = cal_service.calendarList().list(
            pageToken=page_token,
        ).execute()
        for item in result.get("items", []):
            if item.get("summary") == summary:
                return item.get("id")
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return None


def _purge_classroom() -> dict[str, int]:
    service = get_classroom_service()
    mapping = _load_json(CLASSROOM_COURSES_FILE)

    if not isinstance(mapping, dict):
        mapping = {}

    course_ids = {
        str(cid).strip()
        for cid in mapping.values()
        if isinstance(cid, str) and str(cid).strip()
    }
    course_ids |= _discover_course_ids(service)

    if not course_ids:
        return {
            "deleted": 0,
            "archived": 0,
            "failed": 0,
            "coursework_deleted": 0,
            "coursework_failed": 0,
            "ann_deleted": 0,
            "ann_failed": 0,
        }

    deleted = 0
    archived = 0
    failed = 0
    coursework_deleted = 0
    coursework_failed = 0
    ann_deleted = 0
    ann_failed = 0

    for course_id in sorted(course_ids):
        try:
            service.courses().delete(id=course_id).execute()
            deleted += 1
            continue
        except Exception as exc:
            if _status_code(exc) in (404, 410):
                deleted += 1
                continue

        try:
            service.courses().patch(
                id=course_id,
                updateMask="courseState",
                body={"courseState": "ARCHIVED"},
            ).execute()
            archived += 1
        except Exception as exc:
            if _status_code(exc) not in (404, 410):
                failed += 1

        try:
            service.courses().delete(id=course_id).execute()
            deleted += 1
        except Exception as exc:
            if _status_code(exc) in (404, 410):
                deleted += 1
            else:
                failed += 1

    return {
        "deleted": deleted,
        "archived": archived,
        "failed": failed,
        "coursework_deleted": coursework_deleted,
        "coursework_failed": coursework_failed,
        "ann_deleted": ann_deleted,
        "ann_failed": ann_failed,
    }


def _purge_calendar() -> dict[str, int]:
    cal_service, _ = get_services()
    cal_id = _find_calendar_id(cal_service, CALENDAR_NAME)
    if not cal_id:
        return {"deleted": 0, "failed": 0}

    deleted = 0
    failed = 0
    page_token = None
    seen_tokens: set[str | None] = set()

    while True:
        if page_token in seen_tokens:
            break
        seen_tokens.add(page_token)
        result = cal_service.events().list(
            calendarId=cal_id,
            privateExtendedProperty="source=ted-portal",
            maxResults=2500,
            pageToken=page_token,
            singleEvents=True,
        ).execute()
        for event in result.get("items", []):
            event_id = event.get("id")
            if not event_id:
                continue
            try:
                cal_service.events().delete(
                    calendarId=cal_id,
                    eventId=event_id,
                ).execute()
                deleted += 1
            except Exception as exc:
                if _status_code(exc) in (404, 410):
                    deleted += 1
                else:
                    failed += 1

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    return {"deleted": deleted, "failed": failed}


def _purge_drive() -> dict[str, int]:
    _, drive_service = get_services()

    drive_ids: set[str] = set()
    for tracker in DRIVE_TRACKERS:
        payload = _load_json(tracker)
        for did in _iter_drive_ids(payload):
            drive_ids.add(did)

    deleted = 0
    failed = 0

    for file_id in sorted(drive_ids):
        try:
            drive_service.files().delete(fileId=file_id).execute()
            deleted += 1
        except Exception as exc:
            if _status_code(exc) in (404, 410):
                deleted += 1
            else:
                failed += 1

    return {"deleted": deleted, "failed": failed}


def _clear_local_google_state() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    to_clear = [
        CLASSROOM_COURSES_FILE,
        CLASSROOM_SYNC_FILE,
        *DRIVE_TRACKERS,
    ]
    for path in to_clear:
        atomic_json_dump({}, path)


def main() -> None:
    print("[Purge] Google data cleanup started")

    classroom = _purge_classroom()
    print(
        "[Purge] Classroom: "
        f"deleted={classroom['deleted']} "
        f"archived={classroom['archived']} "
        f"failed={classroom['failed']}"
    )
    print(
        "[Purge] Classroom content: "
        f"coursework_deleted={classroom['coursework_deleted']} "
        f"coursework_failed={classroom['coursework_failed']} "
        f"ann_deleted={classroom['ann_deleted']} "
        f"ann_failed={classroom['ann_failed']}"
    )

    calendar = _purge_calendar()
    print(
        "[Purge] Calendar events: "
        f"deleted={calendar['deleted']} failed={calendar['failed']}"
    )

    drive = _purge_drive()
    print(
        "[Purge] Drive files: "
        f"deleted={drive['deleted']} failed={drive['failed']}"
    )

    _clear_local_google_state()
    print("[Purge] Local Google state trackers cleared")
    print("[Purge] Completed")


if __name__ == "__main__":
    main()
