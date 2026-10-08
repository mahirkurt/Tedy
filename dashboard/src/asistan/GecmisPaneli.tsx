import type { ChatInstance } from '@carbon/ai-chat'
import SohbetListesi from '../components/SohbetListesi'
import type { useSohbetler } from '../hooks/useSohbetler'
import { asistanDeposu, useAsistanDurumu } from './asistanDeposu.ts'
import { sohbetiAc, yeniSohbet, etkinSohbetiYaz } from './useAsistanOturumu.ts'

export default function GecmisPaneli({ depo, ogrenci, inst, ogretmenSec }: {
  depo: ReturnType<typeof useSohbetler>; ogrenci: boolean; inst: () => ChatInstance | null; ogretmenSec: (id: string) => void
}) {
  const yukleniyor = useAsistanDurumu(d => d.yukleniyor)
  return <SohbetListesi gomulu depo={depo} student={ogrenci} disabled={yukleniyor || depo.bekliyor}
    onAc={(id, salt) => { const i = inst(); if (i) void sohbetiAc(i, depo, ogretmenSec, id, salt) }}
    onYeni={() => { const i = inst(); if (i) void yeniSohbet(i, depo).catch(() => depo.setHata('Sohbet kaydedilemedi.')) }}
    onSil={id => void depo.sil(id).then(async () => {
      if (depo.secili?.id === id) {
        etkinSohbetiYaz(asistanDeposu.al().email, null)
        asistanDeposu.ayarla({ sohbetId: undefined, dokum: [], mesajVar: false })
        const i = inst(); if (i) await i.messaging.clearConversation()
      }
    }).catch(() => depo.setHata('Sohbet kaydedilemedi.'))} />
}
