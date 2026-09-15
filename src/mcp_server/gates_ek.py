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
# Fix F2 (review I2): only a *real* `type="application/json"` attribute excludes a <script> from
# the bridge scan — not any attribute (e.g. `data-note="..."`) that merely contains the text. The
# unquoted alternative's lookahead relies on `_SCRIPT_RE`'s `attrs` group never containing '>'
# (it stops there), so end-of-string is a valid boundary for an unquoted value at the tag's end.
_JSON_TYPE_RE = re.compile(
    r'(?:^|\s)type\s*=\s*(?:"application/json"|\'application/json\'|application/json(?=\s|/|$))',
    re.I,
)
_ASSETS_RE = re.compile(r'<script type="application/json" id="edupedia-varliklar">(.*?)</script>', re.S)
_FOOTER_RE = re.compile(r'<footer id="edupedia-atif"[^>]*>(.*?)</footer>', re.S)
_GROUNDING_RE = re.compile(r"\bgrounding:\s*\{([^{}]*)\}")
_LICENSE_KEY_RE = re.compile(r"\blicense\s*:")
_SOURCE_START_RE = re.compile(r"\bsource\s*:\s*(['\"`])")
_LICENSE_START_RE = re.compile(r"\blicense\s*:\s*(['\"`])")

# Fix F1 (review C1 + I1): strict JS string/template-literal decoder for grounding's `source`
# and `license` values. No eval; every escape below is handled explicitly, and anything that does
# not decode cleanly makes the caller fail closed instead of raising or silently skipping.
_ESCAPE_MAP = {
    "\\": "\\", '"': '"', "'": "'", "`": "`", "/": "/", "$": "$",
    "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v",
}
_LINE_TERMINATORS = ("\n", "\r", " ", " ")


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _inline_js(html: str) -> str:
    return "\n".join(m.group("body") for m in _SCRIPT_RE.finditer(html)
                     if not _JSON_TYPE_RE.search(m.group("attrs")))


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


def _decode_js_string(body: str, start: int) -> tuple[str, int] | tuple[None, None]:
    """Decode a JS string/template literal in `body` starting at the opening-quote index `start`.

    Returns (decoded_text, index_after_closing_quote), or (None, None) if the literal is
    unterminated, contains a raw line break inside a `"`/`'` literal, contains an unescaped `${`
    inside a template literal, or contains a `\\u` escape that does not decode. Never raises.
    """
    quote = body[start]
    i = start + 1
    n = len(body)
    out: list[str] = []
    while i < n:
        c = body[i]
        if c == quote:
            return "".join(out), i + 1
        if c == "\\":
            if i + 1 >= n:
                return None, None
            nc = body[i + 1]
            if nc == "\n":
                i += 2
                continue
            if nc == "\r":
                i += 3 if body[i + 2:i + 3] == "\n" else 2
                continue
            if nc in (" ", " "):
                i += 2
                continue
            if nc == "u":
                if body[i + 2:i + 3] == "{":
                    end = body.find("}", i + 3)
                    if end == -1:
                        return None, None
                    hexpart = body[i + 3:end]
                    if not hexpart or not re.fullmatch(r"[0-9a-fA-F]+", hexpart):
                        return None, None
                    codepoint = int(hexpart, 16)
                    if codepoint > 0x10FFFF:
                        return None, None
                    out.append(chr(codepoint))
                    i = end + 1
                    continue
                hexpart = body[i + 2:i + 6]
                if len(hexpart) != 4 or not re.fullmatch(r"[0-9a-fA-F]{4}", hexpart):
                    return None, None
                out.append(chr(int(hexpart, 16)))
                i += 6
                continue
            if nc == "0":
                if body[i + 2:i + 3].isdigit():
                    return None, None  # legacy octal escape — not in our accepted set
                out.append("\0")
                i += 2
                continue
            if nc in _ESCAPE_MAP:
                out.append(_ESCAPE_MAP[nc])
                i += 2
                continue
            # any other \x identity escape decodes to x, as JS does
            out.append(nc)
            i += 2
            continue
        if quote != "`" and c in _LINE_TERMINATORS:
            return None, None
        if quote == "`" and c == "$" and body[i + 1:i + 2] == "{":
            return None, None
        out.append(c)
        i += 1
    return None, None  # unterminated literal


def _decode_value(body: str, start_re: re.Pattern[str]) -> tuple[bool, str | None]:
    """Find `key: <literal>` via `start_re` and decode the literal.

    Returns (found, decoded). found=False means the key has no immediately-following literal in
    one of the three accepted forms. found=True with decoded=None means the literal was found but
    failed to decode (see `_decode_js_string`).
    """
    m = start_re.search(body)
    if not m:
        return False, None
    decoded, _end = _decode_js_string(body, m.start(1))
    return True, decoded


def _licensed_sources(html: str) -> tuple[list[str], bool]:
    """Decoded `source` strings from every licensed `grounding: {...}` body (has a `license` key).

    Returns (sources, ok). ok=False means at least one licensed body's `source` or `license`
    value is missing, is not one of the three accepted literal forms, or does not decode —
    callers must FAIL rather than silently drop it or raise.
    """
    sources: list[str] = []
    for match in _GROUNDING_RE.finditer(html):
        body = match.group(1)
        if not _LICENSE_KEY_RE.search(body):
            continue  # not licensed, unchanged
        found_license, license_val = _decode_value(body, _LICENSE_START_RE)
        found_source, source_val = _decode_value(body, _SOURCE_START_RE)
        if not found_license or license_val is None or not found_source or source_val is None:
            return sources, False
        sources.append(source_val)
    return sources, True


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
    missing_credit: list[str] = []
    for asset_id, record in assets.items():
        credit = record.get("credit") if isinstance(record, dict) else None
        if not isinstance(credit, str) or not credit.strip():
            missing_credit.append(str(asset_id))
            continue
        required.append(credit)
    if missing_credit:
        # Fix F3 (review M4): report every asset missing a credit, not just the first.
        detail = "; ".join(f"{aid}: atıf metni yok." for aid in missing_credit[:5])
        R.add("G-ATTRIB", "FAIL", detail)
        return
    licensed_sources, ok = _licensed_sources(html)
    if not ok:
        R.add("G-ATTRIB", "FAIL", "lisanslı kaynak çözümlenemedi.")
        return
    required += licensed_sources
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
