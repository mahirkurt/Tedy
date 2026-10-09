import { expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { mock, mockSohbetler } from './_audit-fixtures'
import { GORSEL } from './_gorsel-fixtures'

export const sse = (...c: [string, unknown][]) => c.map(([a, v]) => `event: ${a}\ndata: ${JSON.stringify(v)}\n\n`).join('')
export const PAYLOAD = (p: Record<string, unknown> = {}) => ({ answer: 'Cevap metni.', citations: [], safety_flags: [], plan_blocks: [],
  intent: 'qa', session_id: '', meta: { model: 'claude-sonnet-5', degraded: [] }, ...p })

/** Her soru gönderen test iki ucu da kendisi yanıtlar: yanıtsız akış /chat'e düşer ve oyun sunucusunda
 *  gerçek çalışma zamanına ulaşır (bilinen tuzak). */
export async function cevapla(page: Page, payload: Record<string, unknown>, olaylar: [string, unknown][] = []) {
  const istekler: Record<string, unknown>[] = []
  await page.route('**/api/assistant/stream', async r => {
    istekler.push(r.request().postDataJSON())
    await r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse(...olaylar, ['answer', { payload }], ['done', {}]) })
  })
  await page.route('**/api/assistant/chat', async r => { istekler.push(r.request().postDataJSON()); await r.fulfill({ json: payload }) })
  return istekler
}
export const soruAlani = (page: Page) => page.getByRole('textbox', { name: /^Sorunu(zu)? yaz/ })
export const gonderDugmesi = (page: Page) => page.getByRole('button', { name: 'Gönder', exact: true })
export async function asistanAc(page: Page, yol = '/asistan') {
  await mockSohbetler(page)
  await page.goto(yol)
  await expect(soruAlani(page)).toBeVisible({ timeout: 15000 })
}
export async function sor(page: Page, metin: string) {
  await soruAlani(page).fill(metin)
  await gonderDugmesi(page).click()
}

/** sabitAc'ın Carbon sayfaları için hâli: saati dondurmaz. page.clock.setFixedTime Date.now'u durdurur ve
 *  Carbon'un markdown çizimindeki lodash throttle'ın sondaki çağrısı hiç gelmez — yüklenen geçmiş boş çizilir. */
export async function carbonSabitAc(page: Page, yol: string, w: number, h: number) {
  await mock(page, GORSEL)
  await page.setViewportSize({ width: w, height: h })
  await page.goto(yol)
  await expect(soruAlani(page)).toBeVisible({ timeout: 15000 })
}

/** Son asistan mesajı (Carbon'un mesaj kabı). */
// Carbon her cevapta bir de gizli kopya tutar; yalnız görünürler sayılır.
export const sonCevap = (page: Page) => page.locator('.cds-aichat--assistant-message').filter({ visible: true }).last()
/** Eklenti ve özel çizici çıktıları (kutu, formül, vurgu kutusu): Carbon bunları mesajın gölge kökünde değil,
 *  sohbet öğesinin ışık DOM'unda yuvalı düğümler olarak tutar; mesaj konumlayıcısı onları görmez. Yalnız
 *  görünenler: akışta çizilen eski düğümler yuvasız kalır. */
export const eklentiler = (page: Page) => page.locator('cds-aichat-react > [slot]').filter({ visible: true })
/** Ekran görüntüsünden önce, kaydırma konumuna göre beliren Carbon öğesini ("en alta kaydır" düğmesi) gizler:
 *  kaydırma bitişinin zamanlamasına göre bazen görünüyordu (tam koşularda ara sıra kırmızı). Düğme Carbon'un gölge
 *  kökünde; belgeye eklenen stil (toHaveScreenshot `style`) oraya ulaşmaz. */
export async function kayanlariGizle(page: Page) {
  await page.evaluate(() => {
    const gez = (k: ParentNode) => {
      for (const el of k.querySelectorAll<HTMLElement>('*')) {
        if (el.classList.contains('cds-aichat__scroll-to-bottom-button')) el.style.setProperty('visibility', 'hidden', 'important')
        if (el.shadowRoot) gez(el.shadowRoot)
      }
    }
    gez(document)
  })
}
