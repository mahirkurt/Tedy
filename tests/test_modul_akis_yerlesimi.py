"""Panoda akış yerleşimi: modül panonun bir bölümü gibi durur (2026-10-19).

Pano `edupedia:appearance` ile `layout: "flow"` bildirir; köprü `<html data-host-layout="flow">`
yazar ve gövde yüksekliğini `edupedia:size` ile panoya gönderir, pano çerçeveyi o boya büyütür.
Köprü JS'i `sablon.py`'nin yamasıdır, burada node'da koşturulur; CSS bloğu vendored şablondadır.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.mcp_server import sablon

SABLON_YOLU = Path("src/mcp_server/vendor/assets/module-template.html")
KOKEN = "https://tedy.online"


def _akis_blogu() -> str:
    kaynak = SABLON_YOLU.read_text(encoding="utf-8")
    bas = kaynak.index("PANODA AKIŞ YERLEŞİMİ")
    bas = kaynak.index("*/", bas) + 2  # açıklama yorumu kural değildir
    return kaynak[bas:kaynak.index("@media (prefers-reduced-motion:reduce)", bas)]


def _kopru_calistir(cagrilar: str) -> list:
    """Köprünün akış fonksiyonlarını sahte bir pencereyle koşturur; gönderilen mesajları döner."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node yok")
    js = sablon.BRIDGE_JS
    bas = js.index("  let flowOn = false")
    son = js.index("    if(embedded){", bas)
    kod = "\n".join([
        "const giden=[]; let boy=812.4; const gozlenen=[];",
        "const document={documentElement:{attrs:{},setAttribute(k,v){this.attrs[k]=v;}},",
        "  body:{getBoundingClientRect(){return {height:boy};}}};",
        "const window={parent:{postMessage(m,o){giden.push([m,o]);}}};",
        "class ResizeObserver{constructor(cb){this.cb=cb;} observe(el){gozlenen.push(this);}}",
        f"const EDUPEDIA_PARENT_ORIGIN={json.dumps(KOKEN)};",
        js[bas:son],
        cagrilar,
        "process.stdout.write(JSON.stringify({giden, attrs:document.documentElement.attrs}));",
    ])
    out = subprocess.run([node, "-e", kod], capture_output=True, text=True, check=True, timeout=30).stdout
    return json.loads(out)


def test_akis_bildirilince_yukseklik_sabit_origine_gider():
    sonuc = _kopru_calistir('adoptHostLayout("flow");')
    assert sonuc["attrs"] == {"data-host-layout": "flow"}
    assert sonuc["giden"] == [[{"type": "edupedia:size", "v": 1, "height": 813}, KOKEN]]


@pytest.mark.parametrize("deger", ['"akis"', "undefined", "null", "1", '{"flow":1}'])
def test_akis_disi_deger_yerlesimi_degistirmez(deger):
    sonuc = _kopru_calistir(f"adoptHostLayout({deger});")
    assert sonuc == {"giden": [], "attrs": {}}


def test_ayni_boy_yeniden_gonderilmez_degisen_gonderilir():
    sonuc = _kopru_calistir('adoptHostLayout("flow"); adoptHostLayout("flow");'
                            "gozlenen[0].cb(); boy=1200; gozlenen[0].cb();")
    assert [m["height"] for m, _ in sonuc["giden"]] == [813, 1200]


def test_bolum_degisince_basa_don_istegi_tasir():
    sonuc = _kopru_calistir('adoptHostLayout("flow"); postSize(true);')
    assert sonuc["giden"][-1] == [{"type": "edupedia:size", "v": 1, "height": 813, "top": True}, KOKEN]


def test_derlenmis_modul_g_bridge_ve_yamalari_tasir():
    from src.mcp_server import derleme, gates_ek, ornekler

    html = derleme.derle(ornekler.ornek("QUIZ"), None, KOKEN)
    assert "edupedia:size" in html and "adoptHostLayout" in html
    assert 'window.scrollTo({top:0,behavior:"instant"});\n    EDUPEDIA_BRIDGE.toTop();' in html

    class _Toplayici:
        def __init__(self):
            self.kayitlar: list[tuple[str, str, str]] = []

        def add(self, ad: str, durum: str, mesaj: str = "") -> None:
            self.kayitlar.append((ad, durum, mesaj))

    R = _Toplayici()
    gates_ek.gate_bridge(html, R)
    assert not [k for k in R.kayitlar if k[1] == "FAIL"], R.kayitlar


def test_akis_blogu_kabugu_kaldirir_ve_yalniz_token_kullanir():
    blok = _akis_blogu()
    # 100vh tabanı kalmalı: yoksa çerçeve boyu içeriği, içerik çerçeveyi büyütür (geri besleme).
    assert re.search(r"\.wrap\{[^}]*min-height:0", blok)
    # Lacivert bant panonun üst bandında; modülün içinde ikinci bir bant olmaz.
    assert re.search(r"\.topbar__hero\{[^}]*background:transparent", blok)
    assert "--tedy-brand" not in blok
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", blok), \
        "akış bloğunda ham renk var"
    assert not re.search(r"box-shadow", blok), "statik yüzeye gölge (S11)"


def test_akista_baslik_bloku_panoya_birakilir():
    """Başlık, ders ve kazanımlar panonun ders panelinde (ModulBasligi); modülde yinelenmez."""
    blok = _akis_blogu()
    assert re.search(r"\.topbar__l\{display:none\}", blok)


def test_akista_zemin_panonun_sayfa_zeminidir():
    """Kanun M1.2 (KB-3): akışta çerçevenin zemini panonun cool-gray sayfa zeminidir, Carbon'un gri
    `--cds-background`'u değil — ölçüldü, #f4f4f4 çerçeve #f2f4f8 sayfada ayrı tonlu bir kutu gibi duruyordu."""
    blok = _akis_blogu()
    assert re.search(r"\bbody\{background:var\(--tedy-page-background\)\}", blok)
    assert "--cds-background" not in blok
    kaynak = SABLON_YOLU.read_text(encoding="utf-8")
    g10 = kaynak[kaynak.index(':root,[data-theme="g10"]'):]
    zemin = re.search(r"--tedy-page-background:(#[0-9a-fA-F]{6})", g10).group(1).lower()
    pano = Path("dashboard/src/theme/ted-theme.scss").read_text(encoding="utf-8")
    assert "--ted-color-page-bg: #{colors.$cool-gray-10};" in pano
    assert zemin == "#f2f4f8"  # Carbon cool-gray-10 (@carbon/colors)
