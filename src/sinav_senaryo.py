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
_SINAV_NO = re.compile(r"\b([12])\s*\.\s*(?:ortak\s+)?(?:yazili|sinav)")
_SOZCUK_NO = re.compile(r"\b(birinci|ikinci)\s+(?:ortak\s+)?(?:yazili|sinav)")
_DONEM = re.compile(r"\b([12])\s*\.?\s*donem")
_SIRA = {"birinci": 1, "ikinci": 2, "ucuncu": 3, "dorduncu": 4, "besinci": 5, "altinci": 6,
         "yedinci": 7, "sekizinci": 8, "dokuzuncu": 9, "onuncu": 10}
# "senaryo"dan önce yalnız noktalı sıra sayısı sayılır ("4. senaryo", "3., 4. senaryolar"); "6 senaryo" bir
# adettir. Sonra yalnız bitişik "senaryo 3" biçimi sayılır ("senaryoda 3 soru" değil).
_LISTE = r"\d{1,2}\s*\.(?:\s*(?:,|\bve\b|\bveya\b|\bile\b)\s*\d{1,2}\s*\.)*"
_ONCE = re.compile(rf"(?<![\d.])({_LISTE})\s*senaryo")
_SONRA = re.compile(r"\bsenaryo\s*(\d{1,2})(?!\d|\.\d)")
_SOZCUK = re.compile(r"\b(" + "|".join(_SIRA) + r")\s+senaryo")
# Pencere sınırları (katlanmış metinde): başka bir tarih ifadesi ya da başka bir sınav numarası.
_AYLAR = "ocak|subat|mart|nisan|mayis|haziran|temmuz|agustos|eylul|ekim|kasim|aralik"
_SINIRLAR = (
    re.compile(rf"\b\d{{1,2}}\s+(?:{_AYLAR})\w*"),
    re.compile(r"(?<![\d.])\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?(?!\d)"),
    _DONEM_SINAV,
    _SINAV_NO,
)
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


def ogretim_yili_adi(gun: date) -> str:
    """Öğretim yılı Eylül'de başlar: Eylül–Aralık Y → "Y-(Y+1)", Ocak–Ağustos Y → "(Y-1)-Y"."""
    yil = gun.year if gun.month >= 9 else gun.year - 1
    return f"{yil}-{yil + 1}"


def donem_no(gun: date) -> int:
    """Eylül–Ocak 1. dönem, Şubat–Ağustos 2. dönem."""
    return 1 if gun.month >= 9 or gun.month == 1 else 2


def _baslik_coz(baslik: str) -> tuple[int | None, int | None]:
    """Bir başlıktan (dönem, sınav no); sınav no okunamıyorsa (None, None)."""
    b = katla(baslik or "")
    m = _DONEM_SINAV.search(b)
    if m:
        return int(m.group(1)), int(m.group(2))
    no = None
    m = _SINAV_NO.search(b)
    if m:
        no = int(m.group(1))
    else:
        m = _SOZCUK_NO.search(b)
        if m:
            no = 1 if m.group(1) == "birinci" else 2
    if no is None:
        return None, None
    d = _DONEM.search(b)
    return (int(d.group(1)) if d else None), no


def sutun_coz(kayit: dict, tablo: dict, bugun: date) -> tuple[str, int] | None:
    if kayit.get("tur") in HARIC_TURLER or kayit.get("sentetik"):
        return None
    ders = kayit.get("ders")
    if ders not in tablo["dersler"]:
        return None
    # Önce kaydın temiz başlığı, sonra takvim sınavının ham başlığı (temiz başlık "Ortak", "N. Yazılı" gibi
    # sözcükleri düşürebilir); numara okunan ilk başlık kazanır. Kaynak alıntılarından numara okunmaz.
    donem = no = None
    for baslik in (kayit.get("baslik"), (kayit.get("taban") or {}).get("rawTitle")):
        donem, no = _baslik_coz(baslik or "")
        if no is not None:
            break
    if no is None:
        return None
    k = tablo["kaynak"]
    gun = _gun(kayit.get("tarih")) or _gun(kayit.get("hafta")) or bugun
    # Tablo tek bir öğretim yılının tek bir dönemine aittir: başka yılın ya da dönemin sınavı bu sütunlara
    # bağlanmaz (kaçırmak güvenli yön). Başlık dönemi söylüyorsa ("1.1") tarihin dönemiyle de çelişmemeli.
    if ogretim_yili_adi(gun) != k["ogretim_yili"] or donem_no(gun) != k["donem"]:
        return None
    if donem is not None and donem != k["donem"]:
        return None
    if str(no) not in tablo["dersler"][ders]["sinavlar"]:
        return None
    return ders, no


def _sayilar(katli: str, bas: int = 0, son: int | None = None) -> list[tuple[int, int]]:
    """Katlanmış metinde anılan senaryo numaraları: (numara, bulunduğu konum), görünüş sırasıyla, tekrarsız."""
    son = len(katli) if son is None else son
    bulunan: list[tuple[int, int]] = []
    # Bir "senaryo" sözcüğü tek numara taşır: öndeki sıra sayısı ("4. senaryo") onu numaralamışsa sondaki sayı
    # ("4. senaryo 7 soru") soru adedi ya da kısım numarasıdır, ikinci bir senaryo değildir.
    numaralanan: set[int] = set()
    for m in _ONCE.finditer(katli, bas, son):
        bulunan += [(int(x), m.start()) for x in re.findall(r"\d{1,2}", m.group(1))]
        numaralanan.add(m.end() - len("senaryo"))
    for m in _SOZCUK.finditer(katli, bas, son):
        bulunan.append((_SIRA[m.group(1)], m.start()))
        numaralanan.add(m.end() - len("senaryo"))
    for m in _SONRA.finditer(katli, bas, son):
        if m.start() not in numaralanan:
            bulunan.append((int(m.group(1)), m.start()))
    sonuc: dict[int, int] = {}
    for sayi, konum in sorted(bulunan, key=lambda t: t[1]):
        if 1 <= sayi <= 10:
            sonuc.setdefault(sayi, konum)
    return list(sonuc.items())


def _cumleler(metin: str) -> list[str]:
    return [c.strip() for c in _CUMLE_AYIR.split(metin or "") if c and c.strip()]


def _katli_cumleler(metin: str) -> tuple[str, list[tuple[int, int, str]]]:
    """Metni cümlelere böler; katlanmış hâli (katla(metin) ile aynı) ve her cümlenin bu metindeki aralığı."""
    katli = ""
    parcalar: list[tuple[int, int, str]] = []
    for c in _cumleler(metin):
        k = katla(c)
        if not k:
            continue
        bas = len(katli) + 1 if katli else 0
        katli = f"{katli} {k}" if katli else k
        parcalar.append((bas, len(katli), c))
    return katli, parcalar


def _pencere(katli: str, alinti_katli: str, tek: bool) -> tuple[int, int] | None:
    """Alıntının başladığı yerden, alıntıdan sonraki ilk sınıra (tarih ya da başka sınav numarası) ya da
    alıntı sonu + PENCERE karaktere kadar. Alıntı bulunamazsa: tek bulguda bütün metin, değilse None."""
    bas = katli.find(alinti_katli) if alinti_katli else -1
    if bas < 0:
        return (0, len(katli)) if tek else None
    son = bas + len(alinti_katli)
    bitis = min(len(katli), son + PENCERE)
    for desen in _SINIRLAR:
        m = desen.search(katli, son, bitis)
        if m:
            bitis = min(bitis, m.start())
    return bas, bitis


def _senaryo_cumleleri(metin: str, alinti: str, tek: bool) -> dict[int, str]:
    """Pencerede anılan her senaryo numarası -> onu anan özgün cümle (≤ CUMLE_SINIRI), görünüş sırasıyla."""
    katli, parcalar = _katli_cumleler(metin)
    pencere = _pencere(katli, katla(alinti), tek)
    if pencere is None:
        katli, parcalar = _katli_cumleler(alinti)
        pencere = (0, len(katli))
    sonuc: dict[int, str] = {}
    for sayi, konum in _sayilar(katli, *pencere):
        cumle = next((c for bas, son, c in parcalar if bas <= konum < son), None)
        if cumle is not None:
            sonuc[sayi] = cumle[:CUMLE_SINIRI]
    return sonuc


def senaryo_cumlesi(metin: str, alinti: str, tek: bool) -> tuple[list[int], str | None]:
    bulunan = _senaryo_cumleleri(metin, alinti, tek)
    sayilar = sorted(bulunan)
    return sayilar, (bulunan[sayilar[0]] if sayilar else None)


def _kokler(metin: str) -> set[str]:
    return {s[:5] for s in re.findall(r"[a-z0-9]+", katla(metin)) if len(s) >= 3 and s not in _DURAK}


def _puan(a: str, b: str) -> float:
    x, y = _KOD_ONEKI.sub("", katla(a)), _KOD_ONEKI.sub("", katla(b))
    if len(min(x, y, key=len)) >= 10 and (x in y or y in x):
        return 1.0
    ka, kb = _kokler(x), _kokler(y)
    return 2 * len(ka & kb) / (len(ka) + len(kb)) if ka and kb else 0.0


def _kesin_eslesme(konu: str, ciktilar: list[dict]) -> list[str]:
    """Konu çıktı kodunu ya da bir/birkaç çıktının tam ifadesini anıyorsa o çıktılar; yoksa []."""
    k = katla(konu)
    kodlar = [c["kod"] for c in ciktilar
              if re.search(rf"(?<![\w.]){re.escape(katla(c['kod']))}(?!\d)", k)]
    if kodlar:
        return kodlar
    # Konu bir ya da birkaç çıktının tam ifadesini içeriyorsa duyuru o çıktıları birebir anıyordur: yalnız onlar
    # (konu grubuna genişletilmez).
    for c in ciktilar:
        metin = _KOD_ONEKI.sub("", katla(c["metin"]))
        if len(metin) >= 10 and metin in k:
            kodlar.append(c["kod"])
    return kodlar


def _puanlar(konu: str, ciktilar: list[dict]) -> tuple[list[tuple[str, float]], dict[str, list[str]], dict[str, float]]:
    puanlar = [(c["kod"], _puan(konu, c["metin"])) for c in ciktilar]
    gruplar: dict[str, list[str]] = {}
    for c in ciktilar:
        if c.get("konu"):
            gruplar.setdefault(c["konu"], []).append(c["kod"])
    return puanlar, gruplar, {ad: _puan(konu, ad) for ad in gruplar}


def konu_eslestir(konu: str, ciktilar: list[dict]) -> list[str]:
    """Duyurudaki konunun EN İYİ eşleşmesi ("duyuruda" etiketi bunu taşır). Senaryo kapsamı kararı için
    `konu_kapsami` kullanılır."""
    kodlar = _kesin_eslesme(konu, ciktilar)
    if kodlar:
        return kodlar
    # Eşit puanlı çıktıların hepsi; konu adı, en az eşiği ve en iyi çıktı puanını tutuyorsa çıktıdan önce gelir.
    puanlar, gruplar, konu_puanlari = _puanlar(konu, ciktilar)
    en_cikti = max((p for _, p in puanlar), default=0.0)
    en_konu = max(konu_puanlari.values(), default=0.0)
    if en_konu >= ESIK and en_konu >= en_cikti:
        return [kod for ad, p in konu_puanlari.items() if abs(p - en_konu) < 1e-9 for kod in gruplar[ad]]
    if en_cikti >= ESIK:
        return [kod for kod, p in puanlar if abs(p - en_cikti) < 1e-9]
    return []


def konu_kapsami(konu: str, ciktilar: list[dict]) -> list[str]:
    """Konunun kapsadığı bütün çıktılar: kesin eşleşme varsa o; yoksa eşiği (ESIK) geçen her çıktı ile her konu
    grubunun çıktılarının birleşimi, tablo sırasıyla. "Dolaşım ve solunum sistemi" iki gruba da eşiği geçer;
    yalnız en iyisine (Solunum) bakmak Dolaşım'ın senaryoda olduğunu görmezdi. Senaryo dışı kararı ve aday süzgeci
    bunu kullanır."""
    kodlar = _kesin_eslesme(konu, ciktilar)
    if kodlar:
        return kodlar
    puanlar, gruplar, konu_puanlari = _puanlar(konu, ciktilar)
    secilen = {kod for kod, p in puanlar if p >= ESIK}
    for ad, p in konu_puanlari.items():
        if p >= ESIK:
            secilen.update(gruplar[ad])
    return [c["kod"] for c in ciktilar if c["kod"] in secilen]


def senaryo_blogu(kayit: dict, metinler: list[tuple[str, str, bool]], tablo: dict, bugun: date) -> dict | None:
    sutun = sutun_coz(kayit, tablo, bugun)
    if sutun is None:
        return None
    ders, no = sutun
    dt = tablo["dersler"][ders]
    sinav = dt["sinavlar"][str(no)]
    cumleler: dict[int, str] = {}
    for metin, alinti, tek in metinler:
        for sayi, c in _senaryo_cumleleri(metin, alinti, tek).items():
            cumleler.setdefault(sayi, c)
    anilan = sorted(cumleler)
    eslesme = {konu: konu_eslestir(konu, dt["ciktilar"]) for konu in kayit.get("konular") or []}
    eslesen = {konu: set(kodlar) for konu, kodlar in eslesme.items() if kodlar}
    # "duyuruda" etiketi en iyi eşleşmede kalır (o senaryoda yoksa kapsamda); senaryo dışı kararı ve aday süzgeci
    # eşiği geçen her çıktı ve konu grubunun birleşimiyle verilir.
    kapsam = {konu: set(konu_kapsami(konu, dt["ciktilar"])) for konu in eslesen}
    blok = {"durum": None, "ders": ders, "sinav_no": no, "donem": tablo["kaynak"]["donem"], "anilan": anilan,
            "cumle": cumleler[anilan[0]] if anilan else None, "senaryo": None, "toplam": None, "dagilim": [],
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
        # Konunun en iyi eşleşmesi senaryoda yoksa onu senaryoya bağlayan kapsam satırları işaretlenir: konu
        # "senaryoda" sayılıyorsa kart onu taşıyan satırı da göstermeli.
        duyuruda: set[str] = set()
        for konu, kodlar in eslesen.items():
            duyuruda |= kodlar if kodlar & set(dagilim) else kapsam[konu]
        blok.update(senaryo=n, cumle=cumleler[n], toplam=sum(dagilim.values()),
                    dagilim=[{"kod": c["kod"], "metin": c["metin"], "soru": dagilim[c["kod"]],
                              "duyuruda": c["kod"] in duyuruda} for c in dt["ciktilar"] if c["kod"] in dagilim])
        blok["senaryo_disi_konular"] = [k for k, kodlar in kapsam.items() if not kodlar & set(dagilim)]
        blok["durum"] = "kismen" if blok["senaryo_disi_konular"] else "dogrulandi"
        return blok
    if eslesen:
        blok["adaylar"] = sorted(int(n) for n, d in senaryolar.items()
                                 if all(kodlar & set(d) for kodlar in kapsam.values()))
    blok["durum"] = "belirtilmedi"
    return blok


def _liste(sayilar: list[int]) -> str:
    parca = [f"{s}." for s in sayilar]
    return parca[0] if len(parca) == 1 else ", ".join(parca[:-1]) + " ve " + parca[-1]


def ozet(blok: dict) -> str:
    d = blok.get("durum")
    anilan = blok.get("anilan") or []
    if d in ("dogrulandi", "kismen") and len(anilan) > 1:
        kismen = " · bazı konular senaryoda yok" if d == "kismen" else ""
        return (f"duyuru {_liste(anilan)} senaryo diyor; {blok['senaryo']}. senaryo tabloda var · "
                f"{blok['toplam']} soru{kismen}")
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


def _ders_coz(ham: str, tablo: dict) -> str | None:
    """Model/kullanıcı ders adını tablo anahtarına çevirir: büyük-küçük harf ve aksan duyarsız; tek anlamlı ilk
    sözcük de yeter ("Fen" → Fen Bilimleri, "Sosyal" → Sosyal Bilgiler)."""
    for ad in (normalize_course(ham) or ham, ham):
        k = katla(ad)
        if not k:
            continue
        for anahtar in tablo["dersler"]:
            if katla(anahtar) == k:
                return anahtar
        ilk = [a for a in tablo["dersler"] if katla(a).split()[0] == k]
        if len(ilk) == 1:
            return ilk[0]
    return None


def arac_metni(tablo: dict, sinavlar: list[dict], args: dict, bugun: date | None = None) -> tuple[str, str]:
    ham = str(args.get("ders") or "").strip()
    ders = _ders_coz(ham, tablo)
    if ders is None:
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
    satirlar = [f"{ders} · {k['sinif']}. sınıf · {k['donem']}. Dönem {no}. Ortak Yazılı "
                f"(MEB konu-soru dağılım tablosu, güncelleme {gun[2]}.{gun[1]}.{gun[0]})",
                f"Bu tablo {k['ogretim_yili']} {k['donem']}. dönem ortak yazılıları içindir."]
    if bugun is not None and donem_no(bugun) != k["donem"]:
        satirlar.append(f"Şu an {donem_no(bugun)}. dönemdeyiz; bu tablo yalnız {k['donem']}. dönem ortak "
                        f"yazılılarını kapsar, bugünkü dönemin sınavları için dağılım vermez.")
    if sinav:
        satirlar.append(f"Sınav: {sinav.get('title')} · {str(sinav.get('date') or 'tarih belirsiz')[:10]}")
        satirlar.append(f"Durum: {ozet(blok)}.")
        if len(blok.get("anilan") or []) > 1:
            satirlar.append(f"Duyuru birden çok senaryo anıyor ({_liste(blok['anilan'])}); örnek sınav yazmadan "
                            f"önce hangisiyle hazırlanacağını sor.")
        if blok.get("cumle"):
            satirlar.append(f"Duyurunun cümlesi: “{blok['cumle']}”")
        if blok.get("eslesmeyen_konular"):
            satirlar.append("MEB tablosunda karşılığı bulunamayan konu: " + "; ".join(blok["eslesmeyen_konular"]))
    sinav_tablosu = dt["sinavlar"][str(no)]
    if sinav_tablosu["tur"] == "ulke_geneli":
        satirlar.append("Bu sınav ülke genelinde ortak yapılır; MEB bu sınav için senaryo vermiyor.")
        satirlar.append("Soru sayısı ya da dağılımı yok, uydurma. Örnek sınav istenirse duyurudaki konulardan "
                        "hazırla (duyuru konu vermiyorsa dersin güncel ünitesinden) ve bunun bir MEB senaryosu "
                        "olmadığını okura açıkça söyle.")
        return "\n".join(satirlar), f"MEB konu-soru dağılım tablosu · {ders} {k['sinif']} · {no}. yazılı"
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
        satirlar.append("Senaryo seçilince sinav_senaryosu'nu senaryo=N ile yeniden çağır; kontrol listesi ve "
                        "çıktı adları o çağrıda gelir.")
    govde = "\n".join(satirlar)
    if len(govde) > GOVDE_SINIRI:
        govde = govde[:GOVDE_SINIRI - 1] + "…"
    return govde, f"MEB konu-soru dağılım tablosu · {ders} {k['sinif']} · {no}. yazılı"
