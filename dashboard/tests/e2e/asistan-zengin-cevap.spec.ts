import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { createRequire } from 'node:module'
import { json } from './_audit-fixtures'
import { sabitAc } from './_gorsel-yardim'

const ACE = createRequire(import.meta.url).resolve('accessibility-checker-engine/ace.js')
const CEVAP = [
  '$\\frac{3}{4}$ daha büyük. Paydaları eşitleyince iki kesri aynı parçalarla sayarız.',
  '', ':::kavram', 'Payda bütünün kaç eş parçaya bölündüğünü söyler [S1].', ':::',
  '', ':::ornek', 'Örnek: $1/2$ yarımdır.', ':::',
  '', ':::adimlar',
  '1. Ortak payda: 4 ile 3’ün ortak katı **12**.',
  '2. $\\frac{3}{4} = \\frac{9}{12}$ ve $\\frac{2}{3} = \\frac{8}{12}$',
  '   - Eşit parçalar kullanırız.',
  '3. Paylar karşılaştırılır: $9 > 8$.',
  '', 'Bu adımlar eş parçaları karşılaştırır.', ':::',
  '', ':::sonuc', '$\\frac{3}{4} > \\frac{2}{3}$', ':::',
  '', '| Gösterim | 3/4 | 2/3 |', '|---|---|---|',
  '| 12’lik | 9/12 | 8/12 |', '| Ondalık | $0{,}75$ | $0{,}67$ |',
  '', ':::hata', 'Paydalar farklıyken pay tek başına karşılaştırılamaz.', ':::',
  '', ':::bilinmeyen', 'Bu düz paragraf olarak görünür.', ':::',
  '', 'Fiyatı 5 \\$ değil, 5 TL.',
  '', '$$x^2 + y^2 = z^2$$',
  '', '**Şimdi:** $\\frac{5}{6}$ ile $\\frac{7}{9}$’u sen karşılaştır.',
].join('\n')

function cevap(answer: string) {
  return { answer, citations: [{ id: 'S1', kind: 'mufredat', label: 'Kesirler',
    locator: {}, snippet: 'Eş parçalar', confidence: 0.9 }],
  safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
  meta: { model: 'claude-sonnet-5', degraded: [], dropped_citations: 0 } }
}

async function sor(page: Page, answer = CEVAP, mod = 'genel', w = 390, h = 844) {
  await page.addInitScript(id => localStorage.setItem('tedy-asistan-ogretmen::test@tedy.online', id), mod)
  await sabitAc(page, '/asistan', w, h)
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/assistant/chat', r => r.fulfill(json(cevap(answer))))
  await page.fill('#ac-input', 'Kesirleri karşılaştır')
  await page.getByLabel('Gönder', { exact: true }).click()
  const msg = page.locator('.ac-msg--assistant').last()
  await expect(msg).toContainText('Payda')
  return msg
}

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

test('bloklar, adımlar, formüller, atıf ve tablo anlamını korur', async ({ page }) => {
  const msg = await sor(page)
  for (const [ad, etiket] of [['kavram', 'Kavram'], ['ornek', 'Örnek'],
    ['sonuc', 'Sonuç'], ['hata', 'Sık yapılan hata']]) {
    await expect(msg.locator(`.ac-kutu--${ad} .ac-kutu__etiket`)).toHaveText(etiket)
  }
  await expect(msg.locator('.ac-adimlar .ac-adim')).toHaveCount(3)
  await expect(msg.locator('.ac-adim__no').first()).toHaveText('1')
  await expect(msg).toContainText('Bu adımlar eş parçaları karşılaştırır.')
  await expect(msg.locator('.ac-adim').nth(1)).toContainText('Eşit parçalar kullanırız.')
  await expect(msg.locator('.ac-formul .katex').first()).toBeVisible()
  expect(await msg.locator('.ac-formul .katex').count()).toBeGreaterThanOrEqual(8)
  await expect(msg.locator('.ac-kutu--kavram .ac-cite')).toHaveCount(1)
  await expect(msg.getByRole('region', { name: 'Tablo' })).toHaveAttribute('tabindex', '-1')
  await expect(msg.locator('table tr')).toHaveCount(3)
  const bilinmeyen = msg.locator('p').filter({ hasText: 'Bu düz paragraf olarak görünür.' })
  await expect(bilinmeyen).toBeVisible()
  expect(await bilinmeyen.evaluate(p => p.closest('.ac-kutu'))).toBeNull()
  await expect(msg.locator('p').filter({ hasText: 'Fiyatı 5 $ değil' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
})

test('bozuk formül kaynak kodunu gösterir, matematikten URL açılmaz', async ({ page }) => {
  const msg = await sor(page, 'Payda $\\bozukkomut{x}$ ve $\\href{https://ornek.test}{git}$')
  await expect(msg.locator('.ac-formul__kaynak').first()).toContainText('\\bozukkomut')
  await expect(msg.locator('a[href="https://ornek.test"]')).toHaveCount(0)
})

test('formül paketi yüklenemezse kaynak ve cevap korunur', async ({ page }) => {
  await page.route(/\/assets\/katex[^/]*\.js$/, r => r.abort())
  const msg = await sor(page, 'Payda $\\frac{1}{2}$ olarak yazılır.')
  await expect(msg.locator('.ac-formul__kaynak')).toHaveText('\\frac{1}{2}')
  await expect(msg).toContainText('olarak yazılır.')
})

test('taşan formül ve tablo klavyeyle kaydırılır', async ({ page }) => {
  const msg = await sor(page, 'Payda:\n\n$$' + 'x + '.repeat(60) + '1$$\n\n' +
    '| Çok uzun sütun | İkinci sütun |\n|---|---|\n| ' + 'kesir'.repeat(30) + ' | Açıklama |')
  await expect(msg.locator('.katex')).toBeVisible()
  for (const el of [msg.locator('.ac-formul'), msg.getByRole('region', { name: 'Tablo' })]) {
    await expect(el).toHaveAttribute('tabindex', '0')
    await el.focus()
    await page.keyboard.press('ArrowRight')
    await expect.poll(() => el.evaluate(node => node.scrollLeft)).toBeGreaterThan(0)
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
})

for (const mod of ['genel', 'matematik']) {
  for (const [boy, w, h] of [['masaustu', 1440, 900], ['telefon', 390, 844]] as const) {
    test(`${mod} ${boy}: zengin cevap görünümü`, async ({ page }) => {
      await sor(page, CEVAP, mod, w, h)
      await expect(page.locator('.ac-formul .katex').first()).toBeVisible()
      await page.evaluate(() => {
        const pane = document.querySelector<HTMLElement>('.ac__messages')!
        const messages = pane.querySelectorAll<HTMLElement>('.ac-msg--assistant')
        pane.style.scrollBehavior = 'auto'
        pane.scrollTop += messages[messages.length - 1].getBoundingClientRect().top - pane.getBoundingClientRect().top
        window.scrollTo(0, 0)
      })
      await expect(page).toHaveScreenshot(`zengin-cevap-${mod}-${boy}.png`, {
        fullPage: true, animations: 'disabled', caret: 'hide', maxDiffPixelRatio: 0.002,
      })
    })
  }
  test(`${mod}: axe ve IBM erişilebilirlik`, async ({ page }) => {
    await sor(page, CEVAP, mod)
    await expect(page.locator('.ac-formul .katex').first()).toBeVisible()
    const { violations } = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice']).analyze()
    expect(violations.map(v => `${v.id}: ${v.nodes.map(n => n.target).join(', ')}`)).toEqual([])
    await page.addScriptTag({ path: ACE })
    const sonuc = await page.evaluate(async () => {
      // @ts-expect-error — IBM engine is injected above.
      const rapor = await new window.ace.Checker().check(document, ['IBM_Accessibility'])
      return rapor.results as { ruleId: string; value: string[]; snippet: string; path: { dom: string } }[]
    })
    expect(sonuc.filter(s => s.value[0] === 'VIOLATION' && s.value[1] === 'FAIL')
      .filter(s => !(s.ruleId === 'aria_id_unique' && /cds--ai-label|cds--toggletip/.test(s.snippet + s.path.dom)))
      .map(s => `${s.ruleId}: ${s.snippet}`)).toEqual([])
  })
}

test('açık adım bloğu akışta dolar, son cevap tek kalır', async ({ page }) => {
  await sabitAc(page, '/asistan', 390, 844)
  await page.route('**/api/assistant/stream', r => r.abort())
  await page.route('**/api/assistant/chat', r => r.fulfill(json(cevap(CEVAP))))
  await page.evaluate(payload => {
    const gercek = window.fetch.bind(window)
    window.fetch = (input, init) => {
      if (!String(input).includes('/api/assistant/stream')) return gercek(input, init)
      const encoder = new TextEncoder()
      const body = new ReadableStream({ start(controller) {
        controller.enqueue(encoder.encode('event: answer_delta\ndata: ' +
          JSON.stringify({ text: ':::adimlar\n1. Payda eşitlenir.' }) + '\n\n'))
        window.addEventListener('test-akisi-bitir', () => {
          controller.enqueue(encoder.encode('event: answer\ndata: ' + JSON.stringify({ payload }) + '\n\n'))
          controller.close()
        }, { once: true })
      } })
      return Promise.resolve(new Response(body, { headers: { 'Content-Type': 'text/event-stream' } }))
    }
  }, cevap(CEVAP))
  await page.fill('#ac-input', 'Kesirleri karşılaştır')
  await page.getByLabel('Gönder', { exact: true }).click()
  await expect(page.locator('.ac-msg--writing .ac-adimlar')).toBeVisible()
  await page.evaluate(() => window.dispatchEvent(new Event('test-akisi-bitir')))
  await expect(page.locator('.ac-msg--writing')).toHaveCount(0)
  await expect(page.locator('.ac-msg--assistant .ac-adimlar')).toHaveCount(1)
})
