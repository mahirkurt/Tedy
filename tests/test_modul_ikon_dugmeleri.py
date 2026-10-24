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


def test_ikon_dugmesinin_adi_arac_ipucunda_gecikmeli_ve_uzerine_gelinebilir():
    """İpucu düğmenin `aria-label`'ı; kutusu dolgu dahil ölçülür (border-box), görünürlükle açılıp kapanır (yerleşim
    hep vardır, böylece açılmadan önce çerçeveye kıstırılabilir); açılış ve kapanış 100 ms gecikmeli (@carbon/react
    IconButton `enterDelayMs`/`leaveDelayMs`); 8 px'lik boşlukta saydam bir köprü vardır, işaretçi ipucuna inerken
    ipucu kapanmaz (WCAG 1.4.13); etkinleştirmede kapanır (Carbon `closeOnActivation`), Esc kapatır (inceleme, Önemli 1–2)."""
    ipucu = re.search(r"\.icon-btn::after,\.pacing-disk__dismiss::after,\.cmap-edge__remove::after\{([^}]*)\}", SABLON)
    assert ipucu, "araç ipucu kuralı yok"
    govde = ipucu.group(1)
    for parca in ("content:attr(aria-label)", "box-sizing:border-box", "visibility:hidden", "opacity:0",
                  "var(--cds-background-inverse)", "var(--cds-text-inverse)", "var(--ipucu-x"):
        assert parca in govde, parca
    assert "display:none" not in govde
    acik = re.search(r"\.icon-btn\.ipucu-acik::after,[^{]*\{([^}]*)\}", SABLON)
    assert acik and "visibility:visible" in acik.group(1) and "opacity:1" in acik.group(1)
    kopru = re.search(r"\.icon-btn\.ipucu-acik::before,[^{]*\{([^}]*)\}", SABLON)
    assert kopru and "inset-block-start:100%" in kopru.group(1) and "block-size:var(--sp-03)" in kopru.group(1)
    # Açılış JS'le: :hover kuralı yok (Kanun M2.12'nin dışında kalır), gecikme hareket değildir (reduced-motion dokunmaz).
    assert not re.search(r"\.icon-btn:hover::after", SABLON)
    for parca in ("const IPUCU_ACIK_MS=100, IPUCU_KAPA_MS=100;", 'ev.key!=="Escape"', 'addEventListener("click"',
                  'classList.add("ipucu-kapali")', 'style.setProperty("--ipucu-x"'):
        assert parca in SABLON, parca


def test_ses_oynaticisinin_renk_semasi_tema_tokenindan():
    """`color-scheme` tema bloklarındaki token'dan gelir; bileşen kuralında `[data-theme]` seçicisi yoktur (KB-22, M4.3)."""
    assert re.search(r"(?m)^\.edupedia-audio__oynatici\{color-scheme:var\(--tedy-renk-semasi\)\}", SABLON)
    assert not re.search(r"\[data-theme[^\]]*\][^{]*edupedia-audio", SABLON)
    for blok, deger in ((':root,[data-theme="g10"]{', "light"), ('[data-theme="white"]{', "light"),
                        ('[data-theme="g100"]{', "dark")):
        bas = SABLON.index(blok)
        govde = SABLON[bas:SABLON.index("\n}", bas)]
        assert f"--tedy-renk-semasi:{deger};" in govde, (blok, deger)


def test_hotspot_bolgesinin_adi_cevabi_sizdirmaz():
    """Bölgenin erişilebilir adı sorunun cevabı (`spots[].label`) değildir; "Bölge n / N" der. Cevap ancak doğru bölge
    bulununca o bölgenin adına girer (WCAG 1.1.1: test için betimleyici tanım, cevap değil; inceleme, Küçük 12)."""
    assert 'r.setAttribute("aria-label", meta.label' not in SABLON
    assert re.search(r'setAttribute\("aria-label", ?`Bölge \$\{', SABLON)


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
    # Denetimleri tarayıcı çizer (Carbon'un ses oynatıcı bileşeni yok); temayı token'dan izler (yukarıdaki test).
    assert "color-scheme:var(--tedy-renk-semasi)" in SABLON
