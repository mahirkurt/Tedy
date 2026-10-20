# MEB konu-soru dağılım senaryoları — doğrulama ve örnek sınav

Tarih: 2026-10-19 · Durum: uygulandı (2026-10-20, dal `feat/sinav-senaryo`); tasarım sohbette üç bölüm hâlinde onaylanmıştı
İlgili: `docs/superpowers/specs/2026-10-16-sinav-tespiti-ve-uyari-design.md` (sınav tespiti; bu iş onun üstüne kurulur)

**Okuma notu (2026-10-20):** metin, yapılanı anlatır. Gerçek tablolar ve inceleme turları tasarımı değiştirdiği yerlerde satırlar yeniden yazıldı; gerekçesi ya da ölçümü olan değişiklikler "Uygulama kararı/kararları (2026-10-20)" ya da "Bilinen sınır" etiketiyle işaretlidir (§2.2, §3.1–§3.5, §4, §5, §6.1–§6.3).

## 0. Niyet

MEB ÖDSGM her dönem, ortak yazılı sınavlar için ders ve sınıf başına **konu-soru dağılım tabloları** yayımlar: bir sınavın hangi öğrenme çıktılarından kaçar soru içereceğini birkaç **senaryo** olarak verir; okul birini seçer. Öğretmenler duyurularında bunu anıyor ("Sınavınızın içeriği, MEB konu soru dağılım tablosu 4. senaryo ağırlıklı olacaktır").

Bu iş üç şey yapar, 7. sınıf ve 2026-2027 1. dönem için:

1. Altı dersin (Türkçe, Matematik, Fen Bilimleri, Sosyal Bilgiler, Din Kültürü ve Ahlak Bilgisi, İngilizce) senaryo tablolarını TEDY'ye alır.
2. Bir sınav duyurusu senaryo andığında bunu tabloyla **doğrular** ve sınav kartında gösterir: senaryo var mı, duyurudaki konular o senaryoda mı, senaryo duyurunun saymadığı hangi çıktıları da kapsıyor. Senaryo anılmadığında kart bunu söyler ve duyurudaki konularla uyumlu senaryoları **tahmin olarak** adlandırır.
3. Asistanın, senaryonun soru dağılımına uyan bir **örnek yazılı kâğıdı** ve ardından aynı çıktılardan bir alıştırma kartı üretmesini sağlar.

Kullanıcı kararları (2026-10-19, sohbette):

- Okulun "1.1" adı MEB'in "1. Dönem 1. Ortak Yazılı Sınav"ı, "1.2" "1. Dönem 2. Ortak Yazılı Sınav"ıdır.
- Örnek sınav: önce yazılı kâğıt, ardından aynı çıktılardan alıştırma kartı (ikisi birden).
- Senaryo anılmadığında kartta kısa not + konular eşleşiyorsa tahmin olarak etiketli uyumlu senaryolar.
- Mimari: eşleştirme tespit anında yapılır, sonuç sınav kaydına yazılır (okuma anında değil, yalnız asistanda değil).

## 1. Ölçülenler (2026-10-19)

- **Kaynak sayfa:** `https://odsgm.meb.gov.tr/www/1donem-konu-soru-dagilim-tablolari-2026-2027/icerik/1724` (yayın 07.09.2026, güncelleme 10.09.2026 17:27). Temel Eğitim için ders başına bir kısa bağlantı: Din Kültürü `meb.ai/ankmeb1`, Fen `ankmeb2`, Matematik `ankmeb3`, Türkçe `ankmeb4`, Sosyal `ankmeb5`, İngilizce `ankmeb6`.
- **Biçim:** her bağlantı bir LibreOffice HTML dışa aktarımı (`<meta name="generator" content="LibreOffice 7.4.7.2">`); sınıf başına bir `<table>` (5–8. sınıf, 4 tablo). Başlık satırları: ders adı ("7. SINIF FEN BİLİMLERİ DERSİ"), "1. DÖNEM ORTAK YAZILI SINAVLAR", "KONU SORU DAĞILIM TABLOSU", sütun başlıkları (Fen/Mat: "Ünite/Tema · Konu (İçerik Çerçevesi) · Öğrenme Çıktıları"; Türkçe: "Alan Becerileri · Öğrenme Çıktıları"), ardından "1. Dönem 1. Ortak Yazılı Sınav" / "1. Dönem 2. Ortak Yazılı Sınav" altında "Senaryo N" sütunları. Hücreler birleşik (`colspan`/`rowspan`); boş hücre = o senaryoda o çıktıdan soru yok.
- **Senaryo sayısı derse ve sınava göre değişir:** Fen 7: 1. yazılı 5, 2. yazılı 5. Türkçe 7: 1. yazılı 6; 2. yazılı senaryo değil, tek birleşik hücre: "1. Dönem 2. Ortak Yazılı Sınav Ülke Geneli Ortak Yazılı Sınav…".
- **Gerçek vaka:** Türkçe "1.1 Ara Değerlendirme Sınavı" (2026-10-22), duyuru "MEB konu soru dağılım tablosu 4. senaryo ağırlıklı", iki konu: "Metnin yüzey anlamını belirleyebilme", "Metinde geçen anlamını bilmediği söz varlığı unsurlarının anlamını tahmin edebilme". Tabloda Türkçe 7, 1. yazılı, Senaryo 4 = 7 soru: T.O.7.4 1, T.O.7.5 2, T.O.7.7 1, T.O.7.21 1, T.Y.7.18 1, T.Y.7.21 1. Duyurudaki iki konu T.O.7.5 ve T.O.7.4'tür; senaryonun öteki dört çıktısını duyuru saymıyor. Senaryo toplamları: 7, 6, 7, 7, 6, 6.
- **Ağ:** HP, mbp ve Pi'den (çıkış Türk Telekom, TR) `odsgm.meb.gov.tr`, `www.meb.gov.tr` ve `meb.ai`'ye TCP bağlanıyor, TLS el sıkışması takılıyor (TLS 1.2/1.3, küçük şifre listesi, HTTP/1.1 denendi). Okuma servisleri: Tavily metni düzleştiriyor ve boş hücreleri kaybediyor (sütun konumu çözülemez); WebFetch zaman aşımı; **Jina Reader** (`https://r.jina.ai/<url>`, `X-Return-Format: html`) ham HTML'i hücre ızgarasıyla birlikte veriyor (Fen 203 KB, Türkçe 433 KB, 1 sn).
- **Sınav kaydı:** `sinav_tespiti.gecerli_belge` yalnız `surum` ve `sinavlar` listesini denetler; isteğe bağlı yeni bir alan sürüm artırmadan eklenebilir. Tespit sırasında her bulgunun aday metni (`Bulgu.aday.metin`) ve alıntısı (`Bulgu.alinti`) elde.

## 2. Veri dosyası ve betik

### 2.1 `src/sinav_senaryolari.json`

Repoya girer, betik üretir, elle düzenlenmez. Biçim:

```json
{
  "surum": 1,
  "kaynak": {"sayfa": "<ODSGM adresi>", "baslik": "1. Dönem Konu Soru Dağılım Tabloları (2026-2027)",
             "meb_guncelleme": "2026-09-10T17:27", "alindi": "2026-10-19", "ogretim_yili": "2026-2027",
             "donem": 1, "sinif": 7},
  "dersler": {
    "Türkçe": {
      "adres": "https://meb.ai/ankmeb4", "sha256": "<indirilen HTML>",
      "ciktilar": [{"kod": "T.O.7.5", "metin": "Metnin yüzey anlamını belirleyebilme",
                    "alan": "OKUMA", "konu": null}],
      "sinavlar": {
        "1": {"tur": "senaryolu", "senaryolar": {"4": {"T.O.7.4": 1, "T.O.7.5": 2, "...": 1}}},
        "2": {"tur": "ulke_geneli", "not": "1. Dönem 2. Ortak Yazılı Sınav Ülke Geneli Ortak Yazılı Sınav…"}
      }
    }
  }
}
```

- Ders anahtarı `course_names.normalize_course`'un kanonik adıdır; tablo başlığındaki ad ("İLKÖĞRETİM MATEMATİK", "DİN KÜLTÜRÜ VE AHLAK BİLGİSİ") betikte buna eşlenir.
- `ciktilar` tablodaki her çıktıyı taşır (soru almayanlar dahil): eşleştirici duyurudaki konuyu senaryo dışı bir çıktıya da bağlayabilsin. `alan` Türkçe'nin "Alan Becerileri" sütunu, `konu` Fen/Mat/Sosyal'in "Konu (İçerik Çerçevesi)" sütunu; olmayan `null`.
- Senaryo yalnız soru alan çıktıları taşır (sayı ≥ 1).

### 2.2 `scripts/odsgm_senaryo_tablolari.py`

- Varsayılan: altı dersin adresini Jina Reader'dan HTML olarak alır. `--dosya DERS=yol` ile tarayıcıdan kaydedilmiş HTML'den okur (Jina erişilemezse). `--sinif` varsayılan 7.
- LibreOffice tablosunu `colspan`/`rowspan` çözerek ızgaraya çevirir (stdlib `html.parser`), başlığında "{sınıf}. SINIF" geçen tabloyu seçer.
- **Yapı denetimi**, biri tutmazsa yazmayı reddeder ve nedenini söyler: başlık satırları ve sütun başlıkları bulunur; her çıktı kodu aşağıdaki iki biçimden birinde ve istenen sınıfta; her senaryolu sınavın en az bir senaryosu var; her senaryonun toplamı ≥ 1; aynı kod iki kez yok; kodu okunamayan ve senaryo hücresi dolu satır yok.

**Uygulama kararları (2026-10-20) — gerçek tablolarda ölçülen biçimler.** Altı dersin tablosu aynı kalıpta değildi; betik şunları ayrıca karşılar:

- **Sınıf başlığı:** Din Kültürü ve Matematik'te "7.SINIF" (boşluksuz); Fen, Türkçe, Sosyal ve İngilizce'de "7. SINIF". Tablo `(?<!\d)7\.\s*SINIF` ile seçilir ("17. SINIF" sayılmaz).
- **Çıktı kodu iki biçimdedir:** `ÖNEK.sınıf.ünite[.sıra]` ("DKAB.7.1.1.", "T.O.7.5") ve İngilizce'nin bitişik biçimi `E7.<ünite>.<beceri harfi><n>` ("E7.1.R1"). İkincisi olduğu gibi tutulur. Sosyal'in bir satırı kodu nokta yerine boşlukla yazıyor ("SB 7.1.1."; kardeşleri "SB.7.1.2."): `SB.7.1.1` biçimine çevrilir. Kod sonundaki nokta atılır. Başka bir biçim okunamayan satırdır (aşağıya bak).
- **Unicode:** hücre metni NFC'ye normalize edilir; Türkçe tablosunda 9 hücre "ü"yü "u" + birleşik ünlem noktası olarak yazıyor; normalize edilmezse aynı harf iki farklı dizgi olarak kalır.
- **Kodsuz satır:** bölüm/ünite başlığı (senaryo hücreleri boş) ve "TOPLAM" altbilgisi atlanır. Kodsuz ama senaryo hücresinde sayı taşıyan başka bir satır, okunamayan bir çıktıdır ve sayıları sessizce düşerdi: **betik reddeder** ("kodu okunamayan satır"). Tek istisna "TOPLAM" satırıdır.
- Ağ yalnız bu betikte; senkron ve pano ağa çıkmaz. Elle koşulur; 2. dönem tabloları yayımlanınca yeni adresle yeniden koşulur (yeni dosya ya da yeni `donem` anahtarı — 2. dönem bu işin kapsamı dışında, bkz. §9).

## 3. Eşleştirici: `src/sinav_senaryo.py`

Saf işlevler; ağ ve dosya yazımı yok. Tablo dosyası `tablo_oku()` ile okunur (önbellek yok, her çağrıda yeniden); yok, bozuk ya da başka sürümdeyse `None` döner ve çağıran bunu bildirir (§6, §7).

### 3.1 Sınav → tablo sütunu

- **Ders:** sınavın `ders`'i (zaten kanonik) tablo dosyasında yoksa blok yazılmaz.
- **Sınav no:** başlıktan, sırayla: dönem.sınav çifti (`1.1`, `1.2`, `2.1`, `2.2` — "1.1 Ara Değerlendirme"; daha uzun bir sayının parçası olan "10.12" ya da "1.1.1" sayılmaz); "N. yazılı", "N. sınav", "N. ortak yazılı/sınav" (yalnız sınav no); "birinci/ikinci [ortak] yazılı/sınav". Dönem başlıkta yoksa ("N. dönem") sınav tarihinden (`tarih` ya da `hafta`): Eylül–Ocak → 1, Şubat–Haziran → 2 (Temmuz–Ağustos dönemsizdir, blok yazılmaz). Tarih de yoksa bugünün dönemi.
- **"N. yazılı / N. sınav" biçimi noktayı şart koşar:** "Tema 1 Sınavı", "1 Yazılı" ya da "Ünite 2 sınavı" sınav no değildir; yalnız 1 ve 2 numarası kabul edilir.
- **Tür:** yalnız `ortak_sinav`, `yazili`, `deneme` türleri ve `diger` türünde başlığı sınav no taşıyanlar; `kisa_sinav` ve `konu_tarama` hiç eşleştirilmez (MEB tablosu ortak yazılı içindir).
- Dönem tablo dosyasının `donem`'i değilse ya da sınav no çözülemezse **blok yazılmaz**: dayanak yokken tahmin yürütülmez ve kart bölümü çizilmez.
- **Bilinen sınır (2026-10-20):** sütun, kaydın `baslik` alanından çözülür. Takvim kaydında bu, portalın temizlenmiş başlığıdır ("Türkçe · 1. Dönem Yazılı"); ham başlıktaki "2. Ortak Yazılı" temizlikte düşer. Bu yüzden canlı takvimdeki ülke geneli Türkçe 2. yazılı (05.01.2027) bugün `ulke_geneli` bloğu almaz. Asistan aracı bundan etkilenmez (`ders` + `sinav_no` ile tabloya doğrudan bakar). Ham başlığı (`taban.rawTitle`) da okumak küçük bir ek olur; bu işe alınmadı.

### 3.2 Duyurudaki senaryo

- Arama penceresi (Türkçe **katlanmış** metinde): sınavın her bulgusu için aday metninde alıntının geçtiği yerden başlar ve alıntının sonundan sonraki ilk **sınıra** ya da alıntı sonu + 400 karaktere (hangisi önceyse) kadar sürer. Sınır, başka bir tarih ifadesi (gün + ay adı ve ekleri: "22 Ekim", "22 Ekim'de"; `dd.mm`; `dd.mm.yyyy`) ya da başka bir sınav numarasıdır (`1.1` gibi dönem.sınav çifti ya da "N. yazılı / N. sınav"). Başka sınavın senaryo cümlesi bu sınava yazılmasın diye.
- **Tek bulgulu metin bütün olarak aranmaz.** Pencere her durumda alıntıdan başlar; alıntı katlanmış metinde bulunamazsa ve metin tek bulgu verdiyse bütün metin yedek olarak aranır, çok bulgulu metinde yalnız alıntının kendisi.
- Kalıplar (katlanmış metinde, yalnız pencerede): "senaryo"dan önce gelen sayı **yalnız noktalı sıra sayısı** olarak sayılır ("4. senaryo", "3., 4. senaryolar", "3. ve 4. senaryo"); "senaryo"dan sonra gelen sayı yalnız bitişik "senaryo N" biçimindedir. Sözcükle yazılan sıra sayıları (birinci … onuncu + "senaryo") sayılır. **Adet bildiren sayılar sayılmaz:** "senaryoda 3 soru", "6 senaryodan birine", "6 senaryo". Numara aralığı 1–10.
- Sonuç: numaralar (küçükten büyüğe, tekrarsız) ve eşleşen **cümle** (duyurunun kendi sözleri, ≤ 300 karakter) — "ağırlıklı" gibi nüans kartta kaybolmasın.
- Bir sınavın birden fazla kaynağı farklı numaralar verirse hepsi alınır; durum her numara için ayrı değerlendirilir (§3.4).

### 3.3 Konular ↔ çıktılar

**Uygulama kararı (2026-10-20):** ilk taslaktaki "önce çıktı, bulunmazsa konu adı" sırası, çıktının tam ifadesini taşıyan bir konuyu bütün konu grubuna genişletiyordu. Sıra şudur; puan, katlanmış ve kod öneki atılmış iki metnin ortak içerik sözcüklerinden (≥ 3 harf, ilk 5 harf, bağlaçsız) Dice katsayısıdır; biri ötekini içeriyorsa (en az 10 karakter) 1.0:

Duyurudaki her konu için, sırayla:

1. Konuda bir çıktı kodu geçiyorsa (`FB.7.2.1`, `T.O.7.5`) o çıktı(lar).
2. Konu, bir ya da birkaç çıktının **tam ifadesini içeriyorsa** (kod öneki atılmış, en az 10 karakter) yalnız o çıktılar **birebir** döner; konu grubuna genişletilmez.
3. Konu adı ("Konu (İçerik Çerçevesi)", Fen/Mat/Sosyal) puanı ≥ 0,6 **ve** en iyi çıktı puanından düşük değilse konunun bütün çıktıları (eşit puanlı konu adlarının hepsi).
4. Aksi hâlde en iyi çıktı puanı ≥ 0,6 ise o puanda **eşit olan bütün** çıktılar.
5. Hiçbiri: konu **eşleşmedi** olarak kalır. "Sınavda yok" denmez; "MEB tablosunda karşılığı bulunamadı" denir.

### 3.4 Durumlar

Sınav kaydına `senaryo` bloğu:

```json
{"durum": "dogrulandi", "ders": "Türkçe", "sinav_no": 1, "donem": 1,
 "anilan": [4], "cumle": "Sınavınızın içeriği, MEB konu soru dağılım tablosu 4. senaryo ağırlıklı olacaktır.",
 "senaryo": 4, "toplam": 7,
 "dagilim": [{"kod": "T.O.7.5", "metin": "…", "soru": 2, "duyuruda": true}, "…"],
 "eslesen_konu_sayisi": 2, "eslesmeyen_konular": [], "senaryo_disi_konular": [],
 "adaylar": [], "senaryo_sayisi": 6,
 "kaynak": "https://odsgm.meb.gov.tr/www/1donem-konu-soru-dagilim-tablolari-2026-2027/icerik/1724",
 "meb_guncelleme": "2026-09-10T17:27"}
```

| Durum | Koşul |
|---|---|
| `dogrulandi` | duyuru N'yi anıyor, sütunda N var, eşleşen her konu N'nin dağılımında (konu yoksa da) |
| `kismen` | N var ama eşleşen konulardan en az biri N'de değil (`senaryo_disi_konular`) |
| `senaryo_yok` | duyuru N'yi anıyor, sütunda N yok (sütun senaryolu, `senaryo_sayisi` verilir) |
| `ulke_geneli` | sütun `ulke_geneli` (anılan numara varsa yine bu durum; `not` taşınır) |
| `belirtilmedi` | duyuru senaryo anmıyor; `adaylar` = eşleşen konuların hepsini içeren senaryolar (eşleşen konu yoksa boş) |

- **Duyuru birden çok numara anıyorsa** (`anilan` uzunluğu > 1) blok **ilk geçerli** numarayla (sütunda var olan) kurulur; `anilan` hepsini taşır; `cumle` bu numarayı anan cümledir. Kart "Duyuru 3. ve 4. senaryo diyor; …" der ve dağılım ilk geçerliyi gösterir. `ozet` ve asistan aracının gövdesi **bütün numaraları adıyla** yazar ve aracın gövdesi asistana örnek sınav yazmadan önce hangisinin istendiğini sormasını söyler.
- `eslesmeyen_konular`: tabloda hiç karşılığı bulunamayanlar (her durumda). `eslesen_konu_sayisi`: tabloda karşılığı bulunan konu sayısı (kart "Duyurudaki N konu bu senaryoda" derken kullanır). `ulke_geneli` bloğu ayrıca `not` taşır.
- Takvimden gelen sınavlarda aday metni yok: ancak `belirtilmedi` (aday listesiz) ya da `ulke_geneli` çıkabilir (sütun çözümü için §3.1 "Bilinen sınır").

### 3.5 Tespite bağlanış

- `sinav_tespiti.birlestir` sınavları kurduktan sonra her kayda `senaryo` bloğu eklenir (tablo yoksa ya da sütun çözülemezse anahtar hiç yazılmaz). Bulguların aday metinleri bu adımda elde; ayrı bir ağ ya da model çağrısı yok.
- `senaryo` bloğu `icerik_surumu`'na **girmez**: bildirim davranışı değişmez (ne yeni "güncellendi" bildirimi ne sessizleşme).
- `sinavlar.json` `surum` 1'de kalır; blok isteğe bağlıdır, eski dosyalarda yoktur.
- Kuru koşu raporu (`--kuru`) bloğu olan her sınav için bir `Senaryo:` satırı yazar (durum · ders ve sınav no · senaryo ve soru sayısı, belirtilmediyse uyumlu adaylar).

## 4. API

`/api/exams`, sınav kaydında blok varsa `senaryo` alanını (yukarıdaki biçimde, camelCase'e çevrilmeden — `konular`/`kaynaklar` gibi) ekler; yoksa alan `null` (`sinavlar.json` yokken düşülen takvim hesabında da `null`). Okuma anında hesap yok.

**Uygulama kararı (2026-10-20):** üst düzeyde `senaryoKaynagi` alanı **yoktur**. Blok kendi kaynağını taşır: `kaynak` (ÖDSGM sayfa adresi) ve `meb_guncelleme` (ISO tarih-saat). Kart dış bağlantıyı ve "MEB, 10.09.2026" tarihini bloktan kurar; bu sayede tablo dosyasının sonradan güncellenmesi, eski sınav kaydının gösterdiği kaynağı değiştirmez.

## 5. Kart (`SinavAyrintisi`)

**Uygulama kararları (2026-10-20):** bölüm yalnız **Sınavlar** sayfasındaki sınav ayrıntısında (`SinavAyrintisi`, `ExamTimeline` içinde) çizilir; İşler sınav satırından Sınavlar'a bağlanır ve ayrıntıyı kendisi çizmez, Bugün'ün önizlemesine de eklenmez (İ1). Dış bağlantı Carbon'un `Launch` ikonunu taşır (B58: sayfadan çıkan bağlantı bunu söyler). Telefonda (< 672 px) bölümün düğmeleri ≥ 44 px olur: Carbon'un yoğunluk değişkeni `--cds-layout-size-height-min` bölümün **düğmelerine** verilir (dolguyu da boyutlar, etiket ortada kalır; `min-block-size` etiketi üste yapıştırırdı), bölüme verilmez çünkü "duyuruda" `Tag`'ı aynı değişkeni okuyup 48 px'e büyüyordu. Bağlantı Carbon düzen bileşeni olmadığı için kendi `min-block-size` kuralını alır.

"Konular" ile "Kaynaklar" arasında **"MEB konu-soru dağılımı"** bölümü. `senaryo` `null` ise bölüm çizilmez.

| Durum | Bölüm |
|---|---|
| `dogrulandi` | `CheckmarkFilled` + "Duyurudaki 4. senaryo MEB tablosunda var: 7 soru. Duyurudaki 2 konu bu senaryoda." |
| `kismen` | `WarningAltFilled` + aynı ilk cümle + "Şu konu 4. senaryoda yok: …" |
| `senaryo_yok` | `WarningAltFilled` + "Duyuru 7. senaryo diyor; MEB tablosunda bu sınav için 1–6 var." |
| `ulke_geneli` | "Bu sınav ülke genelinde ortak yapılır; senaryo yok." |
| `belirtilmedi` | "Duyuruda senaryo belirtilmedi · MEB tablosunda 5 senaryo var." + adaylar varsa "Duyurudaki konular 3. ve 4. senaryolarla uyumlu (TEDY'nin tahmini)." |

- `dogrulandi`/`kismen`: "Senaryonun N çıktısını göster" ghost düğme (`aria-expanded`, `aria-controls`), varsayılan kapalı. Liste satırı: "2 soru · T.O.7.5 Metnin yüzey anlamını belirleyebilme"; duyuruda geçen çıktılar gri `Tag` "duyuruda" taşır. Birden çok numara anıldıysa ilk cümle "Duyuru 3. ve 4. senaryo diyor; …".
- `eslesmeyen_konular` doluysa: "MEB tablosunda karşılığı bulunamayan konu: …".
- Bölüm sonu: "MEB tablosu" dış bağlantısı (`Launch` ikonlu; "MEB tablosu (MEB, 10.09.2026)", adres bloğun `kaynak`ı, tarih `meb_guncelleme`) ve "Örnek sınav için asistana sor" ghost düğmesi (`asistanaSor({ tur: 'sinav', id })`, ödev penceresindeki yolla aynı; başlatıcı yoksa `/asistan?sayfa=sinavlar`).
- Kurallar: durum ikon + metin, renk değil; ikonların Türkçe adı (B44); yeni renk, gölge ya da hex yok; cümle düzeni (S38/B41); telefonda denetimler ≥ 44 px. Biçimlendirme saf işlev olarak `utils/sinavSenaryosu.ts`'te.

## 6. Asistan

### 6.1 `sinav_senaryosu` aracı

**Uygulama kararları (2026-10-20):**

- **Girdi `ders` + `sinav_no` (1/2) + isteğe bağlı `senaryo`'dur; `sinav_id` yoktur.** Model sınav kimliklerini hiç görmez (`sinavlar` aracı kimlik yazmaz); araç, derse (ve verildiyse sınav no'ya) uyan yaklaşan sınavı listeden kendisi bulur. `ders` kanonik ada çevrilir ("Fen" → Fen Bilimleri); tabloda olmayan ders kısa bir araç hatasıdır.
- `sinav_no` ve `senaryo` **tam sayıya çevrilir** (bir JSON araç çağrısı "1" gönderebilir; çevrilemeyen değer "bir tam sayı olmalı" hatasıdır).
- **Beklenmedik bir istisna cevabı düşürmez:** bozuk bir sınav bloğu gibi durumlarda araç **kısa bir araç hatası** ("MEB senaryo bilgisi okunamadı") döner, ayrıntı günlüğe yazılır; model hatayı görür ve cevabı yine yazar.
- **Sapma (kayıtlı):** atıf ÖDSGM adresini taşımaz. `SourcePanel` atıfların `locator` adreslerini çizmez; adrese bağlantıyı Sınavlar kartı verir (§5).

- **Çıktı (model için gövde, ≤ 3.900 karakter):** başlık ("Türkçe · 7. sınıf · 1. Dönem 1. Ortak Yazılı (MEB konu-soru dağılım tablosu, güncelleme 10.09.2026)"); yaklaşan sınav varsa onun adı ve tarihi, durum cümlesi (`ozet`), duyurunun cümlesi ve tabloda karşılığı bulunamayan konular; seçilen senaryo için **kontrol listesi** ("Senaryo 4 · 7 soru. Yazılacak dağılım: - T.O.7.4 → 1 soru · … (duyuruda) … Toplam 7 soru."); senaryo belli değilse `belirtilmedi`'de uyumlu adaylar (tahmin) ve her senaryonun bir satırlık özeti (senaryo → toplam, çıktı kodları); ülke genelinde ortak sınavda senaryo ve soru sayısı olmadığı, uydurulmaması gerektiği. **Duyuru birden çok senaryo anıyorsa** gövde bütün numaraları yazar ve örnek sınav yazmadan önce hangisinin istendiğinin sorulmasını söyler (§3.4).
- **Atıf:** tür `meb-tablo`, etiket "MEB konu-soru dağılım tablosu · Türkçe 7 · 1. yazılı", `locator` `{tool, args}`; ÖDSGM bağlantısı yok (yukarıdaki sapma), güncelleme tarihi gövdenin başlık satırında. `SourcePanel` için grup adı "MEB tabloları".
- **Bildirim koşulu:** `sinavlar` aracının bildirildiği her durumda (Genel ve dört öğretmen modu); tablo dosyası okunamazsa araç bildirilmez ve tespit `sinavlar.json` özetinin `hatalar` listesine "senaryo tablosu okunamadı" yazar (§7). `/v1` ve API anahtarları `sinavlar` ile aynı kurala tabidir. `sinavlar` aracı, bloğu olan her yaklaşan sınavın altına "MEB senaryosu: <özet> — ayrıntı için sinav_senaryosu" satırı ekler.

### 6.2 İstem kuralı: örnek sınav

Taban istemde (önbellekli, tek blok; "## Örnek sınav" bölümü) ve öğretmen becerilerinin "Araç kullanımı" bölümlerinde ("Yazılı provası" maddesi, genel istemin kuralına gönderir):

1. "örnek sınav", "deneme sınavı", "prova", "yazılıya hazırla" istendiğinde önce `sinav_senaryosu`.
2. **Yazılı kâğıdı:** soru sayısı senaryonun toplamı, her çıktıdan tam kontrol listesindeki kadar soru; her sorunun altında ölçtüğü çıktı (kod + kısa ad); MEB ortak yazılı biçimi, çoğu açık uçlu; öğretmen modunda o öğretmenin soru kalıpları. **Cevap anahtarı yazılmaz.**
3. Kâğıdın sonunda iki öneri: "Cevapları göster" (istenince anahtar ayrı mesajda) ve "Aynı konulardan hızlı alıştırma" (`alistirma_olustur`, aynı çıktılardan). Kâğıda yazılan cevabın fotoğrafı yüklenirse mevcut `calisma_degerlendir`.
4. Senaryo belli değilse: tek aday → onu kullanır ve söyler; 2–4 aday → `netlestir`; aday yok → hangi senaryoyu kullanacağını sorar (tek başına seçmez).
5. `senaryo_yok`/`ulke_geneli`: bunu açıkça söyler, senaryo uydurmaz. **Ülke genelinde ortak sınavda** (MEB senaryo vermez; soru sayısı ve dağılımı yoktur) örnek sınavı **duyurudaki konulardan** hazırlar, duyuru konu vermiyorsa **dersin güncel ünitesinden**, ve bunun bir MEB senaryosu olmadığını okura açıkça söyler.
6. Senaryonun ek çıktıları "öğretmen söyledi" diye değil, "MEB senaryosu ayrıca kapsıyor" diye sunulur.
7. **Cevap anahtarı yasağından muaf tutulur.** Dört öğretmen becerisinin (Türkçe, Fen Bilimleri, Sosyal Bilgiler, Matematik) "Sınırlar" bölümü "bir test sayfasının cevap anahtarını üretmezsin" der; bu yasak asistanın **kendi hazırladığı örnek sınavın** (yazılı provasının) cevap anahtarını kapsamaz, o anahtar istenince ayrı bir mesajda verilir. Muafiyet satırda yazılıdır; yoksa beceri, taban istemin "Cevapları göster" önerisiyle çelişirdi. Ödev ve harici test sayfaları için yasak aynen sürer.

### 6.3 Bilinen sınır

Kâğıdın dağılıma uyması istem ve kontrol listesiyle sağlanır; serbest metindeki soru sayısını sunucu denetlemez. `scripts/asistan_eval.py` altın sorularına iki vaka eklendi: `turkce-4` ("Türkçe 1. yazılı için 4. senaryoya uygun örnek sınav hazırla", araç `sinav_senaryosu`, kaynak "MEB konu-soru", nokta `T.O.7.5`) ve `fen-4` ("Fen Bilimleri 1. yazılı için örnek sınav hazırla", senaryo belirtmeyen vaka, nokta "senaryo"). Altın soru sayısı 12 → 14; şema testi ders başına `>= 3` soruya ve `sinav_senaryosu` aracına izin verir. Koşu yalnız `--onayla` ile, elle ve ücretlidir; bu iş sırasında koşulmadı.

### 6.4 Arayüz

`asistan/olayEslemesi.ts` `ARAC_ETIKETI`: `sinav_senaryosu` → "MEB senaryo tablosuna bakılıyor" (`tests/test_asistan_adim_etiketleri.py` zorunlu kılar). Yeni kart arayüzü yok.

## 7. Hata ve boş durumlar

- Tablo dosyası yok/bozuk: tespit `senaryo` yazmaz, `sinav_tespiti` özeti `hatalar`'a "senaryo tablosu okunamadı" ekler; kart bölümü çizilmez; araç bildirilmez. Sessiz düşüş yok.
- Duyurudaki numara tabloda yok: `senaryo_yok`, kart ve asistan bunu söyler.
- Konu eşleşmedi: "karşılığı bulunamadı" — "yok" değil.
- Betik yapı denetimini geçemezse dosya yazılmaz, eski dosya kalır.

## 8. Testler

- **Betik:** küçük, elle yazılmış bir LibreOffice biçimli HTML fikstürüyle (birleşik hücreler, boş hücreler, ülke geneli birleşik sütunu) ızgara ve yapı denetimi; ret nedenleri.
- **Veri dosyası:** yapı değişmezleri (kod biçimi, toplam ≥ 1, ders anahtarları kanonik) ve ölçülmüş gerçekler kapı olarak: Türkçe 1. yazılı Senaryo 4 = 7 soru, T.O.7.5 = 2; Türkçe 2. yazılı `ulke_geneli`; Fen 1. yazılı 5 senaryo, FB.7.2.1 S1 = 3.
- **Eşleştirici:** sütun çözümü (1.1/1.2, "2. yazılı", tarihten dönem, `kisa_sinav` hariç), senaryo kalıpları (sayı, sözcük, çoklu, pencere dışı başka sınavın senaryosu alınmaz), konu eşleşmesi (kod, metin, konu adı, eşleşmeme), beş durum; gerçek Türkçe vakası uçtan uca `dogrulandi`.
- **Tespit:** blok `icerik_surumu`'nu değiştirmez; tablo yokken anahtar yazılmaz ve `hatalar`'a not düşer.
- **API:** alan geçişi, `null`.
- **Pano:** `utils/sinavSenaryosu.ts` birim testleri (beş durumun cümleleri); e2e: beş durum, liste klavyeyle açılıp kapanır, "Asistana sor" sınavı sabitler, axe + IBM; Sınavlar görsel tabanı bilinçli güncellenir.
- **Asistan:** araç gövdesi (durumlar, kontrol listesi, bütçe), mod bildirimleri, istem yönlendirme testi (her araç tam bir kez), tablo yokken araç bildirilmez, adım etiketi.

## 9. Kapsam dışı

- 2. dönem tabloları (yayımlanınca betik yeniden koşulur; dönem anahtarı tasarımı o zaman).
- 7. sınıf dışındaki sınıflar ve ortaöğretim.
- Kâğıttaki soru sayısının sunucuda denetimi (§6.3).
- MEB sitesine bu makineden erişim sorunu (§1, ayrı iş).
- Bildirimlere senaryo bilgisi eklemek.

## 10. Riskler

| Risk | Karşılık |
|---|---|
| Jina Reader kapanır/değişir | `--dosya` ile tarayıcıdan kaydedilmiş HTML; veri dosyası repoda, senkron ona bağlı değil |
| MEB tabloyu dönem içinde günceller | `meb_guncelleme` kartta görünür; betik yeniden koşulunca sha256 değişir ve diff okunur |
| Öğretmen senaryoyu tablo dışı bir anlamda kullanır ("ağırlıklı") | Kart duyurunun cümlesini aynen taşır; doğrulama "senaryo var ve konular içinde" der, "sınav tam olarak budur" demez |
| Konu metni eşleşmesi yanlış pozitif | Kod önce; metinde %60 eşiği ve en yüksek ortaklık; eşleşmeyen konu açıkça listelenir |
| Başka sınavın senaryo cümlesi bu sınava yazılır | Alıntıdan başlayan, sonraki tarihte biten pencere; test edilir |
