"""Per-run scratch record: output/edupedia_runs/<run_id>/ (git-ignored, never shipped to the fleet)."""
from __future__ import annotations

import json
import os
import re
import secrets
from pathlib import Path
from typing import Any

from src.json_utils import atomic_json_dump

# Anchored with \Z (not $): $ matches just before a trailing "\n", which would let
# "abcdef012345\n" slip past the "12 lowercase hex" run_id invariant.
RUN_ID_RE = re.compile(r"^[0-9a-f]{12}\Z")
_PAGE_RE = re.compile(r"^(\d+)-(\d+)\.txt\Z")


class RunStore:
    def __init__(self, data_dir: Path) -> None:
        self.root = Path(data_dir) / "edupedia_runs"

    def new_id(self) -> str:
        return secrets.token_hex(6)

    def _dir(self, run_id: str) -> Path:
        if not RUN_ID_RE.match(run_id or ""):
            raise ValueError("invalid run_id")
        return self.root / run_id

    def save(self, run_id: str, record: dict[str, Any]) -> None:
        atomic_json_dump(record, str(self._dir(run_id) / "run.json"))

    def load(self, run_id: str) -> dict[str, Any] | None:
        try:
            path = self._dir(run_id) / "run.json"
        except ValueError:
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def save_page(self, run_id: str, document_id: int, page_no: int, text: str) -> None:
        # Atomic like save(): write a temp file in the same directory, then os.replace over
        # the target, so a crash or concurrent read mid-write never sees a truncated page.
        pages = self._dir(run_id) / "pages"
        pages.mkdir(parents=True, exist_ok=True)
        target = pages / f"{int(document_id)}-{int(page_no)}.txt"
        tmp = pages / f"{int(document_id)}-{int(page_no)}.txt.tmp"
        try:
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, target)
        except BaseException:
            try:
                tmp.unlink()
            except OSError:
                pass
            raise

    def pages(self, run_id: str) -> list[dict[str, Any]]:
        try:
            folder = self._dir(run_id) / "pages"
        except ValueError:
            return []
        rows = []
        for path in folder.glob("*.txt") if folder.is_dir() else []:
            m = _PAGE_RE.match(path.name)
            if m:
                rows.append({"document_id": int(m.group(1)), "page_no": int(m.group(2)),
                             "text": path.read_text(encoding="utf-8")})
        return sorted(rows, key=lambda r: (r["document_id"], r["page_no"]))
