import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { createRequire } from 'node:module'
import { mock, FULL, json } from './_audit-fixtures'
import { soruAlani, gonderDugmesi } from './_asistan-carbon'

const EK = 'ab'.repeat(16)
const ONERI = { ek_id: EK, photo_hash: 'cd'.repeat(8), adaylar: [
  { ders: 'Matematik', baslik: 'Sayfa 4', teslim: '', aciklama: '1-5. sorular', eksik: ['teslim'] },
] }
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64')

async function hazirla(page: Page, options: { bos?: boolean; fallback?: boolean; dersYok?: boolean } = {}) {
  await mock(page, FULL)
  await page.route(`**/api/assistant/uploads/${EK}`, r => r.fulfill({ contentType: 'image/png', body: PNG }))
  await page.route('**/api/assistant/uploads', r => r.fulfill(json({ id: EK, ad: 'odev.png', tur: 'gorsel', boyut: PNG.length })))
  const oneri = options.dersYok ? { ...ONERI, adaylar: [{ ...ONERI.adaylar[0], ders: '' }] } : ONERI
  const payload = { answer: options.bos ? 'Bu fotoğrafta ödev görünmüyor.' : 'Ödevleri eklemeden önce kontrol et.',
    citations: [], safety_flags: [], plan_blocks: [], meta: {}, ...(options.bos ? {} : { odev_onerisi: oneri }) }
  await page.route('**/api/assistant/stream', r => options.fallback ? r.abort() : r.fulfill({
    contentType: 'text/event-stream', body: (options.bos ? '' : `event: odev_onerisi\ndata: ${JSON.stringify(oneri)}\n\n`)
      + `event: answer\ndata: ${JSON.stringify({ payload })}\n\n`,
  }))
  await page.route('**/api/assistant/chat', r => r.fulfill(json(payload)))
  await page.goto('/asistan')
  await expect(page.getByRole('button', { name: 'Ödev fotoğrafı ekle' })).toHaveCount(0)
  await page.locator('input[type=file]').first().setInputFiles({ name: 'odev.png', mimeType: 'image/png', buffer: PNG })
  // Carbon AI asistanı: ek çipi giriş üstü yuvada, soru Carbon'un giriş alanında (Görev 16, 19).
  await expect(page.getByText('Görsel', { exact: true })).toBeVisible()
  await soruAlani(page).fill('Bu fotoğraftaki ödevi ekle')
  await gonderDugmesi(page).click()
  await expect(gonderDugmesi(page)).toBeDisabled()
  if (!options.bos) await expect(page.getByRole('region', { name: 'Ödev önerisi' })).toBeVisible()
}

test('photo extraction waits for confirmation and saves the edited fields once', async ({ page }) => {
  const bodies: string[] = []
  await page.route('**/api/homework/photo', r => { bodies.push(r.request().postData() || ''); return r.fulfill(json({ added_count: 1 })) })
  await hazirla(page)
  expect(bodies).toHaveLength(0)
  await expect(page.getByLabel('Teslim', { exact: true })).toHaveValue('')
  await page.getByLabel('Başlık', { exact: true }).fill('Sayfa 5')
  await page.getByLabel('Teslim', { exact: true }).fill('04.10.2026')
  await page.getByRole('button', { name: 'Ödevlere ekle' }).click()
  await expect(page.getByRole('status')).toContainText('1 ödev eklendi')
  expect(bodies).toHaveLength(1)
  expect(bodies[0]).toContain('commit')
  expect(bodies[0]).toContain('Sayfa 5')
  expect(bodies[0]).toContain('04.10.2026')
  expect(bodies[0]).toContain(ONERI.photo_hash)
  await expect(page.getByRole('button', { name: 'Ödevlere ekle' })).toHaveCount(0)
})

test('empty extraction has no confirmation action', async ({ page }) => {
  await hazirla(page, { bos: true })
  await expect(page.getByText('Bu fotoğrafta ödev görünmüyor.', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Ödevlere ekle' })).toHaveCount(0)
})

test('missing course must be filled and a missing date stays explicitly unknown', async ({ page }) => {
  let body = ''
  await page.route('**/api/homework/photo', r => { body = r.request().postData() || ''; return r.fulfill(json({ added_count: 1 })) })
  await hazirla(page, { dersYok: true, fallback: true })
  await expect(page.getByRole('button', { name: 'Ödevlere ekle' })).toBeDisabled()
  await page.getByLabel('Ders', { exact: true }).fill('Fen Bilimleri')
  await page.getByRole('button', { name: 'Ödevlere ekle' }).click()
  await expect(page.getByRole('status')).toContainText('1 ödev eklendi')
  expect(body).toContain('eksik_birakilan')
  expect(body).toContain('teslim')
})

test('a duplicate explains why nothing was added', async ({ page }) => {
  await page.route('**/api/homework/photo', r => r.fulfill(json({ added_count: 0, skipped_count: 1 })))
  await hazirla(page)
  await page.getByRole('button', { name: 'Ödevlere ekle' }).click()
  await expect(page.locator('.ac-odev-onayi').getByText('Bu iş zaten listede. Yeni bir şey eklenmedi.')).toBeVisible()
})

test('a failed upload cannot become a photo proposal', async ({ page }) => {
  await mock(page, FULL)
  await page.route('**/api/assistant/uploads', r => r.fulfill({ status: 415, json: { error: 'Dosya türü desteklenmiyor.' } }))
  await page.goto('/asistan')
  await page.locator('input[type=file]').first().setInputFiles({ name: 'dosya.exe', mimeType: 'application/octet-stream', buffer: Buffer.from('bad') })
  await expect(page.getByRole('alert')).toHaveText('Dosya türü desteklenmiyor.')
  await expect(page.getByRole('button', { name: 'Ödevlere ekle' })).toHaveCount(0)
})

test('an uploaded document binds to the selected homework explicitly', async ({ page }) => {
  const key = 'matematik|kesirler|2026'
  await mock(page, { ...FULL, homework: { homework: [{ 'Ders Adı': 'Matematik', 'Ödev Başlığı': 'Kesirler', homework_key: key }] } })
  await page.route('**/api/assistant/uploads', r => r.fulfill(json({ id: EK, ad: 'not.txt', tur: 'txt' })))
  let bound: unknown
  await page.route('**/api/assistant/uploads/*/odeve-bagla', r => { bound = r.request().postDataJSON(); return r.fulfill(json({ documents: [] })) })
  await page.goto('/asistan')
  await page.locator('input[type=file]').first().setInputFiles({ name: 'not.txt', mimeType: 'text/plain', buffer: Buffer.from('Kesirler') })
  const button = page.getByRole('button', { name: 'Bu ödeve bağla' })
  await expect(button).toBeDisabled()
  await page.getByLabel('Ödev', { exact: true }).selectOption(key)
  await button.click()
  await expect(page.getByRole('button', { name: 'Ödeve bağlandı' })).toBeDisabled()
  expect(bound).toEqual({ anahtar: key })
})


test('photo proposal fits a phone and is accessible', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await hazirla(page)
  await expect(page.getByRole('button', { name: 'Ödevlere ekle' })).toBeEnabled()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
  const { violations } = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze()
  expect(violations.map(v => v.id)).toEqual([])
  await page.addScriptTag({ path: createRequire(import.meta.url).resolve('accessibility-checker-engine/ace.js') })
  const result = await page.evaluate(async () => {
    // @ts-expect-error IBM engine is injected above.
    const report = await new window.ace.Checker().check(document, ['IBM_Accessibility'])
    return report.results as { ruleId: string; value: string[]; snippet: string; path: { dom: string } }[]
  })
  expect(result.filter(r => r.value[0] === 'VIOLATION' && r.value[1] === 'FAIL')
    .filter(r => !(r.ruleId === 'aria_id_unique' && /cds--ai-label|cds--toggletip/.test(r.snippet + r.path.dom)))
    .map(r => r.ruleId)).toEqual([])
  await page.locator('.ac-odev-onayi').screenshot({ path: '/tmp/tedy-photo-proposal.png' })
})
