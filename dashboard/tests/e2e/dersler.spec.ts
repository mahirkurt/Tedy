import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'

// docs/frontend-surface-designs.md §1 and §4.3: the timetable and what is in
// those lessons are one question — "what am I studying" — and were two pages
// only because they come from two endpoints.

const json = (b: unknown) => ({
  status: 200, contentType: 'application/json', body: JSON.stringify(b),
})

const SCHEDULE = {
  weeks: [],
  latest: {
    week_label: '15-19 Eylül',
    schedule: {
      headers: ['Saat', 'Pazartesi'],
      rows: [['08:30', 'Matematik']],
    },
  },
  today: null,
}

// /api/content returns the courses at the top level, and a course only counts
// as having content if it carries text or cards — otherwise the component
// renders nothing at all.
const CONTENT = {
  'Matematik': { text: 'Kesirler konusu işlendi.', cards: [], items: [] },
}

async function mock(page: Page) {
  await page.route('**/api/schedule', r => r.fulfill(json(SCHEDULE)))
  await page.route('**/api/content', r => r.fulfill(json(CONTENT)))
  await page.route('**/api/health', r => r.fulfill(json({
    timestamp: '', success: true, scrape_errors: [], duration_seconds: 1,
  })))
}

test('the timetable and the lesson content share one page', async ({ page }) => {
  await mock(page)
  await page.goto('/dersler')
  await page.waitForLoadState('networkidle')

  expect(new URL(page.url()).pathname).toBe('/dersler')
  await expect(page.getByText('Haftalık Program', { exact: false })).toBeVisible()
  await expect(page.getByText('Ders İçerikleri', { exact: false })).toBeVisible()
})

test('the old timetable path still lands somewhere', async ({ page }) => {
  await mock(page)
  await page.goto('/program')
  await page.waitForURL('**/dersler')
  expect(new URL(page.url()).pathname).toBe('/dersler')
})

test('the navigation lost another decision', async ({ page }) => {
  await mock(page)
  await page.goto('/dersler')
  await page.waitForLoadState('networkidle')

  const nav = page.locator('nav').first()
  await expect(nav.getByText('Dersler', { exact: true })).toHaveCount(1)
  await expect(nav.getByText('Program', { exact: true })).toHaveCount(0)
})

test('five things to choose between, the rest one level down', async ({ page }) => {
  await mock(page)
  await page.goto('/dersler')
  await page.waitForLoadState('networkidle')

  const nav = page.locator('nav').first()
  for (const label of ['Bugün', 'İşler', 'Dersler', 'Asistan', 'Tedy Books']) {
    await expect(nav.getByText(label, { exact: true })).toBeVisible()
  }
  // Everything reachable but not worth a decision before doing anything sits
  // under one entry rather than competing for the same glance.
  await expect(nav.getByText('Daha fazla', { exact: true })).toBeVisible()
  await expect(nav.getByText('Notlar', { exact: true })).toHaveCount(1)
})
