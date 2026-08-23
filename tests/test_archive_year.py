"""A finished year is snapshotted before the next one overwrites it."""
import json
import os

from src.archive_year import archive_dir, archive_year_local, UPLOAD_TRACKER_FILES

SCRAPED = {
    "scraped_at": "2026-08-22T10:00:08",
    "odevlerim": {"homework": {"rows": [{"Ders Adı": "Matematik"}]}},
    "gelisim_raporu": {"grades": [], "rubrics": [{"ders": "Müzik"}] * 24},
    "ders_icerikleri": {"Türkçe": [1, 2]},
    "takim_calismalari": {"activities": {"rows": []}},
    "ogep": {"sessions": {"rows": []}},
    "duyurular": {"announcements": []},
    "ders_programi": [],
    "takvim": [],
}


def _seed(out):
    os.makedirs(out, exist_ok=True)
    for name, payload in (
        ("scraped_data.json", SCRAPED),
        ("health.json", {"success": True}),
        ("classroom_sync.json", {"cw:1": {"last_hash": "abc"}}),
        ("eba_textbooks_uploaded.json", {"a": 1}),
        ("mebi_videos_uploaded.json", {}),
        ("uploaded_files.json", {"https://x/y.pdf": {"id": "f1"}}),
    ):
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            json.dump(payload, f)


def test_archive_copies_the_year_and_writes_a_manifest(tmp_path):
    out = str(tmp_path / "output")
    _seed(out)
    manifest = archive_year_local("2025-2026", out)

    d = archive_dir(out, "2025-2026")
    for name in ("scraped_data.json", "health.json", "classroom_sync.json",
                 "eba_textbooks_uploaded.json", "mebi_videos_uploaded.json",
                 "uploaded_files.json", "manifest.json"):
        assert os.path.exists(os.path.join(d, name)), name

    assert manifest["year"] == "2025-2026"
    assert manifest["grade"] is None
    assert manifest["source_scraped_at"] == "2026-08-22T10:00:08"
    assert manifest["drive_folder"] is None
    assert "archived_at" in manifest


def test_counts_come_from_the_shared_validator(tmp_path):
    out = str(tmp_path / "output")
    _seed(out)
    counts = archive_year_local("2025-2026", out)["counts"]
    assert counts["gelisim_raporu"] == 24   # grades + rubrics
    assert counts["odevlerim"] == 1
    assert counts["takim_calismalari"] == 0  # rows, not dict keys


def test_the_snapshot_is_a_copy_not_a_move(tmp_path):
    out = str(tmp_path / "output")
    _seed(out)
    archive_year_local("2025-2026", out)
    assert os.path.exists(os.path.join(out, "scraped_data.json"))


def test_archiving_twice_changes_nothing(tmp_path):
    out = str(tmp_path / "output")
    _seed(out)
    first = archive_year_local("2025-2026", out)

    # the live file moves on to the new year
    with open(os.path.join(out, "scraped_data.json"), "w", encoding="utf-8") as f:
        json.dump({"scraped_at": "2026-09-14T08:00:00"}, f)

    second = archive_year_local("2025-2026", out)
    assert second == first
    with open(os.path.join(archive_dir(out, "2025-2026"),
                           "scraped_data.json"), encoding="utf-8") as f:
        assert json.load(f)["scraped_at"] == "2026-08-22T10:00:08"


def test_missing_optional_files_are_skipped_not_fatal(tmp_path):
    out = str(tmp_path / "output")
    os.makedirs(out)
    with open(os.path.join(out, "scraped_data.json"), "w", encoding="utf-8") as f:
        json.dump(SCRAPED, f)
    manifest = archive_year_local("2025-2026", out)
    assert manifest["year"] == "2025-2026"
    assert not os.path.exists(
        os.path.join(archive_dir(out, "2025-2026"), "health.json"))


def test_sealing_resets_the_live_upload_trackers(tmp_path):
    """Trackers are per-year state, not permanent history. Once sealed,
    every uploader's `if key in uploaded: skip` must start clean, or a
    key that repeats across years (e.g. the same EBA textbook) is never
    (re-)uploaded into the new year's Drive folder."""
    out = str(tmp_path / "output")
    _seed(out)

    archive_year_local("2025-2026", out)

    # The live trackers are reset...
    with open(os.path.join(out, "eba_textbooks_uploaded.json"),
              encoding="utf-8") as f:
        assert json.load(f) == {}
    with open(os.path.join(out, "uploaded_files.json"), encoding="utf-8") as f:
        assert json.load(f) == {}

    # ...but the archived copy still holds the sealed year's real content.
    d = archive_dir(out, "2025-2026")
    with open(os.path.join(d, "eba_textbooks_uploaded.json"),
              encoding="utf-8") as f:
        assert json.load(f) == {"a": 1}
    with open(os.path.join(d, "uploaded_files.json"), encoding="utf-8") as f:
        assert json.load(f) == {"https://x/y.pdf": {"id": "f1"}}


def test_repeated_call_does_not_reset_trackers_again(tmp_path):
    """The reset must fire only on the genuine seal, never on the
    idempotent early-return - otherwise every later sync of the same
    (already-archived) year would wipe out the new year's own uploads."""
    out = str(tmp_path / "output")
    _seed(out)
    archive_year_local("2025-2026", out)

    # New content lands in the live tracker after the seal - real uploads
    # for the new academic year.
    new_content = {"https://x/new.pdf": {"id": "f2"}}
    with open(os.path.join(out, "uploaded_files.json"), "w",
              encoding="utf-8") as f:
        json.dump(new_content, f)

    # A second call for the SAME (already-sealed) year must take the
    # idempotent early-return and leave the live tracker alone.
    archive_year_local("2025-2026", out)

    with open(os.path.join(out, "uploaded_files.json"), encoding="utf-8") as f:
        assert json.load(f) == new_content


def test_upload_tracker_files_constant_matches_purge_google_data():
    """purge_google_data.py enumerates uploaded_files.json alongside the
    four *_uploaded.json trackers - the *_uploaded.json glob alone would
    miss it (see ARCHIVED_GLOBS)."""
    assert "uploaded_files.json" in UPLOAD_TRACKER_FILES
