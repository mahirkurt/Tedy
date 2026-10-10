import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { json } from './_audit-fixtures'
import { OGRETMENLER } from './_gorsel-fixtures'
import { carbonSabitAc as sabitAc, ogretmenSec, ogretmenSecimi, soruAlani, sonCevap } from './_asistan-carbon'

// Öğretmen modları (spec §1, plan B1): the selector, its memory, each teacher's
// theme, greeting and quick prompts, and the request carrying the mode.

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

// The fixture's auth/me is test@tedy.online, a family member (student: false).
const ANAHTAR = 'tedy-asistan-ogretmen::test@tedy.online'
// S35 (B68, Asistan yenilemesi 2026-10-10): the send button keeps Carbon's action blue (blue-60) in every
// mode; the subject's colour lives only on the chat frame's edge and the reader's own bubble.
const MAVI = 'rgb(15, 98, 254)'
const KIPLER = ['genel', 'turkce', 'fen', 'sosyal', 'matematik']
// The frame's 4px top edge: the family's accent (the -60 palette step, theme/_subjects.scss).
const KENAR: Record<string, string> = {
  turkce: 'rgb(208, 38, 112)',
  fen: 'rgb(0, 125, 121)',
  sosyal: 'rgb(0, 114, 195)',
  matematik: 'rgb(138, 63, 252)',
}
const ADLAR = ['Genel', 'Türkçe', 'Fen', 'Sosyal', 'Matematik']

// A canned answer: no test here may let a question reach the real model.
function cevap(extra: Record<string, unknown> = {}) {
  return {
    answer: 'Oran, iki çokluğun bölme yoluyla karşılaştırılmasıdır.', citations: [], safety_flags: [],
    plan_blocks: [], intent: 'qa', session_id: '',
    meta: { model: 'claude-sonnet-5', degraded: [], ogretmen: 'genel' }, ...extra,
  }
}

async function hatirla(page: Page, id: string) {
  await page.addInitScript(([k, v]) => localStorage.setItem(k, v), [ANAHTAR, id])
}

async function asistan(page: Page, w = 1440, h = 900) {
  await sabitAc(page, '/asistan', w, h)
  await expect(ogretmenSecimi(page)).toBeVisible()
}

const kok = (page: Page) => page.locator('section.asistan')

test('one Dropdown, five teachers in order, Genel chosen at first', async ({ page }) => {
  await asistan(page)
  // One control, labelled "Öğretmen", on the line under the chat's title (the radio chips are gone).
  await expect(page.getByRole('radio')).toHaveCount(0)
  await expect(page.getByText('Öğretmen', { exact: true }).first()).toBeVisible()
  await expect(ogretmenSecimi(page)).toContainText('Genel')
  await ogretmenSecimi(page).click()
  const secenekler = page.getByRole('option')
  await expect(secenekler).toHaveCount(5)
  for (const [i, ad] of ADLAR.entries()) await expect(secenekler.nth(i)).toHaveText(ad)
  await expect(kok(page)).toHaveAttribute('data-ogretmen', 'genel')
  // The title is the teacher; the product name is not repeated.
  await expect(page.getByText('Genel asistan', { exact: true }).first()).toBeAttached()
})

test('the keyboard opens the list and chooses, and the choice is remembered', async ({ page }) => {
  await asistan(page)
  await ogretmenSecimi(page).focus()
  // Carbon Dropdown (downshift select): ArrowDown opens the list on the chosen teacher, Enter chooses.
  await page.keyboard.press('ArrowDown')
  await expect(page.getByRole('option')).toHaveCount(5)
  await page.keyboard.press('ArrowDown')
  await page.keyboard.press('ArrowDown')
  await page.keyboard.press('Enter')
  await expect(ogretmenSecimi(page)).toContainText('Fen')
  await expect(ogretmenSecimi(page)).toBeFocused()
  await expect(kok(page)).toHaveAttribute('data-ogretmen', 'fen')
  expect(await page.evaluate(k => localStorage.getItem(k), ANAHTAR)).toBe('fen')
  await page.reload()
  await expect(ogretmenSecimi(page)).toContainText('Fen')
})

test('on a phone the selector is one row of at least 44px', async ({ page }) => {
  await asistan(page, 390, 844)
  const kutu = await ogretmenSecimi(page).boundingBox()
  expect(kutu!.height).toBeGreaterThanOrEqual(44)
  const satir = await page.locator('.asistan__ogretmen').boundingBox()
  expect(satir!.height).toBeLessThan(70)
})

for (const id of KIPLER) {
  test(`${id}: the frame follows the teacher, the send button and the brand band do not`, async ({ page }) => {
    await asistan(page)
    const bant = await page.locator('.cds--header').evaluate(el => getComputedStyle(el).backgroundColor)
    if (id !== 'genel') await ogretmenSec(page, ADLAR[KIPLER.indexOf(id)])
    await expect(kok(page)).toHaveAttribute('data-ogretmen', id)
    // A disabled button draws Carbon's disabled fill; type to enable it. expect.poll retries: Carbon's button
    // eases its fill in from the disabled grey.
    await soruAlani(page).fill('x')
    // Carbon AI Chat'in gönder düğmesi bir simge düğmesi; simgenin dolgusu --cds-interactive: her kipte mavi (S35).
    await expect.poll(() => page.getByRole('button', { name: 'Gönder', exact: true }).evaluate(b => {
      // Düğme cds-button'ın gölge kökünde; simge o öğenin ışık DOM'unda (slot="icon"). Boyanan dolgu ölçülür.
      const svg = (b.getRootNode() as ShadowRoot).host?.querySelector('svg[slot="icon"]')
      return svg ? getComputedStyle(svg).fill : 'simge yok'
    })).toBe(MAVI)
    const kenar = await page.locator('.asistan__sohbet').evaluate(el => getComputedStyle(el).borderTopColor)
    if (id === 'genel') expect(await page.locator('.asistan__sohbet').evaluate(el => getComputedStyle(el).borderTopWidth)).toBe('0px')
    else expect(kenar).toBe(KENAR[id])
    expect(await page.locator('.cds--header').evaluate(el => getComputedStyle(el).backgroundColor)).toBe(bant)
  })
}

test('a teacher brings its own greeting and quick prompts', async ({ page }) => {
  await hatirla(page, 'matematik')
  await asistan(page)
  const mat = OGRETMENLER.ogretmenler[3]
  await expect(page.locator('.asistan__karsilama-metni')).toContainText(mat.karsilama.aile)
  await expect(page.locator('.asistan__hizli-sorular button')).toHaveText(mat.hizli_sorular.aile.slice(0, 3))
  // The chat's title is the teacher's name (header title; no product name, no subtitle).
  await expect(page.getByText('Matematik öğretmeni', { exact: true }).first()).toBeAttached()
  // None of the quick questions is a primary button: the screen's one primary action is "Gönder" (S12).
  await expect(page.locator('.asistan__hizli-sorular .cds--btn--primary')).toHaveCount(0)
})

test('a remembered teacher that no longer exists reads as Genel', async ({ page }) => {
  await hatirla(page, 'tarih')
  await asistan(page)
  await expect(ogretmenSecimi(page)).toContainText('Genel')
  await expect(kok(page)).toHaveAttribute('data-ogretmen', 'genel')
})

test('the request carries the chosen teacher', async ({ page }) => {
  await hatirla(page, 'fen')
  await asistan(page)
  // Both answered here: an unanswered stream falls back to /chat, and /chat
  // must never reach the real model.
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/assistant/chat', r => r.fulfill(json(cevap())))
  const akis = page.waitForRequest('**/api/assistant/stream')
  const klasik = page.waitForRequest('**/api/assistant/chat')
  await soruAlani(page).fill('Mercek nedir?')
  await page.getByRole('button', { name: 'Gönder' }).click()
  expect((await akis).postDataJSON().ogretmen).toBe('fen')
  expect((await klasik).postDataJSON().ogretmen).toBe('fen')
})

test('a list that failed says so and Genel still works', async ({ page }) => {
  await sabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/ogretmenler', r => r.fulfill({ status: 503, body: '{}' }))
  await page.reload()
  await expect(page.getByText('Öğretmen modları şu an yüklenemedi; Genel modda sorabilirsiniz.')).toBeVisible()
  await ogretmenSecimi(page).click()
  await expect(page.getByRole('option')).toHaveCount(1)
})

test('a stale list plus a transient error shows the list, not the banner', async ({ page }) => {
  // Final-fix item 8: useOgretmen's `hata` must gate on an empty list, not
  // merely on useApi's `error` — useApi keeps the previous successful `data`
  // on a failed poll (see useApi.ts), so a transient failure after a good
  // load must not show "yüklenemedi" over a list that is still right there.
  await asistan(page)
  await ogretmenSecimi(page).click()
  await expect(page.getByRole('option')).toHaveCount(5)
  await page.keyboard.press('Escape')
  await page.route('**/api/assistant/ogretmenler', r => r.fulfill({ status: 500, body: '{}' }))
  const yenidenIstek = page.waitForResponse('**/api/assistant/ogretmenler')
  // useApi refetches on this event (homework updates use the same poll hook
  // family); it is the one way to force a re-poll without the real 5-minute
  // interval.
  await page.evaluate(() => window.dispatchEvent(new Event('tedy:homework-updated')))
  await yenidenIstek
  await ogretmenSecimi(page).click()
  await expect(page.getByRole('option')).toHaveCount(5)
  await expect(page.getByText('Öğretmen modları şu an yüklenemedi; Genel modda sorabilirsiniz.')).toHaveCount(0)
})

// ── mod_oner: a suggestion is a button, never a switch ─────────────────────

const ONERI = {
  ogretmen: 'matematik', ogretmen_adi: 'Matematik öğretmeni',
  soru: 'Matematik öğretmenine geçelim mi?',
  gerekce: 'Bu bir oran-orantı sorusu; Matematik öğretmeni adım adım çözer.',
  renk_ailesi: 'purple',
}


const sse = (...olaylar: [string, unknown][]) =>
  olaylar.map(([ad, veri]) => `event: ${ad}\ndata: ${JSON.stringify(veri)}\n\n`).join('')

async function sor(page: Page) {
  await soruAlani(page).fill('Oran nedir?')
  await page.getByRole('button', { name: 'Gönder' }).click()
  // Öneri kartı cevaptan sonra ayrı bir mesajdır: cevabı taşıyan görünür mesaj beklenir.
  await expect(page.locator('.cds-aichat--assistant-message').filter({ visible: true })
    .filter({ hasText: 'Oran, iki çokluğun' })).toHaveCount(1)
}

test('a suggestion from the stream shows a button and changes nothing by itself', async ({ page }) => {
  await asistan(page)
  // Both answered here (Global Constraint): an unanswered stream falls back
  // to /chat, and /chat must never reach the real model.
  await page.route('**/api/assistant/stream', r => r.fulfill({
    status: 200, contentType: 'text/event-stream',
    body: sse(['tool_start', { name: 'mod_oner' }], ['tool_end', { name: 'mod_oner', ok: true }],
      ['mode_suggestion', ONERI], ['answer', { payload: cevap() }], ['done', {}]),
  }))
  await page.route('**/api/assistant/chat', r => r.fulfill(json(cevap({ mode_suggestion: ONERI }))))
  await sor(page)
  const dugme = page.getByRole('button', { name: 'Matematik öğretmenine geçelim mi?' })
  await expect(dugme).toBeVisible()
  // exact: Carbon'un aria-live duyurucusu cevap metnini biriktirir.
  await expect(page.getByText(ONERI.gerekce, { exact: true })).toBeVisible()
  // Nothing switched on its own.
  await expect(kok(page)).toHaveAttribute('data-ogretmen', 'genel')
  await expect(ogretmenSecimi(page)).toContainText('Genel')
  expect(await page.evaluate(k => localStorage.getItem(k), ANAHTAR)).toBeNull()

  await dugme.click()
  await expect(kok(page)).toHaveAttribute('data-ogretmen', 'matematik')
  await expect(ogretmenSecimi(page)).toContainText('Matematik')
  expect(await page.evaluate(k => localStorage.getItem(k), ANAHTAR)).toBe('matematik')
  await expect(dugme).toHaveCount(0)          // in a teacher mode there is nothing to suggest
})

test('keyboard activation of the suggestion focuses that teacher', async ({ page }) => {
  await asistan(page)
  // Both answered here (Global Constraint): an unanswered stream falls back
  // to /chat, and /chat must never reach the real model.
  await page.route('**/api/assistant/stream', r => r.fulfill({
    status: 200, contentType: 'text/event-stream',
    body: sse(['tool_start', { name: 'mod_oner' }], ['tool_end', { name: 'mod_oner', ok: true }],
      ['mode_suggestion', ONERI], ['answer', { payload: cevap() }], ['done', {}]),
  }))
  await page.route('**/api/assistant/chat', r => r.fulfill(json(cevap({ mode_suggestion: ONERI }))))
  await sor(page)
  const dugme = page.getByRole('button', { name: 'Matematik öğretmenine geçelim mi?' })
  await dugme.focus()
  await page.keyboard.press('Enter')
  // The button disappears with the switch; focus goes to the teacher selector, which reads the new teacher.
  await expect(ogretmenSecimi(page)).toContainText('Matematik')
  await expect(ogretmenSecimi(page)).toBeFocused()
})

test('the classic endpoint carries the suggestion too', async ({ page }) => {
  await asistan(page)
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/assistant/chat', r => r.fulfill(json(cevap({ mode_suggestion: ONERI }))))
  await sor(page)
  await expect(page.getByRole('button', { name: 'Matematik öğretmenine geçelim mi?' })).toBeVisible()
  await expect(kok(page)).toHaveAttribute('data-ogretmen', 'genel')
})

test('no suggestion, no button', async ({ page }) => {
  await asistan(page)
  // Both answered here (Global Constraint): an unanswered stream falls back
  // to /chat, and /chat must never reach the real model.
  await page.route('**/api/assistant/stream', r => r.fulfill({
    status: 200, contentType: 'text/event-stream',
    body: sse(['answer', { payload: cevap() }], ['done', {}]),
  }))
  await page.route('**/api/assistant/chat', r => r.fulfill(json(cevap())))
  await sor(page)
  await expect(sonCevap(page)).toContainText('Oran, iki çokluğun')
  await expect(page.locator('.ac-msg__oneri')).toHaveCount(0)
})
