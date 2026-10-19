"""Akşam çalışma planı (Görev 4): saf plan motoru.

Dosya, saat ve ağ yok: ödev satırları, tahminler, akşam düzeni, "şimdi", takvim olayları ve
günün dokunuş durumu (`gunluk`) girer; bloklar çıkar. Aynı girdi aynı planı verir, aynı ödev
parçası yeniden dizilince aynı kimliği taşır. Depolama, uçlar ve bildirim sonraki görevlerdedir.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable, Literal

from src.aksam_duzeni import dakika
from src.course_names import normalize_course
from src.odev_tahmini import OdevTahmini

BLOK_DK = 20
MOLA_KISA, MOLA_UZUN = 5, 10
TAMPON = 1.25
SON_PARCA_EN_AZ = 5
EK_PARCA_DK = 10
KUCUK_IS_DK = 10          # hafif işler bitişinden sonra yalnız bu kadar kısa tek iş girer
HAZIRLIK_ONCESI_BOS = 15  # hazırlıktan önce en az bu kadar dakika boş kalır
GERI_GUN, ILERI_GUN = 3, 7
DEVAM_ADIMI = "Kaldığın yerden devam et"
ZORLUKLAR = ("zor", "orta", "kolay")
ZORLUK_AGIRLIGI = {"zor": 3, "orta": 2, "kolay": 1}


@dataclass
class Blok:
    id: str
    tur: Literal["calisma", "mola", "yemek", "olay"]
    bas: int
    bit: int
    odev_anahtari: str | None = None
    ders: str | None = None
    baslik: str = ""
    adim: str = ""
    parca: int = 0
    parca_sayisi: int = 1
    tahmin_dk: int = 0
    zorluk: str = "orta"
    durum: Literal["bekliyor", "suruyor", "bitti", "ertelendi"] = "bekliyor"


@dataclass
class Plan:
    gun: str
    bloklar: list[Blok]
    tasinan: list[dict]
    sigmayan: list[dict]
    planda_olmayan: int
    durum: Literal["plansiz", "onizleme", "akis", "bitti", "okulsuz", "kapali"]


# ----------------------------------------------------------------------------- seçim

def _teslim(satir: dict) -> tuple[date, int] | None:
    """Teslim günü ve (varsa) saati, dakika olarak; okunamazsa None."""
    ham = str(satir.get("Ödev Son Teslim Tarihi") or "")
    m = re.match(r"\s*(\d{1,2})\.(\d{1,2})\.(\d{4})(?:\D+(\d{1,2}):(\d{2}))?", ham)
    if not m:
        return None
    try:
        gun = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None
    saat = int(m.group(4)) * 60 + int(m.group(5)) if m.group(4) else 23 * 60 + 59
    return gun, saat


def planlanacak(satirlar: list[dict], bugun: date) -> tuple[list[dict], int]:
    """Açık ve teslimi 3 gün geçmişten 7 gün sonrasına kadar olan ödevler; teslimi okunamayan da girer.

    İkinci değer: açık olup teslimi 3 günden fazla geçmiş ödev sayısı (planda yok ama düşmez).
    Teslimi 7 günden uzak olan ne seçilir ne sayılır."""
    secilen: list[dict] = []
    eski = 0
    for s in satirlar:
        if s.get("teacher_resolved") or s.get("student_marked_done"):
            continue
        t = _teslim(s)
        if t is None:
            secilen.append(s)
            continue
        fark = (t[0] - bugun).days
        if fark < -GERI_GUN:
            eski += 1
        elif fark <= ILERI_GUN:
            secilen.append(s)
    return secilen, eski


# ----------------------------------------------------------------------------- yardımcılar

def _kimlik(*parcalar: Any) -> str:
    return hashlib.sha1("|".join(str(p) for p in parcalar).encode("utf-8")).hexdigest()[:10]


def _dk(deger: Any) -> int | None:
    """Dokunuş kaydındaki zaman: dakika (int), "HH:MM" ya da ISO tarih-saat."""
    if isinstance(deger, bool):
        return None
    if isinstance(deger, (int, float)):
        return int(deger)
    if isinstance(deger, str):
        m = re.search(r"(\d{1,2}):(\d{2})", deger)
        if m:
            return int(m.group(1)) * 60 + int(m.group(2))
    return None


def _kademe(teslim: tuple[date, int] | None, bugun: date) -> int:
    if teslim is None:
        return 0
    fark = (teslim[0] - bugun).days
    return 3 if fark <= 1 else 2 if fark == 2 else 1


def _talimatli(satir: dict) -> bool:
    detay = satir.get("detail")
    return isinstance(detay, dict) and bool(str(detay.get("description") or "").strip())


def _parca_sureleri(toplam: int) -> list[int]:
    """20 dk'lık parçalar; kalan 5 dk'dan kısaysa son parçaya eklenir."""
    toplam = max(toplam, SON_PARCA_EN_AZ)
    tam, kalan = divmod(toplam, BLOK_DK)
    sureler = [BLOK_DK] * tam
    if kalan:
        if kalan >= SON_PARCA_EN_AZ or not sureler:
            sureler.append(kalan)
        else:
            sureler[-1] += kalan
    return sureler


@dataclass
class _Parca:
    id: str
    anahtar: str
    ders: str
    baslik: str
    adim: str
    parca: int
    parca_sayisi: int
    dk: int
    zorluk: str
    sira: int           # ödev sırası (puan sırası)
    teslim_ham: str
    teslim_gunu: date | None


def _bos_baslangic(t: int, d: int, sabit: list[tuple[int, int]]) -> int:
    """t'den başlayan, d dakikalık iş sabit bloklarla (yemek, olay) çakışmıyorsa t, yoksa sonraki boş an."""
    degisti = True
    while degisti:
        degisti = False
        for bas, bit in sabit:
            if t < bit and t + d > bas:
                t = bit
                degisti = True
    return t


# ----------------------------------------------------------------------------- motor

def plan_kur(satirlar: list[dict], tahmin: Callable[[dict], OdevTahmini], duzen: dict,
             simdi: datetime, olaylar: list[tuple[int, int, str]], gunluk: dict,
             okul_gunu: bool, tatil: bool = False, *,
             kalibrasyon: Callable[[str], float] | None = None,
             sinav_dersleri: frozenset[str] = frozenset()) -> Plan:
    gun = simdi.date()
    gun_s = gun.isoformat()
    if gunluk.get("aksam_yok") or tatil:
        return Plan(gun_s, [], [], [], 0, "kapali")
    secilen, eski = planlanacak(satirlar, gun)
    if not okul_gunu:
        return Plan(gun_s, [], [], [], eski, "okulsuz")
    simdi_dk = simdi.hour * 60 + simdi.minute
    hazir, hazirlik = dakika(duzen["odeve_hazir"]), dakika(duzen["hazirlik"])
    if simdi_dk >= hazirlik:
        return Plan(gun_s, [], [], [], eski, "bitti")
    anlik = _anlik_bloklar(gunluk, hazir)
    if not secilen and not anlik:
        return Plan(gun_s, [], [], [], eski, "plansiz")

    # ---- puan sırası
    sinavli = {normalize_course(d) for d in sinav_dersleri}
    ek_parca = gunluk.get("ek_parca") or {}
    kayitlar = []
    for satir in secilen:
        t = tahmin(satir)
        teslim = _teslim(satir)
        ders = normalize_course(str(satir.get("Ders Adı") or "")) or ""
        zorluk = t.zorluk if t.zorluk in ZORLUKLAR else "orta"
        if teslim is None and zorluk == "kolay":
            zorluk = "orta"
        kademe = _kademe(teslim, gun)
        if ders in sinavli:
            kademe += 1
        puan = kademe * ZORLUK_AGIRLIGI[zorluk]
        kayitlar.append((satir, t, teslim, ders, zorluk, puan))
    kayitlar.sort(key=lambda k: (-k[5], not _talimatli(k[0]),
                                 k[2] if k[2] else (date.max, 0), str(k[0].get("homework_key") or "")))

    # ---- ödevleri parçala
    parcalar: list[_Parca] = []
    for sira, (satir, t, teslim, ders, zorluk, _puan) in enumerate(kayitlar):
        anahtar = str(satir.get("homework_key") or "")
        carpan = kalibrasyon(ders) if kalibrasyon else 1.0
        sureler = _parca_sureleri(math.ceil(t.dakika * carpan * TAMPON))
        adimlar = [t.ilk_adim] + [t.parcalar[i] if i < len(t.parcalar) else DEVAM_ADIMI
                                  for i in range(1, len(sureler))]
        try:
            ek = max(0, int(ek_parca.get(anahtar) or 0))
        except (TypeError, ValueError):
            ek = 0
        sureler += [EK_PARCA_DK] * ek
        adimlar += [DEVAM_ADIMI] * ek
        for i, (dk, adim) in enumerate(zip(sureler, adimlar)):
            parcalar.append(_Parca(_kimlik(gun_s, anahtar, i), anahtar, ders, str(satir.get("Ödev Başlığı") or ""),
                                   adim, i, len(sureler), dk, zorluk, sira,
                                   str(satir.get("Ödev Son Teslim Tarihi") or ""), teslim[0] if teslim else None))

    # ---- sabit bloklar
    yemek_bas = dakika(duzen["yemek"])
    yemek_bit = yemek_bas + int(duzen["yemek_dk"])
    sabit = sorted([(yemek_bas, yemek_bit)] + [(int(b), int(e)) for b, e, _ in olaylar])
    bloklar: list[Blok] = [Blok(_kimlik(gun_s, "yemek"), "yemek", yemek_bas, yemek_bit, baslik="Yemek")]
    yatma = dakika(duzen["yatma"])
    for b, e, ad in olaylar:
        if e > hazir and b < yatma:
            bloklar.append(Blok(_kimlik(gun_s, "olay", ad, b), "olay", int(b), int(e), baslik=str(ad)))

    # ---- dokunuşla belirlenmiş bloklar (bitmiş / sürmekte) yerinde kalır
    # Anlık görüntüsü olan kayıt ödev seçilmese de (ör. "Yaptım" sonrası) aynen çıkar (R9);
    # görüntüsüz kayıt yalnız ödevi hâlâ seçiliyse korunur (eski davranış).
    baslangic = max(hazir, simdi_dk)
    bekleyen: list[_Parca] = []
    for p in parcalar:
        if p.id in anlik:
            continue
        kayit = gunluk.get(p.id) if isinstance(gunluk.get(p.id), dict) else {}
        durum = kayit.get("durum")
        if durum in ("bitti", "suruyor"):
            bas = _dk(kayit.get("basla"))
            bas = hazir if bas is None else bas
            bit = _dk(kayit.get("bitti")) if durum == "bitti" else None
            bit = bas + p.dk if bit is None else bit
            anlik[p.id] = _blok_calisma(p, bas, bit, durum)
        else:
            bekleyen.append(p)
    yapilanlar = sorted(anlik.values(), key=lambda b: (b.bas, b.bit))
    bloklar.extend(yapilanlar)
    calisma_sayisi = len(yapilanlar)
    imlec, mola_oncesi = baslangic, 0
    if yapilanlar:
        son = max(yapilanlar, key=lambda b: (b.bit, b.bas))
        sira = yapilanlar.index(son) + 1
        kazanilan = MOLA_UZUN if sira % 2 == 0 else MOLA_KISA
        if son.bit + kazanilan > baslangic:
            imlec, mola_oncesi = son.bit, kazanilan

    # ---- ertelenen: parça ve aynı ödevin sonrakileri kuyruğun sonuna, bir kez
    ertelenen = set(gunluk.get("ertelenen") or [])
    ilk_ertelenen: dict[str, int] = {}
    for p in bekleyen:
        if p.id in ertelenen and p.anahtar not in ilk_ertelenen:
            ilk_ertelenen[p.anahtar] = p.parca
    on = [p for p in bekleyen if p.anahtar not in ilk_ertelenen or p.parca < ilk_ertelenen[p.anahtar]]
    sona = [p for p in bekleyen if p.anahtar in ilk_ertelenen and p.parca >= ilk_ertelenen[p.anahtar]]

    # ---- yerleştirme
    zor_sonu, hafif_sonu = dakika(duzen["zor_is_sonu"]), dakika(duzen["hafif_is_sonu"])
    son_bitis = hazirlik - HAZIRLIK_ONCESI_BOS
    kuyruk_disi: list[_Parca] = []
    dusen: set[str] = set()
    kuyruk_sonu_kullanildi = any(b.tur == "calisma" and b.bas >= hafif_sonu for b in bloklar)
    for p in on + sona:
        if p.anahtar in dusen:
            kuyruk_disi.append(p)
            continue
        ilk = imlec + mola_oncesi
        bas = _bos_baslangic(ilk, p.dk, sabit)
        sinir = zor_sonu if p.zorluk != "kolay" else hafif_sonu
        if bas + p.dk > sinir:
            bas = None
            if p.dk <= KUCUK_IS_DK and not kuyruk_sonu_kullanildi:
                aday = _bos_baslangic(max(ilk, hafif_sonu), p.dk, sabit)
                if aday + p.dk <= son_bitis:
                    bas = aday
                    kuyruk_sonu_kullanildi = True
        if bas is None:
            dusen.add(p.anahtar)
            kuyruk_disi.append(p)
            continue
        if mola_oncesi and bas == ilk and not any(b < ilk and e > imlec for b, e in sabit):
            # sabit blok (yemek, olay) araya girmediyse mola görünür; girdiyse o blok molanın yerini tutar
            bloklar.append(Blok(_kimlik(gun_s, "mola", p.id), "mola", imlec, ilk, baslik="Mola"))
        durum = "ertelendi" if p.id in ertelenen else "bekliyor"
        bloklar.append(_blok_calisma(p, bas, bas + p.dk, durum))
        calisma_sayisi += 1
        imlec = bas + p.dk
        mola_oncesi = MOLA_UZUN if calisma_sayisi % 2 == 0 else MOLA_KISA

    # ---- sığmayanlar: teslimi yarından sonraysa taşınır, değilse sığmaz
    yarin = 1
    tasinan: list[dict] = []
    sigmayan: list[dict] = []
    gorulen: dict[str, dict] = {}
    for p in kuyruk_disi:
        kayit = gorulen.get(p.anahtar)
        if kayit is None:
            kayit = {"odev_anahtari": p.anahtar, "ders": p.ders, "baslik": p.baslik,
                     "teslim": p.teslim_ham, "kalan_dk": 0}
            gorulen[p.anahtar] = kayit
            uzak = p.teslim_gunu is None or (p.teslim_gunu - gun).days > yarin
            (tasinan if uzak else sigmayan).append(kayit)
        kayit["kalan_dk"] += p.dk

    bloklar.sort(key=lambda b: (b.bas, b.bit, b.id))
    return Plan(gun_s, bloklar, tasinan, sigmayan, eski, "akis" if simdi_dk >= hazir else "onizleme")


def _anlik_bloklar(gunluk: dict, hazir: int) -> dict[str, Blok]:
    """gunluk'ta anlık görüntüsü (odev_anahtari + bas/bit...) olan bitti/suruyor kayıtları (R9)."""
    sonuc: dict[str, Blok] = {}
    for kimlik, k in gunluk.items():
        if not isinstance(k, dict) or k.get("durum") not in ("bitti", "suruyor") or not k.get("odev_anahtari"):
            continue
        bas = _dk(k.get("bas"))
        if bas is None:
            bas = _dk(k.get("basla"))
        bas = hazir if bas is None else bas
        dk = int(k.get("tahmin_dk") or 0)
        bit = _dk(k.get("bit"))
        if bit is None:
            bit = _dk(k.get("bitti")) if k["durum"] == "bitti" else None
        bit = bas + dk if bit is None else bit
        zorluk = k.get("zorluk") if k.get("zorluk") in ZORLUKLAR else "orta"
        sonuc[str(kimlik)] = Blok(str(kimlik), "calisma", bas, bit, str(k["odev_anahtari"]), k.get("ders"),
                                  str(k.get("baslik") or ""), str(k.get("adim") or ""), int(k.get("parca") or 0),
                                  int(k.get("parca_sayisi") or 1), dk, zorluk, k["durum"])
    return sonuc


def _blok_calisma(p: _Parca, bas: int, bit: int, durum: str) -> Blok:
    return Blok(p.id, "calisma", bas, bit, p.anahtar, p.ders, p.baslik, p.adim,
                p.parca, p.parca_sayisi, p.dk, p.zorluk, durum)  # type: ignore[arg-type]
