"""MEB konu-soru dağılım senaryoları: tablo okuma ve sınav ↔ senaryo eşleştirme (spec 2026-10-19 §3).

Saf işlevler; ağ ve dosya yazımı yok. Tablo `scripts/odsgm_senaryo_tablolari.py`'nin ürettiği
src/sinav_senaryolari.json'dur."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from src.course_names import normalize_course
from src.sinav_tarihi import katla

TABLO = Path(__file__).with_name("sinav_senaryolari.json")
SURUM = 1
HARIC_TURLER = frozenset({"kisa_sinav", "konu_tarama"})
PENCERE = 400
CUMLE_SINIRI = 300
ESIK = 0.6
GOVDE_SINIRI = 3900

_DONEM_SINAV = re.compile(r"(?<![\d.])([12])\s*\.\s*([12])(?![\d.])")
_SINAV_NO = re.compile(r"\b([12])\s*\.?\s*(?:ortak\s+)?(?:yazili|sinav)")
_SOZCUK_NO = re.compile(r"\b(birinci|ikinci)\s+(?:ortak\s+)?(?:yazili|sinav)")
_DONEM = re.compile(r"\b([12])\s*\.?\s*donem")
_SIRA = {"birinci": 1, "ikinci": 2, "ucuncu": 3, "dorduncu": 4, "besinci": 5, "altinci": 6,
         "yedinci": 7, "sekizinci": 8, "dokuzuncu": 9, "onuncu": 10}
_LISTE = r"\d{1,2}\s*\.?(?:\s*(?:,|ve|veya|ile)\s*\d{1,2}\s*\.?)*"
_ONCE = re.compile(rf"(?<![\d.])({_LISTE})\s*senaryo")
_SONRA = re.compile(r"senaryo\w*\s+(\d{1,2}(?:\s*(?:,|ve|veya)\s*\d{1,2})*)(?![\d.])")
_SOZCUK = re.compile(r"\b(" + "|".join(_SIRA) + r")\s+senaryo")
_TARIH_IFADESI = re.compile(r"\b\d{1,2}\s+(ocak|subat|mart|nisan|mayis|haziran|temmuz|agustos|eylul|ekim|kasim|aralik)\b"
                            r"|\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b")
# Cümle sonu: rakam olmayan bir karakterden sonra gelen nokta/ünlem/soru + boşluk + büyük harf ya da
# rakam; ya da satır sonu. "4. Senaryo"daki nokta rakamdan sonra geldiği için bölmez.
_CUMLE_AYIR = re.compile(r"(?<=\D[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9])|\n+")
_DURAK = frozenset({"ile", "ve", "veya", "icin", "ilgili", "yonelik", "olan", "gibi", "bir", "bu", "da", "de"})
_KOD_ONEKI = re.compile(r"^[a-z]{1,5}(?:\.[a-z]{1,5})*\.\d{1,2}\.\d{1,2}(?:\.\d{1,2})?\.?\s*")


def tablo_oku(yol: Path | None = None) -> dict | None:
    try:
        veri = json.loads(Path(yol or TABLO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(veri, dict) or veri.get("surum") != SURUM or not isinstance(veri.get("dersler"), dict) \
            or not isinstance(veri.get("kaynak"), dict):
        return None
    return veri


def _gun(deger: Any) -> date | None:
    try:
        return date.fromisoformat(str(deger)[:10]) if deger else None
    except ValueError:
        return None


def _donem_ayi(ay: int) -> int | None:
    if ay >= 9 or ay == 1:
        return 1
    if 2 <= ay <= 6:
        return 2
    return None


def sutun_coz(kayit: dict, tablo: dict, bugun: date) -> tuple[str, int] | None:
    if kayit.get("tur") in HARIC_TURLER:
        return None
    ders = kayit.get("ders")
    if ders not in tablo["dersler"]:
        return None
    b = katla(kayit.get("baslik") or "")
    donem = no = None
    m = _DONEM_SINAV.search(b)
    if m:
        donem, no = int(m.group(1)), int(m.group(2))
    else:
        m = _SINAV_NO.search(b)
        if m:
            no = int(m.group(1))
        else:
            m = _SOZCUK_NO.search(b)
            if m:
                no = 1 if m.group(1) == "birinci" else 2
        d = _DONEM.search(b)
        if d:
            donem = int(d.group(1))
    if no is None:
        return None
    if donem is None:
        gun = _gun(kayit.get("tarih")) or _gun(kayit.get("hafta")) or bugun
        donem = _donem_ayi(gun.month)
    if donem != tablo["kaynak"]["donem"] or str(no) not in tablo["dersler"][ders]["sinavlar"]:
        return None
    return ders, no


def _sayilar(katli: str) -> list[int]:
    bulunan: list[int] = []
    for m in _ONCE.finditer(katli):
        bulunan += [int(x) for x in re.findall(r"\d{1,2}", m.group(1))]
    for m in _SONRA.finditer(katli):
        bulunan += [int(x) for x in re.findall(r"\d{1,2}", m.group(1))]
    for m in _SOZCUK.finditer(katli):
        bulunan.append(_SIRA[m.group(1)])
    return [s for s in dict.fromkeys(bulunan) if 1 <= s <= 10]


def _cumleler(metin: str) -> list[str]:
    return [c.strip() for c in _CUMLE_AYIR.split(metin or "") if c and c.strip()]


def senaryo_cumlesi(metin: str, alinti: str, tek: bool) -> tuple[list[int], str | None]:
    cumleler = _cumleler(metin)
    if tek:
        aday = cumleler
    else:
        ilk = katla((_cumleler(alinti) or [""])[0])[:40]
        bas = next((i for i, c in enumerate(cumleler) if ilk and ilk in katla(c)), None)
        if bas is None:
            aday = _cumleler(alinti)
        else:
            aday, uzunluk = [], 0
            for i, c in enumerate(cumleler[bas:]):
                if i > 0 and (_TARIH_IFADESI.search(katla(c)) or uzunluk >= PENCERE):
                    break
                aday.append(c)
                uzunluk += len(c)
    sayilar: list[int] = []
    cumle = None
    for c in aday:
        bulunan = _sayilar(katla(c))
        if bulunan:
            sayilar += [s for s in bulunan if s not in sayilar]
            cumle = cumle or c[:CUMLE_SINIRI]
    return sorted(sayilar), cumle


def _kokler(metin: str) -> set[str]:
    return {s[:5] for s in re.findall(r"[a-z0-9]+", katla(metin)) if len(s) >= 3 and s not in _DURAK}


def _puan(a: str, b: str) -> float:
    x, y = _KOD_ONEKI.sub("", katla(a)), _KOD_ONEKI.sub("", katla(b))
    if len(min(x, y, key=len)) >= 10 and (x in y or y in x):
        return 1.0
    ka, kb = _kokler(x), _kokler(y)
    return 2 * len(ka & kb) / (len(ka) + len(kb)) if ka and kb else 0.0


def konu_eslestir(konu: str, ciktilar: list[dict]) -> list[str]:
    k = katla(konu)
    kodlar = [c["kod"] for c in ciktilar
              if re.search(rf"(?<![\w.]){re.escape(katla(c['kod']))}(?!\d)", k)]
    if kodlar:
        return kodlar
    en, puan = None, 0.0
    for c in ciktilar:
        p = _puan(konu, c["metin"])
        if p > puan:
            en, puan = [c["kod"]], p
    if en and puan >= ESIK:
        return en
    gruplar: dict[str, list[str]] = {}
    for c in ciktilar:
        if c.get("konu"):
            gruplar.setdefault(c["konu"], []).append(c["kod"])
    en, puan = None, 0.0
    for ad, kodlar in gruplar.items():
        p = _puan(konu, ad)
        if p > puan:
            en, puan = kodlar, p
    return list(en) if en and puan >= ESIK else []


def senaryo_blogu(kayit: dict, metinler: list[tuple[str, str, bool]], tablo: dict, bugun: date) -> dict | None:
    sutun = sutun_coz(kayit, tablo, bugun)
    if sutun is None:
        return None
    ders, no = sutun
    dt = tablo["dersler"][ders]
    sinav = dt["sinavlar"][str(no)]
    anilan: list[int] = []
    cumle = None
    for metin, alinti, tek in metinler:
        sayilar, c = senaryo_cumlesi(metin, alinti, tek)
        anilan += [s for s in sayilar if s not in anilan]
        cumle = cumle or c
    anilan.sort()
    eslesme = {konu: konu_eslestir(konu, dt["ciktilar"]) for konu in kayit.get("konular") or []}
    eslesen = {konu: set(kodlar) for konu, kodlar in eslesme.items() if kodlar}
    blok = {"durum": None, "ders": ders, "sinav_no": no, "donem": tablo["kaynak"]["donem"], "anilan": anilan,
            "cumle": cumle, "senaryo": None, "toplam": None, "dagilim": [],
            "eslesen_konu_sayisi": len(eslesen),
            "eslesmeyen_konular": [k for k, kodlar in eslesme.items() if not kodlar],
            "senaryo_disi_konular": [], "adaylar": [], "senaryo_sayisi": 0,
            "kaynak": tablo["kaynak"]["sayfa"], "meb_guncelleme": tablo["kaynak"]["meb_guncelleme"]}
    if sinav["tur"] == "ulke_geneli":
        blok.update(durum="ulke_geneli", **{"not": sinav["not"]})
        return blok
    senaryolar = sinav["senaryolar"]
    blok["senaryo_sayisi"] = len(senaryolar)
    if anilan:
        gecerli = [n for n in anilan if str(n) in senaryolar]
        if not gecerli:
            blok["durum"] = "senaryo_yok"
            return blok
        n = gecerli[0]
        dagilim = senaryolar[str(n)]
        duyuruda = set().union(*eslesen.values()) if eslesen else set()
        blok.update(senaryo=n, toplam=sum(dagilim.values()),
                    dagilim=[{"kod": c["kod"], "metin": c["metin"], "soru": dagilim[c["kod"]],
                              "duyuruda": c["kod"] in duyuruda} for c in dt["ciktilar"] if c["kod"] in dagilim])
        blok["senaryo_disi_konular"] = [k for k, kodlar in eslesen.items() if not kodlar & set(dagilim)]
        blok["durum"] = "kismen" if blok["senaryo_disi_konular"] else "dogrulandi"
        return blok
    if eslesen:
        blok["adaylar"] = sorted(int(n) for n, d in senaryolar.items()
                                 if all(kodlar & set(d) for kodlar in eslesen.values()))
    blok["durum"] = "belirtilmedi"
    return blok


def _liste(sayilar: list[int]) -> str:
    parca = [f"{s}." for s in sayilar]
    return parca[0] if len(parca) == 1 else ", ".join(parca[:-1]) + " ve " + parca[-1]


def ozet(blok: dict) -> str:
    d = blok.get("durum")
    if d == "dogrulandi":
        return f"{blok['senaryo']}. senaryo doğrulandı · {blok['toplam']} soru"
    if d == "kismen":
        return f"{blok['senaryo']}. senaryo · {blok['toplam']} soru · bazı konular senaryoda yok"
    if d == "senaryo_yok":
        return f"duyuru {_liste(blok['anilan'])} senaryo diyor; tabloda yok (1–{blok['senaryo_sayisi']})"
    if d == "ulke_geneli":
        return "ülke genelinde ortak sınav; senaryo yok"
    adaylar = f"; uyumlu: {_liste(blok['adaylar'])}" if blok.get("adaylar") else ""
    return f"senaryo belirtilmedi ({blok['senaryo_sayisi']} senaryo{adaylar})"


def _dagilim_satirlari(dt: dict, dagilim: dict[str, int], duyuruda: set[str]) -> list[str]:
    satirlar = []
    for c in dt["ciktilar"]:
        if c["kod"] in dagilim:
            isaret = " (duyuruda)" if c["kod"] in duyuruda else ""
            satirlar.append(f"- {c['kod']} → {dagilim[c['kod']]} soru · {c['metin']}{isaret}")
    return satirlar


def arac_metni(tablo: dict, sinavlar: list[dict], args: dict) -> tuple[str, str]:
    ham = str(args.get("ders") or "").strip()
    ders = normalize_course(ham) or ham
    if ders == "Fen":
        ders = "Fen Bilimleri"
    if ders not in tablo["dersler"]:
        raise ValueError(f"'{ham}' MEB senaryo tablosunda yok; bu ders için senaryo verilemez. "
                         f"Tabloda olanlar: {', '.join(tablo['dersler'])}.")
    dt = tablo["dersler"][ders]
    no = args.get("sinav_no")
    senaryo = args.get("senaryo")
    sinav = next((e for e in sinavlar if isinstance(e, dict) and e.get("status") == "upcoming"
                  and e.get("course") == ders and isinstance(e.get("senaryo"), dict)
                  and (no is None or e["senaryo"].get("sinav_no") == no)), None)
    blok = sinav["senaryo"] if sinav else None
    no = no or (blok or {}).get("sinav_no")
    if no is None:
        raise ValueError("Hangi yazılı? sinav_no olarak 1 ya da 2 ver.")
    if str(no) not in dt["sinavlar"]:
        raise ValueError(f"{ders} için {no}. yazılı tabloda yok.")
    k = tablo["kaynak"]
    gun = k["meb_guncelleme"][:10].split("-")
    satirlar = [f"{ders} · 7. sınıf · {k['donem']}. Dönem {no}. Ortak Yazılı "
                f"(MEB konu-soru dağılım tablosu, güncelleme {gun[2]}.{gun[1]}.{gun[0]})"]
    if sinav:
        satirlar.append(f"Sınav: {sinav.get('title')} · {str(sinav.get('date') or 'tarih belirsiz')[:10]}")
        satirlar.append(f"Durum: {ozet(blok)}.")
        if blok.get("cumle"):
            satirlar.append(f"Duyurunun cümlesi: “{blok['cumle']}”")
        if blok.get("eslesmeyen_konular"):
            satirlar.append("MEB tablosunda karşılığı bulunamayan konu: " + "; ".join(blok["eslesmeyen_konular"]))
    sinav_tablosu = dt["sinavlar"][str(no)]
    if sinav_tablosu["tur"] == "ulke_geneli":
        satirlar.append("Bu sınav ülke genelinde ortak yapılır; MEB bu sınav için senaryo vermiyor.")
        return "\n".join(satirlar), f"MEB konu-soru dağılım tablosu · {ders} 7 · {no}. yazılı"
    senaryolar = sinav_tablosu["senaryolar"]
    duyuruda = {d["kod"] for d in (blok or {}).get("dagilim", []) if d.get("duyuruda")}
    secilen = senaryo or (blok or {}).get("senaryo")
    if secilen is not None:
        if str(secilen) not in senaryolar:
            raise ValueError(f"{ders} {no}. yazılıda {secilen}. senaryo yok (1–{len(senaryolar)}).")
        dagilim = senaryolar[str(secilen)]
        satirlar.append(f"Senaryo {secilen} · {sum(dagilim.values())} soru. Yazılacak dağılım:")
        satirlar += _dagilim_satirlari(dt, dagilim, duyuruda)
        satirlar.append(f"Toplam {sum(dagilim.values())} soru. Örnek sınavda soru sayısı ve dağılım bu listeye birebir uyar.")
    else:
        adaylar = (blok or {}).get("adaylar") or []
        if adaylar:
            satirlar.append(f"Duyurudaki konularla uyumlu senaryolar (tahmin): {_liste(adaylar)}")
        satirlar.append("Senaryolar:")
        for n in sorted(senaryolar, key=int):
            d = senaryolar[n]
            satirlar.append(f"- Senaryo {n} · {sum(d.values())} soru: "
                            + ", ".join(f"{kod}" + (f" ({s})" if s > 1 else "") for kod, s in d.items()))
        satirlar.append("Toplam soru sayıları yukarıda; hangi senaryonun kullanılacağı belli değil.")
    govde = "\n".join(satirlar)
    if len(govde) > GOVDE_SINIRI:
        govde = govde[:GOVDE_SINIRI - 1] + "…"
    return govde, f"MEB konu-soru dağılım tablosu · {ders} 7 · {no}. yazılı"
