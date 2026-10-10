/**
 * Bugün's time logic, kept free of React and of the browser so node:test can
 * pin it (tests/bugun.test.ts). The page (components/TodaySchedule.tsx) builds
 * the day's agenda from the API and asks these functions what to say.
 *
 * Every string here is sentence case (talimatname S38): "Okuldan sonra", not
 * "OKULDAN SONRA". Capitals belong to CSS, and this page uses none.
 */

/** First bell, last bell, the end of the focus window, bedtime — minutes. */
export const SCHOOL_START = 8 * 60
export const SCHOOL_END = 15 * 60 + 45
// Işık's sustained-attention window closes before homework hours begin, so the
// stretch between the last bell and the window's edge is the most valuable time
// in the day and the interface spends it on one demanding thing. See §2 of
// docs/frontend-design-principles.md — this is a parameter, not a fact of life.
export const FOCUS_END = 16 * 60
export const BEDTIME = 22 * 60 + 30

export const DAYS_TR = ['Pazar', 'Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi']
export const MONTHS_TR = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']

export type AgendaType = 'lesson' | 'ogep' | 'deadline' | 'private_lesson' | 'event'

/** The part of an agenda item the time logic reads. */
export interface AgendaSlot {
  type: AgendaType
  startMin: number
  endMin: number
  isActive: boolean
  isPast: boolean
}

export function toMinutes(h: number, m: number): number { return h * 60 + m }

export function clockOf(minutes: number): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(Math.floor(minutes / 60))}:${pad(minutes % 60)}`
}

export function isSameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear()
    && a.getMonth() === b.getMonth()
    && a.getDate() === b.getDate()
}

export function compareCalendarDay(target: Date, reference: Date): -1 | 0 | 1 {
  const t = new Date(target.getFullYear(), target.getMonth(), target.getDate()).getTime()
  const r = new Date(reference.getFullYear(), reference.getMonth(), reference.getDate()).getTime()
  if (t === r) return 0
  return t < r ? -1 : 1
}

/**
 * Is there school on this day?
 *
 * The timetable says so when we have one: a day whose column is empty is not
 * a school day, whatever the calendar. Without a timetable (the portal refused
 * it, or the first sync has not run) Monday to Friday is the honest guess —
 * guessing "no school" on a Wednesday would have the card say "Şimdi" at 07:00.
 */
export function okulGunuMu(dersSayisi: number, tarih: Date, programVar: boolean): boolean {
  if (programVar) return dersSayisi > 0
  const g = tarih.getDay()
  return g >= 1 && g <= 5
}

export interface Ses {
  eyebrow: string
  hint?: string
  /** Where the work is anchored on the Day Strip, minutes. */
  anchorMin?: number
}

/**
 * When the card's work happens, said in one or two words (İ4).
 *
 * On a school day the focus window is 08:00–16:00 and "Şimdi" only belongs in
 * the quarter hour between the last bell and the window's edge: before school
 * and during lessons the work waits for "Okuldan sonra", anchored at 15:45.
 *
 * A day without school has no "after school" to point at — measured
 * 2026-10-10, a Saturday morning's reading card said "OKULDAN SONRA". There the
 * morning and the afternoon are "Şimdi", the evening "Bu akşam" and past
 * bedtime "Yarın". Before 08:00 it is "Bugün": "Şimdi" at 03:15 would pretend
 * the next ten minutes are the slot.
 */
export function windowVoice(minutes: number, kind: 'work' | 'reading', okulGunu = true): Ses {
  const afterBedtime = minutes >= BEDTIME
  const afterWindow = minutes >= FOCUS_END
  const beforeSchool = minutes < SCHOOL_START

  if (!okulGunu) {
    if (afterBedtime) {
      return { eyebrow: 'Yarın', hint: kind === 'work' ? 'Bunu yarın yapmak daha kolay' : undefined }
    }
    if (afterWindow) return { eyebrow: 'Bu akşam' }
    if (beforeSchool) return { eyebrow: 'Bugün' }
    return { eyebrow: 'Şimdi' }
  }

  const beforeLastBell = !beforeSchool && minutes < SCHOOL_END
  if (kind === 'work') {
    if (afterBedtime) return { eyebrow: 'Yarın', hint: 'Bunu yarın okuldan sonra yapmak daha kolay' }
    if (afterWindow) return { eyebrow: 'Bu akşam' }
    if (beforeSchool || beforeLastBell) {
      return { eyebrow: 'Okuldan sonra', hint: 'Bunu okuldan sonra yapmak daha kolay', anchorMin: SCHOOL_END }
    }
    return { eyebrow: 'Şimdi' }
  }

  if (afterBedtime) return { eyebrow: 'Yarın', hint: 'Yarın okuldan sonra daha kolay' }
  if (afterWindow) return { eyebrow: 'Bu akşam' }
  if (beforeSchool) return { eyebrow: 'Bugün', hint: 'Bunu okuldan sonra yapmak daha kolay' }
  // During lessons the card is a preview under the lesson; "Şimdi" there
  // would contradict the lesson card above it.
  if (beforeLastBell) return { eyebrow: 'Okuldan sonra' }
  return { eyebrow: 'Şimdi' }
}

/** The kinds of item that are a place to be. Calendar events stay on the
 *  timeline but never take the card: the live takvim carries 48–55 events,
 *  some running all school day (an election, a trip), and one of those used to
 *  sit on the card as "Şu an" from 08:00 to 15:45 in place of the lesson. */
const YER_TURLERI: ReadonlySet<AgendaType> = new Set(['lesson', 'ogep', 'private_lesson'])

export function yerMi(a: AgendaSlot): boolean { return YER_TURLERI.has(a.type) }

export interface YerSecimi<T extends AgendaSlot> {
  /** Where to be now, or next. */
  simdiki?: T
  /** The place after that. */
  sonraki?: T
  /** True while nothing of today has started yet. */
  ilk: boolean
  /** Lessons not yet begun. */
  kalanDers: number
  /** End of the last lesson, minutes; 0 on a day without lessons. */
  sonZil: number
  dersSayisi: number
}

/** Where to be, read off today's agenda (sorted by start). */
export function yerSec<T extends AgendaSlot>(agenda: readonly T[]): YerSecimi<T> {
  const yerler = agenda.filter(yerMi)
  const dersler = agenda.filter(a => a.type === 'lesson')
  const simdiki = yerler.find(a => a.isActive) ?? yerler.find(a => !a.isPast)
  return {
    simdiki,
    sonraki: simdiki ? yerler.find(a => a.startMin > simdiki.startMin) : undefined,
    ilk: simdiki != null && !yerler.some(a => a.isPast || a.isActive),
    kalanDers: dersler.filter(a => !a.isPast && !a.isActive).length,
    sonZil: dersler.reduce((m, a) => Math.max(m, a.endMin), 0),
    dersSayisi: dersler.length,
  }
}

/** The lesson card's eyebrow: "Şu an · 10 dk kaldı", "İlk ders · 08:00",
 *  "Sıradaki · 5 dk sonra" (or the start time when it is over an hour off). */
export function simdiUstu(yer: AgendaSlot, nowMin: number, ilk: boolean): string {
  if (yer.isActive) return `Şu an · ${yer.endMin - nowMin} dk kaldı`
  const baslar = clockOf(yer.startMin)
  if (ilk && yer.type === 'lesson') return `İlk ders · ${baslar}`
  const kala = yer.startMin - nowMin
  return `Sıradaki · ${kala <= 60 ? `${kala} dk sonra` : baslar}`
}

/** "7 ders, 1 etkinlik bitti": what the folded line is holding, in words. */
export function bitenOzeti(items: readonly AgendaSlot[]): string {
  const ders = items.filter(a => a.type === 'lesson').length
  const teslim = items.filter(a => a.type === 'deadline').length
  const diger = items.length - ders - teslim
  const parcalar: string[] = []
  if (ders) parcalar.push(`${ders} ders`)
  if (diger) parcalar.push(`${diger} etkinlik`)
  if (teslim) parcalar.push(`${teslim} teslim`)
  return `${parcalar.join(', ')} bitti`
}

/**
 * The next day with lessons, at most a week ahead. The timetable repeats week
 * to week (measured 2026-09-20), so next Monday reads from this week's grid.
 */
export function sonrakiOkulGunu(
  bugun: Date, dersVar: (gun: Date) => boolean, sinir = 7,
): { k: number; tarih: Date } | null {
  const bas = new Date(bugun)
  bas.setHours(0, 0, 0, 0)
  for (let k = 1; k <= sinir; k++) {
    const gun = new Date(bas)
    gun.setDate(bas.getDate() + k)
    if (dersVar(gun)) return { k, tarih: gun }
  }
  return null
}

/** "Yarın · Cuma" for tomorrow, the bare day name further out. */
export function yarinBasligi(k: number, tarih: Date): string {
  const ad = DAYS_TR[tarih.getDay()]
  return k === 1 ? `Yarın · ${ad}` : ad
}

/**
 * A string cut into its words and its figures, so only the figures are set in
 * Plex Mono (`.tedy-time`, talimatname [3.3-5]): "Sonra: Fen 11:20" →
 * text "Sonra: Fen ", figure "11:20". Only for strings this page composes —
 * never for a course or homework title, where "2. HAFTA" is a name.
 */
export function rakamParcala(metin: string): { metin: string; rakam: boolean }[] {
  const parcalar: { metin: string; rakam: boolean }[] = []
  const re = /\d{1,2}:\d{2}|\d+/g
  let son = 0
  for (const m of metin.matchAll(re)) {
    const i = m.index ?? 0
    if (i > son) parcalar.push({ metin: metin.slice(son, i), rakam: false })
    parcalar.push({ metin: m[0], rakam: true })
    son = i + m[0].length
  }
  if (son < metin.length) parcalar.push({ metin: metin.slice(son), rakam: false })
  return parcalar
}
