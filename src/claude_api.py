"""Claude for the dashboard's single-request model calls.

The homework-photo extraction and the book-translation fallback make one
request each; the assistant, which runs a tool loop, has its own client
(assistant_core.ClaudeClient). All three moved off Gemini on 2026-09-24: the
Gemini API terms require users to be 18 or older and forbid services "likely
to be accessed by individuals under the age of 18", and TEDY is used by a
12-year-old.
"""
from __future__ import annotations

import os
import re
from typing import Any

VARSAYILAN_MODEL = "claude-sonnet-5"


class ClaudeYapilandirilmamis(RuntimeError):
    """ANTHROPIC_API_KEY is not set: the call cannot be made at all."""


def model_kimligi(ortam_degiskeni: str = "") -> str:
    """The model for one call site: its own override, else the default."""
    if ortam_degiskeni:
        deger = os.environ.get(ortam_degiskeni, "").strip()
        if deger:
            return deger
    return VARSAYILAN_MODEL


def basliklar() -> dict[str, Any]:
    """Client construction extras: the workspace header, when one is set.

    First live call, 2026-09-24: 400 "This API key is not scoped to a
    workspace, so this request must include the anthropic-workspace-id
    header". A key created inside a workspace needs nothing; an
    organisation-level key needs ANTHROPIC_WORKSPACE_ID (wrkspc_…)."""
    ws = os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip()
    return {"default_headers": {"anthropic-workspace-id": ws}} if ws else {}


def istemci(timeout: float, max_retries: int = 1) -> Any:
    anahtar = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not anahtar:
        raise ClaudeYapilandirilmamis("ANTHROPIC_API_KEY ayarlı değil")
    import anthropic  # lazy: most requests never need it
    return anthropic.Anthropic(api_key=anahtar, timeout=timeout, max_retries=max_retries,
                               **basliklar())


def okunur_ad(model: str) -> str:
    """"claude-sonnet-5" -> "Claude Sonnet 5"; anything else unchanged."""
    m = re.match(r"^claude-([a-z]+)-(\d+)(?:-(\d+))?$", model or "")
    if not m:
        return model
    return f"Claude {m.group(1).capitalize()} {m.group(2)}" + (f".{m.group(3)}" if m.group(3) else "")


def metin(yanit: Any) -> str:
    """The text of a response, thinking blocks and all else left out."""
    return "".join(getattr(b, "text", "") for b in (getattr(yanit, "content", None) or [])
                   if getattr(b, "type", "") == "text").strip()
