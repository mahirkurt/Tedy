"""Load environment variables from a .env file."""
import os
import time

# The family, the school and the portal all live on Istanbul time; the host
# does not (Etc/UTC). Every naive `datetime.now()` in TEDY — health stamps,
# "İlk görülme", the sync chip, exam status — was UTC while the portal's times
# and the browser's clock were Istanbul, so a sync from seven minutes earlier
# read "3 saat önce" on Işık's phone (measured 2026-09-24). The zone belongs to
# the application, not to however it was launched: cron, systemd and a manual
# `python src/run_sync.py` all pass through here. A TZ already in the real
# environment still wins, like every other variable in this module.
UYGULAMA_SAAT_DILIMI = "Europe/Istanbul"


def saat_dilimini_kur():
    """Make naive local time Istanbul time for this process and its children
    (chromedriver and Chrome inherit it), unless TZ is already set."""
    os.environ.setdefault("TZ", UYGULAMA_SAAT_DILIMI)
    if hasattr(time, "tzset"):
        time.tzset()


def load_env(path=None):
    """Load key=value pairs from a .env file into os.environ.

    Skips comments (#) and blank lines. Safe if file doesn't exist.

    Uses setdefault rather than a plain assignment so a value already
    present in the real process environment always wins over .env. Without
    this, `.env` silently overrides `FOO=x python ...` on the command line
    and systemd `Environment=` directives, and it defeats
    `monkeypatch.setenv` in tests (a real .env value can leak through and
    run against production instead of the test double).
    """
    if path is None:
        path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", ".env",
        )
    if not os.path.exists(path):
        saat_dilimini_kur()
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
    # After .env, so a TZ written there would win over the default.
    saat_dilimini_kur()
