#!/usr/bin/env python3
"""Scrape SEBİT VCloud homework (digital assignments) completion status.

Logs in via Selenium, fetches homework list from the internal API,
and saves progress to output/sebit_homework.json.
"""
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from src.json_utils import atomic_json_dump
from src.env_loader import load_env

load_env()

OUTPUT_DIR = "output"
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "sebit_homework.json")

SEBIT_TC = os.environ.get("SEBIT_TC", "")
SEBIT_PASSWORD = os.environ.get("SEBIT_PASSWORD", "")
BASE = "https://www.sebitvcloud.com"
API = "https://uygulama.sebitvcloud.com/VCloudFrontEndService"
EXAM_API = "https://sinavsistemi.sebitvcloud.com/VCloudExamSystem"

# Map SEBİT course codes to normalized course names
COURSE_MAP = {
    "sos": "Sosyal Bilgiler",
    "fen": "Fen Bilimleri",
    "mat": "Matematik",
    "trk": "Türkçe",
    "ing": "İngilizce",
    "dkab": "Din Kültürü",
    "bil": "Bilişim",
}


def create_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-setuid-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=opts)


def sebit_login(driver):
    """Login to SEBİT VCloud."""
    driver.get(f"{BASE}/tr/giris.jsp")
    time.sleep(3)
    driver.find_element(By.NAME, "l_un").send_keys(SEBIT_TC)
    driver.find_element(By.NAME, "l_pw").send_keys(SEBIT_PASSWORD)
    btns = driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
    if btns:
        btns[0].click()
    time.sleep(8)

    if "index.html" in driver.current_url:
        print("[SEBIT-HW] Login successful")
        return True
    print(f"[SEBIT-HW] Login may have failed: {driver.current_url}")
    return False


def xhr_get(driver, url):
    """GET request from browser context with session cookies."""
    return driver.execute_async_script("""
        var cb = arguments[arguments.length - 1];
        var x = new XMLHttpRequest();
        x.open('GET', arguments[0], true);
        x.withCredentials = true;
        x.setRequestHeader('Accept', 'application/json');
        x.onload = function() { cb({s: x.status, b: x.responseText}); };
        x.onerror = function() { cb({s: -1, b: 'error'}); };
        x.send();
    """, url)


def xhr_post(driver, url, data):
    """POST request from browser context with session cookies."""
    return driver.execute_async_script("""
        var cb = arguments[arguments.length - 1];
        var x = new XMLHttpRequest();
        x.open('POST', arguments[0], true);
        x.withCredentials = true;
        x.setRequestHeader('Content-Type',
                           'application/x-www-form-urlencoded');
        x.setRequestHeader('Accept', 'application/json');
        x.onload = function() { cb({s: x.status, b: x.responseText}); };
        x.onerror = function() { cb({s: -1, b: 'error'}); };
        x.send(arguments[1]);
    """, url, data)


def fetch_all_homework(driver):
    """Fetch all homework assignments via paginated API."""
    all_hw = []
    page = 0
    page_size = 50

    while True:
        data = (f"pagenumber={page}&pagesize={page_size}"
                f"&sortfield=enddate&sorttype=desc"
                f"&state=&course=&initialized=&viewType=0")
        r = xhr_post(
            driver,
            f"{API}/home/studenttools/getAssignedFavouriteListSetForStudent",
            data,
        )
        if r.get("s") != 200:
            print(f"[SEBIT-HW] API error at page={page}: status={r.get('s')}")
            break
        parsed = json.loads(r["b"])
        total = parsed.get("totalRecords", 0)
        items = parsed.get("favouriteListWithAssignmentSet", [])
        all_hw.extend(items)
        print(f"[SEBIT-HW] Fetched {len(items)} items "
              f"(page={page}, total={total})")
        if len(all_hw) >= total or not items:
            break
        page += 1

    return all_hw


def fetch_homework_courses(driver):
    """Fetch the list of courses that have homework."""
    r = xhr_get(driver, f"{EXAM_API}/home/exam/gethomeworkcourses")
    if r.get("s") == 200:
        parsed = json.loads(r["b"])
        return parsed.get("courses", {})
    return {}


def parse_homework(hw, course_names):
    """Parse a raw homework item into our output format."""
    code = hw.get("courseName", "")
    course_full = course_names.get(code, COURSE_MAP.get(code, code))
    progress = hw.get("progress", 0)
    state = hw.get("assignmentState", -1)
    start_ts = hw.get("startDate", 0)
    end_ts = hw.get("endDate", 0)

    start_str = ""
    end_str = ""
    if isinstance(start_ts, (int, float)) and start_ts > 0:
        start_str = datetime.fromtimestamp(
            start_ts / 1000).strftime("%Y-%m-%d %H:%M")
    if isinstance(end_ts, (int, float)) and end_ts > 0:
        end_str = datetime.fromtimestamp(
            end_ts / 1000).strftime("%Y-%m-%d %H:%M")

    return {
        "id": hw.get("assignmentId", ""),
        "list_id": hw.get("favouriteListId", ""),
        "title": hw.get("favouriteListName", ""),
        "course_code": code,
        "course": course_full,
        "progress": progress,
        "completed": progress >= 100,
        "state": state,
        "state_text": {0: "Aktif", 1: "Tamamlandı",
                       2: "Süresi Doldu"}.get(state, f"Bilinmiyor({state})"),
        "teacher": hw.get("ownerName", ""),
        "classes": hw.get("assignmentGroupNameList", ""),
        "start_date": start_str,
        "end_date": end_str,
    }


def scrape():
    """Scrape SEBİT homework and return progress data."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    driver = create_driver()

    try:
        if not sebit_login(driver):
            return None

        course_names = fetch_homework_courses(driver)
        all_hw = fetch_all_homework(driver)
        if not all_hw:
            print("[SEBIT-HW] No homework found")
            return None

        parsed = [parse_homework(hw, course_names) for hw in all_hw]

        # Group by course
        by_course = {}
        for hw in parsed:
            by_course.setdefault(hw["course"], []).append(hw)

        completed_count = sum(1 for hw in parsed if hw["completed"])

        progress = {
            "scraped_at": datetime.now().isoformat(),
            "total_homework": len(parsed),
            "completed_count": completed_count,
            "courses": list(by_course.keys()),
            "homework": parsed,
        }

        atomic_json_dump(progress, PROGRESS_FILE)
        print(f"[SEBIT-HW] Saved: {len(parsed)} homework items, "
              f"{completed_count} completed -> {PROGRESS_FILE}")
        return progress

    finally:
        driver.quit()


def main():
    progress = scrape()
    if not progress:
        print("[SEBIT-HW] Scraping failed")
        sys.exit(1)

    print(f"\n=== SEBİT Homework Progress ===")
    print(f"Total: {progress['total_homework']}, "
          f"Completed: {progress['completed_count']}")

    for hw in progress["homework"]:
        if hw["completed"]:
            status = "done"
        elif hw["progress"] > 0:
            status = f"%{hw['progress']:.0f}"
        else:
            status = "not started"
        state = f" [{hw['state_text']}]" if hw["state"] == 2 else ""
        print(f"  [{status}]{state} {hw['course']}: {hw['title']}")


if __name__ == "__main__":
    main()
