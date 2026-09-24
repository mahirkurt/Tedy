import { test, expect } from '@playwright/test'
import { bugunAc, SINAV, HW, CALENDAR } from './_bugun-fixtures'
import { mock, LIVE } from './_audit-fixtures'

// The exam list on Bugün had never appeared: /api/exams compared the portal's
// "Z"-marked time with a naive now, the TypeError was swallowed, and every
// takvim exam was "past" (fixed in the API — tests/test_portal_saati.py). Now
// it appears, so it has to follow the page's rules: quiet names and days, no
// coloured countdown chips or per-course colours (İ6, İ8), and an exam that is
// tomorrow leads the evening's "Yarın" instead of shouting on the card — at
// 20:00 the interface must not say "start revising" (İ4's own test).

const SINAVLAR = { exams: [
  SINAV('gis1', 'Özdebir GİS-1', '2026-09-25T09:00:00'),
  SINAV('tr2', 'Türkçe Ortak Yazılı', '2026-10-23T10:30:00'),
], stats: { upcoming: 2, past: 0, averageGrade: null } }

test.describe('C4 — sınavlar', () => {
  test('yarınki sınav akşam Yarın kartının başında, listede tekrar yok', async ({ page }) => {
    await bugunAc(page, '2026-09-24T16:40', { exams: SINAVLAR })

    const yarin = page.locator('.today-tomorrow')
    const ilkSatir = yarin.locator('p').first()
    await expect(ilkSatir).toContainText('SINAV')
    await expect(ilkSatir).toContainText('09:00')
    await expect(ilkSatir).toContainText('Özdebir GİS-1')

    const liste = page.locator('.today-exams')
    await expect(liste).not.toContainText('Özdebir GİS-1')
    await expect(liste).toContainText('Türkçe Ortak Yazılı')
    await expect(liste).toContainText('23 Eki 10:30')
    // The card is still the homework: an exam tomorrow is information for
    // the evening, not a prompt to start deep work at night (İ4).
    await expect(page.locator('.next-thing')).toContainText('Matematik')
  })

  test('sınav listesi sessiz: renkli etiket ve ders rengi yok', async ({ page }) => {
    await bugunAc(page, '2026-09-24T10:15', { exams: SINAVLAR })
    const liste = page.locator('.today-exams')
    await expect(liste).toContainText('Özdebir GİS-1')
    await expect(liste).toContainText('yarın 09:00')
    await expect(liste.locator('.cds--tag')).toHaveCount(0)
    const renkli = await liste.locator('[style*="color"]').count()
    expect(renkli).toBe(0)
  })
})

test.describe('İstanbul saatindeki tarayıcı', () => {
  test.use({ timezoneId: 'Europe/Istanbul' })

  test('kulüp etkinliği ders programındaki yerinde, 12:40\'ta görünür', async ({ page }) => {
    // The API now sends the portal's local time without its bogus "Z"; a
    // browser in Turkey must show it as written. With the "Z" it showed 15:40.
    await bugunAc(page, '2026-09-24T07:30:00+03:00', { calendar: { events: [{
      ...CALENDAR.events[0], start: '2026-09-24T12:40:00', end: '2026-09-24T14:10:00',
    }] } })
    const satir = page.locator('.today-tl__item', { hasText: 'Kulüp' })
    await expect(satir.locator('.today-tl__time')).toHaveText('12:40')
  })
})

test('İşler: Yaptım kaydedilemezse satır bunu söyler', async ({ page }) => {
  // It used to do nothing at all: `if (res.ok) {…}` and no else (D3).
  await mock(page, { ...LIVE, homework: { summary: '', homework: [
    HW('Fransızca', 'S1 Les verbes', '28.09.2026 08:55'),
  ] } })
  await page.route('**/api/homework/mark-done', r => r.fulfill({ status: 500, body: '{}' }))
  await page.clock.setFixedTime(new Date('2026-09-24T16:40:00'))
  await page.goto('/isler')
  await page.waitForLoadState('networkidle')

  await page.locator('.homework-item').getByRole('button', { name: 'Yaptım' }).click()
  await expect(page.locator('.homework-item')).toContainText('Kaydedilemedi')
})

test('Bugün: uzak sınavlar yakın ödevlerin altında', async ({ page }) => {
  // Live, 2026-09-24: exams 29+ days away sat above homework due in four.
  await bugunAc(page, '2026-09-24T16:40', { exams: SINAVLAR })
  const [ayrica, sinav] = [
    await page.locator('.today-also').boundingBox(),
    await page.locator('.today-exams').boundingBox(),
  ]
  expect(ayrica!.y).toBeLessThan(sinav!.y)
})

test.describe('İşler, gerçek sınav verisiyle', () => {
  // The exam list here had never rendered with live data either. Live, the
  // title already carries the course ("Özdebir Gelişim İzleme Sınavı GİS ·
  // İzleme Sınavı" under course "Özdebir Gelişim İzleme Sınavı GİS"), so the
  // row read the same words twice.
  test('başlık dersi zaten söylüyorsa ders ayrıca yazılmaz', async ({ page }) => {
    const gis = { ...SINAV('gis1', 'Özdebir Gelişim İzleme Sınavı GİS · İzleme Sınavı', '2026-10-23T09:00:00'),
      course: 'Özdebir Gelişim İzleme Sınavı GİS' }
    const mat = { ...SINAV('mat1', '1. Yazılı', '2026-10-30T10:35:00'), course: 'Matematik' }
    await mock(page, { ...LIVE, exams: { exams: [gis, mat], stats: {} } })
    await page.goto('/isler')
    await page.waitForLoadState('networkidle')

    const satir = page.locator('.exams-ahead__row', { hasText: 'İzleme Sınavı' })
    await expect(satir.locator('.exams-ahead__course')).toHaveCount(0)
    // Where the title alone would lose the course, the course stays.
    await expect(page.locator('.exams-ahead__row', { hasText: '1. Yazılı' })).toContainText('Matematik')
  })

  test('üstteki kart dersi listeyle aynı adla anar', async ({ page }) => {
    await mock(page, { ...LIVE, homework: { summary: '', homework: [
      HW('İkinci Yabancı Dil (Fransızca)', 'S1 Les verbes', '28.09.2026 08:55', '',
        { normalized_course: 'Fransızca' }),
    ] } })
    await page.clock.setFixedTime(new Date('2026-09-24T16:40:00'))
    await page.goto('/isler')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.next-thing')).toContainText('Fransızca — S1 Les verbes')
    await expect(page.locator('.next-thing')).not.toContainText('İkinci Yabancı Dil')
  })
})
