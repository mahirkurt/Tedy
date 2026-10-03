"""Sohbet deposu (spec §3). Ağ yok."""
import threading
from datetime import datetime, timezone

import pytest

from src.assistant_sohbet import SohbetDeposu

ISIK = "student@example.test"
SIMDI = datetime(2026, 10, 3, 8, 0, tzinfo=timezone.utc)


def test_wal_ve_bos_liste(tmp_path):
    depo = SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")
    assert depo.journal_mode() == "wal"
    assert depo.liste(ISIK) == []


def test_son_yirmi_yeniyi_tutar(tmp_path):
    depo = SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")
    sid = depo.yarat(ISIK, "genel", SIMDI)
    for i in range(25):
        depo.mesaj_ekle(sid, "user", f"m{i}", "genel", [], SIMDI)
    son = depo.son_mesajlar(sid, 20)
    assert [m["icerik"] for m in son] == [f"m{i}" for i in range(5, 25)]
    assert depo.tum_mesajlar(sid)[0]["icerik"] == "m0"


def test_ayni_saniye_soru_cevap_sirasi(tmp_path):
    depo = SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")
    sid = depo.yarat(ISIK, "matematik", SIMDI)
    depo.mesaj_ekle(sid, "user", "soru", "matematik", [], SIMDI)
    depo.mesaj_ekle(sid, "assistant", "cevap", "matematik", [], SIMDI)
    assert [m["rol"] for m in depo.son_mesajlar(sid, 20)] == ["user", "assistant"]
    assert [m["rol"] for m in depo.tum_mesajlar(sid)] == ["user", "assistant"]


def test_mesaj_ogretmeni_satiri_ezmez(tmp_path):
    depo = SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")
    sid = depo.yarat(ISIK, "matematik", SIMDI)
    depo.mesaj_ekle(sid, "user", "soru", "fen", [], SIMDI)
    assert depo.getir(sid)["ogretmen"] == "matematik"
    assert depo.tum_mesajlar(sid)[0]["ogretmen"] == "fen"


def test_iki_yazici(tmp_path):
    yol = tmp_path / "assistant_sohbetler.sqlite"
    depo = SohbetDeposu(yol)
    sid = depo.yarat(ISIK, "genel", SIMDI)
    bariyer = threading.Barrier(2)
    hatalar = []

    def yaz(on):
        try:
            bariyer.wait()
            yerel = SohbetDeposu(yol)
            for i in range(20):
                yerel.mesaj_ekle(sid, "user", f"{on}-{i}", "genel", [], SIMDI)
        except Exception as exc:  # noqa: BLE001 — the assertion is the message
            hatalar.append(exc)

    iplikler = [threading.Thread(target=yaz, args=(n,)) for n in ("a", "b")]
    for t in iplikler:
        t.start()
    for t in iplikler:
        t.join()
    assert hatalar == []
    assert len(SohbetDeposu(yol).tum_mesajlar(sid)) == 40
