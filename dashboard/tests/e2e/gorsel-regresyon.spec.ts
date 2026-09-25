import { test, expect } from '@playwright/test'
import { SAYFALAR, sabitAc } from './_gorsel-yardim'

// Visual regression: every surface at a desktop and a phone width, compared
// pixel by pixel with a stored baseline. On 2026-09-25 a Playwright + axe
// audit found layout faults that no assertion was looking for — İlerleme
// shrunk to 290px, the week table cutting "Matematik" to "Matema", a stray
// connector under the day strip. Each was visible in a screenshot and
// invisible to the tests; this spec is that screenshot, kept.
//
// Deterministic by construction: fixed data (GORSEL, no live endpoint),
// fixed clock (a school Thursday mid-morning, SABIT_SAAT), Istanbul time zone, fonts
// loaded before the shot, animations off.
//
// A change you meant: `npx playwright test gorsel-regresyon --update-snapshots`,
// then look at the new PNGs before committing them.

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

for (const [boy, w, h] of [['masaustu', 1440, 900], ['telefon', 390, 844]] as const) {
  for (const [ad, yol] of SAYFALAR) {
    test(`${ad} looks as it did (${boy})`, async ({ page }) => {
      await sabitAc(page, yol, w, h)
      await expect(page).toHaveScreenshot(`${ad}-${boy}.png`, {
        fullPage: true,
        animations: 'disabled',
        caret: 'hide',
        maxDiffPixelRatio: 0.002,
      })
    })
  }
}

test('the sign-in page looks as it did', async ({ page }) => {
  await page.route('**/api/auth/me', r => r.fulfill({ status: 401, body: '{}' }))
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Hoş geldiniz' })).toBeVisible()
  await page.evaluate(() => document.fonts.ready.then(() => undefined))
  await expect(page).toHaveScreenshot('giris-masaustu.png', {
    animations: 'disabled',
    // The Google button is Google's iframe; it renders when and how Google likes.
    mask: [page.locator('iframe')],
    maxDiffPixelRatio: 0.002,
  })
})
