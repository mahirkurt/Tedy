import assert from 'node:assert/strict'
import { test } from 'node:test'
import { soruGonder, planGonder, okurHatasi, IstekHatasi } from '../src/asistan/akisIstemcisi.ts'
import type { TedyOlayi } from '../src/asistan/olayEslemesi.ts'

const sse = (...cerceveler: [string, unknown][]) => cerceveler.map(([a, v]) => `event: ${a}\ndata: ${JSON.stringify(v)}\n\n`).join('')
const akisYaniti = (govde: string, parca = 7) => new Response(new ReadableStream({
  start(c) { const b = new TextEncoder().encode(govde); for (let i = 0; i < b.length; i += parca) c.enqueue(b.slice(i, i + parca)); c.close() },
}), { headers: { 'Content-Type': 'text/event-stream' } })
const json = (v: unknown, durum = 200) => new Response(JSON.stringify(v), { status: durum, headers: { 'Content-Type': 'application/json' } })
const PAYLOAD = { answer: 'cevap', citations: [], safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '', meta: { model: 'm' } }

function sahte(yanitlar: Record<string, () => Response>) {
  const cagrilar: string[] = []
  const f = (async (url: string) => { cagrilar.push(url); return yanitlar[url]() }) as unknown as typeof fetch
  return { f, cagrilar }
}

test('akış parça parça okunur; /chat çağrılmaz', async () => {
  const { f, cagrilar } = sahte({ '/api/assistant/stream': () => akisYaniti(sse(['tool_start', { name: 'x' }], ['answer', { payload: PAYLOAD }], ['done', {}])) })
  const olaylar: TedyOlayi[] = []
  await soruGonder({}, o => olaylar.push(o), new AbortController().signal, f)
  assert.deepEqual(olaylar.map(o => o.ad), ['tool_start', 'answer', 'done'])
  assert.deepEqual(cagrilar, ['/api/assistant/stream'])
})

test('cevapsız kapanan akış /chat yedeğine düşer, önce akis_dustu', async () => {
  const { f, cagrilar } = sahte({ '/api/assistant/stream': () => akisYaniti(sse(['answer_delta', { text: 'yarım' }])),
    '/api/assistant/chat': () => json(PAYLOAD) })
  const olaylar: TedyOlayi[] = []
  await soruGonder({}, o => olaylar.push(o), new AbortController().signal, f)
  assert.deepEqual(olaylar.map(o => o.ad), ['answer_delta', 'akis_dustu', 'answer'])
  assert.deepEqual(cagrilar, ['/api/assistant/stream', '/api/assistant/chat'])
})

test('answer sonrası gelen error yok sayılır (ikinci cevap yok)', async () => {
  const { f, cagrilar } = sahte({ '/api/assistant/stream': () => akisYaniti(sse(['answer', { payload: PAYLOAD }], ['error', { error: 'x' }])) })
  const olaylar: TedyOlayi[] = []
  await soruGonder({}, o => olaylar.push(o), new AbortController().signal, f)
  assert.deepEqual(olaylar.map(o => o.ad), ['answer'])
  assert.equal(cagrilar.length, 1)
})

test('iki uç da düşerse IstekHatasi, okura Türkçe cümle', async () => {
  const { f } = sahte({ '/api/assistant/stream': () => json({ error: 'session_required' }, 401),
    '/api/assistant/chat': () => json({ error: 'session_required' }, 401) })
  await assert.rejects(soruGonder({}, () => {}, new AbortController().signal, f), (e: unknown) => {
    assert.ok(e instanceof IstekHatasi); assert.equal((e as IstekHatasi).durum, 401)
    assert.equal(okurHatasi(e), 'Oturumun sona ermiş; sayfayı yenileyip yeniden giriş yap.')
    return true
  })
  assert.equal(okurHatasi(new IstekHatasi('Bilinmeyen öğretmen modu.', 400)), 'Bilinmeyen öğretmen modu.')
  assert.equal(okurHatasi(new IstekHatasi('HTTP 502', 502)), 'Asistan yanıtı alınamadı.')
  assert.equal(okurHatasi(new TypeError('Failed to fetch')), 'Asistan yanıtı alınamadı.')
})

test('iptal yedeğe düşmez', async () => {
  const kontrol = new AbortController()
  const f = (async (_u: string, init?: RequestInit) => {
    kontrol.abort()
    throw Object.assign(new Error('aborted'), { name: 'AbortError', signal: init?.signal })
  }) as unknown as typeof fetch
  await assert.rejects(soruGonder({}, () => {}, kontrol.signal, f), { name: 'AbortError' })
})

test('plan klasik uca gider', async () => {
  const { f, cagrilar } = sahte({ '/api/assistant/plan': () => json({ ...PAYLOAD, plan_blocks: [{ day: 'Pzt' }] }) })
  const p = await planGonder({}, new AbortController().signal, f)
  assert.equal(p.plan_blocks.length, 1)
  assert.deepEqual(cagrilar, ['/api/assistant/plan'])
})

test('bozuk JSON çerçevesi atlanır; olay işleyicisinin hatası yutulmaz (okur cevapsız ve hatasız kalmaz)', async () => {
  const bozuk = 'event: tool_start\ndata: {bozuk\n\n'
  const { f } = sahte({ '/api/assistant/stream': () => akisYaniti(bozuk + sse(['answer', { payload: PAYLOAD }])),
    '/api/assistant/chat': () => json(PAYLOAD) })
  const olaylar: string[] = []
  await assert.rejects(soruGonder({}, o => { olaylar.push(o.ad); if (o.ad === 'answer') throw new TypeError('eşleme hatası') },
    new AbortController().signal, f), /eşleme hatası/)
  assert.ok(!olaylar.includes('tool_start'))     // bozuk çerçeve işleyiciye hiç gitmedi
})
