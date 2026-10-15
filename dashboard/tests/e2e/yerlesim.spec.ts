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
  // On Notlar: İşler has no card since its redesign (2026-10-15).
  await sabitAc(page, '/notlar', 1440, 900)
  const kart = await page.locator('.dashboard-card').first().evaluate(el => {
    const cs = getComputedStyle(el)
    return { golge: cs.boxShadow, kenar: cs.borderTopWidth, dolgu: cs.paddingTop }
  })
  expect(kart.golge).toBe('none')
  expect(kart.kenar).toBe('1px')
  expect(kart.dolgu).toBe('16px')
})

// B31 ([3.1-3]) answered by removal (İşler yenilemesi 2026-10-15, S52): the next thing and the lists stand on
// the page, so no block sits inside a card — nothing on İşler is a card in a card.
test('İşler: no card in a card — the panel and the lists stand on the page', async ({ page }) => {
  await sabitAc(page, '/isler', 1440, 900)
  await expect(page.locator('.isler > .next-thing')).toHaveCount(1)
  await expect(page.locator('.isler .dashboard-card, .isler .cds--tile, .isler .cds--layer-two')).toHaveCount(0)
  await expect(page.locator('.isler > .isler-bolum, .isler > .isler-liste')).not.toHaveCount(0)
})

// B11 (WCAG 2.4.1, 2.4.11): the first Tab stop skips to the content; a focused element is never under the
// fixed band (or, on a phone, the bottom bar).
test('the first Tab stop skips past the band and the navigation', async ({ page }) => {
  await sabitAc(page, '/isler', 1440, 900)
  await page.keyboard.press('Tab')
  const atla = page.getByRole('link', { name: 'İçeriğe atla' })
  await expect(atla).toBeFocused()
  await expect(atla).toBeVisible()
  await page.keyboard.press('Enter')
  await expect(page.locator('#main-content')).toBeFocused()
})

for (const [ad, w, h] of [['masaüstü', 1440, 600], ['telefon', 390, 640]] as const) {
  test(`a focused control is never hidden under the band or the bottom bar (${ad})`, async ({ page }) => {
    await sabitAc(page, '/isler', w, h)
    const ortulen: string[] = []
    for (let i = 0; i < 30; i++) {
      await page.keyboard.press('Tab')
      const k = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement | null
        if (!el || el === document.body || el.closest('.cds--header, .bottom-nav, .cds--side-nav')) return null
        const r = el.getBoundingClientRect()
        const alt = document.querySelector('.bottom-nav')
        const altUst = alt && getComputedStyle(alt).display !== 'none' ? alt.getBoundingClientRect().top : innerHeight
        const bant = document.querySelector('.cds--header')?.getBoundingClientRect().bottom ?? 0
        // Fully hidden: the whole box behind the band or behind the bar (2.4.11 is about full obscuring).
        return { ad: el.textContent?.trim().slice(0, 30) || el.tagName, gizli: r.bottom <= bant + 1 || r.top >= altUst - 1 }
      })
      if (k?.gizli) ortulen.push(k.ad)
    }
    expect(ortulen).toEqual([])
  })
}

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
