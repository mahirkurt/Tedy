"""Sınav uyarıları (spec §6): hangi uyarının vadesi geldiğini hesaplar (saf),
metni hitapla kurar, web push ile yollar ve defterine yazar.

systemd zamanlayıcısıyla 10 dakikada bir koşar; senkron kilidini almaz,
sinavlar.json'u yalnız okur. Bir kişiye bir sınav için aynı turda vadesi gelen
uyarılar tek bildirimde birleşir; defter anahtarı (email, sinav_id, tur,
icerik_surumu) olduğundan aynı uyarı iki kez gitmez, sınav değişirse yeni
sürüm yeniden "tespit" doğurur. 22:00–07:30 arası hiçbir şey gitmez.

Bir kişinin bir cihazı alıp öbürü geçici hata verirse defter yine yazılır (anahtar
kişi başınadır) ve hatalı cihaz `output/bildirim_bekleyen.json`'a girer: sonraki
turlar onu yalnız o cihaza, aynı uyarıyla dener; başarıda, altıncı denemede, cihaz
ölünce, sınav başlayınca ya da sürümü değişince kayıt silinir."""
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
BEKLEYEN = PurePosixPath("output/bildirim_bekleyen.json")
BEKLEYEN_DENEME_SINIRI = 6      # the first try counts: 1 + 5 retries, one per round
HATA_LISTESI_SINIRI = 5
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


def _hata_satiri(sinav: Any, exc: Exception) -> str:
    sid = sinav.get("id") if isinstance(sinav, dict) else None
    return f"{sid or '?'}: {exc}"[:160]


def planla(sinavlar: list[dict], alicilar: list[str], gonderilmis: set[tuple], simdi: datetime,
           hatalar: list[str] | None = None) -> list[Bildirim]:
    """A malformed exam record is skipped and named in `hatalar`; it never stops the others."""
    plan = []
    for s in sinavlar:
        try:
            vadeli = vadesi_gelen_turler(s, simdi)
            sid, surum = s["id"], s["icerik_surumu"]
            yeni_by_email = [(email, tuple(t for t in vadeli if (email, sid, t, surum) not in gonderilmis))
                             for email in alicilar]
        except Exception as exc:  # noqa: BLE001 - one bad record must not stop the round
            if hatalar is not None:
                hatalar.append(_hata_satiri(s, exc))
            continue
        plan.extend(Bildirim(email, s, yeni) for email, yeni in yeni_by_email if yeni)
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


class BekleyenKuyruk:
    """Devices that missed an alert the rest of the person's devices got (B9). One record per
    (email, endpoint, sinav_id, icerik_surumu); written under flock and atomically."""

    def __init__(self, yol: str | Path):
        self.yol = Path(yol)

    @contextmanager
    def kilitli(self) -> Iterator[None]:
        self.yol.parent.mkdir(parents=True, exist_ok=True)
        with open(self.yol.with_name(self.yol.name + ".lock"), "a") as kilit:
            fcntl.flock(kilit, fcntl.LOCK_EX)
            yield

    def oku(self) -> list[dict]:
        try:
            veri = json.loads(self.yol.read_text(encoding="utf-8"))
        except (OSError, ValueError, RecursionError):
            return []
        kayitlar = veri.get("kayitlar") if isinstance(veri, dict) else None
        return [k for k in kayitlar if _gecerli_bekleyen(k)] if isinstance(kayitlar, list) else []

    def _yaz(self, kayitlar: list[dict]) -> None:
        atomic_json_dump({"kayitlar": kayitlar}, str(self.yol))

    def ekle(self, yeniler: list[dict]) -> None:
        with self.kilitli():
            kayitlar = self.oku()
            for y in yeniler:
                anahtar = _bekleyen_anahtari(y)
                eski = next((k for k in kayitlar if _bekleyen_anahtari(k) == anahtar), None)
                if eski is None:
                    kayitlar.append(y)
                else:       # the newer alert covers the exam; its retries get a fresh budget
                    eski["turler"], eski["deneme"] = list(y["turler"]), y["deneme"]
            self._yaz(kayitlar)


def _gecerli_bekleyen(k: Any) -> bool:
    return (isinstance(k, dict) and all(isinstance(k.get(a), str) for a in ("email", "endpoint", "sinav_id",
                                                                            "icerik_surumu"))
            and isinstance(k.get("turler"), list) and k["turler"] and all(isinstance(t, str) for t in k["turler"])
            and isinstance(k.get("deneme"), int))


def _bekleyen_anahtari(k: dict) -> tuple[str, str, str, str]:
    return k["email"], k["endpoint"], k["sinav_id"], k["icerik_surumu"]


def _alicilar(depo: web_push.AbonelikDeposu) -> list[str]:
    return sorted(e for e in depo.hepsi() if is_full(e))


def _durum_yaz(kok: Path, durum: dict) -> dict:
    atomic_json_dump(durum, str(kok / DURUM))
    return durum


KOK_SINAVLAR_YOK = "sinavlar.json yok"
KOK_VAPID_YOK = "VAPID ayarlı değil"
CALISMAYAN_TUR = (KOK_SINAVLAR_YOK, KOK_VAPID_YOK)


def _olumcul(durum: dict, mesaj: str) -> None:
    """A round that could not do its job: listed first, and `main` exits 1 for systemd."""
    durum["_olumcul"].append(mesaj[:160])


def _yuk(sinav: dict, email: str, turler: tuple[str, ...], simdi: datetime) -> dict:
    baslik, govde = metin_kur(sinav, okur_turu(email), turler, simdi)
    return {"baslik": baslik, "govde": govde, "etiket": sinav["id"], "url": f"/sinavlar?sinav={sinav['id']}"}


def _sil(depo: web_push.AbonelikDeposu, endpoint: str, durum: dict) -> int:
    """Removing a dead device must not cost the person's other devices their ledger line: a store
    that cannot be written is reported as fatal, and the device's outcome stands."""
    try:
        return depo.endpoint_sil(endpoint)
    except OSError as exc:
        _olumcul(durum, f"abonelik silinemedi: {exc}")
        return 0


def _cihaza_gonder(abonelik: dict, yuk: dict, vapid: Any, gonderici: Callable[..., web_push.GonderimSonucu],
                   depo: web_push.AbonelikDeposu, durum: dict) -> str:
    """One device: "ok", "olu" (removed), "gecersiz" (removed, never dialled) or "hata". A sender
    that raises instead of returning is a failed device, not a failed round."""
    if not web_push.kayitli_abonelik_gecerli(abonelik):
        durum["gecersiz_silinen"] += _sil(depo, abonelik["endpoint"], durum)
        return "gecersiz"
    try:
        sonuc = gonderici(abonelik, yuk, vapid)
    except Exception as exc:  # noqa: BLE001 - one device must not stop the others
        durum["hatalar"].append(f"gönderim: {type(exc).__name__}: {exc}"[:160])
        return "hata"
    if sonuc.durum == "ok":
        return "ok"
    if sonuc.durum == "olu":
        durum["olu_silinen"] += _sil(depo, abonelik["endpoint"], durum)
        return "olu"
    durum["hatalar"].append(f"{sonuc.kod}: {sonuc.mesaj}"[:160])
    return "hata"


def _bildirim_gonder(b: Bildirim, depo: web_push.AbonelikDeposu, defter: BildirimDefteri, kuyruk: BekleyenKuyruk,
                     vapid: Any, gonderici: Callable[..., web_push.GonderimSonucu], simdi: datetime,
                     durum: dict) -> None:
    yuk = _yuk(b.sinav, b.email, b.turler, simdi)
    sonuclar = [(c["abonelik"]["endpoint"], _cihaza_gonder(c["abonelik"], yuk, vapid, gonderici, depo, durum))
                for c in depo.kisinin(b.email)]
    if not any(s == "ok" for _, s in sonuclar):
        return      # nothing reached the person: no ledger, the whole alert is planned again next round
    defter.yaz(b.email, b.sinav, b.turler, simdi)
    durum["gonderilen"] += 1
    hatali = [e for e, s in sonuclar if s == "hata"]
    if hatali:
        # The ledger is per person (spec): without this the failed device would never get it.
        try:
            kuyruk.ekle([{"email": b.email, "endpoint": e, "sinav_id": b.sinav["id"], "turler": list(b.turler),
                          "icerik_surumu": b.sinav["icerik_surumu"], "deneme": 1} for e in hatali])
        except OSError as exc:
            _olumcul(durum, f"bekleyen kuyruk yazılamadı: {exc}")


def _bekleyen_dene(k: dict, sinavlar: dict[str, dict], alicilar: set[str], planli: set[tuple[str, str]],
                   depo: web_push.AbonelikDeposu, vapid: Any, gonderici: Callable[..., web_push.GonderimSonucu],
                   simdi: datetime, durum: dict) -> bool:
    """One pending record; True keeps it for the next round."""
    s = sinavlar.get(k["sinav_id"])
    if s is None or s.get("icerik_surumu") != k["icerik_surumu"] or k["email"] not in alicilar:
        return False        # the exam is gone or changed (the new version reaches everyone), or the person
    if (k["email"], k["sinav_id"]) in planli:
        return False        # a newer alert for this exam goes to all the person's devices this round;
        #                     if it misses this device, it enters the queue again
    if _sessiz(simdi):
        return True         # quiet hours: wait, the attempt is not counted
    if not vadesi_gelen_turler(s, simdi):
        return False        # the exam has begun, or its week is over
    cihaz = next((c for c in depo.kisinin(k["email"]) if c["abonelik"]["endpoint"] == k["endpoint"]), None)
    if cihaz is None:
        return False        # the device left the store (removed, dead or moved to someone else)
    sonuc = _cihaza_gonder(cihaz["abonelik"], _yuk(s, k["email"], tuple(k["turler"]), simdi), vapid, gonderici,
                           depo, durum)
    if sonuc == "ok":
        durum["bekleyen_gonderilen"] += 1
        return False
    if sonuc != "hata":
        return False
    k["deneme"] += 1
    if k["deneme"] >= BEKLEYEN_DENEME_SINIRI:
        durum["hatalar"].append(f"{k['sinav_id']}: bir cihaza {BEKLEYEN_DENEME_SINIRI} denemede gönderilemedi")
        return False
    return True


def _bekleyenler(kuyruk: BekleyenKuyruk, belge: dict, alicilar: list[str], planli: set[tuple[str, str]],
                 depo: web_push.AbonelikDeposu, vapid: Any, gonderici: Callable[..., web_push.GonderimSonucu],
                 simdi: datetime, durum: dict) -> None:
    sinavlar = {s["id"]: s for s in belge["sinavlar"] if isinstance(s, dict) and isinstance(s.get("id"), str)}
    with kuyruk.kilitli():
        kayitlar = kuyruk.oku()
        if not kayitlar:
            return
        kalan = []
        for k in kayitlar:
            try:
                tut = _bekleyen_dene(k, sinavlar, set(alicilar), planli, depo, vapid, gonderici, simdi, durum)
            except Exception as exc:  # noqa: BLE001 - one bad record must not stop the others
                # Kept and counted as an attempt: an unexpected error is not a reason to lose the alert.
                durum["hatalar"].append(f"bekleyen {k.get('sinav_id', '?')}: {exc}"[:160])
                k["deneme"] += 1
                tut = k["deneme"] < BEKLEYEN_DENEME_SINIRI
            if tut:
                kalan.append(k)
        try:
            kuyruk._yaz(kalan)
        except OSError as exc:
            _olumcul(durum, f"bekleyen kuyruk yazılamadı: {exc}")


YEDEK_HABER_SURESI = timedelta(hours=24)


def _depo_sagligi(depo: web_push.AbonelikDeposu, simdi: datetime, durum: dict) -> None:
    """An unreadable store means "no subscribers" to this round; the dashboard moves such a file
    aside on its next write and starts afresh. Either way devices were lost silently: say so in the
    status file (health.json `sinav_uyari` reads it). Browsers re-post their subscription when the
    dashboard is opened, so the list fills again by itself."""
    if depo.son_okuma_bozuk:
        durum["hatalar"].append("abonelik deposu okunamadı (bozuk); cihazlar pano açılınca yeniden kaydolur")
    yakin = [z for z in depo.bozuk_yedekler() if timedelta(0) <= simdi - z <= YEDEK_HABER_SURESI]
    if yakin:
        durum["hatalar"].append(f"abonelik deposu bozuk bulundu, {yakin[-1]:%d.%m %H:%M}'de kenara alındı; "
                                "cihazlar pano açılınca yeniden kaydolur")


def _tur(kok: Path, simdi: datetime, gonderici: Callable[..., web_push.GonderimSonucu] | None, durum: dict) -> None:
    if os.environ.get("TEDY_SINAV_UYARI", "0") != "1":
        durum["kapali"] = True
        return
    belge = sinav_tespiti.oku(kok)
    vapid = web_push.vapid_ayarlari()
    if belge is None or vapid is None:
        _olumcul(durum, KOK_SINAVLAR_YOK if belge is None else KOK_VAPID_YOK)
        return
    gonderici = gonderici or web_push.gonder
    depo = web_push.AbonelikDeposu(kok / web_push.ABONELIKLER)
    defter = BildirimDefteri(kok / DEFTER)
    kuyruk = BekleyenKuyruk(kok / BEKLEYEN)
    alicilar = _alicilar(depo)
    durum["abone_kisi"] = len(alicilar)
    _depo_sagligi(depo, simdi, durum)
    plan = planla(belge["sinavlar"], alicilar, defter.anahtarlar(), simdi, durum["hatalar"])
    _bekleyenler(kuyruk, belge, alicilar, {(b.email, b.sinav["id"]) for b in plan}, depo, vapid, gonderici,
                 simdi, durum)
    for b in plan:
        try:
            _bildirim_gonder(b, depo, defter, kuyruk, vapid, gonderici, simdi, durum)
        except Exception as exc:  # noqa: BLE001 - one failing notification must not stop the round
            durum["hatalar"].append(_hata_satiri(b.sinav, exc))
    durum["bekleyen"] = len(kuyruk.oku())


def _hatalari_kes(durum: dict) -> None:
    """Fatal errors first, then the rest; at most five distinct messages, `hata_sayisi` the total."""
    olumcul = durum.pop("_olumcul")
    tum = olumcul + durum["hatalar"]
    durum["hata_sayisi"] = len(tum)
    durum["hatalar"] = list(dict.fromkeys(tum))[:HATA_LISTESI_SINIRI]
    durum["olumcul"] = bool(olumcul)


def gonder_turu(kok: Path, simdi: datetime, gonderici: Callable[..., web_push.GonderimSonucu] | None = None) -> dict:
    kok = Path(kok)
    durum = {"son_tur": simdi.isoformat(timespec="seconds"), "kapali": False, "gonderilen": 0,
             "olu_silinen": 0, "gecersiz_silinen": 0, "bekleyen_gonderilen": 0, "bekleyen": 0, "hatalar": [],
             "abone_kisi": 0, "_olumcul": []}
    try:
        _tur(kok, simdi, gonderici, durum)
    except Exception as exc:  # noqa: BLE001 - the status file must still say what happened
        _olumcul(durum, f"tur: {type(exc).__name__}: {exc}")
    finally:
        _hatalari_kes(durum)
        try:
            _durum_yaz(kok, durum)
        except OSError as exc:
            durum["hatalar"] = (durum["hatalar"] + [f"durum yazılamadı: {exc}"[:160]])[:HATA_LISTESI_SINIRI]
            durum["hata_sayisi"] += 1
    return durum


def _tohum(kok: Path, emails: list[str], simdi: datetime) -> int:
    belge = sinav_tespiti.oku(Path(kok))
    if belge is None:
        return 0
    defter = BildirimDefteri(Path(kok) / DEFTER)
    eski = defter.anahtarlar()
    sayi = 0
    for s in belge["sinavlar"]:
        try:
            vadeli = vadesi_gelen_turler(s, simdi, sessiz_saat=False)
            sid, surum = s["id"], s["icerik_surumu"]
        except Exception:  # noqa: BLE001 - a malformed record is skipped, the rest is still seeded
            continue
        for email in emails:
            yeni = tuple(t for t in vadeli if (email, sid, t, surum) not in eski)
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
        # A round that could not do its job (no exams file, no VAPID, an unexpected error, a pending
        # queue it could not write) is a failure for systemd; flag-off ("kapali") and a device's
        # own error are not.
        olumcul = durum.get("olumcul") or any(h in CALISMAYAN_TUR for h in durum.get("hatalar", []))
        return 1 if olumcul else 0
    if komut == ["tohumla"]:
        print(f"tohumlanan uyarı: {tohumla(kok, datetime.now())}")
        return 0
    print("kullanım: python -m src.sinav_uyari gonder|tohumla", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
