"""Google identity (S1a / F1): credential shape gate, cached signing certs, short fetch timeout."""
import datetime
import threading
import time

import pytest
import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from google.auth import crypt, jwt
from google.auth import exceptions as google_exceptions
from google.auth import transport

from src import roles
from src.mcp_server import google_identity
from src.mcp_server.google_identity import GoogleCertCache, IdentityError, verify_google_credential

FULL = "drmahirkurt@gmail.com"
NONCE = "nonce-1"

# Every one of these must be refused before any network or verifier work.
MALFORMED_CREDENTIALS = [
    "not-a-jwt",
    "a.b",
    "a.b.c.d",
    pytest.param("a" * 4093 + ".b.c", id="4097-bytes"),
    "a.b+c.d",
    "a.b/c.d",
    "a.b=.c",
    "a.b c.d",
    "a.bü.c",
    "a.b.c\n",
    "a..c",
    ".b.c",
    "a.b.",
    "",
]


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _signer_and_certs(kid: str):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ted-mcp-test-google-certs")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    pem_key = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption())
    return crypt.RSASigner.from_string(pem_key, key_id=kid), {kid: cert.public_bytes(serialization.Encoding.PEM).decode()}


@pytest.fixture(scope="module")
def google_keys():
    signer, certs = _signer_and_certs("k1")
    impostor, _ = _signer_and_certs("k1")  # same key id, different key
    return signer, impostor, certs


def _id_token(signer, **claims) -> str:
    now = int(time.time())
    payload = {"iss": "https://accounts.google.com", "aud": roles.GOOGLE_CLIENT_ID, "iat": now - 5,
               "exp": now + 600, "email": "DrMahirKurt@gmail.com", "email_verified": True, "nonce": NONCE}
    payload.update(claims)
    return jwt.encode(signer, payload).decode("ascii")


class CountingFetch:
    def __init__(self, certs, max_age=300, error=None):
        self.certs, self.max_age, self.error = certs, max_age, error
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.certs, self.max_age


class FakeResponse(transport.Response):
    def __init__(self, status=200, headers=None, data=b"{}"):
        self._status, self._headers, self._data = status, headers or {}, data

    @property
    def status(self):
        return self._status

    @property
    def headers(self):
        return self._headers

    @property
    def data(self):
        return self._data


class FakeTransport(transport.Request):
    def __init__(self, response):
        self.response = response
        self.calls = []

    def __call__(self, url, method="GET", body=None, headers=None, timeout=None, **kwargs):
        self.calls.append({"url": url, "method": method, "timeout": timeout})
        return self.response


# -- F1.2 credential shape -------------------------------------------------------------

@pytest.mark.parametrize("credential", MALFORMED_CREDENTIALS)
def test_malformed_credential_is_invalid_token_without_fetching_certs(credential):
    fetch = CountingFetch({})
    with pytest.raises(IdentityError) as exc:
        verify_google_credential(credential, NONCE, cert_cache=GoogleCertCache(fetch=fetch, clock=Clock()))
    assert exc.value.reason == "invalid_token"
    assert fetch.calls == 0


def test_credential_shape_accepts_three_base64url_segments_up_to_4096_bytes():
    assert google_identity.is_well_formed_credential("eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxIn0.c2ln-_")
    assert google_identity.is_well_formed_credential("a" * 4092 + ".b.c")  # exactly 4096
    assert not google_identity.is_well_formed_credential("a" * 4093 + ".b.c")
    for bad in MALFORMED_CREDENTIALS:
        value = bad.values[0] if hasattr(bad, "values") else bad
        assert not google_identity.is_well_formed_credential(value)


# -- F1.3 cached certs on the real verification path -------------------------------------

def test_default_verifier_checks_the_signature_against_cached_certs(google_keys):
    signer, impostor, certs = google_keys
    cache = GoogleCertCache(fetch=CountingFetch(certs), clock=Clock())
    assert verify_google_credential(_id_token(signer), NONCE, cert_cache=cache) == FULL
    for token, reason in [
        (_id_token(impostor), "invalid_token"),
        (_id_token(signer, aud="someone-else.apps.googleusercontent.com"), "invalid_token"),
        (_id_token(signer, iss="https://evil.example"), "invalid_token"),
        (_id_token(signer, exp=int(time.time()) - 60), "invalid_token"),
        (_id_token(signer, email_verified=False), "email_not_verified"),
        (_id_token(signer, nonce="other"), "nonce_mismatch"),
    ]:
        with pytest.raises(IdentityError) as exc:
            verify_google_credential(token, NONCE, cert_cache=cache)
        assert exc.value.reason == reason


def test_certs_are_fetched_once_per_max_age_window(google_keys):
    signer, _, certs = google_keys
    clock, fetch = Clock(), CountingFetch(certs, max_age=300)
    cache = GoogleCertCache(fetch=fetch, clock=clock)
    token = _id_token(signer)
    assert verify_google_credential(token, NONCE, cert_cache=cache) == FULL
    clock.now += 299
    assert verify_google_credential(token, NONCE, cert_cache=cache) == FULL
    assert fetch.calls == 1
    clock.now += 1  # window elapsed
    assert verify_google_credential(token, NONCE, cert_cache=cache) == FULL
    assert fetch.calls == 2


def test_concurrent_first_fetches_collapse_into_one(google_keys):
    _, _, certs = google_keys
    entered, release, second_fetch = threading.Event(), threading.Event(), threading.Event()
    calls = []

    def slow_fetch():
        calls.append(1)
        if len(calls) > 1:
            second_fetch.set()
        entered.set()
        release.wait(10)
        return certs, 300

    cache = GoogleCertCache(fetch=slow_fetch, clock=Clock())
    results, started = [], [threading.Event() for _ in range(4)]

    def worker(i):
        started[i].set()
        results.append(cache.certs())

    first = threading.Thread(target=worker, args=(0,))
    first.start()
    others = [threading.Thread(target=worker, args=(i,)) for i in range(1, 4)]
    try:
        assert entered.wait(5)
        for t in others:
            t.start()
        assert all(s.wait(5) for s in started)
        # Without the lock the waiting threads would each start their own fetch at once.
        assert not second_fetch.wait(0.2)
    finally:
        release.set()
        for t in [first, *others]:
            t.join(10)
    assert len(calls) == 1
    assert results == [certs] * 4


def test_fetch_failure_is_google_unreachable_and_shared_by_callers_right_behind_it(google_keys):
    signer, _, certs = google_keys
    clock = Clock()
    fetch = CountingFetch(certs, error=google_exceptions.TransportError("no route to googleapis.com"))
    cache = GoogleCertCache(fetch=fetch, clock=clock)
    token = _id_token(signer)
    for _ in range(2):
        with pytest.raises(IdentityError) as exc:
            verify_google_credential(token, NONCE, cert_cache=cache)
        assert exc.value.reason == "google_unreachable"
    assert fetch.calls == 1  # the caller right behind a failed fetch does not refetch
    clock.now += google_identity.CERT_FETCH_RETRY_AFTER_SECONDS
    fetch.error = None
    assert verify_google_credential(token, NONCE, cert_cache=cache) == FULL
    assert fetch.calls == 2


def test_expired_certs_are_not_served_when_the_refetch_fails(google_keys):
    signer, _, certs = google_keys
    clock, fetch = Clock(), CountingFetch(certs, max_age=60)
    cache = GoogleCertCache(fetch=fetch, clock=clock)
    token = _id_token(signer)
    assert verify_google_credential(token, NONCE, cert_cache=cache) == FULL
    clock.now += 60
    fetch.error = google_exceptions.TransportError("down")
    with pytest.raises(IdentityError) as exc:
        verify_google_credential(token, NONCE, cert_cache=cache)
    assert exc.value.reason == "google_unreachable"


# -- F1.3 the real fetch: timeout, Cache-Control, payload -------------------------------

def test_real_cert_fetch_timeout_is_at_most_five_seconds(monkeypatch):
    seen = {}

    def refuse(self, method, url, **kwargs):
        seen.update(method=method, url=url, timeout=kwargs.get("timeout"))
        raise requests.exceptions.ConnectionError("network-free test")

    monkeypatch.setattr(requests.Session, "request", refuse)
    with pytest.raises(google_exceptions.TransportError):
        google_identity.fetch_google_certs()
    assert seen["url"] == google_identity.GOOGLE_CERTS_URL
    assert seen["timeout"] is not None and 0 < seen["timeout"] <= 5
    assert 0 < google_identity.CERT_FETCH_TIMEOUT_SECONDS <= 5


@pytest.mark.parametrize("headers,max_age", [
    ({"Cache-Control": "public, max-age=19137, must-revalidate, no-transform"}, 19137),
    ({"cache-control": "max-age=60"}, 60),
    ({}, 3600),
    ({"Cache-Control": "no-cache"}, 3600),
    ({"Cache-Control": "max-age=soon"}, 3600),
])
def test_cert_fetch_honours_max_age_or_defaults_to_an_hour(headers, max_age):
    fake = FakeTransport(FakeResponse(200, headers, b'{"k1": "-----BEGIN CERTIFICATE-----"}'))
    certs, got = google_identity.fetch_google_certs(fake)
    assert certs == {"k1": "-----BEGIN CERTIFICATE-----"}
    assert got == max_age
    assert fake.calls[0]["timeout"] == google_identity.CERT_FETCH_TIMEOUT_SECONDS


@pytest.mark.parametrize("response", [
    FakeResponse(503, {}, b'{"k1": "pem"}'),
    FakeResponse(200, {}, b"<html>captive portal</html>"),
    FakeResponse(200, {}, b'{"keys": [{"kid": "k1"}]}'),
    FakeResponse(200, {}, b"{}"),
])
def test_unusable_cert_responses_fail_closed_as_transport_errors(response):
    with pytest.raises(google_exceptions.TransportError):
        google_identity.fetch_google_certs(FakeTransport(response))


# -- S1b / T3: max-age is clamped to [60, 86400] ------------------------------------------

@pytest.mark.parametrize("cache_control,max_age", [
    ("max-age=0", 60),
    ("max-age=59", 60),
    ("max-age=60", 60),
    ("max-age=86400", 86400),
    ("max-age=86401", 86400),
    ("max-age=" + "9" * 30, 86400),
    ("max-age=-1", 3600),
    ("max-age=", 3600),
    (None, 3600),
])
def test_cache_max_age_is_clamped_between_a_minute_and_a_day(cache_control, max_age):
    assert google_identity.cache_max_age(cache_control) == max_age
    headers = {} if cache_control is None else {"Cache-Control": cache_control}
    fake = FakeTransport(FakeResponse(200, headers, b'{"k1": "-----BEGIN CERTIFICATE-----"}'))
    assert google_identity.fetch_google_certs(fake)[1] == max_age


# -- S1b / T4: any fetch failure is a TransportError with backoff ---------------------------

def test_unexpected_fetch_exception_becomes_transport_error_with_backoff(google_keys):
    signer, _, certs = google_keys
    clock = Clock()
    fetch = CountingFetch(certs, error=RuntimeError("bug in the fetcher"))
    cache = GoogleCertCache(fetch=fetch, clock=clock)
    token = _id_token(signer)
    for _ in range(2):
        with pytest.raises(IdentityError) as exc:
            verify_google_credential(token, NONCE, cert_cache=cache)
        assert exc.value.reason == "google_unreachable"
    assert fetch.calls == 1  # the second caller is inside the backoff window
    with pytest.raises(google_exceptions.TransportError):
        cache.certs()
    assert fetch.calls == 1
    clock.now += google_identity.CERT_FETCH_RETRY_AFTER_SECONDS
    fetch.error = None
    assert verify_google_credential(token, NONCE, cert_cache=cache) == FULL
    assert fetch.calls == 2


# -- S1b / T2: the cert lock is taken with a timeout ----------------------------------------

CERT_LOCK_THRESHOLD_SECONDS = 2.0


def test_cert_lock_wait_times_out_as_transport_error(google_keys, monkeypatch):
    signer, _, certs = google_keys
    monkeypatch.setattr(google_identity, "CERT_FETCH_TIMEOUT_SECONDS", 0.05)
    fetch = CountingFetch(certs)
    cache = GoogleCertCache(fetch=fetch, clock=Clock())
    held, release = threading.Event(), threading.Event()

    def hold_the_lock():
        with cache._lock:  # stands in for a fetch that never returns
            held.set()
            release.wait(10)

    holder = threading.Thread(target=hold_the_lock)
    outcome = {}

    def verify():
        try:
            outcome["email"] = verify_google_credential(_id_token(signer), NONCE, cert_cache=cache)
        except IdentityError as exc:
            outcome["reason"] = exc.reason

    waiter = threading.Thread(target=verify)
    holder.start()
    try:
        assert held.wait(5)
        waiter.start()
        waiter.join(CERT_LOCK_THRESHOLD_SECONDS)
        assert not waiter.is_alive(), "waited on the cert lock without a timeout"
    finally:
        release.set()
        holder.join(10)
        waiter.join(10)
    assert outcome == {"reason": "google_unreachable"}
    assert fetch.calls == 0


# -- SP2 final review F8: email_verified must be exactly True -------------------------------------

@pytest.mark.parametrize("flag", ["true", False])
def test_email_verified_other_than_true_is_refused(google_keys, flag):
    signer, _, certs = google_keys
    cache = GoogleCertCache(fetch=CountingFetch(certs), clock=Clock())
    assert verify_google_credential(_id_token(signer), NONCE, cert_cache=cache) == FULL  # the claim set verifies
    with pytest.raises(IdentityError) as exc:
        verify_google_credential(_id_token(signer, email_verified=flag), NONCE, cert_cache=cache)
    assert exc.value.reason == "email_not_verified"
