import type { ExamItem } from '../types.ts'
import { MONTHS_SHORT } from './formatters.ts'

const SAAT_48 = 48 * 3600 * 1000
const GUN_7 = 7 * 24 * 3600 * 1000

function an(s?: string | null): number {
  return s ? new Date(s).getTime() : NaN
}

/** "Yeni"/"Değişti" — metinli etiket; renk tek başına anlam taşımaz (spec §8). */
export function sinavEtiketi(e: ExamItem, nowMs: number): 'Yeni' | 'Değişti' | null {
  const d = nowMs - an(e.degisti)
  if (d >= 0 && d < SAAT_48) return 'Değişti'
  const i = nowMs - an(e.ilkTespit)
  if (i >= 0 && i < SAAT_48) return 'Yeni'
  return null
}

export function enYakinSinav(exams: ExamItem[], nowMs: number, haric: Set<string>): ExamItem | null {
  const adaylar = exams
    .filter(e => e.status === 'upcoming' && e.date && !haric.has(e.id))
    .map(e => ({ e, t: an(e.date) }))
    .filter(x => !isNaN(x.t) && x.t - nowMs <= GUN_7)
    .sort((a, b) => a.t - b.t)
  return adaylar[0]?.e ?? null
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
