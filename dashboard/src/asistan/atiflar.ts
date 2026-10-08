import type { AssistantCitation } from '../types'
import type { ConversationalSearchItemCitation } from '@carbon/ai-chat'

const ISARET = /\s?\[(S\d+)\]/g

/** `[S1]` işaretlerinin kapsadığı cümlenin başı: son satır sonu ya da ". ", "! ", "? " sonrası. */
function cumleBasi(metin: string, bitis: number): number {
  let bas = 0
  for (const m of metin.slice(0, Math.max(0, bitis - 1)).matchAll(/[.!?]\s+|\n/g)) bas = (m.index ?? 0) + m[0].length
  while (bas < bitis && /\s/.test(metin[bas])) bas += 1
  return bas
}

/** Sunucunun okuma sırasıyla numaraladığı işaretleri metinden çıkarır, Carbon'un `ranges` biçimine çevirir.
 *  Çözülemeyen işaret metinde kalır (eski arayüzdeki gibi görünür kalır, yutulmaz). */
export function atiflariAyikla(ham: string, kaynaklar: AssistantCitation[]) {
  const byId = new Map(kaynaklar.map(k => [k.id, k]))
  const araliklar = new Map<string, { start: number; end: number }[]>()
  const kimlikler: string[] = []
  let metin = ''
  let son = 0
  for (const m of ham.matchAll(ISARET)) {
    const bas = m.index ?? 0
    metin += ham.slice(son, bas)
    son = bas + m[0].length
    if (metin === '' && ham[son] === ' ') son += 1   // metnin başındaki işaretin ardındaki boşluk da gider
    const id = m[1]
    if (!byId.has(id)) { metin += m[0]; continue }
    if (!araliklar.has(id)) { araliklar.set(id, []); kimlikler.push(id) }
    const bitis = metin.trimEnd().length
    const start = cumleBasi(metin, bitis)
    if (bitis > start) araliklar.get(id)!.push({ start, end: bitis })
  }
  metin += ham.slice(son)
  const atiflar: ConversationalSearchItemCitation[] = kimlikler.map(id => {
    const k = byId.get(id)!
    return { title: k.label, text: k.snippet, ranges: araliklar.get(id) ?? [] }
  })
  return { metin, atiflar, kimlikler }
}
