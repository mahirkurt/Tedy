"""Tedy tasarım dili tek kaynaktan: pano, modül şablonu ve derleyici aynı değerleri taşır.

Kaynak vendor otorite dosyasının `tedyLayer` bölümüdür (vendor/assets/carbon-v11-authority.json):
her Tedy token'ı için Carbon palet adımı + hex ve panoda aynı rolü taşıyan `--ted-*` değişkeni.
Bu testler üç yüzeyin o kaynaktan kopmadığını denetler — pano (dashboard/src/theme/ted-theme.scss),
modül şablonu (vendor/assets/module-template.html) ve derleyicinin `meta.accent` kuralı.
"""
import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from src.mcp_server import derleme, ornekler
from src.mcp_server.vendor_sync import VENDOR_DIR

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = json.loads((VENDOR_DIR / "assets" / "carbon-v11-authority.json").read_text(encoding="utf-8"))
LAYER = AUTHORITY["tedyLayer"]
TEMPLATE = (VENDOR_DIR / "assets" / "module-template.html").read_text(encoding="utf-8")
SCSS = (ROOT / "dashboard" / "src" / "theme" / "ted-theme.scss").read_text(encoding="utf-8")
THEMES = ("g10", "white", "g100")


def _block(selector: str) -> str:
    start = TEMPLATE.index(selector)
    open_brace = TEMPLATE.index("{", start)
    return TEMPLATE[open_brace + 1:TEMPLATE.index("}", open_brace)]


def _var(block: str, name: str) -> str | None:
    found = re.search(re.escape(name) + r"\s*:\s*([^;}]+)", block)
    return found.group(1).strip().lower() if found else None


@pytest.mark.parametrize("token", sorted(LAYER["tokens"]))
def test_template_carries_the_tedy_layer_values(token):
    spec = LAYER["tokens"][token]
    if spec["scope"] == "all":
        assert _var(_block(":root,[data-theme]"), "--" + token) == spec["g10"][1]
        assert spec["g10"] == spec["white"] == spec["g100"]
    else:
        for theme in THEMES:
            assert _var(_block(f'[data-theme="{theme}"]'), "--" + token) == spec[theme][1], theme


@pytest.mark.parametrize("token", sorted(LAYER["tokens"]))
def test_dashboard_declares_the_same_carbon_step(token):
    spec = LAYER["tokens"][token]
    step = spec[LAYER["dashboardTheme"]][0]
    found = re.search(re.escape(spec["dashboard"]) + r"\s*:\s*#\{colors\.\$([a-z0-9-]+)\}", SCSS)
    assert found, f"{spec['dashboard']} ted-theme.scss'te bir Carbon palet adımıyla tanımlı değil"
    assert found.group(1) == step


def test_hex_values_agree_with_the_carbon_palette_where_the_snapshot_has_the_family():
    palette = AUTHORITY["palette"]
    checked = 0
    for token, spec in LAYER["tokens"].items():
        for theme in THEMES:
            step, hex_value = spec[theme]
            family, _, grade = step.rpartition("-")
            if family in palette:
                checked += 1
                assert palette[family][grade] == hex_value, (token, theme, step)
    assert checked >= 10  # blue/green/red families are in the snapshot; cool-gray/orange are not


def test_dashboard_theme_is_one_value_everywhere():
    theme = LAYER["dashboardTheme"]
    main = (ROOT / "dashboard" / "src" / "main.tsx").read_text(encoding="utf-8")
    bridge = (ROOT / "dashboard" / "src" / "utils" / "moduleBridge.ts").read_text(encoding="utf-8")
    assert re.search(r'<Theme theme="([a-z0-9]+)"', main).group(1) == theme
    assert re.search(r"DASHBOARD_THEME: ModuleTheme = '([a-z0-9]+)'", bridge).group(1) == theme
    assert re.search(r'<html lang="tr" data-theme="([a-z0-9]+)">', TEMPLATE).group(1) == theme
    assert f"@include theme.theme(themes.${theme});" in SCSS


def test_subject_accents_match_the_template_and_keep_red_for_urgency():
    strong = re.search(r"const ACCENT_STRONG=\{(.*?)\};", TEMPLATE, re.S).group(1)
    keys = set(re.findall(r'"(#[0-9a-f]{6})":\[', strong))
    allowed = set(LAYER["subjectAccents"]["allowed"])
    reserved = set(LAYER["subjectAccents"]["reserved"])
    assert allowed == keys - reserved
    assert reserved == {"#da1e28"}
    subject = re.search(r"const SUBJECT_ACCENT=\{(.*?)\};", TEMPLATE, re.S).group(1)
    assert set(re.findall(r'"(#[0-9a-f]{6})"', subject)) <= allowed


@pytest.mark.parametrize("accent,accepted", [
    ("#d02670", True), ("#009d9a", True), ("#0F62FE", True),
    ("#da1e28", False), ("#DA1E28", False), ("#123456", False), (" #009d9a", False), (7, False), ("", False),
])
def test_compiler_accepts_only_tedy_subject_accents(accent, accepted):
    data = copy.deepcopy(ornekler.ornek("QUIZ"))
    data["meta"]["accent"] = accent
    errors = [e for e in derleme.sema_dogrula(data) if e.startswith("meta.accent")]
    assert (errors == []) is accepted, errors


def test_a_module_without_an_accent_takes_it_from_the_subject():
    data = copy.deepcopy(ornekler.ornek("QUIZ"))
    data["meta"].pop("accent", None)
    assert [e for e in derleme.sema_dogrula(data) if e.startswith("meta.accent")] == []


def test_token_sync_script_checks_the_tedy_layer():
    script = VENDOR_DIR / "scripts" / "sync_carbon_tokens.py"
    result = subprocess.run([sys.executable, str(script), "--check"], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout
    assert "Tedy katmanı: 17 değer denetlendi." in result.stdout
