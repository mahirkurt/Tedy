import assert from 'node:assert/strict'
import { test } from 'node:test'
import { onar } from '../src/asistan/carbonOnarimi.ts'

test('iç düğme hiç çıkmazsa onarım birkaç denemeden sonra bırakır (sonsuz mikro görev döngüsü sekmeyi dondururdu)', async () => {
  let deneme = 0
  const etiket = {
    shadowRoot: { querySelector: () => null },
    // Bitmiş bir Lit öğesi çözülmüş söz döndürür; 50'den sonra test kendini korumak için askıda bırakır.
    get updateComplete() { deneme += 1; return deneme < 50 ? Promise.resolve() : new Promise(() => {}) },
    getAttribute: () => 'false', removeAttribute: () => {},
  }
  const kok = { querySelectorAll: (s: string) => (s.includes('aria-expanded') ? [etiket] : []) }
  onar(kok as unknown as ParentNode)
  await new Promise(r => setTimeout(r, 20))
  assert.ok(deneme <= 4, `deneme: ${deneme}`)
})
