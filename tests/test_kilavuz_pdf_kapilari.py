"""Kılavuz PDF kapı betiği (scripts/kilavuz_pdf_kapilari.py): basım ortamı, zaman aşımı, çıktı yolu."""
import json
import subprocess
from pathlib import Path

from scripts import kilavuz_pdf_kapilari as kpk


def test_basim_ortami_istanbul_saatiyle(monkeypatch, tmp_path):
    goren = {}

    def kos(komut, **k):
        goren.update(komut=komut, env=k["env"])
        return subprocess.CompletedProcess(komut, 0, "", "TEDY_BELLEK_KB=204800")
    monkeypatch.setattr(kpk.subprocess, "run", kos)
    olcum = kpk.bas(tmp_path, tmp_path / "k.pdf", "ders=fen-bilimleri&sinav=1", None, False)
    assert goren["env"]["TZ"] == "Europe/Istanbul"          # damga ve "üretim" günü İstanbul'a göre
    assert set(goren["env"]) == {"PATH", "HOME", "TZ"}      # servis ortamı (Y8)
    assert olcum["cikis"] == 0 and olcum["bellek"] == "200 MB"


def test_basim_zaman_asimi_anlamli_hata(monkeypatch, tmp_path):
    def takil(komut, **k):
        raise subprocess.TimeoutExpired(cmd=komut, timeout=k["timeout"])
    monkeypatch.setattr(kpk.subprocess, "run", takil)
    olcum = kpk.bas(tmp_path, tmp_path / "k.pdf", "ders=fen-bilimleri&sinav=1", None, False)
    assert olcum["cikis"] == "zaman aşımı"
    assert olcum["stderr"] == "basım 300 s içinde bitmedi"


def test_cikti_mutlak_yola_cevrilir(monkeypatch, tmp_path):
    """Basım `dashboard/` içinde koşar: göreli --cikti oraya yazılmasın diye betik yolu çözer."""
    monkeypatch.chdir(tmp_path)
    gorulen = []

    def bas(dist, cikti, sorgu, model, duz):
        gorulen.append(cikti)
        return {"cikis": 1, "sure_sn": 0.0, "bellek": "?", "stderr": "deneme"}
    monkeypatch.setattr(kpk, "bas", bas)
    assert kpk.main(["--dist", "d", "--cikti", "goreli/k", "--yol", "paged"]) == 1
    assert gorulen == [tmp_path / "goreli" / "k" / "paged.pdf"]
    assert Path(gorulen[0]).is_absolute()


FIKSTUR = Path(__file__).resolve().parents[1] / "dashboard" / "tests" / "e2e" / "fixtures" / "hazirlik"


def test_model_icindekiler_bolumlerle_ayni_yedi_girdi():
    """İçindekiler kapısı `belge.bolumler(m)` ile aynı listeyi denetler; Özet'in sayfasında aranan "Kapsam Kılavuzu"."""
    m = json.loads((FIKSTUR / "fen-bilimleri-1-kilavuz.json").read_text(encoding="utf-8"))
    _, icindekiler = kpk.model_basliklari(m)
    assert icindekiler == [("Özet", "Kapsam Kılavuzu"), "Senaryo Karşılaştırması", "1. Ünite · Uzay Çağı",
                           "2. Ünite · Kuvvet ve Enerjiyi Keşfedelim", "Duyuru Doğrulaması", "Çalışma Planı",
                           "Kaynaklar"]
    e = json.loads((FIKSTUR / "fen-bilimleri-1-kilavuz-ebeveyn.json").read_text(encoding="utf-8"))
    assert kpk.model_basliklari(e)[1][0] == "Ebeveyn Özeti"
    assert kpk.kapak_sayfasi(e) == 2 and kpk.kapak_sayfasi(m) == 1
