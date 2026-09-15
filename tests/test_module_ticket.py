"""Viewing tickets: round trip, tampering, expiry, domain separation, roster binding."""
from urllib.parse import parse_qs, urlparse

import pytest

from src import module_ticket as mt

SECRET = b"k" * 32
NOW = 1_800_000_000
BASE = "https://modul.tedy.online"
EMAIL = " IsikKurtx@gmail.com "
TASLAK = "0123456789abcdef"


def _parts(url):
    parsed = urlparse(url)
    q = parse_qs(parsed.query)
    return parsed.path, q["t"][0], q["e"][0], q["u"][0]


def _module():
    out = mt.issue_module(SECRET, BASE, EMAIL, "fen5-su", 2, NOW)
    return out, *_parts(out["url"])


def test_module_ticket_round_trip():
    out, path, t, e, u = _module()
    assert path == "/m/fen5-su/v2"
    assert out["exp"] == NOW + 600 and e == str(NOW + 600)
    assert u == mt.email_hash("isikkurtx@gmail.com") and len(u) == 32
    assert mt.verify(SECRET, "m", "fen5-su", 2, t, e, u, NOW + 599, {u}) is None


def test_draft_ticket_round_trip_and_domain_separation():
    out = mt.issue_draft(SECRET, BASE, EMAIL, TASLAK, NOW)
    path, t, e, u = _parts(out["url"])
    assert path == f"/taslak/{TASLAK}"
    assert mt.verify(SECRET, "t", TASLAK, None, t, e, u, NOW, {u}) is None
    assert mt.verify(SECRET, "m", TASLAK, 1, t, e, u, NOW, {u}) == "imza"
    _, _, mt_t, mt_e, mt_u = _module()
    assert mt.verify(SECRET, "t", "fen5-su", None, mt_t, mt_e, mt_u, NOW, {mt_u}) == "imza"


@pytest.mark.parametrize("field,value,reason", [
    ("ident", "fen5-baska", "imza"),
    ("version", 3, "imza"),
    ("e", str(NOW + 601), "imza"),
    ("secret", b"z" * 32, "imza"),
    ("t", "g" * 64, "imza_bicimi"),
    ("t", "ab", "imza_bicimi"),
    ("u", "Z" * 32, "u_bicimi"),
    ("e", "abc", "exp_bicimi"),
    ("e", "١٢", "exp_bicimi"),
])
def test_tampered_tickets_are_rejected(field, value, reason):
    _, _, t, e, u = _module()
    args = {"secret": SECRET, "ident": "fen5-su", "version": 2, "t": t, "e": e, "u": u}
    args[field] = value
    allowed = {u}
    assert mt.verify(args["secret"], "m", args["ident"], args["version"], args["t"], args["e"],
                     args["u"], NOW, allowed) == reason


def test_swapping_u_to_another_roster_member_breaks_the_mac():
    _, _, t, e, u = _module()
    other = mt.email_hash("drmahirkurt@gmail.com")
    assert mt.verify(SECRET, "m", "fen5-su", 2, t, e, other, NOW, {u, other}) == "imza"


def test_expiry_future_forgery_and_roster():
    _, _, t, e, u = _module()
    assert mt.verify(SECRET, "m", "fen5-su", 2, t, e, u, NOW + 601, {u}) == "suresi_doldu"
    assert mt.verify(SECRET, "m", "fen5-su", 2, t, e, u, NOW, set()) == "yetkisiz"
    far = NOW + 600 + 61
    forged = mt.sign(SECRET, "m", "fen5-su", 2, u, far)
    assert mt.verify(SECRET, "m", "fen5-su", 2, forged, str(far), u, NOW, {u}) == "exp_ileri"


def test_secret_and_identifier_validation():
    with pytest.raises(mt.TicketConfigError):
        mt.issue_module(b"kisa", BASE, EMAIL, "fen5-su", 1, NOW)
    with pytest.raises(ValueError):
        mt.issue_module(SECRET, BASE, EMAIL, "../x", 1, NOW)
    with pytest.raises(ValueError):
        mt.issue_draft(SECRET, BASE, EMAIL, "zz", NOW)


def test_expired_text_is_the_spec_sentence():
    assert mt.EXPIRED_TEXT == "Bağlantının süresi doldu; tedy.online'dan yeniden açın"


# Tests for newline rejection (Ruling 1)
@pytest.mark.parametrize("field,newline_value", [
    ("t", "a" * 64 + "\n"),
    ("u", "a" * 32 + "\n"),
    ("e", str(NOW + 600) + "\n"),
])
def test_fields_with_trailing_newline_are_rejected(field, newline_value):
    """Ensure .fullmatch() is used (not .match()) to reject trailing newlines."""
    _, _, t, e, u = _module()
    args = {"secret": SECRET, "ident": "fen5-su", "version": 2, "t": t, "e": e, "u": u}
    args[field] = newline_value
    allowed = {u if field != "u" else newline_value.rstrip()}

    # The rejection should happen, indicating .fullmatch() is working
    result = mt.verify(args["secret"], "m", args["ident"], args["version"], args["t"], args["e"],
                       args["u"], NOW, allowed)

    if field == "t":
        assert result == "imza_bicimi", f"Expected 'imza_bicimi' for t with newline, got {result}"
    elif field == "u":
        assert result == "u_bicimi", f"Expected 'u_bicimi' for u with newline, got {result}"
    elif field == "e":
        assert result == "exp_bicimi", f"Expected 'exp_bicimi' for e with newline, got {result}"
