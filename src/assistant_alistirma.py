"""Alıştırma şeması, sunucu puanlaması ve öğrenme günlüğü hesapları."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import re
import unicodedata
from zoneinfo import ZoneInfo


SECENEK_SAYISI = 4
TOLERANS = Decimal("0.01")
SON_DENEME = 10
SON_CALISILAN = 5
DUZEYLER = ("baslangic", "gelisiyor", "yeterli")
_TURLER = {"coktan_secmeli", "dogru_yanlis", "kisa_cevap"}
_ZORLUKLAR = {"kolay", "orta", "zor"}
_KAZANIM = re.compile(r"^[A-ZÇĞİÖŞÜ]{2,10}(?:\.\d+)+$")
_SAYI = re.compile(r"[+-]?[0-9]+(?:[.,][0-9]+)?")
_KESIR = re.compile(r"([+-]?[0-9]+)/([+-]?[0-9]+)")


def _metin(deger):
    return isinstance(deger, str) and bool(deger.strip())


def alistirma_hata(govde) -> str | None:
    """Modelin araç gövdesini doğrular; hata metni yalnız modele döner."""
    if not isinstance(govde, dict):
        return "Alıştırma bir nesne olmalıdır."
    for alan in ("baslik", "ders", "konu", "zorluk"):
        if not _metin(govde.get(alan)):
            return f"{alan} boş olmayan bir metin olmalıdır."
    if govde["zorluk"] not in _ZORLUKLAR:
        return "Zorluk kolay, orta ya da zor olmalıdır."
    kod = govde.get("kazanim_kodu")
    if kod is not None and not isinstance(kod, str):
        return "Kazanım kodu metin olmalıdır."
    sorular = govde.get("sorular")
    if not isinstance(sorular, list) or not 3 <= len(sorular) <= 10:
        return "Alıştırma 3–10 soru içermelidir."
    for sira, soru in enumerate(sorular, 1):
        if (not isinstance(soru, dict) or not isinstance(soru.get("tur"), str)
                or soru["tur"] not in _TURLER):
            return f"{sira}. sorunun türü geçersiz."
        for alan in ("soru", "dogru", "aciklama"):
            if not _metin(soru.get(alan)):
                return f"{sira}. soruda {alan} boş olmayan bir metin olmalıdır."
        if soru["tur"] == "coktan_secmeli":
            secenekler = soru.get("secenekler")
            if (not isinstance(secenekler, list)
                    or len(secenekler) != SECENEK_SAYISI
                    or not all(_metin(secenek) for secenek in secenekler)):
                return f"{sira}. soru tam dört dolu metin seçeneği içermelidir."
            if soru["dogru"] not in secenekler:
                return f"{sira}. sorunun doğru cevabı seçeneklerde bulunmalıdır."
        if "kabul_edilenler" in soru:
            kabul = soru["kabul_edilenler"]
            if not isinstance(kabul, list) or not all(_metin(yanit) for yanit in kabul):
                return f"{sira}. sorunun kabul edilen cevapları dolu metinler olmalıdır."
        if "kaynak" in soru and not isinstance(soru["kaynak"], str):
            return f"{sira}. sorunun kaynağı metin olmalıdır."
    return None


def _katla(metin: str) -> str:
    # assistant_core imports the tool registry, so import lazily just as
    # assistant_tools and assistant_kitaplar do.
    from src.assistant_core import turkce_kucult_katla

    return turkce_kucult_katla(metin)


def _norm(metin: str) -> str:
    katli = _katla(metin)
    kalan = []
    for i, karakter in enumerate(katli):
        onceki = katli[i - 1] if i else ""
        sonraki = katli[i + 1] if i + 1 < len(katli) else ""
        korunur = (
            karakter == "/"
            or (karakter == "-" and sonraki.isdigit())
            or (karakter in ",." and onceki.isdigit() and sonraki.isdigit())
        )
        if korunur or not unicodedata.category(karakter).startswith("P"):
            kalan.append(karakter)
    return " ".join("".join(kalan).split())


def _sayi(metin: str) -> Decimal | None:
    if _SAYI.fullmatch(metin):
        return Decimal(metin.replace(",", "."))
    kesir = _KESIR.fullmatch(metin)
    if kesir:
        pay, payda = (Decimal(parca) for parca in kesir.groups())
        if payda:
            return pay / payda
    return None


def cevap_dogru(verilen: str, dogru: str, kabul: list[str] | None) -> bool:
    """Metin eşitliği ya da mutlak 0,01 sayısal toleransla puanlar."""
    yanit = _norm(verilen)
    if not yanit:
        return False
    adaylar = [_norm(aday) for aday in [dogru, *(kabul or [])]]
    if yanit in adaylar:
        return True
    sayi = _sayi(yanit)
    if sayi is None:
        return False
    for aday in adaylar:
        deger = _sayi(aday)
        if deger is not None and abs(sayi - deger) <= TOLERANS:
            return True
    return False


def zayif_konular(satirlar: list[dict]) -> list[dict]:
    """Konu/kazanım başına son on denemenin yüzde 60 altını döndürür."""
    gruplar = defaultdict(list)
    for satir in satirlar:
        gruplar[(satir["konu"], satir.get("kazanim_kodu") or "")].append(satir)
    sonuc = []
    for (konu, kod), grup in gruplar.items():
        son = sorted(grup, key=lambda s: s.get("zaman") or "")[-SON_DENEME:]
        toplam = len(son)
        dogru = sum(bool(satir["dogru"]) for satir in son)
        if toplam >= 3 and dogru * 5 < toplam * 3:
            sonuc.append({"konu": konu, "kazanim_kodu": kod, "dogru": dogru, "toplam": toplam})
    return sorted(sonuc, key=lambda s: (-s["toplam"], s["konu"], s["kazanim_kodu"]))


def calisilan_konular(atiflar: list[dict]) -> list[dict]:
    """Kaynak yer belirtecinden kazanım ve kitap sayfasını tekilleştirir."""
    sonuc = []
    gorulen = set()
    for atif in atiflar:
        locator = atif.get("locator") or {}
        args = locator.get("args") or {}
        kod = str(args.get("kazanim_kodu") or args.get("kod") or "").strip()
        label = str(atif.get("label") or "").strip()
        if not kod and label:
            ilk = label.split()[0]
            if _KAZANIM.fullmatch(ilk):
                kod = ilk
        sayfa = label if locator.get("tool") == "kitap_sayfa" else ""
        anahtar = (kod, sayfa)
        if (kod or sayfa) and anahtar not in gorulen:
            gorulen.add(anahtar)
            sonuc.append({"kazanim_kodu": kod, "sayfa_basligi": sayfa})
    return sonuc


def hafta_araligi(simdi: datetime) -> tuple[datetime, datetime]:
    """İstanbul pazartesi 00:00 sınırlarını UTC olarak verir."""
    yerel = simdi.astimezone(ZoneInfo("Europe/Istanbul"))
    baslangic = yerel.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=yerel.weekday())
    return baslangic.astimezone(timezone.utc), (baslangic + timedelta(days=7)).astimezone(timezone.utc)


def _belirtecler(metin: str) -> set[str]:
    return {parca for parca in re.findall(r"[a-z0-9]+", _katla(metin)) if len(parca) >= 3}


def yanlis_esle(verilen: str, soru: str, katalog: str) -> dict | None:
    """Yanlış cevabı katalog başlığı ve doğrusu ile eşler; eşitlikte ilkini alır."""
    sorgu = _belirtecler(f"{verilen} {soru}")
    en_iyi = None
    en_yuksek = 1
    for bolum in re.split(r"^### ", katalog, flags=re.MULTILINE)[1:]:
        satirlar = bolum.splitlines()
        baslik = satirlar[0].strip()
        dogrusu = ""
        kontrol = ""
        for satir in satirlar[1:]:
            if satir.startswith("**Doğrusu:**"):
                dogrusu = satir.removeprefix("**Doğrusu:**").strip()
            elif satir.startswith("**Kontrol sorusu:**"):
                kontrol = satir.removeprefix("**Kontrol sorusu:**").strip()
        skor = len(sorgu & _belirtecler(f"{baslik} {dogrusu}"))
        if skor > en_yuksek:
            en_yuksek = skor
            en_iyi = {"baslik": baslik, "dogrusu": dogrusu, "kontrol": kontrol}
    return en_iyi
