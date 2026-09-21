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


class TestKisaHata:
    """A family reads this string; a Selenium stacktrace is not for them.

    `TimeoutException` stringifies to "Message: \\nStacktrace:\\n#0 0x..." —
    eighteen lines of hex whose first line is empty. The full text still
    goes to scrape_errors for the log.
    """

    def test_selenium_yigin_izi_cumleye_iner(self):
        from selenium.common.exceptions import TimeoutException
        metin = run_sync._kisa_hata(
            TimeoutException("Message: \nStacktrace:\n#0 0x58c8 <unknown>"))
        assert metin == "sayfa beklenen içeriği vermedi"
        assert "0x" not in metin

    def test_anlamli_hata_korunur(self):
        metin = run_sync._kisa_hata(
            AttributeError("'list' object has no attribute 'get'"))
        assert metin == "'list' object has no attribute 'get'"

    def test_bos_hata_da_bir_sey_soyler(self):
        assert run_sync._kisa_hata(Exception("")) == "sayfa beklenen içeriği vermedi"
