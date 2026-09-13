# Sınav Sorusu Çözme (EXAM modu) — Anatomi, Zincir ve Degrade Protokolleri

> **Ne zaman okunur:** `/edupedia:soru` çağrıldığında veya `mode:"EXAM"` bir modül
> üretilirken — **ZORUNLU, akışın tamamı**.
>
> **Ön koşul:** `references/adhd-pedagogy.md` (her modülden önce zorunlu) +
> `references/module-architecture.md` (`worked` ve `selfExplain` şemaları).
>
> **Tasarım kaynağı:** `docs/superpowers/specs/2026-07-31-edupedia-sinav-asistani-design.md`
> (tek soru, K1–K4) + `docs/superpowers/specs/2026-08-16-edupedia-coklu-soru-design.md`
> (çoklu soru, K5–K8).

EXAM modu, öğrencinin önüne gelmiş **bir veya birden fazla** sınav sorusunu (fotoğraf
veya yapıştırılmış metin) girdi alır ve onu edupedia'nın pedagojik ilkeleriyle çözen
+ gerektirdiği kavram zincirini öğreten **tek-dosya** etkileşimli bir modüle çevirir.

Bu mod, `CURRICULUM` modunun **tersine çalışır**: orada çerçeveyi ders kitabı çizer ve
model neyi üreteceğini seçer; burada **soru verilidir** ve çerçeveye sonradan bağlanır.

---

## 1. Kararlar (değiştirilemez)

| # | Karar | Gerekçe |
|---|---|---|
| K1 | Çıktı = etkileşimli tek-dosya HTML modül | Motor, mevcut kapılar ve `worked`/`selfExplain` yeniden kullanılır (G-EXAM 15., G-VOICE 16.'dır); yeni çıktı türü yok |
| K2 | Soru **içerikçe birebir** yer alır; modül **paylaşılmaz / siteye yüklenmez** | Öğrenci kendi sorusunu tanımalı; telif riski paylaşılmayarak kapatılır |
| K3 | Anlatım = **geriye doğru kavram zinciri** (kazanımın tamamı değil) | ~10-12 dk, DEHB kısa-oturum ilkesi; her segment soruya bağlı olduğu için "neden bunu öğreniyorum" hep açık |
| K4 | Soru **transkribe + yeniden inşa** edilir; **fotoğraf gömülmez** | Motorda raster taşıyıcı yok; yeniden inşa tema-duyarlı, ekran-okuyucu erişilebilir ve Tier-1 yazar-SVG doktriniyle tutarlı |
| K5 | Teslim = **tek HTML** (konu farklı olsa bile) | Ortak/ardışık konu anlatımı + her sorunun çözümü aynı dosyada |
| K6 | Konu zinciri **soru başına değil konu başına** | Aynı konudaki sorular anlatımı tekrarlamaz |
| K7 | Yumuşak tavan **~4 soru** | DEHB kısa oturum; 5+ için uyarı, üretim durmaz (FAIL değil) |
| K8 | Yeni komut yok | `/edupedia:soru` genişler; tek soru eski `exam:{}` davranışı |

---

## 2. Akış

**Adım 0 — Girdi.** Fotoğraf(lar)ı oku ve/veya yapıştırılmış metni al. Bir veya birden
fazla soru; belirsiz rakam/şık → SOR (D5), tahmin yok. Hangisini istediğini **sorma** —
hepsi aynı HTML'de işlenir (K5). n > 4 ise kullanıcıya “oturum uzayacak” uyarısı ver,
üretimi durdurma (K7).

**Adım 1 — TRANSKRİPSİYON.** Her soruyu **birebir** metne çevir: aynı sayılar, aynı ifade,
aynı şıklar. Şekil/grafik varsa `references/svg-authoring.md` kurallarıyla **yazar-SVG
olarak yeniden çiz** (token renk, `role="img"` + `<title>`, 2px stroke, gradyansız).
Fotoğraf HTML'e gömülmez (K4).

> **Belirsizlik varsa SOR, tahmin etme.** Silik rakam, kesik kenar, okunmayan üs →
> neyin belirsiz olduğunu **tam olarak** söyle: "üçüncü şıkkın son rakamı okunmuyor —
> 6 mı 8 mi?" Yanlış okunan bir soru, sonraki her adımı sessizce yanlış yapar.

**Adım 2 — KAPI: ders + sınıf.** Kesinleşmeden üretim başlamaz. Fotoğrafta yazmıyorsa
`AskUserQuestion` ile **SOR**.

> Kural ve gerekçesi **tek yerde**: `curriculum-integration.md` §3 Adım 0. Burada
> tekrarlanmaz — çoğaltma iki kopyanın sapmasına yol açar.

**Adım 2b — KÜMELE.** Soruları konuya göre grupla. Farklı konular ardışık kümeler olur;
hâlâ tek HTML. Zincir **küme (konu) başına** kurulur, soru başına değil (K6).

**Adım 3 — TEŞHİS (geriye çözümleme).** Her konu kümesini tersine çöz: *"bunu çözmek için
önce neyi bilmek gerekiyor?"* Tipik olarak 2-4 halka. Her halka bir kavram veya beceridir,
bir konu başlığı değil.

Örnek — *"3/4 kg elma 24 TL ise 2/3 kg kaç TL?"*:
1. birim fiyat kavramı
2. kesirle bölme
3. kesirle çarpma

**Adım 4 — KAZANIM.** Zincirin her halkasını `search_learning_outcomes` ile bir MEB
kazanımına **bağla — doğrula, uydurma**. Bağlanamayan halka için **D2** (§5).

**Adım 5 — ÇERÇEVE.** `list_textbooks` → `get_document_text` ile zincirin ders
kitabındaki yerini aç. **Çözümün ve anlatımın dayanağı burasıdır.** Kitap yoksa **D3**.

**Adım 6 — ÇÖZ.** Her sorunun kendi demonstratif çözümünü üret; her adımın dayanağı
kitap sayfası olmalı. Soru bozuksa **D1**, çerçeve üstüyse **D4** — **öğenin**
`integrity`'sine yazılır; bir bozuk soru modülü iptal etmez.

**Adım 7 — KURGU.** Tek soru: `exam` bloğu (§3) + 11 segmentlik kurgu (§4).
Çoklu: `topics[]` + `exams[]` (§3.1) + sıkıştırılmış kurgu (§4.4).

**Adım 8 — TESLİM.** `scripts/validate_module.py` (G-EXAM dahil) → çıktı dizini + yan yana
`.manifest.json`.

> **Çıktı dizini yüzeye göre değişir (ölçüldü 2026-07-31).** `/mnt/user-data/outputs/`
> claude.ai kod-çalıştırma ortamının yoludur ve **Claude Code'da mevcut değildir**. Orada
> dizin varsa oraya yazın; yoksa kullanıcının erişebileceği kalıcı bir yere (`~/edupedia-moduller/`
> gibi) yazın ve **yolu kullanıcıya bildirin** — scratchpad'e bırakmayın, oturumla birlikte gider.

> **SVG yazarken tırnak tuzağına dikkat:** G-SVG `role="img"` (çift tırnak) arar; tek tırnaklı
> öznitelik geçerli SVG üretir ama kapıyı düşürür. Backtick sarmalayıcı kullanın —
> `svg-authoring.md §5.1`.

> **Paylaşılmaz (K2).** Sınav sorusu telifli olabilir; siteye yüklenmez, yayın teklif
> edilmez. Teslim yerel HTML'dir.

---

## 3. `exam` veri bloğu (tek soru, geriye dönük)

`curriculum` bloğuyla aynı desende: motoru değiştirmez, izlenebilirlik taşır,
`G-EXAM` tarafından okunur. Tek soruda bu şekil **geçerli kalır**. `workedId` yoksa
G-EXAM HTML'de `fadeFrom < adım` olan herhangi bir `worked` arar.

```js
exam: {
  stem: "3/4 kg elma 24 TL ise 2/3 kg elma kaç TL'dir?",  // ZORUNLU — transkribe soru
  options: ["12 TL", "14 TL", "16 TL", "18 TL"],           // opsiyonel — şıklıysa
  figure: { kind: "svg", ref: "<svg …>" },                 // opsiyonel — yeniden çizilen şekil
  source: "öğrenci fotoğrafı — okul yazılısı",             // opsiyonel (yoksa WARN)
  integrity: "sound",                     // ZORUNLU: "sound" | "flawed" | "out_of_frame"
  integrityNote: "",                      // "sound" değilse ZORUNLU
  transcriptionCheck: "tc1",              // ZORUNLU — selfExplain segmentinin id'si
  distractorAnalysis: "d1",               // opsiyonel (options varsa yokluğu WARN)
  chain: [                                // ZORUNLU, boş olamaz
    { concept: "birim fiyat",
      outcomeCode: "MAT.6.1.4.1",         // opsiyonel (D2'de düşer)
      mappedTo: ["t1"] },                 // ZORUNLU — segments[]'te var olmalı
    { concept: "kesirle bölme",
      outcomeCode: "MAT.6.1.4.2",
      mappedTo: ["w1"] }
  ]
}
```

**Doğru cevap `exam` / `exams[]` bloğunda tutulmaz.** İki yerde yaşar: `worked`
segmentinin son adımındaki `answer` ve çeldirici analizi `mcq`'sünün `correctIndex`'i.
Tek kaynak.

> **Bilinen sızıntı (yeni değil):** `MODULE_DATA` HTML kaynağındadır; kaynağı açan
> öğrenci `answer`/`correctIndex` görebilir. Bu mevcut tüm `mcq` modülleri için de
> geçerlidir, EXAM modunun getirdiği bir gerileme değildir. Çözülmeyecek.

### 3.1 Çoklu: `topics[]` + `exams[]`

`exams` yalnız `length ≥ 1` ise kullanılır. Boş `exams: []` yok hükmündedir; varsa
`exam:{}` legacy yolu işler. Tek soru yazarı isterse `exams: [{…}]` + `topics: [{…}]`
de yazabilir.

```js
topics: [
  { id: "t-kesir", title: "Kesirle çarpma",
    chain: [
      { concept: "birim fiyat", outcomeCode: "MAT.6.1.4.1", mappedTo: ["t1"] }
    ] }
],
exams: [
  { id: "q1", topicId: "t-kesir",
    stem: "…",
    options: ["…"],          // opsiyonel
    figure: { kind: "svg", ref: "<svg …>" },
    source: "öğrenci fotoğrafı",
    integrity: "sound",      // sound | flawed | out_of_frame
    integrityNote: "",
    transcriptionCheck: "tc-q1",
    distractorAnalysis: "d-q1",
    workedId: "w-q1" }       // ZORUNLU (çokluda); bu id'li worked fadeFrom taşımalı
]
```

- Her `exams[]` öğesi bir `topicId` çözer. Zincir **konuda** yaşar; soru öğesinde
  `chain` yok.
- Çokluda `_exam_worked_ok` (modülde herhangi bir worked) **yasak**: her öğe kendi
  `workedId` si üzerinde `fadeFrom < adım` şart.
- `mode: "EXAM"` kalır. Motor bu blokları okumaz.

---

## 4. Segment kurgusu (tek soru)

Tek soruda 11 segmentlik kurgu **aynen** kalır.

```
 1  teach        "Soruyu birlikte okuyalım"
                  → exam.stem + exam.options + exam.figure (yazar-SVG)
 2  selfExplain  "Soruyu böyle okudum. Bir yeri farklıysa aşağıya yaz."
                  ← TRANSKRİPSİYON KAPISI — exam.transcriptionCheck bu id'yi gösterir
 3  hook         "Sence bunu çözmek için hangi bilgi gerekli?"   resolvesIn → 4
 4  teach + etkileşim   zincir halkası 1  (kitaptan; KB2.x becerisine eşlenmiş)
 5  teach + etkileşim   zincir halkası 2
 6  brainbreak   (≥6 segment ise — module-architecture.md §3 kuralı)
 7  worked       SORUNUN KENDİSİ, adım adım — fadeFrom ile son adım(lar) öğrenciye
 8  selfExplain  "Neden bu adımda böyle yaptık?"  (notsuz, cezasız)
 9  mcq          ÇELDİRİCİ ANALİZİ — exam.distractorAnalysis bu id'yi gösterir
10  mcq          TRANSFER — aynı zincirle 2 izomorfik soru
11  checkpoint
```

### 4.1 Neden 2. adım `mcq` değil `selfExplain`

`G-INTERACT` her `stem:` için bir `correctIndex:` şart koşar. "Soruyu doğru mu okudum?"
sorusunun doğru cevabı **yoktur** — `mcq` yapılırsa ya kapı düşer ya da *"Hayır, şurası
farklı"* diyen öğrenci **yanlış** sayılır (G-WELLBEING ihlali).

`selfExplain` notsuz ve cezasızdır; motor "Devam"ı koşulsuz etkin bırakır. Öğrenci
farkı yazabilir de yazmayabilir de. `modelExplanation` alanına düzeltme yönergesi konur:
*"Bir yeri farklıysa doğrusunu yazıp bana tekrar sor — düzeltilmiş soruyla yeni bir
modül üretirim."*

### 4.2 Neden 7. adımda `fadeFrom` zorunlu

Bu, EXAM modunun **varlık sebebidir**. `worked` segmenti `fadeFrom` ile kapatılır;
cevap hiçbir zaman doğrudan verilmez, öğrenci son adımı kendisi tamamlar.

`G-EXAM` bunu **zorunlu kılar** (`fadeFrom < steps.length`, yoksa FAIL). Ödev-çözme
makinesi olmamak bir üslup tercihi değil, **yapısal bir kısıttır** — modelin iyi
niyetine bırakılmaz.

### 4.3 Neden 9. adım (çeldirici analizi)

Yeni nesil sorularda çeldirici genellikle **doğru ama ilgisiz** bilgidir ve DEHB'li
öğrenci için en zorlayıcı noktadır. Geri bildirim "yanlış" demekle yetinmemeli,
**neden ilgisiz olduğunu** açıklamalıdır (`newgen-question-design.md` §3;
`adhd-pedagogy.md` Ö4).

### 4.4 Çoklu kurgu (sıkıştırılmış)

```
  hook            "Bunlar hangi bilgiyi istiyor?"          // bir kez
  ── konu kümeleri (sırayla) ──
    teach+etkileşim   zincir halkaları (2–4; chain.mappedTo)
    ── kümenin her sorusu ──
      teach           transkribe kök + şıklar + yazar-SVG
      selfExplain     "Böyle okudum"   ← transcriptionCheck
      worked          bu soru, fadeFrom zorunlu
      selfExplain     "Neden bu adım?"
      mcq             çeldirici (yalnız şıklıysa)
    checkpoint        konu sonu
    brainbreak        ≥6 segment kuralı; kümeler arası
  mcq             transfer — konu başına EN FAZLA bir, soru başına değil
  checkpoint      kapanış; wellbeing: sınav/ödev anı aracı değil
```

Transfer’in soru başına tekrarı yasak: uzunluk + ödev-makinesi riski. G-FLOW soru
sayısını sınırlamaz; tempo `module-architecture.md` ≥6 segmentte `brainbreak` + konu
sonu `checkpoint`.

---

## 5. Degrade protokolleri

| # | Durum | Davranış |
|---|---|---|
| **D1** | **Soru bozuk** — iki doğru şık, eksik veri, çelişkili öncül | `integrity:"flawed"` + `integrityNote`. `worked` yerine **tanı segmenti**: sorunun nesinin bozuk olduğu açıklanır. Zincir anlatımı **yine yapılır** (konu öğrenilir), ama **uydurma cevap üretilmez**. Öğrenci "ben anlamadım" sanmasın diye bu açıkça söylenir. Çokluda yalnız **o öğe** etkilenir; diğer sorular devam eder. |
| **D2** | **Kazanım bulunamıyor** | `chain[].outcomeCode` düşer; `curriculum` bloğu EXAM modunda **opsiyoneldir** → G-CURRICULUM tetiklenmez. Kullanıcıya bildirilir: "Bu soruyu bir MEB kazanımına bağlayamadım; konuyu genel bilgiyle anlattım." |
| **D3** | **Ders kitabı yok** (3·4·7·8·11·12. sınıf — TYMM kademeli yürürlüğü) | `verification.frame_source.kind:"program"` + `verdict:"supported_by_source"` (egitim-kaynak; `license` **zorunlu**). Yeni kural yok — `curriculum-integration.md` §6.1 dalı aynen geçerli. |
| **D4** | **Soru çerçeve üstü** — olimpiyat, ileri yayınevi sorusu | `integrity:"out_of_frame"` + `integrityNote`. Soru **yine çözülür**, açık not eklenir: "Bu soru 7. sınıf çerçevesinin üstünde; çözümü 9. sınıfta gelen X kavramını gerektiriyor." |
| **D5** | **Fotoğraf okunamıyor** | SOR, tahmin etme. Kısmi okunuyorsa neyin belirsiz olduğu tam olarak söylenir. |

### 5.1 EXAM ile CURRICULUM farkları (normatif)

| Kural | CURRICULUM | EXAM |
|---|---|---|
| `curriculum` bloğu | **zorunlu** | **opsiyonel** (D2) |
| `verification.scope.in_frame:false` | **üretimi durdurur** | **durdurmaz** (D4) |
| Yayın teklifi | üretim sonrası sorulur | **teklif edilmez** (K2) |
| `exam` / `exams[]` | yok | **zorunlu** (`exam:{}` veya dolu `exams[]`) |

**D4 istisnasının gerekçesi:** CURRICULUM modunda `in_frame:false` üretimi durdurur,
çünkü orada model *neyi üreteceğini kendi seçer* ve çerçeve dışına taşması bir hatadır.
EXAM modunda soru **verilidir** — seçim yoktur. Öğrencinin önüne gelmiş bir soruyu
"çerçeve dışı" diye reddetmek işe yaramaz. Doğru davranış reddetmek değil, **dürüstçe
etiketleyip çözmektir**.

---

## 6. G-EXAM kapısı

Koşullu: `mode:"EXAM"` **veya** `exam:{}` **veya** dolu `exams:[]` varsa tetiklenir.

**FAIL (legacy `exam:{}`):** `exam` bloğu yok · `stem` boş · `transcriptionCheck` yok veya
var olmayan bir id'yi gösteriyor · `fadeFrom < adım sayısı` olan `worked` yok · `chain[]`
boş veya halkalarda `mappedTo` eksik · `mappedTo` id'si `segments[]`'te yok · `integrity`
geçersiz · `integrity` "sound" değilken `integrityNote` boş

**FAIL (`exams[]`):** her öğe için aynı stem/integrity/transcriptionCheck kuralları +
**kendi** `workedId` üzerinde fadeFrom < adım + `topicId` `topics[]`'te + konu `chain`
dolu ve `mappedTo` gerçek id. Bir öğenin FAIL'i kapıyı düşürür; mesaj o öğenin id'sini
taşır. Mode EXAM ama ne `exam:{}` ne dolu `exams[]` → FAIL.

**WARN:** öğede `source` beyanı yok · şık var ama `distractorAnalysis` yok ·
`exams.length > 4` (yumuşak tavan; FAIL değil)

**DENETLEYEMEZ — dürüst sınır.** Validator çevrimdışıdır, MCP erişimi yoktur ve
`MODULE_DATA`'yı parse etmez (salt regex — G-CURRICULUM/G-VERIFY ile aynı sınır):
transkripsiyonun fotoğrafa sadık olduğunu, çözümün **doğru** olduğunu, zincirin
eksiksiz olduğunu, `outcomeCode`'un gerçek bir kazanım olduğunu **ölçemez**.

**Kapı beyanın BİÇİMİNİ ölçer, içeriğini değil.** Doğruluk yargısı modelindir ve insan
denetimine tabidir. Değeri şudur: zinciri iddia etmek, her halkayı bir segmente
bağlamayı zorunlu kılar; çokluda bir sorunun açık cevabı diğerini “çözülmüş” saydırtmaz.

---

## 7. Sınırlar

1. **Sınav/ödev sırasında kullanım için değildir.** Öğrenme sonrası araçtır; modül
   kapanışında wellbeing dilinde (suçlayıcı olmayan) bir not bulunur.
2. **Yumuşak tavan ~4 soru.** 5+ için uyarı; üretim aynı HTML'de devam eder (K7).
   Çoklu-soru hata örüntüsü istatistiği bilinçli olarak kapsam dışıdır.
3. **MEB dışı müfredat kapsam dışıdır.** IB/Cambridge sorusunda çerçeve kurulamaz;
   dürüstçe söylenir. Tüm girdi MEB dışıysa üretim durur; karışıksa MEB olanlar
   üretilir, diğerleri `out_of_frame`.
4. **Transkripsiyon insan denetimine tabidir** — 2. segment tam da bunun içindir.
5. **Fotoğraf gömülmez** (K4). Motorda raster taşıyıcı yoktur.
