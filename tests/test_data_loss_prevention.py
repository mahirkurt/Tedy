"""Tests for data loss prevention: error isolation, atomic writes, health."""
import os
import json

from datetime import datetime

from src.json_utils import atomic_json_dump


class TestPartialScraperFailure:
    """Simulate the run_sync.py scraper loop: one fn raising should not
    prevent others from populating data."""

    def _run_scraper_loop(self, scrapers):
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


class TestAtomicWritePreservation:
    def test_atomic_dump_writes_valid_json(self, tmp_path):
        path = str(tmp_path / "data.json")
        payload = {"key": "value", "number": 42, "turkish": "ders programi"}
        atomic_json_dump(payload, path)
        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == payload

    def test_atomic_dump_preserves_original_on_error(self, tmp_path):
        path = str(tmp_path / "data.json")
        original = {"original": True}
        atomic_json_dump(original, path)

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
        path = str(tmp_path / "data.json")

        class Unserializable:
            pass

        try:
            atomic_json_dump({"bad": Unserializable()}, path)
        except TypeError:
            pass

        assert not os.path.exists(path + ".tmp")


class TestHealthReporting:
    def _build_health(self, scrape_errors, duration=10):
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
        parsed = datetime.fromisoformat(health["timestamp"])
        assert isinstance(parsed, datetime)

    def test_health_duration_non_negative(self):
        health = self._build_health([], duration=42.7)
        assert health["duration_seconds"] >= 0
        assert health["duration_seconds"] == 43

    def test_health_scrape_errors_is_list(self):
        health = self._build_health(["ders_programi: crash"])
        assert isinstance(health["scrape_errors"], list)
        assert len(health["scrape_errors"]) == 1
