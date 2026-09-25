"""After a failed portal login, try again every 5 minutes until one succeeds.

Asked for 2026-09-25, after the 22:00 run of the day before ended "[ERROR]
Login failed, aborting" (five CAPTCHA attempts inside one run) and the next
chance was the next 15-minute cron tick. Cron now ticks every 5 minutes with
`--zamanla`, and the code decides: 15 minutes after the last attempt
normally, 5 after a failed login — every tick — until a login succeeds. The
same day it was first 10; the family asked for 5. A run started by hand
never waits.
"""
import json
from datetime import datetime, timedelta

import pytest

import src.run_sync as run_sync

T0 = datetime(2026, 9, 24, 22, 0, 5)     # a run starts a few seconds after its tick


@pytest.fixture(autouse=True)
def yollar(tmp_path, monkeypatch):
    monkeypatch.setattr(run_sync, "ZAMANLAMA_PATH", str(tmp_path / ".sync_zamanlama.json"))
    monkeypatch.setattr(run_sync, "SYNC_LOCK_PATH", str(tmp_path / ".sync.lock"))
    monkeypatch.setattr(run_sync, "OUTPUT_DIR", str(tmp_path))
    return tmp_path


def _durum(**kw):
    return {"son_deneme": T0.isoformat(), **kw}


def _tik(dk):
    """The cron tick `dk` minutes after the one that started T0's run."""
    return T0.replace(second=0) + timedelta(minutes=dk)


def test_ilk_kosu_hemen():
    assert run_sync._sira_geldi_mi({}, T0)


@pytest.mark.parametrize("dk,beklenen", [(5, False), (10, False), (15, True), (20, True)])
def test_olagan_aralik_15_dakika(dk, beklenen):
    assert run_sync._sira_geldi_mi(_durum(giris_basarisiz=False), _tik(dk)) is beklenen


@pytest.mark.parametrize("dk,beklenen", [(0, False), (5, True), (10, True)])
def test_giris_basarisizsa_5_dakika(dk, beklenen):
    assert run_sync._sira_geldi_mi(_durum(giris_basarisiz=True), _tik(dk)) is beklenen


def test_bozuk_kayit_takvimi_kilitlemez(yollar):
    (yollar / ".sync_zamanlama.json").write_text("{yarım", encoding="utf-8")
    assert run_sync._zamanlama_oku() == {}
    assert run_sync._sira_geldi_mi(run_sync._zamanlama_oku(), T0)


def test_giris_sonucu_ardisik_basarisizligi_sayar_ve_basariyla_sifirlar():
    run_sync._deneme_basladi(T0)
    d = run_sync._giris_sonucu(False, T0)
    assert d["giris_basarisiz"] is True and d["ardisik_basarisiz"] == 1
    run_sync._deneme_basladi(_tik(10))
    d = run_sync._giris_sonucu(False, _tik(10))
    assert d["ardisik_basarisiz"] == 2
    assert d["ilk_basarisiz"] == T0.isoformat()          # since when it has been failing
    assert d["son_deneme"] == _tik(10).isoformat()
    d = run_sync._giris_sonucu(True, _tik(20))
    assert d["giris_basarisiz"] is False and d["ardisik_basarisiz"] == 0
    assert "ilk_basarisiz" not in d


class _Surucu:
    def quit(self):
        pass


def test_zamanlanmis_tik_sirasi_gelmediyse_hicbir_sey_yapmaz(monkeypatch):
    run_sync._deneme_basladi(datetime.now() - timedelta(minutes=5))
    run_sync._giris_sonucu(True, datetime.now() - timedelta(minutes=5))

    def olmamali(*a, **k):
        raise AssertionError("sırası gelmeyen tik tarayıcı açmamalı")
    monkeypatch.setattr(run_sync, "create_driver", olmamali)
    monkeypatch.setattr(run_sync, "_tek_kosu_kilidi", olmamali)
    run_sync.main(zamanla=True)


def test_elle_baslatilan_kosu_beklemez(monkeypatch):
    run_sync._deneme_basladi(datetime.now() - timedelta(minutes=1))

    class Durdu(Exception):
        pass

    def dur(*a, **k):
        raise Durdu()
    monkeypatch.setattr(run_sync, "create_driver", dur)
    with pytest.raises(Durdu):
        run_sync.main()


def test_basarisiz_giris_5_dakika_sonrasini_yazar(monkeypatch, yollar, capsys):
    monkeypatch.setattr(run_sync, "create_driver", lambda: _Surucu())
    monkeypatch.setattr(run_sync, "login", lambda d: None)
    once = datetime.now()
    run_sync.main(zamanla=True)

    d = json.loads((yollar / ".sync_zamanlama.json").read_text(encoding="utf-8"))
    assert d["giris_basarisiz"] is True and d["ardisik_basarisiz"] == 1
    saglik = json.loads((yollar / "health.json").read_text(encoding="utf-8"))
    sonraki = datetime.fromisoformat(saglik["login"]["sonraki_deneme"])
    assert timedelta(minutes=4) < sonraki - once < timedelta(minutes=6)
    assert "5 dakika sonra yeniden denenecek" in capsys.readouterr().out

    # A minute later it waits; the next tick, five minutes on, tries again.
    assert not run_sync._sira_geldi_mi(d, once + timedelta(minutes=1))
    assert run_sync._sira_geldi_mi(d, once + timedelta(minutes=5))


def test_hata_firlatan_giris_de_basarisiz_giristir(monkeypatch, yollar, capsys):
    """scrape_all.login waits 10 s for the login form; with the portal down
    that is a TimeoutException, which crashed the run and left the schedule
    thinking the last login had worked (15 minutes, not 5)."""
    monkeypatch.setattr(run_sync, "create_driver", lambda: _Surucu())

    def zaman_asimi(d):
        raise TimeoutError("Message: \nStacktrace:\n#0 0x55d4")
    monkeypatch.setattr(run_sync, "login", zaman_asimi)
    run_sync.main(zamanla=True)

    d = json.loads((yollar / ".sync_zamanlama.json").read_text(encoding="utf-8"))
    assert d["giris_basarisiz"] is True
    saglik = json.loads((yollar / "health.json").read_text(encoding="utf-8"))
    assert saglik["success"] is False and "sonraki_deneme" in saglik["login"]
    assert "Stacktrace" not in "".join(saglik["scrape_errors"][-1:]).split("\n")[0]
