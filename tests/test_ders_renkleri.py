"""Tedy ders renk sistemi: tek tablo, üç çalışma zamanı, Carbon'un kendi değerleri.

Kaynak vendor otorite dosyasının `tedyLayer.subjectThemes` bölümüdür. Bu testler:
  * alan çözümlemesinin backend (Python), modül şablonu (JS) ve pano (TS) için aynı sonucu verdiğini,
  * her rol renginin Carbon'dan geldiğini (tag token'ları, palet adımları) ve adının değeriyle
    tuttuğunu,
  * kontrast sözlerinin (rol açıklamalarında yazan eşikler) her aile ve her zemin için sağlandığını,
  * anlam renklerinin (kırmızı, yeşil, sarı, turuncu) hiçbir alana verilmediğini,
  * üretilmiş dosyaların (şablon bölgeleri, dashboard/src/theme/subjects.ts ve _subjects.scss)
    otoriteden kopmadığını,
  * panonun ve şablonun Carbon paleti dışında renk yazmadığını denetler.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src import subject_themes
from src.mcp_server.vendor_sync import VENDOR_DIR

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = json.loads((VENDOR_DIR / "assets" / "carbon-v11-authority.json").read_text(encoding="utf-8"))
ST = AUTHORITY["tedyLayer"]["subjectThemes"]
TEMPLATE_PATH = VENDOR_DIR / "assets" / "module-template.html"
EXAMPLES = sorted(ST["examples"].items())

LIGHT_GROUNDS = {"white/layer-01": "#ffffff", "g10 background": "#f4f4f4", "tedy page cool-gray-10": "#f2f4f8"}
DARK_GROUNDS = {"g100 background": "#161616", "layer-01": "#262626", "layer-02": "#393939",
                "tedy page cool-gray-100": "#121619"}


def _luminance(hex_value: str) -> float:
    channels = [int(hex_value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _node(min_major: int = 22) -> str | None:
    node = shutil.which("node")
    if not node:
        return None
    out = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()
    major = int(re.match(r"v(\d+)", out).group(1)) if out.startswith("v") else 0
    return node if major >= min_major else None


# ── çözümleme ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("course,domain", EXAMPLES)
def test_backend_resolves_every_example(course, domain):
    assert subject_themes.domain_of(course)["id"] == domain


def test_every_course_the_portal_normalises_to_has_a_domain_on_purpose():
    from src.course_names import COURSE_ALIASES
    canonical = set(COURSE_ALIASES) | {"Türkçe", "Matematik", "Fen Bilimleri", "Sosyal Bilgiler"}
    for course in canonical:
        assert subject_themes.domain_of(course)["id"] != "genel", course


def test_template_js_resolves_like_the_backend(tmp_path):
    node = _node()
    if node is None:
        pytest.skip("node >= 22 yok")
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    start = html.index("  /* tedy:ders-alanlari */")
    end = html.index("  function subjectFamily(){", start)
    end = html.index("\n  }\n", end) + 4
    probe = tmp_path / "probe.js"
    probe.write_text(
        "let D={meta:{}};\n" + html[start:end]
        + "\nconst out={};for(const [c] of " + json.dumps(EXAMPLES, ensure_ascii=False)
        + "){D={meta:{subject:c}};out[c]=[subjectDomain().id,subjectFamily()];}\n"
        + "D={meta:{subject:'Türkçe',accent:'teal'}};out['__override']=subjectFamily();\n"
        + "D={meta:{subject:'Türkçe',accent:'#da1e28'}};out['__reject']=subjectFamily();\n"
        + "console.log(JSON.stringify(out));\n", encoding="utf-8")
    got = json.loads(subprocess.run([node, str(probe)], capture_output=True, text=True, check=True).stdout)
    for course, domain in EXAMPLES:
        assert got[course] == [domain, subject_themes.family_of(course)], course
    assert got["__override"] == "teal"
    assert got["__reject"] == "magenta"


def test_dashboard_ts_resolves_like_the_backend(tmp_path):
    node = _node()
    if node is None:
        pytest.skip("node >= 22 yok (TypeScript tip ayıklama gerekir)")
    probe = ROOT / "dashboard" / "src" / "theme" / "_probe_subjects.mts"
    probe.write_text(
        "import { subjectDomain } from './subjects.ts'\n"
        "const out: Record<string, string> = {}\n"
        "for (const [c] of " + json.dumps(EXAMPLES, ensure_ascii=False) + ") out[c] = subjectDomain(c).id\n"
        "console.log(JSON.stringify(out))\n", encoding="utf-8")
    try:
        run = subprocess.run([node, "--experimental-strip-types", "--no-warnings", str(probe)],
                             capture_output=True, text=True)
    finally:
        probe.unlink()
    if run.returncode != 0 and "strip-types" in run.stderr:
        pytest.skip("node tip ayıklamayı desteklemiyor")
    assert run.returncode == 0, run.stderr
    got = json.loads(run.stdout)
    for course, domain in EXAMPLES:
        assert got[course] == domain, course


# ── Carbon kökeni ────────────────────────────────────────────────────────────

def _palette_value(step: str) -> str:
    if step == "white-0":
        return "#ffffff"
    family, _, grade = step.rpartition("-")
    if grade == "hover":
        family, _, grade = family.rpartition("-")
        return AUTHORITY["paletteHover"][family][grade]
    return AUTHORITY["palette"][family][grade]


@pytest.mark.parametrize("family", sorted(ST["families"]))
def test_every_role_is_a_named_carbon_value(family):
    for mode, roles in ST["families"][family].items():
        for role, (step, hex_value) in roles.items():
            assert _palette_value(step) == hex_value, (family, mode, role, step)
            if role not in ("onAccent",):
                assert step.startswith(family + "-"), (family, mode, role, step)


@pytest.mark.parametrize("family", sorted(set(ST["families"]) & set(AUTHORITY["tagPairs"])))
def test_surface_pairs_are_carbon_tag_tokens(family):
    for mode in ("light", "dark"):
        roles = ST["families"][family][mode]
        assert [roles["surface"][1], roles["onSurface"][1]] == AUTHORITY["tagPairs"][family][mode]


def test_meaning_colours_are_never_a_subject_colour():
    families = set(ST["families"])
    assert not families & {"red", "green", "yellow", "orange"}
    assert set(ST["reserved"]) == {"red", "green", "yellow", "orange"}
    used = {d["family"] for d in ST["domains"]} | {ST["fallback"]["family"]}
    assert used <= families


# ── kontrast sözleri ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("family", sorted(ST["families"]))
def test_contrast_promises_hold_on_every_ground(family):
    light, dark = ST["families"][family]["light"], ST["families"][family]["dark"]
    for ground in LIGHT_GROUNDS.values():
        assert contrast(light["accent"][1], ground) >= 4.5
        assert contrast(light["text"][1], ground) >= 6.9
    for ground in DARK_GROUNDS.values():
        assert contrast(dark["accent"][1], ground) >= 4.5
        assert contrast(dark["text"][1], ground) >= 6.7
    for roles in (light, dark):
        assert contrast(roles["onSurface"][1], roles["surface"][1]) >= 4.5
        assert contrast(roles["onAccent"][1], roles["accent"][1]) >= 4.5
        assert contrast(roles["accent"][1], roles["surface"][1]) >= 3.0  # halka, seçili karo üstünde
    # ters (inverse) tanım balonu: açık temada #393939 üstünde koyu modun text rolü, g100'de tersi
    assert contrast(dark["text"][1], "#393939") >= 4.5
    assert contrast(light["text"][1], "#f4f4f4") >= 4.5


# ── üretilmiş dosyalar ───────────────────────────────────────────────────────

def test_template_regions_are_generated_from_the_authority():
    script = VENDOR_DIR / "scripts" / "sync_carbon_tokens.py"
    result = subprocess.run([sys.executable, str(script), "--check"], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout
    assert "Ders renk sistemi:" in result.stdout


def test_dashboard_files_are_generated_from_the_authority():
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "gen_subject_themes.py"), "--check"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout


def test_template_carries_no_colour_arithmetic():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "color-mix(" not in html
    assert "function mix(" not in html and "setAccent" not in html
    assert "--seg-accent" not in html  # segment tipi renk ailesi değil, ders ailesinin tonuyla imlenir


# ── backend ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("course", ["Türkçe", "Matematik", "Fransızca", "Görsel Sanatlar", "PDR"])
def test_backend_course_colour_is_the_family_accent(course):
    os.environ.setdefault("TEST_AUTH_BYPASS", "1")
    from src import dashboard_api  # içe aktarma yan etkili; test_dashboard_api.py ile aynı ortam

    family = subject_themes.family_of(course)
    assert dashboard_api._course_color(course) == ST["families"][family]["light"]["accent"][1]


# ── Carbon paleti dışında renk yok ───────────────────────────────────────────

def _palette() -> set[str]:
    values = {"#ffffff", "#000000"}
    for table in ("palette", "paletteHover"):
        for steps in AUTHORITY[table].values():
            values |= {h.lower() for h in steps.values()}
    return values


def _off_palette(text: str) -> set[str]:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(?m)(^|[^:])//.*$", r"\1", text)
    text = re.sub(r"base64,[A-Za-z0-9+/=]+", "", text)
    text = re.sub(r"url\(\"?data:[^)]*\)", "", text)
    palette, bad = _palette(), set()
    for match in re.finditer(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", text):
        value = match.group(0).lower()
        if len(value) == 4:
            value = "#" + "".join(c * 2 for c in value[1:])
        if value not in palette:
            bad.add(match.group(0))
    for match in re.finditer(r"rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)", text):
        value = "#%02x%02x%02x" % tuple(int(g) for g in match.groups())
        if value not in palette:
            bad.add(match.group(0))
    if "color-mix(" in text:
        bad.add("color-mix")
    return bad


DASHBOARD_SOURCES = sorted(
    p for pattern in ("**/*.scss", "**/*.tsx", "**/*.ts")
    for p in (ROOT / "dashboard" / "src").glob(pattern)
)


@pytest.mark.parametrize("path", DASHBOARD_SOURCES, ids=lambda p: str(p.relative_to(ROOT)))
def test_dashboard_writes_only_carbon_palette_colours(path):
    assert _off_palette(path.read_text(encoding="utf-8")) == set()


def test_module_template_writes_only_carbon_palette_colours():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    style = "".join(re.findall(r"<style[^>]*>(.*?)</style>", html, flags=re.S))
    assert _off_palette(style) == set()
