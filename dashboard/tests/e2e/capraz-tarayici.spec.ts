import { test, expect } from '@playwright/test'
import { SAYFALAR, sabitAc } from './_gorsel-yardim'

// Every surface in Safari's engine (WebKit) and Firefox as well as Chromium —
// run by the `webkit` and `firefox` projects in playwright.config.ts; the rest
// of the suite is Chromium only. The family reads TEDY on phones, and an
// iPhone is WebKit whatever its browser says. Kept to what differs between
// engines: the page renders its content, throws nothing, and fits the width.
// Pixel comparison stays in Chromium (gorsel-regresyon.spec.ts): engines set
// type differently, so a cross-engine screenshot would only measure that.

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

for (const [boy, w, h] of [['masaüstü', 1440, 900], ['telefon', 390, 844]] as const) {
  for (const [ad, yol] of SAYFALAR) {
    test(`${ad} renders on a ${boy}`, async ({ page }) => {
      // Three engines share one test server; under the full suite a page can
      // take far longer than alone (sabitAc explains the idle wait).
      test.setTimeout(60_000)
      const hatalar: string[] = []
      page.on('pageerror', e => hatalar.push(String(e)))
      await sabitAc(page, yol, w, h)
      const icerik = page.locator('.app-shell-content')
      await expect(icerik).toContainText(/\S{3,}/)
      await expect(page.getByText('Bu bölüm açılamadı')).toHaveCount(0)
      const tasma = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
      expect(tasma, 'yatay taşma (px)').toBeLessThanOrEqual(0)
      expect(hatalar).toEqual([])
    })
  }
}
