"""Kılavuz PDF'ini iki yoldan (A: Paged.js, B: düz Chrome) basar, kanun kapılarını uygular, süre ve belleği ölçer
(plan 2026-10-25 Görev 2 yoklaması; Görev 13'te gerçek Fen modeliyle). Basım ted-dashboard.service'in ortamıyla koşar
(`env -i`, PATH=.venv/bin:/usr/bin:/bin, HOME); bellek `/usr/bin/time %M` — beklenen en büyük tek sürecin tepe RSS'i
(node ve Chrome süreçleri). systemd-run'ın "Memory peak"i bu makinede güvenilmez (ölçüldü: 512K).

    env -u ANTHROPIC_API_KEY .venv/bin/python -I scripts/kilavuz_pdf_kapilari.py --dist dashboard-dist --cikti /tmp/tedy-yoklama-pdf
    env -u ANTHROPIC_API_KEY .venv/bin/python -I scripts/kilavuz_pdf_kapilari.py --dist dashboard-dist --cikti /tmp/k \\
        --model dashboard/tests/e2e/fixtures/hazirlik/fen-bilimleri-1-kilavuz.json --sorgu 'ders=fen-bilimleri&sinav=1'
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from src.pdf_kapilari import denetle, kusurlar  # noqa: E402

VENV_BIN = "/mnt/thunderbolt/workspaces/TED/.venv/bin"
YOKLAMA_BASLIKLARI = [
    "1. Ünite · Uzay Çağı", "2. Ünite · Kuvvet ve Enerjiyi Keşfedelim", "1. Türkiye ve Uzay Araştırmaları",
    "2. Uzayda Neler Var?", "1. Kuvvet, İş ve Enerji İlişkisi", "Senaryo Karşılaştırması", "Kaynaklar",
    "Fiziksel Anlamda İş", "Uzay Teknolojileri", "Yıldız Oluşumu"]
YOKLAMA_ICINDEKILER = ["Senaryo Karşılaştırması", "1. Ünite · Uzay Çağı", "2. Ünite · Kuvvet ve Enerjiyi Keşfedelim",
                       "Kaynaklar"]


def model_basliklari(model: dict) -> tuple[list[str], list[str]]:
    """Kılavuz modelinden K1 başlıkları (ünite, çerçeve, konu, bölüm başlığı) ve İçindekiler girdileri (bölümler)."""
    basliklar: list[str] = []
    icindekiler = ["Senaryo Karşılaştırması"]
    for u in model.get("uniteler", []):
        basliklar.append(u["baslik"])
        icindekiler.append(u["baslik"])
        for c in u["cerceveler"]:
            if c.get("baslik"):
                basliklar.append(c["baslik"])
            for b in c["bloklar"]:
                if not b["senaryoda"]:
                    continue          # senaryoda olmayan çıktı tek satırdır, başlıkları basılmaz (K2)
                for y in b["kitapta"]:
                    if y.get("konu"):
                        basliklar.append(y["konu"])
                    basliklar += [h["ad"] for h in y.get("basliklar", [])]
    icindekiler.append("Kaynaklar")
    return list(dict.fromkeys(basliklar)), icindekiler


def bas(dist: Path, cikti: Path, sorgu: str, model: Path | None, duz: bool) -> dict:
    komut = ["/usr/bin/time", "-f", "TEDY_BELLEK_KB=%M", "node", "scripts/kilavuz-pdf.mjs",
             "--dist", str(dist.resolve()), "--cikti", str(cikti), "--sorgu", sorgu]
    if model:
        komut += ["--model", str(model.resolve())]
    if duz:
        komut.append("--duz")
    ortam = {"PATH": f"{VENV_BIN}:/usr/bin:/bin", "HOME": os.environ["HOME"]}   # ted-dashboard.service'in ortamı (Y8)
    bas_an = time.monotonic()
    p = subprocess.run(komut, capture_output=True, text=True, timeout=300, cwd=KOK / "dashboard", env=ortam)
    sure = time.monotonic() - bas_an
    m = re.search(r"TEDY_BELLEK_KB=(\d+)", p.stderr)
    return {"cikis": p.returncode, "sure_sn": round(sure, 1), "bellek": f"{int(m.group(1)) // 1024} MB" if m else "?",
            "stderr": p.stderr.strip()[-400:]}


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description="Kılavuz PDF yoklaması / kapı denetimi")
    a.add_argument("--dist", type=Path, required=True)
    a.add_argument("--cikti", type=Path, required=True)
    a.add_argument("--model", type=Path)
    a.add_argument("--sorgu", default="yoklama=1")
    a.add_argument("--yol", choices=("paged", "duz", "ikisi"), default="ikisi")
    g = a.parse_args(argv)
    g.cikti.mkdir(parents=True, exist_ok=True)
    if g.model:
        basliklar, icindekiler = model_basliklari(json.loads(g.model.read_text(encoding="utf-8")))
    else:
        basliklar, icindekiler = YOKLAMA_BASLIKLARI, YOKLAMA_ICINDEKILER
    yollar = {"paged": [False], "duz": [True], "ikisi": [False, True]}[g.yol]
    print("| Yol | Çıkış | Süre (s) | Bellek | Sayfa | Yazı tipleri | Kusurlar |")
    print("|---|---|---|---|---|---|---|")
    sonuc = 0
    for duz in yollar:
        ad = "B düz" if duz else "A Paged.js"
        pdf = g.cikti / ("duz.pdf" if duz else "paged.pdf")
        olcum = bas(g.dist, pdf, g.sorgu, g.model, duz)
        if olcum["cikis"] != 0 or not pdf.exists():
            print(f"| {ad} | {olcum['cikis']} | {olcum['sure_sn']} | {olcum['bellek']} | – | – | basılamadı: {olcum['stderr']} |")
            sonuc = 1
            continue
        rapor = denetle(pdf, basliklar=basliklar, icindekiler=icindekiler)
        if duz:
            # Chrome'un üst/alt bilgi şablonu web yazı tipi kullanamaz (ölçüldü): orada DejaVu Sans beklenir (borç KK-3).
            rapor["yabanci_yazi_tipi"] = [f for f in rapor["yabanci_yazi_tipi"] if not f.startswith("DejaVuSans")]
        k = kusurlar(rapor, icindekiler_beklenir=not duz)
        sonuc = sonuc or (1 if k else 0)
        print(f"| {ad} | 0 | {olcum['sure_sn']} | {olcum['bellek']} | {rapor['sayfa']} | "
              f"{', '.join(rapor['yazi_tipleri'])} | {'; '.join(k) or 'yok'} |")
    return sonuc


if __name__ == "__main__":
    raise SystemExit(main())
