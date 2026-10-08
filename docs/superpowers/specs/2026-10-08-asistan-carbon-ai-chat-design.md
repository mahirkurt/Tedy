# TEDY Asistanı — Carbon AI Chat'e tam geçiş

Tarih: 2026-10-08 · Durum: kullanıcı onaylı tasarım (altı bölüm sohbette onaylandı), yazılı belge incelemede

## Amaç

Asistanın arayüzü bugün kendi yazdığımız bir React bileşeni: `dashboard/src/components/AssistantChat.tsx`
(1.099 satır) ve `AssistantChat.scss` (1.144 satır), çevresinde on'dan fazla kart ve panel. Bu tasarım onu
IBM'in Carbon for AI sohbet uygulamasına, `@carbon/ai-chat` 1.22.0'a taşır
(depo `carbon-design-system/carbon-ai-chat`, Apache 2.0; ikincil paket `@carbon/ai-chat-components` 1.12.0).

Kullanıcının bu geçişten beklediği iki şey:

1. **Carbon for AI standardı** — asistan, Carbon for AI sohbet deneyimiyle aynı görünsün ve davransın
   (AI etiketi ve açıklama penceresi, gradyan/parıltı, mesaj düzeni).
2. **Hazır yeni özellikler** — araç adımları (reasoning), beğen/beğenme geri bildirimi, yeni sohbet/yeniden
   başlat, tam ekran ve klavye kısayolları, yan panel düzeni.

Bakım yükünü azaltmak ve başka uygulamalarla ortaklık bu işin amacı **değildir**; kararlar bu iki amaca göre
tartılır.

## Kullanıcı kararları (2026-10-07/08)

| Konu | Karar |
|---|---|
| Kapsam | `@carbon/ai-chat`'e **tam geçiş** (yalnız Carbon for AI katmanı değil, karşılaştırmalı prototip değil). |
| Eşdeğerlik | **Tam eşdeğerlik**: aşağıdaki tablodaki her özellik ve her test yeni arayüzde yeşil olmadan canlıya çıkılmaz. Eski bileşen geçiş boyunca kodda kalır; değişim tek seferde yapılır. |
| Yerleşim | **Gömülü + her sayfada başlatıcı**: `/asistan` sayfayı doldurur; diğer sayfalarda Carbon'un AI başlatıcısı yan panel açar. |
| Sayfa bağlamı | **Sayfa bağlamı + sayfaya özel hızlı sorular**: görünür, kaldırılabilir bir bağlam çipi. |
| Çatışma kuralı | **Carbon AI kazanır, çekirdek kurallar korunur**: görünüm Carbon AI Chat'in kendi görünümüdür; TEDY'den kalan çekirdek: öğretmen modunun ders rengi, erişilebilirlik alt sınırı, azaltılmış hareket, odak modu, Türkçe metinler. |
| Açılacak hazır özellikler | Araç adımları · geri bildirim · yeni sohbet/yeniden başlat · tam ekran ve klavye kısayolları (dördü de). |
| Yaklaşım | **A** — Carbon AI Chat'in tamamı + TEDY uyarlayıcı katmanı. |
| Geri bildirim görünürlüğü | Işık'ın olumsuz geri bildirim metni aileye açık; kutuda "Ailen bunu görebilir" yazar. |

### Onaylanan varsayımlar

- Arka ucun cevap üretimi (model, araçlar, B6 denetimi, SSE olay sözleşmesi) değişmez; yalnız §5'teki üç ek.
- Başlatıcıyı yalnız `full` rol görür; reader görmez; odak modunda gizlidir.
- Sayfa ile başlatıcı paneli **aynı** sohbeti açar (B3 sohbet kimliği tek kaynak).
- IBM telemetrisi kapalıdır (`IBM_TELEMETRY_DISABLED=true`); bu bir kısıttır, tercih değil.
- Carbon AI Chat yalnız açıldığında yüklenir; Bugün/İşler'in ilk yüklemesine girmez.

## Pakette doğrulananlar (tür tanımlarından, 2026-10-07/08)

- `messaging.customSendMessage` + `instance.messaging.addMessageChunk` — kendi arka ucumuzu akışla bağlar.
  Parçalar: `partial_item` (metin biriktirir), `complete_item` (aynı `streaming_metadata.id` ile biriken
  öğenin yerine geçer), `final_response` (mesajın tamamının yerine geçer). Ayrıca `upsertMessage`,
  `removeMessages`.
- `user_defined` öğe + `renderUserDefinedResponse` — kendi React kartlarımız; `renderCustomMessageFooter` —
  mesaj altbilgisi; `renderWriteableElements` — giriş çevresi yuvaları.
- `conversational_search` öğesi: `text` + `citations[{title, text, url, ranges[{start,end}]}]`.
- `MessageResponseOptions.chain_of_thought[{title, description, tool_name, status}]` ve `reasoning`.
- `GenericItemMessageFeedbackOptions`: beğen/beğenme, kategoriler, metin alanı, istem.
- `history` (+ `messaging.customLoadHistory`), `upload` (`onFileUpload`), `header` (`showAiLabel`,
  `showRestartButton`, `menuOptions`), `layout` (`showFrame`, `corners`, `customProperties`), `aiEnabled`
  (gradyan), `locale`, `strings` (`LanguagePack`), `markdown.markdownItPlugins`, workspace özel paneli.
- Bağımlılıklar: peer `@carbon/web-components` `>=2.54 <3`, React `<20` (bizde 19.2 — uyumlu). İçinde lit,
  markdown-it, tiptap; `@carbon/ai-chat-components` CodeMirror'ın bütün dil paketlerini getirir. Paket
  sıkıştırılmamış ~15 MB. Kurulumda `@ibm/telemetry-js` çalışır.

## 1. Mimari ve birimler

Yeni dizin `dashboard/src/asistan/`. Her birimin tek bir işi var:

| Birim | İşi | Bağımlılığı |
|---|---|---|
| `akisIstemcisi.ts` | `/api/assistant/stream` isteği, SSE okuma; akış düşerse `/api/assistant/chat` yedeği (bugünkü davranış); `AbortController` ile durdurma | yalnız `fetch` |
| `olayEslemesi.ts` | **Saf fonksiyon**: TEDY SSE olay dizisi → Carbon `StreamChunk` / `MessageResponse`. React'e ve DOM'a dokunmaz | Carbon türleri |
| `tedyChatConfig.ts` | `PublicConfig` üretir: `locale: 'tr'`, Türkçe `strings`, başlık ve AI etiketi, geçmiş, yükleme, `markdownItPlugins`, `layout`, geri bildirim seçenekleri | `useOgretmen`, `useSession` |
| `markdownEklentileri.ts` | KaTeX (`$…$`, `$$…$$`) ve `:::kavram/ornek/adimlar/sonuc/hata` için markdown-it eklentileri; bugünkü `renderMarkdown(…, {bicim:'sohbet'})` kurallarının birebir karşılığı (bilinmeyen/yarım blok metin kalır, taşan formül/tablo kendi içinde kayar) | `katex` |
| `OzelYanitlar.tsx` | `renderUserDefinedResponse`: mevcut kartlar `AlistirmaKarti`, `OdevOnayKarti`, `NetlestirmeSecenekleri`, `ModOnerisi`, plan blokları | mevcut kartlar |
| `MesajAltbilgisi.tsx` | `renderCustomMessageFooter`: Sesli oku, Daha derine in, Yeniden yaz, model/denetim/yedek rozeti | `useSes` |
| `AsistanSayfasi.tsx` | `/asistan`: `ChatCustomElement`, sayfayı doldurur; öğretmen seçici başlığın altında | yukarıdakiler |
| `AsistanBaslatici.tsx` | Diğer sayfalar: `ChatContainer` (float/yan panel), bağlam çipi, sayfaya özel hızlı sorular | `routes.ts`, odak modu |
| `useAsistanOturumu.ts` | Sayfa ile başlatıcının aynı sohbeti göstermesi (B3 sohbet kimliği, `customLoadHistory`) | `useSohbetler` |
| `sayfaSorulari.ts` | Sayfa → öğrenci/aile hitabıyla 2–3 hızlı soru | — |

**Yükleme:** `AsistanSayfasi` ve Carbon AI Chat'li panel `React.lazy` ile ayrı parçaya gider. Başlatıcı
düğmesi kendi başına küçüktür (hedef ≤ 10 KB); Carbon AI Chat ilk tıklamada yüklenir.

**Geçiş bayrağı:** Eski `AssistantChat` yerinde kalır. Hangi bileşenin açılacağını derleme zamanı değişkeni
`VITE_ASISTAN_CARBON_AI` belirler — geliştirme ve testte açık, canlıda kapalı. Tam eşdeğerlik yeşil olunca
canlıda açan tek commit atılır. Eski bileşen birkaç gün sorunsuz kullanımdan sonra ayrı bir commit'le silinir.

**Çatışma kuralının uygulanışı:** Carbon AI Chat'in görünümü (gradyan, parıltı, köşeler, mesaj düzeni,
hareket) olduğu gibi kalır. Yalnız şunlar TEDY'den gelir:

- Öğretmen modunda ders rengi, `subjectThemes` rol token'larından Carbon AI Chat'in CSS özel özelliklerine
  aktarılır: gönder düğmesi, panelin üst kenarı, okurun balonu (bugün `AssistantChat.scss`'in yaptığı;
  marka bandı değişmez). Kontrast ≥ 4.5:1.
- `prefers-reduced-motion` altında hiçbir şey canlanmaz; `forced-colors` altında kenarlar kalır.
- Odak modunda başlatıcı gizlenir.
- Görünen her metin Türkçedir (`strings`).

`tests/test_pano_tasarim_sistemi.py` ve stylelint Carbon token kuralı TEDY'nin kendi stillerine uygulanmaya
devam eder; Carbon AI Chat'in kendi stilleri ("Carbon for AI's own gradients") muaftır ve muafiyet gerekçesiyle
yazılır.

## 2. SSE olayı → Carbon mesajı eşlemesi

Bir asistan cevabı tek bir Carbon mesajıdır; birden çok öğe taşır. Tamamı `olayEslemesi.ts` içindedir.

| TEDY olayı | Carbon karşılığı |
|---|---|
| `tool_start` / `tool_end` | Mesajın `chain_of_thought` adımı. Başlık bugünkü `TOOL_LABEL` metni ("Müfredat aranıyor"); `tool_end` adımı tamamlandı yapar, `ozet` (§5.1) açılır-kapanır gövdededir. Ham argüman/JSON gösterilmez (D4). |
| `answer_delta` | Metin öğesine `partial_item`. Akan taslakta `[S1]` işaretleri gizlenir (bugünkü gibi). |
| `answer_reset` | Aynı öğe kimliğiyle boş `complete_item`; akış yeni bir öğe kimliğiyle sürer. |
| `answer` | `final_response` mesajın tamamının yerine geçer. B6 denetimi metni değiştirdiyse okurun gördüğü budur; taslak sessizce yenilenir. |
| `payload.citations` | Son metin `conversational_search` öğesi olur: `[S1]` işaretleri metinden çıkar, yerlerine `ranges`; numaralar bugünkü okuma sırasını (`_finalize_citations`) korur. |
| Figür / modül / Tedy kitabı kaynağı | Carbon atıf kartı taşıyamaz: atıfa tıklanınca workspace panelinde bugünkü `SourcePanel` açılır (figür küçük resmi + `?v=<corpus_version>`, `moduleLink` bağlantısı). |
| `quiz`, `odev_onerisi`, `clarify`, `mode_suggestion` | Her biri ayrı `user_defined` öğe; `OzelYanitlar.tsx` mevcut kartı çizer, davranışı aynen. Mod önerisi yalnız sayfa Genel moddayken görünür. |
| `planBlocks` (`/plan`) | `user_defined`, bugünkü plan blokları. |
| `flags` içinde `warning:yerel_yedek` | Altbilgide gri "Yedek modelden" rozeti; metnin sonundaki italik not (sunucudan) kalır. |
| `error:model_unavailable` / `error` olayı | `inline_error` öğesi, bugünkü Türkçe cümleyle. |
| Akış düşer | `/chat` yedeğine geçilir; yarım taslak `removeMessages` ile kalkar; okura hata gösterilmez (bugünkü davranış, konsola uyarı). |
| Durdur | Carbon'un durdur düğmesi → `AbortController`; sunucu bunu zaten iptal noktası sayar. |

Her mesajın AI etiketi açıklama penceresini açar: model adı (`modelAdi`), öğretmen modu, kaynak sayısı,
denetim durumu, yedek model bilgisi ve bugünkü üst başlıktaki "Bu yanıtları bir yapay zekâ yazıyor" metni.

## 3. Özellik eşdeğerlik tablosu (bağlayıcı)

Bir satır yeni arayüzde testiyle yeşil olmadan bayrak açılmaz. Testlerdeki CSS sınıfı seçicileri (`.ac__…`)
Carbon'un shadow DOM'u yüzünden role ve metin seçicilerine çevrilir; kanıtlanan **davranış** aynı kalır.

| Bugünkü özellik | Yeni yeri | Kanıt |
|---|---|---|
| SSE akışı, `/chat` yedeği, durdur | `akisIstemcisi` + Carbon akışı | `assistant-chat` (15), `olayEslemesi` birim testleri |
| Öğretmen modları ve renkleri, tercih hafızası (`tedy-asistan-ogretmen::<email>`) | `OgretmenSecici` Carbon başlığının altında; ders rengi CSS özel özelliklerine | `asistan-ogretmen` (12), `asistan-ogretmen-gorsel` (4) |
| Karşılama ve hızlı sorular (öğrenci/aile hitabı, skill'den; Genel'de `VOICE`) | Carbon `homescreen` | `asistan-ogretmen`, `assistant-ai` (6) |
| Numaralı atıflar, kaynaklar, figür küçük resmi, modül bağlantısı | `conversational_search` + workspace'te `SourcePanel` | `asistan-gorsel-kaynak` (3), `assistant-moduller` (4) |
| KaTeX, `:::` blokları, tablolar, kayan taşma ve odak | `markdownEklentileri` | `asistan-zengin-cevap` (7), `asistan-cevap-bicimi` (4) — görsel referanslar yeniden çekilir |
| Alıştırma kartları | `user_defined` → `AlistirmaKarti` | `asistan-alistirma` (7) |
| Ödev fotoğrafı onay kartı, `odev_tamamla` | `user_defined` → `OdevOnayKarti` | `photo-homework` (7) |
| Netleştirme seçenekleri (eski/salt okunur sohbette kapalı) | `user_defined` → `NetlestirmeSecenekleri` | `asistan-netlestirme` (1) |
| Mod önerisi | `user_defined` → `ModOnerisi` | `asistan-ogretmen` |
| Dosya yükleme, dokunmatikte arka kamera, ek önizleme/kaldırma, 4/10 sınırları, hata cümleleri | Carbon `upload.onFileUpload` → `/api/assistant/uploads` | `asistan-yukleme` (10) |
| Sohbet geçmişi: oluştur, ad değiştir, sil; aile öğrencininkini salt okur (giriş kapalı) | Carbon geçmiş paneli + B3 uçları | `asistan-sohbet` (9) |
| Asistanın notları (aile) | Workspace'te "Notlar" paneli, başlık menüsünden | `asistan-sohbet` |
| Sesli oku / Durdur, mikrofon ve ilk kullanım onayı (`tedy-ses-onay::<email>`) | Altbilgide Sesli oku; mikrofon giriş yanında (`renderWriteableElements`), `useSes` aynen | `asistan-ses` (5) |
| Daha derine in, Yeniden yaz | Altbilgi düğmeleri | `assistant-chat` |
| Ödev seçici | Giriş üstü yuvası (`renderWriteableElements`) | `assistant-chat` |
| Plan blokları | `user_defined` | `assistant-ai` |
| Denetim / yedek model rozetleri, AI açıklaması | Altbilgi rozeti + mesaj AI etiketi | `assistant-ai` |
| Sayfa bütünlüğü (axe, IBM Equal Access, aria ağacı, 4K, azaltılmış hareket, forced-colors, telefon, alt gezinme, yan kaydırma yok, pencere kaymaz) | Aynı denetimler yeni bileşende | `tasarim-denetimi`, `ibm-erisilebilirlik`, `aria-yapisi`, `ekran-4k`, `gorunum-kipleri`, `alt-gezinme`, `gorsel-regresyon`, `capraz-tarayici` |

Asistana dokunan diğer spec'ler (`dashboard`, `polish`, `d3b-dokunma`, `homework-docs`, `dersler`) yeni
bileşene karşı da geçmelidir.

**Yeni gelenler** (eşdeğerlik dışı, kendi testleriyle): araç adımları; geri bildirim; yeni sohbet/yeniden
başlat; tam ekran ve kısayollar; başlatıcı ve sayfa bağlamı.

## 4. Başlatıcı ve sayfa bağlamı

**Nerede:** ≥ 672 px'te `full` rolün her sayfasında sağ altta Carbon AI başlatıcısı. Görünmez: `/asistan`,
modül görüntüleyici (`/moduller/<slug>/v<N>`), Tedy Books okuyucusu, giriş sayfası, reader rolü, odak modu.
Açılınca sağda yan panel; tam ekrana büyür; Carbon kısayolu açar/kapatır.

**Telefonda (< 672 px):** yüzen düğme yok (alt gezinmeyle çakışır, İ1). Alt gezinmedeki "Asistan" sekmesi
o anki sayfayı taşır (`/asistan?sayfa=<ad>`) ve sayfa aynı çiple açılır.

**Hangi sohbet:** başlatıcı `/asistan`'daki etkin sohbeti açar; biri diğerinde yazılanı görür. "Yeni sohbet"
ikisinde de var.

**Bağlam çipi:** giriş alanının üstünde "Bu sayfa: İşler · ✕"; açık bir öğe varsa onu da adlandırır
("Bu sayfa: İşler — Matematik s.84 ödevi"). Öğe türleri: ödev penceresi, sınav, ders içeriği haftası, takvim
etkinliği. Çip yalnız **bir sonraki mesaja** eşlik eder, sonra kaybolur; ✕ ile kaldırılır.

**Sayfaya özel hızlı sorular** (`sayfaSorulari.ts`, öğrenci/aile hitabıyla 2–3'er): örn. İşler "Bugün
hangisinden başlayayım?", Takvim "Bu haftam nasıl görünüyor?", Notlar "Hangi derste zorlanıyorum?", Dersler
"Bu haftaki konuyu kısaca anlat", Duyurular "Beni ilgilendiren bir duyuru var mı?". Çip etkinken sayfa
soruları, kaldırılınca bugünkü mod soruları görünür.

**Ölçüt:** başlatıcı düğmesi ≤ 10 KB; Carbon AI Chat ilk tıklamada yüklenir. Başlatıcı düğmesi
`gorsel-regresyon` referanslarını değiştirir; farklar okunup yenilenir.

## 5. Arka uç ekleri

### 5.1 Araç adımı özetleri

`tool_end` olayı (`src/assistant_core.py`, `announcing`) bugün `{name, ok}` taşır; yanına okura gösterilebilir
kısa `ozet` eklenir. Özet sunucuda, aracın döndürdüğü atıf etiketlerinden üretilir ("3 ödev bulundu",
"Matematik 7 (2. Kitap) · s.57", "Fen Bilimleri 7 figürü açıldı"); başarısızsa "Bu kaynağa şu an
ulaşılamadı"; `skill_kaynagi` için "Öğretmen notlarına bakıldı". Ham argüman ve araç çıktısı gönderilmez.
Adımlar yalnız canlı akıştadır, veritabanına yazılmaz — geçmişten açılan eski cevapta adım listesi yoktur
(bilerek bırakılan eksik).

### 5.2 Geri bildirim

- Tablo `geri_bildirim` (`output/assistant_sohbetler.sqlite`): `mesaj_id`, `sahip_email`, `deger`
  (`olumlu`|`olumsuz`), `kategori` (olumsuzda: "Yanlış bilgi", "Anlamadım", "Seviyeme uygun değil",
  "Kaynak göstermedi", "Diğer"), `metin` (≤ 500 karakter), `zaman`; birincil anahtar
  (`mesaj_id`, `sahip_email`).
- `PUT` / `DELETE /api/assistant/mesajlar/<id>/geri-bildirim`: kişi yalnız kendi sohbetindeki asistan
  mesajını değerlendirir; yanlış sahip/kimlik 404; aile öğrencinin sohbetini salt okur, orada düğme yoktur.
  Tekrar gönderim günceller; sohbet silinince geri bildirim de silinir.
- Geçmiş API'si her asistan mesajı için okurun kendi geri bildirim değerini döndürür.
- İlerleme sayfasındaki Öğrenme günlüğü (`/api/assistant/ogrenme-gunlugu`) aileye haftalık olumlu/olumsuz
  sayısını ve son olumsuz notların kategori + metnini gösterir. Geri bildirim kutusu "Ailen bunu görebilir"
  der.
- `output/assistant_metrics.jsonl` satırına `geri_bildirim` alanı (B6'nın etkisini ölçmek için).

### 5.3 Sayfa bağlamı alanı

- `/stream` ve `/chat` isteğe bağlı `sayfa: {ad, oge?: {tur, id}}` alır; `/plan` ve `/v1` yok sayar.
- `ad` bilinen sayfa listesinden; `oge.tur` ∈ {`odev`, `sinav`, `etkinlik`, `ders_haftasi`}; `id` biçim
  kontrollü. Geçersiz → 400 "Bilinmeyen sayfa." (`ogretmen` alanı gibi, akış açılmadan).
- Öğe başlığı sunucuda kendi verisinden çözülür (istemcinin metnine güvenilmez); çözülemezse satır yalnız
  sayfa adını taşır.
- O turun kullanıcı mesajına "Bugün:" satırının yanında "Bulunduğu sayfa: İşler (açık: <başlık>)" satırı
  eklenir; sistem istemi ve önbellek değişmez; saklanan kullanıcı metnine girmez.

## 6. Test, ölçüm, yayın ve geri dönüş

### İlk görev: risk denemesi

Kalıcı kod öncesi, ayrı bir geliştirme sayfasında gerçek bileşenle:

1. `answer_reset` → boş `complete_item`; `final_response` ile metin değişimi.
2. `:::` blokları ve KaTeX'in Carbon'un markdown motorunda bugünkü çıktıyla aynı görünmesi.
3. Ders renginin CSS özel özelliklerine geçmesi; kontrast ≥ 4.5:1.
4. Türkçe `strings` sonrası görünür İngilizce metin kalmaması (sayfa metni taranır).
5. axe ve IBM Equal Access'in shadow DOM içini denetleyebilmesi.
6. Tembel parçanın boyutu ve Bugün'ün ilk yüklemesine etkisi (`npm run analyze`).

Biri tutmazsa o parça tasarımdaki yedeğe (`user_defined` + bizim renderer'ımız) iner ve kullanıcıya
bildirilir. Erişilebilirlik denetimi shadow DOM'u göremezse kullanıcıya sorulmadan geçilmez.

### Test katmanları

- Vitest: `olayEslemesi.ts` (olay dizisi → beklenen Carbon parçaları; `answer_reset`, denetim değişimi, yedek
  model, hata, atıf `ranges`), `markdownEklentileri.ts`.
- Python (`unshare -rn`, ağsız): §5 — özet üretimi (atıf yok/var/başarısız), geri bildirim sahipliği ve
  kaskadı, `sayfa` doğrulaması ve satır.
- Playwright: §3'teki her spec yeni bileşene karşı; soru gönderen her test `/stream` ve `/chat`'i kendisi
  yanıtlar, `env -u ANTHROPIC_API_KEY` ile koşar. Yeni testler: başlatıcı, çip, telefon sekmesi, geri bildirim,
  araç adımları, tam ekran.
- Sayfa bütünlüğü spec'leri ve `capraz-tarayici` (WebKit, Firefox); görsel/aria referansları farkları
  okunduktan sonra yenilenir.
- `npm run lint` temiz; Lighthouse erişilebilirlik ≥ 0.95, CLS ≤ 0.1.

### Telemetri

Paket kurulum komutları `IBM_TELEMETRY_DISABLED=true` ile koşar; `CLAUDE.md` Komutlar bölümüne ve bu
makinenin kalıcı ortamına (`~/.config/environment.d/` + kabuk profili) yazılır. Bir test derlenmiş pakette
`www-api.ibm.com/ibm-telemetry` adresinin bulunmadığını doğrular.

### Çalışma yeri

Ana TED checkout'u başka oturumlarla paylaşılır: iş `.claude/worktrees/carbon-ai` worktree'sinde,
`feat/carbon-ai-chat` dalındadır. `main`'e birleştirme ve canlıya alma ayrı adımlardır.

### Yayın (tek seferde)

1. Eşdeğerlik tablosunun bütün satırları ve testleri yeşil.
2. Bayrağı canlıda açan tek commit → `npm run build` → `ted-dashboard` ve `ted-mcp` yeniden başlatılır.
3. Canlı duman testi: site 200, `/asistan` açılır, bir soru-cevap, başlatıcı açılır.
4. Gerçek telefonda deneme kullanıcı (veya Işık) tarafında; sonuç ekran görüntüsüyle beklenir.

### Geri dönüş

Bayrak commit'i geri alınır, yeniden derlenir, servis yeniden başlatılır (birkaç dakika). §5 geriye uyumludur,
geri alınmaz. Eski bileşen birkaç gün sorunsuz kullanımdan sonra ayrı commit'le silinir.

## Kapsam dışı

- Cevap üretiminin, araçların, B6 denetiminin, sistem isteminin değişmesi.
- Araç adımlarının kalıcı saklanması (§5.1).
- Carbon AI Chat'in web bileşeni sürümünün başka uygulamalarda (edupedia modülleri vb.) kullanılması.
- `/v1` ve API anahtarlı istemcilerin herhangi bir değişikliği.
