import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'

// The Bugün screen is judged against docs/frontend-design-principles.md.
// These tests pin the three principles that shaped it, so a later change that
// quietly undoes them fails here rather than in front of Işık.

type Homework = Record<string, string>

async function mockDay(page: Page, opts: { homework?: Homework[] } = {}) {
  const json = (body: unknown) => ({
    status: 200, contentType: 'application/json', body: JSON.stringify(body),
  })
  await page.route('**/api/schedule', r => r.fulfill(json({ weeks: [], latest: null, today: null })))
  await page.route('**/api/teams', r => r.fulfill(json({ ogep: [] })))
  await page.route('**/api/calendar', r => r.fulfill(json({ events: [] })))
  await page.route('**/api/exams', r => r.fulfill(json({ exams: [] })))
  await page.route('**/api/health', r => r.fulfill(json({
    timestamp: '', success: true, scrape_errors: [], duration_seconds: 1,
  })))
  await page.route('**/api/homework', r => r.fulfill(json({
    summary: {}, homework: opts.homework ?? [],
  })))
}

/** A homework row shaped the way the portal actually returns them. */
function hw(over: Homework = {}): Homework {
  const soon = new Date(Date.now() + 26 * 60 * 60 * 1000)
  const pad = (n: number) => String(n).padStart(2, '0')
  return {
    'Ders Adı': 'Matematik',
    'Ödev Başlığı': 'Sayfa 165',
    'Ödev Durumu': 'Değerlendirilmemiş',
    'Ödev Son Teslim Tarihi':
      `${pad(soon.getDate())}.${pad(soon.getMonth() + 1)}.${soon.getFullYear()} 23:59`,
    ...over,
  }
}

test('the day strip shows the time that is left, with a now marker', async ({ page }) => {
  await mockDay(page)
  await page.goto('/')

  const strip = page.locator('.day-strip')
  await expect(strip).toBeVisible()
  // "Now" is the one moving thing on the page (principle İ6) and the anchor
  // that makes the remaining span readable as a distance (İ2).
  await expect(strip.locator('.day-strip__now')).toBeVisible()
  // The strip starts at now, not at the beginning of the day: spent hours are
  // not actionable and must not take up room (İ7).
  await expect(strip).toContainText('ŞİMDİ')
})

test('one named next step leads the page, and the agenda follows it', async ({ page }) => {
  await mockDay(page, { homework: [hw()] })
  await page.goto('/')

  const next = page.locator('.next-thing')
  await expect(next).toBeVisible()
  // Names the work, and names a first step small enough to start (İ3).
  await expect(next).toContainText('Matematik')
  await expect(next).toContainText('dakika')
  // A single, explicitly named action (İ1).
  await expect(next.getByRole('button')).toHaveCount(1)

  // The one thing comes before everything else in reading order.
  const nextY = await next.boundingBox()
  const rest = page.locator('.today__rest')
  if (await rest.count()) {
    const restY = await rest.boundingBox()
    expect(nextY!.y).toBeLessThan(restY!.y)
  }
})

test('the total workload is never the loudest number', async ({ page }) => {
  await mockDay(page, { homework: [hw(), hw({ 'Ödev Başlığı': 'Sayfa 190' }), hw({ 'Ders Adı': 'Fen' })] })
  await page.goto('/')

  // Three items are due, but the card offers one first step, not "3 ödev".
  const next = page.locator('.next-thing')
  await expect(next).toBeVisible()
  await expect(next).not.toContainText('3 ödev')
  await expect(next.locator('.next-thing__step')).toHaveCount(1)
})

test('with no school work, reading takes the slot instead of shouting above it', async ({ page }) => {
  await mockDay(page, { homework: [] })
  await page.goto('/')

  const next = page.locator('.next-thing')
  await expect(next).toBeVisible()
  // Books is the one thing when there is nothing owed — not a louder band
  // sitting on top of the agenda, which is how it read before.
  await expect(next).toContainText('Tedy Books')
  await expect(page.locator('.books-callout')).toHaveCount(0)
})
