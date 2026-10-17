"""Modül şablonunun stil bloğundaki ölçüleri px'ten rem'e çevirir (n px → n/16 rem).

Plan: docs/superpowers/plans/2026-10-15-modul-sablonu-4k-ve-carbon-sapmalari.md (Görev 6)
Spec: docs/superpowers/specs/2026-10-15-modul-sablonu-carbon-sapmalari-design.md §10.3

Dokunulmayanlar:
  * `@media` kırılma noktaları — medya sorgusunda rem, kök yazı boyunu değil tarayıcı
    varsayılanını kullanır, yani çevirmek kırılma noktasını kaydırır;
  * kenarlık/saç çizgisi özellikleri (`border*`, `outline*`, `box-shadow`, `stroke-width`,
    `text-decoration-thickness`, `text-underline-offset`);
  * ≤ 3 px değerler (saç çizgisi sınıfı);
  * `--cds-*` bildirimleri — Carbon'un kendi otorite değerleri (ör. `border-radius-max:999999px`,
    "pill" deyimi), TEDY'nin ölçüsü değil; G-TOKEN onları @carbon/themes'e karşı denetler;
  * yorumlar ve SVG `viewBox` (birimsiz).

Betik bir kez koşar; çıktı diff olarak okunur.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SABLON = Path("src/mcp_server/vendor/assets/module-template.html")
KORUNAN = re.compile(r"(border(-[a-z]+)?|outline(-[a-z]+)?|text-decoration-thickness"
                     r"|text-underline-offset|box-shadow|stroke-width)\s*:")
SAYI = re.compile(r"(\d*\.?\d+)px")


def cevir_bildirim(bildirim: str) -> str:
    if KORUNAN.match(bildirim) or bildirim.startswith("--cds-"):
        return bildirim

    def bir(m: re.Match[str]) -> str:
        deger = float(m.group(1))
        if deger <= 3:
            return m.group(0)
        metin = f"{deger / 16:.4f}".rstrip("0").rstrip(".")
        return f"{metin}rem"

    return SAYI.sub(bir, bildirim)


def main() -> int:
    metin = SABLON.read_text(encoding="utf-8")
    bas, son = metin.index("<style>"), metin.index("</style>")
    stil = metin[bas:son]
    parcalar: list[str] = []
    konum = 0
    # @media satırlarını ve yorumları olduğu gibi geçir, yalnız bildirimleri çevir.
    for m in re.finditer(r"(@media[^{]*\{)|(/\*.*?\*/)|([-a-z]+\s*:[^;}\n]*)", stil, flags=re.S):
        parcalar.append(stil[konum:m.start()])
        parcalar.append(m.group(0) if (m.group(1) or m.group(2)) else cevir_bildirim(m.group(3)))
        konum = m.end()
    parcalar.append(stil[konum:])
    SABLON.write_text(metin[:bas] + "".join(parcalar) + metin[son:], encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
