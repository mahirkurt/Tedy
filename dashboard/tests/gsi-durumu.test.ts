import assert from 'node:assert/strict'
import { test } from 'node:test'
import { gsiDurumu, gsiOlcusu, type GsiKaydi } from '../src/utils/gsiDurumu.ts'

const kayit = (k: Partial<GsiKaydi>): GsiKaydi =>
  ({ betik: 'yukleniyor', apiVar: false, esikGecti: false, gecikti: false, ...k })

// Giriş sayfası yenilemesi (2026-10-15): Google's script used to be awaited on `load` alone, so a blocked script
// left the page with no button and no sentence (D3). Every state of the script is now a state of the page.
test('nothing is drawn in the first 400 ms (S36, B48)', () => {
  assert.equal(gsiDurumu(kayit({})), 'bekliyor')
  assert.equal(gsiDurumu(null), 'bekliyor')
})

test('after the threshold the slot shows a skeleton', () => {
  assert.equal(gsiDurumu(kayit({ esikGecti: true })), 'iskelet')
})

test('a slow script is a warning, not yet a failure (S39)', () => {
  assert.equal(gsiDurumu(kayit({ esikGecti: true, gecikti: true })), 'gecikiyor')
})

test('a script that failed, or loaded without the API (a blocker), cannot be used', () => {
  assert.equal(gsiDurumu(kayit({ betik: 'hata' })), 'yuklenemedi')
  assert.equal(gsiDurumu(kayit({ betik: 'yuklendi', apiVar: false })), 'yuklenemedi')
  assert.equal(gsiDurumu(kayit({ betik: 'hata', gecikti: true, esikGecti: true })), 'yuklenemedi')
})

test('the API wins over every timer: a late script still draws the button', () => {
  assert.equal(gsiDurumu(kayit({ betik: 'yuklendi', apiVar: true, esikGecti: true, gecikti: true })), 'hazir')
})

// Google's button is a px-drawn iframe: 40 px tall ("large"), 200–400 px wide. One zoom factor puts it on
// Carbon's lg control height (48 px) and on the root scale on a 4K screen (S25); the width parameter is the
// column's width divided by that zoom, so the drawn button spans the column.
test('at the 16 px root the button is 48 px tall and as wide as the column', () => {
  const { zoom, genislik } = gsiOlcusu(16, 384)
  assert.equal(zoom, 1.2)
  assert.equal(genislik, 320)
  assert.equal(Math.round(40 * zoom), 48)
})

test('at 4K (32 px root) everything doubles', () => {
  const { zoom, genislik } = gsiOlcusu(32, 768)
  assert.equal(zoom, 2.4)
  assert.equal(genislik, 320)
})

test('Google’s width limits are kept', () => {
  assert.equal(gsiOlcusu(16, 100).genislik, 200)
  assert.equal(gsiOlcusu(16, 2000).genislik, 400)
  assert.equal(gsiOlcusu(Number.NaN, 384).zoom, 1.2)
})
