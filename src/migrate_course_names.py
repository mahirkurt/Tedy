#!/usr/bin/env python3
"""One-time migration: rename old course names to canonical forms in Google Workspace.

Updates:
- Calendar event summaries
- Task titles
- Drive folder names
- Sheets course names (handled by next sync_grades_to_sheets run)

Safe to run multiple times (idempotent).
"""
import os
import re
import sys

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from src.sync_to_google import (
    get_services, normalize_course, _ALIAS_LOOKUP,
    get_or_create_calendar, get_or_create_task_list,
    COLORS,
)


def migrate_calendar(cal, cal_id):
    """Rename non-canonical course names in calendar event summaries."""
    print("\n[1/3] Calendar events")

    events = []
    page_token = None
    while True:
        result = cal.events().list(
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

    updated = 0
    skipped = 0

    for ev in events:
        summary = ev.get("summary", "")
        new_summary = _normalize_summary(summary)

        if new_summary != summary:
            ev["summary"] = new_summary
            cal.events().update(
                calendarId=cal_id, eventId=ev["id"], body=ev
            ).execute()
            updated += 1
            print(f"  ✓ {summary} → {new_summary}")
        else:
            skipped += 1

    print(f"  Updated: {updated}, Already OK: {skipped}")


def _normalize_summary(summary):
    """Normalize course name within a calendar event summary.

    Handles formats:
    - "Matematik"  (ders programi — bare course name)
    - "📝 Ödev: Başlık (Ders Adı)"  (odevlerim)
    """
    # Ödev format: "📝 Ödev: Başlık (Ders)"
    m = re.match(r"^(📝 Ödev: .+)\(([^)]+)\)\s*$", summary)
    if m:
        prefix, course = m.group(1), m.group(2)
        canonical = normalize_course(course)
        if canonical != course:
            return f"{prefix}({canonical})"
        return summary

    # Ders programi: bare course name (no emoji prefix, no special format)
    # Only rename if the result is a known canonical name — prevents stripping
    # meaningful parenthesized content from takvim events like exam announcements.
    if not any(summary.startswith(p) for p in ("📝", "📢", "🎯", "📖", "📊", "ÖGEP:")):
        canonical = normalize_course(summary)
        if canonical != summary and canonical in _ALIAS_LOOKUP:
            return canonical

    return summary


def migrate_tasks(tasks_svc, task_list_id):
    """Rename non-canonical course names in task titles."""
    print("\n[2/3] Tasks")

    all_tasks = []
    page_token = None
    while True:
        result = tasks_svc.tasks().list(
            tasklist=task_list_id,
            maxResults=100,
            pageToken=page_token,
            showCompleted=True,
            showHidden=True,
        ).execute()
        all_tasks.extend(result.get("items", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break

    updated = 0
    skipped = 0

    for t in all_tasks:
        title = t.get("title", "")
        new_title = _normalize_task_title(title)

        if new_title != title:
            t["title"] = new_title
            tasks_svc.tasks().update(
                tasklist=task_list_id, task=t["id"], body=t
            ).execute()
            updated += 1
            print(f"  ✓ {title} → {new_title}")
        else:
            skipped += 1

    print(f"  Updated: {updated}, Already OK: {skipped}")


def _normalize_task_title(title):
    """Normalize course name within a task title.

    Handles formats:
    - "[Ders Adı] Ödev Başlığı"  (odevlerim)
    - "📖 Ders Adı - Haftalık İçerik"  (ders icerikleri)
    - "📊 Notlar: Ders Adı"  (gelisim raporu)
    """
    # [Course] format
    m = re.match(r"^\[([^\]]+)\](.*)$", title)
    if m:
        course, rest = m.group(1), m.group(2)
        canonical = normalize_course(course)
        if canonical != course:
            return f"[{canonical}]{rest}"
        return title

    # 📖 Course - Haftalık İçerik
    m = re.match(r"^(📖\s*)(.+?)(\s*-\s*Haftalık İçerik.*)$", title)
    if m:
        prefix, course, suffix = m.group(1), m.group(2), m.group(3)
        canonical = normalize_course(course)
        if canonical != course:
            return f"{prefix}{canonical}{suffix}"
        return title

    # 📊 Notlar: Course
    m = re.match(r"^(📊 Notlar:\s*)(.+)$", title)
    if m:
        prefix, course = m.group(1), m.group(2)
        canonical = normalize_course(course)
        if canonical != course:
            return f"{prefix}{canonical}"
        return title

    return title


def migrate_drive_folders(drive, parent_folder_name="Ödevler"):
    """Rename non-canonical Drive folder names under Ödevler."""
    print("\n[3/3] Drive folders")

    # Find parent folder
    result = drive.files().list(
        q=(f"name='{parent_folder_name}' and "
           f"mimeType='application/vnd.google-apps.folder' and "
           f"trashed=false"),
        spaces="drive",
        fields="files(id, name)",
    ).execute()
    folders = result.get("files", [])
    if not folders:
        print(f"  '{parent_folder_name}' folder not found, skipping")
        return

    root_id = folders[0]["id"]

    # List subfolders
    result = drive.files().list(
        q=(f"'{root_id}' in parents and "
           f"mimeType='application/vnd.google-apps.folder' and "
           f"trashed=false"),
        spaces="drive",
        fields="files(id, name)",
    ).execute()
    subfolders = result.get("files", [])

    updated = 0
    merged = 0
    skipped = 0

    # Build map of existing canonical folders
    canonical_folders = {}  # canonical_name -> folder_id
    for f in subfolders:
        canonical = normalize_course(f["name"])
        if canonical == f["name"]:
            canonical_folders[canonical] = f["id"]

    for f in subfolders:
        name = f["name"]
        canonical = normalize_course(name)

        if canonical == name:
            skipped += 1
            continue

        if canonical in canonical_folders:
            # Target folder exists — move files, then trash old folder
            target_id = canonical_folders[canonical]
            _move_folder_contents(drive, f["id"], target_id)
            drive.files().update(
                fileId=f["id"], body={"trashed": True}
            ).execute()
            merged += 1
            print(f"  ✓ {name} → merged into {canonical}")
        else:
            # Rename folder
            drive.files().update(
                fileId=f["id"], body={"name": canonical}
            ).execute()
            canonical_folders[canonical] = f["id"]
            updated += 1
            print(f"  ✓ {name} → {canonical}")

    print(f"  Renamed: {updated}, Merged: {merged}, Already OK: {skipped}")


def _move_folder_contents(drive, source_id, target_id):
    """Move all files from source folder to target folder."""
    result = drive.files().list(
        q=f"'{source_id}' in parents and trashed=false",
        spaces="drive",
        fields="files(id, name, parents)",
    ).execute()

    for f in result.get("files", []):
        drive.files().update(
            fileId=f["id"],
            addParents=target_id,
            removeParents=source_id,
            fields="id, parents",
        ).execute()


def main():
    print("=" * 60)
    print("Course Name Migration")
    print("=" * 60)

    cal, tasks_svc, sheets, drive = get_services()

    cal_id = get_or_create_calendar(cal, "TED Rönesans")
    task_list_id = get_or_create_task_list(tasks_svc, "TED Ödevler")

    migrate_calendar(cal, cal_id)
    migrate_tasks(tasks_svc, task_list_id)
    migrate_drive_folders(drive)

    print("\n" + "=" * 60)
    print("Migration complete!")
    print("Sheets will be updated on next sync_to_google run.")
    print("=" * 60)


if __name__ == "__main__":
    main()
