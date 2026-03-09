"""Cookie-based session persistence for TED portal login."""
import json
import os

import requests

PORTAL_BASE = "https://portal.tedronesans.k12.tr"
PROFILE_URL = f"{PORTAL_BASE}/pages/ogrenci_istekler/p_ogrenci_bilgilerim"
DEFAULT_COOKIE_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "portal_cookies.json")


def save_cookies(cookies: list[dict], path: str = DEFAULT_COOKIE_PATH) -> None:
    """Save browser cookies to disk as JSON."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False)


def load_cookies(path: str = DEFAULT_COOKIE_PATH) -> list[dict] | None:
    """Load cookies from disk. Returns None if file missing or corrupted."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def check_session_valid(cookies: list[dict]) -> bool:
    """Test if cached cookies still represent a valid session."""
    session = requests.Session()
    for c in cookies:
        session.cookies.set(c["name"], c["value"], domain=c.get("domain", ""))
    try:
        resp = session.get(PROFILE_URL, timeout=10, allow_redirects=True)
        return resp.status_code == 200 and "/login" not in resp.url
    except requests.RequestException:
        return False


def apply_cookies_to_driver(driver, cookies: list[dict]) -> None:
    """Load cookies into Selenium driver. Must navigate to domain first."""
    driver.get(PORTAL_BASE)
    for c in cookies:
        cookie = {"name": c["name"], "value": c["value"]}
        if "domain" in c:
            cookie["domain"] = c["domain"]
        try:
            driver.add_cookie(cookie)
        except Exception:
            pass  # Skip cookies that Selenium rejects
    driver.refresh()
