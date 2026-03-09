# Işık Dashboard — Tasarım Belgesi

**Tarih:** 2026-03-07
**Amaç:** Işık'ın anlık ders, ödev, sınav, etkinlik ve ilerleme durumunu tek panelden gösteren canlı dashboard.

## Mimari

```
Flask (Python backend)            React SPA (frontend)
├── /api/schedule      ──────►    ├── TodaySchedule
├── /api/homework      ──────►    ├── WeeklySchedule
├── /api/sebit         ──────►    ├── HomeworkTracker (countdown)
├── /api/grades        ──────►    ├── GradeTable
├── /api/calendar      ──────►    ├── CalendarEvents
├── /api/teams         ──────►    ├── TeamActivities
├── /api/ogep          ──────►    ├── (merged with Teams)
├── /api/content       ──────►    ├── CourseContent
├── /api/announcements ──────►    ├── Announcements
├── /api/progress/ec   ──────►    ├── PlatformProgress
├── /api/progress/a3k  ──────►    │
├── /api/health        ──────►    └── SyncStatus (header)
└── serves static build
```

- **Backend:** `src/dashboard_api.py` — Flask app, JSON dosyalarını okur, `normalize_course()` kullanır
- **Frontend:** `dashboard/` — Vite + React + TypeScript + `@carbon/react`
- **Auto-refresh:** 5 dakikada bir tüm API'den güncel veri çeker

## UI Layout (9 Bölüm)

1. **Header** — TED Rönesans logosu, Işık Kurt 6/C, sync durumu
2. **Bugünün Dersleri** — Yatay kart şeridi, aktif ders vurgusu (mavi arka plan)
3. **Haftalık Program** — Tam tablo, bugünün sütunu vurgulanır
4. **Ödevler & Geri Sayım** — Portal + SEBİT ödevleri, progress bar, countdown timer, durum etiketleri
5. **Notlar / Sınav Sonuçları** — DataTable: ders başına 3 sınav + 3 performans notu
6. **Platform İlerleme** — EnglishCentral, Achieve3000, SEBİT ilerleme çubukları
7. **Takvim & Yaklaşan Etkinlikler** — Kişisel takvim, sınavlar, önemli tarihler
8. **Takım Çalışmaları + ÖGEP** — Academy+ aktiviteleri, ÖGEP oturumları, katılım durumu
9. **Ders İçerikleri** — Öğretmen notları/içerikleri, ders bazlı tab yapısı
10. **Duyurular** — Son okul duyuruları, tarih sıralı

## TED × Carbon Açık Tema (Light — g10)

```scss
// Arkaplan
$background:        #F4F4F4;   // Carbon gray-10
$layer-01:          #FFFFFF;   // Beyaz kartlar
$layer-02:          #E0E0E0;   // Carbon gray-20

// TED Marka
$ted-header-bg:     #002D9C;   // Carbon Blue-80 — lacivert header
$ted-header-text:   #FFFFFF;
$ted-accent:        #DA1E28;   // Carbon Red-60 — TED kırmızısı

// Metin
$text-primary:      #161616;   // Carbon gray-100
$text-secondary:    #525252;   // Carbon gray-70

// İnteraktif
$interactive:       #0F62FE;   // Carbon Blue-60
$interactive-hover: #0043CE;   // Carbon Blue-70

// Durum
$support-success:   #198038;   // Green-70 — tamamlandı
$support-warning:   #F1C21B;   // Yellow-30 — yaklaşıyor
$support-error:     #DA1E28;   // Red-60 — gecikmiş/acil
$support-info:      #0043CE;   // Blue-70 — devam ediyor

// Vurgular
$highlight-active:  #D0E2FF;   // Blue-10 — aktif ders
$highlight-today:   #0F62FE;   // Blue-60 — bugünün sütun çerçevesi
$progress-bar:      #0F62FE;   // Blue-60
$border-subtle:     #E0E0E0;   // gray-20
```

## Durum Etiketleri

| Durum | Renk | Carbon Tag |
|-------|------|------------|
| Tamamlandı | Yeşil | `<Tag type="green">` |
| Devam Ediyor | Mavi | `<Tag type="blue">` |
| Yaklaşıyor (< 3 gün) | Sarı | `<Tag type="warm-gray">` + custom |
| Gecikmiş | Kırmızı | `<Tag type="red">` |
| Acil (< 24 saat) | Kırmızı animated | Custom pulse animation |

## Dosya Yapısı

```
TED/
├── src/
│   └── dashboard_api.py          # Flask backend
├── dashboard/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── theme/
│       │   └── ted-theme.scss
│       ├── hooks/
│       │   └── useApi.ts
│       ├── components/
│       │   ├── DashboardHeader.tsx
│       │   ├── TodaySchedule.tsx
│       │   ├── WeeklySchedule.tsx
│       │   ├── HomeworkTracker.tsx
│       │   ├── GradeTable.tsx
│       │   ├── PlatformProgress.tsx
│       │   ├── CalendarEvents.tsx
│       │   ├── TeamActivities.tsx
│       │   ├── CourseContent.tsx
│       │   └── Announcements.tsx
│       └── utils/
│           ├── countdown.ts
│           └── formatters.ts
```

## API Endpoint'leri

| Endpoint | Kaynak Dosya | Veri |
|----------|-------------|------|
| `GET /api/schedule` | `scraped_data.json → ders_programi` | Haftalık program + bugünün dersleri |
| `GET /api/homework` | `scraped_data.json → odevlerim` | Portal ödevleri |
| `GET /api/sebit` | `sebit_homework.json` | SEBİT ödevleri |
| `GET /api/grades` | `scraped_data.json → gelisim_raporu` | Sınav/performans notları |
| `GET /api/calendar` | `scraped_data.json → takvim` | Takvim olayları |
| `GET /api/teams` | `scraped_data.json → takim_calismalari + ogep` | Takım + ÖGEP |
| `GET /api/content` | `scraped_data.json → ders_icerikleri` | Ders içerikleri |
| `GET /api/announcements` | `scraped_data.json → duyurular` | Okul duyuruları |
| `GET /api/progress/ec` | `englishcentral_progress.json` | EC ilerleme |
| `GET /api/progress/a3k` | `achieve3000_progress.json` | A3K ilerleme |
| `GET /api/health` | `health.json` | Sync durumu |

## Bağımlılıklar

**Backend:** `flask`, `flask-cors`
**Frontend:** `react`, `@carbon/react`, `@carbon/icons-react`, `sass`, `vite`, `typescript`
