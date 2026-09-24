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
# Allowed but not required: the dashboard's appearance message (parent → module, the Carbon theme
# the module adopts). Modules compiled before it existed stay valid without it.
OPTIONAL_BRIDGE_TYPES = frozenset({"edupedia:appearance"})
# The vendored template's THEME_STORE_KEY localStorage key (not a bridge message type).
STORAGE_KEYS = frozenset({"edupedia:theme"})
_SCRIPT_RE = re.compile(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", re.S | re.I)
# perf fix (controller ruling): the original _POST_RE captured the whole dotted receiver chain
# via an unanchored finditer over the ENTIRE script body — a single long run of word characters
# anywhere in that body (e.g. a compiled MODULE_DATA string literal) makes the receiver group's
# backtracking retry at every position of that run, which is quadratic in the script length.
# `_POST_CALL_RE` only ever looks for the literal ".postMessage(" (no backtracking group), and
# `_receiver_before` then reads the receiver by a plain backward character scan bounded to
# `_RECEIVER_WINDOW` chars — bounded work per occurrence, however large the rest of the script is.
_POST_CALL_RE = re.compile(r"\.\s*postMessage\s*\(")
_RECEIVER_WINDOW = 256
_RECEIVER_UNREADABLE = "<okunamayan-alici>"
# Same shape of bug for the '*' target check: the old _STAR_RE's `[^;]*?` had to scan forward,
# per `postMessage(` occurrence, over an unbounded amount of text with no ';' to stop it (e.g.
# many `postMessage(` calls in a row). `_POSTMESSAGE_CALL_RE` is a plain literal match; the
# bounded `{0,512}?` after it caps the forward scan to a small constant per occurrence.
_POSTMESSAGE_CALL_RE = re.compile(r"postMessage\s*\(")
_STAR_ARG_RE = re.compile(r"[^;]{0,512}?,\s*[\"']\*[\"']\s*\)")
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


def _receiver_before(js: str, dot_pos: int, window: int = _RECEIVER_WINDOW) -> str | None:
    """The dotted identifier chain immediately ending at `dot_pos` (the '.' before `postMessage`),
    read by a plain backward character scan — no regex group is retried across the chain, so the
    cost is O(chain length), never O(script length). Returns None when the text immediately
    before `dot_pos` is not such a chain, or the chain may extend past `window` characters (the
    caller treats this the same as a foreign receiver — FAIL, never a silent "no bridge" pass).
    """
    limit = max(0, dot_pos - window)
    i = dot_pos
    chain_start = dot_pos
    while True:
        j = i
        while j > limit and js[j - 1] in " \t\r\n":
            j -= 1
        k = j
        while k > limit and (js[k - 1].isalnum() or js[k - 1] in "_$"):
            k -= 1
        if k == j:
            return None  # no identifier where the chain (or its start) was expected
        if k == limit and limit > 0:
            return None  # identifier may continue past the window — unreadable
        if not (js[k].isalpha() or js[k] in "_$"):
            return None  # cannot start with a digit
        chain_start = k
        i = k
        m = i
        while m > limit and js[m - 1] in " \t\r\n":
            m -= 1
        if m > limit and js[m - 1] == ".":
            i = m - 1
            continue
        break
    return re.sub(r"\s+", "", js[chain_start:dot_pos])


def _receivers(js: str) -> list[str]:
    return [_receiver_before(js, m.start()) or _RECEIVER_UNREADABLE for m in _POST_CALL_RE.finditer(js)]


def _has_star_target(js: str) -> bool:
    return any(_STAR_ARG_RE.match(js, m.end()) for m in _POSTMESSAGE_CALL_RE.finditer(js))


def gate_bridge(html: str, R: Any) -> None:
    js = _inline_js(html)
    receivers = _receivers(js)
    if not receivers:
        R.add("G-BRIDGE", "FAIL", "İlerleme köprüsü yok: modül window.parent'a edupedia:progress göndermiyor.")
        return
    issues = []
    wrong = sorted({r for r in receivers if r != "window.parent"})
    if wrong:
        issues.append("postMessage yalnız window.parent'a gönderilir (bulunan: " + ", ".join(wrong) + ")")
    if _has_star_target(js):
        issues.append("postMessage hedef origin'i '*' olamaz")
    types = set(_TYPE_RE.findall(js))
    foreign = types - BRIDGE_TYPES - OPTIONAL_BRIDGE_TYPES - STORAGE_KEYS
    if foreign:
        issues.append("izinsiz mesaj tipi: " + ", ".join(sorted(foreign)))
    if not BRIDGE_TYPES <= types:
        issues.append("köprü edupedia:progress ve edupedia:restore tiplerinin ikisini de taşımalı")
    if not re.search(r"\.source\s*!==\s*window\.parent", js):
        issues.append("ebeveyn dinleyicisi (geri yükleme/görünüm) mesaj kaynağını denetlemiyor")
    if not re.search(r"\.origin\s*!==\s*EDUPEDIA_PARENT_ORIGIN", js):
        issues.append("ebeveyn dinleyicisi (geri yükleme/görünüm) origin'i denetlemiyor")
    if not re.search(r"window\.parent\s*!==\s*window", js):
        issues.append("bağımsız açılışta köprü kapanmıyor")
    if issues:
        R.add("G-BRIDGE", "FAIL", "; ".join(issues))
    else:
        R.add("G-BRIDGE", "PASS", "Köprü yalnız window.parent'a, sabit origin'e ve izinli mesaj tipleriyle "
                                  "konuşuyor; ebeveyn mesajları (geri yükleme, görünüm) kaynak ve origin denetimli.")


def _decode_js_string(body: str, start: int) -> tuple[str, int] | tuple[None, None]:
    """Decode a JS string/template literal in `body` starting at the opening-quote index `start`.

    Returns (decoded_text, index_after_closing_quote), or (None, None) if the literal is
    unterminated, contains a raw line break inside a `"`/`'` literal, contains an unescaped `${`
    inside a template literal, contains a `\\u`/`\\x` escape that does not decode, or contains a
    legacy octal escape (`\\1`-`\\9`, or `\\0` followed by a digit). Never raises.
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
            if nc == "x":
                # Fix F5 (review "New-Important"): \xHH is a real, fixed-length JS escape (the
                # code point of the two hex digits), not a generic identity escape — it must not
                # fall through to the "any other \x" bucket below, which used to decode it to the
                # literal letter 'x' followed by the two digits as plain text.
                hexpart = body[i + 2:i + 4]
                if len(hexpart) != 2 or not re.fullmatch(r"[0-9a-fA-F]{2}", hexpart):
                    return None, None  # truncated \xH or \x at end of literal
                out.append(chr(int(hexpart, 16)))
                i += 4
                continue
            if nc == "0":
                if body[i + 2:i + 3].isdigit():
                    return None, None  # \0<digit> — legacy octal escape, not in our accepted set
                out.append("\0")
                i += 2
                continue
            if nc in "123456789":
                # Fix F5: \1-\9 are legacy octal escapes (sloppy-mode only; strict mode and
                # template literals always throw) — undecodable, fail closed, never identity.
                return None, None
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
