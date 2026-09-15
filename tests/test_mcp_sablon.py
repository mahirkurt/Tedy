"""ted-mcp engine = vendored template + anchored patches (bridge, asset rendering, slots)."""
import hashlib
import re
import shutil
import subprocess

import pytest

from src.mcp_server import gates, sablon, vendor_sync

ORIGIN = "https://tedy.online"


@pytest.fixture(autouse=True)
def _fresh_cache():
    sablon._patched_with_token.cache_clear()
    yield
    sablon._patched_with_token.cache_clear()


def test_every_anchor_occurs_exactly_once_in_the_vendored_template():
    text = sablon.TEMPLATE_PATH.read_text(encoding="utf-8")
    for name, anchor, _insertion, _position in sablon.PATCHES:
        assert text.count(anchor) == 1, name
    assert text.count(sablon.MODULE_DATA_START) == 1
    assert text.count(sablon.ENGINE_MARKER) == 1
    assert "postMessage" not in text


def test_vendored_file_stays_byte_identical():
    pinned = vendor_sync.load_provenance()["files"]["assets/module-template.html"]
    sablon.engine_template(ORIGIN)
    assert hashlib.sha256(sablon.TEMPLATE_PATH.read_bytes()).hexdigest() == pinned


def test_patched_engine_carries_bridge_assets_and_slots():
    html = sablon.engine_template(ORIGIN)
    assert html.count("window.parent.postMessage(msg, EDUPEDIA_PARENT_ORIGIN)") == 1
    assert 'const EDUPEDIA_PARENT_ORIGIN = "https://tedy.online";' in html
    assert sablon.ORIGIN_TOKEN not in html
    assert html.count(sablon.ASSETS_SLOT) == 1 and html.count(sablon.ATTRIB_SLOT) == 1
    assert html.index(sablon.ASSETS_SLOT) < html.index("<script>")
    assert "EDUPEDIA_BRIDGE.answer(s.id, oi, correct, tried.n);" in html
    assert "EDUPEDIA_BRIDGE.segmentComplete(segs[state.idx].id);" in html
    assert "EDUPEDIA_BRIDGE.moduleComplete();" in html
    assert "\n  init();\n  EDUPEDIA_BRIDGE.ready();\n" in html
    assert "html+=edupediaAssetFigure(s.visual);" in html
    assert "html+=edupediaAudio(s.audio);" in html
    assert not re.search(r"postMessage\([^)]*[\"']\*[\"']", html)


@pytest.mark.parametrize("origin", ["http://127.0.0.1:8286", "https://tedy.online"])
def test_origin_is_embedded_as_a_json_string(origin):
    assert f'const EDUPEDIA_PARENT_ORIGIN = "{origin}";' in sablon.engine_template(origin)


@pytest.mark.parametrize("bad", ["", "*", "https://tedy.online/", "javascript:alert(1)",
                                 'https://tedy.online";alert(1)//', "ftp://tedy.online", "https://tedy.online\n"])
def test_invalid_origin_is_refused(bad):
    with pytest.raises(ValueError):
        sablon.engine_template(bad)


def test_drifted_template_fails_loudly(tmp_path, monkeypatch):
    text = sablon.TEMPLATE_PATH.read_text(encoding="utf-8")
    drifted = tmp_path / "module-template.html"
    drifted.write_text(text.replace("\n  init();\n", "\n  init(); /* moved */\n", 1), encoding="utf-8")
    monkeypatch.setattr(sablon, "TEMPLATE_PATH", drifted)
    with pytest.raises(sablon.TemplateDriftError, match="ready"):
        sablon.engine_template(ORIGIN)


def test_patched_demo_has_no_failing_gate():
    report = gates.run_gates(sablon.engine_template(ORIGIN))
    assert not [g for g, v in report.items() if v["status"] == "FAIL"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node yok")
def test_patched_engine_script_is_valid_javascript(tmp_path):
    html = sablon.engine_template(ORIGIN)
    script = html[html.index("<script>") + len("<script>"):html.index("</script>")]
    path = tmp_path / "engine.js"
    path.write_text(script, encoding="utf-8")
    result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
