#!/usr/bin/env python3
"""Scrape SEBİTV Cloud interactive resources and archive them as local ZIPs."""
import io
import json
import os
import re
import sys
import time
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

import requests as req

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from src.env_loader import load_env

load_env()
TC_NO = os.environ.get("EBA_TC_NO", "")
PASSWORD = os.environ.get("EBA_PASSWORD", "")

BASE = "https://www.sebitvcloud.com"
SPA = f"{BASE}/proxy/VCollabPlayer_v0.0.1929/index.html"
API = "https://uygulama.sebitvcloud.com/VCloudFrontEndService"

TRACKER_FILE = os.path.join("output", "sebitv_interactive_uploaded.json")
DISCOVERY_FILE = os.path.join("output", "sebitv_discovered.json")
CONTENT_DIR = os.path.join("content", "sebitv-interactive")
QBANK_DIR = os.path.join("content", "sebitv-qbank")

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

# Prefixes to try when resolving asset references
ASSET_PREFIXES = [
    "",
    "sco1/resources/",
    "sco1/resources/img/",
    "sco1/resources/images/",
    "sco1/resources/css/",
    "sco1/resources/js/",
    "resources/",
    "resources/img/",
    "resources/images/",
    "resources/css/",
    "resources/js/",
    "sco1/",
]

# File extensions to look for in JS/HTML parsing
ASSET_EXTENSIONS = re.compile(
    r'["\']([^"\'<>\s]+\.(?:png|jpg|jpeg|gif|svg|bmp|webp|ico|mp3|mp4|ogg|wav|'
    r'woff|woff2|ttf|eot|otf|json|xml|swf|pdf))["\']',
    re.IGNORECASE,
)


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
    btns = driver.find_elements(
        By.CSS_SELECTOR, "button[type='submit']"
    )
    if btns:
        btns[0].click()
    time.sleep(6)
    ok = "giris.jsp" not in driver.current_url
    print(f"  Login {'OK' if ok else 'FAIL'}")
    return ok


def get_session(driver):
    """Transfer Selenium cookies to requests Session."""
    # Navigate to SPA to ensure all cookies set
    driver.get(f"{SPA}#/main/dashboardNew?routeConst=dashboard")
    time.sleep(5)

    s = req.Session()
    for c in driver.get_cookies():
        s.cookies.set(
            c["name"], c["value"],
            domain=c.get("domain", ""),
            path=c.get("path", "/"),
        )
    s.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Referer": f"{BASE}/",
        "Origin": BASE,
    })
    return s


def get_repo_type(s, resource_id, locid=""):
    """Get REPOSITORY type via tracking/launch API."""
    locids = []
    if locid:
        locids.append(locid)
    locids.append("")
    for lid in locids:
        url = (
            f"{API}/tracking/launch"
            f"?id={resource_id}&loc=10&locid={lid}"
        )
        try:
            r = s.get(url, timeout=15)
            if r.status_code == 200:
                m = re.search(
                    r'REPOSITORY/([a-f0-9]+)/',
                    r.text,
                )
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


def sanitize(name):
    """Sanitize filename."""
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


# =========================================================================
# Content crawling
# =========================================================================

def _is_error_page(response):
    """Check if response is an HTML error page (short HTML with 'Error' in title)."""
    ct = response.headers.get("Content-Type", "")
    if "text/html" not in ct:
        return False
    if len(response.content) > 200:
        return False
    text = response.text.lower()
    return "<title>" in text and "error" in text


def fetch_file(s, url, timeout=15):
    """Fetch a single file from URL. Returns (content_bytes, content_type) or (None, None)."""
    try:
        r = s.get(url, timeout=timeout, allow_redirects=True)
        if r.status_code != 200:
            return None, None
        if _is_error_page(r):
            return None, None
        return r.content, r.headers.get("Content-Type", "")
    except Exception:
        return None, None


def crawl_known_paths(s, base_url):
    """Fetch all KNOWN_PATHS and return dict {path: content_bytes}."""
    files = {}
    for path in KNOWN_PATHS:
        url = f"{base_url}/{path}"
        content, ct = fetch_file(s, url)
        if content is not None:
            files[path] = content
    return files


def extract_refs_from_html(html_text):
    """Extract asset references from HTML (src, href, url(), pdfName, imageName, fileName)."""
    refs = set()

    # src="..." and href="..."
    for m in re.finditer(r'(?:src|href)\s*=\s*["\']([^"\'<>\s]+)["\']', html_text):
        refs.add(m.group(1))

    # url("...") or url('...') in inline CSS
    for m in re.finditer(r'url\s*\(\s*["\']?([^"\')<>\s]+)["\']?\s*\)', html_text):
        refs.add(m.group(1))

    # pdfName, imageName, fileName attributes (JS-like data in HTML)
    for m in re.finditer(
        r'(?:pdfName|imageName|fileName)["\']?\s*[:=]\s*["\']([^"\']+)', html_text
    ):
        refs.add(m.group(1))

    return refs


def extract_refs_from_js(js_text):
    """Extract image/asset references from JS files."""
    refs = set()
    for m in ASSET_EXTENSIONS.finditer(js_text):
        refs.add(m.group(1))
    return refs


def resolve_and_fetch_refs(s, base_url, refs, already_fetched):
    """Try to fetch each ref under multiple prefixes. Returns new {path: content} entries."""
    new_files = {}
    for ref in refs:
        # Clean up the reference
        ref = ref.strip().lstrip("./")

        # Skip external URLs, data URIs, anchors
        if ref.startswith(("http://", "https://", "data:", "#", "javascript:")):
            continue
        if ref in already_fetched:
            continue

        # Try direct path first
        found = False
        url = f"{base_url}/{ref}"
        content, ct = fetch_file(s, url)
        if content is not None:
            new_files[ref] = content
            found = True

        if not found:
            # Try each prefix
            for prefix in ASSET_PREFIXES:
                if prefix and not ref.startswith(prefix):
                    path = f"{prefix}{ref}"
                else:
                    continue
                if path in already_fetched or path in new_files:
                    continue
                url = f"{base_url}/{path}"
                content, ct = fetch_file(s, url)
                if content is not None:
                    new_files[path] = content
                    break

    return new_files


def crawl_interactive_package(s, base_url):
    """Crawl all static files from an interactive resource package.

    Strategy:
    1. Fetch all KNOWN_PATHS
    2. Parse dataLevel.html for additional asset refs
    3. Parse JS files for image/asset references
    4. Try each ref under multiple prefixes
    """
    # Step 1: Fetch known paths
    files = crawl_known_paths(s, base_url)
    print(f"      Known paths: {len(files)} files fetched")

    all_refs = set()

    # Step 2: Parse dataLevel.html for refs
    if "dataLevel.html" in files:
        try:
            html_text = files["dataLevel.html"].decode("utf-8", errors="replace")
            refs = extract_refs_from_html(html_text)
            all_refs.update(refs)
        except Exception:
            pass

    # Also parse any other HTML files
    for path, content in list(files.items()):
        if path.endswith((".html", ".htm")):
            try:
                html_text = content.decode("utf-8", errors="replace")
                refs = extract_refs_from_html(html_text)
                all_refs.update(refs)
            except Exception:
                pass

    # Step 3: Parse JS files for asset references
    for path, content in list(files.items()):
        if path.endswith(".js"):
            try:
                js_text = content.decode("utf-8", errors="replace")
                refs = extract_refs_from_js(js_text)
                all_refs.update(refs)
            except Exception:
                pass

    # Also parse CSS for url() references
    for path, content in list(files.items()):
        if path.endswith(".css"):
            try:
                css_text = content.decode("utf-8", errors="replace")
                for m in re.finditer(
                    r'url\s*\(\s*["\']?([^"\')<>\s]+)["\']?\s*\)', css_text
                ):
                    all_refs.add(m.group(1))
            except Exception:
                pass

    # Step 4: Resolve and fetch all discovered references
    if all_refs:
        new_files = resolve_and_fetch_refs(
            s, base_url, all_refs, set(files.keys())
        )
        files.update(new_files)
        print(f"      Discovered refs: {len(all_refs)} refs -> {len(new_files)} new files")

    return files


# =========================================================================
# Question extraction from SkipIntroDataJSON.js
# =========================================================================

def extract_question_bank(files):
    """Extract question bank JSON from SkipIntroDataJSON.js if present.

    Returns parsed dict or None if not found/parseable.
    """
    skip_path = "sco1/resources/js/SkipIntroDataJSON.js"
    if skip_path not in files:
        return None

    try:
        text = files[skip_path].decode("utf-8", errors="replace")
    except Exception:
        return None

    if not text.strip():
        return None

    # Extract JSON object: var SkipIntroDataJSON = { ... };
    m = re.search(r'=\s*(\{[\s\S]+\})\s*;?\s*$', text)
    if not m:
        # Try: entire file is JSON
        m = re.search(r'(\{[\s\S]+\})', text)
    if not m:
        return {"_raw": text[:5000], "_parse_error": True}

    json_str = m.group(1)

    # Fix common JS -> JSON issues
    # Remove trailing commas before } or ]
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    # Replace single quotes with double quotes (careful with apostrophes)
    # Only do this if the string uses single quotes for keys/values
    if "'" in json_str and '"' not in json_str[:200]:
        json_str = json_str.replace("'", '"')

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return {"_raw": text[:5000], "_parse_error": True}


# =========================================================================
# ZIP creation
# =========================================================================

def create_zip_archive(files):
    """Create a ZIP archive from {path: content_bytes} dict. Returns bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in sorted(files.items()):
            zf.writestr(path, content)
    return buf.getvalue()


# =========================================================================
# Main processing
# =========================================================================

def process_interactive_resources(resources, s, tracker):
    """Process all interactive resources: crawl and archive locally."""
    print(f"\n[İŞLEM] {len(resources)} etkileşimli kaynak işleniyor...")

    added = 0
    skipped = 0
    failed = 0
    questions_found = 0

    for i, res in enumerate(resources):
        key = res["resourceId"]

        if key in tracker:
            skipped += 1
            continue

        course = res["course"]
        unit = res["unit"]
        title = res["title"]

        print(
            f"\n  [{i + 1}/{len(resources)}] "
            f"{course} > {unit} > {title}"
        )

        try:
            # Get REPOSITORY type
            locid = res.get("lessonPlanId", "")
            repo_type = get_repo_type(s, key, locid)
            if repo_type is None:
                print("    Repo tipi bulunamadi")
                tracker[key] = {
                    "status": "no_repo_type",
                    "title": title,
                }
                save_tracker(tracker)
                failed += 1
                continue

            # Build base URL
            base_url = _content_base(res, repo_type)
            print(f"    Base: .../{repo_type}/{key[:8]}.../{res['version']}/{res['code']}")

            # Crawl all static files
            files = crawl_interactive_package(s, base_url)
            if not files:
                print("    Dosya bulunamadi")
                tracker[key] = {
                    "status": "no_files",
                    "title": title,
                }
                save_tracker(tracker)
                failed += 1
                continue

            print(f"    Toplam: {len(files)} dosya")

            # Extract question bank
            qbank = extract_question_bank(files)
            qbank_path = ""

            if qbank is not None:
                questions_found += 1
                is_parse_error = qbank.get("_parse_error", False)
                status_str = "raw" if is_parse_error else "parsed"
                print(f"    Soru bankasi bulundu ({status_str})")

                qbank_json = json.dumps(
                    qbank, indent=2, ensure_ascii=False
                ).encode("utf-8")
                qbank_dir = os.path.join(
                    QBANK_DIR, sanitize(course), sanitize(unit)
                )
                os.makedirs(qbank_dir, exist_ok=True)
                qbank_path = os.path.join(qbank_dir, f"{sanitize(title)}.json")
                with open(qbank_path, "wb") as fh:
                    fh.write(qbank_json)
                print(f"    Soru bankasi kaydedildi: {qbank_path}")

            # Create ZIP archive
            zip_bytes = create_zip_archive(files)
            zip_size = len(zip_bytes)
            print(f"    ZIP: {zip_size / 1024:.1f} KB ({len(files)} dosya)")

            if zip_size < 500:
                print(f"    ZIP cok kucuk ({zip_size} bytes), atla")
                tracker[key] = {
                    "status": "zip_too_small",
                    "title": title,
                    "fileCount": len(files),
                }
                save_tracker(tracker)
                failed += 1
                continue

            dest_dir = os.path.join(
                CONTENT_DIR, sanitize(course), sanitize(unit)
            )
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, f"{sanitize(title)}.zip")
            with open(dest_path, "wb") as fh:
                fh.write(zip_bytes)

            tracker[key] = {
                "course": course,
                "unit": unit,
                "title": title,
                "type": res["type"],
                "path": dest_path,
                "zipSize": zip_size,
                "fileCount": len(files),
                "repoType": repo_type,
            }
            if qbank_path:
                tracker[key]["qbankPath"] = qbank_path
                tracker[key]["hasQuestions"] = True

            save_tracker(tracker)
            added += 1
            print(f"    Kaydedildi: {dest_path}")

        except req.exceptions.Timeout:
            print("    Zaman asimi")
            failed += 1
        except req.exceptions.ConnectionError:
            print("    Baglanti hatasi")
            failed += 1
        except Exception as e:
            print(f"    Hata: {e}")
            failed += 1

    print(
        f"\n  Sonuc: +{added} kaydedildi, "
        f"={skipped} atlandi, "
        f"x{failed} basarisiz, "
        f"?{questions_found} soru bankasi"
    )
    return added, skipped, failed


def main():
    os.makedirs("output", exist_ok=True)
    tracker = load_tracker()
    print(f"[Tracker] {len(tracker)} kaynak zaten islenmi\u015f")

    # Load discovery data
    if not os.path.exists(DISCOVERY_FILE):
        print(f"HATA: {DISCOVERY_FILE} bulunamadi!")
        print("Once scrape_sebitv.py calistirin.")
        return

    with open(DISCOVERY_FILE) as f:
        resources = json.load(f)
    print(f"[Kesif] {len(resources)} toplam kaynak yuklendi")

    # Filter to interactive resources: duration==0 AND fileType != "pdf"
    interactive = [
        r for r in resources
        if r.get("duration", 0) == 0
        and r.get("fileType", "") != "pdf"
    ]
    print(
        f"  {len(interactive)} etkilesimli kaynak "
        f"(duration=0, fileType!=pdf) / {len(resources)} toplam"
    )

    if not interactive:
        print("Hic etkilesimli kaynak bulunamadi!")
        return

    # Login to SEBİTV
    print("\n[1/2] SEBITV giris yapiliyor...")
    driver = create_driver()
    try:
        ok = sebitv_login(driver)
        if not ok:
            print("HATA: SEBITV girisi basarisiz!")
            return
        s = get_session(driver)
    finally:
        driver.quit()

    print("\n[2/2] Etkilesimli kaynaklar arsivleniyor...")
    added, skipped, failed = process_interactive_resources(
        interactive, s, tracker,
    )

    print(f"\n{'=' * 60}")
    print("  SEBITV ETKILESIMLI TAMAMLANDI")
    print(f"  Toplam kaynak: {len(resources)}")
    print(f"  Etkilesimli: {len(interactive)}")
    print(f"  Kaydedilen: {added}")
    print(f"  Atlanan: {skipped}")
    print(f"  Basarisiz: {failed}")
    print("=" * 60)


if __name__ == "__main__":
    main()
