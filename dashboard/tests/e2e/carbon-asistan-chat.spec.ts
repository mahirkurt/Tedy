import { createServer } from 'node:http'
import type { IncomingMessage, ServerResponse } from 'node:http'
import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { mockSohbetler } from './_audit-fixtures'
import { asistanAc, sor, sonCevap, soruAlani } from './_asistan-carbon'

test.beforeEach(async ({ page }) => { await mockSohbetler(page) })

// Eski assistant-chat.spec.ts'in testleri, aynı adlarla (Görev 19). Karar tablosu: "citation chips render
// inside every markdown block type", "…inside bold and italic emphasis…" ve "a citation chip is described by
// the snippet" carbon-asistan-kaynaklar.spec.ts'te tek tek karşılanır (Carbon atıf işaretini metinden çıkarır,
// kaynakları cevabın altındaki "Kaynaklar" düğmesinde listeler). Seçiciler: cevap gövdesi → sonCevap(page),
// rozetler → [data-tedy-altbilgi], kaynak paneli → "Kaynak ayrıntıları" ile açılan .asistan__kaynaklar.

const meta = { model: 'claude-sonnet-5', degraded: [] as string[], dropped_citations: 0 }
const cevap = (p: Record<string, unknown>) => ({ citations: [], safety_flags: [], plan_blocks: [], intent: 'qa',
  session_id: '', meta, ...p })

async function klasik(page: Page, govde: Record<string, unknown>) {
  await page.route('**/api/assistant/stream', route => route.abort())
  await page.route('**/api/assistant/chat', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify(cevap(govde)) }))
}
const altbilgi = (page: Page) => page.locator('[data-tedy-altbilgi]').filter({ visible: true }).last()
async function kaynakPaneli(page: Page) {
  await page.getByRole('button', { name: 'Kaynak ayrıntıları' }).last().click()
  return page.locator('.asistan__kaynaklar')
}

function startStaggeredSseServer(frames: string[], delayMs = 120) {
  const server = createServer((req: IncomingMessage, res: ServerResponse) => {
    const origin = req.headers.origin
    if (origin) {
      res.setHeader('Access-Control-Allow-Origin', origin)
      res.setHeader('Access-Control-Allow-Credentials', 'true')
    }
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS')
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type')
    if (req.method === 'OPTIONS') {
      res.writeHead(204)
      res.end()
      return
    }
    res.writeHead(200, {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache',
    })
    let i = 0
    const sendNext = () => {
      if (i >= frames.length) {
        res.end()
        return
      }
      res.write(frames[i])
      i += 1
      setTimeout(sendNext, delayMs)
    }
    sendNext()
  })
  return new Promise<{ port: number; close: () => Promise<void> }>((resolve, reject) => {
    server.on('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      const port = typeof address === 'object' && address ? address.port : 0
      resolve({
        port,
        close: () => new Promise<void>(r => server.close(() => r())),
      })
    })
  })
}

test('assistant answers render markdown rather than raw syntax', async ({ page }) => {
  await klasik(page, { answer: '## Başlık\n\n- birinci madde\n- ikinci madde [S1]',
    citations: [{ id: 'S1', kind: 'mufredat', label: 'MEB · kesir', locator: {}, snippet: 'kazanım metni', confidence: 0.9 }] })
  await asistanAc(page)
  await sor(page, 'kesirler')
  const govde = sonCevap(page)
  // Sayfanın başlığı h2: cevabın ## bölümü h3 (eski çizici gibi; markdownEklentileri).
  await expect(govde.locator('h3')).toHaveText('Başlık')
  await expect(govde.getByRole('listitem')).toHaveCount(2)
  await expect(govde).not.toContainText('##')
  await expect(govde).not.toContainText('[S1]')
  await expect(page.getByRole('button', { name: 'Kaynaklar', exact: true })).toBeVisible()
})

test('sources are grouped by kind and the cited one highlights', async ({ page }) => {
  await klasik(page, { answer: 'Ödevin [S1] ve kazanım [S2].', citations: [
    { id: 'S1', kind: 'ogrenci', label: 'scraped_data.json', locator: {}, snippet: 'ödev', confidence: 0.8 },
    { id: 'S2', kind: 'mufredat', label: 'MEB · kesir', locator: {}, snippet: 'kazanım', confidence: 0.9 },
  ] })
  await asistanAc(page)
  await sor(page, 'ödevim ne')
  const panel = await kaynakPaneli(page)
  await expect(panel.locator('.ac__ref-group')).toHaveCount(2)
  await expect(panel.locator('.ac__ref-group-title').first()).toContainText('okul verisi')
  // Atfın işaret ettiği yer Carbon'un kaynak listesi açılınca metinde vurgulanır (dar alanda panel sohbeti örter).
  await page.getByRole('button', { name: 'Kaynakları kapat' }).click()
  await page.getByRole('button', { name: 'Kaynaklar', exact: true }).click()
  await expect(sonCevap(page).locator('mark')).toHaveCount(1)
  await expect(sonCevap(page).locator('mark')).toContainText('Ödevin')
})

test('a degraded answer says so', async ({ page }) => {
  await klasik(page, { answer: 'Yalnız okul verisiyle yanıt.', meta: { ...meta, degraded: ['maarif-mufredat'] } })
  await asistanAc(page)
  await sor(page, 'kesir')
  await expect(altbilgi(page)).toContainText('Müfredat kaynağına ulaşılamadı')
})

test('risk and warning safety flags render with different severity, not as raw tokens', async ({ page }) => {
  await klasik(page, { answer: 'Bu konuda dikkatli olmalıyız.',
    safety_flags: ['risk:mental_health_crisis', 'warning:limited_confidence'] })
  await asistanAc(page)
  await sor(page, 'zor bir gün geçiriyorum')
  const flags = altbilgi(page).locator('.cds--tag')
  await expect(flags).toHaveCount(2)
  const riskTag = flags.filter({ hasText: 'mental_health_crisis' })
  const warningTag = flags.filter({ hasText: 'Kaynaksız cevap' })
  await expect(riskTag).toHaveCount(1)
  await expect(warningTag).toHaveCount(1)
  await expect(riskTag).toHaveClass(/cds--tag--red/)
  await expect(warningTag).not.toHaveClass(/cds--tag--red/)
  await expect(warningTag).toHaveClass(/cds--tag--gray/)
  await expect(sonCevap(page)).not.toContainText('warning:limited_confidence')
  await expect(altbilgi(page)).not.toContainText('warning:limited_confidence')
})

test('every degraded source surfaces, not just the first', async ({ page }) => {
  await klasik(page, { answer: 'Kısmi yanıt.', meta: { ...meta, degraded: ['maarif-mufredat', 'some-other-server'] } })
  await asistanAc(page)
  await sor(page, 'kesir')
  await expect(altbilgi(page).locator('.cds--tag')).toHaveCount(2)
  await expect(altbilgi(page)).toContainText('Müfredat kaynağına ulaşılamadı')
  await expect(altbilgi(page)).toContainText('some-other-server')
})

test('citations with an unknown kind get their own group, not folded into ogrenci or mufredat, and their chip still highlights', async ({ page }) => {
  await klasik(page, { answer: 'Bilinen kaynak [S1] ve tanınmayan kaynak [S2].', citations: [
    { id: 'S1', kind: 'ogrenci', label: 'scraped_data.json', locator: {}, snippet: 'ödev', confidence: 0.8 },
    { id: 'S2', kind: 'harici', label: 'Bilinmeyen kaynak', locator: {}, snippet: 'harici parça', confidence: 0.5 },
  ] })
  await asistanAc(page)
  await sor(page, 'karışık kaynaklar')
  const panel = await kaynakPaneli(page)
  await expect(panel.locator('.ac__ref-group')).toHaveCount(2)
  const groupTitles = panel.locator('.ac__ref-group-title')
  await expect(groupTitles.first()).toContainText('okul verisi')
  await expect(groupTitles.last()).toContainText('Sınıflandırılmamış')
  await expect(panel.locator('.ac__ref-group').first()).not.toContainText('Bilinmeyen kaynak')
  // Carbon'un kaynak listesinde tanınmayan atıf da kartıyla gelir ve seçilince metindeki yeri vurgulanır.
  await page.getByRole('button', { name: 'Kaynakları kapat' }).click()
  await page.getByRole('button', { name: 'Kaynaklar', exact: true }).click()
  await expect(sonCevap(page).locator('mark')).toContainText('Bilinen kaynak')
  await page.getByRole('button', { name: 'Sonraki slayt.' }).click()
  await expect(page.getByText('Bilinmeyen kaynak', { exact: true }).filter({ visible: true })).toHaveCount(1)
  await expect(sonCevap(page).locator('mark')).toContainText('tanınmayan kaynak')
  await expect(sonCevap(page)).not.toContainText('undefined')
})

test('the stream is genuinely consumed: tool progress renders, the streamed answer lands, and the classic endpoint is never called', async ({ page }) => {
  let classicCalls = 0
  await page.route('**/api/assistant/chat', route => {
    classicCalls += 1
    return route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify(cevap({ answer: 'YEDEK YOLDAN GELEN CEVAP — bu görünüyorsa akış tüketilmedi demektir.' })) })
  })
  const streamPayload = cevap({
    answer: 'STREAMMARKERXYZ9K2: kesir çizgisi bir bölme işlemidir [S1].',
    citations: [{ id: 'S1', kind: 'mufredat', label: 'MEB · kesir', locator: {}, snippet: 'akıştan gelen kaynak', confidence: 0.9 }],
    session_id: 'dashboard-default',
  })
  const frames = [
    'event: tool_start\ndata: {"name":"kazanim_ara"}\n\n',
    'event: tool_end\ndata: {"name":"kazanim_ara","ok":true,"ms":40}\n\n',
    `event: answer\ndata: ${JSON.stringify({ payload: streamPayload })}\n\n`,
    'event: done\ndata: {}\n\n',
  ]
  const sse = await startStaggeredSseServer(frames, 150)
  try {
    await page.route('**/api/assistant/stream', route => route.continue({ url: `http://127.0.0.1:${sse.port}/` }))
    await asistanAc(page)
    await sor(page, 'kesirler nasıl anlatılır')
    // Araç adımı akış sürerken Carbon'un adım bileşeninde açık görünür (reasoning; cevap gelince katlanır).
    await expect(page.getByText('MEB kazanımları aranıyor', { exact: true }).filter({ visible: true }).first()).toBeVisible()
    await expect(sonCevap(page)).toContainText('STREAMMARKERXYZ9K2')
    await expect(sonCevap(page)).not.toContainText('YEDEK YOLDAN GELEN')
    expect(classicCalls).toBe(0)
    await expect(page.getByText('Asistan yanıtı alınamadı.', { exact: true })).toHaveCount(0)
  } finally {
    await sse.close()
  }
})

test('a stream that closes mid-flight without an answer falls back to the classic endpoint and still answers the reader', async ({ page }) => {
  const consoleWarnings: string[] = []
  page.on('console', msg => { if (msg.type() === 'warning') consoleWarnings.push(msg.text()) })
  await page.route('**/api/assistant/stream', route => route.fulfill({ status: 200, contentType: 'text/event-stream',
    body: 'event: tool_start\ndata: {"name":"kazanim_ara"}\n\n' + 'event: tool_end\ndata: {"name":"kazanim_ara","ok":true,"ms":40}\n\n' }))
  let classicCalls = 0
  await page.route('**/api/assistant/chat', route => {
    classicCalls += 1
    return route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify(cevap({ answer: 'FALLBACKMARKERABC7Q: yedek uçtan gelen cevap.' })) })
  })
  await asistanAc(page)
  await sor(page, 'yarıda kesilen akış')
  await expect(sonCevap(page)).toContainText('FALLBACKMARKERABC7Q')
  expect(classicCalls).toBe(1)
  await expect(page.getByText('Asistan yanıtı alınamadı.', { exact: true })).toHaveCount(0)
  await expect.poll(() => consoleWarnings.some(w => w.includes('akış başarısız'))).toBe(true)
})

test('an unrecognised source group looks different from a verified one', async ({ page }) => {
  await klasik(page, { answer: 'Bilinen [S1] ve bilinmeyen [S2].', citations: [
    { id: 'S1', kind: 'mufredat', label: 'MEB · kesirler', locator: {}, snippet: 'kazanım', confidence: 0.9 },
    { id: 'S2', kind: 'yepyeni_kaynak', label: 'Bilinmeyen', locator: {}, snippet: 'içerik', confidence: 0.5 },
  ] })
  await asistanAc(page)
  await sor(page, 'kesirler')
  const panel = await kaynakPaneli(page)
  await expect(panel.getByText('Sınıflandırılmamış kaynak')).toBeVisible()
  await expect(panel.locator('.ac__ref-group')).toHaveCount(2)
  const unknown = panel.locator('.ac__ref-group--unclassified')
  await expect(unknown).toHaveCount(1)
  await expect(unknown).toContainText('Bilinmeyen')
  const knownBorder = await panel.locator('.ac__ref-group').first().evaluate(el => getComputedStyle(el).borderLeftColor)
  const unknownBorder = await unknown.evaluate(el => getComputedStyle(el).borderLeftColor)
  expect(unknownBorder).not.toBe(knownBorder)
})

function startManualSseServer() {
  let res: ServerResponse | null = null
  let connected!: () => void
  const ready = new Promise<void>(r => { connected = r })
  const server = createServer((req: IncomingMessage, response: ServerResponse) => {
    const origin = req.headers.origin
    if (origin) {
      response.setHeader('Access-Control-Allow-Origin', origin)
      response.setHeader('Access-Control-Allow-Credentials', 'true')
    }
    response.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS')
    response.setHeader('Access-Control-Allow-Headers', 'Content-Type')
    if (req.method === 'OPTIONS') {
      response.writeHead(204)
      response.end()
      return
    }
    response.writeHead(200, {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache',
    })
    res = response
    connected()
  })
  return new Promise<{
    port: number
    ready: Promise<void>
    send: (event: string, data: unknown) => void
    end: () => void
    close: () => Promise<void>
  }>((resolve, reject) => {
    server.on('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      resolve({
        port: typeof address === 'object' && address ? address.port : 0,
        ready,
        send: (event, data) => { res?.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`) },
        end: () => { res?.end() },
        close: () => new Promise<void>(r => { res?.end(); server.close(() => r()) }),
      })
    })
  })
}

// The answer is shown while it is written (2026-09-24). At medium effort a
// normal question takes ~17 s; for this reader a blank wait that long is where
// attention leaves. Three things are pinned: text written before a tool call
// is dropped when `answer_reset` arrives (it is not part of the answer), a
// citation marker never shows as bare "[S1]" while its source is not yet
// known (D4), and the final `answer` replaces the draft with chips.
test('the answer appears while it is written, and the final answer replaces the draft', async ({ page }) => {
  await page.route('**/api/assistant/chat', route => route.abort())
  const payload = cevap({ answer: 'KESİRYAZIMI bir bölme işlemidir [S1].', session_id: 'dashboard-default',
    citations: [{ id: 'S1', kind: 'mufredat', label: 'MEB · kesir', locator: {}, snippet: 'kaynak', confidence: 0.9 }] })
  const sse = await startManualSseServer()
  try {
    await page.route('**/api/assistant/stream', route => route.continue({ url: `http://127.0.0.1:${sse.port}/` }))
    await asistanAc(page)
    await sor(page, 'kesir nedir')
    await sse.ready
    const taslak = sonCevap(page)
    sse.send('answer_delta', { text: 'ÖNMETİN bakıyorum.' })
    await expect(taslak).toContainText('ÖNMETİN')
    sse.send('answer_reset', {})
    sse.send('tool_start', { name: 'kazanim_ara' })
    await expect(page.getByText('MEB kazanımları aranıyor', { exact: true }).filter({ visible: true }).first()).toBeVisible()
    await expect(page.getByText('ÖNMETİN bakıyorum.', { exact: true }).filter({ visible: true })).toHaveCount(0)
    sse.send('tool_end', { name: 'kazanim_ara', ok: true })
    sse.send('answer_delta', { text: 'KESİRYAZIMI bir ' })
    sse.send('answer_delta', { text: 'bölme işlemidir [S1' })
    await expect(taslak).toContainText('bölme işlemidir')
    await expect(taslak).not.toContainText('[S')
    sse.send('answer_delta', { text: '].' })
    await expect(taslak).toContainText('işlemidir.')
    await expect(taslak).not.toContainText('[S')
    sse.send('answer', { payload })
    sse.send('done', {})
    sse.end()
    await expect(page.getByRole('button', { name: 'Kaynaklar', exact: true })).toBeVisible()
    await expect(page.getByText('Asistan yanıtı alınamadı.', { exact: true })).toHaveCount(0)
    await expect(sonCevap(page)).not.toContainText('[S')
    await expect(page.locator('.cds-aichat--assistant-message').filter({ visible: true })
      .filter({ hasText: 'KESİRYAZIMI' })).toHaveCount(1)
  } finally {
    await sse.close()
  }
})

test('the page addresses Işık as "sen" and the family as "siz"', async ({ page }) => {
  await klasik(page, { answer: 'Tamam.' })
  await asistanAc(page)
  await expect(page.getByText(/Işık'ın ödevleri/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Işık bugün neye öncelik vermeli?' })).toBeVisible()
  await expect(soruAlani(page)).toHaveAttribute('placeholder', /sorun/)
  await sor(page, 'ödevler')
  await expect(page.getByText(/^Siz \d{2}:\d{2}$/).filter({ visible: true })).toHaveCount(1)

  await page.route('**/api/auth/me', route => route.fulfill({ status: 200, contentType: 'application/json',
    body: JSON.stringify({ email: 'isikkurtx@gmail.com', name: 'Işık Kurt', picture: '', role: 'full', student: true }) }))
  await asistanAc(page)
  await expect(page.getByText(/sana yardımcı/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Bugün neye öncelik vermeliyim?' })).toBeVisible()
  await sor(page, 'ödevlerim')
  await expect(page.getByText(/^Sen \d{2}:\d{2}$/).filter({ visible: true })).toHaveCount(1)
})

test('local fallback answer is labelled, not shown as a raw flag', async ({ page }) => {
  await klasik(page, { answer: 'Paydaları eşitle.\n\n_Bu cevap TEDY\'nin evdeki yedek modelinden geldi._',
    safety_flags: ['warning:limited_confidence', 'warning:yerel_yedek'],
    meta: { model: 'gemma4-e4b-cpu', provider: 'yerel', degraded: [], dropped_citations: 0 } })
  await asistanAc(page)
  await sor(page, 'kesir nasıl toplanır')
  const yedek = altbilgi(page).locator('.cds--tag').filter({ hasText: 'Yedek modelden' })
  await expect(yedek).toHaveCount(1)
  await expect(yedek).toHaveClass(/cds--tag--gray/)
  await expect(sonCevap(page)).not.toContainText('warning:yerel_yedek')
  await expect(altbilgi(page)).not.toContainText('warning:yerel_yedek')
})
