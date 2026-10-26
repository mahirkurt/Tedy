"""Kapsam kılavuzu A4 PDF hattı (spec 2026-10-25 §5.3, plan Görev 14).

`dashboard/scripts/kilavuz-pdf.mjs` (pano node_modules'undaki Playwright, Chrome kanalı) baskı görünümünü ağsız
basar; bu modül yuvayı, zaman aşımını, yedek yolu ve önbelleği yönetir:
- Eşzamanlılık: `ESZAMANLI` yuva, `fcntl.flock` ile (iki gunicorn işçisi arasında da geçerli); yuva yoksa
  beklemeden `Mesgul` (API 429 + Retry-After).
- Zaman aşımı: Node süreci kendi süreç grubunda başlar; süre dolunca Node'un bütün soy ağacı öldürülür. Playwright
  Chrome'u AYRI bir süreç grubunda başlatır (kontrolcü kararı D6): yalnız Node'un grubunu öldürmek Chrome'u yaşatır.
  Ağaç öldürmeden önce /proc'tan çözülür, ağaçtaki her sürecin grubu SIGKILL alır (kendi grubumuz asla).
- Yedek yol: ana yol (Görev 2 kararı: `ANA_YOL`) düşerse düz Chrome baskısı; o da düşerse `Uretilemedi` (API 503).
  Basım kusurlu da sayılabilir (K3 bekçisi, kontrolcü kararı): Chrome sayfayı küçültmüşse en küçük punto 7,5'in
  altına iner; `denetimli_basim` bunu ölçer ve yolu düşürür.
- Önbellek: `output/hazirlik_pdf/<sha256>.pdf`; anahtar modelin `icerik_ozeti` + sorgu (seçenekler) + baskı
  paketinin imzası (yeni derleme önbelleği kendiliğinden geçersiz kılar). Özet üretim günü damgasını taşıdığı için
  önbellek günlük ayrışır (kabul edildi). En yeni `ONBELLEK_SINIRI` dosya kalır; isabet dosyayı tazeler.
- Güvenlik: betik yalnız sabit argümanlarla, kabuksuz çağrılır; model 700 izinli geçici dizinde 600 izinli dosyaya
  yazılır ve basım bitince silinir; basım ortamı yalnız PATH, HOME ve TZ=Europe/Istanbul taşır (sırlar Chrome'a
  geçmez)."""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import signal
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlencode

from src import pdf_kapilari

KOK = Path(__file__).resolve().parents[1]
DASHBOARD_DIZINI = KOK / "dashboard"
BETIK = DASHBOARD_DIZINI / "scripts" / "kilavuz-pdf.mjs"
ESZAMANLI = 2
SURE_SN = 90
ONBELLEK_SINIRI = 60
ANA_YOL = "paged"          # Görev 2 yoklamasının kararı: "paged" (A) ya da "duz" (B)
OLCUM_SURESI = 30          # saniye; K3 bekçisinin pdftohtml çağrısı
SAAT_DILIMI = "Europe/Istanbul"


class Mesgul(Exception):
    """Bütün basım yuvaları dolu."""


class Uretilemedi(Exception):
    """Ana yol da yedek yol da düştü."""


class Zamanasimi(Exception):
    pass


class BasimHatasi(Exception):
    pass


def baski_imzasi(dist: Path) -> str:
    try:
        return hashlib.sha256((Path(dist) / "baski.html").read_bytes()).hexdigest()[:16]
    except OSError:
        return "yok"


def onbellek_anahtari(model: dict, sorgu: dict, imza: str) -> str:
    govde = json.dumps({"m": model["icerik_ozeti"], "s": sorgu, "b": imza}, sort_keys=True)
    return hashlib.sha256(govde.encode("utf-8")).hexdigest()


# --- Süreç ağacı (D6) ---

def _stat_alanlari(pid: int) -> tuple[int, int] | None:
    """/proc/<pid>/stat → (ebeveyn, süreç grubu); ad alanı boşluk ve parantez taşıyabilir, son ')'tan sonra okunur."""
    try:
        metin = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return None
    alanlar = metin[metin.rfind(")") + 2:].split()
    try:
        return int(alanlar[1]), int(alanlar[2])
    except (IndexError, ValueError):
        return None


def _soy_agaci(kok_pid: int) -> list[tuple[int, int]]:
    """Kök ve bütün torunları: [(pid, süreç grubu)], kök önce. Ayrı oturuma/gruba geçen torun da (Chrome) soydandır."""
    cocuklar: dict[int, list[int]] = {}
    gruplar: dict[int, int] = {}
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        alan = _stat_alanlari(int(d))
        if alan is not None:
            cocuklar.setdefault(alan[0], []).append(int(d))
            gruplar[int(d)] = alan[1]
    if kok_pid not in gruplar:
        return []
    out, sira = [], [kok_pid]
    while sira:
        pid = sira.pop(0)
        out.append((pid, gruplar[pid]))
        sira.extend(c for c in cocuklar.get(pid, []) if c in gruplar)
    return out


def _agaci_oldur(kok_pid: int) -> None:
    """Kökün soy ağacındaki her süreç grubuna ve sürece SIGKILL. Ağaç önce çözülür (kök ölünce torunlar init'e geçer,
    soydan bulunamaz). Kendi süreç grubumuz (gunicorn işçisi) hiçbir zaman hedef olmaz."""
    soy = _soy_agaci(kok_pid)
    kendi = os.getpgrp()
    for g in dict.fromkeys(g for _, g in soy):
        if g != kendi and g > 1:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(g, signal.SIGKILL)
    for pid, _ in soy:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(pid, signal.SIGKILL)


def _basim_ortami() -> dict[str, str]:
    return {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", str(Path.home())),
            "TZ": SAAT_DILIMI}


def _betigi_kos(argumanlar: list[str], *, sure: float, cikti: Path, betik: Path = BETIK,
                yorumlayici: str = "node") -> bytes:
    """Basım betiğini kabuksuz, kendi süreç grubunda koşar. Süre dolarsa soy ağacını öldürür → `Zamanasimi`; sıfırdan
    farklı HER çıkış kodu (işlenmemiş istisna Node'da 1) ya da yazılmamış çıktı → `BasimHatasi`."""
    p = subprocess.Popen([yorumlayici, str(betik), *argumanlar], cwd=str(DASHBOARD_DIZINI), env=_basim_ortami(),
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                         start_new_session=True)
    try:
        _, hata = p.communicate(timeout=sure)
    except subprocess.TimeoutExpired:
        _agaci_oldur(p.pid)
        try:
            p.communicate(timeout=5)
        except subprocess.TimeoutExpired:      # boruyu tutan bir artık kaldıysa beklemeden bırak
            p.kill()
            with contextlib.suppress(OSError):
                p.stderr.close()
            p.wait(timeout=5)
        raise Zamanasimi(f"basım {sure} sn'de bitmedi") from None
    ayrinti = (hata or b"").decode("utf-8", "replace").strip()[-500:]
    if p.returncode != 0:
        raise BasimHatasi(f"çıkış {p.returncode}: {ayrinti}" if ayrinti else f"çıkış {p.returncode}")
    if not cikti.exists():
        raise BasimHatasi("betik çıktı yazmadı")
    return cikti.read_bytes()


def node_calistir(model: dict, sorgu: dict, *, duz: bool, sure: float, dist: Path, betik: Path = BETIK,
                  yorumlayici: str = "node") -> bytes:
    """Modeli 600 izinli geçici dosyaya yazar, basım betiğini koşar, PDF baytlarını döner. Betiğe kendi hazır-sinyali
    süresi toplamın %80'i olarak verilir: önce betik kendisi zaman aşımına düşsün (çıkış 4), takılırsa ağaç öldürülür."""
    with tempfile.TemporaryDirectory(prefix="tedy-kilavuz-") as d:
        model_yolu = Path(d) / "model.json"
        fd = os.open(model_yolu, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(model, f, ensure_ascii=False)
        cikti = Path(d) / "kilavuz.pdf"
        argumanlar = ["--dist", str(dist), "--model", str(model_yolu), "--cikti", str(cikti),
                      "--sorgu", urlencode(sorgu), "--sure", str(max(1000, int(sure * 800)))]
        if duz:
            argumanlar.append("--duz")
        return _betigi_kos(argumanlar, sure=sure, cikti=cikti, betik=betik, yorumlayici=yorumlayici)


def en_kucuk_punto_olc(veri: bytes) -> int | None:
    """PDF baytlarındaki en küçük yazı boyu (pdftohtml `-zoom 1`, tamsayı punto; `pdf_kapilari.en_kucuk_punto`).
    Ölçülemezse None."""
    with tempfile.TemporaryDirectory(prefix="tedy-kilavuz-olcum-") as d:
        yol = Path(d) / "k.pdf"
        fd = os.open(yol, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(veri)
        try:
            xml = subprocess.run(["pdftohtml", "-xml", "-i", "-q", "-zoom", "1", "-stdout", str(yol)],
                                 capture_output=True, text=True, check=True, timeout=OLCUM_SURESI).stdout
        except (OSError, subprocess.SubprocessError):
            return None
    return pdf_kapilari.en_kucuk_punto(xml)


def denetimli_basim(model: dict, sorgu: dict, *, duz: bool, sure: float, dist: Path, basim=node_calistir,
                    olc=en_kucuk_punto_olc) -> bytes:
    """Basım + K3 bekçisi (kontrolcü kararı): en küçük punto 7,5'in altındaysa (Chrome sayfayı küçültmüş) ya da
    ölçülemiyorsa yol kusurludur → `BasimHatasi` (ölçülemeyen değer geçer sayılmaz)."""
    veri = basim(model, sorgu, duz=duz, sure=sure, dist=dist)
    punto = olc(veri)
    if punto is None:
        raise BasimHatasi("K3: en küçük punto ölçülemedi")
    if punto < pdf_kapilari.EN_KUCUK_PUNTO:
        raise BasimHatasi(f"K3: en küçük punto {punto} < 7,5 (Chrome sayfayı küçültmüş)")
    return veri


@contextlib.contextmanager
def _yuva(dizin: Path):
    dizin.mkdir(parents=True, exist_ok=True)
    for i in range(ESZAMANLI):
        f = open(dizin / f".yuva-{i}", "w")
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            f.close()
            continue
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()
        return
    raise Mesgul("bütün basım yuvaları dolu")


def _buda(dizin: Path) -> None:
    pdfler = sorted(dizin.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in pdfler[ONBELLEK_SINIRI:]:
        with contextlib.suppress(OSError):
            p.unlink()


def _isabet(yol: Path) -> bool:
    """Önbellekte var mı; varsa tazelenir (budamada en yeni sayılır, sunulurken silinmez)."""
    try:
        os.utime(yol)
    except FileNotFoundError:
        return False
    return True


def pdf_getir(model: dict, sorgu: dict, *, dizin: Path, dist: Path, calistir=denetimli_basim,
              ana_yol: str | None = None) -> Path:
    """Önbellekteki PDF ya da yeni basım. `Mesgul` / `Uretilemedi` yükseltebilir."""
    yol = Path(dizin) / f"{onbellek_anahtari(model, sorgu, baski_imzasi(dist))}.pdf"
    if _isabet(yol):
        return yol
    with _yuva(Path(dizin)):
        if _isabet(yol):
            return yol
        son_hata: Exception | None = None
        veri = None
        for duz in ([True] if (ana_yol or ANA_YOL) == "duz" else [False, True]):
            try:
                veri = calistir(model, sorgu, duz=duz, sure=SURE_SN, dist=dist)
                break
            except (Zamanasimi, BasimHatasi, OSError) as h:
                son_hata = h
        if veri is None:
            raise Uretilemedi(str(son_hata))
        gecici = yol.with_name(yol.name + ".tmp")
        gecici.write_bytes(veri)
        os.replace(gecici, yol)
    _buda(Path(dizin))
    return yol
