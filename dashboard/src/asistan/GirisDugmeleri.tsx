import { IconButton } from '@carbon/react'
import { CalendarHeatMap, Microphone } from '@carbon/icons-react'
import type { ChatInstance } from '@carbon/ai-chat'
import { useAsistanDurumu } from './asistanDeposu.ts'
import { soruyuYeniden } from './istek.ts'

export default function GirisDugmeleri({ inst, mikrofon }: { inst: () => ChatInstance | null; mikrofon: { var: boolean; dinliyor: boolean; bas: () => void } }) {
  const salt = useAsistanDurumu(d => d.saltOkunur)
  const yukleniyor = useAsistanDurumu(d => d.yukleniyor)
  if (salt) return null
  return <>
    {mikrofon.var && <IconButton kind="ghost" size="sm" label={mikrofon.dinliyor ? 'Dinlemeyi bitir' : 'Sesle sor'}
      disabled={yukleniyor} onClick={mikrofon.bas}><Microphone /></IconButton>}
    <IconButton kind="ghost" size="sm" label="Çalışma Planı" disabled={yukleniyor} onClick={() => {
      const i = inst(); const metin = i?.getState().input.rawValue.trim() ?? ''
      if (i && metin) { i.input.updateRawValue(() => ''); void soruyuYeniden(i, metin, { plan: true }) }
    }}><CalendarHeatMap /></IconButton>
  </>
}
