// A port of src/portal_susu.py `temiz_metin`, kept rule for rule: the API
// already serves course content clean, and this is the page's own defence if
// raw scraped text ever reaches it. Between "Daha fazla oku" and "Yorum Ekle"
// the portal renders other children's names and comments; a blank line does
// not end the block and an unclosed block runs to the end of the text.

const YORUM_BASI = 'Daha fazla oku'
const YORUM_SONU = 'Yorum Ekle'
const SUS = /^(?:Daha fazla oku|Yorum Ekle|İlk yorum yapan sen olmak ister misin\?|\d+ Yorum yapıldı!)$/

export function portalSusunuAyikla(metin: string): string {
  const satirlar: string[] = []
  let yorumda = false
  for (const ham of (metin ?? '').split('\n')) {
    const s = ham.split(/\s+/).filter(Boolean).join(' ')
    if (yorumda) {
      if (s === YORUM_SONU) yorumda = false
      continue
    }
    if (s === YORUM_BASI) {
      yorumda = true
      continue
    }
    if (SUS.test(s)) continue
    if (!s) {
      if (satirlar.length > 0 && satirlar[satirlar.length - 1]) satirlar.push('')
      continue
    }
    satirlar.push(s)
  }
  return satirlar.join('\n').trim()
}
