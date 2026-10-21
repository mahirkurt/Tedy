import { test, expect, type Locator, type Page } from '@playwright/test'
import { createRequire } from 'node:module'
import AxeBuilder from '@axe-core/playwright'
import { mock, LIVE } from './_audit-fixtures'

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

const ACE = createRequire(import.meta.url).resolve('accessibility-checker-engine/ace.js')
const BLOK = {
  durum: 'dogrulandi', ders: 'Türkçe', sinav_no: 1, anilan: [4],
  cumle: 'Sınavınızın içeriği, MEB konu soru dağılım tablosu 4. senaryo ağırlıklı olacaktır.',
  senaryo: 4, toplam: 7,
  dagilim: [
    { kod: 'T.O.7.4', metin: 'Metinde geçen anlamını bilmediği söz varlığı unsurlarının anlamını tahmin edebilme', soru: 1, duyuruda: true },
    { kod: 'T.O.7.5', metin: 'Metnin yüzey anlamını belirleyebilme', soru: 2, duyuruda: true },
    { kod: 'T.Y.7.21', metin: 'Yazım kuralları ve noktalama işaretlerini uygulayabilme', soru: 1, duyuruda: false },
  ],
  eslesen_konu_sayisi: 2, eslesmeyen_konular: [], senaryo_disi_konular: [], adaylar: [], senaryo_sayisi: 6,
  kaynak: 'https://odsgm.meb.gov.tr/www/1donem-konu-soru-dagilim-tablolari-2026-2027/icerik/1724',
  meb_guncelleme: '2026-09-10T17:27',
}
const sinav = (senaryo: Record<string, unknown>) => ({ exams: { exams: [{
  id: 'tr11', course: 'Türkçe', title: '1.1 Ara Değerlendirme Sınavı', rawTitle: '1.1 Ara Değerlendirme Sınavı',
  courseColor: '#9f1853', examNumber: null, date: '2026-10-22', endDate: null, allDay: true, status: 'upcoming',
  grade: null, relatedHomework: [], relatedContent: [], tur: 'ortak_sinav',
  konular: ['Metnin yüzey anlamını belirleyebilme'], kaynaklar: [], senaryo,
}], stats: { upcoming: 1, past: 0, averageGrade: null } } })

async function ac(page: Page, senaryo: Record<string, unknown>) {
  await mock(page, { ...LIVE, ...sinav(senaryo) })
  await page.goto('/sinavlar')
  await page.getByRole('button', { name: 'Detaylar' }).first().click()
  await page.locator('.meb-senaryo').waitFor()
}

test('doğrulandı: cümle, ikon adı, liste klavyeyle açılır', async ({ page }) => {
  await ac(page, BLOK)
  const b = page.locator('.meb-senaryo')
  await expect(b).toContainText('Duyurudaki 4. senaryo MEB tablosunda var: 7 soru. Duyurudaki 2 konu bu senaryoda.')
  await expect(b.getByLabel('Doğrulandı')).toBeVisible()
  // Spec §3.2/§10: öğretmenin sözü ("ağırlıklı" gibi nüans) aynen, tırnaklı satırda görünür.
  await expect(b.locator('.meb-senaryo__duyuru')).toHaveText(`Duyuru: «${BLOK.cumle}»`)
  const dugme = b.getByRole('button', { name: 'Senaryonun 3 çıktısını göster' })
  await dugme.focus()
  await page.keyboard.press('Enter')
  await expect(b.getByRole('button', { name: 'Çıktıları gizle' })).toHaveAttribute('aria-expanded', 'true')
  await expect(b.locator('.meb-senaryo__liste li')).toHaveCount(3)
  await expect(b.locator('.meb-senaryo__liste li').nth(1)).toContainText('2 soru · T.O.7.5')
  await expect(b.locator('.meb-senaryo__liste .meb-senaryo__etiket')).toHaveCount(2)
  const mebBaglantisi = b.getByRole('link', { name: 'MEB tablosu (MEB, 10.09.2026)' })
  await expect(mebBaglantisi).toBeVisible()
  // B58: sayfadan çıkan bağlantı Carbon'un Launch ikonunu taşır.
  await expect(mebBaglantisi.locator('.cds--link__icon svg')).toHaveCount(1)
  const axe = await new AxeBuilder({ page }).include('.meb-senaryo')
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa', 'best-practice']).analyze()
  expect(axe.violations).toEqual([])
  await page.addScriptTag({ path: ACE })
  const ihlal = await page.evaluate(async () => {
    // @ts-expect-error — `ace` is the injected engine's global
    const rapor = await new window.ace.Checker().check(document.querySelector('.meb-senaryo'), ['IBM_Accessibility'])
    return rapor.results.filter((s: { value: string[] }) => s.value[0] === 'VIOLATION' && s.value[1] === 'FAIL')
      .map((s: { ruleId: string }) => s.ruleId)
  })
  expect(ihlal).toEqual([])
})

test('kısmen', async ({ page }) => {
  await ac(page, { ...BLOK, durum: 'kismen', eslesen_konu_sayisi: 3, senaryo_disi_konular: ['Derin anlam'] })
  await expect(page.locator('.meb-senaryo')).toContainText('Şu konu 4. senaryoda yok: Derin anlam.')
  await expect(page.locator('.meb-senaryo').getByLabel('Uyarı')).toBeVisible()
  await expect(page.locator('.meb-senaryo__duyuru')).toHaveText(`Duyuru: «${BLOK.cumle}»`)
})

test('senaryo yok', async ({ page }) => {
  await ac(page, { ...BLOK, durum: 'senaryo_yok', anilan: [9], cumle: 'Sınav 9. senaryo ağırlıklı olacak.',
    senaryo: null, toplam: null, dagilim: [] })
  await expect(page.locator('.meb-senaryo')).toContainText('Duyuru 9. senaryo diyor; MEB tablosunda bu sınav için 1–6 var.')
  await expect(page.locator('.meb-senaryo__duyuru')).toHaveText('Duyuru: «Sınav 9. senaryo ağırlıklı olacak.»')
  await expect(page.locator('.meb-senaryo').getByRole('button', { name: /çıktısını göster/ })).toHaveCount(0)
})

test('ülke geneli', async ({ page }) => {
  await ac(page, { ...BLOK, durum: 'ulke_geneli', anilan: [], senaryo: null, dagilim: [], senaryo_sayisi: 0, not: 'Ülke Geneli' })
  await expect(page.locator('.meb-senaryo')).toContainText('Bu sınav ülke genelinde ortak yapılır; senaryo yok.')
  await expect(page.locator('.meb-senaryo__duyuru')).toHaveCount(0)
})

test('belirtilmedi: tahmin etiketli', async ({ page }) => {
  await ac(page, { ...BLOK, durum: 'belirtilmedi', anilan: [], senaryo: null, toplam: null, dagilim: [], adaylar: [3, 4] })
  const b = page.locator('.meb-senaryo')
  await expect(b).toContainText('Duyuruda senaryo belirtilmedi · MEB tablosunda 6 senaryo var.')
  await expect(b).toContainText('Duyurudaki konular 3. ve 4. senaryolarla uyumlu (TEDY’nin tahmini).')
  await expect(b.locator('.meb-senaryo__duyuru')).toHaveCount(0)
})

test('telefonda asistana sor Asistan sayfasına götürür', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await ac(page, BLOK)
  const dugme = page.locator('.meb-senaryo').getByRole('button', { name: 'Örnek sınav için asistana sor' })
  expect((await dugme.boundingBox())!.height).toBeGreaterThanOrEqual(44)
  await dugme.click()
  await expect(page).toHaveURL(/\/asistan\?sayfa=sinavlar/)
})

/** Düğmenin etiketinin dikey ortası, düğme kutusunun ortasına en çok 4 px uzakta: kutu büyürken etiket üstte kalmasın. */
async function etiketOrtada(dugme: Locator) {
  const { fark, yukseklik } = await dugme.evaluate(el => {
    const aralik = document.createRange()
    aralik.selectNodeContents(el)
    const yazi = aralik.getBoundingClientRect()
    const kutu = el.getBoundingClientRect()
    return { fark: Math.abs((yazi.top + yazi.height / 2) - (kutu.top + kutu.height / 2)), yukseklik: kutu.height }
  })
  expect(yukseklik).toBeGreaterThanOrEqual(44)
  expect(fark).toBeLessThanOrEqual(4)
}

test('telefonda bağlantı ve düğmeler ≥ 44 px, düğme etiketi ortada', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await ac(page, BLOK)
  const b = page.locator('.meb-senaryo')
  const baglanti = await b.getByRole('link', { name: /MEB tablosu/ }).boundingBox()
  expect(baglanti!.height).toBeGreaterThanOrEqual(44)
  const acKapa = b.getByRole('button', { name: 'Senaryonun 3 çıktısını göster' })
  expect((await acKapa.boundingBox())!.height).toBeGreaterThanOrEqual(44)
  await etiketOrtada(acKapa)
  await etiketOrtada(b.getByRole('button', { name: 'Örnek sınav için asistana sor' }))
  // Düğme yoğunluğu etiketlere de yayılmasın: liste açılınca "duyuruda" etiketi küçük kalır.
  await acKapa.click()
  expect((await b.locator('.meb-senaryo__etiket').first().boundingBox())!.height).toBeLessThan(32)
})

test('masaüstünde düğmeler sm boyunda kalır', async ({ page }) => {
  await ac(page, BLOK)
  const b = page.locator('.meb-senaryo')
  expect((await b.getByRole('button', { name: 'Örnek sınav için asistana sor' }).boundingBox())!.height).toBeCloseTo(32, 0)
  expect((await b.getByRole('button', { name: 'Senaryonun 3 çıktısını göster' }).boundingBox())!.height).toBeCloseTo(32, 0)
})

test('blok yoksa bölüm yok', async ({ page }) => {
  const veri = sinav({})
  await mock(page, { ...LIVE, exams: { ...veri.exams, exams: [{ ...veri.exams.exams[0], senaryo: null }] } })
  await page.goto('/sinavlar')
  await page.getByRole('button', { name: 'Detaylar' }).first().click()
  await expect(page.locator('.exam-card__details')).toContainText('Konular')
  await expect(page.locator('.meb-senaryo')).toHaveCount(0)
})
