# TEDY Modül Tasarım Kanunu

**Sürüm 1.4 · 2026-10-24**

Bu kanun, tedy.online panosunda açılan edupedia modüllerinin nasıl görüneceğini ve nasıl davranacağını bağlayıcı olarak yazar. Modül yüzeylerinde talimatnamenin, edupedia vendor referanslarının, `edupedia_rehber`'in vendor bölümlerinin ve edupedia Claude eklentisinin önündedir.

Kime yazıldı: `MODULE_DATA` yazan yapay zekâ ajanına (§1), modül şablonunu ve ted-mcp'yi bakan geliştiriciye (§2–§6), modül sayfasını inceleyen denetçiye (§8). Kanun kodu anlatmaz; kodun nereye gideceğini söyler. Bugünkü kod hükümden ayrılıyorsa madde "borç KB-n" der ve borç §9'da ölçümüyle durur.

## 0. Yetki, kapsam ve öncelik

### 0.1 Kapsam

Kanun yalnız **modül yüzeylerini** yönetir:

- Çerçevenin içi: `iframe.module-frame` içinde çizilen her şey (`src/mcp_server/vendor/assets/module-template.html`, `src/mcp_server/sablon.py` yamaları, derleyicinin yazdığı altbilgi).
- Modül sayfasının başı ve kabı: `ModulBasligi.tsx`, `ModulAiEtiketi.tsx`, `ModuleViewer.tsx` ve `Modules.scss`'in modül sayfası kuralları.
- Aynı yüzeylerin öteki açılışları: taslak önizleme (`/moduller/taslak/<id>`, taslak bildirimi dahil), şablonun `modul.tedy.online`'da tek başına açılışı (yedek, M1.1) ve bilet geçersiz sayfası.
- Yazarın verdiği tasarım kararları: `MODULE_DATA`'nın görünümü etkileyen her alanı ve `meta.assets`.

Kapsam dışı: `/moduller` listesi ve müfredat ağacı (talimatname ve yüzey tasarımları yönetir), İşler'deki "Modülü aç" düğmesi ve asistanın modül atıfı (pano yüzeyleridir), panonun geri kalanı, Tedy Books, modülün pedagojik içeriği (doğruluk, kazanım hizası; vendor `pedagoji` ve `mufredat` bölümleri yönetir).

Kanunun düzenlemediği her konuda modül yüzeylerinde talimatname ve alttaki basamaklar uygulanır (özellikle talimatname §3–§8 ve §12); kanunun düzenlediği bir konuda alt metnin aynı konudaki kuralı modülde uygulanmaz (talimatname §0.2 aynı cümleyi taşır).

### 0.2 Öncelik

1. Değişmezler D1–D4 → 2. İlkeler İ1–İ9 → 3. **Modül Tasarım Kanunu** (yalnız §0.1 kapsamında) → 4. Talimatname → 5. Yüzey tasarımları → 6. Bileşen rehberi → 7. `tedy-carbon` → 8. edupedia vendor (`src/mcp_server/vendor/SKILL.md`, `references/` ve `edupedia_rehber` çıktısının bunlardan gelen kısmı) ve edupedia Claude eklentisi → 9. carbon-builder → 10. Carbon'un genel rehberi.

- Anayasanın D/İ dışındaki bölümleri (§5 Sistem, §9 Yapmayacaklarımız, §10 kapıları) D1–D4 ile İ1–İ9'un açıklamasıdır ve onlarla aynı basamaktadır. Kanun onlarla çelişemez; çelişki varsa anayasa aynı commit'te değişir ya da kanun maddesi düşer.
- `edupedia_rehber`'in `kanun` bölümü ve `akis` ile `carbon` bölümlerinin başındaki §1 kanunun kendisidir; 3. basamaktadır, 8. basamakta değil.
- Çelişkide üstteki kazanır. Kanunla çelişen alt metin aynı commit'te düzeltilir ya da §9'a kanun borcu olarak yazılır. İki kural sessizce yan yana yaşamaz.
- Vendor'un "tek kaynak" ve "yetkili kural" cümleleri (`vendor/SKILL.md:374-376`, `tedy-integration.md:245-250`, talimatname §9.6 T:2946, `CLAUDE.md:354`) **yazım varlıkları** için geçerli kalır: şablon, otorite JSON'u ve referans dosyaları orada yaşar ve `vendor_sync --pin` ile sabitlenir. Tasarım kararında bu dosyalar kanunun altındadır.
- Ölçüm varsayımı yener. Carbon'a ait bir iddia Carbon MCP `anchor_url`'ı taşır (§10.2).

### 0.3 Kanunun ilkeleri

Kanun kullanıcının beş ilkesini beş maddeye çevirir:

| Madde | İlke | Kimlik |
|---|---|---|
| I | Modül tedy sayfasının organik parçasıdır; görsel bütünlük ve stil tutarlılığı | M1.x |
| II | Carbon MCP ile doğrulanmış Carbon tasarım dili | M2.x |
| III | edupedia'nın içerik ve görsellerinden geniş, ölçülebilir yararlanma | M3.x |
| IV | Tek tema; modül içeriğine özel tema ya da stil yok | M4.x |
| V | İlerleme göstergesi, etiketler ve her unsur telefondan 4K'ya en iyi deneyim | M5.x |

Her madde yanlışlanabilir: bir ölçümle ya da testle düşer. Denetimi olmayan madde "kurulacak: KB-n" der.

### 0.4 Yazara ulaşma

Kanun tek dosyadır: `docs/tedy-modul-tasarim-kanunu.md`. Kopyası yoktur. ted-mcp'nin `edupedia_rehber` aracı onu `kanun` bölümü olarak bütünüyle servis eder ve §1'i `akis` ile `carbon` bölümlerinin başına koyar (`src/mcp_server/rehber.py` `SECTIONS`). Bu yüzden:

- Üst bölümler `## N. Ad` biçimindedir; numaralar değiştirilmez. Alt bölümler `###` ile yazılır.
- §1 başlığıyla birlikte en çok **3300 bayt** (UTF-8) tutar.
- `akis` ve `carbon`'un ilk parçası kanun §1 ile başlar; `akis`'te onu `SKILL.md` §8, `carbon`'da `SKILL.md` §10 izler. Parça sınırı 8000 bayttır.

## 1. Yazar için kanun

`MODULE_DATA` yazan ajan bu maddelere uyar. Kanun `edupedia_rehber`'in vendor bölümlerinin ve edupedia Claude eklentisinin önündedir; onların bir cümlesi bunlarla çelişirse kanun kazanır.

1. **Stil yazma (M4.5–M4.7).** `MODULE_DATA` renk, hex, tema, CSS, font, satır içi stil ve `meta.accent` taşımaz; grafik verisinde `color` yazılmaz. Ders rengini `meta.subject` belirler. Yazar SVG'si yalnız `var(--cds-*)` ve `var(--viz-*)` kullanır, metin taşımaz: ad `labels`'a (M5.6).
2. **Tema yok (M4.1).** Modül temayı panodan alır. Tema düğmesi, koyu mod önerisi ya da metni yazılmaz.
3. **Görsel zinciri (M3.1).** Görseli `edupedia_gorsel` getirir: kitap figürü → Pexels → MiniMax. Ücretli medya yalnız kullanıcı onayıyla. Varlık `meta.assets` ile `<teachId>.visual` yuvasına bağlanır. Script çalıştırılmaz.
4. **Görsel yoğunluğu (M3.2–M3.5).** Çerçeve ders kitabıysa teach segmentlerinin en az %60'ı görsel taşır. Pencerede N içerik figürü varsa en az min(N, teach sayısı, 4) farklı kitap figürü kullanılır. Figürün `page_no`'su çerçeve sayfalarındadır; değilse gerekçe `meta.assets[i].pencere_disi_gerekce`'ye yazılır. Her modülde en az bir yazar görseli vardır (chart, table, labeled, flow, cards, numberline); kitap figürü onun yerini almaz. Bütçe az görselin gerekçesi değildir (M3.9). Bir altyapı sınırı (KB-13) bir kuralı engellerse yazar bunu kapı raporunda bildirir (M3.11).
5. **Alt metin ve altyazı (M3.6–M3.8).** Raster görselde `meta.assets[i]`: `alt` 60–150 karakterlik bitmiş cümle, "Bu fotoğraf/çizim/şema" ile başlamaz; `baslik` görünür altyazı, kitaptaki adıyla (ör. "Görsel 1.30: İstiklal Yolu"), ≤ 120 karakter, sayfasız, varlığın tek adı. Süs görseli: `alt: ""`, `baslik` yok. Alt metnin ad ve sayıları kitabın metninde (`kitap_altyazisi`, `etiket`, çerçeve sayfaları) geçer; `betim` dayanak değil. Yoksa nedeni `alt_gerekce`'ye.
6. **Piktogram (M3.10).** Yalnız sprite anahtarları: `pic-idea`, `pic-education`, `pic-rocket`, `pic-growth`, `pic-puzzle`, `pic-microscope`, `pic-magic`. `ic-*` piktogram yerine, `pic-*` ikon yerine (ör. `keyTerms[].icon`) yazılmaz; `ic-idea` ve `ic-flip` yoktur; `pic-trophy`, `ic-trophy` ve `ic-star` kullanılmaz.
7. **Ödül ve rekabet yok (M2.7).** Rozet, XP, seri, puan, kutlama ve `rewards.badges` yok. Başlık, kicker ve yönergede "Yarışma", "Meydan oku", turnuva gibi çerçeve yok (G-WELLBEING); anlatı serbest. `rewards` isteğe bağlı iç sayıdır: `{xpPerCorrect, firstTryBonus}`.
8. **İlerleme (M2.5).** `meta.milestones` 3–7 aşama tanımlar; her öğe `{atSegmentId, title}`. Aşama o segmentte başlar, sonraki öğeye kadar sürer; ilk öğe ilk segmenttedir. `title` 1–2 sözcük, en çok 16 karakter, cümle düzeninde ("Keşfet", "Uygula"). `meta.quest` yazılmaz.
9. **Başlık düzeni (M2.9).** Modül ve bölüm adları başlık düzeninde; kicker, düğme, etiket ve yönerge cümle düzeninde. Tümü büyük harf dizge yok.
10. **Görünüm yazarın değildir (M4.7).** Segment türünü içerik seçer; bir türün görünüşünü yazar değiştiremez.

## 2. Madde I — Organik bütünlük

Modül panonun içinde açılan ayrı bir sayfa değildir; panonun bir bölümüdür. Okur panonun nerede bitip modülün nerede başladığını görmez.

**M1.1 — Akış yerleşimi modülün tek tasarım hedefidir; lacivert bant, Tedy işareti ve modülün kendi başlık bloğu yalnız modül tek başına açıldığında görünür.**
- Neden: Akışta sayfanın başı panonundur (ModulBasligi). Tek başına açılış (`modul.tedy.online` doğrudan) bir yedektir; bir karar yalnız oraya göre verilmez.
- Dayanak: talimatname §9.1 (akış yerleşimi, 2026-10-19); İ1; [Color — guidelines #inline-theming](https://carbondesignsystem.com/building-blocks/foundations/color/guidelines/#inline-theming) (cümle MCP indeksinde yok, canlı sayfada doğrulandı 2026-10-20; Carbon satır içi temanın yaygın kullanımını UI kabuğu ve yan paneller olarak verir; bir içerik bölümünün farklı temada çizilmemesi kanunun kararıdır, M4.1).
- Denetim: `tests/test_modul_akis_yerlesimi.py`; `moduller.spec.ts:412` ("the module sits in the page flow").
- Durum: uyuyor (`module-template.html:1044-1075`).

**M1.2 — Akışta çerçevenin sayfa zemini panonun sayfa zeminidir (`--ted-color-page-bg`, cool-gray-10, #f2f4f8).**
- Neden: Ölçüldü: çerçeve gövdesi rgb(244,244,244), pano gövdesi rgb(242,244,248). Çerçeve sayfada ayrı tonlu bir dikdörtgen olur.
- Dayanak: D1; talimatname §9.4 ("akışta sayfa zemini panonun cool-gray zeminidir"), S20; `ted-theme.scss:49` (`--ted-color-page-bg`), `:95`, `:196`.
- Denetim: `dashboard/tests/e2e/moduller.spec.ts` "the module sits in the page flow" (iki gövdenin hesaplanmış zemini eşit); `tests/test_modul_akis_yerlesimi.py::test_akista_zemin_panonun_sayfa_zeminidir`.
- Durum: uyuyor (KB-3 kapandı 2026-10-20: akış kuralı `body{background:var(--tedy-page-background)}`).

**M1.3 — Modül panonun sütununu her genişlikte tam ve simetrik doldurur.**
- Neden: Ölçüldü: 360 ve 390 px'te modül sayfası 312 ve 342 px; sütunun içerik kutusundan 16 px dar, sol kenar 16 px, sağ kenar 32 px.
- Dayanak: talimatname S1 (tek sütun); `tasarim-denetimi.spec.ts` "every page has the same column".
- Denetim: kurulacak: KB-31 (modül rotası `tasarim-denetimi`'nin eşit sütun ölçümüne eklenir).
- Durum: borç KB-31 (`Modules.scss:45` `width: min(58rem, calc(100vw - 3rem))`).

**M1.4 — Görünümdeki tek büyük ders yüzeyi panonun başıdır; modülün içi nötrdür.**
- Neden: İ8.3 görünüm başına bir büyük ders yüzeyine izin verir ve o yüzey ModulBasligi'dir. Her segmentte dolu renkli bir ikon karesi onunla yarışır.
- Dayanak: İ8 madde 3; talimatname [3.2-13] (görünümde 120 px'i aşan en çok bir ders yüzeyi), [3.2-15] (panel kenarla ayrılır); `Modules.scss:66-75`.
- Denetim: kurulacak: KB-16 (şablonda `background:var(--subject-accent)` ve `--accent` dolgusu sayan statik test).
- Durum: borç KB-16 (`module-template.html:897` etkinlik segmentlerinde dolu `--subject-accent` ikon karesi).

**M1.5 — Ders rengi modülün içinde yalnız şu çapalarda görünür: kavram yüzeylerinin (`.lead`, merak kartı) 4 px kenarı, vurgulu terimin tint zemini, kavram çipinin tint zemini ve ders kenarı, segment ikonunun tint zemini.**
- Neden: Çapa sayısı sınırlı değilse ders rengi her yüzeye yayılır. Ölçüldü (grep, `var(--accent…|--subject…)`): CSS kurallarında 67 kullanım / 56 satır, motorda 23 / 18 satır.
- Dayanak: İ8; S35; talimatname [3.2-14] (ders rengi yalnız dolu şekil: kare, şerit, kenar, zemin; halka, `outline`, alt çizgi ya da seçim kenarı asla; mavi aile eylem mavisiyle aynı değerdir). Talimatname §9.2 bu listeye yönlendirir; vendor'un eski geniş listesi KB-35 ile düzeltildi.
- Denetim: kurulacak: KB-17 (ders rolü token'larını yalnız izinli seçicilerde kabul eden allow-list testi).
- Durum: borç KB-17 (çapa dışı 32 kural, §9).

**M1.6 — Etkileşim durumları (hover, seçili, işaretli, geçerli adım, odak) ders rengi almaz; Carbon etkileşim token'larıyla çizilir.**
- Neden: Bir durum her derste aynı görünür (İ9). Seçili seçenek Matematik'te mor, Fen'de teal olursa okur durumu yeniden öğrenir. Carbon'un seçilebilir karosunda seçili kenar `$border-inverse`, odak `$focus`, hover `$layer-hover`'dır.
- Dayanak: S35 (birincil eylem her kipte `$button-primary`, ilerleme Carbon mavisi); talimatname [3.2-14] (seçili hâl ders renginden bağımsız ikinci işaretle); panoda ders renkli seçili hâle izin veren [3.2-4] modülde uygulanmaz; [Progress indicator — specifications #color](https://carbondesignsystem.com/building-blocks/core/components/progress-indicator/specifications/#color); [Tile — specifications #selectable-tile-interactive-state-color](https://carbondesignsystem.com/building-blocks/core/components/tile/specifications/#selectable-tile-interactive-state-color); [Accessibility — developers #style-focus-indicators](https://carbondesignsystem.com/building-blocks/foundations/accessibility/developers/#style-focus-indicators).
- Denetim: kurulacak: KB-17 (aynı allow-list; `:hover`, `[aria-*]`, `--sel`, `:checked`, `accent-color`, `:focus*` seçicilerinde ders rolü yasak).
- Durum: borç KB-17 (11 durum kuralı: `.opt:hover` 652, `.opt--sel` 662, `.hook-opt` 736-739, `.def-term:hover` 552, `.chip-btn:hover` 691, `.cmap-node--sel` 867 …).

**M1.7 — Kırmızı, yeşil, sarı ve turuncu modülde yalnız anlam rengidir; hiçbir derse ve süse verilmez.**
- Neden: Durum rengi bir uyarı ya da sonuç söyler; süs olarak kullanılırsa sinyal kaybolur.
- Dayanak: İ8; [Status indicators #status-color-palette](https://carbondesignsystem.com/building-blocks/core/patterns/status-indicators/#status-color-palette); [Data visualization — color palettes #alert-palette](https://carbondesignsystem.com/building-blocks/data-visualization/color-palettes/#alert-palette).
- Denetim: `tests/test_ders_renkleri.py`; derleyici şeması (`derleme.py:381-386`).
- Durum: uyuyor.

**M1.8 — Görünümün en büyük yazısı panonun modül başlığıdır (`heading-05`); modülün içinde segment ve özet başlığı en çok `heading-04`'tür (1,75rem); hiçbir modül metni `heading-05` boyuna eşit ya da ondan büyük çizilmez.**
- Neden: Sayfa hiyerarşisi tek başlıkla kurulur (P1). Ölçüldü: özet başlığı serif 40 px / 600, mola geri sayımı 40 px mono. Ekran 1024–1920'de (kök 16) 40 px'e karşı pano başlığı 32 px; ekran 3840'ta (kök 32) 80 px'e karşı 64 px. Telefonda özet başlığı 2rem, pano başlığına eşit.
- Dayanak: talimatname §7.1 P1; `Modules.scss:115-120`; `heading-05` 2rem / 1,25 (`dashboard/node_modules/@carbon/type/lib/index.js:369-374`, @carbon/type 11.69.0).
- Denetim: kurulacak: KB-14 (her genişlikte çerçeve içindeki en büyük hesaplanmış `font-size` < ModulBasligi h2'ninki ve ≤ 1,75rem).
- Durum: borç KB-14 (`module-template.html:779`, 775, `--fs-display` 353, 990).

**M1.9 — IBM Plex Serif modülde yalnız matematik gösterimi içindir (`.math`, kesir eşitliği); giriş metni, özet başlığı ve çeviri satırı Plex Sans'tır.**
- Neden: Panoda serif yalnız Tedy Books'tadır. Giriş metni ve özet başlığı serif olunca modül başka bir ürün gibi okunur.
- Dayanak: anayasa §5.2 (tipografide iki dünya); `ted-theme.scss:2940-2941`. Talimatname §9.8 madde 14 aynı kuralı yazar (`mathExpr` serifi geçerli, `.lead` serifi kalkar; KB-34 kapandı).
- Denetim: kurulacak: KB-15 (`--font-serif` kullanımını `.math` ve `.fb-eq` dışında yasaklayan statik test).
- Durum: borç KB-15 (`.lead` 537, `.summary h2` 779, `.gloss-tr` 973).

**M1.10 — Modülün içinde ikinci bir kazanım satırı, başlık bloğu, AI etiketi ya da yer işareti yoktur; bunlar panonun başındadır.**
- Neden: Aynı bilgi iki kez yazılırsa okur hangisinin geçerli olduğunu sorar (İ1). Kazanım etiketleri `OperationalTag` → `Modal` ile başta açılır; AI etiketi S41 ile çerçeve başlığındadır. Pano zaten `<main>` taşır; akışta çerçevenin `banner` ve `main` yer işareti ikinci bir sayfa iskeleti kurar. Bölüm başlığı çerçevenin tek başlık düzeyini başlatır.
- `objectives` ("Bu modülde", "Tamamladığın hedefler") öğrenci dilinde hedef listesidir, kazanım satırı sayılmaz: kazanım kodu ve resmî kazanım metni taşımaz, ders rengi almaz.
- Dayanak: S41; talimatname §9.1; [AI label — guidelines #in-containers](https://carbondesignsystem.com/building-blocks/core/components/ai-label/guidelines/#in-containers).
- Denetim: `tests/test_modul_akis_yerlesimi.py` (`.topbar__l` gizli); `moduller.spec.ts:463` (baş); kurulacak: KB-40 (`aria-yapisi` modül rotası; akışta `role="banner"`/`role="main"` yok).
- Durum: başlık bloğu ve AI etiketi uyuyor; yer işareti borç KB-40 (1083, 1129); `objectives` kenarı borç KB-17 (783).

**M1.11 — Modül sayfası panonun durum dilini kullanır: yükleme 400 ms'den sonra içeriğin şeklinde iskelet, hata yalnız bizim cümlemizle `InlineNotification`.**
- Neden: Yanıp sönen iskelet gürültüdür (S36). Ölçüldü: `ModuleViewer` bilet yüklenirken iskeleti hemen çiziyor.
- Dayanak: S36, B48; D3; [Loading #skeleton-states](https://carbondesignsystem.com/building-blocks/core/patterns/loading/#skeleton-states).
- Denetim: kurulacak: KB-37 (`yukleme-esigi.spec.ts`'e modül rotası).
- Durum: borç KB-37 (`ModuleViewer.tsx:150`); hata kısmı uyuyor (`:156`).

## 3. Madde II — Carbon dili

Modül Carbon v11 ve Tedy katmanıyla çizilir. Bir Carbon kararı ezberden yazılmaz.

**M2.1 — Şablonun ya da görüntüleyicinin her Carbon iddiası (bileşen anatomisi, token, boyut, durum) Carbon MCP'den doğrulanır ve `anchor_url` ile kaydedilir.**
- Neden: Eğitim verisi bayatlar. Bugünkü şablonun stepper'ı, düğmesi ve bildirimi Carbon'u taklit ediyor ama ölçüleri ve anatomileri Carbon'dan ayrılıyor.
- Dayanak: talimatname §10; `vendor/SKILL.md:377-380`.
- Denetim: §10.2 tablolarında şablonun Carbon'u taklit eden her bileşeni (`.stepper`, `.btn`, `.icon-btn`, `.feedback`, `.callout`, `.opt`, `.def-pop`, form alanları, `.viz-table`, kaydırıcı) için en az bir anchor satırı vardır; satırı olmayan bileşen sınıfı bulgu sayılır. Şablonu değiştiren commit kullandığı anchor'ı mesajında taşır.
- Durum: uyuyor (1.0'da her bileşen sınıfının satırı var).

**M2.2 — Modül düğmeleri Carbon Button dilindedir: görünümde tek primary (Devam, Kontrol et); öteki eylemler secondary, tertiary ya da ghost; boy lg 48 px ve expressive tür (etiket `body-compact-02` 16 px / 400, ikon 20 px); köşe 0; etiket sola yaslı, ortalanmaz; ikon etiketten sonra gelir; ghost düğmenin kabı saydamdır ve çerçevesi yoktur.**
- Neden: Panodaki Carbon `Button` ile aynı görünmeyen düğme organik bütünlüğü bozar (talimatname §4.2, S12; panonun lg düğmesi productive'dir, modülünki expressive). Okuma gövdesi 18 px olduğundan Carbon'un 16 px gövdeyle eşlediği tür expressive'dir.
- Dayanak: [Button — specifications #size](https://carbondesignsystem.com/building-blocks/core/components/button/specifications/#size); [Button — specifications #ghost-button-color](https://carbondesignsystem.com/building-blocks/core/components/button/specifications/#ghost-button-color); [Button — specifications #typography](https://carbondesignsystem.com/building-blocks/core/components/button/specifications/#typography); [Button — guidelines #a-single-high-emphasis-button](https://carbondesignsystem.com/building-blocks/core/components/button/guidelines/#a-single-high-emphasis-button); [Button — guidelines #multiple-button-emphasis](https://carbondesignsystem.com/building-blocks/core/components/button/guidelines/#multiple-button-emphasis); [Button — guidelines #button-sizes](https://carbondesignsystem.com/building-blocks/core/components/button/guidelines/#button-sizes) ("Large (expressive)… balance when paired with 16px body copy"); [Button — guidelines #anatomy](https://carbondesignsystem.com/building-blocks/core/components/button/guidelines/#anatomy) (etiket sola yaslı, ikon sağda; MCP: #4-icon-button); [Button — specifications #button-structure](https://carbondesignsystem.com/building-blocks/core/components/button/specifications/#button-structure) (ikon 16 px, expressive 20 px); [Button — guidelines #label-alignment](https://carbondesignsystem.com/building-blocks/core/components/button/guidelines/#label-alignment); [Button — guidelines #ghost-button](https://carbondesignsystem.com/building-blocks/core/components/button/guidelines/#ghost-button); React'te `isExpressive` (`dashboard/node_modules/@carbon/react/lib/components/Button/Button.d.ts:39`, @carbon/react 1.114.0).
- Denetim: kurulacak: KB-19 (çerçeve içindeki her görünür düğmenin yüksekliği, köşesi, ghost kenarı, etiket hizası ve ikon sırası; görünümde `kind=primary` sayısı ≤ 1).
- Durum: borç KB-19 (ghost ve devre dışı ghost'ta içten 1 px çerçeve 636, 641; ikon etiketin solunda 2048, 2220, 2288, 2888, 3210, 3222, 3223; ortalı etiket `.btn--center` 643, 3167, 3210; etiket 16 px / 500 ve ikon 18,4 px 629, 642).

**M2.3 — Geri bildirim ve bilgi kutusu Carbon inline ya da callout notification anatomisindedir ve düşük kontrastlı türdedir (talimatname S27, §5.3 kural 1): köşe 0, 3 px sol kenar, ikon + başlık + metin, anlam renkleri, en az 48 px yükseklik; callout kapatılamaz; kutunun içinde düğme ya da bağlantı yoktur, eylem kutunun dışındadır.**
- Neden: Modül kendi bildirim dilini icat ederse pano ile iki ayrı uyarı dili oluşur. Carbon'da inline bildirim etkileşimli öğe taşımaz ve odak almaz; eylem taşıyan bildirim ayrı bir türdür (actionable) ve odağı yakalar.
- Dayanak: [Notification — guidelines #inline](https://carbondesignsystem.com/building-blocks/core/components/notification/guidelines/#inline); [Notification — guidelines #callout](https://carbondesignsystem.com/building-blocks/core/components/notification/guidelines/#callout); [Notification — specifications #inline](https://carbondesignsystem.com/building-blocks/core/components/notification/specifications/#inline); [Notification — specifications #callout](https://carbondesignsystem.com/building-blocks/core/components/notification/specifications/#callout); [Notification — accessibility #inline-and-toast](https://carbondesignsystem.com/building-blocks/core/components/notification/accessibility/#inline-and-toast); [Notification — accessibility #actionable](https://carbondesignsystem.com/building-blocks/core/components/notification/accessibility/#actionable). Callout'un içinde bağlantı olmaması Carbon dayanağı yok, kanunun kararı: Carbon callout'ta bağlantıya izin verir ([Notification — accessibility #callout](https://carbondesignsystem.com/building-blocks/core/components/notification/accessibility/#callout)).
- Denetim: kurulacak: KB-20 (`.feedback`, `.callout` hesaplanmış köşe 0, sol kenar 3 px, ikon var, kutu içinde `button`/`a` 0).
- Durum: borç KB-20 (`.feedback` 664-674 8 px köşe; `.callout` 820-830 8 px köşe, 4 px kenar). Eylem bugün kutunun dışında (2042-2045). Köşe 0 Carbon v11'in değeridir; Carbon v12'ye geçişte (inline `$border-radius-04`, `enable-v12-release`) madde yeniden ölçülür.

**M2.4 — Görünümde tek ilerleme göstergesi vardır ve Carbon ProgressIndicator semantiğiyle çizilir: tamamlanan ve geçerli adım `$interactive`, başlanmamış adım `$icon-primary`, çizgiler `$border-interactive` / `$border-subtle`, etiket `$text-primary`.**
- Neden: İki ilerleme göstergesi iki ayrı "neredeyim" cevabıdır (İ1). Ölçüldü: bugünkü stepper etiketsiz numaralı dairelerdir, bekleyen adımı `text-secondary` ile çizer. Bölüm içindeki soru sayacı ("Soru 1 / 5", `.adim-sayaci`) ve süre metni sayaçtır, gösterge sayılmaz.
- Dayanak: [Progress indicator — guidelines](https://carbondesignsystem.com/building-blocks/core/components/progress-indicator/guidelines/); [Progress indicator — specifications #color](https://carbondesignsystem.com/building-blocks/core/components/progress-indicator/specifications/#color); S43.
- Denetim: `dashboard/tests/e2e/moduller.spec.ts` "the progress indicator shows stages where they fit and one line where they do not"; `tests/test_modul_ilerleme.py` (renk rolleri, Carbon ikonlarıyla bayt eşliği).
- Durum: uyuyor (KB-2 kapandı 2026-10-20: `ol.asamalar`, Carbon `ProgressStep`'in `CheckmarkOutline` / `Incomplete` / `CircleDash` ikonları; segment adımları ve "Son N durak" kalktı).

**M2.5 — İlerleme göstergesinin adımları aşamalardır, segmentler değil: `meta.milestones` segmentleri 3–7 aşamaya gruplar; aşama adı 1–2 sözcük, en çok 16 karakter ve cümle düzenindedir.**
- Neden: Yayındaki modüllerde 15–18 segment var. Hesap: 18 adım × 1,75rem + 17 çizgi × 1,25rem ≈ 52,75rem (844 px); 28 segmentli ölçüm örneğinde şerit 1324 px ölçüldü. Okur sonunu göremez. Aşama (Keşfet, Öğren, Uygula…) okurun anlayabileceği bir yerdir (İ2).
- Dayanak: [Progress indicator — guidelines #when-to-use](https://carbondesignsystem.com/building-blocks/core/components/progress-indicator/guidelines/#when-to-use) (≥ 3 adımlı doğrusal süreç); [Progress indicator — specifications #typography](https://carbondesignsystem.com/building-blocks/core/components/progress-indicator/specifications/#typography) (etiket en çok 16 karakter, cümle düzeni); [Progress indicator — specifications #structure](https://carbondesignsystem.com/building-blocks/core/components/progress-indicator/specifications/#structure) (adım en az 8rem; üst sınır 7 buradan türer, §7 KS-6); İ2; İ3.
- Denetim: `tests/test_mcp_derleme.py` (`derleme.asama_hatalari`: 3–7 aşama, ilk segmentte başlar, sıra, ad ≤ 16 karakter ve ≤ 2 sözcük); aşamasız modül geçerlidir ve gösterge yalnız konum metnidir.
- Durum: uyuyor (KB-2 kapandı 2026-10-20). Yayındaki üç modül aşama taşımıyor; yeniden derlenene dek gösterge onlarda yalnız "Bölüm n / N" metnidir.

**M2.6 — ProgressBar, sefer haritası, avatar ve "Son N durak" hedef metni TEDY modüllerinde yoktur; isteğe bağlı tempo diski kalabilir ama M5.3, M5.6 ve M2.11'e uyar.**
- Neden: Carbon kullanıcı eylemiyle belirlenen ilerlemede ProgressBar kullanmaz. Sefer haritası ikinci bir ilerleme göstergesidir (İ1) ve ödül çerçevesi taşır (S43).
- Dayanak: [Progress bar — guidelines #when-not-to-use](https://carbondesignsystem.com/building-blocks/core/components/progress-bar/guidelines/#when-not-to-use); S43; anayasa §9.
- Denetim: `tests/test_modul_rekabet_cercevesi.py::test_sablonda_rekabet_cercevesi_ve_sefer_haritasi_yok` (şablonda `.quest-map`, `#railGoal`, `progress`/`role="progressbar"` sayısı 0); `meta.quest` şema hatasıdır (`derleme.sema_dogrula`); G-WELLBEING arayüz metnindeki (M2.7) sefer haritası ve "Son N durak" metninde FAIL.
- Durum: uyuyor (KB-21 kapandı 2026-10-23, `0388324`: sefer haritası kalktı; "Son N durak" metni KB-2 ile kalkmıştı).

**M2.7 — Rozet Carbon'daki anlamıyla yalnız bir sayaçtır; ödül rozeti, XP, seri, puan ve kutlama yoktur; arayüz metninde "Yarışma", "Meydan oku" gibi rekabet ya da ödül çerçevesi yoktur.**
- Neden: Dışsal ödül ve rekabet okurun dikkatini görevden ödüle taşır (anayasa §9, İ6). `rewards` iç sayıdır; `rewards.badges` hiç çizilmez.
- Dayanak: [Status indicators #badge-indicator](https://carbondesignsystem.com/building-blocks/core/patterns/status-indicators/#badge-indicator); S43; anayasa §9.
- Denetim: G-FLOW (seri sayacında FAIL); G-WELLBEING (`validate_module._arayuz_metni`): arayüz metninde "Yarışma" ve çekimleri, yalın "Yarış", "Meydan oku(ma)", turnuva, düello, liderlik / skor / sıralama tablosu, sefer haritası ve "Son N durak" FAIL; `derleme.odul_hatalari` (`rewards` isteğe bağlı; `badges` ve tanımsız alan şema hatası); `test_pano_talimatname_borclari.py:600` (S43); `tests/test_modul_rekabet_cercevesi.py`.
- Sınır (1.3, 1.3.1): "arayüz metni" şablonun kromu (MODULE_DATA dışı; yorum, atıf altbilgisi ve JSON varlık bloğu çıkarılmış) ve MODULE_DATA'nın arayüz alanlarıdır: `title` (modül, bölüm, aşama, görsel ve simülasyon adları), `kicker`, `instructions`, `selfAssess`, `interactiveLabel` (sayı doğrusu tutamacı) ve etiket dizileri — `bins` (sınıflandırmanın kutu düğmeleri), `params` (simülasyon kaydırıcılarının etiketleri), `columns` (tablo sütun başlıkları). İçerik etiketleri anlatıdır, taranmaz: grafik verisinin, sayı doğrusu noktasının, sıralanan ya da eşlenen öğenin, kavram haritası düğümünün, zaman çizelgesi olayının adı; seçenekler (`options`, `predict.options`) ve anahtar terimler. Gövde anlatısı (`body`, `stem`, `explanation`, `recap` …) ve yazar katmanı (`verification`, `grounding`, `frame_source`, `curriculum`) taranmaz: "bir yarışma düzenlendi" ya da Osmanlı'nın "sefer haritası" bir tarih anlatısıdır, çerçeve değil. Tarama adları bilir; listede olmayan bir eş anlamlıyla kurulmuş çerçeveyi kaçırabilir — denetçi bunu §8.3'te gözle okur.
- Durum: uyuyor (KB-21 kapandı 2026-10-23, `0388324`: soru seti "Alıştırma", zor soru seçeneği "Daha zor bir soru" / "Daha zor bir cümle", panonun mod etiketi QUIZ → "Alıştırma"; `rewards` yoksa motor kendi iç sayısını kullanır).

**M2.8 — Etiketler Carbon Tag kurallarına uyar: salt okunur etiket kategoridir, operational etiket açar, durum ikon + metinle söylenir; boy telefonda lg (32 px), masaüstünde md (24 px); tıklanan etiketin vuruş alanı her boyda dolguyla ≥ 44 px'e genişletilir.**
- Neden: Bir etiketin tıklanıp tıklanmadığı biçiminden okunur. Ders bir etiket değildir. Boy seçimi kanunun kararıdır: Carbon md'yi varsayılan, lg'yi sayfanın odağında sayar. Carbon Tag lg yalnız 32 px'tir, M5.3'ün tabanının altında. Kazanım ayrıntısını operational etiketle açmak TEDY'nin kullanımıdır; Carbon operational etiketi taşan etiketleri popover, modal ya da ayrıntı görünümünde göstermek için verir.
- Dayanak: [Tag — guidelines #when-to-use](https://carbondesignsystem.com/building-blocks/core/components/tag/guidelines/#when-to-use); [Tag — guidelines #clickable-areas](https://carbondesignsystem.com/building-blocks/core/components/tag/guidelines/#clickable-areas); [Tag — guidelines #operational-tag](https://carbondesignsystem.com/building-blocks/core/components/tag/guidelines/#operational-tag); [Tag — guidelines #sizing](https://carbondesignsystem.com/building-blocks/core/components/tag/guidelines/#sizing); [Tag — specifications #size](https://carbondesignsystem.com/building-blocks/core/components/tag/specifications/#size); [Tag — specifications #structure](https://carbondesignsystem.com/building-blocks/core/components/tag/specifications/#structure); [Tag — specifications #typography](https://carbondesignsystem.com/building-blocks/core/components/tag/specifications/#typography); [Status indicators #icon-indicator](https://carbondesignsystem.com/building-blocks/core/patterns/status-indicators/#icon-indicator); talimatname §4.4.
- Denetim: `moduller.spec.ts:463` (kazanım etiketi ve penceresi); kurulacak: KB-4 (etiket vuruş alanı ölçümü).
- Durum: uyuyor (ModulBasligi); vuruş alanı ölçülmedi (`Modules.scss:194-198` ±8 px `::after`); modül içinde etiket bileşeni yok.

**M2.9 — Başlık ağırlığı token'dan gelir; ağırlık yalnız 300, 400 ve 600'dür ve punto Carbon tip ölçeğindedir (talimatname [3.3-1], §3.3); kapsayıcı içinde akışkan başlık yoktur; ad başlıkları başlık düzeninde (`basliga`), etiket, düğme ve cümle başlıkları cümle düzenindedir.**
- Neden: Aynı token iki ağırlıkta yaşamaz (S44). Carbon akışkan başlığı kapsayıcı içinde istemez; şablon 560 px altında başlıkları elle küçültüyor.
- Dayanak: S44; S38 (adlı sapma, §7 KS-2); [Typography — type sets #fluid-heading-styles](https://carbondesignsystem.com/building-blocks/foundations/typography/type-sets/#fluid-heading-styles); [Content #content-foundations](https://carbondesignsystem.com/building-blocks/foundations/content/#content-foundations).
- Denetim: `tests/test_modul_baslik_duzeni.py`; `test_pano_talimatname_borclari.py` (B70, S38); kurulacak: KB-14 (elle akışkan ölçek yok).
- Durum: borç KB-14 (`--fs-display` / `--fs-h-seg` 353, 990; `.topbar__title` 1,5rem / 600, 447, yalnız tek başına açılışta); 500/700 ağırlık ve ölçek dışı punto borç KB-47.

**M2.10 — Bölüm değişiminde giriş animasyonu yoktur; hareket yalnız okurun eylemine cevap verir (geri bildirim, tanım balonunun açılması), productive easing ile ve en çok `$duration-moderate-02` (240 ms); azaltılmış harekette hiç hareket yoktur.**
- Neden: Panoda Bugün'de de giriş animasyonu yok. Her bölümde canlanan sahne okurun başlatmadığı bir uyarandır (İ6). Carbon yeni sayfa açılışında ve bildirim kutusunun belirmesinde expressive hareket önerir; kanun bundan bilerek ayrılır (KS-10).
- Dayanak: [Motion — overview #productive-motion](https://carbondesignsystem.com/building-blocks/foundations/motion/overview/#productive-motion); [Motion — overview #duration-tokens](https://carbondesignsystem.com/building-blocks/foundations/motion/overview/#duration-tokens); [Motion — overview #adaptive-interface-motion-design](https://carbondesignsystem.com/building-blocks/foundations/motion/overview/#adaptive-interface-motion-design); KS-10; talimatname P7, S26, [3.6-2].
- Denetim: `gorunum-kipleri.spec.ts` (azaltılmış harekette hiçbir şey canlanmaz; modül rotası eklenince, KB-33); kurulacak: KB-18 (şablonda `entrance-expressive` ve bölüm girişine bağlı `@keyframes` sayısı 0).
- Durum: borç KB-18 (`segIn` 619-622; `--ease-entrance` 370).

**M2.11 — İkon yalnız Carbon boylarındadır (16, 20, 24, 32 px); piktogram en az 48 px'tir.**
- Neden: Kesirli ikon boyu ikon ızgarasını bozar. 48 px altında piktogram ikon gibi okunur.
- Dayanak: [Icons — guidelines #sizing](https://carbondesignsystem.com/building-blocks/foundations/icons/guidelines/#sizing); [Icons — code #usage](https://carbondesignsystem.com/building-blocks/foundations/icons/code/#usage); [Pictograms — guidelines #sizing](https://carbondesignsystem.com/building-blocks/foundations/pictograms/guidelines/#sizing).
- Denetim: kurulacak: KB-32 (çerçevedeki her `svg use[href^="#ic-"]` çizilmiş boyu kümede; `#pic-` ≥ 48).
- Durum: borç KB-32 (`.fc-hint .cds-icon` 1,1rem 1012; `.btn .cds-icon` 1,15rem 642; segment başı piktogramı 32 px, talimatname §9.7).

**M2.12 — Her `:hover` kuralı `@media (any-hover: hover)` içindedir.**
- Neden: Dokunmatik ekranda koşulsuz hover yapışır ve seçili sanılır.
- Dayanak: talimatname S17, [3.2-3]; `test_pano_talimatname_borclari.py` (pano tarafı; pano borcu B3 kapandı).
- Denetim: kurulacak: KB-28 (aynı testin şablona uzatılması).
- Durum: borç KB-28 (13 koşulsuz `:hover`).

**M2.13 — Her tablanabilir denetimin odak göstergesi Carbon'unkidir: 2 px `$focus` (düğmede iç `$focus-inset` ile, bantta `$focus-inverse`); asla bastırılmaz, ders rengi almaz, zorunlu renk kipinde sistem rengine döner; odak modül açılınca ve geri yüklenince taşınmaz, yalnız okur ilerleyince yeni bölümün başlığına gider.**
- Neden: Klavyeyle gezen okur nerede olduğunu yalnız odaktan görür. Açılışta taşınan odak sayfayı okurun yerinden koparır.
- Dayanak: [Accessibility — developers #style-focus-indicators](https://carbondesignsystem.com/building-blocks/foundations/accessibility/developers/#style-focus-indicators) ("Never suppress the focus indicator altogether"); [Button — specifications #primary-button-interactive-state-color](https://carbondesignsystem.com/building-blocks/core/components/button/specifications/#primary-button-interactive-state-color); CLAUDE.md Modüller (`okurGecti`).
- Denetim: `moduller.spec.ts` (açılışta odak taşınmaz); kurulacak: KB-33 (`ibm-erisilebilirlik` ve `gorunum-kipleri` modül rotası).
- Durum: uyuyor (14 kural `outline:2px solid var(--cds-focus)`, bantta 2 kural `--cds-text-on-color` (464, 473): şablonda `--cds-focus-inverse` tanımlı değil, g10'da değer aynı (#ffffff) ama rol farklı; bant yalnız tek başına açılışta çizilir, düzeltme token bloklarına `--cds-focus-inverse` eklenip bu iki kuralda kullanılmasıdır; 531 yalnız `tabindex="-1"` programatik başlık hedefinde `outline:none`).

**M2.14 — Metin girişi, metin alanı, radyo ve onay kutusu Carbon form anatomisindedir: görünür etiket (yalnız `aria-label` değil), `$field` zemini ve `$border-strong` alt kenarı, boy lg 48 px, hata durumu ikon + metin (`$support-error`); işaretli durum `$interactive`, ders rengi değil.**
- Neden: Görünür etiketi olmayan alan ne istediğini yalnız ekran okuyucuya söyler. Ders rengiyle işaretlenen radyo her derste başka görünür (M1.6).
- Dayanak: [Text input — guidelines #main-elements](https://carbondesignsystem.com/building-blocks/core/components/text-input/guidelines/#main-elements) ("Text fields should always have a label"); [Form — guidelines #best-practices-for-labels](https://carbondesignsystem.com/building-blocks/core/components/form/guidelines/#best-practices-for-labels); [Text input — specifications #text-input-color](https://carbondesignsystem.com/building-blocks/core/components/text-input/specifications/#text-input-color).
- Denetim: kurulacak: KB-42 (her `input`/`textarea` bir görünür `label`'a bağlı; hesaplanmış zemin ve alt kenar token'a eşit; `accent-color` ders rolü değil).
- Durum: borç KB-42 (2212 `worked-input`, 2286 `se-textarea` yalnız `aria-label`; `.blank` 687 dolu ders rengi alt çizgi; radyo 1,375rem 791, 2343).

**M2.15 — Tablo Carbon veri tablosu dilindedir: başlık hücreleri `th scope`, her tabloda `caption`, satır boyu lg 48 px ve başlık satırı aynı boyda, zebra yok, sayı sütunu sağa yaslı ve tabular rakamlı, vurgu ders rengiyle değil kalınlıkla.**
- Neden: Başlıksız tablo ekran okuyucuda hücre yığınıdır. Zebra bilgi taşımayan ikinci bir desendir (talimatname §4.1, İ6); karşılaştırılan sayı hizalı okunur (talimatname P9). Ders rengiyle vurgulanan hücre bir durum gibi okunur.
- Dayanak: [Data table — specifications #rows](https://carbondesignsystem.com/building-blocks/core/components/data-table/specifications/#rows); [Data table — guidelines #header-and-row-height](https://carbondesignsystem.com/building-blocks/core/components/data-table/guidelines/#header-and-row-height) ("Do use the same row height for the table and header rows").
- Denetim: kurulacak: KB-43 (derleyici `caption`'sız tabloyu reddeder; e2e satır boyu ≥ 48 px; `.hi` ders rolü değil).
- Durum: borç KB-43 (`caption` isteğe bağlı 2594; `.viz-table .hi` 913; zebra `tbody tr:nth-child(odd)` 910); sayı sütunu uyuyor (`.num` 912).

## 4. Madde III — İçerik ve görsel

edupedia ve ted-mcp bir modüle kitap figürü, fotoğraf, üretken görsel, ses ve sayfa metni verebilir. Ölçüldü: yayındaki üç modül çerçeve pencerelerindeki yaklaşık 30 içerik figürünün 3'ünü kullanıyor ve tavanların %3–6'sını harcıyor. Bu madde "geniş yararlanma"yı sayıya bağlar.

**M3.1 — Görsel `edupedia_gorsel` zinciriyle gelir (kitap figürü → Pexels → MiniMax); ücretli medya kullanıcı onayı ister; yazar script çalıştırmaz.**
- Neden: Zincir ücretsiz ve lisanslı kaynağı önce dener; atıfı derleyici yazar. Vendor rehberi bugün yerel `fetch_figure.py`'ye yönlendiriyor.
- Dayanak: `server.py:160-161`; `gorsel.py:26-31`; `medya.py:114-131`; CLAUDE.md ted-mcp alt proje 4 ("medya onayını kullanıcıdan al").
- Denetim: G-ATTRIB (atıf altbilgide); kurulacak: KB-35 (vendor `SKILL.md:254-258` düzeltilir).
- Durum: uyuyor (rehber KB-35 2026-10-19'da kapandı).

**M3.2 — Çerçeve ders kitabıysa teach segmentlerinin en az %60'ı bir görsel taşır.**
- Neden: Ölçüldü: mat7 v4 %20, fen7 v3 %40, sb7 v3 %17. Kitap sayfasında görsel olan konu modülde metne iner.
- Dayanak: 3. ilke; ölçüm (içerik olanakları raporu §4).
- Denetim: kurulacak: KB-9 (G-GORSEL, oran altında FAIL).
- Durum: borç KB-9.

**M3.3 — Pencerede N içerik figürü varsa modül en az min(N, teach sayısı, 4) farklı kitap figürü kullanır.**
- Neden: doc 439 s.16-23'te etiketli 12 figür var, modül 2'sini kullanıyor; doc 346'da 10 içerik figürünün 1'i.
- Dayanak: 3. ilke; ölçüm.
- Denetim: kurulacak: KB-9 (G-GORSEL; içerik figürü sayısı run kaydındaki aday listesinden, KB-13).
- Durum: borç KB-9, KB-13.

**M3.4 — Kitap figürünün `page_no`'su çerçeve sayfalarındadır; değilse gerekçe `meta.assets[i].pencere_disi_gerekce` alanına en az 20 karakterle yazılır.**
- Neden: Ölçüldü: sb7 v3'ün tek görseli s.10'dan, kullanılmayan varlığı s.92'den; çerçeve s.40-48. Pencere dışı figür başka bir konuyu gösterir. Gerekçenin yeri tanımlı değilse kapı neye bakacağını bilemez.
- Dayanak: vendor `curriculum-integration.md` §3 (`page_no` sayfa bulucudur); ölçüm.
- Denetim: kurulacak: KB-9 (G-GORSEL; pencere dışı figürde alan boşsa FAIL).
- Durum: borç KB-9 (`gorsel.py:94-107` yalnız `document_id` ile daraltır, ilk sonucu alır; alan bugün okunmaz).

**M3.5 — Her modülde en az bir yazar görseli vardır (chart, table, labeled, flow, cards, numberline); kitap figürü yazar görselinin yerini almaz.**
- Neden: Ölçüldü: mat7 v1'de 3 teach'in 3'ü yazar SVG'si taşıyordu; kitap çerçevesine geçen v4'te 1/5'e düştü ve yazar görseli kalmadı.
- Dayanak: 3. ilke; ölçüm (mat7 v1 → v4). Vendor `curriculum-integration.md:128-134` ile `SKILL.md:254-258` yazar SVG'sini "yedek" sayar; bu cümleler kanuna göre düzeltilir (KB-35).
- Denetim: kurulacak: KB-9 (G-GORSEL).
- Durum: borç KB-9 (canlı üç modülün teach görselinde yazar görseli 0).

**M3.6 — Alt metni yazar yazar: 60–150 karakter, bitmiş cümle; "Bu fotoğraf / çizim / şema" ile başlamaz; içindeki özel adlar ve sayılar kitabın kendi metninde (figür altı yazısı ya da çerçeve sayfaları) geçer; süs görseli `alt=""` alır.**
- Neden: Ölçüldü: dört alt metnin dördü VLM altyazısının tam 200 karakterlik kesiği, sözcük ortasında bitiyor; biri KAAN'ı "F-35" diye adlandırıyor. "Çelişmez" ancak adlarla ve sayılarla ölçülebilir. Dayanak kitabın kendi metnidir, yapay zekânın betimi değil: Maarif'in `caption`'ı bir VLM betimidir (figür 4189: "…F-35…"), kitabın figür altı yazısı `nearby_text`'tir ("Görsel 1.1.1: Kaan"); 1.2'nin "figürün `caption`'ı" ifadesi tam o yanlış kaynağı dayanak yapıyordu (son inceleme, Kritik 1; 1.3'te düzeltildi).
- Dayanak: [Accessibility — developers #give-decorative-images-an-empty-alt-attribute](https://carbondesignsystem.com/building-blocks/foundations/accessibility/developers/#give-decorative-images-an-empty-alt-attribute); D4; G-VOICE.
- Denetim: derleyici, kapı raporundan önce: `derleme.varlik_alani_hatalari` (uzunluk, cümle sonu, yasak açılış — önündeki tırnak, ayraç ve tire açılışı gizlemez, metin NFC'ye getirilir —, G-VOICE) ve `varlik_zorunluluk_hatalari` (raster görselde `alt` zorunlu) şema hatasıdır; `edupedia_derle` `alt_metin.alt_metin_dayanagi` ile alt metindeki özel adları ve rakam dizilerini yalnız kitabın metninde arar: varlık kaydının `kitap_altyazisi`'nda (Maarif `nearby_text`), `etiket`'inde (ör. "Görsel 1.1.1") ve run'ın çerçeve sayfalarında. `betim` (Maarif VLM `caption`'ı, Pexels açıklaması, üretim istemi) dayanak değildir; yalnız betimde geçen ad dayanaksızdır. Geçmeyen varsa `alt_metin_dayanaksiz` döner, gerekçe `meta.assets[i].alt_gerekce`'deyse derleme uyarıyla (`uyarilar`) geçer. `kitap_altyazisi` taşımayan eski varlık kaydında dayanak sayfalar ve etikettir. Türkçede cümle başı büyük harf dil bilgisidir: cümle başındaki sözcük yalnız kesme işaretli ekli ya da tümü büyük kısaltmaysa sayılır. `tests/test_modul_gorsel_alanlari.py`, `tests/test_modul_alt_metin_dayanagi.py`.
- Bilinen gevşeklik ve sıkılık (1.3, belgelendi): ad kaynakta bir sözcüğün başında geçerse dayanaklı sayılır (önek eşleşmesi: "Kemal" ↔ "Kemalpaşa", ek ve bileşik ad serbest); bu, kaynaktaki daha uzun bir adın başını yanlışlıkla doğrulayabilir. Ayraç farkları ise tersine yanlış alarm verir: alt metindeki "F–35" (uzun tire) ya da "1-30" kaynaktaki "F-35" ya da "1.30" ile eşleşmez (yalnız kısa tire birleştirir; ondalıkta nokta ve virgül eşittir). İkisi de `alt_gerekce` ile aşılır: yazar nedeni yazar, derleme uyarıyla geçer.
- Durum: uyuyor (KB-10 kapandı 2026-10-23, `0388324`; dayanak 1.3'te kitabın metnine bağlandı: `edupedia_gorsel` Maarif `nearby_text`'ini `kitap_altyazisi` olarak ayrı saklar ve `kaynak_verisi`'nde `kitap_altyazisi`, `etiket`, `betim` diye ayrı döner; derleyici varlık kaydının 200 karakterlik VLM kesiğini kullanmaz).

**M3.7 — Bilgi taşıyan her raster figürün görünür altyazısı vardır: `figure` + `figcaption`, en çok 120 karakter, kitaptaki adıyla; süs görseli (`alt=""`) altyazı almaz.**
- Neden: Altyazı okura neye baktığını söyler ve atıf satırıyla figürü bağlar. SVG figürde zaten `figcaption` var; raster figürde yok.
- Dayanak: İ9 (aynı tür aynı kalıp); `module-template.html:2353-2355` (svgFigure).
- Karar (1.3, son inceleme Küçük 9): süs görseli okura bilgi vermediği için altyazı da almaz; `alt: ""` yazılmış varlıkta `baslik` şema hatasıdır ("görsel bilgi taşıyorsa alt metnini yaz, taşımıyorsa baslik'i sil") ve `figcaption` çizilmez. Atıf satırı adsız künyedir.
- Denetim: `derleme.varlik_alani_hatalari` ve `varlik_zorunluluk_hatalari` (`baslik` bilgi taşıyan raster görselde zorunlu, süs görselinde yasak, ≤ 120 karakter, tek satır, sayfa göndermesiz; iki varlık aynı adı taşımaz); `tests/test_modul_gorsel_alanlari.py::test_her_img_figure_ve_gorunur_figcaption_icinde` (derlenen modülün görselleri motorun kendi çizicisiyle çizilir: bilgi taşıyan her `img` (alt'ı dolu) bir `figure` ve dolu `figcaption` içinde; süs görselinin `img`'i (`alt=""`) altyazısızdır), `::test_sus_gorseli_baslik_istemez_ve_altyazi_cizilmez`; `dashboard/tests/e2e/modul-svg-metni.spec.ts` (altyazı görünür). Kitap figürünün etiketi altyazıda yoksa `edupedia_derle` uyarır.
- Durum: uyuyor (KB-11 kapandı 2026-10-23, `0388324`; süs görseli kararı 1.3).

**M3.8 — Atıf varlık başına tek satırdır ve figürün adını taşır; sayfa numarası yazmaz.**
- Neden: Bugün aynı MEB satırı iki kez yazılıyor ve satır hangi görsele ait olduğunu söylemiyor.
- Dayanak: G-ATTRIB; G-VOICE (`validate_module.py:2228-2243`).
- Denetim: G-ATTRIB (eksik atıf ve yinelenen satır FAIL), G-VOICE; `derleme.atiflar` satırı `baslik — atıf` biçiminde yazar; aynı varlık iki yuvada iki ayrı `baslik` taşıyamaz (şema hatası, 1.3) — bir varlığın tek adı ve tek satırı vardır; adlar NFC'de ve Türkçe küçültülerek karşılaştırılır; `tests/test_modul_gorsel_alanlari.py`.
- Durum: uyuyor (KB-12 kapandı 2026-10-23, `0388324`).

**M3.9 — Bütçe görseli az kullanmanın gerekçesi değildir.**
- Neden: Ölçüldü: `MODULE_DATA` 400 KB tavanının %5–6'sı, gömülü varlık 2,4 MB tavanının %3–6,5'i kullanılıyor. Altı figür yaklaşık 0,4–0,5 MB eder.
- Dayanak: `derleme.py:24-25`; ölçüm.
- Denetim: G-GORSEL'in raporu (KB-9) oran altında bütçe kullanımını da yazar.
- Durum: uyuyor (kural bir gerekçeyi yasaklar; ihlal M3.2'de sayılır).

**M3.10 — Piktogram yalnız sprite'taki anahtarlardandır; piktogram en az 48 px, daha küçük işaret ikondur (16/20/24/32); ödül piktogramı ve ikonu (`pic-trophy`, `ic-trophy`, `ic-star`) kullanılmaz.**
- Neden: Bilinmeyen anahtar sessizce `pic-education`'a düşer. Vendor örneklerindeki `ic-idea` ve `ic-flip` sprite'ta yok; `ic-trophy`'yi piktogram olarak yazdırıyorlar.
- Dayanak: [Pictograms — guidelines #sizing](https://carbondesignsystem.com/building-blocks/foundations/pictograms/guidelines/#sizing); [Pictograms — guidelines #productive-versus-expressive](https://carbondesignsystem.com/building-blocks/foundations/pictograms/guidelines/#productive-versus-expressive) (piktogram ikon yerine kullanılmaz); `module-template.html:1080` (sprite: 8 `pic-*`, 26 `ic-*`); S43.
- Denetim: kurulacak: KB-32 (derleyici bilinmeyen ve yasak anahtarı reddeder).
- Durum: borç KB-32 (`module-template.html:1542`, 3153 sessiz yedek; `keyTerms[].icon` piktogramı ikon boyunda çiziliyor: 554, 567, 1957, altın örnek 1258); KB-35 (`module-architecture.md:69, 151`).

**M3.11 — Altyapı sınırları kanun borcudur, kural değildir: yuva yalnız teach'te, yuva başına tek varlık, `FIGURE_MAX=6`, gizli figür aranmıyor, altyazı 200 karaktere kırpılıyor, figür seçimi sayfa penceresine bakmıyor.**
- Neden: Yazar bu sınırları kanunun izni sanmaz. M3.2–M3.7 bugün bu sınırlar yüzünden tutturulamayabilir; o durumda yazar eksikliği kapı raporunda bildirir.
- Dayanak: `derleme.py:470-476`; `kapsam.py:255, 525, 589-593`; `gorsel.py:94-107, 132-133`; `varliklar.py:124`.
- Denetim: KB-13'ün kapanış testleri.
- Durum: borç KB-13.

## 5. Madde IV — Tek tema, içeriğe özel stil yok

**M4.1 — Modül temayı yalnız panodan alır (`edupedia:appearance.theme`) ve koşulsuz uygular; modülde tema düğmesi, tema kaydı (`localStorage`, `edupedia:theme`), "öğrencinin seçimi > pano" önceliği ve kendi `prefers-color-scheme` kuralı yoktur.**
- Neden: Ölçüldü: akışta tema düğmesine basılınca çerçeve g100'e (#161616) geçiyor, pano g10'da kalıyor. Sayfanın ortasında koyu bir dikdörtgen organik bütünlüğü bozar. Opak köken yüzünden tercih yeniden yüklemede kalmaz (talimatname §9.4), ama oturum içinde düğmeyle geçiş panonun temasını ezer; kural bu yüzden kalıcılığa değil düğmenin varlığına bakar. Carbon modu ürün düzeyinde bir son kullanıcı ayarı sayar ve denetimini görünüm, profil ya da hesap alanına koyar.
- Dayanak: 4. ilke; [Color — guidelines #creating-a-mode-control](https://carbondesignsystem.com/building-blocks/foundations/color/guidelines/#creating-a-mode-control); S14 (2026-10-19'da bu yönde revize edildi, KB-34).
- Denetim: `dashboard/tests/e2e/moduller.spec.ts` "the module has no theme switch; the dashboard theme always wins"; `tests/test_mcp_gates_ek.py::test_tema_kaydi_yok_ve_kapidan_gecmez` (tema kaydı taşıyan modül G-BRIDGE'de düşer).
- Durum: uyuyor (KB-1 kapandı 2026-10-20: `#themeBtn`, `toggleTheme`, `THEME_STORE_KEY` ve öğrenci önceliği kalktı; `adoptHostTheme` yalnız g10 | g100 kabul eder).

**M4.2 — Pano bir gün koyu mod eklerse bu panonun Profil'deki ayarıdır; modül onu `edupedia:appearance` ile devralır ve değişen tek değer `DASHBOARD_THEME` olur.**
- Neden: Tema kararı tek yerde alınır. Pano bugün yalnız g10'dur (`moduleBridge.ts:67`, `main.tsx:11`).
- Dayanak: [Color — guidelines #creating-a-mode-control](https://carbondesignsystem.com/building-blocks/foundations/color/guidelines/#creating-a-mode-control); talimatname §9.4, S14.
- Denetim: `tests/test_tedy_tasarim_tutarliligi.py:73-80` (g10 dört yerde aynı); `moduller.spec.ts:326` (tema devri).
- Durum: uyuyor.

**M4.3 — g100 token blokları yalnız otoriteden üretilen token eşlemesi olarak durur; bileşene özel `[data-theme="g100"]` kuralı ve ölü `white` teması yoktur.**
- Neden: Bileşen düzeyinde koyu tema kuralı içeriğe özel bir koyu moddur. Token eşlemesi ise panonun bir gün geçeceği hedefin hazır hâlidir.
- Dayanak: 4. ilke; [Themes — overview #theming-applied](https://carbondesignsystem.com/building-blocks/foundations/themes/overview/#theming-applied) (her tema aynı token rollerini taşır, yalnız değer değişir); S19'un kaskad dersi (koyu blok ancak üç tema bloğunda bildirilen token'larla doğru çizer).
- Denetim: kurulacak: KB-22 (şablonda `[data-theme=...]` seçicisi yalnız `:root` token bloklarında; `white` bloğu yok; G-TOKEN g10 ve g100 ile PASS); `test_tedy_tasarim_tutarliligi.py`.
- Durum: borç KB-22 (`.feedback` 664; `--def-pop-rule` 586-587 elle hex; `white` 258-290).

**M4.4 — Azaltılmış hareket ve zorunlu renk sistem erişilebilirlik kipleridir, modüle özel mod değildir; modül ikisini de panoyla aynı ölçütle izler.**
- Neden: Okurun işletim sisteminde açtığı kip panoda geçerliyse modülde de geçerlidir. Şablonda `forced-colors` kuralı yok; panoda var (`ted-theme.scss:261-277`).
- Dayanak: anayasa D2 (erişilebilirlik tabanı); [Motion — overview #adaptive-interface-motion-design](https://carbondesignsystem.com/building-blocks/foundations/motion/overview/#adaptive-interface-motion-design) ("Always provide alternatives for interface state transitions"); `gorunum-kipleri.spec.ts`.
- Denetim (KB-23, KB-33): `prefers-reduced-motion: reduce` altında çerçevedeki her öğenin hesaplanmış `animation-name` değeri `none` ve `transition-duration` değeri `0s`; `forced-colors: active` altında `.stage`, `.opt`, `.callout`, `.feedback`, `.topbar__status` ve kartlar hesaplanmış `border-width ≥ 1px` taşır, odaklanan her denetimin `outline-style` değeri `none` değildir.
- Durum: azaltılmış hareket uyuyor (1076, 1621); zorunlu renk borç KB-23.

**M4.5 — `MODULE_DATA` renk, tema, CSS, font, `meta.accent` ve satır içi stil taşımaz.**
- Neden: Yazar bir rengi seçebilirse her modül biraz farklı görünür. Ders rengi `meta.subject`'ten tek otoriteyle türetilir.
- Dayanak: 4. ilke; talimatname §9.2 aynı yasağı `meta.accent` dahil yazar (KB-34 kapandı); vendor metni KB-35 ile düzeltildi.
- Denetim: derleyici şeması (`derleme.py:381-386` hex'i reddeder); kurulacak: KB-24 (`meta.accent` hiç kabul edilmez).
- Durum: borç KB-24 (`meta.accent` bir aile adıyla hâlâ kabul ediliyor; vendor `module-architecture.md:45, 315` ve `SKILL.md:272-281` onu yazdırıyor).

**M4.6 — Derse özel tipografi ya da düzen yoktur; ders yalnız M1.5'in çapalarında renk olarak görünür.**
- Neden: Bir dersin başka bir yazı tipiyle çizilmesi o dersin modülünü başka bir ürüne çevirir.
- Dayanak: 4. ilke; İ9.
- Denetim: kurulacak: KB-27 (şablonda `data-subject` seçicisi yok; vendor `subject-packs.md:30-32` düzeltilir).
- Durum: borç KB-27.

**M4.7 — Her segment türü yalnız kendi bileşen sözlüğüyle çizilir; bir modül ya da ders bir bileşenin görünüşünü değiştiremez; yazar SVG'si ve grafik verisi ham renk taşımaz; geride kalan öğe opaklıkla değil renkle söner.**
- Neden: Kullanıcı rengi bugün grafikte `fill`'e ve lejantta satır içi stile geçiyor; G-SVG ham hex'e yalnız uyarı veriyor. Bir bileşenin iki tanımı da görünüşü bozuyor: ölçüldü, `.card` iki kez tanımlı ve kavram kartında harfler kırılıyor ("Sıv/ı"). Opaklık kontrastı token dışına düşürür (panoda geçmiş öğeler opaklıkla 3,03:1'e inmişti).
- Dayanak: 4. ilke; D1; S19; talimatname S5 (satır içi stil yalnız çalışma anında hesaplanan değer için); CLAUDE.md "One column, audited".
- Denetim: kurulacak: KB-25 (G-SVG ham hex FAIL; `color` alanı şema hatası); KB-26 (motor statik değeri satır içi yazmaz; çalışma anında hesaplanan geometri yalnız `left`, `top` ya da CSS özel özelliğiyle geçer, `style="--x:…"`; `MODULE_DATA` kaynaklı hiçbir satır içi stil yoktur); KB-8 (her sınıf seçicisi tek blokta tanımlı); KB-41 (`opacity` / `fill-opacity` yalnız geçiş anahtar karelerinde).
- Durum: borç KB-8 (681, 947), KB-25 (2391, 2407, 2417; `validate_module.py:978`), KB-26 (satır içi stil listesi, `sablon.py:47`, 50, `derleme.py:562`), KB-41 (445, 554, 574).

## 6. Madde V — Telefondan 4K'ya

### 6.1 Referans genişlikler

Ölçüldü (pano ve talimatname raporu §2). Modül çerçevesi panonun sütunundan dolguyu çıkarır; çerçevenin içinde kök font panoyla aynıdır.

| Ekran (px) | Pano kökü (px) | Çerçeve genişliği (px) | Çerçeve (rem) | Not |
|---|---|---|---|---|
| 320 | 16 | 272 (KB-31 sonrası 288) | 17 (18) | kenar durum: WCAG 1.4.10 yeniden akış tabanı |
| 360 | 16 | 312 | 19,5 | alt çubuk, yan gezinme gizli |
| 390 | 16 | 342 | 21,4 | alt çubuk |
| 768 | 16 | 720 | 45 | |
| 1024 | 16 | 912 | 57 | |
| 1440 | 16 | 912 | 57 | yan gezinme 256 |
| 1920 | 16 | 912 | 57 | |
| 2560 | 21,33 | 1216 | 57 | |
| 3840 | 32 | 1824 | 57 | ekran-4k eşliği: 2 × 912 |

- Telefon satırları bugünün ölçümüdür ve KB-31'i içerir. KB-31 kapanınca çerçeve 360'ta 328, 390'da 358, 320'de 288 px olur (hesap, doğrulanmadı).
- Kenar durum 320 CSS px görünüm alanıdır: çerçeve bugün 272 px, KB-31'den sonra 288 px. Her responsive madde bu iki değerden geçerli olanda da ölçülür.
- Kanunda bir genişlik "ekran N" ya da "çerçeve N @ kök K" diye yazılır. Şablon ölçümlerinin benzetim değerleri şöyle karşılanır: çerçeve 960 @ 16 ≈ ekran 1024–1920 (çerçeve 912); çerçeve 1280 @ 21,33 ≈ ekran 2560 (1216); çerçeve 1920 @ 32 ≈ ekran 3840 (1824).

**M5.1 — Her responsive madde §6.1'deki genişliklerde ve kenar durumda ölçülür; bir genişlikte geçmeyen madde geçmemiş sayılır.**
- Neden: Tek genişlikte doğrulanan düzen başka genişlikte bozuluyor. Ölçüldü: çerçeve 288'de 10 px taşma, çerçeve 358'de 6,5 px grafik metni, çerçeve 1920 @ 32'de 104 karakterlik satır.
- Dayanak: talimatname §12; `ekran-4k.spec.ts`.
- Denetim: kurulacak: KB-33 (modül rotası e2e kapılarına). Ölçümler §6.1'in çerçeve ve kök sütununa göre yapılır; ekran genişliği yalnız satırı seçer.
- Durum: borç KB-33.

**M5.2 — Hiçbir genişlikte sayfa ya da çerçeve yatay kaymaz; iç kayan bölge yalnız tablo ve geniş formüldür, odaklanabilir ve adlıdır.**
- Neden: Yatay kayan sayfa telefonda içeriğin bir kısmını gizler. Kaydırılan bölge klavyeyle de kaydırılabilir.
- Dayanak: D2; talimatname §5.8 (yatay kaydırma yalnız tablo ve formülde, adlı ve odaklanabilir); `tasarim-denetimi.spec.ts` (yatay kaydırma yok); CLAUDE.md "One column, audited" (panonun haftalık tablosu odaklanabilir, adlı bir kayan bölgedir).
- Denetim: kurulacak: KB-7 (kenar durumdan 3840'a `scrollWidth ≤ clientWidth`; `.viz-table-wrap` `tabindex="0"` ve `aria-label`).
- Durum: borç KB-7 (`cards--2` 945, çerçeve 288'de 10 px; `module-template.html:2594` tabindex yok).

**M5.3 — Dokunmatik girişte (`pointer: coarse`) ve çerçeve md altındayken dokunulan her denetim en az 44 × 44 px'tir; standart 48 px'tir.**
- Neden: Ölçüldü (ekran 390): araç düğmeleri 40, adım düğmesi 28, kavram çipi 30, sesli okuma 36, tempo kapatma 22, sayı doğrusu tutamacı 8–11, simülasyon kaydırıcısı 16, breadcrumb 62 × 18 px. Kaydırıcı Carbon Slider anatomisindedir: görünür etiket, sayısal değer alanı, tutamaç dokunma kutusu ≥ 44 px, dolgu `$interactive`.
- Dayanak: S18 (KS-5), talimatname [3.8-3] (ince işaretçide alt sınır WCAG 2.5.8'in 24 × 24 px'i); [Icons — guidelines #touch-targets](https://carbondesignsystem.com/building-blocks/foundations/icons/guidelines/#touch-targets); [Button — specifications #size](https://carbondesignsystem.com/building-blocks/core/components/button/specifications/#size); [Slider — guidelines #default-slider-anatomy](https://carbondesignsystem.com/building-blocks/core/components/slider/guidelines/#default-slider-anatomy).
- Denetim (KB-4): `d3b-dokunma.spec.ts`'e modül rotası ve çerçeve içi. Her etkileşimli öğe için kenar kutusu ≥ 44 × 44; ya da öğenin merkezine oturtulmuş 44 × 44 karenin dört köşesinde ve merkezinde `elementFromPoint` aynı öğeyi (ya da torununu) döndürür (`::after` ile büyütülmüş vuruş alanı böyle ölçülür). Ekran 390 ve kenar durumda, çerçeve içi dahil.
- Durum: borç KB-4 (547-555, 2509, 841; `ModulBasligi.tsx:45-48`). Adım düğmesi KB-2 ile, araç düğmeleri, tempo kapatma ve "Oku" KB-44 ile 48 px (2026-10-24).

**M5.4 — İlerleme göstergesinde geçerli konum her genişlikte yatay kaydırma olmadan görünür; "Bölüm n / N" metni her zaman DOM'da ve görünürdür; aşama etiketli gösterge yalnız çerçeve md ve üstündeyken (≥ 42rem) ve göstergenin kendi kabı ≥ aşama sayısı × 8rem iken çizilir, aksi hâlde aşama etiketleri yerine tek satır metin gösterilir ("Aşama 2/5 · Uygula · Bölüm 7/18"); metin konumu söyler, toplamı öne çıkarmaz; tıklanabilir her adım dokunmada ≥ 44 px'tir.**
- Neden: Ölçüldü: çerçeve 358'de stepper 1324 px'lik şeridin 332 px'ini gösteriyor, 11. ve 21. adım görünür alanın dışında; geçerli adıma kaydırma kodu yok. Çerçeve eşiği tek başına yetmez: ölçüldü, 7 aşama 42rem ve 45rem'lik (ekran 768) kapta taşıyor; 5 aşama 42rem'de sığıyor. Bugün göstergenin kabı masaüstünde 34,2rem (ekran 1920: 547 px; ekran 3840: 1098 px).
- Eşik çerçeveye ve göstergenin kabına (`container-name:ilerleme`) birlikte uygulanır: 3 aşama 24rem, 5 aşama 40rem, 7 aşama 56rem ister. 7 aşamanın 57rem'lik çerçevede sığması için göstergeye çerçevenin bütün genişliği verilir: araçlar ve bölüm metni ayrı satıra iner, kabın yan dolgusu toplamda en çok 1rem olur. Hiçbir genişlikte göstergenin `scrollWidth`'i `clientWidth`'ini aşmaz.
- Metnin en belirgin öğesi geçerli aşamanın adıdır (İ3): `n` ve aşama adı birincil ağırlıkta; "/ N" ve "Bölüm 7/18" ikincil tip ve renkte (`label-01`, `$text-secondary`). Hiçbir genişlikte toplam sayı aşama adından büyük ya da ağır çizilmez.
- Metin kırpılmaz, gizlenmez, yatay kaydırmaz. Tek satır şunlarla sağlanır: aşama adı ≤ 16 karakter (M2.5), ikincil kısım `label-01`, kap yan dolgusu ≤ 1rem. Ölçüldü: "Aşama 5/7 · Değerlendir · Bölüm 17/18" 18 px'te 322, 16 px'te 287 px; çerçeve 312'de bugünkü kart içi 262 px. Yalnız kenar durumda sığmazsa metin ' · ' ayırıcısından ikinci satıra sarılır; iki satırı geçmez.
- Tıklanabilir adımın vuruş kutusu KS-11'e göre ≥ 48 px'tir; tamamlanmamış adım tıklanamaz.
- Dayanak: S43 (az adımda düz metin yedeği); İ3; [Progress indicator — guidelines #when-to-use](https://carbondesignsystem.com/building-blocks/core/components/progress-indicator/guidelines/#when-to-use); [Progress indicator — specifications #structure](https://carbondesignsystem.com/building-blocks/core/components/progress-indicator/specifications/#structure) (adım en az 8rem); [Progress indicator — specifications #typography](https://carbondesignsystem.com/building-blocks/core/components/progress-indicator/specifications/#typography); S18. Bileşen kararı (Carbon `ProgressIndicator`, `vertical`, özel çizim ya da metin) borca bırakılır: Carbon MCP'de sığmayan gösterge için kural yok.
- Denetim: kurulacak: KB-2 (3, 5 ve 7 aşamalı sabit modülle çerçeve 272/288, 312, 342, 720, 912, 1216 @ 21,33 ve 1824 @ 32'de `ul.scrollWidth ≤ clientWidth`, geçerli adımın kutusu görünür alanda, metin görünür ve ≤ 2 satır, toplam sayının `font-size` ve `font-weight` değeri aşama adınınkini aşmaz, adım vuruş kutusu ≥ 44).
- Durum: uyuyor (KB-2 kapandı 2026-10-20; ölçüm ekran 390, 1440 ve 3840'ta). Eşikler `.topbar` kapsayıcısında: 3–5 aşama 42rem, 6 aşama 48rem, 7 aşama 56rem.

**M5.5 — Düzyazı bloklarının (`p`, `li`, `.lead`, geri bildirim metni) ölçüsü satırda en çok 80 karakterdir; bunu `max-width: 36rem` (gövde 1,125rem'de 32em) sağlar; ölçü `ch` birimiyle verilmez; figür, tablo ve grafik sütunu doldurabilir.**
- Neden: Ölçüldü: çerçeve 960 @ 16 ve çerçeve 1920 @ 32 benzetiminde paragraf satırı 104 karakter. Uzun satırda göz sonraki satırın başını kaybeder. `ch` Plex Sans'ta "0" genişliğidir; Türkçe düzyazının ortalama karakterinden geniş olduğundan satır kapasitesini yaklaşık %40 fazla gösterir. Ölçüldü (18 px Plex Sans, Türkçe paragraf, boşluk dahil, son satır hariç, satırların en çoğu): 36rem çerçeve 912 @ 16, 1216 @ 21,33 ve 1824 @ 32'de 74 karakter; 38rem 76–82; 40rem 83–84; 80ch 106–114.
- Dayanak: WCAG 1.4.8 (Carbon MCP'de satır uzunluğu kuralı bulunamadı); vendor `carbon-excellence.md:76-79` (gövde 8–10 sütun ölçüsü).
- Denetim: kurulacak: KB-29 (sabit Türkçe başvuru paragrafı §6.1 genişliklerinde çizilir; satır başına karakter Range dikdörtgenleriyle, boşluk dahil ve son satır hariç sayılır; her satır ≤ 80, ortalama ≤ 75).
- Durum: borç KB-29 (`module-template.html:416`, 1045; ölçü sınırı yok).

**M5.6 — SVG metni her genişlikte ekranda en az 12 px çizilir.**
- Neden: Ölçüldü: çerçeve 288'de en küçük grafik metni 4,9 px, çerçeve 358'de 6,5 px. viewBox sabit 480 birim, metin 11 birim.
- Dayanak: D2; [Accessibility — color #color-contrast](https://carbondesignsystem.com/building-blocks/foundations/accessibility/color/#color-contrast) (MCP: #use-of-color-and-color-blindness; Carbon UI bileşeninin durum ve sınırı için komşu renge 3:1 ister; yazı boyu kuralı yok, 12 px kanunun kararı).
- Denetim (KB-5): çerçevedeki her görünür `svg text` / `tspan` için `parseFloat(getComputedStyle(t).fontSize) × t.getScreenCTM().a ≥ 12`, §6.1 genişliklerinde ve kenar durumda. `getBoundingClientRect().height` ölçüt değildir: ölçüldü, kutu yüksekliği çizilen yazı boyundan yaklaşık %36 büyüktür (viewBox 480, metin 11: çerçeve 288'de kutu 9, gerçek 6,6 px). Kuruldu: `dashboard/tests/e2e/modul-svg-metni.spec.ts` (çerçeve 272, 288, 342 ve 358 doğrudan, ekran 320, 390, 1440, 2560 ve 3840 panoda — kök 21,33 ve 32 px —, her bölüm; bir SVG'deki hiçbir iki metin kutusu kesişmez; çekirge, "Ardışık Noktalar" (−10…10, −5…5 harfli nokta) ve "Dar Aralık" (−3…3) doğrularında her noktanın değeri ve adı yazılı; daralan pencerede yeniden kurulum ve okurun değeri), `tests/test_modul_svg_metni.py` (çiziciler 180–800 px kutuda, ölçülmüş genişlikle çakışmasızlık, nokta değerleri). Yazar SVG'si (KB-48): `derleme.yazar_svg_hatalari` (`edupedia_derle` `sema_hatasi`), `tests/test_modul_yazar_svg_metni.py`; e2e altın örneklerin yazar figürleri çerçeve 272, 288, 342 ve 358'de (`modul-svg-metni.spec.ts`, "author SVG").
- Durum: şablonun çizdiği SVG uyuyor (KB-5 kapandı 2026-10-23, `9107214`; 1.3'te ölçüyle düzeltildi): viewBox kutunun kök boyuna indirgenmiş genişliğine kurulur (en çok 480), metin 12 birimdir. Etiket genişliği tahminle değil, IBM Plex Sans'ın ölçülmüş glif genişlikleriyle (`vizEmTablosu`; rakam 0,6 em, eksi 0,4 em, 600 ağırlık +%4) hesaplanır. Sayı doğrusunda etiket yalnız komşusuyla gerçekten çakışırsa seyreltilir: düzenli adım (1, 2, 4, 5, 10 …), sıfır ve iki uç öncelikli; masaüstünde −10…10'un 21 etiketi de yazılır. `points` değerine denk gelen tik her genişlikte etiketlidir; komşusuyla çakışırsa bir alt satıra iner ve gerektiği kadar satır açılır (`vizSatirAta`; SVG yüksekliği satır sayısıyla büyür) — noktanın değeri hiçbir genişlikte okunmaz kalmaz ve hiçbir etiket ötekinin üstüne yazılmaz (mat7 çekirge doğrusu: −5, −3, −1, 1, 3, 5, 7; ikinci incelemenin ölçümü: −10…10'da her tam sayı −5…5 nokta, çerçeve 288'de "−3 ↔ −2"; −3…3'te her tam sayı, çerçeve 272'de "−1 ↔ 0" — eski iki satırlı kural üçüncü komşuyu ilk satırın üstüne yazıyordu). Noktaların harf adları (`points[].label`) aynı kuralla üst satırlara dağılır. Tikler seyreltilmez, yalnız etiketler. Çubuk grafik etiketleri dikey eksende (en çok iki satır) sığıyorsa dikey kalır; sığmazsa yataylaşır — bu genişliğe değil etiketin ölçülen boyuna bağlıdır, masaüstünde kısa etiketli grafik dikeydir. Carbon dayanağı: çubuk grafik iki yönü de tanır ([Simple charts #bar-simple](https://carbondesignsystem.com/data-visualization/simple-charts/#bar-simple): "Bar charts use vertical or horizontal data markers to compare individual values"; Jina Reader ile okundu 2026-10-23) ama hangi yönün ne zaman seçileceğini söylemez; sığma ölçütü kanunun kararıdır. Eksen artımı veri yüzünden değiştirilmez ([Axes and labels #consistent-increments](https://carbondesignsystem.com/data-visualization/axes-and-labels/#consistent-increments)): seyreltme yalnız etiketi düşürür. Yazar SVG'si uyuyor (KB-48 kapandı 2026-10-24, `30258d7`): viewBox yazarındır ve şablon onu kutuya göre kuramaz, bu yüzden yazar SVG'si metin taşımaz. Derleyici `MODULE_DATA`'nın her dizgesinde — `visual.kind:"svg"`'nin `ref`'i, etiketli şemanın `base`'i, `hotspot`'un `svg`'si, gövdeye gömülü SVG — `<text>`, `<tspan>`, `<textPath>` ve `<foreignObject>`'i reddeder ve yazarı etiketli şemanın `labels`'ına (iğne numarası ≥ 12 px, ad HTML listede; köşe harfi `labels[].n`) ya da gövde metnine ve altyazıya yönlendirir. Şablonun metni ölçmesi (yol b) seçilmedi: 12 px'e büyüyen metin yazarın şekilleriyle çakışır ve viewBox'tan taşar (altın su döngüsünde çerçeve 288'de "buharlaşma" ~163 birimle buluta, "toplanma" 533'e uzanır; viewBox 480). `title` ve `desc` çizilmez, serbesttir.

**M5.7 — Çerçevenin içinde, akış yerleşiminde `vh`, `dvh`, `svh`, `lvh` birimi yoktur.**
- Neden: Akışta çerçevenin boyu içeriğin boyudur. Çerçeve içinde `vh` çerçeve boyuna bağlıdır; içerik boyu `vh`'ye bağlanırsa boyut bildirimi geri besleme döngüsüne girer. Ölçüldü: `.wrap{min-height:100vh}` ve `.wrap` dışında 40 px'lik bir altbilgi varken pano çerçeveyi bildirilen boya büyüttükçe çerçeve her turda +40 px büyüdü (60 turda 3400 px) ve içerik kısalınca küçülmedi; `min-height:0` ile tek düzeltmede durdu. Pano kabındaki `min-height` (`Modules.scss:40`, 266) bu maddenin dışındadır.
- Dayanak: talimatname §9.1 (akış yerleşimi, `edupedia:size`); `tedy-integration.md` §2; ölçüm.
- Denetim: `moduller.spec.ts:412` (iç kaydırma ≤ 1 px); kurulacak: KB-38 (e2e: akıştaki modülde çerçeve yüksekliği elle 400, sonra 4000 px'e ayarlanır; iki durumda bildirilen `edupedia:size` ±1 px aynı kalır ve 2 saniyede en çok 2 mesaj gelir. Statik: şablonda `vh|dvh|svh|lvh` yalnız `:root:not([data-host-layout="flow"])` ile başlayan seçicilerde geçer).
- Durum: uyuyor (`.wrap` 416'daki `100vh`, akışta 1045'teki `min-height:0` ile düşer); statik biçim borç KB-38.

**M5.8 — Yerleşim ekran 1920 (kök 16) ile ekran 3840 (kök 32) arasında aynıdır; yalnız ölçek iki katıdır.**
- Neden: 4K ekranda okur full-HD düzenini iki kat netlikte görür; çerçeve 57rem'de sabittir.
- Dayanak: CLAUDE.md "4K screens"; `ekran-4k.spec.ts`; `test_modul_kok_olcegi.py`.
- Denetim: `moduller.spec.ts:356` (`rootPx` kıstırma), `:384` (`.wrap` büyür); kurulacak: KB-33 (modül rotası `ekran-4k`'da: her görünür öğe 2 ×).
- Durum: uyuyor (kök ölçek uçtan uca doğru ölçüldü); görseller borç KB-30 (M5.12), kırılımlar borç KB-28 (M5.9).

**M5.9 — Modülün kırılımları `.wrap` üzerinde `container-type: inline-size; container-name: modul` ile kurulan kapsayıcı sorgusudur; eşikler Carbon rem değerleridir (sm 20rem, md 42rem); modülde `@media` genişlik sorgusu yoktur.**
- Neden: Şablonun 560 ve 400 px medya sorguları Carbon kırılımı değildir; ekran 390'da çerçeve 342 px olduğundan "≤ 400" düzeni de açılıyor. Medya sorgusundaki rem tarayıcı varsayılanıdır (16 px), kök ölçeği izlemez.
- Ölçüldü (2026-10-19, Chromium; sandbox'lı ve düz iframe aynı): kapsayıcı sorgusundaki rem çerçevenin hesaplanmış kök boyuyla çözülür. `@container (min-width:42rem)` çerçeve 912 @ 16, 1216 @ 21,33 ve 1824 @ 32'de doğru, 342 @ 16'da yanlış; sınır 1344 @ 32 doğru, 1343 @ 32 yanlış. `@media (min-width:66rem)` çerçeve 912 @ 16'da kapalı, 1216 @ 21,33 ve 1824 @ 32'de açık; medya sorgusu M5.8'i bozar. `@container (min-width:20rem)` 319 px'te yanlış, 320'de doğru.
- Temel (sorgusuz) stil 20rem altı içindir, çünkü ekran 360'ta çerçeve 19,5rem'dir. lg (66rem) modülde yazılmaz: akışta çerçeve en çok 57rem, tek başına açılışta `.wrap` en çok 55rem. Carbon kırılımlarını görüntü alanı yerine kapsayıcıya uygulamak kanunun kararıdır (KS-12).
- Dayanak: [2x Grid — overview #breakpoints](https://carbondesignsystem.com/building-blocks/foundations/2x-grid/overview/#breakpoints); M5.8; ölçüm.
- Denetim: kurulacak: KB-28 (statik: şablonda `@media` içinde `width` özelliği 0 kez geçer; e2e: ekran 1920 ve 3840'ta `.wrap`'in her çocuğunun hesaplanmış `display` ve `grid-template-columns` değeri aynıdır).
- Durum: borç KB-28 (`module-template.html:942`, 987, 992).

**M5.10 — Kenar durumda bile kart ızgarası taşmaz.**
- Neden: Ölçüldü: iki sütunlu kavram kartı çerçeve 288'de 10 px taşıyor (`minmax(16.25rem, 1fr)`).
- Dayanak: D2; [2x Grid — overview #breakpoints](https://carbondesignsystem.com/building-blocks/foundations/2x-grid/overview/#breakpoints) (sm 4 sütun).
- Denetim: kurulacak: KB-7.
- Durum: borç KB-7 (`module-template.html:944-951`).

**M5.11 — Kavram haritası md altında liste ya da dikey düzene geçer; hiçbir genişlikte düğüm üst üste binmez ya da kırpılmaz.**
- Neden: Ölçüldü: çerçeve 288'de 7 düğüm üst üste biniyor, 3'ü kırpılıyor; çerçeve 358'de 5 ve 2.
- Dayanak: D2; [Accordion — guidelines #when-to-use](https://carbondesignsystem.com/building-blocks/core/components/accordion/guidelines/#when-to-use) (dar ekranda sayfayı kısaltan dikey düzen).
- Denetim: kurulacak: KB-6 (kenar durum ve ekran 390'da düğüm kutuları kesişmez ve kabın içinde).
- Durum: borç KB-6 (`module-template.html:852-892`, 2864, 2879).

**M5.12 — Görseller rem ölçeğini izler: `width:100%`, en-boy oranı (`aspect-ratio` ya da `width`/`height` öznitelikleri) ve rem cinsinden bir üst sınır; oran Carbon listesinden seçilir (16:9, 9:16, 2:1, 1:2, 4:3, 3:4, 3:2, 2:3, 1:1), uymayan görselde kendi oranı serbesttir.**
- Neden: `max-width:100%` yalnız küçültür; 529 px'lik bir figür 4K'da sütunun yaklaşık %28'ini kaplarken metin iki katına çıkar. Grafik SVG'si üst sınırsız: çerçeve 1920 @ 32'de (≈ ekran 3840) 1692 × 917 px. Oranı bilinmeyen görsel yüklenirken sayfayı kaydırır.
- Dayanak: [2x Grid — guidelines #using-aspect-ratios](https://carbondesignsystem.com/building-blocks/foundations/2x-grid/guidelines/#using-aspect-ratios); [2x Grid — guidelines #adaptive-aspect-ratios](https://carbondesignsystem.com/building-blocks/foundations/2x-grid/guidelines/#adaptive-aspect-ratios); [2x Grid — overview #fluid-columns](https://carbondesignsystem.com/building-blocks/foundations/2x-grid/overview/#fluid-columns); `AspectRatio` (`dashboard/node_modules/@carbon/react/lib/components/AspectRatio/AspectRatio.js:30, 61-71`, @carbon/react 1.114.0).
- Denetim: kurulacak: KB-30 (CLS ≤ 0,1, `lighthouserc.cjs` eşiği; her `img` ve `video` için `width`/`height` öznitelikleri var ya da hesaplanmış `aspect-ratio` `auto` değil; ekran 3840'ta figürün çerçeve genişliğine oranı ekran 1920'dekiyle ±%1 aynı).
- Durum: borç KB-30 (`sablon.py:47`, 50; `module-template.html:590`, 594).

**M5.13 — İsteğe bağlı tempo diski, sesli okuma ve oturum süresi gibi araçlar M5.3, M5.6 ve M2.11'e uyar; hiçbiri ikinci bir ilerleme göstergesi olmaz.**
- Neden: Ölçüldü: tempo kapatma düğmesi 22 px, WCAG 2.5.8'in 24 px tabanının bile altında.
- Dayanak: S18; G-FLOW (geri sayımlı tempo diski FAIL); M2.4.
- Denetim: KB-4.
- Durum: tempo kapatma düğmesi 48 px, ikon 20 px, adı araç ipucunda (KB-44, 2026-10-24); ölçüm denetimi borç KB-4.

**M5.14 — Akışta kalan araçlar (ses, sesli okuma) Carbon ghost ikon düğmesidir: lg 48 px, ikon 20 px, araç ipucunda adı; yazarın ses varlığı Carbon dilinde stillenmiş bir oynatıcıyla çizilir.**
- Neden: Ölçüldü: araç düğmeleri 40 px, sesli okuma 36 px; `.edupedia-audio` stilsiz. Carbon, adı yerleşik olanlar (Bold, Italic) dışında her ikon düğmesine bir araç ipucu ister.
- Dayanak: İ6; [Tooltip — accessibility #annotate-the-text-for-the-tooltip](https://carbondesignsystem.com/building-blocks/core/components/tooltip/accessibility/#annotate-the-text-for-the-tooltip) ("Every icon-only button needs a tooltip, except for icons with clearly established names"); [Button — specifications #size](https://carbondesignsystem.com/building-blocks/core/components/button/specifications/#size).
- Denetim: kuruldu (KB-44): `dashboard/tests/e2e/modul-ikon-dugmeleri.spec.ts` — çerçeve 272, 288, 342 ve 358 doğrudan, ekran 320, 390, 1440 ve 3840 panoda, her bölümde: metinsiz her düğme ≥ 3rem ve ≥ 48 px, adlı, ikonu 1.25rem; "Oku" ≥ 3rem; araç ipucu fareyle ve klavye odağında düğmenin adını gösterir, Esc kapatır, odak düğmede kalır, çerçeveden taşmaz; 3840'ta araçlar 1920'dekinin iki katı; `audio` sınıflı, adlı, ≥ 3rem. `tests/test_modul_ikon_dugmeleri.py` (statik sözleşme).
- Durum: uyuyor (KB-44 kapandı 2026-10-24, `30258d7`). Ses, sesli okuma, tempo kapatma ve kavram haritasında bağlantı kaldırma `--tap` (3rem) kare, ikon 1.25rem; ad araç ipucunda: düğmenin kendi `aria-label`'ı (`::after`), Carbon ikon ipucu ölçüsünde (ters yüzey, `body-compact-01`, dolgu 2 × 16 px, 8 px aşağıda, en çok 18rem; `dashboard/node_modules/@carbon/styles/scss/components/tooltip/_tooltip.scss:26-29, 46-47, 85-104`, @carbon/styles 1.117.0), `:hover` yalnız `any-hover` altında (M2.12). "Oku" 48 px. Yazarın ses varlığı sınıflı `audio` (`.edupedia-audio__oynatici`) ile adlı Carbon katmanında (KB-11), denetimleri temayı izler (`color-scheme`). Sınır: Carbon'un ses oynatıcı bileşeni yok (bileşen listesi Jina Reader ile okundu 2026-10-24); denetimleri tarayıcı çizer ve stillenemez. Maddenin denetimi (sınıflı `audio`, adlı Carbon katmanı, ≥ 48 px) bunu kabul eder; oynatıcıyı Carbon bileşenlerinden (ghost ikon düğmesi, Slider) kurmak ayrı bir tasarım kararıdır, kullanıcıya bırakıldı. Ses efektinin varsayılanı (bugün hareket azaltma kapalıysa açık, 1478) ve yanlış cevaptaki `retry` sesi ürün kararıdır; kullanıcı kararını bekler.

**M5.15 — Tanım balonu dokunma, odak ve fareyle açılır, Esc ile kapanır; akışta konumunu panonun görünür alanına göre seçer; hiçbir genişlikte bir kısmı panonun bandının altında ya da görünür alanın dışında kalmaz.**
- Neden: `place()` yalnız çerçevenin kendi görünür alanına göre çeviriyor (`r.top`, `window.innerWidth`). Akışta çerçeve sayfa boyunda olduğundan balon panonun görünür alanını ve yapışkan bandını bilmez. Pano görünür alanın sınırını köprüyle bildirir ya da balon terimin altına sabitlenir.
- Dayanak: [Tooltip — accessibility #keyboard-interactions](https://carbondesignsystem.com/building-blocks/core/components/tooltip/accessibility/#keyboard-interactions) (tanım ipucu odakla açılır, Esc ile kapanır, tetikleyicinin noktalı alt çizgisi vardır).
- Denetim: kurulacak: KB-45 (e2e: ekran 390'da sayfa kaydırılmışken balonun kutusu görünür alanda ve bandın altında değil; dokunmada açılır).
- Durum: borç KB-45 (`module-template.html:3394-3403`; dokunmada açılma doğrulanmadı).

**M5.16 — Modül `lang="tr"` ve soldan sağa yazılır; Türkçe dışındaki her metin (gloss, diyalog, kart yüzü, alıntı) kendi `lang` özniteliğini taşır.**
- Neden: Dil işaretlenmezse ekran okuyucu yabancı metni Türkçe okur (WCAG 3.1.2). Dil bugün yalnız sesli okumaya veriliyor.
- Dayanak: D2; WCAG 3.1.2 (Carbon dayanağı yok, kanunun kararı).
- Denetim: kurulacak: KB-46 (`card.lang` ya da `ttsLang` taşıyan her içerik DOM'da aynı `lang`'ı taşır).
- Durum: borç KB-46 (`module-template.html:1737-1767`, 3056, 3069, 3215). Yazdırma tasarım hedefi değildir.

## 7. Adlı sapmalar

Kanunun Carbon'dan ya da TEDY'nin pano kurallarından bilerek ayrıldığı yerler. Sapma "düzeltilmez"; kaldırmak kanun değişikliğidir (§10). Bir KS satırı talimatname §11'in bir S satırına karşılık geliyorsa o satırın modül yüzeylerindeki hâlidir ve kazanır; S satırı modül için KS satırına yönlendirir, metnini tekrarlamaz (KB-34). Karşılıklar: KS-1 → S16, KS-2 → S38, KS-3 → S19, KS-4 → S10, KS-5 → S18, KS-6 → S43, KS-7 → S14, KS-8 → S2, KS-9 → S16, KS-10 → S26, KS-11 → S18 ve S43. KS-12'nin S karşılığı yoktur: talimatname [3.4-5] Carbon kırılımlarını panoda olduğu gibi kullanır.

| Kimlik | Konu | Carbon / pano | Kanun | Gerekçe | Dayanak |
|---|---|---|---|---|---|
| KS-1 | Okuma gövdesi | Carbon taban boyu productive 14 px, expressive 16 px; panoda `body-01` 14 px. Carbon'un hiçbir tip stili 18 px taşımaz (en yakın `body-02` 16 px / 1,5); 18 px tip ölçeğinin bir adımıdır | Modül gövdesi 18 px / 1,6'dır ve tek token `--tedy-body-reading: 1.125rem` ile bağlıdır. Değer Carbon tip ölçeğinin 4. adımından türetilir (`@carbon/type` ölçeği 12 · 14 · 16 · **18** · 20; `scale[3]`, Sass'ta `type.type-scale(4)`); böylece D1'in "Carbon token'larından türetilmiş" koşulunu ve anayasa §5.2'nin "yeni punto icat edilmez" kuralını sağlar. Carbon dışı tek değer satır yüksekliği 1,6'dır (Carbon `body-02` 1,5). Asla 16 px altı yok | Okur 12 yaşında; uzun okuma sahnesidir (vendor `carbon-child-system.md` §4). Satır yüksekliği uzun satırda gözün satır başını bulmasını kolaylaştırır | [Typography — type sets #base-type-sizes](https://carbondesignsystem.com/building-blocks/foundations/typography/type-sets/#base-type-sizes); [Typography — type sets #body-styles](https://carbondesignsystem.com/building-blocks/foundations/typography/type-sets/#body-styles); tip ölçeği `dashboard/node_modules/@carbon/type/lib/index.js:168-176`, @carbon/type 11.69.0; talimatname §9.3; anayasa §5.2 |
| KS-2 | Başlık düzeni | Başlık ve etikette cümle düzeni | Ad başlıkları başlık düzeninde (`basliga`), etiket ve düğme cümle düzeninde | Ailenin kararı (2026-10-19), Türkçe ders kitabı geleneği | S38; [Content #content-foundations](https://carbondesignsystem.com/building-blocks/foundations/content/#content-foundations) |
| KS-3 | Grafik paleti | Kategorik palet, komşu renk farkını en yükseğe çıkaran kesin bir sırayla uygulanır | `--viz-1..5` nötr gri rampa; kategoriyi yerinde etiket ve alt çizgi biçimi taşır | Ders aileleri ve anlam renkleri çıkınca yedek hue kalmıyor | S19; [Data visualization — color palettes #categorical-palettes](https://carbondesignsystem.com/building-blocks/data-visualization/color-palettes/#categorical-palettes); [Data visualization — legends #usage](https://carbondesignsystem.com/building-blocks/data-visualization/legends/#usage) (yerinde etiket; MCP: #color-and-texture); [Data visualization — legends #color-and-texture](https://carbondesignsystem.com/building-blocks/data-visualization/legends/#color-and-texture) (doku rengin yerine) |
| KS-4 | Köşe | Carbon v11 bileşenleri köşesizdir (popover 2 px, Tag 16 px); köşe token'ları `$border-radius-02…08`, `-max` @carbon/layout'ta var, bileşenlere v12 bayrağıyla gelir | Kart ve sahne 8 px = `$border-radius-08` değerine bağlanır; kontrol ve bildirim 0, etiket tam | Tedy katmanının onaylı kimliği; bildirim Carbon anatomisine döner (M2.3) | S10; [Popover — guidelines #corners](https://carbondesignsystem.com/building-blocks/core/components/popover/guidelines/#corners); [Tag — specifications #structure](https://carbondesignsystem.com/building-blocks/core/components/tag/specifications/#structure) (Tag köşesi 16 px); `dashboard/node_modules/@carbon/layout/scss/generated/_border-radius.scss:12-42`, @carbon/layout 11.61.0 |
| KS-5 | Dokunma hedefi | Etkileşimli ikonda ≥ 44 px | Dokunmatik girişte (`pointer: coarse`) ve çerçeve md altındayken her dokunulan denetim ≥ 44 × 44 px, standart 48 | Işık telefonda okur | S18; [Icons — guidelines #touch-targets](https://carbondesignsystem.com/building-blocks/foundations/icons/guidelines/#touch-targets) |
| KS-6 | İlerleme adımları | Adım sayısı sınırı yazılı değil; adımın en az genişliği 128 px (8rem), yani 57rem çerçevede yan yana en çok 7 adım | 3–7 aşama; segment adım değildir | Okurun tutabileceği yer sayısı (İ2, İ3); üst sınır Carbon'un adım genişliğinden türer | M2.5; [Progress indicator — guidelines #when-to-use](https://carbondesignsystem.com/building-blocks/core/components/progress-indicator/guidelines/#when-to-use); [Progress indicator — specifications #structure](https://carbondesignsystem.com/building-blocks/core/components/progress-indicator/specifications/#structure) |
| KS-7 | Tema seçimi | Kullanıcı tercihi yoksa sistem temasına uyulur | Modül sistem tercihine bakmaz; panonun bildirdiği temayı uygular | Tema kararı tek yerde (pano Profil'i); 4. ilke | M4.1; [Themes — code #system-preferences](https://carbondesignsystem.com/building-blocks/foundations/themes/code/#system-preferences); S14 |
| KS-8 | Font teslimi | — | Plex WOFF2 modülde gömülüdür; ağ isteği yok | Opak kökenli çerçeve, G-SELFCONTAINED | talimatname §9.3 |
| KS-9 | Serif | Carbon tip setlerinin harmanlanmasına izin verir | Modülde serif yalnız matematikte | Panoda serif Books'a ayrılmış (M1.9) | [Typography — style strategies #using-expressive-moments-within-product-designs](https://carbondesignsystem.com/building-blocks/foundations/typography/style-strategies/#using-expressive-moments-within-product-designs) |
| KS-10 | Bölüm ve bildirim hareketi | Carbon yeni sayfa açılışında ve bildirim kutusunun belirmesinde expressive hareket önerir | Bölüm değişiminde giriş hareketi yok; geri bildirim yalnız productive easing ile ve en çok `$duration-moderate-02` | Okurun başlatmadığı uyaran dikkat dağıtır (İ6); panoda Bugün'de de giriş hareketi yok | [Motion — overview #expressive-motion](https://carbondesignsystem.com/building-blocks/foundations/motion/overview/#expressive-motion); [Motion — overview #productive-motion](https://carbondesignsystem.com/building-blocks/foundations/motion/overview/#productive-motion); [Motion — overview #duration-tokens](https://carbondesignsystem.com/building-blocks/foundations/motion/overview/#duration-tokens) |
| KS-11 | İlerleme adımının vuruş kutusu | Carbon adım düğmesi 28 px yüksek (kök 16; derlenmiş CSS ölçüldü) | Tıklanabilir adım `min-block-size: 3rem` (48 px); tıklanamayan adım düğme değildir | S18 (KS-5); etiketli gösterge dokunmatik tablette de açılır | [Progress indicator — specifications #structure](https://carbondesignsystem.com/building-blocks/core/components/progress-indicator/specifications/#structure) |
| KS-12 | Kırılımın ölçtüğü şey | Carbon kırılımları görüntü alanı içindir | sm ve md eşikleri çerçevenin `.wrap` kapsayıcısına uygulanır; lg yazılmaz | Çerçeve görüntü alanının bir parçasıdır; medya sorgusu kök ölçeğini izlemez ve 4K eşliğini bozar (ölçüldü, M5.9) | [2x Grid — overview #breakpoints](https://carbondesignsystem.com/building-blocks/foundations/2x-grid/overview/#breakpoints); M5.9 |

## 8. Doğrulama ve bitti tanımı

Bu bölüm talimatname §12'nin modül ekidir: §8.1 ve §8.2'nin kapıları talimatname §12.2'nin "Modül yüzeyi" satırına, §8.3 talimatname §12.4'e eklenir; talimatname §12.1'in elle kapıları modül yüzeyinde de sorulur, "Telefon" kapısı §6.1'in genişliklerinde ve kenar durumda.

### 8.1 Bugün var olan kapılar

| Kapı | Ne düşürür | Madde |
|---|---|---|
| 18 derleme kapısı (G-CARBON, G-CARBON-GRID, G-TOKEN, G-A11Y, G-SVG, G-EMOJI, G-FLOW, G-WELLBEING, G-AUDIO, G-VOICE, G-BRIDGE, G-ATTRIB…) | yayın öncesi FAIL | M2.7, M3.8, M5.13 |
| Yayında kapıların yeniden koşması (`katalog._guncel_fail_kapilari`, 1.3) | `edupedia_yayinla` saklı taslak HTML'ini bugünün 18 kapısından yeniden geçirir; derlendikten sonra sıkılaşan bir kapı düşerse `kapi_fail_guncel` döner, katalog ve sürüm dizini yazılmaz (`tests/test_mcp_katalog.py::test_eski_taslak_bugunun_kapilarindan_gecmezse_yayinlanmaz`) | §8.3, M2.7 |
| `tests/test_modul_akis_yerlesimi.py` | akış bloğunda ham renk, gölge; `.topbar__l` görünür | M1.1, M1.10 |
| `tests/test_modul_kok_olcegi.py` | kök ölçek kıstırma | M5.8 |
| `tests/test_modul_baslik_duzeni.py` | başlık düzeni | M2.9 |
| `tests/test_tedy_tasarim_tutarliligi.py`, `tests/test_ders_renkleri.py` | pano ↔ şablon ↔ otorite, anlam renkleri | M1.7, M4.2 |
| `tests/test_pano_talimatname_borclari.py` (S10, S11, S19, S43, 4K rem) | köşe, gölge, palet, oyunlaştırma | M2.7, KS-3, KS-4 |
| `dashboard/tests/e2e/moduller.spec.ts` | akış, kök ölçek, baş, AI etiketi, açılışta odak | M1.1, M1.10, M2.13, M4.2, M5.7, M5.8 |
| `tests/test_mcp_rehber.py` | kanun §1 `akis` ve `carbon` başında, ≤ 3300 bayt; kanun vendor'a kopyalanmaz | §0.4 |
| `vendor_sync --check`; `src/mcp_server/vendor/tests/test_gates.py`; `tests/test_mcp_gates_ek.py`; `tests/test_mcp_vendor.py`, `tests/test_mcp_vendor_otorite.py` | sabitli vendor varlıkları; 18 kapının regresyonu (G-BRIDGE, G-ATTRIB dahil) | §0.2 (yazım varlıkları), M3.8 |
| G-WELLBEING rekabet listesi, G-ATTRIB yinelenen satır; `derleme.odul_hatalari`, `varlik_alani_hatalari`, `varlik_zorunluluk_hatalari`; `edupedia_derle` `alt_metin.alt_metin_dayanagi` | rekabet çerçevesi, `rewards.badges`, `meta.quest`; raster görselde eksik ya da kurala uymayan `alt`/`baslik`, kaynakta geçmeyen ad ve sayı (gerekçeyle uyarı), yinelenen atıf | M2.6, M2.7, M3.6–M3.8 |
| `tests/test_modul_rekabet_cercevesi.py`, `tests/test_modul_gorsel_alanlari.py`, `tests/test_modul_alt_metin_dayanagi.py`, `tests/test_modul_svg_metni.py`, `tests/test_modul_yazar_svg_metni.py`, `tests/test_modul_ikon_dugmeleri.py`; `dashboard/tests/e2e/modul-svg-metni.spec.ts`, `dashboard/tests/e2e/modul-ikon-dugmeleri.spec.ts` | rekabet sözcüğü ve sefer haritası şablonda; altyazısız raster figür; SVG metni 12 px altında (§6.1 genişlikleri); yazar SVG'sinde metin öğesi (`derleme.yazar_svg_hatalari`); 48 px altı, adsız ya da ipucusuz ikon düğmesi, sınıfsız `audio` | M2.6, M2.7, M3.6–M3.8, M5.6, M5.14 |
| `tests/test_mcp_rehber.py::test_kb35_vendor_bolumleri_kanunla_celismez` | yazara giden vendor bölümlerinde kanunun düşürdüğü dizgeler (tema düğmesi, rozet kasası, `meta.accent`, `fetch_figure.py`, yasak piktogram anahtarları, rekabet çerçevesi …) | M2.7, M3.1, M3.5, M3.10, M4.1, M4.5; KB-35 |

### 8.2 Kurulacak kapılar

1. **Modül rotası denetim takımında (KB-33).** `/moduller/<slug>/v<N>` sabit bir modül ve sabit köprüyle şu spec'lere eklenir: `tasarim-denetimi` (axe, eşit sütun, yatay kaydırma), `d3b-dokunma` (çerçeve içi dahil), `ekran-4k`, `gorsel-regresyon`, `gorunum-kipleri`, `aria-yapisi`, `ibm-erisilebilirlik`, `kontrast`, `yukleme-esigi`. Çerçeve içine Playwright `frameLocator` ile girilir.
2. **G-GORSEL derleme kapısı (KB-9; KB-10–KB-12 2026-10-23'te derleyicide ve G-ATTRIB'de kuruldu, §8.1).** FAIL: teach görsel oranı < %60 (kitap çerçevesinde), farklı kitap figürü < min(N, teach, 4), `pencere_disi_gerekce`'siz pencere dışı figür, yazar görseli yok, alt metin 60–150 dışı ya da kesik ya da yasak açılışlı, kaynakta geçmeyen ad ya da sayı (gerekçeyle WARN), raster figürde `figcaption` yok, yinelenen atıf satırı. G-SVG ve G-A11Y şablonun kendi JS dizelerini saymayı bırakır; ölçüm yalnız `MODULE_DATA` kaynaklı içeriğe bakar.
3. **Tema testi (KB-1, kuruldu 2026-10-20).** `moduller.spec.ts` tersine yazıldı: çerçevede `#themeBtn` yok; panonun gönderdiği tema her gönderişte uygulanır; tema kaydı kapı izin listelerinden çıkar.
4. **Statik şablon testleri.** Ders rolü allow-list (KB-16, KB-17), serif yalnız matematikte (KB-15), bölüm girişi `@keyframes` ve expressive easing yok (KB-18), `[data-theme]` yalnız token bloklarında (KB-22), statik satır içi stil yok — `style=` içinde yalnız hesaplanan geometri (`left`, `top`) ve `--` ile başlayan özellik (KB-26), seçici çift tanımı yok (KB-8), koşulsuz `:hover` yok ve `@media` genişlik sorgusu yok (KB-28), akışta viewport yükseklik birimi yok (KB-38), `--tedy-body-reading` tanımlı (KB-39), akışta `role="banner"`/`"main"` yok (KB-40), kalıcı opaklık yok (KB-41).
5. **Ölçüm e2e'leri.** Zemin eşliği (KB-3, kuruldu), en büyük yazı (KB-14), ilerleme göstergesi (KB-2, kuruldu), SVG metin boyu (KB-5, kuruldu), kavram haritası (KB-6), satır uzunluğu (KB-29), figür oranı ve CLS (KB-30), boyut geri beslemesi (KB-38), form ve tablo (KB-42, KB-43), ikon düğmeleri (KB-44, kuruldu), tanım balonu (KB-45), dil öznitelikleri (KB-46).
6. **Rehber testi.** Kuruldu (2026-10-19, §8.1): `tests/test_mcp_rehber.py` kanun §1 ≤ 3300 bayt, `akis` ve `carbon` ilk parçası kanun §1 ile başlar, vendor bölümlerinde kanunla çelişen dizgeler geçmez (KB-35). Kanun dosyasının her üst başlığı `## N.` biçimindedir (aynı test).

Her maddenin düştüğü test, maddenin "Denetim" satırındadır; kurulacak kapı o satırda KB kimliğiyle anılır.

### 8.3 Bitti tanımı

Modül yüzeyini değiştiren iş, talimatname §12.4'ün bütün koşullarına (önce kırmızı test, `npm run lint` ve `build`, `code_audit` okuması, yayın ve `ted-mcp` yeniden başlatma dahil) ek olarak şunların hepsi doğruysa biter:

1. §8.1 ve kurulmuşsa §8.2 kapıları geçer.
2. Değişen her madde §6.1'deki genişliklerde ve kenar durumda ölçüldü; ölçüm dosyası commit mesajında anılır.
3. Görsel taban farkı okunarak güncellendi (talimatname §12.3).
4. Carbon'a değen her karar MCP `anchor_url`'ı taşır (M2.1).
5. Kanunla çelişen alt metin aynı commit'te düzeltildi ya da §9'a borç olarak yazıldı.
6. Borcu kapatan commit §9'daki satırı "kapandı", tarih ve commit ile işaretler ve kapanış testini adlandırır; §9 girişindeki eşlemede bir talimatname B satırıyla eşliyse o satır da güncellenir.

## 9. Kanun borçları

Önem sırası: önce okuru doğrudan etkileyen ve ölçülen kusurlar, sonra içerik, sonra görünüm dili, sonra belge. Satır numaraları `src/mcp_server/vendor/assets/module-template.html` içindir; başka dosya adıyla yazılır. Bu bölüm modül yüzeylerinin borç kaydıdır; talimatname §13 öteki yüzeylerinkidir ve bir kusur yalnız birinde durur. Talimatnamenin kapanmış satırlarının modüldeki artıkları: B3 → KB-28, B8 → KB-4, B10/B37 → KB-28, B11 → KB-40, B34 → KB-41, B38 → KB-32, B39 → KB-18, B48 → KB-37, B73 → KB-21, B74 → KB-14 ve KB-47. Modül sayfasının `Breadcrumb`'ındaki değiştirici tuş sorunu pano geneli tek düzeltme olduğu için talimatname B80'dedir.

### 9.1 Ağır

| Kimlik | Madde | Yer | Ölçülen olgu | Kapanış testi |
|---|---|---|---|---|
| KB-1 | M4.1 | **Kapandı (2026-10-20).** 1110-1112, 1454, 1528-1531, 1550, 1623-1648, 1040-1042; `moduller.spec.ts:326-354`; `tests/test_mcp_gates_ek.py:55-57`; `src/mcp_server/gates_ek.py:19-20`; `vendor/tests/test_gates.py:1884-1900`; `vendor/tests/fixtures/minimal_pass.html:596, 809, 888`; `dashboard/src/utils/moduleBridge.ts:60-66` | Akışta düğmeyle çerçeve g100'e geçiyor, pano g10; tema kaydı kapı izin listelerinde; köprü yorumu "unless the student picked a theme" ve `ModuleTheme` içinde `'white'` | `moduller.spec.ts` tersine: `#themeBtn` yok, pano teması kazanır; tema kaydı izin listesinden çıkar (`test_gates.py`, `gates_ek.py`) |
| KB-2 | M2.4, M2.5, M5.4 | **Kapandı (2026-10-20).** 479, 483-502, 485, 488, 1797-1801, 1810 | 15–18 adım, 28 px düğme, çerçeve 358'de 11. adım görünmüyor, etiket yok, bekleyen adım `text-secondary`; gösterge kabı 34,2rem | E2e (M5.4'ün genişlik listesi, 3/5/7 aşama): tek gösterge, geçerli adım görünür, metin görünür ve ≤ 2 satır, toplam ikincil, ≥ 44 px; derleyici 3–7 aşama, ad ≤ 16 karakter |
| KB-3 | M1.2 | **Kapandı (2026-10-20).** 1044 | Çerçeve #f4f4f4, pano #f2f4f8 | E2e zemin eşliği |
| KB-4 | M2.8, M5.3, M5.13 | 469, 488, 461, 1025, 547-555, 2509, 841; `ModulBasligi.tsx:45-48`; `Modules.scss:194-198`. 488 KB-2 ile; 469, 461 ve 1025 KB-44 ile 48 px (2026-10-24) | 40, 28, 22, 36, 30, 8–11, 16 px; breadcrumb 62 × 18; etiket vuruş kutusu ölçülmedi | `d3b-dokunma` modül rotası, çerçeve içi, `elementFromPoint` yöntemi |
| KB-5 | M5.6 | **Kapandı (2026-10-23, `9107214`).** **Düzeltme turu (kanun 1.3, `5683e6d`):** etiket genişliği ölçülmüş Plex Sans glifleriyle (`vizEmTablosu`), sayı doğrusunun `points` değerleri her genişlikte etiketli, çubuk grafik dikey sığıyorsa dikey; e2e 2560/3840 ve etiket çakışması, `tests/test_modul_svg_metni.py::test_nokta_degerleri_her_genislikte_okunur`, `::test_cubuk_grafik_dikey_sigiyorsa_dikey_kalir`, `::test_ayni_satirdaki_etiketler_olculmus_genislikle_cakismaz`. 2373, 2382-2388, 2488 **İkinci düzeltme turu (1.3.1, `e11479f`):** zorunlu etiketler gerektiği kadar satıra iner (`vizSatirAta`; eski kural üçüncü komşuyu ilk satıra yazıyordu: çerçeve 288'de "−3 ↔ −2", 272'de "−1 ↔ 0"), harf adları da; SVG yüksekliği satırla büyür; altın örnekte "Ardışık Noktalar" ve "Dar Aralık", e2e çerçeve 272/342 (`tests/test_modul_svg_metni.py::test_sayi_dogrusu_etiket_satirlari_viewboxa_sigar`; e2e kırmızıda 3/11 düştü). | Çerçeve 288'de 4,9 px, 358'de 6,5 px grafik metni (2026-10-23 kırmızı ölçümünde en küçük 4,9 px) | E2e `fontSize × CTM.a ≥ 12`: `dashboard/tests/e2e/modul-svg-metni.spec.ts` (kırmızıda 5/7 düştü, yeşilde 7/7); `tests/test_modul_svg_metni.py` |
| KB-6 | M5.11 | 852-892, 2864, 2879 | Çerçeve 288'de 7 çakışma / 3 kırpma; 358'de 5 / 2 | E2e düğüm kesişimi |
| KB-7 | M5.2, M5.10 | 944-951, 2594 | Çerçeve 288'de 10 px taşma; tablo kabı odaklanamıyor | E2e yatay taşma 0; `tabindex` ve ad |
| KB-8 | M4.7 | 681, 947 | `.card` iki tanım; kavram kartında harf kırılması | Statik: seçici tek blok; görsel taban |
| KB-14 | M1.8, M2.9 | 779, 775, 353, 990, 447 | Özet başlığı 40 px serif 600, mola geri sayımı 40 px mono > `heading-05` 32 px (ekran 3840'ta 80 > 64) | E2e en büyük yazı < pano h2 ve ≤ 1,75rem |
| KB-31 | M1.3 | `Modules.scss:41-46` | Telefonda 16 px dar, kenarlar 16 / 32 | `tasarim-denetimi` eşit sütun, modül rotası |
| KB-33 | M5.1, M2.13, §8.2 | `dashboard/tests/e2e/_gorsel-yardim.ts:9-16` ve takım spec'leri | Modül rotası hiçbir denetim spec'inde yok | Dokuz spec'te modül rotası |

### 9.2 İçerik ve görsel

| Kimlik | Madde | Yer | Ölçülen olgu | Kapanış testi |
|---|---|---|---|---|
| KB-9 | M3.2–M3.5 | `gorsel.py:94-107` | Teach görsel oranı %17–40; pencere figürünün ~%10'u kullanılmış; sb7 pencere içinden 0/1; yazar görseli 0; `pencere_disi_gerekce` alanı yok | G-GORSEL |
| KB-10 | M3.6 | **Kapandı (2026-10-23, `0388324`).** **Düzeltme turu (kanun 1.3, `5683e6d`):** dayanak kitabın metnidir — `edupedia_gorsel` Maarif `nearby_text`'ini `kitap_altyazisi`, VLM `caption`'ını `betim` olarak ayrı saklar; `alt_metin.varlik_kaynagi` betimi okumaz (`tests/test_modul_alt_metin_dayanagi.py::test_yalniz_yapay_zeka_betiminde_gecen_ad_dayanaksizdir`, `tests/test_mcp_gorsel.py::test_textbook_figure_keeps_book_caption_apart_from_the_vlm_description`); tırnak/ayraç/tireyle açılan yasak açılış ve NFC (`tests/test_modul_gorsel_alanlari.py::test_tirnak_ayrac_ve_ayrisik_harf_yasak_acilisi_gizlemez`). `gorsel.py:132-133`, `varliklar.py:124`, `server.py:160` **İkinci düzeltme turu (1.3.1, `e11479f`):** `edupedia_kapsam`'ın figür adayları kitaptaki adla (`etiket`) ve `betim` olarak döner, `aciklama` yok (`tests/test_mcp_kapsam.py`). | Dört alt metin 200 karakterde kesik; "Bu şema…" açılışı; KAAN → "F-35"; yazarın alt metin alanı yok | `meta.assets[i].alt` şeması ve `edupedia_derle`'nin ad/sayı dayanağı (G-GORSEL yerine derleyicide): `tests/test_modul_gorsel_alanlari.py`, `tests/test_modul_alt_metin_dayanagi.py` |
| KB-11 | M3.7, M5.14 | **Kapandı (2026-10-23, `0388324`).** **Düzeltme turu (kanun 1.3, `5683e6d`):** süs görseli `baslik` almaz, `figcaption` çizilmez (`::test_sus_gorseli_baslik_istemez_ve_altyazi_cizilmez`, `::test_sus_gorseli_altyazi_tasimaz`). `sablon.py:45-48`, `derleme.py:477` | Raster figürde `figcaption` yok; `.edupedia-audio` stilsiz | `tests/test_modul_gorsel_alanlari.py::test_her_img_figure_ve_gorunur_figcaption_icinde`, `::test_ses_oynaticisi_carbon_dilinde_gorunur_etiketli`; e2e altyazı görünür |
| KB-12 | M3.8 | **Kapandı (2026-10-23, `0388324`).** **Düzeltme turu (kanun 1.3, `5683e6d`):** aynı varlık iki yuvada iki ad taşıyamaz (`::test_ayni_varlik_iki_yuvada_farkli_adla_yazilamaz`); adlar NFC'de karşılaştırılır. `derleme.py:540`, 557-563 | Aynı MEB satırı iki kez; satır figürü adlandırmıyor | G-ATTRIB yinelenen satır FAIL; satır `baslik — atıf`: `tests/test_modul_gorsel_alanlari.py::test_g_attrib_yinelenen_satirda_duser`, `::test_atif_varlik_basina_tek_satir_ve_figurun_adini_tasir` |
| KB-48 | M5.6 | **Kapandı (2026-10-24, `30258d7`).** Yol (a): derleyici `MODULE_DATA`'daki SVG metin öğesini reddeder (`derleme.py:529-562`, `yazar_svg_hatalari`; `edupedia_derle` `sema_hatasi`, açıklaması); yer genişledi: `hotspot`'un `svg`'si ve gövdeye gömülü SVG de. Altın örnek: t1 metinsiz SVG (adlar altyazıda), t3 etiketli şema (şablon demosu ve `ornek_veri/module_data_demo.json`). Rehber: vendor `svg-authoring.md`, `icon-pictogram-svg.md`, `subject-packs.md`, `SKILL.md` §11. Yayındaki üç modülde yazar SVG'si yok. Yazar SVG'si: `svgFigure` (`visual.kind:"svg"`), etiketli şemanın `base`'i | viewBox yazarındır, şablon kutuya göre kuramaz; altın QUIZ örneğinin diyagramında metin çerçeve 288'de 6,1 px, 358'de 8,3 px (2026-10-23, Chromium, `fontSize × CTM.a`) | `tests/test_modul_yazar_svg_metni.py` (kırmızıda 20/22 düştü); e2e altın örneklerin yazar figürleri `modul-svg-metni.spec.ts` "author SVG" (kırmızıda 4/4 düştü: çerçeve 288'de 6,1 px, 358'de 8,3 px) |
| KB-13 | M3.11 | `derleme.py:470-476`; `kapsam.py:255, 525, 589-593`; `gorsel.py:94-96` | Yuva yalnız teach, tek varlık; 6 aday tavanı; gizli figür (5280, 5282, 3065) aranmıyor; aday listesi run'a yazılmıyor | Derleme ve kapsam testleri: mcq/hotspot/flashcards yuvası, pencerenin tüm adayları run kaydında |
| KB-32 | M2.11, M3.10 | 527, 554, 567, 642, 949, 1012, 1080, 1258, 1542, 1957, 3153; segment piktogramı | 1,1rem ve 1,15rem ikon; 32/30 px piktogram; `keyTerms[].icon`'daki `pic-*` 0,9rem (`.def-term`) ve 1,05rem (`.def-pop`); bilinmeyen anahtar sessiz yedek; sprite'ta ödül ikonları | Statik boy kümesi; derleyici anahtar doğrulaması (yasak anahtarlar dahil) |

### 9.3 Görünüm dili

| Kimlik | Madde | Yer | Ölçülen olgu | Kapanış testi |
|---|---|---|---|---|
| KB-15 | M1.9 | 537, 779, 973 | Serif giriş metni, özet başlığı, çeviri satırı | Statik: `--font-serif` yalnız `.math`, `.fb-eq` |
| KB-16 | M1.4 | 897 | Etkinlik segmentlerinde dolu ders rengi ikon karesi | Statik allow-list |
| KB-17 | M1.5, M1.6, M1.10, M2.14 | Durum seçicileri: 552, 611, 652, 662, 691, 736-739, 762, 791, 841, 865, 867. Çapa dışı: 418, 532, 682, 687, 704, 730, 744, 751, 764, 767, 772, 775, 778, 783, 808-812, 820-822, 844, 913, 928, 932, 936, 940, 948-949, 986, 1012 | Ders rengi çapa dışında ve etkileşim durumlarında (`accent-color` dahil) | Statik allow-list (durum seçicileri ve `accent-color` dahil) |
| KB-18 | M2.10 | 370, 619-622 | `segIn` expressive giriş, her bölümde | Statik: bölüm girişi `@keyframes` 0; `gorunum-kipleri` |
| KB-19 | M2.2 | 629-643, 2048, 2220, 2288, 2888, 3167, 3210, 3222, 3223 | Ghost ve devre dışı ghost'ta içten 1 px çerçeve (636, 641); ikon etiketin solunda; ortalı etiket `.btn--center` (643, 3167, 3210); etiket 16 px / 500 ve ikon 18,4 px (629, 642) | E2e düğme ölçüleri, etiket hizası, ikon etiketten sonra, primary ≤ 1 |
| KB-20 | M2.3 | 664-674, 820-830 | 8 px köşe; callout 4 px kenar | E2e köşe 0, kenar 3 px, kutu içinde etkileşimli öğe 0 |
| KB-21 | M2.6, M2.7 | **Kapandı (2026-10-23, `0388324`).** **Düzeltme turu (kanun 1.3, `5683e6d`):** G-WELLBEING yalnız arayüz metnini tarar (`_arayuz_metni`) ve eş anlamlıları bilir (`tests/test_modul_rekabet_cercevesi.py::test_anlatidaki_yarisma_ve_sefer_haritasi_dusurmez`, `::test_arayuz_alanlarindaki_rekabet_cercevesi_duser`); yayın kapıları yeniden koşar (`tests/test_mcp_katalog.py::test_eski_taslak_bugunun_kapilarindan_gecmezse_yayinlanmaz`). 503-518, 1120, 1807, 1210, 2008, 2049, 2071, 2174; `derleme.py:388-389` **İkinci düzeltme turu (1.3.1, `e11479f`):** etiket türü arayüz alanları da taranır — `interactiveLabel`, `bins`, `params`, `columns` (`tests/test_modul_rekabet_cercevesi.py::test_etiket_turu_arayuz_alanlari_taranir`, `::test_icerik_etiketleri_taranmaz`); kapılar yeniden koşamazsa yayın durur (`tests/test_mcp_katalog.py::test_kapilar_yeniden_kosamazsa_yayin_durur`). | Sefer haritası, "Son N durak", "Yarışma", "Meydan Oku"; `rewards` zorunlu | Statik sayım 0 ve derlenmiş çıktıda 0; G-WELLBEING FAIL listesi; şema (`rewards` isteğe bağlı, `badges` ve `meta.quest` hata): `tests/test_modul_rekabet_cercevesi.py`, vendor `test_gwellbeing_fails_on_competition_framing` |
| KB-22 | M4.3 | 258-290, 586-587, 664; `vendor/scripts/validate_module.py:1094-1157`; `vendor/scripts/sync_carbon_tokens.py:9, 165-169`; `tests/test_tedy_tasarim_tutarliligi.py`, `tests/test_pano_talimatname_borclari.py`, `minimal_pass.html` | `white` bloğu ölü; elle hex; bileşene özel g100 kuralı | Statik `[data-theme]` yalnız token bloklarında; `white` bloğu ve onun G-TOKEN ile `sync_carbon_tokens.py` girdileri aynı commit'te kalkar; G-TOKEN g10 ve g100 ile PASS |
| KB-23 | M4.4 | şablonda `forced-colors` 0 | Zorunlu renk kipinde kenarlar ve odak doğrulanmamış | `gorunum-kipleri` modül rotası (M4.4 ölçütü) |
| KB-24 | M4.5 | `derleme.py:381-386` | `meta.accent` aile adıyla kabul ediliyor | Şema: `meta.accent` hata |
| KB-25 | M4.7 | 2391, 2407, 2417; `validate_module.py:978` | Kullanıcı rengi `fill`'e ve satır içi stile geçiyor; G-SVG yalnız WARN | G-SVG ham hex FAIL; şema `color` hatası |
| KB-26 | M4.7 | 1080, 1578, 1855-1856, 2042, 2047, 2155, 2167, 2172, 2329, 2333, 2417, 2537, 2879, 3100, 3155, 3159, 3162, 3168, 3177, 3221, 3260, 3289, 3306, 3331, 3342, 3348, 3401-3402, 3409; `sablon.py:47`, 50; `derleme.py:562` | Motor ve derleyici satır içi stil yazıyor (görünürlük, `display`, `transition:none`, renk); balon ve kavram haritası konumu hesaplanan geometridir | Statik: satır içi `style` yalnız hesaplanan geometri (`left`, `top`, `--arrow-x`, kavram haritası %-konumu) ya da `--` ile başlayan özellik taşır; görünürlük `hidden` özniteliği ya da sınıfla; renk, boşluk, font ve kenarlık içeren satır içi stil 0 |
| KB-27 | M4.6 | vendor `subject-packs.md:30-32` | Derse özel tipografi önerisi | Statik: `data-subject` seçicisi yok |
| KB-28 | M2.12, M5.9 | 942, 987, 992; 13 `:hover` | Carbon dışı 560/400 px medya sorgusu; koşulsuz hover | Statik: `@media` içinde `width` 0, koşulsuz `:hover` 0; e2e ekran 1920 ve 3840'ta aynı dal |
| KB-29 | M5.5 | 416, 1045 | Çerçeve 960 @ 16 ve 1920 @ 32'de 104 karakter/satır | E2e başvuru paragrafı: her satır ≤ 80, ortalama ≤ 75 |
| KB-30 | M5.12 | `sablon.py:47`, 50; 590, 594 | Görsel piksel boyunda; grafik çerçeve 1920 @ 32'de 1692 × 917 | E2e oran ±%1, oran özniteliği, CLS ≤ 0,1 |
| KB-37 | M1.11 | `ModuleViewer.tsx:150` | İskelet 400 ms eşiksiz | `yukleme-esigi.spec.ts` modül rotası |
| KB-38 | M5.7 | 416, 1045 (önleyici) | Bugün akışta viewport birimi geçerli değil; bir `100vh` geri dönerse çerçeve her turda altbilgi kadar büyür (ölçüldü) | E2e 400/4000 px boyut bildirimi; statik seçici kuralı |
| KB-39 | KS-1 | 354, 412 | Okuma gövdesi `--fs-body` adıyla duruyor; kanunun token adı yok | Statik: `--tedy-body-reading` tanımlı, gövde ondan okur |
| KB-40 | M1.10 | 1083, 1129 | Akışta ikinci `banner` ve `main` yer işareti | `aria-yapisi` modül rotası; statik: akışta `role` kaldırılır |
| KB-41 | M4.7 | 445, 554, 561, 563, 574 | Kalıcı opaklıkla soldurma (`fill-opacity:.5`, `opacity:.85`, `.def-pop__ex-t` `opacity:.92`) | Statik: `opacity` / `fill-opacity` yalnız geçiş anahtar karelerinde |
| KB-42 | M2.14 | 687, 791, 2212, 2286, 2343 | Görünür etiketsiz giriş ve metin alanı; dolu ders rengi alt çizgi; radyo 1,375rem, ders rengi `accent-color` | E2e görünür etiket, token zemin ve kenar, lg boy |
| KB-43 | M2.15 | 910, 913, 2594 | `caption` isteğe bağlı; `.hi` ders rengi; zebra satır | Derleyici `caption` zorunlu; e2e satır ≥ 48 px; statik: `.viz-table` zebra kuralı 0 |
| KB-44 | M5.14 | **Kapandı (2026-10-24, `30258d7`).** 461, 470, 484-494 (araç ipucu), 930, 1070 (`.tts-oku`), 1661 (`aracIpucu`, Esc), 641-642 (`color-scheme`); `sablon.py:60` (`edupedia-audio__oynatici`); altın `ornekler.arac_ornegi()`. Sınır: oynatıcının denetimlerini tarayıcı çizer (M5.14 Durum). Önce: 469, 1478, `.edupedia-audio` | Araç düğmeleri 40 px, sesli okuma 36 px; oynatıcı stilsiz. Kırmızı ölçüm (2026-10-24): çerçeve 272'de ses ve sesli okuma 40, tempo kapatma 22 px (ikon 12,8); ekran 3840'ta 80 ve 44 < 96; araç ipucu yok; `audio` sınıfsız | `dashboard/tests/e2e/modul-ikon-dugmeleri.spec.ts` (kırmızıda 16/17 düştü, yeşilde 17/17); `tests/test_modul_ikon_dugmeleri.py` (kırmızıda 6/7) |
| KB-45 | M5.15 | 3394-3403 | Balon yalnız çerçevenin görünür alanına göre konumlanıyor; dokunma doğrulanmadı | E2e ekran 390 kaydırılmış sayfada balon görünür alanda |
| KB-46 | M5.16 | 1737-1767, 3056, 3069, 3215 | Yabancı dil metni DOM'da `lang` taşımıyor | Statik ve e2e: `lang` eşliği |
| KB-47 | M2.9 | 545, 568, 572, 629, 732, 797, 840, 929, 932 | Carbon dışı ağırlık: 500 (`.terms__lbl`, `.btn`, `.hook-opt`, `.adim-sayaci`, `.sim-param__lbl`) ve 700 (`.def-pop__term`, `.def-pop__ex-lbl`, `.viz .pin-n`, lejant işareti); ölçek dışı punto 13 px (545, 797) ve 11 px (572); `.btn` 629 KB-19 ile ortak | Statik: şablonun kural gövdelerinde (`@font-face` dışı) `font-weight` ∈ {300, 400, 600}, `font-size` Carbon ölçeğinde ya da token |

### 9.4 Belge

| Kimlik | Madde | Yer | Ölçülen olgu | Kapanış testi |
|---|---|---|---|---|
| KB-34 | §0.2, §7, M1.5, M1.9, M2.10, M4.1, M4.3, M4.5, M5.9 | Talimatname T:3, 36, 42-43, 61, §0.3'e kanun satırı, 71-72, 239, 562, 740, 2506, 2828-2831, 2850, 2877-2884 (kicker, seçenek halkası, `meta.accent`), 2892, 2893, 2896, 2899, 2911-2920, 2935, 2946, 2950-2951, 2974, 2999, 3011-3012, 3020-3022, 3036-3037, 3040, 3048-3050, 3214-3215, 3328 (S14), 3357 (S43), §11 S satırlarında KS yönlendirmesi, 3633-3646 (§14.3'e kanun satırı); anayasa `frontend-design-principles.md:13-16`, 327-329 (§5.5); `frontend-surface-designs.md:15-17`, §4.12 (603-631); `carbon-bilesen-rehberi.md:11-14`; `AGENTS.md:106-112`; `CLAUDE.md:218, 251, 354`; `.claude/skills/tedy-carbon/SKILL.md:8, 14-26` | Öncelik zincirlerinde kanun ve vendor yok; vendor "tek kaynak/yetkili" deniyor; S14 modülün g10↔g100 geçişini yazıyor; §9.2 `meta.accent` izni ve geniş çapa listesi; §9.3 "55rem sütun", segment girişi hareketi, `adoptHostTheme()` `white`; §9.8 #4 560/400 px, #8 4 px kenar ve 8 px köşe sapması, #14 `.lead` serifi, #19 gölge ve tek g10 istisnası; S43 "kalırsa sessiz liste"; anayasa §5.5 "Başlık Her Kelime Büyük değil" S38 revizyonuyla çelişiyor; yüzey tasarımları modül sayfasını kanuna bağlamıyor; tedy-carbon 58 bayt boşlukla 4 KB sınırında | **Kapandı 2026-10-19.** İnceleme (düzenleme turu ve denetimi); `tests/test_mcp_rehber.py`; tedy-carbon 4094 bayt ≤ 4 KB (`wc -c`). Talimatname 2.0 ve anayasa 1.3 yazıldı; talimatname 2.0 kullanıcı onayı ister (§14.2), onay commit'te kaydedilir |
| KB-35 | M1.1, M1.5, M2.7, M2.10, M3.1, M3.5, M3.10, M4.1, M4.5 | Vendor: `SKILL.md:24-26, 116-117, 140, 254-258, 270, 272-281, 312, 320, 333-341, 348-349, 374-376, 407, 415-418, 422, 639-641`; `tedy-integration.md:44-52, 78, 100-103, 153-155, 157-159, 180, 200-205, 245-250, 253-254, 260-261, 269`; `carbon-child-system.md:8, 264, 389, 397, 404-454`; `carbon-excellence.md:165-170, 212-216, 228-230, 257-259, 270-274`; `svg-authoring.md:42-44, 108`; `icon-pictogram-svg.md:69-76, 88, 106-126, 145-152`; `module-architecture.md:33, 45, 48, 63-72, 151, 166, 315`; `interaction-patterns.md:124`; `content-enrichment.md:51, 140-144`; `adhd-pedagogy.md:75-81, 104-108, 196, 290-293, 401`; `gamified-flows.md:71, 95-104, 253-257, 315`; `color-system.md:32, 34-…, 59-60`; `curriculum-integration.md:128-134`; `audio-system.md:15, 90` | Yazara giden metinde tema düğmesi, XP/rozet, anında ödül, rozet kasası, `meta.accent`, dolu ders rengi ikon karosu, geniş çapa listesi, eski viz paleti, donut, giriş animasyonu, yerel script, var olmayan piktogram anahtarları, yazar SVG'si "yedek"; "yetkili / tek kaynak" cümleleri tasarım kararı için kanunun altına alınmamış; `meta.milestones` ödül aracı olarak tanımlı | **Kapandı 2026-10-19:** `vendor_sync --pin` (`--check` geçer) ve `tests/test_mcp_rehber.py::test_kb35_vendor_bolumleri_kanunla_celismez` (`akis`, `carbon`, `segmentler`, `pedagoji`, `etkilesim`, `svg`; kanunun düşürdüğü 21 dizge geçmez, "tema düğmesi" yalnız "yok", "kalktı" ya da borç bağlamında). İlk tariften fark: "XP" ve "rozet" sözcükleri tek başına sayılmaz, çünkü motor belgesi iç XP sayısını anlatır; yerine somut dizgeler sayılır |
| KB-36 | §0.2 | edupedia eklentisi `skills/edupedia/SKILL.md:15, 18` (CureoPrivate `surfaces/bootstrap.md`) | "Carbon g10/g100, lacivert Tedy bandı"; kanun anılmıyor | Eklenti sürümü kanunu anar |

## 10. Değişiklik usulü ve kaynaklar

### 10.1 Değişiklik usulü

- Kanun sürümlüdür. Bir maddenin hükmünü değiştirmek, madde eklemek ya da kaldırmak küçük sürümdür (1.x). §0.2'yi, bir maddenin kimliğini ya da bir adlı sapmayı değiştirmek büyük sürümdür (2.0) ve kullanıcı onayı ister.
- Madde kimlikleri (M, KS, KB) yeniden kullanılmaz. Kapanan borç satırı silinmez; "kapandı", tarih ve commit alır (talimatname §0.4).
- Kanunu değiştiren commit etkilenen alt metni aynı commit'te düzeltir: talimatname (§0.2, §0.3, §9, §11 S satırı, §14.3, değişiklik kaydı), anayasanın, yüzey tasarımlarının ve bileşen rehberinin öncelik paragrafları, `AGENTS.md`, `.claude/skills/tedy-carbon/SKILL.md`, `CLAUDE.md` Modüller maddesi, vendor referansları (`vendor_sync --pin` ile `PROVENANCE.json` birlikte). Düzeltilemeyen metin §9'a borç olarak girer.
- §1 değişirse bayt sınırı (§0.4) yeniden ölçülür ve `tests/test_mcp_rehber.py` çalıştırılır.
- Carbon'a ait her iddia talimatname §10.5'e göre kaynak gösterir (§10.2). MCP'de bulunamayan iddia "Carbon dayanağı yok, kanunun kararı" diye yazılır.

### 10.2 Carbon kaynakları

Sayfa listesi ve ortak olgu çapaları [talimatname](tedy-ui-ux-talimatnamesi.md) §15'tedir (§15.6 kanunun kullandığı sayfalar, §15.7 ortak olgular için tek çapa); bu bölümün tabloları kanunun dayandığı çapaları konuya göre tutar ve ortak olgularda §15.7'nin çapasını kullanır.

Carbon'a atıf ve doğrulama usulü [talimatname](tedy-ui-ux-talimatnamesi.md) §10'dur: sorgu protokolü §10.2, `code_audit` §10.3, kaynak gösterme §10.5; kaynakça talimatname §15'tir. Kanun ayrı bir usul tanımlamaz. Her Carbon dayanağı `docs_search` sonucunun `anchor_url`'ını aynen bir bağlantı olarak taşır; kurulu paket olgusu `dashboard/node_modules/<paket>/…:satır` ve paketin sürümüyle yazılır. Yollar yalnız `/building-blocks/...` biçimindedir (talimatname B18). Aşağıdaki tablolar kanunun dayandığı sayfaların ve çapaların tamamıdır.

Carbon MCP indeksi: belgeler `last_crawled_at` 2026-09-30 (veri görselleştirme sayfaları 2026-09-29), kod storybook `v11.117.0`. Doğrulama 2026-10-20: her sayfa ve çapa `docs_search` ile soruldu, döndürülen `anchor_url` ve bölüm metni kanunun o bağlantıya dayandırdığı cümleyle karşılaştırıldı. MCP'nin yalnız giriş parçasını döndürdüğü [AI label — guidelines #in-containers](https://carbondesignsystem.com/building-blocks/core/components/ai-label/guidelines/#in-containers) bölümü canlı sayfadan okundu (talimatname §10.5). İndeksin ayrıca taşıdığı `/building-blocks/data-visualization/chart-design/...` kopyaları canlıda 404 verir; kanun talimatname §15'teki `/building-blocks/data-visualization/...` yolunu kullanır.

**Bileşenler: ilerleme, etiket, düğme**

| Konu | Sayfa ve çapa |
|---|---|
| İlerleme göstergesi (`.stepper`) | [Progress indicator — guidelines](https://carbondesignsystem.com/building-blocks/core/components/progress-indicator/guidelines/) · [Progress indicator — guidelines #when-to-use](https://carbondesignsystem.com/building-blocks/core/components/progress-indicator/guidelines/#when-to-use) · [Progress indicator — specifications #color](https://carbondesignsystem.com/building-blocks/core/components/progress-indicator/specifications/#color) · [Progress indicator — specifications #interactive-states](https://carbondesignsystem.com/building-blocks/core/components/progress-indicator/specifications/#interactive-states) · [Progress indicator — specifications #structure](https://carbondesignsystem.com/building-blocks/core/components/progress-indicator/specifications/#structure) · [Progress indicator — specifications #typography](https://carbondesignsystem.com/building-blocks/core/components/progress-indicator/specifications/#typography) |
| İlerleme çubuğu | [Progress bar — guidelines #when-not-to-use](https://carbondesignsystem.com/building-blocks/core/components/progress-bar/guidelines/#when-not-to-use) · [Progress bar — guidelines #content](https://carbondesignsystem.com/building-blocks/core/components/progress-bar/guidelines/#content) |
| Etiket | [Tag — guidelines #when-to-use](https://carbondesignsystem.com/building-blocks/core/components/tag/guidelines/#when-to-use) · [Tag — guidelines #when-not-to-use](https://carbondesignsystem.com/building-blocks/core/components/tag/guidelines/#when-not-to-use) · [Tag — guidelines #clickable-areas](https://carbondesignsystem.com/building-blocks/core/components/tag/guidelines/#clickable-areas) · [Tag — guidelines #operational-tag](https://carbondesignsystem.com/building-blocks/core/components/tag/guidelines/#operational-tag) · [Tag — guidelines #tag-colors](https://carbondesignsystem.com/building-blocks/core/components/tag/guidelines/#tag-colors) · [Tag — guidelines #sizing](https://carbondesignsystem.com/building-blocks/core/components/tag/guidelines/#sizing) · [Tag — specifications #size](https://carbondesignsystem.com/building-blocks/core/components/tag/specifications/#size) · [Tag — specifications #structure](https://carbondesignsystem.com/building-blocks/core/components/tag/specifications/#structure) · [Tag — specifications #typography](https://carbondesignsystem.com/building-blocks/core/components/tag/specifications/#typography) |
| Düğme (`.btn`, `.icon-btn`) | [Button — specifications #size](https://carbondesignsystem.com/building-blocks/core/components/button/specifications/#size) · [Button — specifications #ghost-button-color](https://carbondesignsystem.com/building-blocks/core/components/button/specifications/#ghost-button-color) · [Button — specifications #typography](https://carbondesignsystem.com/building-blocks/core/components/button/specifications/#typography) · [Button — specifications #primary-button-interactive-state-color](https://carbondesignsystem.com/building-blocks/core/components/button/specifications/#primary-button-interactive-state-color) · [Button — guidelines #a-single-high-emphasis-button](https://carbondesignsystem.com/building-blocks/core/components/button/guidelines/#a-single-high-emphasis-button) · [Button — guidelines #multiple-button-emphasis](https://carbondesignsystem.com/building-blocks/core/components/button/guidelines/#multiple-button-emphasis) · [Button — guidelines #button-sizes](https://carbondesignsystem.com/building-blocks/core/components/button/guidelines/#button-sizes) · [Button — guidelines #ghost-button](https://carbondesignsystem.com/building-blocks/core/components/button/guidelines/#ghost-button) · [Button — guidelines #label-alignment](https://carbondesignsystem.com/building-blocks/core/components/button/guidelines/#label-alignment) · [Button — guidelines #anatomy](https://carbondesignsystem.com/building-blocks/core/components/button/guidelines/#anatomy) (MCP: #4-icon-button) · [Button — specifications #button-structure](https://carbondesignsystem.com/building-blocks/core/components/button/specifications/#button-structure) · [Button — guidelines #main-elements](https://carbondesignsystem.com/building-blocks/core/components/button/guidelines/#main-elements) · [Button — guidelines #when-not-to-use](https://carbondesignsystem.com/building-blocks/core/components/button/guidelines/#when-not-to-use) |

**Bileşenler: bildirim, seçim, form, tablo ve diğerleri**

| Konu | Sayfa ve çapa |
|---|---|
| Bildirim (`.feedback`, `.callout`) | [Notification — guidelines #inline](https://carbondesignsystem.com/building-blocks/core/components/notification/guidelines/#inline) · [Notification — guidelines #callout](https://carbondesignsystem.com/building-blocks/core/components/notification/guidelines/#callout) · [Notification — specifications #inline](https://carbondesignsystem.com/building-blocks/core/components/notification/specifications/#inline) · [Notification — specifications #callout](https://carbondesignsystem.com/building-blocks/core/components/notification/specifications/#callout) · [Notification — accessibility #inline-and-toast](https://carbondesignsystem.com/building-blocks/core/components/notification/accessibility/#inline-and-toast) · [Notification — accessibility #actionable](https://carbondesignsystem.com/building-blocks/core/components/notification/accessibility/#actionable) · [Notification — accessibility #callout](https://carbondesignsystem.com/building-blocks/core/components/notification/accessibility/#callout) |
| Seçenek (`.opt`) | [Tile — specifications #selectable-tile-interactive-state-color](https://carbondesignsystem.com/building-blocks/core/components/tile/specifications/#selectable-tile-interactive-state-color) |
| Tanım balonu (`.def-pop`) ve ikon düğmesi ipucu | [Tooltip — accessibility #keyboard-interactions](https://carbondesignsystem.com/building-blocks/core/components/tooltip/accessibility/#keyboard-interactions) · [Tooltip — accessibility #annotate-the-text-for-the-tooltip](https://carbondesignsystem.com/building-blocks/core/components/tooltip/accessibility/#annotate-the-text-for-the-tooltip) |
| Form alanları | [Text input — guidelines #main-elements](https://carbondesignsystem.com/building-blocks/core/components/text-input/guidelines/#main-elements) · [Text input — specifications #text-input-color](https://carbondesignsystem.com/building-blocks/core/components/text-input/specifications/#text-input-color) · [Form — guidelines #best-practices-for-labels](https://carbondesignsystem.com/building-blocks/core/components/form/guidelines/#best-practices-for-labels) |
| Kaydırıcı | [Slider — guidelines #default-slider-anatomy](https://carbondesignsystem.com/building-blocks/core/components/slider/guidelines/#default-slider-anatomy) |
| Tablo (`.viz-table`) | [Data table — specifications #rows](https://carbondesignsystem.com/building-blocks/core/components/data-table/specifications/#rows) · [Data table — guidelines #header-and-row-height](https://carbondesignsystem.com/building-blocks/core/components/data-table/guidelines/#header-and-row-height) |
| Diğer bileşenler | [Popover — guidelines #corners](https://carbondesignsystem.com/building-blocks/core/components/popover/guidelines/#corners) · [AI label — guidelines #in-containers](https://carbondesignsystem.com/building-blocks/core/components/ai-label/guidelines/#in-containers) · [Accordion — guidelines #when-to-use](https://carbondesignsystem.com/building-blocks/core/components/accordion/guidelines/#when-to-use) |

**Temeller**

| Konu | Sayfa ve çapa |
|---|---|
| Tema ve mod | [Themes — overview #theming-applied](https://carbondesignsystem.com/building-blocks/foundations/themes/overview/#theming-applied) · [Themes — code #system-preferences](https://carbondesignsystem.com/building-blocks/foundations/themes/code/#system-preferences) · [Color — guidelines #creating-a-mode-control](https://carbondesignsystem.com/building-blocks/foundations/color/guidelines/#creating-a-mode-control) · [Color — guidelines #designing-for-inline-theming](https://carbondesignsystem.com/building-blocks/foundations/color/guidelines/#designing-for-inline-theming) · [Color — guidelines #consider-illustrations](https://carbondesignsystem.com/building-blocks/foundations/color/guidelines/#consider-illustrations) |
| Izgara ve oran | [2x Grid — overview #breakpoints](https://carbondesignsystem.com/building-blocks/foundations/2x-grid/overview/#breakpoints) · [2x Grid — overview #mini-unit](https://carbondesignsystem.com/building-blocks/foundations/2x-grid/overview/#mini-unit) · [2x Grid — overview #fluid-columns](https://carbondesignsystem.com/building-blocks/foundations/2x-grid/overview/#fluid-columns) · [2x Grid — guidelines #using-aspect-ratios](https://carbondesignsystem.com/building-blocks/foundations/2x-grid/guidelines/#using-aspect-ratios) · [2x Grid — guidelines #adaptive-aspect-ratios](https://carbondesignsystem.com/building-blocks/foundations/2x-grid/guidelines/#adaptive-aspect-ratios) · [2x Grid — guidelines #2x-grid-at-max-breakpoint](https://carbondesignsystem.com/building-blocks/foundations/2x-grid/guidelines/#2x-grid-at-max-breakpoint) |
| Tipografi | [Typography — type sets #base-type-sizes](https://carbondesignsystem.com/building-blocks/foundations/typography/type-sets/#base-type-sizes) · [Typography — type sets #body-styles](https://carbondesignsystem.com/building-blocks/foundations/typography/type-sets/#body-styles) · [Typography — type sets #fluid-heading-styles](https://carbondesignsystem.com/building-blocks/foundations/typography/type-sets/#fluid-heading-styles) · [Typography — overview #productive-and-expressive-type-sets](https://carbondesignsystem.com/building-blocks/foundations/typography/overview/#productive-and-expressive-type-sets) · [Typography — style strategies #using-expressive-moments-within-product-designs](https://carbondesignsystem.com/building-blocks/foundations/typography/style-strategies/#using-expressive-moments-within-product-designs) |
| Hareket | [Motion — overview #duration-tokens](https://carbondesignsystem.com/building-blocks/foundations/motion/overview/#duration-tokens) · [Motion — overview #productive-motion](https://carbondesignsystem.com/building-blocks/foundations/motion/overview/#productive-motion) · [Motion — overview #expressive-motion](https://carbondesignsystem.com/building-blocks/foundations/motion/overview/#expressive-motion) · [Motion — overview #adaptive-interface-motion-design](https://carbondesignsystem.com/building-blocks/foundations/motion/overview/#adaptive-interface-motion-design) |
| İkon ve piktogram | [Icons — code #usage](https://carbondesignsystem.com/building-blocks/foundations/icons/code/#usage) · [Icons — guidelines #touch-targets](https://carbondesignsystem.com/building-blocks/foundations/icons/guidelines/#touch-targets) · [Icons — guidelines #color](https://carbondesignsystem.com/building-blocks/foundations/icons/guidelines/#color) · [Pictograms — guidelines #sizing](https://carbondesignsystem.com/building-blocks/foundations/pictograms/guidelines/#sizing) · [Pictograms — guidelines #productive-versus-expressive](https://carbondesignsystem.com/building-blocks/foundations/pictograms/guidelines/#productive-versus-expressive) |
| Erişilebilirlik ve kontrast | [Accessibility — developers #give-decorative-images-an-empty-alt-attribute](https://carbondesignsystem.com/building-blocks/foundations/accessibility/developers/#give-decorative-images-an-empty-alt-attribute) · [Accessibility — developers #style-focus-indicators](https://carbondesignsystem.com/building-blocks/foundations/accessibility/developers/#style-focus-indicators) · [Accessibility — color #color-contrast](https://carbondesignsystem.com/building-blocks/foundations/accessibility/color/#color-contrast) (MCP: #use-of-color-and-color-blindness) |
| İçerik | [Content #content-foundations](https://carbondesignsystem.com/building-blocks/foundations/content/#content-foundations) |

**Kalıplar ve veri görselleştirme**

| Konu | Sayfa ve çapa |
|---|---|
| Durum ve rozet | [Status indicators #icon-indicator](https://carbondesignsystem.com/building-blocks/core/patterns/status-indicators/#icon-indicator) · [Status indicators #status-color-palette](https://carbondesignsystem.com/building-blocks/core/patterns/status-indicators/#status-color-palette) · [Status indicators #badge-indicator](https://carbondesignsystem.com/building-blocks/core/patterns/status-indicators/#badge-indicator) |
| Yükleme | [Loading #skeleton-states](https://carbondesignsystem.com/building-blocks/core/patterns/loading/#skeleton-states) |
| Veri görselleştirme | [Data visualization — color palettes #categorical-palettes](https://carbondesignsystem.com/building-blocks/data-visualization/color-palettes/#categorical-palettes) · [Data visualization — color palettes #alert-palette](https://carbondesignsystem.com/building-blocks/data-visualization/color-palettes/#alert-palette) · [Data visualization — legends #usage](https://carbondesignsystem.com/building-blocks/data-visualization/legends/#usage) (MCP: #color-and-texture) · [Data visualization — legends #color-and-texture](https://carbondesignsystem.com/building-blocks/data-visualization/legends/#color-and-texture) |

Kod olguları (MCP dışı; kurulu paketler `@carbon/react` 1.114.0, `@carbon/styles` 1.117.0, `@carbon/type` 11.69.0, `@carbon/layout` 11.61.0):

- `ProgressStep` `label` zorunludur (`label: node.isRequired`, `dashboard/node_modules/@carbon/react/lib/components/ProgressIndicator/ProgressIndicator.js:202`, @carbon/react 1.114.0); `spaceEqually` `vertical` ile birlikte yok sayılır (aynı dosya `:49`); `vertical` varsayılanı false. Adım `inline-size: 8rem; min-inline-size: 7rem` (`dashboard/node_modules/@carbon/styles/scss/components/progress-indicator/_progress-indicator.scss:43-44, 53`, @carbon/styles 1.117.0); derlenmiş CSS'te adım düğmesi 28 px.
- Düğme: productive etiket `body-compact-01` 14 px / 400, ikon 16 px (`dashboard/node_modules/@carbon/styles/scss/components/button/_mixins.scss:46, 93-97`, @carbon/styles 1.117.0); expressive etiket `body-compact-02` 16 px, ikon 20 px (`dashboard/node_modules/@carbon/styles/scss/components/button/_button.scss:431, 448-450`, @carbon/styles 1.117.0); React `isExpressive` (`dashboard/node_modules/@carbon/react/lib/components/Button/Button.d.ts:39`, @carbon/react 1.114.0).
- Inline bildirim v12 bayrağıyla `$border-radius-04` alır (`dashboard/node_modules/@carbon/styles/scss/components/notification/_inline-notification.scss:40-42`, @carbon/styles 1.117.0). Köşe token'ları `dashboard/node_modules/@carbon/layout/scss/generated/_border-radius.scss:12-42`, @carbon/layout 11.61.0.
- Tip ölçeği `@carbon/type` `scale` = [12, 14, 16, 18, 20, 24, …] (`dashboard/node_modules/@carbon/type/lib/index.js:168-176`, @carbon/type 11.69.0); `heading-05` 2rem / 400 / 1,25 (aynı dosya `:369-374`); 1,125rem taşıyan tip stili yok (52 token tarandı).
- `AspectRatio` oranları 16x9, 9x16, 2x1, 1x2, 4x3, 3x4, 3x2, 2x3, 1x1; varsayılan 1x1 (`dashboard/node_modules/@carbon/react/lib/components/AspectRatio/AspectRatio.js:30, 61-71`, @carbon/react 1.114.0).

MCP'de bulunamayanlar (kanun bunlarda kendi kararını yazar): ProgressIndicator'ın en çok adım sayısı ve sığmayan göstergenin davranışı (adım en az genişliği bulundu); dikey varyantın kullanım metni; satır uzunluğu kuralı; "bir ürün tek tema" ilkesi; 18 px'lik tip stili (ölçek adımı var).

### 10.3 Ölçüm kaynakları

Kanunun 1.0 sürümü 2026-10-19 tarihli beş ölçüm raporuna ve dört denetim turuna dayanır: modül şablonu görsel envanteri (Chromium 1.58.2, 28 segmentli örnek, akış benzetimi), edupedia eklentisi ve vendor kuralları, içerik ve görsel olanakları (canlı üç modül: mat7-tam-sayilar v4, fen7-turkiye-ve-uzay v3, sb7-milli-meseleler v3), pano ve talimatname (dashboard-dist derlemesi, gerçek QUIZ modülü), Carbon resmî ilkeleri; denetimde kapsayıcı ve medya sorgusu, `vh` geri beslemesi, satır ölçüsü, ilerleme göstergesi sığması, ekran 320 çerçevesi ve SVG metin boyu Chromium'da yeniden ölçüldü. Ham ölçümler oturum scratchpad'indedir ve repoya girmez; bir madde yeniden ölçülünce ölçüm betiği ve sonucu commit mesajında anılır.

## 11. Değişiklik kaydı

| Sürüm | Tarih | Değişiklik |
|---|---|---|
| 1.0 | 2026-10-19 | İlk sürüm. Beş madde (M1–M5, 60 madde), on iki adlı sapma (KS-1…KS-12), borç kaydı (KB-1…KB-46). Talimatname S14 bu yönde revize edildi ve alt metin aynı gün kanuna bağlandı: talimatname 2.0, anayasa 1.3, yüzey tasarımları, bileşen rehberi, `AGENTS.md`, `CLAUDE.md`, `tedy-carbon` (KB-34 kapandı) ve vendor referansları (KB-35 kapandı). `moduller.spec.ts:339-354` tersine yazılacak (KB-1). |
| 1.1 | 2026-10-20 | Talimatnameyle uyum turu (talimatname 2.1). §0.1'e artık kural: kanunun susduğu konuda modülde talimatname ve alttaki basamaklar geçer. Dayanaklardaki bayat talimatname alıntıları ve `T:` satır numaraları bölüm atfına çevrildi (M1.2, M1.9, M4.2, M4.5) ve talimatnamenin karşılık gelen kuralları eklendi (M1.4, M1.5, M1.6: [3.2-4], [3.2-13]–[3.2-15]; M2.2: §4.2, S12; M2.10: S26; M2.12: S17; M5.2: §5.8; M5.3: [3.8-3]). Hüküm değişiklikleri: M2.3 düşük kontrast türü (S27); M2.9 ağırlık 300/400/600 ve Carbon tip ölçeği; M2.15 zebra yok, sayı sütunu sağa yaslı ve tabular; §1 madde 6 `pic-*` ikon yerine yazılmaz. M2.13 Durum'u bant odağının token rolünü yazar. §7 KS ↔ S karşılıkları tamamlandı; §8 talimatname §12'nin modül eki oldu (§8.1'e vendor kapıları satırı, §8.3 madde 6'ya tarih ve commit); §9 girişine B ↔ KB eşlemesi; KB-32, KB-41 ve KB-43'ün yerleri genişledi; yeni KB-47 (Carbon dışı ağırlık ve ölçek dışı punto); §10.1'de kapanan satır commit de alır. §0.2 ve adlı sapmalar bu turda değişmedi. Aynı gün KB-1 (modülde tema düğmesi ve tema kaydı yok), KB-2 (aşama tabanlı Carbon ilerleme göstergesi, `meta.milestones` derleyici doğrulaması) ve KB-3 (akışta panonun sayfa zemini) şablonda kapandı. Carbon bağlantı turu (canlı denetim 2026-10-20, yalnız atıf): canlıda `id`'si olmayan MCP çapaları (`#4-icon-button`, `#progress-indicator`) ve anlamca yanlış `#contrast-ratios` çapası düzeltildi, doğrudan etiket ve satır içi tema canlı başlığa bağlandı, `#theming-applied` M4.1'den M4.3'e geçti, §10.2 sayfa listesini talimatname §15.6–15.7'ye bağladı. |
| 1.2 | 2026-10-23 | Beş borç kapandı (dal `modul-kalan-borclar`, `0388324`, `9107214`). KB-21 (M2.6, M2.7): sefer haritası kalktı; soru seti etiketi "Alıştırma", zor soru seçeneği "Daha zor bir soru" / "Daha zor bir cümle"; jargon etiketleri bölümün adına döndü ("Karma Geri-Getirme" → "Kontrol noktası", "Öz-açıklama" → "Kendi sözlerinle"; "Sayı doğrusu", "Cümle çözümleme" cümle düzeninde, M2.9); G-WELLBEING öğrenci yüzeyindeki rekabet çerçevesinde FAIL; `rewards` isteğe bağlı iç sayı, `badges` ve `meta.quest` şema hatası; panonun mod etiketi QUIZ → "Alıştırma" (İ9). KB-10, KB-11, KB-12 (M3.6–M3.8): `meta.assets[i].alt`, `.baslik`, `.alt_gerekce` alanları; alt metnin ad/sayı dayanağı `edupedia_derle`'de (G-GORSEL yerine derleyici hatası, gerekçeyle uyarı); raster figür `figure` + görünür `figcaption`; atıf `baslik — atıf`, yinelenen satır G-ATTRIB'de FAIL; ses varlığı görünür adlı oynatıcı (M5.14'ün bir kısmı; KB-44 açık). KB-5 (M5.6): şablonun SVG'si viewBox'ı kutunun genişliğine kurar; e2e ölçümü kuruldu. Yeni borç KB-48 (yazar SVG'sinin metni). §1 madde 5 ve 7 alanlara göre yeniden yazıldı (§1 ≤ 3300 bayt). Hüküm değişmedi; §0.2 ve adlı sapmalar değişmedi. |
| 1.3 | 2026-10-23 | Son incelemenin düzeltme turu (dal `modul-kalan-borclar`, `5683e6d`). Hüküm değişiklikleri: M3.6'nın dayanağı "figürün `caption`'ı" değil "kitabın kendi metni (figür altı yazısı ya da çerçeve sayfaları)"dır — Maarif `caption`'ı VLM betimidir (Kritik 1); M3.7 süs görselini (`alt=""`) altyazıdan ayırır (karar: `baslik` almaz, `figcaption` çizilmez). M2.7'ye "arayüz metni"nin sınırı yazıldı (şablon kromu + `title`/`kicker`/`instructions`/`selfAssess`; gövde anlatısı ve yazar katmanı taranmaz) ve eş anlamlılar (turnuva, düello, liderlik/skor/sıralama tablosu, yalın "Yarış"). M3.6'ya bilinen gevşeklik ve sıkılık (önek eşleşmesi, tire/nokta ayracı; `alt_gerekce` ile aşılır), M3.8'e varlık başına tek ad. M5.6'nın durum satırı ölçüme göre düzeltildi: etiket genişliği ölçülmüş Plex Sans glifleriyle, seyreltme yalnız gerçek çakışmada, nokta değerleri her genişlikte etiketli, çubuk grafik dikey sığıyorsa dikey; Carbon dayanağı Jina Reader ile okundu (Simple charts #bar-simple iki yönü tanır, seçim ölçütü vermez; Axes and labels #consistent-increments). §8.1'e yayında kapıların yeniden koşması. §1 madde 5 ve 7 buna göre (≤ 3300 bayt). §0.2 ve adlı sapmalar değişmedi. |
| 1.3.1 | 2026-10-23 | İkinci düzeltme turu (`e11479f`). M5.6 Durum: noktaların değerleri ve harf adları gerektiği kadar satıra iner (eski iki satırlı kural üçüncü komşuyu ilk satıra yazıyordu; ölçüm çerçeve 288 "−3 ↔ −2", 272 "−1 ↔ 0"), SVG yüksekliği satırla büyür; Denetim çerçeve 272/342 ve yoğun noktalı iki doğru. M2.7 Sınır: `interactiveLabel` ve `bins`/`params`/`columns` etiket dizileri arayüz metnidir; içerik etiketleri taranmaz. M3.7 Denetim: bilgi taşıyan `img` figcaption içindedir, süs görselininki altyazısızdır. `edupedia_kapsam` figür adayları `etiket` + `betim`. Yayında kapılar istisna atarsa yayın durur (test). Hüküm değişmedi; §1, §0.2 ve adlı sapmalar değişmedi. |
| 1.4 | 2026-10-24 | İki borç kapandı (dal `modul-kb44-48`, `30258d7`). KB-44 (M5.14): çerçevedeki her ikon düğmesi (ses, sesli okuma, tempo kapatma, kavram haritasında bağlantı kaldırma) 3rem, ikon 1.25rem, adı Carbon ikon ipucu ölçüsünde araç ipucunda (fare ve odak, Esc); "Oku" 48 px; yazarın ses varlığı sınıflı `audio`, denetimleri temayla; e2e kuruldu. Sınır: Carbon'un ses oynatıcısı yok, denetimleri tarayıcı çizer. KB-48 (M5.6): yol (a) — derleyici yazar SVG'sinde metin öğesini reddeder, rehber adı etiketli şemanın `labels`'ına ya da gövde metnine yönlendirir; yol (b) çakışma ve taşma yüzünden seçilmedi; altın örnek ve vendor rehberi buna göre. §1 madde 1'e yazar SVG'sinin metin taşımadığı, madde 8'den kapanmış KB-2'ye bayat atıf çıktı (§1 ≤ 3300 bayt; `akis` ilk parçası ≤ 8000). M5.3 ve M5.13 Durum, KB-4 satırı, §8.1 ve §8.2 güncellendi. Hüküm değişmedi; §0.2 ve adlı sapmalar değişmedi. |
