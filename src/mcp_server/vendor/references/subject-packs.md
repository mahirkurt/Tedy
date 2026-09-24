# Derse-Özel Frontend Güçleri (subject-packs.md)

Bir ders seçildiğinde `carbon-edupedia`, o derse uygun **görsel/etkileşim güçlerini** etkinleştirir.
Etkinleştirme `meta.subject` (veya `meta.subjectKey`) ile olur; motor bundan üç şey türetir:
(1) **ders renk ailesi** (`data-subject-family`), (2) alan (`data-subject-domain`), (3) dil/konu
anahtarı `data-subject` (derse-özel tipografi, sesli okuma dili).

## 1. Ders renk ailesi ve konu anahtarı
Renk, Tedy ders renk sisteminden gelir (tek kaynak `tedyLayer.subjectThemes`, kurallar
`tedy-integration.md` §3): ders adı katlanır ve alan tablosunda sözcük başı kökle aranır.

| Alan (`data-subject-domain`) | Aile (`data-subject-family`) | Tetikleyiciler (örnek) |
| --- | --- | --- |
| `yabanci-dil` | `blue` | İngilizce, Fransızca, Almanca, english, french |
| `dil` | `magenta` | Türkçe, Türk dili, edebiyat |
| `matematik` | `purple` | matematik, geometri, cebir, math |
| `fen` | `teal` | fen, fizik, kimya, biyoloji, science |
| `degerler` | `warm-gray` | din kültürü, ahlak, değerler, peygamber |
| `sosyal` | `cyan` | sosyal, tarih, inkılap, coğrafya, hayat bilgisi, yurttaşlık |
| `teknoloji` | `cool-gray` | bilişim, teknoloji, yazılım, kodlama |
| `sanat-spor` | `gray` | görsel sanatlar, müzik, beden eğitimi |
| `genel` (yedek) | `gray` | tanınmayan ad |

Sıra önemlidir: yabancı diller Türkçe'den, değerler sosyalden önce denetlenir ("Ahlak ve
Yurttaşlık" → değerler; "İnsan Hakları, Yurttaşlık ve Demokrasi" → sosyal). `meta.accent`
yalnız bir aile adıyla alanı ezebilir; en iyisi hiç yazmamak ve `meta.subject`'e dersin resmî
adını yazmaktır. Renk yalnız **odak çıpası / başlık / yapı** tonunu etkiler; butonlar
erişilebilirlik için Carbon mavisi kalır (bkz. `color-system.md`).

Konu anahtarı (`data-subject`: `math`, `science`, `religion`, `civics`, `history`, `geography`,
`social`, `turkish`, `french`, `english`) renkten bağımsızdır; derse-özel biçim (ör. matematikte
tablo rakamları) ve sesli okuma dili (Fransızca/İngilizce) onu kullanır.

## 2. Matematik paketi — sayı, sembol, geometri mükemmelliği
Motor üç araç sunar:

### a) `mathExpr(src)` — hafif, bağımlılıksız dizgi
`visual:{ kind:"math", expr:"…", caption:"…" }` ile blok denklem; gövde içinde
`<span class="math">…</span>` ile satır-içi. Desteklenen sözdizimi:
- **Üs/alt indis:** `x^2`, `x^{n+1}`, `a_1`, `a_{ij}` → x², xⁿ⁺¹, a₁, aᵢⱼ
- **Kesir:** `{a}/{b}` veya `\frac{a}{b}` → yığılı kesir (pay/payda çizgili)
- **Kök:** `sqrt(x)` veya `\sqrt{x}` → √ x (üst çizgili)
- **Operatör glifleri:** `*`→×, ` - `→− (gerçek eksi), `<=`/`>=`/`!=`→≤/≥/≠, `+/-`→±
- Tipografi: IBM Plex Serif + tabular/lining rakamlar (`.math`).
Örnek: `a^2 + b^2 = c^2`, `{3}/{4} + {1}/{4} = 1`, `c = sqrt(a^2 + b^2)`.

### b) `numberLine(spec)` — sayı doğrusu (SVG, tema-duyarlı, erişilebilir)
`visual:{ kind:"numberline", … }` veya `{ type:"numberline", numberline:{…} }`.
```
{ min:-3, max:5, step:1,
  points:[{value:2,label:"x",color?}],
  highlight:[0,2],            // aralık vurgusu (opsiyonel)
  title, desc, caption }
```
Ok uçlu eksen, etiketli işaretler, vurgulu aralık ve işaretli noktalar; rakamlar tabular.

**Etkileşimli mod (`interactive:true`, v3.0.0 — Task 19).** `numberline` segment
şeması opsiyonel bir `interactive:true` (+ opsiyonel `value`, `interactiveLabel`)
alanı taşıyabilir; bayrak verilirse eksenin üstüne gerçek `role="slider"
tabindex="0"` sürüklenebilir/klavye-adımlı bir nokta + görünür bir canlı okuma
satırı eklenir (`ArrowLeft`/`ArrowRight`/`Home`/`End` **zorunlu/birincil**
klavye yolu; pointer sürükle yalnız opsiyonel zenginleştirme). Bayrak
yoksa/`false` ise render **byte-için-byte** değişmez — tam mekanik/erişilebilirlik
ayrıntısı `interaction-patterns.md` §14, motor ayrıntısı `module-architecture.md`.

### c) Geometri SVG (özgün, kurallı)
`visual:{ kind:"svg", … }` ile `svg-authoring.md` kurallarına göre çiz:
- Dik açı için **kare işaret**, açı için yay; köşe etiketleri (A/B/C), kenar etiketleri (a/b/c).
- Renk: gövde `var(--accent-tint)` dolgu + `var(--accent)` kenar; yardımcı çizgiler `var(--viz-axis)`.
- Metin rengini CSS verir; `class="viz"`, `role="img"`, `<title>`/`<desc>` zorunlu.

### d) Değer tablosu
Doğrusal kural/fonksiyon için `table` segmenti veya `visual.kind:"table"` (Carbon DataTable);
sayısal sütunlar `numeric:true` ile sağa hizalı + tabular rakam; `highlightRows` ile vurgulanır.

### e) `fractionBar(spec)` — kesir/oran çubuğu (alan/uzunluk modeli, daire değil)
`visual.kind:"fraction"` (teach içinde) veya bağımsız `fraction` segmenti olarak çağrılır; SVG
**bar** modeli üç modda çizilir: `kind:"fraction"` ({num,den}) tek kesir; `kind:"sum"`
({addends:[],den}) paydaları eşit kesir toplamı (otomatik denklem, ör. 3/4 + 1/4 = 1);
`kind:"ratio"` ({ratio:[],labels?}) iki/çok çokluğun oranı (ör. 2:3, opsiyonel renkli gösterge).
Dolu hücreler aksan/`--viz-*`, boş hücreler `--cds-layer-01`; dış çerçeve `--cds-border-strong`;
denklem Plex Serif + tabular (`.fb-eq`). Erişilebilirlik: `role="img"` + `<title>`/`<desc>`
(G-SVG). Sadece token renk (ham-hex yok).

**Neden daire değil bar?** Orta-okul öğrencileriyle yapılan değerlendirmede öğrenciler kesirleri en
sık **dairesel** alan modeliyle gösterse de **bar (dikdörtgen) modelini en doğru** kullanmıştır;
yazarlar bar modelini kesir öğretiminde en verimli/etkili alan-modeli görseli olarak önermektedir
([Morano ve ark. 2020, NAEP kesir maddesinde görsel temsil kalitesi](https://consensus.app/papers/details/3ab1cebfe7bc5dfbb2f6b9b7c91dcdf3/)).
Bar modeli, Singapur "model yöntemi"nin çekirdeğidir ve Bruner'in *enactive–iconic–symbolic*
çerçevesinde **ikonik** aşamayı işgal ederek somut nesne ile soyut sembol arasında köprü kurar;
özellikle **parça-bütün** ve **karşılaştırma** (oran) yapılarını görselleştirmede ve "görsel
temsilleri karşılaştırma" stratejisinde etkilidir
([Poh 2025, dijital sınıflarda bar-model karşılaştırması](https://consensus.app/papers/details/b1e8157372cb55df94c22a92234beff6/)).
Temsil aşaması, kesir kavramı öğretiminde etkinliği gösterilen **somut-temsilî-soyut (CRA)** dizisinin
orta halkasıdır ([Flores ve ark. 2018, CRA dizisiyle kesir kavramları](https://consensus.app/papers/details/a445a7288bf1505b9f4fd64c1f6ec360/)).

**Dürüst denge / uyarı.** Tek bir yapısal görsel yeterli değildir: öğrenciler bölgesel modelleri
bölmede usta olsa da kesir alan-modeli dışı bağlamlara aktarımda zorlanabilir; çoklu gömme (multiple
embodiments) ve dikkatli öğretim şarttır
([Zhang ve ark. 2015, alan modellerinden çoklu gömmelere](https://consensus.app/papers/details/df6478ae96775a1fa6ccc3dde3faecf9/)).
Ayrıca **büyüklük (magnitude) ve bölme** kavramında **sayı doğrusu** alan modelinden nedensel olarak
daha güçlüdür ([Hamdan & Gunderson 2017, sayı doğrusu müdahalesi](https://consensus.app/papers/details/83cb1b1e45595702a135cb6da75ea866/);
[Sidney ve ark. 2019, kesir bölmesinde sayı doğrusu vs. alan modeli](https://consensus.app/papers/details/90b782c056fa509a98f53f2c0e2596fa/)).
Bu nedenle `fractionBar`, paketteki **`numberLine`** ile **rakip değil tamamlayıcıdır**: parça-bütün ve
oran için bar, büyüklük/sıralama ve bölme için sayı doğrusu. Sayı-doğrusu merkezli, öğrenme-bilimi
ilkeli bir müdahalenin altıncı sınıf matematik güçlüğü olan öğrencilerde **düşük dikkatin** olumsuz
etkisini tamponladığı da gösterilmiştir — yapılandırılmış kesir çalışmasının DEHB bağlamındaki değerini
destekleyen bir bulgu ([Barbieri ve ark. 2019, sayı doğrusu + bilişsel stratejiler](https://consensus.app/papers/details/9c1ca460656c5022bd3353f290e59439/)).

### f) Native MathML — `mathExpr` yetersiz kaldığında ileri notasyon (Task 16)
`mathExpr` (a) **varsayılan** dizgi motoru olarak kalır: üs/alt indis, kesir, kök ve
temel operatör glifleri için hafif/bağımlılıksız çözümdür ve çoğu K-12 modülü için
yeterlidir. **Yalnızca** `mathExpr`'in ifade edemediği ileri notasyonlarda — matris,
determinant, çok satırlı denklem sistemi, toplam/entegral (Σ/∫) gösterimi gibi —
tarayıcı-yerli **MathML** (`<math>…</math>`) escalation/tamamlayıcı olarak kullanılır.

**Nasıl kullanılır — iki yol:**
1. **Satır-içi (birincil, motor değişikliği gerekmez):** Motor `teach.body` dizisini
   ham (esc()'siz) HTML olarak `innerHTML`'e yazar (bkz. `interaction-patterns.md` §1
   "sade HTML" — yazar-güvenilir model). Bu yüzden `<math>…</math>` bir `body` dizesi
   içine doğrudan yazılabilir ve **hiçbir whitelist/sanitizer değişikliği olmadan**
   tarayıcıda render edilir:
   ```
   body: [ "<p>Kök formülü: <math><mrow><mi>x</mi><mo>=</mo>…</mrow></math></p>" ]
   ```
2. **Blok/başlıklı figür (isteğe bağlı yardımcı):** `visual:{ kind:"mathml", math:"<math>…</math>", caption:"…" }`
   → `mathmlFigure(mathml, caption)` bunu `svgFigure` ile aynı jenerik desende
   `<figure class="viz">…<figcaption>…</figcaption></figure>` olarak sarar (diğer
   `visual.kind` archetype'larıyla —`math`, `svg`, `labeled`— tutarlı bir çağrı biçimi).

**Sıfır payload / tarayıcı desteği.** MathML tarayıcı-yerlidir — harici kütüphane
(KaTeX/MathJax), font veya CDN **gerekmez**; `G-SELFCONTAINED` etkilenmez. Render
kalitesi tarayıcıya göre küçük farklar gösterebilir (bkz. `SKILL.md` §14 taban:
Chromium ≥120, Firefox ≥115, Safari ≥16 — MathML Core desteği bu tabanın altında
zaten mevcuttur); bu yüzden `mathExpr` varsayılan kalır, MathML yalnız onun
yetersiz kaldığı durumlarda tamamlayıcıdır. Ayrıntı: `content-enrichment.md` §2.3.

**Güvenlik disiplini (sanitizer YOK — yazar sorumluluğu).** `body` zaten ham/
sanitize-edilmeyen yazar-HTML'i olduğundan, MathML için ayrı bir whitelist
eklenmedi/eklenmemeli. Yazarlar MathML'de **yalnız yapısal etiketler** kullanmalı
(`mrow, mi, mo, mn, msup, msub, msubsup, mfrac, msqrt, mroot, mtable, mtr, mtd,
mtext, mspace, munder, mover, munderover`) — olay-tutucu (`on*`) veya `href`/
`xlink:href` **eklenmemelidir** (yeni bir XSS yüzeyi açmamak için).

### g) `sim` segmenti — parametrik simülasyon (sanal manipülatif, Task 17)
Yeni bir **segment tipi** (`{type:"sim", simType, params[], labels?}`) — 1-2
kaydırıcıyla canlı yeniden çizilen bir SVG "sanal manipülatif" (fizik/matematik
kavramını elle-oynayarak keşfetme). Tam şema: `module-architecture.md` §2 (`sim`
maddesi). **Kod-güvenli tasarım kararı:** `MODULE_DATA` yalnız `simType` (hangi
preset) + `params[]` (hangi değerler) taşır; render fonksiyonunun kendisi
`MODULE_DATA`'da **asla** yer almaz — motor-içi sabit bir preset kütüphanesi
(`SIM_PRESETS`) taşır ve `simType` ile seçilir (`content-enrichment.md`'nin
"entegre EDİLEMEZ" ilkesiyle aynı ruhta: keyfi kod/iframe yok, yalnız kürasyonlu/
sabit motor yeteneği).

Beş başlangıç preset'i:

| Preset | Parametre(ler) | Ne çizer |
| --- | --- | --- |
| `pendulum` | `length` (+ opsiyonel `angle`) | Pivot + kol + top (sarkacın seçilen konumdaki durağan hâli) |
| `projectile` | `speed`, `angle` | Klasik parabolik mermi yörüngesi (menzil/yükseklik çerçeveye otomatik ölçeklenir) |
| `wave` | `amplitude`, `frequency` | Sinüs eğrisi |
| `numberScale` | `value` | Sayı doğrusunda işaretli nokta (eksen değere göre otomatik genişler) |
| `functionPlot` | `m`, `b` | `y = mx + b` doğrusu, orijinden geçen eksenler |

Her preset yalnız token renk kullanır (`var(--accent)`, `var(--viz-axis)`,
`var(--viz-2)` — ham hex yok) ve tek bir `svg#simSvg role="img" aria-labelledby`
öğesinin `innerHTML`'ini tam değiştirir; bu yüzden yeniden çizim her zaman
anındadır (CSS transition yok — G-CARBON-GRID koreografi kontrolünü etkilemez).
**Bilinmeyen `simType`** → nazik "hazır şablon yok" notu (uydurma/çökme yok).
Yeni preset eklemek motor genişletmesidir, ders paketi/`MODULE_DATA` yeteneği
değil.

## 3. Fen Bilimleri paketi — etiketli şema, süreç, veri
Fen öğreniminde **etiketli, sadeleştirilmiş ve sinyallenmiş** görseller anlamayı ve aktarımı
artırır; yarar özellikle ön-bilgisi düşük öğrencilerde belirgindir (Mayer 1989, *J Educ Psychol*,
[etiketli illüstrasyon → açıklayıcı hatırlama + aktarım](https://consensus.app/papers/details/f528ed4c778c52e782b762d9fbc04de8/); Scheiter ve ark. 2015,
[metin-şekil karşılıklarını sinyalleme → bütünleştirme](https://consensus.app/papers/details/eb20830300ee5598af3582b2bcbf62f0/); Richter ve ark. 2016 meta-analiz,
[sinyalleme, renk-kodu dâhil; düşük ön-bilgide daha güçlü](https://consensus.app/papers/details/8b6a5cad1440525dac1d92a1508c2a1a/); Cromley ve ark. 2016, ortaokulda
[diyagram anlama öğretimi](https://consensus.app/papers/details/f97a595bc1fc55fe984e4b01ef141a6a/)). Uyarı: genç/İngilizce-öğrenen örneklemlerde yarar her zaman
yinelenmez ve "baştan çıkarıcı ayrıntı" riski vardır (McTigue 2009,
[çoklu-ortam ilkeleri ortaokula her zaman taşınmaz](https://consensus.app/papers/details/47027d625c045f028df58db35c6d875f/)) → **sade tut, parçaları VE
süreçleri etiketle, rehberlik ekle**.

- **`labeledFigure(spec)`** — numaralı çağrı-iğneli etiketli diyagram (hücre, bitki, devre,
  kuvvet okları). `visual:{ kind:"labeled", … }` veya `{ type:"diagram", diagram:{…} }`.
  ```
  { viewBox:"0 0 300 280",
    base:"<svg-inner: token renkli şekiller>",
    labels:[{n?,x,y,text}],     // numaralı iğne + sıralı açıklama listesi
    title, desc, caption }
  ```
  İğneler `var(--accent)`; numara `--cds-text-on-color`; açıklamalar figürün altında **okunur**
  sıralı liste (küçük SVG metni yerine). `role="img"` + `<title>`/`<desc>` zorunlu.
- **`relationFlow(spec)`** — süreç/enerji zinciri (örn. Güneş ışığı → Yaprak → Glikoz → Oksijen).
- **`vizChart` / `vizTable`** — deney verisi ve gözlem tabloları.
- **Formül:** `visual:{ kind:"math" }` + `mathExpr` kimyasal alt indis/üs için de çalışır
  (`H_2O` → H₂O, `CO_2` → CO₂).
- **`sim` segmenti** (`pendulum`/`projectile`/`wave` presetleri, §2g) — sarkaç,
  mermi hareketi, dalga gibi fizik kavramlarını elle-oynanabilir bir kaydırıcı +
  canlı SVG ile keşfettirir; tam katalog §2g ve `module-architecture.md` §2.

## 4. Sosyal Bilimler paketi — kavram/ilişki, kartlar, zaman çizelgesi
Sosyal bilgiler, **din kültürü ve ahlak bilgisi** ve **yurttaşlık/insan hakları** için ortak
güçler. Kavram haritaları ve grafik düzenleyiciler bu alanda güçlü, meta-analitik kanıta sahiptir
(Schroeder ve ark. 2018, g = 0.58; oluşturma g = 0.72,
[kavram haritası meta-analizi](https://consensus.app/papers/details/5b2e2d1f20b05887a0d28f8a2249010d/); Nesbit & Adesope 2006,
[düğüm-bağ diyagramları → kalıcılık](https://consensus.app/papers/details/be2bc5f0b65059f5843d1a9011102744/); Nair ve ark. 2017, tarihte
[başarı + ilgi artışı](https://consensus.app/papers/details/c38f5b11bdef52938e610618c08985c2/); Ilter 2016, sosyal bilgilerde
[kelime öğrenimi + olumlu başarı duyguları](https://consensus.app/papers/details/33e5210fee2b587cb4265eef06e41320/); Gallavan & Kellough 2007,
[yurttaşlık/coğrafya/tarih için sekiz grafik düzenleyici türü](https://consensus.app/papers/details/ed92c27501a15d00b42f95696c6d1e0d/); Wang ve ark. 2021,
[etkileşimli düzenleyiciler → daha derin işleme, ortaokul](https://consensus.app/papers/details/b27391ed611f5e18960604fb51917cf9/)).

- **`relationFlow(spec)`** — sebep-sonuç / kavram zinciri (örn. Kural → Düzen → Güven → Huzur).
  `{ steps:[{label,sub?}], caption }`; `visual.kind:"flow"` ya da `{ type:"flow", flow:{…} }`.
- **`infoCards(spec)`** — kavram/değer/hak kartları ızgarası (din kültüründe değerler, yurttaşlıkta
  haklar). `{ cards:[{icon?,term,desc}], columns?, caption }`; `cards` segmenti veya `visual.kind:"cards"`.
- **`timeline`** — olaylar/belgeler zaman çizelgesi (örn. hak belgeleri).
- **`vizTable`** — karşılaştırma (örn. haklar vs sorumluluklar); **harita-tipi** etiketli görsel
  için `labeledFigure` (coğrafya/tarih).

## 5. Dil Bilimleri paketi — Türkçe, İngilizce, Fransızca
Dilde **sistematik renk-kodu** ve **ikili kodlama** (görsel+sözel) öğrenmeyi hızlandırır:
renk-kodlama, dilbilgisel cinsiyet/yapı öğretiminde etkili ve düşük emekli bulunmuştur (Arzt ve ark.
2016, Almanca cinsiyet için [renk-kodu en etkili ve en az emek-yoğun](https://consensus.app/papers/details/a04fc7b48f1e5f71affe9955e4469946/); Kostiuk 2025 derleme,
[renk-kodlu kalıplar → %30–45 daha hızlı tanıma; sistematik tutarlılık şart](https://consensus.app/papers/details/548429910bc85764bf2d723497def7c4/); Aljehani 2022,
[İngilizce artikel/niceleyicide renk-kodu](https://consensus.app/papers/details/a0f23b85682e5a4d97694640ae249b18/)); ikili kodlama ise sözcük edinimi ve
kalıcılığı destekler (Wong ve ark. 2019, [iki-dilli öğrenende sözel+görsel](https://consensus.app/papers/details/8e8c8927628f5ee9b1eb2c50a2b274b7/); Li ve ark. 2019,
[piktografik-sözel kodlama → kalıcılık + motivasyon](https://consensus.app/papers/details/320eec83f9915a428960e7ab47e674bc/)). **Renk daima bir etiketle
birlikte** verilir (CVD-güvenliği + sistematik tutarlılık).

- **`glossSentence(spec)`** — satır-arası çözümleme; sözcük altında küçük etiket + **rol/cinsiyet
  renk-kodu**. `tokens:[{w, role?, tag?/gloss?}]`, `translation?`, `note?`, `caption`.
  Roller → renk (alt-çizgi): `masc`/`eril`→viz-1, `fem`/`dişil`→viz-3, `verb`/`fiil`→viz-2,
  `noun`/`isim`→viz-4, `adj`/`sıfat`→viz-5, `article`/`artikel`→aksan. **Renk etiketle eşlenir**
  (örn. "art · dişil"). `gloss` segmenti veya `visual.kind:"gloss"`.
- **`dialogue(spec)`** — iki konuşmacılı diyalog; satır altı çeviri/gloss.
  `turns:[{speaker,text,gloss?}]`. İlk konuşmacı solda, diğeri sağda.
- **`infoCards`** — artikel/kelime/kavram kartları (örn. le/la/les).
- **`vizTable`** — çekim tablosu (örn. *être* présent); **`flashcards`** — kelime tekrarı.

## 6. Genişletme deseni
Yeni bir ders için: (1) rengi gerekiyorsa `tedyLayer.subjectThemes.domains`'e kök ekle ve
`scripts/sync_carbon_tokens.py --write-subjects` çalıştır; konu anahtarı gerekiyorsa `subjectKey`'e satır ekle; (2) gerekiyorsa
`data-subject="…"` altında tipografi/biçim kuralı tanımla; (3) ilgili yapıcıyı
(`labeledFigure`/`relationFlow`/`infoCards`/`glossSentence`/`dialogue`) ya da `svg-authoring.md`
arketipini kullan.

> İlke: Derse-özel güç, **içeriği en demonstratif biçimde** göstermek içindir; süs değil.
> Renk, hareket ve yoğunluk her zaman `color-system.md` ve `adhd-pedagogy.md` sınırlarına uyar;
> renk tek başına anlam taşımaz, daima metin/etiketle birliktedir.
