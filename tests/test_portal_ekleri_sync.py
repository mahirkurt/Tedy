"""Attachments inside the sync (plan 2026-09-28-portal-ekleri, Görev 7): after the
scrapers, before health and reindex, in an explicit budget, under the lock."""
import fcntl
import inspect
import json
import time

import pytest

import src.portal_ekleri_indir as indir
import src.run_sync as run_sync


def test_butce_hesabi():
    bas = 1000.0
    assert run_sync._ek_butcesi(bas, simdi=bas + 100) == run_sync.EK_SURE_BUTCESI
    assert run_sync._ek_butcesi(bas, simdi=bas + 400) == pytest.approx(50.0)
    assert run_sync._ek_butcesi(bas, simdi=bas + 440) == pytest.approx(10.0)
    assert (run_sync.SYNC_SURE_SINIRI, run_sync.EK_YEDEK_SURE) == (600, 150)


@pytest.fixture
def kok(tmp_path, monkeypatch):
    (tmp_path / "output").mkdir()
    (tmp_path / "output" / "scraped_data.json").write_text(json.dumps({"odevlerim": {}}), encoding="utf-8")
    monkeypatch.setattr(run_sync, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(run_sync, "OUTPUT_DIR", str(tmp_path / "output"))
    return tmp_path


def test_sure_yoksa_adim_atlanir(kok, monkeypatch):
    def cagrilmamali(*a, **k):
        raise AssertionError("çağrılmamalıydı")
    monkeypatch.setattr(indir, "ekleri_esitle", cagrilmamali)
    bas = time.time()
    assert run_sync._ekleri_esitle_adimi(bas, [], simdi=bas + 445) == {"atlandi": "sure_yok"}


def test_adim_butce_ve_kapsamli_cerezle_calisir(kok, monkeypatch):
    alinan = {}

    def sahte(proje_koku, veri, oturum, butce, cerezler=None, **kw):
        alinan.update(kok=proje_koku, veri=veri, butce=butce, cerezler=cerezler)
        return {"toplam": 0, "bu_tur_indirilen": 0, "bu_tur_bayt": 0, "kalan_is": 0}
    monkeypatch.setattr(indir, "ekleri_esitle", sahte)
    bas = time.time()
    ozet = run_sync._ekleri_esitle_adimi(bas, [
        {"name": "ASP.NET_SessionId", "value": "x", "domain": "portal.tedronesans.k12.tr"},
        {"name": "izci", "value": "y", "domain": ".google.com"}], simdi=bas + 300)
    assert ozet["toplam"] == 0
    assert str(alinan["kok"]) == str(kok) and alinan["veri"] == {"odevlerim": {}}
    kalan = alinan["butce"].son_an - time.monotonic()
    assert 140 <= kalan <= 150                      # 600 - 150 - 300
    assert alinan["butce"].bayt == run_sync.EK_BAYT_BUTCESI
    assert [c.name for c in alinan["cerezler"]] == ["ASP.NET_SessionId"]


def test_adim_hatasi_senkronu_dusurmez(kok, monkeypatch):
    def patlak(*a, **k):
        raise OSError("disk dolu")
    monkeypatch.setattr(indir, "ekleri_esitle", patlak)
    bas = time.time()
    assert run_sync._ekleri_esitle_adimi(bas, [], simdi=bas) == {"hata": "disk dolu"}


def test_main_ekleri_saglik_ve_indekslemeden_once_calistirir():
    kaynak = inspect.getsource(run_sync.main)
    adim = kaynak.index("_ekleri_esitle_adimi(")
    # rindex: the failed-login branch writes its own, earlier health file.
    assert kaynak.index("scrape_sebit_hw()") < adim < kaynak.rindex("atomic_json_dump(health")
    assert adim < kaynak.index("perform_incremental_reindex(")
    assert '"ekler": ekler_ozeti' in kaynak
    assert "driver.get_cookies()" in kaynak


def test_cli_kilit_tutuluyken_calismaz(tmp_path, monkeypatch):
    (tmp_path / "output").mkdir()
    (tmp_path / "output" / "scraped_data.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(indir, "ekleri_esitle", lambda *a, **k: {"toplam": 0})
    with open(tmp_path / "output" / ".sync.lock", "w") as kilit:
        fcntl.flock(kilit, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert indir.main(["--sure", "5"], kok=tmp_path) == 1
    assert indir.main(["--sure", "5"], kok=tmp_path) == 0
