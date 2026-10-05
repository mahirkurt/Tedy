"""Asistan indekslerinin bge-m3 vektörleri ve karma (BM25 + vektör) sıralaması.

Ölçüm 2026-10-05 (85 soru, bilinen parça, ilk 8): BM25 dolaylı soruda 0.53, karma 0.69. Öğrenci
indeksinde vektör ağırlıklı karma 0.49 -> 0.82; aile indeksinin %94'ü İngilizce kitap olduğundan
Türkçe soruya BM25 orada 0.00 buluyordu. Aile indeksinin küçük Türkçe notlarında ise BM25 güçlü, bu
yüzden orada iki sıralama eşit ağırlıkta birleşir.

- Toplu gömme mbp ve Pi'de paralel yapılır (bge-m3 üç düğümde aynı vektörü verir, kosinüs ≥ 0.99999);
  eşitleme içinde süreyle sınırlıdır, eksik kalan bir sonraki turda gömülür.
- Soru HP'nin yerel Ollama'sında gömülür (medyan 64 ms), düşerse mbp, sonra Pi. Hepsi düşerse arama
  BM25'e döner — vektör hiçbir zaman cevabın önünde engel değildir.
- Vektör metnin özetiyle anahtarlanır, chunk_id ile değil: portal eşitlemesi metin aynıyken kimliği
  değiştirir.
- 60'tan az harf/rakam taşıyan parça (boş noktalı şablon, "Chapter 3 Research 75" üst bilgisi)
  gömülmez; böyle bir parçanın vektörü her soruya yakın düşüp gerçek isabetleri iterdi.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import queue
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import requests

from src.json_utils import atomic_json_dump

logger = logging.getLogger(__name__)

VEKTOR_DOSYASI = "vektorler.npy"
ANAHTAR_DOSYASI = "vektorler.json"
GOMME_MAX_KARAKTER = 2000
MIN_ANLAMLI = 60
TOPLU_PARTI = 8
DUGUM_HATA_SINIRI = 3
RRF_K = 60
ADAY_SAYISI = 100

Gom = Callable[[str, str, list[str], "float | None"], list[list[float]]]


@dataclass(frozen=True)
class VektorAyari:
    acik: bool
    model: str
    sorgu_adresleri: tuple[str, ...]
    toplu_adresleri: tuple[str, ...]
    agirlik_ogrenci: float
    agirlik_aile: float
    sure: float  # eşitleme başına toplu gömme süresi (sn); 0 = süresiz


def _adresler(ad: str, varsayilan: str) -> tuple[str, ...]:
    ham = os.environ.get(ad, "").strip() or varsayilan
    return tuple(a.strip().rstrip("/") for a in ham.split(",") if a.strip())


def _sayi(ad: str, varsayilan: float) -> float:
    try:
        return max(0.0, float(os.environ.get(ad, "").strip() or varsayilan))
    except ValueError:
        return varsayilan


def ayarlar() -> VektorAyari:
    """Kapalı varsayılan: yalnız ASSISTANT_ENABLE_EMBEDDINGS=1 açar (canlı .env'de açık), böylece
    testler ve el ile kurulan runtime'lar ağa hiç çıkmaz."""
    return VektorAyari(
        acik=os.environ.get("ASSISTANT_ENABLE_EMBEDDINGS", "").strip() == "1",
        model=os.environ.get("ASSISTANT_EMBED_MODEL", "").strip() or "bge-m3",
        sorgu_adresleri=_adresler("ASSISTANT_EMBED_SORGU_URLS",
                                  "http://127.0.0.1:11434,http://mbp.lan:11434,http://pi.lan:11434"),
        toplu_adresleri=_adresler("ASSISTANT_EMBED_TOPLU_URLS", "http://mbp.lan:11434,http://pi.lan:11434"),
        agirlik_ogrenci=_sayi("ASSISTANT_VEKTOR_AGIRLIGI", 3.0),
        agirlik_aile=_sayi("ASSISTANT_AILE_VEKTOR_AGIRLIGI", 1.0),
        # Inside run_sync the reindex shares the 150 s left after attachments with OCR (45 s);
        # ~10 s reindex + 45 s OCR + 60 s embedding fits. The first fill runs by hand, unbounded.
        sure=_sayi("ASSISTANT_GOMME_SURE", 60.0),
    )


def anlamli_mi(metin: str) -> bool:
    return len(re.sub(r"[\W_]", "", metin or "")) >= MIN_ANLAMLI


def metin_anahtari(metin: str) -> str:
    return hashlib.sha256((metin or "")[:GOMME_MAX_KARAKTER].encode("utf-8")).hexdigest()[:24]


def ollama_gom(adres: str, model: str, metinler: list[str], zaman_asimi: float | None) -> list[list[float]]:
    """keep_alive -1 keeps the model resident on that node (mbp and Pi already pin bge-m3; on HP a
    cold load took 4.4 s against a 40 ms warm call, measured 2026-10-05)."""
    resp = requests.post(f"{adres}/api/embed", json={"model": model, "input": metinler, "keep_alive": -1},
                         timeout=zaman_asimi)
    resp.raise_for_status()
    vektorler = resp.json().get("embeddings")
    if not isinstance(vektorler, list) or len(vektorler) != len(metinler):
        raise ValueError("embeddings adedi")
    return vektorler


_ollama_gom_gercek = ollama_gom

# A failed first query node is warmed in the background with an unbounded request, at most once a
# minute per node: the question cannot wait out a cold load, and a request cut at the timeout may
# never let the load finish — live 2026-10-05 every search fell through to mbp (median 2.3 s).
ISITMA_ARALIGI = 60.0
_son_isitma: dict[str, float] = {}
_isitma_kilidi = threading.Lock()
_isitma_iplikleri: list[threading.Thread] = []


def _isit(adres: str, model: str, gom: Gom) -> None:
    simdi = time.monotonic()
    with _isitma_kilidi:
        if simdi - _son_isitma.get(adres, float("-inf")) < ISITMA_ARALIGI:
            return
        _son_isitma[adres] = simdi

    def calis() -> None:
        try:
            gom(adres, model, ["ısıtma"], None)
        except Exception as exc:  # noqa: BLE001
            logger.warning("gömme düğümü ısıtılamadı %s: %s", adres, type(exc).__name__)

    iplik = threading.Thread(target=calis, daemon=True)
    iplik.start()
    _isitma_iplikleri.append(iplik)


def _isitma_bekle(sure: float = 5.0) -> None:
    """For tests: wait for the background warm-ups started so far."""
    for iplik in list(_isitma_iplikleri):
        iplik.join(sure)
    _isitma_iplikleri.clear()


def _normalize(matris: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(matris, axis=1, keepdims=True)
    norm[norm == 0] = 1.0
    return (matris / norm).astype(np.float32)


class VektorDeposu:
    """index_dir/vektorler.npy (N×d, birim uzunluk) + vektorler.json ({model, anahtarlar})."""

    def __init__(self, index_dir: Path) -> None:
        self.index_dir = Path(index_dir)
        self.vektor_yolu = self.index_dir / VEKTOR_DOSYASI
        self.anahtar_yolu = self.index_dir / ANAHTAR_DOSYASI

    def degisim_zamani(self) -> float:
        return self.anahtar_yolu.stat().st_mtime if self.anahtar_yolu.exists() else 0.0

    def yukle(self) -> tuple[list[str], np.ndarray | None, str | None]:
        try:
            meta = json.loads(self.anahtar_yolu.read_text(encoding="utf-8"))
            matris = np.load(self.vektor_yolu)
        except (OSError, ValueError):
            return [], None, None
        anahtarlar = meta.get("anahtarlar") if isinstance(meta, dict) else None
        if not isinstance(anahtarlar, list) or matris.ndim != 2 or len(anahtarlar) != matris.shape[0]:
            return [], None, None
        return [str(a) for a in anahtarlar], matris.astype(np.float32), meta.get("model")

    def kaydet(self, anahtarlar: list[str], matris: np.ndarray, model: str) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        gecici = self.vektor_yolu.with_name(VEKTOR_DOSYASI + ".tmp.npy")
        np.save(gecici, matris.astype(np.float32))
        os.replace(gecici, self.vektor_yolu)
        # The key file is written last and is what readers' mtime checks watch.
        atomic_json_dump({"model": model, "boyut": int(matris.shape[1]) if matris.size else 0,
                          "anahtarlar": anahtarlar}, str(self.anahtar_yolu))


def doldur(parcalar: list[dict[str, Any]], depo: VektorDeposu, ayar: VektorAyari, *,
           gom: Gom | None = None, saat: Callable[[], float] = time.monotonic) -> dict[str, Any]:
    """Anlamlı parçaların eksik vektörlerini toplu düğümlerde paralel gömer, artık var olmayan
    metinlerin vektörlerini atar. `ayar.sure` saniye sonra yeni parti başlatılmaz (0 = süresiz);
    yarım kalan bir sonraki çağrıda devam eder. Hiçbir düğüm yanıt vermese de mevcut depo korunur."""
    istenen: dict[str, str] = {}
    for p in parcalar:
        metin = str(p.get("text", ""))
        if anlamli_mi(metin):
            istenen.setdefault(metin_anahtari(metin), metin[:GOMME_MAX_KARAKTER])
    gom = gom or ollama_gom  # resolved per call, so tests can replace the module attribute
    eski_anahtarlar, eski_matris, eski_model = depo.yukle()
    mevcut: dict[str, np.ndarray] = {}
    if eski_matris is not None and eski_model == ayar.model:
        mevcut = {a: eski_matris[i] for i, a in enumerate(eski_anahtarlar) if a in istenen}
    eksik = [(a, m) for a, m in istenen.items() if a not in mevcut]

    yeni: dict[str, np.ndarray] = {}
    hatalar: dict[str, int] = {}
    if eksik:
        son_an = None if ayar.sure <= 0 else saat() + ayar.sure
        kuyruk: "queue.Queue[list[tuple[str, str]]]" = queue.Queue()
        for i in range(0, len(eksik), TOPLU_PARTI):
            kuyruk.put(eksik[i:i + TOPLU_PARTI])
        kilit = threading.Lock()

        def isci(adres: str) -> None:
            while son_an is None or saat() < son_an:
                try:
                    parti = kuyruk.get_nowait()
                except queue.Empty:
                    return
                try:
                    vektorler = gom(adres, ayar.model, [m for _, m in parti], 120.0)
                    matris = _normalize(np.asarray(vektorler, dtype=np.float32))
                except Exception as exc:  # noqa: BLE001 — a node may be down; others carry on
                    kuyruk.put(parti)
                    with kilit:
                        hatalar[adres] = hatalar.get(adres, 0) + 1
                        bitti = hatalar[adres] >= DUGUM_HATA_SINIRI
                    logger.warning("gömme düğümü %s başarısız: %s", adres, type(exc).__name__)
                    if bitti:
                        return
                    continue
                with kilit:
                    for (anahtar, _), satir in zip(parti, matris):
                        yeni[anahtar] = satir

        iscilar = [threading.Thread(target=isci, args=(a,), daemon=True) for a in ayar.toplu_adresleri]
        for t in iscilar:
            t.start()
        for t in iscilar:
            t.join()

    tum = {**mevcut, **yeni}
    sira = [a for a in istenen if a in tum]
    degisti = bool(yeni) or len(mevcut) != len(eski_anahtarlar) or eski_model != ayar.model
    if degisti and sira:
        depo.kaydet(sira, np.vstack([tum[a] for a in sira]), ayar.model)
    return {"model": ayar.model, "toplam": len(istenen), "vektorlu": len(sira), "yeni": len(yeni),
            "eksik": len(istenen) - len(sira), "hatalar": hatalar}


def sorgu_vektoru(metin: str, ayar: VektorAyari, *, gom: Gom | None = None) -> np.ndarray | None:
    """Soru vektörü; adresler sırayla denenir (ilki yerel, kısa süre). Hepsi düşerse None —
    çağıran BM25 ile devam eder."""
    if not ayar.acik or not (metin or "").strip():
        return None
    gom = gom or ollama_gom
    for i, adres in enumerate(ayar.sorgu_adresleri):
        try:
            v = np.asarray(gom(adres, ayar.model, [metin[:GOMME_MAX_KARAKTER]], 2.0 if i == 0 else 3.0)[0],
                           dtype=np.float32)
        except Exception as exc:  # noqa: BLE001
            logger.warning("soru gömme %s başarısız: %s", adres, type(exc).__name__)
            if i == 0 and len(ayar.sorgu_adresleri) > 1:
                _isit(adres, ayar.model, gom)
            continue
        norm = float(np.linalg.norm(v))
        if norm > 0:
            return v / norm
    return None


def rrf_puanli(siralamalar: list[tuple[list[int], float]], k: int = RRF_K) -> list[tuple[int, float]]:
    """Ağırlıklı Reciprocal Rank Fusion: her sıralama, ağırlığı × 1/(k + sıra) katar."""
    puan: dict[int, float] = {}
    for sira, agirlik in siralamalar:
        if agirlik <= 0:
            continue
        for r, i in enumerate(sira):
            puan[i] = puan.get(i, 0.0) + agirlik / (k + r + 1)
    return sorted(puan.items(), key=lambda x: -x[1])


def rrf(siralamalar: list[tuple[list[int], float]], k: int = RRF_K) -> list[int]:
    return [i for i, _ in rrf_puanli(siralamalar, k)]
