# Scraping Reliability: Layered Defense Design

**Date**: 2026-03-09
**Approach**: Katmanlı Savunma — her seviyede bağımsız koruma, bir katman düşerse diğeri tutar.

## Problem

Scraping sistemi ~70-75% güvenilir. Ana sorunlar:
- 146 `time.sleep()` vs 1 explicit wait — SPA yavaşladığında sessiz veri kaybı
- CAPTCHA OCR ~70% başarı, 5 deneme sonrası tamamen duruyor
- Boş veri "başarılı" sayılıyor — 0 takvim olayı scrape edilse bile `success: true`
- Health check sadece `success: bool` tutuyor — detay yok
- Her 15 dk'da full login gereksiz

## Design Decisions

- **Staleness tolerance** asıl odak — sync sıklığı değil, fail olduğunda eski verinin ne kadar süre kabul edilebilir olduğu
- **Dashboard health banner** yeterli monitoring — push notification gereksiz
- **Session persistence + OCR iyileştirme** — login sayısını minimize et, gerektiğinde daha iyi OCR

---

## Layer 1: Session Persistence

**New file**: `src/session_manager.py`

Cookie'leri diske kaydet, geçerliyse yeniden kullan.

### Flow
```
Sync başlangıcı
  → output/portal_cookies.json var mı?
    → Evet → requests.Session'a yükle → test GET (profil sayfası)
      → 200 OK → Selenium'a da cookie'leri yükle → login atla
      → 401/redirect → cookie'ler expired → normal login akışı
    → Hayır → normal login akışı
  → Login başarılı → cookie'leri output/portal_cookies.json'a kaydet
```

### Key Decisions
- Cookie dosyası `output/portal_cookies.json` (gitignored)
- Geçerlilik testi: GET ile authenticated sayfa → redirect varsa expired
- `login.py`'deki `login()` fonksiyonu `try_cached_session()` ile wrap edilir
- Fallback: mevcut CAPTCHA login korunur

### CAPTCHA OCR Improvement (login gerektiğinde)
- Image preprocessing: grayscale → contrast artır → threshold
- ddddocr çıktısını regex ile doğrula (sadece 4-6 haneli rakam)
- Her denemede CAPTCHA yenile (mevcut: aynı CAPTCHA'yı tekrar deniyor)

---

## Layer 2: Explicit Waits + Retry

**New file**: `src/scrape_helpers.py`

### Utilities

**`wait_for(driver, locator, timeout=15)`**
```python
# Önce:  time.sleep(3); driver.find_element(By.CSS_SELECTOR, "#tablo")
# Sonra: wait_for(driver, (By.CSS_SELECTOR, "#tablo"))
```
WebDriverWait + EC.presence_of_element_located. Element yoksa TimeoutError fırlatır.

**`wait_for_js(driver, js_expr, timeout=15)`**
```python
# Önce:  time.sleep(3); driver.execute_script("return window.calendar.getEvents()")
# Sonra: wait_for_js(driver, "window.calendar && window.calendar.getEvents")
```
FullCalendar yüklenene kadar bekler — takvim event kaybının root cause'u.

**`@retry_on_stale(max=3)`**
StaleElementReferenceException ve NoSuchElementException yakalayıp tekrar dener.

### Migration Strategy
Tüm sleep'leri tek seferde değiştirme. Öncelik sırasıyla:
1. `scrape_takvim()` — en kırılgan
2. `scrape_odevlerim()` — en kritik veri
3. `scrape_ders_programi()` — haftalık
4. Diğerleri sırayla

---

## Layer 3: Data Validation

**New file**: `src/data_validator.py`

Scrape sonrası minimum threshold kontrolü.

### Validation Rules
```python
SECTION_RULES = {
    "odevlerim":         {"min_rows": 5,  "required_keys": ["Ders Adı", "Ödev Başlığı"]},
    "ders_programi":     {"min_rows": 1,  "required_keys": ["schedule"]},
    "takvim":            {"min_items": 1},
    "gelisim_raporu":    {"min_grades": 5, "required_keys": ["Ders"]},
    "ders_icerikleri":   {"min_items": 1},
    "takim_calismalari": {"min_items": 0},
    "ogep":              {"min_items": 0},
    "duyurular":         {"min_items": 1},
}
```

### `validate_scraped_data(new_data, previous_data)`
1. Minimum threshold kontrol
2. Önceki scrape ile karşılaştır — %50'den fazla düşüş → warning
3. Required key'ler kontrol

### Behavior
- **fail** → eski `scraped_data.json` korunur, yeni veri kaydedilmez
- **warning** → yeni veri kaydedilir, health'e uyarı eklenir
- **pass** → normal akış

---

## Layer 4: Rich Health Metrics

**Modified file**: `src/run_sync.py` health section

### New health.json Structure
```json
{
  "timestamp": "2026-03-09T12:15:00",
  "success": true,
  "duration_seconds": 45,
  "scrape_errors": [],
  "validation_warnings": ["takvim: 17→2, %88 düşüş"],
  "login": {
    "method": "cached_session",
    "captcha_attempts": 0
  },
  "sections": {
    "odevlerim":       {"count": 43, "prev_count": 43, "status": "ok"},
    "ders_programi":   {"count": 1,  "prev_count": 1,  "status": "ok"},
    "takvim":          {"count": 2,  "prev_count": 17, "status": "warning"},
    "gelisim_raporu":  {"count": 11, "prev_count": 11, "status": "ok"},
    "ders_icerikleri": {"count": 8,  "prev_count": 8,  "status": "ok"},
    "takim_calismalari": {"count": 5, "prev_count": 5, "status": "ok"},
    "ogep":            {"count": 11, "prev_count": 11, "status": "ok"},
    "duyurular":       {"count": 5,  "prev_count": 5,  "status": "ok"}
  },
  "sync": {
    "calendar_added": 0,
    "calendar_skipped": 12,
    "classroom_errors": []
  },
  "staleness": {
    "last_successful_full_scrape": "2026-03-09T12:00:00",
    "stale_sections": []
  }
}
```

### New Fields
- `login.method`: `"cached_session"` | `"captcha_login"` | `"failed"`
- `sections[].status`: `"ok"` | `"warning"` | `"error"` | `"skipped"`
- `staleness.stale_sections`: Validation fail edip eski veriyle kalan bölümler

---

## Layer 5: Dashboard Health Banner

**Modified file**: `dashboard/src/components/DashboardHeader.tsx`

### Header Tag Behavior
- **Yeşil** `"5 dk önce"` → her şey ok
- **Sarı** `"2 saat önce · 1 uyarı"` → validation warning var
- **Kırmızı** `"10 gün önce · 3 hata"` → sync fail veya çok eski

### Click → Popover Detail
```
Son Sync: 09.03.2026 12:15 (5 dk önce)
Login: Kayıtlı oturum kullanıldı
Süre: 45 saniye

  Ödevler          43 öğe    ✓
  Ders Programı     1 hafta  ✓
  Takvim            2 öğe    ⚠ (17→2, %88 düşüş)
  Notlar           11 ders   ✓
  ...
```

### Implementation
- `HealthData` TypeScript interface genişletilir
- Carbon `Popover` component eklenir
- Status ikonları: ✓ ok, ⚠ warning, ✗ error, — skipped

---

## Files Summary

| File | Action | Layer |
|------|--------|-------|
| `src/session_manager.py` | Create | 1 - Session |
| `src/login.py` | Modify | 1 - Session + CAPTCHA |
| `src/scrape_helpers.py` | Create | 2 - Waits/Retry |
| `src/scrape_all.py` | Modify | 2 - Migrate sleeps |
| `src/data_validator.py` | Create | 3 - Validation |
| `src/run_sync.py` | Modify | 3+4 - Validation + Health |
| `dashboard/src/types.ts` | Modify | 5 - HealthData interface |
| `dashboard/src/components/DashboardHeader.tsx` | Modify | 5 - Health banner |

## Expected Reliability Improvement

| Component | Before | After |
|-----------|--------|-------|
| Login/CAPTCHA | 60-70% | 90-95% (session reuse) |
| Portal scraping | 70-80% | 90-95% (explicit waits) |
| Data validation | 40-50% | 85-90% (threshold + comparison) |
| Error visibility | 50-60% | 90%+ (rich health metrics) |
| **Overall** | **~70-75%** | **~90-95%** |
