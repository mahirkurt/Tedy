import { test, expect } from '@playwright/test'
import { mock, LIVE } from './_audit-fixtures'
import { GENEL, fikstur, json } from './_hazirlik'

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

// Sınav Hazırlığı giriş noktaları (spec §3.4, plan Görev 12): Sınavlar kartı ve Dersler sekmesi.
const blok = (durum: string, senaryo: number | null, ek: Record<string, unknown> = {}) => ({
  durum, ders: 'Türkçe', sinav_no: 1, anilan: senaryo ? [senaryo] : [], cumle: null, senaryo, toplam: null, dagilim: [],
  eslesen_konu_sayisi: 0, eslesmeyen_konular: [], senaryo_disi_konular: [], adaylar: [], senaryo_sayisi: 6,
  kaynak: 'https://odsgm.meb.gov.tr/x', meb_guncelleme: '2026-09-10T17:27', ...ek,
})
const sinav = (senaryo: Record<string, unknown>) => ({ exams: { exams: [{
  id: 'tr11', course: 'Türkçe', title: '1.1 Ara Değerlendirme Sınavı', rawTitle: '1.1 Ara Değerlendirme Sınavı',
  courseColor: '#9f1853', examNumber: null, date: '2026-12-22', endDate: null, allDay: true, status: 'upcoming',
  grade: null, relatedHomework: [], relatedContent: [], tur: 'ortak_sinav', konular: [], kaynaklar: [], senaryo,
}], stats: { upcoming: 1, past: 0, averageGrade: null } } })

const kilavuzBaglantisi = (page: import('@playwright/test').Page) =>
  page.locator('.meb-senaryo').getByRole('link', { name: 'Kapsam kılavuzu' })

async function kartiAc(page: import('@playwright/test').Page, senaryo: Record<string, unknown>) {
  await mock(page, { ...LIVE, ...sinav(senaryo) })
  await page.goto('/sinavlar')
  await page.getByRole('button', { name: 'Detaylar' }).first().click()
}

test('Sınavlar kartı "Kapsam kılavuzu"na bağlanır; senaryo duyurulmuşsa o senaryoyla', async ({ page }) => {
  await kartiAc(page, blok('dogrulandi', 4))
  await expect(kilavuzBaglantisi(page)).toHaveAttribute('href', '/hazirlik/turkce/1?senaryo=4')
})

test('Sınavlar kartı: senaryo belirtilmediyse olası kılavuza bağlanır, tek senaryo adreste yok (K8)', async ({ page }) => {
  await kartiAc(page, blok('belirtilmedi', null))
  await expect(kilavuzBaglantisi(page)).toHaveAttribute('href', '/hazirlik/turkce/1')
})

test('Sınavlar kartı: duyurulan senaryo tabloda yoksa da tek senaryo adrese girmez', async ({ page }) => {
  await kartiAc(page, blok('senaryo_yok', null, { anilan: [9] }))
  await expect(kilavuzBaglantisi(page)).toHaveAttribute('href', '/hazirlik/turkce/1')
})

test('Sınavlar kartı: ülke genelinde yazılı kılavuz değil ders sayfasına, o yazılının numarasıyla bağlanır', async ({ page }) => {
  await kartiAc(page, blok('ulke_geneli', null, { sinav_no: 2 }))
  await expect(kilavuzBaglantisi(page)).toHaveAttribute('href', '/hazirlik/turkce?sinav=2')
})

test('Sınavlar kartındaki bağlantı kılavuza gider (gerçek gezinme)', async ({ page }) => {
  await mock(page, { ...LIVE, ...sinav(blok('dogrulandi', 4)) })
  await page.route(/\/api\/hazirlik\/turkce\/1\/kilavuz(\?.*)?$/, r => r.fulfill(json({ error: 'tablo_yok' }, 503)))
  await page.goto('/sinavlar')
  await page.getByRole('button', { name: 'Detaylar' }).first().click()
  await kilavuzBaglantisi(page).click()
  await expect(page).toHaveURL(/\/hazirlik\/turkce\/1\?senaryo=4$/)
  await expect(page.getByRole('heading', { name: 'Sınavlar', exact: true })).toHaveCount(0)
})

test('Dersler sekmesi "MEB senaryoları"na bağlanır, en yakın yazılının numarasıyla', async ({ page }) => {
  await mock(page, LIVE)
  const genel = fikstur<{ dersler: { anahtar: string; sinavlar: { sinav_no: number; durum: { tur: string } }[] }[] }>('genel')
  // Fen'in 1. yazılısı geçmiş, 2. yazılısı geçmemiş: ders sayfası 1.'yi değil 2.'yi açmalı.
  const fen = genel.dersler.find(d => d.anahtar === 'fen-bilimleri')!
  fen.sinavlar = fen.sinavlar.map(s => ({ ...s, durum: { ...s.durum, tur: s.sinav_no === 1 ? 'gecti' : 'olasi' } }))
  await page.route(GENEL, r => r.fulfill(json(genel)))
  await page.goto('/dersler')
  const panel = page.getByRole('tabpanel')
  const baglanti = panel.getByRole('link', { name: 'MEB senaryoları' })
  await expect(baglanti).toHaveAttribute('href', /^\/hazirlik\/(matematik|turkce|fen-bilimleri)(\?sinav=[12])?$/)
  await page.getByRole('tab', { name: 'Fen Bilimleri' }).click()
  await expect(panel.getByRole('link', { name: 'MEB senaryoları' })).toHaveAttribute('href', '/hazirlik/fen-bilimleri?sinav=2')
})

test('Dersler sekmesi: hazırlık genel bakışı gelmezse bağlantı yine durur, yazılı numarasız', async ({ page }) => {
  await mock(page, LIVE)
  await page.route(GENEL, r => r.fulfill(json({ error: 'tablo_yok' }, 503)))
  await page.goto('/dersler')
  await expect(page.getByRole('tabpanel').getByRole('link', { name: 'MEB senaryoları' }))
    .toHaveAttribute('href', /^\/hazirlik\/(matematik|turkce|fen-bilimleri)$/)
})
