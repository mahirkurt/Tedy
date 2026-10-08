import { Button } from '@carbon/react'
import { ArrowLeft } from '@carbon/icons-react'
import type { ChatInstance } from '@carbon/ai-chat'
import SourcePanel from '../components/SourcePanel'
import { asistanDeposu, useAsistanDurumu } from './asistanDeposu.ts'

/** Workspace panelinin içeriği: bugünkü kaynak paneli, son açılan cevabın atıflarıyla. Dar alanda Carbon paneli
 *  sohbetin üstüne açar ve kendi dönüş düğmesini göstermez: kapatma düğmesi buradadır, odak açan düğmeye döner. */
/** Carbon panel kapanırken sohbeti yeniden gösterir ve bu sırada odak gövdeye düşer (ölçüldü). Odak gövdede
 *  kaldıkça (kullanıcı başka yere geçmediyse) ~1 sn boyunca açan düğmeye geri verilir. */
function odagiGeriVer(el: HTMLElement, kalan = 60) {
  if (!el.isConnected || kalan <= 0) return
  const aktif = document.activeElement
  if ((!aktif || aktif === document.body) && el.checkVisibility()) el.focus()
  requestAnimationFrame(() => odagiGeriVer(el, kalan - 1))
}

export default function KaynakPaneli({ inst }: { inst: () => ChatInstance | null }) {
  const acik = useAsistanDurumu(d => d.acikAtif)
  if (!acik) return null
  const kapat = async () => {
    const donus = acik.donus
    await inst()?.customPanels?.getPanel('workspace' as never).close()
    asistanDeposu.ayarla({ acikAtif: null })
    if (donus) odagiGeriVer(donus)
  }
  return <div className="asistan__kaynaklar">
    <Button kind="ghost" size="sm" renderIcon={ArrowLeft} onClick={() => void kapat()}>Kaynakları kapat</Button>
    <SourcePanel citations={acik.atiflar} activeId={acik.etkin} />
  </div>
}
