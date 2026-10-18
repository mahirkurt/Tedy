"""SEBİT VCloud's login: the captcha, the XML answer and the backoff.

Measured 2026-10-18. `output/sync.log` held 833 "[SEBIT-HW] Login may have
failed" lines and the last good `sebit_homework.json` was from 2026-09-24.
The login page now shows an image captcha (`captchaResponse`, hidden
`captchaId`, `<img id="captchaImg">` in `.captcha-rows`) once the failed-
attempt counter `csidValue` reaches 3, and the scraper never filled it. The
form posts by AJAX to `/login` and answers XML:

    <result><key>…</key><message>…</message><csidValue>N</csidValue>…</result>

With the captcha read correctly the live answer was `login.incorrect`,
`csidValue` 8: the stored password is no longer accepted, which only a human
can fix — and a cron that retries it every 15 minutes is how an account gets
locked (`login.userblocked`). So a refused password is recorded and the
login is not tried again with the same credentials for 24 hours.
"""
import json
import os
from datetime import datetime, timedelta

import pytest
from selenium.common.exceptions import NoSuchElementException


# ── the XML answer ─────────────────────────────────────────────────────────

def _xml(**alanlar):
    govde = "".join(f"<{k}>{v}</{k}>" for k, v in alanlar.items())
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<result>{govde}</result>'


@pytest.fixture
def sb():
    import src.scrape_sebit_homework as sb
    return sb


def test_basarili_giris_afterloginurl_e_gider(sb):
    yanit = _xml(key="login.success", message="100",
                 afterLoginUrl="https://uygulama.sebitvcloud.com/edu/index.html",
                 redirectURL="https://www.sebitvcloud.com/tr/index.jsp")

    assert sb.giris_sonucu(yanit) == (
        "basarili", "https://uygulama.sebitvcloud.com/edu/index.html")


@pytest.mark.parametrize("bos", ["", "null", "undefined"])
def test_basarili_giris_afterloginurl_bossa_redirecturl_e_gider(sb, bos):
    """The page's own afterLogin: an empty, "null" or "undefined"
    afterLoginUrl falls back to redirectURL."""
    yanit = _xml(message="100", afterLoginUrl=bos,
                 redirectURL="https://www.sebitvcloud.com/edu/index.html")

    assert sb.giris_sonucu(yanit) == (
        "basarili", "https://www.sebitvcloud.com/edu/index.html")


def test_basarili_giris_hedefsiz(sb):
    assert sb.giris_sonucu(_xml(message="100")) == ("basarili", "")


def test_sifre_hatali(sb):
    yanit = _xml(key="login.incorrect",
                 message="Kullanıcı adınızı ve/veya şifrenizi hatalı girdiniz.",
                 csidValue="8")

    durum, ayrinti = sb.giris_sonucu(yanit)

    assert durum == "sifre_hatali"
    assert "hatalı" in ayrinti


def test_hesap_kapali(sb):
    yanit = _xml(key="login.userblocked", message="Hesap kapalı", csidValue="9")

    assert sb.giris_sonucu(yanit)[0] == "hesap_kapali"


def test_kod_hatali(sb):
    yanit = _xml(key="login.captcha",
                 message="Geçersiz bir güvenlik kodu girdiniz, lütfen tekrar deneyin.",
                 csidValue="4")

    assert sb.giris_sonucu(yanit)[0] == "kod_hatali"


@pytest.mark.parametrize("anahtar", [
    "license.individualuser", "login.notverifiedemail", "login.noemailregistered",
    "login.userNotVerified", "login.uncompletedregisteration",
    "login.teachershouldregister",
])
def test_diger_anahtarlar_bilinmiyor_ve_sunucunun_sozunu_tasir(sb, anahtar):
    durum, ayrinti = sb.giris_sonucu(_xml(key=anahtar, message="Sunucunun sözü"))

    assert durum == "bilinmiyor"
    assert "Sunucunun sözü" in ayrinti


def test_mesajsiz_anahtar_adi_ayrintiya_girer(sb):
    durum, ayrinti = sb.giris_sonucu(_xml(key="license.individualuser"))

    assert (durum, ayrinti) == ("bilinmiyor", "license.individualuser")


@pytest.mark.parametrize("bozuk", [
    None, "", "   ", "<result><message>100</message>",  # unclosed
    "<html><body>502 Bad Gateway</body></html>",
    "<result></result>", 42,
    '<!DOCTYPE r [<!ENTITY e "100">]><result><message>&e;</message></result>',
])
def test_bos_ya_da_bozuk_yanit_bilinmiyor(sb, bozuk):
    """A truncated answer must never read as a success."""
    durum, ayrinti = sb.giris_sonucu(bozuk)

    assert durum == "bilinmiyor"
    assert ayrinti


def test_uzun_sunucu_mesaji_kisaltilir(sb):
    durum, ayrinti = sb.giris_sonucu(_xml(key="x", message="a" * 1000))

    assert durum == "bilinmiyor" and len(ayrinti) <= 200


# ── the backoff decision ───────────────────────────────────────────────────

SIMDI = datetime(2026, 10, 18, 14, 5)


def _kayit(sonuc="sifre_hatali", zaman=SIMDI, parmak_izi="abc"):
    return {"sonuc": sonuc, "zaman": zaman.isoformat(), "parmak_izi": parmak_izi}


def test_ayni_parmak_izi_24_saat_icinde_denenmez(sb):
    kayit = _kayit(zaman=SIMDI - timedelta(hours=23, minutes=59))

    assert sb.giris_denensin_mi(kayit, "abc", SIMDI) is False


def test_hesap_kapali_da_24_saat_bekler(sb):
    kayit = _kayit(sonuc="hesap_kapali", zaman=SIMDI - timedelta(hours=1))

    assert sb.giris_denensin_mi(kayit, "abc", SIMDI) is False


def test_24_saat_sonra_yeniden_denenir(sb):
    kayit = _kayit(zaman=SIMDI - timedelta(hours=24))

    assert sb.giris_denensin_mi(kayit, "abc", SIMDI) is True


def test_kimlik_bilgisi_degisince_hemen_denenir(sb):
    kayit = _kayit(zaman=SIMDI - timedelta(minutes=15))

    assert sb.giris_denensin_mi(kayit, "yeni", SIMDI) is True


@pytest.mark.parametrize("kayit", [
    None, [], "metin", {}, {"sonuc": "sifre_hatali", "parmak_izi": "abc"},
    {"sonuc": "sifre_hatali", "parmak_izi": "abc", "zaman": "dün"},
    {"sonuc": "sifre_hatali", "parmak_izi": "abc", "zaman": 5},
    {"sonuc": "kod_hatali", "parmak_izi": "abc", "zaman": SIMDI.isoformat()},
    # a stamp from the future would otherwise stop the login until then
    {"sonuc": "sifre_hatali", "parmak_izi": "abc",
     "zaman": (SIMDI + timedelta(days=30)).isoformat()},
])
def test_bozuk_ya_da_ilgisiz_kayit_denemeyi_durdurmaz(sb, kayit):
    assert sb.giris_denensin_mi(kayit, "abc", SIMDI) is True


@pytest.mark.parametrize("icerik", [b"{bozuk", b"\xff\xfe\x00", b"[1, 2]", b""])
def test_okunamayan_durum_dosyasi_denensin_demektir(sb, tmp_path, monkeypatch, icerik):
    yol = tmp_path / ".sebit_giris.json"
    yol.write_bytes(icerik)
    monkeypatch.setattr(sb, "GIRIS_DURUMU", str(yol))

    assert sb.giris_denensin_mi(sb._durum_oku(), "abc", SIMDI) is True


def test_parmak_izi_kimlik_bilgisine_baglidir_ve_sifreyi_tasimaz(sb):
    a = sb.parmak_izi("12345678901", "gizli-sifre")

    assert a == sb.parmak_izi("12345678901", "gizli-sifre")
    assert a != sb.parmak_izi("12345678901", "baska-sifre")
    assert a != sb.parmak_izi("12345678902", "gizli-sifre")
    assert len(a) == 16 and "gizli" not in a


# ── the login flow, with a fake browser ────────────────────────────────────

class _Oge:
    def __init__(self, gorunur=True, png=b"png"):
        self._gorunur = gorunur
        self.screenshot_as_png = png

    def is_displayed(self):
        return self._gorunur


class _Surucu:
    """Driver stand-in: the login page, a captcha row, and a queue of /login
    answers that `execute_async_script` hands back one per submit."""

    def __init__(self, cevaplar, kod_gorunur=True):
        self._cevaplar = list(cevaplar)
        self._kod_gorunur = kod_gorunur
        self.gidilenler = []
        self.gonderimler = []
        self.ekran_goruntuleri = []
        self.current_url = ""

    def get(self, url):
        self.gidilenler.append(url)
        self.current_url = url

    def find_element(self, by, secici):
        bulunan = self.find_elements(by, secici)
        if not bulunan:
            raise NoSuchElementException(secici)
        return bulunan[0]

    def find_elements(self, by, secici):
        if secici == ".captcha-rows":
            return [_Oge(self._kod_gorunur)]
        if secici in ("l_un", "l_pw", "captchaImg"):
            return [_Oge()]
        return []

    def set_script_timeout(self, sure):
        self.betik_suresi = sure

    def execute_async_script(self, betik, *args):
        self.gonderimler.append(args)
        return self._cevaplar.pop(0)

    def save_screenshot(self, yol):
        self.ekran_goruntuleri.append(yol)
        return True

    def quit(self):
        self.kapandi = True


class _Ocr:
    def __init__(self, okumalar):
        self._okumalar = list(okumalar)
        self.okunan = 0

    def classification(self, png):
        self.okunan += 1
        return self._okumalar.pop(0)


def _cevap(**alanlar):
    return {"s": 200, "b": _xml(**alanlar)}


BASARILI = _cevap(message="100",
                  afterLoginUrl="https://uygulama.sebitvcloud.com/edu/index.html")
KOD_HATALI = _cevap(key="login.captcha",
                    message="Geçersiz bir güvenlik kodu girdiniz, lütfen tekrar deneyin.",
                    csidValue="4")
SIFRE_HATALI = _cevap(key="login.incorrect",
                      message="Kullanıcı adınızı ve/veya şifrenizi hatalı girdiniz.",
                      csidValue="8")
HESAP_KAPALI = _cevap(key="login.userblocked", message="", csidValue="9")


@pytest.fixture
def giris(sb, tmp_path, monkeypatch):
    monkeypatch.setattr(sb, "SEBIT_TC", "12345678901")
    monkeypatch.setattr(sb, "SEBIT_PASSWORD", "gizli-sifre")
    monkeypatch.setattr(sb, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(sb, "GIRIS_DURUMU", str(tmp_path / ".sebit_giris.json"))
    monkeypatch.setattr(sb, "SAYFA_BEKLEME", 1)
    return sb


def _durum(sb):
    with open(sb.GIRIS_DURUMU, encoding="utf-8") as f:
        return json.load(f)


def test_kod_okunur_gonderilir_ve_hedefe_gidilir(giris):
    surucu = _Surucu([BASARILI])
    ocr = _Ocr(["38108"])

    assert giris.sebit_login(surucu, ocr) is True

    (kullanici, sifre, kod), = surucu.gonderimler
    assert (kullanici, sifre, kod) == ("12345678901", "gizli-sifre", "38108")
    assert surucu.gidilenler[-1] == "https://uygulama.sebitvcloud.com/edu/index.html"
    assert not os.path.exists(giris.GIRIS_DURUMU)


def test_kod_satiri_gizliyse_ocr_calismaz(giris):
    surucu = _Surucu([BASARILI], kod_gorunur=False)
    ocr = _Ocr([])

    assert giris.sebit_login(surucu, ocr) is True
    assert ocr.okunan == 0
    assert surucu.gonderimler[0][2] == ""


def test_hedefsiz_basari_goreli_adresi_cozer(giris):
    surucu = _Surucu([_cevap(message="100", afterLoginUrl="null",
                             redirectURL="/edu/index.html")])

    assert giris.sebit_login(surucu, _Ocr(["11111"])) is True
    assert surucu.gidilenler[-1] == "https://www.sebitvcloud.com/edu/index.html"


def test_kod_hatasi_taze_kodla_yeniden_denenir(giris):
    surucu = _Surucu([KOD_HATALI, BASARILI])
    ocr = _Ocr(["11111", "22222"])

    assert giris.sebit_login(surucu, ocr) is True
    assert [g[2] for g in surucu.gonderimler] == ["11111", "22222"]
    # each attempt reloads the page, so each code is a fresh captcha
    assert sum("giris.jsp" in u for u in surucu.gidilenler) == 2


def test_rakam_olmayan_okuma_gonderilmez(giris):
    """A misread captcha is not submitted: a wrong code feeds the counter."""
    surucu = _Surucu([BASARILI])
    ocr = _Ocr(["3B1O8", "38108"])

    assert giris.sebit_login(surucu, ocr) is True
    assert [g[2] for g in surucu.gonderimler] == ["38108"]


def test_kod_hatasi_en_cok_uc_kez(giris):
    surucu = _Surucu([KOD_HATALI] * 5)
    ocr = _Ocr(["11111"] * 5)

    with pytest.raises(giris.SebitGirisHatasi) as hata:
        giris.sebit_login(surucu, ocr)

    assert len(surucu.gonderimler) == 3
    assert "güvenlik kodu" in str(hata.value)
    assert not os.path.exists(giris.GIRIS_DURUMU)


def test_sifre_hatasinda_hemen_durur_ve_kaydeder(giris):
    surucu = _Surucu([SIFRE_HATALI, BASARILI])

    with pytest.raises(giris.SebitSifreHatali) as hata:
        giris.sebit_login(surucu, _Ocr(["38108", "11111"]))

    assert len(surucu.gonderimler) == 1
    mesaj = str(hata.value)
    assert "SEBIT_TC/SEBIT_PASSWORD" in mesaj
    assert "son deneme" in mesaj and "sonraki deneme" in mesaj

    kayit = _durum(giris)
    assert kayit["sonuc"] == "sifre_hatali"
    assert kayit["parmak_izi"] == giris.parmak_izi("12345678901", "gizli-sifre")
    ham = open(giris.GIRIS_DURUMU, encoding="utf-8").read()
    assert "gizli-sifre" not in ham and "12345678901" not in ham


def test_hesap_kapaliysa_hemen_durur_ve_kaydeder(giris):
    surucu = _Surucu([HESAP_KAPALI])

    with pytest.raises(giris.SebitHesapKapali) as hata:
        giris.sebit_login(surucu, _Ocr(["38108"]))

    assert "okulla" in str(hata.value)
    assert _durum(giris)["sonuc"] == "hesap_kapali"


def test_tanimsiz_yanit_sunucunun_sozuyle_hata(giris):
    surucu = _Surucu([_cevap(key="license.individualuser",
                             message="vitaminegitim.com üzerinden giriş yapın")])

    with pytest.raises(giris.SebitGirisHatasi) as hata:
        giris.sebit_login(surucu, _Ocr(["38108"]))

    assert "vitaminegitim.com" in str(hata.value)
    assert not os.path.exists(giris.GIRIS_DURUMU)


def test_ag_hatasi_tanimsiz_yanittir(giris):
    surucu = _Surucu([{"s": -1, "b": "TypeError: Failed to fetch"}])

    with pytest.raises(giris.SebitGirisHatasi):
        giris.sebit_login(surucu, _Ocr(["38108"]))


def test_basari_eski_kaydi_siler(giris):
    with open(giris.GIRIS_DURUMU, "w", encoding="utf-8") as f:
        json.dump(_kayit(zaman=datetime.now() - timedelta(days=2),
                         parmak_izi=giris.parmak_izi("12345678901", "gizli-sifre")), f)

    assert giris.sebit_login(_Surucu([BASARILI]), _Ocr(["38108"])) is True
    assert not os.path.exists(giris.GIRIS_DURUMU)


# ── scrape(): the backoff makes no network call ────────────────────────────

def _surucu_yasak():
    raise AssertionError("a backed-off run must not start a browser")


def test_ertelenen_kosu_tarayici_acmaz_ama_hata_sayilir(giris, monkeypatch):
    zaman = datetime.now() - timedelta(hours=2)
    with open(giris.GIRIS_DURUMU, "w", encoding="utf-8") as f:
        json.dump(_kayit(zaman=zaman,
                         parmak_izi=giris.parmak_izi("12345678901", "gizli-sifre")), f)
    monkeypatch.setattr(giris, "create_driver", _surucu_yasak)

    with pytest.raises(giris.SebitSifreHatali) as hata:
        giris.scrape()

    mesaj = str(hata.value)
    assert zaman.strftime("%d.%m %H:%M") in mesaj
    assert (zaman + timedelta(hours=24)).strftime("%d.%m %H:%M") in mesaj


def test_ertelenen_kapali_hesap_da_kapali_der(giris, monkeypatch):
    with open(giris.GIRIS_DURUMU, "w", encoding="utf-8") as f:
        json.dump(_kayit(sonuc="hesap_kapali", zaman=datetime.now(),
                         parmak_izi=giris.parmak_izi("12345678901", "gizli-sifre")), f)
    monkeypatch.setattr(giris, "create_driver", _surucu_yasak)

    with pytest.raises(giris.SebitHesapKapali):
        giris.scrape()


def test_kimlik_bilgisi_yoksa_tarayici_acilmaz(giris, monkeypatch):
    monkeypatch.setattr(giris, "SEBIT_PASSWORD", "")
    monkeypatch.setattr(giris, "create_driver", _surucu_yasak)

    with pytest.raises(giris.SebitGirisHatasi) as hata:
        giris.scrape()

    assert "SEBIT_TC/SEBIT_PASSWORD" in str(hata.value)


def test_degisen_sifre_girisi_hemen_dener(giris, monkeypatch):
    with open(giris.GIRIS_DURUMU, "w", encoding="utf-8") as f:
        json.dump(_kayit(zaman=datetime.now(),
                         parmak_izi=giris.parmak_izi("12345678901", "eski-sifre")), f)
    surucu = _Surucu([SIFRE_HATALI])
    monkeypatch.setattr(giris, "create_driver", lambda: surucu)
    monkeypatch.setattr(giris, "ocr_olustur", lambda: _Ocr(["38108"]))

    with pytest.raises(giris.SebitSifreHatali):
        giris.scrape()

    assert len(surucu.gonderimler) == 1
    assert getattr(surucu, "kapandi", False)
    assert _durum(giris)["parmak_izi"] == giris.parmak_izi("12345678901", "gizli-sifre")


# ── what health.json says ──────────────────────────────────────────────────

def test_platform_adimi_sifre_cumlesini_kaydeder(giris, monkeypatch):
    from src.run_sync import _platform_adimi

    with open(giris.GIRIS_DURUMU, "w", encoding="utf-8") as f:
        json.dump(_kayit(zaman=datetime(2026, 10, 18, 14, 5),
                         parmak_izi=giris.parmak_izi("12345678901", "gizli-sifre")), f)
    monkeypatch.setattr(giris, "create_driver", _surucu_yasak)
    monkeypatch.setattr(giris, "datetime", _SabitSaat)

    hatalar = []
    _platform_adimi("sebit_homework", "src.scrape_sebit_homework", hatalar)

    assert hatalar == [
        "sebit_homework: SEBİT kullanıcı adı ya da şifresi kabul edilmedi; "
        ".env'deki SEBIT_TC/SEBIT_PASSWORD güncellenmeli "
        "(son deneme 18.10 14:05, sonraki deneme 19.10 14:05)"
    ]


def test_platform_adimi_kapali_hesap_cumlesini_kaydeder(giris, monkeypatch):
    from src.run_sync import _platform_adimi

    with open(giris.GIRIS_DURUMU, "w", encoding="utf-8") as f:
        json.dump(_kayit(sonuc="hesap_kapali", zaman=datetime(2026, 10, 18, 14, 5),
                         parmak_izi=giris.parmak_izi("12345678901", "gizli-sifre")), f)
    monkeypatch.setattr(giris, "create_driver", _surucu_yasak)
    monkeypatch.setattr(giris, "datetime", _SabitSaat)

    hatalar = []
    _platform_adimi("sebit_homework", "src.scrape_sebit_homework", hatalar)

    assert hatalar == [
        "sebit_homework: SEBİT hesabı kapalı; okulla iletişime geçin "
        "(son deneme 18.10 14:05, sonraki deneme 19.10 14:05)"
    ]


class _SabitSaat(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 18, 16, 0)


def test_cli_giris_hatasini_cumleyle_bildirir(sb, monkeypatch, capsys):
    def patlat():
        raise sb.SebitSifreHatali("SEBİT kullanıcı adı ya da şifresi kabul edilmedi")

    monkeypatch.setattr(sb, "scrape", patlat)

    with pytest.raises(SystemExit) as cikis:
        sb.main()

    assert cikis.value.code == 1
    assert "kabul edilmedi" in capsys.readouterr().out
