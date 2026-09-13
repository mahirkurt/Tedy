import { test, expect } from '@playwright/test'
import { mock, FULL, LIVE, json } from './_audit-fixtures'

// Aesthetic findings from reading the captured surfaces. Each one is a thing
// the screenshots showed, not a thing the source suggested.

test('the calendar copy is spelled in Turkish', async ({ page }) => {
  await mock(page, LIVE)
  await page.goto('/takvim')
  await page.waitForLoadState('networkidle')
  const text = await page.locator('.app-shell-content').innerText()
  expect(text).toContain('Haftalık Takvim')
  expect(text).not.toContain('Haftalik')
})

test('a markdown list looks like a list', async ({ page }) => {
  // Carbon's reset sets `list-style: none` on every ul/ol, so the assistant's
  // answers rendered their steps as three unmarked lines.
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/assistant/chat', r => r.fulfill(json({
    answer: 'Adımlar:\n\n- önce paydayı eşitle\n- sonra payları topla',
    citations: [], safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
    meta: { model: 'gemini-3.7-flash', degraded: [], dropped_citations: 0 },
  })))
  await page.goto('/asistan')
  await page.waitForLoadState('networkidle')
  await page.fill('#ac-input', 'nasıl')
  await page.getByLabel('Gönder').click()
  // Wait for the element being measured: evaluate() below does not retry.
  await page.locator('.bookmd__list').first().waitFor()

  const style = await page.locator('.bookmd__list').first()
    .evaluate(el => getComputedStyle(el).listStyleType)
  expect(style, 'liste işareti yok').not.toBe('none')
})

test('the two empty sections on Dersler say which is which', async ({ page }) => {
  // Both rendered as bare grey sentences with nothing naming them, so the
  // page read as two unattributed statements.
  // Both sections genuinely empty — LIVE keeps real course content, which
  // would leave only one empty line on the page.
  await mock(page, { ...LIVE, content: {} })
  await page.goto('/dersler')
  await page.waitForLoadState('networkidle')
  // allInnerTexts() does not retry, so reading it before the second section
  // rendered returns a short array. Wait for both labels to exist.
  await expect(page.locator('.tedy-empty__label')).toHaveCount(2)

  // The labels are upper-cased by CSS and innerText reports what is
  // rendered, so compare against the upper-cased forms rather than
  // round-tripping through a Turkish lowercase (where İ → i + combining dot
  // and no longer matches a plain i).
  const labels = await page.locator('.tedy-empty__label').allInnerTexts()
  expect(labels.map(s => s.trim()))
    .toEqual(['HAFTALIK PROGRAM', 'DERS İÇERİKLERİ'])
})

test('an empty grade table says it is empty instead of showing a bare header', async ({ page }) => {
  await mock(page, LIVE)
  await page.goto('/notlar')
  await page.waitForLoadState('networkidle')
  // Zero header cells is the passing case below — and a page that has not
  // rendered yet also has zero header cells. Wait for the grades surface to
  // settle into one of its two shapes before counting anything.
  await page.locator('.tedy-empty, table').first().waitFor({ state: 'attached' })

  // A header row with no rows under it claims data that is not there.
  const headerCells = await page.locator('th').count()
  const bodyRows = await page.locator('tbody tr').count()
  expect(headerCells === 0 || bodyRows > 0,
    `başlıksız gövde: ${headerCells} başlık hücresi, ${bodyRows} satır`).toBe(true)
  await expect(page.getByText('not girilmemiş', { exact: false })).toBeVisible()
})

test('the grade title has no dangling separator', async ({ page }) => {
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/grades', r => r.fulfill(json({ grades: [], semester: '' })))
  await page.goto('/notlar')
  await page.waitForLoadState('networkidle')
  // Same reason: "no dangling dash" is true of a page with no title yet.
  await page.locator('.tedy-empty, table').first().waitFor({ state: 'attached' })
  const text = await page.locator('.app-shell-content').innerText()
  expect(text).not.toMatch(/Notlar\s+[—–-]\s*(\n|$)/)
})

test('the portal banner stays off surfaces that are not portal data', async ({ page }) => {
  await mock(page, LIVE)
  for (const path of ['/kitaplar', '/asistan']) {
    await page.goto(path)
    await page.waitForLoadState('networkidle')
    // An absence is true of a page that has not rendered. The page heading is
    // written by the same App render that decides whether the banner mounts,
    // and networkidle means the health response it would show is already in
    // hand — so once the heading exists, a banner that was coming is here.
    await page.locator('.app-shell-content h1').waitFor({ state: 'attached' })
    await expect(page.locator('.portal-status'),
      `${path} üzerinde portal banner'ı var`).toHaveCount(0)
  }
  // It still appears where the portal's own sections are shown.
  await page.goto('/takvim')
  await page.waitForLoadState('networkidle')
  await expect(page.locator('.portal-status')).toHaveCount(1)
})

test('the calendar legend names only the kinds in view', async ({ page }) => {
  // Seven chips rendered whatever the week held, so a week with two kinds of
  // event still opened with seven colours to read past.
  //
  // This used to run against FULL, whose calendar rows use the wrong field
  // names (baslik/tarih/tur) and so put no event on the grid at all. It passed
  // by counting zero chips, and its failure message counted
  // `.calendar-grid__event`, a class the component has never had. Two kinds
  // this week and a third kind next week make the filter do real work: the
  // legend has to name exactly the kinds on screen, not merely fewer than
  // seven.
  await mock(page, FULL)
  const ev = (id: string, type: string, title: string, start: string, end: string) =>
    ({ id, type, title, start, end, color: '', course: '', status: '' })
  // Registered after mock(), so it takes precedence over FULL's calendar route.
  await page.route('**/api/calendar/unified', r => r.fulfill(json({ events: [
    ev('a', 'lesson', 'Matematik', '2026-09-14T10:00:00', '2026-09-14T10:40:00'),
    ev('b', 'homework', 'Okuma', '2026-09-16T14:00:00', '2026-09-16T14:30:00'),
    ev('c', 'team', 'Satranç', '2026-09-23T15:00:00', '2026-09-23T16:00:00'),
  ] })))
  // A Monday, so the week in view is 14–18 September and 'team' falls outside it.
  await page.clock.setFixedTime(new Date('2026-09-14T09:00:00'))
  await page.goto('/takvim')
  await page.waitForLoadState('networkidle')
  // Zero chips is exactly what an unrendered week shows, so wait for this
  // week's events to be on the grid before reading the legend.
  await expect(page.locator('.calendar-grid .calendar-event')).toHaveCount(2)

  const chips = page.locator('.calendar-legend__chip')
  await expect(chips).toHaveCount(2)
  const labels = (await chips.allInnerTexts()).map(s => s.trim()).sort()
  expect(labels).toEqual(['Ders', 'Ödev'])
})
