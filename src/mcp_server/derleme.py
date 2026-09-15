"""edupedia_derle core: MODULE_DATA -> self-contained module HTML (spec §5.2; plan K-P4..K-P9).

Pure functions and a CLI; no network and no MCP. derle_araci.py wraps this with the run record,
the asset store, the draft store and the gate runner.
"""
from __future__ import annotations

import argparse
import copy
import html as html_lib
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from src.mcp_server import gates, ornekler, sablon

MODES = ornekler.MODES
MAX_INPUT_BYTES = 400_000
ASSET_BUDGET_BYTES = 2_400_000
SEGMENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
SLOT_RE = re.compile(r"^([A-Za-z0-9_-]{1,64})\.(visual|audio)$")
ASSET_ID_RE = re.compile(r"^[0-9a-f]{16}$")
_IDENT_RE = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")
_FORBIDDEN = (
    (re.compile(r"<\s*/?\s*script", re.I), "script etiketi"),
    (re.compile(r"<\s*(?:iframe|object|embed|form|base|meta|link)\b", re.I), "yasak etiket"),
    (re.compile(r"<[^>]*\son[a-z]+\s*=", re.I), "satır içi olay işleyicisi"),
    (re.compile(r"javascript\s*:", re.I), "javascript: adresi"),
    (re.compile(r"vbscript\s*:", re.I), "javascript: adresi"),
    # F2 (fix round 1): a `srcset` candidate list can smuggle a remote URL anywhere after the
    # first candidate ("data:...low-res 1x, https://evil.example/x.png 2x"); this pattern scans
    # the whole quoted/unquoted attribute value, not just the text immediately after `=`.
    (re.compile(r"\bsrcset\s*=\s*(?:\"[^\"]*|'[^']*|[^\s>]*)(?:https?:|//)", re.I), "dış kaynak bağlantısı"),
    (re.compile(r"\b(?:src|href|xlink:href|action|formaction|poster|srcset)\s*=\s*[\"']?\s*(?:https?:|//)", re.I),
     "dış kaynak bağlantısı"),
    (re.compile(r"url\(\s*[\"']?\s*(?:https?:|//)", re.I), "CSS dış kaynağı"),
    # F1: `url(data:text/html,...)` etc. — only `data:image/...` is allowed (legitimate inline images).
    (re.compile(r"url\(\s*[\"']?\s*data:(?!image/)", re.I), "CSS dış kaynağı"),
    (re.compile(r"@import", re.I), "CSS @import"),
    (re.compile(r"expression\s*\(", re.I), "CSS expression"),
)
_SCAN_STRIP_RE = re.compile(r"[\t\n\r\x00]")


class DerlemeHatasi(Exception):
    def __init__(self, status: str, **detay: Any) -> None:
        super().__init__(status)
        self.status = status
        self.detay = detay


@dataclass(frozen=True)
class GomuluVarlik:
    asset_id: str
    tur: str
    mime: str
    data_uri: str
    bayt: int
    credit: str
    lisans: str
    alt: str
    kaynak: str


def _double_quoted_string(text: str) -> str:
    """Ruling T7-3's double-quoted JS string literal: valid JS *and* valid JSON.

    gates_ek.gate_attrib json.loads-parses grounding source/credit literals straight out of the
    compiled HTML, so every escape here must be legal in both languages. "<\\!--" (T7-3's
    starting point) is legal JS but not legal JSON; "\\u003c!--" is legal in both.
    """
    out = json.dumps(text, ensure_ascii=False)
    out = out.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    out = re.sub(r"</(script)", r"<\\/\1", out, flags=re.I)
    return out.replace("<!--", "\\u003c!--")


def _template_literal_string(text: str) -> str:
    """F3 (fix round 1): backtick JS template literal for HTML/SVG fragments.

    Used only for values containing both '"' and '<' (see `_js_string`) — e.g. an inline SVG
    diagram authored with double-quoted attributes (`<svg role="img" ...>`). A JSON-double-quoted
    string necessarily backslash-escapes every embedded '"', which defeats the vendored gates'
    raw-text scans for a literal, unescaped `role="img"` (G-SVG's `_svg_accessible`). A template
    literal never needs to escape '"', so it survives that scan unescaped, exactly like the
    vendored template's own authoring convention for the same content
    (`module-template.html`'s `ref:` fields use backtick strings for this reason).

    Escaping order matters: the backslash escape must run first, so the backslashes the later
    escapes introduce (`\\``, `\\${`, `<\\/script`, `\\u003c!--`, `\\u2028`, `\\u2029`) are never
    themselves re-escaped by it.
    """
    out = text.replace("\\", "\\\\")
    out = out.replace("`", "\\`")
    out = out.replace("${", "\\${")
    out = re.sub(r"</(script)", r"<\\/\1", out, flags=re.I)
    out = out.replace("<!--", "\\u003c!--")
    out = out.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return f"`{out}`"


def _js_string(text: str) -> str:
    """Bare-key JS literal's string encoding: template literal for HTML/SVG fragments (F3), the
    T7-3 double-quoted JSON form for everything else (so free text like `sourceCitation` and the
    vendored G-EXAM regexes' `["\\']`-delimited extraction keep seeing quote-delimited strings)."""
    if '"' in text and "<" in text:
        return _template_literal_string(text)
    return _double_quoted_string(text)


def _js_key(key: str) -> str:
    # A template literal is not valid JS object-key syntax on its own (`` `foo`: 1 `` is a syntax
    # error without a computed-property `[...]` wrapper this compiler doesn't emit), so a
    # non-identifier key always uses the double-quoted form regardless of its content.
    return key if _IDENT_RE.fullmatch(key) else _double_quoted_string(key)


def js_literal(value: Any, depth: int = 0) -> str:
    """Bare-key JS literal in the authoring shape the vendored regex gates expect.

    Objects at depth 0-1 and arrays at depth 0-2 are multi-line; deeper values stay on one line.
    """
    pad, inner = "  " * depth, "  " * (depth + 1)
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("sayı sonlu olmalı")
        return json.dumps(value)
    if isinstance(value, str):
        return _js_string(value)
    if isinstance(value, dict):
        items = [f"{_js_key(str(k))}: {js_literal(v, depth + 1)}" for k, v in value.items()]
        if not items:
            return "{}"
        if depth <= 1:
            return "{\n" + ",\n".join(inner + item for item in items) + "\n" + pad + "}"
        return "{" + ", ".join(items) + "}"
    if isinstance(value, list):
        items = [js_literal(v, depth + 1) for v in value]
        if not items:
            return "[]"
        if depth <= 2:
            return "[\n" + ",\n".join(inner + item for item in items) + "\n" + pad + "]"
        return "[" + ", ".join(items) + "]"
    raise ValueError(f"desteklenmeyen değer türü: {type(value).__name__}")


def _walk_strings(value: Any, path: str = "MODULE_DATA"):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_strings(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_strings(item, f"{path}[{index}]")


def _normalize_for_scan(text: str) -> str:
    """F1 (fix round 1): undo what the raw text alone hides from the scan.

    The vendored engine assigns `teach.body` etc. through `.innerHTML`, so the browser's HTML
    parser decodes character references (`&#106;`, `&colon;`, ...) in attribute values before the
    URL parser ever sees the string; and the WHATWG URL parser strips ASCII tab/CR/LF (and a
    stray NUL) from a URL string before scheme-sniffing. So `java&#9;script:` and
    `&#106;avascript:` are both live `javascript:` URLs even though neither contains the literal
    substring "javascript:" — scanning only the raw text misses them.
    """
    return _SCAN_STRIP_RE.sub("", html_lib.unescape(text))


def guvenlik_tara(data: Any) -> list[str]:
    errors = []
    for path, text in _walk_strings(data):
        normalized = _normalize_for_scan(text)
        for pattern, label in _FORBIDDEN:
            if pattern.search(text) or pattern.search(normalized):
                errors.append(f"{path}: {label}")
                break
    return errors[:50]


def _text(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def sema_dogrula(data: Any) -> list[str]:
    if not isinstance(data, dict):
        return ["MODULE_DATA bir nesne olmalı"]
    meta = data.get("meta")
    if not isinstance(meta, dict):
        return ["meta nesnesi zorunlu"]
    errors = [f"meta.{key} zorunlu" for key in ("title", "subject", "gradeLevel", "sourceCitation")
              if not _text(meta.get(key))]
    if meta.get("mode") not in MODES:
        errors.append("meta.mode geçersiz; izinli: " + ", ".join(MODES))
    if "attributions" in meta:
        errors.append("meta.attributions derleyici tarafından üretilir; MODULE_DATA'da yazılmaz")
    if not isinstance(data.get("rewards"), dict):
        errors.append("rewards nesnesi zorunlu")
    segments = data.get("segments")
    if not isinstance(segments, list) or not segments:
        errors.append("segments boş olmayan bir dizi olmalı")
    else:
        seen: set[str] = set()
        for index, seg in enumerate(segments):
            if not isinstance(seg, dict) or not _text(seg.get("type")):
                errors.append(f"segments[{index}].type zorunlu")
                continue
            sid = seg.get("id")
            # Ruling T7-1: .fullmatch() — .match() would silently accept a trailing newline.
            if not isinstance(sid, str) or not SEGMENT_ID_RE.fullmatch(sid):
                errors.append(f"segments[{index}].id geçersiz")
                continue
            if sid in seen:
                errors.append(f"segments[{index}].id yinelenmiş: {sid}")
            seen.add(sid)
    if not isinstance(data.get("curriculum"), dict):
        errors.append("curriculum bloğu zorunlu (müfredat dayanağı; spec §5.1 hibrit kuralı)")
    verification = data.get("verification")
    if not isinstance(verification, dict):
        errors.append("verification bloğu zorunlu (G-VERIFY)")
    else:
        # F4 (fix round 1): gates_ek captures `grounding: {…}` bodies with a brace-balance-blind
        # `[^{}]*`, and (per F3) `_js_string` only ever emits a template literal — which
        # gates_ek's double-quote-only string regex cannot read — for a value containing both
        # '"' and '<'. Forbidding braces, '<' and backtick in grounding source/license closes
        # both gaps at the schema boundary, before either regex ever sees the text.
        claims = verification.get("claims")
        if isinstance(claims, list):
            for index, claim in enumerate(claims):
                grounding = claim.get("grounding") if isinstance(claim, dict) else None
                if isinstance(grounding, dict) and isinstance(grounding.get("license"), str):
                    texts = [grounding["license"]]
                    source = grounding.get("source")
                    if isinstance(source, str):
                        texts.append(source)
                    if any(ch in t for t in texts for ch in "{}<`"):
                        errors.append("verification.claims[" + str(index) + "].grounding: "
                                      "source/license içinde { } < ` kullanılamaz")
    ted = meta.get("tedLink")
    if ted is not None and not (isinstance(ted, dict) and ted.get("kind") in ("exam", "homework")
                                and isinstance(ted.get("id"), str) and 0 < len(ted["id"]) <= 128):
        errors.append("meta.tedLink {kind: exam|homework, id} olmalı")
    assets = meta.get("assets")
    if assets is not None:
        if not isinstance(assets, list):
            errors.append("meta.assets dizi olmalı")
        else:
            for index, ref in enumerate(assets):
                # Ruling T7-1: .fullmatch() on both ASSET_ID_RE and SLOT_RE.
                if not (isinstance(ref, dict) and isinstance(ref.get("asset_id"), str)
                        and ASSET_ID_RE.fullmatch(ref["asset_id"]) and isinstance(ref.get("slot"), str)
                        and SLOT_RE.fullmatch(ref["slot"])):
                    errors.append(f"meta.assets[{index}] {{asset_id, slot: '<teachId>.visual|audio'}} olmalı")
    return errors


def girdi_boyutu(data: Any) -> int:
    """UTF-8 size of MODULE_DATA as compact JSON — the unit of the 400 KB budget."""
    try:
        return len(json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise DerlemeHatasi("sema_hatasi", hatalar=[f"JSON'a çevrilemeyen değer: {exc}"]) from exc


def varlik_bagla(data: dict[str, Any], varliklar: Mapping[str, GomuluVarlik]) -> tuple[dict[str, Any], list[GomuluVarlik]]:
    out = copy.deepcopy(data)
    by_id = {seg["id"]: seg for seg in out["segments"]}
    used: list[GomuluVarlik] = []
    for ref in out["meta"].get("assets") or []:
        record = varliklar.get(ref["asset_id"])
        if record is None:
            raise DerlemeHatasi("varlik_bulunamadi", asset_id=ref["asset_id"])
        # Ruling T7-1: .fullmatch() (SLOT_RE pattern unchanged).
        match = SLOT_RE.fullmatch(ref["slot"])
        segment_id, field = match.groups()
        segment = by_id.get(segment_id)
        if segment is None:
            raise DerlemeHatasi("slot_segmenti_yok", slot=ref["slot"])
        if segment.get("type") != "teach":
            raise DerlemeHatasi("slot_yalniz_teach", slot=ref["slot"])
        if field == "visual":
            if record.tur not in ("image", "video"):
                raise DerlemeHatasi("slot_tur_uyusmazligi", slot=ref["slot"], tur=record.tur)
            if segment.get("visual"):
                raise DerlemeHatasi("slot_dolu", slot=ref["slot"])
            segment["visual"] = {"kind": record.tur, "asset": record.asset_id, "alt": record.alt}
        else:
            if record.tur not in ("ses", "muzik"):
                raise DerlemeHatasi("slot_tur_uyusmazligi", slot=ref["slot"], tur=record.tur)
            if segment.get("audio"):
                raise DerlemeHatasi("slot_dolu", slot=ref["slot"])
            segment["audio"] = {"asset": record.asset_id, "label": "Seslendirme" if record.tur == "ses" else "Müzik"}
        if record not in used:
            used.append(record)
    total = sum(r.bayt for r in used)
    if total > ASSET_BUDGET_BYTES:
        raise DerlemeHatasi("varlik_butcesi_asildi", bayt=total, sinir=ASSET_BUDGET_BYTES)
    return out, used


def atiflar(data: dict[str, Any], used: list[GomuluVarlik]) -> list[dict[str, str]]:
    rows = [{"metin": r.credit, "lisans": r.lisans, "kaynak": r.kaynak, "asset_id": r.asset_id} for r in used]
    seen = {row["metin"] for row in rows}
    for claim in (data.get("verification") or {}).get("claims") or []:
        grounding = claim.get("grounding") if isinstance(claim, dict) else None
        if isinstance(grounding, dict) and _text(grounding.get("license")) and _text(grounding.get("source")):
            metin = f"Kaynak: {grounding['source'].strip()} — {grounding['license'].strip()}"
            if metin not in seen:
                rows.append({"metin": metin, "lisans": grounding["license"].strip(), "kaynak": "verification"})
                seen.add(metin)
    voice = gates.voice_pattern()
    for row in rows:
        if voice.search(row["metin"]):
            raise DerlemeHatasi("atif_dil_kurali", metin=row["metin"],
                                neden="Öğrenci yüzeyinde kitap/sayfa göndermesi yasak (G-VOICE); kaynak adını yeniden yaz.")
    return rows


def _footer(rows: list[dict[str, str]]) -> str:
    if not rows:
        return ""
    lines = "".join(f"<p>{html_lib.escape(row['metin'], quote=False)}</p>" for row in rows)
    return ('<footer id="edupedia-atif" class="edupedia-atif" '
            'style="padding:1rem;color:var(--cds-text-secondary);font-size:0.75rem">'
            "<p><strong>Atıflar</strong></p>" + lines + "</footer>")


def _assets_block(used: list[GomuluVarlik]) -> str:
    if not used:
        return ""
    payload = {r.asset_id: {"uri": r.data_uri, "tur": r.tur, "credit": r.credit} for r in used}
    # Ruling T7-2: escape every "<" (not just "</") as \u003c. The controller measured that a
    # credit string containing "<!--<script>" inside this <script type="application/json">
    # element makes Chromium's HTML tokenizer swallow the following engine <script> into the
    # JSON element (page ends up with 1 script instead of 2) — the module engine never runs.
    # Credits come from external media providers and are not covered by guvenlik_tara. Escaping
    # every "<" removes the character the tokenizer keys on, structurally, rather than trying to
    # anticipate every "</script"-adjacent spelling.
    text = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    return f'<script type="application/json" id="edupedia-varliklar">{text}</script>'


def derle(data: Any, varliklar: Mapping[str, GomuluVarlik] | None, parent_origin: str) -> str:
    size = girdi_boyutu(data)
    if size > MAX_INPUT_BYTES:
        raise DerlemeHatasi("cok_buyuk", bayt=size, sinir=MAX_INPUT_BYTES)
    errors = sema_dogrula(data)
    if isinstance(data, dict):
        errors += guvenlik_tara(data)
    if errors:
        raise DerlemeHatasi("sema_hatasi", hatalar=errors)
    bound, used = varlik_bagla(data, varliklar or {})
    bound["meta"]["attributions"] = atiflar(bound, used)
    template = sablon.engine_template(parent_origin)
    start = template.index(sablon.MODULE_DATA_START)
    end = template.index(sablon.ENGINE_MARKER, start)
    html = template[:start] + "const MODULE_DATA = " + js_literal(bound) + ";\n" + template[end:]
    html = html.replace(sablon.ASSETS_SLOT, _assets_block(used), 1)
    return html.replace(sablon.ATTRIB_SLOT, _footer(bound["meta"]["attributions"]), 1)


def kapi_ozeti(report: Mapping[str, Mapping[str, Any]]) -> dict[str, int]:
    counts = {"pass": 0, "warn": 0, "fail": 0, "skipped": 0}
    for row in report.values():
        counts[str(row.get("status", "")).lower()] += 1
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MODULE_DATA -> modül HTML (varlıksız derleme)")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--ornek", choices=MODES)
    source.add_argument("--girdi", type=Path)
    parser.add_argument("--cikti", type=Path, required=True)
    parser.add_argument("--ebeveyn-origin", default="https://tedy.online")
    args = parser.parse_args(argv)
    data = ornekler.ornek(args.ornek) if args.ornek else json.loads(args.girdi.read_text(encoding="utf-8"))
    try:
        html = derle(data, {}, args.ebeveyn_origin)
    except DerlemeHatasi as exc:
        print(json.dumps({"status": exc.status, **exc.detay}, ensure_ascii=False))
        return 2
    report = gates.run_gates(html)
    summary = kapi_ozeti(report)
    args.cikti.parent.mkdir(parents=True, exist_ok=True)
    args.cikti.write_text(html, encoding="utf-8")
    print(json.dumps({"kapi_ozeti": summary, "bayt": len(html.encode("utf-8")),
                      "fail": sorted(g for g, v in report.items() if v["status"] == "FAIL")}, ensure_ascii=False))
    return 1 if summary["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
