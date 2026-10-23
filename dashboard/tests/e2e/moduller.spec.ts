import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { execFileSync } from 'node:child_process'
import { createRequire } from 'node:module'
import { mkdtempSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

// Spec §5.4-§5.5 and §11. The iframe content is the real compiler's QUIZ output (real engine patches,
// real gates), served for https://modul.tedy.online by page.route under the spec CSP — only
// frame-ancestors is pointed at this test origin. No network is used.

const PORT = Number(process.env.TEDY_E2E_PORT ?? 8286)
const ORIGIN = `http://127.0.0.1:${PORT}`
const REPO = fileURLToPath(new URL('../../..', import.meta.url))
const PYTHON = process.env.TEDY_E2E_PYTHON ?? join(REPO, '.venv/bin/python')
const SPEC_CSP = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; " +
  "font-src data:; media-src data:; connect-src 'none'; frame-ancestors https://tedy.online; base-uri 'none'; form-action 'none'"
const FRAME_CSP = 'frame-src https://modul.tedy.online https://accounts.google.com'
const json = (b: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(b) })
const ACE = createRequire(import.meta.url).resolve('accessibility-checker-engine/ace.js')
// The shape /api/modules/…/aciklama answers (src/dashboard_api.py _module_explanation).
const ACIKLAMA = {
  baslik: 'Maddenin Hâlleri', ders: 'Fen Bilimleri', sinif: '5. Sınıf', kazanimlar: ['FB.5.4.1.1'],
  kitap: { ad: 'Fen Bilimleri 5', sayfalar: '112-120' }, iddia_durumu: 'ok',
  iddialar: [{ iddia: 'Madde katı, sıvı ve gaz hâllerinde bulunur.', sayfa: 112, kaynak: null }],
  medya: { yapay_zeka: 1, ders_kitabi: 2, fotograf_arsivi: 0 },
}

type Segment = { id: string; type: string; questions?: { correctIndex: number }[] }
let moduleHtml = ''
let quiz: { meta: { title: string }; segments: Segment[] }
let clozeHtml = ''
let asamaliHtml = ''

test.beforeAll(() => {
  const out = join(mkdtempSync(join(tmpdir(), 'tedy-modul-')), 'quiz.html')
  execFileSync(PYTHON, ['-m', 'src.mcp_server.derleme', '--ornek', 'QUIZ', '--cikti', out, '--ebeveyn-origin', ORIGIN],
    { cwd: REPO })
  moduleHtml = readFileSync(out, 'utf8')
  // A module that opens on the template's fill-in-the-blank segment (B42): the real compiler and gates.
  const dir = mkdtempSync(join(tmpdir(), 'tedy-cloze-'))
  execFileSync(PYTHON, ['-c', [
    'import json, sys', 'from src.mcp_server.ornekler import ornek, demo',
    "d = ornek('QUIZ'); fb = next(s for s in demo()['segments'] if s['type'] == 'fillblank')",
    "d['segments'] = [fb] + d['segments']", "open(sys.argv[1], 'w').write(json.dumps(d, ensure_ascii=False))",
  ].join('\n'), join(dir, 'cloze.json')], { cwd: REPO })
  execFileSync(PYTHON, ['-m', 'src.mcp_server.derleme', '--girdi', join(dir, 'cloze.json'), '--cikti', join(dir, 'cloze.html'),
    '--ebeveyn-origin', ORIGIN], { cwd: REPO })
  clozeHtml = readFileSync(join(dir, 'cloze.html'), 'utf8')
  // A module in three stages (Modül Tasarım Kanunu M2.5): the indicator's steps are stages, not segments.
  execFileSync(PYTHON, ['-c', [
    'import json, sys', 'from src.mcp_server.ornekler import ornek', "d = ornek('QUIZ')",
    "d['meta']['milestones'] = [{'atSegmentId': 't1', 'title': 'Keşfet'}, {'atSegmentId': 'q1', 'title': 'Uygula'},"
      + " {'atSegmentId': 'cp1', 'title': 'Pekiştir'}]",
    "open(sys.argv[1], 'w').write(json.dumps(d, ensure_ascii=False))",
  ].join('\n'), join(dir, 'asamali.json')], { cwd: REPO })
  execFileSync(PYTHON, ['-m', 'src.mcp_server.derleme', '--girdi', join(dir, 'asamali.json'), '--cikti',
    join(dir, 'asamali.html'), '--ebeveyn-origin', ORIGIN], { cwd: REPO })
  asamaliHtml = readFileSync(join(dir, 'asamali.html'), 'utf8')
  quiz = JSON.parse(execFileSync(PYTHON, ['-c',
    'import json; from src.mcp_server.ornekler import ornek; print(json.dumps(ornek("QUIZ")))'],
  { cwd: REPO, encoding: 'utf8' }))
})

const CARD = {
  slug: 'fen5-su', version: 1, title: 'Maddenin Hâlleri', subject: 'Fen Bilimleri', gradeLevel: '5. Sınıf',
  mode: 'QUIZ', outcomes: ['FB.5.4.1.1'], ted_link: { kind: 'exam', id: 'ex-1' },
  created_at: '2026-09-14T10:00:00+00:00', gates: { pass: 17, warn: 1, fail: 0 },
}

async function serveModule(page: Page, framePath = '/m/fen5-su/v1', body = moduleHtml) {
  await page.route('**/api/modules', r => r.fulfill(json({ moduller: [CARD] })))
  // Modüller sayfası tek uçtan okur: hazır modüller + müfredat ağacı (2026-10-11).
  // Bu spec yalnız hazır listeyi ve görüntüleyiciyi sınar, ağacı boş bırakır.
  await page.route('**/api/modules/agac', r => r.fulfill(json({
    hazir: [CARD], dersler: [], kapsam: {}, hata: null,
  })))
  await page.route('**/api/modules/fen5-su/v1/ticket', r => r.fulfill(json({
    url: `https://modul.tedy.online${framePath}?t=${'a'.repeat(64)}&e=1&u=${'b'.repeat(32)}`, exp: 1,
  })))
  await page.route('**/api/modules/fen5-su/v1/aciklama', r => r.fulfill(json(ACIKLAMA)))
  await page.route('**/api/modules/taslak/0123456789abcdef/aciklama', r => r.fulfill(json({ ...ACIKLAMA,
    iddia_durumu: 'kayit_yok', iddialar: [] })))
  await page.route('**/api/modules/taslak/0123456789abcdef/ticket', r => r.fulfill(json({
    url: `https://modul.tedy.online/taslak/0123456789abcdef?t=${'a'.repeat(64)}&e=1&u=${'b'.repeat(32)}`, exp: 1,
  })))
  await page.route('https://modul.tedy.online/**', r => r.fulfill({
    status: 200, contentType: 'text/html; charset=utf-8', body,
    headers: {
      'content-security-policy': SPEC_CSP.replace('frame-ancestors https://tedy.online', `frame-ancestors ${ORIGIN}`),
      'x-content-type-options': 'nosniff', 'referrer-policy': 'no-referrer', 'cache-control': 'private, no-store',
    },
  }))
}

async function recordProgress(page: Page, restore = { answers: [] as string[], done: [] as string[], xp: 0 }) {
  const posts: Record<string, unknown>[] = []
  const gets: string[] = []
  await page.route('**/api/modules/fen5-su/progress**', async r => {
    if (r.request().method() === 'POST') {
      posts.push(r.request().postDataJSON())
      return r.fulfill(json({ ok: true, state: restore }))
    }
    gets.push(r.request().url())
    return r.fulfill(json({ state: restore }))
  })
  return { posts, gets, events: () => posts.map(p => p.event) }
}

const segment = (type: string) => quiz.segments.find(s => s.type === type)!

test('Modüller lists the published module under the frame-src policy', async ({ page }) => {
  await serveModule(page)
  const response = await page.goto('/moduller')
  expect(response?.headers()['content-security-policy']).toBe(FRAME_CSP)
  const satir = page.locator('.module-hazir .cds--contained-list-item')
  await expect(satir).toHaveCount(1)
  await expect(satir).toContainText('Maddenin Hâlleri')
  // QUIZ reads as the module's own word for a question set, never a competition (Kanun M2.7, İ9).
  await expect(satir).toContainText('Alıştırma')
  await expect(satir).not.toContainText('Yarışma')
  // The internal mode code must not reach the reader; the row has rendered (above) before this absence.
  await expect(satir).not.toContainText('QUIZ')
})

// B58: opening a module is navigation, so it is a real link that names its module. Since 2026-10-11 the
// row's own title IS that link (the separate tertiary "Aç" button is gone); B17/S12 still holds — the
// page has no primary button.
test('each module opens through a link that names it', async ({ page }) => {
  await serveModule(page)
  await page.goto('/moduller')
  const ac = page.getByRole('link', { name: 'Maddenin Hâlleri', exact: true })
  await expect(ac).toBeVisible()
  await expect(ac).toHaveAttribute('href', '/moduller/fen5-su/v1')
  await expect(page.locator('.modules .cds--btn--primary')).toHaveCount(0)
  // İ8: the subject's colour is never its only carrier — its name is printed too.
  await expect(page.locator('.module-hazir .cds--contained-list-item')).toContainText('Fen Bilimleri')
  await ac.click()
  await expect(page).toHaveURL(/\/moduller\/fen5-su\/v1$/)
  // The way back is a Carbon breadcrumb above the module's head (2026-10-19).
  await expect(page.getByRole('navigation', { name: 'Konum' }).getByRole('link', { name: 'Modüller', exact: true }))
    .toHaveAttribute('href', '/moduller')
})

// B43 (D3, D4): a failed catalogue says what happened in a sentence, never the raw HTTP text, and as an alert.
test('a failed catalogue is a sentence, not a status code', async ({ page }) => {
  await page.route('**/api/modules/agac', r => r.fulfill({ status: 500, contentType: 'text/html', body: 'Internal Server Error' }))
  await page.goto('/moduller')
  const hata = page.locator('.modules .cds--inline-notification[role="alert"]')
  await expect(hata).toContainText('Modüller yüklenemedi.')
  await expect(hata).not.toContainText('HTTP')
  await expect(hata).not.toContainText('Internal')
})

test('an empty catalogue says so', async ({ page }) => {
  await page.route('**/api/modules/agac', r => r.fulfill(json({
    hazir: [], dersler: [], kapsam: {}, hata: null,
  })))
  await page.goto('/moduller')
  await expect(page.locator('.modules .tedy-empty')).toContainText('Henüz yayınlanmış modül yok.')
})

test('the module opens sandboxed and an answer is recorded through the bridge', async ({ page }) => {
  const progress = await recordProgress(page)
  await serveModule(page)
  await page.goto('/moduller/fen5-su/v1')
  await expect(page.locator('iframe.module-frame')).toHaveAttribute('sandbox', 'allow-scripts')
  const frame = page.frameLocator('iframe.module-frame')
  await expect(frame.locator('#titleText')).toHaveText(quiz.meta.title)
  await expect.poll(() => progress.gets.length).toBeGreaterThan(0)
  await frame.locator('#nextBtn').click()
  const mcq = segment('mcq')
  await frame.locator(`.opt[data-i="${mcq.questions![0].correctIndex}"]`).click()
  await expect.poll(() => progress.events()).toContain('answer')
  expect(progress.posts.find(p => p.event === 'answer')).toMatchObject({
    type: 'edupedia:progress', v: 1, slug: 'fen5-su', version: 1, segmentId: mcq.id, item: 0, correct: true, attempts: 1,
  })
  expect(progress.events()).toContain('segment_complete')
})

test('restore brings back earned progress and resumes at the first unfinished segment', async ({ page }) => {
  const progress = await recordProgress(page, { answers: [`${segment('mcq').id}#0`], done: [segment('teach').id], xp: 15 })
  await serveModule(page)
  await page.goto('/moduller/fen5-su/v1')
  const frame = page.frameLocator('iframe.module-frame')
  await expect(frame.locator('#titleText')).toHaveText(quiz.meta.title)
  await expect(frame.locator('.q-stem')).toBeVisible()
  // XP is an internal number since S43 (B73): the bridge still carries the restored value, the reader never sees it.
  await frame.locator(`.opt[data-i="${segment('mcq').questions![0].correctIndex}"]`).click()
  await expect.poll(() => progress.events()).toContain('answer')
  expect(Number(progress.posts.find(p => p.event === 'answer')!.xp)).toBeGreaterThanOrEqual(15)
})

// B73 (S43, anayasa §9): no XP counter, streak chip, badge case or "+N XP" — a correct answer is acknowledged in
// words, nothing moves.
test('a correct answer moves nothing and counts nothing on screen', async ({ page }) => {
  await recordProgress(page)
  await serveModule(page)
  await page.goto('/moduller/fen5-su/v1')
  const frame = page.frameLocator('iframe.module-frame')
  await expect(frame.locator('#titleText')).toHaveText(quiz.meta.title)
  await frame.locator('#nextBtn').click()
  await frame.locator(`.opt[data-i="${segment('mcq').questions![0].correctIndex}"]`).click()
  await expect(frame.locator('.feedback--ok')).toBeVisible()
  for (const iz of ['#xpValue', '.xp', '#streakChip', '.streak-chip', '#badgeCase', '.badge', '.xp-float'])
    await expect(frame.locator(iz)).toHaveCount(0)
  await expect(frame.locator('header.topbar')).not.toContainText('XP')
})

// B71 (S41, §6.2): every module the dashboard shows carries Carbon's AI label in its frame header; it explains
// what was written with AI help and what it rests on, opens by keyboard and passes axe and IBM Equal Access.
test('the module frame carries an AI label that explains itself', async ({ page }) => {
  await recordProgress(page)
  await serveModule(page)
  await page.goto('/moduller/fen5-su/v1')
  const ust = page.locator('.modul-baslik__ai')
  const etiket = ust.getByRole('button', { name: 'AI Yapay zekâ hakkında bilgi', exact: true })
  await expect(etiket).toBeVisible()
  await expect(ust).toContainText('Yapay zekâ yardımıyla hazırlanmış modül')
  // the label sits upper right of its container — the module's head panel — above the frame
  const [e, k, f] = [await etiket.boundingBox(), await page.locator('.modul-baslik__panel').boundingBox(),
    await page.locator('iframe.module-frame').boundingBox()]
  expect(e!.y + e!.height).toBeLessThanOrEqual(f!.y + 1)
  expect(e!.y).toBeLessThan(k!.y + k!.height / 2)
  expect(e!.x + e!.width).toBeGreaterThan(k!.x + k!.width * 0.75)
  await etiket.focus()
  await page.keyboard.press('Enter')
  const pencere = page.locator('.modul-ai')
  await expect(pencere).toBeVisible()
  await expect(pencere).toContainText('Bu modül yapay zekâ yardımıyla hazırlandı')
  await expect(pencere).toContainText('Kazanım: FB.5.4.1.1')
  await expect(pencere).toContainText('Dayandığı kitap: Fen Bilimleri 5, s. 112–120')
  await expect(pencere).toContainText('Madde katı, sıvı ve gaz hâllerinde bulunur.')
  await expect(pencere).toContainText('ders kitabı s. 112')
  await expect(pencere).toContainText('1 görsel ya da ses yapay zekâyla üretildi.')
  await expect(pencere).toContainText('2 görsel ders kitabından alındı.')
  await expect(etiket).toBeFocused()
  const { violations } = await new AxeBuilder({ page }).include('.modul-baslik')
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice']).analyze()
  expect(violations.map(v => `${v.id}: ${v.nodes.map(n => n.target).join(' ')}`)).toEqual([])
  await page.addScriptTag({ path: ACE })
  const ibm: string[] = await page.evaluate(async () => {
    // @ts-expect-error — `ace` is the injected engine's global
    const rapor = await new window.ace.Checker().check(document.querySelector('.modul-baslik'), ['IBM_Accessibility'])
    return (rapor.results as { ruleId: string; value: string[]; snippet: string; path: { dom: string } }[])
      .filter(s => s.value[0] === 'VIOLATION' && s.value[1] === 'FAIL')
      // Carbon's Toggletip points aria-controls at a popover it renders only when open (ibm-erisilebilirlik).
      .filter(s => !(s.ruleId === 'aria_id_unique' && /cds--ai-label|cds--toggletip/.test(s.snippet + s.path.dom)))
      .map(s => `${s.ruleId}: ${s.snippet.slice(0, 120)}`)
  })
  expect(ibm).toEqual([])
  await page.keyboard.press('Escape')
  await expect(pencere).toBeHidden()
  await expect(etiket).toBeFocused()
})

test('a draft preview carries the AI label too and says when there is no check on record', async ({ page }) => {
  await recordProgress(page)
  await serveModule(page)
  await page.goto('/moduller/taslak/0123456789abcdef')
  const etiket = page.locator('.modul-baslik__ai').getByRole('button', { name: 'AI Yapay zekâ hakkında bilgi', exact: true })
  await etiket.click()
  await expect(page.locator('.modul-ai')).toContainText('Bu sürüm için kayıtlı bir karşılaştırma yok.')
})

test('the AI label still explains the module when its details cannot be fetched', async ({ page }) => {
  await recordProgress(page)
  await serveModule(page)
  await page.route('**/api/modules/fen5-su/v1/aciklama', r => r.fulfill({ status: 500, body: 'x' }))
  await page.goto('/moduller/fen5-su/v1')
  await page.locator('.modul-baslik__ai').getByRole('button', { name: 'AI Yapay zekâ hakkında bilgi', exact: true }).click()
  const pencere = page.locator('.modul-ai')
  await expect(pencere).toContainText('Bu modül yapay zekâ yardımıyla hazırlandı')
  await expect(pencere).toContainText('Ayrıntılar şu an alınamadı.')
})

test('a message the page posts to itself is ignored', async ({ page }) => {
  const progress = await recordProgress(page)
  await serveModule(page)
  await page.goto('/moduller/fen5-su/v1')
  const frame = page.frameLocator('iframe.module-frame')
  await expect(frame.locator('#titleText')).toHaveText(quiz.meta.title)
  await expect.poll(() => progress.gets.length).toBeGreaterThan(0)
  await page.evaluate(() => window.postMessage({ type: 'edupedia:progress', v: 1, slug: 'fen5-su', version: 1,
    event: 'module_complete', xp: 999, ts: Date.now() }, '*'))
  await frame.locator('#nextBtn').click()
  // A real later event proves the listener is live; only then is the forged event's absence meaningful.
  await expect.poll(() => progress.events()).toContain('segment_complete')
  expect(progress.events()).not.toContain('module_complete')
})

test('a frame showing another module cannot write this module', async ({ page }) => {
  await page.addInitScript(() => {
    const w = window as unknown as { __olaylar: string[] }
    w.__olaylar = []
    window.addEventListener('message', e => {
      const d = e.data as { type?: string; event?: string } | null
      if (d?.type === 'edupedia:progress' && d.event) w.__olaylar.push(d.event)
    })
  })
  const progress = await recordProgress(page)
  await serveModule(page, '/m/baska-modul/v1')
  await page.goto('/moduller/fen5-su/v1')
  const frame = page.frameLocator('iframe.module-frame')
  await expect(frame.locator('#titleText')).toHaveText(quiz.meta.title)
  await frame.locator('#nextBtn').click()
  await expect.poll(() => page.evaluate(() => (window as unknown as { __olaylar: string[] }).__olaylar))
    .toContain('segment_complete')
  expect(progress.posts).toEqual([])
  expect(progress.gets).toEqual([])
})

test('a draft preview opens without writing progress', async ({ page }) => {
  const progress = await recordProgress(page)
  await serveModule(page)
  await page.goto('/moduller/taslak/0123456789abcdef')
  const frame = page.frameLocator('iframe.module-frame')
  await expect(frame.locator('#titleText')).toHaveText(quiz.meta.title)
  await frame.locator('#nextBtn').click()
  await expect(frame.locator('.q-stem')).toBeVisible()
  expect(progress.posts).toEqual([])
})

// B45 (§4.4): a sentence is not a Tag. The draft note is an info notification above the frame.
test('the draft preview says so in a notification, not a tag', async ({ page }) => {
  await recordProgress(page)
  await serveModule(page)
  await page.goto('/moduller/taslak/0123456789abcdef')
  const not_ = page.locator('.module-page .cds--inline-notification--info')
  await expect(not_).toContainText('Taslak önizleme')
  await expect(not_).toContainText('İlerleme kaydedilmez.')
  // The draft is said in a notification; the only tags on the page are the outcome chips.
  await expect(page.locator('.module-page .cds--tag').filter({ hasText: /taslak/i })).toHaveCount(0)
})

test('the module takes on the dashboard theme, drafts included', async ({ page }) => {
  // Serve the frame starting in the dark theme so that adopting the dashboard's g10 is observable.
  const dark = moduleHtml.replace('<html lang="tr" data-theme="g10">', '<html lang="tr" data-theme="g100">')
  expect(dark).not.toBe(moduleHtml)
  await recordProgress(page)
  await serveModule(page, '/m/fen5-su/v1', dark)
  await page.goto('/moduller/taslak/0123456789abcdef')
  const frame = page.frameLocator('iframe.module-frame')
  await expect(frame.locator('#titleText')).toHaveText(quiz.meta.title)
  await expect(frame.locator('html')).toHaveAttribute('data-theme', 'g10')
})

// Modül Tasarım Kanunu M4.1 (KB-1, 2026-10-20): the module has no theme of its own — no switch,
// no stored choice — so whatever theme the dashboard sends is the theme it renders in, every time.
test('the module has no theme switch; the dashboard theme always wins', async ({ page }) => {
  await recordProgress(page)
  await serveModule(page)
  await page.goto('/moduller/fen5-su/v1')
  const frame = page.frameLocator('iframe.module-frame')
  await expect(frame.locator('html')).toHaveAttribute('data-theme', 'g10')
  await expect(frame.locator('#themeBtn')).toHaveCount(0)
  const gonder = (theme: string) => page.evaluate((t) => {
    const f = document.querySelector('iframe.module-frame') as HTMLIFrameElement
    f.contentWindow!.postMessage({ type: 'edupedia:appearance', v: 1, theme: t }, '*')
  }, theme)
  await gonder('g100')
  await expect(frame.locator('html')).toHaveAttribute('data-theme', 'g100')
  await gonder('g10')
  await expect(frame.locator('html')).toHaveAttribute('data-theme', 'g10')
  // A theme the template does not carry is ignored, not applied.
  await gonder('white')
  await frame.locator('#nextBtn').click()
  await expect(frame.locator('html')).toHaveAttribute('data-theme', 'g10')
})

test('the dashboard tells the module its root font size, and the module clamps it', async ({ page }) => {
  // 4K (spec §10.2): the frame is a separate document and does not inherit the host's clamp(), so
  // the host reports its computed root size. The module validates it the way it validates the
  // theme — the frame is opaque-origin, so the value is never trusted as sent.
  await recordProgress(page)
  await serveModule(page)
  await page.goto('/moduller/fen5-su/v1')
  const frame = page.frameLocator('iframe.module-frame')
  await expect(frame.locator('html')).toHaveAttribute('data-theme', 'g10')

  const bildir = (rootPx: unknown) => page.evaluate((px) => {
    const f = document.querySelector('iframe.module-frame') as HTMLIFrameElement
    f.contentWindow!.postMessage({ type: 'edupedia:appearance', v: 1, theme: 'g10', rootPx: px }, '*')
  }, rootPx)
  const kokBoyu = () => frame.locator('html').evaluate(e => (e as HTMLElement).style.fontSize)

  await bildir(32)
  await expect.poll(kokBoyu).toBe('32px')

  // Aralık dışı: kıstırılır, olduğu gibi uygulanmaz.
  await bildir(999)
  await expect.poll(kokBoyu).toBe('48px')

  // Sayı değil: yok sayılır — NaNpx yazılmaz, son geçerli değer kalır.
  await bildir('otuziki')
  await expect.poll(kokBoyu).toBe('48px')
})

test('the module inside the frame scales with the dashboard at 4K', async ({ page }) => {
  // The thin frame-geometry assertion: ekran-4k.spec.ts iterates SAYFALAR, which has /moduller
  // (the catalogue) but never /moduller/<slug>/v<N>, and never enters iframe.module-frame — so
  // nothing else measures geometry INSIDE the module. This walks the whole chain: host clamp →
  // rootPx message → module root → rem-sized reading column.
  await recordProgress(page)
  await serveModule(page)
  const olc = async (w: number, h: number) => {
    await page.setViewportSize({ width: w, height: h })
    await page.goto('/moduller/fen5-su/v1')
    const frame = page.frameLocator('iframe.module-frame')
    await expect(frame.locator('html')).toHaveAttribute('data-theme', 'g10')
    return frame.locator('.wrap').evaluate(e => ({
      kok: parseFloat(getComputedStyle(document.documentElement).fontSize),
      wrap: e.getBoundingClientRect().width,
    }))
  }
  const kucuk = await olc(1920, 1080)
  const buyuk = await olc(3840, 2160)
  expect(kucuk.kok).toBeCloseTo(16, 1)
  expect(buyuk.kok).toBeCloseTo(32, 1)
  expect(buyuk.wrap / kucuk.wrap).toBeGreaterThan(1.9)
})

// Flow layout (2026-10-19): the module is a section of the page, not a page in a box. The frame
// grows to the module's content (no scrollbar of its own), the page scrolls as one, the module
// drops its own shell — no second brand band, no page padding — and a section change brings the
// frame's top back into view only when the reader has scrolled past it.
test('the module sits in the page flow: one scroll, no inner shell', async ({ page }) => {
  await recordProgress(page)
  await serveModule(page)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/moduller/fen5-su/v1')
  const iframe = page.locator('iframe.module-frame')
  const frame = page.frameLocator('iframe.module-frame')
  await expect(frame.locator('html')).toHaveAttribute('data-host-layout', 'flow')
  await expect(iframe).toHaveClass(/module-frame--akis/)
  await expect(iframe).toHaveAttribute('scrolling', 'no')

  // The frame is exactly as tall as the module's content: nothing scrolls inside it.
  await expect.poll(() => frame.locator('html').evaluate(e => e.scrollHeight - e.clientHeight)).toBeLessThanOrEqual(1)
  // The brand band lives in the dashboard header only; the module's head is a plain page heading.
  const hero = await frame.locator('.topbar__hero').evaluate(e => getComputedStyle(e).backgroundColor)
  expect(hero).toBe('rgba(0, 0, 0, 0)')
  await expect(frame.locator('.tedy-mark')).toBeHidden()
  // Kanun M1.2 (KB-3): the frame's ground is the dashboard's page ground, so no lighter box shows.
  const zemin = await page.evaluate(() => getComputedStyle(document.body).backgroundColor)
  expect(await frame.locator('body').evaluate(e => getComputedStyle(e).backgroundColor)).toBe(zemin)
  // The module fills the dashboard's column rather than centring its own narrower one.
  const [kutu, sarmal] = [await iframe.boundingBox(), await frame.locator('.wrap').boundingBox()]
  expect(Math.abs(sarmal!.width - kutu!.width)).toBeLessThanOrEqual(1)

  // The page owns the scroll. Opening the module did not move it; after scrolling past the
  // frame's top, the next section brings that top back into view.
  expect(await page.evaluate(() => window.scrollY)).toBe(0)
  const sayfaKayar = await page.evaluate(() => document.documentElement.scrollHeight > window.innerHeight)
  if (sayfaKayar) {
    await frame.locator('#nextBtn').scrollIntoViewIfNeeded()
    expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(0)
    await frame.locator('#nextBtn').click()
    await expect.poll(async () => (await iframe.boundingBox())!.y).toBeGreaterThanOrEqual(0)
  }
})

// Modül Tasarım Kanunu M2.4, M2.5, M5.4 (KB-2, 2026-10-20): one progress indicator, whose steps are
// stages. Where the stage row fits (frame ≥ 42rem and ≥ 8rem a stage) it is drawn in Carbon's
// ProgressIndicator anatomy; where it does not, one line of text says the same. Nothing scrolls
// sideways, a step a reader can press is at least 44 px tall, and 1920 and 3840 open the same branch.
test('the progress indicator shows stages where they fit and one line where they do not', async ({ page }) => {
  await recordProgress(page)
  await serveModule(page, '/m/fen5-su/v1', asamaliHtml)
  const ac = async (w: number, h: number) => {
    await page.setViewportSize({ width: w, height: h })
    await page.goto('/moduller/fen5-su/v1')
    const frame = page.frameLocator('iframe.module-frame')
    await expect(frame.locator('html')).toHaveAttribute('data-host-layout', 'flow')
    await expect(frame.locator('.asama')).toHaveCount(3)
    return frame
  }
  const durum = (frame: ReturnType<Page['frameLocator']>) => frame.locator('.topbar').evaluate(t => {
    const ol = t.querySelector('.asamalar') as HTMLElement
    const doc = document.documentElement
    return {
      satir: getComputedStyle(ol).display !== 'none',
      tasma: Math.max(ol.scrollWidth - ol.clientWidth, doc.scrollWidth - doc.clientWidth),
      metin: (t.querySelector('#railLabel') as HTMLElement).innerText.replace(/\s+/g, ' ').trim(),
      genislik: ol.getBoundingClientRect().width,
    }
  })

  let frame = await ac(1440, 900)
  let d = await durum(frame)
  expect(d.satir).toBe(true)
  expect(d.tasma).toBeLessThanOrEqual(0)
  expect(d.metin).toBe('Bölüm 1 / 3')
  await expect(frame.locator('.asama').nth(0)).toHaveAttribute('aria-current', 'step')
  await expect(frame.locator('.asama').nth(0)).toHaveClass(/asama--current/)
  await expect(frame.locator('.asama').nth(1)).toHaveClass(/asama--incomplete/)
  // Only a finished stage is a button; pressing it goes back to the stage's first section.
  await expect(frame.locator('button.asama__btn')).toHaveCount(0)
  await frame.locator('#nextBtn').click()
  await expect(frame.locator('.asama').nth(0)).toHaveClass(/asama--complete/)
  const geri = frame.locator('.asama').nth(0).locator('button.asama__btn')
  expect((await geri.boundingBox())!.height).toBeGreaterThanOrEqual(44)
  await geri.click()
  await expect(frame.locator('.asama').nth(0)).toHaveAttribute('aria-current', 'step')

  const genis = d.genislik
  frame = await ac(3840, 2160)
  d = await durum(frame)
  expect(d.satir).toBe(true)
  expect(d.genislik / genis).toBeGreaterThan(1.9)

  // A phone: the row does not fit, so the line names the stage first and the totals second.
  frame = await ac(390, 844)
  d = await durum(frame)
  expect(d.satir).toBe(false)
  expect(d.tasma).toBeLessThanOrEqual(0)
  expect(d.metin).toBe('Aşama 1/3 · Keşfet · Bölüm 1 / 3')
  const agirlik = (sel: string) => frame.locator(sel).first().evaluate(e => getComputedStyle(e).fontWeight)
  expect(Number(await agirlik('#railStage .rail-vurgu'))).toBeGreaterThan(Number(await agirlik('#railText .rail-n')))
})

test('a module without stages shows its position as one line', async ({ page }) => {
  await recordProgress(page)
  await serveModule(page)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/moduller/fen5-su/v1')
  const frame = page.frameLocator('iframe.module-frame')
  await expect(frame.locator('html')).toHaveAttribute('data-host-layout', 'flow')
  await expect(frame.locator('.asama')).toHaveCount(0)
  await expect(frame.locator('#railLabel')).toHaveText('Bölüm 1 / 3')
})

test('a module compiled before the flow layout keeps its own scroll', async ({ page }) => {
  // A module compiled before 2026-10-19 never reports its height: the frame keeps its minimum
  // height and the module scrolls inside it, as before — nothing collapses to zero.
  const eski = moduleHtml.replace('adoptHostLayout(d.layout); ', '')
  expect(eski).not.toBe(moduleHtml)
  await recordProgress(page)
  await serveModule(page, '/m/fen5-su/v1', eski)
  await page.goto('/moduller/fen5-su/v1')
  const frame = page.frameLocator('iframe.module-frame')
  await expect(frame.locator('#titleText')).toHaveText(quiz.meta.title)
  await expect(frame.locator('html')).not.toHaveAttribute('data-host-layout', 'flow')
  await expect(page.locator('iframe.module-frame')).not.toHaveClass(/module-frame--akis/)
  expect((await page.locator('iframe.module-frame').boundingBox())!.height).toBeGreaterThan(300)
})

// The module's head (2026-10-19): the dashboard names the module in the subject's panel, in title
// case; each outcome is an operational tag that opens its wording in a passive modal, and Escape
// returns focus to the tag. A build compiled before the wording was kept says so instead.
test('the module head names the module and opens each outcome in a dialog', async ({ page }) => {
  await recordProgress(page)
  await serveModule(page)
  await page.route('**/api/modules/fen5-su/v1/aciklama', r => r.fulfill(json({ ...ACIKLAMA, baslik: 'Maddenin hâlleri',
    sure_dk: 15, kazanim_ayrintilari: [{ kod: 'FB.5.4.1.1', metin: 'Maddenin hâllerini açıklar.', beceri: 'KB2.7 Karşılaştırma Becerisi' }] })))
  await page.goto('/moduller/fen5-su/v1')
  const bas = page.locator('.modul-baslik')
  await expect(bas.getByRole('heading', { level: 2, name: 'Maddenin Hâlleri', exact: true })).toBeVisible()
  await expect(bas).toHaveClass(/ted-subject--/)
  await expect(bas.locator('.modul-baslik__kas')).toContainText('Fen Bilimleri · 5. Sınıf · ~15 dk')
  await expect(bas).toContainText('Fen Bilimleri 5, s. 112–120')
  // the module does not repeat its own title in the flow layout
  await expect(page.frameLocator('iframe.module-frame').locator('.topbar__l')).toBeHidden()
  const cip = bas.getByRole('group', { name: 'Kazanımlar' }).getByRole('button', { name: 'FB.5.4.1.1' })
  await cip.click()
  const pencere = page.getByRole('dialog')
  await expect(pencere).toBeVisible()
  await expect(pencere).toContainText('Maddenin hâllerini açıklar.')
  await expect(pencere).toContainText('KB2.7 Karşılaştırma Becerisi')
  const { violations } = await new AxeBuilder({ page }).include('.modul-kazanim')
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze()
  expect(violations.map(v => v.id)).toEqual([])
  await page.keyboard.press('Escape')
  await expect(pencere).toBeHidden()
  await expect(cip).toBeFocused()
})

test('an outcome without kept wording says so, not a blank dialog', async ({ page }) => {
  await recordProgress(page)
  await serveModule(page)
  await page.goto('/moduller/fen5-su/v1')
  await page.locator('.modul-baslik').getByRole('button', { name: 'FB.5.4.1.1' }).click()
  await expect(page.getByRole('dialog')).toContainText('Bu kazanımın metni bu sürümde kayıtlı değil.')
})

test('a refused ticket is explained, not blank', async ({ page }) => {
  await page.route('**/api/modules/fen5-su/v1/ticket', r => r.fulfill({ status: 403, contentType: 'application/json',
    body: JSON.stringify({ error: 'session_required' }) }))
  await page.goto('/moduller/fen5-su/v1')
  await expect(page.locator('.module-viewer .cds--inline-notification')).toContainText('Bu modülü açma yetkin yok.')
  await expect(page.locator('iframe.module-frame')).toHaveCount(0)
})

test('a module linked to an upcoming exam is offered on İşler', async ({ page }) => {
  const inDays = (n: number) => new Date(Date.now() + n * 86_400_000)
  const due = inDays(3)
  const pad = (n: number) => String(n).padStart(2, '0')
  const exam = (id: string, course: string) => ({
    id, course, title: `${course} 1. yazılı`, rawTitle: `${course} 1. yazılı`, courseColor: '#0f62fe', examNumber: 1,
    date: inDays(2).toISOString(), endDate: null, allDay: true, status: 'upcoming', grade: null,
    relatedHomework: [],
  })
  await page.route('**/api/homework', r => r.fulfill(json({ summary: '', homework: [{
    'Ders Adı': 'Türkçe', 'Ödev Başlığı': 'Okuma günlüğü', 'Ödev Durumu': '', first_seen: '2026-09-01T09:00',
    'Ödev Son Teslim Tarihi': `${pad(due.getDate())}.${pad(due.getMonth() + 1)}.${due.getFullYear()} 23:59`,
  }] })))
  await page.route('**/api/enrichment', r => r.fulfill(json({})))
  await page.route('**/api/exams', r => r.fulfill(json({ exams: [exam('ex-1', 'Fen Bilimleri'), exam('ex-2', 'Matematik')] })))
  await page.route('**/api/modules', r => r.fulfill(json({ moduller: [CARD] })))
  await page.goto('/isler')
  const rows = page.locator('.exams-ahead__row')
  await expect(rows).toHaveCount(2)
  const linked = rows.filter({ hasText: 'Fen Bilimleri' })
  const unlinked = rows.filter({ hasText: 'Matematik' })
  await expect(linked.getByRole('button', { name: 'Modülü aç' })).toBeVisible()
  await expect(unlinked).toHaveCount(1)
  await expect(unlinked.getByRole('button', { name: 'Modülü aç' })).toHaveCount(0)
  await linked.getByRole('button', { name: 'Modülü aç' }).click()
  await expect(page).toHaveURL(/\/moduller\/fen5-su\/v1$/)
})

// B42 (D2, §5.9): a word already tried is content to read, not a dead control — it stays in the tab order and in
// the accessibility tree, says that it was tried, and is not faded (it was `disabled` at 40% opacity).
test('a tried word in the module stays readable, not disabled', async ({ page }) => {
  await recordProgress(page)
  await serveModule(page, '/m/fen5-su/v1', clozeHtml)
  await page.goto('/moduller/fen5-su/v1')
  const frame = page.frameLocator('iframe.module-frame')
  await expect(frame.locator('.pool .chip-btn')).toHaveCount(3)
  const yanlis = frame.locator('.chip-btn[data-w="yoğuşma"]')
  await yanlis.click()
  await expect(frame.locator('#ffb')).toContainText('Bu değil.')
  await expect(yanlis).toHaveAttribute('aria-disabled', 'true')
  await expect(yanlis).not.toHaveAttribute('disabled', /.*/)
  await expect(yanlis).toHaveAccessibleName(/yoğuşma.*denendi, doğru değil/)
  expect(await yanlis.evaluate(el => getComputedStyle(el).opacity)).toBe('1')
  await yanlis.focus()
  await expect(yanlis).toBeFocused()
  await frame.locator('.chip-btn[data-w="buharlaşma"]').click()
  await expect(frame.locator('#ffb')).toContainText('Doğru!')
})
