"""Load the vendored edupedia quality gates as a module and run them."""
from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any

VENDOR_DIR = Path(__file__).resolve().parent / "vendor"

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
    return len(GATE_FUNCTION_NAMES)


def run_gates(html: str) -> dict[str, dict[str, Any]]:
    """Run every gate; return {gate_id: {"status": PASS|WARN|FAIL|SKIPPED, ...}}."""
    vm = validator()
    result = vm.Result()
    for name in GATE_FUNCTION_NAMES:
        getattr(vm, name)(html, result)
    return result.to_json_gates()
