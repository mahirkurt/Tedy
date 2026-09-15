"""Per-run media assets and a safe downloader (spec §5.2, §8; plan K-P5, K-P6, K-P25).

Asset bytes never travel through a tool call: fleet tools return hosted URLs or image content,
ted-mcp downloads or decodes them here, normalises images and stores them under the run. The
compiler later embeds them as data: URIs by asset_id.
"""
from __future__ import annotations

import base64
import hashlib
import io
import ipaddress
import json
import os
import re
import secrets
import socket
import time
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlparse

import requests
from PIL import Image, ImageOps, UnidentifiedImageError

from src.json_utils import atomic_json_dump
from src.mcp_server import derleme
from src.mcp_server.derleme import GomuluVarlik
from src.mcp_server.runs import RUN_ID_RE, RunStore

ASSET_ID_RE = re.compile(r"^[0-9a-f]{16}$")
IMAGE_MAX_BYTES = 400_000
IMAGE_MAX_EDGE = 1280
IMAGE_MAX_PIXELS = 40_000_000
DOWNLOAD_MAX_BYTES = 8_000_000
TURLER = ("image", "video", "ses", "muzik")


class VarlikHatasi(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def normalize_image(data: bytes) -> bytes:
    Image.MAX_IMAGE_PIXELS = IMAGE_MAX_PIXELS
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(data)) as image:
            # F2: bake EXIF orientation into the pixels before any resize/convert — the stored
            # JPEG carries no EXIF, so a camera photo's Orientation tag (e.g. a portrait phone
            # photo saved with Orientation=6) would otherwise be silently dropped and the asset
            # stored rotated/flipped from how it was meant to display. Safe with no EXIF at all:
            # exif_transpose() is a no-op (still returns a new Image) when getexif() is empty.
            image = ImageOps.exif_transpose(image)
            # T12-3: Pillow's own MAX_IMAGE_PIXELS guard only *warns* (DecompressionBombWarning)
            # between N and 2N pixels and still decodes; it only raises above 2N. A pixel bound
            # must therefore be checked explicitly, before convert/thumbnail ever touch the data.
            # (width * height is unaffected by exif_transpose's rotate/flip, so checking here,
            # after the transpose, is equivalent to checking pre-transpose.)
            if image.width * image.height > IMAGE_MAX_PIXELS:
                raise VarlikHatasi("gorsel_cok_buyuk")
            if image.mode in ("RGBA", "LA", "P"):
                image = image.convert("RGBA")
                ground = Image.new("RGB", image.size, (255, 255, 255))
                ground.paste(image, mask=image.split()[-1])
                image = ground
            else:
                image = image.convert("RGB")
            image.thumbnail((IMAGE_MAX_EDGE, IMAGE_MAX_EDGE))
            for quality in (82, 74, 66, 60):
                buf = io.BytesIO()
                image.save(buf, format="JPEG", quality=quality, optimize=True)
                if buf.tell() <= IMAGE_MAX_BYTES:
                    return buf.getvalue()
    except VarlikHatasi:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError, ValueError) as exc:
        raise VarlikHatasi("gorsel_bozuk") from exc
    raise VarlikHatasi("gorsel_cok_buyuk")


def _media_mime(data: bytes, tur: str) -> str:
    if tur in ("ses", "muzik"):
        if data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
            return "audio/mpeg"
    elif tur == "video" and data[4:8] == b"ftyp":
        return "video/mp4"
    raise VarlikHatasi("bicim")


class AssetStore:
    def __init__(self, runs: RunStore, clock: Callable[[], float] = time.time) -> None:
        self.runs = runs
        self.clock = clock

    def _folder(self, run_id: str):
        if not RUN_ID_RE.match(run_id or ""):
            return None
        return self.runs.root / run_id / "assets"

    def save(self, run_id: str, data: bytes, tur: str, kaynak: str, lisans: str, credit: str, alt: str,
             created_by: str) -> dict[str, Any]:
        if tur not in TURLER:
            raise VarlikHatasi("gecersiz_tur")
        folder = self._folder(run_id)
        if folder is None or self.runs.load(run_id) is None:
            raise VarlikHatasi("run_bulunamadi")
        if tur == "image":
            data, mime = normalize_image(data), "image/jpeg"
        else:
            mime = _media_mime(data, tur)
            if len(data) > derleme.ASSET_BUDGET_BYTES:
                raise VarlikHatasi("varlik_cok_buyuk")
        folder.mkdir(parents=True, exist_ok=True)
        asset_id = secrets.token_hex(8)
        fd = os.open(folder / f"{asset_id}.bin", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        record = {
            "asset_id": asset_id, "run_id": run_id, "tur": tur, "mime": mime, "bayt": len(data),
            "sha256": hashlib.sha256(data).hexdigest(), "kaynak": kaynak, "lisans": lisans,
            "credit": credit, "alt": alt[:200], "created_by": created_by,
            "created_at": datetime.fromtimestamp(self.clock(), timezone.utc).isoformat(timespec="seconds"),
        }
        atomic_json_dump(record, str(folder / f"{asset_id}.json"))
        return record

    def load(self, run_id: str, asset_id: str) -> dict[str, Any] | None:
        folder = self._folder(run_id)
        # T12-4: .fullmatch() (not .match()) so a trailing "\n" on asset_id can never sneak an
        # otherwise-valid 16-hex id past the pattern, the same RUN_ID_RE \Z-anchoring concern
        # runs.py already documents for run_id.
        if folder is None or not ASSET_ID_RE.fullmatch(asset_id or ""):
            return None
        try:
            return json.loads((folder / f"{asset_id}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def gomulu(self, run_id: str) -> dict[str, GomuluVarlik]:
        folder = self._folder(run_id)
        out: dict[str, GomuluVarlik] = {}
        if folder is None or not folder.is_dir():
            return out
        for meta_path in sorted(folder.glob("*.json")):
            record = self.load(run_id, meta_path.stem)
            if record is None:
                continue
            try:
                data = (folder / f"{record['asset_id']}.bin").read_bytes()
            except OSError:
                # T12-4: a run whose .json survived but whose .bin was deleted (or is otherwise
                # unreadable) is skipped like a sha mismatch, rather than raising and failing the
                # whole embed for every other asset in the run.
                continue
            if hashlib.sha256(data).hexdigest() != record["sha256"]:
                continue
            out[record["asset_id"]] = GomuluVarlik(
                asset_id=record["asset_id"], tur=record["tur"], mime=record["mime"],
                data_uri=f"data:{record['mime']};base64," + base64.b64encode(data).decode("ascii"),
                bayt=record["bayt"], credit=record["credit"], lisans=record["lisans"], alt=record["alt"],
                kaynak=record["kaynak"])
        return out


class GuvenliIndirici:
    """https only, no userinfo, no redirects, public addresses only, bounded size, bounded time.

    T12-1: hostnames resolving into Tailscale's CGNAT range (100.64.0.0/10) or reachable only via
    an IPv4-mapped IPv6 address or the NAT64 well-known prefix are not caught by the brief's
    is_private/is_loopback/is_link_local/is_reserved/is_multicast/is_unspecified disjunction alone
    — ``ip.ipv4_mapped or ip`` unwraps a mapped address to its real (often private) IPv4 form
    first, and ``not ip.is_global`` is the fallback net that also catches ``64:ff9b::/96`` and
    other non-public ranges the disjunction misses.
    """

    def __init__(self, session: Any = None, timeout: float = 25.0, max_bytes: int = DOWNLOAD_MAX_BYTES,
                 resolver: Callable[..., Any] = socket.getaddrinfo,
                 monotonic: Callable[[], float] = time.monotonic) -> None:
        self.session = session if session is not None else requests.Session()
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.resolver = resolver
        self.monotonic = monotonic

    def indir(self, url: str) -> tuple[bytes, str]:
        parsed = urlparse(url or "")
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise VarlikHatasi("sema")
        try:
            port = parsed.port
        except ValueError:
            # T12-1: a malformed port (e.g. "https://cdn.example:notaport/p.jpg") makes
            # urlparse.port raise ValueError on access rather than at parse time.
            raise VarlikHatasi("sema")
        if port is not None and port != 443:
            raise VarlikHatasi("sema")
        try:
            infos = self.resolver(parsed.hostname, port or 443, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise VarlikHatasi("ag_hatasi") from exc
        if not infos:
            raise VarlikHatasi("ag_hatasi")
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            # IPv4Address has no ipv4_mapped attribute at all (only IPv6Address does), so this
            # must be a getattr, not a plain `ip.ipv4_mapped` access.
            ip = getattr(ip, "ipv4_mapped", None) or ip
            if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast
                    or ip.is_unspecified or not ip.is_global):
                raise VarlikHatasi("ozel_adres")
        deadline = self.monotonic() + self.timeout
        try:
            response = self.session.get(url, timeout=self.timeout, stream=True, allow_redirects=False)
        except requests.RequestException as exc:
            raise VarlikHatasi("ag_hatasi") from exc
        try:
            if 300 <= response.status_code < 400:
                raise VarlikHatasi("yonlendirme")
            if response.status_code != 200:
                raise VarlikHatasi(f"http_{response.status_code}")
            declared = (response.headers or {}).get("content-length")
            if declared and declared.isdigit() and int(declared) > self.max_bytes:
                raise VarlikHatasi("cok_buyuk")
            chunks, total = [], 0
            for chunk in response.iter_content(chunk_size=65536):
                total += len(chunk)
                if total > self.max_bytes:
                    raise VarlikHatasi("cok_buyuk")
                chunks.append(chunk)
                if self.monotonic() > deadline:
                    raise VarlikHatasi("zaman_asimi")
            mime = ((response.headers or {}).get("content-type") or "").split(";", 1)[0].strip().lower()
            return b"".join(chunks), mime
        except requests.RequestException as exc:
            # F1: a drop/reset *during* body streaming (ChunkedEncodingError, ConnectionError, a
            # read timeout, …) is an ordinary production event for third-party CDN downloads, not
            # just at connect time. VarlikHatasi is a ValueError and requests.RequestException is
            # an OSError — the two hierarchies never overlap — so none of this function's own
            # VarlikHatasi raises (yonlendirme/http_.../cok_buyuk/zaman_asimi, all above) are ever
            # caught or reclassified here; only a genuine requests exception reaches this clause.
            raise VarlikHatasi("ag_hatasi") from exc
        finally:
            response.close()
