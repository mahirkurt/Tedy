#!/usr/bin/env python3
"""Scrape SEBİTV Cloud videos/PDFs and save them under content/sebitv/."""
import json
import os
import re
import sys
import time

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
KAPI = "https://kapi.sebitvcloud.com"

TRACKER_FILE = os.path.join("output", "sebitv_uploaded.json")
DISCOVERY_FILE = os.path.join("output", "sebitv_discovered.json")
CONTENT_DIR = os.path.join("content", "sebitv")

# Video URL pattern:
# {BASE}/BASE_URL/LEARNING_OBJECT/REPOSITORY/0/{resourceId}/{version}/{code}/
#   sco1/resources/video/{code}.mp4
# Redirects to signed CDN URL at cdn1.sebitvcloud.com

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


def api_get(s, url):
    """GET JSON from API."""
    r = s.get(url, timeout=30)
    if r.status_code == 200:
        return r.json()
    return None


def discover_content_tree(s):
    """Build full content tree: courses > units > topics > resources."""
    print("\n[KEŞIF] İçerik ağacı oluşturuluyor...")

    # Get courses
    data = api_get(
        s,
        f"{API}/node/getclassroomcourseinfo"
        f"?classroom=6&withcourse=true"
        f"&withlocked=true&pointtypeid=",
    )
    if not data:
        print("  HATA: Ders listesi alınamadı!")
        return []

    courses = (
        data.get("classroomList", [{}])[0]
        .get("courses", [])
    )
    print(f"  {len(courses)} ders bulundu")

    all_resources = []

    for course in courses:
        cid = course["id"]
        cname = course["name"]
        print(f"\n  === {cname} ===")

        # Get units
        units_data = api_get(
            s,
            f"{API}/node/getnodesbyparent"
            f"?parentid={cid}&expand=true"
            f"&withperformance=false&withlocked=false"
            f"&withcompletionprogress=true"
            f"&screen=vcCurriculumUnitListNarrowed",
        )
        if not units_data:
            continue

        units = (
            units_data.get("node", {})
            .get("childList", [])
        )

        for unit in units:
            uid = unit["id"]
            uname = unit["name"]

            # Get topics (if unit is not leaf)
            topics = []
            if not unit.get("leafNode", False):
                topics_data = api_get(
                    s,
                    f"{API}/node/getnodesbyparent"
                    f"?parentid={uid}&expand=true"
                    f"&withperformance=false"
                    f"&withlocked=false"
                    f"&withcompletionprogress=true"
                    f"&screen=vcCurriculumUnitListNarrowed",
                )
                if topics_data:
                    topics = (
                        topics_data.get("node", {})
                        .get("childList", [])
                    )
            else:
                # Unit itself is a topic (e.g. İngilizce)
                topics = [unit]

            for topic in topics:
                tid = topic["id"]
                tname = topic["name"]

                # Get lesson plan resources
                lp_data = api_get(
                    s,
                    f"{KAPI}/curriculumservice/lessonplan/"
                    f"getlessonplanlist?nodeid={tid}",
                )
                if not lp_data:
                    continue

                plans = lp_data.get("lessonPlanList") or []
                for plan in plans:
                    ssname = plan.get(
                        "subSubjectName", tname
                    )
                    containers = plan.get(
                        "courseLessonPlanContainer", []
                    )
                    for container in containers:
                        resources = container.get(
                            "resources", []
                        )
                        for res in resources:
                            rd = res.get("resource", {})
                            if not rd.get("code"):
                                continue

                            rid = rd["id"]
                            code = rd["code"]
                            version = rd.get("version", 0)
                            ft = rd.get("fileType", "")
                            dur = rd.get("duration", 0)
                            size = rd.get("fileSize", 0)
                            title = rd.get("title", "?")
                            lct = (
                                rd.get(
                                    "learningCycleType", {}
                                ).get("name", "")
                            )

                            entry = {
                                "course": cname,
                                "unit": uname,
                                "topic": tname,
                                "subSubject": ssname,
                                "resourceId": rid,
                                "code": code,
                                "version": version,
                                "title": title,
                                "fileType": ft,
                                "duration": dur,
                                "fileSize": size,
                                "type": lct or "?",
                                "lessonPlanId": plan.get(
                                    "id", ""
                                ),
                            }
                            all_resources.append(entry)

                resource_count = sum(
                    1 for r in all_resources
                    if r["topic"] == tname
                    and r["course"] == cname
                )
                if resource_count:
                    print(
                        f"    {tname}: "
                        f"{resource_count} kaynak"
                    )

    # Count downloadable items
    videos = [
        r for r in all_resources
        if r["duration"] and r["duration"] > 0
    ]
    pdfs = [
        r for r in all_resources
        if r["fileType"] == "pdf"
    ]
    print(
        f"\n  Toplam: {len(all_resources)} kaynak, "
        f"{len(videos)} video, {len(pdfs)} PDF"
    )
    return all_resources


def get_repo_type(s, resource_id, locid=""):
    """Get REPOSITORY type via tracking/launch API."""
    # Try with locid first, then without
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


def get_pdf_url(s, res, repo_type):
    """Get PDF URL by checking dataLevel.html for pdfName."""
    base = _content_base(res, repo_type)
    code = res["code"]

    # Try dataLevel.html for real filename
    dl = f"{base}/dataLevel.html?userType=student"
    try:
        r = s.get(dl, timeout=10)
        if r.status_code == 200:
            m = re.search(
                r"pdfName[\"']?\s*[:=]\s*[\"']"
                r"([^\"']+)",
                r.text,
            )
            if m:
                return f"{base}/resources/{m.group(1)}"
    except Exception:
        pass

    # Fallback: standard path
    return f"{base}/resources/pdf/{code}.pdf"


def build_content_url(res, repo_type, kind="video"):
    """Build URL for video content."""
    base = _content_base(res, repo_type)
    return (
        f"{base}/sco1/resources/video/"
        f"{res['code']}.mp4"
    )


def test_url(s, url):
    """Test if URL is downloadable (HEAD request)."""
    try:
        r = s.head(url, timeout=15, allow_redirects=True)
        if r.status_code == 200:
            ct = r.headers.get("Content-Type", "")
            if "video" in ct or "pdf" in ct:
                return True
            # Check for non-HTML responses (binary)
            if "text/html" not in ct and ct:
                return True
        return False
    except Exception:
        return False


def download_content(s, url, timeout=300):
    """Download content from URL, following redirects."""
    r = s.get(url, timeout=timeout, allow_redirects=True)
    if r.status_code != 200:
        return None, 0
    # Check we didn't get an error page
    ct = r.headers.get("Content-Type", "")
    if "text/html" in ct and len(r.content) < 50000:
        return None, 0
    return r.content, len(r.content)


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


def download_resources(resources, s, tracker):
    """Download all videos/PDFs into content/sebitv/<course>/<unit>/."""
    print(f"\n[İNDİRME] {len(resources)} kaynak işleniyor...")

    added = 0
    skipped = 0
    failed = 0
    no_video = 0

    for i, res in enumerate(resources):
        key = res["resourceId"]

        if key in tracker:
            skipped += 1
            continue

        is_pdf = res["fileType"] == "pdf"
        has_dur = res["duration"] and res["duration"] > 0

        # Skip resources without video and not PDF
        if not has_dur and not is_pdf:
            no_video += 1
            continue

        course = res["course"]
        unit = res["unit"]
        title = res["title"]

        print(
            f"\n  [{added + skipped + failed + 1}] "
            f"{course} > {unit} > {title}"
        )

        try:
            # Get correct REPOSITORY type
            locid = res.get("lessonPlanId", "")
            repo_type = get_repo_type(s, key, locid)
            if repo_type is None:
                print("    Repo tipi bulunamadı")
                failed += 1
                continue

            kind = "pdf" if is_pdf else "video"
            if is_pdf:
                url = get_pdf_url(s, res, repo_type)
            else:
                url = build_content_url(
                    res, repo_type,
                )
            content, size = download_content(s, url)
            if not content:
                print(
                    f"    {kind.upper()} bulunamadı "
                    f"(REPO/{repo_type})"
                )
                tracker[key] = {
                    "status": f"no_{kind}",
                    "title": title,
                }
                save_tracker(tracker)
                failed += 1
                continue

            ext = ".pdf" if is_pdf else ".mp4"

            size = len(content)
            print(f"    İndirildi: {size / 1024 / 1024:.1f} MB")

            if size < 5000:
                print(f"    Çok küçük ({size} bytes), atla")
                failed += 1
                continue

            dest_dir = os.path.join(
                CONTENT_DIR, sanitize(course), sanitize(unit)
            )
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, f"{sanitize(title)}{ext}")
            with open(dest_path, "wb") as fh:
                fh.write(content)

            tracker[key] = {
                "course": course,
                "unit": unit,
                "title": title,
                "type": res["type"],
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
        f"\n  Sonuç: +{added} kaydedildi, "
        f"={skipped} atlandı, "
        f"x{failed} başarısız, "
        f"~{no_video} video yok (interaktif)"
    )
    return added, skipped, failed


def main():
    os.makedirs("output", exist_ok=True)
    tracker = load_tracker()
    print(f"[Tracker] {len(tracker)} kaynak zaten işlenmiş")

    # Phase 1: Discovery
    resources = []
    if os.path.exists(DISCOVERY_FILE):
        with open(DISCOVERY_FILE) as f:
            resources = json.load(f)
        print(
            f"[Keşif] Önceki keşiften "
            f"{len(resources)} kaynak yüklendi"
        )
    else:
        print("\n[1/2] SEBİTV içerikleri keşfediliyor...")
        driver = create_driver()
        try:
            ok = sebitv_login(driver)
            if not ok:
                print("HATA: SEBİTV girişi başarısız!")
                return
            s = get_session(driver)
            resources = discover_content_tree(s)
        finally:
            driver.quit()

        if resources:
            with open(DISCOVERY_FILE, "w") as f:
                json.dump(
                    resources, f,
                    indent=2, ensure_ascii=False,
                )
            print(
                f"\n  Kaydedildi: {DISCOVERY_FILE} "
                f"({len(resources)} kaynak)"
            )

    if not resources:
        print("Hiç kaynak bulunamadı!")
        return

    # Filter to downloadable items
    downloadable = [
        r for r in resources
        if (r.get("duration") and r["duration"] > 0)
        or r.get("fileType") == "pdf"
    ]
    print(
        f"\n  {len(downloadable)} indirilebilir kaynak "
        f"(video + PDF) / {len(resources)} toplam"
    )

    print("\n[2/2] İndirme başlıyor...")
    driver = create_driver()
    try:
        ok = sebitv_login(driver)
        if not ok:
            print("HATA: SEBİTV girişi başarısız!")
            return
        s = get_session(driver)
    finally:
        driver.quit()

    added, skipped, failed = download_resources(
        downloadable, s, tracker,
    )

    print(f"\n{'=' * 60}")
    print("  SEBİTV TAMAMLANDI")
    print(f"  Toplam kaynak: {len(resources)}")
    print(f"  İndirilebilir: {len(downloadable)}")
    print(f"  Kaydedilen: {added}")
    print(f"  Atlanan: {skipped}")
    print(f"  Başarısız: {failed}")
    print("=" * 60)


if __name__ == "__main__":
    main()
