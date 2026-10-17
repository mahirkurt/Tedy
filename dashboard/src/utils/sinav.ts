import type { ExamItem } from '../types.ts'
import { getExamCountdown } from './countdown.ts'
import type { CountdownResult } from './countdown.ts'
import { MONTHS_SHORT } from './formatters.ts'

const SAAT_48 = 48 * 3600 * 1000
const GUN_7 = 7 * 24 * 3600 * 1000

/** An exam's date as a Date. A date-only "YYYY-MM-DD" is LOCAL midnight —
 *  `new Date("2026-09-28")` is UTC midnight, which an Istanbul browser reads as
 *  03:00 (the API sends date-only for exams found in text). Anything else is
 *  an ISO string already in local wall-clock time. */
export function yerelAni(s: string | null | undefined): Date | null {
  if (!s) return null
  const g = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s)
  const d = g ? new Date(Number(g[1]), Number(g[2]) - 1, Number(g[3])) : new Date(s)
  return isNaN(d.getTime()) ? null : d
}

export function sinavAni(e: Pick<ExamItem, 'date'>): Date | null {
  return yerelAni(e.date)
}

/** When an exam is over for "upcoming" purposes: a timed exam at its start, an all-day (or
 *  date-only) exam at the end of that local day, 23:59 — on the exam day it has not passed yet. */
export function sinavBitisi(e: Pick<ExamItem, 'date' | 'allDay'>): Date | null {
  const d = sinavAni(e)
  if (!d) return null
  if (!e.allDay && !/^\d{4}-\d{2}-\d{2}$/.test(e.date ?? '')) return d
  return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59)
}

export function sinavGeriSayimi(e: Pick<ExamItem, 'date' | 'allDay'>, nowMs: number): CountdownResult {
  return getExamCountdown(sinavBitisi(e), nowMs)
}

// `ilkTespit` / `degisti` are written by the server as naive Istanbul wall-clock time. Read in a
// browser elsewhere they would shift by the zone difference and the 48-hour window with them, so a
// stamp without an offset is read as +03:00 (Turkey has no DST since 2016). One with Z/offset as is.
function an(s?: string | null): number {
  if (!s) return NaN
  const ofsetsiz = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?$/.test(s)
  return new Date(ofsetsiz ? `${s}+03:00` : s).getTime()
}

/** "Yeni"/"Değişti" — metinli etiket; renk tek başına anlam taşımaz (spec §8). */
export function sinavEtiketi(e: ExamItem, nowMs: number): 'Yeni' | 'Değişti' | null {
  const d = nowMs - an(e.degisti)
  if (d >= 0 && d < SAAT_48) return 'Değişti'
  const i = nowMs - an(e.ilkTespit)
  if (i >= 0 && i < SAAT_48) return 'Yeni'
  return null
}

// An exam that has begun (timed: its hour has passed; all-day: its day is over) is not "the nearest
// exam" even while the list still files it as upcoming.
export function enYakinSinav(exams: ExamItem[], nowMs: number, haric: Set<string>): ExamItem | null {
  const adaylar = exams
    .filter(e => e.status === 'upcoming' && e.date && !haric.has(e.id))
    .filter(e => (sinavBitisi(e)?.getTime() ?? NaN) > nowMs)
    .map(e => ({ e, t: sinavAni(e)?.getTime() ?? NaN }))
    .filter(x => !isNaN(x.t) && x.t - nowMs <= GUN_7)
    .sort((a, b) => a.t - b.t)
  return adaylar[0]?.e ?? null
}

/** List keys for topics: a topic the source names twice still gets its own key. */
export function konuAnahtarlari(konular: string[] | undefined): { anahtar: string; konu: string }[] {
  return (konular ?? []).map((konu, i) => ({ anahtar: `${i}:${konu}`, konu }))
}

export function konuOzeti(konular: string[] | undefined, n = 3): string {
  const liste = (konular ?? []).filter(Boolean)
  if (liste.length <= n) return liste.join(', ')
  return `${liste.slice(0, n).join(', ')} +${liste.length - n} konu`
}

export function zamanMetni(e: ExamItem): string {
  const gun = (iso: string) => {
    const [, a, g] = iso.slice(0, 10).split('-').map(Number)
    return `${g} ${MONTHS_SHORT[a - 1]}`
  }
  if (e.date) {
    const saat = !e.allDay && e.date.length >= 16 ? ` ${e.date.slice(11, 16)}` : ''
    return gun(e.date) + saat
  }
  if (e.hafta) return `${gun(e.hafta)} haftası`
  return 'Tarih belirsiz'
}
