import { test, expect } from '@playwright/test'
import { mock, LIVE } from './_audit-fixtures'

// Işık reported on 2026-09-23 that the daily timetable was simply not there.
// It was not a scrape failure: output/scraped_data.json held the full week.
// Bugün looked its day up with `rows[0].indexOf('Çarşamba')` while the portal
// writes "ÇARŞAMBA", so the lookup returned -1 for every one of the seven
// days and the agenda silently had no lessons in it.
//
// The grid also is not one table. The portal lays the week out as two blocks,
// each with its own time column, because Friday runs on a later bell: the
// second lesson starts at 08:55 Monday-Thursday and 09:00 on Friday, and the
// gap reaches ten minutes by the fifth. Reading Friday's times from column 0
// would put Işık outside the classroom five minutes early every period.

/** The real shape from output/scraped_data.json, 2. Hafta 21-27 Eyl. 2026:
 *  empty `headers`, day names in row 0, a blank header over each of the two
 *  time columns, and the short breakfast rows the portal collapses. */
const GRID = {
  weeks: [],
  today: 'Çarşamba',
  latest: {
    week_label: '2. Hafta 21 Eyl. - 27 Eyl.',
    is_current: true,
    schedule: {
      headers: [],
      rows: [
        ['', 'PAZARTESI', 'SALI', 'ÇARŞAMBA', 'PERŞEMBE', '', 'CUMA', 'CUMARTESI', 'PAZAR'],
        ['1. Ders\n\n08:00 - 08:40',
          'Türkçe\nEda Şen', 'Matematik\nNagihan Özdemir',
          'Sosyal Bilgiler\nEmre Angıç', 'Matematik\nNagihan Özdemir',
          '1. Ders\n\n08:00 - 08:40', 'Sosyal Bilgiler\nEmre Angıç', '', ''],
        ['08:40 - 08:55', 'Kahvaltı', '08:40 - 09:00', 'Kahvaltı', ''],
        ['2. Ders\n\n08:55 - 09:35',
          'Fransızca\nHarika Ebru Kalkan', 'Fransızca\nHarika Ebru Kalkan',
          'İngilizce\nİpek Pehlevan', 'Görsel Sanatlar\nSelin Ak',
          '2. Ders\n\n09:00 - 09:40', 'Fen Bilimleri\nAyla Tan', '', ''],
      ],
    },
  },
}

const ac = async (
  page: import('@playwright/test').Page, tarih: string, yol = '/'
) => {
  await page.clock.setFixedTime(new Date(tarih))
  await mock(page, { ...LIVE, schedule: GRID, calendar: { events: [] } })
  await page.goto(yol)
  await page.waitForLoadState('networkidle')
}

test('çarşamba günü o günün dersleri listelenir', async ({ page }) => {
  // Before the first bell: finished lessons now fold to one line (İ7), and
  // this test is about finding the day's column, not about folding.
  await ac(page, '2026-09-23T07:50:00')

  const isimler = page.locator('.today-tl__card-name')
  await expect(isimler.first()).toBeVisible()
  await expect(isimler).toContainText(['Sosyal Bilgiler', 'İngilizce'])
})

test('cuma dersleri cumanın kendi zilini gösterir', async ({ page }) => {
  // The whole point of the second block: column 0 would say 08:55 here.
  await ac(page, '2026-09-25T09:10:00')

  const satir = page.locator('.today-tl__item', { hasText: 'Fen Bilimleri' })
  await expect(satir).toHaveCount(1)
  await expect(satir.locator('.today-tl__time')).toContainText('09:00')
  await expect(satir.locator('.today-tl__time')).not.toContainText('08:55')
})

test('hafta sonu ders göstermez', async ({ page }) => {
  // A day the grid publishes as empty must not borrow another day's column.
  await ac(page, '2026-09-26T09:10:00')

  await expect(page.locator('.today-tl__card-name')).toHaveCount(0)
})

test('haftalık tabloda cuma kendi saatini taşır', async ({ page }) => {
  await ac(page, '2026-09-23T09:10:00', '/dersler')
  await page.locator('.schedule-table').first().waitFor()

  // The shared Saat column speaks for Monday-Thursday...
  const ikinciDers = page.locator('tr', { hasText: 'Fransızca' }).first()
  await expect(ikinciDers.locator('.schedule-time')).toContainText('08:55')
  // ...and the Friday cell corrects itself rather than being misstated by it.
  await expect(ikinciDers.locator('.schedule-own-time')).toHaveText('09:00')
  // Monday sits under the same bell as the Saat column, so it stays quiet (İ6).
  const pzt = ikinciDers.locator('td').nth(1)
  await expect(pzt.locator('.schedule-own-time')).toHaveCount(0)
})
