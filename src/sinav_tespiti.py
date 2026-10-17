"""Sınav tespiti (spec §4, §5 "Birleştirme"): takvim + not tablosu tabanı ile
serbest metin bulgularını tek listede birleştirir ve output/sinavlar.json'u
yazar. Kayıt kimliği: takvimde varsa takvimin kendi kimliği (modüller bağlı,
değişmez), yoksa ders+tür+tarih özeti."""
from __future__ import annotations

import hashlib
import json
import re
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
KONU_EN_AZ = 4
ORTAK_TURLER = ("deneme", "ortak_sinav")


# Anahtar sözcükler katlanmış başlıkta sözcük sınırıyla aranır ("bilgisayar" içindeki "gis" deneme sayılmaz).
# Kısa kökler (<= 4 harf) tam sözcük olmalı; uzun kökler Türkçe ek alabilir ("denemesi", "yazılısı").
_TUR_KURALLARI = (
    ("ortak_sinav", ("ortak",)),
    ("konu_tarama", ("ktt", "konu tarama")),
    ("deneme", ("deneme", "gis", "izleme", "hazirbulunusluk", "kazanim degerlendirme")),
    ("yazili", ("yazili",)),
    ("kisa_sinav", ("quiz", "kisa sinav")),
)


def _sozcuk_var(katli: str, anahtar: str) -> bool:
    son = r"(?![a-z0-9])" if len(anahtar) <= 4 else r""
    return re.search(rf"(?<![a-z0-9]){re.escape(anahtar)}{son}", katli) is not None


def takvim_turu(baslik: str) -> str:
    k = katla(baslik)
    for tur, anahtarlar in _TUR_KURALLARI:
        if any(_sozcuk_var(k, a) for a in anahtarlar):
            return tur
    return "diger"


def _md5(metin: str) -> str:
    return hashlib.md5(metin.encode("utf-8")).hexdigest()[:12]


def _tabandan(e: dict) -> dict:
    tarih_saat = str(e.get("date") or "")
    sentetik = not tarih_saat
    if tarih_saat:
        try:
            date.fromisoformat(tarih_saat[:10])
        except ValueError:
            tarih_saat = ""   # bozuk tarih: tarihsiz takvim sınavı (sentetik değil; takvim kaynağı ve kimliği var)
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
    ka = [x for x in (katla(t) for t in a) if len(x) >= KONU_EN_AZ]
    kb = [y for y in (katla(t) for t in b) if len(y) >= KONU_EN_AZ]
    return any(x in y or y in x for x in ka for y in kb)


def _tek(adaylar: list[dict]) -> dict | None:
    return adaylar[0] if len(adaylar) == 1 else None


def _surum(k: dict) -> str:
    konular = sorted({katla(x) for x in k["konular"]})
    govde = f"{k['tarih']}|{k['saat']}|{k['hafta']}|" + "|".join(konular)
    return hashlib.sha256(govde.encode("utf-8")).hexdigest()[:12]


def birlestir(taban: list[dict], bulgular: list[Bulgu], onceki: dict | None, simdi: datetime) -> list[dict]:
    kayitlar = [_tabandan(e) for e in taban if isinstance(e, dict) and e.get("id")]
    tarihliler = [b for b in bulgular if b.tarih]
    tarihsizler = [b for b in bulgular if not b.tarih]

    for b in tarihliler:
        gun = b.tarih.isoformat()
        eslesen = next((k for k in kayitlar if not k["sentetik"] and k["tarih"] == gun
                        and (katla(k["ders"]) == katla(b.ders) or (b.ders == "Genel" and k["taban"]))), None)
        if eslesen is None and b.tur in ORTAK_TURLER:
            # A shared exam (GİS, a common written) is often announced in one course's tab: its
            # takvim record carries another course name. Same day is enough — preferring a takvim
            # record of a shared kind, then any takvim record of that day.
            gunun = [k for k in kayitlar if k["taban"] and not k["sentetik"] and k["tarih"] == gun]
            eslesen = next((k for k in gunun if k["tur"] in ORTAK_TURLER), gunun[0] if gunun else None)
        if eslesen is None:
            eslesen = _bulgudan(b, _md5(f"{b.ders}|{gun}"))
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
            kimlik = _md5(f"{b.ders}|{ek}")
            hedef = next((k for k in kayitlar if k["id"] == kimlik), None)
            if hedef is None:
                hedef = _bulgudan(b, kimlik)
                kayitlar.append(hedef)
        _ekle(hedef, b)

    bugun = simdi.date()
    for k in kayitlar:   # kaynağın yayın tarihi yoksa kayıt bu çalıştırmada görüldü sayılır, hemen düşmez
        if not k["sentetik"] and not k["tarih"] and not k["hafta"] and not k["son_yayin"]:
            k["son_yayin"] = bugun.isoformat()
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


PROJE_KOKU = Path(__file__).resolve().parents[1]


def tespit_et(kok: Path, veri: dict, taban: list[dict], simdi: datetime, bitis: float,
              okuyucu: Any = None) -> dict:
    from src.sinav_cikarimi import ClaudeSinavOkuyucu, SinavCikarici
    from src.sinav_kaynaklari import adaylar, kaynak_verisi

    kok = Path(kok)
    ekler, ilk_gorulme = kaynak_verisi(kok)
    liste = adaylar(veri, simdi.date(), ek_metinleri=ekler, odev_ilk_gorulme=ilk_gorulme)
    sonuc = SinavCikarici(kok, okuyucu or ClaudeSinavOkuyucu()).cikar(liste, simdi.date(), bitis)
    onceki = oku(kok)
    if onceki is None and (kok / SINAVLAR).exists():
        # A file that is there but unreadable (torn, an older SURUM) is not a first
        # install: None would stamp every record "already there" and swallow its alert.
        onceki = {"surum": SURUM, "sinavlar": []}
    kayitlar = birlestir(taban, sonuc.bulgular, onceki, simdi)
    return {"uretildi": simdi.isoformat(timespec="seconds"), "surum": SURUM, "sinavlar": kayitlar,
            "ozet": {"aday": sonuc.aday, "incelenen": sonuc.incelenen, "incelenmedi": sonuc.incelenmedi,
                     "butce_usd": sonuc.butce_usd, "hatalar": sonuc.hatalar[:5]}}


def kuru_rapor(belge: dict) -> str:
    satirlar = []
    for k in belge.get("sinavlar") or []:
        zaman = k.get("tarih") or (f"{k['hafta']} haftası" if k.get("hafta") else "tarih belirsiz")
        if k.get("saat"):
            zaman += f" {k['saat']}"
        satirlar.append(f"- {k.get('ders')} · {k.get('tur')} · {zaman} · {k.get('baslik')}"
                        + (" (not tablosu)" if k.get("sentetik") else ""))
        if k.get("konular"):
            satirlar.append("  Konular: " + "; ".join(k["konular"]))
        for x in k.get("kaynaklar") or []:
            satirlar.append(f"  Kaynak: {x.get('tur')} {json.dumps(x.get('konum'), ensure_ascii=False)}"
                            f" — {str(x.get('alinti') or '')[:120]}")
    o = belge.get("ozet") or {}
    satirlar.append(f"Özet: {len(belge.get('sinavlar') or [])} sınav · aday {o.get('aday', 0)} · incelenen "
                    f"{o.get('incelenen', 0)} · incelenmedi {o.get('incelenmedi', 0)} · bütçe "
                    f"{o.get('butce_usd', 0)} USD")
    return "\n".join(satirlar)


def _taban(veri: dict) -> list[dict]:
    from src.dashboard_api import _sinav_listesi  # Flask app: imported only where it is needed
    return _sinav_listesi(veri)["exams"]


def main(argv: list[str] | None = None) -> int:
    import argparse
    import time

    from src.env_loader import load_env
    load_env()
    p = argparse.ArgumentParser(description="Sınav tespiti: sinavlar.json üretir")
    p.add_argument("--kuru", action="store_true", help="dosyaya yazmadan bulunanları yazdır")
    p.add_argument("--sure", type=float, default=300.0, help="model çağrıları için saniye")
    a = p.parse_args(argv)
    veri = json.loads((PROJE_KOKU / "output/scraped_data.json").read_text(encoding="utf-8"))
    belge = tespit_et(PROJE_KOKU, veri, _taban(veri), datetime.now(), time.monotonic() + a.sure)
    print(kuru_rapor(belge))
    if not a.kuru:
        yaz(PROJE_KOKU, belge)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
