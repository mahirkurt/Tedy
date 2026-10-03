# Önyüz denetimi — D3b, görev 1 (2026-10-03)

Kod değişmedi. Spec: `docs/superpowers/specs/2026-10-02-asistan-zengin-cevap-yukleme-onyuz-design.md`, bölüm "D3b — Denetim". Anayasa: `docs/frontend-design-principles.md` (D1–D4, İ1–İ9, İ8'in 2026-10-02 hâli).

## Nasıl ölçüldü

Playwright, `dashboard/tests/e2e/_audit-fixtures.ts` içindeki `FULL`, 13 sayfa (`tasarim-denetimi.spec.ts` ile aynı liste) × 1440×900 ve 390×844. Yatay taşma: `scrollWidth - innerWidth`. Dokunma kutusu: görünen `button` / `a` / `[role=button]` sınır kutusu. Ödev penceresi: saat dondurulmuş `/isler` üzerinde "Başla", sonra diyalogdaki düğmelerin erişilebilir adı.

İki saat:

- **Canlı:** 3 Ekim 2026 Cumartesi, tarayıcı saati 06:57. FULL'un Eylül teslimleri bu günde süresi dolmuş; İşler'de aktif liste boş.
- **Dondurulmuş:** `2026-09-01T10:00:00+03:00` (tarayıcıda 07:00, Salı). Aktif ödev ve "Başla" bu sette görünür.

Ekran görüntüleri repoya konmadı. Yatay taşma her sayfada, her iki genişlikte **0 px**.

FULL bazı sayfalarda canlı API'nin şeklini taşımıyor. O satırlar aşağıda "Fikstür" — ürün kusuru diye yazılmadı.

## Önce: kullanım zor, telefonda kötü

Sıra, sonraki sayfa yenilemesinin sırası (Bugün → İşler → Asistan → Dersler, Takvim, Notlar).

### Bugün — gün okları 28×28

`Önceki gün` ve `Sonraki gün` telefon ve masaüstünde **28×28 px** (`1.75rem`, `.today__nav-btn`). D3b'nin sayfa kapısı 44 px. Şerit saat tikleri 42rem altında bilerek gizli (`DayStrip.scss`); "ŞİMDİ", kalan süre, "yatma" ve "odak sonu" duruyor.

Canlı Cumartesi 06:57: adlandırılmış adım okuma ("Tedy Books — The Hobbit", "15 dakikayla oku", "Bunu okuldan sonra yapmak daha kolay"). Altında "Cumartesi için planlı ders, ödev teslimi veya etkinlik yok." Tek adım okunuyor (İ1).

### İşler — kapatma düğmesi İngilizce "Close"

Dondurulmuş sette sayfa tek adımı adlandırıyor: "SIRADAKİ / Matematik — Kesirlerde toplama… / 10 dakikayla başla / Başla". Bitmiş gruplar kapalı (İ7).

"Başla" ödev penceresini açıyor. Pencerenin kapatma kontrolünün erişilebilir adı **`Close`**. Aynı panelde kitap okuyucu ve takvim açılırı `Kapat` diyor (`BookReader.tsx`, `CalendarEvents.tsx`). `HomeworkTracker.tsx` içindeki `ModalHeader` `iconDescription` vermiyor; Carbon'un varsayılanı İngilizce "Close". İ9, §5.5. D3a bunu bilerek bıraktı (`dashboard/tests/e2e/alt-gezinme.spec.ts`, "the close button is the reliable way to shut it").

Telefon bölüm başlıkları kısa: "Tamamlandı" **339×26**, "Yapılmayan" **339×26**.

### Asistan — öneri çipleri 26 px, selamlama "size"

Öneri düğmeleri telefonda yaklaşık **26 px** yüksek ("Işık bugün neye öncelik vermeli?" 238×26). Karşılama: "size yardımcı olabilirim" — panelin geri kalanı sen diyor (§5.5, İ9).

Üst banttaki "Ödev fotoğrafı ekle" duruyor (48×48). Kaldırmak D2'nin işi; bu denetim ona dokunmadı.

### Dersler — içerik cümlesi iki kez

Dondurulmuş ve canlı sette ders içeriği aynı cümleyi başlık ve açık gövde olarak iki kez basıyor ("Kesirlerde toplama ve çıkarma işlendi…"). `CourseContent` akordeonu `open={!focusMode}` ve başlık metnin ilk 80 karakteri. İ6.

Haftalık program ızgarasının ders adları bu çekimde yok. Sebep fikstür: `WeeklySchedule` gün adlarını `rows[0]`'dan okur (`utils/schedule.ts`); FULL gün adlarını `schedule.headers`'a koyup satırlara yalnız saat ve ders yazar. Canlı kazıma satır 0'da gün adını taşır.

### Takvim — hafta okları 32×32, "Onceki"

Hafta okları **32×32**. Geri okun `iconDescription` değeri **`Onceki hafta`** — noktasız I (`CalendarEvents.tsx`). İleri ok "Sonraki hafta".

FULL etkinlikleri (`baslik` / `tarih`) ızgarada yok. Sayfa `ev.title` okuyor. Fikstür şekli; boş ızgara canlı takvimin hâli diye yazılmadı.

### Notlar — "Expand current row", 32×33

Not tablosunun satır genişletme düğmesinin adı **`Expand current row`**, kutu **32×33**. Başlık hücresinde görsel olarak gizlenmiş "Ayrıntı" var; satır düğmesi Carbon varsayılanında kalmış. İ9, §5.5. Telefonda 44 px'in altında.

Tablodaki tireler fikstür: FULL notları `{ ders, sinav, puan }` dizisi; tablo ders × sütun matrisi bekliyor.

## Kabuk

Telefon alt çubuğu Bugün, İşler, Asistan, Dersler, Daha fazla; sekme kutuları **78×48** (Bugün sekmesi metinle birlikte daha geniş). Yatay taşma yok. D3a kabuğu bu çekimde bozulmadı.

`RouteBoundary` çökünce şöyle diyor: "soldaki menüden başka bir sayfaya geçebilirsin." 390 px'te sol menü yok; çıkış alt çubuk. Cümle, sınır her çalıştığında yanlış. Bu çekimde `/sinavlar` sınıra düştü çünkü FULL'da `stats` yok ve `ExamTimeline` `data.stats.upcoming` okuyor. Çökme fikstür; cümle değil.

## Fikstür yüzünden ürün sayılmayanlar

- **Sınavlar** beyaz sayfa değil, sınır metni. Canlı uç `stats` döndürüyor.
- **Duyurular** satırı İngilizce `title`. Carbon `AccordionItem` varsayılanı `title = "title"`. FULL `baslik` taşır; sayfa `e-Posta Başlık` okur.
- **Bugün**, dondurulmuş sabah, ödev varken okumayı adlandırıyor. Bugün yalnız `Ödev Durumu === 'Değerlendirilmemiş'` olanı iş sayar; FULL boş dizgi gönderir. Canlı API boş durumu o sözcüğe çevirir (`dashboard_api.py`). İşler boş dizgiyi aktif saydığı için iki sayfa bu fikstürde ayrışıyor.
- **İlerleme** `0/0`. FULL ilerleme nesneleri boş.

## Sonraki sayfa işi için sıra

Yenileme spec'teki sırayı korur: Bugün (gün okları) → İşler (Close → `Kapat`, bölüm başlığı yüksekliği) → Asistan (çip yüksekliği, sen) → Dersler (çift cümle) → Takvim (`Önceki`, ok boyu) → Notlar (`Expand current row`). Her sayfanın görsel taban çizgisi, ancak o sayfanın farkı okunduktan sonra güncellenir. Bu denetim taban çizgisini değiştirmedi.
