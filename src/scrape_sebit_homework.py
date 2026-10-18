#!/usr/bin/env python3
"""Scrape SEBİT VCloud homework (digital assignments) completion status.

Logs in via Selenium, fetches homework list from the internal API,
and saves progress to output/sebit_homework.json.

The login (2026-10-18) solves the page's image captcha with ddddocr, posts
the form's own fields to /login and reads the XML answer; a refused password
or a closed account is recorded in output/.sebit_giris.json and not retried
with the same credentials for 24 hours. Every failure raises a
`SebitGirisHatasi` whose message is the sentence health.json carries.
"""
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.parse import urljoin

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.json_utils import atomic_json_dump
from src.env_loader import load_env
from src.login import captcha_oku, ocr_olustur

load_env()

OUTPUT_DIR = "output"
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "sebit_homework.json")
# The last refused login (outcome, time, credential fingerprint) — never the
# password. Read before a browser starts; see `giris_denensin_mi`.
GIRIS_DURUMU = os.path.join(OUTPUT_DIR, ".sebit_giris.json")

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


class SebitGirisHatasi(RuntimeError):
    """SEBİT refused or could not complete the login. The message is the
    sentence `run_sync._platform_adimi` writes into health.json."""


class SebitSifreHatali(SebitGirisHatasi):
    """`login.incorrect`: the stored user name or password is not accepted."""


class SebitHesapKapali(SebitGirisHatasi):
    """`login.userblocked`: the account is closed; only the school reopens it."""


KOD_DENEME_SINIRI = 3
SAYFA_BEKLEME = 20
GIRIS_BETIK_SURESI = 30
ERTELEME = timedelta(hours=24)
# Outcomes a retry cannot change. The same credentials wait ERTELEME before
# the next attempt, so a cron every 15 minutes does not walk the failed-
# attempt counter (`csidValue`) into a locked account.
ERTELENEN = ("sifre_hatali", "hesap_kapali")
KOD_HATASI_MESAJI = "Geçersiz bir güvenlik kodu girdiniz, lütfen tekrar deneyin."
_BOS_HEDEF = ("", "null", "undefined")

# The page's own submitHandler without jQuery: the same fields in the same
# order and encoding, posted to /login from the login page so the session
# cookie and the captchaId belong together. The answer text comes back to
# Python instead of to the page's afterLogin, which only shows a toast.
GIRIS_BETIGI = """
var cb = arguments[arguments.length - 1];
var un = String(arguments[0]).trim(), pw = String(arguments[1]).trim(),
    kod = String(arguments[2]);
var idAlani = document.getElementById('captchaId');
var ruAlani = document.getElementById('l_ru');
var ga = (typeof gaUserId !== 'undefined' && gaUserId) ? gaUserId : '';
var govde = 'captchaId=' + encodeURIComponent(idAlani ? idAlani.value : '')
  + '&captchaResponse=' + encodeURIComponent(kod)
  + '&gaCode=' + encodeURIComponent(ga)
  + '&l_op=tibeslogin&l_un=' + encodeURIComponent(un)
  + '&l_pw=' + encodeURIComponent(pw).replace(/'/g, '%27')
  + '&l_kmli=false&l_ru=' + encodeURIComponent(ruAlani ? ruAlani.value : undefined);
fetch('/login', {
  method: 'POST', credentials: 'same-origin', cache: 'no-store',
  headers: {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest'},
  body: govde
}).then(function (r) {
  return r.text().then(function (t) { cb({s: r.status, b: t}); });
}).catch(function (e) { cb({s: -1, b: String(e)}); });
"""


def _kisalt(metin, sinir=160):
    metin = " ".join(str(metin).split())
    return metin if len(metin) <= sinir else metin[: sinir - 1] + "…"


def giris_sonucu(xml_metni):
    """Read the `/login` XML answer the way the page's `afterLogin` does.

    Returns `(durum, ayrinti)`:
      basarili      `message` "100"; ayrinti is the URL to open next —
                    `afterLoginUrl`, or `redirectURL` when that is empty,
                    "null" or "undefined" — possibly "".
      hesap_kapali  `key` login.userblocked.
      kod_hatali    the captcha message.
      sifre_hatali  `key` login.incorrect.
      bilinmiyor    anything else, with the server's own words.
    An empty, truncated or non-XML answer is `bilinmiyor`, never a success.
    """
    if not isinstance(xml_metni, str) or not xml_metni.strip():
        return "bilinmiyor", "boş yanıt"
    # The answer is five flat fields. A DTD has no business in it, and
    # refusing one keeps entity tricks away from the stdlib parser (no
    # defusedxml in .venv; ElementTree resolves no external entities anyway).
    if re.search(r"<!(DOCTYPE|ENTITY)", xml_metni, re.IGNORECASE):
        return "bilinmiyor", "çözülemeyen yanıt: DTD taşıyor"
    try:
        kok = ET.fromstring(xml_metni.strip())
    except ET.ParseError:
        return "bilinmiyor", "çözülemeyen yanıt: " + _kisalt(xml_metni, 80)

    def alan(ad):
        oge = next(kok.iter(ad), None)
        return (oge.text or "").strip() if oge is not None else ""

    anahtar, mesaj = alan("key"), alan("message")
    if mesaj == "100":
        hedef = alan("afterLoginUrl")
        if hedef in _BOS_HEDEF:
            hedef = alan("redirectURL")
        return "basarili", "" if hedef in _BOS_HEDEF else hedef
    if anahtar == "login.userblocked":
        return "hesap_kapali", _kisalt(mesaj or anahtar)
    if mesaj == KOD_HATASI_MESAJI:
        return "kod_hatali", mesaj
    if anahtar == "login.incorrect":
        return "sifre_hatali", _kisalt(mesaj or anahtar)
    if not anahtar and not mesaj:
        return "bilinmiyor", "çözülemeyen yanıt: " + _kisalt(xml_metni, 80)
    return "bilinmiyor", _kisalt(mesaj or anahtar)


def parmak_izi(kullanici, sifre):
    """Which credentials a refusal was about: a truncated hash, so a change
    in .env is noticed without the password being written down."""
    return hashlib.sha256(f"{kullanici}\n{sifre}".encode("utf-8")).hexdigest()[:16]


def _kayit_zamani(kayit):
    try:
        return datetime.fromisoformat(kayit["zaman"])
    except (KeyError, TypeError, ValueError):
        return None


def giris_denensin_mi(kayit, iz, simdi):
    """Should this run log in? Only a refusal of these same credentials in
    the last ERTELEME says no; anything unreadable says yes — a broken state
    file must never stop the login for good."""
    if not isinstance(kayit, dict) or kayit.get("sonuc") not in ERTELENEN:
        return True
    if kayit.get("parmak_izi") != iz:
        return True
    zaman = _kayit_zamani(kayit)
    if zaman is None:
        return True
    return not (timedelta(0) <= simdi - zaman < ERTELEME)


def _durum_oku():
    try:
        with open(GIRIS_DURUMU, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _durumu_sil():
    try:
        os.remove(GIRIS_DURUMU)
    except FileNotFoundError:
        pass


def _ret_hatasi(sonuc, zaman):
    """The health.json sentence for a refusal, fresh or remembered."""
    saat = (f"son deneme {zaman:%d.%m %H:%M}, "
            f"sonraki deneme {zaman + ERTELEME:%d.%m %H:%M}")
    if sonuc == "hesap_kapali":
        return SebitHesapKapali(f"SEBİT hesabı kapalı; okulla iletişime geçin ({saat})")
    return SebitSifreHatali(
        "SEBİT kullanıcı adı ya da şifresi kabul edilmedi; .env'deki "
        f"SEBIT_TC/SEBIT_PASSWORD güncellenmeli ({saat})")


def giris_kontrolu():
    """Raise, before any browser starts, when this run must not log in."""
    if not SEBIT_TC or not SEBIT_PASSWORD:
        raise SebitGirisHatasi(
            "SEBİT kimlik bilgileri .env'de yok (SEBIT_TC/SEBIT_PASSWORD)")
    kayit = _durum_oku()
    if not giris_denensin_mi(kayit, parmak_izi(SEBIT_TC, SEBIT_PASSWORD),
                             datetime.now()):
        print("[SEBIT-HW] Giriş denenmedi: aynı kimlik bilgileri son 24 saatte reddedildi")
        raise _ret_hatasi(kayit["sonuc"], _kayit_zamani(kayit))


def _kod_satiri_gorunur(driver):
    return any(oge.is_displayed()
               for oge in driver.find_elements(By.CSS_SELECTOR, ".captcha-rows"))


def sebit_login(driver, ocr=None):
    """Log in to SEBİT VCloud and open the page the server sends us to.

    The page posts the form by AJAX and answers XML; that answer is read
    (`giris_sonucu`) instead of guessing from `current_url` after a fixed
    sleep. A wrong captcha is retried with a fresh one, at most
    KOD_DENEME_SINIRI times; a refused password or a closed account stops at
    once and is recorded, so the next runs do not feed the lockout counter.
    """
    driver.set_script_timeout(GIRIS_BETIK_SURESI)
    for deneme in range(1, KOD_DENEME_SINIRI + 1):
        driver.get(f"{BASE}/tr/giris.jsp")
        WebDriverWait(driver, SAYFA_BEKLEME).until(
            EC.presence_of_element_located((By.ID, "l_un")))

        kod = ""
        if _kod_satiri_gorunur(driver):
            if ocr is None:
                ocr = ocr_olustur()
            kod = captcha_oku(ocr, driver.find_element(By.ID, "captchaImg"))
            if not re.fullmatch(r"\d{5}", kod):
                # not submitted: a wrong code would feed the counter too
                print(f"[SEBIT-HW] Güvenlik kodu okunamadı "
                      f"({deneme}/{KOD_DENEME_SINIRI})")
                continue

        yanit = driver.execute_async_script(
            GIRIS_BETIGI, SEBIT_TC, SEBIT_PASSWORD, kod) or {}
        durum, ayrinti = giris_sonucu(yanit.get("b"))

        if durum == "basarili":
            _durumu_sil()
            driver.get(urljoin(f"{BASE}/login", ayrinti or "/"))
            print("[SEBIT-HW] Login successful")
            return True
        if durum == "kod_hatali":
            print(f"[SEBIT-HW] Güvenlik kodu kabul edilmedi "
                  f"({deneme}/{KOD_DENEME_SINIRI})")
            continue
        if durum in ERTELENEN:
            zaman = datetime.now().replace(microsecond=0)
            atomic_json_dump({
                "sonuc": durum,
                "zaman": zaman.isoformat(),
                "parmak_izi": parmak_izi(SEBIT_TC, SEBIT_PASSWORD),
                "mesaj": ayrinti,
            }, GIRIS_DURUMU)
            raise _ret_hatasi(durum, zaman)
        raise SebitGirisHatasi(
            f"SEBİT girişi tanınmayan bir yanıt verdi "
            f"(HTTP {yanit.get('s')}): {ayrinti}")

    raise SebitGirisHatasi(
        f"SEBİT güvenlik kodu {KOD_DENEME_SINIRI} denemede de kabul edilmedi; "
        "sonraki senkronda yeniden denenecek")


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
    giris_kontrolu()
    driver = create_driver()

    try:
        sebit_login(driver)

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
    try:
        progress = scrape()
    except SebitGirisHatasi as e:
        print(f"[SEBIT-HW] {e}")
        sys.exit(1)
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
