/** Strip presentation marks while preserving fractions and identifiers. */
export function okunacakMetin(text: string): string {
  return text.replace(/\r\n/g, '\n')
    .replace(/```[^\n]*\n([\s\S]*?)```/g, '$1').replace(/```/g, '')
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/\s?\[S\d+\]/g, '')
    .replace(/`([^`]+)`/g, '$1').replace(/\*\*|__/g, '')
    .replace(/^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/gm, '')
    .replace(/^\s*(?:#{1,6}\s+|> ?|[-+*]\s+|\d+\.\s+)/gm, '')
    .replace(/[*_]/g, (mark, offset: number, value: string) => {
      const before = value[offset - 1] || ''
      const after = value[offset + 1] || ''
      return ((/\s/.test(before) && /\s/.test(after))
        || (/[\p{L}\p{N}]/u.test(before) && /[\p{L}\p{N}]/u.test(after))) ? mark : ''
    })
    .replace(/\s+/g, ' ').trim()
}

export function turkceSes<T extends { lang: string }>(voices: T[]): T | null {
  const lang = (v: T) => v.lang.replace(/_/g, '-').toLowerCase()
  return voices.find(v => lang(v) === 'tr-tr') ?? voices.find(v => lang(v).startsWith('tr')) ?? null
}

export function birlestir(taban: string, ek: string): string {
  return [taban.trim(), ek.trim()].filter(Boolean).join(' ')
}

export function onayAnahtari(email: string | null): string | null {
  const normalized = email?.trim().toLowerCase()
  return normalized ? `tedy-ses-onay::${normalized}` : null
}
