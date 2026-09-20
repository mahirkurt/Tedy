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

const HAFTALAR = {
  weeks: {
    '1. Hafta 14 Eyl. - 20 Eyl.': {
      'Türkçe': { cards: ['Defter düzeni | Eda Şen | 14.09.2026\nBirinci hafta metni'] },
    },
    '2. Hafta 21 Eyl. - 27 Eyl.': {
      'Türkçe': { cards: ['Okuma günlüğü | Eda Şen | 21.09.2026\nİkinci hafta metni'] },
    },
  },
  current: '1. Hafta 14 Eyl. - 20 Eyl.',
}

test('course content opens on the current week and can move to another', async ({ page }) => {
  // The portal fills the year in ahead of time and the cards genuinely
  // differ: 12 of 17 courses had different cards in week 2 than week 1.
  // Only 10 of 84 carried a "N. HAFTA" marker, so they cannot be poured
  // into one list and grouped — a week has to be chosen.
  await mock(page, { ...LIVE, content: HAFTALAR.weeks['1. Hafta 14 Eyl. - 20 Eyl.'], 'content/weeks': HAFTALAR })
  await page.goto('/dersler')
  await page.waitForLoadState('networkidle')

  // Scoped to the card body: the same text is also the accordion's title.
  const govde = (t: string) =>
    page.locator('.course-content-text').filter({ hasText: t })

  await expect(govde('Birinci hafta metni')).toHaveCount(1)

  await page.locator('.course-content__week-picker').getByRole('combobox').click()
  await page.getByRole('option', { name: '2. Hafta 21 Eyl. - 27 Eyl.' }).click()

  await expect(govde('İkinci hafta metni')).toHaveCount(1)
  await expect(govde('Birinci hafta metni')).toHaveCount(0)
})

test('no week picker when the portal has given only one week', async ({ page }) => {
  // İ6: a control with one option is something to read past for nothing.
  await mock(page, {
    ...LIVE,
    content: HAFTALAR.weeks['1. Hafta 14 Eyl. - 20 Eyl.'],
    'content/weeks': {
      weeks: { '1. Hafta 14 Eyl. - 20 Eyl.': HAFTALAR.weeks['1. Hafta 14 Eyl. - 20 Eyl.'] },
      current: '1. Hafta 14 Eyl. - 20 Eyl.',
    },
  })
  await page.goto('/dersler')
  await page.waitForLoadState('networkidle')

  await expect(page.locator('.course-content-text')
    .filter({ hasText: 'Birinci hafta metni' })).toHaveCount(1)
  await expect(page.locator('.course-content__week-picker')).toHaveCount(0)
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
