# tests/test_retry.py
"""Tests for Google API retry logic."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.sync_to_google import _api_call_with_retry


class _FakeHttpError(Exception):
    def __init__(self, status):
        self.resp = type("R", (), {"status": status})()
        super().__init__(f"HTTP {status}")


class TestApiRetry:
    def test_success_on_first_try(self):
        calls = []
        def fn():
            calls.append(1)
            return "ok"
        assert _api_call_with_retry(fn) == "ok"
        assert len(calls) == 1

    def test_retries_on_503(self):
        attempts = []
        def fn():
            attempts.append(1)
            if len(attempts) < 3:
                raise _FakeHttpError(503)
            return "ok"
        assert _api_call_with_retry(fn, max_retries=3, base_delay=0) == "ok"
        assert len(attempts) == 3

    def test_gives_up_after_max_retries(self):
        def fn():
            raise _FakeHttpError(503)
        result = _api_call_with_retry(fn, max_retries=2, base_delay=0)
        assert result is None

    def test_no_retry_on_400(self):
        attempts = []
        def fn():
            attempts.append(1)
            raise _FakeHttpError(400)
        result = _api_call_with_retry(fn, max_retries=3, base_delay=0)
        assert result is None
        assert len(attempts) == 1
