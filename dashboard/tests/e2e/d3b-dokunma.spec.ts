import { test, expect } from '@playwright/test'
import type { Locator } from '@playwright/test'
import { mock } from './_audit-fixtures'
import { GORSEL } from './_gorsel-fixtures'
import { sabitAc } from './_gorsel-yardim'
import { bugunAc, HOMEWORK, HW, SINAV } from './_bugun-fixtures'

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

// Since the 2026-10-10 redesign every control on Bugün meets the gate, not
// only the arrows (talimatname B8): the rows, "+N iş daha", the fold, the
// deadline row, "Başla" and "Bugüne dön".
test('every Bugün control is at least 44px on a phone', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  // This file runs the browser in Istanbul time, so the moment carries its offset.
  await bugunAc(page, '2026-09-24T16:40:00+03:00', { homework: { summary: '', homework: [
    ...HOMEWORK.homework,
    HW('Türkçe', 'Okuma günlüğü', '24.09.2026 18:00'),
    HW('Müzik', 'Nota çalışması', '30.09.2026 12:00'),
  ] }, exams: { exams: [{
    ...SINAV('ktt', 'Matematik KTT', '2026-09-29T09:00:00'), course: 'Matematik', konular: ['Oran'],
    kaynaklar: [{ tur: 'ders_karti', etiket: 'Matematik ders içeriği', alinti: 'KTT', baglanti: '/dersler' }],
  }], stats: { upcoming: 1, past: 0, averageGrade: null } } })
  await enAz(page.locator('.next-thing').getByRole('button', { name: 'Başla' }))
  await enAz(page.locator('.today-also li button'))
  await enAz(page.locator('.today-also').getByRole('link', { name: /iş daha/ }))
  await enAz(page.locator('.today-past-fold'))
  await enAz(page.locator('.today-tl').getByRole('link'))
  // C21: the exam preview's row and its links (source, alerts) are tapped too.
  await enAz(page.locator('.sinav-onizleme li button'))
  await enAz(page.locator('.sinav-onizleme').getByRole('link'))
  await page.getByRole('button', { name: 'Sonraki gün', exact: true }).click()
  await enAz(page.getByRole('button', { name: 'Bugüne dön', exact: true }))
})

test('Asistan prompt chips are at least 44px on a phone', async ({ page }) => {
  await sabitAc(page, '/asistan', 390, 844)
  // Carbon AI asistanı: hızlı sorular giriş üstündeki karşılamada (Karsilama.tsx).
  await enAz(page.locator('.asistan__hizli-sorular button'))
})

// Asistan yenilemesi (2026-10-10): every TEDY control on the assistant, not only the prompts — the teacher
// selector, the input row's actions and the history panel's rows and actions.
test('every Asistan control TEDY draws is at least 44px on a phone', async ({ page }) => {
  await sabitAc(page, '/asistan', 390, 844)
  await expect(page.getByRole('textbox', { name: /^Sorunu(zu)? yaz/ })).toBeVisible({ timeout: 15000 })
  await enAz(page.locator('#asistan-ogretmen button'))
  // B79: Carbon AI Chat'in kendi denetimleri de (gölge kök; carbonOnarimi.ts dokunma kuralı) ve AI etiketi.
  for (const ad of ['Gönder', 'Sohbetler', 'Sohbeti yeniden başlat', 'AI Yapay zekâ hakkında bilgi']) {
    await enAz(page.getByRole('button', { name: ad, exact: true }).first())
  }
  await enAz(page.locator('.asistan__giris-eylemleri button'))
  await page.getByRole('button', { name: 'Sohbetler', exact: true }).first().click()
  await expect(page.getByRole('heading', { name: 'Sohbetler', exact: true })).toBeVisible()
  await enAz(page.locator('.asistan-gecmis button'))
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

test('İşler section headers are at least 44px on a phone', async ({ page }) => {
  await sabitAc(page, '/isler', 390, 844)
  await enAz(page.getByRole('button', { name: /^Ayrıca/ }))
})

test('Dersler shows a short lesson note once', async ({ page }) => {
  await sabitAc(page, '/dersler', 390, 844)
  const note = 'Kesirlerde toplama ve çıkarma işlendi. Payda eşitleme üzerinde duruldu.'
  await expect(page.getByText(note, { exact: true })).toHaveCount(1)
})

test('a longer Dersler note keeps a 44px heading and one body', async ({ page }) => {
  const uzun = 'Kuvvet ve hareket ünitesine giriş yapıldı. '.repeat(4)
  await mock(page, {
    ...GORSEL,
    content: { 'Fen Bilimleri': { text: uzun, cards: [], items: [] } },
  })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/dersler')
  await page.waitForLoadState('networkidle')
  await enAz(page.locator('.course-content .cds--accordion__heading:visible'))
  await expect(page.locator('.course-content-text').filter({ hasText: uzun.slice(0, 40) })).toHaveCount(1)
})
