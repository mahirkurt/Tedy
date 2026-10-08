import { test, expect } from '@playwright/test'
import { PAYLOAD, cevapla, gonderDugmesi } from './_asistan-carbon'
import { mock, FULL } from './_audit-fixtures'

const baslatici = (page: import('@playwright/test').Page) => page.getByRole('button', { name: 'Sohbet penceresini aç' })

test('İşler sayfasında başlatıcı, çip ve sayfa soruları; istek sayfa bağlamını taşır, çip bir kez', async ({ page }) => {
  await mock(page, FULL)
  const istekler = await cevapla(page, PAYLOAD({ answer: 'Önce matematikten başla.' }))
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/isler')
  await baslatici(page).click()
  await expect(page.getByText('Bu sayfa: İşler', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Işık bugün hangi işten başlamalı?' }).click()
  await expect(page.getByText('Önce matematikten başla.', { exact: true })).toBeVisible()
  expect(istekler[0]).toMatchObject({ sayfa: { ad: 'isler' } })
  await expect(page.getByText('Bu sayfa: İşler', { exact: true })).toHaveCount(0)
  await page.getByRole('textbox', { name: /^Sorunu(zu)? yaz/ }).fill('Başka soru')
  await gonderDugmesi(page).click()
  await expect.poll(() => istekler.length).toBe(2)
  expect(istekler[1]).not.toHaveProperty('sayfa')
})

test('çip kaldırılınca istek bağlamsız, sorular mod sorularına döner', async ({ page }) => {
  await mock(page, FULL)
  const istekler = await cevapla(page, PAYLOAD())
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/takvim')
  await baslatici(page).click()
  await page.getByRole('button', { name: 'Bağlamı kaldır: Takvim' }).click()
  await expect(page.getByRole('button', { name: 'Işık bugün neye öncelik vermeli?' })).toBeVisible()
  await page.getByRole('textbox', { name: /^Sorunu(zu)? yaz/ }).fill('Soru')
  await gonderDugmesi(page).click()
  await expect.poll(() => istekler.length).toBe(1)
  expect(istekler[0]).not.toHaveProperty('sayfa')
})

test('başlatıcının gizli olduğu yerler: asistan, odak modu, telefon', async ({ page }) => {
  await mock(page, FULL)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/asistan')
  await expect(baslatici(page)).toHaveCount(0)
  await page.goto('/isler')
  await expect(baslatici(page)).toBeVisible()
  await page.evaluate(() => localStorage.setItem('tedy-focus-mode', 'true'))
  await page.reload()
  await expect(baslatici(page)).toHaveCount(0)
  await page.evaluate(() => localStorage.removeItem('tedy-focus-mode'))
  await page.setViewportSize({ width: 390, height: 844 })
  await page.reload()
  await expect(baslatici(page)).toHaveCount(0)
})

test('telefonda Asistan sekmesi sayfa bağlamını taşır; bilinmeyen ad sessizce yok sayılır', async ({ page }) => {
  await mock(page, FULL)
  const istekler = await cevapla(page, PAYLOAD())
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/notlar')
  await page.getByRole('navigation', { name: 'Ana gezinme' }).getByRole('link', { name: 'Asistan' }).click()
  await expect(page).toHaveURL(/\/asistan\?sayfa=notlar$/)
  await expect(page.getByText('Bu sayfa: Notlar', { exact: true })).toBeVisible()
  await page.goto('/asistan?sayfa=xyz')
  await expect(page.getByText(/Bu sayfa:/)).toHaveCount(0)
  await page.getByRole('textbox', { name: /^Sorunu(zu)? yaz/ }).fill('Soru')
  await page.getByRole('button', { name: 'Gönder', exact: true }).click()
  await expect.poll(() => istekler.length).toBe(1)
  expect(istekler[0]).not.toHaveProperty('sayfa')
})

test('başlatıcıda sorulan soru sayfaya geçince bir kez görünür', async ({ page }) => {
  await mock(page, FULL)
  let kayitli: unknown[] = []
  await page.route('**/api/assistant/sohbetler', r => r.request().method() === 'POST'
    ? r.fulfill({ json: { id: 'ab'.repeat(16), ogretmen: 'genel', baslik: '' } }) : r.fulfill({ json: { sohbetler: [] } }))
  await page.route(`**/api/assistant/sohbetler/${'ab'.repeat(16)}`, r => r.fulfill({ json: {
    sohbet: { id: 'ab'.repeat(16), baslik: 'Tek soru', ogretmen: 'genel' }, mesajlar: kayitli } }))
  await cevapla(page, PAYLOAD({ answer: 'Tek cevap.', mesaj_id: 'c'.repeat(32) }))
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/isler')
  await baslatici(page).click()
  await page.getByRole('textbox', { name: /^Sorunu(zu)? yaz/ }).fill('Tek soru')
  await gonderDugmesi(page).click()
  // exact: Carbon'un aria-live duyurucusu metni biriktirir.
  await expect(page.getByText('Tek cevap.', { exact: true })).toBeVisible()
  kayitli = [
    { id: 'd'.repeat(32), rol: 'user', icerik: 'Tek soru', atiflar_json: '[]', ekler_json: '[]', zaman: '2026-10-08T09:00:00Z' },
    { id: 'c'.repeat(32), rol: 'assistant', icerik: 'Tek cevap.', atiflar_json: '[]', ekler_json: '[]', zaman: '2026-10-08T09:00:02Z' },
  ]
  await page.goto('/asistan')
  // Görünenler: Carbon gizli bir yinelenen mesaj kopyası tutar (bkz. sonCevap).
  await expect(page.getByText('Tek cevap.', { exact: true }).filter({ visible: true })).toHaveCount(1)
  await expect(page.getByText('Tek soru', { exact: true }).filter({ visible: true })).toHaveCount(1)   // liste bu testte boş: yalnız mesaj balonu
})

test('Tam ekran paneli pencereyi kaplatır, Küçült geri alır', async ({ page }) => {
  await mock(page, FULL)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/isler')
  await baslatici(page).click()
  // Carbon'un yüzen penceresi ölçülür (gölge kökte); sarmalayıcı kap akıştaki tam genişlikte bir bloktur.
  const pencere = page.locator('.asistan-paneli .cds-aichat--widget')
  await expect.poll(async () => (await pencere.boundingBox())?.width ?? 0).toBeLessThan(800)
  await page.getByRole('button', { name: 'Tam ekran' }).click()
  await expect.poll(async () => (await pencere.boundingBox())?.width ?? 0).toBeGreaterThan(1400)
  expect((await pencere.boundingBox())!.height).toBeGreaterThan(880)
  await page.getByRole('button', { name: 'Küçült' }).click()
  await expect.poll(async () => (await pencere.boundingBox())?.width ?? 0).toBeLessThan(800)
})

test('başlatıcı düğmesi Bugün’ün ilk yüklemesine Carbon AI Chat getirmez', async ({ page }) => {
  await mock(page, FULL)
  const yuklenen: string[] = []
  page.on('response', r => { if (r.url().includes('/assets/') && r.url().endsWith('.js')) yuklenen.push(r.url()) })
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/')
  await expect(baslatici(page)).toBeVisible()
  const govdeler = await Promise.all(yuklenen.map(u => page.request.get(u).then(r => r.text())))
  expect(govdeler.some(g => g.includes('cds-aichat-container'))).toBe(false)
})

test('açık ödev çipte görünür ve istekte öğe olarak gider; pencere kapanınca çip sayfaya döner', async ({ page }) => {
  // Teslimi gerçek saate göre ileride (FULL'ün tarihleri Eylül'e sabit; saat bu testte donmuyor).
  const ileri = new Date(Date.now() + 3 * 864e5)
  const teslim = `${String(ileri.getDate()).padStart(2, '0')}.${String(ileri.getMonth() + 1).padStart(2, '0')}.${ileri.getFullYear()} 23:59`
  const odev = { ...(FULL.homework as { homework: Record<string, unknown>[] }).homework[0], homework_key: 'mat-kesir',
    'Ödev Son Teslim Tarihi': teslim }
  await mock(page, { ...FULL, homework: { summary: '', homework: [odev] } })
  const istekler = await cevapla(page, PAYLOAD())
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/isler')
  await baslatici(page).click()
  await expect(page.getByText('Bu sayfa: İşler', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Başla', exact: true }).click()
  await expect(page.getByText('Bu sayfa: İşler — Matematik — Kesirlerde toplama — sayfa 165, 1-12 arası', { exact: true })).toBeVisible()
  await page.getByRole('textbox', { name: /^Sorunu(zu)? yaz/ }).fill('Nasıl başlarım?')
  await gonderDugmesi(page).click()
  await expect.poll(() => istekler.length).toBe(1)
  expect(istekler[0]).toMatchObject({ sayfa: { ad: 'isler', oge: { tur: 'odev', id: 'mat-kesir' } } })
})
