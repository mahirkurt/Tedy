import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'

// public/sw.js'i sahte bir `self` ile çalıştırır: tarayıcı olmadan push ve
// bildirim tıklaması davranışını sınar.

const KAYNAK = readFileSync(new URL('../public/sw.js', import.meta.url), 'utf8')
const KOK = 'https://tedy.online'

interface SahteIstemci { url: string; focus: () => Promise<void>; navigate?: (u: string) => Promise<void> }

interface Istek { url: string; secenek?: { method?: string; credentials?: string; body?: string } }

function kur(istemciler: SahteIstemci[] = [], anahtarYaniti: { ok: boolean; anahtar: string | null } = { ok: true, anahtar: 'BAAA' }) {
  const dinleyiciler: Record<string, (e: unknown) => void> = {}
  const gosterilen: { baslik: string; secenek: Record<string, unknown> }[] = []
  const acilan: string[] = []
  const istekler: Istek[] = []
  const abonelikler: { userVisibleOnly: boolean; applicationServerKey: Uint8Array }[] = []
  const fetch = async (url: string, secenek?: Istek['secenek']) => {
    istekler.push({ url, secenek })
    if (url === '/api/bildirim/anahtar') return { ok: anahtarYaniti.ok, json: async () => ({ anahtar: anahtarYaniti.anahtar }) }
    return { ok: true, json: async () => ({ ok: true }) }
  }
  const self = {
    navigator: { userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 8)' },
    addEventListener: (ad: string, fn: (e: unknown) => void) => { dinleyiciler[ad] = fn },
    skipWaiting: () => {},
    clients: {
      claim: async () => {},
      matchAll: async () => istemciler,
      openWindow: async (u: string) => { acilan.push(u) },
    },
    registration: {
      showNotification: async (baslik: string, secenek: Record<string, unknown>) => { gosterilen.push({ baslik, secenek }) },
      pushManager: {
        subscribe: async (s: { userVisibleOnly: boolean; applicationServerKey: Uint8Array }) => {
          abonelikler.push(s)
          return { toJSON: () => ({ endpoint: 'https://fcm.googleapis.com/fcm/send/yeni', keys: { p256dh: 'p', auth: 'a' } }) }
        },
      },
    },
    location: { origin: KOK },
  }
  vm.runInNewContext(KAYNAK, { self, URL, fetch, atob })
  const bekleyen: Promise<unknown>[] = []
  const olay = (ek: Record<string, unknown>) => ({ ...ek, waitUntil: (p: Promise<unknown>) => { bekleyen.push(p) } })
  return {
    gosterilen, acilan, istekler, abonelikler,
    async abonelikDegisti() {
      dinleyiciler.pushsubscriptionchange(olay({}))
      await Promise.all(bekleyen)
    },
    async push(veri: { json?: () => unknown; text?: () => string } | null) {
      dinleyiciler.push(olay({ data: veri }))
      await Promise.all(bekleyen)
    },
    async tikla(url?: string) {
      let kapandi = false
      dinleyiciler.notificationclick(olay({
        notification: { close: () => { kapandi = true }, data: url ? { url } : undefined },
      }))
      await Promise.all(bekleyen)
      return kapandi
    },
  }
}

test('push: JSON yükü başlık, gövde, etiket ve adresi taşır', async () => {
  const sw = kur()
  await sw.push({ json: () => ({ baslik: 'Matematik sınavı', govde: 'Yarın 09:00', etiket: 's1', url: '/sinavlar?sinav=s1' }) })
  assert.equal(sw.gosterilen.length, 1)
  const { baslik, secenek } = sw.gosterilen[0]
  assert.equal(baslik, 'Matematik sınavı')
  assert.equal(secenek.body, 'Yarın 09:00')
  assert.equal(secenek.tag, 's1')
  assert.equal((secenek.data as { url: string }).url, '/sinavlar?sinav=s1') // vm'den gelen nesne: alan alan karşılaştır
})

test('push: JSON olmayan metin gövde olur, başlık TEDY', async () => {
  const sw = kur()
  await sw.push({ json: () => { throw new SyntaxError('bozuk') }, text: () => 'düz metin' })
  const { baslik, secenek } = sw.gosterilen[0]
  assert.equal(baslik, 'TEDY')
  assert.equal(secenek.body, 'düz metin')
  assert.equal(secenek.tag, 'tedy')
  assert.equal((secenek.data as { url: string }).url, '/sinavlar')
})

test('tıklama: navigate reddeden pencerede openWindow mutlak adresle açılır', async () => {
  const odak: string[] = []
  const sw = kur([{
    url: `${KOK}/bugun`,
    focus: async () => { odak.push('focus') },
    navigate: async () => { throw new TypeError('denetlenmeyen istemci') },
  }])
  assert.equal(await sw.tikla('/sinavlar?sinav=s1'), true, 'bildirim kapanmalı')
  assert.deepEqual(odak, ['focus'])
  assert.deepEqual(sw.acilan, [`${KOK}/sinavlar?sinav=s1`])
})

test('tıklama: pencere yoksa openWindow', async () => {
  const sw = kur([])
  await sw.tikla()
  assert.deepEqual(sw.acilan, [`${KOK}/sinavlar`])
})

test('tıklama: başka kökenli pencere yok sayılır', async () => {
  const sw = kur([{ url: 'https://baska.example/x', focus: async () => assert.fail('odaklanmamalı') }])
  await sw.tikla('/sinavlar')
  assert.deepEqual(sw.acilan, [`${KOK}/sinavlar`])
})

test('tıklama: pencere zaten hedefte ise yalnız odaklanır', async () => {
  const olaylar: string[] = []
  const sw = kur([{
    url: `${KOK}/sinavlar?sinav=s1`,
    focus: async () => { olaylar.push('focus') },
    navigate: async () => { olaylar.push('navigate') },
  }])
  await sw.tikla('/sinavlar?sinav=s1')
  assert.deepEqual(olaylar, ['focus'])
  assert.deepEqual(sw.acilan, [])
})

test('tıklama: başka sayfadaki pencere odaklanır ve hedefe gider', async () => {
  const olaylar: string[] = []
  const sw = kur([{
    url: `${KOK}/bugun`,
    focus: async () => { olaylar.push('focus') },
    navigate: async (u: string) => { olaylar.push(`navigate ${u}`) },
  }])
  await sw.tikla('/sinavlar')
  assert.deepEqual(olaylar, ['focus', `navigate ${KOK}/sinavlar`])
  assert.deepEqual(sw.acilan, [])
})

test('abonelik değişti: anahtar alınır, yeniden abone olunur, sunucuya bildirilir', async () => {
  const sw = kur()
  await sw.abonelikDegisti()
  assert.equal(sw.abonelikler.length, 1)
  assert.equal(sw.abonelikler[0].userVisibleOnly, true)
  assert.deepEqual([...sw.abonelikler[0].applicationServerKey], [4, 0, 0])
  const [anahtar, kayit] = sw.istekler
  assert.equal(anahtar.url, '/api/bildirim/anahtar')
  assert.equal(anahtar.secenek?.credentials, 'same-origin')
  assert.equal(kayit.url, '/api/bildirim/abonelik')
  assert.equal(kayit.secenek?.method, 'POST')
  assert.equal(kayit.secenek?.credentials, 'same-origin')
  const govde = JSON.parse(kayit.secenek?.body ?? '{}')
  assert.equal(govde.endpoint, 'https://fcm.googleapis.com/fcm/send/yeni')
  assert.equal(govde.cihaz, 'Android')
})

test('abonelik değişti: anahtar yoksa abone olunmaz, hata fırlatılmaz', async () => {
  const sw = kur([], { ok: true, anahtar: null })
  await sw.abonelikDegisti()
  assert.equal(sw.abonelikler.length, 0)
  assert.equal(sw.istekler.length, 1)
})
