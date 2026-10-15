/**
 * Google Identity Services on the sign-in page, as page states (giriş sayfası yenilemesi, 2026-10-15; spec
 * docs/superpowers/specs/2026-10-15-giris-sayfasi-yenileme-design.md §3.4–3.5). Pure, so `node --test` reads it.
 */

/** What the <script> tag itself reported. */
export type BetikDurumu = 'yukleniyor' | 'yuklendi' | 'hata'

export interface GsiKaydi {
  betik: BetikDurumu
  /** `window.google.accounts.id` existed when the script finished. A blocker can let the request "load" empty. */
  apiVar: boolean
  /** YUKLEME_ESIGI_MS (400 ms) has passed: a skeleton may be drawn (S36, B48). */
  esikGecti: boolean
  /** GSI_GECIKME_MS has passed without an answer. */
  gecikti: boolean
}

/** What the page draws in the button's slot. */
export type GsiGorunum = 'bekliyor' | 'iskelet' | 'gecikiyor' | 'hazir' | 'yuklenemedi'

/** After this long without Google's script the page says so (a warning — it may still arrive). */
export const GSI_GECIKME_MS = 10_000

export function gsiDurumu(k: GsiKaydi | null): GsiGorunum {
  if (!k) return 'bekliyor'
  if (k.apiVar) return 'hazir'
  if (k.betik !== 'yukleniyor') return 'yuklenemedi'
  if (k.gecikti) return 'gecikiyor'
  return k.esikGecti ? 'iskelet' : 'bekliyor'
}

/** Google's "large" button is 40 px; ×1.2 puts it on Carbon's lg control height, 48 px ([3.4-8], S18). */
const LG_CARPANI = 1.2
const GSI_EN_AZ = 200
const GSI_EN_COK = 400

/**
 * Google's button is an iframe drawn in px, so neither the 4K root scale (S25) nor the column reaches it.
 * `zoom` = root scale × 1.2; `genislik` (the `width` parameter) = the column ÷ zoom, inside Google's 200–400 px.
 */
export function gsiOlcusu(kokPx: number, sutunPx: number): { zoom: number; genislik: number } {
  const olcek = Number.isFinite(kokPx) && kokPx > 0 ? kokPx / 16 : 1
  const zoom = Math.round(olcek * LG_CARPANI * 1000) / 1000
  const genislik = Math.min(GSI_EN_COK, Math.max(GSI_EN_AZ, Math.floor(sutunPx / zoom)))
  return { zoom, genislik }
}
