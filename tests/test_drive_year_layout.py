# tests/test_drive_year_layout.py
"""Drive is namespaced by academic year so two years never share a folder."""
import json
import os
import pytest

from src.sync_to_google import (
    UnknownAcademicYear, get_year_root, move_root_folders,
)
from src.archive_year import archive_year_drive


class FakeFiles:
    """Minimal stand-in for drive.files() with parent tracking."""

    def __init__(self, existing=None):
        self.store = dict(existing or {})   # id -> {name, parents}
        self._next = 100

    class _Req:
        def __init__(self, result):
            self._result = result

        def execute(self):
            return self._result

    def list(self, q="", **kw):
        name = q.split("name='", 1)[1].split("'", 1)[0] if "name='" in q else None
        parent = q.split("and '", 1)[1].split("' in parents", 1)[0] \
            if "' in parents" in q else None
        hits = [{"id": i, "parents": v.get("parents", [])}
                for i, v in self.store.items()
                if v["name"] == name
                and (parent in v.get("parents", []) if parent else
                     not v.get("parents"))]
        return self._Req({"files": hits})

    def create(self, body=None, **kw):
        self._next += 1
        fid = f"f{self._next}"
        self.store[fid] = {"name": body["name"],
                           "parents": body.get("parents", [])}
        return self._Req({"id": fid})

    def update(self, fileId=None, addParents=None, removeParents=None, **kw):
        self.store[fileId]["parents"] = [addParents]
        return self._Req({"id": fileId, "parents": [addParents]})


class FakeDrive:
    def __init__(self, existing=None):
        self._files = FakeFiles(existing)

    def files(self):
        return self._files


def test_year_root_is_tedy_slash_year():
    drive = FakeDrive()
    root = get_year_root(drive, "2026-2027")
    names = {v["name"] for v in drive._files.store.values()}
    assert names == {"TEDY", "2026-2027"}
    assert drive._files.store[root]["name"] == "2026-2027"


def test_year_root_is_reused_not_duplicated():
    drive = FakeDrive()
    assert get_year_root(drive, "2026-2027") == get_year_root(drive, "2026-2027")
    assert len(drive._files.store) == 2


def test_unknown_year_refuses_rather_than_misfiling(tmp_path, monkeypatch):
    """Better to skip an upload than to file it under the wrong year."""
    monkeypatch.setattr("src.sync_to_google.OUTPUT_DIR", str(tmp_path))
    with pytest.raises(UnknownAcademicYear):
        get_year_root(FakeDrive(), None)


def test_year_root_reads_stored_state_when_year_omitted(tmp_path, monkeypatch):
    monkeypatch.setattr("src.sync_to_google.OUTPUT_DIR", str(tmp_path))
    with open(tmp_path / "academic_year.json", "w", encoding="utf-8") as f:
        json.dump({"year": "2026-2027"}, f)
    drive = FakeDrive()
    root = get_year_root(drive, None)
    assert drive._files.store[root]["name"] == "2026-2027"


def test_move_reparents_existing_root_folders():
    drive = FakeDrive({
        "a": {"name": "Ödevler", "parents": []},
        "b": {"name": "Ders Kitapları", "parents": []},
    })
    parent = get_year_root(drive, "2025-2026")
    moved = move_root_folders(drive, ["Ödevler", "Ders Kitapları", "Yok"], parent)
    assert sorted(moved) == ["a", "b"]
    assert drive._files.store["a"]["parents"] == [parent]
    assert drive._files.store["b"]["parents"] == [parent]


def test_drive_archive_records_the_folder_id(tmp_path):
    out = str(tmp_path / "output")
    os.makedirs(out)
    with open(os.path.join(out, "scraped_data.json"), "w", encoding="utf-8") as f:
        json.dump({"scraped_at": "x"}, f)
    drive = FakeDrive({"a": {"name": "Ödevler", "parents": []}})
    manifest = archive_year_drive("2025-2026", out, drive)
    assert manifest["drive_folder"] is not None
    assert drive._files.store["a"]["parents"] == [manifest["drive_folder"]]


def test_drive_failure_still_leaves_a_local_archive(tmp_path):
    class Broken(FakeDrive):
        def files(self):
            raise RuntimeError("drive down")

    out = str(tmp_path / "output")
    os.makedirs(out)
    with open(os.path.join(out, "scraped_data.json"), "w", encoding="utf-8") as f:
        json.dump({"scraped_at": "x"}, f)
    manifest = archive_year_drive("2025-2026", out, Broken())
    assert manifest["year"] == "2025-2026"
    assert manifest["drive_folder"] is None
