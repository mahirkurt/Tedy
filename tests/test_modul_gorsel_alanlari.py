"""Yazarın görsel alanları: alt metin, görünür altyazı ve atıf satırı (Modül Tasarım Kanunu M3.6–M3.8;
KB-10, KB-11, KB-12, 2026-10-23).

`meta.assets[i]` raster görselde `alt` (60–150 karakter bitmiş cümle ya da süs görseli için "") ve `baslik`
(kitaptaki adıyla görünür altyazı, en çok 120 karakter) taşır; derleyici varlık kaydının 200 karakterlik
VLM kesiğini kullanmaz. Atıf varlık başına tek satırdır, figürün adını taşır, sayfa yazmaz ve yinelenmez.
"""
import html as html_lib
import json
import re
import shutil
import subprocess
from html.parser import HTMLParser

import pytest

from src.mcp_server import derleme, gates, ornekler, sablon
from src.mcp_server.derleme import DerlemeHatasi, GomuluVarlik
from src.mcp_server.gorsel import MEB_CREDIT, MEB_LISANS

ORIGIN = "https://tedy.online"
ALT = "Askerler toprak bir yolda cephane yüklü kağnıların yanında yürüyor."
BASLIK = "Görsel 1.30: İstiklal Yolu yürüyüşü"
VLM_KESIGI = ("The image shows a group of soldiers walking beside ox carts on a dirt road while carrying "
              "ammunition boxes during the national struggle and several people are watching from a hill "
              "nearby the")[:200]


def _teach(data):
    return next(s for s in data["segments"] if s["type"] == "teach")


def _varlik(asset_id="a1b2c3d4e5f60718", tur="image", credit=MEB_CREDIT, kaynak="mufredat"):
    mime = {"image": "image/jpeg", "video": "video/mp4", "ses": "audio/mpeg", "muzik": "audio/mpeg"}[tur]
    return GomuluVarlik(asset_id=asset_id, tur=tur, mime=mime, data_uri=f"data:{mime};base64,QUJD", bayt=1000,
                        credit=credit, lisans=MEB_LISANS, alt=VLM_KESIGI, kaynak=kaynak)


def _modul(*refs):
    data = ornekler.ornek("MODULE")
    _teach(data).pop("visual", None)
    data["meta"]["assets"] = list(refs)
    return data


def _ref(asset_id="a1b2c3d4e5f60718", slot=None, **alanlar):
    data = ornekler.ornek("MODULE")
    ref = {"asset_id": asset_id, "slot": slot or f"{_teach(data)['id']}.visual"}
    ref.update(alanlar)
    return ref


def _hatalar(data, varliklar):
    with pytest.raises(DerlemeHatasi) as exc:
        derleme.derle(data, varliklar, ORIGIN)
    assert exc.value.status == "sema_hatasi", exc.value.status
    return exc.value.detay["hatalar"]


# ── KB-10 (M3.6): yazarın alt metni ─────────────────────────────────────────

def test_raster_gorselde_alt_ve_baslik_zorunlu():
    img = _varlik()
    hatalar = _hatalar(_modul(_ref()), {img.asset_id: img})
    assert any(h.startswith("meta.assets[0].alt zorunlu") for h in hatalar), hatalar
    assert any(h.startswith("meta.assets[0].baslik zorunlu") for h in hatalar), hatalar


@pytest.mark.parametrize("alt, parca", [
    ("Kısa bir cümle.", "60–150 karakter"),
    ("Askerler " + "uzun bir yolda " * 12 + "yürüyor.", "60–150 karakter"),
    ("Askerler toprak bir yolda cephane yüklü kağnıların yanında yürüyor", "bitmiş bir cümle"),
    ("Bu fotoğrafta askerler toprak bir yolda kağnıların yanında yürüyor.", "Bu fotoğraf/çizim/şema"),
    ("Bu şema askerlerin toprak bir yolda kağnılarla nasıl yürüdüğünü gösterir.", "Bu fotoğraf/çizim/şema"),
    ("bu çizimde askerler toprak bir yolda kağnıların yanında yürüyor.", "Bu fotoğraf/çizim/şema"),
    (42, "metin"),
])
def test_alt_metin_kurallari(alt, parca):
    img = _varlik()
    hatalar = _hatalar(_modul(_ref(alt=alt, baslik=BASLIK)), {img.asset_id: img})
    assert any(h.startswith("meta.assets[0].alt") and parca in h for h in hatalar), hatalar


def test_derleyici_yazarin_alt_metnini_kullanir_vlm_kesigini_degil():
    img = _varlik()
    html = derleme.derle(_modul(_ref(alt=ALT, baslik=BASLIK)), {img.asset_id: img}, ORIGIN)
    assert ALT in html
    assert VLM_KESIGI not in html
    assert f'visual: {{kind: "image", asset: "{img.asset_id}", alt: "{ALT}", caption: "{BASLIK}"}}' in html


def test_sus_gorseli_baslik_istemez_ve_altyazi_cizilmez():
    # Son inceleme, Küçük 9 (karar): süs görseli (alt "") altyazı almaz; figcaption çizilmez, atıf satırı
    # adsız künyedir.
    img = _varlik()
    html = derleme.derle(_modul(_ref(alt="")), {img.asset_id: img}, ORIGIN)
    assert f'visual: {{kind: "image", asset: "{img.asset_id}", alt: ""}}' in html
    cizim = _gorselleri_ciz(html)
    assert 'alt=""' in cizim and "<figcaption" not in cizim
    assert _altbilgi_satirlari(html) == [MEB_CREDIT]


def test_sus_gorseli_altyazi_tasimaz():
    img = _varlik()
    hatalar = _hatalar(_modul(_ref(alt="", baslik=BASLIK)), {img.asset_id: img})
    assert any(h.startswith("meta.assets[0].baslik") and "süs görseli" in h for h in hatalar), hatalar


@pytest.mark.parametrize("alt", [
    '"Bu fotoğrafta askerler toprak bir yolda kağnıların yanında yürüyor."',
    "«Bu çizimde askerler toprak bir yolda kağnıların yanında yürüyor.»",
    "“Bu şema askerlerin toprak bir yolda kağnılarla nasıl yürüdüğünü gösterir.”",
    "(Bu fotoğrafta) askerler toprak bir yolda kağnıların yanında yürüyor.",
    "— Bu fotoğrafta askerler toprak bir yolda kağnıların yanında yürüyor.",
    "BU FOTOG" + chr(0x306) + "RAFTA ASKERLER TOPRAK BİR YOLDA KAĞNILARIN YANINDA YÜRÜYOR.",
])
def test_tirnak_ayrac_ve_ayrisik_harf_yasak_acilisi_gizlemez(alt):
    # Son inceleme, Küçük 8: tırnak, ayraç ya da tireyle açılan ve ayrışık (NFD) harfle yazılan
    # "Bu fotoğraf…" da yakalanır.
    img = _varlik()
    hatalar = _hatalar(_modul(_ref(alt=alt, baslik=BASLIK)), {img.asset_id: img})
    assert any(h.startswith("meta.assets[0].alt") and "Bu fotoğraf/çizim/şema" in h for h in hatalar), hatalar


def test_turkce_kucult_ayrisik_harfi_birlestirir():
    assert derleme.turkce_kucult("GO" + chr(0x308) + "RSEL") == "görsel"
    assert derleme.turkce_kucult("I" + chr(0x307) + "STIKLAL") == "istıklal"


@pytest.mark.parametrize("gerekce, parca", [("kısa", "en az 20"), ("", "en az 20"), ([], "metin")])
def test_alt_gerekce_bos_gecilmez(gerekce, parca):
    img = _varlik()
    hatalar = _hatalar(_modul(_ref(alt=ALT, baslik=BASLIK, alt_gerekce=gerekce)), {img.asset_id: img})
    assert any("alt_gerekce" in h and parca in h for h in hatalar), hatalar


def test_ses_yuvasi_gorsel_alanlarini_almaz():
    data = ornekler.ornek("MODULE")
    ses = _varlik("0f1e2d3c4b5a6978", tur="ses", credit="Seslendirme: yapay zekâ ile üretildi (MiniMax speech-2.8-hd)")
    ref = {"asset_id": ses.asset_id, "slot": f"{_teach(data)['id']}.audio", "baslik": "Seslendirme"}
    hatalar = _hatalar(_modul(ref), {ses.asset_id: ses})
    assert any("meta.assets[0]" in h and "ses" in h for h in hatalar), hatalar


# ── KB-11 (M3.7, M5.14): görünür altyazı ve ses oynatıcısı ──────────────────

@pytest.mark.parametrize("baslik, parca", [
    ("Görsel 1.30: " + "İstiklal Yolu yürüyüşü " * 6, "en çok 120"),
    ("Görsel 1.30:\nİstiklal Yolu", "tek satır"),
    ("Görsel 1.30: İstiklal Yolu, sayfa 42", "sayfa"),
    ("Ders kitabındaki İstiklal Yolu görseli", "kitap"),
    ("   ", "zorunlu"),
])
def test_baslik_kurallari(baslik, parca):
    img = _varlik()
    hatalar = _hatalar(_modul(_ref(alt=ALT, baslik=baslik)), {img.asset_id: img})
    assert any(h.startswith("meta.assets[0].baslik") and parca in h for h in hatalar), hatalar


class _FigurDenetcisi(HTMLParser):
    """Her <img>'in bir <figure> içinde olduğunu ve o figürün dolu bir <figcaption> taşıdığını toplar."""

    def __init__(self):
        super().__init__()
        self.yigin, self.figurler, self.imgler = [], [], []

    def handle_starttag(self, tag, attrs):
        if tag == "figure":
            self.yigin.append({"img": 0, "altyazi": ""})
            self.figurler.append(self.yigin[-1])
        elif tag == "img":
            self.imgler.append(dict(attrs))
            if self.yigin:
                self.yigin[-1]["img"] += 1
            else:
                self.imgler[-1]["figursuz"] = True
        elif tag == "figcaption" and self.yigin:
            self.yigin[-1]["altyazida"] = True

    def handle_endtag(self, tag):
        if tag == "figure" and self.yigin:
            self.yigin.pop()
        elif tag == "figcaption" and self.yigin:
            self.yigin[-1]["altyazida"] = False

    def handle_data(self, data):
        if self.yigin and self.yigin[-1].get("altyazida"):
            self.yigin[-1]["altyazi"] += data


def _gorselleri_ciz(html: str) -> str:
    """Derlenmiş modülün bağlanmış görsellerini motorun kendi çizicisiyle (sablon.py yaması) çizer."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node yok")
    bas = html.index("const MODULE_DATA = ")
    son = html.index(sablon.ENGINE_MARKER, bas)
    varliklar = re.search(r'<script type="application/json" id="edupedia-varliklar">(.*?)</script>', html, re.S)
    js = sablon.BRIDGE_JS
    cizici = js[js.index("  function edupediaAssetUri"):js.index("  const EDUPEDIA_BRIDGE")]
    kod = "\n".join([
        "const esc = s => String(s).replace(/[&<>\"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]));",
        "function icon(ad){ return `<svg class=\"cds-icon\" aria-hidden=\"true\"><use href=\"#${ad}\"></use></svg>`; }",
        "const EDUPEDIA_ASSETS = " + (varliklar.group(1) if varliklar else "{}") + ";",
        html[bas:son].replace("const MODULE_DATA =", "globalThis.MD ="),
        cizici,
        "process.stdout.write(MD.segments.map(s => (s.visual && (s.visual.kind==='image'||s.visual.kind==='video'))"
        " ? edupediaAssetFigure(s.visual) : '').join('') + MD.segments.map(s => edupediaAudio(s.audio)).join(''));",
    ])
    return subprocess.run([node, "-e", kod], capture_output=True, text=True, check=True, timeout=30).stdout


def test_her_img_figure_ve_gorunur_figcaption_icinde():
    img = _varlik()
    html = derleme.derle(_modul(_ref(alt=ALT, baslik=BASLIK)), {img.asset_id: img}, ORIGIN)
    cizim = _gorselleri_ciz(html)
    denetci = _FigurDenetcisi()
    denetci.feed(cizim)
    assert len(denetci.imgler) == 1
    assert not any(i.get("figursuz") for i in denetci.imgler)
    assert denetci.imgler[0]["alt"] == ALT
    assert all(f["img"] == 0 or 0 < len(f["altyazi"].strip()) <= 120 for f in denetci.figurler)
    assert [f["altyazi"].strip() for f in denetci.figurler if f["img"]] == [BASLIK]
    # Satır içi stil yok (KB-26); boyutu şablonun CSS'i verir.
    assert "style=" not in cizim
    sablon_metni = sablon.TEMPLATE_PATH.read_text(encoding="utf-8")
    assert re.search(r"figure\.viz img[^{]*\{[^}]*max-width:100%", sablon_metni)


def test_ses_oynaticisi_carbon_dilinde_gorunur_etiketli():
    data = ornekler.ornek("MODULE")
    ses = _varlik("0f1e2d3c4b5a6978", tur="ses", credit="Seslendirme: yapay zekâ ile üretildi (MiniMax speech-2.8-hd)")
    data["meta"]["assets"] = [{"asset_id": ses.asset_id, "slot": f"{_teach(data)['id']}.audio"}]
    cizim = _gorselleri_ciz(derleme.derle(data, {ses.asset_id: ses}, ORIGIN))
    assert '<div class="edupedia-audio" role="group"' in cizim
    assert re.search(r'<span class="edupedia-audio__ad"[^>]*>.*Seslendirme</span>', cizim)
    sablon_metni = sablon.TEMPLATE_PATH.read_text(encoding="utf-8")
    kural = re.search(r"\.edupedia-audio\{([^}]*)\}", sablon_metni)
    assert kural, ".edupedia-audio stilsiz (M5.14)"
    assert "var(--cds-border-subtle)" in kural.group(1) and "var(--cds-layer-02)" in kural.group(1)
    assert re.search(r"(?m)^\.ses-kaydirici\{[^}]*block-size:var\(--tap\)", sablon_metni)  # 48 px dokunma (KB-49)


# ── KB-12 (M3.8): atıf satırı ───────────────────────────────────────────────

def _altbilgi_satirlari(html):
    footer = re.search(r'<footer id="edupedia-atif"[^>]*>(.*?)</footer>', html, re.S).group(1)
    return [html_lib.unescape(p) for p in re.findall(r"<p>(.*?)</p>", footer)][1:]


def test_atif_varlik_basina_tek_satir_ve_figurun_adini_tasir():
    a, b = _varlik(), _varlik("0123456789abcdef")
    data = _modul(_ref(alt=ALT, baslik=BASLIK))
    next(s for s in data["segments"] if s["id"] == "t2").pop("visual", None)
    data["meta"]["assets"].append(_ref("0123456789abcdef", slot="t2.visual", alt=ALT, baslik="Görsel 1.31: Kağnı"))
    html = derleme.derle(data, {a.asset_id: a, b.asset_id: b}, ORIGIN)
    satirlar = _altbilgi_satirlari(html)
    assert f"{BASLIK} — {MEB_CREDIT}" in satirlar
    assert f"Görsel 1.31: Kağnı — {MEB_CREDIT}" in satirlar
    assert len(satirlar) == len(set(satirlar)), satirlar
    assert gates.run_gates(html)["G-ATTRIB"]["status"] == "PASS"


def test_iki_varlik_ayni_adi_tasiyamaz():
    a, b = _varlik(), _varlik("0123456789abcdef")
    data = _modul(_ref(alt=ALT, baslik=BASLIK))
    next(s for s in data["segments"] if s["id"] == "t2").pop("visual", None)
    data["meta"]["assets"].append(_ref("0123456789abcdef", slot="t2.visual", alt=ALT, baslik=BASLIK))
    hatalar = _hatalar(data, {a.asset_id: a, b.asset_id: b})
    assert any("meta.assets[1].baslik" in h and "aynı" in h for h in hatalar), hatalar


def test_ayrisik_yazilmis_ayni_ad_da_ayni_addir():
    a, b = _varlik(), _varlik("0123456789abcdef")
    data = _modul(_ref(alt=ALT, baslik=BASLIK))
    next(s for s in data["segments"] if s["id"] == "t2").pop("visual", None)
    ayrisik = BASLIK.replace("ö", "o" + chr(0x308))
    assert ayrisik != BASLIK
    data["meta"]["assets"].append(_ref("0123456789abcdef", slot="t2.visual", alt=ALT, baslik=ayrisik))
    hatalar = _hatalar(data, {a.asset_id: a, b.asset_id: b})
    assert any("meta.assets[1].baslik" in h and "aynı" in h for h in hatalar), hatalar


def test_ayni_varlik_iki_yuvada_farkli_adla_yazilamaz():
    # Son inceleme, Küçük 10 (karar): aynı asset_id farklı baslik taşıyamaz — atıf satırı varlık başına tektir.
    a = _varlik()
    data = _modul(_ref(alt=ALT, baslik=BASLIK))
    next(s for s in data["segments"] if s["id"] == "t2").pop("visual", None)
    data["meta"]["assets"].append(_ref(a.asset_id, slot="t2.visual", alt=ALT, baslik="Görsel 1.31: Kağnı"))
    hatalar = _hatalar(data, {a.asset_id: a})
    assert any("meta.assets[1].baslik" in h and "aynı varlık" in h for h in hatalar), hatalar


def test_ayni_varlik_iki_yuvada_ayni_adla_tek_atif_satiri_alir():
    a = _varlik()
    data = _modul(_ref(alt=ALT, baslik=BASLIK))
    next(s for s in data["segments"] if s["id"] == "t2").pop("visual", None)
    data["meta"]["assets"].append(_ref(a.asset_id, slot="t2.visual", alt=ALT, baslik=BASLIK))
    html = derleme.derle(data, {a.asset_id: a}, ORIGIN)
    assert _altbilgi_satirlari(html) == [f"{BASLIK} — {MEB_CREDIT}"]


def test_g_attrib_yinelenen_satirda_duser():
    img = _varlik()
    html = derleme.derle(_modul(_ref(alt=ALT, baslik=BASLIK)), {img.asset_id: img}, ORIGIN)
    satir = f"<p>{html_lib.escape(BASLIK + ' — ' + MEB_CREDIT, quote=False)}</p>"
    assert satir in html
    rapor = gates.run_gates(html.replace(satir, satir + satir, 1))
    assert rapor["G-ATTRIB"]["status"] == "FAIL"
    assert "yinelenen" in rapor["G-ATTRIB"]["detail"]


def test_atif_sayfa_numarasi_yazmaz():
    img = _varlik()
    html = derleme.derle(_modul(_ref(alt=ALT, baslik=BASLIK)), {img.asset_id: img}, ORIGIN)
    for satir in _altbilgi_satirlari(html):
        assert not re.search(r"(?:sayfa|s\.)\s*\d", satir, re.I), satir


def test_eski_ses_atifi_degismez():
    data = ornekler.ornek("MODULE")
    ses = _varlik("0f1e2d3c4b5a6978", tur="ses", credit="Seslendirme: yapay zekâ ile üretildi (MiniMax speech-2.8-hd)")
    data["meta"]["assets"] = [{"asset_id": ses.asset_id, "slot": f"{_teach(data)['id']}.audio"}]
    html = derleme.derle(data, {ses.asset_id: ses}, ORIGIN)
    assert _altbilgi_satirlari(html)[0] == ses.credit
    assert json.loads(re.search(r'id="edupedia-varliklar">(.*?)</script>', html, re.S).group(1)
                      .replace("\\u003c", "<"))[ses.asset_id]["credit"] == ses.credit
