import assert from 'node:assert/strict'
import { test } from 'node:test'
import { geriBildirimGonder } from '../src/asistan/geriBildirim.ts'
import { asistanDeposu } from '../src/asistan/asistanDeposu.ts'

const olay = { interactionType: 'submitted', isPositive: false, categories: ['Anlamadım'], text: 'x',
  messageItem: { message_item_options: { feedback: { id: 'a'.repeat(32) } } } } as never

test('kaydedilemeyen geri bildirim okura söylenir (sessiz hata yok): sunucu hatası ve ağ hatası', async () => {
  for (const f of [async () => ({ ok: false, status: 500 }), async () => { throw new TypeError('ağ yok') }]) {
    asistanDeposu.ayarla({ uyari: null })
    await geriBildirimGonder(olay, f as unknown as typeof fetch)
    assert.equal(asistanDeposu.al().uyari, 'Geri bildirim kaydedilemedi.')
  }
  asistanDeposu.ayarla({ uyari: null })
  await geriBildirimGonder(olay, (async () => ({ ok: true, status: 200 })) as unknown as typeof fetch)
  assert.equal(asistanDeposu.al().uyari, null)
})
