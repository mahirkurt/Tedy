"""Media budget: pricing table, estimate-only ledger, cap with reservations, approval tokens."""
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.mcp_server import butce
from src.mcp_server.butce import Butce, ButceAsildi, Kalem, OnayKullanildi

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
