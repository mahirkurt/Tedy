import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

// D17: kâğıt kuralları iki kopyadır — sayfa.css (Paged.js'e ham metin, ana yol A) ve baski.scss (düz yol B, Chrome
// @page'i okur). Paged.js 0.4.3'ün ayrıştırıcısı Carbon'un tam CSS'ini kaldıramadığı için kopya kalır (karar 18); bu test
// iki kopyanın kanun değerlerinde (K5) ayrışmadığını sınar.
const oku = (ad: string) => readFileSync(new URL(`../src/baski/${ad}`, import.meta.url), 'utf8')
  .replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '')

/** Adsız (varsayılan) @page'in `size` ve `margin` değerleri; kenar kutuları ({…}) atlanır. */
function sayfa(css: string): { size: string; margin: string } {
  const bas = css.search(/@page\s*\{/)
  assert.notEqual(bas, -1, 'adsız @page yok')
  let derinlik = 0, govde = ''
  for (let i = css.indexOf('{', bas); i < css.length; i += 1) {
    const c = css[i]
    if (c === '{') derinlik += 1
    else if (c === '}') derinlik -= 1
    else if (derinlik === 1) govde += c
    if (derinlik === 0) break
  }
  const deger = (ad: string) => (govde.match(new RegExp(`(?:^|;|\\s)${ad}\\s*:\\s*([^;]+)`))?.[1] ?? '').trim()
  return { size: deger('size'), margin: deger('margin') }
}

/** Bildirimi `ozellik: deger` olan düz kuralların seçicileri (iç içe @page kuralları atlanır). */
function seciciler(css: string, bildirim: RegExp): string[] {
  const duz = css.replace(/@page[^{]*\{(?:[^{}]|\{[^{}]*\})*\}/g, '')
  const out = new Set<string>()
  for (const m of duz.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    if (bildirim.test(m[2])) m[1].split(',').map(s => s.trim()).filter(Boolean).forEach(s => out.add(s))
  }
  return [...out].sort()
}

const A = oku('sayfa.css')
const B = oku('baski.scss')

test('kâğıt kuralları eşit: @page boyutu ve kenarları (K5: A4 dikey, 18/16/20 mm)', () => {
  assert.deepEqual(sayfa(A), { size: 'A4 portrait', margin: '18mm 16mm 20mm' })
  assert.deepEqual(sayfa(B), sayfa(A))
})

test('kâğıt kuralları eşit: başlıktan sonra kesilmez (break-after: avoid)', () => {
  const a = seciciler(A, /break-after\s*:\s*avoid/)
  assert.ok(a.includes('h3') && a.includes('h5'), 'başlıklar break-after kuralında yok')
  assert.deepEqual(seciciler(B, /break-after\s*:\s*avoid/), a)
})

test('kâğıt kuralları eşit: blok içinde kesilmez (break-inside: avoid)', () => {
  const a = seciciler(A, /break-inside\s*:\s*avoid/)
  assert.ok(a.includes('.kilavuz-matris tr'), 'tablo satırı break-inside kuralında yok')
  assert.deepEqual(seciciler(B, /break-inside\s*:\s*avoid/), a)
})

test('kâğıt kuralları eşit: işaret satırı önceki satırdan ayrılmaz (break-before: avoid)', () => {
  const a = seciciler(A, /break-before\s*:\s*avoid/)
  assert.ok(a.includes('.kilavuz-isaret'))
  assert.deepEqual(seciciler(B, /break-before\s*:\s*avoid/), a)
})

test('kâğıt kuralları eşit: ebeveyn özeti tek sayfa (break-after: page)', () => {
  const a = seciciler(A, /break-after\s*:\s*page/)
  assert.deepEqual(a, ['.kilavuz-ebeveyn'])
  assert.deepEqual(seciciler(B, /break-after\s*:\s*page/), a)
})
