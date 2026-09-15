"""Media budget: pricing table, estimate-only ledger, cap with reservations, approval tokens."""
import json
import math
import os
import stat
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.mcp_server import butce
from src.mcp_server.butce import Butce, ButceAsildi, DefterBozuk, Kalem, OnayKullanildi

SECRET = b"f" * 40
EMAIL = "drmahirkurt@gmail.com"
RUN = "abcdef012345"
SEPT = 1_789_000_000.0  # 2026-09-10
OCT = 1_791_600_000.0   # 2026-10-10


def _pricing(verified=True):
    return {
        "minimax.ses": Kalem("minimax.ses", "minimax", "text_to_audio", "karakter", 0.0001, verified, True),
        "minimax.gorsel": Kalem("minimax.gorsel", "minimax", "text_to_image", "adet", 0.01, verified, True),
        "minimax.muzik": Kalem("minimax.muzik", "minimax", "music_generation", "adet", 0.15, verified, False),
    }


def _butce(tmp_path, cap=1.0, clock=lambda: SEPT, verified=True):
    return Butce(tmp_path / "ledger.json", _pricing(verified), cap, SECRET, clock=clock)


def test_shipped_pricing_is_unverified_and_has_no_forbidden_tools():
    table = butce.load_pricing()
    assert {"minimax.ses", "minimax.gorsel", "minimax.muzik", "minimax.video",
            "comfyui.muzik", "comfyui.video"} <= set(table)
    assert all(k.dogrulandi is False for k in table.values())
    assert not {k.arac for k in table.values()} & butce.YASAK_ARACLAR
    assert table["minimax.ses"].otomatik and not table["minimax.muzik"].otomatik


def test_forbidden_tool_in_pricing_is_refused(tmp_path):
    path = tmp_path / "pricing.json"
    path.write_text(json.dumps({"surum": 1, "kalemler": {"minimax.klon": {
        "sunucu": "minimax", "arac": "voice_clone", "birim": "adet", "birim_usd": 1, "dogrulandi": True,
        "otomatik": False}}}), encoding="utf-8")
    with pytest.raises(ValueError):
        butce.load_pricing(path)


def test_estimates_reservations_and_month_rollover(tmp_path):
    now = {"t": SEPT}
    b = _butce(tmp_path, cap=1.0, clock=lambda: now["t"])
    assert b.tahmin("minimax.ses", 3000) == 0.3 and b.otomatik_mi("minimax.ses")
    first = b.rezerve(EMAIL, RUN, "minimax.ses", "ses", 3000, 0.3)
    b.sonuclandir(first, "ok")
    failed = b.rezerve(EMAIL, RUN, "minimax.gorsel", "gorsel", 1, 0.5)
    b.sonuclandir(failed, "hata")
    assert b.harcanan() == 0.3 and b.kalan() == 0.7
    with pytest.raises(ButceAsildi) as exc:
        b.rezerve(EMAIL, RUN, "minimax.muzik", "muzik", 1, 0.8)
    assert exc.value.kalan_usd == 0.7
    assert b.modul_kullanimi(RUN, "minimax.ses") == 3000 and b.modul_kullanimi(RUN, "minimax.gorsel") == 0
    durum = b.durum()
    assert durum["ay"] == "2026-09" and durum["tavan_usd"] == 1.0 and durum["kalan_usd"] == 0.7
    assert "TAHMİN" in durum["not"]
    now["t"] = OCT
    assert b.harcanan() == 0.0 and b.kalan() == 1.0
    entry = json.loads((tmp_path / "ledger.json").read_text(encoding="utf-8"))["kayitlar"][0]
    assert set(entry) == {"id", "ts", "user", "run_id", "server", "kalem", "tur", "miktar", "tahmini_usd",
                          "sonuc", "is_kimligi", "onay"}


def test_unverified_price_is_never_automatic(tmp_path):
    assert _butce(tmp_path, verified=False).otomatik_mi("minimax.ses") is False


def test_concurrent_reservations_never_exceed_the_cap(tmp_path):
    b = _butce(tmp_path, cap=1.0)

    def attempt(_):
        try:
            b.rezerve(EMAIL, RUN, "minimax.gorsel", "gorsel", 1, 0.1)
            return 1
        except ButceAsildi:
            return 0

    with ThreadPoolExecutor(max_workers=20) as pool:
        assert sum(pool.map(attempt, range(20))) == 10
    assert round(b.harcanan(), 4) == 1.0


def test_approval_token_binds_user_run_kind_item_and_request(tmp_path):
    b = _butce(tmp_path)
    token = b.onay_belirteci(EMAIL, RUN, "muzik", "minimax.muzik", "neşeli bir şarkı", 0.15)
    assert b.onay_dogrula(token, EMAIL, RUN, "muzik", "minimax.muzik", "neşeli bir şarkı") == 0.15
    for args in [("isikkurtx@gmail.com", RUN, "muzik", "minimax.muzik", "neşeli bir şarkı"),
                 (EMAIL, "ffffffffffff", "muzik", "minimax.muzik", "neşeli bir şarkı"),
                 (EMAIL, RUN, "video", "minimax.muzik", "neşeli bir şarkı"),
                 (EMAIL, RUN, "muzik", "comfyui.muzik", "neşeli bir şarkı"),
                 (EMAIL, RUN, "muzik", "minimax.muzik", "hüzünlü bir şarkı")]:
        assert b.onay_dogrula(token, *args) is None
    assert b.onay_dogrula("bozuk", EMAIL, RUN, "muzik", "minimax.muzik", "neşeli bir şarkı") is None
    cents, exp, sig = token.split(".")
    assert b.onay_dogrula(f"99999.{exp}.{sig}", EMAIL, RUN, "muzik", "minimax.muzik", "neşeli bir şarkı") is None
    later = Butce(tmp_path / "ledger.json", _pricing(), 1.0, SECRET, clock=lambda: SEPT + 901)
    assert later.onay_dogrula(token, EMAIL, RUN, "muzik", "minimax.muzik", "neşeli bir şarkı") is None


def test_short_secret_is_refused(tmp_path):
    with pytest.raises(ValueError):
        Butce(tmp_path / "l.json", _pricing(), 1.0, b"kisa")


# --- T11-1: defence in depth for the cap — bool/NaN/inf/negative amounts are refused everywhere
# they could otherwise silently defeat the monthly cap. ------------------------------------------

def test_belirsiz_nedenler_are_exactly_the_agreed_reason_codes():
    assert butce.BELIRSIZ_NEDENLER == frozenset({"timeout", "zaman_asimi", "malformed_result",
                                                  "undecodable_json", "unexpected_shape"})


@pytest.mark.parametrize("miktar", [True, float("nan"), float("inf"), -1])
def test_tahmin_rejects_bad_miktar(tmp_path, miktar):
    b = _butce(tmp_path)
    with pytest.raises(ValueError):
        b.tahmin("minimax.ses", miktar)


def test_butce_rejects_non_finite_monthly_cap(tmp_path):
    with pytest.raises(ValueError):
        Butce(tmp_path / "ledger.json", _pricing(), float("inf"), SECRET)


def test_butce_rejects_negative_monthly_cap(tmp_path):
    with pytest.raises(ValueError):
        Butce(tmp_path / "ledger.json", _pricing(), -1.0, SECRET)


def test_load_pricing_rejects_negative_birim_usd(tmp_path):
    path = tmp_path / "pricing.json"
    path.write_text(json.dumps({"surum": 1, "kalemler": {"minimax.ses": {
        "sunucu": "minimax", "arac": "text_to_audio", "birim": "karakter", "birim_usd": -1,
        "dogrulandi": False, "otomatik": True}}}), encoding="utf-8")
    with pytest.raises(ValueError):
        butce.load_pricing(path)


def test_load_pricing_rejects_nan_birim_usd(tmp_path):
    path = tmp_path / "pricing.json"
    raw = json.dumps({"surum": 1, "kalemler": {"minimax.ses": {
        "sunucu": "minimax", "arac": "text_to_audio", "birim": "karakter", "birim_usd": float("nan"),
        "dogrulandi": False, "otomatik": True}}}, allow_nan=True)
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(ValueError):
        butce.load_pricing(path)


@pytest.mark.parametrize("tahmini_usd,miktar", [
    (-0.5, 1),
    (float("nan"), 1),
    (float("inf"), 1),
    (0.1, True),
])
def test_rezerve_rejects_bad_amounts_before_taking_the_lock_or_writing(tmp_path, tahmini_usd, miktar):
    b = _butce(tmp_path)
    with pytest.raises(ValueError):
        b.rezerve(EMAIL, RUN, "minimax.gorsel", "gorsel", miktar, tahmini_usd)
    # No lock file and no ledger row: the reject happens before _locked() is ever entered.
    assert not (tmp_path / "ledger.json").exists()
    assert not (tmp_path / "ledger.json.lock").exists()


@pytest.mark.parametrize("tahmini_usd", [True, float("nan"), float("inf"), -1])
def test_onay_belirteci_rejects_bad_tahmini_usd(tmp_path, tahmini_usd):
    b = _butce(tmp_path)
    with pytest.raises(ValueError):
        b.onay_belirteci(EMAIL, RUN, "muzik", "minimax.muzik", "istek", tahmini_usd)


# --- T11-2: single-use approval tokens; ambiguous ("belirsiz") outcomes still count against the
# cap. ---------------------------------------------------------------------------------------

def test_reservation_with_approval_token_is_single_use(tmp_path):
    b = _butce(tmp_path, cap=10.0)
    token = b.onay_belirteci(EMAIL, RUN, "muzik", "minimax.muzik", "neşeli bir şarkı", 0.15)
    b.rezerve(EMAIL, RUN, "minimax.muzik", "muzik", 1, 0.15, onay_belirteci=token)
    with pytest.raises(OnayKullanildi):
        b.rezerve(EMAIL, RUN, "minimax.muzik", "muzik", 1, 0.15, onay_belirteci=token)


def test_reservations_with_the_same_token_are_serialized_to_exactly_one_success(tmp_path):
    b = _butce(tmp_path, cap=10.0)
    token = b.onay_belirteci(EMAIL, RUN, "muzik", "minimax.muzik", "neşeli bir şarkı", 0.1)

    def attempt(_):
        try:
            b.rezerve(EMAIL, RUN, "minimax.muzik", "muzik", 1, 0.1, onay_belirteci=token)
            return "ok"
        except OnayKullanildi:
            return "used"

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(8)))
    assert results.count("ok") == 1
    assert results.count("used") == 7


def test_approval_token_is_reusable_after_a_failed_reservation(tmp_path):
    b = _butce(tmp_path, cap=10.0)
    token = b.onay_belirteci(EMAIL, RUN, "muzik", "minimax.muzik", "neşeli bir şarkı", 0.15)
    first = b.rezerve(EMAIL, RUN, "minimax.muzik", "muzik", 1, 0.15, onay_belirteci=token)
    b.sonuclandir(first, "hata")
    second = b.rezerve(EMAIL, RUN, "minimax.muzik", "muzik", 1, 0.15, onay_belirteci=token)
    assert second != first


def test_belirsiz_outcome_counts_towards_spending(tmp_path):
    b = _butce(tmp_path, cap=1.0)
    kayit = b.rezerve(EMAIL, RUN, "minimax.gorsel", "gorsel", 1, 0.4)
    b.sonuclandir(kayit, "belirsiz")
    assert b.harcanan() == 0.4
    with pytest.raises(ButceAsildi):
        b.rezerve(EMAIL, RUN, "minimax.gorsel", "gorsel", 1, 0.7)


def test_ledger_never_contains_the_raw_approval_token(tmp_path):
    b = _butce(tmp_path, cap=10.0)
    token = b.onay_belirteci(EMAIL, RUN, "muzik", "minimax.muzik", "neşeli bir şarkı", 0.15)
    b.rezerve(EMAIL, RUN, "minimax.muzik", "muzik", 1, 0.15, onay_belirteci=token)
    raw = (tmp_path / "ledger.json").read_text(encoding="utf-8")
    assert token not in raw


# --- F1: a corrupted/wrong-shaped ledger fails closed (DefterBozuk), never silently resets spend
# to empty. Only a genuinely missing file is treated as "no ledger yet". ------------------------

def _corrupt_row(tahmini_usd=0.1, miktar=1):
    return {"id": "abc", "ts": "2026-09-01T00:00:00+00:00", "user": EMAIL, "run_id": RUN,
            "server": "minimax", "kalem": "minimax.gorsel", "tur": "gorsel", "miktar": miktar,
            "tahmini_usd": tahmini_usd, "sonuc": "ok", "is_kimligi": None, "onay": None}


def _row_missing_miktar():
    row = _corrupt_row()
    del row["miktar"]
    return row


CORRUPT_LEDGERS = [
    ("non_json_text", "not valid json {{{"),
    ("top_level_not_dict", json.dumps([1, 2, 3])),
    ("kayitlar_not_list", json.dumps({"surum": 1, "kayitlar": "x"})),
    ("row_tahmini_usd_null", json.dumps({"surum": 1, "kayitlar": [_corrupt_row(tahmini_usd=None)]})),
    ("row_tahmini_usd_string", json.dumps({"surum": 1, "kayitlar": [_corrupt_row(tahmini_usd="0.5")]})),
    ("row_tahmini_usd_negative", json.dumps({"surum": 1, "kayitlar": [_corrupt_row(tahmini_usd=-1)]})),
    # F7: miktar is validated with the same fail-closed rule as tahmini_usd/ts/sonuc.
    ("row_miktar_string", json.dumps({"surum": 1, "kayitlar": [_corrupt_row(miktar="3")]})),
    ("row_miktar_bool", json.dumps({"surum": 1, "kayitlar": [_corrupt_row(miktar=False)]})),
    ("row_miktar_negative", json.dumps({"surum": 1, "kayitlar": [_corrupt_row(miktar=-1)]})),
    ("row_miktar_nan", json.dumps({"surum": 1, "kayitlar": [_corrupt_row(miktar=float("nan"))]})),
    ("row_miktar_inf", json.dumps({"surum": 1, "kayitlar": [_corrupt_row(miktar=float("inf"))]})),
    ("row_miktar_missing", json.dumps({"surum": 1, "kayitlar": [_row_missing_miktar()]})),
]


@pytest.mark.parametrize("label,content", CORRUPT_LEDGERS, ids=[c[0] for c in CORRUPT_LEDGERS])
def test_corrupt_ledger_fails_closed(tmp_path, label, content):
    ledger_path = tmp_path / "ledger.json"
    ledger_path.write_text(content, encoding="utf-8")
    original_bytes = ledger_path.read_bytes()
    b = _butce(tmp_path, cap=1.0)

    with pytest.raises(DefterBozuk) as exc:
        b.rezerve(EMAIL, RUN, "minimax.gorsel", "gorsel", 1, 0.1)
    assert isinstance(exc.value, ButceAsildi)
    assert ledger_path.read_bytes() == original_bytes  # rezerve raised before any write

    with pytest.raises(DefterBozuk):
        b.harcanan()

    assert b.kalan() == 0.0

    durum = b.durum()
    assert durum["defter_bozuk"] is True
    assert durum["harcanan_tahmini_usd"] is None
    assert durum["kalan_usd"] == 0.0

    assert b.modul_kullanimi(RUN, "minimax.gorsel") == math.inf

    b.sonuclandir("some-id", "ok")  # logs, does not raise, does not write
    assert ledger_path.read_bytes() == original_bytes


def test_missing_ledger_file_still_starts_empty(tmp_path):
    b = _butce(tmp_path, cap=1.0)
    assert b.harcanan() == 0.0
    assert b.kalan() == 1.0
    durum = b.durum()
    assert durum["defter_bozuk"] is False
    assert durum["harcanan_tahmini_usd"] == 0.0
    assert b.modul_kullanimi(RUN, "minimax.gorsel") == 0


# --- F2: the pricing table is typed strictly — no truthy-JSON-value coercion into a real bool,
# no bare KeyError/TypeError escaping for a missing/wrong-typed field. ---------------------------

def _pricing_row(**overrides):
    row = {"sunucu": "minimax", "arac": "text_to_audio", "birim": "karakter", "birim_usd": 0.0001,
           "dogrulandi": False, "otomatik": True}
    row.update(overrides)
    return row


def _write_pricing(tmp_path, row):
    path = tmp_path / "pricing.json"
    path.write_text(json.dumps({"surum": 1, "kalemler": {"minimax.ses": row}}), encoding="utf-8")
    return path


def test_load_pricing_rejects_string_dogrulandi(tmp_path):
    path = _write_pricing(tmp_path, _pricing_row(dogrulandi="false"))
    with pytest.raises(ValueError):
        butce.load_pricing(path)


def test_load_pricing_rejects_non_bool_otomatik(tmp_path):
    path = _write_pricing(tmp_path, _pricing_row(otomatik=1))
    with pytest.raises(ValueError):
        butce.load_pricing(path)


def test_load_pricing_rejects_missing_arac_key_with_value_error_not_key_error(tmp_path):
    row = _pricing_row()
    del row["arac"]
    path = _write_pricing(tmp_path, row)
    with pytest.raises(ValueError):
        butce.load_pricing(path)


def test_load_pricing_rejects_non_string_arac(tmp_path):
    path = _write_pricing(tmp_path, _pricing_row(arac={"x": 1}))
    with pytest.raises(ValueError):
        butce.load_pricing(path)


def test_load_pricing_rejects_a_row_that_is_a_string(tmp_path):
    path = tmp_path / "pricing.json"
    path.write_text(json.dumps({"surum": 1, "kalemler": {"minimax.ses": "not-a-dict"}}), encoding="utf-8")
    with pytest.raises(ValueError):
        butce.load_pricing(path)


def test_shipped_pricing_still_loads_under_strict_typing():
    table = butce.load_pricing()
    assert len(table) >= 6


# --- F3: rezerve() reads the clock exactly once and reuses it for both the cap-check month and
# the row's ts, so the two cannot straddle a month boundary. -------------------------------------

def test_rezerve_reads_the_clock_only_once_per_reservation(tmp_path):
    calls = []

    def clock():
        t = SEPT if not calls else OCT
        calls.append(t)
        return t

    b = Butce(tmp_path / "ledger.json", _pricing(), 1.0, SECRET, clock=clock)
    b.rezerve(EMAIL, RUN, "minimax.gorsel", "gorsel", 1, 0.1)
    assert len(calls) == 1
    entry = json.loads((tmp_path / "ledger.json").read_text(encoding="utf-8"))["kayitlar"][0]
    assert entry["ts"].startswith("2026-09")


# --- F4: the ledger file is chmod 600 after every write, regardless of the process umask. -------

def test_ledger_file_is_chmod_600_after_a_write(tmp_path):
    old_umask = os.umask(0o002)
    try:
        b = _butce(tmp_path, cap=10.0)
        b.rezerve(EMAIL, RUN, "minimax.gorsel", "gorsel", 1, 0.1)
        mode = stat.S_IMODE(os.stat(tmp_path / "ledger.json").st_mode)
        assert mode == 0o600
    finally:
        os.umask(old_umask)


# --- F5: a bool monthly cap is refused, like every other quantity reaching the cap arithmetic. --

def test_bool_monthly_cap_is_refused(tmp_path):
    with pytest.raises(ValueError):
        Butce(tmp_path / "ledger.json", _pricing(), True, SECRET)


# --- F6: an approval token backing a "belirsiz" (ambiguous) outcome is still single-use. --------

def test_approval_token_reuse_after_belirsiz_outcome_is_refused(tmp_path):
    b = _butce(tmp_path, cap=10.0)
    token = b.onay_belirteci(EMAIL, RUN, "muzik", "minimax.muzik", "neşeli bir şarkı", 0.15)
    first = b.rezerve(EMAIL, RUN, "minimax.muzik", "muzik", 1, 0.15, onay_belirteci=token)
    b.sonuclandir(first, "belirsiz")
    with pytest.raises(OnayKullanildi):
        b.rezerve(EMAIL, RUN, "minimax.muzik", "muzik", 1, 0.15, onay_belirteci=token)


# --- F7: modul_kullanimi()'s miktar is validated with the same fail-closed rule as the other
# numeric fields — a corrupt miktar must raise DefterBozuk (-> modul_kullanimi returns math.inf),
# never crash with a raw ValueError, and never silently under-count a falsy `miktar: false` to 0.
# (The corrupt-miktar shapes themselves are folded into CORRUPT_LEDGERS/test_corrupt_ledger_fails_
# closed above — every one of that test's assertions, including modul_kullanimi()==math.inf, runs
# against them too.) ------------------------------------------------------------------------------

def test_modul_kullanimi_sums_valid_rows_correctly_on_a_healthy_ledger(tmp_path):
    b = _butce(tmp_path, cap=10.0)
    first = b.rezerve(EMAIL, RUN, "minimax.ses", "ses", 100, 0.01)
    b.sonuclandir(first, "ok")
    second = b.rezerve(EMAIL, RUN, "minimax.ses", "ses", 50, 0.005)
    b.sonuclandir(second, "ok")
    assert b.modul_kullanimi(RUN, "minimax.ses") == 150
