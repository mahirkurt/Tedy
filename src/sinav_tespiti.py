"""Sınav tespiti (spec §4, §5 "Birleştirme"): takvim + not tablosu tabanı ile
serbest metin bulgularını tek listede birleştirir ve output/sinavlar.json'u
yazar. Kayıt kimliği: takvimde varsa takvimin kendi kimliği (modüller bağlı,
değişmez), yoksa ders+tür+tarih özeti."""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any

from src.json_utils import atomic_json_dump
from src.sinav_cikarimi import Bulgu
from src.sinav_tarihi import katla

SURUM = 1
SINAVLAR = PurePosixPath("output/sinavlar.json")
GECMIS_GUN = 30
TARIHSIZ_OMUR_GUN = 21
BAGLAMA_GUN = 14
KONU_SINIRI = 15
KAYNAK_SINIRI = 6


def takvim_turu(baslik: str) -> str:
    k = katla(baslik)
    if "ortak" in k:
        return "ortak_sinav"
    if "ktt" in k or "konu tarama" in k:
        return "konu_tarama"
    if any(s in k for s in ("deneme", "gis", "izleme", "hazirbulunusluk", "kazanim degerlendirme")):
        return "deneme"
    if "yazili" in k:
        return "yazili"
    if "quiz" in k or "kisa sinav" in k:
        return "kisa_sinav"
    return "diger"


def _md5(metin: str) -> str:
    return hashlib.md5(metin.encode("utf-8")).hexdigest()[:12]


def _tabandan(e: dict) -> dict:
    tarih_saat = str(e.get("date") or "")
    sentetik = not tarih_saat
    saat = tarih_saat[11:16] if len(tarih_saat) >= 16 and not e.get("allDay") else None
    kaynak = ({"tur": "not_tablosu", "konum": {"id": e.get("id")}, "alinti": str(e.get("rawTitle") or "")[:300]}
              if sentetik else
              {"tur": "takvim", "konum": {"id": e.get("id")}, "alinti": str(e.get("rawTitle") or "")[:300]})
    return {"id": e.get("id"), "ders": e.get("course") or "Genel", "tur": takvim_turu(e.get("title") or ""),
            "baslik": e.get("title") or e.get("rawTitle") or "Sınav", "tarih": tarih_saat[:10] or None,
            "saat": saat, "hafta": None, "konular": [], "kaynaklar": [kaynak], "sentetik": sentetik,
            "taban": e, "son_yayin": None}


def _bulgudan(b: Bulgu, kimlik: str) -> dict:
    return {"id": kimlik, "ders": b.ders, "tur": b.tur, "baslik": b.baslik,
            "tarih": b.tarih.isoformat() if b.tarih else None, "saat": b.saat,
            "hafta": b.hafta.isoformat() if b.hafta and not b.tarih else None,
            "konular": [], "kaynaklar": [], "sentetik": False, "taban": None, "son_yayin": None}


def _ekle(kayit: dict, b: Bulgu) -> None:
    for k in b.konular:
        if katla(k) not in {katla(x) for x in kayit["konular"]}:
            kayit["konular"].append(k)
    for konum in b.aday.konumlar:
        kaynak = {"tur": b.aday.tur, "konum": konum, "alinti": b.alinti[:300]}
        if kaynak not in kayit["kaynaklar"]:
            kayit["kaynaklar"].append(kaynak)
    if b.saat and not kayit["saat"]:
        kayit["saat"] = b.saat
    if b.aday.yayin and (kayit["son_yayin"] is None or b.aday.yayin.isoformat() > kayit["son_yayin"]):
        kayit["son_yayin"] = b.aday.yayin.isoformat()


def _konu_ortusur(a: list[str], b: list[str]) -> bool:
    ka, kb = [katla(x) for x in a], [katla(x) for x in b]
    return any(x and y and (x in y or y in x) for x in ka for y in kb)


def _tek(adaylar: list[dict]) -> dict | None:
    return adaylar[0] if len(adaylar) == 1 else None


def _surum(k: dict) -> str:
    govde = f"{k['tarih']}|{k['saat']}|{k['hafta']}|" + "|".join(k["konular"])
    return hashlib.sha256(govde.encode("utf-8")).hexdigest()[:12]


def birlestir(taban: list[dict], bulgular: list[Bulgu], onceki: dict | None, simdi: datetime) -> list[dict]:
    kayitlar = [_tabandan(e) for e in taban if isinstance(e, dict) and e.get("id")]
    tarihliler = [b for b in bulgular if b.tarih]
    tarihsizler = [b for b in bulgular if not b.tarih]

    for b in tarihliler:
        gun = b.tarih.isoformat()
        eslesen = next((k for k in kayitlar if not k["sentetik"] and k["tarih"] == gun
                        and (katla(k["ders"]) == katla(b.ders) or (b.ders == "Genel" and k["taban"]))), None)
        if eslesen is None:
            eslesen = _bulgudan(b, _md5(f"{b.ders}|{b.tur}|{gun}"))
            kayitlar.append(eslesen)
        _ekle(eslesen, b)

    for b in tarihsizler:
        ayni_ders = [k for k in kayitlar if k["tarih"] and not k["sentetik"] and katla(k["ders"]) == katla(b.ders)]
        hedef = None
        if b.hafta:
            son = b.hafta + timedelta(days=6)
            hedef = _tek([k for k in ayni_ders if b.hafta.isoformat() <= k["tarih"] <= son.isoformat()])
        elif b.konular and b.aday.yayin:
            son = b.aday.yayin + timedelta(days=BAGLAMA_GUN)
            hedef = _tek([k for k in ayni_ders if b.aday.yayin.isoformat() <= k["tarih"] <= son.isoformat()
                          and _konu_ortusur(k["konular"], b.konular)])
        if hedef is None:
            ek = f"hafta:{b.hafta.isoformat()}" if b.hafta else b.aday.anahtar[:12]
            kimlik = _md5(f"{b.ders}|{b.tur}|{ek}")
            hedef = next((k for k in kayitlar if k["id"] == kimlik), None)
            if hedef is None:
                hedef = _bulgudan(b, kimlik)
                kayitlar.append(hedef)
        _ekle(hedef, b)

    bugun = simdi.date()
    kalan = []
    for k in kayitlar:
        if k["sentetik"]:
            kalan.append(k)
        elif k["tarih"]:
            if date.fromisoformat(k["tarih"]) >= bugun - timedelta(days=GECMIS_GUN):
                kalan.append(k)
        elif k["hafta"]:
            if date.fromisoformat(k["hafta"]) + timedelta(days=6) >= bugun - timedelta(days=GECMIS_GUN):
                kalan.append(k)
        elif k["son_yayin"] and date.fromisoformat(k["son_yayin"]) >= bugun - timedelta(days=TARIHSIZ_OMUR_GUN):
            kalan.append(k)

    eski = {k.get("id"): k for k in ((onceki or {}).get("sinavlar") or []) if isinstance(k, dict)}
    an = simdi.isoformat(timespec="seconds")
    for k in kalan:
        k["konular"] = k["konular"][:KONU_SINIRI]
        k["kaynaklar"] = k["kaynaklar"][:KAYNAK_SINIRI]
        k["icerik_surumu"] = _surum(k)
        o = eski.get(k["id"])
        if o is not None:
            k["ilk_tespit"] = o.get("ilk_tespit")
            k["degisti"] = an if o.get("icerik_surumu") != k["icerik_surumu"] else o.get("degisti")
        else:
            k["ilk_tespit"] = None if onceki is None else an
            k["degisti"] = None

    def sira(k: dict) -> tuple:
        if k["sentetik"]:
            return (2, "")
        if k["tarih"]:
            return (0, f"{k['tarih']}T{k['saat'] or '00:00'}")
        return (1, k["hafta"] or "9999")
    return sorted(kalan, key=sira)


def gecerli_belge(veri: Any) -> dict | None:
    if not isinstance(veri, dict) or veri.get("surum") != SURUM or not isinstance(veri.get("sinavlar"), list):
        return None
    return veri


def oku(kok: Path) -> dict | None:
    try:
        return gecerli_belge(json.loads((Path(kok) / SINAVLAR).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return None


def yaz(kok: Path, belge: dict) -> None:
    atomic_json_dump(belge, str(Path(kok) / SINAVLAR))
