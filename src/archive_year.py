"""Snapshot a finished academic year before the next one overwrites it."""
import glob
import json
import os
import shutil
from datetime import datetime

from src.data_validator import SECTION_RULES, _count_section
from src.json_utils import atomic_json_dump

# Copied verbatim into the archive. Missing files are skipped.
ARCHIVED_FILES = ("scraped_data.json", "health.json")
ARCHIVED_GLOBS = ("*_uploaded.json",)

# Idempotent-download tracker files: {key: {...}} dicts every downloader
# consults as `if key in uploaded: skip`. They are per-year state, not
# permanent history — once a year's archive is sealed they must reset to
# {}, or every key that repeats across years is silently never
# re-downloaded into content/<year-equivalent> paths.
# uploaded_files.json (the homework-attachments tracker) doesn't match the
# *_uploaded.json glob — it's the plural "uploaded_files", not a
# "<thing>_uploaded" name — so it is listed explicitly.
UPLOAD_TRACKER_FILES = ("uploaded_files.json",)


def archive_dir(output_dir: str, year: str) -> str:
    return os.path.join(output_dir, "archive", year)


def archive_year_local(year: str, output_dir: str) -> dict:
    """Copy the year's JSON into output/archive/<year>/ and describe it.

    Idempotent: once manifest.json exists the archive is sealed and this
    returns it untouched, so a repeated sync cannot overwrite a good
    snapshot with new-year data.
    """
    target = archive_dir(output_dir, year)
    manifest_path = os.path.join(target, "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            return json.load(f)

    os.makedirs(target, exist_ok=True)

    tracker_names = list(UPLOAD_TRACKER_FILES)
    for pattern in ARCHIVED_GLOBS:
        tracker_names += [os.path.basename(p)
                          for p in glob.glob(os.path.join(output_dir, pattern))]

    names = list(ARCHIVED_FILES) + tracker_names

    for name in names:
        src_path = os.path.join(output_dir, name)
        if os.path.exists(src_path):
            shutil.copy2(src_path, os.path.join(target, name))

    scraped = {}
    scraped_path = os.path.join(target, "scraped_data.json")
    if os.path.exists(scraped_path):
        try:
            with open(scraped_path, encoding="utf-8") as f:
                scraped = json.load(f)
        except (json.JSONDecodeError, OSError):
            scraped = {}

    manifest = {
        "year": year,
        "grade": None,
        "archived_at": datetime.now().isoformat(),
        "counts": {s: _count_section(s, scraped) for s in SECTION_RULES},
        "source_scraped_at": scraped.get("scraped_at", ""),
    }
    # written last: an interrupted archive is retried, never half-trusted
    atomic_json_dump(manifest, manifest_path)

    # Seal complete — only reached once, never on the idempotent
    # early-return above. Reset the live trackers so the new year
    # re-downloads its own content instead of skipping keys that repeat
    # across years.
    for name in tracker_names:
        atomic_json_dump({}, os.path.join(output_dir, name))

    return manifest
