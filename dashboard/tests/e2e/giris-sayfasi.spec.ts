import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { createRequire } from 'node:module'
import { girisAc, gsiBekleyen, gsiEngelli, gsiHazir, oturumYok, GSI_ADRESI } from './_gsi-sahte'

// Giriş sayfası yenilemesi (2026-10-15; spec docs/superpowers/specs/2026-10-15-giris-sayfasi-yenileme-design.md).
// Measured before: a blocked Google script left the page with no button and no sentence (D3); nothing was
// shown while a credential was checked; on a 4K screen Google's px-drawn button stayed at half the page's
// scale; a 390 px phone scrolled 48 px of nothing; the form floated in the middle of the white half.
// Google's real script is never loaded here (_gsi-sahte.ts).

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

const ACE = createRequire(import.meta.url).resolve('accessibility-checker-engine/ace.js')
const baslik = (page: Page) => page.getByRole('heading', { level: 1, name: "TEDY'ye giriş yap" })
const dugme = (page: Page) => page.locator('.sahte-gsi')

async function kimlikVer(page: Page) {
  await dugme(page).click()
}

test.describe('layout', () => {
  test('the page names itself, the school and what Google sends', async ({ page }) => {
    await girisAc(page)
    await expect(baslik(page)).toBeVisible()
    await expect(page.getByRole('banner').getByRole('img', { name: 'TEDY' })).toBeVisible()
    await expect(page.getByRole('banner')).toContainText('TED Rönesans Koleji')
    await expect(page.getByRole('main')).toContainText('Yalnız ailenin tanımlı Google hesaplarıyla giriş yapılır.')
    const altbilgi = page.getByRole('contentinfo')
    // True to the code: /api/auth/login reads the e-mail, the name and the picture from Google's token.
    await expect(altbilgi).toContainText("şifren TEDY'ye gelmez")
    await expect(altbilgi).toContainText('yalnız adını, e-posta adresini ve profil fotoğrafını alır')
    await expect(altbilgi).toContainText('TED Rönesans Koleji · 2026')
  })

  for (const [w, h] of [[1440, 900], [390, 844]] as const) {
    test(`one left keyline and a 48 px Google button as wide as the column (${w})`, async ({ page }) => {
      await girisAc(page, w, h)
      const x = async (sel: string) => Math.round((await page.locator(sel).first().boundingBox())!.x)
      const xler = [
        await x('.login-page__title'), await x('.login-page__intro'), await x('.login-page__gsi'),
        await x('.login-page__helper'), await x('.login-page__footer-text'),
      ]
      expect(Math.max(...xler) - Math.min(...xler), JSON.stringify(xler)).toBeLessThanOrEqual(1)
      if (w === 390) expect(xler[0]).toBe(16)
      const kutu = (await dugme(page).boundingBox())!
      const sutun = (await page.locator('.login-page__gsi').boundingBox())!
      expect(Math.round(kutu.height)).toBe(48)
      expect(Math.abs(kutu.width - sutun.width), `düğme ${kutu.width} / sütun ${sutun.width}`).toBeLessThanOrEqual(2)
    })
  }

  test('on a wide screen the form sits on the grid, not in the middle of the white half', async ({ page }) => {
    await girisAc(page, 1440, 900)
    const bant = (await page.getByRole('banner').boundingBox())!
    const form = (await page.locator('.login-page__title').boundingBox())!
    // 10/16 of the width is the band; the form starts 2rem (16 px margin + 16 px padding) to its right.
    expect(Math.round(bant.width)).toBe(900)
    expect(Math.round(form.x)).toBe(900 + 32)
  })

  for (const [w, h] of [[320, 640], [390, 844], [1440, 900], [3840, 2160]] as const) {
    test(`nothing scrolls sideways, and a phone does not scroll at all (${w})`, async ({ page }) => {
      await girisAc(page, w, h)
      const { yana, asagi } = await page.evaluate(() => ({
        yana: document.documentElement.scrollWidth - window.innerWidth,
        asagi: document.documentElement.scrollHeight - window.innerHeight,
      }))
      expect(yana).toBeLessThanOrEqual(0)
      if (w === 390) expect(asagi, 'telefonda boş kayma').toBeLessThanOrEqual(0)
    })
  }

  test('on a 4K screen the heading and Google’s button are twice their full-HD size', async ({ page }) => {
    const olc = async (w: number, h: number) => {
      await girisAc(page, w, h)
      const yazi = await baslik(page).evaluate(el => parseFloat(getComputedStyle(el).fontSize))
      const k = (await dugme(page).boundingBox())!
      return { yazi, boy: k.height, en: k.width }
    }
    const hd = await olc(1920, 1080)
    const uhd = await olc(3840, 2160)
    expect(uhd.yazi / hd.yazi).toBeCloseTo(2, 1)
    expect(uhd.boy / hd.boy).toBeCloseTo(2, 1)
    expect(uhd.en / hd.en).toBeGreaterThan(1.8)
  })
})

test.describe('states', () => {
  test('while Google’s script loads: nothing, then a skeleton, then an honest warning', async ({ page }) => {
    await page.clock.install({ time: new Date('2026-10-15T10:30:00+03:00') })
    await oturumYok(page)
    const birak = await gsiBekleyen(page)
    await page.goto('/')
    await expect(baslik(page)).toBeVisible()
    const yuva = page.locator('.login-page__gsi')
    await expect(yuva.locator('.cds--skeleton__placeholder')).toHaveCount(0)
    await page.clock.runFor(450)
    await expect(yuva.locator('.cds--skeleton__placeholder')).toBeVisible()
    await expect(yuva).toHaveAttribute('aria-busy', 'true')
    // aria-busy asks a screen reader to wait on the slot; the status line beside it says why.
    await expect(page.locator('.login-page__durum')).toHaveText('Google giriş düğmesi yükleniyor')
    // Same height before and after: nothing under the slot jumps when the button arrives.
    const iskeletBoyu = (await yuva.boundingBox())!.height
    await page.clock.runFor(10_000)
    const uyari = page.locator('.cds--inline-notification--warning')
    await expect(uyari).toContainText('Google düğmesi gecikiyor')
    await expect(uyari).toContainText('Bağlantın yavaş olabilir. Biraz bekle ya da yeniden dene.')
    await expect(page.getByRole('button', { name: 'Yeniden dene' })).toBeVisible()
    birak()
    await expect(dugme(page)).toBeVisible()
    await expect(uyari).toHaveCount(0)
    await expect(yuva).not.toHaveAttribute('aria-busy', 'true')
    expect((await yuva.boundingBox())!.height).toBe(iskeletBoyu)
  })

  test('a blocked script says so and a retry brings the button', async ({ page }) => {
    await oturumYok(page)
    await gsiEngelli(page)
    await page.goto('/')
    const hata = page.getByRole('alert')
    await expect(hata).toContainText('Google düğmesi yüklenemedi')
    await expect(hata).toContainText('engelleyici')
    await page.unroute(GSI_ADRESI)
    await gsiHazir(page)
    await page.getByRole('button', { name: 'Yeniden dene' }).click()
    await expect(dugme(page)).toBeVisible()
    await expect(page.getByText('Google düğmesi yüklenemedi')).toHaveCount(0)
    // Focus does not fall to <body> when the retry button goes (talimatname [3.8-8]).
    await expect(baslik(page)).toBeFocused()
  })

  test('a script that loads without Google’s API (a blocker’s empty answer) is a failure, not a blank', async ({ page }) => {
    await oturumYok(page)
    await page.route(GSI_ADRESI, r => r.fulfill({ status: 200, contentType: 'text/javascript', body: '/* engellendi */' }))
    await page.goto('/')
    await expect(page.getByRole('alert')).toContainText('Google düğmesi yüklenemedi')
  })

  test('while the credential is checked: one InlineLoading in the button’s place', async ({ page }) => {
    await girisAc(page)
    let cevapla!: (durum: number) => void
    const durum = new Promise<number>(r => { cevapla = r })
    await page.route('**/api/auth/login', async r => {
      const s = await durum
      await r.fulfill({ status: s, contentType: 'application/json', body: JSON.stringify({ error: 'Bu hesapla giris yapilamaz' }) })
    })
    await kimlikVer(page)
    const yukleniyor = page.locator('.login-page .cds--inline-loading')
    await expect(yukleniyor).toHaveCount(1)
    await expect(yukleniyor).toContainText('Giriş yapılıyor…')
    await expect(dugme(page)).toBeHidden()
    cevapla(403)
    const hata = page.getByRole('alert')
    await expect(hata).toContainText('Bu hesap tanımlı değil')
    await expect(hata).toContainText('Bu Google hesabıyla giriş yapılamaz. Ailenin tanımlı hesabıyla dene.')
    await expect(page.getByText('giris yapilamaz')).toHaveCount(0)   // the server's own string never shows (D4)
    await expect(yukleniyor).toHaveCount(0)
    await expect(dugme(page)).toBeVisible()
  })

  test('a server error and a dropped connection are each their own sentence', async ({ page }) => {
    await girisAc(page)
    await page.route('**/api/auth/login', r => r.fulfill({
      status: 401, contentType: 'application/json', body: '{"error": "Invalid token: Wrong number of segments"}',
    }))
    await kimlikVer(page)
    await expect(page.getByRole('alert')).toContainText('Giriş yapılamadı')
    await expect(page.getByRole('alert')).toContainText('Google girişi doğrulanamadı. Yeniden dene.')
    await expect(page.getByText(/Invalid token|HTTP|401/)).toHaveCount(0)
    await page.unroute('**/api/auth/login')
    await page.route('**/api/auth/login', r => r.abort('internetdisconnected'))
    await kimlikVer(page)
    await expect(page.getByRole('alert')).toContainText('Bağlantı kurulamadı')
    await expect(page.getByRole('alert')).toHaveCount(1)
  })

  test('an accepted account goes straight to the dashboard', async ({ page }) => {
    await girisAc(page)
    await page.route('**/api/auth/login', r => r.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ email: 'aile@example.com', name: 'Aile', picture: '', role: 'full' }),
    }))
    await kimlikVer(page)
    await expect(baslik(page)).toHaveCount(0)
    await expect(page.locator('.app-shell-content')).toBeVisible()
  })
})

test.describe('accessibility and display modes', () => {
  for (const [boy, w, h] of [['masaüstü', 1440, 900], ['telefon', 390, 844]] as const) {
    test(`axe and IBM Equal Access find nothing, with a notification shown (${boy})`, async ({ page }) => {
      await girisAc(page, w, h)
      await page.route('**/api/auth/login', r => r.fulfill({ status: 403, contentType: 'application/json', body: '{}' }))
      await kimlikVer(page)
      await expect(page.getByRole('alert')).toBeVisible()
      const { violations } = await new AxeBuilder({ page })
        .exclude('.sahte-gsi')   // the stand-in for Google's iframe is not TEDY's markup
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'])
        .analyze()
      expect(violations.map(v => `${v.impact} ${v.id}: ${v.nodes.map(n => n.target.join(' ')).join(' | ')}`)).toEqual([])
      await page.addScriptTag({ path: ACE })
      const ihlal: string[] = await page.evaluate(async () => {
        // @ts-expect-error — `ace` is the injected engine's global
        const rapor = await new window.ace.Checker().check(document, ['IBM_Accessibility'])
        return rapor.results
          .filter((s: { value: string[]; snippet: string }) =>
            s.value[0] === 'VIOLATION' && s.value[1] === 'FAIL' && !s.snippet.includes('sahte-gsi'))
          .map((s: { ruleId: string; message: string }) => `${s.ruleId}: ${s.message}`)
      })
      expect(ihlal).toEqual([])
    })
  }

  test('on a phone every control is at least 44 px', async ({ page }) => {
    await oturumYok(page)
    await gsiEngelli(page)
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/')
    await expect(page.getByRole('button', { name: 'Yeniden dene' })).toBeVisible()
    // The notification spans the form column (Carbon caps it at 18rem below md).
    const bildirim = (await page.locator('.login-page__notification').boundingBox())!
    const sutun = (await page.locator('.login-page__gsi').boundingBox())!
    expect(Math.round(bildirim.width)).toBe(Math.round(sutun.width))
    const kucuk = await page.locator('button, a, [role=button]').evaluateAll(els => els
      .filter(el => (el as HTMLElement).offsetParent !== null)
      .map(el => ({ ad: el.textContent?.trim(), k: el.getBoundingClientRect() }))
      .filter(({ k }) => k.height < 44 || k.width < 44)
      .map(({ ad, k }) => `${ad} ${Math.round(k.width)}×${Math.round(k.height)}`))
    expect(kucuk).toEqual([])
    await page.unroute(GSI_ADRESI)
    await gsiHazir(page)
    await page.getByRole('button', { name: 'Yeniden dene' }).click()
    expect(Math.round((await dugme(page).boundingBox())!.height)).toBeGreaterThanOrEqual(44)
  })

  test('nothing moves under reduced motion, the skeleton included', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.clock.install({ time: new Date('2026-10-15T10:30:00+03:00') })
    await oturumYok(page)
    await gsiBekleyen(page)
    await page.goto('/')
    await page.clock.runFor(450)
    await expect(page.locator('.login-page .cds--skeleton__placeholder')).toBeVisible()
    const hareketli = await page.evaluate(() => {
      const sn = (v: string) => Math.max(...v.split(',').map(x => parseFloat(x) * (x.trim().endsWith('ms') ? 0.001 : 1)))
      return Array.from(document.querySelectorAll('body *, body *::before, body *::after')).flatMap(el => {
        const cs = getComputedStyle(el)
        const out: string[] = []
        if (cs.animationName !== 'none' && sn(cs.animationDuration) > 0.01) out.push(`animation ${cs.animationName}`)
        if (sn(cs.transitionDuration) > 0.01) out.push(`transition ${cs.transitionProperty}`)
        return out.map(o => `${String(el.className).split(' ')[0]}: ${o}`)
      })
    })
    expect([...new Set(hareketli)]).toEqual([])
  })

  test('in Windows high contrast the band keeps an edge and the logo turns dark', async ({ page }) => {
    await page.emulateMedia({ forcedColors: 'active' })
    await girisAc(page)
    const kenar = await page.getByRole('banner').evaluate(el => {
      const cs = getComputedStyle(el)
      return cs.borderInlineEndStyle !== 'none' && parseFloat(cs.borderInlineEndWidth) > 0
    })
    expect(kenar).toBe(true)
    const logo = await page.getByRole('banner').getByRole('img', { name: 'TEDY' })
      .evaluate(el => (el as HTMLImageElement).currentSrc)
    expect(logo).toMatch(/tedy-logo\.svg$/)
  })
})
