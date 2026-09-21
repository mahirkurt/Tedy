"""One sync at a time.

Measured 2026-09-21 03:19 on the live machine: six `run_sync` processes and
22 Chrome processes were alive together. Runs take 190-550s and cron fires
every 900s, so they should never meet — but `timeout 600` does not reliably
kill a process blocked in Selenium, and every tick started another one on
top. Six sessions sharing one portal account read each other's pages:
different URLs returned byte-identical text, the Drive previews came back as
zero documents, and scrapers nobody had touched failed with "'list' object
has no attribute 'get'".
"""
import src.run_sync as run_sync


def test_ikinci_kosu_kilidi_alamaz(tmp_path, monkeypatch):
    monkeypatch.setattr(run_sync, "SYNC_LOCK_PATH", str(tmp_path / ".sync.lock"))

    birinci = run_sync._tek_kosu_kilidi()
    assert birinci is not None, "ilk koşu kilidi alabilmeli"

    ikinci = run_sync._tek_kosu_kilidi()
    assert ikinci is None, "ikinci koşu reddedilmeli"

    birinci.close()


def test_kilit_birakilinca_yeniden_alinabilir(tmp_path, monkeypatch):
    # A crashed run must not wedge the schedule: the lock lives on the open
    # file description, so it goes when the process does.
    monkeypatch.setattr(run_sync, "SYNC_LOCK_PATH", str(tmp_path / ".sync.lock"))

    birinci = run_sync._tek_kosu_kilidi()
    assert birinci is not None
    birinci.close()

    ikinci = run_sync._tek_kosu_kilidi()
    assert ikinci is not None, "serbest bırakılan kilit yeniden alınabilmeli"
    ikinci.close()


def test_kilit_dosyasi_pid_yazar(tmp_path, monkeypatch):
    # So a human looking at output/.sync.lock can tell who is holding it.
    import os
    yol = tmp_path / ".sync.lock"
    monkeypatch.setattr(run_sync, "SYNC_LOCK_PATH", str(yol))

    kilit = run_sync._tek_kosu_kilidi()
    assert kilit is not None
    icerik = yol.read_text()
    assert str(os.getpid()) in icerik
    kilit.close()
