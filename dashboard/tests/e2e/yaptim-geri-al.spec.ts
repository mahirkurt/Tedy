import { test, expect, type Page, type Route } from '@playwright/test'
import { bugunAc, HOMEWORK, MATEMATIK } from './_bugun-fixtures'

// B63 (talimatname S40, İ5): "Yaptım" is low impact, so it is done without a
// confirmation and taken back on the same line — "Geri al". Both places that
// record "Yaptım" (Bugün's box, İşler's rows) send the undo through
// utils/odevYaptim.ts, the same record the mark was sent with.

const json = (b: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(b) })

type Kayit = { yol: string; govde: Record<string, unknown> }

/** /api/homework that remembers the mark and its undo, like the real endpoints. */
async function odevSunucusu(page: Page, geriAlCevabi = 200) {
  const gelen: Kayit[] = []
  let yapildi = false
  await page.route('**/api/homework', (r: Route) => r.fulfill(json({
    ...HOMEWORK,
    homework: HOMEWORK.homework.map(h =>
      yapildi && h === MATEMATIK ? { ...h, student_marked_done: true, homework_key: 'mat-key' }
        : h === MATEMATIK ? { ...h, homework_key: 'mat-key' } : h),
  })))
  await page.route('**/api/homework/mark-done', async (r: Route) => {
    gelen.push({ yol: 'mark-done', govde: JSON.parse(r.request().postData() || '{}') })
    yapildi = true
    await r.fulfill(json({ ok: true }))
  })
  await page.route('**/api/homework/unmark-done', async (r: Route) => {
    gelen.push({ yol: 'unmark-done', govde: JSON.parse(r.request().postData() || '{}') })
    if (geriAlCevabi === 200) yapildi = false
    await r.fulfill({ status: geriAlCevabi, contentType: 'application/json',
      body: JSON.stringify(geriAlCevabi === 200 ? { ok: true, removed: true } : { error: 'x' }) })
  })
  return gelen
}

test.describe('Bugün', () => {
  async function yaptimDe(page: Page) {
    const kart = page.locator('.next-thing')
    await kart.getByRole('button', { name: 'Başla' }).click()
    await kart.getByRole('button', { name: 'Yaptım' }).click()
    await expect(page.locator('.today-done-note')).toContainText('Yaptın: Matematik')
    await expect(kart).toContainText('Fransızca')
  }

  test('Yaptın satırındaki Geri al işareti kaldırır ve iş karta geri döner', async ({ page }) => {
    const gelen = await odevSunucusu(page)
    await bugunAc(page, '2026-09-24T16:40', { homework: null })
    await yaptimDe(page)

    const satir = page.locator('.today-done-note')
    await satir.getByRole('button', { name: 'Geri al', exact: true }).click()

    // The same record "Yaptım" sent, to the endpoint that takes it back.
    await expect.poll(() => gelen.map(k => k.yol)).toEqual(['mark-done', 'unmark-done'])
    expect(gelen[1].govde).toEqual(gelen[0].govde)
    expect(gelen[1].govde.homework_key).toBe('mat-key')

    // The line goes; the work is the card's again.
    await expect(satir).toHaveCount(0)
    await expect(page.locator('.next-thing')).toContainText('Matematik')
  })

  test('geri alınamazsa söyler, satır kalır', async ({ page }) => {
    await odevSunucusu(page, 500)
    await bugunAc(page, '2026-09-24T16:40', { homework: null })
    await yaptimDe(page)

    const satir = page.locator('.today-done-note')
    await satir.getByRole('button', { name: 'Geri al', exact: true }).click()
    await expect(satir.getByRole('alert')).toHaveText('Geri alınamadı. Bağlantını kontrol edip yeniden dene.')
    await expect(satir).toContainText('Yaptın: Matematik')
    await expect(satir.getByRole('button', { name: 'Geri al', exact: true })).toBeVisible()
  })

  test('Geri al telefonda en az 44px', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await odevSunucusu(page)
    await bugunAc(page, '2026-09-24T16:40', { homework: null })
    await yaptimDe(page)
    const kutu = await page.locator('.today-done-note').getByRole('button', { name: 'Geri al' }).boundingBox()
    expect(kutu!.height).toBeGreaterThanOrEqual(44)
    expect(kutu!.width).toBeGreaterThanOrEqual(44)
  })
})

test.describe('İşler', () => {
  async function islerAc(page: Page) {
    await page.route('**/api/enrichment', r => r.fulfill(json({})))
    await page.route('**/api/exams', r => r.fulfill(json({ exams: [] })))
    await page.route('**/api/modules', r => r.fulfill(json({ moduller: [] })))
    await page.route('**/api/health', r => r.fulfill(json({
      timestamp: '', success: true, scrape_errors: [], duration_seconds: 1 })))
    await page.clock.setFixedTime(new Date('2026-09-24T16:40:00'))
    await page.goto('/isler')
    await expect(page.locator('.isler .next-thing')).toBeVisible()
  }

  test('satırdaki Yaptım sonrası Geri al aynı kaydı gönderir', async ({ page }) => {
    const gelen = await odevSunucusu(page)
    await islerAc(page)

    // The nearest (Matematik) is the next thing, named once; the rows are the rest (yenileme 2026-10-15).
    const satir = page.locator('.homework-item').filter({ hasText: 'S1 Les verbes' })
    await satir.getByRole('button', { name: 'Yaptım' }).click()

    const not = page.locator('.isler-yaptin')
    await expect(not).toContainText('Yaptın: Fransızca — S1 Les verbes')
    await not.getByRole('button', { name: 'Geri al', exact: true }).click()

    await expect.poll(() => gelen.map(k => k.yol)).toEqual(['mark-done', 'unmark-done'])
    expect(gelen[1].govde).toEqual(gelen[0].govde)
    await expect(not).toHaveCount(0)
    // Back among the active work, with its "Yaptım" again.
    await expect(page.locator('.homework-item').filter({ hasText: 'S1 Les verbes' })
      .getByRole('button', { name: 'Yaptım' })).toBeVisible()
  })

  test('Yapılan grubundaki kendi işaretini her zaman geri alabilir', async ({ page }) => {
    const gelen = await odevSunucusu(page)
    await page.route('**/api/homework', (r: Route) => r.fulfill(json({
      ...HOMEWORK,
      homework: HOMEWORK.homework.map(h =>
        h === MATEMATIK ? { ...h, student_marked_done: true, homework_key: 'mat-key' } : h),
    })))
    await islerAc(page)

    await page.getByRole('button', { name: /^Yapılan/ }).click()
    const geriAl = page.getByRole('button', { name: 'Geri al: 2. HAFTA MATEMATİK HAFTA İÇİ ÖDEVİ', exact: true })
    await expect(geriAl).toBeVisible()
    await geriAl.click()
    await expect.poll(() => gelen.map(k => k.yol)).toEqual(['unmark-done'])
    expect(gelen[0].govde.homework_key).toBe('mat-key')
  })
})
