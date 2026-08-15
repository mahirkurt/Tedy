"""Sync scraped TED portal data to Google Calendar & Drive.

Calendar-only sync: ders programi, takvim (timed events), OGEP.
Homework, grades, announcements, and course content go to Classroom.
"""
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src.json_utils import atomic_json_dump

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
TOKEN_FILE = os.path.join(PROJECT_ROOT, "token.json")
DATA_FILE = os.path.join(PROJECT_ROOT, "output", "scraped_data.json")

TIMEZONE = "Europe/Istanbul"

# Color IDs for Google Calendar (1-11)
COLORS = {
    "ders": "1",        # Lavender - regular class
    "takim": "3",       # Purple - team/club
    "sinav": "4",       # Flamingo - exam
    "etkinlik": "2",    # Sage - activity
    "ogep": "6",        # Tangerine - ÖGEP
}

# Canonical course names and their aliases
COURSE_ALIASES = {
    "Fransızca": [
        "İkinci Yabancı Dil",
        "İkinci Yabancı Dil (Fransızca)",
        "2. Yabancı Dil (F)",
        "2. Yabancı Diller",
    ],
    "Din Kültürü": [
        "Din Kültürü ve Ahlak Bilgisi",
        "DKAB",
    ],
    "Beden Eğitimi": [
        "Beden Eğitimi ve Spor",
    ],
    "İngilizce": [
        "İngilizce (Language)",
        "İngilizce Language",
        "İngilizce (2)",
        "İngilizce Literature",
        "İngilizce (Literature)",
    ],
    "Bilişim": [
        "Bilişim Teknolojileri",
    ],
    "Ahlak ve Yurttaşlık": [
        "Ahlak ve Yurttaşlık Eğitimi",
    ],
}

# Build reverse lookup: alias -> canonical
_ALIAS_LOOKUP = {}
for _canonical, _aliases in COURSE_ALIASES.items():
    _ALIAS_LOOKUP[_canonical] = _canonical
    for _alias in _aliases:
        _ALIAS_LOOKUP[_alias] = _canonical
_ALIAS_LONGEST_FIRST = sorted(_ALIAS_LOOKUP.keys(), key=len, reverse=True)

# Keywords for takvim event color classification (substring match)
TAKVIM_DERS_KEYWORDS = (
    "ders", "matematik", "türkçe", "fen", "sosyal",
    "din kültürü", "ingilizce", "english", "français", "fransızca",
    "bilişim", "görsel", "müzik", "beden", "ahlak", "literature",
)


def normalize_course(name):
    """Normalize a course name to its canonical form.

    1. Exact match in alias lookup
    2. Prefix match against known aliases (longest first)
    3. Strip parenthesized suffix, retry
    4. Return original if no match
    """
    name = name.strip()
    if not name:
        return name

    # Exact match
    if name in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[name]

    # Prefix match: handles "İngilizce (Literature) (i-403 (İngilizce))"
    # by matching the known alias "İngilizce (Literature)" as a prefix
    for alias in _ALIAS_LONGEST_FIRST:
        if name.startswith(alias) and (
            len(name) == len(alias) or name[len(alias)] == " "
        ):
            return _ALIAS_LOOKUP[alias]

    # Strip trailing parenthesized content and retry
    stripped = re.sub(r"\s*\(.*\)\s*$", "", name).strip()
    if stripped != name and stripped in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[stripped]

    return stripped if stripped != name else name


def get_services(token_file=None):
    """Build Google API service clients from token file.

    Returns (calendar_service, drive_service).
    """
    token_file = token_file or TOKEN_FILE
    creds = Credentials.from_authorized_user_file(token_file)
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_file, "w") as f:
            f.write(creds.to_json())
    cal = build("calendar", "v3", credentials=creds)
    drive = build("drive", "v3", credentials=creds)
    return cal, drive


def get_or_create_calendar(cal_service, summary):
    """Get existing or create a new secondary calendar."""
    calendars = cal_service.calendarList().list().execute()
    for c in calendars.get("items", []):
        if c["summary"] == summary:
            print(f"  Calendar exists: {summary}")
            return c["id"]

    body = {"summary": summary, "timeZone": TIMEZONE}
    created = cal_service.calendars().insert(body=body).execute()
    print(f"  Calendar created: {summary} ({created['id'][:20]}...)")
    return created["id"]


def fetch_existing_events(cal_service, cal_id):
    """Fetch all events created by this script (source=ted-portal).

    Returns dict: {(summary, start_str): event_id}
    """
    existing = {}
    page_token = None
    while True:
        result = cal_service.events().list(
            calendarId=cal_id,
            privateExtendedProperty="source=ted-portal",
            maxResults=2500,
            pageToken=page_token,
            singleEvents=True,
        ).execute()
        for ev in result.get("items", []):
            summary = ev.get("summary", "")
            start = ev.get("start", {})
            raw = start.get("dateTime", start.get("date", ""))
            existing[(summary, _normalize_dt(raw))] = ev["id"]
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return existing


SOURCE_TAG = {"private": {"source": "ted-portal"}}


def _normalize_dt(s):
    """Normalize datetime to local naive ISO for comparison.

    All events use Europe/Istanbul, so we strip offsets and
    convert UTC (Z) to Istanbul (+03:00) before stripping.

    '2026-01-12T08:00:00+03:00' -> '2026-01-12T08:00:00'
    '2026-01-12T16:00:00Z'      -> '2026-01-12T19:00:00'
    '2026-01-12T08:00:00'       -> '2026-01-12T08:00:00'
    '2026-01-12'                -> '2026-01-12'
    """
    if not s or "T" not in s:
        return s
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo:
            ist = timezone(timedelta(hours=3))
            dt = dt.astimezone(ist).replace(tzinfo=None)
        return dt.isoformat()
    except (ValueError, TypeError):
        return s


def _api_call_with_retry(fn, max_retries=5, base_delay=3):
    """Call fn() with retry on transient HTTP errors (403, 429, 500, 503).

    Note: 403 is included because Google Classroom API uses it for rate
    limiting in addition to permission errors.
    """
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            status = getattr(getattr(e, "resp", None), "status", 0)
            if status in (403, 429, 500, 503) and attempt < max_retries - 1:
                time.sleep(base_delay * (2 ** attempt))
                continue
            return None
    return None


def upsert_event(cal_service, cal_id, event_body, existing_events):
    """Insert or skip a calendar event. Returns 'added', 'exists', or 'error'."""
    summary = event_body.get("summary", "")
    start = event_body.get("start", {})
    start_str = _normalize_dt(start.get("dateTime", start.get("date", "")))
    key = (summary, start_str)

    event_body["extendedProperties"] = SOURCE_TAG

    if key in existing_events:
        return "exists"

    result = _api_call_with_retry(
        lambda: cal_service.events().insert(
            calendarId=cal_id, body=event_body,
        ).execute()
    )
    return "added" if result else "error"


def parse_tr_datetime(s):
    """Parse Turkish date formats like '20.02.2026 08:00'."""
    s = s.strip()
    for fmt in ["%d.%m.%Y %H:%M", "%d.%m.%Y"]:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def parse_week_range(week_label):
    """Parse week label like '22. Hafta 16 Şub. - 22 Şub.' to date range."""
    TR_MONTHS = {
        "Oca": 1, "Şub": 2, "Mar": 3, "Nis": 4, "May": 5, "Haz": 6,
        "Tem": 7, "Ağu": 8, "Eyl": 9, "Eki": 10, "Kas": 11, "Ara": 12,
    }
    # Match patterns like "16 Şub." or "02 Şub."
    matches = re.findall(r"(\d{1,2})\s+(\w{3})\.", week_label)
    if len(matches) >= 2:
        day1, mon1 = int(matches[0][0]), TR_MONTHS.get(matches[0][1])
        day2, mon2 = int(matches[1][0]), TR_MONTHS.get(matches[1][1])
        if mon1 and mon2:
            year = datetime.now().year
            start = datetime(year, mon1, day1)
            end = datetime(year, mon2, day2)
            return start, end
    return None, None


# =============================================================================
# SYNC: DERS PROGRAMI -> GOOGLE CALENDAR
# =============================================================================
def sync_ders_programi(cal_service, data, cal_id, existing_events):
    """Sync weekly class schedule to Google Calendar.

    Table format (headerless):
      Row 0: ['', 'Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', '', 'Cuma', ...]
      Row N: ['N. Ders\\n08:00 - 08:40', 'Ders (sınıf)\\nÖğretmen', ...]
      Break rows: ['08:40 - 08:55', 'Kahvaltı', ...]
    """
    print("\n[1/3] Ders Programı -> Calendar")
    weeks = data.get("ders_programi", [])
    events_added = 0
    events_skipped = 0

    for week in weeks:
        week_label = week.get("week_label", "")
        week_start, _ = parse_week_range(week_label)
        if not week_start:
            print(f"  Skipping week (can't parse): {week_label}")
            continue

        schedule = week.get("schedule", {})
        rows = schedule.get("rows", [])
        if not rows or len(rows) < 2:
            continue

        # Row 0 has day names; build day_name -> column_index map
        day_row = rows[0]
        DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
        day_col_map = {}  # day_name -> col_index
        for col_idx, cell in enumerate(day_row):
            for day in DAYS:
                if day in cell:
                    day_col_map[day] = col_idx
                    break

        print(f"  Week: {week_label} (days at cols: {day_col_map})")

        # Iterate lesson rows (skip row 0 = day headers)
        for row in rows[1:]:
            if not isinstance(row, list) or len(row) < 2:
                continue

            # First cell: "N. Ders\nHH:MM - HH:MM" or "HH:MM - HH:MM" (break)
            first_cell = row[0]
            time_match = re.search(r"(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})", first_cell)
            if not time_match:
                continue

            # Skip break rows (Kahvaltı, Öğle Yemeği, etc.)
            is_lesson = "Ders" in first_cell
            if not is_lesson:
                continue

            h1, m1 = int(time_match.group(1)), int(time_match.group(2))
            h2, m2 = int(time_match.group(3)), int(time_match.group(4))

            for day_name, col_idx in day_col_map.items():
                if col_idx >= len(row):
                    continue
                cell_text = row[col_idx].strip()
                if not cell_text or len(cell_text) < 3:
                    continue

                # Parse: "Ders Adı (sınıf)\nÖğretmen"
                parts = cell_text.split("\n")
                lesson_full = parts[0].strip()
                teacher = parts[1].strip() if len(parts) > 1 else ""

                # Extract lesson name (before parenthesis)
                lesson_name = normalize_course(lesson_full)

                day_offset = DAYS.index(day_name)
                day_date = week_start + timedelta(days=day_offset)

                event = {
                    "summary": f"{lesson_name}",
                    "description": f"{lesson_full}\n{teacher}".strip(),
                    "start": {
                        "dateTime": day_date.replace(hour=h1, minute=m1).isoformat(),
                        "timeZone": TIMEZONE,
                    },
                    "end": {
                        "dateTime": day_date.replace(hour=h2, minute=m2).isoformat(),
                        "timeZone": TIMEZONE,
                    },
                    "colorId": COLORS["ders"],
                    "location": "TED Rönesans Koleji",
                    "reminders": {
                        "useDefault": False,
                        "overrides": [
                            {"method": "popup", "minutes": 15},
                        ],
                    },
                }
                result = upsert_event(cal_service, cal_id, event, existing_events)
                if result == "added":
                    events_added += 1
                elif result == "exists":
                    events_skipped += 1

    print(f"  Ders: +{events_added} added, ={events_skipped} skipped")
    return events_added


# =============================================================================
# SYNC: TAKVİM EVENTS -> GOOGLE CALENDAR (timed events only)
# =============================================================================
def sync_takvim(cal_service, data, cal_id, existing_events):
    """Sync academic calendar events (from FullCalendar JS API data).

    Only timed events are synced to Calendar. All-day events are skipped
    (they go to Classroom as announcements). ÖGEP sessions are skipped
    (they are synced by sync_ogep to avoid duplicates).

    Each event has: title, start (ISO), end (ISO), allDay (bool),
    backgroundColor, extendedProps.
    """
    print("\n[2/3] Akademik Takvim -> Calendar")
    events = data.get("takvim", [])
    events_added = 0
    events_skipped = 0
    all_day_skipped = 0
    ogep_skipped = 0

    # Build set of ÖGEP session titles for dedup with sync_ogep
    ogep_titles = set()
    for r in data.get("ogep", {}).get("sessions", {}).get("rows", []):
        name = r.get("ÖGEP (Öğrenci Gelişim Programı)", "")
        if name:
            ogep_titles.add(name)

    for ev in events:
        title = ev.get("title", "").strip()
        start = ev.get("start", "")
        end = ev.get("end", "")
        all_day = ev.get("allDay", False)

        if not title or not start:
            continue

        # Skip all-day events (they go to Classroom announcements)
        if all_day:
            all_day_skipped += 1
            continue

        # Skip ÖGEP sessions (handled by sync_ogep)
        if any(t in title for t in ogep_titles) or "ögep" in title.lower():
            ogep_skipped += 1
            continue

        # Only timed events from here on

        # Determine color by keyword
        color = COLORS["etkinlik"]
        lower = title.lower()
        if "sınav" in lower or "test" in lower or "exam" in lower:
            color = COLORS["sinav"]
        elif "ögep" in lower or "ogep" in lower:
            color = COLORS["ogep"]
        elif any(w in lower for w in TAKVIM_DERS_KEYWORDS):
            color = COLORS["ders"]
        elif "gezi" in lower or "müze" in lower or "trip" in lower:
            color = COLORS["takim"]

        event = {
            "summary": title,
            "colorId": color,
            "start": {
                "dateTime": start,
                "timeZone": TIMEZONE,
            },
            "end": {
                "dateTime": end if end else start,
                "timeZone": TIMEZONE,
            },
        }

        result = upsert_event(cal_service, cal_id, event, existing_events)
        if result == "added":
            events_added += 1
        elif result == "exists":
            events_skipped += 1

    print(f"  Takvim: +{events_added} added, "
          f"={events_skipped} skipped, "
          f"~{all_day_skipped} all-day -> Classroom, "
          f"~{ogep_skipped} ÖGEP -> sync_ogep")
    return events_added


# =============================================================================
# SYNC: ÖGEP -> GOOGLE CALENDAR
# =============================================================================
def sync_ogep(cal_service, data, cal_id, existing_events):
    """Sync ÖGEP sessions to Google Calendar."""
    print("\n[3/3] ÖGEP -> Calendar")
    rows = data.get("ogep", {}).get("sessions", {}).get("rows", [])
    added = 0
    skipped = 0

    for row in rows:
        name = row.get("ÖGEP (Öğrenci Gelişim Programı)", "")
        start_str = row.get("Çalışma Başlangıç", "")
        end_str = row.get("Çalışma Bitiş", "")
        katilim = row.get("Katılım Durumu", "")
        link = row.get("Teams Link", "")

        start_dt = parse_tr_datetime(start_str)
        end_dt = parse_tr_datetime(end_str)
        if not start_dt or not end_dt:
            continue

        desc = f"Katılım: {katilim}" if katilim else ""
        location = "TED Rönesans Koleji" if link == "Yüz Yüze" else (link if link else "")

        event = {
            "summary": f"ÖGEP: {name}",
            "description": desc,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": TIMEZONE},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": TIMEZONE},
            "colorId": COLORS["ogep"],
            "location": location,
        }
        result = upsert_event(cal_service, cal_id, event, existing_events)
        if result == "added":
            added += 1
        elif result == "exists":
            skipped += 1

    print(f"  OGEP: +{added} added, ={skipped} skipped")
    return added


# =============================================================================
# SYNC: ATTACHMENTS -> GOOGLE DRIVE
# =============================================================================
UPLOADED_FILES = os.path.join(PROJECT_ROOT, "output",
                              "uploaded_files.json")


def sync_attachments_to_drive(drive_service, data):
    """Download homework attachments and upload to Google Drive.

    Returns the uploaded dict: {url: {id, link, ders}}.
    """
    print("\n[Drive] Attachments -> Google Drive")

    hw_data = data.get("odevlerim", {})
    rows = hw_data.get("homework", {}).get("rows", [])

    # Collect all attachments
    attachments = []
    for row in rows:
        detail = row.get("detail", {})
        for att in detail.get("attachments", []):
            url = att.get("url", "")
            name = att.get("name", "")
            ders = normalize_course(row.get("Ders Adı", "Genel"))
            if url and name:
                attachments.append({
                    "url": url, "name": name, "ders": ders,
                })

    if not attachments:
        print("  No attachments found, skipping")
        return {}

    # Load already-uploaded files
    uploaded = {}
    if os.path.exists(UPLOADED_FILES):
        with open(UPLOADED_FILES) as f:
            uploaded = json.load(f)

    # Get or create root folder
    folder_id = _get_or_create_folder(
        drive_service, "Ödevler"
    )

    added = 0
    skipped = 0
    for att in attachments:
        if att["url"] in uploaded:
            skipped += 1
            continue

        try:
            # Download file
            import requests as req
            resp = req.get(att["url"], timeout=30)
            if resp.status_code != 200:
                continue

            # Get or create subject folder
            subj_folder = _get_or_create_folder(
                drive_service, att["ders"],
                parent_id=folder_id
            )

            # Upload to Drive
            from googleapiclient.http import MediaInMemoryUpload
            media = MediaInMemoryUpload(
                resp.content,
                mimetype=resp.headers.get(
                    "Content-Type", "application/octet-stream"
                ),
            )
            file_meta = {
                "name": att["name"],
                "parents": [subj_folder],
            }
            result = drive_service.files().create(
                body=file_meta, media_body=media,
                fields="id,webViewLink",
            ).execute()

            uploaded[att["url"]] = {
                "id": result["id"],
                "link": result.get("webViewLink", ""),
                "ders": att["ders"],
            }
            added += 1
        except Exception as e:
            print(f"  Error uploading {att['name']}: {e}")

    # Save uploaded files tracker (atomic)
    atomic_json_dump(uploaded, UPLOADED_FILES)

    print(f"  Drive: +{added} uploaded, ={skipped} skipped")
    return uploaded


def _get_or_create_folder(drive_service, name, parent_id=None):
    """Get or create a Drive folder by name."""
    q = (f"name='{name}' and "
         f"mimeType='application/vnd.google-apps.folder' and "
         f"trashed=false")
    if parent_id:
        q += f" and '{parent_id}' in parents"

    results = drive_service.files().list(
        q=q, spaces="drive", fields="files(id)",
    ).execute()
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        meta["parents"] = [parent_id]

    folder = drive_service.files().create(
        body=meta, fields="id",
    ).execute()
    return folder["id"]


# =============================================================================
# MAIN (standalone usage)
# =============================================================================
def _sync_account(data, token_file, label):
    """Run Calendar + Drive sync for a single Google account."""
    print(f"\n{'=' * 50}")
    print(f"SYNC: {label}")
    print(f"{'=' * 50}")

    print("Connecting to Google APIs...")
    cal_svc, drive_svc = get_services(token_file=token_file)

    print("\nSetting up Google Calendar...")
    cal_id = get_or_create_calendar(cal_svc, "TED Rönesans")

    print("Fetching existing events for dedup...")
    existing_events = fetch_existing_events(cal_svc, cal_id)
    print(f"  Found {len(existing_events)} existing events")

    sync_ders_programi(cal_svc, data, cal_id, existing_events)
    sync_takvim(cal_svc, data, cal_id, existing_events)
    sync_ogep(cal_svc, data, cal_id, existing_events)
    sync_attachments_to_drive(drive_svc, data)


def main():
    print("Loading scraped data...")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Sync primary account (Calendar + Drive)
    _sync_account(data, TOKEN_FILE, "Primary Account")

    print("\n" + "=" * 50)
    print("SYNC COMPLETE!")
    print("=" * 50)


if __name__ == "__main__":
    main()
