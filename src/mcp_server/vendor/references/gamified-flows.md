# Oyunlaştırılmış Akış Şablonları — 4 Akış Deseni, Mekanikler ve Atıflı YAPMA Listesi

> Bu referans, `carbon-edupedia` modüllerinde segmentlerin **hangi sırayla ve
> hangi motivasyonel mantıkla** dizileceğini tanımlayan dört adlandırılmış
> **akış şablonu**, bunları besleyen **oyunlaştırma mekanikleri** ve kanıt-atıflı
> bir **YAPMA listesi** sunar. Tasarım spec'inin §4.3 + §10.3'ünün
> (`docs/superpowers/specs/2026-07-06-edupedia-deep-upgrade-design.md`) normatif
> düzyazıya dökümüdür ve gelecekteki **G-FLOW** doğrulayıcı kapısının (spec
> §6.1) tek doğruluk kaynağıdır — kapı henüz yazılmamış olsa bile (motor+şema
> yükseltmesi spec §11 madde 3'te, bu belgeden sonra gelir) bu belge onun
> sözleşmesidir; `carbon-excellence.md`'nin G-CARBON-GRID için kurduğu emsalin
> aynısı.

## 1. Amaç ve kapsam

**Şablon ≠ mod.** `SKILL.md` §6'daki 9 mod (MODULE/QUIZ/FLASHCARDS/GAME/
EXPLAINER/ASSESSMENT/SERIES/CURRICULUM/EXAM) **çıktının türünü** belirler; bu
belgedeki 4 şablon ise seçilen modun **içindeki segmentlerin ritmini ve
motivasyonel örgüsünü** belirler — ikisi ortogonaldir, birbirinin yerine
geçmez. Sefer şablonu tipik olarak MODULE/SERIES modunda tüm-modül iskeleti
olarak; Antrenman tipik olarak QUIZ/ASSESSMENT modunda veya bir Sefer
istasyonunun içinde uygulanır; ama hiçbir şablon belirli bir moda kilitli
değildir ve bir modül birden fazla şablonu (ör. Sefer'in içinde Antrenman)
iç içe kullanabilir.

**Alan durumu etiketleme.** Aşağıdaki her segment-dizisi tablosunda **"Durum"**
sütunu iki değerden birini taşır:
- **[MEVCUT]** — `module-architecture.md`/`interaction-patterns.md`'de zaten
  tanımlı ve motorun bugün desteklediği segment tipi/alan.
- **[YENİ]** — tasarım spec'i §5.1/§5.2'de tanımlı, motor+şema yükseltmesinde
  (bu belgeden sonraki görev) uygulanacak segment tipi/alan. Bu belge onların
  **davranışsal ve pedagojik sözleşmesidir**; bazı alanlar (avatar seçimi gibi)
  spec'in bıraktığı boşluğu bu belge somutlaştırır — ilgili yerde açıkça
  belirtilir.

**Değişmez ilke — ekleyici, gevşetici değil.** Aşağıdaki dört şablon ve
mekanikler, bu skill'in mevcut `adhd-pedagogy.md` §3 (yarışma/ödül etiği) ve
`G-WELLBEING` kapısı değişmezlerine (ceza yok, öz-rekabet önceliği, süre
opsiyonel, sabit-cetvel ödül) **eklenir** — hiçbirini gevşetmez veya yerini
almaz. Bir şablonun mekaniği ile `adhd-pedagogy.md` §3/`G-WELLBEING` çelişirse
her zaman §3/`G-WELLBEING` kazanır.

**Kanıt kalibrasyonu.** Aşağıdaki dört şablonun **hiçbiri** doğrudan "bu tam
HTML tasarımı" üzerinde test edilmemiştir. Kanıt, ilgili mekanik **sınıfı**
(merak-boşluğu, hedef-gradyanı, seviye-ilerleme + uyarlanır-zorluk, kaygısız
zaman-göstergesi, beden-ikizliği) üzerinden genel dijital/DEHB literatüründen
bu tasarıma aktarılmıştır — `adhd-pedagogy.md`'nin kendi "Sentez" bölümündeki
kalibrasyon ilkesiyle birebir aynı disiplin izlenir: bulgu var, ama bu spesifik
uygulama üzerinde RCT yok.

---

## 2. Dört akış şablonu

Her şablon, mevcut segment tiplerini (`teach`/`mcq`/`match`/`fillblank`/
`brainbreak`/`checkpoint` — bkz. `interaction-patterns.md`) belirli bir sırada
ve belirli yeni alanlarla zenginleştirerek dizer.

### 2.1 Keşif Döngüsü (atomik döngü)

En küçük tekrarlanabilir birim; Sefer ve Antrenman şablonları onu N kez
zincirler. Tek bir kazanımı tek bir merak-anı içinde açar ve **aynı döngü
içinde** kapatır.

**Akış:** hook → teach → interaction (mcq/match/fillblank) → mikro-kazanım.

| # | Adım | Segment/alan | Durum | Not |
|---|---|---|---|---|
| 1 | Kanca (hook) | `type:"hook"`, alanlar: `id`, `question`, `predict?`, `resolvesIn` | **[YENİ]** spec §5.1 | Bir merak boşluğu açar ("Sence hücrenin enerji santrali hangisi?"); opsiyonel notsuz `predict` tahmin kartı. `resolvesIn` **zorunlu** ve aynı `segments[]` dizisindeki bir sonraki `teach`'in `id`'sini gösterir. |
| 2 | Öğretim (teach) | mevcut `teach` şeması | **[MEVCUT]** | Hook'un sorusunu doğrudan yanıtlayan kısa anlatım (İlke 1, ≤4–6 birim). Bu segmente ulaşıldığında hook **kapanır** (bkz. §3.1). |
| 3 | Etkileşim | `mcq`/`match`/`fillblank` | **[MEVCUT]** | Anında geri bildirim + XP (İlke 3); ton her zaman sakin/nötr (G-WELLBEING). |
| 4 | Mikro-kazanım | üst-düzey `meta.milestones[]` rayı bir artar | **[YENİ]** spec §5.1 (rayın genişlemesi) | Döngü kendi başına yeni alan taşımaz — paylaşılan ilerleme rayını görünür biçimde ilerletir (hedef-gradyanı, bkz. §3.2). |

Hook segmentinin şeması:

```js
{ type: "hook", id: "h1",
  question: "Sence hücrenin enerji santrali hangisi?",
  predict: { options: ["Çekirdek", "Mitokondri", "Hücre zarı"] },  // opsiyonel
  resolvesIn: "t1" }  // aynı segments[] içindeki teach id'si — zorunlu
```

**Kanıt:** merak-boşluğu motivasyonun en güçlü yollarından biridir ve
**kapanmadan bırakılırsa hayal kırıklığına döner** — bu yüzden `resolvesIn`
zorunludur ([Kao ve ark. 2024, CHI](https://dl.acm.org/doi/10.1145/3613904.3642656);
açık boşluk → frustrasyon: [bulgu](https://www.sciencedirect.com/science/article/abs/pii/S0749597823000523);
kuramsal temel: Loewenstein 1994, information-gap kuramı). Mikro-kazanımın
gerekçesi hedef-gradyanı etkisidir (§3.2).

### 2.2 Sefer (modül omurgası)

Tüm modülü bir görev anlatısına oturtan omurga şablonu; N adet Keşif Döngüsü'nü
bir "yolculuk" çerçevesinde zincirler.

**Akış:** görev-girişi + avatar seçimi + SVG mini-harita (N istasyon,
istasyon-1 bahşedilmiş) → N × Keşif Döngüsü (istasyon başına dönüşümlü
etkileşim türü) → her ~3 istasyonda kamp molası → checkpoint + koleksiyon +
selfAssess → sağlıklı kapanış.

| # | Adım | Segment/alan | Durum | Not |
|---|---|---|---|---|
| 1 | Görev girişi | `objectives[]` + kısa görev cümlesi | **[MEVCUT]** (objectives) | "Bu modülde…" yerine görev çerçevesi: "Görevin: hücrenin gizli şehrini keşfetmek." |
| 2 | Avatar seçimi | `meta.quest.avatarOptions?` — nesne dizisi: `id`, `label`, `pictogram` | **[YENİ]** — bu belgenin `meta.quest`'e önerdiği ek alan (spec §5.1'in `meta.quest?:{stations[]}` şemasını somutlaştıran genişleme, çelişmez) | Opsiyonel; seçilen seçeneğin `pictogram`'ı üst çubukta öğrenciyi temsil eder. Yokluğunda Sefer avatar'sız çalışır — akış bozulmaz, yalnızca özerklik/temsil kazanımı azalır. |
| 3 | SVG mini-harita | `meta.quest.stations` — nesne dizisi: `id`, `label`, `completed?` | **[YENİ]** spec §5.1 | N istasyon düğümü SVG üzerinde dizilir. İlk istasyon **`completed: true`** ile baştan işaretlenir — öğrenci henüz hiçbir şey yapmadan **bahşedilmiş ilerleme** (endowed progress) kazanır. |
| 4 | N istasyon | N × Keşif Döngüsü (§2.1) | **[MEVCUT]+[YENİ]** karışık | Her istasyon bir önceki istasyondan **farklı** etkileşim tipi kullanır (mcq→match→fillblank→… dönüşümlü) — düşük-dış-yük/yüksek-uyarılma dengesini yenilik yoluyla korur (`adhd-pedagogy.md` İlke 5/Sergeant 2005), tekdüzelik yaratmadan. |
| 5 | Kamp molası | `brainbreak` (her ~3 istasyonda bir) | **[MEVCUT]**, anlatı çerçevesi yeni | Var olan `brainbreak` segmenti; sunumda "kamp molası" olarak adlandırılır. Mola dozu/sıklığı için bkz. `adhd-pedagogy.md` §10.1 (Broad ve ark. 2021). |
| 6 | Kapanış | `checkpoint` (recap + mixedQuestions + selfAssess) + `rewards.badges` koleksiyonu | **[MEVCUT]** | Modül-sonu özeti motor tarafından otomatik üretilir (ustalık, rozet kasası, öz-değerlendirme — `adhd-pedagogy.md` §6). |
| 7 | Sağlıklı kapanış | özet ekranı metni | **[MEVCUT]** segment, metin kuralı yeni | Özet **"başka modül" baskısı içermez**; "bugünlük bu kadarı yeterli" tonuyla biter (`adhd-pedagogy.md` Ö1). |

`meta.quest` şeması (avatar + istasyon):

```js
meta: {
  quest: {
    avatarOptions: [                          // opsiyonel genişleme (bu belge)
      { id: "explorer", label: "Kâşif", pictogram: "pic-rocket" },
      { id: "scholar", label: "Bilge", pictogram: "pic-idea" }
    ],
    stations: [                               // spec §5.1
      { id: "s1", label: "Giriş Kapısı", completed: true },   // bahşedilmiş ilerleme
      { id: "s2", label: "Enerji Odası" },
      { id: "s3", label: "Çekirdek Kalesi" }
    ]
  }
}
```

**Kanıt:** oyunlaştırılmış seviye-ilerleme + uyarlanır zorluk birlikte
uygulandığında 8 haftalık bir DEHB RCT'sinde dikkat ve akademik kazanımlarda
**büyük etki büyüklükleri (d>0.9) ve 8 hafta sonunda korunan kazanımlar**
saptanmıştır
([Dai, Wufue & Zhang 2025, *Front. Educ.*](https://doi.org/10.3389/feduc.2025.1668260)).
Bahşedilmiş ilerleme hedef-gradyanı etkisinin bir uzantısıdır — hedef-gradyanı
temeli için [Kivetz, Urminsky & Zheng 2006](https://www.researchgate.net/publication/239776073),
bahşedilmiş ilerlemenin birincil kaynağı için Nunes & Drèze 2006 (*Journal of
Consumer Research*), ikincil açıklama için
[LogRocket](https://blog.logrocket.com/ux-design/goal-gradient-effect/).
Avatar seçimi Proteus etkisiyle gerekçelenir — bir temsilci seçmek/kullanmak
küçük-orta düzeyde davranış/motivasyon etkisi taşır (Yee & Bailenson 2007;
[Ratan ve ark. 2020 meta-analiz](https://www.tandfonline.com/doi/full/10.1080/15213269.2019.1623698)).

### 2.3 Antrenman (uyarlanır pratik)

Tek bir beceriyi tekrarlı, uyarlanır-zorlukta pratikle pekiştiren drill
şablonu. Tipik olarak QUIZ/ASSESSMENT modunda veya bir Sefer istasyonunun
içinde kullanılır.

**Akış:** ısınma (1 kolay soru) → uyarlanır item merdiveni (yuvarlanan pencere;
2 yanlışta ipucu-önce; güçlü seride opsiyonel "meydan okuma") → gain-only
streak → öğe-başına açıklama → öz-rekor özeti (liderlik tablosu YOK) →
opsiyonel tempo diski (varsayılan KAPALI).

| # | Adım | Segment/alan | Durum | Not |
|---|---|---|---|---|
| 1 | Isınma | tek `mcq`/`fillblank`, `tier: 1` | **[MEVCUT]** segment, **[YENİ]** `tier` alanı (spec §5.2) | Garanti-kolay ilk soru (erken başarı, İlke 6). |
| 2 | Uyarlanır merdiven | ardışık sorular, `tier?: 1/2/3` | **[YENİ]** spec §5.2 | Yuvarlanan pencere: **2 ardışık yanlış → ipucu-önce** sunulur (soru zorlaşmaz, destek artar); **2 ardışık doğru → opsiyonel "meydan okuma"** (tier 3, öğrencinin **kendi seçtiği**, dayatılmayan). Taban her zaman `tier: 1`'e kilitli (asla daha kolayın altına düşmez) ve geçiş **görünmez** (bkz. §3.3). |
| 3 | Gain-only streak | mevcut `streak` sayacı, kayıp-dili kaldırılmış | **[MEVCUT]** sayaç, **[YENİ]** dil kısıtı (spec §5.1) | Yanlışta seri **sıfırlanmaz**, nötr "korundu" diliyle **tutulur**. `adhd-pedagogy.md` §3 (ceza yok) ilkesinin doğrudan uzantısı. |
| 4 | Öğe-başına açıklama | `explanation` alanı | **[MEVCUT]** (genel G-INTERACT'ta WARN) | Bu şablonda **fiilen zorunlu** — Antrenman'ın öğretici çekirdeği budur (drill = yalnız ölçme değil öğretim, `adhd-pedagogy.md` İlke 8). Genel G-INTERACT kapısının şiddetini değiştirmez; yalnızca bu şablonun yazım disiplinini yükseltir. |
| 5 | Öz-rekor özeti | özet ekranı, önceki-en-iyi karşılaştırması | **[YENİ]** kalıcılık deseni (spec §5.4'ün `localStorage` desenini yeniden kullanır — bkz. `content-enrichment.md` §2.4) | Özet öğrencinin **kendi** önceki en iyi skoruna kıyaslanır; **küresel/akran liderlik tablosu asla yok** (bkz. §4 madde 2). `localStorage` yoksa/bloklu ise sessizce oturum-içi karşılaştırmaya düşülür (yalnız bu oturumun geçmişi). |
| 6 | Tempo diski | `learner.pacingDisk?: false` | **[YENİ]** spec §5.1 | Varsayılan **KAPALI**; açılırsa sayısız/kesintisiz SVG disk (§3.4). |

**Kanıt:** uyarlanır zorluk, seviye-ilerleme RCT'sinin bir parçası olarak
olumlu sonuç vermiştir ([Dai 2025](https://doi.org/10.3389/feduc.2025.1668260)),
ama dinamik-zorluk-ayarlama (DDA) literatürü genel olarak **karışık** sonuçlar
bildirir — evrensel bir kazanım olarak sunulmamalı, tasarıma duyarlıdır
([Zohaib 2018, derleme](https://onlinelibrary.wiley.com/doi/10.1155/2018/5681652)).
Bu yüzden taban-koruma ve görünmezlik (etiketlememe) isteğe bağlı süslemeler
değil, kritik güvenlik sınırlarıdır.

### 2.4 Birlikte Odak (co-play sarmalayıcı)

Diğer üç şablonun üstüne **opsiyonel** bir ince katman olarak eklenen, tek
başına yeni segment tipi veya kalıcı alan **gerektirmeyen** bir sunum
sarmalayıcısı. Var olan metin alanlarını (`instructions`, `objectives`,
`teach.body`) birlikte-oyun çerçevesinde yeniden yazarak gerçekleşir.

**Akış:** opsiyonel "tek başına / biriyle" seçimi → etkileşimlerde
sıra-tabanlı istemler → sakin "odak yoldaşı" kartı → paylaşılan beyin
molaları.

| # | Adım | Gerçekleşme | Durum | Not |
|---|---|---|---|---|
| 1 | Seçim | tanıtım metninde tek soru ("Bunu tek başına mı, biriyle mi yapmak istersin?") | **[MEVCUT]** metin alanı, yeni şema gerekmez | Kalıcı bir alan tutmaz; oturum başında bir kez sorulan, akışı değiştirmeyen bir çerçeveleme sorusu (özerklik, İlke 6). |
| 2 | Sıra-tabanlı istem | `mcq`/`match`/vb. `instructions` metni "biriyle" seçildiğinde dönüşümlü ifade taşır ("Senin sıran" / "Arkadaşının sırası") | **[MEVCUT]** alan, içerik yeniden yazılır | Yeni segment tipi yok; var olan `instructions` alanının içeriği değişir. |
| 3 | Odak yoldaşı kartı | `teach`-benzeri sakin bir mikro-kart | **[MEVCUT]** segment tipi, yeni içerik çerçevesi | Bilgi vermez, yalnız "yanında biri var" hissini nazikçe hatırlatır — beden-ikizliği (body doubling) çerçevesinde. |
| 4 | Paylaşılan mola | `brainbreak` | **[MEVCUT]** | Aynı segment; "birlikte yapın" yönergesiyle sunulur. |

**Kanıt ve sınır (düşük-kesinlik uyarısı):** beden ikizliği (body doubling)
DEHB topluluğunda yaygın doğrulanmış bir pratik olsa da kanıt tabanı RCT değil,
topluluk-onaylı nitel/karma-yöntem araştırmadır
([Eagle, Baltaxe-Admony & Ringland 2024, *ACM TACCESS*](https://dl.acm.org/doi/full/10.1145/3689648)).
Bu yüzden bu şablon **düşük-kesinlik** etiketiyle sunulur: gerçek bir insan
partnerin (akran, kardeş, veli) yerini **asla almaz**, yalnız dijital oturumu
insanla paylaşma **çerçevesini** kolaylaştırır — `adhd-pedagogy.md` §11
"tamamlar, yerine geçmez" ilkesiyle birebir uyumlu. Bu nedenle §5'teki
makine-denetlenebilir alt-kümeye **dahil değildir** — yeni persist edilen bir
alan/durum taşımadığından denetlenecek bir makine yüzeyi yoktur (§5 sonundaki
not, `carbon-excellence.md` §3'ün madde-6 dışlama gerekçesiyle aynı mantık).

---

## 3. Mekanikler — ADHD gerekçesi ve HTML tezahürü

Aşağıdaki dört mekaniğin tümü mevcut emoji-yasağı (G-EMOJI) ve cezalandırıcı-dil
yasağı (G-WELLBEING) içinde kalır; hiçbiri anlam taşımak için emoji kullanmaz —
ikon/piktogram/SVG kullanır (`icon-pictogram-svg.md`). "HTML/motor tezahürü"
alt-başlıkları, motor+şema yükseltmesinin (spec §11 madde 3) bu mekanikleri
somutlaştırırken uyacağı normatif davranışı tanımlar.

### 3.1 Merak-boşluğu — segment içinde kapanır

**Ne:** Bir `hook` segmenti bilgi boşluğu açar (soru, opsiyonel tahmin); hedef
alınan `teach` segmentine ulaşıldığında boşluk **aynı akış içinde** kapanır.
**Asla** bir sonraki oturuma, modüle veya "ileride açıklanacak" bir vaade
ertelenmez.

**Gerekçe:** Bilgi-boşluğu kuramına göre merak, bilinen ile bilinmek istenen
arasındaki boşluğun kendisinden doğar (Loewenstein 1994). Güncel deneysel
kanıt, merakı öğrenme motivasyonunun **en güçlü** yollarından biri olarak
doğrular ([Kao ve ark. 2024, CHI](https://dl.acm.org/doi/10.1145/3613904.3642656));
ama boşluk **kapanmazsa** motivasyon yerini hayal kırıklığına bırakır
([bulgu](https://www.sciencedirect.com/science/article/abs/pii/S0749597823000523)) —
DEHB'de gecikme itimi (delay aversion, `adhd-pedagogy.md` §1 Sonuga-Barke) bu
riski büyütür: kapanmayan bir boşluk, DEHB'li öğrenci için sıradan bir
sabırsızlıktan çok daha maliyetlidir.

**HTML/motor tezahürü (iki katman):**
1. **Veri şeması (birincil, statik-denetlenebilir).** Her `hook` segmentinin
   `resolvesIn` alanı, aynı `segments[]` dizisinde var olan bir `id`'yi
   gösterir — `G-CURRICULUM`'un `mappedTo`↔`segments` deseninin (bkz.
   `skill-manifest.yaml`) birebir aynı tekniği.
2. **Motor şablonu (ikincil, çalışma-zamanı kanıtı).** `resolvesIn` ile
   hedeflenen segment render edildiğinde motor onun kök öğesine
   `data-hook-resolved="<hookId>"` attribute'unu ekler. Bu, hem
   `module-auditor` ajanının (spec §7) DOM denetiminde ikinci bir doğrulama
   katmanı sağlar hem de ileride bir DOM-farkında denetleyici eklenirse hazır
   bir kanca bırakır.

### 3.2 Hedef-gradyanı + bahşedilmiş ilerleme

**Ne:** İlerleme rayı hedefe yaklaştıkça motivasyonu artıracak biçimde sunulur
("son iki durak" yakın-hedef etiketi) ve bir Sefer'in ilk istasyonu öğrenci
henüz hiçbir şey yapmadan **önceden tamamlanmış** işaretlenir.

**Gerekçe:** Hedef-gradyanı hipotezi, bir hedefe yaklaşıldıkça çabanın
arttığını gösterir ([Kivetz, Urminsky & Zheng 2006](https://www.researchgate.net/publication/239776073)).
**Bahşedilmiş ilerleme** (endowed progress) bu etkinin bir uzantısıdır:
kullanıcıya henüz hak etmediği bir baş-ilerleme verildiğinde tamamlama
olasılığı artar. Birincil kaynak Nunes & Drèze 2006'dır (*Journal of Consumer
Research*; bkz. §6 Kaynakça); [LogRocket açıklaması](https://blog.logrocket.com/ux-design/goal-gradient-effect/)
ikincil bir anlatı özetidir.

**HTML/motor tezahürü:** `meta.milestones[]` üst-düzey ilerleme rayında
düğümler olarak render edilir; son iki düğüme yaklaşıldığında ray "son iki
durak" etiketiyle vurgulanır. Sefer'de `meta.quest.stations[0].completed`
başlangıçta `true` yazılarak ilk düğüm dolu render edilir — bu bir hata değil,
kasıtlı tasarımdır (§2.2).

### 3.3 Görünmez taban-korumalı uyarlanır zorluk

**Ne:** Soru zorluğu (`tier`) öğrencinin son performansına göre sessizce
ayarlanır; taban her zaman kolay seviyeye kilitlidir (asla daha da aşağı
düşmez) ve ayar **hiçbir görünür duyuru/etiket üretmez**.

**Gerekçe:** Seviye-ilerleme + uyarlanır zorluk birlikte bir 8 haftalık DEHB
RCT'sinde dikkat ve akademik kazanımda büyük, kalıcı etkiler üretmiştir
([Dai, Wufue & Zhang 2025](https://doi.org/10.3389/feduc.2025.1668260)). Ama
dinamik zorluk ayarlama literatürü genelde **karışık** bulgular taşır —
tasarıma aşırı duyarlıdır ([Zohaib 2018](https://onlinelibrary.wiley.com/doi/10.1155/2018/5681652)).
Etiketleme riski özellikle kritiktir: DEHB'de duygu-düzenleme kırılganlığı
başarısızlık/etiketleme diline karşı savunmasızdır (`adhd-pedagogy.md` Ö4,
Groves 2021).

**HTML/motor tezahürü:** `tier` geçişi yalnız **bir sonraki sorunun içeriğini**
değiştirir — hiçbir banner/toast/rozet ("seviye düştü", "kolay soruya geçtik",
"zorlanıyorsun" vb.) üretilmez. Geçiş öğrenciye tamamen **görünmezdir**; yalnız
motorun iç durumunda (`tier` sayacı) izlenir. Metinsel çıktıda ikinci-tekil
etiketleyici sıfat/yargı **yasaktır** (bkz. §5 regex kara listesi).

### 3.4 Kaygısız tempo diski

**Ne:** Opsiyonel (varsayılan **KAPALI**) bir SVG disk, geçen zamanı
**sayısız** ve **kesintisiz** biçimde (azalan dilim, sayı yok) gösterir. Disk
boşaldığında **hiçbir engelleyici olay tetiklenmez** — segment kilitlenmez,
otomatik ilerlemez; disk yalnız ortam ipucudur, bir sınır değildir.

**Gerekçe:** Görsel-disk biçimli, sayısız bir süre göstergesi hem beklenti
kaygısını (anticipatory anxiety, d=0.42) hem de dikkatsizliği azaltmış,
performansı değiştirmemiştir ([Hallez & Vallier 2025, *EJIHPE*](https://pmc.ncbi.nlm.nih.gov/articles/PMC12731990/)).
Kritik tasarım çıkarımı: yarar **sayısal/sert geri-sayım biçiminden değil,
disk-biçiminin kendisinden ve sayı içermemesinden** gelir — bu yüzden
`pacingDisk` bir sayaç/geri-sayım **değil**, yalnız bir görsel doku olarak
tanımlanır.

**HTML/motor tezahürü:** `learner.pacingDisk` alanı `false`/`true`; `true`
olduğunda motor bir SVG dilimini zamanla daraltır (`stroke-dasharray`
animasyonu, `prefers-reduced-motion` saygılı). Diskin üstünde/yanında **hiçbir
sayısal metin** (saniye, geri-sayım, "00:23" vb.) render edilmez; disk
sıfırlandığında yalnız görsel olarak "tükenmiş" görünür, hiçbir zamanlayıcıya
bağlı engelleyici olay (segment kilidi, otomatik-devam, uyarı sesi) bağlanmaz.

---

## 4. Atıflı YAPMA listesi

Aşağıdaki sekiz kalıp, iyi niyetli oyunlaştırma çabalarının bile DEHB'de zarar
verdiği, kanıtla belgelenmiş kalıplardır. Bu liste `adhd-pedagogy.md` §3 (etik
sınırlar) ve `G-WELLBEING` kapısına **eklenir**, onların yerini almaz.

1. **Cross-session streak / kayıp-aversiyonu.** Gün-aşırı süregelen bir
   "seriyi bozma" baskısı (Duolingo'nun seri mekaniği gibi) kayıp-aversiyonunu
   devreye sokar — kullanıcı ilerlemekten çok **kaybetmemek** için geri döner;
   bu içsel değil dışsal-kaygı-güdümlü bir bağlılıktır
   ([Duolingo vaka incelemesi](https://trophy.so/blog/duolingo-gamification-case-study)).
   Bu skill'in streak'i (§2.3) **oturum-içi ve gain-only** kalır; gün-aşırı
   "serini bozma" baskısı kurulmaz.
2. **Liderlik tablosu (leaderboard).** Akran karşılaştırması/sıralaması,
   oyunlaştırma unsurları arasında tutarsız ve bazen olumsuz etkili
   bulunmuştur, özellikle düşük-performans algılayan öğrencilerde
   ([Hanus & Fox 2015](https://www.sciencedirect.com/science/article/abs/pii/S0360131514002000)).
   Varsayılan **yok**; §2.3'teki özet daima öğrencinin **kendi** geçmişine
   kıyaslanır.
3. **Değişken-oran ödül / loot-box.** Öngörülemez (variable-ratio) ödül
   çizelgesi kumar mekaniğiyle aynı pekiştirme yapısını taşır ve DEHB'nin
   gecikmeli-pekiştirme duyarlılığını sömürme riski taşır (`adhd-pedagogy.md`
   Ö3, Tripp & Wickens 2009). Ödül her zaman **sabit-cetvel** (doğru = +10,
   ilk-deneme bonus = +5) kalır — asla rastgele/gizli bir dağılımdan çekilmez.
4. **Geri-sayım / sert-süre baskısı.** Sayısal geri-sayım ve sert zaman
   sınırı kaygı üretir; bunun yerine test edilmiş, kaygı-azaltan biçim
   sayısız/kesintisiz disktir (§3.4, Hallez & Vallier 2025). Süre her zaman
   **opsiyonel ve varsayılan kapalı** kalır (`adhd-pedagogy.md` §3).
5. **Aşırı-juicing.** Her mikro-eylemde ekran-sarsıntısı, confetti, art arda
   parıltı/flaş gibi "juice" katmanları düşük-dış-yük ilkesini ihlal eder
   (`adhd-pedagogy.md` İlke 5, Sergeant 2005 aşırı-uyarılma riski) ve
   `carbon-excellence.md`'nin koreografi bütçesini (öğe başına ~20ms stagger,
   toplam <500ms, madde 9) aşar. Geri bildirim **ölçülü** kalır: tek bir sakin
   onay ikonu + kısa geçiş, art arda efekt yığını değil.
6. **Overjustification (aşırı-gerekçelendirme).** Zaten içsel ilgi duyulan bir
   etkinliğe güçlü dışsal ödül eklemek, ödül kaldırıldığında içsel motivasyonu
   **azaltabilir** (Deci, Koestner & Ryan 1999, klasik meta-analiz). Bu
   yüzden ödül her zaman **bilgilendirici** çerçevede kalır (ustalık/ilerleme
   anlatır), performansı "satın alan" bir sopa-havuç değil (`adhd-pedagogy.md`
   İlke 6).
7. **Hyperfocus-sömürüsü.** Mekanikleri, DEHB'nin hiper-odaklanma eğilimini
   sömürüp oturumu sağlıksız biçimde uzatacak "bir istasyon daha" çekişi
   üretecek şekilde tasarlamak, ihtiyaç-ihmaline (uyku, sosyal, dinlenme) yol
   açabilir ([Ashinoff & Abu-Akel 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC9579965/)).
   Sefer'in sağlıklı-kapanışı (§2.2) ve `adhd-pedagogy.md` Ö1'in nazik mola
   hatırlatıcısı bunun karşı-tedbiridir.
8. **Açık (kapanmayan) merak-boşluğu.** Bir kancayı bilerek bir sonraki
   segmente, modüle veya oturuma **erteleyip** kapatmamak — "bunu ileride
   öğreneceksin" vaadiyle bırakmak — hem hayal kırıklığı riski taşır
   ([bulgu](https://www.sciencedirect.com/science/article/abs/pii/S0749597823000523))
   hem de §5'teki G-FLOW kuralının doğrudan ihlalidir. Her `hook` **aynı
   akışta** kapanır (§2.1, §3.1).

---

## 5. Makine-denetlenebilir alt-küme (G-FLOW normatif sözleşmesi)

Yukarıdaki mekaniklerin/YAPMA maddelerinin bir kısmı yargı gerektirir (ör. "bu
kart gerçekten sakin mi hissettiriyor" — `module-auditor` ajanına bırakılır,
spec §7). **G-FLOW** kapısı (spec §6.1; koşullu — yeni oyunlaştırma alanları
yoksa **atlanır**, geriye uyum) yalnız aşağıdaki **statik-metin/şema-
denetlenebilir** dört kuralı kapsar — bu tablo, kapı implementasyonunun tam
sözleşmesidir:

| # | Kural | Kontrol (marker/regex) | Sonuç sınıfı |
|---|---|---|---|
| 1 | **Kanca kapanışı.** Her `hook` segmentinin `resolvesIn`'i `segments[]` içinde var olan bir `id`'ye karşılık gelir. | Render edilmiş HTML'de her `[data-seg="hook"]` öğesinin karşılığında bir `data-hook-resolved="<hookId>"` markeri var mı taraması (§3.1'deki motor tezahürüyle aynı marker çifti). | **FAIL** (karşılık gelen marker yoksa = hiç kapanmayan kanca, §4 madde 8) |
| 2 | **Gain-only streak dili.** Streak/XP metinlerinde kayıp-çerçeveli/ceza dili yok. | Regex kara liste: "kaybettin", "serin bozuldu", "sıfırlandı", "-XP", "canını kaybet" vb. | **FAIL** (eşleşirse) |
| 3 | **`pacingDisk` sayısız + kesintisiz.** Etkin bir tempo-diski öğesi sayısal geri-sayım/hard-stop taşımaz. | Render edilmiş HTML'de tempo-diski öğesi bir `data-countdown` attribute'u **taşımaz** (ve yanında sayısal geri-sayım/hard-stop deseni yoktur). | **FAIL** (bulunursa) |
| 4 | **Etiketlemeyen uyarlanır zorluk.** `tier` geçişiyle ilişkili ikinci-tekil etiketleyici/yargılayıcı dil yok ("zorlanıyorsun" vb. yok). | Regex kara liste: "zorlanıyorsun", "yavaşsın", "başarısızsın", "kolay geldi çünkü…" vb. | **FAIL** (eşleşirse) |
| — | **İlgili alan yokluğu.** Modülde `hook`/`pacingDisk`/`tier`/`meta.quest`/`meta.milestones` alanlarının hiçbiri yoksa. | Alan taraması boş döner. | Kapı **atlanır** (geriye uyum — mevcut modüller kırılmaz) |

Kesin regex/uygulama Task 6 `gate_flow`'da; bu bölüm denetlenen değişmezi
tanımlar.

**Not — Birlikte Odak (§2.4) neden bu alt-kümede yok:** bu şablon yeni bir
segment tipi veya persist edilen alan taşımaz (yalnız var olan
`instructions`/`teach` metnini yeniden çerçeveler) — denetlenecek yeni bir veri
yüzeyi yoktur. Bu, `carbon-excellence.md` §3'ün madde-6'yı (render edilmiş
sütun genişliği hesabı gerektirir) G-CARBON-GRID'in dışında tutma
gerekçesiyle aynı mantığı izler: statik/şema denetimi **buradaki dört kuralla**
sınırlıdır; şablonların geri kalan niteliksel yönleri (kartın gerçekten "sakin"
hissettirip hissettirmediği, anlatının gerçekten ilgi çekici olup olmadığı)
`module-auditor` ajanının insan-benzeri değerlendirmesine kalır.

**Değişmezlik hatırlatması:** bu dört kural `G-WELLBEING`'i **tamamlar**, onun
yerine geçmez — `G-WELLBEING` zaten genel cezalandırıcı/süre-baskısı dilini
denetler (`skill-manifest.yaml`); G-FLOW bunun **oyunlaştırmaya özgü** dört ek
yüzeyini (kanca, streak, disk, zorluk-etiketleme) ekler.

---

## 6. Kaynakça

- Loewenstein, G. (1994). The psychology of curiosity: A review and
  reinterpretation. *Psychological Bulletin*, 116(1). (bilgi-boşluğu kuramı;
  kanonik, URL yok)
- Kao, D. ve ark. (2024). How does Juicy Game Feedback Motivate? Testing
  Curiosity, Competence, and Effectance. *CHI 2024*.
  https://dl.acm.org/doi/10.1145/3613904.3642656
- Schweitzer, V. M., Gerpott, F. H., Rivkin, W., & Stollberger, J. (2023).
  (Don't) mind the gap? Information gaps compound curiosity yet also feed
  frustration at work. *Organizational Behavior and Human Decision
  Processes*, 178.
  https://www.sciencedirect.com/science/article/abs/pii/S0749597823000523
- Kivetz, R., Urminsky, O., & Zheng, Y. (2006). The Goal-Gradient Hypothesis
  Resurrected: Purchase Acceleration, Illusionary Goal Progress, and
  Customer Retention. *Journal of Marketing Research*, 43(1).
  https://www.researchgate.net/publication/239776073
- Nunes, J. C., & Drèze, X. (2006). The Endowed Progress Effect: How
  Artificial Advancement Increases Effort. *Journal of Consumer Research*,
  32(4). (bahşedilmiş ilerlemenin birincil kaynağı; kanonik, URL yok)
- Bahşedilmiş ilerleme (endowed progress) — LogRocket açıklaması (ikincil).
  https://blog.logrocket.com/ux-design/goal-gradient-effect/
- Dai, Wufue, & Zhang (2025). Effectiveness of a gamified educational
  application on attention and academic performance in children with ADHD:
  an 8-week randomized controlled trial. *Frontiers in Education*, 10.
  https://doi.org/10.3389/feduc.2025.1668260
- Zohaib, M. (2018). Dynamic Difficulty Adjustment (DDA) in Computer Games:
  A Review. *Advances in Human-Computer Interaction*.
  https://onlinelibrary.wiley.com/doi/10.1155/2018/5681652
- Hallez, Q., & Vallier, F. (2025). Time on Their Side: How Visual Timers
  Affect Anticipatory Anxiety, Performance, and On-Task Behavior in
  Elementary Math Assessments. *European Journal of Investigation in Health,
  Psychology and Education*. https://pmc.ncbi.nlm.nih.gov/articles/PMC12731990/
- Eagle, L., Baltaxe-Admony, L. B., & Ringland, K. E. (2024). "It Was
  Something I Naturally Found Worked and Heard About Later": An
  Investigation of Body Doubling with Neurodivergent Participants. *ACM
  Transactions on Accessible Computing (TACCESS)*, 17(3).
  https://dl.acm.org/doi/full/10.1145/3689648
- Yee, N., & Bailenson, J. (2007). The Proteus Effect: The Effect of
  Transformed Self-Representation on Behavior. *Human Communication
  Research*, 33(3). (kanonik, URL yok)
- Ratan, R. ve ark. (2020). Avatar Characteristics Induce Users' Behavioral
  Conformity with Small-to-Medium Effect Sizes: A Meta-Analysis of the
  Proteus Effect. *Media Psychology*, 23(5).
  https://www.tandfonline.com/doi/full/10.1080/15213269.2019.1623698
- Hanus, M. D., & Fox, J. (2015). Assessing the effects of gamification in
  the classroom: A longitudinal study on intrinsic motivation, social
  comparison, satisfaction, effort, and academic performance. *Computers &
  Education*, 80.
  https://www.sciencedirect.com/science/article/abs/pii/S0360131514002000
- Duolingo streak = kayıp-aversiyonu vaka incelemesi.
  https://trophy.so/blog/duolingo-gamification-case-study
- Deci, E. L., Koestner, R., & Ryan, R. M. (1999). A meta-analytic review of
  experiments examining the effects of extrinsic rewards on intrinsic
  motivation. *Psychological Bulletin*, 125(6). (kanonik, URL yok)
- Ashinoff, B. K., & Abu-Akel, A. (2021). Hyperfocus: the forgotten frontier
  of attention. *Psychological Research* (PMC).
  https://pmc.ncbi.nlm.nih.gov/articles/PMC9579965/

> **Not:** Yukarıdaki kaynaklar bu belgeye **özgü yeni** atıflardır. Mola
> dozu, ceza-yok ilkesi, öz-belirleme kuramı, ustalık/öz-izleme gibi zaten
> `adhd-pedagogy.md`'de tam atıfla kurulmuş ilkeler burada **yeniden atıf
> almadan** çapraz-referanslanır (ilgili şablon/mekanik metninde "bkz.
> adhd-pedagogy.md §X" biçiminde işaretlenir) — bu, kaynakçanın şişmesini
> önler ve tek-doğruluk-kaynağı ilkesini korur.
