"""Serve the vendored edupedia guide as bounded sections for every web surface (spec §9.1)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.mcp_server.vendor_sync import VENDOR_DIR

PART_MAX_BYTES = 8000
_R = "references/"

# bölüm → ((file, heading numbers), ...); an empty tuple means the whole file.
SECTIONS: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "akis": (("SKILL.md", ("8",)), (_R + "module-architecture.md", ("3", "4")), (_R + "curriculum-integration.md", ("3",))),
    "modlar": (("SKILL.md", ("3", "6")), (_R + "module-architecture.md", ("1",))),
    "segmentler": ((_R + "module-architecture.md", ("2",)), (_R + "interaction-patterns.md", ())),
    "etkilesim": (("SKILL.md", ("9",)), (_R + "gamified-flows.md", ("2", "3", "4"))),
    "pedagoji": (("SKILL.md", ("4",)), (_R + "adhd-pedagogy.md", ("2", "3", "6", "7", "9"))),
    "carbon": (("SKILL.md", ("10",)), (_R + "tedy-integration.md", ()), (_R + "carbon-child-system.md", ()),
               (_R + "carbon-excellence.md", ("2", "4")), (_R + "color-system.md", ())),
    "svg": (("SKILL.md", ("11",)), (_R + "svg-authoring.md", ()), (_R + "icon-pictogram-svg.md", ())),
    "ses": ((_R + "audio-system.md", ()),),
    "mufredat": (("SKILL.md", ("7",)), (_R + "curriculum-integration.md", ())),
    "soru": ((_R + "newgen-question-design.md", ()),),
    "sinav": ((_R + "exam-solving.md", ()),),
    "zenginlestirme": ((_R + "content-enrichment.md", ()), (_R + "carbon-sources.md", ())),
    "kalite": (("SKILL.md", ("12", "15")), (_R + "carbon-excellence.md", ("3",)), (_R + "gamified-flows.md", ("5",)),
               (_R + "svg-authoring.md", ("6",))),
}

UYARI = (
    "Bu rehber Claude Code plugin'i için yazıldı. Dosya yolu, script çalıştırma (validate_module.py) ve "
    "yerel teslim adımlarını UYGULAMA: HTML'i kendin yazma; MODULE_DATA'yı edupedia_derle ile derlet, "
    "edupedia_yayinla ile yayınla. Müfredat adımları için edupedia_kapsam ve edupedia_kaynak_oku kullan."
)

_HEADING = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_NUMBER = re.compile(r"^##\s+(\d+(?:\.\d+)?)")


def _fold(text: str) -> str:
    return text.replace("I", "ı").replace("İ", "i").lower()


def split_sections(text: str) -> list[tuple[str, str]]:
    matches = list(_HEADING.finditer(text))
    out: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        heading = m.group(0).strip()
        if _fold(heading).startswith("## içindekiler"):
            continue
        out.append((heading, text[m.end():end].strip()))
    return out


def preamble(text: str) -> str:
    """Text before the first `## ` heading (the whole text when there is none), stripped."""
    first = _HEADING.search(text)
    return (text[: first.start()] if first else text).strip()


def _matches(heading: str, numbers: tuple[str, ...]) -> bool:
    if not numbers:
        return True
    m = _NUMBER.match(heading)
    if not m:
        return False
    value = m.group(1)
    return any(value == n or value.startswith(n + ".") for n in numbers)


def _blocks(bolum: str, vendor: Path) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    for filename, numbers in SECTIONS[bolum]:
        text = (vendor / filename).read_text(encoding="utf-8")
        if numbers == ():
            pre = preamble(text)
            if pre:
                blocks.append((f"{filename} (giriş)", f"{pre}\n"))
        for heading, body in split_sections(text):
            if _matches(heading, numbers):
                blocks.append((f"{filename} {heading}", f"{heading}\n\n{body}\n"))
    return blocks


def _pieces(block: str) -> list[str]:
    """Split one oversized block on paragraph, then hard byte boundaries."""
    if len(block.encode("utf-8")) <= PART_MAX_BYTES:
        return [block]
    pieces, current = [], ""
    for para in block.split("\n\n"):
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate.encode("utf-8")) <= PART_MAX_BYTES:
            current = candidate
            continue
        if current:
            pieces.append(current)
        while len(para.encode("utf-8")) > PART_MAX_BYTES:
            cut = para.encode("utf-8")[:PART_MAX_BYTES].decode("utf-8", errors="ignore")
            pieces.append(cut)
            para = para[len(cut):]
        current = para
    if current:
        pieces.append(current)
    return pieces


def _parts(bolum: str, vendor: Path) -> list[tuple[str, list[str]]]:
    parts: list[tuple[str, list[str]]] = []
    text, sources = "", []
    for source, block in _blocks(bolum, vendor):
        for piece in _pieces(block):
            if text and len((text + "\n" + piece).encode("utf-8")) > PART_MAX_BYTES:
                parts.append((text, sources))
                text, sources = "", []
            text = f"{text}\n{piece}" if text else piece
            if source not in sources:
                sources.append(source)
    if text:
        parts.append((text, sources))
    return parts


def guide(bolum: str, parca: int = 1, vendor: Path = VENDOR_DIR) -> dict[str, Any]:
    if bolum not in SECTIONS:
        return {"status": "gecersiz_bolum", "bolumler": sorted(SECTIONS), "mcp_verified": False}
    parts = _parts(bolum, vendor)
    if parca < 1 or parca > len(parts):
        return {"status": "gecersiz_parca", "bolum": bolum, "toplam_parca": len(parts), "mcp_verified": False}
    text, sources = parts[parca - 1]
    body: dict[str, Any] = {
        "status": "ok", "bolum": bolum, "parca": parca, "toplam_parca": len(parts),
        "metin": text, "kaynaklar": sources, "uyari": UYARI, "mcp_verified": False,
    }
    if parca < len(parts):
        body["sonraki_parca"] = parca + 1
    return body


def search(q: str, limit: int = 5, vendor: Path = VENDOR_DIR) -> dict[str, Any]:
    terms = [t for t in re.findall(r"\w+", _fold(q or "")) if len(t) >= 3]
    if not terms:
        return {"status": "gecersiz_sorgu", "mcp_verified": False}
    owners: dict[str, list[str]] = {}
    for bolum, sources in SECTIONS.items():
        for filename, _ in sources:
            owners.setdefault(filename, []).append(bolum)
    scored = []
    files = ["SKILL.md", *sorted(str(p.relative_to(vendor)) for p in (vendor / "references").glob("*.md"))]
    for filename in files:
        file_text = (vendor / filename).read_text(encoding="utf-8")
        sections = list(split_sections(file_text))
        pre = preamble(file_text)
        if pre:
            sections.insert(0, ("(giriş)", pre))
        for heading, body in sections:
            h, b = _fold(heading), _fold(body)
            score = sum(3 * h.count(t) + b.count(t) for t in terms)
            if score:
                scored.append((score, filename, heading, body))
    scored.sort(key=lambda row: -row[0])
    return {
        "status": "ok",
        "sorgu": q,
        "sonuclar": [
            {"kaynak": f, "baslik": h, "bolumler": owners.get(f, []), "ozet": b[:400]}
            for _, f, h, b in scored[:limit]
        ],
        "uyari": UYARI,
        "mcp_verified": False,
    }
