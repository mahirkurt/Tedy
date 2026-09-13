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
Kaynak: [2x Grid — Overview](https://carbondesignsystem.com/elements/2x-grid/overview/) ·
[2x Grid — Usage](https://carbondesignsystem.com/elements/2x-grid/usage/)

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
Kaynak: [Color — Usage](https://carbondesignsystem.com/elements/color/usage/) (3–4,
layer/elevation) · [Tile — Usage](https://carbondesignsystem.com/components/tile/usage/) (5,
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
Kaynak: [Spacing — Overview](https://carbondesignsystem.com/elements/spacing/overview/)

6. **Ölçü-sınırlı gövde metni.** Uzun gövde/anlatım metni 16 sütunun **alt-kümesini**
   kaplar (tipik 8–10 sütun sütun-genişliği), **tam-genişlik (edge-to-edge) değil** —
   okunabilir satır uzunluğu (~60–80 karakter) korunur. Metin-yoğun alanlarda (uzun
   `teach` bloğu, alıntı) geniş gutter/kenar boşluğu bilinçli bırakılır.
7. **Bölümler-arası nefes.** Bir bölümün **içi** yoğun olabilir (çok satırlı liste,
   yoğun tablo) — ama **sayfa asla duvardan-duvara değildir**: bölümler arası
   `--cds-spacing-07..10` (32–64px) ölçeğinde düşey ritim korunur. İç yoğunluk, dış
   nefesi telafi etmek için bir gerekçe değildir.

### 2.4 Hareket ve koreografi (8–9)
Kaynak: [Motion — Overview](https://carbondesignsystem.com/elements/motion/overview/) ·
[Motion — Choreography](https://carbondesignsystem.com/elements/motion/choreography/)
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
Kaynak: [Typography — Type Sets](https://carbondesignsystem.com/elements/typography/type-sets/) ·
[Typography — Style Strategies](https://carbondesignsystem.com/elements/typography/style-strategies/)
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
Kaynak: [Color — Usage](https://carbondesignsystem.com/elements/color/usage/)
(bu skill'in mevcut işlevsel-renk sözleşmesi: `color-system.md`)

11. **Aksan anlam taşır, süs değil.** Aksan rengi yalnız kategori/wayfinding anlamı
    taşıdığında kullanılır (segment türü, ders kimliği), **yapısal/dolgu** öğeler
    üstünde (bkz. `color-system.md` §2–3) — **birincil eylem her zaman Blue 60**
    (`--cds-button-primary`) kalır, kategori aksanına asla devredilmez (kontrast
    güvenliği; `carbon-child-system.md` §11). **Küçük metin düşük-kontrast aksan
    renginde asla yazılmaz** — aksan metin olarak taşınacaksa `--accent-strong`
    (resmî tag çifti) zorunludur.

### 2.7 Veri görselleştirme (12–13)
Kaynak: [Data Viz — Color Palettes](https://carbondesignsystem.com/data-visualization/color-palettes/) ·
[Data Viz — Chart Anatomy](https://carbondesignsystem.com/data-visualization/chart-anatomy/) ·
[Data Viz — Chart Types](https://carbondesignsystem.com/data-visualization/chart-types/)
(uygun grafik türü seçimi için Chart Types rehberine bakın)

12. **Sabit kategorik sıra + veri-tipine-göre palet.** Çok-serili (kategorik) bir
    grafik Carbon'un **sabit 14-renk sırasını** izler — sıra keyfi değildir, kategori
    kimliğinin bir parçasıdır:

    `Purple 70 → Cyan 50 → Teal 70 → Magenta 70 → Red 50 → Red 90 → Green 60 →
    Blue 80 → Magenta 50 → Yellow 50 → Teal 50 → Cyan 90 → Orange 70 → Purple 50`

    > **Kanonik kaynak (esas).** Yukarıdaki sıra yaklaşık bir sezgiseldir;
    > **kesin palet `@carbon/charts`'tır** ve **N-renk-başına optimize** edilmiştir
    > (14 sabit sıra değil) — kanonik white-teması dizisi `purple70 #6929c4 →
    > blue80 #002d9c → cyan50 #1192e8 → teal60 #007d79 → magenta70 #9f1853 …`
    > biçimindedir. Grafik rengi kararı için `carbon-sources.md` §4 (@carbon/charts
    > per-count palet) esas alınır; HEX değeri npm'den gelir.

    Sıralı (ordinal) veri **sequential/tek-tonlu** (ör. tek rengin açıktan koyuya
    tonları) bir palet kullanır; artı/eksi veya orta-noktalı veri (ör. bir eşiğin
    üstü/altı) **diverging** (iki uçtan orta-nötre giden) bir palet kullanır —
    kategorik paleti sıralı/diverging veri için kullanmak kategori-kodlama hatasıdır.
    > **Motor notu:** bu skill'in motoru bugün 5 pratik `--viz-1..5` yuvası taşır
    > (`color-system.md` §1) — bu, ≤5 serili basit grafikler için yeterlidir. Bu
    > maddenin 14-renk sabit sırası, **>5 kategori** gerektiğinde veya azami
    > Carbon-sadakati istendiğinde motorun palet genişlemesi için **hedef sırasıdır**;
    > mevcut 5-yuva implementasyonunu bugün değiştirmez, gelecekteki bir motor
    > genişletmesine normatif hedef verir.
13. **İçgörü-taşıyan başlık + tam anatomi.** Her grafik şu üç öğeyi eksiksiz taşır:
    (a) veriyi **özetleyen/içgörü-taşıyan** (qualitative) bir başlık — "Aylık Satışlar"
    gibi nötr bir etiket değil, "Satışlar Mart'ta %18 arttı" gibi bulguyu adlandıran
    bir başlık; (b) eksen başlıkları **birimleriyle** birlikte; (c) renk→anlam
    eşlemesini açıklayan bir **legend**. **Renk hiçbir zaman tek-kodlayıcı değildir** —
    legend/etiket/desen ile birlikte kullanılır (WCAG + CVD gereği; bkz.
    `color-system.md` §2 kural 3).

### 2.8 İkon ve piktogram (14–15)
Kaynak: [Icons — Usage](https://carbondesignsystem.com/elements/icons/usage/) ·
[Pictograms — Usage](https://carbondesignsystem.com/elements/pictograms/usage/)
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
| 12 | Grafik serileri keyfi/rastgele renk sırasında | Sabit 14-renk kategorik sıra; sıralı=sequential, ±=diverging |
| 13 | Grafik başlığı nötr etiket ("Veri 1"), legend yok | İçgörü-taşıyan başlık + birimli eksen + renk legend'ı |
| 14 | Aynı listede karışık ikon boyutları (16px + 32px) | Bağlam başına tek boyut; boyut komşu metinle eşleşir |
| 15 | Her madde işaretinde büyük expressive piktogram | Productive line stili varsayılan; expressive seyrek/büyük |

## 5. Kaynakça

- 2x Grid — Overview: https://carbondesignsystem.com/elements/2x-grid/overview/
- 2x Grid — Usage: https://carbondesignsystem.com/elements/2x-grid/usage/
- Color — Usage: https://carbondesignsystem.com/elements/color/usage/
- Motion — Overview: https://carbondesignsystem.com/elements/motion/overview/
- Motion — Choreography: https://carbondesignsystem.com/elements/motion/choreography/
- Typography — Type Sets: https://carbondesignsystem.com/elements/typography/type-sets/
- Typography — Style Strategies: https://carbondesignsystem.com/elements/typography/style-strategies/
- Data Visualization — Color Palettes: https://carbondesignsystem.com/data-visualization/color-palettes/
- Data Visualization — Chart Anatomy: https://carbondesignsystem.com/data-visualization/chart-anatomy/
- Data Visualization — Chart Types: https://carbondesignsystem.com/data-visualization/chart-types/
- Icons — Usage: https://carbondesignsystem.com/elements/icons/usage/
- Pictograms — Usage: https://carbondesignsystem.com/elements/pictograms/usage/
- Spacing — Overview: https://carbondesignsystem.com/elements/spacing/overview/
- Tile — Usage: https://carbondesignsystem.com/components/tile/usage/
