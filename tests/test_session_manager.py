import json
from unittest.mock import MagicMock, patch

from src.session_manager import save_cookies, load_cookies, check_session_valid


def test_save_cookies_writes_json(tmp_path):
    path = str(tmp_path / "cookies.json")
    cookies = [{"name": "sid", "value": "abc123", "domain": ".example.com"}]
    save_cookies(cookies, path)
    with open(path) as f:
        saved = json.load(f)
    assert saved == cookies


def test_load_cookies_returns_list(tmp_path):
    path = str(tmp_path / "cookies.json")
    data = [{"name": "sid", "value": "abc123"}]
    with open(path, "w") as f:
        json.dump(data, f)
    result = load_cookies(path)
    assert result == data


def test_load_cookies_returns_none_if_missing(tmp_path):
    path = str(tmp_path / "cookies.json")
    result = load_cookies(path)
    assert result is None


def test_load_cookies_returns_none_if_corrupted(tmp_path):
    path = str(tmp_path / "cookies.json")
    with open(path, "w") as f:
        f.write("not json {{{")
    result = load_cookies(path)
    assert result is None


def test_session_valid_returns_true_on_200():
    cookies = [{"name": "sid", "value": "abc"}]
    with patch("src.session_manager.requests") as mock_req:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://portal.tedronesans.k12.tr/dashboard"
        mock_req.Session.return_value.get.return_value = mock_resp
        assert check_session_valid(cookies) is True


def test_session_valid_returns_false_on_redirect_to_login():
    cookies = [{"name": "sid", "value": "abc"}]
    with patch("src.session_manager.requests") as mock_req:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://portal.tedronesans.k12.tr/login"
        mock_req.Session.return_value.get.return_value = mock_resp
        assert check_session_valid(cookies) is False
