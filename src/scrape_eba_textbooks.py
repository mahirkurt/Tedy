#!/usr/bin/env python3
"""Scrape EBA textbook PDFs and upload to Google Drive."""
import json
import os
import sys
import time
import requests as req

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from googleapiclient.http import MediaInMemoryUpload

from src.sync_to_google import get_services, _get_or_create_folder, get_year_root
from src.env_loader import load_env

load_env()
TC_NO = os.environ.get("EBA_TC_NO", "")
PASSWORD = os.environ.get("EBA_PASSWORD", "")

DOWNLOAD_BASE = "https://iys.eba.gov.tr/ders/ContentSystem/"
TRACKER_FILE = os.path.join("output", "eba_textbooks_uploaded.json")


def create_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-setuid-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=opts)


def eba_login(driver):
    driver.get("https://giris.eba.gov.tr/EBA_GIRIS/student.jsp")
    time.sleep(3)
    driver.find_element(By.ID, "tckn").send_keys(TC_NO)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    for btn in driver.find_elements(By.CSS_SELECTOR,
                                     "button.nl-form-send-btn"):
        if btn.text.strip() == "Giriş":
            btn.click()
            break
    time.sleep(5)
    print(f"[EBA LOGIN] {driver.current_url}")


def get_cdn_url_via_js(driver, download_url):
    """Resolve CDN URL using JS fetch from within the SPA (carries cookies)."""
    full_url = DOWNLOAD_BASE + download_url
    try:
        cdn_url = driver.execute_script(f"""
            try {{
                var resp = await fetch('{full_url}', {{
                    method: 'HEAD',
                    redirect: 'follow'
                }});
                if (resp.url && resp.url.indexOf('cdn') !== -1 &&
                    resp.url.indexOf('.pdf') !== -1) {{
                    return resp.url;
                }}
                // HEAD may not follow redirect properly, try opening in new tab
                return null;
            }} catch(e) {{
                return 'ERROR: ' + e.message;
            }}
        """)
        if cdn_url and cdn_url.startswith("http"):
            return cdn_url
        if cdn_url and cdn_url.startswith("ERROR"):
            print(f"    JS fetch: {cdn_url}")
    except Exception as e:
        print(f"    JS CDN resolve failed: {e}")
    return None


def get_cdn_url_via_intercept(driver, download_url):
    """Resolve CDN URL by intercepting window.open and using a hidden link."""
    full_url = DOWNLOAD_BASE + download_url
    try:
        # Use XMLHttpRequest which follows redirects
        cdn_url = driver.execute_script(f"""
            return new Promise(function(resolve) {{
                var xhr = new XMLHttpRequest();
                xhr.open('GET', '{full_url}', true);
                xhr.onreadystatechange = function() {{
                    if (xhr.readyState >= 2) {{
                        var url = xhr.responseURL;
                        xhr.abort();
                        if (url && url.indexOf('cdn') !== -1) {{
                            resolve(url);
                        }} else {{
                            resolve(null);
                        }}
                    }}
                }};
                xhr.onerror = function() {{ resolve(null); }};
                xhr.timeout = 30000;
                xhr.ontimeout = function() {{ resolve(null); }};
                xhr.send();
            }});
        """)
        if cdn_url and cdn_url.startswith("http"):
            return cdn_url
    except Exception as e:
        print(f"    XHR CDN resolve failed: {e}")
    return None


def get_cdn_url(driver, download_url, session=None):
    """Resolve CDN URL - tries JS first, then XHR, then browser navigation."""
    # Try JS fetch from within the SPA
    cdn_url = get_cdn_url_via_js(driver, download_url)
    if cdn_url:
        return cdn_url

    # Try XHR approach
    cdn_url = get_cdn_url_via_intercept(driver, download_url)
    if cdn_url:
        return cdn_url

    # Try requests session
    full_url = DOWNLOAD_BASE + download_url
    if session:
        try:
            resp = session.get(full_url, allow_redirects=True, timeout=30,
                               stream=True)
            resp.close()
            if "cdn" in resp.url and ".pdf" in resp.url:
                return resp.url
        except Exception as e:
            print(f"    Requests CDN resolve failed: {e}")

    # Fallback: browser navigation (disrupts SPA)
    driver.get(full_url)
    time.sleep(5)
    final_url = driver.current_url
    if "cdn" in final_url and ".pdf" in final_url:
        return final_url
    return None


def get_session_from_driver(driver):
    """Create a requests session with cookies from the browser."""
    session = req.Session()
    for cookie in driver.get_cookies():
        session.cookies.set(cookie["name"], cookie["value"],
                           domain=cookie.get("domain", ""))
    session.headers.update({
        "User-Agent": driver.execute_script("return navigator.userAgent"),
    })
    return session


def get_all_textbooks(driver):
    """Navigate to each course page and collect textbook data."""
    print("\n[Textbooks] Collecting from all courses...")

    # Go to SPA
    driver.get("https://ders.eba.gov.tr/ders/proxy/VCollabPlayer_v0.0.1064/"
               "index.html#/main/dashboard/3/6/0")
    time.sleep(5)

    # Get course list
    courses = driver.execute_script("""
        try {
            var items = document.querySelectorAll(
                '[ng-repeat="onelesson in render.allLessons"]');
            if (items.length === 0) {
                // Navigate to Dersler first
                var sidebar = document.querySelectorAll(
                    '[ng-click="itemSelected(item)"]');
                for (var i = 0; i < sidebar.length; i++) {
                    if (sidebar[i].textContent.trim() === 'Dersler') {
                        sidebar[i].click();
                        return 'NAVIGATING';
                    }
                }
            }
            var result = [];
            for (var i = 0; i < items.length; i++) {
                var scope = angular.element(items[i]).scope();
                if (scope.onelesson) {
                    result.push({
                        name: scope.onelesson.name,
                        nodeId: scope.onelesson.nodeId,
                        courseName: scope.onelesson.courseName
                    });
                }
            }
            return JSON.stringify(result);
        } catch(e) {
            return 'ERROR: ' + e.message;
        }
    """)

    if courses == "NAVIGATING":
        time.sleep(5)
        courses = driver.execute_script("""
            var items = document.querySelectorAll(
                '[ng-repeat="onelesson in render.allLessons"]');
            var result = [];
            for (var i = 0; i < items.length; i++) {
                var scope = angular.element(items[i]).scope();
                if (scope.onelesson) {
                    result.push({
                        name: scope.onelesson.name,
                        nodeId: scope.onelesson.nodeId,
                        courseName: scope.onelesson.courseName
                    });
                }
            }
            return JSON.stringify(result);
        """)

    try:
        course_list = json.loads(courses)
    except (json.JSONDecodeError, TypeError):
        print(f"  Could not get courses: {courses}")
        return []

    # Deduplicate
    seen = set()
    unique_courses = []
    for c in course_list:
        if c["nodeId"] not in seen:
            seen.add(c["nodeId"])
            unique_courses.append(c)

    print(f"  Found {len(unique_courses)} courses")

    all_books = []

    for course in unique_courses:
        print(f"\n  --- {course['name']} ---")

        # Navigate to course page
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

        # Extract textbook data from the course page
        books_data = driver.execute_script("""
            try {
                // Find book items on the page
                var bookBtns = document.querySelectorAll(
                    '[ng-click="downloadPdf(one)"]');
                if (bookBtns.length === 0) {
                    // Try Angular scope for book data
                    var elements = document.querySelectorAll(
                        '[ng-repeat*="render"]');
                    for (var i = 0; i < elements.length; i++) {
                        var scope = angular.element(elements[i]).scope();
                        if (scope && scope.render &&
                            scope.render.currentTabData) {
                            return JSON.stringify(
                                scope.render.currentTabData.map(function(b) {
                                    return {
                                        title: b.title || b.name || '?',
                                        id: b.id || '',
                                        downloadUrl: b.downloadUrl || ''
                                    };
                                })
                            );
                        }
                    }
                }

                // Try via downloadPdf buttons
                var books = [];
                for (var i = 0; i < bookBtns.length; i++) {
                    var scope = angular.element(bookBtns[i]).scope();
                    var book = scope.one || {};
                    books.push({
                        title: book.title || book.name || '?',
                        id: book.id || '',
                        downloadUrl: book.downloadUrl || ''
                    });
                }
                return JSON.stringify(books);
            } catch(e) {
                return '[]';
            }
        """)

        try:
            books = json.loads(books_data)
            for b in books:
                if b.get("downloadUrl"):
                    b["course"] = course["name"]
                    all_books.append(b)
                    print(f"    Book: {b['title']}")
        except json.JSONDecodeError:
            pass

        # Go back to courses list
        driver.execute_script("""
            var sidebar = document.querySelectorAll(
                '[ng-click="itemSelected(item)"]');
            for (var i = 0; i < sidebar.length; i++) {
                if (sidebar[i].textContent.trim() === 'Dersler') {
                    sidebar[i].click();
                    break;
                }
            }
        """)
        time.sleep(3)

    # Deduplicate books
    seen_ids = set()
    unique_books = []
    for b in all_books:
        if b["id"] not in seen_ids:
            seen_ids.add(b["id"])
            unique_books.append(b)

    print(f"\n  Total unique books: {len(unique_books)}")
    return unique_books


def download_and_upload(driver, books, drive_service):
    """Download PDFs from EBA CDN and upload to Google Drive."""
    print("\n[Drive] Uploading textbooks...")

    # Create a requests session with browser cookies
    session = get_session_from_driver(driver)

    # Load tracker
    uploaded = {}
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE) as f:
            uploaded = json.load(f)

    # Create Drive folder structure
    root_id = _get_or_create_folder(
        drive_service, "Ders Kitapları",
        parent_id=get_year_root(drive_service))

    added = 0
    skipped = 0

    for book in books:
        book_id = book["id"]
        title = book["title"]

        if book_id in uploaded:
            print(f"  Skip (exists): {title}")
            skipped += 1
            continue

        print(f"\n  Downloading: {title}...")

        # Get CDN URL (tries requests first, falls back to Selenium)
        cdn_url = get_cdn_url(driver, book["downloadUrl"], session)
        if not cdn_url:
            print(f"    Failed to get CDN URL")
            continue

        print(f"    CDN: {cdn_url[:80]}...")

        # Download PDF
        try:
            resp = req.get(cdn_url, timeout=120)
            if resp.status_code != 200:
                print(f"    Download failed: HTTP {resp.status_code}")
                continue

            pdf_size = len(resp.content)
            print(f"    Downloaded: {pdf_size / 1024 / 1024:.1f} MB")

            if pdf_size < 1000:
                print(f"    Too small, skipping")
                continue

            # Get/create course subfolder
            course = book.get("course", "Genel")
            # Simplify course name
            course_short = (course.replace(" (Yeni Müfredat)", "")
                           .replace("(Yeni Müfredat)", "").strip())
            subfolder_id = _get_or_create_folder(
                drive_service, course_short, parent_id=root_id
            )

            # Upload to Drive
            filename = f"{title}.pdf"
            media = MediaInMemoryUpload(
                resp.content,
                mimetype="application/pdf",
            )
            file_meta = {
                "name": filename,
                "parents": [subfolder_id],
            }
            result = drive_service.files().create(
                body=file_meta, media_body=media,
                fields="id,webViewLink",
            ).execute()

            uploaded[book_id] = {
                "title": title,
                "course": course,
                "driveId": result["id"],
                "link": result.get("webViewLink", ""),
                "size": pdf_size,
            }
            added += 1
            print(f"    Uploaded: {result.get('webViewLink', '')}")

        except Exception as e:
            print(f"    Error: {e}")

    # Save tracker
    with open(TRACKER_FILE, "w") as f:
        json.dump(uploaded, f, indent=2, ensure_ascii=False)

    print(f"\n  Drive: +{added} uploaded, ={skipped} skipped")
    return uploaded


def main():
    os.makedirs("output", exist_ok=True)

    print("[1/3] EBA Login + collect textbooks...")
    driver = create_driver()

    try:
        eba_login(driver)

        # Go to SPA dashboard
        driver.get("https://ders.eba.gov.tr/ders/proxy/VCollabPlayer_v0.0.1064/"
                    "index.html#/main/dashboard/3/6/0")
        time.sleep(5)

        # Navigate to Dersler
        driver.execute_script("""
            var sidebar = document.querySelectorAll(
                '[ng-click="itemSelected(item)"]');
            for (var i = 0; i < sidebar.length; i++) {
                if (sidebar[i].textContent.trim() === 'Dersler') {
                    sidebar[i].click();
                    break;
                }
            }
        """)
        time.sleep(5)

        books = get_all_textbooks(driver)

        if not books:
            # Fallback: use the previously discovered books
            print("\n  Using fallback book list...")
            fallback_path = "output/eba_all_textbooks_complete.json"
            if os.path.exists(fallback_path):
                with open(fallback_path) as f:
                    fb = json.load(f)
                books = [{"title": v["title"], "id": v["id"],
                          "downloadUrl": v["downloadUrl"],
                          "course": "Genel"}
                         for v in fb.values() if v.get("downloadUrl")]
                print(f"  Loaded {len(books)} fallback books")

        print(f"\n[2/3] Downloading + uploading {len(books)} books...")
        _, _, _, drive_svc = get_services()
        uploaded = download_and_upload(driver, books, drive_svc)

        print(f"\n[3/3] Summary")
        for book_id, info in uploaded.items():
            print(f"  {info['title']} ({info.get('course', '?')}) "
                  f"-> {info.get('link', 'N/A')}")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
