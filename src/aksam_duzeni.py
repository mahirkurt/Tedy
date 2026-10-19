"""Hanenin akşam düzeni: ödeve hazır olma saatinden yatmaya kadar tek ayar.

Saf mantık burada (Flask'sız): varsayılanlar, doğrulama, okuma. Dosya
``output/aksam_duzeni.json``; eski ``output/odak_penceresi.json`` yalnız yeni
dosya yokken ``okul_bitisi`` ve ``yatma`` için okunur.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

VARSAYILAN: dict[str, Any] = {
    "odeve_hazir": "17:00",
    "zor_is_sonu": "19:00",
    "hafif_is_sonu": "19:30",
    "yemek": "18:30",
    "yemek_dk": 30,
    "hazirlik": "20:30",
    "yatma": "21:00",
    "okul_bitisi": "15:45",
    "baslamadi_esik_dk": 15,
    "takildi_esik_dk": 15,
    "haber_alacaklar": [],
}

_SAAT_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
_SAAT_ALANLARI = ("okul_bitisi", "odeve_hazir", "zor_is_sonu", "hafif_is_sonu", "hazirlik", "yatma", "yemek")


def dakika(saat: str) -> int:
    """``"HH:MM"`` → günün dakikası."""
    s, d = saat.split(":")
    return int(s) * 60 + int(d)


def _sayi(deger: Any, alt: int, ust: int) -> int | None:
    if isinstance(deger, bool) or not isinstance(deger, int):
        return None
    return deger if alt <= deger <= ust else None


def dogrula(govde: Any, aile_epostalari: set[str]) -> tuple[dict | None, str | None]:
    """``(düzen, None)`` ya da ``(None, tek Türkçe cümle)``."""
    if not isinstance(govde, dict):
        return None, "Akşam düzeni bir saat listesi olarak gönderilmeli."
    d: dict[str, Any] = {}
    for alan in _SAAT_ALANLARI:
        deger = str(govde.get(alan) or "").strip()
        if not _SAAT_RE.match(deger):
            return None, "Her saat SS:DD biçiminde olmalı (örneğin 17:00)."
        d[alan] = deger
    d["yemek_dk"] = _sayi(govde.get("yemek_dk"), 10, 60)
    if d["yemek_dk"] is None:
        return None, "Yemek süresi 10 ile 60 dakika arasında olmalı."
    for alan in ("baslamadi_esik_dk", "takildi_esik_dk"):
        d[alan] = _sayi(govde.get(alan), 5, 60)
        if d[alan] is None:
            return None, "Haber verme süreleri 5 ile 60 dakika arasında olmalı."
    m = {a: dakika(d[a]) for a in _SAAT_ALANLARI}
    if not (m["okul_bitisi"] <= m["odeve_hazir"] < m["zor_is_sonu"] <= m["hafif_is_sonu"]
            <= m["hazirlik"] < m["yatma"]):
        return None, ("Saatler sırayla olmalı: okul bitişi, ödeve hazır, zor işlerin sonu, "
                      "hafif işlerin sonu, hazırlık, sonra yatma.")
    if not (m["odeve_hazir"] <= m["yemek"] <= m["hazirlik"] - d["yemek_dk"]):
        return None, "Yemek, ödeve hazır olma saati ile hazırlık arasında kalmalı ve süresi sığmalı."
    kisiler = govde.get("haber_alacaklar", [])
    if not isinstance(kisiler, list):
        return None, "Haber alacaklar bir e-posta listesi olmalı."
    izinli = {e.strip().lower() for e in aile_epostalari}
    temiz: list[str] = []
    for k in kisiler:
        e = str(k).strip().lower()
        if e not in izinli:
            return None, "Haber yalnız aile üyelerine gönderilebilir."
        if e not in temiz:
            temiz.append(e)
    d["haber_alacaklar"] = temiz
    return d, None


def oku(yol: Path, eski: Path | None = None) -> dict:
    """Her zaman tam bir düzen + ``"varsayilan"`` bayrağı. Bozuk dosya → varsayılan."""
    yol = Path(yol)
    try:
        with open(yol, "r", encoding="utf-8") as f:
            ham = json.load(f)
        if isinstance(ham, dict):
            tam = {**VARSAYILAN, **{k: v for k, v in ham.items() if k in VARSAYILAN}}
            # Kayıtlı e-postalar sonradan aileden çıkmış olabilir; burada yalnız biçim denetlenir.
            d, _hata = dogrula(tam, set(tam.get("haber_alacaklar") or []) if isinstance(tam.get("haber_alacaklar"), list) else set())
            if d is not None:
                return {**d, "varsayilan": False}
    except (OSError, ValueError):
        pass
    if not yol.exists() and eski is not None:
        try:
            with open(eski, "r", encoding="utf-8") as f:
                ham = json.load(f)
            if isinstance(ham, dict):
                tam = {**VARSAYILAN}
                for alan in ("okul_bitisi", "yatma"):
                    if _SAAT_RE.match(str(ham.get(alan) or "")):
                        tam[alan] = ham[alan]
                d, _hata = dogrula(tam, set())
                if d is not None:
                    return {**d, "varsayilan": False}
        except (OSError, ValueError):
            pass
    return {**VARSAYILAN, "haber_alacaklar": [], "varsayilan": True}
