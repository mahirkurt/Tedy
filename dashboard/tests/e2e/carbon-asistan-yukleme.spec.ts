import { test, expect } from '@playwright/test'
import type { Page, Route } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { createRequire } from 'node:module'
import { json } from './_audit-fixtures'
import { carbonSabitAc as sabitAc, soruAlani } from './_asistan-carbon'

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

const ID = 'ab'.repeat(16)
const CEVAP = {
  answer: 'Baktım.', citations: [], safety_flags: [], plan_blocks: [], intent: 'qa',
  session_id: '', mode_suggestion: null, meta: { model: 'claude-sonnet-5', degraded: [], ogretmen: 'genel' },
}
const ACE = createRequire(import.meta.url).resolve('accessibility-checker-engine/ace.js')

async function hazir(page: Page, w = 1440, h = 900) {
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/assistant/chat', r => r.fulfill(json(CEVAP)))
  await page.route('**/api/assistant/plan', r => r.fulfill(json(CEVAP)))
  await sabitAc(page, '/asistan', w, h)
}

async function yukleme(route: Route, durum = 200, govde: Record<string, unknown> = {
  id: ID, ad: 'not.png', tur: 'gorsel', boyut: 8,
}) {
  await route.fulfill({ status: durum, contentType: 'application/json', body: JSON.stringify(govde) })
}

test('chip shows the server name and type, and remove drops it', async ({ page }) => {
  await hazir(page)
  await page.route('**/api/assistant/uploads', r => yukleme(r))
  await page.locator('.ac__dosya-girdi').setInputFiles({ name: 'not.png', mimeType: 'image/png', buffer: Buffer.from('x') })
  await expect(page.getByText('not.png', { exact: true })).toBeVisible()
  await expect(page.getByText('Görsel', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Kaldır: not.png' }).click()
  await expect(page.getByText('not.png', { exact: true })).toHaveCount(0)
})

test('a 415 sentence sits on the chip', async ({ page }) => {
  await hazir(page)
  await page.route('**/api/assistant/uploads', r => yukleme(r, 415, { error: 'Bu dosya biçimi okunamadı.' }))
  await page.locator('.ac__dosya-girdi').setInputFiles({ name: 'a.heic', mimeType: 'image/heic', buffer: Buffer.from('x') })
  await expect(page.getByRole('alert')).toHaveText('Bu dosya biçimi okunamadı.')
})

test('the fifth file is not posted', async ({ page }) => {
  await hazir(page)
  let n = 0
  await page.route('**/api/assistant/uploads', r => { n += 1; return yukleme(r, 200, { id: (n + 'c').padEnd(32, 'a').slice(0, 32), ad: `n${n}.txt`, tur: 'txt', boyut: 1 }) })
  const input = page.locator('.ac__dosya-girdi')
  for (let i = 0; i < 4; i += 1) {
    await input.setInputFiles({ name: `n${i}.txt`, mimeType: 'text/plain', buffer: Buffer.from('a') })
    await expect(page.getByText(`n${i + 1}.txt`)).toBeVisible()
  }
  await input.setInputFiles({ name: 'bes.txt', mimeType: 'text/plain', buffer: Buffer.from('b') })
  await expect(page.getByText('Bir mesaja en fazla 4 dosya eklenebilir.', { exact: true })).toBeVisible()
  expect(n).toBe(4)
})

// hazir() aborts /stream. This test only checks the /chat fallback and the plan
// button. It does not prove the composer posts ekler to /stream.
test('chat sends ekler and the plan button does not', async ({ page }) => {
  await hazir(page)
  await page.route('**/api/assistant/uploads', r => yukleme(r))
  await page.locator('.ac__dosya-girdi').setInputFiles({ name: 'not.png', mimeType: 'image/png', buffer: Buffer.from('x') })
  await expect(page.getByText('Görsel', { exact: true })).toBeVisible()
  await soruAlani(page).fill('bak')
  const sohbet = page.waitForRequest('**/api/assistant/chat')
  await page.getByRole('button', { name: 'Gönder' }).click()
  const govde = (await sohbet).postDataJSON() as { ogretmen: string; messages: { role: string; ekler?: string[] }[] }
  const son = govde.messages[govde.messages.length - 1]
  expect(govde.ogretmen).toBe('genel')
  expect(son).toMatchObject({ role: 'user', ekler: [ID] })
  await expect(page.locator('.ac-yuklenen-ek')).toContainText('not.png')
  await expect(page.locator('.ac-yuklenen-ek img')).toHaveCount(1)

  await page.locator('.ac__dosya-girdi').setInputFiles({ name: 'not.png', mimeType: 'image/png', buffer: Buffer.from('x') })
  await soruAlani(page).fill('plan')
  const plan = page.waitForRequest('**/api/assistant/plan')
  await page.getByRole('button', { name: 'Çalışma Planı', exact: true }).click()
  const planGovde = (await plan).postDataJSON() as { messages: { ekler?: string[] }[] }
  expect(planGovde.messages.every(m => m.ekler === undefined)).toBe(true)
})

test('the composer posts ekler to /stream and does not fall back', async ({ page }) => {
  let sohbet = 0
  await page.route('**/api/assistant/chat', () => { sohbet += 1 })
  await page.route('**/api/assistant/plan', r => r.fulfill(json(CEVAP)))
  await page.route('**/api/assistant/uploads', r => yukleme(r))
  await page.route('**/api/assistant/stream', async r => {
    const govde = r.request().postDataJSON() as { messages: { ekler?: string[] }[] }
    const son = govde.messages[govde.messages.length - 1]
    expect(son.ekler).toEqual([ID])
    await r.fulfill({
      status: 200, contentType: 'text/event-stream',
      body: `event: answer\ndata: ${JSON.stringify({ payload: CEVAP })}\n\nevent: done\ndata: {}\n\n`,
    })
  })
  await sabitAc(page, '/asistan', 1440, 900)
  await page.locator('.ac__dosya-girdi').setInputFiles({ name: 'not.png', mimeType: 'image/png', buffer: Buffer.from('x') })
  await expect(page.getByText('Görsel', { exact: true })).toBeVisible()
  await soruAlani(page).fill('bak')
  await page.getByRole('button', { name: 'Gönder' }).click()
  await expect(page.getByText('Baktım.', { exact: true })).toBeVisible()
  expect(sohbet).toBe(0)
})

test('drop and paste add a chip; a text paste does not', async ({ page }) => {
  await hazir(page)
  await page.route('**/api/assistant/uploads', r => yukleme(r))
  await page.locator('.asistan').evaluate(el => {
    const file = new File([new Uint8Array([1])], 'not.png', { type: 'image/png' })
    const dt = new DataTransfer()
    dt.items.add(file)
    el.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true }))
  })
  await expect(page.getByText('not.png', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Kaldır: not.png' }).click()
  await soruAlani(page).fill('kalem')
  await expect(soruAlani(page)).toHaveValue('kalem')
  await soruAlani(page).evaluate(el => {
    const file = new File([new Uint8Array([1])], 'not.png', { type: 'image/png' })
    const dt = new DataTransfer()
    dt.items.add(file)
    // Tarayıcının gerçek yapıştırma olayı composed'dır (gölge kökten çıkar); yapay olay da öyle olmalı.
    el.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true, composed: true }))
  })
  await expect(page.getByText('not.png', { exact: true })).toBeVisible()
  await expect(soruAlani(page)).toHaveValue('kalem')
})

test('desktop has no camera input', async ({ page }) => {
  await hazir(page)
  await expect(page.locator('.ac__dosya-girdi--kamera')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Dosya ekle' })).toBeVisible()
})

test('the source panel previews an uploaded image', async ({ page }) => {
  await hazir(page)
  await page.route('**/api/assistant/chat', r => r.fulfill(json({
    ...CEVAP,
    citations: [{ id: 'S1', kind: 'yuklenen-dosya', label: 'not.png',
      locator: { upload_id: ID, tur: 'gorsel' }, snippet: 'Görsel', confidence: 0.9 }],
  })))
  await page.route(`**/api/assistant/uploads/${ID}`, r => r.fulfill({
    // The plan's base64 has a bad IHDR CRC (FcSJ was written FCSj), so Chromium
    // refuses to decode it and the preview's onError replaces the image.
    status: 200, contentType: 'image/png', body: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64'),
  }))
  await soruAlani(page).fill('bak')
  await page.getByRole('button', { name: 'Gönder' }).click()
  // Kaynak paneli Carbon'da workspace'te; cevabın altbilgisinden açılır.
  await page.getByRole('button', { name: 'Kaynak ayrıntıları' }).click()
  await expect(page.getByRole('heading', { name: 'Yüklediğin dosya' })).toBeVisible()
  await expect(page.getByRole('img', { name: 'not.png' })).toBeVisible()
})

test('chips stay within axe and IBM', async ({ page }) => {
  await hazir(page)
  await page.route('**/api/assistant/uploads', r => yukleme(r))
  await page.locator('.ac__dosya-girdi').setInputFiles({ name: 'not.png', mimeType: 'image/png', buffer: Buffer.from('x') })
  await expect(page.getByText('Görsel', { exact: true })).toBeVisible()
  const { violations } = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'])
    .analyze()
  expect(violations.map(v => v.id)).toEqual([])
  await page.addScriptTag({ path: ACE })
  const ihlal: string[] = await page.evaluate(async () => {
    // @ts-expect-error ace is injected
    const rapor = await new window.ace.Checker().check(document, ['IBM_Accessibility'])
    return rapor.results
      .filter((s: { value: string[]; ruleId: string; snippet: string; path: { dom: string } }) =>
        s.value[0] === 'VIOLATION' && s.value[1] === 'FAIL'
        && !(s.ruleId === 'aria_id_unique' && /cds--ai-label|cds--toggletip/.test(s.snippet + ' ' + s.path.dom)))
      .map((s: { ruleId: string }) => s.ruleId)
  })
  expect(ihlal).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0)
})

test.describe('phone camera', () => {
  test.use({ hasTouch: true, viewport: { width: 390, height: 844 } })
  test('capture is environment and accept is images', async ({ page }) => {
    await hazir(page, 390, 844)
    const kamera = page.locator('.ac__dosya-girdi--kamera')
    await expect(kamera).toHaveAttribute('capture', 'environment')
    await expect(kamera).toHaveAttribute('accept', 'image/*')
    await expect(page.getByRole('button', { name: 'Fotoğraf çek' })).toBeVisible()
  })
})
