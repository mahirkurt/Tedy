# Tedy ile bütünlük (tedy-integration.md)

edupedia modülleri Tedy panosunun içinde, `ModuleViewer`'ın tam genişlikli çerçevesinde
açılır. Bu belge, modülün panoyla **tek bir yüzey** gibi okunması için şablonun (v1.9.0)
uyguladığı kuralları toplar (ders renk sistemi: şablon v2.1). Kural kaynağı Tedy Tasarım Sistemi v3'tür (Carbon v11'in
kendisi + `tedy-*` katmanı); depodaki karşılığı `dashboard/src/theme/ted-theme.scss`'tir.

**Öncelik.** Tasarım kararında TEDY Modül Tasarım Kanunu (`docs/tedy-modul-tasarim-kanunu.md`,
`edupedia_rehber('kanun')`) bu dosyanın önündedir. Bu dosya yazım varlıklarını ve şablonun
bugünkü davranışını anlatır; kanunla çelişen bir yeri kanun lehine okunur ve şablondaki farkı
kanunun borç kaydı (KB-n) adlandırır.

## 1. Katman modeli

Carbon token'larının **hiçbiri** yeniden tanımlanmaz veya anlamı değiştirilmez; `G-TOKEN`
her tema bloğunu `@carbon/themes` otoritesine karşı denetler. Tedy'ye özgü dil yalnız
`tedy-*` token'larıyla **üstüne** eklenir. Bu değerlerin makine-okunur tek kaynağı
`assets/carbon-v11-authority.json` → `tedyLayer`'dır: her token için Carbon palet adımı, hex ve
panoda aynı rolü taşıyan `--ted-*` değişkeni (pano adları: `--ted-color-brand-primary`,
`--ted-color-brand-primary-hover`, `--ted-color-brand-text-secondary`, `--ted-color-brand-rule`,
`--ted-color-page-bg`, `--ted-text-success/-error/-info/-warning`). Şablonda ve panoda renk
aritmetiği (`color-mix`, yarı saydam beyaz/siyah katman, gradyan yıkama) yoktur: her renk bir
Carbon token'ı ya da palet adımıdır. Bilinen istisnalar adlıdır: panoda Tedy Books ve Carbon AI
Chat'in Carbon for AI gradyanları (test muafiyeti), şablonda Tedy işaretinin yarı saydam hilali
ve birkaç `opacity` (.6 / .78 / .85) kullanımı; kalıcı opaklık Kanun M4.7 ile kalkar (borç KB-41).

| Token | g10 (varsayılan) | white (eski kayıt) | g100 | Kullanım |
|---|---|---|---|---|
| `--tedy-brand` | `#002d9c` | `#002d9c` | `#002d9c` | Yalnız üst kimlik bandı ve işaretin onayı. Eylem rengi değildir. |
| `--tedy-brand-hover` | `#001d6c` | `#001d6c` | `#001d6c` | Bant üstündeki çipler ve ikon düğmesi hover'ı. |
| `--tedy-brand-text-secondary` | `#d0e2ff` | `#d0e2ff` | `#d0e2ff` | Bant üstü ikincil metin (blue-20, lacivert üstünde 8,6:1). Yarı saydam beyazın yerine. |
| `--tedy-brand-rule` | `#0f62fe` | `#0f62fe` | `#0f62fe` | Bant üstü ince ayraç ve tempo diski izi (blue-60). |
| `--tedy-page-background` | `#f2f4f8` | `#ffffff` | `#121619` | `body` zemini (cool-gray: "okul" hissi). `--cds-background` Carbon değerinde kalır. |
| `--tedy-text-success/-error/-info/-warning` | `#0e6027` `#a2191f` `#0043ce` `#8a3800` | aynı | `#6fdc8c` `#ffb3b8` `#a6c8ff` `#ffb784` | Okunması gereken durum metni. `support-*` yalnız ikon/kenar/çubuk içindir. |
| `--tedy-accent-urgent` | `var(--cds-support-error)` | aynı | aynı | Kırmızı yalnız gerçek aciliyettir. |

Kanonik Carbon adları birincildir: `--cds-border-strong-01`, `--cds-border-tile-01`,
`--cds-notification-background-{success,info,warning,error}`, `--cds-background-inverse`,
`--cds-text-inverse`. `--cds-notif-*-bg` eski bir takma addır; yeni kodda kanonik adı kullanın.
Dikkat: Carbon v11'de numarasız `--cds-layer`, `--cds-field`, `--cds-border-subtle`,
`--cds-border-strong` takma ad değil **bağlamsal token'dır**; değerlerini `Layer` iç içeliği
belirler (https://carbondesignsystem.com/building-blocks/foundations/color/guidelines/#designing-for-contextual-tokens).
Şablon bugün bunları sabit değere bağlar (`--cds-border-subtle` → `-00`, `--cds-border-strong`
→ `-01`); gerçek bağlamsal davranış şablon değişikliğidir — açık madde
(`carbon-excellence.md` §2.9).

## 2. Tema

- Varsayılan **g10**'dur (`<html data-theme="g10">`), çünkü pano `<Theme theme="g10">`
  altında çalışır. **Modül temayı yalnız panodan alır** ve koşulsuz uygular (Kanun M4.1):
  tema düğmesi, tema kaydı ve "öğrencinin seçimi > pano" önceliği yoktur. Şablon bugün tema
  düğmesini, kaydı ve bu önceliği hâlâ taşır: borç KB-1. g100 bloğu yalnız otoriteden üretilen
  token eşlemesidir; `white` ölü bir temadır (M4.3, borç KB-22).
- Pano bir gün koyu mod eklerse bu panonun Profil'deki ayarıdır; modül onu bu mesajla devralır
  (Kanun M4.2).
- Carbon, kullanıcı seçimi yoksa işletim sistemi temasına uyar
  (https://carbondesignsystem.com/building-blocks/foundations/themes/code/#system-preferences).
  Modül sistem tercihine bakmaz; panonun bildirdiği temayı uygular (adlı sapma KS-7).
- **Pano → modül mesajı:** `{"type": "edupedia:appearance", "v": 1, "theme": "g10", "rootPx": 32}`.
  `ModuleViewer` bunu çerçevenin `load` olayında gönderir (taslak önizleme dahil;
  taslaklar `ready` üretmez). Modül mesajı yalnız `e.source === window.parent` ve
  `e.origin === EDUPEDIA_PARENT_ORIGIN` iken işler; `adoptHostTheme()` yalnız
  `g10 | g100 | white` değerlerini kabul eder. Mesaj ilerleme taşımaz ve saklanmaz.
- **`rootPx` (isteğe bağlı, 2026-10-15).** Panonun o andaki hesaplanmış kök yazı boyu. Pano
  1920 px üstünde kök puntoyu pencereyle büyütür (`clamp(100%, calc(100vw / 120), 250%)`); çerçeve
  ayrı bir belge olduğu için o kuralı devralmaz **ve kendisi türetemez**: içeride `100vw`
  çerçevenin genişliğidir, yani panonun sütunu eksi sayfa dolgusu — CSS'ten türetmek modülün yazı
  boyunu pano yerleşimine bağlar ve `modul.tedy.online`'da tek başına açılan modülü yanlış
  ölçekler. Bu yüzden değeri pano bildirir. `adoptHostRootSize()` yalnız sayı kabul eder ve
  **12–48 px**'e kıstırır; alan yoksa modül 16 px'te kalır (tek başına açılış ve eski pano aynen
  çalışır, bu yüzden `v` 1'de kaldı). Okurun tarayıcı yazı boyu tercihi panonun `clamp()`
  tabanında (`100%`) zaten vardır, yani hesaplanmış değer onu taşır. Pano kökü değişen her
  yeniden boyutlamada yeniden gönderilir; değişmediyse gönderilmez.
- **`layout: "flow"` (isteğe bağlı, 2026-10-19) — modül panonun bir bölümüdür, çerçevedeki ayrı
  bir sayfa değil.** Pano bu alanı gönderince köprü `<html data-host-layout="flow">` yazar ve gövde
  yüksekliğini **modül → pano** `{"type": "edupedia:size", "v": 1, "height": 1840}` mesajıyla
  bildirir (`ResizeObserver`; aynı boy yeniden gönderilmez). Pano çerçeveyi o boya büyütür, çerçevenin
  kendi kaydırma çubuğu olmaz, sayfa tek parça kayar. Bölüm değişince modülün `window.scrollTo`'su
  boş bir pencereyi kaydırır; köprü aynı mesajı `"top": true` ile gönderir ve pano çerçevenin üstü
  okurun gördüğü alanın üstünde kaldıysa onu görünüme getirir (modülü açmak sayfayı kaydırmaz).
  Akışta modül kendi sayfa kabuğunu bırakır (şablondaki `data-host-layout="flow"` bloğu): 55rem
  sütun, dolgu ve `.wrap`'in `100vh` tabanı kalkar — taban kalsaydı çerçeve boyu içeriği, içerik
  çerçeveyi büyütürdü. Kimlik bandı ve modülün başlık bloğu gizlenir; sayfanın başı panonundur
  (§3, Kanun M1.1). İlerleme rayı panonun kart diliyle tek kart olur; araç düğmeleri (ses, sesli
  okuma) kalır, tema düğmesi yoktur (Kanun M4.1; şablonda borç KB-1). Mesaj yalnız
  `window.parent`'a ve `EDUPEDIA_PARENT_ORIGIN`'e gider; pano onu yalnız açtığı çerçeveden
  (`event.source`, origin `"null"`) ve `1–200000` tam sayı boyla kabul eder (`acceptSizeMessage`).
  Alan yoksa (eski pano, tek başına açılış) bu yol hiç kurulmaz; bu tarihten önce derlenmiş modül
  alanı tanımaz, pano o zaman çerçevenin sabit asgari boyunu ve modülün kendi kaydırmasını korur.
- `G-BRIDGE` `edupedia:appearance` ve `edupedia:size` tiplerini **izinli ama zorunlu değil** sayar;
  bu tiplerden önce derlenmiş modüller geçerli kalır. `sablon.py`, şablonda `adoptHostTheme` yoksa
  `TemplateDriftError` verir.

## 3. Kimlik bandı ve ders rengi

- Üst bant düz `--tedy-brand` zemindir; solda Tedy işareti (beyaz disk, yarı saydam beyaz
  hilal, lacivert onay; renkler token, `aria-hidden`), üzerinde `text-on-color` başlık.
  Gradyan, radyal parıltı, ham hex ve cam (`rgba`) yüzey yoktur.
- **Bant yalnız tek başına açılışta vardır.** Panonun akış yerleşiminde (§2, `layout: "flow"`)
  Tedy laciverti panonun kendi üst bandındadır; sayfanın içinde ikinci bir lacivert bant başka bir
  uygulama gibi okunur (2026-10-19, ölçüldü: kullanıcı modülü "başka bir sayfadan çerçeveye
  konmuş" diye tarif etti). Orada modülün başlık bloğu (`.topbar__l`) ve Tedy işareti gizlenir;
  modül adı, kazanım etiketleri ve AI etiketi panonun başındadır (`ModulBasligi`, Kanun M1.1,
  M1.10). Araç düğmeleri Carbon ghost ikon düğmesidir (lg 48 px, araç ipucunda adı; M5.14).
- Bantta XP sayacı, seri çipi ve rozet yoktur (2026-10-11, talimatname S43, B73 kapandı):
  bant başlık, ilerleme rayı ve araç düğmelerini taşır.
- Ders rengi bantta **değildir**. Modülün içinde yalnız Kanun M1.5'in çapalarında görünür:
  kavram yüzeylerinin (`.lead`, merak kartı) 4 px kenarı, vurgulu terimin tint zemini, kavram
  çipinin tint zemini ve ders kenarı, segment ikonunun tint zemini. Etkileşim durumları (hover,
  seçili, işaretli, geçerli adım, odak) ders rengi almaz (M1.6). Şablon bugün daha geniş kullanır
  (dolu ikon karosu, kicker, seçenek halkası): borç KB-16, KB-17. Anlatım kutuları (`.lead`,
  `.hook-card`, `.se-model`, `.callout`, `.self-assess`) nötr `--cds-layer-02` yüzeydir.
- İlerleme göstergesi ve düğmeler arayüz kabuğudur: Carbon `button-primary`/`interactive`.
  Bu kural panoda da istisnasızdır (2026-10-10, talimatname S35): asistanın öğretmen modu da birincil
  eylemi Carbon mavisinde tutar.

### 3.1 Tedy ders renk sistemi

Ders rengi Tedy'nin **her yüzeyinde aynıdır**: modül ve pano (sınav kartı, bugünün sınavları,
ödevler, platform ilerlemesi, takvim, asistanın öğretmen modu). Emekli katalog sitesi artık bir
yüzey değildir; panonun Modüller listesi dersi metinle gösterir. Tek kaynak `assets/carbon-v11-authority.json` →
`tedyLayer.subjectThemes`.

**Çözümleme.** Ders adı (`meta.subject`, panoda normalleştirilmiş ders adı) katlanır — Türkçe
küçük harf, `ç ğ ı ö ş ü â î û` → `c g i o s u a i u` — ve alan tablosu sırayla denenir; bir kök
bir sözcüğün başında geçerse o alan seçilir, hiçbiri geçmezse `genel`. Aynı tablo ve aynı kural
üç çalışma zamanında koşar: şablon (`subjectDomain()`), backend (`src/subject_themes.py`) ve pano
(`dashboard/src/theme/subjects.ts`, üretilir). `examples` test vektörleri üçünü bağlar.

| Alan | Aile | Açık accent / text | Koyu accent / text | Örnek dersler |
|---|---|---|---|---|
| Türkçe ve edebiyat | `magenta` | `#d02670` / `#9f1853` | `#ff7eb6` / `#ffafd2` | Türkçe, Türk Dili ve Edebiyatı |
| Matematik | `purple` | `#8a3ffc` / `#6929c4` | `#be95ff` / `#d4bbff` | Matematik, Geometri |
| Fen bilimleri | `teal` | `#007d79` / `#005d5d` | `#08bdba` / `#3ddbd9` | Fen Bilimleri, Fizik, Kimya, Biyoloji |
| Sosyal bilimler | `cyan` | `#0072c3` / `#00539a` | `#33b1ff` / `#82cfff` | Sosyal Bilgiler, İnkılap Tarihi, Coğrafya |
| Yabancı diller | `blue` | `#0f62fe` / `#0043ce` | `#78a9ff` / `#a6c8ff` | İngilizce, Fransızca, Almanca |
| Din ve değerler | `warm-gray` | `#726e6e` / `#565151` | `#ada8a8` / `#cac5c4` | Din Kültürü ve Ahlak Bilgisi, Ahlak ve Yurttaşlık |
| Bilişim ve teknoloji | `cool-gray` | `#697077` / `#4d5358` | `#a2a9b0` / `#c1c7cd` | Bilişim Teknolojileri ve Yazılım |
| Sanat ve spor | `gray` | `#6f6f6f` / `#525252` | `#a8a8a8` / `#c6c6c6` | Görsel Sanatlar, Müzik, Beden Eğitimi |
| Genel (yedek) | `gray` | aynı | aynı | PDR, tanınmayan adlar |

**Roller.** Otorite her aile ve mod için dokuz rol taşır; şablon bunların yedisini üretir
(`panel` ve `panelBorder` yalnız panonun tek büyük ders yüzeyi içindir, aşağıda "Panoda").
Şablonun yedi rolü, açık (white, g10) ve koyu (g90, g100) mod için:
`accent` (palet 60 / 40: çizgi ve kenar), `text` (70 / 30: renkli metin ve ikon),
`surface`, `onSurface`, `surfaceHover`, `border` (Carbon `tag-background-X`, `tag-color-X`,
`tag-hover-X`, `tag-border-X`) ve `onAccent` (white-0 / gray-100). Şablonda `--subject-*`
değişkenleridir; `--accent`, `--accent-strong`, `--accent-tint`, `--accent-on` bunların takma
adıdır. Değerler `tedy:ders-renkleri` bölgesinde üretilir; tema değişince CSS kendiliğinden
geçer, JavaScript renk hesaplamaz. Ters (inverse) tanım balonunda aksan metni karşı modun
`text` rolüdür (`--subject-text-inverse`).

**Kontrast.** Carbon paleti adım başına algısal olarak eşittir; sekiz aile aynı profili taşır
ve hiçbir ders diğerinden "yüksek sesle" konuşmaz: `accent` açık zeminlerde ≥ 4,5:1, koyu
zeminlerde ≥ 4,8:1; `text` açıkta ≥ 6,9:1, koyuda ≥ 6,7:1; tag çifti ≥ 5,8:1; halka tag zemini
üstünde ≥ 3,2:1. `tests/test_ders_renkleri.py` her aile ve her zemin için hesaplar.

**Ayrılmış renkler.** Kırmızı (aciliyet), yeşil (doğru/tamamlandı), sarı (uyarı) ve
turuncu (uyarı) anlam renkleridir; hiçbir derse verilmez. Önceki eşlemedeki yeşil Din, kırmızıya
yakın tonlar ve hex aksanlar kaldırıldı.

**Wayfinding.** Etkinlik tipini ikon ve kicker metni taşır. Segment ikon karosu ders
renginin tint zeminidir (`surface`), molada nötr `layer-accent-01`; dolu `accent` karo yoktur
(Kanun M1.4; şablonda etkileşim segmentlerindeki dolu karo borç KB-16; color-system.md §3).

**Yazar kuralı.** `meta.subject`'e dersin resmî adını yazın ("Fen Bilimleri"). `meta.accent`
yazılmaz; `MODULE_DATA` renk, tema, CSS, font ve satır içi stil taşımaz (Kanun M4.5).
Derleyici hex'i ve anlam renklerini reddeder ama bir aile adını bugün hâlâ kabul eder: borç
KB-24.

**Panoda.** İ8 2026-10-02'de yeniden yazıldı: ders rengi yüzeye ölçüyle çıkabilir. Bir görünümde
**en çok bir büyük ders yüzeyi** vardır — o ekranın "tek şey"i (Bugün'de sıradaki ders ya da iş,
asistanda öğretmen paneli): `--ted-subject-panel` zemin (açıkta palet 10, koyuda 90),
`--ted-subject-panel-border` kenar (30 / 70), metin `--ted-subject-text`. Küçük kartlar açık
zemin ve üst şerit kullanabilir; listeler dersi şerit, kenar ya da noktayla taşır (ders adının
önünde `0.625rem` renk karesi, `SubjectLabel`). Gradyan, saydamlık, `filter`, `color-mix` yasağı
sürer; gri tonlama testi geçer. Ders hiçbir yerde durum etiketi (Carbon Tag) biçiminde
görünmez; etiketler durum ve üst veri içindir ve geri sayım ölçeği yalnız kırmızı + nötrdür
(`countdownTagType`). Kaynak: `docs/frontend-design-principles.md` İ8.

## 4. Köşe ve gölge

| Öğe | Köşe | Token |
|---|---|---|
| Üst bant, sahne, iç kartlar ve paneller | 8 px | `--cds-radius` = `--cds-border-radius-08` |
| Düğme, seçenek kutusu, ikon düğmesi, kavram-haritası düğümü | 0 | `--radius-btn` = `--cds-border-radius-00` |
| Metin alanı, sayı alanı | 0 | `--radius-field` = `--cds-border-radius-00` |
| Tablo | 0 | `--cds-border-radius-00` |
| Etiket/çip (tanım etiketi, kavram çipi) | tam | `--radius-tag` = `--cds-border-radius-max` |

**Statik yüzey gölge almaz** (S11, P4; 2026-10-15). `.topbar` ve `.stage`'in
`--tedy-shadow-card`'ı kalktı — ikisinde de 1 px `var(--cds-border-subtle)` zaten vardı ve derinlik
katman token'ı ile kenarla kurulur. Token iki `rgba()` katmanı taşıdığı için D1'in renk aritmetiği
yasağını da ihlal ediyordu. İç kutular eskiden olduğu gibi gölgesizdir (`G-CARBON-GRID`). Gölge
yalnız **geçici** yüzeyde kalır: tanım popover'ı Carbon ters yüzeydir (`background-inverse`,
`text-inverse`) ve `0 2px 6px var(--cds-shadow)` (shadow-menu) taşır.

Tabloda olmayan üç yer 2026-10-15'te token'a bağlandı ve 4 px sapması kapandı: tanım popover'ı
`--cds-border-radius-04`'ten **`-02`**'ye indi (Carbon popover köşesi 2 px'tir,
https://carbondesignsystem.com/building-blocks/core/components/popover/guidelines/#corners);
satır içi terim vurgusu (`mark.term`) düz `4px` yazıyordu, yani token sözlüğünü atlıyordu →
**`-00`** (S10: kart/panel 8, çip/etiket tam, geri kalan 0 — satır içi vurgu "geri kalan"dır);
lejant yuvarlağı (`.viz-legend i`) düz `3px` yazıyordu → **`-00`** (işaretler 0'a girer).
`.topbar`/`.stage` gölgesi de kalktı; Carbon'un "statik karoda gölge yok" kuralına adlı Tedy
istisnası artık **yok** (`carbon-excellence.md` madde 4, S11).

## 5. Oyunlaştırma — yok (S43)

**Karar (2026-10-10, talimatname S43, Ç9'un kararı):** modülde kutlama ya da ödül animasyonu
(XP/seri nabzı, "+N XP" yükselişi, rozet belirişi, ödül sesi) ve seri sayacı yoktur. İlerleme sessiz,
etiketli tek bir göstergedir; adımları 3–7 aşamadır, segment değil (`meta.milestones`, Kanun M2.4,
M2.5; şablonda borç KB-2). Anında geri bildirim metinle kalır. XP ve rozet ekranda hiç yoktur
(Kanun M2.7). Dayanak: anayasa §9 ("kutlama", "seri sayacı"), İ6 (aynı anda tek hareket), Carbon productive
hareket (https://carbondesignsystem.com/building-blocks/foundations/motion/overview/#productive-motion).
Şablon bu kararı uygular (2026-10-11, talimatname B73 kapandı):

- **XP** iç ilerleme sayısıdır: ilerleme köprüsü panoya bildirir (`edupedia:progress` `xp`), okur
  görmez. Üst bantta sayaç, "+N XP" yükselişi ve nabız yoktur. `rewards.xpPerCorrect` /
  `firstTryBonus` yalnız bu iç sayıyı besler.
- **Seri sayacı yoktur.** G-FLOW, işaretlemede seri sayacı öğesi (`id="streakChip"`) bulursa FAIL verir.
- **Rozet gösterilmez** (kararın "kalırsa" seçeneği kullanılmadı: kilitli rozet "rozet avı"dır, kazanılan
  rozet de ilerleme etiketinin taşımadığı bir bilgi taşımaz — anayasa §9, İ6). `rewards.badges`
  geriye uyum için kabul edilir, ekranda yer almaz.
- **Ödül sesi yoktur**; doğru cevabın kısa `correct` earcon'u anında geri bildirim olarak kalır
  (isteğe bağlı, `audio-system.md`).
- **Özet ekranı sessizdir:** "Modülü tamamladın", tamamlanan alıştırma sayısı düz metinle
  ("8 / 10 alıştırmayı doğru tamamladın"), hedefler ve tekrar önerisi; büyük sayı, halka grafik,
  "Toplam XP", rozet sayısı ve "En uzun seri" yoktur.
- `--reward` / `--reward-bg` rolü kalktı; sarı yalnız uyarıdır.

## 6. Doğrulama

- `scripts/sync_carbon_tokens.py --check`: g10 · white · g100 bloklarını, Tedy katmanını
  (19 değer) ve ders renk sisteminin iki üretilmiş bölgesini (8 aile × 2 mod × 7 rol, 8 alan)
  otoriteye karşı diff'ler. `--write-subjects` bölgeleri yeniden yazar.
- `scripts/validate_module.py` → `G-TOKEN` g10'u da denetler; açık temalarda
  `--cds-support-info:#4589ff` FAIL'dir.
- Depo testleri: `tests/test_tedy_tasarim_tutarliligi.py` (pano `ted-theme.scss` ↔ şablon ↔
  otorite: aynı Carbon adımları, tek pano teması, izinli aileler), `tests/test_ders_renkleri.py`
  (üç çalışma zamanında aynı çözümleme, Carbon kökeni, kontrast, panoda ve şablonda palet dışı
  renk yok), `tests/test_mcp_sablon.py`,
  `tests/test_mcp_gates_ek.py`, `tests/test_pano_tasarim_sistemi.py` (panoda renk aritmetiği yok,
  lacivert yalnız bantta, Tag'de ders rengi yok); pano uçtan uca: `dashboard/tests/e2e/moduller.spec.ts`
  (tema devri).
- Otorite dosyasının bayt-özdeş kopyası CureoHub `services/edupedia_site/app/static/`
  altındadır (emekli katalog sitesi, `carbon.css` oradan üretilir); dosya burada değişince
  oraya da kopyalanır. 2026-10-10 ölçümü: kopya güncel değil (sha256 `4d4dd1ff…`, buradaki
  `d6958862…`; `tedyLayer`, `subjectThemes` ve panel rolleri eksik). Kopyalama kuralının
  sürdürülmesi ya da kaldırılması açık maddedir.

## 7. Kanonik kılavuz, Carbon kaynakları ve adlı istisnalar

- **Kanun ve kılavuz:** modül yüzeylerinde tasarım kararı TEDY Modül Tasarım Kanunu'nundur
  (`docs/tedy-modul-tasarim-kanunu.md`, `edupedia_rehber('kanun')`); adlı sapmalar KS-1…KS-12,
  borçlar KB-1…KB-46. Talimatname (`docs/tedy-ui-ux-talimatnamesi.md`) pano bağını verir: §9
  modüller, §10 Carbon MCP protokolü, §11 sapmalar (S1…S50), §13 borçlar. Bu dosya yazım
  varlıklarının tek kaynağı olarak kalır (şablon, otorite JSON'u, referanslar; `vendor_sync
  --pin`); tasarım kararında kanun önceliklidir. Kod ajanları için TEDY katmanı:
  `.claude/skills/tedy-carbon/SKILL.md` (IBM'in `carbon-builder` becerisinin üstünde; çelişkide kazanır).
- **Carbon iddiası kaynakla yazılır:** güncel `https://carbondesignsystem.com/building-blocks/...`
  URL'si ya da Carbon MCP `docs_search` `anchor_url`'ı; değer yine npm `@carbon/*`'tan
  (`carbon-sources.md`).
- **Adlı sapmalar** kanunun §7'sindedir (KS-1…KS-12). Burada kalan Tedy istisnaları: 8 px
  kart köşesi (§4, KS-4), lacivert bant yalnız tek başına açılışta — Carbon'un "yüksek kontrast
  anı" biçiminde marka bölgesi
  (https://carbondesignsystem.com/building-blocks/foundations/color/overview/#high-contrast-moments)
  ve tek tema (§2, KS-7). Statik yüzey gölgesi 2026-10-15'te kalktı (§4, S11). 2026-10-10'da istisna olmaktan çıkanlar: 700 ms "+N XP" yükselişi
  (S43; 2026-10-11'de kalktı, B73) ve panodaki asistanın öğretmen modunda `--cds-button-primary` /
  `--cds-interactive`'in ders aksanına yönlenmesi (S35: birincil eylem her yerde Carbon mavisi; B68).
- **4K eşliği kapandı** (2026-10-15): şablon rem tabanlıdır ve kök boyunu `rootPx` ile panodan
  alır (§2, Kanun M5.8).
- **AI etiketi — karar (2026-10-10, talimatname S41, Ç7'nin kararı).** Panoda gösterilen her modül
  `ModuleViewer`'ın çerçeve başlığında Carbon `AILabel` taşır; açıklama penceresi neyin yapay zekâyla
  üretildiğini (anlatım, sorular, görseller) ve dayandığı kaynakları (kazanım, ders kitabı sayfaları,
  iddia dayanakları) söyler
  (https://carbondesignsystem.com/building-blocks/core/components/ai-label/guidelines/#in-containers).
  Etiket panonun çerçevesindedir, şablona eklenmez: modülün içinde G-VOICE aynen geçerlidir (öğrenci
  yüzeyinde kaynak-meta atıf yok). Panoda uygulandı (`ModulAiEtiketi.tsx`; Kanun M1.10).
