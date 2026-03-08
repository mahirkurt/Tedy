"""Schema validation tests for external scraper tracker JSON files."""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")


def load_json(filename):
    """Load a JSON file from the output directory, skip test if not found."""
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        pytest.skip(f"{filename} not found")
    with open(path) as f:
        return json.load(f)


class TestEbaTextbooks:
    def test_is_dict(self):
        data = load_json("eba_textbooks_uploaded.json")
        assert isinstance(data, dict)

    def test_non_empty(self):
        data = load_json("eba_textbooks_uploaded.json")
        assert len(data) > 0

    def test_values_have_required_keys(self):
        data = load_json("eba_textbooks_uploaded.json")
        required = {"title", "course", "driveId", "link"}
        for key, entry in data.items():
            missing = required - set(entry.keys())
            assert not missing, f"Entry {key!r} missing keys: {missing}"

    def test_values_are_strings(self):
        data = load_json("eba_textbooks_uploaded.json")
        for key, entry in data.items():
            assert isinstance(entry["title"], str), f"Entry {key!r}: title not str"
            assert isinstance(entry["course"], str), f"Entry {key!r}: course not str"
            assert isinstance(entry["driveId"], str), f"Entry {key!r}: driveId not str"
            assert isinstance(entry["link"], str), f"Entry {key!r}: link not str"


class TestMebiVideos:
    def test_is_dict(self):
        data = load_json("mebi_videos_uploaded.json")
        assert isinstance(data, dict)

    def test_minimum_entries(self):
        data = load_json("mebi_videos_uploaded.json")
        assert len(data) >= 80, f"Expected 80+ entries, got {len(data)}"

    def test_values_have_required_keys(self):
        data = load_json("mebi_videos_uploaded.json")
        required = {"course", "unit", "topic", "driveId", "link"}
        for key, entry in data.items():
            missing = required - set(entry.keys())
            assert not missing, f"Entry {key!r} missing keys: {missing}"

    def test_values_are_strings(self):
        data = load_json("mebi_videos_uploaded.json")
        for key, entry in data.items():
            for field in ("course", "unit", "topic", "driveId", "link"):
                assert isinstance(entry[field], str), (
                    f"Entry {key!r}: {field} not str"
                )


class TestSebitvUploaded:
    def test_is_dict(self):
        data = load_json("sebitv_uploaded.json")
        assert isinstance(data, dict)

    def test_minimum_entries(self):
        data = load_json("sebitv_uploaded.json")
        assert len(data) >= 150, f"Expected 150+ entries, got {len(data)}"

    def test_values_have_required_keys(self):
        data = load_json("sebitv_uploaded.json")
        required = {"course", "unit", "title", "type", "driveId", "link"}
        for key, entry in data.items():
            missing = required - set(entry.keys())
            assert not missing, f"Entry {key!r} missing keys: {missing}"

    def test_values_are_strings(self):
        data = load_json("sebitv_uploaded.json")
        for key, entry in data.items():
            for field in ("course", "unit", "title", "type", "driveId", "link"):
                assert isinstance(entry[field], str), (
                    f"Entry {key!r}: {field} not str"
                )


class TestSebitvInteractive:
    def test_skips_if_not_found(self):
        data = load_json("sebitv_interactive_uploaded.json")
        # If we reach here, the file exists; just verify it is a dict
        assert isinstance(data, dict)


class TestHealthJson:
    def test_has_required_keys(self):
        data = load_json("health.json")
        required = {"timestamp", "success", "scrape_errors", "duration_seconds"}
        missing = required - set(data.keys())
        assert not missing, f"health.json missing keys: {missing}"

    def test_timestamp_is_string(self):
        data = load_json("health.json")
        assert isinstance(data["timestamp"], str)

    def test_success_is_bool(self):
        data = load_json("health.json")
        assert isinstance(data["success"], bool)

    def test_scrape_errors_is_list(self):
        data = load_json("health.json")
        assert isinstance(data["scrape_errors"], list)

    def test_duration_is_numeric(self):
        data = load_json("health.json")
        assert isinstance(data["duration_seconds"], (int, float))


class TestClassroomSync:
    def test_is_dict(self):
        data = load_json("classroom_sync.json")
        assert isinstance(data, dict)

    def test_non_empty(self):
        data = load_json("classroom_sync.json")
        assert len(data) > 0

    def test_values_have_required_keys(self):
        data = load_json("classroom_sync.json")
        required = {"classroom_id", "last_hash"}
        for key, entry in data.items():
            missing = required - set(entry.keys())
            assert not missing, f"Entry {key!r} missing keys: {missing}"

    def test_classroom_id_is_string(self):
        data = load_json("classroom_sync.json")
        for key, entry in data.items():
            assert isinstance(entry["classroom_id"], str), (
                f"Entry {key!r}: classroom_id not str"
            )

    def test_last_hash_is_string(self):
        data = load_json("classroom_sync.json")
        for key, entry in data.items():
            assert isinstance(entry["last_hash"], str), (
                f"Entry {key!r}: last_hash not str"
            )
