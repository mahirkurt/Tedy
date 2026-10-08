import { useSyncExternalStore } from 'react'
import type { MarkdownItPlugin } from '@carbon/ai-chat'
import { tedyMarkdownEklentisi, type KatexBenzeri } from './markdownEklentileri.ts'

// KaTeX ayrı parça olarak yüklenir (eski Formul bileşeni gibi): yüklenemezse sayfa yine açılır, formül kaynak
// metniyle görünür. Sohbet, yükleme sonuçlanınca çizilir (useKatexHazir) ki ilk cevaplar da formülle gelsin.
let katex: KatexBenzeri | undefined
let sonuclandi = false
const dinleyiciler = new Set<() => void>()
void Promise.all([import('katex'), import('katex/dist/katex.min.css')])
  .then(([m]) => { katex = m.default }, () => undefined)
  .finally(() => { sonuclandi = true; dinleyiciler.forEach(f => f()) })

const katexVekili: KatexBenzeri = {
  renderToString(tex, ayar) {
    if (!katex) throw new Error('KaTeX yüklenemedi')
    return katex.renderToString(tex, ayar)
  },
}

export function useKatexHazir(): boolean {
  return useSyncExternalStore(f => { dinleyiciler.add(f); return () => { dinleyiciler.delete(f) } }, () => sonuclandi)
}

/** Carbon'a verilen sabit dizi: her render'da aynı başvuru (paket yeniden kurmasın diye). */
export const TEDY_MARKDOWN_EKLENTILERI: MarkdownItPlugin[] = [[tedyMarkdownEklentisi, katexVekili] as unknown as MarkdownItPlugin]
