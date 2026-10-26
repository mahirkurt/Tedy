import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { DERS, KILAVUZ, erisilebilirlik, fikstur, hazirlikAc, json } from './_hazirlik'
import { LIVE, mock } from './_audit-fixtures'

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

const KESIN = () => fikstur('fen-bilimleri-1-kilavuz')

/** Kılavuzun başlıkları, sırasıyla: düzey ve metin. */
async function basliklar(page: Page) {
  return page.locator('.kilavuz-sayfa').locator('h2, h3, h4, h5, h6').evaluateAll(els =>
    els.map(e => ({ duzey: Number(e.tagName[1]), metin: (e.textContent ?? '').trim() })))
}

test('kılavuz ekranı: özet, yan içindekiler, bloklar; axe + IBM sıfır ihlal', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), KESIN()]])
  await expect(page.getByRole('heading', { name: 'Kapsam Kılavuzu', level: 2 })).toBeVisible()
  await expect(page.locator('.kilavuz-baslik__alt')).toHaveText('Fen Bilimleri · 1. yazılı · 2. senaryo')
  await expect(page.locator('.kilavuz-ozet__zaman')).toHaveText('3 Kasım Salı · 9 gün kaldı')
  await expect(page.getByRole('navigation', { name: 'Kılavuzun bölümleri' }).getByRole('link'))
    .toHaveText(['Özet', 'Senaryo Karşılaştırması', '1. Ünite · Uzay Çağı', '2. Ünite · Kuvvet ve Enerjiyi Keşfedelim',
      'Duyuru Doğrulaması', 'Çalışma Planı', 'Kaynaklar'])
  const is_ = page.locator('#cikti-FB-7-2-1')
  await expect(is_.locator('.kilavuz-blok__soru')).toContainText('3 soru')
  await expect(is_.locator('.kilavuz-basliklar li').first()).toContainText('Etkinlik Noktası-1 — Fiziksel anlamda yapılan işin niteliklerini tanımlama · s. 60')
  // Çıktının etiketi MEB metninin kendisi (G10 kararı): senaryoda olmayan çıktı tek satır, soluk.
  await expect(page.locator('#cikti-FB-7-2-2')).toHaveText(/^FB\.7\.2\.2 Enerji çeşitlerinden kinetik ve potansiyel enerjiyi karşılaştırabilme · 2\. senaryoda yok$/)
  await expect(page.locator('#bolum-icindekiler')).toHaveCount(0)   // kâğıdın içindekileri ekranda yok
  // MEB metni blokta bir kez yazılır (başlık kodu taşır, metin alıntıda).
  expect((await is_.innerText()).split('Fiziksel anlamda yapılan işin bağlı olduğu faktörlere ilişkin bilimsel çıkarım yapabilme').length - 1).toBe(1)
  // Okul haftası alanı "işlendi" demez; hafta yoksa "işlenmedi" de demez (karar: "Ders kartında geçtiği hafta").
  await expect(is_.locator('.kilavuz-blok__baglam').first()).toHaveText('Ders kartında geçtiği hafta: bulunamadı')
  await expect(page.locator('.kilavuz-sayfa')).not.toContainText(/işlen/)
  // Doğrulama bölümü duyuruya göredir.
  await expect(page.locator('#bolum-dogrulama')).toContainText('Duyuruya göre')
  expect(await erisilebilirlik(page, '.kilavuz-sayfa')).toEqual({ axe: [], ibm: [] })
})

test('blok iç sırası sabit (K2)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), KESIN()]])
  await page.locator('#cikti-FB-7-2-1').waitFor()
  const sira = await page.locator('#cikti-FB-7-2-1').evaluate(el => [...el.children].map(c => c.className.split(' ')[0]))
  expect(sira).toEqual(['kilavuz-blok__ust', 'kilavuz-blok__soru', 'kilavuz-blok__meb', 'kilavuz-blok__etiket',
    'kilavuz-blok__yollar', 'kilavuz-blok__baglam', 'kilavuz-isaret'])
  // "Kitapta" ile "Bu bölümde ele alınanlar" tek iç içe liste: her yolun altında o konunun başlıkları.
  const grup = await page.locator('#cikti-FB-7-2-1 .kilavuz-yol').first().evaluate(el => [...el.children].map(c => c.className.split(' ')[0]))
  expect(grup).toEqual(['kilavuz-yol__satir', 'kilavuz-yol__etiket', 'kilavuz-basliklar'])
})

test('iki konuya bağlı çıktıda her konunun başlıkları kendi yolunun altında (düzeltme 1)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), KESIN()]])
  const gruplar = page.locator('#cikti-FB-7-1-1 .kilavuz-yol')
  await expect(gruplar).toHaveCount(2)
  const [ilk, ikinci] = [gruplar.nth(0), gruplar.nth(1)]
  await expect(ilk.locator('.kilavuz-yol__satir')).toContainText('1. Türkiye ve Uzay Araştırmaları › Uzay Teknolojileri')
  await expect(ilk.locator('.kilavuz-yol__satir')).toContainText('s. 16–24')
  await expect(ilk.locator('.kilavuz-yol__satir strong')).toHaveText('Uzay Teknolojileri')
  await expect(ikinci.locator('.kilavuz-yol__satir strong')).toHaveText('Teknoloji ile Uzay Araştırmaları Arasındaki İlişki')
  await expect(ikinci.locator('.kilavuz-yol__satir')).toContainText('s. 24–33')
  // s. 24'teki Kontrol Noktası ilk konunun; ikinci konu s. 25'teki Bağlantı Noktası ile başlar.
  await expect(ilk.locator('.kilavuz-basliklar li').last()).toHaveText('Kontrol Kontrol Noktası · s. 24')
  await expect(ikinci.locator('.kilavuz-basliklar li').first()).toHaveText('Bağlantı Bağlantı Noktası · s. 25')
  await expect(ikinci.locator('.kilavuz-basliklar li').filter({ hasText: 'Kontrol Noktası' })).toHaveCount(0)
  await expect(ilk.locator('.kilavuz-basliklar li').filter({ hasText: 'Astronot' })).toHaveCount(0)
  // Konu olmayan ara başlık "Konu" değil "Alt başlık" (kitap yolundaki konuyla çakışmasın).
  await expect(ilk.locator('.kilavuz-basliklar li').filter({ hasText: 'Teleskop Çeşitleri' }).locator('.kilavuz-basliklar__tur')).toHaveText('Alt başlık')
  await expect(page.locator('.kilavuz-basliklar__tur').filter({ hasText: /^Konu$/ })).toHaveCount(0)
  // Tek yollu çıktı aynı düzende tek grup.
  await expect(page.locator('#cikti-FB-7-2-1 .kilavuz-yol')).toHaveCount(1)
})

test('olası kip: tek senaryo sayısı yok (K8)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), fikstur('fen-bilimleri-1-olasi-kilavuz')]])
  await expect(page.locator('.kilavuz-baslik__alt')).toHaveText('Fen Bilimleri · 1. yazılı · bütün senaryolar (olası)')
  const sorular = page.locator('.kilavuz-blok__soru')
  await expect(sorular.first()).toBeVisible()
  for (const metin of await sorular.allInnerTexts()) expect(metin).toMatch(/^(senaryoya göre \d–\d soru|her senaryoda \d soru)/)
  await expect(page.locator('.kilavuz-ozet__sayilar')).toContainText('senaryoya göre 6–9')
  await expect(page.getByText(/Kesin:/)).toHaveCount(0)
  // Çıktı sayısı "olası" diye etiketlenir; "her senaryoda" ayrıca görünür; hiçbir sütun "duyurulan" ya da "seçilen" değil.
  await expect(page.locator('.kilavuz-ozet__sayilar dt')).toHaveText(['Toplam soru', 'Olası öğrenme çıktısı', 'Her senaryoda'])
  await expect(page.locator('#cikti-FB-7-2-1 .kilavuz-blok__her')).toHaveText('her senaryoda')
  await expect(page.getByRole('columnheader', { name: /duyurulan|seçilen/ })).toHaveCount(0)
  await expect(page.getByText(/Seçtiğin/)).toHaveCount(0)
})

test('seçilen ama duyurulmamış senaryo öyle etiketlenir; sayılar o senaryoyla nitelenir (K8)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1?senaryo=3', [[KILAVUZ('fen-bilimleri', 1), fikstur('fen-bilimleri-1-secilen-kilavuz')]])
  await expect(page.locator('.kilavuz-baslik__alt')).toHaveText('Fen Bilimleri · 1. yazılı · 3. senaryo (olası)')
  await expect(page.locator('.kilavuz-ozet__secim')).toHaveText('Seçtiğin 3. senaryo (duyurulmadı)')
  await expect(page.getByRole('columnheader', { name: 'Senaryo S3 · seçilen' })).toBeVisible()
  await expect(page.getByText(/Kesin:/)).toHaveCount(0)
  await expect(page.locator('.kilavuz-ozet__sayi dd').first()).toHaveText('3. senaryoda toplam 8 soru')
  await expect(page.locator('#cikti-FB-7-1-1 .kilavuz-blok__sayi')).toHaveText('3. senaryoda 2 soru')
  for (const metin of await page.locator('.kilavuz-blok__sayi').allInnerTexts()) expect(metin).toMatch(/^3\. senaryoda \d soru$/)
  for (const metin of await page.locator('.kilavuz-ozet__soru').allInnerTexts()) expect(metin).toMatch(/^3\. senaryoda \d soru$/)
  await expect(page.locator('#cikti-FB-7-1-5')).toHaveText(/· 3\. senaryoda yok$/)
})

test('kitapta karşılığı bulunamayan çıktı "bulunamadı" der, "yok" demez', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), fikstur('fen-bilimleri-1-bulunamadi-kilavuz')]])
  const blok = page.locator('#cikti-FB-7-1-3')
  await expect(blok.locator('.kilavuz-blok__yok')).toHaveText('Kitapta karşılığı bulunamadı.')
  await expect(blok.locator('.kilavuz-basliklar')).toHaveCount(0)
})

test('kitap güncellendi uyarısı (K12)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), fikstur('fen-bilimleri-1-k12-kilavuz')]])
  await expect(page.getByText('MEB ders kitabının PDF’i değişti; kitap bölümleri güncel değil, harita yenilenmeli.')).toBeVisible()
})

test('işaret konur; kaydedilemezse geri alınır ve söylenir (spec §7)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), KESIN()]])
  const gonderilen: unknown[] = []
  await page.route('**/api/hazirlik/isaret', r => {
    gonderilen.push(r.request().postDataJSON())
    return r.fulfill(json({ ders: 'fen-bilimleri', isaretler: { 'FB.7.1.1': 'hazirim' } }))
  })
  const blok = page.locator('#cikti-FB-7-1-1')
  const hazirim = blok.getByRole('checkbox', { name: 'Hazırım' })
  await hazirim.check({ force: true })
  await expect(hazirim).toBeChecked()
  // D3: gönderilen istek dizisi beklenir, anlık okunmaz.
  await expect.poll(() => gonderilen).toEqual([{ ders: 'fen-bilimleri', kod: 'FB.7.1.1', durum: 'hazirim' }])
  // FB.7.2.1 fikstürde "tekrar": Hazırım'a geçince Tekrar kalkar; sunucu düşerse ikisi de eski hâline döner.
  await page.unroute('**/api/hazirlik/isaret')
  const dusen: unknown[] = []
  await page.route('**/api/hazirlik/isaret', r => { dusen.push(r.request().postDataJSON()); return r.fulfill(json({ error: 'yazilamadi' }, 503)) })
  const is_ = page.locator('#cikti-FB-7-2-1')
  await expect(is_.getByRole('checkbox', { name: 'Tekrar' })).toBeChecked()
  await is_.getByRole('checkbox', { name: 'Hazırım' }).check({ force: true })
  await expect.poll(() => dusen).toEqual([{ ders: 'fen-bilimleri', kod: 'FB.7.2.1', durum: 'hazirim' }])
  await expect(page.getByRole('alert')).toContainText('İşaret kaydedilemedi; geri alındı.')
  await expect(is_.getByRole('checkbox', { name: 'Tekrar' })).toBeChecked()
  await expect(is_.getByRole('checkbox', { name: 'Hazırım' })).not.toBeChecked()
  // Önceki başarılı işaret yerinde kalır.
  await expect(hazirim).toBeChecked()
})

test('işaret yarışı: eski isteğin hatası daha yeni işareti ezmez (düzeltme 3)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), KESIN()]])
  const gelen: unknown[] = []
  let birak: () => void = () => {}
  const bekle = new Promise<void>(a => { birak = a })
  await page.route('**/api/hazirlik/isaret', async r => {
    gelen.push(r.request().postDataJSON())
    if (gelen.length === 1) { await bekle; return r.fulfill(json({ error: 'yazilamadi' }, 503)) }
    return r.fulfill(json({ ders: 'fen-bilimleri', isaretler: { 'FB.7.1.1': 'tekrar' } }))
  })
  const blok = page.locator('#cikti-FB-7-1-1')
  const [hazirim, tekrar] = [blok.getByRole('checkbox', { name: 'Hazırım' }), blok.getByRole('checkbox', { name: 'Tekrar' })]
  await hazirim.check({ force: true })                 // yavaş ve düşecek ilk istek
  await expect.poll(() => gelen.length).toBe(1)
  await tekrar.check({ force: true })                  // yeni istek, başarılı
  await expect.poll(() => gelen).toEqual([{ ders: 'fen-bilimleri', kod: 'FB.7.1.1', durum: 'hazirim' },
    { ders: 'fen-bilimleri', kod: 'FB.7.1.1', durum: 'tekrar' }])
  await expect(tekrar).toBeChecked()
  const dustu = page.waitForResponse(r => r.url().endsWith('/api/hazirlik/isaret') && r.status() === 503)
  birak()
  await dustu
  // Hata işlenip çizilene dek iki kare bekle (süre değil, koşul: tarayıcının çizim döngüsü).
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => r(null)))))
  await expect(tekrar).toBeChecked()
  await expect(hazirim).not.toBeChecked()
  await expect(page.getByRole('alert')).toHaveCount(0)
})

test('kırıntının son öğesi bulunulan sayfa, sonda "/" yok (düzeltme 5)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), KESIN()]])
  const kirinti = page.getByRole('navigation', { name: 'Konum' })
  await expect(kirinti.locator('.cds--breadcrumb-item')).toHaveText(['Sınav hazırlığı', 'Fen Bilimleri', 'Kapsam Kılavuzu'])
  const son = kirinti.locator('.cds--breadcrumb-item').last()
  await expect(son.locator('[aria-current="page"]')).toHaveText('Kapsam Kılavuzu')
  expect(await son.evaluate(e => getComputedStyle(e, '::after').content)).not.toContain('/')
})

test('telefonda "Bölümler" menüsü yan içindekilerle aynı bağlantıları taşır (düzeltme 4)', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), KESIN()]])
  const ac = page.getByRole('button', { name: 'Bölümler' })
  await expect(ac).toBeVisible()
  await expect(ac).toHaveAttribute('aria-expanded', 'false')
  await ac.click()
  await expect(ac).toHaveAttribute('aria-expanded', 'true')
  const menu = page.getByRole('navigation', { name: 'Kılavuzun bölümleri' })
  await expect(menu.getByRole('link')).toHaveText(['Özet', 'Senaryo Karşılaştırması', '1. Ünite · Uzay Çağı',
    '2. Ünite · Kuvvet ve Enerjiyi Keşfedelim', 'Duyuru Doğrulaması', 'Çalışma Planı', 'Kaynaklar'])
  expect(await erisilebilirlik(page, '.kilavuz-sayfa')).toEqual({ axe: [], ibm: [] })
  await menu.getByRole('link', { name: 'Duyuru Doğrulaması' }).click()
  await expect(page).toHaveURL(/#bolum-dogrulama$/)
  await expect(page.locator('#bolum-dogrulama')).toBeInViewport()
  // Masaüstünde menü yok, yan içindekiler var; kâğıt belgesi (KilavuzBelgesi) menüyü taşımaz.
  await page.setViewportSize({ width: 1440, height: 900 })
  await expect(ac).toBeHidden()
  await expect(page.locator('.kilavuz-belge .kilavuz-sayfa__bolumler')).toHaveCount(0)
})

test('başlık düzeyi sıçramaz, ünite başlıkları ve yan menü adları tekil (U4)', async ({ page }) => {
  for (const ad of ['fen-bilimleri-1-kilavuz', 'fen-bilimleri-1-bulunamadi-kilavuz']) {
    await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), fikstur(ad)]])
    await expect(page.getByRole('heading', { name: 'Kapsam Kılavuzu', level: 2 })).toBeVisible()
    await expect(page.locator('#cikti-FB-7-1-3')).toBeVisible()
    const b = await basliklar(page)
    expect(b[0], ad).toEqual({ duzey: 2, metin: 'Kapsam Kılavuzu' })
    for (let i = 1; i < b.length; i++) expect(b[i].duzey, `${ad}: ${b[i - 1].metin} → ${b[i].metin}`).toBeLessThanOrEqual(b[i - 1].duzey + 1)
    const uniteler = b.filter(x => x.duzey === 3 && /Ünite/.test(x.metin)).map(x => x.metin)
    expect(uniteler, ad).toEqual(['1. Ünite · Uzay Çağı', '2. Ünite · Kuvvet ve Enerjiyi Keşfedelim'])
    const menu = await page.getByRole('navigation', { name: 'Kılavuzun bölümleri' }).getByRole('link').allInnerTexts()
    expect(new Set(menu).size, ad).toBe(menu.length)
    // Her çapa tekil (yinelenen anahtar yinelenen öğe çizerdi).
    const kimlikler = await page.locator('.kilavuz-belge [id]').evaluateAll(els => els.map(e => e.id))
    expect(new Set(kimlikler).size, ad).toBe(kimlikler.length)
  }
  // Çerçevesi olmayan çıktı (bulunamadı fikstüründe FB.7.1.3) ünitenin hemen altında: h4, h5 değil.
  await expect(page.locator('#cikti-FB-7-1-3 h4')).toHaveCount(1)
})

test('ders sayfasından kılavuza gerçek gezinme: adres, istek ve çizilen sayfa (U3)', async ({ page }) => {
  const istenen: string[] = []
  await mock(page, LIVE)
  await page.route(DERS('fen-bilimleri', 1), r => r.fulfill(json(fikstur('fen-bilimleri-1-olasi'))))
  await page.route(KILAVUZ('fen-bilimleri', 1), r => {
    istenen.push(new URL(r.request().url()).search)
    return r.fulfill(json(fikstur('fen-bilimleri-1-secilen-kilavuz')))
  })
  await page.goto('/hazirlik/fen-bilimleri?sinav=1')
  await page.getByText('3. senaryo', { exact: true }).click()
  await page.getByRole('link', { name: 'Kapsam kılavuzunu aç (3. senaryo, olası)' }).click()
  await expect(page).toHaveURL(/\/hazirlik\/fen-bilimleri\/1\?senaryo=3$/)
  await expect(page.getByRole('heading', { name: 'Kapsam Kılavuzu', level: 2 })).toBeVisible()
  await expect(page.locator('.kilavuz-ozet__secim')).toHaveText('Seçtiğin 3. senaryo (duyurulmadı)')
  await expect(page.getByRole('heading', { name: 'Fen Bilimleri', level: 2 })).toHaveCount(0)
  await expect.poll(() => istenen).toEqual(['?senaryo=3&ebeveyn=0&isaret=1'])
})

test('"Kılavuzda aç" çıktının bloğuna kaydırır (D21)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri?sinav=1', [[DERS('fen-bilimleri', 1), fikstur('fen-bilimleri-1')],
    [KILAVUZ('fen-bilimleri', 1), KESIN()]])
  await page.getByRole('button', { name: /FB\.7\.2\.1/ }).click()
  await page.locator('aside.cikti-ayrinti').getByRole('link', { name: 'Kılavuzda aç' }).click()
  await expect(page).toHaveURL(/\/hazirlik\/fen-bilimleri\/1#cikti-FB-7-2-1$/)
  await expect(page.locator('#cikti-FB-7-2-1')).toBeInViewport()
  // Doğrudan açılan adres de kaydırır.
  await page.goto('/hazirlik/fen-bilimleri/1#cikti-FB-7-2-2')
  await expect(page.locator('#cikti-FB-7-2-2')).toBeInViewport()
})

test('tablo yılı bitmişse sunucunun cümlesi bildirimde görünür (D15, 409)', async ({ page }) => {
  await mock(page, LIVE)
  await page.route(KILAVUZ('fen-bilimleri', 1), r => r.fulfill(json({ error: 'tablo_eski', mesaj: 'Yeni yılın tabloları bekleniyor.' }, 409)))
  await page.goto('/hazirlik/fen-bilimleri/1')
  await expect(page.getByText('Yeni yılın tabloları bekleniyor.')).toBeVisible()
  await expect(page.getByText('Kapsam kılavuzu yüklenemedi.')).toHaveCount(0)
  await expect(page.locator('.kilavuz-belge')).toHaveCount(0)
})

test('"Asistana sor" sınavı ve senaryoyu bağlam olarak sabitler; sınav kaydı yoksa ders + yazılı + senaryo (D11)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), KESIN()]])
  await page.getByRole('button', { name: 'Asistana sor' }).click()
  await expect(page).toHaveURL(/\/asistan\?sayfa=sinavlar$/)
  await expect(page.getByText('Bu sayfa: Sınavlar — Fen Bilimleri · 1. yazılı · 2. senaryo')).toBeVisible({ timeout: 15000 })
  const m = KESIN() as { durum: Record<string, unknown> }
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), { ...m, durum: { ...m.durum, sinav_id: null } }]])
  await page.getByRole('button', { name: 'Asistana sor' }).click()
  await expect(page).toHaveURL(/\/asistan\?sayfa=sinavlar$/)
  await expect(page.getByText('Bu sayfa: Sınavlar — Fen Bilimleri · 1. yazılı · 2. senaryo')).toBeVisible({ timeout: 15000 })
})

test('telefonda belge yatay taşmaz; yan içindekiler masaüstünde yapışkan', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), KESIN()]])
  await expect(page.locator('#cikti-FB-7-2-1')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0)
  expect(await erisilebilirlik(page, '.kilavuz-sayfa')).toEqual({ axe: [], ibm: [] })
  await page.setViewportSize({ width: 1440, height: 900 })
  const menu = page.locator('.kilavuz-sayfa__icindekiler')
  await expect(menu).toBeVisible()
  expect(await menu.evaluate(e => getComputedStyle(e).position)).toBe('sticky')
})
