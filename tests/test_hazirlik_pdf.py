"""Kılavuz PDF hattı (plan Görev 14): yuva, zaman aşımında süreç grubunun öldürülmesi, yedek yol, önbellek, uç."""
import copy
import fcntl
import json
import os
import shutil
import stat
import sys
import time
from pathlib import Path

import pytest

from src import hazirlik_pdf as hp

MODEL = {"icerik_ozeti": "a" * 64, "senaryo": 2, "secenekler": {"ebeveyn": False, "isaret": True}}
SORGU = {"ders": "fen-bilimleri", "sinav": "1", "senaryo": "2"}
KOK = Path(__file__).resolve().parents[1]
GERCEK_DIST = KOK / "dashboard-dist"
FIKSTUR = KOK / "dashboard" / "tests" / "e2e" / "fixtures" / "hazirlik" / "fen-bilimleri-1-kilavuz.json"


@pytest.fixture
def dist(tmp_path):
    d = tmp_path / "dist"
    d.mkdir()
    (d / "baski.html").write_text("<html>baski</html>", encoding="utf-8")
    return d


class SahteBasim:
    def __init__(self, *sonuclar):
        self.sonuclar, self.cagrilar = list(sonuclar), []

    def __call__(self, model, sorgu, *, duz, sure, dist):
        self.cagrilar.append(duz)
        s = self.sonuclar.pop(0)
        if isinstance(s, Exception):
            raise s
        return s


def test_onbellek_ikinci_istekte_basmaz(tmp_path, dist):
    basim = SahteBasim(b"%PDF-1")
    a = hp.pdf_getir(MODEL, SORGU, dizin=tmp_path / "o", dist=dist, calistir=basim)
    b = hp.pdf_getir(MODEL, SORGU, dizin=tmp_path / "o", dist=dist, calistir=basim)
    assert a == b and a.read_bytes() == b"%PDF-1" and basim.cagrilar == [False]
    (dist / "baski.html").write_text("<html>yeni derleme</html>", encoding="utf-8")
    basim.sonuclar.append(b"%PDF-2")
    assert hp.pdf_getir(MODEL, SORGU, dizin=tmp_path / "o", dist=dist, calistir=basim).read_bytes() == b"%PDF-2"


def test_onbellek_anahtari_icerik_ozeti_ve_seceneklerle_ayrisir(tmp_path, dist):
    """Önbellek anahtarı içerik özeti + seçenekler (sorgu) + baskı paketinin imzası: biri değişince yeniden basılır."""
    basim = SahteBasim(b"%PDF-a", b"%PDF-b", b"%PDF-c")
    hp.pdf_getir(MODEL, SORGU, dizin=tmp_path, dist=dist, calistir=basim)
    hp.pdf_getir({**MODEL, "icerik_ozeti": "b" * 64}, SORGU, dizin=tmp_path, dist=dist, calistir=basim)
    hp.pdf_getir(MODEL, {**SORGU, "ebeveyn": "1"}, dizin=tmp_path, dist=dist, calistir=basim)
    assert basim.cagrilar == [False, False, False] and len(list(tmp_path.glob("*.pdf"))) == 3


def test_ana_yol_duserse_yedek_yol_denenir(tmp_path, dist):
    """Review Focus: Paged.js yolu zaman aşımına düşerse düz Chrome baskısı denenir."""
    basim = SahteBasim(hp.Zamanasimi("90 sn"), b"%PDF-duz")
    yol = hp.pdf_getir(MODEL, SORGU, dizin=tmp_path, dist=dist, calistir=basim)
    assert basim.cagrilar == [False, True] and yol.read_bytes() == b"%PDF-duz"


def test_iki_yol_duserse_uretilemedi_ve_dosya_yazilmaz(tmp_path, dist):
    basim = SahteBasim(hp.BasimHatasi("sayfa hatası"), hp.Zamanasimi("90 sn"))
    with pytest.raises(hp.Uretilemedi):
        hp.pdf_getir(MODEL, SORGU, dizin=tmp_path, dist=dist, calistir=basim)
    assert list(tmp_path.glob("*.pdf")) == []


def test_ana_yol_duz_ise_yalniz_duz(tmp_path, dist):
    basim = SahteBasim(b"%PDF")
    hp.pdf_getir(MODEL, SORGU, dizin=tmp_path, dist=dist, calistir=basim, ana_yol="duz")
    assert basim.cagrilar == [True]


def test_yuvalar_doluyken_mesgul(tmp_path, dist):
    """Review Focus: eşzamanlı istek sınırı aşılınca beklemeden Mesgul; basım çağrılmaz."""
    tutulan = []
    for i in range(hp.ESZAMANLI):
        f = open(tmp_path / f".yuva-{i}", "w")
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        tutulan.append(f)
    basim = SahteBasim(b"%PDF")
    with pytest.raises(hp.Mesgul):
        hp.pdf_getir(MODEL, SORGU, dizin=tmp_path, dist=dist, calistir=basim)
    assert basim.cagrilar == []
    for f in tutulan:
        f.close()
    assert hp.pdf_getir(MODEL, SORGU, dizin=tmp_path, dist=dist, calistir=basim).exists()


def test_onbellek_en_yeni_dosyalari_tutar(tmp_path, monkeypatch):
    monkeypatch.setattr(hp, "ONBELLEK_SINIRI", 2)
    for i in range(3):
        (tmp_path / f"{i}.pdf").write_bytes(b"%PDF")
        os.utime(tmp_path / f"{i}.pdf", (1000 + i, 1000 + i))
    hp._buda(tmp_path)
    assert sorted(p.name for p in tmp_path.glob("*.pdf")) == ["1.pdf", "2.pdf"]


def test_onbellek_isabeti_dosyayi_tazeler(tmp_path, dist, monkeypatch):
    """Önbellekten verilen dosya budamada en yeni sayılır (sunulurken silinmesin)."""
    basim = SahteBasim(b"%PDF")
    yol = hp.pdf_getir(MODEL, SORGU, dizin=tmp_path, dist=dist, calistir=basim)
    os.utime(yol, (1000, 1000))
    hp.pdf_getir(MODEL, SORGU, dizin=tmp_path, dist=dist, calistir=basim)
    assert yol.stat().st_mtime > 1000


# --- K3 bekçisi (kontrolcü kararı): Chrome sayfayı küçültmüşse (en küçük punto < 7,5) yol kusurludur ---

def test_k3_bekcisi_kucultulmus_basimi_kusurlu_sayar(dist):
    olcumler = []

    def olc(veri):
        olcumler.append(veri)
        return {b"%PDF-kucuk": 5, b"%PDF-iyi": 8}.get(veri)
    for veri, beklenen in ((b"%PDF-kucuk", "en küçük punto 5"), (b"%PDF-bozuk", "ölçülemedi")):
        with pytest.raises(hp.BasimHatasi, match=beklenen):
            hp.denetimli_basim(MODEL, SORGU, duz=False, sure=5, dist=dist,
                               basim=lambda *a, v=veri, **k: v, olc=olc)
    assert hp.denetimli_basim(MODEL, SORGU, duz=True, sure=5, dist=dist,
                              basim=lambda *a, **k: b"%PDF-iyi", olc=olc) == b"%PDF-iyi"
    assert olcumler == [b"%PDF-kucuk", b"%PDF-bozuk", b"%PDF-iyi"]


def test_k3_bekcisi_ana_yolu_dusurur_duz_denenir_o_da_kucukse_uretilemedi(tmp_path, dist):
    """Paged.js basımı küçülmüşse düz yol denenir; düz yol da küçülmüşse Uretilemedi (API: 503 + Türkçe cümle)."""
    puntolar = {b"%PDF-paged": 5, b"%PDF-duz": 9}
    cagrilar = []

    def basim(model, sorgu, *, duz, sure, dist):
        cagrilar.append(duz)
        return hp.denetimli_basim(model, sorgu, duz=duz, sure=sure, dist=dist,
                                  basim=lambda *a, **k: b"%PDF-duz" if duz else b"%PDF-paged", olc=puntolar.get)
    assert hp.pdf_getir(MODEL, SORGU, dizin=tmp_path / "a", dist=dist, calistir=basim).read_bytes() == b"%PDF-duz"
    assert cagrilar == [False, True]
    puntolar[b"%PDF-duz"] = 6
    with pytest.raises(hp.Uretilemedi, match="punto"):
        hp.pdf_getir(MODEL, SORGU, dizin=tmp_path / "b", dist=dist, calistir=basim)
    assert list((tmp_path / "b").glob("*.pdf")) == []


def test_pdf_getirin_varsayilan_basimi_denetimlidir():
    import inspect
    assert inspect.signature(hp.pdf_getir).parameters["calistir"].default is hp.denetimli_basim


# --- Basım betiğinin çağrılması: sabit argümanlar, kabuk yok, model 600 izinli geçici dosyada, TZ ---

SAHTE_BETIK = r'''
import json, os, stat, subprocess, sys, time
a = sys.argv[1:]
deger = lambda k: a[a.index(k) + 1]
sorgu = deger("--sorgu")
if "--uyu" in sorgu:
    # Chrome'un yerine: kendi süreç grubunda (setsid) başlayan torun ve onun çocuğu (Chrome'un alt süreçleri gibi).
    torun = subprocess.Popen([sys.executable, "-c",
        "import subprocess, sys, time; c = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']);"
        "open(sys.argv[1], 'w').write(str(c.pid)); time.sleep(60)", deger("--dist") + "/cocuk.pid"],
        start_new_session=True)
    son = time.monotonic() + 30          # yükte üç Python başlangıcı yavaş: çocuk başlayınca torun.pid yazılır
    while not os.path.exists(deger("--dist") + "/cocuk.pid") and time.monotonic() < son:
        time.sleep(0.02)
    open(deger("--dist") + "/torun.pid", "w").write(f"{torun.pid} {os.getpgid(torun.pid)} {os.getpgrp()}")
    time.sleep(60)
if sorgu.startswith("cikis="):
    sys.exit(int(sorgu.split("=")[1]))
if "ortam" in sorgu:
    m = deger("--model")
    open(deger("--cikti"), "wb").write(b"%PDF-sahte " + json.dumps({
        "tz": os.environ.get("TZ"), "anahtar": "ANTHROPIC_API_KEY" in os.environ,
        "izin": oct(stat.S_IMODE(os.stat(m).st_mode)), "model": m,
        "dizin_izni": oct(stat.S_IMODE(os.stat(os.path.dirname(m)).st_mode)),
        "icerik": json.load(open(m, encoding="utf-8"))}).encode())
    sys.exit(0)
open(deger("--cikti"), "wb").write(b"%PDF-sahte " + json.dumps(a).encode())
'''


def _yasiyor(pid):
    try:
        return Path(f"/proc/{pid}/stat").read_text().split()[2] != "Z"
    except FileNotFoundError:
        return False


@pytest.fixture
def sahte_betik(tmp_path):
    betik = tmp_path / "sahte.py"
    betik.write_text(SAHTE_BETIK, encoding="utf-8")
    return betik


def test_basim_betigi_argumanlari_ve_ciktisi(dist, sahte_betik):
    veri = hp.node_calistir(MODEL, SORGU, duz=True, sure=20, dist=dist, betik=sahte_betik, yorumlayici=sys.executable)
    assert veri.startswith(b"%PDF-sahte ")
    argv = json.loads(veri[len(b"%PDF-sahte "):])
    assert argv[argv.index("--sorgu") + 1] == "ders=fen-bilimleri&sinav=1&senaryo=2"
    assert argv[argv.index("--dist") + 1] == str(dist) and "--duz" in argv
    assert argv[argv.index("--sure") + 1] == "16000"


def test_basim_ortami_tz_istanbul_model_600_ve_silinir(dist, sahte_betik, monkeypatch):
    """Model geçici dizinde 600 izinle yazılır ve basım bitince silinir; ortam TZ=Europe/Istanbul, sırlar taşınmaz."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-deneme")
    monkeypatch.setenv("TZ", "Etc/UTC")
    veri = hp.node_calistir({**MODEL, "ders": "Fen Bilimleri"}, {"sorgu": "ortam"}, duz=False, sure=20, dist=dist,
                            betik=sahte_betik, yorumlayici=sys.executable)
    o = json.loads(veri[len(b"%PDF-sahte "):])
    assert (o["tz"], o["anahtar"], o["izin"], o["dizin_izni"]) == ("Europe/Istanbul", False, "0o600", "0o700")
    assert o["icerik"]["ders"] == "Fen Bilimleri"
    assert not Path(o["model"]).exists() and not Path(o["model"]).parent.exists()


@pytest.mark.parametrize("kod", [1, 2, 3, 4, 5])
def test_sifirdan_farkli_her_cikis_basim_hatasi(dist, sahte_betik, kod):
    """Görev 1 kalanı (a): çağıran taraf sıfırdan farklı HER çıkış kodunu hata sayar."""
    with pytest.raises(hp.BasimHatasi, match=f"çıkış {kod}"):
        hp.node_calistir(MODEL, {"cikis": str(kod)}, duz=False, sure=20, dist=dist, betik=sahte_betik,
                         yorumlayici=sys.executable)


def test_zaman_asiminda_surec_grubu_oldurulur(dist, sahte_betik):
    """Review Focus (D6): takılan basım öldürülür; kendi süreç grubunda (setsid) başlayan torun — Playwright Chrome'u
    ayrı grupta başlatır — ve onun çocuğu da yaşamaz."""
    with pytest.raises(hp.Zamanasimi):
        hp.node_calistir(MODEL, {"sorgu": "--uyu"}, duz=False, sure=6, dist=dist, betik=sahte_betik,
                         yorumlayici=sys.executable)
    assert (dist / "torun.pid").exists(), "kurulum süre dolmadan bitmedi: torun ve çocuğu başlamamıştı"
    torun, torun_grubu, betik_grubu = map(int, (dist / "torun.pid").read_text().split())
    cocuk = int((dist / "cocuk.pid").read_text())
    assert torun_grubu == torun != betik_grubu          # torun gerçekten ayrı grupta başlamıştı
    son = time.monotonic() + 5
    while (_yasiyor(torun) or _yasiyor(cocuk)) and time.monotonic() < son:
        time.sleep(0.05)
    assert not _yasiyor(torun) and not _yasiyor(cocuk)


def test_soy_agaci_ayri_gruptaki_torunu_bulur():
    """Ağaç /proc'tan çözülür: ayrı oturumdaki torun da soydan sayılır, kendi grubumuz hiç öldürülmez."""
    import subprocess
    p = subprocess.Popen([sys.executable, "-c",
                          "import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', 'import time; "
                          "time.sleep(30)'], start_new_session=True); time.sleep(30)"], start_new_session=True)
    try:
        son = time.monotonic() + 5
        soy = []
        while len(soy) < 2 and time.monotonic() < son:
            soy = hp._soy_agaci(p.pid)
            time.sleep(0.05)
        assert soy[0][0] == p.pid and len(soy) == 2
        gruplar = {g for _, g in soy}
        assert len(gruplar) == 2 and os.getpgrp() not in gruplar
    finally:
        hp._agaci_oldur(p.pid)
        p.wait(timeout=5)


# --- Gerçek basım betiği (Görev 1 kalanı b): işlenmemiş istisna çıkış 1, dist'te baski.html yoksa beklemeden hata ---

gercek_basim = pytest.mark.skipif(shutil.which("node") is None or not (KOK / "dashboard" / "node_modules").exists(),
                                  reason="node ya da pano node_modules yok: gerçek basım betiği koşamaz")


@gercek_basim
def test_gercek_betik_islenmemis_istisnada_cikis_1(dist, tmp_path):
    """Betikte yakalanmayan istisna (burada okunamayan --model) Node'u çıkış 1 ile bitirir; çağıran hata sayar."""
    t = time.monotonic()
    with pytest.raises(hp.BasimHatasi, match="çıkış 1"):
        hp._betigi_kos(["--dist", str(dist), "--model", str(tmp_path / "yok.json"), "--cikti", str(tmp_path / "k.pdf"),
                        "--sorgu", "ders=fen-bilimleri&sinav=1", "--sure", "5000"], sure=20, cikti=tmp_path / "k.pdf")
    assert time.monotonic() - t < 15


@gercek_basim
def test_gercek_betik_dist_baski_html_yoksa_beklemeden_hata(tmp_path):
    bos = tmp_path / "bos-dist"
    bos.mkdir()
    t = time.monotonic()
    with pytest.raises(hp.BasimHatasi, match="baski.html"):
        hp.node_calistir(MODEL, SORGU, duz=False, sure=60, dist=bos)
    assert time.monotonic() - t < 10                      # 45 sn hazır sinyali beklenmez


@gercek_basim
def test_gercek_betik_sayfa_acilamazsa_goto_hatasi(tmp_path):
    """goto yanıtı ok() değilse (baski.html okunamıyor → 404) betik hazır sinyalini beklemeden çıkış 3 verir."""
    d = tmp_path / "dist"
    d.mkdir()
    (d / "baski.html").write_text("<html></html>", encoding="utf-8")
    (d / "baski.html").chmod(0)
    try:
        if os.access(d / "baski.html", os.R_OK):
            pytest.skip("kök kullanıcı: izinsiz dosya yine okunur")
        t = time.monotonic()
        with pytest.raises(hp.BasimHatasi, match="HTTP 404"):
            hp.node_calistir(MODEL, SORGU, duz=False, sure=60, dist=d)
        assert time.monotonic() - t < 30
    finally:
        (d / "baski.html").chmod(stat.S_IRUSR | stat.S_IWUSR)


def _uzun_metinli_model(uzunluk: int) -> dict:
    """Gerçek Fen modelinin ilk ünitesi kâğıttaki en büyük parça boyuna (8 satır) çıkarılır, her çıktı metni
    `uzunluk` karakter (MEB tablosundaki en uzun çıktı metni 170 karakter, Matematik)."""
    m = json.loads(FIKSTUR.read_text(encoding="utf-8"))
    g = m["matris"]["gruplar"][0]
    taban = ("Uzay araştırmaları için geliştirilen teknolojileri karşılaştırabilme ve bu teknolojilerin günlük "
             "yaşamdaki kullanım alanlarını örneklerle açıklayabilme; ") * 3
    metin = taban[:uzunluk].rsplit(" ", 1)[0]
    satirlar = []
    for i in range(8):
        s = copy.deepcopy(g["satirlar"][i % len(g["satirlar"])])
        s["kod"], s["metin"], s["kisa_ad"] = f"FB.7.9.{i + 1}", metin, metin
        satirlar.append(s)
    g["satirlar"] = satirlar
    m["icerik_ozeti"] = "u" * 64
    return m


@gercek_basim
@pytest.mark.skipif(not (GERCEK_DIST / "baski.html").exists(), reason="dashboard-dist yok: önce npm run build")
def test_k3_bekcisi_uzun_metinli_fikstur_gercek_basim(tmp_path):
    """Uzun metinli 8 satırlık ünite tablosu gerçek Chrome'la basılır: sunulan PDF K3'ü sağlar (en küçük punto ≥ 7,5)
    ve bekçi ölçümü yanlış alarm vermez (ana yol kabul edilir)."""
    yollar = []

    def casus(model, sorgu, *, duz, sure, dist):
        yollar.append(duz)
        return hp.denetimli_basim(model, sorgu, duz=duz, sure=sure, dist=dist)
    yol = hp.pdf_getir(_uzun_metinli_model(170), {"ders": "fen-bilimleri", "sinav": "1", "senaryo": "2"},
                       dizin=tmp_path, dist=GERCEK_DIST, calistir=casus)
    veri = yol.read_bytes()
    assert veri.startswith(b"%PDF-")
    punto = hp.en_kucuk_punto_olc(veri)
    assert punto is not None and punto >= 8
    assert yollar == [False]
