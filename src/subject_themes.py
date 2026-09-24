"""Tedy ders renk sistemi: ders adı → alan → Carbon Tag ailesi.

Tek kaynak vendor otorite dosyasının `tedyLayer.subjectThemes` bölümüdür
(src/mcp_server/vendor/assets/carbon-v11-authority.json). Aynı algoritma modül şablonunda
(`subjectDomain()`, JavaScript) ve panoda (dashboard/src/theme/subjects.ts, üretilir) çalışır;
üçü aynı `domains` tablosunu ve aynı katlama kuralını kullanır, `examples` test vektörleri
hepsini bağlar (tests/test_ders_renkleri.py).

Kural: ders adı katlanır (Türkçe küçük harf; ç ğ ı ö ş ü â î û → c g i o s u a i u), `domains`
sırayla denenir; bir kök bir sözcüğün başında geçerse o alan seçilir. Hiçbiri tutmazsa `fallback`.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

AUTHORITY_PATH = Path(__file__).resolve().parent / "mcp_server" / "vendor" / "assets" / "carbon-v11-authority.json"

_FOLD = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u"})


def fold(text: str) -> str:
    """Türkçe küçük harfe indirger, aksanları katlar ve boşlukları tekler."""
    lowered = str(text).replace("İ", "i").replace("I", "ı").lower()
    return re.sub(r"\s+", " ", lowered.translate(_FOLD)).strip()


@lru_cache(maxsize=1)
def themes() -> dict[str, Any]:
    authority = json.loads(AUTHORITY_PATH.read_text(encoding="utf-8"))
    return authority["tedyLayer"]["subjectThemes"]


@lru_cache(maxsize=1)
def _patterns() -> tuple[tuple[dict[str, Any], re.Pattern[str]], ...]:
    compiled = []
    for domain in themes()["domains"]:
        stems = "|".join(re.escape(fold(stem)) for stem in domain["stems"])
        compiled.append((domain, re.compile(r"(?:^|[^a-z0-9])(?:" + stems + ")")))
    return tuple(compiled)


def domain_of(course: str | None) -> dict[str, Any]:
    """Ders adının alanı: {'id', 'label', 'family'}; tanınmayan ad `fallback` alanıdır."""
    folded = fold(course or "")
    for domain, pattern in _patterns():
        if pattern.search(folded):
            return {"id": domain["id"], "label": domain["label"], "family": domain["family"]}
    return dict(themes()["fallback"])


def family_of(course: str | None) -> str:
    """Ders adının Carbon Tag ailesi (magenta, purple, teal, cyan, blue, warm-gray, cool-gray, gray)."""
    return domain_of(course)["family"]


def families() -> tuple[str, ...]:
    return tuple(themes()["families"])


def role(family: str, name: str, mode: str = "light") -> str:
    """Bir ailenin rol rengi (hex). mode: 'light' (white, g10) ya da 'dark' (g90, g100)."""
    return themes()["families"][family][mode][name][1]
