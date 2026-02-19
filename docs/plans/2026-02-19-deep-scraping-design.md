# Deep Scraping Design - EBA, MEBI, SEBİTV Ek İçerikler

**Tarih:** 2026-02-19
**Yaklaşım:** B - Her biri için ayrı script (mevcut scraper'lara dokunmadan)

## Kapsam

| # | Platform | İçerik | Çıktı | Script |
|---|----------|--------|-------|--------|
| 1 | SEBİTV | 413 etkileşimli kaynak | Statik arşiv ZIP + soru bankası JSON → Drive | `scrape_sebitv_interactive.py` |
| 2 | MEBI | ~2,355 quiz | Soru JSON → Drive | `scrape_mebi_quizzes.py` |
| 3 | EBA | Ders videoları | Video MP4 → Drive | `scrape_eba_videos.py` |

MEBI oyunları kapsam dışı.

---

## 1. SEBİTV Etkileşimli Arşiv

**Dosya:** `src/scrape_sebitv_interactive.py`

**Girdi:** `output/sebitv_discovered.json` (413 interactive kaynak, fileType="zip", duration=0)

**Akış:**
1. SEBİTV Selenium login → cookie transfer to requests.Session
2. `sebitv_discovered.json`'dan interactive kaynakları filtrele
3. Her kaynak için:
   - `get_repo_type()` → REPOSITORY tipi (hex)
   - `_content_base()` → base URL
   - `dataLevel.html` parse → dosya listesi, asset referansları
   - `SkipIntroDataJSON.js` varsa → soru bankası JSON çıkar
   - Tüm statik dosyaları indir (HTML, JS, CSS, görseller)
4. Drive'a yükle:
   - Soru bankası: `SEBİTV Soru Bankaları/{Ders}/{Ünite}/{konu}.json`
   - Statik arşiv: `SEBİTV Etkileşimli/{Ders}/{Ünite}/{başlık}.zip`

**Tracker:** `output/sebitv_interactive_uploaded.json`

**Dosya keşfi:** `dataLevel.html` asset referansları + bilinen pattern'ler (resources/, sco1/)

---

## 2. MEBI Quizler

**Dosya:** `src/scrape_mebi_quizzes.py`

**Akış:**
1. EBA Selenium login → MEBI navigate
2. Dersler → Üniteler → Konular hiyerarşisi (mevcut pattern)
3. Her konu sayfasında quiz butonlarını keşfet (3 tip: ön/ara/son değerlendirme)
4. Quiz verilerini çıkar (DOM veya API'den)
5. JSON formatı:
   ```json
   {
     "course": "Matematik",
     "unit": "Ünite 1",
     "topic": "Konu Adı",
     "quizType": "on_degerlendirme",
     "questions": [{"text": "...", "options": [...], "correct": "B"}]
   }
   ```
6. Drive'a yükle: `MEBI Quizler/{Ders}/{Ünite}/{konu}-{tip}.json`

**Tracker:** `output/mebi_quizzes_uploaded.json`

**Not:** Quiz yükleme mekanizması önce discover script ile keşfedilecek.

---

## 3. EBA Ders Videoları

**Dosya:** `src/scrape_eba_videos.py`

**Akış:**
1. EBA Selenium login (mevcut pattern)
2. Ders listesi keşfi (AngularJS scope)
3. İçerik sayfalarına navigate → video embed linkleri çıkar
4. CDN URL resolve (mevcut `get_cdn_url()` pattern)
5. requests ile indir → Drive'a yükle

**Drive yapısı:** `EBA Ders Videoları/{Ders}/{Ünite}/{video-adı}.mp4`

**Tracker:** `output/eba_videos_uploaded.json`

**Not:** Video embed yapısı önce discover script ile keşfedilecek.

---

## Ortak Pattern'ler

- **Login:** Selenium headless Chrome (mevcut options)
- **Session:** Selenium cookies → requests.Session transfer
- **Drive:** `get_services()` + `_get_or_create_folder()` (sync_to_google.py'den import)
- **Upload:** <100MB MediaInMemoryUpload, >=100MB chunked 50MB resumable
- **Tracker:** JSON dosyası, key=resourceId/uuid, idempotent
- **Discovery cache:** JSON dosyası, 2-faz (keşif → indirme)

## Uygulama Sırası

1. SEBİTV etkileşimli (hazır data var, keşif gereksiz)
2. MEBI quizler (discover + scraper)
3. EBA videolar (discover + scraper)
