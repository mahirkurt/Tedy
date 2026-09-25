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
