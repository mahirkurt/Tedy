import { test, expect } from '@playwright/test'
import type { Page, Route } from '@playwright/test'
import { mockSohbetler } from './_audit-fixtures'
import { asistanAc, sor, sonCevap } from './_asistan-carbon'

// Eski assistant-moduller.spec.ts'in testleri, aynı adlarla (Görev 19). Kaynak paneli aynı bileşen (SourcePanel),
// cevabın altbilgisindeki "Kaynak ayrıntıları" ile açılan çalışma alanında; araç adımı Carbon'un adım bileşeninde.

test.beforeEach(async ({ page }) => { await mockSohbetler(page) })

// Sub-project 5. A module citation links to the dashboard's own module route, and only that
// route fetches a viewing ticket (spec §5.4). Every absence below follows proof that the surface
// it is absent from rendered, and every fixture is counted before it is trusted (TEDY traps 3-5).
// The stream endpoint is aborted or fulfilled in-browser in every test, so no request reaches
// the real dashboard's Gemini key.

const json = (body: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
const TICKET = 'a'.repeat(64)

const MODULE_CITATION = {
  id: 'S1', kind: 'modul', label: 'Maddenin Hâlleri · Fen Bilimleri 5. Sınıf · v2',
  locator: { slug: 'fen5-su', version: 2 }, snippet: 'QUIZ · FB.5.4.1.1 · yayın 2026-09-14', confidence: 1,
}

function answer(citations: unknown[], text = 'Bu konu için yayınlanmış bir modül var [S1].', degraded: string[] = []) {
  return {
    answer: text, citations, safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
    meta: { model: 'claude-sonnet-5', degraded, dropped_citations: 0 },
  }
}

async function ask(page: Page, prompt: string) {
  await asistanAc(page)
  await sor(page, prompt)
}
async function kaynaklar(page: Page) {
  await expect(page.getByRole('button', { name: 'Kaynaklar', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Kaynak ayrıntıları' }).click()
}

test('a module citation gets its own group and opens only through the ticketed module route', async ({ page }) => {
  let ticketCalls = 0
  const viewerRequests: string[] = []
  await page.route('**/api/assistant/stream', route => route.abort())
  await page.route('**/api/assistant/chat', route => route.fulfill(json(answer([MODULE_CITATION]))))
  await page.route('**/api/modules/fen5-su/v2/ticket', route => {
    ticketCalls += 1
    return route.fulfill(json({
      url: `https://modul.tedy.online/m/fen5-su/v2?t=${TICKET}&e=1&u=${'b'.repeat(32)}`, exp: 1,
    }))
  })
  await page.route('**/api/modules/fen5-su/progress**', route => route.fulfill(json({
    state: { answers: [], done: [], xp: 0 },
  })))
  await page.route('https://modul.tedy.online/**', (route: Route) => {
    viewerRequests.push(route.request().url())
    return route.fulfill({
      status: 200, contentType: 'text/html; charset=utf-8',
      body: '<!doctype html><html lang="tr"><body><p class="modul-yuklendi">modül</p></body></html>',
    })
  })

  await ask(page, 'maddenin hâlleri için modül var mı')

  // Atıf Carbon'un kaynak düğmesinde; ayrıntı paneli açılır.
  await kaynaklar(page)
  const group = page.locator('.ac__ref-group--modul')
  await expect(group.locator('.ac__ref-group-title')).toHaveText('Yayınlanmış modül')
  await expect(group.locator('.ac__ref-path')).toHaveText('Maddenin Hâlleri · Fen Bilimleri 5. Sınıf · v2')
  const open = group.locator('a.ac__ref-open')
  await expect(open).toHaveText('Modülü aç')
  await expect(open).toHaveAttribute('href', '/moduller/fen5-su/v2')

  // Rendering an answer must neither mint a ticket nor touch the viewer host.
  expect(ticketCalls).toBe(0)
  expect(viewerRequests).toEqual([])

  await open.click()
  await expect(page).toHaveURL(/\/moduller\/fen5-su\/v2$/)
  await expect(page.frameLocator('iframe.module-frame').locator('.modul-yuklendi')).toHaveText('modül')
  expect(ticketCalls).toBeGreaterThanOrEqual(1)
  expect(viewerRequests[0]).toContain(`t=${TICKET}`)
})

test('a module citation with an unsafe locator renders without a link', async ({ page }) => {
  await page.route('**/api/assistant/stream', route => route.abort())
  await page.route('**/api/assistant/chat', route => route.fulfill(json(answer([
    { ...MODULE_CITATION, id: 'S1', label: 'Kaçak yol', locator: { slug: '../x', version: 2 } },
    { ...MODULE_CITATION, id: 'S2', label: 'Taslak yolu', locator: { slug: 'taslak', version: 1 } },
    { ...MODULE_CITATION, id: 'S3', label: 'Metin sürüm', locator: { slug: 'fen5-su', version: '2' } },
  ], 'Üç bozuk atıf [S1] [S2] [S3].'))))

  await ask(page, 'bozuk modül atıfları')

  await kaynaklar(page)
  const items = page.locator('.ac__ref-group--modul .ac__ref-item')
  await expect(items).toHaveCount(3)
  await expect(items.locator('.ac__ref-path')).toHaveText(['Kaçak yol', 'Taslak yolu', 'Metin sürüm'])
  await expect(items.locator('.ac__ref-unlinked')).toHaveText(
    ['Bağlantı kurulamadı', 'Bağlantı kurulamadı', 'Bağlantı kurulamadı'])
  await expect(page.locator('.ac__ref-group--modul a')).toHaveCount(0)
})

test('while modul_ara runs, the thinking indicator names it', async ({ page }) => {
  let releaseClassic: () => void = () => {}
  const classicHeld = new Promise<void>(resolve => { releaseClassic = resolve })
  // The stream narrates modul_ara and closes without an answer, so the component falls back to
  // the classic endpoint while the stage label is still set. Holding that request open keeps
  // the label on screen for a condition-based assertion (plan K-S13) — no fixed wait.
  await page.route('**/api/assistant/stream', route => route.fulfill({
    status: 200, contentType: 'text/event-stream',
    body: 'event: tool_start\ndata: {"name":"modul_ara"}\n\n',
  }))
  await page.route('**/api/assistant/chat', async route => {
    await classicHeld
    await route.fulfill(json(answer([MODULE_CITATION])))
  })

  await ask(page, 'modül var mı')
  await expect(page.getByText('Yayınlanmış modüller aranıyor', { exact: true }).filter({ visible: true }).first()).toBeVisible()
  releaseClassic()
  await expect(page.getByRole('button', { name: 'Kaynaklar', exact: true })).toBeVisible()
  await expect(sonCevap(page)).toContainText('Bu konu için yayınlanmış bir modül var')
})

test('an unreadable module catalog is named, not hidden', async ({ page }) => {
  await page.route('**/api/assistant/stream', route => route.abort())
  await page.route('**/api/assistant/chat', route => route.fulfill(json(
    answer([], 'Modül kataloğunu şu an okuyamadım.', ['modul-katalogu']))))

  await ask(page, 'modül var mı')

  const degraded = page.locator('[data-tedy-altbilgi]').filter({ visible: true }).last()
  await expect(degraded.locator('.cds--tag')).toHaveCount(1)
  await expect(degraded).toContainText('Modül kataloğu okunamadı')
  await expect(degraded).not.toContainText('modul-katalogu')
})
