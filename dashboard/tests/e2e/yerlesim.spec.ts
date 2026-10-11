import { test, expect } from '@playwright/test'
import { sabitAc } from './_gorsel-yardim'

// Talimatname §13, 4th round (2026-10-11): layout and depth rules measured in the browser.

for (const [ad, w, h] of [['masaüstü', 1440, 900], ['telefon', 390, 844]] as const) {
  // B37 (P3): Bugün's quiet homework line and the Carbon lists under it start on one left line.
  test(`Bugün: the quiet line and the lists share one keyline (${ad})`, async ({ page }) => {
    await sabitAc(page, '/', w, h)
    const sessiz = page.locator('.next-thing--quiet .next-thing__eyebrow')
    const liste = page.locator('.today .cds--contained-list__label').first()
    await expect(sessiz).toBeVisible()
    await expect(liste).toBeVisible()
    const a = (await sessiz.boundingBox())!.x
    const b = (await liste.boundingBox())!.x
    expect(Math.abs(a - b)).toBeLessThanOrEqual(1)
  })
}

// B2 (S11): a card is a layer and a hairline, not a shadow; B37: Carbon's tile padding at every width.
test('a dashboard card has a border, no shadow and 16px padding', async ({ page }) => {
  await sabitAc(page, '/isler', 1440, 900)
  const kart = await page.locator('.dashboard-card').first().evaluate(el => {
    const cs = getComputedStyle(el)
    return { golge: cs.boxShadow, kenar: cs.borderTopWidth, dolgu: cs.paddingTop }
  })
  expect(kart.golge).toBe('none')
  expect(kart.kenar).toBe('1px')
  expect(kart.dolgu).toBe('16px')
})

// B31 ([3.1-2]): a block set inside a card sits one layer up — Carbon's <Layer>, not a hand-paired colour.
test('İşler: the next-thing block is one Carbon layer above its card', async ({ page }) => {
  await sabitAc(page, '/isler', 1440, 900)
  const katman = page.locator('.dashboard-card .cds--layer-two')
  await expect(katman).toHaveCount(1)
  await expect(katman.locator('.next-thing')).toHaveCount(1)
  const zemin = await katman.evaluate(el => getComputedStyle(el).getPropertyValue('--cds-layer').trim())
  expect(zemin).toBe('#f4f4f4')   // layer-02 in g10; the card is layer-01 (#ffffff)
})

// B37: no private breakpoint narrows the band at 320px; its actions keep the phone's 44px floor (S18).
test('the header holds at 320px without shrinking its actions', async ({ page }) => {
  await sabitAc(page, '/', 320, 700)
  const yatay = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(yatay).toBeLessThanOrEqual(0)
  for (const ad of ['Yenile', 'Çıkış yap']) {
    const kutu = (await page.getByRole('button', { name: ad }).boundingBox())!
    expect(kutu.width).toBeGreaterThanOrEqual(44)
    expect(kutu.height).toBeGreaterThanOrEqual(44)
    expect(kutu.x + kutu.width).toBeLessThanOrEqual(320)
  }
})
