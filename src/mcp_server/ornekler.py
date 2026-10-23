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


def ornek(mode: str) -> dict[str, Any]:
    if mode not in MODES:
        raise ValueError(f"bilinmeyen mod: {mode}")
    data = demo()
    segments = data["segments"]
    # Fix round 1, F3: the vendored demo's `teach` visuals (`kind:"svg"`, inline diagram markup)
    # are no longer converted to decorative pictograms here. `_js_string`'s new template-literal
    # branch (derleme.py) lets these compile through with an accessible, unescaped
    # `role="img"` — see the F3 note there for why the earlier pictogram workaround existed and
    # why it is no longer needed.
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


GORSEL_ORNEGI_ALT = "Kağnıların yanında yürüyen halk toprak bir yolda cepheye cephane taşıyor."
GORSEL_ORNEGI_BASLIK = "Görsel 1.30: İstiklal Yolu yürüyüşü"


def _ornek_jpeg() -> bytes:
    import io

    from PIL import Image, ImageDraw

    image = Image.new("RGB", (640, 400), (214, 222, 230))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 260, 640, 400), fill=(160, 140, 110))
    for x in range(40, 640, 120):
        draw.rectangle((x, 200, x + 70, 260), fill=(90, 70, 50))
        draw.ellipse((x + 5, 245, x + 30, 270), fill=(40, 40, 40))
        draw.ellipse((x + 45, 245, x + 70, 270), fill=(40, 40, 40))
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def gorsel_ornegi() -> tuple[dict[str, Any], dict[str, Any]]:
    """Şablonun çizdiği her SVG türü, bir raster figür ve bir ses varlığı (Modül Tasarım Kanunu M5.6,
    M3.6–M3.8, M5.14; KB-5, KB-10–KB-12). (MODULE_DATA, varlıklar) döner; varlıklar derleyicinin
    `GomuluVarlik` kayıtlarıdır. `dashboard/tests/e2e/modul-svg-metni.spec.ts` ve derleme testleri kullanır."""
    import base64

    from src.mcp_server.derleme import GomuluVarlik  # derleme bu modülü içe aktarır; döngü olmasın diye burada

    data = ornek("MODULE")
    ay = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    data["meta"]["title"] = "Grafik, Sayı Doğrusu ve Figür"
    data["segments"] = [
        {"type": "teach", "id": "t1", "title": "Tam Sayılar", "pictogram": "pic-idea",
         "body": ["<p>Sıfırın solundaki sayılar negatif, sağındakiler pozitiftir.</p>"],
         "visual": {"kind": "numberline", "min": -10, "max": 10, "step": 1, "title": "Tam sayılar",
                    "points": [{"value": -3, "label": "A"}, {"value": 4, "label": "B"}]}},
        {"type": "teach", "id": "t2", "title": "İstiklal Yolu", "pictogram": "pic-idea",
         "body": ["<p>Halk cepheye cephane taşıdı.</p>"]},
        {"type": "chart", "id": "c1", "title": "Sektörlere Göre Çalışanlar", "kind": "bar",
         "data": [{"label": "Tarım", "value": 18}, {"label": "Sanayi", "value": 27},
                  {"label": "Hizmetler", "value": 41}, {"label": "Turizm", "value": 9},
                  {"label": "Madencilik", "value": 3}, {"label": "Ulaştırma", "value": None}]},
        {"type": "chart", "id": "c2", "title": "Aylık Yağış", "kind": "line",
         "data": [{"label": a, "value": v} for a, v in zip(ay, [92, 78, 66, 51, 38, 21, 9, 7, 19, 44, 71, 95])]},
        {"type": "numberline", "id": "n1", "title": "Sayıyı Yerleştir",
         "numberline": {"min": 0, "max": 20, "step": 1, "interactive": True, "value": 7,
                        "interactiveLabel": "Seçilen sayı", "title": "0 ile 20 arası"}},
        # Yayındaki mat7 "Çekirgenin altı eşit sıçrayışı"na benzer: her noktanın değeri her genişlikte okunur.
        {"type": "numberline", "id": "n2", "title": "Çekirgenin Sıçrayışları",
         "numberline": {"min": -6, "max": 8, "step": 1, "title": "Çekirgenin konumları",
                        "points": [{"value": v} for v in (-5, -3, -1, 1, 3, 5, 7)]}},
        {"type": "fraction", "id": "fr1", "title": "Kesirleri Topla", "kind": "sum", "addends": [1, 2, 3], "den": 8},
        {"type": "diagram", "id": "d1", "title": "Hücrenin Bölümleri", "viewBox": "0 0 480 300",
         "base": ('<ellipse cx="240" cy="150" rx="200" ry="120" fill="var(--cds-layer-01)" '
                  'stroke="var(--cds-border-strong)" stroke-width="3"/>'
                  '<circle cx="250" cy="150" r="48" fill="var(--cds-layer-accent-01)" '
                  'stroke="var(--cds-border-strong)" stroke-width="2"/>'),
         "labels": [{"x": 250, "y": 150, "text": "Çekirdek"}, {"x": 110, "y": 110, "text": "Sitoplazma"},
                    {"x": 420, "y": 190, "text": "Hücre zarı"}]},
        {"type": "sim", "id": "s1", "title": "Sayı Ölçeği", "simType": "numberScale",
         "params": [{"key": "value", "label": "Değer", "min": 0, "max": 20, "step": 1, "default": 13}]},
        {"type": "sim", "id": "s2", "title": "Sarkaç", "simType": "pendulum",
         "params": [{"key": "length", "label": "Uzunluk (m)", "min": 0.2, "max": 2.2, "step": 0.1, "default": 2.2},
                    {"key": "angle", "label": "Açı (derece)", "min": -60, "max": 60, "step": 5, "default": 60}]},
        {"type": "sim", "id": "s3", "title": "Atış", "simType": "projectile",
         "params": [{"key": "speed", "label": "Hız (m/sn)", "min": 5, "max": 40, "step": 1, "default": 20},
                    {"key": "angle", "label": "Açı (derece)", "min": 10, "max": 80, "step": 5, "default": 45}]},
    ]
    data["curriculum"] = _curriculum(["t1", "c1"])
    gorsel = _ornek_jpeg()
    ses = b"ID3" + b"\0" * 64
    varliklar = {
        "a1b2c3d4e5f60718": GomuluVarlik(
            asset_id="a1b2c3d4e5f60718", tur="image", mime="image/jpeg",
            data_uri="data:image/jpeg;base64," + base64.b64encode(gorsel).decode("ascii"), bayt=len(gorsel),
            credit="Görsel: T.C. Millî Eğitim Bakanlığı, Türkiye Yüzyılı Maarif Modeli yayını",
            lisans="MEB yayını — yalnız aile içi eğitim kullanımı", alt="", kaynak="mufredat",
            betim="Fotoğraf: kağnılarla toprak yolda yürüyen kalabalık.",
            kitap_altyazisi="Görsel 1.30: İstiklal Yolu yürüyüşü", etiket="Görsel 1.30"),
        "0f1e2d3c4b5a6978": GomuluVarlik(
            asset_id="0f1e2d3c4b5a6978", tur="ses", mime="audio/mpeg",
            data_uri="data:audio/mpeg;base64," + base64.b64encode(ses).decode("ascii"), bayt=len(ses),
            credit="Seslendirme: yapay zekâ ile üretildi (MiniMax speech-2.8-hd)", lisans="MiniMax üretimi",
            alt="", kaynak="minimax"),
    }
    data["meta"]["assets"] = [
        {"asset_id": "a1b2c3d4e5f60718", "slot": "t2.visual", "alt": GORSEL_ORNEGI_ALT, "baslik": GORSEL_ORNEGI_BASLIK},
        {"asset_id": "0f1e2d3c4b5a6978", "slot": "t2.audio"},
    ]
    return data, varliklar
