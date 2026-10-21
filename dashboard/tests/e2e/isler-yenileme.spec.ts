import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { createRequire } from 'node:module'
import AxeBuilder from '@axe-core/playwright'
import { json, mock } from './_audit-fixtures'
import { GORSEL, SABIT_SAAT } from './_gorsel-fixtures'
import { sabitAc } from './_gorsel-yardim'

// İşler yenilemesi (2026-10-15, ana dala taşındı 2026-10-20; spec docs/superpowers/specs/2026-10-15-isler-yenileme-
// design.md, talimatname S52–S53). The page names one thing once, lists the rest in Carbon on-page contained
// lists of 48px rows, says when each is due as a day and a time, spends red only on work due today (icon + word),
// and has one primary action. Fixed data and clock: GORSEL at SABIT_SAAT (Thursday 24.09.2026 10:30, Istanbul).

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

const hw = (ders: string, baslik: string, teslim: string, ek: Record<string, unknown> = {}) => ({
  'Ders Adı': ders, normalized_course: ders, 'Ödev Başlığı': baslik, 'Ödev Son Teslim Tarihi': teslim,
  'Ödev Durumu': 'Değerlendirilmemiş', homework_key: `${ders}|${baslik}`, ...ek,
})
// GORSEL's three active homework, two due today (the first is the next thing), and one of each settled kind.
const ZENGIN = { summary: '', homework: [
  ...(GORSEL.homework as { homework: unknown[] }).homework,
  hw('Türkçe', 'OKUMA GÜNLÜĞÜ 3. HAFTA', '24.09.2026 18:00'),
  hw('Bilişim', 'Algoritma çizimi', '24.09.2026 17:00'),
  hw('Sosyal Bilgiler', 'Harita çalışması', '20.09.2026 12:00', { 'Ödev Durumu': 'Yaptı' }),
  hw('İngilizce', 'Unit 2 kelime testi', '19.09.2026 12:00', { 'Ödev Durumu': 'Yapmadı' }),
  hw('Din Kültürü', 'Sunum hazırlığı', '22.09.2026 12:00', { student_marked_done: true }),
  hw('Görsel Sanatlar', 'Eskiz', '21.09.2026 12:00'),
] }

async function zenginAc(page: Page, w = 1440, h = 900, ek: Record<string, unknown> = {}) {
  await page.clock.setFixedTime(new Date(SABIT_SAAT))
  await mock(page, { ...GORSEL, homework: ZENGIN, ...ek })
  await page.setViewportSize({ width: w, height: h })
  await page.goto('/isler')
  await expect(page.locator('.next-thing')).toBeVisible()
  await page.evaluate(() => document.fonts.ready.then(() => undefined))
}

const gruplariAc = async (page: Page) => {
  for (const ad of [/^Yapılan/, /^Tamamlandı/, /^Yapılmayan/]) await page.getByRole('button', { name: ad }).click()
}

test('the next thing is named once: it is not repeated in the list', async ({ page }) => {
  await sabitAc(page, '/isler', 1440, 900)
  const kart = page.locator('.next-thing')
  await expect(kart).toContainText('2. HAFTA MATEMATİK HAFTA İÇİ ÖDEVİ')
  await expect(page.locator('.isler-liste').filter({ hasText: '2. HAFTA MATEMATİK' })).toHaveCount(0)
  // The rest follows in deadline order, under "Ayrıca" — Bugün's word for the same thing (İ9).
  const satirlar = page.locator('.isler-liste--sonra .homework-item')
  await expect(satirlar).toHaveCount(2)
  await expect(satirlar.nth(0)).toContainText('S1 Les verbes')
  await expect(satirlar.nth(1)).toContainText('Ödev (Hibrit 10-16)')
  await expect(page.getByRole('heading', { name: 'Ayrıca 2' })).toBeVisible()
  // The panel says when it is owed, as Bugün's card does (İ2).
  await expect(kart).toContainText('Teslim yarın 12:00')
})

for (const [ad, w, h] of [['masaüstü', 1440, 900], ['telefon', 390, 844]] as const) {
  test(`one primary button on the page (${ad})`, async ({ page }) => {
    await zenginAc(page, w, h)
    await gruplariAc(page)
    await expect(page.locator('.cds--btn--primary:visible')).toHaveCount(1)
    await expect(page.locator('.next-thing').getByRole('button', { name: 'Başla' })).toHaveClass(/cds--btn--primary/)
  })
}

test('a row is one control that opens the work, plus one "Yaptım"; keyboard reaches both', async ({ page }) => {
  await zenginAc(page)
  const satir = page.locator('.isler-liste--sonra .homework-item').filter({ hasText: 'S1 Les verbes' })
  // Carbon's clickable item: the whole row is a button; the action sits beside it, never inside it.
  const ac = satir.locator('.cds--contained-list-item__content')
  await expect(ac).toHaveJSProperty('tagName', 'BUTTON')
  await expect(ac.locator('button')).toHaveCount(0)
  await expect(ac.locator('.ted-subject-label__mark')).toHaveCount(1)
  await expect(ac.locator('.isler-satir__teslim')).toHaveText('Pazartesi 08:55')
  const yaptim = satir.getByRole('button', { name: 'Yaptım', exact: true })
  await expect(yaptim).toHaveCount(1)
  await expect(satir.getByRole('button')).toHaveCount(2)
  // "Yaptım" repeats on every row; it says which row it belongs to ([3.8-6]).
  await expect(yaptim).toHaveAccessibleDescription('Fransızca — S1 Les verbes')
  // No countdown chip, no bar pretending to be data, no left status edge.
  await expect(page.locator('main .cds--tag', { hasText: /\d+g \d+s/ })).toHaveCount(0)
  await expect(page.locator('.hw-countdown-bar, main [role="progressbar"]')).toHaveCount(0)

  await ac.focus()
  await page.keyboard.press('Tab')
  await expect(yaptim).toBeFocused()
  await page.keyboard.press('Shift+Tab')
  await expect(ac).toBeFocused()
  await page.keyboard.press('Enter')
  const pencere = page.getByRole('dialog')
  await expect(pencere.getByRole('heading', { name: 'S1 Les verbes' })).toBeVisible()
  // First focus is "Kapat", whose Carbon tooltip takes the first Escape; the next one closes the window.
  await expect(pencere.getByRole('button', { name: 'Kapat', exact: true })).toBeFocused()
  await expect(async () => {
    await page.keyboard.press('Escape')
    await expect(pencere).toHaveCount(0, { timeout: 500 })
  }).toPass({ timeout: 5000 })
  // Focus goes back to the row it was opened from ([3.8-8]).
  await expect(ac).toBeFocused()
})

test('red is spent only on work due today, as an icon and a word', async ({ page }) => {
  await zenginAc(page)
  await gruplariAc(page)
  const acil = page.locator('.isler-satir__teslim--bugun')
  await expect(acil).toHaveCount(1)
  await expect(acil).toHaveText('Bugün 18:00')
  await expect(acil.locator('svg')).toHaveCount(1)
  await expect(page.locator('.homework-item', { has: acil })).toContainText('OKUMA GÜNLÜĞÜ 3. HAFTA')
  const renk = await acil.evaluate(el => ({
    yazi: getComputedStyle(el).color,
    ikon: getComputedStyle(el.querySelector('svg')!).fill,
  }))
  expect(renk.yazi).toBe('rgb(162, 25, 31)')   // --ted-text-error, red-70
  expect(renk.ikon).toBe('rgb(218, 30, 40)')   // --ted-support-error, red-60
  // Settled work carries no expiry alarm, and a group's own name is not repeated as a tag on its rows (İ6).
  await expect(page.getByText('Süresi doldu')).toHaveCount(0)
  await expect(page.locator('.isler-liste--yapilan .cds--tag')).toHaveCount(0)
  await expect(page.locator('.isler-liste--tamamlanan .cds--tag')).toHaveCount(0)
  // Where the group holds more than one verdict, the teacher's word stays, with its icon.
  await expect(page.locator('.isler-liste--yapilmayan .cds--tag', { hasText: 'Yapmadı' }).locator('svg')).toHaveCount(1)
})

test('only figures are set in mono', async ({ page }) => {
  await zenginAc(page)
  await gruplariAc(page)
  const monolar = await page.locator('main .tedy-time').allInnerTexts()
  expect(monolar.length).toBeGreaterThan(5)
  for (const m of monolar) expect(m, m).toMatch(/^[\d:.\-–\s]+$/)
  const yazilar = await page.locator('.isler-satir__teslim, .exams-ahead__when').evaluateAll(els =>
    els.map(el => getComputedStyle(el).fontFamily))
  for (const f of yazilar) expect(f).toMatch(/^"?IBM Plex Sans/)
  await expect(page.locator('.exams-ahead__row').first()).toContainText('1 Eki 09:00 · 7 gün sonra')
})

test('exams: the same list, and "Tüm sınavlar" in the list header', async ({ page, context }) => {
  await sabitAc(page, '/isler', 1440, 900)
  const liste = page.locator('.isler-liste.exams-ahead')
  // A heading that names a section is title case (S38, revised 2026-10-19).
  await expect(liste.getByRole('heading', { name: 'Yaklaşan Sınavlar 2' })).toBeVisible()
  const tum = liste.locator('.cds--contained-list__header').getByRole('link', { name: 'Tüm sınavlar' })
  await expect(tum).toHaveClass(/cds--btn--ghost/)
  // C13: a new-tab click is the browser's — the page stays where it is.
  const [yeni] = await Promise.all([context.waitForEvent('page'), tum.click({ modifiers: ['ControlOrMeta'] })])
  await yeni.close()
  await expect(page).toHaveURL(/\/isler$/)
  await tum.click()
  await expect(page).toHaveURL(/\/sinavlar$/)
})

// What main added to the exam rows after 2026-10-15 lives in the redesigned row: an all-day exam is its day
// with no invented hour (C11, C20), a week-only one says its week, a timed one its day and hour.
test('an exam row says its day the way the exam page does', async ({ page }) => {
  const sinav = (id: string, title: string, date: string | null, ek: Record<string, unknown> = {}) => ({
    id, title, rawTitle: title, course: 'Fen Bilimleri', courseFamily: 'teal', courseColor: '#007d79', date,
    endDate: null, allDay: false, status: 'upcoming', grade: null, examNumber: null, relatedContent: [],
    relatedHomework: [], ...ek,
  })
  await zenginAc(page, 1440, 900, { exams: { exams: [
    sinav('gun', 'Fen Bilimleri KTT', '2026-09-28', { allDay: true }),
    sinav('saat', 'Fen Bilimleri yazılı', '2026-09-25T09:40:00'),
    sinav('hafta', 'Fen Bilimleri quiz', null, { hafta: '2026-09-28', tarihBelirsiz: true }),
  ], stats: { upcoming: 3, past: 0, averageGrade: null }, tespit: null } })
  const satir = (ad: string) => page.locator('.exams-ahead__row', { hasText: ad }).locator('.exams-ahead__when')
  await expect(satir('KTT')).toHaveText('Pazartesi')
  await expect(satir('yazılı')).toHaveText('Yarın 09:40')
  await expect(satir('quiz')).toHaveText('28 Eyl haftası')
})

test('settled groups start closed, name their size, and open by keyboard', async ({ page }) => {
  await zenginAc(page)
  for (const [ad, n] of [['Yapılan', 1], ['Tamamlandı', 1], ['Yapılmayan', 2]] as const) {
    const dugme = page.getByRole('button', { name: `${ad} ${n}` })
    await expect(dugme).toHaveAttribute('aria-expanded', 'false')
    const hedef = await dugme.getAttribute('aria-controls')
    await expect(page.locator(`#${hedef}`)).toHaveCount(1)
    await expect(page.getByRole('heading', { name: `${ad} ${n}` })).toBeVisible()
    await dugme.focus()
    await page.keyboard.press('Enter')
    await expect(dugme).toHaveAttribute('aria-expanded', 'true')
    await expect(page.locator(`#${hedef} .homework-item`)).toHaveCount(n)
  }
})

test('"Başla" opens the work, and "Yaptım" lives in that window too', async ({ page }) => {
  await zenginAc(page)
  await page.route('**/api/homework/mark-done', r => r.fulfill(json({ ok: true })))
  await page.getByRole('button', { name: 'Başla' }).click()
  const pencere = page.getByRole('dialog')
  await expect(pencere.getByRole('heading', { name: 'Algoritma çizimi' })).toBeVisible()
  await pencere.getByRole('button', { name: 'Yaptım', exact: true }).click()
  await expect(pencere).toHaveCount(0)
  const not = page.locator('.isler-yaptin')
  await expect(not).toContainText('Yaptın: Bilişim — Algoritma çizimi')
  await expect(page.locator('.yaptin-satiri__metin')).toBeFocused()
})

test('a "Yaptım" that fails in the window says so there, and the window stays', async ({ page }) => {
  await zenginAc(page)
  await page.route('**/api/homework/mark-done', r => r.fulfill({ status: 500, body: '{}' }))
  await page.getByRole('button', { name: 'Başla' }).click()
  const pencere = page.getByRole('dialog')
  await pencere.getByRole('button', { name: 'Yaptım', exact: true }).click()
  await expect(pencere.getByRole('alert')).toContainText('Kaydedilemedi')
  await expect(pencere.getByRole('button', { name: 'Yaptım', exact: true })).toBeVisible()
})

test('loading shows the page’s shape after 400 ms; a failed load says so in words', async ({ page }) => {
  await page.clock.setFixedTime(new Date(SABIT_SAAT))
  await mock(page, GORSEL)
  await page.route('**/api/homework', async r => { await new Promise(t => setTimeout(t, 2000)); await r.fulfill(json(ZENGIN)) })
  await page.goto('/isler')
  await expect(page.locator('.isler[aria-busy="true"] .cds--skeleton__text').first()).toBeVisible()
  await expect(page.getByText('Şu an teslim bekleyen bir işin yok.')).toHaveCount(0)
  await expect(page.locator('.next-thing')).toBeVisible()

  await page.unroute('**/api/homework')
  await page.route('**/api/homework', r => r.fulfill({ status: 500, contentType: 'application/json', body: '{}' }))
  await page.reload()
  const hata = page.locator('.isler').getByRole('alert')
  await expect(hata).toContainText('Ödevler yüklenemedi')
  await expect(hata).not.toContainText('HTTP')
  // A failure is not an empty list (D3).
  await expect(page.getByText('Şu an teslim bekleyen bir işin yok.')).toHaveCount(0)
})

test('on a phone every control on the page is at least 44px', async ({ page }) => {
  await zenginAc(page, 390, 844)
  await gruplariAc(page)
  const kucuk = await page.locator('main').evaluate(main =>
    Array.from(main.querySelectorAll<HTMLElement>('button, a[href], [role="button"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({ ad: (el.textContent || el.getAttribute('aria-label') || el.tagName).trim().slice(0, 40),
        r: el.getBoundingClientRect() }))
      .filter(({ r }) => r.height < 44 || r.width < 44)
      .map(({ ad, r }) => `${ad}: ${Math.round(r.width)}×${Math.round(r.height)}`))
  expect(kucuk).toEqual([])
})

for (const [ad, w, h] of [['masaüstü', 1440, 900], ['telefon', 390, 844]] as const) {
  test(`axe and IBM Equal Access find nothing, groups open (${ad})`, async ({ page }) => {
    await zenginAc(page, w, h)
    await gruplariAc(page)
    const { violations } = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'])
      .analyze()
    expect(violations.map(v => `${v.id}: ${v.nodes.slice(0, 3).map(n => n.target.join(' ')).join(' | ')}`)).toEqual([])
    await page.addScriptTag({ path: createRequire(import.meta.url).resolve('accessibility-checker-engine/ace.js') })
    const ihlal: string[] = await page.evaluate(async () => {
      // @ts-expect-error — `ace` is the injected engine's global
      const rapor = await new window.ace.Checker().check(document, ['IBM_Accessibility'])
      return rapor.results
        .filter((s: { value: string[] }) => s.value[0] === 'VIOLATION' && s.value[1] === 'FAIL')
        .map((s: { ruleId: string; snippet: string }) => `${s.ruleId}: ${s.snippet.slice(0, 120)}`)
    })
    expect(ihlal).toEqual([])
  })
}

for (const [w, h] of [[320, 640], [390, 844], [1440, 900], [3840, 2160]] as const) {
  test(`nothing scrolls sideways at ${w}px`, async ({ page }) => {
    await zenginAc(page, w, h)
    await gruplariAc(page)
    const tasma = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
    expect(tasma).toBeLessThanOrEqual(0)
  })
}
