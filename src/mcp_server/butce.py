"""Media budget (spec §8; plan K-P11, K-P13): estimate-only ledger, monthly cap, approval tokens.

No provider returns a real cost, so every amount is an estimate from pricing.json and says so.
Spending is reserved under an inter-process lock before the provider call ("basladi") and settled
afterwards ("ok" | "hata" | "belirsiz" — an ambiguous outcome, e.g. a provider timeout or a
malformed result where we cannot tell whether the vendor actually charged us, still counts against
the cap because we cannot prove it did not), so concurrent tool calls cannot overshoot the cap.

Every amount that reaches the cap arithmetic (a pricing row's birim_usd, a tahmin()/rezerve()
miktar or tahmini_usd, an onay_belirteci() tahmini_usd) is validated as a genuine, non-negative,
finite number before it is used anywhere — defence in depth for the cap, since a bool, NaN or
infinite value would otherwise silently defeat it (True == 1 but is not a quantity; NaN compares
false to every bound; inf never trips a <= check the way a huge-but-finite number would).

Approval tokens (onay_belirteci/onay_dogrula) are short-lived HMAC-signed receipts binding a
user+run+kind+item+request to an estimated amount, so a human approval cannot be replayed for a
different request. When such a token is handed to rezerve(), the reservation ledger also enforces
single use: the same token digest may not back a second reservation while the first is still
"basladi", "ok", or "belirsiz" (a "hata" row does not block reuse — that reservation is void).

A ledger file that exists but is unreadable or wrong-shaped (disk fault, bad backup restore, a
maintainer's stray edit) is not the same thing as no ledger yet: `_read()` only treats a missing
file as "first run"; anything else that fails to parse into the expected shape raises
`DefterBozuk` (a `ButceAsildi` subclass) so every caller fails closed — the cap is reported
exhausted rather than silently reset to empty. See `DefterBozuk` and `_read()` below.
"""
from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import logging
import math
import os
import secrets
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from src.json_utils import atomic_json_dump
from src.module_ticket import email_hash

logger = logging.getLogger(__name__)

PRICING_PATH = Path(__file__).resolve().parent / "pricing.json"
ONAY_TTL_SECONDS = 900
LEDGER_NAME = "edupedia_media_ledger.json"
TAHMIN_NOTU = ("Tutarlar sağlayıcı fiyat tablosundan hesaplanan TAHMİNDİR; hiçbir sunucu gerçek maliyet "
               "döndürmez. Fatura bu tahminden sapabilir.")
YASAK_ARACLAR = frozenset({"voice_clone", "voice_design"})

# Outcomes a caller cannot resolve to a definite ok/hata — e.g. the provider call timed out, or its
# result could not be parsed/shaped as expected. Treated as spent (see module docstring) because we
# cannot prove the vendor did not charge us. Tasks 13/14 pass one of these to sonuclandir(...,"belirsiz").
BELIRSIZ_NEDENLER = frozenset({"timeout", "zaman_asimi", "malformed_result", "undecodable_json",
                                "unexpected_shape"})
_COUNTED = ("basladi", "ok", "belirsiz")


@dataclass(frozen=True)
class Kalem:
    anahtar: str
    sunucu: str
    arac: str
    birim: str
    birim_usd: float
    dogrulandi: bool
    otomatik: bool


class ButceAsildi(Exception):
    def __init__(self, kalan_usd: float, tahmini_usd: float) -> None:
        super().__init__("budget_exceeded")
        self.kalan_usd = kalan_usd
        self.tahmini_usd = tahmini_usd


class DefterBozuk(ButceAsildi):
    """Raised by _read() when the ledger file exists but is unreadable or wrong-shaped.

    A ButceAsildi subclass so every existing `except ButceAsildi` caller already treats this as
    "budget exhausted" — fail closed, never silently reset to an empty (and therefore fully
    unspent) ledger. `.reason` names the cause for logging/metrics; `.kalan_usd`/`.tahmini_usd`
    (inherited) are always 0.0 since no real amount is known.
    """

    def __init__(self) -> None:
        super().__init__(0.0, 0.0)
        self.reason = "defter_bozuk"


class OnayKullanildi(Exception):
    """Raised by rezerve() when the same approval token digest already backs a counted row."""


def _validate_amount(value: Any, name: str) -> float:
    """A genuine, finite, non-negative quantity — rejects bool (True/False are not quantities,
    but Python happily coerces them to 1.0/0.0), NaN (compares false to every bound, so a naive
    `<=` cap check would let it through) and +/-inf (never trips a finite bound)."""
    if isinstance(value, bool):
        raise ValueError(f"{name} bool olamaz")
    try:
        amount = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} sayısal olmalı") from None
    if not math.isfinite(amount) or amount < 0:
        raise ValueError(f"{name} sonlu ve negatif olmayan bir sayı olmalı")
    return amount


_KALEM_REQUIRED_FIELDS = ("sunucu", "arac", "birim", "birim_usd", "dogrulandi", "otomatik")


def _ledger_row_ok(row: Any) -> bool:
    """A row read back from disk is well-formed: a dict with string ts/sonuc and a tahmini_usd
    that is a genuine, finite, non-negative int or float (bool excluded, same reasoning as
    _validate_amount). Used only to validate what comes off disk in _read() — rows this process
    itself appends are always built to satisfy this by construction."""
    if not isinstance(row, dict):
        return False
    if not isinstance(row.get("ts"), str) or not isinstance(row.get("sonuc"), str):
        return False
    tahmini_usd = row.get("tahmini_usd")
    if isinstance(tahmini_usd, bool) or not isinstance(tahmini_usd, (int, float)):
        return False
    return math.isfinite(tahmini_usd) and tahmini_usd >= 0


def load_pricing(path: Path = PRICING_PATH) -> dict[str, Kalem]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    kalemler = data.get("kalemler", {})
    if not isinstance(kalemler, dict):
        raise ValueError("kalemler bir sözlük olmalı")
    table = {}
    for key, row in kalemler.items():
        if not isinstance(row, dict):
            raise ValueError(f"{key}: kalem bir sözlük olmalı")
        for field in _KALEM_REQUIRED_FIELDS:
            if field not in row:
                raise ValueError(f"{key}: '{field}' alanı eksik")
        arac = row["arac"]
        if not isinstance(arac, str) or not arac:
            raise ValueError(f"{key}: arac boş olmayan bir metin olmalı")
        if arac in YASAK_ARACLAR:
            raise ValueError(f"yasak araç fiyat tablosunda: {arac}")
        sunucu = row["sunucu"]
        if not isinstance(sunucu, str) or not sunucu:
            raise ValueError(f"{key}: sunucu boş olmayan bir metin olmalı")
        birim = row["birim"]
        if not isinstance(birim, str) or not birim:
            raise ValueError(f"{key}: birim boş olmayan bir metin olmalı")
        birim_usd = _validate_amount(row["birim_usd"], f"{key}.birim_usd")
        dogrulandi = row["dogrulandi"]
        if not isinstance(dogrulandi, bool):
            raise ValueError(f"{key}: dogrulandi tam olarak bool olmalı")
        otomatik = row["otomatik"]
        if not isinstance(otomatik, bool):
            raise ValueError(f"{key}: otomatik tam olarak bool olmalı")
        table[key] = Kalem(key, sunucu, arac, birim, birim_usd, dogrulandi, otomatik)
    return table


class Butce:
    def __init__(self, ledger_path: Path | str, pricing: dict[str, Kalem], monthly_usd: float, secret: bytes,
                 clock: Callable[[], float] = time.time) -> None:
        if not isinstance(secret, (bytes, bytearray)) or len(secret) < 32:
            raise ValueError("approval secret must be at least 32 bytes")
        if isinstance(monthly_usd, bool):
            raise ValueError("monthly_usd bool olamaz")
        try:
            monthly = float(monthly_usd)
        except (TypeError, ValueError):
            raise ValueError("monthly_usd sayısal olmalı") from None
        if not math.isfinite(monthly) or monthly < 0:
            raise ValueError("monthly_usd sonlu ve negatif olmayan bir sayı olmalı")
        self.path = Path(ledger_path)
        self.lock_path = self.path.with_name(self.path.name + ".lock")
        self.pricing = pricing
        self.monthly_usd = monthly
        self.secret = bytes(secret)
        self.clock = clock

    @contextmanager
    def _locked(self) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _read(self) -> dict[str, Any]:
        """Only a genuinely missing file means "no ledger yet". Anything else that fails to
        parse into the expected shape (unreadable, malformed JSON, wrong top-level shape, a
        non-dict row, or a row whose ts/sonuc/tahmini_usd is not the type it must be) raises
        DefterBozuk instead of silently normalizing to an empty ledger — an empty ledger reports
        the whole month as unspent, which is exactly the wrong direction for a spending cap to
        fail in."""
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {"surum": 1, "kayitlar": []}
        except OSError:
            raise DefterBozuk() from None
        try:
            data = json.loads(raw)
        except ValueError:
            raise DefterBozuk() from None
        if not isinstance(data, dict):
            raise DefterBozuk()
        kayitlar = data.get("kayitlar")
        if not isinstance(kayitlar, list) or not all(_ledger_row_ok(row) for row in kayitlar):
            raise DefterBozuk()
        return data

    def _month(self, now: float | None = None) -> str:
        ts = self.clock() if now is None else now
        return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m")

    def kalem(self, anahtar: str) -> Kalem:
        return self.pricing[anahtar]

    def tahmin(self, anahtar: str, miktar: float) -> float:
        amount = _validate_amount(miktar, "miktar")
        return round(self.pricing[anahtar].birim_usd * amount, 4)

    def otomatik_mi(self, anahtar: str) -> bool:
        k = self.pricing.get(anahtar)
        return bool(k and k.otomatik and k.dogrulandi)

    def _spent(self, rows: list[dict[str, Any]], now: float | None = None) -> float:
        month = self._month(now)
        return round(sum(float(r.get("tahmini_usd") or 0) for r in rows
                         if str(r.get("ts", "")).startswith(month) and r.get("sonuc") in _COUNTED), 4)

    def harcanan(self) -> float:
        """Propagates DefterBozuk — the caller decides how to fail closed (see kalan/durum)."""
        return self._spent(self._read()["kayitlar"])

    def kalan(self) -> float:
        try:
            spent = self.harcanan()
        except DefterBozuk:
            return 0.0
        return round(max(0.0, self.monthly_usd - spent), 4)

    def durum(self) -> dict[str, Any]:
        base = {"ay": self._month(), "tavan_usd": self.monthly_usd, "not": TAHMIN_NOTU}
        try:
            spent = self.harcanan()
        except DefterBozuk:
            return {**base, "harcanan_tahmini_usd": None, "kalan_usd": 0.0, "defter_bozuk": True}
        return {**base, "harcanan_tahmini_usd": spent,
                "kalan_usd": round(max(0.0, self.monthly_usd - spent), 4), "defter_bozuk": False}

    def modul_kullanimi(self, run_id: str, anahtar: str) -> float:
        try:
            rows = self._read()["kayitlar"]
        except DefterBozuk:
            return math.inf
        return sum(float(r.get("miktar") or 0) for r in rows
                   if r.get("run_id") == run_id and r.get("kalem") == anahtar and r.get("sonuc") == "ok")

    def rezerve(self, email: str, run_id: str, anahtar: str, tur: str, miktar: float, tahmini_usd: float,
                onay_belirteci: str | None = None) -> str:
        miktar_v = _validate_amount(miktar, "miktar")
        tahmini_usd_v = _validate_amount(tahmini_usd, "tahmini_usd")
        onay_digest = (hashlib.sha256(onay_belirteci.encode("utf-8")).hexdigest()[:32]
                       if onay_belirteci is not None else None)
        now = self.clock()  # one read, reused below for both the cap-check month and the row's ts
        with self._locked():
            data = self._read()  # lets DefterBozuk propagate — nothing below has written yet
            if onay_digest is not None:
                for row in data["kayitlar"]:
                    if row.get("onay") == onay_digest and row.get("sonuc") in _COUNTED:
                        raise OnayKullanildi("onay belirteci zaten kullanıldı")
            remaining = round(max(0.0, self.monthly_usd - self._spent(data["kayitlar"], now)), 4)
            if tahmini_usd_v > remaining + 1e-9:
                raise ButceAsildi(remaining, tahmini_usd_v)
            entry_id = secrets.token_hex(8)
            data["kayitlar"].append({
                "id": entry_id, "ts": datetime.fromtimestamp(now, timezone.utc).isoformat(timespec="seconds"),
                "user": email, "run_id": run_id, "server": self.pricing[anahtar].sunucu, "kalem": anahtar, "tur": tur,
                "miktar": miktar_v, "tahmini_usd": round(tahmini_usd_v, 4), "sonuc": "basladi", "is_kimligi": None,
                "onay": onay_digest,
            })
            atomic_json_dump(data, str(self.path))
            os.chmod(self.path, 0o600)
            return entry_id

    def sonuclandir(self, kayit_id: str, sonuc: str, is_kimligi: str | None = None) -> None:
        if sonuc not in ("ok", "hata", "basladi", "belirsiz"):
            raise ValueError("sonuc")
        with self._locked():
            try:
                data = self._read()
            except DefterBozuk:
                logger.error("medya defteri bozuk; sonuç yazılamadı (kayit_id=%s)", kayit_id)
                return
            for row in data["kayitlar"]:
                if row.get("id") == kayit_id:
                    row["sonuc"] = sonuc
                    if is_kimligi is not None:
                        row["is_kimligi"] = is_kimligi
            atomic_json_dump(data, str(self.path))
            os.chmod(self.path, 0o600)

    def _mac(self, email: str, run_id: str, tur: str, anahtar: str, istek: str, cents: int, exp: int) -> str:
        digest = hashlib.sha256(istek.encode("utf-8")).hexdigest()[:16]
        message = f"onay|{email_hash(email)}|{run_id}|{tur}|{anahtar}|{digest}|{cents}|{exp}".encode("utf-8")
        return hmac.new(self.secret, message, hashlib.sha256).hexdigest()

    def onay_belirteci(self, email: str, run_id: str, tur: str, anahtar: str, istek: str, tahmini_usd: float) -> str:
        tahmini_usd_v = _validate_amount(tahmini_usd, "tahmini_usd")
        cents = int(round(tahmini_usd_v * 10000))
        exp = int(self.clock()) + ONAY_TTL_SECONDS
        return f"{cents}.{exp}.{self._mac(email, run_id, tur, anahtar, istek, cents, exp)}"

    def onay_dogrula(self, token: Any, email: str, run_id: str, tur: str, anahtar: str, istek: str) -> float | None:
        try:
            cents_s, exp_s, sig = str(token).split(".")
            cents, exp = int(cents_s), int(exp_s)
        except ValueError:
            return None
        now = int(self.clock())
        if exp < now or exp > now + ONAY_TTL_SECONDS + 60 or cents < 0:
            return None
        if not hmac.compare_digest(self._mac(email, run_id, tur, anahtar, istek, cents, exp), sig):
            return None
        return cents / 10000
