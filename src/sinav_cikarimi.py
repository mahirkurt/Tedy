"""Serbest metinden sınav çıkarımı (spec §5): Claude Haiku yapılandırılmış çıktı,
önbellek, aylık bütçe ve deterministik uydurma kapısı.

Model yalnız ön süzgeçten geçen, önbellekte olmayan metni görür. Kapı modelin
dediğini kaynağa karşı sınar: alıntı ve her konu kaynakta geçmeli; tarih yalnız
kaynakta doğrulanan ifadeden bizim çözümleyicimizle çıkar (model tarihi tek
başına kullanılmaz); saat kaynakta yazmalı; başlığın sözcükleri kaynakta yoksa
başlık türden kurulur."""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from src import claude_api
from src.course_names import normalize_course
from src.json_utils import atomic_json_dump
from src.ocr_katmani import OcrDefteri
from src.sinav_kaynaklari import Aday
from src.sinav_tarihi import katla, okul_yili, tarih_coz

ISTEM_SURUMU = 1
SINAV_VARSAYILAN_MODEL = "claude-haiku-4-5"
AYLIK_TAVAN_USD = float(os.environ.get("TEDY_SINAV_AYLIK_USD", "2"))
ONBELLEK = PurePosixPath("output/sinav_cikarim_onbellegi.json")
DEFTER = PurePosixPath("output/sinav_cikarim_defteri.json")
CAGRI_EN_AZ_SURE = 8.0
CAGRI_EN_COK_SURE = 30.0
METIN_SINIRI = 6000
SINAV_TURLERI = ["yazili", "kisa_sinav", "konu_tarama", "deneme", "ortak_sinav", "diger"]
TUR_ADI = {"yazili": "Yazılı", "kisa_sinav": "Kısa sınav", "konu_tarama": "KTT", "deneme": "Deneme",
           "ortak_sinav": "Ortak sınav", "diger": "Sınav"}
_ALANLAR = ["ders", "tur", "baslik", "tarih_ifadesi", "tarih", "saat", "konular", "alinti"]
CIKARIM_SEMASI = {
    "type": "object", "additionalProperties": False, "required": ["sinavlar"],
    "properties": {"sinavlar": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": _ALANLAR,
        "properties": {
            "ders": {"type": "string"}, "tur": {"type": "string", "enum": SINAV_TURLERI},
            "baslik": {"type": "string"}, "tarih_ifadesi": {"type": "string"},
            "tarih": {"type": "string"}, "saat": {"type": "string"},
            "konular": {"type": "array", "items": {"type": "string"}}, "alinti": {"type": "string"},
        }}}},
}
_SAAT = re.compile(r"^(\d{1,2})[:.](\d{2})$")
_SOZCUK = re.compile(r"[0-9a-z]{3,}")

ISTEM = """Sen bir okul duyurusu okuyucususun. Aşağıdaki metin 7. sınıf öğrencisi Işık'ın okul portalından.
Metinde DUYURULAN, yapılacak ya da yakında yapılacak sınavları çıkar: yazılı, kısa sınav/quiz,
konu tarama testi (KTT), deneme, ortak sınav.

Bugün: {bugun} · Metnin yayın tarihi: {yayin} · Metnin dersi: {ders}

Her sınav için:
- ders: metnin dersi; metin başka bir ders söylüyorsa o ders; ders dışı ortak sınavsa "Genel".
- tur: yazili | kisa_sinav | konu_tarama | deneme | ortak_sinav | diger
- baslik: kısa ad, metindeki sözcüklerle (ör. "Matematik KTT", "Irregular Verbs Quiz").
- tarih_ifadesi: metinde sınavın zamanını söyleyen ifade, metindeki gibi birebir ("15 EKİM PERŞEMBE",
  "Next week", "bu hafta"). Yoksa boş.
- tarih: tarih_ifadesi açık bir gün söylüyorsa YYYY-AA-GG, yoksa boş.
- saat: metinde yazıyorsa SS:DD, yoksa boş.
- konular: metinde sınavın konusu olarak sayılan başlıklar, metindeki sözcüklerle; yoksa boş liste.
- alinti: sınavı duyuran cümle, metinden birebir kopya (en çok 300 karakter).

Kurallar:
- Metinde olmayan bir şeyi yazma, tahmin etme. Emin değilsen alanı boş bırak.
- Geçmiş bir sınavın sonucu, ödev, etkinlik ya da "Quizlet" gibi bir uygulama sınav değildir.
- Sınav yoksa boş liste döndür.

METİN:
<<<
{metin}
>>>"""


class CikarimHatasi(RuntimeError):
    """The model call failed or answered something unusable; nothing is cached."""


@dataclass
class OkumaSonucu:
    satirlar: list[dict]
    girdi: int
    cikti: int


class ClaudeSinavOkuyucu:
    def __init__(self, istemci_fabrikasi: Callable[..., Any] = claude_api.istemci, model: str | None = None):
        self._fabrika = istemci_fabrikasi
        self.model = model or os.environ.get("TEDY_SINAV_MODEL", "").strip() or SINAV_VARSAYILAN_MODEL

    def oku(self, aday: Aday, bugun: date, zaman_asimi: float) -> OkumaSonucu:
        istem = ISTEM.format(bugun=bugun.isoformat(), yayin=aday.yayin.isoformat() if aday.yayin else "bilinmiyor",
                             ders=aday.ders or "belirtilmemiş", metin=aday.metin[:METIN_SINIRI])
        try:
            istemci = self._fabrika(timeout=zaman_asimi, max_retries=0)
            yanit = istemci.messages.create(
                model=self.model, max_tokens=2000,
                messages=[{"role": "user", "content": istem}],
                output_config={"format": {"type": "json_schema", "schema": CIKARIM_SEMASI}})
        except Exception as e:  # anthropic.APIError, ClaudeYapilandirilmamis, timeouts
            raise CikarimHatasi(str(e)[:120] or type(e).__name__) from e
        if getattr(yanit, "stop_reason", "") == "refusal":
            raise CikarimHatasi("model reddetti")
        try:
            veri = json.loads(claude_api.metin(yanit))
        except ValueError as e:
            raise CikarimHatasi("model çıktısı JSON değil") from e
        satirlar = [s for s in (veri.get("sinavlar") or []) if isinstance(s, dict)] if isinstance(veri, dict) else []
        kullanim = getattr(yanit, "usage", None)
        return OkumaSonucu(satirlar, int(getattr(kullanim, "input_tokens", 0) or 0),
                           int(getattr(kullanim, "output_tokens", 0) or 0))


@dataclass
class Bulgu:
    ders: str
    tur: str
    baslik: str
    tarih: date | None
    hafta: date | None
    saat: str | None
    konular: list[str]
    alinti: str
    aday: Aday


def _ders(aday: Aday, model_dersi: Any, kaynak: str) -> str:
    if aday.tur in ("ders_karti", "odev") and aday.ders and aday.ders != "Genel":
        return aday.ders
    aday_ders = normalize_course(str(model_dersi or "")) or ""
    ilk = katla(aday_ders).split()[:1]
    if ilk and re.search(rf"\b{re.escape(ilk[0])}\b", kaynak):
        return aday_ders
    return "Genel"


def _baslik(model_basligi: Any, ders: str, tur: str, kaynak: str) -> str:
    baslik = " ".join(str(model_basligi or "").split())[:80]
    sozcukler = _SOZCUK.findall(katla(baslik))
    if sozcukler and all(s in kaynak or s in katla(ders) for s in sozcukler):
        return baslik
    return f"{ders} {TUR_ADI[tur]}" if ders != "Genel" else TUR_ADI[tur]


def uydurma_kapisi(satirlar: list[dict], aday: Aday, bugun: date) -> list[Bulgu]:
    kaynak = katla(aday.metin)
    yayin = aday.yayin or bugun
    aralik = okul_yili(bugun)
    sonuc = []
    for s in satirlar:
        alinti = " ".join(str(s.get("alinti") or "").split())
        if not alinti or katla(alinti) not in kaynak:
            continue
        ifade = str(s.get("tarih_ifadesi") or "").strip()
        cozum = tarih_coz(ifade if ifade and katla(ifade) in kaynak else alinti, yayin, aralik)
        if cozum.gun is None and cozum.hafta is None and cozum.gecersiz:
            continue
        m = _SAAT.match(str(s.get("saat") or "").strip())
        saat = f"{int(m.group(1)):02d}:{m.group(2)}" if m and str(s.get("saat")).strip() in aday.metin else None
        konular: list[str] = []
        for k in s.get("konular") or []:
            k = " ".join(str(k).split())
            if k and katla(k) in kaynak and k not in konular:
                konular.append(k)
        tur = s.get("tur") if s.get("tur") in SINAV_TURLERI else "diger"
        ders = _ders(aday, s.get("ders"), kaynak)
        sonuc.append(Bulgu(ders, tur, _baslik(s.get("baslik"), ders, tur, kaynak), cozum.gun, cozum.hafta,
                           saat, konular, alinti[:300], aday))
    return sonuc


@dataclass
class CikarimSonucu:
    bulgular: list[Bulgu]
    aday: int
    incelenen: int
    incelenmedi: int
    butce_usd: float
    hatalar: list[str] = field(default_factory=list)


class SinavCikarici:
    def __init__(self, kok: Path, okuyucu: Any, tavan: float = AYLIK_TAVAN_USD,
                 saat: Callable[[], float] = time.monotonic, simdi: Callable[[], datetime] = datetime.now):
        self.kok = Path(kok)
        self.okuyucu = okuyucu
        self.saat = saat
        self.defter = OcrDefteri(self.kok / DEFTER, tavan=tavan, simdi=simdi)
        self._onbellek_yolu = self.kok / ONBELLEK
        try:
            veri = json.loads(self._onbellek_yolu.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            veri = {}
        self._onbellek: dict[str, Any] = veri if isinstance(veri, dict) else {}

    def cikar(self, adaylar: list[Aday], bugun: date, bitis: float) -> CikarimSonucu:
        bulgular: list[Bulgu] = []
        incelenen = incelenmedi = 0
        hatalar: list[str] = []
        degisti = False
        for aday in adaylar:
            anahtar = f"{ISTEM_SURUMU}:{aday.anahtar}"
            kayit = self._onbellek.get(anahtar)
            if isinstance(kayit, dict) and isinstance(kayit.get("satirlar"), list):
                satirlar = kayit["satirlar"]
            else:
                kalan = bitis - self.saat()
                if kalan < CAGRI_EN_AZ_SURE or not self.defter.izin_var():
                    incelenmedi += 1
                    continue
                try:
                    okuma = self.okuyucu.oku(aday, bugun, zaman_asimi=min(CAGRI_EN_COK_SURE, kalan))
                except CikarimHatasi as e:
                    incelenmedi += 1
                    hatalar.append(str(e)[:120])
                    continue
                self.defter.yaz(self.okuyucu.model, okuma.girdi, okuma.cikti)
                satirlar = okuma.satirlar
                self._onbellek[anahtar] = {"satirlar": satirlar, "zaman": datetime.now().isoformat(timespec="seconds")}
                degisti = True
            incelenen += 1
            bulgular.extend(uydurma_kapisi(satirlar, aday, bugun))
        if degisti or not self._onbellek_yolu.exists():
            atomic_json_dump(self._onbellek, str(self._onbellek_yolu))
        return CikarimSonucu(bulgular, len(adaylar), incelenen, incelenmedi,
                             round(self.defter.harcanan(), 6), hatalar)
