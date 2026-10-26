import { test, expect } from '@playwright/test'
import { mock, LIVE } from './_audit-fixtures'
import { DERS, erisilebilirlik, fikstur, json } from './_hazirlik'

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

// Kartın ana eylemi: Carbon ghost düğmesi, ama bağlantı olarak çizilir (rolü `link`, adresi var, yeni sekmede açılır).
const giris = (page: import('@playwright/test').Page, ad: string) =>
  page.locator('.meb-senaryo').getByRole('link', { name: ad })

async function kartiAc(page: import('@playwright/test').Page, senaryo: Record<string, unknown>) {
  await mock(page, { ...LIVE, ...sinav(senaryo) })
  await page.goto('/sinavlar')
  await page.getByRole('button', { name: 'Detaylar' }).first().click()
}

test('Sınavlar kartı kılavuzu ana eylem olarak açar; senaryo duyurulmuşsa o senaryoyla', async ({ page }) => {
  await kartiAc(page, blok('dogrulandi', 4))
  await expect(giris(page, 'Kapsam kılavuzunu aç (4. senaryo)')).toHaveAttribute('href', '/hazirlik/turkce/1?senaryo=4')
  // Ana eylem "Örnek sınav için asistana sor"dan önce gelir; ikisi de düğme biçiminde, "MEB tablosu" meta satırında kalır.
  const sira = await page.locator('.meb-senaryo').evaluate(el => [...el.querySelectorAll('a.cds--btn, button.cds--btn')].map(e => e.textContent?.trim()))
  expect(sira.slice(-2)).toEqual(['Kapsam kılavuzunu aç (4. senaryo)', 'Örnek sınav için asistana sor'])
  await expect(page.locator('.meb-senaryo').getByRole('link', { name: /^MEB tablosu/ })).toBeVisible()
})

test('Sınavlar kartı: senaryo belirtilmediyse olası kılavuza bağlanır, tek senaryo adreste ve etikette yok (K8)', async ({ page }) => {
  await kartiAc(page, blok('belirtilmedi', null))
  await expect(giris(page, 'Kapsam kılavuzunu aç')).toHaveAttribute('href', '/hazirlik/turkce/1')
})

test('Sınavlar kartı: duyurulan senaryo tabloda yoksa da tek senaryo adrese girmez', async ({ page }) => {
  await kartiAc(page, blok('senaryo_yok', null, { anilan: [9] }))
  await expect(giris(page, 'Kapsam kılavuzunu aç')).toHaveAttribute('href', '/hazirlik/turkce/1')
})

test('Sınavlar kartı: ülke genelinde yazılı kılavuz değil ders sayfasına, o yazılının numarasıyla bağlanır', async ({ page }) => {
  await kartiAc(page, blok('ulke_geneli', null, { sinav_no: 2 }))
  await expect(giris(page, 'MEB senaryolarını aç')).toHaveAttribute('href', '/hazirlik/turkce?sinav=2')
})

test('Sınavlar kartının giriş düğmesi: axe + IBM sıfır ihlal; telefonda ≥ 44 px', async ({ page }) => {
  await kartiAc(page, blok('dogrulandi', 4))
  // Kapsam: yalnız yeni düğme (kapalı "Çıktıları göster"in aria-controls'u henüz çizilmemiş listeyi gösterir: IBM aria_id_unique,
  // bu görevden önce de vardı).
  expect(await erisilebilirlik(page, '.meb-senaryo a.cds--btn')).toEqual({ axe: [], ibm: [] })
  await page.setViewportSize({ width: 390, height: 844 })
  const kutu = await giris(page, 'Kapsam kılavuzunu aç (4. senaryo)').boundingBox()
  expect(kutu!.height).toBeGreaterThanOrEqual(44)
  expect(await erisilebilirlik(page, '.meb-senaryo a.cds--btn')).toEqual({ axe: [], ibm: [] })
})

test('Sınavlar kartındaki düğme kılavuza gider; Ctrl+tık sayfayı yerinde değiştirmez', async ({ page }) => {
  await mock(page, { ...LIVE, ...sinav(blok('dogrulandi', 4)) })
  await page.route(/\/api\/hazirlik\/turkce\/1\/kilavuz(\?.*)?$/, r => r.fulfill(json({ error: 'tablo_yok' }, 503)))
  await page.goto('/sinavlar')
  await page.getByRole('button', { name: 'Detaylar' }).first().click()
  const dugme = giris(page, 'Kapsam kılavuzunu aç (4. senaryo)')
  // Ctrl+tık tarayıcıya kalır: uygulama yerinde gezinmez (yeni sekme açılırsa o sekme sayfayı değiştirmez).
  await dugme.click({ modifiers: ['Control'] })
  await expect(page).toHaveURL(/\/sinavlar$/)
  await dugme.click()
  await expect(page).toHaveURL(/\/hazirlik\/turkce\/1\?senaryo=4$/)
  await expect(page.locator('.kilavuz-sayfa')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Sınavlar', exact: true })).toHaveCount(0)
})

test('Dersler sekmesi numarasız "MEB senaryoları"na bağlanır', async ({ page }) => {
  await mock(page, LIVE)
  await page.goto('/dersler')
  const panel = page.getByRole('tabpanel')
  await expect(panel.getByRole('link', { name: 'MEB senaryoları' })).toHaveAttribute('href', /^\/hazirlik\/(matematik|turkce|fen-bilimleri)$/)
  await page.getByRole('tab', { name: 'Fen Bilimleri' }).click()
  await expect(panel.getByRole('link', { name: 'MEB senaryoları' })).toHaveAttribute('href', '/hazirlik/fen-bilimleri')
})

test('Dersler sekmesinden gelince 1. yazılı geçmişse ders sayfası 2. yazılıyı açar (adres yerine yazılır)', async ({ page }) => {
  await mock(page, LIVE)
  const bir = fikstur<{ sinavlar: { sinav_no: number; durum: { tur: string } }[] }>('fen-bilimleri-1')
  bir.sinavlar = bir.sinavlar.map(s => ({ ...s, durum: { ...s.durum, tur: s.sinav_no === 1 ? 'gecti' : 'olasi' } }))
  const istekler: string[] = []
  await page.route(DERS('fen-bilimleri', 1), r => { istekler.push('1'); return r.fulfill(json(bir)) })
  await page.route(DERS('fen-bilimleri', 2), r => { istekler.push('2'); return r.fulfill(json(fikstur('fen-bilimleri-2'))) })
  await page.goto('/dersler')
  await page.getByRole('tab', { name: 'Fen Bilimleri' }).click()
  await page.getByRole('tabpanel').getByRole('link', { name: 'MEB senaryoları' }).click()
  await expect(page).toHaveURL(/\/hazirlik\/fen-bilimleri\?sinav=2$/)
  await expect(page.getByRole('tab', { name: /^2\. yazılı/ })).toHaveAttribute('aria-selected', 'true')
  expect(istekler).toContain('2')
  // replace: Geri tuşu Dersler'e döner, ders sayfasına yeniden yönlendirmez.
  await page.goBack()
  await expect(page).toHaveURL(/\/dersler$/)
})

test('Ders sayfası: ?sinav yoksa ve 1. yazılı geçmemişse 1. yazılıda kalır, adres değişmez', async ({ page }) => {
  await mock(page, LIVE)
  await page.route(DERS('fen-bilimleri', 1), r => r.fulfill(json(fikstur('fen-bilimleri-1'))))
  await page.goto('/hazirlik/fen-bilimleri')
  await expect(page.getByRole('heading', { name: 'Fen Bilimleri' })).toBeVisible()
  await expect(page).toHaveURL(/\/hazirlik\/fen-bilimleri$/)
})
