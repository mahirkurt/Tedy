"""G-BRIDGE and G-ATTRIB: detect a missing, loosened or foreign bridge; missing attributions."""
import html as html_lib
import json

import pytest

from src.mcp_server import gates, gates_ek, sablon

ENGINE = sablon.engine_template("https://tedy.online")


def _run(fn, html):
    result = gates.validator().Result()
    fn(html, result)
    return result.to_json_gates()


def test_bridge_passes_on_the_patched_engine():
    assert _run(gates_ek.gate_bridge, ENGINE)["G-BRIDGE"]["status"] == "PASS"


def test_raw_vendored_template_has_no_bridge():
    raw = sablon.TEMPLATE_PATH.read_text(encoding="utf-8")
    report = _run(gates_ek.gate_bridge, raw)["G-BRIDGE"]
    assert report["status"] == "FAIL" and "köprüsü yok" in report["detail"]


@pytest.mark.parametrize("old,new,fragment", [
    ("window.parent.postMessage(msg, EDUPEDIA_PARENT_ORIGIN)", "window.top.postMessage(msg, EDUPEDIA_PARENT_ORIGIN)", "window.top"),
    ("window.parent.postMessage(msg, EDUPEDIA_PARENT_ORIGIN)", 'window.parent.postMessage(msg, "*")', "'*'"),
    ("if(e.source!==window.parent) return;", "", "kaynağını"),
    ("if(e.origin!==EDUPEDIA_PARENT_ORIGIN) return;", "", "origin'i denetlemiyor"),
    ("const embedded = window.parent !== window;", "const embedded = true;", "bağımsız"),
    ('d.type !== "edupedia:restore"', 'd.type !== "edupedia:komut"', "izinsiz mesaj tipi"),
])
def test_loosened_bridge_fails(old, new, fragment):
    assert old in ENGINE
    report = _run(gates_ek.gate_bridge, ENGINE.replace(old, new, 1))["G-BRIDGE"]
    assert report["status"] == "FAIL" and fragment in report["detail"]


def test_json_asset_block_is_not_scanned_as_script():
    block = '<script type="application/json" id="edupedia-varliklar">{"x": "window.top.postMessage(1)"}</script>'
    assert _run(gates_ek.gate_bridge, ENGINE.replace(sablon.ASSETS_SLOT, block))["G-BRIDGE"]["status"] == "PASS"


def test_vendored_storage_key_is_not_a_message_type():
    # THEME_STORE_KEY is a localStorage key from the vendored template, not a bridge message
    # type (ruling T6-2); it must not trip G-BRIDGE's foreign-message-type check.
    assert '"edupedia:theme"' in ENGINE
    assert _run(gates_ek.gate_bridge, ENGINE)["G-BRIDGE"]["status"] == "PASS"


def test_foreign_quoted_string_in_script_fails_as_unauthorized_message_type():
    old = "const EDUPEDIA_ASSETS"
    new = 'const EDUPEDIA_X = "edupedia:komut"; const EDUPEDIA_ASSETS'
    assert old in ENGINE
    report = _run(gates_ek.gate_bridge, ENGINE.replace(old, new, 1))["G-BRIDGE"]
    assert report["status"] == "FAIL" and "izinsiz mesaj tipi" in report["detail"]


def _compose(assets=None, footer_lines=(), grounding=None):
    html = ENGINE
    if assets is not None:
        block = ('<script type="application/json" id="edupedia-varliklar">'
                 + json.dumps(assets, ensure_ascii=False) + "</script>")
        html = html.replace(sablon.ASSETS_SLOT, block, 1)
    if footer_lines:
        footer = ('<footer id="edupedia-atif" class="edupedia-atif">'
                  + "".join(f"<p>{html_lib.escape(line)}</p>" for line in footer_lines) + "</footer>")
        html = html.replace(sablon.ATTRIB_SLOT, footer, 1)
    if grounding is not None:
        injected = ('const MODULE_DATA = {\n  verification: {claims: [{claim: "x", grounding: '
                    + grounding + ', verdict: "supported_by_source"}]},')
        html = html.replace("const MODULE_DATA = {", injected, 1)
    return html


CREDIT = 'Fotoğraf: Ayşe & "Deniz" / Pexels'
ASSET = {"a1b2c3d4e5f60718": {"uri": "data:image/jpeg;base64,QUJD", "tur": "image", "credit": CREDIT}}


def test_attrib_is_skipped_without_licensed_material():
    assert _run(gates_ek.gate_attrib, ENGINE)["G-ATTRIB"]["status"] == "SKIPPED"
    meb = _compose(grounding="{document_id: 197, page: 112}")
    assert _run(gates_ek.gate_attrib, meb)["G-ATTRIB"]["status"] == "SKIPPED"


def test_attrib_passes_when_every_credit_is_in_the_footer():
    assert _run(gates_ek.gate_attrib, _compose(ASSET, [CREDIT]))["G-ATTRIB"]["status"] == "PASS"


@pytest.mark.parametrize("assets,lines,grounding,fragment", [
    (ASSET, [], None, "Pexels"),
    ({"a1b2c3d4e5f60718": {"uri": "data:image/png;base64,QQ==", "tur": "image"}}, ["x"], None, "atıf metni yok"),
    (None, [], '{source: "PhET: Fotosentez", url: "https://phet.colorado.edu", license: "CC BY-NC 4.0"}', "PhET"),
])
def test_attrib_fails_when_a_credit_is_missing(assets, lines, grounding, fragment):
    report = _run(gates_ek.gate_attrib, _compose(assets, lines, grounding))["G-ATTRIB"]
    assert report["status"] == "FAIL" and fragment in report["detail"]


def test_licensed_grounding_in_footer_passes():
    html = _compose(None, ["Kaynak: PhET: Fotosentez — CC BY-NC 4.0"],
                    '{source: "PhET: Fotosentez", url: "https://phet.colorado.edu", license: "CC BY-NC 4.0"}')
    assert _run(gates_ek.gate_attrib, html)["G-ATTRIB"]["status"] == "PASS"


def test_malformed_asset_block_fails():
    html = ENGINE.replace(sablon.ASSETS_SLOT,
                          '<script type="application/json" id="edupedia-varliklar">{bozuk</script>', 1)
    assert _run(gates_ek.gate_attrib, html)["G-ATTRIB"]["status"] == "FAIL"


def test_gate_runner_reports_eighteen_gates():
    report = gates.run_gates(ENGINE)
    assert gates.gate_count() == 18 and len(report) == 18
    assert set(gates.EXTRA_GATES) <= set(report)
    assert gates.voice_pattern().search("ders kitabında geçen")
