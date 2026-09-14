"""Verify a Google Identity Services credential for the OAuth consent step.

The real default path never touches the network for a credential that is not JWT-shaped, and
reuses Google's signing certs for their Cache-Control max-age instead of fetching them per call.
"""
from __future__ import annotations

import json
import re
import threading
import time
from typing import Any, Callable, Mapping

from google.auth import exceptions as google_exceptions
from google.auth import transport
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from src import roles

IdentityVerifier = Callable[[str, str], str]
CertFetcher = Callable[[], tuple[Mapping[str, str], int]]

GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v1/certs"
MAX_CREDENTIAL_BYTES = 4096
CERT_FETCH_TIMEOUT_SECONDS = 5.0
DEFAULT_CERT_MAX_AGE_SECONDS = 3600
MIN_CERT_MAX_AGE_SECONDS = 60
MAX_CERT_MAX_AGE_SECONDS = 86400
# A failed fetch is reported to every caller queued behind it instead of being retried by each.
CERT_FETCH_RETRY_AFTER_SECONDS = 5.0

_JWT_SHAPE = re.compile(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")


class IdentityError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def is_well_formed_credential(credential: str) -> bool:
    """Three non-empty unpadded base64url segments, at most 4096 bytes (ASCII by construction)."""
    return len(credential) <= MAX_CREDENTIAL_BYTES and _JWT_SHAPE.fullmatch(credential) is not None


def cache_max_age(cache_control: str | None) -> int:
    """max-age clamped to [60, 86400] seconds; missing, malformed or negative means an hour."""
    for directive in (cache_control or "").split(","):
        name, _, value = directive.partition("=")
        if name.strip().lower() == "max-age":
            value = value.strip().strip('"')
            if value.isascii() and value.isdigit():
                # 0 would refetch on every consent; a huge value would pin rotated-out keys.
                return min(max(int(value), MIN_CERT_MAX_AGE_SECONDS), MAX_CERT_MAX_AGE_SECONDS)
    return DEFAULT_CERT_MAX_AGE_SECONDS


def _header(headers: Mapping[str, str], name: str) -> str | None:
    return next((v for k, v in headers.items() if k.lower() == name), None)


def fetch_google_certs(request: transport.Request | None = None) -> tuple[dict[str, str], int]:
    """GET Google's x509 signing certs with a short timeout; return (certs, max_age_seconds).

    Anything other than a non-empty key id -> PEM map is a TransportError, so verification fails
    closed as google_unreachable rather than trusting or mis-parsing an unexpected payload.
    """
    request = google_requests.Request() if request is None else request
    response = request(GOOGLE_CERTS_URL, method="GET", timeout=CERT_FETCH_TIMEOUT_SECONDS)
    if response.status != 200:
        raise google_exceptions.TransportError(f"Google certs returned HTTP {response.status}")
    try:
        certs = json.loads(response.data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise google_exceptions.TransportError("Google certs payload is not JSON") from exc
    if not (isinstance(certs, dict) and certs
            and all(isinstance(k, str) and isinstance(v, str) for k, v in certs.items())):
        raise google_exceptions.TransportError("Google certs payload is not a key id -> certificate map")
    return certs, cache_max_age(_header(response.headers, "cache-control"))


class GoogleCertCache:
    """Process-wide Google signing certs, refreshed after max-age; one fetch at a time.

    Callers run in worker threads, so a threading lock makes concurrent cold fetches collapse into
    one: whoever waits behind the in-flight fetch reuses its certs, or its failure for a short while.
    """

    def __init__(self, fetch: CertFetcher = fetch_google_certs,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._fetch = fetch
        self._clock = clock
        self._lock = threading.Lock()
        self._certs: Mapping[str, str] | None = None
        self._fresh_until = 0.0
        self._retry_after = 0.0

    def certs(self) -> Mapping[str, str]:
        # A fetch stuck past its own timeout must not queue every later verification behind it.
        if not self._lock.acquire(timeout=CERT_FETCH_TIMEOUT_SECONDS):
            raise google_exceptions.TransportError("Google certs fetch is still in flight")
        try:
            now = self._clock()
            if self._certs is not None and now < self._fresh_until:
                return self._certs
            if now < self._retry_after:
                raise google_exceptions.TransportError("Google certs fetch failed moments ago")
            try:
                certs, max_age = self._fetch()
            except Exception as exc:
                # Any failure (not only a transport one) backs off and fails closed as unreachable.
                self._retry_after = self._clock() + CERT_FETCH_RETRY_AFTER_SECONDS
                if isinstance(exc, google_exceptions.TransportError):
                    raise
                raise google_exceptions.TransportError(
                    f"Google certs fetch failed unexpectedly: {type(exc).__name__}") from exc
            self._certs, self._fresh_until = certs, now + max_age
            return certs
        finally:
            self._lock.release()


class _CertsResponse(transport.Response):
    def __init__(self, data: bytes) -> None:
        self._data = data

    @property
    def status(self) -> int:
        return 200

    @property
    def headers(self) -> Mapping[str, str]:
        return {}

    @property
    def data(self) -> bytes:
        return self._data


class _CachedCertsRequest(transport.Request):
    """Transport handed to google-auth: serves the certs URL from the cache and nothing else."""

    def __init__(self, cache: GoogleCertCache) -> None:
        self._cache = cache

    def __call__(self, url: str, method: str = "GET", body: Any = None, headers: Any = None,
                 timeout: Any = None, **kwargs: Any) -> transport.Response:
        if url != GOOGLE_CERTS_URL or method != "GET":
            raise google_exceptions.TransportError(f"unexpected identity request: {method} {url}")
        return _CertsResponse(json.dumps(self._cache.certs()).encode("utf-8"))


_DEFAULT_CERT_CACHE = GoogleCertCache()


def verify_google_credential(credential: str, expected_nonce: str,
                             cert_cache: GoogleCertCache | None = None) -> str:
    """Return the verified, lower-cased email or raise IdentityError."""
    if not is_well_formed_credential(credential):
        raise IdentityError("invalid_token")
    request = _CachedCertsRequest(_DEFAULT_CERT_CACHE if cert_cache is None else cert_cache)
    try:
        info = id_token.verify_oauth2_token(credential, request, roles.GOOGLE_CLIENT_ID)
    except google_exceptions.TransportError as exc:
        raise IdentityError("google_unreachable") from exc
    except (ValueError, google_exceptions.GoogleAuthError) as exc:
        raise IdentityError("invalid_token") from exc
    # Exactly True: a string such as "true" is not Google's boolean claim and is refused like False.
    if info.get("email_verified") is not True:
        raise IdentityError("email_not_verified")
    if not expected_nonce or info.get("nonce") != expected_nonce:
        raise IdentityError("nonce_mismatch")
    return str(info.get("email", "")).strip().lower()
