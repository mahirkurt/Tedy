import { useCallback, useSyncExternalStore } from 'react'
import { YUKLEME_ESIGI_MS } from './useApi'
import { GSI_GECIKME_MS, gsiDurumu, type GsiGorunum, type GsiKaydi } from '../utils/gsiDurumu'

/**
 * Google Identity Services' <script>, as a store the sign-in page reads (giriş sayfası yenilemesi, 2026-10-15).
 *
 * The page used to wait on the tag's `load` alone. A blocked request fires `error`, and a blocker can also
 * answer with an empty script that "loads" without `window.google` — either way the page showed no button and
 * no sentence (D3). The tag's own outcome, the skeleton threshold and the slow-script warning all live here, so
 * the component derives its state (`gsiDurumu`) instead of setting it from effects.
 */

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string
            callback: (response: { credential: string }) => void
            auto_select?: boolean
          }) => void
          renderButton: (
            element: HTMLElement,
            config: {
              theme?: string
              size?: string
              width?: number
              text?: string
              shape?: string
              locale?: string
            }
          ) => void
        }
      }
    }
  }
}

const BETIK_ID = 'google-gsi-script'
const KAYNAK = 'https://accounts.google.com/gsi/client'

let kayit: GsiKaydi | null = null
const dinleyiciler = new Set<() => void>()

function apiVar() {
  return Boolean(window.google?.accounts?.id)
}

function guncelle(betik: HTMLScriptElement, degisim: Partial<GsiKaydi>) {
  // A retried tag replaces the old one; the old tag's late events and timers must not touch the new record.
  if (document.getElementById(BETIK_ID) !== betik || !kayit) return
  kayit = { ...kayit, ...degisim }
  dinleyiciler.forEach(f => f())
}

function betikEkle() {
  document.getElementById(BETIK_ID)?.remove()
  const betik = document.createElement('script')
  betik.id = BETIK_ID
  betik.src = KAYNAK
  betik.async = true
  kayit = { betik: 'yukleniyor', apiVar: apiVar(), esikGecti: false, gecikti: false }
  betik.addEventListener('load', () => guncelle(betik, { betik: 'yuklendi', apiVar: apiVar() }))
  betik.addEventListener('error', () => guncelle(betik, { betik: 'hata', apiVar: apiVar() }))
  window.setTimeout(() => guncelle(betik, { esikGecti: true }), YUKLEME_ESIGI_MS)
  window.setTimeout(() => guncelle(betik, { gecikti: true }), GSI_GECIKME_MS)
  document.head.appendChild(betik)
}

function abone(degisti: () => void) {
  dinleyiciler.add(degisti)
  if (!kayit) betikEkle()
  return () => { dinleyiciler.delete(degisti) }
}

const anlik = () => kayit
const sunucuda = () => null

export function useGsi(): { durum: GsiGorunum; yenidenDene: () => void } {
  const k = useSyncExternalStore(abone, anlik, sunucuda)
  const yenidenDene = useCallback(() => {
    betikEkle()
    dinleyiciler.forEach(f => f())
  }, [])
  return { durum: gsiDurumu(k), yenidenDene }
}
