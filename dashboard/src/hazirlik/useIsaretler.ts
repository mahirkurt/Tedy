import { useCallback, useMemo, useRef, useState } from 'react'
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
  // Kod başına istek sıra numarası (düzeltme 3): geç dönen eski bir isteğin hatası ve geri alması, aynı çıktıdaki daha
  // yeni bir isteğin sonucunu ezmez; yalnız o çıktının son isteği geri alır ve hata söyler.
  const sira = useRef(new Map<string, number>())
  const isaretle = useCallback(async (kod: string, durum: IsaretDurumu, onceki: IsaretDurumu) => {
    const no = (sira.current.get(kod) ?? 0) + 1
    sira.current.set(kod, no)
    setYerel(y => ({ ...y, [kod]: durum }))
    setHata(null)
    try {
      const r = await fetch('/api/hazirlik/isaret', {
        method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ders: anahtar, kod, durum }),
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
    } catch {
      if (sira.current.get(kod) !== no) return
      setYerel(y => ({ ...y, [kod]: onceki }))
      setHata({ kod, metin: 'İşaret kaydedilemedi; geri alındı.' })
    }
  }, [anahtar])
  const hatayiKapat = useCallback(() => setHata(null), [])
  return { isaretler, isaretle, hata, hatayiKapat }
}
