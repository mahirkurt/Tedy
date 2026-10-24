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
    assert re.search(r"--tap:3rem", SABLON)
    ikon = _kural(f"{secici} .cds-icon")
    assert "width:1.25rem" in ikon and "height:1.25rem" in ikon, ikon


def test_sesli_okuma_dugmesi_48_px():
    assert "min-height:var(--tap)" in _kural(".tts-oku")


def test_ikon_dugmesinin_adi_arac_ipucunda_gecikmeli_ve_uzerine_gelinebilir():
    """İpucu düğmenin `aria-label`'ı; tek, ayrı bir `role="tooltip"` öğesidir (`#aracIpucu`, gövdenin sonunda, hiçbir
    düğmenin içinde değil; düğmeye `aria-describedby` ile bağlanır) — ona ya da köprüsüne tıklamak düğmeyi
    etkinleştirmez (ikinci inceleme, Önemli). Kutusu border-box; görünürlükle açılıp kapanır; açılış ve kapanış 100 ms
    gecikmeli; 8 px'lik köprü ipucunun parçasıdır, işaretçi ipucuna inerken kapanmaz (WCAG 1.4.13); etkinleştirmede ve
    Esc'te kapanır; JS onu çerçevenin içine yerleştirir."""
    ipucu = re.search(r"(?m)^\.arac-ipucu\{([^}]*)\}", SABLON)
    assert ipucu, "araç ipucu öğesinin kuralı yok"
    govde = ipucu.group(1)
    for parca in ("position:absolute", "box-sizing:border-box", "visibility:hidden", "opacity:0",
                  "var(--cds-background-inverse)", "var(--cds-text-inverse)", "max-inline-size:min(18rem"):
        assert parca in govde, parca
    acik = re.search(r"(?m)^\.arac-ipucu--acik\{([^}]*)\}", SABLON)
    assert acik and "visibility:visible" in acik.group(1) and "opacity:1" in acik.group(1)
    kopru = re.search(r"(?m)^\.arac-ipucu::before\{([^}]*)\}", SABLON)
    assert kopru and "inset-block-end:100%" in kopru.group(1) and "block-size:var(--sp-03)" in kopru.group(1)
    # Düğmenin kendi sahte öğesi ipucu taşımaz (isabeti düğmeye giderdi); :hover kuralı yok.
    for secici in IKON_DUGMELERI:
        assert not re.search(re.escape(secici) + r"[^{,]*::(?:after|before)", SABLON), secici
    assert not re.search(r"\.icon-btn:hover::after", SABLON)
    for parca in ("const IPUCU_ACIK_MS=100, IPUCU_KAPA_MS=100;", 'ev.key!=="Escape"', 'addEventListener("click"',
                  'setAttribute("role","tooltip")', '"aria-describedby"', 'document.body.appendChild(ipucu)',
                  'getAttribute("aria-label")'):
        assert parca in SABLON, parca
    # Karar: ipucu metni adla aynıysa aria-describedby kurulmaz (ad iki kez okunmaz); farklıysa (data-ipucu) kurulur.
    assert 'getAttribute("data-ipucu")' in SABLON
    assert re.search(r'if\(metin!==ad\) b\.setAttribute\("aria-describedby","aracIpucu"\)', SABLON)


def test_ses_oynaticisi_carbon_bilesenlerinden_kurulur():
    """Kanun M5.14 (KB-49): yazarın sesi şablonun kendi oynatıcısıyla çalar; Carbon'da oynatıcı yok, bileşenlerinden
    kurulur: ghost ikon düğmesi (oynat/duraklat, sessiz; KB-44 boyu ve ipucu), Slider anatomisi (iz 2 px
    `--cds-border-subtle`, dolgu ve tutamaç `--cds-layer-selected-inverse`, tutamaç 14 px, odakta `--cds-interactive`
    ve 20 px; vuruş alanı 3rem), mono tabular süre, yükleniyor ve InlineNotification dilinde hata. <audio> gizli."""
    govde = _kural(".ses-dugme")
    assert "inline-size:var(--tap)" in govde and "block-size:var(--tap)" in govde, govde
    ikon = _kural(".ses-dugme .cds-icon")
    assert "inline-size:1.25rem" in ikon and "block-size:1.25rem" in ikon, ikon
    assert "block-size:var(--tap)" in _kural(".ses-kaydirici")
    iz = _kural(".ses-kaydirici__iz")
    assert "var(--cds-border-subtle)" in iz and "block-size:.125rem" in iz
    tutamac = _kural(".ses-kaydirici__tutamac")
    assert "var(--cds-layer-selected-inverse)" in tutamac and "inline-size:.875rem" in tutamac
    assert re.search(r"\.ses-kaydirici:focus-visible \.ses-kaydirici__tutamac\{[^}]*var\(--cds-interactive\)", SABLON)
    sure = _kural(".ses-sure")
    assert "var(--font-mono)" in sure and "tabular-nums" in sure
    hata = _kural(".ses-hata")
    assert "var(--cds-notification-background-error)" in hata and "3px solid var(--cds-support-error)" in hata
    assert re.search(r"@media \(forced-colors:active\)\{[^@]*\.ses-kaydirici__tutamac", SABLON)
    # Slider'ın dolgu ve tutamaç rengi tema bloklarında (@carbon/themes 11.83.0 layerSelectedInverse).
    for blok, deger in ((':root,[data-theme="g10"]{', "#161616"), ('[data-theme="white"]{', "#161616"),
                        ('[data-theme="g100"]{', "#f4f4f4")):
        bas = SABLON.index(blok)
        assert f"--cds-layer-selected-inverse:{deger};" in SABLON[bas:SABLON.index("\n}", bas)], (blok, deger)
    # Davranış: ±5 sn, ±%10, Home/End; ipucu sistemi oynatıcı düğmelerini de kapsar; ses yalnız tıklamayla başlar.
    for parca in ("const SES_ADIM_SN=5, SES_SAYFA_ORAN=.1;", "PageUp:t+top*SES_SAYFA_ORAN", "Home:0", "End:top",
                  'const IPUCU=".icon-btn,.pacing-disk__dismiss,.cmap-edge__remove,.ses-dugme";'):
        assert parca in SABLON, parca
    oynatici = SABLON[SABLON.index("(function sesOynatici(){"):]
    oynatici = oynatici[:oynatici.index("\n  })();")]
    assert oynatici.count(".play()") == 1 and "autoplay" not in oynatici


def test_hotspot_bolgesinin_adi_cevabi_sizdirmaz():
    """Bölgenin erişilebilir adı sorunun cevabı (`spots[].label`) değildir; "Bölge n / N" der. Cevap ancak doğru bölge
    bulununca o bölgenin adına girer (WCAG 1.1.1: test için betimleyici tanım, cevap değil; inceleme, Küçük 12)."""
    assert 'r.setAttribute("aria-label", meta.label' not in SABLON
    assert re.search(r'setAttribute\("aria-label", ?`Bölge \$\{', SABLON)
    # İkinci inceleme: numara uzamsal sıradır (kutu merkezi; soldan sağa, sonra yukarıdan aşağı), DOM sırası değil;
    # bulunan bölge sonraki soruda da işaretli ve devre dışı kalır.
    assert "getBoundingClientRect" in SABLON[SABLON.index("function renderHotspot"):SABLON.index("function renderTimeline")]
    assert 'setAttribute("aria-disabled","true")' in SABLON


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
    sesler = re.findall(r"<audio\b[^>]*\bsrc=[^>]*>", html)  # işaretleme (yorumlardaki <audio> sözü değil)
    assert sesler, "ses oynatıcısı yok"
    for oge in sesler:
        assert re.search(r'class="[^"]+"', oge), f"sınıfsız audio (M5.14): {oge}"
        assert "controls" not in oge and "autoplay" not in oge, oge   # tarayıcının oynatıcısı çizilmez (KB-49)
    assert '<audio class="edupedia-audio__kaynak" preload="metadata"' in html
    # Oynatıcının işaretlemesi (sablon.py): adlı grup, iki ikon düğmesi, slider, gizli yükleniyor ve hata.
    for parca in ('class="edupedia-audio" role="group" aria-labelledby="',
                  'class="ses-dugme ses-oynat" type="button" aria-label="Oynat"',
                  'class="ses-dugme ses-sessiz" type="button" aria-label="Seslendirmenin sesini kapat"',
                  'class="ses-kaydirici" role="slider" tabindex="0" aria-label="Konum" aria-valuemin="0"',
                  'class="ses-yukleniyor" role="status" hidden', 'class="ses-hata" role="alert" hidden'):
        assert parca in html, parca
