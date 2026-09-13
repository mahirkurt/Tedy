---
name: carbon-edupedia
description: >-
  Kaynak metinden veya MEB Türkiye Yüzyılı Maarif Modeli kazanımlarından DEHB-dostu,
  IBM Carbon v11 tabanlı, erişilebilir tek dosyalı etkileşimli ders, quiz, oyun ve
  flashcard üretir.
license: MIT
metadata:
  version: 3.11.0
  last_updated: 2026-08-18
  manifest: ./skill-manifest.yaml
---

# Carbon Edupedia — DEHB-Odaklı Etkileşimli Öğrenim Modülü Üreticisi

## 1. Amaç — Purpose / What This Skill Does

Sağlanan kaynak materyali (ders kitabı bölümü, ders notu, konu metni, müfredat
kazanımı) **tek-dosya, tarayıcıda çalışan, etkileşimli bir HTML öğrenim
modülüne** dönüştürür. Modül iki katmanı iç içe örer:

1. **Öğretim katmanı (teach)** — Kaynağa sadık, kapsamlı, izah edici, görsel
   açıdan zengin konu anlatımı. "Eğlenceli" olması derinlikten ödün vermez.
2. **Etkileşim katmanı (engage)** — Anlatım parçaları arasına serpiştirilmiş
   oyunlar, quizler, yarışmalar, flashcard'lar; XP/rozet ekonomisi, anında
   geri bildirim, ilerleme rayı ve mola (brain-break) noktaları.

Çıktı tamamen **IBM Carbon Design System v11** token sistemiyle, IBM Plex
tipografisiyle biçimlendirilir; **emoji içermez** ama Carbon ikonları,
piktogramları ve özgün SVG çizimlerle zenginleştirilir; WCAG 2.1 AA ve
DEHB-dostu etkileşim ilkelerine uyar.

Bu yetkinlik **ders-bağımsızdır** (fen, matematik, sosyal bilgiler, Türkçe,
tarih, biyoloji, fizik, kimya, coğrafya...) ve **öğrenci profili
yapılandırılabilir** (varsayılan: 12 yaş, ortaokul, DEHB tanılı).

## 2. Ne zaman kullanılır — When To Invoke / Tetikleyiciler

**Tetikleyici ifadeler (TR/EN):**
- "etkileşimli ders/öğrenim modülü", "interaktif ders", "oyunlaştırılmış ders"
- "ADHD/DEHB için ders/çalışma", "dikkat eksikliği olan çocuk için ders"
- "konu anlatımı + oyun", "konuyu oyunla öğret", "quiz oyunu", "yarışma hazırla"
- "flashcard hazırla", "eğitici oyun", "interactive lesson", "learning game"
- "şu konuyu eğlenceli/etkileşimli hale getir"

**Sınav sorusu tetikleyicileri (EXAM modu):**
- bir veya birden fazla sınav sorusunun **fotoğrafı** yüklendi veya soru metni yapıştırıldı
- "bu soruyu çöz", "bu soruları çöz", "bu soruyu açıkla", "bunu nasıl yaparım"
- "sınav sorusu", "test sorusu", "deneme sorusu", "yazılı sorusu", "yazılı kâğıdı"
- "bu soruyu anlamadım", "bu soru neden B değil"
- Bu sinyallerde **`references/exam-solving.md` okunur ve akışın tamamı uygulanır**.

**Müfredat MCP tetikleyicileri (Türkiye MEB / Maarif Modeli):**
- "müfredata uygun ders/modül", "MEB kazanımına göre", "kazanımla çalışma"
- "Türkiye Yüzyılı Maarif Modeli", "Maarif Modeli", "öğretim programına göre"
- kazanım kodu verilmesi (örn. "FB.5.3.1.1 ile modül yap")
- "X. sınıf <ders> müfredatından <konu>" (ders + sınıf + konu birlikte)
- "bu konuya hangi kazanımlar denk geliyor?"
- Bu sinyallerde **Müfredat MCP** çağrılır (bkz. `references/curriculum-integration.md`).

**Bu yetkinliği KULLANMA, şunları kullan:**
- Yalnız Fransızca içerik, React artifact → `francais-coach`
- Statik baskıya hazır doküman (etkileşim yok) → `carbon-html-report`
- Sunum/slayt → `carbon-pptx` veya `pptx`
- Genel amaçlı React UI (eğitim dışı) → `frontend-design`
- Word/Excel/PDF deliverable → `docx` / `xlsx` / `pdf`

## 3. Çıktı sözleşmesi (Output specification)

Yetkinlik **her zaman** şunu üretir:
1. **Tek** bir `.html` dosyası — tüm CSS/JS/font/görsel kaynakları satır içi veya
   `data:` URI'dır. CDN, ağ veya göreli/yerel runtime bağımlılığı yoktur; çevrimdışı açılır.
2. **Teslim yüzeye göre** (§8 Adım 6): **Claude Code'da** `/mnt/user-data/outputs/`,
   **Cursor'da** kullanıcının çalışma alanındaki seçilen çıktı dizini altında açıklayıcı
   kebab-case adla kaydedilir (örn. `hucre-ve-organeller-fen-7-modul.html`);
   **claude.ai'de** native dosya sistemi yoktur → HTML sohbet artefaktı olarak sunulur.
   Plugin yayınlamaz.
3. Modern tarayıcıda açılır, etkileşimler (quiz/oyun/flashcard) **JavaScript ile
   gerçekten çalışır**; durum bellekte tutulur.
4. **Emoji içermez.** Tüm görsel anlam ikon, piktogram ve SVG çizimle taşınır.
5. **IBM Carbon v11** token sistemine ve IBM Plex tipografisine uyar.
6. WCAG 2.1 AA: klavye erişimi, ARIA, `prefers-reduced-motion`, ≥44px hedef.
7. **Run-manifest'i DİSKE yazar — yerel plugin yüzeylerinde (Claude Code/Cursor).**
   (claude.ai'de native dosya sistemi yoktur; orada HTML sohbet artefaktıdır.) HTML'in
   yanına, **aynı ad + `.manifest.json`** ile (aynı
   dizin; örn. `hucre-ve-organeller-fen-7-modul.html` →
   `hucre-ve-organeller-fen-7-modul.manifest.json`; sabit `run_manifest.json` adı KULLANILMAZ).
   İçerik `../../shared/run-manifest-schema.json`'a uyar: `run_id`, `ts`, `plugin_version`,
   `requested_scope`, `connector_call_ledger`, `single_shot_enforced:true`,
   `canonical_artifacts`, `tier2_status`, `deliverable_path`, `caveats` ve opsiyonel
   `quality_gates`. Kalite kapılarının OTORİTESİ
   yerel `scripts/validate_module.py`'dir. `quality_gates` yazılacaksa `python
   scripts/validate_module.py --json <html>` çıktısının BİREBİR kendisi olmalı — elle yazma,
   konsol raporundan transkribe, hiçbir kapıyı PASS'a yükseltme yok. `--json` çıktısı yalnız
   `PASS`/`FAIL`/`WARN`/`SKIPPED` durumlarını içerir; koşturulmayan kapı kendiliğinden
   `SKIPPED` gelir (asla `PASS`). `run_id` **NORMATİF KALIP** ile (verbatim, başka bir
   biçim KULLANMA): `Edupedia-YYYYMMDD-<ders>-<konu>-v<N>` — ör. `Edupedia-20260706-fen5-hucre-v1`
   (`<ders>`/`<konu>` yalnız küçük harf/rakam/tire, `<N>` sürüm tamsayısı; şema kısıtı
   `../../shared/run-manifest-schema.json` `properties.run_id.pattern`).
   Bkz. `../../shared/canonical-cache-contract.md §1`.

> **Neden tek-dosya etkileşimli HTML, React değil?** Claude.ai artifact ortamı
> React'te yalnız Tailwind çekirdek sınıflarına izin verir; Carbon token sistemi
> CSS özel değişkenleriyle HTML'de tam ve sadık biçimde uygulanır. Tek dosya
> ayrıca veliye/öğretmene kolay paylaşım ve çevrimdışı kullanım sağlar.

## 4. DEHB-öncelikli tasarım felsefesi (özet)

Bu yetkinliğin entelektüel çekirdeği **kanıta dayalı DEHB öğretim tasarımıdır**.
Bir modül üretmeden önce **mutlaka** `references/adhd-pedagogy.md` dosyasını
okuyun. Çekirdek ilkeler (tam gerekçe ve kaynaklar referansta):

- **Parçalama (chunking) / mikro-öğrenme** — anlatım 3–6 dakikalık birimlere
  bölünür (çalışma belleği + bilişsel yük kuramı).
- **Sık aktif yanıtlama (high OTR)** — pasif okuma yerine sürekli tıklama/yanıt.
- **Anında geri bildirim + ödül** — DEHB'de dopaminerjik ödül işleme ve gecikme
  itimi (delay aversion); ödül gecikmeden verilir.
- **Yürütücü işlev dışsallaştırma** — açık hedefler, ilerleme rayı, "neredeyim"
  yönelimi, görünür zaman (Barkley modeli).
- **Düşük dış yük + yüksek uyarılma dengesi** — temiz Carbon düzeni (dikkat
  dağıtıcıyı azaltır) + canlı aksan/hareket/piktogram (uyarılmayı korur).
- **Özerklik ve seçim** — öz-belirleme kuramı; öğrenci yol/konu seçebilir.
- **Çoklu temsil (UDL + ikili kodlama)** — görsel + sözel; bol piktogram/SVG.

## 5. Aşamalı açığa çıkarma — Hangi referansı ne zaman okumalı

Modülü ezberden üretmeyin; Carbon token kayması ve pedagoji ihlalleri kolay
hatalardır. İlgili referansı **emisyondan önce** okuyun.

| Referans | Ne zaman okunur |
|---|---|
| `references/adhd-pedagogy.md` | **Her modülden önce** (zorunlu). Kanıt tabanı, mola/ödül/parçalama ilkeleri. |
| `references/module-architecture.md` | Modülün omurgasını ve segment akışını planlarken. `MODULE_DATA` şeması. |
| `references/interaction-patterns.md` | Quiz/oyun/yarışma/flashcard mekaniklerini seçer ve doldururken. |
| `references/carbon-child-system.md` | Renk/tip/spacing/hareket token'larını ve çocuk-dostu Carbon uyarlamasını uygularken. **v2: otorite-doğrulanmış** (`@carbon/themes@11.75.0`), etkileşim-durumu token'ları, tam hareket/spacing matrisi, resmî tag-çifti aksanları. |
| `references/figma-carbon-interop.md` | **Opsiyonel görsel QA:** Carbon v11 Figma kütüphaneleri üzerinden Figma MCP doğrulaması (get_libraries → search_design_system → get_variable_defs), Figma↔`--cds-*` eşleme tablosu, sapma triyajı, `figma-forge` composability. |
| `references/icon-pictogram-svg.md` | İkon/piktogram seçer veya özgün SVG çizim üretirken. |
| `references/svg-authoring.md` | Tema-duyarlı/erişilebilir SVG figür ve grafik (`vizChart`, `svgFigure`) üretirken; SVG arketipleri. |
| `references/color-system.md` | İşlevsel renk rolleri, wayfinding aksanı, kontrast/CVD kuralları. |
| `references/subject-packs.md` | Derse-özel güçler: kimlik aksanı + Matematik / Fen / Sosyal / Dil paketleri (etiketli diyagram, ilişki akışı, kavram kartları, satır-arası çözümleme, çekim tablosu). |
| `references/audio-system.md` | İşitsel geri bildirim (earcon) tasarımı, kanıt ve sorumlu kullanım; ses + görsel oyunlaştırma. |
| `references/curriculum-integration.md` | **Müfredat MCP entegrasyonu — CURRICULUM modunda ZORUNLU, §3 akışının TAMAMI** (kullanıcı sözleşmesi, 2026-07-17): 21 aracın orkestrasyonu; **Adım 0 sınıf+ders KAPISI** (koddan çıkarma — doğrula), kazanım çekme, **Adım 3 ÇERÇEVE: ders kitabını AÇ** (105'in 103'ü tam metin — çerçeve üretimin sınırıdır), **beceri (KB2.x) → etkileşim deseni haritalama tablosu**, `curriculum` şeması, **§2.1 görsel önceliği: kitabın figürü birincil / yazar-SVG yedek**, **Adım 5.5 + §6.1 `verification` bloğu** (kapsam + doğruluk dayanağı → G-VERIFY), **Adım 5.6 öğrenci yüzeyi nihai dil (G-VOICE)** — kitaba/sayfaya meta-atıf yok, provenans + G-CURRICULUM, hata/geri-dönüş. |
| `references/exam-solving.md` | **EXAM modunda ZORUNLU — akışın TAMAMI.** Fotoğrafı çekilen/yapıştırılan bir veya birden fazla sınav sorusunu çözen modül: K1–K8, transkripsiyon → kümeleme → sınıf/ders kapısı → konu başına zincir → çöz → kurgu → teslim; `exam:{}` (tek) veya `topics[]`+`exams[]` (çoklu); tek soruda 11 segment, çokluda sıkıştırılmış kurgu; D1–D5 öğe bazında. Yayın bu modda **teklif edilmez** (telif). |
| `references/newgen-question-design.md` | Modüle **"yeni nesil" / LGS tarzı** soru bloğu eklerken — uyaran-temelli muhakeme taksonomisi, bilişsel eşleme, yazım reçetesi. Ön koşul: `adhd-pedagogy.md` + `interaction-patterns.md`. **Kapsam notu:** bu blok tema kazanımının **ötesinde** ileri bir katmandır, yerine geçmez — CURRICULUM modunda çerçeve kapısına (§6.1 `scope`) yine tabidir. |
| `references/content-enrichment.md` | İçerik zenginleştirme kaynağı/tekniği seçerken (Wikidata olgu-çipi, Wikimedia PD/CC-BY görsel, native MathML, çapraz-oturum aralıklı-tekrar veri modeli) veya PhET/GeoGebra/Desmos/Khan/EBA/Açık Ders gibi bir kaynağı gömme isteği geldiğinde — lisans/entegrasyon kısıtları + dürüst "yapılamaz" listesi + dyslexia-font miti. |
| `references/carbon-excellence.md` | Görsel-yoğun bir modül (hero, `sim`, `conceptMap`, `vizChart`, çok kartlı düzen) üretirken veya gözden geçirirken — Carbon estetik mükemmelliği: 15-madde uzman-vs-jenerik checklist (2x grid, en-boy oranı, layer-elevation, koreografi, expressive/productive tip-seti, veri-viz palet, ikon/piktogram disiplini); **G-CARBON-GRID** doğrulayıcı kapısının normatif kaynağı. |
| `references/gamified-flows.md` | Oyunlaştırma/motivasyon akışı planlarken — 4 akış şablonu (Keşif Döngüsü, Sefer, Antrenman, Birlikte Odak), her biri segment-dizisi eşlemesiyle; merak-boşluğu/hedef-gradyanı/uyarlanır-zorluk/tempo-diski mekanikleri + ADHD gerekçesi; atıflı YAPMA listesi. **G-FLOW** doğrulayıcı kapısının normatif kaynağı. |

## 6. Modlar (Modes)

Toplam **dokuz mod** vardır. Varsayılan **MODULE**. Kullanıcı talebine göre seçin:

| Mod | Çıktı | Ne zaman |
|---|---|---|
| **MODULE** (varsayılan) | Tam modül: öğretim + etkileşim katmanları iç içe, özet ekranı | "şu konuyu öğret + oyunlaştır" |
| **QUIZ** | Bağımsız quiz/yarışma; XP, süre, sıralama | "quiz/yarışma hazırla" |
| **FLASHCARDS** | Aralıklı tekrar (spaced repetition) flashcard destesi | "flashcard hazırla", "kelime/terim ezberi" |
| **GAME** | Tek odaklı oyun (eşleştirme, sıralama, gruplama, vb.) | "şu konu için oyun" |
| **EXPLAINER** | Görsel-ağırlıklı zengin anlatım; hafif oyunlaştırma | "detaylı konu anlatımı (görselli)" |
| **ASSESSMENT** | Tanılayıcı/kontrol noktası; ustalık (mastery) takibi | "ön/son test", "seviye ölç" |
| **SERIES** | Çok modüllü öğrenme yolu (birden çok HTML veya tek dosyada bölümler) | "bütün üniteyi modüle çevir" |
| **CURRICULUM** | **Müfredat-temelli tam modül**: MEB kazanım kodundan veya ders+sınıf+konudan üretilir; kazanım çekilir, resmî beceri (KB2.x) etkileşime haritalanır, `curriculum` provenans bloğu doldurulur, G-CURRICULUM ile doğrulanır | "müfredata uygun ders", "FB.5.3.1.1 ile modül", "5. sınıf fen müfredatından hücre" |
| **EXAM** | **Sınav sorusu çözme modülü**: fotoğrafı çekilen veya yapıştırılan bir veya birden fazla soru transkribe edilip yeniden inşa edilir; konu başına kavram zinciri öğretilir; her soru kendi `worked` + `fadeFrom` ile çözülür (cevap asla doğrudan değil); `exam:{}` veya `topics[]`+`exams[]` doldurulur, G-EXAM ile doğrulanır | "bu soruyu/soruları çöz", "sınav sorusu", soru fotoğrafı yüklendi |

**Müfredat-duyarlılık tüm modlarda opsiyoneldir.** CURRICULUM ayrı bir mod
olmasının yanında, yukarıdaki **herhangi bir mod** (MODULE/QUIZ/FLASHCARDS/...)
Müfredat MCP'sinden kaynak çekebilir ve `curriculum` bloğu taşıyabilir. Tetikleyici
geldiğinde (`§2 Müfredat tetikleyicileri`) önce `references/curriculum-integration.md`
okunur; mod CURRICULUM değilse de kazanım/beceri katmanı eklenebilir.

Mod seçimi yalnız oyunlaştırma yoğunluğunu ve segment karışımını ayarlar;
**kaynak-sadakati ve Carbon/erişilebilirlik kuralları tüm modlarda geçerlidir.**

## 7. Kaynak-sadakati kuralı (Content Fidelity) — KRİTİK

Modül bir **bilgi aktarım** ve **pedagojik dönüşüm** ürünüdür. Sağlanan kaynak
**tek doğruluk kaynağıdır**. `carbon-html-report`'un bijektif kuralından farklı
olarak, çocuğa öğretmek için *pedagojik dönüşüme* izin verilir — ama bu dönüşüm
sıkı sınırlar içinde kalır.

**İzin verilen pedagojik dönüşümler:**
- Cümle yapısını ve kelime dağarcığını yaş düzeyine sadeleştirme (anlam korunur).
- İçeriği segmentlere bölme, yeniden sıralama, parçalama.
- Kaynaktaki olguları quiz sorusu/cevabı, eşleştirme çifti, flashcard'a çevirme.
- Kaynaktaki kavramlar için açıklayıcı **görsel/şema/piktogram** üretme.
- Açıkça pedagojik (illüstratif) analoji/örnek ekleme — kaynak olgusu gibi
  sunulmamak ve kaynağı çarpıtmamak şartıyla.

**Yasak (uydurma / KURAL İHLALİ):**
- Kaynakta olmayan olgu, sayı, tarih, isim, tanım eklemek.
- Kaynağı çürüten/çelişen ifade veya quiz "tuzak" cevabı üretmek.
- Kaynaktaki bir kısıtı/uyarıyı atlamak (basitleştirme adına bile).
- Bir kısaltmayı/terimi kaynak tanımlamıyorsa "açımlayarak" tanım uydurmak.
- Analojiyi/örneği kaynağın asıl ifadesiymiş gibi sunmak.

**Kaynak yetersizse:** Modülü "doldurmak" için olgu uydurmayın. Eksikliği
kullanıcıya bildirin ("Kaynak X konusunda yeterli ayrıntı içermiyor; ek
materyal sağlayabilir misiniz?") veya iyi yerleşik müfredat konularında kendi
güvenilir bilginizi kullanırken bunu **açıkça etiketleyin** ve kullanıcıdan
doğrulama isteyin. Akademik titizlik kaynak-öncelikli akışı zorunlu kılar.

**Quiz/yarışma doğrulanabilirliği — ters içerik denetimi (reverse content audit):**
Üretilen her sorunun doğru cevabı kaynaktan **izlenebilir** olmalı. Mümkünse her
soruya kaynak içi dayanak notu (segment id) bağlayın; `scripts/validate_module.py`
kapsam kancalarını kontrol eder. Emisyondan önce **HTML→source provenance** geçişi
uygulayın: modüldeki her olgusal iddia (anlatım cümlesi, quiz cevabı, eşleştirme
çifti) kaynakta bir dayanağa sahip olmalı — *every claim grounded; no fabrication;
bidirectional content check*. Bu, tek-yönlü (yalnız atlamayı engelleyen) bir kuralın
açık bıraktığı kısaltma açımlaması, parantez içi gloss ve yorumsal çerçeveleme
sızıntısını kapatır.

**Öğrenci yüzeyi — orijinal ve nihai dil (KRİTİK, G-VOICE):**
Kitap/program **yazarın** doğruluk kaynağıdır; öğrenciye görünen metin o kaynağı
*anımsatmaz*. `body`, `stem`, `explanation`, `recap`, `prompt`, `keyTerms`,
`instructions`, `question` bu modülün kendi tamamlanmış (nihai) cümleleridir —
tanım tanımdır, "kitabın tanımı" değil. Provenans yalnız `verification` +
`meta.sourceCitation` + `sourceRef` içinde kalır (öğrenci bunları görmez).

Yasak (öğrenci yüzeyinde):
- "kitabın tanımı", "kitaptaki yazıyı hatırla", "kitaba göre", "ders kitabında"
- "ünitede gördüğün / öğrendiğin", "sayfa 42'de", "kaynakta belirtildiği gibi"
- Kitabı hatırlatan yarım dil; kitaptan kopyalanmış cümleyi atıfla sarmalama

Doğru: kavramı bu modülün sesiyle, yaş düzeyine sadeleştirilmiş tam cümlelerle
yeniden yaz. Geri getirme meşrudur ("Enerji santralini hatırla") — yasak olan
kitaba bağlanan hatırlatmadır. PhET CC BY-NC künyesi lisans atfıdır, kitap-meta
değildir; görünür kalır. Türkçe dersinde edebi eser olarak "kitap" ("bu kitabın
yazarı") meşrudur.

## 8. İnşa iş akışı (Build workflow)

Bir modül üretirken bu sırayı izleyin:

**Adım 0 — Niyet ve girdi.** Kaynağı belirleyin (kullanıcının verdiği metin,
yüklenen dosya, ya da belirtilen konu+müfredat). Yoksa isteyin. Modu, dersi,
sınıf düzeyini, öğrenci profilini (varsayılan: 12 yaş ortaokul DEHB) ve hedef
süreyi netleştirin.

**Adım 0.5 — Müfredat MCP akışı (Müfredat sinyali varsa ZORUNLU).** Kullanıcı sinyali
Müfredat-temelli ise (kazanım kodu, "MEB kazanımına göre", ders+sınıf+konu, "Maarif
Modeli" — bkz. §2) **önce `references/curriculum-integration.md` okuyun ve §3'teki
akışın TAMAMINI uygulayın** — bu akış kullanıcı sözleşmesidir (2026-07-17), seçmeli
bir zenginleştirme değil:

- **Adım 0 (KAPI):** sınıf+ders kesinleşmeden üretim başlamaz. Kod verildiyse koddan
  **çıkarma — MCP'den DOĞRULA**; yoksa/belirsizse **SOR**.
- **Adım 3 (ÇERÇEVE):** ders kitabını **AÇ** (`list_textbooks` → sayfayı bul →
  `get_document_text`). **Çerçeveyi o metin çizer** ve üretimin sınırıdır. Kitap
  yoksa/`page_count=0` → programa düş ve `frame_source.kind:"program"` yaz.
- **Adım 5.5 (DENETİM):** kapsam + doğruluk denetimini yap, `verification` bloğunu üret
  (§6.1). Dayanaksız iddia modülde kalmaz.

Görselde **kitabın kendi figürleri önceliklidir**: `search_figures` +
`get_figure` metadata/ImageContent ile Tier-2a gözlemi sağlar; yerel dosya sistemi+Python
varsa `scripts/fetch_figure.py` Tier-2b binary çıkarımını yapar (native Claude Code/Cursor).
`include_image=true` ham base64 metin vermez. Yazar-üretimli SVG **yedektir** (bkz. o
belgede §2.1; öncelik 2026-07-17'de tersine çevrildi).

MCP erişilemezse offline yola dönün ve **kullanıcıya bildirin** — üretim bloke olmaz ama
"kitaba dayandım" **denemez**. Müfredat sinyali yoksa bu adım atlanır (serbest kaynak modu).

**Adım 1 — Referansları oku.** En az `adhd-pedagogy.md` +
`module-architecture.md`. Etkileşim seçimi için `interaction-patterns.md`.

**Adım 2 — Modülü planla (semantic plan).** Kaynağı kazanımlara/öğrenme
hedeflerine ayrıştırın. Her hedef için: 1 öğretim segmenti + en az 1 etkileşim
segmenti + arada mola noktaları kurgulayın. Parçalama: hiçbir öğretim segmenti
6 dakikalık okuma/etkileşim yükünü aşmamalı. Akış kalıbı:
`teach → practice → reward → (brain-break) → teach → ...`

**Adım 3 — Tasarım katmanını seç.** `carbon-child-system.md`'den bir aksan
renk token'ı (derse göre, örn. fen=Teal 50, tarih=Magenta 60), tipografi ölçeği
ve hareket profilini belirleyin. `icon-pictogram-svg.md`'den her segmente uygun
piktogram/ikon seçin veya gereken kavram için özgün SVG çizin.

**Adım 4 — Şablondan derle.** `assets/module-template.html` dosyasını okuyun.
Bu dosya, tüm Carbon stilini ve etkileşim motorunu (engine) içeren çalışan bir
şablondur. **İçeriği üst kısımdaki `MODULE_DATA` JS nesnesini değiştirerek**
yerleştirin; aksanı/temayı ayarlayın; gerekli ek piktogram/SVG'leri satır içi
gömün. Motoru yeniden yazmayın; veriyi doldurun.

**Adım 5 — Doğrula.** `python scripts/validate_module.py
<çıktı.html>` çalıştırın. Kapılar: emoji-yok, Carbon token kullanımı, IBM Plex yüklemesi,
ARIA/erişilebilirlik asgarileri, etkileşim bütünlüğü (her quiz sorusunda doğru cevap +
açıklama), satır-içi varlık (harici bağımlılık yok), müfredat provenansı + kapsam/doğruluk
dayanağı (G-CURRICULUM + G-VERIFY), öğrenci yüzeyi nihai dil (G-VOICE). İhlalleri giderin.
Kalite kapılarının OTORİTESİ bu yerel doğrulayıcıdır (PostToolUse hook'u da aynı betiği
koşar). `--json` çıktısı manifeste gömülebilir.

> **claude.ai'de script koşmuyorsa** kapıları "PASS" diye beyan etmeyin — ölçülmemiş kapı
> ölçülmemiştir. HTML'i sohbet artefaktı olarak sunun.

**Adım 6 — Teslim (YÜZEYE GÖRE).**

Plugin yayınlamaz. Siteye yükleme, `edupedia_publish` ve `/edupedia:yayinla` **yok**.

- **claude.ai'de (dosya sistemi YOK):** HTML'i sohbet artefaktı olarak sunun.
- **Claude Code'da:** `/mnt/user-data/outputs/` altına kebab-case adla kaydedin; **aynı ad +
  `.manifest.json`** ile run-manifest'i yan yana yazın (§3 madde 7). `present_files` ile sunun.
- **Cursor'da:** kullanıcı çalışma alanında seçilen çıktı dizinine aynı HTML +
  `.manifest.json` çiftini yazın; Cursor'a özgü hook manifesti
  `hooks/hooks-cursor.json`dır.

Tüm yüzeylerde kısa bir özet + "nasıl kullanılır" notu ekleyin.

## 9. Etkileşim deseni kataloğu (özet)

Tam mekanik, veri şeması ve erişilebilirlik notları için
`references/interaction-patterns.md`. Çekirdek desenler:

- **MCQ Quiz / Yarışma** — 3–4 seçenek, anında doğru/yanlış + açıklama, XP.
- **Flashcard (aralıklı tekrar)** — çevirmeli kart, "biliyorum/tekrar et".
- **Eşleştirme (match)** — terim↔tanım, kavram↔görsel çiftleri.
- **Boşluk doldurma (fill-blank)** — bağlamda eksik kelime; ipucu desteği.
- **Sıralama (order)** — adımları/olayları doğru sıraya dizme (sürükle-bırak).
- **Gruplama (sorting bins)** — öğeleri kategorilere ayırma.
- **Zaman çizelgesi / etkileşimli görsel (hotspot)** — görsel üzerinde tıklama.
- **Mola noktası (brain-break)** — kısa hareket/nefes yönergesi (DEHB için kritik).
- **Kontrol noktası / özet** — ustalık göstergesi, rozet kasası, tekrar önerisi.

## 10. Carbon tasarım token'ları (özet)

Tam token tablosu ve çocuk-dostu uyarlama için `references/carbon-child-system.md`.
- **Tipografi:** IBM Plex Sans (gövde/başlık/**tüm UI metni, etiket ve sayaç
  sözcükleri**), IBM Plex Serif (vurgulu anlatım/matematik), IBM Plex Mono
  **yalnızca sayı, veri ve kod için** (sayaç/istatistik/yüzde/tablo rakamları,
  kod blokları). Mono font **düz metinde, etikette, eyebrow'da veya başlıkta
  asla kullanılmaz**; sayaçlarda yalnız **rakamlar** `<b>` ile sarılıp mono +
  `font-variant-numeric:tabular-nums` ile hizalanır, çevreleyen sözcükler Sans
  kalır. Ağ fontu/CDN kullanılmaz; gerekli font dosyası varsa `data:` URI olarak
  gömülür. Letter-spacing (`--ls-label:.32px`) `@carbon/type` ile birebir.
- **Renk:** Carbon v11 **White + Gray-100** tema token'ları CSS değişkeni olarak —
  yüzey/metin/kenar çekirdeği **artı** etkileşim-durumu katmanı
  (`--cds-layer-hover/active/selected-01`, `--cds-background-hover/active`,
  `--cds-border-tile/interactive`, `--cds-highlight`, `--cds-skeleton-*` vb.).
  Durum: `--cds-support-info` açık temada **#0043ce** (Blue 70 — AA-doğru),
  g100'de #4589ff. Ders aksanı tam Carbon paletinden; aksan-renkli metin **resmî
  tag token çiftleriyle** (`ACCENT_STRONG`) yazılır.
- **Spacing:** 2px tabanlı **tam** Carbon ölçeği (`--cds-spacing-01..13`);
  `--tap:48px` = Carbon size **Large**.
- **İlerleme/durum çipleri nötr ve kompakt:** sayaç ve ilerleme göstergeleri
  (örn. "Soru 1/5", "Öğrenilen 0/4 · Destede 4 kart") **gri** Carbon
  token'larıyla yazılır (`layer-01` zemin · `border-subtle` kenar ·
  `text-secondary` metin) ve küçük tutulur. **Aksan rengi yalnız
  ödül/oyunlaştırma** öğelerine ayrılır (XP çipi, seri çipi, kazanılan rozet).
  Böylece dikkat içerikte kalır; nötr durum göstergesi aksan-yük dağıtmaz.
- **Hareket:** `@carbon/motion` tam matrisi — 6 süre (`fast-01..slow-02`) ×
  6 easing (standard/entrance/exit × productive/expressive); her hareket
  `prefers-reduced-motion` ile geçersiz kılınabilir.
- **Çocuk uyarlaması:** Carbon'un dikdörtgensel dilini korurken hafif köşe
  yarıçapı (`--cds-radius`), büyük dokunma hedefleri ve canlı aksanlar — gerekçe
  referansta (düşük yük + uyarılma dengesi).

### 10.1 Token otorite zinciri + Figma doğrulama (v2.0.0)

Üç katman (uyuşmazlıkta üst kazanır):
1. **`npm @carbon/*`** (themes 11.75.0 · type 11.61.0 · motion 11.46.0 ·
   layout 11.53.0 · colors 11.52.0) — tek doğruluk kaynağı.
2. **`assets/carbon-v11-authority.json`** — sürüm-damgalı, makine-okunur anlık
   görüntü; `scripts/sync_carbon_tokens.py` (`--check` çevrimdışı diff /
   `--refresh` npm'den tazeleme) ve `G-TOKEN` kapısı bunu kullanır.
3. **Figma Carbon v11 kütüphaneleri** — opsiyonel görsel QA
   (`references/figma-carbon-interop.md`); kullanıcı dosya URL'si verirse
   `get_variable_defs` ile değer teyidi yapılabilir. Token değerinin kaynağı
   **asla** Figma değildir.

## 11. İkon, piktogram ve SVG stratejisi (özet)

Tam rehber: `references/icon-pictogram-svg.md`.
- **Carbon Icons** (`@carbon/icons`, MIT) — işlevsel UI ikonları (onay, ok,
  kapat). Şablona satır-içi SVG `<symbol>` spritetı olarak gömülür; `<use>` ile.
- **Carbon Pictograms** (`@carbon/pictograms`, MIT) — kavramsal illüstrasyonlar
  (kitap, fikir, roket, laboratuvar). Segment başlıklarını ve ödülleri süsler.
- **Özgün SVG çizim** — kaynaktaki bir kavram bespoke şema gerektirdiğinde
  (etiketli hücre, su döngüsü, sayı doğrusu), Carbon görsel diline uygun
  (2px stroke, Carbon paleti, geometrik, gradyansız) elle SVG çizin.
- **Kural:** Tüm görseller **satır içi** gömülür (çevrimdışı/güvenilir). Emoji
  asla kullanılmaz. Görseller `aria-hidden` veya uygun `role="img"`+`<title>`.

### 11.1 Tema-duyarlı SVG figür + grafik sistemi
Tam rehber: `references/svg-authoring.md`. Motorun sunduğu en güçlü araçlar:
- **`vizChart(spec)`** — veriden **çubuk/çizgi grafik** üretir; `viewBox` ile responsive,
  `--accent`/`--viz-1..5` ile tema-duyarlı, `role="img"`+`<title>`/`<desc>` ile erişilebilir,
  **animasyonsuz**. `{ type:"chart", chart:{…} }` görüntüleme segmenti veya `teach`
  içinde `visual:{ kind:"chart", … }` olarak kullanılır.
- **`svgFigure(inner, caption)`** — herhangi bir özel SVG'yi başlıklı/çerçeveli `figure.viz`'e sarar.
- **Renk token'ları** — kategorik `--viz-1..5`, anlamsal `--viz-sun/water/cloud`,
  eksen/ızgara `--viz-axis/--viz-grid`; açık+koyu temada tanımlı. **Figür SVG'de ham hex yok.**
  Metin rengini CSS verir (`.viz text` → primary; `.viz-muted` → secondary).
- **Donut** ustalık göstergesi olarak yalnız özet ekranına ayrılmıştır.
- **`vizTable(spec)`** — Carbon **DataTable** (anlamsal `<table>`: `<caption>`, `<th scope>`,
  zebra `--cds-layer-01/02`, başlık `--cds-layer-accent-01`, sayısal sütun sağa hizalı/tabular,
  satır vurgusu). `{ type:"table", table:{…} }` veya `visual:{ kind:"table", … }`.
- **`numberLine(spec)`** + **`mathExpr(src)`** — matematik paketi (aşağıda §11.3).

### 11.2 Frontend ilkeleri (rafine minimalizm)
`frontend-design` rehberiyle uyumlu, DEHB-sakin sınırı içinde: token-tabanlı renk +
**keskin tek aksan**; ayırt edici **IBM Plex** tipografisi (Sans gövde, Serif/Mono vurgu —
jenerik Inter/Arial yok); ölçülü derinlik (yüzey ritmi, ince kenarlık/gölge); **tek**
orkestre giriş animasyonu (`prefers-reduced-motion` ile kapalı); öngörülemez değil,
**niyetli ve tutarlı** kompozisyon. "AI-slop" estetiğinden (mor degrade, kalıp düzen) kaçınılır.

### 11.3 İşlevsel renk ve derse-özel güçler
- **İşlevsel renk** (`references/color-system.md`): renk **işlevle** atanır (eylem=mavi buton,
  durum=Carbon support, kategori=`--viz-1..5`, ödül=`--reward`, **odak çıpası**=aksan), nötr
  Carbon tuvali üzerinde, daima metin/ikon ile **artıklı** ve CVD-güvenli. Etkinlik türü
  başlıkta `--seg-accent` ile imlenir (wayfinding/sinyalleme). Kanıt: `adhd-pedagogy.md` §12.
- **Derse-özel güçler** (`references/subject-packs.md`): `meta.subject`/`meta.subjectKey` →
  derse-özel **kimlik aksanı** + `data-subject`. Paketler:
  - **Matematik:** `mathExpr` (üs/alt indis, kesir, kök, operatör glifleri; Plex Serif + tabular),
    `numberLine` (SVG sayı doğrusu), **`fractionBar`** (kanıta dayalı kesir/oran **çubuk** modeli —
    tek kesir · kesir toplamı · oran; daire değil, §11.5), geometri SVG kuralları, Carbon değer tablosu.
  - **Fen Bilimleri:** `labeledFigure` (numaralı çağrı-iğneli etiketli diyagram + sıralı açıklama
    listesi — hücre/bitki/devre), `relationFlow` (süreç zinciri), `vizChart`/`vizTable`; `mathExpr`
    kimyasal alt indis için (H₂O, CO₂).
  - **Sosyal Bilimler** (sosyal bilgiler · din kültürü ve ahlak · yurttaşlık/insan hakları):
    `relationFlow` (sebep-sonuç / kavram zinciri), `infoCards` (kavram/değer/hak kartları),
    `timeline`, `vizTable`.
  - **Dil Bilimleri** (Türkçe · İngilizce · Fransızca): `glossSentence` (satır-arası çözümleme +
    **rol/cinsiyet renk-kodu**, renk daima etiketle birlikte), `dialogue` (iki konuşmacılı),
    `infoCards` (artikel/kelime), `vizTable` (çekim), `flashcards`.
  - Kanıt temeli `adhd-pedagogy.md` §12–§13'te (renk-kodu, sinyalleme, kavram haritası, ikili kodlama).

### 11.4 İşitsel geri bildirim ve oyunlaştırma sesi
- **Earcon katmanı** (`references/audio-system.md`): Web Audio ile sentezlenen kısa, hoş-değerlikli,
  düşük sesli olay-earcon'ları — `correct` (doğru/XP), `retry` (yanlış; nazik, **cezasız**),
  `reward` (modül tamamlama), `notify` (mola/onay). Sürekli arka plan müziği/gürültüsü **yoktur**.
- **Daima görselle eşli**: ses tek başına bilgi taşımaz; sessizde/işitme engelinde tam işlevsellik.
  Doğru cevapta **XP patlaması** (+N XP çipi + sayaç nabzı), yeni rozette **kutlama** (`badge--new`).
- **Opsiyonel & güvenli**: üst çubukta hoparlör düğmesi; `prefers-reduced-motion: reduce` ise ses
  **varsayılan kapalı**; düşük ses; ilk etkileşimde `AudioContext` devreye alınır. Tüm animasyonlar
  reduced-motion duyarlı.
- Kanıt: çok-duyulu (ses+görsel) geri bildirim tercih edilir ve akışı destekler; sert/alçak-değerlikli
  ses ödülde gerilim artırır (kaçınılır); DEHB'de **kısa yeni sesler** uyarılmaya yardımcı olabilirken
  **sürekli ses** dağıtıcıdır (`adhd-pedagogy.md` §14). Doğrulama: **G-AUDIO** kapısı.

### 11.5 v1.8.0 yenilikleri — kesir/oran çubuğu · seri · sesli oku (TTS)
Üç ek, hepsi kanıt-temelli ve mevcut güvenlik kapılarıyla uyumlu:

- **Kesir/oran çubuğu (`fractionBar`)** — daire (pasta) yerine **alan/uzunluk modeli** olan bir bar.
  Üç mod: `kind:"fraction"` ({num,den}) tek kesir; `kind:"sum"` ({addends:[],den}) paydaları eşit
  kesir toplamı (otomatik denklem, örn. 3/4 + 1/4 = 1); `kind:"ratio"` ({ratio:[],labels?}) oran (örn.
  2:3, opsiyonel renkli gösterge). Her bar `role="img"` + `<title>`/`<desc>` ve yalnız Carbon/`--viz-*`
  token rengiyle çizilir (G-SVG uyumlu). Hem `teach` görseli (`visual.kind:"fraction"`) hem de bağımsız
  `fraction` segment tipi olarak kullanılabilir. Kanıt temeli `references/subject-packs.md` §2 (alan
  modeli daireden üstündür; bar modeli kesir-toplamı ve oranı görselleştirmede etkilidir — uyarı:
  yapısal görsel yalnızca dikkatli öğretimle işe yarar).
- **Seri / combo göstergesi** — ardışık doğru yanıtlarda üst çubukta CVD-güvenli bir **seri çipi**
  (`--reward-bg` zemin + metin-birincil sayı + `ic-flash`); kilometre taşlarında (3·5·8·13·21·34)
  **mütevazı** sessiz XP bonusu + kutlama earcon'u + görsel kutlama. Yanlışta seri **sıfırlanır**
  (cezalandırıcı dil **yok**; flashcard "tekrar et" seriyi düşürmez). Tüm kutlama animasyonları
  `prefers-reduced-motion` duyarlıdır. Kanıt: oyunlaştırma öğesi olarak ilerleme/seri geri bildirimi
  motivasyonu destekler (Sailer 2019, `adhd-pedagogy.md` §13).
- **Sesli oku (TTS)** — `teach`, soru kökü, `gloss`, `dialogue` ve `flashcard` arkasında **opsiyonel**
  "Oku" düğmeleri; `speechSynthesis` ile. **Varsayılan KAPALI**, üst çubuk kulaklık düğmesiyle açılır;
  **otomatik okuma yoktur**; aynı düğmeye yeniden basınca durur, mod kapanınca konuşma iptal edilir
  (`.cancel`). Dil otomatiktir: öğretim metni öğretim dilinde (varsayılan `tr-TR`), hedef-dil içeriği
  (gloss/diyalog/dil-flashcard'ları) ders konusundan türetilir (Fransızca→`fr-FR`, İngilizce→`en-US`)
  ya da `spec.lang`/`card.lang`/`meta.ttsLang` ile geçersiz kılınır. Kanıt temeli
  `references/audio-system.md` (metin-konuşma/TTS bölümü; Wood 2017 meta-analiz, Keelor 2023) ve
  `adhd-pedagogy.md` §15. Doğrulama: genişletilmiş **G-AUDIO** kapısı (earcon + TTS iki katman).

### 11.6 Rozet ekonomisi — modüle özel, çeşitlendirilmiş, Carbon-ikonlu

Üst çubuktaki rozet kasası DEHB için kritik bir **somut hedef/ödül** katmanıdır.
Her modül `rewards.badges`'te **2–3 adet modüle özel rozet** tanımlamalıdır —
asla jenerik veya tek-tip değil:

- **Şema:** `{id, label, icon, condition}`.
  - `label` — konuya tematik, kısa, Türkçe (örn. "Alan Kâşifi", "Kesir Ustası",
    "Hız Şampiyonu", "Keskin Göz", "Üçgen Avcısı", "Denklem Dedektifi").
  - `icon` — rozete **anlamca uygun ve her rozette farklı** bir Carbon UI ikon
    id'si. Palet: `ic-compass` (kâşif/keşif) · `ic-view` (keskin gözlem,
    hatasızlık) · `ic-target` (isabet/doğruluk) · `ic-trophy` (tamamlama/zafer) ·
    `ic-flag` (hedefe ulaşma) · `ic-flash` (hız) · `ic-star` (genel başarı) ·
    `ic-light` (kavrayış) · `ic-check` (ustalık) · `ic-grid` / `ic-area` /
    `ic-ruler` (ölçme, geometri).
  - `condition` — kazanım tetikleyicisi. Mevcut: `"module-complete"` (modül
    tamamlanır) · `"flawless-mcq"` (tüm çoktan seçmeli ilk denemede doğru).
- **Görünüm (motor otomatik):** kilitli rozet **kendi ikonunu** gri tonda +
  küçük bir kilit rozetiyle gösterir (jenerik yıldız **değil**); kazanılınca
  ders aksanına döner ve `badge--new` kutlamasıyla belirir. Her rozetin kendi
  ikonu olduğundan kasa **görsel olarak çeşitlidir** — çocuk "hangi rozetler
  var, hangisini kazandım"ı bir bakışta ayırt eder.
- **Gerekçe:** görünür, ulaşılabilir ve **çeşitlendirilmiş** hedef-temsilleri
  içsel motivasyonu ve görev sürdürümünü güçlendirir; tek-tip/soyut rozetler bu
  etkiyi zayıflatır (`adhd-pedagogy.md` §13; Sailer 2019).

## 12. Kalite kapıları (Quality gates)

**OTORİTE yerel `scripts/validate_module.py`'dir** (PostToolUse hook'u aynı betiği koşar).
Plugin yayınlamaz; yalnız bu yerel validator'ın ölçtüğü sonucu beyan edin.

`scripts/validate_module.py` aşağıdakileri denetler (ihlal = düzelt). İnsan-okur konsol
raporu varsayılan moddur; **`--json` bayrağı** (v3.2.0) stdout'a yalnız geçerli JSON basar —
`{"G-EMOJI": {"status": "PASS"}, ...}` şeklinde, dilenirse manifest `quality_gates` alanına
doğrudan gömülebilir biçimde (bkz. §3 madde 7, Adım 5-6). `status` yalnız `PASS`/`FAIL`/`WARN`/
`SKIPPED` olur; koşturulmayan/uygulanamayan bir kapı `SKIPPED` yazılır (asla `PASS`).
- **G-EMOJI:** Çıktıda hiçbir emoji yok (Unicode emoji aralıkları taranır).
- **G-CARBON:** IBM Plex Sans/Serif/Mono gerçek inline `@font-face` ile yüklü;
  çekirdek `--cds-*` token'ları tanımlı ve kullanımda.
- **G-A11Y:** `lang`, `<title>`, odak görünürlüğü, ARIA rolleri, reduced-motion bloğu.
- **G-INTERACT:** Her quiz sorusunda doğru cevap indeksi + açıklama mevcut.
- **G-SELFCONTAINED:** Runtime kaynakları yalnız inline/`data:`/aynı-belge fragmentidir.
  Ağ, CDN, göreli/yerel kaynak; iframe; form/meta yönlendirmesi; CSS/SVG harici `url()` /
  `image-set()` ve inline JS ağ/dinamik kaynak yükleyicileri FAIL verir.
- **G-CONTRAST (öneri):** Metin/zemin kontrastı WCAG AA eşiğinde.
- **G-SVG:** Figür SVG'leri `role="img"`+başlık/etiket taşır; ham-hex yerine token renk (uyarı).
- **G-WELLBEING:** Cezalandırıcı/süre-baskısı dili yok; uzun modülde mola/azaltılmış hareket (uyarı).
- **G-VOICE (v3.8.0):** Öğrenci yüzeyinde kaynak-meta atıf yok ("kitabın tanımı",
  "kitaptaki yazıyı hatırla", "ders kitabında", "ünitede gördüğün", "sayfa N'de").
  Anlatım bu modülün kendi tamamlanmış (nihai) cümleleridir. `verification` /
  `sourceCitation` / `sourceRef` yazar katmanıdır, taranmaz. PhET CC BY-NC künyesi
  lisans atfıdır (yasak değil). Edebi eser olarak "kitap" meşrudur. Tam kural: §7.
- **G-AUDIO:** İşitsel katman(lar) — earcon **ve/veya** sesli-okuma (TTS) — opsiyonel,
  susturulabilir/durdurulabilir, reduced-motion duyarlı ve varsayılan kapalı; autoplay/loop ve
  otomatik-okuma yok. TTS kullanılıyorsa `toggleTTS`/`#ttsBtn`, `speechSynthesis.cancel` ve
  `data-tts="off"` varsayılanı aranır.
- **G-CURRICULUM (koşullu):** Yalnız `mode:"CURRICULUM"` ise veya `curriculum`
  bloğu varsa tetiklenir (yoksa atlanır — geriye dönük uyum). Denetler: CURRICULUM
  modunda `curriculum` bloğu zorunlu; `curriculum.outcomes[]` boş değil ve her
  öğede `code`+`text` var; her `outcomes[].mappedTo` segment id'si `segments[]`'te
  mevcut (kazanım→segment izlenebilirliği); `meta.sourceCitation` kazanım/korpus
  referansı içerir (eksikse uyarı). Tam kural: `references/curriculum-integration.md` §6.
- **G-VERIFY (koşullu, v3.6.0):** CURRICULUM modunda `verification` bloğu **zorunlu**.
  Kullanıcı sözleşmesi (2026-07-17): içerik **kapsam** ve **doğruluk/tutarlılık** denetiminden
  geçmeden canlıya alınmaz. **Yargıyı MODEL yapar, bu kapı YAPIYI denetler** — Python
  "bilimsel olarak doğru mu" diye karar veremez, ama "her iddianın dayanağı gösterilmiş mi"
  diye ölçebilir. **Denetler (çevrimdışı, dengeli/string+yorum-duyarlı ayrıştırıcı —
  validator'ın MCP erişimi YOKTUR):** `verification` bloğu var; `frame_source` geçerli
  `document_id` + `kind` + pozitif sayfa/kesin locator taşıyor;
  `scope.in_frame` **true** (false → FAIL, üretilmez); `claims[]` boş değil ve **her** öğede
  gerçek `claim`+verdict-uygun `grounding`+izinli `verdict` var; boş/placeholder kimlik,
  locator, license, provenance veya reason FAIL verir. Dayanaksız
  (`verdict:"general_knowledge"`) iddia → WARN, çoğunluk öyleyse → FAIL.
  **Altı verdict:** `supported` (ders kitabı) ·
  `supported_by_program` (öğretim programı) · `supported_by_source` (alternatif kaynak —
  ders kitabı OLMAYAN 3,4,7,8,11,12. sınıflar için, TYMM kademeli yürürlüğü) ·
  `general_knowledge` (dayanaksız) · `unverified` (placeholder olmayan açık reason ile WARN) ·
  `unsupported` (kaynak iddiayı desteklemiyor; daima FAIL).
  **`supported_by_source` kuralı:** kanıtlı sayılır
  (general_knowledge cezası YOK) ama grounding'i kaynak künyesi + `license` **taşımalı**
  (izlenebilirlik — eksikse FAIL); yalnız `frame_source.kind:"program"` (kitapsız/program-çerçeveli)
  modülde **meşru** — ders-kitabı çerçevesinde kullanılırsa azınlık WARN / çoğunluk FAIL
  (omurga `supported` olmalı). Görünür atıf (PhET CC BY-NC) yazarın sorumluluğudur, kapı
  dayatmaz. Çelişkide **ders kitabı > program > kaynak**.
  **DENETLEYEMEDİKLERİ (dürüst sınır, fazla güvenmeyin):** `document_id`'nin gerçekten var
  olduğunu, `kind:"textbook"` yazan belgenin `page_count>0` olduğunu, iddianın o sayfada
  geçtiğini ve iddianın DOĞRU olduğunu **bu kapı doğrulayamaz** — hiçbiri çevrimdışı
  ölçülemez. Kapı yalnız *dayanağın gösterildiğini* kanıtlar; **doğruluk yargısı modelindir
  ve insan denetimine tabidir.** Kapının değeri şudur: iddiayı yazmak, dayanağını yazmayı
  zorunlu kılar — "kontrol ettim" tiyatrosu yapısal olarak imkânsızlaşır.
  Tam kural: `references/curriculum-integration.md` §6.1.
- **G-TOKEN (v2.0.0):** Tema bloklarındaki `--cds-*` değerleri gömülü
  `@carbon/themes@11.75.0` otorite haritasına (≈19 token × White/G100) karşı
  denetlenir. Sapma = **WARN**; White temada `--cds-support-info:#4589ff` =
  **FAIL** (bilinen AA kontrast regresyonu — doğrusu #0043ce). Otorite kaynağı
  ve tazeleme: `scripts/sync_carbon_tokens.py` + `assets/carbon-v11-authority.json`.
- **G-FLOW (v3.0.0, koşullu):** Yalnız gamification imzası (`hook`/streak/
  pacingDisk) varsa tetiklenir; aksi halde atlanır. Açık kalan merak-boşluğu
  (bir `hook`'un `resolvesIn` hedefi hiç kapanmıyorsa), kayıp-cezalandırıcı seri
  dili, uyarlanır-zorluğun kullanıcıyı etiketlemesi ("zorlanıyorsun" vb.) ve
  kaygılı (geri-sayımlı) tempo diski **FAIL** üretir. Normatif kaynak:
  `references/gamified-flows.md`.
- **G-CARBON-GRID (v3.0.0):** Statik kart/segment/tile'da gerçek (non-inset)
  `box-shadow` = layer-elevation ihlali (**FAIL**); 2×-grid konteyneri,
  en-boy oranı (`aspect-ratio`) ve >500ms koreografi eksikliği (**WARN**).
  Normatif kaynak: `references/carbon-excellence.md` §3.
- **G-EXAM (v3.10.0, koşullu):** Yalnız `mode:"EXAM"` ise veya `exam:{}` veya dolu
  `exams:[]` varsa tetiklenir (yoksa atlanır — geriye dönük uyum). Legacy: `exam.stem`
  dolu; `transcriptionCheck` var olan bir segment id'sini gösteriyor; **`fadeFrom <
  adım sayısı` olan bir `worked`**; `exam.chain[]` dolu ve her halka `mappedTo` taşıyor;
  `integrity` ∈ {`sound`, `flawed`, `out_of_frame`}. Çoklu: her `exams[]` öğesi kendi
  `workedId` fadeFrom'u + `topicId` → `topics[].chain`. WARN: `source` yok; şık var ama
  `distractorAnalysis` yok; `exams.length > 4`. **DENETLEYEMEZ:** transkripsiyon
  sadakati, çözüm doğruluğu, zincir eksiksizliği. Tam kural:
  `references/exam-solving.md` §6.

## 13. Composability (SMP v1.0)

Makine-okunur graf: `skill-manifest.yaml`.

**Yukarı akış üreticiler (`pipe_from`)** — modüle kaynak içerik sağlayanlar:
- **Müfredat MCP** (Türkiye MEB / Maarif Modeli) — kazanım, program, beceri
  çerçevesi ve ders kitabı kataloğu sağlar; CURRICULUM modunun ve Müfredat-duyarlı
  modların **primer kaynağıdır** (bkz. `references/curriculum-integration.md`).
- `francais-coach` — Fransızca ders içeriği → Carbon etkileşimli modül.
- `medical-research`, `psychdev` — sağlık okuryazarlığı/gelişim içeriği (uygun
  yaş düzeyinde).
- `vekayinuvis` — tarih konuları için kaynak-temelli anlatı.
- `cureolex` — (yetişkin) mevzuat değil; uygun değil. (Yalnız uygun yaş içeriği.)

**Aşağı akış tüketiciler (`pipe_to`):**
- `carbon-html-report` — aynı içeriğin baskıya hazır statik (çalışma kâğıdı) sürümü.
- `pdf` — modülün özet/çalışma kâğıdı PDF'i.
- `figma-forge` — edupedia token'larını (`carbon-v11-authority.json`) Figma
  Variables'a, bileşen desenlerini ComponentSet'lere aktarma (paydaş gözden
  geçirmesi; bkz. `references/figma-carbon-interop.md` §6).

**Ortak ikon kelime dağarcığı:** `carbon-html-report`'un `icon-library.md`
modülüyle hizalı; piktogram seçimleri tutarlı.

**Orkestrasyon:** `smp-orchestrator pipelines carbon-edupedia` geçerli hatları
listeler (örn. `francais-coach → carbon-edupedia`,
`carbon-edupedia → carbon-html-report → pdf`).

## 14. Sınırlılıklar — Limitations / Out-of-Scope

- **Statik baskı dokümanı değil** → `carbon-html-report`. Bu yetkinlik
  *etkileşimli* HTML üretir; baskıda etkileşimler kaybolur.
- **Backend yok; tarayıcı depolaması sıkı izin listelidir.** `localStorage` yalnız
  tema + Leitner kutularını kalıcı tutar (`meta.id` varsa Leitner anahtarına girer).
  XP/seri/rozet/yanıt kümeleri yalnız `sessionStorage`'dadır; sekme oturumu dışında
  skor/ilerleme kalıcılığı yoktur. Her erişim try/catch ile degrade-safe'tir;
  depolama engelliyse çekirdek modül bellekte çalışmayı sürdürür.
- **Gerçek-zamanlı veri yok; tek istisna Müfredat MCP.** Çıktı tek-dosya offline
  HTML'dir ve çalışma anında canlı veri çekmez. Ancak **derleme anında** Müfredat
  MCP (Türkiye MEB / Maarif Modeli) opsiyonel **kaynak ve doğrulama katmanı** olarak
  çağrılabilir (kazanım çekme, beceri haritalama, provenans; bkz.
  `references/curriculum-integration.md`). Bu, üretilmiş modüle gömülmez — çekilen
  içerik kaynak olur, modül yine bağımsız ve çevrimdışıdır. MCP erişilemezse skill
  kullanıcı kaynağı/yerleşik bilgiyle (offline) çalışmaya geri döner.
- **Olgu doğrulama yok.** Kaynağın doğruluğu yukarı akış sorumluluğudur. (Müfredat
  MCP kullanıldığında kazanım metni primer kaynaktır; yine de olgular kazanıma/
  programa izlenebilir olmalı — uydurma yasak.)
- **Yaş uygunluğu zorunlu.** Yetişkin/uzman içerik (mevzuat, klinik ayrıntı) bu
  yetkinliğin kapsamı değildir; çocuk/öğrenci içeriğine sadık kalın.
- **Tarayıcı:** Chromium ≥ 120, Firefox ≥ 115, Safari ≥ 16.
- **Sorumlu kullanım (kanıt-temelli).** Modüller eğitim-destek materyalidir; **tıbbi
  cihaz/tedavi değildir** ve öğretmen/aile/akran etkileşiminin yerine geçmez. DEHB
  klinik kanıtına göre (bkz. `references/adhd-pedagogy.md` §10–§11) oturumlar kısa ve
  günün erken saatinde tutulmalı (uyku/sosyal yaşam koruması). Motor **nazik mola
  hatırlatıcısı** (`learner.breakReminderMin`, vars. 20 dk; `0` = kapalı), **sağlıklı
  kapanış** ve **sabit-cetvel (kumar-benzeri olmayan) ödül** ile bu ilkeleri uygular;
  `G-WELLBEING` kapısı cezalandırıcı/süre-baskısı dilini engeller.

## 15. Çocuk güvenliği ve refahı

- İçerik yaş-uygun, kapsayıcı, teşvik edici olmalı; başarısızlık "öğrenme
  fırsatı" olarak çerçevelenir (4:1 olumlu:düzeltici geri bildirim oranı).
- Olumsuz öz-konuşma, utandırma, ceza mekaniği **kullanılmaz**. Yarışmalar
  öz-rekabet (kişisel rekor) ya da düşük-baskılı sıralama üzerine kurulur.
- DEHB'ye duyarlı: aşırı uyaran/yanıp sönme yok; molalar yerleşik; başarı
  ulaşılabilir; ilerleme her zaman görünür.

---

**Sürüm geçmişi:** `docs/CHANGELOG.md`. SMP manifesti: `skill-manifest.yaml`.
Bu dosya kanonik işletim kılavuzudur; ayrıntı için ilgili `references/` dosyasını
okuyun.
