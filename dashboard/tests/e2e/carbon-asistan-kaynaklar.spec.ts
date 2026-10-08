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

test('kaynak paneli "Kaynakları kapat" ile kapanır, sohbet geri gelir (dar alanda panel sohbeti örter)', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 })
  await cevapla(page, PAYLOAD({ answer: 'Kesir parçadır [S1].', citations: ATIFLAR.slice(0, 1) }))
  await asistanAc(page)
  await sor(page, 'Soru')
  await page.getByRole('button', { name: 'Kaynak ayrıntıları' }).click()
  await expect(page.locator('.asistan__kaynaklar')).toBeVisible()
  await page.getByRole('button', { name: 'Kaynakları kapat' }).click()
  await expect(page.locator('.asistan__kaynaklar')).toHaveCount(0)
  await expect(page.getByText('Kesir parçadır.', { exact: true }).filter({ visible: true })).toHaveCount(1)
  await expect(page.getByRole('button', { name: 'Kaynak ayrıntıları' })).toBeFocused()
})

// Eski "citation chips render inside every markdown block type" ve "…inside bold and italic emphasis, but not
// inside code spans" (karar tablosu): Carbon atıfı metin içinde çip olarak değil, kaynak listesinde gösterir.
test('kutu, liste, tablo hücresi ve vurgudaki işaretler metinden çıkar, her atıf listede; kod aralığındaki [S1] yazı kalır', async ({ page }) => {
  const atif = (id: string, label: string) => ({ id, kind: 'mufredat', label, locator: {}, snippet: `${label} özeti`, confidence: 0.9 })
  await cevapla(page, PAYLOAD({
    answer: [':::kavram', 'Pay üstteki sayıdır [S1].', ':::', '', '- ikinci madde [S2]', '',
      '| a | b |', '|---|---|', '| hücre [S3] | x |', '', 'Bu **önemli bir uyarı [S4]** böyle.', '',
      'Kod `örnek [S1]` aralığı.'].join('\n'),
    citations: [atif('S1', 'Kutu kaynağı'), atif('S2', 'Liste kaynağı'), atif('S3', 'Tablo kaynağı'), atif('S4', 'Vurgu kaynağı')],
  }))
  await asistanAc(page)
  await sor(page, 'Soru')
  await expect(page.getByText('önemli bir uyarı', { exact: true }).filter({ visible: true })).toHaveCount(1)
  await expect(page.getByText('hücre', { exact: true }).filter({ visible: true })).toHaveCount(1)
  await expect(page.getByText(/\[S[2-4]\]/).filter({ visible: true })).toHaveCount(0)
  // Kutu eklenti düğümünde; Carbon'un yuvası aynı metni yedek içerik olarak da tutar (çizilmez).
  await expect(page.locator('.ac-kutu--kavram').getByText('Pay üstteki sayıdır.', { exact: true })).toBeVisible()
  await expect(page.locator('code').filter({ hasText: 'örnek [S1]' }).filter({ visible: true })).toHaveCount(1)
  await page.getByRole('button', { name: 'Kaynaklar', exact: true }).click()
  await expect(page.getByText('1 / 4', { exact: true }).filter({ visible: true })).toHaveCount(1)
  for (const label of ['Kutu kaynağı', 'Liste kaynağı', 'Tablo kaynağı', 'Vurgu kaynağı'])
    await expect(page.getByText(label, { exact: true }).first()).toBeAttached()
})

// Eski "a citation chip is described by the snippet, not just named by its label" (karar tablosu).
test('atıf kartı kaynağı adıyla ve özetiyle anlatır', async ({ page }) => {
  await cevapla(page, PAYLOAD({ answer: 'Kesirler böyle çalışır [S1].', citations: [{ id: 'S1', kind: 'mufredat',
    label: 'MEB · kesirler', locator: {}, snippet: 'Payda eşitlenerek toplanır.', confidence: 0.9 }] }))
  await asistanAc(page)
  await sor(page, 'kesirler')
  await page.getByRole('button', { name: 'Kaynaklar', exact: true }).click()
  await expect(page.getByText('MEB · kesirler', { exact: true }).filter({ visible: true })).toHaveCount(1)
  await expect(page.getByText('Payda eşitlenerek toplanır.', { exact: true }).filter({ visible: true })).toHaveCount(1)
})
