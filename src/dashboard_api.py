"""Dashboard API server — serves TED data as JSON endpoints."""
import base64
import hashlib
import json
import os
import re
import secrets
import sys
from datetime import datetime, timedelta
from functools import wraps

import requests as http_requests
from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from src.env_loader import load_env
from src.json_utils import atomic_json_dump
from src.sync_to_google import normalize_course

load_env()

app = Flask(__name__)
app.secret_key = os.environ.get("DASHBOARD_SECRET_KEY", secrets.token_hex(32))
CORS(app, supports_credentials=True)

TEST_AUTH_BYPASS = os.environ.get("TEST_AUTH_BYPASS") == "1"

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
DIST_DIR = os.path.join(PROJECT_ROOT, "dashboard-dist")
PHOTO_HOMEWORK_FILE = os.path.join(OUTPUT_DIR, "photo_homework.json")
PRIVATE_LESSON_FILE = os.path.join(OUTPUT_DIR, "private_lessons.json")
STUDENT_DONE_FILE = os.path.join(OUTPUT_DIR, "homework_student_done.json")
MAX_PHOTO_SIZE_BYTES = 12 * 1024 * 1024
GEMINI_VISION_MODEL = os.environ.get("HOMEWORK_VISION_MODEL", "gemini-2.5-flash")

GOOGLE_CLIENT_ID = "343043757928-mivqip09orvrf73m7kj9b0atohgin2ho.apps.googleusercontent.com"

ALLOWED_EMAILS = {
    "isikkurtx@gmail.com",
    "drmahirkurt@gmail.com",
    "ozlem.murzoglu@gmail.com",
    "huriye.murzoglu@gmail.com",
}

DAY_NAMES = {
    0: "Pazartesi", 1: "Salı", 2: "Çarşamba",
    3: "Perşembe", 4: "Cuma", 5: "Cumartesi", 6: "Pazar"
}


# --- Auth ---

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if TEST_AUTH_BYPASS:
            return f(*args, **kwargs)
        if not session.get("user_email"):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json()
    token = data.get("credential") if data else None
    if not token:
        return jsonify({"error": "No credential provided"}), 400
    try:
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
        email = idinfo.get("email", "").lower()
        if email not in ALLOWED_EMAILS:
            return jsonify({"error": "Bu hesapla giris yapilamaz"}), 403
        session["user_email"] = email
        session["user_name"] = idinfo.get("name", "")
        session["user_picture"] = idinfo.get("picture", "")
        return jsonify({
            "email": email,
            "name": session["user_name"],
            "picture": session["user_picture"],
        })
    except ValueError as e:
        return jsonify({"error": f"Invalid token: {e}"}), 401


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/auth/me")
def auth_me():
    if TEST_AUTH_BYPASS:
        return jsonify({
            "email": "test@tedy.online",
            "name": "Test User",
            "picture": "",
        })
    if session.get("user_email"):
        return jsonify({
            "email": session["user_email"],
            "name": session.get("user_name", ""),
            "picture": session.get("user_picture", ""),
        })
    return jsonify({"error": "Not authenticated"}), 401


# --- Data helpers ---

def _load_json(filename):
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _scraped():
    return _load_json("scraped_data.json")


def _parse_iso_datetime(value):
    s = str(value or "").strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _latest_iso_timestamp(*values):
    best_raw = ""
    best_dt = None
    for raw in values:
        s = str(raw or "").strip()
        if not s:
            continue
        dt = _parse_iso_datetime(s)
        if dt is None:
            if not best_raw:
                best_raw = s
            continue
        if best_dt is None or dt > best_dt:
            best_dt = dt
            best_raw = s
    return best_raw


_WEEKDAY_TO_INDEX = {
    "pazartesi": 0,
    "salı": 1,
    "sali": 1,
    "çarşamba": 2,
    "carsamba": 2,
    "perşembe": 3,
    "persembe": 3,
    "cuma": 4,
    "cumartesi": 5,
    "pazar": 6,
}


def _load_private_lessons():
    data = _load_json("private_lessons.json")
    if not isinstance(data, dict):
        return []
    lessons = data.get("lessons", [])
    if not isinstance(lessons, list):
        return []
    return [x for x in lessons if isinstance(x, dict)]


def _save_private_lessons(lessons):
    payload = {"updated_at": datetime.now().isoformat(), "lessons": lessons}
    atomic_json_dump(payload, PRIVATE_LESSON_FILE)


def _find_private_lesson(lesson_id):
    for lesson in _load_private_lessons():
        if str(lesson.get("id", "")) == str(lesson_id):
            return lesson
    return None


def _parse_hhmm(value):
    s = str(value or "").strip()
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", s)
    if not m:
        return None
    h, mins = int(m.group(1)), int(m.group(2))
    if h < 0 or h > 23 or mins < 0 or mins > 59:
        return None
    return h, mins


def _coerce_bool(value, default=False):
    """Parse bool-ish values from JSON payloads safely."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    s = str(value).strip().lower()
    if s in {"true", "1", "yes", "y", "on"}:
        return True
    if s in {"false", "0", "no", "n", "off", ""}:
        return False
    return default


def _normalize_weekday_name(value):
    s = str(value or "").strip().lower()
    idx = _WEEKDAY_TO_INDEX.get(s)
    if idx is None:
        return ""
    labels = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    return labels[idx]


def _private_lessons_for_week(week_dates):
    """Expand private lesson configs into concrete events for current week."""
    events = []
    lessons = _load_private_lessons()
    if not lessons:
        return events

    monday = week_dates[0]
    friday = week_dates[4]

    for lesson in lessons:
        if not lesson.get("active", True):
            continue

        start_pair = _parse_hhmm(lesson.get("start_time"))
        end_pair = _parse_hhmm(lesson.get("end_time"))
        if not start_pair or not end_pair:
            continue
        sh, sm = start_pair
        eh, em = end_pair

        day_date = None
        if lesson.get("is_recurring", True):
            weekday_name = lesson.get("weekday", "")
            weekday_idx = _WEEKDAY_TO_INDEX.get(str(weekday_name).strip().lower())
            if weekday_idx is None:
                continue
            if weekday_idx > 4:
                # Weekly calendar UI currently shows Mon-Fri.
                continue
            day_date = week_dates[weekday_idx]
        else:
            date_str = str(lesson.get("date", "")).strip()
            if not date_str:
                continue
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            if d < monday or d > friday:
                continue
            day_date = d

        start_dt = datetime(day_date.year, day_date.month, day_date.day, sh, sm)
        end_dt = datetime(day_date.year, day_date.month, day_date.day, eh, em)
        if end_dt <= start_dt:
            end_dt = start_dt + timedelta(minutes=50)

        title = f"{lesson.get('course', 'Özel Ders')} · {lesson.get('teacher', '').strip()}"
        subtitle = (
            f"Özel Ders • {lesson.get('teacher', '').strip()}"
            if lesson.get("teacher")
            else "Özel Ders"
        )
        events.append({
            "id": _make_id("private_lesson", lesson.get("id", ""), start_dt.isoformat()),
            "type": "private_lesson",
            "title": title,
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "course": lesson.get("course", ""),
            "status": "Özel Ders",
            "subtitle": subtitle,
            "private_lesson_id": lesson.get("id", ""),
        })

    return events


def _private_lessons_for_day(day_date):
    """Expand private lessons for a specific date into simple calendar events."""
    monday = day_date - timedelta(days=day_date.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(5)]
    events = _private_lessons_for_week(week_dates)
    out = []
    for ev in events:
        try:
            d = datetime.fromisoformat(ev["start"])
        except (ValueError, KeyError):
            continue
        if d.date() != day_date:
            continue
        out.append(ev)
    return out


def _private_lessons_calendar_events(days_before=30, days_after=120):
    """Generate private lesson events in Google Calendar-like format."""
    out = []
    today = datetime.now().date()
    start_date = today - timedelta(days=days_before)
    end_date = today + timedelta(days=days_after)

    cur = start_date
    while cur <= end_date:
        day_events = _private_lessons_for_day(cur)
        for ev in day_events:
            out.append({
                "id": ev.get("id", ""),
                "title": ev.get("title", ""),
                "allDay": False,
                "start": ev.get("start", ""),
                "end": ev.get("end", ev.get("start", "")),
                "extendedProps": {
                    "kind": "private_lesson",
                    "badge": "Özel Ders",
                    "course": ev.get("course", ""),
                    "description": ev.get("subtitle", ""),
                    "private_lesson_id": ev.get("private_lesson_id", ""),
                },
            })
        cur += timedelta(days=1)
    return out


def _homework_row_key(row):
    """Build a stable identity key for a homework row."""
    course = normalize_course(str(row.get("Ders Adı", ""))).strip().lower()
    title = str(row.get("Ödev Başlığı", "")).strip().lower()
    due = _normalize_due_datetime(row.get("Ödev Son Teslim Tarihi", ""))
    return f"{course}|{title}|{due}"


def _dedupe_homework_rows(rows):
    """Deduplicate homework rows while preserving order."""
    seen = set()
    deduped = []
    for row in rows:
        key = _homework_row_key(row)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _load_photo_homework_rows():
    """Load user-added homework rows extracted from photos."""
    data = _load_json("photo_homework.json")
    if not isinstance(data, dict):
        return []
    rows = data.get("homework", [])
    if not isinstance(rows, list):
        return []
    return [r for r in rows if isinstance(r, dict)]


def _save_photo_homework_rows(rows):
    """Persist user-added homework rows."""
    payload = {
        "updated_at": datetime.now().isoformat(),
        "homework": rows,
    }
    atomic_json_dump(payload, PHOTO_HOMEWORK_FILE)


def _load_student_done_marks():
    """Load homework keys manually marked as done by student."""
    data = _load_json("homework_student_done.json")
    if not isinstance(data, dict):
        return {}
    marks = data.get("marks", {})
    if not isinstance(marks, dict):
        return {}

    cleaned = {}
    for key, value in marks.items():
        if not isinstance(key, str) or not key.strip():
            continue
        if isinstance(value, str):
            cleaned[key] = value
            continue
        if isinstance(value, dict):
            marked_at = str(value.get("marked_at", "")).strip()
            if marked_at:
                cleaned[key] = marked_at
    return cleaned


def _save_student_done_marks(marks):
    """Persist homework keys manually marked as done by student."""
    payload = {
        "updated_at": datetime.now().isoformat(),
        "marks": marks,
    }
    atomic_json_dump(payload, STUDENT_DONE_FILE)


def _normalize_homework_status_text(value):
    """Normalize status text to canonical dashboard values when possible."""
    raw = str(value or "").strip().lower()
    if raw in {"yaptı", "yapti", "tamamlandı", "tamamlandi", "done"}:
        return "Yaptı"
    if raw in {"yapmadı", "yapmadi", "missing", "incomplete"}:
        return "Yapmadı"
    if raw == "eksik":
        return "Eksik"
    if raw in {"değerlendirilmemiş", "degerlendirilmemis", "bekliyor", "pending"}:
        return "Değerlendirilmemiş"
    return str(value or "").strip()


def _is_teacher_resolved_homework_status(value):
    """Whether teacher-side status is already finalized on portal."""
    normalized = _normalize_homework_status_text(value)
    return normalized in {"Yaptı", "Yapmadı", "Eksik"}


def _combined_homework_rows(scraped_data):
    """Merge scraped and photo-extracted homework rows."""
    scraped_rows = (
        scraped_data.get("odevlerim", {})
        .get("homework", {})
        .get("rows", [])
    )
    rows = []
    for row in [*(scraped_rows or []), *_load_photo_homework_rows()]:
        if not isinstance(row, dict):
            continue
        r = dict(row)
        if "Ders Adı" in r:
            r["normalized_course"] = normalize_course(r["Ders Adı"])
        rows.append(r)
    return _dedupe_homework_rows(rows)


def _normalize_due_datetime(value):
    """Normalize due datetime to 'DD.MM.YYYY HH:MM'."""
    if value is None:
        return ""
    s = str(value).strip().replace("T", " ")
    if not s:
        return ""

    def _build(day, month, year, hour, minute):
        dt = datetime(
            year=int(year),
            month=int(month),
            day=int(day),
            hour=int(hour),
            minute=int(minute),
        )
        return dt.strftime("%d.%m.%Y %H:%M")

    patterns = [
        # DD.MM.YYYY [HH:MM]
        r"(?P<d>\d{1,2})[./-](?P<m>\d{1,2})[./-](?P<y>\d{4})(?:\s+(?P<h>\d{1,2})[:.](?P<min>\d{2}))?",
        # YYYY.MM.DD [HH:MM]
        r"(?P<y>\d{4})[./-](?P<m>\d{1,2})[./-](?P<d>\d{1,2})(?:\s+(?P<h>\d{1,2})[:.](?P<min>\d{2}))?",
    ]
    for pattern in patterns:
        m = re.search(pattern, s)
        if not m:
            continue
        try:
            return _build(
                m.group("d"),
                m.group("m"),
                m.group("y"),
                m.group("h") or "23",
                m.group("min") or "59",
            )
        except ValueError:
            continue
    return ""


def _extract_json_payload(raw_text):
    """Parse JSON payload from model text output."""
    if not raw_text:
        raise ValueError("Model output empty")

    candidate = raw_text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\s*```$", "", candidate)

    for blob in (candidate,):
        try:
            return json.loads(blob)
        except json.JSONDecodeError:
            pass

    for pattern in (r"\{[\s\S]*\}", r"\[[\s\S]*\]"):
        m = re.search(pattern, candidate)
        if not m:
            continue
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
    raise ValueError("Model output did not contain valid JSON")


def _extract_homework_candidates_from_photo(image_bytes, mime_type):
    """Extract homework candidates from photo via Gemini vision."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY ayarlı değil")

    now_str = datetime.now().strftime("%d.%m.%Y")
    prompt = f"""Sen bir okul ödevi çıkarım ajanısın.
Görselde görünen ödevleri OCR + anlama ile çıkar.

Bugünün tarihi: {now_str}

SADECE geçerli JSON dön. Açıklama ekleme.
JSON şeması:
{{
  "homework": [
    {{
      "ders_adi": "string",
      "odev_basligi": "string",
      "odev_kaynagi": "string",
      "son_teslim_tarihi": "DD.MM.YYYY HH:MM",
      "odev_durumu": "Değerlendirilmemiş",
      "aciklama": "string"
    }}
  ]
}}

Kurallar:
- Görselde birden fazla ödev varsa hepsini listele.
- son_teslim_tarihi mutlaka DD.MM.YYYY HH:MM formatında olsun.
- Saat bilgisi yoksa 23:59 kullan.
- Emin olmadığın alanları boş string yap.
- Bilgi uydurma."""

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64.b64encode(image_bytes).decode("ascii"),
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_VISION_MODEL}:generateContent?key={api_key}"
    )
    resp = http_requests.post(url, json=payload, timeout=90)
    resp.raise_for_status()
    data = resp.json()

    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("Model aday üretmedi")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
    parsed = _extract_json_payload(text)

    if isinstance(parsed, list):
        return [x for x in parsed if isinstance(x, dict)]
    if isinstance(parsed, dict):
        rows = parsed.get("homework", [])
        if isinstance(rows, list):
            return [x for x in rows if isinstance(x, dict)]
    raise RuntimeError("Model çıktısı beklenen formatta değil")


def _coerce_homework_status(value):
    """Map arbitrary status text to dashboard-supported status values."""
    raw = str(value or "").strip().lower()
    if raw in {"yaptı", "yapti", "tamamlandı", "tamamlandi", "done"}:
        return "Yaptı"
    if raw in {"yapmadı", "yapmadi", "eksik", "missing", "incomplete"}:
        return "Yapmadı" if "yapma" in raw else "Eksik"
    return "Değerlendirilmemiş"


def _to_photo_homework_row(
    candidate,
    image_hash,
    source_type="ted",
    selected_course="",
    due_override="",
    private_lesson=None,
):
    """Convert extracted candidate to HomeworkItem-compatible row."""
    source_type = str(source_type or "ted").strip().lower()

    extracted_course = str(candidate.get("ders_adi", "")).strip()
    selected_course = normalize_course(str(selected_course or "").strip()) if selected_course else ""
    lesson_course = ""
    lesson_teacher = ""
    if isinstance(private_lesson, dict):
        lesson_course = normalize_course(str(private_lesson.get("course", "")).strip())
        lesson_teacher = str(private_lesson.get("teacher", "")).strip()

    if source_type == "private":
        course = lesson_course or selected_course or extracted_course or "Özel Ders"
    else:
        course = selected_course or extracted_course or "Genel"

    title = str(candidate.get("odev_basligi", "")).strip() or "Başlıksız Ödev"
    due = _normalize_due_datetime(due_override) or _normalize_due_datetime(
        candidate.get("son_teslim_tarihi", "")
    )
    if not due:
        due = datetime.now().replace(
            hour=23, minute=59, second=0, microsecond=0
        ).strftime("%d.%m.%Y %H:%M")

    if source_type == "private":
        if lesson_teacher:
            source = f"Özel Ders ({lesson_teacher})"
        else:
            source = "Özel Ders"
    else:
        source = "TED Connect"

    candidate_source = str(candidate.get("odev_kaynagi", "")).strip()
    if candidate_source and source_type != "private":
        source = f"{source} • {candidate_source[:50]}"

    description = str(candidate.get("aciklama", "")).strip()
    detail_desc = description or "Fotoğraftan AI ile işlendi."
    if source_type == "private" and lesson_teacher:
        detail_desc = f"Özel ders öğretmeni: {lesson_teacher}\n{detail_desc}"
    if source_type == "ted":
        detail_desc = f"Kaynak: TED Connect\n{detail_desc}"

    return {
        "Ders Adı": course[:120],
        "Ödev Başlığı": title[:280],
        "Ödev Kaynağı": source[:120],
        "Ödev Son Teslim Tarihi": due,
        "Ödev Durumu": _coerce_homework_status(candidate.get("odev_durumu")),
        "Ödev Görüntüle": "",
        "detail": {
            "description": detail_desc[:4000],
            "attachments": [],
        },
        "created_at": datetime.now().isoformat(),
        "source": "photo_ai_private" if source_type == "private" else "photo_ai_ted",
        "photo_hash": image_hash,
        "source_type": source_type,
        "private_lesson_id": (private_lesson or {}).get("id", "") if isinstance(private_lesson, dict) else "",
    }


# --- API endpoints (all require auth) ---

@app.route("/api/schedule")
@require_auth
def schedule():
    data = _scraped()
    weeks = data.get("ders_programi", [])
    today = DAY_NAMES.get(datetime.now().weekday(), "")
    latest = weeks[-1] if weeks else {}
    # Normalize course names in schedule cells
    rows = latest.get("schedule", {}).get("rows", [])
    for r in range(1, len(rows)):
        for c in range(1, len(rows[r])):
            cell = rows[r][c]
            if cell:
                lines = cell.split("\n")
                lines[0] = normalize_course(lines[0])
                rows[r][c] = "\n".join(lines)
    return jsonify({"weeks": weeks, "latest": latest, "today": today})


@app.route("/api/student/profile")
@require_auth
def student_profile():
    data = _scraped()
    profile = data.get("ogrenci_profili", {}) if isinstance(data, dict) else {}
    if not isinstance(profile, dict):
        profile = {}

    auth_user = {
        "email": session.get("user_email", ""),
        "name": session.get("user_name", ""),
        "picture": session.get("user_picture", ""),
    }
    fields = profile.get("fields", {})
    if not isinstance(fields, dict):
        fields = {}

    name = "Işık Kurt"
    student_no = str(profile.get("student_no", "")).strip() or str(
        fields.get("Öğrenci No", "")
    ).strip()
    class_name = str(profile.get("class_name", "")).strip() or str(
        fields.get("Sınıf", "")
    ).strip()
    branch = str(profile.get("branch", "")).strip() or str(
        fields.get("Şube", "")
    ).strip()

    return jsonify({
        "name": name,
        "student_no": student_no,
        "class_name": class_name,
        "branch": branch,
        "photo_data_url": profile.get("photo_data_url", ""),
        "fields": fields,
        "scraped_at": profile.get("scraped_at", ""),
        "auth": auth_user,
    })


@app.route("/api/private-lessons")
@require_auth
def private_lessons():
    lessons = _load_private_lessons()
    return jsonify({"lessons": lessons})


@app.route("/api/private-lessons", methods=["POST"])
@require_auth
def create_private_lesson():
    payload = request.get_json(silent=True) or {}
    course = str(payload.get("course", "")).strip()
    teacher = str(payload.get("teacher", "")).strip()
    is_recurring = _coerce_bool(payload.get("is_recurring", True), default=True)
    weekday = _normalize_weekday_name(payload.get("weekday", ""))
    start_time = str(payload.get("start_time", "")).strip()
    end_time = str(payload.get("end_time", "")).strip()
    date = str(payload.get("date", "")).strip()

    if not course:
        return jsonify({"error": "course gerekli"}), 400
    if not teacher:
        return jsonify({"error": "teacher gerekli"}), 400
    if not _parse_hhmm(start_time) or not _parse_hhmm(end_time):
        return jsonify({"error": "Saat formatı HH:MM olmalı"}), 400

    if is_recurring:
        if not weekday:
            return jsonify({"error": "Tekrarlı ders için weekday gerekli"}), 400
    else:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Tek seferlik ders için date YYYY-MM-DD olmalı"}), 400

    lessons = _load_private_lessons()
    item = {
        "id": secrets.token_hex(8),
        "course": normalize_course(course),
        "teacher": teacher,
        "is_recurring": is_recurring,
        "weekday": weekday if is_recurring else "",
        "date": "" if is_recurring else date,
        "start_time": start_time,
        "end_time": end_time,
        "active": True,
        "created_at": datetime.now().isoformat(),
    }
    lessons.append(item)
    _save_private_lessons(lessons)
    return jsonify({"ok": True, "lesson": item})


@app.route("/api/homework")
@require_auth
def homework():
    data = _scraped()
    hw = data.get("odevlerim", {})
    rows = _combined_homework_rows(data)
    summary = hw.get("summary", "")
    student_done_marks = _load_student_done_marks()
    student_done_changed = False

    # Track first-seen dates for homework items
    first_seen_path = os.path.join(OUTPUT_DIR, "homework_first_seen.json")
    try:
        with open(first_seen_path, "r", encoding="utf-8") as f:
            first_seen = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        first_seen = {}

    now_iso = datetime.now().isoformat()
    changed = False
    for r in rows:
        if "Ders Adı" in r:
            r["normalized_course"] = normalize_course(r["Ders Adı"])

        hw_key = _homework_row_key(r)
        r["homework_key"] = hw_key
        status_text = _normalize_homework_status_text(r.get("Ödev Durumu", ""))
        teacher_resolved = _is_teacher_resolved_homework_status(status_text)

        if teacher_resolved and hw_key in student_done_marks:
            student_done_marks.pop(hw_key, None)
            student_done_changed = True

        student_marked_done = bool(
            hw_key and hw_key in student_done_marks and not teacher_resolved
        )
        r["student_marked_done"] = student_marked_done
        if student_marked_done:
            r["student_done_at"] = student_done_marks.get(hw_key, "")

        title = r.get("Ödev Başlığı", "")
        if title and title not in first_seen:
            first_seen[title] = now_iso
            changed = True
        r["first_seen"] = first_seen.get(title, now_iso)

    if changed:
        atomic_json_dump(first_seen, first_seen_path)
    if student_done_changed:
        _save_student_done_marks(student_done_marks)

    return jsonify({"summary": summary, "homework": rows})


@app.route("/api/homework/mark-done", methods=["POST"])
@require_auth
def homework_mark_done():
    payload = request.get_json(silent=True) or {}
    requested_key = str(payload.get("homework_key") or "").strip()
    requested_title = str(
        payload.get("Ödev Başlığı") or payload.get("title") or ""
    ).strip()
    requested_due = _normalize_due_datetime(
        payload.get("Ödev Son Teslim Tarihi") or payload.get("due") or ""
    )
    requested_course = normalize_course(
        str(payload.get("Ders Adı") or payload.get("course") or "").strip()
    )

    if not requested_key and (not requested_title or not requested_due):
        return jsonify({
            "error": "homework_key veya (Ödev Başlığı + Ödev Son Teslim Tarihi) gerekli"
        }), 400

    rows = _combined_homework_rows(_scraped())
    target = None
    target_key = ""
    for row in rows:
        row_key = _homework_row_key(row)
        if requested_key and row_key == requested_key:
            target = row
            target_key = row_key
            break

        if not requested_key:
            row_title = str(row.get("Ödev Başlığı", "")).strip()
            row_due = _normalize_due_datetime(row.get("Ödev Son Teslim Tarihi", ""))
            row_course = normalize_course(str(row.get("Ders Adı", "")).strip())
            if (
                row_title == requested_title
                and row_due == requested_due
                and (not requested_course or row_course == requested_course)
            ):
                target = row
                target_key = row_key
                break

    if not target:
        return jsonify({"error": "Ödev bulunamadı"}), 404

    normalized_status = _normalize_homework_status_text(target.get("Ödev Durumu", ""))
    if _is_teacher_resolved_homework_status(normalized_status):
        return jsonify({
            "ok": True,
            "skipped": True,
            "reason": "teacher_status_resolved",
            "homework_key": target_key,
            "status": normalized_status,
        })

    marks = _load_student_done_marks()
    if target_key not in marks:
        marks[target_key] = datetime.now().isoformat()
        _save_student_done_marks(marks)

    return jsonify({
        "ok": True,
        "homework_key": target_key,
        "marked_at": marks.get(target_key, ""),
        "status": "YAPILAN",
    })


@app.route("/api/homework/photo", methods=["POST"])
@require_auth
def homework_from_photo():
    photo = request.files.get("photo")
    if not photo:
        return jsonify({"error": "photo dosyası gerekli"}), 400

    mime_type = (photo.mimetype or "").strip().lower()
    if not mime_type.startswith("image/"):
        return jsonify({"error": "Sadece görsel dosyası kabul edilir"}), 400

    image_bytes = photo.read()
    if not image_bytes:
        return jsonify({"error": "Boş görsel gönderildi"}), 400
    if len(image_bytes) > MAX_PHOTO_SIZE_BYTES:
        return jsonify({
            "error": "Görsel çok büyük (maksimum 12MB)"
        }), 413

    source_type = str(request.form.get("source_type", "ted")).strip().lower()
    if source_type not in {"ted", "private"}:
        return jsonify({"error": "source_type 'ted' veya 'private' olmalı"}), 400
    selected_course = str(request.form.get("course", "")).strip()
    due_override = str(request.form.get("due_date", "")).strip()
    private_lesson_id = str(request.form.get("private_lesson_id", "")).strip()
    private_lesson = None
    if source_type == "private":
        if not private_lesson_id:
            return jsonify({"error": "Özel Ders kaynağı için private_lesson_id gerekli"}), 400
        private_lesson = _find_private_lesson(private_lesson_id)
        if not private_lesson:
            return jsonify({"error": "Seçilen özel ders bulunamadı"}), 404

    try:
        candidates = _extract_homework_candidates_from_photo(image_bytes, mime_type)
    except RuntimeError as e:
        return jsonify({"error": f"AI işleme başarısız: {e}"}), 503
    except http_requests.HTTPError as e:
        return jsonify({"error": f"AI servis hatası: {e}"}), 502
    except Exception as e:
        return jsonify({"error": f"Görsel işlenemedi: {e}"}), 500

    image_hash = hashlib.sha256(image_bytes).hexdigest()[:16]
    extracted_rows = [
        _to_photo_homework_row(
            c,
            image_hash=image_hash,
            source_type=source_type,
            selected_course=selected_course,
            due_override=due_override,
            private_lesson=private_lesson,
        )
        for c in candidates
        if isinstance(c, dict)
    ]
    if not extracted_rows:
        return jsonify({"error": "Görselden ödev bilgisi çıkarılamadı"}), 422

    existing_photo_rows = _load_photo_homework_rows()
    known_keys = {_homework_row_key(r) for r in _combined_homework_rows(_scraped())}
    added = []
    skipped = 0
    for row in extracted_rows:
        key = _homework_row_key(row)
        if key in known_keys:
            skipped += 1
            continue
        known_keys.add(key)
        existing_photo_rows.append(row)
        added.append(row)

    if added:
        _save_photo_homework_rows(existing_photo_rows)

    return jsonify({
        "added_count": len(added),
        "skipped_count": skipped,
        "homework": added,
    })


@app.route("/api/sebit")
@require_auth
def sebit():
    return jsonify(_load_json("sebit_homework.json"))


@app.route("/api/grades")
@require_auth
def grades():
    data = _scraped()
    return jsonify(data.get("gelisim_raporu", {}))


@app.route("/api/calendar")
@require_auth
def calendar():
    data = _scraped()
    base = data.get("takvim", [])
    if not isinstance(base, list):
        base = []
    merged = [*base, *_private_lessons_calendar_events()]
    return jsonify({"events": merged})


@app.route("/api/teams")
@require_auth
def teams():
    data = _scraped()
    activities = data.get("takim_calismalari", {}).get("activities", {}).get("rows", [])
    ogep = data.get("ogep", {}).get("sessions", {}).get("rows", [])
    return jsonify({"activities": activities, "ogep": ogep})


@app.route("/api/content")
@require_auth
def content():
    data = _scraped()
    return jsonify(data.get("ders_icerikleri", {}))


@app.route("/api/announcements")
@require_auth
def announcements():
    data = _scraped()
    ann = data.get("duyurular", {}).get("announcements", [])
    return jsonify({"announcements": ann})


@app.route("/api/progress/ec")
@require_auth
def progress_ec():
    return jsonify(_load_json("englishcentral_progress.json"))


@app.route("/api/progress/a3k")
@require_auth
def progress_a3k():
    return jsonify(_load_json("achieve3000_progress.json"))


@app.route("/api/enrichment")
@require_auth
def enrichment():
    return jsonify(_load_json("enrichment_cache.json"))


@app.route("/api/health")
@require_auth
def health():
    payload = _load_json("health.json")
    if not isinstance(payload, dict):
        payload = {}

    scraped = _scraped()
    scraped_at = ""
    if isinstance(scraped, dict):
        scraped_at = str(scraped.get("scraped_at", "") or "").strip()

    staleness = payload.get("staleness")
    if not isinstance(staleness, dict):
        staleness = {}
    stale_sections = staleness.get("stale_sections")
    if not isinstance(stale_sections, list):
        stale_sections = []

    last_successful = _latest_iso_timestamp(
        staleness.get("last_successful_full_scrape", ""),
        scraped_at,
    )

    payload.setdefault("timestamp", "")
    payload.setdefault("success", False)
    payload.setdefault("scrape_errors", [])
    payload.setdefault("duration_seconds", 0)

    payload["timestamp"] = _latest_iso_timestamp(
        payload.get("timestamp", ""),
        scraped_at,
    )
    staleness["last_successful_full_scrape"] = last_successful
    staleness["stale_sections"] = stale_sections
    payload["staleness"] = staleness

    return jsonify(payload)


# --- Color constants for unified calendar ---
_UNIFIED_COLORS = {
    "lesson": "#002d9c",
    "homework": "#da1e28",
    "private_lesson": "#ff832b",
    "ogep": "#009d9a",
    "team": "#8a3ffc",
    "sebit": "#6f6f6f",
    "event": "#0072c3",
}


def _make_id(*parts):
    """Deterministic short id from parts."""
    raw = "|".join(str(p) for p in parts)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _current_week_dates():
    """Return list of 5 date objects (Mon-Fri) for the current week."""
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    return [monday + timedelta(days=i) for i in range(5)]


def _parse_time_range(cell_text):
    """Parse time range from first column like '1. Ders\\n08:00 - 08:40' or '08:40 - 08:55'.
    Returns (start_h, start_m, end_h, end_m) or None."""
    m = re.search(r"(\d{1,2})[:.:](\d{2})\s*[-–/]\s*(\d{1,2})[:.:](\d{2})", cell_text)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    return None


def _parse_ddmmyyyy_hhmm(s):
    """Parse 'DD.MM.YYYY HH:MM' to ISO string."""
    try:
        dt = datetime.strptime(s.strip(), "%d.%m.%Y %H:%M")
        return dt.isoformat()
    except (ValueError, AttributeError):
        return s


@app.route("/api/calendar/unified")
@require_auth
def calendar_unified():
    data = _scraped()
    events = []
    week_dates = _current_week_dates()

    # 1. Lessons from ders_programi
    weeks = data.get("ders_programi", [])
    if weeks:
        latest = weeks[-1]
        rows = latest.get("schedule", {}).get("rows", [])
        # headers row: ['', 'Pazartesi', 'Salı', ...]
        # day_col_map: column index -> weekday index (0=Mon)
        day_names_order = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
        day_col_map = {}
        if rows:
            for ci, hdr in enumerate(rows[0]):
                for di, dn in enumerate(day_names_order):
                    if dn in str(hdr):
                        day_col_map[ci] = di
                        break

        for r in range(1, len(rows)):
            row = rows[r]
            if not row:
                continue
            time_cell = row[0] if row else ""
            parsed = _parse_time_range(time_cell)
            if not parsed:
                continue
            sh, sm, eh, em = parsed

            for ci in range(1, len(row)):
                cell = row[ci]
                if not cell or ci not in day_col_map:
                    continue
                # Skip break/breakfast rows
                cell_lower = cell.strip().lower()
                if cell_lower in ("kahvaltı", "öğle yemeği", "teneffüs", "yemek"):
                    continue
                if re.match(r"^\d{1,2}[:.]\d{2}\s*[-–]\s*\d{1,2}[:.]\d{2}$", cell.strip()):
                    continue

                day_idx = day_col_map[ci]
                day_date = week_dates[day_idx]
                start_dt = datetime(day_date.year, day_date.month, day_date.day, sh, sm)
                end_dt = datetime(day_date.year, day_date.month, day_date.day, eh, em)

                lines = cell.split("\n")
                lesson_name = normalize_course(lines[0].strip())
                subtitle = lines[1].strip() if len(lines) > 1 else ""

                events.append({
                    "id": _make_id("lesson", day_idx, sh, sm, lesson_name),
                    "title": lesson_name,
                    "type": "lesson",
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat(),
                    "color": _UNIFIED_COLORS["lesson"],
                    "course": lesson_name,
                    "subtitle": subtitle,
                })

    # 2. Homework deadlines
    hw_rows = _combined_homework_rows(data)
    for hw in hw_rows:
        deadline_str = hw.get("Ödev Son Teslim Tarihi", "")
        course = normalize_course(hw.get("Ders Adı", ""))
        title = hw.get("Ödev Başlığı", "Ödev")
        status = hw.get("Ödev Durumu", "")
        iso_start = _parse_ddmmyyyy_hhmm(deadline_str)
        events.append({
            "id": _make_id("hw", title, deadline_str),
            "title": title,
            "type": "homework",
            "start": iso_start,
            "end": iso_start,
            "color": _UNIFIED_COLORS["homework"],
            "course": course,
            "status": status,
        })

    # 3. Private lessons
    for pev in _private_lessons_for_week(week_dates):
        pev["color"] = _UNIFIED_COLORS["private_lesson"]
        events.append(pev)

    # 4. ÖGEP sessions
    ogep_rows = data.get("ogep", {}).get("sessions", {}).get("rows", [])
    for og in ogep_rows:
        name = og.get("ÖGEP (Öğrenci Gelişim Programı)", "ÖGEP")
        start_str = og.get("Çalışma Başlangıç", "")
        end_str = og.get("Çalışma Bitiş", "")
        status = og.get("Katılım Durumu", "")
        events.append({
            "id": _make_id("ogep", name, start_str),
            "title": name,
            "type": "ogep",
            "start": _parse_ddmmyyyy_hhmm(start_str),
            "end": _parse_ddmmyyyy_hhmm(end_str),
            "color": _UNIFIED_COLORS["ogep"],
            "status": status,
        })

    # 5. Team activities
    team_rows = data.get("takim_calismalari", {}).get("activities", {}).get("rows", [])
    for t in team_rows:
        name = t.get("Academy+", "Takım")
        start_str = t.get("Çalışma Başlangıç", "")
        end_str = t.get("Çalışma Bitiş", "")
        status = t.get("Katılım Durumu", "")
        events.append({
            "id": _make_id("team", name, start_str),
            "title": name,
            "type": "team",
            "start": _parse_ddmmyyyy_hhmm(start_str),
            "end": _parse_ddmmyyyy_hhmm(end_str),
            "color": _UNIFIED_COLORS["team"],
            "status": status,
        })

    # 6. SEBIT homework
    sebit_data = _load_json("sebit_homework.json")
    sebit_hw = sebit_data.get("homework", []) if isinstance(sebit_data, dict) else []
    for s in sebit_hw:
        title = s.get("title", "SEBIT")
        course = s.get("course", "")
        start_str = s.get("start_date", "")
        end_str = s.get("end_date", "")
        # sebit dates are "YYYY-MM-DD HH:MM" format
        try:
            iso_start = datetime.strptime(start_str, "%Y-%m-%d %H:%M").isoformat()
        except (ValueError, TypeError):
            iso_start = start_str
        try:
            iso_end = datetime.strptime(end_str, "%Y-%m-%d %H:%M").isoformat()
        except (ValueError, TypeError):
            iso_end = end_str
        events.append({
            "id": _make_id("sebit", s.get("id", title), start_str),
            "title": title,
            "type": "sebit",
            "start": iso_start,
            "end": iso_end,
            "color": _UNIFIED_COLORS["sebit"],
            "course": course,
            "status": s.get("state_text", ""),
        })

    # 7. Takvim events (currently empty but included for future)
    takvim = data.get("takvim", [])
    for ev in takvim:
        events.append({
            "id": _make_id("event", ev.get("title", ""), ev.get("start", "")),
            "title": ev.get("title", ""),
            "type": "event",
            "start": ev.get("start", ""),
            "end": ev.get("end", ev.get("start", "")),
            "color": _UNIFIED_COLORS["event"],
        })

    return jsonify({"events": events})


# --- SPA static serving (production build) ---
@app.route("/")
@app.route("/<path:path>")
def serve_spa(path=""):
    if path and os.path.exists(os.path.join(DIST_DIR, path)):
        return send_from_directory(DIST_DIR, path)
    index = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index):
        return send_from_directory(DIST_DIR, "index.html")
    return jsonify({"error": "Dashboard not built. Run: cd dashboard && npm run build"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8085, debug=True)
