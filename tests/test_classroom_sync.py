"""Tests for Google Classroom sync module."""
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestComputeHash:
    def test_same_input_same_hash(self):
        from src.sync_to_classroom import compute_hash
        item = {"title": "Test", "description": "Desc"}
        assert compute_hash(item) == compute_hash(item)

    def test_different_input_different_hash(self):
        from src.sync_to_classroom import compute_hash
        a = {"title": "Test A"}
        b = {"title": "Test B"}
        assert compute_hash(a) != compute_hash(b)

    def test_order_independent(self):
        from src.sync_to_classroom import compute_hash
        a = {"b": 2, "a": 1}
        b = {"a": 1, "b": 2}
        assert compute_hash(a) == compute_hash(b)

    def test_string_input(self):
        from src.sync_to_classroom import compute_hash
        h = compute_hash("simple string")
        assert isinstance(h, str) and len(h) == 16


class TestSyncState:
    def test_load_missing_file(self, tmp_path):
        from src.sync_to_classroom import load_sync_state
        state = load_sync_state(str(tmp_path / "nonexistent.json"))
        assert state == {}

    def test_save_and_load(self, tmp_path):
        from src.sync_to_classroom import load_sync_state, save_sync_state
        path = str(tmp_path / "state.json")
        data = {"key1": {"classroom_id": "abc", "last_hash": "def"}}
        save_sync_state(data, path)
        loaded = load_sync_state(path)
        assert loaded == data
