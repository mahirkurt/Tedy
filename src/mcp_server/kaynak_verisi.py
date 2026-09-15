"""Third-party free text wrapper (spec §6.3, made concrete in sub-project 2; plan K-P27).

Any tool that returns provider or source text puts it inside one top-level `kaynak_verisi`
object carrying this exact note, and never repeats it at the top level. Identifiers, URLs,
licenses and numeric metadata may stay outside.
"""
from __future__ import annotations

from typing import Any

from src.mcp_server.kapsam import KAYNAK_VERISI_NOT as KAYNAK_VERISI_NOTU

__all__ = ["KAYNAK_VERISI_NOTU", "sar"]


def sar(**alanlar: Any) -> dict[str, Any]:
    return {"not": KAYNAK_VERISI_NOTU, **alanlar}
