import assert from 'node:assert/strict'
import { test } from 'node:test'
import { DOKUNMA_KURALI, HAREKET_KURALI, IKON_KURALI, dokunmaHedefiniUygula, onar } from '../src/asistan/carbonOnarimi.ts'

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

test('dokunma kuralı (B79): Carbon düğmelerinin yoğunluk değişkeni yalnız telefonda 3rem', () => {
  assert.match(DOKUNMA_KURALI, /@media \(max-width: 671px\)/)
  assert.match(DOKUNMA_KURALI, /cds-button, cds-icon-button \{ --cds-layout-size-height-min: 3rem; \}/)
})

test('dokunma kuralı her gölge köke bir kez eklenir; iç içe kökler de taranır', () => {
  const kural = { ad: 'kural' } as unknown as CSSStyleSheet
  const ic = { adoptedStyleSheets: [] as CSSStyleSheet[], querySelectorAll: () => [] }
  const dis = { adoptedStyleSheets: [] as CSSStyleSheet[], querySelectorAll: () => [{ shadowRoot: ic }] }
  const gorulen = new WeakSet<ShadowRoot>()
  const ilk = dokunmaHedefiniUygula(dis as unknown as ShadowRoot, gorulen, kural)
  assert.equal(ilk.length, 2)
  assert.deepEqual(dis.adoptedStyleSheets, [kural])
  assert.deepEqual(ic.adoptedStyleSheets, [kural])
  const ikinci = dokunmaHedefiniUygula(dis as unknown as ShadowRoot, gorulen, kural)
  assert.equal(ikinci.length, 0)
  assert.equal(ic.adoptedStyleSheets.length, 1)
})

test('4K ikon kuralı (B28): gölge kökte de ted-theme.scss ile aynı, sıfır özgüllükle rem', () => {
  assert.match(IKON_KURALI, /:where\(svg\[width='16'\]\[height='16'\]\) \{ width: 1rem; height: 1rem; \}/)
  assert.match(IKON_KURALI, /:where\(svg\[width='32'\]\[height='32'\]\) \{ width: 2rem; height: 2rem; \}/)
  assert.equal(IKON_KURALI.split('\n').length, 9)
})

test('azaltılmış hareket kuralı gölge kökte her animasyonu ve geçişi kapatır', () => {
  assert.match(HAREKET_KURALI, /@media \(prefers-reduced-motion: reduce\)/)
  assert.match(HAREKET_KURALI, /animation-duration: 0s !important; animation-iteration-count: 1 !important; transition-duration: 0s !important;/)
})
