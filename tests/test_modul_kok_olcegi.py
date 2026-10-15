"""Pano kök yazı boyunu bildirir; modül onu kıstırarak uygular (spec §10.2).

Köprü JS'i `sablon.py`'nin yamasıdır (vendored şablonda değil), burada node'da koşturulur.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.mcp_server import sablon

ARALIK = (12, 48)
SABLON_YOLU = Path("src/mcp_server/vendor/assets/module-template.html")


def _kopru_calistir(cagrilar: str) -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node yok")
    govde = re.search(r"function adoptHostRootSize\(rootPx\)\{.*?\n  \}", sablon.BRIDGE_JS, re.S)
    assert govde, "adoptHostRootSize köprüde yok"
    kod = "\n".join([
        "const document={documentElement:{style:{}}};",
        govde.group(0),
        cagrilar,
    ])
    return subprocess.run([node, "-e", kod], capture_output=True, text=True,
                          check=True, timeout=30).stdout


def test_gecerli_deger_uygulanir():
    out = _kopru_calistir("adoptHostRootSize(32);"
                          "process.stdout.write(String(document.documentElement.style.fontSize));")
    assert out == "32px"


@pytest.mark.parametrize("deger", ["NaN", '"32"', "Infinity", "-5", "1e9", "null", "undefined", "{}"])
def test_dusmanca_deger_yok_sayilir_ya_da_kistirilir(deger):
    out = _kopru_calistir(f"adoptHostRootSize({deger});"
                          "process.stdout.write(String(document.documentElement.style.fontSize||''));")
    assert "NaN" not in out, f"{deger} için NaNpx yazıldı"
    if out:
        sayi = float(out.removesuffix("px"))
        assert ARALIK[0] <= sayi <= ARALIK[1], f"{deger} aralık dışına çıktı: {out}"


def test_tema_degisimi_kok_olcegini_sifirlamaz():
    """applyTheme yalnız data-theme yazar; style.fontSize'a dokunmaz (spec §10.6)."""
    kaynak = SABLON_YOLU.read_text(encoding="utf-8")
    bas = kaynak.index("function applyTheme(next){")
    govde = kaynak[bas:kaynak.index("\n  }", bas)]
    assert "fontSize" not in govde, "applyTheme kök yazı boyuna dokunuyor"


def test_g_bridge_root_px_ile_gecer():
    """rootPx bir ALAN'dir, yeni mesaj tipi degil: G-BRIDGE degismeden gecer.

    Kapi mesaj TIPLERINI denetler (gates_ek.py:127-130) ve edupedia:appearance zaten
    OPTIONAL_BRIDGE_TYPES'ta (gates_ek.py:17). Plan kapiyi degistirmeyi soyluyordu; olculdu,
    gerekmiyor. Bu test gercek kapiyi gercek derlenmis cikti uzerinde kosturur.
    """
    from src.mcp_server import derleme, gates_ek, ornekler

    html = derleme.derle(ornekler.ornek("QUIZ"), None, "https://tedy.online")
    assert "adoptHostRootSize" in html, "kopru uygulayiciyi tasimiyor"
    assert "edupedia:appearance" in html

    class _Toplayici:
        def __init__(self):
            self.kayitlar: list[tuple[str, str, str]] = []

        def add(self, ad: str, durum: str, mesaj: str = "") -> None:
            self.kayitlar.append((ad, durum, mesaj))

    R = _Toplayici()
    gates_ek.gate_bridge(html, R)
    kotu = [k for k in R.kayitlar if k[1] == "FAIL"]
    assert not kotu, f"G-BRIDGE FAIL verdi: {kotu}"
