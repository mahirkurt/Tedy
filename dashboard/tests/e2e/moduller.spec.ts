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
  const card = page.locator('.module-card')
  await expect(card).toHaveCount(1)
  await expect(card).toContainText('Maddenin Hâlleri')
  await expect(card).toContainText('Yarışma')
  // The internal mode code must not reach the reader; the card has rendered (above) before this absence.
  await expect(card).not.toContainText('QUIZ')
})

// B17 (S12): the row action is not the page's primary button; B58: opening a module is navigation, so it is a
// real link that names its module (B41: every "Aç" on the list is told apart).
test('each module opens through a tertiary link that names it', async ({ page }) => {
  await serveModule(page)
  await page.goto('/moduller')
  const ac = page.getByRole('link', { name: 'Aç: Maddenin Hâlleri', exact: true })
  await expect(ac).toBeVisible()
  await expect(ac).toHaveAttribute('href', '/moduller/fen5-su/v1')
  await expect(ac).toHaveClass(/cds--btn--tertiary/)
  await expect(page.locator('.modules .cds--btn--primary')).toHaveCount(0)
  await ac.click()
  await expect(page).toHaveURL(/\/moduller\/fen5-su\/v1$/)
  await expect(page.getByRole('link', { name: 'Modüllere dön' })).toHaveAttribute('href', '/moduller')
})

// B43 (D3, D4): a failed catalogue says what happened in a sentence, never the raw HTTP text, and as an alert.
test('a failed catalogue is a sentence, not a status code', async ({ page }) => {
  await page.route('**/api/modules', r => r.fulfill({ status: 500, contentType: 'text/html', body: 'Internal Server Error' }))
  await page.goto('/moduller')
  const hata = page.locator('.modules .cds--inline-notification[role="alert"]')
  await expect(hata).toContainText('Modüller yüklenemedi.')
  await expect(hata).not.toContainText('HTTP')
  await expect(hata).not.toContainText('Internal')
})

test('an empty catalogue says so', async ({ page }) => {
  await page.route('**/api/modules', r => r.fulfill(json({ moduller: [] })))
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
  const ust = page.locator('.module-viewer__ust')
  const etiket = ust.getByRole('button', { name: 'AI Yapay zekâ hakkında bilgi', exact: true })
  await expect(etiket).toBeVisible()
  await expect(ust).toContainText('Yapay zekâ yardımıyla hazırlanmış modül')
  // the label sits above the frame, at its upper right
  const [e, f] = [await etiket.boundingBox(), await page.locator('iframe.module-frame').boundingBox()]
  expect(e!.y + e!.height).toBeLessThanOrEqual(f!.y + 1)
  expect(e!.x + e!.width).toBeGreaterThan(f!.x + f!.width * 0.75)
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
  const { violations } = await new AxeBuilder({ page }).include('.module-viewer__ust')
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice']).analyze()
  expect(violations.map(v => `${v.id}: ${v.nodes.map(n => n.target).join(' ')}`)).toEqual([])
  await page.addScriptTag({ path: ACE })
  const ibm: string[] = await page.evaluate(async () => {
    // @ts-expect-error — `ace` is the injected engine's global
    const rapor = await new window.ace.Checker().check(document.querySelector('.module-viewer__ust'), ['IBM_Accessibility'])
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
  const etiket = page.locator('.module-viewer__ust').getByRole('button', { name: 'AI Yapay zekâ hakkında bilgi', exact: true })
  await etiket.click()
  await expect(page.locator('.modul-ai')).toContainText('Bu sürüm için kayıtlı bir karşılaştırma yok.')
})

test('the AI label still explains the module when its details cannot be fetched', async ({ page }) => {
  await recordProgress(page)
  await serveModule(page)
  await page.route('**/api/modules/fen5-su/v1/aciklama', r => r.fulfill({ status: 500, body: 'x' }))
  await page.goto('/moduller/fen5-su/v1')
  await page.locator('.module-viewer__ust').getByRole('button', { name: 'AI Yapay zekâ hakkında bilgi', exact: true }).click()
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
  await expect(page.locator('.module-page .cds--tag')).toHaveCount(0)
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
  await expect(frame.locator('#themeBtn')).toHaveAttribute('aria-label', 'Koyu temaya geç')
})

test('a theme the student picks in the module is not overridden', async ({ page }) => {
  await recordProgress(page)
  await serveModule(page)
  await page.goto('/moduller/fen5-su/v1')
  const frame = page.frameLocator('iframe.module-frame')
  await expect(frame.locator('html')).toHaveAttribute('data-theme', 'g10')
  await frame.locator('#themeBtn').click()
  await expect(frame.locator('html')).toHaveAttribute('data-theme', 'g100')
  // Re-send the dashboard's theme the way the viewer does on load; the student's choice stands.
  await page.evaluate(() => {
    const f = document.querySelector('iframe.module-frame') as HTMLIFrameElement
    f.contentWindow!.postMessage({ type: 'edupedia:appearance', v: 1, theme: 'g10' }, '*')
  })
  await frame.locator('#nextBtn').click()
  await expect(frame.locator('html')).toHaveAttribute('data-theme', 'g100')
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
    date: inDays(2).toISOString(), endDate: null, allDay: true, status: 'upcoming', grade: null, studyGuide: null,
    aiSummary: null, relatedHomework: [],
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
