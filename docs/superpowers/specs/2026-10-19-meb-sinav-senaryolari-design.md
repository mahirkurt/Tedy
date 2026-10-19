# MEB konu-soru dağılım senaryoları — doğrulama ve örnek sınav

Tarih: 2026-10-19 · Durum: tasarım onaylandı (sohbette, üç bölüm), spec incelemede
İlgili: `docs/superpowers/specs/2026-10-16-sinav-tespiti-ve-uyari-design.md` (sınav tespiti; bu iş onun üstüne kurulur)

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
- **Yapı denetimi**, biri tutmazsa yazmayı reddeder ve nedenini söyler: başlık satırları ve sütun başlıkları bulunur; her çıktı kodu `^[A-ZÇĞİÖŞÜ]+(\.[A-ZÇĞİÖŞÜ]+)*\.7\.\d+(\.\d+)?$` biçiminde; her senaryolu sınavın en az bir senaryosu var; her senaryonun toplamı ≥ 1; aynı kod iki kez yok.
- Ağ yalnız bu betikte; senkron ve pano ağa çıkmaz. Elle koşulur; 2. dönem tabloları yayımlanınca yeni adresle yeniden koşulur (yeni dosya ya da yeni `donem` anahtarı — 2. dönem bu işin kapsamı dışında, bkz. §9).

## 3. Eşleştirici: `src/sinav_senaryo.py`

Saf işlevler; ağ ve dosya yazımı yok. Tablo dosyası bir kez okunur ve süreç içinde tutulur; okunamazsa `None` döner ve çağıran bunu bildirir (§6).

### 3.1 Sınav → tablo sütunu

- **Ders:** sınavın `ders`'i (zaten kanonik) tablo dosyasında yoksa blok yazılmaz.
- **Sınav no:** başlıktan, sırayla: `(\d)\s*\.\s*(\d)` (dönem.sınav — "1.1 Ara Değerlendirme"); "N. yazılı", "N. ortak (yazılı) sınav", "birinci/ikinci yazılı" (yalnız sınav no). Dönem başlıkta yoksa sınav tarihinden (`tarih` ya da `hafta`): Eylül–Ocak → 1, Şubat–Haziran → 2. Tarih de yoksa öğretim yılının bugünkü dönemi.
- **Tür:** yalnız `ortak_sinav`, `yazili`, `deneme` türleri ve `diger` türünde başlığı sınav no taşıyanlar; `kisa_sinav` ve `konu_tarama` hiç eşleştirilmez (MEB tablosu ortak yazılı içindir).
- Dönem tablo dosyasının `donem`'i değilse ya da sınav no çözülemezse **blok yazılmaz**: dayanak yokken tahmin yürütülmez ve kart bölümü çizilmez.

### 3.2 Duyurudaki senaryo

- Arama penceresi: sınavın her bulgusu için aday metninde alıntının başladığı yerden, alıntının sonundan sonraki ilk tarih ifadesine ya da 400 karaktere (hangisi önceyse) kadar. Aday metni tek bir bulgu verdiyse bütün metin.
- Kalıplar (Türkçe katlanmış metinde): `(\d{1,2})\s*\.?\s*senaryo`, `senaryo\s*(\d{1,2})\b`, `(birinci|ikinci|üçüncü|dördüncü|beşinci|altıncı|yedinci|sekizinci|dokuzuncu|onuncu)\s+senaryo`; "3. ve 4. senaryo", "3., 4. senaryolar" birden çok numara verir.
- Sonuç: numaralar (küçükten büyüğe, tekrarsız) ve eşleşen **cümle** (duyurunun kendi sözleri, ≤ 300 karakter) — "ağırlıklı" gibi nüans kartta kaybolmasın.
- Bir sınavın birden fazla kaynağı farklı numaralar verirse hepsi alınır; durum her numara için ayrı değerlendirilir (§3.4).

### 3.3 Konular ↔ çıktılar

Duyurudaki her konu için, sırayla:

1. Konuda bir çıktı kodu geçiyorsa (`FB.7.2.1`, `T.O.7.5`) o çıktı.
2. Türkçe katlanmış (`turkce_kucult_katla` ailesi), kod öneki atılmış metinlerde: biri ötekini içeriyorsa ya da içerik sözcüklerinin (≥ 3 harf, bağlaçsız) en az %60'ı ortaksa en yüksek ortaklıklı çıktı.
3. Çıktı bulunmazsa `konu` adı (Fen/Mat/Sosyal "Konu (İçerik Çerçevesi)") aynı kuralla; eşleşen konunun bütün çıktıları.
4. Hiçbiri: konu **eşleşmedi** olarak kalır. "Sınavda yok" denmez; "MEB tablosunda karşılığı bulunamadı" denir.

### 3.4 Durumlar

Sınav kaydına `senaryo` bloğu:

```json
{"durum": "dogrulandi", "ders": "Türkçe", "sinav_no": 1, "donem": 1,
 "anilan": [4], "cumle": "Sınavınızın içeriği, MEB konu soru dağılım tablosu 4. senaryo ağırlıklı olacaktır.",
 "senaryo": 4, "toplam": 7,
 "dagilim": [{"kod": "T.O.7.5", "metin": "…", "soru": 2, "duyuruda": true}, "…"],
 "eslesmeyen_konular": [], "senaryo_disi_konular": [],
 "adaylar": [], "senaryo_sayisi": 6, "meb_guncelleme": "2026-09-10T17:27"}
```

| Durum | Koşul |
|---|---|
| `dogrulandi` | duyuru N'yi anıyor, sütunda N var, eşleşen her konu N'nin dağılımında (konu yoksa da) |
| `kismen` | N var ama eşleşen konulardan en az biri N'de değil (`senaryo_disi_konular`) |
| `senaryo_yok` | duyuru N'yi anıyor, sütunda N yok (sütun senaryolu, `senaryo_sayisi` verilir) |
| `ulke_geneli` | sütun `ulke_geneli` (anılan numara varsa yine bu durum; `not` taşınır) |
| `belirtilmedi` | duyuru senaryo anmıyor; `adaylar` = eşleşen konuların hepsini içeren senaryolar (eşleşen konu yoksa boş) |

- Duyuru birden çok numara anıyorsa (`anilan` uzunluğu > 1) blok ilk geçerli numarayla kurulur, `anilan` hepsini taşır; kart "3. ve 4. senaryo" der, dağılım ilk geçerliyi gösterir ve asistan hangisini istediğini sorar.
- `eslesmeyen_konular`: tabloda hiç karşılığı bulunamayanlar (her durumda).
- Takvimden gelen sınavlarda aday metni yok: ancak `belirtilmedi` (aday listesiz) ya da `ulke_geneli` çıkabilir.

### 3.5 Tespite bağlanış

- `sinav_tespiti.birlestir` sınavları kurduktan sonra her kayda `senaryo` bloğu eklenir (tablo yoksa ya da sütun çözülemezse anahtar hiç yazılmaz). Bulguların aday metinleri bu adımda elde; ayrı bir ağ ya da model çağrısı yok.
- `senaryo` bloğu `icerik_surumu`'na **girmez**: bildirim davranışı değişmez (ne yeni "güncellendi" bildirimi ne sessizleşme).
- `sinavlar.json` `surum` 1'de kalır; blok isteğe bağlıdır, eski dosyalarda yoktur.
- Kuru koşu raporu (`--kuru`) her sınav için senaryo durumunu bir satırla yazar.

## 4. API

`/api/exams`, sınav kaydında blok varsa `senaryo` alanını (yukarıdaki biçimde, camelCase'e çevrilmeden — `konular`/`kaynaklar` gibi) ekler; yoksa alan `null`. Okuma anında hesap yok. Ek olarak `senaryoKaynagi`: `{"sayfa", "mebGuncelleme"}` (ODSGM adresi ve tarih), tablo dosyası okunabiliyorsa.

## 5. Kart (`SinavAyrintisi`)

Sınavlar ve İşler'deki sınav ayrıntısında, "Konular" ile "Kaynaklar" arasında **"MEB konu-soru dağılımı"** bölümü. Bugün'ün önizlemesine eklenmez (İ1). `senaryo` `null` ise bölüm çizilmez.

| Durum | Bölüm |
|---|---|
| `dogrulandi` | `CheckmarkFilled` + "Duyurudaki 4. senaryo MEB tablosunda var: 7 soru. Duyurudaki 2 konu bu senaryoda." |
| `kismen` | `WarningAltFilled` + aynı ilk cümle + "Şu konu 4. senaryoda yok: …" |
| `senaryo_yok` | `WarningAltFilled` + "Duyuru 7. senaryo diyor; MEB tablosunda bu sınav için 1–6 var." |
| `ulke_geneli` | "Bu sınav ülke genelinde ortak yapılır; senaryo yok." |
| `belirtilmedi` | "Duyuruda senaryo belirtilmedi · MEB tablosunda 5 senaryo var." + adaylar varsa "Duyurudaki konular 3. ve 4. senaryolarla uyumlu (TEDY'nin tahmini)." |

- `dogrulandi`/`kismen`: "Senaryonun N çıktısını göster" ghost düğme (`aria-expanded`, `aria-controls`), varsayılan kapalı. Liste satırı: "2 soru · T.O.7.5 Metnin yüzey anlamını belirleyebilme"; duyuruda geçen çıktılar gri `Tag` "duyuruda" taşır. Birden çok numara anıldıysa ilk cümle "Duyuru 3. ve 4. senaryo diyor; …".
- `eslesmeyen_konular` doluysa: "MEB tablosunda karşılığı bulunamayan konu: …".
- Bölüm sonu: "MEB tablosu" dış bağlantısı ("MEB, 10.09.2026") ve "Örnek sınav için asistana sor" ghost düğmesi (`asistanaSor({ tur: 'sinav', id })`, ödev penceresindeki yolla aynı; başlatıcı yoksa `/asistan?sayfa=sinavlar`).
- Kurallar: durum ikon + metin, renk değil; ikonların Türkçe adı (B44); yeni renk, gölge ya da hex yok; cümle düzeni (S38/B41); telefonda denetimler ≥ 44 px. Biçimlendirme saf işlev olarak `utils/sinavSenaryosu.ts`'te.

## 6. Asistan

### 6.1 `sinav_senaryosu` aracı

- **Girdi:** `sinav_id` (sabitlenmiş sınav ya da `sinavlar` aracının listesinden) **ya da** `ders` + `sinav_no` (1/2), isteğe bağlı `senaryo`.
- **Çıktı (model için gövde, ≤ 3.900 karakter):** başlık ("Türkçe · 7. sınıf · 1. Dönem 1. Ortak Yazılı · Senaryo 4 · 7 soru"), durum cümlesi, **kontrol listesi** ("Yazılacak dağılım: T.O.7.4 → 1 soru; T.O.7.5 → 2 soru; … Toplam 7."), duyuruda geçen/geçmeyen işaretleri; `belirtilmedi`'de adaylar, aday yoksa senaryoların bir satırlık özeti (senaryo → toplam, çıktı kodları).
- **Atıf:** tür `meb-tablo`, etiket "MEB konu-soru dağılım tablosu · Türkçe 7 · 1. yazılı", ODSGM bağlantısı ve güncelleme tarihi. `SourcePanel` için grup adı "MEB tabloları".
- **Bildirim koşulu:** `sinavlar` aracının bildirildiği her durumda (Genel ve dört öğretmen modu); tablo dosyası okunamazsa araç bildirilmez ve `health.json`'a not düşülür (`sinav_senaryo: "tablo okunamadı"`). `/v1` ve API anahtarları `sinavlar` ile aynı kurala tabidir.

### 6.2 İstem kuralı: örnek sınav

Taban istemde (önbellekli, tek blok) ve öğretmen becerilerinin "Araç kullanımı" bölümlerinde:

1. "örnek sınav", "deneme sınavı", "prova", "yazılıya hazırla" istendiğinde önce `sinav_senaryosu`.
2. **Yazılı kâğıdı:** soru sayısı senaryonun toplamı, her çıktıdan tam kontrol listesindeki kadar soru; her sorunun altında ölçtüğü çıktı (kod + kısa ad); MEB ortak yazılı biçimi, çoğu açık uçlu; öğretmen modunda o öğretmenin soru kalıpları. **Cevap anahtarı yazılmaz.**
3. Kâğıdın sonunda iki öneri: "Cevapları göster" (istenince anahtar ayrı mesajda) ve "Aynı konulardan hızlı alıştırma" (`alistirma_olustur`, aynı çıktılardan). Kâğıda yazılan cevabın fotoğrafı yüklenirse mevcut `calisma_degerlendir`.
4. Senaryo belli değilse: tek aday → onu kullanır ve söyler; 2–4 aday → `netlestir`; aday yok → hangi senaryoyu kullanacağını sorar (tek başına seçmez).
5. `senaryo_yok`/`ulke_geneli`: bunu açıkça söyler, senaryo uydurmaz; ülke genelinde ise duyurudaki konulara göre hazırlar ve bunun MEB senaryosu olmadığını belirtir.
6. Senaryonun ek çıktıları "öğretmen söyledi" diye değil, "MEB senaryosu ayrıca kapsıyor" diye sunulur.

### 6.3 Bilinen sınır

Kâğıdın dağılıma uyması istem ve kontrol listesiyle sağlanır; serbest metindeki soru sayısını sunucu denetlemez. `scripts/asistan_eval.py` altın sorularına iki vaka eklenir (Türkçe 4. senaryo örnek sınavı; senaryosuz bir sınav) — yalnız `--onayla` ile, elle ve ücretli koşar.

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
