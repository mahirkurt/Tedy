# Carbon Estetik Mükemmelliği — 15 Madde Uzman-vs-Jenerik Checklist

> Bu referans, "Carbon token'ları kullanıyoruz" ile "Carbon'u **uzmanca** kullanıyoruz"
> arasındaki farkı 15 somut, **ikili-denetlenebilir** (evet/hayır) maddeyle tanımlar.
> Doğru token + jenerik kompozisyon hâlâ jeneriktir: bir modül `var(--cds-layer-01)`
> kullanıp yine de düz kenarlı, gölgeli, edge-to-edge, tek-easing'li bir kart yığını
> olabilir. Bu belge tam o boşluğu — token **varlığı** ile token'ların **bileşim
> grameri** arasındaki farkı — kapatır.
>
> **Kapsam ayrımı (önemli):** mevcut `G-CARBON` kapısı (`scripts/validate_module.py`)
> yalnız IBM Plex yüklü mü / çekirdek `--cds-*` token'lar tanımlı ve kullanımda mı
> denetler — token **varlığı**. Bu belge ve onun normatif ürünü olan **G-CARBON-GRID**
> kapısı (§3) token'ların **nasıl bileşime döküldüğünü** denetler: grid disiplini,
> en-boy oranı, derinlik, koreografi, tip-seti ayrımı, veri-viz sadakati, ikon/piktogram
> disiplini. Bir modül `G-CARBON`'dan PASS alıp yine de jenerik görünebilir — bu iki
> kapı **birbirini tamamlar**, çakışmaz.
>
> Token **değerleri** (hex/rem/ms) için otorite `carbon-child-system.md`'dir; bu belge
> onları **nasıl bir araya getireceğinizi** tanımlar — biri "ne", diğeri "nasıl".
> Kaynak: tasarım spec'i §4.2 + §10.2 (`docs/superpowers/specs/2026-07-06-edupedia-deep-upgrade-design.md`).

## 1. Amaç ve konumlandırma

Her madde şu testten geçer: **bir insan veya araç, üretilmiş HTML'e bakıp maddeye
uyulup uyulmadığını evet/hayır olarak karar verebilir mi?** Süsleme tercihleri
("daha güzel görünsün") değil, Carbon'un resmî kompozisyon kurallarına atıfla
somutlaştırılmış, kaynağı `carbondesignsystem.com` olan kurallardır.

Bu belge iki tüketiciye hizmet eder:
- **Emisyon-öncesi kontrol listesi** — bir modül üretilirken (özellikle görsel-yoğun
  `sim`/`conceptMap`/`vizChart`/hero içeren modüllerde) yazar bu 15 maddeyi tarar.
- **Normatif kaynak** — tasarım spec'i §6.2'de tanımlı **G-CARBON-GRID** doğrulayıcı
  kapısının (WARN→FAIL) tek doğruluk kaynağıdır (§3); ayrıca ileride eklenecek
  `module-auditor` ajanının (bkz. tasarım spec'i §7) dört denetim ekseninden biri
  doğrudan bu 15 maddedir — kapı henüz yazılmamış olsa bile bu belge onun sözleşmesidir.

## 2. 15 madde

### 2.1 Grid ve yerleşim (1–2)
Kaynak: [2x Grid — Overview](https://carbondesignsystem.com/building-blocks/foundations/2x-grid/overview/) ·
[2x Grid — Guidelines](https://carbondesignsystem.com/building-blocks/foundations/2x-grid/guidelines/)

1. **16-sütun (Lg) grid disiplini.** İçerik Carbon'un Lg breakpoint'inde 16 sütunlu
   grid konteynerine oturur; blok genişlikleri **tam-sütun span** olarak ifade edilir
   (`span-4`, `span-8`, `span-16` vb.) — ad-hoc `px`/`%` genişlik **yasak**. Daha dar
   breakpoint'lerde sütun sayısı azalır; disiplin aynı kalır (tam breakpoint tablosu
   için Overview sayfası).
2. **Carbon en-boy oranı.** Her media/figür/tile/hero öğesi Carbon'un altı standart
   en-boy oranından birini kullanır: **1:1, 2:1, 2:3, 3:2, 4:3, 16:9**. Serbest/rastgele
   oran (ör. `847×512`) jenerik göstergedir; CSS `aspect-ratio` özelliği bu altı
   değerden biriyle set edilir.

### 2.2 Derinlik ve katman (3–5)
Kaynak: [Color — Guidelines](https://carbondesignsystem.com/building-blocks/foundations/color/guidelines/) (3–4,
layer/elevation) · [Tile — Guidelines](https://carbondesignsystem.com/building-blocks/core/components/tile/guidelines/) (5,
bağlamsal token)

3. **Derinlik = layer adımı, gölge değil.** Bir öğenin "üstte" veya "içeride"
   hissettirilmesi `--cds-layer-01/02/03` basamaklarıyla (zemin rengi kontrastı)
   sağlanır — `box-shadow` ile değil. Carbon'un düz (flat), katmanlı estetiği budur.
4. **Drop-shadow yalnız floating/geçici yüzeyde.** Gölge **yalnızca** kullanıcı
   etkileşimiyle beliren/kaybolan geçici yüzeylerde kullanılır: tooltip, dropdown menü,
   modal, popover. **Statik bir kartta (segment gövdesi, teach kutusu, sabit tile) sıfır
   gölge** — bu tek başına en güçlü "jenerik Carbon" belirtisidir (bkz. §3, tek
   FAIL-seviyeli makine kuralı).
5. **Bağlamsal (contextual) layer/field/border token'ları.** Tekrar-kullanılır bir kart
   bileşeni, içine yerleştirildiği ebeveyn katmana **göreli** bir token seçer (Carbon'un
   `Layer`/contextual layering deseni: layer-01 içindeki bir kart layer-02 kullanır,
   aynı bileşen layer-02 içine taşınırsa layer-03'e geçer) — `--cds-layer-02` gibi
   **hardcoded, mutlak** bir basamağa asla kilitlenmez. Aksi hâlde bileşen bir üst
   katmana taşındığında kendi zeminiyle aynılaşıp görünmez olur.

### 2.3 Metin ölçüsü ve nefes (6–7)
Kaynak: [Spacing — Overview](https://carbondesignsystem.com/building-blocks/foundations/spacing/overview/)

6. **Ölçü-sınırlı gövde metni.** Uzun gövde/anlatım metni 16 sütunun **alt-kümesini**
   kaplar (tipik 8–10 sütun sütun-genişliği), **tam-genişlik (edge-to-edge) değil** —
   okunabilir satır uzunluğu (~60–80 karakter) korunur. Metin-yoğun alanlarda (uzun
   `teach` bloğu, alıntı) geniş gutter/kenar boşluğu bilinçli bırakılır.
7. **Bölümler-arası nefes.** Bir bölümün **içi** yoğun olabilir (çok satırlı liste,
   yoğun tablo) — ama **sayfa asla duvardan-duvara değildir**: bölümler arası
   `--cds-spacing-07..10` (32–64px) ölçeğinde düşey ritim korunur. İç yoğunluk, dış
   nefesi telafi etmek için bir gerekçe değildir.

### 2.4 Hareket ve koreografi (8–9)
Kaynak: [Motion — Overview](https://carbondesignsystem.com/building-blocks/foundations/motion/overview/) ·
[Motion — Choreography](https://carbondesignsystem.com/building-blocks/foundations/motion/choreography/)
(tam süre/easing token tablosu: `carbon-child-system.md` §6)

8. **Anlamlı easing seçimi (tek easing değil).** Beliren öğe **entrance** easing
   (`--cds-easing-entrance-*`), ayrılan/kaybolan öğe **exit** easing
   (`--cds-easing-exit-*`), yerinde kalan/durum değiştiren öğe **standard** easing
   (`--cds-easing-standard-*`) kullanır. Tüm hareketlere aynı tek eğriyi (ör. hepsi
   `ease-in-out`) uygulamak jenerik CSS'in imzasıdır — Carbon üç ailenin **anlamla**
   eşleştiğini varsayar.
9. **Koreografi bütçesi.** Bir liste/dizi (quiz şıkları, flashcard destesi, stepper
   düğümleri) ortaya çıkarken öğe başına **~20ms stagger**, **toplam <500ms**; tek bir
   geçişin süresi **100–300ms** bandında kalır (Carbon `moderate-01/02` = 150/240ms
   bu bandın içindedir). Daha uzun/daha stagger'sız bir "hepsi birden" geçiş, ya da
   500ms'yi aşan bir sahne-girişi, dikkat dağıtıcı ve DEHB için maliyetlidir.

### 2.5 Tipografi (10)
Kaynak: [Typography — Type Sets](https://carbondesignsystem.com/building-blocks/foundations/typography/type-sets/) ·
[Typography — Style Strategies](https://carbondesignsystem.com/building-blocks/foundations/typography/style-strategies/)
(tam ölçek tablosu: `carbon-child-system.md` §4)

10. **Expressive/productive karıştırılmaz.** Carbon iki tip-seti tanımlar: **expressive**
    (akışkan/fluid, büyük, ifade gücü yüksek — hero/modül başlığı) ve **productive**
    (yoğun, işlevsel, öngörülebilir — gövde metni, soru/quiz, form, tablo).
    **Expressive tip yalnız hero/başlıkta**; gövde ve quiz **her zaman productive**.
    **Tek bir bileşen** (ör. tek bir kart, tek bir soru bloğu) içinde iki tip-setini
    aynı anda kullanmak — ör. bir MCQ şıkkına akışkan/serif hero fontu uygulamak —
    kompozisyon disiplinini bozar; bu doc'un en doğrudan denetlenebilir maddelerinden
    biridir (§3).

### 2.6 Renk ve anlam (11)
Kaynak: [Color — Guidelines](https://carbondesignsystem.com/building-blocks/foundations/color/guidelines/)
(bu skill'in mevcut işlevsel-renk sözleşmesi: `color-system.md`)

11. **Aksan anlam taşır, süs değil.** Aksan rengi yalnız kategori/wayfinding anlamı
    taşıdığında kullanılır (segment türü, ders kimliği), **yapısal/dolgu** öğeler
    üstünde (bkz. `color-system.md` §2–3) — **birincil eylem her zaman Blue 60**
    (`--cds-button-primary`) kalır, kategori aksanına asla devredilmez (kontrast
    güvenliği; `carbon-child-system.md` §11). **Küçük metin düşük-kontrast aksan
    renginde asla yazılmaz** — aksan metin olarak taşınacaksa `--accent-strong`
    (= `--subject-text`, palet 70 / 30; tag çifti `--accent-tint`/`--accent-on`'dur)
    zorunludur. Kural panoda da istisnasızdır (2026-10-10, talimatname S35): panodaki
    asistanın öğretmen modu da birincil eylemi Carbon mavisinde tutar, ders rengi yalnız
    yüzeydedir; bugünkü `dashboard/src/asistan/ogretmenRenkleri.ts` yönlendirmesi borçtur
    (talimatname B68), adlı istisna değildir (§2.9).

### 2.7 Veri görselleştirme (12–13)
Kaynak: [Data Viz — Color Palettes](https://carbondesignsystem.com/building-blocks/data-visualization/color-palettes/) ·
[Data Viz — Chart Anatomy](https://carbondesignsystem.com/building-blocks/data-visualization/chart-anatomy/) ·
[Data Viz — Simple charts](https://carbondesignsystem.com/building-blocks/data-visualization/simple-charts/)
(uygun grafik türü seçimi için Simple charts rehberine bakın)

12. **Sabit kategorik sıra + veri-tipine-göre palet.** Çok-serili (kategorik) bir
    grafik Carbon'un **sabit 14-renk sırasını** izler — sıra keyfi değildir, kategori
    kimliğinin bir parçasıdır:

    `Purple 70 → Cyan 50 → Teal 70 → Magenta 70 → Red 50 → Red 90 → Green 60 →
    Blue 80 → Magenta 50 → Yellow 50 → Teal 50 → Cyan 90 → Orange 70 → Purple 50`

    > **Doğrulandı (2026-10-10).** Bu sıra Carbon sitesinin kategorik dizisidir ve
    > `@carbon/charts` 1.27.2 `scss/_color-palette.scss` içindeki `'14'` grubuyla aynıdır;
    > site renkleri "sırayla, kesin" uygulatır
    > (https://carbondesignsystem.com/building-blocks/data-visualization/color-palettes/#categorical-palettes).
    > Kategori sayısı öngörülebilirse sayıya özel gruplar (1–5 renk) diziyi geçersiz
    > kılabilir. Önceki "kanonik dizi purple70 → blue80 → cyan50 → teal60…" iddiası
    > yanlıştı: o dört renk 1-renk grubunun dört *seçeneğidir*, bir dizi değildir.
    > HEX değeri npm'den (`@carbon/colors`) gelir; ayrıntı `carbon-sources.md` §4.
    >
    > **TEDY sınırı (S19).** 14'lü dizi Red 50, Red 90, Green 60, Yellow 50 ve Orange 70
    > içerir; Tedy'de kırmızı, yeşil, sarı ve turuncu anlam renkleridir
    > (`tedy-integration.md` §3.1 "Ayrılmış renkler", Carbon uyarı paleti:
    > https://carbondesignsystem.com/building-blocks/data-visualization/color-palettes/#alert-palette).
    > Modül grafiğinde seri rengi bu ailelerden seçilmez;
    > 5 seriyi aşan grafik doğrudan etiket ya da desenle ayrışır.

    Sıralı (ordinal) veri **sequential/tek-tonlu** (ör. tek rengin açıktan koyuya
    tonları) bir palet kullanır; artı/eksi veya orta-noktalı veri (ör. bir eşiğin
    üstü/altı) **diverging** (iki uçtan orta-nötre giden) bir palet kullanır —
    kategorik paleti sıralı/diverging veri için kullanmak kategori-kodlama hatasıdır.
    > **Motor notu:** motor bugün 5 `--viz-1..5` yuvası taşır (`color-system.md` §7).
    > Bu yuvalar Carbon'un kategorik tonlarından **anlam renklerini dışarıda bırakan bir
    > TEDY alt kümesidir** (S19), resmî bir Carbon grubu değildir: açık temada
    > purple70 · blue80 · cyan50 · teal60 · magenta70, `@carbon/charts`'ın iki 5-renk
    > grubundan hiçbirine uymaz (ikisi de Red 90 içerir). Yuvaların yeniden seçimi bir
    > şablon değişikliğidir — **açık madde**; bu belge şablonu değiştirmez.
13. **İçgörü-taşıyan başlık + tam anatomi.** Her grafik şu üç öğeyi eksiksiz taşır:
    (a) veriyi **özetleyen/içgörü-taşıyan** (qualitative) bir başlık — "Aylık Satışlar"
    gibi nötr bir etiket değil, "Satışlar Mart'ta %18 arttı" gibi bulguyu adlandıran
    bir başlık; (b) eksen başlıkları **birimleriyle** birlikte; (c) renk→anlam
    eşlemesini açıklayan bir **legend** (yalnız çok seride; tek seride lejant yok, veri
    doğrudan etiketlenir — §2.9). **Renk hiçbir zaman tek-kodlayıcı değildir** —
    legend/etiket/desen ile birlikte kullanılır (WCAG + CVD gereği; bkz.
    `color-system.md` §2 kural 3).

### 2.8 İkon ve piktogram (14–15)
Kaynak: [Icons — Guidelines](https://carbondesignsystem.com/building-blocks/foundations/icons/guidelines/) ·
[Pictograms — Guidelines](https://carbondesignsystem.com/building-blocks/foundations/pictograms/guidelines/)
(envanter/gömme mekaniği: `icon-pictogram-svg.md`)

14. **İkon boyut disiplini.** Bir bağlam içinde (ör. tek bir buton grubu, tek bir liste)
    **tek bir ikon boyutu** kullanılır — Carbon'un dört standart boyutundan biri
    (**16/20/24/32px**), tam-piksel (kesirli/ölçeklenmiş değil). İkonlar **monokromatik**
    olup `currentColor` ile zemine göre **≥4.5:1** kontrast taşır. Boyut, komşu metinle
    **eşleşir**: 16–20px ikon ↔ 14–16px metin (küçük metin yanına 32px ikon, ya da
    büyük başlık yanına 16px ikon — ölçek uyumsuzluğu jenerik göstergedir).
15. **Piktogram disiplini: expressive seyrek, productive varsayılan.** Büyük, ifade
    gücü yüksek (expressive) piktogramlar **büyük ve seyrek** kullanılır — segment
    başına bir tane, dikkat çekmesi gereken tek bir odak noktasında (ör. bir bölümün
    açılış ikonu). **Varsayılan/tekrarlayan** her yerde Carbon'un **line stili**
    (productive, ince çizgi, küçük) kullanılır. Her satırda/her madde işaretinde bir
    expressive piktogram = aşırı-doygunluk, dikkat dağıtıcı gürültü.

### 2.9 Carbon doğrulamalı inceltmeler ve adlı istisnalar (2026-10-10)

Aşağıdakiler 15 maddeyi Carbon'un güncel rehberiyle inceltir (Carbon MCP `docs_search`
`anchor_url`'ları ve 2026-10-10 site taramasıyla doğrulandı; kanonik kılavuz
`docs/tedy-ui-ux-talimatnamesi.md` §9 ve §11). Madde numaraları değişmez.

- **Madde 1 — kırılımlar ve mini birim.** Carbon kırılımları: sm 320 · md 672 · lg 1056 ·
  xlg 1312 · max 1584 px (…/foundations/2x-grid/overview/#breakpoints). 2x Grid'in temel
  birimi **8 px mini birimdir**; 2 px yalnız en küçük aralık adımıdır
  (…/foundations/2x-grid/overview/#mini-unit). Bugün motor tek 880 px okuma sütunu ve özel
  560/400 px kırılımları kullanır, pano 672 px'te geçer; motorun 16 sütuna geçmesi açık maddedir.
- **Madde 2 — en-boy oranı.** Carbon uyarlanır ve seyrek oranlara da izin verir; oran kırılımda
  değişebilir (…/foundations/2x-grid/guidelines/#adaptive-aspect-ratios). "Serbest oran =
  jenerik" hükmü Carbon'dan **katıdır**; bilinçli bir edupedia sıkılaştırması olarak okunur.
- **Madde 4 — yüzen yüzey.** Carbon gölgesi `0 2px 6px 0 rgba(0,0,0,.2)` yalnız üstte açılan
  menü/popover içindir (…/core/components/dropdown/guidelines/#elevation); popover köşesi
  2 px'tir (…/core/components/popover/guidelines/#corners). *Adlı Tedy istisnaları:*
  `.topbar` ve `.stage` açık temada `--tedy-shadow-card` taşır (G-CARBON-GRID seçici listesi
  dışında, `tedy-integration.md` §4); tanım popover'ı ve satır içi terim vurgusu (`mark.term`) 4 px köşe kullanır.
- **Madde 5 — bağlamsal token doğru okunuşu.** Carbon v11'de numarasız adlar (`--cds-layer`,
  `--cds-layer-hover`, `--cds-field`, `--cds-border-subtle`, `--cds-border-strong`) **bağlamsal
  token'dır**: değerlerini çevreleyen `Layer` iç içeliği belirler, numarayı düşürmek bir
  katman-seti token'ını bağlamsal yapar (…/foundations/color/guidelines/#designing-for-contextual-tokens).
  "Eski takma ad" değildirler. Motor bugün bunları sabit değere bağlar
  (`--cds-border-subtle: var(--cds-border-subtle-00)`) ve `var(--cds-layer-02)`'yi 31 yerde
  mutlak kullanır — **açık madde** (şablon değişikliği).
- **Madde 8–9 — mikro etkileşim.** Hover, basma ve geçiş geri bildirimi kullanıcı girdisinde
  ease-out (entrance) eğrisiyle, 90–120 ms statik sürede biter; `duration-fast-01` (70 ms)
  düğme/anahtar, `duration-fast-02` (110 ms) solma içindir
  (…/foundations/motion/overview/#duration-tokens). Motorun `--dur-fast` (110 ms) bandın
  içindedir ama standard eğri kullanır. "+N XP" yükselişi `duration-slow-02` (700 ms) koşar ve
  G-CARBON-GRID onu görmez (yalnız literal `Nms` okur); 2026-10-10'dan beri adlı istisna değil,
  kalkacak bir ödül hareketidir (talimatname S43, borç B73).
- **Madde 10 — tip seti.** Productive set ürün arayüzü, expressive set editoryal sayfalar
  içindir (…/foundations/typography/style-strategies/#overview). Modülde expressive/fluid
  stil yalnız kap dışı, sayfa düzeyi başlıkta kullanılır; kart, seçenek ya da soru bloğu içinde
  asla. `mathExpr` ve `.lead` çekme alıntısındaki Plex Serif bilinçli bir set harmanlamasıdır,
  madde 10'un "MCQ şıkkında serif hero" anti-kalıbı değildir.
- **Madde 11 — tek yüksek vurgulu düğme.** Bir düzen ya da düğme grubunda tek yüksek vurgulu
  (birincil) düğme bulunur; kalan eylemler daha düşük vurgudadır
  (…/core/components/button/guidelines/#multiple-button-emphasis). Kontrol + İleri çifti
  buna uyar.
- **Madde 12 — grafik rengi ve kontrastı.** Grafik öğeleri ve bilgi taşıyan SVG parçaları
  zemine karşı ≥ 3:1 taşır (…/foundations/color/overview/#contrast-ratios). Açık temada
  `--viz-sun` (`#f1c21b`, 1,68:1) ve `--viz-cloud` (`#c1c7cd`, 1,70:1) bunu geçemez: dolgu
  olarak kullanıldıklarında 3:1'i geçen bir kontur ya da etiket eşlik eder — **açık madde**.
- **Madde 13 — lejant, doğrudan etiket, boşluk.** Mümkünse lejant kullanılmaz, veri doğrudan
  etiketlenir; **tek veri kategorisi olan grafiğe lejant konmaz**
  (…/data-visualization/legends/#usage). Çubuk/alan ekseni sıfırdan başlar
  (…/data-visualization/axes-and-labels/#when-starting-at-non-zero-is-bad). Eksik veri
  **asla** enterpolasyonla doldurulmaz ve sıfır çizilmez; boşluğun başı ve sonu etiketlenir
  (…/data-visualization/axes-and-labels/#gaps-in-data). Motorun `vizChart`'ı eksik değeri
  bugün 0 çizer — **açık madde** (B52, şablon değişikliği); yazar eksik noktayı veri dizisine
  koymaz, `desc`/`caption`'da "veri yok" der.
- **Madde 14 — ikon rengi ve hedef.** İkon tek renklidir, komşu metnin rengini taşır ve
  4,5:1 sağlar (…/foundations/icons/guidelines/#color); etkileşimli ikonun dokunma hedefi
  ≥ 44 px'tir (…/foundations/icons/guidelines/#touch-targets; Tedy `--tap: 48px`).
  `icon-pictogram-svg.md` §6'daki 3:1 yalnız bilgi taşıyan grafik parçası içindir.
  Motor ikonları bugün kesirli rem boyutlarındadır — açık madde.
- **Madde 15 — piktogram asgarisi.** Piktogram en az 48 px'tir
  (…/foundations/pictograms/guidelines/#sizing). Motorun bölüm başı (32 px) ve kart (30 px)
  piktogramları bunun altındadır — borç, şablon değişikliği.
- **Durum göstergesi.** Carbon durumu dört öğeyle kurar (ikon, şekil, renk, etiket) ve WCAG
  için **en az üçünü** ister (…/core/patterns/status-indicators/#visual-guidance); renk tek
  başına durum söylemez (`color-system.md` §2 kural 3). Yükleniyor hâli iskelet kalıbıdır
  (…/core/patterns/loading/#skeleton-states).
- **Callout ve ilerleme göstergesi.** Callout statik, bağlamsal ve kapatılamazdır; 3 px sol
  kenar, en az 48 px yükseklik (…/core/components/notification/guidelines/#callout).
  Şablonun 4 px kenarı ve 8 px köşesi adlı Tedy sapmasıdır. İlerleme göstergesinde
  tamamlanan ve geçerli adım `$interactive`, etkin olmayan çizgi `$border-subtle`'dır
  (…/core/components/progress-indicator/specifications/#color); stepper'ın `button-primary`
  dolgusu g100'de farklı çizer.
- **Tema ve marka bölgesi.** Carbon, kullanıcı seçimi yoksa işletim sistemi temasına uyar
  (…/foundations/themes/code/#system-preferences); Tedy panosu tek g10'dur ve modül panonun
  temasını alır — kullanıcıya ait **açık ürün kararı** (S14). Lacivert Tedy bandı, açık sayfada
  Carbon'un "yüksek kontrast anı" (…/foundations/color/overview/#high-contrast-moments)
  biçiminde adlı bir marka bölgesidir.

`…/` kısaltması `https://carbondesignsystem.com/building-blocks/` demektir. Bir Carbon
iddiası yazmadan önce Carbon MCP ile doğrulanır: rehber ve `anchor_url` için `docs_search`,
kanonik ikon/piktogram/bileşen kodu için `code_search`, grafik için `get_charts`, token ve
erişilebilirlik denetimi için `code_audit` (kılavuz §10). Değerin kaynağı yine npm
`@carbon/*`'tır (`carbon-sources.md`).

## 3. Makine-denetlenebilir alt-küme (G-CARBON-GRID)

Yukarıdaki 15 maddenin tamamı **kavramsal olarak** ikili-denetlenebilir olsa da, bir
kısmı statik metin/regex/heuristik ile güvenilir biçimde denetlenebilirken bir kısmı
(ör. "başlık gerçekten içgörü taşıyor mu", "aksan gerçekten anlam taşıyor mu")
**anlam/yargı** gerektirir ve şimdilik `module-auditor` ajanının (spec §7)
insan-benzeri değerlendirmesine bırakılır. **G-CARBON-GRID** kapısı (spec §6.2;
WARN→FAIL) aşağıdaki **dört maddenin** **statik-metin-denetlenebilir** alt-kümesini
kapsar — bu tablo Task 7'nin (kapı implementasyonu) tam olarak neyi denetleyeceğinin
normatif sözleşmesidir (madde 10 aday olarak değerlendirilmiş, ancak Task 7'de
`module-auditor`'a devredilmiştir — gerekçe için tablo altındaki Not'a bakın):

| Madde | Kural | Heuristik yaklaşım | Sonuç sınıfı |
|---|---|---|---|
| **1** — Grid | 16-sütun grid konteyneri | HTML'de `cds--grid`/`carbon-grid` sınıfı **veya** CSS'te `grid-template-columns` varlığı; üçü de yoksa ad-hoc genişlik riski | WARN (yokluk) |
| **2** — En-boy oranı | Media/figür/tile Carbon oranı kullanır | CSS'te `aspect-ratio` özelliği varlığı (altı standart değerden biri) | WARN (yokluk) |
| **3/4** — Layer-elevation | Derinlik layer'la, gölge yalnız floating'de | Regex: statik kart/segment/tile/teach seçicilerinde (`.card`,`.seg`,`.tile`,`.teach`) gerçek (non-inset) `box-shadow` **≠ none** araması — sıfır-blur `inset` gölgeler (border simülasyonu, ör. `inset 0 0 0 2px`) kasıtlı olarak dışlanır (derinlik/floating hissi vermez, bkz. `gate_carbon_grid` docstring) | **FAIL** (tek ağır-ihlal seviyeli madde — statik kartta gölge, en güçlü jenerik belirtisi) |
| **9** — Koreografi zamanlaması | Stagger ~20ms, toplam <500ms, tek geçiş 100–300ms | Regex: `transition`/`animation` bildirimlerinde `Nms` süre yakala; `N>500` bulunursa bütçe aşımı | WARN (aşım) |

**Not — madde 6 (ölçü-sınırlı gövde metni) ve madde 10 (tip-seti karışımı) neden bu
alt-kümede değil:** tasarım spec'i §6.2'nin taslak nesir metni "edge-to-edge gövde
metni"ni bir ağır-ihlal örneği olarak anar; ancak bunu güvenilir biçimde tespit etmek
**render edilmiş sütun genişliğinin hesaplanmasını** gerektirir — statik metin/regex
taraması bunu yapamaz. Bu yüzden madde 6, G-CARBON-GRID'in ilk sürümünün **dışında**
tutulmuştur. Madde 10 (expressive/productive tip-seti karışımı) de **module-auditor'a
devredildi** (regex ile güvenilir denetlenemez): aynı bileşen/kart alt-ağacında hem
expressive tipografi sınıfı/token'ı (ör. `--fs-display`, `.hero`, serif akışkan başlık)
hem de productive gövde/soru sınıfının **birlikteliğini** güvenilir tespit etmek **DOM
iç-içelik/düzen muhakemesi** gerektirir — CSS metin sırası DOM ağacındaki gerçek
ebeveyn-çocuk ilişkisini garanti etmediğinden saf regex bunu yapamaz. Her iki madde de
`module-auditor` ajanının görsel/semantik değerlendirmesine bırakılmıştır. Kalan
maddeler (beşinci, yedinci, sekizinci, on birinci ilâ on beşinci arası) de aynı nedenle
(statik regex'in aşamayacağı bir muhakeme gerektirdikleri için) şimdilik ajan-denetimli
kalır; bu tablo yalnız **bugün** regex/heuristik ile güvenilir yakalanabilecek **dört**
maddeyi listeler — küme zamanla genişleyebilir, daralmaz.

## 4. Jenerik belirtiler → uzman düzeltme (hızlı karşılaştırma)

| # | Jenerik (amatör) belirti | Uzman (Carbon-sadık) düzeltme |
|---|---|---|
| 1 | Blok genişliği `width:63%` gibi ad-hoc bir değer | `span-10` gibi tam-sütun span |
| 2 | Görsel kutusu rastgele oran (`847×512`) | Altı standart orandan biri (`aspect-ratio:16/9` vb.) |
| 3 | Derinlik `box-shadow:0 4px 8px …` ile taklit edilir | Derinlik `--cds-layer-01/02/03` basamağıyla |
| 4 | Statik kartta kalıcı gölge | Statik kartta 0 gölge; gölge yalnız tooltip/menu/modal |
| 5 | Kart her yerde hardcoded `--cds-layer-02` | Kart ebeveyn katmana göreli (bağlamsal) token seçer |
| 6 | Gövde metni tam genişlik (edge-to-edge) | Gövde metni 8–10 sütun ölçüsünde, geniş gutter |
| 7 | Sayfa yoğun bölümlerde duvardan-duvara | Bölümler arası düşey ritim (spacing-07..10) her zaman |
| 8 | Her yerde aynı tek `ease-in-out` | Entrance/exit/standard — anlamla eşleşen 3 aile |
| 9 | Liste tek seferde/gecikmesiz belirir ya da >500ms sürer | ~20ms/öğe stagger, toplam <500ms, tek geçiş 100–300ms |
| 10 | Bir MCQ şıkkına akışkan/serif hero fontu | Gövde/quiz her zaman productive; expressive yalnız hero |
| 11 | Kategori aksanı birincil butona da uygulanır | Birincil eylem her zaman Blue 60; aksan yalnız yapısal |
| 12 | Grafik serileri keyfi/rastgele renk sırasında | Carbon kategorik sırası (anlam renkleri hariç, S19); sıralı=sequential, ±=diverging |
| 13 | Grafik başlığı nötr etiket ("Veri 1"); eksik değer 0 çizilir | İçgörü-taşıyan başlık + birimli eksen + doğrudan etiket (çok seride legend); boşluk etiketlenir |
| 14 | Aynı listede karışık ikon boyutları (16px + 32px) | Bağlam başına tek boyut; boyut komşu metinle eşleşir |
| 15 | Her madde işaretinde büyük expressive piktogram | Productive line stili varsayılan; expressive seyrek/büyük |

## 5. Kaynakça

Güncel yol biçimi `https://carbondesignsystem.com/building-blocks/...`'dir; eski `/elements/...`,
`/components/...` ve `/data-visualization/...` yolları yönlendirilir ve eskimiştir; "Usage"
sekmeleri artık "Guidelines"tır (2026-10-10).

- 2x Grid — Overview: https://carbondesignsystem.com/building-blocks/foundations/2x-grid/overview/
- 2x Grid — Guidelines: https://carbondesignsystem.com/building-blocks/foundations/2x-grid/guidelines/
- Color — Overview: https://carbondesignsystem.com/building-blocks/foundations/color/overview/
- Color — Guidelines: https://carbondesignsystem.com/building-blocks/foundations/color/guidelines/
- Themes — Code: https://carbondesignsystem.com/building-blocks/foundations/themes/code/
- Motion — Overview: https://carbondesignsystem.com/building-blocks/foundations/motion/overview/
- Motion — Choreography: https://carbondesignsystem.com/building-blocks/foundations/motion/choreography/
- Typography — Type Sets: https://carbondesignsystem.com/building-blocks/foundations/typography/type-sets/
- Typography — Style Strategies: https://carbondesignsystem.com/building-blocks/foundations/typography/style-strategies/
- Data Visualization — Color Palettes: https://carbondesignsystem.com/building-blocks/data-visualization/color-palettes/
- Data Visualization — Chart Anatomy: https://carbondesignsystem.com/building-blocks/data-visualization/chart-anatomy/
- Data Visualization — Simple charts: https://carbondesignsystem.com/building-blocks/data-visualization/simple-charts/
- Data Visualization — Axes and labels: https://carbondesignsystem.com/building-blocks/data-visualization/axes-and-labels/
- Data Visualization — Legends: https://carbondesignsystem.com/building-blocks/data-visualization/legends/
- Icons — Guidelines: https://carbondesignsystem.com/building-blocks/foundations/icons/guidelines/
- Pictograms — Guidelines: https://carbondesignsystem.com/building-blocks/foundations/pictograms/guidelines/
- Spacing — Overview: https://carbondesignsystem.com/building-blocks/foundations/spacing/overview/
- Tile — Guidelines: https://carbondesignsystem.com/building-blocks/core/components/tile/guidelines/
- Button — Guidelines: https://carbondesignsystem.com/building-blocks/core/components/button/guidelines/
- Notification (callout) — Guidelines: https://carbondesignsystem.com/building-blocks/core/components/notification/guidelines/
- Popover — Guidelines: https://carbondesignsystem.com/building-blocks/core/components/popover/guidelines/
- Status indicators: https://carbondesignsystem.com/building-blocks/core/patterns/status-indicators/
- Loading: https://carbondesignsystem.com/building-blocks/core/patterns/loading/
