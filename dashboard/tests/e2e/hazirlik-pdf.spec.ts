import { test, expect } from '@playwright/test'
import { DERS, KILAVUZ, PDF, fikstur, hazirlikAc, json } from './_hazirlik'

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

// PDF seçenekleri (spec §4, plan Görev 14): Carbon Modal; seçim bu cihazda kişi başına (localStorage, D26).
test('PDF seçenekleri: indirme, seçim kişi başına hatırlanır (spec §4)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), fikstur('fen-bilimleri-1-kilavuz')]])
  const istekler: string[] = []
  await page.route(PDF('fen-bilimleri', 1), r => {
    istekler.push(r.request().url())
    return r.fulfill({ status: 200, contentType: 'application/pdf', body: '%PDF-1.7 deneme',
      headers: { 'Content-Disposition': "attachment; filename=kapsam-kilavuzu-fen-bilimleri-1-s2.pdf; filename*=UTF-8''kapsam-kilavuzu-fen-bilimleri-1-s2.pdf" } })
  })
  await page.getByRole('button', { name: 'PDF olarak indir' }).click()
  const pencere = page.getByRole('dialog')
  await expect(pencere.getByRole('heading', { name: 'Kılavuzu PDF olarak indir' })).toBeVisible()
  await expect(pencere.getByRole('checkbox', { name: 'Ebeveyn özetini başa ekle' })).not.toBeChecked()
  await expect(pencere.getByRole('checkbox', { name: 'Hazırlık işaretlerimi ekle' })).toBeChecked()
  await expect(pencere.getByRole('button', { name: 'Kapat' })).toBeVisible()          // B44
  await expect(pencere.getByText(/yapay zekâ|prova/i)).toHaveCount(0)                 // YZ ve prova Plan 2'de (B42)
  await pencere.getByText('Ebeveyn özetini başa ekle').click()
  const indirme = page.waitForEvent('download')
  await pencere.getByRole('button', { name: "PDF'i indir" }).click()
  expect((await indirme).suggestedFilename()).toBe('kapsam-kilavuzu-fen-bilimleri-1-s2.pdf')
  await expect.poll(() => istekler).toHaveLength(1)
  expect(istekler[0]).toMatch(/kilavuz\.pdf\?senaryo=2&ebeveyn=1&isaret=1$/)
  await expect(pencere).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'PDF olarak indir' })).toBeFocused()   // odak açan düğmeye döner
  // A4 önizleme aynı seçimi taşır (önizleme PDF'in birebir önizlemesi).
  await expect(page.getByRole('link', { name: 'A4 önizleme' })).toHaveAttribute('href', /ebeveyn=1&isaret=1/)
  await page.getByRole('button', { name: 'PDF olarak indir' }).click()
  await expect(page.getByRole('checkbox', { name: 'Ebeveyn özetini başa ekle' })).toBeChecked()
})

test('PDF hazırlanamazsa sunucunun cümlesi pencerede görünür (429 / 503)', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), fikstur('fen-bilimleri-1-kilavuz')]])
  const yanitlar = [
    json({ error: 'mesgul', mesaj: 'Şu an başka bir kılavuz hazırlanıyor; bir dakika sonra yeniden dene.' }, 429),
    json({ error: 'pdf_uretilemedi', mesaj: 'PDF hazırlanamadı. Ekrandaki kılavuzu tarayıcının yazdır komutuyla da kaydedebilirsin.' }, 503),
  ]
  await page.route(PDF('fen-bilimleri', 1), r => r.fulfill(yanitlar.shift()!))
  await page.getByRole('button', { name: 'PDF olarak indir' }).click()
  const pencere = page.getByRole('dialog')
  await pencere.getByRole('button', { name: "PDF'i indir" }).click()
  await expect(pencere).toContainText('Şu an başka bir kılavuz hazırlanıyor; bir dakika sonra yeniden dene.')
  await pencere.getByRole('button', { name: "PDF'i indir" }).click()
  await expect(pencere).toContainText('PDF hazırlanamadı. Ekrandaki kılavuzu tarayıcının yazdır komutuyla da kaydedebilirsin.')
  await expect(pencere).not.toContainText('Şu an başka bir kılavuz')
})

test('A4 önizleme baskı görünümünü yeni sekmede açar; ders sayfasında da PDF düğmesi var', async ({ page }) => {
  await hazirlikAc(page, '/hazirlik/fen-bilimleri/1', [[KILAVUZ('fen-bilimleri', 1), fikstur('fen-bilimleri-1-kilavuz')],
    [DERS('fen-bilimleri', 1), fikstur('fen-bilimleri-1')]])
  const onizleme = page.getByRole('link', { name: 'A4 önizleme' })
  await expect(onizleme).toHaveAttribute('href', '/baski.html?senaryo=2&ebeveyn=0&isaret=1&ders=fen-bilimleri&sinav=1')
  await expect(onizleme).toHaveAttribute('target', '_blank')
  await page.goto('/hazirlik/fen-bilimleri?sinav=1')
  await expect(page.getByRole('heading', { name: 'Fen Bilimleri' })).toBeVisible()
  await page.getByRole('button', { name: 'PDF olarak indir' }).click()
  await expect(page.getByRole('dialog').getByRole('heading', { name: 'Kılavuzu PDF olarak indir' })).toBeVisible()
})
