# TEDY Yüzey Tasarımları

**Sürüm 1.0 · 2026-08-31 · `docs/frontend-design-principles.md`'nin uygulaması**

İlkeler dokümanı *neye göre karar verileceğini* yazar. Bu doküman o kararların
her yüzeyde ne olduğunu yazar. Çelişki hâlinde ilkeler dokümanı kazanır.

Atıflar: **D1–D4** değişmezler, **İ1–İ9** ilkeler.

---

## 0. Nasıl okunur

Her yüzey dört başlıkla anlatılır:

- **Ne için var** — bu sayfa hangi soruyu cevaplıyor. Cevaplamıyorsa sayfa
  gereksizdir.
- **Bugünkü kusur** — ölçülmüş. Ölçülmemişse "doğrulanacak" diye işaretli.
- **Tasarım** — ne yapılacak.
- **Kapılar** — bitmiş sayılması için geçmesi gereken kontroller.

**Ölçüm notu:** Bugün ve Ödevler ekran görüntüsünden okundu. Diğer yüzeylerin
kusurları kod okumasından çıkarıldı; görsel iddialar "doğrulanacak" taşır.

---

## 1. Bilgi mimarisi — karar

13 nav öğesi **5 birincil + 6 ikincil**e iner. Nav **etiketlenir**; ikon tek
başına taşıyıcı olamaz (çalışma belleği yükü).

| Birincil | Kapsadığı bugünkü sayfalar |
|---|---|
| **Bugün** | Bugün |
| **İşler** | Ödevler + Sınavlar |
| **Dersler** | Program + Ders İçerikleri |
| **Asistan** | Asistan |
| **Tedy Books** | Tedy Books |

**İkincil** (bir "Daha fazla" altında): Notlar, Takvim, Takımlar, İlerleme,
Duyurular, Profil.

Eski rotalar **kırılmaz**, yenilerine yönlendirilir. `readerAccess` mantığı
aynen korunur; okur yalnız Tedy Books görür.

**Neden birleştirme:** Ödev ile sınav Işık'ın kafasında iki ayrı şey değil —
ikisi de "borcum olan iş". Program ile ders içeriği de öyle: "ne çalışıyorum".
Ayrı sayfalar, ürünün iç kategorilerini kullanıcıya ödev olarak veriyor.

---

## 2. Ortak kalıplar

Bunlar bir kez burada tanımlanır, her yüzeyde tekrar edilmez. Yeni bir kalıp
icat etmeden önce buraya bakılır.

### 2.1 Zaman gösterimi

**Kural:** ekranda görünen her saat, süre ve sayaç **IBM Plex Mono**, tabular
rakamlarla. Dil Plex Sans'ta kalır.

*Neden:* çizelge bir alettir; iki süre okunmadan karşılaştırılabilmeli.

Üç biçim var, karıştırılmaz:

| Biçim | Ne zaman | Örnek |
|---|---|---|
| **Saat** | Bir ana bağlıysa | `15:45` |
| **Kalan** | Bir kaynak anlatıyorsa (İ2) | `3 saat 20 dakikan var` |
| **Kutu** | Bir başlama teklifiyse (İ3) | `10 dakikayla başla` |

**Yasak:** çıplak tarih tek başına ("20 Mart 23:59"). Tarih varsa yanında ne
zaman/ne kadar sorusunu cevaplayan bir gösterim olur. Ham ISO damgası hiçbir
yerde görünmez (D4).

### 2.2 İş satırı

Yapılacak/yapılmış bir işi gösteren tek satırın kanonik biçimi:

```
┌────────────────────────────────────────────────────────┐
│ Matematik                              yarın · 2 gün   │
│ Sayfa 165                                              │
│                                        [ Yaptım ]      │
└────────────────────────────────────────────────────────┘
```

- Ders adı **birincil**, iş adı ikincil.
- Zaman sağda, mono, kalan biçiminde.
- **Tek eylem.** Ödevde bu `Yaptım` (`/api/homework/mark-done` zaten var).
- Bitmiş satır aynı yapıyı kullanır ama **nötr** ve **eylemsiz** (İ7).

### 2.3 Boş durum

Boş durum bir davettir, bir özür değil (İ9). Üç bilgi taşır ve **fazlasını
taşımaz**:

1. Ne yok
2. **Neden yok** — biliniyorsa (D3)
3. Bunun yerine ne yapılabilir — varsa

**Yasak:** büyük dekoratif ikon. Bugün "ajanda boş" kartı bir güneş ikonuyla
~200px kaplıyor ve tek-iş kartıyla yarışıyor (İ6). Boş durum **tek satır
metindir**, kart değil.

```
Bugün teslim edilecek bir şey yok. Yeni ödevler portal açılınca görünecek.
```

### 2.4 Yükleniyor

Carbon `SkeletonText`/`SkeletonPlaceholder`, gerçek içeriğin **şekliyle**.
Dönen ikon yok (İ6: aynı anda tek hareket, ve o "şimdi" işaretçisi).
Yükleme 400 ms'den kısaysa hiçbir şey gösterilmez — titreşim gürültüdür.

### 2.5 Bölüm başlığı ve katlama

**Varsayılan katlama kuralı:** bugün eylem gerektiren bölüm **açık**, geçmiş
**kapalı** başlar (İ7). Bugün Ödevler'de `collapsed` boş başlıyor, yani
*hepsi* açık — bu tersine çevrilir.

Başlık şu biçimdedir: `BAŞLIK  (n)  ⌄` — sayı, katlanmış içeriğin büyüklüğünü
söyler; açıkken de kalır.

### 2.6 Eylem

- Ekranda **bir** birincil (Carbon `kind="primary"`) eylem (İ1).
- İkincil eylemler `kind="ghost"` veya `tertiary`.
- Eylem adı akış boyunca **değişmez**: `Yaptım` diyen düğme `Yapıldı` sonucu
  üretir (İ9).
- Yıkıcı eylem yok. `Yaptım` geri alınabilir olmalı (İ5).

### 2.7 Durum rozeti

Rozet **yalnız** bir durum ayrımı taşıyorsa konur (İ6). Şiddet ayrımı
`risk:` ↔ `warning:` mantığıyla aynıdır: kırmızı yalnız gerçek aciliyet.

| Durum | Görünüm |
|---|---|
| Gecikmiş | Kırmızı, metinle: `2 gün gecikti` |
| Yaklaşan | Nötr + mono kalan |
| Bitmiş | Rozet **yok** — satır zaten nötr |
| Bozuk (sistem) | Gri, nedenle (D3) |

**Yasak:** bitmiş işe "Süresi doldu" rozeti. Teknik olarak doğru, anlamca
yanlış, gereksiz alarm — bugün Ödevler'de 12 kez tekrarlanıyor.

---

## 3. Kabuk

### 3.1 Başlık

Bugünkü hâli çalışıyor. İki değişiklik:

- **Sağlık göstergesi** (`5 dk önce · 4 uyarı`) kalır. Popover içindeki bölüm
  listesi zaten `unavailable` nedenlerini taşıyor.
- **Odak anahtarı** kalır ve güçlenir (§5).

### 3.2 Gezinme

- 13 → 5 birincil (§1).
- **Etiketler görünür.** Dar ekranda ikon+etiket alt alta ya da Carbon
  `SideNav` genişletilmiş hâlde.
- Aktif sayfa Carbon'un kendi göstergesiyle; ek süsleme yok.

### 3.3 Portal durum bandı

Uygulandı (`PortalStatusBanner`). Kural: yalnız portalın **açıkça reddettiği**
bölümler için çıkar; boş tablo arıza değildir. Okur rolüne render edilmez.

### 3.4 Altbilgi

Bugün iki satır ("TED Rönesans Koleji" / "TEDY — Öğrenci Takip Paneli ©2026").
Hiçbir soruyu cevaplamıyor ve her sayfanın altında yer kaplıyor. **Tek satıra
iner**, ve son senkron zamanını taşır — o, bakılabilir bir bilgidir.

---

## 4. Yüzeyler

### 4.1 Bugün — *uygulandı, referans*

**Ne için var:** "Şimdi ne yapmalıyım?"

**Tasarım (yürürlükte):** Gün Şeridi + tek adlandırılmış adım + altında sessiz
"bugün ayrıca". Şerit yalnız kalanı çizer; odak penceresi sıcak alanla gösterilir
ve sınır `odak sonu 16:00` etiketini taşır; okul sürerken iş son zilden sonraki
dilime çapalanır.

**Tek şey günün saatine göre değişir** (2026-09-24):

| Ne zaman | Tek ana kart | Altında, sessiz |
|---|---|---|
| Son zilden önce | Şu anki ya da sıradaki ders (`.today-now`): öğretmen, "Sonra: …", "N ders kaldı" | Ödev tek satır önizleme (`next-thing--quiet`): ad + teslim günü, düğmesiz |
| Son zilden sonra | Ödev (`NextThing`), "Teslim yarın 12:00" ile | "Ayrıca": kalan işler ad + gün olarak, en çok iki satır |

- **"Başla" başlatır.** Kartta 10 dakikalık bir kutu açar: "BAŞLADIN · N dk kaldı",
  öğretmenin talimatı ve ekler kartın içinde. Kutu `localStorage`'da işin
  kimliğiyle tutulur; yenilemede ya da dönüşte kaybolmaz (İ5). Süre dolunca
  "10 dakika daha" önerir, yapılanla ilgili hüküm vermez.
- **Biten öğeler katlanır** (İ7): bugünün geçmişi tek satır, "7 ders, 1 etkinlik
  bitti · Göster". Başka bir gün bilerek açıldığı için bütün görünür.
- **Kaldırılanlar ve nedenleri:** degrade "ŞU AN" kartı (nabız animasyonu +
  kendi ilerleme çubuğu), ikinci gün çubuğu, ham `3/7` sayacı, yeşil "program
  bitti" kartı, üç renkli geri sayım etiketli ödev kutusu. Ölçüm 2026-09-24:
  aynı ekranda üç zaman çubuğu vardı, sıradaki ödev iki kez yazılıyordu ve
  10:15'te telefonda o anki ders ilk ekranın dışındaydı.
- **"Yaptım" Bugün'de de var** (kutu açıkken ve süre dolduğunda). İşler ile
  aynı kaydı gönderir (`utils/odevYaptim.ts`). Başarılı olursa kart sıradaki işe
  geçer ve altında sessiz bir "Yaptın: …" satırı çıkar. Başarısız olursa kart
  "Kaydedilemedi" der ve kutu açık kalır (D3).
- **Öğrencinin "Yaptım"ı işi aktif listeden çıkarır**; İşler'de de böyle.
  Ölçüm 2026-09-22 17:26: Işık haftanın Matematik ödevini işaretledi, ama Bugün
  yalnız öğretmen durumuna baktığı için iki gün boyunca aynı işe "Başla" dedi.
- **Yarın** (son zilden sonra; okul olmayan günde 15:45'ten sonra): sıradaki
  okul günü, yani ilk ders, o günün dersleri ve etkinlikler. Çanta akşamdan
  hazırlansın diye. Cuma akşamı "PAZARTESİ" der. Teslimleri tekrar etmez; onlar
  kartta ve "Ayrıca"da gün adıyla zaten yazıyor.
- **Sınavlar** "Ayrıca"nın sessiz satırlarıyla gösterilir: ad ve gün. Renkli
  geri sayım etiketi ve ders rengi yok (İ6, İ8). Blok "Ayrıca"nın altında durur,
  çünkü haftalar sonraki bir sınav dört gün sonraki ödevin üstünde durmamalı.
  Ertesi okul günündeki sınav akşam **Yarın'ın ilk satırı** olur ("SINAV · 09:00
  · …") ve listeden çıkar. Ana karta **çıkmaz**: İ4'ün kendi testi, 20:00'de
  "sınav hazırlığına başla" demeyi ihlal sayar. Bu blok 2026-09-24'e kadar
  hiç görünmemişti; API takvimdeki her sınavı "geçmiş" sayıyordu.
- **Önerilmeyen ve nedeni:** "teslim yarından sonraysa işi yarının penceresine
  ertele" kuralı. §2'ye göre ev ödevi zaten büyük ölçüde pencere dışında
  yapılıyor. Her işi 15:45–16:00 arasındaki 15 dakikalık dilime itmek dürüst olmaz.
  Pencere dışında kart yalnız kısa ve tek adımlı kalır ("10 dakikayla").

---

### 4.2 İşler *(Ödevler + Sınavlar)*

**Ne için var:** "Neyi, ne zamana kadar borçluyum?"

**Bugünkü kusur** (ölçüldü):
1. Altı sıfırlık özet satırı — hiçbir şey söylemeyen en yoğun biçim.
2. Sayfa Mart'tan kalma **12 bitmiş ödevle** açılıyor; bütün bölümler
   varsayılan açık (`collapsed` boş başlıyor).
3. `İlk görülme: 2026-03-11T23:29:16.752613` — ham ISO damgası (**D4 ihlali**).
4. Bitmiş ve bekleyen aynı görsel ağırlıkta.
5. Bitmiş işte "Süresi doldu" rozeti.

**Tasarım:**

```
İşler

┌──────────────────────────────────────────────┐
│ ŞİMDİ · Matematik — Sayfa 165                │
│ 10 dakikayla başla            [ Başla ]      │   ← tek adım (İ1)
└──────────────────────────────────────────────┘

BEKLEYEN (3)                                  ⌄   ← açık
  Matematik · Sayfa 165          yarın · 2 gün  [Yaptım]
  Fen · 3 soru                   perşembe       [Yaptım]
  Türkçe · okuma                 gelecek hafta  [Yaptım]

SINAVLAR (2)                                  ⌄   ← açık
  Matematik yazılı               12 gün sonra
  Fen yazılı                     19 gün sonra

GEÇMİŞ (14)                                   ›   ← kapalı
```

- Özet satırı **silinir**. Sayı bölüm başlığındaki `(n)`'dedir.
- Sınavlar ayrı sayfa olmaktan çıkıp burada bir bölüm olur.
- Geçmiş kapalı başlar; açıldığında nötr, eylemsiz.
- `Yaptım` geri alınabilir: işaretlemeden sonra 10 saniye `Geri al` (İ5).
- Ham damga kaldırılır; gerekiyorsa "11 Mart'ta görüldü".

**Kapılar:** ilk ekran testi · gri tonlama · sızıntı taraması · 2 saniye testi.

---

### 4.3 Dersler *(Program + Ders İçerikleri)*

**Ne için var:** "Bugün/bu hafta hangi dersler var, ve o derste ne var?"

**Bugünkü kusur:** Program ayrı sayfa, içerik ayrı sayfa; ders adına iki kez
gidiliyor. *(Görsel kusurlar doğrulanacak.)*

**Tasarım:** haftalık ızgara üstte, seçilen günün dersleri altta; bir derse
tıklanınca o dersin içeriği **aynı sayfada** açılır.

- Izgara Carbon `DataTable` ile; bugünün sütunu vurgulu, **geçmiş günler
  soluk** (İ7).
- Şu anki ders işaretli — Gün Şeridi'ndeki "şimdi" ile aynı dil.
- Ders satırı: saat (mono) · ders adı · varsa o derse ait bekleyen iş sayısı.

**Portal kapalıyken:** §3.3 bandı zaten nedeni söylüyor; sayfa §2.3 boş durumu
gösterir, kart değil.

---

### 4.4 Notlar

**Ne için var:** "Nerede iyiyim, nerede değilim?"

**İncelendi (2026-08-31) — kusur bulunamadı.** `GradeTable` zaten Carbon
`DataTable` + genişletilebilir satır kullanıyor: detay istendiğinde açılıyor,
ok yok, renk kodlaması yok, kutlama yok, sıralama yok. Yani aşağıdaki tasarım
bir **düzeltme değil, iyileştirme** — ve eğilim hesaplamak için gereken not
verisi henüz yok. Çalışan bir tabloyu doküman öyle diyor diye değiştirmiyoruz;
not verisi geldiğinde yeniden değerlendirilir.

**Önerilen (ertelendi):** ders bazlı tablo değil, **ders bazlı özet +
istendiğinde detay**.

- Her ders bir satır: ders adı · dönem ortalaması (mono) · eğilim.
- Eğilim **ok değil, kelime**: `yükseliyor` / `sabit` / `düşüyor`. Ok, renkle
  birlikte iki kanaldan aynı şeyi söyler ve bütçe harcar (İ6).
- Detay istendiğinde açılır (Carbon `Accordion`), varsayılan kapalı.
- **Yasak:** başarı kutlaması, hedef çubuğu, sıralama. Not bir bilgidir, bir
  yargı değil (İ9).

---

### 4.5 Takvim

**Ne için var:** "Bu ay ne var?"

**Düzeltme (2026-08-31):** bu bölüm ay ızgarası varsayılarak yazılmıştı.
Takvim aslında **hafta görünümü** (saat × gün). Ölçmeden yazmanın sonucu;
aşağısı gerçek yapıya göre düzeltildi.

**Uygulandı:** **geçmiş saatler geriye çekilir** (İ7) — bu haftanın geçmiş
günleri ve bugünün geçmiş saatleri soluklaşır, etkinlikleri doygunluğunu
yitirir. Bugün zaten vurguluydu; eksik olan, harcanmış olanın ayırt
edilmesiydi.

**Değerlendirildi, uygulanmadı:** popover'ı satır içi panele çevirmek. Gerekçe
"kaybolan yüzey"di (İ5), ama popover yalnız dışarı tıklandığında kapanıyor —
standart davranış, ve okurun yeniden bulmak zorunda kalacağı bir durum
üretmiyor. Gerçek bir zarar ölçülmeden değiştirilmeyecek.

---

### 4.6 Takımlar

**Ne için var:** "Hangi kulüp/takım etkinliğim var?"

**Tasarım:** §2.2 iş satırı biçiminde liste. Tablo başlıkları
(`Etkinlik / Tarih / Durum`) tek satırlık öğelere iner — üç sütunluk bir tablo,
üç alanlı bir satırdan daha pahalıdır.

---

### 4.7 İlerleme

**Ne için var:** "Dış platformlarda (EnglishCentral, Achieve3000, SEBİT)
neredeyim?"

**Bugünkü kusur:** üç ayrı akordeon, her biri kendi yükleme metniyle
("Video listesi yükleniyor…", "Ders listesi yükleniyor…", "Ödev listesi
yükleniyor…") — üç eşzamanlı yükleme göstergesi (İ6 ihlali).

**Ölçüldü (2026-08-31):** bu üç metin `dashboard-empty-text` sınıfıyla, yani
**boş durum kılığında** basılıyor. Yükleniyor olmakla boş olmak iki ayrı şey;
aynı görünümü paylaşmaları, veri gelmediğinde okurun hangisiyle karşı karşıya
olduğunu ayırt edememesi demek. §2.4'e göre iskelete geçerler ve boş-durum
sınıfını bırakırlar. (Bu yüzden §2.3 çıkarımında dokunulmadılar — `EmptyLine`'a
çevirmek karışıklığı kalıcılaştırırdı.)

**Tasarım:**

- Üç platform **tek listede**, her biri bir satır: platform · ilerleme ·
  son etkinlik.
- Detay tek akordeon altında, varsayılan kapalı.
- Yükleme: tek iskelet, üç ayrı metin değil (§2.4).
- **Yasak:** yüzde halkası, rozet, seri sayacı.

---

### 4.8 Duyurular

**Ne için var:** "Okuldan ne haber var?"

**Tasarım:** ters kronolojik liste; **okunmamış** olan öne çıkar, okunmuş nötr.

- Uzun duyuru katlanır, ilk iki satır görünür.
- Boş durum §2.3 — bugün portal boş döndüğü için bu sık görülecek.

---

### 4.9 Profil

**Ne için var:** "Benim bilgilerim doğru mu?" (Işık) / "Kayıt doğru mu?" (veli)

**Bugünkü kusur:** portal profil sayfası taşındığı için alanlar boştu;
düzeltildi (`p_temel_bilgiler`). Sınıf ve şube **bu sayfada yok**, boş kalır —
uydurulmaz.

**Tasarım:** ad + foto üstte; alanlar §2.2 ritminde; özel dersler ayrı bölüm.
Boş alan gizlenmez, **boş olduğu söylenir** (D3).

---

### 4.10 Asistan

**Ne için var:** "Bunu bana anlatır mısın?"

**Bugünkü durum:** yeni tamamlandı — atıf çipleri, kaynak paneli, degradasyon
rozeti, SSE akışı. İlkelerle **zaten büyük ölçüde uyumlu**.

**Kalan uyum işi:**
- Güvenlik bayrağı şiddet ayrımı uygulandı; `warning:` gri, `risk:` kırmızı.
- Sınıflandırılmamış kaynak grubu bilinen gruplarla aynı görsel stille
  basılıyor — başlık dürüst ama görsel ayrım zayıf (ertelenmiş minor).
- `CitationChip`'e `aria-describedby` eklenmemiş (ertelenmiş minor, D2).

**Cevap yazılırken görünür (2026-09-24).** Normal bir soru orta eforda ~17 sn
sürüyor; bu okur için boş bir bekleme dikkatin gittiği yerdir. Akışın
`answer_delta` olayları düşünme göstergesinin yerine `.ac-msg--writing`
taslağını koyar (`aria-busy`); son `answer` gelince taslak onun yerini bırakır.
Taslakta `[S1]` görünmez: kaynağı henüz gelmemiş bir işaret iç temsildir (D4),
çip bir an sonra gelir. Araç çağrısından önce yazılan metin cevap değildir;
`answer_reset` onu siler. Taslak uzarken sayfa onu izleyip kaymaz, yalnız
yazım başlarken bir kez kayar (İ6).

**Ödev soruları Bugün'ün listesinden (2026-09-24).** Asistan ödevi `odev_listesi`
aracıyla okur: Bugün'ün gösterdiği satırlar, Işık'ın "Yaptım" işaretleriyle. Metin
dizininden okurken "Yaptım" dediği işi yapılacak diye saymıştı; iki yüzey aynı
şeyi farklı söyleyemez (İ9).

---

### 4.11 Tedy Books — *ayrı dünya*

**Ne için var:** okumak.

Bu yüzey **bilinçli olarak farklı bir sesle** konuşur: Cormorant Garamond +
Literata, kitap tipografisi, tam ekran okuyucu. Bu ayrım korunur — yapma
yüzeyine kitap sesi, okuma yüzeyine arayüz sesi sızmaz (§5.2, ilkeler).

**Değişen tek şey:** kitap, pano üzerinde artık bağıran bir bant değil.
Borç yokken tek-iş yuvasına girer (uygulandı).

---

## 5. Odak kipi

Bugün `FocusModeContext` var ve bir localStorage anahtarı tutuyor. İlkelere
göre güçlendirilir:

Odak açıkken:
- İkincil nav gizlenir, birincil kalır.
- Sayfa **yalnız** tek-iş kartını ve o işe ait olanı gösterir.
- Bildirim/rozet/sayaç susar.
- Gün Şeridi kalır — zaman görünürlüğü odak kipinde daha da gereklidir.

Odak, gürültüyü azaltan bir tercih değil, **bir çalışma kipidir**.

---

## 6. Uygulama sırası

Sıra, en çok kazandırandan başlar ve her adım tek başına sevk edilebilir:

| # | İş | Durum |
|---|---|---|
| 1 | Bugün'ün boş durum kartı → §2.3 | ✅ |
| 2 | **İşler** birleştirme + ham damga temizliği | ✅ |
| 3 | Ortak kalıplar (§2) bileşen olarak | ✅ zaman + boş durum; bölüm başlığı ikinci tüketici çıkınca |
| 4 | Dersler birleştirme | ✅ |
| 5 | Nav 13 → 5 + görünür etiketler | ✅ |
| 6 | Notlar · Takvim · Takımlar · İlerleme · Duyurular | ✅ |
| 7 | Odak kipi | ✅ |
| 8 | Profil | ✅ |

**Sıra değişikliği:** 4 ve 5 yer değiştirdi. Nav indirgemesi Dersler
birleştirmesinden önce yapılırsa Program evsiz kalıyor; birleştirme önce gelmeli.

**Uygulama sırasında ölçülen, dokümanda olmayan kusurlar** — hepsi düzeltildi:

| Bulgu | Yüzey |
|---|---|
| Dört yüzey boşken `null` döndürüyor, sayfa bomboş açılıyor (D3) | Takımlar · Duyurular · Dersler×2 |
| "…yükleniyor" metni **boş dalı** — kalıcı boş liste sonsuza dek "bekle" diyor | İlerleme |
| Odak kipi ödev adını ve teslimini gizliyor — "Türkçe [Yaptım]" | İşler |
| `formatTurkishDate` tanımadığı girdiyi **olduğu gibi döndürüyor** | tüm tarihler |
| Sonraki adım listenin başını alıyor, liste ise en uzak-önce sıralı | İşler |
| Liste **tamamen** en uzak-önce sıralı — en acil iş en altta | İşler |
| Profil alanları 12'de sessizce kırpılıyor | Profil |
| Ray kalkınca kapalı nav'ın kenarlığı 1px ekranda kalıyor | kabuk |

**Sıralama kararı (2026-08-31).** İlk düzeltme yalnız *kartı* en yakın teslime
bağlamıştı; liste hâlâ en uzak-önce sıralıydı, çünkü bu CLAUDE.md'de belgelenmiş
bir ürün tercihiydi. Tek taraflı çevirmedim, kullanıcıya sordum — ve onay
geldi. Şimdi sıralama **grup başına**:

| Grup | Sıra | Gerekçe |
|---|---|---|
| `aktif` | en yakın teslim önce | Yarın teslim edilecek iş, gelecek ay teslim edilecek dördünü kaydırmadan görünmeli (İ2, İ3) |
| `yapilan` · `tamamlanan` · `yapilmayan` | en yeni önce | Bunlar geçmiştir; geçmiş en yeniden okunur |

Okunamayan teslim tarihi taşıyan satır iki sırada da **dibe iner** — 1970 (en
yakın) ya da uzak gelecek (en az acil) gibi sıralanmaz. `nextHw` artık
`aktif[0]`; en küçüğü arayan tarama gerekmiyor. Yan etki: sıralama memo'nun
içine girdi — dışarıdayken her render'da yeni dizi ürettiği için `useMemo`
hiçbir zaman bellemiyordu.

**Playwright denetimi (2026-08-31).** Yayınlanan paket 11 yüzey × 2 görüntü
alanı × 2 veri durumu (dolu / bugün gerçekten sunulan boş) olarak yakalandı ve
kontrast, odak halkası, dokunma hedefi, başlık sırası ve yatay taşma ölçüldü.
Sekiz bulgu; hepsi `tests/e2e/audit.spec.ts` ile çivilendi.

| Bulgu | Kök neden | Etki |
|---|---|---|
| Bozuk tek bir API yanıtı **tüm panoyu** beyaz ekrana düşürüyordu | `ErrorBoundary` yok | her yüzey |
| "Odak" etiketi koyu mavi başlıkta **1,6:1** | kural `.cds--toggle__label-text`'i hedefliyordu; Carbon v11 `.cds--toggle__text` üretiyor | her sayfa |
| Hiçbir sayfada `h1` yok | kabuk sayfayı adlandırmıyordu | her sayfa |
| Başlık listesi **kapalı bir kipin** iki başlığıyla açılıyordu | kapalı `ComposedModal` `ModalHeader`'ını DOM'da tutuyor | her sayfa |
| h2 → h4 atlaması | kart başlıkları h4 | 8 yüzey |
| Profil ızgarası telefonda ikinci sütunu ekran dışına taşıyordu | sabit `1fr 1fr` | Profil |
| Sağlık düğmesi 82×20 | WCAG 2.2 asgari 24×24 | başlık |
| Altbilgi sayfa ortasında, altında 212px ölü boşluk | kabuk görüntü alanını doldurmuyordu | boş günler |

`.cds--toggle__label-text` ile daha önce silinen `.cds--skeleton` **aynı
ailedir**: Carbon'un ürettiği sınıf adı varsayıldı, ölçülmedi. Carbon
seçicisi yazarken DOM'a bakılır.

**Estetik turu (2026-08-31).** Aynı yakalama düzeni, bu kez **gerçek API
verisiyle** koşuldu (yalnız ödev/sınav mocklandı) — mock şekli tutmayınca sayfa
yanlış render oluyor ve yanlış render edilmiş bir sayfanın estetiğini incelemek
boşa emek. Yedi düzeltme:

| Bulgu | Karar |
|---|---|
| "Haftalik Takvim", "Bugun", "goster" | Türkçe harfleri düşmüş dizgeler — hepsi `CalendarEvents.tsx` içinde |
| Asistan yanıtlarında madde işareti yok | Carbon reset'i `list-style: none` koyuyor; `.bookmd__list` kendi işaretini geri alır |
| Dersler'de **iki adsız cümle** yan yana | `EmptyLine` sessiz bir `label` aldı — panel değil, etiket (§2.3 korundu) |
| Boş not tablosu yalnız **başlık satırı** gösteriyordu | satırsız başlık, yüklenememiş veri gibi okunuyor → boş satır |
| `Notlar —` boşlukta biten ayraç | ikinci işlenen yoksa ayraç da yok |
| Portal banner'ı **Kitaplık ve Asistan**'ın üstünde | portal bölümü göstermeyen yüzeyde bilgi değil gürültü (İ6) → `offPortal` |
| Takvim göstergesi haftada olmayan türleri de listeliyordu | yalnız o haftadakiler + kullanıcının gizledikleri |

**İki kez ölçüm beni yanlış "düzeltmeden" kurtardı.** Asistan'ın `fullPage`
görüntüsünde içerik sabit başlığın altında kalmış görünüyordu — görüntü alanı
çekiminde sorun yoktu, dikiş artefaktıymış. Odak kipinde başlık ile düğme
bitişik görünüyordu — ölçülen boşluk 16px (`$spacing-05`), kırpma yok.

**Asistan — Carbon for AI turu (2026-08-31).** Yüzey Carbon'un AI token'larını
zaten kullanıyordu (`ai-gradient`, `ai-aura-*`, `ai-border-*`, `AILabel`).
Eksik olan token değil, **anlamdı**.

*Kural: AI aurası bir köken işaretidir, süs değil.* Modelin yazdığına konur;
müfredatın söylediğine konmaz. Bu ürün için sıradan bir tercih değil — asistanın
tüm değeri "bunun nereden geldiğini kontrol edebilirsin" olduğuna göre, "asistan
dedi" ile "kitap dedi" ayrımı tasarımın kendisidir (D4, İ9).

| Bulgu | Karar |
|---|---|
| `<AILabel/>` hiçbir şey açıklamıyordu | `AILabelContent`: ne olduğu, kaynakların denetlenebilirliği, yanılabilirliği |
| `meta.model` her yanıtta geliyor, kimseye gösterilmiyordu | AILabel açıklamasında; ekranda sürekli değil (İ6) |
| Işık'ın **kendi mesajı** `ai-aura-hover-background` ile boyalıydı | nötr `$layer-02` — çocuğun sözleri makine çıktısı gibi işaretlenemez |
| Aktif kaynak satırı AI aurasıyla vurgulanıyordu | nötr `$layer-selected` — alıntı, modelin yazdığı şey değil |
| İki değişmez renk (`#fff`, `#001d6c`) | token; `--ted-color-brand-primary-hover` eklendi |

Kullanıcı balonundaki auranın gerekçesi kayıtlıydı: "değer-değer token takası,
yeniden tasarım değil". Doğruydu — hex korunmuş, **anlam kaybolmuştu**. Token
uyumu için seçilen bir renk, o token'ın taşıdığı iddiayı da beraberinde getirir.

**Ölçüm iddiamı bir kez çürüttü:** alıntı popover'ının metnin üstüne gölgesiz
bindiğini yazmıştım; ölçülen gölge var (mavi tonlu, z-index 6000). Ayrım zayıf
ama yok değil — iddiayı kurtarmak için değişiklik yapmadım, testi sildim.

**Ölçüm notu:** `page.evaluate()`'e dize olarak verilen `() => {...}` *ifade*
olarak değerlendirilir ve fonksiyonun kendisi döner — `{}` olarak serileşir ve
denetim sessizce boş geçer. IIFE olmalı. Ayrıca arka planı ararken yalnız
`background-color`'a bakan bir sonda gradient'li başlığı kaçırır ve beyaz
metni "görünmez" diye raporlar (ölçülen yanlış pozitif).

**Doğrulama notu:** tam süit çıktısı `tail -1` ile okunmamalı — Playwright
başarısızlığı geçenlerin **üstüne** yazar. Çıkış koduna bakılır.

**Bekleme kuralı (2026-09-13).** Süitte sabit süreli bekleme yok:
`suite-hygiene.spec.ts` yorum dışındaki her `waitForTimeout`'u reddeder. 21
bekleme koşula çevrildi; `homework.spec.ts` paralel yük altında iki kez tam da
böyle oynamıştı. İki kural:

- Sonraki satır **yeniden denemeyen** bir okumaysa (`count`, `innerText`,
  `evaluate`, `allInnerTexts`), okunacak duruma göre beklenir. Sonraki satır
  yeniden deneyen bir `expect(locator)` ise bekleme zaten gereksizdir.
- Bir **yokluk** iddiasından önce — banner yok, taşma yok, başlık atlaması yok,
  "en fazla N çip" — o şeyin içinde yok olduğu yüzeyin render olduğu kanıtlanır.
  Her yokluk boş bir sayfada da doğrudur.

Çeviri iki sahte geçmeyi ortaya çıkardı. `empty-surfaces` testi, kabuğa eklenen
gizli `h1` yüzünden **tamamen boşaltılmış** bir yüzeyde de geçiyordu — ölçüldü:
bölgenin metni "Takımlar" kalıyor. Takvim gösterge testinin fixture'ı yanlış
alan adlarıyla (`baslik/tarih/tur`) ızgaraya hiç olay koymuyordu; test sıfır
çipi sayarak geçiyor, hata mesajı da bileşende hiç olmamış
`.calendar-grid__event` sınıfını sayıyordu.

**Her adımın sonunda** ilkeler dokümanının §10 kapıları koşulur ve ekran
görüntüsüyle doğrulanır.

---

## Değişiklik kaydı

| Sürüm | Tarih | Not |
|---|---|---|
| 1.0 | 2026-08-31 | İlk sürüm. Bugün uygulandı; diğer yüzeyler tasarlandı. |
| 1.1 | 2026-09-24 | Bugün: saate göre tek ana kart, yerinde zaman kutusu, katlanan geçmiş; ham HTML ve `3/7` kaldırıldı. |
| 1.2 | 2026-09-24 | Bugün: akşam için "Yarın", kutu içinde "Yaptım"; öğrencinin işaretlediği iş artık sıradaki iş olmaz. |
| 1.3 | 2026-09-24 | Sınavlar sessiz liste; yarınki sınav Yarın'ın başında. İşler: "Yaptım" hatası görünür, ders adı tek. Portal saatleri yerel okunur. |
| 1.4 | 2026-09-24 | Asistan: cevap yazılırken görünür, taslakta çıplak atıf yok; ödev soruları Bugün'ün listesinden, "Yaptım" işaretleriyle. |
| 1.5 | 2026-09-24 | Asistan tek sesle konuşur: Işık'a "sen", aileye "siz" (sayfa metinleri de); kaynak numaraları okuma sırasıyla. |
