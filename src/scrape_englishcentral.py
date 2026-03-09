#!/usr/bin/env python3
"""Scrape English Central homework completion status.

Logs in via Selenium, intercepts Angular SPA API responses to get
video list and per-activity completion data. Saves to
output/englishcentral_progress.json.
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
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "englishcentral_progress.json")

EC_EMAIL = os.environ.get("EC_EMAIL", "")
EC_PASSWORD = os.environ.get("EC_PASSWORD", "")
CLASS_ID = os.environ.get("EC_CLASS_ID", "204944")

# Activity type IDs → human-readable names
ACTIVITY_TYPES = {
    9: "watch",
    10: "watch_again",
    11: "learn",
    15: "speak",
    24: "quiz",
    32: "comprehension",
    40: "watch_video",
    55: "vocab_quiz",
    65: "ai_speak",
}

# A video is "completed" when watch + learn are done.
# The SPA shows green "COMPLETED" badge for these.
# watch_video (40) or watch_again (10) count as "watched".
WATCH_ACTIVITIES = {"watch", "watch_again", "watch_video"}
LEARN_ACTIVITIES = {"learn"}


INTERCEPTOR_JS = """
window.__ecResponses = {};
(function() {
    var origFetch = window.fetch;
    window.fetch = function() {
        var url = arguments[0];
        if (typeof url === 'string') {
            return origFetch.apply(this, arguments).then(function(resp) {
                if (url.indexOf('/rest/') !== -1 &&
                    url.indexOf('datadog') === -1) {
                    var cloned = resp.clone();
                    cloned.text().then(function(body) {
                        window.__ecResponses[url] = {
                            status: resp.status, body: body
                        };
                    });
                }
                return resp;
            });
        }
        return origFetch.apply(this, arguments);
    };
    var origOpen = XMLHttpRequest.prototype.open;
    var origSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function(method, url) {
        this.__url = url;
        return origOpen.apply(this, arguments);
    };
    XMLHttpRequest.prototype.send = function() {
        var self = this;
        this.addEventListener('load', function() {
            var u = self.__url;
            if (u && u.indexOf('/rest/') !== -1 &&
                u.indexOf('datadog') === -1) {
                window.__ecResponses[u] = {
                    status: self.status, body: self.responseText
                };
            }
        });
        return origSend.apply(this, arguments);
    };
})();
"""


def create_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-setuid-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=opts)
    # Inject interceptor on every page load via CDP
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": INTERCEPTOR_JS},
    )
    return driver


def ec_login(driver):
    """Login to English Central via the modal dialog."""
    driver.get("https://tr.englishcentral.com/browse/videos")
    time.sleep(3)
    driver.find_element(By.ID, "sign-in-button").click()
    time.sleep(2)
    modal = driver.find_element(By.CSS_SELECTOR, "ngb-modal-window")
    modal.find_element(
        By.ID, "login-username-input-box"
    ).send_keys(EC_EMAIL)
    modal.find_element(
        By.ID, "login-password-input-box"
    ).send_keys(EC_PASSWORD)
    for btn in modal.find_elements(By.CSS_SELECTOR, "button"):
        if "giriş" in btn.text.strip().lower():
            btn.click()
            break
    time.sleep(5)
    if "/myclass/" in driver.current_url:
        print("[EC] Login successful")
        return True
    print(f"[EC] Login may have failed: {driver.current_url}")
    driver.save_screenshot(
        os.path.join(OUTPUT_DIR, "ec_login_fail.png")
    )
    return False


def collect_responses(driver):
    """Collect intercepted API responses from the page."""
    return driver.execute_script(
        "return window.__ecResponses || {};"
    )


def extract_api_data(responses):
    """Parse intercepted responses into video list, details, activity."""
    video_ids = []
    dialog_details = {}
    activity_data = {}

    for url, resp in responses.items():
        if resp.get("status") != 200:
            continue
        try:
            data = json.loads(resp["body"])
        except (json.JSONDecodeError, KeyError):
            continue

        if "commerce/my/english/video" in url and "count" not in url:
            if isinstance(data, list):
                video_ids.extend(data)

        if "content/dialog" in url:
            if isinstance(data, list):
                for d in data:
                    did = d.get("dialogID")
                    if did:
                        dialog_details[did] = d

        if "dialogs/v1" in url:
            dialogs = data.get("dialogs", []) if isinstance(data, dict) else []
            for d in dialogs:
                did = d.get("id") or d.get("dialogID")
                if did and did not in dialog_details:
                    dialog_details[did] = {
                        "dialogID": did,
                        "title": d.get("title", ""),
                        "dialogURL": d.get("dialogURL", ""),
                        "difficulty": d.get("difficulty"),
                        "duration": d.get("duration", ""),
                    }

        if "report/activity/dialog" in url:
            if isinstance(data, list):
                for item in data:
                    did = item.get("dialogID")
                    if did:
                        activity_data[did] = item

    return video_ids, dialog_details, activity_data


def parse_activities(activity_item):
    """Parse activity list into structured completion info."""
    result = {}
    for act in activity_item.get("activities", []):
        type_id = act.get("activityTypeID")
        name = ACTIVITY_TYPES.get(type_id, f"type_{type_id}")
        result[name] = {
            "started": act.get("started", False),
            "completed": act.get("completed", False),
            "points": act.get("activityPoints", 0),
        }
    return result


def is_video_completed(activities_parsed):
    """A video is completed if watch + learn activities are done."""
    watched = any(
        activities_parsed.get(a, {}).get("completed", False)
        for a in WATCH_ACTIVITIES
    )
    learned = any(
        activities_parsed.get(a, {}).get("completed", False)
        for a in LEARN_ACTIVITIES
    )
    return watched and learned


def scrape():
    """Scrape English Central and return progress data."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    driver = create_driver()

    try:
        if not ec_login(driver):
            return None

        all_video_ids = []
        all_details = {}
        all_activity = {}

        # CDP interceptor is already active from create_driver().
        # Navigate to myclass videos page — interceptor catches
        # all API responses automatically.
        myclass_url = (
            f"https://www.englishcentral.com/myclass/"
            f"{CLASS_ID}/0/videos"
        )
        driver.get(myclass_url)
        time.sleep(8)

        responses = collect_responses(driver)
        ids, details, activity = extract_api_data(responses)
        all_video_ids = ids
        all_details.update(details)
        all_activity.update(activity)
        print(f"[EC] Page 0: {len(ids)} video IDs, "
              f"{len(details)} details, "
              f"{len(activity)} activity records")

        # Click through pagination pages (page 2, 3, ...)
        for page_num in range(2, 10):
            page_links = driver.find_elements(
                By.CSS_SELECTOR, ".page-link"
            )
            clicked = False
            for pl in page_links:
                if pl.text.strip() == str(page_num):
                    driver.execute_script(
                        "arguments[0].scrollIntoView(true);",
                        pl,
                    )
                    time.sleep(1)
                    driver.execute_script(
                        "arguments[0].click();", pl
                    )
                    clicked = True
                    time.sleep(6)
                    break
            if not clicked:
                break
            responses = collect_responses(driver)
            ids2, det2, act2 = extract_api_data(responses)
            new_ids = [i for i in ids2
                       if i not in all_video_ids]
            all_video_ids.extend(new_ids)
            all_details.update(det2)
            all_activity.update(act2)
            if new_ids:
                print(f"[EC] Page {page_num}: "
                      f"+{len(new_ids)} video IDs "
                      f"(total: {len(all_video_ids)})")
            else:
                break

        # Build output
        videos = []
        for did in all_video_ids:
            detail = all_details.get(did, {})
            act_item = all_activity.get(did, {})
            activities = parse_activities(act_item)
            completed = is_video_completed(activities)

            video_url = detail.get(
                "dialogURL",
                f"https://www.englishcentral.com/video/{did}"
            )

            videos.append({
                "dialog_id": did,
                "title": detail.get("title", f"Video {did}"),
                "url": video_url,
                "difficulty": detail.get("difficulty"),
                "duration": detail.get("duration", ""),
                "completed": completed,
                "started": any(
                    a.get("started") for a in activities.values()
                ),
                "activities": {
                    k: {"started": v["started"],
                        "completed": v["completed"]}
                    for k, v in activities.items()
                },
            })

        completed_count = sum(1 for v in videos if v["completed"])
        progress = {
            "scraped_at": datetime.now().isoformat(),
            "class_name": "6C",
            "class_id": int(CLASS_ID),
            "total_videos": len(videos),
            "completed_videos": completed_count,
            "videos": videos,
        }

        atomic_json_dump(progress, PROGRESS_FILE)
        print(f"[EC] Saved: {len(videos)} videos, "
              f"{completed_count} completed → {PROGRESS_FILE}")
        return progress

    finally:
        driver.quit()


def main():
    progress = scrape()
    if not progress:
        print("[EC] Scraping failed")
        sys.exit(1)

    print(f"\n=== English Central Progress ===")
    print(f"Videos: {progress['completed_videos']}/{progress['total_videos']} completed")
    for v in progress["videos"]:
        status = "✅" if v["completed"] else ("🔄" if v["started"] else "⬜")
        print(f"  {status} {v['title']}")


if __name__ == "__main__":
    main()
