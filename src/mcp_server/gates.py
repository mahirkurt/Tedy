"""Load the vendored edupedia quality gates as a module and run them."""
from __future__ import annotations

import importlib.util
import re
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any

VENDOR_DIR = Path(__file__).resolve().parent / "vendor"

from src.mcp_server import gates_ek

EXTRA_GATES = ("G-BRIDGE", "G-ATTRIB")

# Order mirrors the retired edupedia_site runner (_GATE_FUNCS), 16 gates.
GATE_FUNCTION_NAMES = (
    "gate_emoji",
    "gate_carbon",
    "gate_a11y",
    "gate_interact",
    "gate_selfcontained",
    "gate_contrast",
    "gate_wellbeing",
    "gate_voice",
    "gate_svg",
    "gate_audio",
    "gate_token_authority",
    "gate_curriculum",
    "gate_verify",
    "gate_flow",
    "gate_carbon_grid",
    "gate_exam",
)


@lru_cache(maxsize=1)
def validator() -> ModuleType:
    path = VENDOR_DIR / "scripts" / "validate_module.py"
    spec = importlib.util.spec_from_file_location("ted_mcp_vendor_validate_module", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load vendored validator at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def gate_count() -> int:
    return len(GATE_FUNCTION_NAMES) + len(EXTRA_GATES)


def run_gates(html: str) -> dict[str, dict[str, Any]]:
    """Run the 16 vendored gates and ted-mcp's G-BRIDGE and G-ATTRIB; {gate_id: {"status", ...}}."""
    vm = validator()
    result = vm.Result()
    for name in GATE_FUNCTION_NAMES:
        getattr(vm, name)(html, result)
    gates_ek.gate_bridge(html, result)
    gates_ek.gate_attrib(html, result)
    return result.to_json_gates()


def voice_pattern() -> re.Pattern[str]:
    """The vendored G-VOICE deixis pattern; the compiler refuses attribution lines that match it."""
    return validator().VOICE_DEIXIS_RE
