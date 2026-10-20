"""Ödev tahmini (akşam çalışma planı, Görev 3): her ödev için bir kez süre, zorluk ve somut ilk adım.

Claude Haiku yapılandırılmış çıktıyla tahmin eder; model yalnız önbellekte olmayan ödev için,
bütçe ve süre içinde çağrılır. Modelin yazdığı ilk adım ve parçalar deterministik bir kapıdan
geçer: ödev metninde olmayan bir sayı (sayfa, soru numarası) geçiyorsa o parça düşer. Model
yoksa, bütçe doluysa ya da çağrı düşerse kural tabanlı bir yedek konuşur. Okurun kendi
düzelttiği süre (`output/odev_tahmin_okur.json`) modelin süresini ezer.

Önbellek `output/odev_tahmin_onbellegi.json`, defter `output/odev_tahmin_defteri.json` (sınav
defterinden ayrı), okur düzeltmesi `output/odev_tahmin_okur.json`. Üçü de flock + atomik yazılır:
iki gunicorn işçisi ve senkron aynı dosyalara yazabilir."""
from __future__ import annotations

import fcntl
import hashlib
import json
import logging
import math
import os
import re
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Iterator, Literal

from src import claude_api
from src.json_utils import atomic_json_dump
from src.ocr_katmani import OcrDefteri

logger = logging.getLogger(__name__)

ISTEM_SURUMU = 1
VARSAYILAN_MODEL = "claude-haiku-4-5"
VARSAYILAN_AYLIK_USD = 2.0


def ortam_usd(ad: str, varsayilan: float = VARSAYILAN_AYLIK_USD) -> float:
    """Ortamdaki aylık tavan (USD): sonlu, negatif olmayan bir sayı; gerisi (yazım hatası, "nan",
    eksi) varsayılandır. İçe aktarmada okunur: bozuk bir değer panoyu ve senkronu düşürmemeli."""
    try:
        deger = float(str(os.environ.get(ad, "")).strip())
    except ValueError:
        return varsayilan
    return deger if math.isfinite(deger) and deger >= 0 else varsayilan


AYLIK_TAVAN_USD = ortam_usd("TEDY_PLAN_AYLIK_USD")
ONBELLEK = "output/odev_tahmin_onbellegi.json"
DEFTER = "output/odev_tahmin_defteri.json"
OKUR = "output/odev_tahmin_okur.json"
YEDEK_ILK_ADIM = "Ödevin yönergesini ve ekini aç"
DAKIKA_EN_AZ, DAKIKA_EN_COK = 5, 120
CAGRI_EN_AZ_SURE = 8.0
CAGRI_EN_COK_SURE = 30.0
METIN_SINIRI = 4000
ZORLUKLAR = ("zor", "orta", "kolay")

TAHMIN_SEMASI = {
    "type": "object", "additionalProperties": False,
    "required": ["dakika", "zorluk", "ilk_adim", "parcalar"],
    "properties": {
        "dakika": {"type": "integer"},
        "zorluk": {"type": "string", "enum": list(ZORLUKLAR)},
        "ilk_adim": {"type": "string"},
        "parcalar": {"type": "array", "items": {"type": "string"}},
    },
}
ISTEM = """Sen 7. sınıfta okuyan, dikkat dağınıklığı yaşayan bir öğrencinin ödev koçusun.
Aşağıdaki ödevi tahmin et.

Bugün: {bugun}
{metin}

Kurallar:
- "dakika": öğrencinin bu ödevi bitirmesi için gereken süre, dakika olarak. Cömert ol, iyimser
  olma: öğrenci yavaş başlar ve sık ara verir. En az 5, en çok 120.
- "zorluk": "kolay", "orta" ya da "zor".
- "ilk_adim": ödeve başlamak için TEK, somut, tek cümlelik ilk adım (en çok 80 karakter).
  Örnek biçim: "Defterini aç ve ilk soruyu oku".
- "parcalar": işi 4 küçük adıma kadar böl (her biri en çok 60 karakter); gerekmiyorsa boş bırak.
- Sayfa, soru numarası ya da başka bir sayıyı YALNIZCA ödev metninde aynen geçiyorsa kullan.
  Metinde olmayan sayı uydurma. Emin değilsen sayısız yaz.
- Yanıtın Türkçe olsun."""


@dataclass
class OdevTahmini:
    dakika: int
    zorluk: Literal["zor", "orta", "kolay"]
    ilk_adim: str
    parcalar: list[str] = field(default_factory=list)
    kaynak: Literal["model", "yedek", "okur"] = "yedek"


@dataclass
class OkumaSonucu:
    tahmin: OdevTahmini
    girdi: int
    cikti: int


class TahminHatasi(Exception):
    """faturalandi: model yanıt verdi (ücret yazıldı) ama kullanılamadı; aynı ödev tekrar sorulmaz."""

    def __init__(self, mesaj: str, girdi: int = 0, cikti: int = 0, faturalandi: bool = False):
        super().__init__(mesaj)
        self.girdi, self.cikti, self.faturalandi = girdi, cikti, faturalandi


# ----------------------------------------------------------------------------- metin ve yedek

def odev_metni(satir: dict) -> str:
    """Ders + başlık + öğretmenin açıklaması + ek adları: modelin gördüğü ve kapının sınadığı metin."""
    detay = satir.get("detail") if isinstance(satir.get("detail"), dict) else {}
    ekler = detay.get("attachments") if isinstance(detay.get("attachments"), list) else []
    ek_adlari = [str(e.get("name")) for e in ekler if isinstance(e, dict) and e.get("name")]
    parcalar = [f"Ders: {satir.get('Ders Adı') or ''}".strip(),
                f"Başlık: {satir.get('Ödev Başlığı') or ''}".strip(),
                f"Açıklama: {detay.get('description') or ''}".strip()]
    if ek_adlari:
        parcalar.append("Ekler: " + ", ".join(ek_adlari))
    return "\n".join(p for p in parcalar if p.split(":", 1)[-1].strip())[:METIN_SINIRI]


def _teslim_gunu(satir: dict) -> date | None:
    ham = str(satir.get("Ödev Son Teslim Tarihi") or "")
    m = re.match(r"\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", ham)
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def kural_tahmini(satir: dict, bugun: date) -> OdevTahmini:
    """Model olmadan: bugün/yarın/2–3 gün içinde teslim 30 dk, daha uzak 20 dk; zorluk hep "orta"."""
    gun = _teslim_gunu(satir)
    kalan = (gun - bugun).days if gun else None
    dakika = 20 if kalan is not None and kalan > 3 else 30
    return OdevTahmini(dakika, "orta", YEDEK_ILK_ADIM, [], "yedek")


def _kisitla(dakika: Any) -> int:
    try:
        return max(DAKIKA_EN_AZ, min(DAKIKA_EN_COK, int(dakika)))
    except (TypeError, ValueError):
        return 30


def uydurma_kapisi(t: OdevTahmini, metin: str) -> OdevTahmini:
    """ilk_adim ve her parçadaki her sayı ödev metninde geçmeli. Geçmeyen parça düşer; geçmeyen
    ilk adım YEDEK_ILK_ADIM olur. Süre ve zorluk sayı değil tahmindir, kapıya girmez."""
    metindeki = set(re.findall(r"\d+", metin))

    def temiz(s: str) -> bool:
        return all(n in metindeki for n in re.findall(r"\d+", s))

    ilk = t.ilk_adim.strip()[:80]  # önce kes, sonra sına: kesilmiş "320" -> "32" geçemez
    if not ilk or not temiz(ilk):
        ilk = YEDEK_ILK_ADIM
    kesik = [p.strip()[:60] for p in t.parcalar if isinstance(p, str) and p.strip()]
    parcalar = [p for p in kesik if temiz(p)][:4]
    return OdevTahmini(_kisitla(t.dakika), t.zorluk if t.zorluk in ZORLUKLAR else "orta",
                       ilk, parcalar, t.kaynak)


# ----------------------------------------------------------------------------- model

class ClaudeTahminOkuyucu:
    def __init__(self, istemci_fabrikasi: Callable[..., Any] = claude_api.istemci, model: str | None = None):
        self._fabrika = istemci_fabrikasi
        self.model = model or os.environ.get("TEDY_PLAN_MODEL", "").strip() or VARSAYILAN_MODEL

    def oku(self, metin: str, bugun: date, zaman_asimi: float) -> OkumaSonucu:
        istem = ISTEM.format(bugun=bugun.isoformat(), metin=metin[:METIN_SINIRI])
        try:
            istemci = self._fabrika(timeout=zaman_asimi, max_retries=0)
            yanit = istemci.messages.create(
                model=self.model, max_tokens=600,
                messages=[{"role": "user", "content": istem}],
                output_config={"format": {"type": "json_schema", "schema": TAHMIN_SEMASI}})
        except Exception as e:  # anthropic.APIError, yapılandırma yok, zaman aşımı
            raise TahminHatasi(str(e)[:120] or type(e).__name__) from e
        kullanim = getattr(yanit, "usage", None)
        girdi = int(getattr(kullanim, "input_tokens", 0) or 0)
        cikti = int(getattr(kullanim, "output_tokens", 0) or 0)
        durus = getattr(yanit, "stop_reason", "")
        if durus == "refusal":
            raise TahminHatasi("model reddetti", girdi, cikti, True)
        if durus == "max_tokens":
            raise TahminHatasi("model çıktısı kesildi", girdi, cikti, True)
        try:
            v = json.loads(claude_api.metin(yanit))
            t = OdevTahmini(int(v["dakika"]), v["zorluk"], str(v["ilk_adim"]),
                            [str(p) for p in (v.get("parcalar") or [])], "model")
        except (ValueError, KeyError, TypeError) as e:
            raise TahminHatasi("model çıktısı geçersiz", girdi, cikti, True) from e
        return OkumaSonucu(t, girdi, cikti)


# ----------------------------------------------------------------------------- depo

def _anahtar_kimligi(satir: dict) -> str:
    """homework_key; yoksa ders + başlık + teslim tarihi (küçük harf, boşluk sadeleştirilmiş)."""
    k = str(satir.get("homework_key") or "").strip()
    if k:
        return k
    ham = "|".join(str(satir.get(a) or "") for a in ("Ders Adı", "Ödev Başlığı", "Ödev Son Teslim Tarihi"))
    return re.sub(r"\s+", " ", ham).strip().lower()


@contextmanager
def _kilitli(yol: Path) -> Iterator[None]:
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol.with_name(yol.name + ".lock"), "a") as kilit:
        fcntl.flock(kilit, fcntl.LOCK_EX)
        yield


def _oku_json(yol: Path) -> dict:
    try:
        v = json.loads(yol.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return v if isinstance(v, dict) else {}


def _oku_siki(yol: Path) -> dict:
    """Yoksa {}; var ama okunamıyor ya da bozuksa istisna: sessizce boş sayıp yeniden faturalandırmayız."""
    try:
        ham = yol.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    v = json.loads(ham)
    if not isinstance(v, dict):
        raise ValueError(f"{yol.name} sözlük değil")
    return v


def _yazilabilir_mi(yol: Path) -> None:
    """Dosyaya DOKUNMADAN yazılabilirliği sına: aynı kilit altında yanına bir sınama dosyası
    yaz ve sil. Başarısızlıkta istisna fırlatır."""
    with _kilitli(yol):
        sinama = yol.with_name(yol.name + ".sinama")
        sinama.write_text("ok", encoding="utf-8")
        sinama.unlink()


def _birlestir_yaz(yol: Path, degisiklik: dict) -> None:
    """Kilit altında diske bak, değişikliği ekle, atomik yaz: başka işçinin satırı ezilmez."""
    with _kilitli(yol):
        veri = _oku_json(yol)
        veri.update(degisiklik)
        atomic_json_dump(veri, str(yol))


class TahminDeposu:
    def __init__(self, kok: Path, okuyucu: Any, tavan: float = AYLIK_TAVAN_USD,
                 simdi: Callable[[], datetime] = None):
        self.kok = Path(kok)
        self.okuyucu = okuyucu
        self._simdi = simdi or datetime.now
        self.defter = OcrDefteri(self.kok / DEFTER, tavan=tavan, simdi=self._simdi)

    def _anahtar(self, satir: dict) -> str:
        ozet = hashlib.sha256(odev_metni(satir).encode("utf-8")).hexdigest()[:12]
        return f"{ISTEM_SURUMU}:{self.okuyucu.model}:{_anahtar_kimligi(satir)}:{ozet}"

    def _onbellek(self) -> dict:
        """isit için sıkı okuma (bozuk/okunamaz -> istisna)."""
        return _oku_siki(self.kok / ONBELLEK)

    def tahmin(self, satir: dict, bugun: date) -> OdevTahmini:
        """Önbellekten (diskten, her çağrıda: işçiler birbirinin yazdığını görür); yoksa yedek. Modeli çağırmaz."""
        kayit = _oku_json(self.kok / ONBELLEK).get(self._anahtar(satir))
        t = None
        if isinstance(kayit, dict) and not kayit.get("yok"):
            try:
                t = OdevTahmini(_kisitla(kayit["dakika"]), kayit["zorluk"], str(kayit["ilk_adim"]),
                                [str(p) for p in kayit.get("parcalar", [])], "model")
            except (KeyError, TypeError):
                t = None
        if t is None:
            t = kural_tahmini(satir, bugun)
        okur = _oku_json(self.kok / OKUR).get(_anahtar_kimligi(satir))
        if isinstance(okur, int) and not isinstance(okur, bool):
            t = OdevTahmini(_kisitla(okur), t.zorluk, t.ilk_adim, t.parcalar, "okur")
        return t

    def okur_suresi_yaz(self, anahtar: str, dakika: int) -> None:
        _birlestir_yaz(self.kok / OKUR, {anahtar: _kisitla(dakika)})

    @staticmethod
    def _hata(ozet: dict, e: BaseException, ne: str = "okuma") -> None:
        """Nedeni günlüğe yaz, ilkini özete koy (kısa; anahtar/gövde yok)."""
        neden = f"{ne}: {type(e).__name__}: {str(e)[:100]}"
        logger.warning("ödev tahmini %s", neden)
        ozet["hata"] += 1
        if not ozet.get("son_hata"):
            ozet["son_hata"] = neden

    def isit(self, satirlar: list[dict], bugun: date, bitis: float) -> dict:
        """Önbellekte olmayan ödevler için modeli çağırır; `bitis` time.monotonic() cinsinden son an.
        Bütçe ya da süre bitince durur, hata ödevi yuttur (yedek kalır)."""
        ozet = {"cagri": 0, "onbellekte": 0, "hata": 0, "durdu": None, "son_hata": None}
        try:
            onbellek = self._onbellek()
        except Exception as w:
            self._hata(ozet, w, "okuma")
            ozet["durdu"] = "okuma"
            return ozet
        sinandi = False
        for satir in satirlar:
            anahtar = self._anahtar(satir)
            if anahtar in onbellek:
                ozet["onbellekte"] += 1
                continue
            metin = odev_metni(satir)
            if not metin.strip():
                continue
            kalan = bitis - time.monotonic()
            if kalan < CAGRI_EN_AZ_SURE:
                ozet["durdu"] = "sure"
                break
            try:
                izin = self.defter.izin_var()
            except Exception as w:
                self._hata(ozet, w, "defter")
                ozet["durdu"] = "defter"
                break
            if not izin:
                ozet["durdu"] = "butce"
                break
            if not sinandi:
                # Ücretli çağrıdan önce yazılabilirlik: yazılamayan çıktı her senkronda aynı ödevi
                # yeniden faturalandırırdı. Dosyalara dokunulmaz (yalnız sınama dosyası).
                try:
                    _yazilabilir_mi(self.kok / ONBELLEK)
                    _yazilabilir_mi(self.kok / DEFTER)
                except Exception as w:
                    self._hata(ozet, w, "yazma")
                    ozet["durdu"] = "yazma"
                    break
                sinandi = True
            try:
                sonuc = self.okuyucu.oku(metin, bugun, min(kalan, CAGRI_EN_COK_SURE))
            except TahminHatasi as e:
                self._hata(ozet, e)
                if e.faturalandi:
                    try:
                        self.defter.yaz(self.okuyucu.model, e.girdi, e.cikti)
                        _birlestir_yaz(self.kok / ONBELLEK, {anahtar: {"yok": True, "neden": str(e)[:80]}})
                    except Exception as w:
                        self._hata(ozet, w, "yazma")
                        ozet["durdu"] = "yazma"
                        break
                continue
            except Exception as e:
                self._hata(ozet, e)
                continue
            ozet["cagri"] += 1
            # Ücret ödendi: sonucu kaybetme. Yazma düşerse döngü temiz durur, isit çağırana fırlatmaz.
            try:
                self.defter.yaz(self.okuyucu.model, sonuc.girdi, sonuc.cikti)
                temiz = uydurma_kapisi(sonuc.tahmin, metin)
                kayit = asdict(temiz)
                kayit.pop("kaynak", None)
                kayit["zaman"] = self._simdi().isoformat(timespec="seconds")
                _birlestir_yaz(self.kok / ONBELLEK, {anahtar: kayit})
            except Exception as w:
                self._hata(ozet, w, "yazma")
                ozet["durdu"] = "yazma"
                break
        return ozet
