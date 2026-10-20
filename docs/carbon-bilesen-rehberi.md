# Carbon Bileşen Rehberi — TEDY

**Sürüm 1.1 · 2026-10-10** (1.1: talimatname Ç1–Ç10 kararları, S35–S44, işlendi) · `docs/tedy-ui-ux-talimatnamesi.md`'nin eki ("Talimatname").

## Bu belge nedir

Carbon Design System v11'in her çekirdek bileşeni için bir kart: Carbon ne diyor, TEDY'de nerede
kullanılıyor, TEDY'nin kuralı ya da sapması ne. Kalıp kartları (boş durum, diyalog, form …) bu
belgenin ikinci bölümündedir.

- **Öncelik.** Bu rehber talimatnamenin öncelik sırasında 5. basamaktır: D1–D4 → İ1–İ9 →
  talimatname (sapmalar dahil) → yüzey tasarımları → **bu rehber** → `tedy-carbon` katmanı →
  carbon-builder → Carbon'un genel rehberi. Modül yüzeylerinde `docs/tedy-modul-tasarim-kanunu.md`
  İ1–İ9'dan sonra, talimatnameden önce; edupedia vendor ve eklentisi `tedy-carbon`'dan sonra,
  carbon-builder'dan önce gelir (kanun §0.2). Bir kart talimatnameyle çelişirse **talimatname kazanır**;
  çelişki kartta adıyla yazılır, sessizce düzeltilmez. Ölçüm varsayımı yener.
- **Kaynak.** carbondesignsystem.com taraması, 2026-10-10. Erişilebilirlik sekmelerinin test ettiği
  sürüm `@carbon/react` 1.114.0'dır; panoda kurulu olan da budur (`@carbon/styles` 1.117.0,
  `@carbon/ai-chat` 1.22.0). Carbon değerleri sayfadan birebir alınmıştır. Sayfanın vermediği değer
  **"sayfada belirtilmemiş"** diye yazılır; kurulu paketten okunan değer **[paket]** ile işaretlidir.
  Hiçbir değer bellekten tamamlanmamıştır.
- **Sayfa içi tutarsızlıklar** (Carbon'un kendi sayfasında iki farklı değer) kartta "sayfa
  tutarsız" diye ikisiyle birlikte verilir.
- **Kod satır numaraları kayabilir.** Repo kanıtı dosya adıyla verilir; satır yalnız yeri belirsizse.

## Kart nasıl okunur

Başlık `### 1.N Türkçe ad (`carbon-id`)` biçimindedir; `carbon-id` Carbon sitesindeki yol
parçasıdır ve kartın bağlantı çapasıdır (`carbon-bilesen-rehberi.md#button`). Bir kalıbın kimliği bir
bileşeninkiyle çakışırsa kalıp çapası `kalip-` öneki alır: `#kalip-overview`, `#kalip-loading`,
`#kalip-search`. Alanlar:

| Alan | İçerik |
|---|---|
| Ne için | Bileşenin işi, Carbon'un tanımıyla. |
| Kullan / Kullanma | Carbon'un "when to use / when not to use" kuralları ve önerdiği alternatif bileşen. |
| Varyantlar | Carbon'un varyant ve stil adları. |
| Ölçüler ve token'lar | Yükseklik, boyut, dolgu, tip ve renk token'ları; px / rem sayfadaki gibi. |
| Durumlar | Carbon'un durum listesi ve davranışı. |
| Erişilebilirlik | Klavye, ARIA, etiket, hedef boyutu; Carbon'un 1.114.0 test durumu. |
| İçerik | Etiket ve metin kuralları. |
| AI varyantı | Carbon for AI'ın bileşene eklediği; yoksa "sayfada belirtilmemiş". |
| React | `@carbon/react` 1.114.0'daki **tam dışa aktarım adları** (`lib/index.d.ts` ve bileşen `index.d.ts` dosyalarından doğrulandı). `preview__` / `unstable__` önekli adlar kararsız API'dir; TEDY bunlara bağlanmaz (talimatname S4). |
| TEDY durumu | Lejanttaki üç değerden biri, kullanıldığı yer, TEDY kuralı ya da sapması, ilgili talimatname bölümü ve S/B numarası. |
| Kaynak | Güncel Carbon URL'si. Sekmeler: `guidelines/`, `specifications/`, `accessibility/`, `code/`. |

## "TEDY durumu" lejantı

| Değer | Anlamı |
|---|---|
| **Kullanılıyor** | `dashboard/src` ya da modül şablonu bileşeni (veya Carbon anatomisini birebir kopyalayan yerel karşılığını) bugün kullanıyor. Kart, kullanımın Carbon'a ve TEDY kuralına uyup uymadığını söyler. |
| **Uygun ama kullanılmıyor** | Bileşen TEDY kurallarıyla çatışmıyor; bugün ihtiyaç yok. Gerektiğinde kartın "TEDY kuralı" satırıyla eklenir. |
| **Kullanılmaz (neden)** | Bileşen ya da bir varyantı TEDY'de bilinçli olarak kullanılmaz; neden ve ölçüm kartta. Değiştirmek talimatname §14 sürecinden geçer. |

## Kısaltmalar

- **D1–D4, İ1–İ9**: anayasa, `docs/frontend-design-principles.md` (değişmezler ve ilkeler).
- **§N**: talimatname bölümü (`docs/tedy-ui-ux-talimatnamesi.md`). Sık geçenler: §3.2 renk, §3.3
  tipografi, §3.4 yerleşim, §3.5 köşe/kenar/derinlik, §3.6 hareket, §3.7 ikon, §3.8 erişilebilirlik,
  §3.9 içerik ve dil, §4 bileşen seçimi, §5 kalıplar, §6 Carbon for AI, §9 edupedia modülleri.
- **S1…S45**: talimatname §11.1, bilinçli sapmalar (S1–S34) ve 2026-10-10'da Carbon pratiğine göre kararlaştırılan
  çelişkiler (S35–S45). **Ç1…Ç11**: talimatname §11.2; hepsi kararlaştırıldı (→ S35–S45).
  **B1…B75**: talimatname §13, bilinen borçlar (borç kaydı; kapanan satır "Kapandı" diye kalır).
- **Yüzey §N.M**: `docs/frontend-surface-designs.md` bölümü.
- **Modül şablonu**: `src/mcp_server/vendor/assets/module-template.html`; Carbon eşlemesi
  `src/mcp_server/vendor/references/carbon-child-system.md`.
- Bu rehberin taramasında ölçülen her kusur talimatname §13'te bir B numarası aldı; kartlar o numarayla anar.

---

## 1. Bileşenler

Carbon'un bileşen listesindeki 43 giriş 42 kartta toplanır: Multiselect (ve Combo box) Dropdown
kartının içindedir; UI shell üç karttır. Kartlar Carbon kimliğine göre alfabetiktir.

<a id="overview"></a>

### 1.0 Genel bakış: erişilebilirlik durumu, özellik bayrakları, ortak kurallar (`overview`)

- **Erişilebilirlik durumu.** Carbon her değişiklikte IBM Equal Access Accessibility Checker ile
  otomatik test koşar; ekran okuyucu testleri dönemsel ve elle yapılır. Her bileşen için dört satır:
  ilk çizim, ek durumlar/varyantlar, odak ve klavye, elle ekran okuyucu (JAWS, VoiceOver, NVDA).
  Etiketler: *Tested*, *Partially tested*, *Manually tested*, *Not available* (ör. etkileşimsiz
  bileşende klavye), *Not tested* (çoğunlukla preview/unstable). 1.114.0'da "ek durumlar" satırı
  eksik ya da ertelenmiş olanlar: Combo Box, Composed Modal, Date Picker, Dropdown, Multi Select;
  Icon Button, Copy Button, Definition Tooltip, Inline Loading, Loading, Menu, Modal, Toggletip, Form,
  Pagination Nav (önizleme ve yardımcılar — Aspect Ratio, Layer, Form Group, Fluid Form, Fluid Combo Box,
  Chat Button, Icon/Shape Indicator — ayrıca). Menu'nün klavye testi de kısmi; Interactive Tag ve Popover'ın ilk çizim testi
  ertelenmiş; Code Snippet'in ilk çizim testi kısmi. **TEDY kuralı:** Carbon'un "geçti" demesi
  TEDY'nin kapısını geçmek demek değildir; her sayfa axe + IBM Equal Access ile 1440 ve 390 px'te
  ayrıca denetlenir (`dashboard/tests/e2e/tasarim-denetimi.spec.ts`, `ibm-erisilebilirlik.spec.ts`).
  Carbon bileşeninin kendi ihlali ölçülürse onarılır ve onarım belgelenir (S13).
- **Özellik bayrakları.** Yeni bayrak varsayılan kapalıdır; v12'de varsayılan olur; mevcut
  bileşenler kullanımdan kaldırılmaz. Bayraklı bileşenler (şimdilik yalnız React): Menu buttons
  (overflow menu, `enable-v12-overflowmenu`), Modal (`enable-focus-wrap-without-sentinels`),
  Notification (actionable; bayrak adı sayfada belirtilmemiş), Structured list
  (`enable-v12-structured-list-visible-icons`, tasarım değişir), Tile (`enable-tile-contrast`,
  `enable-v12-tile-default-icons`, `enable-v12-tile-radio-icons`, tasarım değişir), Toggle
  (`enable-v12-toggle-reduced-label-spacing`, tasarım değişir), Tree view
  (`enable-treeview-controllable`). React: `FeatureFlags`, `useFeatureFlag`, `useFeatureFlags`.
  **TEDY durumu:** hiçbir bayrak açık değil (`dashboard/src`'de `FeatureFlags` yok). Bayrak açmak
  görsel tabanı değiştirir; görsel fark okunarak ve tek commit'te yapılır (talimatname §12).
- **Ortak kurallar (birden çok kartta geçer, kartlarda tekrar edilmez):**
  - *Yükseklik basamağı*: 24 (xs) · 32 (sm) · 40 (md, varsayılan) · 48 (lg) · 64 (data table xl ve
    bütün fluid alanlar). Bir sayfadaki form bileşenleri tek boy kullanır. TEDY'de telefonda
    dokunulan her denetim ≥ 44 × 44 px, standart `$spacing-09` (48 px) (S18); bu, mümkünse `size`
    prop'uyla sağlanır, bileşen başına `min-block-size` yamasıyla değil (B8).
  - *Alan anatomisi* (text input, select, dropdown, date picker, number input): etiket `$label-01`
    12 px `$text-secondary`, 8 px (`$spacing-03`) altında alan; alan 14 px `$body-compact-01`, yan
    dolgu 16 px (`$spacing-05`), `$field` zemin, 1 px `$border-strong` alt çizgi; yardım metni 12 px
    `$helper-text-01` `$text-helper`, 4 px (`$spacing-02`) üstte; hata = 2 px `$support-error`
    kenar + ikon + `$text-error` mesaj (yalnız renk asla); uyarı ikonu `$support-warning`, mesaj
    `$text-primary`; odak `$focus`.
  - *Devre dışı ≠ salt okunur*: devre dışı odak almaz, ekran okuyucu okumaz, kontrast şartı yoktur;
    salt okunur odak alır, okunur, kontrastı geçer. Okurun incelemesi ama değiştirmemesi gereken her
    şey salt okunurdur (talimatname §5 "salt okunur/devre dışı").
  - *Kayan katman gölgesi*: sayfa `0 2px 6px 0 rgba(0,0,0,.2)` yazar; TEDY bunu token biçimiyle
    `0 2px 6px var(--cds-shadow)` (`--ted-shadow-popover`) yazar; alfa rengi elle yazılmaz (D1, S11).
  - *Taşma*: Carbon'un her bileşeninde "üç nokta + tam metin ipucu"; sessiz kırpma yok.
  - *Türkçe varsayılan metinler*: Carbon bileşenlerinin İngilizce varsayılanları (`"Close"`,
    `"<kind> icon"`, `"loading"`, `"Clear filter"`) her kullanımda Türkçeyle verilir (D4; açık yerler B44, B15 kapandı).
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/overview/components/ ·
  …/overview/accessibility-status/ · …/overview/feature-flags/

<a id="accordion"></a>

### 1.1 Akordeon (`accordion`)

- **Ne için:** Çok içeriği aşamalı açarak küçük alanda vermek; başlık, okurun neyi açacağına karar
  vermesine yeter. Carbon uyarır: içerik gizlenir, okur bir kısmını hiç görmeyebilir.
- **Kullan:** İlişkili bilgiyi düzenlemek; tamamı okunmayacak içerikle sayfayı kısaltmak; dar alan
  (mobil, yan panel).
- **Kullanma:** Okur büyük olasılıkla hepsini okuyacaksa (başlıklı kaydırılan sayfa); iç içe büyük
  bilgi (→ tree view); görevi bitirmek için gereken bilgi kapalı panelde durmaz (disclosures kalıbı).
- **Varyantlar:** Varsayılan (başlık ve içerik ızgaraya girintili, kenarlar oluğa taşar) · flush
  (0 px; yan panel, kenar çakışması). Chevron `end` (varsayılan) ya da `start` (nadir, ağaç benzeri);
  sayfada tutarlı, asla dönüşümlü.
- **Ölçüler ve token'lar:** Başlık sm 32 / md 40 / lg 48 px. Başlık sol boşluğu 16 (`$spacing-05`);
  panel üst 8 (`$spacing-03`), alt 24 (`$spacing-06`), sol 16; gövde sağ boşluğu genişlik > 640 →
  %25, 420–640 → 64 px (`$spacing-10`), < 420 → 16 px. İkon 16. Başlık ve içerik `$body-01` 14/400.
  Renk: metin `$text-primary`, ikon `$icon-primary`, ayırıcı `$border-subtle`, hover `$layer-hover`,
  odak `$focus`, devre dışı `$text-disabled` / `$icon-disabled`. Açık panelin azami yüksekliği yok.
- **Durumlar:** Kapalı/açık (chevron aşağı = kapalı, yukarı = açık), hover, odak, devre dışı.
  Carbon varsayılanı: bütün paneller kapalı başlar; paneller bağımsız açılır. Panel içinde kaydırma
  yok; yatay kaydırma hiç yok.
- **Erişilebilirlik:** Başlık `<button>` + `aria-expanded` + `aria-controls`. `Tab`/`Shift-Tab`
  başlıklar arasında, `Enter`/`Space` açar-kapar; açık paneldeki denetimler sekme sırasına girer.
  Birden çok akordeon `<ul>` içinde `<li>`; tek akordeon listeye konmaz. Carbon başlıkları
  varsayılan olarak heading değildir; ürünün ilk kullanımında sayfa yapısına uygun `h1–h6` (ya da
  `aria-level`) işaretlenir. Sola konan chevron az görenler için daha erişilebilirdir. 1.114.0: dört
  satır geçti.
- **İçerik:** Başlık kısa, açık, cümle düzeninde; gövdede paragraf ve alt başlık olabilir.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `Accordion`, `AccordionItem`, `AccordionSkeleton` (`Accordion`: `size`, `align`,
  `isFlush`, `ordered`; `AccordionItem`: `open`, `title`, `disabled`).
- **TEDY durumu:** **Kullanılıyor** — `PlatformProgress.tsx`, `CourseContent.tsx`,
  `Announcements.tsx`. TEDY kuralı (Yüzey §2.5, ölçülmüş): bugünün eyleme açık bölümü açık, geçmiş
  kapalı, başlık "Başlık (n) ⌄" (cümle düzeni, S38) — Carbon'un "hepsi kapalı" varsayılanından bilinçli sapma (S34); modül ve
  geçmiş bölümleri Carbon varsayılanını izler. İşler grupları Carbon akordeonu değildir
  (`HomeworkTracker.tsx`: `<button aria-expanded>`, `aria-controls` ve liste sarmalayıcısı yok).
  Hiçbir yerde `size`/`align`/`isFlush` verilmiyor; Dersler'de 48 px telefon hedefi `size="lg"`
  yerine `ted-theme.scss`'teki `.course-content .cds--accordion__heading` yamasıyla sağlanıyor (S18,
  B8). Akordeon başlıklarına heading seviyesi verilmemiş. Bulgu: Duyurular'da en yeni duyuru da
  kapalı açılıyor; okurun tamamını okuyacağı içerik akordeona girmez. Talimatname §5
  "katlama/açılma".
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/accordion/guidelines/

<a id="ai-label"></a>

### 1.2 AI etiketi (`ai-label`)

- **Ne için:** Arayüzdeki her AI örneğini işaretleyen etkileşimli öğe ve açıklanabilirliğe giden
  tutarlı yol (eski adı "AI Slug"; artık kararlı).
- **Kullan:** AI'ın ürettiği ya da AI ile üretilen içeriği işaretlemek; açıklamaya (modelin nasıl
  kurulduğuna) giden tek yol olarak.
- **Kullanma:** Süs olarak; "yeniden üret" gibi bir AI eyleminin tetiği olarak (o eylemlerin kendi
  ikonları vardır); davranışını değiştirerek.
- **Varyantlar:** Default (kap ve bileşenler; geniş ve odaklı örnekler) · Inline (küçük, odaklı
  örnek; metinle aynı satırda). Görünürlük düzeyi: *focused* (bölümdeki tek tek AI örnekleri),
  *broad* (bölümdeki AI kullanımının özeti); AI içerik insan içeriğinden ayırt edilecek ve tek tek
  açıklanacaksa ikisi birden.
- **Ölçüler ve token'lar:** Default boylar mini 16 · 2xs 20 · xs 24 · sm 32 · md 40 · lg 48 · xl 64
  px; ghost ikon düğmenin yanında bir boy küçüğü. Inline: sm 16 (12 px metinle) · md 18 (14 px) ·
  lg 22 (16 px). Yerleşim: kapta sağ üst, kenara yapışmadan; alanda sağda, dikey ortada; ikon
  grubunda en solda. Renk (default): metin `$text-primary`, kenar `$border-inverse`, zemin saydam;
  hover metin `$text-inverse`, zemin `$background-inverse`; odak `$focus`. Açıklama popover'ı:
  zemin `$ai-popover-background` + `$ai-aura-start` → `$ai-aura-end`, kenar `$ai-border-start` →
  `$ai-border-end`, dolgu 24 (`$spacing-06`), alt bilgi 48 px; başlık `$heading-04` 28, gövde
  `$body-01` 14. Etiket metni: xl `$heading-03` 20/600; sm–lg `$heading-02` 16/600; 2xs–xs 12/600 ve
  mini 9/600 token'sız.
- **Durumlar:** Yalnız etkin, hover, odak. Devre dışı ya da salt okunur bir alanın içinde bile
  **asla devre dışı olmaz.** Kullanıcı AI içeriğini değiştirirse AI stili kalkar, etiketin yerine
  "revert" ikon düğmesi gelir; basınca AI içeriği, stili ve etiketi geri döner.
- **Erişilebilirlik:** Toggletip davranışı: sekme sırasında; `Enter`/`Space` açar-kapar, odak
  tetikte kalır; `Tab` popover'daki ilk denetime girer, yoksa kapatıp sonraki durağa geçer; `Esc`
  kapatır ve odağı tetiğe döndürür. Alan içinde etiket, alandan sonra ek bir sekme durağıdır.
  `aria-label="AI - Show information"`, `aria-expanded`, `aria-controls`. 1.114.0: varsayılan ve ek
  durumlar geçti; klavye "yok/uygulanamaz"; elle test edildi.
- **İçerik:** Kısaltma çevrilir (AI, IA, KI, ИИ …); **Türkçe karşılığı sayfada belirtilmemiş.**
  Açıklama şablonu dört bölüm: Overview, Supporting details, Artifacts and resources, Additional
  actions.
- **AI varyantı:** Bileşenin kendisi Carbon for AI'dır.
- **React:** `AILabel` (`kind`: `default` | `inline`; `size`: `mini` | `2xs` | `xs` | `sm` | `md` |
  `lg` | `xl`; `autoAlign`), `AILabelContent`, `AILabelActions`. Eski adlar `unstable__Slug`,
  `preview__Slug`, `…SlugContent`, `…SlugActions` — kullanılmaz. Bileşenlerde `slug` prop'u yerine
  `decorator`.
- **TEDY durumu:** **Kullanılıyor** — canlı asistan `asistan/AiAciklama.tsx`
  (`size="xs" autoAlign align="bottom-right"`, `aiText="AI"`), sohbet başlığının sağ üstünde
  (`headerFixedActionsElement`). Carbon AI Chat'in kendi başlık etiketi axe `nested-interactive`
  ihlali verdiği için kapalı; yerine `AiAciklama` (S13; her `@carbon/ai-chat` yükseltmesinde
  Carbon'un kendi etiketi yeniden denenir). "Yeniden üret" ayrı `Renew` ikon düğmesi — kurala uygun.
  Açık konular: canlı yüzeyde yalnız *broad* etiket var (eski `AssistantChat.tsx`'te mesaj başına
  *focused* `mini` etiket vardı); popover'da "Artifacts and resources" ve "Additional actions"
  yok; fotoğraftan çıkarılan ödev alanlarında (`OdevOnayKarti.tsx`) AI etiketi ve revert yok;
  modüllerde AI etiketi S41 (2026-10-10) ile `ModuleViewer`'ın çerçeve başlığındadır (2026-10-11, B71 kapandı;
  `ModulAiEtiketi.tsx`, açıklanabilirlik içeriğiyle); modülün içi değişmez. Kısaltma: "AI" ("YZ" kararı
  verilmedi). Talimatname §6.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/ai-label/guidelines/

<a id="breadcrumb"></a>

### 1.3 Ekmek kırıntısı (`breadcrumb`)

- **Ne için:** Okurun bilgi mimarisindeki yerini göstermek ve üst düzeye ya da önceki adıma dönmek.
- **Kullan:** İkiden fazla düzeyli hiyerarşide çok içerik varsa.
- **Kullanma:** Birincil gezinmenin yerine (her zaman ikincildir); tek düzeyli gezinmede (kalabalık);
  çok adımlı süreçte (→ progress indicator).
- **Varyantlar:** Konuma dayalı (site hiyerarşisi) · yola dayalı (atılan adımlar, hep dinamik); aynı
  görünüm; ürün başına biri tutarlı.
- **Ölçüler ve token'lar:** small `$label-01` 12 px, yükseklik 16 (sayfa başlığı, sıkışık alan,
  küçük kırılım); medium (varsayılan) `$body-compact-01` 14 px, yükseklik 18. Bağlantı yan boşluğu
  small 4 (`$spacing-02`), medium 8 (`$spacing-03`); taşma menüsü yüksekliği 40. Renk: bağlantı
  `$link-primary`, hover `$link-primary-hover`, geçerli sayfa ve ayırıcı `$text-primary`, odak
  `$focus`; hover/odak/aktifte alt çizgi.
- **Durumlar:** Geçerli sayfa dışında her bağlantı etkileşimli; ayırıcılar değil. Taşma: ilk ve son
  iki bağlantı görünür, ortası taşma menüsüne; **asla ikinci satıra kaymaz**. Mobilde önce taşma,
  sonra tek kırıntı.
- **Erişilebilirlik:** `<nav>` "breadcrumb" adlı; bağlantılar `<ul>` içinde `<li>`; ayırıcılar CSS,
  odaklanmaz; üç nokta düğmesi "more breadcrumbs" adlı ve sekme sırasında. 1.114.0: dört satır geçti.
- **İçerik:** Kısa bağlantılar; en üst ebeveynden başlar; geçerli sayfa varsayılan olarak listede
  yok; sayfanın başlığı yoksa son öğe olarak, bağlantısız eklenir.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `Breadcrumb`, `BreadcrumbItem`, `BreadcrumbSkeleton`.
- **TEDY durumu:** **Uygun ama kullanılmıyor.** Üç düzeyli rotalar (`/moduller/:slug/:version`,
  `/kitaplar/:slug/:chapterId`) tek bir geri bağlantısıyla çözülüyor ("Modüllere dön",
  "← Kitaplık", "İçindekiler"); birincil gezinme yan menüde. Bu, Carbon'un "tek düzeyde kalabalık
  yapar" kuralıyla ve İ1/İ6 ile tutarlı. Kitaplar için küçük bir breadcrumb seçenektir, kusur değil.
  Not: "Modüllere dön" `Button` + `useNavigate` ile gidiyor; gezinme bağlantıdır (1.4, 1.15).
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/breadcrumb/guidelines/

<a id="button"></a>

### 1.4 Düğme (`button`)

- **Ne için:** Bir eylemi tetiklemek; etiket ne olacağını söyler.
- **Kullan:** Sayfa başına **tek birincil** düğme (uygulama başlığı, modal ve yan panel sayılmaz;
  sayfadan açılan geçici akış kendi birincilini getirebilir). Okuma sayfalarında birincil gerekmez;
  tertiary ve ghost yeter.
- **Kullanma:** Gezinme için (başka sayfaya gidiyorsa → link).
- **Varyantlar:** Primary (sayfanın asıl eylemi) · Secondary (yalnız birincille birlikte; çiftin
  **olumsuz** eylemi: "Cancel", "Back"; tek başına ve olumlu eylem için asla) · Tertiary (daha az
  belirgin, tek başına olabilir; sayfa başlığı ve birincili olan sayfadaki boş durum eylemi
  tertiary'dir) · Ghost (en hafif; ilerleme akışında "Cancel") · Danger (veriyi yok eden eylem;
  primary, tertiary, ghost; **asla yalnız ikon**). Önerilen ikililer: primary+secondary,
  primary+tertiary, primary+ghost, primary+danger tertiary, danger primary+secondary, danger
  primary+ghost; birincilsiz: 2 tertiary, tertiary+ghost, 2 ghost. Kaçınılan: iki yüksek vurgu bir
  arada, secondary'nin birincilsiz kullanımı, tertiary+danger tertiary, primary+danger ghost.
- **Ölçüler ve token'lar:** xs 24 · sm 32 (32 px alanlarla) · md 40 (40 px alanlarla) · lg 48
  ("yazılımda en yaygın", 14 px gövdeyle) · lg expressive 48 · xl 64 · 2xl 80 px; grupta boy
  karıştırılmaz. Etiket `$body-compact-01` 14/400 (expressive `$body-compact-02` 16). Dolgu: ikonsuz
  sol 16 (`$spacing-05`) / sağ 64 (`$spacing-10`); ikonlu 16/16, etiket–ikon 32 (`$spacing-07`);
  ghost etiket–ikon 8 (`$spacing-03`); kenardan 16 px içeride hiçbir öğe olmaz. İkon 16 × 16
  (expressive 20), etiketin sağında, etiketle aynı renk, çizgi (line) varyantı. Odak 1 px iç gölge.
  Renk: primary `$button-primary` / `-hover` / `-active`, metin `$text-on-color`; secondary
  `$button-secondary…`; tertiary `$button-tertiary` (metin, ikon, kenar) → hover `$text-inverse` +
  `$button-tertiary-hover`; ghost `$link-primary` → hover `$link-primary-hover` + `$background-hover`;
  danger `$button-danger-primary` / `-hover` / `-active`, `$button-danger-secondary`; devre dışı
  `$button-disabled` + `$text-on-color-disabled` (opaklık değil). Grup: aynı genişlik (ghost hariç),
  aralık 16 (`$spacing-05`); akışkan grup ayırıcısı 1 px `$button-separator`; tam yayılım kodda
  320 px'te durur.
- **Durumlar:** Etkin, hover, odak, aktif, devre dışı; yükleniyor = düğmenin içinde inline loading,
  düğme devre dışı. Dialog açılınca birincil varsayılan odağı alır.
- **Erişilebilirlik:** `Tab` ile ulaşılır, `Enter`/`Space` tetikler. Yalnız ikonlu düğmenin adı
  hover ve odakta ipucu olarak görünür; ipucu her zaman gerekir. Aç/kapa düğmesi `aria-pressed`
  ya da adını değiştirir ("play"/"pause"). 1.114.0: dört satır geçti. Asgari dokunma hedefi sayfada
  belirtilmemiş (TEDY: S18).
- **İçerik:** Etiket eylemi söyler; yalnız isim olmaz ("Done", "Close", "Cancel", "Add", "Delete"
  istisna). Cümle düzeni. Etiket sola hizalı, genişte bile; taşarsa ikinci satıra kayar, kırpılmaz.
  Eylemi başka sekmede açan düğmede "launch" ikonu. Grupta ikon ya hepsinde ya hiçbirinde.
- **AI varyantı:** Sayfada belirtilmemiş (AI etiketi düğme gibi kullanılmaz, bkz. 1.2).
- **React:** `Button` (`kind`: `primary` | `secondary` | `tertiary` | `ghost` | `danger` |
  `danger--primary` | `danger--tertiary` | `danger--ghost`; `size`: `xs` | `sm` | `md` | `lg` | `xl` |
  `2xl`; `hasIconOnly`, `iconDescription`, `tooltipPosition`, `renderIcon`), `IconButton` (kind:
  primary, secondary, ghost, tertiary), `ButtonSet`, `ButtonSkeleton`; ayrıca `PrimaryButton`,
  `SecondaryButton`, `DangerButton` kısayolları. `preview__ChatButton` / `unstable__ChatButton`
  kararsız — kullanılmaz.
- **TEDY durumu:** **Kullanılıyor** (21 dosya). Tek birincil kuralı TEDY'de daha katıdır (İ1, S12):
  Bugün/İşler'in birincili `NextThing.tsx` "Başla"; `HomeworkTracker.tsx` bilinçli tertiary.
  Sapmalar: yüzen asistan başlatıcısı `asistan/AsistanBaslatici.tsx` her sayfada `kind="primary"
  hasIconOnly`, `Modules.tsx` her kartta `kind="primary"` "Aç" (B17). `secondary` olumlu eylemde
  ve birincilsiz: "Yaptım" (`NextThing.tsx`), "Belge ekle" (`YuklemeAlani.tsx`) — Carbon ve Yüzey
  §2.6 ikisi de ghost/tertiary der (B58). Danger hiç yok; sohbet ve not "Sil"
  (`SohbetListesi.tsx`) ve belge "Kaldır" onaysız ghost — Carbon (danger + onay modalı) ve İ5
  (geri alınabilirlik) ikisini de karşılamıyor (B23). Karar S40 (2026-10-10): geri alınabilir düşük etkili eylem
  onaysız + "Geri al"; geri alınamaz silme danger `Modal`, başlık ve birincil düğme nesneyi adlandırır. Düğmeyle gezinme:
  `Modules.tsx` "Aç"/"Modüllere dön" (Books doğru: `<Link>`; B58). Boy: 57 boyutlu düğmenin 44'ü `sm`;
  telefon hedefi yamalarla (S18, B8). Yükleniyor: `HomeworkTracker.tsx` düğmeyi `InlineLoading` ile
  değiştiriyor (Carbon'un inline loading kuralına uygun, 1.17); `NextThing.tsx` metni
  "Kaydediliyor…" yapıp devre dışı bırakıyor (S36: tek eylem tek `InlineLoading`, B69). Birincil düğme her kipte
  `$button-primary` (Blue 60), öğretmen kiplerinde de (S35, 2026-10-10; Ç1'in kararı); bugün öğretmen kiplerinde
  `--cds-button-primary` ders vurgusuna boyanıyor (B68). Modül referansının "birincil hep Blue 60" kuralı artık iki
  çalışma zamanının ortak kuralıdır (talimatname §3.2). Modül şablonu `.btn--ghost` kenarlı
  (Carbon'un tertiary şekli), devre dışı `opacity: .45` (§9). Talimatname §4, §3.7.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/button/guidelines/

<a id="checkbox"></a>

### 1.5 Onay kutusu (`checkbox`)

- **Ne için:** Birbirinden bağımsız çoklu seçim; bir kutuyu işaretlemek diğerlerini etkilemez.
- **Kullan:** Formlar; data table'da filtre ve toplu eylem; koşullar; ebeveyn/çocuk alt seçimli
  listeler.
- **Kullanma:** Tek seçenek seçilecekse (→ radio button); sonuç anında uygulanıyorsa (→ toggle).
- **Varyantlar:** Tek kutu, grup (dikey ya da yatay; mümkünse dikey); iç içe (ebeveyn/çocuk).
- **Ölçüler ve token'lar:** Kutu 16 × 16, kenar 1 px; odak kenarı 2 px + 1 px iç. Grup etiketi
  `$label-01` 12 `$text-secondary`, 8 px (`$spacing-03`) altında; etiket `$body-compact-01` 14
  `$text-primary`, kutudan 8 px (`$spacing-03`); öğeler arası 4 (`$spacing-02`). İşaretsiz kenar
  `$icon-primary`; işaretli zemin `$icon-primary`, tik `$icon-inverse`. Formda sonraki bileşene ≥ 32
  px (`layout-03`), sıkışıkta 24/16. Hata kenarı `$support-error`; uyarı ikonu `$support-warning`.
- **Durumlar:** İşaretsiz, işaretli, kararsız (indeterminate); odak, devre dışı, salt okunur, hata,
  uyarı. Ebeveyn: tümünü seçer/bırakır; çocuklar kısmen seçiliyse kararsız.
- **Erişilebilirlik:** Kutu da etiket de tıklanır. `Tab`/`Shift-Tab`, `Space` değiştirir. Grup
  `<fieldset>`/`<legend>`; kararsız = `aria-checked="mixed"`. Çok sütunlu ızgarada anlamlı sekme
  sırası işaretlenir. 1.114.0: dört satır geçti.
- **İçerik:** Etiket üç kelimeden az, cümle düzeni; üç noktayla kırpılmaz; kayan metin kutunun
  altına, kutu ve etiket üstten hizalı (dikey ortalanmaz). Görünmese de kodda etiket şart.
- **AI varyantı:** Grup etiketine ya da tek etiketlere AI etiketi, boy **mini**; gerisi aynı.
- **React:** `Checkbox`, `CheckboxGroup`, `CheckboxSkeleton`, `InlineCheckbox` (`indeterminate`,
  `decorator`).
- **TEDY durumu:** **Uygun ama kullanılmıyor** (Carbon `Checkbox` yok). Tek yerel kutu
  `StudentProfile.tsx` "Ders tekrar ediyor": 1.5 rem (24 px) ve `accent-color: var(--cds-interactive)`
  (Carbon: 16 px, `$icon-primary`). Yeni çoklu seçimde Carbon `Checkbox`/`CheckboxGroup` kullanılır;
  telefon hedefi kutunun kendisiyle değil etiketin tıklanabilirliğiyle karşılanır (S18). Modül
  şablonunda onay kutusu yok.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/checkbox/guidelines/

<a id="code-snippet"></a>

### 1.6 Kod parçası (`code-snippet`)

- **Ne için:** Okurun bir dizgeyi kolayca kopyalaması; anahtar sözcükleri öne çıkarmak (çoğunlukla
  kod belgelerinde).
- **Kullan:** Kopyalanacak komut, kod, anahtar.
- **Kullanma:** Okurun değiştirmesi gereken değer için (salt okunurdur).
- **Varyantlar:** Inline (cümle içinde) · single line · multi-line (göster/gizle). Inline çok satırlı
  olmaz.
- **Ölçüler ve token'lar:** Kod metni `$code-01` 12/400. Single line: yükseklik 40 (sayfa rem'i
  "3" yazıyor — sayfa tutarsız), azami genişlik 768 / 48 rem, sağ dolgu 48 (`$spacing-09`), sol 16
  (`$spacing-05`); uzun metin yatay kayar. Multi-line: asgari yükseklik 288 / 18 rem, azami 768
  genişlik, dolgu 16, sağ 40 (`$spacing-08`); kopya düğmesi 32, "Show more" düğmesi 40; dokuz
  satırı aşınca dikey kaydırma. Inline: yükseklik 16, köşe 2 px, yan dolgu 8 (`$spacing-03`).
  Renk: kap `$layer` (bağlamsal), kod `$text-primary`, inline hover `$layer-hover`, aktif
  `$layer-active`, odak `$focus`; kopya düğmesi = ghost yalnız ikon düğme token'ları. Erişilebilir
  sözdizimi renkleri ayrı bir CodePen'de; değerler sayfada belirtilmemiş.
- **Durumlar:** Kopya varsayılan açık; ikonun onay ipucu vardır ("Copied to clipboard").
- **Erişilebilirlik:** Inline parça ve kopya düğmeleri `Tab` + `Space`/`Enter`; kopyadan sonra odak
  düğmede kalır; single line ok tuşlarıyla kaydırma için ek sekme durağı alır. Inline kod düğme
  olarak gerçeklenir. 1.114.0: ilk çizim **kısmen test edildi**, diğerleri geçti.
- **İçerik:** Doğru sözdizimi (kopyalanan kod bozulmasın); ipucu "Copied to clipboard"; düğme
  "Show more" / "Show less".
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `CodeSnippet` (`type`: single, multi, inline; `feedback`), `CodeSnippetSkeleton`,
  `CopyButton`, `Copy`.
- **TEDY durumu:** **Kullanılmaz (TEDY belge sitesi değil).** Okura kopyalanacak kod verilmez.
  Satır içi `<code>` (Markdown ters tırnağı, KaTeX yedeği) `utils/markdown.tsx`,
  `asistan/markdownEklentileri.ts`, `components/Formul.tsx`'te; stil `code-01` + `$layer-02`, yan
  dolgu 2 px (Carbon 8 px), köşe yok — kopya düğmesi gerekmez. Modüllerde Plex Mono yalnız sayı ve
  formül için.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/code-snippet/guidelines/

<a id="contained-list"></a>

### 1.7 Kapsanmış liste (`contained-list`)

- **Ne için:** Kart, kenar çubuğu ya da açılır içindeki tek başlıklı liste; satırlarda satır içi
  eylem ve etkileşimli öğe olabilir.
- **Kullan:** Küçük alan ve açılırlar; satır içi eylemler; aynı yapıdaki öğeleri gruplamak.
- **Kullanma:** Bir düzeyden derin ya da karmaşık/uzun içerik (→ data table); birden çok sütun
  başlığı (→ structured list).
- **Varyantlar:** On-page (kalıcı bağlam: kart, kenar çubuğu) · disclosed (geçici bağlam: popover,
  yükseltilmiş katman). Değiştiriciler: içe çekik satır ayırıcıları, tıklanabilir satırlar (kalıcı
  görsel işaret yok, geliştiriciye not edilir), satır içi eylem, başlıkta arama.
- **Ölçüler ve token'lar:** On-page sm 32 · md 40 · lg 48 (varsayılan) · xl (başlık 48, satır 64);
  disclosed başlık 32, satır 48. (Specifications'daki "Structure" tablosu başlıkları ters veriyor —
  sayfa tutarsız; Size tabloları ve guidelines birbirini tutuyor.) Başlık ve satır yan dolgusu 16
  (`$spacing-05`); ikon 16 + 16 dolgu. Üst üste on-page listeler 16 px aralıklı, disclosed listeler
  0. On-page başlık `$heading-compact-01` 14/600 `$text-primary`; disclosed başlık `$label-01` 12
  `$text-secondary` `$layer` üzerinde; öğe `$body-01` 14; ayırıcı `$border-subtle`; hover
  `$layer-hover`; aktif `$layer-active`.
- **Durumlar:** Varsayılan liste etkileşimsiz; etkileşimli varyantlarda hover, odak, aktif, devre
  dışı.
- **Erişilebilirlik:** `<ul>`/`<li>`, başlık `aria-labelledby` ile bağlı; çalışan her satır ya da
  eylem `<li>` içinde `<button>`. `Tab` ile gezilir, `Space`/`Enter` etkinleştirir; bir satırda
  birden çok sekme durağı olabilir. 1.114.0: dört satır geçti.
- **İçerik:** Başlık 1–3 kelime, cümle düzeni; satırlar aynı yapıda; birkaç kısa satır olabilir,
  paragraf olmaz.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `ContainedList` (`kind`: `on-page` | `disclosed`; `size`: `sm` | `md` | `lg` | `xl`;
  `isInset`), `ContainedListItem`.
- **TEDY durumu:** **Uygun ama kullanılmıyor.** Aynı şekildeki listeler elle yazılmış:
  `SohbetListesi.tsx` (başlık düğmesi + satır içi "Yeniden adlandır"/"Sil"), `DahaFazla.tsx`
  (bağlantı satırları), ek listeleri (`next-thing__attachments`, `announcements-detail__ekler`).
  Yeni tek başlıklı liste `ContainedList` ile yazılır; telefon satır yüksekliği lg 48 (S18).
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/contained-list/guidelines/

<a id="content-switcher"></a>

### 1.8 İçerik değiştirici (`content-switcher`)

- **Ne için:** Aynı ya da ilişkili içeriğin **alternatif görünümleri** arasında geçiş (ızgara ↔
  tablo; "Tümü / Okunmuş / Okunmamış").
- **Kullan:** Aynı içeriği farklı biçimde göstermek, daraltmak, sıralamak; bir sekmenin içinde alt
  düzeyde.
- **Kullanma:** Ayrı içerik alanları (→ tabs); ikili girdi evet/hayır (→ toggle); değer seçimi
  (bir kip, bir öğretmen) — bu bir girdidir (→ radio group ya da dropdown).
- **Varyantlar:** Yüksek kontrast (varsayılan; sayfa üstü) · düşük kontrast (kart, modal, birincil/
  ikincil düğme yanı); "şüphedeysen yüksek kontrast". Metin ya da ikon; aynı değiştiricide
  karıştırılmaz.
- **Ölçüler ve token'lar:** sm 32 · md 40 · lg 48; ikon 16/16/20. Köşe **4 px** (token yok). Etiket
  dolgusu 16 (`$spacing-05`); ikon dolgusu sm 8 / md 12 / lg 14. Bütün sekmeler eşit genişlikte; en
  uzun etiketin sağında ≥ 16 px; ikon sekmede genişlik = yükseklik. En az iki seçenek. Yüksek
  kontrast: seçili `$layer-selected-inverse` + `$text-inverse`; seçilmemiş `$text-secondary`, kenar
  `$border-inverse`, hover `$background-hover`. Düşük kontrast: `$content-switcher-background`,
  seçili `$content-switcher-selected` + `$heading-compact-01` 14/600; diğer metin `$body-compact-01`.
- **Durumlar:** Seçili/seçilmemiş, hover, odak, devre dışı (tümü ya da tek sekme). Her zaman bir
  sekme seçili; varsayılan genellikle ilk.
- **Erişilebilirlik:** Tek sekme durağı; `Left`/`Right` sekmeler arasında. Otomatik (odak = seçim) ya
  da elle (`Enter`/`Space` seçer) — hangisi olduğu tasarımda işaretlenir. `tablist`, her sekme
  `role="tab"` düğme, `aria-selected` + `tabindex`. 1.114.0: dört satır geçti.
- **İçerik:** 2–3 kelime, isim ya da isim öbeği, eylem gibi değil; cümle düzeni; ≤ 3 kelime. Taşma:
  üç nokta + tarayıcı ipucu; sığmıyorsa ikon değiştirici.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `ContentSwitcher` (`size`, `lowContrast`, `selectionMode`), `Switch`, `IconSwitch`.
- **TEDY durumu:** **Kullanılmaz (öğretmen kipi bir girdidir).** Öğretmen seçici
  `OgretmenSecici.tsx` yerel radyo grubu çipleri: beş eşit segment 390 px'te "Matematik"i kesti ve
  IBM Equal Access `label_content_exists` ihlali ölçüldü (asistan B1 planı kararı; `carbon-asistan-ogretmen*.spec.ts`
  sabitler). Dersler'de sekme doğru bileşen (1.32), hafta seçimi `Dropdown` (1.11). Bir gün gerçek bir
  görünüm değişimi (liste ↔ ızgara) gelirse `ContentSwitcher` kullanılır; Carbon'un 4 px köşesi
  TEDY'nin köşe basamağında yoktur (S10) — benimsenmeden önce karar yazılır.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/content-switcher/guidelines/

<a id="data-table"></a>

### 1.9 Veri tablosu (`data-table`)

- **Ne için:** Veriyi düzenleyip göstermek; sütun sıralama, satır açma, tekli/toplu eylem; araç
  çubuğunda arama, filtre, ayarlar.
- **Kullan:** Okurun belli bir veriye gidip görevi bitirmesi gerektiğinde; bütün kaynaklarını
  göstermek.
- **Kullanma:** Daha karmaşık gösterim gerekiyorsa; elektronik tablo yerine. Basit liste →
  structured list; tek başlıklı → contained list.
- **Varyantlar:** Default · with selection (radyo tekli, onay kutusu çoklu) · with expansion. Zebra
  değiştiricisi. Araç çubuğu, toplu eylem çubuğu, sayfalama.
- **Ölçüler ve token'lar:** Satır xs 24 · sm 32 · md 40 (varsayılan, en yaygın) · lg 48 · xl 64
  (yalnız iki satırlık veri; `padding-top: 16px`). Başlık satırı her zaman satırla aynı yükseklik.
  Araç çubuğu 48 (lg/xl ile) ya da 32 (sm/xs ile); toplu eylem çubuğu ve sayfalama satır
  yüksekliğinde (xl'de büyük boy). Sütun arası 16 (`$spacing-05`); tablo başlığı üst 16 / alt 24 /
  yan 16; açık panel üst/sağ 16, sol 48 (`$spacing-09`), alt 24. En az üç sütun. Tip: tablo başlığı
  `$heading-03` 20/400, sütun başlığı `$heading-compact-01` 14/600, satır `$body-compact-01` 14/400.
  Renk: sütun başlığı `$layer-accent` (hover `-hover`, aktif `-active`); satır `$layer` +
  `$text-secondary`, ayırıcı `$border-subtle`, hover `$layer-hover` + `$text-primary`, seçili
  `$layer-selected`; zebra `$layer-accent`; toplu eylem çubuğu `$background-brand` + `$text-on-color`.
- **Durumlar:** Satır hover **her zaman açık**, etkileşimsiz satırda bile. Sıralama üç durum
  (`arrows`, `arrow--up`, `arrow--down`); yalnız sıralanan sütun ikon gösterir, diğerleri hover/odakta.
  Toplu eylem kipinde satır eylemleri devre dışı, iptal en sağda. Satır eylemi < 3 ise satır içi
  ikon düğme, değilse taşma menüsü (kalıcı; `overflowMenuOnHover` ile yalnız hover, dokunmatikte
  hep görünür). Toplu açma varsayılan gösterilmez. Yükleniyorsa iskelet, döner gösterge değil.
- **Erişilebilirlik:** Sıralanabilir başlıklar `Tab` + `Space`/`Enter`; `aria-sort`. Tablo
  erişilebilir ad taşır (`aria-label`, `aria-labelledby` ya da `title`; IBM kuralı
  `aria_accessiblename_exists`). Sıralanabilirliğin kalıcı görsel işareti olmadığından tasarımda
  işaretlenir. Hücre içi denetimler sekme sırasında. Açılan satırlar akordeon gibi. 1.114.0: dört
  satır geçti.
- **İçerik:** Başlık verinin ortak noktasını söyler, açıklama altında; cümle düzeni. Sütun başlığı
  1–2 kelime; uzunsa iki satır, sonra kırpma + ipucu.
- **AI varyantı:** Kararlı. Bütün tablo: `$ai-drop-shadow`, `$ai-inner-shadow`, `$ai-aura-start-sm` →
  `$ai-aura-stop`, kenar `$ai-border-start` → `$ai-border-end`, etiket **large**. Tek hücre: inline
  etiket **medium**, katman yok. Satır/sütun: aura + `$ai-border-strong`, etiket **mini**.
- **React:** `DataTable`, `Table`, `TableHead`, `TableHeader`, `TableBody`, `TableRow`, `TableCell`,
  `TableContainer`, `TableExpandHeader`, `TableExpandRow`, `TableExpandedRow`, `TableSelectAll`,
  `TableSelectRow`, `TableToolbar`, `TableToolbarContent`, `TableToolbarSearch`, `TableToolbarMenu`,
  `TableToolbarAction`, `TableBatchActions`, `TableBatchAction`, `TableActionList`,
  `TableDecoratorRow`, `TableSlugRow`, `DataTableSkeleton` (`size`, `useZebraStyles`, `isSortable`,
  `overflowMenuOnHover`).
- **TEDY durumu:** **Kullanılıyor** — `WeeklySchedule.tsx` (`size="xs"`) ve `GradeTable.tsx`
  (`size="sm"`, `TableExpandRow` ek bilgi için, Türkçe `translateWithId`; Carbon'un açılır satır
  kuralının birebir örneği). Program tablosu sapması (B50): `size="xs"` (24 px) etiketli ama
  `ted-theme.scss` satırı 52 px, başlığı 40 px yapıyor; Carbon'da başlık = satır yüksekliği ve iki
  satırlı hücrenin boyu xl 64'tür; hücre metni 12 px `label-01` (Carbon 14 px). Kaydırma kabı yalnız
  kaydığında `tabIndex=0 role="region"` ve adlı (axe ↔ IBM ölçümüyle, korunur). Bugün sütunu ve
  aktif ders satırı Carbon'da olmayan TEDY durumlarıdır (Yüzey). Zebra, sıralama, araç çubuğu, toplu
  eylem, sayfalama yok — İ6 ile uyumlu. Toplu eylem çubuğunun `$background-brand` zemini İ8'in "görünüm
  başına bir büyük renkli yüzey" bütçesini harcar; gelirse yeniden token'lanır. Asistan tabloları
  `asistan/Tablo.tsx` elle yazılmış (`th scope="col"`, adlı kaydırma bölgesi) çünkü Carbon AI Chat'in
  tablosu axe/IBM ihlali veriyor (S13). Modül şablonu `vizTable()` Carbon DataTable eşlemesi; zebra
  hep açık ama `$layer-01` üzerinde (Carbon `$layer-accent`) (§9). Talimatname §8.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/data-table/guidelines/

<a id="date-picker"></a>

### 1.10 Tarih seçici (`date-picker`)

- **Ne için:** Geçmiş, bugün ya da gelecek tarih ve saat seçmek; tarihin türü varyantı belirler.
- **Kullan:** Kesin, yaklaşık ya da akılda kalan tarih; planlama.
- **Kullanma:** Göreli zaman ("şimdi", "bir saat sonra") için (→ select); biçim hatası riskliyse gün,
  ay, yıl için ayrı alanlar düşünülür. Slider tarih seçici olarak kullanılmaz.
- **Varyantlar:** Simple date input (akılda kalan, takvimsiz; yaklaşık geçmiş tarih) · calendar
  picker (tekli ya da aralık; günün diğer günlerle ilişkisi önemliyse, planlama) · time picker. Stil:
  default (etiket üstte) · fluid (etiket alanın içinde). Takvim her zaman yazılabilir alanla gelir.
- **Ölçüler ve token'lar:** Alan sm 32 · md 40 (varsayılan) · lg 48; fluid 64. Takvim menüsü sabit
  336 × 288 px; gün hücresi 40 × 40; bugün noktası 4 × 4; takvim alanın sol kenarına hizalı. Alan
  metni `$code-02` 14 (eş aralıklı); ay/yıl `$heading-compact-01` 14/600; gün `$body-compact-01`.
  Seçili gün `$background-brand` + `$text-on-color`; aralık `$highlight`; "bugün" sayfada v10 adıyla
  `$link-01` (v11'de `$link-primary`). Diğerleri ortak alan anatomisi (1.0).
- **Durumlar:** Etkin, hover, odak, açık, hata, uyarı, devre dışı, iskelet, salt okunur. Çok alanlı
  seçicide hata yalnız sorunlu parçaya. En küçük/en büyük tarih; geçmiş seçilemiyorsa en küçük = bugün.
- **Erişilebilirlik:** Etiket şart ("arrival date"/"departure date" gibi açık); tasarım notu
  gerekmez; WAI-ARIA APG tarih seçici diyalog kalıbı. Takvim: ikonla ya da alana odakla açılır; ok
  tuşları + `Enter` seçer; `Esc` kapatır. Tuş tablosu sayfada belirtilmemiş. 1.114.0: ek durumlar
  tamamlanmamış; diğerleri geçti.
- **İçerik:** Etiket ≤ 3 kelime, cümle düzeni; aralıkta başlangıç ve bitiş etiketi. Biçim etiketin
  yanında parantez içinde ya da yardım metninde; **yalnız placeholder'da biçim sorunludur** (yazınca
  kaybolur). Saat: `11:30`; 12 saatlikte AM/PM büyük harf, noktasız; belirli saat saat dilimi taşır.
- **AI varyantı:** Aura `$ai-aura-start-sm` → `$ai-aura-stop`, alt çizgi `$ai-border-strong`, etiket
  **mini**; kullanıcı değiştirirse "revert to AI" düğmesi.
- **React:** `DatePicker`, `DatePickerInput`, `DatePickerSkeleton`, `TimePicker`, `TimePickerSelect`;
  `FluidDatePicker`, `FluidDatePickerInput`, `FluidTimePicker`, `FluidTimePickerSelect` (ayrıca
  `unstable__`/`preview__` takma adları); `preview__DatePicker` (yeni gerçekleme) kararsız —
  kullanılmaz.
- **TEDY durumu:** **Uygun ama kullanılmıyor.** Özel ders formu yerel `<input type="date">` ve iki
  `<input type="time">` (`StudentProfile.tsx`), Carbon md anatomisini kopyalayan stille; biçim
  yardımı ve en küçük tarih yok; iki saat alanı telefonda yan yana (Carbon formu mobilde tek sütun).
  `OdevOnayKarti.tsx` "Teslim" alanı `TextInput` + `placeholder="gg.aa.yyyy"` — biçim yalnız
  placeholder'da (B56). TEDY saat dilimi sabit Europe/Istanbul, 24 saat. Yeni tarih girişi:
  `DatePicker` simple ya da calendar, biçim yardım metninde. Talimatname §5 "form".
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/date-picker/guidelines/

<a id="dropdown"></a>

### 1.11 Açılır liste: dropdown, multiselect, combo box (`dropdown`)

- **Ne için:** Listeden seçim. Dropdown tek seçim; multiselect çoklu seçim ve süzme; combo box çok
  uzun ya da önceden tanımsız listeden seçim veya özel değer yazma.
- **Kullan:** Formlar, modal, yan panel; **sayfa içeriğini süzmek ya da sıralamak**.
- **Kullanma:** İki seçenek (→ radio); iç içe ya da karmaşık bilgi; ağırlıkla form tabanlı ya da
  sık mobil kullanım (→ yerel select). Select'te süzme ve çoklu seçim yoktur; dropdown'da vardır.
  Liste çok uzun ya da veritabanından geliyorsa combo box.
- **Varyantlar:** Dropdown · multiselect (seçim sayısı etiketi, "tümü" ebeveyn kutusu isteğe bağlı,
  süzülebilir multiselect) · combo box · inline (görünür etiket solda; görünür etiket yoksa
  erişilebilir ad zorunlu; yalnız dropdown ve multiselect, süzme yok). Stil default · fluid.
- **Ölçüler ve token'lar:** xs 24 · sm 32 · md 40 (varsayılan) · lg 48; fluid alan 64, menü öğesi
  64 ya da sıkışık 40. Açık menüde her öğe alan yüksekliğinde. Genişlik sınırı yok; açık ve kapalı
  aynı genişlik. Alan sağ dolgusu 48 (`$spacing-09`), combo box 72; multiselect sayı etiketi 24
  yükseklik. Menü aşağı açılır, alt kenara yakınsa yukarı; 6. öğeden sonra kaydırma ve son öğenin
  yarısı görünür. Menü öğesi `$layer` + `$text-secondary`, hover `$layer-hover` + `$text-primary`,
  seçili `$layer-selected`; sayı etiketi `$background-inverse` + `$text-inverse`. Gölge: 1.0 ortak
  kural. Gerisi ortak alan anatomisi.
- **Durumlar:** Etkin, hover, odak, hata, uyarı, devre dışı, iskelet, salt okunur. Multiselect seçim
  yaparken açık kalır; yeniden açılınca seçilenler alfasayısal sırayla üste.
- **Erişilebilirlik:** Dropdown `Enter`/`Space`/`Down` açar, `Space`/`Enter` seçip kapatır,
  `Esc`/`Tab` değiştirmeden kapatır. Multiselect: kapalı alanda `Delete` tüm seçimi temizler. Combo
  box: `Space` seçmez, filtreye boşluk yazar; `Enter` vurgulananı seçer. Dropdown/multiselect
  `button` + `aria-haspopup="listbox"`; combo box `role="combobox"` + `aria-autocomplete="list"` +
  `aria-controls` → `role="listbox"`; hepsi `aria-expanded`. 1.114.0: Dropdown, Multi Select, Combo
  Box ek durumlar tamamlanmamış; diğer satırlar geçti.
- **İçerik:** Etiket tek satır, **asla placeholder'a feda edilmez**; yardım metni etiketin altında;
  placeholder önemli bilgi taşımaz ("Choose an option"); seçenek ≤ 3 kelime, dekoratif ikon yok,
  Carbon **alfabetik sıra önerir**; "tümü" kutusu eylem değil seçenek adıdır ("All"). Taşma: üç
  nokta + Carbon ipucu.
- **AI varyantı:** Kararlı. Aura `$ai-aura-start-sm` → `$ai-aura-stop`, alt çizgi `$ai-border-strong`,
  etiket **mini**, "revert to AI".
- **React:** `Dropdown` (`titleText`, `hideLabel`, `size`, `readOnly`, `decorator`),
  `DropdownSkeleton`, `MultiSelect`, `FilterableMultiSelect`, `ComboBox` (`ListBox` bileşen olarak
  dışa aktarılmaz, yalnız `ListBoxProps` … tipleri);
  `FluidDropdown`, `FluidMultiSelect`, `FluidComboBox` (+ `…Skeleton`; `unstable__`/`preview__`
  takma adları kararsız).
- **TEDY durumu:** **Kullanılıyor** — `CourseContent.tsx` hafta süzgeci `Dropdown size="sm"`: doğru
  bileşen (aynı içeriği süzmek), ama `titleText=""` + `label="Hafta"` ile **görünür etiket yok**;
  `selectedItem` hep dolu olduğu için "Hafta" yer tutucu olarak da görünmüyor (B40). Seçenekler kronolojik, alfabetik değil: TEDY'nin zaman ve aciliyet
  sırası (İ2/İ7) Carbon'un önerisinden önce gelir — bilinçli sapma (S33), kural olarak kalır. Multiselect
  ve combo box kullanılmıyor (uygun, ihtiyaç yok). Talimatname §4, §5 "form".
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/dropdown/guidelines/

<a id="file-uploader"></a>

### 1.12 Dosya yükleyici (`file-uploader`)

- **Ne için:** Kullanıcının kendi içeriğini yüklemesi; çoğunlukla formda, tek başına da.
- **Kullan:** Bir ya da çok dosya; sürükle-bırak; yükleme sürecini göstermek.
- **Kullanma:** Çok dosyalı yüklemeyi modal içinde (dosyalar dikey yığılır).
- **Varyantlar:** File uploader (düğme dosya penceresini açar) · drag and drop (bırakma alanı; çoklu
  ya da tek dosya kipi; tek kipte başarılı yüklemeden sonra alan kaybolur).
- **Ölçüler ve token'lar:** lg 48 · md 40 (varsayılan) · sm 32; düğme ve dosya satırı aynı
  yükseklikte. Dosya satırı genişliği 288 (düzene göre değişir), yan dolgu 16, alt boşluk 8; sil
  ikonu 16, yan boşluk 16. Başlık `$heading-compact-01` 14/600; açıklama, bırakma metni, dosya adı
  `$body-compact-01` 14; hata `$label-01` 12. Renk: bırakma metni `$link-primary`, alan kenarı
  `$border-strong` (hover/odak `$focus`), dosya kabı `$field`, yüklendi tiki `$interactive`, hata
  kenarı `$support-error`. Bırakma alanı ölçüleri sayfada belirtilmemiş (yalnız görsel).
- **Durumlar:** Dosya başına yükleniyor → başarılı → yüklendi; dosya başına hata (tek ya da çok
  satır); yükleyicinin bütününe ait hata inline notification. Sürüklerken alan kenarının rengi ve
  kalınlığı değişir.
- **Erişilebilirlik:** Düğme ve bırakma alanı düğmedir (`Tab`, `Enter`/`Space`); dosya penceresi
  kapanınca odak çağıran öğeye döner; her dosyanın "x"i sekme sırasında ve dosya adıyla programatik
  olarak bağlı; hata mesajları yardımcı teknolojiye açık. 1.114.0: dört satır geçti.
- **İçerik:** Başlık ("Upload files"), **açıklama boyut ve biçim sınırlarını söyler**, düğme fiil
  ("Add files"); dosya adı taşarsa üç nokta + ipucu. Sayfada zaten birincil varsa yükleme düğmesi
  tertiary.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `FileUploader`, `FileUploaderButton`, `FileUploaderDropContainer`, `FileUploaderItem`,
  `Filename`, `FileUploaderSkeleton` (`labelTitle`, `labelDescription`, `buttonLabel`,
  `filenameStatus`).
- **TEDY durumu:** **Kullanılıyor (yerel karşılık).** `YuklemeAlani.tsx` gizli `<input type="file">`
  (dokunmatikte ayrıca `capture="environment"`) + `Button kind="secondary"` "Belge ekle" (birincilsiz
  secondary, 1.4) ya da ghost ikon düğmeler. Sınırlar (görsel 12 MiB, PDF 10 MiB/50 sayfa,
  docx/txt 5 MiB, mesaj başına 4 dosya) okura **önceden söylenmiyor**: boyut ve sayfa sınırı yalnız sunucu
  hatası, dört dosya sınırı seçimden sonra istemci hatası olarak geliyor (D3; B59). Dosya satırı `asistan/GirisEkleri.tsx`: hata `role="alert"` ✓, kaldırma
  düğmesi `aria-label="Kaldır: <ad>"` ✓, yükleniyor düz metin (Carbon üç durumu yok). Sürükle-bırak
  bütün sohbet alanında, görünür alan ve kenar değişimi yok; klavye yolu düğmeler. Modülde yükleme
  yok. Talimatname §5 "form".
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/file-uploader/guidelines/

<a id="form"></a>

### 1.13 Form (`form`)

- **Ne için:** Alanları bir başlık, gövde ve alt bilgi (gönder/vazgeç) içinde toplamak; ayrıntı form
  kalıbında.
- **Kullan:** Veri girişi ve gönderme.
- **Kullanma:** Sayfada belirtilmemiş (kalıp sayfasına bakılır).
- **Varyantlar:** Default (etiket dışarıda; sm/md/lg alan; bileşenler arası 32 px) · fluid (etiket
  içeride; tek boy 64; aralıksız, 1 px oluk).
- **Ölçüler ve token'lar:** Default: öğeler arası 32 (`$spacing-07`), başlık altı 40 (`$spacing-08`),
  iki sütun arası 32, düğmeler üstü 48 (`$spacing-09`). Fluid: öğe aralığı 0, oluk 1 px. Mobilde tek
  sütun; iki sütunlu satır grup olarak büyür (biri hata verip uzarsa öteki de). Default form geniş
  oluk ve sütuna yaslı; dar oluk (16) formda kullanılmaz. Başlık `$heading-03` (sayfa 28 px yazıyor,
  data table sayfası 20 — sayfa tutarsız); etiket `$label-01`; alan `$body-compact-01`; yardım
  `$helper-text-01`; hata `$label-01`.
- **Durumlar:** Etkin, aktif, odak, hata, uyarı, devre dışı, iskelet, salt okunur (1.0 ortak kural).
- **Erişilebilirlik:** `<form>` ile sarılır; zorunluluk programatik (`aria-required` ya da etiket);
  yardım ve talimat `aria-describedby`; satır içi hata ve uyarı programatik bildirilir. Zorunlu/
  isteğe bağlı işareti varsa formun başında açıklanır ("Aksi belirtilmedikçe bütün alanlar
  zorunludur"). Bilgi ikonu toggletip. 1.114.0: ilk çizim geçti; ek durumlar ertelenmiş; klavye
  uygulanamaz; elle test edildi.
- **İçerik:** Etiket her zaman var, kısa, cümle düzeni, **iki nokta yok**. Yardım metni tam cümle,
  noktalı, kalıcı; hata gelince yerini alır. Biçim gibi gerekli bilgi yardım metninde, yalnız
  ipucunda değil. Placeholder varsayılan yok, noktalamasız, asla etiket ya da kritik bilgi yerine.
  Azınlık işaretlenir: çoğu zorunluysa "(isteğe bağlı)", çoğu isteğe bağlıysa "(zorunlu)".
- **AI varyantı:** Kararlı. Bütün form: `$layer`, `$ai-drop-shadow`, `$ai-inner-shadow`, aura
  `$ai-aura-start-sm` → `$ai-aura-stop`, kenar `$ai-border-start` → `$ai-border-end`, etiket
  **large**; kısmi AI'da yalnız AI bileşenleri.
- **React:** `Form`, `FormGroup`, `FormItem`, `FormLabel`, `FluidForm`.
- **TEDY durumu:** **Kullanılıyor (yerel `<form>`).** `AlistirmaKarti.tsx`, `StudentProfile.tsx`,
  eski `AssistantChat.tsx`; Carbon `Form`/`FormGroup` hiç import edilmiyor. `OdevOnayKarti.tsx` aday
  başına `fieldset`/`legend`, yardım metni tam cümle ✓, hata `role="alert"`, başarı `role="status"`;
  aralık 16 px (kart içi form — Carbon 32). `StudentProfile.tsx` "Özel Ders Ekle": Title Case
  etiketler, zorunlu/isteğe bağlı işareti yok, sonuç `window.alert` (D3; B22, B60), telefonda iki alan
  yan yana. Salt okunur aile görünümünde alanlar `disabled` (`OdevOnayKarti.tsx`, eski
  `AssistantChat.tsx`) — Carbon'a göre salt okunur olmalı (B42). Kural: sayfa formu `$spacing-07`,
  kart içi form adı konmuş daha küçük token ve gerekçesiyle (talimatname §5 "form").
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/form/guidelines/

<a id="inline-loading"></a>

### 1.14 Satır içi yükleniyor (`inline-loading`)

- **Ne için:** Bir eylemin işlendiğini, arka uç ayrıntısı vermeden göstermek (oluştur/güncelle/sil).
- **Kullan:** Anında olamayan ama kısa süren eylem; küçük veri yenileme.
- **Kullanma:** Sayfa yüklemesi (→ iskelet); aynı anda birden çok öğe ya da eylemde (ilk yükleme
  hariç).
- **Varyantlar:** Etiketli · yalnız ikon (bağlamı bir etiket veriyorsa, çoğunlukla alan içinde).
- **Ölçüler ve token'lar:** Döner gösterge ve tik 16 × 16. Metin `$body-compact-01` 14/400 (sayfa
  "0.75 rem" yazıyor — sayfa tutarsız) `$text-secondary`; iz `$border-interactive`, zemin
  `$border-subtle`; bitti `$support-success`, hata `$support-error`. Animasyon süresi sayfada
  belirtilmemiş.
- **Durumlar:** Inactive (gösterge yok) · active · finished (1,5 sn başarı, sonra isteğe bağlı
  `onSuccess`; fonksiyon yoksa kalıcı) · error (inactive olur, inline notification ya da form
  hatası). Bağlı denetimler yükleme boyunca devre dışı.
- **Erişilebilirlik:** Klavyeyle çalışmaz. Metin `aria-live="polite"` ile durum olarak okunur; metin
  yoksa SVG başlığı ("active", "finished", "error"). [paket] metin verilmezse ikon adı İngilizce
  `"loading"`. 1.114.0: ilk çizim geçti, ek durumlar ertelenmiş, klavye uygulanamaz, elle test edildi.
- **İçerik:** Etiket önerilir ve eylemin durumunu söyler: "Saving…" → "Saved"; hatada hata olduğunu.
  Bir düğme tetiklediyse gösterge o düğmenin yerine aynı yerde, aynı hizada çıkar.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `InlineLoading` (`status`, `description`, `iconDescription`, `successDelay` [paket]
  varsayılan 1500).
- **TEDY durumu:** **Kullanılıyor** — `HomeworkTracker.tsx` "Yaptım" düğmesinin yerine
  `description="Kaydediliyor" status="active"`, hata "Kaydedilemedi" `role="alert"`: Carbon'un yer ve
  dil kuralına uygun. `iconDescription` verilmediği için ikon adı İngilizce "loading" (B44). Diğer
  yerlerde metin değişimi, beş ayrı yazımla ("Ekleniyor…", "Ekleniyor...", "Yükleniyor", "Yükleniyor...",
  "Kaydediliyor…") — tek sözlük (İ9; B41). Yüzey §2.4 "dönen ikon yok" kuralı içerik yüklemesi
  içindir; tek eylem için tek bir `InlineLoading` İ6'nın "aynı anda tek hareket" ilkesine uyar —
  talimatname §5.2 ve S36 (2026-10-10 kararı) bu kapsamı yazar; `NextThing.tsx`'in metin değiştiren kaydı B69.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/inline-loading/guidelines/

<a id="link"></a>

### 1.15 Bağlantı (`link`)

- **Ne için:** Gezinme: uygulamada başka sayfa, başka site, aynı sayfada bir öğe, e-posta ya da
  telefon.
- **Kullan:** Bir yere gidiliyorsa.
- **Kullanma:** Veriyi, görünümü ya da durumu değiştiren eylemler (→ button); görsel bağlantı
  (→ tile). Çok bağlantı kalabalık yapar, satır içi olanları seyrek kullan.
- **Varyantlar:** Standalone (alt çizgisiz; hover/odak/aktifte çizgi; ikon alabilir) · inline (cümle
  içinde, altı çizili, ikonsuz).
- **Ölçüler ve token'lar:** small 12 `$helper-text-01`, yükseklik 16, ikon 16 · medium 14
  `$body-compact-01`, yükseklik 18, ikon 16 · large 16 `$body-compact-02`, yükseklik 22, ikon 20.
  Satır içi bağlantı çevresindeki metnin boyunda. Renk: metin ve ikon `$link-primary`, hover
  `$link-primary-hover`, aktif `$text-primary` / `$icon-primary`, ziyaret edilmiş `$link-visited`,
  devre dışı `$text-disabled` / `$icon-disabled`, odak ve aktif kenarı `$focus`. Gruplama aralığı
  (sağ 16, alt 4 ya da 8) bileşende gerçeklenmemiş tasarım önerisidir.
- **Durumlar:** Etkin, hover, odak, aktif, ziyaret edilmiş (varsayılan kapalı; seyrek), devre dışı.
  Tıklanabilir alan metnin tamamı (+ ikon).
- **Erişilebilirlik:** Sekme sırasında, `Enter` etkinleştirir; altı çizili değilse odakta çizilir.
  Bağlantı ve ziyaret rengi zeminle 4.5:1 ve çevre metinden ayırt edilir. Genel "devamını oku" metni
  benzersiz yapılır ya da `aria-describedby`/`aria-labelledby` ile bağlama bağlanır; aynı sayfada
  farklı hedefe aynı metin olmaz. 1.114.0: ilk çizim ve durumlar geçti, klavye uygulanamaz, elle
  test edildi.
- **İçerik:** Hedefi söyleyen ayırt edici metin. Dış bağlantıda "launch", iç bağlantıda "arrow right"
  ikonu yaygın; hangisi seçilirse tutarlı.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `Link` (`inline`, `visited`, `renderIcon`, `size`, `disabled`).
- **TEDY durumu:** **Kullanılıyor** — `PlatformProgress.tsx` dış platform bağlantıları
  `renderIcon={Launch}` (Carbon'un birebir örneği); `HomeworkTracker.tsx` "Tüm sınavlar" iç gezinme;
  `patterns/EkBaglantisi.tsx` ek bağlantısı ve "Kaynağında aç: <ad>" `aria-label`'ı (genel metne
  bağlam; kurala uygun). Sapmalar (B58, B41): dışarı açılan "Kaynağında aç" ve duyuru eki `Launch`
  taşımıyor; `.today-also__all` bağlantı gibi görünen ve `/isler`'e giden bir `<button>` (gezinme `<Link>`
  olur); "Modülü aç" kaynak panelinde her atıfta aynı metin. Modüllerde
  `<a>` yok (sandbox). Talimatname §3.7, §3.9.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/link/guidelines/

<a id="list"></a>

### 1.16 Liste (`list`)

- **Ne için:** İlişkili içeriği taranabilir biçimde vermek; sırasız (madde) ya da sıralı (numara).
- **Kullan:** Basit, ilişkili öğeler.
- **Kullanma:** Karmaşık veri, sıralama/süzme/seçim (→ data table); ayırıcılı temel hiyerarşi
  (→ structured list, contained list).
- **Varyantlar:** Unordered · ordered; iki düzey (iç içe); productive (`$body-01` 14) · expressive
  (`$body-02` 16).
- **Ölçüler ve token'lar:** Metin `$text-primary`; düzey 1 ve 2 alt boşluk 0; düzey 2 sol dolgu 16
  (`$spacing-05`). İmler: sırasız düzey 1 **kısa çizgi (en dash)**, düzey 2 kare; sıralı düzey 1
  sayı, düzey 2 harf. 10+ öğede sayılar sola (varsayılan) ya da sağa hizalı. Yalnız dikey; im
  ızgaraya yaslı, oluğa taşmaz.
- **Durumlar:** Etkileşimsiz (içindeki bağlantılar hariç).
- **Erişilebilirlik:** Yerel `ul`/`ol`/`li`; imler `::before`/`::marker` ile, ekran okuyucu okur;
  tasarım notu gerekmez. 1.114.0: klavye uygulanamaz.
- **İçerik:** İm ilk satıra üstten hizalı; uzun öğe kayar, kırpılmaz; öğeler dilbilgisi olarak
  paralel.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `UnorderedList`, `OrderedList` (`nested`, `native`, `isExpressive`), `ListItem`.
- **TEDY durumu:** **Kullanılmaz (Carbon list bileşeni); yerel liste kullanılıyor.** Bileşen
  listeleri `list-style: none` olan `<ul>`. Düzyazı listeleri (asistan, Markdown) Carbon'un
  sıfırladığı imleri geri getirir: **disc / decimal**, `li + li` arası `$spacing-03`, `::marker`
  `$text-secondary`, sıralıda kalın tablo rakamı (`AssistantChat.scss`, `utils/markdown.scss`).
  Carbon'un kısa çizgi/kare imi bir IBM sözleşmesidir, anayasada ölçülmüş bir kural değil; TEDY
  disc/decimal'de ve satır arası nefeste (12 yaşındaki okur) kalır — bilinçli sapma, tek karar,
  karıştırılmaz (İ9). Adımlar `:::adimlar` anlamsal `<ol aria-label="Adımlar">`. Talimatname §3.9.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/list/guidelines/

<a id="loading"></a>

### 1.17 Yükleniyor (`loading`)

- **Ne için:** Bir sürecin sürdüğünü göstermek; tam sayfa kaplama ya da bölüm içinde.
- **Kullan:** Beklenen süre **3 saniyeyi** aşıyorsa; veri getirme, yavaş hesap, gönderimden sonra
  bölümün işlenmesi.
- **Kullanma:** Aşamalı görünen içerik ve tam ekran yükleme (→ iskelet); kullanıcı etkileşimi
  gerekiyorsa (→ tooltip, progress indicator, notification); **aynı anda birden çok gösterge**.
- **Varyantlar:** Large (varsayılan; tam ekran, bölüm, modal, karo; arkasında örtü) · small (öğe
  içinde ya da yanında; örtüsüz; ilgili düğmeler devre dışı).
- **Ölçüler ve token'lar:** Large 88 / 5.5 rem, small 16 / 1 rem. İz `$interactive`; örtü
  `$overlay`; etiket (varsayılan yok) `$body-compact-01`.
- **Durumlar:** Inactive, active.
- **Erişilebilirlik:** Çalıştırılmaz; SVG başlığı "loading" okunur; `aria-live="assertive"`.
  Bitiş bildirilir: ya yeni içerik odağı alır ya da gizli bir durum mesajı (`role="status"`). [paket]
  varsayılan `withOverlay=true`, `description="loading"`. 1.114.0: ilk çizim geçti, ek durumlar
  ertelenmiş, elle test edildi.
- **İçerik:** Large altında kısa durum ("Loading data…"), varsayılan yok.
- **AI varyantı:** Sayfada belirtilmemiş. AI içeriğinin iskeleti için kararlı `AISkeletonText`,
  `AISkeletonIcon`, `AISkeletonPlaceholder` vardır (`unstable__`/`preview__` takma adları kullanılmaz).
- **React:** `Loading` (`withOverlay`, `small`, `description`); iskelet için `SkeletonText`,
  `SkeletonPlaceholder`, `SkeletonIcon`.
- **TEDY durumu:** **Kullanılmaz (büyük döner gösterge + örtü).** Yüzey §2.4 (S36): içerik iskeleti
  içeriğin şeklinde, içerik yüklemesinde dönen ikon yok, tek eylemde tek `InlineLoading`, 400 ms altı hiçbir şey. Uygulama: `SkeletonText`
  (`WeeklySchedule.tsx`, `PlatformProgress.tsx`, `ModuleViewer.tsx`, `Modules.tsx`,
  `DashboardHeader.tsx`), `SkeletonPlaceholder` (`CalendarEvents.tsx`). Carbon da sayfa ölçeğinde
  iskeleti tercih eder; TEDY'nin reddettiği tek durum bölümü kilitleyen spinner. Açıklar: 400 ms
  eşiği kodda yok (`useApi` ilk karede iskelet çiziyor); Bugün iskeleti stilsiz (B5); uygulama
  kabuğu düz "Yükleniyor..." metni; İşler'de "Yaptım" sonrası `role="status"` yok (Bugün'de var).
  Talimatname §5 "yükleniyor", §3.6.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/loading/guidelines/

<a id="menu"></a>

### 1.18 Menü (`menu`)

- **Ne için:** Bir denetime, alana, veri öğesine ya da görünüme ait eylemleri açan açılır bileşen;
  menü düğmesinden ya da sağ tıkla açılır.
- **Kullan:** Seyrek ve ileri seçenekleri gizlemek; bağlam menüsü; özelleştirilebilir eylemler.
- **Kullanma:** Statik seçenekli form ya da süzme (→ dropdown); çok ya da karmaşık girdi (→ popover).
- **Varyantlar:** Eylem öğesi, ayırıcı, alt menü (sağda caret), klavye kısayolu, tekli/çoklu
  seçilebilir öğe (öğenin önünde tik), tehlikeli öğe (hover'da kırmızı).
- **Ölçüler ve token'lar:** Öğe xs 24 · sm 32 · md 40 · lg 48; menü düğmesiyle tetikleniyorsa öğe =
  düğme boyu (xs düğmede yok). Genişlik en az 160, en çok 288 px; düğmeden asla dar değil. Öğe
  dolgusu 16 (seçilebilir, seçilmemiş: sol 40); ilk/son öğe ve ayırıcı yanı 4 (`$spacing-02`).
  Metin `$body-compact-01` 14. Renk: öğe `$layer` + `$text-secondary`, ayırıcı `$border-subtle`,
  hover `$layer-hover` + `$text-primary`, tehlikeli hover `$support-error` + `$text-on-color`, devre
  dışı `$text-disabled`; ikon `$icon-secondary`. Gölge: 1.0 ortak kural.
- **Durumlar:** Etkin, hover, odak, odak+hover, tehlikeli hover (+odak), devre dışı. Hiç izin
  verilmeyecek eylem devre dışı değil gizli. Bir öğeyi etkinleştirmek menüyü kapatır.
- **Erişilebilirlik:** Açılınca ilk öğe odakta; `Up`/`Down`; `Enter`/`Space` etkinleştirip kapatır;
  `Right`/`Left` alt menü; `Esc` kapatır. `ul role="menu"`, `li role="menuitem"`, seçilebilir
  `menuitemcheckbox`/`menuitemradio`, grup `role="group"`, alt menü ebeveyni `aria-haspopup` +
  `aria-expanded`. 1.114.0: ilk çizim geçti; ek durumlar ertelenmiş; odak **kısmen**; elle test
  edildi.
- **İçerik:** Kısa etiket; kırpılırsa tarayıcı `title` ipucu. En çok kullanılan üstte; çok öğe
  ayırıcıyla gruplanır. Bağlam ve taşma menüsü ≤ 12 öğe; menü düğmesi < 5 öğe. İç içe alt menüden
  kaçınılır.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `Menu`, `MenuItem`, `MenuItemDivider`, `MenuItemGroup`, `MenuItemRadioGroup`,
  `MenuItemSelectable`, `useContextMenu`.
- **TEDY durumu:** **Uygun ama kullanılmıyor.** Tek açılır gezinme Carbon `SideNavMenu` "Daha fazla"
  (7 ikincil rota) — eylem menüsü değil, gezinme (1.41); Carbon'un "menü düğmesinde < 5" sayısı ona
  uygulanmaz. Tek kayan yüzey senkron sağlık popover'ı, menünün gölgesini token biçimiyle taşır.
  Satırlarda en çok iki eylem var; eşiğe ulaşılmadı. Talimatname §4.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/menu/guidelines/

<a id="menu-buttons"></a>

### 1.19 Menü düğmeleri: menu button, combo button, overflow menu (`menu-buttons`)

- **Ne için:** Bir düğme + bir menü; dar alanda çok seçenek.
- **Kullan:** Menu button: eşit önemde eylemler (genellikle sayfa başlığında; tümüne ortak fiil
  öğelerde tekrar edilmez; farklı eylemlerse etiket "Actions"). Combo button: biri daha önemli
  (varsayılan eylem solda, kalanı ok menüsünde; yalnız primary). Overflow menu: satır ve kartlarda
  ek seçenekler; kartta üçten çok etkileşimli ikon varsa az önemliler taşmaya, taşma üçüncü yuvaya.
- **Kullanma:** Menu ve combo button yalnız tam sayfayı ya da büyük nesneyi (tuval, tablo)
  etkileyen eylemler için; karmaşık girdiler (onay/radyo grupları) için taşma menüsü değil tab tip
  popover.
- **Varyantlar:** Menu button (primary, tertiary ya da ghost; ikon hep caret) · combo button
  (yalnız primary) · overflow menu (ghost ikon düğme).
- **Ölçüler ve token'lar:** xs 24 · sm 32 · md 40 · lg 48; menü öğesi = tetik boyu. Genişlik menü
  kuralları (160–288, düğmeden dar değil, ghost asla akışkan değil). Metin `$body-compact-01` 14.
  Renk düğme spesifikasyonundan; taşma açıkken `$layer`.
- **Durumlar:** Düğme stiline göre.
- **Erişilebilirlik:** Menu button: `Space`/`Enter` açar, ilk öğe odakta, `Esc` kapatır ve odağı
  düğmeye döndürür. Combo: iki sekme durağı (önce birincil, sonra ikon düğme); `Esc` odağı ikon
  düğmeye döndürür. Hepsi `aria-haspopup="true"` + `aria-label`; öğeler `ul > li > button
  role="menuitem" tabindex="-1"`; combo `aria-controls` + `aria-expanded`. Combo ipucu "Additional
  actions" yalnız çeviri için değişir. 1.114.0: menu ve combo button dört satır geçti; overflow
  odak uygulanamaz.
- **İçerik:** Etiket eylemi ya da bir eylem listesinin geldiğini söyler.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `MenuButton` [paket varsayılan `size="lg"`, `menuAlignment="bottom"`], `ComboButton`,
  `OverflowMenu`, `OverflowMenuItem`; `unstable_OverflowMenuV2` / `preview_OverflowMenuV2` kararsız
  — kullanılmaz. Bayrak `enable-v12-overflowmenu`.
- **TEDY durumu:** **Uygun ama kullanılmıyor.** `OverflowMenuHorizontal` yalnız ikon olarak "Daha
  fazla" gezinmesinde kullanılıyor (`routes.ts`, `App.tsx`, `BottomNav.tsx`). Satırda üçten çok
  eylem birikirse Carbon taşma menüsü (ghost, ilk öğe odakta, `Esc` tetiğe döner). Talimatname §4.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/menu-buttons/guidelines/

<a id="modal"></a>

### 1.20 Modal (`modal`)

- **Ne için:** Diyalog: iş akışını tamamlamak için kritik bilgi ya da girdi; kısa, seyrek işler için
  akışı keser.
- **Kullan:** Kullanıcının başlattığı süreçte anında yanıt gerektiğinde; o anki işle ilgili acil
  bilgi; bir kararı onaylamak (başlık ve düğme eylemi söyler); yıkıcı/geri dönüşsüz eylem → danger
  modal.
- **Kullanma:** Sık yapılan iş (ana sayfada durur); kritik olmayan bilgi (→ inline notification);
  sayfa yerine; iç içe; dışarıdaki bilgiye bakmak gerekiyorsa. **Asla sistem tetiklemez.**
- **Varyantlar:** Passive (yalnız bilgi) · transactional (vazgeç + birincil) · danger · acknowledgment
  (tek düğme) · progress (çok adım). Boy xs, sm, md (varsayılan), lg; kısa metin xs/sm, karmaşık
  bileşen md/lg; lg yetmezse tam sayfa.
- **Ölçüler ve token'lar:** Genişlik tarayıcı yüzdesi (ör. 1584'te xs %24, sm %36, md %48, lg %72;
  320'de hepsi %100); azami yükseklik xs %48, sm %72, md %84, lg %96; mobilde tam ekran ya da içerik
  yüksekliği, alta yapışık. %36 ve üstü genişlikte gövde metni ve başlık için sağda %20 boşluk, daha
  darda 16 px; bileşenler tam genişlik. Kap `$layer` + 1 px `$border-subtle`; başlık etiketi
  `$label-01` `$text-secondary`; başlık `$heading-03` 20/400; içerik `$body-01` 14; kapat düğmesi
  48 × 48, ikon 16, hover `$layer-hover`; örtü `$overlay`. Başlık üst/sol 16, alt 16; içerik alt 48.
  Düğmeler: 1 → %50 sağa yaslı; 2 → %50'şer, kenardan kenara (ikincil solda, birincil sağda); 3 →
  %25'er.
- **Durumlar:** Açılınca odak: girdi varsa ilk girdi; onay → birincil; **yıkıcı → "Cancel"**; passive
  → kapat düğmesi; asla bağlantı. Odak içeride kilitli. Doğrulama kapanmadan önce; sunucu hatası
  inline notification. Uzun işte gövdede spinner + örtü, birincil devre dışı; kısa işte birincilde
  inline loading.
- **Erişilebilirlik:** `role="dialog"`, `aria-modal="true"`, başlıkla adlandırılır; `Esc` kapatır.
  [paket] `closeButtonLabel` varsayılanı İngilizce `"Close"`; `danger` iken ilk odak ikincil
  düğmeye düşer. 1.114.0: ilk çizim ve odak yönetimi geçti, ek durumlar ertelenmiş, elle test
  edildi. Bayrak `enable-focus-wrap-without-sentinels`.
- **İçerik:** Başlık kısa fiil öbeği; **bir düğmeden açıldıysa başlık o düğmenin etiketidir.**
  Açıklama yalnız amaç belli değilse. Gövde metni modal genişliğinin %80'i. Düğmeler etken fiil
  (Add, Delete, Save); "Done"/"OK" değil. Gövde dikey kayar, başlık ve alt bilgi sabit; yatay asla.
- **AI varyantı:** Broad (bütün modal) ya da focused (yalnız AI parçaları). `$layer`,
  `$ai-drop-shadow`, `$ai-inner-shadow`, örtü `$ai-overlay`, aura `$ai-aura-start-sm` →
  `$ai-aura-stop`, kenar `$ai-border-start` → `$ai-border-end`, etiket **large**.
- **React:** `Modal` (`size`, `danger`, `passiveModal`, `closeButtonLabel`, `loadingStatus`,
  `decorator`), `ComposedModal`, `ModalHeader`, `ModalBody`, `ModalFooter`, `ModalPresence`,
  `ComposedModalPresence`, `ModalWrapper`; `preview__Dialog` (`Dialog`, `DialogHeader`, …) kararsız —
  kullanılmaz.
- **TEDY durumu:** **Kullanılıyor** — `HomeworkTracker.tsx` ödev ayrıntısı passive `ComposedModal
  size="md"`, yalnız açıkken bağlanır, `ModalHeader iconDescription="Kapat"` (e2e sabitler); ilk odak
  kapat düğmesi (Carbon'un passive kuralı). `asistan/SesOnayi.tsx` mikrofon onayı `Modal`:
  `primaryButtonText="Onayla" secondaryButtonText="Vazgeç"` ✓; ama başlık "Mikrofon", tetik "Sesle
  sor" (başlık = düğme etiketi kuralı, İ9; B41); tek cümle için `size` yok (md); `closeButtonLabel`
  yok → "Close" (B44). Asistan paneli açık ödev modalının üstüne çıkıyor (iki diyalog; B61). Danger
  modal yok; silme kararı 1.4'te. Modül şablonunda modal yok. Talimatname §5 "diyalog".
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/modal/guidelines/

<a id="notification"></a>

### 1.21 Bildirim (`notification`)

- **Ne için:** Sistem durumu ve geri bildirim; dört durum × varyant ile ne kadar böleceği ayarlanır.
  Böler; seyrek kullanılır.
- **Kullan:** Inline: görev akışında eylemin durumu, birincil içerik alanının üstünde ya da ilgili
  öğenin yanında. Toast: zamana bağlı kısa mesaj. Actionable: tek eylemli. Callout: sayfayla
  yüklenen, görevden **önce** rehberlik; kapatılamaz.
- **Kullanma:** Kritik ve görevle ilgili bilgi değilse modal değil; callout geri bildirim değildir.
  Başarı bildirimi bir eylemin ardından gelir; kalıcı durum bandı olmaz.
- **Varyantlar:** Inline · toast · actionable (inline ya da toast stilinde) · callout. Durumlar:
  info (mavi, `information filled`), success (yeşil, `checkmark filled`), warning (sarı, `warning
  filled`), error (kırmızı, `error filled`); callout yalnız info ve warning. Yüksek kontrast (kritik)
  · düşük kontrast ("şüphedeysen düşük"); aynı varyantta karıştırılmaz.
- **Ölçüler ve token'lar:** Inline ve callout: asgari yükseklik 48 (`$spacing-09`), sol kenar 3 px,
  metin üst/alt 12 (`$spacing-04`), yan 16; en çok iki satır; kabı doldurabilir. Toast: genişlik 288,
  sağ üstten kayar, `$spacing-03` aralıkla yığılır, en yeni üstte; varsayılan kalıcı, 5 sn'de
  kapanacak kodlanabilir. Kapat düğmesi 48 × 48, ikon 16. Başlık `$heading-compact-01` 14/600, alt
  başlık `$body-compact-01` 14. Düşük kontrast: `$notification-<durum>-background-color`, kenar ve
  ikon `$support-<durum>`, metin `$text-primary`. Yüksek kontrast: `$background-inverse`,
  `$text-inverse`, `$support-<durum>-inverse`.
- **Durumlar:** Inline kendiliğinden kapanmaz; kapat düğmesi isteğe bağlı, okumak kritikse yok.
  Actionable odak alır ve kilitler; kullanıcı kapatana dek kalır. Callout kapatılamaz.
- **Erişilebilirlik:** Inline ve toast odak almaz; eylemsiz bildirim `alert`, `log` ya da `status`;
  eylemli `alertdialog`. Callout `aria-live` taşımaz, duyurulmaz. Ekran okuyucu mesajı tek cümle
  okur — metin stiline anlam yüklenmez. Kullanıcının zaman aşımı tercihine uyulur. [paket]
  `InlineNotification` `role="status"`; ikon adı `statusIconDescription` yoksa İngilizce
  `"<kind> icon"`; `ToastNotification` `timeout=0`. 1.114.0: ilk çizim uygulanamaz, ek durumlar
  ertelenmiş, elle test edildi.
- **İçerik:** Başlık kısa, en önemli olgu; hatada ne durdu; **başlık sonunda nokta yok**. Gövde bir-iki
  kısa cümle, başlığı tekrarlamaz; hatada **ne yapılacağı zorunlu**. Eylem düğmesi 1–2 kelime. İki
  satırı aşarsa actionable + "View more". Form hatası formun altında, gönder/vazgeç düğmelerinin
  üstünde. Cümle düzeni.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `InlineNotification` (`kind`: `error` | `info` | `info-square` | `success` | `warning` |
  `warning-alt`; `lowContrast`, `hideCloseButton`, `statusIconDescription`), `ToastNotification`
  (`timeout`), `ActionableNotification`, `Callout`, `StaticNotification`, `NotificationActionButton`,
  `NotificationButton`.
- **TEDY durumu:** **Kullanılıyor** — `InlineNotification`, hepsi `lowContrast`:
  `PortalStatusBanner.tsx` (info, gün içinde kapatılabilir; warning, kendiliğinden çözülür,
  kapatılamaz; sütun genişliğine yayılır, Carbon'un 46 rem sınırı kaldırılmış — tek sütun kuralı),
  `LoginPage.tsx`, `asistan/GirisUyarisi.tsx`, `ModuleViewer.tsx`, `Modules.tsx`,
  `PlatformProgress.tsx`. **Toast ve actionable: Kullanılmaz** (S27) — toast kayan hareket ve 5 sn kayboluş
  (İ6, "bildirim yağmuru" anti-kalıbı), actionable odağı kapar (İ1); eylem sayfada durur, bildirim
  yalnız söyler. Callout bileşeni yok; aynı token'larla elle yazılmış kutular var
  (`.homework-modal__enrichment`, `.route-boundary`, asistan `:::sonuc`/`:::hata`). Sapmalar:
  `PlatformProgress.tsx` sayfayla yüklenen kalıcı yeşil `kind="success"` "Tüm platformlar
  tamamlandı!" — Carbon'un başarı modeline ve İ7 "kutlama yok"a aykırı (B51); `statusIconDescription`
  sekiz kullanımın birinde var (B44); giriş hatası `role="status"` (durdurucu hata `alert`) ve
  düğmenin altında (CLS gerekçesiyle bilinçli). Asistanın hata kartı kırmızı `Tag` içinde cümle
  (`asistan/OzelYanitlar.tsx`) — hata bir bildirimdir (1.33; B45). Modül `.feedback` (3 px) ve `.callout`
  (4 px; Carbon 3 px) eşlemeleri (§9). Talimatname §5 "bildirim ve hata".
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/notification/guidelines/

<a id="number-input"></a>

### 1.22 Sayı girişi (`number-input`)

- **Ne için:** Yalnız sayı alan metin girişi; iki parçalı denetim küçük artırma/azaltma yapar.
- **Kullan:** Sayısal değer; birkaç tıkla küçük ayar; okur kesin değeri bilmeyip mevcut değere göre
  değiştiriyorsa.
- **Kullanma:** Büyük değişim (1'den 30'a; → slider); fiyat, uzunluk, boy gibi sürekli değişkenler
  (geniş aralıkta kesin değer → text input).
- **Varyantlar:** Default · fluid.
- **Ölçüler ve token'lar:** sm 32 · md 40 (varsayılan) · lg 48; fluid 64. Artı/eksi ikonları 16,
  yan dolgu 16; odak ve hata kenarı 2 px. Denetim hover `field-hover`. Gerisi ortak alan anatomisi.
- **Durumlar:** Etkin (**varsayılan değer içermeli**, genellikle 1, bazen 0; asla boş), hover, odak,
  hata (kırmızı kenar + ikon + mesaj), uyarı, devre dışı, iskelet, salt okunur.
- **Erişilebilirlik:** Tek sekme durağı; `Up`/`Down` adım; artı/eksi sekme sırasında değil; yalnız
  rakam. Yardım ve hata `aria-describedby`; hata ikonu `aria-hidden`. En küçük/en büyük ve
  varsayılan dışı adım yardım metninde önceden söylenir. 1.114.0: dört satır geçti.
- **İçerik:** Etiket zorunlu (onaylı erişilebilirlik istisnası hariç) ve görünür; cümle düzeni;
  etiket, değer ve yardım metni iki satırı geçmez.
- **AI varyantı:** Aura `$ai-aura-start-sm` → `$ai-aura-stop`, alt çizgi `$ai-border-strong`, etiket
  **mini**, "revert to AI".
- **React:** `NumberInput` (`step`, `allowEmpty`, `hideSteppers`, `decorator`), `NumberInputSkeleton`,
  `validateNumberSeparators`; `FluidNumberInput` (+ kararsız takma adlar).
- **TEDY durumu:** **Uygun ama kullanılmıyor.** Kesin sayısal cevap `TextInput` ile
  (`AlistirmaKarti.tsx`; sunucuda 0,01 mutlak tolerans) — Carbon'un "geniş aralıkta kesin değer"
  kuralı. Zaman kutusu sabit 10 dakikalık adım ("10 dakika daha"); süre girdirilmez, çünkü süre
  tahmini uydurma olur (İ3, D4). Modül şablonunda yok.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/number-input/guidelines/

<a id="pagination"></a>

### 1.23 Sayfalama (`pagination`)

- **Ne için:** Büyük içeriği sayfalara bölmek; sayfa başına kaç öğe gösterileceğini seçtirmek.
- **Kullan:** Hepsini birden yüklemek uzun sürüyorsa; tek görünüme sığmayacak kadar veri; alanı
  verimli kullanmak.
- **Kullanma:** Doğrusal yolculuk (form ilerlemesi); gereksiz yere.
- **Varyantlar:** Pagination (data table'ın altına bağlı çubuk: sayfa başına öğe, aralık, geçerli
  sayfa, önceki/sonraki) · pagination nav (sayfa içi; sayfa düğmeleri, üç nokta taşma).
- **Ölçüler ve token'lar:** Pagination xs 24 · sm 32 · md 40 (varsayılan) · lg 48; nav sm/md/lg.
  Tablonun altına boşluksuz, satır yüksekliğinde (xl satır → lg, xs satır → sm; sayfa xs'i hem
  listeler hem "sunulmaz" der — sayfa tutarsız). Nav içeriğin altında, sola ya da sağa (şüphedeysen
  sağ). Kap `$layer` + üst `$border-subtle`; aralık metni `$text-secondary`; nav seçili sayfa 4 px
  `$border-interactive` + `$heading-compact-01` 14/600; metin `$body-compact-01`.
- **Durumlar:** İç içe select ve ghost ikon düğme durumları; aralığın ucunda düğme devre dışı (ya da
  nav'da döngü). Küçük kırılımda select'ler kalkar.
- **Erişilebilirlik:** Yerel `<select>`; adlar "Page", "Previous", "Next"; sekme sırası soldan sağa.
  1.114.0: dört satır geçti (Pagination Nav ek durumlar ertelenmiş).
- **İçerik:** Etiketler kısa ve yol gösterici; gerekmedikçe değiştirilmez; üç nokta asla serinin
  başında ya da sonunda.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `Pagination`, `PaginationNav`, `PaginationSkeleton`; `unstable_Pagination` /
  `preview_Pagination` / `…PageSelector` kararsız — kullanılmaz.
- **TEDY durumu:** **Kullanılmaz (İ5, İ7).** Büyüyebilen listeler (İşler, Duyurular, Notlar)
  hepsini gösterir, bitmiş grupları katlar; sayfa bölmek okurun dönüşte yerini kaybettirir.
  Carbon'un "gereksiz yere kullanma"sı bu seçimi kapsar. Asistan tablolarında da yok.
  Talimatname §5 "katlama/açılma".
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/pagination/guidelines/

<a id="popover"></a>

### 1.24 Popover (`popover`)

- **Ne için:** Diğer içeriğin üstünde bir katman; metin ve etkileşimli öğe taşıyabilir; tooltip,
  taşma menüsü, dropdown menüsünün temeli. **Aynı anda tek popover.**
- **Kullan:** Etkileşimli öğeleri erişilebilir biçimde yerleştirmek (açılırların temeli); bir öğenin
  ek ayrıntısı.
- **Kullanma:** İç içe; dört sütunu aşıyorsa (→ modal).
- **Varyantlar:** No tip (tetiğin görünür basılı durumu varsa) · caret tip (basılı durumu yoksa, ikon
  düğmelerde) · tab tip (araç çubuğuna ya da başlığa bağlıysa).
- **Ölçüler ve token'lar:** Genişlik 1–4 sütun, en çok 352 / 22 rem; dolgu 16 (`$spacing-05`);
  caret 8 × 8, tetikle 4 px aralık (no tip ve caret), tab tip 0. Köşe **2 px**; tab tipte düz. Zemin
  `$layer` ya da `$background-inverse`. Gölge, z-index ve hareket sayfada belirtilmemiş.
- **Durumlar:** Açık/kapalı; tıkla ya da hover ile açılır; dışarı tıklamak kapatır. Yön varsayılan
  otomatik (kenar algılama).
- **Erişilebilirlik:** Tetik sekme sırasında; `Enter`/`Space` açar-kapar, odak tetikte kalır;
  etkileşimli içerikte `Tab` içeri girer; yalnız metinse ya da son öğeden `Tab` kapatıp sonraki
  durağa geçer; `Esc` kapatır. Tetik `aria-label` (ikon düğme), `aria-expanded`, `aria-controls`.
  1.114.0: ilk çizim testi ertelenmiş; diğerleri geçti.
- **İçerik:** Kaydırma gerekirse gövde dikey kayar, başlık ve alt bilgi sabit; yatay asla; sayfadan
  taşmaz.
- **AI varyantı:** Sayfada belirtilmemiş (AI etiketi açıklama popover'ı için 1.2).
- **React:** `Popover` (`caret`, `align`, `autoAlign`, `dropShadow`, `highContrast`, `open`),
  `PopoverContent`.
- **TEDY durumu:** **Kullanılıyor** — `CitationChip.tsx` (eski sohbet; Görev 21'de silinecek): hover/
  odakla açılan, metin içerikli — aslında tooltip ilişkisi; `Esc` yok. Elle yazılmış iki "popover"
  (B49; kart yüzeyi S30): başlıktaki senkron sağlık kutusu (`DashboardHeader.tsx`; `aria-expanded`,
  `aria-haspopup="dialog"`, `Esc` ✓; `aria-controls` yok; `Tab` ile çıkınca kapanmıyor; 380 px > 352;
  köşe 8 px) ve takvim olay kutusu (`CalendarEvents.tsx`; kartın ortasında, tetiğe bağlı değil;
  `role`, `Esc` ve odak taşıma yok — D2). TEDY kuralı: tıklamayla açılan bilgi kutusu Carbon
  `Toggletip`/`Popover` ile yazılır, `Esc` kapatır, odak tetiğe döner; gölge `--ted-shadow-popover`
  (S11). Kayan katman köşesi (2 px Carbon, 8 px TEDY kartı) talimatnamede tek değere bağlanır (S10, İ9).
  Modül `.def-pop` tanım ipucu eşlemesi (1.38). Talimatname §5 "katlama/açılma", §3.5.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/popover/guidelines/

<a id="progress-bar"></a>

### 1.25 İlerleme çubuğu (`progress-bar`)

- **Ne için:** İsteğin alındığını ve sistemin ilerlediğini göstermek: durum, tahmini süre, sürüyor
  bilgisi.
- **Kullan:** Uzun ya da süresi bilinmeyen, yüzdeyle anlatılabilen **sistem** işlemi: indirme,
  yükleme, veri yükleme, form gönderme, kaydetme.
- **Kullanma:** Açılınca genişleyen içerik (→ iskelet); ilerleme için elle adım gerekiyorsa (→
  progress indicator); **ilerleme kullanıcının eylemleriyle belirleniyorsa** (tamamlanan dersler,
  depolama); 5 saniyeden kısa süreç (→ loading).
- **Varyantlar:** Determinate (0 → %100, asla azalmaz ya da sıfırlanmaz) · indeterminate (yüzde yok;
  soldan sağa sabit hızla; ileri-geri hareket iskelete ayrılmış). Hizalama: default, inline (tablo),
  indent (kap içinde, kenara uzanan).
- **Ölçüler ve token'lar:** Yükseklik big 8 / small 4 px; genişlik en az 48 px, mümkünse en çok altı
  sütun, asla pencere genişliği. Etiket her zaman üstte (`$body-compact-01` 14, `$text-primary`), 8
  px (`$spacing-03`); yardım metni altta ya da yanda (`$helper-text-01` 12, `$text-helper`); çubuğun
  içinde metin yok. İz `$border-subtle`; etkin `$border-interactive`; başarı `$support-success` +
  tik; hata `$support-error` + ikon (tam genişlik, kalıcı).
- **Durumlar:** Active, success, error; bitince kalıcı ya da kendiliğinden kapanır. Kap içinde
  çalışırken bağlı denetimler devre dışı.
- **Erişilebilirlik:** `role="progressbar"` + `aria-valuemin/max/now`; yüklenen bölgeye
  `aria-busy="true"` + `aria-describedby`; yardım metni kabına `aria-live="polite"`; durum ikonları
  `aria-hidden`. Etiket yalnız süreç çok açıksa görsel olarak gizlenir, yine de verilir.
  Indeterminate ve hata durumunda yardım metni zorunlu. 1.114.0: ilk çizim ve durumlar geçti, klavye
  uygulanamaz, elle test edildi.
- **İçerik:** Etiket kısa, yükleme boyunca değişmez; yardım metni genel ("Fetching assets…") ya da
  kesin ("42/256 items"); yüzde ilerledikçe sayar.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `ProgressBar` (`value`, `max`, `status`, `size`: `small` | `big`, `helperText`,
  `hideLabel`, `type`).
- **TEDY durumu:** **Kullanılıyor — kuralla çatışarak.** `PlatformProgress.tsx`'te üç `ProgressBar`
  (EnglishCentral, Achieve3000, SEBİT) okurun tamamladığı etkinlik oranını çiziyor: Carbon'un açıkça
  dışladığı "kullanıcı eylemiyle belirlenen ilerleme"; çubuk 60 rem sütunu boydan boya kaplıyor
  (altı sütun tavanı aşılıyor); `helperText` yok, sayı akordeon başlığında. Yüzey §4.7 "platform ·
  ilerleme · son etkinlik" satırı ister; karar: düz metin ("12/40 video · son etkinlik …") ya da
  çubuğun neden kaldığı Yüzey'e yazılır (B51). Kitap okuyucudaki 2 px bölüm çizgisi
  (`BookReader.tsx`, Books dünyası) Carbon'un ARIA şeklini izliyor. Gün Şeridi bilerek ilerleme
  çubuğu değildir: zaman bir yerdir, yüzde değil (İ2; talimatname §8). Talimatname §4, §8.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/progress-bar/guidelines/

<a id="progress-indicator"></a>

### 1.26 İlerleme göstergesi (`progress-indicator`)

- **Ne için:** Çok adımlı süreçte hangi adımda olunduğunu, adım sayısını ve genel ilerlemeyi
  göstermek.
- **Kullan:** Üç ya da daha çok adımlı doğrusal süreç (uzun formlar); ilerlemeden önce doğrulama;
  geri/ileri gezinmeyi tamamlamak.
- **Kullanma:** Üçten az adım; herhangi sırayla tamamlanabilen süreç; adım sayısı koşula göre
  değişiyorsa.
- **Varyantlar:** Yatay · dikey ("mümkünse dikey"); etkileşimsiz (varsayılan) · etkileşimli (adıma
  gidilir).
- **Ölçüler ve token'lar:** Adım asgari genişliği 128 / 8 rem; ikon 16, ikon ve etiket boşluğu 16
  (`$spacing-05`). Etiket `$body-compact-01` 14 `$text-primary`; yardım `$label-01` 12
  `$text-secondary`. Tamamlanan ve geçerli ikon `$interactive`; başlanmamış `$icon-primary`; etkin
  çizgi `$border-interactive`, etkin olmayan `$border-subtle`; hata `$support-error`; etiket hover
  `$link-primary-hover`.
- **Durumlar:** Tamamlandı (dış çizgili daire + tik), geçerli (yarı dolu daire), başlanmadı (dış
  çizgili), hata, devre dışı (odak almaz, okunmaz), hover, odak.
- **Erişilebilirlik:** Etkileşimlide ilk adım varsayılan seçili, `Right`/`Left` adımlar arasında;
  etiket alanının her yeri tıklanır. Etiketler her adımın durumunu içerir. Doğrulama odak çıkınca;
  geçersiz girdi hem adımı hem alanı hataya çevirir. 1.114.0: dört satır geçti.
- **İçerik:** Etiket 1–2 kelime, fiil + isim ("Configure IdP"), ≤ 16 karakter, cümle düzeni; adım
  numarası ilerlemeyi açık eder. Taşma: yeniden yaz ya da üç nokta + ipucu; yardım metni ikinci satıra
  kayar.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `ProgressIndicator` (`vertical`, `spaceEqually`), `ProgressStep`,
  `ProgressIndicatorSkeleton`.
- **TEDY durumu:** **Panoda uygun ama kullanılmıyor; modülde eşlemeyle kullanılıyor.** Alıştırma
  kartı "Soru 2/5" metni (`AlistirmaKarti.tsx`). Modül bandındaki `.stepper` Carbon ProgressIndicator
  eşlemesidir (`carbon-child-system.md`): yatay, numaralı, görünür etiketsiz (`title` + `aria-label`),
  tamamlanan dolu daire, geçerli halka, gelecek adımlar `disabled` (Carbon'a göre ekran okuyucudan
  düşer), ok tuşu gezinmesi yok; "Son N durak" yalnız 1–2 durak kalınca. Toplamı baştan göstermek
  İ3 ile gerilim yaratır; istisna modül pedagojisi kurallarında yazılır (§9). 2026-10-10'dan beri (S43) modül
  ilerlemesi yalnız bu sessiz, etiketli göstergedir — seri çipi, rozet ve ödül animasyonu yoktur, XP ekranda gösterilmez (2026-10-11, B73 kapandı);
  ProgressBar kullanıcı eylemiyle belirlenen ilerleme için kullanılmaz.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/progress-indicator/guidelines/

<a id="radio-button"></a>

### 1.27 Radyo düğmesi (`radio-button`)

- **Ne için:** Karşılıklı dışlayan seçenekler; aynı anda bir seçili.
- **Kullan:** Formlar (karo, tablo, modal, yan panel, tam sayfa); ayarlar ve süzgeçler.
- **Kullanma:** Çoklu seçim (→ checkbox). Seçim için daha çok bilgi gerekiyorsa selectable tile;
  tam iki durum açık/kapalı → toggle; basit çok sütunlu veriden tek öğe → structured list.
- **Varyantlar:** Dikey ya da yatay grup ("mümkünse dikey").
- **Ölçüler ve token'lar:** Daire 20 × 20, nokta 8 × 8, etikete 8 (`$spacing-03`). Grup etiketi
  `$label-01` 12 `$text-secondary`, 8 px altında; etiket `$body-compact-01` 14 `$text-primary`; öğe
  aralığı 8. Kenar ve nokta `$icon-primary`; odak `$focus`; hata `$support-error`. Formda sonraki
  bileşene ≥ 32 (`layout-03`), sıkışıkta 24/16 (v10 adları). Asgari hedef sayfada belirtilmemiş.
- **Durumlar:** Seçilmemiş, seçili; varsayılan olarak **hiçbiri seçili değil**; seçimi kaldırmak
  gerekebiliyorsa "diğer"/"hiçbiri" seçeneği. Odak, devre dışı, salt okunur, hata, uyarı.
- **Erişilebilirlik:** Grup tek sekme durağı; seçim yoksa ilk öğe odak alır; ok tuşları seçimi
  değiştirir; `Tab` gruptan çıkar. `fieldset` + `legend`, `label for`; zorunlu grup programatik
  (`aria-required` ya da etiket). Etiket de tıklanır. 1.114.0: dört satır geçti.
- **İçerik:** Etiket üç kelimeden az, kırpılmaz; uzunsa alta kayar, daire ve etiket üstten hizalı.
  Grup etiketi kategori ya da kısa talimat.
- **AI varyantı:** Grup ya da tek etikete AI etiketi, **mini**; başka değişiklik yok.
- **React:** `RadioButton`, `RadioButtonGroup` (`orientation`, `readOnly`, `invalid`, `decorator`),
  `RadioTile` (1.35).
- **TEDY durumu:** **Kullanılıyor** — `AlistirmaKarti.tsx` `RadioButtonGroup legendText="Cevabın"`;
  cümle uzunluğunda dört seçenek, `orientation` verilmemiş; cevaplanınca ve salt okunur sohbette
  `disabled` (Carbon'a göre seçilen cevap ekran okuyucudan düşer → `readOnly` olmalı; B42; e2e
  `toBeDisabled()` sabitliyor); 48 px etiket yüksekliği (S18). `OgretmenSecici.tsx` yerel radyo grubu
  çip görünümünde: tek durak, ok tuşu seçer, tik ile "seçili" yalnız renk değil (İ8); "Genel" önceden
  seçili (İ1; Carbon'un kaynak gösterdiği NN/g 2014 makul varsayılana izin verir); yatay sarma
  ölçülmüş karar. Modül öz değerlendirme radyosu `fieldset`/`legend`'sız, 22 px, ders vurgulu (§9).
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/radio-button/guidelines/

<a id="search"></a>

### 1.28 Arama (`search`)

- **Ne için:** Anahtar sözcükle keşif; birincil keşif aracı ya da süzgeç.
- **Kullan:** Karmaşık ya da büyük veri; küresel (site), sayfa ya da bileşen (tablo) düzeyi.
- **Kullanma:** Az veri; tek görünümde bulunabilen basit bilgi.
- **Varyantlar:** Default (etiketsiz) · fluid (etiket içeride); açılabilir (expandable) arama.
- **Ölçüler ve token'lar:** xs 24 · sm 32 · md 40 (varsayılan) · lg 48 (çoğunlukla küresel); fluid
  64. Yan dolgu yüksekliğe eşit (`$spacing-06…09`); arama ve temizle ikonu 16. Genişlik sınırı yok.
  Alan `$field` + `$border-strong`; placeholder `$text-placeholder`; arama ikonu `$icon-secondary`;
  metin `$body-compact-01` 14.
- **Durumlar:** Etkin, odak, dolu, devre dışı. Yazınca "x" çıkar.
- **Erişilebilirlik:** `Enter` gönderir, `Esc` temizler; "x" sonraki sekme durağı (`Space`/`Enter`).
  Bütünü `role="search"`; girdi `role="searchbox"` (ya da `type="search"`); gizli adlar "search",
  "clear search input". Öneriler, sonuç durumu ("25 results found" / "no results found") ve sonuç
  gezinmesi ayrı tasarım notu ister. 1.114.0: dört satır geçti.
- **İçerik:** Placeholder kısa, yararlı ipucu; cümle düzeni.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `Search` (`size`, `closeButtonLabelText`), `SearchSkeleton`, `ExpandableSearch`,
  `FluidSearch` (+ kararsız takma adlar), `TableToolbarSearch`.
- **TEDY durumu:** **Kullanılmaz (az veri; İ1/İ6).** On iki sayfa, birkaç kitaplık raf, boş başlayan
  sohbet listesi: Carbon'un "az veride kullanma"sı. Başlıkta küresel arama her ekranda yarışan bir
  olanak olurdu. Bir yüzey ölçülerek arama gerektirirse önce "0 sonuç" cümlesi tasarlanır (D3).
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/search/guidelines/

<a id="select"></a>

### 1.29 Select (`select`)

- **Ne için:** Listeden tek seçim; genellikle veri gönderilen formlarda. Liste tarayıcı tarafından
  çizilir.
- **Kullan:** Form içinde tek seçim ve gönderme; ağırlıkla form tabanlı, mobil yoğun deneyim.
- **Kullanma:** Üçten az seçenek (→ radio); çoklu seçim, süzme, sıralama (→ dropdown).
- **Varyantlar:** Default · inline (kenarlıksız, hafif); stil default · fluid.
- **Ölçüler ve token'lar:** xs 24 · sm 32 · md 40 (varsayılan) · lg 48; fluid 64; liste yüksekliği
  tarayıcınınki. Alan sağ dolgu 48 (`$spacing-09`). Gerisi ortak alan anatomisi; hover `$field-hover`.
- **Durumlar:** Etkin (**varsayılan değer içermeli**), hover, seçili, odak, açık, hata, uyarı, devre
  dışı, iskelet, salt okunur.
- **Erişilebilirlik:** `Space`/`Enter`/`Up`/`Down` açar; harf tuşu o harfle başlayan ilk seçeneğe
  atlar; `Esc` değiştirmeden kapatır. "Choose an option" gibi istem `disabled hidden selected`
  verilir, açık listede görünmez. HTML `select` üzerine kurulu.
- **İçerik:** Etiket 1–3 kelime; yardım metni seçmeye yardım eder; sıra alfabetik ya da artan,
  değilse kullanım sıklığı; seçenek ≤ 3 kelime, cümle düzeni. Varsayılan seçenek boş ya da ilk/en sık.
- **AI varyantı:** Kararlı; text input ile aynı (aura, `$ai-border-strong`, **mini**, revert).
- **React:** `Select` (`inline`, `readOnly`, `decorator`), `SelectItem`, `SelectItemGroup`,
  `SelectSkeleton`; `FluidSelect` (+ kararsız takma adlar).
- **TEDY durumu:** **Kullanılıyor** — `asistan/GirisEkleri.tsx` "Ödev" (ilk öğe gerçek bir seçenek
  "Seçilmedi — genel soru"; sıra teslim listesinin sırası; metin 80 karakterde ipucusuz kesiliyor —
  B35), `YuklenenEk.tsx` "Belgenin ödevi" (istem "Ödev seç" seçilebilir bir öğe olarak duruyor —
  Carbon'a göre `disabled hidden`; B60), eski `AssistantChat.tsx`. Mobil yoğun form bağlamında yerel
  select Carbon'un tercihine uygun. `StudentProfile.tsx`'teki iki yerel `<select>` elle stillenmiş;
  Carbon `Select` aynı yerel denetimi etiket/yardım/hata anatomisiyle verir. Sıra: TEDY'de teslim
  sırası (İ2/İ7) alfabetiğe üstün.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/select/guidelines/

<a id="slider"></a>

### 1.30 Kaydırıcı (`slider`)

- **Ne için:** Bir izde tek değer ya da aralık seçmek; değeri gösteren bir sayı girişiyle.
- **Kullan:** Tek sayı ya da sayı aralığı; seçenekleri hızla sınırlamak.
- **Kullanma:** Çok büyük aralık (1–1000), çok küçük aralık (1–3), sayısal olmayan değer, tarih
  (→ date picker).
- **Varyantlar:** Default (etiket + sayı girişi) · range (iki tutamak, iki sayı girişi).
- **Ölçüler ve token'lar:** Tutamak 14 (aktif 20); iz 4, yan boşluk 8; range tutamak 16. Etiket
  `$label-01` 12 `$text-secondary`; aralık etiketi `$body-compact-01` 14. Tutamak `$icon-primary`; iz
  `$border-subtle`; dolu iz `$border-inverse`; odak/aktif `$interactive`. Genişlik önerisi en az 200,
  en çok 640 (bileşende yok).
- **Durumlar:** Etkin, hover, odak, aktif, hata, uyarı, devre dışı, salt okunur, iskelet. Sayı
  girişi yoksa değer hover/odak/aktifte ipucunda.
- **Erişilebilirlik:** Ok tuşları bir adım; `Shift` + ok `stepMultiplier` kadar (önerilen aralığın
  onda biri); `Home`/`End` uçlar. Sıra: kaydırıcı, sonra sayı girişi. Aralık dışı değer en yakın
  geçerli değere düzeltilir ve hata gösterilir. `step` için "1" önerilir. 1.114.0: odak testi
  uygulanamaz.
- **İçerik:** Etiket tek satır, kaydırıcının üstünde, ≤ 3 kelime, cümle düzeni.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `Slider` (`step`, `stepMultiplier`, `hideTextInput`), `SliderSkeleton`.
- **TEDY durumu:** **Panoda uygun ama kullanılmıyor; modülde yerel karşılıkla kullanılıyor.** Modül
  simülasyon parametreleri yerel `<input type="range" aria-label>` + kalıcı `<output>` okuması;
  etkileşimli sayı doğrusu SVG `role="slider"` + `aria-valuemin/max/now`, ok ve `Home`/`End`
  (`Shift` çarpanı yok). Kalıcı okuma Carbon'un "hover ipucunda değer"inden iyidir: hover'a gizli
  bilgi yok (İ6, D3) — bilinçli sapma (§9).
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/slider/guidelines/

<a id="structured-list"></a>

### 1.31 Yapılandırılmış liste (`structured-list`)

- **Ne için:** Satırlardaki çok öğeyi taranabilir düzende vermek; satırlar salt okunur ya da seçilebilir.
- **Kullan:** Bir grupta gezinmek ya da seçmek; açıklamalar, özellikler, plan karşılaştırma.
- **Kullanma:** İç içe öğe (→ data table); dar alan (→ contained list).
- **Varyantlar:** Default · selectable (tek satır; bayrakla radyo ikonları solda ve hep görünür).
  Hizalama hang ya da flush (flush seçilebilirde yok); zemin rengi yalnız hang ile.
- **Ölçüler ve token'lar:** Satır varsayılan 60, sıkışık 36. Kap asgari 500 (tasarım değeri; [paket]
  CSS zorlamıyor, hücre en çok 36 rem). Başlık dolgusu üst 16 / alt 8 / yan 16; satır üst 16 / alt
  24 (`$spacing-06`). Başlık `$heading-compact-01` 14/600 `$text-primary`; satır `$body-01` 14/400
  **`$text-secondary`**; ayırıcı `$border-subtle`. Seçili `$layer-selected`.
- **Durumlar:** Default: etkin, iskelet. Selectable: hover, odak, seçili, devre dışı.
- **Erişilebilirlik:** Seçilebilir: `Tab`, `Space` seçer, `Up`/`Down`. Başlıklar veriyi tanımlar;
  açıklama `aria-describedby`.
- **İçerik:** Satır en çok üç paragraf; sütun başlığı 1–2 kelime, cümle düzeni.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `StructuredListWrapper` (`isCondensed`, `isFlush`, `selection`), `StructuredListHead`,
  `StructuredListBody`, `StructuredListRow`, `StructuredListCell`, `StructuredListInput`,
  `StructuredListSkeleton`. Bayrak `enable-v12-structured-list-visible-icons`.
- **TEDY durumu:** **Kullanılıyor** — `TeamActivities.tsx` iki `StructuredListWrapper isCondensed`,
  3–4 tek kelimelik sütun başlığı (birden çok başlık → structured list: Carbon'un kuralı); "Konum"
  odak kipinde gizli. Sapma: ad hücresi 600 ağırlık (Carbon 400; başlıkla yarışır, İ6). Bulgu:
  "Yüz Yüze / Teams" etiketi `blue`/`teal` — ders renk aileleri (1.33).
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/structured-list/guidelines/

<a id="tabs"></a>

### 1.32 Sekmeler (`tabs`)

- **Ne için:** Farklı ama ilişkili içeriği gruplamak; sayfadan çıkmadan görünümler arası gezinme.
- **Kullan:** Tam sayfa, modal, kart, yan panel; formları, ayarları, panoları kategorilere ayırmak.
- **Kullanma:** Aynı içeriğin biçimini değiştirmek ya da süzmek (→ content switcher); adım adım süreç
  (→ progress indicator); grupları karşılaştırmak gerekiyorsa.
- **Varyantlar:** Line (bağımsız ya da bileşen içinde; her zaman otomatik genişlik) · contained
  (vurgulu; alt sayfa gibi alanlar; panelle aynı katman token'ı) · vertical (gezinmenin yerine asla).
  Otomatik genişlik ya da ızgaraya duyarlı (yalnız contained, ≤ 4 sekme). İkon her zaman etiketin
  sağında; yalnız ikon sekmede ipucu ve genişlik = yükseklik. Kapatılabilir sekmeler.
- **Ölçüler ve token'lar:** Line sm 32 / md 40 (lg yalnız ikonlu 48); contained sm 32 / md 40 / lg 48;
  vertical 32/40/48 ve varsayılan xl 64. Line alt çizgi 2 px; contained üst çizgi 2 px + sağ 1 px;
  vertical sol 3 px. Etiket dolgusu 16; seçilmemiş `$body-compact-01` 14/400 `$text-secondary`,
  seçili `$heading-compact-01` 14/600 `$text-primary`. Line seçili alt çizgi `$border-interactive`;
  contained seçilmemiş `$layer-accent`, seçili `$layer` + üst `$border-interactive`.
- **Durumlar:** Seçili, seçilmemiş, hover, odak, devre dışı; her zaman bir seçili; **kullanıcı
  değiştirene dek seçili kalır**. Sığmazsa yatay kayar, asla kaymaz-yığılmaz (vertical yığılır).
- **Erişilebilirlik:** En az iki sekme durağı (sekme listesi, sonra panelin ilk denetimi ya da
  panel). `Left`/`Right` sekmeler arasında, sarar; kaydırma okları odak sırasında değil. Otomatik
  (odak = seçim; panel hızlı yükleniyorsa) ya da elle (`Enter`/`Space`; yavaşsa) — işaretlenir.
  `tablist`, `<button role="tab">`, `aria-selected`, `tabindex`, `aria-controls`.
- **İçerik:** Etiket 1–2 kelime (spesifikasyon ≤ 3 diyor), görünümün içeriğini söyler, cümle düzeni;
  line/contained kırpılmaz (kayar).
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `Tabs` (`selectedIndex`, `defaultSelectedIndex`, `onChange`), `TabList` (`contained`,
  `activation`: `automatic` | `manual`), `Tab`, `IconTab`, `TabPanels`, `TabPanel`, `TabsVertical`,
  `TabListVertical`, `TabsSkeleton`.
- **TEDY durumu:** **Kullanılıyor** — `CourseContent.tsx` ders başına `Tab`, `TabList contained
  aria-label="Ders içerikleri"`, paneller akordeon; doğru bileşen (farklı dersler). Sapmalar (B47):
  `Tabs` denetimsiz, seçim yeniden yüklemede ilk derse dönüyor (Carbon "seçili kalır"; İ5'in dönüş
  testi); otomatik/elle seçimi işaretlenmemiş; sekmeye dokunan e2e yok. Kart içinde contained mı line
  mı kararı yazılmamış (kart sayfanın içerik alanı). Modülde sekme yok. Talimatname §4.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/tabs/guidelines/

<a id="tag"></a>

### 1.33 Etiket (`tag`)

- **Ne için:** Öğeleri etiketlemek, kategorilere ayırmak, süzmek, seçenek seçmek/bırakmak, taşan
  etiketleri açmak.
- **Kullan:** İçerik birden çok kategoriye giriyorsa; süzgeç; sohbet akışında karar; kullanıcının
  kaldırabileceği etiketler.
- **Kullanma:** Başka sayfaya ya da sekmeye bağlantı olarak; birden çok işlevle.
- **Varyantlar:** Read-only (etkileşimsiz) · dismissible (yalnız kapat ikonu etkileşimli; kalıcı
  olması gereken şey için değil) · selectable (seçili `$background-inverse`; grup en çok beş satıra
  sarar) · operational (daha çok etiket açar). Selectable ve operational kenarlıdır.
- **Ölçüler ve token'lar:** sm 18 · md 24 (varsayılan) · lg 32; köşe 16 px (hap); yan dolgu sm/md 8,
  lg 12; ikon 16. Grupta dört yönde 8 px. Metin `$label-01` 12/400. Renk: read-only, dismissible,
  operational bileşen token'ları (açık tema metin 70, kenar 40, zemin 20 adımı); selectable yalnız
  çekirdek token'lar. [paket] `.cds--tag` en çok 208 px, taşınca üç nokta; `size="sm"`'de `renderIcon`
  çizilmez; `title` yalnız kapat düğmesinin adıdır.
- **Durumlar:** Read-only: etkin, devre dışı, iskelet. Dismissible/operational: + hover, odak, tık.
  Selectable: + seçili.
- **Erişilebilirlik:** Read-only sekme sırasında değil. Dismissible: odak kapat alanında,
  `Enter`/`Space` kapatır; etikete `onClick` verilmez. Selectable: kap odak alır, `Enter`/`Space`
  değiştirir. Taşan başlık hover ve odakta ipucuyla. 1.114.0: geçti (Interactive Tag ilk çizim
  ertelenmiş).
- **İçerik:** Mümkünse 20 karakterin altında, birkaç kelime; çok satıra kaymaz; uzunsa üç nokta + ipucu.
  Dekoratif ikon başta, küçük boyda önerilmez. Carbon: farklı kategoriye farklı renk.
- **AI varyantı:** Yalnız read-only ve dismissible'da satır içi AI etiketi (small, sağ dolgu 4),
  rengi etiket metniyle aynı.
- **React:** `Tag` (`type`, `size`, `renderIcon`, `decorator`; `filter`/`onClose`/`title` kullanımdan
  kalkıyor), `DismissibleTag`, `SelectableTag`, `OperationalTag`, `TagSkeleton`.
- **TEDY durumu:** **Kullanılıyor** (16 dosya; çoğu `size="sm"`, `gray`/`cool-gray`/`warm-gray`/
  `green`/`red`); `asistan/BaglamCipi.tsx` `DismissibleTag` Carbon'a uygun. **Bilinçli sapma:** renk
  kategori değil; mavi/turkuaz/mor/macenta/camgöbeği ders kimliğidir, etiket yalnız durum ve üst veri
  taşır, tür ikonla gösterilir (İ6/İ8, `tests/test_pano_tasarim_sistemi.py`); durum etiketleri metinli
  kalır, yeni durum göstergeleri ikon + metin taşır (S4, B16). Bulgular: test regex'i ifadelerden
  kaçanları yakalamıyor (`TeamActivities.tsx` `'blue' : 'teal'`, `PlatformProgress.tsx` `'blue'`);
  etikette cümle (`Modules.tsx` 38 karakter, `asistan/OzelYanitlar.tsx` ve eski sohbette hata
  cümlesi, `MesajAltbilgisi.tsx` 26–30 karakter) — 208 px'te kırpılır, hata bir bildirimdir (1.21);
  `CalendarEvents.tsx` küçük etikette `renderIcon` sessizce düşüyor; `DashboardHeader.tsx`
  senkron zamanı `title`'da — çizilmiyor (D3). Başlık bandındaki çip Tedy katmanının "bant çipi"
  (§3.2). Grup aralığı bir yerde 4 px (`.today-tl__card-tags`). Talimatname §3.2, §5 "durum göstergesi".
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/tag/guidelines/

<a id="text-input"></a>

### 1.34 Metin girişi: text input, text area, password (`text-input`)

- **Ne için:** Serbest metin; beklenen uzunluğa göre tek satır (text input) ya da çok satır (text
  area); gizli karakterli parola.
- **Kullan:** Girdi bir ön ayardan tahmin edilemiyorsa ya da yazmak seçmekten hızlıysa.
- **Kullanma:** Yalnız listeden bir seçenek girilebiliyorsa (→ dropdown, select, radio).
- **Varyantlar:** Default · fluid (komşularla hep bitişik; yardım metni ipucunda). Text area yeniden
  boyutlandırma tutamağı ve karakter/kelime sayacı taşıyabilir. Password görünürlük düğmesi (sağda).
- **Ölçüler ve token'lar:** xs 24 · sm 32 · md 40 (varsayılan) · lg 48; fluid 64. Text area asgari
  40, azami yok; tutamak yalnız yüksekliği değiştirir. Alan kenarı 3:1 metin dışı kontrast. Genişlik
  sınırı yok; beklenen içerikle orantılı, ızgaraya hizalı. Text area dolgusu üst/alt 11. Gerisi ortak
  alan anatomisi.
- **Durumlar:** Etkin, aktif, odak, hata (üç işaret: kırmızı kenar, ikon, mesaj), uyarı, devre dışı,
  iskelet, salt okunur. Gerçek zamanlı ya da gönderimde doğrulama.
- **Erişilebilirlik:** `Tab` odaklar; etiket `for` ile, yardım `aria-describedby` ile; hata
  erişilebilir biçimde açılır. Text input'a odakta mevcut metin seçilir. Sayaç sınırda girdiyi durdurur
  ve söyler. Parola yardım metni biçim şartlarını listeler.
- **İçerik:** Etiket zorunlu, ≤ 3 kelime, cümle düzeni, iki nokta yok. Yardım metni tam cümle, kalıcı,
  biçimi söyler. Placeholder varsayılan yok, asla etiket ya da kritik bilgi yerine. Azınlık
  işaretlenir ("(isteğe bağlı)" / "(zorunlu)").
- **AI varyantı:** Aura `$ai-aura-start-sm` → `$ai-aura-stop`, alt çizgi `$ai-border-strong`, etiket
  **mini**; kullanıcı değiştirirse AI stili kalkar, "revert to AI" düğmesi geri getirir.
- **React:** `TextInput` (`readOnly`, `helperText`, `invalid`, `warn`, `decorator`),
  `TextInputSkeleton`, `TextArea`, `TextAreaSkeleton`, `PasswordInput`, `ControlledPasswordInput`;
  `FluidTextInput`, `FluidPasswordInput`, `FluidTextArea` (+ kararsız takma adlar).
- **TEDY durumu:** **Kullanılıyor** — `AlistirmaKarti.tsx` ("Cevabın", `aria-describedby` soruya ✓),
  `OdevOnayKarti.tsx` (Ders, Başlık, Teslim, `TextArea` Açıklama), `SohbetListesi.tsx` (yeniden
  adlandırma; `Enter` kaydeder, `Esc` vazgeçer), eski `AssistantChat.tsx`; hepsi md, sayfada tek boy
  ✓. Bulgular: `OdevOnayKarti` boş zorunlu alanda yalnız gönder düğmesini sessizce devre dışı
  bırakıyor (hata durumu ve mesaj yok, D3); zorunlu/isteğe bağlı işareti yok; fotoğraftan AI'ın
  doldurduğu alanlarda AI etiketi ve revert yok (§6); salt okunur aile görünümünde `disabled`
  (`readOnly` olmalı). `StudentProfile.tsx` yerel alanlar Carbon anatomisini kopyalıyor ama hata/
  uyarı/salt okunur durumu ve `aria-describedby` yok. Modül `.se-textarea`, `.worked-input` (48 px,
  `aria-label`; devre dışı opaklıkla) (§9). Talimatname §5 "form", "salt okunur/devre dışı".
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/text-input/guidelines/

<a id="tile"></a>

### 1.35 Karo (`tile`)

- **Ne için:** İçerik ve iç içe bileşen taşıyan, sayfa zemininden farklı renkte, ızgaraya duyarlı
  kap; hazır stili yok. Kartlar karonun üstüne kurulur; **Carbon'un kart kalıbı yok**.
- **Kullan:** İlişkili bilgi ve eylemleri gruplamak; eyleme ya da gezinmeye yönlendirmek; tekli/
  çoklu seçim; büyük içeriği gizleyip göstermek.
- **Kullanma:** İkincil bilgi, eylem ya da bildirim açmak için (→ modal, popover). **Karo sayfa
  zemini düzlemindedir, yükseltisi ve gölgesi yoktur.**
- **Varyantlar:** Base (içinde düğme/bağlantı olabilir; kendisi etkileşimsiz) · clickable (bütün karo
  hedef; **içinde ayrı eylem yok**; sağ altta ok) · selectable (tekli/çoklu) · expandable. Grupta
  varyant karıştırılmaz. Bayraklar: kenarlık, radyo/onay ikonları.
- **Ölçüler ve token'lar:** Asgari 64 yükseklik, 128 genişlik; asgari en-boy 2:1; dolgu dört yönde
  16 (`$spacing-05`). Clickable ikon 20 + 12 dolgu; selectable/expandable ikon 16 + 16. Başlık
  varsayılan `$body-compact-01` 14. Zemin `$layer`; kenar `$border-tile` (bayrak); hover
  `$layer-hover`; seçili kenar `$border-inverse`; clickable ikon `$icon-interactive`. Köşe sayfada
  belirtilmemiş; [paket] `hasRoundedCorners` "yalnız AILabel varken geçerli".
- **Durumlar:** Clickable: etkin, hover, odak, devre dışı. Selectable: + seçili, hover-seçili.
  Expandable: tıklama ya da sağ alttaki chevron.
- **Erişilebilirlik:** Base etkileşimsiz (içindekiler odak alır). Clickable `Tab` + `Enter`.
  Selectable tekli grup tek durak + ok tuşları; çoklu her karo bir durak, `Space`/`Enter`.
  **Doğrudan etkileşimli karonun üstüne etkileşimli öğe konmaz; karmaşıksa base karo.** Etkileşimli
  karonun erişilebilir adı olur.
- **İçerik:** Başlık, gövde, etiket ve etkileşimli öğeler; base'de bağlantılar sol altta, düğmeler
  altta tam genişlik.
- **AI varyantı:** `$layer`, `$ai-drop-shadow`, `$ai-inner-shadow`, aura `$ai-aura-start` →
  `$ai-aura-stop`, kenar `$ai-border-start` → `$ai-border-stop`, etiket **mini**.
- **React:** `Tile` (`hasRoundedCorners`, `decorator`), `ClickableTile`, `SelectableTile`,
  `ExpandableTile`, `TileAboveTheFoldContent`, `TileBelowTheFoldContent`, `RadioTile`, `TileGroup`;
  `preview__Card` kararsız — kullanılmaz.
- **TEDY durumu:** **Kullanılıyor (base)** — `HomeworkTracker.tsx` satırları, `ExamTimeline.tsx`,
  `SourcePanel.tsx`, eski sohbet paneli. **Bilinçli sapmalar:** `.cds--tile` köşesi 8 px
  (`--ted-radius-card`; Carbon'da yuvarlak karo AI demektir, TEDY'de kart demektir — AI aura ve
  AILabel ile ayrışır) (S10); yeni statik yüzey gölge almaz, `.dashboard-card` gölgesi borç (S11, B2).
  Bulgular: İşler satırı `onClick`'li base `Tile` — odaklanmayan `div`, klavyeyle açılmıyor, içinde
  "Yaptım" düğmesi var (Carbon'un yasakladığı üst üste eylem; D2); hover `$layer-hover` yerine
  `--ted-color-page-bg`. Kural: satır ya clickable karo (içinde eylem yok) ya base karo + adlı açma
  düğmesi. Modül `.opt` selectable tile eşlemesi; tekli seçim radyo anlamıyla, seçili durum renk +
  işaret + `aria-pressed`/`aria-checked` ile (§9). Talimatname §3.5.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/tile/guidelines/

<a id="toggle"></a>

### 1.36 Aç/kapa anahtarı (`toggle`)

- **Ne için:** İki durum arasında hızlı geçiş; yalnız "anahtar çevrilince" **hemen** etkili ikili
  eylemler.
- **Kullan:** Sistem ya da sayfa ayarını etkileyen tek seçenek; anında uygulanan tercihler; onaysız
  geri alınabilen eylemler.
- **Kullanma:** Onay gerektiren eylem (dosya silme); ikiden çok seçenek (→ dropdown, radio,
  checkbox); ikili olmayan ya da anında uygulanmayan ayar (→ checkbox + düğme).
- **Varyantlar:** Default (etiket ve durum metni zorunlu) · small (etiket ve durum metni isteğe bağlı;
  açıkta tik).
- **Ölçüler ve token'lar:** Default 48 × 24, tutamak 18 (sayfa rem'i "1.25" — sayfa tutarsız); small
  32 × 16, tutamak 10. Etiket boşluğu 16 (bayrakla 8); durum metni 8 solda. Etiket `$label-01` 12
  `$text-secondary`; durum metni `$body-compact-01` 14 `$text-primary`. Kapalı zemin `$toggle-off`,
  açık `$support-success`, tutamak `$icon-on-color`, tik `$support-success`; salt okunur saydam +
  `$border-subtle`.
- **Durumlar:** Açık, kapalı, odak, devre dışı, salt okunur, iskelet.
- **Erişilebilirlik:** `role="switch"` düğme, `aria-checked`; açık/kapalı metni `aria-hidden`; etiket
  `for` ile. `Tab`, `Enter`/`Space`. Durum renk + metin (small'da + tik). [paket] varsayılan
  `labelA="Off"`, `labelB="On"`; `hideLabel` iken yan etiketlerin yerine `labelText` geçer. 1.114.0:
  geçti.
- **İçerik:** Etiket ≤ 3 kelime, cümle düzeni; **etiket duruma göre değişmez**; yalnız durum metni
  Açık/Kapalı arasında değişir; durum metni sıfat. Yer varsa durum metni gösterilir; yoksa tik.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `Toggle` (`size`: `sm` | `md`; `labelText`, `hideLabel`, `labelA`, `labelB`,
  `readOnly`), `ToggleSkeleton`, `ToggleSmallSkeleton` (`ToggleSmall` diye bir dışa aktarım yok; küçük boy
  `size="sm"`). Bayrak `enable-v12-toggle-reduced-label-spacing`.
- **TEDY durumu:** **Kullanılıyor** — tek örnek odak kipi anahtarı (`DashboardHeader.tsx`
  `size="sm"`, başlık bandında; açık zemin `$support-success` = anlam rengi, İ8 uyumlu). Sapma
  (B41): `labelA="Odak" labelB="Odak"` — durum metni yuvasında sabit bir kelime; Carbon'un yolu
  `labelText="Odak" hideLabel` (etiket sabit, durum `aria-checked` ve tikte). Telefonda metin gizli
  (bir kelime "Çıkış"ı 320 px'te 16 px taşırdı; ölçüldü) — small toggle'ın tiki bunu karşılar. Bant
  rengi ve ters odak halkası kabuk iç teması (1.40). Modülde anahtar yok; ses/tema düğmeleri
  `aria-pressed` düğmeler.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/toggle/guidelines/

<a id="toggletip"></a>

### 1.37 Tıkla-aç ipucu (`toggletip`)

- **Ne için:** Bir düğmeye tıklanınca açılan ve kullanıcı kapatana dek açık kalan ek içerik; popover
  tabanlı; içinde etkileşimli öğe olabilir.
- **Kullan:** İçinde düğme ya da bağlantı gerekiyorsa; hızlı yerinde düzenleme; içeriği örten süzgeç
  paneli. Formda bilgi ikonu.
- **Kullanma:** Kritik bilgi ya da iş akışı için zorunlu girdi (→ modal). Etkileşimsiz kısa ek bilgi
  (→ tooltip).
- **Varyantlar:** Tek tür; tetik bir bilgi ikon düğmesi.
- **Ölçüler ve token'lar:** En çok 288 / 18 rem (dört sütun içinde kalması önerilir); dolgu 16;
  tetikten 8 (`$spacing-03`; tooltip'te 4). Tetik ikonu 16, sol boşluk 8. Zemin `$background-inverse`,
  metin `$text-inverse` `$body-01` 14; tetik `$icon-secondary` (hover `$icon-primary`). Sayfanın
  altından en az 16 px; **mobilde yalnız tetiğin altında**. Yön varsayılan otomatik.
- **Durumlar:** Açık (tık ya da `Enter`), kapalı.
- **Erişilebilirlik:** `Enter`/`Space` açar-kapar, odak tetikte kalır; etkileşimli öğe varsa `Tab`
  ilkine; yalnız metinse ya da son öğeden `Tab` kapatıp sonraki durağa; `Esc` kapatır ve odak içerideyse
  tetiğe döndürür. Tetik `aria-label="Show information"`, `aria-expanded`, `aria-controls`. 1.114.0:
  ek durumlar ertelenmiş.
- **İçerik:** Başlık, gövde, alt bilgi kullanım durumuna göre (disclosure kalıbı). Kaydırma gerekirse
  gövde dikey; yatay asla.
- **AI varyantı:** AI etiketi toggletip etkileşimini kullanır (1.2).
- **React:** `Toggletip`, `ToggletipButton`, `ToggletipContent`, `ToggletipActions`, `ToggletipLabel`.
- **TEDY durumu:** **Uygun ama kullanılmıyor.** En yakın yüzey başlıktaki senkron sağlık kutusu
  (`role="dialog"` kart; 1.24'teki klavye açıkları). Yoğun içerik (beş satır + bölüm listesi) 288 px
  ters yüzeye sığmaz; D3 kartı savunur (S30) — yüzey kart kalır, klavye sözleşmesi toggletip'inki olur
  (`aria-controls`, `Tab` ile çıkınca kapanma). `AiAciklama.tsx`'teki `AILabel` toggletip tabanlı.
  Bulgu: sağlık kutusunda portal ret gerekçesi yalnız odaklanmayan bir `<span title>` ile hover'da
  (D2, D3) — görünür satıra iner ya da toggletip olur.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/toggletip/guidelines/

<a id="tooltip"></a>

### 1.38 İpucu (`tooltip`)

- **Ne için:** Görsel etiketi olmayan denetimin adı ve odaklanabilir öğeye kısa, temel olmayan
  bağlam; hover **ya da** odakla açılır. Çoğu Carbon bileşeninde (ikon düğme, ikon sekme, kaydırıcı,
  kopya düğmesi) gömülüdür; ayrıca eklenmez. Tek ayrı bileşen tanım ipucudur (definition tooltip).
- **Kullan:** İkon düğmelerin adı; odaklanabilir öğeye ek bilgi; metin içinde ya da dar alanda
  (tablo) terim tanımı.
- **Kullanma:** Görevi bitirmek için gereken bilgi (her zaman görünen yardım metni); etkileşimli öğe
  (→ toggletip).
- **Varyantlar:** Gömülü ipucu · definition tooltip (noktalı alt çizgili terim; hover ya da tık).
- **Ölçüler ve token'lar:** Çok satırlı en çok 288 / 18 rem, dolgu 16; tek satır en çok 208 / 13
  rem, dolgu 16 / 2; tanım ipucu en çok 176 / 11 rem, dolgu 16 / 8, tetik 1 px noktalı alt çizgi;
  tetikten 4 (`$spacing-02`); caret 6. Zemin `$background-inverse`, metin `$text-inverse`; etiket
  `$label-01` 12, gövde `$body-01` 14. Sayfa altından en az 16 px; mobilde yalnız tetiğin altında.
  Gecikmeler sayfada belirtilmemiş ([paket] `enterDelayMs=100`, `leaveDelayMs=300`).
- **Durumlar:** Açık (hover ve odak), kapalı. İmleç ipucunun ya da tetiğin üstündeyken açık kalır.
- **Erişilebilirlik:** `Tab` ile gösterilir, `Esc` kapatır; ipucu `role="tooltip"`, tetik
  `aria-labelledby`. **Her yalnız ikon düğmenin ipucu vardır** (Kalın, İtalik gibi yerleşik adlar
  hariç); metin tasarımda yazılır. 1.114.0: geçti (Definition Tooltip ek durumlar ertelenmiş).
- **İçerik:** İkon düğmede 1–2 kelime; tanım ve öğretici ipuçları cümle düzeni ve noktalama ile.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `Tooltip` (`align`, `enterDelayMs`, `leaveDelayMs`), `DefinitionTooltip` (`definition`,
  `openOnHover`).
- **TEDY durumu:** **Kullanılıyor (gömülü).** Carbon ikon denetimleri adlarını kendileri gösteriyor:
  `IconButton label=` (`MesajAltbilgisi.tsx`, `YuklemeAlani.tsx`, `GirisDugmeleri.tsx`), `Button
  hasIconOnly iconDescription=` ("Önceki hafta"/"Sonraki hafta", "Sohbet penceresini aç"),
  `HeaderGlobalAction` ("Yenile", "Çıkış"). `Tooltip`/`DefinitionTooltip` doğrudan import edilmiyor.
  Bulgular: yerel `title=` tek bilgi kaynağı olamaz (yalnız fare; 1.37); `ReaderChrome.tsx` çıkış
  düğmesi elle yazılmış, ipucusuz (Carbon `IconButton` olur); eski `CitationChip` 352 px (> 288).
  Modül tanım ipucu `.def-pop` (`role="tooltip"`, hover/odak, `Esc`, `aria-describedby`) Carbon
  davranışında ama şekil farklı (ders renkli hap tetik, 300 px, 11 px ok); çocuk okur uyarlamasıysa
  `carbon-child-system.md` sapma tablosuna yazılır; modül üst bandındaki ikon düğmelerinde ipucu yok
  (§9). Talimatname §3.8.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/tooltip/guidelines/

<a id="tree-view"></a>

### 1.39 Ağaç görünümü (`tree-view`)

- **Ne için:** İç içe başlık düzeyleriyle içerik hiyerarşisi; açılıp kapanan dal düğümleri, her
  düzeyde yaprak düğümler.
- **Kullan:** Dosya sistemi benzeri yapılarda gezinme; birden çok düzeyde iç içe büyük bilgi.
- **Kullanma:** Sayfada öğe göstermek/gizlemek; tek düzey (→ accordion ya da data table); ürünün
  birincil gezinmesi (→ UI shell sol panel + breadcrumb).
- **Varyantlar:** Metin düğümleri · ikonlu düğümler (ya her düğümde ikon ya hiçbirinde; karıştırılmaz).
- **Ölçüler ve token'lar:** Düğüm sm 32 (varsayılan; sol panelle aynı geometri) · xs 24; düğümler 0
  aralıkla yığılır. Renk, tip ve yapı tabloları taramada kayıp — **sayfada belirtilmemiş** (tarama).
- **Durumlar:** Seçili; seçili çocuğun dalı kapalıysa ebeveyn seçili durumu devralır.
- **Erişilebilirlik:** Tek sekme durağı; girişte önceki seçili düğüm ya da ilk düğüm. `Right` açar /
  ilk çocuğa; `Left` kapatır / ebeveyne; `Up`/`Down` düğümler arası; `Enter` etkinleştirir; `Space`
  ya da `Enter` seçer. `ul role="tree"`, `li role="treeitem" tabindex="-1"`, `aria-selected`, dallarda
  `aria-expanded`. 1.114.0: geçti.
- **İçerik:** Dal etiketi çocuklarını özetler; yaprak kısa ve açıklayıcı; taşma üç nokta + tarayıcı
  ipucu (tercih edilmez).
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `TreeView` (`size`: `xs` | `sm`; `hideLabel`), `TreeNode`. Bayrak
  `enable-treeview-controllable`.
- **TEDY durumu:** **Uygun ama kullanılmıyor.** Bütün hiyerarşiler tek düzey ve Carbon'un tek düzey
  için önerdiği bileşenle (Tabs + Accordion); birincil gezinme `SideNav`. İki düzeyden derin bir
  hiyerarşi gelirse (MEBİ ders → ünite → konu, SEBİTV, kaynak paneli) iç içe akordeon değil
  `TreeView size="sm"`.
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/tree-view/guidelines/

<a id="ui-shell-header"></a>

### 1.40 UI kabuğu: başlık (`ui-shell-header`)

- **Ne için:** Arayüzü adıyla tanıtmak; gezinme bağlantıları ve sistem araçları için küresel, kalıcı
  yer. Kabuk üç bileşendir (başlık, sol panel, sağ panel); soldan sağa üründen küresele.
- **Kullan:** Her üründe en üst gezinme düzeyi.
- **Kullanma:** Başlık bağlantısı olarak fiil; alt menü etiketini bağlantı olarak.
- **Varyantlar:** Base · with navigation · with actions · with sidenav. Öğeler: hamburger (yalnız
  katlanır sol panel varsa), ad, bağlantılar (dar ekranda yan menüye), alt menü, araçlar (profil,
  arama, bildirim), switcher (en sağ, sağ panelde).
- **Ölçüler ve token'lar:** Yükseklik 48; hamburger ve eylem düğmeleri 48 × 48, eylem ikonu 20; ad
  sol 16 / sağ 32; bağlantı yan 16. Ad `$heading-compact-01` 14/600; bağlantılar `$body-compact-01`.
  Renk: zemin `$background`, alt çizgi `$border-subtle`, ad `$text-primary`, eylemler
  `$icon-secondary`, hover `$background-hover`, seçili bağlantı alt çizgisi `$border-interactive`.
  Tam genişlik; yapışık ya da kayan. Kabuk dört IBM temasından birini **kabuk bölgesine satır içi
  tema** olarak alabilir. İkonlar sağa, aralıksız; arama grubun en solunda, switcher en sağında.
- **Durumlar:** Etkin, hover, odak, aktif, seçili.
- **Erişilebilirlik:** Hedefler başlığın tam yüksekliğinde. **"Skip to main content"** ilk
  odaklanabilir öğe (WCAG 2.4.1), odak gelince görünür. Her öğe `Tab`; bağlantı ve ikonlar `Enter`,
  ikonlar `Space` da. HTML5 `header`. Her ürün için kabuk klavye etkileşimi bir kez tasarımda
  işaretlenir. [paket] `SkipToContent` varsayılan `href="#main-content"`; `Content` varsayılan `id`
  vermez. Dar ekranda bağlantılar ve menüler hamburgerli sol panele katlanır.
- **İçerik:** Ad kısa, yer duygusu verir; bağlantılar benzersiz, hedefi söyler.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `Header`, `HeaderName`, `HeaderMenuButton`, `HeaderNavigation`, `HeaderMenu`,
  `HeaderMenuItem`, `HeaderGlobalBar`, `HeaderGlobalAction`, `HeaderPanel`, `HeaderContainer`,
  `HeaderSideNavItems`, `SkipToContent`, `Content`.
- **TEDY durumu:** **Kullanılıyor** — `DashboardHeader.tsx`: `Header` → `HeaderMenuButton` →
  `HeaderName` (logo) → `HeaderGlobalBar` (ad/avatar, senkron sağlık tetiği, Odak anahtarı,
  `HeaderGlobalAction` "Yenile", "Çıkış"; ikon 20 ✓). **Bilinçli sapma:** lacivert marka bandı —
  zemin `--ted-color-brand-primary`, metin `--cds-text-on-color`, ikon `--cds-icon-on-color`, odak
  `--cds-focus-inverse`, hover `--ted-color-brand-primary-hover`, alt çizgi yok; Carbon'un "kabuk
  bölgesine satır içi tema" kapısından geçer, bu beş token başka yüzeyde kullanılmaz
  (`tests/test_pano_tasarim_sistemi.py`) (§3.2). Global bar'da ad ve senkron durumu var, çünkü D3
  "veri yok" ile "sistem bozuk"un her an görünmesini ister. Açıklar: **SkipToContent yok**, `Content`
  `id`'siz; ana içeriğe en çok 17 durakla varılıyor (B11); ≤ 22 rem'de eylemler 40 px'e iniyor
  (Carbon 48; S18); senkron tetiği 24 px. Okur rolünün başlığı elle yazılmış `ReaderChrome.tsx`
  (`Header` değil, atlama bağlantısı yok). Modül `.topbar` "Tedy bandı" (§9). Talimatname §5 "kabuk ve
  gezinme".
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/ui-shell-header/guidelines/

<a id="ui-shell-left-panel"></a>

### 1.41 UI kabuğu: sol panel (`ui-shell-left-panel`)

- **Ne için:** İkincil gezinme; başlığın altında, sola sabit; bağlantılar ve alt menüler karışık
  olabilir.
- **Kullan:** Beşten çok ikincil gezinme öğesi varsa ya da okur bunlar arasında sık geçiyorsa.
- **Kullanma:** Üç kademe gezinme (desteklemez; alt menünün altı → sayfa içi sekme).
- **Varyantlar:** Kalıcı · kalıcı olmayan (dar ekranda ya da ~%175 yakınlaştırmada hamburgerin
  arkasında; içeriği örter, genellikle karartır; hamburger X olur) · side rail (hover/klavyeyle
  açılır; genişliği sayfada belirtilmemiş).
- **Ölçüler ve token'lar:** Genişlik 256 / 16 rem, tam yükseklik; bağlantı, alt menü ve alt öğe 32
  yüksekliğinde, yan dolgu 16 (alt öğe sol 32); seçili kenar 4 px; ikon 16. Bağlantı ve alt menü
  `$heading-compact-01` 14/600; alt öğe `$body-compact-01` 14/400. Zemin `$background`; bağlantı
  `$text-secondary`, hover `$background-hover`, seçili `$background-selected` + `$border-interactive`.
  Kalıcı olmama kırılımının px değeri sayfada belirtilmemiş.
- **Durumlar:** Etkin, hover, odak, aktif, seçili; alt menü tıklanınca açılır, diğerlerini aşağı iter.
- **Erişilebilirlik:** Her öğe `Tab`; `Space`/`Enter` bölümü açar; `Enter` bağlantıyı etkinleştirir,
  ana içeriği günceller ve **odağı sayfanın başına koyar**; geçerli bağlantı kalın, `aria-current="page"`.
  `<nav aria-label>`, iç içe `<ul>`, alt menü `<button aria-expanded>`.
- **İçerik:** Sayfada ayrıca belirtilmemiş (başlık bağlantı kuralları geçerli).
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `SideNav` (`expanded`, `isRail`, `isFixedNav`, `isChildOfHeader`), `SideNavItems`,
  `SideNavLink`, `SideNavMenu`, `SideNavMenuItem`, `SideNavItem`, `SideNavIcon`, `SideNavLinkText`,
  `SideNavDivider`, `SideNavHeader`, `SideNavDetails`, `SideNavFooter`, `SideNavSwitcher`.
- **TEDY durumu:** **Kullanılıyor** — `App.tsx`: beş birincil `SideNavLink` + `SideNavMenu` "Daha
  fazla" altında yedi ikincil (toplam 12 > 5: Carbon eşiğine uygun; iki kademe). Ölçüler Carbon'un
  (16 rem). **Bilinçli sapmalar (S29):** rail asla (etiketin hover'a saklanması çalışan belleğe vergi; İ1/İ9);
  672 px altında hamburger ve yan menü gizli, yerine `BottomNav` (Bugün · İşler · Asistan · Dersler ·
  Daha fazla; 48 px; İ1, 2026-10-02 kararı); 672–1055 px arası Carbon'un hamburger modeli
  değişmeden geçerli. Hover zemini `$background-hover` yerine `--ted-color-page-bg` (S17 bağlamı);
  ≤ 671 px rail kuralı ölü kod. Rota değişiminde odağın sayfa başına taşındığı doğrulanmadı: `App.tsx`'te konuma bağlı odak kodu yok,
  ama çalışma zamanında ölçülmediği için borç sayılmadı. Tek sütun düzeni S1, S8. Talimatname §5 "kabuk ve gezinme".
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/ui-shell-left-panel/guidelines/

<a id="ui-shell-right-panel"></a>

### 1.42 UI kabuğu: sağ panel (`ui-shell-right-panel`)

- **Ne için:** Başlıktaki bir sistem ikonuna bağlı ek sistem düzeyi eylem ya da içerik; switcher
  burada yaşar.
- **Kullan:** Başlığın sağındaki bir ikonla açılan, ürünü değiştiren (switcher) ya da hesap/bildirim
  gibi küresel içerik.
- **Kullanma:** En sağ ikonu switcher dışında bir şey için; switcher için başka ikon.
- **Varyantlar:** Switcher paneli · diğer sistem panelleri; aynı anda yalnız biri açık.
- **Ölçüler ve token'lar:** Genişlik 256 / 16 rem, tam yükseklik, sağa yaslı, içeriğin üstünde yüzer;
  öğe 32, yan dolgu 16, `$heading-compact-01` 14/600. Zemin `$layer`, sol kenar `$border-subtle`;
  öğe `$text-secondary`, hover `$layer-hover`. Açıkken ikon dış çizgili, alt kenarı panele akar.
- **Durumlar:** Panel öğelerinin seçili durumu yoktur.
- **Erişilebilirlik:** Switcher düğmesi başlıktaki son öğe; `Space`/`Enter` açar; bağlantı `Enter`
  yükleyip paneli kapatır; `Esc` kapatır. Panel `<nav>`, bağlantılar `<ul>`. Switcher düğmesinin adı
  kapsamına göre ("App switcher").
- **İçerik:** Ayırıcı her öğeyi ayırmak için değil, grupları ayırmak için.
- **AI varyantı:** Sayfada belirtilmemiş.
- **React:** `HeaderPanel`, `Switcher`, `SwitcherItem`, `SwitcherDivider`.
- **TEDY durumu:** **Uygun ama kullanılmıyor.** Switcher yok; hesap eylemi "Çıkış" en sağda —
  Carbon'un "en küresel sağda" kuralıyla tutarlı. Sağlık kutusu sağ panel değil (bağlı kart, tam
  yükseklik değil). Asistan başlatıcısı yüzen birincil düğme; Carbon'un birincil sayımından muaf
  tuttuğu "yan panel" sayılıp sayılmayacağı talimatnamede karara bağlanır (S12, B17). Sistem düzeyi
  bir panel gerekirse Carbon `HeaderPanel` (16 rem, `$layer`, `Esc`).
- **Kaynak:** https://carbondesignsystem.com/building-blocks/core/components/ui-shell-right-panel/guidelines/

## 2. Kalıplar

Carbon'un 18 kalıp sayfasının (overview + 17) kartları. Her kart aynı alanları taşır: **Ne için** ·
**Carbon kuralları** (sayfada yazanlar; sayfa bir değer vermiyorsa "sayfada yok" denir) · **TEDY'de nerede**
(`dashboard/src` altındaki yol; satır numaraları 2026-10-10 taramasına göredir, kayabilir) · **TEDY kuralı /
sapma** (talimatname [§5](tedy-ui-ux-talimatnamesi.md#5-kalıplar), sapmalar §11 S-numarası, borçlar §13
B-numarası, karar bekleyen çelişkiler §11.2 Ç-numarası) · **Test** · **Kaynak**.

Carbon kalıbı bileşen değildir: "Patterns differ from components … patterns have multiple ways of accomplishing
a user need and typically use a combination of components". Kalıp kartı bu yüzden bir bileşen seçimi değil,
bir karar sırası verir; bileşenin kendisi 1. bölümdeki kartındadır. Bu ek talimatnameye bağlıdır: çelişkide
talimatname ve anayasa kazanır (öncelik sırası, talimatname §0).

<a id="kalip-overview"></a>

### 2.1 Genel bakış (`overview`)

- **Ne için.** Carbon'un kalıp kataloğu: 14 kalıp, her biri bir kullanıcı ihtiyacını birden çok bileşenle çözer;
  kod yalnız bazı kalıplarda vardır.
- **Carbon kuralları.** Katalog sırası: Common actions · Dialogs · Disabled states · Disclosures · Empty states ·
  Filtering · Forms · Global header · Loading · Login · Notifications · Read-only states · Search · Text toolbar.
  Fluid styles ve Status indicators katalog tablosunda yok, ayrı sayfalardır. Sayfa "Ready-only states" diye
  yazım hatası taşır ve "Search" satırını kalıp yerine bileşen sayfasına bağlar.
- **TEDY'de nerede.** Kalıpların TEDY karşılığı [anayasa](frontend-design-principles.md) D1–D4 / İ1–İ9 ve
  [yüzey tasarımları](frontend-surface-designs.md) §2 ortak kalıplarıdır (§2.3 boş durum, §2.4 yükleniyor,
  §2.5 katlama, §2.6 eylem, §2.7 rozet).
- **TEDY kuralı / sapma.** Bir Carbon kalıbı ölçülmüş bir TEDY kuralını sessizce ezmez; çelişki §11'e yazılır.
- **Test.** Yok (dizin sayfası).
- **Kaynak.** https://carbondesignsystem.com/building-blocks/core/patterns/overview/

<a id="common-actions"></a>

### 2.2 Ortak eylemler (`common-actions`)

- **Ne için.** Bileşenler ve akışlar boyunca tekrarlanan eylemlerin tek biçimi: "apply these actions only in the
  prescribed ways".
- **Carbon kuralları.** Sayfadaki eylemler tam olarak şu on ikidir (Save ve Apply bölümü yoktur; Apply yalnız
  Reset'in tanımında geçer):

  | Eylem | Ne yapar | Denetim |
  |---|---|---|
  | Add | Var olan bir nesneyi listeye/kümeye ekler | Vurgu yüksek/orta/düşük; yüksek vurguda tek birincil, diğerleri ikincil |
  | Cancel | Süren eylemi durdurur, bileşeni kapatır; olumsuz sonucu (veri kaybı) önceden söyler | İkincil düğme ya da bağlantı |
  | Clear | Alandaki veriyi ya da seçimi siler; varsayılanı olan denetimde varsayılana döner | Alanın sağında `close` ikonu |
  | Close | Sayfa, pencere ya da menüyü kapatır; bildirimi kaldırır | `close` ikonu, genelde sağ üst. **Düğme içinde "Close" kullanılmaz** |
  | Copy | Seçilen nesnenin özdeş kopyasını oluşturur | `copy` ikonu + tıklamadan sonra "copied" onay tooltip'i |
  | Delete | Nesneyi yok eder; genelde kalıcı | `delete`/çöp kutusu ikonu, danger düğme ya da menüde danger seçenek; uyarı gerekiyorsa danger modal |
  | Edit | Değer değiştirmeye izin verir | Menü seçeneği, düğme ya da `edit` ikonu |
  | Errors | Başarısız eylemi bağlamı ve devam yoluyla bildirir | Küçük bileşende satır içi; tam sayfa/büyük modalda en çok 3 satır, form hatasında en çok 2 satır |
  | Next | Adımlı akışta sonraki adım | İkonlu düğme ya da tek başına `forward` ikonu |
  | Refresh | Kaynakla eşzamanı bozulan görünümü yeniden yükler | `refresh` ikonu ya da düğme |
  | Remove | Nesneyi listeden çıkarır, yok etmez; toplu olabilir | Düğme ya da `subtract` ikonu; nadiren birincil, aşırı vurgulanmaz |
  | Reset | Değerleri son kaydedilmiş (son Apply) duruma döndürür | Genelde bağlantı |

  Silmenin üç etki düzeyi: **düşük** (geri almak/yeniden oluşturmak kolay) → tıklamada uyarısız sil; **orta**
  (geri alınamaz ya da kolay yeniden oluşturulamaz, ya da birden çok nesne) → ne olacağını söyleyen onay;
  **yüksek** (yeniden oluşturmak pahalı, büyük veri ya da zincirleme silme) → diyalog + kaynağın adını elle
  yazdırma. Silmeden sonra: listeye dön, kaldırmayı canlandır, başarı bildirimi; başarısızsa "silinemedi"
  bildirimi. Add ve Remove için sayfa altı/yedi soruluk bir kontrol listesi verir (izin, kalıcılık, süre,
  başarısızlık, tekil/toplu, sonuçlar).
- **TEDY'de nerede.**
  - Close: `x` + `aria-label="Kapat"` — `components/CalendarEvents.tsx` (olay popover'ı),
    `components/BookReader.tsx`, `components/HomeworkTracker.tsx` (`ModalHeader iconDescription="Kapat"`).
    Metin düğmesi "Kapat": `components/SohbetListesi.tsx:61` (telefon çekmecesi) — Carbon'un "düğmede Close yok"
    kuralına aykırı.
  - Delete: `components/SohbetListesi.tsx:50` (sohbet) ve `:72` (asistan notu) ghost "Sil", **onaysız**; sunucu
    silmesi sohbetin eklerini ve alıştırma/günlük satırlarını da kaldırır (CLAUDE.md, asistan B3 sohbet geçmişi) → Carbon'un orta etki
    durumu. Silme hatası yanlış fiille: `asistan/GecmisPaneli.tsx:20` "Sohbet kaydedilemedi.". Pano genelinde
    `kind="danger"` 0.
  - Remove: `asistan/GirisEkleri.tsx` gönderilmemiş ek çipi `aria-label="Kaldır: …"` (gerçek Remove);
    `components/HomeworkTracker.tsx` "Kaldır" yüklenmiş belgeyi sunucuda siler (adı Remove, işi Delete).
  - Copy: `asistan/MesajAltbilgisi.tsx:40` `IconButton label="Kopyala"` — "Kopyalandı" onayı yok (Carbon AI
    Chat'in kod parçası onayı ayrı: `asistan/dilPaketi.ts` "Kopyalandı!").
  - Refresh: `components/DashboardHeader.tsx` `HeaderGlobalAction aria-label="Yenile"` + Renew ikonu.
  - Next: `components/NextThing.tsx` "Başla" + `ArrowRight`; `components/ModOnerisi.tsx` tertiary + `ArrowRight`;
    `components/AlistirmaKarti.tsx` "Sonraki soru" ikonsuz.
  - Errors: `components/RouteBoundary.tsx` iki cümle + tek "Yeniden dene"; `asistan/GirisUyarisi.tsx`
    `InlineNotification`. Uzunluklar 2/3 satır sınırında.
  - Clear (alan içi `x`) ve Reset (bağlantı): panoda yok.
- **TEDY kuralı / sapma.** [§5](tedy-ui-ux-talimatnamesi.md#5-kalıplar) eylem + yüzey tasarımları §2.6 (tek
  birincil; diğerleri ghost/tertiary). Tek birincil kuralı S12; Asistan başlatıcı ve Modüller satır başı birincil
  düğmeleri B17. Silme Carbon'un etki derecesiyle yazılır: düşük → anında + aynı satırda "Geri al" (toast değil);
  orta (sohbet silme) → danger `Modal`, başlık ve birincil düğme aynı eylemi söyler ("Bu sohbet silinsin mi?" /
  "Sohbeti sil" / "Vazgeç"), başarı bildirimi yok (satırın listeden çıkması onaydır, İ6), başarısızlık satırda
  "Sohbet silinemedi." (D3). Bu derecelendirme 2026-10-10'da karara bağlandı (S40; yüzey tasarımları §2.6'nın eski
  "Yıkıcı eylem yok" cümlesi yerine). Bugünkü kod B23 (onaysız silme + yanlış fiil), B63 ("Yaptım"ın geri alı).
  Ad yazdırmalı yüksek etki basamağı kullanılmaz. Tekrarlanan düğme ("Sil", "Yaptım") görünen metnini adında tutar, satırı
  `aria-describedby` ile bağlar (WCAG 2.5.3). Kopyalama onayı ve "Kapat" metin düğmesi B41.
- **Test.** Önerilen Playwright: "Sil" → `role=dialog`, birincil `.cds--btn--danger`, `DELETE` isteği yalnız
  onaydan sonra (rota sayacı); "Vazgeç" sonrası sohbet listede kalır. Grep: `components/` altında metni "Kapat"
  olan `Button` 0.
- **Kaynak.** https://carbondesignsystem.com/building-blocks/core/patterns/common-actions/

<a id="dialogs"></a>

### 2.3 Diyaloglar (`dialogs`)

- **Ne için.** Kullanıcıdan girdi ya da akışıyla ilgili acil bilgi gerektiğinde, sayfanın üstünde açılan ve
  kapatılana dek kalan yüzey. "Dialogs are disruptive … Use them sparingly."
- **Carbon kuralları.**
  - Anatomi: başlık (başlık + isteğe bağlı üst etiket + kapatma ikonu), gövde, eylemler ("Add, Delete, Save" gibi
    betimleyici fiiller; "Done", "OK" gibi belirsiz sözcükler yok), `x` (veri göndermeden kapatır), örtü (yalnız
    modal).
  - Kullanılmaz: iş akışıyla ilgisiz içerik, karmaşık/büyük veri, tam uygulamayı ya da sayfayı yeniden kurmak,
    **kullanıcının tetiklemediği durum** (sistemden gelen arka plan uyarısı → toast). Dolaylı tetik serbest
    (kaydedilmemiş sekmeyi kapatınca "değişiklikler kaydedilsin mi?").
  - Modal varyantları:

    | Varyant | Kullanım | Düğmeler | Kapatma |
    |---|---|---|---|
    | Passive | Akışla ilgili bilgi, eylem yok | — | `x`, dışarı tıklama, `Esc` |
    | Transactional | Tamamlanması bir eylem ister | İptal + birincil | Görev tamamlanınca, İptal ("Cancel undoes all applied changes"), `x`, `Esc` |
    | Acknowledgment | Bilginin onaylanması | Tek düğme ("commonly 'OK'") | Transactional ile aynı |
    | Progress | Kapanmadan önce birkaç adım | İptal, Önceki, Sonraki/tamamla | Transactional ile aynı |

    Modal dışı (non-modal) diyalog: Passive ve Transactional; sayfa erişilebilir kalır; `x`, İptal, `Esc` kapatır.
  - Modal iç içe açılmaz ("One modal should never trigger another modal"); tam sayfa yapılmaz ("A modal is not an
    alternative to page"); yıkıcı/geri alınamaz onay → transactional **danger** modal; başlık ve düğme aynı eylemi
    söyler.
  - Düğme grubu: İptal en solda, birincil en sağda, diyalog başına tek birincil; düğmeler tam taşar ve alta
    yapışır. Tek düğme %50 genişlik sağda; iki düğme %50 + %50; üç düğme her biri %25 sağa hizalı (yalnız en
    sağdaki birincil olabilir; üçü eşitse üçü ikincil); progress: İptal (ghost, solda) + Önceki + Sonraki, her biri
    %25; son adımda Sonraki'nin etiketi son eyleme döner.
  - Davranış: ilk odak girdi kabul eden ilk yere, modalda odak hapsedilir, kapanınca açan öğeye döner (WCAG
    2.4.3); girdi varken ilk odak düğmeye verilmez. Sekme sırası: gövde (soldan sağa, yukarıdan aşağı) →
    birincil → ikincil → kapatma ikonu. Gövde kayar, başlık ve altbilgi sabit kalır. Doğrulama kapanmadan önce,
    alan odaktan çıkınca; sunucu hatası satır içi bildirim. Kısa yükleme: modal gövdesinde spinner + örtü, birincil
    düğme pasif; birkaç saniyeden uzunsa ilerleme başka yerde.
  - İçeride: form denetimleri, content switcher, structured list. Kaçınılır: bağlamdan çıkaran bağlantı, bilgiyi
    saklayan bileşen (accordion, tabs), karmaşık data table.
  - Sayfada olmayan: modal boyutlarının değerleri ve max-height'lar (modal bileşen sayfasındadır), renk/tip/aralık
    token'ı.
- **TEDY'de nerede.** İki diyalog, ikisi de Carbon:
  - `components/HomeworkTracker.tsx:403` `ComposedModal size="md"` + `ModalHeader` + `ModalBody`, altbilgi yok →
    **passive**; yalnız açıkken DOM'da (kapalı `ComposedModal` başlığını belge ana hattında tutuyordu). Kapatma
    düğmesinin erişilebilir adı "Kapat" (`iconDescription`, `isler.spec.ts` sabitler; B15 kapandı).
  - `asistan/SesOnayi.tsx:9` `Modal modalHeading="Mikrofon" primaryButtonText="Onayla" secondaryButtonText="Vazgeç"`
    → **transactional**, Carbon'un 50/50 altbilgisi; mikrofona basmanın dolaylı sonucu (izinli). Başlık yalnız ad,
    birincil "Onayla" belirsiz; hatası `<p role="alert">` olarak modalın **dışında**.
  - Modal dışı, pasif: `asistan/AsistanBaslatici.tsx` (Carbon AI Chat paneli), `components/DashboardHeader.tsx`
    senkron popover'ı (`role="dialog"`); ikisi de `Esc` / dışarı tıklamayla kapanır.
  - `theme/ted-theme.scss` modal görünürken `.bottom-nav`'ı gizler. Danger modal yok.
- **TEDY kuralı / sapma.** [§5](tedy-ui-ux-talimatnamesi.md#5-kalıplar) diyalog. "Tamam/Onayla/Evet/OK" düğme
  etiketi olmaz (İ9; Carbon'un "commonly 'OK'" satırı aynı sayfanın anatomisiyle çelişir, anatomi kazanır).
  Mikrofon diyaloğu: başlık "Mikrofonu açalım mı?", birincil "Mikrofonu aç" — B41 (asistan B5 ses planının e2e metinleri birlikte
  değişir). Diyalogdaki hata diyalogun içinde, satır içi. Odak dönüşü bir testle sabitlenir.
- **Test.** Var: `tests/e2e/isler.spec.ts` (modal kapatma adı), `tests/e2e/carbon-asistan-ses.spec.ts` (onay
  beklenir, kendiliğinden gönderilmez). Önerilen: ödev modalı kapanınca odak açan karta döner; grep
  `primaryButtonText` ∉ {Onayla, Tamam, Evet, OK}.
- **Kaynak.** https://carbondesignsystem.com/building-blocks/core/patterns/dialogs/

<a id="disabled-states"></a>

### 2.4 Devre dışı durumlar (`disabled-states`)

- **Ne için.** Bir bileşenin etkileşimini tümüyle kaldırmak.
- **Carbon kuralları.**

  | Varyasyon | Tanım |
  |---|---|
  | Default disabled | Tıklanamaz, seçilemez; ekran okuyucu okumaz; varsayılan devre dışı görünüm |
  | Read-only | Etkileşim yok ama içerik okunur ve ekran okuyucuya açık; `$interactive` rengi, hover, alt çizgi gibi etkileşim işareti yok |
  | Hidden | Tümüyle gizli; yalnız izin değişince görünür (ör. yalnız kuruluş sahibi "Add member" görür) |

  Varsayılan devre dışı görünüm ("most commonly"; kesin değer her bileşenin sayfasındadır):

  | Öğe | Değer |
  |---|---|
  | Bileşen | %50 opaklık |
  | Metin | %25 opaklık |
  | İkon | %50 opaklık |
  | Hover | Yok |
  | İmleç | `not-allowed` |

  Geçici devre dışı (bağımlılık/önkoşul) bileşen **asla görünümden tamamen kaybolmaz**. Birden çok öğeyi ya da
  akışın birincil eylemini etkileyen devre dışı durum, nasıl yeniden etkinleşeceğini söyleyen satır içi uyarı
  bildirimi taşıyabilir.
- **TEDY'de nerede.** Carbon bileşenleri kendi görünümünü taşır (`Button disabled`,
  `components/OdevOnayKarti.tsx:46` `fieldset disabled`, `components/AlistirmaKarti.tsx:87` `RadioButtonGroup`).
  Elle yazılmış: `components/AssistantChat.scss` `.ac__prompt-chip:disabled { opacity: 0.5; cursor: not-allowed }`.
  Modül şablonunda beş farklı opaklık (.45, .4, .75, .85, satır içi .4) ve iki imleç. Nedenini söyleyen devre dışı:
  `components/YuklemeAlani.tsx` "Ekleniyor…", `components/AlistirmaKarti.tsx` "Cevap gönderiliyor". Gizli (izin):
  `routes.ts` `readerAccess`, `components/SohbetListesi.tsx` başkasının sohbetinde ad değiştir/sil yok.
- **TEDY kuralı / sapma.** [§5](tedy-ui-ux-talimatnamesi.md#5-kalıplar) salt okunur / devre dışı. TEDY özel
  denetimleri opaklık sayısıyla değil Carbon'un devre dışı renk token'larıyla boyar: `ted-theme.scss`'te ölçüldü,
  %40 opaklıklı metin 3:1'in altına düştü ("by colour, not opacity"). Birincil eylemi kilitleyen devre dışı düğmenin
  yanında nedeni söyleyen bir cümle durur (D3; Carbon'un satır içi uyarısının TEDY biçimi). Modül şablonundaki beş
  opaklık kuralı (dört değer) ve bir satır içi opaklık tek kurala iner — B34 (modül tarafı, `vendor/` tek kaynak).
- **Test.** Önerilen: stylelint/grep — `components/**/*.scss` içinde `:disabled` bloklarında `opacity` 0; modülde
  G-TOKEN kapısına devre dışı opaklık denetimi.
- **Kaynak.** https://carbondesignsystem.com/building-blocks/core/patterns/disabled-states/

<a id="disclosures"></a>

### 2.5 Açılırlar (`disclosures`)

- **Ne için.** Bir UI parçası hakkında ek içeriği tetik + popover ile açmak. Tooltip'ten farkı: içerik
  etkileşimli öğe taşıyabilir.
- **Carbon kuralları.**
  - Kullanılır: ek içerik; popover'da etkileşimli öğe; bölüm/sayfa ayar-süzgeç-sıralama menüleri; profil menüsü,
    combo button, menu button. Kullanılmaz: kritik bilgi ya da zorunlu girdi (→ modal); **tıklamayla açılmayan**
    popover; **altı sütundan geniş** popover.
  - Kurallar: altı sütun ya da daha dar; **asla kendiliğinden açılmaz**; **aynı anda tek açılır**; iç içe açılır yok
    (bağlam menüsünün yana açılan alt menüsü hariç); kritik bilgi açılırın içinde saklanmaz.
  - Açma: tetiğe tıklama, `Enter`/`Space`. Kapatma: tetiğe yeniden tıklama, dışarı tıklama, `x`, `Esc`, `Tab` ile
    çıkış. Kapatma `x`'i popover'ın sağ üst köşesinde, satır içi etkileşimli öğelerle çakışmadan.
  - Görsel: tetik 48 / 40 / 32 px (lg/md/sm), tetik ikonu 20 ya da 16 px; başlık gövdenin üstünde 0 px dolguyla ya
    da ayraçla, altbilgi 16 px dolguyla ya da ayraçla; ayar/süzgeç menüsünde öğeler arası en az 16 px.
  - Kullanım örnekleri: profil menüsü (açınca odak ilk öğeye, `Up`/`Down`), ayar ve süzgeç menüsü (açınca odak ilk
    etkileşimli öğeye; canlı süzme yoksa Reset/Apply düğme grubu, Apply menüyü kapatır), combo button (varsayılan
    eylem metin-yalnız, ikon yok).
  - Sayfa accordion / expandable tile / "show more" / tabs arasında seçim **vermez** (accordion için 1. bölümdeki
    kart; "show more" için 2.14).
- **TEDY'de nerede.** Carbon `Popover` bir yerde: `components/CitationChip.tsx:42` — **hover ve odakla** açılır,
  bilgilendirici (etkileşimli öğe yok); işlevce tooltip/toggletip melezi. Elle yazılmış popover'lar:
  `components/DashboardHeader.tsx` senkron durumu (`aria-expanded`, `aria-haspopup="dialog"`, `Esc` + dışarı
  tıklama); `components/CalendarEvents.tsx` olay popover'ı (sağ üst `x` "Kapat", dışarı tıklama) — **`Escape`
  işleyicisi yok**. Katlamalar (tetik + satır içi bölge): `components/HomeworkTracker.tsx` grup başlıkları,
  `components/ExamTimeline.tsx` "Detaylar/Gizle", `components/TodaySchedule.tsx` "Göster/Gizle",
  `components/SohbetListesi.tsx` "Sohbetler". Accordion/Tabs: `components/CourseContent.tsx`,
  `components/Announcements.tsx`, `components/PlatformProgress.tsx`; "Daha fazla" `SideNavMenu` (`App.tsx`).
  Profil menüsü, süzgeç menüsü, combo button yok.
- **TEDY kuralı / sapma.** [§5](tedy-ui-ux-talimatnamesi.md#5-kalıplar) katlama/açılma + yüzey tasarımları §2.5:
  eylem gerektiren açık, geçmiş kapalı başlar (İ7); bugün eylem gerektiren hiçbir şey katlanmış başlamaz (Carbon:
  kritik bilgi açılırda saklanmaz). Popover türü açılırlar aynı anda tek açık; `Esc`, dışarı tıklama ve `Tab` kapatır.
  Takvim popover'ının `Esc` eksiği B49. Katlama fiili tek: "Göster/Gizle" ("Detaylar" İ9 ihlali, B41).
- **Test.** Var: `tests/e2e/dashboard.spec.ts` (senkron popover'ı). Önerilen: senkron popover'ı açıkken takvim
  olayına tıkla → açık popover sayısı 1; takvim popover'ı `Esc` ile kapanır; İşler'de aktif grup ilk yüklemede
  `aria-expanded=true`; `.cds--accordion__content` içinde `.cds--accordion` yok.
- **Kaynak.** https://carbondesignsystem.com/building-blocks/core/patterns/disclosures/

<a id="empty-states"></a>

### 2.6 Boş durumlar (`empty-states`)

- **Ne için.** Gösterilecek veri olmayan anı bilgilendirici ve ileri götüren bir ana çevirmek: veri olsaydı ne
  görüneceğini söyle, sonraki adımı göster.
- **Carbon kuralları.**
  - Anatomi: görsel (isteğe bağlı, etkileşimsiz) → başlık (kısa, mümkünse olumlu: "Start by adding data assets",
    ya da "You don't have any data assets yet") → gövde (sonraki eylem; isteğe bağlı neden ve fayda) → birincil
    eylem (düğme ya da metindeki bağlantı ya da kullanıcıyı UI öğesine yönlendirmek; isteğe bağlı) → ikincil
    çağrı (ör. belge bağlantısı, metnin altında).
  - Türler (taramada kaybolan tablo ayrıca kurtarıldı):

    | Tür | Kullanım | Hedef | Ne zaman |
    |---|---|---|---|
    | Veri yok | İlk kullanım, henüz veri yok | Veri gelince ne olacağını ve nasıl ekleneceğini anlar | Basit durumlar, ikincil özellikler |
    | Kullanıcı eylemi | Aramada sonuç yok; bir sürecin tamamlanma onayı | Aramayı/süzgeci nasıl değiştireceğini ya da işin bittiğini anlar | Bir etkileşime geri bildirim gerektiğinde |
    | Hata yönetimi | İzin, sistem, yapılandırma sorunu | Sorunu ve varsa düzeltici eylemi bilir | Bir şey ters gittiğinde; daha fazla ayrıntı |

    | Hata türü | Neden veri yok | Kullanıcı ne yapabilir |
    |---|---|---|
    | İzin sorunu | Görme izni yok | Erişim isteme adımı |
    | Sistem sorunu | İlgili bir sistem veriyi sağlayamıyor | Ne olduğunu öğrenme adımı (ör. etkinlik günlüğü) |
    | Yapılandırma gerekli | Ek yapılandırma gerekebilir | Açıklama + ilk adım |
    | Eylem desteklenmiyor | Ör. desteklenmeyen dosya türü | Desteklenen türleri söyle |

    Derinlemesine alternatifler (ilk kullanım): satır içi belgeleme, onboarding (isteğe bağlı olduğu için temel
    boş durumla birlikte), başlangıç içeriği (silinebiliyorsa yedek boş durum gerekir).
  - Yapma: tek boş durumda birden çok seçenek; kullanıcının bilmediği ürün terimi; uygulamanın başka alanı hakkında
    içerik; çıkmaz; şaka ya da hafif dil (hata türünde).
  - Görsel: küçük alanda öğeler blok halinde sola hizalı (istisna: küçük karoda görsel, sola hizalı metnin üstünde
    ortalı); **"If space is limited, use just text"**; aynı anda birden çok boş durumda çağrı **tertiary düğme**;
    büyük alanda sola hizalı blok, geniş sol boşluk ya da blok-ortalama.
  - **Boş durum, normalde görünecek öğenin yerini alır**: boş tablonun başlık satırı ve altbilgisi gösterilmez
    (ekran okuyucu boş tabloyu baştan sona okumasın). Panoda birçok bileşen aynı anda boşsa salt metin tercih edilir.
  - Erişilebilirlik: dekoratif görsel ekran okuyucudan gizlenir; `alt=""` önerilir, `role="presentation"` değil.
  - Sayfada yok: görsel boyutu, tip ve aralık token'ı.
- **TEDY'de nerede.** Tek biçim `components/patterns/EmptyLine.tsx` (`<p class="tedy-empty">`, isteğe bağlı
  etiket; `patterns.scss`'te `body-compact-01`, `$text-secondary`); görsel, başlık bloğu ya da kendi düğmesi yok.
  Kullanım: `HomeworkTracker.tsx` ("Şu an teslim bekleyen bir işin yok."), `Announcements.tsx`, `Modules.tsx`,
  `PlatformProgress.tsx`, `TeamActivities.tsx`, `ExamTimeline.tsx`, `StudentProfile.tsx`, `TodaySchedule.tsx`,
  `CourseContent.tsx`. Öğenin yerini alma: `GradeTable.tsx` ve `WeeklySchedule.tsx` başlıksız tablo yerine
  `EmptyLine` döndürür. Hata yönetimi ayrı yolda: `PortalStatusBanner.tsx` ("sunmuyor" ↔ "okunamadı" iki ayrı
  cümle), `RouteBoundary.tsx` ("Bu bölüm açılamadı … Yeniden dene"). İyi örnek eylemli boş durum:
  `SohbetListesi.tsx` "Henüz sohbet yok — bir soru sorarak başla". Kullanıcı eylemiyle boşalma (takvimde bütün
  türler gizlenince) için tanımlı cümle yok.
- **TEDY kuralı / sapma.** [§5](tedy-ui-ux-talimatnamesi.md#5-kalıplar) boş durum + yüzey tasarımları §2.3: boş
  durum **tek satır metindir, kart ya da görsel değil** — bilinçli sapma (S32): 2026-08-31 ölçümünde ~200 px'lik güneş
  ikonu tek-iş kartıyla yarıştı (İ6); Carbon'un kendi "yer azsa salt metin" ve "birden çok boş durumda salt metin"
  kaçışları bunu kapsar. Cümle Carbon'un sırasını taşır: ne yok → neden (biliniyorsa) → ne yapılabilir; yol yoksa
  cümle orada biter. Üç tür adıyla ayrılır: veri yok (`EmptyLine`), kullanıcı eylemiyle boş (seçimi adlandırır ve
  geri dönüşü aynı satıra koyar), hata (boş durum değildir; `InlineNotification` ya da `PortalStatusBanner`, D3).
  Boş durumdaki eylem tertiary/ghost (İ1, §2.6). Bugün API hatalarının sessizliği B6.
- **Test.** Var: `tests/e2e/okunamadi.spec.ts` (okunamayan bölüm "boş" denmez), `tests/e2e/portal-status.spec.ts`,
  `tests/e2e/takvim.spec.ts` (kapalı takvim boş hafta çizmez), `tests/e2e/carbon-asistan-sohbet.spec.ts` (boş
  liste cümlesi), `tests/e2e/empty-surfaces.spec.ts`. Önerilen üç fixture (API boş dizi / kullanıcı süzgeciyle sıfır
  / API 500): (c)'de `.tedy-empty` yok, `.cds--inline-notification` var. AST: `EmptyLine` içinde `svg`/`img` yok.
- **Kaynak.** https://carbondesignsystem.com/building-blocks/core/patterns/empty-states/

<a id="filtering"></a>

### 2.7 Süzme (`filtering`)

- **Ne için.** Görüntülenen veri kümesine öğe ekleyip çıkarmanın düzeneği.
- **Carbon kuralları.**

  | Seçim yöntemi | Tanım | Denetim |
  |---|---|---|
  | Tekli seçim | Tek öznitelik | Radyo gibi: dropdown, inline dropdown, radyo seti |
  | Çoklu seçim | Birden çok öznitelik | Onay kutusu gibi: multiselect, inline multiselect, onay kutusu seti |
  | Çoklu kategori | Birden çok kategoride öznitelik | Sayfanın solunda dikey ya da veri kümesinin üstünde yatay; **asla menü ya da dropdown içinde değil** |
  | Toplu güncelleme | Seçimler ek bir eylemle uygulanır | Tetik çoğunlukla "Apply filters"; çok kategorili, düşünme gerektiren ya da yavaş veri |
  | Anlık güncelleme | Her seçimde sonuç yenilenir | Tek kategori ya da tek seçim beklenen durum |

  Kategorideki süzgeçler ya hepsi seçili ya hiçbiri seçili başlar. Gizli süzgeç kabında (çekmece, menü) kapalıyken
  görünür bir gösterge en az **uygulanan süzgeç sayısını** taşır ve **kabı açmadan temizleme** sunar. Her kategori
  tek hamlede temizlenir; çok kategoride tümünü birden kaldırma da vardır; temizleme varsayılan başlangıç durumuna
  döner. Sayfa px, token ya da sayı vermez.
- **TEDY'de nerede.** Tek anlık, tek kategorili süzgeç: `components/CalendarEvents.tsx` olay türleri
  (`hiddenTypes`); lejant süzülmüş listeden değil tarih penceresinden türetilir, gizlenen tür lejantta kalır (kabı
  açmadan geri alma işini görür). Tekli seçim: `components/CourseContent.tsx` hafta `Dropdown` (birden çok hafta
  varsa, odak kipi dışında). Multiselect, toplu "Uygula", çok kategorili panel yok.
- **TEDY kuralı / sapma.** [§5](tedy-ui-ux-talimatnamesi.md#5-kalıplar). Çelişki yok: Carbon sıfırlama denetimini
  ister, İ5 seçimin gezinme ve yeniden yüklemede korunmasını ister; ikisi birlikte geçerli. Bütün türler gizlenince
  boş durum "kullanıcı eylemi" türüdür (2.6).
- **Test.** Önerilen: takvimde bir tür gizle → yeniden yükle → tür gizli kalır (İ5); bütün türler gizliyken satır
  seçimi adlandırır ve geri alma düğmesi taşır.
- **Kaynak.** https://carbondesignsystem.com/building-blocks/core/patterns/filtering/

<a id="fluid-styles"></a>

### 2.8 Akışkan stiller (`fluid-styles`)

- **Ne için.** Bileşenin kabının bir ya da daha çok kenarına taşarak bileşik bir yapının parçası olduğu "fluid"
  görünüm; varsayılan stille aynı işlev, farklı görünüm ve hizalama.
- **Carbon kuralları.**
  - Terimler: sabit genişlik, akışkan genişlik; varsayılan stil (productive, ürün UI'ında en yaygın) ↔ akışkan stil
    (expressive, "drama and emphasis"); productive an ↔ expressive an.
  - Kullanılır: dikkat çekilmesi gereken expressive anlar, bileşik bileşenin içinde, ferah düzen. Kullanılmaz:
    girdiler arası boşluk gereken ya da yoğun düzen, **karmaşık form gibi hiper-productive an**, accordion ya da
    bölümlü kap içinde (hiyerarşi karışır).
  - Akışkan girdi: etiket alanın içinde; **tek yükseklik 64 px**. Akışkan düğme: kap genişliğinin **%25 / %50 /
    %100**'ü, en az bir kenara yapışık, akışın ortasına gömülmez. Sabit genişlikli varsayılan düğme: etiket + sağda
    64 px, solda 16 px sabit dolgu; ilgili düğme grupları aynı genişlikte.
  - Akışkan formlar araya boşluk koymaz (0 px), condensed/narrow gutter; varsayılan formlar wide gutter.
    Akışkan form yalnız basit görevde; karmaşık ya da çok bölümlü form varsayılan stilde.
  - Erişilebilirlik: yığılmış akışkan bileşenler arasında **3:1 kenarlık**. En yaygın eşleşme: varsayılan girdiler
    + modal ya da yan paneldeki akışkan düğmeler.
- **TEDY'de nerede.** `Fluid*` bileşeni 0. Bütün girdiler varsayılan stilde, 40 px; özel ders formundaki yerel
  denetimler Carbon'un varsayılan anatomisine çizilir (`ted-theme.scss`: `block-size: 2.5rem`, alt çizgi
  `--cds-border-strong-01`, köşe 0). Tek akışkan çift `asistan/SesOnayi.tsx`'teki `Modal`'ın kendi 50/50 altbilgisi.
- **TEDY kuralı / sapma.** [§5](tedy-ui-ux-talimatnamesi.md#5-kalıplar) form. Akışkan stil yalnız Carbon'un modal
  altbilgisinde kalır; sayfadaki hiçbir form akışkana geçmez: Işık'ın yüzeyi productive ve öngörülebilir (S16'nın
  productive tabanı; Carbon'un kendi "karmaşık formda kullanma" kuralıyla uyumlu).
- **Test.** Grep: `dashboard/src` içinde `Fluid[A-Z]` importu 0.
- **Kaynak.** https://carbondesignsystem.com/building-blocks/core/patterns/fluid-styles/

<a id="forms"></a>

### 2.9 Formlar (`forms`)

- **Ne için.** Kullanıcının veri girdiği ya da seçenek yapılandırdığı ilişkili girdi denetimleri grubu.
- **Carbon kuralları.**
  - Yalnız gerekeni sor; ilişkili alanları bölüm başlığıyla grupla; mantıklı sıra; tek etkileşim biçimi; parola
    yöneticisi ve otomatik doldurmayı düşün; ek girdileri ancak ilgili olunca aç.
  - Etiketler: cümle düzeni; her girdinin etiketi var; **iki nokta yok**; **bir ila üç sözcük**; üste hizalı
    (Carbon'un tek düzeni). Zorunlu/isteğe bağlı: çoğunluk zorunluysa yalnız isteğe bağlılar "(optional)",
    çoğunluk isteğe bağlıysa yalnız zorunlular "(required)"; ürün boyunca tutarlı.
  - Yardım: tooltip "i" ikonuyla, temel bilgi tooltip'e konmaz; yardımcı metin alanın altında hep görünür, gerekli
    bilgi için doğru yer; placeholder kaybolur, kritik bilgi taşımaz, etiketin yerine geçmez, örnekler
    anonimleştirilir; iyi varsayılanlar (bugünün tarihi, algılanan ülke).
  - Denetim seçimi: radyo varsayılanı önceden seçili, boş seçenek "None"; radyo/onay kutusu grupları dikey; beşten
    çok seçenekte select listesi (combo box, multiselect). Sınırlı girdi denetimleri (number input, slider, date
    picker, time picker) doğrulama gerektirmez.
  - Düğmeler: ana eylem birincil, Cancel/Discard ikincil. Sayfa içi form: sola hizalı, birincil solda; çok adımlı
    form/sihirbaz: sağa hizalı, birincil sağda; diyalog/yan panel: tam genişlik, alta taşar. Düğmeler üste
    konmaz; "Back" ikincil düğmede eylem olmaz; "Submit" yerine göreve özgü fiil.
  - Hata: önce ne olduğunu, sonra ne yapılacağını söyle; satır içi; istemci doğrulaması alan odaktan çıkınca
    ("Password must be at least 16 characters."); sunucu hatası satır içi bildirim + alan hataları; ölçüt sağlanınca
    alan hatası kaybolur.
  - Düğme etkinliği: **kısa** formda birincil, gereksinimler sağlanana dek pasif; **uzun** formda pasif yapılmaz
    (hata ve düğme aynı anda görünmeyebilir); gönderimde çift gönderime karşı pasif.
  - Aralık: girdi yüksekliği **40 px**; ayrı sayfa formunda alanlar arası **32 px** (`$spacing-07`); kapsanmış
    formda **24 px** (`$spacing-06`) ya da **16 px** (`$spacing-05`); bölüm öncesi 24 px aralıkta **32 px**, 32 px
    aralıkta **40 px** (`$spacing-08`); son girdiden düğme grubuna **48 px** (`$spacing-09`). Form başlığı kap ya da
    diyalogda `$productive-heading-03`. Tek sütun; çok sütun yalnız mantıksal ilişkili 2–3 alan.
  - Varyant: ayrı sayfa (karmaşık/uzun), diyalog (**beşten az girdi**, akordeon/sekme yok), yan panel (**beşten çok
    girdi**). İlk zorunlu alan açılışta odak alır. `<form>` sarmalayıcısı, görünür etiket, sekmeyle gezinme.
  - Sayfada yok: satır içi düzenleme ve form içi ayraçlar için birleşik rehber; akordeon form rehberi olgun değil.
- **TEDY'de nerede.** Üç form: (a) `components/StudentProfile.tsx` özel ders — yerel `<label>`/`<select>`/`<input>`,
  Başlık Düzeni etiketler ("Öğretmen Adı"), görünür işaretsiz `required`, placeholder "Örn: Ayşe Yılmaz", gönder
  tertiary "Özel Ders Ekle" → "Ekleniyor..."; (b) `components/OdevOnayKarti.tsx` — `fieldset`+`legend`, Carbon
  `TextInput`/`TextArea`, tarih biçimi yalnız placeholder'da (`gg.aa.yyyy`), "Ders" ve "Başlık" boşken düğme
  **nedensiz** pasif, sunucu hatası kartın altında `<p role="alert">`; (c) `components/AlistirmaKarti.tsx` — `<form>`,
  `RadioButtonGroup legendText="Cevabın"`. `invalid`/`invalidText` kullanımı 0; "(isteğe bağlı)" işareti 0.
- **TEDY kuralı / sapma.** [§5](tedy-ui-ux-talimatnamesi.md#5-kalıplar) form. Etiketler cümle düzeninde, iki
  noktasız; azınlık işaretlenir (TEDY formları kısa, çoğunluk zorunlu → "(isteğe bağlı)"); biçim yardımcı metinde.
  Doğrulama alanın kendisinde (`invalid` + `invalidText`); kısa formda birincil pasifse nedeni yanında yazılı (D3 —
  Carbon'un pasif-düğme kuralının TEDY biçimi) ya da düğme etkin kalır ve gönderimde eksik alan `invalidText` alıp
  odağı çeker. "İlk zorunlu alan odak alır" yalnız diyalogda ve sayfanın tek işi olan formda: sayfa açılınca pencere
  kaydırılmaz (`tasarim-denetimi.spec.ts`, İ5). Profil'deki gönder düğmesinin tertiary olması İ1'dir (sayfanın tek
  işi kimlik kartı). Özel ders formunun yerel denetimleri B60, OdevOnayKarti'nın nedensiz pasif düğmesi B56.
- **Test.** Var: `tests/e2e/profil.spec.ts`, `tests/e2e/photo-homework.spec.ts`. Önerilen: Ders alanını boşalt →
  "Ödevlere ekle" → `aria-invalid=true`, alan hata metni görünür, ağ isteği yok, odak o alanda; grep: `labelText`
  değerlerinde iki nokta yok, ≤ 3 sözcük; `components/` altında ham `input`/`select` (`type=file` hariç) 0.
- **Kaynak.** https://carbondesignsystem.com/building-blocks/core/patterns/forms/

<a id="global-header"></a>

### 2.10 Genel başlık (`global-header`)

- **Ne için.** UI Shell ile ürün içi ve ürünler arası gezinme; tutarlı bir yön duygusu.
- **Carbon kuralları.**
  - Anatomi: ana menü ikonu (sol paneli açar); başlık adı (**yalnız ve her zaman alanın ana sayfasına bağlanır**);
    başlık bağlantıları (yeni sekme ya da başka alan açmaz, dar ekranda yan menüye düşer); alt menü (tıklamayla
    açılır, etiket bağlantı değildir); yardımcılar ("Utility icons should not be used to directly navigate to an
    area. Instead, they should open a panel"); değiştirici (switcher).
  - Kalıcılık × görev matrisi: genel × sistem (giriş, bildirimler, profil, ürün değiştirme), genel × ürün (yerel
    gezinmeyi açan hamburger), yerel × sistem (ayrıntılı ayarlar), yerel × ürün (belgede yorum).
  - Yapılandırma: yalnız başlık (az ana bölüm) ya da başlık + sol panel (daha çok öğe, ek hiyerarşi düzeyi, alt
    menüler içeriği örtmeden açık kalır). Sistem bağlantıları sağa, ürün bağlantıları sola yaslı.
  - İyi pratik: sayfa durumu korunur ya da geri yüklenir, kaybolacaksa söylenir, gerekli durum URL'de; başlık yer
    duygusu verir (giriş yapan hesap, girilen kip); derine inen sayfada breadcrumb başlığın üstünde; sınırsız
    (kullanıcı üretimi) içerik yan gezinmeye konmaz.
  - Erişilebilirlik: DOM sırası = görsel sıra (dar ekranda gezinmenin taşınması meşru istisna); başlık görünümü
    rütbesine uyar; gezinmenin ilk odaklanabilir öğesi **"Skip to main content"** (SC 2.4.1); landmark'lar
    (navigation, main, form, banner, search); **birden çok navigation landmark'ının her biri benzersiz etiket**.
  - Sayfada px değeri yok (özellikler görseldedir).
- **TEDY'de nerede.** `components/DashboardHeader.tsx`: `HeaderName href="/"` + logo, kimlik bloğu, senkron durumu
  tetiği (panel açar, `aria-haspopup="dialog"`), odak anahtarı, "Yenile", "Çıkış"; başlık bağlantısı yok. Gezinme
  `App.tsx` `SideNav aria-label="Navigasyon"` (beş birincil + "Daha fazla" `SideNavMenu`); telefonda (< 672 px)
  `components/BottomNav.tsx` `aria-label="Ana gezinme"` + `components/DahaFazla.tsx`. `SkipToContent` 0. Çıkış fiili
  "Çıkış" (başlık) ↔ "Çıkış yap" (`components/ReaderChrome.tsx`). Derinlik 1: modül sayfasında tek ghost
  "Modüllere dön" (breadcrumb gereksiz).
- **TEDY kuralı / sapma.** [§5](tedy-ui-ux-talimatnamesi.md#5-kalıplar) kabuk ve gezinme. Tek 60rem sütun S1;
  `Content` dolgusu ve telefon üst boşluğu S8; dokunma hedefi ≥ 44 px S18 (B8). Telefonda Carbon'un hamburger +
  örtülü sol paneli yerine alt gezinme: kullanıcı kararı 2026-10-02 (D3a, İ1: iki dokunuş + on iki öğe taraması
  yerine tek dokunuş); korunan güvenceler etiketli landmark, `aria-current`, görünür etiket, %200 yakınlaştırmada
  içerik örtülmez. Başlık yer ve kip duygusu verir (odak kipi, senkron durumu, giriş yapan kişi); yardımcılar panel
  açar. Öğretmen kipi bantta değil sohbet panelinde (bant `.ac` dışında, hiç değişmez). Eksikler: SkipToContent ve
  `scroll-padding` B11; iki gezinme landmark'ının aynı gezinmeye iki ad vermesi ("Navigasyon" / "Ana gezinme") ve
  "Çıkış/Çıkış yap" İ9 — B40, B41; İngilizce erişilebilir adlar B44 (B15 kapandı).
- **Test.** Var: `tests/e2e/alt-gezinme.spec.ts` (telefonda alt çubuk, menü düğmesi yok, çubuk sayfa sonunu
  örtmez, odak kipinde dört sekme), `tests/e2e/d3b-dokunma.spec.ts` (≥ 44 px), `tests/e2e/tasarim-denetimi.spec.ts`
  (eşit sütun, telefon üst boşluğu), `tests/e2e/aria-yapisi.spec.ts`, `tests/e2e/ibm-erisilebilirlik.spec.ts`.
  Önerilen: ilk `Tab` "Ana içeriğe geç"i odaklar, `Enter` odağı `main`'e taşır.
- **Kaynak.** https://carbondesignsystem.com/building-blocks/core/patterns/global-header/

<a id="kalip-loading"></a>

### 2.11 Yükleniyor (`loading`)

- **Ne için.** Bilginin işlenmesi zaman aldığında isteğin sürdüğünü güvenceye almak; algılanan süreyi kısaltmak.
- **Carbon kuralları.**
  - **İskelet (skeleton)**: ilk sayfa yüklemesinde bileşenin sadeleştirilmiş hâli; "only a few seconds"; donmadığını
    söylemek için **hareket** kullanır. Yalnız kap tabanlı (karo, structured list) ya da veri tabanlı (data table,
    kart) bileşende. Eylem bileşenleri (düğme, girdi, onay kutusu, toggle) çoğu durumda iskelet almaz. **Asla**
    iskeletle gösterilmez: toast, overflow menu, dropdown öğesi, modal, yükleyici (modalın içindeki öğeler alabilir).
  - **Yükleme göstergesi**: ilerleme bildirmez; "more than a moment or two" sürecekse ilerleme göstergesi. Tam ekran
    (`Loading`) yalnız bütün uygulama işlerken ya da kullanıcı verisi kaydedilirken; birkaç dakikadan uzunsa bildirim
    ekle. Satır içi (`InlineLoading`) tek bileşen işlerken.
  - **Aşamalı yükleme**: önce yapı (kap iskeletleri), veri metni iskelet metin olarak ve veri dışı metin; sonra
    görseller, görüş alanı dışı içerik, eylem bileşenleri. Her öğe iskelet istemez; boş alan yer tutabilir (600 ×
    600 px görsel → 600 × 600 px boşluk). "Load more": listenin küçük bir kısmı gösteriliyorsa.
  - Erişilebilirlik: ekran okuyucu yükleniyor, meşgul, takıldı ve **başarısız** durumlarından haberdar edilir.
  - Sayfada sayısal eşik yok ("a few seconds", "a moment or two", "a few minutes").
- **TEDY'de nerede.** İskelet kart ve listelerde: `components/CalendarEvents.tsx`, `components/WeeklySchedule.tsx`,
  `components/PlatformProgress.tsx`, `components/Modules.tsx`, `components/ModuleViewer.tsx`,
  `components/AssistantChat.tsx`. Eylem bileşeninde iskelet: `components/DashboardHeader.tsx:146` senkron
  düğmesinin içinde `<SkeletonText width="72px" />` (px literal). Tam ekran `Loading` yok; `InlineLoading` tek
  eylemde: `components/HomeworkTracker.tsx:511` "Kaydediliyor", `components/AssistantChat.tsx:271` düşünme aşaması;
  aynı anda tek (`markingKey`). Ekran okuyucu: `aria-busy`, `role="status"` "Asistan yükleniyor…"; yükleme
  **hatası** rolsüz `<p>` ("Öğrenme günlüğü alınamadı.", `components/PlatformProgress.tsx`). Bugün'ün iskeleti
  stilsiz `.today-loading__bar` (B5). `hooks/useApi.ts` yüklemeyi gecikmesiz başlatır.
- **TEDY kuralı / sapma.** [§5](tedy-ui-ux-talimatnamesi.md#5-kalıplar) yükleniyor. Kapsama göre seçim: ilk
  yüklemede bölgenin şeklinde Carbon iskeleti; tek eylem sürerken düğmenin yerinde `InlineLoading` (biter → sonuç
  metni, hata → satır içi uyarı); tam ekran yükleme kullanılmaz; aynı anda en çok bir eylem yükleniyor gösterir
  (Carbon'un satır içi yükleme kuralı = İ6'nın tek hareketli öğesi; bir bölgenin iskeletleri tek hareket sayılır ve
  `InlineLoading` ile yan yana koşmaz). Bu ayrım 2026-10-10'da karara bağlandı (S36): yüzey tasarımları §2.4'ün
  "Dönen ikon yok" cümlesi içerik yüklemesine daraltıldı. "400 ms'den kısaysa hiçbir şey gösterilmez" cümlesi hâlâ
  kodla çelişir — B48: ya `useApi`'de gecikmeli iskelet ya cümle düzeltilir (eşik Carbon'da yok, TEDY'nin kendi
  kararıdır). `NextThing`'in metin değiştiren kaydı B69. Yükleme hatası `role="alert"` taşır
  (D3) — B43. "Load more" yalnız geçmişte; aktif liste hep tam (İ7). B5 Bugün iskeleti.
- **Test.** Var: `tests/e2e/gorunum-kipleri.spec.ts` (azaltılmış harekette hiçbir şey canlanmaz). Önerilen:
  `/api/homework` 1 sn geciktir → bölge şekilli `.cds--skeleton`; ilk "Yaptım" askıdayken ikinci "Yaptım" → sayfada
  `.cds--inline-loading` en çok 1; AST: `@carbon/react` `Loading` importu 0.
- **Kaynak.** https://carbondesignsystem.com/building-blocks/core/patterns/loading/

<a id="login"></a>

### 2.12 Giriş (`login`)

- **Ne için.** Kullanıcı kimliğiyle uygulamaya erişim.
- **Carbon kuralları.**
  - Anatomi: başlık (**"Log in"** sözcükleri, "Sign in" değil); hesap oluştur (isteğe bağlı); zorunlu alanlar
    (kimlik, sonra aşamalı açılan parola); unuttum bağlantısı; kimliği hatırla (neyin hatırlandığını söyler); alternatif
    girişler (sırayla); birincil **Continue**; yardım; arka plan görseli (isteğe bağlı).
  - Hareketsizlikten çıkıştan sonra yeniden girişte **son sayfaya dönülür**; gönüllü çıkışta onay mesajı ve girişe
    yönlendirme.
  - Hata: ekranda, satır içi; istemci doğrulaması odak çıkışında; sunucu hatasında parola temizlenir, odak kimlik
    alanına, satır içi bildirim, hatalar yığılır, yanlış kimlik ve yanlış parola için **aynı genel mesaj**.
  - Düzen: birincil düğme metin girdisine en yakın; alternatif düğmeler girdi ile birincil arasına ya da formun
    üstüne konmaz. Ortalı düzen: düz renk ya da marka dokusu, karmaşık illüstrasyon yok. Bölünmüş ekran: pazarlama ve
    giriş içeriği ayrık (test: kullanıcılar giriş bölgesi dışına bakmıyor). Üçüncü taraf logoları markanın
    kurallarıyla.
  - Erişilebilirlik: form sekmeyle gezilebilir; **giriş bölgesi için landmark**. Sayfada tek sayı: "Remember ID"
    yoksa onun 24 px üst boşluğu kaldırılır; diğer aralıklar görseldedir. MFA için rehber yok.
- **TEDY'de nerede.** `components/LoginPage.tsx`: bölünmüş ekran — hero yalnız logo, okul adı, alt başlık; panelde
  Google'ın kendi `renderButton`'ı (`text: 'signin_with'`, `locale: 'tr'` → "Google ile oturum açın"); `h1` "Hoş
  geldiniz", metin "giriş yapın". Hata `InlineNotification kind="error" lowContrast hideCloseButton title="Hata"`,
  yedek metin "Giriş başarısız" (sonraki adım yok); sunucu dizeleri `src/dashboard_api.py`'den doğrudan (İngilizce /
  diakritiksiz olanlar dahil). Sayfa yalnız `div` — `<main>` ya da etiketli bölge yok.
- **TEDY kuralı / sapma.** [§5](tedy-ui-ux-talimatnamesi.md#5-kalıplar) bildirim ve hata + talimatname §3.9 içerik.
  Tek fiil (İ9; Carbon'un "Log in" kuralının özü): ekranda "giriş yap" ile Google'ın "oturum aç"ı yan yana, başlıkta
  "Çıkış" — fiil sözlüğü §3.9'da. Hata başlığı olmayan şeyi, alt metin yapılacak şeyi söyler ("Bu hesapla giriş
  yapılamıyor. Ailenin yetkili hesabıyla dene."); makine metni ekrana çıkmaz (D4). Giriş bölgesi landmark'ı B40,
  hata metinleri B43. Google düğmesinin markası Google'ın kurallarıyla (Carbon'un üçüncü taraf kuralı).
- **Test.** Önerilen: giriş sayfasında `main` (ya da etiketli `region`) landmark'ı var; `/api/auth/login` hata
  gövdeleri Türkçe ve diakritikli ("giris", "yapilamaz" yok); oturum düşünce yeniden girişte son sayfaya dönüş
  (doğrulanmadı — test eklenecek).
- **Kaynak.** https://carbondesignsystem.com/building-blocks/core/patterns/login/

<a id="notifications"></a>

### 2.13 Bildirimler (`notifications`)

- **Ne için.** Kullanıcıyla iletişim ve geri bildirim; ilkeler: ilgili, zamanında, bilgilendirici. Çok sık ya da
  bölücü bildirim kullanıcıyı uzaklaştırır.
- **Carbon kuralları.**
  - Bildirim = **durum** (amaç) + **tür** (ne kadar bölücü). Görev kaynaklı (kullanıcı eylemine yanıt, çalıştığı
    bölgede) ↔ sistem kaynaklı (arka plan, bağlam dışı).
  - Durum → renk → ikon:

    | Durum | Kullanım | Renk | İkon |
    |---|---|---|---|
    | Informational | Ek bilgi, göreve bağlı olmayabilir | Mavi | `information filled` |
    | Success | Görev beklendiği gibi bitti | Yeşil | `checkmark filled` |
    | Warning | İstenmeyen ya da beklenmedik sonuçlu eylem | Sarı | `warning filled` |
    | Error | Hata ya da kritik arıza; çözülene dek engelleyebilir | Kırmızı | `error filled` |

  - Tür → süre/etkileşim:

    | Tür | Kullanım | Süre / etkileşim |
    |---|---|---|
    | Inline | Bölücü olmayan geri bildirim, eylem durumu | Çözülene ya da kapatılana dek; ghost düğme eylemi olabilir |
    | Toast | Kayarak girip çıkan kısa, zamanlı mesaj | Eylemsizse kendiliğinden ya da kullanıcı kapatır; eylemliyse kapatılana dek |
    | Actionable | Inline ya da toast biçiminde etkileşimli öğe | Eylem alınana ya da kapatılana dek |
    | Callout | Sayfa içeriğinde bağlamsal önemli bilgi | Tetiklenmez; sayfayla yüklenir; kalıcı; **kapatılamaz** |
    | Banner | Sistem/ürün düzeyi, göreve özgü değil | Kapatılana dek; ghost düğme ya da bağlantı olabilir |
    | Notification panel | Sistem mesajları merkezi | Kullanıcı açar, kapatır |
    | Modal | Çok bölücü; kritik bilgi | Kapatılana dek görevi durdurur |

  - Inline: ilgili öğenin yanında, formda üstte ya da altta, **iki satırın altında**, içeriği örtmez. Toast: sağ üst,
    yığında en yeni üstte, sabit genişlik, **en çok üç satır**; otomatik kapanma süresi sayfada yok. Actionable:
    tetiklenince odak alır; inline biçimde **tek ghost düğme**, toast biçiminde **tek tertiary düğme**; eylem etiketi
    **en çok iki sözcük**; okunması kritikse kapatma düğmesi konmaz. Callout: başarı/hata durumu yok, eylemin
    yanına, sayfada az. Banner: ana başlığın hemen altında, **yapışkan değil, içerikle kayar**, **aynı anda tek
    banner**; Carbon'da banner ve notification panel bileşeni henüz yok.
  - Öncelik: yüksek kontrast acil/kritik, düşük kontrast destekleyici; bir varyasyon içinde stiller karışmaz.
  - Erişilebilirlik: kritik mesaj zamanlayıcıyla kapanmaz (WCAG 2.2.4, AAA); kritik olmayan bildirimler
    yönetilebilir/sınırlanabilir olmalı (WCAG 2.2.3, AAA).
- **TEDY'de nerede.** Toast ve Actionable yok (grep 0); zamanla kapanan bildirim yok. Sekiz `InlineNotification`
  sitesinin hepsi `lowContrast`: `components/PlatformProgress.tsx`, `components/LoginPage.tsx`,
  `components/ModuleViewer.tsx`, `components/PortalStatusBanner.tsx`, `components/Modules.tsx`,
  `asistan/GirisUyarisi.tsx`. Okunması gereken mesajda `hideCloseButton` (giriş, modül hataları, "okunamadı" bandı).
  `components/PortalStatusBanner.tsx`: içerik sütununun başında, içerikle kayar, sütun genişliğinde (Carbon'un 46rem
  tavanı açılmış), "sunmuyor" (`kind="info"`) ve "okunamadı" (`kind="warning"`) `/dersler`'de birlikte görünebilir;
  sayfayla gelen, kapatılamayan "okunamadı" Carbon tanımıyla bir Callout'tur. `components/RouteBoundary.tsx`:
  `role="alert"` + tek "Yeniden dene" (actionable kuralına uygun). Odak kipi uyarı sayısını ve portal bandını gizler.
  `components/PlatformProgress.tsx` `kind="success"` "Tüm platformlar tamamlandı!" — eylemsiz, ünlemli.
- **TEDY kuralı / sapma.** [§5](tedy-ui-ux-talimatnamesi.md#5-kalıplar) bildirim ve hata. Tür seçimi: kendi
  eyleminin sonucu → `InlineNotification` eylemin yanında; sayfayla gelen ve kendiliğinden geçecek durum → Callout
  (kapatma yok); Toast kullanılmaz (kendiliğinden kaybolan bilgi Işık için kaybolan bilgidir, İ5); Actionable
  kullanılmaz (odağı hapseder, İ6). Bütün bildirimler düşük kontrast: bilinçli sapma (S27), ekranda tek dikkat çekici renk
  alanı eylem gerektiren şeyde kalır (İ6) — "düzeltilmez". Birden çok durum aynı bölgede tek
  bildirime birleşir, tür en yüksek dikkat (Carbon'un birleşik durum kuralı) — `/dersler`'deki çift bant B62.
  Tamamlanma düz metindir, ünlemsiz (anayasa §9 "Tamamlanma sessizce ve net"). B6 Bugün API hataları sessiz.
- **Test.** Var: `tests/e2e/okunamadi.spec.ts` (birden çok okunamayan bölüm birlikte adlandırılır), `tests/e2e/portal-status.spec.ts`,
  `tests/e2e/sinav-ve-hata.spec.ts` ("Yaptım kaydedilemezse satır bunu söyler"). Önerilen: grep
  `ToastNotification|ActionableNotification` = 0; fixture `unavailable` + `okunamadi` birlikte → içerik sütununda
  bildirim sayısı 1, türü warning.
- **Kaynak.** https://carbondesignsystem.com/building-blocks/core/patterns/notifications/

<a id="overflow-content"></a>

### 2.14 Taşan içerik (`overflow-content`)

- **Ne için.** Kabını aşan metin ve büyük miktarda içerik.
- **Carbon kuralları.**
  - Kısaltma (truncation) statik metin ve bağlantı içindir; üç nokta **üç ya da daha çok** kesilmiş karakteri temsil
    eder. Uygun: breadcrumb, pagination, uzun URL, paragraf (açıklama), uzun öğe adı. **Asla kesilmez**: sayfa
    başlığı, başlık, etiket, hata mesajı, doğrulama mesajı, bildirim.

    | Tür | Amaç | Örnek |
    |---|---|---|
    | Front-line | Metin önceki bir yerden sürüyor | `...56789` |
    | Mid-line | Ortası ortak ya da sonu kesilemez | `1234...56789876...4321` |
    | End-line | Devamı başka yerde; uzun dize | `12345...` |

  - Tek başına üç nokta yoğunlaştırılmış içeriği temsil edebilir; o zaman tarayıcı tooltip'i değil **hover'da
    overflow menu** gerekir.
  - Kod: `.cds--text-truncate--front`, `.cds--text-truncate--end`; tarayıcı tooltip'i için `title`; kabın genişliği
    ayarlı olmalı; mid-line JavaScript ister.
  - **"Show more"**: kaydırma, gradyan ya da solma yerine; isteğe bağlı "Show less"; başarım için "Load more".
- **TEDY'de nerede.** Üç nokta = taşma menüsü: "Daha fazla" `SideNavMenu` (`OverflowMenuHorizontal`, `App.tsx`),
  "Daha fazla" alt sekmesi ve `components/DahaFazla.tsx`. Kesme siteleri (`ted-theme.scss`): kullanıcı adı/e-posta,
  `.calendar-event__title` (`title=` var), `.platform-detail-row__title` (`title=` **yok**),
  `.schedule-lesson`/`.schedule-detail` (`title=` var), `.reader__bar-chapter` (okuyucu çubuğunda bölüm başlığı,
  tooltip yok). Başlık, etiket, hata, bildirim kesilmiyor. Yatay kaydırma tablolar ve formüller için, yalnız taştığında
  odaklanabilir bölge: `components/Kaydirilabilir.tsx`. Carbon AI Chat kod parçası "Daha fazla göster / Daha az göster"
  (`asistan/dilPaketi.ts`).
- **TEDY kuralı / sapma.** [§5](tedy-ui-ux-talimatnamesi.md#5-kalıplar) taşan içerik. Gradyan/solma zaten yasak
  (D1, renk aritmetiği yok); katlama yalnız geçmişte, aktif liste hep tam (İ7 — Carbon'un "show more"u işi
  saklayamaz). Kesilen her öğe adı `title` taşır; başlık kesilmez — `.platform-detail-row__title` ve
  `.reader__bar-chapter` B35 (okuyucu Books dünyasıdır, kendi kararıyla).
- **Test.** Var: `tests/e2e/takvim.spec.ts` (uzun etkinlik başlığı günü genişletmez). Önerilen: `text-overflow:
  ellipsis` taşıyan her sınıfın DOM öğesinde `title` niteliği (birim/AST).
- **Kaynak.** https://carbondesignsystem.com/building-blocks/core/patterns/overflow-content/

<a id="read-only-states"></a>

### 2.15 Salt okunur durumlar (`read-only-states`)

- **Ne için.** Kullanıcının etkinken değiştirebileceği bir bileşenin, verisi süreçlere katılmaya devam ederken
  yalnız okunur olması.
- **Carbon kuralları.**
  - Kullanım: uygulama süreci (süreç bitene dek), kilit (eşzamanlı düzenleme), izin (görme var, değiştirme yok).
    Kullanılmaz: etkin durumu olmayan bileşen (düz bilgi); devre dışının yerine (kullanıcı eylemi bekleyen bileşen
    **disabled**dır); disabled bir bileşen read-only'ye çevrilmez.
  - Anatomi: zemin saydam; kenarlık rengi değişir; **metin rengi değişmez** (≥ 4.5:1); gömülü ikon rengi değişir
    (`$icon-disabled`), imleç.
  - Etkin durumla aynı yapı ve aralık; etkileşimli öğeler kaldırılır ya da değiştirilir; varsayılan stil alanlar
    katman zeminine karışır, akışkan alanlar etkin zeminini korur.
  - **Okunması gereken bileşende disabled kullanılmaz**: ekran okuyucu okumaz, kontrastı geçmez. Salt okunur
    görünümde disabled olan disabled kalır.
  - Etkileşim: fare **ok imleci**; klavye ile **gezilebilir** ama değiştirilemez (disabled'a ulaşılamaz). İçerik
    etkinle aynı; yönlendirici metin bilgilendiriciye dönebilir.
- **TEDY'de nerede.** Aile Işık'ın sohbetini salt okunur açınca okunacak içerik `disabled`:
  `components/AlistirmaKarti.tsx:41` (`kapali = saltOkunur || …` → şıklar ve cevap alanı),
  `components/OdevOnayKarti.tsx:46` (`fieldset disabled={bekliyor || saltOkunur}`),
  `components/NetlestirmeSecenekleri.tsx`, `asistan/OzelYanitlar.tsx`; eski arayüzde `components/AssistantChat.tsx`.
  `readOnly` prop'u panoda 0. İyi örnekler: Carbon AI Chat `isReadonly` (`asistan/tedyChatConfig.ts`), girdi satırı
  düğmeleri salt okunurda **kaldırılır** (`asistan/GirisDugmeleri.tsx`), "Bu sohbet salt okunur." cümlesi
  (`asistan/GirisEkleri.tsx`), mikrofon gizlenir (asistan B5 ses planı). Hızlı öneriler yalnız pasif (`asistan/Karsilama.tsx`).
- **TEDY kuralı / sapma.** [§5](tedy-ui-ux-talimatnamesi.md#5-kalıplar) salt okunur / devre dışı. Carbon ve D2
  burada aynı şeyi söyler, repo aykırıdır: okunacak içerik (seçenekler, Işık'ın cevabı, önerilen ödevler) `readOnly`
  ya da düz metin; hiç yapılamayacak eylem (Gönder, Ödevlere ekle, mikrofon) gizlenir; `disabled` yalnız geçici
  durumda (yanıt beklenirken) — B42. Modül şablonunda öğrencinin kendi doğru cevabını soluklaştıran ve sekme
  sırasından düşüren `disabled` aynı borcun modül tarafıdır.
- **Test.** Var: `tests/e2e/carbon-asistan-sohbet.spec.ts` ("family section is read only"),
  `tests/e2e/carbon-asistan-ses.spec.ts` (aile dikte edemez). Önerilen: `?kisi=ogrenci` fixture'ında alıştırma,
  netleştirme ve ödev onay kartlarında `[disabled]` 0; Işık'ın seçtiği şık `getByText` ile bulunur; axe
  `color-contrast` 0.
- **Kaynak.** https://carbondesignsystem.com/building-blocks/core/patterns/read-only-states/

<a id="kalip-search"></a>

### 2.16 Arama (`search`)

- **Ne için.** Anahtar sözcükle keşif; geniş başlar, süzgeçle daralır.
- **Carbon kuralları.**
  - Anatomi: kapsam süzgeci (isteğe bağlı), büyüteç ikonu, kısa ve yararlı placeholder ("Search for networks or
    devices."), metin alanı. Genel aramanın yeri genel başlık kalıbında, tablo içi arama data table bileşenindedir.
  - Türler (taramada kaybolan tablo ayrıca kurtarıldı):

    | Tür | Ne zaman | Kullanım |
    |---|---|---|
    | Basic | Ayrı sonuç sayfasına yönlenecekse | Genel arama; arama pahalı, yavaş ya da bilgi tanıdık değilse; kullanıcı çalıştırana dek sorgu yok |
    | Active | Küçük veri (tek sayfa, site, tablo); sürekli geri bildirim yararlı ve sunucu taşıyabiliyor | Her karakterde sonuç alanın hemen altında; alan + ikon + temizleyen **X**; **Search/Go düğmesi yok** |
    | Focused | Etkin kullanıcıya özgü görev ve bilgi | Atanmış görevler, kişisel depolar; kapsamı genişletme seçeneği altta |

  - Pratik: çıkmaz yok (sonuç yoksa öneri ve kaynak; boş durum kalıbı); bir iki andan uzun aramada yükleme göstergesi,
    ağır aramada ilerleme çubuğu; **sonuç sayısı her zaman, sıfır dahil**; **etiket konmaz** (ikon + placeholder
    yeter); kapsam süzgeci tek kategori, "All/Any" varsayılan.
  - Erişilebilirlik: `Tab` girdiye, `Enter` çalıştırır; öneride ok tuşları, `Enter` seçer, `Esc` seçmeden çıkar;
    yönlü süzmede içerik yeniden yüklenirken odak korunur.
- **TEDY'de nerede.** Panoda arama alanı yok (`Search`, `ExpandableSearch`, `TableToolbarSearch` 0). Asistanın
  `kitap_ara`/`modul_ara` sunucu araçlarıdır, alan değil; Carbon AI Chat'in "Arama sonuçları" etiketi
  (`asistan/dilPaketi.ts`) tek arama sözcüğüdür.
- **TEDY kuralı / sapma.** Uygulanmıyor. Bir arama alanı eklenecekse: active search, etiketsiz, özgül placeholder,
  sonuç sayısı sıfır dahil hep görünür, `Esc` temizler, "sonuç yok" `EmptyLine`'ın kullanıcı-eylemi türüdür ve bir
  sonraki adımı söyler (D3). Görünür etiket kuralıyla (D2) çelişirse etiket `hideLabel` ile erişilebilir ad olarak
  kalır.
- **Test.** Yok (yüzey yok).
- **Kaynak.** https://carbondesignsystem.com/building-blocks/core/patterns/search/

<a id="status-indicators"></a>

### 2.17 Durum göstergeleri (`status-indicators`)

- **Ne için.** Bir nesnenin ya da sistemin durumunu simge, şekil, renk ve metinle göstermek.
- **Carbon kuralları.**
  - Varyantlar:

    | Varyant | Kullanım | Örnek yerler |
    |---|---|---|
    | Icon indicator | Bol alan, en yüksek dikkat; ikon + şekil + anlamlı renk + betimleyici etiket | Bildirimler, ilerleme, data table, görev listesi |
    | Shape indicator | Dar alan ya da çok veri taraması; şekil + renk + etiket, simge yok | Listeler, panolar, data table, veri görselleştirme |
    | Badge (sayılı) | Yeni öğe sayısı önemliyse; **en çok üç hane, sonuncusu "+"**; yalnız başlıktaki 48 px ikon düğmede | Başlık bildirim bölmesi |
    | Badge (noktalı) | Sayı bilinmiyor ya da önemsiz | Araç çubuğu ikon düğmeleri |
    | Differential | Büyük istatistik listelerinde değişim; **"+"/"−", şapka ya da ok zorunlu** | Finans panoları |

  - Görsel öğeler: simge, şekil, renk, yazı — "For WCAG compliance, at least three of these elements must be
    present" (aynı sayfanın erişilebilirlik bölümü "renk, şekil, simgeden en az ikisi + metin" der; ikisi de sayfada).
    Durum renkleri arasında ve gösterge ile zemin arasında **en az 3:1**; gri tonlamada ayırt edilebilir kalır.
  - Durum renk paleti (açık tema, sayfadaki değerler; kodda hex yazılmaz, token kullanılır):

    | Ad | Hex | Anlam |
    |---|---|---|
    | Red 60 | `#da1e28` | Tehlike ya da hata |
    | Green 50 | `#24a148` | Normal ya da başarı |
    | Orange 40 | `#ff832b` | Ciddi uyarı |
    | Orange 60 (dış çizgi) | `#ba4e00` | Turuncu şekillerin dış çizgisi |
    | Yellow 30 | `#f1c21b` | Olağan uyarı |
    | Yellow 60 (dış çizgi) | `#8e6a00` | Sarı şekillerin dış çizgisi |
    | Blue 70 | `#0043ce` | Pasif bildirim, ek bilgi, iş akışı ilerlemesi |
    | Purple 60 | `#8a3ffc` | Aykırı ya da tanımsız durum |
    | Gray 60 | `#6f6f6f` | Taslak ya da başlamamış iş |

    Genişletilmiş sarı/turuncu paletleri yalnız ek kontrast için, yalnız veri görselleştirme ve bazı durum
    göstergelerinde.
  - İkon–yazı eşleşmesi:

    | Varyant | İkon | Yazı |
    |---|---|---|
    | Icon indicator | 20 px | 16 pt |
    | Icon indicator | 16 px | 14 pt |
    | Shape indicator | 16 px | 14 pt |
    | Shape indicator | 16 px | 12 pt |

  - Seçim: birden çok durum birleşince grup **en yüksek dikkat rengini** alır (yeşil + sarı + kırmızı → kırmızı);
    eylem gerekmiyorsa ya da durum önemsizse gösterge değil **düz metin**; beş altıdan çok gösterge bunaltır.
    Önem düzeyleri (ürün tanımlar): yüksek (hemen eylem: hata, yıkıcı eylem), orta (onay, ilerleme), düşük (hazır,
    değişti). Simgeler yalnız Carbon ikon kütüphanesinden ve en tanınmışlardan (ünlem = uyarı, onay = başarı).
  - Hizalama: ikonlar metinle **sola hizalı**; sağa yaslı göstergede iki haneli etiket ikonları kaydırır (yapma).
    Şekil göstergesi etiketten **önce**. Aynı şekil farklı renklerle tek deneyimde kullanılmaz. İkon göstergesi dış
    çizgi almaz; şekil göstergesi (özellikle açık temada sarı/turuncu) dış çizgi ve metin etiketi ister.
- **TEDY'de nerede.**
  - Ödev durum Tag'i: ikon (`CheckmarkFilled`/`CloseFilled`) etiketten önce (`components/HomeworkTracker.tsx`); ama
    durum sözlüğü `utils/formatters.ts:110` "Bekliyor" → `blue`, `HomeworkTracker.tsx:446,558` "YAPILAN" → `blue`,
    `components/TeamActivities.tsx:99` `blue`/`teal` — ders ailesi (blue, teal) durum Tag'inde; tasarım testi yalnız
    JSX literalini yakalıyor.
  - Geri sayım Tag'leri yalnız renkle ayrışır (aynı biçim, aynı `Timer` simgesi; `utils/countdown.ts`); metin ("3 saat
    kaldı") ve sıralama aciliyeti renksiz de taşır.
  - Senkron popover'ı (`components/DashboardHeader.tsx`): ok → `CheckmarkFilled`, uyarı → `WarningFilled`, hata →
    `ErrorFilled`, sunulmuyor → `WarningFilled` + `--cds-support-caution-undefined` (mor = tanımsız), atlandı →
    `SkipForwardFilled` + `text-helper` (gri = başlamamış) — Carbon'un palet anlamlarıyla aynı. Ama ikon, uzunluğu
    değişen sayıdan **sonra**, sağa yaslı sütunda (Carbon'un "yapma"sı). İkonlar 14 px; Tag içinde 12 px (Carbon'un
    en küçüğü 16 px).
  - Başlıktaki senkron Tag'i: yalnız senkron başarısızsa kırmızı; uyarılar gri sayı ("15 dk önce · 4 uyarı").
  - Notlar durum rengiyle boyanıyor: `utils/formatters.ts:115` `gradeColor` (85+ success, 70+ info, 50+ warning,
    altı error) → `components/GradeTable.tsx`, `components/ExamTimeline.tsx`.
  - Rozet ve fark göstergesi yok.
- **TEDY kuralı / sapma.** [§5](tedy-ui-ux-talimatnamesi.md#5-kalıplar) durum göstergesi; S4: mevcut metinli durum
  Tag'leri kalır (gri tonlama testini geçer), **yeni** durum göstergeleri ikon + metin (+ renk) taşır;
  `preview__IconIndicator` kararlı olunca yeniden değerlendirilir (preview API'ye bağlanılmaz). Durum Tag'lerinin ikonsuz
  olması B16. Kırmızı/sarı/yeşil/turuncu anlam renkleridir, ders rengi olmaz; mavi ve mor TEDY'de ders ailesidir
  (İ8, kullanıcı kararı 2026-10-02) — "bekliyor/sürüyor" gri aile + simgeyle gösterilir; ders ailesi taşıyan durum
  Tag'leri ve testin çalışma anında hesaplanan Tag türünü kaçırması B21 (B13 ile ilişkili). Sistem arızasının şiddeti
  Carbon'un durum anlamıyladır: başarısız ve ilerlenemiyor hata, kısmi/bayat uyarı, bilgilendirici bilgi; gri yalnız
  başlamamış/taslak (S39, 2026-10-10). Başlıkta uyarı sayısının gri kalması bilinçli sapmaydı (S23: sürekli "4 uyarı"
  sarısı hiç çözülmeyen bir alarmdır, İ6); S39 ile gerilimi ve asistanın gri "Yedek modelden" rozeti S45 ile kapandı: kısmi/bayat
  durum uyarı ikonu + metin taşır (borç B75). Not renklendirilmez, nötr metindir (S42, 2026-10-10); bugünkü `gradeColor` bantları B72. Rozet yok ve öyle kalır (İ6, odak kipi).
  Eylem gerektirmeyen bilgi rozet değil düz metindir (yüzey tasarımları §2.7).
- **Test.** Var: `tests/test_pano_tasarim_sistemi.py` (ders ailesi Tag'de yok — yalnız literal),
  `tests/test_ders_renkleri.py`, `tests/e2e/kontrast.spec.ts` (not bantları AA), `tests/e2e/sinav-ve-hata.spec.ts`
  ("sınav listesi sessiz: renkli etiket ve ders rengi yok"). Önerilen: `test_ders_rengi_etiket_olmaz` dize-literal
  taramasına çevrilir (bugün `formatters.ts:110`, `HomeworkTracker.tsx:446/558`, `TeamActivities.tsx:99` düşer); durum
  sözlüğünden gelen her yeni Tag `renderIcon` taşır.
- **Kaynak.** https://carbondesignsystem.com/building-blocks/core/patterns/status-indicators/

<a id="text-toolbar"></a>

### 2.18 Metin araç çubuğu (`text-toolbar`)

- **Ne için.** Metin düzenlemek için yatay düğme ve menü grubu; biçim altındaki metin alanına uygulanır.
- **Carbon kuralları.** Anatomi: eylemler (geri al/yinele, kes/kopyala/yapıştır), biçim (yazı tipi, boyut, stil, renk),
  paragraf (hizalama, girinti, listeler), ek (dosya, bağlantı), arama (anahtar sözcük — "not currently available for
  production use"), metin alanı. Ek dosya metin alanının sol altında yüklenir, `x` ile kaldırılır; arama sonuç sayısı
  bir Tag'de. Dar alanda denetimler taşma menüsüne. Kaydetme: kaydet/gönder; taslak düğmeyle ya da otomatik.
  Erişilebilirlik: eylem düğmeleri hover ve odakta tooltip; `Tab`/`Shift+Tab` çubuğa girip çıkar, ilk girişte ilk
  etkin denetim odak alır; `Sol/Sağ ok` denetimler arası; `Yukarı/Aşağı ok` menüde; `toolbar` rolü sekme duraklarını
  azaltır. Sayfada boyut ya da token yok.
- **TEDY'de nerede.** Zengin metin düzenleme yok. Sohbet girdi satırındaki ikon düğmeler (mikrofon, plan, durdur —
  `asistan/GirisDugmeleri.tsx`) `label` tooltip'i taşır; `role="toolbar"` ve ok tuşu gezinmesi yok.
- **TEDY kuralı / sapma.** Uygulanmıyor. İki üç denetimde `Tab` doğrudur; ok tuşu işlenmeden `role="toolbar"`
  eklemek yanlış olur. Zengin düzenleyici gelirse bu kalıp ve WAI-ARIA toolbar uygulaması birlikte gelir.
- **Test.** Yok (yüzey yok).
- **Kaynak.** https://carbondesignsystem.com/building-blocks/core/patterns/text-toolbar/

## 3. Temel sayfalar dizini

Carbon'un temel (foundations) ve veri görselleştirme sayfaları; kuralların kendisi talimatnamededir, burada yalnız
kaynak ile uygulayan bölüm eşleşir. Alt sayfalar ana sayfanın altındaki yollardır (2026-10-10 taraması).

| Sayfa | Alt sayfalar | URL | Talimatname |
|---|---|---|---|
| 2x Grid | overview · guidelines · code | https://carbondesignsystem.com/building-blocks/foundations/2x-grid/overview/ | §3.4 (S1 tek sütun) |
| Spacing | overview · code | https://carbondesignsystem.com/building-blocks/foundations/spacing/overview/ | §3.4 (S8, S18) |
| Themes | overview · code | https://carbondesignsystem.com/building-blocks/foundations/themes/overview/ | §3.1 (S7, S14); derinlik §3.5 (S11) |
| Typography | overview · type-sets · style-strategies · code | https://carbondesignsystem.com/building-blocks/foundations/typography/overview/ | §3.3 (S2, S9, S16) |
| Color | overview · guidelines · tokens · code | https://carbondesignsystem.com/building-blocks/foundations/color/overview/ | §3.2 (S17 hover) |
| Motion | overview · choreography · code | https://carbondesignsystem.com/building-blocks/foundations/motion/overview/ | §3.6 |
| Icons | library · guidelines · code | https://carbondesignsystem.com/building-blocks/foundations/icons/library/ | §3.7 |
| Pictograms | library · guidelines · code | https://carbondesignsystem.com/building-blocks/foundations/pictograms/library/ | §3.7 |
| Accessibility | overview · color · keyboard · developers | https://carbondesignsystem.com/building-blocks/foundations/accessibility/overview/ | §3.8 (S18) |
| Content | — | https://carbondesignsystem.com/building-blocks/foundations/content/ | §3.9 |
| Carbon for AI | — (eski yol `/guidelines/carbon-for-ai/` aynı içerik) | https://carbondesignsystem.com/building-blocks/foundations/carbon-for-ai/ | §6 (S13) |
| Veri görselleştirme — Overview | — | https://carbondesignsystem.com/building-blocks/data-visualization/overview/ | §8 |
| Chart anatomy | — | https://carbondesignsystem.com/building-blocks/data-visualization/chart-anatomy/ | §8 |
| Axes and labels | — | https://carbondesignsystem.com/building-blocks/data-visualization/axes-and-labels/ | §8 |
| Legends | — | https://carbondesignsystem.com/building-blocks/data-visualization/legends/ | §8 |
| Color palettes | — | https://carbondesignsystem.com/building-blocks/data-visualization/color-palettes/ | §8 (B9 Gün Şeridi kontrastı) |
| Simple charts | — | https://carbondesignsystem.com/building-blocks/data-visualization/simple-charts/ | §8 |
| Spatial charts | — | https://carbondesignsystem.com/building-blocks/data-visualization/spatial-charts/ | §8 |
| Flow charts | — | https://carbondesignsystem.com/building-blocks/data-visualization/flow-charts/ | §8 |
| Gantt charts | — | https://carbondesignsystem.com/building-blocks/data-visualization/gantt-charts/ | §8 |
| Dashboards | — | https://carbondesignsystem.com/building-blocks/data-visualization/dashboards/ | §8 (S15 KPI karosu yok) |

Eski yollar (`/elements/...`, `/components/...`, `/data-visualization/...`, `/guidelines/...`) bayattır (B18, 2026-10-11'de kapandı);
bağlantı yalnız yukarıdaki `/building-blocks/...` biçimiyle verilir.

## 4. Kaynak ve tazelik

- **Tarama.** carbondesignsystem.com, 2026-10-10: site haritasından 307 sayfa Markdown'a çevrildi (bileşenler 171,
  deneyimler 36, başlangıç 31, temeller 30, kalıplar 18, veri görselleştirme 10, Carbon MCP 5, diğer 6). Crawl'da
  `[TABLE]` olarak kaybolan tablolar (ör. boş durum türleri, arama türleri) ayrıca kurtarıldı; kurtarılamayan
  değerler kartlarda "sayfada yok" diye yazılıdır. Sayfalar üçüncü taraf içeriğidir ve veri olarak okundu.
- **Nokta denetimi.** Tek bir kuralı doğrulamak için Carbon MCP `docs_search` (rehber, kullanım, erişilebilirlik,
  içerik) ve `code_search` (prop, varyant, ikon); dönen `anchor_url` kaynak olarak yazılır. Çalışma biçimi
  talimatname §10'dadır. MCP dizininde olmayan içerik (ör. boş durum görsel boyutları, Numbers içerik sayfası) "Carbon
  MCP'de bulunamadı" diye yazılır, tahmin edilmez.
- **Yeniden tarama.** `https://www.carbondesignsystem.com/sitemap.xml` bir site haritası dizinidir (`pages-`,
  `articles-`, `tutorials-`, `building-blocks-` … `-sitemap.xml`); alt haritalardaki URL'ler yeniden çekilir; sayfa sayısı, başlık ve tablo satırı sayısı önceki dizinle
  karşılaştırılır; değişen sayfanın kartı yeniden okunur. Carbon'un sürümü (`@carbon/react`, `@carbon/ai-chat`)
  yükseltildiğinde ya da bu ek bir yıldan eski olduğunda yeniden tarama yapılır; S13 onarımları her `@carbon/ai-chat`
  yükseltmesinde IBM testiyle yeniden denetlenir.
- **Bağlılık.** Bu rehber [talimatnameye](tedy-ui-ux-talimatnamesi.md) bağlıdır (öncelik sırası 5. basamak):
  değişmezler, ilkeler, talimatname ve yüzey tasarımları kartlardaki her Carbon kuralını yener. Bir kart talimatnameyle
  çelişirse kart düzeltilir; bir Carbon kuralı benimsenecekse önce talimatnameye (gerekirse §11'e sapma) yazılır.
