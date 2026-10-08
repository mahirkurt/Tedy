import katex from 'katex'
import 'katex/dist/katex.min.css'
import type { MarkdownItPlugin } from '@carbon/ai-chat'
import { tedyMarkdownEklentisi } from './markdownEklentileri.ts'

/** Carbon'a verilen sabit dizi: her render'da aynı başvuru (paket yeniden kurmasın diye). */
export const TEDY_MARKDOWN_EKLENTILERI: MarkdownItPlugin[] = [[tedyMarkdownEklentisi, katex] as unknown as MarkdownItPlugin]
