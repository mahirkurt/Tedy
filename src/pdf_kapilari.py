"""Kapsam kılavuzu PDF'inin kanun kapıları (docs/sinav-kilavuzu-kanunu.md): üretilen dosyanın kendisi ölçülür.

Ayrıştırıcılar saf (tests/test_pdf_kapilari.py fikstürle sınar); `denetle` poppler (pdfinfo, pdffonts, pdftotext,
pdftohtml) ve qpdf'i argüman listesiyle çağırır. pdftohtml `-zoom 1` ile yazı boyu yaklaşık punto olarak okunur
(tamsayıya yuvarlanır: 8,4 pt → 8).

Yetim başlık (K5) kapısı başlığı metinden tahmin etmez: Chrome her başlık öğesini (h1–h6) PDF yer imi olarak yazar ve
yer imi gösterdiği sayfayı taşır. Başlık işareti bu yer imleridir (düz metne yansımaz); konu adıyla biten çalışma planı
satırı, duyuru doğrulaması ya da ebeveyn özeti satırı yer imi değildir, dolayısıyla yetim sayılmaz (kontrolcü kararı D5)."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from src.sinav_tarihi import katla

# Alt bilgi satırı (damga "TEDY · …" ile başlar; sayfa numarası "s. n/N" ile biter): yetim denetimine girmez.
ALT_BILGI = re.compile(r"(^TEDY\b|s\.\s*\d+\s*/\s*\d+\s*$)")
PLEX_ONEKLERI = ("IBMPlexSans", "IBMPlexMono")
EN_KUCUK_PUNTO = 8   # K3: 7,5 pt; pdftohtml tamsayıya yuvarlar
YETIM_SATIR = 3      # iki ya da üç satıra bölünen başlığın sayfa sonunda aranacağı son satır sayısı


def pdffonts_ayristir(metin: str) -> list[dict]:
    """`pdffonts` tablosu → [{"ad", "gomulu"}]; alt küme öneki ("AAAAAA+") atılır. Sütunlar sağdan okunur
    (tür "Type 1C" gibi iki sözcük olabilir): …, emb, sub, uni, nesne no, kuşak."""
    satirlar = metin.splitlines()
    bas = next((i + 1 for i, s in enumerate(satirlar) if s.startswith("---")), None)
    if bas is None:
        return []
    out = []
    for s in satirlar[bas:]:
        p = s.split()
        if len(p) < 7:
            continue
        out.append({"ad": p[0].split("+", 1)[-1], "gomulu": p[-5] == "yes"})
    return out


def pdfinfo_alani(metin: str, alan: str) -> str | None:
    m = re.search(rf"^{re.escape(alan)}:\s*(.*)$", metin, re.M)
    return m.group(1).strip() if m else None


def etiketli_mi(pdfinfo: str) -> bool:
    return pdfinfo_alani(pdfinfo, "Tagged") == "yes"


def sayfa_sayisi(pdfinfo: str) -> int:
    deger = pdfinfo_alani(pdfinfo, "Pages") or "0"
    return int(deger) if deger.isdigit() else 0


def _yer_imi_ogeleri(outlines_json: dict) -> list[dict]:
    out: list[dict] = []

    def gez(ogeler):
        for o in ogeler or []:
            out.append(o)
            gez(o.get("kids"))
    gez(outlines_json.get("outlines"))
    return out


def yer_imleri(outlines_json: dict) -> list[str]:
    return [str(o.get("title", "")) for o in _yer_imi_ogeleri(outlines_json)]


def yer_imi_sayfalari(outlines_json: dict) -> list[tuple[int, str]]:
    """Başlık işareti: (yer imi sayfası, başlık). Chrome yer imlerini yalnız başlık öğelerinden üretir; qpdf JSON v2
    `destpageposfrom1` gösterdiği sayfanın 1 tabanlı sırasıdır. Sayfası çözülemeyen yer imi atlanır."""
    out = []
    for o in _yer_imi_ogeleri(outlines_json):
        sayfa = o.get("destpageposfrom1")
        if isinstance(sayfa, int) and sayfa >= 1:
            out.append((sayfa, str(o.get("title", ""))))
    return out


def pdf_dili(qpdf_json: dict) -> str | None:
    """qpdf JSON v2: qpdf[1]["trailer"]["value"]["/Root"] → "obj:<ref>" → value["/Lang"] ("u:tr")."""
    q = qpdf_json.get("qpdf")
    if not isinstance(q, list) or len(q) < 2 or not isinstance(q[1], dict):
        return None
    nesneler = q[1]
    kok = ((nesneler.get("trailer") or {}).get("value") or {}).get("/Root")
    dil = ((nesneler.get(f"obj:{kok}") or {}).get("value") or {}).get("/Lang")
    if not isinstance(dil, str):
        return None
    return dil[2:] if dil.startswith("u:") else dil


def sayfa_metinleri(pdftotext: str) -> list[str]:
    parcalar = pdftotext.split("\f")
    if parcalar and not parcalar[-1].strip():
        parcalar = parcalar[:-1]
    return parcalar


def _anlamli_satirlar(sayfa: str) -> list[str]:
    return [s.strip() for s in sayfa.splitlines() if s.strip() and not ALT_BILGI.search(s.strip())]


def eksik_basliklar(sayfalar: list[str], basliklar: list[str]) -> list[str]:
    """K1: kitap ve MEB başlıkları PDF metninde birebir (katlanmış) geçmeli."""
    tum = katla(" ".join(" ".join(s.split()) for s in sayfalar))
    return [b for b in basliklar if katla(b) not in tum]


def yetim_basliklar(sayfalar: list[str], basliklar: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """K5: başlık işaretli (sayfa, başlık) çiftlerinden, sayfasının son anlamlı satırlarıyla (alt bilgi hariç; birkaç
    satıra bölünen başlık için son `YETIM_SATIR` satır) biten ve son sayfada olmayanlar yetimdir. `basliklar` yer
    imlerinden gelir (`yer_imi_sayfalari`); işaretsiz metin hiçbir zaman yetim sayılmaz (D5). Sınır: aynı sayfada hem
    işaretli bir başlık hem de aynı yazıyla biten düz bir satır varsa ikisi ayırt edilemez (kapı tek yönlü yanılır:
    yanlış alarm verir, kusur kaçırmaz)."""
    out = []
    for sayfa_no, baslik in basliklar:
        if not 1 <= sayfa_no < len(sayfalar):      # son sayfa ve aralık dışı sayfalar yetim sayılmaz
            continue
        katli = katla(baslik)
        satirlar = _anlamli_satirlar(sayfalar[sayfa_no - 1])
        if katli and satirlar and katla(" ".join(satirlar[-YETIM_SATIR:])).endswith(katli):
            out.append((sayfa_no, baslik))
    return sorted(set(out))


def icindekiler_hatalari(sayfalar: list[str], girdiler: list[str]) -> list[str]:
    """K5, spec §4.2: İçindekiler'deki her girdinin gösterdiği sayfada o başlık geçmeli."""
    t = next((i for i, s in enumerate(sayfalar) if "icindekiler" in katla(s)), None)
    if t is None:
        return ["İçindekiler sayfası yok"]
    satirlar = [" ".join(s.split()) for s in sayfalar[t].splitlines() if s.strip()]
    hatalar = []
    for g in girdiler:
        k = katla(g)
        gosterilen = None
        for s in satirlar:
            m = re.search(r"(\d+)\s*$", s)
            if m and k in katla(s):
                gosterilen = int(m.group(1))
                break
        if gosterilen is None:
            hatalar.append(f"İçindekiler'de sayfa numarası yok: {g}")
        elif not (1 <= gosterilen <= len(sayfalar)) or k not in katla(" ".join(sayfalar[gosterilen - 1].split())):
            hatalar.append(f"{g}: İçindekiler s. {gosterilen} diyor, başlık o sayfada yok")
    return hatalar


def en_kucuk_punto(xml: str) -> int | None:
    boy = {m.group(1): int(m.group(2)) for m in re.finditer(r'<fontspec id="(\d+)" size="(\d+)"', xml)}
    kullanilan = {m.group(1) for m in re.finditer(r'<text [^>]*font="(\d+)"', xml)}
    degerler = [boy[f] for f in kullanilan if f in boy]
    return min(degerler) if degerler else None


def _calistir(*argv: str) -> str:
    return subprocess.run(list(argv), capture_output=True, text=True, check=True, timeout=120).stdout


def denetle(yol: Path, *, basliklar: list[str], icindekiler: list[str]) -> dict:
    y = str(yol)
    info = _calistir("pdfinfo", y)
    fontlar = pdffonts_ayristir(_calistir("pdffonts", y))
    sayfalar = sayfa_metinleri(_calistir("pdftotext", "-layout", y, "-"))
    qpdf = json.loads(_calistir("qpdf", "--json", "--json-key=qpdf", y))
    anahat = json.loads(_calistir("qpdf", "--json", "--json-key=outlines", y))
    xml = _calistir("pdftohtml", "-xml", "-i", "-q", "-zoom", "1", "-stdout", y)
    return {
        "sayfa": sayfa_sayisi(info), "etiketli": etiketli_mi(info), "dil": pdf_dili(qpdf),
        "yazi_tipleri": sorted({f["ad"] for f in fontlar}),
        "gomulu_degil": sorted({f["ad"] for f in fontlar if not f["gomulu"]}),
        "yabanci_yazi_tipi": sorted({f["ad"] for f in fontlar if not f["ad"].startswith(PLEX_ONEKLERI)}),
        "yer_imi": len(yer_imleri(anahat)), "yetim": yetim_basliklar(sayfalar, yer_imi_sayfalari(anahat)),
        "icindekiler": icindekiler_hatalari(sayfalar, icindekiler) if icindekiler else [],
        "eksik_baslik": eksik_basliklar(sayfalar, basliklar), "en_kucuk_punto": en_kucuk_punto(xml),
    }


def kusurlar(r: dict, *, icindekiler_beklenir: bool = True) -> list[str]:
    """Raporun kanun kusurları; boş liste kapıların geçtiği anlamına gelir. Düz yolda (B) İçindekiler sayfa numarası
    taşımadığı için `icindekiler_beklenir=False` verilir."""
    k = []
    if r["gomulu_degil"]:
        k.append("gömülmemiş yazı tipi: " + ", ".join(r["gomulu_degil"]))
    if r["yabanci_yazi_tipi"]:
        k.append("Plex dışı yazı tipi: " + ", ".join(r["yabanci_yazi_tipi"]))
    if not r["etiketli"]:
        k.append("PDF etiketli değil")
    if (r["dil"] or "").split("-")[0] != "tr":
        k.append(f"PDF dili tr değil: {r['dil']}")
    if r["yer_imi"] == 0:
        k.append("yer imi yok")
    k += [f"yetim başlık s. {s}: {b}" for s, b in r["yetim"]]
    if icindekiler_beklenir:
        k += r["icindekiler"]
    k += [f"başlık PDF metninde yok: {b}" for b in r["eksik_baslik"]]
    if r["en_kucuk_punto"] is not None and r["en_kucuk_punto"] < EN_KUCUK_PUNTO:
        k.append(f"en küçük punto {r['en_kucuk_punto']} < 7,5")
    return k
