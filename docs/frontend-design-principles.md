# TEDY Arayüz Tasarım İlkeleri

**Sürüm 1.0 · 2026-08-31 · Kapsam: `dashboard/` (React 19 + Carbon v11)**

Bu doküman TEDY panosunun neye benzeyeceğini değil, **neye göre karar verileceğini**
yazar. Bir ekran tasarlarken "bu doğru mu?" sorusunun cevabı buradan çıkmalı.

---

## 0. Bu doküman nasıl kullanılır

İki tür madde var ve karıştırılmamalı:

- **Değişmez** — tartışmaya kapalı. İhlal ediliyorsa yapılan iş yanlıştır.
- **İlke** — bağlayıcı, ama gerekçesiyle birlikte. Gerekçe bir vakada geçerli
  değilse ilke o vakada esneyebilir; esnetme *yazılır*, sessizce yapılmaz.

**Her ilkenin bir testi var.** Test yoksa ilke değil, temennidir. Bir ekrana
bakıp "bu ilkeye uyuyor mu?" sorusunu evet/hayır cevaplayamıyorsan, ilke kötü
yazılmıştır — düzelt.

---

## 1. Kim için tasarlıyoruz

### 1.1 Işık — birincil kullanıcı

12 yaşında, ortaokul öğrencisi. **Dikkat eksikliği ağırlıklı** profil. Tasarımı
belirleyen üç özellik:

| Gözlem | Tasarıma çevirisi |
|---|---|
| Dikkat dağılır, iş yarıda kalır | Arayüz **savrulmayı arıza saymaz**; dönüşü ucuzlatır |
| **Süreyi fazla tahmin eder** — iş gözünde büyür, başlayamaz | Arayüz **girişi küçültür**, toplamı öne çıkarmaz |
| **Net yönlendirme ister** — seçenek yığını felç eder | Arayüz **tek ve adlandırılmış** bir sonraki adım verir |

Bu üçü çelişmiyor, aynı yöne bakıyor: **aynı anda tek şey, küçültülmüş, adı konmuş.**
Bu cümle dokümanın geri kalanının özetidir.

### 1.2 Veliler — ikincil

Özlem ve Huriye. İhtiyaçları farklı: **durum görünürlüğü** (ne oldu, ne bekliyor)
ve **müdahale noktası** (neye bakmalıyım). Işık'ın yüzeyini onların ihtiyacıyla
kalabalıklaştırmayız; veli bilgisi ya kendi görünümünde durur ya da Işık'ın
akışında ikincil ağırlıkta kalır.

### 1.3 Okur — üçüncül

`reader` rolü (Tedy Books). Ayrı bir dünya, ayrı bir sesle — bkz. §5.2.

---

## 2. Merkezî gerçek: odak penceresi okul çıkışında kapanıyor

Işık'ın sürdürülebilir dikkat penceresi kabaca **08:00–16:00**. Okul bu pencerenin
neredeyse tamamını tüketiyor. **Ev ödevi büyük ölçüde pencerenin dışında yapılıyor.**

Bunun tasarım sonucu, günün en değerli diliminin nerede olduğunu değiştirir:

```
07  08    10    12    14    16    18    20    22
 │  ├─────────── odak penceresi ──────────┤
 │  ├──────── okul ────────┤ ▓▓▓▓ │  ödev saatleri (pencere dışı)
                            ↑
                   günün en pahalı 60 dakikası
```

**Kural:** okul çıkışı ile pencerenin kapanışı arasındaki dilim, günün en yüksek
değerli kaynağıdır ve arayüz onu **tek bir zor işe** harcar. Pencere kapandıktan
sonra arayüz derin iş önermeyi bırakır; kısa, düşük sürtünmeli, tek adımlı işlere
geçer.

**Pencere bir parametredir**, sabit değil. `output/` içinde yapılandırılabilir
tutulur; değişirse tasarım değil veri değişir.

---

## 3. Değişmezler

**D1 — Carbon token'ları zorunludur.** Renk, tipografi, aralık, yükseklik ve
hareket süreleri Carbon token'larından (`--cds-*`) veya onlardan türetilmiş
`--ted-*` token'larından gelir. Elle yazılmış hex, px veya ms yoktur. Carbon'da
karşılığı olmayan bir kalıp için **özel bileşen yazılabilir**, ama o bileşen de
token'larla boyanır.

**D2 — Erişilebilirlik tabanı.** WCAG 2.1 AA kontrast; klavyeyle ulaşılabilir ve
**görünür** odak; `prefers-reduced-motion` gerçekten uygulanır; her etkileşimli
öğe bir isme sahiptir. Ekran okuyucuya giden metin ham token olamaz.

**D3 — Sessiz arıza yok.** Bir bölüm boşsa arayüz **nedenini söyler**. "Veri yok"
ile "sistem bozuk" okurun ayırt edebileceği iki ayrı şeydir. Bilinmeyen bir durum
sessizce yutulmaz; ham hâliyle bile olsa görünür kalır.

**D4 — İç temsil okura sızmaz.** `warning:limited_confidence`, `(yetkisiz_giris)`,
`2026-03-11T23:29:16.752613` — bunların hiçbiri kullanıcı arayüzünde görünmez.
Makine tarafı `reason`/`kind` alanlarında yaşar; ekranda insan cümlesi durur.

---

## 4. İlkeler

### İ1 — Tek şey, adı konmuş

Her ekranda **tam olarak bir** sonraki eylem adlandırılır. Diğer her şey
ulaşılabilir ama ikincil ağırlıktadır. "Şunlardan birini seç" değil, "şimdi şunu
yap" + "başka bir şey istersen buradan".

*Neden:* net yönlendirme isteyen ve seçenek karşısında donan bir kullanıcıda,
eşit ağırlıkta üç kart üç karar demektir; üç karar sıfır eylem demektir.

*Test:* Ekranın görüntüsünü 2 saniye göster, kapat. "Şimdi ne yapman gerekiyor?"
sorusuna tek ve doğru cevap verilebiliyor mu?

---

### İ2 — Zaman bir yerdir, bir sayı değil

Son tarihler **görünür bir zaman üzerinde konum** olarak gösterilir; yalnız tarih
olarak asla. "20 Mart 23:59" bir zaman duygusu üretmez. "Yarın akşam — bu akşam
40 dakikan var" üretir.

*Neden:* zaman körlüğü, DEHB'de tarihin soyut kalması demektir. Somutlaştırma
tedavi edici değil ama telafi edicidir.

*Test:* Ekranda bir teslim tarihi varsa, yanında **"ne zaman ve ne kadar vaktim
var"** sorusunu cevaplayan bir gösterim var mı?

---

### İ3 — Girişi küçült, toplamı gizle

Bir işin **tamamının büyüklüğü** asla ilk gösterilen şey değildir. İlk gösterilen,
o işin **dürüst en küçük ilk adımıdır**. Toplam yalnız istendiğinde açılır.

*Neden:* süreyi fazla tahmin eden bir kullanıcıda toplam, başlamayı engelleyen
şeyin ta kendisidir. "3 ödev, 2 saat" bir duvardır; "şimdi 10 dakika, matematik
165. sayfa" bir kapıdır.

*Test:* Ekranın en belirgin sayısı bir **toplam** mı, yoksa bir **ilk adım** mı?
Toplamsa ilke ihlal edilmiştir.

---

### İ4 — Pencere kıt kaynaktır

Zorlu iş, odak penceresinin içine yerleştirilir (§2). Pencere dışında arayüz
derin iş önermez; kısa ve tek adımlı işe geçer ve bunu **söyler** ("bunu yarın
okuldan sonra yapmak daha kolay olur").

*Neden:* pencere gerçek ve dar. Onu görmezden gelen bir arayüz, kullanıcının en
zayıf saatinde en zor işi önerir.

*Test:* Saat 20:00'de açıldığında arayüz hâlâ "sınav hazırlığına başla" mı diyor?
Diyorsa ilke ihlal edilmiştir.

---

### İ5 — Dönüş bedavadır

Yarıda bırakıp 20 dakika sonra dönmek **hiçbir şeye mal olmaz**. Durum korunur,
konum işaretlidir, hiçbir şey yeniden bulunmak zorunda değildir. Kaybolan bir
form alanı, sıfırlanan bir filtre, unutulan bir kaydırma konumu — hepsi bu ilkenin
ihlalidir.

*Neden:* savrulma bu kullanıcıda istisna değil, varsayılan. Dönüşü cezalandıran
arayüz, savrulmayı terke çevirir.

*Test:* Sayfayı yenile. Kullanıcı nerede kalmıştı, oraya dönüyor mu?

---

### İ6 — Uyaran bir bütçedir

Her renk, hareket, rozet ve sayı **aynı dikkat bütçesinden** harcar. Bütçe
eyleme dönüşen şeye harcanır. Dekoratif olan her şey vergidir.

Somut sınırlar:
- Bir ekranda **en fazla bir** dikkat çekici renk alanı (uyarı/aciliyet).
- Aynı anda **en fazla bir** hareket eden öğe.
- Rozet, gerçekten bir durum ayrımı taşımıyorsa konmaz.

*Neden:* dikkat eksikliği, gürültüyü sinyalden ayırmanın pahalı olması demektir.
Arayüz o işi kullanıcıya bırakamaz.

*Test:* Ekrandaki her renkli/hareketli öğe için "bu kaldırılırsa hangi bilgi
kaybolur?" — cevap yoksa kaldır.

---

### İ7 — Bitmiş iş öne çıkmaz

Tamamlanan, süresi geçen, artık eylem gerektirmeyen hiçbir şey, eylem gerektiren
şeyle **aynı görsel ağırlıkta** durmaz. Geçmiş erişilebilir kalır; öne çıkmaz.

*Neden:* şu anki Ödevler sayfası Mart'tan kalma 12 bitmiş ödevle açılıyor ve
yapılacak iş yokken 1500 piksel ölü geçmiş gösteriyor. Bu, dikkati tam olarak
işe yaramaz yere harcatır.

*Test:* Sayfayı aç. İlk ekranda görünen öğelerin kaçı **bugün eylem gerektiriyor**?
Yarıdan azsa ilke ihlal edilmiştir.

---

### İ8 — Renk durumu kodlar, taksonomiyi değil

Renk öncelikle **ne yapılması gerektiğini** söyler (acil / bekliyor / bitti /
bozuk). Ders veya içerik türü gibi taksonomi, renkten önce **konum, sıra ve
etiketle** anlatılır. Taksonomi rengi ancak eylem rengiyle çakışmadığı yerde ve
düşük doygunlukta kullanılır.

*Neden:* bugün yedi kategori rengi var (`--ted-cat-*`). Yedi renk, hiçbiri
"bu önemli" diyemeyecek kadar çok renktir.

*Test:* Ekranı gri tonlamaya çevir. Neyin acil olduğu hâlâ anlaşılıyor mu?
Anlaşılmıyorsa renk tek taşıyıcı olmuş demektir (D2 ihlali de sayılır).

*Ders rengi (2026-09-24):* taksonominin renk alabilen tek biçimi **ders
kimliğidir** ve bu ilkenin koşullarını yapısal olarak sağlar. Her ders bir alana,
her alan bir Carbon Tag ailesine bağlanır (Türkçe magenta, matematik mor, fen
teal, sosyal camgöbeği, yabancı diller mavi, değerler sıcak gri, bilişim soğuk
gri, sanat-spor ve genel gri); tek kaynak `tedyLayer.subjectThemes`
(`src/subject_themes.py`, `dashboard/src/theme/subjects.ts`). Eylem ve durum
renkleri — kırmızı, yeşil, sarı, turuncu — hiçbir derse verilmez. Panoda ders
rengi yalnız küçük işarettir (`SubjectLabel` karesi), kart kenarıdır ya da ders
adının yanındaki kicker'dır; ders asla durum etiketi (`Tag`) biçiminde görünmez ve
geri sayım etiketleri yalnız kırmızı + nötr kullanır, bu yüzden ders rengiyle
durum rengi aynı biçimde karşılaşmaz. Modül, pano ve katalog aynı dersi aynı
renkle gösterir.

---

### İ9 — Arayüz tek bir sesle konuşur

Aynı şey her yerde aynı kelimeyle anılır. Bir eylem, akışın başından sonuna
adını korur: "Başla" diyen düğme "Başladın" diyen bir sonuç üretir. Boş ekran bir
davettir, bir özür değil. Hata ne olduğunu ve ne yapılacağını söyler.

*Neden:* tutarlı sözlük, öğrenme yükünü düşürür — çalışma belleği zayıf olan
kullanıcıda bu doğrudan kullanılabilirliktir.

*Test:* Aynı kavram iki ekranda iki farklı kelimeyle mi anılıyor?

---

## 5. Sistem

### 5.1 Renk

Temel: **Carbon g10**. TEDY'nin kendi katmanı `--ted-*` token'larıyla, Carbon
token'larından türetilerek yaşar.

Yeniden yapılandırma yönü:

| Rol | Kullanım | Sınır |
|---|---|---|
| **Eylem** | Şimdi yapılacak tek şey | Ekranda bir tane |
| **Uyarı** | Yaklaşan / gecikmiş | Gerçek aciliyet varken |
| **Durum-bozuk** | Sistem/portal arızası (D3) | Nadir, ayırt edici |
| **Nötr** | Geçmiş, bitmiş, arka plan | Çoğunluk |
| **Taksonomi** | Ders/tür ayrımı | Düşük doygunluk, eylem rengiyle çakışmaz |

Bugünkü yedi `--ted-cat-*` rengi bu şemaya indirgenir. Hangi kategorinin renk
hakkını koruyacağı §7'deki bilgi mimarisiyle birlikte kararlaştırılır.

### 5.2 Tipografi — iki dünya

TEDY'de iki farklı iş var ve ikisi aynı sesle konuşmamalı:

- **Yapma yüzeyi** (pano, ödev, program, asistan): **IBM Plex Sans** — Carbon'un
  kendi sesi. Nötr, yoğun bilgi taşıyan, tarayarak okunan.
- **Okuma yüzeyi** (Tedy Books): **Cormorant Garamond + Literata** — kitap sesi.
  Sürekli okuma için, uzun satır, sakin ritim.

Bu ayrım **zaten var ve doğrudur**; icat edilmesi değil korunması gerekir. Bir
kullanıcı okuma dünyasına girdiğinde bunu tipografiden anlar. Yapma yüzeyine
kitap tipografisi, okuma yüzeyine arayüz tipografisi sızmaz.

Ölçek Carbon type token'larından gelir (`type-style`). Yeni punto icat edilmez.

### 5.3 Yoğunluk

Işık'ın yüzeyi **seyrek**, veli görünümü **yoğun** olabilir. Aynı bileşenin iki
yoğunlukta yaşaması Carbon'da doğaldır; hangi yoğunluğun kullanılacağı
kullanıcıya göre değil **role** göre seçilir.

### 5.4 Hareket

Hareket üç işe yarar: **konum değişimini anlatmak**, **yeni geleni işaret etmek**,
**bekleyişi katlanılır kılmak**. Bunların dışındaki hareket İ6'ya göre vergidir.

Süreler Carbon `motion` token'larından. Aynı anda tek hareket (İ6).
`prefers-reduced-motion` yalnız süreyi kısaltmaz; hareketin **bilgi taşıdığı**
yerde hareketi kaldırmaz, taşımadığı yerde tamamen kaldırır.

### 5.5 Dil

Türkçe, sen diliyle, cümle düzeninde (Başlık Her Kelime Büyük değil).
Emir kipi net yönlendirmede kullanılır (İ1) ama suçlayıcı olmaz.
"Yapmadın" değil "henüz yapılmadı". Ham token yasak (D4).

---

## 6. İmza öğe: Gün Şeridi

Panonun hatırlanacak tek öğesi **Gün Şeridi** olur: uyanmadan uykuya günün
tamamını gösteren yatay bir bant.

Üzerinde:
- **"şimdi"** — gerçek ve hareket eden bir konum
- **odak penceresi** — gölgeli alan (§2)
- **okul blokları** — sabit, değiştirilemez
- **işler** — teslim tarihine değil, **yapılacağı dilime** yerleştirilmiş

Neden bu:
1. Okul hayatı zaten zamanla örgütlüdür — ders, teneffüs, zil. Şerit konunun
   kendi diliyle konuşur, panoların jenerik kart dilini değil.
2. Zaman körlüğüne doğrudan yanıt: soyut tarih yerine görülebilir mesafe (İ2).
3. Pencereyi görünür kılar; İ4 böylece anlatılan bir kural olmaktan çıkıp
   **bakılan bir şey** olur.
4. İşi teslim tarihine değil **yapılacağı ana** bağlar; bu, süreyi büyüten
   kullanıcıda "ne zaman başlayacağım" sorusunu ortadan kaldırır (İ3).

Şerit **Bugün**'ün omurgasıdır ve diğer sayfalarda daraltılmış hâliyle bulunur.

Bu, panonun tek gösterişli öğesidir. Etrafındaki her şey sakin ve disiplinli
kalır (İ6).

---

## 7. Bilgi mimarisi — öneri

Bugün **13 nav öğesi** var ve hepsi **ikon, etiketsiz**. Çalışma belleği zayıf bir
kullanıcı için bu, iş yapmadan önce 13 hatırlama kararıdır.

Önerilen indirgeme — **5 birincil**:

| Birincil | İçerir |
|---|---|
| **Bugün** | Gün Şeridi, şimdi yapılacak tek şey |
| **İşler** | Ödevler + Sınavlar (ikisi de "borcum olan iş") |
| **Dersler** | Program + Ders içerikleri (ikisi de "ne çalışıyorum") |
| **Asistan** | — |
| **Tedy Books** | — |

İkincil (bir "Daha fazla" altında veya profil menüsünde): Notlar, İlerleme,
Duyurular, Takvim, Takımlar, Profil.

**Nav etiketlenir.** İkon tek başına taşıyıcı olamaz.

Bu bir öneridir, karar değil. Kabul edilirse rota değişikliği ve yönlendirme
gerektirir; eski yollar kırılmaz, yeni yerlerine yönlendirilir.

---

## 8. Bugünkü arayüzün ölçülmüş kusurları

Aşağıdakiler varsayım değil; 2026-08-31'de canlı panodan alınmış ekran
görüntülerinden çıkarıldı.

**Bugün sayfası**
1. Sayfadaki en gürültülü öğe **Tedy Books** bandı (koyu zemin, altın, büyük) ve
   okul ajandasının üstünde duruyor. Opsiyonel olan, zorunlu olandan yüksek sesle
   konuşuyor. → İ1, İ6 ihlali.
2. Sol ray 13 ikon, etiketsiz. → §7.
3. İçerik ~530px'te bitiyor, altında ~350px boşluk. Katlama altı bilgi taşımıyor.

**Ödevler sayfası**
4. Özet satırı: "Toplam Ödev: 0 Yaptı: 0 Geç: 0 Eksik: 0 Değerlendirilmemiş: 0
   Teslim Edilmeyen: 0" — altı sıfır, tek satırda, hiçbir şey söylemeden. → İ3, İ6.
5. Sayfa **Mart'tan kalma 12 bitmiş ödevle** açılıyor; hepsi "YAPILAN", hepsinde
   "Süresi doldu". Yapılacak iş yokken 1500px ölü geçmiş. → İ7 ihlali.
6. `İlk görülme: 2026-03-11T23:29:16.752613` — mikrosaniyeli ham ISO damgası
   ekranda. → **D4 ihlali.**
7. Bitmiş ödev ile bekleyen ödev **aynı görsel ağırlıkta**. → İ7, İ8.
8. Bitmiş işte "Süresi doldu" rozeti — teknik olarak doğru, anlamca yanlış ve
   gereksiz alarm. → İ9.

---

## 9. Yapmayacaklarımız

- **KPI kartı ızgarası.** Dört renkli sayı kutusu, okul panosunun jenerik
  cevabıdır ve İ3'ü doğrudan ihlal eder (toplamı öne çıkarır).
- **Kutlama.** Konfeti, rozet avı, seri sayacı. Dışsal ödül, bu profilde içsel
  motivasyonu aşındırma riski taşır ve İ6'nın bütçesini harcar. Tamamlanma
  **sessizce ve net** gösterilir.
- **Bildirim yağmuru.** Hatırlatma, kalıcı görünürlüğün yerini tutmaz. Kalıcı
  görünürlük (şerit) tercih edilir.
- **Suçlayıcı dil.** "Yapmadın", "geciktin", kırmızı ünlem. Gecikme bilgi olarak
  verilir, yargı olarak değil.
- **Sonsuz kaydırma / gizli keşif.** Her şey adlandırılmış bir yerde durur.
- **Carbon dışı renk ve punto.** (D1)

---

## 10. Doğrulama kapıları

Bir ekran "bitti" sayılmadan önce:

- [ ] **2 saniye testi** (İ1): sonraki adım tek ve doğru okunuyor.
- [ ] **Gri tonlama testi** (İ8/D2): aciliyet renk olmadan da anlaşılıyor.
- [ ] **İlk ekran testi** (İ7): görünen öğelerin yarısından çoğu bugün eylem
      gerektiriyor.
- [ ] **Yenileme testi** (İ5): kullanıcı kaldığı yere dönüyor.
- [ ] **20:00 testi** (İ4): pencere dışında derin iş önerilmiyor.
- [ ] **Sızıntı taraması** (D4): ekranda ham token, ISO damgası, iç kod yok.
- [ ] **Klavye turu** (D2): her etkileşimli öğeye ulaşılıyor, odak görünür.
- [ ] **Kontrast** (D2): AA sağlanıyor.
- [ ] **Reduced motion** (5.4): kapalıyken bilgi kaybı yok.
- [ ] **Boş durum** (D3): boşsa nedeni yazıyor.

---

## Değişiklik kaydı

| Sürüm | Tarih | Not |
|---|---|---|
| 1.0 | 2026-08-31 | İlk sürüm. Işık'ın profili, ölçülmüş mevcut durum ve Carbon v11 tabanı üzerine. |
