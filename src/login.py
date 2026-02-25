"""Login to TED Rönesans portal with captcha OCR."""
import os
import time

import ddddocr
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

LOGIN_URL = "https://portal.tedronesans.k12.tr/login"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
MAX_CAPTCHA_RETRIES = 5


def create_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-setuid-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,1024")
    return webdriver.Chrome(options=opts)


def solve_captcha(driver, ocr):
    """Screenshot the captcha image element and OCR it."""
    captcha_img = driver.find_element(
        By.CSS_SELECTOR, 'img[src*="CaptchaHandler"]'
    )
    png_bytes = captcha_img.screenshot_as_png
    result = ocr.classification(png_bytes)
    return result.strip()


def login(username: str, password: str, role: str = "ogrenci"):
    """
    Login to the portal.

    role: "ogrenci" | "veli" | "ogretmen"
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ocr = ddddocr.DdddOcr(show_ad=False)
    driver = create_driver()

    button_map = {
        "ogretmen": "bt_giris_yap",
        "ogrenci": "btn_ogrenci",
        "veli": "btn_veli",
    }
    btn_id = button_map.get(role, "btn_ogrenci")

    try:
        for attempt in range(1, MAX_CAPTCHA_RETRIES + 1):
            print(f"\n--- Attempt {attempt}/{MAX_CAPTCHA_RETRIES} ---")

            driver.get(LOGIN_URL)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "tx_kullanici_adi"))
            )

            # Fill credentials
            user_input = driver.find_element(By.ID, "tx_kullanici_adi")
            pass_input = driver.find_element(By.ID, "tx_kullanici_sifre")
            code_input = driver.find_element(By.ID, "txtKod")

            user_input.clear()
            user_input.send_keys(username)
            pass_input.clear()
            pass_input.send_keys(password)

            # Solve captcha
            captcha_text = solve_captcha(driver, ocr)
            print(f"Captcha OCR: '{captcha_text}'")

            if not captcha_text or not captcha_text.isdigit():
                print("OCR returned non-numeric result, retrying...")
                continue

            code_input.clear()
            code_input.send_keys(captcha_text)

            # Click the appropriate login button
            submit_btn = driver.find_element(By.ID, btn_id)
            submit_btn.click()

            # Wait for navigation
            time.sleep(3)

            current_url = driver.current_url
            print(f"Current URL: {current_url}")

            # Check login success
            if "/login" not in current_url.lower():
                print(f"LOGIN SUCCESS! Redirected to: {current_url}")
                screenshot_path = os.path.join(OUTPUT_DIR, "after_login.png")
                driver.save_screenshot(screenshot_path)
                print(f"Post-login screenshot: {screenshot_path}")

                # Save cookies for future use
                cookies = driver.get_cookies()
                print(f"Cookies: {len(cookies)} cookies captured")
                return driver, cookies

            # Check for error messages on page
            page_text = driver.page_source
            if "hatalı" in page_text.lower() or "error" in page_text.lower():
                print("Login failed - credentials or captcha error, retrying...")
            else:
                print("Still on login page, retrying...")

        print("All captcha attempts exhausted.")
        return None, None

    except Exception as e:
        print(f"Error: {e}")
        driver.save_screenshot(os.path.join(OUTPUT_DIR, "error.png"))
        driver.quit()
        raise


if __name__ == "__main__":
    from src.env_loader import load_env
    load_env()

    driver, cookies = login(
        username=os.environ.get("PORTAL_USERNAME", ""),
        password=os.environ.get("PORTAL_PASSWORD", ""),
        role="ogrenci",
    )

    if driver:
        print("\n=== Login successful ===")
        print(f"Page title: {driver.title}")
        print(f"URL: {driver.current_url}")
        driver.quit()
    else:
        print("\n=== Login failed ===")
