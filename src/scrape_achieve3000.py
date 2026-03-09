#!/usr/bin/env python3
"""Scrape Achieve3000 lesson completion status.

Logs in via Selenium, fetches lesson list from the internal API,
and saves teacher-assigned lesson progress to
output/achieve3000_progress.json.
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
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "achieve3000_progress.json")

A3K_USERNAME = os.environ.get("A3K_USERNAME", "")
A3K_PASSWORD = os.environ.get("A3K_PASSWORD", "")

# The 5 core steps that define lesson completion
CORE_STEPS = {"Ready", "Read", "Respond", "Reflect", "Write"}


def create_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-setuid-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=opts)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', "
                    "{get: () => undefined});"},
    )
    return driver


def a3k_login(driver):
    """Login to Achieve3000: credentials + class/location selection."""
    driver.get("https://portal.achieve3000.com/index")
    time.sleep(3)

    driver.find_element(By.ID, "login_name1").send_keys(A3K_USERNAME)
    driver.find_element(By.ID, "password1").send_keys(A3K_PASSWORD)
    driver.find_element(By.ID, "loginButton").click()
    time.sleep(5)

    # Select "In School" location and continue
    try:
        driver.find_element(By.ID, "inSchoolFormRadioButton").click()
        time.sleep(1)
        driver.find_element(By.ID, "loginButton").click()
        time.sleep(8)
    except Exception as e:
        print(f"[A3K] Location selection error: {e}")

    if "/home" in driver.current_url:
        print("[A3K] Login successful")
        return True
    print(f"[A3K] Login may have failed: {driver.current_url}")
    driver.save_screenshot(os.path.join(OUTPUT_DIR, "a3k_login_fail.png"))
    return False


def xhr_get(driver, url):
    """XHR from browser context — carries session cookies."""
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


def fetch_all_lessons(driver):
    """Fetch all lessons via paginated API."""
    base = "https://portal.achieve3000.com"
    all_lessons = []
    offset = 0
    limit = 200

    while True:
        url = f"{base}/api/v1/student/my-lessons?offset={offset}&limit={limit}"
        r = xhr_get(driver, url)
        if r.get("s") != 200:
            print(f"[A3K] API error at offset={offset}: status={r.get('s')}")
            break
        data = json.loads(r["b"])
        lessons = data.get("lessons", [])
        all_lessons.extend(lessons)
        total = data.get("count", 0)
        print(f"[A3K] Fetched {len(lessons)} lessons "
              f"(offset={offset}, total={total})")
        if len(all_lessons) >= total or not lessons:
            break
        offset += limit

    return all_lessons


def is_lesson_completed(steps):
    """A lesson is completed when all 5 core steps are done."""
    for step in steps:
        if step.get("stepName") in CORE_STEPS:
            if step.get("status") != "complete":
                return False
    return True


def parse_lesson(lesson):
    """Parse a lesson record into our output format."""
    steps = lesson.get("steps", [])
    core_steps = [s for s in steps if s.get("stepName") in CORE_STEPS]
    completed_steps = sum(
        1 for s in core_steps if s.get("status") == "complete"
    )
    total_steps = len(core_steps)

    # Extract score from Respond step (the quiz score)
    score = None
    for s in steps:
        if s.get("score") and s["score"] != "":
            try:
                score = int(s["score"])
            except (ValueError, TypeError):
                pass

    lid = lesson.get("lessonId")
    lesson_url = lesson.get("lessonUrl", f"/lesson?lid={lid}")
    if lesson_url.startswith("/"):
        lesson_url = f"https://portal.achieve3000.com{lesson_url}"

    return {
        "lesson_id": lid,
        "title": lesson.get("lessonName", f"Lesson {lid}"),
        "url": lesson_url,
        "category": lesson.get("categoryName", ""),
        "subcategory": lesson.get("sCategoryName", ""),
        "lesson_type": lesson.get("lessonType", ""),
        "start_date": lesson.get("startDate", ""),
        "end_date": lesson.get("endDate", ""),
        "is_teacher_assigned": lesson.get("isTeacherAssigned", False),
        "completed": is_lesson_completed(steps),
        "completed_steps": completed_steps,
        "total_steps": total_steps,
        "score": score,
        "steps": {
            s["stepName"]: s.get("status") == "complete"
            for s in steps
        },
    }


def scrape():
    """Scrape Achieve3000 and return progress data."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    driver = create_driver()

    try:
        if not a3k_login(driver):
            return None

        all_lessons = fetch_all_lessons(driver)
        if not all_lessons:
            print("[A3K] No lessons found")
            return None

        # Parse all lessons
        parsed = [parse_lesson(l) for l in all_lessons]

        # Separate teacher-assigned (homework) from self-assigned
        teacher_assigned = [l for l in parsed if l["is_teacher_assigned"]]
        completed_count = sum(1 for l in teacher_assigned if l["completed"])

        # Also get dashboard stats
        r = xhr_get(
            driver,
            "https://portal.achieve3000.com"
            "/api/v1/student-dashboard/fetch/my-lessons",
        )
        dashboard = {}
        if r.get("s") == 200:
            dash_data = json.loads(r["b"])
            dashboard = dash_data.get("activities", {})

        progress = {
            "scraped_at": datetime.now().isoformat(),
            "class_name": "6C 25-26",
            "dashboard_stats": dashboard,
            "total_lessons": len(parsed),
            "teacher_assigned_count": len(teacher_assigned),
            "teacher_assigned_completed": completed_count,
            "lessons": teacher_assigned,
        }

        atomic_json_dump(progress, PROGRESS_FILE)
        print(f"[A3K] Saved: {len(teacher_assigned)} teacher-assigned lessons, "
              f"{completed_count} completed -> {PROGRESS_FILE}")
        return progress

    finally:
        driver.quit()


def main():
    progress = scrape()
    if not progress:
        print("[A3K] Scraping failed")
        sys.exit(1)

    print(f"\n=== Achieve3000 Progress ===")
    stats = progress.get("dashboard_stats", {})
    if stats:
        print(f"Activities: {stats.get('completed', 0)}/{stats.get('target', 0)} "
              f"(first try: {stats.get('firstTryScore', 0)}%)")

    print(f"Teacher-Assigned: {progress['teacher_assigned_completed']}/"
          f"{progress['teacher_assigned_count']} completed")

    for l in progress["lessons"]:
        if l["completed"]:
            status = "done"
        elif l["completed_steps"] > 0:
            status = f"{l['completed_steps']}/{l['total_steps']}"
        else:
            status = "not started"
        score_str = f" ({l['score']}%)" if l["score"] is not None else ""
        print(f"  [{status}]{score_str} {l['title']}")


if __name__ == "__main__":
    main()
