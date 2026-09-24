import { useState } from 'react'

/** The ten minutes behind "10 dakikayla başla".
 *
 *  The card had always offered a time box and then, on "Başla", navigated to
 *  a list — so the box was a sentence, not a thing, and the work had to be
 *  found again on another page. This keeps the box on the card, and keeps it
 *  across a reload or a wander away and back (İ5): the start time lives in
 *  localStorage keyed by the work it belongs to, so a different top item
 *  simply finds no box.
 */

const ANAHTAR = 'tedy-zaman-kutusu'
/** How long "10 dakika doldu" stays offered before the card goes back to
 *  its resting state; the next day must not open on yesterday's box. */
const DOLDU_GECERLI_MS = 60 * 60_000

interface Kayit { is: string; basla: number; dakika: number }

function oku(): Kayit | null {
  try {
    const k = JSON.parse(localStorage.getItem(ANAHTAR) || 'null')
    return k && typeof k.is === 'string' && typeof k.basla === 'number' ? k : null
  } catch {
    return null
  }
}

function yaz(k: Kayit | null) {
  try {
    if (k) localStorage.setItem(ANAHTAR, JSON.stringify(k))
    else localStorage.removeItem(ANAHTAR)
  } catch { /* storage full or blocked: the box just will not survive a reload */ }
}

export type KutuDurumu =
  | { durum: 'bos' }
  | { durum: 'suruyor'; kalanDk: number }
  | { durum: 'doldu' }

export function useZamanKutusu(is: string, dakika: number, nowMs: number) {
  const [kayit, setKayit] = useState<Kayit | null>(oku)

  const baslat = () => {
    const k = { is, basla: Date.now(), dakika }
    yaz(k)
    setKayit(k)
  }
  const birak = () => {
    yaz(null)
    setKayit(null)
  }

  let durum: KutuDurumu = { durum: 'bos' }
  if (kayit && kayit.is === is) {
    const bitis = kayit.basla + kayit.dakika * 60_000
    // The page clock ticks once a minute, so right after "Başla" it can lag
    // the start by up to a minute; never show more than the box holds.
    const simdi = Math.max(nowMs, kayit.basla)
    if (simdi < bitis) {
      durum = { durum: 'suruyor', kalanDk: Math.min(kayit.dakika, Math.ceil((bitis - simdi) / 60_000)) }
    } else if (simdi < bitis + DOLDU_GECERLI_MS) {
      durum = { durum: 'doldu' }
    }
  }

  return { ...durum, baslat, birak }
}
