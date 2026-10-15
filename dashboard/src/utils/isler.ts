// İşler'in saf yarısı (yenileme 2026-10-15, spec docs/superpowers/specs/2026-10-15-isler-yenileme-design.md):
// işler hangi gruba düşer, sıradaki hangisidir, teslim nasıl okunur. Sayfa yalnız çizer.
import type { ExamItem, HomeworkItem } from '../types'
import { kisaGun, kisaTeslim, MONTHS_SHORT, parseDeadline } from './formatters.ts'
import { sinavAni, zamanMetni } from './sinav.ts'

export type IsGrubu = 'yapilan' | 'tamamlanan' | 'yapilmayan'

export interface IsGruplari {
  /** The one named step (İ1): the active work due soonest. Shown once, as the subject panel. */
  siradaki: HomeworkItem | null
  /** The rest of the active work, nearest deadline first — never the next thing again. */
  sonra: HomeworkItem[]
  /** Işık marked it done; the teacher has not said yet. */
  yapilan: HomeworkItem[]
  /** The teacher said "Yaptı". */
  tamamlanan: HomeworkItem[]
  /** The teacher said "Yapmadı"/"Eksik", or the deadline passed with no mark. */
  yapilmayan: HomeworkItem[]
}

/** The portal's verdict in its canonical spelling; anything unknown passes through as written. */
export function normalizeStatus(value: string): string {
  const raw = (value || '').trim().toLocaleLowerCase('tr-TR')
  if (['yaptı', 'yapti', 'tamamlandı', 'tamamlandi', 'done'].includes(raw)) return 'Yaptı'
  if (['yapmadı', 'yapmadi', 'missing', 'incomplete'].includes(raw)) return 'Yapmadı'
  if (raw === 'eksik') return 'Eksik'
  if (['değerlendirilmemiş', 'degerlendirilmemis', 'bekliyor', 'pending'].includes(raw)) return 'Değerlendirilmemiş'
  return value
}

const zamani = (hw: HomeworkItem) => parseDeadline(hw['Ödev Son Teslim Tarihi'])?.getTime()

// A row with no readable deadline sinks in both orders rather than sorting as 1970 (nearest) or as the far
// future (least urgent).
const teslimSirasi = (yon: 1 | -1) => (a: HomeworkItem, b: HomeworkItem) => {
  const at = zamani(a)
  const bt = zamani(b)
  if (at === undefined && bt === undefined) return 0
  if (at === undefined) return 1
  if (bt === undefined) return -1
  return (at - bt) * yon
}

/**
 * Two orders, because the groups answer two questions: work still to do is nearest-deadline-first (the thing
 * due tomorrow is reachable without scrolling, İ2/İ3); everything settled is history and reads newest-first.
 * The head of the active work is the next thing and is taken out of the list, so it is never named twice.
 */
export function isleriGrupla(odevler: readonly HomeworkItem[], simdiMs: number): IsGruplari {
  const aktif: HomeworkItem[] = []
  const yapilan: HomeworkItem[] = []
  const tamamlanan: HomeworkItem[] = []
  const yapilmayan: HomeworkItem[] = []
  for (const hw of odevler) {
    const durum = normalizeStatus(hw['Ödev Durumu'])
    if (durum === 'Yaptı') tamamlanan.push(hw)
    else if (durum === 'Yapmadı' || durum === 'Eksik') yapilmayan.push(hw)
    else if (hw.student_marked_done) yapilan.push(hw)
    else {
      const t = zamani(hw)
      if (t !== undefined && t <= simdiMs) yapilmayan.push(hw)
      else aktif.push(hw)
    }
  }
  aktif.sort(teslimSirasi(1))
  for (const gecmis of [yapilan, tamamlanan, yapilmayan]) gecmis.sort(teslimSirasi(-1))
  const [siradaki = null, ...sonra] = aktif
  return { siradaki, sonra, yapilan, tamamlanan, yapilmayan }
}

const buyukBasla = (s: string) => s.charAt(0).toLocaleUpperCase('tr-TR') + s.slice(1)
const gunu = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()

/**
 * When something is due, as a day and a time ("Yarın 12:00", "Pazartesi 08:55") — the words Bugün uses
 * (`kisaTeslim`), in sentence case because here they open their own cell. Beyond the week the date carries its
 * distance ("1 Eki 09:00 · 7 gün sonra", İ2); the past is a plain date. `bugun` is the one real urgency.
 * `saatsiz` is for a day with no hour (an all-day exam): the day alone, never an invented 00:00 (`kisaGun`).
 */
export function teslimMetni(teslim: Date, simdi: Date, saatsiz = false): { metin: string; bugun: boolean } {
  const fark = Math.round((gunu(teslim) - gunu(simdi)) / 86_400_000)
  if (fark < 0) {
    const saat = saatsiz ? '' : ` ${String(teslim.getHours()).padStart(2, '0')}:${String(teslim.getMinutes()).padStart(2, '0')}`
    return { metin: `${teslim.getDate()} ${MONTHS_SHORT[teslim.getMonth()]}${saat}`, bugun: false }
  }
  const metin = buyukBasla(saatsiz ? kisaGun(teslim, simdi) : kisaTeslim(teslim, simdi))
  return { metin: fark > 6 ? `${metin} · ${fark} gün sonra` : metin, bugun: fark === 0 }
}

/**
 * When an exam is, in an İşler row: a timed exam like a deadline; an all-day exam (the API's `allDay`, or a bare
 * "YYYY-MM-DD", which is the local day — C11, C20) as its day alone; an exam known only by its week, or with no
 * day, as the exam page says it ("28 Eyl haftası", "Tarih belirsiz"). Null when there is nothing to say.
 */
export function sinavZamani(e: ExamItem, simdi: Date): { metin: string; bugun: boolean } | null {
  const ani = sinavAni(e)
  if (ani) return teslimMetni(ani, simdi, e.allDay || /^\d{4}-\d{2}-\d{2}$/.test(e.date ?? ''))
  if (e.hafta || e.tarihBelirsiz) return { metin: zamanMetni(e), bugun: false }
  return null
}
