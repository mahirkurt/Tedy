"""Draft store: output/edupedia_drafts/<taslak_id>/{index.html, taslak.json}. Immutable; ted-mcp only."""
from __future__ import annotations

import hashlib
import secrets
from pathlib import Path
from typing import Any

from src import module_store as ms
from src.json_utils import atomic_json_dump


class DraftStore:
    def __init__(self, data_dir: Path | str) -> None:
        self.data_dir = Path(data_dir)

    def new_id(self) -> str:
        return secrets.token_hex(8)

    def save(self, taslak_id: str, html: str, record: dict[str, Any]) -> dict[str, Any]:
        folder = ms.draft_dir(self.data_dir, taslak_id)
        if folder is None:
            raise ValueError("gecersiz_taslak")
        folder.mkdir(parents=True, exist_ok=False)
        data = html.encode("utf-8")
        (folder / ms.MODULE_HTML).write_bytes(data)
        full = {**record, "taslak_id": taslak_id, "bayt": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        atomic_json_dump(full, str(folder / ms.DRAFT_RECORD))
        return full

    def load(self, taslak_id: str) -> dict[str, Any] | None:
        return ms.read_draft(self.data_dir, taslak_id)

    def html_bytes(self, taslak_id: str) -> bytes | None:
        path = ms.draft_html_path(self.data_dir, taslak_id)
        if path is None:
            return None
        try:
            return path.read_bytes()
        except OSError:
            return None
