import { AILabel, AILabelContent } from '@carbon/react'
import { modelAdi } from '../utils/formatters'
import { useAsistanDurumu } from './asistanDeposu.ts'
import { VOICE } from './ses.ts'
import { useDar } from './useDar.ts'

const DENETIM: Record<string, string> = {
  gecti: 'Yanıtı ikinci bir model kaynak ve seviye açısından okudu; sorun bulmadı.',
  duzeltildi: 'Yanıtı ikinci bir model kaynak ve seviye açısından okudu ve düzeltti.',
}

/** Açıklama penceresinin içeriği (Carbon'un dört bölümlü şablonu, §6.2): genel bakış, son yanıtın ayrıntıları
 *  (model insan adıyla, öğretmen, ikinci okuma, yedek model), kaynaklar ve yanılabilirlik. */
export function AiAciklamaIcerigi({ ogretmenAdi }: { ogretmenAdi: string | null }) {
  const okur = useAsistanDurumu(d => d.okur)
  const sonModel = useAsistanDurumu(d => d.sonModel)
  const denetim = useAsistanDurumu(d => d.sonDenetim)
  const yedek = useAsistanDurumu(d => d.sonYedek)
  const ad = modelAdi(sonModel)
  return <div className="asistan-ai">
    <h2 className="asistan-ai__baslik">Bu yanıtları bir yapay zekâ yazıyor</h2>
    <p className="asistan-ai__govde">{VOICE[okur].caution}</p>
    <ul className="asistan-ai__ayrintilar">
      <li>{ad ? `Son yanıtı ${ad} yazdı.` : sonModel ? 'Son yanıtı bir yapay zekâ modeli yazdı.' : 'Henüz yanıt yok.'}</li>
      {yedek && <li>Asıl model yanıt veremediği için evdeki yedek model yazdı; bu yanıt kaynaksızdır.</li>}
      <li>{ogretmenAdi ? `${ogretmenAdi} modunda: konuyu ders öğretmeni gibi adım adım anlatır.` : 'Genel asistan modunda.'}</li>
      {denetim && DENETIM[denetim] && <li>{DENETIM[denetim]}</li>}
    </ul>
    <p className="asistan-ai__govde">{VOICE[okur].sources}</p>
  </div>
}

/** Başlıktaki AI etiketi. Carbon AI Chat'in kendi başlık etiketi axe nested-interactive ihlali verdiği için
 *  (2026-10-10 yeniden ölçüldü) @carbon/react AILabel; ad B53'e göre: `slugLabel=""` (boş dize — yazılmazsa eskimiş
 *  varsayılan "Show information" adı ezer) + Türkçe aria-label → "AI Yapay zekâ hakkında bilgi". Salt okunur
 *  sohbette de etkin kalır (Carbon: "never disabled"). */
export default function AiAciklama({ ogretmenAdi }: { ogretmenAdi: string | null }) {
  // Telefonda dokunma hedefi ≥ 44 px (D3b, B79): lg (48 px); masaüstünde başlığın xs etiketi.
  const dar = useDar()
  return (
    <AILabel size={dar ? 'lg' : 'xs'} autoAlign aiText="AI" slugLabel="" aria-label="Yapay zekâ hakkında bilgi" align="bottom-right">
      <AILabelContent>
        <AiAciklamaIcerigi ogretmenAdi={ogretmenAdi} />
      </AILabelContent>
    </AILabel>
  )
}
