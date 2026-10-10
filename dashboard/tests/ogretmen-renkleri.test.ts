import assert from 'node:assert/strict'
import { test } from 'node:test'
import { ogretmenDegiskenleri } from '../src/asistan/ogretmenRenkleri.ts'

test('Genel modda hiçbir değişken yazılmaz', () => assert.deepEqual(ogretmenDegiskenleri(null), {}))
test('öğretmen modunda yalnız okurun balonu ders yüzeyine bağlanır', () => {
  assert.deepEqual(ogretmenDegiskenleri('blue'), {
    '--cds-chat-bubble-user': 'var(--ted-subject-surface)',
    '--cds-chat-bubble-user-text': 'var(--ted-subject-on-surface)',
  })
})
test('eylem rengi hiçbir kipte boyanmaz (S35, B68): düğme ve etkileşim token’ı yazılmaz', () => {
  for (const aile of ['blue', 'purple', 'teal', 'magenta', 'cyan'] as const) {
    const d = ogretmenDegiskenleri(aile)
    for (const k of Object.keys(d)) assert.ok(!/--cds-(button|interactive)/.test(k), `${aile}: ${k}`)
  }
})
