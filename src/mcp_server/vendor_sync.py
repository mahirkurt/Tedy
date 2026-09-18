"""Pin the edupedia authoring assets that ted-mcp owns and report drift from those pins.

Until edupedia 1.0.0 these files were copied from the CureoPrivate plugin. Since then this
directory is their single source (spec §5.2, §9.1): edit a file here, run --pin, and commit the
file together with PROVENANCE.json. PROVENANCE.json keeps where the files came from ("origin")
and the last copy ("source_commit", "synced_at") as history. The repository is private:
external readers (for example the egitim-kaynak pattern indexer) receive a pinned export of these files.

Usage:
    .venv/bin/python -m src.mcp_server.vendor_sync --check    # exit 1 when a file differs from its pin
    .venv/bin/python -m src.mcp_server.vendor_sync --pin      # re-pin after an intentional edit
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parent / "vendor"
PROVENANCE_NAME = "PROVENANCE.json"
AUTHORITY = "ted-mcp"
_SKIPPED_PARTS = frozenset({"__pycache__", ".pytest_cache"})


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_provenance(vendor: Path = VENDOR_DIR) -> dict:
    return json.loads((vendor / PROVENANCE_NAME).read_text(encoding="utf-8"))


def files_on_disk(vendor: Path = VENDOR_DIR) -> list[str]:
    """Every pinned-worthy file under vendor as sorted POSIX paths (no PROVENANCE.json, no caches)."""
    return sorted(
        path.relative_to(vendor).as_posix()
        for path in vendor.rglob("*")
        if path.is_file() and path.name != PROVENANCE_NAME and not _SKIPPED_PARTS & set(path.parts)
    )


def pin(vendor: Path = VENDOR_DIR, now: datetime | None = None) -> dict:
    """Rewrite the sha256 pins from the files on disk; every other field is kept as history."""
    provenance = load_provenance(vendor)
    if provenance.get("authority") != AUTHORITY:
        raise ValueError(f"{PROVENANCE_NAME}: authority must be {AUTHORITY!r} before pinning")
    provenance["files"] = {rel: _sha256(vendor / rel) for rel in files_on_disk(vendor)}
    provenance["pinned_at"] = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    (vendor / PROVENANCE_NAME).write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return provenance


def check(vendor: Path = VENDOR_DIR) -> list[str]:
    """Drift between the files on disk and their pins; an empty list means identical."""
    pinned = load_provenance(vendor)["files"]
    on_disk = files_on_disk(vendor)
    problems = [f"missing: {rel}" for rel in sorted(set(pinned) - set(on_disk))]
    problems += [f"unpinned: {rel}" for rel in on_disk if rel not in pinned]
    problems += [f"drift: {rel}" for rel in on_disk if rel in pinned and _sha256(vendor / rel) != pinned[rel]]
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report drift from the pins, change nothing")
    mode.add_argument("--pin", action="store_true", help="re-pin every file after an intentional edit")
    args = parser.parse_args(argv)
    if args.check:
        problems = check()
        for line in problems:
            print(line)
        return 1 if problems else 0
    provenance = pin()
    print(f"pinned {len(provenance['files'])} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
