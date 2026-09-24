"""The one-off UTC -> Istanbul migration moves exactly what it should."""
import importlib.util
import json
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("gocu", KOK / "scripts" / "saat_dilimi_gocu.py")
gocu = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gocu)

SIMDI = datetime(2026, 9, 24, 11, 40, 0)   # UTC now at migration time


def test_bizim_damgamiz_uc_saat_ileri():
    assert gocu.kaydir("2026-09-24T05:34:28.169324", SIMDI) == "2026-09-24T08:34:28.169324"


def test_gun_donumunu_dogru_gecer():
    assert gocu.kaydir("2026-03-11T23:29:16.479863", SIMDI) == "2026-03-12T02:29:16.479863"


def test_portal_ve_kullanici_saatleri_dokunulmaz():
    # No microseconds: not ours. Portal times, "Z" times, deadlines, dates.
    for deger in ("2026-09-24T12:40:00", "2026-09-24T12:40:00Z", "25.09.2026 12:00",
                  "2026-09-24", "12:40", "2026-09-24T12:40:00.000000+03:00"):
        assert gocu.kaydir(deger, SIMDI) is None, deger


def test_gecisten_sonra_yazilan_iki_kez_kaymaz():
    # Written under the new zone: Istanbul time, so ahead of UTC now.
    assert gocu.kaydir("2026-09-24T14:39:00.123456", SIMDI) is None


def test_ic_ice_yapida_sayar_ve_kaydirir():
    sayac = [0]
    veri = {"marks": {"matematik|x|25.09.2026 12:00": "2026-09-22T17:26:17.130481"},
            "updated_at": "2026-09-22T17:26:17.130495",
            "rows": [{"start": "2026-09-24T12:40:00Z", "created_at": "2026-03-12T16:18:03.869496"}]}
    yeni = gocu.gez(veri, SIMDI, sayac)
    assert sayac[0] == 3
    assert yeni["marks"]["matematik|x|25.09.2026 12:00"] == "2026-09-22T20:26:17.130481"
    assert yeni["rows"][0]["start"] == "2026-09-24T12:40:00Z"
    # Keys are data, not stamps — never rewritten.
    assert list(yeni["marks"]) == ["matematik|x|25.09.2026 12:00"]


def test_ikinci_kez_calismayi_reddeder(tmp_path, monkeypatch, capsys):
    isaret = tmp_path / ".saat_dilimi_gocu.json"
    isaret.write_text(json.dumps({"yapildi_utc": "x"}))
    monkeypatch.setattr(gocu, "ISARET", str(isaret))
    monkeypatch.setattr("sys.argv", ["gocu", "--uygula"])
    try:
        gocu.main()
    except SystemExit as e:
        assert "zaten" in str(e)
    else:
        raise AssertionError("ikinci çalıştırma reddedilmedi")
