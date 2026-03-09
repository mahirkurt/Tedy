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
  [key: string]: string
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

export interface OgepSession {
  "ÖGEP (Öğrenci Gelişim Programı)": string
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

export interface HealthData {
  timestamp: string
  success: boolean
  scrape_errors: string[]
  duration_seconds: number
}
