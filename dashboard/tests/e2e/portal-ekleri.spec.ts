import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { bugunAc, HW } from './_bugun-fixtures'

// Plan docs/superpowers/plans/2026-09-28-portal-ekleri.md, Görev 11: an
// attachment opens TEDY's copy, keeps a secondary "Kaynağında aç" link to the
// original, and says so when there is no copy. Hosts and ids are invented.

const json = (b: unknown) => ({
  status: 200, contentType: 'application/json', body: JSON.stringify(b),
})

const INDIRILDI = {
  name: 'Sayfa 12-13.pdf',
  url: 'https://ornekokul-my.sharepoint.com/:b:/g/personal/ogretmen_ornekokul_k12_tr/EaBcDeF?e=AbC123',
  id: 'a1b2c3d4e5f60718', tedyUrl: '/api/ekler/a1b2c3d4e5f60718', status: 'indirildi',
}
const INDIRILEMEDI = {
  name: 'Kitap sayfaları',
  url: 'https://ornekokul-my.sharepoint.com/:b:/g/personal/ogretmen_ornekokul_k12_tr/EzYxWvU?e=XyZ789',
  id: '0f1e2d3c4b5a6978', tedyUrl: null, status: 'erisilemedi',
  reason: 'kaynak giriş istiyor; paylaşım herkese açık değil',
}
const BAGLANTI = {
  name: 'Konu videosu', url: 'https://www.youtube.com/watch?v=ornekvideo01',
  id: null, tedyUrl: null, status: 'baglanti',
}
const ODEV = HW('Sosyal Bilgiler', 'Kitap okuma ödevi', '25.09.2026 12:00', 'Sayfa 12-13 okunacak.', {
  detail: { description: 'Sayfa 12-13 okunacak.', attachments: [INDIRILDI, INDIRILEMEDI, BAGLANTI] },
})

async function islerModali(page: Page) {
  await page.route('**/api/homework', r => r.fulfill(json({ summary: '', homework: [ODEV] })))
  await page.route('**/api/enrichment', r => r.fulfill(json({})))
  await page.route('**/api/exams', r => r.fulfill(json({ exams: [] })))
  await page.route('**/api/health', r => r.fulfill(json({
    timestamp: '', success: true, scrape_errors: [], duration_seconds: 1,
  })))
  await page.clock.setFixedTime(new Date('2026-09-24T18:00:00'))
  await page.goto('/isler')
  await page.locator('.homework-item').first().waitFor()
  await page.locator('.homework-item').first().click()
  const ekler = page.locator('.homework-modal__attachments')
  await ekler.waitFor()
  return ekler
}

test.describe('Portal ekleri', () => {
  test('İşler: indirilen ek TEDY kopyasını açar, kaynağı ikincil kalır', async ({ page }) => {
    const ekler = await islerModali(page)
    await expect(ekler.getByRole('link', { name: 'Sayfa 12-13.pdf', exact: true }))
      .toHaveAttribute('href', '/api/ekler/a1b2c3d4e5f60718')
    await expect(ekler.getByRole('link', { name: 'Kaynağında aç: Sayfa 12-13.pdf' }))
      .toHaveAttribute('href', INDIRILDI.url)
  })

  test('İşler: indirilemeyen ek bunu söyler; düz bağlantı uyarı taşımaz', async ({ page }) => {
    const ekler = await islerModali(page)
    await expect(ekler.getByRole('link', { name: 'Kitap sayfaları', exact: true }))
      .toHaveAttribute('href', INDIRILEMEDI.url)
    await expect(ekler.locator('li', { hasText: 'Kitap sayfaları' }))
      .toContainText('İndirilemedi — kaynağında aç')
    const video = ekler.locator('li', { hasText: 'Konu videosu' })
    await expect(video.getByRole('link', { name: 'Konu videosu', exact: true }))
      .toHaveAttribute('href', BAGLANTI.url)
    await expect(video).not.toContainText('İndirilemedi')
  })

  test('İşler: ek listesi erişilebilir', async ({ page }) => {
    await islerModali(page)
    const sonuc = await new AxeBuilder({ page })
      .include('.homework-modal__attachments')
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
      .analyze()
    expect(sonuc.violations).toEqual([])
  })

  test('Bugün: Başla kutusunda aynı ek bağlantısı', async ({ page }) => {
    await bugunAc(page, '2026-09-24T16:40', { homework: { summary: '', homework: [ODEV] } })
    const kart = page.locator('.next-thing')
    await kart.getByRole('button', { name: 'Başla' }).click()
    await expect(kart.getByRole('link', { name: 'Sayfa 12-13.pdf', exact: true }))
      .toHaveAttribute('href', '/api/ekler/a1b2c3d4e5f60718')
    await expect(kart).toContainText('İndirilemedi — kaynağında aç')
  })

  test('Duyurular: ek TEDY kopyasını açar, indirilemeyen bunu söyler', async ({ page }) => {
    await page.route('**/api/announcements', r => r.fulfill(json({
      announcements: [{
        'e-Posta Başlık': 'Kitap okuma duyurusu',
        'Ekleri': 'Sayfa 12-13.pdf',
        'Yayın Tarihi': '22.09.2026',
        'e-Posta İçerik': 'Sayfa 12-13 okunacak.',
        ekler: [INDIRILDI, INDIRILEMEDI, BAGLANTI],
      }],
    })))
    await page.route('**/api/health', r => r.fulfill(json({
      timestamp: '', success: true, scrape_errors: [], duration_seconds: 1,
    })))
    await page.route('**/api/private-lessons', r => r.fulfill(json({ lessons: [] })))
    await page.goto('/duyurular')
    await page.getByRole('button', { name: 'Kitap okuma duyurusu' }).click()
    const ekler = page.locator('.announcements-detail__ekler')
    await expect(ekler.getByRole('link', { name: 'Sayfa 12-13.pdf', exact: true }))
      .toHaveAttribute('href', '/api/ekler/a1b2c3d4e5f60718')
    await expect(ekler.getByRole('link', { name: 'Kaynağında aç: Sayfa 12-13.pdf' }))
      .toHaveAttribute('href', INDIRILDI.url)
    await expect(ekler.locator('li', { hasText: 'Kitap sayfaları' }))
      .toContainText('İndirilemedi — kaynağında aç')
    await expect(ekler.locator('li', { hasText: 'Konu videosu' })).not.toContainText('İndirilemedi')
  })
})
