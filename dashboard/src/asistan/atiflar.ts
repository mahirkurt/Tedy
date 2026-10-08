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

/** Kod bloklarının (``` … ```) ve satır içi kod aralıklarının (`…`) konumları: içlerindeki `[S1]` koddur, atıf değil. */
function kodAraliklari(ham: string): [number, number][] {
  const araliklar: [number, number][] = []
  for (const m of ham.matchAll(/^```[^\n]*\n[\s\S]*?(?:^```[^\n]*$|(?![\s\S]))|`[^`\n]+`/gm)) {
    araliklar.push([m.index ?? 0, (m.index ?? 0) + m[0].length])
  }
  return araliklar
}

/** Sunucunun okuma sırasıyla numaraladığı işaretleri metinden çıkarır, Carbon'un `ranges` biçimine çevirir.
 *  Çözülemeyen işaret metinde kalır (eski arayüzdeki gibi görünür kalır, yutulmaz). */
export function atiflariAyikla(ham: string, kaynaklar: AssistantCitation[]) {
  const byId = new Map(kaynaklar.map(k => [k.id, k]))
  const araliklar = new Map<string, { start: number; end: number }[]>()
  const kimlikler: string[] = []
  let metin = ''
  let son = 0
  const kod = kodAraliklari(ham)
  for (const m of ham.matchAll(ISARET)) {
    const bas = m.index ?? 0
    if (kod.some(([a, b]) => bas + m[0].length > a && bas < b)) continue   // kodun içinde: metin olduğu gibi kalır
    metin += ham.slice(son, bas)
    son = bas + m[0].length
    if (metin === '' && ham[son] === ' ') son += 1   // metnin başındaki işaretin ardındaki boşluk da gider
    const id = m[1]
    if (!byId.has(id)) { metin += m[0]; continue }
    if (!araliklar.has(id)) { araliklar.set(id, []); kimlikler.push(id) }
    const bitis = metin.trimEnd().length
    let start = cumleBasi(metin, bitis)
    // Carbon aralığı markdown kaynağına "==…==" ekleyerek vurgular: satırın blok imi (liste, başlık, alıntı)
    // aralığa girerse blok bozulur; tablo satırında sütun sayısı bozulacağından aralık hiç verilmez.
    const satirBasi = metin.lastIndexOf('\n', bitis - 1) + 1
    const satir = metin.slice(satirBasi, bitis)
    if (/^\s*\|/.test(satir)) continue
    const im = /^(?:\s*(?:[-*+]|\d+[.)]|>|#{1,6})\s+)+/.exec(satir)
    if (im && start < satirBasi + im[0].length) start = satirBasi + im[0].length
    if (bitis > start) araliklar.get(id)!.push({ start, end: bitis })
  }
  metin += ham.slice(son)
  const atiflar: ConversationalSearchItemCitation[] = kimlikler.map(id => {
    const k = byId.get(id)!
    return { title: k.label, text: k.snippet, ranges: araliklar.get(id) ?? [] }
  })
  return { metin, atiflar, kimlikler }
}
