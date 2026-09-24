"""G-BRIDGE and G-ATTRIB: detect a missing, loosened or foreign bridge; missing attributions."""
import html as html_lib
import json
import random
import shutil
import signal
import string
import subprocess
import time

import pytest

from src.mcp_server import gates, gates_ek, sablon

ENGINE = sablon.engine_template("https://tedy.online")
BACKSLASH = chr(92)


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


def test_appearance_message_is_allowed_but_not_required():
    # The dashboard's theme message (parent → module) is an allowed bridge type; modules compiled
    # before it existed carry only progress/restore and must still pass.
    assert '"edupedia:appearance"' in ENGINE
    assert _run(gates_ek.gate_bridge, ENGINE)["G-BRIDGE"]["status"] == "PASS"
    line = 'if(d.type === "edupedia:appearance"){ adoptHostTheme(d.theme); return; }'
    assert line in ENGINE
    assert _run(gates_ek.gate_bridge, ENGINE.replace(line, "", 1))["G-BRIDGE"]["status"] == "PASS"


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


# ---------------------------------------------------------------------------
# Fix round 2 (controller review-r2, finding "New-Important"): F5 — the strict JS string
# decoder must handle \xHH hex escapes and legacy octal escapes (\1-\9, \0<digit>) like a real
# JS engine, or fail closed — not silently mis-decode them as generic identity escapes. Every
# backslash below is built with chr(92) (BACKSLASH) rather than typed literally.
# ---------------------------------------------------------------------------

def test_hex_escape_decodes_like_javascript():
    escape = BACKSLASH + "x41"  # \x41 -> the code point 0x41, i.e. 'A'
    for quote in ('"', "'", "`"):
        body = quote + escape + quote
        decoded, end = gates_ek._decode_js_string(body, 0)
        assert decoded == "A" and end == len(body)

    grounding = '{source: "PhET' + escape + '", license: "CC BY 4.0"}'
    html = _compose(None, ["Kaynak: PhETA — CC BY 4.0"], grounding)
    assert gates.run_gates(html)["G-ATTRIB"]["status"] == "PASS"


def test_truncated_hex_escape_is_undecodable():
    escape = BACKSLASH + "x4"  # only one hex digit before the closing quote
    body = '"' + escape + '"'
    decoded, end = gates_ek._decode_js_string(body, 0)
    assert decoded is None and end is None

    grounding = '{source: "PhET' + escape + '", license: "CC BY 4.0"}'
    html = _compose(None, [], grounding)
    report = gates.run_gates(html)["G-ATTRIB"]
    assert report["status"] == "FAIL" and "lisanslı kaynak çözümlenemedi" in report["detail"]


@pytest.mark.parametrize("digits", ["1", "7", "01"])
def test_legacy_octal_escapes_are_undecodable(digits):
    escape = BACKSLASH + digits
    body = '"' + escape + '"'
    decoded, end = gates_ek._decode_js_string(body, 0)
    assert decoded is None and end is None

    grounding = '{source: "PhET' + escape + '", license: "CC BY 4.0"}'
    html = _compose(None, [], grounding)
    report = gates.run_gates(html)["G-ATTRIB"]
    assert report["status"] == "FAIL" and "lisanslı kaynak çözümlenemedi" in report["detail"]


def test_lone_zero_escape_still_decodes_to_nul():
    escape = BACKSLASH + "0"  # not followed by a digit — unchanged behaviour
    body = '"' + escape + '"'
    decoded, end = gates_ek._decode_js_string(body, 0)
    assert decoded == "\0" and end == len(body)


_NODE_EVAL_SCRIPT = '"use strict"; process.stdout.write(JSON.stringify(eval(process.argv[1])));'
_NAMED_ESCAPE_CHARS = [BACKSLASH, '"', "'", "`", "/", "$", "b", "f", "n", "r", "t", "v"]
_HEX_DIGITS = "0123456789abcdefABCDEF"


def _node_eval(literal):
    # Safe by construction, not just by intent: `literal` is one of our own locally-generated
    # quote-terminated string/template literals (see _random_js_literals), never external input,
    # passed as a real argv element (never interpolated into a shell string). node's `eval` here
    # only ever evaluates a single JS string/template-literal expression built from a small fixed
    # alphabet (letters, digits, '{}', backslash escapes) — this is a network-free differential
    # oracle against real JS semantics per the fix brief, not a code-execution surface.
    proc = subprocess.run(["node", "-e", _NODE_EVAL_SCRIPT, literal],
                          capture_output=True, text=True, timeout=5)
    return proc.returncode, proc.stdout, proc.stderr


def _biased_escape(rng):
    kind = rng.choice(["hex_ok", "hex_short1", "hex_short0", "u_ok", "u_short", "u_brace_ok",
                        "u_brace_unterminated", "octal_1_9", "octal_0d", "zero", "named"])
    if kind == "hex_ok":
        return BACKSLASH + "x" + rng.choice(_HEX_DIGITS) + rng.choice(_HEX_DIGITS)
    if kind == "hex_short1":
        return BACKSLASH + "x" + rng.choice(_HEX_DIGITS)
    if kind == "hex_short0":
        return BACKSLASH + "x"
    if kind == "u_ok":
        return BACKSLASH + "u" + "".join(rng.choice(_HEX_DIGITS) for _ in range(4))
    if kind == "u_short":
        return BACKSLASH + "u" + "".join(rng.choice(_HEX_DIGITS) for _ in range(rng.randint(0, 3)))
    if kind == "u_brace_ok":
        return BACKSLASH + "u{" + "".join(rng.choice(_HEX_DIGITS) for _ in range(rng.randint(1, 5))) + "}"
    if kind == "u_brace_unterminated":
        return BACKSLASH + "u{" + "".join(rng.choice(_HEX_DIGITS) for _ in range(rng.randint(1, 5)))
    if kind == "octal_1_9":
        return BACKSLASH + rng.choice("123456789")
    if kind == "octal_0d":
        return BACKSLASH + "0" + rng.choice("0123456789")
    if kind == "zero":
        return BACKSLASH + "0"
    return BACKSLASH + rng.choice(_NAMED_ESCAPE_CHARS)


def _random_js_literals(count, seed):
    # No '$' and no raw quote characters in the plain-filler alphabet: without '$' a template
    # literal can never form an unescaped "${" (out of scope here — F1/parked M3 territory), and
    # without raw quotes every generated literal is guaranteed a single, cleanly-terminated
    # string/template expression that eval(literal) and _decode_js_string(literal, 0) can be
    # compared on 1:1.
    rng = random.Random(seed)
    plain_alphabet = string.ascii_letters + string.digits + "{}"
    literals = []
    for _ in range(count):
        quote = rng.choice(('"', "'", "`"))
        pieces = []
        for _ in range(rng.randint(1, 4)):
            if rng.random() < 0.6:
                pieces.append(_biased_escape(rng))
            else:
                pieces.append("".join(rng.choice(plain_alphabet) for _ in range(rng.randint(1, 3))))
        literals.append(quote + "".join(pieces) + quote)
    return literals


@pytest.mark.skipif(shutil.which("node") is None, reason="node yok")
def test_decoder_matches_node_semantics_differentially():
    literals = _random_js_literals(200, seed=20260915)
    accepted = rejected = 0
    for literal in literals:
        returncode, stdout, stderr = _node_eval(literal)
        decoded, end = gates_ek._decode_js_string(literal, 0)
        if returncode == 0:
            accepted += 1
            node_value = json.loads(stdout)
            assert decoded == node_value and end == len(literal), (literal, decoded, node_value)
        else:
            rejected += 1
            assert "SyntaxError" in stderr, (literal, stderr)
            assert decoded is None and end is None, (literal, decoded)
    assert accepted + rejected == len(literals)
    print(f"node differential: {accepted} accepted, {rejected} rejected, {len(literals)} total")
