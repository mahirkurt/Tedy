"""Akşam çalışma planı (Görev 4–5): saf plan motoru ve (dosyanın sonunda) günün durum/kayıt deposu.

Dosya, saat ve ağ yok: ödev satırları, tahminler, akşam düzeni, "şimdi", takvim olayları ve
günün dokunuş durumu (`gunluk`) girer; bloklar çıkar. Aynı girdi aynı planı verir, aynı ödev
parçası yeniden dizilince aynı kimliği taşır. Depo (`PlanDeposu`, `CalismaKayitlari`) en altta; uçlar `dashboard_api`'de, bildirim sonraki görevdedir.
"""
from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import math
import os
import re
import statistics
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterator, Literal

from src.aksam_duzeni import dakika
from src.course_names import normalize_course
from src.json_utils import atomic_json_dump
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


def _tam(deger: Any) -> int | None:
    """Yalnız sonlu tam sayı: int, tam değerli float ya da rakamdan oluşan metin; gerisi None."""
    if isinstance(deger, bool):
        return None
    if isinstance(deger, int):
        return deger
    if isinstance(deger, float):
        return int(deger) if math.isfinite(deger) and deger == int(deger) else None
    if isinstance(deger, str) and re.fullmatch(r"\s*-?\d{1,9}\s*", deger):
        return int(deger)
    return None


def _dk(deger: Any) -> int | None:
    """Dokunuş kaydındaki zaman: dakika (sonlu sayı), "HH:MM" ya da ISO tarih-saat; okunamazsa None."""
    if isinstance(deger, str):
        m = re.search(r"(\d{1,2}):(\d{2})", deger)
        if m:
            return int(m.group(1)) * 60 + int(m.group(2))
    if isinstance(deger, float) and math.isfinite(deger):
        return int(deger)
    return _tam(deger)


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
    ek_parca = gunluk.get("ek_parca") if isinstance(gunluk.get("ek_parca"), dict) else {}
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
            ek = max(0, min(20, _tam(ek_parca.get(anahtar)) or 0))
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
            bit = bas + p.dk if bit is None or bit < bas else bit
            anlik[p.id] = _blok_calisma(p, bas, bit, durum)
        else:
            bekleyen.append(p)
    yapilanlar = sorted(anlik.values(), key=lambda b: (b.bas, b.bit))
    bloklar.extend(yapilanlar)
    calisma_sayisi = len(yapilanlar)
    imlec, mola_oncesi = baslangic, 0
    if yapilanlar:
        son = yapilanlar[-1]       # zamana göre sonuncu
        kazanilan = MOLA_UZUN if len(yapilanlar) % 2 == 0 else MOLA_KISA
        if son.bit + kazanilan > baslangic:
            imlec, mola_oncesi = son.bit, kazanilan

    # ---- ertelenen: parça ve aynı ödevin sonrakileri kuyruğun sonuna, bir kez
    ham_ertelenen = gunluk.get("ertelenen")
    ertelenen = {e for e in ham_ertelenen if isinstance(e, str)} if isinstance(ham_ertelenen, (list, tuple, set)) else set()
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
    """gunluk'ta anlık görüntüsü (odev_anahtari + bas/bit...) olan bitti/suruyor kayıtları (R9).

    Paylaşılan, elle düzenlenebilir durum: kullanılamayan görüntü (okunamayan bas/bit, bit < bas)
    atlanır; plan_kur bu yüzden asla düşmez."""
    sonuc: dict[str, Blok] = {}
    for kimlik, k in gunluk.items():
        if not isinstance(k, dict) or k.get("durum") not in ("bitti", "suruyor") or not k.get("odev_anahtari"):
            continue
        bas = _dk(k.get("bas"))
        bit = _dk(k.get("bit"))
        if bas is None or bit is None or bit < bas:
            continue
        dk = _tam(k.get("tahmin_dk"))
        dk = dk if dk is not None and dk >= 0 else 0
        parca = _tam(k.get("parca"))
        parca = parca if parca is not None and parca >= 0 else 0
        sayi = _tam(k.get("parca_sayisi"))
        sayi = sayi if sayi is not None and sayi >= 1 else 1
        zorluk = k.get("zorluk") if k.get("zorluk") in ZORLUKLAR else "orta"
        ders = k.get("ders")
        sonuc[str(kimlik)] = Blok(str(kimlik), "calisma", bas, bit, str(k["odev_anahtari"]),
                                  ders if isinstance(ders, str) else None, str(k.get("baslik") or ""),
                                  str(k.get("adim") or ""), parca, sayi, dk, zorluk, k["durum"])
    return sonuc


def _blok_calisma(p: _Parca, bas: int, bit: int, durum: str) -> Blok:
    return Blok(p.id, "calisma", bas, bit, p.anahtar, p.ders, p.baslik, p.adim,
                p.parca, p.parca_sayisi, p.dk, p.zorluk, durum)  # type: ignore[arg-type]


# ----------------------------------------------------------------------------- depo (Görev 5)
# Günün dokunuş durumu (`PlanDeposu`) ve çalışma kayıtları (`CalismaKayitlari`): ikisi de paylaşılan,
# `fcntl.flock` altında yazılan dosyalardır (gunicorn iki işçi çalıştırır). Motor bunları bilmez;
# uçlar (`dashboard_api`) okur, yazar ve motora `gunluk` olarak verir.

PLAN_DOSYASI = "output/aksam_plani.json"
KAYIT_DOSYASI = "output/calisma_kayitlari.jsonl"
GUN_SAKLAMA = 14
KALIBRASYON_SON, KALIBRASYON_EN_AZ = 10, 3
KALIBRASYON_ARALIK = (0.5, 2.0)

_BIRIMLER = {1: "bir", 2: "iki", 3: "üç", 4: "dört", 5: "beş", 6: "altı", 7: "yedi", 8: "sekiz", 9: "dokuz"}
_ONLAR = {10: "on", 20: "yirmi", 30: "otuz", 40: "kırk", 50: "elli"}
_ON_UNLU = "eiöü"
_UNLULER = "aeıioöuü"


def saat_hali(saat: str) -> str:
    """``"17:15"`` → ``"17:15'e"``: yönelme eki, sayının okunuşundaki son sözcüğe göre.

    Okunuşta son sözcük dakikadır ("on yedi on beş" → beş → "beşe"); dakika 00 ise saattir
    ("on yedi" → "on yediye" → "17:00'ye"). Son ünlü ince (e, i, ö, ü) ise "e", kalın ise "a";
    sözcük ünlüyle bitiyorsa kaynaştırma "y" gelir. Kod tabanında başka biçim yok; burada tek yerde."""
    s, d = (int(x) for x in saat.split(":"))
    n = d if d else s
    if n == 0:
        kelime = "sıfır"
    elif n % 10:
        kelime = _BIRIMLER[n % 10]
    else:
        kelime = _ONLAR[n]
    son_unlu = next(h for h in reversed(kelime) if h in _UNLULER)
    ek = "e" if son_unlu in _ON_UNLU else "a"
    return f"{saat}'{'y' if kelime[-1] in _UNLULER else ''}{ek}"


def anlik_goruntu(blok: Blok) -> dict | None:
    """Bloğun `gunluk` kaydına yazılacak anlık görüntüsü (R9): ödev "Yaptım" olsa ya da listeden
    düşse de motor bloğu aynen çıkarsın diye. 0 <= bas <= bit <= 1440 değilse None: motor sınır
    dışı görüntüyü zaten atlar, hiç yazmamak onu en baştan önler."""
    bas, bit = blok.bas, blok.bit
    if not (isinstance(bas, int) and isinstance(bit, int)) or isinstance(bas, bool) or isinstance(bit, bool):
        return None
    if not 0 <= bas <= bit <= 1440:
        return None
    return {"odev_anahtari": blok.odev_anahtari, "ders": blok.ders, "baslik": blok.baslik,
            "parca": blok.parca, "parca_sayisi": blok.parca_sayisi, "tahmin_dk": blok.tahmin_dk,
            "zorluk": blok.zorluk, "adim": blok.adim, "bas": bas, "bit": bit}


@contextmanager
def _kilit(yol: Path) -> Iterator[None]:
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol.with_name(yol.name + ".lock"), "a") as kilit:
        fcntl.flock(kilit, fcntl.LOCK_EX)
        yield


class PlanDeposu:
    """`output/aksam_plani.json`: gün (YYYY-MM-DD) → o günün dokunuş durumu (`plan_kur`'un `gunluk`'u).

    14 günden eski günler her yazımda budanır. Bozuk dosya yazımda kenara alınır (`.bozuk-<damga>`),
    okumada yok sayılır: plan yeniden kurulabilir durumdur, bozuk bir dosya akşamı kilitlemez."""

    def __init__(self, kok: Path):
        self.yol = Path(kok) / PLAN_DOSYASI

    def _oku(self) -> dict:
        try:
            ham = self.yol.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {}
        veri = json.loads(ham)
        if not isinstance(veri, dict):
            raise ValueError("aksam_plani.json sözlük değil")
        return veri

    def gunluk(self, gun: str) -> dict:
        try:
            g = self._oku().get(gun)
        except (OSError, ValueError):
            return {}
        return copy.deepcopy(g) if isinstance(g, dict) else {}

    def degistir(self, gun: str, fn: Callable[[dict], None]) -> dict:
        """Kilit altında yeniden oku → `fn` günü yerinde değiştirir → atomik yaz; yeni günü döner."""
        with _kilit(self.yol):
            try:
                veri = self._oku()
            except (OSError, ValueError):
                self._kenara_al()
                veri = {}
            g = veri.get(gun)
            g = g if isinstance(g, dict) else {}
            fn(g)
            veri[gun] = g
            try:
                sinir = date.fromisoformat(gun) - timedelta(days=GUN_SAKLAMA)
            except ValueError:
                sinir = None
            if sinir is not None:
                for k in list(veri):
                    try:
                        if date.fromisoformat(k) < sinir:
                            del veri[k]
                    except ValueError:
                        pass
            atomic_json_dump(veri, str(self.yol))
            return copy.deepcopy(g)

    def _kenara_al(self) -> None:
        try:
            self.yol.rename(self.yol.with_name(f"{self.yol.name}.bozuk-{datetime.now():%Y%m%d%H%M%S}"))
        except OSError:
            pass


class CalismaKayitlari:
    """`output/calisma_kayitlari.jsonl`: her dokunuş (başla, bitti, ertelendi) bir satır, eklemeli.

    Kalibrasyon yalnız `bitti` satırlarından: ders başına son 10 kaydın gerçek/tahmin oranının
    medyanı, [0,5; 2,0]'ya kıstırılır; 3'ten az kayıtta 1,0 (öğrenme başlamadı)."""

    def __init__(self, kok: Path):
        self.yol = Path(kok) / KAYIT_DOSYASI

    def ekle(self, kayit: dict) -> None:
        satir = json.dumps(kayit, ensure_ascii=False) + "\n"
        with _kilit(self.yol):
            with open(self.yol, "a", encoding="utf-8") as f:
                f.write(satir)
                f.flush()
                os.fsync(f.fileno())

    def kalibrasyon(self, ders: str) -> float:
        oranlar: list[float] = []
        try:
            with open(self.yol, "r", encoding="utf-8") as f:
                for satir in f:
                    try:
                        k = json.loads(satir)
                        if not isinstance(k, dict) or k.get("durum") != "bitti" or k.get("ders") != ders:
                            continue
                        tahmin = _tam(k.get("tahmin_dk"))
                        gercek = (datetime.fromisoformat(k["bitti"]) - datetime.fromisoformat(k["basla"])
                                  ).total_seconds() / 60
                    except (ValueError, KeyError, TypeError):
                        continue
                    if tahmin and tahmin > 0 and gercek >= 0:
                        oranlar.append(gercek / tahmin)
        except OSError:
            return 1.0
        oranlar = oranlar[-KALIBRASYON_SON:]
        if len(oranlar) < KALIBRASYON_EN_AZ:
            return 1.0
        alt, ust = KALIBRASYON_ARALIK
        return min(ust, max(alt, statistics.median(oranlar)))
