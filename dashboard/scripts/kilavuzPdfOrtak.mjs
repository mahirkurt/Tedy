// kilavuz-pdf.mjs'in saf yardımcıları (plan 2026-10-25 Görev 1); tests/kilavuz-pdf-ortak.test.ts sınar.
import { extname, resolve, sep } from 'node:path'

/** Baskı sayfasının sunulduğu sahte kök: başka her köke giden istek kesilir (ağsız basım). */
export const KOK = 'https://baski.tedy.yerel'

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.woff2': 'font/woff2', '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon',
  '.json': 'application/json', '.webmanifest': 'application/manifest+json',
}

export function argumanlariCoz(argv) {
  const a = { dist: null, model: null, cikti: null, sorgu: '', duz: false, sure: 45000 }
  for (let i = 0; i < argv.length; i += 1) {
    const k = argv[i]
    if (k === '--duz') { a.duz = true; continue }
    const v = argv[i + 1]
    if (v === undefined) throw new Error(`${k} için değer yok`)
    if (k === '--dist') a.dist = v
    else if (k === '--model') a.model = v
    else if (k === '--cikti') a.cikti = v
    else if (k === '--sorgu') a.sorgu = v
    else if (k === '--sure') {
      a.sure = Number(v)
      if (!Number.isInteger(a.sure) || a.sure < 1000) throw new Error('--sure en az 1000 ms')
    } else throw new Error(`bilinmeyen argüman: ${k}`)
    i += 1
  }
  if (!a.dist || !a.cikti) throw new Error('--dist ve --cikti gerekli')
  return a
}

/** URL yol adını dist altındaki dosyaya çevirir; dist dışına çıkan, NUL taşıyan ya da çözülemeyen yol null. */
export function guvenliYol(dist, yolAdi) {
  let cozulmus
  try { cozulmus = decodeURIComponent(yolAdi) } catch { return null }
  if (cozulmus.includes('\0')) return null
  const kok = resolve(dist)
  const tam = resolve(kok, `.${cozulmus.startsWith('/') ? cozulmus : `/${cozulmus}`}`)
  return tam === kok || tam.startsWith(kok + sep) ? tam : null
}

export function mimeTuru(yol) {
  return MIME[extname(yol).toLowerCase()] ?? 'application/octet-stream'
}

export function baskiAdresi(sorgu, duz) {
  const q = new URLSearchParams(sorgu)
  if (duz) q.set('duz', '1')
  return `${KOK}/baski.html?${q}`
}
