import { test, expect, type Page, type Request } from '@playwright/test'
import { createRequire } from 'node:module'
import AxeBuilder from '@axe-core/playwright'
import { mock } from './_audit-fixtures'
import { GORSEL } from './_gorsel-fixtures'
import { bildirimTaklidi } from './_bildirim-taklidi'
import { bugunAc } from './_bugun-fixtures'

// Tonight's study plan on Bugün (spec 2026-10-19 §6.7, §6.8; Görev 7). The
// backend is src/dashboard_api.py's /api/plan/*; here a small in-test server
// keeps the plan's state so a touch is answered the way the real one answers:
// with the whole plan. Every other endpoint is the visual fixture (GORSEL).

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

const ACE = createRequire(import.meta.url).resolve('accessibility-checker-engine/ace.js')
const json = (b: unknown, status = 200) => ({ status, contentType: 'application/json', body: JSON.stringify(b) })
const dk = (s: string) => { const [h, m] = s.split(':').map(Number); return h * 60 + m }
const saat = (n: number) => `${String(Math.floor(n / 60)).padStart(2, '0')}:${String(n % 60).padStart(2, '0')}`

type Blok = {
  id: string; tur: 'calisma' | 'mola' | 'yemek' | 'olay'; bas: number; bit: number
  odev_anahtari: string | null; ders: string | null; baslik: string; adim: string
  parca: number; parca_sayisi: number; tahmin_dk: number; zorluk: string
  durum: 'bekliyor' | 'suruyor' | 'bitti' | 'ertelendi'; ham_dk: number
}

const is = (id: string, bas: string, bit: string, ek: Partial<Blok> = {}): Blok => ({
  id, tur: 'calisma', bas: dk(bas), bit: dk(bit), odev_anahtari: 'matematik|hafta ici',
  ders: 'Matematik', baslik: '2. HAFTA MATEMATİK HAFTA İÇİ ÖDEVİ', adim: 'Sayfa 165, ilk 4 soruyu çöz',
  parca: 0, parca_sayisi: 1, tahmin_dk: dk(bit) - dk(bas), zorluk: 'zor', durum: 'bekliyor', ham_dk: 16, ...ek,
})
const mola = (id: string, bas: number, bit: number): Blok => ({
  id, tur: 'mola', bas, bit, odev_anahtari: null, ders: null, baslik: 'Mola', adim: '',
  parca: 0, parca_sayisi: 1, tahmin_dk: 0, zorluk: 'orta', durum: 'bekliyor', ham_dk: 0,
})

/** Tonight: Matematik in two parts, then Fransızca, dinner at 18:30. */
const AKSAM = (): Blok[] => [
  is('mat0', '17:00', '17:25', { parca: 0, parca_sayisi: 2, ham_dk: 20 }),
  mola('m1', dk('17:25'), dk('17:30')),
  is('mat1', '17:30', '17:50', { parca: 1, parca_sayisi: 2, adim: 'Kalan 8 soruyu çöz', ham_dk: 16 }),
  mola('m2', dk('17:50'), dk('18:00')),
  is('fr', '18:00', '18:20', { odev_anahtari: 'fransizca|s1', ders: 'Fransızca', baslik: 'S1 Les verbes',
    adim: 'Fiil tablosunu doldur', zorluk: 'orta', ham_dk: 16 }),
  { ...mola('yemek', dk('18:30'), dk('19:00')), tur: 'yemek', baslik: 'Yemek' },
]

/** A small stand-in for the plan endpoints: state, touches, and the requests it saw. */
class PlanSunucu {
  durum: string
  bloklar: Blok[]
  haber: string | null = null
  tasinan: unknown[] = []
  plandaOlmayan = 0
  istekler: { yol: string; govde: unknown }[] = []
  basla409 = false
  aksamYok = false
  okumalar = 0
  constructor(durum: string, bloklar: Blok[]) { this.durum = durum; this.bloklar = bloklar }

  yanit() {
    const bloklar = this.bloklar.map(b => ({ ...b, bas_saat: saat(b.bas), bit_saat: saat(b.bit) }))
    const calisma = bloklar.filter(b => b.tur === 'calisma').sort((a, b) => a.bas - b.bas)
    return {
      gun: '2026-09-24', durum: this.durum, bloklar,
      simdiki: calisma.find(b => b.durum === 'suruyor') ?? null,
      siradaki: calisma.find(b => b.durum === 'bekliyor' || b.durum === 'ertelendi') ?? null,
      tasinan: this.tasinan, sigmayan: [], planda_olmayan: this.plandaOlmayan, haber_metni: this.haber,
      aksam_yok: this.aksamYok,
    }
  }

  /** "Bitti" at `simdi`: the block ends now; a break and the next block follow from here. */
  bitir(id: string, simdi: number) {
    const b = this.bloklar.find(x => x.id === id)!
    b.durum = 'bitti'
    b.bit = simdi
    const sonraki = this.bloklar.find(x => x.tur === 'calisma' && x.durum === 'bekliyor')
    this.bloklar = this.bloklar.filter(x => x.tur !== 'mola')
    if (sonraki) {
      this.bloklar.push(mola('m-yeni', simdi, simdi + 5))
      const sure = sonraki.bit - sonraki.bas
      sonraki.bas = simdi + 5
      sonraki.bit = simdi + 5 + sure
    }
    this.bloklar.sort((a, c) => a.bas - c.bas)
  }

  async kur(page: Page, simdi: number) {
    await page.route('**/api/plan/**', async route => {
      const r: Request = route.request()
      const yol = new URL(r.url()).pathname.replace('/api/plan/', '')
      if (r.method() === 'GET') {
        this.okumalar++
        return route.fulfill(json(this.yanit()))
      }
      const govde = r.postDataJSON?.() ?? null
      this.istekler.push({ yol: decodeURIComponent(yol), govde })
      const m = /^blok\/([^/]+)\/(basla|bitti|simdi-degil)$/.exec(yol)
      if (m) {
        const b = this.bloklar.find(x => x.id === m[1])!
        if (m[2] === 'basla') {
          if (this.basla409) return route.fulfill(json({ error: 'Önce süren bloğu bitir.' }, 409))
          b.durum = 'suruyor'
          b.bit = simdi + b.tahmin_dk
          b.bas = simdi
        } else if (m[2] === 'bitti') {
          this.bitir(b.id, simdi)
        } else {
          if (b.durum === 'ertelendi') return route.fulfill(json({ error: 'Bu bloğu bir kez erteledin.' }, 409))
          b.durum = 'ertelendi'
        }
      } else if (yol === 'aksam-yok') {
        this.aksamYok = (govde as { aktif: boolean }).aktif
        this.durum = this.aksamYok ? 'kapali' : 'akis'
      }
      return route.fulfill(json({ ok: true, ...this.yanit() }))
    })
  }
}

async function planAc(page: Page, anlik: string, sunucu: PlanSunucu | null,
  { w = 1440, h = 900, ogrenci = true, rotalar }: {
    w?: number; h?: number; ogrenci?: boolean; rotalar?: (page: Page) => Promise<void>
  } = {}) {
  await page.clock.setFixedTime(new Date(`2026-09-24T${anlik}:00+03:00`))
  await bildirimTaklidi(page, { izin: 'default', abone: false })
  await mock(page, {
    ...GORSEL,
    'auth/me': { email: 'test@tedy.online', name: 'Test User', picture: '', role: 'full', student: ogrenci },
  })
  if (sunucu) await sunucu.kur(page, dk(anlik))
  if (rotalar) await rotalar(page)
  await page.setViewportSize({ width: w, height: h })
  await page.goto('/')
  await page.waitForLoadState('networkidle')
  await page.evaluate(() => document.fonts.ready.then(() => undefined))
}

const kart = (page: Page) => page.locator('section.aksam-plani:not(.aksam-plani--sessiz)')

test('16:30 önizleme: NextThing yerine tek sessiz satır, "Ayrıca" yerinde', async ({ page }) => {
  await planAc(page, '16:30', new PlanSunucu('onizleme', AKSAM()))
  const satir = page.locator('.aksam-plani--onizleme')
  await expect(satir).toContainText("Bu akşam 2 iş · 17:00'de başlıyor")
  await expect(satir).toContainText('İlk iş: Matematik — 2. HAFTA MATEMATİK HAFTA İÇİ ÖDEVİ')
  await expect(page.locator('.next-thing')).toHaveCount(0)
  await expect(kart(page)).toHaveCount(0)
  await expect(page.locator('.today-also')).toBeVisible()
})

test('okul sürerken önizleme satırı okul kartının altında; okul kartı değişmez', async ({ page }) => {
  await planAc(page, '10:15', new PlanSunucu('onizleme', AKSAM()))
  await expect(page.locator('.today-now')).toContainText('İngilizce')
  await expect(page.locator('.aksam-plani--onizleme')).toContainText("17:00'de başlıyor")
  await expect(page.locator('.next-thing')).toHaveCount(0)
})

test('17:05 kart: Başla → Bitti → mola; ara parça Bitti soru sormaz', async ({ page }) => {
  const sunucu = new PlanSunucu('akis', AKSAM())
  await planAc(page, '17:05', sunucu)
  const k = kart(page)
  await expect(k.getByRole('heading', { level: 2 })).toHaveText('Sayfa 165, ilk 4 soruyu çöz')
  await expect(k).toContainText('tahmin 25 dk')
  await expect(k).toContainText('1. parça / 2')
  // The card takes NextThing's and "Ayrıca"'s place; the school card is gone after the last bell.
  await expect(page.locator('.next-thing')).toHaveCount(0)
  await expect(page.locator('.today-also')).toHaveCount(0)

  await k.getByRole('button', { name: 'Başla' }).click()
  await expect(k.getByRole('button', { name: 'Bitti' })).toBeVisible()
  await expect(k).toContainText('Sürüyor · tahminen 25 dk kaldı')
  await expect(k.getByRole('button', { name: 'Başla' })).toHaveCount(0)

  await k.getByRole('button', { name: 'Bitti' }).click()
  await expect(k.getByRole('heading', { level: 2 })).toHaveText('Mola · 5 dk')
  await expect(k).toContainText('Sırada: Matematik · Kalan 8 soruyu çöz')
  expect(sunucu.istekler.map(i => i.yol)).toEqual(['blok/mat0/basla', 'blok/mat0/bitti'])
  expect(sunucu.istekler[1].govde).toEqual({})
  await expect(page.getByText('Ödevin tamamı bitti mi?')).toHaveCount(0)
})

test('son parçanın Bitti\'si sorar; "Evet" tamamlandi:true gönderir', async ({ page }) => {
  const bloklar = AKSAM()
  bloklar[0] = { ...bloklar[0], durum: 'bitti', bit: dk('17:22') }
  bloklar[2] = { ...bloklar[2], durum: 'suruyor', bas: dk('17:30'), bit: dk('17:50') }
  const sunucu = new PlanSunucu('akis', bloklar)
  await planAc(page, '17:40', sunucu)
  const k = kart(page)
  await k.getByRole('button', { name: 'Bitti' }).click()
  await expect(k.getByText('Ödevin tamamı bitti mi?')).toBeVisible()
  expect(sunucu.istekler).toEqual([])
  await k.getByRole('button', { name: 'Evet' }).click()
  await expect(k.getByRole('heading', { level: 2 })).toHaveText('Mola · 5 dk')
  expect(sunucu.istekler).toEqual([{ yol: 'blok/mat1/bitti', govde: { tamamlandi: true } }])
})

test('son parçada "Biraz kaldı" tamamlandi:false gönderir', async ({ page }) => {
  const bloklar = AKSAM()
  bloklar[2] = { ...bloklar[2], durum: 'suruyor', bas: dk('17:30'), bit: dk('17:50') }
  const sunucu = new PlanSunucu('akis', bloklar)
  await planAc(page, '17:40', sunucu)
  await kart(page).getByRole('button', { name: 'Bitti' }).click()
  await kart(page).getByRole('button', { name: 'Biraz kaldı' }).click()
  await expect.poll(() => sunucu.istekler).toEqual([{ yol: 'blok/mat1/bitti', govde: { tamamlandi: false } }])
})

test('listeden düşmüş süren blok için de "Bitti" vardır', async ({ page }) => {
  // The running block comes from the stored snapshot; its homework may have left the list.
  const sunucu = new PlanSunucu('akis', [is('eski', '17:00', '17:20', {
    durum: 'suruyor', odev_anahtari: 'artik|yok', ders: 'Türkçe', baslik: 'Okuma', adim: 'Bir sayfa oku' })])
  await planAc(page, '17:10', sunucu)
  await expect(kart(page).getByRole('button', { name: 'Bitti' })).toBeVisible()
})

test('"Şimdi değil" bir kez; ertelenen blokta yerine metin', async ({ page }) => {
  const sunucu = new PlanSunucu('akis', AKSAM())
  await planAc(page, '17:05', sunucu)
  await kart(page).getByRole('button', { name: 'Şimdi değil' }).click()
  await expect.poll(() => sunucu.istekler.map(i => i.yol)).toEqual(['blok/mat0/simdi-degil'])

  // Only the postponed block is left: the card carries it and says it was postponed once.
  const yalniz = new PlanSunucu('akis', [is('fr', '18:00', '18:20', { durum: 'ertelendi', ders: 'Fransızca' })])
  await page.unrouteAll({ behavior: 'ignoreErrors' })
  await planAc(page, '17:55', yalniz)
  await expect(kart(page)).toContainText('Bu bloğu bir kez erteledin.')
  await expect(kart(page).getByRole('button', { name: 'Şimdi değil' })).toHaveCount(0)
  await expect(kart(page).getByRole('button', { name: 'Başla' })).toBeVisible()
})

test('reddedilen dokunuş sunucunun cümlesini söyler, HTTP metnini değil', async ({ page }) => {
  const sunucu = new PlanSunucu('akis', AKSAM())
  sunucu.basla409 = true
  await planAc(page, '17:05', sunucu)
  const once = sunucu.okumalar
  await kart(page).getByRole('button', { name: 'Başla' }).click()
  const not = kart(page).locator('.aksam-plani__bildirim')
  await expect(not).toContainText('Önce süren bloğu bitir.')
  await expect(not).not.toContainText('409')
  // A refusal reads the plan again, so the card catches up with what the server holds.
  await expect.poll(() => sunucu.okumalar).toBeGreaterThan(once)
})

test('süresi dolmuş oturumun İngilizce cevabı karta düşmez', async ({ page }) => {
  const sunucu = new PlanSunucu('akis', AKSAM())
  await planAc(page, '17:05', sunucu)
  await page.route('**/api/plan/blok/**', r => r.fulfill(json({ error: 'Unauthorized' }, 401)))
  await kart(page).getByRole('button', { name: 'Başla' }).click()
  const not = kart(page).locator('.aksam-plani__bildirim')
  await expect(not).toContainText('Kaydedilemedi')
  await expect(not).not.toContainText('Unauthorized')
})

test('aynı anda iki tık tek istek gönderir', async ({ page }) => {
  const sunucu = new PlanSunucu('akis', AKSAM())
  await planAc(page, '17:05', sunucu)
  await kart(page).getByRole('button', { name: 'Başla' }).dblclick()
  await expect(kart(page).getByRole('button', { name: 'Bitti' })).toBeVisible()
  expect(sunucu.istekler.map(i => i.yol)).toEqual(['blok/mat0/basla'])
})

test('kullanıcının dokunuşu odağı başlığa taşır; akşam bitince sessiz satıra', async ({ page }) => {
  const bloklar = [is('son', '17:00', '17:20', { durum: 'suruyor' })]
  const sunucu = new PlanSunucu('akis', bloklar)
  await planAc(page, '17:10', sunucu)
  await kart(page).getByRole('button', { name: 'Bitti' }).click()
  await kart(page).getByRole('button', { name: 'Evet' }).click()
  const satir = page.locator('.aksam-plani--bitti .aksam-plani__baslik')
  await expect(satir).toHaveText('Bugünlük bu kadar')
  await expect(satir).toBeFocused()
})

test('süre düzeltme: tahmin metninden açılır, PUT dakikayı gönderir', async ({ page }) => {
  const sunucu = new PlanSunucu('akis', AKSAM())
  await planAc(page, '17:05', sunucu)
  await kart(page).getByRole('button', { name: /tahmin 25 dk/ }).click()
  const alan = page.getByRole('spinbutton', { name: /Ödevin tamamı için tahmin/ })
  await expect(alan).toHaveValue('36')
  await alan.fill('45')
  await kart(page).getByRole('button', { name: 'Kaydet' }).click()
  await expect.poll(() => sunucu.istekler).toEqual([{ yol: 'odev/matematik|hafta ici/sure', govde: { dakika: 45 } }])
})

test('haber metni sakin bir satır; null ise hiçbir şey', async ({ page }) => {
  const sunucu = new PlanSunucu('akis', AKSAM())
  sunucu.haber = "17:15'e kadar başlamazsan ailene haber gider."
  await planAc(page, '17:05', sunucu)
  await expect(kart(page).locator('.aksam-plani__haber')).toHaveText("17:15'e kadar başlamazsan ailene haber gider.")
  await page.unrouteAll({ behavior: 'ignoreErrors' })
  await planAc(page, '17:05', new PlanSunucu('akis', AKSAM()))
  await expect(kart(page)).toBeVisible()
  await expect(page.locator('.aksam-plani__haber')).toHaveCount(0)
})

test('yarına kalan ve plana girmeyen eski ödevler birer satır; akşamın tamamı kapalı', async ({ page }) => {
  const sunucu = new PlanSunucu('akis', AKSAM())
  sunucu.tasinan = [{ odev_anahtari: 'fen|hibrit', ders: 'Fen Bilimleri', baslik: 'Ödev (Hibrit 10-16)',
    teslim: '29.09.2026 12:00', kalan_dk: 30 }]
  sunucu.plandaOlmayan = 2
  await planAc(page, '17:05', sunucu)
  await expect(page.getByText('Yarına kaldı: Fen Bilimleri — Ödev (Hibrit 10-16)')).toBeVisible()
  await expect(page.getByText("Planda olmayan 2 eski ödev · İşler'de")).toBeVisible()
  const tamami = page.getByRole('button', { name: 'Bu akşamın tamamı' })
  await expect(tamami).toHaveAttribute('aria-expanded', 'false')
  await tamami.click()
  await expect(page.locator('.aksam-plani__liste')).toContainText('18:00–18:20')
  await expect(page.locator('.aksam-plani__not')).toHaveText('Saatler tahmindir; sıradaki iş, bir önceki bitince başlar.')
})

test('"Bu akşam plan yok" anahtarı yalnız aileye', async ({ page }) => {
  const sunucu = new PlanSunucu('akis', AKSAM())
  await planAc(page, '17:05', sunucu, { ogrenci: true })
  await expect(page.getByRole('switch', { name: 'Bu akşam plan yok' })).toHaveCount(0)

  await page.unrouteAll({ behavior: 'ignoreErrors' })
  const aile = new PlanSunucu('akis', AKSAM())
  await planAc(page, '17:05', aile, { ogrenci: false })
  // Carbon's switch sits under its label, which is the tap target (and the 44px one on a phone).
  await page.locator('.aksam-plani__yok .cds--toggle__label').click()
  await expect.poll(() => aile.istekler).toEqual([{ yol: 'aksam-yok', govde: { aktif: true } }])
  // With the plan off the old flow is back, and the switch stays to turn it on again.
  await expect(page.locator('.next-thing')).toBeVisible()
  await expect(page.getByRole('switch', { name: 'Bu akşam plan yok' })).toHaveAttribute('aria-checked', 'true')
})

test('tatil: anahtar kapalı görünür, tek sessiz satır', async ({ page }) => {
  await planAc(page, '17:05', new PlanSunucu('kapali', []), { ogrenci: false })
  await expect(page.locator('.aksam-plani__tatil')).toHaveText('Bugün tatil, akşam planı yok.')
  await expect(page.getByRole('switch', { name: 'Bu akşam plan yok' })).toHaveAttribute('aria-checked', 'false')
  await expect(page.locator('.next-thing')).toBeVisible()
})

test('JSON\'suz 404 de bayrak kapalı sayılır, arıza değil', async ({ page }) => {
  await planAc(page, '17:05', null, { rotalar: p => p.route('**/api/plan/bugun',
    r => r.fulfill({ status: 404, contentType: 'text/html', body: '<h1>Not Found</h1>' })) })
  await expect(page.locator('.next-thing')).toBeVisible()
  await expect(page.locator('.today-ariza')).toHaveCount(0)
})

test('uç 404 (bayrak kapalı): NextThing görünür, plan kartı yok', async ({ page }) => {
  await bugunAc(page, '2026-09-24T17:05')
  await expect(page.locator('.next-thing')).toBeVisible()
  await expect(page.locator('.aksam-plani')).toHaveCount(0)
})

test('"Bugünlük bu kadar" akşam bitince', async ({ page }) => {
  await planAc(page, '20:40', new PlanSunucu('bitti', []))
  await expect(page.locator('.aksam-plani--bitti')).toContainText('Bugünlük bu kadar')
})

test('odak kipi yalnız kartı bırakır', async ({ page }) => {
  const sunucu = new PlanSunucu('akis', AKSAM())
  sunucu.plandaOlmayan = 1
  await page.addInitScript(() => localStorage.setItem('tedy-focus-mode', 'true'))
  await planAc(page, '17:05', sunucu, { ogrenci: false })
  await expect(kart(page)).toBeVisible()
  await expect(page.locator('.aksam-plani__ek')).toBeHidden()
  await expect(page.locator('.today-tl')).toBeHidden()
})

for (const [boy, w, h] of [['masaustu', 1440, 900], ['telefon', 390, 844]] as const) {
  test(`plan kartı axe ve IBM denetiminden temiz geçer (${boy})`, async ({ page }) => {
    const sunucu = new PlanSunucu('akis', AKSAM())
    sunucu.haber = "17:15'e kadar başlanmazsa haber gider."
    sunucu.plandaOlmayan = 1
    await planAc(page, '17:05', sunucu, { w, h, ogrenci: false })
    await page.getByRole('button', { name: 'Bu akşamın tamamı' }).click()
    const { violations } = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'])
      .analyze()
    expect(violations.map(v => `${v.id}: ${v.nodes.map(n => n.target).join(', ')}`)).toEqual([])

    await page.addScriptTag({ path: ACE })
    type Sonuc = { ruleId: string; value: string[]; message: string; path: { dom: string }; snippet: string }
    const sonuclar: Sonuc[] = await page.evaluate(async () => {
      // @ts-expect-error — `ace` is the injected engine's global
      const rapor = await new window.ace.Checker().check(document, ['IBM_Accessibility'])
      return rapor.results
    })
    const ihlal = sonuclar
      .filter(s => s.value[0] === 'VIOLATION' && s.value[1] === 'FAIL')
      .filter(s => !(s.ruleId === 'aria_id_unique' && /cds--ai-label|cds--toggletip/.test(s.snippet + s.path.dom)))
      .map(s => `${s.ruleId}: ${s.message} — ${s.snippet.slice(0, 120)}`)
    expect(ihlal).toEqual([])
  })
}

test('telefonda yatay kayma yok, her denetim en az 44 px', async ({ page }) => {
  const sunucu = new PlanSunucu('akis', AKSAM())
  sunucu.plandaOlmayan = 1
  await planAc(page, '17:05', sunucu, { w: 390, h: 844, ogrenci: false })
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0)
  const denetimler = [
    kart(page).getByRole('button', { name: 'Başla' }),
    kart(page).getByRole('button', { name: 'Şimdi değil' }),
    kart(page).getByRole('button', { name: /tahmin 25 dk/ }),
    page.getByRole('button', { name: 'Bu akşamın tamamı' }),
    page.locator('.aksam-plani__yok .cds--toggle__label'),
  ]
  for (const d of denetimler) {
    const kutu = await d.boundingBox()
    expect(kutu, String(d)).not.toBeNull()
    expect(kutu!.height, String(d)).toBeGreaterThanOrEqual(44)
    expect(kutu!.width, String(d)).toBeGreaterThanOrEqual(44)
  }
  await kart(page).getByRole('button', { name: 'Başla' }).click()
  const bitti = await kart(page).getByRole('button', { name: 'Bitti' }).boundingBox()
  expect(bitti!.height).toBeGreaterThanOrEqual(44)
})

for (const [boy, w, h] of [['masaustu', 1440, 900], ['telefon', 390, 844]] as const) {
  test(`plan kartı görünüşü (${boy})`, async ({ page }) => {
    const sunucu = new PlanSunucu('akis', AKSAM())
    sunucu.haber = "17:15'e kadar başlanmazsa haber gider."
    sunucu.plandaOlmayan = 1
    await planAc(page, '17:05', sunucu, { w, h, ogrenci: false })
    await expect(page).toHaveScreenshot(`aksam-plani-${boy}.png`, {
      fullPage: true, animations: 'disabled', caret: 'hide', maxDiffPixelRatio: 0.002,
    })
  })
}
