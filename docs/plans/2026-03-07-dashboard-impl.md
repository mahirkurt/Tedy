# Işık Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Flask + React SPA dashboard showing Işık's real-time school data (schedule, homework, grades, progress, events, announcements) with IBM Carbon Design System and TED-branded theme.

**Architecture:** Flask backend serves JSON API endpoints reading from `output/*.json` files. React SPA with Vite + TypeScript + `@carbon/react` consumes the API. TED × Carbon light theme (g10 base, Blue-80 header, Red-60 accents).

**Tech Stack:** Python/Flask, React 18, TypeScript, Vite, @carbon/react, Sass

---

### Task 1: Flask Backend — API Server

**Files:**
- Create: `src/dashboard_api.py`

**Step 1: Install Flask dependencies**

Run: `pip install flask flask-cors`

**Step 2: Write the Flask API server**

```python
"""Dashboard API server — serves TED data as JSON endpoints."""
import json
import os
import sys
from datetime import datetime, timedelta
from flask import Flask, jsonify
from flask_cors import CORS

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from src.sync_to_google import normalize_course

app = Flask(__name__)
CORS(app)

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")


def _load_json(filename):
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _scraped():
    return _load_json("scraped_data.json")


# --- Day name mapping for schedule ---
DAY_NAMES = {
    0: "Pazartesi", 1: "Salı", 2: "Çarşamba",
    3: "Perşembe", 4: "Cuma", 5: "Cumartesi", 6: "Pazar"
}


@app.route("/api/schedule")
def schedule():
    data = _scraped()
    weeks = data.get("ders_programi", [])
    today = DAY_NAMES.get(datetime.now().weekday(), "")
    # Return latest week + today indicator
    latest = weeks[-1] if weeks else {}
    return jsonify({"weeks": weeks, "latest": latest, "today": today})


@app.route("/api/homework")
def homework():
    data = _scraped()
    hw = data.get("odevlerim", {})
    rows = hw.get("homework", {}).get("rows", [])
    summary = hw.get("summary", "")
    # Normalize course names
    for r in rows:
        if "Ders Adı" in r:
            r["normalized_course"] = normalize_course(r["Ders Adı"])
    return jsonify({"summary": summary, "homework": rows})


@app.route("/api/sebit")
def sebit():
    data = _load_json("sebit_homework.json")
    return jsonify(data)


@app.route("/api/grades")
def grades():
    data = _scraped()
    gr = data.get("gelisim_raporu", {})
    return jsonify(gr)


@app.route("/api/calendar")
def calendar():
    data = _scraped()
    events = data.get("takvim", [])
    return jsonify({"events": events})


@app.route("/api/teams")
def teams():
    data = _scraped()
    activities = data.get("takim_calismalari", {}).get("activities", {}).get("rows", [])
    ogep = data.get("ogep", {}).get("sessions", {}).get("rows", [])
    return jsonify({"activities": activities, "ogep": ogep})


@app.route("/api/content")
def content():
    data = _scraped()
    return jsonify(data.get("ders_icerikleri", {}))


@app.route("/api/announcements")
def announcements():
    data = _scraped()
    ann = data.get("duyurular", {}).get("announcements", [])
    return jsonify({"announcements": ann})


@app.route("/api/progress/ec")
def progress_ec():
    return jsonify(_load_json("englishcentral_progress.json"))


@app.route("/api/progress/a3k")
def progress_a3k():
    return jsonify(_load_json("achieve3000_progress.json"))


@app.route("/api/health")
def health():
    return jsonify(_load_json("health.json"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8085, debug=True)
```

**Step 3: Test the API**

Run: `python src/dashboard_api.py &`
Run: `curl -s http://localhost:8085/api/health | python3 -m json.tool`
Expected: JSON with `timestamp`, `success` fields
Run: `kill %1`

**Step 4: Commit**

```bash
git add src/dashboard_api.py
git commit -m "feat: add Flask dashboard API server"
```

---

### Task 2: React SPA — Project Scaffold

**Files:**
- Create: `dashboard/` (entire directory via Vite)

**Step 1: Create Vite React TypeScript project**

```bash
cd /mnt/thunderbolt/workspaces/TED
npm create vite@latest dashboard -- --template react-ts
cd dashboard
```

**Step 2: Install Carbon dependencies**

```bash
npm install @carbon/react @carbon/icons-react
npm install -D sass
```

**Step 3: Configure Vite proxy for API**

Edit `dashboard/vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8085'
    }
  }
})
```

**Step 4: Clean default files**

Remove default Vite content from `src/App.tsx`, `src/App.css`, `src/index.css`.

**Step 5: Verify scaffold works**

Run: `cd dashboard && npm run dev -- --host &`
Expected: Vite dev server on http://localhost:3000

**Step 6: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED
git add dashboard/
git commit -m "feat: scaffold React+Vite+Carbon dashboard app"
```

---

### Task 3: TED Theme + Global Styles

**Files:**
- Create: `dashboard/src/theme/ted-theme.scss`
- Modify: `dashboard/src/main.tsx`

**Step 1: Create TED Carbon theme**

```scss
// TED Rönesans × Carbon Light Theme
@use '@carbon/react/scss/themes';
@use '@carbon/react/scss/theme' with (
  $theme: themes.$g10
);
@use '@carbon/react' with (
  $css--default-type: true,
  $css--reset: true
);

// TED Brand overrides
:root {
  // TED Marka
  --ted-header-bg: #002D9C;
  --ted-header-text: #FFFFFF;
  --ted-accent: #DA1E28;

  // Layout
  --ted-page-bg: #F4F4F4;
  --ted-card-bg: #FFFFFF;

  // Status colors
  --status-success: #198038;
  --status-warning: #F1C21B;
  --status-error: #DA1E28;
  --status-info: #0043CE;

  // Highlights
  --highlight-active: #D0E2FF;
  --highlight-today: #0F62FE;
}

body {
  background-color: var(--ted-page-bg);
  margin: 0;
}

// Pulse animation for urgent items
@keyframes pulse-urgent {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.tag-urgent {
  animation: pulse-urgent 1.5s ease-in-out infinite;
}

// Card styling
.dashboard-card {
  background: var(--ted-card-bg);
  border-radius: 0;
  padding: 1rem 1.5rem;
  margin-bottom: 1rem;
  border-left: 3px solid transparent;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

.dashboard-card--accent {
  border-left-color: var(--ted-accent);
}

// Active lesson highlight
.lesson-active {
  background-color: var(--highlight-active);
  border-left: 3px solid var(--highlight-today);
}

// Today column highlight in weekly schedule
.today-column {
  background-color: #EDF5FF;
  font-weight: 600;
}
```

**Step 2: Import theme in main.tsx**

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { Theme } from '@carbon/react'
import App from './App'
import './theme/ted-theme.scss'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Theme theme="g10">
      <App />
    </Theme>
  </React.StrictMode>
)
```

**Step 3: Commit**

```bash
git add dashboard/src/theme/ dashboard/src/main.tsx
git commit -m "feat: add TED × Carbon light theme"
```

---

### Task 4: API Hook + Data Types

**Files:**
- Create: `dashboard/src/hooks/useApi.ts`
- Create: `dashboard/src/types.ts`
- Create: `dashboard/src/utils/formatters.ts`
- Create: `dashboard/src/utils/countdown.ts`

**Step 1: Create TypeScript types**

```typescript
// dashboard/src/types.ts

export interface HomeworkItem {
  "Ders Adı": string
  "Ödev Başlığı": string
  "Ödev Kaynağı": string
  "Ödev Son Teslim Tarihi": string
  "Ödev Durumu": string
  "Ödev Görüntüle": string
  normalized_course?: string
  detail?: {
    description: string
    attachments: { name: string; url: string }[]
  }
}

export interface SebitHomework {
  id: string
  title: string
  course: string
  progress: number
  completed: boolean
  state_text: string
  teacher: string
  start_date: string
  end_date: string
}

export interface GradeItem {
  Ders: string
  "1. Sınav": string
  "2. Sınav": string
  "3. Sınav": string
  "DİKP/Performans-1": string
  "DİKP/Performans-2": string
  "DİKP/Performans-3": string
}

export interface CalendarEvent {
  allDay: boolean
  start: string
  end: string
  title: string
  extendedProps?: {
    location?: string
    description?: string
  }
}

export interface TeamActivity {
  "Academy+": string
  "Çalışma Başlangıç": string
  "Çalışma Bitiş": string
  "Katılım Durumu": string
  "Teams Link": string
}

export interface Announcement {
  "e-Posta Başlık": string
  "Ekleri": string
  "Yayın Tarihi": string
}

export interface ECProgress {
  total_videos: number
  completed_videos: number
  videos: { title: string; completed: boolean; difficulty: number }[]
}

export interface A3KProgress {
  total_lessons: number
  teacher_assigned_count: number
  teacher_assigned_completed: number
  dashboard_stats: {
    completed: number
    target: number
    firstTryScore: number
  }
  lessons: {
    title: string
    completed: boolean
    is_teacher_assigned: boolean
    end_date: string
  }[]
}

export interface HealthData {
  timestamp: string
  success: boolean
  scrape_errors: string[]
  duration_seconds: number
}
```

**Step 2: Create useApi hook with auto-refresh**

```typescript
// dashboard/src/hooks/useApi.ts
import { useState, useEffect, useCallback } from 'react'

const REFRESH_INTERVAL = 5 * 60 * 1000 // 5 minutes

export function useApi<T>(endpoint: string, defaultValue: T): {
  data: T
  loading: boolean
  error: string | null
  refresh: () => void
} {
  const [data, setData] = useState<T>(defaultValue)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(endpoint)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      setData(json)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Fetch error')
    } finally {
      setLoading(false)
    }
  }, [endpoint])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, REFRESH_INTERVAL)
    return () => clearInterval(interval)
  }, [fetchData])

  return { data, loading, error, refresh: fetchData }
}
```

**Step 3: Create formatters utility**

```typescript
// dashboard/src/utils/formatters.ts

export function formatTurkishDate(dateStr: string): string {
  if (!dateStr) return ''
  // Handle "DD.MM.YYYY HH:MM" format
  const match = dateStr.match(/(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})/)
  if (match) {
    const [, day, month, year, hour, min] = match
    const months = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz',
                    'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara']
    return `${parseInt(day)} ${months[parseInt(month) - 1]} ${year} ${hour}:${min}`
  }
  return dateStr
}

export function parseDeadline(dateStr: string): Date | null {
  const match = dateStr.match(/(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})/)
  if (!match) return null
  const [, day, month, year, hour, min] = match
  return new Date(parseInt(year), parseInt(month) - 1, parseInt(day),
                  parseInt(hour), parseInt(min))
}

export function getHomeworkStatus(status: string): {
  label: string; type: 'green' | 'red' | 'blue' | 'gray' | 'warm-gray'
} {
  switch (status) {
    case 'Yaptı': return { label: 'Tamamlandı', type: 'green' }
    case 'Yapmadı': return { label: 'Yapılmadı', type: 'red' }
    case 'Eksik': return { label: 'Eksik', type: 'warm-gray' }
    case 'Değerlendirilmemiş': return { label: 'Bekliyor', type: 'blue' }
    default: return { label: status, type: 'gray' }
  }
}

export function gradeColor(score: string): string {
  const n = parseInt(score)
  if (isNaN(n)) return ''
  if (n >= 85) return 'var(--status-success)'
  if (n >= 70) return 'var(--status-info)'
  if (n >= 50) return 'var(--status-warning)'
  return 'var(--status-error)'
}
```

**Step 4: Create countdown utility**

```typescript
// dashboard/src/utils/countdown.ts

export interface CountdownResult {
  days: number
  hours: number
  minutes: number
  text: string
  urgency: 'expired' | 'urgent' | 'soon' | 'normal'
}

export function getCountdown(deadline: Date | null): CountdownResult {
  if (!deadline) return { days: 0, hours: 0, minutes: 0, text: '-', urgency: 'normal' }

  const now = new Date()
  const diff = deadline.getTime() - now.getTime()

  if (diff <= 0) {
    return { days: 0, hours: 0, minutes: 0, text: 'Süresi doldu', urgency: 'expired' }
  }

  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))

  let text: string
  if (days > 0) text = `${days}g ${hours}s`
  else if (hours > 0) text = `${hours}s ${minutes}dk`
  else text = `${minutes}dk`

  let urgency: CountdownResult['urgency']
  if (days === 0 && hours < 24) urgency = 'urgent'
  else if (days < 3) urgency = 'soon'
  else urgency = 'normal'

  return { days, hours, minutes, text, urgency }
}
```

**Step 5: Commit**

```bash
git add dashboard/src/types.ts dashboard/src/hooks/ dashboard/src/utils/
git commit -m "feat: add API hook, types, and utility functions"
```

---

### Task 5: Dashboard Header Component

**Files:**
- Create: `dashboard/src/components/DashboardHeader.tsx`

**Step 1: Create header**

```tsx
import {
  Header, HeaderName, HeaderGlobalBar, HeaderGlobalAction,
  Tag, SkeletonText
} from '@carbon/react'
import { Renew } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { HealthData } from '../types'

export default function DashboardHeader() {
  const { data: health, loading, refresh } = useApi<HealthData>(
    '/api/health',
    { timestamp: '', success: false, scrape_errors: [], duration_seconds: 0 }
  )

  const syncAgo = health.timestamp
    ? getTimeAgo(health.timestamp)
    : '...'

  return (
    <Header aria-label="TED Dashboard"
      style={{ backgroundColor: 'var(--ted-header-bg)' }}>
      <HeaderName prefix="">
        <span style={{ fontWeight: 700, letterSpacing: '0.05em' }}>
          TED RÖNESANS
        </span>
      </HeaderName>
      <HeaderGlobalBar>
        <span style={{ color: 'var(--ted-header-text)', padding: '0 1rem',
                        display: 'flex', alignItems: 'center', gap: '0.75rem',
                        fontSize: '0.875rem' }}>
          <strong>Işık Kurt</strong> · 6/C
          {loading ? (
            <SkeletonText width="60px" />
          ) : (
            <Tag type={health.success ? 'green' : 'red'} size="sm">
              {syncAgo}
            </Tag>
          )}
        </span>
        <HeaderGlobalAction aria-label="Yenile" onClick={refresh}>
          <Renew size={20} />
        </HeaderGlobalAction>
      </HeaderGlobalBar>
    </Header>
  )
}

function getTimeAgo(timestamp: string): string {
  const diff = Date.now() - new Date(timestamp).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Az önce'
  if (mins < 60) return `${mins} dk önce`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} saat önce`
  return `${Math.floor(hours / 24)} gün önce`
}
```

**Step 2: Commit**

```bash
git add dashboard/src/components/DashboardHeader.tsx
git commit -m "feat: add dashboard header with sync status"
```

---

### Task 6: TodaySchedule Component

**Files:**
- Create: `dashboard/src/components/TodaySchedule.tsx`

**Step 1: Create today's schedule horizontal card strip**

The component reads `/api/schedule`, finds today's column, parses lesson times and names, highlights the current lesson.

```tsx
import { Tile, Tag } from '@carbon/react'
import { Time } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'

interface ScheduleData {
  latest: { schedule?: { rows: string[][] } }
  today: string
}

interface Lesson {
  period: string
  time: string
  name: string
  teacher: string
  room: string
}

export default function TodaySchedule() {
  const { data, loading } = useApi<ScheduleData>(
    '/api/schedule',
    { latest: {}, today: '' }
  )

  if (loading) return <TodayScheduleSkeleton />

  const rows = data.latest?.schedule?.rows || []
  const dayHeaders = rows[0] || []
  const todayIdx = dayHeaders.indexOf(data.today)
  if (todayIdx < 0) return <Tile>Bugün ders yok</Tile>

  const lessons = parseLessons(rows, todayIdx)
  const now = new Date()
  const currentHour = now.getHours()
  const currentMin = now.getMinutes()

  return (
    <div className="dashboard-card">
      <h4 style={{ margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Time size={20} />
        Bugünün Dersleri — {data.today}
      </h4>
      <div style={{ display: 'flex', gap: '0.75rem', overflowX: 'auto', paddingBottom: '0.5rem' }}>
        {lessons.map((lesson, i) => {
          const isActive = isCurrentLesson(lesson.time, currentHour, currentMin)
          return (
            <Tile key={i}
              className={isActive ? 'lesson-active' : ''}
              style={{
                minWidth: '160px', flex: '0 0 auto',
                borderLeft: isActive ? '3px solid var(--highlight-today)' : '3px solid transparent',
                padding: '0.75rem 1rem'
              }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--status-info)', fontWeight: 600 }}>
                {lesson.period} · {lesson.time}
              </div>
              <div style={{ fontWeight: 600, margin: '0.25rem 0' }}>
                {lesson.name}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#525252' }}>
                {lesson.teacher}
              </div>
              {isActive && <Tag type="blue" size="sm">Şimdi</Tag>}
            </Tile>
          )
        })}
      </div>
    </div>
  )
}

function parseLessons(rows: string[][], dayIdx: number): Lesson[] {
  const lessons: Lesson[] = []
  for (let r = 1; r < rows.length; r++) {
    const timeCell = rows[r][0] || ''
    const content = rows[r][dayIdx] || ''
    if (!content || content === 'Kahvaltı' || content === 'Öğle yemeği'
        || content === 'İkindi Kahvaltısı' || content === 'Çıkış') continue
    const periodMatch = timeCell.match(/(\d+)\. Ders/)
    const timeMatch = timeCell.match(/(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})/)
    if (!periodMatch || !timeMatch) continue
    const lines = content.split('\n')
    const name = lines[0]?.replace(/\s*\(.*?\)\s*/g, '').trim() || ''
    const teacher = lines.slice(1).join(', ').trim()
    lessons.push({
      period: `${periodMatch[1]}. Ders`,
      time: `${timeMatch[1]}-${timeMatch[2]}`,
      name,
      teacher,
      room: ''
    })
  }
  return lessons
}

function isCurrentLesson(timeRange: string, hour: number, min: number): boolean {
  const match = timeRange.match(/(\d{2}):(\d{2})-(\d{2}):(\d{2})/)
  if (!match) return false
  const startMin = parseInt(match[1]) * 60 + parseInt(match[2])
  const endMin = parseInt(match[3]) * 60 + parseInt(match[4])
  const nowMin = hour * 60 + min
  return nowMin >= startMin && nowMin < endMin
}

function TodayScheduleSkeleton() {
  return <Tile style={{ height: '120px' }}>Yükleniyor...</Tile>
}
```

**Step 2: Commit**

```bash
git add dashboard/src/components/TodaySchedule.tsx
git commit -m "feat: add TodaySchedule component with active lesson highlight"
```

---

### Task 7: WeeklySchedule Component

**Files:**
- Create: `dashboard/src/components/WeeklySchedule.tsx`

**Step 1: Create full weekly schedule table**

Uses Carbon DataTable to render the week's schedule with today's column highlighted.

```tsx
import { useApi } from '../hooks/useApi'
import { Calendar } from '@carbon/icons-react'

interface ScheduleData {
  latest: {
    week_label?: string
    schedule?: { rows: string[][] }
  }
  today: string
}

export default function WeeklySchedule() {
  const { data, loading } = useApi<ScheduleData>(
    '/api/schedule',
    { latest: {}, today: '' }
  )

  if (loading) return <div className="dashboard-card">Yükleniyor...</div>

  const rows = data.latest?.schedule?.rows || []
  if (rows.length === 0) return null

  const dayHeaders = rows[0] || []
  const DAYS = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma']
  const dayIndices = DAYS.map(d => dayHeaders.indexOf(d)).filter(i => i >= 0)

  return (
    <div className="dashboard-card">
      <h4 style={{ margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Calendar size={20} />
        Haftalık Program — {data.latest.week_label || ''}
      </h4>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
          <thead>
            <tr>
              <th style={thStyle}>Saat</th>
              {DAYS.map(day => (
                <th key={day} className={day === data.today ? 'today-column' : ''}
                    style={thStyle}>
                  {day}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.slice(1).map((row, ri) => {
              const timeCell = row[0] || ''
              if (!timeCell || timeCell === 'Çıkış') return null
              const isBreak = timeCell.includes('Kahvaltı') || timeCell.includes('yemeği')
                             || timeCell.includes('İkindi') || row.some(c => c === 'Kahvaltı')
              if (isBreak) return null
              return (
                <tr key={ri}>
                  <td style={{ ...tdStyle, fontWeight: 600, whiteSpace: 'nowrap', fontSize: '0.75rem' }}>
                    {formatTime(timeCell)}
                  </td>
                  {dayIndices.map((di, ci) => {
                    const cell = row[di] || ''
                    const lines = cell.split('\n')
                    const isToday = DAYS[ci] === data.today
                    return (
                      <td key={ci}
                          className={isToday ? 'today-column' : ''}
                          style={{ ...tdStyle, ...(isToday ? { backgroundColor: '#EDF5FF' } : {}) }}>
                        {lines[0] && (
                          <>
                            <div style={{ fontWeight: 500 }}>
                              {lines[0].replace(/\s*\(.*?\)\s*/g, '').trim()}
                            </div>
                            {lines[1] && (
                              <div style={{ fontSize: '0.6875rem', color: '#525252' }}>
                                {lines.slice(1).join(', ').trim()}
                              </div>
                            )}
                          </>
                        )}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function formatTime(cell: string): string {
  const periodMatch = cell.match(/(\d+)\. Ders/)
  const timeMatch = cell.match(/(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})/)
  if (periodMatch && timeMatch) return `${periodMatch[1]}. ${timeMatch[1]}`
  const justTime = cell.match(/(\d{2}:\d{2})/)
  return justTime ? justTime[1] : cell
}

const thStyle: React.CSSProperties = {
  padding: '0.5rem 0.75rem',
  textAlign: 'left',
  borderBottom: '2px solid #E0E0E0',
  backgroundColor: '#F4F4F4'
}

const tdStyle: React.CSSProperties = {
  padding: '0.5rem 0.75rem',
  borderBottom: '1px solid #E0E0E0',
  verticalAlign: 'top'
}
```

**Step 2: Commit**

```bash
git add dashboard/src/components/WeeklySchedule.tsx
git commit -m "feat: add WeeklySchedule component with today highlight"
```

---

### Task 8: HomeworkTracker Component

**Files:**
- Create: `dashboard/src/components/HomeworkTracker.tsx`

**Step 1: Create homework tracker with countdown and progress bars**

Combines portal homework (`/api/homework`) and SEBİT homework (`/api/sebit`). Shows countdown timers, progress bars, and status tags.

```tsx
import { Tag, ProgressBar, Tile } from '@carbon/react'
import { Task, Timer, CheckmarkFilled, WarningFilled } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { HomeworkItem, SebitHomework } from '../types'
import { parseDeadline, getHomeworkStatus, formatTurkishDate } from '../utils/formatters'
import { getCountdown } from '../utils/countdown'
import { useState, useEffect } from 'react'

export default function HomeworkTracker() {
  const { data: hwData } = useApi<{ summary: string; homework: HomeworkItem[] }>(
    '/api/homework', { summary: '', homework: [] }
  )
  const { data: sebitData } = useApi<{ homework?: SebitHomework[]; total_homework?: number }>(
    '/api/sebit', {}
  )

  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 60000)
    return () => clearInterval(t)
  }, [])

  const portalHw = hwData.homework || []
  const sebitHw = sebitData.homework || []

  // Sort: pending first (by deadline), then completed
  const sortedPortal = [...portalHw].sort((a, b) => {
    const aD = a["Ödev Durumu"] === "Yaptı" ? 1 : 0
    const bD = b["Ödev Durumu"] === "Yaptı" ? 1 : 0
    if (aD !== bD) return aD - bD
    const aDate = parseDeadline(a["Ödev Son Teslim Tarihi"])
    const bDate = parseDeadline(b["Ödev Son Teslim Tarihi"])
    return (aDate?.getTime() || 0) - (bDate?.getTime() || 0)
  })

  return (
    <div className="dashboard-card dashboard-card--accent">
      <h4 style={{ margin: '0 0 0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Task size={20} />
        Ödevler & Geri Sayım
      </h4>
      <p style={{ fontSize: '0.8125rem', color: '#525252', margin: '0 0 1rem' }}>
        {hwData.summary.split('\n').slice(1).join(' · ')}
      </p>

      {/* Portal Homework */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {sortedPortal.slice(0, 15).map((hw, i) => {
          const deadline = parseDeadline(hw["Ödev Son Teslim Tarihi"])
          const countdown = getCountdown(deadline)
          const status = getHomeworkStatus(hw["Ödev Durumu"])
          return (
            <Tile key={`p-${i}`} style={{ padding: '0.75rem 1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                    <Tag type={status.type} size="sm">{status.label}</Tag>
                    <span style={{ fontWeight: 600, fontSize: '0.8125rem' }}>
                      {hw.normalized_course || hw["Ders Adı"]}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.8125rem' }}>{hw["Ödev Başlığı"]}</div>
                  <div style={{ fontSize: '0.75rem', color: '#525252', marginTop: '0.25rem' }}>
                    Teslim: {formatTurkishDate(hw["Ödev Son Teslim Tarihi"])}
                  </div>
                </div>
                <div style={{ textAlign: 'right', minWidth: '80px' }}>
                  {hw["Ödev Durumu"] !== "Yaptı" && countdown.urgency !== 'expired' && (
                    <div className={countdown.urgency === 'urgent' ? 'tag-urgent' : ''}>
                      <Tag type={countdown.urgency === 'urgent' ? 'red' : countdown.urgency === 'soon' ? 'warm-gray' : 'blue'} size="sm">
                        <Timer size={12} /> {countdown.text}
                      </Tag>
                    </div>
                  )}
                  {countdown.urgency === 'expired' && hw["Ödev Durumu"] !== "Yaptı" && (
                    <Tag type="red" size="sm"><WarningFilled size={12} /> Gecikmiş</Tag>
                  )}
                  {hw["Ödev Durumu"] === "Yaptı" && (
                    <CheckmarkFilled size={20} style={{ color: 'var(--status-success)' }} />
                  )}
                </div>
              </div>
            </Tile>
          )
        })}
      </div>

      {/* SEBİT Homework */}
      {sebitHw.length > 0 && (
        <>
          <h5 style={{ margin: '1.5rem 0 0.5rem', fontSize: '0.875rem' }}>SEBİT Dijital Ödevler</h5>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {sebitHw.filter(h => !h.completed).concat(sebitHw.filter(h => h.completed)).slice(0, 10).map((hw, i) => (
              <Tile key={`s-${i}`} style={{ padding: '0.75rem 1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                      <Tag type={hw.completed ? 'green' : 'red'} size="sm">
                        {hw.completed ? 'Tamamlandı' : hw.state_text}
                      </Tag>
                      <span style={{ fontWeight: 600, fontSize: '0.8125rem' }}>{hw.course}</span>
                    </div>
                    <div style={{ fontSize: '0.8125rem' }}>{hw.title}</div>
                  </div>
                  <div style={{ width: '120px' }}>
                    <ProgressBar
                      value={hw.progress}
                      size="small"
                      status={hw.completed ? 'finished' : 'active'}
                    />
                    <div style={{ fontSize: '0.6875rem', textAlign: 'right', color: '#525252' }}>
                      %{hw.progress}
                    </div>
                  </div>
                </div>
              </Tile>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add dashboard/src/components/HomeworkTracker.tsx
git commit -m "feat: add HomeworkTracker with countdown and progress"
```

---

### Task 9: GradeTable Component

**Files:**
- Create: `dashboard/src/components/GradeTable.tsx`

**Step 1: Create grade table with color-coded scores**

```tsx
import { useApi } from '../hooks/useApi'
import { Certificate } from '@carbon/icons-react'
import { GradeItem } from '../types'
import { gradeColor } from '../utils/formatters'

export default function GradeTable() {
  const { data } = useApi<{ semester?: string; grades?: GradeItem[] }>(
    '/api/grades', {}
  )

  const grades = data.grades || []
  const cols = ['1. Sınav', '2. Sınav', '3. Sınav', 'DİKP/Performans-1', 'DİKP/Performans-2', 'DİKP/Performans-3'] as const

  return (
    <div className="dashboard-card">
      <h4 style={{ margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Certificate size={20} />
        Notlar — {data.semester || ''}
      </h4>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
          <thead>
            <tr>
              <th style={thStyle}>Ders</th>
              <th style={thStyle}>S1</th>
              <th style={thStyle}>S2</th>
              <th style={thStyle}>S3</th>
              <th style={thStyle}>P1</th>
              <th style={thStyle}>P2</th>
              <th style={thStyle}>P3</th>
            </tr>
          </thead>
          <tbody>
            {grades.map((g, i) => (
              <tr key={i}>
                <td style={{ ...tdStyle, fontWeight: 500 }}>{g.Ders}</td>
                {cols.map(col => {
                  const val = g[col]
                  const color = gradeColor(val)
                  return (
                    <td key={col} style={{
                      ...tdStyle,
                      textAlign: 'center',
                      fontWeight: 600,
                      color: color || '#161616',
                      backgroundColor: val !== '-' && color ? `${color}11` : 'transparent'
                    }}>
                      {val}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const thStyle: React.CSSProperties = {
  padding: '0.5rem 0.75rem', textAlign: 'center',
  borderBottom: '2px solid #E0E0E0', backgroundColor: '#F4F4F4', fontSize: '0.75rem'
}
const tdStyle: React.CSSProperties = {
  padding: '0.5rem 0.75rem', borderBottom: '1px solid #E0E0E0'
}
```

**Step 2: Commit**

```bash
git add dashboard/src/components/GradeTable.tsx
git commit -m "feat: add GradeTable with color-coded scores"
```

---

### Task 10: PlatformProgress Component

**Files:**
- Create: `dashboard/src/components/PlatformProgress.tsx`

**Step 1: Create platform progress bars for EC, A3K, SEBİT**

```tsx
import { ProgressBar, Tile, Tag } from '@carbon/react'
import { ChartBar } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'

export default function PlatformProgress() {
  const { data: ec } = useApi<{ total_videos?: number; completed_videos?: number }>(
    '/api/progress/ec', {}
  )
  const { data: a3k } = useApi<{
    teacher_assigned_count?: number; teacher_assigned_completed?: number
    dashboard_stats?: { completed?: number; target?: number; firstTryScore?: number }
  }>('/api/progress/a3k', {})
  const { data: sebit } = useApi<{ total_homework?: number; completed_count?: number; courses?: string[] }>(
    '/api/sebit', {}
  )

  const platforms = [
    {
      name: 'EnglishCentral',
      done: ec.completed_videos || 0,
      total: ec.total_videos || 0,
      color: '#0F62FE'
    },
    {
      name: 'Achieve3000',
      done: a3k.teacher_assigned_completed || 0,
      total: a3k.teacher_assigned_count || 0,
      color: '#0043CE'
    },
    {
      name: 'SEBİT',
      done: sebit.completed_count || 0,
      total: sebit.total_homework || 0,
      color: '#002D9C'
    }
  ]

  return (
    <div className="dashboard-card">
      <h4 style={{ margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <ChartBar size={20} />
        Platform İlerleme
      </h4>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {platforms.map(p => {
          const pct = p.total > 0 ? Math.round((p.done / p.total) * 100) : 0
          return (
            <div key={p.name}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                <span style={{ fontWeight: 500, fontSize: '0.8125rem' }}>{p.name}</span>
                <span style={{ fontSize: '0.8125rem' }}>
                  <Tag type={pct === 100 ? 'green' : pct > 50 ? 'blue' : 'warm-gray'} size="sm">
                    {p.done}/{p.total}
                  </Tag>
                </span>
              </div>
              <ProgressBar value={pct} status={pct === 100 ? 'finished' : 'active'} size="small" />
            </div>
          )
        })}
      </div>
      {a3k.dashboard_stats?.firstTryScore && (
        <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: '#525252' }}>
          A3K İlk Deneme Skoru: <strong>{a3k.dashboard_stats.firstTryScore}</strong>
        </div>
      )}
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add dashboard/src/components/PlatformProgress.tsx
git commit -m "feat: add PlatformProgress component"
```

---

### Task 11: CalendarEvents Component

**Files:**
- Create: `dashboard/src/components/CalendarEvents.tsx`

**Step 1: Create upcoming calendar events**

```tsx
import { Tile, Tag } from '@carbon/react'
import { EventSchedule } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { CalendarEvent } from '../types'

export default function CalendarEvents() {
  const { data } = useApi<{ events: CalendarEvent[] }>('/api/calendar', { events: [] })

  const now = new Date()
  const upcoming = data.events
    .filter(e => new Date(e.end || e.start) >= now)
    .sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime())
    .slice(0, 10)

  return (
    <div className="dashboard-card">
      <h4 style={{ margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <EventSchedule size={20} />
        Takvim & Yaklaşan Etkinlikler
      </h4>
      {upcoming.length === 0 ? (
        <p style={{ fontSize: '0.8125rem', color: '#525252' }}>Yaklaşan etkinlik yok</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {upcoming.map((ev, i) => {
            const d = new Date(ev.start)
            const months = ['Oca','Şub','Mar','Nis','May','Haz','Tem','Ağu','Eyl','Eki','Kas','Ara']
            return (
              <Tile key={i} style={{ padding: '0.5rem 1rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
                <div style={{
                  textAlign: 'center', minWidth: '48px',
                  padding: '0.25rem', backgroundColor: '#EDF5FF', borderRadius: '4px'
                }}>
                  <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--highlight-today)' }}>
                    {d.getDate()}
                  </div>
                  <div style={{ fontSize: '0.6875rem', color: '#525252' }}>
                    {months[d.getMonth()]}
                  </div>
                </div>
                <div>
                  <div style={{ fontWeight: 500, fontSize: '0.8125rem' }}>{ev.title}</div>
                  {!ev.allDay && (
                    <div style={{ fontSize: '0.75rem', color: '#525252' }}>
                      {d.getHours().toString().padStart(2,'0')}:{d.getMinutes().toString().padStart(2,'0')}
                    </div>
                  )}
                  {ev.extendedProps?.location && (
                    <div style={{ fontSize: '0.75rem', color: '#525252' }}>
                      {ev.extendedProps.location}
                    </div>
                  )}
                </div>
              </Tile>
            )
          })}
        </div>
      )}
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add dashboard/src/components/CalendarEvents.tsx
git commit -m "feat: add CalendarEvents component"
```

---

### Task 12: TeamActivities Component

**Files:**
- Create: `dashboard/src/components/TeamActivities.tsx`

**Step 1: Create team activities + ÖGEP sessions**

```tsx
import { Tag, Tile } from '@carbon/react'
import { GroupPresentation } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { TeamActivity } from '../types'

export default function TeamActivities() {
  const { data } = useApi<{ activities: TeamActivity[]; ogep: TeamActivity[] }>(
    '/api/teams', { activities: [], ogep: [] }
  )

  return (
    <div className="dashboard-card">
      <h4 style={{ margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <GroupPresentation size={20} />
        Takım Çalışmaları & ÖGEP
      </h4>

      {/* Academy+ Activities */}
      {data.activities.length > 0 && (
        <>
          <h5 style={{ fontSize: '0.8125rem', margin: '0 0 0.5rem', color: '#525252' }}>Academy+</h5>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem', marginBottom: '1rem' }}>
            {data.activities.map((a, i) => (
              <Tile key={i} style={{ padding: '0.5rem 1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 500, fontSize: '0.8125rem' }}>{a["Academy+"]}</div>
                  <div style={{ fontSize: '0.75rem', color: '#525252' }}>
                    {a["Çalışma Başlangıç"]} — {a["Çalışma Bitiş"]}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <Tag type={a["Katılım Durumu"] === "Katıldı" ? 'green' : 'gray'} size="sm">
                    {a["Katılım Durumu"] || 'Bekliyor'}
                  </Tag>
                  <Tag type={a["Teams Link"] === "Yüz Yüze" ? 'blue' : 'teal'} size="sm">
                    {a["Teams Link"]}
                  </Tag>
                </div>
              </Tile>
            ))}
          </div>
        </>
      )}

      {/* ÖGEP Sessions */}
      {data.ogep.length > 0 && (
        <>
          <h5 style={{ fontSize: '0.8125rem', margin: '0 0 0.5rem', color: '#525252' }}>ÖGEP Oturumları</h5>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
            {data.ogep.map((s, i) => (
              <Tile key={i} style={{ padding: '0.5rem 1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 500, fontSize: '0.8125rem' }}>
                    {s["ÖGEP (Öğrenci Gelişim Programı)"] || s["Academy+"]}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#525252' }}>
                    {s["Çalışma Başlangıç"]} — {s["Çalışma Bitiş"]}
                  </div>
                </div>
                <Tag type={s["Katılım Durumu"] === "Katıldı" ? 'green' : 'gray'} size="sm">
                  {s["Katılım Durumu"] || 'Bekliyor'}
                </Tag>
              </Tile>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add dashboard/src/components/TeamActivities.tsx
git commit -m "feat: add TeamActivities + ÖGEP component"
```

---

### Task 13: CourseContent Component

**Files:**
- Create: `dashboard/src/components/CourseContent.tsx`

**Step 1: Create course content with tabs**

```tsx
import { Tabs, TabList, Tab, TabPanels, TabPanel, Tile } from '@carbon/react'
import { Education } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'

interface CourseData {
  [course: string]: {
    tab_id?: string
    text?: string
    cards?: string[]
    items?: unknown[]
  }
}

export default function CourseContent() {
  const { data } = useApi<CourseData>('/api/content', {})

  const courses = Object.entries(data).filter(([, v]) =>
    v.text || (v.cards && v.cards.length > 0)
  )

  if (courses.length === 0) return null

  return (
    <div className="dashboard-card">
      <h4 style={{ margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Education size={20} />
        Ders İçerikleri
      </h4>
      <Tabs>
        <TabList aria-label="Ders içerikleri" contained>
          {courses.map(([name]) => (
            <Tab key={name}>{name}</Tab>
          ))}
        </TabList>
        <TabPanels>
          {courses.map(([name, content]) => (
            <TabPanel key={name}>
              {content.text && (
                <div style={{
                  fontSize: '0.8125rem', lineHeight: '1.5',
                  whiteSpace: 'pre-wrap', padding: '0.5rem 0'
                }}>
                  {content.text.slice(0, 1000)}
                </div>
              )}
              {content.cards && content.cards.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem', marginTop: '0.5rem' }}>
                  {content.cards.slice(0, 5).map((card, i) => (
                    <Tile key={i} style={{ padding: '0.5rem 1rem', fontSize: '0.8125rem' }}>
                      {card.slice(0, 300)}
                    </Tile>
                  ))}
                </div>
              )}
            </TabPanel>
          ))}
        </TabPanels>
      </Tabs>
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add dashboard/src/components/CourseContent.tsx
git commit -m "feat: add CourseContent with Carbon tabs"
```

---

### Task 14: Announcements Component

**Files:**
- Create: `dashboard/src/components/Announcements.tsx`

**Step 1: Create announcements list**

```tsx
import { Tile, Tag } from '@carbon/react'
import { Notification } from '@carbon/icons-react'
import { useApi } from '../hooks/useApi'
import { Announcement } from '../types'
import { formatTurkishDate } from '../utils/formatters'

export default function Announcements() {
  const { data } = useApi<{ announcements: Announcement[] }>(
    '/api/announcements', { announcements: [] }
  )

  return (
    <div className="dashboard-card">
      <h4 style={{ margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Notification size={20} />
        Okul Duyuruları
      </h4>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
        {data.announcements.map((ann, i) => (
          <Tile key={i} style={{ padding: '0.5rem 1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.8125rem', fontWeight: 500 }}>
              {ann["e-Posta Başlık"]}
            </span>
            <Tag type="gray" size="sm">
              {formatTurkishDate(ann["Yayın Tarihi"])}
            </Tag>
          </Tile>
        ))}
      </div>
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add dashboard/src/components/Announcements.tsx
git commit -m "feat: add Announcements component"
```

---

### Task 15: App Layout — Assemble All Components

**Files:**
- Modify: `dashboard/src/App.tsx`

**Step 1: Compose all components into the dashboard layout**

```tsx
import { Grid, Column, Content } from '@carbon/react'
import DashboardHeader from './components/DashboardHeader'
import TodaySchedule from './components/TodaySchedule'
import WeeklySchedule from './components/WeeklySchedule'
import HomeworkTracker from './components/HomeworkTracker'
import GradeTable from './components/GradeTable'
import PlatformProgress from './components/PlatformProgress'
import CalendarEvents from './components/CalendarEvents'
import TeamActivities from './components/TeamActivities'
import CourseContent from './components/CourseContent'
import Announcements from './components/Announcements'

export default function App() {
  return (
    <>
      <DashboardHeader />
      <Content style={{ padding: '3rem 1rem 2rem' }}>
        <Grid fullWidth>
          {/* 1. Today's Schedule — full width */}
          <Column lg={16} md={8} sm={4}>
            <TodaySchedule />
          </Column>

          {/* 2. Weekly Schedule — full width */}
          <Column lg={16} md={8} sm={4}>
            <WeeklySchedule />
          </Column>

          {/* 3-4. Homework + Grades — side by side */}
          <Column lg={10} md={8} sm={4}>
            <HomeworkTracker />
          </Column>
          <Column lg={6} md={8} sm={4}>
            <GradeTable />
          </Column>

          {/* 5-6. Platform Progress + Calendar — side by side */}
          <Column lg={8} md={4} sm={4}>
            <PlatformProgress />
          </Column>
          <Column lg={8} md={4} sm={4}>
            <CalendarEvents />
          </Column>

          {/* 7-8. Teams/ÖGEP + Course Content — side by side */}
          <Column lg={8} md={4} sm={4}>
            <TeamActivities />
          </Column>
          <Column lg={8} md={4} sm={4}>
            <CourseContent />
          </Column>

          {/* 9. Announcements — full width */}
          <Column lg={16} md={8} sm={4}>
            <Announcements />
          </Column>
        </Grid>
      </Content>
    </>
  )
}
```

**Step 2: Verify the dashboard renders**

Run Flask backend and Vite dev server together, open http://localhost:3000.

**Step 3: Commit**

```bash
git add dashboard/src/App.tsx
git commit -m "feat: assemble complete dashboard layout with all components"
```

---

### Task 16: Build & Serve from Flask

**Files:**
- Modify: `src/dashboard_api.py`
- Modify: `dashboard/vite.config.ts`

**Step 1: Configure Vite build output to Flask-servable directory**

Update `dashboard/vite.config.ts`:
```typescript
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../dashboard-dist',
    emptyOutDir: true
  },
  server: {
    port: 3000,
    proxy: { '/api': 'http://localhost:8085' }
  }
})
```

**Step 2: Add static file serving to Flask**

Add to `src/dashboard_api.py`:
```python
from flask import send_from_directory

DIST_DIR = os.path.join(PROJECT_ROOT, "dashboard-dist")

@app.route("/")
@app.route("/<path:path>")
def serve_spa(path=""):
    if path and os.path.exists(os.path.join(DIST_DIR, path)):
        return send_from_directory(DIST_DIR, path)
    return send_from_directory(DIST_DIR, "index.html")
```

**Step 3: Build and test**

```bash
cd dashboard && npm run build
cd ..
python src/dashboard_api.py
# Open http://localhost:8085
```

**Step 4: Commit**

```bash
git add src/dashboard_api.py dashboard/vite.config.ts
git commit -m "feat: serve React build from Flask, production-ready"
```

---

### Task 17: Integration with run_sync.py

**Files:**
- Modify: `src/run_sync.py` (optional)

**Step 1: Document dashboard launch command in CLAUDE.md**

Add to CLAUDE.md commands section:
```
# Dashboard
python src/dashboard_api.py   # Start dashboard server on port 8085
cd dashboard && npm run dev   # Dev mode with hot reload on port 3000
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add dashboard commands to CLAUDE.md"
```
