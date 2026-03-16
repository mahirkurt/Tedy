#!/usr/bin/env python3
"""Enrich Classroom courseWork and announcements with Gemini-generated study notes.

For each homework courseWork in Google Classroom, generates a brief note using
an AI model that explains:
- General content / what the homework covers
- Related topics and concepts
- What's important to focus on

For exam courseWork, generates study guides.
For ders icerikleri announcements, generates weekly summaries.
For performans, creates an overall grade analysis announcement.

Uses --force flag to regenerate all notes (removes existing ones first).
Otherwise skips items that already have a note.

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

ENRICHMENT_CACHE = os.path.join(PROJECT_ROOT, "output", "enrichment_cache.json")

from src.json_utils import atomic_json_dump
from src.env_loader import load_env
load_env()

from google import genai
from google.genai import errors as genai_errors
from src.sync_to_classroom import (
    get_classroom_service, load_sync_state, save_sync_state,
)
from src.sync_to_google import normalize_course, _api_call_with_retry, _ALIAS_LONGEST_FIRST, _ALIAS_LOOKUP

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


def enrich_sinav(classroom_service, sync_state, router, grades_data):
    """Enrich sınav courseWork entries with AI study guides."""
    # Build grades lookup: course -> last grade
    grade_lookup = {}
    for row in grades_data:
        course = row.get("Ders", "")
        for key in ["3. Sınav", "2. Sınav", "1. Sınav"]:
            val = row.get(key, "-")
            if val and val != "-":
                grade_lookup[course] = val
                break

    cache_path = ENRICHMENT_CACHE
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        cache = {}

    enriched = 0
    skipped = 0

    for key, info in sync_state.items():
        if not key.startswith("grade:"):
            continue

        # Parse key: "grade:{course_id}:{col_name}"
        parts = key.split(":", 2)
        if len(parts) < 3:
            continue
        course_id = parts[1]
        col_name = parts[2]

        # Only enrich sınav entries
        if "Sınav" not in col_name:
            skipped += 1
            continue

        classroom_id = info.get("classroom_id")
        if not classroom_id:
            skipped += 1
            continue

        # Fetch the courseWork from Classroom
        try:
            cw = _api_call_with_retry(
                lambda cid=course_id, cwid=classroom_id: (
                    classroom_service.courses().courseWork().get(
                        courseId=cid, id=cwid,
                    ).execute()
                )
            )
        except Exception as e:
            print(f"  [WARN] Failed to fetch courseWork {classroom_id}: {e}")
            skipped += 1
            continue

        if not cw:
            skipped += 1
            continue

        desc = cw.get("description", "") or ""
        if SINAV_MARKER in desc:
            skipped += 1
            continue

        title = cw.get("title", "")
        # Extract course from title format: "Not: Matematik - 1. Sınav"
        course = ""
        if title.startswith("Not: ") and " - " in title:
            course = title[len("Not: "):title.index(" - ")]

        last_grade = grade_lookup.get(course)
        prompt = build_sinav_prompt(title, "", course or "Bilinmiyor", last_grade)

        try:
            note = router.generate(prompt)
            new_desc = desc + SINAV_MARKER + note
            _api_call_with_retry(
                lambda cid=course_id, cwid=classroom_id, d=new_desc: (
                    classroom_service.courses().courseWork().patch(
                        courseId=cid, id=cwid,
                        updateMask="description",
                        body={"description": d},
                    ).execute()
                )
            )
            enriched += 1
            cache[f"{course}|{title}"] = {"course": course, "title": title, "note": note, "type": "sinav"}
            atomic_json_dump(cache, cache_path)
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


def enrich_ders_icerikleri(classroom_service, sync_state, router, ders_data):
    """Enrich ders içerikleri announcements with AI summaries."""
    enriched = 0
    skipped = 0

    for key, info in sync_state.items():
        if not key.startswith("mat:"):
            continue

        # Parse key: "mat:{course_id}:{title}"
        parts = key.split(":", 2)
        if len(parts) < 3:
            continue
        course_id = parts[1]
        title = parts[2]

        classroom_id = info.get("classroom_id")
        if not classroom_id:
            skipped += 1
            continue

        # Extract course name from title (remove " - Haftalık İçerik" suffix)
        course_name = title
        suffix = " - Haftalık İçerik"
        if course_name.endswith(suffix):
            course_name = course_name[:-len(suffix)]

        # Find matching ders content from scraped data
        matched_content = None
        for raw_name, content_info in ders_data.items():
            normalized = normalize_course(raw_name)
            if normalized == course_name:
                matched_content = content_info
                break

        if not matched_content or not isinstance(matched_content, dict):
            skipped += 1
            continue

        text = matched_content.get("text", "").strip()
        cards = matched_content.get("cards", [])
        if not text and not cards:
            skipped += 1
            continue

        content = text
        if cards:
            content += "\n" + "\n".join(str(c)[:300] for c in cards[:5])

        # Fetch the announcement from Classroom
        try:
            ann = _api_call_with_retry(
                lambda cid=course_id, aid=classroom_id: (
                    classroom_service.courses().announcements().get(
                        courseId=cid, id=aid,
                    ).execute()
                )
            )
        except Exception as e:
            print(f"  [WARN] Failed to fetch announcement {classroom_id}: {e}")
            skipped += 1
            continue

        if not ann:
            skipped += 1
            continue

        ann_text = ann.get("text", "") or ""
        if DERS_MARKER in ann_text:
            skipped += 1
            continue

        prompt = build_ders_icerikleri_prompt(course_name, content)
        try:
            summary = router.generate(prompt)
            new_text = ann_text + DERS_MARKER + summary
            _api_call_with_retry(
                lambda cid=course_id, aid=classroom_id, t=new_text: (
                    classroom_service.courses().announcements().patch(
                        courseId=cid, id=aid,
                        updateMask="text",
                        body={"text": t},
                    ).execute()
                )
            )
            enriched += 1
            print(f"  ✓ {title}")
        except Exception as e:
            print(f"  ✗ {title}: {e}")

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


def enrich_performans(classroom_service, courses_mapping, router, grades):
    """Create or update a performance analysis announcement in TED Genel course."""
    if not grades:
        print("  No grades data, skipping performans")
        return

    from src.sync_to_classroom import GENERAL_COURSE

    genel_id = courses_mapping.get(GENERAL_COURSE)
    if not genel_id:
        print("  [WARN] TED Genel course not found, skipping performans")
        return

    prompt = build_performans_prompt(grades)
    try:
        note = router.generate(prompt)
    except Exception as e:
        print(f"  ✗ Performans: {e}")
        return

    perf_text = f"📊 Performans Analizi{PERFORMANS_MARKER}{note}"

    # List announcements in TED Genel to find existing performans
    existing_ann_id = None
    try:
        result = _api_call_with_retry(
            lambda gid=genel_id: (
                classroom_service.courses().announcements().list(
                    courseId=gid,
                ).execute()
            )
        )
        if result:
            for ann in result.get("announcements", []):
                if ann.get("text", "").startswith("📊 Performans Analizi"):
                    existing_ann_id = ann["id"]
                    break
    except Exception as e:
        print(f"  [WARN] Failed to list announcements: {e}")

    if existing_ann_id:
        try:
            _api_call_with_retry(
                lambda gid=genel_id, aid=existing_ann_id, t=perf_text: (
                    classroom_service.courses().announcements().patch(
                        courseId=gid, id=aid,
                        updateMask="text",
                        body={"text": t},
                    ).execute()
                )
            )
            print("  ✓ 📊 Performans Analizi (updated)")
        except Exception as e:
            print(f"  ✗ Performans update: {e}")
    else:
        try:
            _api_call_with_retry(
                lambda gid=genel_id, t=perf_text: (
                    classroom_service.courses().announcements().create(
                        courseId=gid,
                        body={"text": t, "state": "PUBLISHED"},
                    ).execute()
                )
            )
            print("  ✓ 📊 Performans Analizi (created)")
        except Exception as e:
            print(f"  ✗ Performans create: {e}")


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


def _enrich_odev(classroom_service, sync_state, router, force=False):
    """Enrich ödev courseWork entries with AI study notes."""
    # Load scraped homework data
    hw_lookup = load_homework_details()
    total_hw = sum(len(v) for v in hw_lookup.values())
    print(f"Scraped homework items loaded: {total_hw}")

    cache_path = ENRICHMENT_CACHE
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        cache = {}

    enriched = 0
    skipped = 0
    errors = 0

    for key, info in sync_state.items():
        if not key.startswith("cw:"):
            continue

        # Parse key: "cw:{course_id}:{baslik}"
        parts = key.split(":", 2)
        if len(parts) < 3:
            continue
        course_id = parts[1]
        baslik = parts[2]

        classroom_id = info.get("classroom_id")
        if not classroom_id:
            skipped += 1
            continue

        # Fetch the courseWork from Classroom
        try:
            cw = _api_call_with_retry(
                lambda cid=course_id, cwid=classroom_id: (
                    classroom_service.courses().courseWork().get(
                        courseId=cid, id=cwid,
                    ).execute()
                )
            )
        except Exception as e:
            print(f"  [WARN] Failed to fetch courseWork {classroom_id}: {e}")
            errors += 1
            continue

        if not cw:
            skipped += 1
            continue

        desc = cw.get("description", "") or ""

        # Handle existing note
        if GEMINI_MARKER in desc:
            if not force:
                skipped += 1
                continue
            # Strip old note for regeneration
            desc = desc.split(GEMINI_MARKER)[0]

        # Find matching homework in scraped data
        hw_row = find_matching_hw(hw_lookup, baslik, None)
        hw_desc = ""
        hw_attachments = []
        if hw_row:
            detail = hw_row.get("detail", {})
            hw_desc = detail.get("description", "")
            hw_attachments = detail.get("attachments", [])

        # Determine ders from courseWork title or scraped data
        ders = ""
        if hw_row:
            ders = hw_row.get("Ders Adı", "")
            if ders:
                ders = normalize_course(ders)

        # Generate note with auto-fallback
        prompt = build_prompt(
            ders or "Bilinmiyor", baslik, hw_desc, hw_attachments, "",
        )
        try:
            note = router.generate(prompt)
        except RuntimeError as e:
            print(f"  ✗ {e}")
            break
        except Exception as e:
            print(f"  ✗ {baslik}: {e}")
            errors += 1
            continue

        # Update courseWork description
        new_desc = desc + GEMINI_MARKER + note
        try:
            _api_call_with_retry(
                lambda cid=course_id, cwid=classroom_id, d=new_desc: (
                    classroom_service.courses().courseWork().patch(
                        courseId=cid, id=cwid,
                        updateMask="description",
                        body={"description": d},
                    ).execute()
                )
            )
            enriched += 1
            cache_key = f"{ders}|{baslik}"
            cache[cache_key] = {
                "course": ders,
                "title": baslik,
                "note": note,
                "type": "odev",
            }
            atomic_json_dump(cache, cache_path)
            print(f"  ✓ {baslik}")
        except Exception as e:
            print(f"  ✗ Update failed for {baslik}: {e}")
            errors += 1

        time.sleep(router.delay)

    print(f"\n  Ödev: +{enriched} enriched, ={skipped} skipped, !{errors} errors")


def enrich_all(token_file=None, force=False):
    """Run all enrichment functions targeting Classroom API."""
    from src.env_loader import load_env
    load_env()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found, skipping enrichment")
        return

    gemini = genai.Client(api_key=api_key)
    router = ModelRouter(gemini)
    print(f"\n[Enrich] Model: {router.current}")

    classroom_service = get_classroom_service(token_file)
    sync_state = load_sync_state()

    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    from src.sync_to_classroom import _load_courses_mapping
    courses_mapping = _load_courses_mapping()

    # 1. Ödev enrichment -> Classroom courseWork
    print("\n[Enrich] Ödev notları...")
    _enrich_odev(classroom_service, sync_state, router, force)

    # 2. Sınav enrichment -> Classroom courseWork
    print("\n[Enrich] Sınav rehberleri...")
    gelisim = data.get("gelisim_raporu", {})
    grades = gelisim.get("grades", []) if isinstance(gelisim, dict) else []
    enrich_sinav(classroom_service, sync_state, router, grades)

    # 3. Ders içerikleri enrichment -> Classroom announcements
    print("\n[Enrich] Ders özetleri...")
    ders_data = data.get("ders_icerikleri", {})
    enrich_ders_icerikleri(classroom_service, sync_state, router, ders_data)

    # 4. Performans enrichment -> Classroom announcement
    print("\n[Enrich] Performans analizi...")
    enrich_performans(classroom_service, courses_mapping, router, grades)


def main():
    force = "--force" in sys.argv

    print("=" * 60)
    print("AI Enrichment (Classroom)")
    if force:
        print("(--force: tüm notlar yeniden oluşturulacak)")
    print("=" * 60)

    enrich_all(force=force)


if __name__ == "__main__":
    main()
