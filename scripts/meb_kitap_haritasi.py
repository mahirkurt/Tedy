"""MEB ders kitabı haritası üretici (spec 2026-10-25 §2.2): EBA PDF'inden ünite → içerik çerçevesi → konu → bölüm
içi başlıklar ve basılı sayfalar; çıktı → kitap bölümü eşlemesi. Çıktı src/kitap_haritalari/<anahtar>.json; elle
düzenlenmez (gürültü temizliği KITAPLAR ayarındadır, sonra betik yeniden koşar).

PDF güvenilmeyen veridir: boş bir geçici dizine iner, poppler araçları argüman listesiyle çağrılır, betik o
dizinden koşmaz ve Python `-I` ile çalışır.

    env -u ANTHROPIC_API_KEY .venv/bin/python -I scripts/meb_kitap_haritasi.py fen-bilimleri --pdf 1=/tmp/meb-kitap-yoklama/fen7-1.pdf --kuru
    env -u ANTHROPIC_API_KEY .venv/bin/python -I scripts/meb_kitap_haritasi.py fen-bilimleri --pdf 1=… --denetim-kim "…"
    env -u ANTHROPIC_API_KEY .venv/bin/python -I scripts/meb_kitap_haritasi.py fen-bilimleri --denetle
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from src.json_utils import atomic_json_dump  # noqa: E402
from src.sinav_senaryo import tablo_oku  # noqa: E402
from src.sinav_tarihi import katla  # noqa: E402

SURUM = 1
CIKTI_DIZINI = KOK / "src" / "kitap_haritalari"
DENETIM_DOSYASI = KOK / "output" / "kitap_denetimi.json"
# Ünite içindeki ama konu olmayan girdiler (katlanmış): sayfa sınırı için okunur, haritaya girmez.
UNITE_EKLERI = ("on degerlendirme", "iz birakanlar", "unite sonu degerlendirme")
_UNITE = re.compile(r"^(\d+)\.\s*Ünite\s+(\S.*)$")
_GIRDI = re.compile(r"^(?:(\d+)\.\s+)?(.+?)\s*\.{2,}[\s.]*(\d{1,4})$")
_SAYI = re.compile(r"^\d+$")


class YapiHatasi(ValueError):
    """Kitap beklenen yapıda değil; harita yazılmaz, eskisi kalır."""


def icindekiler_ayristir(metin: str) -> list[dict]:
    """`pdftotext -layout` İçindekiler sayfası → üniteler (basılı sayfa). Ünite satırı "1. Ünite   Uzay Çağı"; numaralı
    girdi içerik çerçevesi, numarasız girdi konu. Ünite ekleri ve ön/arka kısım (Kitabımızı Tanıyalım, Sözlük…) yalnız
    bitiş sayfası için okunur. Bir satır noktalı sayfa numarasıyla bitmiyorsa sonraki satırla birleşir (iki satıra
    bölünmüş başlık); birleşince de tanınmayan satır YapiHatasi'dır — hiçbir girdi sessizce düşmez."""
    bas = metin.find("İçindekiler")
    if bas < 0:
        raise YapiHatasi("İçindekiler başlığı yok")
    govde = metin[bas + len("İçindekiler"):].split("\f", 1)[0]
    uniteler: list[dict] = []
    akis: list[dict] = []          # sayfası olan her girdi, okunuş sırasıyla: {"sayfa", "tur", "u", "c", "k"}
    bekleyen = ""
    kapali = True                  # henüz ünite yok ya da son ünitenin "Ünite Sonu Değerlendirme"si geçti
    for ham in govde.splitlines():
        s = " ".join(ham.split())
        if not s or _SAYI.fullmatch(s):
            continue
        if bekleyen:
            s = f"{bekleyen} {s}"
        m = _UNITE.match(s)
        if m:
            uniteler.append({"no": int(m.group(1)), "ad": m.group(2).strip(), "sayfa": None, "son_sayfa": None,
                             "cerceveler": []})
            bekleyen, kapali = "", False
            continue
        g = _GIRDI.match(s)
        if not g:
            if bekleyen:
                raise YapiHatasi(f"tanınmayan İçindekiler satırı: {s}")
            bekleyen = s
            continue
        bekleyen = ""
        no, ad, sayfa = g.group(1), g.group(2).strip(), int(g.group(3))
        if akis and sayfa < akis[-1]["sayfa"]:
            raise YapiHatasi(f"İçindekiler sayfaları geriye gidiyor: {ad} s. {sayfa}")
        if kapali:
            akis.append({"sayfa": sayfa, "tur": "dis", "u": None, "c": None, "k": None})
            continue
        u = len(uniteler) - 1
        unite = uniteler[u]
        if unite["sayfa"] is None:
            unite["sayfa"] = sayfa
        if katla(ad) in UNITE_EKLERI:
            akis.append({"sayfa": sayfa, "tur": "ek", "u": u, "c": None, "k": None})
            kapali = katla(ad) == "unite sonu degerlendirme"
            continue
        if no is not None:
            unite["cerceveler"].append({"no": int(no), "ad": ad, "sayfa": sayfa, "son_sayfa": None, "ciktilar": [],
                                        "basliklar": [], "konular": []})
            akis.append({"sayfa": sayfa, "tur": "cerceve", "u": u, "c": len(unite["cerceveler"]) - 1, "k": None})
            continue
        if not unite["cerceveler"]:
            raise YapiHatasi(f"çerçevesiz konu: {ad}")
        cer = unite["cerceveler"][-1]
        cer["konular"].append({"ad": ad, "sayfa": sayfa, "son_sayfa": None, "basliklar": []})
        akis.append({"sayfa": sayfa, "tur": "konu", "u": u, "c": len(unite["cerceveler"]) - 1, "k": len(cer["konular"]) - 1})
    if bekleyen:
        raise YapiHatasi(f"tanınmayan İçindekiler satırı: {bekleyen}")
    if not uniteler:
        raise YapiHatasi("İçindekiler'de ünite yok")

    def bitis(i: int, ayni) -> int:
        """i'den sonra `ayni` olmayan ilk girdinin sayfası − 1 (aynı sayfadaysa kendi sayfası)."""
        for j in range(i + 1, len(akis)):
            if not ayni(akis[j]):
                return max(akis[j]["sayfa"] - 1, akis[i]["sayfa"])
        raise YapiHatasi(f"bitiş sayfası okunamadı: s. {akis[i]['sayfa']}")

    for i, a in enumerate(akis):
        if a["tur"] == "konu":
            uniteler[a["u"]]["cerceveler"][a["c"]]["konular"][a["k"]]["son_sayfa"] = bitis(i, lambda b: False)
        elif a["tur"] == "cerceve":
            uniteler[a["u"]]["cerceveler"][a["c"]]["son_sayfa"] = bitis(
                i, lambda b, a=a: b["tur"] == "konu" and b["u"] == a["u"] and b["c"] == a["c"])
    for u, unite in enumerate(uniteler):
        if unite["sayfa"] is None or not unite["cerceveler"]:
            raise YapiHatasi(f"{unite['no']}. ünitede içerik çerçevesi yok")
        son = max(i for i, a in enumerate(akis) if a["u"] == u)
        unite["son_sayfa"] = bitis(son, lambda b: False)
    return uniteler
