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

    def test_real_environment_wins_over_dotenv(self, tmp_path, monkeypatch):
        """A key already in os.environ must not be overwritten by .env (H1).

        `FOO=x python ...` and systemd `Environment=` must be able to
        override .env; a plain assignment in load_env silently defeats that.
        """
        monkeypatch.setenv("SHARED_KEY", "from-real-environment")
        env_file = tmp_path / ".env"
        env_file.write_text("SHARED_KEY=from-dotenv\n")
        load_env(str(env_file))
        assert os.environ["SHARED_KEY"] == "from-real-environment"

    def test_dotenv_only_key_is_still_loaded(self, tmp_path, monkeypatch):
        """A key with no real-environment counterpart still fills the gap."""
        monkeypatch.delenv("DOTENV_ONLY_KEY", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("DOTENV_ONLY_KEY=from-dotenv\n")
        load_env(str(env_file))
        assert os.environ["DOTENV_ONLY_KEY"] == "from-dotenv"
