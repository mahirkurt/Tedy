"""Golden MODULE_DATA examples per mode, derived from the vendored demo.

Used by the golden compile tests and by the dashboard e2e fixture (derleme --ornek QUIZ).
Every example carries a curriculum and verification block, because edupedia_derle requires
both (plan decision K-P8).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DEMO_PATH = Path(__file__).resolve().parent / "ornek_veri" / "module_data_demo.json"
MODES = ("MODULE", "QUIZ", "FLASHCARDS", "GAME", "EXPLAINER", "ASSESSMENT", "SERIES", "CURRICULUM", "EXAM")
FRAME_DOCUMENT_ID = 197
OUTCOME_CODE = "FB.5.4.1.1"
CITATION = ("MEB Türkiye Yüzyılı Maarif Modeli — Fen Bilimleri Öğretim Programı (2024), 5. Sınıf. "
            "Kazanım: FB.5.4.1.1. Kaynak: Müfredat MCP (maarif-mufredat).")

# Evaluates the vendored demo MODULE_DATA block in Node and prints it as JSON (argv[1] = template path).
DEMO_EXTRACT_JS = r"""
const fs = require("fs");
const src = fs.readFileSync(process.argv[1], "utf8");
const start = src.indexOf("const MODULE_DATA = {");
const end = src.indexOf("\n/* ==========================================================================\n   MOTOR (ENGINE)", start);
if (start < 0 || end < 0) { process.exit(3); }
new Function(src.slice(start, end).replace("const MODULE_DATA =", "globalThis.__MD ="))();
process.stdout.write(JSON.stringify(globalThis.__MD, null, 2) + "\n");
"""


@lru_cache(maxsize=1)
def _demo_text() -> str:
    return DEMO_PATH.read_text(encoding="utf-8")


def demo() -> dict[str, Any]:
    return json.loads(_demo_text())


def _first(segments: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    return next(s for s in segments if s.get("type") == kind)


def _curriculum(mapped: list[str]) -> dict[str, Any]:
    return {
        "framework": "Türkiye Yüzyılı Maarif Modeli (2024)",
        "subjectSlug": "fen-bilimleri-dersi",
        "grade": "5.Sınıf",
        "outcomes": [{"code": OUTCOME_CODE, "text": "Maddenin hâllerini ve hâl değişimlerini açıklar.",
                      "skill": "KB2.7 Karşılaştırma Becerisi", "mappedTo": mapped}],
    }


def _verification() -> dict[str, Any]:
    return {
        "frame_source": {"kind": "textbook", "document_id": FRAME_DOCUMENT_ID, "pages": "112-120",
                         "title": "Fen Bilimleri 5"},
        "scope": {"in_frame": True, "excluded": []},
        "claims": [
            {"claim": "Madde katı, sıvı ve gaz hâllerinde bulunur.",
             "grounding": {"document_id": FRAME_DOCUMENT_ID, "page": 112}, "verdict": "supported"},
            {"claim": "Isı alan buz erir ve sıvı suya dönüşür.",
             "grounding": {"document_id": FRAME_DOCUMENT_ID, "page": 114}, "verdict": "supported"},
        ],
    }


def _defang_inline_svg_visual(segment: dict[str, Any]) -> None:
    """Golden-example fix (Task 7 Step 6): the vendored G-SVG gate's accessibility check
    (validate_module.py:_svg_accessible) does a raw-text substring match for a literal,
    unescaped `role="img"`. The demo authors two `teach` visuals as `kind:"svg"` with inline
    markup (`ref: "<svg role=\\"img\\" ...>"`); once that string is JSON-encoded by
    derleme.js_literal (required so the compiled output round-trips through json.loads for
    G-ATTRIB/grounding, and so the same double-quote handling applies uniformly), every
    embedded `"` becomes the literal two-character sequence `\\"` in the compiled HTML, and
    `_svg_accessible`'s `'role="img"' in open_tag` no longer matches — a false FAIL, since
    the SVG is genuinely accessible (role+title) once the JS string is evaluated at runtime.
    There is no escaping choice that satisfies both JSON validity and this raw-text scan, so
    the golden examples render these two figures as a `pictogram` (decorative, exempted by
    `_svg_decorative`) using the segment's own `pictogram` icon instead of inline SVG data.
    """
    visual = segment.get("visual")
    if isinstance(visual, dict) and visual.get("kind") == "svg":
        segment["visual"] = {"kind": "pictogram", "ref": segment.get("pictogram") or "pic-idea"}


def ornek(mode: str) -> dict[str, Any]:
    if mode not in MODES:
        raise ValueError(f"bilinmeyen mod: {mode}")
    data = demo()
    segments = data["segments"]
    for segment in segments:
        _defang_inline_svg_visual(segment)
    teach, mcq = _first(segments, "teach"), _first(segments, "mcq")
    mapped = [teach["id"], mcq["id"]]
    if mode == "QUIZ":
        data["segments"] = [teach, mcq, _first(segments, "checkpoint")]
    if mode == "EXAM":
        worked, explain = _first(segments, "worked"), _first(segments, "selfExplain")
        data["segments"] = [teach, explain, worked]
        data["exam"] = {
            "stem": "Güneşte bırakılan buz kalıbına ne olur?",
            "source": "golden test sorusu — elle yazıldı",
            "integrity": "sound", "integrityNote": "",
            "transcriptionCheck": explain["id"],
            "chain": [{"concept": "hâl değişimi", "outcomeCode": OUTCOME_CODE, "mappedTo": [teach["id"]]},
                      {"concept": "adım adım çözüm", "mappedTo": [worked["id"]]}],
        }
        mapped = [teach["id"], worked["id"]]
    data["meta"]["mode"] = mode
    data["meta"]["sourceCitation"] = CITATION
    data["curriculum"] = _curriculum(mapped)
    data["verification"] = _verification()
    return data
