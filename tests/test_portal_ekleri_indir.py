"""One attachment download (plan 2026-09-28-portal-ekleri, Görev 5).

The shape tests run against the fake HTTP layer in tests/sahte_http.py. Every
safety claim about time, addresses, cookies and resume is proven through real
`requests` — against a loopback HTTPS server on 127.0.0.1 (nothing leaves the
host) or a recording transport adapter — because the fake cannot show what
urllib3 does with a slow socket, a redirect or a cookie jar. Name resolution
is always a monkeypatched `socket.getaddrinfo`: no test does real DNS."""
import hashlib
import io
import logging
import ipaddress
import json
import socket
import shutil
import ssl
import struct
import subprocess
import threading
import time
import zipfile
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requests
from requests.adapters import BaseAdapter
from requests.models import Response

import src.portal_ekleri_indir as indir_modulu
from src.portal_ekleri import ek_kimligi, ek_turu
from src.portal_ekleri_indir import (DOCX_MIME, EK_AZAMI_YONLENDIRME, EK_BOYUT_SINIRI, MB,
                                     HTML_BAS_SINIRI, PARCA_BOYUTU, Butce, drive_onay_adresi, ek_indir,
                                     html_mi,
                                     portal_cerez_kavanozu, tur_bul)
from tests.sahte_http import (DOCS_URL, DRIVE_KIMLIK, DRIVE_ONAY, DRIVE_URL, GIRIS_DUVARI, PDF,
                              PORTAL_URL, SP_DUVAR_URL, SP_URL, SahteOturum, SahteSaat,
                              SahteYanit, aralikli, docx_bayt, surum_etiketi)

SP = "https://ornekokul-my.sharepoint.com/"


def _kayit(url):
    return {"id": ek_kimligi(url), "url": url, "type": ek_turu(url)}


def _sinirsiz():
    return Butce(son_an=float("inf"), bayt=10 * EK_BOYUT_SINIRI)


def _bol(govde, n=MB):
    return [govde[i:i + n] for i in range(0, len(govde), n)]


def _parcalar(dizin):
    return sorted((dizin / ".parca").iterdir()) if (dizin / ".parca").exists() else []


def _yarim_birak(dizin, kayit, govde, etag=None, toplam=None, last_modified=None):
    """A part file as an earlier run leaves it: the bytes plus the version
    sidecar ek_indir needs before it will resume with Range."""
    (dizin / ".parca").mkdir(parents=True, exist_ok=True)
    (dizin / ".parca" / f"{kayit['id']}.part").write_bytes(govde)
    (dizin / ".parca" / f"{kayit['id']}.meta.json").write_text(
        json.dumps({"etag": etag, "last_modified": last_modified, "toplam": toplam}), encoding="utf-8")


def test_sharepoint_download_1_ile_istenir_pdf_saklanir(tmp_path):
    oturum = SahteOturum({SP: lambda u, h: SahteYanit(200, PDF, {"Content-Type": "application/pdf",
                                                                 "Content-Length": str(len(PDF))})})
    sonuc = ek_indir(oturum, _kayit(SP_URL), tmp_path, _sinirsiz())
    assert (sonuc.durum, sonuc.uzanti, sonuc.mime) == ("indirildi", ".pdf", "application/pdf")
    assert sonuc.sha256 == hashlib.sha256(PDF).hexdigest() and sonuc.boyut == len(PDF)
    istek = oturum.istekler[0]
    assert "download=1" in istek["url"] and "e=AbC123" in istek["url"]
    assert istek["cookies"] is None and istek["stream"] is True and "Range" not in istek["headers"]
    assert (tmp_path / sonuc.dosya).read_bytes() == PDF
    assert _parcalar(tmp_path) == []


def test_giris_duvari_dosya_olarak_saklanmaz(tmp_path):
    duvar = SahteYanit(200, GIRIS_DUVARI, {"Content-Type": "text/html; charset=utf-8"},
                       url="https://login.microsoftonline.com/common/oauth2/authorize?client_id=ornek")
    sonuc = ek_indir(SahteOturum({SP: duvar}), _kayit(SP_DUVAR_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "erisilemedi" and "giriş istiyor" in sonuc.neden
    assert [p.name for p in tmp_path.iterdir()] == [".parca"] and _parcalar(tmp_path) == []


def test_octet_stream_diyen_html_de_web_sayfasidir(tmp_path):
    sayfa = SahteYanit(200, b"  <!DOCTYPE html><html>klasor</html>", {"Content-Type": "application/octet-stream"})
    sonuc = ek_indir(SahteOturum({SP: sayfa}), _kayit(SP_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "erisilemedi" and "web sayfası" in sonuc.neden


def test_drive_onay_sayfasi_formdaki_ikinci_istekle_gecilir(tmp_path):
    oturum = SahteOturum({
        f"https://drive.google.com/uc?export=download&id={DRIVE_KIMLIK}":
            lambda u, h: SahteYanit(200, DRIVE_ONAY, {"Content-Type": "text/html; charset=utf-8"}),
        "https://drive.usercontent.google.com/download?":
            lambda u, h: SahteYanit(200, PDF, {"Content-Type": "application/octet-stream"}),
    })
    sonuc = ek_indir(oturum, _kayit(DRIVE_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "indirildi" and sonuc.uzanti == ".pdf"
    ikinci = oturum.istekler[1]["url"]
    assert f"id={DRIVE_KIMLIK}" in ikinci and "confirm=t" in ikinci and "uuid=" in ikinci


def test_drive_onay_sayfasi_ikinci_kez_gelirse_dongu_yok(tmp_path):
    def onay(u, h):
        return SahteYanit(200, DRIVE_ONAY, {"Content-Type": "text/html"})
    oturum = SahteOturum({"https://drive.google.com/": onay, "https://drive.usercontent.google.com/": onay})
    sonuc = ek_indir(oturum, _kayit(DRIVE_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "erisilemedi" and len(oturum.istekler) == 2


def test_google_dokumani_pdf_olarak_disari_aktarilir(tmp_path):
    oturum = SahteOturum({
        "https://docs.google.com/document/d/1ZyXwVuTsRqPoNmLkJiHgFeDcBa98765/export?format=pdf":
            SahteYanit(200, PDF, {"Content-Type": "application/pdf"})})
    sonuc = ek_indir(oturum, _kayit(DOCS_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "indirildi" and sonuc.uzanti == ".pdf"


@pytest.mark.parametrize("govde,uzanti,mime", [
    (docx_bayt(["Soru 1"]), ".docx", DOCX_MIME),
    (bytes.fromhex("89504e470d0a1a0a") + b"0" * 64, ".png", "image/png"),
    (bytes.fromhex("ffd8ffe0") + b"0" * 64, ".jpg", "image/jpeg"),
    (b"GIF89a" + b"0" * 64, ".gif", "image/gif"),
    (b"bilinmeyen ikili veri", ".bin", "application/octet-stream"),
])
def test_tur_basliktan_degil_baytlardan_okunur(tmp_path, govde, uzanti, mime):
    yanit = SahteYanit(200, govde, {"Content-Type": "application/pdf"})
    sonuc = ek_indir(SahteOturum({SP: yanit}), _kayit(SP_URL), tmp_path, _sinirsiz())
    assert (sonuc.durum, sonuc.uzanti, sonuc.mime) == ("indirildi", uzanti, mime)
    assert (tmp_path / f"{ek_kimligi(SP_URL)}{uzanti}").is_file()


@pytest.mark.parametrize("kod,durum", [(403, "erisilemedi"), (404, "erisilemedi"), (503, "hata")])
def test_http_hatalari(tmp_path, kod, durum):
    sonuc = ek_indir(SahteOturum({SP: SahteYanit(kod, b"")}), _kayit(SP_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == durum and str(kod) in sonuc.neden


def test_ag_hatasi_hata_olur_istisna_kacmaz(tmp_path):
    def kopuk(u, h):
        raise requests.ConnectionError("bağlantı koptu")
    sonuc = ek_indir(SahteOturum({SP: kopuk}), _kayit(SP_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "hata" and "ConnectionError" in sonuc.neden


def test_baglanti_indirilmez(tmp_path):
    kayit = {"id": "0" * 16, "url": "https://www.youtube.com/watch?v=x", "type": "baglanti"}
    sonuc = ek_indir(SahteOturum({}), kayit, tmp_path, _sinirsiz())
    assert sonuc.durum == "erisilemedi"


def test_300_mb_ustu_govdesi_okunmadan_reddedilir(tmp_path):
    def patla():
        raise AssertionError("gövde okunmamalıydı")
    yanit = SahteYanit(200, headers={"Content-Type": "application/pdf",
                                     "Content-Length": str(EK_BOYUT_SINIRI + 1)}, bloklar=[patla])
    sonuc = ek_indir(SahteOturum({SP: yanit}), _kayit(SP_URL), tmp_path, _sinirsiz())
    assert EK_BOYUT_SINIRI == 300 * MB
    assert sonuc.durum == "cok_buyuk" and "300 MB" in sonuc.neden
    assert yanit.kapandi


def test_uzunluk_bildirmeyen_akis_sinirda_kesilir_parca_silinir(tmp_path):
    yanit = SahteYanit(200, headers={"Content-Type": "application/pdf"},
                       bloklar=_bol(PDF + b"0" * (4 * MB)))
    sonuc = ek_indir(SahteOturum({SP: yanit}), _kayit(SP_URL), tmp_path, _sinirsiz(), sinir=3 * MB)
    assert sonuc.durum == "cok_buyuk" and _parcalar(tmp_path) == []


def test_bayt_butcesi_dolunca_parca_kalir_sonraki_tur_range_ile_surer(tmp_path):
    govde = PDF + bytes(range(256)) * (4 * 4096)          # ~4 MB after a PDF head
    kayit = _kayit(SP_URL)
    oturum = SahteOturum({SP: aralikli(govde)})
    ilk = ek_indir(oturum, kayit, tmp_path, Butce(float("inf"), 2 * MB))
    assert ilk.durum == "bekliyor" and ilk.parca_bayt == 2 * MB
    assert "Range" not in oturum.istekler[0]["headers"]
    ikinci = ek_indir(oturum, kayit, tmp_path, Butce(float("inf"), 100 * MB))
    assert ikinci.durum == "indirildi"
    assert oturum.istekler[1]["headers"]["Range"] == f"bytes={2 * MB}-"
    assert (tmp_path / ikinci.dosya).read_bytes() == govde
    assert ikinci.sha256 == hashlib.sha256(govde).hexdigest() and _parcalar(tmp_path) == []


def test_sure_butcesi_dolunca_da_durur(tmp_path):
    butce = Butce(son_an=3.5, bayt=10 ** 12, saat=SahteSaat(adim=1.0))
    govde = PDF + b"0" * (5 * MB)
    sonuc = ek_indir(SahteOturum({SP: aralikli(govde)}), _kayit(SP_URL), tmp_path, butce)
    assert sonuc.durum == "bekliyor" and 0 < sonuc.parca_bayt < len(govde)


def test_onceki_tur_tam_sonda_durduysa_416_dosyayi_tamamlar(tmp_path):
    kayit = _kayit(SP_URL)
    _yarim_birak(tmp_path, kayit, PDF, etag=surum_etiketi(PDF), toplam=len(PDF))
    oturum = SahteOturum({SP: aralikli(PDF)})
    sonuc = ek_indir(oturum, kayit, tmp_path, _sinirsiz())
    assert oturum.istekler[0]["headers"]["Range"] == f"bytes={len(PDF)}-"
    assert sonuc.durum == "indirildi" and (tmp_path / sonuc.dosya).read_bytes() == PDF
    assert _parcalar(tmp_path) == []


def test_uyusmayan_aralik_parcayi_atar(tmp_path):
    kayit = _kayit(SP_URL)
    _yarim_birak(tmp_path, kayit, PDF[:100], etag=surum_etiketi(PDF), toplam=len(PDF))
    yanlis = SahteYanit(206, PDF[:100], {"Content-Range": f"bytes 0-99/{len(PDF)}"})
    oturum = SahteOturum({SP: yanlis})
    sonuc = ek_indir(oturum, kayit, tmp_path, _sinirsiz())
    assert oturum.istekler[0]["headers"]["Range"] == "bytes=100-"
    assert sonuc.durum == "hata" and _parcalar(tmp_path) == []


def test_range_yok_sayilirsa_bastan_yazilir(tmp_path):
    kayit = _kayit(SP_URL)
    _yarim_birak(tmp_path, kayit, b"eski yarim", etag='"eski"', toplam=len(PDF))
    oturum = SahteOturum({SP: SahteYanit(200, PDF, {"Content-Type": "application/pdf"})})
    sonuc = ek_indir(oturum, kayit, tmp_path, _sinirsiz())
    assert oturum.istekler[0]["headers"]["Range"] == "bytes=10-"
    assert sonuc.durum == "indirildi" and (tmp_path / sonuc.dosya).read_bytes() == PDF
    assert _parcalar(tmp_path) == []


def test_gecersiz_kimlik_dizin_disina_yazmaz(tmp_path):
    """kayit['id'] drives every path ek_indir builds (.parca/<id>.part,
    <id><uzanti>); an unvalidated id can carry `../` — confirmed by direct
    reproduction: sandbox/.parca/../../disari/evil.part's mkdir(parents=True)
    really does create `disari` next to `sandbox`, outside the run's own
    directory. A future caller bug (or an id built by hand instead of
    ek_kimligi()) must be refused before any path is touched, not exploited."""
    disari = tmp_path.parent / "disari-yazilmamali"
    assert not disari.exists()
    kayit = {"id": "../../disari-yazilmamali/evil", "url": SP_URL, "type": ek_turu(SP_URL)}
    sonuc = ek_indir(SahteOturum({SP: SahteYanit(200, PDF, {"Content-Type": "application/pdf"})}),
                     kayit, tmp_path, _sinirsiz())
    assert sonuc.durum == "hata" and "kimli" in sonuc.neden.lower()
    assert not disari.exists()
    assert list(tmp_path.iterdir()) == []


def test_bos_kimlik_de_reddedilir(tmp_path):
    kayit = {"id": "", "url": SP_URL, "type": ek_turu(SP_URL)}
    sonuc = ek_indir(SahteOturum({}), kayit, tmp_path, _sinirsiz())
    assert sonuc.durum == "hata"
    assert list(tmp_path.iterdir()) == []


def test_portal_cerezleri_yalniz_portal_istegine_gider(tmp_path):
    kavanoz = portal_cerez_kavanozu([
        {"name": "ASP.NET_SessionId", "value": "ornek-oturum", "domain": "portal.tedronesans.k12.tr", "path": "/"},
        {"name": "izci", "value": "x", "domain": ".google.com", "path": "/"},
    ])
    assert [c.name for c in kavanoz] == ["ASP.NET_SessionId"]
    oturum = SahteOturum({
        "https://portal.tedronesans.k12.tr/": lambda u, h: SahteYanit(200, PDF, {"Content-Type": "application/pdf"}),
        SP: lambda u, h: SahteYanit(200, PDF, {"Content-Type": "application/pdf"}),
    })
    ek_indir(oturum, _kayit(PORTAL_URL), tmp_path, _sinirsiz(), cerezler=kavanoz)
    ek_indir(oturum, _kayit(SP_URL), tmp_path, _sinirsiz(), cerezler=kavanoz)
    assert oturum.istekler[0]["cookies"] is kavanoz
    assert oturum.istekler[1]["cookies"] is None
    assert portal_cerez_kavanozu([]) is None and portal_cerez_kavanozu(None) is None


# ---------------------------------------------------------------------------
# Real `requests` against a loopback HTTPS server (fix round 1, R1/R3/R5/R7).
# ---------------------------------------------------------------------------

YEREL = "127.0.0.1"
# A dripping or silent handler gives up after this long, so a regression makes
# a timing test fail (it measures well over 2.5 s) instead of hanging the suite.
AZAMI_OYALAMA = 8.0


def _oyalama(dur, adim):
    """Yield every `adim` seconds until teardown or AZAMI_OYALAMA has passed."""
    son = time.monotonic() + AZAMI_OYALAMA
    while not dur.wait(adim) and time.monotonic() < son:
        yield


def _yalniz_yerel(host):
    """The loopback server's policy: only 127.0.0.1 may be fetched."""
    return host == YEREL


@pytest.fixture(autouse=True)
def _is_parcacigi_sizmaz():
    """Every watchdog timer is cancelled and every request thread has ended
    once a test (and its servers) is done."""
    yield
    son = time.monotonic() + 3.0
    kalan = []
    while time.monotonic() < son:
        kalan = [t.name for t in threading.enumerate() if t.name.startswith("ek-indir")]
        if not kalan:
            return
        time.sleep(0.02)
    pytest.fail(f"ek_indir iş parçacığı sızdı: {kalan}")


@pytest.fixture(scope="module")
def sertifika(tmp_path_factory):
    """A throwaway self-signed certificate for 127.0.0.1 (cryptography ships
    with google-auth, a declared requirement)."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    anahtar = ec.generate_private_key(ec.SECP256R1())
    ad = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, YEREL)])
    simdi = datetime.now(timezone.utc)
    sert = (x509.CertificateBuilder().subject_name(ad).issuer_name(ad)
            .public_key(anahtar.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(simdi - timedelta(minutes=5)).not_valid_after(simdi + timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(YEREL))]),
                           critical=False)
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(anahtar.public_key()), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(anahtar.public_key()),
                           critical=False)
            .sign(anahtar, hashes.SHA256()))
    dizin = tmp_path_factory.mktemp("sertifika")
    (dizin / "sert.pem").write_bytes(sert.public_bytes(serialization.Encoding.PEM))
    (dizin / "anahtar.pem").write_bytes(anahtar.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    return str(dizin / "sert.pem"), str(dizin / "anahtar.pem")


class _Sunucu(ThreadingHTTPServer):
    daemon_threads = False      # server_close() joins every handler thread
    block_on_close = True


def _geri_donus_calisiyor():
    try:
        with socket.create_server((YEREL, 0)) as dinleyen:
            with socket.create_connection(dinleyen.getsockname(), timeout=1):
                return True
    except OSError:
        return False


def _geri_donus_ayakta():
    """Loopback must work. Measured 2026-09-28: under `unshare -rn` (the
    network-free namespace the plan's Görev 7 step runs this file in) `lo`
    starts DOWN — and /sys/class/net still shows the host's, so it is probed
    with a real connect. Raising it touches only that private namespace (the
    only place this user has CAP_NET_ADMIN); on the host it already works.
    Never a skip: a skipped safety test proves nothing."""
    if _geri_donus_calisiyor():
        return
    ip = shutil.which("ip") or "/usr/sbin/ip"
    subprocess.run([ip, "link", "set", "lo", "up"], check=False, capture_output=True, timeout=10)
    if not _geri_donus_calisiyor():
        pytest.fail("geri dönüş arayüzü (lo) çalışmıyor ve açılamadı; yerel sunucu testleri koşamaz")


@pytest.fixture
def yerel(sertifika):
    """Start loopback HTTPS servers. `yanitla(isleyici, dur)` writes the
    response; `dur` is set at teardown so a dripping handler stops."""
    _geri_donus_ayakta()
    dur = threading.Event()
    acilan = []

    def baslat(yanitla):
        kayitlar = []

        class Isleyici(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def do_GET(self):
                kayitlar.append({"yol": self.path, "Range": self.headers.get("Range"),
                                 "If-Range": self.headers.get("If-Range"),
                                 "Cookie": self.headers.get("Cookie")})
                try:
                    yanitla(self, dur)
                except OSError:
                    pass
                self.close_connection = True

        sunucu = _Sunucu((YEREL, 0), Isleyici)
        baglam = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        baglam.load_cert_chain(*sertifika)
        sunucu.socket = baglam.wrap_socket(sunucu.socket, server_side=True)
        dongu = threading.Thread(target=sunucu.serve_forever, kwargs={"poll_interval": 0.05},
                                 name="yerel-sunucu", daemon=True)
        dongu.start()
        acilan.append((sunucu, dongu))
        return f"https://{YEREL}:{sunucu.server_address[1]}", kayitlar

    yield baslat
    dur.set()
    for sunucu, dongu in acilan:
        sunucu.shutdown()
        sunucu.server_close()
        dongu.join(5)


@pytest.fixture
def https_oturum(sertifika):
    with requests.Session() as oturum:
        oturum.verify = sertifika[0]
        yield oturum


def _dosya_kaydi(url):
    kayit = _kayit(url)
    assert kayit["type"] == "dosya", kayit
    return kayit


def _damla(uzunluk_var):
    def yanitla(h, dur):
        h.send_response(200)
        h.send_header("Content-Type", "application/pdf")
        if uzunluk_var:
            h.send_header("Content-Length", "100000")
        h.send_header("Connection", "close")
        h.end_headers()
        h.wfile.write(b"%PDF-1.7\n")
        for _ in _oyalama(dur, 0.25):
            h.wfile.write(b"x")
    return yanitla


# --- R1: a real wall-clock bound per download --------------------------------

@pytest.mark.parametrize("uzunluk_var", [True, False], ids=["uzunluklu", "kapanisa-kadar"])
def test_yavas_damlayan_govde_butceyi_asamaz(tmp_path, yerel, https_oturum, uzunluk_var):
    """Measured on 4f6f8ca: 1 byte / 0.25 s held ek_indir 6 s against a 1 s
    budget (iter_content blocks until 1 MB or EOF; each byte resets the 30 s
    read timeout). The watchdog now cuts the socket at the budget's end."""
    kok, kayitlar = yerel(_damla(uzunluk_var))
    kayit = _dosya_kaydi(f"{kok}/yavas.pdf")
    t0 = time.monotonic()
    sonuc = ek_indir(https_oturum, kayit, tmp_path, Butce(time.monotonic() + 1.0, 10 ** 12),
                     adres_izni=_yalniz_yerel)
    gecen = time.monotonic() - t0
    assert gecen < 2.5, gecen
    assert sonuc.durum == "bekliyor", sonuc
    assert len(kayitlar) == 1


def test_basliktan_once_susan_sunucu_butceyi_asamaz(tmp_path, yerel, https_oturum):
    kok, kayitlar = yerel(lambda h, dur: dur.wait(AZAMI_OYALAMA))
    t0 = time.monotonic()
    sonuc = ek_indir(https_oturum, _dosya_kaydi(f"{kok}/sessiz.pdf"), tmp_path,
                     Butce(time.monotonic() + 1.0, 10 ** 12), adres_izni=_yalniz_yerel)
    assert time.monotonic() - t0 < 2.5
    assert sonuc.durum == "bekliyor", sonuc


def test_basliklari_damlatan_sunucu_butceyi_asamaz(tmp_path, yerel, https_oturum):
    """A header line dripped a byte at a time never trips the per-read
    timeout, and there is no response object yet for the watchdog to close:
    the request itself is waited for only until the budget ends."""
    def yanitla(h, dur):
        h.wfile.write(b"HTTP/1.1 200 OK\r\nX-Damla: ")
        for _ in _oyalama(dur, 0.2):
            h.wfile.write(b"a")
    kok, _ = yerel(yanitla)
    t0 = time.monotonic()
    sonuc = ek_indir(https_oturum, _dosya_kaydi(f"{kok}/baslik.pdf"), tmp_path,
                     Butce(time.monotonic() + 1.0, 10 ** 12), adres_izni=_yalniz_yerel)
    assert time.monotonic() - t0 < 2.5
    assert sonuc.durum == "bekliyor", sonuc


def test_tam_blok_sonrasi_susan_govde_kesilince_tamam_sayilmaz(tmp_path, yerel, https_oturum):
    """Exactly one block arrives, then silence, no Content-Length. The
    watchdog's cut ends the stream with EOF and no further bytes — a "clean"
    end. Only the watchdog's flag tells a cut read from a finished file;
    without it the first 64 KiB would be stored as the whole attachment."""
    govde = PDF + b"0" * (PARCA_BOYUTU - len(PDF))

    def yanitla(h, dur):
        h.send_response(200)
        h.send_header("Content-Type", "application/pdf")
        h.send_header("Connection", "close")
        h.end_headers()
        h.wfile.write(govde)
        dur.wait(AZAMI_OYALAMA)
    kok, _ = yerel(yanitla)
    t0 = time.monotonic()
    sonuc = ek_indir(https_oturum, _dosya_kaydi(f"{kok}/yarim.pdf"), tmp_path,
                     Butce(time.monotonic() + 1.0, 10 ** 12), adres_izni=_yalniz_yerel)
    assert time.monotonic() - t0 < 2.5
    assert sonuc.durum == "bekliyor", sonuc
    assert [p.name for p in tmp_path.iterdir()] == [".parca"]


def test_yonlendirme_zinciri_bes_adimda_kesilir(tmp_path, yerel, https_oturum):
    """Measured on 4f6f8ca: requests follows 30 redirects, each with its own
    40 s of timeouts. Now at most EK_AZAMI_YONLENDIRME hops, each re-checked."""
    def yanitla(h, dur):
        n = int(h.path.strip("/").split(".")[0].lstrip("d") or 0)
        if n >= 50:                     # an unbounded follower fails here, not hangs
            h.send_response(404)
            h.send_header("Content-Length", "0")
            h.end_headers()
            return
        h.send_response(302)
        h.send_header("Location", f"/d{n + 1}.pdf")
        h.send_header("Content-Length", "0")
        h.end_headers()
    kok, kayitlar = yerel(yanitla)
    sonuc = ek_indir(https_oturum, _dosya_kaydi(f"{kok}/d0.pdf"), tmp_path, _sinirsiz(),
                     adres_izni=_yalniz_yerel)
    assert EK_AZAMI_YONLENDIRME == 5
    assert len(kayitlar) == 1 + EK_AZAMI_YONLENDIRME
    assert sonuc.durum == "erisilemedi" and "yönlendirme" in sonuc.neden


def test_istek_zaman_asimi_kalan_sureyle_sinirli_ve_yonlendirme_elle(tmp_path):
    oturum = SahteOturum({SP: SahteYanit(200, PDF, {"Content-Type": "application/pdf"})})
    ek_indir(oturum, _kayit(SP_URL), tmp_path, Butce(time.monotonic() + 5.0, 10 ** 12))
    baglanti, okuma = oturum.istekler[0]["timeout"]
    assert 4.0 < baglanti <= 5.0 and 4.0 < okuma <= 5.0
    assert oturum.istekler[0]["allow_redirects"] is False
    assert PARCA_BOYUTU == 64 * 1024


def test_istek_zaman_asimi_bol_surede_10_ve_30_sn(tmp_path):
    oturum = SahteOturum({SP: SahteYanit(200, PDF, {"Content-Type": "application/pdf"})})
    ek_indir(oturum, _kayit(SP_URL), tmp_path, Butce(time.monotonic() + 600.0, 10 ** 12))
    assert oturum.istekler[0]["timeout"] == (10.0, 30.0)


def test_butce_bitmisse_hic_istek_yapilmaz(tmp_path):
    oturum = SahteOturum({})
    sonuc = ek_indir(oturum, _kayit(SP_URL), tmp_path, Butce(time.monotonic() - 1.0, 10 ** 12))
    assert sonuc.durum == "bekliyor" and oturum.istekler == []


def test_drive_onay_istegi_de_butceyi_denetler(tmp_path):
    oturum = SahteOturum({
        "https://drive.google.com/": SahteYanit(200, DRIVE_ONAY, {"Content-Type": "text/html"}),
        "https://drive.usercontent.google.com/": SahteYanit(200, PDF, {"Content-Type": "application/pdf"})})
    sonuc = ek_indir(oturum, _kayit(DRIVE_URL), tmp_path, Butce(2.5, 10 ** 12, saat=SahteSaat(adim=1.0)))
    assert sonuc.durum == "bekliyor" and len(oturum.istekler) == 1


# --- R2: HTML is never stored -------------------------------------------------

_HTML_KILIKLARI = {
    "utf8_bom": bytes.fromhex("efbbbf") + "<!DOCTYPE html><html><body>Oturum açın</body></html>".encode("utf-8"),
    "yorum_onde": (b"<!-- Copyright (C) Ornek Kurum. All rights reserved. -->\r\n"
                   b"<!DOCTYPE html><html></html>"),
    "yalniz_head": b"<head><title>Sign in</title></head><body></body>",
    "utf16_bom": "<!DOCTYPE html><html></html>".encode("utf-16"),
    "utf16_bomsuz": "<html><body>x</body></html>".encode("utf-16-le"),
    "utf32_bom": "<html></html>".encode("utf-32"),
    "xml_bildirimi": b'<?xml version="1.0"?>\n<html xmlns="http://www.w3.org/1999/xhtml"></html>',
    "buyuk_harf_script": b"\n\t <SCRIPT>alert(1)</SCRIPT>",
    "meta": b"<meta http-equiv=refresh content=0>",
    "title": b"<TITLE>x</TITLE>",
    "body": b"<BODY onload=x()>",
    "kapanmamis_yorum": b"<!-- " + b"a" * (70 * 1024),
}


@pytest.mark.parametrize("ad", sorted(_HTML_KILIKLARI))
def test_kilik_degistirmis_html_saklanmaz(tmp_path, ad):
    """The reviewer's four bypasses of 4f6f8ca (BOM, leading comment, bare
    <head>, UTF-16) and their relatives, all sent as application/pdf."""
    govde = _HTML_KILIKLARI[ad]
    assert html_mi(govde[:PARCA_BOYUTU], "application/pdf")
    yanit = SahteYanit(200, govde, {"Content-Type": "application/pdf"})
    sonuc = ek_indir(SahteOturum({SP: yanit}), _kayit(SP_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "erisilemedi" and "web sayfası" in sonuc.neden
    assert [p.name for p in tmp_path.iterdir()] == [".parca"] and _parcalar(tmp_path) == []


@pytest.mark.parametrize("govde", [
    b"%PDF-1.7\n<html><script>alert(1)</script></html>",
    bytes.fromhex("89504e470d0a1a0a") + b"<html>",
    docx_bayt(["<html>"]),
    b"bilinmeyen ikili veri",
    b"<svg xmlns='http://www.w3.org/2000/svg'/>",
])
def test_bilinen_ikili_imza_ya_da_html_olmayan_icerik_html_sayilmaz(govde):
    assert not html_mi(govde, "application/octet-stream")


def test_html_icerik_turu_yine_yeter():
    assert html_mi(PDF, "text/html; charset=utf-8") and html_mi(b"", "application/xhtml+xml")


def test_ilk_blogu_bosluk_olan_html_sonda_yakalanir(tmp_path):
    """A host can send a first chunk of whitespace (chunked encoding yields
    per chunk): the finished file's head is checked again before it is kept."""
    yanit = SahteYanit(200, headers={"Content-Type": "application/pdf"},
                       bloklar=[b"   \r\n", b"<html><body>klasor</body></html>"])
    sonuc = ek_indir(SahteOturum({SP: yanit}), _kayit(SP_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "erisilemedi" and _parcalar(tmp_path) == []
    assert [p.name for p in tmp_path.iterdir()] == [".parca"]


# --- R3: addresses — https only, global addresses only ------------------------

class _Kaydedici(BaseAdapter):
    """A transport adapter that records what real `requests` would send."""

    def __init__(self, plan):
        super().__init__()
        self.plan = list(plan)
        self.gorulen = []

    def send(self, request, **kwargs):
        self.gorulen.append({"url": request.url, "Cookie": request.headers.get("Cookie")})
        if not self.plan:
            raise AssertionError(f"planlanmamış istek: {request.url}")
        durum, konum, govde = self.plan.pop(0)
        yanit = Response()
        yanit.status_code = durum
        yanit.url = request.url
        yanit.request = request
        yanit.headers["Content-Type"] = "application/pdf"
        if konum:
            yanit.headers["Location"] = konum
        yanit.raw = io.BytesIO(govde)
        return yanit

    def close(self):
        pass


def _kaydedici_oturum(plan):
    oturum = requests.Session()
    adaptor = _Kaydedici(plan)
    oturum.mount("https://", adaptor)
    oturum.mount("http://", adaptor)
    return oturum, adaptor


_DIS_IP = "93.184.215.14"      # a global address; the fake resolver hands it out, nothing connects


def _sahte_cozucu(tablo, cagrilar=None):
    def getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        if cagrilar is not None:
            cagrilar.append(host)
        if host not in tablo:
            raise socket.gaierror(socket.EAI_NONAME, "ad çözülemedi")
        sonuc = []
        for ip in tablo[host]:
            if ":" in ip:
                sonuc.append((socket.AF_INET6, socket.SOCK_STREAM, 6, "", (ip, port, 0, 0)))
            else:
                sonuc.append((socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port)))
        return sonuc
    return getaddrinfo


_COZUCU = {
    "dis.ornek": [_DIS_IP],
    "localhost": ["127.0.0.1", "::1"],
    "ic.ornek": ["10.20.30.40"],
    "karisik.ornek": [_DIS_IP, "192.168.1.5"],
    "cgnat.ornek": ["100.64.0.7"],
    "esleme.ornek": ["::ffff:10.0.0.1"],
    "uyumlu.ornek": ["::8.8.8.8"],                 # IPv4-compatible ::/96
    "nat64.ornek": ["64:ff9b::808:808"],           # NAT64 well-known prefix
    "cokgonderim4.ornek": ["224.0.0.1"],
    "cokgonderim6.ornek": ["ff0e::1"],
    "altidort.ornek": ["2002:a00:1::1"],           # 6to4 around 10.0.0.1
}


@pytest.mark.parametrize("url", [
    "https://127.0.0.1/rapor.pdf",
    "https://localhost/rapor.pdf",
    "https://10.1.2.3/rapor.pdf",
    "https://169.254.169.254/latest/meta-data/rapor.pdf",
    "https://[::1]/rapor.pdf",
    "https://ic.ornek/rapor.pdf",
    "https://karisik.ornek/rapor.pdf",
    "https://cgnat.ornek/rapor.pdf",
    "https://esleme.ornek/rapor.pdf",
    "https://cozulmeyen.ornek/rapor.pdf",
    "https://uyumlu.ornek/rapor.pdf",
    "https://nat64.ornek/rapor.pdf",
    "https://cokgonderim4.ornek/rapor.pdf",
    "https://cokgonderim6.ornek/rapor.pdf",
    "https://altidort.ornek/rapor.pdf",
    "https://[ff02::1]/rapor.pdf",
])
def test_varsayilan_politika_ic_adrese_gitmez(tmp_path, monkeypatch, url):
    """Measured on 4f6f8ca: a link at 127.0.0.1 was fetched and stored."""
    monkeypatch.setattr(socket, "getaddrinfo", _sahte_cozucu(_COZUCU))
    oturum, adaptor = _kaydedici_oturum([(200, None, PDF)])
    sonuc = ek_indir(oturum, _kayit(url), tmp_path, _sinirsiz())
    assert sonuc.durum == "erisilemedi" and "iç adres" in sonuc.neden
    assert adaptor.gorulen == []


def test_varsayilan_politika_genel_adrese_izin_verir(tmp_path, monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _sahte_cozucu(_COZUCU))
    oturum, adaptor = _kaydedici_oturum([(200, None, PDF)])
    sonuc = ek_indir(oturum, _kayit("https://dis.ornek/rapor.pdf"), tmp_path, _sinirsiz())
    assert sonuc.durum == "indirildi" and [g["url"] for g in adaptor.gorulen] == ["https://dis.ornek/rapor.pdf"]


@pytest.mark.parametrize("hedef", ["https://127.0.0.1/api/gizli", "https://ic.ornek/api/gizli",
                                   "https://localhost:8443/api/gizli"])
def test_izinli_adresten_ic_adrese_yonlendirme_izlenmez(tmp_path, monkeypatch, hedef):
    monkeypatch.setattr(socket, "getaddrinfo", _sahte_cozucu(_COZUCU))
    oturum, adaptor = _kaydedici_oturum([(302, hedef, b""), (200, None, b'{"gizli": 1}')])
    sonuc = ek_indir(oturum, _kayit("https://dis.ornek/odev.pdf"), tmp_path, _sinirsiz())
    assert sonuc.durum == "erisilemedi" and "iç adres" in sonuc.neden
    assert [g["url"] for g in adaptor.gorulen] == ["https://dis.ornek/odev.pdf"]
    assert [p.name for p in tmp_path.iterdir()] == [".parca"] and _parcalar(tmp_path) == []


def test_http_adresi_ve_http_ye_yonlendirme_reddedilir(tmp_path, monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _sahte_cozucu(_COZUCU))
    oturum, adaptor = _kaydedici_oturum([(200, None, PDF)])
    kavanoz = portal_cerez_kavanozu([{"name": "SID", "value": "gizli", "domain": "portal.tedronesans.k12.tr"}])
    sonuc = ek_indir(oturum, _kayit("http://portal.tedronesans.k12.tr/dosyalar/a.pdf"), tmp_path,
                     _sinirsiz(), cerezler=kavanoz)
    assert sonuc.durum == "erisilemedi" and "https" in sonuc.neden and adaptor.gorulen == []
    oturum, adaptor = _kaydedici_oturum([(302, "http://dis.ornek/odev.pdf", b""), (200, None, PDF)])
    sonuc = ek_indir(oturum, _kayit("https://dis.ornek/odev.pdf"), tmp_path, _sinirsiz())
    assert sonuc.durum == "erisilemedi" and "https" in sonuc.neden and len(adaptor.gorulen) == 1


def test_politika_sirasi_arguman_sonra_oturum_sonra_kati(tmp_path, monkeypatch):
    """Görev 6/7 drive ek_indir with SahteOturum and invented hosts: the
    session's permissive policy means no DNS at all; an explicit argument
    still wins over it."""
    cagrilar = []
    monkeypatch.setattr(socket, "getaddrinfo", _sahte_cozucu({}, cagrilar))
    yanit = lambda u, h: SahteYanit(200, PDF, {"Content-Type": "application/pdf"})  # noqa: E731
    assert ek_indir(SahteOturum({SP: yanit}), _kayit(SP_URL), tmp_path, _sinirsiz()).durum == "indirildi"
    assert cagrilar == []
    red = ek_indir(SahteOturum({SP: yanit}), _kayit(SP_URL), tmp_path / "b", _sinirsiz(),
                   adres_izni=lambda host: False)
    assert red.durum == "erisilemedi" and "iç adres" in red.neden


def test_yerel_sunucu_varsayilan_politikayla_reddedilir(tmp_path, yerel, https_oturum):
    kok, kayitlar = yerel(lambda h, dur: None)
    sonuc = ek_indir(https_oturum, _dosya_kaydi(f"{kok}/ic.pdf"), tmp_path, _sinirsiz())
    assert sonuc.durum == "erisilemedi" and "iç adres" in sonuc.neden and kayitlar == []


# --- R4: the Drive confirm target --------------------------------------------

@pytest.mark.parametrize("eylem", ["http://127.0.0.1:9/api/gizli", "https://evil.example/download",
                                   "https://drive.google.com.evil.example/download",
                                   "http://drive.usercontent.google.com/download", "//evil.example/x"])
def test_drive_onay_formu_baska_yere_gitmez(eylem):
    html = (f'<!DOCTYPE html><html><form id="download-form" action="{eylem}">'
            '<input type="hidden" name="id" value="x"></form></html>')
    assert drive_onay_adresi(html, "https://drive.google.com/uc?export=download&id=x") is None


def test_drive_onay_eski_confirm_bagi_de_izinli_hostta_kalir():
    html = '<a href="/uc?export=download&confirm=AbC1&id=x">indir</a>'
    assert drive_onay_adresi(html, "https://evil.example/uc?export=download&id=x") is None
    assert drive_onay_adresi(html, "https://drive.google.com/uc?export=download&id=x") == \
        "https://drive.google.com/uc?export=download&id=x&confirm=AbC1"


@pytest.mark.parametrize("host", ["drive.usercontent.google.com", "drive.google.com", "docs.google.com"])
def test_drive_onay_izinli_hostlari(host):
    html = (f'<form id="download-form" action="https://{host}/download">'
            '<input type="hidden" name="id" value="x"></form>')
    assert drive_onay_adresi(html, "https://drive.google.com/uc").startswith(f"https://{host}/download?id=x")


def test_kotu_onay_formu_ikinci_istek_yaptirmaz(tmp_path):
    kotu = ('<!DOCTYPE html><html><form id="download-form" action="http://127.0.0.1:9/api/gizli">'
            '<input type="hidden" name="x" value="1"></form></html>').encode("utf-8")
    oturum = SahteOturum({"https://drive.google.com/": SahteYanit(200, kotu, {"Content-Type": "text/html"})})
    sonuc = ek_indir(oturum, _kayit(DRIVE_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "erisilemedi" and len(oturum.istekler) == 1


# --- R5: portal cookies --------------------------------------------------------

def test_portal_cerezi_secure_kalir_ust_alan_adlari_dusurulur():
    kavanoz = portal_cerez_kavanozu([
        {"name": "SID", "value": "gizli", "domain": "portal.tedronesans.k12.tr", "path": "/",
         "secure": True, "httpOnly": True},
        {"name": "noktali", "value": "v", "domain": ".portal.tedronesans.k12.tr", "path": "/"},
        {"name": "genis", "value": "v", "domain": ".k12.tr", "path": "/"},
        {"name": "okul", "value": "v", "domain": "tedronesans.k12.tr", "path": "/"},
        {"name": "alt", "value": "v", "domain": "alt.portal.tedronesans.k12.tr", "path": "/"},
    ])
    assert sorted(c.name for c in kavanoz) == ["SID", "noktali"]
    assert {c.name: c.secure for c in kavanoz} == {"SID": True, "noktali": False}


def test_portal_cerezi_yonlendirmede_baska_hosta_gitmez(tmp_path):
    """Real requests, recording adapter: the cookie goes to the portal hop
    and not to the host it redirects to."""
    kavanoz = portal_cerez_kavanozu([{"name": "SID", "value": "gizli", "domain": "portal.tedronesans.k12.tr",
                                      "path": "/", "secure": True}])
    oturum, adaptor = _kaydedici_oturum([(302, "https://baska.ornek/x.pdf", b""), (200, None, PDF)])
    sonuc = ek_indir(oturum, _kayit("https://portal.tedronesans.k12.tr/dosyalar/a.pdf"), tmp_path,
                     _sinirsiz(), cerezler=kavanoz, adres_izni=lambda host: True)
    assert sonuc.durum == "indirildi"
    assert adaptor.gorulen == [
        {"url": "https://portal.tedronesans.k12.tr/dosyalar/a.pdf", "Cookie": "SID=gizli"},
        {"url": "https://baska.ornek/x.pdf", "Cookie": None}]


def test_portal_disi_kayit_cerezi_hic_gondermez(tmp_path):
    kavanoz = portal_cerez_kavanozu([{"name": "SID", "value": "gizli", "domain": "portal.tedronesans.k12.tr"}])
    oturum, adaptor = _kaydedici_oturum([(302, "https://portal.tedronesans.k12.tr/a.pdf", b""),
                                         (200, None, PDF)])
    ek_indir(oturum, _kayit("https://dis.ornek/odev.pdf"), tmp_path, _sinirsiz(), cerezler=kavanoz,
             adres_izni=lambda host: True)
    assert [g["Cookie"] for g in adaptor.gorulen] == [None, None]


# --- R6: the zip probe cannot throw or blow memory -----------------------------

def _gecersiz_adli_zip():
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as z:
        z.writestr("word/document.xml", "<x/>")
    ham = bytearray(tampon.getvalue())
    cd = ham.rfind(bytes.fromhex("504b0102"))
    ham[cd + 9] |= 0x08            # general-purpose flag bit 11: names are UTF-8
    ham[cd + 46] = 0xFF            # ... and the first name byte is not
    return bytes(ham)


def _cok_girdili_zip(n, ad_bicimi="{:08d}"):
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_STORED) as z:
        for i in range(n):
            z.writestr(ad_bicimi.format(i), b"")
    return tampon.getvalue()


class _ZipAcilmamali:
    """Stands in for zipfile.ZipFile and records the attempt: raising alone
    would be swallowed by tur_bul's own `except Exception`."""
    acilislar = []

    def __init__(self, *a, **k):
        _ZipAcilmamali.acilislar.append(a)
        raise zipfile.BadZipFile("merkez dizini listelenmemeliydi")


@pytest.fixture
def zip_acilmamali(monkeypatch):
    """Call it once the test's archive is built (zipfile is one module)."""
    _ZipAcilmamali.acilislar = []
    yield lambda: monkeypatch.setattr(indir_modulu.zipfile, "ZipFile", _ZipAcilmamali)
    assert _ZipAcilmamali.acilislar == []


def test_gecersiz_utf8_adli_zip_istisna_firlatmaz(tmp_path):
    yol = tmp_path / "a.bin"
    yol.write_bytes(_gecersiz_adli_zip())
    assert tur_bul(yol.read_bytes()[:4096], yol) == (".zip", "application/zip")
    sonuc = ek_indir(SahteOturum({SP: SahteYanit(200, _gecersiz_adli_zip(), {"Content-Type": "application/pdf"})}),
                     _kayit(SP_URL), tmp_path / "d", _sinirsiz())
    assert (sonuc.durum, sonuc.uzanti) == ("indirildi", ".zip")


def test_cok_girdili_zip_listelenmez(tmp_path, zip_acilmamali):
    yol = tmp_path / "a.bin"
    yol.write_bytes(_cok_girdili_zip(20_000))
    zip_acilmamali()
    assert tur_bul(yol.read_bytes()[:4096], yol) == (".zip", "application/zip")


def test_girdi_sayisi_yalan_soylese_de_buyuk_merkez_dizini_listelenmez(tmp_path, zip_acilmamali):
    ham = bytearray(_cok_girdili_zip(20_000))
    son = ham.rfind(bytes.fromhex("504b0506"))
    ham[son + 8:son + 12] = struct.pack("<HH", 3, 3)      # "3 entries" — the directory holds 20 000
    yol = tmp_path / "a.bin"
    yol.write_bytes(bytes(ham))
    zip_acilmamali()
    assert tur_bul(bytes(ham[:4096]), yol) == (".zip", "application/zip")


def test_zip64_bulucusu_olan_zip_listelenmez(tmp_path, zip_acilmamali):
    ham = bytearray(docx_bayt(["x"]))
    son = ham.rfind(bytes.fromhex("504b0506"))
    ham[son:son] = bytes.fromhex("504b0607") + bytes(16)   # a zip64 locator right before the record
    yol = tmp_path / "a.bin"
    yol.write_bytes(bytes(ham))
    zip_acilmamali()
    assert tur_bul(bytes(ham[:4096]), yol) == (".zip", "application/zip")


def test_sonu_olmayan_zip_bin_olur(tmp_path):
    govde = docx_bayt(["x"])
    yol = tmp_path / "a.bin"
    yol.write_bytes(govde[:govde.rfind(bytes.fromhex("504b0506"))])
    assert tur_bul(yol.read_bytes()[:4096], yol) == (".bin", "application/octet-stream")


def test_kucuk_docx_hala_docx(tmp_path):
    yol = tmp_path / "a.bin"
    yol.write_bytes(docx_bayt(["Soru"]))
    assert tur_bul(yol.read_bytes()[:4096], yol) == (".docx", DOCX_MIME)


# --- R7: a resume never mixes two versions -------------------------------------

def _surumlu(durum):
    """A host with Range + If-Range; `durum` is swapped between runs."""
    def yanitla(h, dur):
        govde, etag, lm = durum["govde"], durum.get("etag"), durum.get("lm")
        aralik, kosul = h.headers.get("Range"), h.headers.get("If-Range")
        if aralik and (durum.get("if_range_yok_say") or kosul is None or kosul in (etag, lm)):
            bas = int(aralik.split("=", 1)[1].rstrip("-"))
            parca = govde[bas:]
            h.send_response(206)
            h.send_header("Content-Range", f"bytes {bas}-{len(govde) - 1}/{len(govde)}")
        else:
            parca = govde
            h.send_response(200)
        h.send_header("Content-Type", "application/pdf")
        h.send_header("Content-Length", str(len(parca)))
        if etag:
            h.send_header("ETag", etag)
        if lm:
            h.send_header("Last-Modified", lm)
        h.send_header("Connection", "close")
        h.end_headers()
        h.wfile.write(parca)
    return yanitla


_ESKI = PDF + b"A" * (300 * 1024)
_YENI = PDF + b"B" * (300 * 1024) + b"C" * 1000


def _ilk_tur(tmp_path, oturum, kayit):
    sonuc = ek_indir(oturum, kayit, tmp_path, Butce(float("inf"), 2 * PARCA_BOYUTU), adres_izni=_yalniz_yerel)
    assert sonuc.durum == "bekliyor" and sonuc.parca_bayt == 2 * PARCA_BOYUTU
    return sonuc


def test_surum_degisince_yeni_surum_bastan_iner(tmp_path, yerel, https_oturum):
    """Measured on 4f6f8ca: a Range resume after the file changed stored the
    old head glued to the new tail. If-Range now makes the host send the new
    version whole."""
    durum = {"govde": _ESKI, "etag": '"v1"'}
    kok, kayitlar = yerel(_surumlu(durum))
    kayit = _dosya_kaydi(f"{kok}/degisen.pdf")
    _ilk_tur(tmp_path, https_oturum, kayit)
    yan = json.loads((tmp_path / ".parca" / f"{kayit['id']}.meta.json").read_text(encoding="utf-8"))
    assert yan == {"etag": '"v1"', "last_modified": None, "toplam": len(_ESKI)}
    durum.update(govde=_YENI, etag='"v2"')
    sonuc = ek_indir(https_oturum, kayit, tmp_path, _sinirsiz(), adres_izni=_yalniz_yerel)
    assert sonuc.durum == "indirildi"
    assert kayitlar[1]["Range"] == f"bytes={2 * PARCA_BOYUTU}-" and kayitlar[1]["If-Range"] == '"v1"'
    assert (tmp_path / sonuc.dosya).read_bytes() == _YENI
    assert _parcalar(tmp_path) == []


def test_surum_ayni_ise_kaldigi_yerden_surer(tmp_path, yerel, https_oturum):
    durum = {"govde": _ESKI, "etag": '"v1"'}
    kok, kayitlar = yerel(_surumlu(durum))
    kayit = _dosya_kaydi(f"{kok}/ayni.pdf")
    _ilk_tur(tmp_path, https_oturum, kayit)
    sonuc = ek_indir(https_oturum, kayit, tmp_path, _sinirsiz(), adres_izni=_yalniz_yerel)
    assert sonuc.durum == "indirildi" and (tmp_path / sonuc.dosya).read_bytes() == _ESKI
    assert kayitlar[1]["If-Range"] == '"v1"'


def test_if_range_i_yok_sayan_host_baska_toplamla_206_verirse_reddedilir(tmp_path, yerel, https_oturum):
    durum = {"govde": _ESKI, "etag": '"v1"'}
    kok, kayitlar = yerel(_surumlu(durum))
    kayit = _dosya_kaydi(f"{kok}/yalanci.pdf")
    _ilk_tur(tmp_path, https_oturum, kayit)
    durum.update(govde=_YENI, etag=None, if_range_yok_say=True)
    ikinci = ek_indir(https_oturum, kayit, tmp_path, _sinirsiz(), adres_izni=_yalniz_yerel)
    assert ikinci.durum == "hata" and _parcalar(tmp_path) == []
    ucuncu = ek_indir(https_oturum, kayit, tmp_path, _sinirsiz(), adres_izni=_yalniz_yerel)
    assert ucuncu.durum == "indirildi" and kayitlar[2]["Range"] is None
    assert (tmp_path / ucuncu.dosya).read_bytes() == _YENI


def test_dogrulayici_yoksa_range_gonderilmez_bastan_iner(tmp_path, yerel, https_oturum):
    durum = {"govde": _ESKI}
    kok, kayitlar = yerel(_surumlu(durum))
    kayit = _dosya_kaydi(f"{kok}/etiketsiz.pdf")
    _ilk_tur(tmp_path, https_oturum, kayit)
    durum.update(govde=_YENI)
    sonuc = ek_indir(https_oturum, kayit, tmp_path, _sinirsiz(), adres_izni=_yalniz_yerel)
    assert kayitlar[1]["Range"] is None and kayitlar[1]["If-Range"] is None
    assert sonuc.durum == "indirildi" and (tmp_path / sonuc.dosya).read_bytes() == _YENI


def test_etag_yoksa_last_modified_ile_surer(tmp_path, yerel, https_oturum):
    lm = "Mon, 28 Sep 2026 08:00:00 GMT"
    durum = {"govde": _ESKI, "lm": lm}
    kok, kayitlar = yerel(_surumlu(durum))
    kayit = _dosya_kaydi(f"{kok}/tarihli.pdf")
    _ilk_tur(tmp_path, https_oturum, kayit)
    sonuc = ek_indir(https_oturum, kayit, tmp_path, _sinirsiz(), adres_izni=_yalniz_yerel)
    assert kayitlar[1]["If-Range"] == lm
    assert sonuc.durum == "indirildi" and (tmp_path / sonuc.dosya).read_bytes() == _ESKI


def test_sahte_katmanda_da_degisen_surum_karismaz(tmp_path):
    """The reviewer's scenario, on the fake layer Görev 6 uses."""
    eski = PDF + b"A" * (3 * MB)
    yeni = PDF + b"B" * (3 * MB)
    kayit = _kayit(SP_URL)
    ilk = ek_indir(SahteOturum({SP: aralikli(eski)}), kayit, tmp_path, Butce(float("inf"), MB))
    assert ilk.durum == "bekliyor"
    ikinci = ek_indir(SahteOturum({SP: aralikli(yeni)}), kayit, tmp_path, _sinirsiz())
    assert (tmp_path / ikinci.dosya).read_bytes() == yeni



# ---------------------------------------------------------------------------
# Fix round 2
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("konum", ["https://[::1/x", "https://[zz::1]/x.pdf"])
def test_bozuk_location_erisilemedi_olur_istisna_kacmaz(tmp_path, yerel, https_oturum, konum):
    """Measured on 2cb0918: `Location: https://[::1/x` made urljoin raise
    ValueError out of ek_indir — Görev 7's ekleri_esitle has no try around
    it, so one such link would stop every run's attachment step."""
    def yanitla(h, dur):
        h.send_response(302)
        h.send_header("Location", konum)
        h.send_header("Content-Length", "0")
        h.end_headers()
    kok, kayitlar = yerel(yanitla)
    sonuc = ek_indir(https_oturum, _dosya_kaydi(f"{kok}/bozuk.pdf"), tmp_path, _sinirsiz(),
                     adres_izni=_yalniz_yerel)
    assert sonuc.durum == "erisilemedi" and "adres" in sonuc.neden, sonuc
    assert len(kayitlar) == 1


def test_bozuk_onay_formu_eylemi_istisna_firlatmaz():
    html = ('<form id="download-form" action="https://[::1/download">'
            '<input type="hidden" name="id" value="x"></form>')
    assert drive_onay_adresi(html, "https://drive.google.com/uc?export=download&id=x") is None
    assert drive_onay_adresi('<a href="?confirm=AbC1">x</a>', "https://[::1/uc") is None


def test_beklenmeyen_ic_hata_hata_sonucu_olur_ve_loglanir(tmp_path, monkeypatch, caplog):
    """The contract is "never raises": a bug below ek_indir costs this one
    attachment a `hata`, not the whole attachment step."""
    def bozuk(*a, **k):
        raise RuntimeError("iç hata")
    monkeypatch.setattr(indir_modulu, "_tamamla", bozuk)
    oturum = SahteOturum({SP: SahteYanit(200, PDF, {"Content-Type": "application/pdf"})})
    with caplog.at_level(logging.WARNING, logger="src.portal_ekleri_indir"):
        sonuc = ek_indir(oturum, _kayit(SP_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "hata" and "RuntimeError" in sonuc.neden
    assert any("RuntimeError" in (r.exc_text or "") or r.exc_info for r in caplog.records)
    assert all("ornekokul" not in r.getMessage() for r in caplog.records)   # no URL in the log


@pytest.mark.parametrize("govde", [bytes(70 * 1024), b" " * (70 * 1024), b"\r\n\t" * 30000,
                                   bytes(10) + b"ikili"])
def test_yalniz_nul_ya_da_bosluk_bas_html_sayilmaz(tmp_path, govde):
    assert not html_mi(govde, "application/octet-stream")
    yanit = SahteYanit(200, govde, {"Content-Type": "application/octet-stream"})
    sonuc = ek_indir(SahteOturum({SP: yanit}), _kayit(SP_URL), tmp_path, _sinirsiz())
    assert (sonuc.durum, sonuc.uzanti) == ("indirildi", ".bin")


def test_basi_dolduran_yorum_onsozu_hala_html():
    """A prologue of closed comments filling the whole head is markup, not a
    file: otherwise padding would push the <html> tag past the window."""
    govde = b"<!-- dolgu -->\n" * (HTML_BAS_SINIRI // 15 + 10) + b"<html><body>x</body></html>"
    assert html_mi(govde, "application/octet-stream")


def test_soket_canli_yanitta_bulunur(yerel, https_oturum):
    """The watchdog reaches the socket through urllib3 private attributes
    (urllib3>=2.6,<3 pinned). An upgrade that renames them fails here, at
    once, not only as a slow drip test."""
    def yanitla(h, dur):
        h.send_response(200)
        h.send_header("Content-Length", "4")
        h.end_headers()
        h.wfile.write(b"%PDF")
    kok, _ = yerel(yanitla)
    with https_oturum.get(f"{kok}/x.pdf", stream=True, timeout=5) as yanit:
        soket = indir_modulu._soket(yanit)
        assert isinstance(soket, ssl.SSLSocket) and soket.fileno() >= 0
        assert soket.getpeername()[0] == YEREL


def test_sahte_oturumda_bozuk_location_da_erisilemedi(tmp_path):
    """A session that does not pre-parse Location (the fake layer Görev 6/7
    drive) reaches ek_indir's own urljoin: guarded there as well."""
    oturum = SahteOturum({SP: SahteYanit(302, b"", {"Location": "https://[::1/x"})})
    sonuc = ek_indir(oturum, _kayit(SP_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "erisilemedi" and "adres" in sonuc.neden and len(oturum.istekler) == 1
