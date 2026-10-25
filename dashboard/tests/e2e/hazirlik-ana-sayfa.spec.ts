import { test, expect } from '@playwright/test'
import { GENEL, erisilebilirlik, fikstur, hazirlikAc } from './_hazirlik'

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

test('ana sayfa: önce zaman, sonra altı ders (spec §3.1, taslak A)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik', [[GENEL, fikstur('genel')]])
  await expect(page.getByRole('heading', { name: 'Sınav Hazırlığı', level: 2 })).toBeVisible()
  await expect(page.locator('.hazirlik__kaynak')).toHaveText('MEB konu-soru dağılım tabloları · 7. sınıf · 1. dönem (güncelleme 10.09.2026)')
  const yaklasan = page.locator('.hazirlik-yaklasan__oge')
  await expect(yaklasan).toHaveCount(2)
  await expect(yaklasan.nth(0)).toContainText('Fen Bilimleri · 1. yazılı')
  await expect(yaklasan.nth(0)).toContainText('9 gün')
  await expect(yaklasan.nth(0)).toContainText('3 Kasım Salı · 7 soru · 3 konu duyuruldu')
  await expect(yaklasan.nth(0)).toContainText('Kesin: 2. senaryo')
  await expect(yaklasan.nth(1)).toContainText('Türkçe · 2. yazılı')
  await expect(yaklasan.nth(1)).toContainText('72 gün')
  await expect(yaklasan.nth(1)).toContainText('5 Ocak Salı · ülke geneli ortak sınav')
  // Her yaklaşan kayıt ders renkli sol kenarı olan bir kart (taslak A).
  for (const i of [0, 1]) {
    const kenar = await yaklasan.nth(i).evaluate(e => parseFloat(getComputedStyle(e).borderInlineStartWidth))
    expect(kenar).toBeGreaterThan(0)
  }
  // K10: iki bölüm başlığı da <h3>.
  await expect(page.getByRole('heading', { name: 'Yaklaşan Ortak Yazılılar', level: 3 })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Dersler', level: 3 })).toBeVisible()
  // Karo yalnız en yakın ilgili yazılıyı gösterir (spec §3.1): ilk geçmemiş; öteki yazılı ders sayfasında.
  const karolar = page.locator('.hazirlik-karo')
  await expect(karolar).toHaveCount(6)
  const tr = karolar.filter({ hasText: 'Türkçe' })
  await expect(tr).toContainText('2. yazılı · 5 Ocak')
  await expect(tr).toContainText('Ülke geneli')
  await expect(tr).not.toContainText('1. yazılı')
  const mat = karolar.filter({ hasText: 'Matematik' })
  await expect(mat).toContainText('1. yazılı · tarih yok')
  await expect(mat).toContainText('Olası: 4 senaryo')
  await expect(mat).not.toContainText('2. yazılı')
  // K8: olası kipte hiçbir yüzey tek bir senaryoyu adlandırmaz ("2. senaryo" biçimi yok).
  await expect(mat).not.toContainText(/\d\. senaryo/)
  const fen = karolar.filter({ hasText: 'Fen Bilimleri' })
  await expect(fen).toContainText('1. yazılı · 3 Kasım')
  await expect(fen).toContainText('Kesin: 2. senaryo')
  await expect(fen).not.toContainText('2. yazılı')
  // K4: kesin yeşil ikon, olası mavi ikon; ülke geneli ve geçti ikonsuz düz metin.
  await expect(yaklasan.nth(0).locator('.hazirlik-durum--kesin svg')).toHaveCount(1)
  await expect(yaklasan.nth(1).locator('.hazirlik-durum--notr svg')).toHaveCount(0)
  // Düzen: yaklaşan satırının ayrıntısı ve durumu ayrı satırlarda (Carbon içeriği bir iç kutuya sarar; sütun oraya konur).
  const ayrinti = await yaklasan.nth(0).locator('.hazirlik-yaklasan__ayrinti').boundingBox()
  const durum = await yaklasan.nth(0).locator('.hazirlik-durum').boundingBox()
  expect(ayrinti && durum && durum.y >= ayrinti.y + ayrinti.height - 1).toBe(true)
  expect(await erisilebilirlik(page, '.hazirlik')).toEqual({ axe: [], ibm: [] })
})

test('ana sayfa: ders bağlantısı klavyeyle odaklanır ve ders sayfasına gider; gezinmede "Sınav hazırlığı" var', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik', [[GENEL, fikstur('genel')]])
  const bag = page.locator('.hazirlik-yaklasan__oge').first().getByRole('link', { name: 'Fen Bilimleri · 1. yazılı' })
  await expect(bag).toBeVisible()
  await bag.focus()
  await expect(bag).toBeFocused()
  // U2: ders sayfası rotası Görev 10'da doğar; burada bağlantının adresi sınanır, gezinme o görevde.
  await expect(bag).toHaveAttribute('href', '/hazirlik/fen-bilimleri?sinav=1')
  await expect(page.locator('.hazirlik-karo').filter({ hasText: 'Fen Bilimleri' }).getByRole('link', { name: 'Fen Bilimleri' }))
    .toHaveAttribute('href', '/hazirlik/fen-bilimleri')
  await page.goto('/daha-fazla')
  await expect(page.locator('section.daha-fazla').getByRole('link', { name: 'Sınav hazırlığı' })).toHaveAttribute('href', '/hazirlik')
})

test('ana sayfa: hepsi geçtiyse karo sonuncuyu gösterir; "Geçti" bir kez yazılır (K7)', async ({ page }) => {
  const genel = fikstur<{ dersler: { anahtar: string; sinavlar: { durum: { tur: string; senaryo: number | null } }[] }[] }>('genel')
  const tr = genel.dersler.find(d => d.anahtar === 'turkce')!
  for (const s of tr.sinavlar) s.durum = { ...s.durum, tur: 'gecti', senaryo: 4 }
  await hazirlikAc(page, '/hazirlik', [[GENEL, genel]])
  const karo = page.locator('.hazirlik-karo').filter({ hasText: 'Türkçe' })
  await expect(karo).toContainText('2. yazılı · 5 Ocak')
  await expect(karo).toContainText('Geçti · 4. senaryoydu')
  await expect(karo).not.toContainText('yazılı · geçti')
  await expect(karo.getByText(/geçti/i)).toHaveCount(1)
})

test('ana sayfa: yeni yılın tabloları bekleniyor', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik', [[GENEL, { ...fikstur('genel'), durum: 'tablo_eski', yaklasan: [], dersler: [] }]])
  await expect(page.getByText('Yeni yılın tabloları bekleniyor.')).toBeVisible()
  await expect(page.locator('.hazirlik-karo')).toHaveCount(0)
})
