import { test, expect } from '@playwright/test'
import { GENEL, DERS, erisilebilirlik, fikstur, hazirlikAc, json } from './_hazirlik'
import { LIVE, mock } from './_audit-fixtures'

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

test('ders sayfası: duyuru aynen, karşılaştırma tablosu, duyurulan sütun, toplam', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri?sinav=1', [[DERS('fen-bilimleri', 1), fikstur('fen-bilimleri-1')]])
  await expect(page.getByRole('heading', { name: 'Fen Bilimleri', level: 2 })).toBeVisible()
  await expect(page.getByText('Okul 2. senaryoyu duyurdu.')).toBeVisible()
  await expect(page.getByText('«Sınav, İstanbul İl MEB tarafından belirlenen 2. senaryoya göre uygulanacaktır.»')).toBeVisible()
  const tablo = page.locator('table.kilavuz-matris')
  await expect(tablo.getByRole('columnheader', { name: 'Senaryo S2 · duyurulan' })).toBeVisible()
  // (d) ekran okuyucu için "Senaryo" öneki görünmez; görünen başlık "S1" kalır.
  await expect(tablo.getByRole('columnheader', { name: 'Senaryo S1', exact: true })).toBeVisible()
  await expect(tablo.getByRole('columnheader', { name: 'Senaryo S1', exact: true }).locator('.cds--visually-hidden')).toHaveText('Senaryo ')
  await expect(tablo.locator('.kilavuz-matris__grup')).toHaveText(['1. Ünite · Uzay Çağı', '2. Ünite · Kuvvet ve Enerjiyi Keşfedelim'])
  await expect(tablo.locator('.kilavuz-matris__toplam td')).toHaveText(['9', '7', '8', '6'])
  const is_ = tablo.getByRole('row').filter({ hasText: 'FB.7.2.1' })
  // Etiket MEB çıktı metninin kendisi: kod ayrı satırda, altında tam metin, "her senaryoda" metnin altında.
  await expect(is_).toContainText('Fiziksel anlamda yapılan işin bağlı olduğu faktörlere ilişkin bilimsel çıkarım yapabilme')
  await expect(is_).not.toContainText('Fiziksel Anlamda İş')
  await expect(is_).toContainText('her senaryoda')
  const kutu = async (k: string) => (await is_.locator(k).first().boundingBox())!
  const [kod, metin, her] = [await kutu('.kilavuz-kod'), await kutu('.kilavuz-matris__metin'), await kutu('.kilavuz-matris__her')]
  expect(metin.y).toBeGreaterThanOrEqual(kod.y + kod.height - 1)
  expect(her.y).toBeGreaterThanOrEqual(metin.y + metin.height - 1)
  // Kırpma yok: metin satır kısıtı ya da taşma gizleme taşımaz.
  expect(await is_.locator('.kilavuz-matris__metin').first().evaluate(e => {
    const c = getComputedStyle(e)
    return [c.webkitLineClamp, c.textOverflow, c.overflow].join('|')
  })).toBe('none|clip|visible')
  await expect(page.getByRole('link', { name: 'Kapsam kılavuzunu aç (2. senaryo)' })).toBeVisible()
  expect(await erisilebilirlik(page, '.hazirlik-ders')).toEqual({ axe: [], ibm: [] })
})

test('duyurulan sütun ders renginde, mavi vurgu değil; renk tek taşıyıcı değil (K4)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri?sinav=1', [[DERS('fen-bilimleri', 1), fikstur('fen-bilimleri-1')]])
  const tablo = page.locator('table.kilavuz-matris')
  await expect(tablo).toBeVisible()
  const belirtec = (ad: string, ozellik: string) => page.locator('section.hazirlik-ders').evaluate((kok, [a, o]) => {
    const p = document.createElement('div')
    p.style.setProperty(o, `var(${a})`)
    kok.append(p)
    const v = getComputedStyle(p).getPropertyValue(o)
    p.remove()
    return v
  }, [ad, ozellik])
  await expect(page.locator('section.hazirlik-ders.ted-subject')).toHaveCount(1)
  const yuzey = await belirtec('--ted-subject-surface', 'background-color')
  const yuzeydeki = await belirtec('--ted-subject-on-surface', 'color')
  const panel = await belirtec('--ted-subject-panel', 'background-color')
  const panelMetni = await belirtec('--ted-subject-text', 'color')
  const vurgulu = tablo.locator('tbody td.kilavuz-matris__vurgu').first()
  const hucre = await vurgulu.evaluate(e => { const c = getComputedStyle(e); return { bg: c.backgroundColor, renk: c.color } })
  expect(hucre).toEqual({ bg: panel, renk: panelMetni })
  const baslik = tablo.getByRole('columnheader', { name: 'Senaryo S2 · duyurulan' })
  const b = await baslik.evaluate(e => { const c = getComputedStyle(e); return { bg: c.backgroundColor, renk: c.color, kenar: c.borderBottomColor, kalinlik: parseFloat(c.borderBottomWidth) } })
  expect(b.bg).toBe(yuzey)
  expect(b.renk).toBe(yuzeydeki)
  const vurguRengi = await page.locator('section.hazirlik-ders').evaluate(k => {
    const p = document.createElement('div'); p.style.color = 'var(--cds-highlight)'; k.append(p)
    const v = getComputedStyle(p).color; p.remove(); return v
  })
  expect(hucre.bg).not.toBe(vurguRengi)
  const accent = await belirtec('--ted-subject-accent', 'color')
  expect(b.kenar).toBe(accent)
  expect(b.kalinlik).toBeGreaterThanOrEqual(3)
  // Metin de söylüyor: renk tek taşıyıcı değil.
  await expect(baslik).toContainText('duyurulan')
})

test('ana sayfadan ders sayfasına gerçek gezinme: adres ve çizilen sayfa (U2)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik', [[GENEL, fikstur('genel')], [DERS('fen-bilimleri', 1), fikstur('fen-bilimleri-1')]])
  await page.locator('.hazirlik-yaklasan__oge').first().getByRole('link', { name: 'Fen Bilimleri · 1. yazılı' }).click()
  await expect(page).toHaveURL(/\/hazirlik\/fen-bilimleri\?sinav=1$/)
  await expect(page.getByRole('heading', { name: 'Fen Bilimleri', level: 2 })).toBeVisible()
  await expect(page.locator('table.kilavuz-matris')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Sınav Hazırlığı', level: 2 })).toHaveCount(0)
})

test('satır ayrıntısı: tam MEB metni ve kitap bölümü; Esc kapatır, odak satıra döner', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri?sinav=1', [[DERS('fen-bilimleri', 1), fikstur('fen-bilimleri-1')]])
  const dugme = page.getByRole('button', { name: /FB\.7\.2\.1/ })
  await dugme.click()
  const panel = page.locator('aside.cikti-ayrinti')
  await expect(panel.getByRole('heading', { level: 3 })).toBeFocused()
  // S38: başlık yalnız kodu taşır; MEB cümlesi alıntıda bir kez yazılır, kitap konusunun adı yalnız "Kitapta" satırında.
  await expect(panel.getByRole('heading', { level: 3 })).toHaveText('Öğrenme Çıktısı FB.7.2.1')
  await expect(panel).toContainText('MEB: “Fiziksel anlamda yapılan işin bağlı olduğu faktörlere ilişkin bilimsel çıkarım yapabilme”')
  expect((await panel.innerText()).split('Fiziksel anlamda yapılan işin bağlı olduğu faktörlere ilişkin bilimsel çıkarım yapabilme').length - 1).toBe(1)
  const kitap = panel.getByRole('link', { name: /Fen Bilimleri 7 \(1\. Kitap\) › 2\. Ünite › 1\. Kuvvet, İş ve Enerji İlişkisi › Fiziksel Anlamda İş/ })
  await expect(kitap).toHaveAttribute('href', /#page=61$/)
  await expect(panel).toContainText('s. 60–63')
  await expect(panel.getByRole('link', { name: 'Kılavuzda aç' })).toHaveAttribute('href', '/hazirlik/fen-bilimleri/1#cikti-FB-7-2-1')
  // Ayrıntı açıkken de sayfa erişilebilir (panel bir bölge; sayfanın içinde iç içe işaret bölgesi olmamalı).
  expect(await erisilebilirlik(page, '.hazirlik-ders')).toEqual({ axe: [], ibm: [] })
  await page.keyboard.press('Escape')
  await expect(panel).toHaveCount(0)
  await expect(dugme).toBeFocused()
})

test('ayrıntı: düğme açıp kapatır; bağlantılar en az 24 px; Esc yalnız en üstteki katmanı kapatır (D20)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri?sinav=1', [[DERS('fen-bilimleri', 1), fikstur('fen-bilimleri-1')]])
  const dugme = page.getByRole('button', { name: /FB\.7\.2\.1/ })
  await dugme.click()
  await expect(dugme).toHaveAttribute('aria-expanded', 'true')
  const panel = page.locator('aside.cikti-ayrinti')
  for (const bag of await panel.getByRole('link').all()) {
    expect((await bag.boundingBox())!.height).toBeGreaterThanOrEqual(24)
  }
  // Başka bir katman (ör. asistan) açık ve odak onda: Esc ayrıntıyı kapatmaz, o katmanın işidir.
  await page.evaluate(() => {
    const d = document.createElement('button')
    d.id = 'ust-katman'
    d.textContent = 'Üst katman'
    document.body.append(d)
    d.focus()
  })
  await expect(page.locator('#ust-katman')).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(panel).toHaveCount(1)
  // Odak ayrıntının içindeyse Esc onu kapatır; kapat düğmesi de aynısını yapar.
  await panel.getByRole('button', { name: 'Ayrıntıyı kapat' }).click()
  await expect(panel).toHaveCount(0)
  await expect(dugme).toHaveAttribute('aria-expanded', 'false')
})

test('telefonda ayrıntı alttan açılır; alt gezinmeyi örtmez, asistan başlatıcısıyla aynı katmanda değildir (D20)', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await hazirlikAc(page, '/hazirlik/fen-bilimleri?sinav=1', [[DERS('fen-bilimleri', 1), fikstur('fen-bilimleri-1')]])
  await page.getByRole('button', { name: /FB\.7\.2\.1/ }).click()
  const panel = page.locator('aside.cikti-ayrinti')
  await expect(panel).toBeVisible()
  const bar = page.getByRole('navigation', { name: 'Ana gezinme' })
  await expect(bar).toBeVisible()
  const [p, b] = [await panel.boundingBox(), await bar.boundingBox()]
  expect(p!.y + p!.height).toBeLessThanOrEqual(b!.y + 1)
  expect(p!.y + p!.height).toBeGreaterThan(b!.y - 8)        // panel çubuğun hemen üstünde durur (altta sabit)
  // Alt gezinme ve asistan başlatıcısı (z 8000) panelin üstünde kalır; panel hiçbirinin düzeyinde değil.
  const z = await page.evaluate(() => {
    const katman = (s: string) => parseInt(getComputedStyle(document.querySelector(s)!).zIndex, 10)
    const baslatici = document.createElement('div')
    baslatici.className = 'asistan-baslatici'
    document.body.append(baslatici)
    const sonuc = { panel: katman('aside.cikti-ayrinti'), bar: katman('.bottom-nav'), baslatici: katman('.asistan-baslatici') }
    baslatici.remove()
    return sonuc
  })
  expect(z.panel).toBeLessThan(z.bar)
  expect(z.panel).toBeLessThan(z.baslatici)
  expect(z.panel).toBeGreaterThan(0)
})

test('olası kip: senaryo seçilebilir, kılavuz o senaryoyla ve "olası" diye açılır (K8)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri?sinav=1', [[DERS('fen-bilimleri', 1), fikstur('fen-bilimleri-1-olasi')]])
  await expect(page.getByText('Senaryo duyurulmadı.')).toBeVisible()
  await expect(page.getByText('Olası: 4 senaryo')).toBeVisible()
  await expect(page.getByRole('columnheader', { name: /duyurulan/ })).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'Kapsam kılavuzunu aç (bütün senaryolar)' })).toHaveAttribute('href', '/hazirlik/fen-bilimleri/1')
  await expect(page.getByText(/Seçtiğin/)).toHaveCount(0)
  await page.getByText('3. senaryo', { exact: true }).click()
  await expect(page.getByRole('columnheader', { name: 'S3 · seçilen' })).toBeVisible()
  await expect(page.getByText('Seçtiğin 3. senaryo (duyurulmadı)')).toBeVisible()
  // U3: kılavuz rotası Görev 11'de gelir; burada bağlantının adresi sınanır, gezinme orada.
  await expect(page.getByRole('link', { name: 'Kapsam kılavuzunu aç (3. senaryo, olası)' })).toHaveAttribute('href', '/hazirlik/fen-bilimleri/1?senaryo=3')
  expect(await erisilebilirlik(page, '.hazirlik-ders')).toEqual({ axe: [], ibm: [] })
})

test('yazılı seçici 2. yazılıyı yükler; haritasız ders "kitap bölümleri henüz eklenmedi" (spec §7)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri?sinav=1', [[DERS('fen-bilimleri', 1), fikstur('fen-bilimleri-1')],
    [DERS('fen-bilimleri', 2), fikstur('fen-bilimleri-2')], [DERS('matematik', 1), fikstur('matematik-1')]])
  await page.getByRole('tab', { name: '2. yazılı · tarih yok' }).click()
  await expect(page).toHaveURL(/sinav=2$/)
  // 2. yazılıda FB.7.1.3 yalnız 4. senaryoda var: üç ünite grubu.
  await expect(page.locator('.kilavuz-matris__grup')).toHaveText(['1. Ünite · Uzay Çağı', '2. Ünite · Kuvvet ve Enerjiyi Keşfedelim',
    '3. Ünite · Vücudumuzdaki Sistemler'])
  await page.goto('/hazirlik/matematik')
  await expect(page.getByText('Kitap bölümleri henüz eklenmedi; bu dersin MEB metinleri ve senaryoları burada.')).toBeVisible()
  await page.getByRole('button', { name: /MAT\.7\.1\.1/ }).click()
  await expect(page.locator('aside.cikti-ayrinti')).toContainText('Kitap bölümleri henüz eklenmedi.')
})

test('yazılı değişince önceki yazılının tablosu yeni yazılının adı altında kalmaz', async ({ page }) => {
  await mock(page, LIVE)
  await page.route(DERS('fen-bilimleri', 1), r => r.fulfill(json(fikstur('fen-bilimleri-1'))))
  let birak: () => void = () => {}
  const bekle = new Promise<void>(a => { birak = a })
  await page.route(DERS('fen-bilimleri', 2), async r => { await bekle; await r.fulfill(json(fikstur('fen-bilimleri-2'))) })
  await page.goto('/hazirlik/fen-bilimleri?sinav=1')
  await expect(page.locator('table.kilavuz-matris')).toBeVisible()
  await page.getByRole('tab', { name: '2. yazılı · tarih yok' }).click()
  await expect(page.getByRole('tab', { name: '2. yazılı · tarih yok' })).toHaveAttribute('aria-selected', 'true')
  await expect(page.locator('table.kilavuz-matris')).toHaveCount(0)
  birak()
  await expect(page.locator('.kilavuz-matris__grup')).toHaveCount(3)
  // Seçici yerinde kaldı: klavyeyle seçenin odağı yüklenince düşmez.
  await expect(page.getByRole('tab', { name: '2. yazılı · tarih yok' })).toBeFocused()
})

test('tablo yılı bitmişse sunucunun cümlesi bildirimde görünür (D15, 409)', async ({ page }) => {
  await mock(page, LIVE)
  await page.route(DERS('fen-bilimleri', 1), r => r.fulfill(json({ error: 'tablo_eski', mesaj: 'Yeni yılın tabloları bekleniyor.' }, 409)))
  await page.goto('/hazirlik/fen-bilimleri?sinav=1')
  await expect(page.getByText('Yeni yılın tabloları bekleniyor.')).toBeVisible()
  await expect(page.getByText('Ders sayfası yüklenemedi.')).toHaveCount(0)
  await expect(page.locator('table.kilavuz-matris')).toHaveCount(0)
})

test('ders bulunamazsa sunucunun cümlesi, hata başlığıyla (404)', async ({ page }) => {
  await mock(page, LIVE)
  await page.route(DERS('yok', 1), r => r.fulfill(json({ error: 'bilinmeyen_ders', mesaj: 'Bu ders için MEB senaryosu yok.' }, 404)))
  await page.goto('/hazirlik/yok')
  await expect(page.getByText('Ders sayfası yüklenemedi.')).toBeVisible()
  await expect(page.getByText('Bu ders için MEB senaryosu yok.')).toBeVisible()
})

test('kırıntı bağlantısı Ctrl ile yeni sekmede açılır, düz tıkla uygulama içinde gider (düzeltme 3a)', async ({ page, context }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri?sinav=1', [[DERS('fen-bilimleri', 1), fikstur('fen-bilimleri-1')], [GENEL, fikstur('genel')]])
  const bag = page.getByRole('link', { name: 'Sınav hazırlığı' })
  await expect(bag).toHaveAttribute('href', '/hazirlik')
  const yeni = context.waitForEvent('page')
  await bag.click({ modifiers: ['Control'] })
  await (await yeni).waitForURL(/\/hazirlik$/)
  await expect(page).toHaveURL(/\/hazirlik\/fen-bilimleri\?sinav=1$/)
  await bag.click()
  await expect(page).toHaveURL(/\/hazirlik$/)
})

test('geçmiş yazılının sekmesi de tarih yazar (spec §3.2)', async ({ page }) => {
  const ders = fikstur<{ sinavlar: { durum: Record<string, unknown> }[] }>('fen-bilimleri-1')
  ders.sinavlar[0].durum = { ...ders.sinavlar[0].durum, tur: 'gecti', tarih: '2026-10-22', kalan_gun: null }
  await hazirlikAc(page, '/hazirlik/fen-bilimleri?sinav=1', [[DERS('fen-bilimleri', 1), ders]])
  await expect(page.getByRole('tab', { name: '1. yazılı · 22 Ekim' })).toBeVisible()
  await expect(page.getByRole('tab', { name: '2. yazılı · tarih yok' })).toBeVisible()
})

test('bildirimler tabloyla aynı genişlikte (düzeltme 3c)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri?sinav=1', [[DERS('fen-bilimleri', 1), fikstur('fen-bilimleri-1')]])
  const govde = page.locator('.hazirlik-ders__govde')
  await expect(page.locator('table.kilavuz-matris')).toBeVisible()
  const bildirim = await page.locator('.hazirlik-ders .cds--inline-notification').first().boundingBox()
  const tablo = await govde.boundingBox()
  expect(Math.abs(bildirim!.width - tablo!.width)).toBeLessThanOrEqual(1)
})

test('"her senaryoda" etiketi her satırda metnin altında (kısa metinde de)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/matematik', [[DERS('matematik', 1), fikstur('matematik-1')]])
  await expect(page.locator('table.kilavuz-matris')).toBeVisible()
  const her = page.locator('.kilavuz-matris__her')
  expect(await her.count()).toBeGreaterThan(0)
  for (const e of await her.all()) {
    const satir = e.locator('xpath=ancestor::th')
    const metin = (await satir.locator('.kilavuz-matris__metin').boundingBox())!
    expect((await e.boundingBox())!.y).toBeGreaterThanOrEqual(metin.y + metin.height - 1)
  }
})

test('telefonda dört senaryo sütunu da yatay kaydırmadan görünür', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await hazirlikAc(page, '/hazirlik/fen-bilimleri?sinav=1', [[DERS('fen-bilimleri', 1), fikstur('fen-bilimleri-1')]])
  await expect(page.locator('table.kilavuz-matris')).toBeVisible()
  const kaydirici = page.locator('.hazirlik-ders__tablo')
  expect(await kaydirici.evaluate(e => e.scrollWidth - e.clientWidth)).toBeLessThanOrEqual(1)
  const son = (await page.getByRole('columnheader', { name: 'Senaryo S4' }).boundingBox())!
  expect(son.x + son.width).toBeLessThanOrEqual(390)
})
