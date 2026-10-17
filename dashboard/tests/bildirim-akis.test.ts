import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  aboneligiTazele, bildirimDurumu, bildirimiAc, bildirimiBanaGecir, bildirimiKapat, BildirimHatasi, CIHAZ_YOK_METNI,
  denemeBilgisi, denemeGonder, DURUM_METNI, ortamiOku, PUSH_ULASILAMADI_METNI, SAHIBI_DEGIL_METNI, sonIstekKazanir,
} from '../src/utils/bildirim.ts'

// Tarayıcı akışları (bildirim.ts'in fetch kullanan yarısı) sahte globallerle: navigator.serviceWorker,
// Notification, PushManager ve fetch. Sunucu yanıtları tek tek verilir; istekler sırayla kaydedilir.

// 'asili': yanıt hiç gelmez (ağ takıldı).
type Yanit = { status: number; govde?: unknown; bozuk?: boolean } | Error | 'asili'
type Istek = { url: string; method: string; govde: Record<string, unknown> | null }

function yanitKur(y: Exclude<Yanit, 'asili'>): Response {
  if (y instanceof Error) throw y
  return {
    ok: y.status >= 200 && y.status < 300,
    status: y.status,
    // Bir vekil ya da Flask hata sayfası HTML döndürür: json() SyntaxError ile düşer.
    json: async () => {
      if (y.bozuk) throw new SyntaxError("Unexpected token '<', \"<!doctype \"... is not valid JSON")
      return y.govde
    },
  } as unknown as Response
}

function ortamKur(o: {
  izin?: 'default' | 'granted' | 'denied'
  abone?: boolean
  yanitlar: Record<string, Yanit | Yanit[]>
}) {
  const istekler: Istek[] = []
  const olaylar: string[] = []
  let abone = o.abone ?? false
  let izin = o.izin ?? 'granted'
  const abonelik = {
    endpoint: 'https://fcm.googleapis.com/fcm/send/test',
    options: { applicationServerKey: Uint8Array.from([4, 0, 0]).buffer },
    toJSON: () => ({ endpoint: 'https://fcm.googleapis.com/fcm/send/test', keys: { p256dh: 'p', auth: 'a' } }),
    unsubscribe: async () => { abone = false; olaylar.push('unsubscribe'); return true },
  }
  const kayit = {
    pushManager: {
      getSubscription: async () => (abone ? abonelik : null),
      subscribe: async () => { abone = true; olaylar.push('subscribe'); return abonelik },
    },
  }
  const g = globalThis as unknown as Record<string, unknown>
  g.window = globalThis
  g.PushManager = function PushManager() {}
  g.Notification = { get permission() { return izin }, requestPermission: async () => { izin = 'granted'; return izin } }
  Object.defineProperty(globalThis, 'navigator', { configurable: true, value: {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', platform: 'Win32', maxTouchPoints: 0,
    serviceWorker: { getRegistration: async () => kayit, register: async () => kayit, ready: Promise.resolve(kayit) },
  } })
  const sira: Record<string, number> = {}
  g.fetch = async (url: string, s?: { method?: string; body?: string }) => {
    const method = s?.method ?? 'GET'
    istekler.push({ url, method, govde: s?.body ? JSON.parse(s.body) : null })
    const anahtar = `${method} ${url}`
    const y = o.yanitlar[anahtar]
    if (!y) throw new Error(`beklenmeyen istek: ${anahtar}`)
    if (Array.isArray(y)) {
      const i = sira[anahtar] ?? 0
      sira[anahtar] = i + 1
      const secilen = y[Math.min(i, y.length - 1)]
      return secilen === 'asili' ? new Promise<Response>(() => {}) : yanitKur(secilen)
    }
    return y === 'asili' ? new Promise<Response>(() => {}) : yanitKur(y)
  }
  return { istekler, olaylar, abone: () => abone }
}

const ANAHTAR = { status: 200, govde: { anahtar: 'BAAA', acik: true } }

async function hataKodu(p: Promise<unknown>): Promise<string> {
  try {
    await p
  } catch (e) {
    assert.ok(e instanceof BildirimHatasi, `BildirimHatasi bekleniyordu, gelen: ${String(e)}`)
    return e.kod
  }
  assert.fail('hata bekleniyordu')
}

// C1: önce ok, sonra json(). HTML hata gövdesi SyntaxError olarak yukarı çıkmaz.
test('C1 aç: anahtar ucu HTML 502 döndürürse sunucu hatası, SyntaxError değil', async () => {
  const o = ortamKur({ izin: 'default', yanitlar: { 'GET /api/bildirim/anahtar': { status: 502, bozuk: true } } })
  assert.equal(await hataKodu(bildirimiAc()), 'sunucu')
  assert.equal(o.abone(), false)
})

test('C1 aç: 200 ama gövde JSON değilse de sunucu hatası', async () => {
  ortamKur({ izin: 'default', yanitlar: { 'GET /api/bildirim/anahtar': { status: 200, bozuk: true } } })
  assert.equal(await hataKodu(bildirimiAc()), 'sunucu')
})

test('C1 deneme: HTML 502 gövdesi sunucu hatası', async () => {
  ortamKur({ abone: true, yanitlar: { 'POST /api/bildirim/deneme': { status: 502, bozuk: true } } })
  assert.equal(await hataKodu(denemeGonder()), 'sunucu')
})

// C3: sunucudaki kayıt silinemese de yerel abonelik bırakılır; sonuç bunu söyler.
test('C3 kapat: DELETE ağda düşerse yerel abonelik yine bırakılır, sonuç "sunucu silinemedi"', async () => {
  const o = ortamKur({ abone: true, yanitlar: { 'DELETE /api/bildirim/abonelik': new TypeError('Failed to fetch') } })
  assert.equal(await bildirimiKapat(), 'sunucu-silinemedi')
  assert.deepEqual(o.olaylar, ['unsubscribe'])
  assert.equal(o.istekler[0].govde?.endpoint, 'https://fcm.googleapis.com/fcm/send/test')
})

test('C3 kapat: 5xx de "sunucu silinemedi"; 200 tamam', async () => {
  ortamKur({ abone: true, yanitlar: { 'DELETE /api/bildirim/abonelik': { status: 503, govde: {} } } })
  assert.equal(await bildirimiKapat(), 'sunucu-silinemedi')
  const o = ortamKur({ abone: true, yanitlar: { 'DELETE /api/bildirim/abonelik': { status: 200, govde: { ok: true } } } })
  assert.equal(await bildirimiKapat(), 'tamam')
  assert.deepEqual(o.olaylar, ['unsubscribe'])
})

// C4: açılıştaki sessiz kayıt `yenile: true` gönderir; cihaz başka üyedeyse hiçbir şey değişmez.
test('C4 tazele: gövde yenile: true taşır', async () => {
  const o = ortamKur({ abone: true, yanitlar: {
    'GET /api/bildirim/anahtar': ANAHTAR, 'POST /api/bildirim/abonelik': { status: 201, govde: { ok: true } } } })
  assert.equal(await aboneligiTazele(), 'bildirildi')
  const kayit = o.istekler.find(i => i.method === 'POST')!
  assert.equal(kayit.govde?.yenile, true)
  assert.equal(kayit.govde?.endpoint, 'https://fcm.googleapis.com/fcm/send/test')
})

test('C4 tazele: 409 sahip_baska → "baska-sahip", abonelik dokunulmaz; kart bunu söyler', async () => {
  const o = ortamKur({ abone: true, yanitlar: {
    'GET /api/bildirim/anahtar': ANAHTAR,
    'POST /api/bildirim/abonelik': { status: 409, govde: { sahip_baska: true } } } })
  assert.equal(await aboneligiTazele(), 'baska-sahip')
  assert.deepEqual(o.olaylar, [])
  assert.equal(o.abone(), true)
  const ortam = await ortamiOku()
  assert.equal(ortam.baskaSahip, true)
  assert.equal(bildirimDurumu(ortam), 'baska-sahip')
  assert.match(DURUM_METNI['baska-sahip'], /^Bu cihaz başka bir aile üyesine kayıtlı/)
})

test('C4 bana geçir: yenile olmadan POST; sonra kart açık der', async () => {
  const o = ortamKur({ abone: true, yanitlar: {
    'GET /api/bildirim/anahtar': ANAHTAR,
    'POST /api/bildirim/abonelik': [{ status: 409, govde: { sahip_baska: true } }, { status: 201, govde: { ok: true } }] } })
  assert.equal(await aboneligiTazele(), 'baska-sahip')
  await bildirimiBanaGecir()
  const gecir = o.istekler.filter(i => i.method === 'POST')[1]
  assert.equal(gecir.govde?.yenile, undefined)
  assert.equal(gecir.govde?.endpoint, 'https://fcm.googleapis.com/fcm/send/test')
  assert.equal(bildirimDurumu(await ortamiOku()), 'acik')
})

test('C4 bana geçir: sunucu reddederse sunucu hatası, durum başka üyede kalır', async () => {
  ortamKur({ abone: true, yanitlar: {
    'GET /api/bildirim/anahtar': ANAHTAR,
    'POST /api/bildirim/abonelik': [{ status: 409, govde: { sahip_baska: true } }, { status: 503, bozuk: true }] } })
  assert.equal(await aboneligiTazele(), 'baska-sahip')
  assert.equal(await hataKodu(bildirimiBanaGecir()), 'sunucu')
  assert.equal(bildirimDurumu(await ortamiOku()), 'baska-sahip')
})

test('C4 tazele: 409 olmayan hata "hata" kalır, kart başka üye demez', async () => {
  ortamKur({ abone: true, yanitlar: {
    'GET /api/bildirim/anahtar': ANAHTAR, 'POST /api/bildirim/abonelik': { status: 503, bozuk: true } } })
  assert.equal(await aboneligiTazele(), 'hata')
  assert.equal(bildirimDurumu(await ortamiOku()), 'acik')
})

// C5: deneme yanıtı ayrıştırılır.
test('C5 deneme: yanıt dört sayıyla döner', async () => {
  ortamKur({ abone: true, yanitlar: { 'POST /api/bildirim/deneme':
    { status: 200, govde: { gonderilen: 1, basarisiz: 1, olu: 0, cihaz: 2 } } } })
  assert.deepEqual(await denemeGonder(), { gonderilen: 1, basarisiz: 1, olu: 0, cihaz: 2 })
})

test('C5 deneme: 404 cihaz yok', async () => {
  ortamKur({ abone: true, yanitlar: { 'POST /api/bildirim/deneme': { status: 404, govde: {} } } })
  assert.equal(await hataKodu(denemeGonder()), 'cihaz-yok')
})

test('C5 deneme bilgisi: başarı, kayıt yok, push servisi', () => {
  assert.deepEqual(denemeBilgisi({ gonderilen: 2, basarisiz: 1, olu: 0, cihaz: 3 }),
    { tur: 'success', metin: 'Deneme bildirimi 2 cihaza gönderildi.' })
  assert.deepEqual(denemeBilgisi({ gonderilen: 0, basarisiz: 0, olu: 0, cihaz: 0 }), { tur: 'error', metin: CIHAZ_YOK_METNI })
  assert.deepEqual(denemeBilgisi({ gonderilen: 0, basarisiz: 0, olu: 2, cihaz: 2 }), { tur: 'error', metin: CIHAZ_YOK_METNI })
  assert.deepEqual(denemeBilgisi({ gonderilen: 0, basarisiz: 2, olu: 0, cihaz: 2 }), { tur: 'error', metin: PUSH_ULASILAMADI_METNI })
  assert.match(PUSH_ULASILAMADI_METNI, /push servisine ulaşılamadı/)
  assert.match(PUSH_ULASILAMADI_METNI, /sonra yeniden deneyin/i)
})

// Düzeltme turu 1 — 6: DELETE 404 bu kişinin listesinde böyle bir cihaz olmadığı demektir (başka bir üyenin
// cihazı). Yerel abonelik bırakılmaz: bırakılsa o üyenin bildirimleri sessizce kesilirdi.
test('T1-6 kapat: DELETE 404 → yerel abonelik bırakılmaz, sonuç "sahibi-degil", kart başka üye der', async () => {
  const o = ortamKur({ abone: true, yanitlar: {
    'GET /api/bildirim/anahtar': ANAHTAR, 'DELETE /api/bildirim/abonelik': { status: 404, govde: { error: 'yok' } } } })
  assert.equal(await bildirimiKapat(), 'sahibi-degil')
  assert.deepEqual(o.olaylar, [])
  assert.equal(o.abone(), true)
  assert.equal(bildirimDurumu(await ortamiOku()), 'baska-sahip')
  assert.equal(SAHIBI_DEGIL_METNI, 'Bu cihaz sizin adınıza kayıtlı değil; bildirimler onun sahibine gitmeye devam eder.')
})

// Düzeltme turu 1 — 2: 409'dan sonra "Bu cihazda aç" cihazı taşır; kart artık başka üye demez. Kapatma da
// eski sonucu unutur.
test('T1-2 aç: 409 sonrası başarılı açma kartı "açık"a döndürür; kapatma tazeleme sonucunu unutur', async () => {
  ortamKur({ abone: true, yanitlar: {
    'GET /api/bildirim/anahtar': ANAHTAR, 'POST /api/bildirim/abonelik': { status: 409, govde: { sahip_baska: true } } } })
  assert.equal(await aboneligiTazele(), 'baska-sahip')
  ortamKur({ abone: false, yanitlar: {
    'GET /api/bildirim/anahtar': ANAHTAR, 'POST /api/bildirim/abonelik': { status: 201, govde: { ok: true } } } })
  await bildirimiAc()
  assert.equal(bildirimDurumu(await ortamiOku()), 'acik')

  ortamKur({ abone: true, yanitlar: {
    'GET /api/bildirim/anahtar': ANAHTAR, 'POST /api/bildirim/abonelik': { status: 409, govde: { sahip_baska: true } },
    'DELETE /api/bildirim/abonelik': { status: 200, govde: { ok: true } } } })
  assert.equal(await aboneligiTazele(), 'baska-sahip')
  assert.equal(await bildirimiKapat(), 'tamam')
  // Aynı tarayıcıda yeniden abone olunursa (sayfa yenilenmeden) eski 409 kartı yanıltmaz.
  ortamKur({ abone: true, yanitlar: { 'GET /api/bildirim/anahtar': ANAHTAR } })
  assert.equal(bildirimDurumu(await ortamiOku()), 'acik')
})

// Düzeltme turu 1 — 4: sekmeye dönüş ve izin olayı sunucu bayrağını yeniden istemez; bilinen bayrak kullanılır.
test('T1-4 ortam: bayrak önbellekten okunursa anahtar ucu çağrılmaz', async () => {
  const o = ortamKur({ abone: true, yanitlar: { 'GET /api/bildirim/anahtar': { status: 200, govde: { anahtar: 'BAAA', acik: false } } } })
  assert.equal(bildirimDurumu(await ortamiOku()), 'acik-bekliyor')
  const once = o.istekler.length
  assert.equal(bildirimDurumu(await ortamiOku({ bayrak: 'onbellek' })), 'acik-bekliyor')
  assert.equal(o.istekler.length, once)
})

// Düzeltme turu 1 — 4: sıra sayacı: eski bir okumanın yanıtı yenisinin üstüne yazmaz.
test('T1-4 sıra: önce başlayıp sonra biten okuma düşer', async () => {
  const sira = sonIstekKazanir()
  let bitir1!: (v: string) => void, bitir2!: (v: string) => void
  const eski = sira(new Promise<string>(r => { bitir1 = r }))
  const yeni = sira(new Promise<string>(r => { bitir2 = r }))
  bitir2('yeni')
  bitir1('eski')
  assert.deepEqual(await Promise.all([eski, yeni]), [{ guncel: false, deger: 'eski' }, { guncel: true, deger: 'yeni' }])
})

// Düzeltme turu 1 — 5: ilk durum iki ağ isteğini sonsuza dek beklemez; süre dolarsa bilinmeyen sayılır.
test('T1-5 ortam: bayrak ve sessiz kayıt yanıt vermezse süre dolunca yerel duruma göre karar verilir', async () => {
  ortamKur({ abone: true, yanitlar: { 'GET /api/bildirim/anahtar': 'asili' } })
  void aboneligiTazele()   // takılı: anahtar isteği hiç dönmez
  const t0 = Date.now()
  const ortam = await ortamiOku({ beklemeMs: 50 })
  assert.ok(Date.now() - t0 < 1000, 'süre sınırı uygulanmalı')
  assert.equal(ortam.sunucuAcik, undefined)
  assert.equal(ortam.baskaSahip, false)
  assert.equal(bildirimDurumu(ortam), 'acik')
})
