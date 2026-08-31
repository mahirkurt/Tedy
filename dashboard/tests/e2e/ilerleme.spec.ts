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
  // Give the panels time to settle past any genuine loading state.
  await page.waitForTimeout(800)

  // The message lives inside the panels, which start collapsed — a test that
  // only reads the page as it lands passes without touching the defect.
  const panels = page.locator('.cds--accordion__heading')
  const count = await panels.count()
  expect(count).toBeGreaterThan(0)
  for (let i = 0; i < count; i++) {
    await panels.nth(i).click()
  }
  await page.waitForTimeout(300)

  const body = await page.locator('body').innerText()
  expect(body).not.toContain('yükleniyor')
})
