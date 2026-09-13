# Yeni Nesil Soru Tasarımı — Taksonomi, Bilişsel Eşleme ve Yazım Reçetesi

> **Ne zaman okunur:** Bir modüle "yeni nesil" / LGS tarzı bir soru bloğu
> eklerken. Bu blok, tema kazanımlarının **ötesinde**, ileri düzey bir katman
> olarak konumlanır (bkz. §6 Kapsam notu) — tema kazanımının yerine geçmez.
>
> **Ön koşul:** `references/adhd-pedagogy.md` (zorunlu) ve
> `references/interaction-patterns.md` (segment şemaları).

Yeni nesil sorular, MEB'in ölçme yaklaşımında **bilgiyi hatırlatmaktan** çok
**bir uyaran üzerinde muhakeme ettirmeye** dayanır. Öğrenci bir metin, görsel,
tablo ya da senaryo ile karşılaşır; doğru cevap o uyaranın **içinden** çıkarılır.
Bu dosya deseni dört kategoriye ayırır, her birini bilişsel yetkinliğe eşler ve
`MODULE_DATA` içinde nasıl kurulacağını gösterir.

---

## 1. Dört kategorili taksonomi

| # | Kategori | Uyaran | Öğrenciden istenen |
|---|---|---|---|
| K1 | **İnfografik / görsel okuryazarlık** | Şema, grafik, etiketli figür, tablo | Veriyi **sentezlemek**: birden çok görsel öğeyi birleştirip tek bir çıkarıma varmak |
| K2 | **Sözel mantık / muhakeme** | Kısa önerme kümesi, koşullu ifadeler, kural + durum | **Analitik çıkarım**: verilen kurallardan zorunlu sonucu türetmek |
| K3 | **Çoklu metin analizi** | İki (veya daha çok) kısa metin | **Metinlerarası ilişkilendirme**: iki metnin ortaklaştığı/ayrıştığı noktayı saptamak |
| K4 | **Gerçek-yaşam senaryosu / işlevsel okuma** | Bilet, kullanım kılavuzu, ilan, tarife, etiket | **İşlevsel okuma**: günlük bir belgeden hedefe yönelik bilgi çekmek |

---

## 2. Bilişsel yetkinlik eşlemesi

Her kategori farklı bir bilişsel yükü hedefler. DEHB-odaklı tasarımda bu önemlidir:
kategoriler **rastgele değil**, hedeflenen yetkinliğe göre seçilir.

| Kategori | Birincil yetkinlik | İkincil | DEHB tasarım özeni (ped §10) |
|---|---|---|---|
| K1 | **Ayrıntıya odak** (görsel tarama, ilgili/ilgisiz ayrımı) | Veri sentezi | Görselde süs-kalabalığı yok; tek odak; uyaran soru kökü ile **aynı ekranda** kalır (Ö2) |
| K2 | **İşleyen bellek** (önermeleri akılda tutup birleştirme) | Nesnel çıkarım | Önerme sayısı sınırlı (≤3–4); "akılda tut ve sayfayı çevir" yasak (Ö2) |
| K3 | **Nesnel çıkarım** (kendi görüşünü değil, metnin dediğini raporlama) | İşleyen bellek | İki metin ardışık `teach` ile sunulur, soru anında **ikisi de erişilebilir** olmalı |
| K4 | **Ayrıntıya odak** + amaç-yönelimli tarama | Veri sentezi | Belge gerçekçi ama sade; aranan bilgi tek; süre baskısı yok |

> **Neden bu üçlü (işleyen bellek, ayrıntıya odak, nesnel çıkarım)?** Üçü de
> DEHB'de kırılgan olan yürütücü işlev bileşenleridir (ped §1, Ö2). Yeni nesil
> soru bunları **çalıştırır**; bu nedenle destekleyici tasarım (tek görev, uyaran
> ekranda kalır, ceza yok) burada gevşetilemez — aksine sıkılaştırılır.

---

## 3. Geleneksel ↔ yeni nesil karşıtlığı

| Boyut | Geleneksel soru | Yeni nesil soru |
|---|---|---|
| Uyaran | Tek metin / doğrudan soru kökü | **Çoklu uyaran** (metin + görsel + tablo) |
| Bilişsel talep | Bilgiyi **hatırlama** | Uyarandan **çıkarım** |
| Doğru cevabın kaynağı | Ezberlenmiş bilgi | **Uyaranın kendisi** |
| Ön bilgi rolü | Belirleyici (bilmiyorsa yapamaz) | Erişim koşulu (okuyup muhakeme edebilen yapar) |
| Bağlam | Soyut / ders-içi | **Gerçek yaşam** bağlamı sık |
| Çeldirici mantığı | Yanlış bilgi | **Uyaranda geçen ama sorulmayan** doğru bilgi (dikkat testi) |

> Çeldirici farkı kritiktir: yeni nesilde çeldirici genellikle **doğru ama
> ilgisiz**tir. Bu, ayrıntıya odağı ölçer — ama aynı zamanda DEHB'li öğrenci için
> en zorlayıcı noktadır. Bu yüzden geri bildirim **neden ilgisiz olduğunu**
> açıklamalıdır (yalnız "yanlış" demek yetmez; Ö4).

---

## 4. `MODULE_DATA`'da yazım reçetesi

Yeni nesil blok **yeni bir segment tipi getirmez** — mevcut desenlerden kurulur.

| Kategori | Segment kurgusu | Not |
|---|---|---|
| **K1** — infografik | `svgFigure` / `vizChart` içeren `teach` **veya** `hotspot` / etiketli figür → ardından `mcq` | Görsel, soruyla aynı ekranda kalmıyorsa `hotspot` tercih edilir (uyaran + soru tek segment) |
| **K2** — sözel mantık | Doğrudan `mcq`; önermeler soru kökünün içinde | Ek `teach` gerekmez; önerme kümesi kısa tutulur |
| **K3** — çoklu metin | Ardışık `teach` (Metin I) + `teach` (Metin II) → `mcq` | İki metin de kısa olmalı; soru köküne her ikisinden de alıntı/anahtar sözcük konur |
| **K4** — senaryo | Belgeyi taşıyan `teach` (veya `table`) → `mcq` | Belge biçimsel görünsün (tarife/etiket düzeni); `table` segmenti çoğu zaman en sadık taşıyıcıdır |

**Ortak kurallar**

- Her soru `mcq` şemasına uyar; `correctIndex` **zorunlu** (G-INTERACT kapısı).
- Zorluk kademeli artar: blok içinde K1 → K2 → K3 → K4 sırası doğal bir gradyan verir
  (görselden metne, tekil uyarandan çoklu uyarana).
- Yeni nesil blok **mola kuralını** boşa düşürmez: blok ≥6 segmentse en az bir
  `brainbreak` (ped §10.1; `interaction-patterns.md` Akış kurgu kuralları).
- Emoji yok; geri bildirim ikonu Carbon setinden (G-EMOJI).

---

## 5. Uyaran-izlenebilirlik ilkesi (ZORUNLU)

> **Her sorunun doğru cevabı, yalnızca kendi uyaranından (metin / görsel / tablo /
> senaryo) çıkarılabilmelidir. Dış bilgi, ders-dışı ön bilgi veya genel kültür
> gerektiren hiçbir soru yazılmaz.**

Bu ilke iki nedenle pazarlık dışıdır:

1. **Ölçme geçerliği.** Uyarandan çıkarılamayan bir cevap, muhakemeyi değil ön
   bilgiyi ölçer — yani sorunun yeni nesil olma iddiasını çürütür.
2. **Adalet ve kaynak-sadakati.** Modül, kendi kaynağına sadık olmak zorundadır
   (SKILL.md §7). Uyaranda olmayan bir bilgiyi doğru cevap yapmak, modülü
   kaynağının ötesine taşır — üretilmiş (fabricated) içerik olur.

**Yazım denetimi (her soru için, tek tek):**

- [ ] Doğru cevabı destekleyen ifade uyaranda **birebir veya çıkarımla** var mı?
- [ ] Uyaranı hiç görmeyen biri soruyu güvenilir biçimde yapabilir mi? → **Yapabiliyorsa soru bozuktur** (ön bilgiyle çözülüyor).
- [ ] Her çeldirici, uyaranla **ilişkilendirilebilir** mi? (rastgele yanlış değil)
- [ ] Geri bildirim, doğru cevabın uyarandaki **dayanağını** gösteriyor mu?

---

## 6. Kapsam notu — yeni nesil blok tema kazanımına haritalanmaz

Yeni nesil blok, tema kazanımlarının **üzerine** oturan bir **ileri düzey**
katmandır. Ölçtüğü şey büyük ölçüde **format becerisi**dir (çoklu uyaranı
işleme, işlevsel okuma, analitik çıkarım) — tek bir tema kazanımının
davranışsal ifadesi değil.

Sonuç olarak:

- Blok, `curriculum` veri bloğunda bir kazanım koduna **bağlanmaz**; bağlanmaya
  zorlanırsa sahte bir provenans üretilmiş olur (G-CURRICULUM'un kaçınmak istediği şey).
- Blok, modülde **ayrı ve isteğe bağlı** bir ileri-düzey bölüm olarak sunulur;
  tema kazanımlarının değerlendirmesi checkpoint'te ayrıca yapılır.
- Modül özetinde blok "ileri düzey" olarak etiketlenir; düşük skor **etiketleyici
  değil bilgilendirici** sunulur (Ö4).

---

## 7. Örnek soru iskeletleri

> Aşağıdakiler **iskelet**tir (içerik yer tutucudur) — id konvansiyonu `ng1…ngN`.
> Gerçek modülde uyaran ve seçenekler **kaynaktan** doldurulur (SKILL.md §7).

### K1 — İnfografik / görsel okuryazarlık (`ng1`)

```js
// Uyaran ve soru AYNI ekranda: hotspot tercih edilir
{ type:"hotspot", id:"ng1", title:"Grafiği Oku", pictogram:"pic-microscope",
  instructions:"Grafikteki iki eğriyi karşılaştır, sonra soruyu yanıtla.",
  svg:"<svg …>",              // tema-duyarlı, erişilebilir (svg-authoring.md)
  regions:[ /* … */ ] },
{ type:"mcq", id:"ng1q", title:"Veri Sentezi",
  questions:[{
    q:"Grafiğe göre iki değişkenin birlikte arttığı tek aralık hangisidir?",
    options:["…","…","…","…"],
    correctIndex:2,
    // Geri bildirim doğru cevabın UYARANDAKİ dayanağını gösterir:
    explain:"Yalnız 3. aralıkta her iki eğri de yükseliyor; 1. aralıkta biri düşüyor." }] }
```

### K2 — Sözel mantık / muhakeme (`ng2`)

```js
// Önermeler soru kökünün İÇİNDE; ek teach gerekmez, akılda-tutma yükü düşük
{ type:"mcq", id:"ng2", title:"Mantıksal Çıkarım", pictogram:"pic-puzzle",
  questions:[{
    q:"Bir kulüpte şu kurallar geçerlidir: (1) Satranç oynayan herkes salı günü gelir. "
     +"(2) Salı günü gelenlerin bazıları koroya da katılır. Buna göre AŞAĞIDAKİLERDEN "
     +"HANGİSİ kesinlikle doğrudur?",
    options:[
      "Satranç oynayan herkes koroya katılır.",   // aşırı genelleme çeldiricisi
      "Satranç oynayan herkes salı günü kulüptedir.",
      "Koroya katılan herkes satranç oynar.",     // yön çevirme çeldiricisi
      "Salı günü gelen herkes satranç oynar."],
    correctIndex:1,
    explain:"(1) doğrudan bunu söyler. Diğerleri kurallardan ZORUNLU olarak çıkmaz — "
           +"'bazıları' ifadesi 'hepsi'ne genişletilemez." }] }
```

### K3 — Çoklu metin analizi (`ng3`)

```js
// İki kısa metin ardışık teach ile; soru her ikisine de dokunur
{ type:"teach", id:"ng3a", title:"Metin I", body:"<p>…</p>" },
{ type:"teach", id:"ng3b", title:"Metin II", body:"<p>…</p>" },
{ type:"mcq", id:"ng3q", title:"İki Metni Karşılaştır",
  questions:[{
    q:"Metin I ve Metin II, aynı olguyu ele almalarına rağmen hangi noktada AYRILIR?",
    options:["…","…","…","…"],
    correctIndex:0,
    explain:"Metin I olgunun nedenine, Metin II sonucuna odaklanır; ikisi de olgunun "
           +"varlığını yadsımaz." }] }
```

### K4 — Gerçek-yaşam senaryosu / işlevsel okuma (`ng4`)

```js
// Belge biçimsel görünsün: table çoğu zaman en sadık taşıyıcı
{ type:"table", id:"ng4", title:"Otobüs Tarifesi", pictogram:"pic-education",
  caption:"Hafta içi kalkış saatleri",
  headers:["Hat","İlk kalkış","Sefer aralığı","Son kalkış"],
  rows:[ ["…","…","…","…"] ] },
{ type:"mcq", id:"ng4q", title:"Tarifeyi Kullan",
  questions:[{
    q:"Saat 08:15'te durağa varan biri, 12 numaralı hatta en erken hangi saatte binebilir?",
    options:["08:20","08:25","08:30","08:40"],
    correctIndex:1,
    explain:"12 numaralı hat 07:45'te başlar ve 20 dakikada bir kalkar; 08:15'ten sonraki "
           +"ilk kalkış 08:25'tir." }] }
```

---

## 8. Yapma listesi (anti-pattern)

- **YAPMA** — **Ön bilgiyle çözülen "yeni nesil" soru.** Uzun bir senaryo yazıp cevabı
  senaryodan değil ezberden istemek — en yaygın sahte yeni-nesil hatası (§5).
- **YAPMA** — **Çeldiricisiz uzun metin.** Uyaranı şişirip soruyu kolaylaştırmak; okuma
  yükü artar, ölçme değeri artmaz (Ö2'ye aykırı).
- **YAPMA** — **Akılda-tutmalı çoklu metin.** Metni gösterip sonra gizlemek; işleyen bellek
  yükü ölçüm hatasına dönüşür.
- **YAPMA** — **Kazanım koduna zorla bağlama.** Format becerisini tema kazanımı gibi
  raporlamak (§6).
- **YAPMA** — **Süre baskısı / ceza.** Yeni nesil blok da baskısızdır; yanlışta ipucu +
  tekrar (Ö4, G-WELLBEING).
