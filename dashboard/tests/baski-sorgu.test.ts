import { test } from 'node:test'
import assert from 'node:assert/strict'
import { baskiSorgusuCoz } from '../src/baski/sorgu.ts'

test('baskı adresi çözülür; seçenekler varsayılanla', () => {
  assert.deepEqual(baskiSorgusuCoz('?ders=fen-bilimleri&sinav=1'),
    { ders: 'fen-bilimleri', sinav: 1, senaryo: null, secenekler: { ebeveyn: false, isaret: true }, duz: false })
  assert.deepEqual(baskiSorgusuCoz('?ders=fen-bilimleri&sinav=2&senaryo=3&ebeveyn=1&isaret=0&duz=1'),
    { ders: 'fen-bilimleri', sinav: 2, senaryo: 3, secenekler: { ebeveyn: true, isaret: false }, duz: true })
  assert.equal(baskiSorgusuCoz('?ders=fen-bilimleri&sinav=3'), null)
  assert.equal(baskiSorgusuCoz('?ders=../x&sinav=1'), null)
  assert.equal(baskiSorgusuCoz('?yoklama=1'), null)
  assert.equal(baskiSorgusuCoz('?ders=fen-bilimleri&sinav=1&senaryo=abc')?.senaryo, null)
})
