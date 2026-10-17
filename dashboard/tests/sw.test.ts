import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { inflateSync } from 'node:zlib'

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
  // Düzeltme turu 1 — 3: sessiz yol; başka bir üyenin tuttuğu ucu taşımaz (sunucu 409 der).
  assert.equal(govde.yenile, true)
})

test('abonelik değişti: anahtar yoksa abone olunmaz, hata fırlatılmaz', async () => {
  const sw = kur([], { ok: true, anahtar: null })
  await sw.abonelikDegisti()
  assert.equal(sw.abonelikler.length, 0)
  assert.equal(sw.istekler.length, 1)
})

// C7: `json()` null ya da ilkel bir değer dönerse yük boş nesnedir; bildirim yine gösterilir.
for (const [ad, deger] of [['null', null], ['sayı', 42], ['metin', 'yalnız metin'], ['dizi', ['a']]] as const) {
  test(`push: json() ${ad} dönerse varsayılan bildirim`, async () => {
    const sw = kur()
    await sw.push({ json: () => deger })
    assert.equal(sw.gosterilen.length, 1)
    const { baslik, secenek } = sw.gosterilen[0]
    assert.equal(baslik, 'TEDY')
    assert.equal(secenek.body, '')
    assert.equal(secenek.tag, 'tedy')
    assert.equal((secenek.data as { url: string }).url, '/sinavlar')
  })
}

// C8: rozet tek renkli, saydam zeminli 96 px; simge 192 px kalır.
test('push: rozet tek renkli 96 px dosya, simge 192', async () => {
  const sw = kur()
  await sw.push({ json: () => ({ baslik: 'x' }) })
  const { secenek } = sw.gosterilen[0]
  assert.equal(secenek.icon, '/tedy-192.png')
  assert.equal(secenek.badge, '/tedy-rozet-96.png')
})

// PNG'yi çözer (yalnız 8 bit RGBA/gri+alfa, taramasız): rozet yalnız beyaz ve saydam piksellerden oluşur.
function pngPikselleri(veri: Buffer): { en: number; boy: number; kanal: number; satirlar: Buffer[] } {
  assert.equal(veri.subarray(0, 8).toString('hex'), '89504e470d0a1a0a')
  let i = 8
  let en = 0, boy = 0, tur = 0
  const idat: Buffer[] = []
  while (i < veri.length) {
    const uzunluk = veri.readUInt32BE(i)
    const ad = veri.subarray(i + 4, i + 8).toString('latin1')
    const govde = veri.subarray(i + 8, i + 8 + uzunluk)
    if (ad === 'IHDR') {
      en = govde.readUInt32BE(0); boy = govde.readUInt32BE(4)
      assert.equal(govde[8], 8, 'bit derinliği 8')
      tur = govde[9]
      assert.equal(govde[12], 0, 'taramasız')
    }
    if (ad === 'IDAT') idat.push(govde)
    i += 12 + uzunluk
  }
  const kanal = ({ 4: 2, 6: 4 } as Record<number, number>)[tur]
  assert.ok(kanal, `saydam zeminli renk türü (4 ya da 6) bekleniyordu, gelen ${tur}`)
  const ham = inflateSync(Buffer.concat(idat))
  const satir = en * kanal
  const satirlar: Buffer[] = []
  let onceki = Buffer.alloc(satir)
  for (let y = 0; y < boy; y++) {
    const filtre = ham[y * (satir + 1)]
    const s = Buffer.from(ham.subarray(y * (satir + 1) + 1, (y + 1) * (satir + 1)))
    for (let x = 0; x < satir; x++) {
      const a = x >= kanal ? s[x - kanal] : 0, b = onceki[x], c = x >= kanal ? onceki[x - kanal] : 0
      const tahmin = filtre === 0 ? 0 : filtre === 1 ? a : filtre === 2 ? b : filtre === 3 ? (a + b) >> 1
        : (() => { const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c)
          return pa <= pb && pa <= pc ? a : pb <= pc ? b : c })()
      s[x] = (s[x] + tahmin) & 0xff
    }
    satirlar.push(s)
    onceki = s
  }
  return { en, boy, kanal, satirlar }
}

test('rozet dosyası: 96×96, saydam zemin, yalnız beyaz siluet', () => {
  const { en, boy, kanal, satirlar } = pngPikselleri(readFileSync(new URL('../public/tedy-rozet-96.png', import.meta.url)))
  assert.deepEqual([en, boy], [96, 96])
  let saydam = 0, dolu = 0
  for (const s of satirlar) {
    for (let x = 0; x < en; x++) {
      const p = s.subarray(x * kanal, (x + 1) * kanal)
      const alfa = p[kanal - 1]
      if (alfa === 0) { saydam++; continue }
      dolu++
      for (let k = 0; k < kanal - 1; k++) assert.equal(p[k], 255, 'görünen her piksel beyaz')
    }
  }
  assert.ok(saydam > 96 * 96 * 0.2, 'zemin saydam')
  assert.ok(dolu > 96 * 96 * 0.2, 'siluet var')
})
