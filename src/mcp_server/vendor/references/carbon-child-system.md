# Carbon v11 Çocuk-Dostu Tasarım Sistemi — Token Referansı (v2)

> `carbon-edupedia` çıktısının görsel dilini tanımlar. Tüm token değerleri
> **`@carbon/*` npm paketlerinden programatik olarak çıkarılmış** ve şablonla
> birebir hizalanmıştır. Çocuk-dostu uyarlamalar gerekçeleriyle işaretlenmiştir
> (§7). Token'lar `assets/module-template.html` içindeki `:root` /
> `[data-theme]` bloklarında uygulanır; **şablonu kullanın, yeniden
> tanımlamayın** — yalnız aksan/temayı derse göre ayarlayın.

**Provenans (otorite çıkarımı):**
`@carbon/themes@11.75.0` · `@carbon/type@11.61.0` · `@carbon/motion@11.46.0` ·
`@carbon/layout@11.53.0` · `@carbon/colors@11.52.0` — çıkarım tarihi
**2026-06-12**; makine-okunur anlık görüntü: `assets/carbon-v11-authority.json`.

## İçindekiler
1. Otorite zinciri ve token altyapısı
2. Renk token'ları — White teması (çekirdek + etkileşim durumları + status)
3. Ders kategorisi aksan paleti (motor tablosu + resmî tag çiftleri)
4. Tipografi (IBM Plex + tip otoritesi + çocuk ölçeği)
5. Spacing ölçeği (tam 01–13) ve boyutlar
6. Hareket (motion) — tam süre × easing matrisi
7. Çocuk-dostu uyarlamalar (gerekçeli bilinçli sapmalar)
8. Kontrast ve erişilebilirlik kuralları
9. Carbon bileşen → edupedia eşlemesi
10. Gray-100 (dark) teması token'ları
11. Kontrast düzeltmesi — birincil eylem rengi
12. Yüzey ritmi ve çağrı kutuları

---

## 1. Otorite zinciri ve token altyapısı

Üç katmanlı doğruluk hiyerarşisi (uyuşmazlıkta üst katman kazanır):

| Katman | Kaynak | Rol |
|---|---|---|
| **PRIMARY** | `npm @carbon/*` paketleri (themes, type, motion, layout, colors) | Tek doğruluk kaynağı — token değerleri buradan çıkarılır |
| **SNAPSHOT** | `assets/carbon-v11-authority.json` | Sürüm-damgalı, makine-okunur anlık görüntü; `G-TOKEN` kapısı ve sync aracı bunu okur |
| **GÖRSEL QA** | Figma "Carbon Design System v11" kütüphaneleri | Bileşen anatomisi/görsel doğrulama yüzeyi (bkz. `figma-carbon-interop.md`) |

### 1.1 Token altyapısı araçları

- **`scripts/sync_carbon_tokens.py`** — `--check` (varsayılan, çevrimdışı):
  şablon tema bloklarını otorite JSON'a karşı diff'ler (~44 token × 2 tema);
  `--refresh`: npm'den taze çıkarım yapıp JSON'u günceller. Carbon yeni minor
  sürüm yayınladığında `--refresh` + `--check` çalıştırın.
- **`scripts/validate_module.py` → `G-TOKEN` kapısı** — üretilen her modülün
  tema bloklarını gömülü otorite haritasına karşı denetler. Sapma = WARN;
  White temada `--cds-support-info:#4589ff` = **FAIL** (bilinen AA kontrast
  regresyonu, bkz. §2 durum tablosu).

### 1.2 Kanonik tema blokları (şablona gömülü — buradan kopyalanır)

Aşağıdaki bloklar `assets/module-template.html` `<style>` içindeki tema
bildirimlerinin kanonik kaynağıdır; `@carbon/themes@11.75.0` ile birebirdir:

```css
/* ===== IBM Carbon v11 — WHITE teması (varsayılan) ===== */
:root,[data-theme="white"]{
  /* yüzeyler */
  --cds-background:#ffffff; --cds-layer-01:#f4f4f4; --cds-layer-02:#ffffff; --cds-layer-03:#f4f4f4;
  --cds-layer-hover-01:#e8e8e8; --cds-layer-active-01:#c6c6c6; --cds-layer-selected-01:#e0e0e0;
  --cds-layer-accent-01:#e0e0e0; --cds-layer-accent-hover-01:#d1d1d1;
  --cds-field-01:#f4f4f4; --cds-field-hover-01:#e8e8e8;
  --cds-background-hover:rgba(141,141,141,.12); --cds-background-active:rgba(141,141,141,.5);
  /* kenarlar — iki kademeli border-subtle: 00 zemin üstü, 01 layer-01 üstü */
  --cds-border-subtle-00:#e0e0e0; --cds-border-subtle-01:#c6c6c6;
  --cds-border-subtle:var(--cds-border-subtle-00);
  --cds-border-strong:#8d8d8d; --cds-border-tile:#c6c6c6; --cds-border-interactive:#0f62fe;
  /* metin + ikon */
  --cds-text-primary:#161616; --cds-text-secondary:#525252; --cds-text-helper:#6f6f6f;
  --cds-text-placeholder:rgba(22,22,22,.4); --cds-text-on-color:#ffffff;
  --cds-icon-primary:#161616; --cds-icon-secondary:#525252; --cds-icon-on-color:#ffffff;
  /* etkileşim / aksiyon */
  --cds-interactive:#0f62fe; --cds-link-primary:#0f62fe; --cds-link-primary-hover:#0043ce;
  --cds-button-primary:#0f62fe; --cds-button-primary-hover:#0050e6; --cds-button-primary-active:#002d9c;
  --cds-focus:#0f62fe; --cds-focus-inset:#ffffff;
  --cds-highlight:#d0e2ff; --cds-overlay:rgba(0,0,0,.6); --cds-shadow:rgba(0,0,0,.3);
  --cds-skeleton-background:#e8e8e8; --cds-skeleton-element:#c6c6c6;
  /* durum (status-token: info açık temada Blue 70) */
  --cds-support-success:#24a148; --cds-support-error:#da1e28;
  --cds-support-warning:#f1c21b; --cds-support-info:#0043ce;
  --cds-notif-success-bg:#defbe6; --cds-notif-info-bg:#edf5ff;
  --cds-notif-warning-bg:#fcf4d6; --cds-notif-error-bg:#fff1f1;
  --reward:#d2a106; --reward-bg:#fcf4d6;
}
```

(Gray-100 bloğu için §10; spacing/tip/hareket ortak `:root` bloğu için §5–6.)

## 2. Renk token'ları — White teması

**Çekirdek yüzey/metin:**
| Carbon token | CSS değişkeni | Değer | Kullanım |
|---|---|---|---|
| background | `--cds-background` | `#ffffff` | Sayfa zemini |
| layer-01 | `--cds-layer-01` | `#f4f4f4` (Gray 10) | Kart/panel zemini |
| layer-02 | `--cds-layer-02` | `#ffffff` | İç içe katman |
| layer-03 | `--cds-layer-03` | `#f4f4f4` | Üçüncü katman (layer-02 üstü) |
| layer-accent-01 | `--cds-layer-accent-01` | `#e0e0e0` (Gray 20) | Vurgulu yüzey |
| field-01 | `--cds-field-01` | `#f4f4f4` | Form alanı zemini |
| border-subtle-00 | `--cds-border-subtle-00` | `#e0e0e0` | İnce ayraç (**zemin** üstü) |
| border-subtle-01 | `--cds-border-subtle-01` | `#c6c6c6` | İnce ayraç (**layer-01** üstü) |
| border-strong-01 | `--cds-border-strong` | `#8d8d8d` (Gray 50) | Belirgin kenar |
| border-tile-01 | `--cds-border-tile` | `#c6c6c6` | Tile (seçilebilir kart) kenarı |
| text-primary | `--cds-text-primary` | `#161616` (Gray 100) | Birincil metin |
| text-secondary | `--cds-text-secondary` | `#525252` (Gray 70) | İkincil metin |
| text-helper | `--cds-text-helper` | `#6f6f6f` (Gray 60) | Yardımcı/açıklama metni |
| text-placeholder | `--cds-text-placeholder` | `rgba(22,22,22,.4)` | Placeholder (v11 alfa) |
| text-on-color | `--cds-text-on-color` | `#ffffff` | Renkli zemin üstü metin |
| icon-primary / -secondary / -on-color | `--cds-icon-*` | `#161616` / `#525252` / `#ffffff` | İkonlar |

> **Sapma notu (v2.0.0'da düzeltildi):** v1.x dokümanı `text-placeholder` için
> v10 değeri `#a8a8a8` ve tek kademeli `border-subtle` listeliyordu; v11
> otoritesi alfa-tabanlı placeholder ve **iki kademeli** border-subtle tanımlar
> (kenar, üzerinde durduğu katmana göre seçilir).

**Etkileşim/aksiyon:**
| Carbon token | CSS değişkeni | Değer | Kullanım |
|---|---|---|---|
| interactive | `--cds-interactive` | `#0f62fe` (Blue 60) | Birincil aksiyon, bağlantı |
| link-primary | `--cds-link-primary` | `#0f62fe` | Bağlantı |
| link-primary-hover | `--cds-link-primary-hover` | `#0043ce` (Blue 70) | Bağlantı hover |
| button-primary | `--cds-button-primary` | `#0f62fe` | Birincil buton |
| button-primary-hover | `--cds-button-primary-hover` | `#0050e6` | Buton hover (**tüm temalarda aynı**) |
| button-primary-active | `--cds-button-primary-active` | `#002d9c` (Blue 80) | Buton aktif |
| focus | `--cds-focus` | `#0f62fe` | Odak halkası (2px) |
| focus-inset | `--cds-focus-inset` | `#ffffff` | Odak iç çizgisi |
| highlight | `--cds-highlight` | `#d0e2ff` (Blue 20) | Metin seçimi / vurgu zemini |

**Etkileşim durumları (hover/active/selected) — v2.0.0'da eklendi:**
| Carbon token | CSS değişkeni | Değer | Kullanım |
|---|---|---|---|
| layer-hover-01 | `--cds-layer-hover-01` | `#e8e8e8` | layer-01 üstü hover |
| layer-active-01 | `--cds-layer-active-01` | `#c6c6c6` | layer-01 üstü basılı |
| layer-selected-01 | `--cds-layer-selected-01` | `#e0e0e0` | layer-01 üstü seçili |
| layer-accent-hover-01 | `--cds-layer-accent-hover-01` | `#d1d1d1` | accent katman hover |
| field-hover-01 | `--cds-field-hover-01` | `#e8e8e8` | Form alanı hover |
| background-hover | `--cds-background-hover` | `rgba(141,141,141,.12)` | Ghost buton / ikon-buton hover |
| background-active | `--cds-background-active` | `rgba(141,141,141,.5)` | Ghost buton basılı |
| border-interactive | `--cds-border-interactive` | `#0f62fe` | Seçili tile / aktif kenar |
| overlay | `--cds-overlay` | `rgba(0,0,0,.6)` | Modal arkası karartma |
| shadow | `--cds-shadow` | `rgba(0,0,0,.3)` | Gölge rengi |
| skeleton-background / -element | `--cds-skeleton-*` | `#e8e8e8` / `#c6c6c6` | Yüklenme iskeleti |

**Durum (status) — renk + ikon birlikte kullanılır (renk tek başına anlam değil):**
| Carbon token | CSS değişkeni | Değer | Anlam | İkon |
|---|---|---|---|---|
| support-success | `--cds-support-success` | `#24a148` (Green 50) | Doğru/başarı | checkmark--filled |
| support-error | `--cds-support-error` | `#da1e28` (Red 60) | Yanlış/hata | close--filled / warning |
| support-warning | `--cds-support-warning` | `#f1c21b` (Yellow 30) | Uyarı/dikkat | warning--alt--filled |
| support-info | `--cds-support-info` | **`#0043ce`** (Blue 70) | Bilgi/ipucu | information--filled |

> ⚠ **KRİTİK düzeltme (v2.0.0):** White temada `support-info` **`#0043ce`**'dir
> (`@carbon/themes` status-token: açık temalarda info = Blue 70). v1.x'in
> kullandığı `#4589ff` (Blue 50) beyaz zeminde ~3.7:1 kontrast verir — küçük
> ikon/metin için **AA başarısız**. `#4589ff` yalnız **g100** temasında
> doğrudur. Bu sapma `G-TOKEN` kapısında **FAIL** seviyesindedir.
>
> **Genel kural:** Yanlış cevap **kırmızı + ikon + "tekrar dene" metni** ile
> gösterilir, asla yalnız kırmızıyla. Doğru cevap **yeşil + onay ikonu + olumlu
> metin**. Bu hem WCAG (renk tek başına anlam yasağı) hem DEHB (çoklu kanal)
> gereğidir.

**Bildirim (inline notification) zeminleri — White:**
`success #defbe6 · info #edf5ff · warning #fcf4d6 · error #fff1f1`
(Carbon notification-token; her biri 3px durum çubuğu + durum ikonu ile.)

## 3. Ders kategorisi aksan paleti

Her ders bir aksan token'ı alır; modül başlığı, ilerleme rayı, segment
ikon karoları bu aksanı kullanır. Aksan **anlam taşır** (kategori kodlama),
dekor değil. Seçim önceliği: `MODULE_DATA.meta.accent` (hex) →
`meta.subject`/`meta.subjectKey` üzerinden motor `SUBJECT_ACCENT` tablosu →
varsayılan Blue 60.

**Motor tablosu (`SUBJECT_ACCENT`) — şablonla birebir:**

| Ders anahtarı | Aksan | Hex | Resmî tag çifti (açık tema: zemin / metin) | Tag çifti (g100: zemin / metin) |
|---|---|---|---|---|
| `math` | Purple 60 | `#8a3ffc` | `#e8daff` / `#6929c4` | `#6929c4` / `#e8daff` |
| `science` | Teal 60 | `#007d79` | `#9ef0f0` / `#005d5d` | `#005d5d` / `#9ef0f0` |
| `social` | Magenta 50 | `#ee5396` | `#ffd6e8` / `#9f1853` | `#9f1853` / `#ffd6e8` |
| `civics` | Cyan 60 | `#0072c3` | `#bae6ff` / `#00539a` | `#00539a` / `#bae6ff` |
| `religion` | Green 60 | `#198038` | `#a7f0ba` / `#0e6027` | `#0e6027` / `#a7f0ba` |
| `history` | Purple 50 | `#a56eff` | `#e8daff` / `#6929c4` | `#6929c4` / `#e8daff` |
| `geography` | Teal 70 | `#005d5d` | `#9ef0f0` / `#005d5d` | `#005d5d` / `#9ef0f0` |
| `turkish` | Red 60 | `#da1e28` | `#ffd7d9` / `#a2191f` | `#a2191f` / `#ffd7d9` |
| `english` / `language` | Blue 60 | `#0f62fe` | `#d0e2ff` / `#0043ce` | `#0043ce` / `#d0e2ff` |
| `french` | Purple 70 | `#6929c4` | `#e8daff` / `#6929c4` | `#6929c4` / `#e8daff` |
| *(varsayılan)* | Blue 60 | `#0f62fe` | `#d0e2ff` / `#0043ce` | `#0043ce` / `#d0e2ff` |

**Tag-çifti motoru (`ACCENT_STRONG`, v2.0.0):** `setAccent(hex)` artık bilinen
aksan ailelerinde **resmî Carbon tag token çiftini** kullanır
(`@carbon/themes` tag-tokens: `tag-background-X` / `tag-color-X`): açık temada
`--accent-strong` = koyu tag-color, koyu temada açık tag-color; `--accent-tint`
zemini `color-mix` ile temaya göre türetilir. Bilinmeyen hex'lerde önceki
`color-mix` karartma/açma yedeği devrededir. Böylece `.def-term`, `.badge`,
`.seg-ic` üzerindeki aksan-renkli metin her iki temada da **AA-garantili resmî
çiftlerle** yazılır.

> **Doc-motor uzlaşması (v2.0.0):** v1.x dokümanındaki §3 tablosu motor
> tablosuyla çelişiyordu (ör. matematik için Blue 60, kimya için Purple 60
> listeliyordu; motor matematiğe Purple 60, fene Teal 60 atar). Bu sürümde
> tablo **motor `SUBJECT_ACCENT` kaynak alınarak** yeniden yazıldı; tüm hex'ler
> `@carbon/colors@11.52.0` paletiyle doğrulandı.

## 4. Tipografi — IBM Plex + tip otoritesi

**Font aileleri (tamamen çevrimdışı; yedek zincirleri `@carbon/type`
`fontFamilies` ile hizalı):** Şablon resmî `@ibm/plex@6.4.1` npm
dağıtımındaki Latin1 + Latin2 WOFF2 altkümelerini `data:font/woff2;base64`
olarak gömer. Google Fonts, CDN, ağ isteği ve göreli font dosyası yoktur.

Gömülü yüzler, şablonun gerçekten kullandığı ağırlıklarla sınırlıdır:
- Sans normal: 400 / 500 / 600 / 700
- Serif normal: 400 / 600; italic: 400
- Mono normal: 400 / 600 / 700

Üretim zinciri: `scripts/embed_ibm_plex_fonts.py` → inline `@font-face`
blokları + `assets/fonts-manifest.json` (her WOFF2 için sabit SHA-256) +
`assets/ibm-plex-OFL.txt` (SIL OFL 1.1 tam metni). `--check` ağsız olarak
şablon/blob/manifest/lisans paritesini doğrular; yeniden üretim yalnız
önceden indirilmiş resmî `.tgz` ile `--archive` veya açık `--fetch` seçeneğiyle
yapılır. `@font-face src` zincirinde `local()` kullanılmaz; böylece tarayıcı
kanıtı sistemde tesadüfen kurulu bir Plex yüzüne değil gömülü bloba dayanır.

- `--font-sans: 'IBM Plex Sans',system-ui,-apple-system,BlinkMacSystemFont,sans-serif;` — UI, gövde, başlık
- `--font-serif: 'IBM Plex Serif',Georgia,serif;` — vurgulu anlatım/alıntı
- `--font-mono: 'IBM Plex Mono','Menlo','Consolas',monospace;` — sayı, formül, XP

**Carbon tip otoritesi (`@carbon/type@11.61.0`) ↔ edupedia ölçeği:**
| Carbon stili | Otorite değeri | Edupedia rolü | Edupedia değeri | Sapma? |
|---|---|---|---|---|
| heading-05 | 2rem / 400 / lh 1.25 | — | — | — |
| heading-04 | 1.75rem / 400 / lh 1.28 | `--fs-h-seg` segment başlığı | 1.75rem / **600** | ağırlık ↑ (çocuk hiyerarşi netliği) |
| heading-03 | 1.25rem / 400 / lh 1.4 | `--fs-h-sub` alt başlık | 1.25rem / **600** | ağırlık ↑ |
| body-02 | 1rem / 400 / lh 1.5 | `--fs-compact` yardımcı | 1rem / 400 | — |
| body-02 | 1rem | `--fs-body` gövde | **1.125rem (18px)** / lh 1.6 | boyut ↑ (bkz. §7) |
| label-01 | .75rem / ls .32px | `--fs-label` etiket | **.875rem** / `--ls-label:.32px` | boyut ↑, letter-spacing otoriteyle aynı |
| code-02 | .875rem / ls .32px | mono sayı/XP | 1rem mono / ls .32px | boyut ↑ |
| display | — | `--fs-display` modül başlığı | 2.5rem / 600 / lh 1.2 | edupedia eklentisi |

> Çocuk için gövde **18px** (Carbon body-02 16px yerine); okunabilirlik ve
> disleksi örtüşmesi (referans: adhd-pedagogy §5). Asla 16px altına düşürmeyin.
> Letter-spacing değerleri (`.32px` label/code) otoriteyle birebirdir.

## 5. Spacing ölçeği (tam 01–13) ve boyutlar

`@carbon/layout@11.53.0` — 2px mini-unit tabanlı; şablonda tamamı tanımlı
(`--cds-spacing-01..13` + kısa `--sp-01..10` alias'ları):

| Token | Değer | | Token | Değer |
|---|---|---|---|---|
| spacing-01 | 0.125rem (2px) | | spacing-08 | 2.5rem (40px) |
| spacing-02 | 0.25rem (4px) | | spacing-09 | 3rem (48px) |
| spacing-03 | 0.5rem (8px) | | spacing-10 | 4rem (64px) |
| spacing-04 | 0.75rem (12px) | | spacing-11 | 5rem (80px) |
| spacing-05 | 1rem (16px) | | spacing-12 | 6rem (96px) |
| spacing-06 | 1.5rem (24px) | | spacing-13 | 10rem (160px) |
| spacing-07 | 2rem (32px) | | | |

**Carbon `sizes` ölçeği (etkileşim hedefleri):** XSmall 1.5rem · Small 2rem ·
Medium 2.5rem · **Large 3rem (48px)** · XLarge 4rem · 2XLarge 5rem.
Edupedia'nın `--tap:48px` dokunma hedefi **Carbon "Large" boyutuyla** örtüşür
(yetişkin Carbon varsayılanı Medium/40px'tir; bkz. §7).

Bolca beyaz alan (negative space) DEHB'de dış yükü azaltır; ekranlar ferah olmalı.

## 6. Hareket (motion) — tam süre × easing matrisi

`@carbon/motion@11.46.0` — **6 süre + 2 sınıf × 3 mod = 6 easing**; tamamı
şablonda token olarak tanımlıdır:

**Süreler:**
| Token | Değer | Tipik kullanım |
|---|---|---|
| `--cds-duration-fast-01` | 70ms | Mikro durum (hover rengi) |
| `--cds-duration-fast-02` | 110ms | Buton/tile durum geçişi |
| `--cds-duration-moderate-01` | 150ms | Küçük açılır öğe |
| `--cds-duration-moderate-02` | 240ms | Segment girişi, panel |
| `--cds-duration-slow-01` | 400ms | Ödül vurgusu (XP nabzı) |
| `--cds-duration-slow-02` | 700ms | Büyük sahne geçişi (nadiren) |

**Easing'ler (productive = fonksiyonel/kısa · expressive = ifadeli/ödül):**
| Token | Bezier |
|---|---|
| `--cds-easing-standard-productive` | `cubic-bezier(.2, 0, .38, .9)` |
| `--cds-easing-standard-expressive` | `cubic-bezier(.4, .14, .3, 1)` |
| `--cds-easing-entrance-productive` | `cubic-bezier(0, 0, .38, .9)` |
| `--cds-easing-entrance-expressive` | `cubic-bezier(0, 0, .3, 1)` |
| `--cds-easing-exit-productive` | `cubic-bezier(.2, 0, 1, .9)` |
| `--cds-easing-exit-expressive` | `cubic-bezier(.4, .14, 1, 1)` |

**Şablon bağlamaları (alias'lar):** `--ease-std`→standard-productive ·
`--ease-expr`→standard-expressive · `--ease-entrance`→entrance-expressive ·
`--ease-exit`→exit-expressive · `--dur-fast`→fast-02 ·
`--dur-mod`→moderate-02 · `--dur-slow`→slow-01.

**Animasyon eşlemesi:** segment girişi (`segIn`) moderate-02 + entrance;
XP yükselişi/şerit kayboluşu exit; XP nabzı slow-01 + expressive; rozet
patlaması entrance; şerit vuruşu expressive. **Yanıp sönme, sürekli döngü,
parıltı yok** (foto-duyarlılık + dikkat).

**Zorunlu:** Tüm hareket `prefers-reduced-motion: reduce` altında devre dışı:
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}
```

## 7. Çocuk-dostu uyarlamalar (gerekçeli)

Carbon kurumsal/yetişkin bağlama optimize edilmiştir. Aşağıdaki **bilinçli
sapmalar** çocuk + DEHB için yapılır ve `adhd-pedagogy.md`'ye dayanır:

| Uyarlama | Carbon varsayılan | Edupedia değeri | Gerekçe |
|---|---|---|---|
| Köşe yarıçapı | ~0–2px (dikdörtgensel) | `--cds-radius: 8px` (kart), 6px (buton) | Yumuşak köşeler çocukta "dostça"; Carbon'un expressive ucu yarıçapı tolere eder |
| Gövde boyutu | body-02 = 16px | 18px | Okunabilirlik + disleksi (ped §5) |
| Başlık ağırlığı | heading 400 | 600 | Hiyerarşi belirginliği (yürütücü işlev desteği) |
| Dokunma hedefi | size Medium 40px | ≥48px (= Carbon size **Large**) | Motor + dürtüsellik (WCAG 2.5.5; ped §5) |
| Aksan yoğunluğu | Ölçülü | Kategori-renk belirgin | Uyarılma (ped İlke 5) |
| Hareket | Productive ağırlıklı | Expressive ödül anları | Ödül belirginliği (ped İlke 3) |
| Piktogram | Seçici | Bol (her segment) | İkili kodlama (ped İlke 7) |

> Bu sapmalar Carbon'un **token disiplinini bozmaz** — yalnız değerleri çocuk
> bağlamına ayarlar; sapmayan her şey (renk, durum, spacing, hareket, harf
> aralığı) otoriteyle **birebirdir** ve `G-TOKEN` kapısıyla denetlenir. Token
> isimleri, ölçek mantığı, renk paleti Carbon kalır. Bu, `skill-censor` D11
> "design-system-claim" denetiminden geçmek için önemlidir: "Carbon
> kullanıyoruz" iddiası token sistemine sadakatle + otorite zinciriyle
> desteklenir.

## 8. Kontrast ve erişilebilirlik kuralları (özet)

- Metin/zemin ≥ **4.5:1** (normal), ≥ **3:1** (≥24px/19px-bold büyük metin).
  `#161616`/`#ffffff` ≈ 16:1 (mükemmel); ikincil `#525252`/`#ffffff` ≈ 7.4:1;
  helper `#6f6f6f`/`#ffffff` ≈ 4.95:1 (geçer, daha küçükte kullanmayın).
- **support-info:** açık temada **`#0043ce`** kullanın (≈ 6.6:1 ✓); `#4589ff`
  açık zeminde ~3.7:1 → AA başarısız, yalnız g100'de geçerli (G-TOKEN FAIL).
- Aksan renkleri **metin olarak** kullanılırken `--accent-strong` (resmî tag
  çifti) zorunlu: Teal 60 `#007d79` beyaz zeminde ~4.7:1 sınırda; ham aksanı
  yalnız büyük başlık/dolgu/kenarda kullanın, küçük gövde metnini daima
  `--cds-text-primary` yapın.
- Durum daima **çift-kanal** (renk + ikon + metin).
- Odak halkası: `outline: 2px solid var(--cds-focus); outline-offset: 2px;` —
  asla `outline: none` (klavye kullanıcısı). Koyu temada odak **beyaz**.
- Renkli butonda metin `--cds-text-on-color` (#ffffff) ve buton zemini yeterince
  koyu (Blue 60 #0f62fe beyaz metinle ~4.6:1 — geçer).
- Metin seçimi `::selection{background:var(--cds-highlight)}` — tema-duyarlı.

## 9. Carbon bileşen → edupedia kullanımı

Şablon, Carbon v11 bileşen **desenlerini** (React kütüphanesi değil, saf
HTML/CSS karşılıkları) sadık biçimde uygular. Eşleme:

| Carbon bileşeni | edupedia karşılığı | Token bağı |
|---|---|---|
| **ProgressIndicator** (stepper) | `.stepper` — tamamlanan (yeşil + onay), mevcut (aksan halka), bekleyen (nötr); tamamlanana tıklanıp geri dönülür | `support-success`, `--accent`, `border-strong` |
| **Selectable Tile** | `.opt` — 1px `border-tile` → hover/seçili 2px `border-interactive`; köşe işaret yuvası; doğru/yanlış durumları | `border-tile`, `border-interactive`, `layer-hover-01` |
| **Inline notification** | `.feedback--ok/no/info` — 3px sol durum çubuğu + durum ikonu; koyu temada 1px `border-subtle-01` çerçeve | `support-*`, `notif-*-bg` |
| **Tag** | `.def-term`, `.badge` — pill, resmî tag çifti zemin/metin | `ACCENT_STRONG` tag-tokens |
| **Definition tooltip** | `.def-term:hover/focus::after` — koyu (#393939) popover | — |
| **Button (primary/ghost)** | `.btn--primary` (Blue 60), `.btn--ghost` (1px kenar); hover/active `background-hover/active` | `button-primary-*`, `background-*` |
| **Icon button (ghost)** | `.icon-btn`; hover `background-hover`, basılı `background-active` | `background-*` |
| **Data-viz donut** | `donutSvg()` — Carbon Charts paletiyle uyumlu SVG halka | `--viz-*` |
| **Skeleton** | (rezerve) yüklenme iskeleti | `skeleton-*` |

İkonlar **gerçek `@carbon/icons`**, piktogramlar **gerçek `@carbon/pictograms`**
varlıklarıdır (bkz. `icon-pictogram-svg.md` §2–3); satır-içi tek sprite olarak
gömülür, `currentColor` ile tema/aksan rengini alır.

## 10. Gray-100 (dark) teması token'ları

Tema **token-tabanlıdır**: `<html data-theme="white|g100">` özniteliği tema
bloğunu seçer; tüm bileşenler değişken okuduğu için yeniden render gerekmez.
Üst çubuktaki ikon-buton (`ic-moon`/`ic-light`) geçişi yapar. Kanonik blok
(`@carbon/themes@11.75.0` g100 ile birebir):

```css
[data-theme="g100"]{
  --cds-background:#161616; --cds-layer-01:#262626; --cds-layer-02:#393939; --cds-layer-03:#525252;
  --cds-layer-hover-01:#333333; --cds-layer-active-01:#525252; --cds-layer-selected-01:#393939;
  --cds-layer-accent-01:#393939; --cds-layer-accent-hover-01:#474747;
  --cds-field-01:#262626; --cds-field-hover-01:#333333;
  --cds-background-hover:rgba(141,141,141,.16); --cds-background-active:rgba(141,141,141,.4);
  --cds-border-subtle-00:#393939; --cds-border-subtle-01:#525252;
  --cds-border-subtle:var(--cds-border-subtle-00);
  --cds-border-strong:#6f6f6f; --cds-border-tile:#525252; --cds-border-interactive:#4589ff;
  --cds-text-primary:#f4f4f4; --cds-text-secondary:#c6c6c6; --cds-text-helper:#a8a8a8;
  --cds-text-placeholder:rgba(244,244,244,.4); --cds-text-on-color:#ffffff;
  --cds-icon-primary:#f4f4f4; --cds-icon-secondary:#c6c6c6; --cds-icon-on-color:#ffffff;
  --cds-interactive:#4589ff; --cds-link-primary:#78a9ff; --cds-link-primary-hover:#a6c8ff;
  --cds-button-primary:#0f62fe; --cds-button-primary-hover:#0050e6; --cds-button-primary-active:#002d9c;
  --cds-focus:#ffffff; --cds-focus-inset:#161616;
  --cds-highlight:#001d6c; --cds-overlay:rgba(0,0,0,.6); --cds-shadow:rgba(0,0,0,.8);
  --cds-skeleton-background:#292929; --cds-skeleton-element:#393939;
  --cds-support-success:#42be65; --cds-support-error:#fa4d56;
  --cds-support-warning:#f1c21b; --cds-support-info:#4589ff;
  /* Carbon koyu bildirim: zemin layer-01-eşdeğeri #262626; anlamı 3px durum çubuğu + ikon taşır */
  --cds-notif-success-bg:#262626; --cds-notif-info-bg:#262626;
  --cds-notif-warning-bg:#262626; --cds-notif-error-bg:#262626;
}
```

**v2.0.0 g100 düzeltmeleri:** `button-primary-hover` `#0353e9` → **`#0050e6`**
(otorite tüm temalarda `#0050e6` tanımlar); `layer-03` `#4c4c4c` → `#525252`;
bildirim zeminleri özel koyu tintler → dördü de **`#262626`** (Carbon koyu
bildirim deseni: nötr katman zemini, anlam durum çubuğu + ikonda).

`setAccent(hex)` **tema-duyarlıdır**: `--accent-tint` aksanı tema zemini ile
karıştırır (white'ta açık, g100'de koyu tint); `--accent-strong` resmî tag
çiftinden gelir — açık temada koyu, g100'de açık değer (bkz. §3).

## 11. Kontrast düzeltmesi — birincil eylem rengi

**v1.0'ın gizli kusuru:** birincil butonlar kategori aksanını dolu zemin
+ beyaz metinle kullanıyordu. Açık aksanlarda (teal, cyan) beyaz metin
kontrastı ~2.9:1 — **AA başarısız**.

**Carbon-doğru çözüm:** birincil eylemler **her zaman Blue 60**
(`--cds-button-primary`, beyaz metinle ~4.6:1 ✓) kullanır; kategori aksanı yalnız
**metin-taşımayan yapısal/dekoratif** öğelerde kullanılır: ilerleme dolgusu,
stepper, tile seçimi, tag zemini, üst çubuk üst-kenarı, piktogramlar. Aksan-renkli
**metin** her zaman `--accent-strong` (resmî tag çifti — kontrast-güvenli) ile
yazılır; tamamlandı/doğru göstergeleri `--cds-support-success` (yeşil) kullanır.
Bu, hem Carbon'un eylem-rengi tutarlılığını hem WCAG AA'yı sağlar.

## 12. Yüzey ritmi ve çağrı kutuları

**Sorun:** Tek katman + tek aksan, ekranları görsel olarak tekdüze yapıyordu.
**Carbon-doğru çözüm:** Renk *çoğaltmadan*, **katman (layer) ve tint** ile yüzey
ritmi kurmak. DEHB için bu, dikkat-dağıtıcı süs değil; segment türünü ele veren
**anlamlı mod ipucudur** (ped İlke 1 parçalama + 7 ikili kodlamayla uyumlu).

| Öğe | Yüzey | Token |
|---|---|---|
| Sahne (varsayılan) | nötr kart | `--cds-layer-01` |
| Segment ikon karosu (`.seg-ic`) | aksan-tint yuvarlatılmış kare, içinde piktogram | `--accent-tint` + `--accent-strong` |
| Çekme-alıntı (`.lead`) | aksan-tint **çağrı kutusu** + 4px sol bar, serif, **metin `--text-primary`** (her iki temada AA) | `--accent-tint` |
| Görsel (`.visual`) / Kavramlar (`.terms`) | yükseltilmiş çerçeveli yüzey | `--cds-layer-02` + `--border-subtle` |
| Çağrı kutusu (`.callout`, `--info`/`--success`) | tint + durum bar + ikon; teach gövdesinde kullanılır | `--accent-tint` / `color-mix(support)` |
| **brainbreak** sahnesi | tamamı aksan-tint (sakinleştirici "mola" sinyali) | `.stage[data-seg="brainbreak"]` |
| **checkpoint** sahnesi | üst 4px aksan kenarı (kilometre taşı) | `.stage[data-seg="checkpoint"]` |
| **summary** sahnesi | üstten aksan-tint → layer-01 yumuşak geçiş (kutlama) | `.stage[data-seg="summary"]` |

**Kontrast güvencesi:** Tüm tint zeminler `--accent-tint` (temaya göre çok açık/çok
koyu) olduğundan üzerine **`--text-primary`** yazılır → White ve Gray-100'de AA.
Aksan yalnız bar/ikon/karo gibi **dekoratif** yüzeylerde; metin asla düşük-kontrast
aksan renginde değil. `data-seg` özniteliği motor tarafından her segmentte sahneye
yazılır; renk paleti **tek kategori aksanı + nötr katmanlar** ile sınırlı kalır
(marka tutarlılığı + aşırı-uyarım önleme).
