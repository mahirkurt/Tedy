"""A finished year is snapshotted before the next one overwrites it."""
import json
import os

from src.archive_year import archive_dir, archive_year_local

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
                 "manifest.json"):
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
