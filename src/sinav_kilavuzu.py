"""Sınav Hazırlığı kılavuz modeli (spec 2026-10-25 §2.4, §3, §4, §7; plan Görev 6–7).

Saf işlevler: girdiler `Girdiler` ile gelir (API toplar), ağ ve yazım yok — yalnız `harita_oku` dosya okur.
Senaryo tablosu `sinav_senaryo.tablo_oku()`, kitap haritaları `src/kitap_haritalari/<anahtar>.json`
(scripts/meb_kitap_haritasi.py üretir). Kanun K8: senaryo duyurulmadıysa hiçbir alan tek senaryoyu "bu" diye
taşımaz. Kanun K1: kitap başlıkları yalnız haritadan; haritada karşılığı olmayan çıktı "bulunamadi" (yok değil)."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from src.sinav_senaryo import DERS_ANAHTARLARI, _gun, donem_no, ogretim_yili_adi

SURUM = 1
HARITA_DIZINI = Path(__file__).with_name("kitap_haritalari")
ANAHTAR_DERSLERI = {anahtar: ders for ders, anahtar in DERS_ANAHTARLARI.items()}
KESIN_DURUMLAR = ("dogrulandi", "kismen")
KISA_AD_SOZCUK = 6
_UNITE_KODU = re.compile(r"^(?:[A-ZÇĞİÖŞÜ]+\.)+7\.(\d+)\.|^E7\.(\d+)\.")


class KilavuzHatasi(ValueError):
    """`kod`: bilinmeyen_ders | bilinmeyen_sinav | bilinmeyen_senaryo | tablo_yok | tablo_eski (API durum koduna çevirir)."""

    def __init__(self, kod: str):
        super().__init__(kod)
        self.kod = kod


@dataclass(frozen=True)
class Girdiler:
    tablo: dict | None
    haritalar: dict[str, dict]
    sinavlar: list[dict]                    # /api/exams "exams" kayıtları (senaryo bloğu olanlar kullanılır)
    bugun: date
    kitap_denetimi: dict = field(default_factory=dict)   # output/kitap_denetimi.json
    haftalar: dict = field(default_factory=dict)         # ders_icerikleri_haftalar (temizlenmiş)
    odevler: list = field(default_factory=list)          # _combined_homework_rows
    moduller: list = field(default_factory=list)         # module_store.latest_active
    isaretler: dict = field(default_factory=dict)        # {ders anahtarı: {çıktı kodu: "hazirim"|"tekrar"}}


def harita_oku(anahtar: str, dizin: Path | None = None) -> dict | None:
    try:
        h = json.loads(((dizin or HARITA_DIZINI) / f"{anahtar}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(h, dict) or h.get("surum") != SURUM or not isinstance(h.get("kitaplar"), list) \
            or not isinstance(h.get("eslesme"), dict):
        return None
    return h


def tablo_durumu(tablo: dict | None, bugun: date) -> str | None:
    """None (kullanılabilir) | "tablo_yok" | "tablo_eski" (bugünün öğretim yılı ya da dönemi tablonunki değil)."""
    if tablo is None:
        return "tablo_yok"
    k = tablo.get("kaynak") or {}
    if ogretim_yili_adi(bugun) != k.get("ogretim_yili") or donem_no(bugun) != k.get("donem"):
        return "tablo_eski"
    return None


def _ders(anahtar: str) -> str:
    ders = ANAHTAR_DERSLERI.get(anahtar)
    if ders is None:
        raise KilavuzHatasi("bilinmeyen_ders")
    return ders


def _sinav_kaydi(g: Girdiler, ders: str, no: int) -> dict | None:
    """O dersin o yazılısına ait sınav kaydı; birden çoksa kesin duyurulu, tarihli, yaklaşan olan."""
    adaylar = [e for e in g.sinavlar if isinstance(e, dict) and isinstance(e.get("senaryo"), dict)
               and e["senaryo"].get("ders") == ders and e["senaryo"].get("sinav_no") == no]
    if not adaylar:
        return None
    return max(adaylar, key=lambda e: (e["senaryo"].get("durum") in KESIN_DURUMLAR, bool(e.get("date")),
                                       e.get("status") == "upcoming"))


def sinav_durumu(g: Girdiler, ders: str, no: int) -> dict:
    """Kesin (duyurulan senaryo tabloda var) | olası | ülke geneli | geçti. Olası durum tek senaryo taşımaz (K8)."""
    tablo_sinavi = g.tablo["dersler"][ders]["sinavlar"][str(no)]
    senaryolar = tablo_sinavi.get("senaryolar") or {}
    kayit = _sinav_kaydi(g, ders, no)
    blok = kayit["senaryo"] if kayit else {}
    tarih = _gun(kayit.get("date")) if kayit else None
    gecti = bool(kayit) and kayit.get("status") == "past"
    d = {"tur": "olasi", "senaryo": None, "senaryo_sayisi": len(senaryolar),
         "tarih": tarih.isoformat() if tarih else None,
         "kalan_gun": (tarih - g.bugun).days if tarih and not gecti and tarih >= g.bugun else None,
         "sinav_id": kayit.get("id") if kayit else None, "duyuru": blok.get("cumle"), "uyari": None,
         "anilan": [int(n) for n in blok.get("anilan") or []],
         "duyurulan_konu": int(blok.get("eslesen_konu_sayisi") or 0)}
    duyurulan = blok.get("durum") in KESIN_DURUMLAR and str(blok.get("senaryo")) in senaryolar
    if gecti:
        # D22: geçmiş sınavın kılavuzu duyurulan senaryoyla açılır; duyurulmamışsa hiçbir senaryo söylenmez (K8).
        d.update(tur="gecti", senaryo=int(blok["senaryo"]) if duyurulan else None)
    elif tablo_sinavi["tur"] == "ulke_geneli":
        d["tur"] = "ulke_geneli"
    elif duyurulan:
        d.update(tur="kesin", senaryo=int(blok["senaryo"]), uyari="kismen" if blok["durum"] == "kismen" else None)
    elif blok.get("durum") == "senaryo_yok":
        d["uyari"] = "senaryo_yok"
    return d


def _soru(g: Girdiler, ders: str, no: int, durum: dict) -> int | None:
    if durum["tur"] not in ("kesin", "gecti") or durum["senaryo"] is None:
        return None
    dagilim = (g.tablo["dersler"][ders]["sinavlar"][str(no)].get("senaryolar") or {}).get(str(durum["senaryo"]))
    return sum(dagilim.values()) if dagilim else None


def genel_bakis(g: Girdiler) -> dict:
    """Ana sayfa (spec §3.1): önce tarihi belli yaklaşan yazılılar, sonra altı dersin karosu."""
    durum = tablo_durumu(g.tablo, g.bugun)
    kaynak = None
    if g.tablo is not None:
        k = g.tablo.get("kaynak") or {}
        kaynak = {a: k.get(a) for a in ("baslik", "sayfa", "meb_guncelleme", "ogretim_yili", "donem", "sinif")}
    sonuc = {"durum": durum or "hazir", "kaynak": kaynak, "yaklasan": [], "dersler": []}
    if durum:
        return sonuc
    for ders, anahtar in DERS_ANAHTARLARI.items():
        dt = g.tablo["dersler"].get(ders)
        if dt is None:
            continue
        sinavlar = []
        for no in sorted(int(n) for n in dt["sinavlar"]):
            d = sinav_durumu(g, ders, no)
            soru = _soru(g, ders, no, d)
            sinavlar.append({"sinav_no": no, "durum": d, "soru": soru})
            if d["tarih"] and d["kalan_gun"] is not None:
                sonuc["yaklasan"].append({"ders": ders, "anahtar": anahtar, "sinav_no": no, "durum": d, "soru": soru})
        sonuc["dersler"].append({"ders": ders, "anahtar": anahtar, "kitap_bolumleri": anahtar in g.haritalar,
                                 "sinavlar": sinavlar})
    sonuc["yaklasan"].sort(key=lambda y: (y["durum"]["tarih"], y["ders"]))
    return sonuc


def _kod_sirasi(kod: str) -> tuple:
    return tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in kod.split("."))


def _eslesen_bolumler(harita: dict | None, kod: str):
    """Haritanın bu çıktı için gösterdiği bölümler: (kitap, ünite, çerçeve, konu | None)."""
    if not harita:
        return
    for e in harita.get("eslesme", {}).get(kod, []):
        try:
            kitap = harita["kitaplar"][e["kitap"]]
            unite = next(u for u in kitap["uniteler"] if u["no"] == e["unite"])
            cer = next(c for c in unite["cerceveler"] if c["no"] == e["cerceve"])
        except (IndexError, KeyError, TypeError, StopIteration):
            continue
        konu = next((k for k in cer["konular"] if k["ad"] == e.get("konu")), None) if e.get("konu") else None
        yield kitap, unite, cer, konu


def _kitap_yollari(harita: dict | None, kod: str) -> list[dict]:
    yollar = []
    for kitap, unite, cer, konu in _eslesen_bolumler(harita, kod):
        hedef = konu or cer
        pdf = hedef["sayfa"] + int(kitap.get("sayfa_kaymasi") or 0)
        yollar.append({"kitap": kitap["baslik"], "unite": f"{unite['no']}. Ünite", "unite_no": unite["no"],
                       "unite_ad": unite["ad"], "cerceve": f"{cer['no']}. {cer['ad']}", "cerceve_no": cer["no"],
                       "konu": konu["ad"] if konu else None, "sayfa": hedef["sayfa"], "son_sayfa": hedef["son_sayfa"],
                       "baglanti": f"{kitap['pdf_url']}#page={pdf}"})
    return yollar


def _kisa_ad(cikti: dict, yollar: list[dict]) -> str:
    """Tek bir kitap konusuna bağlıysa konunun kitaptaki adı (K1); değilse MEB metninin ilk altı sözcüğü."""
    if len(yollar) == 1 and yollar[0]["konu"]:
        return yollar[0]["konu"]
    sozcukler = cikti["metin"].split()
    return " ".join(sozcukler[:KISA_AD_SOZCUK]) + ("…" if len(sozcukler) > KISA_AD_SOZCUK else "")


def _cumle_duzeni(s: str) -> str:
    k = s.replace("İ", "i").replace("I", "ı").lower()
    return (k[:1].replace("i", "İ").replace("ı", "I").upper() + k[1:]) if k else k


def unite_grubu(harita: dict | None, no: int, ad: str | None = None) -> tuple[tuple, str]:
    """Bir ünitenin tek grup anahtarı ve başlığı (U4/D19; kılavuz bölümleri de bunu kullanır). Başlık, o ünitenin
    haritadaki adından çözülür — gruba ilk giren çıktıdan değil; ad verilmişse (kitap yolundan) o, yoksa haritanın
    kitaplarında aynı numaralı ilk ünite; harita ya da ünite yoksa yalnız "N. Ünite"."""
    if ad is None and harita:
        ad = next((u.get("ad") for k in harita.get("kitaplar", []) for u in k.get("uniteler", [])
                   if u.get("no") == no), None)
    return (0, no, ""), f"{no}. Ünite · {ad}" if ad else f"{no}. Ünite"


def _grup(cikti: dict, yollar: list[dict], harita: dict | None) -> tuple[tuple, str]:
    """Karşılaştırma tablosunun grubu: haritadan ünite; yoksa tablonun alanı (Türkçe); yoksa koddaki ünite no
    (başlığı yine haritanın ünitesinden); o da yoksa "Diğer"."""
    if yollar:
        return unite_grubu(harita, yollar[0]["unite_no"], yollar[0]["unite_ad"])
    if cikti.get("alan"):
        return (1, 0, cikti["alan"]), _cumle_duzeni(cikti["alan"])
    m = _UNITE_KODU.match(cikti["kod"])
    if m:
        return unite_grubu(harita, int(m.group(1) or m.group(2)))
    return (2, 0, ""), "Diğer"


def _hazir_mi(g: Girdiler) -> None:
    durum = tablo_durumu(g.tablo, g.bugun)
    if durum:
        raise KilavuzHatasi(durum)


def _sinav_tablosu(g: Girdiler, ders: str, no: int) -> tuple[dict, dict]:
    dt = g.tablo["dersler"][ders]
    if str(no) not in dt["sinavlar"]:
        raise KilavuzHatasi("bilinmeyen_sinav")
    return dt, dt["sinavlar"][str(no)]


def _guncellik(g: Girdiler, anahtar: str, harita: dict | None, dt: dict) -> dict:
    """K12: harita başka bir tablo sürümüne göre kurulduysa ya da `--denetle` kitabın değiştiğini yazdıysa."""
    tablo_degisti = bool(harita) and (harita.get("senaryo_tablosu") or {}).get("ders_sha256") != dt.get("sha256")
    denetim = g.kitap_denetimi.get(anahtar) if isinstance(g.kitap_denetimi, dict) else None
    guncel = {k.get("pdf_url"): k.get("sha256") for k in (denetim or {}).get("kitaplar", []) if isinstance(k, dict)}
    kitap_degisti = bool(harita) and any(k.get("pdf_url") in guncel and guncel[k["pdf_url"]] != k.get("sha256")
                                         for k in harita["kitaplar"])
    return {"tablo_degisti": tablo_degisti, "kitap_degisti": kitap_degisti}


def ders_ozeti(g: Girdiler, anahtar: str, no: int) -> dict:
    """Ders sayfası (spec §3.2): bu yazılının çıktı × senaryo matrisi, ünite gruplu, kitap yollarıyla."""
    ders = _ders(anahtar)
    _hazir_mi(g)
    dt, sinav = _sinav_tablosu(g, ders, no)
    harita = g.haritalar.get(anahtar)
    durum = sinav_durumu(g, ders, no)
    senaryolar = sorted(int(n) for n in (sinav.get("senaryolar") or {}))
    gruplar: dict[tuple, dict] = {}
    for c in sorted(dt["ciktilar"], key=lambda c: _kod_sirasi(c["kod"])):
        sayilar = {str(n): int(sinav["senaryolar"][str(n)].get(c["kod"], 0)) for n in senaryolar}
        if not any(sayilar.values()):
            continue
        yollar = _kitap_yollari(harita, c["kod"])
        grup_anahtari, baslik = _grup(c, yollar, harita)
        gruplar.setdefault(grup_anahtari, {"baslik": baslik, "satirlar": []})["satirlar"].append({
            "kod": c["kod"], "kisa_ad": _kisa_ad(c, yollar), "metin": c["metin"], "sayilar": sayilar,
            "her_senaryoda": all(sayilar.values()), "kitapta": yollar,
            "kitap_durumu": ("var" if yollar else "bulunamadi") if harita else "harita_yok"})
    return {"ders": ders, "anahtar": anahtar, "sinav_no": no, "tur": sinav["tur"], "not": sinav.get("not"),
            "sinavlar": [{"sinav_no": int(n), "durum": sinav_durumu(g, ders, int(n))}
                         for n in sorted(dt["sinavlar"], key=int)],
            "durum": durum, "senaryolar": senaryolar, "duyurulan": durum["senaryo"],
            "gruplar": [gruplar[k] for k in sorted(gruplar)],
            "toplamlar": {str(n): sum(sinav["senaryolar"][str(n)].values()) for n in senaryolar},
            "kitap_bolumleri": harita is not None,
            "harita_onayli": bool(harita and (harita.get("denetim") or {}).get("kim")),
            "guncellik": _guncellik(g, anahtar, harita, dt)}

