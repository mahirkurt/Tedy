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
from datetime import date, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from src import claude_api
from src.course_names import normalize_course
from src.json_utils import atomic_json_dump
from src.ocr_katmani import OcrDefteri
from src.sinav_kaynaklari import Aday, on_suzgec
from src.sinav_tarihi import TarihCozumu, katla, okul_yili, tarih_coz

ISTEM_SURUMU = 1
SINAV_VARSAYILAN_MODEL = "claude-haiku-4-5"
AYLIK_TAVAN_USD = float(os.environ.get("TEDY_SINAV_AYLIK_USD", "2"))
ONBELLEK = PurePosixPath("output/sinav_cikarim_onbellegi.json")
DEFTER = PurePosixPath("output/sinav_cikarim_defteri.json")
# A text older than this is never sent to the model for the first time (its exam is most likely
# past, and a backlog would spend the budget on history). A cached reading is used whatever its age.
YENI_CAGRI_SINIR_GUN = 45
CAGRI_EN_AZ_SURE = 8.0
CAGRI_EN_COK_SURE = 30.0
# A longer text is read in overlapping parts, each its own request and cache entry: an exam
# announced past the first 6,000 characters is not cut off.
METIN_SINIRI = 6000
PARCA_ORTUSME = 500
# A billed but unusable answer is not asked again for a week (then once more: a refusal or a
# cut-off answer may not repeat).
HATA_YENIDEN_DENEME_GUN = 7
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
# Part of a date or decimal chain only when a digit touches it, directly or across one of ./: —
# a sentence's full stop, comma, bracket or "Saat:" leaves the time standing.
_SAAT_ONCE = re.compile(r"\d[./:]?$")
_SAAT_SONRA = re.compile(r"^[./:]?\d")
_SOZCUK = re.compile(r"[0-9a-z]{3,}")
_RAKAM = re.compile(r"\d+")
_PARAGRAF = re.compile(r"\n\s*\n")

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
    """The model call failed or answered something unusable. `faturalandi` means a response
    came back (so it was billed): `girdi`/`cikti` carry its tokens and the caller must book
    them and remember the failure; a network/config error carries 0 and is simply retried."""

    def __init__(self, mesaj: str, girdi: int = 0, cikti: int = 0, faturalandi: bool = False):
        super().__init__(mesaj)
        self.girdi, self.cikti, self.faturalandi = girdi, cikti, faturalandi


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
        kullanim = getattr(yanit, "usage", None)
        girdi = int(getattr(kullanim, "input_tokens", 0) or 0)
        cikti = int(getattr(kullanim, "output_tokens", 0) or 0)
        durus = getattr(yanit, "stop_reason", "")
        if durus == "refusal":
            raise CikarimHatasi("model reddetti", girdi, cikti, True)
        if durus == "max_tokens":
            raise CikarimHatasi("model çıktısı kesildi", girdi, cikti, True)
        try:
            veri = json.loads(claude_api.metin(yanit))
        except ValueError as e:
            raise CikarimHatasi("model çıktısı JSON değil", girdi, cikti, True) from e
        satirlar = [s for s in (veri.get("sinavlar") or []) if isinstance(s, dict)] if isinstance(veri, dict) else []
        return OkumaSonucu(satirlar, girdi, cikti)


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
    # A number ("3. yazılı") must be in the source as a number of its own, not inside "2026".
    rakamlar_kaynakta = all(re.search(rf"(?<!\d){r}(?!\d)", kaynak) for r in _RAKAM.findall(baslik))
    if sozcukler and rakamlar_kaynakta and all(s in kaynak or s in katla(ders) for s in sozcukler):
        return baslik
    return f"{ders} {TUR_ADI[tur]}" if ders != "Genel" else TUR_ADI[tur]


def _saat(ham: Any, alinti: str) -> str | None:
    """SS:DD ya da SS.DD; yalnız alıntının içinde bağımsız bir saat olarak geçiyorsa (tarih ya da
    ondalık zincirinin parçası değilse) ve aralıktaysa kabul edilir."""
    ham = str(ham or "").strip()
    m = _SAAT.match(ham)
    if not m or not (int(m.group(1)) < 24 and int(m.group(2)) < 60):
        return None
    for y in re.finditer(re.escape(ham), alinti):
        if _SAAT_ONCE.search(alinti[:y.start()]) or _SAAT_SONRA.match(alinti[y.end():]):
            continue
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    return None


def _sozcukle_gecer(parca: str, butun: str) -> bool:
    """`parca` in `butun` on word boundaries, both folded: "this week" is not in "this weekend",
    "bu hafta" is not in "bu haftaki"."""
    k = katla(parca)
    return bool(k) and re.search(rf"(?<![0-9a-z]){re.escape(k)}(?![0-9a-z])", katla(butun)) is not None


def _ayni_paragraf(metin: str, alinti: str, ifade: str) -> bool:
    """Whether the quote and the date phrase sit in one paragraph (a block between blank lines)."""
    return any(katla(alinti) in katla(p) and _sozcukle_gecer(ifade, p) for p in _PARAGRAF.split(metin))


def uydurma_kapisi(satirlar: list[dict], aday: Aday, bugun: date, yayin: date | None = None) -> list[Bulgu]:
    """`yayin` overrides the candidate's publication date (an earlier, known reading of the same
    text). With no publication date at all only explicit dates are resolved (`goreli=False`)."""
    kaynak = katla(aday.metin)
    yayin = yayin or aday.yayin
    goreli = yayin is not None
    yayin = yayin or bugun
    aralik = okul_yili(bugun)
    sonuc = []
    for s in satirlar:
        if not isinstance(s, dict):
            continue
        alinti = " ".join(str(s.get("alinti") or "").split())
        if not alinti or katla(alinti) not in kaynak or not on_suzgec(alinti):
            continue
        # Tarih ifadesi ancak alıntının içindeyse kullanılır: aynı metnin başka bir cümlesindeki
        # tarih (ör. veli toplantısı) sınava bağlanmaz.
        ifade = str(s.get("tarih_ifadesi") or "").strip()
        alintida = bool(ifade) and _sozcukle_gecer(ifade, alinti)
        cozum = tarih_coz(ifade if alintida else alinti, yayin, aralik, goreli=goreli)
        if (ifade and not alintida and cozum == TarihCozumu(None, None, False)
                and _ayni_paragraf(aday.metin, alinti, ifade)):
            # "This week …. You will also have a short quiz": a week phrase in the quote's own
            # paragraph dates it. One that names a day does not (the day may be another event's).
            disari = tarih_coz(ifade, yayin, aralik, goreli=goreli)
            if disari.gun is None and disari.hafta is not None:
                cozum = disari
        if cozum.gun is None and cozum.hafta is None and cozum.gecersiz:
            continue
        saat = _saat(s.get("saat"), alinti)
        konular: list[str] = []
        ham_konular = s.get("konular")
        for k in ham_konular if isinstance(ham_konular, list) else []:
            k = " ".join(str(k).split())
            if k and katla(k) in kaynak and k not in konular:
                konular.append(k)
        tur = s.get("tur") if s.get("tur") in SINAV_TURLERI else "diger"
        ders = _ders(aday, s.get("ders"), kaynak)
        sonuc.append(Bulgu(ders, tur, _baslik(s.get("baslik"), ders, tur, kaynak), cozum.gun, cozum.hafta,
                           saat, konular, alinti[:300], aday))
    return sonuc


def _ilk_okuma(kayit: dict, aday: Aday) -> date | None:
    """The cache's first reading of this text, when it is earlier than the candidate's publication
    date: the text certainly existed then (a homework's first_seen is written only when the
    dashboard is opened, so it can be late). Never for a candidate with no publication date —
    the first reading may be weeks after the post, and a relative "Cuma günü" would be invented."""
    if aday.yayin is None:
        return None
    try:
        zaman = datetime.fromisoformat(str(kayit.get("zaman") or "")[:19]).date()
    except ValueError:
        return None
    return zaman if zaman < aday.yayin else None


def _parcalar(aday: Aday) -> list[Aday]:
    """The candidate itself, or — past METIN_SINIRI — overlapping parts of it (same course,
    publication date and positions; each its own cache key, since the text differs)."""
    if len(aday.metin) <= METIN_SINIRI:
        return [aday]
    adim = METIN_SINIRI - PARCA_ORTUSME
    parcalar = []
    bas = 0
    while True:
        parcalar.append(Aday(aday.metin[bas:bas + METIN_SINIRI], aday.ders, aday.yayin, aday.tur,
                             list(aday.konumlar)))
        if bas + METIN_SINIRI >= len(aday.metin):
            return parcalar
        bas += adim


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
        self._simdi = simdi
        self.defter = OcrDefteri(self.kok / DEFTER, tavan=tavan, simdi=simdi)
        self._onbellek_yolu = self.kok / ONBELLEK
        try:
            veri = json.loads(self._onbellek_yolu.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            veri = {}
        self._onbellek: dict[str, Any] = veri if isinstance(veri, dict) else {}
        self._tasindi = False

    def _anahtar(self, aday: Aday) -> str:
        # The model is part of the key: another model's reading is not this one's (temizlik A12).
        # The text, not the course: the same post read once, wherever it is pinned.
        return f"{ISTEM_SURUMU}:{self.okuyucu.model}:{aday.metin_anahtari}"

    def _onbellekten(self, parca: Aday, tek_parca: bool) -> dict | None:
        """The cache entry for a part. Before the model joined the key it was
        `ISTEM_SURUMU:<text hash>` and covered the first METIN_SINIRI characters only: a
        single-part candidate reuses such an entry and moves it under the new key."""
        anahtar = self._anahtar(parca)
        kayit = self._onbellek.get(anahtar)
        if kayit is None and tek_parca:
            eski = self._onbellek.get(f"{ISTEM_SURUMU}:{parca.metin_anahtari}")
            if isinstance(eski, dict) and isinstance(eski.get("satirlar"), list):
                self._onbellek[anahtar] = kayit = dict(eski)
                self._tasindi = True
        return kayit

    def _hata_tazelendi(self, kayit: dict) -> bool:
        """A billed failure is retried once it is a week old; an unreadable stamp is retried."""
        try:
            zaman = datetime.fromisoformat(str(kayit.get("zaman") or "")[:19])
        except ValueError:
            return True
        return self._simdi() - zaman >= timedelta(days=HATA_YENIDEN_DENEME_GUN)

    def cikar(self, adaylar: list[Aday], bugun: date, bitis: float,
              yeni_cagri_sinir_gun: int = YENI_CAGRI_SINIR_GUN,
              korunan_konumlar: set[str] | frozenset[str] = frozenset()) -> CikarimSonucu:
        """`korunan_konumlar` (json.dumps(konum, sort_keys=True)): portal positions of exams still
        ahead in the previous sinavlar.json. A candidate there is asked about even past the age
        limit — the teacher edited an early post, and the edit must not drop the exam (A14)."""
        bulgular: list[Bulgu] = []
        incelenen = incelenmedi = atlanan = 0
        sinir = bugun - timedelta(days=yeni_cagri_sinir_gun)
        hatalar: list[str] = []
        degisti = False
        try:
            for aday in adaylar:
                korunan = any(json.dumps(k, sort_keys=True) in korunan_konumlar for k in aday.konumlar)
                eski = aday.yayin is not None and aday.yayin < sinir and not korunan
                satirlar: list = []
                okunan = okunamayan = 0
                onceki_okuma: date | None = None
                parcalar = _parcalar(aday)
                for parca in parcalar:
                    anahtar = self._anahtar(parca)
                    kayit = self._onbellekten(parca, len(parcalar) == 1)
                    gecerli = isinstance(kayit, dict) and isinstance(kayit.get("satirlar"), list)
                    if gecerli:
                        if not kayit.get("hata"):
                            satirlar += kayit["satirlar"]
                            okunan += 1
                            ilk = _ilk_okuma(kayit, aday)
                            if ilk is not None and (onceki_okuma is None or ilk < onceki_okuma):
                                onceki_okuma = ilk
                            continue
                        if not self._hata_tazelendi(kayit):
                            # Billed, unusable answer: not asked again for a week (or a new ISTEM_SURUMU).
                            okunamayan += 1
                            hatalar.append(str(kayit["hata"])[:120])
                            continue
                    if eski and not gecerli:
                        # Too old to ask about for the first time: skipped silently, not "unread"
                        # (nothing was missed that the list could still have shown). A failure whose
                        # week is over was asked before, so it is asked again whatever its age.
                        continue
                    kalan = bitis - self.saat()
                    if kalan < CAGRI_EN_AZ_SURE or not self.defter.izin_var():
                        okunamayan += 1
                        continue
                    try:
                        okuma = self.okuyucu.oku(parca, bugun, zaman_asimi=min(CAGRI_EN_COK_SURE, kalan))
                    except CikarimHatasi as e:
                        okunamayan += 1
                        hatalar.append(str(e)[:120])
                        if e.faturalandi:
                            self.defter.yaz(self.okuyucu.model, e.girdi, e.cikti)
                            self._onbellek[anahtar] = {"satirlar": [], "hata": str(e)[:120],
                                                       "zaman": self._simdi().isoformat(timespec="seconds")}
                            degisti = True
                        continue
                    # Defter OcrDefteri'nin Haiku fiyatıyla hesaplar: TEDY_SINAV_MODEL daha pahalı
                    # bir modele çevrilirse harcama eksik sayılır ve tavan gevşer.
                    self.defter.yaz(self.okuyucu.model, okuma.girdi, okuma.cikti)
                    self._onbellek[anahtar] = {"satirlar": okuma.satirlar,
                                               "zaman": self._simdi().isoformat(timespec="seconds")}
                    degisti = True
                    satirlar += okuma.satirlar
                    okunan += 1
                if okunamayan:
                    incelenmedi += 1
                elif okunan:
                    incelenen += 1
                else:
                    atlanan += 1
                    continue
                # The gate reads the whole text: a part's quote and topics are checked against it,
                # and every finding names the candidate itself (its key, its positions).
                yeni_bulgular = uydurma_kapisi(satirlar, aday, bugun, yayin=onceki_okuma)
                for b in yeni_bulgular:   # overlapping parts may report the same exam twice
                    if b not in bulgular:
                        bulgular.append(b)
        finally:  # ücreti ödenmiş sonuçlar bir istisnada bile kaybolmasın
            if degisti or self._tasindi or not self._onbellek_yolu.exists():
                atomic_json_dump(self._onbellek, str(self._onbellek_yolu))
        return CikarimSonucu(bulgular, len(adaylar) - atlanan, incelenen, incelenmedi,
                             round(self.defter.harcanan(), 6), hatalar)
