import { test, expect } from '@playwright/test'
import { PAYLOAD, asistanAc, cevapla, sor } from './_asistan-carbon'

const ATIFLAR = [
  { id: 'S1', kind: 'mufredat', label: 'Matematik 7 · s.57', locator: {}, snippet: 'Kesirler bölümü', confidence: 1 },
  { id: 'S2', kind: 'mufredat', label: 'Fen Bilimleri 7 figürü', locator: { figure_id: 42, caption: 'Hücre', corpus_version: '1.6' }, snippet: 'Hücre', confidence: 1 },
  { id: 'S3', kind: 'modul', label: 'Kesir modülü', locator: { slug: 'kesir', version: 2 }, snippet: 'Modül', confidence: 1 },
]

test('atıflar Carbon kaynak listesinde, numaralı ve doğru sırada', async ({ page }) => {
  await cevapla(page, PAYLOAD({ answer: 'Kesir parçadır [S1]. Hücre canlının birimidir [S2]. Modül var [S3].', citations: ATIFLAR }))
  await asistanAc(page)
  await sor(page, 'Soru')
  await expect(page.getByText('Kesir parçadır. Hücre canlının birimidir. Modül var.', { exact: true })).toBeVisible()
  await expect(page.getByText('[S1]', { exact: true })).toHaveCount(0)
  // Carbon atıfları cevabın altındaki "Kaynaklar" açılır düğmesinde listeler.
  await page.getByRole('button', { name: 'Kaynaklar', exact: true }).click()
  await expect(page.getByText('Matematik 7 · s.57', { exact: true })).toBeVisible()
})

test('Kaynaklar paneli figür küçük resmini sürümüyle ve modül bağlantısını gösterir', async ({ page }) => {
  await page.route('**/api/assistant/figure/42?v=1.6', r => r.fulfill({ body: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64'), contentType: 'image/png' }))
  await cevapla(page, PAYLOAD({ answer: 'Bak [S2]. Modül [S3].', citations: ATIFLAR.slice(1) }))
  await asistanAc(page)
  await sor(page, 'Soru')
  await page.getByRole('button', { name: 'Kaynak ayrıntıları' }).click()
  await expect(page.getByRole('img', { name: 'Hücre' })).toHaveAttribute('src', /\/api\/assistant\/figure\/42\?v=1\.6/)
  await expect(page.getByRole('link', { name: 'Modülü aç' })).toHaveAttribute('href', '/moduller/kesir/v2')
})
