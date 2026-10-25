# Sınav Hazırlığı — MEB senaryo yüzeyleri, kapsam kılavuzu ve A4 PDF

Tarih: 2026-10-25 · Durum: tasarım onaylandı (sohbette dört bölüm hâlinde), yazılı spec onayı bekliyor
İlgili: `docs/superpowers/specs/2026-10-19-meb-sinav-senaryolari-design.md` (senaryo tablosu ve doğrulama; bu iş onun üstüne kurulur), `docs/superpowers/specs/2026-10-16-sinav-tespiti-ve-uyari-design.md` (sınav kayıtları), `docs/superpowers/specs/2026-10-19-aksam-calisma-plani-design.md` (akşam planı)

## 0. Niyet

7. sınıf öğrencisi, MEB ÖDSGM'nin 2026-2027 1. dönem konu-soru dağılım senaryolarının **hepsini** ders ders, şık ve kolay kullanılan yüzeylerde görür; herhangi bir dersin herhangi bir ortak yazılısı için **çok kapsamlı bir kapsam kılavuzu** açar ve onu Carbon uyumlu, şık bir **A4 PDF** olarak indirir.

Kılavuzun omurgası MEB ders kitabıdır: senaryodaki her öğrenme çıktısı için kitabın **ünite, içerik çerçevesi ve konu başlıkları** kitaptaki adlarıyla ve basılı sayfa numaralarıyla yazılır; o bölümde ele alınan konular **başlıklar** hâlinde sayılır.

Kullanıcı kararları (2026-10-25, sohbette):

- Kılavuz bir **öğrenci çalışma kılavuzudur**; MEB kitabının konu ve bölüm başlıkları açıkça belirtilir ve ilgili bölümde ele alınan konular başlıklar biçiminde verilir. Tasarım çok önemlidir; tasarım için ayrı bir kurallar bütünü (§6, kanun) yazılır.
- Asistanın önerdiği eklerin hepsi kabul edildi: senaryo karşılaştırması, kesin/olası ayrımı, kişisel hazırlık durumu, geri sayım planı, prova kâğıdı, kaynak/sürüm damgası, ebeveyn özeti, kitaba bağlantı.
- Yapay zekâ: **belgeye dayalı çekirdek + ayrı, etiketli, isteğe bağlı YZ bölümleri** (seçenek A).
- Yerleşim: **ayrı "Sınav Hazırlığı" sayfası + her yerden giriş** (seçenek A).
- PDF: **sunucuda başsız Chrome + Paged.js**; ilk görev bir yoklama (§5.4).
- Görsel kararlar (görsel taslaklar, 2026-10-25): ana sayfa **önce zaman**; ders sayfası **karşılaştırma tablosu**; A4 çizgisi **Carbon üretken** (ekranla birebir).
- Aşamalı teslim; 4. ve 5. aşamalar önce Fen için açılır (3 Kasım Fen 1. yazılısı), sonra altı derse genişler.

## 1. Ölçülenler (2026-10-25)

- **Senaryo tablosu:** `src/sinav_senaryolari.json` — altı ders, iki ortak yazılı, toplam 63 senaryo; Türkçe 2. yazılı `ulke_geneli`. Çıktı kayıtları `kod`, `metin`, `konu` (içerik çerçevesi adı) taşır. Örnek: Fen 1. yazılı 4 senaryo, toplam 9/7/8/6 soru; FB.7.2.1 dört senaryonun hepsinde (3/3/2/2).
- **Ders kitapları (Maarif korpusu `list_textbooks`, 7. sınıf):** Türkçe 1. Kitap (id 460) ve 2. Kitap (340); Matematik 1 (346), 2 (506); Fen Bilimleri 1 (439, `fenbilimleri7-1_v3.pdf`), 2 (473); Sosyal Bilgiler 1 (491), 2 (361); İngilizce ders kitabı (334) ve çalışma kitabı (457). **Din Kültürü ve Ahlak Bilgisi 7 listede yok** — EBA'da doğrudan aranacak (§8).
- **Kitap PDF'lerinin yapısı (Fen 7 1. Kitap, 86,8 MB):**
  - PDF yer imleri yalnız ünite düzeyinde (3 öğe).
  - Basılı "İçindekiler" sayfası tam yapıyı verir: ünite (no, ad) → numaralı içerik çerçevesi ("1. Türkiye ve Uzay Araştırmaları ……… 15") → konu başlıkları ("Uzay Teknolojileri ……… 16"). `pdftotext -layout` bunu temiz okur.
  - Basılı sayfa = PDF sayfası − 1 (Fen 7-1'de; kitap başına ölçülür).
  - Bölüm içi başlıklar sayfa düzeninden okunur: konu ve kitabın pedagojik blokları 18 pt ("Fiziksel Anlamda İş", "Etkinlik Noktası-1", "Bağlantı Noktası", "Kontrol Noktası", "Neler Öğrendik?"), gövde 15,2 pt; etkinliklerin "Amaç:" satırı başlığın konusunu verir. Kalın tanım başlıkları ("Potansiyel Enerji:") gövde boyundadır; yazı tipi ağırlığıyla ayrılır.
  - Maarif korpusunun sayfa metni bazı sayfalarda bozuk kodlamalı ve İçindekiler sayfaları boş; kaynak EBA PDF'inin kendisidir.
- **Paged.js:** npm `pagedjs` 0.4.3 (son kararlı, 2024-10), 0.5.0-beta.2; MIT. `pagedjs-cli` 0.4.3.
- **Mevcut uygulama:** rota kaydı `dashboard/src/routes.ts`; Sınavlar `/sinavlar` (`ExamTimeline`), Dersler `/dersler`, "Daha fazla" `/daha-fazla`. Depoda PDF ya da baskı altyapısı yok. Ders renkleri `theme/_subjects.scss` (`--ted-subject-accent`, Carbon 60 tonları).

## 2. Veri katmanı

### 2.1 Senaryo tablosu (var)
Değişmez. Kılavuz modeli `sinav_senaryo.tablo_oku()` ile okur.

### 2.2 Kitap haritası (yeni)
- **Üretici:** `scripts/meb_kitap_haritasi.py <ders> [--pdf yol]`; EBA'dan PDF'i indirir (ya da yerel dosya), `src/kitap_haritalari/<ders-anahtarı>.json` yazar. Elle düzenlenmez.
- **Yapı:**
  ```
  {surum, ders, kitaplar: [{baslik, pdf_url, kaynak_sayfa, sha256, baski, sayfa_kaymasi,
     uniteler: [{no, ad, sayfa,
       cerceveler: [{no, ad, sayfa, son_sayfa, ciktilar: ["FB.7.1.1", …],
         konular: [{ad, sayfa, son_sayfa,
           basliklar: [{ad, tur: "etkinlik"|"baglanti"|"kontrol"|"tanim"|"ozet"|"diger", amac?, sayfa}]}]}]}]}],
   eslesme: {"FB.7.2.1": [{kitap, unite, cerceve, konu}]}, denetim: {kim, tarih}}
  ```
- **Kaynaklar:** ünite/çerçeve/konu ve sayfalar İçindekiler'den birebir; `ciktilar` çerçeve açılış sayfasındaki "Öğrenme Çıktıları" listesinden; `basliklar` sayfa düzeninden (yazı boyu ve ağırlığı); `eslesme` çerçeve çıktı listesi + konu adının çıktı metniyle örtüşmesi.
- **Yapı denetimi (geçmezse dosya yazılmaz, eski kalır):** senaryo tablosundaki her çıktı en az bir konuya bağlı ya da açıkça `eslesmedi` listesinde; sayfalar artan sırada ve kitap sınırları içinde; her konunun en az bir başlığı var; İçindekiler'deki her girdi haritada.
- **Onay:** ilk üretimi asistan kitapla tek tek karşılaştırır, `denetim` alanına kim/tarih yazılır. MEB PDF'i değişirse (`sha256` farkı) kılavuz "kitap güncellendi, harita yenilenmeli" der (K12).

### 2.3 TEDY verisi (var) ve hazırlık işaretleri (yeni)
- Sınav kayıtları ve duyurulan senaryo (`output/sinavlar.json`, `senaryo` bloğu), ders kartı haftaları, ödevler, notlar, yayındaki modüller.
- **Hazırlık işareti:** kişi başına, çıktı başına `hazirim` | `tekrar` | yok; `output/hazirlik_isaretleri.json` (atomik yazım, kişi anahtarlı). Okuma yetkili hesap işaret koyamaz.

### 2.4 Kılavuz modeli
`src/sinav_kilavuzu.py`:
- `genel_bakis(kullanici, bugun)` → yaklaşan ortak yazılılar (geri sayım, senaryo durumu) + altı ders karosu.
- `ders_ozeti(ders, sinav_no)` → karşılaştırma matrisi (ünite gruplu çıktı × senaryo), "her senaryoda" çıktılar, duyurulan senaryo.
- `kilavuz(ders, sinav_no, senaryo | None, kullanici, secenekler)` → deterministik JSON: özet, içindekiler girdileri, matris, ünite → çerçeve → çıktı blokları (MEB metni, soru sayısı, kitapta yolu, ele alınan başlıklar, okulda işlendiği hafta, ödev/modül/not, işaret), doğrulama, çalışma planı, kaynaklar, damgalar, `icerik_ozeti` (sha256; PDF önbellek anahtarı).
- Senaryo yoksa (duyurulmadı) blok soru sayıları yerine "senaryoya göre 0–3" aralığını ve "her senaryoda" işaretini taşır; hiçbir yüzey tek senaryoyu "bu" diye sunmaz (K8).

### 2.5 API
- `GET /api/hazirlik` — genel bakış
- `GET /api/hazirlik/<ders>/<sinav_no>` — ders özeti
- `GET /api/hazirlik/<ders>/<sinav_no>/kilavuz?senaryo=N` — kılavuz modeli
- `GET /api/hazirlik/<ders>/<sinav_no>/kilavuz.pdf?senaryo=N&yz=1&prova=1&ebeveyn=1&isaret=1` — A4 PDF
- `PUT /api/hazirlik/isaret` — `{ders, kod, durum}`
Hepsi `@require_auth`; ders anahtarı ve sınav no doğrulanır; bilinmeyen değer 404.

## 3. Yüzeyler

### 3.1 Sınav Hazırlığı ana sayfası (`/hazirlik`)
Başlık + kaynak satırı (MEB tablosu, güncelleme tarihi). **Yaklaşan ortak yazılılar:** tarihi belli sınavlar, geri sayım, durum etiketi (kesin: N. senaryo / olası / ülke geneli / geçti), soru sayısı, duyurulan konu sayısı. **Dersler:** altı karo (ders rengi üst çizgi), her karoda en yakın yazılı ve durum. Telefonda tek sütun karolar 2×3.

### 3.2 Ders sayfası (`/hazirlik/:ders`)
Breadcrumb, ders adı ve ders rengi çizgisi; sınav sekmeleri (1. yazılı / 2. yazılı, tarihleriyle). Duyuru varsa yeşil bildirim duyuru cümlesini aynen taşır. **Karşılaştırma tablosu** (Carbon DataTable): satırlar ünite gruplu çıktılar (kod + kısa ad), sütunlar senaryolar, duyurulan sütun vurgulu, sıfır "–", "her senaryoda" etiketi, toplam satırı. Satıra dokununca (telefonda alttan, masaüstünde yan panel) tam MEB metni ve kitap bölümü. Altta birincil düğme "Kapsam kılavuzunu aç (N. senaryo)" ve ikincil "PDF olarak indir". Senaryo duyurulmadıysa sütun seçimi kullanıcıya bırakılır; kılavuz "olası" kipinde açılabilir.

### 3.3 Kapsam kılavuzu ekranı (`/hazirlik/:ders/:sinav?senaryo=N`)
Masaüstünde yapışkan yan içindekiler; içerik §4 sırasıyla. Eylemler: "PDF olarak indir" (seçenek penceresi), "A4 önizleme" (Paged.js sayfa görünümü), "Asistana sor" (sınavı ve senaryoyu sabitler). Hazırlık işaretleri burada konur.

### 3.4 Giriş noktaları
Sınavlar sayfasında her ortak yazılı kartında "Kapsam kılavuzu"; Dersler'de dersin sekmesinde "MEB senaryoları"; "Daha fazla" ve masaüstü kenar menüsünde "Sınav Hazırlığı" (`routes.ts`, `secondary: true`, ikon `ExamMode`); asistanın örnek sınav/senaryo cevabından sonra "Kılavuzu aç" önerisi. Sayfa portal kapalıyken açılır (`offPortal`).

## 4. Kılavuzun içeriği (ekran ve PDF aynı sıra)
1. **Özet sayfası:** ders, sınav, tarih ve geri sayım, senaryo durumu, toplam soru, çıktı × soru dağılımı, "her senaryoda" çıktılar, damgalar.
2. **İçindekiler** (PDF'te Paged.js `target-counter` ile gerçek sayfa numaraları).
3. **Senaryo karşılaştırması** (§3.2 tablosu).
4. **Ünite ünite çıktılar.** Blok sırası sabit (K2): kod + kısa ad, soru sayısı (ve "her senaryoda"), MEB metni, **Kitapta** (kitap › ünite › içerik çerçevesi › konu · s. a–b), **Bu bölümde ele alınanlar** (başlıklar, türü ve sayfasıyla; etkinlikte "Amaç" kısaltılmış), okulda işlendiği hafta, ödev/modül/not, hazırlık işareti. Senaryoda olmayan çıktı soluk, tek satır.
5. **Duyuru doğrulaması:** duyurudaki konuların karşılığı; senaryonun duyurunun saymadığı çıktıları.
6. **Çalışma planı:** kalan günlere çıktıları soru ağırlığı ve işarete göre dağıtan deterministik plan; "Akşam planına ekle".
7. **YZ bölümleri (isteğe bağlı, Carbon AI etiketi):** çıktı başına özet ve ipucu — kaynak yalnız kitabın ilgili sayfalarının metni, cümle başına sayfa atfı; **prova kâğıdı** (senaryo dağılımına uyan örnek yazılı, cevap anahtarı ayrı sayfada).
8. **Ebeveyn özeti (isteğe bağlı):** başa tek sayfa.
9. **Kaynaklar:** ÖDSGM sayfası, EBA kitap PDF'leri (bölüm bağlantıları `#page=N`), sürümler.

**PDF seçenekleri penceresi:** YZ bölümleri, prova kâğıdı, ebeveyn özeti, hazırlık işaretleri; son seçim kişi başına hatırlanır.

**YZ üretimi:** sunucuda (ders, sınav, senaryo, kitap sha256) başına bir kez, `output/hazirlik_yz/` altında saklanır; kitap ya da tablo değişince yeniden üretilir. Modele kişisel veri gitmez (K9). Model ve bütçe uygulama planında sabitlenir.

## 5. PDF hattı

### 5.1 Baskı görünümü
`/hazirlik/:ders/:sinav/baski?…` — aynı React bileşenleri, baskı kipi: etkileşimli öğeler durağan karşılığa döner (K11), Carbon baskı stilleri, A4 `@page` kuralları.

### 5.2 Sayfalama
Paged.js (sürüm sabit, depoya alınmış; CDN yok) React çizimi ve yazı tipleri yüklendikten sonra çalışır (`document.fonts.ready`); adlandırılmış sayfalar (kapak, içindekiler, gövde, ek), kayan üst/alt bilgi, `break-inside: avoid` blokları, yetim başlık önleme, "(devam)" başlık tekrarı.

### 5.3 Basım
Sunucu (`src/hazirlik_pdf.py`) başsız Chrome'u açar (makinedeki Chrome kanalı), baskı görünümünü iç bir bilet ile yükler, Paged.js'in bitiş sinyalini bekler, `page.pdf({preferCSSPageSize: true, tagged: true, outline: true})`. Eşzamanlılık sınırı 1–2 iş, zaman aşımı; çıktı `icerik_ozeti` + seçenekler anahtarıyla önbellekte. Hata → Paged.js'siz düz baskı → yine hata → açık ileti.

### 5.4 Yoklama (1. aşamanın ilk işi)
Gerçek Fen taslağı (elle kurulmuş model + Fen 7-1 haritasının o bölümü) Carbon + Paged.js ile basılır; ölçülür: yazı tipi gömme, tablo bölünmesi, içindekiler numaraları, yetim başlık, etiket ağacı ve yer imleri, süre, bellek. Kötüyse yedek yol (düz Chrome baskısı) ana yol olur ve kanunun K5 maddeleri ona göre güncellenir.

## 6. Sınav Kılavuzu Tasarım Kanunu
Ayrı belge: `docs/sinav-kilavuzu-kanunu.md` (sürümlü, numaralı maddeler; Modül Tasarım Kanunu gibi). İlk sürümün maddeleri:

| # | Madde | Öz | Kapı |
|---|---|---|---|
| K1 | Kaynak dürüstlüğü | Kitap başlıkları yalnız kitap haritasından, birebir yazım; sayfa = basılı sayfa; MEB çıktı metni birebir; bulunamayan "bulunamadı". | var |
| K2 | Hiyerarşi | En çok dört düzey: ünite › içerik çerçevesi › çıktı › bölüm başlıkları; blok iç sırası sabit. | var |
| K3 | Tipografi | Carbon üretken tip ölçeği; IBM Plex Sans, kodlar Plex Mono; A4 gövde 9,5–10 pt, en küçük 7,5 pt. | var |
| K4 | Renk | Yalnız Carbon belirteçleri; ders rengi yalnız vurgu; durum: yeşil kesin, mavi olası, gri ülke geneli/geçti; mor yalnız YZ; kontrast AA. | var |
| K5 | Kâğıt | A4 dikey; kenar 18/16/20 mm; üst bilgi ders·sınav·senaryo, alt bilgi damga + "s. n/N"; yetim başlık yok; bölünen blokta "(devam)"; siyah-beyaz baskıda anlam korunur. | var |
| K6 | Eksiksizlik | Kılavuz kısaltılmaz; bir bölümün bütün başlıkları yazılır. | var |
| K7 | Dil | Türkçe; ad bildiren başlıklar başlık düzeninde, diğer etiketler cümle düzeninde (panonun S38/B41 kuralı, aile kararı 2026-10-19); MEB terimleri birebir; öğrenciye "sen"; sayılar rakamla; başarı vaadi yok. | kısmen |
| K8 | Durum dürüstlüğü | Senaryo duyurulmadıysa hiçbir yüzey tek senaryoyu "bu" diye sunmaz. | var |
| K9 | YZ ayrımı | Carbon AI etiketi, ayrı başlık, cümle başına sayfa atfı, kapatılabilir; modele kişisel veri gitmez. | var |
| K10 | Erişilebilirlik | WCAG 2.2 AA; axe + IBM Equal Access sıfır ihlal; PDF etiketli, yer imli, dil `tr`. | var |
| K11 | Ekran–kâğıt eşliği | Aynı bileşen, aynı sıra; etkileşimli öğenin durağan karşılığı (☐). | var |
| K12 | Güncellik | Damgalar her sayfada; tablo ya da kitap değişince "güncel değil". | var |

Kapılar: ekranda e2e (Playwright, axe, IBM Equal Access); PDF'te üretilen dosyanın kendisi (sayfa sayısı, yetim başlık, gömülü yazı tipi, etiket ağacı, yer imleri, metin araması ile K1 başlık doğrulaması).

## 7. Hata ve boş durumlar
- Kitap haritası yok/bozuk: kılavuz kitap bölümleri olmadan çıkar ve bunu açıkça yazar; ders sayfası "kitap bölümleri henüz eklenmedi".
- Tablonun öğretim yılı bitmiş: "Yeni yılın tabloları bekleniyor"; kılavuz üretilmez.
- Harita–tablo uyuşmazlığı (çıktı kitapta bulunamadı): blokta "kitapta karşılığı bulunamadı", "yok" değil.
- PDF: §5.3 yedek yolu; zaman aşımı ve eşzamanlılık sınırı aşımı açık ileti.
- YZ: bölüm yerine not; kılavuzun geri kalanı etkilenmez.
- İşaret yazılamadı: ekranda hata bildirimi, işaret geri alınır.

## 8. Riskler
| Risk | Karşılık |
|---|---|
| Din Kültürü 7 kitabı korpusta yok | EBA'da doğrudan aranır; bulunamazsa ders kitap bölümsüz çıkar ve kılavuz bunu yazar |
| Kitap PDF'i İçindekiler'i farklı dizer (ders başına) | Betik ders başına ayrıştırıcı ayarı taşır; yapı denetimi ve elle onay |
| Bölüm içi başlık çıkarımı gürültülü | Yalnız tanınan türler (etkinlik/bağlantı/kontrol/tanım/özet) + yazı boyu eşiği; onayda temizlenir |
| Paged.js bakımı yavaş | Sürüm sabit, depoda; yedek yol düz Chrome |
| Chrome süreci bellek/süre | Eşzamanlılık 1–2, zaman aşımı, önbellek |
| MEB tabloyu/kitabı sessizce değiştirir | sha256 damgaları, K12 "güncel değil" |
| 3 Kasım'a yetişme | 4–5. aşamalar önce Fen ile |

## 9. Testler
Betik: küçük PDF fikstürleriyle İçindekiler ve başlık ayrıştırma, yapı denetimi ret nedenleri. Haritalar: değişmezler (çıktı → bölüm, sayfa sırası, sınırlar). Model: beş senaryo durumu, olası kip, plan dağılımı, damgalar. API: yetki, 404, PDF içerik türü. Pano: birim (durum cümleleri, matris), e2e (ana sayfa, ders sayfası, kılavuz; klavye; axe + IBM Equal Access), görsel taban (bilinçli güncelleme). PDF: kanun kapıları (§6).

## 10. Aşamalar
1. Yoklama (§5.4) + kanun belgesinin ilk sürümü.
2. Kitap haritaları: betik + altı ders (Din Kültürü araştırması) + onay.
3. Kılavuz modeli + API + hazırlık işaretleri.
4. Yüzeyler (önce Fen): ana sayfa, ders sayfası, kılavuz ekranı, giriş noktaları.
5. PDF hattı (önce Fen): baskı görünümü, seçenek penceresi, önbellek.
6. YZ bölümleri: özet/ipucu, prova kâğıdı; ardından 4–5'in altı derse genişlemesi.

Her aşama ayrı incelenir ve kullanıcının açık onayıyla canlıya alınır.

## 11. Kapsam dışı
- 2. dönem tabloları (MEB yayımlayınca senaryo betiği ve haritalar yeniden koşulur).
- 7. sınıf dışındaki sınıflar.
- Prova kâğıdının sunucuda puanlanması (fotoğraf yüklenirse mevcut `calisma_degerlendir`).
- Kılavuzun e-postayla ya da bildirimle gönderilmesi.
