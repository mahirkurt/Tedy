import type { ChatInstance, GenericItem, MessageResponse } from '@carbon/ai-chat'
import type { AltbilgiVerisi } from './olayEslemesi.ts'
import MesajAltbilgisi from './MesajAltbilgisi.tsx'

export function altbilgiCizici() {
  return (_slot: string, mesaj: MessageResponse, _oge: GenericItem, inst: ChatInstance, ek?: Record<string, unknown>) =>
    ek ? <MesajAltbilgisi veri={ek as unknown as AltbilgiVerisi} mesaj={mesaj} inst={inst} /> : null
}
