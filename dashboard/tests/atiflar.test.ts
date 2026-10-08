import assert from 'node:assert/strict'
import { test } from 'node:test'
import { atiflariAyikla } from '../src/asistan/atiflar.ts'
import type { AssistantCitation } from '../src/types.ts'

const k = (id: string, label = `Kaynak ${id}`): AssistantCitation =>
  ({ id, kind: 'mufredat', label, locator: {}, snippet: `${label} parçası`, confidence: 1 })

test('işaret metinden çıkar, cümle aralığı kalır', () => {
  const r = atiflariAyikla('Kesir parçadır [S1]. Payda eşit parçadır [S2].', [k('S1'), k('S2')])
  assert.equal(r.metin, 'Kesir parçadır. Payda eşit parçadır.')
  assert.deepEqual(r.kimlikler, ['S1', 'S2'])
  assert.deepEqual(r.atiflar[0].ranges, [{ start: 0, end: 14 }])
  assert.deepEqual(r.atiflar[1].ranges, [{ start: 16, end: 35 }])
  assert.equal(r.atiflar[0].title, 'Kaynak S1')
  assert.equal(r.atiflar[0].text, 'Kaynak S1 parçası')
})

test('aynı kaynak iki kez: tek atıf, iki aralık', () => {
  const r = atiflariAyikla('A cümlesi [S1]. B cümlesi [S1].', [k('S1')])
  assert.equal(r.atiflar.length, 1)
  assert.equal(r.atiflar[0].ranges?.length, 2)
})

test('metin başı, blok, tablo hücresi ve liste: aralık metnin içinde, işaret kalmaz', () => {
  const ham = '[S1] Giriş.\n:::kavram\nPay üstteki sayıdır [S2].\n:::\n| a [S3] | b |\n|---|---|\n- madde [S1]'
  const r = atiflariAyikla(ham, [k('S1'), k('S2'), k('S3')])
  assert.ok(!/\[S\d/.test(r.metin))
  for (const a of r.atiflar) for (const g of a.ranges ?? []) {
    assert.ok(g.start >= 0 && g.end <= r.metin.length && g.start <= g.end)
  }
  assert.ok((r.atiflar[0].ranges ?? []).every(g => g.end > g.start))
  assert.equal(r.metin.slice(r.atiflar[1].ranges![0].start, r.atiflar[1].ranges![0].end), 'Pay üstteki sayıdır')
  assert.equal(r.metin.slice(r.atiflar[2].ranges![0].start, r.atiflar[2].ranges![0].end), '| a')
})

test('boş aralık atılır ama atıf listede kalır', () => {
  const r = atiflariAyikla('[S1] Metin', [k('S1')])
  assert.equal(r.metin, 'Metin')
  assert.deepEqual(r.atiflar[0].ranges, [])
})

test('çözülemeyen işaret metin olarak kalır', () => {
  const r = atiflariAyikla('Bir şey [S9].', [k('S1')])
  assert.equal(r.metin, 'Bir şey [S9].')
  assert.deepEqual(r.atiflar, [])
})
