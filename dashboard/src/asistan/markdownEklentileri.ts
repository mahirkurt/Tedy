// Bugünkü sohbet renderer'ının (utils/markdown.tsx, bicim: 'sohbet') kutu ve formül kuralları, markdown-it
// eklentisi olarak. Carbon AI Chat eklenti çıktısını light DOM'a koyar; utils/markdown.scss sınıfları uygulanır.
import type MarkdownIt from 'markdown-it'

type BlokKurali = Parameters<MarkdownIt['block']['ruler']['before']>[2]
type SatirKurali = Parameters<MarkdownIt['inline']['ruler']['before']>[2]
type BlokDurumu = Parameters<BlokKurali>[0]
// Paragrafı kesebilsin: ":::kavram" bir paragrafın hemen altında da kutu açar (eski renderer gibi).
const KESER = { alt: ['paragraph', 'reference', 'blockquote', 'list'] }

export interface KatexBenzeri { renderToString(tex: string, o: Record<string, unknown>): string }

const KUTULAR = { kavram: 'Kavram', ornek: 'Örnek', adimlar: 'Adımlar', sonuc: 'Sonuç', hata: 'Sık yapılan hata' } as const
const ACILIS = /^:::\s*([a-zçğıöşü]+)\s*$/
const KAPANIS = /^:::\s*$/
const KATEX_AYARI = { throwOnError: true, output: 'htmlAndMathml', trust: false, strict: 'ignore', maxSize: 10, maxExpand: 100 }

const kac = (s: string) => s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]!))
const satir = (s: BlokDurumu, n: number) => s.src.slice(s.bMarks[n] + s.tShift[n], s.eMarks[n])

function formulHtml(katex: KatexBenzeri | undefined, tex: string, blok: boolean): string {
  let ic = `<code class="ac-formul__kaynak">${kac(tex)}</code>`
  if (katex) { try { ic = katex.renderToString(tex, { ...KATEX_AYARI, displayMode: blok }) } catch { /* yedek kalır */ } }
  return blok ? `<div class="ac-formul ac-formul--blok">${ic}</div>` : `<span class="ac-formul">${ic}</span>`
}

function adimlarHtml(md: MarkdownIt, icerik: string): string {
  const ogeler = icerik.split('\n').map(s => /^\s*(\d+)[.)]\s+(.+)$/.exec(s))
  if (!ogeler.length || ogeler.some(o => !o)) return md.render(icerik)
  const lis = ogeler.map(o => `<li class="ac-adim"><span class="ac-adim__no" aria-hidden="true">${o![1]}</span><div class="ac-adim__govde">${md.renderInline(o![2])}</div></li>`)
  return `<ol class="ac-adimlar" aria-label="Adımlar">${lis.join('')}</ol>`
}

export function tedyMarkdownEklentisi(md: MarkdownIt, katex?: KatexBenzeri): void {
  const kutu: BlokKurali = (s, bas, son, sessiz) => {
    const m = ACILIS.exec(satir(s, bas).trim())
    if (!m) return false
    if (sessiz) return true
    let n = bas + 1
    while (n < son && !KAPANIS.test(satir(s, n).trim())) n += 1
    const t = s.push('tedy_kutu', 'div', 0)
    t.info = m[1]; t.content = s.getLines(bas + 1, n, s.blkIndent, false).replace(/\n$/, ''); t.block = true
    t.map = [bas, Math.min(n + 1, son)]
    s.line = Math.min(n + 1, son)
    return true
  }
  md.block.ruler.before('fence', 'tedy_kutu', kutu, KESER)
  md.renderer.rules.tedy_kutu = (tokens, i) => {
    const ad = tokens[i].info as keyof typeof KUTULAR
    const icerik = tokens[i].content
    if (!(ad in KUTULAR)) return md.render(icerik)
    if (ad === 'adimlar') return `<div class="ac-kutu--adimlar">${adimlarHtml(md, icerik)}</div>`
    return `<div class="ac-kutu ac-kutu--${ad}"><span class="ac-kutu__etiket">${KUTULAR[ad]}</span>${md.render(icerik)}</div>`
  }

  const blokFormul: BlokKurali = (s, bas, son, sessiz) => {
    const ilk = satir(s, bas).trim()
    const tek = /^\$\$(.+)\$\$$/.exec(ilk)
    if (!tek && ilk !== '$$') return false
    if (sessiz) return true
    let n = bas + 1
    let tex = tek?.[1] ?? ''
    if (!tek) {
      while (n < son && satir(s, n).trim() !== '$$') n += 1
      tex = s.getLines(bas + 1, n, s.blkIndent, false).replace(/\n$/, '')
      n += 1
    }
    const t = s.push('tedy_formul', 'div', 0)
    t.content = tex; t.block = true; t.map = [bas, Math.min(n, son)]
    s.line = Math.min(n, son)
    return true
  }
  md.block.ruler.before('fence', 'tedy_blok_formul', blokFormul, KESER)
  const satirFormul: SatirKurali = (s, sessiz) => {
    if (s.src[s.pos] !== '$' || s.src[s.pos + 1] === '$' || /\s/.test(s.src[s.pos + 1] ?? ' ')) return false
    const kapanis = s.src.indexOf('$', s.pos + 1)
    if (kapanis < 0 || /\s/.test(s.src[kapanis - 1])) return false
    if (!sessiz) { const t = s.push('tedy_formul_satir', 'span', 0); t.content = s.src.slice(s.pos + 1, kapanis) }
    s.pos = kapanis + 1
    return true
  }
  md.inline.ruler.before('escape', 'tedy_satir_formul', satirFormul)
  md.renderer.rules.tedy_formul = (tokens, i) => formulHtml(katex, tokens[i].content, true)
  md.renderer.rules.tedy_formul_satir = (tokens, i) => formulHtml(katex, tokens[i].content, false)
}
