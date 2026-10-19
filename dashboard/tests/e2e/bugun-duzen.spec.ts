import { test, expect, type Page } from '@playwright/test'
import { bugunAc, HOMEWORK, HW, CALENDAR } from './_bugun-fixtures'

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
    await expect(simdi).toContainText('İlk ders')
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
    await expect(kutu.locator('.next-thing__eyebrow')).toContainText('Başladın')
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
    await expect(page.locator('.next-thing__eyebrow')).toContainText('Başladın')
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
    await expect(kutu.locator('.next-thing__eyebrow')).toContainText('Başladın')
    await expect(kutu).toContainText('10 dk kaldı')
  })
})

// The 2026-10-10 redesign (docs/superpowers/specs/2026-10-10-bugun-yenileme-design.md):
// the voice knows whether there is school, calendar events never take the card,
// a deadline row is reachable by keyboard, a failed fetch says so, and the Day
// Strip's marks can be seen.

/** WCAG relative-luminance contrast of two computed `rgb(…)` colours. */
function kontrast(a: string, b: string): number {
  const lum = (c: string) => {
    const [r, g, bl] = (c.match(/[\d.]+/g) ?? []).slice(0, 3).map(Number).map(v => {
      const s = v / 255
      return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
    })
    return 0.2126 * r + 0.7152 * g + 0.0722 * bl
  }
  const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p)
  return (x + 0.05) / (y + 0.05)
}

test.describe('D — yenileme', () => {
  test('okul olmayan gün kart "Okuldan sonra" demez', async ({ page }) => {
    // Saturday: the grid publishes an empty column, so there is no school.
    await bugunAc(page, '2026-09-26T10:00')
    const kart = page.locator('.next-thing')
    await expect(kart.locator('.next-thing__eyebrow')).toHaveText('Şimdi')
    await expect(kart).not.toContainText(/okuldan sonra/i)
  })

  test('gün boyu süren takvim etkinliği şimdi kartını almaz', async ({ page }) => {
    await bugunAc(page, '2026-09-24T10:15', { calendar: { events: [
      ...CALENDAR.events,
      { allDay: false, start: '2026-09-24T08:00:00', end: '2026-09-24T15:45:00',
        title: 'Okul Meclisi Seçimi', extendedProps: { description: '' } },
    ] } })
    const simdi = page.locator('.today-now')
    await expect(simdi).toContainText('İngilizce')
    await expect(simdi).not.toContainText('Okul Meclisi Seçimi')
    // It is still on the day's line.
    await expect(page.locator('.today-tl')).toContainText('Okul Meclisi Seçimi')
  })

  test('bugünkü teslim satırı klavyeyle İşler\'e götürür', async ({ page }) => {
    await bugunAc(page, '2026-09-24T16:40', { homework: { summary: '', homework: [
      ...HOMEWORK.homework,
      HW('Türkçe', 'Okuma günlüğü', '24.09.2026 18:00'),
    ] } })
    const satir = page.locator('.today-tl').getByRole('link', { name: /Okuma günlüğü/ })
    await expect(satir).toBeVisible()
    await satir.focus()
    await expect(satir).toBeFocused()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/\/isler$/)
  })

  test('alınamayan bilgi sessiz geçmez, ham hata metni basmaz', async ({ page }) => {
    await page.route('**/api/homework', r => r.fulfill({ status: 500, body: 'boom' }))
    await bugunAc(page, '2026-09-24T16:40', { homework: null })
    const bant = page.locator('.today-ariza')
    await expect(bant).toContainText('Bazı bilgiler şu an alınamadı')
    await expect(bant).toContainText('Sayfa birkaç dakika içinde kendini yeniler.')
    await expect(bant).not.toContainText(/HTTP|JSON|Fetch|500/)
  })

  test('her şey geldiğinde arıza bandı yok', async ({ page }) => {
    await bugunAc(page, '2026-09-24T16:40')
    await expect(page.locator('.today-ariza')).toHaveCount(0)
  })

  test('geçmiş katlaması zaman çizelgesini adıyla açar', async ({ page }) => {
    await bugunAc(page, '2026-09-24T16:40')
    const katlanan = page.locator('.today-past-fold')
    await expect(katlanan).toHaveAttribute('aria-expanded', 'false')
    const hedef = await katlanan.getAttribute('aria-controls')
    expect(hedef).toBeTruthy()
    await katlanan.click()
    await expect(katlanan).toHaveAttribute('aria-expanded', 'true')
    await expect(page.locator(`#${hedef}`)).toBeVisible()
  })

  test('Gün Şeridi\'nin işaretleri zemine karşı en az 3:1', async ({ page }) => {
    await bugunAc(page, '2026-09-24T10:15')
    const renk = await page.evaluate(() => {
      const cs = (s: string) => getComputedStyle(document.querySelector(s)!)
      return {
        ray: cs('.day-strip__track').backgroundColor,
        okul: cs('.day-strip__part--okul').backgroundColor,
        odev: cs('.day-strip__part--odev').backgroundColor,
        simdi: cs('.day-strip__now').backgroundColor,
        kenar: cs('.day-strip__part--odev').borderInlineStartColor,
        ad: cs('.day-strip__part--okul .day-strip__part-name').color,
      }
    })
    for (const zemin of [renk.ray, renk.okul]) {
      expect(kontrast(renk.simdi, zemin), `şimdi / ${zemin}`).toBeGreaterThanOrEqual(3)
      expect(kontrast(renk.odev, zemin), `ödev zamanı / ${zemin}`).toBeGreaterThanOrEqual(3)
    }
    // A part's edge separates it from the rest of the rail; its name is text.
    expect(kontrast(renk.kenar, renk.ray)).toBeGreaterThanOrEqual(3)
    expect(kontrast(renk.ad, renk.okul)).toBeGreaterThanOrEqual(4.5)
  })

  test('Gün Şeridi günü adlı parçalara böler, saat cetveli yok', async ({ page }) => {
    await bugunAc(page, '2026-09-24T10:15')
    const serit = page.locator('.day-strip')
    await expect(serit.locator('.day-strip__part')).toHaveCount(3)
    await expect(serit.locator('.day-strip__part--okul')).toContainText('Okul')
    await expect(serit.locator('.day-strip__part--aksam')).toContainText('Akşam')
    await expect(serit.locator('.day-strip__homework')).toHaveText(/Ödev zamanı 15:\d\d–16:00/)
    await expect(serit.locator('.day-strip__tick')).toHaveCount(0)
    // The parts fill the rail exactly: no gap, nothing pushed past its end.
    const { ray, toplam } = await serit.evaluate(el => {
      const r = el.querySelector('.day-strip__track')!.getBoundingClientRect()
      const parcalar = [...el.querySelectorAll('.day-strip__part')].map(p => p.getBoundingClientRect())
      return { ray: r.width - 2, toplam: parcalar.reduce((t, p) => t + p.width, 0) }
    })
    expect(Math.abs(ray - toplam)).toBeLessThan(1.5)
  })
})
