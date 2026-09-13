"""Copy edupedia authoring assets into src/mcp_server/vendor/ and pin their provenance.

ted-mcp is the runtime authority for the module template, the MODULE_DATA schema
reference and the quality gates (spec §5.2). This tool is the only way those files
change: it copies them from the CureoPrivate edupedia skill and writes PROVENANCE.json
(source commit + sha256 per file). tests/test_mcp_vendor.py pins the result.

Usage:
    .venv/bin/python -m src.mcp_server.vendor_sync            # sync from the default source
    .venv/bin/python -m src.mcp_server.vendor_sync --check    # exit 1 on drift
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parent / "vendor"
DEFAULT_SOURCE = Path("/mnt/thunderbolt/workspaces/CureoPrivate/plugins/edupedia/skills/carbon-edupedia")
FIXED_FILES = ("SKILL.md", "assets/module-template.html", "scripts/validate_module.py")
PROVENANCE_NAME = "PROVENANCE.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_files(source: Path) -> list[str]:
    refs = sorted(str(p.relative_to(source)) for p in (source / "references").glob("*.md"))
    rels = [*FIXED_FILES, *refs]
    missing = [rel for rel in rels if not (source / rel).is_file()]
    if missing:
        raise FileNotFoundError(f"missing in source {source}: {', '.join(missing)}")
    return rels


def _git_commit(source: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip() or None


def load_provenance(vendor: Path = VENDOR_DIR) -> dict:
    return json.loads((vendor / PROVENANCE_NAME).read_text(encoding="utf-8"))


def sync(source: Path, vendor: Path = VENDOR_DIR) -> dict:
    """Copy every source file, drop vendored files no longer in the source, write provenance."""
    rels = _source_files(source)
    wanted = set(rels)
    if vendor.is_dir():
        for path in sorted(vendor.rglob("*")):
            if not path.is_file() or path.name == PROVENANCE_NAME or "__pycache__" in path.parts:
                continue
            if str(path.relative_to(vendor)) not in wanted:
                path.unlink()
    files: dict[str, str] = {}
    for rel in rels:
        dst = vendor / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / rel, dst)
        files[rel] = _sha256(dst)
    provenance = {
        "source_root": str(source),
        "source_commit": _git_commit(source),
        "synced_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": files,
    }
    (vendor / PROVENANCE_NAME).write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return provenance


def check(source: Path, vendor: Path = VENDOR_DIR) -> list[str]:
    """Drift messages between source and vendor; an empty list means identical."""
    pinned = load_provenance(vendor)["files"]
    rels = _source_files(source)
    problems = [f"missing in vendor: {rel}" for rel in rels if rel not in pinned]
    problems += [f"removed upstream: {rel}" for rel in pinned if rel not in rels]
    problems += [
        f"drift: {rel}" for rel in rels if rel in pinned and _sha256(source / rel) != pinned[rel]
    ]
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--check", action="store_true", help="report drift, do not copy")
    args = parser.parse_args(argv)
    if args.check:
        problems = check(args.source)
        for line in problems:
            print(line)
        return 1 if problems else 0
    provenance = sync(args.source)
    print(f"vendored {len(provenance['files'])} files from {provenance['source_commit']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
