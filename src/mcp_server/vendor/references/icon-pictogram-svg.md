# İkon, Piktogram ve SVG Çizim Stratejisi

> `carbon-edupedia` **emoji kullanmaz**; tüm görsel anlam Carbon ikonları, Carbon
> piktogramları ve özgün SVG çizimlerle taşınır. Tüm görseller **satır içi**
> gömülür (çevrimdışı/güvenilir tek-dosya). Bu dosya üç kaynağı ve özgün çizim
> kurallarını tanımlar.
>
> **Kanonik kaynak (esas).** İkon/piktogram **ad ve SVG path kaynağı** IBM'in resmî
> **`@carbon/icons`** (v11.74.0 · 2584 ikon) ve **`@carbon/pictograms`** paketleridir
> (bkz. `carbon-sources.md` §3). Motor sprite'ının `ic-*`/`pic-*` id'leri iç
> anahtarlardır; her biri bir **kanonik Carbon ikonundan türetilir** (adlandırma
> kebab-case, varyant ayracı `--`; ör. `arrow--right`, `volume--up`). Yeni ikon
> eklerken kanonik addan türet — sprite→kanonik eşleme tablosu carbon-sources.md §3.

## İçindekiler
1. Üç görsel kaynağı ve ne zaman hangisi
2. Carbon Icons — sourcing ve satır-içi sprite kalıbı
3. Carbon Pictograms — sourcing ve kullanım
4. Özgün SVG illüstrasyon — Carbon-uyumlu çizim kuralları
5. Hazır geometrik ikon seti (şablona gömülü, güvenli)
6. Erişilebilirlik ve renk

---

## 1. Üç görsel kaynağı

| Kaynak | Ne | Boyut/karakter | Kullanım |
|---|---|---|---|
| **Carbon Icons** (`@carbon/icons`, MIT) | İşlevsel UI ikonu | 16/20/24/32px, tek renk, geometrik | Buton/durum/navigasyon: onay, kapat, ok, bilgi, yardım |
| **Carbon Pictograms** (`@carbon/pictograms`, MIT) | Kavramsal illüstrasyon | en az 48px (Kanun M2.11), ince çizgi, daha betimleyici | Segment başlığı, konu temsili: kitap, laboratuvar, roket; ödül piktogramı yok (M3.10) |
| **Özgün SVG** (elle) | Bespoke şema | Carbon görsel diline uygun | Kaynaktaki kavram diyagramı: etiketli hücre, su döngüsü, sayı doğrusu |

**Karar kuralı:** İşlev → Carbon Icon. Kavram/konu temsili → Carbon Pictogram.
Kaynağa özgü açıklayıcı diyagram (mevcut piktogram yetmiyor) → özgün SVG çiz.

## 2. Carbon Icons — sourcing ve satır-içi sprite

**Otoritatif kaynak:** `@carbon/icons` paketi. CDN ile tek tek erişim:
```
https://unpkg.com/@carbon/icons/svg/32/<isim>.svg
```
(örn. `.../svg/32/checkmark--filled.svg`, `.../svg/32/close.svg`,
`.../svg/32/arrow--right.svg`, `.../svg/32/help.svg`, `.../svg/32/view.svg`,
`.../svg/32/restart.svg`, `.../svg/32/information--filled.svg`,
`.../svg/32/warning--filled.svg`, `.../svg/32/play--filled--alt.svg`).

**Satır-içi sprite kalıbı (tercih edilen):** Tek-dosya güvenilirliği için ikonları
HTML başına bir gizli SVG sprite olarak göm, `<use>` ile çağır:
```html
<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <symbol id="ic-check" viewBox="0 0 32 32"><path d="..." fill="currentColor"/></symbol>
  <symbol id="ic-close" viewBox="0 0 32 32"><path d="..." fill="currentColor"/></symbol>
  <!-- ... -->
</svg>
<!-- kullanım -->
<svg class="cds-icon" aria-hidden="true"><use href="#ic-check"></use></svg>
```
- `fill="currentColor"` → ikon, kapsayıcının `color`'unu alır (durum/aksan rengi).
- Boyut CSS ile: `.cds-icon{width:1.25rem;height:1.25rem;display:inline-block}`.
- Carbon ikonları çoğunlukla 16/20/24/32 grid'inde tek-renk path; bu sprite'a
  birebir kopyalanır. Path verisini **doğrudan paketten** al; ezbere üretme.

> Doğru path verisi kritik (yanlış path bozuk ikon verir). Erişimin varsa CDN'den
> `web_fetch` ile gerçek SVG'yi çekip `<symbol>`'e göm. Erişim yoksa, §5'teki
> hazır geometrik set güvenli yedektir.

> **Gömülü otantik sprite:** `assets/module-template.html` **gerçek** Carbon
> varlıklarından üretilmiş tek bir satır-içi sprite taşır (8 `pic-*`, 26 `ic-*`).
> Üretim: `npm i @carbon/icons @carbon/pictograms` → her SVG'nin iç içeriği
> `<symbol id="ic-*|pic-*" viewBox="0 0 32 32">` olarak çıkarılır; tümü
> `currentColor` ile çalışır. **Yazar piktogram olarak yalnız şu anahtarları yazar**
> (Kanun §1 madde 6, M3.10): `pic-idea`, `pic-education`, `pic-rocket`, `pic-growth`,
> `pic-puzzle`, `pic-microscope`, `pic-magic`. `ic-*` piktogram yerine yazılmaz; ödül
> piktogramı ve ödül ikonları (kupa, yıldız) kullanılmaz. Bilinmeyen anahtar bugün
> sessizce `pic-education`'a düşer (borç KB-32).

## 3. Carbon Pictograms — sourcing ve kullanım

**Otoritatif kaynak:** `@carbon/pictograms` paketi.
```
https://unpkg.com/@carbon/pictograms/svg/<isim>.svg
```
(örn. `book`, `idea`, `rocket`, `microscope`, `chemistry`, `calculator`,
`globe`, `notebook`, `puzzle`, `growth`, `education`, `magic_wand`).

**Karakter:** İnce çizgili (≈2px stroke), tek renk veya çift-ton; en az 48 px
gösterilir (Kanun M2.11). Segment başlığının yanında ve konu kapağında; ödül ya da
rozet kartı yoktur (M2.7).
- Satır içi göm; renklendirmek için stroke/fill'i `currentColor`'a çevir ya da
  Carbon iki-ton kuralını koru.
- Piktogram **dekoratif** ise `aria-hidden="true"`; **bilgi taşıyorsa**
  `role="img"` + `<title>`.

> Piktogram dosyaları daha karmaşık path/stroke içerir; mutlaka paketten alınır.
> Ezbere piktogram path'i üretme — bozulur. Erişim yoksa §5 geometrik set + sade
> özgün SVG (§4) ile ikame et.

## 4. Özgün SVG illüstrasyon — Carbon-uyumlu çizim kuralları

Kaynaktaki bir kavram bespoke diyagram gerektirdiğinde (mevcut piktogram yetmez),
**Carbon görsel diline uygun** SVG çiz. Stil kuralları:

- **viewBox:** Net oran, örn. `0 0 480 320`; responsive `width:100%;height:auto`.
- **Stroke:** Tutarlı **2px** ana çizgi (`stroke-width:2`), `stroke-linecap:round`,
  `stroke-linejoin:round`. İnce ayrıntı 1px.
- **Renk:** Yalnız `var(--cds-*)` ve `var(--viz-*)` (Kanun §1 madde 1, M4.7). Çizgi
  `var(--cds-text-primary)` ya da `var(--viz-axis)`; dolgu `var(--cds-layer-02)` ya da
  `var(--viz-1..5)`. Ham hex, renk karıştırma ve gradyan yok; ders rengi yazar SVG'sine
  girmez (M1.5).
- **Geometri:** Geometrik, sade, kavramsal — fotogerçekçi değil. Carbon
  pictogram estetiğini taklit et (temiz formlar, yuvarlatılmış köşeler).
- **Etiketler:** Diyagram parçaları `<text>` ile etiketlenir; yazı tipini ve rengini CSS
  verir (`.viz text`). Metin ekranda en az 12 px çizilir (Kanun M5.6); etiket çizgileri
  ince (1px), `var(--viz-axis)`.
- **Boşluk:** Ferah; öğeler kalabalık değil (dış yük, ped İlke 5).

**Örnek iskelet (etiketli kavram diyagramı):**
```html
<svg class="viz" viewBox="0 0 480 320" role="img" aria-labelledby="t1 d1">
  <title id="t1">Bitki hücresi</title>
  <desc id="d1">Hücre duvarı, çekirdek ve kloroplastları gösteren basit şema.</desc>
  <rect x="40" y="40" width="400" height="240" rx="16"
        fill="var(--cds-layer-02)" stroke="var(--viz-2)" stroke-width="2"/>
  <circle cx="240" cy="160" r="44" fill="var(--cds-layer-01)" stroke="var(--cds-text-primary)" stroke-width="2"/>
  <text x="240" y="166" text-anchor="middle">Çekirdek</text>
  <!-- ek organeller + etiket çizgileri (1px, var(--viz-axis)) -->
</svg>
```
**Kural:** Çizilen şema kaynaktaki bilgiyi temsil eder; **kaynakta olmayan yapı/
etiket eklenmez** (SKILL.md §7). Şema bir "süs" değil, ikili kodlama aracıdır.

## 5. Hazır geometrik ikon seti (şablona gömülü, güvenli)

CDN/paket erişimi olmadığında veya hızlı/güvenli ikon gerektiğinde kullanılacak,
Carbon görsel diline uygun (currentColor, geometrik, 32 grid) **elle çizilmiş
güvenli** ikon seti. Bunlar byte-birebir Carbon ikonları değildir ama Carbon
estetiğiyle tutarlıdır ve doğru render olur. Şablonun sprite'ında bulunur:

| symbol id | Anlam | Kullanım |
|---|---|---|
| `ic-check` | onay | doğru cevap |
| `ic-close` | hata | yanlış cevap |
| `ic-arrow-right` | ileri | devam butonu |
| `ic-arrow-left` | geri | geri butonu |
| `ic-help` | yardım | ipucu |
| `ic-restart` | yeniden | tekrar dene |
| `ic-info` | bilgi | açıklama/ipucu |
| `ic-flag` | hedef | öğrenme hedefi |
| `ic-pause` | mola | brain-break |
| `ic-view` | göster | flashcard çevir |
| `ic-checkmark-outline` · `ic-incomplete` · `ic-circle-dash` | aşama durumu | yalnız motorun ilerleme göstergesi (Kanun M2.4); yazar kullanmaz |

(Path tanımları `assets/module-template.html` sprite'ında. Yazar yalnız sprite'taki
`id`'leri yazar; ödül ikonları kullanılmaz (Kanun M3.10). Yeni ikon şablon değişikliğidir.)

## 6. Erişilebilirlik ve renk

- **Dekoratif** görsel: `aria-hidden="true"` (durum ikonu yanında zaten metin var).
- **Bilgi taşıyan** görsel (diyagram, hotspot): `role="img"` + `<title>` (+`<desc>`).
- İkon **tek başına anlam taşımaz**: durum daima ikon **+ metin** (renk üçüncü
  kanal). Örn. yanlış = kırmızı + `ic-close` + "Tekrar dene".
- İkon yalnız Carbon boylarındadır (16, 20, 24, 32 px; durum ikonu ≥ 20 px); piktogram
  ≥ 48 px (Kanun M2.11).
- Kontrast: ikon rengi zemine karşı ≥3:1; aksan ikonları açık zeminde test edilir.
- Emoji **asla**; emoji görsel anlam taşımak için kullanılmaz (SKILL.md §3, kalite
  kapısı G-EMOJI).
