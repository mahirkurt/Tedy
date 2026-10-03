import { createRequire } from 'node:module'
import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { sabitAc } from './_gorsel-yardim'
import { json } from './_audit-fixtures'

const ACE = createRequire(import.meta.url).resolve('accessibility-checker-engine/ace.js')
const SID = 'ab'.repeat(16)
const QUIZ = {
  id: 'cd'.repeat(16), baslik: 'Payda', ders: 'Matematik', konu: 'Kesir', kazanim_kodu: null,
  zorluk: 'orta', sorular: [
    { tur: 'kisa_cevap', soru: '1/2 + 1/3 kaçtır?' },
    { tur: 'coktan_secmeli', soru: 'Yarıma eşit olanı seç.', secenekler: ['2/4', '1/3', '1/4', '2/3'] },
    { tur: 'dogru_yanlis', soru: 'Paydalar toplanır mı?' },
  ],
}
const SOHBET = { id: SID, baslik: 'Kesir alıştırması', ogretmen: 'matematik',
  olusturma: '2026-10-03T08:00:00Z', guncelleme: '2026-10-03T08:00:00Z' }

async function hazir(page: Page, w = 1440) {
  await sabitAc(page, '/asistan', w, 1000)
  let fallback = 0
  const sorular: Record<string, unknown>[] = []
  await page.route('**/api/assistant/chat', r => { fallback += 1; return r.fulfill(json({ answer: 'Yedek', citations: [] })) })
  await page.route('**/api/assistant/stream', r => {
    sorular.push(r.request().postDataJSON())
    return r.fulfill({ status: 200, contentType: 'text/event-stream', body:
      (sorular.length === 1 ? `event: quiz\ndata: ${JSON.stringify(QUIZ)}\n\n` : '')
      + 'event: answer\ndata: {"payload":{"answer":"Paydaları eşitledim.","citations":[],"meta":{}}}\n\n' })
  })
  await page.fill('#ac-input', 'Kesir alıştırması hazırla')
  await page.getByRole('button', { name: 'Gönder', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Payda', exact: true })).toBeVisible()
  return { sorular, fallback: () => fallback }
}

test('quiz hides solutions, scores each answer and sends only missed questions', async ({ page }) => {
  const durum = await hazir(page)
  const card = page.getByRole('region', { name: 'Payda', exact: true })
  const cevaplar: { sira: number; cevap: string }[] = []
  await page.route(`**/api/assistant/alistirmalar/${QUIZ.id}/cevap`, r => {
    const cevap = r.request().postDataJSON()
    cevaplar.push(cevap)
    return r.fulfill(json({ dogru: cevap.sira !== 3, aciklama: 'Paydalar eşitlenir.',
      ...(cevap.sira === 3 ? { yanlis_analizi: { baslik: 'Paydalar ayrı ayrı toplanmaz' } } : {}) }))
  })
  await expect(card.getByText('Paydalar eşitlenir.')).toHaveCount(0)
  await card.getByLabel('Cevabın', { exact: true }).fill('5/6')
  await card.getByRole('button', { name: 'Cevabı gönder' }).click()
  await expect(card.getByText('Doğru', { exact: true })).toBeVisible()
  await expect(card.getByText('Paydalar eşitlenir.')).toBeVisible()
  await card.getByRole('button', { name: 'Sonraki soru' }).click()
  await card.getByText('2/4', { exact: true }).click()
  await expect(card.getByRole('radio', { name: '2/4', exact: true })).toBeChecked()
  await card.getByRole('button', { name: 'Cevabı gönder' }).click()
  await card.getByRole('button', { name: 'Sonraki soru' }).click()
  await card.getByLabel('Cevabın', { exact: true }).fill('Evet')
  await card.getByRole('button', { name: 'Cevabı gönder' }).click()
  await expect(card.getByText('Puan', { exact: true })).toBeVisible()
  await expect(card.getByText('Puan · 2/3')).toBeVisible()
  await expect(card.getByText('Paydalar ayrı ayrı toplanmaz')).toBeVisible()
  await card.getByRole('button', { name: 'Yanlışlarımı anlat' }).click()
  await expect.poll(() => durum.sorular.length).toBe(2)
  expect(durum.sorular[1]).toMatchObject({ sohbet_id: SID, messages: [{ role: 'user', content: 'Yanlış yaptığım bu soruları açıklar mısın?\nPaydalar toplanır mı?' }] })
  expect(cevaplar).toEqual([{ sira: 1, cevap: '5/6' }, { sira: 2, cevap: '2/4' }, { sira: 3, cevap: 'Evet' }])
  expect(durum.fallback()).toBe(0)
})

test('a family reading the student conversation cannot answer the saved card', async ({ page }) => {
  await sabitAc(page, '/asistan', 1440, 1000)
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/assistant/chat', r => r.fulfill(json({ answer: 'Yedek', citations: [] })))
  await page.route('**/api/assistant/sohbetler?*', r => r.fulfill(json({ sohbetler: [SOHBET] })))
  await page.route(`**/api/assistant/sohbetler/${SID}`, r => r.fulfill(json({
    sohbet: SOHBET, salt_okunur: true,
    mesajlar: [{ id: 'ef'.repeat(16), rol: 'assistant', icerik: 'Alıştırma hazır.', ogretmen: 'matematik',
      atiflar_json: '[]', ekler_json: '[]', alistirma: [QUIZ], zaman: SOHBET.guncelleme }],
  })))
  await page.goto('/asistan')
  await page.getByRole('button', { name: SOHBET.baslik, exact: true }).click()
  const card = page.getByRole('region', { name: 'Payda', exact: true })
  await expect(card.getByText('Bu sohbet salt okunur.')).toBeVisible()
  await expect(card.getByLabel('Cevabın', { exact: true })).toBeDisabled()
  await expect(card.getByRole('button', { name: 'Cevabı gönder' })).toBeDisabled()
})

test('the journal shows week counts, weak topics and rubric levels', async ({ page }) => {
  await sabitAc(page, '/ilerleme', 1440, 1000)
  await page.route('**/api/assistant/ogrenme-gunlugu', r => r.fulfill(json({
    zayif: [{ konu: 'Kesir', kazanim_kodu: null, dogru: 1, toplam: 3 }],
    calisilan: [{ id: 'aa'.repeat(16), kazanim_kodu: null, sayfa_basligi: 'Kesirler sayfa 12', ogretmen: 'matematik' }],
    degerlendirmeler: [{ id: 'ef'.repeat(16), guclu_yanlar: 'Gösterim açık.', duzeyler: 'yeterli', sonraki_adim: 'Yeni bir örnek çöz.' }],
    hafta: { baslangic: '2026-09-28', sohbet: [{ ogretmen: 'matematik', sayi: 2 }], alistirma: 1, puan: { dogru: 1, toplam: 3 } },
  })))
  await page.goto('/ilerleme')
  const gunluk = page.getByRole('region', { name: 'Öğrenme günlüğü' })
  for (const metin of ['Bu hafta', 'Matematik · 2', 'Alıştırma · 1', 'Puan · 1/3', 'Kesir', 'Yeterli', 'Kesirler sayfa 12']) {
    await expect(gunluk.getByText(metin, { exact: true })).toBeVisible()
  }
})

test('the empty journal explains when it fills; a denied journal is hidden', async ({ page }) => {
  await sabitAc(page, '/ilerleme', 1440, 1000)
  await page.route('**/api/assistant/ogrenme-gunlugu', r => r.fulfill(json({ zayif: [], calisilan: [], degerlendirmeler: [],
    hafta: { baslangic: '2026-09-28', sohbet: [], alistirma: 0, puan: { dogru: 0, toplam: 0 } } })))
  await page.goto('/ilerleme')
  const gunluk = page.getByRole('region', { name: 'Öğrenme günlüğü' })
  await expect(gunluk.getByText('Henüz deneme yok. Bir alıştırma bitince burada görünür.')).toBeVisible()
  await expect(gunluk.getByText('Sohbet · 0')).toBeVisible()
  await expect(gunluk.getByText('Alıştırma · 0')).toBeVisible()
  await expect(gunluk.getByText(/Puan/)).toHaveCount(0)
  await page.route('**/api/assistant/ogrenme-gunlugu', r => r.fulfill({ status: 403, body: '{}' }))
  await page.reload()
  await expect(gunluk).toHaveCount(0)
})

test('the exercise card passes axe and IBM checks', async ({ page }) => {
  await hazir(page)
  const { violations } = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice']).analyze()
  expect(violations.map(v => v.id)).toEqual([])
  await page.addScriptTag({ path: ACE })
  const ihlal: string[] = await page.evaluate(async () => {
    // @ts-expect-error ace is injected
    const rapor = await new window.ace.Checker().check(document, ['IBM_Accessibility'])
    return rapor.results.filter((s: { value: string[]; ruleId: string; snippet: string; path: { dom: string } }) =>
      s.value[0] === 'VIOLATION' && s.value[1] === 'FAIL'
      && !(s.ruleId === 'aria_id_unique' && /cds--ai-label|cds--toggletip/.test(s.snippet + ' ' + s.path.dom)))
      .map((s: { ruleId: string }) => s.ruleId)
  })
  expect(ihlal).toEqual([])
})


test('the exercise fits the phone and keeps touch targets usable', async ({ page }) => {
  await hazir(page, 390)
  const card = page.getByRole('region', { name: 'Payda', exact: true })
  await expect(card.getByLabel('Cevabın', { exact: true })).toBeVisible()
  const bounds = await card.getByRole('button', { name: 'Cevabı gönder' }).boundingBox()
  expect(bounds?.height).toBeGreaterThanOrEqual(44)
  await expect(page.locator('body')).toHaveJSProperty('scrollWidth', 390)
  await page.screenshot({ path: 'test-results/alistirma-phone.png', fullPage: true })
})

test('a JSON fallback keeps the quiz card after a failed stream', async ({ page }) => {
  await sabitAc(page, '/asistan', 1440, 1000)
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/assistant/chat', r => r.fulfill(json({
    answer: 'Alıştırma hazır.', citations: [], meta: {}, quiz: QUIZ,
  })))
  await page.fill('#ac-input', 'Alıştırma hazırla')
  await page.getByRole('button', { name: 'Gönder', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Payda', exact: true })).toBeVisible()
})
