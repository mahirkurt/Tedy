import pytest
from unittest.mock import MagicMock, patch
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
)

from src.scrape_helpers import wait_for, wait_for_js, retry_on_stale


def test_wait_for_returns_element():
    mock_driver = MagicMock()
    mock_element = MagicMock()
    with patch("src.scrape_helpers.WebDriverWait") as mock_wait:
        mock_wait.return_value.until.return_value = mock_element
        result = wait_for(mock_driver, ("id", "myElement"), timeout=5)
    assert result == mock_element


def test_wait_for_raises_on_timeout():
    mock_driver = MagicMock()
    with patch("src.scrape_helpers.WebDriverWait") as mock_wait:
        mock_wait.return_value.until.side_effect = TimeoutException()
        with pytest.raises(TimeoutException):
            wait_for(mock_driver, ("id", "myElement"), timeout=1)


def test_wait_for_js_returns_truthy_result():
    mock_driver = MagicMock()
    mock_driver.execute_script.return_value = [{"title": "Event"}]
    with patch("src.scrape_helpers.WebDriverWait") as mock_wait:
        mock_wait.return_value.until.side_effect = (
            lambda fn: fn(mock_driver))
        result = wait_for_js(
            mock_driver,
            "return window.calendar.getEvents()",
            timeout=5,
        )
    assert result == [{"title": "Event"}]


def test_retry_on_stale_retries_and_succeeds():
    call_count = 0

    @retry_on_stale(max_retries=3)
    def flaky_fn():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise StaleElementReferenceException()
        return "success"

    assert flaky_fn() == "success"
    assert call_count == 3


def test_retry_on_stale_raises_after_max():
    @retry_on_stale(max_retries=2)
    def always_fails():
        raise StaleElementReferenceException()

    with pytest.raises(StaleElementReferenceException):
        always_fails()
