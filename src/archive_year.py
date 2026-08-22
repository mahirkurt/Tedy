"""Snapshot a finished academic year before the next one overwrites it."""
import glob
import json
import os
import shutil
from datetime import datetime

from src.data_validator import SECTION_RULES, _count_section
from src.json_utils import atomic_json_dump

# Copied verbatim into the archive. Missing files are skipped.
ARCHIVED_FILES = ("scraped_data.json", "health.json", "classroom_sync.json")
ARCHIVED_GLOBS = ("*_uploaded.json",)


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

    names = list(ARCHIVED_FILES)
    for pattern in ARCHIVED_GLOBS:
        names += [os.path.basename(p)
                  for p in glob.glob(os.path.join(output_dir, pattern))]

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
        "drive_folder": None,
        "source_scraped_at": scraped.get("scraped_at", ""),
    }
    # written last: an interrupted archive is retried, never half-trusted
    atomic_json_dump(manifest, manifest_path)
    return manifest
