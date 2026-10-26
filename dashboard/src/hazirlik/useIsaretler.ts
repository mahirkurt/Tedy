import { useCallback, useMemo, useState } from 'react'
import { tumBloklar } from './belge'
import type { IsaretDurumu, KilavuzModeli } from './tipler'

/** Kaydedilemeyen işaretin hatası: hangi çıktıda (bildirim o bloğun yanında çizilir) ve ne söylenecek. */
export interface IsaretHatasi { kod: string; metin: string }

/** Hazırlık işaretleri (spec §2.3, §7): iyimser güncelleme; PUT düşerse işaret eski hâline döner ve hata söylenir.
 *  Render sırasında depolama okunmaz (D24): sunucunun işaretleri modelden, yereldeki değişiklik durumda. */
export function useIsaretler(anahtar: string, model: KilavuzModeli | null) {
  const [yerel, setYerel] = useState<Record<string, IsaretDurumu>>({})
  const [hata, setHata] = useState<IsaretHatasi | null>(null)
  const sunucu = useMemo(() => Object.fromEntries(tumBloklar(model).map(b => [b.kod, b.isaret])), [model])
  const isaretler = useMemo(() => ({ ...sunucu, ...yerel }), [sunucu, yerel])
  const isaretle = useCallback(async (kod: string, durum: IsaretDurumu, onceki: IsaretDurumu) => {
    setYerel(y => ({ ...y, [kod]: durum }))
    setHata(null)
    try {
      const r = await fetch('/api/hazirlik/isaret', {
        method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ders: anahtar, kod, durum }),
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
    } catch {
      setYerel(y => ({ ...y, [kod]: onceki }))
      setHata({ kod, metin: 'İşaret kaydedilemedi; geri alındı.' })
    }
  }, [anahtar])
  const hatayiKapat = useCallback(() => setHata(null), [])
  return { isaretler, isaretle, hata, hatayiKapat }
}
