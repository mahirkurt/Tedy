/**
 * Bugün's time logic, kept free of React and of the browser so node:test can
 * pin it (tests/bugun.test.ts). The page (components/TodaySchedule.tsx) builds
 * the day's agenda from the API and asks these functions what to say.
 *
 * Every string here is sentence case (talimatname S38): "Okuldan sonra", not
 * "OKULDAN SONRA". Capitals belong to CSS, and this page uses none.
 */

/** First bell and the last bell's default — minutes. */
export const SCHOOL_START = 8 * 60
export const SCHOOL_END = 15 * 60 + 45

/**
 * The household's evening in minutes (spec 2026-10-19, akşam çalışma planı):
 * the last bell, when Işık is ready for homework, where the hard work ends and
 * the light work ends, dinner, getting ready and bedtime, plus the two
 * "tell the family" thresholds and who is told. Read from the server
 * (`/api/aksam-duzeni`, stored in `output/aksam_duzeni.json`, set on Profil —
 * talimatname B29); the defaults below are the family's own evening, used
 * until it loads and whenever what arrives is not a well-formed one. Işık's
 * sustained-attention window is a parameter, not a fact of life (§2 of
 * docs/frontend-design-principles.md).
 */
export interface AksamDuzeni {
  okulBitisi: number
  odeveHazir: number
  zorIsSonu: number
  hafifIsSonu: number
  yemek: number
  yemekDk: number
  hazirlik: number
  yatma: number
  baslamadiEsikDk: number
  takildiEsikDk: number
  haberAlacaklar: string[]
}

export const VARSAYILAN_DUZEN: AksamDuzeni = {
  okulBitisi: SCHOOL_END,
  odeveHazir: 17 * 60,
  zorIsSonu: 19 * 60,
  hafifIsSonu: 19 * 60 + 30,
  yemek: 18 * 60 + 30,
  yemekDk: 30,
  hazirlik: 20 * 60 + 30,
  yatma: 21 * 60,
  baslamadiEsikDk: 15,
  takildiEsikDk: 15,
  haberAlacaklar: [],
}

const SAAT_RE = /^([01]\d|2[0-3]):([0-5]\d)$/

/** "15:45" → 945, or null for anything that is not a 24-hour HH:MM. */
export function saattenDakika(s: unknown): number | null {
  const m = typeof s === 'string' ? SAAT_RE.exec(s.trim()) : null
  return m ? Number(m[1]) * 60 + Number(m[2]) : null
}

/** The server's own sentences (src/aksam_duzeni.py), so the form can say them before sending. */
export const SIRA_HATASI = 'Saatler sırayla olmalı: okul bitişi, ödeve hazır, zor işlerin sonu, hafif işlerin sonu, hazırlık, sonra yatma.'
export const YEMEK_HATASI = 'Yemek, ödeve hazır olma saati ile hazırlık arasında kalmalı ve süresi sığmalı.'
export const YEMEK_SURESI_HATASI = 'Yemek süresi 10 ile 60 dakika arasında olmalı.'
export const ESIK_HATASI = 'Haber verme süreleri 5 ile 60 dakika arasında olmalı.'

const aralikta = (n: number, alt: number, ust: number) => Number.isInteger(n) && n >= alt && n <= ust

/** The first rule the evening breaks, in the server's wording; null when it holds. */
export function duzenHatasi(d: AksamDuzeni): string | null {
  if (!aralikta(d.yemekDk, 10, 60)) return YEMEK_SURESI_HATASI
  if (!aralikta(d.baslamadiEsikDk, 5, 60) || !aralikta(d.takildiEsikDk, 5, 60)) return ESIK_HATASI
  if (!(d.okulBitisi <= d.odeveHazir && d.odeveHazir < d.zorIsSonu && d.zorIsSonu <= d.hafifIsSonu
    && d.hafifIsSonu <= d.hazirlik && d.hazirlik < d.yatma)) return SIRA_HATASI
  if (!(d.odeveHazir <= d.yemek && d.yemek <= d.hazirlik - d.yemekDk)) return YEMEK_HATASI
  return null
}

/** The API's snake_case evening as minutes; the defaults otherwise. */
export function duzenCoz(json: unknown): AksamDuzeni {
  if (!json || typeof json !== 'object') return VARSAYILAN_DUZEN
  const j = json as Record<string, unknown>
  const saat = (k: string) => saattenDakika(j[k])
  const okulBitisi = saat('okul_bitisi'), odeveHazir = saat('odeve_hazir'), zorIsSonu = saat('zor_is_sonu')
  const hafifIsSonu = saat('hafif_is_sonu'), yemek = saat('yemek'), hazirlik = saat('hazirlik'), yatma = saat('yatma')
  if (okulBitisi === null || odeveHazir === null || zorIsSonu === null || hafifIsSonu === null
    || yemek === null || hazirlik === null || yatma === null) return VARSAYILAN_DUZEN
  const sayi = (k: string) => (typeof j[k] === 'number' ? (j[k] as number) : NaN)
  const haber = Array.isArray(j.haber_alacaklar)
    ? j.haber_alacaklar.filter((e): e is string => typeof e === 'string') : []
  const d: AksamDuzeni = {
    okulBitisi, odeveHazir, zorIsSonu, hafifIsSonu, yemek, yemekDk: sayi('yemek_dk'), hazirlik, yatma,
    baslamadiEsikDk: sayi('baslamadi_esik_dk'), takildiEsikDk: sayi('takildi_esik_dk'), haberAlacaklar: haber,
  }
  return duzenHatasi(d) === null ? d : VARSAYILAN_DUZEN
}

/** The body `PUT /api/aksam-duzeni` takes. */
export function duzenGovdesi(d: AksamDuzeni) {
  return {
    okul_bitisi: clockOf(d.okulBitisi),
    odeve_hazir: clockOf(d.odeveHazir),
    zor_is_sonu: clockOf(d.zorIsSonu),
    hafif_is_sonu: clockOf(d.hafifIsSonu),
    yemek: clockOf(d.yemek),
    yemek_dk: d.yemekDk,
    hazirlik: clockOf(d.hazirlik),
    yatma: clockOf(d.yatma),
    baslamadi_esik_dk: d.baslamadiEsikDk,
    takildi_esik_dk: d.takildiEsikDk,
    haber_alacaklar: d.haberAlacaklar,
  }
}

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
 * On a school day "Şimdi" belongs to [ödeve hazır, zor işlerin sonu) — 17:00 to
 * 19:00 by default: before it, through school and the way home, the work waits
 * for "Okuldan sonra", anchored at the hour Işık is ready for homework.
 *
 * A day without school has no "after school" to point at — measured
 * 2026-10-10, a Saturday morning's reading card said "OKULDAN SONRA". There the
 * morning and the afternoon are "Şimdi", the evening "Bu akşam" and past
 * bedtime "Yarın". Before 08:00 it is "Bugün": "Şimdi" at 03:15 would pretend
 * the next ten minutes are the slot.
 */
export function windowVoice(
  minutes: number, kind: 'work' | 'reading', okulGunu = true, duzen: AksamDuzeni = VARSAYILAN_DUZEN,
): Ses {
  const afterBedtime = minutes >= duzen.yatma
  const afterWindow = minutes >= duzen.zorIsSonu
  const beforeSchool = minutes < SCHOOL_START

  if (!okulGunu) {
    if (afterBedtime) {
      return { eyebrow: 'Yarın', hint: kind === 'work' ? 'Bunu yarın yapmak daha kolay' : undefined }
    }
    if (afterWindow) return { eyebrow: 'Bu akşam' }
    if (beforeSchool) return { eyebrow: 'Bugün' }
    return { eyebrow: 'Şimdi' }
  }

  // "Şimdi" belongs to [ödeve hazır, zor işlerin sonu); the walk home and the
  // snack before it are still "Okuldan sonra", anchored where homework starts.
  const beforeLastBell = !beforeSchool && minutes < duzen.odeveHazir
  if (kind === 'work') {
    if (afterBedtime) return { eyebrow: 'Yarın', hint: 'Bunu yarın okuldan sonra yapmak daha kolay' }
    if (afterWindow) return { eyebrow: 'Bu akşam' }
    if (beforeSchool || beforeLastBell) {
      return { eyebrow: 'Okuldan sonra', hint: 'Bunu okuldan sonra yapmak daha kolay', anchorMin: duzen.odeveHazir }
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
