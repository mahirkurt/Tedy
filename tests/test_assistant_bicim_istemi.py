"""The answer's format rules (D1): the closed block vocabulary, math and tables,
and when to clarify. The dashboard renders exactly these names; a block the
prompt teaches and the renderer does not know would print as plain text."""
from src.assistant_core import AssistantRuntime

P = AssistantRuntime.SYSTEM_PROMPT
BICIM = P.split("## Biçim\n", 1)[1].split("\n## ", 1)[0]


def test_bes_blok_adi_ogretilir():
    for ad in ("kavram", "ornek", "adimlar", "sonuc", "hata"):
        assert f":::{ad}" in BICIM, ad
    assert "\n:::\n" in BICIM or "`:::`" in BICIM  # kapanış satırı öğretilir


def test_formul_ve_ondalik_virgul():
    assert "$" in BICIM and "$$" in BICIM
    assert "{,}" in BICIM


def test_tablo_artik_serbest_ama_sinirli():
    assert "Tablo" in BICIM or "tablo" in BICIM
    assert "4 sütun" in BICIM and "6 satır" in BICIM
    assert "Tablo, yatay çizgi" not in BICIM  # eski yasak cümlesi gitti


def test_simdi_ve_not_korunur():
    assert "**Şimdi:**" in BICIM and "**Not:**" in BICIM


def test_netlestirme_bolumu():
    bolum = P.split("## Netleştirme\n", 1)[1].split("\n## ", 1)[0]
    assert "`netlestir`" in bolum
    assert "iki" in bolum  # art arda ikiden fazla netleştirme sorma
