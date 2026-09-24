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

// Tedy ders renk sistemi (2026-09-24): an event's kind is its icon, its colour
// its course's mark on the left edge; the chip itself is neutral. Every
// homework used to be a red chip and every private lesson an orange one —
// meaning colours on a taxonomy — and the day heads were a navy strip that
// belongs to the header band alone.
test('events carry their course as an edge and their kind as an icon', async ({ page }) => {
  await page.route('**/api/health', r => r.fulfill(json({
    timestamp: '', success: true, scrape_errors: [], duration_seconds: 1,
  })))
  const ev = (id: string, type: string, title: string, start: string, end: string, course = '', courseFamily = 'gray') =>
    ({ id, type, title, start, end, color: '', course, courseFamily, status: '' })
  await page.route('**/api/calendar/unified', r => r.fulfill(json({ events: [
    ev('a', 'lesson', 'Matematik', '2026-09-14T10:00:00', '2026-09-14T10:40:00', 'Matematik', 'purple'),
    ev('b', 'homework', 'Okuma günlüğü', '2026-09-16T14:00:00', '2026-09-16T14:00:00', 'Türkçe', 'magenta'),
    ev('c', 'event', 'Kulüp', '2026-09-17T12:00:00', '2026-09-17T13:00:00'),
  ] })))
  await page.clock.setFixedTime(new Date('2026-09-14T08:00:00'))
  await page.goto('/takvim')
  await expect(page.locator('.calendar-grid .calendar-event')).toHaveCount(3)

  const odev = page.locator('.calendar-event', { hasText: 'Okuma günlüğü' })
  await expect(odev).toHaveClass(/ted-subject--magenta/)
  await expect(odev.locator('svg')).toHaveCount(1)
  const renk = await odev.evaluate(el => {
    const cs = getComputedStyle(el)
    return { zemin: cs.backgroundColor, kenar: cs.borderLeftColor }
  })
  expect(renk.zemin).toBe('rgb(244, 244, 244)')     // layer-02, not a red fill
  expect(renk.kenar).toBe('rgb(208, 38, 112)')      // magenta-60: Türkçe's mark
  await expect(page.locator('.calendar-event', { hasText: 'Kulüp' })).toHaveClass(/ted-subject--gray/)
  await expect(page.locator('.calendar-legend__chip svg')).toHaveCount(3)

  const bas = await page.locator('.calendar-grid__header').first()
    .evaluate(el => getComputedStyle(el).backgroundColor)
  expect(bas).toBe('rgb(224, 224, 224)')            // layer-accent-01, not the band's navy
})

// A 1fr track grows to its content's min-content: one long unbreakable title
// widened its day and pushed Friday off the grid (live data, 2026-09-24).
test('a long event title does not widen its day', async ({ page }) => {
  await page.route('**/api/health', r => r.fulfill(json({
    timestamp: '', success: true, scrape_errors: [], duration_seconds: 1,
  })))
  const uzun = '5,6,7,8. Sınıflar Kulüp Tanıtımları/ 5,6,7,8th Grades Club Presentations and a much longer tail'
  await page.route('**/api/calendar/unified', r => r.fulfill(json({ events: [
    { id: 'u', type: 'event', title: uzun, start: '2026-09-14T12:00:00', end: '2026-09-14T13:00:00',
      color: '', course: '', courseFamily: 'gray', status: '' },
  ] })))
  await page.clock.setFixedTime(new Date('2026-09-14T08:00:00'))
  for (const [w, h] of [[1280, 900], [390, 844]]) {
    await page.setViewportSize({ width: w, height: h })
    await page.goto('/takvim')
    await expect(page.locator('.calendar-grid .calendar-event')).toHaveCount(1)
    const genislik = await page.locator('.calendar-grid__header').evaluateAll(
      els => els.slice(1).map(e => Math.round(e.getBoundingClientRect().width)))
    expect(genislik).toHaveLength(5)
    expect(Math.max(...genislik) - Math.min(...genislik)).toBeLessThanOrEqual(1)
    await expect(page.locator('.calendar-grid__header').last()).toBeInViewport()
  }
})
