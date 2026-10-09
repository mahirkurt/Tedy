import { test, expect } from '@playwright/test'
import { PAYLOAD, asistanAc, cevapla, sor, sse, soruAlani } from './_asistan-carbon'

test('akış tüketilir: araç adımı görünür, cevap gelir, /chat çağrılmaz', async ({ page }) => {
  const istekler = await cevapla(page, PAYLOAD({ answer: 'Kesir bir bütünün parçasıdır.' }),
    [['tool_start', { name: 'kazanim_ara' }], ['tool_end', { name: 'kazanim_ara', ok: true, ozet: 'M.7.1.1' }]])
  let klasik = 0
  page.on('request', r => { if (r.url().endsWith('/api/assistant/chat')) klasik += 1 })
  await asistanAc(page)
  await sor(page, 'Kesir nedir?')
  await expect(page.getByText('Kesir bir bütünün parçasıdır.', { exact: true })).toBeVisible()
  // Carbon'un adım bileşeni (reasoning) akış sürerken açıktır, cevap gelince katlanır; "Adımları göster" açar.
  await page.getByRole('button', { name: 'Adımları göster' }).click()
  await expect(page.getByText('MEB kazanımları aranıyor', { exact: true }).filter({ visible: true }).first()).toBeVisible()
  await expect(page.getByText('M.7.1.1', { exact: true }).filter({ visible: true }).first()).toBeVisible()
  expect(klasik).toBe(0)
  expect(istekler[0]).toMatchObject({ ogretmen: 'genel' })
})

test('cevapsız kapanan akış /chat yedeğine düşer, yarım taslak kalmaz', async ({ page }) => {
  await page.route('**/api/assistant/stream', r => r.fulfill({ status: 200, contentType: 'text/event-stream',
    body: sse(['answer_delta', { text: 'YARIM TASLAK' }]) }))
  await page.route('**/api/assistant/chat', r => r.fulfill({ json: PAYLOAD({ answer: 'Yedekten gelen cevap.' }) }))
  await asistanAc(page)
  await sor(page, 'Soru')
  await expect(page.getByText('Yedekten gelen cevap.', { exact: true })).toBeVisible()
  await expect(page.getByText('YARIM TASLAK', { exact: true })).toHaveCount(0)
})

test('answer_reset sonrası ön metin cevap sanılmaz; denetimli son metin taslağın yerine geçer', async ({ page }) => {
  await cevapla(page, PAYLOAD({ answer: 'Denetlenmiş son metin.' }),
    [['answer_delta', { text: 'Önce müfredata bakayım.' }], ['answer_reset', {}], ['answer_delta', { text: 'Taslak metin' }]])
  await asistanAc(page)
  await sor(page, 'Soru')
  await expect(page.getByText('Denetlenmiş son metin.', { exact: true })).toBeVisible()
  await expect(page.getByText('Önce müfredata bakayım.', { exact: true })).toHaveCount(0)
  await expect(page.getByText('Taslak metin', { exact: true })).toHaveCount(0)
})

test('iki uç da 401: okura oturum cümlesi ve Tekrar dene; tekrar aynı gövdeyi yollar', async ({ page }) => {
  let n = 0
  const govdeler: unknown[] = []
  await page.route('**/api/assistant/stream', r => r.fulfill({ status: 401, json: { error: 'session_required' } }))
  await page.route('**/api/assistant/chat', async r => {
    govdeler.push(r.request().postDataJSON()); n += 1
    await r.fulfill(n === 1 ? { status: 401, json: { error: 'session_required' } } : { json: PAYLOAD({ answer: 'İkinci denemede geldi.' }) })
  })
  await asistanAc(page)
  await sor(page, 'Soru')
  await expect(page.getByText('Oturumun sona ermiş; sayfayı yenileyip yeniden giriş yap.', { exact: true })).toBeVisible()
  await expect(page.getByText(/HTTP 401|session_required/)).toHaveCount(0)
  await page.getByRole('button', { name: 'Tekrar dene' }).click()
  await expect(page.getByText('İkinci denemede geldi.', { exact: true })).toBeVisible()
  expect(govdeler[1]).toEqual(govdeler[0])
})

test('durdur isteği keser, hata kartı çıkmaz', async ({ page }) => {
  await page.route('**/api/assistant/stream', () => { /* hiç yanıtlanmaz */ })
  await page.route('**/api/assistant/chat', () => { /* hiç yanıtlanmaz */ })
  await asistanAc(page)
  await sor(page, 'Uzun soru')
  await page.getByRole('button', { name: 'Yanıtı durdur' }).click()
  await expect(page.getByText('Asistan yanıtı alınamadı.', { exact: true })).toHaveCount(0)
  await expect(soruAlani(page)).toBeEditable()
})

test('öğrenciye sen, aileye siz: karşılama ve hızlı sorular', async ({ page }) => {
  await asistanAc(page)
  await expect(page.getByText(/size yardımcı olabilirim/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Işık bugün neye öncelik vermeli?' })).toBeVisible()
})

test('cevaptaki ve kutudaki ham HTML çalışmaz (XSS)', async ({ page }) => {
  await cevapla(page, PAYLOAD({ answer: 'Metin <img src=x onerror="window.__xss=1"> son.\n\n:::kavram\n<img src=y onerror="window.__xss2=1">\n:::' }))
  await asistanAc(page)
  await sor(page, 'Soru')
  await expect(page.locator('p', { hasText: /son\.$/ }).first()).toBeVisible()
  await page.waitForTimeout(500)
  expect(await page.evaluate(() => (window as unknown as { __xss?: number; __xss2?: number }).__xss ?? (window as unknown as { __xss2?: number }).__xss2)).toBeUndefined()
})

test('atıflı cevaptaki ham HTML de çalışmaz (Carbon atıflı cevapta temizleyiciyi kapatıyor)', async ({ page }) => {
  await cevapla(page, PAYLOAD({
    answer: 'Metin <img src=x onerror="window.__xss=1"> son [S1].',
    citations: [{ id: 'S1', kind: 'mufredat', label: 'Kesirler', locator: {}, snippet: 'Eş <img src=z onerror="window.__xss3=1"> parça', confidence: 0.9 }],
  }))
  await asistanAc(page)
  await sor(page, 'Soru')
  await expect(page.getByRole('button', { name: 'Kaynaklar', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Kaynaklar', exact: true }).click()
  await page.waitForTimeout(500)
  expect(await page.evaluate(() => { const w = window as unknown as Record<string, number | undefined>; return [w.__xss, w.__xss3] })).toEqual([undefined, undefined])
})

test('giriş satırındaki mikrofon ve plan düğmeleri yan yana durur (eski giriş alanı gibi)', async ({ page }) => {
  await page.addInitScript(() => Object.assign(window, { webkitSpeechRecognition: class { start() {} stop() {} abort() {} } }))
  await asistanAc(page)
  const [mik, plan] = await Promise.all([
    page.getByRole('button', { name: 'Sesle sor', exact: true }).boundingBox(),
    page.getByRole('button', { name: 'Çalışma Planı', exact: true }).boundingBox(),
  ])
  expect(Math.abs(mik!.y - plan!.y)).toBeLessThan(2)
  expect(plan!.x).toBeGreaterThan(mik!.x)
})

test('zaman 24 saat, ad TEDY Asistan, tablo filtre kutusuz kendi tablomuz', async ({ page }) => {
  await cevapla(page, PAYLOAD({ answer: '| a | b |\n|---|---|\n| 1 | 2 |' }))
  await asistanAc(page)
  await sor(page, 'Tablo')
  await expect(page.locator('table.ac-md__table')).toBeVisible()
  await expect(page.getByPlaceholder(/Filter table|Tabloyu süz/).filter({ visible: true })).toHaveCount(0)
  await expect(page.getByText(/\b(AM|PM)\b/)).toHaveCount(0)
  await expect(page.getByText('watsonx', { exact: true })).toHaveCount(0)
})

test('adımlar gösterilmişken akış da /chat da düşerse mesaj hata kartıyla biter, yarım kalmaz', async ({ page }) => {
  await page.route('**/api/assistant/stream', r => r.fulfill({ status: 200, contentType: 'text/event-stream',
    body: sse(['tool_start', { name: 'kazanim_ara' }]) }))
  await page.route('**/api/assistant/chat', r => r.fulfill({ status: 500, json: { error: 'x' } }))
  await asistanAc(page)
  await sor(page, 'Soru')
  await expect(page.getByRole('alert').filter({ hasText: 'Asistan yanıtı alınamadı.' }).first()).toBeVisible()
  await expect(page.getByRole('button', { name: 'Yanıtı durdur' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Tekrar dene' })).toBeVisible()
  await expect(soruAlani(page)).toBeEditable()
})

test('iki soru üst üste düşerse her kartın Tekrar dene düğmesi kendi sorusunu yeniden yollar', async ({ page }) => {
  const govdeler: { messages: { content: string }[] }[] = []
  let n = 0
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/assistant/chat', async r => {
    govdeler.push(r.request().postDataJSON()); n += 1
    await r.fulfill(n <= 2 ? { status: 500, json: { error: 'x' } } : { json: PAYLOAD({ answer: 'Şimdi geldi.' }) })
  })
  await asistanAc(page)
  await sor(page, 'Birinci soru')
  await expect(page.getByRole('button', { name: 'Tekrar dene' })).toHaveCount(1)
  await sor(page, 'İkinci soru')
  await expect(page.getByRole('button', { name: 'Tekrar dene' })).toHaveCount(2)
  await page.getByRole('button', { name: 'Tekrar dene' }).first().click()
  await expect(page.getByText('Şimdi geldi.', { exact: true })).toBeVisible()
  expect(govdeler[2].messages.at(-1)?.content).toBe('Birinci soru')
  await expect(page.getByRole('button', { name: 'Tekrar dene' })).toHaveCount(1)   // ikincinin kartı duruyor
})

test('ilk soruda oturum düşerse sohbet açılamaz: oturum cümlesi ve aynı soruyu yollayan Tekrar dene', async ({ page }) => {
  let acilis = 0
  const istekler = await cevapla(page, PAYLOAD({ answer: 'Oturum geri geldi.' }))
  await asistanAc(page)
  await page.route('**/api/assistant/sohbetler', async r => {
    if (r.request().method() !== 'POST') return r.fulfill({ json: { sohbetler: [] } })
    acilis += 1
    await r.fulfill(acilis === 1 ? { status: 401, json: { error: 'session_required' } } : { json: { id: 'cd'.repeat(16), ogretmen: 'genel', baslik: '' } })
  })
  await sor(page, 'Merhaba')
  await expect(page.getByText('Oturumun sona ermiş; sayfayı yenileyip yeniden giriş yap.', { exact: true })).toBeVisible()
  await expect(page.getByText('Sohbet kaydedilemedi.', { exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: 'Tekrar dene' }).click()
  await expect(page.getByText('Oturum geri geldi.', { exact: true })).toBeVisible()
  expect(istekler.at(-1)).toMatchObject({ sohbet_id: 'cd'.repeat(16), messages: [{ role: 'user', content: 'Merhaba' }] })
  await expect(page.getByText('Merhaba', { exact: true }).filter({ visible: true })).toHaveCount(1)   // soru balonu çoğalmaz
})

test('Tekrar dene ile başlayan istek durdur düğmesiyle kesilir', async ({ page }) => {
  let n = 0
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/assistant/chat', async r => {
    n += 1
    if (n === 1) return r.fulfill({ status: 500, json: { error: 'x' } })
    // Tekrar: hiç yanıtlanmaz, okur durdurur.
  })
  await asistanAc(page)
  await sor(page, 'Soru')
  await page.getByRole('button', { name: 'Tekrar dene' }).click()
  await page.getByRole('button', { name: 'Yanıtı durdur' }).click()
  await expect(page.getByRole('button', { name: 'Yanıtı durdur' })).toHaveCount(0)
  // Görünenler: ilk hatanın ekran okuyucu duyurusu gizli bölgede kalır.
  await expect(page.getByText('Asistan yanıtı alınamadı.', { exact: true }).filter({ visible: true })).toHaveCount(0)
  await expect(page.getByText('Yeniden deneniyor…', { exact: true }).filter({ visible: true })).toHaveCount(0)
  await expect(soruAlani(page)).toBeEditable()
})

test('Çalışma Planı düğmesi giriş boşken devre dışı, yazınca etkin (eski giriş alanı gibi)', async ({ page }) => {
  await asistanAc(page)
  const plan = page.getByRole('button', { name: 'Çalışma Planı', exact: true })
  await expect(plan).toBeDisabled()
  await soruAlani(page).fill('Haftalık plan')
  await expect(plan).toBeEnabled()
  await soruAlani(page).fill('   ')
  await expect(plan).toBeDisabled()
})
