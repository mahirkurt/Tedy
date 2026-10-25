import { test } from 'node:test'
import assert from 'node:assert/strict'
import { KOK, argumanlariCoz, baskiAdresi, guvenliYol, mimeTuru } from '../scripts/kilavuzPdfOrtak.mjs'

test('argümanlar: zorunlu alanlar, varsayılan süre, bilinmeyen argüman', () => {
  assert.deepEqual(
    argumanlariCoz(['--dist', '/d', '--cikti', '/t/k.pdf', '--model', '/t/m.json', '--sorgu', 'ders=fen-bilimleri&sinav=1']),
    { dist: '/d', model: '/t/m.json', cikti: '/t/k.pdf', sorgu: 'ders=fen-bilimleri&sinav=1', duz: false, sure: 45000 })
  const a = argumanlariCoz(['--dist', '/d', '--cikti', '/k.pdf', '--duz', '--sure', '5000'])
  assert.equal(a.duz, true)
  assert.equal(a.sure, 5000)
  assert.equal(a.model, null)
  assert.throws(() => argumanlariCoz(['--dist', '/d']), /--cikti/)
  assert.throws(() => argumanlariCoz(['--dist', '/d', '--cikti', '/k.pdf', '--sure', '10']), /en az 1000/)
  assert.throws(() => argumanlariCoz(['--dist', '/d', '--cikti', '/k.pdf', '--bilinmeyen', 'x']), /bilinmeyen/)
  assert.throws(() => argumanlariCoz(['--dist', '/d', '--cikti']), /değer yok/)
})

test('güvenli yol: dist içinde kalır, dışarı çıkamaz', () => {
  assert.equal(guvenliYol('/d', '/baski.html'), '/d/baski.html')
  assert.equal(guvenliYol('/d', '/assets/a%20b.js'), '/d/assets/a b.js')
  assert.equal(guvenliYol('/d', '/../etc/passwd'), null)
  assert.equal(guvenliYol('/d', '/%2e%2e/etc/passwd'), null)
  assert.equal(guvenliYol('/d', '/a%00b'), null)
  assert.equal(guvenliYol('/d', '/%E0%A4%A'), null)
})

test('mime türü ve baskı adresi', () => {
  assert.equal(mimeTuru('/d/fonts/plex/IBMPlexSans-Regular.woff2'), 'font/woff2')
  assert.equal(mimeTuru('/d/assets/A.JS'), 'text/javascript; charset=utf-8')
  assert.equal(mimeTuru('/d/x.bilinmez'), 'application/octet-stream')
  assert.equal(baskiAdresi('ders=fen-bilimleri&sinav=1', false), `${KOK}/baski.html?ders=fen-bilimleri&sinav=1`)
  assert.equal(baskiAdresi('yoklama=1', true), `${KOK}/baski.html?yoklama=1&duz=1`)
})
