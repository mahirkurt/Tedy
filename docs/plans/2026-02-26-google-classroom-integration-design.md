# Google Classroom Integration Design

**Date:** 2026-02-26
**Status:** Approved

## Goal

TED portalından çekilen tüm eğitim verilerini Google Classroom'a yazmak. Işık (isikkurtx@gmail.com) için her ders ayrı bir kurs olarak yapılandırılır. Modül bağımsız çalışabilir — ileride Calendar/Tasks'ı tamamen değiştirme opsiyonu korunur.

## Approach

Yaklaşım B: Ayrı `src/sync_to_classroom.py` modülü. Mevcut sync pipeline'ına ek bir faz olarak eklenir ama standalone da çalışır. Ortak utility'ler (`normalize_course`, `_api_call_with_retry`) mevcut `sync_to_google.py`'den import edilir.

## 1. Course Lifecycle

- `ders_programi`'ndaki benzersiz ders isimleri `normalize_course()` ile standartlaştırılır
- Her ders için bir Classroom kursu oluşturulur: `Course(name="Matematik", section="TED Rönesans 2025-26")`
- İlk çalışmada kurslar yaratılır, sonraki çalışmalarda mevcut kurslar bulunup kullanılır
- `isikkurtx@gmail.com` her kursa "STUDENT" rolüyle otomatik davet edilir
- Dersle eşleşmeyen veriler için "TED Genel" kursu oluşturulur
- Kurs mapping: `output/classroom_courses.json` — `{normalized_name: course_id}`

## 2. Data Mapping

| TED Verisi | Classroom Kaynağı | Detay |
|---|---|---|
| **odevlerim** | `courseWork` (ASSIGNMENT) | Başlık, açıklama, teslim tarihi, Drive link ekleri |
| **ders_icerikleri** | `courseWorkMaterial` | Haftalık ders notu başlığı + içerik |
| **gelisim_raporu** | `courseWork` (SHORT_ANSWER) + grade | Sınav adı, maxPoints, draftGrade |
| **duyurular** | `announcement` | Tüm kurslara veya TED Genel'e |
| **takvim** | `announcement` | Sınav tarihleri → ilgili ders, genel → tüm kurslar |
| **takim_calismalari** | `announcement` | İlgili derse veya TED Genel'e |
| **ogep** | `announcement` | TED Genel kursuna |

Ödev ekleri mevcut Drive upload mantığıyla yüklenir, Classroom'a `Link` material olarak eklenir.

## 3. Sync Logic

**Idempotent upsert + update:**

Dedup anahtarları:
- courseWork (ödev): `course_id` + ödev başlığı
- courseWork (sınav): `course_id` + sınav adı
- courseWorkMaterial: `course_id` + hafta başlığı
- announcement: `course_id` + metnin ilk 100 karakteri

Akış (her 15 dk cron'da):
1. `output/scraped_data.json` oku
2. `output/classroom_courses.json`'dan kurs mapping yükle
3. Yeni dersler varsa kurs oluştur + öğrenci davet + mapping güncelle
4. Her kurs için mevcut Classroom içeriklerini list API ile çek
5. Dedup anahtarıyla karşılaştır: yeni → create, değişmiş → patch, aynı → skip
6. Sonuçları `output/classroom_sync.json`'a yaz

State tracking:
- `output/classroom_courses.json` — kurs name→id mapping
- `output/classroom_sync.json` — `{dedup_key: {classroom_id, last_hash}}`
- Hash karşılaştırması ile gereksiz API çağrıları önlenir

Retry: `_api_call_with_retry` — 429/500/503'te 3 deneme, exponential backoff.

## 4. Module Structure

File: `src/sync_to_classroom.py`

```
sync_to_classroom.py
├── get_classroom_service(creds)
├── ensure_courses(service, ders_listesi)
├── sync_odevler(service, courses, data)
├── sync_ders_icerikleri(service, courses, data)
├── sync_notlar(service, courses, data)
├── sync_duyurular(service, courses, data)
├── load_sync_state() / save_sync_state()
├── compute_hash(item)
└── main()
```

Standalone:
```bash
python src/sync_to_classroom.py
python src/sync_to_classroom.py --reset-courses
```

OAuth scopes (google_auth.py SCOPES'a eklenir):
- `classroom.courses`
- `classroom.coursework.students`
- `classroom.announcements`
- `classroom.rosters`
- `classroom.profile.emails`

run_sync.py entegrasyonu:
```python
# Phase 4 - Classroom sync
try:
    from sync_to_classroom import main as sync_classroom
    sync_classroom(scraped_data)
except Exception as e:
    errors.append(f"Classroom sync: {e}")
```

Ortak bağımlılıklar: `normalize_course()` ve `_api_call_with_retry()` mevcut `sync_to_google.py`'den import edilir.

## 5. Error Handling & Edge Cases

Hata izolasyonu: Bir kursun sync'i başarısız olursa diğerleri devam eder.

| Durum | Davranış |
|---|---|
| Öğrenci daveti zaten var | API 409 → atla |
| Kurs ismi değişti | Eski kurs orphan kalır, yeni oluşur — `--reset-courses` ile temizlenir |
| Ödev eki Drive'da yok | Eksiz oluşturulur, log uyarısı |
| `scraped_data.json` kısmen boş | Mevcut tipler sync edilir, eksikler atlanır |
| API quota aşımı | 3x retry + backoff, sonraki döngüde tekrar |
| Token expired | Mevcut refresh ile otomatik yenilenir |
| Davet kabul edilmemiş | İçerik oluşturmayı engellemez |

Health check: `output/health.json`'a `classroom_synced`, `classroom_errors` alanları eklenir.
