"""Asset store and safe downloader: normalisation, formats, run scoping, SSRF refusals."""
import io
import socket

import pytest
import requests
from PIL import Image

from src.mcp_server import derleme, gates, ornekler, varliklar
from src.mcp_server.derle_araci import Derleyici
from src.mcp_server.runs import RunStore
from src.mcp_server.taslak import DraftStore
from src.mcp_server.varliklar import AssetStore, GuvenliIndirici, VarlikHatasi

RUN = "abcdef012345"
FULL = "drmahirkurt@gmail.com"


def _png(size=(3000, 2000)):
    image = Image.linear_gradient("L").resize(size).convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def store(tmp_path):
    runs = RunStore(tmp_path)
    runs.save(RUN, {"run_id": RUN, "created_by": FULL, "cerceve": {"kind": "textbook", "document_id": 197},
                    "kazanimlar": [{"code": "FB.5.4.1.1"}], "coverage": {}})
    return AssetStore(runs, clock=lambda: 1_800_000_000.0)


def test_image_is_normalised_and_stored_under_the_run(store, tmp_path):
    rec = store.save(RUN, _png(), "image", "pexels", "Pexels Lisansı", "Fotoğraf: Ayşe / Pexels", "degrade", FULL)
    assert varliklar.ASSET_ID_RE.match(rec["asset_id"]) and rec["mime"] == "image/jpeg"
    assert rec["bayt"] <= varliklar.IMAGE_MAX_BYTES
    stored = tmp_path / "edupedia_runs" / RUN / "assets" / f"{rec['asset_id']}.bin"
    with Image.open(stored) as img:
        assert max(img.size) == 1280 and img.format == "JPEG"
    assert store.load(RUN, rec["asset_id"])["credit"] == "Fotoğraf: Ayşe / Pexels"
    embedded = store.gomulu(RUN)[rec["asset_id"]]
    assert embedded.data_uri.startswith("data:image/jpeg;base64,") and embedded.tur == "image"


def test_bad_inputs_are_refused(store, monkeypatch):
    with pytest.raises(VarlikHatasi, match="gorsel_bozuk"):
        store.save(RUN, b"not an image", "image", "pexels", "l", "c", "a", FULL)
    with pytest.raises(VarlikHatasi, match="bicim"):
        store.save(RUN, b"RIFF0000WAVE", "ses", "minimax", "l", "c", "a", FULL)
    with pytest.raises(VarlikHatasi, match="gecersiz_tur"):
        store.save(RUN, b"ID3", "belge", "minimax", "l", "c", "a", FULL)
    with pytest.raises(VarlikHatasi, match="run_bulunamadi"):
        store.save("ffffffffffff", b"ID3" + b"\0" * 10, "ses", "minimax", "l", "c", "a", FULL)
    with pytest.raises(VarlikHatasi, match="varlik_cok_buyuk"):
        store.save(RUN, b"ID3" + b"\0" * derleme.ASSET_BUDGET_BYTES, "ses", "minimax", "l", "c", "a", FULL)
    monkeypatch.setattr(varliklar, "IMAGE_MAX_BYTES", 100)
    noisy = io.BytesIO()
    Image.effect_noise((800, 800), 90).convert("RGB").save(noisy, format="PNG")
    with pytest.raises(VarlikHatasi, match="gorsel_cok_buyuk"):
        store.save(RUN, noisy.getvalue(), "image", "pexels", "l", "c", "a", FULL)


def test_audio_and_video_signatures(store):
    assert store.save(RUN, b"ID3" + b"\0" * 64, "ses", "minimax", "l", "c", "a", FULL)["mime"] == "audio/mpeg"
    assert store.save(RUN, b"\xff\xfb" + b"\0" * 64, "muzik", "minimax", "l", "c", "a", FULL)["mime"] == "audio/mpeg"
    assert store.save(RUN, b"\0\0\0\x18ftypmp42" + b"\0" * 64, "video", "minimax", "l", "c", "a", FULL)["mime"] == "video/mp4"
    assert store.load(RUN, "../../etc") is None and store.load("../x", "0123456789abcdef") is None


def test_saved_asset_flows_into_derle_with_attribution(store, tmp_path):
    rec = store.save(RUN, _png((600, 400)), "image", "pexels", "Pexels Lisansı", "Fotoğraf: Ayşe Yılmaz / Pexels",
                     "Buz kalıbı", FULL)
    data = ornekler.ornek("QUIZ")
    teach = next(s for s in data["segments"] if s["type"] == "teach")
    teach.pop("visual", None)
    data["meta"]["assets"] = [{"asset_id": rec["asset_id"], "slot": f"{teach['id']}.visual"}]
    derleyici = Derleyici(store.runs, DraftStore(tmp_path), "https://tedy.online", "https://tedy.online",
                          assets=store.gomulu)
    body = derleyici.derle(FULL, RUN, data)
    assert body["status"] == "ok" and body["kapi_ozeti"]["fail"] == 0
    assert body["kapilar"]["G-ATTRIB"]["status"] == "PASS"


class _Resp:
    def __init__(self, status=200, body=b"x", headers=None):
        self.status_code, self._body = status, body
        self.headers = headers or {"content-type": "image/jpeg"}

    def iter_content(self, chunk_size):
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i:i + chunk_size]

    def close(self):
        pass


class _Session:
    def __init__(self, response):
        self.response, self.calls = response, []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def _resolver(ip):
    return lambda host, port, **kw: [(socket.AF_INET if ":" not in ip else socket.AF_INET6, 1, 6, "", (ip, port))]


def test_downloader_happy_path_without_redirects():
    session = _Session(_Resp(body=b"abc", headers={"content-type": "image/jpeg; charset=binary"}))
    data, mime = GuvenliIndirici(session=session, resolver=_resolver("93.184.216.34")).indir("https://images.pexels.com/p.jpg")
    assert (data, mime) == (b"abc", "image/jpeg")
    assert session.calls[0][1]["allow_redirects"] is False and session.calls[0][1]["stream"] is True


@pytest.mark.parametrize("url,ip,response,reason", [
    ("http://images.pexels.com/p.jpg", "93.184.216.34", _Resp(), "sema"),
    ("https://user:pw@images.pexels.com/p.jpg", "93.184.216.34", _Resp(), "sema"),
    ("https://evil.example/p.jpg", "127.0.0.1", _Resp(), "ozel_adres"),
    ("https://evil.example/p.jpg", "10.0.0.5", _Resp(), "ozel_adres"),
    ("https://evil.example/p.jpg", "169.254.169.254", _Resp(), "ozel_adres"),
    ("https://evil.example/p.jpg", "::1", _Resp(), "ozel_adres"),
    ("https://cdn.example/p.jpg", "93.184.216.34", _Resp(status=302, headers={"location": "http://127.0.0.1"}), "yonlendirme"),
    ("https://cdn.example/p.jpg", "93.184.216.34", _Resp(status=404), "http_404"),
    ("https://cdn.example/p.jpg", "93.184.216.34", _Resp(headers={"content-length": "9000001"}), "cok_buyuk"),
    ("https://cdn.example/p.jpg", "93.184.216.34", _Resp(body=b"x" * 101), "cok_buyuk"),
])
def test_downloader_refusals(url, ip, response, reason):
    downloader = GuvenliIndirici(session=_Session(response), resolver=_resolver(ip),
                                 max_bytes=100 if reason == "cok_buyuk" and len(response._body) > 1 else 8_000_000)
    with pytest.raises(VarlikHatasi) as exc:
        downloader.indir(url)
    assert exc.value.reason == reason


# --- Controller rulings on top of the brief's baseline coverage ---


def _dual_stack_resolver(ip):
    family = socket.AF_INET if ":" not in ip else socket.AF_INET6
    return lambda host, port, **kw: [(family, 1, 6, "", (ip, port))]


@pytest.mark.parametrize("ip", [
    "100.64.0.1",       # CGNAT / Tailscale range — not private/loopback/link-local/reserved
    "100.100.100.100",  # same CGNAT range
    "192.0.2.10",       # TEST-NET-1, documentation range: reserved but worth an explicit case
    "::ffff:127.0.0.1", # IPv4-mapped IPv6 loopback
    "64:ff9b::7f00:1",  # NAT64 well-known prefix mapping to 127.0.0.1 — globally routable per stdlib, must still be rejected
])
def test_downloader_refuses_addresses_missed_by_the_briefs_disjunction(ip):
    downloader = GuvenliIndirici(session=_Session(_Resp()), resolver=_dual_stack_resolver(ip))
    with pytest.raises(VarlikHatasi) as exc:
        downloader.indir("https://evil.example/p.jpg")
    assert exc.value.reason == "ozel_adres"


def test_downloader_refuses_nonstandard_port_as_sema():
    downloader = GuvenliIndirici(session=_Session(_Resp()), resolver=_resolver("93.184.216.34"))
    with pytest.raises(VarlikHatasi) as exc:
        downloader.indir("https://cdn.example:8443/p.jpg")
    assert exc.value.reason == "sema"


def test_downloader_refuses_malformed_port_as_sema():
    downloader = GuvenliIndirici(session=_Session(_Resp()), resolver=_resolver("93.184.216.34"))
    with pytest.raises(VarlikHatasi) as exc:
        downloader.indir("https://cdn.example:notaport/p.jpg")
    assert exc.value.reason == "sema"


def test_downloader_empty_resolver_result_is_ag_hatasi():
    downloader = GuvenliIndirici(session=_Session(_Resp()), resolver=lambda host, port, **kw: [])
    with pytest.raises(VarlikHatasi) as exc:
        downloader.indir("https://evil.example/p.jpg")
    assert exc.value.reason == "ag_hatasi"


def test_downloader_happy_path_never_disables_tls_verification():
    session = _Session(_Resp(body=b"abc", headers={"content-type": "image/jpeg; charset=binary"}))
    GuvenliIndirici(session=session, resolver=_resolver("93.184.216.34")).indir("https://images.pexels.com/p.jpg")
    kwargs = session.calls[0][1]
    assert kwargs.get("verify", True)


def test_normalize_image_pixel_bound_is_checked_explicitly_before_pillow_warns(monkeypatch):
    monkeypatch.setattr(varliklar, "IMAGE_MAX_PIXELS", 1000)
    buf = io.BytesIO()
    Image.linear_gradient("L").resize((40, 40)).convert("RGB").save(buf, format="PNG")
    with pytest.raises(VarlikHatasi) as exc:
        varliklar.normalize_image(buf.getvalue())
    assert exc.value.reason == "gorsel_cok_buyuk"


def test_asset_id_regex_rejects_trailing_newline_via_fullmatch(store):
    rec = store.save(RUN, _png(), "image", "pexels", "l", "c", "a", FULL)
    assert store.load(RUN, rec["asset_id"] + chr(10)) is None


def test_gomulu_skips_asset_whose_bin_was_deleted_but_keeps_others(store, tmp_path):
    rec1 = store.save(RUN, _png(), "image", "pexels", "l", "c", "a", FULL)
    rec2 = store.save(RUN, _png((600, 400)), "image", "pexels", "l", "c", "a", FULL)
    folder = tmp_path / "edupedia_runs" / RUN / "assets"
    (folder / f"{rec1['asset_id']}.bin").unlink()
    embedded = store.gomulu(RUN)
    assert rec1["asset_id"] not in embedded
    assert rec2["asset_id"] in embedded


def test_downloader_timeout_mid_chunk_raises_zaman_asimi():
    class _SlowResp(_Resp):
        def iter_content(self, chunk_size):
            yield self._body[:1]
            # A second chunk exists, but the fake clock will have crossed the deadline by
            # the time the loop asks for it.
            yield self._body[1:]

    clock = {"t": 0.0}

    def fake_monotonic():
        clock["t"] += 100.0  # first call fixes the deadline; each later call jumps far past it
        return clock["t"]

    downloader = GuvenliIndirici(session=_Session(_SlowResp(body=b"xy")), resolver=_resolver("93.184.216.34"),
                                 timeout=1.0, monotonic=fake_monotonic)
    with pytest.raises(VarlikHatasi) as exc:
        downloader.indir("https://cdn.example/p.jpg")
    assert exc.value.reason == "zaman_asimi"


# --- Fix round 1 (controller task-12-fix-1-brief.md) ---


def test_downloader_mid_stream_chunked_encoding_error_is_ag_hatasi():
    """F1: a drop *during* body streaming (not just at connect time) must close-reason, not leak."""
    class _FlakyResp(_Resp):
        def iter_content(self, chunk_size):
            yield self._body[:1]
            raise requests.exceptions.ChunkedEncodingError("Connection broken: peer reset")

    downloader = GuvenliIndirici(session=_Session(_FlakyResp(body=b"xy")), resolver=_resolver("93.184.216.34"))
    with pytest.raises(VarlikHatasi) as exc:
        downloader.indir("https://cdn.example/p.jpg")
    assert exc.value.reason == "ag_hatasi"


def test_downloader_mid_stream_connection_error_is_ag_hatasi():
    """F1: a reset mid-transfer is ordinary for third-party CDNs and must also close-reason."""
    class _FlakyResp(_Resp):
        def iter_content(self, chunk_size):
            yield self._body[:1]
            raise requests.exceptions.ConnectionError("reset by peer")

    downloader = GuvenliIndirici(session=_Session(_FlakyResp(body=b"xy")), resolver=_resolver("93.184.216.34"))
    with pytest.raises(VarlikHatasi) as exc:
        downloader.indir("https://cdn.example/p.jpg")
    assert exc.value.reason == "ag_hatasi"


def test_downloader_zaman_asimi_and_cok_buyuk_still_propagate_unchanged_by_f1():
    """F1 must not reclassify the loop's own VarlikHatasi raises (cok_buyuk / zaman_asimi) as
    ag_hatasi — the fix wraps requests.RequestException only, and VarlikHatasi does not subclass
    it (VarlikHatasi < ValueError; requests.RequestException < OSError), but this is asserted
    directly so a future refactor that merges the except clauses trips a red test immediately."""
    downloader = GuvenliIndirici(session=_Session(_Resp(body=b"x" * 101)), resolver=_resolver("93.184.216.34"),
                                 max_bytes=100)
    with pytest.raises(VarlikHatasi) as exc:
        downloader.indir("https://cdn.example/p.jpg")
    assert exc.value.reason == "cok_buyuk"

    clock = {"t": 0.0}

    def fake_monotonic():
        clock["t"] += 100.0
        return clock["t"]

    class _SlowResp(_Resp):
        def iter_content(self, chunk_size):
            yield self._body[:1]
            yield self._body[1:]

    downloader = GuvenliIndirici(session=_Session(_SlowResp(body=b"xy")), resolver=_resolver("93.184.216.34"),
                                 timeout=1.0, monotonic=fake_monotonic)
    with pytest.raises(VarlikHatasi) as exc:
        downloader.indir("https://cdn.example/p.jpg")
    assert exc.value.reason == "zaman_asimi"


def _oriented_jpeg():
    """A portrait 40x100 JPEG whose EXIF Orientation=6 says "rotate 90 CW to display" — i.e. the
    intended, upright display is 100x40 landscape. Matches the review's Finding-2 repro exactly."""
    img = Image.new("RGB", (40, 100), (10, 200, 10))
    buf = io.BytesIO()
    exif = img.getexif()
    exif[0x0112] = 6  # Orientation tag
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def test_normalize_image_applies_exif_orientation_before_reencoding():
    """F2: the stored JPEG carries no EXIF, so the orientation must be baked into the pixels."""
    data = _oriented_jpeg()
    with Image.open(io.BytesIO(data)) as probe:
        assert probe.getexif().get(0x0112) == 6
        assert probe.size == (40, 100)
    out = varliklar.normalize_image(data)
    with Image.open(io.BytesIO(out)) as result:
        assert result.format == "JPEG"
        # exif_transpose actually ran: dimensions are swapped relative to the un-transposed decode.
        assert result.size == (100, 40)


def test_normalize_image_with_no_exif_does_not_crash():
    """F2: getexif() empty must not make exif_transpose raise."""
    data = _png((300, 200))
    with Image.open(io.BytesIO(data)) as probe:
        assert dict(probe.getexif()) == {}
    out = varliklar.normalize_image(data)
    with Image.open(io.BytesIO(out)) as result:
        assert result.size == (300, 200)


def _rgba_half_transparent(size=(100, 100)):
    image = Image.new("RGBA", size, (200, 30, 30, 255))
    w, h = size
    for x in range(w // 2, w):
        for y in range(h):
            image.putpixel((x, y), (0, 0, 0, 0))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _p_mode_with_transparent_index(size=(100, 100)):
    image = Image.new("P", size, 0)
    image.putpalette([200, 30, 30] + [0, 0, 0] * 255)
    image.info["transparency"] = 1
    w, h = size
    for x in range(w // 2, w):
        for y in range(h):
            image.putpixel((x, y), 1)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.parametrize("builder", [_rgba_half_transparent, _p_mode_with_transparent_index])
def test_normalize_image_flattens_alpha_to_white(builder):
    """F3 (review Minor 3): RGBA and P-mode-with-transparent-index both flatten alpha to a plain
    RGB JPEG — opaque region keeps its colour, transparent region becomes white."""
    out = varliklar.normalize_image(builder())
    with Image.open(io.BytesIO(out)) as img:
        assert img.format == "JPEG" and img.mode == "RGB"
        opaque = img.getpixel((10, 10))
        transparent = img.getpixel((90, 90))
    assert opaque[0] > 150 and opaque[1] < 100 and opaque[2] < 100
    assert all(c > 240 for c in transparent)
