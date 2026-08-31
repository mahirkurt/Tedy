import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'

// docs/frontend-surface-designs.md §4.9. The profile is the one page that is
// about Işık rather than about her work, so operator detail does not belong on
// it and an absent field must be said rather than swallowed.

const json = (b: unknown) => ({
  status: 200, contentType: 'application/json', body: JSON.stringify(b),
})

async function mock(page: Page, profile: Record<string, unknown>) {
  await page.route('**/api/student/profile', r => r.fulfill(json(profile)))
  await page.route('**/api/private-lessons', r => r.fulfill(json({ lessons: [] })))
  await page.route('**/api/health', r => r.fulfill(json({
    timestamp: '', success: true, scrape_errors: [], duration_seconds: 1,
  })))
}

test('no sync plumbing on the page about the child', async ({ page }) => {
  await mock(page, {
    name: 'Işık Kurt', student_no: '260', class_name: '', branch: '',
    photo_data_url: '', fields: { 'Doğum Tarihi': '31.07.2014' },
    scraped_at: '2026-08-31T00:00:13.148211',
  })
  await page.goto('/profil')
  await page.waitForLoadState('networkidle')

  const main = await page.locator('.app-shell-content').innerText()
  // Operator detail, in English, duplicated from the header's health popover.
  expect(main).not.toContain('TED Connect sync')
  // And never the raw shape underneath it.
  expect(main).not.toMatch(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)
})

test('a profile with no fields says so', async ({ page }) => {
  // Exactly what the portal returned on 2026-08-31 while the page it used to
  // live on was 404ing: the shape intact, every value empty.
  await mock(page, {
    name: '', student_no: '', class_name: '', branch: '',
    photo_data_url: '', fields: {}, scraped_at: '',
  })
  await page.goto('/profil')
  await page.waitForLoadState('networkidle')

  // Assert the specific absence. The page already carries an empty line for
  // private lessons, so a generic .tedy-empty check passes without the fields
  // ever saying anything.
  await expect(page.getByText('Portaldan öğrenci bilgisi gelmedi', { exact: false }))
    .toBeVisible()
})
