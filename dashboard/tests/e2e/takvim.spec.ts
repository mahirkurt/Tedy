import { test, expect } from '@playwright/test'

// §4.5 / İ7: hours already spent cannot be acted on, so they recede rather
// than competing with what is still ahead. Today was marked; the past was not.

const json = (b: unknown) => ({
  status: 200, contentType: 'application/json', body: JSON.stringify(b),
})

test('a closed calendar does not draw an empty week', async ({ page }) => {
  await page.route('**/api/calendar/unified', r => r.fulfill(json({ events: [] })))
  await page.route('**/api/health', r => r.fulfill(json({
    timestamp: '', success: true, scrape_errors: [], duration_seconds: 1,
    unavailable: {
      takvim: { reason: 'yetkisiz', detail: 'Akademik Takvim: portal bu sayfaya yetki vermiyor' },
    },
  })))
  await page.goto('/takvim')
  await page.waitForLoadState('networkidle')

  await expect(page.locator('.calendar-grid')).toHaveCount(0)
  await expect(page.locator('.tedy-empty')).toContainText('portal bu sayfaya yetki vermiyor')
  await expect(page.getByRole('button', { name: /Bugün/ })).toBeVisible()
})

test('spent hours recede in the week grid', async ({ page }) => {
  await page.route('**/api/calendar/unified', r => r.fulfill(json({ events: [] })))
  await page.route('**/api/health', r => r.fulfill(json({
    timestamp: '', success: true, scrape_errors: [], duration_seconds: 1,
  })))
  // Midweek, midday: there are hours behind and hours ahead.
  await page.clock.setFixedTime(new Date('2026-09-16T13:00:00'))
  await page.goto('/takvim')
  await page.waitForLoadState('networkidle')

  const past = page.locator('.calendar-grid__cell--past')
  const cells = page.locator('.calendar-grid__cell')
  expect(await cells.count()).toBeGreaterThan(0)
  // Some of the week is behind us, and not all of it.
  expect(await past.count()).toBeGreaterThan(0)
  expect(await past.count()).toBeLessThan(await cells.count())
})
