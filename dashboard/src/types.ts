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
  color: string
  course?: string
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
  status: 'ok' | 'warning' | 'error' | 'skipped'
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
}

export interface AssistantCitation {
  id: string
  path: string
  chunk_index: number
  score: number
  confidence: number
  snippet: string
  source_kind: string
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
  }
}
