# İşler yenilemesi — tasarım

**Tarih:** 2026-10-15 · **Yüzey:** `/isler` — `dashboard/src/components/HomeworkTracker.tsx` (+ `HomeworkTracker.scss`,
`utils/isler.ts`) · **İstek:** "isler sayfasını carbon mcp kullanarak tekrar tasarla" · **Öncelik:** anayasa D1–D4 /
İ1–İ9 > talimatname (§3–§5, §11, §12) > yüzey tasarımları §4.2 > Carbon. **Durum:** 2026-10-15'te
`worktree-agent-ae48bb5000264af46` dalında uygulandı (`205c2f8`), ana dala birleşmedi; 2026-10-20'de bugünkü ana dalın
üstüne `isler-yenileme` dalında taşındı (§7). Talimatname §14.1 adım 4'ün kullanıcı onayı bu dalın ekran görüntüleri
üzerinden verilecek.

## 1. Bugün ne var (ölçüldü, `isler-ekran/once/`, `GORSEL` fikstürü, `SABIT_SAAT` 24.09.2026 10:30)

- **Aynı iş iki kez.** "Sıradaki" paneli (`NextThing`) ilk ödevi adlandırıyor; "Aktif ödevler"in ilk satırı aynı ödev
  (İ1; Bugün'ün "kartın işi listede bir daha yazılmaz" kuralına aykırı).
- **Kart içinde kart.** Sayfa tek `.dashboard-card`; içinde `<Layer>`'lı panel ve her satırda ayrı `Tile` — üç kat kap.
- **Satır başına beş sinyal.** Renkli sol kenar, ders karesi, geri sayım `Tag`'i ("1g 1s"), `tertiary` "Yaptım" ve tam
  genişlikte bir çubuk. Çubuk `getCountdown().fraction` = "7 günlük pencerenin geçen kısmı"dır: portalda böyle bir
  pencere yok, uydurma bir oran veri gibi duruyor (D4, İ6). "Teslim: 25 Eyl 2026 12:00" ve "İlk görülme: …" ayrıca.
- **Bitmiş işte alarm.** "Tamamlandı" (öğretmen "Yaptı") satırlarında "Süresi doldu" etiketi (yüzey tasarımları §2.7
  yasağı); "Yapılan" grubundaki her satır "Yapılan" etiketini, "Tamamlandı"daki her satır "Yaptı"yı tekrar ediyor.
- **Sınavlar.** Liste elle kurulmuş `ul`; "Tüm sınavlar" listenin altında çıplak bağlantı; başlık bir `div`, düğme değil.
- **Durumlar.** İlk yükleme 400 ms'yi geçerse iskelet yok; `/api/homework` hata verirse sayfa "Şu an teslim bekleyen bir
  işin yok." diyor (D3: arıza boşluk kılığında). Başlıklar `h2` değil ([3.8-9]).
- **Portal metni büyük harf.** "2. HAFTA MATEMATİK HAFTA İÇİ ÖDEVİ" 28 px'lik başlıkta da öyle. Talimatname [3.3-6]
  (S38): "Portaldan büyük harfle gelen veri gösterilirken cümle düzenine çevrilmez ama kalınlaştırılmaz." **Karar:
  çevrilmez.** Bizim metnimiz cümle düzenindedir; portalın başlığı onun adıdır (D4: anlam değiştirilmez). `heading-04`
  400 ağırlıkta kalır, kalınlaşmaz.

## 2. Carbon ne der (MCP `docs_search`; bileşenler `code_search` `component_type: "React"` + `node_modules`)

| Kural | Kaynak |
|---|---|
| Contained list benzer içeriği gruplar, okunur ya da etkileşimli olabilir; satır içi eylem ve etkileşimli öğe içeren listede, aynı yapıdaki öğeler için | [contained-list/guidelines#contained-list](https://carbondesignsystem.com/building-blocks/core/components/contained-list/guidelines/#contained-list) · [#when-to-use](https://carbondesignsystem.com/building-blocks/core/components/contained-list/guidelines/#when-to-use) |
| Liste satırı satır içi eylem taşıyabilir (satırı kapatma ya da kaldırma gibi) | [contained-list/guidelines#inline-actions](https://carbondesignsystem.com/building-blocks/core/components/contained-list/guidelines/#inline-actions) |
| Tıklanabilir satır bir sekme durağıdır, Enter/Boşluk ile çalışır; satırın eylemi ayrı bir durak — satır başına birden çok durak olabilir | [contained-list/accessibility#keyboard-interactions](https://carbondesignsystem.com/building-blocks/core/components/contained-list/accessibility/#keyboard-interactions) |
| Structured list terim–tanım içindir (tarama, sütun başlıkları); data table sıralama/seçim ister — burada ikisi de yok | [structured-list/guidelines#structured-list](https://carbondesignsystem.com/building-blocks/core/components/structured-list/guidelines/#structured-list); talimatname §4.5 |
| Taşma menüsü ek seçenekler ve yer darlığı içindir | [menu-buttons/guidelines#overflow-menu](https://carbondesignsystem.com/building-blocks/core/components/menu-buttons/guidelines/#overflow-menu) |
| ProgressBar kullanıcı eylemiyle belirlenen ilerleme için değildir | [progress-bar/guidelines#when-not-to-use](https://carbondesignsystem.com/building-blocks/core/components/progress-bar/guidelines/#when-not-to-use) |
| Etiket başka sayfaya giden bağlantı ve çok işlevli öğe olmaz | [tag/guidelines#when-not-to-use](https://carbondesignsystem.com/building-blocks/core/components/tag/guidelines/#when-not-to-use) |
| İkon göstergesi: ikon + şekil + anlamlı renk + açıklayıcı etiket; renk tek başına yetmez | [status-indicators#icon-indicator](https://carbondesignsystem.com/building-blocks/core/patterns/status-indicators/#icon-indicator) · [#icon-indicator-statuses](https://carbondesignsystem.com/building-blocks/core/patterns/status-indicators/#icon-indicator-statuses) |
| Boş durum, gösterilecek veri olmadığında ortaya çıkar | [empty-states#empty-states](https://carbondesignsystem.com/building-blocks/core/patterns/empty-states/#empty-states) |
| Açılır içerik kullanıcı başlatır, iç içe açılmaz, kritik bilgi saklamaz | [disclosures#disclosures](https://carbondesignsystem.com/building-blocks/core/patterns/disclosures/#disclosures) · [#avoid-nesting-disclosures](https://carbondesignsystem.com/building-blocks/core/patterns/disclosures/#avoid-nesting-disclosures) |
| Görünüm başına bir birincil; geçici akış (modal) kendi birincilini getirebilir | [button/guidelines#primary-button](https://carbondesignsystem.com/building-blocks/core/components/button/guidelines/#primary-button) (talimatname §4.2) |
| Tarih/saat biçimi etiket ya da yardım metninde; 24 saat | [date-picker/guidelines#date-format](https://carbondesignsystem.com/building-blocks/core/components/date-picker/guidelines/#date-format) (talimatname [3.9-6]) |

Doğrulanan adlar (`code_search` + `node_modules/@carbon/react` 1.114, `@carbon/icons-react`): `ContainedList`
(`kind`, `size`, `label`, `action`, `className`), `ContainedListItem` (`action`, `onClick`, `className`; `onClick`
`() => void`), `ComposedModal` (`selectorPrimaryFocus`), `ModalFooter` (`primaryButtonText`, `loadingStatus`,
`loadingDescription`, `loadingIconDescription`, `onRequestSubmit`; ikincil metin verilmezse ikinci düğme yok),
`InlineNotification`, `InlineLoading`, `SkeletonText`, `SkeletonPlaceholder`; ikonlar `WarningFilled`,
`ChevronDown`/`ChevronUp`, `CloseFilled`, `Incomplete` (son ikisi `lib/index.js` dışa aktarımında görüldü; MCP
indeksi "incomplete" aramasında bulmadı).

## 3. Tasarım

### 3.1 Yerleşim

Tek sütun (S1, 60rem), **sayfanın kendisinde** — kart yok, kart içinde kart yok (S11). Bölümler boşlukla
(`$spacing-06`, Bugün'ün ritmi) ve başlıkla ayrılır:

1. **Sıradaki** — `NextThing`, görünümün tek ders paneli (İ8.3): ders adı + portal başlığı, "Teslim yarın 12:00"
   (Bugün'le aynı cümle), "10 dakikayla başla", birincil **Başla**.
2. **Ayrıca (n)** — aktif işin geri kalanı, teslim sırasıyla. Sözcük Bugün'ün aynı kavram için kullandığıdır (İ9).
3. **Yaklaşan Sınavlar (n)** — başlığın eylem yuvasında **Tüm sınavlar** (ad başlığı başlık düzeninde, §7).
4. **Yapılan (n) · Tamamlandı (n) · Yapılmayan (n)** — kapalı başlar (İ7, S34).

| Kırılım | Davranış |
|---|---|
| ≥ 672 px | Satır: ders işareti + ad solda, gün + saat sağda (`grid`, 3 sütun), eylem Carbon'un eylem yuvasında. Panel düğmesi sağda. |
| < 672 px | Satır içi alt alta: ad, (karar etiketi), gün + saat. Panel düğmesi tam genişlik (NextThing'in kendi kuralı). Kenar 16 px (`$spacing-05`, Carbon satır dolgusu). |
| > 1920 px | Kök ölçek (S25); her ölçü `rem`, ikonlar `:where(svg[…])` kuralıyla. |

### 3.2 Tek birincil eylem

Sayfada tek `kind="primary"`: paneldeki **Başla** (S12, İ1). Başla işin penceresini açar; pencerenin tek eylemi
**Yaptım**'dır (ModalFooter birincili — geçici yüzey kendi birincilini taşır, §4.2). Akış Bugün'ün kutusuyla aynı
adları taşır: Başla → Yaptım → "Yaptın: … · Geri al" (İ9). Önceden İşler'de sıradaki işin "Yaptım"ı yalnız listedeki
kopyasındaydı; tekrar kalkınca pencere onun tek yeri olur. Pencerenin ilk odağı **Kapat**'tır (öncekiyle aynı): ilk
odağı "Yaptım" olan bir pencerede tek bir yanlış Enter işi kaydeder → **S53**.

### 3.3 Satır neyi taşır, neden

Satır Carbon'un tıklanabilir `ContainedListItem`'ıdır, `size="lg"` (48 px): **bütün satır tek düğme**, işin
penceresini açar (B46 artık Carbon'un kendi denetimi). Satırın içinde yalnız:

- **Ders işareti + "Ders — Başlık"** (`SubjectLabel`; ders rengi yalnız 10 px kare, İ8);
- **Öğretmen kararı**, yalnız grup birden çok karar taşıyorsa ("Yapılmayan": "Yapmadı" kırmızı + `CloseFilled`,
  "Eksik" gri + `Incomplete`; S4, B16). "Yapılan" ve "Tamamlandı" satırlarında grubun adını tekrar eden etiket yok (İ6).
- **Ne zaman**: gün ve saat (`utils/isler.ts` `teslimMetni`: "Yarın 12:00", "Pazartesi 08:55"; haftadan uzaksa tarih +
  uzaklık "1 Eki 09:00 · 7 gün sonra", İ2; geçmişte düz tarih). Rakamlar `Rakamli` ile Mono, sözcükler Sans (S22, B36).

Satırın **tek eylemi** Carbon'un eylem yuvasındadır: "Ayrıca"da ghost lg **Yaptım** (`aria-describedby` satırın
adına, [3.8-6]), "Yapılan"da ghost lg **Geri al: …** (B63), sınavda **Modülü aç**. Taşma menüsü seçilmedi: "Yaptım"
satırın en sık eylemidir, ek bir seçenek değil; menünün arkasına saklamak her işaretlemeye iki dokunuş ekler ve
eylemin adını gizler (Carbon: taşma menüsü ek seçenekler ve yer darlığı için; İ1). Satır başına iki sekme durağı
(satır + eylem) Carbon'un klavye modelidir. Metinli düğme Carbon'un ikon için ayırdığı 4rem'lik yuvaya sığmadığı için
satır içeriğinin sonu masaüstünde 10rem, telefonda 6rem boşaltılır (S3 seçicisi, **S52**).

**Kaldırılanlar:** geri sayım `Tag`'i (gün + saat cümlesi yerine geçti), çubuk (doğru ve okunur bir şey söylemiyordu),
renkli sol kenar, satırdaki "Teslim:"/"İlk görülme:" satırları (ilk görülme pencerede kalır), "Süresi doldu" etiketi.

### 3.4 Teslim, aciliyet ve durum

- Kırmızı yalnız **gerçek aciliyette**: bugün teslim. `WarningFilled` (`--ted-support-error`) + "Bugün 18:00"
  (`--ted-text-error`, -70) — ikon + sözcük + renk (S4; gri tonlamada ikon ve "Bugün" kalır). Aktif listede gecikmiş iş
  olmaz: teslimi geçen iş "Yapılmayan"a düşer ve orada alarm değil geçmiştir (§2.7).
- Yarın ve sonrası nötr (`text-secondary`). Geçmiş grupların adı `text-secondary` (İ7).
- Pencerede: durum etiketi (ikonlu), "Son teslim" + aynı gün/saat sözcükleri + tam tarih, "İlk görülme".

### 3.5 Sınavlar ve geçmiş gruplar

- Sınavlar aynı liste kalıbı: Carbon on-page `ContainedList`, etiketi `h2` "Yaklaşan Sınavlar (n)", eylem yuvasında
  ghost lg **Tüm sınavlar** (`href="/sinavlar"`, Bugün'ün "+N iş daha" ile aynı biçim). Başlık dersi zaten söylüyorsa
  ders ayrıca yazılmaz (eski kural korunur). Satır tıklanmaz (gidecek yer başlıktaki bağlantı); modül varsa satır eylemi.
- Geçmiş gruplar: başlık `h2` içinde gerçek düğme, "Başlık (n) ⌄", `aria-expanded` + `aria-controls` her zaman var
  olan bir bölgeye (`hidden`). Carbon'un on-page başlığıyla satır satır aynı çizilir (`heading-compact-01`, 48 px,
  alt çizgi, 16 px dolgu) — sayfadaki bütün başlıklar tek sistem.

### 3.6 Durumlar

| Durum | Görünüm |
|---|---|
| Yükleniyor < 400 ms | Hiçbir şey (S36, B48) |
| Yükleniyor ≥ 400 ms | Sayfanın şekli: panel yerinde `SkeletonPlaceholder`, `SkeletonText` başlık + 3 satır; kök `aria-busy="true"` |
| Hata (`/api/homework`) | Hata `InlineNotification` (`lowContrast`, `role="alert"`, "Ödevler yüklenemedi." + ne yapılacağı, `apiHataCumlesi`); boş cümle **gösterilmez** (D3); eski veri varsa altında durur |
| Boş | "Şu an teslim bekleyen bir işin yok." (`EmptyLine`, tek satır) |
| Sınavlar alınamadı | "Yaklaşan sınavlar şu an alınamadı." (`role="status"`) |
| Portal bölümü okunamadı / kapalı | Kabuğun `PortalStatusBanner`'ı (değişmedi) |
| "Yaptım" başarısız (satır) | Satırın hemen altında `role="alert"` cümle |
| "Yaptım" başarısız (pencere) | Pencerede hata `InlineNotification` "Kaydedilemedi"; pencere açık kalır |
| Odak kipi | Panel + "Ayrıca (n)" kapalı (sayı görünür); sınavlar ve geçmiş gizli (§5.11) |

### 3.7 Erişilebilirlik

- Başlıklar gerçek `h2` (sayfa `h1`'i kabukta); pencerede "Ekler" `h3` (pencere başlığı `h2`).
- Satır tek düğme, eylem ayrı durak (Carbon klavye modeli); "Yaptım" tekrarlandığı için satırın adıyla
  `aria-describedby` ([3.8-6]).
- Pencere kapanınca odak açan satıra döner ([3.8-8]); "Yaptım" sonrası odak "Yaptın: …" satırına (B40).
- Telefonda sayfadaki her denetim ≥ 44 px (başlık düğmeleri 48, satırlar 48, eylemler lg 48; S18).
- Zorlanmış renk: panelin ve başlıkların gerçek kenarları var; Carbon satır ayraçları yüksek kontrastta `CanvasText`.
- Azaltılmış hareket: sayfa kendi hareketini yazmaz; Carbon geçişleri genel kuralla durur.

## 4. Sapmalar (§11)

- **S52** — Contained list satır eylemi metinli ghost lg düğmedir; Carbon'un ikon için ayırdığı 4rem yerine 10rem
  (telefonda 6rem) boşaltılır (`.isler-liste .cds--contained-list-item--with-action .cds--contained-list-item__content`,
  S3: ölçüm yorumu, prop yok, taban okundu).
- **S53** — Eylemli ödev penceresinin ilk odağı birincil değil **Kapat**'tır.

## 5. Kapılar

`tests/isler.test.ts` (9, node:test; ikisi §7 taşımasında eklendi), `tests/e2e/isler-yenileme.spec.ts` (tekrar yok, tek birincil, satır yapısı ve
klavye, aciliyet sözcük + ikon + renk, yalnız rakam Mono, sınav başlığı eylemi, geçmiş grupların açılması, pencerede
Yaptım ve hatası, iskelet ve hata, 44 px, axe + IBM Equal Access 1440/390 gruplar açıkken, 320/390/1440/3840'ta yana
kaydırma yok). Var olan davranış testleri yeni sunuma göre seçici değiştirdi; hiçbir iddia gevşetilmedi.

## 6. Açık kalan

- Bugün'ün "Ayrıca" ve "Sınavlar" hücreleri `kisaTeslim`'i küçük harfle ("yarın 12:00") ve uzak tarihi uzaklıksız
  yazar; İşler hücreleri cümle düzeninde ve uzaklıklı (`teslimMetni`). Bugün'ün tabanı bu işin kapsamında değil → **B82**.

## 7. Ana dala taşıma (2026-10-20)

`205c2f8` bugünkü ana dalın (`28029c0`) üstüne `isler-yenileme` dalında seçilip (cherry-pick) çakışmaları çözüldü. Ana
dal 2026-10-15'ten sonra İşler'e ve kurallara şunları eklemişti; hepsi yeni satırda korunur:

- **Sınav satırı** (`1dde7ec`, `613b015`, `3d27060`): son 48 saatte bulunan ya da değişen sınavda gri "Yeni"/"Değişti"
  etiketi (`SinavKarti` `SinavEtiketi`; sayfanın dakikalık saatinden okunur, render içinde `Date.now()` yok — C16), ızgaranın
  orta sütununda, karar etiketiyle aynı yerde. Zaman `utils/isler.ts` `sinavZamani` ile: saatli sınav teslim gibi
  ("Yarın 09:40"); tüm gün sınav (API `allDay` ya da çıplak "YYYY-MM-DD", yerel gün — C11, C20) yalnız günüyle
  ("Pazartesi", saat uydurulmaz; `teslimMetni(…, saatsiz)` `kisaGun`'ü kullanır); yalnız haftası bilinen ya da günsüz sınav
  sınav sayfasının sözcükleriyle ("28 Eyl haftası", "Tarih belirsiz").
- **İncelenemedi notu**: son tespit turunda okunamayan duyuru varsa listenin altında, satır metninin hizasında; liste
  boşken tek başına (`IncelenmediNotu`). Odak kipinde sınavlarla birlikte gizli.
- **Başlık düzeni** (S38, 2026-10-19 revizyonu): bölüm adı bir addır → "Yaklaşan Sınavlar (n)"; "Ayrıca", "Yapılan",
  "Tamamlandı", "Yapılmayan" tek sözcük. Cümle olan "Yaklaşan sınavlar şu an alınamadı." cümle düzeninde kalır.
  `test_s38_ad_basliklari_baslik_duzeninde` başlığı yakalar (küçük harfli hâliyle düştüğü denendi).
- **Uygulama içi bağlantı** (C13, `utils/gezinme.ts`): "Tüm sınavlar" düz tıkta uygulama içinde gider, Ctrl/Cmd/orta
  tık tarayıcıya kalır.
- Fotoğraflı ödev ve belgeler (`YuklemeAlani`, belge silme onayı), "Asistana sor", "Yaptım/Geri al" akışı (S40, B63),
  odak kipi, 400 ms iskeleti ve hata bildirimi 2026-10-15 sürümünde zaten vardı; davranışları değişmedi.

**Numaralar.** Bu belgenin ilk sürümündeki S51, S52 ve B81 ana dalda başka işlerce alınmıştı (B81 modül kanunu satır
ölçüsü; S51 bekleyen akşam çalışma planı dalı). Bu belgede ve her yerde **S52** (satır eylemi metinli), **S53** (ilk odak
Kapat) ve **B82** (Bugün hücreleri; artık Bugün'ün sınav önizlemesini de kapsar) olarak yeniden numaralandı. Talimatname
2.3, yüzey tasarımları 1.19.
