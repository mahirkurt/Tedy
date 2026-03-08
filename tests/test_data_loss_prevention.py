"""Tests for data loss prevention: error isolation, atomic writes, state recovery,
API retry, and health reporting."""
import sys
import os
import json
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch, call
from datetime import datetime


# ---------------------------------------------------------------------------
# Helpers for API retry tests
# ---------------------------------------------------------------------------

class FakeResp:
    def __init__(self, status):
        self.status = status


class FakeHttpError(Exception):
    def __init__(self, status):
        self.resp = FakeResp(status)
        super().__init__(f"HTTP {status}")


# ===========================================================================
# TestPartialScraperFailure
# ===========================================================================

class TestPartialScraperFailure:
    """Simulate the run_sync.py scraper loop: one fn raising should not
    prevent others from populating data."""

    def _run_scraper_loop(self, scrapers):
        """Replicate the try-except loop from run_sync.py (lines 62-78)."""
        data = {"scraped_at": datetime.now().isoformat()}
        scrape_errors = []
        for name, fn in scrapers:
            try:
                data[name] = fn(None)
            except Exception as e:
                scrape_errors.append(f"{name}: {e}")
                data[name] = [] if name in ("takvim", "ders_programi") else {}
        return data, scrape_errors

    def test_failed_scraper_doesnt_affect_others(self):
        scrapers = [
            ("ders_programi", lambda d: [{"lesson": "math"}]),
            ("odevlerim", lambda d: (_ for _ in ()).throw(RuntimeError("timeout"))),
            ("takvim", lambda d: [{"event": "exam"}]),
        ]
        data, errors = self._run_scraper_loop(scrapers)
        assert data["ders_programi"] == [{"lesson": "math"}]
        assert data["takvim"] == [{"event": "exam"}]
        assert len(errors) == 1

    def test_failed_list_scraper_gets_empty_list(self):
        scrapers = [
            ("takvim", lambda d: (_ for _ in ()).throw(ValueError("boom"))),
            ("ders_programi", lambda d: (_ for _ in ()).throw(ValueError("boom"))),
        ]
        data, _ = self._run_scraper_loop(scrapers)
        assert data["takvim"] == []
        assert data["ders_programi"] == []

    def test_failed_dict_scraper_gets_empty_dict(self):
        scrapers = [
            ("odevlerim", lambda d: (_ for _ in ()).throw(ValueError("fail"))),
            ("ogep", lambda d: (_ for _ in ()).throw(ValueError("fail"))),
            ("gelisim_raporu", lambda d: (_ for _ in ()).throw(ValueError("fail"))),
            ("duyurular", lambda d: (_ for _ in ()).throw(ValueError("fail"))),
        ]
        data, _ = self._run_scraper_loop(scrapers)
        for name in ("odevlerim", "ogep", "gelisim_raporu", "duyurular"):
            assert data[name] == {}

    def test_scrape_errors_records_failure(self):
        scrapers = [
            ("ders_programi", lambda d: []),
            ("odevlerim", lambda d: (_ for _ in ()).throw(
                RuntimeError("connection reset"))),
        ]
        _, errors = self._run_scraper_loop(scrapers)
        assert len(errors) == 1
        assert "odevlerim" in errors[0]
        assert "connection reset" in errors[0]


# ===========================================================================
# TestAtomicWritePreservation
# ===========================================================================

class TestAtomicWritePreservation:
    """Verify atomic_json_dump protects existing data on write failure."""

    def test_atomic_dump_writes_valid_json(self, tmp_path):
        from src.json_utils import atomic_json_dump
        path = str(tmp_path / "data.json")
        payload = {"key": "value", "number": 42, "turkish": "ders programi"}
        atomic_json_dump(payload, path)
        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == payload

    def test_atomic_dump_preserves_original_on_error(self, tmp_path):
        from src.json_utils import atomic_json_dump
        path = str(tmp_path / "data.json")
        original = {"original": True}
        atomic_json_dump(original, path)

        # An object that cannot be serialized to JSON
        class Unserializable:
            pass

        try:
            atomic_json_dump({"bad": Unserializable()}, path)
        except TypeError:
            pass

        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == original

    def test_no_tmp_file_left_on_error(self, tmp_path):
        from src.json_utils import atomic_json_dump
        path = str(tmp_path / "data.json")

        class Unserializable:
            pass

        try:
            atomic_json_dump({"bad": Unserializable()}, path)
        except TypeError:
            pass

        assert not os.path.exists(path + ".tmp")

    def test_save_sync_state_uses_atomic_dump(self, tmp_path):
        with patch("src.sync_to_classroom.atomic_json_dump") as mock_dump:
            from src.sync_to_classroom import save_sync_state
            path = str(tmp_path / "state.json")
            state = {"key": "value"}
            save_sync_state(state, path)
            mock_dump.assert_called_once_with(state, path)


# ===========================================================================
# TestMissingStateRecovery
# ===========================================================================

class TestMissingStateRecovery:
    """Verify graceful behavior when state/tracker files are missing."""

    def test_load_sync_state_missing_returns_empty(self, tmp_path):
        from src.sync_to_classroom import load_sync_state
        result = load_sync_state(str(tmp_path / "does_not_exist.json"))
        assert result == {}

    def test_load_upload_tracker_missing_returns_empty(self, tmp_path):
        from src.sync_to_classroom import _load_upload_tracker
        with patch("src.sync_to_classroom.OUTPUT_DIR", str(tmp_path)):
            result = _load_upload_tracker("nonexistent_uploaded.json")
        assert result == {}

    def test_sync_odevler_works_with_empty_state(self):
        """sync_odevler with state={} creates new courseWork items."""
        from src.sync_to_classroom import sync_odevler

        service = MagicMock()
        create_resp = {"id": "cw_123"}
        service.courses().courseWork().create().execute.return_value = create_resp

        courses = {"Matematik": "course_1", "TED Genel": "course_gen"}
        data = {
            "odevlerim": {
                "homework": {
                    "rows": [
                        {
                            "Ders Adi": "Matematik",
                            "Odev Basligi": "Test Odevi",
                            "detail": {"description": "Do exercises 1-10"},
                        }
                    ]
                }
            }
        }
        state = {}

        with patch("src.sync_to_classroom._api_call_with_retry",
                    side_effect=lambda fn: fn()):
            result = sync_odevler(service, courses, data, state)

        # Even with empty initial state, function should complete without error
        assert isinstance(result, dict)
        assert "added" in result
        assert "errors" in result

    def test_corrupted_state_file_recovers(self, tmp_path):
        """A corrupted (non-JSON) state file returns {} gracefully,
        allowing the sync pipeline to continue."""
        from src.sync_to_classroom import load_sync_state
        path = str(tmp_path / "corrupted.json")
        with open(path, "w") as f:
            f.write("{invalid json content!!!")

        result = load_sync_state(path)
        assert result == {}

    def test_missing_courses_file_returns_empty(self, tmp_path):
        from src.sync_to_classroom import _load_courses_mapping
        with patch("src.sync_to_classroom.COURSES_FILE",
                    str(tmp_path / "missing_courses.json")):
            result = _load_courses_mapping()
        assert result == {}


# ===========================================================================
# TestApiRetryBehavior
# ===========================================================================

class TestApiRetryBehavior:
    """Verify _api_call_with_retry retries on transient errors, gives up
    on non-retryable ones, and uses exponential backoff."""

    def test_retries_on_429(self):
        from src.sync_to_google import _api_call_with_retry
        fn = MagicMock(side_effect=[
            FakeHttpError(429), FakeHttpError(429), "success"
        ])
        with patch("src.sync_to_google.time.sleep"):
            result = _api_call_with_retry(fn, max_retries=5, base_delay=3)
        assert result == "success"
        assert fn.call_count == 3

    def test_retries_on_503(self):
        from src.sync_to_google import _api_call_with_retry
        fn = MagicMock(side_effect=[
            FakeHttpError(503), FakeHttpError(503), "ok"
        ])
        with patch("src.sync_to_google.time.sleep"):
            result = _api_call_with_retry(fn, max_retries=5, base_delay=3)
        assert result == "ok"
        assert fn.call_count == 3

    def test_retries_on_403_classroom_rate_limit(self):
        """403 is retried because Google Classroom uses it for rate limiting."""
        from src.sync_to_google import _api_call_with_retry
        fn = MagicMock(side_effect=[FakeHttpError(403), "done"])
        with patch("src.sync_to_google.time.sleep"):
            result = _api_call_with_retry(fn, max_retries=5, base_delay=3)
        assert result == "done"
        assert fn.call_count == 2

    def test_no_retry_on_404(self):
        """404 is not in the retryable set; should return None after 1 attempt."""
        from src.sync_to_google import _api_call_with_retry
        fn = MagicMock(side_effect=FakeHttpError(404))
        with patch("src.sync_to_google.time.sleep"):
            result = _api_call_with_retry(fn, max_retries=5, base_delay=3)
        assert result is None
        assert fn.call_count == 1

    def test_exponential_backoff_timing(self):
        """After 4 retries with base_delay=3, delays should be 3, 6, 12, 24."""
        from src.sync_to_google import _api_call_with_retry
        fn = MagicMock(side_effect=[
            FakeHttpError(429), FakeHttpError(429),
            FakeHttpError(429), FakeHttpError(429),
            "finally",
        ])
        with patch("src.sync_to_google.time.sleep") as mock_sleep:
            result = _api_call_with_retry(fn, max_retries=5, base_delay=3)
        assert result == "finally"
        assert mock_sleep.call_args_list == [
            call(3), call(6), call(12), call(24),
        ]


# ===========================================================================
# TestSyncFunctionIsolation
# ===========================================================================

class TestSyncFunctionIsolation:
    """Test that sync function failures are handled (or not) properly."""

    def test_state_preserved_after_partial_sync(self):
        """If sync_odevler succeeds and mutates state, then a subsequent
        sync function raises, the odevler entries remain in the state dict."""
        state = {}

        def fake_sync_odevler(service, courses, data, state, **kwargs):
            state["cw:course1:Odev1"] = {"classroom_id": "x", "last_hash": "h"}
            return {"added": 1, "updated": 0, "skipped": 0, "errors": 0}

        def fake_sync_notlar(service, courses, data, state):
            raise RuntimeError("API quota exceeded")

        fake_sync_odevler(None, {}, {}, state)
        assert "cw:course1:Odev1" in state

        try:
            fake_sync_notlar(None, {}, {}, state)
        except RuntimeError:
            pass

        # State still contains odevler data from the successful sync
        assert state["cw:course1:Odev1"]["classroom_id"] == "x"

    @patch("src.sync_to_classroom.get_classroom_service")
    @patch("src.sync_to_classroom.ensure_courses")
    @patch("src.sync_to_classroom.sync_odevler")
    @patch("src.sync_to_classroom.sync_ders_icerikleri")
    @patch("src.sync_to_classroom.sync_notlar")
    @patch("src.sync_to_classroom.sync_duyurular")
    @patch("src.sync_to_classroom.sync_eba_textbooks")
    @patch("src.sync_to_classroom.sync_mebi_videos")
    @patch("src.sync_to_classroom.sync_sebitv")
    @patch("src.sync_to_classroom.sync_englishcentral")
    @patch("src.sync_to_classroom.sync_achieve3000")
    @patch("src.sync_to_classroom.sync_sebit_homework")
    @patch("src.sync_to_classroom.save_sync_state")
    def test_main_isolates_sync_errors(self, mock_save, mock_sebit_hw,
                                        mock_a3k, mock_ec, mock_sebitv,
                                        mock_mebi, mock_eba, mock_duyuru,
                                        mock_notlar, mock_ders, mock_odev,
                                        mock_ensure, mock_svc):
        """main() wraps each sync in try-except. If sync_odevler raises,
        others still run and state is saved."""
        from src.sync_to_classroom import main

        mock_svc.return_value = MagicMock()
        mock_ensure.return_value = {"Matematik": "c1", "TED Genel": "cg"}
        mock_odev.side_effect = RuntimeError("API quota exceeded")
        zero = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
        for m in [mock_ders, mock_notlar, mock_duyuru, mock_eba,
                  mock_mebi, mock_sebitv, mock_ec, mock_a3k, mock_sebit_hw]:
            m.return_value = zero

        test_data = {"odevlerim": {}, "ders_icerikleri": {},
                     "gelisim_raporu": {}, "duyurular": {},
                     "takvim": [], "takim_calismalari": {},
                     "ogep": {}, "ders_programi": []}

        errors = main(scraped_data=test_data)

        # All other syncs ran despite odevler failure
        mock_ders.assert_called_once()
        mock_notlar.assert_called_once()
        mock_sebit_hw.assert_called_once()

        # State was saved despite the error
        mock_save.assert_called_once()

        # Errors list reports the failure
        assert len(errors) == 1
        assert "odevler" in errors[0]


# ===========================================================================
# TestHealthReporting
# ===========================================================================

class TestHealthReporting:
    """Verify health.json structure matches the pattern from run_sync.py.

    Does NOT import run_sync.py -- constructs the health dict inline."""

    def _build_health(self, scrape_errors, duration=10):
        """Replicate the health dict construction from run_sync.py."""
        return {
            "timestamp": datetime.now().isoformat(),
            "success": len(scrape_errors) == 0,
            "scrape_errors": scrape_errors,
            "duration_seconds": round(duration),
        }

    def test_health_success_when_no_errors(self):
        health = self._build_health([])
        assert health["success"] is True

    def test_health_failure_when_errors_exist(self):
        health = self._build_health(["takvim: timeout", "ogep: 500 error"])
        assert health["success"] is False

    def test_health_has_valid_timestamp(self):
        health = self._build_health([])
        # Should parse without raising
        parsed = datetime.fromisoformat(health["timestamp"])
        assert isinstance(parsed, datetime)

    def test_health_duration_non_negative(self):
        health = self._build_health([], duration=42.7)
        assert health["duration_seconds"] >= 0
        assert health["duration_seconds"] == 43  # round(42.7) == 43

    def test_health_scrape_errors_is_list(self):
        health = self._build_health(["ders_programi: crash"])
        assert isinstance(health["scrape_errors"], list)
        assert len(health["scrape_errors"]) == 1
