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
  // Carbon aralığı markdown kaynağına "==…==" ekleyerek vurgular: blok imleri aralığa girmez, yoksa liste,
  // başlık ve tablo bozulur. Tablo satırında aralık verilmez (sütun sayısı bozulurdu); atıf listede kalır.
  assert.deepEqual(r.atiflar[2].ranges, [])
  const madde = (r.atiflar[0].ranges ?? []).slice(-1)[0]
  assert.equal(r.metin.slice(madde.start, madde.end), 'madde')
})

test('başlık, alıntı ve numaralı madde imi aralığa girmez', () => {
  const r = atiflariAyikla('### Başlık [S1]\n\n> alıntı [S2]\n\n12. adım [S3]', [k('S1'), k('S2'), k('S3')])
  const parca = (i: number) => { const g = (r.atiflar[i].ranges ?? [])[0]; return r.metin.slice(g.start, g.end) }
  assert.deepEqual([parca(0), parca(1), parca(2)], ['Başlık', 'alıntı', 'adım'])
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

test('kod aralığı ve kod bloğundaki işaret yazı olarak kalır, atıf sayılmaz', () => {
  const { metin, kimlikler } = atiflariAyikla('Kod `örnek [S1]` aralığı [S2].\n\n```\nx = [S1]\n```', [k('S1'), k('S2')])
  assert.equal(metin, 'Kod `örnek [S1]` aralığı.\n\n```\nx = [S1]\n```')
  assert.deepEqual(kimlikler, ['S2'])
})
