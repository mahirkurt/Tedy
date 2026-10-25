"""Sınav Hazırlığı kılavuz modeli (spec 2026-10-25 §2.4, §3, §4, §7; plan Görev 6–7).

Saf işlevler: girdiler `Girdiler` ile gelir (API toplar), ağ ve yazım yok — yalnız `harita_oku` dosya okur.
Senaryo tablosu `sinav_senaryo.tablo_oku()`, kitap haritaları `src/kitap_haritalari/<anahtar>.json`
(scripts/meb_kitap_haritasi.py üretir). Kanun K8: senaryo duyurulmadıysa hiçbir alan tek senaryoyu "bu" diye
taşımaz. Kanun K1: kitap başlıkları yalnız haritadan; haritada karşılığı olmayan çıktı "bulunamadi" (yok değil)."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from src.course_names import normalize_course
from src.sinav_senaryo import DERS_ANAHTARLARI, _gun, donem_no, konu_eslestir, ogretim_yili_adi
from src.sinav_tarihi import katla

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
    isaret_sahibi: str | None = None                     # işaretlerin sahibi (kâğıtta yazılır, D16); API belirler


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



# ── Kılavuz (spec §2.4, §4; plan Görev 7) ──────────────────────────────────────────────────────────────────────

ISARETLER = ("hazirim", "tekrar")
_ISARET_SIRASI = {"tekrar": 0, None: 1, "hazirim": 2}


def _bolum_basliklari(harita: dict | None, kod: str) -> list[dict]:
    """Çıktının kitap bölümlerinde ele alınan başlıklar (K6: hepsi). Konuya bağlıysa konunun, çerçeveye bağlıysa
    (`konu: None`) çerçevenin ve bütün konularının başlıkları; aynı bölüm iki kez yazılmaz."""
    out: list[dict] = []
    gorulen: set[int] = set()
    for _, _, cer, konu in _eslesen_bolumler(harita, kod):
        for bolum in ([konu] if konu else [cer, *cer["konular"]]):
            if id(bolum) in gorulen:
                continue
            gorulen.add(id(bolum))
            out += [{"ad": b["ad"], "tur": b["tur"], "amac": b.get("amac"), "sayfa": b["sayfa"]}
                    for b in bolum.get("basliklar", [])]
    return out


def _terimler(yollar: list[dict]) -> list[str]:
    """Okul kartı ve ödev metninde aranacak katlanmış adlar: konu adları, yoksa çerçeve adları."""
    adlar = [y["konu"] for y in yollar if y["konu"]] or [y["cerceve"].split(". ", 1)[-1] for y in yollar]
    return [katla(a) for a in dict.fromkeys(adlar) if len(katla(a)) >= 4]


def _hafta_no(etiket: str) -> int:
    m = re.match(r"\s*(\d+)\.\s*Hafta", etiket)
    return int(m.group(1)) if m else 999


def _metinler(deger) -> list[str]:
    return [str(x) for x in deger] if isinstance(deger, (list, tuple)) else []


def okulda(haftalar: dict, ders: str, terimler: list[str]) -> list[dict]:
    """Konunun adı o dersin haftalık kartlarında geçtiği haftalar (spec §4.4 "okulda işlendiği hafta")."""
    if not terimler or not isinstance(haftalar, dict):
        return []
    out = []
    for etiket in sorted(haftalar, key=_hafta_no):
        dersler = haftalar[etiket] if isinstance(haftalar[etiket], dict) else {}
        for ad, icerik in dersler.items():
            if normalize_course(str(ad)) != ders or not isinstance(icerik, dict):
                continue
            metin = katla(" ".join(_metinler(icerik.get("cards")) + _metinler(icerik.get("items"))
                                   + [str(icerik.get("text") or "")]))
            if any(t in metin for t in terimler):
                out.append({"hafta": etiket})
                break
    return out


def ilgili_odevler(odevler: list, ders: str, terimler: list[str]) -> list[dict]:
    if not terimler:
        return []
    out = []
    for r in odevler:
        if not isinstance(r, dict) or normalize_course(str(r.get("Ders Adı") or "")) != ders:
            continue
        ayrinti = r.get("detail") if isinstance(r.get("detail"), dict) else {}
        metin = katla(f"{r.get('Ödev Başlığı') or ''} {ayrinti.get('description') or ''}")
        if any(t in metin for t in terimler):
            out.append({"baslik": str(r.get("Ödev Başlığı") or ""), "teslim": r.get("Ödev Son Teslim Tarihi")})
    return out


def ilgili_moduller(moduller: list, kod: str) -> list[dict]:
    return [{"baslik": str(m.get("title") or m["slug"]), "yol": f"/moduller/{m['slug']}/v{m['version']}"}
            for m in moduller if isinstance(m, dict) and m.get("slug") and isinstance(m.get("version"), int)
            and kod in (m.get("outcomes") or [])]


def _agirlik(b: dict) -> int:
    """Çıktının ağırlığı: seçili senaryodaki soru sayısı; olası kipte senaryolar arası en yüksek sayı."""
    if b["soru"] is not None:
        return b["soru"]
    return b["aralik"][1] if b["aralik"] else 0


def calisma_plani(bloklar: list[dict], bugun: date, tarih: date | None) -> dict | None:
    """Kalan günlere çıktıları dağıtan deterministik plan (spec §4.6): önce "tekrar" işaretliler, sonra işaretsizler,
    en son "hazırım"lar; her grupta soru ağırlığı büyükten küçüğe. Sınavdan önceki gün genel tekrardır."""
    if tarih is None or tarih <= bugun:
        return None
    adaylar = [b for b in bloklar if b["senaryoda"]]
    if not adaylar:
        return None
    adaylar.sort(key=lambda b: (_ISARET_SIRASI.get(b["isaret"], 1), -_agirlik(b), _kod_sirasi(b["kod"])))
    gunler = [bugun + timedelta(days=i) for i in range((tarih - bugun).days)]
    calisma = gunler[:-1] if len(gunler) >= 2 else gunler
    plan = [{"tarih": g.isoformat(), "ciktilar": [], "genel_tekrar": False} for g in calisma]
    for i, b in enumerate(adaylar):
        plan[i % len(plan)]["ciktilar"].append(b["kod"])
    if len(gunler) >= 2:
        plan.append({"tarih": gunler[-1].isoformat(), "ciktilar": [b["kod"] for b in adaylar], "genel_tekrar": True})
    return {"gunler": [p for p in plan if p["ciktilar"]]}


def _ozet(bloklar: list[dict], dagilim: dict | None, sinav: dict) -> dict:
    """K8: seçili senaryo yoksa tek toplam yok; senaryolar arası toplam aralığı ve "her senaryoda" çıktılar var."""
    kapsam = [b for b in bloklar if b["senaryoda"]]
    toplamlar = [sum(d.values()) for d in (sinav.get("senaryolar") or {}).values()]
    return {"toplam_soru": sum(b["soru"] for b in kapsam) if dagilim is not None else None,
            "soru_araligi": [min(toplamlar), max(toplamlar)] if dagilim is None and toplamlar else None,
            "cikti_sayisi": len(kapsam), "her_senaryoda": [b["kod"] for b in bloklar if b["her_senaryoda"]]}


def _dogrulama(kayit: dict | None, dt: dict) -> dict | None:
    """Duyuru doğrulaması (spec §4.5): duyurudaki konuların karşılığı, senaryo dışı ve karşılıksız konular,
    duyurunun saymadığı senaryo çıktıları."""
    if not kayit:
        return None
    blok = kayit["senaryo"]
    konular = [str(k) for k in kayit.get("konular") or []]
    if not konular:
        return None
    kesin = blok.get("durum") in KESIN_DURUMLAR
    return {"duyurulan_konular": [{"konu": k, "kodlar": konu_eslestir(k, dt["ciktilar"])} for k in konular],
            "senaryo_disi": list(blok.get("senaryo_disi_konular") or []),
            "karsiligi_yok": list(blok.get("eslesmeyen_konular") or []),
            "duyurunun_saymadigi": [d["kod"] for d in blok.get("dagilim") or [] if kesin and not d.get("duyuruda")]}


def _ebeveyn(bloklar: list[dict], ozet: dict) -> dict:
    kapsam = [b for b in bloklar if b["senaryoda"]]
    return {"cikti_sayisi": len(kapsam), "toplam_soru": ozet["toplam_soru"], "soru_araligi": ozet["soru_araligi"],
            "hazirim": sum(b["isaret"] == "hazirim" for b in kapsam), "tekrar": sum(b["isaret"] == "tekrar" for b in kapsam),
            "isaretsiz": sum(b["isaret"] is None for b in kapsam),
            "en_agir": [b["kod"] for b in sorted(kapsam, key=lambda b: (-_agirlik(b), _kod_sirasi(b["kod"])))[:3]]}


def _kaynaklar(tablo: dict, dt: dict, harita: dict | None, ders: str) -> list[dict]:
    k = tablo["kaynak"]
    out = [{"etiket": f"MEB ÖDSGM · {k['baslik']}", "adres": k["sayfa"]}]
    if dt.get("adres"):
        out.append({"etiket": f"{ders} konu-soru dağılım tablosu", "adres": dt["adres"]})
    out += [{"etiket": f"{kt['baslik']} (EBA PDF)", "adres": kt["pdf_url"]} for kt in (harita or {}).get("kitaplar", [])]
    return out


def _damgalar(g: Girdiler, harita: dict | None) -> dict:
    k = g.tablo["kaynak"]
    return {"meb_guncelleme": k.get("meb_guncelleme"), "tablo_alindi": k.get("alindi"),
            "kitaplar": [{"baslik": kt["baslik"], "baski": kt.get("baski"), "sha256_kisa": str(kt.get("sha256") or "")[:12]}
                         for kt in (harita or {}).get("kitaplar", [])],
            "uretim": g.bugun.isoformat()}


def icerik_ozeti(model: dict) -> str:
    """Modelin sha256 özeti (PDF önbellek anahtarı): aynı girdi, aynı özet."""
    govde = {k: v for k, v in model.items() if k != "icerik_ozeti"}
    return hashlib.sha256(json.dumps(govde, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _uniteler(oz: dict, blok_listesi: list[list[dict]], sayfalar: dict[str, tuple[int, int]]) -> list[dict]:
    """Ünite › çerçeve › çıktı. Üniteler `ders_ozeti` gruplarıdır (başlık/anahtar `unite_grubu`'ndan: matrisle aynı,
    tek); haritada karşılığı olmayan çıktı kendi ünitesinde başlıksız (`baslik: None`) son çerçevede toplanır, ikinci
    bir ünite açılmaz (U4). `duzey` göreli başlık düzeyidir (ünite 1); çerçeve başlığı yoksa çıktı bir basamak yukarıda
    durur, düzey atlanmaz (D4)."""
    uniteler = []
    for grup, bloklar in zip(oz["gruplar"], blok_listesi):
        cerceveler: dict[tuple, dict] = {}
        for b in bloklar:
            yol = b["kitapta"][0] if b["kitapta"] else None
            anahtar = (0, yol["cerceve_no"]) if yol else (1, 0)
            cerceve = cerceveler.setdefault(anahtar, {
                "baslik": yol["cerceve"] if yol else None, "sayfa": None, "son_sayfa": None, "bloklar": []})
            if yol and cerceve["sayfa"] is None:
                cerceve["sayfa"], cerceve["son_sayfa"] = sayfalar[b["kod"]]
            cerceve["bloklar"].append(b)
        siralı = [cerceveler[k] for k in sorted(cerceveler)]
        for c in siralı:
            c["duzey"] = 2 if c["baslik"] is not None else None
            for b in c["bloklar"]:
                b["duzey"] = 3 if c["baslik"] is not None else 2
        uniteler.append({"baslik": grup["baslik"], "duzey": 1, "cerceveler": siralı})
    return uniteler


def kilavuz(g: Girdiler, anahtar: str, no: int, senaryo: int | None, secenekler: dict) -> dict:
    """Kapsam kılavuzu modeli (spec §2.4, §4). `senaryo` verilmezse duyurulan senaryo; o da yoksa olası kip: bloklar
    tek sayı değil senaryolar arası aralık taşır (K8). `secenekler`: {"ebeveyn": bool, "isaret": bool}. İşaretler
    `g.isaretler`'den gelir, sahibi `g.isaret_sahibi`'dir (D16: model saf; kimin işaretiyle çağrılacağını API seçer)."""
    oz = ders_ozeti(g, anahtar, no)
    ders = oz["ders"]
    dt, sinav = _sinav_tablosu(g, ders, no)
    harita = g.haritalar.get(anahtar)
    duyurulan = oz["duyurulan"]
    if sinav["tur"] == "ulke_geneli":
        senaryo, kip = None, "ulke_geneli"
    else:
        if senaryo is not None and str(senaryo) not in (sinav.get("senaryolar") or {}):
            raise KilavuzHatasi("bilinmeyen_senaryo")
        senaryo = senaryo if senaryo is not None else duyurulan
        kip = "kesin" if senaryo is not None and senaryo == duyurulan else "olasi"
    isaret_acik = bool(secenekler.get("isaret", True))
    ham_isaretler = g.isaretler.get(anahtar) if isinstance(g.isaretler, dict) else None
    isaretler = ham_isaretler if isaret_acik and isinstance(ham_isaretler, dict) else {}
    dagilim = sinav["senaryolar"][str(senaryo)] if senaryo is not None else None
    bloklar: list[dict] = []
    blok_listesi: list[list[dict]] = []
    cerceve_sayfalari: dict[str, tuple[int, int]] = {}      # çıktı kodu → ilk eşleşen çerçevenin basılı sayfa aralığı
    for grup in oz["gruplar"]:
        grup_bloklari = []
        for s in grup["satirlar"]:
            sayilar = list(s["sayilar"].values())
            terimler = _terimler(s["kitapta"])
            isaret = isaretler.get(s["kod"])
            bolum = next(_eslesen_bolumler(harita, s["kod"]), None)
            b = {"kod": s["kod"], "kisa_ad": s["kisa_ad"], "metin": s["metin"],
                 "senaryoda": dagilim.get(s["kod"], 0) > 0 if dagilim is not None else True,
                 "soru": int(dagilim.get(s["kod"], 0)) if dagilim is not None else None,
                 "aralik": None if dagilim is not None else [min(sayilar), max(sayilar)],
                 "her_senaryoda": s["her_senaryoda"], "kitapta": s["kitapta"], "kitap_durumu": s["kitap_durumu"],
                 "basliklar": _bolum_basliklari(harita, s["kod"]),
                 "okulda": okulda(g.haftalar, ders, terimler), "odevler": ilgili_odevler(g.odevler, ders, terimler),
                 "moduller": ilgili_moduller(g.moduller, s["kod"]), "isaret": isaret if isaret in ISARETLER else None}
            if bolum:
                cerceve_sayfalari[s["kod"]] = (bolum[2]["sayfa"], bolum[2]["son_sayfa"])
            grup_bloklari.append(b)
        bloklar += grup_bloklari
        blok_listesi.append(grup_bloklari)
    uniteler = _uniteler(oz, blok_listesi, cerceve_sayfalari)
    ozet = _ozet(bloklar, dagilim, sinav)
    tarih = _gun(oz["durum"]["tarih"])
    model = {
        "surum": SURUM, "ders": ders, "anahtar": anahtar, "sinav_no": no, "durum": oz["durum"], "kip": kip,
        "senaryo": senaryo, "duyurulan": duyurulan,
        "secilen_duyurulan_degil": senaryo is not None and senaryo != duyurulan, "not": sinav.get("not"),
        "ozet": ozet, "matris": {k: oz[k] for k in ("senaryolar", "duyurulan", "gruplar", "toplamlar")},
        "uniteler": uniteler,
        "dogrulama": _dogrulama(_sinav_kaydi(g, ders, no), dt),
        "plan": calisma_plani(bloklar, g.bugun, tarih) if oz["durum"]["tur"] != "gecti" else None,
        "ebeveyn": _ebeveyn(bloklar, ozet) if secenekler.get("ebeveyn") else None,
        "kaynaklar": _kaynaklar(g.tablo, dt, harita, ders), "damgalar": _damgalar(g, harita),
        "guncellik": oz["guncellik"], "kitap_bolumleri": oz["kitap_bolumleri"], "harita_onayli": oz["harita_onayli"],
        "yz": {"durum": "kapali"},
        "isaret_sahibi": g.isaret_sahibi if isaret_acik else None,
        "secenekler": {"ebeveyn": bool(secenekler.get("ebeveyn")), "isaret": isaret_acik},
    }
    model["icerik_ozeti"] = icerik_ozeti(model)
    return model
