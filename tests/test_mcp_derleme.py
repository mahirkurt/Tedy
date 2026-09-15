"""Compiler: golden modes, conditional gates really applied, JS literal, schema, security, assets, attributions."""
import json
import shutil
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
