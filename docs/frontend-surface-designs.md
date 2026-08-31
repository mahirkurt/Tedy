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

**Kalan iş:** alttaki "ajanda boş" kartı §2.3'e indirilecek.

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

**Tasarım:** ders bazlı tablo değil, **ders bazlı özet + istendiğinde detay**.

- Her ders bir satır: ders adı · dönem ortalaması (mono) · eğilim.
- Eğilim **ok değil, kelime**: `yükseliyor` / `sabit` / `düşüyor`. Ok, renkle
  birlikte iki kanaldan aynı şeyi söyler ve bütçe harcar (İ6).
- Detay istendiğinde açılır (Carbon `Accordion`), varsayılan kapalı.
- **Yasak:** başarı kutlaması, hedef çubuğu, sıralama. Not bir bilgidir, bir
  yargı değil (İ9).

---

### 4.5 Takvim

**Ne için var:** "Bu ay ne var?"

**Tasarım:** ay ızgarası kalır. Değişenler:

- **Geçmiş günler soluk** (İ7).
- Bir güne birden çok etkinlik düşerse nokta yığını değil, **sayı**: `3`.
- Popover yerine seçilen gün ızgaranın **altında** açılır — popover, kaybolan
  ve yeniden bulunması gereken bir yüzeydir (İ5).
- Renk türü değil **durumu** kodlar (İ8): geçmiş nötr, bugün vurgulu, sınav
  günü işaretli.

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

| # | İş | Neden önce |
|---|---|---|
| 1 | Bugün'ün boş durum kartı → §2.3 | Uygulanan ekranı bitirir |
| 2 | **İşler** birleştirme + ham damga temizliği | En çok ölçülmüş kusur burada, D4 ihlali dahil |
| 3 | Ortak kalıplar (§2) bileşen olarak | Sonraki her yüzeyi ucuzlatır |
| 4 | Nav 13 → 5 + etiketler | Her sayfaya dokunur, kalıplar oturduktan sonra |
| 5 | Dersler birleştirme | İkinci büyük birleştirme |
| 6 | Notlar · Takvim · Takımlar · İlerleme · Duyurular | Kalıplar hazırken hızlı |
| 7 | Odak kipi | Diğerleri oturmadan anlamsız |
| 8 | Profil | En az kusurlu |

**Her adımın sonunda** ilkeler dokümanının §10 kapıları koşulur ve ekran
görüntüsüyle doğrulanır.

---

## Değişiklik kaydı

| Sürüm | Tarih | Not |
|---|---|---|
| 1.0 | 2026-08-31 | İlk sürüm. Bugün uygulandı; diğer yüzeyler tasarlandı. |
