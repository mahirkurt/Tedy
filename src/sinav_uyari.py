"""Sınav uyarıları (spec §6): hangi uyarının vadesi geldiğini hesaplar (saf),
metni hitapla kurar, web push ile yollar ve defterine yazar.

systemd zamanlayıcısıyla 10 dakikada bir koşar; senkron kilidini almaz,
sinavlar.json'u yalnız okur. Bir kişiye bir sınav için aynı turda vadesi gelen
uyarılar tek bildirimde birleşir; defter anahtarı (email, sinav_id, tur,
icerik_surumu) olduğundan aynı uyarı iki kez gitmez, sınav değişirse yeni
sürüm yeniden "tespit" doğurur. 22:00–07:30 arası hiçbir şey gitmez."""
from __future__ import annotations

import fcntl
import json
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterator

from src import sinav_tespiti, web_push
from src.json_utils import atomic_json_dump
from src.roles import is_full, okur_turu
from src.sinav_tarihi import katla

SESSIZ_BAS = time(22, 0)
SESSIZ_SON = time(7, 30)
OKUL_BASI = time(8, 0)
HATIRLATMA = {"gun_7": (7, time(18, 0)), "gun_2": (2, time(18, 0)), "aksam": (1, time(19, 0))}
DEFTER = PurePosixPath("output/bildirim_defteri.jsonl")
DURUM = PurePosixPath("output/sinav_uyari_durumu.json")
BASLIK_SINIRI = 80
GOVDE_SINIRI = 300
GUN_ADLARI = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
AY_ADLARI = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim",
             "Kasım", "Aralık"]


def _sessiz(an: datetime) -> bool:
    return an.time() >= SESSIZ_BAS or an.time() < SESSIZ_SON


def _baslangic(s: dict) -> datetime | None:
    if not s.get("tarih"):
        return None
    saat = time.fromisoformat(s["saat"]) if s.get("saat") else OKUL_BASI
    return datetime.combine(date.fromisoformat(s["tarih"]), saat)


def _yerel(deger: Any) -> datetime | None:
    try:
        an = datetime.fromisoformat(str(deger))
    except (TypeError, ValueError):
        return None
    return an.replace(tzinfo=None)


def vadesi_gelen_turler(sinav: dict, simdi: datetime, sessiz_saat: bool = True) -> list[str]:
    if sinav.get("sentetik"):
        return []
    bas = _baslangic(sinav)
    if bas is not None and simdi >= bas:
        return []
    if bas is None and sinav.get("hafta") and date.fromisoformat(sinav["hafta"]) + timedelta(days=6) < simdi.date():
        return []
    if sessiz_saat and _sessiz(simdi):
        return []
    turler = ["tespit"]
    if bas is None:
        return turler
    ilk = _yerel(sinav.get("ilk_tespit"))
    for tur, (gun, saat) in HATIRLATMA.items():
        hedef = datetime.combine(bas.date() - timedelta(days=gun), saat)
        if hedef <= simdi and (ilk is None or hedef >= ilk):
            turler.append(tur)
    return turler


@dataclass(frozen=True)
class Bildirim:
    email: str
    sinav: dict
    turler: tuple[str, ...]


def planla(sinavlar: list[dict], alicilar: list[str], gonderilmis: set[tuple], simdi: datetime) -> list[Bildirim]:
    plan = []
    for s in sinavlar:
        vadeli = vadesi_gelen_turler(s, simdi)
        for email in alicilar:
            yeni = tuple(t for t in vadeli if (email, s["id"], t, s["icerik_surumu"]) not in gonderilmis)
            if yeni:
                plan.append(Bildirim(email, s, yeni))
    return plan


def _kirp(metin: str, sinir: int) -> str:
    metin = " ".join(metin.split())
    return metin if len(metin) <= sinir else metin[: sinir - 1].rstrip() + "…"


def gun_ifadesi(hedef: date, bugun: date) -> str:
    fark = (hedef - bugun).days
    if fark == 0:
        return "Bugün"
    if fark == 1:
        return "Yarın"
    if 1 < fark < 7:
        return GUN_ADLARI[hedef.weekday()]
    return f"{hedef.day} {AY_ADLARI[hedef.month - 1]} {GUN_ADLARI[hedef.weekday()]}"


def kisa_ad(sinav: dict) -> str:
    ders, baslik = str(sinav.get("ders") or ""), str(sinav.get("baslik") or "Sınav")
    ad = baslik if ders == "Genel" or katla(baslik).startswith(katla(ders)) else f"{ders} {baslik}"
    return _kirp(ad, 50)


def _konu_ozeti(konular: list[str]) -> str:
    ilk = [_kirp(k, 60) for k in konular[:3]]
    return ", ".join(ilk) + (" …" if len(konular) > 3 else "")


def metin_kur(sinav: dict, okur: str, turler: tuple[str, ...], simdi: datetime) -> tuple[str, str]:
    ad = kisa_ad(sinav)
    konu = _konu_ozeti(list(sinav.get("konular") or []))
    sinav_sozu = "" if "sinav" in katla(ad) else " sınavı"
    if not sinav.get("tarih"):
        hafta = sinav.get("hafta")
        zaman = (f"{date.fromisoformat(hafta).day} {AY_ADLARI[date.fromisoformat(hafta).month - 1]} haftası"
                 if hafta else "tarihi belli değil")
        baslik = f"Yeni sınav: {ad}"
        if okur == "ogrenci":
            govde = f"{ad} duyuruldu ({zaman})" + (f" — {konu}" if konu else "") + ". Ayrıntı TEDY'de."
        else:
            govde = f"Işık'ın {ad}{sinav_sozu} duyuruldu ({zaman})." + (f" Konular: {konu}" if konu else "")
        return _kirp(baslik, BASLIK_SINIRI), _kirp(govde, GOVDE_SINIRI)

    gun = gun_ifadesi(date.fromisoformat(sinav["tarih"]), simdi.date())
    degisti = "tespit" in turler and bool(sinav.get("degisti"))
    baslik = f"{'Sınav güncellendi' if degisti else 'Sınav'}: {ad} · {gun}"
    if okur == "ogrenci":
        if gun == "Bugün":
            son = "Başarılar!"
        elif "aksam" in turler:
            son = "Çantanı hazırla, erken uyu."
        else:
            son = "Bugün 10 dakikayla başla?"
        govde = f"{gun} {ad} var" + (f" — {konu}" if konu else "") + f". {son}"
        if konu.endswith("…"):
            govde = f"{gun} {ad} var — {konu} {son}"
    else:
        gun_sozu = gun.lower() if gun in ("Bugün", "Yarın") else gun
        govde = f"Işık'ın {gun_sozu} {ad}{sinav_sozu} var." + (f" Konular: {konu}" if konu else "")
    return _kirp(baslik, BASLIK_SINIRI), _kirp(govde, GOVDE_SINIRI)


class BildirimDefteri:
    def __init__(self, yol: str | Path):
        self.yol = Path(yol)

    @contextmanager
    def _kilitli(self) -> Iterator[None]:
        self.yol.parent.mkdir(parents=True, exist_ok=True)
        with open(self.yol.with_name(self.yol.name + ".lock"), "a") as kilit:
            fcntl.flock(kilit, fcntl.LOCK_EX)
            yield

    def anahtarlar(self) -> set[tuple[str, str, str, str]]:
        sonuc = set()
        try:
            satirlar = self.yol.read_text(encoding="utf-8").splitlines()
        except OSError:
            return sonuc
        for satir in satirlar:
            try:
                k = json.loads(satir)
                sonuc.add((k["email"], k["sinav_id"], k["tur"], k["icerik_surumu"]))
            except (ValueError, KeyError, TypeError):
                continue
        return sonuc

    def yaz(self, email: str, sinav: dict, turler: tuple[str, ...], simdi: datetime) -> None:
        with self._kilitli(), self.yol.open("a", encoding="utf-8") as f:
            for tur in turler:
                f.write(json.dumps({"zaman": simdi.isoformat(timespec="seconds"), "email": email,
                                    "sinav_id": sinav["id"], "tur": tur,
                                    "icerik_surumu": sinav["icerik_surumu"]}, ensure_ascii=False) + "\n")


def _alicilar(depo: web_push.AbonelikDeposu) -> list[str]:
    return sorted(e for e in depo.hepsi() if is_full(e))


def _durum_yaz(kok: Path, durum: dict) -> dict:
    atomic_json_dump(durum, str(kok / DURUM))
    return durum


def gonder_turu(kok: Path, simdi: datetime, gonderici: Callable[..., web_push.GonderimSonucu] | None = None) -> dict:
    kok = Path(kok)
    durum = {"son_tur": simdi.isoformat(timespec="seconds"), "kapali": False, "gonderilen": 0,
             "olu_silinen": 0, "hatalar": [], "abone_kisi": 0}
    if os.environ.get("TEDY_SINAV_UYARI", "0") != "1":
        return _durum_yaz(kok, {**durum, "kapali": True})
    belge = sinav_tespiti.oku(kok)
    vapid = web_push.vapid_ayarlari()
    if belge is None or vapid is None:
        return _durum_yaz(kok, {**durum, "hatalar": ["sinavlar.json yok" if belge is None else "VAPID ayarlı değil"]})
    gonderici = gonderici or web_push.gonder
    depo = web_push.AbonelikDeposu(kok / web_push.ABONELIKLER)
    defter = BildirimDefteri(kok / DEFTER)
    alicilar = _alicilar(depo)
    durum["abone_kisi"] = len(alicilar)
    for b in planla(belge["sinavlar"], alicilar, defter.anahtarlar(), simdi):
        baslik, govde = metin_kur(b.sinav, okur_turu(b.email), b.turler, simdi)
        yuk = {"baslik": baslik, "govde": govde, "etiket": b.sinav["id"], "url": f"/sinavlar?sinav={b.sinav['id']}"}
        basarili = False
        for cihaz in depo.kisinin(b.email):
            sonuc = gonderici(cihaz["abonelik"], yuk, vapid)
            if sonuc.durum == "ok":
                basarili = True
            elif sonuc.durum == "olu":
                durum["olu_silinen"] += depo.endpoint_sil(cihaz["abonelik"]["endpoint"])
            else:
                durum["hatalar"].append(f"{sonuc.kod}: {sonuc.mesaj}"[:160])
        if basarili:
            defter.yaz(b.email, b.sinav, b.turler, simdi)
            durum["gonderilen"] += 1
    durum["hatalar"] = durum["hatalar"][:5]
    return _durum_yaz(kok, durum)


def _tohum(kok: Path, emails: list[str], simdi: datetime) -> int:
    belge = sinav_tespiti.oku(Path(kok))
    if belge is None:
        return 0
    defter = BildirimDefteri(Path(kok) / DEFTER)
    eski = defter.anahtarlar()
    sayi = 0
    for s in belge["sinavlar"]:
        vadeli = vadesi_gelen_turler(s, simdi, sessiz_saat=False)
        for email in emails:
            yeni = tuple(t for t in vadeli if (email, s["id"], t, s["icerik_surumu"]) not in eski)
            if yeni:
                defter.yaz(email, s, yeni, simdi)
                sayi += len(yeni)
    return sayi


def kisiyi_tohumla(kok: Path, email: str, simdi: datetime) -> int:
    """A person's first device: mark what is already due as sent."""
    return _tohum(Path(kok), [email], simdi)


def tohumla(kok: Path, simdi: datetime) -> int:
    """Rollout: mark everything already due for every subscriber as sent."""
    depo = web_push.AbonelikDeposu(Path(kok) / web_push.ABONELIKLER)
    return _tohum(Path(kok), _alicilar(depo), simdi)


def main(argv: list[str] | None = None) -> int:
    from src.env_loader import load_env
    load_env()
    kok = Path(__file__).resolve().parents[1]
    komut = (argv if argv is not None else sys.argv[1:])[:1]
    if komut == ["gonder"]:
        durum = gonder_turu(kok, datetime.now())
        print(json.dumps(durum, ensure_ascii=False))
        return 0
    if komut == ["tohumla"]:
        print(f"tohumlanan uyarı: {tohumla(kok, datetime.now())}")
        return 0
    print("kullanım: python -m src.sinav_uyari gonder|tohumla", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
