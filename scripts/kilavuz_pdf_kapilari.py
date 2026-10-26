"""Kılavuz PDF'ini iki yoldan (A: Paged.js, B: düz Chrome) basar, kanun kapılarını uygular, süre ve belleği ölçer
(plan 2026-10-25 Görev 2 yoklaması; Görev 13'te gerçek Fen modeliyle). Basım ted-dashboard.service'in ortamıyla koşar
(`env -i`, PATH=.venv/bin:/usr/bin:/bin, HOME, TZ=Europe/Istanbul); bellek `/usr/bin/time %M` — bekleyen süreç
ağacındaki en büyük TEK sürecin tepe RSS'i (node ya da Chrome süreçlerinden biri; toplam değil). systemd-run'ın
"Memory peak"i bu makinede güvenilmez (ölçüldü: 512K).

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

from src.pdf_kapilari import DenetimHatasi, denetle, kusurlar  # noqa: E402

VENV_BIN = "/mnt/thunderbolt/workspaces/TED/.venv/bin"
BASIM_SURESI = 300   # saniye
YOKLAMA_BASLIKLARI = [
    "1. Ünite · Uzay Çağı", "2. Ünite · Kuvvet ve Enerjiyi Keşfedelim", "1. Türkiye ve Uzay Araştırmaları",
    "2. Uzayda Neler Var?", "1. Kuvvet, İş ve Enerji İlişkisi", "Senaryo Karşılaştırması", "Kaynaklar",
    "Fiziksel Anlamda İş", "Uzay Teknolojileri", "Yıldız Oluşumu"]
YOKLAMA_ICINDEKILER = ["Senaryo Karşılaştırması", "1. Ünite · Uzay Çağı", "2. Ünite · Kuvvet ve Enerjiyi Keşfedelim",
                       "Kaynaklar"]


def model_basliklari(model: dict) -> tuple[list[str], list]:
    """Kılavuz modelinden K1 başlıkları (ünite, çerçeve, konu, bölüm başlığı) ve İçindekiler girdileri — panonun
    `belge.bolumler(m)` listesinin aynısı, sırasıyla. Özet'in sayfasında görünen başlık "Kapsam Kılavuzu"dur."""
    basliklar: list[str] = []
    icindekiler: list = [
        *(["Ebeveyn Özeti"] if model.get("ebeveyn") else []), ("Özet", "Kapsam Kılavuzu"),
        *(["Senaryo Karşılaştırması"] if (model.get("matris") or {}).get("senaryolar") else []),
        *[u["baslik"] for u in model.get("uniteler", [])],
        *(["Duyuru Doğrulaması"] if model.get("dogrulama") else []),
        *(["Çalışma Planı"] if model.get("plan") else []), "Kaynaklar"]
    for u in model.get("uniteler", []):
        basliklar.append(u["baslik"])
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
    return list(dict.fromkeys(basliklar)), icindekiler


def kapak_sayfasi(model: dict) -> int:
    """Üst bilgisi olmayan kapak: ebeveyn özeti başa tek sayfa gelirse 2, yoksa 1 (K5)."""
    return 2 if model.get("ebeveyn") else 1


def bas(dist: Path, cikti: Path, sorgu: str, model: Path | None, duz: bool) -> dict:
    komut = ["/usr/bin/time", "-f", "TEDY_BELLEK_KB=%M", "node", "scripts/kilavuz-pdf.mjs",
             "--dist", str(dist.resolve()), "--cikti", str(cikti), "--sorgu", sorgu]
    if model:
        komut += ["--model", str(model.resolve())]
    if duz:
        komut.append("--duz")
    # ted-dashboard.service'in ortamı (Y8); TZ: tarih ve "üretim" günü İstanbul'a göre (sunucu UTC olabilir).
    ortam = {"PATH": f"{VENV_BIN}:/usr/bin:/bin", "HOME": os.environ["HOME"], "TZ": "Europe/Istanbul"}
    bas_an = time.monotonic()
    try:
        p = subprocess.run(komut, capture_output=True, text=True, timeout=BASIM_SURESI, cwd=KOK / "dashboard", env=ortam)
    except subprocess.TimeoutExpired:
        return {"cikis": "zaman aşımı", "sure_sn": round(time.monotonic() - bas_an, 1), "bellek": "?",
                "stderr": f"basım {BASIM_SURESI} s içinde bitmedi"}
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
    g.cikti = g.cikti.resolve()          # basım dashboard/ içinde koşar; göreli yol oraya yazmasın
    g.cikti.mkdir(parents=True, exist_ok=True)
    kapak = 1
    if g.model:
        model = json.loads(g.model.read_text(encoding="utf-8"))
        basliklar, icindekiler = model_basliklari(model)
        kapak = kapak_sayfasi(model)
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
        try:
            rapor = denetle(pdf, basliklar=basliklar, icindekiler=icindekiler, duz=duz, kapak=kapak)
        except DenetimHatasi as e:
            print(f"| {ad} | 0 | {olcum['sure_sn']} | {olcum['bellek']} | – | – | denetlenemedi: {e} |")
            sonuc = 1
            continue
        k = kusurlar(rapor, icindekiler_beklenir=not duz)
        sonuc = sonuc or (1 if k else 0)
        print(f"| {ad} | 0 | {olcum['sure_sn']} | {olcum['bellek']} | {rapor['sayfa']} | "
              f"{', '.join(rapor['yazi_tipleri'])} | {'; '.join(k) or 'yok'} |")
    return sonuc


if __name__ == "__main__":
    raise SystemExit(main())
