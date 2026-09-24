import { test, expect, type Page } from '@playwright/test'
import { bugunAc } from './_bugun-fixtures'

// Bugün, judged against its own spec (docs/frontend-surface-designs.md §4.1):
// "Gün Şeridi + tek adlandırılmış adım + altında sessiz 'bugün ayrıca'".
// Measured on 2026-09-24 with the live data, the page had drifted from that:
// two hero cards competing, three time bars, the top homework shown twice, a
// green "program bitti" card over 550px of finished lessons, a calendar event
// printing its raw HTML, and a "Başla" that started nothing.

async function ac(page: Page, saat: string) {
  await bugunAc(page, `2026-09-24T${saat}`)
}

test.describe('A — okura sızan ve belirsiz olan', () => {
  test('takvim etkinliği ham HTML basmaz, başlığını da tekrar etmez', async ({ page }) => {
    await ac(page, '07:30')
    const etkinlik = page.locator('.today-tl__item', { hasText: 'Kulüp' })
    await expect(etkinlik).toHaveCount(1)
    await expect(etkinlik).not.toContainText('<p>')
    // Once the markup is gone the description is the title again, word for
    // word; saying it twice is not information.
    await expect(etkinlik.locator('.today-tl__card-sub')).toHaveCount(0)
  })

  test('çıplak "3/7" sayacı yok', async ({ page }) => {
    await ac(page, '10:15')
    await expect(page.locator('.today__lesson-counter')).toHaveCount(0)
  })

  test('ders adı portalın yazdığı gibi kalır', async ({ page }) => {
    await ac(page, '07:30')
    await expect(page.locator('.today-tl')).toContainText('Kültür ve Medeniyetimize Yön Verenler')
  })
})

test.describe('B — günün saatine göre tek ana kart', () => {
  test('ders sürerken ana kart o anki ders, ödev sessiz bir satır', async ({ page }) => {
    await ac(page, '10:15')

    const simdi = page.locator('.today-now')
    await expect(simdi).toBeVisible()
    await expect(simdi).toContainText('İngilizce')
    await expect(simdi).toContainText('10 dk kaldı')
    await expect(simdi).toContainText('Sonra: Matematik 10:35')

    // The homework is still named — as a preview, not as a second hero.
    const odev = page.locator('.next-thing')
    await expect(odev).toHaveClass(/next-thing--quiet/)
    await expect(odev.getByRole('button')).toHaveCount(0)
    const [a, b] = [await simdi.boundingBox(), await odev.boundingBox()]
    expect(a!.y).toBeLessThan(b!.y)

    // One time bar (the strip), no second hero, no pulse.
    await expect(page.locator('.today-hero')).toHaveCount(0)
    await expect(page.locator('.today-daybar')).toHaveCount(0)
  })

  test('okuldan önce ana kart ilk ders', async ({ page }) => {
    await ac(page, '07:30')
    const simdi = page.locator('.today-now')
    await expect(simdi).toContainText('İLK DERS')
    await expect(simdi).toContainText('Matematik')
  })

  test('son zilden sonra ana kart ödev olur', async ({ page }) => {
    await ac(page, '16:40')
    await expect(page.locator('.today-now')).toHaveCount(0)
    const odev = page.locator('.next-thing')
    await expect(odev).not.toHaveClass(/next-thing--quiet/)
    await expect(odev.getByRole('button')).toHaveCount(1)
  })

  test('sıradaki iş aşağıda bir daha listelenmez', async ({ page }) => {
    await ac(page, '16:40')
    await expect(page.getByText('2. HAFTA MATEMATİK HAFTA İÇİ ÖDEVİ')).toHaveCount(1)
    const ayrica = page.locator('.today-also')
    await expect(ayrica).toContainText('S1 Les verbes')
    await expect(ayrica).toContainText('Ödev (Hibrit 10-16)')
    // Quiet means quiet: no coloured countdown chips (İ6).
    await expect(ayrica.locator('.cds--tag')).toHaveCount(0)
  })

  test('biten dersler tek satıra katlanır, yeşil "bitti" kartı yok', async ({ page }) => {
    await ac(page, '16:40')
    await expect(page.getByText('Bugünkü program bitti')).toHaveCount(0)
    await expect(page.locator('.today-tl__item')).toHaveCount(0)

    const katlanan = page.locator('.today-past-fold')
    await expect(katlanan).toContainText('7 ders')
    await katlanan.click()
    await expect(page.locator('.today-tl__item')).toHaveCount(8)
  })

  test('ders sırasında yalnız bitenler katlanır', async ({ page }) => {
    await ac(page, '10:15')
    await expect(page.locator('.today-past-fold')).toContainText('2 ders')
    await expect(page.locator('.today-tl__item').first()).toContainText('İngilizce')
  })
})

test.describe('B — Başla gerçekten başlatır', () => {
  test('sıradaki iş teslim zamanını söyler', async ({ page }) => {
    await ac(page, '16:40')
    await expect(page.locator('.next-thing')).toContainText('Teslim yarın 12:00')
  })

  test('Başla yerinde bir 10 dakikalık kutu açar ve talimatı gösterir', async ({ page }) => {
    await ac(page, '16:40')
    await page.locator('.next-thing').getByRole('button', { name: 'Başla' }).click()

    const kutu = page.locator('.next-thing')
    await expect(kutu.locator('.next-thing__eyebrow')).toContainText('BAŞLADIN')
    await expect(kutu).toContainText('10 dk kaldı')
    // What to do for those ten minutes, in the teacher's own words.
    await expect(kutu).toContainText('sayfa 165')
    // It stayed here: nothing to find again on another page (İ5).
    await expect(page).toHaveURL(/\/$/)
  })

  test('kutu yenilemede kaybolmaz', async ({ page }) => {
    await ac(page, '16:40')
    await page.locator('.next-thing').getByRole('button', { name: 'Başla' }).click()
    await page.clock.setFixedTime(new Date('2026-09-24T16:44:00'))
    await page.reload()
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.next-thing__eyebrow')).toContainText('BAŞLADIN')
    await expect(page.locator('.next-thing')).toContainText('6 dk kaldı')
  })

  test('süre dolunca bir 10 dakika daha önerir', async ({ page }) => {
    await ac(page, '16:40')
    await page.locator('.next-thing').getByRole('button', { name: 'Başla' }).click()
    await page.clock.setFixedTime(new Date('2026-09-24T16:51:00'))
    await page.reload()
    await page.waitForLoadState('networkidle')

    const kutu = page.locator('.next-thing')
    await expect(kutu).toContainText('10 dakika doldu')
    await kutu.getByRole('button', { name: '10 dakika daha' }).click()
    await expect(kutu.locator('.next-thing__eyebrow')).toContainText('BAŞLADIN')
    await expect(kutu).toContainText('10 dk kaldı')
  })
})
