"""Modülün ikon düğmeleri ve ses oynatıcısı (Modül Tasarım Kanunu M5.14; KB-44, 2026-10-24).

Akışta kalan araçlar (ses, sesli okuma) ve çerçevedeki öteki ikon düğmeleri (tempo diskini gizleme, kavram
haritasında bağlantıyı kaldırma) Carbon ghost ikon düğmesidir: lg 48 px (`--tap`, 3rem: 4K'da kökle büyür), ikon
20 px (1.25rem), adı araç ipucunda — fareyle ve klavye odağında açılır, Esc ile kapanır (talimatname §4.3). Sesli
okuma ("Oku") düğmesi de 48 px'tir. Yazarın ses varlığı sınıflı bir `audio` öğesiyle, adlı Carbon katmanında çizilir.
Bunlar statik sözleşmedir; ölçüm (`getBoundingClientRect`, `::after` içeriği, Esc) `dashboard/tests/e2e/
modul-ikon-dugmeleri.spec.ts`'tedir.
"""
import re

import pytest

from src.mcp_server import derleme, ornekler, sablon

SABLON = sablon.TEMPLATE_PATH.read_text(encoding="utf-8")
IKON_DUGMELERI = (".icon-btn", ".pacing-disk__dismiss", ".cmap-edge__remove")


def _kural(secici: str) -> str:
    """Seçicinin ilk temel kural gövdesi (`secici{...}`; `:root[...] secici` ezmeleri değil)."""
    m = re.search(r"(?m)^" + re.escape(secici) + r"\{([^}]*)\}", SABLON)
    assert m, secici
    return m.group(1)


@pytest.mark.parametrize("secici", IKON_DUGMELERI)
def test_ikon_dugmesi_lg_48_px_ve_ikonu_20_px(secici):
    govde = _kural(secici)
    assert "width:var(--tap)" in govde and "height:var(--tap)" in govde, govde
    assert "position:relative" in govde  # ipucu düğmeye göre konumlanır
    assert re.search(r"--tap:3rem", SABLON)
    ikon = _kural(f"{secici} .cds-icon")
    assert "width:1.25rem" in ikon and "height:1.25rem" in ikon, ikon


def test_sesli_okuma_dugmesi_48_px():
    assert "min-height:var(--tap)" in _kural(".tts-oku")


def test_ikon_dugmesinin_adi_arac_ipucunda_ve_kosulsuz_hover_yok():
    ipucu = re.search(r"\.icon-btn::after,\.pacing-disk__dismiss::after,\.cmap-edge__remove::after\{([^}]*)\}", SABLON)
    assert ipucu, "araç ipucu kuralı yok"
    govde = ipucu.group(1)
    assert "content:attr(aria-label)" in govde and "display:none" in govde
    assert "var(--cds-background-inverse)" in govde and "var(--cds-text-inverse)" in govde
    # Fareyle açılış yalnız fareli girişte (Kanun M2.12), odakla açılış her zaman, Esc'in sınıfı en sonda kapatır.
    assert re.search(r"@media \(any-hover:hover\)\{[^@]*\.icon-btn:hover::after[^{]*\{display:block\}", SABLON)
    odak = SABLON.index(".icon-btn:focus-visible::after,")
    kapali = SABLON.index(".icon-btn.ipucu-kapali::after,")
    assert odak < kapali
    for secici in IKON_DUGMELERI:
        assert f"{secici}:focus-visible::after" in SABLON and f"{secici}.ipucu-kapali::after" in SABLON
    assert re.search(r'ev\.key!=="Escape"', SABLON) and 'classList.add("ipucu-kapali")' in SABLON


def test_her_ikon_dugmesi_adli():
    """Şablonun yazdığı her ikon düğmesi (ikon taşıyan ama metni olmayan `<button>`) bir aria-label taşır."""
    dugmeler = []
    for m in re.finditer(r"(<button\b[^>]*>)((?:(?!</?button\b).)*?)</button>", SABLON, re.S):
        icerik = re.sub(r"\$\{icon\([^)]*\)\}|<[^>]+>", "", m.group(2)).strip()
        if not icerik and re.search(r"<svg\b|\$\{icon\(", m.group(2)):
            dugmeler.append(m.group(1))
    assert len(dugmeler) >= 4, dugmeler  # soundBtn, ttsBtn, pacingDiskDismiss, cmap-edge__remove
    for d in dugmeler:
        assert re.search(r'aria-label="[^"]+"', d), d


def test_yazarin_ses_varligi_sinifli_oynaticida_ve_adli():
    data, varliklar = ornekler.arac_ornegi()
    html = derleme.derle(data, varliklar, "https://tedy.online")
    sesler = re.findall(r"<audio\b[^>]*>", html)
    assert sesler, "ses oynatıcısı yok"
    for oge in sesler:
        assert re.search(r'class="[^"]+"', oge), f"sınıfsız audio (M5.14): {oge}"
        assert "aria-label=" in oge and "autoplay" not in oge
    assert '<audio class="edupedia-audio__oynatici" controls' in html
    # Denetimleri tarayıcı çizer (Carbon'un ses oynatıcı bileşeni yok); temayı izler.
    assert re.search(r':root\[data-theme="g100"\] \.edupedia-audio__oynatici\{color-scheme:dark\}', SABLON)
