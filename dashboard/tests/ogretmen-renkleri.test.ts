import assert from 'node:assert/strict'
import { test } from 'node:test'
import { ogretmenDegiskenleri } from '../src/asistan/ogretmenRenkleri.ts'

test('Genel modda hiçbir değişken yazılmaz', () => assert.deepEqual(ogretmenDegiskenleri(null), {}))
test('öğretmen modunda düğme ve okurun balonu eski arayüzün rol token’larına bağlanır', () => {
  assert.deepEqual(ogretmenDegiskenleri('blue'), {
    '--cds-button-primary': 'var(--ted-subject-accent)',
    '--cds-button-primary-hover': 'var(--ted-subject-text)',
    '--cds-button-primary-active': 'var(--ted-subject-text)',
    '--cds-interactive': 'var(--ted-subject-accent)',
    '--cds-chat-bubble-user': 'var(--ted-subject-surface)',
    '--cds-chat-bubble-user-text': 'var(--ted-subject-on-surface)',
  })
})
