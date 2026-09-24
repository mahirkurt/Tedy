import type { Page } from '@playwright/test'
import { mock, LIVE } from './_audit-fixtures'

// The week of 21-27 Eylül 2026, shaped like the portal's grid: day names in
// caps in row 0, a blank header over each block's time column, Friday on its
// own later bell in the second block, Thursday's periods 6-7 empty because
// the club presentation takes that slot.
type Satir = { saat: string; pzt?: string; pers?: string; cumaSaat?: string; cuma?: string }

const SATIRLAR: Satir[] = [
  { saat: '1. Ders\n\n08:00 - 08:40', pzt: 'Türkçe\nEda Şen', pers: 'Matematik\nNagihan Özdemir',
    cumaSaat: '1. Ders\n\n08:00 - 08:40', cuma: 'Sosyal Bilgiler\nEmre Angıç' },
  { saat: '2. Ders\n\n08:55 - 09:35', pzt: 'Fransızca\nHarika Ebru Kalkan', pers: 'İngilizce\nMerima Gueller',
    cumaSaat: '2. Ders\n\n09:00 - 09:40', cuma: 'Fen Bilimleri\nYasemin Kuzucu' },
  { saat: '3. Ders\n\n09:45 - 10:25', pzt: 'İngilizce\nİpek Pehlevan', pers: 'İngilizce\nMerima Gueller',
    cumaSaat: '3. Ders\n\n09:50 - 10:30', cuma: 'Türkçe\nEda Şen' },
  { saat: '4. Ders\n\n10:35 - 11:15', pers: 'Matematik\nElif Özge Şener',
    cumaSaat: '4. Ders\n\n10:40 - 11:20', cuma: 'Müzik\nAyşe Kaya' },
  { saat: '5. Ders\n\n11:20 - 12:00', pers: 'Fen Bilimleri\nYasemin Kuzucu',
    cumaSaat: '5. Ders\n\n11:30 - 12:10', cuma: 'İngilizce\nİpek Pehlevan' },
  { saat: '6. Ders\n\n12:40 - 13:20' },
  { saat: '7. Ders\n\n13:30 - 14:10' },
  { saat: '8. Ders\n\n14:15 - 14:55', pers: 'Türkçe\nEda Şen' },
  { saat: '9. Ders\n\n15:05 - 15:45', pers: 'Kültür ve Medeniyetimize Yön Verenler\nEda Şen' },
]

export const SCHEDULE = {
  weeks: [], today: 'Perşembe',
  latest: {
    week_label: '2. Hafta 21 Eyl. - 27 Eyl.', is_current: true,
    schedule: {
      headers: [],
      rows: [
        ['', 'PAZARTESI', 'SALI', 'ÇARŞAMBA', 'PERŞEMBE', '', 'CUMA', 'CUMARTESI', 'PAZAR'],
        ...SATIRLAR.map(s =>
          [s.saat, s.pzt ?? '', '', '', s.pers ?? '', s.cumaSaat ?? '', s.cuma ?? '', '', '']),
      ],
    },
  },
}

export const HW = (ders: string, baslik: string, teslim: string, aciklama = '', ek: Record<string, unknown> = {}) => ({
  'Ders Adı': ders, 'Ödev Başlığı': baslik, 'Ödev Kaynağı': 'portal',
  'Ödev Son Teslim Tarihi': teslim, 'Ödev Durumu': 'Değerlendirilmemiş',
  'Ödev Görüntüle': 'Ödevi Görüntüle',
  detail: { description: aciklama, attachments: [] },
  ...ek,
})

export const MATEMATIK = HW('Matematik', '2. HAFTA MATEMATİK HAFTA İÇİ ÖDEVİ', '25.09.2026 12:00',
  'Ders kitabı sayfa 165, 1-12 arası soruları çözünüz.\nİyi çalışmalar')

export const HOMEWORK = {
  summary: '', homework: [
    MATEMATIK,
    HW('Fransızca', 'S1 Les verbes', '28.09.2026 08:55'),
    HW('Fen Bilimleri', 'Ödev (Hibrit 10-16)', '29.09.2026 12:00'),
  ],
}

// The portal hands the description over as HTML, and it repeats the title.
export const CALENDAR = { events: [{
  allDay: false, start: '2026-09-24T12:40:00', end: '2026-09-24T14:10:00',
  title: '5,6,7,8. Sınıflar Kulüp Tanıtımları',
  extendedProps: { description: '<p>5,6,7,8. Sınıflar Kulüp Tanıtımları</p>' },
}] }

/** Opens Bugün at a moment of the week. `anlik` is "2026-09-24T16:40", or a
 *  full ISO string with an offset when the browser runs in another zone. Pass
 *  `homework: null` to route /api/homework yourself. */
export async function bugunAc(page: Page, anlik: string, ek: Record<string, unknown> = {}) {
  await page.clock.setFixedTime(new Date(/[+Z]/.test(anlik.slice(10)) ? anlik : `${anlik}:00`))
  const veri: Record<string, unknown> = {
    ...LIVE, schedule: SCHEDULE, homework: HOMEWORK, calendar: CALENDAR,
    teams: { ogep: [] }, books: { books: [] }, ...ek,
  }
  if (veri.homework === null) delete veri.homework
  await mock(page, veri)
  await page.goto('/')
  await page.waitForLoadState('networkidle')
  await page.locator('.next-thing').waitFor()
}

/** An exam as /api/exams returns it — local time, no "Z" (see _portal_yerel). */
export const SINAV = (id: string, title: string, date: string) => ({
  id, course: title, title, rawTitle: title, courseColor: '#9f1853',
  examNumber: null, date, endDate: null, allDay: false, status: 'upcoming',
  grade: null, studyGuide: null, aiSummary: null, relatedHomework: [], relatedContent: [],
})
