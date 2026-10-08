import './AsistanBaslatici.scss'
import { lazy, Suspense, useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Button } from '@carbon/react'
import { Chat } from '@carbon/icons-react'
import { useFocusMode } from '../contexts/focusMode'
import type { UserRole } from '../hooks/useAuth'
import { baslaticiGorunur } from './sayfaBaglami.ts'

// Kabuğun ilk parçasında durur ve Carbon AI Chat'i içe aktarmaz: panel ilk tıklamada tembel yüklenir.
const AsistanPaneli = lazy(() => import('./AsistanPaneli.tsx'))
const GENIS = '(min-width: 42rem)'   // Carbon md, 672 px; altında alt gezinmedeki Asistan sekmesi var

export default function AsistanBaslatici({ rol }: { rol: UserRole }) {
  const { pathname } = useLocation()
  const { focusMode } = useFocusMode()
  const [genis, setGenis] = useState(() => window.matchMedia(GENIS).matches)
  const [acildi, setAcildi] = useState(false)
  useEffect(() => {
    const mq = window.matchMedia(GENIS)
    const f = () => setGenis(mq.matches)
    mq.addEventListener('change', f)
    return () => mq.removeEventListener('change', f)
  }, [])
  if (!baslaticiGorunur(pathname, rol, focusMode, genis)) return null
  // İlk tıklamadan sonra Carbon'un kendi başlatıcısı aynı yerde devralır (ad yine "Sohbet penceresini aç").
  // Adlandırılmış bölge: içerik bir işaret bölgesinde (IBM aria_content_in_landmark) ve düğmenin ipucu
  // sarmalayıcısı sayfa akışına girmez (sabit konum kapta).
  return <aside className={`asistan-baslatici${acildi ? ' asistan-baslatici--acik' : ''}`} aria-label="TEDY Asistan">
    {acildi
      ? <Suspense fallback={null}><AsistanPaneli /></Suspense>
      : <Button kind="primary" size="lg" hasIconOnly renderIcon={Chat} iconDescription="Sohbet penceresini aç"
          tooltipPosition="left" onClick={() => setAcildi(true)} />}
  </aside>
}
