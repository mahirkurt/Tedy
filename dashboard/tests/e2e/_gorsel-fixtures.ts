// Fixtures for the visual regression and ARIA snapshot specs: FULL plus every
// endpoint FULL leaves to the live test server. A screenshot is only a baseline
// if nothing under it changes on its own, so nothing here comes from live
// data that moves. Book and module metadata are the real catalog (not
// personal, and they change only when a book or module is published); the
// profile, SEBIT and Achieve3000 answers are invented — the live profile
// carries phone numbers and the family's names, which do not belong in a test.
import { FULL, LIVE_HEALTH } from './_audit-fixtures'
import { SCHEDULE, HOMEWORK } from './_bugun-fixtures'

// The clock the snapshots run at: Thursday of the fixture week, between the
// third and fourth lesson, so Bugün shows a school day in progress.
export const SABIT_SAAT = '2026-09-24T10:30:00+03:00'

const RENK: Record<string, string> = { purple: '#8a3ffc', magenta: '#d02670', gray: '#6f6f6f' }
const sinav = (id: string, title: string, course: string, courseFamily: string, date: string,
  status: 'upcoming' | 'past', grade: string | null = null) => ({
  id, title, rawTitle: title, course, courseFamily, courseColor: RENK[courseFamily], date, endDate: date,
  allDay: false, status, grade, examNumber: null, aiSummary: null, studyGuide: null,
  relatedContent: [], relatedHomework: [],
})

export const GORSEL: Record<string, unknown> = {
  ...FULL,
  health: { ...LIVE_HEALTH, timestamp: '2026-09-24T10:15:00', validation_warnings: [], unavailable: {} },
  schedule: SCHEDULE,
  homework: HOMEWORK,
  // The shape /api/exams serves. FULL's exams ({ders, tarih, tur}) predate it
  // and crashed Sınavlar into "Bu bölüm açılamadı" (found by capraz-tarayici).
  exams: { exams: [
    sinav('m1', 'Matematik 1. Yazılı', 'Matematik', 'purple', '2026-10-01T09:00:00', 'upcoming'),
    sinav('g1', 'Özdebir Gelişim İzleme Sınavı GİS · İzleme Sınavı', '', 'gray', '2026-10-23T09:00:00', 'upcoming'),
    sinav('t1', 'Türkçe 1. Yazılı', 'Türkçe', 'magenta', '2026-09-18T10:00:00', 'past', '92'),
  ], stats: { averageGrade: 92, past: 1, upcoming: 2 } },
  'auth/me': { email: 'test@tedy.online', name: 'Test User', picture: '', role: 'full', student: false },
  books: {"books": [{"author": "J.R.R. Tolkien", "availableChapters": 6, "availableWords": 11411, "cover": {"monogram": "H", "palette": "midnight"}, "description": "Bilbo Baggins'in macerasını İngilizce okuma pratiğiyle birlikte keşfet.", "edition": "Enhanced Edition (2011)", "epigraph": "", "language": "en", "publisher": "", "readingMinutes": 63, "slug": "hobbit-eng", "subtitle": "English Reader", "title": "The Hobbit", "totalChapters": 19, "totalSourceWords": 0, "translator": "", "year": "2011"}, {"author": "J.R.R. Tolkien", "availableChapters": 6, "availableWords": 37390, "cover": {"monogram": "YE", "palette": "forest"}, "description": "Bilbo Baggins'in yüz on birinci yaş günü davetiyle başlayan yolculuk, Frodo'yu Shire'dan Hüküm Dağı'na taşır. Üç cilt — Yüzük Kardeşliği, İki Kule ve Kralın Dönüşü — burada tek bir okuma akışında birleşiyor.", "edition": "14 yaş uyarlaması", "epigraph": "Gezgin olan herkes yolunu kaybetmiş değildir.", "language": "tr", "publisher": "Metis Yayıncılık", "readingMinutes": 208, "slug": "yuzuklerin-efendisi", "subtitle": "Üç cilt bir arada", "title": "Yüzüklerin Efendisi", "totalChapters": 67, "totalSourceWords": 366073, "translator": "Çiğdem Erkal İpek", "year": "2026"}]},
  'books/progress': { books: {} },
  modules: {"moduller": [{"created_at": "2026-09-19T19:32:46+00:00", "gates": {"fail": 0, "pass": 17, "warn": 0}, "gradeLevel": "7. Sınıf", "mode": "MODULE", "outcomes": ["MAT.7.1.1"], "slug": "mat7-tam-sayilar", "subject": "Matematik", "ted_link": null, "title": "Tam Sayılar: Sıfırın İki Yanı", "version": 1}]},
  'student/profile': {
    auth: { email: 'test@tedy.online', name: 'Test User', picture: '' },
    name: 'Deneme Öğrenci', student_no: '100', class_name: '7-D', branch: 'D',
    fields: { 'Okul No': '100', 'Doğum Tarihi': '01.01.2014', 'İkinci Yabancı Dil': 'Fransızca', 'Servis No': '12' },
    photo_data_url: '', scraped_at: '2026-09-16T08:05:00',
  },
  sebit: { completed_count: 1, courses: ['Matematik'], homework: [
    { classes: '7-D', completed: true, course: 'Matematik', course_code: 'MAT', end_date: '2026-09-20', id: 's1',
      list_id: 'l1', progress: 1.0, start_date: '2026-09-14', state: 2, state_text: 'Tamamlandı', teacher: 'Öğretmen', title: 'Tam sayılar tekrar' },
  ], scraped_at: '2026-09-16T08:05:00', total_homework: 1 },
  'progress/a3k': { class_name: '7-D', dashboard_stats: { completed: 3, firstTryScore: 80, scoredAboveLine: 3, target: 5 },
    lessons: [], scraped_at: '2026-09-16T08:05:00', teacher_assigned_completed: 3, teacher_assigned_count: 5, total_lessons: 3 },
  calendar: { events: [] },
}
