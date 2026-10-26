"""Sınav hazırlığında bilerek kopyalanan ya da paylaşılan mantığın ayrışmaması (son inceleme, madde 6)."""
import re
from pathlib import Path

from scripts import meb_kitap_haritasi as mkh
from src import sinav_kilavuzu, sinav_senaryo

KOK = Path(__file__).resolve().parents[1]
HAZIRLIK_TS = KOK / "dashboard" / "src" / "hazirlik" / "hazirlik.ts"


def test_ts_ders_anahtarlari_python_ile_ayni():
    """`hazirlik.ts` ANAHTARLAR (ders adı -> adres anahtarı) `sinav_senaryo.DERS_ANAHTARLARI`'nın eşidir; biri değişip
    öbürü kalırsa pano yanlış adrese gider ya da ders karosu açılmaz."""
    kaynak = HAZIRLIK_TS.read_text(encoding="utf-8")
    govde = re.search(r"const ANAHTARLAR: Record<string, string> = \{(.*?)\n\}", kaynak, re.S)
    assert govde, "hazirlik.ts içinde ANAHTARLAR bildirimi bulunamadı"
    ts = dict(re.findall(r"'([^']+)':\s*'([^']+)'", govde.group(1)))
    assert ts, "ANAHTARLAR ayrıştırılamadı"
    assert ts == sinav_senaryo.DERS_ANAHTARLARI


def test_kod_sirasi_tek_kaynaktan_gelir():
    assert sinav_kilavuzu._kod_sirasi is sinav_senaryo._kod_sirasi
    assert mkh._kod_sirasi is sinav_senaryo._kod_sirasi


def test_kod_sirasi_sayisal_siralar():
    kodlar = ["FB.7.2.10", "FB.7.2.9", "FB.7.1.1", "FB.7.10.1", "FB.7.2.2"]
    assert sorted(kodlar, key=sinav_senaryo._kod_sirasi) == [
        "FB.7.1.1", "FB.7.2.2", "FB.7.2.9", "FB.7.2.10", "FB.7.10.1"]
