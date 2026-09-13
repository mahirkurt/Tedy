# Kanonik Carbon Kaynak Haritası — `carbon-design-system/carbon` (ESAS KAYNAK)

> **Doktrin (normatif).** `carbon-edupedia`'nın TÜM Carbon fidelity'sinin **tek
> doğruluk kaynağı**, IBM'in resmî **`carbon-design-system/carbon`** monorepo'su ve
> ondan yayımlanan **`@carbon/*` npm paketleridir**. Figma kütüphaneleri (bkz.
> `figma-carbon-interop.md`) yalnız **üçüncül, opsiyonel görsel-anatomi QA**
> katmanıdır — token/renk/ikon/palet **değerinin kaynağı DEĞİLDİR** (Figma
> community kopyaları sürüm-geridir). Bu dosya her Carbon endişesi için kanonik
> paketi, GitHub yolunu ve doğrulanmış değerleri sabitler. Empirik doğrulama:
> `@carbon/*` 11.7x yerelinden (2026-07-07).

## 1. Endişe → kanonik `@carbon/*` paketi eşlemesi

Monorepo: `https://github.com/carbon-design-system/carbon` → `packages/<paket>`.
npm: `@carbon/<paket>`. Senkron: `scripts/sync_carbon_tokens.py --refresh`
(`_provenance.source: 'carbon-design-system/carbon via npm'`).

| Endişe | Kanonik paket | GitHub yolu | edupedia tüketim noktası |
|---|---|---|---|
| **Tema/token değerleri** | `@carbon/themes` | `packages/themes` | `assets/carbon-v11-authority.json` (sync) · G-TOKEN kapısı |
| **Renk primitifleri** | `@carbon/colors` | `packages/colors` | aksan + `--viz-*` (bkz. §2) · `color-system.md` |
| **Tipografi** | `@carbon/type` | `packages/type` | IBM Plex + tip ölçeği · `carbon-child-system.md` |
| **Hareket** | `@carbon/motion` | `packages/motion` | `--cds-easing-*` + süre · `carbon-child-system.md` |
| **Spacing/layout** | `@carbon/layout` | `packages/layout` | `--cds-spacing-*` · `carbon-excellence.md` §1 (2x grid) |
| **UI ikonları** | `@carbon/icons` | `packages/icons` | motor sprite → §3 eşleme · `icon-pictogram-svg.md` |
| **Piktogramlar** | `@carbon/pictograms` | `packages/pictograms` | motor `pic-*` sprite → §3 · `icon-pictogram-svg.md` |
| **Grafik paleti/anatomi** | `@carbon/charts` | `packages/charts` | `vizChart`/`vizTable` → §4 · `carbon-excellence.md` §3 (12-13) |

> Token **değeri** için asla Figma/tahmin kullanılmaz — yukarıdaki paket + sync
> zinciri kanonik ve çevrimdışıdır. Figma yalnız *anatomi/durum/ad* teyidi (§QA).

## 2. Doğrulanmış aksan + veri-görselleştirme renkleri (`@carbon/colors`)

Motor aksan token'ları kanonik `@carbon/colors` ile **birebir** (2026-07-07):

| Token | Değer | `@carbon/colors` |
|---|---|---|
| `--accent` | `#0f62fe` | **blue60** ✓ |
| `--accent-strong` | `#0043ce` | blue70 ✓ |
| `--accent-tint` | `#edf5ff` | blue10 ✓ |

Diğer ders-aksan kanonik değerleri (subject-packs eşlemesi için): teal60 `#007d79` ·
purple60 `#8a3ffc` · magenta60 `#d02670` · green60 `#198038` · cyan50 `#1192e8`.

## 3. İkon/piktogram: motor sprite → kanonik `@carbon/icons` adı

`@carbon/icons` **v11.74.0 · 2584 kanonik ikon**. Adlandırma: kebab-case; varyant
ayracı `--` (ör. `arrow--right`, `chevron--right`, `volume--up`). Motor sprite'ı
tek-dosya offline olduğu için **satır-içi** özel `ic-*`/`pic-*` id'ler kullanır;
her biri bir **kanonik Carbon ikonundan türetilmelidir** (SVG path kaynağı):

| Motor sprite id | Kanonik `@carbon/icons` adı | Not |
|---|---|---|
| `ic-area` | `area` | ✓ birebir |
| `ic-arrow-left` / `ic-arrow-right` | `arrow--left` / `arrow--right` | ✓ (kısa-tire alias) |
| `ic-check` | `checkmark` | ✓ (Carbon adı "checkmark") |
| `ic-chevron-right` | `chevron--right` | ✓ |
| `ic-close` · `ic-compass` · `ic-flag` · `ic-flash` · `ic-grid` · `ic-headphones` · `ic-help` · `ic-light` · `ic-locked` · `ic-moon` · `ic-pause` · `ic-renew` · `ic-restart` · `ic-ruler` · `ic-star` · `ic-trophy` · `ic-view` | aynı ad | ✓ birebir kanonik |
| `ic-info` | **`information`** | SVG path'i kanonikten türetildi (2026-07-07); id kısa-alias korunur |
| `ic-volume` | **`volume--up`** | SVG path'i kanonikten türetildi (2026-07-07); id kısa-alias korunur |
| `ic-volume-off` | **`volume--mute`** | SVG path'i kanonikten türetildi (2026-07-07); id kısa-alias korunur |
| `ic-target` | **`center--circle`** | SVG path'i kanonikten türetildi (2026-07-07); id kısa-alias korunur |

**Kural:** `ic-*`/`pic-*` id'ler motorun **iç anahtarlarıdır** (render `icon("ic-info")`
ile çağırır) — id'yi yeniden adlandırmak tüm çağrı-yerlerini kırar, bu yüzden kısa
alias'lar **kasıtlıdır**. Ama her sprite ikonunun **SVG path'i kanonik @carbon/icons
ikonundan** gelmelidir; yeni ikon eklenirken kanonik addan (yukarıdaki 2584) türet.
Piktogramlar (`pic-education/growth/idea/magic/microscope/puzzle/rocket/trophy`)
kanonik kaynağı **`@carbon/pictograms`**'dır; aynı türetme kuralı geçerli.

## 4. Grafik paleti (`@carbon/charts`)

Kanonik Carbon Charts kategorik paleti **`@carbon/charts/scss/_color-palette.scss`**'te
tanımlıdır ve doğrudan **`@carbon/colors` ölçek-değerlerinden** türer. Önemli:
Carbon Charts **sabit tek 14-sıra kullanmaz** — **N-renk-başına optimize** (1..14
renk sayısına göre farklı seçim) + **tema-başına** (White/G10/G90/G100) palet sunar.

White-teması ölçek dizisi (kanonik, hex çözümlü):

`purple70 #6929c4` · `blue80 #002d9c` · `cyan50 #1192e8` · `teal60 #007d79` ·
`magenta70 #9f1853` · `red50 #fa4d56` · `red90 #520408` · `green60 #198038` ·
`magenta50 #ee5396` · `yellow50 #b28600` · `teal50 #009d9a` · `cyan90 #012749` ·
`orange70 #8a3800` · `purple50 #a56eff`

> **Düzeltme:** `carbon-excellence.md` §3 madde 12'nin araştırma-türevi sırası
> ("Purple70, Cyan50, Teal70, Magenta70, Red50…") kanonik @carbon/charts
> white-teması dizisiyle **tam örtüşmez** (kanonik: purple70→blue80→cyan50→teal60…).
> Kanonik kaynak esastır; grafik rengi için `@carbon/charts` per-count paletini
> kullan (mümkünse @carbon/charts-react `getColors`/`ColorLegend` ile). Sıralı
> (sequential mono) ve diverging paletleri de aynı pakette tanımlıdır.

**Düzeltme (2026-07-07):** `assets/module-template.html`'deki motor `--viz-1..5`
artık kanonik Carbon Charts kategorik-aile sırasına hizalıdır — light tema
purple70→blue80→cyan50→teal60→magenta70 (`#6929c4 #002d9c #1192e8 #007d79
#9f1853`), dark tema (G100) aynı ailenin scale-40 karşılığı
purple40→blue40→cyan40→teal40→magenta40 (`#be95ff #78a9ff #33b1ff #08bdba
#ff7eb6`). `--viz-*` G-TOKEN denetimine tabi değildir (§5); bu hizalama
elle yapılmıştır, `sync_carbon_tokens.py` bu değerleri henüz otomatik
denetlemez.

## 5. Senkron + doğrulama protokolü

1. **Token:** `python scripts/sync_carbon_tokens.py --refresh` → `@carbon/{themes,
   type,motion,layout,colors}`'tan `authority.json`; `--check` (G-TOKEN) ile denetle.
   `--refresh` artık ayrıca `@carbon/icons` ve `@carbon/charts`'ı (kuruluysa) okuyup
   sürüm + ikon-sayısı bilgisini `authority.json`'un `canonical_sources` bloğuna
   kaydeder — bunlar token değeri değil, envanter/sürüm izlenebilirliğidir; `npm`
   üzerinden erişilemezlerse sessizce atlanır, `--check` yolunu etkilemez.
2. **İkon/piktogram:** yeni sprite ikonu = kanonik `@carbon/icons`/`@carbon/pictograms`
   adından SVG path türet (§3); ad kanonik listeye karşı doğrula.
3. **Grafik:** palet/tür kararı `@carbon/charts` per-count paletine dayan (§4).
4. **Figma (üçüncül):** yalnız anatomi/durum görsel teyidi — `figma-carbon-interop.md`
   §2 wire edilmiş 6 kütüphane; **değer kaynağı değil**.
