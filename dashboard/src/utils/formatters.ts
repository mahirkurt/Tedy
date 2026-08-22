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
  const match = dateStr.match(/(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})/)
  if (match) {
    const [, day, month, year, hour, min] = match
    return `${parseInt(day)} ${MONTHS_SHORT[parseInt(month) - 1]} ${year} ${hour}:${min}`
  }
  return dateStr
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

/** Capitalizes the first letter of each word (simple title-case). */
export function toTitleCase(str: string): string {
  return str.replace(/\S+/g, word => word.charAt(0).toUpperCase() + word.slice(1))
}
