"""Shared module identifiers and paths: slug rules, versions, drafts, realpath containment."""
import json
import os
import re
from pathlib import Path

import pytest

from src import module_store as ms

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_slug_regex_is_the_tedy_books_regex():
    source = (PROJECT_ROOT / "src" / "dashboard_api.py").read_text(encoding="utf-8")
    match = re.search(r'BOOK_SLUG_RE = re\.compile\(r"([^"]+)"\)', source)
    assert match and match.group(1) == ms.SLUG_RE.pattern


@pytest.mark.parametrize("slug,ok", [
    ("fen5-maddenin-halleri", True), ("a", True), ("a1-b2", True), ("a" * 60, True),
    ("", False), ("-a", False), ("a-", False), ("a--b", False), ("A", False), ("ş", False),
    ("../x", False), ("a/b", False), ("a" * 61, False), (None, False), (5, False),
])
def test_valid_slug(slug, ok):
    assert ms.valid_slug(slug) is ok


def test_reserved_slug_is_valid_but_not_publishable():
    assert ms.valid_slug("taslak") and not ms.publishable_slug("taslak")
    assert ms.publishable_slug("fen5-su")


@pytest.mark.parametrize("segment,expected", [
    ("v1", 1), ("v9999", 9999), ("v0", None), ("v01", None), ("v10000", None),
    ("1", None), ("v1a", None), ("V1", None), ("", None),
])
def test_parse_version_segment(segment, expected):
    assert ms.parse_version_segment(segment) == expected


@pytest.mark.parametrize("version,ok", [(1, True), (9999, True), (0, False), (10000, False), (True, False), ("1", False)])
def test_valid_version(version, ok):
    assert ms.valid_version(version) is ok


def test_taslak_id():
    assert ms.valid_taslak_id("0123456789abcdef")
    for bad in ("0123456789ABCDEF", "0123456789abcde", "../../etc/passwd", None):
        assert not ms.valid_taslak_id(bad)


def test_module_html_path_stays_under_modules_root(tmp_path):
    path = ms.module_html_path(tmp_path, "fen5-su", 2)
    assert path == Path(os.path.realpath(tmp_path)) / "modules" / "fen5-su" / "v2" / "index.html"
    assert ms.module_html_path(tmp_path, "../x", 1) is None
    assert ms.module_html_path(tmp_path, "fen5-su", 0) is None


def test_symlink_escape_is_refused(tmp_path):
    outside = tmp_path / "outside"
    (outside / "v1").mkdir(parents=True)
    (outside / "v1" / "index.html").write_text("x", encoding="utf-8")
    (tmp_path / "data" / "modules").mkdir(parents=True)
    os.symlink(outside, tmp_path / "data" / "modules" / "kacak")
    assert ms.module_html_path(tmp_path / "data", "kacak", 1) is None


def test_read_catalog_tolerates_missing_and_corrupt(tmp_path):
    assert ms.read_catalog(tmp_path) == []
    ms.catalog_path(tmp_path).parent.mkdir(parents=True)
    ms.catalog_path(tmp_path).write_text("{bozuk", encoding="utf-8")
    assert ms.read_catalog(tmp_path) == []
    ms.catalog_path(tmp_path).write_text(
        json.dumps({"surum": 1, "moduller": [{"slug": "a", "version": 1}, "x"]}), encoding="utf-8")
    assert ms.read_catalog(tmp_path) == [{"slug": "a", "version": 1}]
    assert ms.find_record(tmp_path, "a", 1) == {"slug": "a", "version": 1}
    assert ms.find_record(tmp_path, "a", 2) is None


def test_latest_active_keeps_highest_active_version_per_slug():
    rows = [
        {"slug": "a", "version": 1, "status": "active", "created_at": "2026-09-01"},
        {"slug": "a", "version": 2, "status": "active", "created_at": "2026-09-03"},
        {"slug": "a", "version": 3, "status": "removed", "created_at": "2026-09-04"},
        {"slug": "b", "version": 1, "status": "active", "created_at": "2026-09-02"},
        {"slug": "../c", "version": 1, "status": "active", "created_at": "2026-09-05"},
    ]
    assert [(r["slug"], r["version"]) for r in ms.latest_active(rows)] == [("a", 2), ("b", 1)]


def test_draft_read_and_html_path(tmp_path):
    folder = ms.drafts_root(tmp_path) / "0123456789abcdef"
    folder.mkdir(parents=True)
    (folder / "taslak.json").write_text(json.dumps({"taslak_id": "0123456789abcdef"}), encoding="utf-8")
    assert ms.read_draft(tmp_path, "0123456789abcdef")["taslak_id"] == "0123456789abcdef"
    assert ms.read_draft(tmp_path, "ffffffffffffffff") is None
    assert ms.draft_html_path(tmp_path, "0123456789abcdef").name == "index.html"
    assert ms.draft_html_path(tmp_path, "../x") is None


def test_fullmatch_rejects_newline_suffixed_slug():
    """Regression: regex $ matches before newline; fullmatch prevents it."""
    assert not ms.valid_slug("abc\n")


def test_fullmatch_rejects_newline_suffixed_taslak_id():
    """Regression: regex $ matches before newline; fullmatch prevents it."""
    assert not ms.valid_taslak_id("0123456789abcdef\n")


def test_fullmatch_rejects_newline_suffixed_version_segment():
    """Regression: regex $ matches before newline; fullmatch prevents it."""
    assert ms.parse_version_segment("v12\n") is None


def test_read_catalog_with_json_list(tmp_path):
    """MINOR: JSON is a list, not dict with 'moduller' key."""
    ms.catalog_path(tmp_path).parent.mkdir(parents=True)
    ms.catalog_path(tmp_path).write_text(json.dumps([{"slug": "a"}]), encoding="utf-8")
    assert ms.read_catalog(tmp_path) == []


def test_read_catalog_missing_moduller_key(tmp_path):
    """MINOR: dict without 'moduller' key."""
    ms.catalog_path(tmp_path).parent.mkdir(parents=True)
    ms.catalog_path(tmp_path).write_text(json.dumps({"other": "value"}), encoding="utf-8")
    assert ms.read_catalog(tmp_path) == []


def test_read_catalog_moduller_as_dict(tmp_path):
    """MINOR: 'moduller' is dict instead of list."""
    ms.catalog_path(tmp_path).parent.mkdir(parents=True)
    ms.catalog_path(tmp_path).write_text(json.dumps({"moduller": {"slug": "a"}}), encoding="utf-8")
    assert ms.read_catalog(tmp_path) == []


def test_read_catalog_moduller_as_non_dict(tmp_path):
    """MINOR: 'moduller' is list but contains non-dict items."""
    ms.catalog_path(tmp_path).parent.mkdir(parents=True)
    ms.catalog_path(tmp_path).write_text(
        json.dumps({"moduller": ["string", {"slug": "a"}, 42]}), encoding="utf-8")
    assert ms.read_catalog(tmp_path) == [{"slug": "a"}]


def test_read_catalog_with_status_distinguishes_missing_from_unreadable(tmp_path):
    assert ms.read_catalog_with_status(tmp_path) == (ms.CATALOG_MISSING, [])
    ms.catalog_path(tmp_path).parent.mkdir(parents=True)
    for bad in ("{bozuk", json.dumps([1, 2]), json.dumps({"surum": 1})):
        ms.catalog_path(tmp_path).write_text(bad, encoding="utf-8")
        assert ms.read_catalog_with_status(tmp_path) == (ms.CATALOG_UNREADABLE, [])
        assert ms.read_catalog(tmp_path) == []
    ms.catalog_path(tmp_path).write_text(json.dumps({"surum": 1, "moduller": [{"slug": "a"}, 3]}), encoding="utf-8")
    assert ms.read_catalog_with_status(tmp_path) == (ms.CATALOG_OK, [{"slug": "a"}])
