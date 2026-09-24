"""One-off: re-read TEDY's stored UTC timestamps as Istanbul time.

Until 2026-09-24 the host ran on Etc/UTC and TEDY wrote `datetime.now()`
naive, so every stored stamp ("İlk görülme", student "Yaptım" times, health,
private-lesson metadata) is UTC wearing no zone. From that day TEDY runs on
Europe/Istanbul (src/env_loader.py), and a naive stamp means Istanbul time.
This moves the old ones across, once.

What moves, and what does not:
  * Only values shaped like `datetime.now().isoformat()` — seconds with six
    fractional digits. Portal times, user-entered lesson times and dates
    never carry microseconds, so they are never touched.
  * Only values at or before the current UTC time. A stamp written after the
    switch is Istanbul time and therefore ahead of UTC now; shifting it would
    double-count. This is what makes the script safe to run while a sync
    that started under the new zone has already written its stamps.
  * Only top-level output/*.json. Sealed year archives are history as they
    were written and stay as they are; append-only logs are left alone.

Safety: dry run unless --uygula; takes output/.sync.lock so no sync writes
underneath it; copies every file it changes to output/saat_dilimi_gocu_yedek/
first; writes output/.saat_dilimi_gocu.json and refuses to run a second time.

    .venv/bin/python scripts/saat_dilimi_gocu.py            # what would change
    .venv/bin/python scripts/saat_dilimi_gocu.py --uygula   # do it
"""
import argparse
import fcntl
import glob
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
from src.json_utils import atomic_json_dump  # noqa: E402

CIKTI = os.path.join(KOK, "output")
ISARET = os.path.join(CIKTI, ".saat_dilimi_gocu.json")
YEDEK = os.path.join(CIKTI, "saat_dilimi_gocu_yedek")
KILIT = os.path.join(CIKTI, ".sync.lock")
ISTANBUL = ZoneInfo("Europe/Istanbul")
DAMGA = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}$")


def kaydir(deger, utc_simdi):
    """The Istanbul reading of a naive UTC stamp, or None if it stays."""
    if not isinstance(deger, str) or not DAMGA.match(deger):
        return None
    try:
        t = datetime.fromisoformat(deger)
    except ValueError:
        return None
    if t > utc_simdi:
        return None  # written after the switch: already Istanbul time
    return t.replace(tzinfo=timezone.utc).astimezone(ISTANBUL).replace(tzinfo=None).isoformat()


def gez(o, utc_simdi, sayac):
    if isinstance(o, dict):
        return {k: gez(v, utc_simdi, sayac) for k, v in o.items()}
    if isinstance(o, list):
        return [gez(v, utc_simdi, sayac) for v in o]
    yeni = kaydir(o, utc_simdi)
    if yeni is None:
        return o
    sayac[0] += 1
    return yeni


def kilit_al(saniye=900):
    f = open(KILIT, "a+")
    bitis = time.time() + saniye
    while True:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return f
        except OSError:
            if time.time() > bitis:
                sys.exit("Senkron kilidi 15 dakikada boşalmadı; hiçbir şey değişmedi.")
            time.sleep(5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uygula", action="store_true", help="dosyalara yaz")
    args = ap.parse_args()

    if os.path.exists(ISARET):
        sys.exit(f"Göç zaten yapılmış: {ISARET}. İkinci kez kaydırmak saatleri bozardı.")

    kilit = kilit_al() if args.uygula else None
    try:
        # Re-read UTC now after the lock: a sync may have run while we waited.
        utc_simdi = datetime.now(timezone.utc).replace(tzinfo=None)
        rapor = {}
        for yol in sorted(glob.glob(os.path.join(CIKTI, "*.json"))):
            try:
                with open(yol, encoding="utf-8") as fh:
                    veri = json.load(fh)
            except (OSError, ValueError):
                continue
            sayac = [0]
            yeni = gez(veri, utc_simdi, sayac)
            if not sayac[0]:
                continue
            ad = os.path.basename(yol)
            rapor[ad] = sayac[0]
            print(f"{'kaydırıldı' if args.uygula else 'kayacak'}: {sayac[0]:>4}  {ad}")
            if args.uygula:
                os.makedirs(YEDEK, exist_ok=True)
                shutil.copy2(yol, os.path.join(YEDEK, ad))
                atomic_json_dump(yeni, yol)
        if args.uygula:
            atomic_json_dump({
                "yapildi_utc": utc_simdi.isoformat(),
                "kural": "naive UTC (mikrosaniyeli, UTC şimdi'den önce) -> Europe/Istanbul",
                "dosyalar": rapor,
                "yedek": os.path.relpath(YEDEK, KOK),
            }, ISARET)
            print(f"İşaret yazıldı: {os.path.relpath(ISARET, KOK)}")
        else:
            print("Kuru çalıştırma — yazmak için --uygula.")
    finally:
        if kilit:
            kilit.close()


if __name__ == "__main__":
    main()
