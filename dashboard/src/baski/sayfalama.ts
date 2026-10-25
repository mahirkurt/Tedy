import { Previewer } from './vendor/pagedjs-0.4.3/paged.esm.js'
import sayfaKurallari from './sayfa.css?raw'

/** React'in çizdiği kaynağı Paged.js ile A4 sayfalara döker ve sayfa sayısını döner. Kaynak DOM'dan kaldırılır:
 *  Paged.js içeriği kendi sayfa kutularına kopyalar; kâğıtta olay dinleyicisi gerekmez (K11). Paged.js'e yalnız
 *  sayfa.css verilir (Carbon'un tam CSS'i ayrıştırıcısını düşürür); belgedeki stil sayfaları yerinde kalır. */
export async function sayfala(kaynak: HTMLElement): Promise<number> {
  const sablon = document.createElement('template')
  sablon.innerHTML = kaynak.innerHTML
  kaynak.remove()
  const akis = await new Previewer().preview(sablon.content, [{ [`${location.origin}/sayfa.css`]: sayfaKurallari }], document.body)
  return akis.total
}
