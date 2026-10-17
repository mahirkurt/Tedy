"""Web push (spec §7): VAPID keys, the subscription store and sending.

Keys are generated once (`python -m src.web_push anahtar-uret`) into .env
through env_prep, never printed. The store is per person (email) and per
device, written under flock because gunicorn runs two workers. A 403/404/410
from the push service means the subscription is dead: it is removed."""
from __future__ import annotations

import base64
import fcntl
import json
import os
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterator, NamedTuple
from urllib.parse import urlsplit

from src.json_utils import atomic_json_dump

BILINEN_PUSH_ALANLARI = ("fcm.googleapis.com", "push.services.mozilla.com", "push.apple.com",
                         "notify.windows.com")
OLU_KODLAR = {403, 404, 410}
TTL = 12 * 3600
VAPID_KONU_VARSAYILAN = "https://tedy.online"
ABONELIKLER = PurePosixPath("output/bildirim_abonelikleri.json")
_ENDPOINT_SINIRI = 2000
_CIHAZ_SINIRI = 80
CIHAZ_SINIRI = 10          # devices kept per person; the oldest goes when an 11th arrives
_B64URL = re.compile(r"^[A-Za-z0-9_-]+={0,2}$")


def _b64(veri: bytes) -> str:
    return base64.urlsafe_b64encode(veri).rstrip(b"=").decode("ascii")


def _b64_bayt(deger: Any) -> bytes | None:
    if not isinstance(deger, str) or not deger or len(deger) > 200 or not _B64URL.match(deger):
        return None
    try:
        return base64.urlsafe_b64decode(deger + "=" * (-len(deger) % 4))
    except (ValueError, TypeError):
        return None


@dataclass(frozen=True)
class VapidAyarlari:
    public: str
    private: str
    subject: str


def vapid_ayarlari() -> VapidAyarlari | None:
    acik = os.environ.get("TEDY_VAPID_PUBLIC", "").strip()
    ozel = os.environ.get("TEDY_VAPID_PRIVATE", "").strip()
    if not acik or not ozel:
        return None
    return VapidAyarlari(acik, ozel, os.environ.get("TEDY_VAPID_SUBJECT", "").strip() or VAPID_KONU_VARSAYILAN)


def anahtar_uret() -> tuple[str, str]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    ozel = ec.generate_private_key(ec.SECP256R1())
    acik = ozel.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return _b64(acik), _b64(ozel.private_numbers().private_value.to_bytes(32, "big"))


def _bilinen_alan(host: str) -> bool:
    return any(host == a or host.endswith("." + a) for a in BILINEN_PUSH_ALANLARI)


def _endpoint_guvenli(endpoint: Any) -> bool:
    """The host must be the same to every parser that may later connect to it.
    urlsplit and urllib3 (what requests uses) disagree on `https://evil\\@fcm.googleapis.com/`,
    so anything that makes the authority ambiguous is refused outright, and the
    host urllib3 would dial must equal the one the allow-list checked."""
    if not isinstance(endpoint, str) or len(endpoint) > _ENDPOINT_SINIRI or not endpoint.isascii():
        return False
    if "\\" in endpoint or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in endpoint):
        return False
    try:
        parca = urlsplit(endpoint)
        if parca.scheme != "https" or not parca.hostname:
            return False
        if parca.username is not None or parca.password is not None or "@" in parca.netloc or ":" in parca.netloc:
            return False
        if not _bilinen_alan(parca.hostname.lower()):
            return False
        from urllib3.util import parse_url
        return (parse_url(endpoint).host or "").lower() == parca.hostname.lower()
    except ValueError:      # urlsplit, port parsing and urllib3's LocationParseError are all ValueErrors
        return False


def abonelik_dogrula(govde: Any) -> dict | None:
    if not isinstance(govde, dict):
        return None
    endpoint = govde.get("endpoint")
    if not _endpoint_guvenli(endpoint):
        return None
    anahtarlar = govde.get("keys") if isinstance(govde.get("keys"), dict) else {}
    p256 = _b64_bayt(anahtarlar.get("p256dh"))
    auth = _b64_bayt(anahtarlar.get("auth"))
    if p256 is None or len(p256) != 65 or auth is None or len(auth) != 16:
        return None
    cihaz = " ".join(str(govde.get("cihaz") or "").split())[:_CIHAZ_SINIRI] or "Tarayıcı"
    return {"endpoint": endpoint, "keys": {"p256dh": anahtarlar["p256dh"], "auth": anahtarlar["auth"]},
            "cihaz": cihaz}


class EkleSonucu(NamedTuple):
    yeni_cihaz: bool    # this endpoint was not among the person's devices
    ilk_cihaz: bool     # the person had no device at all before this call (decided under the lock)


def _gecerli_cihaz(c: Any) -> bool:
    return isinstance(c, dict) and isinstance(c.get("abonelik"), dict) and isinstance(c["abonelik"].get("endpoint"), str)


def _endpoint(c: dict) -> str:
    return c["abonelik"]["endpoint"]


class AbonelikDeposu:
    def __init__(self, yol: str | Path, simdi: Callable[[], datetime] = datetime.now):
        self.yol = Path(yol)
        self.simdi = simdi

    @contextmanager
    def _kilitli(self) -> Iterator[None]:
        self.yol.parent.mkdir(parents=True, exist_ok=True)
        with open(self.yol.with_name(self.yol.name + ".lock"), "a") as kilit:
            fcntl.flock(kilit, fcntl.LOCK_EX)
            yield

    def _oku_ham(self) -> tuple[dict[str, list[dict]], bool]:
        """(people, unreadable). Unreadable means the file exists but is not JSON."""
        try:
            metin = self.yol.read_text(encoding="utf-8")
        except OSError:
            return {}, False
        try:
            veri = json.loads(metin)
        except ValueError:
            return {}, True
        kisiler = veri.get("kisiler") if isinstance(veri, dict) else None
        if not isinstance(kisiler, dict):
            return {}, False
        return {e: [c for c in v if _gecerli_cihaz(c)] for e, v in kisiler.items()
                if isinstance(e, str) and isinstance(v, list)}, False

    def _oku(self) -> dict[str, list[dict]]:
        return self._oku_ham()[0]

    def _oku_yazmak_icin(self) -> dict[str, list[dict]]:
        """Under the lock: an unreadable file is moved aside, never silently overwritten."""
        kisiler, bozuk = self._oku_ham()
        if bozuk:
            yedek = self.yol.with_name(f"{self.yol.name}.bozuk-{self.simdi().strftime('%Y%m%d%H%M%S')}")
            try:
                os.replace(self.yol, yedek)
            except OSError:
                pass
        return kisiler

    def _yaz(self, kisiler: dict[str, list[dict]]) -> None:
        atomic_json_dump({"kisiler": {e: v for e, v in kisiler.items() if v}}, str(self.yol))

    def ekle(self, email: str, abonelik: dict) -> EkleSonucu:
        with self._kilitli():
            kisiler = self._oku_yazmak_icin()
            onceki = kisiler.get(email, [])
            cihazlar = [c for c in onceki if _endpoint(c) != abonelik["endpoint"]]
            sonuc = EkleSonucu(len(cihazlar) == len(onceki), not onceki)
            cihazlar.append({"abonelik": {"endpoint": abonelik["endpoint"], "keys": abonelik["keys"]},
                             "cihaz": abonelik.get("cihaz") or "Tarayıcı",
                             "eklendi": self.simdi().isoformat(timespec="seconds")})
            if len(cihazlar) > CIHAZ_SINIRI:
                cihazlar.sort(key=lambda c: str(c.get("eklendi", "")))     # stable: the new one stays last on a tie
                cihazlar = cihazlar[-CIHAZ_SINIRI:]
            kisiler[email] = cihazlar
            self._yaz(kisiler)
            return sonuc

    def sil(self, email: str, endpoint: str) -> bool:
        with self._kilitli():
            kisiler = self._oku_yazmak_icin()
            once = kisiler.get(email, [])
            sonra = [c for c in once if _endpoint(c) != endpoint]
            if len(sonra) == len(once):
                return False
            kisiler[email] = sonra
            self._yaz(kisiler)
            return True

    def endpoint_sil(self, endpoint: str) -> int:
        with self._kilitli():
            kisiler = self._oku_yazmak_icin()
            silinen = 0
            for email, cihazlar in list(kisiler.items()):
                kalan = [c for c in cihazlar if _endpoint(c) != endpoint]
                silinen += len(cihazlar) - len(kalan)
                kisiler[email] = kalan
            if silinen:
                self._yaz(kisiler)
            return silinen

    def kisinin(self, email: str) -> list[dict]:
        return list(self._oku().get(email, []))

    def hepsi(self) -> dict[str, list[dict]]:
        return {e: v for e, v in self._oku().items() if v}


@dataclass(frozen=True)
class GonderimSonucu:
    durum: str
    kod: int | None
    mesaj: str


def gonder(abonelik: dict, yuk: dict, vapid: VapidAyarlari, webpush_fn: Callable[..., Any] | None = None) -> GonderimSonucu:
    if webpush_fn is None:
        from pywebpush import webpush as webpush_fn
    try:
        yanit = webpush_fn(subscription_info={"endpoint": abonelik.get("endpoint"), "keys": abonelik.get("keys") or {}},
                           data=json.dumps(yuk, ensure_ascii=False), vapid_private_key=vapid.private,
                           vapid_claims={"sub": vapid.subject}, ttl=TTL, timeout=10)
        return GonderimSonucu("ok", getattr(yanit, "status_code", None), "")
    except Exception as e:  # pywebpush.WebPushException, requests errors
        kod = getattr(getattr(e, "response", None), "status_code", None)
        return GonderimSonucu("olu" if kod in OLU_KODLAR else "hata", kod, str(e)[:160])


def main(argv: list[str] | None = None) -> int:
    import argparse
    from src.mcp_server import env_prep
    p = argparse.ArgumentParser(description="TEDY web push")
    alt = p.add_subparsers(dest="komut", required=True)
    uret = alt.add_parser("anahtar-uret", help="VAPID anahtar çiftini .env'e yaz (değer basılmaz)")
    uret.add_argument("--degistir", action="store_true", help="var olan anahtarı değiştir (abonelikler geçersizleşir)")
    a = p.parse_args(argv)
    env = env_prep.PROJECT_ROOT / ".env"
    acik, ozel = anahtar_uret()
    try:
        satirlar = env_prep.read_env(env)
        satirlar = env_prep.set_value(satirlar, "TEDY_VAPID_PUBLIC", acik, replace=a.degistir)
        satirlar = env_prep.set_value(satirlar, "TEDY_VAPID_PRIVATE", ozel, replace=a.degistir)
    except env_prep.EnvPrepError as e:
        print(f"hata: {e}", file=sys.stderr)
        return 1
    env_prep.write_env(env, satirlar)
    print("TEDY_VAPID_PUBLIC ve TEDY_VAPID_PRIVATE .env'e yazıldı; ted-dashboard yeniden başlatılmalı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
