"""Classify scraped TED portal data and sync to Google Calendar & Tasks."""
import json
import os
import re
from datetime import datetime, timedelta, timezone

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
TOKEN_FILE = os.path.join(PROJECT_ROOT, "token.json")
DATA_FILE = os.path.join(PROJECT_ROOT, "output", "scraped_data.json")

TIMEZONE = "Europe/Istanbul"

# Color IDs for Google Calendar (1-11)
COLORS = {
    "ders": "1",        # Lavender - regular class
    "odev": "11",       # Red - homework due
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
    ],
    "İngilizce Literature": [
        "İngilizce (Literature)",
    ],
    "Bilişim": [
        "Bilişim Teknolojileri",
    ],
}

# Build reverse lookup: alias -> canonical
_ALIAS_LOOKUP = {}
for _canonical, _aliases in COURSE_ALIASES.items():
    _ALIAS_LOOKUP[_canonical] = _canonical
    for _alias in _aliases:
        _ALIAS_LOOKUP[_alias] = _canonical

# Keywords for takvim event color classification (substring match)
TAKVIM_DERS_KEYWORDS = (
    "ders", "matematik", "türkçe", "fen", "sosyal",
    "din kültürü", "ingilizce", "english", "français", "fransızca",
    "bilişim", "görsel", "müzik", "beden", "ahlak", "literature",
)


def normalize_course(name):
    """Normalize a course name to its canonical form.

    1. Exact match in alias lookup
    2. Strip parenthesized suffix, retry
    3. Return original if no match
    """
    name = name.strip()
    if not name:
        return name

    # Exact match
    if name in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[name]

    # Strip trailing parenthesized content and retry
    stripped = re.sub(r"\s*\(.*\)\s*$", "", name).strip()
    if stripped != name and stripped in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[stripped]

    return stripped if stripped != name else name


def get_services():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE)
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    cal = build("calendar", "v3", credentials=creds)
    tasks = build("tasks", "v1", credentials=creds)
    sheets = build("sheets", "v4", credentials=creds)
    drive = build("drive", "v3", credentials=creds)
    return cal, tasks, sheets, drive


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


def get_or_create_task_list(tasks_service, title):
    """Get existing or create a task list."""
    lists = tasks_service.tasklists().list().execute()
    for t in lists.get("items", []):
        if t["title"] == title:
            print(f"  Task list exists: {title}")
            return t["id"]

    created = tasks_service.tasklists().insert(body={"title": title}).execute()
    print(f"  Task list created: {title}")
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


def fetch_existing_tasks(tasks_service, task_list_id):
    """Fetch all tasks from the TED task list.

    Returns dict: {(title, due): task_id}
    """
    existing = {}
    page_token = None
    while True:
        result = tasks_service.tasks().list(
            tasklist=task_list_id,
            maxResults=100,
            pageToken=page_token,
            showCompleted=True,
            showHidden=True,
        ).execute()
        for t in result.get("items", []):
            title = t.get("title", "")
            due = t.get("due", "")
            existing[(title, due)] = t["id"]
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


def upsert_event(cal_service, cal_id, event_body, existing_events):
    """Insert or skip a calendar event. Returns 'added', 'exists', or 'error'."""
    summary = event_body.get("summary", "")
    start = event_body.get("start", {})
    start_str = _normalize_dt(start.get("dateTime", start.get("date", "")))
    key = (summary, start_str)

    event_body["extendedProperties"] = SOURCE_TAG

    if key in existing_events:
        return "exists"

    try:
        cal_service.events().insert(calendarId=cal_id, body=event_body).execute()
        return "added"
    except Exception:
        return "error"


def upsert_task(tasks_service, task_list_id, task_body, existing_tasks,
                update_if_changed=False):
    """Insert, skip, or update a task.

    When update_if_changed=True, compares notes and updates if different.
    Returns 'added', 'exists', 'updated', or 'error'.
    """
    title = task_body.get("title", "")
    due = task_body.get("due", "")
    key = (title, due)

    if key in existing_tasks:
        if not update_if_changed:
            return "exists"
        # Check if content changed, update if so
        task_id = existing_tasks[key]
        try:
            existing = tasks_service.tasks().get(
                tasklist=task_list_id, task=task_id
            ).execute()
            if existing.get("notes") != task_body.get("notes"):
                existing.update(task_body)
                tasks_service.tasks().update(
                    tasklist=task_list_id, task=task_id,
                    body=existing
                ).execute()
                return "updated"
        except Exception:
            pass
        return "exists"

    try:
        tasks_service.tasks().insert(
            tasklist=task_list_id, body=task_body
        ).execute()
        return "added"
    except Exception:
        return "error"


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
            year = 2026  # Current school year
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
    print("\n[1/8] Ders Programı -> Calendar")
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
# SYNC: ÖDEVLERİM -> GOOGLE TASKS + CALENDAR
# =============================================================================
def sync_odevlerim(cal_service, tasks_service, data, cal_id, task_list_id,
                    existing_events, existing_tasks, drive_service=None):
    """Sync homework to Google Tasks (as tasks) and Calendar (as reminders)."""
    print("\n[2/8] Ödevlerim -> Tasks + Calendar")
    hw_data = data.get("odevlerim", {})
    rows = hw_data.get("homework", {}).get("rows", [])
    tasks_added = 0
    tasks_skipped = 0
    tasks_updated = 0
    events_added = 0
    events_skipped = 0

    # Build Drive folder links per course
    drive_links = {}  # ders -> folder web link
    if drive_service:
        try:
            root_id = _get_or_create_folder(drive_service, "Ödevler")
            for row in rows:
                ders = normalize_course(row.get("Ders Adı", ""))
                if ders and ders not in drive_links:
                    subj_id = _get_or_create_folder(
                        drive_service, ders, parent_id=root_id
                    )
                    drive_links[ders] = (
                        f"https://drive.google.com/drive/folders/{subj_id}"
                    )
        except Exception as e:
            print(f"  Drive folder link error: {e}")

    for row in rows:
        ders = normalize_course(row.get("Ders Adı", ""))
        baslik = row.get("Ödev Başlığı", "")
        kaynak = row.get("Ödev Kaynağı", "")
        tarih_str = row.get("Ödev Son Teslim Tarihi", "")
        durum = row.get("Ödev Durumu", "")

        due_dt = parse_tr_datetime(tarih_str)
        if not due_dt:
            continue

        # Build enriched notes from detail
        detail = row.get("detail", {})
        desc = detail.get("description", "")
        attachments = detail.get("attachments", [])

        notes_parts = [
            f"Kaynak: {kaynak}",
            f"Durum: {durum}",
            f"Son Teslim: {tarih_str}",
        ]
        if desc:
            notes_parts.append(f"\n---\n{desc}")
        if attachments:
            notes_parts.append("\nEkler:")
            for att in attachments:
                notes_parts.append(
                    f"  - {att['name']}: {att['url']}"
                )
        drive_link = drive_links.get(ders, "")
        if drive_link:
            notes_parts.append(f"\n📁 Drive: {drive_link}")

        # Create Google Task
        task_body = {
            "title": f"[{ders}] {baslik}",
            "notes": "\n".join(notes_parts)[:8000],
            "due": due_dt.strftime("%Y-%m-%dT00:00:00.000Z"),
        }
        if durum == "Yaptı":
            task_body["status"] = "completed"

        result = upsert_task(
            tasks_service, task_list_id, task_body,
            existing_tasks, update_if_changed=True
        )
        if result == "added":
            tasks_added += 1
        elif result == "updated":
            tasks_updated += 1
        elif result == "exists":
            tasks_skipped += 1

        # Create Calendar event for due date
        event_desc = f"Durum: {durum}\nKaynak: {kaynak}"
        if desc:
            event_desc += f"\n\n{desc[:2000]}"
        if drive_link:
            event_desc += f"\n\n📁 Drive: {drive_link}"
        event = {
            "summary": f"📝 Ödev: {baslik} ({ders})",
            "description": event_desc,
            "start": {
                "dateTime": due_dt.isoformat(),
                "timeZone": TIMEZONE,
            },
            "end": {
                "dateTime": (due_dt + timedelta(minutes=30)).isoformat(),
                "timeZone": TIMEZONE,
            },
            "colorId": COLORS["odev"],
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 60 * 24},  # 1 day before
                    {"method": "popup", "minutes": 60},        # 1 hour before
                ],
            },
        }
        result = upsert_event(cal_service, cal_id, event, existing_events)
        if result == "added":
            events_added += 1
        elif result == "exists":
            events_skipped += 1

    print(f"  Tasks: +{tasks_added} added, ~{tasks_updated} updated, ={tasks_skipped} skipped")
    print(f"  Events: +{events_added} added, ={events_skipped} skipped")
    return tasks_added, events_added


# =============================================================================
# SYNC: TAKIM ÇALIŞMALARI -> GOOGLE CALENDAR
# =============================================================================
def sync_takim_calismalari(cal_service, data, cal_id, existing_events):
    """Sync team activities to Google Calendar."""
    print("\n[3/8] Takım Çalışmaları -> Calendar")
    activities = data.get("takim_calismalari", {}).get("activities", {}).get("rows", [])
    events_added = 0
    events_skipped = 0

    for row in activities:
        name = row.get("Academy+", "")
        start_str = row.get("Çalışma Başlangıç", "")
        end_str = row.get("Çalışma Bitiş", "")
        katilim = row.get("Katılım Durumu", "")
        link = row.get("Teams Link", "")

        start_dt = parse_tr_datetime(start_str)
        end_dt = parse_tr_datetime(end_str)
        if not start_dt or not end_dt:
            continue

        desc = f"Katılım: {katilim}\n" if katilim else ""
        desc += f"Konum: {link}" if link else ""

        event = {
            "summary": f"🎯 {name}",
            "description": desc,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": TIMEZONE,
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": TIMEZONE,
            },
            "colorId": COLORS["takim"],
            "location": link if link != "Yüz Yüze" else "TED Rönesans Koleji",
        }
        result = upsert_event(cal_service, cal_id, event, existing_events)
        if result == "added":
            events_added += 1
        elif result == "exists":
            events_skipped += 1

    print(f"  Takim: +{events_added} added, ={events_skipped} skipped")
    return events_added


# =============================================================================
# SYNC: TAKVİM EVENTS -> GOOGLE CALENDAR
# =============================================================================
def sync_takvim(cal_service, data, cal_id, existing_events):
    """Sync academic calendar events (from FullCalendar JS API data).

    Each event has: title, start (ISO), end (ISO), allDay (bool),
    backgroundColor, extendedProps.
    """
    print("\n[4/8] Akademik Takvim -> Calendar")
    events = data.get("takvim", [])
    events_added = 0
    events_skipped = 0

    for ev in events:
        title = ev.get("title", "").strip()
        start = ev.get("start", "")
        end = ev.get("end", "")
        all_day = ev.get("allDay", False)

        if not title or not start:
            continue

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

        if all_day:
            # All-day event: use date format (YYYY-MM-DD)
            start_date = start[:10]  # "2026-02-16" from ISO
            end_date = end[:10] if end else start_date
            # Google Calendar all-day end is exclusive, add 1 day if same
            if end_date <= start_date:
                dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_date = (dt + timedelta(days=1)).strftime("%Y-%m-%d")

            event = {
                "summary": title,
                "colorId": color,
                "start": {"date": start_date},
                "end": {"date": end_date},
            }
        else:
            # Timed event: use dateTime format
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

    print(f"  Takvim: +{events_added} added, ={events_skipped} skipped")
    return events_added


# =============================================================================
# SYNC: DERS İÇERİKLERİ -> GOOGLE TASKS
# =============================================================================
def sync_ders_icerikleri(tasks_service, data, task_list_id, existing_tasks):
    """Sync course content notes to Google Tasks as reference items."""
    print("\n[5/8] Ders İçerikleri -> Tasks")
    ders_data = data.get("ders_icerikleri", {})
    tasks_added = 0
    tasks_skipped = 0

    for raw_name, info in ders_data.items():
        ders_name = normalize_course(raw_name)
        text = info.get("text", "").strip()
        cards = info.get("cards", [])
        if not text and not cards:
            continue

        # Create a task for each course with content
        notes = text[:5000] if text else ""
        if cards:
            notes += "\n\n---\n" + "\n\n".join(c[:500] for c in cards[:5])

        task_body = {
            "title": f"📖 {ders_name} - Haftalık İçerik",
            "notes": notes[:8000],
        }
        result = upsert_task(tasks_service, task_list_id, task_body, existing_tasks)
        if result == "added":
            tasks_added += 1
        elif result == "exists":
            tasks_skipped += 1

    print(f"  Icerik: +{tasks_added} added, ={tasks_skipped} skipped")
    return tasks_added


# =============================================================================
# SYNC: ÖGEP -> GOOGLE CALENDAR
# =============================================================================
def sync_ogep(cal_service, data, cal_id, existing_events):
    """Sync ÖGEP sessions to Google Calendar."""
    print("\n[6/8] ÖGEP -> Calendar")
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
# SYNC: GELİŞİM RAPORU -> GOOGLE TASKS
# =============================================================================
def sync_gelisim_raporu(tasks_service, data, task_list_id,
                        existing_tasks):
    """Sync grade report to Google Tasks (with update support)."""
    print("\n[7/8] Gelişim Raporu -> Tasks")
    gr = data.get("gelisim_raporu", {})
    semester = gr.get("semester", "")
    grades = gr.get("grades", [])

    added = 0
    updated = 0
    skipped = 0

    for row in grades:
        ders = normalize_course(row.get("Ders", ""))
        if not ders:
            continue

        notes_parts = [f"Dönem: {semester}"]
        for key in ["1. Sınav", "2. Sınav", "3. Sınav",
                     "DİKP/Performans-1", "DİKP/Performans-2",
                     "DİKP/Performans-3"]:
            val = row.get(key, "-")
            notes_parts.append(f"{key}: {val}")

        task_body = {
            "title": f"📊 Notlar: {ders}",
            "notes": "\n".join(notes_parts),
        }

        result = upsert_task(
            tasks_service, task_list_id, task_body,
            existing_tasks, update_if_changed=True
        )
        if result == "added":
            added += 1
        elif result == "updated":
            updated += 1
        elif result == "exists":
            skipped += 1

    print(f"  Notlar: +{added} added, ~{updated} updated, "
          f"={skipped} skipped")
    return added


# =============================================================================
# SYNC: DUYURULAR -> GOOGLE CALENDAR
# =============================================================================
def sync_duyurular(cal_service, data, cal_id, existing_events):
    """Sync announcements to Google Calendar as all-day events."""
    print("\n[8/8] Duyurular -> Calendar")
    announcements = data.get("duyurular", {}).get("announcements", [])
    added = 0
    skipped = 0

    for row in announcements:
        title = row.get("e-Posta Başlık", "").strip()
        date_str = row.get("Yayın Tarihi", "").strip()
        att_url = row.get("Ekleri_url", "")

        if not title or not date_str:
            continue

        pub_dt = None
        for fmt in ["%d.%m.%Y %H:%M", "%d.%m.%Y"]:
            try:
                pub_dt = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue
        if not pub_dt:
            continue

        desc = ""
        if att_url:
            desc = f"Ek: {att_url}"

        pub_date = pub_dt.strftime("%Y-%m-%d")
        event = {
            "summary": f"📢 {title}",
            "description": desc,
            "start": {"date": pub_date},
            "end": {"date": pub_date},
            "colorId": COLORS["etkinlik"],
        }

        result = upsert_event(
            cal_service, cal_id, event, existing_events
        )
        if result == "added":
            added += 1
        elif result == "exists":
            skipped += 1

    print(f"  Duyuru: +{added} added, ={skipped} skipped")
    return added


# =============================================================================
# SYNC: GRADES -> GOOGLE SHEETS
# =============================================================================
SHEETS_ID_FILE = os.path.join(PROJECT_ROOT, "output", "sheets_id.txt")


def _get_or_create_spreadsheet(sheets_service):
    """Get spreadsheet ID from cache or create new one."""
    if os.path.exists(SHEETS_ID_FILE):
        with open(SHEETS_ID_FILE) as f:
            sid = f.read().strip()
        if sid:
            return sid

    body = {
        "properties": {"title": "TED Rönesans Notlar"},
        "sheets": [
            {"properties": {"title": "Notlar"}},
            {"properties": {"title": "Geçmiş"}},
        ],
    }
    result = sheets_service.spreadsheets().create(
        body=body
    ).execute()
    sid = result["spreadsheetId"]

    with open(SHEETS_ID_FILE, "w") as f:
        f.write(sid)
    print(f"  Spreadsheet created: {sid}")
    return sid


def sync_grades_to_sheets(sheets_service, data):
    """Sync grade report to Google Sheets with history tracking."""
    print("\n[Sheets] Notlar -> Google Sheets")
    gr = data.get("gelisim_raporu", {})
    grades = gr.get("grades", [])
    semester = gr.get("semester", "")

    if not grades:
        print("  No grade data, skipping Sheets sync")
        return

    try:
        sid = _get_or_create_spreadsheet(sheets_service)
    except Exception as e:
        print(f"  Sheets error: {e}")
        return

    # Build header + data for "Notlar" sheet
    headers = [
        "Ders", "1. Sınav", "2. Sınav", "3. Sınav",
        "DİKP/Performans-1", "DİKP/Performans-2",
        "DİKP/Performans-3",
    ]
    values = [headers]
    for row in grades:
        values.append([
            normalize_course(row.get(h, "")) if h == "Ders" else row.get(h, "")
            for h in headers
        ])

    # Add semester info row
    values.append([])
    values.append([f"Dönem: {semester}",
                   f"Güncelleme: {datetime.now().strftime('%d.%m.%Y %H:%M')}"])

    # Write to "Notlar" sheet
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sid,
        range="Notlar!A1",
        valueInputOption="RAW",
        body={"values": values},
    ).execute()
    print(f"  Notlar sheet updated ({len(grades)} courses)")

    # Append to "Geçmiş" sheet for trend tracking
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    history_row = [ts, semester]
    for row in grades:
        ders = row.get("Ders", "")
        s1 = row.get("1. Sınav", "-")
        s2 = row.get("2. Sınav", "-")
        history_row.extend([ders, s1, s2])

    sheets_service.spreadsheets().values().append(
        spreadsheetId=sid,
        range="Geçmiş!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [history_row]},
    ).execute()
    print("  Geçmiş sheet appended")

    # Apply conditional formatting (only on first creation)
    try:
        sheet_meta = sheets_service.spreadsheets().get(
            spreadsheetId=sid
        ).execute()
        notlar_sheet_id = None
        for s in sheet_meta.get("sheets", []):
            if s["properties"]["title"] == "Notlar":
                notlar_sheet_id = s["properties"]["sheetId"]
                break

        if notlar_sheet_id is not None:
            # Check if formatting already applied
            existing_rules = []
            for s in sheet_meta.get("sheets", []):
                if s["properties"]["sheetId"] == notlar_sheet_id:
                    existing_rules = s.get(
                        "conditionalFormats", []
                    )
                    break

            if not existing_rules:
                _apply_grade_formatting(
                    sheets_service, sid, notlar_sheet_id,
                    len(grades)
                )
    except Exception:
        pass


def _apply_grade_formatting(sheets_svc, sid, sheet_id, num_rows):
    """Apply red/yellow/green conditional formatting to grade cells."""
    requests = []

    # Columns B-G (indices 1-6) contain grade values
    grade_range = {
        "sheetId": sheet_id,
        "startRowIndex": 1,
        "endRowIndex": num_rows + 1,
        "startColumnIndex": 1,
        "endColumnIndex": 7,
    }

    # Red: < 50
    requests.append({
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [grade_range],
                "booleanRule": {
                    "condition": {
                        "type": "NUMBER_LESS",
                        "values": [{"userEnteredValue": "50"}],
                    },
                    "format": {
                        "backgroundColor": {
                            "red": 0.96, "green": 0.8, "blue": 0.8,
                        },
                    },
                },
            },
            "index": 0,
        },
    })

    # Yellow: 50-70
    requests.append({
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [grade_range],
                "booleanRule": {
                    "condition": {
                        "type": "NUMBER_BETWEEN",
                        "values": [
                            {"userEnteredValue": "50"},
                            {"userEnteredValue": "70"},
                        ],
                    },
                    "format": {
                        "backgroundColor": {
                            "red": 1.0, "green": 0.95, "blue": 0.8,
                        },
                    },
                },
            },
            "index": 1,
        },
    })

    # Green: > 70
    requests.append({
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [grade_range],
                "booleanRule": {
                    "condition": {
                        "type": "NUMBER_GREATER",
                        "values": [{"userEnteredValue": "70"}],
                    },
                    "format": {
                        "backgroundColor": {
                            "red": 0.85, "green": 0.95, "blue": 0.85,
                        },
                    },
                },
            },
            "index": 2,
        },
    })

    sheets_svc.spreadsheets().batchUpdate(
        spreadsheetId=sid,
        body={"requests": requests},
    ).execute()
    print("  Conditional formatting applied")


# =============================================================================
# SYNC: ATTACHMENTS -> GOOGLE DRIVE
# =============================================================================
UPLOADED_FILES = os.path.join(PROJECT_ROOT, "output",
                              "uploaded_files.json")


def sync_attachments_to_drive(drive_service, cal_service,
                              data, cal_id):
    """Download homework attachments and upload to Google Drive."""
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
        return

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
            }
            added += 1
        except Exception as e:
            print(f"  Error uploading {att['name']}: {e}")

    # Save uploaded files tracker
    with open(UPLOADED_FILES, "w") as f:
        json.dump(uploaded, f, indent=2)

    print(f"  Drive: +{added} uploaded, ={skipped} skipped")


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
def main():
    print("Loading scraped data...")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("Connecting to Google APIs...")
    cal_svc, tasks_svc, sheets_svc, drive_svc = get_services()

    print("\nSetting up Google Calendar & Tasks...")
    cal_id = get_or_create_calendar(cal_svc, "TED Rönesans")
    task_list_id = get_or_create_task_list(
        tasks_svc, "TED Ödevler"
    )

    print("Fetching existing events/tasks for dedup...")
    existing_events = fetch_existing_events(cal_svc, cal_id)
    existing_tasks = fetch_existing_tasks(tasks_svc, task_list_id)
    print(f"  Found {len(existing_events)} existing events, "
          f"{len(existing_tasks)} existing tasks")

    sync_ders_programi(cal_svc, data, cal_id, existing_events)
    sync_odevlerim(
        cal_svc, tasks_svc, data, cal_id,
        task_list_id, existing_events, existing_tasks
    )
    sync_takim_calismalari(cal_svc, data, cal_id, existing_events)
    sync_takvim(cal_svc, data, cal_id, existing_events)
    sync_ders_icerikleri(
        tasks_svc, data, task_list_id, existing_tasks
    )
    sync_ogep(cal_svc, data, cal_id, existing_events)
    sync_gelisim_raporu(
        tasks_svc, data, task_list_id, existing_tasks
    )
    sync_duyurular(cal_svc, data, cal_id, existing_events)
    sync_grades_to_sheets(sheets_svc, data)
    sync_attachments_to_drive(drive_svc, cal_svc, data, cal_id)

    print("\n" + "=" * 50)
    print("SYNC COMPLETE!")
    print("=" * 50)


if __name__ == "__main__":
    main()
