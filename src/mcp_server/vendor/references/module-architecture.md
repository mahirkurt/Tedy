# Modül Mimarisi ve `MODULE_DATA` Şeması

> Bir `carbon-edupedia` modülü, `assets/module-template.html` içindeki **etkileşim
> motoru** (engine) + üstteki **`MODULE_DATA` veri nesnesi**nden oluşur. İçeriği
> üretmek = `MODULE_DATA`'yı doldurmak. Motoru değiştirmeyin; veriyi yerleştirin.

## İçindekiler
1. Üst düzey anatomi
2. Tam `MODULE_DATA` şeması
3. Segment akışı kuralları
4. İskeleden doldurmaya — adım adım
5. Kalite öz-kontrol listesi

---

## 1. Üst düzey anatomi

```
modul.html
├── <head>: SHA-256 manifestli inline IBM Plex WOFF2, satır-içi Carbon CSS, reduced-motion
├── <body>
│   ├── SVG icon sprite (gizli, currentColor)
│   ├── Üst çubuk: modül başlığı + ilerleme rayı + araç düğmeleri (XP sayacı, seri, rozet yok — S43)
│   ├── #stage: aktif segment buraya render edilir (tek-odak)
│   └── Alt: yönlendirme (Geri / Devam), erişilebilirlik kontrolleri
└── <script>
    ├── const MODULE_DATA = { ... }   ← İÇERİK BURADA (sen doldurursun)
    └── engine: segment render, etkileşim mantığı, iç ilerleme (xp), sessiz özet  ← DEĞİŞMEZ
```

**Tek-odak ilkesi:** Aynı anda yalnız bir segment görünür (ped İlke 5, dış yük).
Üst çubuk yürütücü dışsallaştırmadır (ped İlke 4): nerede olduğum ve ne kadar
kaldığı görünür (tek aşama göstergesi, Kanun M2.4, M2.5); ödül göstergesi yoktur (M2.7).

## 2. Tam `MODULE_DATA` şeması

```js
const MODULE_DATA = {
  meta: {
    id: "fen7-hucre-organeller",          // opsiyonel kararlı kimlik; varsa Leitner anahtarına girer
    title: "Hücre ve Organeller",        // modül başlığı (TR)
    subject: "Fen Bilimleri",            // ders
    gradeLevel: "7. Sınıf",              // sınıf düzeyi
    mode: "MODULE",                      // MODULE|QUIZ|FLASHCARDS|GAME|EXPLAINER|ASSESSMENT|SERIES
    // accent yazılmaz: ders rengi subject'ten türetilir (Kanun M4.5)
    milestones: [                        // 3–7 aşama; aşama o segmentte başlar (Kanun M2.5)
      { atSegmentId: "t1", title: "Keşfet" }, { atSegmentId: "t2", title: "Uygula" }, /* … */
    ],                                   // title 1–2 sözcük, ≤ 16 karakter, cümle düzeni
    estimatedMinutes: 18,                // tahmini süre (üst çubukta gösterilir)
    coverPictogram: "pic-idea",          // kapak piktogramı (izinli anahtarlar Kanun §1 madde 6)
    sourceCitation: "MEB Fen 7, Ünite 1 / kullanıcı ders notu", // KAYNAK (SKILL.md §7)
    assets: [                            // edupedia_gorsel / edupedia_medya varlıkları (Kanun M3.1, M3.6–M3.8)
      { asset_id: "a1b2c3d4e5f60718", slot: "t1.visual",           // raster görsel: alt ve baslik zorunlu
        alt: "Kağnıların yanında yürüyen halk toprak bir yolda cepheye cephane taşıyor.", // 60–150, bitmiş cümle; süs: ""
        baslik: "Görsel 1.30: İstiklal Yolu yürüyüşü",            // görünür altyazı, kitaptaki adıyla, ≤ 120, sayfa yok
        alt_gerekce: "…" },                                        // isteğe bağlı, ≥ 20: kaynakta geçmeyen ad/sayının nedeni
      { asset_id: "0f1e2d3c4b5a6978", slot: "t1.audio" }           // ses: alt/baslik yazılmaz
    ]
  },

  learner: {                             // opsiyonel kişiselleştirme
    name: "",                            // boşsa nötr; "Işık" gibi verilebilir
    showTimer: false                     // süre sayacı varsayılan KAPALI (ped §3)
  },

  objectives: [                          // başta gösterilir: "Bu modülde…"
    "Hücrenin temel kısımlarını tanıyacaksın.",
    "Bitki ve hayvan hücresini ayırt edeceksin.",
    "Organellerin görevlerini eşleştireceksin."
  ],

  rewards: { xpPerCorrect: 10, firstTryBonus: 5 },  // isteğe bağlı iç sayı (0–1000), okur görmez; yazılmazsa
                                         // motor 10/5 kullanır. badges yazılmaz, şema hatası (Kanun M2.7)

  segments: [
    // 0) opsiyonel kanca (hook) — merak-boşluğu açar; hedeflediği teach render
    //    edilince AYNI akış içinde kapanır (Keşif Döngüsü, gamified-flows.md §2.1)
    { type: "hook", id: "h1", title: "Merak Anı", pictogram: "pic-idea",
      question: "Sence hücrenin enerji santrali hangisi?",
      predict: { options: ["Çekirdek", "Mitokondri", "Hücre zarı"] },  // opsiyonel, notsuz
      resolvesIn: "t1" },                       // zorunlu — aşağıdaki teach'in id'si

    // 1) öğretim
    { type: "teach", id: "t1", title: "Hücre nedir?", pictogram: "pic-idea",
      body: ["<p>...</p>", "<ul><li>...</li></ul>"],
      keyTerms: [{ term: "hücre", def: "canlının en küçük yapı birimi" }],
      visual: { kind: "svg", ref: "<svg ...>...</svg>" } },          // opsiyonel

    // 2) etkileşim (OTR — teach'ten sonra zorunlu)
    { type: "mcq", id: "q1", title: "Kısa Alıştırma", pictogram: "pic-rocket",
      instructions: "Doğru seçeneği işaretle.",
      questions: [
        { stem: "...", options: ["...","...","..."], correctIndex: 1,
          explanation: "...", sourceRef: "t1" }
      ] },

    // 3) öğretim
    { type: "teach", id: "t2", ... },

    // 4) mola (uzun modülde)
    { type: "brainbreak", id: "b1", title: "Kısa Mola", pictogram: "ic-pause",
      prompt: "30 saniye ayağa kalk, derin nefes al.", durationSec: 30 },

    // 5) eşleştirme
    { type: "match", id: "m1", title: "Organel Eşleştirme", pictogram: "pic-idea",
      mode: "text", pairs: [{ a: "Mitokondri", b: "enerji üretir" }, ...] },

    // 6) flashcard / fillblank / order / sorting / hotspot ... (interaction-patterns.md)

    // 7) soluk-çözümlü örnek (worked) — tam çözüm fadeFrom'dan itibaren boşalır,
    //    öğrenci son adım(lar)ı tamamlar (fading; en güçlü matematik alt-özelliği)
    { type: "worked", id: "w1", title: "Denklemi Çöz", pictogram: "pic-idea",
      instructions: "Önce çözülmüş adımları oku, sonra boş adımları doldur.",
      steps: [
        { text: "3x + 2 = 14" },                 // fadeFrom altı: salt-görünür (verilen)
        { text: "3x = 12" },
        { text: "x = ?", answer: ["4"] }          // fadeFrom ve üzeri: <input> ile boşluk
      ],
      fadeFrom: 2 },

    // 8) öz-açıklama (selfExplain) — düşük-baskı metakognisyon: öğrenci kendi
    //    açıklamasını serbestçe/notsuz yazar, sonra model açıklamayı kendi
    //    isteğiyle açar; ilerleme asla bloklanmaz (puanlama/XP/ceza YOK)
    { type: "selfExplain", id: "se1", title: "Neden Böyle?", pictogram: "pic-idea",
      prompt: "3x + 2 = 14 denkleminde neden önce 2'yi çıkarıyoruz? Kendi cümlelerinle açıkla.",
      modelExplanation: "<p>Denklemi çözmek için x'i yalnız bırakmalıyız; bu yüzden önce her iki taraftan da 2 çıkarılır.</p>" },

    // 9) parametrik simülasyon (sim) — sanal manipülatif: 1-2 kaydırıcı canlı bir
    //    SVG'yi yeniden çizer. simType motor-içi SABİT bir preset kütüphanesini
    //    (SIM_PRESETS) seçer — MODULE_DATA asla render kodu taşımaz (Task 17,
    //    gamified-flows.md §5.3.1). Keşfedici/puanlanmaz.
    { type: "sim", id: "s1", title: "Sarkaç Uzunluğu", pictogram: "pic-idea",
      instructions: "Kaydırıcıyı hareket ettir ve sarkacın nasıl değiştiğini gözlemle.",
      simType: "pendulum",                      // pendulum|projectile|wave|numberScale|functionPlot
      params: [
        { key: "length", label: "Uzunluk (m)", min: 0.2, max: 2.2, step: 0.1, default: 1 },
        { key: "angle",  label: "Açı (derece)", min: -60, max: 60,  step: 5,   default: 20 }
      ] },

    // 10) kavram haritası (conceptMap) — düğümleri bağlayarak ilişki kur, hedef
    //     yapıyla sırasız karşılaştır (v3.0.0 — Task 18). Klavye yolu ZORUNLU
    //     ve TEKTİR (sürükle-bırak bu sürümde hiç eklenmedi).
    { type: "conceptMap", id: "cm1", title: "Hücre İlişkileri", pictogram: "pic-idea",
      instructions: "Bir düğüm seç, sonra bağlamak istediğin ikinci düğümü seç.",
      nodes: [
        { id: "n1", label: "Mitokondri" }, { id: "n2", label: "Enerji üretir" },
        { id: "n3", label: "Çekirdek" }, { id: "n4", label: "Yönetir" }
      ],
      targetEdges: [ ["n1","n2"], ["n3","n4"] ] },

    // son) kontrol noktası (karma geri-getirme, ped İlke 8)
    { type: "checkpoint", id: "c1", title: "Kontrol Noktası", pictogram: "pic-growth",
      recap: ["...", "..."],
      mixedQuestions: [ /* mcq şeması */ ],
      selfAssess: ["Bunu öğrendim", "Tekrar etmeliyim"] }
  ]
};
```

**Şema notları:**
- `meta.id` opsiyoneldir; varsa Leitner kalıcı anahtarı hem bu kimliği hem başlık
  hashini içerir. Yoksa geriye uyum için yalnız başlık hashinden türetilir.
- `meta.sourceCitation` **zorunlu** (kaynak izlenebilirliği). Kaynak yoksa
  SKILL.md §7'ye göre işaretle.
- `mcq` sorularında `sourceRef` doğrulanabilirlik kancası (validate_module.py).
- `body` sade HTML; `<script>`/satır-içi olay yok (motor olayları bağlar).
- `visual.ref` ya bir sprite anahtarı (`"pic-idea"`) ya satır-içi `<svg>` (yalnız
  `var(--cds-*)`/`var(--viz-*)` renkli). Kitap figürü ve fotoğraf `meta.assets` ile
  `<teachId>.visual` yuvasına bağlanır (Kanun M3.1). Raster görselin iki alanı zorunludur:
  `alt` (60–150 karakterlik bitmiş cümle; "Bu fotoğraf/çizim/şema" ile başlamaz; süs görseli
  `""`) ve `baslik` (figure + görünür figcaption; kitaptaki adıyla, en çok 120 karakter, tek
  satır, sayfa numarası yok; her varlıkta ayrı). Alt metindeki özel ad ve sayılar figürün
  açıklamasında (`edupedia_gorsel` → `kaynak_verisi.varlik.aciklama`, `etiket`) ya da çerçeve
  sayfalarında geçer; geçmiyorsa `edupedia_derle` `alt_metin_dayanaksiz` döner, nedeni
  `alt_gerekce`'ye yazılınca uyarıyla derler. Atıf satırını derleyici `baslik — atıf` olarak
  yazar (M3.6–M3.8). Ses yuvası bu alanları almaz.
- Piktogram anahtarları yalnız Kanun §1 madde 6'dakilerdir; `ic-*` piktogram yerine
  yazılmaz, ödül ikonu kullanılmaz (M3.10). `meta.quest` yazılmaz (M2.6).
- `hook` **opsiyoneldir** (yalnız Keşif Döngüsü kullanan modüllerde). Alanlar:
  `id`, `title?`, `question` (zorunlu), `predict?:{options:[...]}` (opsiyonel,
  notsuz ön-tahmin), `resolvesIn` (**zorunlu** — aynı `segments[]` içindeki bir
  `teach`'in `id`'si). `resolvesIn` hedeflediği `teach` render edilince motor
  kancayı **aynı akış içinde** kapatır (`data-hook-resolved`); açık bırakılan
  bir kanca `validate_module.py`'nin **G-FLOW** kapısında FAIL üretir — her
  `hook` mutlaka var olan bir `id`'yi hedeflemeli. Şema/mekanik ayrıntısı:
  `interaction-patterns.md` + `gamified-flows.md` §2.1/§3.1.
- `worked` (soluk-çözümlü örnek / fading worked example) **opsiyoneldir**. Alanlar:
  `id`, `title?`, `instructions?`, `steps:[{text, answer?}]` (zorunlu dizi),
  `fadeFrom:int` (zorunlu — bu indeksten itibaren adımlar boşluk). `fadeFrom`
  **altındaki** adımlar salt-görünür verilen çözüm satırlarıdır (`answer` gerekmez);
  `fadeFrom` ve **üzerindeki** adımlarda motor bir `<input aria-label>` boşluğu
  render eder ve `answer` (dizi veya tekil string, `norm()` ile karşılaştırılır)
  zorunludur — eksikse o adım hiçbir girdiyle eşleşmez (sessiz-yanlış değil,
  güvenli varsayılan). Tek "Kontrol et" düğmesi `fadeFrom`+ adımların tamamını
  birlikte değerlendirir (renderFillblank'in doğru-işareti deseni: token renk +
  ikon + `aria-invalid`); yanlış girdi **tekrar denenebilir** (kilitlenmez, ceza
  yok — G-WELLBEING); tümü doğru olunca `addXP`+ustalık+ilerleme açılır. En yüksek
  kanıt ağırlıklı alt-özellik (matematik g=0.48 — Barbieri 2023); şema/motor
  ayrıntısı: `renderWorked` (module-template.html).
- `selfExplain` (öz-açıklama / self-explanation prompt) **opsiyoneldir**. Alanlar:
  `id`, `title?`, `prompt` (zorunlu — öğrenciye yöneltilen açıklama istemi),
  `modelExplanation` (zorunlu — güvenli HTML/metin, karşılaştırma için model
  açıklama; `worked`'in `steps[].text`i gibi yazar-güvenilir işlenir, kaçışsız
  yerleştirilir). Motor bir serbest `<textarea aria-label>` sunar (**opsiyonel,
  notsuz, karakter zorunluluğu yok**) ve bir "Modeli gör"/"Modeli gizle" aç/kapa
  düğmesi (`aria-expanded`, klavye-erişilebilir gerçek `<button>`) ile
  `modelExplanation`'ı açar/kapatır. **Puanlama/XP/ceza YOK** — `setNav` next'i
  render'da **koşulsuz** etkin bırakır; öğrenci taslak yazsa da yazmasa da,
  modeli açsa da açmasa da "Devam" her zaman etkindir (G-WELLBEING — düşük-baskı
  metakognisyon; ne "eksik"/"yanlış" uyarısı ne de gizli bir gating vardır).
  Çözümlü-örnek ailesinin 2. en güçlü alt-özelliği (bkz. yukarıdaki `worked`
  notu — Barbieri 2023 çözümlü-örnek alt-özellik sıralaması); şema/motor
  ayrıntısı: `renderSelfExplain` (module-template.html).
- `mcq.questions[]` ve `fillblank.items[]` **opsiyonel** bir `tier?: 1|2|3` alanı
  taşıyabilir (1=kolay taban, 3=zor; yoksa/geçersizse 1 varsayılır —
  mevcut tier'sız modüllerde davranış **birebir korunur**). Görünmez taban-
  korumalı uyarlanır zorluk (v3.0.0 — Task 13, gamified-flows.md §2.3/§3.3):
  `state.perf` yuvarlanan penceresi 2 ardışık yanlıştan-sonra-doğruda ipucu-önce
  + en-düşük-kalan-tier tercihini, 2 ardışık ilk-denemede-doğruda opsiyonel/
  atlanabilir bir zor soru (tier 3) davetini tetikler ("Daha zor bir soru"; okuru etiketlemez,
  yalnız seçeneği adlandırır; rekabet çerçevesi yok, Kanun M2.7); uyarlama yalnız
  segmentte gerçek tier'lı bir soru/öğe varsa etkindir ve kullanıcıya **hiçbir**
  görünür zorluk-etiketi yazılmaz (G-FLOW `FLOW_LABEL_RE`). Tam şema/motor
  ayrıntısı: `interaction-patterns.md` §2/§5 + `runQuestionSet`/`renderFillblank`
  (module-template.html).
- `sim` (parametrik simülasyon / sanal manipülatif, v3.0.0 — Task 17) **opsiyoneldir**.
  Alanlar: `id`, `title?`, `instructions?`, `simType` (zorunlu —
  `"pendulum"|"projectile"|"wave"|"numberScale"|"functionPlot"`),
  `params:[{key,min,max,step,default,label}]` (zorunlu dizi, 1-2 öğe önerilir),
  `labels?` (opsiyonel — yalnız `labels.title` SVG başlığını override eder).
  **Kod-güvenli tasarım kararı** (gamified-flows.md §5.3.1): `simType` motor-içi
  SABİT bir preset kütüphanesini (`SIM_PRESETS`) seçer — `MODULE_DATA` asla render
  fonksiyonu/kod taşımaz, yalnız hangi preset'in hangi parametrelerle çağrılacağını
  seçer (şema değişmezi: "motor olayları bağlar"). Motor her `params[]` öğesi için
  klavye-erişilebilir bir `input type="range" aria-label` (native — ok tuşları
  `step` kadar değiştirir, Home/End min/max'a atlar, ekstra kod gerekmez) + canlı
  `output aria-live="polite"` değer okuması render eder; her kaydırıcı `input`
  olayında (ve ilk çizimde) `SIM_PRESETS[simType](svgEl, values, labels)` çağrılır
  ve hedef svg öğesinin `innerHTML`'ini **tamamen** değiştirir — bu yüzden CSS
  transition/animasyon yoktur, yeniden çizim reduced-motion altında da üstünde de
  mimari olarak **anındadır** (eski düğümler yok edilip yenileri kuruluyor).
  **Bilinmeyen `simType`** → nazik/uydurmasız bir not ("Bu simülasyon için hazır
  şablon yok.") render edilir, kaydırıcı/SVG hiç kurulmaz — çökme yok. Segment
  **keşfedicidir/puanlanmaz** (`setNav` next hep etkin; `addXP`/`markMastered`/
  dokunuşu yok; `totalGradeable` paydasına katkısı yok — `selfExplain`
  ile aynı ilke). Beş başlangıç preset'i (tam katalog: `subject-packs.md` §2g):
  `pendulum` (uzunluk + opsiyonel açı → pivot+kol+top), `projectile` (hız+açı →
  yörünge yayı), `wave` (genlik+frekans → sinüs eğrisi), `numberScale` (değer →
  sayı doğrusunda işaretli nokta), `functionPlot` (eğim m + kesişim b → y=mx+b
  doğrusu). Yeni bir preset eklemek **motor genişletmesi**dir (yeni `SIM_PRESETS`
  dalı + G-SVG erişilebilirliği), `MODULE_DATA` yeteneği değil. Şema/motor
  ayrıntısı: `renderSim` + `SIM_PRESETS` (module-template.html).
- `conceptMap` (kavram haritası kurucu / concept-map builder, v3.0.0 — Task 18)
  **opsiyoneldir**. Alanlar: `id`, `title?`, `instructions?`, `nodes:[{id,label}]`
  (zorunlu dizi, **en az 2 düğüm**), `targetEdges:[[nodeIdA,nodeIdB],...]`
  (zorunlu dizi — **sırasız** karşılaştırılır: `[A,B]` ile `[B,A]` eşdeğerdir).
  **Klavye yolu ZORUNLUDUR ve bu sürümde TEKTİR** (WCAG 2.1 AA — sürükle-bırak
  hiç eklenmedi; eklenseydi bile yalnız opsiyonel bir zenginleştirme olabilirdi,
  asla tek yol olamazdı): her düğüm gerçek bir `<button aria-label>` —
  kaynak-düğüm seç (tıkla/Enter/Space), ardından **farklı** bir hedef-düğüm seç
  (tıkla/Enter/Space) → aralarında bir kenar kurulur; aynı düğüme ikinci kez
  basmak seçimi iptal eder. Kurulan kenarlar hem salt-görsel bir SVG çizgi
  katmanında (`aria-hidden` — dekoratif) hem de klavye-erişilebilir bir "kaldır"
  `<button aria-label>` taşıyan bir metin listesinde ("Bağlantılarım",
  gerçek erişilebilir kayıt) gösterilir. "Kontrol et" düğmesi kurulan kenarları
  `targetEdges`'e karşı sırasız karşılaştırır; doğru kenarlar yeşil+onay
  ikonuyla, hedef-dışı ("fazla") kenarlar nötr bilgi rengiyle işaretlenir,
  eksik hedef kenarlar nazikçe (cezasız — G-WELLBEING) listelenir; öğrenci
  listeden düzenleyip tekrar kontrol edebilir. **Tam eşleşince** (eksiksiz VE
  fazlasız) `addXP`+`markMastered` **tek seferde** tetiklenir (`worked`'in
  tüm-adım-birlikte deseniyle aynı ilke — `match`/`order`'ın kenar-başına
  ödülü DEĞİL); `totalGradeable` paydasına katkısı da `worked`'in
  fadeFrom-boş-korumasıyla birebir aynı ilke: gerçek bir `targetEdges` varsa
  +1, yoksa +0. En az 2 düğüm yoksa veya `targetEdges` boşsa → nazik/uydurmasız
  bir bilgi notu (`sim`'in bilinmeyen-`simType` dalıyla aynı desen), çökme yok.
  Kanıt temeli: kavram haritası/grafik düzenleyici meta-analizleri (Schroeder
  ve ark. 2018, g=0,58; oluşturma g=0,72; Nesbit & Adesope 2006) —
  `adhd-pedagogy.md` §"Sosyal" ve `subject-packs.md` §4. Şema/motor ayrıntısı:
  `renderConceptMap` (module-template.html); mekanik/erişilebilirlik ayrıntısı:
  `interaction-patterns.md` §13.
- `numberline` / `numberLine(spec)`'in `interactive?:true` genişlemesi (v3.0.0 —
  Task 19) **opsiyoneldir** ve **geriye-tam-uyumludur**: bayrak yoksa (mevcut
  tüm çağrılar) üretilen SVG **byte-için-byte** Task 19 öncesiyle aynıdır —
  `numberLine`'ın interactive üretimi (dıştaki svg'ye `data-nl-handle/-min/-max/
  -step` öznitelikleri + bir `<circle class="nl-handle">` + görünür bir
  `nl-readout` satırı) tamamen tek bir `if(spec.interactive){...}` bloğunun
  içindedir; blok dışında hiçbir koşulsuz katkı yoktur. `interactive:true`
  iken eklenen nokta gerçek bir `role="slider" tabindex="0"` taşır +
  `aria-valuemin`/`aria-valuemax`/`aria-valuenow`/`aria-label`; opsiyonel
  `value` (başlangıç değeri, yoksa min/max ortası `step`'e yuvarlanır) ve
  `interactiveLabel`/`label` (aria-label metni) alanları vardır. **Klavye
  ZORUNLU/BİRİNCİL yoldur** (`wireNumberlineInteractive`, stage.innerHTML
  atamasından SONRA bağlanır — sim/conceptMap ile aynı "motor olayları bağlar"
  deseni): `ArrowLeft`/`ArrowRight` (+`ArrowDown`/`ArrowUp`) `step` kadar,
  `Home`/`End` min/max'a atlar; pointer sürükle (`pointerdown/move/up`) YALNIZ
  isteğe bağlı bir zenginleştirmedir, WCAG 2.1 AA gereği asla tek yol olamaz
  (burada değil — klavye tam işlevsel). Her hareket hem `aria-valuenow`'u hem
  ayrı bir görünür `aria-live="polite"` okuma satırını (`nl-readout`) günceller
  — çift kanal (yalnız slider rolüne güvenmeyen AT'ler için de). `reduceMotion()`
  altında `handle.style.transition="none"` ile konum değişimi **anındadır**
  (CSS'te de `.nl-handle` geçişi yalnız `prefers-reduced-motion:no-preference`
  altında tanımlı — çift-katmanlı garanti). Şema/motor ayrıntısı: `numberLine`
  + `wireNumberlineInteractive` (module-template.html); mekanik/erişilebilirlik
  ayrıntısı: `interaction-patterns.md` §14; ders-paketi bağlamı:
  `subject-packs.md` §2b.

## 3. Segment akışı kuralları (motor + planlama)

1. **Parçalama:** Hiçbir `teach` ekranda 4–6 kısa birimi aşmaz (ped İlke 1).
2. **OTR:** İki `teach` arasında ≥1 etkileşim (ped İlke 2). Saf okuma zinciri yok.
3. **Erken başarı:** İlk etkileşim kolay; zorluk kademeli (ped İlke 6).
4. **Mola:** ≥6 segmentlik modülde ≥1 `brainbreak` (ped §4).
5. **Anında geri bildirim:** Her etkileşim sonrası anında, hareketsiz geri bildirim metni (ped İlke 3);
   XP yalnız iç ilerleme sayısıdır, ekranda gösterilmez (talimatname S43).
6. **Geri-getirme:** Modül `checkpoint` ile biter (ped İlke 8) — motor ayrıca
   otomatik, sessiz bir **özet** ekranı (tamamlanan alıştırma sayısı düz metinle, hedefler,
   öz-değerlendirme; büyük sayı ve rozet yok) üretir.
7. **Tek-odak:** Aynı anda tek segment (ped İlke 5).
8. **Aşamalar:** `meta.milestones` segmentleri 3–7 aşamaya gruplar; ilk öğe ilk segmenttedir
   (Kanun M2.5).
9. **Görsel:** Çerçeve ders kitabıysa teach segmentlerinin en az %60'ı görsel taşır; her
   modülde en az bir yazar görseli vardır, kitap figürü onun yerini almaz (Kanun M3.2, M3.5).

## 4. İskeleden doldurmaya — adım adım

1. Kaynağı **kazanımlara** ayır (her kazanım → bir öğretim segmenti).
2. Her kazanım için: `teach` yaz (kaynağa sadık **ama kitaba atıf etmeyen** nihai dil —
   SKILL.md §7; G-VOICE) → ardından uygun etkileşim seç (interaction-patterns.md) ve
   **kaynaktan** soru/çift/cevap üret (öğrenci "kitabı hatırlasın" değil, bu modülde öğrensin).
3. Akışı kur: teach→etkileşim→(mola)→teach→... → checkpoint.
4. `meta.subject`'e dersin resmî adını yaz; `meta.accent`, renk ve tema yazılmaz (Kanun
   M4.5). Piktogramları seç (izinli anahtarlar Kanun §1 madde 6); görselleri `edupedia_gorsel`
   ile getir ve en az bir yazar görseli çiz (M3.1, M3.5). Her raster görsele `meta.assets`'te
   `alt` ve `baslik` yaz; `kaynak_verisi.varlik.aciklama`'yı kopyalama, ondan kendi cümleni kur
   (M3.6, M3.7).
5. `MODULE_DATA`'yı şablona yerleştir; motoru değiştirme.
6. `validate_module.py` ile doğrula; ihlalleri gider.

## 5. Kalite öz-kontrol listesi (emisyon öncesi)

- [ ] Her `teach` kısa ve tek-kazanım; uzun olan bölünmüş (İlke 1).
- [ ] İki teach arası ≥1 etkileşim (İlke 2); saf okuma zinciri yok.
- [ ] Her `mcq` sorusunda `correctIndex` + `explanation` + `sourceRef` var.
- [ ] Quiz cevapları kaynaktan izlenebilir; kaynak-dışı olgu yok (SKILL.md §7).
- [ ] ≥6 segmentte ≥1 `brainbreak`; modül `checkpoint` ile biter.
- [ ] Aksan derse uygun; metin rengi daima `--cds-text-primary` (aksan değil).
- [ ] Görseller satır içi; emoji yok; durum çift-kanal (renk+ikon+metin).
- [ ] `meta.sourceCitation` dolu; süre varsayılan kapalı.
- [ ] Öğrenci yüzeyi nihai dil: kitaba/sayfaya/üniteye meta-atıf yok (SKILL.md §7; G-VOICE).
- [ ] Her raster görselde `alt` ve `baslik` var; alt metnin adları ve sayıları kaynakta geçiyor (M3.6–M3.8).
- [ ] Rekabet çerçevesi yok: "Yarışma", "Meydan oku" yazılmaz; `rewards.badges` ve `meta.quest` yok (M2.6, M2.7).
- [ ] Ton teşvik edici; ceza mekaniği yok (§3 etik).
