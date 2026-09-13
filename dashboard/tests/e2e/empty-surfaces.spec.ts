import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'

// D3, "sessiz arıza yok": a surface with nothing on it must say so. Four
// components returned null when their data was empty, so with the portal
// closed for the new school year those pages opened completely blank — and a
// blank page is indistinguishable from a broken one.

const json = (b: unknown) => ({
  status: 200, contentType: 'application/json', body: JSON.stringify(b),
})

async function everythingEmpty(page: Page) {
  const empties: Array<[string, unknown]> = [
    ['schedule', { weeks: [], latest: null, today: null }],
    ['content', {}],
    ['teams', { activities: [], ogep: [] }],
    ['announcements', { announcements: [] }],
    ['calendar/unified', { events: [] }],
    ['exams', { exams: [] }],
    ['grades', { grades: [] }],
    ['homework', { summary: '', homework: [] }],
    ['enrichment', {}],
    ['health', { timestamp: '', success: true, scrape_errors: [], duration_seconds: 1 }],
  ]
  for (const [ep, body] of empties) {
    await page.route(`**/api/${ep}`, r => r.fulfill(json(body)))
  }
}

const surfaces: Array<[string, string]> = [
  ['/dersler', 'Dersler'],
  ['/takimlar', 'Takımlar'],
  ['/duyurular', 'Duyurular'],
]

for (const [path, name] of surfaces) {
  test(`${name} says it is empty rather than showing nothing`, async ({ page }) => {
    await everythingEmpty(page)
    await page.goto(path)
    await page.waitForLoadState('networkidle')

    // The surface's own words, not the region's text. This used to read the
    // innerText of .app-shell-content and require it to be non-empty — which
    // stopped proving anything once the shell gained a visually hidden page
    // <h1>: innerText includes it, so the region always has text and a
    // completely blank surface would pass. The empty line is what the surface
    // says; waiting on it is also the condition that replaces the fixed wait.
    const main = page.locator('.app-shell-content')
    await expect(main.locator('.tedy-empty').first()).toBeVisible()
  })
}
