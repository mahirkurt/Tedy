export const MONTHS_SHORT = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz',
                             'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara']

export const COURSE_CONTENT_ORDER = [
  'Genel',
  'Matematik',
  'Fen Bilimleri',
  'Sosyal Bilgiler',
  'Türkçe',
  'İngilizce',
  'İngilizce (Language)',
  'Fransızca',
  'Ahlak ve Yurttaşlık',
  'Bilişim Teknolojileri',
  'Din Kültürü ve Ahlak',
] as const

const COURSE_ALIASES: Record<string, string[]> = {
  'Genel': ['Genel', 'TED Genel', 'Sınıf Öğretmeni', 'PDR'],
  'Matematik': ['Matematik'],
  'Fen Bilimleri': ['Fen Bilimleri'],
  'Sosyal Bilgiler': ['Sosyal Bilgiler'],
  'Türkçe': ['Türkçe'],
  'İngilizce': ['İngilizce', 'İngilizce Literature', 'İngilizce (Literature)'],
  'İngilizce (Language)': ['İngilizce (Language)', 'İngilizce Language', 'İngilizce (2)'],
  'Fransızca': [
    'Fransızca',
    'İkinci Yabancı Dil',
    'İkinci Yabancı Dil (Fransızca)',
    '2. Yabancı Dil (F)',
    'Français (İkinci Yabancı Dil (Fransızca))',
  ],
  'Ahlak ve Yurttaşlık': ['Ahlak ve Yurttaşlık', 'Ahlak ve Yurttaşlık Eğitimi'],
  'Bilişim Teknolojileri': ['Bilişim Teknolojileri', 'Bilişim'],
  'Din Kültürü ve Ahlak': ['Din Kültürü ve Ahlak', 'Din Kültürü', 'Din Kültürü ve Ahlak Bilgisi', 'DKAB'],
}

const COURSE_LOOKUP = Object.entries(COURSE_ALIASES).reduce<Record<string, string>>((acc, [canonical, aliases]) => {
  acc[canonical] = canonical
  for (const alias of aliases) acc[alias] = canonical
  return acc
}, {})

const COURSE_ALIASES_LONGEST_FIRST = Object.keys(COURSE_LOOKUP).sort((a, b) => b.length - a.length)

export function normalizeCourseDisplayName(name: string): string {
  const raw = name.trim()
  if (!raw) return raw

  if (COURSE_LOOKUP[raw]) return COURSE_LOOKUP[raw]

  for (const alias of COURSE_ALIASES_LONGEST_FIRST) {
    if (!raw.startsWith(alias)) continue
    const nextChar = raw.charAt(alias.length)
    if (!nextChar || nextChar === ' ' || nextChar === '(') {
      return COURSE_LOOKUP[alias]
    }
  }

  const stripped = raw.replace(/\s*\(.*\)\s*$/, '').trim()
  if (COURSE_LOOKUP[stripped]) return COURSE_LOOKUP[stripped]

  return raw
}

export function formatTurkishDate(dateStr?: string | null): string {
  if (!dateStr) return ''

  // The portal's own format.
  const dotted = dateStr.match(/(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})/)
  if (dotted) {
    const [, day, month, year, hour, min] = dotted
    return `${parseInt(day)} ${MONTHS_SHORT[parseInt(month) - 1]} ${year} ${hour}:${min}`
  }

  // ISO, which is what first_seen carries. Without this branch the function
  // fell through to the line below and handed the caller its own input, so
  // "2026-03-11T23:29:16.752613" printed on screen — microseconds and all.
  const iso = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/)
  if (iso) {
    const [, year, month, day, hour, min] = iso
    return `${parseInt(day)} ${MONTHS_SHORT[parseInt(month) - 1]} ${year} ${hour}:${min}`
  }

  // Returning the input on failure is how internal text reaches a reader
  // (D4). An empty string is the honest answer: we could not read it, so we
  // have nothing to say. Callers must render on the RESULT, not the source.
  return ''
}

export function parseDeadline(dateStr?: string | null): Date | null {
  if (!dateStr) return null
  const match = dateStr.match(/(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})/)
  if (!match) return null
  const [, day, month, year, hour, min] = match
  return new Date(parseInt(year), parseInt(month) - 1, parseInt(day),
                  parseInt(hour), parseInt(min))
}

export function getHomeworkStatus(status: string): {
  label: string; type: 'green' | 'red' | 'blue' | 'gray' | 'warm-gray'
} {
  switch (status) {
    case 'Yaptı':
    case 'Yapti': return { label: 'Yaptı', type: 'green' }
    case 'Yapmadı':
    case 'Yapmadi': return { label: 'Yapmadı', type: 'red' }
    case 'Eksik': return { label: 'Eksik', type: 'warm-gray' }
    case 'Değerlendirilmemiş':
    case 'Degerlendirilmemis': return { label: 'Bekliyor', type: 'blue' }
    default: return { label: status, type: 'gray' }
  }
}

export function gradeColor(score: string): string {
  const n = parseInt(score)
  if (isNaN(n)) return ''
  if (n >= 85) return 'var(--status-success)'
  if (n >= 70) return 'var(--status-info)'
  if (n >= 50) return 'var(--status-warning)'
  return 'var(--status-error)'
}

/** Strips trailing " ," from each line then joins with ', '.
 *  Fixes portal data like "Gözde Enginler ,\nAyşe Sinem Değer" → "Gözde Enginler, Ayşe Sinem Değer"
 */
export function cleanTeacherNames(text: string): string {
  return text
    .split('\n')
    .map(line => line.replace(/\s*,\s*$/, '').trim())
    .filter(Boolean)
    .join(', ')
}

/** Plain text from a fragment the portal sends as HTML.
 *
 *  Calendar descriptions arrive as "<p>…</p>" and were printed verbatim under
 *  the event on Bugün (measured 2026-09-24) — internal representation reaching
 *  the reader (D4). DOMParser builds an inert document: nothing in it runs,
 *  and entities decode the way a browser would. */
export function htmlToText(s?: string | null): string {
  if (!s) return ''
  if (!/[<&]/.test(s)) return s.trim()
  const doc = new DOMParser().parseFromString(s, 'text/html')
  return (doc.body.textContent || '').replace(/\s+/g, ' ').trim()
}

const GUNLER = ['Pazar', 'Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi']

/** When something is due, in the words a person would use: "bugün 12:00",
 *  "yarın 12:00", "Pazartesi 08:55" within the week, "3 Eki 12:00" beyond it.
 *  A countdown ("1g 1s") makes the reader do the arithmetic; a day name does
 *  not. */
export function kisaTeslim(deadline: Date, now: Date): string {
  const gun = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
  const fark = Math.round((gun(deadline) - gun(now)) / 86_400_000)
  const saat = `${String(deadline.getHours()).padStart(2, '0')}:${String(deadline.getMinutes()).padStart(2, '0')}`
  if (fark === 0) return `bugün ${saat}`
  if (fark === 1) return `yarın ${saat}`
  if (fark > 1 && fark < 7) return `${GUNLER[deadline.getDay()]} ${saat}`
  return `${deadline.getDate()} ${MONTHS_SHORT[deadline.getMonth()]} ${saat}`
}

/** Turkish names for the scrape sections health.json reports on. Shared so the
 *  header popover and the portal-status banner cannot drift apart. */
export const SECTION_LABELS: Record<string, string> = {
  ogrenci_profili: 'Öğrenci Profili',
  odevlerim: 'Ödevler',
  ders_programi: 'Ders Programı',
  takvim: 'Takvim',
  gelisim_raporu: 'Notlar',
  ders_icerikleri: 'Ders İçerikleri',
  takim_calismalari: 'Takımlar',
  ogep: 'ÖGEP',
  duyurular: 'Duyurular',
}

/** A model identifier as a person would say it: "claude-sonnet-5" →
 *  "Claude Sonnet 5", "claude-opus-4-8" → "Claude Opus 4.8". The AI label
 *  names the model that wrote the answer; an API identifier there is internal
 *  representation reaching the reader (D4). Anything unrecognised passes
 *  through unchanged rather than being guessed at. */
export function modelAdi(id?: string | null): string {
  if (!id) return ''
  const m = id.match(/^claude-([a-z]+)-(\d+)(?:-(\d+))?$/)
  if (!m) return id
  const aile = m[1].charAt(0).toUpperCase() + m[1].slice(1)
  return `Claude ${aile} ${m[2]}${m[3] ? `.${m[3]}` : ''}`
}
