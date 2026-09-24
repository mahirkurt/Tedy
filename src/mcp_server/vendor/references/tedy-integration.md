# Tedy ile bütünlük (tedy-integration.md)

edupedia modülleri Tedy panosunun içinde, `ModuleViewer`'ın tam genişlikli çerçevesinde
açılır. Bu belge, modülün panoyla **tek bir yüzey** gibi okunması için şablonun (v1.9.0)
uyguladığı kuralları toplar. Kural kaynağı Tedy Tasarım Sistemi v3'tür (Carbon v11'in
kendisi + `tedy-*` katmanı); depodaki karşılığı `dashboard/src/theme/ted-theme.scss`'tir.

## 1. Katman modeli

Carbon token'larının **hiçbiri** yeniden tanımlanmaz veya anlamı değiştirilmez; `G-TOKEN`
her tema bloğunu `@carbon/themes` otoritesine karşı denetler. Tedy'ye özgü dil yalnız
`tedy-*` token'larıyla **üstüne** eklenir. Bu değerlerin makine-okunur tek kaynağı
`assets/carbon-v11-authority.json` → `tedyLayer`'dır: her token için Carbon palet adımı, hex ve
panoda aynı rolü taşıyan `--ted-*` değişkeni (pano adları: `--ted-color-brand-primary`,
`--ted-color-brand-primary-hover`, `--ted-color-page-bg`, `--ted-text-success/-error/-info/-warning`).

| Token | g10 (varsayılan) | white (eski kayıt) | g100 | Kullanım |
|---|---|---|---|---|
| `--tedy-brand` | `#002d9c` | `#002d9c` | `#002d9c` | Yalnız üst kimlik bandı ve işaretin onayı. Eylem rengi değildir. |
| `--tedy-brand-hover` | `#001d6c` | `#001d6c` | `#001d6c` | Bant üstündeki çipler ve ikon düğmesi hover'ı. |
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

## 3. Kimlik bandı ve ders aksanı

- Üst bant düz `--tedy-brand` zemindir; solda Tedy işareti (beyaz disk, yarı saydam beyaz
  hilal, lacivert onay; renkler token, `aria-hidden`), üzerinde `text-on-color` başlık.
  Gradyan, radyal parıltı, ham hex ve cam (`rgba`) yüzey yoktur.
- Bant üstündeki XP ve seri çipleri Carbon Tag'dir: `--tedy-brand-hover` zemin,
  `text-on-color` metin. XP yıldızı `--cds-support-warning` (lacivert üstünde 7,3:1).
- Ders aksanı (`--accent`) bantta **değildir**; yalnız odak çapalarında yaşar: bölüm ikon
  karosu (`.seg-ic`), `kicker` ve bölüm başlığı çizgisi, seçili/hover seçenek halkası,
  anlatım kutularının 4 px sol çizgisi, tanım etiketi, zaman çizelgesi düğümü,
  piktogramlar ve küçük işaretler (boşluk alt çizgisi, çözümlü örnek adım numarası).
  Anlatım kutuları (`.lead`, `.hook-card`, `.se-model`, `.callout`, `.self-assess`)
  nötr `--cds-layer-02` yüzeydir; tint dolgu ve özet gradyanı kaldırıldı.
- İlerleme göstergesi arayüz kabuğudur: Carbon `button-primary`/`interactive`
  (ders aksanı değil).
- Kırmızı ders aksanı olarak kullanılmaz: Türkçe **magenta-60** (`#d02670`) taşır.
- `meta.accent` isteğe bağlıdır ve yalnız `tedyLayer.subjectAccents.allowed` listesindeki bir
  değeri (Carbon mavi, camgöbeği, turkuaz, yeşil, magenta, mor, gri adımları) alabilir; derleyici
  (`edupedia_derle`) başka her değeri şema hatasıyla reddeder. En iyisi hiç yazmamaktır — aksan
  konudan türetilir. MODULE_DATA'ya renk, tema ya da CSS yazılmaz.

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

- `scripts/sync_carbon_tokens.py --check`: g10 · white · g100 bloklarını ve Tedy katmanını
  (17 değer) otoriteye karşı diff'ler (eski modüllerde kısa adlar ve `:root` white bloğu da okunur).
- `scripts/validate_module.py` → `G-TOKEN` g10'u da denetler; açık temalarda
  `--cds-support-info:#4589ff` FAIL'dir.
- Depo testleri: `tests/test_tedy_tasarim_tutarliligi.py` (pano `ted-theme.scss` ↔ şablon ↔
  otorite: aynı Carbon adımları, tek pano teması, izinli aksanlar), `tests/test_mcp_sablon.py`,
  `tests/test_mcp_gates_ek.py`; pano uçtan uca: `dashboard/tests/e2e/moduller.spec.ts` (tema devri).
- Otorite dosyasının bayt-özdeş kopyası CureoHub `services/edupedia_site/app/static/`
  altındadır (emekli katalog sitesi, `carbon.css` oradan üretilir); dosya burada değişince
  oraya da kopyalanır.
