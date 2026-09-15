"""G-BRIDGE and G-ATTRIB: detect a missing, loosened or foreign bridge; missing attributions."""
import html as html_lib
import json
import signal
import time

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


# ---------------------------------------------------------------------------
# Fix round 1 (controller review): F1 — licensed grounding parsing never raises
# and never silently skips (C1 + I1); F2 — only a real type="application/json"
# script is excluded from the bridge scan (I2); F3 — every missing-credit asset
# is reported (M4); F4 — asset-block shape tests (M6).
# ---------------------------------------------------------------------------

def test_escaped_apostrophe_source_decodes_and_matches_footer():
    grounding = r'{source: "MEB\'nin ders kitabı", url: "https://example.gov.tr", license: "CC BY-NC 4.0"}'
    with_footer = _compose(None, ["Kaynak: MEB'nin ders kitabı — CC BY-NC 4.0"], grounding)
    assert gates.run_gates(with_footer)["G-ATTRIB"]["status"] == "PASS"

    without_footer = _compose(None, [], grounding)
    report = gates.run_gates(without_footer)["G-ATTRIB"]
    assert report["status"] == "FAIL"


def test_single_quoted_grounding_values_decode_and_are_enforced():
    grounding = "{source: 'PhET: Fotosentez', url: 'https://phet.colorado.edu', license: 'CC BY-NC 4.0'}"
    with_footer = _compose(None, ["Kaynak: PhET: Fotosentez — CC BY-NC 4.0"], grounding)
    assert _run(gates_ek.gate_attrib, with_footer)["G-ATTRIB"]["status"] == "PASS"

    without_footer = _compose(None, [], grounding)
    report = _run(gates_ek.gate_attrib, without_footer)["G-ATTRIB"]
    assert report["status"] == "FAIL" and "PhET" in report["detail"]


def test_template_literal_source_decodes_and_matches_html_escaped_footer():
    grounding = '{source: `PhET "Hâller" <b>`, license: "CC BY 4.0"}'
    with_footer = _compose(None, ['PhET "Hâller" <b> — CC BY 4.0'], grounding)
    assert _run(gates_ek.gate_attrib, with_footer)["G-ATTRIB"]["status"] == "PASS"

    without_footer = _compose(None, [], grounding)
    report = _run(gates_ek.gate_attrib, without_footer)["G-ATTRIB"]
    assert report["status"] == "FAIL"


def test_undecodable_source_fails_closed_without_raising():
    grounding = r'{source: "PhET \u12", license: "CC BY 4.0"}'
    html = _compose(None, [], grounding)
    report = gates.run_gates(html)["G-ATTRIB"]
    assert report["status"] == "FAIL" and "lisanslı kaynak çözümlenemedi" in report["detail"]


def test_unescaped_template_placeholder_is_undecodable():
    # A template literal containing an unescaped ${ is undecodable (F1). Tested at the
    # _decode_value level rather than end-to-end through engine_template: _GROUNDING_RE's
    # brace-balance limitation (review M3, explicitly parked for this fix round) means a
    # grounding body containing literal '{'/'}' characters — which "${x}" necessarily has —
    # can never be captured by _GROUNDING_RE in the first place, so gate_attrib can never
    # actually observe this shape end-to-end today; asserting FAIL through the full pipeline
    # here would be a false-pass test that doesn't exercise the decoder at all (it would in
    # fact currently come back SKIPPED, not FAIL, because no grounding body is found).
    body = 'source: `PhET ${x}`, license: "CC BY 4.0"'
    found, decoded = gates_ek._decode_value(body, gates_ek._SOURCE_START_RE)
    assert found and decoded is None


def test_decoder_unit_cases():
    decoded, end = gates_ek._decode_js_string(r'"\u{1F600}"', 0)
    assert decoded == chr(0x1F600) and end == len(r'"\u{1F600}"')

    decoded, end = gates_ek._decode_js_string(r'"\0"', 0)
    assert decoded == "\0" and end == len(r'"\0"')

    # line continuation: backslash followed by a real newline vanishes entirely
    body = '"ab\\\ncd"'
    decoded, end = gates_ek._decode_js_string(body, 0)
    assert decoded == "abcd" and end == len(body)

    # \$ inside a template literal decodes to a literal '$' and does not trip the
    # unescaped-${ check for the '{' that (coincidentally) is not present here
    decoded, end = gates_ek._decode_js_string("`\\$100`", 0)
    assert decoded == "$100" and end == len("`\\$100`")


def test_decoy_attribute_containing_the_text_is_not_excluded_from_bridge_scan():
    decoy = '<script data-note="see application/json">window.top.postMessage({a:1}, "*");</script>'
    report = _run(gates_ek.gate_bridge, ENGINE + decoy)["G-BRIDGE"]
    assert report["status"] == "FAIL" and "window.top" in report["detail"]


def test_single_quoted_json_type_is_still_excluded_from_bridge_scan():
    block = ('<script type=\'application/json\' id="edupedia-varliklar">'
             '{"x": "window.top.postMessage(1)"}</script>')
    assert _run(gates_ek.gate_bridge, ENGINE.replace(sablon.ASSETS_SLOT, block))["G-BRIDGE"]["status"] == "PASS"


def test_attrib_reports_every_asset_missing_a_credit():
    assets = {
        "a1b2c3d4e5f60718": {"uri": "data:image/png;base64,QQ==", "tur": "image"},
        "1122334455667788": {"uri": "data:image/png;base64,Qg==", "tur": "image", "credit": "   "},
    }
    report = _run(gates_ek.gate_attrib, _compose(assets, ["x"]))["G-ATTRIB"]
    assert report["status"] == "FAIL"
    assert "a1b2c3d4e5f60718" in report["detail"] and "1122334455667788" in report["detail"]


def test_attrib_fails_when_asset_block_is_not_an_object():
    html = ENGINE.replace(sablon.ASSETS_SLOT,
                          '<script type="application/json" id="edupedia-varliklar">[1]</script>', 1)
    report = _run(gates_ek.gate_attrib, html)["G-ATTRIB"]
    assert report["status"] == "FAIL" and "nesne değil" in report["detail"]


def test_attrib_fails_when_asset_record_is_not_an_object():
    html = ENGINE.replace(sablon.ASSETS_SLOT,
                          '<script type="application/json" id="edupedia-varliklar">'
                          '{"a1b2c3d4e5f60718": "x"}</script>', 1)
    report = _run(gates_ek.gate_attrib, html)["G-ATTRIB"]
    assert report["status"] == "FAIL" and "atıf metni yok" in report["detail"]


# ---------------------------------------------------------------------------
# perf fix (controller ruling, SP4 Task 8): G-BRIDGE's receiver and '*' scans must be linear in
# the script length. The old `_POST_RE` captured the whole dotted receiver chain via an
# unanchored finditer over the entire script body, so a single long run of word characters
# anywhere in that body (e.g. a compiled MODULE_DATA string literal) made its backtracking group
# retry at every position of that run — quadratic. The old `_STAR_RE`'s unbounded `[^;]*?` had
# the same shape: many `postMessage(` occurrences with no ';' to stop the scan made each one
# rescan an unbounded amount of remaining text. Each scenario below is bounded by a hard
# wall-clock SIGALRM (not just an assertion) so a reintroduced ReDoS fails fast here instead of
# hanging the whole run — before the fix, scenarios 1, 3 and 4 hang past the alarm; scenario 2
# stays under the alarm but is still ~6-10x slower than the fixed code (see task-8-report.md).
# ---------------------------------------------------------------------------

class _PerfTimeout(Exception):
    pass


def _bounded_seconds(seconds, fn):
    def _handler(signum, frame):
        raise _PerfTimeout(f"exceeded {seconds}s — G-BRIDGE perf regression")
    old_handler = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    start = time.monotonic()
    try:
        result = fn()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
    return result, time.monotonic() - start


def test_gate_bridge_is_fast_next_to_a_long_unrelated_identifier_run():
    """Reproduces the SP4 Task 8 hang: a compiled MODULE_DATA string can contain a very long run
    of plain word characters with no postMessage call anywhere near it."""
    html = "<script>var " + "a" * 400_000 + ";</script>"
    report, elapsed = _bounded_seconds(10, lambda: _run(gates_ek.gate_bridge, html))
    assert elapsed < 2.0, f"gate_bridge took {elapsed:.2f}s"
    assert report["G-BRIDGE"]["status"] == "FAIL" and "köprüsü yok" in report["G-BRIDGE"]["detail"]


def test_gate_bridge_is_fast_with_many_legitimate_calls_and_still_names_the_receiver():
    html = "<script>" + "a.postMessage(x, EDUPEDIA_PARENT_ORIGIN);" * 20_000 + "</script>"
    report, elapsed = _bounded_seconds(10, lambda: _run(gates_ek.gate_bridge, html))
    assert elapsed < 2.0, f"gate_bridge took {elapsed:.2f}s"
    assert report["G-BRIDGE"]["status"] == "FAIL" and "bulunan: a" in report["G-BRIDGE"]["detail"]


def test_gate_bridge_is_fast_scanning_for_a_star_target_with_no_semicolons():
    # One legitimate call first so the scan does not short-circuit on "no bridge"; then 50,000
    # bare `postMessage(` occurrences with no ';' anywhere — the shape that made the old
    # `_STAR_RE`'s unbounded `[^;]*?` scan quadratic.
    html = ("<script>window.parent.postMessage(x, EDUPEDIA_PARENT_ORIGIN);"
           + "postMessage(" * 50_000 + "</script>")
    report, elapsed = _bounded_seconds(10, lambda: _run(gates_ek.gate_bridge, html))
    assert elapsed < 2.0, f"gate_bridge took {elapsed:.2f}s"
    assert report["G-BRIDGE"]["status"] == "FAIL"


def test_gate_bridge_is_fast_on_the_real_engine_template_with_a_long_embedded_run():
    engine = sablon.engine_template("https://tedy.online")
    html = engine.replace("const MODULE_DATA = {", 'const MODULE_DATA = { x: "' + "a" * 400_000 + '", ', 1)
    report, elapsed = _bounded_seconds(10, lambda: _run(gates_ek.gate_bridge, html))
    assert elapsed < 2.0, f"gate_bridge took {elapsed:.2f}s"
    assert report["G-BRIDGE"]["status"] == "PASS"
