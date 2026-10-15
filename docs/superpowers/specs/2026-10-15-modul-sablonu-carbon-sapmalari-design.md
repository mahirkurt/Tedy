# Modül şablonu: 4K eşliği ve kalan Carbon sapmalarının kapatılması

Tarih: 2026-10-15 · Durum: tasarım onayı bekliyor · Kapsam: `src/mcp_server/vendor/assets/module-template.html`

## 0. Niyet

Talimatname §11'de modül şablonu için açık kalan üç sapma kapatılır: **S19** (grafik paletinin
ders ailelerini kullanması), **S11** (statik yüzey gölgesi) ve **köşe yarıçapı** sapması.

Bu üç kalem *kaza değil, yazılı karardır*: §9.3 "Aşağıdaki farklar bilinçlidir ve kendi yerlerinde
gerekçelidir" der, S11 satırı `.topbar`/`.stage` gölgesini "modülün kendi kararı" diye adlandırır.
Bu yüzden iş yalnız CSS değiştirmek değil, **kararları geri almak ve gerekçelerini yeniden
yazmaktır**. Talimatname kuralı: çatışma §11'e yazılır, sessizce "düzeltilmez".

Aynı turda **4K eşliği** de istenmiştir (§10): modül, panonun kök yazı ölçeğini izler.

Kullanıcı kararı (2026-10-15): sapmalar kapatılır; S19 **biçimle** çözülür, renkle değil; 4K eşliği bu işe dahildir.

## 1. Ölçülenler

Her sayı bu tasarımın yazıldığı gün dosyadan okunmuştur.

| Olgu | Kaynak |
|---|---|
| `--viz-1..5` açık temada purple-70/blue-80/cyan-50/teal-70/magenta-70 | `module-template.html:378` |
| `--viz-1..5` koyu temada -40 adımları | `module-template.html:308` |
| Beş aile de `tagPairs` ders ailesidir (blue, cyan, teal, green, magenta, purple, red, gray) | `carbon-v11-authority.json` → `tagPairs` |
| `--viz-*`'ın ikinci tüketicisi: dilbilgisi rolleri | `module-template.html:947-951` |
| `art` rolü **ders aksanını** kullanıyor (`var(--accent)`) | `module-template.html:952` |
| Çubuk ve çizgi serisi varsayılanı tek renktir (`var(--viz-1)`) | `module-template.html:2305, 2320` |
| Çubuk ve nokta **zaten yerinde etiketlidir** (`label(p,i)`) | `module-template.html:2301` |
| `vizChart` tek çizgi serisi çizer (çoklu seri yok) | `module-template.html:2304-2314` |
| `--tedy-shadow-card` = iki `rgba()` katmanı (D1 alfa yasağı) | `module-template.html:249, 281` |
| Koyu temada gölge yok | `module-template.html:318` |
| `.topbar` ve `.stage` gölgeyi kullanıyor, ikisinde de 1 px `border-subtle` var | `module-template.html:429, 517` |
| `.def-pop` gölgesi Carbon'un geçici yüzey biçimi (`0 2px 6px var(--cds-shadow)`) | `module-template.html:552` |
| Yarıçap token değerleri Carbon `@carbon/layout` ile birebir | `_border-radius.scss`: `00:0px, 02:.125rem, 04:.25rem, 08:.5rem, max:999999px` |
| `.def-pop` 4 px kullanıyor (`-04`), Carbon popover'ı 2 px | `module-template.html:550` |
| `mark.term` **düz `4px` yazıyor** (token atlanmış) | `module-template.html:532` |
| **Kaskad hatası:** `[data-theme="g100"]` (`:284`) ile çıplak `:root` (`:336`) eşit özgüllükte (0,1,0); `data-theme` `documentElement`'e yazıldığı için ikisi aynı öğeyi eşler ve kaynak sırası kazanır → `:378` `:308`'i ezer, **koyu palet ölü koddur** | `module-template.html:284, 336, 378, 1565` |
| Bu yüzden g100'de bugün etkin olan değerler 3:1'i geçmiyor: purple-70 1,96:1 · blue-80 1,34:1 · magenta-70 1,97:1 (yalnız cyan-50 4,54:1 ve teal-70 3,03:1 geçiyor) | ölçüm; zemin `#262626` |
| `test_b52_seriler_viz_paletinde` yalnız `var(--viz-1)` referansını şart koşar, hex değeri sabitlemez | `tests/test_pano_talimatname_borclari.py:598-605` |

Kontrast ölçümü (3:1 metin-dışı grafik tabanı; zeminler şablonun kendi `--cds-layer-01`
değerleri: g10 `#ffffff:217`, white `#f4f4f4:254`, g100 `#262626:285`):

| Açık ramp | `#ffffff` | `#f4f4f4` | Koyu ramp | `#262626` |
|---|---|---|---|---|
| gray-100 `#161616` | 18,10:1 | — | gray-10 `#f4f4f4` | 13,76:1 |
| gray-90 `#262626` | 15,13:1 | — | gray-20 `#e0e0e0` | 11,46:1 |
| gray-80 `#393939` | 11,55:1 | — | gray-30 `#c6c6c6` | 8,86:1 |
| gray-70 `#525252` | 7,81:1 | — | gray-40 `#a8a8a8` | 6,36:1 |
| gray-60 `#6f6f6f` | 5,02:1 | 4,25:1 | gray-50 `#8d8d8d` | 4,56:1 |

Elenen iki aday: **gray-40 beyaz zeminde 2,38:1** ile düşer; **gray-50 white temasının `#f4f4f4`
zemininde 2,81:1** ile düşer (saf beyazda 3,32:1 ile geçmesine rağmen). Açık ramp bu yüzden
gray-60'ta durur.

## 2. S19 — kategoriyi biçim taşır, renk değil

### 2.1 Karar

Hiçbir yerde **hue** kategori taşımaz. Beş `--viz-*` yuvası tek bir nötr gri rampaya dönüşür;
kategoriyi ayıran şey yazıdır (grafikte zaten var olan yerinde etiket) ve dilbilgisinde altı
çizginin **biçimi**dir.

Gerekçe: ders aileleri (purple, blue, cyan, teal, magenta) ders işaretine ayrılmıştır ve
kırmızı/yeşil/sarı/turuncu anlam renkleridir (İ8). İkisini çıkarınca kategorik palete yedek hue
kalmaz — "başka renk seç" seçeneği yoktur. §7.5 P5: aynı görünüm iki anlam taşımaz.

### 2.2 Token değişikliği ve kaskad onarımı

Yalnız değerleri değiştirmek **yetmez, zararlıdır**: çıplak `:root` (`:336`) koyu bloğu ezdiği için
açık rampa g100'de `#262626` zemine düşer ve beş adımın dördü 3:1'i veremez (gray-90 zeminin tam
kendisidir, 1,00:1). Bu yüzden iki iş birlikte yapılır:

1. **Kaskad onarılır.** `--viz-1..5` çıplak `:root` (`:378`) bloğundan **çıkarılır** ve üç tema
   bloğunun her birinde ayrı ayrı bildirilir: g10 (`:215`), white (`:252`), g100 (`:284`). Böylece
   değer sıraya değil temaya bağlanır. (Dosyanın kendi deyimi de budur: ders aileleri
   `:root[data-subject-family="…"]` ile, yani kasıtlı olarak daha yüksek özgüllükle bildirilmiş.)
2. **Değerler nötr rampaya döner.**
   - g10 ve white (zeminler `#ffffff` / `#f4f4f4`):
     `--viz-1:#161616; --viz-2:#262626; --viz-3:#393939; --viz-4:#525252; --viz-5:#6f6f6f`
   - g100 (zemin `#262626`):
     `--viz-1:#f4f4f4; --viz-2:#e0e0e0; --viz-3:#c6c6c6; --viz-4:#a8a8a8; --viz-5:#8d8d8d`

Hepsi Carbon gri palet adımıdır (`test_ders_renkleri.py`'nin "palet dışı renk" denetimi geçer) ve
§1'de ölçülen kontrastı taşır. Token **adları korunur**: `test_b52_seriler_viz_paletinde`
`var(--viz-1)` referansını arar, değerini değil — tek noktadan değişince grafik, `fractionBar` ve
dilbilgisi rolleri aynı anda düzelir.

Kaskad onarımı kapsam genişletmesi değil, S19'un **ön koşuludur**: onarılmazsa koyu temada hangi
palet yazılırsa yazılsın okunmaz kalır.

### 2.3 Grafik motorunda yapılacak iş: yok

Ölçüm bunu gösterdi: her iki seri varsayılanı zaten `var(--viz-1)`, çubuk ve noktalar zaten
yerinde etiketli, `vizChart` tek çizgi serisi çiziyor. Desen dolgusu, çizgi kesikliği ve ayrı
nokta işareti **gerekmiyor**; eklenmeyecek. Lejant yuvarlakları rampadan beslendiği için
kendiliğinden nötrleşir.

Yazarın `p.color` ile hue geçirme yolu açık kalır ama artık palet ona ders ailesi sunmaz.

### 2.4 Dilbilgisi rolleri (`:945-952`)

`.tok .w` bugün `border-bottom:3px solid transparent` taşıyor ve rol rengi
`border-bottom-color`'dan geliyor. Renk tek ayırt edici değil — satır 942 yorumu zaten
"rol/cinsiyet renk-kodu DAİMA etiketle birlikte (CVD-güvenli)" diyor ve `.tg` etiketi rolü yazıyla
söylüyor. Yani taşıyıcı hâlâ etiket; renk ikincil ipucudur ve biçime devredilir.

Altı rol, altı ayrı biçim (`text-decoration-style` beş değer verir, altıncı işaretsizdir):

| Rol | Biçim |
|---|---|
| `masc` | alt çizgi `solid` |
| `fem` | alt çizgi `double` |
| `verb` | alt çizgi `dotted` |
| `noun` | alt çizgi `dashed` |
| `adj` | alt çizgi `wavy` |
| `art` | işaretsiz (işlev sözcüğü) |

Tek nötr renk: `--cds-border-strong`. `border-bottom` yerine `text-decoration` kullanılır, çünkü
`border-style`'da `wavy` yoktur ve sözcük işaretlemenin doğru özelliği budur
(`text-decoration-thickness:3px`, `text-underline-offset` ile bugünkü 3 px boşluk korunur).

**`art` rolünden `var(--accent)` kalkar.** Bu, ölçüm sırasında bulunan ve S19'un en keskin hâli
olan sapmadır: dilbilgisi rolü modülün kendi ders renginde çiziliyordu.

## 3. S11 — statik yüzeyde gölge yok

`--tedy-shadow-card` tanımı (`:249, :281, :318`) ve `.topbar` (`:429`) ile `.stage` (`:517`)
kullanımları kalkar. İkisinde de 1 px `var(--cds-border-subtle)` zaten var; derinlik katman
token'ı ve kenarla kurulur (S11, P4).

İki kazanç: statik yüzey gölgesi gider ve **iki `rgba()` alfa rengi** gider (D1 renk aritmetiği
yasağı).

`.def-pop`'un `0 2px 6px var(--cds-shadow)` gölgesi **kalır** — geçici yüzey gölgesi Carbon'da ve
S11'de meşrudur.

`G-CARBON-GRID` bugün `.card`/`.seg`/`.tile`/`.teach` seçicilerinde `inset` olmayan `box-shadow`'u
FAIL ediyor; `.topbar`/`.stage` o listede değildi. Liste genişletilmez: kapı sözleşmesi
`carbon-excellence §3`'tedir ve bu iş kapıyı değil şablonu değiştirir.

## 4. Yarıçap

- `.def-pop` (`:550`): `--cds-border-radius-04` → `--cds-border-radius-02`. Carbon popover'ı 2 px'tir.
- `mark.term` (`:532`): düz `4px` → `var(--cds-border-radius-00)` (0). İki kusur birden vardı:
  token sözlüğünün atlanması **ve** sistemde olmayan bir değer. S10 "kart/panel 8, çip/etiket tam,
  geri kalan 0" der; satır içi terim vurgusu "geri kalan"dır. Şablonun kendi yorumu da bunu söylüyor
  (`:366`: "Tedy'nin tek yumuşatması kart ve üst banttır (08); etiket/çip max").

§11'in "4 px" satırı bu iki kalemi birlikte anıyordu; ölçüm ikisinin farklı olduğunu gösterdi.

## 5. Belge değişiklikleri

Geri alınan her karar yeniden yazılır; satır silinmez, yeni gerekçe ve tarih ile güncellenir.

| Belge | Değişiklik |
|---|---|
| `docs/tedy-ui-ux-talimatnamesi.md` §11 **S19** | Modül grafikleri artık nötr rampa; kategoriyi etiket ve alt çizgi biçimi taşır; `--viz-*` ders ailesi değil |
| §11 **S11** | `.topbar`/`.stage` gölgesi "modülün kendi kararı" değil; kalktı. Geçici yüzey gölgesi (`.def-pop`) kalır |
| §11 "4 px" satırı | `.def-pop` 2 px'e indi; `mark.term` token'a bağlandı |
| §9.3 "Gölge" satırı | Pano ve modül artık aynı: yeni statik gölge yok |
| §13 **B2** | Modül tarafı kapandı notu; pano tarafı açık kalır |
| `vendor/references/tedy-integration.md` §4 | Köşe ve gölge dili: statik yüzey gölgesiz |
| `vendor/references/color-system.md` | `--viz-*`'ın rolü: nötr rampa, kategori taşıyıcısı değil |

## 6. Testler ve kapılar

Yeni/genişletilen testler (`tests/test_pano_talimatname_borclari.py`, şablonun kendi işlevlerini
node'da koşturan mevcut kalıpla):

1. `--viz-1..5`'in hiçbir değeri `tagPairs` ders ailesi tonu değil (üç tema bloğunun hepsinde).
1a. **Kaskad:** çıplak `:root` bloğu `--viz-*` bildirmiyor; üç tema bloğu bildiriyor. Her tema için
    *etkin* değer o temanın `--cds-layer-01` zeminine karşı ≥ 3:1 (yalnız bildirilen değil, kaskaddan
    sonra kazanan değer ölçülür — bugünkü hatayı yakalayacak olan test budur).
2. `--viz-*` değerleri Carbon gri palet adımı ve zeminine karşı ≥ 3:1 (tablo 1 kapı olur).
3. Şablonda `--tedy-shadow-card` yok; `.topbar`/`.stage` `box-shadow` taşımıyor; `.def-pop` taşıyor.
4. Şablonda `rgba(` yok.
5. Dilbilgisi rollerinin hiçbiri `var(--viz-*)` ya da `var(--accent)` kullanmıyor; altı rol altı
   ayrı `text-decoration-style`/işaretsiz hâl veriyor.
6. `mark.term` ve `.def-pop` yarıçapı token referansı (düz px yok).

Mevcut olup geçmesi gerekenler: `test_b52_seriler_viz_paletinde`, `test_ders_renkleri.py`,
`test_tedy_tasarim_tutarliligi.py`, `test_pano_tasarim_sistemi.py` ve 18 kapı (`G-CARBON`,
`G-CARBON-GRID`, `G-TOKEN`, `G-CONTRAST`, `G-SVG` doğrudan ilgili).

## 7. Süreç

1. Dosya `src/mcp_server/vendor/assets/` altında düzenlenir (tek kaynak).
2. `.venv/bin/python -m src.mcp_server.vendor_sync --pin` → dosya ve `PROVENANCE.json` **aynı commit'te**.
3. `sablon.py` çapaları yeniden doğrulanır (`TemplateDriftError`); bu iş çapa satırlarına
   dokunmaz ama doğrulama atlanmaz.
4. `.venv/bin/python -m src.mcp_server.derleme --ornek QUIZ --cikti /tmp/quiz.html` ile 18 kapı özeti.
5. Görsel kontrol: bir modül her iki temada açılır.

## 8. Riskler

| Risk | Karşılık |
|---|---|
| Nötr rampanın beş adımı birbirinden zor ayrılır | Kabul: taşıyıcı etiket, rampa ikincil ipucu. Her adım zemine karşı ≥ 3:1 (§1) |
| `text-decoration` geçişi `.tok .w` yerleşimini kaydırır | `text-underline-offset` ile bugünkü 3 px boşluk korunur; görsel kontrol (§7.5) |
| `wavy` tarayıcı desteği | Chromium/WebKit/Firefox'ta var; modül Chromium'da açılıyor. İşaretsiz `art` yedek değil, ayrı roldür |
| Kaskad onarımı başka token'ları da etkiler mi | Hayır: yalnız `--viz-*` taşınır. Çıplak `:root` bloğundaki diğer bildirimler yerinde kalır; taşıma sonrası üç temada görsel kontrol (§7.5) |
| Yazar `p.color` ile hue geçirmeye devam eder | Kapsam dışı: palet artık ders ailesi sunmuyor. Şema kısıtı ayrı iş |
| Belge satırları geri alınırken gerekçe kaybı | §5 satırları siler değil yeniden yazar; tarih ve yeni gerekçe ile |

## 9. Kapsam dışı

- `G-CARBON-GRID` seçici listesini genişletmek.
- `MODULE_DATA` şemasında `p.color` kısıtı.
- Panodaki açık B2 yerleri.

## 10. 4K eşliği

### 10.1 Sorun

Pano 2026-10-06'da kök yazı boyunu pencereyle büyütmeye başladı
(`dashboard/src/theme/ted-theme.scss:174`: `font-size: clamp(100%, calc(100vw / 120), 250%)`) ve
her ölçüyü `rem`'e çevirdi; `ekran-4k.spec.ts` bunu 14 sayfada sabitliyor. Modül bu işin dışında
kaldı: şablonun stil bloğunda **236 px değere karşı 84 rem** var, okuma sütunu
`.wrap{max-width:880px}` (`module-template.html:412`) ve kök ölçek kuralı **hiç yok** (yalnız token
blokları `:217/:254/:285/:336`). Sonuç: 3840 px ekranda panonun kendi kabuğu iki katına çıkarken
çerçevenin içindeki modül 880 px ve 18 px metinde kalır — tek sayfa içinde iki ayrı ölçek.

### 10.2 Ölçek nereden gelir: pano söyler

`.module-frame` `width:100%`'tir (`dashboard/src/components/Modules.scss:131`) ve panonun 60rem
sütununun içindedir; yani çerçevenin CSS genişliği `(60rem − sayfa dolgusu) × pano_kökü` kadardır.
Bu yüzden iki aday yol var ve ilki seçilmedi:

- **Reddedildi — CSS'ten türetme.** Modül `calc(100vw / k)` ile kendi görüntü alanından ölçeği
  türetebilirdi, ama `k` panonun sayfa dolgusuna bağlıdır: pano dolgusunu değiştirdiği gün modülün
  yazı boyu sessizce kayar. Dahası modül `modul.tedy.online`'da tek başına da açılabilir; orada
  `100vw` tüm ekrandır ve aynı kural ölçeği fahiş büyütür.
- **Seçildi — pano kök boyunu bildirir.** Mevcut `edupedia:appearance` mesajı zaten tasarım değeri
  taşıyor (tema). Buna **isteğe bağlı** sayısal bir alan eklenir: `rootPx` — panonun o andaki
  hesaplanmış kök yazı boyu
  (`parseFloat(getComputedStyle(document.documentElement).fontSize)`).

Bu alan okurun kendi tarayıcı yazı boyu tercihini **korur**: panonun `clamp()`'inin tabanı `100%`
olduğu için hesaplanmış değer tercihi zaten içinde taşır; modül o değeri birebir uygulayınca
panoyla aynı sonucu üretir.

Sözleşme ayrıntıları:

- Alan **isteğe bağlıdır**, `v` 1'de kalır: `G-BRIDGE` `edupedia:appearance`'ı "izinli ama zorunlu
  değil" sayar (§9.5), eski pano ve tek başına açılış mesaj göndermez.
- Mesaj yoksa modül 16 px'te kalır — bugünkü davranış birebir korunur (geriye uyum).
- Modül değeri `12`–`48` px aralığına **kıstırır** ve sayı değilse yok sayar; çerçeve opak kökenli
  olduğu için gelen değer yine de doğrulanır (tema için `adoptHostTheme`'in yaptığının aynısı).
- Uygulama: `document.documentElement.style.fontSize = rootPx + "px"`.
- İlerleme ya da kişisel veri taşımaz; saklanmaz.

### 10.3 Şablonda yapılacak iş

1. **px → rem** (`n px → n/16 rem`), panonun kendi kuralıyla aynı istisnalar: kenarlık ve ≤ 3 px
   saç çizgileri px kalır, `@media` kırılma noktaları px kalır (medya sorgusunda `rem` kök boyunu
   değil tarayıcı varsayılanını kullanır).
2. `.wrap{max-width:880px}` → `55rem`; `.card{max-width:540px}` → `33.75rem` ve benzerleri.
3. **İkon kuralı gerekmiyor** (ölçüldü). Panonun `ted-theme.scss:185`'ten başlayan 9 adet
   `:where(svg[width='N'][height='N'])` kuralı, Carbon React ikonlarının öznitelikle gelen 16 px'ini
   yakalamak içindir. Şablonun ikonları ise CSS ile boyutlanır: `icon()` (`module-template.html:1297`)
   `class="cds-icon"` yazar ve `size` verilmedikçe `width`/`height` özniteliği **koymaz**. Öznitelikli
   tek tek SVG'ler (`120`, `32`, `28`) durağan işaretlemededir. **Denetim turunda (2026-10-15) bu
   dayanağın iki yerde tutmadığı ölçüldü** ve ikisine CSS boyutu verildi: `.pacing-disk__ring`
   (`width="28"`, kuralı yalnız `flex:none`) ve bölüm resmi (`icon(ref,"pic",96)`, `.pic` boyut
   vermiyor) — ikisi de 3840 px'te yerinde kalırdı. Kural yine taşınmadı, çünkü kalan öznitelikli
   SVG'lerin sınıfları CSS boyutu taşıyor; kapı `test_4k_oznitelikli_svgler_css_boyutu_tasir`.
4. `--sp-*` ve tipografi değişkenleri rem tabanlı olmalı; px olan varsa çevrilir.
5. SVG `viewBox` değerleri birimsizdir, dokunulmaz; `font-size:10px` gibi SVG içi mutlak değerler
   rem'e çevrilir (`.quest-map__label`, `module-template.html:514`).

### 10.4 Pano tarafında yapılacak iş

- `dashboard/src/utils/moduleBridge.ts`: `appearanceMessage(theme)` → `appearanceMessage(theme, rootPx)`;
  `rootPx` çağrı anında okunur.
- `ModuleViewer`'ın `onFrameLoad`'u mesajı bugünkü gibi `load`'da gönderir. Pencere yeniden
  boyutlandığında pano kökü değişir; mesaj **yeniden gönderilir** (kısıtlanmış `resize` dinleyicisi),
  yoksa modül ilk ölçekte kalır.

### 10.5 Belge ve test

| Belge | Değişiklik |
|---|---|
| Talimatname §9.3 "Sütun" satırı | 880 px → 55rem; modül de rem tabanlı |
| Talimatname §9.4 ve altındaki cümle | "Tasarım açısından akan **tek şey** temadır" artık doğru değil: tema **ve** kök ölçek akar |
| `vendor/references/tedy-integration.md` §2 | `edupedia:appearance`'ın `rootPx` alanı ve kıstırma kuralı |
| Talimatname §11 (yeni satır) | Modülün kök ölçeği panodan gelir; sapma değil, eşlik |

Testler:

1. `G-BRIDGE` **değişmez** (ölçüldü): kapı mesaj *tiplerini* denetler, alanları değil
   (`gates_ek.py:127-130`) ve `edupedia:appearance` zaten `OPTIONAL_BRIDGE_TYPES`'tadır
   (`gates_ek.py:17`). `rootPx` bir alandır, yeni tip değil — kapı olduğu gibi geçer. Yine de
   regresyon testi yazılır: `rootPx` taşıyan derlenmiş modül `G-BRIDGE`'den FAIL almaz.
2. `moduleBridge` birim testi: `appearanceMessage` kök boyunu taşır; şema doğrulaması geçer.
3. Şablon birim testi: `rootPx` uygulanınca `documentElement.style.fontSize` değişir; mesaj yokken 16 px.
4. e2e: derlenmiş bir modül 1920 ve 3840 px'te açılır; sütun ve ikonlar 3840'ta iki katı; yana kaydırma yok.
   `ekran-4k.spec.ts`'in modül karşılığı.
5. Şablonda kalan px: yalnız kenarlık/saç çizgisi ve `@media` değerleri (kapı testi).

### 10.6 Risk

| Risk | Karşılık |
|---|---|
| 236 değerin elle çevrilmesinde hata | Dönüşüm betikle yapılır, diff okunur; görsel taban iki temada karşılaştırılır |
| Kök boyu değişince modül içi `100vh` ölçüleri | `vh` kökten bağımsızdır, etkilenmez; `.wrap{min-height:100vh}` korunur |
| `resize`'da mesaj seli | Dinleyici kısıtlanır (`requestAnimationFrame` ya da 150 ms); değer değişmediyse gönderilmez |
| Tek başına açılışta ölçek yok | Kasıtlı: mesaj yoksa 16 px. Pano içi kullanım birincil yoldur |
