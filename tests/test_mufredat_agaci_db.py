"""Üreticinin veritabanı katmanı. DB makineye bağlı; yoksa atlanır (spec §6.1)."""
import sqlite3
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "scripts"))

import mufredat_agaci as u  # noqa: E402


def _db_var() -> bool:
    try:
        u.baglan().execute("select 1 from document limit 1").fetchone()
        return True
    except sqlite3.Error:
        return False


pytestmark = pytest.mark.skipif(not _db_var(), reason="müfredat veritabanı bu makinede yok")


@pytest.fixture(scope="module")
def baglanti():
    return u.baglan()


def test_dort_ders_tanimli():
    assert set(u.DERSLER) == {"turkce", "matematik", "fen", "sosyal"}


def test_her_dersin_kitaplari_yedinci_sinif_ders_kitabi(baglanti):
    for slug, ders in u.DERSLER.items():
        for kitap_id in ders.kitaplar:
            satir = baglanti.execute(
                "select kind, grades_csv from document where id=?", (kitap_id,)).fetchone()
            assert satir is not None, f"{slug}: {kitap_id} yok"
            assert satir[0] == "textbook" and "7.Sınıf" in (satir[1] or "")


def test_fen_program_uniteleri_yedi_unite(baglanti):
    # src/assistant_skills/fen/references/unite-haritasi.md: 7 ünite, ilki "Uzay Çağı" s.146.
    uniteler = u.program_uniteleri(baglanti, u.DERSLER["fen"])
    assert len(uniteler) == 7
    assert uniteler[0]["no"] == 1 and "Uzay Çağı" in uniteler[0]["ad"]
    assert uniteler[0]["program_sayfa"] == 146


def test_fen_kazanimlari_unite_numarasini_kodundan_tasir(baglanti):
    kazanimlar = u.program_kazanimlari(baglanti, u.DERSLER["fen"])
    kodlar = {k["kod"] for k in kazanimlar}
    assert "FB.7.3.2" in kodlar
    assert next(k for k in kazanimlar if k["kod"] == "FB.7.3.2")["unite_no"] == 3


def test_icindekiler_satirlari_fen_ve_matematikte_dolu(baglanti):
    # Ölçüldü (spec §0): Fen 1 → 37, Mat 1 → 33 nokta öncüllü satır.
    assert len(u.icindekiler_satirlari(baglanti, 439)) >= 30
    assert len(u.icindekiler_satirlari(baglanti, 346)) >= 30


def test_icindekiler_satirlari_turkce_ve_sosyalde_bos(baglanti):
    # Ölçüldü (spec §0): iki sütunlu düzen, sayfa numarası başlıktan kopuk → 0 eşleşme.
    assert u.icindekiler_satirlari(baglanti, 460) == []
    assert u.icindekiler_satirlari(baglanti, 491) == []


def test_kitap_sayfalari_metin_dondurur(baglanti):
    sayfalar = u.kitap_sayfalari(baglanti, 439)
    assert len(sayfalar) > 100 and isinstance(sayfalar[10], str)
