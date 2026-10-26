// PDF seçeneklerinin deposu (plan Görev 14, D26): bu cihazda kişi başına (localStorage `tedy-hazirlik-pdf::<e-posta>`).
// Render sırasında localStorage elle okunmaz (D24): React'in dış depo kancası anlık değeri okur, pencere ve A4 önizleme
// aynı değeri görür; kayıt (bu sekmede olay, öbür sekmelerde `storage`) bütün okuyucuları yeniler.
import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react'
import { secenekAnahtari, secenekleriOku, secenekleriYaz } from './hazirlik'
import type { PdfSecenekleri } from './tipler'

const OLAY = 'tedy:hazirlik-pdf-secenekleri'

function abone(bildir: () => void): () => void {
  window.addEventListener(OLAY, bildir)
  window.addEventListener('storage', bildir)
  return () => {
    window.removeEventListener(OLAY, bildir)
    window.removeEventListener('storage', bildir)
  }
}

function hamKayit(email: string): string {
  try { return localStorage.getItem(secenekAnahtari(email)) ?? '' } catch { return '' }
}

/** Kişinin bu cihazdaki son PDF seçimi (yoksa ya da bozuksa varsayılan). */
export function usePdfSecenekleri(email: string): PdfSecenekleri {
  const ham = useSyncExternalStore(abone, () => hamKayit(email), () => '')
  return useMemo(() => secenekleriOku(email, { getItem: () => ham || null }), [email, ham])
}

export function pdfSecenekleriniKaydet(email: string, s: PdfSecenekleri): void {
  secenekleriYaz(email, s, localStorage)
  window.dispatchEvent(new Event(OLAY))
}

/** Pencerenin açık/kapalı durumu ve açan düğme: pencere yalnız açıkken bağlanır; kapanınca (pencere ağaçtan kalktıktan
 *  sonra — Carbon'un odak tuzağı açıkken odak dışarı kaçmaz) odak açan düğmeye döner. */
export function usePdfPenceresi() {
  const [acik, setAcik] = useState(false)
  const dugme = useRef<HTMLButtonElement>(null)
  const odakDonsun = useRef(false)
  useEffect(() => {
    if (!acik && odakDonsun.current) {
      odakDonsun.current = false
      dugme.current?.focus()
    }
  }, [acik])
  const ac = useCallback(() => setAcik(true), [])
  const kapat = useCallback(() => { odakDonsun.current = true; setAcik(false) }, [])
  return { acik, ac, kapat, dugme }
}
