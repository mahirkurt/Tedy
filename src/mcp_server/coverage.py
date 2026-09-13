"""Coverage manifest: which fleet server answered, came back empty, degraded or was skipped.

Empty is not evidence of absence (fleet no-fabrication invariant); every retrieval tool
returns this manifest so the model can say what it did not see.
"""
from __future__ import annotations


class Coverage:
    def __init__(self) -> None:
        self._rows: dict[str, str] = {}

    def hit(self, server: str) -> None:
        self._rows[server] = "hit"

    def empty(self, server: str) -> None:
        self._rows[server] = "empty"

    def degraded(self, server: str, reason: str) -> None:
        self._rows[server] = f"degraded:{reason}"

    def skipped(self, server: str, reason: str) -> None:
        self._rows[server] = f"skipped:{reason}"

    def as_dict(self) -> dict[str, str]:
        return dict(self._rows)
