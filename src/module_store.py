"""Module catalog identifiers and paths shared by ted-mcp (writer) and the dashboard (reader).

Stdlib only: the dashboard must not import src.mcp_server (it pulls in the MCP SDK) and
ted-mcp must not import src.dashboard_api (import side effects). The slug rule and the
realpath containment check mirror Tedy Books (spec §4.1).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SLUG_MAX = 60
RESERVED_SLUGS = frozenset({"taslak"})
TASLAK_ID_RE = re.compile(r"^[0-9a-f]{16}$")
VERSION_SEGMENT_RE = re.compile(r"^v([1-9][0-9]{0,3})$")
VERSION_MAX = 9999
CATALOG_NAME = "index.json"
MODULE_HTML = "index.html"
DRAFT_RECORD = "taslak.json"


def valid_slug(slug: Any) -> bool:
    return isinstance(slug, str) and len(slug) <= SLUG_MAX and bool(SLUG_RE.fullmatch(slug))


def publishable_slug(slug: Any) -> bool:
    return valid_slug(slug) and slug not in RESERVED_SLUGS


def valid_version(version: Any) -> bool:
    return isinstance(version, int) and not isinstance(version, bool) and 1 <= version <= VERSION_MAX


def parse_version_segment(segment: str) -> int | None:
    match = VERSION_SEGMENT_RE.fullmatch(segment or "")
    return int(match.group(1)) if match else None


def valid_taslak_id(taslak_id: Any) -> bool:
    return isinstance(taslak_id, str) and bool(TASLAK_ID_RE.fullmatch(taslak_id))


def modules_root(data_dir: Path | str) -> Path:
    return Path(data_dir) / "modules"


def drafts_root(data_dir: Path | str) -> Path:
    return Path(data_dir) / "edupedia_drafts"


def catalog_path(data_dir: Path | str) -> Path:
    return modules_root(data_dir) / CATALOG_NAME


def _contained(root: Path, candidate: Path) -> Path | None:
    """Resolved candidate if it lies strictly inside the resolved root, else None."""
    real_root = os.path.realpath(root)
    real = os.path.realpath(candidate)
    if real == real_root or os.path.commonpath([real, real_root]) != real_root:
        return None
    return Path(real)


def module_html_path(data_dir: Path | str, slug: Any, version: Any) -> Path | None:
    if not valid_slug(slug) or not valid_version(version):
        return None
    root = modules_root(data_dir)
    return _contained(root, root / slug / f"v{version}" / MODULE_HTML)


def draft_dir(data_dir: Path | str, taslak_id: Any) -> Path | None:
    if not valid_taslak_id(taslak_id):
        return None
    root = drafts_root(data_dir)
    return _contained(root, root / taslak_id)


def draft_html_path(data_dir: Path | str, taslak_id: Any) -> Path | None:
    folder = draft_dir(data_dir, taslak_id)
    if folder is None:
        return None
    return _contained(drafts_root(data_dir), folder / MODULE_HTML)


def read_catalog(data_dir: Path | str) -> list[dict[str, Any]]:
    try:
        data = json.loads(catalog_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = data.get("moduller") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def find_record(data_dir: Path | str, slug: Any, version: Any) -> dict[str, Any] | None:
    for row in read_catalog(data_dir):
        if row.get("slug") == slug and row.get("version") == version:
            return row
    return None


def latest_active(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per slug — its highest active version — newest first."""
    best: dict[str, dict[str, Any]] = {}
    for row in records:
        slug, version = row.get("slug"), row.get("version")
        if row.get("status") != "active" or not valid_slug(slug) or not valid_version(version):
            continue
        current = best.get(slug)
        if current is None or version > current["version"]:
            best[slug] = row
    return sorted(best.values(), key=lambda r: str(r.get("created_at") or ""), reverse=True)


def read_draft(data_dir: Path | str, taslak_id: Any) -> dict[str, Any] | None:
    folder = draft_dir(data_dir, taslak_id)
    if folder is None:
        return None
    try:
        data = json.loads((folder / DRAFT_RECORD).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None
