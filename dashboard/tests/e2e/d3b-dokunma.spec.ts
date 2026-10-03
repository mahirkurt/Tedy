import { test, expect } from '@playwright/test'
import type { Locator } from '@playwright/test'
import { sabitAc } from './_gorsel-yardim'

// D3b page gate after the audit: on a phone, a control the reader taps is at
// least 44px. spacing-09 is 48px. The English library defaults named in the
// audit fail here too.

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

async function enAz(locator: Locator, px = 44) {
  const n = await locator.count()
  expect(n).toBeGreaterThan(0)
  for (let i = 0; i < n; i++) {
    const box = await locator.nth(i).boundingBox()
    expect(box, `kontrol ${i}`).not.toBeNull()
    expect(box!.width).toBeGreaterThanOrEqual(px)
    expect(box!.height).toBeGreaterThanOrEqual(px)
  }
}

test('Bugün day arrows are at least 44px on a phone', async ({ page }) => {
  await sabitAc(page, '/', 390, 844)
  await enAz(page.getByRole('button', { name: 'Önceki gün', exact: true }))
  await enAz(page.getByRole('button', { name: 'Sonraki gün', exact: true }))
})

test('Asistan prompt chips are at least 44px on a phone', async ({ page }) => {
  await sabitAc(page, '/asistan', 390, 844)
  await enAz(page.locator('.ac__prompt-chip'))
})

test('Takvim week arrows say Önceki and are at least 44px on a phone', async ({ page }) => {
  await sabitAc(page, '/takvim', 390, 844)
  await expect(page.getByRole('button', { name: 'Onceki hafta', exact: true })).toHaveCount(0)
  await enAz(page.getByRole('button', { name: 'Önceki hafta', exact: true }))
  await enAz(page.getByRole('button', { name: 'Sonraki hafta', exact: true }))
})

test('Notlar row detail control is Turkish and at least 44px on a phone', async ({ page }) => {
  await sabitAc(page, '/notlar', 390, 844)
  await expect(page.getByRole('button', { name: 'Expand current row', exact: true })).toHaveCount(0)
  await enAz(page.getByRole('button', { name: 'Ayrıntı', exact: true }))
})

test('Dersler content headings are at least 44px on a phone', async ({ page }) => {
  await sabitAc(page, '/dersler', 390, 844)
  // Other course tabs keep their headings in the DOM, hidden. Measure the one on screen.
  await enAz(page.locator('.course-content .cds--accordion__heading:visible'))
})
