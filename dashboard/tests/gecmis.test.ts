/* eslint-disable @typescript-eslint/no-explicit-any -- testler Carbon parçalarının iç içe yapısında serbestçe gezinir */
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { gecmisOgeleri } from '../src/asistan/gecmis.ts'
import type { KayitliMesaj } from '../src/hooks/useSohbetler.ts'

const M = (p: Partial<KayitliMesaj>): KayitliMesaj => ({ id: 'm', rol: 'user', icerik: '', atiflar_json: '[]', ekler_json: '[]', ...p })

test('kullanıcı ve asistan sırası, zaman, geri bildirim durumu', () => {
  const ogeler = gecmisOgeleri([
    M({ id: 'u1', rol: 'user', icerik: 'Kesir nedir?', zaman: '2026-10-08T09:00:00Z' }),
    M({ id: 'a'.repeat(32), rol: 'assistant', icerik: 'Parça [S1].', zaman: '2026-10-08T09:00:05Z',
      atiflar_json: JSON.stringify([{ id: 'S1', kind: 'mufredat', label: 'Mat', locator: {}, snippet: 's', confidence: 1 }]),
      geri_bildirim: { deger: 'olumsuz', kategori: 'Anlamadım', metin: 'hızlı' } }),
  ], { geriBildirim: true, ogrenci: true })
  assert.equal(ogeler.length, 2)
  assert.deepEqual((ogeler[0].message as Record<string, any>).input, { text: 'Kesir nedir?' })
  assert.equal(ogeler[0].time, '2026-10-08T09:00:00Z')
  const yanit = ogeler[1].message as Record<string, any>
  assert.equal(yanit.output.generic[0].response_type, 'conversational_search')
  assert.deepEqual(yanit.history.feedback['a'.repeat(32)], { is_positive: false, text: 'hızlı', categories: ['Anlamadım'] })
})

test('salt okunur sohbette geri bildirim kapalı; kayıtlı kartlar geri gelir', () => {
  const [o] = gecmisOgeleri([M({ id: 'b'.repeat(32), rol: 'assistant', icerik: 'x',
    netlestirme: { soru: 'Hangisi?', secenekler: ['a', 'b'] } })], { geriBildirim: false, ogrenci: false })
  const g = (o.message as Record<string, any>).output.generic
  assert.equal(g[0].message_item_options.feedback, undefined)
  assert.equal(g[1].user_defined.tedy.tur, 'netlestirme')
})
