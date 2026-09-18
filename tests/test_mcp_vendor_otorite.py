"""ted-mcp owns the edupedia authoring assets since edupedia 1.0.0 (spec §5.2, §9.1)."""
import hashlib
import inspect
import json
import re
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.mcp_server import vendor_sync

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_EXTRAS = (
    "assets/ibm-plex-OFL.txt",
    "assets/fonts-manifest.json",
    "assets/carbon-v11-authority.json",
    "scripts/embed_ibm_plex_fonts.py",
    "scripts/sync_carbon_tokens.py",
    "tests/conftest.py",
    "tests/test_gates.py",
)


def test_provenance_names_ted_mcp_as_authority_and_keeps_its_origin():
    prov = vendor_sync.load_provenance()
    assert prov["authority"] == "ted-mcp"
    assert prov["origin"]["repo"] == "https://github.com/mahirkurt/CureoPrivate"
    assert prov["origin"]["path"] == "plugins/edupedia/skills/carbon-edupedia"
    assert re.fullmatch(r"[0-9a-f]{40}", prov["origin"]["last_commit"])
    assert prov["origin"]["retired_in"] == "edupedia 1.0.0"
    assert "source_root" not in prov
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00", prov["pinned_at"])
    # History that edupedia_durum still reports.
    assert re.fullmatch(r"[0-9a-f]{40}", prov["source_commit"])
    assert prov["synced_at"]


def test_canonical_set_carries_font_license_template_tooling_and_gate_suite():
    files = vendor_sync.load_provenance()["files"]
    for rel in CANONICAL_EXTRAS:
        assert rel in files, rel
    assert len([r for r in files if r.startswith("tests/fixtures/") and r.endswith(".html")]) == 18
    assert len([r for r in files if r.startswith("references/")]) == 17
    assert len(files) == 45


def test_vendor_sync_reads_no_external_source():
    assert not hasattr(vendor_sync, "DEFAULT_SOURCE")
    assert not hasattr(vendor_sync, "sync")
    assert list(inspect.signature(vendor_sync.check).parameters) == ["vendor"]
    assert "/mnt/thunderbolt/workspaces/CureoPrivate" not in Path(vendor_sync.__file__).read_text(encoding="utf-8")


def test_live_vendor_dir_matches_its_pins():
    assert vendor_sync.files_on_disk()  # the surface exists before the no-drift claim
    assert vendor_sync.check() == []


def _mini_vendor(tmp_path: Path) -> Path:
    vendor = tmp_path / "vendor"
    (vendor / "references").mkdir(parents=True)
    (vendor / "SKILL.md").write_text("skill\n", encoding="utf-8")
    (vendor / "references" / "a.md").write_text("a\n", encoding="utf-8")
    (vendor / "PROVENANCE.json").write_text(json.dumps({
        "authority": "ted-mcp", "origin": {"repo": "r"}, "source_commit": "c", "synced_at": "s", "files": {},
    }), encoding="utf-8")
    return vendor


def test_pin_records_every_file_and_keeps_history(tmp_path):
    vendor = _mini_vendor(tmp_path)
    (vendor / "tests" / "__pycache__").mkdir(parents=True)
    (vendor / "tests" / "__pycache__" / "x.pyc").write_bytes(b"\0")
    prov = vendor_sync.pin(vendor, now=datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc))
    assert prov["files"] == {
        "SKILL.md": hashlib.sha256(b"skill\n").hexdigest(),
        "references/a.md": hashlib.sha256(b"a\n").hexdigest(),
    }
    assert prov["pinned_at"] == "2026-09-20T10:00:00+00:00"
    assert (prov["origin"], prov["source_commit"], prov["synced_at"]) == ({"repo": "r"}, "c", "s")
    assert json.loads((vendor / "PROVENANCE.json").read_text(encoding="utf-8")) == prov
    assert vendor_sync.check(vendor) == []


def test_check_reports_missing_unpinned_and_drift_in_stable_order(tmp_path):
    vendor = _mini_vendor(tmp_path)
    vendor_sync.pin(vendor)
    (vendor / "SKILL.md").unlink()
    (vendor / "references" / "z.md").write_text("new\n", encoding="utf-8")
    (vendor / "references" / "a.md").write_text("changed\n", encoding="utf-8")
    assert vendor_sync.check(vendor) == ["missing: SKILL.md", "unpinned: references/z.md", "drift: references/a.md"]


def test_pin_refuses_provenance_without_ted_mcp_authority(tmp_path):
    vendor = _mini_vendor(tmp_path)
    (vendor / "PROVENANCE.json").write_text(json.dumps({"files": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="authority"):
        vendor_sync.pin(vendor)


def test_cli_check_passes_and_a_bare_call_is_a_usage_error():
    ok = subprocess.run([sys.executable, "-m", "src.mcp_server.vendor_sync", "--check"],
                        cwd=ROOT, capture_output=True, text=True)
    assert (ok.returncode, ok.stdout) == (0, "")
    bare = subprocess.run([sys.executable, "-m", "src.mcp_server.vendor_sync"], cwd=ROOT, capture_output=True, text=True)
    assert bare.returncode == 2


def test_pytest_collects_the_vendored_gate_suite():
    cfg = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert cfg["tool"]["pytest"]["ini_options"]["testpaths"] == ["tests", "src/mcp_server/vendor/tests"]
