import './GirisUstu.scss'
import { DismissibleTag } from '@carbon/react'
import { asistanDeposu, useAsistanDurumu } from './asistanDeposu.ts'

/** "Bu sayfa: İşler — Matematik — Test 1": sonraki soru bu bağlamla gider; kapatılırsa bağlamsız. */
export default function BaglamCipi() {
  const sayfa = useAsistanDurumu(d => d.sayfa)
  if (!sayfa) return null
  const metin = `Bu sayfa: ${sayfa.etiket}${sayfa.ogeEtiketi ? ` — ${sayfa.ogeEtiketi}` : ''}`
  // title kısaltılmamış etikette, dismissTooltipLabel kısaltılmışta kapatma düğmesinin adıdır (@carbon/react).
  const kaldir = `Bağlamı kaldır: ${sayfa.etiket}`
  return <div className="asistan__baglam">
    <DismissibleTag type="gray" size="sm" text={metin} title={kaldir} dismissTooltipLabel={kaldir}
      onClose={() => asistanDeposu.ayarla({ sayfa: null })} />
  </div>
}
