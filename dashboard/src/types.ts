import type { SubjectFamily } from './theme/subjects'

export interface HomeworkItem {
  "Ders Adı": string
  "Ödev Başlığı": string
  "Ödev Kaynağı": string
  "Ödev Son Teslim Tarihi": string
  "Ödev Durumu": string
  "Ödev Görüntüle": string
  normalized_course?: string
  first_seen?: string
  homework_key?: string
  student_marked_done?: boolean
  student_done_at?: string
  detail?: {
    description: string
    attachments: { name: string; url: string }[]
  }
  source?: string
  source_type?: 'ted' | 'private'
  private_lesson_id?: string
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
  [key: string]: string
}

export interface CalendarEvent {
  id?: string
  allDay: boolean
  start: string
  end: string
  title: string
  extendedProps?: {
    location?: string
    description?: string
    kind?: 'event' | 'private_lesson'
    badge?: string
    course?: string
    private_lesson_id?: string
  }
}

export interface StudentProfileData {
  name: string
  student_no: string
  class_name: string
  branch: string
  photo_data_url: string
  fields: Record<string, string>
  scraped_at: string
  auth?: {
    email?: string
    name?: string
    picture?: string
  }
}

export interface PrivateLesson {
  id: string
  course: string
  teacher: string
  is_recurring: boolean
  weekday: string
  date: string
  start_time: string
  end_time: string
  active: boolean
  created_at: string
}

export interface TeamActivity {
  "Academy+": string
  "Çalışma Başlangıç": string
  "Çalışma Bitiş": string
  "Katılım Durumu": string
  "Teams Link": string
}

export interface OgepSession {
  "ÖGEP (Öğrenci Gelişim Programı)": string
  "Çalışma Başlangıç": string
  "Çalışma Bitiş": string
  "Katılım Durumu": string
  "Teams Link": string
}

export interface UnifiedEvent {
  id: string
  title: string
  type: 'lesson' | 'homework' | 'private_lesson' | 'ogep' | 'team' | 'sebit' | 'event'
  start: string
  end: string
  /** The course's mark colour (backend `_takvim_rengi`); grey without a course. */
  color: string
  course?: string
  courseFamily?: SubjectFamily
  status?: string
  subtitle?: string
}

export interface Announcement {
  "e-Posta Başlık": string
  "Ekleri": string
  "Yayın Tarihi": string
  "Ekleri_url"?: string
  "e-Posta İçerik"?: string
  "Duyuru Detayı"?: string
  "İçerik"?: string
  "Açıklama"?: string
  "Mesaj"?: string
  [key: string]: string | undefined
}

export interface ECVideo {
  title: string
  url: string
  difficulty: number
  duration: string
  completed: boolean
  activities?: Record<string, { started: boolean; completed: boolean }>
}

export interface A3KLesson {
  title: string
  url: string
  category: string
  score: number
  completed: boolean
  completed_steps: number
  total_steps: number
  is_teacher_assigned?: boolean
}

export interface SectionHealth {
  count: number
  prev_count: number
  status: 'ok' | 'warning' | 'error' | 'skipped' | 'unavailable'
}

export interface HealthData {
  timestamp: string
  success: boolean
  scrape_errors: string[]
  duration_seconds: number
  validation_warnings?: string[]
  login?: {
    method: 'cached_session' | 'captcha_login' | 'failed'
    captcha_attempts: number
  }
  sections?: Record<string, SectionHealth>
  staleness?: {
    last_successful_full_scrape: string
    stale_sections: string[]
  }
  /** Academic year the sync resolved, e.g. "2026-2027". */
  academic_year?: string | null
  /** How that year was resolved: current | rollover | held | initialized | ignored_regression | unknown */
  year_detection?: string
  /** True when this run sealed the previous year's archive. */
  year_archived?: boolean
  /** Sections the portal itself refused, keyed by section name. */
  unavailable?: Record<string, { reason: string; detail: string }>
  /**
   * Sections whose scrape failed this run — distinct from `unavailable`,
   * which is the portal explaining itself. Measured 2026-09-21: for nearly
   * two hours the dashboard showed Işık no homework, no timetable and no
   * grades, and every surface said "portalda kayıt yok" — which was not
   * true. It could not be read; that is a different sentence.
   */
  /** Sections this run could not read. `son_okuma` is the ISO time of the
   *  earlier reading the dashboard is showing in its place, when there is one. */
  okunamadi?: Record<string, { detail?: string; son_okuma?: string }>
}

export type CitationKind = 'ogrenci' | 'mufredat' | 'kitap' | 'oer' | 'modul'

export interface AssistantCitation {
  id: string
  kind: CitationKind
  label: string
  locator: Record<string, unknown>
  snippet: string
  confidence: number
}

export interface AssistantToolCall {
  name: string
  ms: number
  ok: boolean
}

export interface AssistantPlanBlock {
  type: string
  title: string
  day: string
  estimated_minutes: number
  actions: string[]
  rationale: string
}

export interface AssistantResponse {
  answer: string
  citations: AssistantCitation[]
  safety_flags: string[]
  plan_blocks: AssistantPlanBlock[]
  intent: string
  session_id: string
  meta: {
    model: string
    retrieval_count?: number
    latency_ms?: number
    index_generated_at?: string
    tier?: 'fast' | 'deep'
    tool_calls?: AssistantToolCall[]
    dropped_citations?: number
    degraded?: string[]
    budget_exhausted?: boolean
  }
}

export interface ExamItem {
  id: string
  course: string
  title: string
  rawTitle: string
  /** Subject mark colour (light-theme accent of the subject family). */
  courseColor: string
  /** Tedy ders renk ailesi (Carbon Tag family) — see theme/subjects.ts. */
  courseFamily?: SubjectFamily
  examNumber: number | null
  date: string | null
  endDate: string | null
  allDay: boolean
  status: 'upcoming' | 'past'
  grade: string | null
  studyGuide: string | null
  aiSummary: string | null
  relatedHomework: { title: string; deadline: string; status: string }[]
  relatedContent: { title: string; type: string }[]
}

export interface ExamsApiResponse {
  exams: ExamItem[]
  stats: { upcoming: number; past: number; averageGrade: number | null }
}

/* ── Tedy Books ─────────────────────────────────────────────────────────── */

export interface BookCover {
  palette?: string
  monogram?: string
}

export interface BookSummary {
  slug: string
  title: string
  subtitle: string
  author: string
  translator: string
  publisher: string
  edition: string
  year: string
  language: string
  description: string
  epigraph: string
  cover: BookCover
  totalChapters: number
  availableChapters: number
  availableWords: number
  totalSourceWords: number
  readingMinutes: number
}

export interface BookChapter {
  id: string
  order: number
  volume: string
  part: string
  numeral: string
  label: string
  title: string
  sourceWords: number
  available: boolean
  words: number
  readingMinutes: number
}

export interface BookDetail extends BookSummary {
  chapters: BookChapter[]
}

export interface BookChapterNav {
  id: string
  title: string
  label: string
}

export interface BookChapterContent extends BookChapter {
  content: string
  credit: string
  partHeading: string
}

export interface BookChapterResponse {
  book: BookSummary
  chapter: BookChapterContent
  prev: BookChapterNav | null
  next: BookChapterNav | null
  position: { index: number; total: number }
}

export interface ModuleCard {
  slug: string
  version: number
  title: string | null
  subject: string | null
  gradeLevel: string | null
  mode: string | null
  outcomes: string[]
  ted_link: { kind: 'exam' | 'homework'; id: string } | null
  created_at: string | null
  gates: { pass: number; warn: number; fail: number }
}

export interface ModuleTicket {
  url: string
  exp: number
}
