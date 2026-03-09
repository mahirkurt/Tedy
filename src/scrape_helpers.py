"""Shared Selenium wait and retry utilities for scrapers."""
import functools
import time

from selenium.common.exceptions import (
    StaleElementReferenceException,
    NoSuchElementException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def wait_for(driver, locator: tuple, timeout: int = 15):
    """Wait for element to be present. Returns element or raises TimeoutException."""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(locator)
    )


def wait_for_js(driver, js_expression: str, timeout: int = 15):
    """Wait for a JS expression to return a truthy value."""
    def check(d):
        result = d.execute_script(js_expression)
        return result if result else False
    return WebDriverWait(driver, timeout).until(check)


def retry_on_stale(max_retries: int = 3, delay: float = 1.0):
    """Decorator: retry on StaleElementReferenceException or NoSuchElementException."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries):
                try:
                    return fn(*args, **kwargs)
                except (
                    StaleElementReferenceException,
                    NoSuchElementException,
                ) as e:
                    last_exc = e
                    if attempt < max_retries - 1:
                        time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator
