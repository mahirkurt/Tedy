import { DismissibleTag } from '@carbon/react'
import { useApi } from '../hooks/useApi'
import type { HomeworkItem } from '../types'
import { asistanDeposu, useAsistanDurumu } from './asistanDeposu.ts'
import { odevAdi } from './odevler.ts'
import { sabitOgeyiBirak } from './sayfaBaglami.ts'

/** "Bu sayfa: İşler — Matematik — Test 1" ve "Ödev: Matematik — Kesirler": sonraki soru bu bağlamla gider;
 *  kapatılırsa bağlamsız. Ödev çipi giriş satırındaki "Ödeve bağla" eyleminin seçimidir (istekte `odev_anahtari`). */
export default function BaglamCipi() {
  const sayfa = useAsistanDurumu(d => d.sayfa)
  const odevKey = useAsistanDurumu(d => d.odevKey)
  const { data } = useApi<{ homework: HomeworkItem[] }>('/api/homework', { homework: [] })
  const odev = odevKey ? (data.homework || []).find(hw => hw.homework_key === odevKey) : undefined
  if (!sayfa && !odevKey) return null
  const metin = sayfa ? `Bu sayfa: ${sayfa.etiket}${sayfa.ogeEtiketi ? ` — ${sayfa.ogeEtiketi}` : ''}` : ''
  // title kısaltılmamış etikette, dismissTooltipLabel kısaltılmışta kapatma düğmesinin adıdır (@carbon/react).
  const kaldir = sayfa ? `Bağlamı kaldır: ${sayfa.etiket}` : ''
  const odevMetni = `Ödev: ${odev ? odevAdi(odev) : 'seçili ödev'}`
  return <div className="asistan__baglam">
    {sayfa && <DismissibleTag type="gray" size="md" text={metin} title={kaldir} dismissTooltipLabel={kaldir}
      onClose={() => { sabitOgeyiBirak(); asistanDeposu.ayarla({ sayfa: null }) }} />}
    {odevKey && <DismissibleTag type="gray" size="md" text={odevMetni} title="Ödevi kaldır" dismissTooltipLabel="Ödevi kaldır"
      onClose={() => asistanDeposu.ayarla({ odevKey: '' })} />}
  </div>
}
