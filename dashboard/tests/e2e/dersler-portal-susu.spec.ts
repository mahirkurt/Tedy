import { test, expect } from '@playwright/test'

// Plan 2026-09-28-portal-ekleri, Görev 12: the API already serves course
// content clean (src/portal_susu.py); this proves the page is safe on its own
// if raw data ever reaches it. Invented names — the shape is the real one.

const json = (b: unknown) => ({
  status: 200, contentType: 'application/json', body: JSON.stringify(b),
})

const GENEL_KART = [
  'Okulumuzda Bilim Şenliği Başlıyor',
  'TED Rönesans Koleji | 22.09.2026',
  '  3 Yorum yapıldı!',
  '  Daha fazla oku',
  'Kurgu Öğrenci Bir', '3', 'çok güzel olmuş',
  'Uydurma Öğrenci İki', '0', 'harika bir etkinlik',
  'Yorum Ekle',
].join('\n')
const YALNIZ_YORUM = ['  Daha fazla oku', 'Deneme Öğrenci Üç', '1', 'ben de katılacağım', 'Yorum Ekle'].join('\n')
const SIZINTI = ['Daha fazla oku', 'Yorum Ekle', 'Yorum yapıldı', 'İlk yorum yapan',
  'Kurgu Öğrenci Bir', 'Uydurma Öğrenci İki', 'Deneme Öğrenci Üç',
  'çok güzel olmuş', 'harika bir etkinlik', 'ben de katılacağım']

test('Ders İçerikleri ham portal süsünü ve başka çocukların yorumlarını göstermez', async ({ page }) => {
  await page.route('**/api/schedule', r => r.fulfill(json({
    weeks: [], latest: { week_label: '15-19 Eylül', schedule: { headers: ['Saat', 'Pazartesi'], rows: [['08:30', 'Matematik']] } },
    today: null,
  })))
  await page.route('**/api/content', r => r.fulfill(json({
    Genel: { tab_id: 'tab_genel', text: GENEL_KART, cards: [GENEL_KART, YALNIZ_YORUM], items: [] },
  })))
  await page.route('**/api/content/weeks', r => r.fulfill(json({ weeks: {}, current: '' })))
  await page.route('**/api/health', r => r.fulfill(json({
    timestamp: '', success: true, scrape_errors: [], duration_seconds: 1,
  })))
  await page.goto('/dersler')
  // Prove the school post rendered before asserting what is absent.
  await expect(page.getByText('Okulumuzda Bilim Şenliği Başlıyor').first()).toBeVisible()
  // textContent, not innerText: closed accordion bodies must be clean too.
  const metin = (await page.locator('body').textContent()) ?? ''
  for (const s of SIZINTI) expect(metin, s).not.toContain(s)
})
