# Giriş sayfası yenilemesi — tasarım

**Tarih:** 2026-10-15 · **Yüzey:** `dashboard/src/components/LoginPage.tsx` (+ `LoginPage.scss`, `hooks/useGsi.ts`,
`utils/gsiDurumu.ts`, `utils/girisHatasi.ts`) · **İstek:** "bu sayfayı carbon mcp ile en estetik biçimde yeniden
tasarla" · **Öncelik:** anayasa D1–D4 / İ1–İ9 > talimatname (§3–§5, §7, §11) > Carbon login kalıbı.

## 1. Bugün ne var (ölçüldü, 2026-10-15, `giris-ekran/once/`)

- 1440 px: lacivert alan %55, iki ince dekor halka; form beyaz yarının **ortasında** yüzüyor (x ≈ 943), alt
  not ortalı, başlık ve giriş sola yaslı — üç farklı hiza. Altbilgi yok; "Hoş geldiniz" ve "giriş yapın" **siz**,
  hata cümleleri (`girisHatasi.ts`) **sen**: iki ses (İ9).
- 390 px: sayfa 892 px, ekran 844 px — kabuğun telefonda alt çubuk için bıraktığı 48 px (`.app-root`
  `padding-block-end`) giriş sayfasında da duruyor; sayfa boşuna kayıyor, altta gri şerit. Giriş sayfasında alt çubuk yok.
- 3840 px: Google'ın düğmesi px'le çizilen bir iframe; kök 32 px'e büyürken düğme 320 × 40 px kalıyor, sayfanın
  yarı ölçeğinde (4K kuralı S25 düğmeye ulaşmıyor).
- Durumlar: betik yüklenirken boşluk; betik engellenirse **hiçbir şey** (D3 ihlali — `load` dışında olay
  dinlenmiyor); doğrulanırken hiçbir şey; hata `title="Hata"` + cümle.
- `@keyframes login-hero-shift` tanımlı ama hiçbir kural kullanmıyor (ölü kod).
- Altbilgi cümlesi için sunucu okundu: `POST /api/auth/login` (`src/dashboard_api.py:282-305`) Google kimlik
  belirtecinden **e-posta, ad ve profil fotoğrafını** okuyup oturuma yazar. "TEDY yalnız e-posta adresini alır"
  doğru olmazdı; cümle üçünü sayar.

## 2. Carbon ne der (MCP `docs_search`, `anchor_url` ile)

| Kural | Kaynak |
|---|---|
| Giriş sayfası, kimlik bilgisiyle ya da başka bir desteklenen yöntemle uygulamaya erişimi sağlar | [login#login](https://carbondesignsystem.com/building-blocks/core/patterns/login/#login) |
| Başlık akışın tepesindedir, "Log in" sözcüklerini taşır, ürün adını içerebilir, sarabilir; arka plan görseli isteğe bağlıdır | [login#anatomy-of-a-basic-login-screen](https://carbondesignsystem.com/building-blocks/core/patterns/login/#anatomy-of-a-basic-login-screen) |
| Yerleşim: sol, sağ ya da orta — "alanlar ızgarada kaldıkça"; bölünmüş ekranda ek içerik az ve taranabilir, pazarlama ile giriş içeriği ayrı; alternatif giriş markası kendi rehberiyle | sayfa içi "Position", "Split-screen layout", "Separate authentication methods" (aynı sayfa; MCP indeksinde yalnız üst bölümler var, metin sayfadan okundu) |
| Sunucu hatası satır içi bildirimle, çözüm adımıyla; birden çok bildirim üst üste | sayfa içi "Server-side errors" |
| Klavyeyle gezilebilir; giriş bölgesi bir işaretleyiciyle (landmark) adlanır, özellikle bölünmüş ekranda | sayfa içi "Accessibility"; [accessibility/developers#utilize-aria-roles-and-landmark-roles](https://carbondesignsystem.com/building-blocks/foundations/accessibility/developers/#utilize-aria-roles-and-landmark-roles) |
| Expressive set editoryal ve pazarlama içindir, üründe dikkat dağıtır; fluid başlıklar kap içinde kullanılmaz, kap dışındaki ürün metninde kullanılabilir | [typography/overview#productive-and-expressive-type-sets](https://carbondesignsystem.com/building-blocks/foundations/typography/overview/#productive-and-expressive-type-sets) · [type-sets#fluid-heading-styles](https://carbondesignsystem.com/building-blocks/foundations/typography/type-sets/#fluid-heading-styles) |
| Tip her zaman kutu dolgusuna yaslanır; dolgu her standart kırılımda 16 px | [2x-grid/overview#padding](https://carbondesignsystem.com/building-blocks/foundations/2x-grid/overview/#padding) · [#margins](https://carbondesignsystem.com/building-blocks/foundations/2x-grid/overview/#margins) |
| Yüksek kontrast anı: açık temalı sayfada koyu bir bölge dikkati toplar | [color/overview#high-contrast-moments](https://carbondesignsystem.com/building-blocks/foundations/color/overview/#high-contrast-moments) |
| Satır içi bildirim görev akışında, eylemin durumunu söyler; en az 48 px, 3 px sol kenar | [notification/guidelines#inline](https://carbondesignsystem.com/building-blocks/core/components/notification/guidelines/#inline) · [notification/specifications#inline](https://carbondesignsystem.com/building-blocks/core/components/notification/specifications/#inline) |

Bileşenler `code_search` (`component_type: "React"`) ile doğrulandı ve `node_modules/@carbon/react` 1.114
`lib/components/*/*.d.ts` satırlarında görüldü: `InlineNotification` (`kind`, `lowContrast`, `hideCloseButton`,
`role`, `statusIconDescription`, `title`, `subtitle`), `InlineLoading` (`description`, `iconDescription`,
`status`), `SkeletonPlaceholder` (`className`), `Button` (`kind`, `size`). Piktogram kullanılmaz ([3.7-5]: panoda
piktogram yok); tek görsel mevcut logodur.

## 3. Karar

### 3.1 Yerleşim

**≥ 66rem (lg) — bölünmüş ekran.** İki sütun `10fr 6fr` (16 sütunlu 2x ızgarada 10 + 6):

- **Bant (sol, 10/16)** lacivert `--ted-color-brand-primary` ([3.2-9]: marka yalnız bantta ve giriş kahramanında).
  Üstte logo (3rem), altta — formun altbilgisiyle aynı alt çizgide — okulun adı (`label-01`,
  `--ted-color-brand-text-secondary`), değer cümlesi (`fluid-heading-03`, 20 → 24 px, `text-on-color`) ve bir
  destek cümlesi (`body-01`, ikincil bant metni). İçerik 2rem (`$spacing-07` = 16 px kenar + 16 px dolgu) içeride
  başlar. Halka yok, hareket yok, gradyan yok.
- **Form sütunu (sağ, 6/16)** `--cds-layer-01` üstünde; metin ve denetimler **tek sol çizgide** (2rem içeride,
  P3), form en çok 24rem. Form dikeyde ortada, altbilgi sütunun dibinde aynı sol çizgide.

**< 66rem — yığılmış.** Üstte kısa bant: logo (2rem) ve okulun adı tek satırda, 16 px kenar; değer cümleleri
gizlenir (Carbon: bölünmüş ekranın ek içeriği az olmalı; telefonda giriş tek şeydir). Form 16 px kenarla bandın
altında başlar; altbilgi en altta. Sayfa yüksekliği `100dvh`; kabuğun alt çubuk payı giriş sayfasında sıfırdır (bugünkü 48 px'lik boş kayma biter); 320 px'te
yana kayma yok.

**4K.** Her boyut `rem`; kök ölçeği (S25) bandı, sütunları ve tipi büyütür. Google düğmesi bir iframe olduğu için
CSS `zoom` ile kök ölçeğine eşitlenir (aşağıda).

### 3.2 Tip ölçeği (P1: tek şey en büyüktür)

| Öğe | Token | Neden |
|---|---|---|
| "TEDY'ye giriş yap" (`h1`) | `heading-04` 28 px | Görünümün tek şeyi; başka başlık yok (P1). Carbon: başlık "giriş" sözcüğünü ve ürün adını taşır |
| Bant değer cümlesi | `fluid-heading-03` 20 → 24 px | Kap dışı sayfa düzeyi metin (S16); başlıktan küçük kalır — bant ne kadar büyük olursa olsun tek şey formdur |
| Giriş cümlesi | `body-01` 14 px | Productive gövde |
| İzin notu | `helper-text-01` 12 px | Düğmenin yardım metni |
| Bant okul adı, altbilgi | `label-01` 12 px | Üst veri; altbilgi gövdeden büyük olamaz (P1) |

**Gerilim:** istek bantta "IBM tarzı expressive tip" öneriyordu (ör. `fluid-heading-05`, 60 px'e kadar). P1 bunu
yasaklar: değer cümlesi giriş başlığından büyük olsaydı ekranın en büyük metni bir slogan olurdu. Talimatname
kazanır; expressive set **seçildi** ama başlığın altında bir basamakta (`fluid-heading-03`). §11'e yeni satır
gerekmez (S16 kap dışı fluid başlığa zaten izin verir).

### 3.3 Ses ve metin (cümle düzeni, S38; tek ses, İ9)

Sayfa **sen** der — hata cümleleri zaten sen'di; aile ve Işık aynı sayfayı okur, panonun yapma yüzeyi Işık'a sen
der ([3.9-2]).

- Başlık: "TEDY'ye giriş yap"
- Giriş: "Derslerini, ödevlerini ve sınavlarını görmek için Google hesabınla devam et."
- İzin notu: "Yalnız ailenin tanımlı Google hesaplarıyla giriş yapılır."
- Bant: "TED Rönesans Koleji" · "Okul günü tek bakışta." · "TEDY okulun portalını düzenli okur; dersi, ödevi ve
  sınavı sırayla önüne koyar."
- Altbilgi: "Giriş Google ile yapılır; şifren TEDY'ye gelmez. TEDY bu girişten yalnız adını, e-posta adresini ve
  profil fotoğrafını alır." · "TED Rönesans Koleji · {yıl}" (yıl çalışma anında; testler saati sabitler).

### 3.4 Google düğmesi

Google'ın düğmesi (GSI `renderButton`, `size: 'large'` = 40 px) bir iframe'dir: boyu sabit, eni 200–400 px, px ile
çizilir. Carbon'un `lg` denetim boyu 48 px'tir ([3.4-8]), telefonda dokunma hedefi ≥ 44 px (S18). İkisi tek
çarpanla sağlanır: düğmenin kabı `zoom = kökÖlçeği × 1,2` alır (40 × 1,2 = 48 px; 4K'da 96 px), `width` parametresi
`min(400, max(200, sütunEni ÷ zoom))` olur — düğme sütunun tam eninde, 48 px boyunda, 4K'da 2×. `zoom` çalışma anında
hesaplanır (S5). Sütunun eni değişirse (`ResizeObserver`) düğme yeniden çizilir. Bu bir Carbon sapması değil, bir
üçüncü taraf denetimin Carbon ölçüsüne getirilmesidir; Google'ın kendi görünümü (renk, logo, metin) değişmez
(Carbon: alternatif giriş markası kendi rehberiyle).

### 3.5 Durumlar (D3, D4)

| Durum | Ne zaman | Ne görünür |
|---|---|---|
| Betik yükleniyor | ilk 400 ms | Hiçbir şey (S36, B48) — slot yüksekliğini korur, sayfa zıplamaz |
| Betik yükleniyor | 400 ms sonra | Düğme boyunda `SkeletonPlaceholder`; slot `aria-busy="true"`, gizli durum metni "Google giriş düğmesi yükleniyor" |
| Betik gecikiyor | 10 sn sonra hâlâ yok | `warning` (S39: bozulmuş, henüz başarısız değil): "Google düğmesi gecikiyor" · "Bağlantın yavaş olabilir. Biraz bekle ya da yeniden dene." + "Yeniden dene" (`tertiary`, `lg`). Betik sonra gelirse düğme çizilir, uyarı kalkar |
| Betik yüklenemedi | `error` olayı ya da yüklendiği hâlde `google.accounts.id` yok (engelleyici) | `error` (S39: okur ilerleyemiyor): "Google düğmesi yüklenemedi" · "Bir reklam engelleyici ya da ağ Google'ı durdurmuş olabilir. Bu sayfada engelleyiciyi kapatıp yeniden dene." + "Yeniden dene". Yeniden deneme betiği yeniden ekler |
| Doğrulanıyor | Google kimliği geldi, `/api/auth/login` sürüyor | Düğmenin yerinde tek `InlineLoading` "Giriş yapılıyor…" (S36); düğme gizli |
| Reddedildi (403) | E-posta izin listesinde yok | `error`: "Bu hesap tanımlı değil" · "Bu Google hesabıyla giriş yapılamaz. Ailenin tanımlı hesabıyla dene." Düğme geri gelir |
| Giriş hatası | 400/401/5xx | `error`: "Giriş yapılamadı" · "Google girişi doğrulanamadı. Yeniden dene." (başlığı tekrarlamaz) |
| Bağlantı yok | `fetch` atar | `error`: "Bağlantı kurulamadı" · "İnternetini kontrol edip yeniden dene." |

Her bildirim `lowContrast` (S27), `hideCloseButton`, Türkçe `statusIconDescription`, başlıkta nokta yok; görevi
durduran `role="alert"`, gecikme `role="status"`. Bildirim formun başında, giriş cümlesinin altında (Carbon:
satır içi bildirim birincil içeriğin başında). Sunucunun `error` dizesi hiç gösterilmez (B43).

### 3.6 Erişilebilirlik ve görünüm kipleri

- İşaretleyiciler: bant `<header>` (banner), form `<main aria-labelledby>`, altbilgi `<footer>` (contentinfo) —
  Carbon login: giriş bölgesi landmark'la adlanır.
- Logo `alt="TEDY"`; zorunlu renklerde beyaz logo `<picture>` ile koyu logoya döner (korunur); bant ve sütun gerçek
  kenarla ayrılır (`border-inline-end` / telefonda `border-block-end`, `--ted-color-brand-rule`) — zorunlu renk
  dolguyu silince sınır kalsın ([3.8-5]).
- Odak: bantta odaklanabilir öğe yok; form sütunu Carbon odağı.
- Azaltılmış hareket: sayfa kendi hareketini taşımaz; iskeletin parıltısı ve `InlineLoading` genel `reduce` bloğuyla
  durur (S37).
- Koyu tema: pano yalnız g10 ([3.1-6], S14) — eklenmez.

## 4. Testler

- Birim (`node --test`): `gsiDurumu` (betik/zaman → görünür durum), `girisBildirimi` (durum → başlık + cümle),
  `gsiOlcusu` (kök ölçeği + sütun eni → `zoom` + `width`).
- E2E `giris-sayfasi.spec.ts`, Google betiği her testte yönlendirilir (gerçek betik hiç yüklenmez): her durum
  (gecikme → iskelet → uyarı, engel → hata → yeniden dene → düğme, 403, 500, ağ hatası, doğrulanıyor), başarılı giriş
  panoya geçer; axe + IBM Equal Access 1440/390; 390'da her denetim ≥ 44 px ve düğme 48 px; 320/390/1440/3840'ta yana
  kayma yok, 3840'ta başlık ve düğme 1920'nin 2 katı; azaltılmış harekette hiçbir şey hareket etmez; zorunlu renkte
  bant sınırı yaşar.
- `gorsel-regresyon` giriş tabanı (masaüstü + yeni telefon) ve `aria-yapisi` giriş ağacı, fark okunarak.
