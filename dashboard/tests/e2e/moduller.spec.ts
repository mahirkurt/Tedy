import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { execFileSync } from 'node:child_process'
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
const PYTHON = join(REPO, '.venv/bin/python')
const SPEC_CSP = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; " +
  "font-src data:; media-src data:; connect-src 'none'; frame-ancestors https://tedy.online; base-uri 'none'; form-action 'none'"
const FRAME_CSP = 'frame-src https://modul.tedy.online https://accounts.google.com'
const json = (b: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(b) })

type Segment = { id: string; type: string; questions?: { correctIndex: number }[] }
let moduleHtml = ''
let quiz: { meta: { title: string }; segments: Segment[] }

test.beforeAll(() => {
  const out = join(mkdtempSync(join(tmpdir(), 'tedy-modul-')), 'quiz.html')
  execFileSync(PYTHON, ['-m', 'src.mcp_server.derleme', '--ornek', 'QUIZ', '--cikti', out, '--ebeveyn-origin', ORIGIN],
    { cwd: REPO })
  moduleHtml = readFileSync(out, 'utf8')
  quiz = JSON.parse(execFileSync(PYTHON, ['-c',
    'import json; from src.mcp_server.ornekler import ornek; print(json.dumps(ornek("QUIZ")))'],
  { cwd: REPO, encoding: 'utf8' }))
})

const CARD = {
  slug: 'fen5-su', version: 1, title: 'Maddenin Hâlleri', subject: 'Fen Bilimleri', gradeLevel: '5. Sınıf',
  mode: 'QUIZ', outcomes: ['FB.5.4.1.1'], ted_link: { kind: 'exam', id: 'ex-1' },
  created_at: '2026-09-14T10:00:00+00:00', gates: { pass: 17, warn: 1, fail: 0 },
}

async function serveModule(page: Page, framePath = '/m/fen5-su/v1') {
  await page.route('**/api/modules', r => r.fulfill(json({ moduller: [CARD] })))
  await page.route('**/api/modules/fen5-su/v1/ticket', r => r.fulfill(json({
    url: `https://modul.tedy.online${framePath}?t=${'a'.repeat(64)}&e=1&u=${'b'.repeat(32)}`, exp: 1,
  })))
  await page.route('**/api/modules/taslak/0123456789abcdef/ticket', r => r.fulfill(json({
    url: `https://modul.tedy.online/taslak/0123456789abcdef?t=${'a'.repeat(64)}&e=1&u=${'b'.repeat(32)}`, exp: 1,
  })))
  await page.route('https://modul.tedy.online/**', r => r.fulfill({
    status: 200, contentType: 'text/html; charset=utf-8', body: moduleHtml,
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
  await recordProgress(page, { answers: [`${segment('mcq').id}#0`], done: [segment('teach').id], xp: 15 })
  await serveModule(page)
  await page.goto('/moduller/fen5-su/v1')
  const frame = page.frameLocator('iframe.module-frame')
  await expect(frame.locator('#titleText')).toHaveText(quiz.meta.title)
  await expect(frame.locator('#xpValue')).toHaveText('15')
  await expect(frame.locator('.q-stem')).toBeVisible()
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
