import { test, expect } from '@playwright/test'
import { PAYLOAD, asistanAc, cevapla, sor } from './_asistan-carbon'
import { OGRETMENLER } from './_gorsel-fixtures'

const QUIZ = { id: 'q1', baslik: 'Kesirler', ders: 'Matematik', konu: 'Kesir', kazanim_kodu: null, zorluk: 'kolay',
  sorular: [{ tur: 'coktan_secmeli', soru: '1/2 + 1/2 kaçtır?', secenekler: ['1', '2', '1/4', '0'] }] }

test('alıştırma akışta görünür, cevap sonra işaretlenir', async ({ page }) => {
  await cevapla(page, PAYLOAD({ answer: 'Alıştırma hazır.' }), [['quiz', QUIZ]])
  await page.route('**/api/assistant/alistirmalar/q1/cevap', r => r.fulfill({ json: { dogru: true, aciklama: 'İki yarım bir bütündür.' } }))
  await asistanAc(page)
  await sor(page, 'Kesirden alıştırma ver')
  await expect(page.getByText('1/2 + 1/2 kaçtır?', { exact: true })).toBeVisible()
  await page.locator('.ac-alistirma').getByText('1', { exact: true }).click()
  await page.getByRole('button', { name: 'Cevabı gönder' }).click()
  await expect(page.getByText('Doğru', { exact: true })).toBeVisible()
})

test('netleştirme seçeneği soruyu gönderir; eski cevapta kapalı', async ({ page }) => {
  const istekler = await cevapla(page, PAYLOAD({ answer: 'Hangisini kastettin?', netlestirme: { soru: 'Hangisi?', secenekler: ['Kesir', 'Ondalık'] } }))
  await asistanAc(page)
  await sor(page, 'Bunu anlat')
  await page.getByRole('button', { name: 'Kesir' }).click()
  await expect.poll(() => istekler.length).toBe(2)
  expect(JSON.stringify(istekler[1])).toContain('Kesir')
  await expect(page.getByRole('button', { name: 'Kesir' }).first()).toBeDisabled()
})

test('ödev fotoğrafı onay kartı adayları gösterir ve kayıt yalnız onayla', async ({ page }) => {
  let kayit = 0
  await page.route('**/api/homework/photo**', r => { kayit += 1; return r.fulfill({ json: { ok: true } }) })
  await cevapla(page, PAYLOAD({ answer: 'Fotoğraftaki ödevler.', odev_onerisi: { ek_id: 'e'.repeat(32),
    adaylar: [{ ders: 'Matematik', baslik: 's.84', teslim: '2026-10-09', aciklama: '1-10', eksik: [] }] } }))
  await asistanAc(page)
  await sor(page, 'Bunu işlere ekle')
  await expect(page.getByLabel('Başlık', { exact: true })).toHaveValue('s.84')
  expect(kayit).toBe(0)
  await page.getByRole('button', { name: 'Ödevlere ekle' }).click()
  await expect.poll(() => kayit).toBe(1)
})

test('mod önerisi yalnız Genel modda, tıklanınca öğretmen değişir', async ({ page }) => {
  await page.route('**/api/assistant/ogretmenler', r => r.fulfill({ json: OGRETMENLER }))
  await cevapla(page, PAYLOAD({ answer: 'Bu bir matematik sorusu.' }), [['mode_suggestion', { ogretmen: 'matematik',
    ogretmen_adi: 'Matematik öğretmeni', soru: 'Matematik öğretmenine geçelim mi?', gerekce: 'Kesir konusu', renk_ailesi: 'blue' }]])
  await asistanAc(page)
  await sor(page, 'Kesir nedir?')
  await page.getByRole('button', { name: 'Matematik öğretmenine geçelim mi?' }).click()
  await expect(page.getByRole('radio', { name: 'Matematik' })).toBeChecked()
  await expect(page.getByRole('button', { name: 'Matematik öğretmenine geçelim mi?' })).toHaveCount(0)
})

test('çalışma planı hızlı sorusu /plan ucuna gider ve plan bloklarını gösterir', async ({ page }) => {
  let plan = 0
  await page.route('**/api/assistant/plan', r => { plan += 1; return r.fulfill({ json: PAYLOAD({ answer: 'Planın hazır.',
    plan_blocks: [{ day: 'Pazartesi', title: 'Kesir tekrarı', actions: ['Örnekleri çöz'], estimated_minutes: 25 }] }) }) })
  await cevapla(page, PAYLOAD())
  await asistanAc(page)
  await page.getByRole('button', { name: 'Işık için çalışma planı hazırla' }).click()
  await expect(page.getByText('Kesir tekrarı', { exact: true })).toBeVisible()
  await expect(page.getByText('25 dk', { exact: true })).toBeVisible()
  expect(plan).toBe(1)
})
