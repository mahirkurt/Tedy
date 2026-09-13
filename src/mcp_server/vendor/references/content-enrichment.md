# İçerik Zenginleştirme — Entegre Edilebilir Kaynaklar ve Lisans Sınırları

> Bu referans, `carbon-edupedia` modüllerine **derleme anında (build-time)** hangi dış
> içerik kaynaklarının/tekniklerinin gömülebileceğini (*bakeable*) ve hangilerinin —
> lisans veya çalışma-zamanı (runtime) bağımlılığı yüzünden — gömülemeyeceğini
> tanımlar. Amaç, skill'in dış kaynak vaadini **dürüst** tutmaktır: bir entegrasyon
> burada "yapılamaz" olarak işaretliyse, modül onu iddia etmez veya taklit etmez
> (over-promise yasak).
>
> **Temel ilke:** Bir kaynağın lisans olarak *bakeable* olması onu otomatik meşru
> kılmaz. Çekilen her olgu yine `SKILL.md §7` kaynak-sadakati kuralına — özellikle
> Müfredat MCP tabanlı modüllerde kazanım metnine — **uzlaştırılmalıdır**
> (no-fabrication). Bu belge, içerik üreten skill'in kendisi ve içerik/lisans
> denetimi yapan herhangi bir gelecek aracın (ör. bir denetim ajanı) başvuracağı
> normatif kaynaktır.

## 1. Amaç ve self-contained kısıt

`carbon-edupedia` çıktısı **tek dosya, çevrimdışı** bir HTML modülüdür: `file://`
üzerinden doğrudan çift-tıkla açılabilir, kaydedildikten sonra hiçbir yerel harici
dosyaya veya çalışma-zamanı ağ isteğine bağımlı değildir (`G-SELFCONTAINED`,
`SKILL.md §12`). Bu, içerik zenginleştirme için **sert bir sınır** çizer:

- **"Entegre edilebilir" = yalnızca yazım/derleme anında.** Skill bir modül
  üretirken (yani *şimdi*, siz bu belgeyi okurken) bir kaynaktan veri/görsel
  çekip bunu modülün içine **donmuş (statik)** biçimde yerleştirebilir —
  `MODULE_DATA` sabiti, satır-içi SVG/PNG, native bir HTML düğümü (`<math>`)
  olarak. Kullanıcı modülü **açtığında** (runtime) o kaynağa bir daha **asla**
  erişilmez.
- **Runtime ağ isteği gerektiren hiçbir şey entegre edilemez** — canlı API
  çağrısı, `iframe` gömme, CDN'den çekilen etkileşimli widget/applet — kaynağın
  lisansı ne olursa olsun bu skill'in çıktı sözleşmesini ihlal eder. Böyle bir
  kaynak en iyi ihtimalle **bağlantı/atıf** olarak sunulur, gömülmez.
- **Artifact önizlemesiyle karıştırılmamalı.** `SKILL.md §14`, Claude artifact
  önizlemesinde `localStorage`/`sessionStorage` yerine opsiyonel bir
  `window.storage` API'sinden söz eder — bu, Claude'un kendi sanal alanına özgü
  ayrı bir mekanizmadır. Bu belgedeki kısıtlar (özellikle §2.4), kullanıcının
  **indirip kendi tarayıcısında** açtığı bağımsız tek-dosya çıktıyı konu alır;
  ikisi farklı çalışma yüzeyleridir ve birbirinin yerine geçmez.
- **Lisans uygunluğu ≠ pedagojik/kaynak-sadakati uygunluğu.** Bir kaynağın
  burada "entegre edilebilir" işaretli olması yalnızca **telif** açısından
  güvenli olduğu anlamına gelir. Olgunun modüle girmesi yine `SKILL.md §7`'nin
  onayından geçer: kazanım metniyle çelişmemeli, onu **tamamlamalı**, ve
  yerleşik bilgi kullanıldığında olduğu gibi etiketlenmelidir.

## 2. Entegre edilebilir kaynaklar ve teknikler

| Kaynak / Teknik | Lisans / Durum | Build-zamanı entegrasyon | Zorunlu kısıt |
|---|---|---|---|
| Wikidata olgu-çipleri | **CC0** (kamu malına eşdeğer, atıf gerekmez) | Derleme anında sorgulanır → sonuç `MODULE_DATA`'ya donmuş değer olarak yazılır | QID + çekim tarihi provenans; kazanım metnine **uzlaştırma zorunlu** (no-fabrication) |
| Wikimedia Commons görseli | Karışık: PD / CC BY / CC BY-SA (dosya bazında değişir) | Yalnız **PD veya CC BY** dosyalar statik gömülür (inline SVG/PNG) | **CC BY-SA'dan kaçının**; atıf satırı zorunlu; seyrek kullanım, Tier-1 yazar-SVG doktrini birincil kalır |
| Native MathML | Yok — tarayıcı-yerli özellik | `<math>` düğümü doğrudan HTML'e yazılır | Sıfır JS/font/payload; yalnız `mathExpr` yetersiz kaldığında tamamlayıcı |
| Çapraz-oturum aralıklı tekrar (spaced-rep) | Yok — istemci-taraf teknik, telif konusu değil | Leitner/kutu durumu modül-başına anahtarla `localStorage`'a yazılır | `localStorage` bazı `file://` kökenlerinde tutarsız/bloklu → **feature-detect + zarif düşüş** zorunlu; **IndexedDB kullanılmaz** |

### 2.1 Wikidata — CC0 olgu-çipleri
Wikidata'nın verisi [CC0 (kamu malına eşdeğer)](https://www.wikidata.org/wiki/Wikidata:Licensing)
lisanslıdır — yeniden kullanım için atıf **gerekmez** (yine de iyi pratik olarak
QID kaynak damgasına eklenir). Bu, Wikidata'yı yalnızca **atomik olgular** için
uygun kılar: tarih, miktar gibi kesin/sayısal değerler — uzun editoryal veya
anlatı metni için değil (zaten Wikidata öyle bir kaynak sunmaz).

Akış: derleme anında build-zamanı SPARQL sorgusu ile ilgili varlık sorgulanır → dönen değer `MODULE_DATA`'ya
**donmuş** biçimde yazılır (çalışma anında bir daha Wikidata'ya gidilmez) →
kaynak damgasına **QID + çekim tarihi** eklenir. Kritik sınır: Wikidata olgusu,
**Maarif kazanım metnine veya kullanıcı kaynağına uzlaştırılmalıdır** —
çelişiyorsa ya da konu dışıysa kullanılmaz (`SKILL.md §7`). Wikidata burada
yalnızca bir **doğrulama/zenginleştirme katmanıdır**, MEB kazanımının veya
kullanıcı kaynağının yerine geçmez.

### 2.2 Wikimedia Commons — PD / CC BY görsel
Commons'taki her dosyanın lisansı **dosya bazında** değişir — PD, CC BY, CC BY-SA
ve bazen daha kısıtlı olabilir; "Commons'taki her şey serbesttir" varsayımı
**yanlıştır** ([Commons: Reusing content outside Wikimedia](https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia)).
Yalnız **PD veya CC BY** etiketli dosyalar seçilip statik olarak (inline SVG
veya base64 PNG) gömülür.

**CC BY-SA'dan kaçının.** ShareAlike copyleft'tir: türetilmiş eser (bu modül)
de aynı lisans altına girmek zorunda kalır — bu, tek bir görsel yüzünden
**tüm modülü CC BY-SA'ya sürükler**, ki bu istenen bir sonuç değildir.
Kullanılan her CC BY görsel için atıf satırı (yazar + lisans + kaynak URL)
görselin hemen yanına eklenir. Kullanım **seyrek** kalmalı: bu skill'in
birincil ve **garantili** görsel-dayanak yolu her zaman yazar-üretimli
tema-duyarlı SVG'dir (`svg-authoring.md` Tier-1 doktrini) — Wikimedia yalnız
SVG ile ifade edilemeyen belgesel/fotoğrafik durumlarda tamamlayıcı olarak
düşünülür.

### 2.3 Native MathML
`mathExpr` yetersiz kaldığı (karmaşık kesir, kök, toplam/entegral gösterimi
gerektiren) durumlarda inline `<math>…</math>` (MathML) kullanılabilir.
Tarayıcı-yerlidir — `SKILL.md §14`'teki desteklenen sürümlerde (Chromium ≥120,
Firefox ≥115, Safari ≥16) harici kütüphane, font veya JS gerekmeden render
edilir → **sıfır ek payload**. Render kalitesi tarayıcıya göre küçük farklar
gösterebilir; bu yüzden `mathExpr` **varsayılan** kalır, MathML yalnız onun
yetersiz kaldığı ileri-notasyon durumlarında tamamlayıcıdır.

### 2.4 Çapraz-oturum aralıklı tekrar — veri modeli
`flashcards` segmentinin bugünkü aralıklı tekrarı **oturum-içidir** (deste
sonunda zor kartlar yeniden gösterilir; `interaction-patterns.md §3`).
**Çapraz-oturum** kalıcılık (kullanıcı modülü kapatıp ertesi gün kaldığı yerden
devam ettiğinde) için Leitner-benzeri kutu durumu, modül-başına bir anahtarla
tarayıcının `localStorage`'ına yazılabilir. Bu bir **telif** meselesi değil,
bir **saklama/dayanıklılık** meselesidir — bu yüzden burada teknik kısıt olarak
ele alınır, lisans tablosunda değil.

**Zorunlu saklama kısıtı:**
- `localStorage`, bazı `file://` kökenlerinde (tarayıcıya/güvenlik profiline
  göre değişir) tutarsız veya tamamen bloklu olabilir → erişim
  **feature-detect** edilmeli (`try/catch` ile yaz/oku denenir) ve
  engellenirse **sessizce** oturum-içi tekrara geri düşülmelidir — kullanıcıya
  hata gösterilmez.
- **IndexedDB kullanılmaz.** `file://` kökeninde IndexedDB, `localStorage`'dan
  bile daha güvenilmez biçimde bloklanır; bu yüzden kalıcılık katmanı yalnız
  `localStorage` + feature-detect ile sınırlı tutulur.
- Bu veri modelinin motor tarafındaki tam şeması (kutu geçişleri, anahtar
  biçimi) ileride motor/şema çalışmasında somutlaşacaktır; burada normatif olan
  yalnızca **lisans-dışılık + saklama kısıtı**dır.

## 3. Entegre edilemez — dürüst liste

Aşağıdaki kaynaklar **cazip görünür ama gömülemez** — ya lisansları (NC/SA/ND)
ya da mimarileri (runtime bağımlılık) buna izin vermez. Bunları açıkça
listelemek, skill'in vaadini abartmaması (*over-promise* önleme) içindir.

| Kaynak | Lisans | Neden gömülemez | Ne yapılabilir |
|---|---|---|---|
| PhET simülasyonları | CC BY (içerik) ama HTML kaynağı **açık kaynak değil** | Çevrimdışı kurulum ~200MB; web gömme = `iframe` → PhET sunucuları (runtime ağ) | Yalnız bağlantı/atıf; veya kavramı özgün yazar-SVG simülasyonu olarak yeniden üret |
| GeoGebra içeriği | CC BY-NC-SA | **NC** (ticari-olmayan) + applet çalışma-zamanı bağımlılığı | Statik SVG/PNG dışa aktarım teknik olarak gömülebilir — ama NC koşulu yine de ticari yeniden dağıtımı engeller; pratikte kaçının |
| Desmos | Araç görselleri CC BY-SA; hesap makinesi API anahtarı + runtime JS gerektirir | ShareAlike + çalışma-zamanı bağımlılık | Gömme; gerekiyorsa kavramı özgün SVG ile ifade et |
| Khan Academy | CC BY-NC-SA, video ağırlıklı | **NC+SA** + video boyutu/runtime | Yalnız bağlantı/atıf |
| EBA / MEBİ / MEB portalı | FSEK (telif) kapsamında, açık lisans **yok** | Resmî MEB portal içeriği açık lisanslı değildir | Yalnız sanksiyone edilmiş yol: Müfredat MCP'nin çektiği kazanım/program metni (`curriculum-integration.md`) — başka hiçbir MEB-kökenli içerik doğrudan alıntılanmaz/gömülmez |
| TÜBİTAK ULAKBİM Açık Ders | CC BY-NC-ND | **ND**: türetme/remiks yasak | Yalnız referans/kısa alıntı, kaynak açıkça belirtilerek |

Kaynak sayfaları: [PhET HTML Licensing](https://phet.colorado.edu/en/licensing/html),
[PhET Offline Access](https://phet.colorado.edu/en/offline-access),
[GeoGebra License](https://www.geogebra.org/license),
[Desmos API Terms](https://www.desmos.com/api-terms),
[Khan Academy — telif SSS](https://support.khanacademy.org/hc/en-us/articles/202262954),
[TÜBİTAK ULAKBİM Açık Ders](https://acikders.ulakbim.gov.tr).

**Genel ilke:** Hiçbir "yapılamaz" kaynak zorla bakeable hale getirilmeye
çalışılmaz (örn. bir `iframe`'i gömüp "çevrimdışı" diye sunmak — bu hem
G-SELFCONTAINED'i hem lisansı ihlal eder). Şüpheli durumda varsayılan davranış
her zaman Tier-1 yazar-SVG'ye dönmektir (`svg-authoring.md`) — bu skill'in
**tek garantili** görsel-dayanak yoludur.

## 4. Dyslexia-font miti → ispatlı kaldıraçlar

**Yaygın ama yanlış varsayım:** "Disleksiye özel" bir font (ör. OpenDyslexic)
seçmek, disleksili/okuma güçlüğü olan öğrenciler için otomatik olarak okuma
performansını iyileştirir.

**Kanıt bunu desteklemiyor.** [PMC'de indekslenmiş bir çalışma](https://pmc.ncbi.nlm.nih.gov/articles/PMC5629233/)
özel disleksi fontunun (OpenDyslexic) okuma hızı/doğruluğunda güvenilir bir fayda
sağlamadığını; standart fontların en az onun kadar — çoğu ölçümde daha iyi — okunduğunu
bildirir. Özel bir "disleksi fontu" yatırımı, kanıtla desteklenmeyen bir sezgiye dayanır.

**İyi haber:** `carbon-edupedia` zaten IBM Plex Sans/Mono kullanır — bu
hâlihazırda kanıtla uyumlu bir humanist sans-serif seçimidir
(`carbon-child-system.md`). Özel bir "disleksi fontu"na geçmeye **gerek yok**;
tipografi kararı zaten doğru temel üzerine kuruludur.

**Ispatlı kaldıraçlar — bunları kullanın (font değiştirmek yerine):**
- **Satır aralığı (line-height):** Cömert aralık (≈1.5+) okuma akışını kolaylaştırır.
- **Satır uzunluğu / ölçü:** Kısa sütun genişliği (okunabilir karakter/satır
  oranı) — modülün mevcut sütun disiplini bunu zaten destekler.
- **Harf/kelime aralığı:** Hafif artırılmış `letter-spacing`/`word-spacing`
  bazı okuyucular için yardımcı olabilir.
- **Kullanıcı seçimi:** Okunabilirlik ayarlarını (aralık/ölçü büyütme) kullanıcıya
  bir kontrol olarak sunmak, tek bir varsayılanı herkese dayatmaktan üstündür.

**Yapılmaması gereken:** İleride bir "erişilebilirlik modu" eklenirse, buraya
**özel disleksi fontu seçeneğini varsayılan veya tek çözüm olarak koymayın** —
kanıt bunu desteklemiyor. Yukarıdaki kaldıraçlar (aralık, ölçü, kullanıcı
kontrolü) kanıt-temelli, düşük-riskli ve font-bağımsız çözümdür.

## 5. Lisans özet tablosu

Hızlı başvuru için tüm kaynaklar/teknikler tek tabloda (kaynak: içerik-zenginliği
araştırma bulguları özeti):

| Kaynak / Teknik | Lisans | Bakeable mi? | Not |
|---|---|---|---|
| Wikidata | CC0 | **Evet** | QID+tarih provenans; kazanıma uzlaştır |
| Wikimedia Commons (PD/CC BY seçili) | PD / CC BY | **Evet** (seyrek) | CC BY-SA'dan kaçının; atıf zorunlu |
| Native MathML | Yok (tarayıcı-yerli) | **Evet** | `mathExpr` yetersiz kalınca tamamlayıcı |
| Spaced-rep veri modeli | Yok (teknik, telif dışı) | **Evet** (yapı build-time, veri runtime yerel) | feature-detect zorunlu; IndexedDB yok |
| PhET | CC BY (içerik) / kapalı kaynak | **Hayır** | link/atıf veya yazar-SVG |
| GeoGebra | CC BY-NC-SA | **Hayır** (pratikte) | statik export bile NC'ye tabi |
| Desmos | CC BY-SA (görsel) + runtime | **Hayır** | link/atıf |
| Khan Academy | CC BY-NC-SA | **Hayır** | link/atıf |
| EBA / MEBİ / MEB portalı | FSEK, açık lisans yok | **Hayır** | yalnız Müfredat MCP kanalı |
| TÜBİTAK Açık Ders | CC BY-NC-ND | **Hayır** | referans/kısa alıntı |

Her satırdaki lisans iddiası, yukarıdaki ilgili bölümde (§2/§3/§4) verilen
kaynak URL'siyle doğrulanabilir.

## 6. Kaynakça

- Wikidata lisansı — https://www.wikidata.org/wiki/Wikidata:Licensing
- Wikimedia Commons dışarıda yeniden kullanım — https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia
- PhET HTML Licensing — https://phet.colorado.edu/en/licensing/html
- PhET Offline Access — https://phet.colorado.edu/en/offline-access
- GeoGebra License — https://www.geogebra.org/license
- Desmos API Terms of Use — https://www.desmos.com/api-terms
- Khan Academy telif SSS — https://support.khanacademy.org/hc/en-us/articles/202262954
- TÜBİTAK ULAKBİM Açık Ders — https://acikders.ulakbim.gov.tr
- OpenDyslexic font okunabilirlik kanıtı (PMC) — https://pmc.ncbi.nlm.nih.gov/articles/PMC5629233/
