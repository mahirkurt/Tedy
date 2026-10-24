"""Modülün ikon düğmeleri ve ses oynatıcısı (Modül Tasarım Kanunu M5.14; KB-44, 2026-10-24).

Akışta kalan araçlar (ses, sesli okuma) ve çerçevedeki öteki ikon düğmeleri (tempo diskini gizleme, kavram
haritasında bağlantıyı kaldırma) Carbon ghost ikon düğmesidir: lg 48 px (`--tap`, 3rem: 4K'da kökle büyür), ikon
20 px (1.25rem), adı araç ipucunda — fareyle ve klavye odağında açılır, Esc ile kapanır (talimatname §4.3). Sesli
okuma ("Oku") düğmesi de 48 px'tir. Yazarın ses varlığı sınıflı bir `audio` öğesiyle, adlı Carbon katmanında çizilir.
Bunlar statik sözleşmedir; ölçüm (`getBoundingClientRect`, `::after` içeriği, Esc) `dashboard/tests/e2e/
modul-ikon-dugmeleri.spec.ts`'tedir.
"""
import re
from pathlib import Path

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
    for parca in ("const SES_ADIM_SN=5, SES_SAYFA_ORAN=.1, SES_ARIA_ARALIK_MS=10000;", "PageUp:t+top*SES_SAYFA_ORAN",
                  "Home:0", "End:top",
                  'const IPUCU=".icon-btn,.pacing-disk__dismiss,.cmap-edge__remove,.ses-dugme";'):
        assert parca in SABLON, parca
    oynatici = SABLON[SABLON.index("(function sesOynatici(){"):]
    oynatici = oynatici[:oynatici.index("\n  })();")]
    assert oynatici.count(".play()") == 1 and "autoplay" not in oynatici


def test_ses_kaydiricisinin_sozlu_degeri_oynarken_seyrek_yazilir():
    """İnceleme turu 1, bulgu 3: aria-valuenow/-valuetext her timeupdate'te yazılıyordu (3,2 sn'de 15). Artık yalnız
    okurun kaydırıcı eyleminde (klavye, sürükleme: `git`), duraklat/bitti/arama ve üst veride, oynarken en çok 10
    saniyede bir. Görsel ilerleme (dolgu, tutamaç, süre metni) her timeupdate'te güncellenir."""
    oynatici = SABLON[SABLON.index("(function sesOynatici(){"):]
    oynatici = oynatici[:oynatici.index("\n  })();")]
    assert '["loadedmetadata","durationchange","seeked","emptied","pause","ended"].forEach(function(tur){ medya(tur, guncelle); });' in oynatici
    assert 'medya("timeupdate", oynarken);' in oynatici and oynatici.count('"timeupdate"') == 1
    oynarken = oynatici[oynatici.index("function oynarken(p){"):]
    oynarken = oynarken[:oynarken.index("\n    }\n")]
    assert "gorsel(p);" in oynarken
    assert "if(!p.a.paused && performance.now()-(sonAria.get(p.k)||0) >= SES_ARIA_ARALIK_MS) sozlu(p);" in oynarken
    gorsel = oynatici[oynatici.index("function gorsel(p){"):]
    gorsel = gorsel[:gorsel.index("\n    }\n")]
    assert "aria-value" not in gorsel and "--ses-oran" in gorsel and "p.gecen.textContent" in gorsel
    sozlu = oynatici[oynatici.index("function sozlu(p){"):]
    sozlu = sozlu[:sozlu.index("\n    }\n")]
    assert all(f'"aria-value{a}"' in sozlu for a in ("max", "now", "text")) and "sonAria.set(p.k, performance.now());" in sozlu
    assert "p.a.currentTime=Math.max(0, Math.min(top, sn)); guncelle(p);" in oynatici   # okurun eylemi hemen yazar
    assert oynatici.count("aria-valuenow") == 1   # sözlü değeri yalnız sozlu() yazar


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
    # Oynatıcının işaretlemesi (sablon.py): adlı grup, iki ikon düğmesi, slider, iki canlı bölge.
    for parca in ('class="edupedia-audio" role="group" aria-labelledby="',
                  'class="ses-dugme ses-oynat" type="button" aria-label="Oynat"',
                  'class="ses-dugme ses-sessiz" type="button" aria-label="Seslendirmenin sesini kapat"',
                  'class="ses-kaydirici" role="slider" tabindex="0" aria-label="Konum" aria-valuemin="0"',
                  '<div class="ses-duyuru" role="status"></div>', '<div class="ses-uyari" role="alert"></div>'):
        assert parca in html, parca


def test_ses_oynaticisinin_canli_bolgeleri_hep_var_gorunur_ve_bos_baslar():
    """İnceleme turu 1, bulgu 2: `hidden`'ı açıp kapamak ekran okuyucuya güvenilir duyuru vermez. Canlı bölgeler
    (`role="status"` yükleniyor, `role="alert"` hata) DOM'da hep vardır, gizlenmez ve boş başlar; durum gelince
    metin (ve görsel kutusu) yazılır, durum bitince boşaltılır. Aynı durum yeniden gelirse yeniden yazılmaz."""
    kaynak = Path(sablon.__file__).read_text(encoding="utf-8")
    ses = kaynak[kaynak.index("function edupediaAudio(a){"):]
    ses = ses[:ses.index("\n  }\n")]
    assert '<div class="ses-duyuru" role="status"></div>' in ses and '<div class="ses-uyari" role="alert"></div>' in ses
    assert " hidden" not in ses and "ses-yukleniyor" not in ses and "ses-hata" not in ses
    oynatici = SABLON[SABLON.index("(function sesOynatici(){"):]
    oynatici = oynatici[:oynatici.index("\n  })();")]
    durum = oynatici[oynatici.index("function durum(p, d){"):]
    durum = durum[:durum.index("\n    }\n")]
    assert 'if(p.k.getAttribute("data-ses-durum")===d) return;' in durum
    assert 'p.duyuru.innerHTML = d==="yukleniyor" ? SES_YUKLENIYOR : "";' in durum
    assert 'p.uyari.innerHTML = d==="hata" ? SES_HATA : "";' in durum
    assert ".hidden" not in durum
    assert '<span>Yükleniyor</span>' in oynatici and '<span>Ses dosyası açılamadı</span>' in oynatici
    # Bölgeler gizlenmez; boşken yer kaplamaz (kendi aralıklarını içerikleri taşır, kapsayıcının gap'i yok).
    assert "[hidden]" not in SABLON[SABLON.index(".ses-yukleniyor{"):SABLON.index("@media (forced-colors:active){\n  .ses-kaydirici__iz")]
    assert not re.search(r"\.ses-(duyuru|uyari)\{[^}]*(display:none|visibility:hidden)", SABLON)
    assert "gap:" not in _kural(".edupedia-audio")
    for secici in (".ses-denetim", ".ses-yukleniyor", ".ses-hata"):
        assert "margin-block-start:var(--sp-03)" in _kural(secici), secici
