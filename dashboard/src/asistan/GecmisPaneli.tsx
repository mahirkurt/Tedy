import type { ChatInstance } from '@carbon/ai-chat'
import type { useSohbetler } from '../hooks/useSohbetler'
import { asistanDeposu, useAsistanDurumu } from './asistanDeposu.ts'
import { sohbetiAc, yeniSohbet, etkinSohbetiYaz, gecmisiAc } from './useAsistanOturumu.ts'
import SohbetGecmisi from './SohbetGecmisi.tsx'

/** Telefonda geçmiş paneli sohbeti örter: bir sohbet açılınca ya da yenisi başlayınca kapanır. */
function dardaKapat(i: ChatInstance) {
  if (i.getState().customPanels.history.isMobile) void gecmisiAc(i, false)
}

export default function GecmisPaneli({ depo, ogrenci, inst, ogretmenSec }: {
  depo: ReturnType<typeof useSohbetler>; ogrenci: boolean; inst: () => ChatInstance | null; ogretmenSec: (id: string) => void
}) {
  const yukleniyor = useAsistanDurumu(d => d.yukleniyor)
  return <SohbetGecmisi depo={depo} ogrenci={ogrenci} kilitli={yukleniyor || depo.bekliyor}
    // Kapatma iş bittikten sonra da yinelenir: Carbon konuşmayı boşaltıp geçmişi eklerken panel durumunu yeniden
    // kurabiliyor (telefonda ölçüldü, ara sıra açık kalıyordu).
    onAc={(id, salt) => { const i = inst(); if (i) { dardaKapat(i); void sohbetiAc(i, depo, ogretmenSec, id, salt).finally(() => dardaKapat(i)) } }}
    onYeni={() => { const i = inst(); if (i) { dardaKapat(i); void yeniSohbet(i, depo).catch(() => depo.setHata('Yeni sohbet açılamadı.')).finally(() => dardaKapat(i)) } }}
    onKapat={() => { const i = inst(); if (i) void gecmisiAc(i, false) }}
    onSil={istek => asistanDeposu.ayarla({ silinecek: istek })}
    onSilSohbet={async id => {
      await depo.sil(id)
      if (asistanDeposu.al().sohbetId === id) {
        etkinSohbetiYaz(asistanDeposu.al().email, null)
        asistanDeposu.ayarla({ sohbetId: undefined, dokum: [], mesajVar: false })
        const i = inst(); if (i) await i.messaging.clearConversation()
      }
    }} />
}
