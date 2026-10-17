import { useSyncExternalStore } from 'react'

// Carbon md kırılımının altı (672 px): telefonda dokunma hedefi en az 44 px (D3b) — denetimler lg (48 px) olur.
const DAR = '(max-width: 671px)'
const abone = (f: () => void) => { const mq = window.matchMedia(DAR); mq.addEventListener('change', f); return () => mq.removeEventListener('change', f) }

/** Telefon genişliği mi: masaüstünde küçük (sm/md), telefonda büyük (lg) Carbon denetimi seçmek için. */
export function useDar(): boolean {
  return useSyncExternalStore(abone, () => window.matchMedia(DAR).matches, () => false)
}

const kokPiksel = () => parseFloat(getComputedStyle(document.documentElement).fontSize) || 16
const yenidenBoyut = (f: () => void) => { window.addEventListener('resize', f); return () => window.removeEventListener('resize', f) }

/** Carbon AI Chat'in geçmiş genişliği (20rem) px olarak. Carbon dar/geniş kararını `--cds-aichat-history-width`'i
 *  Number.parseFloat ile px sanarak verir: "20rem" 20 okunuyor ve telefonda panel yan sütuna düşüp sohbeti ekran
 *  dışına itiyordu (ölçüldü 2026-10-10; calc() de Chrome'da "20rem"e sadeleşiyor). Değer kökün o anki yazı
 *  boyundan hesaplanır, pencere boyu değişince (4K kök ölçeği) yenilenir. */
export function useGecmisGenisligi(): string {
  const px = useSyncExternalStore(yenidenBoyut, () => kokPiksel() * 20, () => 320)
  return `${px}px`
}
