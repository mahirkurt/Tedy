"""Scrape all relevant data from TED portal for the last 4 weeks."""
import base64
import json
import os
import re
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin

import ddddocr
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select

from src.env_loader import load_env
from src.scrape_helpers import wait_for, wait_for_js
load_env()

LOGIN_URL = "https://portal.tedronesans.k12.tr/login"
BASE_URL = "https://portal.tedronesans.k12.tr"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
OGRENCI_ID = "13240"


def create_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-setuid-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=opts)


def login(driver):
    from src.session_manager import (
        load_cookies, save_cookies,
        check_session_valid, apply_cookies_to_driver,
    )

    # Try cached session first
    cached = load_cookies()
    if cached and check_session_valid(cached):
        print("[LOGIN] Using cached session")
        apply_cookies_to_driver(driver, cached)
        driver.get(f"{BASE_URL}/pages/ogrenci_istekler/p_temel_bilgiler")
        time.sleep(2)
        if "/login" not in driver.current_url:
            print(f"[LOGIN] Cached session OK -> {driver.current_url}")
            return {"method": "cached_session", "captcha_attempts": 0}
        print("[LOGIN] Cached session expired in browser, falling back to CAPTCHA")

    # CAPTCHA login
    ocr = ddddocr.DdddOcr(show_ad=False)
    for attempt in range(5):
        driver.get(LOGIN_URL)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "tx_kullanici_adi"))
        )
        driver.find_element(By.ID, "tx_kullanici_adi").send_keys(
            os.environ.get("PORTAL_USERNAME", ""))
        driver.find_element(By.ID, "tx_kullanici_sifre").send_keys(
            os.environ.get("PORTAL_PASSWORD", ""))

        # CAPTCHA with validation
        captcha_img = driver.find_element(
            By.CSS_SELECTOR, 'img[src*="CaptchaHandler"]')
        captcha_text = ocr.classification(
            captcha_img.screenshot_as_png).strip()
        if not captcha_text or not captcha_text.isdigit() or len(captcha_text) < 4:
            print(f"[LOGIN] OCR '{captcha_text}' invalid, refreshing...")
            continue

        driver.find_element(By.ID, "txtKod").send_keys(captcha_text)
        driver.find_element(By.ID, "btn_ogrenci").click()
        time.sleep(3)
        if "/login" not in driver.current_url:
            print(f"[LOGIN] OK -> {driver.current_url}")
            save_cookies(driver.get_cookies())
            return {"method": "captcha_login", "captcha_attempts": attempt + 1}

    print("[LOGIN] FAILED after 5 attempts")
    return None


class PortalUnavailable(Exception):
    """The portal declined to serve a page, and said why.

    Raised when the absence of data is explained by the portal itself -
    no permission, or a module its administrators have closed. That is
    not a scrape failure and must not be reported as one.
    """

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


UNAUTHORIZED_PATH = "/hata/yetkisiz_giris"
MODULE_CLOSED_MARKER = "erişime kapalı"


def detect_portal_block(current_url, body_text):
    """Return (reason, detail) when the portal is refusing this page."""
    if UNAUTHORIZED_PATH in (current_url or ""):
        # The reason code below stays machine-readable; the detail is shown to
        # a family in the dashboard banner, so it does not echo the portal's
        # internal error path.
        return ("yetkisiz", "portal bu sayfaya yetki vermiyor")
    if MODULE_CLOSED_MARKER in (body_text or ""):
        for line in body_text.splitlines():
            if MODULE_CLOSED_MARKER in line:
                return ("modul_kapali", line.strip())
        return ("modul_kapali", "modül erişime kapalı")
    return None


def _anchor_present(driver, anchor):
    """True if any of the given CSS selectors matches an element on the page."""
    selectors = [anchor] if isinstance(anchor, str) else list(anchor)
    for sel in selectors:
        try:
            if driver.find_elements(By.CSS_SELECTOR, sel):
                return True
        except Exception:
            continue
    return False


def _require_portal_access(driver, label, anchor=None):
    """Fail fast with a named reason instead of timing out on a missing element.

    A "module closed" banner can be a sitewide maintenance notice rather
    than a per-page block - it has been observed naming a module other
    than the page it appeared on (health.json once marked ders_programi
    unavailable on the strength of a banner reading "Akademi Modülü kısa
    bir süre erişime kapalıdır", which names a different module). The
    banner text alone is therefore not proof this page is blocked: pass
    `anchor` (a CSS selector, or a list of them) naming an element this
    page always renders when it is genuinely serving content. If the
    anchor IS present, the banner is incidental and access is not
    suppressed. The unauthorized-redirect reason is unambiguous on its
    own and needs no anchor.
    """
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
    except Exception:
        body_text = ""
    block = detect_portal_block(driver.current_url, body_text)
    if not block:
        return
    reason, detail = block
    if reason == "modul_kapali" and anchor and _anchor_present(driver, anchor):
        return
    raise PortalUnavailable(reason, f"{label}: {detail}")


def parse_gelisim_rubrics(html):
    """Extract per-course rubric assessments from the gelişim raporu page.

    Each course card holds a two-column table: the assessment text and the
    level reached. Rows whose second cell is empty are group headings
    ("OYUN VE HÜCUM OYUNLARI"), which scope the rows that follow.
    """
    soup = BeautifulSoup(html, "html.parser")
    rubrics = []
    for card in soup.select("div.card.mobil_gelisim_raporu_dersler"):
        header = card.select_one(".card-header, .card-title, h4, h5")
        ders = header.get_text(" ", strip=True) if header else ""
        for table in card.find_all("table"):
            alan = ""
            for tr in table.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                if len(cells) != 2:
                    continue
                if all(c.name == "th" for c in cells):
                    continue  # column labels, not an assessment
                left = cells[0].get_text(" ", strip=True)
                right = cells[1].get_text(" ", strip=True)
                if not left:
                    continue
                if not right:
                    alan = left
                    continue
                rubrics.append({"ders": ders, "alan": alan,
                                "kazanim": left, "duzey": right})
    return rubrics


def _is_empty_state_row(cells, headers):
    """True for the single spanning cell DataTables renders for an empty table.

    Such a row carries no record - keeping it would hand every consumer an
    object whose real fields are all missing.
    """
    if len(cells) != 1:
        return False
    colspan = cells[0].get_attribute("colspan")
    if colspan and colspan.strip().isdigit() and int(colspan) > 1:
        return True
    return len(headers) > 1


def extract_table(driver, table_el):
    """Extract a table into a list of dicts (header->value)."""
    headers = [th.text.strip() for th in table_el.find_elements(By.TAG_NAME, "th")]
    rows = []
    empty_state = False
    for tr in table_el.find_elements(By.TAG_NAME, "tr"):
        cells = tr.find_elements(By.TAG_NAME, "td")
        if not cells:
            continue
        if _is_empty_state_row(cells, headers):
            empty_state = True
            continue
        if headers:
            row = {}
            for i, cell in enumerate(cells):
                key = headers[i] if i < len(headers) else f"col_{i}"
                row[key] = cell.text.strip()
            rows.append(row)
        else:
            rows.append([c.text.strip() for c in cells])
    return {"headers": headers, "rows": rows,
            "empty_state": empty_state and not rows}


# =============================================================================
# 0. ÖĞRENCİ PROFİLİ
# =============================================================================
def _download_profile_image_data_url(driver, img_src):
    """Download profile image with current portal cookies and return data URL."""
    if not img_src:
        return ""
    if img_src.startswith("data:image/"):
        return img_src

    image_url = urljoin(BASE_URL, img_src)
    sess = requests.Session()
    for c in driver.get_cookies():
        try:
            sess.cookies.set(c["name"], c["value"], domain=c.get("domain", ""))
        except Exception:
            pass

    try:
        r = sess.get(image_url, timeout=15)
        r.raise_for_status()
    except requests.RequestException:
        return ""

    content_type = r.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if not content_type.startswith("image/"):
        return ""
    b64 = base64.b64encode(r.content).decode("ascii")
    return f"data:{content_type};base64,{b64}"


def scrape_ogrenci_profili(driver):
    """Scrape student profile info (including photo) from TED Connect."""
    print("\n[0/9] Öğrenci Profili")
    url = f"{BASE_URL}/pages/ogrenci_istekler/p_temel_bilgiler"
    driver.get(url)
    time.sleep(3)

    fields = {}

    # 1) Label + input/select/textarea based fields
    for label_el in driver.find_elements(By.TAG_NAME, "label"):
        label = (label_el.text or "").strip().rstrip(":")
        if len(label) < 2:
            continue
        value = ""
        for_id = label_el.get_attribute("for")
        if for_id:
            try:
                target = driver.find_element(By.ID, for_id)
                value = (
                    target.get_attribute("value")
                    or target.text
                    or ""
                ).strip()
            except Exception:
                value = ""
        if not value:
            try:
                parent = label_el.find_element(By.XPATH, "./..")
                value_el = parent.find_element(
                    By.XPATH, ".//input|.//textarea|.//select|.//span|.//div"
                )
                value = (
                    value_el.get_attribute("value")
                    or value_el.text
                    or ""
                ).strip()
            except Exception:
                value = ""
        if value and value.lower() != label.lower():
            fields.setdefault(label, value)

    # 2) Table-like fields
    for tr in driver.find_elements(By.CSS_SELECTOR, "tr"):
        ths = tr.find_elements(By.CSS_SELECTOR, "th, td")
        if len(ths) < 2:
            continue
        key = (ths[0].text or "").strip().rstrip(":")
        val = (ths[1].text or "").strip()
        if len(key) >= 2 and val:
            fields.setdefault(key, val)

    # 2b) The card-profile layout: <h6> label followed by its <h5> value.
    # p_temel_bilgiler carries no <label> elements at all and only one table,
    # so strategies 1 and 2 come back with nothing but chrome. Scoped to the
    # card rather than the page: an unscoped sweep is what collected the
    # navigation item "ÖGEP: Teams" as if it were profile data.
    for card in driver.find_elements(By.CSS_SELECTOR, ".card-profile"):
        for h6 in card.find_elements(By.TAG_NAME, "h6"):
            key = (h6.text or "").strip().rstrip(":")
            if len(key) < 2:
                continue
            try:
                val = (h6.find_element(
                    By.XPATH, "./following-sibling::h5[1]").text or "").strip()
            except Exception:
                continue
            # The portal repeats the label as a placeholder when a field is
            # unset (E-Posta / E-Posta); that is absence, not a value.
            if val and val.lower() != key.lower():
                fields.setdefault(key, val)

    # 3) Profile image candidates
    photo_data_url = ""
    for img in driver.find_elements(By.TAG_NAME, "img"):
        try:
            if not img.is_displayed():
                continue
        except Exception:
            continue
        src = (img.get_attribute("src") or "").strip()
        alt = (img.get_attribute("alt") or "").lower()
        klass = (img.get_attribute("class") or "").lower()
        if not src:
            continue
        lowered_src = src.lower()
        if any(x in lowered_src for x in ("captcha", "logo", "favicon", "icon")):
            continue
        likely = any(x in (alt + " " + klass + " " + lowered_src) for x in (
            "profil", "profile", "ogrenci", "öğrenci", "avatar"
        ))
        size = img.size or {}
        if not likely and (size.get("width", 0) < 80 or size.get("height", 0) < 80):
            continue
        photo_data_url = _download_profile_image_data_url(driver, src)
        if photo_data_url:
            break

    # 4) Canonical summary fields (best-effort)
    lowered = {k.lower(): v for k, v in fields.items()}

    # The name is the profile card's own heading, not a label/value pair, so
    # no amount of field matching finds it.
    card_name = ""
    for card in driver.find_elements(By.CSS_SELECTOR, ".card-profile"):
        try:
            candidate = (card.find_element(By.TAG_NAME, "h3").text or "").strip()
        except Exception:
            continue
        # A heading, not a paragraph: guards against a layout change turning
        # this into a block of text we would file as someone's name.
        if candidate and len(candidate) <= 60 and "\n" not in candidate:
            card_name = candidate
            break

    full_name = card_name
    student_no = ""
    class_name = ""
    branch = ""
    for k, v in lowered.items():
        if not full_name and ("ad soyad" in k or k == "adı soyadı" or "ogrenci adı" in k):
            full_name = v
        if not student_no and ("öğrenci no" in k or "ogrenci no" in k
                               or "okul no" in k or "numara" in k):
            student_no = v
        if not class_name and ("sınıf" in k or "sinif" in k):
            class_name = v
        if not branch and ("şube" in k or "sube" in k):
            branch = v

    # The profile page never lists the class, so class_name came back empty
    # while the portal printed "Işık Kurt 7-D" in the header of every page —
    # measured 2026-09-20. That header is where a family reads it, so read it
    # from there rather than leaving the dashboard with a blank field.
    if not class_name:
        try:
            govde = driver.find_element(By.TAG_NAME, "body").text
        except Exception:
            govde = ""
        kalip = (
            rf"{re.escape(full_name)}\s+(\d{{1,2}})\s*-\s*([A-ZÇĞİÖŞÜ])\b"
            if full_name
            else r"\b(\d{1,2})\s*-\s*([A-ZÇĞİÖŞÜ])\b"
        )
        eslesme = re.search(kalip, govde)
        if eslesme:
            class_name = f"{eslesme.group(1)}-{eslesme.group(2)}"
            branch = branch or eslesme.group(2)

    result = {
        "name": full_name,
        "student_no": student_no,
        "class_name": class_name,
        "branch": branch,
        "fields": fields,
        "photo_data_url": photo_data_url,
        "profile_url": url,
        "scraped_at": datetime.now().isoformat(),
    }

    driver.save_screenshot(os.path.join(OUTPUT_DIR, "ogrenci_profili.png"))
    print(
        f"  Fields: {len(fields)} | "
        f"Photo: {'OK' if bool(photo_data_url) else 'YOK'}"
    )
    return result


# =============================================================================
# 1. HAFTALIK DERS PROGRAMI
# =============================================================================
HAFTA_KAPSAMI_ENV = "TEDY_HAFTA_KAPSAMI"
ILERI_HAFTA = 2


def hafta_kapsami():
    """'tum' for a one-off backfill, 'guncel' for the every-15-minutes run."""
    return (os.environ.get(HAFTA_KAPSAMI_ENV) or "guncel").strip().lower()


def seviye_kodu(sinif):
    """The calendar's level-filter value for a class like "7-D" → "70".

    The filter was hardcoded to "60" (6. Sınıf) from the day it was written.
    Işık is in 7-D, so the page — if it ever opens — would have answered for
    the wrong year group. Unverified against the live page on purpose: the
    portal refuses `/pages/akademik_takvim/p_ogrenci` for this account (0
    successes and 1057 refusals in output/sync.log), so `<grade>0` is a
    pattern read off the one value we have ever seen, not a measurement.
    scrape_takvim falls back to matching the option's text.
    """
    m = re.match(r"\s*(\d{1,2})", str(sinif or ""))
    if not m:
        return None
    return f"{int(m.group(1))}0"


def hafta_indeksleri(option_count, current_idx, kapsam=None):
    """Which week options to visit.

    The portal publishes the whole school year up front — 36 weeks were on
    offer on 2026-09-20. Visiting all of them on every cron run multiplies a
    job that already takes two minutes; visiting only the open week, which is
    what this did, means a week the school has already published stays
    invisible until it arrives. So: one backfill pass over everything, then
    the current week and the two ahead of it.
    """
    kapsam = kapsam or hafta_kapsami()
    if option_count <= 0:
        return []
    if kapsam == "tum":
        return list(range(option_count))
    current_idx = max(0, min(current_idx, option_count - 1))
    son = min(option_count - 1, current_idx + ILERI_HAFTA)
    return list(range(current_idx, son + 1))


def scrape_ders_programi(driver, kapsam=None):
    """Scrape the weekly class schedule — the open week, and only that.

    The portal offers 36 weeks in this selector, but measured on 2026-09-20
    every one renders the identical grid: all four tables on the page were
    byte-identical for weeks 1, 21 and 31 while the selector genuinely moved.
    A school timetable repeats, so there is nothing to walk. What does vary
    week to week is the course content, and that lives on the dashboard —
    see scrape_ders_icerikleri.

    `kapsam` is accepted and ignored so run_sync can pass it uniformly.
    """
    del kapsam
    print("\n[1/8] Haftalık Ders Programı")
    url = f"{BASE_URL}/pages/ogrenci_istekler/p_haftalik_ders_hazirlik_programim"
    driver.get(url)
    time.sleep(3)
    _require_portal_access(driver, "Haftalık Ders Programı", anchor="select")

    all_weeks = []

    def _hafta_select():
        # By id: this page carries three selects and the first in DOM order is
        # not guaranteed to be the week one.
        try:
            return Select(driver.find_element(By.ID, "dp_secili_hafta"))
        except Exception:
            return Select(driver.find_element(By.CSS_SELECTOR, "select"))

    # Find week selector dropdown
    try:
        select = _hafta_select()
        options = select.options
        print(f"  Week options found: {len(options)}")

        # Find current week index
        current_idx = None
        for i, opt in enumerate(options):
            if opt.is_selected():
                current_idx = i
                break
        if current_idx is None:
            # The first week, not the last: in September the portal's own
            # selection is week 1, and falling back to the end of the list
            # would file June's empty grid as "this week".
            current_idx = 0

        # The open week and nothing else: every other option renders the same
        # grid (see the docstring).
        target_weeks = [current_idx]
        print(f"  Current week index: {current_idx} of {len(options)}")

        for week_idx in target_weeks:
            select = _hafta_select()
            opt_text = select.options[week_idx].text.strip()
            print(f"  Selecting week: {opt_text}")
            select.select_by_index(week_idx)
            time.sleep(2)

            # Extract the schedule grid
            week_data = {
                "week_label": opt_text,
                "week_index": week_idx,
                "is_current": week_idx == current_idx,
                "schedule": [],
                "screenshot": None,
            }

            # Try to find the schedule table/grid
            tables = driver.find_elements(By.TAG_NAME, "table")
            if tables:
                week_data["schedule"] = extract_table(driver, tables[0])

            # Also get color-coded cells from divs/spans
            cells = driver.find_elements(By.CSS_SELECTOR, "td[style], td.ders-cell, .schedule-cell, td[bgcolor]")
            if not cells:
                # Try getting all td with content in schedule area
                all_tds = driver.find_elements(By.CSS_SELECTOR, "table td")
                schedule_items = []
                for td in all_tds:
                    text = td.text.strip()
                    bg = td.get_attribute("style") or ""
                    if text and len(text) > 2:
                        schedule_items.append({"text": text, "style": bg[:100]})
                if schedule_items:
                    week_data["schedule_cells"] = schedule_items

            # One screenshot, of the week someone might actually open. A
            # backfill would otherwise leave 36 PNGs nobody looks at.
            if week_data["is_current"]:
                ss_name = f"schedule_week_{week_idx}.png"
                driver.save_screenshot(os.path.join(OUTPUT_DIR, ss_name))
                week_data["screenshot"] = ss_name

            all_weeks.append(week_data)

    except Exception as e:
        print(f"  Error with week selector: {e}")
        # Fallback: just extract current view
        tables = driver.find_elements(By.TAG_NAME, "table")
        if tables:
            all_weeks.append({
                "week_label": "current",
                "is_current": True,
                "schedule": extract_table(driver, tables[0]),
            })

    # No selector and no table is not an empty timetable, it is the wrong
    # page. Returning [] here let the 2026-09-23 18:45 run overwrite a good
    # reading with nothing while health.json reported the section as fine;
    # raising puts it in `okunamadi`, where run_sync keeps the last reading.
    if not all_weeks:
        raise RuntimeError("ders programı tablosu sayfada yok")

    print(f"  Scraped {len(all_weeks)} weeks")
    return all_weeks


# =============================================================================
# 2. ÖDEVLERİM
# =============================================================================
def _scrape_homework_detail(driver, odev_id, ders_id):
    """Fetch a single homework detail popup page."""
    popup_url = (
        f"{BASE_URL}/popups/odev_islemleri/Odev_Goruntule"
        f"?ID={odev_id}&ders_id={ders_id}&ogrenci_id={OGRENCI_ID}"
    )
    driver.get(popup_url)
    time.sleep(1.5)

    detail = {"description": "", "attachments": []}

    # Parse description: HTML content after "Ödev Detayı" label
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Find the col-md-12 div containing the description
    for div in soup.find_all("div", class_="col-md-12"):
        label = div.find("label")
        if label and "Detay" in (label.get_text() or ""):
            # Everything after <hr> is the description
            hr = div.find("hr")
            if hr:
                # Get all siblings after hr
                parts = []
                for sib in hr.next_siblings:
                    text = sib.get_text(strip=True) if hasattr(sib, 'get_text') else str(sib).strip()
                    if text:
                        parts.append(text)
                detail["description"] = "\n".join(parts)
            else:
                # Fallback: get all text in div minus label
                full = div.get_text(separator="\n", strip=True)
                lbl_text = label.get_text(strip=True)
                detail["description"] = full.replace(lbl_text, "", 1).strip()
            break

    # Look for file attachment links
    for a in driver.find_elements(By.TAG_NAME, "a"):
        href = a.get_attribute("href") or ""
        text = a.text.strip()
        if href and "javascript" not in href.lower() and text:
            detail["attachments"].append({
                "name": text,
                "url": href,
            })

    return detail


def scrape_odevlerim(driver):
    """Scrape homework list with detail pages."""
    print("\n[2/8] Ödevlerim")
    url = f"{BASE_URL}/pages/ogrenci_istekler/p_odevlerim"
    driver.get(url)
    try:
        wait_for(driver, (By.CSS_SELECTOR,
                          "select[name='t_odevlerim_length']"),
                 timeout=15)
    except Exception:
        wait_for(driver, (By.TAG_NAME, "table"), timeout=15)

    result = {"summary": "", "homework": []}

    # Get summary text
    try:
        cards = driver.find_elements(
            By.CSS_SELECTOR, ".card-header, .card-title, h4, h5"
        )
        for card in cards:
            text = card.text.strip()
            if "Toplam" in text or "Ödev" in text:
                result["summary"] = text
                break
    except Exception:
        pass

    # Select "Tamamı" (show all) from DataTables length dropdown
    try:
        length_select = driver.find_element(
            By.CSS_SELECTOR, "select[name='t_odevlerim_length']"
        )
        Select(length_select).select_by_visible_text("Tamamı")
        # Wait for table to reload with all rows
        try:
            wait_for(driver, (By.CSS_SELECTOR,
                              "#tblOdevlerim tbody tr"),
                     timeout=10)
        except Exception:
            time.sleep(1)
        print("  DataTables: selected 'Tamamı' (show all)")
    except Exception as e:
        print(f"  Could not select 'Tamamı': {e}")

    # Extract homework table + detail span IDs
    hw_rows = []
    hw_empty_state = False
    tables = driver.find_elements(By.TAG_NAME, "table")
    for tbl in tables:
        headers = [
            th.text.strip()
            for th in tbl.find_elements(By.TAG_NAME, "th")
        ]
        if not any("Ders" in h or "Ödev" in h for h in headers):
            continue

        for tr in tbl.find_elements(By.TAG_NAME, "tr"):
            cells = tr.find_elements(By.TAG_NAME, "td")
            if not cells:
                continue
            if _is_empty_state_row(cells, headers):
                hw_empty_state = True
                continue
            row = {}
            for j, cell in enumerate(cells):
                key = headers[j] if j < len(headers) else f"col_{j}"
                row[key] = cell.text.strip()

            # Grab span attributes for detail page URL
            span = tr.find_elements(By.CSS_SELECTOR, "span[odev_id]")
            if span:
                row["_odev_id"] = span[0].get_attribute("odev_id")
                row["_ders_id"] = span[0].get_attribute("ids")

            hw_rows.append(row)
        break

    result["homework"] = {"headers": headers if hw_rows else [],
                          "rows": hw_rows,
                          "empty_state": hw_empty_state and not hw_rows}

    driver.save_screenshot(os.path.join(OUTPUT_DIR, "odevlerim.png"))
    print(f"  Found {len(hw_rows)} homework items")

    # Fetch detail for each homework item
    detail_count = 0
    for row in hw_rows:
        odev_id = row.pop("_odev_id", None)
        ders_id = row.pop("_ders_id", None)
        if odev_id and ders_id:
            try:
                row["detail"] = _scrape_homework_detail(
                    driver, odev_id, ders_id
                )
                detail_count += 1
            except Exception as e:
                row["detail"] = {"description": "", "attachments": [],
                                 "error": str(e)}

    print(f"  Fetched {detail_count} homework details")
    return result


# =============================================================================
# 3. TAKIM ÇALIŞMALARIM
# =============================================================================
def scrape_takim_calismalari(driver):
    """Scrape team activities."""
    print("\n[3/8] Takım Çalışmalarım")
    url = f"{BASE_URL}/pages/ogrenci_istekler/p_takim_calismalarim"
    driver.get(url)
    time.sleep(3)

    result = {"activities": []}

    tables = driver.find_elements(By.TAG_NAME, "table")
    for tbl in tables:
        headers = [th.text.strip() for th in tbl.find_elements(By.TAG_NAME, "th")]
        if headers:
            result["activities"] = extract_table(driver, tbl)
            break

    driver.save_screenshot(os.path.join(OUTPUT_DIR, "takim_calismalari.png"))
    print(f"  Found {len(result['activities'].get('rows', []))} team activities")
    return result


# =============================================================================
# 4. TAKVİM (tüm filtreler seçili)
# =============================================================================
def scrape_takvim(driver, sinif=None):
    """Scrape calendar events via FullCalendar JS API for last 4+ weeks.

    Uses month view + prev navigation to cover ~8 weeks.
    Extracts structured data: title, start, end, allDay from the JS API.
    """
    print("\n[4/8] Akademik Takvim")
    url = f"{BASE_URL}/pages/akademik_takvim/p_ogrenci"
    driver.get(url)
    _require_portal_access(driver, "Akademik Takvim", anchor="#select-all")
    wait_for(driver, (By.ID, "select-all"), timeout=15)

    # 1. Enable all filter checkboxes
    filter_ids = ("etkinlik", "sinav", "gezi", "diger",
                  "ders", "ogep", "veli_toplantisi", "kisisel")
    enabled = []
    for cb_id in filter_ids:
        try:
            cb = driver.find_element(By.ID, cb_id)
            if not cb.is_selected():
                driver.execute_script(
                    "arguments[0].click();", cb)
                enabled.append(cb_id)
                time.sleep(0.3)
        except Exception:
            pass
    if enabled:
        time.sleep(3)
    print(f"  Enabled filters: "
          f"{', '.join(enabled) or '(all already on)'}")

    # 2. Level filter: the student's own year group, not a hardcoded one.
    # This read "60" (6. Sınıf) from the day it was written; Işık is in 7-D.
    hedef = seviye_kodu(sinif) or "70"
    sinif_no = hedef[:-1]
    try:
        level_select = Select(driver.find_element(
            By.ID, "filter-select-level"))
        secili = level_select.first_selected_option.get_attribute("value")
        if secili != hedef:
            try:
                level_select.select_by_value(hedef)
            except Exception:
                # `<grade>0` is a pattern read off the single value we have
                # ever seen, and the page has never opened for this account,
                # so fall back to whichever option names the year group.
                for o in level_select.options:
                    if re.search(rf"\b{sinif_no}\s*\.?\s*s[ıi]n[ıi]f",
                                 o.text or "", re.I):
                        level_select.select_by_visible_text(o.text)
                        break
            time.sleep(1)
        print(f"  Level filter: {sinif or '(sınıf bilinmiyor)'} -> {hedef}")
    except Exception:
        pass

    # 3. Extract events via FullCalendar JS API
    # FullCalendar lazy-loads per month — reload page for each.
    # Scan: 2 previous + current + 4 forward = 7 months
    all_events = []
    seen = set()

    JS_GET_EVENTS = """
        if (!window.calendar) return [];
        return window.calendar.getEvents().map(function(e) {
            return {
                title: e.title || '',
                start: e.startStr || '',
                end: e.endStr || '',
                allDay: e.allDay || false,
                backgroundColor: e.backgroundColor || '',
                extendedProps: e.extendedProps || {}
            };
        });
    """
    JS_CALENDAR_READY = (
        "return typeof window.calendar !== 'undefined'"
        " && window.calendar.getEvents().length >= 0"
    )

    def _collect():
        header = ""
        try:
            h = driver.find_element(
                By.CSS_SELECTOR, ".fc-toolbar-title")
            header = h.text.strip()
        except Exception:
            pass
        events = driver.execute_script(
            JS_GET_EVENTS) or []
        new_count = 0
        for ev in events:
            key = (ev.get("title", ""),
                   ev.get("start", ""))
            if key not in seen and ev.get("title"):
                seen.add(key)
                all_events.append(ev)
                new_count += 1
        print(f"  {header}: {new_count} new"
              f" (total {len(all_events)})")

    def _nav(sel, count=1):
        for _ in range(count):
            before = driver.execute_script(
                "return window.calendar"
                " ? window.calendar.getEvents().length"
                " : 0")
            try:
                driver.find_element(
                    By.CSS_SELECTOR, sel).click()
            except Exception:
                break
            # Wait for event count to change or stabilize
            for _w in range(8):
                time.sleep(0.5)
                after = driver.execute_script(
                    "return window.calendar"
                    " ? window.calendar.getEvents()"
                    ".length : 0")
                if after != before:
                    time.sleep(0.5)
                    break
            else:
                time.sleep(1)

    wait_for_js(driver, JS_CALENDAR_READY, timeout=15)

    # Current month
    _collect()
    # Forward 4 months
    for _ in range(4):
        _nav(".fc-next-button")
        _collect()
    # Back to current, then 2 months back
    _nav(".fc-prev-button", 4)
    for _ in range(2):
        _nav(".fc-prev-button")
        _collect()

    driver.save_screenshot(
        os.path.join(OUTPUT_DIR, "takvim_final.png"))
    print(f"  Total unique events scraped:"
          f" {len(all_events)}")
    return all_events


# =============================================================================
# 5. DERS İÇERİKLERİ (dashboard tabları)
# =============================================================================
def _icerik_acik_hafta(driver, git=True):
    """Extract the dashboard's course tabs for whichever week is open.

    `git=False` when the caller has already selected a week: navigating again
    would reset the selector back to the current week and every week would
    come back with the same content.
    """
    if git:
        driver.get(f"{BASE_URL}/pages/ogrenci/")
        time.sleep(3)

    ders_tabs = {
        "Genel": "tab_genel",
        "Türkçe": "ders_1",
        "Matematik": "ders_2",
        "Fen Bilimleri": "ders_4",
        "Sosyal Bilgiler": "ders_5",
        "DKAB": "ders_7",
        "Görsel Sanatlar": "ders_8",
        "Müzik": "ders_9",
        "Beden Eğitimi": "ders_10",
        "İngilizce": "ders_16",
        "2. Yabancı Dil (F)": "ders_18",
        "Bilişim Teknolojileri": "ders_19",
        "PDR": "ders_20",
        "Sınıf Öğretmeni": "ders_65",
        "İngilizce Language": "ders_144",
        "İngilizce (2)": "ders_157",
        "Ahlak ve Yurttaşlık": "ders_172",
    }

    all_content = {}

    for ders_name, tab_id in ders_tabs.items():
        print(f"  Tab: {ders_name} (#{tab_id})")
        try:
            # Click the tab
            tab_link = driver.find_element(By.CSS_SELECTOR, f'a[href="#{tab_id}"]')
            driver.execute_script("arguments[0].click();", tab_link)
            time.sleep(1)

            # Find the tab content panel
            panel = driver.find_element(By.ID, tab_id)
            panel_text = panel.text.strip()

            # Extract any tables in this tab
            tables_data = []
            for tbl in panel.find_elements(By.TAG_NAME, "table"):
                tables_data.append(extract_table(driver, tbl))

            # Extract any list items
            items = []
            for li in panel.find_elements(By.TAG_NAME, "li"):
                text = li.text.strip()
                if text:
                    items.append(text[:2000])

            # Extract card content
            cards = []
            for card in panel.find_elements(By.CSS_SELECTOR, ".card, .card-body, .list-group-item"):
                text = card.text.strip()
                if text and len(text) > 5:
                    cards.append(text[:2000])

            all_content[ders_name] = {
                "tab_id": tab_id,
                "text": panel_text[:8000],
                "tables": tables_data,
                "items": items,
                "cards": cards,
            }

        except Exception as e:
            print(f"    Error: {e}")
            all_content[ders_name] = {"tab_id": tab_id, "error": str(e)}

    print(f"  Scraped {len(all_content)} course tabs")
    return all_content


def scrape_ders_icerikleri(driver, kapsam=None):
    """Scrape course content for every week in scope.

    Returns both shapes. `guncel` is the open week keyed by course — the
    contract /api/content and the assistant index already read — and
    `haftalar` maps each visited week's label to that same structure. The
    portal fills the whole year in; reading only the open week meant a week
    the school had already published stayed invisible until it arrived.
    """
    kapsam = kapsam or hafta_kapsami()
    print(f"\n[5/8] Ders İçerikleri (Dashboard) (kapsam: {kapsam})")
    driver.get(f"{BASE_URL}/pages/ogrenci/")
    time.sleep(3)

    def _hafta_select():
        try:
            return Select(driver.find_element(By.ID, "dp_icerik_secili_hafta"))
        except Exception:
            return None

    select = _hafta_select()
    if select is None:
        # No week selector on the page: one week is all there is to read.
        guncel = _icerik_acik_hafta(driver, git=False)
        return {"guncel": guncel, "guncel_hafta": "", "haftalar": {}}

    options = select.options
    current_idx = 0
    for i, opt in enumerate(options):
        if opt.is_selected():
            current_idx = i
            break

    hedef = hafta_indeksleri(len(options), current_idx, kapsam)
    print(f"  Week options: {len(options)} | in scope: {len(hedef)}"
          f" (current index {current_idx})")

    haftalar = {}
    guncel, guncel_hafta = {}, ""
    for idx in hedef:
        select = _hafta_select()
        if select is None:
            print("  Week selector disappeared, stopping")
            break
        etiket = select.options[idx].text.strip()
        print(f"  Week: {etiket}")
        select.select_by_index(idx)
        time.sleep(2)
        icerik = _icerik_acik_hafta(driver, git=False)
        haftalar[etiket] = icerik
        if idx == current_idx:
            guncel, guncel_hafta = icerik, etiket

    # A backfill starts at week 1 and the open week is in the list, so this
    # only binds if the selector never reported a selection.
    if not guncel and haftalar:
        guncel_hafta, guncel = next(iter(haftalar.items()))

    print(f"  Scraped {len(haftalar)} week(s) of course content")
    return {"guncel": guncel, "guncel_hafta": guncel_hafta, "haftalar": haftalar}


# =============================================================================
# 6. ÖGEP'LERİM
# =============================================================================
def scrape_ogep(driver):
    """Scrape ÖGEP (Öğrenci Gelişim Programı) sessions."""
    print("\n[6/8] ÖGEP'lerim")
    url = f"{BASE_URL}/pages/ogrenci_istekler/p_etutlerim"
    driver.get(url)
    time.sleep(3)

    # Select "Tamamı" to show all rows
    try:
        length_select = driver.find_element(
            By.CSS_SELECTOR, "select[name='t_etutlerim_length']"
        )
        Select(length_select).select_by_value("-1")
        time.sleep(2)
        print("  DataTables: selected 'Tamamı'")
    except Exception as e:
        print(f"  Could not select Tamamı: {e}")

    result = {"sessions": []}
    tables = driver.find_elements(By.TAG_NAME, "table")
    for tbl in tables:
        headers = [th.text.strip() for th in tbl.find_elements(By.TAG_NAME, "th")]
        if any("ÖGEP" in h for h in headers):
            result["sessions"] = extract_table(driver, tbl)
            break

    driver.save_screenshot(os.path.join(OUTPUT_DIR, "ogep.png"))
    print(f"  Found {len(result['sessions'].get('rows', []))} ÖGEP sessions")
    return result


# =============================================================================
# 7. GELİŞİM RAPORU (Notlar)
# =============================================================================
def scrape_gelisim_raporu(driver):
    """Scrape grade report for current semester."""
    print("\n[7/8] Gelişim Raporu")
    url = f"{BASE_URL}/pages/ogrenci_istekler/p_gelisim_raporum"
    driver.get(url)
    time.sleep(3)
    _require_portal_access(
        driver, "Gelişim Raporu", anchor="#genel_icerik_dp_ilgili_donem")

    result = {"semester": "", "grades": [], "physical": {}, "rubrics": []}

    # Get current semester from selector
    try:
        sel = Select(driver.find_element(
            By.ID, "genel_icerik_dp_ilgili_donem"
        ))
        result["semester"] = sel.first_selected_option.text.strip()
        print(f"  Semester: {result['semester']}")
    except Exception as e:
        print(f"  Semester selector error: {e}")

    # Find the grades table (has "Sınav" in headers)
    tables = driver.find_elements(By.TAG_NAME, "table")
    for tbl in tables:
        headers = [
            th.text.strip()
            for th in tbl.find_elements(By.TAG_NAME, "th")
        ]
        if any("Sınav" in h for h in headers):
            for tr in tbl.find_elements(By.TAG_NAME, "tr"):
                cells = tr.find_elements(By.TAG_NAME, "td")
                if not cells or _is_empty_state_row(cells, headers):
                    continue
                row = {}
                for j, cell in enumerate(cells):
                    key = headers[j] if j < len(headers) else f"col_{j}"
                    row[key] = cell.text.strip()
                result["grades"].append(row)
            print(f"  Found {len(result['grades'])} course grades")
            break

    # Find physical metrics table (Boy, Kilo, etc.)
    for tbl in tables:
        headers = [
            th.text.strip()
            for th in tbl.find_elements(By.TAG_NAME, "th")
        ]
        if any("Boy" in h for h in headers):
            trs = tbl.find_elements(By.TAG_NAME, "tr")
            for tr in trs:
                cells = tr.find_elements(By.TAG_NAME, "td")
                if cells and not _is_empty_state_row(cells, headers):
                    for j, cell in enumerate(cells):
                        if j < len(headers):
                            val = cell.text.strip()
                            if val:
                                result["physical"][headers[j]] = val
            break

    # Rubric assessments (kazanım/beceri levels) live outside the grades
    # table and are the whole report in terms without exams.
    try:
        result["rubrics"] = parse_gelisim_rubrics(driver.page_source)
        print(f"  Found {len(result['rubrics'])} rubric assessments")
    except Exception as e:
        print(f"  Rubric parse error: {e}")

    driver.save_screenshot(
        os.path.join(OUTPUT_DIR, "gelisim_raporum.png")
    )
    return result


# =============================================================================
# 8. DUYURULAR
# =============================================================================
def scrape_duyurular(driver):
    """Scrape school announcements."""
    print("\n[8/8] Duyurular")
    url = f"{BASE_URL}/pages/ogrenci_istekler/p_duyurular"
    driver.get(url)
    time.sleep(3)

    result = {"announcements": []}

    try:
        tbl = driver.find_element(By.ID, "aranan_tablo")
    except Exception:
        tbl = None
        tables = driver.find_elements(By.TAG_NAME, "table")
        for t in tables:
            headers = [
                th.text.strip()
                for th in t.find_elements(By.TAG_NAME, "th")
            ]
            if any("Başlık" in h for h in headers):
                tbl = t
                break

    if tbl:
        headers = [
            th.text.strip()
            for th in tbl.find_elements(By.TAG_NAME, "th")
        ]
        for tr in tbl.find_elements(By.TAG_NAME, "tr"):
            cells = tr.find_elements(By.TAG_NAME, "td")
            if not cells:
                continue
            if _is_empty_state_row(cells, headers):
                result["empty_state"] = True
                continue
            row = {}
            for j, cell in enumerate(cells):
                key = headers[j] if j < len(headers) else f"col_{j}"
                row[key] = cell.text.strip()
                # Capture attachment links
                links = cell.find_elements(By.TAG_NAME, "a")
                for link in links:
                    href = link.get_attribute("href") or ""
                    if href and "javascript" not in href.lower():
                        row[f"{key}_url"] = href
            result["announcements"].append(row)

    if result["announcements"]:
        result.pop("empty_state", None)
    driver.save_screenshot(os.path.join(OUTPUT_DIR, "duyurular.png"))
    print(f"  Found {len(result['announcements'])} announcements")
    return result


# =============================================================================
# 9. EK SAYFALAR (proje, rehberlik, kulüp, politika belgeleri)
# =============================================================================
EK_SAYFALAR = [
    ("ders_projeleri", "Ders Projeleri",
     "/pages/proje_istekler/p_ders_projeler"),
    ("rehberlik_formlari", "Rehberlik Formları",
     "/pages/ogrenci_istekler/p_ogrenci_rehberlik_formlari"),
    ("kulup_secimi", "Kulüp Seçimi",
     "/pages/kulup_istekler/p_kulup_secimi"),
    ("akademik_durustluk", "Akademik Dürüstlük Politikası",
     "/pages/proje_istekler/p_akademik_durustluk_politikasi"),
    ("mla_kaynakca", "MLA Kaynakça Hazırlama Rehberi",
     "/pages/proje_istekler/p_kaynakca_hazirlama_rehberi"),
]

_EK_SAYFA_JS = """
  const kok = document.querySelector('.content-wrapper, main, #content')
            || document.body;
  return {
    metin: (kok.innerText || '').replace(/[ \\t]+/g, ' ').trim().slice(0, 4000),
    belgeler: [...document.querySelectorAll('iframe, embed, object')]
      .map(e => e.getAttribute('src') || e.getAttribute('data') || '')
      .filter(Boolean),
    secenekler: [...document.querySelectorAll('select')]
      .map(s => ({
        ad: s.id || s.name || '',
        degerler: [...s.options].map(o => (o.text || '').trim())
                   .filter(t => t && !/seçiniz/i.test(t)),
      }))
      // Drop DataTables' page-size select (10/20/30/40/50): an all-numeric
      // list is the table's own chrome, not a choice the school is offering.
      .filter(s => s.degerler.length
                   && !s.degerler.every(v => /^\\d+$/.test(v))),
  };
"""


_SAYFALAMA = re.compile(
    r"(sayfa\b|gösteriliyor|toplam\s+\d+\s+kayıt|kayıt bulunamadı|^/\s*\d+$)",
    re.I,
)


def _tablo_kayit_tasiyor(cikti):
    """True only when a table holds a record, not its own scaffolding.

    Measured on the guidance-forms page, 2026-09-20, while it reported
    "toplam 0 kayıt": one table was its column names rendered into the body
    with `headers` empty, and another was the pager ("10 20 30 40 50",
    "Sayfa", "/ 0"). How many of them exist varies between runs — four on
    one run, none a minute later — so the rule cannot be "has rows".
    """
    veri = cikti or {}
    basliklar = [str(h).strip() for h in (veri.get("headers") or [])]
    adaylar = []
    for satir in (veri.get("rows") or []):
        hucreler = [str(c).strip() for c in satir]
        dolu = [c for c in hucreler if c]
        if len(dolu) < 2:
            continue                      # an empty-state spans one cell
        if basliklar and hucreler[:len(basliklar)] == basliklar:
            continue                      # the header echoed into the body
        if _SAYFALAMA.search(" ".join(dolu)):
            continue                      # DataTables' own pager
        adaylar.append(dolu)
    if not adaylar:
        return False
    # A table that declares no headers puts its column names in the first
    # body row, so one qualifying row there is a header, not a record.
    return len(adaylar) >= (1 if basliklar else 2)


def _sayfa_yerlesti(driver, saniye=10):
    """Wait for the page to settle rather than guessing how long it takes.

    A fixed 2.5s sleep read three of these pages before they had rendered:
    measured 2026-09-20 19:30, two Google Drive previews that had been
    captured minutes earlier came back as zero documents, and the text
    lengths across different URLs were byte-identical — the mark of reading
    a page that had not arrived. Waits for readyState plus any of the things
    worth reading, and gives up quietly, because some of these pages really
    are empty.
    """
    son = time.time() + saniye
    while time.time() < son:
        try:
            if driver.execute_script("return document.readyState") == "complete" \
               and driver.execute_script(
                   "return !!document.querySelector("
                   "'iframe, embed, object, table tbody tr, select option')"):
                return True
        except Exception:
            pass
        time.sleep(0.4)
    return False


def scrape_ek_sayfalar(driver):
    """Scrape the five portal pages nothing was reading yet.

    Measured 2026-09-20, all five are all but empty: Ders Projeleri lists no
    project (selection opens 1 November), Rehberlik Formları reports "toplam
    0 kayıt", Kulüp Seçimi's dropdowns have no options yet, and the two
    policy pages are Google Drive previews with no text of their own. So this
    stores what is there — the portal's own announcement text, any table that
    has rows, the document URLs — and records emptiness rather than inventing
    a section. Nothing surfaces a page whose `empty` is true.
    """
    print("\n[9/9] Ek Sayfalar")
    sonuc = {}
    for anahtar, baslik, yol in EK_SAYFALAR:
        kayit = {"title": baslik, "url": f"{BASE_URL}{yol}"}
        try:
            driver.get(f"{BASE_URL}{yol}")
            _sayfa_yerlesti(driver)
            _require_portal_access(driver, baslik)

            veri = driver.execute_script(_EK_SAYFA_JS) or {}
            tablolar = []
            for tbl in driver.find_elements(By.TAG_NAME, "table"):
                try:
                    if not tbl.find_elements(By.CSS_SELECTOR, "tbody tr"):
                        continue
                    cikti = extract_table(driver, tbl)
                    if _tablo_kayit_tasiyor(cikti):
                        tablolar.append(cikti)
                except Exception:
                    continue

            kayit.update({
                "text": veri.get("metin", ""),
                "tables": tablolar,
                "documents": veri.get("belgeler", []),
                "options": veri.get("secenekler", []),
            })
            kayit["empty"] = not (
                tablolar or kayit["documents"] or kayit["options"])
            print(f"  {baslik}: tablo={len(tablolar)}"
                  f" belge={len(kayit['documents'])}"
                  f" seçenek={len(kayit['options'])}"
                  f"{' (boş)' if kayit['empty'] else ''}")
        except PortalUnavailable as e:
            # The portal explaining itself is not a scrape failure; keep its
            # words so the dashboard can say why rather than showing nothing.
            kayit.update({"unavailable": {"reason": e.reason,
                                          "detail": str(e)}, "empty": True})
            print(f"  {baslik}: KULLANILAMAZ ({e.reason})")
        except Exception as e:
            kayit.update({"error": str(e)[:200], "empty": True})
            print(f"  {baslik}: HATA {str(e)[:80]}")
        sonuc[anahtar] = kayit
    return sonuc


# =============================================================================
# MAIN
# =============================================================================
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    driver = create_driver()

    try:
        if not login(driver):
            return

        data = {}
        data["scraped_at"] = datetime.now().isoformat()
        data["ogrenci_profili"] = scrape_ogrenci_profili(driver)
        data["ders_programi"] = scrape_ders_programi(driver)
        data["odevlerim"] = scrape_odevlerim(driver)
        data["takim_calismalari"] = scrape_takim_calismalari(driver)
        data["takvim"] = scrape_takvim(driver)
        icerik = scrape_ders_icerikleri(driver)
        data["ders_icerikleri"] = icerik.get("guncel") or {}
        data["ders_icerikleri_haftalar"] = icerik.get("haftalar") or {}
        data["ogep"] = scrape_ogep(driver)
        data["gelisim_raporu"] = scrape_gelisim_raporu(driver)
        data["duyurular"] = scrape_duyurular(driver)
        data["ek_sayfalar"] = scrape_ek_sayfalar(driver)

        # Save all data
        out_path = os.path.join(OUTPUT_DIR, "scraped_data.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n[DONE] All data saved to {out_path}")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
