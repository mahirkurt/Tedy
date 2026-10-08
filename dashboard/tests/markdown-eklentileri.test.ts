import assert from 'node:assert/strict'
import { test } from 'node:test'
import MarkdownIt from 'markdown-it'
import katex from 'katex'
import { tedyMarkdownEklentisi } from '../src/asistan/markdownEklentileri.ts'

const md = () => { const m = new MarkdownIt(); m.use(tedyMarkdownEklentisi, katex); return m }

test('beş kutu etiketiyle, içi markdown', () => {
  const html = md().render(':::kavram\nPay **üstteki** sayıdır.\n:::')
  assert.match(html, /^<div class="ac-kutu ac-kutu--kavram"><span class="ac-kutu__etiket">Kavram<\/span><p>Pay <strong>üstteki<\/strong> sayıdır\.<\/p>\n<\/div>/)
  assert.match(md().render(':::hata\nx\n:::'), /Sık yapılan hata/)
})

test('adımlar kutusu numaralı adım listesi olur', () => {
  const html = md().render(':::adimlar\n1. Paydaları eşitle\n2. Payları topla\n:::')
  assert.match(html, /<ol class="ac-adimlar" aria-label="Adımlar">/)
  assert.match(html, /<li class="ac-adim"><span class="ac-adim__no" aria-hidden="true">2<\/span><div class="ac-adim__govde">Payları topla<\/div><\/li>/)
})

test('bilinmeyen kutu etiketsiz içerik, kapanmayan kutu sona kadar', () => {
  const html = md().render(':::bilinmez\nmetin\n:::')
  assert.ok(!html.includes(':::') && html.includes('<p>metin</p>') && !html.includes('ac-kutu'))
  assert.match(md().render(':::ornek\nyarım'), /ac-kutu--ornek.*yarım/s)
})

test('formüller: satır içi, blok, çok satır, hatalı', () => {
  const r = md().render('Kesir $\\frac{3}{4}$ ve\n\n$$a^2+b^2$$\n\n$$\nx=1\n$$\n\n$\\bozuk{$')
  assert.equal((r.match(/class="katex"/g) ?? []).length, 3)
  assert.match(r, /<div class="ac-formul ac-formul--blok">/)
  assert.match(r, /<code class="ac-formul__kaynak">\\bozuk\{<\/code>/)
})

test('tek dolar ($5 ve $6 gibi para) formül sayılmaz', () => {
  assert.ok(!md().render('Fiyat 5$ ve 6 $ oldu').includes('katex'))
})

test('kutu ve formül içindeki ham HTML yazı olarak kalır (XSS yok), html açık bir örnekte bile', () => {
  const m = new MarkdownIt({ html: true })   // Carbon'un örneği HTML'e açık olsa bile
  m.use(tedyMarkdownEklentisi, katex)
  const html = m.render(':::kavram\n<img src=x onerror="window.__xss=1">\n[tıkla](javascript:alert(1))\n:::\n\n$<b>x</b>$')
  assert.ok(!/<img/i.test(html), html)
  assert.ok(!/href="javascript:/i.test(html), html)
  assert.ok(!/<b>x<\/b>/.test(html), html)
})

test('vurgu kutuları: Şimdi/Öneri eylem, Not/Dikkat not; iki yazım biçimi', () => {
  const r = md().render('**Şimdi:** Matematiğe 10 dakika ayırın.\n\n**Not**: Işık işaretlemiş.')
  assert.match(r, /<div class="ac-md__callout ac-md__callout--eylem"><span class="ac-md__callout-label">Şimdi<\/span><p class="ac-md__p">Matematiğe 10 dakika ayırın\.<\/p><\/div>/)
  assert.match(r, /ac-md__callout--not"><span class="ac-md__callout-label">Not<\/span><p class="ac-md__p">Işık işaretlemiş\.<\/p>/)
})

test('yalnız kalın, kısa satır h4 başlık olur; uzun kalın satır paragraf kalır', () => {
  assert.match(md().render('**Pazartesiye üç ödev**'), /^<h4>Pazartesiye üç ödev<\/h4>/)
  assert.match(md().render('**' + 'a'.repeat(81) + '**'), /^<p><strong>/)
})

test('satır içi formül öğesi Carbon’un kendi çizdiği etiketi taşımaz (yoksa içi boş <span> çizilir)', () => {
  // Carbon yalnız tanımadığı etiketli öğeyi markdown-it çizicisine bırakıp ışık DOM'a taşır (pluginFallback).
  const ogeler = md().parse('Metin $\\frac{1}{2}$ var.\n\n$$x$$', {}).flatMap(t => [t, ...(t.children ?? [])])
  assert.deepEqual(ogeler.filter(t => t.type.startsWith('tedy_formul')).map(t => [t.type, t.tag]),
    [['tedy_formul_satir', ''], ['tedy_formul', 'div']])
})

test('adımlar kutusu alt maddeyi adımın içinde, kapanış paragrafını listenin altında tutar', () => {
  const html = md().render(':::adimlar\n1. Ortak payda\n2. Genişlet\n   - Eşit parçalar\n3. Karşılaştır\n\nBu adımlar karşılaştırır.\n:::')
  assert.equal((html.match(/class="ac-adim"/g) ?? []).length, 3)
  assert.match(html, /<span class="ac-adim__no" aria-hidden="true">2<\/span><div class="ac-adim__govde">Genişlet\n?<ul>\n<li>Eşit parçalar<\/li>/)
  assert.match(html, /<\/ol><p>Bu adımlar karşılaştırır\.<\/p>/)
})

test('ana metindeki ham HTML, HTML’e açık örnekte de yazı kalır (Carbon atıflı cevapta temizleyiciyi kapatıyor)', () => {
  const m = new MarkdownIt({ html: true })
  m.use(tedyMarkdownEklentisi, katex)
  const html = m.render('Metin <img src=x onerror="window.__xss=1"> son.\n\n<div onclick="x()">blok</div>')
  assert.ok(!/<img|<div onclick/.test(html), html)
  assert.match(html, /&lt;img src=x onerror=&quot;window.__xss=1&quot;&gt;/)
})
