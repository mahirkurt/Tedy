import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { mock, LIVE } from './_audit-fixtures'
import { bildirimOlaylari, bildirimTaklidi, izinDegistir, type Taklit } from './_bildirim-taklidi'
import { bugunAc, SINAV } from './_bugun-fixtures'

// Sınav uyarıları kartı: tarayıcının bildirim API'leri taklit edilir; sunucu
// uçları route ile karşılanır. Gerçek push servisine gidilmez.

// `onceden`: açılıştan önce kurulacak ek yollar (sonra kurulan yol öncekini ezer) — açılıştaki sessiz
// kayıt sayfa yüklenirken gider.
async function sinavlarAc(page: Page, t: Taklit, sunucuAcik = true, onceden?: () => Promise<void>) {
  await bildirimTaklidi(page, t)
  await mock(page, { ...LIVE, 'bildirim/anahtar': { anahtar: 'BAAA', acik: sunucuAcik } })
  await page.route('**/api/bildirim/abonelik', r => r.fulfill({ status: 201, json: { ok: true } }))
  await page.route('**/api/bildirim/deneme', r => r.fulfill({ json: { gonderilen: 1, basarisiz: 0, olu: 0, cihaz: 1 } }))
  await onceden?.()
  await page.goto('/sinavlar')
  await page.locator('#uyarilar').waitFor()
}

const IHLALSIZ = async (page: Page) => {
  const sonuc = await new AxeBuilder({ page }).include('#uyarilar')
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa', 'best-practice']).analyze()
  expect(sonuc.violations).toEqual([])
}

test.describe('Sınav uyarıları kartı', () => {
  test('kapalıdan açığa, deneme ve kapatma', async ({ page }) => {
    await sinavlarAc(page, { izin: 'default', abone: false })
    const kart = page.locator('#uyarilar')
    await expect(kart.getByText('Bu cihazda kapalı.', { exact: true })).toBeVisible()
    const kayit = page.waitForRequest(r => r.url().endsWith('/api/bildirim/abonelik') && r.method() === 'POST')
    await kart.getByRole('button', { name: 'Bu cihazda aç' }).click()
    const govde = (await kayit).postDataJSON()
    expect(govde.endpoint).toBe('https://fcm.googleapis.com/fcm/send/test')
    expect(govde.cihaz).toBeTruthy()
    await expect(kart.getByText(/^Bu cihazda açık\./)).toBeVisible()
    // Tıklanan düğme kalktı; odak gövdeye düşmemeli, durum satırına geçmeli.
    await expect(page.locator('.sinav-uyarilari__durum')).toBeFocused()
    await kart.getByRole('button', { name: 'Deneme bildirimi gönder' }).click()
    await expect(kart.getByText('Deneme bildirimi 1 cihaza gönderildi.')).toBeVisible()
    // C9: kapatma DELETE'i aboneliğin uç noktasını taşır.
    const silme = page.waitForRequest(r => r.url().endsWith('/api/bildirim/abonelik') && r.method() === 'DELETE')
    await kart.getByRole('button', { name: 'Bu cihazda kapat' }).click()
    expect((await silme).postDataJSON()).toEqual({ endpoint: 'https://fcm.googleapis.com/fcm/send/test' })
    await expect(kart.getByText('Bu cihazda kapalı.', { exact: true })).toBeVisible()
    await expect(kart.locator('.cds--inline-notification')).toHaveCount(0)
  })

  test('C9: kayıt 5xx ise genel hata, tarayıcı aboneliği bırakılır', async ({ page }) => {
    await sinavlarAc(page, { izin: 'default', abone: false }, true, async () => {
      await page.route('**/api/bildirim/abonelik', r => r.fulfill({ status: 503, contentType: 'text/html', body: '<!doctype html><h1>503</h1>' }))
    })
    const kart = page.locator('#uyarilar')
    await kart.getByRole('button', { name: 'Bu cihazda aç' }).click()
    await expect(kart.getByText('İşlem tamamlanamadı; biraz sonra yeniden denenebilir.')).toBeVisible()
    await expect(kart.getByText('Bu cihazda kapalı.', { exact: true })).toBeVisible()
    expect(await bildirimOlaylari(page)).toEqual(['subscribe 4,0,0', 'unsubscribe'])
  })

  test('C9: izin penceresinde "engelle": reddedildi denir, düğme kalmaz', async ({ page }) => {
    await sinavlarAc(page, { izin: 'default', abone: false, istemYaniti: 'denied' })
    const kart = page.locator('#uyarilar')
    await kart.getByRole('button', { name: 'Bu cihazda aç' }).click()
    await expect(kart.locator('.sinav-uyarilari__durum')).toHaveText(/^Bildirim izni reddedilmiş\./)
    await expect(kart.locator('.cds--inline-notification')).toContainText('Tarayıcı ayarlarından')
    await expect(kart.getByRole('button')).toHaveCount(0)
    expect(await bildirimOlaylari(page)).toEqual([])
  })

  test('C3: sunucudaki kayıt silinemezse kart uyarır, tarayıcı aboneliği yine bırakılır', async ({ page }) => {
    await sinavlarAc(page, { izin: 'granted', abone: true }, true, async () => {
      await page.route('**/api/bildirim/abonelik', r => r.request().method() === 'DELETE'
        ? r.fulfill({ status: 500, contentType: 'text/html', body: '<!doctype html>' })
        : r.fulfill({ status: 201, json: { ok: true } }))
    })
    const kart = page.locator('#uyarilar')
    await kart.getByRole('button', { name: 'Bu cihazda kapat' }).click()
    await expect(kart.getByText('Bu cihazda kapalı.', { exact: true })).toBeVisible()
    const bilgi = kart.locator('.cds--inline-notification')
    await expect(bilgi).toContainText('Sunucudaki kayıt silinemedi; bildirimler bu cihaza gelmeye devam edebilir.')
    await expect(bilgi).toHaveClass(/cds--inline-notification--warning/)
    expect(await bildirimOlaylari(page)).toEqual(['unsubscribe'])
  })

  test('C2: kayıt okunamazsa kart "Denetleniyor"da kalmaz, işlenmemiş ret olmaz', async ({ page }) => {
    const hatalar: string[] = []
    page.on('pageerror', e => hatalar.push(e.message))
    await sinavlarAc(page, { izin: 'default', abone: false, okumaReddi: 1 })
    const kart = page.locator('#uyarilar')
    await expect(kart.getByText('Bu cihazda kapalı.', { exact: true })).toBeVisible()
    await expect(kart.getByRole('button', { name: 'Bu cihazda aç' })).toBeEnabled()
    expect(hatalar).toEqual([])
  })

  test('C2: eylemden sonraki okuma reddedilirse düğmeler kilitli kalmaz', async ({ page }) => {
    const hatalar: string[] = []
    page.on('pageerror', e => hatalar.push(e.message))
    await sinavlarAc(page, { izin: 'default', abone: false, okumaReddi: 2 })
    const kart = page.locator('#uyarilar')
    const ac = kart.getByRole('button', { name: 'Bu cihazda aç' })
    await ac.click()
    await expect(ac).toBeEnabled()
    await page.waitForTimeout(300)
    expect(hatalar).toEqual([])
  })

  test('C4: cihaz başka üyeye kayıtlıysa sessiz kayıt bir şey değiştirmez; "bana geçir" taşır', async ({ page }) => {
    const kayitlar: Record<string, unknown>[] = []
    await sinavlarAc(page, { izin: 'granted', abone: true }, true, async () => {
      await page.route('**/api/bildirim/abonelik', async r => {
        const govde = r.request().postDataJSON()
        kayitlar.push(govde)
        await (govde.yenile === true
          ? r.fulfill({ status: 409, json: { sahip_baska: true } })
          : r.fulfill({ status: 201, json: { ok: true } }))
      })
    })
    const kart = page.locator('#uyarilar')
    await expect(kart.locator('.sinav-uyarilari__durum')).toHaveText(/^Bu cihaz başka bir aile üyesine kayıtlı/)
    await expect(kart.getByRole('button', { name: 'Deneme bildirimi gönder' })).toHaveCount(0)
    expect(kayitlar).toHaveLength(1)
    expect(kayitlar[0].yenile).toBe(true)
    expect(await bildirimOlaylari(page)).toEqual([])
    await IHLALSIZ(page)
    await kart.getByRole('button', { name: 'Bu cihazda bana geçir' }).click()
    await expect(kart.getByText(/^Bu cihazda açık\./)).toBeVisible()
    await expect(kart.locator('.cds--inline-notification')).toContainText('Bu cihaz artık sizin hesabınıza kayıtlı.')
    expect(kayitlar).toHaveLength(2)
    expect(kayitlar[1]).not.toHaveProperty('yenile')
    expect(kayitlar[1].endpoint).toBe('https://fcm.googleapis.com/fcm/send/test')
    expect(await bildirimOlaylari(page)).toEqual([])
  })

  test('C5: cihazlar var ama push servisine ulaşılamadıysa bunu söyler', async ({ page }) => {
    await sinavlarAc(page, { izin: 'granted', abone: true }, true, async () => {
      await page.route('**/api/bildirim/deneme', r => r.fulfill({ json: { gonderilen: 0, basarisiz: 2, olu: 0, cihaz: 2 } }))
    })
    const kart = page.locator('#uyarilar')
    await kart.getByRole('button', { name: 'Deneme bildirimi gönder' }).click()
    const bilgi = kart.locator('.cds--inline-notification')
    await expect(bilgi).toContainText('push servisine ulaşılamadı')
    await expect(bilgi).toHaveClass(/cds--inline-notification--error/)
    await expect(kart).not.toContainText('hiçbir cihaza ulaşmadı')
  })

  test('C5: deneme 404 ise bu cihazın kaydı yok denir', async ({ page }) => {
    await sinavlarAc(page, { izin: 'granted', abone: true }, true, async () => {
      await page.route('**/api/bildirim/deneme', r => r.fulfill({ status: 404, json: { error: 'yok' } }))
    })
    const kart = page.locator('#uyarilar')
    await kart.getByRole('button', { name: 'Deneme bildirimi gönder' }).click()
    await expect(kart.locator('.cds--inline-notification')).toContainText('bu cihazın kaydı sunucuda yok')
  })

  test('C6: izin kartın dışında değişince kart kendini yeniler', async ({ page }) => {
    await sinavlarAc(page, { izin: 'default', abone: false })
    const durum = page.locator('#uyarilar .sinav-uyarilari__durum')
    await expect(durum).toHaveText('Bu cihazda kapalı.')
    await izinDegistir(page, 'denied')
    await expect(durum).toHaveText(/^Bildirim izni reddedilmiş\./)
  })

  test('C6: olay gelmese de sekmeye dönünce kart yeniden okunur', async ({ page }) => {
    await sinavlarAc(page, { izin: 'granted', abone: true })
    const durum = page.locator('#uyarilar .sinav-uyarilari__durum')
    await expect(durum).toHaveText(/^Bu cihazda açık\./)
    await izinDegistir(page, 'denied', false)
    await page.waitForTimeout(200)
    await expect(durum).toHaveText(/^Bu cihazda açık\./)
    await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')))
    await expect(durum).toHaveText(/^Bildirim izni reddedilmiş\./)
  })

  test('izin reddedilmiş', async ({ page }) => {
    await sinavlarAc(page, { izin: 'denied', abone: false })
    await expect(page.locator('#uyarilar')).toContainText('Tarayıcı ayarlarından')
    await expect(page.locator('#uyarilar').getByRole('button')).toHaveCount(0)
  })

  test('abone ama sunucu uyarıları başlatmamış', async ({ page }) => {
    await sinavlarAc(page, { izin: 'granted', abone: true }, false)
    const kart = page.locator('#uyarilar')
    await expect(kart).toContainText('Bu cihazda açık; sınav uyarıları henüz başlatılmadı.')
    await expect(kart.getByRole('button', { name: 'Deneme bildirimi gönder' })).toHaveCount(0)
    await expect(kart.getByRole('button', { name: 'Bu cihazda kapat' })).toBeVisible()
  })

  test('kapatılan izin penceresi: genel hata değil, "izin verilmedi"', async ({ page }) => {
    await sinavlarAc(page, { izin: 'default', abone: false, istemYaniti: 'default' })
    const kart = page.locator('#uyarilar')
    await kart.getByRole('button', { name: 'Bu cihazda aç' }).click()
    await expect(kart.getByText('İzin verilmedi; bildirimler kapalı kaldı.')).toBeVisible()
    await expect(kart.getByText('Bu cihazda kapalı.', { exact: true })).toBeVisible()
    await expect(kart).not.toContainText('İşlem tamamlanamadı')
  })

  test('desteklenmiyor', async ({ page }) => {
    await sinavlarAc(page, { izin: 'default', abone: false, destek: false })
    await expect(page.locator('#uyarilar')).toContainText('Bu tarayıcı bildirim desteklemiyor.')
  })

  test('iPhone ana ekrana eklenmemiş', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await sinavlarAc(page, { izin: 'default', abone: false, ios: true })
    await expect(page.locator('#uyarilar')).toContainText('Paylaş → Ana Ekrana Ekle')
  })

  test('deneme hiçbir cihaza ulaşmadıysa başarı denmez', async ({ page }) => {
    await sinavlarAc(page, { izin: 'granted', abone: true })
    await page.unroute('**/api/bildirim/deneme')
    await page.route('**/api/bildirim/deneme', r => r.fulfill({ json: { gonderilen: 0 } }))
    const kart = page.locator('#uyarilar')
    await kart.getByRole('button', { name: 'Deneme bildirimi gönder' }).click()
    const bilgi = kart.locator('.cds--inline-notification')
    await expect(bilgi).toContainText('hiçbir cihaza ulaşmadı')
    await expect(bilgi).toHaveClass(/cds--inline-notification--error/)
    await expect(kart).not.toContainText('0 cihaza gönderildi')
  })

  test('axe: kart ihlalsiz', async ({ page }) => {
    await sinavlarAc(page, { izin: 'default', abone: false })
    await IHLALSIZ(page)
  })

  // C9: öbür durumlar da ihlalsiz — reddedildi, iPhone (ana ekran), uyarılar başlatılmamış.
  for (const [ad, t, sunucuAcik, metin] of [
    ['reddedildi', { izin: 'denied', abone: false }, true, 'Tarayıcı ayarlarından'],
    ['iPhone', { izin: 'default', abone: false, ios: true }, true, 'Ana Ekrana Ekle'],
    ['bekliyor', { izin: 'granted', abone: true }, false, 'henüz başlatılmadı'],
  ] as [string, Taklit, boolean, string][]) {
    test(`axe: ${ad} durumunda kart ihlalsiz`, async ({ page }) => {
      await sinavlarAc(page, t, sunucuAcik)
      await expect(page.locator('#uyarilar')).toContainText(metin)
      await IHLALSIZ(page)
    })
  }

  test('manifest ve servis çalışanı sunuluyor', async ({ request }) => {
    const manifest = await request.get('/manifest.webmanifest')
    expect(manifest.ok()).toBeTruthy()
    expect((await manifest.json()).icons).toHaveLength(2)
    const sw = await request.get('/sw.js')
    expect(sw.ok()).toBeTruthy()
    expect(await sw.text()).toContain("addEventListener('push'")
    expect((await request.get('/tedy-192.png')).ok()).toBeTruthy()
    // C8: bildirim rozeti sunuluyor.
    const rozet = await request.get('/tedy-rozet-96.png')
    expect(rozet.ok()).toBeTruthy()
    expect(rozet.headers()['content-type']).toContain('image/png')
  })

  // C22: index.html'in andığı her simge gerçekten sunuluyor.
  test('index.html simge bağlantıları 200 döner', async ({ page, request }) => {
    await mock(page, LIVE)
    await page.goto('/')
    const adresler = await page.locator('head link[rel~="icon"], head link[rel="apple-touch-icon"], head link[rel="manifest"]')
      .evaluateAll(l => l.map(e => (e as HTMLLinkElement).getAttribute('href')!))
    expect(adresler).toContain('/favicon-32.png')
    for (const a of adresler) {
      const y = await request.get(a)
      expect(y.status(), a).toBe(200)
      expect(y.headers()['content-type'], a).not.toContain('text/html')
    }
  })
})

const KTT = {
  ...SINAV('ktt', 'Matematik KTT', '2026-09-28T09:00:00'), course: 'Matematik',
  konular: ['Tam sayılar', 'Rasyonel sayılar', 'Mutlak değer', 'Oran'],
  kaynaklar: [{ tur: 'ders_karti', etiket: 'Matematik ders içeriği · 2. Hafta 21 Eyl. - 27 Eyl.',
    alinti: '28 EYLÜL PAZARTESİ günü yapılacak olan Matematik KTT', baglanti: '/dersler?hafta=2.%20Hafta' }],
  ilkTespit: '2026-09-24T08:00:00', degisti: null, tarihBelirsiz: false,
}
const QUIZ = { ...SINAV('quiz', 'Irregular Verbs Quiz', null as unknown as string), course: 'İngilizce', date: null,
  hafta: '2026-09-28', tarihBelirsiz: true, konular: [], kaynaklar: [], ilkTespit: '2026-09-20T08:00:00',
  degisti: '2026-09-24T07:00:00' }
const SINAVLAR = { exams: [KTT, QUIZ], stats: { upcoming: 2, past: 0, averageGrade: null },
  tespit: { uretildi: '2026-09-24T10:00:00', incelenmedi: 2 } }

test.describe('Sınavlar panoda', () => {
  test('Bugün: en yakın sınav konularıyla, renkli çip yok', async ({ page }) => {
    await bugunAc(page, '2026-09-24T10:15', { exams: SINAVLAR })
    const onizleme = page.locator('.sinav-onizleme')
    await expect(onizleme).toContainText('Matematik KTT')
    await expect(onizleme).toContainText('Konular: Tam sayılar, Rasyonel sayılar, Mutlak değer +1 konu')
    await expect(onizleme.getByRole('link', { name: /Kaynak: Matematik ders içeriği/ })).toBeVisible()
    await expect(onizleme.getByRole('link', { name: 'Sınav uyarıları' })).toHaveAttribute('href', '/sinavlar#uyarilar')
    await expect(onizleme.locator('.cds--tag')).toHaveCount(0)
    await expect(page.locator('.today-exams', { hasText: 'Matematik KTT' })).toHaveCount(0)
    await onizleme.getByRole('button').click()
    await expect(page).toHaveURL(/\/sinavlar\?sinav=ktt$/)
    await expect(page.locator('#sinav-ktt')).toContainText('Mutlak değer')
  })

  // C13: önizleme bağlantıları uygulama içinde gezinir (sayfa yeniden yüklenmez); yeni sekme isteyen tık
  // tarayıcıya kalır. Sınavlar kartının kaynak bağlantısı aynı kuralı uygular.
  test('C13: Bugün önizlemesi SPA içinde gezinir, ctrl-tık yeni sekme açar', async ({ page, context }) => {
    await bildirimTaklidi(page, { izin: 'default', abone: false })
    await bugunAc(page, '2026-09-24T10:15', { exams: SINAVLAR, 'bildirim/anahtar': { anahtar: 'BAAA', acik: true } })
    const baglanti = page.locator('.sinav-onizleme').getByRole('link', { name: 'Sınav uyarıları' })
    await page.evaluate(() => { (window as unknown as { __ayniSayfa: boolean }).__ayniSayfa = true })
    const [yeni] = await Promise.all([context.waitForEvent('page'), baglanti.click({ modifiers: ['ControlOrMeta'] })])
    await yeni.close()
    expect(new URL(page.url()).pathname).toBe('/')
    await baglanti.click()
    await expect(page).toHaveURL(/\/sinavlar#uyarilar$/)
    await expect(page.locator('#uyarilar')).toBeVisible()
    expect(await page.evaluate(() => (window as unknown as { __ayniSayfa?: boolean }).__ayniSayfa)).toBe(true)
  })

  test('C13: Sınavlar kaynak bağlantısı ctrl-tıkta sayfayı değiştirmez', async ({ page, context }) => {
    await bildirimTaklidi(page, { izin: 'default', abone: false })
    await page.clock.setFixedTime(new Date('2026-09-24T10:30:00'))
    await mock(page, { ...LIVE, exams: SINAVLAR, 'bildirim/anahtar': { anahtar: 'BAAA', acik: true } })
    await page.goto('/sinavlar?sinav=ktt')
    const kaynak = page.locator('#sinav-ktt').getByRole('link', { name: /Matematik ders içeriği/ })
    const [yeni] = await Promise.all([context.waitForEvent('page'), kaynak.click({ modifiers: ['ControlOrMeta'] })])
    await yeni.close()
    await expect(page).toHaveURL(/\/sinavlar\?sinav=ktt$/)
    await page.evaluate(() => { (window as unknown as { __ayniSayfa: boolean }).__ayniSayfa = true })
    await kaynak.click()
    await expect(page).toHaveURL(/\/dersler\?hafta=2\.%20Hafta$/)
    expect(await page.evaluate(() => (window as unknown as { __ayniSayfa?: boolean }).__ayniSayfa)).toBe(true)
  })

  // C15: aynı sayfadayken ?sinav= değişirse (bildirim tıklaması, önizleme) o kart açılır ve kaydırılır.
  test('C15: ?sinav= sayfa açıkken değişince ilgili kart açılır', async ({ page }) => {
    await bildirimTaklidi(page, { izin: 'default', abone: false })
    await page.clock.setFixedTime(new Date('2026-09-24T10:30:00'))
    await mock(page, { ...LIVE, exams: SINAVLAR, 'bildirim/anahtar': { anahtar: 'BAAA', acik: true } })
    await page.setViewportSize({ width: 1440, height: 500 })
    await page.goto('/sinavlar?sinav=ktt')
    await expect(page.locator('#sinav-ktt')).toContainText('Mutlak değer')
    const quiz = page.locator('#sinav-quiz')
    await expect(quiz).not.toContainText('Tarih belirsiz: duyuruda gün yazmıyor.')
    await page.evaluate(() => {
      history.pushState({}, '', '/sinavlar?sinav=quiz')
      window.dispatchEvent(new PopStateEvent('popstate'))
    })
    await expect(quiz).toContainText('Tarih belirsiz: duyuruda gün yazmıyor.')
    await expect(quiz).toBeInViewport()
  })

  test('İşler: Yeni ve Değişti etiketleri ve incelenemedi notu', async ({ page }) => {
    await page.clock.setFixedTime(new Date('2026-09-24T10:30:00'))
    await mock(page, { ...LIVE, exams: SINAVLAR })
    await page.goto('/isler')
    const satir = (ad: string) => page.locator('.exams-ahead__row', { hasText: ad })
    await expect(satir('Matematik KTT').getByText('Yeni', { exact: true })).toBeVisible()
    await expect(satir('Irregular Verbs Quiz').getByText('Değişti', { exact: true })).toBeVisible()
    await expect(satir('Irregular Verbs Quiz')).toContainText('28 Eyl haftası')
    await expect(page.getByText('Bazı ders duyuruları incelenemedi; sınav listesi eksik olabilir.')).toBeVisible()
  })

  test('Sınavlar: tarih belirsiz ve kaynak alıntısı', async ({ page }) => {
    await bildirimTaklidi(page, { izin: 'default', abone: false })
    await page.clock.setFixedTime(new Date('2026-09-24T10:30:00'))
    await mock(page, { ...LIVE, exams: SINAVLAR, 'bildirim/anahtar': { anahtar: 'BAAA', acik: true } })
    await page.goto('/sinavlar?sinav=quiz')
    const kart = page.locator('#sinav-quiz')
    await expect(kart).toContainText('Tarih belirsiz: duyuruda gün yazmıyor.')
    await page.goto('/sinavlar?sinav=ktt')
    await expect(page.locator('#sinav-ktt blockquote')).toContainText('28 EYLÜL PAZARTESİ')
    const sonuc = await new AxeBuilder({ page }).include('#sinav-ktt').withTags(['wcag2a', 'wcag2aa', 'wcag22aa']).analyze()
    expect(sonuc.violations).toEqual([])
  })
})

// Tüm gün sınav ("2026-09-28", saat yok) tarayıcının bölgesinden bağımsız
// olarak o yerel gündür: UTC gece yarısı olarak okununca İstanbul'da 03:00
// görünüyordu.
test.describe('Tüm gün sınav, İstanbul tarayıcısı', () => {
  test.use({ timezoneId: 'Europe/Istanbul' })
  const GUN = { ...SINAV('gun', 'Fen Bilimleri KTT', '2026-09-28'), course: 'Fen Bilimleri', allDay: true,
    konular: ['Hücre'], kaynaklar: [], ilkTespit: '2026-09-01T08:00:00', degisti: null, tarihBelirsiz: false }
  const VERI = { exams: [GUN], stats: { upcoming: 1, past: 0, averageGrade: null }, tespit: null }

  test('Bugün: önizleme günü yazar, saat uydurmaz', async ({ page }) => {
    await bugunAc(page, '2026-09-24T07:30:00+03:00', { exams: VERI })
    const onizleme = page.locator('.sinav-onizleme')
    await expect(onizleme).toContainText('Fen Bilimleri KTT')
    await expect(onizleme.locator('.today-also__due')).toHaveText('Pazartesi')
    await expect(onizleme).not.toContainText('03:00')
    await expect(onizleme.locator('.today-also__due')).not.toHaveText(/\d{2}:\d{2}/)
  })

  test('Sınavlar: kart tarihi "28 Eyl", saatsiz', async ({ page }) => {
    await bildirimTaklidi(page, { izin: 'default', abone: false })
    await page.clock.setFixedTime(new Date('2026-09-24T07:30:00+03:00'))
    await mock(page, { ...LIVE, exams: VERI, 'bildirim/anahtar': { anahtar: 'BAAA', acik: true } })
    await page.goto('/sinavlar')
    await expect(page.locator('#sinav-gun .exam-card__date')).toHaveText('28 Eyl')
  })
})

test.describe('İncelenemedi notu liste boşken de görünür', () => {
  const BOS = { exams: [], stats: { upcoming: 0, past: 0, averageGrade: null },
    tespit: { uretildi: '2026-09-24T10:00:00', incelenmedi: 2 } }
  const NOT = 'Bazı ders duyuruları incelenemedi; sınav listesi eksik olabilir.'

  test('İşler', async ({ page }) => {
    await page.clock.setFixedTime(new Date('2026-09-24T10:30:00'))
    await mock(page, { ...LIVE, exams: BOS })
    await page.goto('/isler')
    await expect(page.getByText(NOT)).toBeVisible()
  })

  test('Sınavlar', async ({ page }) => {
    await bildirimTaklidi(page, { izin: 'default', abone: false })
    await page.clock.setFixedTime(new Date('2026-09-24T10:30:00'))
    await mock(page, { ...LIVE, exams: BOS, 'bildirim/anahtar': { anahtar: 'BAAA', acik: true } })
    await page.goto('/sinavlar')
    await expect(page.getByText(NOT)).toBeVisible()
  })
})

// Açılışta abonelik sessizce yeniden bildirilir (son inceleme, Important 3): sunucu cihazı
// düşürmüş olabilir; tarayıcıda abonelik ve izin varsa pano onu bir kez yeniden gönderir.
test.describe('Açılışta abonelik tazeleme', () => {
  async function bugunTaklitle(page: Page, t: Taklit) {
    await bildirimTaklidi(page, t)
    const kayitlar: { endpoint: string }[] = []
    await page.route('**/api/bildirim/abonelik', async r => {
      if (r.request().method() === 'POST') kayitlar.push(r.request().postDataJSON())
      await r.fulfill({ status: 201, json: { ok: true } })
    })
    await mock(page, { ...LIVE, 'bildirim/anahtar': { anahtar: 'BAAA', acik: true } })
    return kayitlar
  }

  test('izin ve abonelik varken açılışta bir kez yeniden gönderilir', async ({ page }) => {
    const kayitlar = await bugunTaklitle(page, { izin: 'granted', abone: true })
    await page.goto('/bugun')
    await expect.poll(() => kayitlar.length).toBe(1)
    expect(kayitlar[0].endpoint).toBe('https://fcm.googleapis.com/fcm/send/test')
    expect(await bildirimOlaylari(page)).toEqual([])   // aynı anahtar: yeniden abone olunmaz
  })

  test('anahtar değişmişse çıkılır, sunucunun anahtarıyla yeniden abone olunur, sonra gönderilir', async ({ page }) => {
    const kayitlar = await bugunTaklitle(page, { izin: 'granted', abone: true, abonelikAnahtari: [4, 9, 9] })
    await page.goto('/bugun')
    await expect.poll(() => kayitlar.length).toBe(1)
    expect(await bildirimOlaylari(page)).toEqual(['unsubscribe', 'subscribe 4,0,0'])
  })

  test('izin yoksa ya da abonelik yoksa hiçbir şey gönderilmez', async ({ page }) => {
    const kayitlar = await bugunTaklitle(page, { izin: 'granted', abone: false })
    await page.goto('/bugun')
    await page.locator('.today').first().waitFor()
    await page.waitForTimeout(500)
    expect(kayitlar).toEqual([])
  })
})
