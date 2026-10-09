import './GirisDugmeleri.scss'
import { IconButton } from '@carbon/react'
import { CalendarHeatMap, Microphone, StopFilledAlt } from '@carbon/icons-react'
import type { ChatInstance } from '@carbon/ai-chat'
import { useAsistanDurumu } from './asistanDeposu.ts'
import { soruyuYeniden, tekrariDurdur } from './istek.ts'

export default function GirisDugmeleri({ inst, mikrofon }: { inst: () => ChatInstance | null; mikrofon: { var: boolean; dinliyor: boolean; bas: () => void } }) {
  const salt = useAsistanDurumu(d => d.saltOkunur)
  const yukleniyor = useAsistanDurumu(d => d.yukleniyor)
  const tekrar = useAsistanDurumu(d => d.tekrarSuruyor)
  if (salt) return null
  // Tek satır: Carbon'un yuvası blok kap; iki düğme ayrı ayrı konunca alt alta düşüyordu.
  return <div className="asistan__giris-dugmeleri">
    {mikrofon.var && <IconButton kind="ghost" size="sm" label={mikrofon.dinliyor ? 'Dinlemeyi bitir' : 'Sesle sor'}
      disabled={yukleniyor} onClick={mikrofon.bas}><Microphone /></IconButton>}
    <IconButton kind="ghost" size="sm" label="Çalışma Planı" disabled={yukleniyor} onClick={() => {
      const i = inst(); const metin = i?.getState().input.rawValue.trim() ?? ''
      if (i && metin) { i.input.updateRawValue(() => ''); void soruyuYeniden(i, metin, { plan: true }) }
    }}><CalendarHeatMap /></IconButton>
    {/* Tekrar dene Carbon'un gönderimi değil; Carbon'un durdur düğmesi çıkmaz, bu onun yerini tutar. */}
    {tekrar && <IconButton kind="ghost" size="sm" label="Yanıtı durdur" onClick={tekrariDurdur}><StopFilledAlt /></IconButton>}
  </div>
}
