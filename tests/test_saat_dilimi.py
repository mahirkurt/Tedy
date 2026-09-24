"""TEDY runs on Istanbul time whatever the host's zone is.

The HP host is Etc/UTC. Until 2026-09-24 every naive `datetime.now()` in TEDY
was UTC while the portal's times and the family's browsers were Istanbul, so a
sync seven minutes old read "3 saat önce" on Işık's phone. The zone is set in
`env_loader` (which every entry point loads) and, belt and braces, in both
systemd units and the cron line. Each check runs in a fresh interpreter,
because TZ and tzset() are process-wide.
"""
import os
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent

PROBE = (
    "import sys; sys.path.insert(0, {kok!r});"
    "from src.env_loader import load_env; load_env('/yok/.env');"
    "import datetime, os;"
    "print(os.environ['TZ'], int(datetime.datetime.now().astimezone().utcoffset().total_seconds()))"
)


def _calistir(env_tz=None):
    env = {k: v for k, v in os.environ.items() if k != "TZ"}
    if env_tz is not None:
        env["TZ"] = env_tz
    out = subprocess.run([sys.executable, "-c", PROBE.format(kok=str(KOK))],
                         env=env, capture_output=True, text=True, check=True)
    tz, ofset = out.stdout.split()
    return tz, int(ofset)


def test_tz_yoksa_istanbul_olur():
    tz, ofset = _calistir()
    assert tz == "Europe/Istanbul"
    assert ofset == 3 * 3600


def test_gercek_ortamdaki_tz_kazanir():
    # Same rule as every other variable here: the real environment wins, so
    # a test or an operator can still pin UTC deliberately.
    tz, ofset = _calistir("UTC")
    assert tz == "UTC"
    assert ofset == 0


def test_systemd_birimleri_tz_tasir():
    for birim in ("ted-dashboard.service", "ted-mcp.service"):
        metin = (KOK / birim).read_text(encoding="utf-8")
        assert "Environment=TZ=Europe/Istanbul" in metin, birim
