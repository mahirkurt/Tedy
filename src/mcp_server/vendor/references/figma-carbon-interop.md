# Figma ↔ Carbon İnterop — Görsel QA Doğrulama Protokolü

> Bu referans, `carbon-edupedia` token otorite zincirinin **üçüncü (opsiyonel)
> katmanını** tanımlar: IBM'in resmî **Carbon Design System v11 Figma
> kütüphaneleri** üzerinden Figma MCP araçlarıyla görsel doğrulama. **BİRİNCİL
> (kanonik) otorite daima `carbon-design-system/carbon` monorepo'su + `@carbon/*`
> npm paketleridir — bkz. `carbon-sources.md` (kanonik kaynak haritası).** Figma
> katmanı yalnız **bileşen anatomisi, durum görselleri ve değişken adlandırması**
> için üçüncül bir doğrulama yüzeyidir — token/renk/ikon **değerinin kaynağı
> DEĞİLDİR** (Figma community kopyaları sürüm-geri olabilir).

## İçindekiler
1. Ne zaman kullanılır (ve kullanılmaz)
2. Ön koşul: kütüphane erişimi
3. Doğrulama akışı (araç sırası)
4. Figma değişken adı ↔ `--cds-*` eşleme tablosu
5. Sapma triyajı kuralı
6. `figma-forge` composability — edupedia ekranlarını Figma'ya itmek
7. Bilinen sınırlamalar

---

## 1. Ne zaman kullanılır (ve kullanılmaz)

**Kullanın:**
- Bir Carbon bileşeninin **anatomisini/durumlarını** görsel olarak doğrulamak
  gerektiğinde (ör. selectable tile'ın seçili durumunda kenar kalınlığı,
  notification'ın durum çubuğu konumu).
- Kullanıcı bir **Figma dosya URL'si** paylaştığında ve edupedia çıktısının o
  dosyadaki Carbon kullanımıyla hizalanması istendiğinde.
- Yeni bir Carbon bileşen deseni şablona eklenmeden önce **ikinci-kaynak
  teyidi** istendiğinde.

**Kullanmayın:**
- Rutin modül üretiminde — şablon zaten otorite-hizalıdır; Figma çağrısı
  gereksiz gecikme ekler.
- Token **hex değeri** sorusunda — değerin kaynağı npm'dir;
  `assets/carbon-v11-authority.json` çevrimdışı yanıt verir.
- `G-TOKEN` kapısı veya `sync_carbon_tokens.py` yerine — bunlar deterministik
  ve çevrimdışıdır.

## 2. Ön koşul: kütüphane erişimi — WIRE EDİLMİŞ 6 KOPYA (2026-07-07)

IBM'in resmî v11 kütüphaneleri Figma Community'de yayımlanır; **kullanıcının kendi
hesabına kopyaladığı** altı dosya bu skill'e kanonik QA hedefi olarak bağlanmıştır.
Bu `fileKey`'ler MCP araçlarıyla **doğrudan erişilebilir** (empirik doğrulandı —
`get_metadata` sayfa yapısını döndürür):

| Kütüphane | `fileKey` | QA rolü / bağlı referans |
|---|---|---|
| **(v11) Carbon Design System** | `pqtFy76S5yq9EwRru3bNXT` | Bileşen anatomisi + değişken adlandırması (stepper/tile/notification/tag) → `carbon-child-system.md`, `carbon-excellence.md` |
| **IBM® Color Library** | `Uu7QTLz6ERkFJPD7cVEWel` | Renk primitifi/token adları — npm değeriyle çapraz-teyit (§5) → `color-system.md` |
| **IBM® UI Icon Library** | `LRj4xR57NbIBbMqH1qecJU` | 16/20/24/32px ikon **ad envanteri** + geometri → `icon-pictogram-svg.md` §2-3 |
| **IBM® Pictogram Library** | `oKaWaMXm3uqxVRTh8mbk5y` | 48px+ piktogram **ad envanteri** + stroke stili → `icon-pictogram-svg.md` |
| **Carbon Charts Library** | `503EVkMrbdCfkqBbfjLqA3` | Grafik anatomisi + kategorik/sıralı/diverging palet + tür seçimi → `carbon-excellence.md` §3 (madde 12-13), `subject-packs.md` vizChart |
| **IBM Technical Diagram Library** | `RtZDc7pMQt8HcgYTiitspr` | Teknik diyagram/akış çizgi-oku/düğüm desenleri → `svg-authoring.md` relationFlow (opsiyonel anatomi-teyidi) |

**Erişim modeli (empirik, 2026-07-07):**
1. Bu altı dosya kullanıcının **kopyalarıdır** → MCP doğrudan okur (`get_metadata`,
   `get_design_context`, `get_screenshot`, `get_variable_defs`, `get_libraries`).
2. **`search_design_system` bu bağımsız kopyalarda BOŞ döner** (`variables:[]`,
   `components:[]`) — çünkü dosyalar **abone-kütüphane içermez** (`get_libraries` →
   `libraries_added_to_file:[]`). Bulk asset araması bu dosyalarda **çalışmaz**;
   bir dizine (org/team library) yayımlanmış kütüphane gerekir.
3. Bu yüzden çıkarım **node-spesifiktir:** `get_metadata(fileKey)` → sayfa/düğüm
   ağacını gez → hedef düğümde `get_variable_defs(fileKey, nodeId)` (değişken değeri)
   veya `get_design_context(fileKey, nodeId)` (kod + ekran görüntüsü). Toplu
   token/ikon dökümü için kullanıcının **o düğümleri kullanan bir frame URL'si**
   (`…?node-id=<id>`) vermesi hızlandırır.

**Token-değeri doktrini değişmez (kritik):** Bu Figma kopyaları IBM'in bir
sürümünün *anlık görüntüsüdür* ve npm'den **eski olabilir**. Token **değerinin**
kaynağı daima npm `@carbon/*`'dır (`carbon-v11-authority.json` + `G-TOKEN` +
`sync_carbon_tokens.py`). Figma katmanı yalnız **anatomi/durum/ad** teyidi ve
§5 çapraz-doğrulaması içindir — değer kaynağı **değildir**.

## 3. Doğrulama akışı (araç sırası)

Kullanıcı bir dosya URL'si verdiğinde:

```
1. get_libraries(fileKey)
   → dosyaya bağlı kütüphaneleri listele; Carbon v11 kütüphane anahtarlarını al.

2. search_design_system(fileKey, query, includeLibraryKeys=[...])
   → hedef bileşeni/değişkeni bul (ör. "notification", "tag teal",
     "support-info"). Anahtar kapsamı verilirse sonuç gürültüsü azalır.

3. get_variable_defs(fileKey, nodeId)
   → seçili düğüme bağlı değişken tanımlarını al (ör.
     'support/support-info': #0043ce). Node-spesifik URL gerekir.

4. get_design_context(fileKey, nodeId)  [gerekirse]
   → bileşenin ekran görüntüsü + referans kodu; anatomi doğrulaması için.

5. Karşılaştır: Figma değeri ↔ assets/carbon-v11-authority.json
   → §5 triyaj kuralını uygula.
```

İkon/piktogram doğrulaması için aynı akış Icons/Pictograms kütüphanesine
uygulanır; SVG path'leri `icon-pictogram-svg.md` §2–3'teki gömülü sprite ile
karşılaştırılır.

## 4. Figma değişken adı ↔ `--cds-*` eşleme tablosu

Carbon Figma kütüphanesi değişkenleri **grup/ad** hiyerarşisi kullanır; CSS
özel değişkeni karşılıkları:

| Figma değişkeni | CSS değişkeni |
|---|---|
| `background/background` | `--cds-background` |
| `layer/layer-01` … `layer-03` | `--cds-layer-01..03` |
| `layer/layer-hover-01` / `layer-active-01` / `layer-selected-01` | `--cds-layer-hover-01` vb. |
| `layer-accent/layer-accent-01` / `-hover-01` | `--cds-layer-accent-*` |
| `field/field-01` / `field-hover-01` | `--cds-field-*` |
| `background/background-hover` / `-active` | `--cds-background-hover/active` |
| `border/border-subtle-00` / `-01` | `--cds-border-subtle-00/01` |
| `border/border-strong-01` | `--cds-border-strong` |
| `border/border-tile-01` | `--cds-border-tile` |
| `border/border-interactive` | `--cds-border-interactive` |
| `text/text-primary` / `-secondary` / `-helper` / `-placeholder` / `-on-color` | `--cds-text-*` |
| `icon/icon-primary` / `-secondary` / `-on-color` | `--cds-icon-*` |
| `link/link-primary` / `-hover` | `--cds-link-primary(-hover)` |
| `button/button-primary` / `-hover` / `-active` | `--cds-button-primary-*` |
| `focus/focus` / `focus-inset` | `--cds-focus(-inset)` |
| `support/support-success` / `-error` / `-warning` / `-info` | `--cds-support-*` |
| `notification/notification-background-*` | `--cds-notif-*-bg` |
| `misc/highlight` / `overlay` / `skeleton-*` | `--cds-highlight` vb. |
| `tag/tag-background-X` / `tag-color-X` | motor `ACCENT_STRONG` çiftleri |

Tip stilleri (`Heading 04`, `Body 02`, `Label 01`, `Code 02`) `@carbon/type`
adlarıyla aynıdır; spacing değişkenleri (`spacing/spacing-01..13`)
`--cds-spacing-*` ile birebirdir.

## 5. Sapma triyajı kuralı

Figma değeri ile npm otoritesi çelişirse:

1. **npm kazanır.** Şablon ve `authority.json` npm değerini korur.
2. Figma sapması **rapor edilir** (kullanıcıya: "Figma kütüphane kopyanız
   muhtemelen eski bir yayın; All-themes kütüphanesini güncelleyin").
3. Sapma `@carbon/themes` sürüm farkından kaynaklanıyorsa (ör. kullanıcının
   kopyası v11.x-eski), `sync_carbon_tokens.py --refresh` ile npm tarafı
   tazelenir ve karşılaştırma yinelenir.
4. Yalnız **anatomi** farkı varsa (değer aynı, görsel yapı farklı), şablonun
   bileşen deseni `get_design_context` ekran görüntüsüne göre gözden geçirilir
   — bu, token değil **desen** güncellemesidir.

## 6. `figma-forge` composability — edupedia ekranlarını Figma'ya itmek

Ters yön (edupedia → Figma) bu skill'in kapsamı dışındadır; **`figma-forge`**
skill'i ile yapılır:

- `figma-forge`'un **Carbon v11 yerleşik mapper'ı** `--cds-*` token'larını
  Figma Variables'a, edupedia bileşen desenlerini (stepper, tile, notification,
  tag) variant ComponentSet'lere dönüştürür.
- Akış: edupedia modülü üret → `figma-forge` `TOKENS_IMPORT` modu ile
  `carbon-v11-authority.json`'u (W3C DTCG-benzeri yapı) Variables olarak içe
  aktar → `COMPONENTS_BUILD` ile ekran iskeletini kur.
- Bu yol, öğretmen/veli paydaşlarına modül tasarımını Figma üzerinde gözden
  geçirtmek istendiğinde kullanılır.

## 6.1 Carbon Charts + Technical Diagram (yeni bağlı iki kütüphane)

- **Carbon Charts Library** (`503EVkMrbdCfkqBbfjLqA3`): `vizChart`/`vizTable`
  arketiplerinin **ikinci-kaynak anatomi/palet teyidi**. `carbon-excellence.md`
  §3 madde 12-13'ün (kategorik sabit sıra · sıralı/diverging · içgörü-başlığı ·
  eksen/legend) Figma karşılığı buradadır. Grafik türü/palet kararı için
  `get_screenshot(fileKey, nodeId)` ile bir örnek grafik anatomisini görsel
  teyit et — **palet HEX değeri yine npm `@carbon/colors`'tan** alınır (§5).
- **IBM Technical Diagram Library** (`RtZDc7pMQt8HcgYTiitspr`): `relationFlow`/
  süreç-diyagramı çizgi-oku, düğüm-kutu ve bağlaç desenleri için opsiyonel
  anatomi referansı (`svg-authoring.md` ok-ucu/`vz-arrow` marker'ıyla hizalı).
  Diyagram *deseni* teyidi içindir; token değeri değil.

## 7. Bilinen sınırlamalar

- **`search_design_system` bu bağımsız kopyalarda boş döner** (§2 madde 2):
  bulk asset araması çalışmaz; çıkarım **node-spesifiktir** (`get_metadata` →
  `get_variable_defs`/`get_design_context`). Toplu döküm için kullanıcının
  o düğümleri kullanan bir frame URL'si (`…?node-id=<id>`) gerekir.
- Bu altı dosya **kullanıcının kopyalarıdır** ve MCP-erişilebilir (§2); orijinal
  Community anahtarlarıyla (`1157761560874207208` vb.) doğrudan çağrı **erişim
  hatası** döndürür — daima §2'deki wire edilmiş `fileKey`'leri kullan.
- Figma kütüphanesindeki tema modları (White/G10/G90/G100) 4'lüdür; edupedia
  yalnız White + G100 kullanır — G10/G90 değerleri karşılaştırma dışıdır.
- Figma tarafındaki `light`/`dark` mod adlandırması kütüphane sürümüne göre
  değişebilir; eşlemeyi ada değil **değere** göre yapın.
- Figma kopyası npm'den **eski olabilir** → değer farkı görülürse npm kazanır
  (§5), Figma kopyasının güncellenmesi önerilir.
