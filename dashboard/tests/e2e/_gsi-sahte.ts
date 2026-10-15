import type { Page, Route } from '@playwright/test'

// A deterministic stand-in for Google Identity Services (giriş sayfası yenilemesi, 2026-10-15). The real script
// is never loaded in a test: it renders when and how Google likes, and a test that reaches accounts.google.com
// depends on the network. The stand-in keeps GSI's contract — `initialize({callback})`, then
// `renderButton(el, {width, size: 'large'})` draws a 40 px button `width` px wide — and clicking it hands the
// page a fake credential, as Google's popup would.
export const SAHTE_GSI = `window.google = { accounts: { id: {
  initialize(c) { window.__gsiAyar = c },
  renderButton(el, o) {
    const b = document.createElement('div')
    b.setAttribute('role', 'button')
    b.tabIndex = 0
    b.className = 'sahte-gsi'
    b.textContent = 'Google ile oturum açın'
    b.style.cssText = 'box-sizing:border-box;width:' + (o.width || 320) + 'px;height:40px;border:1px solid #dadce0;' +
      'border-radius:4px;display:flex;align-items:center;justify-content:center;font:500 14px Arial,sans-serif;' +
      'color:#3c4043;background:#fff;cursor:pointer'
    const ver = () => window.__gsiAyar.callback({ credential: 'sahte-kimlik' })
    b.addEventListener('click', ver)
    b.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') ver() })
    el.replaceChildren(b)
  },
} } }`

export const GSI_ADRESI = 'https://accounts.google.com/**'

/** Google's script answers at once. */
export async function gsiHazir(page: Page) {
  await page.unroute(GSI_ADRESI).catch(() => undefined)
  await page.route(GSI_ADRESI, r => r.fulfill({ status: 200, contentType: 'text/javascript', body: SAHTE_GSI }))
}

/** Google's script is blocked (an extension, a network filter): the request fails. */
export async function gsiEngelli(page: Page) {
  await page.route(GSI_ADRESI, r => r.abort('blockedbyclient'))
}

/** Google's script hangs until `birak()` is called. */
export async function gsiBekleyen(page: Page): Promise<() => void> {
  let birak!: () => void
  const serbest = new Promise<void>(r => { birak = r })
  await page.route(GSI_ADRESI, async (r: Route) => {
    await serbest
    await r.fulfill({ status: 200, contentType: 'text/javascript', body: SAHTE_GSI }).catch(() => undefined)
  })
  return birak
}

/** Signed out: the session check answers 401 (the test server would otherwise let everyone in). */
export async function oturumYok(page: Page) {
  await page.route('**/api/auth/me', r => r.fulfill({ status: 401, contentType: 'application/json', body: '{}' }))
}

/** The sign-in page as a stranger sees it, with Google answering at once and the clock fixed. */
export async function girisAc(page: Page, w = 1440, h = 900) {
  await page.clock.setFixedTime(new Date('2026-10-15T10:30:00+03:00'))
  await oturumYok(page)
  await gsiHazir(page)
  await page.setViewportSize({ width: w, height: h })
  await page.goto('/')
  await page.locator('.sahte-gsi').waitFor()
  await page.evaluate(() => document.fonts.ready.then(() => undefined))
}
