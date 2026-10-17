"""Müfredat ağacı (7. sınıf ders → ünite → ders kitabı alt başlığı) okuyucusu ve şeması.

Dosya `scripts/mufredat_agaci.py` tarafından üretilir, elle düzenlenmez (spec §2). Burada
yalnız okuma ve şema doğrulaması vardır: pano `src/mcp_server`'ı, ted-mcp `src/dashboard_api`'yi
import etmediği için bu modül **yalnız stdlib** kullanır (`src/module_store.py` ile aynı kural).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterator

AGAC_ADI = "mufredat_agaci.json"
KAZANIM_KAYNAKLARI = ("metin-ortusmesi", "eslenmedi")
SAYFA_KAYNAKLARI = ("icindekiler", "yok")
# module_store.SLUG_RE ile aynı alfabe: kimlik iki yere sızıyor (localStorage, asistan bağlamı).
KIMLIK_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def agac_yolu(kok: Path | str) -> Path:
    return Path(kok) / AGAC_ADI


def _tam_sayi(deger: Any) -> bool:
    return isinstance(deger, int) and not isinstance(deger, bool)


def _konu_hatalari(konu: Any, nerede: str) -> list[str]:
    if not isinstance(konu, dict):
        return [f"{nerede}: konu sözlük değil"]
    hatalar = []
    for alan in ("id", "ad", "ad_kaynak"):
        if not isinstance(konu.get(alan), str) or not konu[alan].strip():
            hatalar.append(f"{nerede}: {alan} boş ya da dize değil")
    if isinstance(konu.get("id"), str) and not KIMLIK_RE.fullmatch(konu["id"]):
        hatalar.append(f"{nerede}: id slug alfabesinde değil")
    if konu.get("sayfa_kaynak") not in SAYFA_KAYNAKLARI:
        hatalar.append(f"{nerede}: sayfa_kaynak bilinmiyor")
    if konu.get("kazanim_kaynak") not in KAZANIM_KAYNAKLARI:
        hatalar.append(f"{nerede}: kazanim_kaynak bilinmiyor")
    # Sayfa uydurulmaz: kaynak "yok" ise alan hiç bulunmaz (spec §2.1).
    if konu.get("sayfa_kaynak") == "yok" and "sayfa" in konu:
        hatalar.append(f"{nerede}: sayfa_kaynak 'yok' ama sayfa alanı var")
    if konu.get("sayfa_kaynak") == "icindekiler":
        sayfa = konu.get("sayfa")
        if (not isinstance(sayfa, list) or len(sayfa) != 2 or not all(_tam_sayi(s) for s in sayfa)
                or sayfa[0] < 1 or sayfa[1] < sayfa[0]):
            hatalar.append(f"{nerede}: sayfa [başlangıç, bitiş] değil")
    if not isinstance(konu.get("kazanimlar"), list) or not all(
            isinstance(k, str) for k in konu["kazanimlar"]):
        hatalar.append(f"{nerede}: kazanimlar dize listesi değil")
    if not _tam_sayi(konu.get("kitap")):
        hatalar.append(f"{nerede}: kitap belge kimliği değil")
    return hatalar


def dogrula(payload: Any) -> list[str]:
    """Şema hatalarının listesi; boş liste geçerli demektir."""
    if not isinstance(payload, dict):
        return ["gövde sözlük değil"]
    hatalar = []
    if payload.get("surum") != 1:
        hatalar.append("surum 1 değil")
    for alan in ("korpus_surumu", "sinif"):
        if not isinstance(payload.get(alan), str) or not payload[alan].strip():
            hatalar.append(f"{alan} boş ya da dize değil")
    if not isinstance(payload.get("kapsam"), dict):
        hatalar.append("kapsam sözlük değil")
    dersler = payload.get("dersler")
    if not isinstance(dersler, list):
        return hatalar + ["dersler liste değil"]
    kimlikler: set[str] = set()
    for ders in dersler:
        if not isinstance(ders, dict):
            hatalar.append("ders sözlük değil")
            continue
        slug = ders.get("slug")
        if not isinstance(slug, str) or not KIMLIK_RE.fullmatch(slug or ""):
            hatalar.append("ders slug'ı geçersiz")
            slug = "?"
        if not isinstance(ders.get("ders"), str) or not ders["ders"].strip():
            hatalar.append(f"{slug}: ders adı boş")
        if not isinstance(ders.get("kitaplar"), list):
            hatalar.append(f"{slug}: kitaplar liste değil")
        uniteler = ders.get("uniteler")
        if not isinstance(uniteler, list):
            hatalar.append(f"{slug}: uniteler liste değil")
            continue
        for unite in uniteler:
            if not isinstance(unite, dict):
                hatalar.append(f"{slug}: ünite sözlük değil")
                continue
            if not _tam_sayi(unite.get("no")):
                hatalar.append(f"{slug}: ünite no tam sayı değil")
            if not isinstance(unite.get("ad"), str) or not unite["ad"].strip():
                hatalar.append(f"{slug}: ünite adı boş")
            konular_listesi = unite.get("konular")
            if not isinstance(konular_listesi, list):
                hatalar.append(f"{slug}/{unite.get('no')}: konular liste değil")
                continue
            for konu in konular_listesi:
                nerede = f"{slug}/{unite.get('no')}"
                hatalar.extend(_konu_hatalari(konu, nerede))
                kimlik = konu.get("id") if isinstance(konu, dict) else None
                if isinstance(kimlik, str):
                    if kimlik in kimlikler:
                        hatalar.append(f"{nerede}: id yinelendi ({kimlik})")
                    kimlikler.add(kimlik)
    return hatalar


def oku(yol: Path | str) -> tuple[str, dict | None]:
    """("ok", ağaç) | ("yok", None) | ("bozuk", None). Hiçbir durumda yükseltmez."""
    try:
        metin = Path(yol).read_text(encoding="utf-8")
    except FileNotFoundError:
        return "yok", None
    except OSError:
        return "bozuk", None
    try:
        payload = json.loads(metin)
    except ValueError:
        return "bozuk", None
    if dogrula(payload):
        return "bozuk", None
    return "ok", payload


def konular(agac: dict) -> Iterator[tuple[dict, dict, dict]]:
    for ders in agac.get("dersler") or []:
        for unite in ders.get("uniteler") or []:
            for konu in unite.get("konular") or []:
                yield ders, unite, konu


def konu_bul(agac: dict, konu_id: str) -> tuple[dict, dict, dict] | None:
    return next((ucu for ucu in konular(agac) if ucu[2].get("id") == konu_id), None)
