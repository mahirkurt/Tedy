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
        # Real Drive only filters by parent when the query names one -
        # including the "root" alias, which move_root_folders and the
        # TEDY-root lookup both now pass deliberately so a folder of the
        # right name is matched only at Drive's top level, never at any
        # depth (e.g. nested inside a previous year's archive, or shared
        # in from another user under an unrelated parent).
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


def test_tedy_root_ignores_a_same_named_folder_elsewhere():
    """A folder named TEDY living anywhere other than Drive root - shared
    in from another user, or nested under some unrelated parent - must not
    be mistaken for the real TEDY root. Finding-1's second half: the
    unparented _get_or_create_folder(drive, DRIVE_ROOT_NAME) lookup used to
    match a folder of that name at ANY depth in the account."""
    drive = FakeDrive({
        "decoy": {"name": "TEDY", "parents": ["someone_elses_folder"]},
    })
    root = get_year_root(drive, "2026-2027")

    tedy_entries = {i: v for i, v in drive._files.store.items()
                    if v["name"] == "TEDY"}
    assert "decoy" in tedy_entries
    # a second, genuine TEDY was created at Drive root - the decoy was
    # never reused as the root
    assert len(tedy_entries) == 2
    real_tedy_id = next(i for i in tedy_entries if i != "decoy")
    assert tedy_entries[real_tedy_id]["parents"] == ["root"]
    assert drive._files.store[root]["parents"] == [real_tedy_id]


def test_unknown_year_refuses_rather_than_misfiling(tmp_path, monkeypatch):
    """Better to skip an upload than to file it under the wrong year."""
    monkeypatch.setattr("src.sync_to_google.OUTPUT_DIR", str(tmp_path))
    with pytest.raises(UnknownAcademicYear):
        get_year_root(FakeDrive(), None)


@pytest.mark.parametrize("bad_year", ["2025", "2025-2026-2027", "not-a-year", ""])
def test_malformed_year_refuses_rather_than_becoming_a_folder_name(bad_year):
    """run_sync.py already refuses to build a filesystem path from a stored
    year that isn't YYYY-YYYY (see _YEAR_RE there) - get_year_root must
    apply the same guard before a malformed value becomes a Drive folder
    name."""
    with pytest.raises(UnknownAcademicYear):
        get_year_root(FakeDrive(), bad_year)


def test_year_root_reads_stored_state_when_year_omitted(tmp_path, monkeypatch):
    monkeypatch.setattr("src.sync_to_google.OUTPUT_DIR", str(tmp_path))
    with open(tmp_path / "academic_year.json", "w", encoding="utf-8") as f:
        json.dump({"year": "2026-2027"}, f)
    drive = FakeDrive()
    root = get_year_root(drive, None)
    assert drive._files.store[root]["name"] == "2026-2027"


def test_move_reparents_existing_root_folders():
    drive = FakeDrive({
        "a": {"name": "Ödevler", "parents": ["root"]},
        "b": {"name": "Ders Kitapları", "parents": ["root"]},
    })
    parent = get_year_root(drive, "2025-2026")
    moved = move_root_folders(drive, ["Ödevler", "Ders Kitapları", "Yok"], parent)
    assert sorted(moved) == ["a", "b"]
    assert drive._files.store["a"]["parents"] == [parent]
    assert drive._files.store["b"]["parents"] == [parent]


def test_move_removes_the_root_parent_not_just_adds_the_new_one():
    """A moved folder must end up ONLY under its new year parent - the
    root parent must be dropped, not left alongside the new one."""
    drive = FakeDrive({
        "a": {"name": "Ödevler", "parents": ["root"]},
    })
    parent = get_year_root(drive, "2026-2027")
    moved = move_root_folders(drive, ["Ödevler"], parent)
    assert moved == ["a"]
    assert drive._files.store["a"]["parents"] == [parent]


def test_folder_nested_inside_a_previous_years_archive_is_not_moved():
    """Finding-1 regression: without root-scoping in the query, this exact
    lookup matches a folder of this name at ANY depth - including one that
    already lives inside a previous year's archive. A second rollover would
    then find last year's already-migrated 'Ödevler' folder and re-parent
    it straight into the new year, emptying the old archive and merging two
    years' content: the exact mixing year-namespacing exists to prevent.
    Once a folder is nested under TEDY/<year>/ (not Drive root), it must
    never be matched by move_root_folders again."""
    drive = FakeDrive({
        "a": {"name": "Ödevler", "parents": ["last_years_TEDY_2025-2026_id"]},
    })
    parent = get_year_root(drive, "2026-2027")
    moved = move_root_folders(drive, ["Ödevler"], parent)
    assert moved == []
    assert drive._files.store["a"]["parents"] == ["last_years_TEDY_2025-2026_id"]


def test_move_ignores_an_unrelated_folder_of_the_same_name():
    """A same-named folder that lives anywhere other than Drive root (e.g.
    one a colleague shared in) must not be swept up either."""
    drive = FakeDrive({
        "a": {"name": "Ödevler", "parents": ["someone_elses_folder"]},
    })
    parent = get_year_root(drive, "2026-2027")
    moved = move_root_folders(drive, ["Ödevler"], parent)
    assert moved == []
    assert drive._files.store["a"]["parents"] == ["someone_elses_folder"]


def test_move_is_idempotent_no_redundant_update_on_second_call():
    """Once a folder already sits under parent_id, a second pass must
    recognize that (via the root-scoped lookup no longer finding it there)
    and skip it - not reissue an update() call."""
    drive = FakeDrive({
        "a": {"name": "Ödevler", "parents": ["root"]},
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
    drive = FakeDrive({"a": {"name": "Ödevler", "parents": ["root"]}})
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
