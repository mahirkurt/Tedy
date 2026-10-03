"""Attachments inside the sync (plan 2026-09-28-portal-ekleri, Görev 7): after the
scrapers, before health and reindex, in an explicit budget, under the lock."""
import fcntl
import json
import os
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


def _kilit_alinabilir(yol):
    """Whether this process can take the exclusive lock.

    Measured 2026-10-03 on Linux 6.8: flock on a second open conflicts with
    a lock the same process already holds. A download running inside main()
    or the CLI can therefore see that the sync lock is still theirs; closing
    the lock file just before the download makes this return True.
    """
    f = open(os.fspath(yol), "a+")
    try:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return False
        fcntl.flock(f, fcntl.LOCK_UN)
        return True
    finally:
        f.close()


class _CerezliSurucu:
    def get_cookies(self):
        return [
            {"name": "ASP.NET_SessionId", "value": "oturum", "domain": "portal.tedronesans.k12.tr"},
            {"name": "izci", "value": "y", "domain": ".google.com"},
        ]

    def get(self, url):
        pass

    def quit(self):
        pass


def _basarili_main(tmp_path, monkeypatch, ekleri, reindex):
    """Drive main() through login and the scrapers without a portal."""
    out = tmp_path / "output"
    out.mkdir()
    monkeypatch.setattr(run_sync, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(run_sync, "OUTPUT_DIR", str(out))
    monkeypatch.setattr(run_sync, "SYNC_LOCK_PATH", str(out / ".sync.lock"))
    monkeypatch.setattr(run_sync, "create_driver", lambda: _CerezliSurucu())
    monkeypatch.setattr(run_sync, "login",
                        lambda d: {"method": "cached_session", "captcha_attempts": 0})
    monkeypatch.setattr(run_sync, "run_year_rollover", lambda *a, **k: {
        "year": "2026-2027", "status": "current", "source": "test",
        "archived": False, "manifest": None})
    for name in (
        "scrape_ogrenci_profili", "scrape_ders_programi", "scrape_odevlerim",
        "scrape_takim_calismalari", "scrape_takvim", "scrape_ders_icerikleri",
        "scrape_ogep", "scrape_gelisim_raporu", "scrape_duyurular", "scrape_ek_sayfalar",
    ):
        monkeypatch.setattr(run_sync, name, lambda d, *a, **k: {})
    monkeypatch.setattr("src.scrape_englishcentral.scrape", lambda: None)
    monkeypatch.setattr("src.scrape_achieve3000.scrape", lambda: None)
    monkeypatch.setattr("src.scrape_sebit_homework.scrape", lambda: None)
    monkeypatch.setattr(indir, "ekleri_esitle", ekleri)
    monkeypatch.setattr(run_sync, "perform_incremental_reindex", reindex)
    cwd = os.getcwd()
    try:
        run_sync.main()
    finally:
        os.chdir(cwd)
    return out


def test_basarili_main_eki_kilit_altinda_sagliktan_once_calistirir(tmp_path, monkeypatch):
    olay = []
    alinan = {}
    ozet = {"toplam": 0, "bu_tur_indirilen": 0, "bu_tur_bayt": 0, "kalan_is": 0}

    def sahte(proje_koku, veri, oturum, butce, cerezler=None, **kw):
        # Health is not written yet, and the sync lock is still held. A
        # return above the call skips this; closing the lock file lets us
        # take it; a get_cookies() that nothing reads leaves the jar empty.
        assert not (tmp_path / "output" / "health.json").exists()
        assert not _kilit_alinabilir(run_sync.SYNC_LOCK_PATH)
        alinan["cerezler"] = cerezler
        alinan["kok"] = proje_koku
        olay.append("ek")
        return ozet

    def reindex(project_root):
        olay.append("indeks")
        return {}

    out = _basarili_main(tmp_path, monkeypatch, sahte, reindex)
    assert olay == ["ek", "indeks"]
    assert os.path.abspath(alinan["kok"]) == os.path.abspath(tmp_path)
    assert [c.name for c in (alinan["cerezler"] or [])] == ["ASP.NET_SessionId"]
    with open(out / "health.json", encoding="utf-8") as f:
        health = json.load(f)
    assert health["ekler"] == ozet


def test_cli_kilit_tutuluyken_indirilmez(tmp_path, monkeypatch):
    (tmp_path / "output").mkdir()
    (tmp_path / "output" / "scraped_data.json").write_text("{}", encoding="utf-8")
    kilit_yolu = tmp_path / "output" / ".sync.lock"
    cagrilar = []

    def sahte(*a, **k):
        cagrilar.append(True)
        assert not _kilit_alinabilir(kilit_yolu)
        return {"toplam": 0}

    monkeypatch.setattr(indir, "ekleri_esitle", sahte)
    with open(kilit_yolu, "w") as kilit:
        fcntl.flock(kilit, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert indir.main(["--sure", "5"], kok=tmp_path) == 1
        assert cagrilar == []
    assert indir.main(["--sure", "5"], kok=tmp_path) == 0
    assert cagrilar == [True]
