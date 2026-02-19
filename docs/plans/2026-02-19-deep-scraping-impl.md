# Deep Scraping Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Scrape additional content from SEBİTV (412 interactive resources), MEBI (quizzes), and EBA (course videos) and upload to Google Drive.

**Architecture:** Three independent scripts, each following the existing 2-phase pattern (Selenium discovery → requests download → Drive upload). Each script is self-contained with its own tracker JSON.

**Tech Stack:** Python 3, Selenium (headless Chrome), requests, google-api-python-client, zipfile (stdlib)

---

### Task 1: SEBİTV Interactive Scraper — Core Structure

**Files:**
- Create: `src/scrape_sebitv_interactive.py`

**Step 1: Write the script scaffold with login + session reuse from scrape_sebitv.py**

```python
#!/usr/bin/env python3
"""Scrape SEBİTV interactive resources: static archives + question banks → Google Drive."""
import io
import json
import os
import re
import sys
import time
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

import requests as req
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from googleapiclient.http import MediaInMemoryUpload, MediaIoBaseUpload

from src.sync_to_google import get_services, _get_or_create_folder

TC_NO = "50653866492"
PASSWORD = "mkhu7979"

BASE = "https://www.sebitvcloud.com"
SPA = f"{BASE}/proxy/VCollabPlayer_v0.0.1929/index.html"
API = "https://uygulama.sebitvcloud.com/VCloudFrontEndService"

DISCOVERY_FILE = os.path.join("output", "sebitv_discovered.json")
TRACKER_FILE = os.path.join("output", "sebitv_interactive_uploaded.json")

MAX_INMEMORY = 100 * 1024 * 1024


def create_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-setuid-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=opts)


def sebitv_login(driver):
    """Login to SEBİTV Cloud via Selenium."""
    print("[LOGIN] SEBİTV Cloud...")
    driver.get(f"{BASE}/tr/giris.jsp")
    time.sleep(3)
    driver.find_element(By.NAME, "l_un").send_keys(TC_NO)
    driver.find_element(By.NAME, "l_pw").send_keys(PASSWORD)
    btns = driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
    if btns:
        btns[0].click()
    time.sleep(6)
    ok = "giris.jsp" not in driver.current_url
    print(f"  Login {'OK' if ok else 'FAIL'}")
    return ok


def get_session(driver):
    """Transfer Selenium cookies to requests Session."""
    driver.get(f"{SPA}#/main/dashboardNew?routeConst=dashboard")
    time.sleep(5)
    s = req.Session()
    for c in driver.get_cookies():
        s.cookies.set(c["name"], c["value"],
                      domain=c.get("domain", ""),
                      path=c.get("path", "/"))
    s.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Referer": f"{BASE}/",
        "Origin": BASE,
    })
    return s


def sanitize(name):
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    return name.strip(". ")[:200]


def load_tracker():
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE) as f:
            return json.load(f)
    return {}


def save_tracker(tracker):
    with open(TRACKER_FILE, "w") as f:
        json.dump(tracker, f, indent=2, ensure_ascii=False)
```

**Step 2: Verify scaffold runs**

Run: `cd /mnt/pi-shared/projects/TED && .venv/bin/python -c "import src.scrape_sebitv_interactive"`
Expected: No errors

**Step 3: Commit**

```bash
git add src/scrape_sebitv_interactive.py
git commit -m "feat: add SEBİTV interactive scraper scaffold"
```

---

### Task 2: SEBİTV Interactive — Content Crawling Functions

**Files:**
- Modify: `src/scrape_sebitv_interactive.py`

**Step 1: Add get_repo_type() and _content_base() (copied from scrape_sebitv.py)**

```python
def get_repo_type(s, resource_id):
    """Get REPOSITORY type via tracking/launch API."""
    url = f"{API}/tracking/launch?id={resource_id}&loc=10&locid="
    try:
        r = s.get(url, timeout=15)
        if r.status_code == 200:
            m = re.search(r'REPOSITORY/([a-f0-9]+)/', r.text)
            if m:
                return m.group(1)
    except Exception:
        pass
    return None


def _content_base(res, repo_type):
    """Build base URL for a resource."""
    return (
        f"{BASE}/BASE_URL/LEARNING_OBJECT/"
        f"REPOSITORY/{repo_type}/"
        f"{res['resourceId']}/{res['version']}/"
        f"{res['code']}"
    )
```

**Step 2: Add crawl_content_files() — discovers all downloadable files in a resource package**

This function fetches known file paths from the content package structure and collects all available static files:

```python
# Known file paths to check in every interactive resource
KNOWN_PATHS = [
    "dataLevel.html",
    "start.htm",
    "imsmanifest.xml",
    "sco1/imsmanifest.xml",
    "sco1/resources/js/SkipIntroDataJSON.js",
    "sco1/resources/js/internalLoader.js",
    "sco1/resources/js/config.js",
    "sco1/resources/js/dataJSON.js",
    "sco1/resources/js/ActivityJSON.js",
    "sco1/resources/css/style.css",
    "sco1/resources/css/main.css",
    "sco1/index.html",
]


def crawl_content_files(s, base_url):
    """Discover and download all static files from an interactive resource.

    Returns dict: {relative_path: bytes_content}
    """
    files = {}

    # 1. Fetch all known paths
    for path in KNOWN_PATHS:
        url = f"{base_url}/{path}"
        try:
            r = s.get(url, timeout=10)
            if r.status_code == 200 and len(r.content) > 0:
                # Skip HTML error pages
                ct = r.headers.get("Content-Type", "")
                if "text/html" in ct and len(r.content) < 200:
                    text = r.content.decode("utf-8", errors="ignore")
                    if "<title>Error</title>" in text:
                        continue
                files[path] = r.content
        except Exception:
            pass

    # 2. Parse dataLevel.html for additional asset refs
    if "dataLevel.html" in files:
        html = files["dataLevel.html"].decode("utf-8", errors="ignore")
        # Extract image/media refs
        refs = re.findall(
            r'(?:src|href|url|pdfName|imageName|fileName)'
            r'["\']?\s*[:=]\s*["\']([^"\'<>]+\.\w{2,4})',
            html, re.IGNORECASE,
        )
        for ref in refs:
            if ref.startswith("http"):
                continue
            # Normalize path
            path = ref.lstrip("./")
            if path not in files:
                url = f"{base_url}/{path}"
                try:
                    r = s.get(url, timeout=10)
                    if r.status_code == 200 and len(r.content) > 0:
                        files[path] = r.content
                except Exception:
                    pass
            # Also try under resources/
            rpath = f"resources/{path}"
            if rpath not in files:
                url = f"{base_url}/{rpath}"
                try:
                    r = s.get(url, timeout=10)
                    if r.status_code == 200 and len(r.content) > 0:
                        files[rpath] = r.content
                except Exception:
                    pass

    # 3. Parse JS files for image/asset references
    for fpath, content in list(files.items()):
        if not fpath.endswith(".js"):
            continue
        text = content.decode("utf-8", errors="ignore")
        # Find image references: "image.png", "diagram.svg", etc.
        img_refs = re.findall(
            r'["\']([^"\']+\.(?:png|jpg|jpeg|gif|svg|webp|mp3|wav|ogg))["\']',
            text, re.IGNORECASE,
        )
        for ref in img_refs:
            if ref.startswith("http") or ref.startswith("data:"):
                continue
            path = ref.lstrip("./")
            # Try under sco1/resources/
            for prefix in ["sco1/resources/", "sco1/resources/img/",
                           "sco1/resources/images/", "resources/", ""]:
                full = f"{prefix}{path}" if prefix else path
                if full not in files:
                    url = f"{base_url}/{full}"
                    try:
                        r = s.get(url, timeout=8)
                        if r.status_code == 200 and len(r.content) > 100:
                            ct = r.headers.get("Content-Type", "")
                            if "text/html" not in ct:
                                files[full] = r.content
                                break
                    except Exception:
                        pass

    return files
```

**Step 3: Add extract_questions() — parses SkipIntroDataJSON.js for question bank data**

```python
def extract_questions(files):
    """Extract question bank from SkipIntroDataJSON.js if present.

    Returns dict with questions or None.
    """
    js_path = "sco1/resources/js/SkipIntroDataJSON.js"
    if js_path not in files:
        return None

    text = files[js_path].decode("utf-8", errors="ignore")

    # SkipIntroDataJSON.js typically contains a JSON object assigned to a var
    # Pattern: var SkipIntroDataJSON = { ... };
    m = re.search(r'=\s*(\{[\s\S]+\})\s*;?\s*$', text)
    if not m:
        # Try: entire file is JSON
        m = re.search(r'(\{[\s\S]+\})', text)
    if not m:
        return None

    try:
        data = json.loads(m.group(1))
        return data
    except json.JSONDecodeError:
        # Try to fix common JS→JSON issues (trailing commas, single quotes)
        cleaned = m.group(1)
        cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
        cleaned = cleaned.replace("'", '"')
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"_raw": text[:5000], "_parse_error": True}
```

**Step 4: Commit**

```bash
git add src/scrape_sebitv_interactive.py
git commit -m "feat: add content crawling and question extraction for SEBİTV interactive"
```

---

### Task 3: SEBİTV Interactive — Upload + Main Loop

**Files:**
- Modify: `src/scrape_sebitv_interactive.py`

**Step 1: Add upload_to_drive() helper**

```python
def upload_to_drive(drive, content, filename, mimetype, folder_id):
    """Upload file to Google Drive."""
    size = len(content)
    if size <= MAX_INMEMORY:
        media = MediaInMemoryUpload(content, mimetype=mimetype)
    else:
        media = MediaIoBaseUpload(
            io.BytesIO(content), mimetype=mimetype,
            chunksize=50 * 1024 * 1024, resumable=True,
        )
    result = drive.files().create(
        body={"name": filename, "parents": [folder_id]},
        media_body=media,
        fields="id,webViewLink",
    ).execute()
    return result
```

**Step 2: Add process_interactive_resources() — main processing loop**

```python
def process_interactive_resources(resources, s, drive, tracker):
    """Process all interactive resources: crawl, zip, extract questions, upload."""
    print(f"\n[İŞLEM] {len(resources)} etkileşimli kaynak işleniyor...")

    archive_root = _get_or_create_folder(drive, "SEBİTV Etkileşimli")
    qbank_root = _get_or_create_folder(drive, "SEBİTV Soru Bankaları")

    course_folders = {}    # archive folders
    unit_folders = {}
    q_course_folders = {}  # question bank folders
    q_unit_folders = {}

    added = 0
    skipped = 0
    failed = 0

    for i, res in enumerate(resources):
        key = res["resourceId"]
        if key in tracker:
            skipped += 1
            continue

        course = res["course"]
        unit = res["unit"]
        title = res["title"]

        print(f"\n  [{i + 1}/{len(resources)}] {course} > {unit} > {title}")

        try:
            # Get REPOSITORY type
            repo_type = get_repo_type(s, key)
            if repo_type is None:
                print("    Repo tipi bulunamadı")
                failed += 1
                continue

            base_url = _content_base(res, repo_type)

            # Crawl all static files
            files = crawl_content_files(s, base_url)
            if not files:
                print("    Dosya bulunamadı")
                failed += 1
                continue

            print(f"    {len(files)} dosya bulundu")

            # Extract question bank
            questions = extract_questions(files)
            q_uploaded = False

            if questions:
                # Upload question bank JSON
                if course not in q_course_folders:
                    q_course_folders[course] = _get_or_create_folder(
                        drive, sanitize(course), parent_id=qbank_root)
                ukey = f"q/{course}/{unit}"
                if ukey not in q_unit_folders:
                    q_unit_folders[ukey] = _get_or_create_folder(
                        drive, sanitize(unit),
                        parent_id=q_course_folders[course])

                q_data = {
                    "course": course, "unit": unit,
                    "topic": res["topic"],
                    "subSubject": res["subSubject"],
                    "title": title, "code": res["code"],
                    "questions": questions,
                }
                q_bytes = json.dumps(
                    q_data, ensure_ascii=False, indent=2
                ).encode("utf-8")
                q_filename = f"{sanitize(title)}.json"
                q_result = upload_to_drive(
                    drive, q_bytes, q_filename,
                    "application/json", q_unit_folders[ukey])
                print(f"    Soru bankası: {q_result.get('webViewLink', '')}")
                q_uploaded = True

            # Create ZIP archive of all static files
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for fpath, fcontent in files.items():
                    zf.writestr(fpath, fcontent)
            zip_bytes = zip_buf.getvalue()

            if len(zip_bytes) < 500:
                print(f"    ZIP çok küçük ({len(zip_bytes)} bytes)")
                failed += 1
                continue

            print(f"    ZIP: {len(zip_bytes) / 1024:.1f} KB")

            # Upload ZIP
            if course not in course_folders:
                course_folders[course] = _get_or_create_folder(
                    drive, sanitize(course), parent_id=archive_root)
            ukey = f"a/{course}/{unit}"
            if ukey not in unit_folders:
                unit_folders[ukey] = _get_or_create_folder(
                    drive, sanitize(unit),
                    parent_id=course_folders[course])

            zip_filename = f"{sanitize(title)}.zip"
            z_result = upload_to_drive(
                drive, zip_bytes, zip_filename,
                "application/zip", unit_folders[ukey])
            print(f"    Arşiv: {z_result.get('webViewLink', '')}")

            # Track
            tracker[key] = {
                "course": course, "unit": unit, "title": title,
                "type": res["type"],
                "fileCount": len(files),
                "zipSize": len(zip_bytes),
                "archiveDriveId": z_result["id"],
                "archiveLink": z_result.get("webViewLink", ""),
                "hasQuestions": q_uploaded,
            }
            if q_uploaded:
                tracker[key]["questionsDriveId"] = q_result["id"]
                tracker[key]["questionsLink"] = q_result.get("webViewLink", "")
            save_tracker(tracker)
            added += 1

        except req.exceptions.Timeout:
            print("    Zaman aşımı")
            failed += 1
        except req.exceptions.ConnectionError:
            print("    Bağlantı hatası")
            failed += 1
        except Exception as e:
            print(f"    Hata: {e}")
            failed += 1

    print(f"\n  Sonuç: +{added} yüklendi, ={skipped} atlandı, x{failed} başarısız")
    return added, skipped, failed
```

**Step 3: Add main()**

```python
def main():
    os.makedirs("output", exist_ok=True)
    tracker = load_tracker()
    print(f"[Tracker] {len(tracker)} kaynak zaten işlenmiş")

    # Load discovered resources
    if not os.path.exists(DISCOVERY_FILE):
        print(f"HATA: {DISCOVERY_FILE} bulunamadı!")
        print("Önce src/scrape_sebitv.py çalıştırın.")
        return

    with open(DISCOVERY_FILE) as f:
        all_resources = json.load(f)

    # Filter to interactive only (duration=0, not PDF)
    interactive = [
        r for r in all_resources
        if not (r.get("duration") and r["duration"] > 0)
        and r.get("fileType") != "pdf"
    ]
    print(f"  {len(interactive)} etkileşimli kaynak / {len(all_resources)} toplam")

    if not interactive:
        print("Etkileşimli kaynak bulunamadı!")
        return

    # Login and get session
    print("\n[1/2] SEBİTV giriş yapılıyor...")
    driver = create_driver()
    try:
        ok = sebitv_login(driver)
        if not ok:
            print("HATA: SEBİTV girişi başarısız!")
            return
        s = get_session(driver)
    finally:
        driver.quit()

    # Get Drive service
    _, _, _, drive_svc = get_services()

    # Process
    print("\n[2/2] Etkileşimli kaynaklar işleniyor...")
    added, skipped, failed = process_interactive_resources(
        interactive, s, drive_svc, tracker)

    print(f"\n{'=' * 60}")
    print("  SEBİTV ETKİLEŞİMLİ TAMAMLANDI")
    print(f"  Toplam: {len(interactive)}")
    print(f"  Yüklenen: {added}")
    print(f"  Atlanan: {skipped}")
    print(f"  Başarısız: {failed}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
```

**Step 4: Run the script**

Run: `cd /mnt/pi-shared/projects/TED && .venv/bin/python src/scrape_sebitv_interactive.py`
Expected: Login OK, processes 412 interactive resources, uploads ZIPs + question JSONs to Drive

**Step 5: Check results and fix any issues**

Review output for errors. Common issues:
- Repo type not found → check if session expired
- Connection errors → add retry logic if needed
- ZIP too small → some resources may have no accessible content

**Step 6: Commit**

```bash
git add src/scrape_sebitv_interactive.py
git commit -m "feat: complete SEBİTV interactive scraper with archive + question bank upload"
```

---

### Task 4: MEBI Quizzes — Discovery Script

**Files:**
- Create: `src/discover_mebi_quizzes.py`

This task requires live exploration of the MEBI quiz UI. The quiz mechanism is unknown and needs discovery.

**Step 1: Write discovery script that navigates to a topic and explores quiz elements**

```python
#!/usr/bin/env python3
"""Discover MEBI quiz structure: navigate to topics and explore quiz UI/API."""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

TC_NO = "50653866492"
PASSWORD = "mkhu7979"
MEBI_BASE = "https://mebi.eba.gov.tr"


def create_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-setuid-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    return webdriver.Chrome(options=opts)


def mebi_login(driver):
    driver.get(
        "https://giris.eba.gov.tr/EBA_GIRIS/Giris"
        "?uygulamaKodu=mebi&login=student"
    )
    time.sleep(8)
    if "giris.eba.gov.tr" in driver.current_url:
        driver.find_element(By.ID, "tckn").send_keys(TC_NO)
        driver.find_element(By.ID, "password").send_keys(PASSWORD)
        for btn in driver.find_elements(
            By.CSS_SELECTOR, "button.nl-form-send-btn"
        ):
            if btn.text.strip() == "Giriş":
                btn.click()
                break
        time.sleep(8)
    print(f"[MEBI LOGIN] {driver.current_url}")
    return "mebi.eba.gov.tr" in driver.current_url


def explore_topic_page(driver, topic_uuid, topic_name):
    """Navigate to a topic and explore quiz/assessment elements."""
    url = f"{MEBI_BASE}/student/section/subject-details/{topic_uuid}"
    driver.get(url)
    time.sleep(5)

    print(f"\n{'=' * 60}")
    print(f"  TOPIC: {topic_name}")
    print(f"  URL: {url}")
    print(f"{'=' * 60}")

    # 1. Page text content
    body = driver.find_element(By.TAG_NAME, "body").text
    print(f"\n  Body text (first 500 chars):")
    print(f"  {body[:500]}")

    # 2. Find all links and buttons
    elements = driver.execute_script("""
        var result = [];
        // Links
        document.querySelectorAll('a').forEach(function(el) {
            result.push({
                type: 'link',
                href: (el.href || '').substring(0, 300),
                text: el.textContent.trim().substring(0, 100),
                cls: el.className.substring(0, 80)
            });
        });
        // Buttons
        document.querySelectorAll('button').forEach(function(el) {
            result.push({
                type: 'button',
                text: el.textContent.trim().substring(0, 100),
                cls: el.className.substring(0, 80),
                onclick: (el.getAttribute('onclick') || '').substring(0, 200)
            });
        });
        // Tabs/nav items
        document.querySelectorAll('[role="tab"], .nav-link, .tab').forEach(function(el) {
            result.push({
                type: 'tab',
                text: el.textContent.trim().substring(0, 100),
                cls: el.className.substring(0, 80),
                href: (el.getAttribute('href') || '').substring(0, 200)
            });
        });
        return result;
    """)

    print(f"\n  Interactive elements ({len(elements)}):")
    for el in elements:
        if el.get("text"):
            print(f"    [{el['type']}] {el['text'][:60]}"
                  f" | cls={el.get('cls', '')[:40]}"
                  f" | href={el.get('href', '')[:100]}")

    # 3. Look for quiz/assessment keywords
    page_source = driver.page_source
    quiz_keywords = [
        "değerlendirme", "quiz", "test", "sınav", "soru",
        "assessment", "question", "exam", "evaluate"
    ]
    for kw in quiz_keywords:
        if kw.lower() in page_source.lower():
            print(f"\n  Found keyword: '{kw}' in page source")

    # 4. Check for tabs/sections that might contain quizzes
    tabs = driver.find_elements(By.CSS_SELECTOR,
        "[role='tab'], .nav-link, .tab-link, .mat-tab-label")
    print(f"\n  Tabs found ({len(tabs)}):")
    for tab in tabs:
        print(f"    '{tab.text.strip()}'")

    # 5. Click any assessment/quiz links
    for tab in tabs:
        text = tab.text.strip().lower()
        if any(kw in text for kw in ["değerlendirme", "quiz", "test", "soru"]):
            print(f"\n  >>> Clicking tab: '{tab.text.strip()}'")
            tab.click()
            time.sleep(3)
            body2 = driver.find_element(By.TAG_NAME, "body").text
            print(f"  After click: {body2[:500]}")

    # 6. Check performance logs for API calls
    try:
        logs = driver.get_log("performance")
        api_calls = []
        for entry in logs:
            msg = json.loads(entry["message"])["message"]
            if msg["method"] == "Network.requestWillBeSent":
                url = msg.get("params", {}).get("request", {}).get("url", "")
                if "mebi" in url or "eba" in url:
                    api_calls.append(url)
        print(f"\n  API calls ({len(api_calls)}):")
        for u in api_calls[:30]:
            print(f"    {u[:200]}")
    except Exception:
        pass

    # Save full page source
    with open(f"output/mebi_topic_{topic_uuid[:8]}.html", "w") as f:
        f.write(page_source)


def main():
    os.makedirs("output", exist_ok=True)
    driver = create_driver()

    try:
        ok = mebi_login(driver)
        if not ok:
            print("HATA: MEBI girişi başarısız!")
            return

        # Load discovered topics
        with open("output/mebi_videos_discovered.json") as f:
            topics = json.load(f)

        # Explore first 3 topics from different courses
        explored = set()
        for topic in topics:
            course = topic["course"]
            if course in explored:
                continue
            explored.add(course)
            explore_topic_page(driver, topic["uuid"], topic["topic"])
            if len(explored) >= 3:
                break

    finally:
        driver.quit()

    print("\nKeşif tamamlandı. output/ klasöründeki HTML dosyalarını inceleyin.")


if __name__ == "__main__":
    main()
```

**Step 2: Run discovery script**

Run: `cd /mnt/pi-shared/projects/TED && .venv/bin/python src/discover_mebi_quizzes.py`
Expected: Explores 3 topic pages, finds quiz-related UI elements and API endpoints

**Step 3: Analyze discovery results and adapt**

Based on findings, determine:
- How quizzes are loaded (API endpoint, DOM injection, or iframe?)
- Quiz data format (JSON, HTML form, or JavaScript object?)
- How to navigate to quiz content programmatically

**Step 4: Commit**

```bash
git add src/discover_mebi_quizzes.py
git commit -m "feat: add MEBI quiz discovery script"
```

---

### Task 5: MEBI Quizzes — Scraper (Post-Discovery)

**Files:**
- Create: `src/scrape_mebi_quizzes.py`

**Depends on:** Task 4 discovery results. The exact implementation depends on what Task 4 reveals about the quiz loading mechanism.

**Step 1: Write scraper based on discovery findings**

The scraper will follow the MEBI videos pattern:
- Login via EBA → MEBI
- Navigate course → unit → topic hierarchy
- For each topic, find and extract quiz content
- Upload quiz JSON to Drive

Skeleton (to be filled after Task 4):

```python
#!/usr/bin/env python3
"""Scrape MEBI quizzes and upload to Google Drive as JSON."""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from googleapiclient.http import MediaInMemoryUpload

from src.sync_to_google import get_services, _get_or_create_folder

TC_NO = "50653866492"
PASSWORD = "mkhu7979"
MEBI_BASE = "https://mebi.eba.gov.tr"

COURSES = {
    "Din Kültürü": "66ed9e38-25bf-4800-0877-08ddc2afb3ce",
    "Fen Bilimleri": "1f4b44bc-a0ac-4b08-087c-08ddc2afb3ce",
    "İngilizce": "cf7102fa-6b36-4a6a-087d-08ddc2afb3ce",
    "Matematik": "1c9295cc-16a0-4a7c-0882-08ddc2afb3ce",
    "Sosyal Bilgiler": "4b2a1a59-f118-45c9-0883-08ddc2afb3ce",
    "Türkçe": "72a6b6a9-3473-414a-0888-08ddc2afb3ce",
}

TRACKER_FILE = os.path.join("output", "mebi_quizzes_uploaded.json")
DISCOVERY_FILE = os.path.join("output", "mebi_quizzes_discovered.json")

# ... create_driver, mebi_login, load_tracker, save_tracker (same patterns)
# ... discover_quizzes(driver) — uses discovery findings
# ... extract_quiz_data(driver, topic_uuid) — quiz-specific extraction
# ... upload_quizzes(quizzes, drive, tracker) — JSON upload to Drive
# ... main()
```

**Step 2: Run the scraper**

Run: `cd /mnt/pi-shared/projects/TED && .venv/bin/python src/scrape_mebi_quizzes.py`

**Step 3: Commit**

```bash
git add src/scrape_mebi_quizzes.py
git commit -m "feat: add MEBI quiz scraper"
```

---

### Task 6: EBA Videos — Discovery Script

**Files:**
- Create: `src/discover_eba_videos.py`

This task requires exploring the EBA course pages to find embedded videos.

**Step 1: Write EBA video discovery script**

```python
#!/usr/bin/env python3
"""Discover EBA course video structure: find embedded videos in course pages."""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

TC_NO = "50653866492"
PASSWORD = "mkhu7979"

SPA_BASE = ("https://ders.eba.gov.tr/ders/proxy/"
            "VCollabPlayer_v0.0.1064/index.html")


def create_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-setuid-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    return webdriver.Chrome(options=opts)


def eba_login(driver):
    driver.get("https://giris.eba.gov.tr/EBA_GIRIS/student.jsp")
    time.sleep(3)
    driver.find_element(By.ID, "tckn").send_keys(TC_NO)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    for btn in driver.find_elements(
        By.CSS_SELECTOR, "button.nl-form-send-btn"
    ):
        if btn.text.strip() == "Giriş":
            btn.click()
            break
    time.sleep(5)
    print(f"[EBA LOGIN] {driver.current_url}")


def explore_course_content(driver):
    """Navigate through EBA SPA to find video content."""
    # Go to SPA
    driver.get(f"{SPA_BASE}#/main/dashboard/3/6/0")
    time.sleep(5)

    # Navigate to Dersler
    driver.execute_script("""
        var sidebar = document.querySelectorAll(
            '[ng-click="itemSelected(item)"]');
        for (var i = 0; i < sidebar.length; i++) {
            if (sidebar[i].textContent.trim() === 'Dersler') {
                sidebar[i].click();
                return;
            }
        }
    """)
    time.sleep(5)

    # Get courses
    courses = driver.execute_script("""
        var items = document.querySelectorAll(
            '[ng-repeat="onelesson in render.allLessons"]');
        var result = [];
        for (var i = 0; i < items.length; i++) {
            var scope = angular.element(items[i]).scope();
            if (scope.onelesson) {
                result.push({
                    name: scope.onelesson.name,
                    nodeId: scope.onelesson.nodeId
                });
            }
        }
        return JSON.stringify(result);
    """)
    course_list = json.loads(courses)
    print(f"  {len(course_list)} ders bulundu")

    # For first course, navigate into it and explore content types
    if course_list:
        course = course_list[0]
        print(f"\n  Exploring: {course['name']}")

        # Click course
        driver.execute_script(f"""
            var items = document.querySelectorAll(
                '[ng-repeat="onelesson in render.allLessons"]');
            for (var i = 0; i < items.length; i++) {{
                var scope = angular.element(items[i]).scope();
                if (scope.onelesson &&
                    scope.onelesson.nodeId === '{course["nodeId"]}') {{
                    var clickable = items[i].querySelector('[ng-click]')
                                   || items[i];
                    clickable.click();
                    break;
                }}
            }}
        """)
        time.sleep(5)

        # Dump page content structure
        content = driver.execute_script("""
            var r = {};
            // Get all tabs
            r.tabs = [];
            document.querySelectorAll('[ng-click*="tab"]').forEach(function(el) {
                r.tabs.push({
                    text: el.textContent.trim().substring(0, 60),
                    ngClick: (el.getAttribute('ng-click') || '').substring(0, 100)
                });
            });
            // Get all content items
            r.items = [];
            document.querySelectorAll('[ng-repeat]').forEach(function(el) {
                var repeat = el.getAttribute('ng-repeat');
                r.items.push({
                    repeat: repeat,
                    text: el.textContent.trim().substring(0, 100),
                    cls: el.className.substring(0, 60)
                });
            });
            // Look for video-related elements
            r.videoElements = [];
            document.querySelectorAll('video, [class*="video"], [ng-click*="video"]').forEach(function(el) {
                r.videoElements.push({
                    tag: el.tagName,
                    cls: el.className.substring(0, 60),
                    html: el.outerHTML.substring(0, 500)
                });
            });
            // Check Angular scope for content data
            try {
                var scopeEl = document.querySelector('[ng-repeat]');
                if (scopeEl) {
                    var scope = angular.element(scopeEl).scope();
                    r.scopeKeys = Object.keys(scope).filter(function(k) {
                        return !k.startsWith('$') && !k.startsWith('_');
                    });
                    if (scope.render) {
                        r.renderKeys = Object.keys(scope.render);
                    }
                }
            } catch(e) {
                r.scopeError = e.message;
            }
            return JSON.stringify(r);
        """)
        info = json.loads(content)

        print(f"\n  Tabs: {json.dumps(info.get('tabs', []), ensure_ascii=False)}")
        print(f"\n  Items: {len(info.get('items', []))}")
        for item in info.get("items", [])[:10]:
            print(f"    {item}")
        print(f"\n  Video elements: {len(info.get('videoElements', []))}")
        for v in info.get("videoElements", []):
            print(f"    {v}")
        print(f"\n  Scope keys: {info.get('scopeKeys', [])}")
        print(f"  Render keys: {info.get('renderKeys', [])}")

    # Check API calls
    try:
        logs = driver.get_log("performance")
        api_calls = []
        for entry in logs:
            msg = json.loads(entry["message"])["message"]
            if msg["method"] == "Network.requestWillBeSent":
                url = msg.get("params", {}).get("request", {}).get("url", "")
                if "eba.gov.tr" in url and not url.endswith((".js", ".css", ".png", ".jpg", ".woff")):
                    api_calls.append(url)
        print(f"\n  API calls ({len(api_calls)}):")
        for u in api_calls[:30]:
            print(f"    {u[:200]}")
    except Exception:
        pass

    # Save page source
    with open("output/eba_course_explore.html", "w") as f:
        f.write(driver.page_source)


def main():
    os.makedirs("output", exist_ok=True)
    driver = create_driver()
    try:
        eba_login(driver)
        explore_course_content(driver)
    finally:
        driver.quit()
    print("\nKeşif tamamlandı.")


if __name__ == "__main__":
    main()
```

**Step 2: Run discovery**

Run: `cd /mnt/pi-shared/projects/TED && .venv/bin/python src/discover_eba_videos.py`

**Step 3: Analyze findings and adapt**

**Step 4: Commit**

```bash
git add src/discover_eba_videos.py
git commit -m "feat: add EBA video discovery script"
```

---

### Task 7: EBA Videos — Scraper (Post-Discovery)

**Files:**
- Create: `src/scrape_eba_videos.py`

**Depends on:** Task 6 discovery results.

**Step 1: Write scraper based on discovery findings**

Pattern follows `scrape_eba_textbooks.py`:
- EBA login → SPA navigation
- Course list → navigate into each course
- Find video content (CDN URLs or embedded players)
- Download via requests
- Upload to Drive: `EBA Ders Videoları/{Ders}/{Ünite}/{video}.mp4`

**Step 2: Run and verify**

**Step 3: Commit**

```bash
git add src/scrape_eba_videos.py
git commit -m "feat: add EBA video scraper"
```

---

## Execution Order

1. **Task 1-3**: SEBİTV interactive (can run immediately, data already discovered)
2. **Task 4**: MEBI quiz discovery (live exploration needed)
3. **Task 5**: MEBI quiz scraper (depends on Task 4)
4. **Task 6**: EBA video discovery (live exploration needed)
5. **Task 7**: EBA video scraper (depends on Task 6)

Tasks 4 and 6 are discovery tasks that may change the implementation of Tasks 5 and 7 respectively. The plan provides skeleton code that will be adapted based on actual findings.
