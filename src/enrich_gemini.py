#!/usr/bin/env python3
"""Enrich ödev calendar events with Gemini-generated study notes.

For each homework event in Google Calendar, generates a brief note using
an AI model that explains:
- General content / what the homework covers
- Related topics and concepts
- What's important to focus on

Uses --force flag to regenerate all notes (removes existing ones first).
Otherwise skips events that already have a note.

Automatically cycles through Gemini models when daily quota is exhausted,
then falls back to local Ollama models.
"""
import json
import os
import sys
import time

import requests as http_requests

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from src.env_loader import load_env
load_env()

from google import genai
from google.genai import errors as genai_errors
from src.sync_to_google import get_services, get_or_create_calendar

# Models to try in order: Gemini cloud first, then local Ollama
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]
OLLAMA_MODELS = [
    "qwen2.5:14b",
    "qwen2.5-coder:7b",
]
OLLAMA_URL = "http://localhost:11434/api/generate"

GEMINI_MARKER = "\n\n🤖 Gemini Notu\n"
DATA_FILE = os.path.join(PROJECT_ROOT, "output", "scraped_data.json")


def load_homework_details():
    """Load scraped homework data, indexed by baslik for matching.

    When duplicate titles exist, stores all rows in a list.
    """
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("odevlerim", {}).get("homework", {}).get("rows", [])
    lookup = {}
    for row in rows:
        baslik = row.get("Ödev Başlığı", "")
        if baslik not in lookup:
            lookup[baslik] = []
        lookup[baslik].append(row)
    return lookup


def extract_event_info(event):
    """Extract ders and baslik from an ödev event summary.

    Format: '📝 Ödev: Başlık (Ders)' — ders may contain nested parens.
    """
    summary = event.get("summary", "")
    prefix = "📝 Ödev: "
    if not summary.startswith(prefix):
        return None, None
    rest = summary[len(prefix):]
    if not rest.endswith(")"):
        return None, None
    # Find matching opening paren for the last closing paren
    depth = 0
    for i in range(len(rest) - 1, -1, -1):
        if rest[i] == ")":
            depth += 1
        elif rest[i] == "(":
            depth -= 1
            if depth == 0:
                ders = rest[i + 1:-1].strip()
                baslik = rest[:i].strip()
                return baslik, ders
    return None, None


def get_event_due_date(event):
    """Extract due date string from calendar event."""
    start = event.get("start", {})
    dt_str = start.get("dateTime", start.get("date", ""))
    if "T" in dt_str:
        return dt_str.split("T")[0]  # "2026-02-27"
    return dt_str


def find_matching_hw(hw_lookup, baslik, due_date):
    """Find best matching homework row from scraped data.

    Matches by title, and when duplicates exist, by closest due date.
    """
    rows = hw_lookup.get(baslik, [])
    if not rows:
        return None
    if len(rows) == 1:
        return rows[0]
    # Multiple rows with same title — match by due date
    for row in rows:
        tarih = row.get("Ödev Son Teslim Tarihi", "")
        # tarih format: "27.02.2026 12:00" → extract date part
        if tarih and due_date:
            parts = tarih.split(" ")[0].split(".")
            if len(parts) == 3:
                row_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
                if row_date == due_date:
                    return row
    return rows[0]  # fallback to first


def build_prompt(ders, baslik, description, attachments, due_date):
    """Build the shared prompt for both Gemini and Ollama."""
    att_text = ""
    if attachments:
        att_names = ", ".join(a.get("name", "") for a in attachments)
        att_text = f"\nEkler: {att_names}"

    return f"""Sen bir ortaokul öğrencisine yardımcı olan eğitim asistanısın.

Aşağıdaki ödev hakkında kısa ve öz bir not yaz. Notun şunları içersin:
- Bu ödevin genel olarak neyle ilgili olduğu (1-2 cümle)
- İlgili konular ve kavramlar (madde işaretleriyle)
- Dikkat edilmesi gereken önemli noktalar (madde işaretleriyle)

Ders: {ders}
Ödev Başlığı: {baslik}
Son Teslim Tarihi: {due_date}
Ödev Açıklaması: {description or '(açıklama yok)'}{att_text}

KRİTİK KURALLAR:
- Türkçe yaz
- Kısa tut (en fazla 150 kelime)
- Sadece notu yaz, başka bir şey ekleme
- Markdown kullanma, düz metin yaz
- SADECE açıklamada verilen bilgileri kullan, bilgi UYDURMA
- Açıklamada belirtilmeyen konuları, tarihleri veya detayları ekleme
- Eğer açıklama yoksa veya yetersizse, bunu belirt ve genel tavsiyeler ver"""


SINAV_MARKER = "\n\n🤖 Sınav Rehberi\n"


def build_sinav_prompt(title, date, course, last_grade):
    """Build prompt for exam preparation study guide."""
    grade_info = f"Bu dersteki son sınav notu: {last_grade}" if last_grade else "Bu ders için henüz not bilgisi yok"

    return f"""Sen bir ortaokul öğrencisine yardımcı olan eğitim asistanısın.

Aşağıdaki sınav için kısa bir çalışma rehberi hazırla:
- Sınava nasıl hazırlanılmalı (3-4 madde)
- Dikkat edilmesi gereken konular
- Çalışma önerileri

Sınav: {title}
Ders: {course}
Tarih: {date}
{grade_info}

KRİTİK KURALLAR:
- Türkçe yaz
- Kısa tut (en fazla 120 kelime)
- Sadece rehberi yaz, başka bir şey ekleme
- Markdown kullanma, düz metin yaz
- Genel çalışma tavsiyeleri ver (konu detayı bilinmiyorsa)"""


def _fetch_all_events(cal_service, cal_id):
    """Fetch all TED portal events from calendar."""
    events = []
    page_token = None
    while True:
        result = cal_service.events().list(
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
    return events


def enrich_sinav(cal_service, cal_id, router, grades_data):
    """Enrich sınav calendar events with AI study guides."""
    events = _fetch_all_events(cal_service, cal_id)

    # Build grades lookup: course -> last grade
    grade_lookup = {}
    for row in grades_data:
        course = row.get("Ders", "")
        for key in ["3. Sınav", "2. Sınav", "1. Sınav"]:
            val = row.get(key, "-")
            if val and val != "-":
                grade_lookup[course] = val
                break

    sinav_keywords = ("sınav", "test", "exam", "yazılı")
    sinav_events = [
        e for e in events
        if any(k in e.get("summary", "").lower() for k in sinav_keywords)
        and not e.get("summary", "").startswith("📝 Ödev:")
    ]

    print(f"\nSınav events found: {len(sinav_events)}")
    enriched = 0
    skipped = 0

    for ev in sinav_events:
        desc = ev.get("description", "") or ""
        if SINAV_MARKER in desc:
            skipped += 1
            continue

        title = ev.get("summary", "")
        date = ev.get("start", {}).get("date", ev.get("start", {}).get("dateTime", ""))

        # Try to match course name from title
        course = ""
        try:
            from src.sync_to_google import normalize_course, COURSE_ALIASES
            for alias in COURSE_ALIASES:
                if alias.lower() in title.lower():
                    course = normalize_course(alias)
                    break
        except ImportError:
            pass

        last_grade = grade_lookup.get(course)
        prompt = build_sinav_prompt(title, date, course or "Bilinmiyor", last_grade)

        try:
            note = router.generate(prompt)
            ev["description"] = desc + SINAV_MARKER + note
            cal_service.events().update(
                calendarId=cal_id, eventId=ev["id"], body=ev,
            ).execute()
            enriched += 1
            print(f"  ✓ {title}")
        except Exception as e:
            print(f"  ✗ {title}: {e}")

        time.sleep(router.delay)

    print(f"  Sınav: +{enriched} enriched, ={skipped} skipped")


DERS_MARKER = "\n\n🤖 Haftalık Özet\n"


def build_ders_icerikleri_prompt(course, raw_content):
    """Build prompt for weekly course content summary."""
    content = raw_content[:1500] if raw_content else "(içerik yok)"
    return f"""Sen bir ortaokul öğrencisine yardımcı olan eğitim asistanısın.

Bu haftanın ders içeriğini kısaca özetle:
- Temel kavramlar (madde işaretleriyle)
- Önemli noktalar
- Varsa önceki konularla bağlantılar

Ders: {course}
İçerik: {content}

KRİTİK KURALLAR:
- Türkçe yaz
- Kısa tut (en fazla 100 kelime)
- Sadece özeti yaz, başka bir şey ekleme
- Markdown kullanma, düz metin yaz
- SADECE verilen içerikten bilgi kullan, bilgi UYDURMA"""


def enrich_ders_icerikleri(tasks_service, task_list_id, router, ders_data):
    """Enrich ders içerikleri tasks with AI summaries."""
    from src.sync_to_google import normalize_course, fetch_existing_tasks

    existing = fetch_existing_tasks(tasks_service, task_list_id)
    enriched = 0
    skipped = 0

    for raw_name, info in ders_data.items():
        course = normalize_course(raw_name)
        text = info.get("text", "").strip() if isinstance(info, dict) else ""
        cards = info.get("cards", []) if isinstance(info, dict) else []
        if not text and not cards:
            continue

        content = text
        if cards:
            content += "\n" + "\n".join(str(c)[:300] for c in cards[:5])

        task_title = f"📖 {course} - Haftalık İçerik"

        # Find existing task
        task_id = None
        for (title, due), tid in existing.items():
            if title == task_title:
                task_id = tid
                break

        if not task_id:
            skipped += 1
            continue

        # Check if already enriched
        try:
            task = tasks_service.tasks().get(
                tasklist=task_list_id, task=task_id,
            ).execute()
        except Exception:
            skipped += 1
            continue

        notes = task.get("notes", "") or ""
        if DERS_MARKER in notes:
            skipped += 1
            continue

        prompt = build_ders_icerikleri_prompt(course, content)
        try:
            summary = router.generate(prompt)
            task["notes"] = notes + DERS_MARKER + summary
            tasks_service.tasks().update(
                tasklist=task_list_id, task=task_id, body=task,
            ).execute()
            enriched += 1
            print(f"  ✓ {task_title}")
        except Exception as e:
            print(f"  ✗ {task_title}: {e}")

        time.sleep(router.delay)

    print(f"  Ders İçerikleri: +{enriched} enriched, ={skipped} skipped")


PERFORMANS_MARKER = "\n\n🤖 Performans Analizi\n"


def build_performans_prompt(grades):
    """Build prompt for grade performance analysis."""
    lines = []
    for g in grades:
        ders = g.get("Ders", "?")
        scores = []
        for k in ["1. Sınav", "2. Sınav", "3. Sınav",
                   "DİKP/Performans-1", "DİKP/Performans-2"]:
            v = g.get(k, "-")
            if v and v != "-":
                scores.append(f"{k}: {v}")
        lines.append(f"  {ders}: {', '.join(scores) or 'not yok'}")

    grades_text = "\n".join(lines)
    return f"""Sen bir ortaokul öğrencisine yardımcı olan eğitim asistanısın.

Bu öğrencinin sınav notlarını analiz et ve kısa bir performans özeti yaz:
- En iyi 3 ders (ve neden)
- İyileştirme gereken 2 ders (ve tavsiye)
- Genel eğilim (yükseliyor/düşüyor/stabil)

Notlar:
{grades_text}

KRİTİK KURALLAR:
- Türkçe yaz
- Kısa tut (en fazla 150 kelime)
- Sadece analizi yaz, başka bir şey ekleme
- Markdown kullanma, düz metin yaz
- Motive edici ve yapıcı bir ton kullan"""


def enrich_performans(tasks_service, task_list_id, router, grades):
    """Create or update a performance analysis task."""
    from src.sync_to_google import fetch_existing_tasks

    if not grades:
        print("  No grades data, skipping performans")
        return

    existing = fetch_existing_tasks(tasks_service, task_list_id)
    task_title = "📊 Performans Analizi"

    # Find or create the task
    task_id = None
    for (title, due), tid in existing.items():
        if title == task_title:
            task_id = tid
            break

    prompt = build_performans_prompt(grades)
    try:
        note = router.generate(prompt)
    except Exception as e:
        print(f"  ✗ Performans: {e}")
        return

    if task_id:
        try:
            task = tasks_service.tasks().get(
                tasklist=task_list_id, task=task_id,
            ).execute()
            task["notes"] = note  # Always overwrite with latest
            tasks_service.tasks().update(
                tasklist=task_list_id, task=task_id, body=task,
            ).execute()
            print(f"  ✓ {task_title} (updated)")
        except Exception as e:
            print(f"  ✗ {task_title}: {e}")
    else:
        try:
            tasks_service.tasks().insert(
                tasklist=task_list_id,
                body={"title": task_title, "notes": note},
            ).execute()
            print(f"  ✓ {task_title} (created)")
        except Exception as e:
            print(f"  ✗ {task_title}: {e}")


def call_gemini(client, model, prompt):
    """Generate content via Gemini API. Raises on quota exhaustion."""
    response = client.models.generate_content(
        model=model, contents=prompt,
    )
    return response.text.strip()


def call_ollama(model, prompt):
    """Generate content via local Ollama. Returns None on failure."""
    try:
        r = http_requests.post(OLLAMA_URL, json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 512},
        }, timeout=300)
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except Exception as e:
        raise RuntimeError(f"Ollama ({model}): {e}")


class ModelRouter:
    """Routes generation requests through available models with fallback."""

    def __init__(self, gemini_client):
        self.gemini_client = gemini_client
        self.exhausted = set()
        self.current = None
        self.using_ollama = False
        self._pick_model()

    def _pick_model(self):
        """Pick next available model."""
        # Try Gemini models first
        for m in GEMINI_MODELS:
            if m not in self.exhausted:
                self.current = m
                self.using_ollama = False
                return True
        # Fall back to Ollama
        for m in OLLAMA_MODELS:
            if m not in self.exhausted:
                self.current = m
                self.using_ollama = True
                return True
        return False

    def generate(self, prompt):
        """Generate text, auto-falling back on quota exhaustion."""
        while True:
            if self.current is None:
                raise RuntimeError("Tüm modeller tükendi!")

            try:
                if self.using_ollama:
                    return call_ollama(self.current, prompt)
                else:
                    return call_gemini(
                        self.gemini_client, self.current, prompt,
                    )
            except genai_errors.ClientError as e:
                if "RESOURCE_EXHAUSTED" in str(e):
                    self.exhausted.add(self.current)
                    if self._pick_model():
                        print(
                            f"  ⟳ Kota doldu, geçiş: {self.current}"
                            f"{' (Ollama)' if self.using_ollama else ''}"
                        )
                        time.sleep(2)
                        continue
                    raise RuntimeError("Tüm modellerin kotası doldu!")
                raise
            except RuntimeError:
                # Ollama failure — mark and try next
                self.exhausted.add(self.current)
                if self._pick_model():
                    print(f"  ⟳ Model hatası, geçiş: {self.current}")
                    continue
                raise RuntimeError("Tüm modeller tükendi!")

    @property
    def delay(self):
        """Rate limiting delay: 13s for Gemini free tier, 1s for Ollama."""
        return 1 if self.using_ollama else 13


def _enrich_odev(cal, cal_id, router, force=False):
    """Enrich ödev calendar events with AI study notes (existing logic)."""
    # Load scraped homework data
    hw_lookup = load_homework_details()
    total_hw = sum(len(v) for v in hw_lookup.values())
    print(f"Scraped homework items loaded: {total_hw}")

    # Fetch all ödev events from calendar
    events = _fetch_all_events(cal, cal_id)

    odev_events = [
        e for e in events
        if e.get("summary", "").startswith("📝 Ödev:")
    ]
    print(f"Ödev events in calendar: {len(odev_events)}")

    enriched = 0
    skipped = 0
    errors = 0

    for ev in odev_events:
        summary = ev.get("summary", "")
        desc = ev.get("description", "")

        # Handle existing note
        if GEMINI_MARKER in desc:
            if not force:
                skipped += 1
                continue
            # Strip old note for regeneration
            desc = desc.split(GEMINI_MARKER)[0]

        baslik, ders = extract_event_info(ev)
        if not baslik:
            skipped += 1
            continue

        due_date = get_event_due_date(ev)

        # Find matching homework in scraped data
        hw_row = find_matching_hw(hw_lookup, baslik, due_date)
        hw_desc = ""
        hw_attachments = []
        if hw_row:
            detail = hw_row.get("detail", {})
            hw_desc = detail.get("description", "")
            hw_attachments = detail.get("attachments", [])

        # Generate note with auto-fallback
        prompt = build_prompt(
            ders, baslik, hw_desc, hw_attachments, due_date,
        )
        try:
            note = router.generate(prompt)
        except RuntimeError as e:
            print(f"  ✗ {e}")
            errors += len(odev_events) - enriched - skipped - errors
            break
        except Exception as e:
            print(f"  ✗ {summary}: {e}")
            errors += 1
            continue

        # Update event description
        new_desc = desc + GEMINI_MARKER + note
        ev["description"] = new_desc

        try:
            cal.events().update(
                calendarId=cal_id, eventId=ev["id"], body=ev
            ).execute()
            enriched += 1
            print(f"  ✓ {summary}")
        except Exception as e:
            print(f"  ✗ Update failed for {summary}: {e}")
            errors += 1

        time.sleep(router.delay)

    print(f"\n  Ödev: +{enriched} enriched, ={skipped} skipped, !{errors} errors")


def enrich_all(token_file=None, force=False):
    """Run all enrichment functions for a given account."""
    from src.env_loader import load_env
    load_env()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found, skipping enrichment")
        return

    gemini = genai.Client(api_key=api_key)
    router = ModelRouter(gemini)
    print(f"\n[Enrich] Model: {router.current}")

    cal, tasks_svc, _, _ = get_services(token_file=token_file)
    cal_id = get_or_create_calendar(cal, "TED Rönesans")

    from src.sync_to_google import get_or_create_task_list
    task_list_id = get_or_create_task_list(tasks_svc, "TED Ödevler")

    # Load scraped data
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    # 1. Ödev enrichment (existing)
    print("\n[Enrich] Ödev notları...")
    _enrich_odev(cal, cal_id, router, force)

    # 2. Sınav enrichment
    print("\n[Enrich] Sınav rehberleri...")
    gelisim = data.get("gelisim_raporu", {})
    if isinstance(gelisim, dict):
        grades = gelisim.get("grades", [])
    elif isinstance(gelisim, list):
        grades = gelisim
    else:
        grades = []
    enrich_sinav(cal, cal_id, router, grades)

    # 3. Ders içerikleri enrichment
    print("\n[Enrich] Ders özetleri...")
    ders_data = data.get("ders_icerikleri", {})
    enrich_ders_icerikleri(tasks_svc, task_list_id, router, ders_data)

    # 4. Performans enrichment
    print("\n[Enrich] Performans analizi...")
    enrich_performans(tasks_svc, task_list_id, router, grades)


def main():
    force = "--force" in sys.argv

    print("=" * 60)
    print("AI Enrichment (All)")
    if force:
        print("(--force: tüm notlar yeniden oluşturulacak)")
    print("=" * 60)

    enrich_all(force=force)


if __name__ == "__main__":
    main()
