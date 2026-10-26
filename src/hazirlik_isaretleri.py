"""Kişi başına hazırlık işaretleri (spec 2026-10-25 §2.3): output/hazirlik_isaretleri.json.

{"surum": 1, "kisiler": {email: {ders anahtarı: {çıktı kodu: "hazirim" | "tekrar"}}}}. İki gunicorn işçisi aynı
dosyaya yazar: okuma-değiştirme-yazma `fcntl.flock` altında ve atomik; bozuk dosya yazmadan önce
`.bozuk-<YYYYmmddHHMMSS>` olarak kenara alınır (silinmez; yalnız ValueError/şema hatası 'bozuk' sayılır, OSError
yukarı geçer)."""
from __future__ import annotations

import fcntl
import json
import os
from datetime import datetime
from pathlib import Path

from src.json_utils import atomic_json_dump

SURUM = 1
DURUMLAR = ("hazirim", "tekrar")


class HazirlikIsaretleri:
    def __init__(self, yol: Path | str):
        self.yol = Path(yol)

    def _oku(self) -> tuple[dict, bool]:
        """(veri, bozuk_mu). Dosya yoksa boş veri, bozuk değil."""
        bos = {"surum": SURUM, "kisiler": {}}
        try:
            veri = json.loads(self.yol.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return bos, False
        except ValueError:
            # Yalnız içerik bozukluğu (JSON/UTF-8) 'bozuk'tur; OSError (izin, NFS, G/Ç) yukarı geçer — geçici bir
            # okuma hatası dosyayı kenara aldırıp işaretleri sessizce sıfırlamasın (API yazımda 503'e çevirir).
            return bos, True
        if not isinstance(veri, dict) or veri.get("surum") != SURUM or not isinstance(veri.get("kisiler"), dict):
            return bos, True
        return veri, False

    def _bozuk_kopya_adi(self) -> Path:
        """`.bozuk-<YYYYmmddHHMMSS>`; aynı saniyede ikinci kopya `-1`, `-2`… alır, öncekini ezmez."""
        taban = f"{self.yol.name}.bozuk-{datetime.now():%Y%m%d%H%M%S}"
        aday, n = self.yol.with_name(taban), 0
        while aday.exists():
            n += 1
            aday = self.yol.with_name(f"{taban}-{n}")
        return aday

    def kisi(self, email: str) -> dict[str, dict[str, str]]:
        kayit = self._oku()[0]["kisiler"].get(email.lower())
        if not isinstance(kayit, dict):
            return {}
        return {ders: {kod: d for kod, d in kodlar.items() if d in DURUMLAR}
                for ders, kodlar in kayit.items() if isinstance(kodlar, dict)}

    def yaz(self, email: str, ders: str, kod: str, durum: str | None) -> dict[str, str]:
        """İşareti koyar (`durum` None ise kaldırır); kişinin o dersteki işaretlerini döner."""
        if durum is not None and durum not in DURUMLAR:
            raise ValueError(f"geçersiz işaret: {durum}")
        self.yol.parent.mkdir(parents=True, exist_ok=True)
        with open(self.yol.with_name(f".{self.yol.name}.kilit"), "w") as kilit:
            fcntl.flock(kilit, fcntl.LOCK_EX)
            veri, bozuk = self._oku()
            if bozuk and self.yol.exists():
                os.replace(self.yol, self._bozuk_kopya_adi())
            kisiler = veri["kisiler"]
            kisi = kisiler.get(email.lower())
            if not isinstance(kisi, dict):
                kisi = kisiler[email.lower()] = {}
            kodlar = kisi.get(ders)
            if not isinstance(kodlar, dict):
                kodlar = kisi[ders] = {}
            if durum is None:
                kodlar.pop(kod, None)
            else:
                kodlar[kod] = durum
            if not kodlar:
                kisi.pop(ders, None)
            atomic_json_dump(veri, str(self.yol))
            return dict(kodlar)
