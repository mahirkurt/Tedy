"""Tests for .env loader utility."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.env_loader import load_env


class TestLoadEnv:
    def test_loads_key_value(self, tmp_path, monkeypatch):
        monkeypatch.delenv("FOO", raising=False)
        monkeypatch.delenv("BAZ", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("FOO=bar\nBAZ=qux\n")
        load_env(str(env_file))
        assert os.environ.get("FOO") == "bar"
        assert os.environ.get("BAZ") == "qux"

    def test_skips_comments_and_blanks(self, tmp_path, monkeypatch):
        monkeypatch.delenv("KEY1", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\n\nKEY1=val1\n")
        load_env(str(env_file))
        assert os.environ.get("KEY1") == "val1"

    def test_handles_equals_in_value(self, tmp_path, monkeypatch):
        monkeypatch.delenv("API_KEY", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=abc=def=ghi\n")
        load_env(str(env_file))
        assert os.environ.get("API_KEY") == "abc=def=ghi"

    def test_missing_file_no_error(self):
        load_env("/nonexistent/.env")  # should not raise
