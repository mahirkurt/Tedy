import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

// Arşivleme (2026-10-24): yeni sürüm yayınlanınca eski sürümler arşivlenir. Arşivlenmiş bir sürümün bileti
// 410 {arsivlendi: true, guncel} döner (src/dashboard_api.py _module_archived_response); sayfa güncel sürüme
// geçmişte yerini alarak (replace) yönlenir, güncel sürüm yoksa "Bu modül artık yayında değil." der.
// Ağ yok: pano uçları ve modül çerçevesi page.route ile verilir.

const json = (b: unknown, status = 200) => ({ status, contentType: 'application/json', body: JSON.stringify(b) })
const ACIKLAMA = {
  baslik: 'Maddenin Hâlleri', ders: 'Fen Bilimleri', sinif: '5. Sınıf', kazanimlar: ['FB.5.4.1.1'],
  kitap: { ad: 'Fen Bilimleri 5', sayfalar: '112-120' }, iddia_durumu: 'kayit_yok', iddialar: [],
  medya: { yapay_zeka: 0, ders_kitabi: 0, fotograf_arsivi: 0 },
}
const KART = {
  slug: 'fen5-su', version: 1, title: 'Maddenin Hâlleri', subject: 'Fen Bilimleri', gradeLevel: '5. Sınıf',
  mode: 'QUIZ', outcomes: ['FB.5.4.1.1'], ted_link: null, created_at: '2026-09-14T10:00:00+00:00',
  gates: { pass: 18, warn: 0, fail: 0 },
}

async function arsiv(page: Page, guncel: number | null) {
  const biletler: string[] = []
  // Bayat bir liste (sekme açık kalmış): hâlâ v1'e bağlantı veriyor.
  await page.route('**/api/modules/agac', r => r.fulfill(json({ hazir: [KART], dersler: [], kapsam: {}, hata: null })))
  await page.route(/\/api\/modules\/fen5-su\/v\d+\/(ticket|aciklama)$/, r => {
    const [, surum, uc] = /\/v(\d+)\/(ticket|aciklama)$/.exec(r.request().url())!
    if (uc === 'ticket') biletler.push(`v${surum}`)
    if (surum === '1') return r.fulfill(json({ arsivlendi: true, guncel }, 410))
    if (uc === 'aciklama') return r.fulfill(json(ACIKLAMA))
    return r.fulfill(json({ url: `https://modul.tedy.online/m/fen5-su/v${surum}?t=${'a'.repeat(64)}&e=1&u=${'b'.repeat(32)}`, exp: 1 }))
  })
  await page.route('**/api/modules/fen5-su/progress**', r => r.fulfill(json({ state: { answers: [], done: [], xp: 0 } })))
  await page.route('https://modul.tedy.online/**', r => r.fulfill({
    status: 200, contentType: 'text/html; charset=utf-8', body: '<!doctype html><html lang="tr"><title>v2</title><p>Sürüm 2</p>',
  }))
  return biletler
}

test('arşivlenmiş sürümün adresi güncel sürüme geçmişte yerini alarak yönlenir', async ({ page }) => {
  const biletler = await arsiv(page, 2)
  await page.goto('/moduller')
  await page.getByRole('link', { name: 'Maddenin Hâlleri', exact: true }).click()
  await expect(page).toHaveURL(/\/moduller\/fen5-su\/v2$/)
  await expect(page.locator('iframe.module-frame')).toHaveAttribute('src', /^https:\/\/modul\.tedy\.online\/m\/fen5-su\/v2\?/)
  await expect(page.frameLocator('iframe.module-frame').getByText('Sürüm 2')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Maddenin Hâlleri' })).toBeVisible()
  expect(biletler).toEqual(['v1', 'v2'])
  // Hata cümlesi çizilmedi; yönlenme sessiz bir başarısızlık değil, güncel modülün kendisi.
  await expect(page.locator('.module-viewer .cds--inline-notification')).toHaveCount(0)
  // replace: Geri, arşivlenmiş adrese değil, geldiği listeye döner.
  await page.goBack()
  await expect(page).toHaveURL(/\/moduller$/)
})

test('doğrudan açılan arşiv adresi de güncel sürüme yönlenir', async ({ page }) => {
  const biletler = await arsiv(page, 2)
  await page.goto('/moduller/fen5-su/v1')
  await expect(page).toHaveURL(/\/moduller\/fen5-su\/v2$/)
  await expect(page.locator('iframe.module-frame')).toHaveAttribute('src', /\/m\/fen5-su\/v2\?/)
  expect(biletler).toEqual(['v1', 'v2'])
})

test('güncel sürüm yoksa sayfa modülün artık yayında olmadığını söyler', async ({ page }) => {
  const biletler = await arsiv(page, null)
  await page.goto('/moduller/fen5-su/v1')
  const bilgi = page.locator('.module-viewer .cds--inline-notification--info')
  await expect(bilgi).toContainText('Bu modül artık yayında değil.')
  await expect(bilgi).toHaveAttribute('role', 'status')
  await expect(page).toHaveURL(/\/moduller\/fen5-su\/v1$/)
  // Bir bilgi, hata değil; çerçeve de yok. Bilgi çizildikten sonra bakılır (boş sayfanın yokluğu sayılmaz).
  await expect(page.locator('.module-viewer [role="alert"]')).toHaveCount(0)
  await expect(page.locator('iframe.module-frame')).toHaveCount(0)
  expect(biletler).toEqual(['v1'])
  const { violations } = await new AxeBuilder({ page }).include('.module-page').analyze()
  expect(violations).toEqual([])
})
