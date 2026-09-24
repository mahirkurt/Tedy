import { test, expect, type Page, type Route } from '@playwright/test'
import { bugunAc, HOMEWORK, MATEMATIK, HW } from './_bugun-fixtures'

// C1: once the school day is over, Bugün says where to be tomorrow — the first
// lesson and the day's courses — which is what packing a bag the evening
// before needs (a standard executive-function support). Deadlines are not
// repeated there: the card and "Ayrıca" already name them with their days.
//
// C3: "Yaptım" on Bugün itself, inside the time box, so the loop closes on the
// page where the work was started.

test.describe('C1 — Yarın', () => {
  test('son zilden sonra yarının ilk dersi ve dersleri görünür', async ({ page }) => {
    await bugunAc(page, '2026-09-24T16:40')
    const yarin = page.locator('.today-tomorrow')
    await expect(yarin).toContainText('YARIN · CUMA')
    await expect(yarin).toContainText('İlk ders 08:00 · Sosyal Bilgiler')
    await expect(yarin).toContainText('5 ders')
    await expect(yarin).toContainText('Müzik')
    // Tomorrow's work is already on the card above; not a second time here.
    await expect(yarin).not.toContainText('MATEMATİK')
  })

  test('ders sürerken yarın kartı yok', async ({ page }) => {
    await bugunAc(page, '2026-09-24T10:15')
    await expect(page.locator('.today-tomorrow')).toHaveCount(0)
  })

  test('cuma akşamı sıradaki okul günü pazartesidir', async ({ page }) => {
    await bugunAc(page, '2026-09-25T17:00')
    const yarin = page.locator('.today-tomorrow')
    await expect(yarin).toContainText('PAZARTESİ')
    await expect(yarin).not.toContainText('YARIN')
    await expect(yarin).toContainText('İlk ders 08:00 · Türkçe')
  })

  test('odak kipinde yarın kartı gizli', async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem('tedy-focus-mode', 'true'))
    await bugunAc(page, '2026-09-24T16:40')
    await expect(page.locator('.today-tomorrow')).toBeHidden()
  })
})

/** /api/homework that remembers "Yaptım", like the real endpoint does. */
async function odevSunucusu(page: Page, cevap: { status: number } = { status: 200 }) {
  const gelen: Record<string, unknown>[] = []
  let yapildi = false
  await page.route('**/api/homework', (r: Route) => r.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({
      ...HOMEWORK,
      homework: HOMEWORK.homework.map(h =>
        yapildi && h === MATEMATIK ? { ...h, student_marked_done: true } : h),
    }),
  }))
  await page.route('**/api/homework/mark-done', async (r: Route) => {
    gelen.push(JSON.parse(r.request().postData() || '{}'))
    if (cevap.status === 200) yapildi = true
    await r.fulfill({ status: cevap.status, contentType: 'application/json',
      body: JSON.stringify(cevap.status === 200 ? { ok: true } : { error: 'x' }) })
  })
  return gelen
}

test.describe('C3 — Bugün\'den Yaptım', () => {
  test('kutu açıkken Yaptım işi işaretler, kart sıradakine geçer', async ({ page }) => {
    const gelen = await odevSunucusu(page)
    await bugunAc(page, '2026-09-24T16:40', { homework: null })

    const kart = page.locator('.next-thing')
    await kart.getByRole('button', { name: 'Başla' }).click()
    await kart.getByRole('button', { name: 'Yaptım' }).click()

    // The same record İşler would have sent.
    await expect.poll(() => gelen.length).toBe(1)
    expect(gelen[0]['Ödev Başlığı']).toBe('2. HAFTA MATEMATİK HAFTA İÇİ ÖDEVİ')
    expect(gelen[0]['Ödev Son Teslim Tarihi']).toBe('25.09.2026 12:00')

    // The loop closes here: the next work steps up, the box is gone, and the
    // page says what it recorded (İ9 — "Yaptım" answers with "yaptın").
    await expect(kart).toContainText('Fransızca')
    await expect(kart.locator('.next-thing__eyebrow')).not.toContainText('BAŞLADIN')
    await expect(page.locator('.today-done-note')).toContainText('Matematik')
  })

  test('süre dolduğunda da Yaptım var', async ({ page }) => {
    await odevSunucusu(page)
    await bugunAc(page, '2026-09-24T16:40', { homework: null })
    await page.locator('.next-thing').getByRole('button', { name: 'Başla' }).click()
    await page.clock.setFixedTime(new Date('2026-09-24T16:51:00'))
    await page.reload()
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.next-thing').getByRole('button', { name: 'Yaptım' })).toBeVisible()
  })

  test('kaydedilemezse söyler, kutu açık kalır', async ({ page }) => {
    await odevSunucusu(page, { status: 500 })
    await bugunAc(page, '2026-09-24T16:40', { homework: null })

    const kart = page.locator('.next-thing')
    await kart.getByRole('button', { name: 'Başla' }).click()
    await kart.getByRole('button', { name: 'Yaptım' }).click()

    // D3: a failure says what happened and what to do, and loses nothing.
    await expect(kart).toContainText('Kaydedilemedi')
    await expect(kart.locator('.next-thing__eyebrow')).toContainText('BAŞLADIN')
    await expect(kart).toContainText('Matematik')
  })

  test('kart dersi, altındaki liste ve İşler ile aynı adla anar', async ({ page }) => {
    // Measured 2026-09-24 on the live data: the card said "İkinci Yabancı Dil
    // (Fransızca)" and the list one line below it said "Fransızca" (İ9).
    await bugunAc(page, '2026-09-24T19:30', { homework: { summary: '', homework: [
      HW('İkinci Yabancı Dil (Fransızca)', 'S1 Les verbes', '28.09.2026 08:55', '',
        { normalized_course: 'Fransızca' }),
    ] } })
    const kart = page.locator('.next-thing')
    await expect(kart).toContainText('Fransızca — S1 Les verbes')
    await expect(kart).not.toContainText('İkinci Yabancı Dil')
  })

  test('öğrencinin yaptım dediği iş sıradaki iş olarak gösterilmez', async ({ page }) => {
    // Live, 2026-09-22 17:26: Işık marked the week's Matematik homework done,
    // and for two days Bugün went on offering "Başla" on it.
    // İşler already moves these to "Yapılan"; Bugün kept naming them as the
    // next thing, because it only looked at the teacher's status.
    await bugunAc(page, '2026-09-24T16:40', { homework: { summary: '', homework: [
      { ...MATEMATIK, student_marked_done: true },
      HW('Fransızca', 'S1 Les verbes', '28.09.2026 08:55'),
    ] } })
    const kart = page.locator('.next-thing')
    await expect(kart).toContainText('Fransızca')
    await expect(kart).not.toContainText('Matematik')
  })
})
