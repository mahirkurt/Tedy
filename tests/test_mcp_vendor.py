"""Vendored edupedia assets: provenance pins, template and gate loader."""
import hashlib
import json
from pathlib import Path

import pytest

from src.mcp_server import gates, vendor_sync


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_provenance_lists_required_files():
    prov = vendor_sync.load_provenance()
    for rel in ("SKILL.md", "assets/module-template.html", "scripts/validate_module.py"):
        assert rel in prov["files"]
    refs = [r for r in prov["files"] if r.startswith("references/")]
    assert len(refs) == 18
    assert "references/tedy-integration.md" in refs


def test_every_vendored_file_matches_its_pinned_sha256():
    prov = vendor_sync.load_provenance()
    for rel, digest in prov["files"].items():
        path = vendor_sync.VENDOR_DIR / rel
        assert path.is_file(), rel
        assert _sha(path) == digest, rel


def test_no_unpinned_files_in_vendor_dir():
    prov = vendor_sync.load_provenance()
    on_disk = {
        str(p.relative_to(vendor_sync.VENDOR_DIR))
        for p in vendor_sync.VENDOR_DIR.rglob("*")
        if p.is_file() and p.name != "PROVENANCE.json" and "__pycache__" not in p.parts
    }
    assert on_disk == set(prov["files"])


def test_template_carries_module_data_placeholder():
    html = (vendor_sync.VENDOR_DIR / "assets" / "module-template.html").read_text(encoding="utf-8")
    assert "const MODULE_DATA = {" in html


def test_gate_loader_exposes_sixteen_vendored_and_two_ted_mcp_gates():
    assert len(gates.GATE_FUNCTION_NAMES) == 16
    assert gates.gate_count() == 18
    vm = gates.validator()
    for name in gates.GATE_FUNCTION_NAMES:
        assert callable(getattr(vm, name)), name


def test_ted_mcp_engine_demo_has_no_failing_gate():
    from src.mcp_server import sablon

    report = gates.run_gates(sablon.engine_template("https://tedy.online"))
    assert len(report) == 18
    assert not [g for g, v in report.items() if v["status"] == "FAIL"]


def test_raw_vendored_template_fails_only_the_bridge_gate():
    html = (vendor_sync.VENDOR_DIR / "assets" / "module-template.html").read_text(encoding="utf-8")
    report = gates.run_gates(html)
    assert sorted(g for g, v in report.items() if v["status"] == "FAIL") == ["G-BRIDGE"]


def test_run_gates_reports_failures_on_broken_html():
    report = gates.run_gates("<html><body><p>emoji 🎉</p></body></html>")
    assert any(v["status"] == "FAIL" for v in report.values())
