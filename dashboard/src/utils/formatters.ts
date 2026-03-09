const MONTHS = ['Oca', 'Sub', 'Mar', 'Nis', 'May', 'Haz',
                'Tem', 'Agu', 'Eyl', 'Eki', 'Kas', 'Ara']

export function formatTurkishDate(dateStr: string): string {
  if (!dateStr) return ''
  const match = dateStr.match(/(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})/)
  if (match) {
    const [, day, month, year, hour, min] = match
    return `${parseInt(day)} ${MONTHS[parseInt(month) - 1]} ${year} ${hour}:${min}`
  }
  return dateStr
}

export function parseDeadline(dateStr: string): Date | null {
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
    case 'Yapti': return { label: 'Tamamlandı', type: 'green' }
    case 'Yapmadi': return { label: 'Yapılmadı', type: 'red' }
    case 'Eksik': return { label: 'Eksik', type: 'warm-gray' }
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
