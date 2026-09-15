"""Compiler: golden modes, conditional gates really applied, JS literal, schema, security, assets, attributions."""
import json
import re
import shutil
import signal
import subprocess

import pytest

from src.mcp_server import derleme, gates, ornekler, sablon
from src.mcp_server.derleme import DerlemeHatasi, GomuluVarlik

ORIGIN = "https://tedy.online"


def _fails(report):
    return sorted(g for g, v in report.items() if v["status"] == "FAIL")


def _teach(data):
    return next(s for s in data["segments"] if s["type"] == "teach")


@pytest.mark.parametrize("mode", ornekler.MODES)
def test_golden_every_mode_compiles_with_no_failing_gate(mode):
    data = ornekler.ornek(mode)
    report = gates.run_gates(derleme.derle(data, {}, ORIGIN))
    assert len(report) == 18
    assert _fails(report) == []
    assert report["G-BRIDGE"]["status"] == "PASS"
    assert report["G-VERIFY"]["status"] in ("PASS", "WARN")
    assert report["G-CURRICULUM"]["status"] in ("PASS", "WARN")
    if mode == "MODULE":
        # Fix round 1, F3: the SVG->pictogram golden-example workaround is gone; the demo's
        # inline-SVG teach visual must compile through and G-SVG must genuinely check it, not
        # skip it because there is nothing left to check.
        assert report["G-SVG"]["status"] != "FAIL"
        assert _teach(data)["visual"]["kind"] == "svg"


def test_golden_exam_applies_the_exam_gate():
    report = gates.run_gates(derleme.derle(ornekler.ornek("EXAM"), {}, ORIGIN))
    assert report["G-EXAM"]["status"] in ("PASS", "WARN")


def test_conditional_gates_really_run_on_compiled_output():
    data = ornekler.ornek("CURRICULUM")
    data["curriculum"]["outcomes"][0]["mappedTo"] = ["yok-boyle-segment"]
    assert gates.run_gates(derleme.derle(data, {}, ORIGIN))["G-CURRICULUM"]["status"] == "FAIL"
    data = ornekler.ornek("MODULE")
    data["verification"]["scope"]["in_frame"] = False
    assert gates.run_gates(derleme.derle(data, {}, ORIGIN))["G-VERIFY"]["status"] == "FAIL"


def test_quoted_json_keys_would_hide_the_curriculum_gate():
    # Why js_literal exists: the same broken module written with JSON-quoted keys is not caught.
    data = ornekler.ornek("CURRICULUM")
    data["curriculum"]["outcomes"][0]["mappedTo"] = ["yok-boyle-segment"]
    template = sablon.engine_template(ORIGIN)
    start = template.index(sablon.MODULE_DATA_START)
    end = template.index(sablon.ENGINE_MARKER, start)
    quoted = (template[:start] + "const MODULE_DATA = " + json.dumps(data, ensure_ascii=False, indent=2)
              + ";\n" + template[end:])
    assert gates.run_gates(quoted)["G-CURRICULUM"]["status"] != "FAIL"


def test_js_literal_shape():
    assert derleme.js_literal({"a": 1, "b-c": [True, None, 1.5, "x"]}) == (
        '{\n  a: 1,\n  "b-c": [\n    true,\n    null,\n    1.5,\n    "x"\n  ]\n}')
    assert derleme.js_literal({"k": {"x": {"y": [1]}}}) == '{\n  k: {\n    x: {y: [1]}\n  }\n}'


def test_js_string_escapes_only_what_breaks_the_script():
    out = derleme.js_literal("a</script><!--\u2028b</svg>")
    assert "</script" not in out and "<!--" not in out and "\u2028" not in out
    assert "</svg>" in out
    with pytest.raises(ValueError):
        derleme.js_literal(float("nan"))


def test_trailing_newline_ids_and_slots_are_rejected_by_fullmatch():
    # Ruling T7-1: SEGMENT_ID_RE/ASSET_ID_RE/SLOT_RE use .fullmatch() so a trailing
    # newline (which .match() would silently accept) is rejected.
    data = ornekler.ornek("MODULE")
    data["segments"][0]["id"] = "t1\n"
    with pytest.raises(DerlemeHatasi) as exc:
        derleme.derle(data, {}, ORIGIN)
    assert exc.value.status == "sema_hatasi"
    assert any("id geçersiz" in h for h in exc.value.detay["hatalar"])

    data = ornekler.ornek("MODULE")
    data["meta"]["assets"] = [{"asset_id": "a1b2c3d4e5f60718\n", "slot": "t1.visual"}]
    with pytest.raises(DerlemeHatasi) as exc:
        derleme.derle(data, {}, ORIGIN)
    assert exc.value.status == "sema_hatasi"
    assert any("meta.assets[0]" in h for h in exc.value.detay["hatalar"])

    data = ornekler.ornek("MODULE")
    data["meta"]["assets"] = [{"asset_id": "a1b2c3d4e5f60718", "slot": "t1.visual\n"}]
    with pytest.raises(DerlemeHatasi) as exc:
        derleme.derle(data, {}, ORIGIN)
    assert exc.value.status == "sema_hatasi"
    assert any("meta.assets[0]" in h for h in exc.value.detay["hatalar"])


def test_js_literal_quotes_keys_with_a_trailing_newline():
    # Ruling T7-1: _js_key's _IDENT_RE also uses .fullmatch(), so "a\n" is not a bare
    # identifier key and must be JSON-string-quoted (and thus escaped) instead.
    assert derleme.js_literal({"a\n": 1}) == '{\n  "a\\n": 1\n}'


def test_asset_block_escapes_lt_so_a_credit_cannot_swallow_the_engine_script():
    # Ruling T7-2: a credit string containing "<!--<script>" inside the
    # <script type="application/json" id="edupedia-varliklar"> element must not let the HTML
    # tokenizer treat "</script" (however it appears) as closing that JSON script early and
    # swallowing the following engine <script>. Escaping "<" as \u003c (not just "</" as
    # "<\/") closes that path structurally, because no literal "<" survives in the JSON text.
    data = ornekler.ornek("MODULE")
    teach = _teach(data)
    teach.pop("visual", None)
    img = _varlik(credit="Foto: <!--<script> Ayşe / Pexels")
    data["meta"]["assets"] = [{"asset_id": img.asset_id, "slot": f"{teach['id']}.visual"}]
    html = derleme.derle(data, {img.asset_id: img}, ORIGIN)
    start = html.index('id="edupedia-varliklar">') + len('id="edupedia-varliklar">')
    end = html.index("</script>", start)
    payload = html[start:end]
    assert "<" not in payload
    assert json.loads(payload)[img.asset_id]["credit"] == "Foto: <!--<script> Ayşe / Pexels"
    report = gates.run_gates(html)
    assert _fails(report) == []
    assert report["G-BRIDGE"]["status"] == "PASS"
    assert report["G-ATTRIB"]["status"] == "PASS"


def test_js_string_is_also_valid_json_when_it_stays_double_quoted():
    # Ruling T7-3 (still true for any string F3's new template-literal branch does not claim,
    # i.e. one that does not contain both '"' and '<' -- this one has no '"' at all):
    # gates_ek.gate_attrib json.loads-parses grounding/credit string literals straight out of
    # the compiled HTML. "<\!--" is valid JS but not valid JSON, so a source containing "<!--"
    # would make json.loads (and therefore run_gates) raise. "\u003c!--" is valid in both.
    assert json.loads(derleme.js_literal("a<!--b</script>c d")) == "a<!--b</script>c d"


def test_grounding_source_containing_angle_bracket_is_now_refused_by_f4():
    # Fix round 1, F4 supersedes part of ruling T7-3's original scenario: a grounding
    # source/license may no longer contain "<" at all (new schema-level ban below), precisely
    # so `_js_string` can never route a grounding source/license through F3's new
    # template-literal branch (which triggers on both a quote and "<") -- gates_ek's grounding
    # parser only understands double-quoted JSON strings, not backtick template literals (see F4
    # in derleme.sema_dogrula). A source containing "<!--", which used to compile and PASS
    # G-ATTRIB before this fix round, is therefore now a sema_hatasi instead.
    data = ornekler.ornek("MODULE")
    data["verification"]["claims"].append({
        "claim": "Su döngüsü güneş enerjisiyle sürer.",
        "grounding": {"source": "<!--Açık Ders Notları", "url": "https://example.org/notlar",
                      "license": "CC BY 4.0"},
        "verdict": "supported_by_source"})
    with pytest.raises(DerlemeHatasi) as exc:
        derleme.derle(data, {}, ORIGIN)
    assert exc.value.status == "sema_hatasi"
    assert any("grounding" in h for h in exc.value.detay["hatalar"])


def test_grounding_source_with_braces_is_refused_by_schema():
    # F4: gates_ek's `grounding: {…}` capture is brace-balance-blind ([^{}]*), so a source or
    # license containing '{'/'}' would never be seen by it (a silent false SKIPPED, per the
    # review's Important-2 finding) -- refuse it at the schema boundary instead.
    data = ornekler.ornek("MODULE")
    data["verification"]["claims"].append({
        "claim": "Test iddiası.",
        "grounding": {"source": "PhET {Maddenin Hâlleri}", "url": "https://phet.colorado.edu/x",
                      "license": "CC BY 4.0"},
        "verdict": "supported_by_source"})
    with pytest.raises(DerlemeHatasi) as exc:
        derleme.derle(data, {}, ORIGIN)
    assert exc.value.status == "sema_hatasi"
    assert any("grounding" in h for h in exc.value.detay["hatalar"])


def test_js_string_keeps_double_quoted_json_when_there_is_no_angle_bracket():
    # F3: only strings containing BOTH '"' and '<' become template literals; plain prose with
    # a quote and no markup (e.g. an exam stem) keeps today's double-quoted JSON encoding, so
    # the vendored G-EXAM free-text regexes (hardcoded ["\']...["\'] delimiters) still see a
    # quote-delimited string.
    out = derleme.js_literal('Diyor ki "hızlı" olmalı')
    assert out.startswith('"')


@pytest.mark.skipif(shutil.which("node") is None, reason="node yok")
def test_template_literal_html_fragment_round_trips_through_node():
    # F3: `_js_string` emits a backtick template literal only for a value containing both '"'
    # and '<' (e.g. inline SVG/HTML with double-quoted attributes), so the vendored gates' raw-
    # text scans (G-SVG's role="img" substring match) see real, unescaped double quotes. This
    # proves the emitted literal is valid JS *and* round-trips to the exact original text.
    text = ('<svg role="img"><title>a' + chr(96) + 'b ${x} ' + chr(92)
            + ' </script><!--' + chr(0x2028) + ' </title></svg>')
    literal = derleme.js_literal(text)
    assert literal.startswith("`") and literal.endswith("`")
    out = subprocess.run(["node", "-e", "process.stdout.write(JSON.stringify(" + literal + "))"],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == text


@pytest.mark.parametrize("mutate,fragment", [
    (lambda d: d.pop("meta"), "meta"),
    (lambda d: d["meta"].pop("title"), "meta.title"),
    (lambda d: d["meta"].__setitem__("mode", "OYUN"), "meta.mode"),
    (lambda d: d["meta"].__setitem__("attributions", []), "attributions"),
    (lambda d: d.pop("curriculum"), "curriculum"),
    (lambda d: d.pop("verification"), "verification"),
    (lambda d: d.pop("rewards"), "rewards"),
    (lambda d: d.__setitem__("segments", []), "segments"),
    (lambda d: d["segments"].append(dict(d["segments"][0])), "yinelenmiş"),
    (lambda d: d["segments"][0].__setitem__("id", "a b"), "id geçersiz"),
    (lambda d: d["meta"].__setitem__("tedLink", {"kind": "quiz", "id": "1"}), "tedLink"),
    (lambda d: d["meta"].__setitem__("assets", [{"asset_id": "x", "slot": "t1.visual"}]), "meta.assets[0]"),
])
def test_schema_errors(mutate, fragment):
    data = ornekler.ornek("MODULE")
    mutate(data)
    with pytest.raises(DerlemeHatasi) as exc:
        derleme.derle(data, {}, ORIGIN)
    assert exc.value.status == "sema_hatasi"
    assert any(fragment in h for h in exc.value.detay["hatalar"])


@pytest.mark.parametrize("payload,label", [
    ("<p>x</p><script>alert(1)</script>", "script"),
    ('<img src="x" onerror="alert(1)">', "olay"),
    ('<a href="javascript:alert(1)">x</a>', "javascript"),
    ('<img src="https://evil.example/p.png" alt="">', "dış kaynak"),
    ('<div style="background:url(//evil.example/p.png)">x</div>', "CSS"),
    ('<iframe src="data:text/html,x"></iframe>', "yasak etiket"),
    # F1 (fix round 1): the raw text alone hides these — the URL parser strips ASCII
    # tab/CR/LF before scheme-sniffing, and the HTML parser decodes character references in
    # attribute values assigned through .innerHTML; guvenlik_tara now also scans a normalised
    # (html.unescape'd, tab/CR/LF/NUL-stripped) copy of every string.
    ('<a href="java\tscript:alert(1)">x</a>', "javascript"),
    ('<a href="java\nscript:alert(1)">x</a>', "javascript"),
    ('<a href="&#106;avascript:alert(1)">x</a>', "javascript"),
    ('<a href="javascript&colon;alert(1)">x</a>', "javascript"),
    ('<a href="vbscript:msgbox(1)">x</a>', "javascript"),
    ('<div style="width:expression(alert(1))">x</div>', "CSS"),
    ('<div style="background:url(data:text/html;base64,PHNjcmlwdD4=)">x</div>', "CSS"),
    # F2 (fix round 1): a srcset candidate list can smuggle a remote URL anywhere after the
    # first (lowest-DPI) candidate, not only right after `=`.
    ('<img src="data:image/gif;base64,AA==" '
     'srcset="data:image/gif;base64,AA== 1x, https://evil.example/t.png 2x" alt="">', "dış kaynak"),
    # F7 (fix round 2) regression: a '<' inside a quoted attribute value must not confuse the
    # linear-time "inside a tag" check into missing the on-handler that follows it in the same,
    # still-open tag. Explicitly named in the fix-round-2/3 briefs as a required regression (the
    # inner '<b' is itself letter-led, so F11's narrower tag-opening rule still counts it).
    ('<img alt="a<b" onerror=alert(1)>', "olay"),
    ('<img src=x onerror=alert(1)>', "olay"),
    ('<a href="x" onclick = "y">', "olay"),
    # F8 (fix round 2) true positives for the new srcset candidate parser.
    ('<img src="data:image/gif;base64,AA==" srcset="//evil.example/t.png" alt="">', "dış kaynak"),
    ('<img src="data:image/gif;base64,AA==" srcset=https://evil.example/t.png alt="">', "dış kaynak"),
])
def test_content_security_rejects_active_or_remote_html(payload, label):
    data = ornekler.ornek("MODULE")
    _teach(data)["body"] = [payload]
    with pytest.raises(DerlemeHatasi) as exc:
        derleme.derle(data, {}, ORIGIN)
    assert exc.value.status == "sema_hatasi"
    assert any(label in h for h in exc.value.detay["hatalar"])


def test_content_security_still_allows_data_image_css_background():
    # F1's negative case: `url(data:image/...)` (a legitimate inline CSS image) must not be
    # refused by the new `url(data:(?!image/))` pattern.
    data = ornekler.ornek("MODULE")
    payload = '<div style="background:url(data:image/png;base64,QQ==)">x</div>'
    _teach(data)["body"] = [payload]
    html = derleme.derle(data, {}, ORIGIN)
    assert "background:url(data:image/png;base64,QQ==)" in html


def test_srcset_data_uri_with_slashes_in_payload_is_not_a_false_positive():
    # F8 (re-review Important): the fix-round-1 "scan the whole value for // anywhere" pattern
    # false-positived on any data: URI whose base64 payload happened to contain "//" (measured
    # ~55% of realistic small inline images). The new candidate parser only checks each
    # candidate's own URL scheme, so a "//" inside the base64 payload is inert.
    data = ornekler.ornek("MODULE")
    payload = '<img src="data:image/gif;base64,AA==" srcset="data:image/png;base64,AAAA//AAAA 1x" alt="">'
    _teach(data)["body"] = [payload]
    html = derleme.derle(data, {}, ORIGIN)
    assert "AAAA//AAAA" in html


def _guvenlik_tara_within(data, seconds=2.0):
    """Runs `derleme.guvenlik_tara` under a hard wall-clock deadline (SIGALRM), so a performance
    regression fails fast with a clear timeout instead of hanging the test process."""
    class _PerfTimeout(Exception):
        pass

    def _handler(signum, frame):
        raise _PerfTimeout(f"guvenlik_tara did not finish within {seconds}s")

    old_handler = signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        return derleme.guvenlik_tara(data)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)


@pytest.mark.parametrize("name,data", [
    ("lt_400k", {"x": "<" * 400_000}),
    ("la_130k", {"x": "<a " * 130_000}),
    ("onclick_40k", {"x": " onclick=" * 40_000}),
    ("srcset_a_400k", {"x": '<img srcset="' + "a" * 400_000}),
    ("url_100k", {"x": "url(" * 100_000}),
    ("entity_200k", {"x": "&#" * 200_000}),
    ("java_100k", {"x": "java" * 100_000}),
    ("f6_list_50k_lt", {"x": ["<"] * 50_000}),
])
def test_content_scan_is_linear_time_not_quadratic(name, data):
    # F7 (controller measurement at 9551455, network-free): guvenlik_tara({"x": "<" * 20_000})
    # took 11.08s; "<" * 40_000 took more than 40s. The retired `<[^>]*\son[a-z]+\s*=` pattern
    # retried its greedy scan from every '<' in the string. None of these 8 adversarial inputs is
    # itself dangerous (no scheme/handler ever sits inside a still-open tag), so the correctness
    # assertion is "no false positive" — the point of the test is that it completes at all.
    assert _guvenlik_tara_within(data) == []


@pytest.mark.parametrize("body,label", [
    (['<a href="java', 'script:alert(1)">x</a>'], "javascript"),
    (['<a href="&#106;ava', 'script:alert(1)">x</a>'], "javascript"),
    (['<img src=x o', 'nerror=alert(1)>'], "olay"),
])
def test_array_join_bypass_is_caught_across_body_elements(body, label):
    # F6 (re-review Critical): the vendored engine renders `teach.body` as
    # `(s.body||[]).join("")` straight into innerHTML — proven live in a real Chromium tab by
    # the re-review. Neither element contains the forbidden substring on its own, so per-string
    # scanning alone (`_walk_strings`) sees nothing; `guvenlik_tara` must also scan the joined
    # text of every all-string list.
    data = ornekler.ornek("MODULE")
    _teach(data)["body"] = body
    with pytest.raises(DerlemeHatasi) as exc:
        derleme.derle(data, {}, ORIGIN)
    assert exc.value.status == "sema_hatasi"
    assert any(label in h and "[*]" in h for h in exc.value.detay["hatalar"])


def test_array_join_bypass_error_path_has_the_star_suffix():
    # F6: "The error path is <list path>[*], for example MODULE_DATA.segments[0].body[*]."
    data = ornekler.ornek("MODULE")
    teach = _teach(data)
    segment_index = data["segments"].index(teach)
    teach["body"] = ['<a href="java', 'script:alert(1)">x</a>']
    with pytest.raises(DerlemeHatasi) as exc:
        derleme.derle(data, {}, ORIGIN)
    expected_prefix = f"MODULE_DATA.segments[{segment_index}].body[*]:"
    assert any(h.startswith(expected_prefix) for h in exc.value.detay["hatalar"])


def test_array_join_scan_does_not_false_positive_on_a_normal_multi_paragraph_body():
    data = ornekler.ornek("MODULE")
    _teach(data)["body"] = ["<p>Birinci paragraf.</p>", "<p>İkinci paragraf.</p>"]
    html = derleme.derle(data, {}, ORIGIN)
    assert "Birinci paragraf" in html and "İkinci paragraf" in html


@pytest.mark.parametrize("body", [
    ["<p>x < 3 ise onun = 5</p>"],
    ["<p>a <", " onun = 2</p>"],
])
def test_on_handler_check_does_not_refuse_ordinary_comparison_text(body):
    # F11 (re-review Important #2): an HTML tokeniser only enters its tag-open state at '<'
    # immediately followed by an ASCII letter or '/'; a '<' followed by a space or digit is
    # literal text (a comparison, as in "x < 3"), not a tag opening. Before this fix, math/
    # comparison content like this was refused outright, and F6's list-join scan multiplied the
    # false refusal across every per-item-wrapped field.
    data = ornekler.ornek("MODULE")
    _teach(data)["body"] = body
    html = derleme.derle(data, {}, ORIGIN)
    assert "onun" in html


def test_on_handler_check_does_not_refuse_comparison_text_in_mcq_options():
    data = ornekler.ornek("MODULE")
    mcq = next(s for s in data["segments"] if s["type"] == "mcq")
    mcq["questions"][0]["options"] = ["3 < 5", " onda = doğru"]
    html = derleme.derle(data, {}, ORIGIN)
    assert "onda" in html


def test_exam_stem_with_quote_and_angle_bracket_stays_double_quoted():
    # F9 (re-review Important + PARTIAL): gate_exam extracts stem/source/integrityNote with
    # hardcoded ["\']-only delimiters. Without F9, an ordinary exam.stem containing both '"'
    # and '<' would route through F3's template-literal branch and become invisible to that
    # regex, producing a spurious G-EXAM FAIL on well-formed content.
    data = ornekler.ornek("EXAM")
    data["exam"]["stem"] = '<b>"Buz"</b> güneşte ne olur?'
    html = derleme.derle(data, {}, ORIGIN)
    report = gates.run_gates(html)
    assert report["G-EXAM"]["status"] != "FAIL"
    tail = html[html.index("stem:") + len("stem:"):].lstrip()
    assert tail.startswith('"')


def test_exams_plural_stem_with_quote_and_angle_bracket_stays_double_quoted():
    # F10 (re-review PARTIAL, completing F9): the vendored template documents `exam:{}` as
    # "legacy" and `exams[]` (a list of per-item exam objects) as the current multi-item path;
    # `_exam_collect` extracts stem/source/integrityNote with the same ["\']-only regex for both
    # forms. F9 only special-cased the singular top-level key "exam"; a top-level "exams" list
    # was untouched and reproduced the identical spurious-FAIL bug.
    data = ornekler.ornek("MODULE")
    data["exams"] = [{"stem": '<b>"Buz"</b> güneşte ne olur?', "source": "golden test sorusu",
                       "integrity": "sound", "integrityNote": ""}]
    html = derleme.derle(data, {}, ORIGIN)
    vm = gates.validator()
    inner = vm._array_inner(html, "exams")
    assert inner is not None
    item_block = next(vm._iter_balanced_objects(inner))
    stem_tail = item_block[item_block.index("stem:") + len("stem:"):].lstrip()
    assert stem_tail.startswith('"')
    signals = vm._exam_collect(item_block, html)
    assert signals["stem_ok"] is True


def test_module_data_at_the_budget_compiles():
    data = ornekler.ornek("MODULE")
    base = derleme.girdi_boyutu(data)
    _teach(data)["body"].append("<p>" + "a" * (derleme.MAX_INPUT_BYTES - base - 12) + "</p>")
    assert derleme.girdi_boyutu(data) <= derleme.MAX_INPUT_BYTES
    assert "const MODULE_DATA = {" in derleme.derle(data, {}, ORIGIN)


def test_oversize_module_data_is_refused_honestly():
    data = ornekler.ornek("MODULE")
    _teach(data)["body"] = ["<p>" + "a" * derleme.MAX_INPUT_BYTES + "</p>"]
    with pytest.raises(DerlemeHatasi) as exc:
        derleme.derle(data, {}, ORIGIN)
    assert exc.value.status == "cok_buyuk"
    assert exc.value.detay["sinir"] == 400_000 and exc.value.detay["bayt"] > 400_000


def _varlik(tur="image", credit="Fotoğraf: Ayşe Yılmaz / Pexels", bayt=1000, asset_id="a1b2c3d4e5f60718"):
    mime = {"image": "image/jpeg", "video": "video/mp4", "ses": "audio/mpeg", "muzik": "audio/mpeg"}[tur]
    return GomuluVarlik(asset_id=asset_id, tur=tur, mime=mime, data_uri=f"data:{mime};base64,QUJD", bayt=bayt,
                        credit=credit, lisans="Pexels Lisansı", alt="Buz kalıbı", kaynak="pexels")


def test_visual_and_audio_slots_bind_and_attributions_render():
    data = ornekler.ornek("MODULE")
    teach = _teach(data)
    teach.pop("visual", None)
    img = _varlik()
    ses = _varlik("ses", credit="Seslendirme: yapay zekâ ile üretildi (MiniMax speech-2.8-hd)", asset_id="0f1e2d3c4b5a6978")
    data["meta"]["assets"] = [{"asset_id": img.asset_id, "slot": f"{teach['id']}.visual"},
                              {"asset_id": ses.asset_id, "slot": f"{teach['id']}.audio"}]
    html = derleme.derle(data, {img.asset_id: img, ses.asset_id: ses}, ORIGIN)
    report = gates.run_gates(html)
    assert _fails(report) == [] and report["G-ATTRIB"]["status"] == "PASS"
    assert f'visual: {{kind: "image", asset: "{img.asset_id}", alt: "Buz kalıbı"}}' in html
    assert html.index('id="edupedia-varliklar"') < html.index("const MODULE_DATA = {")
    assert '<footer id="edupedia-atif"' in html and "<p>Fotoğraf: Ayşe Yılmaz / Pexels</p>" in html


@pytest.mark.parametrize("slot_of,assets,status", [
    (lambda d: f"{_teach(d)['id']}.visual", {}, "varlik_bulunamadi"),
    (lambda d: f"{next(s for s in d['segments'] if s['type'] == 'mcq')['id']}.visual", None, "slot_yalniz_teach"),
    (lambda d: f"{_teach(d)['id']}.audio", None, "slot_tur_uyusmazligi"),
    (lambda d: "yok-boyle.visual", None, "slot_segmenti_yok"),
])
def test_slot_errors(slot_of, assets, status):
    data = ornekler.ornek("MODULE")
    _teach(data).pop("visual", None)
    img = _varlik()
    data["meta"]["assets"] = [{"asset_id": img.asset_id, "slot": slot_of(data)}]
    with pytest.raises(DerlemeHatasi) as exc:
        derleme.derle(data, {img.asset_id: img} if assets is None else assets, ORIGIN)
    assert exc.value.status == status


def test_occupied_slot_and_asset_budget():
    data = ornekler.ornek("MODULE")
    teach = _teach(data)
    teach["visual"] = {"kind": "pictogram", "ref": "pic-idea"}
    img = _varlik()
    data["meta"]["assets"] = [{"asset_id": img.asset_id, "slot": f"{teach['id']}.visual"}]
    with pytest.raises(DerlemeHatasi) as exc:
        derleme.derle(data, {img.asset_id: img}, ORIGIN)
    assert exc.value.status == "slot_dolu"
    teach.pop("visual")
    big = _varlik(bayt=derleme.ASSET_BUDGET_BYTES + 1)
    with pytest.raises(DerlemeHatasi) as exc:
        derleme.derle(data, {big.asset_id: big}, ORIGIN)
    assert exc.value.status == "varlik_butcesi_asildi"


def test_attribution_that_trips_g_voice_is_refused():
    data = ornekler.ornek("MODULE")
    teach = _teach(data)
    teach.pop("visual", None)
    img = _varlik(credit="Görsel: ders kitabı sayfa 12")
    data["meta"]["assets"] = [{"asset_id": img.asset_id, "slot": f"{teach['id']}.visual"}]
    with pytest.raises(DerlemeHatasi) as exc:
        derleme.derle(data, {img.asset_id: img}, ORIGIN)
    assert exc.value.status == "atif_dil_kurali"


def test_licensed_grounding_becomes_a_footer_line_and_g_attrib_guards_it():
    data = ornekler.ornek("MODULE")
    data["verification"]["claims"].append({
        "claim": "Madde tanecikleri sürekli hareket eder.",
        "grounding": {"source": "PhET: Maddenin Hâlleri", "url": "https://phet.colorado.edu/tr/simulations/states-of-matter",
                      "license": "CC BY 4.0"},
        "verdict": "supported_by_source"})
    html = derleme.derle(data, {}, ORIGIN)
    assert gates.run_gates(html)["G-ATTRIB"]["status"] == "PASS"
    line = "<p>Kaynak: PhET: Maddenin Hâlleri — CC BY 4.0</p>"
    assert line in html
    assert gates.run_gates(html.replace(line, ""))["G-ATTRIB"]["status"] == "FAIL"


def test_cli_writes_a_gate_clean_quiz(tmp_path, capsys):
    out = tmp_path / "quiz.html"
    assert derleme.main(["--ornek", "QUIZ", "--cikti", str(out), "--ebeveyn-origin", "http://127.0.0.1:8286"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["kapi_ozeti"]["fail"] == 0 and summary["bayt"] == out.stat().st_size
    assert 'const EDUPEDIA_PARENT_ORIGIN = "http://127.0.0.1:8286";' in out.read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("node") is None, reason="node yok")
def test_demo_fixture_is_the_vendored_demo():
    out = subprocess.run(["node", "-e", ornekler.DEMO_EXTRACT_JS, str(sablon.TEMPLATE_PATH)],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == ornekler.demo()


# ---------------------------------------------------------------------------
# F12 (fix round 4, re-review Critical): the on-handler scan required WHITESPACE
# immediately before `on` (`\son…=`), so a handler separated from the previous
# attribute by `/` (`<img/onerror=…>`, `<svg/onload=…>`, `<img src=x/onerror=…>`)
# or by a closing attribute-value quote with no whitespace (`<img src="x"onerror=…>`
# — proven live in Chromium by the re-review) compiled through guvenlik_tara with
# ZERO refusals and produced real, firing DOM event handlers. The negative
# lookbehind `(?<![A-Za-z0-9:_-])` refuses `on…=` on every attribute boundary while
# still ignoring a name continuation (`data-onx`). Over-refusal is acceptable; a
# miss is a live XSS.
# ---------------------------------------------------------------------------

_F12_PREVIOUSLY_BYPASSED = [
    ['<img/onerror=alert(1)>'],
    ['<svg/onload=alert(1)>'],
    ['<img src="x"onerror=alert(1)>'],
    ['<img src=x/onerror=alert(1)>'],
    ['<img src="x"onmouseover="alert(1)">'],
    ['<a href=x /onclick=alert(1)>'],
    # Split across two adjacent body elements: neither element carries the handler
    # inside a still-open tag on its own, so only the F6 list-join scan catches it.
    ['<img src=x', '/onerror=alert(1)>'],
]


@pytest.mark.parametrize("body", _F12_PREVIOUSLY_BYPASSED)
def test_f12_slash_and_quote_separated_on_handlers_are_refused(body):
    data = ornekler.ornek("MODULE")
    _teach(data)["body"] = body
    with pytest.raises(DerlemeHatasi) as exc:
        derleme.derle(data, {}, ORIGIN)
    assert exc.value.status == "sema_hatasi"
    assert any("satır içi olay işleyicisi" in h for h in exc.value.detay["hatalar"])


@pytest.mark.parametrize("payload", [
    '<img src=x onerror=alert(1)>',
    '<img alt="a<b" onerror=alert(1)>',
    '<a href="x" onclick = "y">',
    '<img' + chr(9) + 'onerror=alert(1)>',  # tab-separated handler (chr(9))
])
def test_f12_whitespace_separated_on_handlers_still_refused(payload):
    # No regression: every handler the old whitespace rule already caught must stay caught.
    data = ornekler.ornek("MODULE")
    _teach(data)["body"] = [payload]
    with pytest.raises(DerlemeHatasi) as exc:
        derleme.derle(data, {}, ORIGIN)
    assert exc.value.status == "sema_hatasi"
    assert any("satır içi olay işleyicisi" in h for h in exc.value.detay["hatalar"])


@pytest.mark.parametrize("body,needle", [
    (["<p>x < 3 ise onun = 5</p>"], "onun"),          # comparison text, not a tag
    (["<p>ışık = yol, onun = 2</p>"], "onun"),        # comparison text, not a tag
    (['<div data-onx="v">alt</div>'], "data-onx"),    # a data-* attribute name, `on` follows '-'
])
def test_f12_boundary_does_not_refuse_non_handlers(body, needle):
    # The lookbehind class `[A-Za-z0-9:_-]` are attribute-name-continuation characters, so
    # `data-onx` is ignored; and F11's tag-context walk keeps the comparison text (no still-open
    # tag before `onun`) from being refused. Neither must become a new false positive.
    data = ornekler.ornek("MODULE")
    _teach(data)["body"] = body
    html = derleme.derle(data, {}, ORIGIN)
    assert needle in html


@pytest.mark.parametrize("s", ["<a" * 200_000, "< on=" * 80_000, "<img/on" * 57_000])
def test_f12_on_handler_scan_stays_linear(s):
    # F13 (fix round 5): rewritten for stability under load. `derleme.MAX_INPUT_BYTES` (400_000)
    # is the real MODULE_DATA input budget, so a 400_000-character adversarial string (each of
    # these three is ~400_000 chars: "<a"*200_000, "< on="*80_000, "<img/on"*57_000) is already at
    # the extreme edge of any real input — there is no larger real-world case worth also covering.
    #
    # The sole gate is an 8 s *wall-clock* SIGALRM, load-independent by construction (it fires
    # however busy the runner is, unlike a CPU-time or tight wall-clock micro-threshold). The
    # retired quadratic `<[^>]*\son[a-z]+\s*=` pattern took over 40 s at just 40_000 chars (fix
    # round 2's controller measurement); `test_f13_retired_quadratic_pattern_times_out_under_the_same_alarm`
    # below proves, self-containedly, that this same 8 s alarm actually catches that pattern at
    # 200_000 chars — so it would catch any reintroduced quadratic behaviour here at 400_000 chars
    # by an even wider margin. No CPU-time or tighter wall-clock assertion is kept (the previous
    # `cpu < 2.0` micro-threshold is exactly what flaked under load).
    #
    # None of these three shapes ever puts a handler inside a still-open tag, so the correct
    # verdict is "no refusal"; `test_f13_on_handler_scan_still_refuses_a_real_slash_separated_handler_at_scale`
    # below is the correctness companion proving detection was not traded away for speed.
    assert _guvenlik_tara_within({"x": s}, seconds=8.0) == []


def test_f13_on_handler_scan_still_refuses_a_real_slash_separated_handler_at_scale():
    # Correctness companion to the linearity test above, at the same ~400 KB scale: the
    # "<img/on"-repeated shape with a real handler completing at the very end (F12's
    # slash-separated-handler case) must still be refused — the linear-time scan must not have
    # traded away detection for speed.
    dangerous = ("<img/on" * 57_000) + "error=alert(1)>"
    result = _guvenlik_tara_within({"x": dangerous}, seconds=8.0)
    assert any("satır içi olay işleyicisi" in h for h in result)


def test_f13_retired_quadratic_pattern_times_out_under_the_same_alarm():
    # F13 requirement 5: a self-contained, in-test proof that the 8 s SIGALRM guard used above
    # would actually fire on a real quadratic regression. The retired pattern is built here only —
    # it is NOT imported from derleme.py (it no longer exists there) and must never be
    # reintroduced into the compiler.
    retired_quadratic_pattern = re.compile(r"<[^>]*\son[a-z]+\s*=", re.I)
    s = "<" * 200_000  # half the size of the F13 inputs above; the retired pattern took over 40 s
                       # at just 40_000 chars (fix round 2's controller measurement), so 200_000
                       # chars is expected to time out many times over under an 8 s deadline.

    class _RetiredPatternTimeout(Exception):
        pass

    def _handler(signum, frame):
        raise _RetiredPatternTimeout()

    old_handler = signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, 8.0)
    try:
        with pytest.raises(_RetiredPatternTimeout):
            retired_quadratic_pattern.search(s)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)


@pytest.mark.parametrize("mode", ornekler.MODES)
def test_f12_golden_sweep_stays_fail_free_with_g_svg_pass(mode):
    # F12 must not regress any golden mode: all nine still compile FAIL-free with G-SVG PASS.
    report = gates.run_gates(derleme.derle(ornekler.ornek(mode), {}, ORIGIN))
    assert _fails(report) == []
    assert report["G-SVG"]["status"] == "PASS"
