#!/usr/bin/env python3
"""Download EBA textbook PDFs and SEBİTV PDF summaries to content/ for RAG indexing."""
import json
import os
import re
import sys
import time

import requests as req

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

from src.env_loader import load_env
load_env()

CONTENT_DIR = os.path.join("content")
SEBITV_DIR = os.path.join(CONTENT_DIR, "sebitv")
EBA_DIR = os.path.join(CONTENT_DIR, "eba")

# SEBİTV constants (from scrape_sebitv.py)
SEBITV_BASE = "https://www.sebitvcloud.com"
SEBITV_API = "https://uygulama.sebitvcloud.com/VCloudFrontEndService"
SEBITV_KAPI = "https://kapi.sebitvcloud.com"


def sanitize(name):
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    return name.strip()[:120]


# ── SEBİTV ───────────────────────────────────────────────

def sebitv_login():
    """Login to SEBİTV via Selenium, return requests session."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By

    tc = os.environ.get("EBA_TC_NO", "")
    pw = os.environ.get("EBA_PASSWORD", "")
    if not tc or not pw:
        print("  EBA_TC_NO / EBA_PASSWORD not set")
        return None

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=opts)

    try:
        driver.get(f"{SEBITV_BASE}/tr/giris.jsp")
        time.sleep(3)
        driver.find_element(By.NAME, "l_un").send_keys(tc)
        driver.find_element(By.NAME, "l_pw").send_keys(pw)
        btns = driver.find_elements(
            By.CSS_SELECTOR, "button[type='submit']")
        if btns:
            btns[0].click()
        time.sleep(6)

        ok = "giris.jsp" not in driver.current_url
        if not ok:
            print("  SEBİTV login FAILED")
            return None
        print("  SEBİTV login OK")

        # Navigate to SPA for full cookies
        driver.get(
            f"{SEBITV_BASE}/edu/index.html"
            "#/main/dashboardNew?routeConst=dashboard")
        time.sleep(5)

        # Transfer cookies to requests session
        s = req.Session()
        for c in driver.get_cookies():
            s.cookies.set(
                c["name"], c["value"],
                domain=c.get("domain", ""),
                path=c.get("path", "/"))
        s.headers.update({
            "User-Agent": driver.execute_script(
                "return navigator.userAgent"),
            "Accept": "application/json, text/plain, */*",
            "Referer": f"{SEBITV_BASE}/",
            "Origin": SEBITV_BASE,
        })
        return s
    finally:
        driver.quit()


from src.scrape_sebitv import (
    get_repo_type as sebitv_get_repo_type,
    get_pdf_url as sebitv_get_pdf_url,
    download_content as sebitv_download_content,
)


def download_sebitv_pdfs():
    """Download SEBİTV PDF summaries to content/sebitv/."""
    print("\n=== SEBİTV PDF İndirme ===")

    disco_path = "output/sebitv_discovered.json"
    if not os.path.exists(disco_path):
        print("  sebitv_discovered.json bulunamadı — "
              "önce scrape_sebitv.py çalıştırın")
        return 0

    with open(disco_path) as f:
        resources = json.load(f)

    pdfs = [r for r in resources
            if isinstance(r, dict) and r.get("fileType") == "pdf"]
    print(f"  {len(pdfs)} PDF kaynağı bulundu")

    if not pdfs:
        return 0

    s = sebitv_login()
    if not s:
        return 0

    os.makedirs(SEBITV_DIR, exist_ok=True)
    downloaded = 0

    for i, res in enumerate(pdfs):
        course = sanitize(res.get("course", "Genel"))
        unit = sanitize(res.get("unit", ""))
        title = sanitize(res.get("title", res["code"]))
        rid = res["resourceId"]

        course_dir = os.path.join(SEBITV_DIR, course)
        os.makedirs(course_dir, exist_ok=True)

        filename = f"{title}.pdf"
        filepath = os.path.join(course_dir, filename)

        if os.path.exists(filepath):
            continue

        print(f"  [{i+1}/{len(pdfs)}] {course} > {title}",
              end="", flush=True)

        try:
            locid = res.get("lessonPlanId", "")
            repo_type = sebitv_get_repo_type(s, rid, locid)
            if not repo_type:
                print(" — repo tipi bulunamadı")
                continue

            url = sebitv_get_pdf_url(s, res, repo_type)
            if not url:
                print(" — PDF URL bulunamadı")
                continue

            content, size = sebitv_download_content(s, url)
            if not content or size < 1000:
                print(" — indirilemedi")
                continue

            with open(filepath, "wb") as f:
                f.write(content)
            print(f" — {size / 1024 / 1024:.1f} MB ✓")
            downloaded += 1

        except Exception as e:
            print(f" — hata: {e}")

        time.sleep(0.3)

    print(f"\n  Toplam: {downloaded} PDF indirildi")
    return downloaded


# ── EBA ──────────────────────────────────────────────────

def download_eba_pdfs():
    """Download EBA textbook PDFs to content/eba/."""
    print("\n=== EBA Ders Kitapları İndirme ===")

    # EBA requires Selenium for login + SPA navigation
    # Use the existing scraper but save to disk instead of Drive
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By

    tc = os.environ.get("EBA_TC_NO", "")
    pw = os.environ.get("EBA_PASSWORD", "")
    if not tc or not pw:
        print("  EBA_TC_NO / EBA_PASSWORD not set")
        return 0

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=opts)

    try:
        # Login
        driver.get(
            "https://giris.eba.gov.tr/EBA_GIRIS/student.jsp")
        time.sleep(3)
        driver.find_element(By.ID, "tckn").send_keys(tc)
        driver.find_element(By.ID, "password").send_keys(pw)
        for btn in driver.find_elements(
                By.CSS_SELECTOR, "button.nl-form-send-btn"):
            if btn.text.strip() == "Giriş":
                btn.click()
                break
        time.sleep(5)
        print(f"  EBA login: {driver.current_url}")

        # Navigate to SPA
        driver.get(
            "https://ders.eba.gov.tr/ders/proxy/"
            "VCollabPlayer_v0.0.1064/"
            "index.html#/main/courses/3/6/0")
        time.sleep(5)

        # Import textbook discovery from scraper
        from src.scrape_eba_textbooks import (
            get_all_textbooks, get_cdn_url,
            get_session_from_driver)

        books = get_all_textbooks(driver)
        if not books:
            # Fallback
            fb_path = "output/eba_textbooks_data.json"
            if os.path.exists(fb_path):
                with open(fb_path) as f:
                    books = json.load(f)
                print(f"  Fallback: {len(books)} kitap")

        if not books:
            print("  Kitap bulunamadı")
            return 0

        print(f"  {len(books)} kitap bulundu")
        session = get_session_from_driver(driver)
        os.makedirs(EBA_DIR, exist_ok=True)

        downloaded = 0
        for book in books:
            title = sanitize(
                book.get("title", book.get("name", "?")))
            course = sanitize(
                book.get("course", "Genel"))
            dl_url = book.get("downloadUrl", "")

            if not dl_url:
                continue

            course_dir = os.path.join(EBA_DIR, course)
            os.makedirs(course_dir, exist_ok=True)
            filepath = os.path.join(
                course_dir, f"{title}.pdf")

            if os.path.exists(filepath):
                print(f"  Mevcut: {title}")
                continue

            print(f"  İndiriliyor: {title}...", end="",
                  flush=True)
            cdn = get_cdn_url(driver, dl_url, session)
            if not cdn:
                print(" — CDN URL bulunamadı")
                continue

            try:
                r = req.get(cdn, timeout=120)
                if r.status_code != 200 or len(r.content) < 1000:
                    print(f" — başarısız")
                    continue
                with open(filepath, "wb") as f:
                    f.write(r.content)
                mb = len(r.content) / 1024 / 1024
                print(f" — {mb:.1f} MB ✓")
                downloaded += 1
            except Exception as e:
                print(f" — hata: {e}")

        return downloaded

    finally:
        driver.quit()


def main():
    os.makedirs(CONTENT_DIR, exist_ok=True)

    total = 0
    total += download_sebitv_pdfs()
    total += download_eba_pdfs()

    print(f"\n=== Toplam: {total} PDF indirildi → "
          f"{CONTENT_DIR}/ ===")


if __name__ == "__main__":
    main()
