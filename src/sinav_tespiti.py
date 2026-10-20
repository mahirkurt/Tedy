"""Sınav tespiti (spec §4, §5 "Birleştirme"): takvim + not tablosu tabanı ile
serbest metin bulgularını tek listede birleştirir ve output/sinavlar.json'u
yazar. Kayıt kimliği: takvimde varsa takvimin kendi kimliği (modüller bağlı,
değişmez), yoksa ders+tür+tarih özeti."""
from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any

from src import sinav_senaryo
from src.json_utils import atomic_json_dump
from src.sinav_cikarimi import Bulgu
from src.sinav_tarihi import katla, kati_gun, kati_tarih_saat, yerel_saat

logger = logging.getLogger(__name__)

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
# Kısa kökler (<= 4 harf) ve "ortak" tam sözcük olmalı — ardından harf gelemez, rakam gelebilir ("KTT2",
# "GİS2"; "Ortaklık" ortak sınav değildir); uzun kökler Türkçe ek alabilir ("denemesi", "yazılısı").
_TUR_KURALLARI = (
    ("ortak_sinav", ("ortak",)),
    ("konu_tarama", ("ktt", "konu tarama")),
    ("deneme", ("deneme", "gis", "izleme", "hazirbulunusluk", "kazanim degerlendirme")),
    ("yazili", ("yazili",)),
    ("kisa_sinav", ("quiz", "kisa sinav")),
)


_TAM_SOZCUK = frozenset({"ortak"})


def _sozcuk_var(katli: str, anahtar: str) -> bool:
    son = r"(?![a-z])" if len(anahtar) <= 4 or anahtar in _TAM_SOZCUK else r""
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
    sentetik = not e.get("date")
    # _sinav_listesi already writes local time; an offset or "Z" kept anyway is converted, not dropped.
    ham = yerel_saat(e.get("date"))
    # Bozuk tarih (katı biçim dışı): tarihsiz takvim sınavı — sentetik değil, takvim kaynağı ve kimliği var.
    an = kati_tarih_saat(ham)
    tarih = an.date().isoformat() if an else None
    saat = an.strftime("%H:%M") if an and "T" in ham and not e.get("allDay") else None
    kaynak = ({"tur": "not_tablosu", "konum": {"id": e.get("id")}, "alinti": str(e.get("rawTitle") or "")[:300]}
              if sentetik else
              {"tur": "takvim", "konum": {"id": e.get("id")}, "alinti": str(e.get("rawTitle") or "")[:300]})
    # The kind reads the raw title: the cleaned one drops words ("Ortak", "MEB Ülke Geneli").
    return {"id": e.get("id"), "ders": e.get("course") or "Genel",
            "tur": takvim_turu(e.get("rawTitle") or e.get("title") or ""),
            "baslik": e.get("title") or e.get("rawTitle") or "Sınav", "tarih": tarih,
            "saat": saat, "hafta": None, "konular": [], "kaynaklar": [kaynak], "sentetik": sentetik,
            "taban": e, "son_yayin": None}


def _bulgudan(b: Bulgu, kimlik: str) -> dict:
    return {"id": kimlik, "ders": b.ders, "tur": b.tur, "baslik": b.baslik,
            "tarih": b.tarih.isoformat() if b.tarih else None, "saat": b.saat,
            "hafta": b.hafta.isoformat() if b.hafta and not b.tarih else None,
            "konular": [], "kaynaklar": [], "sentetik": False, "taban": None, "son_yayin": None}


def _ekle(kayit: dict, b: Bulgu) -> None:
    # A text record takes the first finding's kind that says something ("diger" says nothing);
    # a takvim or grade-table base keeps its own kind and title.
    if kayit["taban"] is None and kayit["tur"] == "diger" and b.tur != "diger":
        kayit["tur"], kayit["baslik"] = b.tur, b.baslik
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


def _metin_konumlari(k: dict) -> set[str]:
    """The portal positions of a record's text sources (not takvim / grade table)."""
    sonuc = set()
    for x in k.get("kaynaklar") or []:
        if isinstance(x, dict) and x.get("tur") not in ("takvim", "not_tablosu") and isinstance(x.get("konum"), dict):
            sonuc.add(json.dumps(x["konum"], sort_keys=True))
    return sonuc


def _surum(k: dict) -> str:
    konular = sorted({katla(x) for x in k["konular"]})
    govde = f"{k['tarih']}|{k['saat']}|{k['hafta']}|" + "|".join(konular)
    return hashlib.sha256(govde.encode("utf-8")).hexdigest()[:12]


def birlestir(taban: list[dict], bulgular: list[Bulgu], onceki: dict | None, simdi: datetime,
              senaryolar: dict | None = None, senaryo_hatalari: list[str] | None = None) -> list[dict]:
    """`senaryo_hatalari` verilirse, MEB senaryosu eşleştirilemeyen her kayıt için bir not eklenir."""
    kayitlar = []
    # Each record's findings, for the MEB scenario sentence (spec 2026-10-19 §3.5): the full candidate
    # text is in hand only here. A text that yielded a single finding is searched whole.
    kayit_bulgulari: dict[int, list[Bulgu]] = {}
    aday_sayisi = Counter(id(b.aday) for b in bulgular)
    gorulen: set = set()
    for e in taban:
        if not isinstance(e, dict) or not e.get("id") or e["id"] in gorulen:
            continue   # a repeated id (duplicate grade rows) would break keys, ?sinav= and ledgers
        gorulen.add(e["id"])
        kayitlar.append(_tabandan(e))
    tarihliler = [b for b in bulgular if b.tarih]
    tarihsizler = [b for b in bulgular if not b.tarih]

    for b in tarihliler:
        gun = b.tarih.isoformat()
        eslesen = next((k for k in kayitlar if not k["sentetik"] and k["tarih"] == gun
                        and (katla(k["ders"]) == katla(b.ders) or (b.ders == "Genel" and k["taban"]))), None)
        if eslesen is None and b.tur in ORTAK_TURLER:
            # A shared exam (GİS, a common written) is often announced in one course's tab: its
            # takvim record carries another course name. Same day is enough when it is unambiguous.
            # Only when the day is unambiguous: one takvim record of a shared kind, else the day's only one.
            gunun = [k for k in kayitlar if k["taban"] and not k["sentetik"] and k["tarih"] == gun]
            eslesen = _tek([k for k in gunun if k["tur"] in ORTAK_TURLER]) or _tek(gunun)
        if eslesen is None:
            eslesen = _bulgudan(b, _md5(f"{b.ders}|{gun}"))
            kayitlar.append(eslesen)
        _ekle(eslesen, b)
        kayit_bulgulari.setdefault(id(eslesen), []).append(b)

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
            ek = f"hafta:{b.hafta.isoformat()}" if b.hafta else b.aday.metin_anahtari[:12]
            kimlik = _md5(f"{b.ders}|{ek}")
            hedef = next((k for k in kayitlar if k["id"] == kimlik), None)
            if hedef is None:
                hedef = _bulgudan(b, kimlik)
                kayitlar.append(hedef)
        _ekle(hedef, b)
        kayit_bulgulari.setdefault(id(hedef), []).append(b)

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
    # A text exam whose date changed gets a new id. If the previous file has a record of the same
    # course that is no longer produced and was found at the same portal position, it is the same
    # exam: its first sighting carries over and it reads as changed, not new. (Same course, since
    # an announcement's position is a list index that a newer post shifts.)
    uretilen = {k["id"] for k in kalan}
    yetim = [o for i, o in eski.items() if i not in uretilen and _metin_konumlari(o)]
    for k in kalan:
        k["konular"] = k["konular"][:KONU_SINIRI]
        k["kaynaklar"] = k["kaynaklar"][:KAYNAK_SINIRI]
        k["icerik_surumu"] = _surum(k)
        if senaryolar is not None:
            metinler = [(b.aday.metin, b.alinti, aday_sayisi[id(b.aday)] == 1)
                        for b in kayit_bulgulari.get(id(k), [])]
            # The scenario block is optional enrichment: one record's failure must neither drop the other
            # records' blocks nor stop the whole detection round (a thrown exception would skip the file write
            # and the new-exam alert). No block for that record, a note in the summary.
            try:
                blok = sinav_senaryo.senaryo_blogu(k, metinler, senaryolar, bugun)
            except Exception as exc:  # noqa: BLE001 — see above
                logger.error("senaryo eşleştirilemedi (%s): %s", k.get("id"), type(exc).__name__)
                blok = None
                if senaryo_hatalari is not None:
                    senaryo_hatalari.append(f"senaryo eşleştirilemedi: {k['ders']} {k['baslik']}")
            if blok is not None:
                k["senaryo"] = blok   # not part of icerik_surumu: no new alert (spec §3.5)
        o = eski.get(k["id"])
        ata = None if o is not None or k["taban"] else next(
            (y for y in yetim if katla(str(y.get("ders") or "")) == katla(k["ders"])
             and _metin_konumlari(y) & _metin_konumlari(k)), None)
        if o is not None:
            k["ilk_tespit"] = o.get("ilk_tespit")
            k["degisti"] = an if o.get("icerik_surumu") != k["icerik_surumu"] else o.get("degisti")
        elif ata is not None:
            yetim.remove(ata)
            k["ilk_tespit"], k["degisti"] = ata.get("ilk_tespit"), an
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


def korunan_konumlar(onceki: dict | None, bugun: date) -> set[str]:
    """Portal positions (json.dumps(konum, sort_keys=True)) of the previous file's exams still
    ahead — dated today or later, or a week not yet over. A candidate there is read even past the
    age limit for new model calls: an early post the teacher edited must not lose its exam (A14)."""
    sonuc: set[str] = set()
    for k in (onceki or {}).get("sinavlar") or []:
        if not isinstance(k, dict):
            continue
        tarih, hafta = kati_gun(k.get("tarih")), kati_gun(k.get("hafta"))
        if not ((tarih and tarih >= bugun) or (hafta and hafta + timedelta(days=6) >= bugun)):
            continue
        for x in k.get("kaynaklar") or []:
            if isinstance(x, dict) and isinstance(x.get("konum"), dict):
                sonuc.add(json.dumps(x["konum"], sort_keys=True))
    return sonuc


def tespit_et(kok: Path, veri: dict, taban: list[dict], simdi: datetime, bitis: float,
              okuyucu: Any = None) -> dict:
    from src.sinav_cikarimi import ClaudeSinavOkuyucu, SinavCikarici
    from src.sinav_kaynaklari import adaylar, kaynak_verisi

    kok = Path(kok)
    ekler, ilk_gorulme = kaynak_verisi(kok)
    liste = adaylar(veri, simdi.date(), ek_metinleri=ekler, odev_ilk_gorulme=ilk_gorulme)
    onceki = oku(kok)
    sonuc = SinavCikarici(kok, okuyucu or ClaudeSinavOkuyucu()).cikar(
        liste, simdi.date(), bitis, korunan_konumlar=korunan_konumlar(onceki, simdi.date()))
    if onceki is None and (kok / SINAVLAR).exists():
        # A file that is there but unreadable (torn, an older SURUM) is not a first
        # install: None would stamp every record "already there" and swallow its alert.
        onceki = {"surum": SURUM, "sinavlar": []}
    tablo = sinav_senaryo.tablo_oku()
    senaryo_hatalari: list[str] = []
    kayitlar = birlestir(taban, sonuc.bulgular, onceki, simdi, senaryolar=tablo, senaryo_hatalari=senaryo_hatalari)
    hatalar = ozet_hatalari(tablo_okundu=tablo is not None, senaryo_hatalari=senaryo_hatalari,
                            cikarim_hatalari=list(sonuc.hatalar))
    return {"uretildi": simdi.isoformat(timespec="seconds"), "surum": SURUM, "sinavlar": kayitlar,
            "ozet": {"aday": sonuc.aday, "incelenen": sonuc.incelenen, "incelenmedi": sonuc.incelenmedi,
                     "butce_usd": sonuc.butce_usd, "hatalar": hatalar}}


def ozet_hatalari(*, tablo_okundu: bool, senaryo_hatalari: list[str], cikarim_hatalari: list[str]) -> list[str]:
    """En çok 5 satır. Senaryo notları çıkarım ve bütçe hatalarının arkasında ve tek satırdadır: tablo yapısı
    değişince her kayıt patlar ve beş not asıl hataları özetten iterdi."""
    senaryo = senaryo_hatalari[:1]
    if len(senaryo_hatalari) > 1:
        senaryo = [f"{senaryo_hatalari[0]} (+{len(senaryo_hatalari) - 1} kayıt daha)"]
    hatalar = (["senaryo tablosu okunamadı"] if not tablo_okundu else []) + cikarim_hatalari
    return (hatalar[:5 - len(senaryo)] + senaryo)[:5]


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
        s = k.get("senaryo")
        if isinstance(s, dict):
            satirlar.append(f"  Senaryo: {s.get('durum')} · {s.get('ders')} {s.get('sinav_no')}. yazılı"
                            + (f" · {s['senaryo']}. senaryo · {s['toplam']} soru" if s.get("senaryo") else "")
                            + (f" · uyumlu {s['adaylar']}" if s.get("adaylar") else ""))
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
    import fcntl
    import sys
    import time

    from src.env_loader import load_env
    load_env()
    p = argparse.ArgumentParser(description="Sınav tespiti: sinavlar.json üretir")
    p.add_argument("--kuru", action="store_true",
                   help="bulunanları sinavlar.json'a yazmadan (model önbelleği ve bütçe defteri yine yazılır) yazdır")
    p.add_argument("--sure", type=float, default=300.0, help="model çağrıları için saniye")
    a = p.parse_args(argv)
    # The sync runs this step under output/.sync.lock and writes the same model cache and budget
    # ledger: by hand it waits for nobody — if a sync holds the lock, it says so and stops.
    kilit_yolu = PROJE_KOKU / "output" / ".sync.lock"
    kilit_yolu.parent.mkdir(parents=True, exist_ok=True)
    with open(kilit_yolu, "a") as kilit:
        try:
            fcntl.flock(kilit, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            print("senkron çalışıyor, sonra deneyin", file=sys.stderr)
            return 2
        veri = json.loads((PROJE_KOKU / "output/scraped_data.json").read_text(encoding="utf-8"))
        belge = tespit_et(PROJE_KOKU, veri, _taban(veri), datetime.now(), time.monotonic() + a.sure)
        print(kuru_rapor(belge))
        if not a.kuru:
            yaz(PROJE_KOKU, belge)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
