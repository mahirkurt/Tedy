import { createRoot } from 'react-dom/client'
import { flushSync } from 'react-dom'
import { Theme } from '@carbon/react'
import YoklamaBelgesi from './YoklamaBelgesi'
import { sayfala } from './sayfalama'
import './baski.scss'

declare global {
  interface Window { __KILAVUZ_HAZIR__?: { sayfa: number }; __KILAVUZ_HATA__?: string }
}

async function baslat(): Promise<void> {
  const p = new URLSearchParams(location.search)
  if (p.get('yoklama') !== '1') throw new Error('Bu sayfa şimdilik yalnız yoklama kipinde açılır (?yoklama=1).')
  const duz = p.get('duz') === '1'
  const kaynak = document.getElementById('kaynak')!
  document.title = 'Fen Bilimleri · 1. yazılı · 2. senaryo — MEB tablosu 10.09.2026 · üretim 25.10.2026'
  const kok = createRoot(kaynak)
  // Kâğıt beyaz temadır: katman kutuları gray-10 (taslak A, "gri katman kutuları").
  flushSync(() => kok.render(<Theme theme="white"><YoklamaBelgesi /></Theme>))
  await document.fonts.ready
  window.__KILAVUZ_HAZIR__ = { sayfa: duz ? 0 : await sayfala(kaynak) }
}

baslat().catch(e => { window.__KILAVUZ_HATA__ = e instanceof Error ? e.message : String(e) })
