"""ted-mcp gates on top of the vendored 16: G-BRIDGE (spec §5.5) and G-ATTRIB (spec §7).

Both read only the compiled HTML. G-ATTRIB depends on the compiler's deterministic output
(the asset JSON block, the attribution footer and bare-key `grounding: {…}` literals), which is
why it lives in ted-mcp rather than in the vendored validator.
"""
from __future__ import annotations

import html as html_lib
import json
import re
from typing import Any

BRIDGE_TYPES = frozenset({"edupedia:progress", "edupedia:restore"})
# The vendored template's THEME_STORE_KEY localStorage key (not a bridge message type).
STORAGE_KEYS = frozenset({"edupedia:theme"})
_SCRIPT_RE = re.compile(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", re.S | re.I)
_POST_RE = re.compile(r"([A-Za-z_$][\w$]*(?:\s*\.\s*[A-Za-z_$][\w$]*)*)\s*\.\s*postMessage\s*\(")
_STAR_RE = re.compile(r"postMessage\s*\([^;]*?,\s*[\"']\*[\"']\s*\)")
_TYPE_RE = re.compile(r"[\"'](edupedia:[a-z_]+)[\"']")
_ASSETS_RE = re.compile(r'<script type="application/json" id="edupedia-varliklar">(.*?)</script>', re.S)
_FOOTER_RE = re.compile(r'<footer id="edupedia-atif"[^>]*>(.*?)</footer>', re.S)
_GROUNDING_RE = re.compile(r"\bgrounding:\s*\{([^{}]*)\}")
_STRING = r'"(?:\\.|[^"\\])*"'


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _inline_js(html: str) -> str:
    return "\n".join(m.group("body") for m in _SCRIPT_RE.finditer(html)
                     if "application/json" not in m.group("attrs").lower())


def gate_bridge(html: str, R: Any) -> None:
    js = _inline_js(html)
    receivers = [re.sub(r"\s+", "", m.group(1)) for m in _POST_RE.finditer(js)]
    if not receivers:
        R.add("G-BRIDGE", "FAIL", "İlerleme köprüsü yok: modül window.parent'a edupedia:progress göndermiyor.")
        return
    issues = []
    wrong = sorted({r for r in receivers if r != "window.parent"})
    if wrong:
        issues.append("postMessage yalnız window.parent'a gönderilir (bulunan: " + ", ".join(wrong) + ")")
    if _STAR_RE.search(js):
        issues.append("postMessage hedef origin'i '*' olamaz")
    types = set(_TYPE_RE.findall(js))
    foreign = types - BRIDGE_TYPES - STORAGE_KEYS
    if foreign:
        issues.append("izinsiz mesaj tipi: " + ", ".join(sorted(foreign)))
    if not BRIDGE_TYPES <= types:
        issues.append("köprü edupedia:progress ve edupedia:restore tiplerinin ikisini de taşımalı")
    if not re.search(r"\.source\s*!==\s*window\.parent", js):
        issues.append("geri yükleme dinleyicisi mesaj kaynağını denetlemiyor")
    if not re.search(r"\.origin\s*!==\s*EDUPEDIA_PARENT_ORIGIN", js):
        issues.append("geri yükleme dinleyicisi origin'i denetlemiyor")
    if not re.search(r"window\.parent\s*!==\s*window", js):
        issues.append("bağımsız açılışta köprü kapanmıyor")
    if issues:
        R.add("G-BRIDGE", "FAIL", "; ".join(issues))
    else:
        R.add("G-BRIDGE", "PASS", "Köprü yalnız window.parent'a, sabit origin'e ve iki mesaj tipiyle konuşuyor; "
                                  "geri yükleme kaynak ve origin denetimli.")


def _licensed_sources(html: str) -> list[str]:
    sources = []
    for match in _GROUNDING_RE.finditer(html):
        body = match.group(1)
        license_m = re.search(r"\blicense:\s*(" + _STRING + ")", body)
        source_m = re.search(r"\bsource:\s*(" + _STRING + ")", body)
        if license_m and source_m:
            sources.append(json.loads(source_m.group(1)))
    return sources


def gate_attrib(html: str, R: Any) -> None:
    block = _ASSETS_RE.search(html)
    try:
        assets = json.loads(block.group(1)) if block else {}
    except ValueError:
        R.add("G-ATTRIB", "FAIL", "Varlık bloğu çözümlenemedi.")
        return
    if not isinstance(assets, dict):
        R.add("G-ATTRIB", "FAIL", "Varlık bloğu nesne değil.")
        return
    required: list[str] = []
    for asset_id, record in assets.items():
        credit = record.get("credit") if isinstance(record, dict) else None
        if not isinstance(credit, str) or not credit.strip():
            R.add("G-ATTRIB", "FAIL", f"{asset_id}: atıf metni yok.")
            return
        required.append(credit)
    required += _licensed_sources(html)
    if not required:
        R.add("G-ATTRIB", "PASS", "Lisanslı varlık veya lisanslı kaynak yok (uygulanmaz).", applicable=False)
        return
    footer = _FOOTER_RE.search(html)
    text = _collapse(html_lib.unescape(re.sub(r"<[^>]+>", " ", footer.group(1)))) if footer else ""
    missing = [item for item in required if _collapse(item) not in text]
    if missing:
        R.add("G-ATTRIB", "FAIL", "Altbilgide eksik atıf: " + "; ".join(missing[:5]))
    else:
        R.add("G-ATTRIB", "PASS", f"{len(required)} lisanslı varlık/kaynağın atfı altbilgide.")
