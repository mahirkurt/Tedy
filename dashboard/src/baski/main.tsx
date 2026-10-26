import { createRoot } from 'react-dom/client'
import { flushSync } from 'react-dom'
import { Theme } from '@carbon/react'
import KilavuzBelgesi from '../hazirlik/KilavuzBelgesi'
import { damgaMetni, ustBilgi } from '../hazirlik/belge'
import { modelAdresi } from '../hazirlik/hazirlik'
import type { KilavuzModeli } from '../hazirlik/tipler'
import { baskiSorgusuCoz } from './sorgu'
import { sayfala } from './sayfalama'
import './baski.scss'

declare global {
  interface Window { __KILAVUZ_HAZIR__?: { sayfa: number }; __KILAVUZ_HATA__?: string }
}

/** Baskı görünümü (spec §5.1, plan kararı 1): ekrandaki KilavuzBelgesi kâğıt kipinde; model API'den (tarayıcıda oturum
 *  çereziyle, sunucuda kilavuz-pdf.mjs'in sahte kökünden). Hazır olunca kilavuz-pdf.mjs'e sinyal verir. */
async function baslat(): Promise<void> {
  const s = baskiSorgusuCoz(location.search)
  if (!s) throw new Error('Baskı adresi eksik: ?ders=<ders>&sinav=1|2 gerekli.')
  const r = await fetch(modelAdresi(s.ders, s.sinav, s.senaryo, s.secenekler), { credentials: 'include' })
  if (!r.ok) throw new Error(`Kılavuz alınamadı (HTTP ${r.status}).`)
  const m = await r.json() as KilavuzModeli
  // Düz yolda (yedek) Chrome'un üst bilgisi belge başlığını basar: damga da başlığa girer (K5 B metni, K12).
  document.title = s.duz ? `${ustBilgi(m)} — ${damgaMetni(m)}` : ustBilgi(m)
  const kaynak = document.getElementById('kaynak')!
  flushSync(() => createRoot(kaynak).render(<Theme theme="white"><KilavuzBelgesi model={m} kip="baski" /></Theme>))
  await document.fonts.ready
  window.__KILAVUZ_HAZIR__ = { sayfa: s.duz ? 0 : await sayfala(kaynak) }
}

baslat().catch(e => { window.__KILAVUZ_HATA__ = e instanceof Error ? e.message : String(e) })
