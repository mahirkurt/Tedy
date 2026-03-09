# Dashboard Turkish Text & ADHD-Friendly Layout Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all 26 ASCII Turkish text issues and redesign dashboard layout for spacious, ADHD-friendly readability with mobile support.

**Architecture:** Two-pass approach — first fix all hardcoded text strings across 12 files, then restructure layout with increased spacing, visual breathing room, and mobile-first responsive design. No structural refactoring — same components, better text and spacing.

**Tech Stack:** React 19, Carbon Design System, SCSS, IBM Plex Sans (Google Fonts CDN)

---

### Task 1: Fix Turkish characters in utility files

**Files:**
- Modify: `dashboard/src/utils/countdown.ts:16`
- Modify: `dashboard/src/utils/formatters.ts:26-30`

**Step 1: Fix countdown.ts**

```typescript
// Line 16: Change
text: 'Suresi doldu'
// To:
text: 'Süresi doldu'
```

**Step 2: Fix formatters.ts status labels**

```typescript
// Lines 26-30: Change
case 'Yapti': return { label: 'Tamamlandi', type: 'green' }
case 'Yapmadi': return { label: 'Yapilmadi', type: 'red' }
case 'Eksik': return { label: 'Eksik', type: 'warm-gray' }
case 'Degerlendirilmemis': return { label: 'Bekliyor', type: 'blue' }
// To:
case 'Yapti': return { label: 'Tamamlandı', type: 'green' }
case 'Yapmadi': return { label: 'Yapılmadı', type: 'red' }
case 'Eksik': return { label: 'Eksik', type: 'warm-gray' }
case 'Degerlendirilmemis': return { label: 'Bekliyor', type: 'blue' }
```

Note: The `case` keys stay ASCII — they match backend data. Only `label` display values get proper Turkish.

**Step 3: Verify build**

Run: `cd dashboard && npm run build`
Expected: Build succeeds

**Step 4: Commit**

```
fix: correct Turkish characters in utility display text
```

---

### Task 2: Fix Turkish characters in App.tsx and LoginPage.tsx

**Files:**
- Modify: `dashboard/src/App.tsx:25`
- Modify: `dashboard/src/components/LoginPage.tsx:66,113,122,146`

**Step 1: Fix App.tsx loading text**

```
Yukleniyor... → Yükleniyor...
```

**Step 2: Fix LoginPage.tsx (4 strings)**

```
Line 66:  Giris basarisiz → Giriş başarısız
Line 113: Ogrenci Takip Paneli → Öğrenci Takip Paneli
Line 122: Devam etmek icin Google hesabinizla giris yapin. → Devam etmek için Google hesabınızla giriş yapın.
Line 146: Sadece yetkili aile uyeleri giris yapabilir. → Sadece yetkili aile üyeleri giriş yapabilir.
```

**Step 3: Verify build**

Run: `cd dashboard && npm run build`

**Step 4: Commit**

```
fix: correct Turkish characters in App and LoginPage
```

---

### Task 3: Fix Turkish characters in DashboardHeader.tsx

**Files:**
- Modify: `dashboard/src/components/DashboardHeader.tsx:13-17,63`

**Step 1: Fix time-ago strings and logout**

```
Az once → Az önce
dk once → dk önce
saat once → saat önce
gun once → gün önce
Cikis → Çıkış
```

**Step 2: Verify build**

**Step 3: Commit**

```
fix: correct Turkish characters in DashboardHeader
```

---

### Task 4: Fix Turkish characters in HomeworkTracker.tsx

**Files:**
- Modify: `dashboard/src/components/HomeworkTracker.tsx:47,82,93`

**Step 1: Fix 3 strings**

```
Odevler & Geri Sayim → Ödevler & Geri Sayım
Suresi doldu → Süresi doldu
SEBIT Dijital Odevler → SEBİT Dijital Ödevler
```

**Step 2: Verify build, commit**

```
fix: correct Turkish characters in HomeworkTracker
```

---

### Task 5: Fix Turkish characters in remaining components

**Files:**
- Modify: `dashboard/src/components/TodaySchedule.tsx:57,65,79,101`
- Modify: `dashboard/src/components/WeeklySchedule.tsx:48,60`
- Modify: `dashboard/src/components/Announcements.tsx:18`
- Modify: `dashboard/src/components/TeamActivities.tsx:17,48`
- Modify: `dashboard/src/components/CalendarEvents.tsx:22,25`
- Modify: `dashboard/src/components/CourseContent.tsx:27,30`
- Modify: `dashboard/src/components/PlatformProgress.tsx:27`

**Step 1: Fix TodaySchedule (4 strings)**

```
Yukleniyor... → Yükleniyor...
Bugun ders yok → Bugün ders yok
Bugunun Dersleri → Bugünün Dersleri
Simdi → Şimdi
```

**Step 2: Fix WeeklySchedule (2 strings)**

```
Yukleniyor... → Yükleniyor...
Haftalik Program → Haftalık Program
```

**Step 3: Fix Announcements (1 string)**

```
Okul Duyurulari → Okul Duyuruları
```

**Step 4: Fix TeamActivities (2 strings)**

```
Takim Calismalari & OGEP → Takım Çalışmaları & ÖGEP
OGEP Oturumlari → ÖGEP Oturumları
```

**Step 5: Fix CalendarEvents (2 strings)**

```
Takvim & Yaklasan Etkinlikler → Takvim & Yaklaşan Etkinlikler
Yaklasan etkinlik yok → Yaklaşan etkinlik yok
```

**Step 6: Fix CourseContent (2 strings)**

```
Ders Icerikleri → Ders İçerikleri
Ders icerikleri → Ders içerikleri
```

**Step 7: Fix PlatformProgress (1 string)**

```
Platform Ilerleme → Platform İlerleme
```

**Step 8: Verify build**

Run: `cd dashboard && npm run build`

**Step 9: Commit**

```
fix: correct Turkish characters in all remaining components
```

---

### Task 6: ADHD-friendly layout — increase spacing and visual hierarchy

**Files:**
- Modify: `dashboard/src/theme/ted-theme.scss`
- Modify: `dashboard/src/App.tsx`

**Step 1: Update SCSS for spacious layout**

Add to `ted-theme.scss`:
```scss
// ADHD-friendly spacing
.dashboard-card {
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.5rem;  // was 1rem
  border-radius: 6px;     // was 0
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
}

.dashboard-card h4 {
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.01em;
}

// Breathing room between grid sections
.cds--css-grid-column {
  margin-bottom: 0.5rem;
}

// Mobile: full-width cards with more padding
@media (max-width: 671px) {
  .cds--content {
    padding: 3.5rem 0.5rem 2rem !important;
  }

  .dashboard-card {
    margin-bottom: 1rem;
    padding: 1rem;
  }
}
```

**Step 2: Update App.tsx Content padding**

```typescript
// Change padding from '3.5rem 1rem 2rem' to:
<Content style={{ padding: '3.5rem 1.5rem 2rem' }}>
```

**Step 3: Verify build**

**Step 4: Commit**

```
style: ADHD-friendly spacing with rounded cards and breathing room
```

---

### Task 7: Mobile responsiveness improvements

**Files:**
- Modify: `dashboard/src/theme/ted-theme.scss`
- Modify: `dashboard/src/components/GradeTable.tsx` (table overflow)
- Modify: `dashboard/src/components/WeeklySchedule.tsx` (table overflow)

**Step 1: Add mobile table handling in SCSS**

```scss
@media (max-width: 671px) {
  // Horizontal scroll for wide tables
  .cds--data-table-container {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  // Stack homework items tighter
  .dashboard-card .cds--tile {
    padding: 0.5rem 0.75rem;
  }

  // Smaller section titles on mobile
  .dashboard-card h4 {
    font-size: 0.9375rem;
  }
}
```

**Step 2: Verify build**

**Step 3: Test mobile via Playwright**

Open dashboard at localhost:8085, resize to 375x812 (iPhone), take screenshot.

**Step 4: Commit**

```
style: improve mobile responsiveness for tables and cards
```

---

### Task 8: Build, deploy, and verify

**Step 1: Full build**

```bash
cd dashboard && npm run build
```

**Step 2: Restart service**

```bash
systemctl --user restart ted-dashboard
```

**Step 3: Visual verification via Playwright**

Navigate to tedy.online, take screenshots at desktop (1440px) and mobile (375px) widths. Verify:
- All Turkish characters render correctly
- Cards have rounded corners and spacing
- Mobile layout stacks properly
- No horizontal overflow on mobile

**Step 4: Final commit with all changes**

```
feat: dashboard Turkish text fixes and ADHD-friendly layout
```
