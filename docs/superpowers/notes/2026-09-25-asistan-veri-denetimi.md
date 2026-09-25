# Asistanın veri erişimi — denetim (2026-09-25)

Salt-okuma denetim; ölçüm, tahmin değil. Plan: `docs/superpowers/plans/2026-09-25-asistan-tam-baglam.md`.

**Özet:** Asistan, araç açıklamasının ve CLAUDE.md'nin söylediğinden çok daha azını görüyor. Üç yapısal sorun var:
- Haftalık ders programı ve ders içeriği metni BM25 indeksine hiç girmiyor.
- İndeks gürültüyle (log, çerez, yedek dosyaları) dolu.
- Diskteki tek ders kitapları geçen yılın 6. sınıf kitapları ve 120. sayfada kesiliyor.

## 1. Yerel veri envanteri

| Öğe | Boyut / sayı | İçerik | Asistan erişimi |
|---|---|---|---|
| `output/scraped_data.json` | 424 KB | profile, `ders_programi` (1 hafta), `odevlerim`, `takvim` (41 etkinlik), `ders_icerikleri` (12 ders, güncel hafta), `gelisim_raporu` (notlar + 37 kazanım düzeyi `rubrics`), `ogep`/`takim` (boş), `duyurular` (boş), `ek_sayfalar` (5 sayfa), `ders_icerikleri_haftalar` (36 hafta, 274 KB) | Kısmen (bkz. §2) |
| `content/eba/` | 871 MB, 10 PDF | **6. sınıf** MEB ders kitapları (Fen, Mat, Sosyal, Türkçe, İng, Müzik) | İndekste ama kesik |
| `content/sebitv/` | 71 MB, 81 PDF | 6. sınıf konu özetleri (4 ders) | İndekste (330 parça) |
| `content/pedagoji/` | 150 MB, 7 md + 3 PDF | Yetişkinlere yönelik pedagoji notları; Woolfolk, Santrock, *Child Psychopathology* | İndekste, **15.049 parçanın 9.769'u (%65)** |
| `content/yabanci-dil/` | 302 MB, 9 PDF | İngilizce/Fransızca ders kitapları, *Amulet* | İndekste; 3 taranmış PDF'ten yalnız üst veri |
| `content/mebi/`, `content/sebitv-interactive/` | **yok** | — | yok |
| `books/` (2 kitap) | 12 `.md` bölüm, 2 `book.json`, zip, xlsx | Tedy Books (Hobbit EN, Yüzüklerin Efendisi TR) | **Görünmez**: `books` `DEFAULT_INCLUDE_DIRS`'te değil |
| `sebit_homework.json` | 15 KB, 32 ödev | SEBİT ödevleri (ilerleme, öğretmen) | Görünmez (`sebit_*` deseni) |
| `photo_homework.json`, `homework_student_done.json` | 7 KB, 1 KB | Fotoğraftan eklenen ödevler; "Yaptım" işaretleri | Yalnız `odev_listesi` üzerinden (bilerek indeks dışı) |
| `private_lessons.json` | 2 ders | Özel ders saatleri | Görünmez |
| `englishcentral_progress.json` / `achieve3000_progress.json` | 49 KB / 0,3 KB | Platform ilerlemesi | Ham JSON olarak indekste |
| `ec_dialog_details.json`, `a3k_*.json` | 26 KB, 32 diyalog | EnglishCentral diyalogları, A3K dersleri | Görünmez |
| `mebi_videos_discovered.json` (112), `sebitv_discovered.json` (657), `sebitv_content_tree.json` | üst veri | Konu → video/PDF eşlemeleri | Görünmez |
| `*_uploaded.json` izleyiciler | hepsi `{}` | 2025-26 yılı mühürlenince sıfırlandı | İndekste ama boş |
| `enrichment_cache.json`, `exam_content_map.json` | **yok** | — | Biçimlendiricileri ölü kod |
| `output/modules/index.json` | 1 modül | edupedia modülleri | `modul_ara` |
| `book_progress.json`, `module_progress.json`, `health.json` | — | Kişi başı ilerleme; senkron sağlığı | `book_progress` **indekste** (bkz. §2c) |

## 2. BM25 indeksi (`output/assistant_index/`)

İndekste 143 dosya ve **15.049 parça** var; tavan `ASSISTANT_MAX_CHUNKS=15000`, yani **tavana dayanmış**.

- **Kaynağa göre parça:** pedagoji 9.769 · eba 1.962 · yabanci-dil 801 · sebitv 330 · output 2.187.
- **output/ parçalarının çoğu gürültü:** `sync.log.1` 1.300 parça (`*.log` deseni `.log.1`'i yakalamıyor), `portal_architecture.json` 650, `mebi_quiz_discovery` 124.
- **Gerçek öğrenci verisi yalnız 8 parça.** Üstelik `saat_dilimi_gocu_yedek/scraped_data.json` aynı dosya adı yüzünden aynı biçimlendiriciden geçip eski bir kopya olarak da indeksleniyor.
- **Tavan dolunca dosyalar sessizce düşer.** Keşif yola göre sıralı, `content/` `output/`'tan önce geliyor ve döngü tavanda duruyor. 7. sınıf PDF'leri eklenirse `output/scraped_data.json` hiçbir hata vermeden indeksten düşer.

**(a) `_fmt_scraped_data` diskteki veri biçimine uymuyor.**
- **DERS PROGRAMI:** Yalnız hafta etiketi çıkıyor. `schedule` aslında `{headers, rows, empty_state}` biçiminde; biçimlendirici gün → saat sözlüğü bekliyor.
- **DERS İÇERİKLERİ:** Boş bir başlık çıkıyor. Her ders `{tab_id, text, tables, items, cards}` sözlüğü; biçimlendirici liste bekliyor.
- **Hiç okunmayanlar:** `ders_icerikleri_haftalar`, `ek_sayfalar`, `rubrics`, takvim `extendedProps`, profil.
- **Çalışanlar:** ödevler (200 karakterde kesik), takvim başlıkları, notlar. Notlar da geçen yılın (2025-26 "4. Arakarne").

**(b) Dosya türleri.**
- **PDF:** pypdf ile yalnız ilk 120 sayfa okunuyor. 10 EBA kitabının 8'i daha uzun (131–222 sayfa).
- **Taranmış PDF:** OCR yok, yalnız üst veri kalıyor.
- **ZIP/XLSX:** üst veri ya da çöp.
- **Görseller:** OCR kapalı.

**(c) İndekse sızan dosyalar:** `portal_cookies.json` (portal oturum çerezleri), `book_progress.json` (e-postalar, okuma konumları), `crontab`, `.sync_zamanlama.json`, `*.pid`.

**(d) Bir isabetin işe yararlığı.**
- `_dispatch_local` her isabetten yalnız **260 karakterlik `snippet`**'i döndürüyor; tam metin elde olduğu hâlde.
- Belirteçleyici Türkçe büyük/küçük harf bilmiyor: "İngilizce" → `['i','ngilizce']`.
- **Denenen sorgular:**
  - "ders programı yarın" → 8/8 `sync.log.1`.
  - "Fen Bilimleri notum" → not parçası yok.
  - "İngilizce ödevi" → 8/8 `homework_first_seen.json`.

## 3. Asistanın ulaşamadığı pano uçları

| Uç | Durum |
|---|---|
| `/api/schedule`, `/api/calendar/unified` | **Erişilemez.** Ders programı biçimlendiricide kayboluyor. Unified ayrıca özel ders, SEBİT, ÖGEP ve takımları birleştiriyor; asistan bunların hiçbirini görmüyor. |
| `/api/content`, `/api/content/weeks` | **Erişilemez** |
| `/api/exams` | Yalnız dolaylı, takvim başlıklarından. Sınıflandırma ve yaklaşan/geçmiş mantığı `dashboard_api`'de kalıyor. |
| `/api/grades` | Dolaylı; rubrik yok |
| `/api/pages`, `/api/sebit`, `/api/private-lessons`, `/api/books*`, `/api/progress/a3k` | Erişilemez |
| `/api/homework` | `odev_listesi` ile tam (SEBİT hariç) |
| `/api/modules` | `modul_ara` |

## 4. MCP kapsamı

**27 araçtan 9'u izinli.**
- **İzinli, maarif:** search_learning_outcomes, list_learning_outcomes, search, list_textbooks, get_document_text, search_figures, get_figure.
- **İzinli, egitim-kaynak:** kb_search, kb_for_outcome.
- **Öğrenciye değer katacak olup izinli olmayanlar:**
  - `get_curriculum_program`: ünite/tema sırası.
  - `get_subject`: bir dersin kitabı var mı?
  - `list_videos` / `get_video`: anlatım videoları.
  - `kb_get`: `oer_ara` parçasının bağlamını genişletmek.

## 5. `get_figure` görselleri

Görseller modele de arayüze de hiç ulaşmıyor:
- `McpClient` görselleri topluyor.
- `McpRegistry.dispatch` ise yalnız `result.text`'i kullanıyor.
- `ToolOutcome`'da görsel alanı yok.
- `chat_with_tools` araç sonucunu 4.000 karakterlik bir dize olarak gönderiyor.
- `SourcePanel` yalnız `snippet` gösteriyor.

## 6. Diğer kaynaklar

- **ted-mcp federasyonu** (anamnesis, pexels, minimax, comfyui, tr-literatur, openalex): pano asistanına bağlı değil.
- **Portalda okunmayan sayfa:** Akademik Takvim; öğrenci hesabına kapalı.
- **Google Drive arşivi:** erişim yolu yok.
- **EBA/MEBİ/SEBİTV:** keşif JSON'ları var ama indirmeler geçen yıla ait.

## Kapanış (2026-09-25, plan `docs/superpowers/plans/2026-09-25-asistan-tam-baglam.md`, Görev 6)

Görev 1–5'in her biri bu denetimin bir kesitini kapattı. Aşağıda denetimin her
bulgusu için: kapandı (hangi görev) ya da ertelendi (neden).

**§1 Yerel veri envanteri**
- Ders programı/ders içerikleri metni indekse hiç girmiyordu → **kapandı (Görev 2)**:
  `_fmt_scraped_data` diskteki gerçek biçimlere (`{headers, rows}`, `{tab_id, text, …}`)
  göre yeniden yazıldı; ayrıca beş canlı araç (`ders_programi`, `sinavlar`, `takvim`,
  `ders_icerigi`, `notlar`) aynı veriye BM25'in dışından da erişir.
- `content/eba` 120 sayfada kesiliyordu (10 kitabın 8'i 131–222 sayfa) → **kapandı
  (Görev 1)**: `ASSISTANT_PDF_MAX_PAGES` 400'e çıktı.
- `content/pedagoji` tavana çarpıp %65'te kalıyordu → **kapandı (Görev 1 + Görev 5)**:
  tavan 15.000'den 30.000'e çıktı, ve `content/pedagoji` artık paylaşılan tavanla hiç
  yarışmıyor — kendi ayrı indeksinde (`aile_kaynak_ara`, Görev 5).
- `content/yabanci-dil`'deki taranmış PDF'ler (OCR yok) → **ertelendi**: bu planın
  kapsamında OCR işi yok; hâlâ yalnız üst veri.
- `content/mebi`, `content/sebitv-interactive` diskte yok → **ertelendi**: ortada
  indekslenecek veri olmadığından bu plan bir şey scrape etmedi.
- `books/` (Tedy Books) görünmezdi → **kapandı (Görev 3)**: `kitap_ara`, kendi küçük
  BM25 indeksiyle (`src/assistant_kitaplar.py`), `dashboard_api._book_chapters()`'ı
  yeniden kullanarak.
- `sebit_homework.json` `odev_listesi`'nde görünmüyordu → **kapandı (Görev 3)**:
  `odev_listesi`'nin kendi "SEBİT" bölümü.
- `photo_homework.json`, `homework_student_done.json` → **değişmedi (kasıtlı)**:
  denetim bunları zaten "yalnız `odev_listesi` üzerinden, bilerek indeks dışı" diye
  işaretlemişti; bu plan onu bozmadı.
- `private_lessons.json` görünmezdi → **kapandı (Görev 2)**: `takvim` aracı, hafta
  sonu dahil, aynı `_birlesik_takvim`/`_private_lessons_for_week` verisini okur.
- `englishcentral_progress.json`/`achieve3000_progress.json` ham JSON olarak
  indekste → **kapandı (Görev 3 + fix round 1)**: `platform_ilerlemesi` okunur bir
  özet verir (ham JSON modele hiç gitmez); fix round 1'de (kontrolör) iki dosya da
  `DEFAULT_EXCLUDED_FILE_PATTERNS`'e eklendi, artık genel indekste de yok
  (`tests/test_assistant_indeks_hijyeni.py::test_excluded_files_are_never_discovered`).
- `ec_dialog_details.json`, `a3k_*.json` görünmezdi → **ertelendi**: `platform_ilerlemesi`
  yalnız özet dosyalarını okur, diyalog ayrıntısı hâlâ erişilemez; kasıtlı dışlama
  desenleri (`ec_*.json`, `a3k_*.json`, Görev 1) bunları indeksten de çıkardı.
- `mebi_videos_discovered.json` (112), `sebitv_discovered.json` (657) görünmezdi →
  **kapandı (Görev 3)**: `video_oner` bu iki katalogda arar; bağlantı yalnız kayıtta
  varsa verilir, sınıf hiç uydurulmaz — kayıtların hiçbirinde sınıf alanı yok
  (0/769, ölçüldü), bunun yerine katalogun kendi toplanma zamanı (dosya mtime'ı)
  okunur (fix round 1).
- `sebitv_content_tree.json` → **ertelendi**: hiçbir yeni araç bunu okumuyor.
- `enrichment_cache.json`, `exam_content_map.json` (diskte yok) → **ertelendi**:
  `dashboard_api._sinav_listesi()` bunları hâlâ okumaya çalışıyor (no-op, dosyalar
  yok); ölü kod yolu bu planın kapsamı dışında bırakıldı.
- `book_progress.json`, `module_progress.json`, `health.json` → **değişmedi**:
  üçü de `DEFAULT_EXCLUDED_FILE_PATTERNS`'te kalıyor (health.json Görev 1'de
  eklendi, diğer ikisi zaten dışarıdaydı).

**§2 BM25 indeksi**
- 15.049 parça, tavana dayanmış, `sync.log.1`/`portal_architecture.json`/
  `mebi_quiz_discovery` gürültüsü, `saat_dilimi_gocu_yedek` kopyası → **kapandı
  (Görev 1)**: `*.log.*` deseni, `portal_architecture.json`, `mebi_quiz_discovery`
  ve `saat_dilimi_gocu_yedek`/`crontab_yedek`/`archive` dizinleri artık dışlanıyor;
  tavan 30.000'e çıktı; tavanda kısmen sığan dosya artık ne yarım ne de sonsuza
  dek "tam" görünüyor (fix round 1, atomik dosya-bazlı yazım).
- `_fmt_scraped_data` diskteki biçime uymuyordu (DERS PROGRAMI/DERS İÇERİKLERİ boş;
  haftalar/ek sayfalar/rubrikler/takvim `extendedProps`/profil hiç okunmuyordu) →
  **kapandı (Görev 2)**: hepsi yeniden yazılan biçimlendiricide.
- Ödevler 200 karakterde kesikti, notlar geçen yılınkiydi → **kapandı (Görev 2,
  canlı araçlar üzerinden)**: BM25'in kendi metni hâlâ 200 karakterde kesiliyor
  (bu değişmedi — o yalnız arama isabeti), ama birincil yol artık `odev_listesi`
  (tam metin) ve `notlar` (önceki öğretim yılını açıkça etiketleyen) araçları;
  istem bu araçları önce çağırmayı söylüyor.
- PDF 120 sayfa → **kapandı (Görev 1)**, taranmış PDF/ZIP/XLSX/görsel OCR'ı →
  **ertelendi** (yukarıdaki gibi, bu planın kapsamı dışında).
- `portal_cookies.json`, `book_progress.json`, `crontab`, `.sync_zamanlama.json`,
  `*.pid` indekse sızıyordu → **kapandı (Görev 1)**: hepsi artık
  `DEFAULT_EXCLUDED_FILE_PATTERNS`'te (`*cookie*`, `book_progress.json`,
  `crontab*`, `.sync_zamanlama.json`, `*.pid`).
- 260 karakterlik snippet, Türkçe büyük/küçük harf hatası ("İngilizce" →
  `['i','ngilizce']`), "ders programı yarın" → `sync.log.1`, "İngilizce ödevi" →
  `homework_first_seen.json` → **kapandı (Görev 1)**: `turkce_kucult_katla` İ/I
  çevirisini `.lower()`'dan önce yapıyor; `sync.log.1` ve `homework_first_seen.json`
  artık dışlanıyor. Atıf snippet'i hâlâ 260 karakter (kasıtlı — kısa önizleme);
  `ogrenci_verisi_ara` artık isabet başına ≤1.200/toplam ≤3.900 karakterlik tam
  metin döndürüyor, snippet'in yerini değil, tam metin ihtiyacını karşılıyor.

**§3 Asistanın ulaşamadığı pano uçları**
- `/api/schedule`, `/api/calendar/unified` → **kapandı (Görev 2)**: `ders_programi`,
  `takvim`. Unified'ın ÖGEP/takım/özel ders birleşimi de `takvim` üzerinden gelir;
  yalnız unified'ın kendi ders-çizme hatası (bkz. CLAUDE.md "Panonun bilinen
  sorunları") `takvim`'i de etkiler — `ders_programi` ayrı bir Python portu
  olduğundan bu hatadan bağımsız çalışır.
- `/api/content`, `/api/content/weeks` → **kapandı (Görev 2)**: `ders_icerigi`.
- `/api/exams` (yalnız dolaylı, sınıflandırma dashboard_api'de) → **kapandı
  (Görev 2)**: `sinavlar` aynı `_sinav_listesi()`'ni okur; sınıflandırmanın
  dashboard_api'de kalması kasıtlı (tek kaynak, asistan onu kopyalamıyor).
  `relatedContent`'in her zaman boş gelmesi ayrı, önceden bilinmeyen bir hataydı
  → **ertelendi** (CLAUDE.md "Panonun bilinen sorunları"; bu plan dashboard
  hatalarını düzeltmiyor, asistanın veri erişimini düzeltiyor).
- `/api/grades` (rubriksiz) → **kapandı (Görev 2)**: `notlar` rubrikleri de okur.
- `/api/pages` → **kapandı (Görev 2)**: `_fmt_scraped_data`'nın ek sayfalar bloğu +
  `ogrenci_verisi_ara`. `/api/sebit` → **kapandı (Görev 3)**. `/api/private-lessons`
  → **kapandı (Görev 2, `takvim` üzerinden)**. `/api/books*` → **kapandı (Görev 3,
  `kitap_ara`)**. `/api/progress/a3k` → **kapandı (Görev 3, `platform_ilerlemesi`)**.
- `/api/homework` (SEBİT hariç tam) → **kapandı (Görev 3)**: SEBİT bölümü eklendi.
- `/api/modules` → değişmedi, zaten kapalıydı (alt proje 5, bu plandan önce).

**§4 MCP kapsamı — 27 araçtan 9'u izinli**
- `get_curriculum_program`, `get_subject`, `list_videos`/`get_video`, `kb_get` →
  **kapandı (Görev 4)**: `program_getir`, `ders_bilgisi`, `video_listele`/
  `video_getir`, `oer_getir`. maarif-mufredat artık 11 araç, egitim-kaynak 3
  (`oer_ara`, `oer_kazanima_gore`, `oer_getir`) — üçü de `TOOL_ALLOWLIST`'te ve
  uzak sunucu onları listelediği sürece otomatik ilan ediliyor. `oer_kazanima_gore`
  (`kb_for_outcome`) ve `kazanim_listele` (`list_learning_outcomes`) zaten izinliydi
  (denetimden önce) ama Görev 6'nın ilk halinde istemde hiç yönlendirme satırı
  taşımıyorlardı — declared-ama-unrouted, review bulgusu (Önemli) → **kapandı
  (fix round 1)**: ikisi de artık kendi `→` satırına sahip ve
  `tests/test_assistant_core.py::test_system_prompt_routing_names_every_declared_tool_exactly_once`
  bunu, `TOOL_ALLOWLIST`'i canlı okuyarak, her araç için doğruluyor.

**§5 `get_figure` görselleri**
- Görsellerin ne modele ne arayüze ulaşmaması → **kapandı (Görev 4)**:
  `ToolOutcome.images` → `chat_with_tools` gerçek görsel bloğu (≤2, boyut/biçim
  filtreli) → model artık görüyor; `/api/assistant/figure/<id>` + `SourcePanel`
  küçük önizleme → okur da görüyor.

**§6 Diğer kaynaklar**
- ted-mcp federasyonu (anamnesis, pexels, minimax, comfyui, tr-literatur, openalex)
  → **ertelendi**: bu plan pano asistanını bu federasyona bağlamadı; kapsam dışı.
- Akademik Takvim (portalın kendisi reddediyor) → **ertelendi**: scraper/portal
  erişim kısıtı, asistanın veri erişimi düzeltmesiyle çözülmez.
- Google Drive arşivi → **ertelendi**: erişim yolu hâlâ yok, kapsam dışı.
- EBA/MEBİ/SEBİTV indirmeleri geçen yıla ait → **kısmen ertelendi**: `video_oner`
  artık en azından katalogun kendi toplanma tarihini dürüstçe söylüyor (Görev 3
  fix round 1); indirmelerin kendisi bu planda yeniden çalıştırılmadı.
