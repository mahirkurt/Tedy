"""Portal UI residue, removed from scraped text in one place.

The portal renders a course tab's posts with its own chrome — "N Yorum
yapıldı!", "Daha fazla oku", "Yorum Ekle", "İlk yorum yapan sen olmak ister
misin?" — and, between "Daha fazla oku" and "Yorum Ekle", the comment block:
per comment another child's name, a like count and the comment. Measured
2026-09-28 in output/scraped_data.json: 445 such blocks, mostly in the
"Genel" school feed. None of it is the teacher's or the school's content and
the names are not ours to pass on, so it is dropped before storage
(scrape_all, run_sync), at the API boundary (dashboard_api) and again in the
browser (dashboard/src/utils/portalSusu.ts, a port of this file).
"""
from __future__ import annotations

import re
from typing import Any

YORUM_BASI = "Daha fazla oku"
YORUM_SONU = "Yorum Ekle"
# The chrome strings, as tests and the frontend port assert against.
SUS_ISARETLERI = (YORUM_BASI, YORUM_SONU,
                  "İlk yorum yapan sen olmak ister misin?", "Yorum yapıldı!")
_SUS_SATIRI = re.compile(
    r"^(?:Daha fazla oku|Yorum Ekle|İlk yorum yapan sen olmak ister misin\?|\d+ Yorum yapıldı!)$")


def temiz_metin(metin: Any) -> str:
    """`metin` without the portal's chrome and without any comment block.

    A block runs from "Daha fazla oku" to "Yorum Ekle". A blank line does not
    end it (a comment can hold one), and a block that never closes runs to
    the end of the text: 87 cards were measured ending right after "Daha
    fazla oku" and the scraper cuts a tab at 8,000 characters, so an unclosed
    block is a cut one — dropping the tail is the side that never leaks a
    name. Lines are whitespace-normalised (the portal renders NBSPs and
    doubled spaces) and runs of blank lines collapse to one.
    """
    satirlar: list[str] = []
    yorumda = False
    for ham in str("" if metin is None else metin).split("\n"):
        s = " ".join(ham.split())
        if yorumda:
            if s == YORUM_SONU:
                yorumda = False
            continue
        if s == YORUM_BASI:
            yorumda = True
            continue
        if _SUS_SATIRI.match(s):
            continue
        if not s:
            if satirlar and satirlar[-1]:
                satirlar.append("")
            continue
        satirlar.append(s)
    return "\n".join(satirlar).strip()


def _temiz_hucre(deger: Any) -> Any:
    return temiz_metin(deger) if isinstance(deger, str) else deger


def _temiz_tablo(tablo: Any) -> Any:
    if not isinstance(tablo, dict) or "rows" not in tablo:
        return tablo
    satirlar = []
    for satir in tablo.get("rows") or []:
        if isinstance(satir, list):
            satirlar.append([_temiz_hucre(h) for h in satir])
        elif isinstance(satir, dict):
            satirlar.append({k: _temiz_hucre(v) for k, v in satir.items()})
        else:
            satirlar.append(_temiz_hucre(satir))
    return {**tablo, "rows": satirlar}


def temiz_icerik_kaydi(kayit: Any) -> Any:
    """One course tab ({tab_id, text, tables, items, cards}) cleaned; a card
    or item that was nothing but a comment block is dropped. A non-dict comes
    back unchanged, and a failed tab ({tab_id, error}) has nothing to clean.
    Never mutates its input."""
    if not isinstance(kayit, dict):
        return kayit
    temiz = dict(kayit)
    if "text" in kayit:
        temiz["text"] = temiz_metin(kayit.get("text"))
    for alan in ("items", "cards"):
        if isinstance(kayit.get(alan), list):
            temiz[alan] = [t for t in (_temiz_hucre(x) for x in kayit[alan]) if t != ""]
    if isinstance(kayit.get("tables"), list):
        temiz["tables"] = [_temiz_tablo(t) for t in kayit["tables"]]
    return temiz


def temiz_dersler(dersler: Any) -> Any:
    """{course: tab} — ders_icerikleri, /api/content."""
    if not isinstance(dersler, dict):
        return dersler
    return {ad: temiz_icerik_kaydi(kayit) for ad, kayit in dersler.items()}


def temiz_haftalar(haftalar: Any) -> Any:
    """{week label: {course: tab}} — ders_icerikleri_haftalar, /api/content/weeks."""
    if not isinstance(haftalar, dict):
        return haftalar
    return {etiket: temiz_dersler(dersler) for etiket, dersler in haftalar.items()}
