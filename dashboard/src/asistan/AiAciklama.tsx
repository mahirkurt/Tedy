import { AILabel, AILabelContent } from '@carbon/react'
import { modelAdi } from '../utils/formatters'
import { useAsistanDurumu } from './asistanDeposu.ts'
import { VOICE } from './ses.ts'

/** Başlıktaki AI etiketi ve açıklama penceresi (eski üst başlıktaki metin). Carbon'un kendi başlık etiketi
 *  axe nested-interactive ihlali verdiği için (Görev 1 raporu) @carbon/react AILabel kullanılır. */
export default function AiAciklama() {
  const okur = useAsistanDurumu(d => d.okur)
  const sonModel = useAsistanDurumu(d => d.sonModel)
  return (
    <AILabel size="xs" autoAlign aiText="AI" slugLabel="bilgisi" aria-label="Yapay zekâ hakkında bilgi" align="bottom-right">
      <AILabelContent>
        <h4 className="ac__ai-pop-title">Bu yanıtları bir yapay zekâ yazıyor</h4>
        <p className="ac__ai-pop-body">{VOICE[okur].sources}</p>
        <p className="ac__ai-pop-body">{VOICE[okur].caution}</p>
        <p className="ac__ai-pop-meta">{sonModel ? `Son yanıtı ${modelAdi(sonModel)} yazdı.` : 'Henüz yanıt yok.'}</p>
      </AILabelContent>
    </AILabel>
  )
}
