# Kanonik Carbon Kaynak Haritası — `carbon-design-system/carbon` (ESAS KAYNAK)

> **Doktrin (normatif).** `carbon-edupedia`'nın TÜM Carbon fidelity'sinin **tek
> doğruluk kaynağı**, IBM'in resmî **`carbon-design-system/carbon`** monorepo'su ve
> ondan yayımlanan **`@carbon/*` npm paketleridir**. Figma kütüphaneleri (bkz.
> `figma-carbon-interop.md`) yalnız **üçüncül, opsiyonel görsel-anatomi QA**
> katmanıdır — token/renk/ikon/palet **değerinin kaynağı DEĞİLDİR** (Figma
> community kopyaları sürüm-geridir). Bu dosya her Carbon endişesi için kanonik
> paketi, GitHub yolunu ve doğrulanmış değerleri sabitler. Empirik doğrulama:
> `@carbon/*` 11.7x yerelinden (2026-07-07); §4 paleti 2026-10-10'da Carbon sitesi,
> `@carbon/charts` 1.27.2 kaynağı ve `@carbon/colors` 11.60.0 ile yeniden doğrulandı.

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
| **Spacing/layout** | `@carbon/layout` | `packages/layout` | `--cds-spacing-*` · `carbon-excellence.md` §2.1 (madde 1–2, 2x grid) |
| **UI ikonları** | `@carbon/icons` | `packages/icons` | motor sprite → §3 eşleme · `icon-pictogram-svg.md` |
| **Piktogramlar** | `@carbon/pictograms` | `packages/pictograms` | motor `pic-*` sprite → §3 · `icon-pictogram-svg.md` |
| **Grafik paleti/anatomi** | `@carbon/charts` | `packages/charts` | `vizChart`/`vizTable` → §4 · `carbon-excellence.md` §2.7 (madde 12–13) |

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

> **Güncel durum (ders renk sistemi v2.1, 2026-09-24).** Yukarıdaki tablo tarihsel kayıttır.
> Bugün `--accent`, `--accent-strong`, `--accent-tint`, `--accent-on` dersin ailesinden
> üretilen `--subject-*` rollerinin takma adlarıdır (accent palet 60 / 40, text 70 / 30,
> surface = tag zemini); sosyal bilimler cyan ailesidir (accent cyan-60 `#0072c3`), yeşil
> ayrılmış anlam rengidir ve hiçbir derse verilmez. Değerler ve kurallar:
> `tedy-integration.md` §3.1, otorite `assets/carbon-v11-authority.json` → `tedyLayer.subjectThemes`.

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
| `ic-checkmark-outline` · `ic-incomplete` · `ic-circle-dash` | `checkmark--outline` · `incomplete` · `circle-dash` | ✓ birebir (`@carbon/icons` svg/32; ilerleme göstergesinin tamamlanan / geçerli / başlanmamış adımı, Carbon `ProgressStep`'in ikonları; 2026-10-20) |
| `ic-chevron-right` | `chevron--right` | ✓ |
| `ic-close` · `ic-compass` · `ic-flag` · `ic-flash` · `ic-grid` · `ic-headphones` · `ic-help` · `ic-light` · `ic-locked` · `ic-moon` · `ic-pause` · `ic-renew` · `ic-restart` · `ic-ruler` · `ic-star` · `ic-trophy` · `ic-view` | aynı ad | ✓ birebir kanonik |
| `ic-info` | **`information`** | SVG path'i kanonikten türetildi (2026-07-07); id kısa-alias korunur |
| `ic-volume` | **`volume--up`** | SVG path'i kanonikten türetildi (2026-07-07); id kısa-alias korunur |
| `ic-volume-off` | **`volume--mute`** | SVG path'i kanonikten türetildi (2026-07-07); id kısa-alias korunur |
| `ic-target` | **`center--circle`** | SVG path'i kanonikten türetildi (2026-07-07); id kısa-alias korunur |

> **Denetim (2026-10-10, `@carbon/icons` 11.90.0 · 2633 ikon; Carbon MCP v11.117.0 etiketini
> indeksler).** Tablodaki "birebir" iddiası her ikon için doğru değildir: `ic-flash`, `ic-headphones`,
> `ic-ruler`, `ic-area`, `ic-grid` elle çizilmiş tam sayı geometridir; `ic-compass` ve `ic-trophy`
> 11.90 çiziminden farklıdır; eşleşenlerin çoğu `--filled` varyantından gelir (`checkmark--filled`,
> `close--filled`, `star--filled`, `help--filled`, `flag--filled`, `pause--filled`, `view--filled`).
> Sprite şablonun içindedir ve şablon bayt-sabitlidir; ikonların yeniden türetilmesi açık maddedir.
> Yeni ikonun kanonik kaynağı Carbon MCP `code_search` (`canonical_url`) ya da npm paketidir.

**Kural:** `ic-*`/`pic-*` id'ler motorun **iç anahtarlarıdır** (render `icon("ic-info")`
ile çağırır) — id'yi yeniden adlandırmak tüm çağrı-yerlerini kırar, bu yüzden kısa
alias'lar **kasıtlıdır**. Ama her sprite ikonunun **SVG path'i kanonik @carbon/icons
ikonundan** gelmelidir; yeni ikon eklenirken kanonik addan (yukarıdaki 2584) türet.
Piktogramlar (`pic-education/growth/idea/magic/microscope/puzzle/rocket/trophy`)
kanonik kaynağı **`@carbon/pictograms`**'dır; aynı türetme kuralı geçerli.

## 4. Grafik paleti (`@carbon/charts`)

Kanonik Carbon Charts kategorik paleti **`@carbon/charts/scss/_color-palette.scss`**'te
tanımlıdır ve renkleri `@carbon/colors` adımlarıyla adlandırır. Carbon sitesi kategorik
renklerin **sırayla, kesin** uygulanmasını ister; kategori sayısı öngörülebilirse sayıya
özel gruplar (1–5 renk) diziyi geçersiz kılabilir
(https://carbondesignsystem.com/building-blocks/data-visualization/color-palettes/#categorical-palettes).
Paket tema başına (white / dark) ayrı gruplar tanımlar; 6–13 renk için grup yoktur.

White-teması 14'lü kategorik dizi (site ile `@carbon/charts` 1.27.2 `'14'` grubu aynı; HEX
`@carbon/colors` 11.60.0'dan):

`purple70 #6929c4` · `cyan50 #1192e8` · `teal70 #005d5d` · `magenta70 #9f1853` ·
`red50 #fa4d56` · `red90 #520408` · `green60 #198038` · `blue80 #002d9c` ·
`magenta50 #ee5396` · `yellow50 #b28600` · `teal50 #009d9a` · `cyan90 #012749` ·
`orange70 #8a3800` · `purple50 #a56eff`

White-teması 5-renk grupları: seçenek 1 purple70 · cyan50 · teal70 · magenta70 · red90;
seçenek 2 blue80 · teal50 · magenta70 · red90 · purple50. 1-renk grubu dört **seçenektir**
(purple70 / blue80 / cyan50 / teal60), bir dizi değildir.

> **Düzeltme (2026-10-10).** Bu bölümün 2026-07-07 tarihli "düzeltmesi" yanlıştı: dizinin
> "purple70 → blue80 → cyan50 → teal60 → magenta70 …" olduğunu söylüyordu; bu, 1-renk grubunun
> dört seçeneğinin bir dizi gibi okunmasıydı. `carbon-excellence.md` §2.7 madde 12'deki sıra
> doğrudur. **HEX npm'den gelir ilkesi geçerlidir:** site Red 90'ı `#570408`, Magenta 50'yi
> `#ee538b` basar; `@carbon/colors` `#520408` ve `#ee5396` verir — değer kaynağı paket.
> Site 1-renk seçenek 4'ü Teal 70 basar, paket teal60 kullanır; hangisinin güncel olduğu
> açık maddedir. Sıralı (sequential mono) ve diverging paletler de aynı paketin içindedir.

**Motor `--viz-1..5` (TEDY alt kümesi, S19).** Şablonun yuvaları açık temada
purple70 · blue80 · cyan50 · teal60 · magenta70 (`#6929c4 #002d9c #1192e8 #007d79 #9f1853`),
g100'de purple40 · blue40 · cyan40 · teal40 · magenta40 (`#be95ff #78a9ff #33b1ff #08bdba
#ff7eb6`) değerlerini taşır. Önceki notun dediği gibi "kanonik Carbon Charts sırasına hizalı"
**değildir**: hiçbir resmî 5-renk grubuna (açık ya da koyu) uymaz. Doğru okunuşu, Carbon'un
kategorik tonlarından Tedy anlam renklerini (kırmızı, yeşil, sarı, turuncu) dışarıda bırakan
bir alt kümedir; açık temanın iki 5'li grubu Red 90, koyu seçenek 2 Red 10 ve Green 30 içerdiği
için olduğu gibi alınamaz (koyu seçenek 1 — purple60 · teal40 · cyan20 · blue50 · magenta40 —
anlam rengi içermez). Yuvaların yeniden seçimi şablon değişikliğidir — **açık madde**
(`color-system.md` §7). `--viz-2` Tedy bandının laciverdi, `--viz-1` Matematik'in `text`
rolüyle aynı renktir; tek ders bağlamında kabul edilir. `--viz-*` G-TOKEN denetimine tabi
değildir; `sync_carbon_tokens.py` bu değerleri denetlemez.

## 5. Senkron + doğrulama protokolü

1. **Token:** `python scripts/sync_carbon_tokens.py --refresh` → `@carbon/{themes,
   type,motion,layout,colors}`'tan `authority.json`; `--check` (G-TOKEN) ile denetle.
   (2026-10-10 notu: otoritede `canonical_sources` bloğu yoktur; sürüm izi
   `_provenance`'tadır. `--refresh`'in ikon/grafik envanteri yazdığına güvenmeyin.)
2. **İkon/piktogram:** yeni sprite ikonu = kanonik `@carbon/icons`/`@carbon/pictograms`
   adından SVG path türet (§3); ad kanonik listeye karşı doğrula.
3. **Grafik:** palet/tür kararı `@carbon/charts` per-count paletine dayan (§4).
4. **Carbon MCP (doğrulama katmanı):** npm değerleri ile Figma arasında rehber ve kod
   doğrulaması — `docs_search` (rehber metni + `anchor_url`, her Carbon iddiasının kaynağı),
   `code_search` (kanonik ikon, piktogram ve bileşen kodu, `canonical_url`), `get_charts`
   (Carbon Charts), `code_audit` (token ve erişilebilirlik denetimi). Değer kaynağı yine npm'dir.
   Protokol: `docs/tedy-ui-ux-talimatnamesi.md` §10.
5. **Figma (üçüncül):** yalnız anatomi/durum görsel teyidi — `figma-carbon-interop.md`;
   **değer kaynağı değil**. 2026-10-10'da altı kopya kapak sayfasından ibaretti.
