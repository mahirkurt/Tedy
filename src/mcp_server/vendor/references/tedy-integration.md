# Tedy ile bütünlük (tedy-integration.md)

edupedia modülleri Tedy panosunun içinde, `ModuleViewer`'ın tam genişlikli çerçevesinde
açılır. Bu belge, modülün panoyla **tek bir yüzey** gibi okunması için şablonun (v1.9.0)
uyguladığı kuralları toplar (ders renk sistemi: şablon v2.1). Kural kaynağı Tedy Tasarım Sistemi v3'tür (Carbon v11'in
kendisi + `tedy-*` katmanı); depodaki karşılığı `dashboard/src/theme/ted-theme.scss`'tir.

## 1. Katman modeli

Carbon token'larının **hiçbiri** yeniden tanımlanmaz veya anlamı değiştirilmez; `G-TOKEN`
her tema bloğunu `@carbon/themes` otoritesine karşı denetler. Tedy'ye özgü dil yalnız
`tedy-*` token'larıyla **üstüne** eklenir. Bu değerlerin makine-okunur tek kaynağı
`assets/carbon-v11-authority.json` → `tedyLayer`'dır: her token için Carbon palet adımı, hex ve
panoda aynı rolü taşıyan `--ted-*` değişkeni (pano adları: `--ted-color-brand-primary`,
`--ted-color-brand-primary-hover`, `--ted-color-brand-text-secondary`, `--ted-color-brand-rule`,
`--ted-color-page-bg`, `--ted-text-success/-error/-info/-warning`). Şablonda ve panoda renk
aritmetiği (`color-mix`, yarı saydam beyaz/siyah katman, gradyan yıkama) yoktur: her renk bir
Carbon token'ı ya da palet adımıdır.

| Token | g10 (varsayılan) | white (eski kayıt) | g100 | Kullanım |
|---|---|---|---|---|
| `--tedy-brand` | `#002d9c` | `#002d9c` | `#002d9c` | Yalnız üst kimlik bandı ve işaretin onayı. Eylem rengi değildir. |
| `--tedy-brand-hover` | `#001d6c` | `#001d6c` | `#001d6c` | Bant üstündeki çipler ve ikon düğmesi hover'ı. |
| `--tedy-brand-text-secondary` | `#d0e2ff` | `#d0e2ff` | `#d0e2ff` | Bant üstü ikincil metin (blue-20, lacivert üstünde 8,6:1). Yarı saydam beyazın yerine. |
| `--tedy-brand-rule` | `#0f62fe` | `#0f62fe` | `#0f62fe` | Bant üstü ince ayraç ve tempo diski izi (blue-60). |
| `--tedy-page-background` | `#f2f4f8` | `#ffffff` | `#121619` | `body` zemini (cool-gray: "okul" hissi). `--cds-background` Carbon değerinde kalır. |
| `--tedy-text-success/-error/-info/-warning` | `#0e6027` `#a2191f` `#0043ce` `#8a3800` | aynı | `#6fdc8c` `#ffb3b8` `#a6c8ff` `#ffb784` | Okunması gereken durum metni. `support-*` yalnız ikon/kenar/çubuk içindir. |
| `--tedy-accent-urgent` | `var(--cds-support-error)` | aynı | aynı | Kırmızı yalnız gerçek aciliyettir. |
| `--tedy-shadow-card` | `0 1px 3px rgba(0,0,0,.05), 0 1px 2px rgba(0,0,0,.08)` | aynı | `none` | Yalnız sayfa düzeyindeki iki kart: `.topbar` ve `.stage`. |

Kanonik Carbon adları birincildir: `--cds-border-strong-01`, `--cds-border-tile-01`,
`--cds-notification-background-{success,info,warning,error}`, `--cds-background-inverse`,
`--cds-text-inverse`. Eski kısa adlar (`--cds-border-strong`, `--cds-border-tile`,
`--cds-notif-*-bg`) takma ad olarak durur; yeni kodda kanonik adı kullanın.

## 2. Tema

- Varsayılan **g10**'dur (`<html data-theme="g10">`), çünkü pano `<Theme theme="g10">`
  altında çalışır. Koyu tema **g100**; tema düğmesi g10 ↔ g100 arasında geçer.
  `white` yalnız eski bir kayıtlı tercihi bozmamak için tanınır.
- **Öncelik:** öğrencinin kendi seçimi (bu modülde düğmeye bastıysa ya da kayıtlı tercih
  varsa) > panonun bildirdiği tema > g10.
- **Pano → modül mesajı:** `{"type": "edupedia:appearance", "v": 1, "theme": "g10"}`.
  `ModuleViewer` bunu çerçevenin `load` olayında gönderir (taslak önizleme dahil;
  taslaklar `ready` üretmez). Modül mesajı yalnız `e.source === window.parent` ve
  `e.origin === EDUPEDIA_PARENT_ORIGIN` iken işler; `adoptHostTheme()` yalnız
  `g10 | g100 | white` değerlerini kabul eder. Mesaj ilerleme taşımaz ve saklanmaz.
- `G-BRIDGE` bu tipi **izinli ama zorunlu değil** sayar; bu tipten önce derlenmiş modüller
  geçerli kalır. `sablon.py`, şablonda `adoptHostTheme` yoksa `TemplateDriftError` verir.

## 3. Kimlik bandı ve ders rengi

- Üst bant düz `--tedy-brand` zemindir; solda Tedy işareti (beyaz disk, yarı saydam beyaz
  hilal, lacivert onay; renkler token, `aria-hidden`), üzerinde `text-on-color` başlık.
  Gradyan, radyal parıltı, ham hex ve cam (`rgba`) yüzey yoktur.
- Bant üstündeki XP ve seri çipleri Carbon Tag'dir: `--tedy-brand-hover` zemin,
  `text-on-color` metin. XP yıldızı `--cds-support-warning` (lacivert üstünde 7,3:1).
- Ders rengi bantta **değildir**; yalnız odak çapalarında yaşar: bölüm ikon karosu (`.seg-ic`),
  `kicker`, seçili seçenek halkası, anlatım kutularının 4 px sol çizgisi, tanım etiketi, zaman
  çizelgesi düğümü, piktogramlar ve küçük işaretler. Anlatım kutuları (`.lead`, `.hook-card`,
  `.se-model`, `.callout`, `.self-assess`) nötr `--cds-layer-02` yüzeydir.
- İlerleme göstergesi ve düğmeler arayüz kabuğudur: Carbon `button-primary`/`interactive`.

### 3.1 Tedy ders renk sistemi

Ders rengi Tedy'nin **her yüzeyinde aynıdır**: modül, pano (sınav kartı, bugünün sınavları,
ödevler, platform ilerlemesi) ve katalog. Tek kaynak `assets/carbon-v11-authority.json` →
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

**Roller.** Her aile, açık (white, g10) ve koyu (g90, g100) mod için yedi rol taşır:
`accent` (palet 60 / 40: çizgi, halka, dolu karo), `text` (70 / 30: kicker, renkli ikon),
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

**Ayrılmış renkler.** Kırmızı (aciliyet), yeşil (doğru/tamamlandı), sarı (uyarı ve ödül) ve
turuncu (uyarı) anlam renkleridir; hiçbir derse verilmez. Önceki eşlemedeki yeşil Din, kırmızıya
yakın tonlar ve hex aksanlar kaldırıldı.

**Wayfinding.** Etkinlik tipi renk ailesiyle değil, dersin ailesinin tonuyla imlenir:
etkileşim segmentlerinde ikon karosu dolu `accent` (`onAccent` ikon), anlatım/veri segmentlerinde
`surface`, molada nötr `layer-accent-01` (color-system.md §3).

**Yazar kuralı.** `meta.subject`'e dersin resmî adını yazın ("Fen Bilimleri"). `meta.accent`
isteğe bağlıdır ve yalnız bir aile adı olabilir (`magenta`, `purple`, `teal`, `cyan`, `blue`,
`warm-gray`, `cool-gray`, `gray`); derleyici hex'i ve anlam renklerini şema hatasıyla reddeder.
MODULE_DATA'ya renk, tema ya da CSS yazılmaz.

**Panoda.** Ders rengi yalnız işaret, çubuk ve kenardır (İ8): ders adının önünde 10 px renk
karesi (`SubjectLabel`), sınav kartının sol kenarı, kartın `kicker`'ı `text` rolünde. Ders hiçbir
yerde durum etiketi (Carbon Tag) biçiminde görünmez; etiketler durum ve üst veri içindir ve geri
sayım ölçeği yalnız kırmızı + nötrdür (`countdownTagType`).

## 4. Köşe ve gölge

| Öğe | Köşe | Token |
|---|---|---|
| Üst bant, sahne, iç kartlar ve paneller | 8 px | `--cds-radius` = `--cds-border-radius-08` |
| Düğme, seçenek kutusu, ikon düğmesi, kavram-haritası düğümü | 0 | `--radius-btn` = `--cds-border-radius-00` |
| Metin alanı, sayı alanı | 0 | `--radius-field` = `--cds-border-radius-00` |
| Tablo | 0 | `--cds-border-radius-00` |
| Etiket/çip (XP, seri, rozet, tanım etiketi) | tam | `--radius-tag` = `--cds-border-radius-max` |

Gölge yalnız `.topbar` ve `.stage`'de (`--tedy-shadow-card`); iç kutular gölgesiz kalır
(`G-CARBON-GRID`). Tanım popover'ı Carbon ters yüzeydir (`background-inverse`,
`text-inverse`) ve `0 2px 6px var(--cds-shadow)` (shadow-menu) taşır.

## 5. Oyunlaştırma (yumuşatılmış)

XP, rozet ve seri korunur; dilleri Tedy'nin "kutlama yok" ilkesine yaklaştırıldı:

- Renk: ayrı altın ham-hex yoktur. `--reward` = `--tedy-text-warning` (Carbon sarısının
  metin-güvenli karşılığı), `--reward-bg` = `--cds-notification-background-warning`.
- Hareket: ölçek sıçraması yok. XP ve seri vurgusu kısa bir opaklık nabzıdır
  (`duration-moderate-02`, productive); "+N XP" 10 px yükselip söner (`duration-slow-02`);
  yeni rozet yalnız belirir. Hepsi `prefers-reduced-motion` altında kapalıdır.
- Kazanılan rozet sessiz "seçili" çiptir (`--cds-layer-selected-01`, `text-primary`):
  bitmiş iş öne çıkmaz, rozet avına dönüşmez.
- Dil: seri çipi "Seri 3" yazar; ünlem yok.

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
  `tests/test_mcp_gates_ek.py`; pano uçtan uca: `dashboard/tests/e2e/moduller.spec.ts` (tema devri).
- Otorite dosyasının bayt-özdeş kopyası CureoHub `services/edupedia_site/app/static/`
  altındadır (emekli katalog sitesi, `carbon.css` oradan üretilir); dosya burada değişince
  oraya da kopyalanır.
