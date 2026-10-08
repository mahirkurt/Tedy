import { test, expect } from '@playwright/test'
import { PAYLOAD, asistanAc, cevapla, sor } from './_asistan-carbon'

const MID = 'a'.repeat(32)

test('rozetler: kaynak sorunu, risk kırmızı, uyarı gri, yedek model; ham bayrak yok', async ({ page }) => {
  await cevapla(page, PAYLOAD({ answer: 'Cevap.', safety_flags: ['risk:self_harm', 'warning:yerel_yedek'],
    meta: { model: 'gemma4-e4b-cpu', degraded: ['maarif-mufredat', 'yeni-sunucu'] } }))
  await asistanAc(page)
  await sor(page, 'Soru')
  await expect(page.getByText('Müfredat kaynağına ulaşılamadı', { exact: true })).toBeVisible()
  await expect(page.getByText('Kaynağa ulaşılamadı: yeni-sunucu', { exact: true }).first()).toBeVisible()
  await expect(page.getByText('Yedek modelden', { exact: true })).toBeVisible()
  await expect(page.getByText('warning:yerel_yedek', { exact: true })).toHaveCount(0)
  await expect(page.locator('[data-tedy-altbilgi] .cds--tag--red')).toHaveCount(1)
})

test('Daha derine in force_deep yollar; Yeniden üret eskisini kaldırır; Kopyala', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  const istekler = await cevapla(page, PAYLOAD({ answer: 'İlk cevap.' }))
  await asistanAc(page)
  await sor(page, 'Kesir nedir?')
  await page.getByRole('button', { name: 'Daha derine in' }).click()
  await expect.poll(() => istekler.length).toBe(2)
  expect(istekler[1]).toMatchObject({ force_deep: true })
  await page.getByRole('button', { name: 'Kopyala' }).first().click()
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe('İlk cevap.')
})

test('olumsuz geri bildirim kategorisiyle PUT eder; öğrenciye değil aileye uygun yer tutucu', async ({ page }) => {
  let govde: unknown = null
  await page.route(`**/api/assistant/mesajlar/${MID}/geri-bildirim`, async r => {
    govde = r.request().postDataJSON(); await r.fulfill({ json: govde as object })
  })
  await cevapla(page, PAYLOAD({ answer: 'Cevap.', mesaj_id: MID }))
  await asistanAc(page)
  await sor(page, 'Soru')
  await page.locator('button[aria-label="Bu yanıtı beğenmedim"]').click()
  await page.getByRole('button', { name: 'Anlamadım' }).click()
  await page.locator('textarea[placeholder="Yorum ekle"]').filter({ visible: true }).fill('çok hızlı')
  await page.getByRole('button', { name: 'Geri bildirimi gönder' }).filter({ visible: true }).first().click()
  await expect.poll(() => govde).toEqual({ deger: 'olumsuz', kategori: 'Anlamadım', metin: 'çok hızlı' })
})

test('mesaj kimliği olmayan cevapta geri bildirim düğmesi yok', async ({ page }) => {
  await cevapla(page, PAYLOAD({ answer: 'Kayıtsız.' }))
  await asistanAc(page)
  await sor(page, 'Soru')
  await expect(page.getByText('Kayıtsız.', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Bu yanıtı beğenmedim' })).toHaveCount(0)
})

test('AI etiketi açıklaması modeli ve kaynak notunu söyler', async ({ page }) => {
  await cevapla(page, PAYLOAD({ answer: 'Cevap.', meta: { model: 'claude-sonnet-5', degraded: [] } }))
  await asistanAc(page)
  await sor(page, 'Soru')
  await page.locator('.cds--ai-label__button').first().click()
  await expect(page.getByText('Bu yanıtları bir yapay zekâ yazıyor', { exact: true })).toBeVisible()
  await expect(page.locator('.cds--ai-label-content').first()).toContainText('Son yanıtı Claude Sonnet 5 yazdı.')
})

test('İlerleme sayfası günlüğünde haftalık geri bildirim özeti', async ({ page }) => {
  await page.route('**/api/assistant/ogrenme-gunlugu', r => r.fulfill({ json: { zayif: [], calisilan: [], degerlendirmeler: [],
    hafta: { baslangic: '2026-10-05', sohbet: [], alistirma: 0, puan: { dogru: 0, toplam: 0 } },
    geri_bildirim: { hafta: { olumlu: 3, olumsuz: 1 }, son_olumsuz: [{ kategori: 'Anlamadım', metin: 'çok hızlı', zaman: '2026-10-08T09:00:00Z' }] } } }))
  await page.goto('/ilerleme')
  await expect(page.getByText('Asistan cevapları: 3 beğenildi, 1 beğenilmedi', { exact: true })).toBeVisible()
  await expect(page.getByText('Anlamadım — çok hızlı', { exact: true })).toBeVisible()
})
