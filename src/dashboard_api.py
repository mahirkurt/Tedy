"""Dashboard API server — serves TED data as JSON endpoints."""
import base64
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import sys
import time
import unicodedata
from datetime import datetime, timedelta
from functools import wraps

import requests as http_requests
from flask import Flask, Response, jsonify, request, send_from_directory, session
from flask_cors import CORS
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from werkzeug.exceptions import HTTPException

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from src.env_loader import load_env
from src.json_utils import atomic_json_dump
from src.course_names import normalize_course
from src.roles import (  # noqa: F401  (re-exported: tests read dashboard_api.USER_ROLES etc.)
    ALLOWED_EMAILS,
    FULL_ACCESS_EMAILS,
    GOOGLE_CLIENT_ID,
    ROLE_FULL,
    ROLE_READER,
    USER_ROLES,
)
from src import module_progress, module_store, module_ticket

load_env()

# H3: fail loudly instead of silently generating a random per-process key.
# With 2 gunicorn workers, a missing key means each worker mints its own
# random secret at startup, so a session cookie signed by one worker is
# rejected by the other — users get logged out at random with no error
# anywhere. A dead service with a clear reason beats a live service that
# randomly logs people out.
_DASHBOARD_SECRET_KEY = os.environ.get("DASHBOARD_SECRET_KEY", "").strip()
if not _DASHBOARD_SECRET_KEY:
    raise RuntimeError(
        "DASHBOARD_SECRET_KEY is not set. Set it in .env (or the process "
        "environment) before starting the dashboard — see CLAUDE.md's "
        "Required Credentials section. Do not fall back to a random key: "
        "with multiple gunicorn workers each worker would mint a different "
        "one, silently invalidating sessions signed by the other worker."
    )

app = Flask(__name__)
app.secret_key = _DASHBOARD_SECRET_KEY
CORS(app, supports_credentials=True)


def _dashboard_cookie_secure_default() -> bool:
    """Whether the session cookie should require HTTPS (H4).

    Defaults to True — the site is served over HTTPS in production.
    Override with DASHBOARD_COOKIE_SECURE=0 for local/plain-HTTP runs: a
    `Secure` cookie is never sent back by the browser over `http://`.
    Compatibility note (checked against dashboard/playwright.config.ts):
    the Playwright e2e suite serves the app at http://localhost:8086 and
    local dev/manual testing hits http://127.0.0.1:8085, both plain HTTP.
    Today's e2e specs run entirely under TEST_AUTH_BYPASS and never call
    /api/auth/login (the only route that sets session["user_email"]), so
    they do not currently exercise a session-cookie flow and are not known
    to break with SESSION_COOKIE_SECURE=True. If a future e2e spec adds a
    real login flow, run it with DASHBOARD_COOKIE_SECURE=0.
    """
    return os.environ.get("DASHBOARD_COOKIE_SECURE", "1") != "0"


def _apply_cookie_config(flask_app: Flask) -> None:
    """Apply session cookie hardening (H4) to `flask_app`.

    Factored out (rather than inlined at module scope) so tests can flip
    DASHBOARD_COOKIE_SECURE and re-apply without re-importing the module.
    """
    flask_app.config["SESSION_COOKIE_HTTPONLY"] = True
    flask_app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    flask_app.config["SESSION_COOKIE_SECURE"] = _dashboard_cookie_secure_default()


_apply_cookie_config(app)

TEST_AUTH_BYPASS = os.environ.get("TEST_AUTH_BYPASS") == "1"

if TEST_AUTH_BYPASS:
    # H5: TEST_AUTH_BYPASS disables five separate auth gates at once
    # (_current_user_email, require_auth, _require_assistant_access x2,
    # auth_me). It is a documented test workflow (see CLAUDE.md), so it
    # must keep working — but if it were ever set in production (e.g. the
    # systemd unit's EnvironmentFile=.env picked it up), every gate would
    # go dark with no other signal. Make it impossible to miss instead.
    print(
        "\n" + "!" * 70 +
        "\n!! AUTH BYPASS ACTIVE — all authentication disabled"
        "\n!! TEST_AUTH_BYPASS=1 is set in this process's environment."
        "\n!! Every session/API-key check is being skipped."
        "\n!! This must NEVER be set in production (.env on the live host)."
        "\n" + "!" * 70 + "\n",
        file=sys.stderr,
    )

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
DIST_DIR = os.path.join(PROJECT_ROOT, "dashboard-dist")
PHOTO_HOMEWORK_FILE = os.path.join(OUTPUT_DIR, "photo_homework.json")
PRIVATE_LESSON_FILE = os.path.join(OUTPUT_DIR, "private_lessons.json")
STUDENT_DONE_FILE = os.path.join(OUTPUT_DIR, "homework_student_done.json")
MAX_PHOTO_SIZE_BYTES = 12 * 1024 * 1024
GEMINI_VISION_MODEL = os.environ.get("HOMEWORK_VISION_MODEL", "gemini-2.5-flash")

# --- Roles: defined in src/roles.py (shared with the ted-mcp orchestrator) ---

# Endpoints a reader may reach. Default-deny: a route that is not named here is
# refused for readers, so adding an endpoint never leaks data by omission.
READER_ENDPOINTS = {
    "books_list",
    "book_detail",
    "book_chapter",
    "book_translate",
    "book_progress_get",
    "book_progress_save",
}

ASSISTANT_API_KEY = os.environ.get("ASSISTANT_API_KEY", "").strip()
ASSISTANT_ADMIN_EMAILS = {
    x.strip().lower()
    for x in os.environ.get(
        "ASSISTANT_ADMIN_EMAILS", ",".join(sorted(FULL_ACCESS_EMAILS))
    ).split(",")
    if x.strip()
}

_ASSISTANT_RUNTIME = None


class AssistantUnavailableError(RuntimeError):
    """Raised when the optional assistant subsystem cannot be loaded."""


def _load_api_keys() -> list[tuple[str, str]]:
    """Load API keys from env. Format: 'label:key,label2:key2' or 'key1,key2'."""
    raw = os.environ.get("API_KEYS", "").strip()
    if not raw:
        return []
    keys = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if ":" in entry:
            label, key = entry.split(":", 1)
            keys.append((label.strip(), key.strip()))
        else:
            keys.append(("default", entry))
    return keys


API_KEYS = _load_api_keys()


def _validate_api_key(provided: str) -> str | None:
    """Return label if key is valid, None otherwise. Timing-safe."""
    if not provided or not provided.startswith("tdyK_"):
        return None
    for label, stored_key in API_KEYS:
        if hmac.compare_digest(provided, stored_key):
            return label
    return None

DAY_NAMES = {
    0: "Pazartesi", 1: "Salı", 2: "Çarşamba",
    3: "Perşembe", 4: "Cuma", 5: "Cumartesi", 6: "Pazar"
}


def _is_json_api_request() -> bool:
    path = str(getattr(request, "path", "") or "")
    return path.startswith("/api/") or path.startswith("/v1/")


@app.errorhandler(HTTPException)
def _handle_http_exception(err: HTTPException):
    if _is_json_api_request():
        msg = str(getattr(err, "description", "") or getattr(err, "name", "HTTP error")).strip()
        return jsonify({"error": msg, "status": err.code}), int(err.code or 500)
    return err


@app.errorhandler(Exception)
def _handle_unexpected_exception(err: Exception):
    if _is_json_api_request():
        app.logger.exception("Unhandled API exception: %s", err)
        return jsonify({"error": "internal_server_error"}), 500
    app.logger.exception("Unhandled exception: %s", err)
    return ("Internal Server Error", 500)


# --- Auth ---

def _current_user_email():
    """Email of the signed-in session user, or None for key/bypass callers."""
    email = str(session.get("user_email", "") or "").lower().strip()
    if email:
        return email
    if TEST_AUTH_BYPASS:
        return "test@tedy.online"
    return None


def _current_user_role():
    """Role derived from the roster, never from the session.

    Deriving on every request means a role change takes effect immediately
    instead of waiting for old sessions to expire, and an email that has been
    dropped from the roster falls back to the least privilege.

    No session email also falls back to the least privilege (ROLE_READER),
    not ROLE_FULL: every current call site already sits behind a
    `session.get("user_email")` check, so this branch is unreached today —
    but a future caller outside that guard must not silently receive full
    access by default.
    """
    email = str(session.get("user_email", "") or "").lower().strip()
    if not email:
        return ROLE_READER
    return USER_ROLES.get(email, ROLE_READER)


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if TEST_AUTH_BYPASS:
            return f(*args, **kwargs)
        if session.get("user_email"):
            if _current_user_role() != ROLE_FULL and request.endpoint not in READER_ENDPOINTS:
                return jsonify({"error": "forbidden", "role": _current_user_role()}), 403
            return f(*args, **kwargs)
        # API key: Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            label = _validate_api_key(auth_header[7:])
            if label is not None:
                return f(*args, **kwargs)
        # API key: query parameter
        query_key = request.args.get("api_key", "")
        if query_key:
            label = _validate_api_key(query_key)
            if label is not None:
                return f(*args, **kwargs)
        return jsonify({"error": "Unauthorized"}), 401
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
            "role": USER_ROLES.get(email, ROLE_READER),
        })
    except ValueError as e:
        return jsonify({"error": f"Invalid token: {e}"}), 401


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/auth/me")
def auth_me():
    if session.get("user_email"):
        return jsonify({
            "email": session["user_email"],
            "name": session.get("user_name", ""),
            "picture": session.get("user_picture", ""),
            "role": _current_user_role(),
        })
    if TEST_AUTH_BYPASS:
        return jsonify({
            "email": "test@tedy.online",
            "name": "Test User",
            "picture": "",
            "role": ROLE_FULL,
        })
    return jsonify({"error": "Not authenticated"}), 401


def _assistant_runtime():
    global _ASSISTANT_RUNTIME
    if _ASSISTANT_RUNTIME is None:
        try:
            from src.assistant_core import AssistantRuntime

            _ASSISTANT_RUNTIME = AssistantRuntime(PROJECT_ROOT)
        except Exception as exc:
            app.logger.error(
                "Assistant subsystem unavailable (%s)", type(exc).__name__
            )
            raise AssistantUnavailableError("assistant_unavailable") from exc

    return _ASSISTANT_RUNTIME


def _has_valid_assistant_api_key() -> bool:
    if not ASSISTANT_API_KEY:
        return False
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return False
    provided = auth.split(" ", 1)[1].strip()
    return bool(provided) and secrets.compare_digest(provided, ASSISTANT_API_KEY)


def _require_assistant_access(api_key_only=False):
    """Allow access to assistant routes.

    - External OpenAI-compatible routes should use api_key_only=True.
    - Internal dashboard routes can reuse session auth.
    """
    if TEST_AUTH_BYPASS:
        return None
    if _has_valid_assistant_api_key():
        return None
    if not api_key_only and session.get("user_email"):
        if _current_user_role() != ROLE_FULL:
            return jsonify({"error": "forbidden", "role": _current_user_role()}), 403
        return None
    return jsonify({"error": "Unauthorized"}), 401


def _is_assistant_admin() -> bool:
    if TEST_AUTH_BYPASS:
        return True
    if _has_valid_assistant_api_key():
        return True
    email = str(session.get("user_email", "")).lower().strip()
    return bool(email) and email in ASSISTANT_ADMIN_EMAILS


def _assistant_progress_allowed() -> bool:
    """Module progress may enter the Assistant's model context only for a signed-in full-role
    person (plan SP5 K-S6). API keys — tdyK_ integrations and ASSISTANT_API_KEY on /v1/* — and the
    test bypass are not people, so their answers never carry progress."""
    return _module_person() is not None


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
    # The scraper now keeps the whole published year, so the last element is a
    # week in June. The week the scraper saw selected carries `is_current`;
    # weeks[-1] stays the fallback for data written before that mark existed.
    latest = next(
        (w for w in weeks if isinstance(w, dict) and w.get("is_current")),
        weeks[-1] if weeks else {},
    )
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


@app.route("/api/pages")
@require_auth
def portal_pages():
    """The portal pages that carry documents and forms rather than a feed.

    Only the ones with something in them: measured 2026-09-20 all five were
    empty — no project listed, "toplam 0 kayıt" on the forms, no club options
    yet — and a surface that lists five empty pages is five things to read
    past. `empty` is the scraper's own verdict; pages the portal refused keep
    their `unavailable` reason so the absence can be explained.
    """
    data = _scraped()
    sayfalar = data.get("ek_sayfalar") or {}
    if not isinstance(sayfalar, dict):
        sayfalar = {}
    dolu = {
        k: v for k, v in sayfalar.items()
        if isinstance(v, dict) and not v.get("empty")
    }
    engelli = {
        k: v.get("unavailable") for k, v in sayfalar.items()
        if isinstance(v, dict) and v.get("unavailable")
    }
    return jsonify({"pages": dolu, "unavailable": engelli,
                    "known": sorted(sayfalar)})


@app.route("/api/content/weeks")
@require_auth
def content_weeks():
    """Course content for every week the scraper has collected.

    The portal fills the year in ahead of time and the cards genuinely differ
    week to week — measured 2026-09-20: 12 of 17 courses carried different
    cards in week 2 than in week 1. /api/content stays the open week so the
    surfaces that read it do not change shape.
    """
    data = _scraped()
    haftalar = data.get("ders_icerikleri_haftalar") or {}
    if not isinstance(haftalar, dict):
        haftalar = {}
    guncel = ""
    for w in data.get("ders_programi") or []:
        if isinstance(w, dict) and w.get("is_current"):
            guncel = w.get("week_label") or ""
            break
    # Fall back to the week /api/content is serving, so a caller always has
    # somewhere to start even on data written before the weeks existed.
    if guncel not in haftalar:
        guncel = next(iter(haftalar), "")
    return jsonify({"weeks": haftalar, "current": guncel})


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


# ---------------------------------------------------------------------------
# Exams API — unified exam data (takvim events + grades + related content)
# ---------------------------------------------------------------------------

def _turkish_lower(s):
    """Turkish-aware lowercase (İ→i, I→ı)."""
    return unicodedata.normalize(
        'NFC', s.replace('İ', 'i').replace('I', 'ı')
    ).lower()


def _turkish_title(s):
    """Turkish-aware title case for all-caps strings."""
    words = _turkish_lower(s).split()
    _MINOR = {"ve", "ile", "da", "de", "mi", "mu"}

    def _cap(c):
        if c == 'i':
            return 'İ'
        if c == 'ı':
            return 'I'
        return c.upper()

    result = []
    for i, w in enumerate(words):
        if i > 0 and w in _MINOR:
            result.append(w)
        else:
            result.append(_cap(w[0]) + w[1:] if w else w)
    return " ".join(result)


_SINAV_KEYWORDS = ("sınav", "yazılı", "exam")
_SINAV_WORD_RE = re.compile(r"\btest\b", re.IGNORECASE)
_SINAV_NUMBER_RE = re.compile(
    r"(\d)\.\s*(?:Yazılı|Sınav)", re.IGNORECASE)
_COURSE_FROM_TITLE_RE = re.compile(
    r"^(?:\d+-)*\d+\.\s*S[Iİıi]n[Iİıi]flar\s+(.+?)\s*[-–]",
    re.IGNORECASE
)


_SINAV_EXCLUDE = (
    "başlangıcı", "beginning of",
    "bitişi", "end of",
    "not girişleri", "grades entries",
)

# Stable course → color mapping (hue-shifted, WCAG-friendly)
_COURSE_COLORS = {
    "Türkçe":             "#0f62fe",  # blue
    "Matematik":          "#8a3ffc",  # purple
    "Fen Bilimleri":      "#009d9a",  # teal
    "Sosyal Bilgiler":    "#a56eff",  # violet
    "İngilizce":          "#1192e8",  # cyan
    "Din Kültürü":        "#005d5d",  # dark teal
    "Fransızca":          "#fa4d56",  # red
    "Görsel Sanatlar":    "#d4bbff",  # lavender
    "Müzik":              "#ee5396",  # magenta
    "Beden Eğitimi":      "#24a148",  # green
    "Bilişim":            "#0072c3",  # dark blue
    "Ahlak ve Yurttaşlık": "#b28600",  # gold
    "PDR":                "#007d79",  # dark cyan
}
_FALLBACK_COLORS = [
    "#6929c4", "#002d9c", "#a56eff", "#005d5d",
    "#9f1853", "#198038", "#b28600",
]


def _course_color(course_name):
    """Return a stable hex color for a course name."""
    if course_name in _COURSE_COLORS:
        return _COURSE_COLORS[course_name]
    # Stable hash-based fallback
    idx = sum(ord(c) for c in course_name) % len(_FALLBACK_COLORS)
    return _FALLBACK_COLORS[idx]


_DONEM_RE = re.compile(
    r"(\d)\.\s*(?:DÖNEM|Dönem|dönem)", re.IGNORECASE)


def _clean_exam_title(course, exam_number, raw_title):
    """Build a short, readable exam title."""
    lower = _turkish_lower(raw_title)

    # Extract dönem (term) number
    dm = _DONEM_RE.search(raw_title)
    donem = f"{dm.group(1)}. Dönem " if dm else ""

    # Determine exam type
    if "dinleme" in lower or "listening" in lower:
        suffix = f"{donem}Dinleme Sınavı"
    elif "izleme" in lower or "monitoring" in lower:
        suffix = f"{donem}İzleme Sınavı"
    elif exam_number:
        suffix = f"{donem}{exam_number}. Yazılı"
    elif "yazılı" in lower:
        suffix = f"{donem}Yazılı"
    else:
        suffix = f"{donem}Sınav" if donem else "Sınav"
    return f"{course} · {suffix}"


def _is_exam_event(title):
    lower = _turkish_lower(title)
    if any(ex in lower for ex in _SINAV_EXCLUDE):
        return False
    if any(kw in lower for kw in _SINAV_KEYWORDS):
        return True
    return bool(_SINAV_WORD_RE.search(title))


def _extract_exam_info(title):
    """Extract (normalized_course, raw_course, exam_number) from event title."""
    num_match = _SINAV_NUMBER_RE.search(title)
    exam_number = int(num_match.group(1)) if num_match else None

    course_match = _COURSE_FROM_TITLE_RE.match(title)
    if course_match:
        raw_course = course_match.group(1).strip()
        # Strip bilingual suffix and scope tags
        if " / " in raw_course:
            raw_course = raw_course.split(" / ")[0].strip()
        raw_course = re.sub(
            r'\s*\([^)]*[Gg]enel[^)]*\)\s*$',
            '', raw_course).strip()
    else:
        # Strip "X-Y. Sınıflar " prefix
        raw_course = re.sub(
            r'^(?:\d+-)*\d+\.\s*'
            r'S[Iİıi]n[Iİıi]flar\s+',
            '', title, flags=re.IGNORECASE)
        # Strip bilingual " / English..." suffix
        if " / " in raw_course:
            raw_course = raw_course.split(" / ")[0].strip()
        # Strip "(TED Geneli)" / "(Türkiye Geneli)" scope
        raw_course = re.sub(
            r'\s*\([^)]*[Gg]enel[^)]*\)\s*$',
            '', raw_course).strip()
    # Normalize via aliases
    normalized = normalize_course(raw_course)
    if normalized == raw_course and raw_course.upper() == raw_course:
        tc = _turkish_title(raw_course)
        normalized = normalize_course(tc)
    return normalized, raw_course, exam_number


def _build_grade_lookup(grades_list):
    """Build {normalized_course: {"1": score, "2": score, "3": score}} from gelisim_raporu grades."""
    lookup = {}
    for row in grades_list:
        if not isinstance(row, dict):
            continue
        course = normalize_course(row.get("Ders", ""))
        if not course:
            continue
        entry = {}
        for col_num in ("1", "2", "3"):
            val = row.get(f"{col_num}. Sınav", "-")
            if val and val != "-":
                entry[col_num] = val
        lookup[course] = entry
    return lookup


def _find_related_homework(exam_course, exam_date_str, homework_rows):
    """Find homework from same course within 4 weeks before exam date."""
    related = []
    if not exam_date_str:
        return related
    try:
        exam_dt = datetime.fromisoformat(
            exam_date_str.replace("Z", "+00:00"))
        # Strip tz for comparison with naive hw dates
        exam_dt = exam_dt.replace(tzinfo=None)
    except (ValueError, TypeError):
        return related

    window_start = exam_dt - timedelta(weeks=4)
    exam_lower = _turkish_lower(exam_course)

    for row in homework_rows:
        if not isinstance(row, dict):
            continue
        hw_course = row.get("normalized_course", "")
        if not hw_course:
            hw_course = normalize_course(
                row.get("Ders Adı", ""))
        if _turkish_lower(hw_course) != exam_lower:
            continue

        deadline_str = row.get("Ödev Son Teslim Tarihi", "")
        try:
            # Try DD.MM.YYYY HH:MM format first
            hw_dt = datetime.strptime(deadline_str, "%d.%m.%Y %H:%M")
        except (ValueError, TypeError):
            try:
                hw_dt = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue

        if window_start <= hw_dt <= exam_dt:
            related.append({
                "title": row.get("Ödev Başlığı", ""),
                "deadline": deadline_str,
                "status": row.get("Ödev Durumu", ""),
            })

    return related[:5]


def _find_related_content(exam_course, ders_icerikleri):
    """Find course content from same course."""
    related = []
    if not isinstance(ders_icerikleri, dict):
        return related

    exam_lower = _turkish_lower(exam_course)
    for course_name, items in ders_icerikleri.items():
        nc = normalize_course(course_name)
        if _turkish_lower(nc) != exam_lower:
            continue
        if isinstance(items, list):
            for item in items[:5]:
                if isinstance(item, dict):
                    related.append({
                        "title": item.get("title", item.get("konu", str(item))),
                        "type": "ders_icerikleri",
                    })
                elif isinstance(item, str):
                    related.append({"title": item, "type": "ders_icerikleri"})

    return related[:10]


@app.route("/api/exams")
@require_auth
def exams():
    data = _scraped()
    now = datetime.now()

    # --- Takvim exam events ---
    takvim = data.get("takvim", [])
    if not isinstance(takvim, list):
        takvim = []

    # --- Grades lookup ---
    gelisim = data.get("gelisim_raporu", {})
    grades_list = gelisim.get("grades", []) if isinstance(gelisim, dict) else []
    grade_lookup = _build_grade_lookup(grades_list)

    # --- Homework rows ---
    hw_rows = _combined_homework_rows(data)

    # --- Course content ---
    ders_icerikleri = data.get("ders_icerikleri", {})

    # --- AI content map ---
    content_map = _load_json("exam_content_map.json")
    if not isinstance(content_map, dict):
        content_map = {}

    # --- Enrichment cache for study guides ---
    enrichment = _load_json("enrichment_cache.json")
    if not isinstance(enrichment, dict):
        enrichment = {}

    exams_list = []
    seen_course_nums = set()  # track which course+examNumber combos we've seen from takvim

    for evt in takvim:
        if not isinstance(evt, dict):
            continue
        title = evt.get("title", "")
        if not _is_exam_event(title):
            continue

        course, raw_course, exam_number = _extract_exam_info(title)
        date_str = evt.get("start", "")

        # Determine status
        try:
            evt_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            status = "upcoming" if evt_dt > now else "past"
        except (ValueError, TypeError):
            status = "past"

        # Match grade
        grade = None
        if exam_number and course in grade_lookup:
            grade = grade_lookup[course].get(str(exam_number))

        # Related content
        related_hw = _find_related_homework(course, date_str, hw_rows)
        related_content = _find_related_content(course, ders_icerikleri)

        # AI content map
        map_key = f"{course}|{title}|{date_str[:10] if date_str else ''}"
        ai_summary = None
        map_entry = content_map.get(map_key)
        if isinstance(map_entry, dict):
            ai_summary = map_entry.get("summary")

        # Study guide from enrichment cache
        study_guide = None
        for ek, ev in enrichment.items():
            if isinstance(ev, dict) and ev.get("type") == "sinav":
                if course in ek or title in ek:
                    study_guide = ev.get("note")
                    break

        exam_id = hashlib.md5(f"{course}|{title}|{date_str}".encode()).hexdigest()[:12]

        if exam_number:
            seen_course_nums.add((course, str(exam_number)))

        exams_list.append({
            "id": exam_id,
            "course": course,
            "title": _clean_exam_title(
                course, exam_number, title),
            "rawTitle": title,
            "courseColor": _course_color(course),
            "examNumber": exam_number,
            "date": date_str or None,
            "endDate": evt.get("end") or None,
            "allDay": evt.get("allDay", False),
            "status": status,
            "grade": grade,
            "studyGuide": study_guide,
            "aiSummary": ai_summary,
            "relatedHomework": related_hw,
            "relatedContent": related_content,
        })

    # --- Synthetic exams from grades without takvim events ---
    for row in grades_list:
        if not isinstance(row, dict):
            continue
        course = normalize_course(row.get("Ders", ""))
        if not course:
            continue
        for col_num in ("1", "2", "3"):
            val = row.get(f"{col_num}. Sınav", "-")
            if val and val != "-" and (course, col_num) not in seen_course_nums:
                exam_id = hashlib.md5(
                    f"{course}|{col_num}. Sınav|synthetic".encode()
                ).hexdigest()[:12]
                raw = f"{course} {col_num}. Sınav"
                exams_list.append({
                    "id": exam_id,
                    "course": course,
                    "title": _clean_exam_title(
                        course, int(col_num), raw),
                    "rawTitle": raw,
                    "courseColor": _course_color(course),
                    "examNumber": int(col_num),
                    "date": None,
                    "endDate": None,
                    "allDay": False,
                    "status": "past",
                    "grade": val,
                    "studyGuide": None,
                    "aiSummary": None,
                    "relatedHomework": [],
                    "relatedContent": [],
                })

    # --- Sort: upcoming by date asc, past by date desc ---
    upcoming = sorted(
        [e for e in exams_list if e["status"] == "upcoming"],
        key=lambda e: e["date"] or "",
    )
    past = sorted(
        [e for e in exams_list if e["status"] == "past"],
        key=lambda e: e["date"] or "",
        reverse=True,
    )

    all_exams = upcoming + past

    # --- Stats ---
    grade_vals = [int(e["grade"]) for e in exams_list if e["grade"] and e["grade"].isdigit()]
    avg_grade = round(sum(grade_vals) / len(grade_vals), 1) if grade_vals else None

    return jsonify({
        "exams": all_exams,
        "stats": {
            "upcoming": len(upcoming),
            "past": len(past),
            "averageGrade": avg_grade,
        },
    })


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


@app.route("/api/assistant/chat", methods=["POST"])
@require_auth
def assistant_chat():
    payload = request.get_json(silent=True) or {}
    messages = payload.get("messages", [])
    if not isinstance(messages, list):
        return jsonify({"error": "messages list olmalı"}), 400

    context_filters = payload.get("context_filters", {})
    if not isinstance(context_filters, dict):
        return jsonify({"error": "context_filters dict olmalı"}), 400

    session_id = str(payload.get("session_id", "")).strip()
    temperature = payload.get("temperature", 0.2)
    try:
        temperature = float(temperature)
    except (TypeError, ValueError):
        temperature = 0.2

    try:
        runtime = _assistant_runtime()
        out = runtime.chat(
            messages=messages,
            session_id=session_id,
            context_filters=context_filters,
            temperature=temperature,
            ilerleme_izni=_assistant_progress_allowed(),
        )
        return jsonify(out)
    except AssistantUnavailableError:
        return jsonify({"error": "assistant_unavailable"}), 503
    except Exception as e:
        return jsonify({"error": f"assistant chat failed: {e}"}), 500


@app.route("/api/assistant/stream", methods=["POST"])
@require_auth
def assistant_stream():
    access = _require_assistant_access()
    if access is not None:
        return access

    data = request.get_json(silent=True) or {}
    messages = data.get("messages") or []
    session_id = str(data.get("session_id", ""))
    force_deep = bool(data.get("force_deep", False))
    # Decided here, inside the request: generate() runs after this view has returned, where the
    # session is no longer reachable.
    ilerleme_izni = _assistant_progress_allowed()

    def generate():
        try:
            runtime = _assistant_runtime()
            for event in runtime.chat_events(
                messages=messages, session_id=session_id, force_deep=force_deep,
                ilerleme_izni=ilerleme_izni,
            ):
                name = event.pop("event")
                yield f"event: {name}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
        except AssistantUnavailableError:
            yield 'event: error\ndata: {"error":"assistant_unavailable"}\n\n'
        except Exception as exc:  # noqa: BLE001 — the stream must always close
            app.logger.error("assistant stream failed: %s", exc)
            yield f'event: error\ndata: {json.dumps({"error": str(exc)})}\n\n'
        yield "event: done\ndata: {}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no"})


@app.route("/api/assistant/plan", methods=["POST"])
@require_auth
def assistant_plan():
    payload = request.get_json(silent=True) or {}
    messages = payload.get("messages", [])
    if not isinstance(messages, list):
        return jsonify({"error": "messages list olmalı"}), 400

    context_filters = payload.get("context_filters", {})
    if not isinstance(context_filters, dict):
        return jsonify({"error": "context_filters dict olmalı"}), 400

    session_id = str(payload.get("session_id", "")).strip()

    try:
        runtime = _assistant_runtime()
        out = runtime.study_plan(
            messages=messages,
            session_id=session_id,
            context_filters=context_filters,
            ilerleme_izni=_assistant_progress_allowed(),
        )
        return jsonify(out)
    except AssistantUnavailableError:
        return jsonify({"error": "assistant_unavailable"}), 503
    except Exception as e:
        return jsonify({"error": f"assistant plan failed: {e}"}), 500


@app.route("/api/assistant/reindex", methods=["POST"])
@require_auth
def assistant_reindex():
    if not _is_assistant_admin():
        return jsonify({"error": "Forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    full = bool(payload.get("full", False))

    try:
        runtime = _assistant_runtime()
        stats = runtime.reindex(incremental=not full)
        return jsonify({"ok": True, "stats": stats})
    except AssistantUnavailableError:
        return jsonify({"ok": False, "error": "assistant_unavailable"}), 503
    except Exception as e:
        return jsonify({"ok": False, "error": f"reindex failed: {e}"}), 500


@app.route("/v1/models")
def openai_models():
    access = _require_assistant_access(api_key_only=True)
    if access is not None:
        return access

    try:
        runtime = _assistant_runtime()
        return jsonify({"object": "list", "data": runtime.models()})
    except AssistantUnavailableError:
        return jsonify({"error": "assistant_unavailable"}), 503
    except Exception as e:
        return jsonify({"error": f"models unavailable: {e}"}), 500


@app.route("/v1/chat/completions", methods=["POST"])
def openai_chat_completions():
    access = _require_assistant_access(api_key_only=True)
    if access is not None:
        return access

    payload = request.get_json(silent=True) or {}
    try:
        runtime = _assistant_runtime()
        out = runtime.openai_chat_completion(payload)
        return jsonify(out)
    except AssistantUnavailableError:
        return jsonify({"error": "assistant_unavailable"}), 503
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"chat completion failed: {e}"}), 500


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


# --- Tedy Books ---
#
# A book is a directory under books/<slug>/ holding one Markdown file per
# chapter plus an optional book.json manifest. The manifest declares the full
# table of contents up front (including chapters not written yet); the scanner
# decides which of them are actually readable by looking for a matching .md
# file. Dropping a new chapter file into the directory is the only step needed
# to publish it — no code change, no restart.

BOOKS_DIR = os.path.join(PROJECT_ROOT, "books")
BOOK_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BOOK_CHAPTER_ID_RE = re.compile(r"^[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*$")
BOOK_DEFAULT_WPM = 180
BOOK_TRANSLATION_MYMEMORY_API_URL = "https://api.mymemory.translated.net/get"
BOOK_TRANSLATION_GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
)
BOOK_TRANSLATION_GEMINI_MODEL = os.environ.get(
    "BOOK_TRANSLATION_GEMINI_MODEL", "gemini-2.5-flash"
).strip()
BOOK_TRANSLATION_MAX_BYTES = 500
BOOK_TRANSLATION_CONTEXT_MAX_BYTES = 1500


class BookTranslationProviderError(RuntimeError):
    """Raised when one translation provider cannot produce a usable result."""


def _book_translate_deepl(source_text, context):
    api_key = os.environ.get("DEEPL_API_KEY", "").strip()
    if not api_key:
        raise BookTranslationProviderError("deepl_not_configured")

    api_url = os.environ.get("DEEPL_API_URL", "").strip()
    if not api_url:
        api_url = (
            "https://api-free.deepl.com/v2/translate"
            if api_key.endswith(":fx")
            else "https://api.deepl.com/v2/translate"
        )

    provider_request = {
        "text": [source_text],
        "source_lang": "EN",
        "target_lang": "TR",
    }
    if context:
        provider_request["context"] = context

    response = http_requests.post(
        api_url,
        headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
        json=provider_request,
        timeout=8,
    )
    response.raise_for_status()
    provider_payload = response.json()
    if not isinstance(provider_payload, dict):
        raise BookTranslationProviderError("deepl_invalid_response")
    translations = provider_payload.get("translations")
    if not isinstance(translations, list) or not translations:
        raise BookTranslationProviderError("deepl_empty_response")
    first = translations[0]
    if not isinstance(first, dict):
        raise BookTranslationProviderError("deepl_invalid_translation")
    translated = html.unescape(str(first.get("text") or "")).strip()
    if not translated:
        raise BookTranslationProviderError("deepl_empty_translation")
    return translated


def _book_translate_gemini(source_text, context):
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise BookTranslationProviderError("gemini_not_configured")

    prompt = (
        "Translate the selected English text into natural Turkish for a "
        "literary reader. Use the context only to resolve meaning and tone; "
        "do not translate or summarize the context. Return only the Turkish "
        "translation, with no alternatives, labels, or explanation. If the "
        "selected text is a single word, return only its Turkish dictionary "
        "headword (lemma); never add neighboring context words or inflect it "
        "as part of the surrounding sentence.\n"
        f"Selected text: {json.dumps(source_text, ensure_ascii=False)}\n"
        f"Context: {json.dumps(context or source_text, ensure_ascii=False)}"
    )
    provider_request = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 200,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    api_url = (
        f"{BOOK_TRANSLATION_GEMINI_API_URL}/"
        f"{BOOK_TRANSLATION_GEMINI_MODEL}:generateContent"
    )
    response = http_requests.post(
        api_url,
        headers={"x-goog-api-key": api_key},
        json=provider_request,
        timeout=12,
    )
    response.raise_for_status()
    provider_payload = response.json()
    if not isinstance(provider_payload, dict):
        raise BookTranslationProviderError("gemini_invalid_response")
    candidates = provider_payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise BookTranslationProviderError("gemini_empty_response")
    first = candidates[0]
    if not isinstance(first, dict):
        raise BookTranslationProviderError("gemini_invalid_candidate")
    content = first.get("content")
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list):
        raise BookTranslationProviderError("gemini_invalid_content")
    translated = "".join(
        str(part.get("text") or "")
        for part in parts
        if isinstance(part, dict)
    ).strip()
    if translated.startswith("```"):
        translated = re.sub(
            r"^```(?:text)?\s*|\s*```$", "", translated, flags=re.IGNORECASE
        ).strip()
    if not translated:
        raise BookTranslationProviderError("gemini_empty_translation")
    return translated


def _book_translate_mymemory(source_text, context):
    # MyMemory has no separate context field. A short surrounding sentence is
    # safer than an isolated ambiguous word (for example, literary "tunnel").
    query_text = context or source_text
    if len(query_text.encode("utf-8")) > BOOK_TRANSLATION_MAX_BYTES:
        query_text = source_text

    response = http_requests.get(
        BOOK_TRANSLATION_MYMEMORY_API_URL,
        params={"q": query_text, "langpair": "en|tr", "mt": "1"},
        timeout=8,
    )
    response.raise_for_status()
    provider_payload = response.json()
    if not isinstance(provider_payload, dict):
        raise BookTranslationProviderError("mymemory_invalid_response")
    response_data = provider_payload.get("responseData")
    if not isinstance(response_data, dict):
        raise BookTranslationProviderError("mymemory_invalid_translation")
    translated = html.unescape(str(
        response_data.get("translatedText") or ""
    )).strip()
    if not translated:
        raise BookTranslationProviderError("mymemory_empty_translation")
    return translated

# word counts are expensive relative to a directory listing, so memoise them
# against (mtime_ns, size) and recompute only when a file actually changes
_BOOK_WORD_CACHE: dict[str, tuple[int, int, int]] = {}


def _book_dir(slug):
    """Resolve a book slug to its directory, refusing anything outside books/."""
    if not slug or not BOOK_SLUG_RE.match(slug):
        return None
    path = os.path.realpath(os.path.join(BOOKS_DIR, slug))
    if os.path.commonpath([path, os.path.realpath(BOOKS_DIR)]) != os.path.realpath(BOOKS_DIR):
        return None
    return path if os.path.isdir(path) else None


def _book_word_count(path):
    try:
        st = os.stat(path)
    except OSError:
        return 0
    cached = _BOOK_WORD_CACHE.get(path)
    if cached and cached[0] == st.st_mtime_ns and cached[1] == st.st_size:
        return cached[2]
    try:
        with open(path, encoding="utf-8") as f:
            count = len(f.read().split())
    except OSError:
        return 0
    _BOOK_WORD_CACHE[path] = (st.st_mtime_ns, st.st_size, count)
    return count


def _book_reading_minutes(words, wpm=BOOK_DEFAULT_WPM):
    if not words:
        return 0
    return max(1, round(words / max(1, wpm)))


def _book_chapter_file_pattern(chapter_id):
    """`B01` matches `B01_Title.md`; `EK-A` also matches `EK_A_Title.md`."""
    parts = [re.escape(p) for p in re.split(r"[-_\s]+", chapter_id) if p]
    if not parts:
        return None
    return re.compile(r"^" + r"[-_.\s]".join(parts) + r"(?:[-_.\s].*)?$", re.IGNORECASE)


def _book_markdown_files(book_dir):
    files = []
    try:
        for entry in os.scandir(book_dir):
            if entry.is_file() and entry.name.lower().endswith(".md"):
                files.append(entry.name)
    except OSError:
        return []
    return sorted(files)


def _book_manifest(slug, book_dir):
    """Manifest is optional — a bare directory of .md files is still a book."""
    manifest_path = os.path.join(book_dir, "book.json")
    manifest = {}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                manifest = loaded
        except (OSError, json.JSONDecodeError):
            app.logger.warning("books: %s/book.json okunamadı", slug)
    manifest.setdefault("slug", slug)
    manifest.setdefault("title", slug.replace("-", " ").title())
    manifest.setdefault("chapters", [])
    return manifest


_BOOK_RULES = ("---", "***", "___")
_BOOK_FRONT_MATTER_MAX_LINES = 8


def _book_is_shouted_title(line):
    """A bare title line such as `ÜÇ KAFADAR` — capitals, no sentence punctuation."""
    if len(line) > 80 or not any(ch.isalpha() for ch in line):
        return False
    if line.rstrip()[-1:] in ".!?:;,":
        return False
    return line == line.upper()


def _book_split_front_matter(text):
    """Peel a chapter's title preamble off the body.

    The reader typesets its own title page from manifest metadata, so leaving
    the source's headings in place would print the chapter title twice. Chapter
    files do not agree on one preamble shape — some use
    `# Part / ## Chapter / *credit* / ---`, others `### BÖLÜM III` followed by a
    bare shouted title and no rule — so consume whatever leading run is clearly
    title matter and stop at the first line of real prose.
    """
    lines = text.split("\n")
    front = {}
    consumed = -1
    seen = 0

    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue
        if seen >= _BOOK_FRONT_MATTER_MAX_LINES:
            break

        if line in _BOOK_RULES:
            consumed = i          # an explicit rule terminates the preamble
            break

        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            heading = line[level:].strip()
            if not heading:
                break
            if level == 1:
                front.setdefault("partHeading", heading)
            else:
                front.setdefault("chapterHeading", heading)
        elif line.startswith("*") and line.endswith("*") and not line.startswith("**"):
            front.setdefault("credit", line.strip("*").strip())
        elif _book_is_shouted_title(line) and front:
            # Only after a heading — otherwise a shouted line is body text.
            front.setdefault("chapterHeading", line)
        else:
            break                 # first line of prose: stop before it

        consumed = i
        seen += 1

    if consumed < 0 or not front:
        return {}, text
    return front, "\n".join(lines[consumed + 1:]).lstrip("\n")


def _book_chapters(slug, book_dir, manifest):
    """Merge the declared table of contents with the .md files actually present."""
    files = _book_markdown_files(book_dir)
    used = set()
    chapters = []

    for idx, entry in enumerate(manifest.get("chapters") or []):
        if not isinstance(entry, dict):
            continue
        chapter_id = str(entry.get("id") or "").strip()
        if not chapter_id or not BOOK_CHAPTER_ID_RE.match(chapter_id):
            continue
        pattern = _book_chapter_file_pattern(chapter_id)
        filename = None
        if pattern:
            for name in files:
                if name in used:
                    continue
                if pattern.match(os.path.splitext(name)[0]):
                    filename = name
                    used.add(name)
                    break
        words = _book_word_count(os.path.join(book_dir, filename)) if filename else 0
        chapters.append({
            "id": chapter_id,
            "order": int(entry.get("order") or idx + 1),
            "volume": str(entry.get("volume") or ""),
            "part": str(entry.get("part") or ""),
            "numeral": str(entry.get("numeral") or ""),
            "label": str(entry.get("label") or ""),
            "title": str(entry.get("title") or chapter_id),
            "sourceWords": int(entry.get("sourceWords") or 0),
            "available": filename is not None,
            "words": words,
            "readingMinutes": _book_reading_minutes(
                words, int(manifest.get("wordsPerMinute") or BOOK_DEFAULT_WPM)
            ),
            "_file": filename,
        })

    # Files that match no manifest entry still deserve to be readable.
    next_order = max((c["order"] for c in chapters), default=0)
    for name in files:
        if name in used:
            continue
        stem = os.path.splitext(name)[0]
        chapter_id = re.sub(r"[^A-Za-z0-9_-]+", "-", stem).strip("-") or "bolum"
        if not BOOK_CHAPTER_ID_RE.match(chapter_id):
            continue
        next_order += 1
        words = _book_word_count(os.path.join(book_dir, name))
        chapters.append({
            "id": chapter_id,
            "order": next_order,
            "volume": "", "part": "", "numeral": "", "label": "",
            "title": stem.replace("_", " ").replace("-", " ").strip(),
            "sourceWords": 0,
            "available": True,
            "words": words,
            "readingMinutes": _book_reading_minutes(
                words, int(manifest.get("wordsPerMinute") or BOOK_DEFAULT_WPM)
            ),
            "_file": name,
        })

    chapters.sort(key=lambda c: c["order"])
    return chapters


def _book_summary(manifest, chapters):
    available = [c for c in chapters if c["available"]]
    return {
        "slug": manifest.get("slug"),
        "title": manifest.get("title"),
        "subtitle": manifest.get("subtitle", ""),
        "author": manifest.get("author", ""),
        "translator": manifest.get("translator", ""),
        "publisher": manifest.get("publisher", ""),
        "edition": manifest.get("edition", ""),
        "year": manifest.get("year", ""),
        "language": manifest.get("language", ""),
        "description": manifest.get("description", ""),
        "epigraph": manifest.get("epigraph", ""),
        "cover": manifest.get("cover", {}),
        "totalChapters": len(chapters),
        "availableChapters": len(available),
        "availableWords": sum(c["words"] for c in available),
        "totalSourceWords": int(manifest.get("totalSourceWords") or 0),
        "readingMinutes": _book_reading_minutes(
            sum(c["words"] for c in available),
            int(manifest.get("wordsPerMinute") or BOOK_DEFAULT_WPM),
        ),
    }


def _book_load(slug):
    book_dir = _book_dir(slug)
    if not book_dir:
        return None, None, None
    manifest = _book_manifest(slug, book_dir)
    return book_dir, manifest, _book_chapters(slug, book_dir, manifest)


def _public_chapter(chapter):
    return {k: v for k, v in chapter.items() if not k.startswith("_")}


@app.route("/api/books")
@require_auth
def books_list():
    books = []
    if os.path.isdir(BOOKS_DIR):
        for name in sorted(os.listdir(BOOKS_DIR)):
            book_dir, manifest, chapters = _book_load(name)
            if not book_dir or not chapters:
                continue
            books.append(_book_summary(manifest, chapters))
    return jsonify({"books": books})


@app.route("/api/books/translate", methods=["POST"])
@require_auth
def book_translate():
    payload = request.get_json(silent=True) or {}
    source_text = re.sub(
        r"\s+", " ", str(payload.get("text") or "")
    ).strip()
    context = re.sub(
        r"\s+", " ", str(payload.get("context") or "")
    ).strip()
    if not source_text:
        return jsonify({"error": "selection_required"}), 400
    if len(source_text.encode("utf-8")) > BOOK_TRANSLATION_MAX_BYTES:
        return jsonify({
            "error": "selection_too_long",
            "maxBytes": BOOK_TRANSLATION_MAX_BYTES,
        }), 413
    if len(context.encode("utf-8")) > BOOK_TRANSLATION_CONTEXT_MAX_BYTES:
        return jsonify({
            "error": "context_too_long",
            "maxBytes": BOOK_TRANSLATION_CONTEXT_MAX_BYTES,
        }), 413

    providers = (
        ("DeepL", _book_translate_deepl),
        ("Gemini 2.5 Flash", _book_translate_gemini),
        ("MyMemory", _book_translate_mymemory),
    )
    for provider_name, translate in providers:
        try:
            translated = translate(source_text, context)
        except (
            BookTranslationProviderError,
            http_requests.RequestException,
            ValueError,
        ):
            continue
        return jsonify({
            "sourceText": source_text,
            "translatedText": translated,
            "sourceLanguage": "en",
            "targetLanguage": "tr",
            "provider": provider_name,
        })

    return jsonify({"error": "translation_provider_unavailable"}), 502


@app.route("/api/books/<slug>")
@require_auth
def book_detail(slug):
    book_dir, manifest, chapters = _book_load(slug)
    if not book_dir:
        return jsonify({"error": "Kitap bulunamadı"}), 404
    payload = _book_summary(manifest, chapters)
    payload["chapters"] = [_public_chapter(c) for c in chapters]
    return jsonify(payload)


@app.route("/api/books/<slug>/chapters/<chapter_id>")
@require_auth
def book_chapter(slug, chapter_id):
    book_dir, manifest, chapters = _book_load(slug)
    if not book_dir:
        return jsonify({"error": "Kitap bulunamadı"}), 404

    readable = [c for c in chapters if c["available"]]
    idx = next((i for i, c in enumerate(readable) if c["id"] == chapter_id), -1)
    if idx < 0:
        return jsonify({"error": "Bölüm bulunamadı"}), 404

    chapter = readable[idx]
    try:
        with open(os.path.join(book_dir, chapter["_file"]), encoding="utf-8") as f:
            raw = f.read()
    except OSError:
        return jsonify({"error": "Bölüm okunamadı"}), 500

    front, body = _book_split_front_matter(raw)
    payload = _public_chapter(chapter)
    payload["content"] = body
    payload["credit"] = front.get("credit", "")
    # Not every chapter file names its volume; the manifest always does.
    payload["partHeading"] = front.get("partHeading") or chapter["part"]

    def nav(target):
        if target is None:
            return None
        return {"id": target["id"], "title": target["title"], "label": target["label"]}

    return jsonify({
        "book": _book_summary(manifest, chapters),
        "chapter": payload,
        "prev": nav(readable[idx - 1] if idx > 0 else None),
        "next": nav(readable[idx + 1] if idx + 1 < len(readable) else None),
        "position": {"index": idx + 1, "total": len(readable)},
    })


# --- Reading position (per profile) ---
#
# Reader settings stay device-local, but the bookmark belongs to the person, not
# to the browser: a profile that opens Tedy Books anywhere resumes where it left
# off, and two profiles sharing a device never see each other's position.

BOOK_PROGRESS_FILE = os.path.join(OUTPUT_DIR, "book_progress.json")
BOOK_PROGRESS_MAX_BOOKS = 200
BOOK_PROGRESS_MAX_CHAPTERS = 1000


def _load_book_progress_store():
    if not os.path.exists(BOOK_PROGRESS_FILE):
        return {}
    try:
        with open(BOOK_PROGRESS_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _normalize_progress_chapter(value):
    if not isinstance(value, dict):
        return None
    try:
        ratio = float(value.get("ratio") or 0)
    except (TypeError, ValueError):
        ratio = 0.0
    if ratio != ratio:  # NaN
        ratio = 0.0
    return {"ratio": round(min(1.0, max(0.0, ratio)), 4), "done": bool(value.get("done"))}


def _normalize_progress_books(raw):
    """Coerce a stored or client-supplied map into the persisted shape.

    The client payload is untrusted, so slugs and chapter ids go through the
    same regexes the book routes use and anything unrecognised is dropped
    rather than stored.
    """
    books = {}
    if not isinstance(raw, dict):
        return books
    for slug, entry in list(raw.items())[:BOOK_PROGRESS_MAX_BOOKS]:
        if not isinstance(slug, str) or not BOOK_SLUG_RE.match(slug):
            continue
        if not isinstance(entry, dict):
            continue
        chapters = {}
        raw_chapters = entry.get("chapters")
        if isinstance(raw_chapters, dict):
            for chapter_id, chapter in list(raw_chapters.items())[:BOOK_PROGRESS_MAX_CHAPTERS]:
                if not isinstance(chapter_id, str) or not BOOK_CHAPTER_ID_RE.match(chapter_id):
                    continue
                normalized = _normalize_progress_chapter(chapter)
                if normalized:
                    chapters[chapter_id] = normalized
        last = entry.get("lastChapterId")
        updated = entry.get("updatedAt")
        books[slug] = {
            "lastChapterId": (
                last if isinstance(last, str) and BOOK_CHAPTER_ID_RE.match(last) else None
            ),
            "updatedAt": (
                updated if isinstance(updated, str) and 0 < len(updated) <= 40 else None
            ),
            "chapters": chapters,
        }
    return books


def _progress_is_newer(candidate, current):
    a = _parse_iso_datetime(candidate.get("updatedAt"))
    b = _parse_iso_datetime(current.get("updatedAt"))
    if a is None:
        return False
    if b is None:
        return True
    try:
        return a >= b
    except TypeError:  # one side carried a timezone and the other did not
        return str(candidate.get("updatedAt")) >= str(current.get("updatedAt"))


def _merge_book_progress(stored, incoming):
    """Per book, the more recently touched copy wins; new books are added."""
    merged = dict(stored)
    for slug, entry in incoming.items():
        current = merged.get(slug)
        if not isinstance(current, dict) or _progress_is_newer(entry, current):
            merged[slug] = entry
    return merged


def _book_progress_for(email):
    return _normalize_progress_books(_load_book_progress_store().get(email) or {})


@app.route("/api/books/progress")
@require_auth
def book_progress_get():
    email = _current_user_email()
    if not email:
        return jsonify({"error": "session_required"}), 403
    return jsonify({"books": _book_progress_for(email)})


@app.route("/api/books/progress", methods=["POST"])
@require_auth
def book_progress_save():
    email = _current_user_email()
    if not email:
        return jsonify({"error": "session_required"}), 403
    payload = request.get_json(silent=True) or {}
    incoming = _normalize_progress_books(payload.get("books"))
    store = _load_book_progress_store()
    merged = _merge_book_progress(
        _normalize_progress_books(store.get(email) or {}), incoming
    )
    store[email] = merged
    try:
        atomic_json_dump(store, BOOK_PROGRESS_FILE)
    except OSError:
        return jsonify({"error": "progress_write_failed"}), 500
    return jsonify({"books": merged})


# --- Modules: edupedia catalog, viewing tickets and the progress bridge (spec §5.3-§5.5) ---
# ted-mcp writes output/modules/ and output/edupedia_drafts/; the dashboard only reads them.
# output/module_progress.json has one writer (this app) but two gunicorn worker processes,
# so module_progress.ProgressStore serialises every read-modify-write with fcntl.flock.

MODULE_VIEWER_BASE_URL = os.environ.get("EDUPEDIA_VIEWER_BASE_URL", "https://modul.tedy.online").rstrip("/")
MODULE_PROGRESS_MAX_BYTES = 4096
MODULE_FRAME_CSP = "frame-src https://modul.tedy.online https://accounts.google.com"
_MODULE_CARD_FIELDS = ("slug", "version", "title", "subject", "gradeLevel", "mode", "outcomes", "ted_link",
                       "created_at", "gates")


def _module_person():
    """Session email of a full-role member. API keys and the test bypass are not people."""
    email = str(session.get("user_email", "") or "").lower().strip()
    return email if email and USER_ROLES.get(email) == ROLE_FULL else None


def _module_active_record(slug, version):
    if not module_store.valid_slug(slug) or not module_store.valid_version(version):
        return None
    record = module_store.find_record(OUTPUT_DIR, slug, version)
    return record if record and record.get("status") == "active" else None


def _module_ticket_secret():
    return os.environ.get("EDUPEDIA_TICKET_SECRET", "").encode("utf-8")


def _module_progress_store():
    return module_progress.ProgressStore(os.path.join(OUTPUT_DIR, "module_progress.json"))


def _no_store(payload, status=200):
    response = jsonify(payload)
    response.status_code = status
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/api/modules")
@require_auth
def modules_list():
    rows = module_store.latest_active(module_store.read_catalog(OUTPUT_DIR))
    return jsonify({"moduller": [{key: row.get(key) for key in _MODULE_CARD_FIELDS} for row in rows]})


@app.route("/api/modules/<slug>/v<int:version>/ticket")
@require_auth
def module_ticket_issue(slug, version):
    email = _module_person()
    if not email:
        return jsonify({"error": "session_required"}), 403
    if _module_active_record(slug, version) is None:
        return jsonify({"error": "not_found"}), 404
    try:
        ticket = module_ticket.issue_module(_module_ticket_secret(), MODULE_VIEWER_BASE_URL, email, slug, version,
                                            time.time())
    except module_ticket.TicketConfigError:
        return jsonify({"error": "ticket_unconfigured"}), 503
    return _no_store(ticket)


@app.route("/api/modules/taslak/<taslak_id>/ticket")
@require_auth
def module_draft_ticket_issue(taslak_id):
    email = _module_person()
    if not email:
        return jsonify({"error": "session_required"}), 403
    if module_store.read_draft(OUTPUT_DIR, taslak_id) is None:
        return jsonify({"error": "not_found"}), 404
    try:
        ticket = module_ticket.issue_draft(_module_ticket_secret(), MODULE_VIEWER_BASE_URL, email, taslak_id, time.time())
    except module_ticket.TicketConfigError:
        return jsonify({"error": "ticket_unconfigured"}), 503
    return _no_store(ticket)


@app.route("/api/modules/<slug>/progress")
@require_auth
def module_progress_get(slug):
    email = _module_person()
    if not email:
        return jsonify({"error": "session_required"}), 403
    version = request.args.get("version", type=int)
    if not module_store.valid_slug(slug) or not module_store.valid_version(version):
        return jsonify({"error": "gecersiz_olay:modul"}), 400
    if _module_active_record(slug, version) is None:
        return jsonify({"error": "not_found"}), 404
    state = _module_progress_store().state_for(module_ticket.email_hash(email), slug, version)
    return _no_store({"state": state})


@app.route("/api/modules/<slug>/progress", methods=["POST"])
@require_auth
def module_progress_save(slug):
    email = _module_person()
    if not email:
        return jsonify({"error": "session_required"}), 403
    if (request.content_length or 0) > MODULE_PROGRESS_MAX_BYTES:
        return jsonify({"error": "cok_buyuk"}), 413
    raw = request.get_data(cache=True)
    if len(raw) > MODULE_PROGRESS_MAX_BYTES:
        return jsonify({"error": "cok_buyuk"}), 413
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "gecersiz_olay:json"}), 400
    version = payload.get("version")
    if not module_store.valid_slug(slug) or not module_store.valid_version(version):
        return jsonify({"error": "gecersiz_olay:modul"}), 400
    if _module_active_record(slug, version) is None:
        return jsonify({"error": "not_found"}), 404
    try:
        event = module_progress.validate_event(payload, slug, version)
    except module_progress.ProgressEventError as exc:
        return jsonify({"error": f"gecersiz_olay:{exc.reason}"}), 400
    try:
        state = _module_progress_store().record(module_ticket.email_hash(email), slug, version, event, time.time())
    except OSError:
        return jsonify({"error": "progress_write_failed"}), 500
    return _no_store({"ok": True, "state": state})


@app.after_request
def _module_frame_policy(response):
    # Only frame-src: the dashboard keeps its existing font and Google Sign-In loading (plan K-P15).
    response.headers.setdefault("Content-Security-Policy", MODULE_FRAME_CSP)
    return response


# --- SPA static serving (production build) ---
@app.route("/")
@app.route("/<path:path>")
def serve_spa(path=""):
    normalized = str(path or "").lstrip("/")
    if normalized.startswith("api/") or normalized.startswith("v1/"):
        return jsonify({"error": "Not found"}), 404

    if normalized and os.path.exists(os.path.join(DIST_DIR, normalized)):
        return send_from_directory(DIST_DIR, normalized)

    # Missing static assets (fonts/js/css/images) should be hard 404, not index.html.
    if normalized and "." in os.path.basename(normalized):
        return ("Not Found", 404)

    index = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index):
        return send_from_directory(DIST_DIR, "index.html")
    return jsonify({"error": "Dashboard not built. Run: cd dashboard && npm run build"}), 404


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TED Dashboard API")
    parser.add_argument("--generate-key", action="store_true", help="Generate a new API key")
    args = parser.parse_args()
    if args.generate_key:
        key = f"tdyK_{secrets.token_urlsafe(32)}"
        print(f"\nNew API key: {key}\n")
        print("Add to .env:  API_KEYS=myapp:" + key)
        print("Or append:    API_KEYS=...existing...,myapp:" + key)
    else:
        app.run(host="0.0.0.0", port=8085, debug=True)
