"""H6: output/sync.log rotation.

Cron appends to output/sync.log forever with no logrotate config, so it
grows unbounded (measured: ~3.3 KB/run * 96 runs/day). rotate_sync_log()
renames it to sync.log.1 once it crosses a size threshold, keeping exactly
one previous generation. All tests use tmp_path -- never the real output/.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.run_sync import rotate_sync_log


def test_rotates_when_over_threshold(tmp_path):
    log = tmp_path / "sync.log"
    log.write_bytes(b"x" * (21 * 1024 * 1024))

    rotate_sync_log(str(log), max_bytes=20 * 1024 * 1024)

    assert not log.exists()
    rotated = tmp_path / "sync.log.1"
    assert rotated.exists()
    assert rotated.stat().st_size == 21 * 1024 * 1024


def test_leaves_file_alone_when_under_threshold(tmp_path):
    log = tmp_path / "sync.log"
    log.write_bytes(b"x" * 100)

    rotate_sync_log(str(log), max_bytes=20 * 1024 * 1024)

    assert log.exists()
    assert log.stat().st_size == 100
    assert not (tmp_path / "sync.log.1").exists()


def test_exactly_at_threshold_is_not_rotated(tmp_path):
    log = tmp_path / "sync.log"
    log.write_bytes(b"x" * (20 * 1024 * 1024))

    rotate_sync_log(str(log), max_bytes=20 * 1024 * 1024)

    assert log.exists()
    assert not (tmp_path / "sync.log.1").exists()


def test_replaces_existing_previous_generation_rather_than_accumulating(tmp_path):
    log = tmp_path / "sync.log"
    log.write_bytes(b"new-generation-content" * 1_000_000)  # well over threshold
    old_gen = tmp_path / "sync.log.1"
    old_gen.write_bytes(b"stale-previous-generation")

    rotate_sync_log(str(log), max_bytes=20 * 1024 * 1024)

    assert not log.exists()
    assert old_gen.exists()
    # The old .1 content is gone -- replaced, not appended to.
    assert old_gen.read_bytes() != b"stale-previous-generation"
    assert old_gen.read_bytes().startswith(b"new-generation-content")


def test_missing_log_is_a_silent_no_op(tmp_path):
    missing = tmp_path / "sync.log"
    rotate_sync_log(str(missing), max_bytes=20 * 1024 * 1024)  # must not raise
    assert not missing.exists()
    assert not (tmp_path / "sync.log.1").exists()


def test_default_log_path_honours_module_level_output_dir(tmp_path, monkeypatch):
    """rotate_sync_log() with no args must resolve OUTPUT_DIR at call time.

    main() calls it with no arguments; other tests (e.g.
    test_year_rollover_sync.py) monkeypatch src.run_sync.OUTPUT_DIR to a
    tmp_path and then call main() directly, so a hard-coded/def-time-bound
    default here would silently fall through to the real output/ dir.
    """
    import src.run_sync as run_sync

    monkeypatch.setattr(run_sync, "OUTPUT_DIR", str(tmp_path))
    log = tmp_path / "sync.log"
    log.write_bytes(b"x" * (21 * 1024 * 1024))

    run_sync.rotate_sync_log()

    assert not log.exists()
    assert (tmp_path / "sync.log.1").exists()
