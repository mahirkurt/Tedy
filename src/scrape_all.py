"""Scrape all relevant data from TED portal for the last 4 weeks."""
import json
import os
import re
import time
from datetime import datetime, timedelta

import ddddocr
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select

from src.env_loader import load_env
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
        driver.get(f"{BASE_URL}/pages/ogrenci_istekler/p_ogrenci_bilgilerim")
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


def extract_table(driver, table_el):
    """Extract a table into a list of dicts (header->value)."""
    headers = [th.text.strip() for th in table_el.find_elements(By.TAG_NAME, "th")]
    rows = []
    for tr in table_el.find_elements(By.TAG_NAME, "tr"):
        cells = tr.find_elements(By.TAG_NAME, "td")
        if not cells:
            continue
        if headers:
            row = {}
            for i, cell in enumerate(cells):
                key = headers[i] if i < len(headers) else f"col_{i}"
                row[key] = cell.text.strip()
            rows.append(row)
        else:
            rows.append([c.text.strip() for c in cells])
    return {"headers": headers, "rows": rows}


# =============================================================================
# 1. HAFTALIK DERS PROGRAMI
# =============================================================================
def scrape_ders_programi(driver):
    """Scrape weekly class schedule for the last 4 weeks."""
    print("\n[1/8] Haftalık Ders Programı")
    url = f"{BASE_URL}/pages/ogrenci_istekler/p_haftalik_ders_hazirlik_programim"
    driver.get(url)
    time.sleep(3)

    all_weeks = []

    # Find week selector dropdown
    try:
        select_el = driver.find_element(By.CSS_SELECTOR, "select")
        select = Select(select_el)
        options = select.options
        print(f"  Week options found: {len(options)}")

        # Find current week index
        current_idx = None
        for i, opt in enumerate(options):
            if opt.is_selected():
                current_idx = i
                break
        if current_idx is None:
            current_idx = len(options) - 1

        # Scrape last 4 weeks (current + 3 previous)
        start_idx = max(0, current_idx - 3)
        target_weeks = list(range(start_idx, current_idx + 1))

        for week_idx in target_weeks:
            select_el = driver.find_element(By.CSS_SELECTOR, "select")
            select = Select(select_el)
            opt_text = select.options[week_idx].text.strip()
            print(f"  Selecting week: {opt_text}")
            select.select_by_index(week_idx)
            time.sleep(2)

            # Extract the schedule grid
            week_data = {"week_label": opt_text, "schedule": [], "screenshot": None}

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

            # Screenshot
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
                "schedule": extract_table(driver, tables[0]),
            })

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
    time.sleep(3)

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
        time.sleep(2)
        print("  DataTables: selected 'Tamamı' (show all)")
    except Exception as e:
        print(f"  Could not select 'Tamamı': {e}")

    # Extract homework table + detail span IDs
    hw_rows = []
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

    result["homework"] = {"headers": headers if hw_rows else [], "rows": hw_rows}

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
def scrape_takvim(driver):
    """Scrape calendar events via FullCalendar JS API for last 4+ weeks.

    Uses month view + prev navigation to cover ~8 weeks.
    Extracts structured data: title, start, end, allDay from the JS API.
    """
    print("\n[4/8] Akademik Takvim")
    url = f"{BASE_URL}/pages/akademik_takvim/p_ogrenci"
    driver.get(url)
    time.sleep(3)

    # 1. Check "Tümünü Göster" (select-all) checkbox to enable all filters
    try:
        select_all = driver.find_element(By.ID, "select-all")
        if not select_all.is_selected():
            driver.execute_script("arguments[0].click();", select_all)
            time.sleep(1)
        print("  Enabled 'Tümünü Göster' filter")
    except Exception:
        # Fallback: check all individually
        checkboxes = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
        for cb in checkboxes:
            cb_id = cb.get_attribute("id") or ""
            if cb_id in ("select-all", "etkinlik", "sinav", "gezi", "diger",
                         "ders", "ogep", "veli_toplantisi", "kisisel"):
                if not cb.is_selected():
                    driver.execute_script("arguments[0].click();", cb)
                    time.sleep(0.3)
        print(f"  Enabled filters individually")
    time.sleep(2)

    # 2. Confirm 6. Sınıf is selected in level filter (value=60)
    try:
        level_select = Select(driver.find_element(By.ID, "filter-select-level"))
        selected_val = level_select.first_selected_option.get_attribute("value")
        if selected_val != "60":
            level_select.select_by_value("60")
            time.sleep(2)
        print(f"  Level filter: 6. Sınıf (value={selected_val})")
    except Exception as e:
        print(f"  Level filter check: {e}")

    # 3. Switch to month view for broader coverage
    try:
        month_btn = driver.find_element(By.CSS_SELECTOR, ".fc-dayGridMonth-button")
        month_btn.click()
        time.sleep(2)
        print("  Switched to month view")
    except Exception:
        pass

    # 4. Extract events via FullCalendar JS API for current + previous month
    all_events = []
    seen = set()  # deduplicate by (title, start)

    JS_GET_EVENTS = """
        if (!window.calendar) return [];
        var events = window.calendar.getEvents();
        return events.map(function(e) {
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

    for month_offset in range(2):  # current month + 1 previous
        # Get header (month name)
        header = ""
        try:
            h = driver.find_element(By.CSS_SELECTOR, ".fc-toolbar-title")
            header = h.text.strip()
        except Exception:
            pass

        events = driver.execute_script(JS_GET_EVENTS)
        if not events:
            events = []

        new_count = 0
        for ev in events:
            key = (ev.get("title", ""), ev.get("start", ""))
            if key not in seen and ev.get("title"):
                seen.add(key)
                all_events.append(ev)
                new_count += 1

        ss_name = f"takvim_month_{month_offset}.png"
        driver.save_screenshot(os.path.join(OUTPUT_DIR, ss_name))
        print(f"  {header}: {new_count} new events (total {len(all_events)})")

        # Navigate to previous month
        if month_offset < 1:
            try:
                prev_btn = driver.find_element(By.CSS_SELECTOR, ".fc-prev-button")
                prev_btn.click()
                time.sleep(2)
            except Exception:
                break

    print(f"  Total unique events scraped: {len(all_events)}")
    return all_events


# =============================================================================
# 5. DERS İÇERİKLERİ (dashboard tabları)
# =============================================================================
def scrape_ders_icerikleri(driver):
    """Scrape course content from dashboard tabs."""
    print("\n[5/8] Ders İçerikleri (Dashboard)")
    url = f"{BASE_URL}/pages/ogrenci/"
    driver.get(url)
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

    # Also handle week navigation on dashboard if present
    # Check for week selector on dashboard
    try:
        week_selectors = driver.find_elements(By.CSS_SELECTOR, "select, .week-selector")
        if week_selectors:
            print(f"  Found {len(week_selectors)} week selector(s) on dashboard")
    except Exception:
        pass

    print(f"  Scraped {len(all_content)} course tabs")
    return all_content


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

    result = {"semester": "", "grades": [], "physical": {}}

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
                if not cells:
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
                if cells:
                    for j, cell in enumerate(cells):
                        if j < len(headers):
                            val = cell.text.strip()
                            if val:
                                result["physical"][headers[j]] = val
            break

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

    driver.save_screenshot(os.path.join(OUTPUT_DIR, "duyurular.png"))
    print(f"  Found {len(result['announcements'])} announcements")
    return result


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
        data["ders_programi"] = scrape_ders_programi(driver)
        data["odevlerim"] = scrape_odevlerim(driver)
        data["takim_calismalari"] = scrape_takim_calismalari(driver)
        data["takvim"] = scrape_takvim(driver)
        data["ders_icerikleri"] = scrape_ders_icerikleri(driver)
        data["ogep"] = scrape_ogep(driver)
        data["gelisim_raporu"] = scrape_gelisim_raporu(driver)
        data["duyurular"] = scrape_duyurular(driver)

        # Save all data
        out_path = os.path.join(OUTPUT_DIR, "scraped_data.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n[DONE] All data saved to {out_path}")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
