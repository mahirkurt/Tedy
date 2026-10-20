"""Modül başlık düzeni (2026-10-19): şablonun `basliga`sı panonun `utils/baslik.ts`'iyle aynı kural.

Modül ve bölüm adları ad öbeğidir; her sözcük büyük harfle, bağlaç ve soru eki küçük, yalnız ilk
harf büyür. Tablo `dashboard/tests/baslik.test.ts`'ten okunur, şablonun JS'i node'da koşar.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SABLON = Path("src/mcp_server/vendor/assets/module-template.html")
TABLO = Path("dashboard/tests/baslik.test.ts")


def _ornekler() -> list[tuple[str, str]]:
    return [(a.replace("\\'", "'"), b.replace("\\'", "'")) for a, b in
            re.findall(r"\['((?:[^'\\]|\\.)*)', '((?:[^'\\]|\\.)*)'\]", TABLO.read_text(encoding="utf-8"))]


def test_sablon_basligasi_panoyla_ayni():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node yok")
    kaynak = SABLON.read_text(encoding="utf-8")
    bas = kaynak.index("  const BASLIK_KUCUK")
    son = kaynak.index("\n  }\n", kaynak.index("function basliga(metin){", bas)) + 4
    ornekler = _ornekler()
    assert len(ornekler) >= 10
    kod = kaynak[bas:son] + f"\nprocess.stdout.write(JSON.stringify({json.dumps([a for a, _ in ornekler])}.map(basliga)));"
    cikti = json.loads(subprocess.run([node, "-e", kod], capture_output=True, text=True, check=True, timeout=30).stdout)
    assert cikti == [b for _, b in ornekler]


def test_sablon_basliklari_acilista_duzenler_ve_html_tasiyani_atlar():
    kaynak = SABLON.read_text(encoding="utf-8")
    assert 'D.meta.title.indexOf("<")<0) D.meta.title=basliga(D.meta.title);' in kaynak
    assert 's.title.indexOf("<")<0) s.title=basliga(s.title);' in kaynak
    # titleText ilk kez düzenlenmiş adla yazılır
    assert kaynak.index("s.title=basliga(s.title)") < kaynak.index('$("#titleText").textContent = D.meta.title')


def test_acilista_odak_tasinmaz_okur_gecince_tasinir():
    kaynak = SABLON.read_text(encoding="utf-8")
    govde = kaynak[kaynak.index("  function render(){"):kaynak.index("  function segHead(")]
    assert "const odakla = okurGecti; okurGecti = false;" in govde
    assert "focusStageHeading(stage);" not in govde.replace("if(odakla) focusStageHeading(stage);", "")
    for yer in ("state.idx++; persistSession(); okurGecti=true; render();",
                "state.idx--; okurGecti=true; render();",
                # The progress indicator's finished stage (Kanun M2.4, 2026-10-20) is a reader move too.
                "state.idx=st.start; okurGecti=true; render();"):
        assert yer in kaynak
