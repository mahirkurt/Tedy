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
        self.update_calls = 0

    class _Req:
        def __init__(self, result):
            self._result = result

        def execute(self):
            return self._result

    def list(self, q="", **kw):
        name = q.split("name='", 1)[1].split("'", 1)[0] if "name='" in q else None
        parent = q.split("and '", 1)[1].split("' in parents", 1)[0] \
            if "' in parents" in q else None
        # Real Drive only filters by parent when the query names one. A
        # parent-agnostic query (as move_root_folders deliberately issues)
        # must match a folder by name Drive-wide, regardless of its current
        # parents - not just folders that happen to have none.
        hits = [{"id": i, "parents": v.get("parents", [])}
                for i, v in self.store.items()
                if v["name"] == name
                and (parent in (v.get("parents") or []) if parent else True)]
        return self._Req({"files": hits})

    def create(self, body=None, **kw):
        self._next += 1
        fid = f"f{self._next}"
        self.store[fid] = {"name": body["name"],
                           "parents": body.get("parents", [])}
        return self._Req({"id": fid})

    def update(self, fileId=None, addParents=None, removeParents=None, **kw):
        # Real Drive's addParents/removeParents are comma-separated id lists
        # applied as a union/subtract against the existing parents - not a
        # wholesale replacement. Modelling that is what lets a missing or
        # wrong removeParents show up as a folder left with two parents.
        self.update_calls += 1
        parents = set(self.store[fileId].get("parents") or [])
        remove = {p for p in (removeParents or "").split(",") if p}
        add = {p for p in (addParents or "").split(",") if p}
        parents = sorted((parents - remove) | add)
        self.store[fileId]["parents"] = parents
        return self._Req({"id": fileId, "parents": parents})


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


def test_move_removes_the_old_parent_not_just_adds_the_new_one():
    """Two years must never share a folder: moving a folder that already
    belongs to a different parent (e.g. last year's TEDY/<year>/) must drop
    that old parent, not just add the new one alongside it."""
    drive = FakeDrive({
        "a": {"name": "Ödevler", "parents": ["last_years_parent"]},
    })
    parent = get_year_root(drive, "2026-2027")
    moved = move_root_folders(drive, ["Ödevler"], parent)
    assert moved == ["a"]
    assert drive._files.store["a"]["parents"] == [parent]


def test_move_is_idempotent_no_redundant_update_on_second_call():
    """Once a folder already sits under parent_id, a second pass must
    recognize that (via the parent-agnostic lookup) and skip it - not
    reissue an update() call."""
    drive = FakeDrive({
        "a": {"name": "Ödevler", "parents": []},
    })
    parent = get_year_root(drive, "2025-2026")

    first = move_root_folders(drive, ["Ödevler"], parent)
    assert first == ["a"]
    assert drive._files.update_calls == 1

    second = move_root_folders(drive, ["Ödevler"], parent)
    assert second == []
    assert drive._files.update_calls == 1


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


def test_no_content_root_is_created_at_drive_root():
    """Every content root must hang off TEDY/<year>/, never Drive root."""
    import inspect

    import src.scrape_eba_textbooks as eba
    import src.scrape_mebi_videos as mebi
    import src.scrape_sebitv as sebitv
    import src.scrape_sebitv_interactive as sebitv_i
    import src.sync_to_google as stg

    roots = [
        (stg, '"Ödevler"'),
        (eba, '"Ders Kitapları"'),
        (mebi, '"MEBI Videolar"'),
        (sebitv, '"SEBİTV Videolar"'),
        (sebitv_i, '"SEBİTV Etkileşimli"'),
        (sebitv_i, '"SEBİTV Soru Bankaları"'),
    ]
    for module, literal in roots:
        src = inspect.getsource(module)
        idx = src.find(literal)
        assert idx != -1, f"{module.__name__}: {literal} not found"
        window = src[max(0, idx - 300): idx + 200]
        assert ("parent_id" in window and
                ("get_year_root" in window or "year_root" in window)), (
            f"{module.__name__}: {literal} root folder is not year-scoped")
