"""Tests for atomic JSON write utility."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.json_utils import atomic_json_dump


class TestAtomicJsonDump:
    def test_writes_valid_json(self, tmp_path):
        path = str(tmp_path / "data.json")
        atomic_json_dump({"key": "value"}, path)
        with open(path) as f:
            assert json.load(f) == {"key": "value"}

    def test_no_tmp_file_left(self, tmp_path):
        path = str(tmp_path / "data.json")
        atomic_json_dump({"a": 1}, path)
        assert not os.path.exists(path + ".tmp")

    def test_overwrites_existing(self, tmp_path):
        path = str(tmp_path / "data.json")
        atomic_json_dump({"v": 1}, path)
        atomic_json_dump({"v": 2}, path)
        with open(path) as f:
            assert json.load(f)["v"] == 2

    def test_original_preserved_on_error(self, tmp_path):
        import pytest
        path = str(tmp_path / "data.json")
        atomic_json_dump({"v": 1}, path)
        with pytest.raises(TypeError):
            atomic_json_dump({"v": object()}, path)
        with open(path) as f:
            assert json.load(f)["v"] == 1
        assert not os.path.exists(path + ".tmp")
