import { test, expect } from '@playwright/test'
import { mock, LIVE } from './_audit-fixtures'

// The timetable arrived from the portal with lessons in it and rendered as a
// bare column of times: the day columns never matched, so nothing was shown
// beside the clock. Measured against the real scraped_data.json on
// 2026-09-20.

test('the days match however the portal capitalises them', async ({ page }) => {
  // The portal writes "PAZARTESI". The component compared against
  // "Pazartesi" with indexOf, so no column matched at all — and a Turkish
  // locale uppercase does not fix it either, because that produces
  // "PAZARTESİ" with a dotted İ against the portal's dotless one. Monday was
  // the only day with an i, so it alone failed and every lesson shifted a
  // column to the left.
  await mock(page, {
    ...LIVE,
    schedule: {
      latest: {
        week_label: '1. Hafta', is_current: true,
        schedule: {
          headers: [],
          rows: [
            ['', 'PAZARTESI', 'SALI', 'ÇARŞAMBA', 'PERŞEMBE', 'CUMA'],
            ['1. Ders\n08:00 - 08:40', 'Türkçe', 'Matematik', 'Fen', 'Görsel', 'Müzik'],
          ],
        },
      },
      today: '',
    },
  })
  await page.goto('/dersler')
  await page.waitForLoadState('networkidle')

  await expect(page.getByRole('columnheader', { name: 'Pazartesi' })).toBeVisible()
  await expect(page.locator('.schedule-lesson').first()).toHaveText('Türkçe')
  // Alignment: the last day's lesson has to land under the last day.
  await expect(page.locator('.schedule-lesson').nth(4)).toHaveText('Müzik')
})

test('a day the portal leaves out does not shift the rest', async ({ page }) => {
  // The old code filtered the index list, so one missing day moved every day
  // after it one column left.
  await mock(page, {
    ...LIVE,
    schedule: {
      latest: {
        week_label: '1. Hafta', is_current: true,
        schedule: {
          headers: [],
          rows: [
            ['', 'PAZARTESI', 'ÇARŞAMBA', 'CUMA'],
            ['1. Ders\n08:00 - 08:40', 'Türkçe', 'Fen', 'Müzik'],
          ],
        },
      },
      today: '',
    },
  })
  await page.goto('/dersler')
  await page.waitForLoadState('networkidle')

  await expect(page.getByRole('columnheader', { name: 'Salı' })).toHaveCount(0)
  const cells = page.locator('.schedule-lesson')
  await expect(cells).toHaveCount(3)
  await expect(cells.nth(1)).toHaveText('Fen')
})

test('the timetable shows no week picker', async ({ page }) => {
  // İ6: the portal offers 36 weeks and every one renders the identical grid,
  // so a stepper here would change a label and nothing else.
  await mock(page, {
    ...LIVE,
    schedule: {
      latest: {
        week_label: '1. Hafta', is_current: true,
        schedule: {
          headers: [],
          rows: [
            ['', 'PAZARTESI'],
            ['1. Ders\n08:00 - 08:40', 'Türkçe'],
          ],
        },
      },
      today: '',
    },
  })
  await page.goto('/dersler')
  await page.waitForLoadState('networkidle')

  await expect(page.locator('.schedule-lesson').first()).toHaveText('Türkçe')
  await expect(page.getByLabel('Sonraki hafta')).toHaveCount(0)
})
