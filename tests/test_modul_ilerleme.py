"""İlerleme göstergesi: adımlar aşamadır, segment değil (Modül Tasarım Kanunu M2.4, M2.5, M5.4; KB-2, 2026-10-20).

Davranış `dashboard/tests/e2e/moduller.spec.ts`'te ölçülür (genişlikler, metin, vuruş kutusu); burada
şablonun kanunla bağlı sabitleri durur: eşikler, Carbon ikonları ve eski segment adımlarının dönmemesi.
"""
import re
from pathlib import Path

import pytest

SABLON = Path("src/mcp_server/vendor/assets/module-template.html").read_text(encoding="utf-8")
IKONLAR = Path("dashboard/node_modules/@carbon/icons/svg/32")


def test_eski_segment_adimlari_ve_hedef_metni_yok():
    for eski in (".stepper{", "step__btn", "step--milestone", 'id="railGoal"', "Son \"+left+\" durak"):
        assert eski not in SABLON, eski


@pytest.mark.parametrize("asama, esik", [(3, 42), (4, 42), (5, 42), (6, 48), (7, 56)])
def test_asama_satiri_kanunun_esiginde_acilir(asama, esik):
    """Satır yalnız kap en az max(42rem, aşama × 8rem) iken çizilir (M5.4); md 42rem, adım 8rem (Carbon)."""
    blok = re.search(r"@container ilerleme \(min-width:%drem\)\{(.*?)\n\}" % esik, SABLON, re.S)
    assert blok, esik
    assert re.search(r'data-asama="%d"' % asama, blok.group(1))
    assert ".asamalar{display:flex}" in blok.group(1) and "#railStage{display:none}" in blok.group(1)


def test_kapsayici_ust_cubuk_ve_adim_olculeri_carbon():
    assert ".topbar{container:ilerleme / inline-size}" in SABLON
    assert re.search(r"\.asama\{[^}]*min-inline-size:8rem", SABLON)
    assert re.search(r"\.asama__btn\{[^}]*min-block-size:3rem", SABLON)  # KS-11: 48 px vuruş kutusu
    assert re.search(r"\.asama__ikon\{[^}]*inline-size:1rem;block-size:1rem", SABLON)
    # Renk rolleri Carbon'un spesifikasyonu: tamamlanan/geçerli interactive, başlanmamış icon-primary.
    assert re.search(r"\.asama--incomplete \.asama__ikon\{fill:var\(--cds-icon-primary\)\}", SABLON)
    assert re.search(r"\.asama--complete::before,\.asama--current::before\{background:var\(--cds-interactive\)\}", SABLON)


@pytest.mark.parametrize("sembol, carbon", [
    ("ic-checkmark-outline", "checkmark--outline"), ("ic-incomplete", "incomplete"), ("ic-circle-dash", "circle-dash"),
])
def test_adim_ikonlari_carbon_ile_bayt_es(sembol, carbon):
    kaynak = IKONLAR / f"{carbon}.svg"
    if not kaynak.is_file():
        pytest.skip("dashboard/node_modules yok")
    beklenen = re.findall(r'<path d="([^"]+)"', kaynak.read_text(encoding="utf-8"))
    govde = re.search(r'<symbol id="%s" viewBox="0 0 32 32">(.*?)</symbol>' % sembol, SABLON).group(1)
    assert re.findall(r'<path d="([^"]+)"', govde) == beklenen
