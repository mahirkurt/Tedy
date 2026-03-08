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

TOKEN_FILE = os.path.join(PROJECT_ROOT, "token_huriye.json")
DATA_FILE = os.path.join(PROJECT_ROOT, "output", "scraped_data.json")
COURSES_FILE = os.path.join(PROJECT_ROOT, "output", "classroom_courses.json")
SYNC_STATE_FILE = os.path.join(PROJECT_ROOT, "output", "classroom_sync.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

STUDENT_EMAIL = "isikkurtx@gmail.com"
COURSE_SECTION = "TED Rönesans 2025-26"
GENERAL_COURSE = "TED Genel"

# Only create/sync these courses (others are ignored)
ALLOWED_COURSES = {
    "İngilizce", "Türkçe",
    "TED Genel", "Sosyal Bilgiler", "Matematik",
    "Fransızca", "Fen Bilimleri", "Din Kültürü",
    "Bilişim", "Ahlak ve Yurttaşlık",
}


def compute_hash(item):
    """Compute a short hash of an item for change detection."""
    if isinstance(item, str):
        raw = item
    else:
        raw = json.dumps(item, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def load_sync_state(path=None):
    """Load sync state from JSON file. Returns empty dict if missing or corrupted."""
    path = path or SYNC_STATE_FILE
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"  [WARN] Corrupted sync state: {path} — starting fresh")
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
        try:
            with open(COURSES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"  [WARN] Corrupted courses mapping: {COURSES_FILE} — starting fresh")
    return {}


def _save_courses_mapping(mapping):
    """Save course name -> id mapping atomically."""
    atomic_json_dump(mapping, COURSES_FILE)


def ensure_courses(service, ders_listesi):
    """Ensure a Classroom course exists for each ders + TED Genel.

    Returns dict: {normalized_name: course_id}
    """
    existing = {}
    for state in ["ACTIVE", "PROVISIONED"]:
        result = _api_call_with_retry(
            lambda s=state: service.courses().list(
                courseStates=[s],
            ).execute()
        ) or {}
        for c in result.get("courses", []):
            if c.get("section") == COURSE_SECTION:
                existing[c["name"]] = c["id"]

    all_courses = sorted(
        (set(ders_listesi) | {GENERAL_COURSE}) & ALLOWED_COURSES
    )
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


def _format_iso_date(iso_str):
    """Format ISO 8601 date string to human-readable Turkish format.

    '2026-02-16T16:00:00Z' -> '16.02.2026 16:00'
    """
    try:
        s = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt.strftime("%d.%m.%Y %H:%M")
    except (ValueError, AttributeError):
        return iso_str


def _resolve_course_id(courses, ders_adi):
    """Map a course name to its Classroom course ID, falling back to TED Genel."""
    normalized = normalize_course(ders_adi)
    return courses.get(normalized, courses.get(GENERAL_COURSE))


def sync_odevler(service, courses, data, state, drive_uploads=None):
    """Sync homework to Classroom as courseWork (ASSIGNMENT).

    Args:
        drive_uploads: Dict mapping attachment URLs to Drive file info
            {id, link, ders}. When present, Drive links are preferred
            over original portal URLs in courseWork materials.

    Returns dict: {added, updated, skipped, errors}
    """
    drive_uploads = drive_uploads or {}
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

        # Distinguish İngilizce sections by teacher
        if "Literature" in ders:
            baslik = f"[Literature - Ms. Gözde] {baslik}"
        elif "Language" in ders or ders.strip() == "İngilizce":
            baslik = f"[Language - Ms. Julie] {baslik}"

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

        materials = []
        attachments = row.get("detail", {}).get("attachments", [])
        for att in attachments:
            url = att.get("url", "")
            name = att.get("name", "Ek")
            drive_info = drive_uploads.get(url)
            if drive_info and drive_info.get("link"):
                materials.append({
                    "link": {"url": drive_info["link"], "title": f"\U0001f4c1 {name}"}
                })
            elif url:
                materials.append({
                    "link": {"url": url, "title": name}
                })
        if materials:
            body["materials"] = materials

        if existing:
            cw_id = existing["classroom_id"]
            # Classroom API rejects past due dates on update
            update_fields = "title,description"
            if due_date:
                from datetime import date
                d = date(due_date["year"], due_date["month"], due_date["day"])
                if d >= date.today():
                    update_fields += ",dueDate,dueTime"
                else:
                    body.pop("dueDate", None)
                    body.pop("dueTime", None)
            updated = _api_call_with_retry(
                lambda cid=course_id, cwid=cw_id, b=body, uf=update_fields: (
                    service.courses().courseWork().patch(
                        courseId=cid, id=cwid,
                        updateMask=uf,
                        body=b,
                    ).execute()
                )
            )
            if updated:
                state[dedup_key] = {"classroom_id": cw_id, "last_hash": current_hash}
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
                state[dedup_key] = {"classroom_id": created["id"], "last_hash": current_hash}
                result["added"] += 1
            else:
                result["errors"] += 1

    print(f"  Ödevler: +{result['added']} ~{result['updated']} "
          f"={result['skipped']} !{result['errors']}")
    return result


def sync_ders_icerikleri(service, courses, data, state):
    """Sync course content as announcements (per-course).

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
            course_id = courses.get(
                normalized, courses.get(GENERAL_COURSE),
            )
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

        ann_text = f"📚 {title}\n\n{text[:1950]}"

        if existing:
            ann_id = existing["classroom_id"]
            updated = _api_call_with_retry(
                lambda cid=course_id, aid=ann_id, t=ann_text: (
                    service.courses().announcements().patch(
                        courseId=cid, id=aid,
                        updateMask="text",
                        body={"text": t, "state": "PUBLISHED"},
                    ).execute()
                )
            )
            if updated:
                state[dedup_key] = {
                    "classroom_id": ann_id,
                    "last_hash": current_hash,
                }
                result["updated"] += 1
            else:
                result["errors"] += 1
        else:
            created = _api_call_with_retry(
                lambda cid=course_id, t=ann_text: (
                    service.courses().announcements().create(
                        courseId=cid,
                        body={"text": t, "state": "PUBLISHED"},
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
            lambda cid=course_id, aid=ann_id, b=body: (
                service.courses().announcements().patch(
                    courseId=cid, id=aid,
                    updateMask="text",
                    body=b,
                ).execute()
            )
        )
        if updated:
            state[dedup_key] = {"classroom_id": ann_id, "last_hash": current_hash}
            result["updated"] += 1
        else:
            result["errors"] += 1
    else:
        created = _api_call_with_retry(
            lambda cid=course_id, b=body: (
                service.courses().announcements().create(
                    courseId=cid, body=b,
                ).execute()
            )
        )
        if created:
            state[dedup_key] = {"classroom_id": created["id"], "last_hash": current_hash}
            result["added"] += 1
        else:
            result["errors"] += 1


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

    # 2. Calendar events -> TED Genel
    for ev in data.get("takvim", []):
        title = ev.get("title", "")
        start = ev.get("start", "")
        start_display = _format_iso_date(start) if start else ""
        text = f"Takvim: {title}\nTarih: {start_display}"
        _upsert_announcement(service, genel_id, text, state, result)

    # 3. Team activities -> TED Genel
    rows = (data.get("takim_calismalari", {}).get("activities", {}).get("rows", []))
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
    ogep_rows = (data.get("ogep", {}).get("sessions", {}).get("rows", []))
    for row in ogep_rows:
        name = row.get("ÖGEP (Öğrenci Gelişim Programı)", "")
        baslangic = row.get("Çalışma Başlangıç", "")
        text = f"ÖGEP: {name}\nTarih: {baslangic}"
        _upsert_announcement(service, genel_id, text, state, result)

    print(f"  Duyurular: +{result['added']} ~{result['updated']} "
          f"={result['skipped']} !{result['errors']}")
    return result


def _load_upload_tracker(filename):
    """Load an upload tracker JSON file from output directory."""
    path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"  [WARN] Corrupted tracker: {path} — treating as empty")
    return {}


def _ensure_materials_accessible(drive_ids):
    """Share Drive files with the Classroom teacher account.

    Uses primary account (token.json) to grant reader access to the
    teacher so Classroom can attach them as materials.
    Idempotent: silently skips already-shared files.
    """
    token_path = os.path.join(PROJECT_ROOT, "token.json")
    if not os.path.exists(token_path) or not drive_ids:
        return

    creds = Credentials.from_authorized_user_file(token_path)
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    drive = build("drive", "v3", credentials=creds)

    teacher_email = "huriye.murzoglu@gmail.com"
    for file_id in drive_ids:
        try:
            drive.permissions().create(
                fileId=file_id,
                body={
                    "type": "user",
                    "role": "reader",
                    "emailAddress": teacher_email,
                },
                sendNotificationEmail=False,
            ).execute()
        except Exception:
            pass  # Already shared or other non-critical error


def _upsert_announcement_with_materials(
    service, course_id, text, materials, dedup_key, current_hash, state, result,
):
    """Create or update an announcement with optional materials.

    Materials are only included on create (Classroom API doesn't support
    materials in announcements.patch updateMask).
    """
    if not course_id or not text.strip():
        result["errors"] += 1
        return

    existing = state.get(dedup_key)
    if existing and existing["last_hash"] == current_hash:
        result["skipped"] += 1
        return

    if existing:
        ann_id = existing["classroom_id"]
        updated = _api_call_with_retry(
            lambda cid=course_id, aid=ann_id, t=text[:2000]: (
                service.courses().announcements().patch(
                    courseId=cid, id=aid,
                    updateMask="text",
                    body={"text": t, "state": "PUBLISHED"},
                ).execute()
            )
        )
        if updated:
            state[dedup_key] = {"classroom_id": ann_id, "last_hash": current_hash}
            result["updated"] += 1
        else:
            result["errors"] += 1
    else:
        body = {"text": text[:2000], "state": "PUBLISHED"}
        if materials:
            body["materials"] = materials[:20]
        created = _api_call_with_retry(
            lambda cid=course_id, b=body: (
                service.courses().announcements().create(
                    courseId=cid, body=b,
                ).execute()
            )
        )
        if created:
            state[dedup_key] = {"classroom_id": created["id"], "last_hash": current_hash}
            result["added"] += 1
        else:
            result["errors"] += 1


def sync_eba_textbooks(service, courses, state):
    """Sync EBA textbook PDFs as announcements with Drive links (per course).

    Reads output/eba_textbooks_uploaded.json and creates one announcement
    per course listing all textbook PDFs with Drive links.

    Returns dict: {added, updated, skipped, errors}
    """
    result = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
    uploaded = _load_upload_tracker("eba_textbooks_uploaded.json")
    if not uploaded:
        return result

    by_course = {}
    for book_id, info in uploaded.items():
        normalized = normalize_course(info.get("course", ""))
        by_course.setdefault(normalized, []).append(info)

    all_drive_ids = [
        info["driveId"] for info in uploaded.values() if info.get("driveId")
    ]
    _ensure_materials_accessible(all_drive_ids)

    for ders, books in sorted(by_course.items()):
        course_id = courses.get(ders, courses.get(GENERAL_COURSE))
        if not course_id:
            result["errors"] += 1
            continue

        dedup_key = f"eba:{course_id}:textbooks"
        titles = sorted(b["title"] for b in books)
        current_hash = compute_hash(titles)

        lines = [f"\U0001f4d6 {ders} Ders Kitapları\n"]
        materials = []
        for b in sorted(books, key=lambda x: x["title"]):
            lines.append(f"\u2022 {b['title']}")
            if b.get("link"):
                materials.append({
                    "link": {"url": b["link"], "title": f"\U0001f4d6 {b['title']}"}
                })

        _upsert_announcement_with_materials(
            service, course_id, "\n".join(lines), materials,
            dedup_key, current_hash, state, result,
        )

    print(f"  EBA kitaplar: +{result['added']} ~{result['updated']} "
          f"={result['skipped']} !{result['errors']}")
    return result


def sync_mebi_videos(service, courses, state):
    """Sync MEBI videos as announcements with Drive links (per unit).

    Reads output/mebi_videos_uploaded.json and creates one announcement
    per course+unit listing all topic videos with Drive links.

    Returns dict: {added, updated, skipped, errors}
    """
    result = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
    uploaded = _load_upload_tracker("mebi_videos_uploaded.json")
    if not uploaded:
        return result

    all_drive_ids = [
        info["driveId"] for info in uploaded.values() if info.get("driveId")
    ]
    _ensure_materials_accessible(all_drive_ids)

    by_unit = {}
    for uuid, info in uploaded.items():
        normalized = normalize_course(info.get("course", ""))
        unit = info.get("unit", "")
        key = (normalized, unit)
        by_unit.setdefault(key, []).append(info)

    for (ders, unit), videos in sorted(by_unit.items()):
        course_id = courses.get(ders, courses.get(GENERAL_COURSE))
        if not course_id:
            result["errors"] += 1
            continue

        dedup_key = f"mebi:{course_id}:{unit}"
        topics = sorted(v.get("topic", "") for v in videos)
        current_hash = compute_hash(topics)

        lines = [f"\U0001f3ac {ders} - {unit}\n"]
        materials = []
        for v in sorted(videos, key=lambda x: x.get("topic", "")):
            topic = v.get("topic", "Video")
            lines.append(f"\u2022 {topic}")
            if v.get("link"):
                materials.append({
                    "link": {"url": v["link"], "title": f"\U0001f3ac {topic}"}
                })

        _upsert_announcement_with_materials(
            service, course_id, "\n".join(lines), materials,
            dedup_key, current_hash, state, result,
        )

    print(f"  MEBI videolar: +{result['added']} ~{result['updated']} "
          f"={result['skipped']} !{result['errors']}")
    return result


def sync_sebitv(service, courses, state):
    """Sync SEBİTV resources as announcements with Drive links (per unit).

    Reads output/sebitv_uploaded.json (and sebitv_interactive_uploaded.json
    if present) and creates one announcement per course+unit listing all
    resources with Drive links.

    Returns dict: {added, updated, skipped, errors}
    """
    result = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
    uploaded = _load_upload_tracker("sebitv_uploaded.json")
    interactive = _load_upload_tracker("sebitv_interactive_uploaded.json")
    if not uploaded and not interactive:
        return result

    combined = {**uploaded, **interactive}
    all_drive_ids = [
        info["driveId"] for info in combined.values() if info.get("driveId")
    ]
    _ensure_materials_accessible(all_drive_ids)

    by_unit = {}
    for rid, info in combined.items():
        normalized = normalize_course(info.get("course", ""))
        unit = info.get("unit", "")
        key = (normalized, unit)
        by_unit.setdefault(key, []).append(info)

    for (ders, unit), resources in sorted(by_unit.items()):
        course_id = courses.get(ders, courses.get(GENERAL_COURSE))
        if not course_id:
            result["errors"] += 1
            continue

        dedup_key = f"sebitv:{course_id}:{unit}"
        titles = sorted(r.get("title", "") for r in resources)
        current_hash = compute_hash(titles)

        lines = [f"\U0001f393 {ders} - {unit}\n"]
        materials = []
        for r in sorted(resources, key=lambda x: x.get("title", "")):
            title = r.get("title", "Kaynak")
            rtype = r.get("type", "")
            suffix = f" ({rtype})" if rtype else ""
            lines.append(f"\u2022 {title}{suffix}")
            if r.get("link"):
                materials.append({
                    "link": {"url": r["link"], "title": f"\U0001f393 {title}"}
                })
            if r.get("qbankLink"):
                materials.append({
                    "link": {"url": r["qbankLink"], "title": f"\u2753 {title} - Soru Bankası"}
                })

        _upsert_announcement_with_materials(
            service, course_id, "\n".join(lines), materials,
            dedup_key, current_hash, state, result,
        )

    print(f"  SEBİTV kaynaklar: +{result['added']} ~{result['updated']} "
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


def sync_englishcentral(service, courses, state):
    """Sync English Central progress as an announcement in İngilizce course.

    Reads output/englishcentral_progress.json and creates/updates one
    announcement with completion status and direct video links.

    Returns dict: {added, updated, skipped, errors}
    """
    result = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
    progress = _load_upload_tracker("englishcentral_progress.json")
    if not progress or not progress.get("videos"):
        print("  [EC] No English Central data found")
        return result

    course_id = courses.get("İngilizce")
    if not course_id:
        print("  [EC] İngilizce course not found")
        return result

    videos = progress["videos"]
    total = progress.get("total_videos", len(videos))
    completed = progress.get("completed_videos",
                             sum(1 for v in videos if v.get("completed")))
    scraped_at = progress.get("scraped_at", "")
    date_str = scraped_at[:10] if scraped_at else ""

    # Build announcement text
    lines = [f"English Central Odev Durumu ({date_str})", ""]
    lines.append(f"{completed}/{total} video tamamlandi")
    lines.append("")

    incomplete = [v for v in videos if not v.get("completed")]
    done = [v for v in videos if v.get("completed")]

    if incomplete:
        lines.append("Tamamlanmamis videolar:")
        for v in incomplete:
            status = "baslandi" if v.get("started") else "baslanmadi"
            lines.append(f"  * {v['title']} ({status})")
            lines.append(f"    {v['url']}")
        lines.append("")

    if done:
        lines.append(f"Tamamlanan videolar ({len(done)}):")
        for v in done:
            lines.append(f"  * {v['title']}")
        lines.append("")

    text = "\n".join(lines)
    dedup_key = f"ec:{course_id}:progress"
    current_hash = compute_hash(text)

    _upsert_announcement_with_materials(
        service, course_id, text, [], dedup_key,
        current_hash, state, result,
    )

    print(f"  [EC] English Central: "
          f"added={result['added']} updated={result['updated']} "
          f"skipped={result['skipped']}")
    return result


def sync_achieve3000(service, courses, state):
    """Sync Achieve3000 progress as an announcement in Literature course.

    Reads output/achieve3000_progress.json and creates/updates one
    announcement with teacher-assigned lesson completion status.

    Returns dict: {added, updated, skipped, errors}
    """
    result = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
    progress = _load_upload_tracker("achieve3000_progress.json")
    if not progress or not progress.get("lessons"):
        print("  [A3K] No Achieve3000 data found")
        return result

    course_id = courses.get("İngilizce Literature")
    if not course_id:
        print("  [A3K] İngilizce Literature course not found")
        return result

    lessons = progress["lessons"]
    total = progress.get("teacher_assigned_count", len(lessons))
    completed = progress.get("teacher_assigned_completed",
                             sum(1 for l in lessons if l.get("completed")))
    scraped_at = progress.get("scraped_at", "")
    date_str = scraped_at[:10] if scraped_at else ""

    # Dashboard stats
    stats = progress.get("dashboard_stats", {})
    stats_str = ""
    if stats:
        stats_str = (f"Genel: {stats.get('completed', 0)}/{stats.get('target', 0)} "
                     f"aktivite, ilk deneme: %{stats.get('firstTryScore', 0)}")

    # Build announcement text
    lines = [f"Achieve3000 Odev Durumu ({date_str})", ""]
    lines.append(f"{completed}/{total} ders tamamlandi")
    if stats_str:
        lines.append(stats_str)
    lines.append("")

    incomplete = [l for l in lessons if not l.get("completed")]
    done = [l for l in lessons if l.get("completed")]

    if incomplete:
        lines.append("Tamamlanmamis dersler:")
        for l in incomplete:
            steps = l.get("completed_steps", 0)
            total_s = l.get("total_steps", 5)
            if steps > 0:
                status = f"{steps}/{total_s} adim"
            else:
                status = "baslanmadi"
            lines.append(f"  * {l['title']} ({status})")
            lines.append(f"    {l.get('url', '')}")
        lines.append("")

    if done:
        lines.append(f"Tamamlanan dersler ({len(done)}):")
        for l in done:
            score_str = f" (%{l['score']})" if l.get("score") is not None else ""
            lines.append(f"  * {l['title']}{score_str}")
        lines.append("")

    text = "\n".join(lines)
    dedup_key = f"a3k:{course_id}:progress"
    current_hash = compute_hash(text)

    _upsert_announcement_with_materials(
        service, course_id, text, [], dedup_key,
        current_hash, state, result,
    )

    print(f"  [A3K] Achieve3000: "
          f"added={result['added']} updated={result['updated']} "
          f"skipped={result['skipped']}")
    return result


def sync_sebit_homework(service, courses, state):
    """Sync SEBİT homework progress as per-course announcements.

    Reads output/sebit_homework.json and creates/updates one announcement
    per course with homework completion status.

    Returns dict: {added, updated, skipped, errors}
    """
    result = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
    progress = _load_upload_tracker("sebit_homework.json")
    if not progress or not progress.get("homework"):
        print("  [SEBIT-HW] No SEBiT homework data found")
        return result

    by_course = {}
    for hw in progress["homework"]:
        course = hw.get("course", "")
        by_course.setdefault(course, []).append(hw)

    scraped_at = progress.get("scraped_at", "")
    date_str = scraped_at[:10] if scraped_at else ""

    for course_name, items in by_course.items():
        norm = normalize_course(course_name)
        course_id = courses.get(norm)
        if not course_id:
            continue

        completed = sum(1 for h in items if h.get("completed"))
        total = len(items)

        lines = [f"SEBiT Dijital Odev Durumu ({date_str})", ""]
        lines.append(f"{completed}/{total} odev tamamlandi")
        lines.append("")

        incomplete = [h for h in items if not h.get("completed")]
        done = [h for h in items if h.get("completed")]

        if incomplete:
            lines.append("Tamamlanmamis odevler:")
            for h in incomplete:
                p = h.get("progress", 0)
                if p > 0:
                    status_str = f"%{p:.0f}"
                else:
                    status_str = "baslanmadi"
                expired = ""
                if h.get("state") == 2:
                    expired = " [Suresi Doldu]"
                lines.append(f"  * {h['title']} ({status_str}){expired}")
                lines.append(f"    Ogretmen: {h.get('teacher', '')}")
                lines.append(f"    Tarih: {h.get('start_date', '')} - "
                             f"{h.get('end_date', '')}")
            lines.append("")

        if done:
            lines.append(f"Tamamlanan odevler ({len(done)}):")
            for h in done:
                lines.append(f"  * {h['title']}")
            lines.append("")

        text = "\n".join(lines)
        dedup_key = f"sebit_hw:{course_id}:progress"
        current_hash = compute_hash(text)

        _upsert_announcement_with_materials(
            service, course_id, text, [], dedup_key,
            current_hash, state, result,
        )

    print(f"  [SEBIT-HW] SEBiT Homework: "
          f"added={result['added']} updated={result['updated']} "
          f"skipped={result['skipped']}")
    return result


def main(scraped_data=None, token_file=None, reset_courses=False, drive_uploads=None):
    """Main entry point for Classroom sync.

    Args:
        scraped_data: Pre-loaded data dict. If None, reads from DATA_FILE.
        token_file: OAuth token file path.
        reset_courses: If True, archive and recreate all courses.
        drive_uploads: Dict mapping attachment URLs to Drive file info
            {id, link, ders}. Passed to sync_odevler for Drive materials.
    """
    print("\n--- Classroom Sync ---")

    if scraped_data is None:
        if not os.path.exists(DATA_FILE):
            print("  [SKIP] No scraped data found")
            return
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            scraped_data = json.load(f)

    service = get_classroom_service(token_file)

    if reset_courses:
        print("  Resetting courses...")
        mapping = _load_courses_mapping()
        for name, cid in mapping.items():
            try:
                _api_call_with_retry(
                    lambda c=cid: service.courses().delete(
                        id=c,
                    ).execute()
                )
                print(f"    Deleted: {name}")
            except Exception:
                print(f"    [WARN] Could not delete: {name}")
        _save_courses_mapping({})

    ders_listesi = _extract_course_names(scraped_data)
    courses = ensure_courses(service, ders_listesi)

    state = load_sync_state()

    sync_errors = []
    sync_functions = [
        ("odevler", lambda: sync_odevler(
            service, courses, scraped_data, state,
            drive_uploads=drive_uploads)),
        ("ders_icerikleri", lambda: sync_ders_icerikleri(
            service, courses, scraped_data, state)),
        ("notlar", lambda: sync_notlar(
            service, courses, scraped_data, state)),
        ("duyurular", lambda: sync_duyurular(
            service, courses, scraped_data, state)),
        ("eba_textbooks", lambda: sync_eba_textbooks(
            service, courses, state)),
        ("mebi_videos", lambda: sync_mebi_videos(
            service, courses, state)),
        ("sebitv", lambda: sync_sebitv(
            service, courses, state)),
        ("englishcentral", lambda: sync_englishcentral(
            service, courses, state)),
        ("achieve3000", lambda: sync_achieve3000(
            service, courses, state)),
        ("sebit_homework", lambda: sync_sebit_homework(
            service, courses, state)),
    ]

    for name, fn in sync_functions:
        try:
            fn()
        except Exception as e:
            sync_errors.append(f"{name}: {e}")
            print(f"  [ERROR] {name} sync failed: {e}")

    save_sync_state(state)
    print("  Classroom sync complete.")
    return sync_errors


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sync TED data to Google Classroom")
    parser.add_argument("--reset-courses", action="store_true",
                        help="Archive and recreate all courses")
    parser.add_argument("--token", default=None,
                        help="Path to OAuth token file")
    args = parser.parse_args()
    main(token_file=args.token, reset_courses=args.reset_courses)
