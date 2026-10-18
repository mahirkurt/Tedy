import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'

// docs/frontend-surface-designs.md §4.7. The three platform panels rendered
// "… listesi yükleniyor…" as their EMPTY branch, so a list that is simply
// empty told the reader to wait for something that was never coming.

const json = (b: unknown) => ({
  status: 200, contentType: 'application/json', body: JSON.stringify(b),
})

async function mock(page: Page) {
  await page.route('**/api/progress/ec', r => r.fulfill(json({})))
  await page.route('**/api/progress/a3k', r => r.fulfill(json({})))
  await page.route('**/api/sebit', r => r.fulfill(json({})))
  await page.route('**/api/health', r => r.fulfill(json({
    timestamp: '', success: true, scrape_errors: [], duration_seconds: 1,
  })))
}

test('an empty platform says it is empty, not that it is loading', async ({ page }) => {
  await mock(page)
  await page.goto('/ilerleme')
  await page.waitForLoadState('networkidle')

  // The message lives inside the panels, which start collapsed — a test that
  // only reads the page as it lands passes without touching the defect.
  const panels = page.locator('.cds--accordion__heading')
  // count() does not retry: read early it returns 0. Wait for the panels to
  // exist instead of for a duration.
  await expect(panels).not.toHaveCount(0)
  const count = await panels.count()
  for (let i = 0; i < count; i++) {
    await panels.nth(i).click()
  }
  // "Not loading" is an absence, and an absence is true of panels that have
  // not opened yet. Prove every panel opened before reading what they say.
  await expect(page.locator('.cds--accordion__item--active')).toHaveCount(count)

  const body = await page.locator('body').innerText()
  expect(body).not.toContain('yükleniyor')
})

test('SEBİT switched off says "Takip edilmiyor" and shows no old homework', async ({ page }) => {
  await mock(page)
  // The old reading still sits on disk; while SEBİT is off the API never serves it.
  await page.route('**/api/sebit', r => r.fulfill(json({ pasif: true })))
  await page.goto('/ilerleme')

  const satir = page.locator('.platform-list__row', { hasText: 'SEBIT' })
  await expect(satir.locator('.platform-list__state')).toHaveText('Takip edilmiyor')
  await expect(page.getByRole('button', { name: 'SEBIT ödevleri' })).toHaveCount(0)
})
