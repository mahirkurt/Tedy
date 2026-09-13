"""Vendored edupedia assets: provenance pins, template and gate loader."""
import hashlib
import json
from pathlib import Path

import pytest

from src.mcp_server import gates, vendor_sync

SOURCE = Path("/mnt/thunderbolt/workspaces/CureoPrivate/plugins/edupedia/skills/carbon-edupedia")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_provenance_lists_required_files():
    prov = vendor_sync.load_provenance()
    for rel in ("SKILL.md", "assets/module-template.html", "scripts/validate_module.py"):
        assert rel in prov["files"]
    refs = [r for r in prov["files"] if r.startswith("references/")]
    assert len(refs) == 17
    assert prov["source_root"]


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


def test_gate_loader_exposes_sixteen_gates():
    assert gates.gate_count() == 16
    vm = gates.validator()
    for name in gates.GATE_FUNCTION_NAMES:
        assert callable(getattr(vm, name)), name


def test_vendored_template_demo_has_no_failing_gate():
    html = (vendor_sync.VENDOR_DIR / "assets" / "module-template.html").read_text(encoding="utf-8")
    report = gates.run_gates(html)
    assert len(report) == 16
    assert not [g for g, v in report.items() if v["status"] == "FAIL"]
    assert sum(1 for v in report.values() if v["status"] == "PASS") >= 13


def test_run_gates_reports_failures_on_broken_html():
    report = gates.run_gates("<html><body><p>emoji 🎉</p></body></html>")
    assert any(v["status"] == "FAIL" for v in report.values())


def test_sync_then_check_round_trip(tmp_path):
    src = tmp_path / "src"
    for rel in ("SKILL.md", "assets/module-template.html", "scripts/validate_module.py", "references/a.md"):
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        (src / rel).write_text(f"content of {rel}\n", encoding="utf-8")
    vendor = tmp_path / "vendor"
    (vendor / "references").mkdir(parents=True)
    (vendor / "references" / "stale.md").write_text("old\n", encoding="utf-8")

    prov = vendor_sync.sync(src, vendor)

    assert set(prov["files"]) == {"SKILL.md", "assets/module-template.html", "scripts/validate_module.py", "references/a.md"}
    assert not (vendor / "references" / "stale.md").exists()
    assert vendor_sync.check(src, vendor) == []
    (src / "references" / "a.md").write_text("changed\n", encoding="utf-8")
    assert vendor_sync.check(src, vendor) == ["drift: references/a.md"]


@pytest.mark.skipif(not SOURCE.is_dir(), reason="CureoPrivate checkout not present")
def test_vendor_matches_live_plugin_source():
    assert vendor_sync.check(SOURCE) == []
