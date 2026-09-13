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
| **Carbon Icons** (`@carbon/icons`, MIT) | İşlevsel UI ikonu | 16/20/24/32px, tek renk, geometrik | Buton/durum/navigasyon: onay, kapat, ok, yıldız, fikir |
| **Carbon Pictograms** (`@carbon/pictograms`, MIT) | Kavramsal illüstrasyon | ~48px+, ince çizgi, daha betimleyici | Segment başlığı, ödül, konu temsili: kitap, laboratuvar, roket |
| **Özgün SVG** (elle) | Bespoke şema | Carbon görsel diline uygun | Kaynaktaki kavram diyagramı: etiketli hücre, su döngüsü, sayı doğrusu |

**Karar kuralı:** İşlev → Carbon Icon. Kavram/konu temsili → Carbon Pictogram.
Kaynağa özgü açıklayıcı diyagram (mevcut piktogram yetmiyor) → özgün SVG çiz.

## 2. Carbon Icons — sourcing ve satır-içi sprite

**Otoritatif kaynak:** `@carbon/icons` paketi. CDN ile tek tek erişim:
```
https://unpkg.com/@carbon/icons/svg/32/<isim>.svg
```
(örn. `.../svg/32/checkmark--filled.svg`, `.../svg/32/close.svg`,
`.../svg/32/arrow--right.svg`, `.../svg/32/star--filled.svg`, `.../svg/32/idea.svg`,
`.../svg/32/trophy.svg`, `.../svg/32/restart.svg`, `.../svg/32/information--filled.svg`,
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

> **v1.1.0 — gömülü otantik sprite:** `assets/module-template.html` artık
> **gerçek** Carbon varlıklarından üretilmiş tek bir satır-içi sprite taşır:
> 15 ikon (`@carbon/icons`) + 8 piktogram (`@carbon/pictograms`), toplam 23 sembol.
> Üretim: `npm i @carbon/icons @carbon/pictograms` → her SVG'nin iç içeriği
> `<symbol id="ic-*|pic-*" viewBox="0 0 32 32">` olarak çıkarılır. Tümü
> `currentColor` ile çalışır (ikonlar fill-inherit; piktogramlar fill-inherit
> ince-çizgi). Gömülü anahtarlar: `ic-check, ic-close, ic-arrow-right/left,
> ic-chevron-right, ic-star, ic-info, ic-help, ic-restart, ic-renew, ic-flag,
> ic-pause, ic-view, ic-light, ic-moon`; `pic-idea, pic-education, pic-rocket,
> pic-growth, pic-trophy, pic-puzzle, pic-microscope, pic-magic`.

## 3. Carbon Pictograms — sourcing ve kullanım

**Otoritatif kaynak:** `@carbon/pictograms` paketi.
```
https://unpkg.com/@carbon/pictograms/svg/<isim>.svg
```
(örn. `book`, `idea`, `rocket`, `microscope`, `chemistry`, `calculator`,
`globe`, `notebook`, `trophy`, `puzzle`, `growth`, `education`, `magic_wand`).

**Karakter:** İnce çizgili (≈2px stroke), tek renk veya çift-ton; ~48–64px
gösterilir. Segment başlığının yanında, ödül/rozet kartlarında, konu kapağında.
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
- **Renk:** Yalnız Carbon paletinden (`carbon-child-system.md` §2–3). Çizgi
  `--cds-text-primary` (#161616) veya aksan; dolgu açık tint (`color-mix` veya
  Gray 10/20). **Gradyan yok** (ya da çok ölçülü, Carbon data-viz tarzı).
- **Geometri:** Geometrik, sade, kavramsal — fotogerçekçi değil. Carbon
  pictogram estetiğini taklit et (temiz formlar, yuvarlatılmış köşeler).
- **Etiketler:** Diyagram parçaları IBM Plex Sans ile etiketlenir (`<text
  font-family="IBM Plex Sans" font-size="14" fill="#161616">`); etiket çizgileri
  ince (1px), aksan rengi.
- **Boşluk:** Ferah; öğeler kalabalık değil (dış yük, ped İlke 5).

**Örnek iskelet (etiketli kavram diyagramı):**
```html
<svg viewBox="0 0 480 320" role="img" aria-labelledby="t1 d1"
     style="width:100%;height:auto" font-family="IBM Plex Sans">
  <title id="t1">Bitki hücresi</title>
  <desc id="d1">Hücre duvarı, çekirdek ve kloroplastları gösteren basit şema.</desc>
  <rect x="40" y="40" width="400" height="240" rx="16"
        fill="#e5f6f5" stroke="#009d9a" stroke-width="2"/>
  <circle cx="240" cy="160" r="44" fill="#ffffff" stroke="#161616" stroke-width="2"/>
  <text x="240" y="166" text-anchor="middle" font-size="14" fill="#161616">Çekirdek</text>
  <!-- ek organeller + etiket çizgileri (1px, #009d9a) -->
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
| `ic-star` | yıldız | XP/başarı |
| `ic-idea` | fikir/ampul | ipucu |
| `ic-trophy` | kupa | rozet/bitiş |
| `ic-restart` | yeniden | tekrar dene |
| `ic-info` | bilgi | açıklama/ipucu |
| `ic-flag` | hedef | öğrenme hedefi |
| `ic-pause` | mola | brain-break |
| `ic-flip` | çevir | flashcard |

(Path tanımları `assets/module-template.html` sprite'ında; oradan kopyalanır
veya yeni ihtiyaç için aynı stilde — 32 grid, currentColor, geometrik — eklenir.)

## 6. Erişilebilirlik ve renk

- **Dekoratif** görsel: `aria-hidden="true"` (durum ikonu yanında zaten metin var).
- **Bilgi taşıyan** görsel (diyagram, hotspot): `role="img"` + `<title>` (+`<desc>`).
- İkon **tek başına anlam taşımaz**: durum daima ikon **+ metin** (renk üçüncü
  kanal). Örn. yanlış = kırmızı + `ic-close` + "Tekrar dene".
- İkon boyutu okunur: durum ikonları ≥20px; piktogramlar ≥48px.
- Kontrast: ikon rengi zemine karşı ≥3:1; aksan ikonları açık zeminde test edilir.
- Emoji **asla**; emoji görsel anlam taşımak için kullanılmaz (SKILL.md §3, kalite
  kapısı G-EMOJI).
