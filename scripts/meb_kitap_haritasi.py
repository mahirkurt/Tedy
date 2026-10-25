"""MEB ders kitabı haritası üretici (spec 2026-10-25 §2.2): EBA PDF'inden ünite → içerik çerçevesi → konu → bölüm
içi başlıklar ve basılı sayfalar; çıktı → kitap bölümü eşlemesi. Çıktı src/kitap_haritalari/<anahtar>.json; elle
düzenlenmez (gürültü temizliği KITAPLAR ayarındadır, sonra betik yeniden koşar).

PDF güvenilmeyen veridir: boş bir geçici dizine iner, poppler araçları argüman listesiyle çağrılır, betik o
dizinden koşmaz ve Python `-I` ile çalışır.

    env -u ANTHROPIC_API_KEY .venv/bin/python -I scripts/meb_kitap_haritasi.py fen-bilimleri --pdf 1=/tmp/meb-kitap-yoklama/fen7-1.pdf --kuru
    env -u ANTHROPIC_API_KEY .venv/bin/python -I scripts/meb_kitap_haritasi.py fen-bilimleri --pdf 1=… --denetim-kim "…"
    env -u ANTHROPIC_API_KEY .venv/bin/python -I scripts/meb_kitap_haritasi.py fen-bilimleri --denetle
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from src.json_utils import atomic_json_dump  # noqa: E402
from src.sinav_senaryo import _puan, tablo_oku  # noqa: E402
from src.sinav_tarihi import katla  # noqa: E402

SURUM = 1
CIKTI_DIZINI = KOK / "src" / "kitap_haritalari"
DENETIM_DOSYASI = KOK / "output" / "kitap_denetimi.json"
# Ünite içindeki ama konu olmayan girdiler (katlanmış): sayfa sınırı için okunur, haritaya girmez.
UNITE_EKLERI = ("on degerlendirme", "iz birakanlar", "unite sonu degerlendirme")
_UNITE = re.compile(r"^(\d+)\.\s*Ünite\s+(\S.*)$")
_GIRDI = re.compile(r"^(?:(\d+)\.\s+)?(.+?)\s*\.{2,}[\s.]*(\d{1,4})$")
_SAYI = re.compile(r"^\d+$")

# Ders başına ayar. Ölçüldü (2026-10-25, Fen 7-1): pdftohtml'de başlık size 20 (Arial, beyaz bant), gövde 17, içerik
# çerçevesi adı Anton; başlıklar sol 107–124 px'te, gövde 119 px'te; kalın tanım başlığı gövde boyunda ve ":" ile biter.
# "atla": onayda gürültü bulunan başlıklar (s. 49 kavram haritası kutusundaki "Bulutsu", s. 25'teki altı "… Alanında"
# şekil etiketi — başlık boyunda ve sarı, +1 punto toleransıyla girer).
KITAPLAR: dict[str, dict] = {
    "fen-bilimleri": {
        "ders": "Fen Bilimleri",
        "beklenen_eslesmeyen": (),
        "basliksiz_konular": (),
        "kitaplar": [{
            "baslik": "Fen Bilimleri 7 (1. Kitap)",
            "pdf_url": "https://cdn.eba.gov.tr/temel-egitim/yayin/2026-2027/ktp/fenbilimleri7-1_v3.pdf",
            "kaynak_sayfa": None,
            "baski": "2026-2027",
            "sayfa_kaymasi": 1,
            "icindekiler_pdf_sayfalari": (8, 8),
            "duzen": {"baslik_boyu": 20, "govde_boyu": 17, "cerceve_ailesi": "Anton", "baslik_sol_en_cok": 130,
                      "govde_sol": 119, "tanim": True,
                      "atla": ("Bulutsu", "Sağlık Alanında", "Enerji Alanında", "İletişim Alanında", "Gıda Alanında",
                               "Ulaşım Alanında", "Endüstri Alanında")},
        }],
    },
}
# Pedagojik bloklar (katlanmış önek → tür) ve başlık sayılmayan kutu etiketleri / tanım dışı kalın satırlar.
ETIKETLER = (("etkinlik noktasi", "etkinlik"), ("kesif noktasi", "etkinlik"), ("performans gorevi", "etkinlik"),
             ("baglanti noktasi", "baglanti"), ("kontrol noktasi", "kontrol"), ("neler ogrendik", "ozet"))
KUTU_ETIKETLERI = ("haber", "bilgi bankasi", "tarihe not dusenler")
TANIM_DISI = ("ornek", "ornek problem", "amac", "amaci", "islevi", "sorunlar", "cozum onerileri")
YAKINLIK = 0.1


def _ogeler(xml: str) -> list[dict]:
    """pdftohtml -xml → metin öğeleri (sayfa, üst, sol sırasıyla); fontspec kimlikleri sayfalar arasında geçerlidir."""
    kok = ET.fromstring(xml.encode("utf-8"))
    boylar: dict[str, tuple[int, str]] = {}
    out = []
    for sayfa in kok.iter("page"):
        no = int(sayfa.get("number"))
        for el in sayfa:
            if el.tag == "fontspec":
                boylar[el.get("id")] = (int(el.get("size")), el.get("family") or "")
            elif el.tag == "text":
                boy, aile = boylar.get(el.get("font"), (0, ""))
                metin = " ".join("".join(el.itertext()).split())
                if metin:
                    out.append({"sayfa": no, "ust": int(el.get("top")), "sol": int(el.get("left")),
                                "genislik": int(el.get("width") or 0), "boy": boy, "aile": aile, "kalin": el.find(".//b") is not None, "metin": metin})
    out.sort(key=lambda o: (o["sayfa"], o["ust"], o["sol"]))
    return out


def _etiket_turu(katli: str) -> str | None:
    return next((tur for on, tur in ETIKETLER if katli.startswith(on)), None)


def _etiket(ogeler: list[dict], baslik: dict) -> tuple[dict, list[dict]] | None:
    """Başlığın altındaki (≤ 120 px) "Amaç:" etiketi. Poppler etiketi bazen iki kutuya böler ("A" + "maç:", ölçüldü:
    basılı s. 94); aynı satırdaki (üst farkı ≤ 3) bitişik (aralık ≤ 8 px) kalın parçalar birleştirilip öyle eşleştirilir.
    Etiketin parçalarıyla birlikte döner."""
    kalin = sorted((o for o in ogeler if o["sayfa"] == baslik["sayfa"] and o["kalin"]
                    and 0 < o["ust"] - baslik["ust"] <= 120), key=lambda o: (o["ust"], o["sol"]))
    for i, ilk in enumerate(kalin):
        parcalar = [ilk]
        for o in kalin[i + 1:]:
            son = parcalar[-1]
            if abs(o["ust"] - ilk["ust"]) <= 3 and 0 <= o["sol"] - (son["sol"] + son["genislik"]) <= 8:
                parcalar.append(o)
        # Bitişik dizinin her ön eki aday: "Amaç:" yanındaki kalın sözcükle ("Amaç: Adımlar") uzamış olabilir.
        for n in range(1, len(parcalar) + 1):
            if katla("".join(p["metin"] for p in parcalar[:n])).rstrip(": ") == "amac":
                return ilk, parcalar[:n]
    return None


def _amac(ogeler: list[dict], baslik: dict) -> str | None:
    """Etkinlik başlığının altındaki "Amaç:" satırı ve hemen alttaki (≤ 26 px, etiketin 15 px'ten fazla solunda — kutunun
    kenarına taşan) en çok iki devam satırı; tireyle bölünen sözcük birleşir. Paragraf gövde kenarında (etiketle aynı
    hizada) başlar, alınmaz (ölçüldü: devam satırı sol 86–95 px, etiket 120–129 px, paragraf 119 px)."""
    bulunan = _etiket(ogeler, baslik)
    if bulunan is None:
        return None
    e, parcalar = bulunan
    ayni = sorted((o for o in ogeler if o["sayfa"] == e["sayfa"] and abs(o["ust"] - e["ust"]) <= 3 and o["sol"] > e["sol"]
                   and not any(o is p for p in parcalar)), key=lambda o: o["sol"])
    satirlar = [" ".join(o["metin"] for o in ayni)]
    ust = e["ust"]
    for _ in range(2):
        alt = sorted((o for o in ogeler if o["sayfa"] == e["sayfa"] and 12 < o["ust"] - ust <= 26
                      and o["sol"] < e["sol"] - 15), key=lambda o: o["sol"])
        if not alt:
            break
        satirlar.append(" ".join(o["metin"] for o in alt))
        ust = alt[0]["ust"]
    metin = ""
    for s in satirlar:
        s = s.strip()
        metin = metin[:-1].rstrip() + s if metin.endswith("-") else f"{metin} {s}".strip()
    return " ".join(metin.split()) or None


def basliklari_ayristir(xml: str, duzen: dict) -> list[dict]:
    """Bölüm içi başlık adayları: başlık boyundaki (çerçeve ailesi dışı) satırlar — aynı satırdaki parçalar birleşir
    ("Performans Görevi" + adı) —, pedagojik etiketler türleriyle; kutu etiketleri, sol kenardan içerideki şekil
    yazıları ve ":" ile biten liste girişleri atılır; `tanim` açıksa gövde boyunda kalın, ":" ile biten, ≤ 4 sözcüklük, gövde kenarındaki satırlar."""
    ogeler = _ogeler(xml)
    atla = {katla(a) for a in duzen.get("atla", ())}
    # Başlık boyu ya da bir punto büyüğü: ölçüldü, bir bölüm başlığı 21 punto geliyor ("Takımyıldızlar", s. 43). Bir punto
    # küçüğü (19) tablo hücresi gürültüsü getirir (s. 97) ve 22 ve üstü şekil yazısıdır; genişliği 0 olan öğe döndürülmüş
    # şekil etiketidir (s. 122), başlık sayılmaz.
    buyuk = [o for o in ogeler if 0 <= o["boy"] - duzen["baslik_boyu"] <= 1 and o["genislik"] > 0
             and duzen["cerceve_ailesi"] not in o["aile"]]
    kullanildi: set[int] = set()
    adaylar = []
    for i, o in enumerate(buyuk):
        if i in kullanildi:
            continue
        satir = [j for j in range(i, len(buyuk)) if j not in kullanildi and buyuk[j]["sayfa"] == o["sayfa"]
                 and abs(buyuk[j]["ust"] - o["ust"]) <= 8]
        kullanildi.update(satir)
        parcalar = sorted((buyuk[j] for j in satir), key=lambda p: p["sol"])
        ilk = parcalar[0]
        tur = _etiket_turu(katla(ilk["metin"]))
        if tur is None:
            if katla(ilk["metin"]) in KUTU_ETIKETLERI or ilk["sol"] > duzen["baslik_sol_en_cok"] or len(ilk["metin"]) < 4:
                continue
            tur, metin = "diger", " ".join(p["metin"] for p in parcalar)
            if metin.endswith(":"):
                continue          # liste girişi ("… hususlar şunlardır:"), başlık değil
        else:
            ek = " ".join(p["metin"] for p in parcalar[1:])
            metin = f"{ilk['metin']}: {ek}" if ek else ilk["metin"]
        if katla(metin) in atla:
            continue
        adaylar.append({"pdf_sayfa": ilk["sayfa"], "ust": min(p["ust"] for p in parcalar), "metin": metin, "tur": tur,
                        "amac": _amac(ogeler, ilk) if tur == "etkinlik" else None})
    if duzen.get("tanim"):
        for o in ogeler:
            if o["boy"] != duzen["govde_boyu"] or not o["kalin"] or not o["metin"].endswith(":"):
                continue
            ad = " ".join(o["metin"].rstrip(":").split())
            if abs(o["sol"] - duzen["govde_sol"]) > 3 or len(ad.split()) > 4 or katla(ad) in TANIM_DISI or katla(ad) in atla:
                continue
            adaylar.append({"pdf_sayfa": o["sayfa"], "ust": o["ust"], "metin": ad, "tur": "tanim", "amac": None})
    adaylar.sort(key=lambda a: (a["pdf_sayfa"], a["ust"]))
    return adaylar


def basliklari_yerlestir(uniteler: list[dict], adaylar: list[dict], kayma: int) -> None:
    """Adayları (sayfa, üst) sırasıyla çerçeve ve konulara dağıtır. Konunun sınırı kendi başlığının konumudur (bulunamazsa
    başlangıç sayfasının tepesi): sonraki konunun başlangıç sayfasında, onun başlığının üstünde kalan blok önceki konuya
    aittir. Konu adının kendisi listeye girmez; konunun bitişi içine düşen son başlığın sayfasına uzar."""
    for u in uniteler:
        for f in u["cerceveler"]:
            f["basliklar"] = []
            f_bas, f_son = (f["sayfa"] + kayma, -1), f["son_sayfa"] + kayma
            adlar = {katla(k["ad"]) for k in f["konular"]}
            sinirlar = []
            for k in f["konular"]:
                k["basliklar"] = []
                p = k["sayfa"] + kayma
                ust = next((a["ust"] for a in adaylar if a["pdf_sayfa"] == p and katla(a["metin"]) == katla(k["ad"])), -1)
                sinirlar.append(((p, ust), k))
            for a in adaylar:
                konum = (a["pdf_sayfa"], a["ust"])
                if konum < f_bas or a["pdf_sayfa"] > f_son or katla(a["metin"]) in adlar:
                    continue
                hedef = f
                for sinir, k in sinirlar:
                    if konum >= sinir:
                        hedef = k
                hedef["basliklar"].append({"ad": a["metin"], "tur": a["tur"], "amac": a["amac"], "sayfa": a["pdf_sayfa"] - kayma})
            for k in f["konular"]:
                k["son_sayfa"] = max([k["son_sayfa"], *(b["sayfa"] for b in k["basliklar"])])


class YapiHatasi(ValueError):
    """Kitap beklenen yapıda değil; harita yazılmaz, eskisi kalır."""


def icindekiler_ayristir(metin: str) -> list[dict]:
    """`pdftotext -layout` İçindekiler sayfası → üniteler (basılı sayfa). Ünite satırı "1. Ünite   Uzay Çağı"; numaralı
    girdi içerik çerçevesi, numarasız girdi konu. Ünite ekleri ve ön/arka kısım (Kitabımızı Tanıyalım, Sözlük…) yalnız
    bitiş sayfası için okunur. Bir satır noktalı sayfa numarasıyla bitmiyorsa sonraki satırla birleşir (iki satıra
    bölünmüş başlık); birleşince de tanınmayan satır YapiHatasi'dır — hiçbir girdi sessizce düşmez."""
    bas = metin.find("İçindekiler")
    if bas < 0:
        raise YapiHatasi("İçindekiler başlığı yok")
    govde = metin[bas + len("İçindekiler"):].split("\f", 1)[0]
    uniteler: list[dict] = []
    akis: list[dict] = []          # sayfası olan her girdi, okunuş sırasıyla: {"sayfa", "tur", "u", "c", "k"}
    bekleyen = ""
    kapali = True                  # henüz ünite yok ya da son ünitenin "Ünite Sonu Değerlendirme"si geçti
    for ham in govde.splitlines():
        s = " ".join(ham.split())
        if not s or _SAYI.fullmatch(s):
            continue
        if bekleyen:
            s = f"{bekleyen} {s}"
        m = _UNITE.match(s)
        if m:
            uniteler.append({"no": int(m.group(1)), "ad": m.group(2).strip(), "sayfa": None, "son_sayfa": None,
                             "cerceveler": []})
            bekleyen, kapali = "", False
            continue
        g = _GIRDI.match(s)
        if not g:
            if bekleyen:
                raise YapiHatasi(f"tanınmayan İçindekiler satırı: {s}")
            bekleyen = s
            continue
        bekleyen = ""
        no, ad, sayfa = g.group(1), g.group(2).strip(), int(g.group(3))
        if akis and sayfa < akis[-1]["sayfa"]:
            raise YapiHatasi(f"İçindekiler sayfaları geriye gidiyor: {ad} s. {sayfa}")
        if kapali:
            akis.append({"sayfa": sayfa, "tur": "dis", "u": None, "c": None, "k": None})
            continue
        u = len(uniteler) - 1
        unite = uniteler[u]
        if unite["sayfa"] is None:
            unite["sayfa"] = sayfa
        if katla(ad) in UNITE_EKLERI:
            akis.append({"sayfa": sayfa, "tur": "ek", "u": u, "c": None, "k": None})
            kapali = katla(ad) == "unite sonu degerlendirme"
            continue
        if no is not None:
            unite["cerceveler"].append({"no": int(no), "ad": ad, "sayfa": sayfa, "son_sayfa": None, "ciktilar": [],
                                        "basliklar": [], "konular": []})
            akis.append({"sayfa": sayfa, "tur": "cerceve", "u": u, "c": len(unite["cerceveler"]) - 1, "k": None})
            continue
        if not unite["cerceveler"]:
            raise YapiHatasi(f"çerçevesiz konu: {ad}")
        cer = unite["cerceveler"][-1]
        cer["konular"].append({"ad": ad, "sayfa": sayfa, "son_sayfa": None, "basliklar": []})
        akis.append({"sayfa": sayfa, "tur": "konu", "u": u, "c": len(unite["cerceveler"]) - 1, "k": len(cer["konular"]) - 1})
    if bekleyen:
        raise YapiHatasi(f"tanınmayan İçindekiler satırı: {bekleyen}")
    if not uniteler:
        raise YapiHatasi("İçindekiler'de ünite yok")

    def bitis(i: int, ayni) -> int:
        """i'den sonra `ayni` olmayan ilk girdinin sayfası − 1 (aynı sayfadaysa kendi sayfası)."""
        for j in range(i + 1, len(akis)):
            if not ayni(akis[j]):
                return max(akis[j]["sayfa"] - 1, akis[i]["sayfa"])
        raise YapiHatasi(f"bitiş sayfası okunamadı: s. {akis[i]['sayfa']}")

    for i, a in enumerate(akis):
        if a["tur"] == "konu":
            uniteler[a["u"]]["cerceveler"][a["c"]]["konular"][a["k"]]["son_sayfa"] = bitis(i, lambda b: False)
        elif a["tur"] == "cerceve":
            uniteler[a["u"]]["cerceveler"][a["c"]]["son_sayfa"] = bitis(
                i, lambda b, a=a: b["tur"] == "konu" and b["u"] == a["u"] and b["c"] == a["c"])
    for u, unite in enumerate(uniteler):
        if unite["sayfa"] is None or not unite["cerceveler"]:
            raise YapiHatasi(f"{unite['no']}. ünitede içerik çerçevesi yok")
        son = max(i for i, a in enumerate(akis) if a["u"] == u)
        unite["son_sayfa"] = bitis(son, lambda b: False)
    return uniteler


def benzerlik(a: str, b: str) -> float:
    """Konu eşlemesinin ölçüsü; senaryo eşleştirmesininki ile aynı olmalı (D18), bu yüzden onu kullanır: biri ötekinin
    ≥ 10 harflik parçasıysa 1; değilse 5 harflik kök Dice'ı."""
    return _puan(a, b)


def ciktilari_esle(uniteler: list[dict], ciktilar: list[dict], kitap_no: int) -> tuple[dict[str, list[dict]], list[str]]:
    """Çıktı → çerçeve: tablonun `konu` alanı İçindekiler'deki çerçeve adıyla katlanmış eşit. Çerçeve içinde konu: çıktı
    metnine en benzer konular (en iyiye YAKINLIK kadar yakın olanlar, okunuş sırasıyla); hiçbir konuya benzemiyorsa
    çerçevenin tamamı (`konu: None`). Çerçevesi bulunamayan çıktı eşleşmeyendir."""
    eslesme: dict[str, list[dict]] = {}
    eslesmedi: list[str] = []
    for c in ciktilar:
        hedef = katla(c.get("konu") or "")
        bulunan = next(((u, f) for u in uniteler for f in u["cerceveler"] if hedef and katla(f["ad"]) == hedef), None)
        if bulunan is None:
            eslesmedi.append(c["kod"])
            continue
        u, f = bulunan
        f["ciktilar"].append(c["kod"])
        puanlar = [(k["ad"], benzerlik(c["metin"], k["ad"])) for k in f["konular"]]
        en = max((p for _, p in puanlar), default=0.0)
        secilen = [ad for ad, p in puanlar if en > 0 and p >= en - YAKINLIK] or [None]
        eslesme[c["kod"]] = [{"kitap": kitap_no, "unite": u["no"], "cerceve": f["no"], "konu": ad} for ad in secilen]
    return eslesme, eslesmedi


def yapi_denetimi(harita: dict, ciktilar: list[dict], beklenen_eslesmeyen=(), basliksiz_konular=()) -> list[str]:
    """Spec §2.2 yapı denetimi; boş liste geçti demektir. Geçmezse harita yazılmaz."""
    hatalar = []
    for kitap in harita["kitaplar"]:
        sinir = kitap["toplam_sayfa"] - kitap["sayfa_kaymasi"]
        onceki = 0
        for u in kitap["uniteler"]:
            for f in u["cerceveler"]:
                if not (1 <= f["sayfa"] <= f["son_sayfa"] <= sinir):
                    hatalar.append(f"çerçeve sayfaları geçersiz: {f['ad']} s. {f['sayfa']}–{f['son_sayfa']}")
                if f["sayfa"] < onceki:
                    hatalar.append(f"sayfalar geriye gidiyor: {f['ad']}")
                onceki = f["sayfa"]
                for k in f["konular"]:
                    if not (f["sayfa"] <= k["sayfa"] <= k["son_sayfa"] <= f["son_sayfa"]):
                        hatalar.append(f"konu çerçevenin dışında: {k['ad']}")
                    if not k["basliklar"] and k["ad"] not in basliksiz_konular:
                        hatalar.append(f"konunun başlığı yok: {k['ad']}")
                    for b in k["basliklar"]:
                        if not (k["sayfa"] <= b["sayfa"] <= k["son_sayfa"]):
                            hatalar.append(f"başlık konunun dışında: {k['ad']} › {b['ad']} s. {b['sayfa']}")
                for b in [*f["basliklar"], *(b for k in f["konular"] for b in k["basliklar"])]:
                    # "Keşif Noktası"nın kitapta amacı yoktur; etkinlik ve performans görevinin amacı olmalı (yoksa etiket
                    # okunamamıştır, amaç sessizce kaybolur).
                    if b["tur"] == "etkinlik" and not b["amac"] and katla(b["ad"]).startswith(("etkinlik noktasi", "performans gorevi")):
                        hatalar.append(f"etkinliğin amacı yok: {b['ad']} s. {b['sayfa']}")
    kodlar = [c["kod"] for c in ciktilar]
    eslesmedi = set(harita["eslesmedi"])
    hatalar += [f"çıktı haritada yok: {kod}" for kod in kodlar if kod not in harita["eslesme"] and kod not in eslesmedi]
    hatalar += [f"beklenmeyen eşleşmeyen çıktı: {kod}" for kod in sorted(eslesmedi - set(beklenen_eslesmeyen))]
    if kodlar and len(eslesmedi) * 2 > len(kodlar):
        hatalar.append(f"çıktıların yarısından çoğu eşleşmedi ({len(eslesmedi)}/{len(kodlar)})")
    return hatalar


def _kod_sirasi(kod: str) -> tuple:
    return tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in kod.split("."))


def harita_kur(anahtar: str, ayar: dict, girdiler: list[dict], tablo: dict, bugun: date) -> dict:
    """Kitap girdilerinden harita (denetimsiz; `main` yapı denetimini uygular). Bir çıktı ilk eşleştiği kitapta kalır."""
    dt = tablo["dersler"][ayar["ders"]]
    kitaplar, eslesme = [], {}
    kalan = list(dt["ciktilar"])
    for no, (kitap, girdi) in enumerate(zip(ayar["kitaplar"], girdiler)):
        uniteler = icindekiler_ayristir(girdi["icindekiler"])
        basliklari_yerlestir(uniteler, basliklari_ayristir(girdi["xml"], kitap["duzen"]), kitap["sayfa_kaymasi"])
        bulunan, _ = ciktilari_esle(uniteler, kalan, no)
        eslesme.update(bulunan)
        kalan = [c for c in kalan if c["kod"] not in bulunan]
        kitaplar.append({"baslik": kitap["baslik"], "pdf_url": kitap["pdf_url"], "kaynak_sayfa": kitap["kaynak_sayfa"],
                         "sha256": girdi["sha256"], "baski": kitap["baski"], "sayfa_kaymasi": kitap["sayfa_kaymasi"],
                         "toplam_sayfa": girdi["toplam_sayfa"], "uniteler": uniteler})
    return {"surum": SURUM, "ders": ayar["ders"], "anahtar": anahtar, "uretildi": bugun.isoformat(),
            "senaryo_tablosu": {"meb_guncelleme": tablo["kaynak"].get("meb_guncelleme"), "ders_sha256": dt.get("sha256")},
            "kitaplar": kitaplar, "eslesme": {k: eslesme[k] for k in sorted(eslesme, key=_kod_sirasi)},
            "eslesmedi": sorted((c["kod"] for c in kalan), key=_kod_sirasi), "denetim": {"kim": None, "tarih": None}}


def _arac(*argv: str) -> str:
    return subprocess.run(list(argv), capture_output=True, text=True, check=True, timeout=300).stdout


def _sha256(yol: Path) -> str:
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def pdf_girdisi(yol: Path, kitap: dict) -> dict:
    """PDF'ten İçindekiler metni (-layout) ve ünitelerin sayfa aralığının düzeni (pdftohtml -xml)."""
    y = str(yol)
    toplam = int(re.search(r"^Pages:\s*(\d+)", _arac("pdfinfo", y), re.M).group(1))
    a, b = kitap["icindekiler_pdf_sayfalari"]
    icindekiler = _arac("pdftotext", "-f", str(a), "-l", str(b), "-layout", y, "-")
    uniteler = icindekiler_ayristir(icindekiler)
    ilk = uniteler[0]["sayfa"] + kitap["sayfa_kaymasi"]
    son = uniteler[-1]["son_sayfa"] + kitap["sayfa_kaymasi"]
    xml = _arac("pdftohtml", "-xml", "-i", "-q", "-f", str(ilk), "-l", str(son), "-stdout", y)
    return {"sha256": _sha256(yol), "toplam_sayfa": toplam, "icindekiler": icindekiler, "xml": xml}


def indir(url: str, dizin: Path, sinir: int = 300 * 1024 * 1024) -> Path:
    import requests
    hedef = dizin / "kitap.pdf"
    toplam = 0
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(hedef, "wb") as f:
            for parca in r.iter_content(1 << 20):
                toplam += len(parca)
                if toplam > sinir:
                    raise YapiHatasi(f"PDF {sinir // 2**20} MB sınırını aşıyor: {url}")
                f.write(parca)
    return hedef


def denetle(anahtar: str, yollar: list[Path], harita_yolu: Path, denetim_yolu: Path = DENETIM_DOSYASI) -> int:
    """K12: PDF'lerin sha256'sını haritadakiyle karşılaştırır, output/kitap_denetimi.json'a yazar (model okur)."""
    try:
        harita = json.loads(Path(harita_yolu).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print(f"harita okunamadı: {harita_yolu}", file=sys.stderr)
        return 1
    kayit = {"denetlendi": date.today().isoformat(), "kitaplar": []}
    degisen = []
    for kitap, yol in zip(harita["kitaplar"], yollar):
        sha = _sha256(yol)
        kayit["kitaplar"].append({"pdf_url": kitap["pdf_url"], "sha256": sha})
        if sha != kitap["sha256"]:
            degisen.append(kitap["baslik"])
    try:
        tum = json.loads(Path(denetim_yolu).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        tum = {}
    if not isinstance(tum, dict):
        tum = {}
    tum[anahtar] = kayit
    atomic_json_dump(tum, str(denetim_yolu))
    print("değişti: " + ", ".join(degisen) if degisen else "kitaplar haritadakiyle aynı")
    return 0


def ozet_metni(harita: dict, ayrinti: bool = False) -> str:
    satirlar = []
    for kitap in harita["kitaplar"]:
        cer = [f for u in kitap["uniteler"] for f in u["cerceveler"]]
        kon = [k for f in cer for k in f["konular"]]
        bas = sum(len(k["basliklar"]) for k in kon) + sum(len(f["basliklar"]) for f in cer)
        satirlar.append(f"{kitap['baslik']}: {len(kitap['uniteler'])} ünite, {len(cer)} çerçeve, {len(kon)} konu, {bas} başlık")
        if not ayrinti:
            continue
        for u in kitap["uniteler"]:
            satirlar.append(f"{u['no']}. Ünite {u['ad']} · s. {u['sayfa']}–{u['son_sayfa']}")
            for f in u["cerceveler"]:
                satirlar.append(f"  {f['no']}. {f['ad']} · s. {f['sayfa']}–{f['son_sayfa']} · çıktılar: {', '.join(f['ciktilar']) or '—'}")
                satirlar += [f"      [{b['tur']}] {b['ad']} · s. {b['sayfa']}" for b in f["basliklar"]]
                for k in f["konular"]:
                    satirlar.append(f"    {k['ad']} · s. {k['sayfa']}–{k['son_sayfa']}")
                    satirlar += [f"      [{b['tur']}] {b['ad']}{' — ' + b['amac'] if b['amac'] else ''} · s. {b['sayfa']}"
                                 for b in k["basliklar"]]
    satirlar.append(f"eşleşmeyen çıktı: {', '.join(harita['eslesmedi']) or 'yok'}")
    return "\n".join(satirlar)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="MEB ders kitabı haritası → src/kitap_haritalari/<anahtar>.json")
    p.add_argument("anahtar", choices=sorted(KITAPLAR))
    p.add_argument("--pdf", action="append", default=[], metavar="N=YOL", help="N. kitap için yerel PDF (1'den)")
    p.add_argument("--cikti", type=Path)
    p.add_argument("--denetle", action="store_true", help="yalnız sha256'yı mevcut haritayla karşılaştır")
    p.add_argument("--denetim-kim", help="elle onayı yapan; denetim alanına bugünün tarihiyle yazılır")
    p.add_argument("--kuru", action="store_true", help="yazma; ayrıntılı ağacı ve denetimi yazdır")
    a = p.parse_args(argv)
    ayar = KITAPLAR[a.anahtar]
    yerel: dict[int, Path] = {}
    for s in a.pdf:
        n, _, yol = s.partition("=")
        if not n.isdigit() or not yol:
            p.error(f"--pdf N=YOL bekleniyor: {s}")
        yerel[int(n) - 1] = Path(yol)
    cikti = a.cikti or CIKTI_DIZINI / f"{a.anahtar}.json"
    with tempfile.TemporaryDirectory(prefix="tedy-kitap-") as gecici:
        yollar = []
        for i, kitap in enumerate(ayar["kitaplar"]):
            if i in yerel:
                yollar.append(yerel[i])
            else:
                d = Path(gecici) / str(i)
                d.mkdir()
                yollar.append(indir(kitap["pdf_url"], d))
        if a.denetle:
            return denetle(a.anahtar, yollar, cikti)
        tablo = tablo_oku()
        if tablo is None:
            print("senaryo tablosu okunamadı", file=sys.stderr)
            return 1
        try:
            harita = harita_kur(a.anahtar, ayar, [pdf_girdisi(y, k) for y, k in zip(yollar, ayar["kitaplar"])], tablo,
                                date.today())
        except YapiHatasi as h:
            print(f"yapı hatası, {cikti} yazılmadı: {h}", file=sys.stderr)
            return 1
    hatalar = yapi_denetimi(harita, tablo["dersler"][ayar["ders"]]["ciktilar"], ayar.get("beklenen_eslesmeyen", ()),
                            ayar.get("basliksiz_konular", ()))
    print(ozet_metni(harita, ayrinti=a.kuru))
    if hatalar:
        print(f"yapı denetimi geçmedi, {cikti} yazılmadı:\n  " + "\n  ".join(hatalar), file=sys.stderr)
        return 1
    if a.denetim_kim:
        harita["denetim"] = {"kim": a.denetim_kim, "tarih": date.today().isoformat()}
    if not a.kuru:
        atomic_json_dump(harita, str(cikti))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
