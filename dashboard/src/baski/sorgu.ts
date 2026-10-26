// Baskı adresinin çözümü (plan Görev 13): /baski.html?ders=<anahtar>&sinav=1|2[&senaryo=N][&ebeveyn=1][&isaret=0][&duz=1]
import type { PdfSecenekleri } from '../hazirlik/tipler.ts'

export interface BaskiSorgusu {
  ders: string
  sinav: number
  senaryo: number | null
  secenekler: PdfSecenekleri
  duz: boolean
}

const ANAHTAR = /^[a-z]+(?:-[a-z]+)*$/

export function baskiSorgusuCoz(arama: string): BaskiSorgusu | null {
  const p = new URLSearchParams(arama)
  const ders = p.get('ders') ?? ''
  const sinav = p.get('sinav')
  if (!ANAHTAR.test(ders) || (sinav !== '1' && sinav !== '2')) return null
  const s = p.get('senaryo')
  return {
    ders, sinav: Number(sinav), senaryo: s && /^\d{1,2}$/.test(s) ? Number(s) : null,
    secenekler: { ebeveyn: p.get('ebeveyn') === '1', isaret: p.get('isaret') !== '0' }, duz: p.get('duz') === '1',
  }
}
