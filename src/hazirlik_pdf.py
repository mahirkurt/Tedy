"""Kapsam kılavuzu A4 PDF hattı (spec 2026-10-25 §5.3, plan Görev 14).

`dashboard/scripts/kilavuz-pdf.mjs` (pano node_modules'undaki Playwright, Chrome kanalı) baskı görünümünü ağsız
basar; bu modül yuvayı, zaman aşımını, yedek yolu ve önbelleği yönetir:
- Eşzamanlılık: `ESZAMANLI` yuva, `fcntl.flock` ile (iki gunicorn işçisi arasında da geçerli); yuva yoksa
  beklemeden `Mesgul` (API 429 + Retry-After).
- Zaman aşımı: Node süreci kendi süreç grubunda başlar; süre dolunca Node'un bütün soy ağacı öldürülür. Playwright
  Chrome'u AYRI bir süreç grubunda başlatır (kontrolcü kararı D6): yalnız Node'un grubunu öldürmek Chrome'u yaşatır.
  Ağaç öldürmeden önce /proc'tan çözülür, ağaçtaki her sürecin grubu SIGKILL alır (kendi grubumuz asla).
- Yedek yol: ana yol (Görev 2 kararı: `ANA_YOL`) düşerse düz Chrome baskısı; o da düşerse `Uretilemedi` (API 503).
  Basım kusurlu da sayılabilir (kapı bekçisi, kontrolcü kararı): `denetimli_basim` üretilen PDF'i kanun kapılarının
  hepsinden geçirir (`pdf_kapilari.denetle` + `kusurlar`: yetim, İçindekiler, K1, alt/üst bilgi, yazı tipi, punto);
  başlıklar ve İçindekiler girdileri modelden (`pdf_kapilari.model_basliklari`). Kusur yolu düşürür.
- Bütçe: Cloudflare tünelinin ~100 sn kenar sınırı. Ana yol `ANA_SURE_SN`, düz yol `DUZ_SURE_SN`; her biri basım +
  denetimdir (`DENETIM_SURESI`). Gerçek basım 2–6 sn, denetim ~1 sn sürüyor.
- Önbellek: `output/hazirlik_pdf/<sha256>.pdf`; anahtar modelin `icerik_ozeti` + sorgu (seçenekler) + baskı
  paketinin imzası (yeni derleme önbelleği kendiliğinden geçersiz kılar). Özet üretim günü damgasını taşıdığı için
  önbellek günlük ayrışır (kabul edildi). En yeni `ONBELLEK_SINIRI` dosya kalır; isabet dosyayı tazeler.
- Güvenlik: betik yalnız sabit argümanlarla, kabuksuz çağrılır; model 700 izinli geçici dizinde 600 izinli dosyaya
  yazılır ve basım bitince silinir; basım ortamı yalnız PATH, HOME, TZ=Europe/Istanbul ve TMPDIR (koşunun geçici
  dizini: Chrome profili orada kalır, zorla öldürmede /tmp'ye sızmaz) taşır (sırlar Chrome'a geçmez)."""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urlencode

from src import pdf_kapilari

KOK = Path(__file__).resolve().parents[1]
DASHBOARD_DIZINI = KOK / "dashboard"
BETIK = DASHBOARD_DIZINI / "scripts" / "kilavuz-pdf.mjs"
ESZAMANLI = 2
ANA_SURE_SN = 40           # ana yol: basım + denetim (Cloudflare kenar sınırı ~100 sn; ana + düz ≤ 70)
DUZ_SURE_SN = 30           # yedek yol: basım + denetim
DENETIM_SURESI = 8         # her yolun bütçesinden kapı denetimine ayrılan saniye
ONBELLEK_SINIRI = 60
YARIM_YAS_SN = 300         # bundan eski `*.pdf.*.tmp` yarım kalmış yazımdır, budanır
ANA_YOL = "paged"          # Görev 2 yoklamasının kararı: "paged" (A) ya da "duz" (B)
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


def _basim_ortami(tmpdir: str | None = None) -> dict[str, str]:
    ortam = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", str(Path.home())),
             "TZ": SAAT_DILIMI}
    if tmpdir:
        ortam["TMPDIR"] = tmpdir
    return ortam


def _betigi_kos(argumanlar: list[str], *, sure: float, cikti: Path, betik: Path = BETIK,
                yorumlayici: str = "node", ortam: dict[str, str] | None = None) -> bytes:
    """Basım betiğini kabuksuz, kendi süreç grubunda koşar. Süre dolarsa soy ağacını öldürür → `Zamanasimi`; sıfırdan
    farklı HER çıkış kodu (işlenmemiş istisna Node'da 1) ya da yazılmamış çıktı → `BasimHatasi`."""
    p = subprocess.Popen([yorumlayici, str(betik), *argumanlar], cwd=str(DASHBOARD_DIZINI),
                         env=_basim_ortami() if ortam is None else ortam,
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
            with contextlib.suppress(subprocess.TimeoutExpired):   # yine bitmezse de sonuç zaman aşımıdır
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
    # Zorla öldürülen Chrome dizine yazarken silinebilir: temizlik hatası basımın sonucunu değiştirmez.
    with tempfile.TemporaryDirectory(prefix="tedy-kilavuz-", ignore_cleanup_errors=True) as d:
        model_yolu = Path(d) / "model.json"
        fd = os.open(model_yolu, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(model, f, ensure_ascii=False)
        cikti = Path(d) / "kilavuz.pdf"
        argumanlar = ["--dist", str(dist), "--model", str(model_yolu), "--cikti", str(cikti),
                      "--sorgu", urlencode(sorgu), "--sure", str(max(1000, int(sure * 800)))]
        if duz:
            argumanlar.append("--duz")
        return _betigi_kos(argumanlar, sure=sure, cikti=cikti, betik=betik, yorumlayici=yorumlayici,
                           ortam=_basim_ortami(d))


def kapilari_denetle(veri: bytes, model: dict, *, duz: bool, sure: float) -> list[str]:
    """Üretilen PDF'in kanun kusurları (`pdf_kapilari.denetle` + `kusurlar`); boş liste temiz. Başlıklar ve İçindekiler
    girdileri modelden; düz yolda İçindekiler sayfa numarası taşımaz, beklenmez. `DenetimHatasi` yükseltebilir."""
    basliklar, icindekiler = pdf_kapilari.model_basliklari(model)
    with tempfile.TemporaryDirectory(prefix="tedy-kilavuz-denetim-") as d:
        yol = Path(d) / "k.pdf"
        fd = os.open(yol, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(veri)
        rapor = pdf_kapilari.denetle(yol, basliklar=basliklar, icindekiler=icindekiler, duz=duz,
                                     kapak=pdf_kapilari.kapak_sayfasi(model), sure=sure)
    return pdf_kapilari.kusurlar(rapor, icindekiler_beklenir=not duz)


def denetimli_basim(model: dict, sorgu: dict, *, duz: bool, sure: float, dist: Path, basim=node_calistir,
                    denetci=kapilari_denetle) -> bytes:
    """Basım + kapı bekçisi (kontrolcü kararı): `sure` yolun bütçesidir; basım `sure - DENETIM_SURESI`, denetim
    `DENETIM_SURESI` alır. Kusur varsa ya da PDF denetlenemezse (ölçülemeyen değer geçer sayılmaz) `BasimHatasi`."""
    veri = basim(model, sorgu, duz=duz, sure=sure - DENETIM_SURESI, dist=dist)
    try:
        kusur = denetci(veri, model, duz=duz, sure=DENETIM_SURESI)
    except (pdf_kapilari.DenetimHatasi, ValueError) as h:
        # ValueError (JSONDecodeError dahil): qpdf/pdftohtml çıktısı ayrışmadı — ölçülemeyen geçer sayılmaz ve
        # 500 olmaz; BasimHatasi ana yolu düşürür, düz yol denenir.
        raise BasimHatasi(f"kapılar: denetlenemedi ({h})") from None
    if kusur:
        raise BasimHatasi("kapılar: " + "; ".join(kusur))
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


def _mtime(p: Path) -> float | None:
    try:
        return p.stat().st_mtime
    except FileNotFoundError:      # başka işçi bu arada sildi
        return None


def _buda(dizin: Path) -> None:
    """En yeni `ONBELLEK_SINIRI` PDF kalır; `YARIM_YAS_SN`'den eski yarım yazımlar (`*.pdf.*.tmp`) silinir."""
    zamanlar = [(p, m) for p in dizin.glob("*.pdf") if (m := _mtime(p)) is not None]
    zamanlar.sort(key=lambda pm: pm[1], reverse=True)
    silinecek = [p for p, _ in zamanlar[ONBELLEK_SINIRI:]]
    esik = time.time() - YARIM_YAS_SN
    silinecek += [p for p in dizin.glob("*.pdf.*.tmp") if (m := _mtime(p)) is not None and m < esik]
    for p in silinecek:
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
        veri = None
        hatalar = []
        for duz in ([True] if (ana_yol or ANA_YOL) == "duz" else [False, True]):
            try:
                veri = calistir(model, sorgu, duz=duz, sure=DUZ_SURE_SN if duz else ANA_SURE_SN, dist=dist)
                break
            except (Zamanasimi, BasimHatasi, OSError) as h:
                hatalar.append(f"{'düz' if duz else 'ana'} yol: {h}")
        if veri is None:
            raise Uretilemedi(" | ".join(hatalar))
        # Benzersiz geçici ad: iki işçi aynı anahtarı aynı anda yazarsa birbirinin yarım dosyasını taşımaz.
        fd, gecici = tempfile.mkstemp(dir=str(dizin), prefix=yol.name + ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(veri)
            os.replace(gecici, yol)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(gecici)
            raise
    _buda(Path(dizin))
    return yol
