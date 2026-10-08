import type { ReactNode } from 'react'
import type { ChatInstance, RenderUserDefinedState } from '@carbon/ai-chat'
import type { OzelKart } from './olayEslemesi.ts'
import TedyKarti from './OzelYanitlar.tsx'

export function ozelYanitCizici(ogretmenSec: (id: string) => Promise<void>) {
  return (state: RenderUserDefinedState, inst: ChatInstance): ReactNode => {
    const kart = (state.messageItem?.user_defined as { tedy?: OzelKart } | undefined)?.tedy
    return kart ? <TedyKarti kart={kart} state={state} inst={inst} ogretmenSec={ogretmenSec} /> : null
  }
}
