import './GirisUstu.scss'
import { InlineNotification } from '@carbon/react'
import { asistanDeposu, useAsistanDurumu } from './asistanDeposu.ts'

/** Bir eylem kaydedilemediğinde (ör. geri bildirim) giriş alanının üstünde kısa, kapatılabilir uyarı. */
export default function GirisUyarisi() {
  const uyari = useAsistanDurumu(d => d.uyari)
  if (!uyari) return null
  return <div className="asistan__uyari">
    <InlineNotification kind="error" lowContrast role="alert" title={uyari} statusIconDescription="Hata"
      onClose={() => { asistanDeposu.ayarla({ uyari: null }); return false }} />
  </div>
}
