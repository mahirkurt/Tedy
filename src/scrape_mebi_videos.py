#!/usr/bin/env python3
"""Scrape ALL MEBI videos and save them under content/mebi/."""
import json
import os
import re
import sys
import time

import requests as req

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from src.env_loader import load_env

load_env()
TC_NO = os.environ.get("EBA_TC_NO", "")
PASSWORD = os.environ.get("EBA_PASSWORD", "")

TRACKER_FILE = os.path.join("output", "mebi_videos_uploaded.json")
DISCOVERY_FILE = os.path.join("output", "mebi_videos_discovered.json")
CONTENT_DIR = os.path.join("content", "mebi")

COURSES = {
    "Din Kültürü": "66ed9e38-25bf-4800-0877-08ddc2afb3ce",
    "Fen Bilimleri": "1f4b44bc-a0ac-4b08-087c-08ddc2afb3ce",
    "İngilizce": "cf7102fa-6b36-4a6a-087d-08ddc2afb3ce",
    "Matematik": "1c9295cc-16a0-4a7c-0882-08ddc2afb3ce",
    "Sosyal Bilgiler": "4b2a1a59-f118-45c9-0883-08ddc2afb3ce",
    "Türkçe": "72a6b6a9-3473-414a-0888-08ddc2afb3ce",
}

MEBI_BASE = "https://mebi.eba.gov.tr"
CDN_PATTERN = re.compile(
    r"https://ogm-large-cdn\.eba\.gov\.tr/mebi/video/[a-z0-9]+\.mp4"
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


def eba_login(driver):
    driver.get("https://giris.eba.gov.tr/EBA_GIRIS/student.jsp")
    time.sleep(3)
    driver.find_element(By.ID, "tckn").send_keys(TC_NO)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    for btn in driver.find_elements(By.CSS_SELECTOR, "button.nl-form-send-btn"):
        if btn.text.strip() == "Giriş":
            btn.click()
            break
    time.sleep(5)
    print(f"[EBA LOGIN] {driver.current_url}")


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


def load_tracker():
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE) as f:
            return json.load(f)
    return {}


def save_tracker(tracker):
    with open(TRACKER_FILE, "w") as f:
        json.dump(tracker, f, indent=2, ensure_ascii=False)


def discover_units(driver, course_name, course_uuid):
    url = f"{MEBI_BASE}/student/section/upper-subjects/{course_uuid}"
    driver.get(url)
    time.sleep(5)

    units = []
    links = driver.find_elements(
        By.CSS_SELECTOR, 'a[href*="/student/section/lower-subjects/"]'
    )
    for link in links:
        href = link.get_attribute("href") or ""
        uuid = href.split("/lower-subjects/")[-1].split("?")[0].strip("/")
        name = link.text.strip()
        if uuid and name:
            units.append({"name": name, "uuid": uuid})

    # Deduplicate by uuid
    seen = set()
    unique = []
    for u in units:
        if u["uuid"] not in seen:
            seen.add(u["uuid"])
            unique.append(u)

    print(f"  [{course_name}] {len(unique)} ünite bulundu")
    return unique


def discover_topics(driver, unit_name, unit_uuid):
    url = f"{MEBI_BASE}/student/section/lower-subjects/{unit_uuid}"
    driver.get(url)
    time.sleep(5)

    topics = []
    links = driver.find_elements(
        By.CSS_SELECTOR, 'a[href*="/student/section/subject-details/"]'
    )
    for link in links:
        href = link.get_attribute("href") or ""
        uuid = href.split("/subject-details/")[-1].split("?")[0].strip("/")
        name = link.text.strip()
        if uuid and name:
            topics.append({"name": name, "uuid": uuid})

    seen = set()
    unique = []
    for t in topics:
        if t["uuid"] not in seen:
            seen.add(t["uuid"])
            unique.append(t)

    print(f"    [{unit_name}] {len(unique)} konu bulundu")
    return unique


def extract_video_url(driver, topic_uuid):
    url = f"{MEBI_BASE}/student/section/subject-details/{topic_uuid}"
    driver.get(url)
    time.sleep(5)

    # Method 1: <source> element
    sources = driver.find_elements(
        By.CSS_SELECTOR, "video source[type='video/mp4']"
    )
    for source in sources:
        src = source.get_attribute("src") or ""
        if "ogm-large-cdn.eba.gov.tr/mebi/video/" in src:
            return src

    # Method 2: Regex on page source
    match = CDN_PATTERN.search(driver.page_source)
    if match:
        return match.group(0)

    # Method 3: JS extraction
    cdn_url = driver.execute_script("""
        var sources = document.querySelectorAll('video source');
        for (var i = 0; i < sources.length; i++) {
            var src = sources[i].src || sources[i].getAttribute('src') || '';
            if (src.indexOf('ogm-large-cdn') !== -1 &&
                src.indexOf('.mp4') !== -1) {
                return src;
            }
        }
        var html = document.documentElement.innerHTML;
        var m = html.match(
            /https:\\/\\/ogm-large-cdn\\.eba\\.gov\\.tr\\/mebi\\/video\\/[a-z0-9]+\\.mp4/
        );
        return m ? m[0] : null;
    """)
    return cdn_url


def discover_all_videos(driver):
    all_entries = []
    discovered_uuids = set()

    # Resume from previous discovery
    if os.path.exists(DISCOVERY_FILE):
        with open(DISCOVERY_FILE) as f:
            all_entries = json.load(f)
        discovered_uuids = {e["uuid"] for e in all_entries}
        print(f"  Önceki keşiften {len(all_entries)} konu yüklendi")

    for course_name, course_uuid in COURSES.items():
        print(f"\n{'=' * 60}")
        print(f"  DERS: {course_name}")
        print(f"{'=' * 60}")

        units = discover_units(driver, course_name, course_uuid)

        for unit in units:
            topics = discover_topics(driver, unit["name"], unit["uuid"])

            for topic in topics:
                if topic["uuid"] in discovered_uuids:
                    print(f"      Atla (zaten keşfedildi): {topic['name']}")
                    continue

                print(f"      Video çıkarılıyor: {topic['name']}...")
                cdn_url = extract_video_url(driver, topic["uuid"])

                entry = {
                    "course": course_name,
                    "unit": unit["name"],
                    "topic": topic["name"],
                    "uuid": topic["uuid"],
                    "cdnUrl": cdn_url,
                }
                all_entries.append(entry)
                discovered_uuids.add(topic["uuid"])

                if cdn_url:
                    print(f"        Video: {cdn_url}")
                else:
                    print(f"        Video yok (test/quiz)")

                # Save progress
                with open(DISCOVERY_FILE, "w") as f:
                    json.dump(all_entries, f, indent=2, ensure_ascii=False)

    videos = [e for e in all_entries if e.get("cdnUrl")]
    print(
        f"\n  Keşif tamamlandı: {len(videos)} video / "
        f"{len(all_entries)} toplam konu"
    )
    return videos


def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    return name.strip(". ")[:200]


def download_videos(videos, tracker):
    print(f"\n[Local] {len(videos)} video kaydediliyor...")

    added = 0
    skipped = 0
    failed = 0

    for i, video in enumerate(videos):
        uuid = video["uuid"]
        course = video["course"]
        unit = video["unit"]
        topic = video["topic"]
        cdn_url = video["cdnUrl"]

        if uuid in tracker:
            print(f"  Atla ({i + 1}/{len(videos)}): {topic}")
            skipped += 1
            continue

        print(f"\n  [{i + 1}/{len(videos)}] {course} > {unit} > {topic}")

        try:
            resp = req.get(cdn_url, timeout=300)
            if resp.status_code != 200:
                print(f"    İndirme başarısız: HTTP {resp.status_code}")
                failed += 1
                continue

            content = resp.content
            size = len(content)
            print(f"    İndirildi: {size / 1024 / 1024:.1f} MB")

            if size < 10000:
                print(f"    Çok küçük ({size} bytes), atlanıyor")
                failed += 1
                continue

            dest_dir = os.path.join(
                CONTENT_DIR, sanitize_filename(course), sanitize_filename(unit)
            )
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, f"{sanitize_filename(topic)}.mp4")
            with open(dest_path, "wb") as fh:
                fh.write(content)

            tracker[uuid] = {
                "course": course,
                "unit": unit,
                "topic": topic,
                "cdnUrl": cdn_url,
                "path": dest_path,
                "size": size,
            }
            save_tracker(tracker)
            added += 1
            print(f"    Kaydedildi: {dest_path}")

        except req.exceptions.Timeout:
            print("    Zaman aşımı")
            failed += 1
        except req.exceptions.ConnectionError:
            print("    Bağlantı hatası")
            failed += 1
        except Exception as e:
            print(f"    Hata: {e}")
            failed += 1

    print(
        f"\n  Sonuç: +{added} kaydedildi, ={skipped} atlandı, x{failed} başarısız"
    )
    return added, skipped, failed


def main():
    os.makedirs("output", exist_ok=True)
    tracker = load_tracker()
    print(f"[Tracker] {len(tracker)} video zaten kaydedilmiş")

    # Phase 1: Discovery
    print("\n[1/2] Tüm MEBI videoları keşfediliyor...")
    driver = create_driver()
    try:
        eba_login(driver)
        ok = mebi_login(driver)
        if not ok:
            print("HATA: MEBI girişi başarısız!")
            return
        videos = discover_all_videos(driver)
    finally:
        driver.quit()

    if not videos:
        print("Hiç video bulunamadı!")
        return

    print(f"\n[2/2] {len(videos)} video indiriliyor...")
    added, skipped, failed = download_videos(videos, tracker)

    print(f"\n{'=' * 60}")
    print("  MEBI VIDEO TAMAMLANDI")
    print(f"  Toplam keşfedilen: {len(videos)}")
    print(f"  Kaydedilen: {added}")
    print(f"  Atlanan: {skipped}")
    print(f"  Başarısız: {failed}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
