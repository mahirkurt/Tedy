# TEDY Asistanı — Carbon AI Chat'e tam geçiş: uygulama planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Asistanın arayüzünü (`/asistan` ve her sayfadaki başlatıcı) `@carbon/ai-chat` 1.22.0 üzerine, bugünkü her özelliği ve testi koruyarak taşımak; araç adımları, geri bildirim, yeni sohbet/yeniden başlat, tam ekran ve sayfa bağlamı eklemek.

**Architecture:** Carbon AI Chat'in React bileşenleri (`ChatCustomElement` sayfada, `ChatContainer` başlatıcıda) kabuk olur. `dashboard/src/asistan/` altındaki ince bir uyarlayıcı katman bizim SSE olaylarımızı Carbon mesaj parçalarına çevirir (`olayEslemesi.ts`, saf), TEDY kartlarını `user_defined` yanıt olarak çizer, `:::` bloklarını ve KaTeX'i markdown-it eklentileriyle verir. Arka uçta yalnız üç ek var: `tool_end.ozet`, `sayfa` istek alanı, geri bildirim tablosu ve uçları. Eski `AssistantChat` derleme zamanı bayrağı `VITE_ASISTAN_CARBON_AI` kapalıyken çalışmaya devam eder; bayrak son görevde tek commit'le açılır.

**Tech Stack:** React 19 + Vite 7 + TypeScript 5.9, `@carbon/ai-chat` 1.22.0 (+ `@carbon/web-components` 2.x, lit), markdown-it eklentileri, KaTeX; Flask + SQLite (WAL); Playwright 1.58 + axe + IBM Equal Access; `node --test` (TS tip silme) birim testleri; pytest.

**Spec:** `docs/superpowers/specs/2026-10-08-asistan-carbon-ai-chat-design.md`

## Global Constraints

- `@carbon/ai-chat` tam sürüm `1.22.0` (caret yok); `@carbon/web-components` `^2.58.1`; React `^19.2`.
- Her `npm install` / `npm ci` / `npx` kurulumu `IBM_TELEMETRY_DISABLED=true` ile koşar; derlenmiş pakette `www-api.ibm.com/ibm-telemetry` geçmez.
- Görünen her metin Türkçedir; öğrenciye "sen", aileye "siz" (bugünkü `VOICE`, skill `karsilama`/`hizli_sorular` okura göre).
- Görünüm Carbon AI Chat'in kendisidir; TEDY'den yalnız: öğretmen modunun ders rengi (kontrast ≥ 4.5:1, marka bandı değişmez), erişilebilirlik alt sınırı (axe + IBM Equal Access ihlalsiz), `prefers-reduced-motion` altında hareket yok, `forced-colors` altında kenar var, odak modu, Türkçe metin.
- Cevap üretimi (model, araçlar, B6 denetimi, sistem istemi, SSE olay adları) değişmez; yalnız spec §5'teki ekler.
- Bayrak: `import.meta.env.VITE_ASISTAN_CARBON_AI === '1'` yeni arayüzü açar. Görev 20'ye kadar `dashboard/.env.production` bayrağı **içermez**; yeni arayüzü sınayan e2e koşuları `npm run build:carbon-ai` ile derlenmiş pakete karşı yapılır.
- Başlatıcı: yalnız `full` rol, ≥ 672 px; `/asistan`, `/moduller/:slug/:version`, `/moduller/taslak/:taslakId`, `/kitaplar/:slug/:chapterId`, giriş sayfası, reader ve odak modunda yok. Başlatıcı düğmesi ilk yüklemeye yalnız kendi küçük bileşenini getirir; Carbon AI Chat (ve lit, web components, tiptap, CodeMirror) ilk tıklamada yüklenir — Görev 2 ve 18'deki testler bunu sabitler.
- Telefon (< 672 px): yüzen düğme yok; alt gezinmedeki Asistan sekmesi `/asistan?sayfa=<ad>` taşır.
- `tool_end.ozet` ≤ 120 karakter, ham argüman/çıktı yok. Geri bildirim `metin` ≤ 500 karakter; olumsuz kategoriler tam olarak: "Yanlış bilgi", "Anlamadım", "Seviyeme uygun değil", "Kaynak göstermedi", "Diğer". Öğrencinin geri bildirim kutusunda "Ailen bunu görebilir." yazar.
- `sayfa.ad` ∈ {`bugun`, `isler`, `dersler`, `notlar`, `takvim`, `takimlar`, `ilerleme`, `duyurular`, `profil`, `moduller`, `kitaplar`, `sinavlar`}; `sayfa.oge.tur` ∈ {`odev`, `sinav`, `etkinlik`, `ders_haftasi`}; geçersiz → 400 "Bilinmeyen sayfa.".
- Yeni boyutlar `rem`; ikonlar mevcut `:where(svg[width][height])` kuralına uyan `size`.
- Python testleri: `unshare -rn .venv/bin/python -m pytest -q …` (ağsız). e2e: `cd dashboard && env -u ANTHROPIC_API_KEY npx playwright test …`; soru gönderen her e2e testi `/api/assistant/stream` **ve** `/api/assistant/chat`'i kendisi yanıtlar.
- TS birim testleri: `cd dashboard && node --test tests/<ad>.test.ts` (Node 26 tip silme). Bu testlerin içe aktardığı modüller yalnız `import type` kullanır (çalışma zamanında `@carbon/ai-chat` yüklenmez).
- Çalışma yeri: worktree `/mnt/thunderbolt/workspaces/TED/.claude/worktrees/carbon-ai`, dal `feat/carbon-ai-chat`. Ana checkout'a dokunulmaz; push ve `main`'e birleştirme yalnız kullanıcının sözüyle (Görev 20).
- Arka plan kabuk işi yok: her test ve derleme ön planda koşar (alt ajanlar arka plan işinde takılıyor).

## Review Focus

1. **Bilinmeyen sayfa adıyla açılan telefon sekmesi** (`/asistan?sayfa=xyz`): çip görünmez, istekte `sayfa` gitmez, 400 almaz — Görev 18'de test.
2. **Oturum ortada düşer (401/403)**: okur ham "HTTP 401" görmez; "Oturumun sona ermiş; sayfayı yenileyip yeniden giriş yap." cümlesi ve Tekrar dene — Görev 9 ve 11'de test.
3. **Atıf işareti blok, tablo hücresi, liste ve metin başında**: `ranges` metin dışına taşmaz, işaret metinde kalmaz — Görev 7'de test.
4. **Tekrar gönderimde dönen (yeniden oynatılan) cevaba geri bildirim**: `tekrar` yükü de `mesaj_id` taşır, geri bildirim 404 olmaz — Görev 6'da test.
5. **Başlatıcıda yazılan soru sayfada bir kez görünür**: başlatıcıdan gönderip `/asistan`'a geçince mesaj çift olmaz — Görev 18'de test.

---

## Dosya yapısı

| Dosya | Sorumluluk | Görev |
|---|---|---|
| `dashboard/deneme/*` | Atılacak risk denemesi (Görev 1 sonunda silinir) | 1 |
| `docs/superpowers/notes/2026-10-08-carbon-ai-deneme.md` | Deneme raporu (kalır) | 1 |
| `dashboard/vite.config.ts` | `@carbon/ai-chat*`, `@carbon/web-components`, `lit` ayrı tembel parçada | 2 |
| `dashboard/src/asistan/bayrak.ts` | `CARBON_AI_ACIK` | 2 |
| `dashboard/tests/paket-telemetri.test.ts` | Derlenmiş pakette telemetri ucu yok | 2 |
| `src/assistant_tools.py` (`arac_ozeti`) | `tool_end.ozet` | 3 |
| `src/assistant_core.py` (`announcing`, `_build_conversation`, `chat`) | `ozet` yayını; `sayfa_satiri` | 3, 4 |
| `src/dashboard_api.py` (`_istek_sayfasi`, geri bildirim uçları, `mesaj_id`) | §5.2–5.3 | 4, 6 |
| `src/assistant_sohbet.py` (`geri_bildirim` tablosu ve yöntemleri) | §5.2 depo | 5 |
| `dashboard/src/asistan/olayEslemesi.ts` | SSE olayı → Carbon parçaları (saf) | 7 |
| `dashboard/src/asistan/atiflar.ts` | `[S1]` → `ranges` (saf) | 7 |
| `dashboard/src/asistan/markdownEklentileri.ts` | `:::` blokları, KaTeX (markdown-it) | 8 |
| `dashboard/src/asistan/kaydirmaOdagi.ts` | Taşan formül/tablo bölgesine odak | 8 |
| `dashboard/src/asistan/akisIstemcisi.ts` | `/stream`, `/chat` yedeği, `/plan`, iptal | 9 |
| `dashboard/src/asistan/dilPaketi.ts` | Carbon'un 263 metni Türkçe (Ek A) | 10 |
| `dashboard/src/asistan/tedyChatConfig.ts` | `PublicConfig` üretimi | 10 |
| `dashboard/src/asistan/AsistanSohbeti.tsx` | Sayfa ve başlatıcının ortak gövdesi (config + render işlevleri) | 11 |
| `dashboard/src/asistan/AsistanSayfasi.tsx` | `/asistan` (`ChatCustomElement`) | 11 |
| `dashboard/src/asistan/OzelYanitlar.tsx` | `user_defined` kartlar | 12 |
| `dashboard/src/asistan/KaynakPaneli.tsx` | Workspace'te `SourcePanel` | 13 |
| `dashboard/src/asistan/MesajAltbilgisi.tsx` | Altbilgi düğmeleri ve rozetler | 14 |
| `dashboard/src/asistan/geriBildirim.ts` | `BusEventFeedback` → `PUT` | 14 |
| `dashboard/src/asistan/useAsistanOturumu.ts` | Ortak etkin sohbet (sayfa ↔ başlatıcı) | 15 |
| `dashboard/src/asistan/GecmisPaneli.tsx` | Geçmiş paneli yuvası + notlar | 15 |
| `dashboard/src/asistan/GirisEkleri.tsx` | Ek çipleri, ödev seçici, mikrofon, plan | 16 |
| `dashboard/src/asistan/ogretmenRenkleri.ts` | Ders rengi → Carbon AI Chat CSS özel özellikleri | 17 |
| `dashboard/src/asistan/sayfaBaglami.ts`, `AsistanBaglami.tsx`, `sayfaSorulari.ts`, `AsistanBaslatici.tsx` | Başlatıcı, çip, sayfa soruları | 18 |
| `dashboard/tests/e2e/_asistan-carbon.ts` | Shadow DOM'a dayanıklı ortak test yardımcıları | 11 |

Mevcut bileşenler (`AlistirmaKarti`, `OdevOnayKarti`, `NetlestirmeSecenekleri`, `ModOnerisi`, `OgretmenSecici`, `SourcePanel`, `SohbetListesi`, `YuklenenEk`, `YuklemeAlani`, `CitationChip`) **değiştirilmeden** yeniden kullanılır; yalnız gerekli prop eklemeleri ilgili görevde yazılıdır.

---

### Task 1: Risk denemesi (atılacak kod + rapor + karar kapısı)

Spec §6 "İlk görev". Altı nokta gerçek bileşenle ölçülür. Bu görevin kodu **atılır**; kalıcı olan yalnız `package.json` bağımlılıkları ve rapordur. Bir nokta tutmazsa raporda yedek yol işaretlenir ve **Görev 2'ye geçmeden kullanıcıya sorulur** (özellikle 5. nokta).

**Files:**
- Modify: `dashboard/package.json`, `dashboard/package-lock.json`
- Create (atılacak): `dashboard/deneme/carbon-ai.html`, `dashboard/deneme/carbon-ai.tsx`, `dashboard/deneme/playwright.deneme.config.ts`, `dashboard/deneme/olcum.spec.ts`
- Create (kalır): `docs/superpowers/notes/2026-10-08-carbon-ai-deneme.md`

**Interfaces:**
- Consumes: —
- Produces: `@carbon/ai-chat@1.22.0` ve `@carbon/web-components` bağımlılıkları; rapordaki altı kararın her biri "TUTTU" ya da "YEDEK: <yol>".

- [ ] **Step 1: Paketleri telemetri kapalı kur**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/carbon-ai/dashboard
IBM_TELEMETRY_DISABLED=true npm install --save-exact @carbon/ai-chat@1.22.0
IBM_TELEMETRY_DISABLED=true npm install '@carbon/web-components@^2.58.1'
grep -E '"@carbon/(ai-chat|web-components)"' package.json
```
Expected: `"@carbon/ai-chat": "1.22.0"` ve `"@carbon/web-components": "^2.58.1"` satırları.

- [ ] **Step 2: Deneme sayfasını yaz**

`dashboard/deneme/carbon-ai.html`:
```html
<!doctype html>
<html lang="tr">
  <head><meta charset="UTF-8" /><title>Carbon AI deneme</title></head>
  <body><div id="kok" style="height:100vh"></div><script type="module" src="./carbon-ai.tsx"></script></body>
</html>
```

`dashboard/deneme/carbon-ai.tsx` (atılacak; yalnız ölçüm için):
```tsx
import { createRoot } from 'react-dom/client'
import { ChatCustomElement } from '@carbon/ai-chat'
import type { ChatInstance, MessageRequest, CustomSendMessageOptions, PublicConfig } from '@carbon/ai-chat'
import type MarkdownIt from 'markdown-it'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import '../src/theme/ted-theme.scss'

const KUTU = /^:::\s*(kavram|ornek)\s*$/
function kutuEklentisi(md: MarkdownIt) {
  md.block.ruler.before('fence', 'tedy_kutu', (state, start, end, silent) => {
    const satir = state.src.slice(state.bMarks[start] + state.tShift[start], state.eMarks[start])
    const m = KUTU.exec(satir.trim())
    if (!m) return false
    if (silent) return true
    let son = start + 1
    while (son < end && state.src.slice(state.bMarks[son], state.eMarks[son]).trim() !== ':::') son++
    const ic = state.getLines(start + 1, son, 0, false)
    const t = state.push('tedy_kutu', 'div', 0)
    t.content = ic; t.info = m[1]; t.block = true
    state.line = Math.min(son + 1, end)
    return true
  })
  md.renderer.rules.tedy_kutu = (tokens, i) =>
    `<div class="ac-kutu ac-kutu--${tokens[i].info}"><span class="ac-kutu__etiket">Kavram</span>${md.render(tokens[i].content)}</div>`
  md.inline.ruler.before('escape', 'tedy_formul', (state, silent) => {
    if (state.src[state.pos] !== '$') return false
    const kapanis = state.src.indexOf('$', state.pos + 1)
    if (kapanis < 0) return false
    if (!silent) { const t = state.push('tedy_formul', 'span', 0); t.content = state.src.slice(state.pos + 1, kapanis) }
    state.pos = kapanis + 1
    return true
  })
  md.renderer.rules.tedy_formul = (tokens, i) => katex.renderToString(tokens[i].content, { throwOnError: false })
}

const yanitId = () => crypto.randomUUID()
async function gonder(istek: MessageRequest, _s: CustomSendMessageOptions, inst: ChatInstance) {
  const metin = (istek.input as { text?: string }).text ?? ''
  const rid = yanitId()
  const m = inst.messaging
  const bekle = (ms: number) => new Promise(r => setTimeout(r, ms))
  if (metin === 'akis') {
    await m.addMessageChunk({ partial_item: { response_type: 'text' as never, text: '', streaming_metadata: { id: 'm0' } },
      partial_response: { message_options: { chain_of_thought: [{ title: 'Müfredat aranıyor', status: 'processing' as never }] } },
      streaming_metadata: { response_id: rid } })
    await bekle(300)
    await m.addMessageChunk({ partial_item: { response_type: 'text' as never, text: 'Önce müfredata bakayım.', streaming_metadata: { id: 'm0' } }, streaming_metadata: { response_id: rid } })
    await bekle(300)
    await m.addMessageChunk({ complete_item: { response_type: 'text' as never, text: '', streaming_metadata: { id: 'm0' } }, streaming_metadata: { response_id: rid } })
    await m.addMessageChunk({ partial_item: { response_type: 'text' as never, text: 'TASLAK METİN', streaming_metadata: { id: 'm1' } }, streaming_metadata: { response_id: rid } })
    await bekle(300)
    await m.addMessageChunk({ final_response: { id: rid, output: { generic: [
      { response_type: 'conversational_search' as never, text: 'Kesir bir bütünün parçasıdır. Payda eşit parça sayısıdır.',
        citations: [{ title: 'Matematik 7 · s.57', text: 'Kesirler…', ranges: [{ start: 0, end: 32 }] }],
        message_item_options: { feedback: { is_on: true, id: 'mesaj-1', categories: ['Yanlış bilgi', 'Anlamadım'] } } } as never,
      { response_type: 'user_defined' as never, user_defined: { tedy: { tur: 'deneme' } } } as never,
    ] }, message_options: { chain_of_thought: [{ title: 'Müfredat aranıyor', description: 'Matematik 7 · s.57', status: 'success' as never }] } } })
    return
  }
  if (metin === 'blok') {
    await m.addMessage({ id: rid, output: { generic: [{ response_type: 'text' as never,
      text: ':::kavram\nPay **üstteki** sayıdır ve $\\frac{3}{4}$ gibi yazılır.\n:::\n\n| a | b | c | d |\n|---|---|---|---|\n| 1 | 2 | 3 | 4 |' } as never] } })
  }
}

const config: PublicConfig = {
  locale: 'tr', aiEnabled: true, header: { title: 'TEDY Asistan', showAiLabel: true, showRestartButton: true },
  history: { isOn: true }, messaging: { customSendMessage: gonder },
  strings: { input_placeholder: 'Bir soru sor...', input_buttonLabel: 'Gönder' },
  homescreen: { isOn: true, greeting: 'Merhaba!', starters: { isOn: true, buttons: [{ label: 'akis' }, { label: 'blok' }] } },
}

createRoot(document.getElementById('kok')!).render(
  <div className="ted-subject ted-subject--blue" style={{ height: '100%' }}>
    <ChatCustomElement className="deneme-sohbet" {...config}
      markdown={{ markdownItPlugins: [kutuEklentisi] }}
      renderUserDefinedResponse={() => <p className="deneme-kart">TEDY kartı</p>}
      renderCustomMessageFooter={() => <button type="button">Sesli oku</button>}
      renderWriteableElements={{ historyPanelElement: <p>Sohbetler</p> }} />
  </div>)
```
(`markdown-it` türleri için `npm i -D @types/markdown-it` yalnız denemede gerekirse `--no-save` ile kurulur.)

- [ ] **Step 3: Ölçüm yapılandırması ve ölçüm testleri**

`dashboard/deneme/playwright.deneme.config.ts`:
```ts
import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: '.', testMatch: /olcum\.spec\.ts/, timeout: 60000,
  use: { baseURL: 'http://127.0.0.1:3107' },
  webServer: { command: 'IBM_TELEMETRY_DISABLED=true npx vite --port 3107 --strictPort', port: 3107, reuseExistingServer: false, timeout: 60000 },
})
```

`dashboard/deneme/olcum.spec.ts`:
```ts
import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { readFileSync } from 'node:fs'

const ac = async (page: import('@playwright/test').Page) => {
  await page.goto('/deneme/carbon-ai.html')
  await expect(page.getByRole('textbox')).toBeVisible({ timeout: 30000 })
}

test('1 akış: reset ve final_response', async ({ page }) => {
  await ac(page)
  await page.getByRole('button', { name: 'akis' }).click()
  await expect(page.getByText('Önce müfredata bakayım.')).toBeVisible()
  await expect(page.getByText('Önce müfredata bakayım.')).toHaveCount(0, { timeout: 2000 })
  await expect(page.getByText('TASLAK METİN')).toBeVisible()
  await expect(page.getByText('Kesir bir bütünün parçasıdır.')).toBeVisible()
  await expect(page.getByText('TASLAK METİN')).toHaveCount(0)
  await expect(page.getByText('TEDY kartı')).toBeVisible()
  await expect(page.getByText('Müfredat aranıyor')).toBeVisible()
  await expect(page.getByRole('button', { name: /like|beğen/i }).first()).toBeVisible()
  await page.screenshot({ path: 'deneme/1-akis.png', fullPage: true })
})

test('2 blok ve KaTeX', async ({ page }) => {
  await ac(page)
  await page.getByRole('button', { name: 'blok' }).click()
  await expect(page.locator('.ac-kutu--kavram')).toBeVisible()
  await expect(page.locator('.ac-kutu--kavram .katex')).toHaveCount(1)
  await expect(page.locator('.ac-kutu--kavram strong')).toHaveText('üstteki')
  const kayma = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
  expect(kayma).toBe(false)
  await page.screenshot({ path: 'deneme/2-blok.png', fullPage: true })
})

test('3 ders rengi CSS değişkeni içeri geçiyor', async ({ page }) => {
  await ac(page)
  const renk = await page.evaluate(() => {
    const kok = document.querySelector('.deneme-sohbet') as HTMLElement
    kok.style.setProperty('--cds-button-primary', 'rgb(1, 2, 3)')
    const ara = (r: Document | ShadowRoot): HTMLElement | null => {
      for (const el of Array.from(r.querySelectorAll('*'))) {
        if ((el as HTMLElement).getAttribute?.('aria-label') === 'Gönder') return el as HTMLElement
        const s = (el as HTMLElement).shadowRoot
        if (s) { const b = ara(s); if (b) return b }
      }
      return null
    }
    const d = ara(document)
    return d ? getComputedStyle(d).backgroundColor : 'bulunamadı'
  })
  console.log('gönder düğmesi rengi:', renk)
})

test('4 Türkçe: görünür İngilizce metin', async ({ page }) => {
  await ac(page)
  const metin = await page.evaluate(() => {
    const parcalar: string[] = []
    const gez = (r: Node) => {
      r.childNodes.forEach(n => {
        if (n.nodeType === 3 && n.textContent?.trim()) parcalar.push(n.textContent.trim())
        if (n instanceof HTMLElement) {
          for (const a of ['aria-label', 'title', 'placeholder']) { const v = n.getAttribute(a); if (v) parcalar.push(v) }
          if (n.shadowRoot) gez(n.shadowRoot)
        }
        gez(n)
      })
    }
    gez(document.body)
    return parcalar
  })
  console.log(JSON.stringify(metin, null, 1))
})

test('5 erişilebilirlik shadow DOM içini görüyor mu', async ({ page }) => {
  await ac(page)
  await page.getByRole('button', { name: 'blok' }).click()
  const axe = await new AxeBuilder({ page }).analyze()
  console.log('axe ihlal:', axe.violations.map(v => v.id), 'geçen kural sayısı:', axe.passes.length)
  const ace = readFileSync('node_modules/accessibility-checker-engine/ace.js', 'utf8')
  await page.addScriptTag({ content: ace })
  const sonuc = await page.evaluate(async () => {
    const w = window as unknown as { ace: { Checker: new () => { check: (d: Document, r: string[]) => Promise<{ results: { value: string[]; path: { dom: string } }[] }> } } }
    const r = await new w.ace.Checker().check(document, ['IBM_Accessibility'])
    return r.results.filter(x => x.value[1] === 'FAIL').map(x => x.path.dom)
  })
  console.log('IBM FAIL:', sonuc)
  const golgeIci = sonuc.filter(p => p.includes('#document-fragment')).length
  console.log('shadow içi bulgu yolu sayısı:', golgeIci)
})
```

- [ ] **Step 4: Ölç, ekran görüntülerini oku**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/carbon-ai/dashboard
IBM_TELEMETRY_DISABLED=true npx playwright test -c deneme/playwright.deneme.config.ts --reporter=list 2>&1 | tee /tmp/carbon-ai-deneme.log
```
Expected: 1 ve 2 PASS. 3–5 çıktıyı konsola yazar. `deneme/1-akis.png` ve `deneme/2-blok.png` Read ile açılıp gözle bakılır.

- [ ] **Step 5: Paket boyutunu ölç (6. nokta)**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/carbon-ai/dashboard
IBM_TELEMETRY_DISABLED=true npx vite build --outDir /tmp/deneme-dist --emptyOutDir deneme/carbon-ai.html 2>&1 | tail -15
du -sh /tmp/deneme-dist/assets; ls -S /tmp/deneme-dist/assets | head -5
grep -l "ibm-telemetry" /tmp/deneme-dist/assets/*.js || echo "telemetri ucu yok"
```

- [ ] **Step 6: Raporu yaz**

`docs/superpowers/notes/2026-10-08-carbon-ai-deneme.md` — her nokta için ölçülen değer ve karar. Şablon (değerler ölçümden doldurulur, tahmin yazılmaz):

```markdown
# Carbon AI Chat risk denemesi — 2026-10-08

| # | Nokta | Ölçülen | Karar |
|---|---|---|---|
| 1 | answer_reset → boş complete_item; final_response yerine geçme; chain_of_thought akışta güncelleniyor mu; user_defined; feedback düğmesi | … | TUTTU / YEDEK |
| 2 | ::: blok + KaTeX eklenti çıktısı light DOM'da, stil alıyor; tablo yan kaydırma yapmıyor | … | TUTTU / YEDEK |
| 3 | `--cds-button-primary` kökten gönder düğmesine geçiyor mu (rgb(1, 2, 3)) | … | TUTTU / YEDEK |
| 4 | Türkçe strings sonrası kalan İngilizce metinler (listesi) | … | … |
| 5 | axe/IBM shadow DOM içini görüyor mu (shadow içi bulgu yolu sayısı, geçen kural sayısı) | … | TUTTU / KULLANICIYA SOR |
| 6 | Paket boyutu (en büyük 5 parça), telemetri ucu | … | … |

## Yedek yollar
- 1 tutmazsa: `answer_reset`te `removeMessages([yanitId])` ve aynı kimlikle yeni mesaj; final'de `upsertMessage`.
- 2 tutmazsa: cevap gövdesi `user_defined` olur, bugünkü `renderMarkdown(…, {bicim:'sohbet'})` çizer (spec §"Yaklaşım C").
- 3 tutmazsa: `layout.customProperties` ile aynı değişkenler verilir.
- 5 tutmazsa: kullanıcıya sorulur; sormadan geçilmez.
```

- [ ] **Step 7: Deneme kodunu sil, raporu ve bağımlılıkları commit'le**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/carbon-ai
rm -rf dashboard/deneme
git add dashboard/package.json dashboard/package-lock.json docs/superpowers/notes/2026-10-08-carbon-ai-deneme.md
git commit -m "chore: Carbon AI Chat bağımlılıkları ve risk denemesi raporu

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 8: Karar kapısı** — Rapordaki her satır TUTTU ise Görev 2'ye geç. Bir satır YEDEK ise rapordaki yedek yolu sonraki görevlerde uygula ve kullanıcıya bir paragrafla bildir. 5. satır tutmazsa **dur ve kullanıcıya sor**.

---

### Task 2: Paket altyapısı — tembel parça, bayrak, telemetri

**Files:**
- Modify: `dashboard/vite.config.ts` (`manualChunks`)
- Modify: `dashboard/package.json` (`scripts`)
- Create: `dashboard/src/asistan/bayrak.ts`
- Create: `dashboard/tests/paket-telemetri.test.ts`
- Create: `~/.config/environment.d/ibm-telemetri.conf`; Modify: `~/.profile` (bir satır)
- Modify: `CLAUDE.md` (Commands bölümü)

**Interfaces:**
- Produces: `CARBON_AI_ACIK: boolean` (`dashboard/src/asistan/bayrak.ts`); npm betikleri `build:carbon-ai`, `test:birim`.

- [ ] **Step 1: Başarısız telemetri testini yaz**

`dashboard/tests/paket-telemetri.test.ts`:
```ts
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'

const DIST = new URL('../../dashboard-dist/assets/', import.meta.url)

test('derlenmiş pakette IBM telemetri ucu yok', () => {
  // Bilerek atlamaz: paket yoksa test başarısızdır (bayat/eksik paket yanlış-geçiş tuzağı).
  assert.ok(existsSync(DIST), 'dashboard-dist yok: önce `npm run build:carbon-ai`')
  const js = readdirSync(DIST).filter(f => f.endsWith('.js'))
  assert.ok(js.some(f => readFileSync(new URL(f, DIST), 'utf8').includes('cds-aichat')),
    'pakette Carbon AI Chat yok: bayrak kapalı derlenmiş olabilir')
  for (const f of js) {
    assert.ok(!readFileSync(new URL(f, DIST), 'utf8').includes('ibm-telemetry/v1/metrics'), `${f} telemetri ucu içeriyor`)
  }
})

test('Carbon AI Chat ilk yüklenen parçalarda değil', () => {
  const html = readFileSync(new URL('../../dashboard-dist/index.html', import.meta.url), 'utf8')
  const ilk = [...html.matchAll(/(?:src|href)="\/assets\/([^"]+\.js)"/g)].map(m => m[1])
  for (const f of ilk) {
    const govde = readFileSync(new URL(f, DIST), 'utf8')
    assert.ok(!govde.includes('cds-aichat-container'), `${f} ilk yüklemede Carbon AI Chat taşıyor (${statSync(new URL(f, DIST)).size} bayt)`)
  }
})
```

- [ ] **Step 2: Bayrak modülü ve betikler**

`dashboard/src/asistan/bayrak.ts`:
```ts
/** Yeni (Carbon AI Chat) asistan arayüzü. Derleme zamanında sabitlenir: Görev 20'ye kadar canlı
 *  derlemede kapalı, `npm run build:carbon-ai` ve geliştirme sunucusunda açık. */
export const CARBON_AI_ACIK = import.meta.env.VITE_ASISTAN_CARBON_AI === '1'
```

`dashboard/.env.development` (yeni dosya):
```
VITE_ASISTAN_CARBON_AI=1
```

`dashboard/package.json` `scripts` içine:
```json
"build:carbon-ai": "VITE_ASISTAN_CARBON_AI=1 npm run build",
"test:birim": "node --test tests/*.test.ts"
```

- [ ] **Step 3: Carbon AI Chat'i `carbon` parçasından ayır**

`dashboard/vite.config.ts` içindeki `manualChunks`:
```ts
        manualChunks(id: string) {
          if (!id.includes('node_modules')) return
          // Carbon AI Chat ve bağımlılıkları (web components, lit, markdown-it, tiptap, CodeMirror)
          // yalnız asistan açıldığında yüklenir: tembel import'un kendi parçasında kalırlar.
          if (/[\\/]node_modules[\\/](@carbon[\\/](ai-chat|ai-chat-components|web-components)|lit|@lit|lit-html|lit-element|@tiptap|prosemirror-[^\\/]+|@codemirror|@lezer|markdown-it|dompurify)[\\/]/.test(id)) return
          if (id.includes('@carbon')) return 'carbon'
          if (id.includes('react-router')) return 'router'
          if (/[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/.test(id)) return 'react'
        }
```

- [ ] **Step 4: Derle, testi koş** (bu görevde henüz Carbon AI Chat içe aktaran kalıcı kod yok; 1. test "Carbon AI Chat yok" diye başarısız olur — beklenen. Görev 11'den sonra yeşile döner.)

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/carbon-ai/dashboard
IBM_TELEMETRY_DISABLED=true npm run build:carbon-ai 2>&1 | tail -5
node --test tests/paket-telemetri.test.ts
```
Expected: `derlenmiş pakette IBM telemetri ucu yok` FAIL ("pakette Carbon AI Chat yok"), ikinci test PASS. Görev 11 Step 7'de ikisi de PASS olmalı.

- [ ] **Step 5: Makinede telemetriyi kalıcı kapat**

```bash
mkdir -p ~/.config/environment.d
printf 'IBM_TELEMETRY_DISABLED=true\n' > ~/.config/environment.d/ibm-telemetri.conf
grep -q IBM_TELEMETRY_DISABLED ~/.profile || printf '\n# Carbon (@carbon/ai-chat) kurulum telemetrisi kapalı — TEDY\nexport IBM_TELEMETRY_DISABLED=true\n' >> ~/.profile
```

`CLAUDE.md` Commands bloğunda `# Dashboard` altına:
```bash
cd dashboard && IBM_TELEMETRY_DISABLED=true npm ci   # Carbon AI Chat kurulumu telemetrisiz; makinede ~/.config/environment.d/ibm-telemetri.conf da ayarlı
cd dashboard && npm run build:carbon-ai              # yeni asistan arayüzüyle derle (VITE_ASISTAN_CARBON_AI=1); Görev 20'den sonra varsayılan
cd dashboard && npm run test:birim                    # node:test birim testleri (tests/*.test.ts)
```

- [ ] **Step 6: Commit**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/carbon-ai
git add dashboard/vite.config.ts dashboard/package.json dashboard/.env.development dashboard/src/asistan/bayrak.ts dashboard/tests/paket-telemetri.test.ts CLAUDE.md
git commit -m "build: Carbon AI Chat ayrı tembel parçada, bayrak ve telemetri denetimi

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 3: Arka uç — araç adımı özeti (`tool_end.ozet`)

Spec §5.1.

**Files:**
- Modify: `src/assistant_tools.py` (yeni `arac_ozeti`, `ToolOutcome` sınıfının hemen altına)
- Modify: `src/assistant_core.py:3041-3047` (`announcing`)
- Test: `tests/test_assistant_arac_ozeti.py`

**Interfaces:**
- Produces: `arac_ozeti(ad: str, sonuc: ToolOutcome) -> str`; SSE `tool_end` olayı `{"name", "ok", "ozet"}` (`ozet` ≤ 120 karakter, her zaman dolu).

- [ ] **Step 1: Başarısız testleri yaz**

`tests/test_assistant_arac_ozeti.py`:
```python
"""tool_end'in okura gösterilen özeti (Carbon AI Chat araç adımı, spec §5.1)."""
from src.assistant_core import AssistantRuntime, ToolLoopResult
from src.assistant_tools import ToolOutcome, arac_ozeti


def _atif(label):
    return {"id": "S1", "kind": "mufredat", "label": label, "locator": {}, "snippet": "gövde metni", "confidence": 1.0}


def test_basarisiz_arac_tek_cumle():
    assert arac_ozeti("kitap_sayfa", ToolOutcome(ok=False, error="HTTP 500 upstream")) == "Bu kaynağa şu an ulaşılamadı"


def test_ogretmen_notlari_atifsiz_ama_adli():
    assert arac_ozeti("skill_kaynagi", ToolOutcome(ok=True, text="## Kavram yanılgıları…")) == "Öğretmen notlarına bakıldı"


def test_tek_iki_cok_atif_ve_tekrar():
    assert arac_ozeti("kitap_sayfa", ToolOutcome(ok=True, citations=[_atif("Matematik 7 (2. Kitap) · s.57")])) \
        == "Matematik 7 (2. Kitap) · s.57"
    assert arac_ozeti("x", ToolOutcome(ok=True, citations=[_atif("A"), _atif("A"), _atif("B")])) == "A · B"
    assert arac_ozeti("x", ToolOutcome(ok=True, citations=[_atif("A"), _atif("B"), _atif("C")])) == "A ve 2 kaynak daha"


def test_atifsiz_basari_ve_uzunluk_ve_ham_govde_yok():
    assert arac_ozeti("netlestir", ToolOutcome(ok=True, text='{"soru": "…"}')) == "Tamamlandı"
    uzun = arac_ozeti("x", ToolOutcome(ok=True, citations=[_atif("ç" * 300)]))
    assert len(uzun) == 120 and uzun.endswith("…")
    assert "gövde metni" not in arac_ozeti("x", ToolOutcome(ok=True, citations=[_atif("Etiket")]))


def test_tool_end_olayi_ozet_tasir(tmp_path, monkeypatch):
    (tmp_path / "output").mkdir()
    runtime = AssistantRuntime(tmp_path)

    def sahte_dispatch(name, args, **kwargs):
        if name == "kitap_sayfa":
            return ToolOutcome(ok=True, text="sayfa", citations=[_atif("Fen Bilimleri 7 · s.12")])
        return ToolOutcome(ok=False, error="zaman aşımı")

    def dongu(*, dispatch, **kwargs):
        dispatch("kitap_sayfa", {"sayfa": 12})
        dispatch("mufredat_ara", {"q": "hücre"})
        return ToolLoopResult(text="cevap", citations=[])

    monkeypatch.setattr(runtime.registry, "declarations", lambda *a, **k: [])
    monkeypatch.setattr(runtime.registry, "degraded", lambda: [])
    monkeypatch.setattr(runtime.registry, "dispatch", sahte_dispatch)
    monkeypatch.setattr(runtime.llm, "chat_with_tools", dongu)

    bitenler = [e for e in runtime.chat_events(messages=[{"role": "user", "content": "hücre"}], session_id="s")
                if e["event"] == "tool_end"]
    assert bitenler == [
        {"event": "tool_end", "name": "kitap_sayfa", "ok": True, "ozet": "Fen Bilimleri 7 · s.12"},
        {"event": "tool_end", "name": "mufredat_ara", "ok": False, "ozet": "Bu kaynağa şu an ulaşılamadı"},
    ]
```

- [ ] **Step 2: Başarısız olduğunu gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_assistant_arac_ozeti.py`
Expected: FAIL — `ImportError: cannot import name 'arac_ozeti'`.

- [ ] **Step 3: Uygula**

`src/assistant_tools.py`, `class ToolOutcome` tanımının hemen altına:
```python
ARAC_OZETI_SINIRI = 120


def arac_ozeti(ad: str, sonuc: "ToolOutcome") -> str:
    """tool_end'in okura gösterilen tek satırı (Carbon AI Chat araç adımı, spec §5.1).

    Ham argüman ya da araç gövdesi asla girmez (D4): yalnız aracın kendi atıf etiketleri,
    yoksa sabit bir cümle."""
    if not getattr(sonuc, "ok", False):
        return "Bu kaynağa şu an ulaşılamadı"
    if ad == "skill_kaynagi":
        return "Öğretmen notlarına bakıldı"
    etiketler: list[str] = []
    for atif in getattr(sonuc, "citations", None) or []:
        etiket = " ".join(str((atif or {}).get("label") or "").split())
        if etiket and etiket not in etiketler:
            etiketler.append(etiket)
    if not etiketler:
        return "Tamamlandı"
    if len(etiketler) == 1:
        ozet = etiketler[0]
    elif len(etiketler) == 2:
        ozet = f"{etiketler[0]} · {etiketler[1]}"
    else:
        ozet = f"{etiketler[0]} ve {len(etiketler) - 1} kaynak daha"
    return ozet if len(ozet) <= ARAC_OZETI_SINIRI else ozet[:ARAC_OZETI_SINIRI - 1] + "…"
```

`src/assistant_core.py` `announcing` içinde (`events.put({"event": "tool_end", …})` satırı):
```python
            from src.assistant_tools import arac_ozeti
            events.put({"event": "tool_end", "name": name,
                        "ok": bool(outcome.ok), "ozet": arac_ozeti(name, outcome)})
```

- [ ] **Step 4: Geç ve eski akış testleri bozulmadı mı bak**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_assistant_arac_ozeti.py tests/test_assistant_core.py tests/test_assistant_ogretmen_modu.py tests/test_assistant_modul_araci.py tests/test_dashboard_api.py`
Expected: PASS (eskiler yalnız `event`/`name` alanlarına baktığı için etkilenmez).

- [ ] **Step 5: Commit**

```bash
git add src/assistant_tools.py src/assistant_core.py tests/test_assistant_arac_ozeti.py
git commit -m "feat(asistan): tool_end olayına okura gösterilen özet

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Arka uç — sayfa bağlamı alanı (`sayfa`)

Spec §5.3.

**Files:**
- Modify: `src/dashboard_api.py` (yeni `SAYFA_ADLARI`, `_istek_sayfasi`; `/api/assistant/chat` ve `/api/assistant/stream` görünümleri)
- Modify: `src/assistant_core.py` (`chat(...)` parametresi `sayfa_satiri`, `_build_conversation(...)` parametresi ve kullanıcı turu)
- Test: `tests/test_asistan_sayfa_baglami.py`

**Interfaces:**
- Produces: istek alanı `sayfa: {ad: str, oge?: {tur: str, id: str}}`; `AssistantRuntime.chat(..., sayfa_satiri: str = "")`; `_build_conversation(..., sayfa_satiri: str = "")`; kullanıcı turunda `Bulunduğu sayfa: <Etiket>[ (açık: <başlık>)]` satırı.

- [ ] **Step 1: Başarısız testleri yaz**

`tests/test_asistan_sayfa_baglami.py`:
```python
"""İstekteki sayfa bağlamı (spec §5.3): doğrulama, başlığın sunucuda çözülmesi, kullanıcı turu."""
import os

import pytest

os.environ["TEST_AUTH_BYPASS"] = "1"

from src import dashboard_api  # noqa: E402
from src.assistant_core import AssistantRuntime  # noqa: E402


class _Kayit:
    def __init__(self):
        self.kwargs = None

    def chat(self, **kwargs):
        self.kwargs = kwargs
        return {"answer": "cevap", "citations": [], "safety_flags": [], "plan_blocks": [],
                "intent": "qa", "session_id": "", "meta": {"model": "m", "degraded": []}}

    def chat_events(self, **kwargs):
        self.kwargs = kwargs
        yield {"event": "answer", "payload": self.chat(**kwargs)}


@pytest.fixture
def istemci(monkeypatch):
    kayit = _Kayit()
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: kayit)
    monkeypatch.setattr(dashboard_api, "_canli_odevler", lambda: [
        {"homework_key": "hw-1", "normalized_course": "Matematik", "Ödev Başlığı": "s.84 alıştırmalar"}])
    monkeypatch.setattr(dashboard_api, "_canli_sinavlar", lambda: [{"id": "abc123def456", "title": "Fen Bilimleri 1. Sınav"}])
    dashboard_api.app.config["TESTING"] = True
    with dashboard_api.app.test_client() as c:
        c.kayit = kayit
        yield c


SORU = {"messages": [{"role": "user", "content": "Bugün hangisinden başlayayım?"}]}


@pytest.mark.parametrize("uc", ["/api/assistant/chat", "/api/assistant/stream"])
@pytest.mark.parametrize("sayfa", [
    {"ad": "xyz"}, {"ad": 3}, "isler", {"ad": "isler", "oge": {"tur": "gizli", "id": "a"}},
    {"ad": "isler", "oge": {"tur": "odev", "id": ""}}, {"ad": "isler", "oge": {"tur": "odev", "id": "a\nb"}},
    {"ad": "isler", "oge": {"tur": "odev", "id": "x" * 401}},
])
def test_gecersiz_sayfa_akistan_once_400(istemci, uc, sayfa):
    yanit = istemci.post(uc, json={**SORU, "sayfa": sayfa})
    assert yanit.status_code == 400
    assert yanit.get_json()["error"] == "Bilinmeyen sayfa."
    assert istemci.kayit.kwargs is None


def test_sayfa_yoksa_satir_bos(istemci):
    assert istemci.post("/api/assistant/chat", json=SORU).status_code == 200
    assert istemci.kayit.kwargs["sayfa_satiri"] == ""


def test_odev_basligi_sunucudan_cozulur(istemci):
    istemci.post("/api/assistant/stream", json={**SORU, "sayfa": {"ad": "isler", "oge": {"tur": "odev", "id": "hw-1"}}}).get_data()
    assert istemci.kayit.kwargs["sayfa_satiri"] == "Bulunduğu sayfa: İşler (açık: Matematik — s.84 alıştırmalar)"


def test_cozulemeyen_oge_yalniz_sayfa_adi(istemci):
    istemci.post("/api/assistant/chat", json={**SORU, "sayfa": {"ad": "sinavlar", "oge": {"tur": "sinav", "id": "yok"}}})
    assert istemci.kayit.kwargs["sayfa_satiri"] == "Bulunduğu sayfa: Sınavlar"
    istemci.post("/api/assistant/chat", json={**SORU, "sayfa": {"ad": "sinavlar", "oge": {"tur": "sinav", "id": "abc123def456"}}})
    assert istemci.kayit.kwargs["sayfa_satiri"] == "Bulunduğu sayfa: Sınavlar (açık: Fen Bilimleri 1. Sınav)"


def test_satir_kullanici_turunda_sistemde_degil(tmp_path):
    (tmp_path / "output").mkdir()
    rt = AssistantRuntime(tmp_path)
    konusma = rt._build_conversation([{"role": "user", "content": "x"}], "x", "qa", [],
                                     sayfa_satiri="Bulunduğu sayfa: İşler")
    sistem = [m for m in konusma if m["role"] == "system"]
    assert all("Bulunduğu sayfa" not in str(m["content"]) for m in sistem)
    son = konusma[-1]
    assert son["role"] == "user" and "Bulunduğu sayfa: İşler\n" in son["content"]
    assert son["content"].endswith("Soru: x")
```

- [ ] **Step 2: Başarısız olduğunu gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_asistan_sayfa_baglami.py`
Expected: FAIL (400 dönmüyor; `sayfa_satiri` anahtarı yok; `_build_conversation` beklenmeyen argüman).

- [ ] **Step 3: Sunucu doğrulaması ve çözümleme**

`src/dashboard_api.py`, `_secili_odev` fonksiyonunun hemen altına:
```python
# Sayfa bağlamı (spec §5.3): yalnız sayfa adı ve öğe kimliği gelir; başlık buradan çözülür.
SAYFA_ADLARI = {
    "bugun": "Bugün", "isler": "İşler", "dersler": "Dersler", "notlar": "Notlar",
    "takvim": "Takvim", "takimlar": "Takımlar", "ilerleme": "İlerleme", "duyurular": "Duyurular",
    "profil": "Profil", "moduller": "Modüller", "kitaplar": "Tedy Books", "sinavlar": "Sınavlar",
}
SAYFA_OGE_TURLERI = ("odev", "sinav", "etkinlik", "ders_haftasi")


def _sayfa_ogesi_basligi(tur, kimlik):
    try:
        if tur == "odev":
            row = next((r for r in _canli_odevler() if r.get("homework_key") == kimlik), None)
            if row:
                ders = str(row.get("normalized_course") or row.get("Ders Adı") or "").strip()
                return f"{ders} — {str(row.get('Ödev Başlığı') or '').strip()}".strip(" —")
        elif tur == "sinav":
            sinav = next((s for s in _canli_sinavlar() if s.get("id") == kimlik), None)
            if sinav:
                return str(sinav.get("title") or "")
        elif tur == "etkinlik":
            olay = next((e for e in _birlesik_takvim(_scraped()) if e.get("id") == kimlik), None)
            if olay:
                return str(olay.get("title") or "")
        elif tur == "ders_haftasi":
            if kimlik in _icerik_haftalari(_scraped())["weeks"]:
                return kimlik
    except Exception as exc:  # noqa: BLE001 — bağlam satırı hiçbir zaman cevabı düşürmez
        app.logger.warning("Sayfa öğesi çözülemedi (%s)", type(exc).__name__)
    return ""


def _istek_sayfasi(payload):
    """(satır, None) ya da ("", 400 yanıtı). Alan yoksa boş satır — genel sohbet."""
    sayfa = (payload or {}).get("sayfa")
    if sayfa is None:
        return "", None
    hata = (jsonify({"error": "Bilinmeyen sayfa."}), 400)
    if not isinstance(sayfa, dict) or sayfa.get("ad") not in SAYFA_ADLARI:
        return "", hata
    satir = f"Bulunduğu sayfa: {SAYFA_ADLARI[sayfa['ad']]}"
    oge = sayfa.get("oge")
    if oge is None:
        return satir, None
    kimlik = oge.get("id") if isinstance(oge, dict) else None
    if (not isinstance(oge, dict) or oge.get("tur") not in SAYFA_OGE_TURLERI or not isinstance(kimlik, str)
            or not kimlik.strip() or len(kimlik) > 400 or any(ord(c) < 32 for c in kimlik)):
        return "", hata
    baslik = " ".join(_sayfa_ogesi_basligi(oge["tur"], kimlik).split())[:160]
    return (f"{satir} (açık: {baslik})" if baslik else satir), None
```

Her iki görünümde `_secili_odev` çağrısının hemen altına (`/chat`'te `payload`, `/stream`'de `data`):
```python
    sayfa_satiri, sayfa_hata = _istek_sayfasi(payload)   # /stream'de: _istek_sayfasi(data)
    if sayfa_hata is not None:
        return sayfa_hata
```
ve `runtime.chat(...)` / `runtime.chat_events(...)` çağrılarına `sayfa_satiri=sayfa_satiri,` eklenir.

- [ ] **Step 4: Çalışma zamanına geçir**

`src/assistant_core.py`:
- `def chat(…)` imzasında `secili_odev: str = "",` satırının altına `sayfa_satiri: str = "",`.
- `self._build_conversation(...)` çağrısına `sayfa_satiri=sayfa_satiri,`.
- `def _build_conversation(…)` imzasında `secili_odev: str = "",` altına `sayfa_satiri: str = "",`.
- Kullanıcı turunda `+ (f"\n{secili_odev}\n" if secili_odev else "\n")` satırının **önüne**:
```python
                + (f"{sayfa_satiri}\n" if sayfa_satiri else "")
```
(`chat_events` `**kwargs`'ı `chat`'e aynen geçirdiği için orada değişiklik gerekmez; yerel yedek bu satırı kullanmaz.)

- [ ] **Step 5: Geç**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_asistan_sayfa_baglami.py tests/test_assistant_core.py tests/test_dashboard_api.py tests/test_assistant_sohbet_api.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/dashboard_api.py src/assistant_core.py tests/test_asistan_sayfa_baglami.py
git commit -m "feat(asistan): istekte sayfa bağlamı; başlık sunucuda çözülür

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Arka uç — geri bildirim deposu

Spec §5.2 (depo kısmı).

**Files:**
- Modify: `src/assistant_sohbet.py` (`_SEM`, `sil`, yeni yöntemler, sabit)
- Test: `tests/test_assistant_geri_bildirim_deposu.py`

**Interfaces:**
- Produces (`SohbetDeposu`):
  - `GERI_BILDIRIM_KATEGORILERI: tuple[str, ...]` (modül sabiti)
  - `mesaj_sahibi(mid: str) -> dict | None` → `{"mesaj_id", "sohbet_id", "rol", "ogretmen", "sahip_email"}`
  - `geri_bildirim_yaz(mid: str, email: str, deger: str, kategori: str | None, metin: str, simdi: datetime) -> dict` (`ValueError` geçersiz girdide)
  - `geri_bildirim_sil(mid: str, email: str) -> bool`
  - `geri_bildirimler(sid: str, email: str) -> dict[str, dict]` (mesaj_id → `{"deger", "kategori", "metin"}`)
  - `geri_bildirim_ozeti(emails: set[str], simdi: datetime) -> dict` → `{"hafta": {"olumlu": int, "olumsuz": int}, "son_olumsuz": [{"kategori", "metin", "zaman"}]}` (en çok 5)

- [ ] **Step 1: Başarısız testleri yaz**

`tests/test_assistant_geri_bildirim_deposu.py`:
```python
from datetime import datetime, timedelta, timezone

import pytest

from src.assistant_sohbet import GERI_BILDIRIM_KATEGORILERI, SohbetDeposu

ISIK = "student@example.test"
SIMDI = datetime(2026, 10, 8, 9, 0, tzinfo=timezone.utc)  # Perşembe


@pytest.fixture
def depo(tmp_path):
    return SohbetDeposu(tmp_path / "s.sqlite")


def _cevap(depo):
    sid = depo.yarat(ISIK, "genel", SIMDI)
    depo.mesaj_ekle(sid, "user", "soru", "genel", [], SIMDI)
    mid = depo.mesaj_ekle(sid, "assistant", "cevap", "genel", [], SIMDI)
    return sid, mid


def test_kategoriler_sabit():
    assert GERI_BILDIRIM_KATEGORILERI == ("Yanlış bilgi", "Anlamadım", "Seviyeme uygun değil", "Kaynak göstermedi", "Diğer")


def test_yaz_guncelle_oku_sil(depo):
    sid, mid = _cevap(depo)
    assert depo.mesaj_sahibi(mid) == {"mesaj_id": mid, "sohbet_id": sid, "rol": "assistant",
                                      "ogretmen": "genel", "sahip_email": ISIK}
    depo.geri_bildirim_yaz(mid, ISIK, "olumlu", None, "", SIMDI)
    depo.geri_bildirim_yaz(mid, ISIK, "olumsuz", "Anlamadım", "  çok hızlı  ", SIMDI)
    assert depo.geri_bildirimler(sid, ISIK) == {mid: {"deger": "olumsuz", "kategori": "Anlamadım", "metin": "çok hızlı"}}
    assert depo.geri_bildirim_sil(mid, ISIK) is True
    assert depo.geri_bildirim_sil(mid, ISIK) is False
    assert depo.geri_bildirimler(sid, ISIK) == {}


@pytest.mark.parametrize("deger,kategori,metin", [
    ("iyi", None, ""), ("olumlu", "Anlamadım", ""), ("olumsuz", "Başka", ""), ("olumsuz", None, "x" * 501),
])
def test_gecersiz_girdi(depo, deger, kategori, metin):
    _, mid = _cevap(depo)
    with pytest.raises(ValueError):
        depo.geri_bildirim_yaz(mid, ISIK, deger, kategori, metin, SIMDI)


def test_sohbet_silinince_geri_bildirim_gider(depo):
    sid, mid = _cevap(depo)
    depo.geri_bildirim_yaz(mid, ISIK, "olumsuz", "Diğer", "neden", SIMDI)
    depo.sil(sid)
    assert depo.mesaj_sahibi(mid) is None
    assert depo.geri_bildirim_ozeti({ISIK}, SIMDI) == {"hafta": {"olumlu": 0, "olumsuz": 0}, "son_olumsuz": []}


def test_ozet_hafta_ve_son_bes(depo):
    for i in range(7):
        _, mid = _cevap(depo)
        depo.geri_bildirim_yaz(mid, ISIK, "olumsuz", "Yanlış bilgi", f"not {i}", SIMDI + timedelta(minutes=i))
    _, mid = _cevap(depo)
    depo.geri_bildirim_yaz(mid, ISIK, "olumlu", None, "", SIMDI)
    _, eski = _cevap(depo)
    depo.geri_bildirim_yaz(eski, ISIK, "olumsuz", "Diğer", "geçen hafta", SIMDI - timedelta(days=7))
    ozet = depo.geri_bildirim_ozeti({ISIK}, SIMDI)
    assert ozet["hafta"] == {"olumlu": 1, "olumsuz": 7}
    assert [n["metin"] for n in ozet["son_olumsuz"]] == ["not 6", "not 5", "not 4", "not 3", "not 2"]
    assert ozet["son_olumsuz"][0]["kategori"] == "Yanlış bilgi"
    assert depo.geri_bildirim_ozeti({"baska@example.test"}, SIMDI)["hafta"] == {"olumlu": 0, "olumsuz": 0}
```

- [ ] **Step 2: Başarısız olduğunu gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_assistant_geri_bildirim_deposu.py`
Expected: FAIL — `ImportError: cannot import name 'GERI_BILDIRIM_KATEGORILERI'`.

- [ ] **Step 3: Uygula**

`src/assistant_sohbet.py` — `_SEM` sonuna (kapanış `"""`'den önce):
```sql
CREATE TABLE IF NOT EXISTS geri_bildirim (
    mesaj_id TEXT NOT NULL, sahip_email TEXT NOT NULL, deger TEXT NOT NULL,
    kategori TEXT, metin TEXT NOT NULL DEFAULT '', zaman TEXT NOT NULL,
    PRIMARY KEY (mesaj_id, sahip_email)
);
```

Modül sabiti (`zaman_yazi`'nın üstüne):
```python
GERI_BILDIRIM_KATEGORILERI = ("Yanlış bilgi", "Anlamadım", "Seviyeme uygun değil", "Kaynak göstermedi", "Diğer")
GERI_BILDIRIM_METIN_SINIRI = 500
```

`sil` içinde `DELETE FROM mesaj …` satırının **önüne**:
```python
                conn.execute("DELETE FROM geri_bildirim WHERE mesaj_id IN "
                             "(SELECT id FROM mesaj WHERE sohbet_id = ?)", (sid,))
```

`SohbetDeposu` sınıfının sonuna:
```python
    def mesaj_sahibi(self, mid: str) -> dict | None:
        with self._baglan() as conn:
            row = conn.execute(
                "SELECT m.id AS mesaj_id, m.sohbet_id, m.rol, m.ogretmen, s.sahip_email FROM mesaj m "
                "JOIN sohbet s ON s.id = m.sohbet_id WHERE m.id = ?", (mid,)).fetchone()
        return dict(row) if row else None

    def geri_bildirim_yaz(self, mid: str, email: str, deger: str, kategori: str | None,
                          metin: str, simdi: datetime) -> dict:
        metin = " ".join(str(metin or "").split())
        if deger not in ("olumlu", "olumsuz"):
            raise ValueError("deger")
        if deger == "olumlu" and kategori is not None:
            raise ValueError("kategori")
        if kategori is not None and kategori not in GERI_BILDIRIM_KATEGORILERI:
            raise ValueError("kategori")
        if len(metin) > GERI_BILDIRIM_METIN_SINIRI:
            raise ValueError("metin")
        with self._baglan() as conn:
            conn.execute(
                "INSERT INTO geri_bildirim (mesaj_id, sahip_email, deger, kategori, metin, zaman) "
                "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (mesaj_id, sahip_email) DO UPDATE SET "
                "deger = excluded.deger, kategori = excluded.kategori, metin = excluded.metin, zaman = excluded.zaman",
                (mid, email, deger, kategori, metin, zaman_yazi(simdi)))
        return {"deger": deger, "kategori": kategori, "metin": metin}

    def geri_bildirim_sil(self, mid: str, email: str) -> bool:
        with self._baglan() as conn:
            return conn.execute("DELETE FROM geri_bildirim WHERE mesaj_id = ? AND sahip_email = ?",
                                (mid, email)).rowcount > 0

    def geri_bildirimler(self, sid: str, email: str) -> dict[str, dict]:
        with self._baglan() as conn:
            rows = conn.execute(
                "SELECT g.mesaj_id, g.deger, g.kategori, g.metin FROM geri_bildirim g "
                "JOIN mesaj m ON m.id = g.mesaj_id WHERE m.sohbet_id = ? AND g.sahip_email = ?",
                (sid, email)).fetchall()
        return {r["mesaj_id"]: {"deger": r["deger"], "kategori": r["kategori"], "metin": r["metin"]} for r in rows}

    def geri_bildirim_ozeti(self, emails: set[str], simdi: datetime) -> dict:
        bas, son = hafta_araligi(simdi)
        sonuc = {"hafta": {"olumlu": 0, "olumsuz": 0}, "son_olumsuz": []}
        if not emails:
            return sonuc
        yer = ",".join("?" * len(emails))
        with self._baglan() as conn:
            for r in conn.execute(
                    f"SELECT deger, COUNT(*) AS n FROM geri_bildirim WHERE sahip_email IN ({yer}) "
                    "AND zaman >= ? AND zaman < ? GROUP BY deger",
                    (*sorted(emails), zaman_yazi(bas), zaman_yazi(son))):
                sonuc["hafta"][r["deger"]] = r["n"]
            sonuc["son_olumsuz"] = [dict(r) for r in conn.execute(
                f"SELECT kategori, metin, zaman FROM geri_bildirim WHERE sahip_email IN ({yer}) "
                "AND deger = 'olumsuz' ORDER BY zaman DESC, rowid DESC LIMIT 5", tuple(sorted(emails)))]
        return sonuc
```

- [ ] **Step 4: Geç**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_assistant_geri_bildirim_deposu.py tests/test_assistant_sohbet.py tests/test_assistant_sohbet_api.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/assistant_sohbet.py tests/test_assistant_geri_bildirim_deposu.py
git commit -m "feat(asistan): geri bildirim tablosu ve deposu

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Arka uç — geri bildirim uçları, `mesaj_id`, geçmişte değer, günlük özeti

Spec §5.2 (API kısmı). Kayıt satırı `output/assistant_geri_bildirim.jsonl`'a yazılır (spec güncellemesi: `assistant_metrics.jsonl`'ın her satırı bir cevap sayılıyor, `assistant_ops metrics` özetini bozardı).

**Files:**
- Modify: `src/dashboard_api.py` (`_sohbet_cevap_kaydet`, `_sohbet_istegini_hazirla` tekrar yükü, `assistant_sohbet` GET, `assistant_ogrenme_gunlugu`, yeni uç)
- Test: `tests/test_assistant_geri_bildirim_api.py`

**Interfaces:**
- Consumes: Görev 5'teki depo yöntemleri.
- Produces:
  - Cevap yükünde (SSE `answer.payload` ve `/chat` JSON) `mesaj_id: str` — yalnız sohbet kimliğiyle kaydedilen cevaplarda; tekrar yükünde de.
  - `PUT /api/assistant/mesajlar/<mid>/geri-bildirim` gövde `{deger: 'olumlu'|'olumsuz', kategori?: str|null, metin?: str}` → 200 `{deger, kategori, metin}`; `DELETE` → 204.
  - `GET /api/assistant/sohbetler/<sid>` her asistan mesajında `geri_bildirim: {deger, kategori, metin} | null` (yalnız sahibe; salt okuyana hep `null`).
  - `GET /api/assistant/ogrenme-gunlugu` → ek alan `geri_bildirim` (Görev 5 özeti; aile için öğrencinin, öğrenci için kendisinin).

- [ ] **Step 1: Başarısız testleri yaz**

`tests/test_assistant_geri_bildirim_api.py`:
```python
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

os.environ["TEST_AUTH_BYPASS"] = "1"

from src import dashboard_api  # noqa: E402

ISIK, AILE, DIGER = "student@example.test", "parent@example.test", "other@example.test"
SIMDI = datetime(2026, 10, 8, 9, 0, tzinfo=timezone.utc)


class _Rt:
    def chat(self, **kwargs):
        return {"answer": "cevap", "citations": [], "safety_flags": [], "plan_blocks": [], "intent": "qa",
                "session_id": "", "meta": {"model": "m", "degraded": []}}

    def chat_events(self, **kwargs):
        yield {"event": "answer", "payload": self.chat(**kwargs)}


@pytest.fixture
def istemci(monkeypatch, tmp_path):
    monkeypatch.setattr(dashboard_api, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", True)
    monkeypatch.setattr(dashboard_api, "USER_ROLES", {ISIK: "full", AILE: "full", DIGER: "full"})
    monkeypatch.setattr(dashboard_api, "OGRENCI_EMAILS", {ISIK}, raising=False)
    monkeypatch.setattr(dashboard_api, "okur_turu", lambda e: "ogrenci" if e == ISIK else "aile")
    monkeypatch.setattr(dashboard_api, "_asistan_simdi", lambda: SIMDI, raising=False)
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: _Rt())
    monkeypatch.setattr(dashboard_api, "_sohbet_ozetle", lambda sohbet: None)
    dashboard_api.app.config["TESTING"] = True
    with dashboard_api.app.test_client() as c:
        yield c


def _giris(c, email):
    with c.session_transaction() as ses:
        ses["user_email"] = email


def _cevapli_sohbet(c):
    _giris(c, ISIK)
    sid = c.post("/api/assistant/sohbetler", json={"ogretmen": "genel"}).get_json()["id"]
    rid = "0123456789abcdef0123456789abcdef"
    yuk = c.post("/api/assistant/chat", json={"sohbet_id": sid, "request_id": rid,
                                               "messages": [{"role": "user", "content": "soru"}]}).get_json()
    return sid, rid, yuk


def test_cevap_mesaj_id_tasir_tekrar_da(istemci):
    sid, rid, yuk = _cevapli_sohbet(istemci)
    assert len(yuk["mesaj_id"]) == 32
    tekrar = istemci.post("/api/assistant/chat", json={"sohbet_id": sid, "request_id": rid,
                                                       "messages": [{"role": "user", "content": "soru"}]}).get_json()
    assert tekrar["mesaj_id"] == yuk["mesaj_id"]
    akis = istemci.post("/api/assistant/stream", json={"sohbet_id": sid, "request_id": rid,
                                                       "messages": [{"role": "user", "content": "soru"}]}).get_data(as_text=True)
    assert f'"mesaj_id": "{yuk["mesaj_id"]}"' in akis


def test_put_delete_ve_gecmiste_deger(istemci, tmp_path):
    sid, _, yuk = _cevapli_sohbet(istemci)
    uc = f"/api/assistant/mesajlar/{yuk['mesaj_id']}/geri-bildirim"
    r = istemci.put(uc, json={"deger": "olumsuz", "kategori": "Anlamadım", "metin": "hızlı"})
    assert r.status_code == 200 and r.get_json() == {"deger": "olumsuz", "kategori": "Anlamadım", "metin": "hızlı"}
    mesajlar = istemci.get(f"/api/assistant/sohbetler/{sid}").get_json()["mesajlar"]
    assert [m.get("geri_bildirim") for m in mesajlar] == [None, {"deger": "olumsuz", "kategori": "Anlamadım", "metin": "hızlı"}]
    kayit = [json.loads(s) for s in (tmp_path / "assistant_geri_bildirim.jsonl").read_text().splitlines()]
    assert kayit[-1]["deger"] == "olumsuz" and kayit[-1]["metin_uzunlugu"] == 5 and "metin" not in kayit[-1]
    assert istemci.delete(uc).status_code == 204
    assert istemci.delete(uc).status_code == 404


@pytest.mark.parametrize("govde", [{"deger": "iyi"}, {"deger": "olumsuz", "kategori": "Başka"},
                                   {"deger": "olumsuz", "metin": "x" * 501}, ["olumlu"]])
def test_gecersiz_govde_400(istemci, govde):
    _, _, yuk = _cevapli_sohbet(istemci)
    assert istemci.put(f"/api/assistant/mesajlar/{yuk['mesaj_id']}/geri-bildirim", json=govde).status_code == 400


def test_sahiplik(istemci, monkeypatch):
    sid, _, yuk = _cevapli_sohbet(istemci)
    uc = f"/api/assistant/mesajlar/{yuk['mesaj_id']}/geri-bildirim"
    _giris(istemci, AILE)
    r = istemci.put(uc, json={"deger": "olumlu"})
    assert r.status_code == 403 and r.get_json()["error"] == "Bu sohbet salt okunur."
    assert all(m.get("geri_bildirim") is None for m in istemci.get(f"/api/assistant/sohbetler/{sid}").get_json()["mesajlar"])
    monkeypatch.setattr(dashboard_api, "okur_turu", lambda e: {ISIK: "ogrenci", AILE: "aile"}.get(e, "bilinmiyor"))
    _giris(istemci, DIGER)
    assert istemci.put(uc, json={"deger": "olumlu"}).status_code == 404
    _giris(istemci, ISIK)
    assert istemci.put("/api/assistant/mesajlar/" + "f" * 32 + "/geri-bildirim", json={"deger": "olumlu"}).status_code == 404
    assert istemci.put("/api/assistant/mesajlar/x/geri-bildirim", json={"deger": "olumlu"}).status_code == 404


def test_kullanici_mesajina_geri_bildirim_yok(istemci):
    sid, _, _ = _cevapli_sohbet(istemci)
    kullanici = istemci.get(f"/api/assistant/sohbetler/{sid}").get_json()["mesajlar"][0]["id"]
    assert istemci.put(f"/api/assistant/mesajlar/{kullanici}/geri-bildirim", json={"deger": "olumlu"}).status_code == 404


def test_gunluk_aileye_ogrencinin_ozeti(istemci):
    _, _, yuk = _cevapli_sohbet(istemci)
    istemci.put(f"/api/assistant/mesajlar/{yuk['mesaj_id']}/geri-bildirim",
                json={"deger": "olumsuz", "kategori": "Yanlış bilgi", "metin": "kesir yanlış"})
    _giris(istemci, AILE)
    ozet = istemci.get("/api/assistant/ogrenme-gunlugu").get_json()["geri_bildirim"]
    assert ozet["hafta"] == {"olumlu": 0, "olumsuz": 1}
    assert ozet["son_olumsuz"][0]["metin"] == "kesir yanlış"
```

- [ ] **Step 2: Başarısız olduğunu gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_assistant_geri_bildirim_api.py`
Expected: FAIL (`KeyError: 'mesaj_id'`, 404/405 uç yok).

- [ ] **Step 3: `mesaj_id`'yi yüke koy**

`_sohbet_cevap_kaydet` içinde `mid = depo.mesaj_ekle(...)` satırının hemen altına:
```python
    # Okurun geri bildirimi bu kimliğe yazılır (spec §5.2); SSE `answer` gövdesi bundan sonra kurulur.
    payload["mesaj_id"] = mid
```
`_sohbet_istegini_hazirla` içindeki `"tekrar": {` sözlüğüne `"mesaj_id": cevap["id"],` eklenir.

- [ ] **Step 4: Uç, geçmiş, günlük**

`src/dashboard_api.py`, `assistant_ogrenme_gunlugu`'nun altına:
```python
def _geri_bildirim_kaydi(kayit):
    """Sunucu kaydı: metnin kendisi değil uzunluğu. .jsonl asistan indeksine girmez."""
    try:
        yol = Path(OUTPUT_DIR) / "assistant_geri_bildirim.jsonl"
        with yol.open("a", encoding="utf-8") as f:
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
    except OSError:
        pass


@app.route("/api/assistant/mesajlar/<mid>/geri-bildirim", methods=["PUT", "DELETE"])
@require_auth
@_sohbet_kapisi
def assistant_geri_bildirim(mid):
    email = _module_person()
    depo = _sohbet_deposu()
    mesaj = depo.mesaj_sahibi(mid) if re.fullmatch(r"[0-9a-f]{32}", mid or "") else None
    if mesaj is None or mesaj["rol"] != "assistant":
        return jsonify({"error": "Mesaj bulunamadı."}), 404
    if mesaj["sahip_email"] != email:
        if okur_turu(email) == "aile" and mesaj["sahip_email"] in OGRENCI_EMAILS:
            return jsonify({"error": "Bu sohbet salt okunur."}), 403
        return jsonify({"error": "Mesaj bulunamadı."}), 404
    if request.method == "DELETE":
        if not depo.geri_bildirim_sil(mid, email):
            return jsonify({"error": "Geri bildirim bulunamadı."}), 404
        return "", 204
    govde = request.get_json(silent=True)
    if not isinstance(govde, dict):
        return jsonify({"error": "Geçersiz istek gövdesi."}), 400
    try:
        sonuc = depo.geri_bildirim_yaz(mid, email, govde.get("deger"), govde.get("kategori"),
                                       govde.get("metin") or "", _asistan_simdi())
    except (ValueError, TypeError):
        return jsonify({"error": "Geçersiz geri bildirim."}), 400
    _geri_bildirim_kaydi({"zaman": _asistan_simdi().isoformat(), "mesaj_id": mid, "sohbet_id": mesaj["sohbet_id"],
                          "ogretmen": mesaj["ogretmen"], "deger": sonuc["deger"], "kategori": sonuc["kategori"],
                          "metin_uzunlugu": len(sonuc["metin"])})
    return jsonify(sonuc)
```
(`from pathlib import Path` ve `re` dosyada yoksa en üstteki içe aktarmalara eklenir.)

`assistant_sohbet` GET dalında `for mesaj in mesajlar:` döngüsünden önce:
```python
        geri = depo.geri_bildirimler(sid, _module_person()) if sahip else {}
```
döngünün içine:
```python
            mesaj["geri_bildirim"] = geri.get(mesaj["id"]) if mesaj["rol"] == "assistant" else None
```

`assistant_ogrenme_gunlugu` gövdesi:
```python
    email = _module_person()
    depo = _sohbet_deposu()
    gunluk = depo.gunluk(email, _asistan_simdi())
    kisiler = set(OGRENCI_EMAILS) if okur_turu(email) == "aile" else {email}
    gunluk["geri_bildirim"] = depo.geri_bildirim_ozeti(kisiler, _asistan_simdi())
    return jsonify(gunluk)
```

- [ ] **Step 5: Geç**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_assistant_geri_bildirim_api.py tests/test_assistant_sohbet_api.py tests/test_dashboard_api.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/dashboard_api.py tests/test_assistant_geri_bildirim_api.py
git commit -m "feat(asistan): geri bildirim uçları, cevapta mesaj_id, günlükte özet

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 7: Saf eşleme — atıflar ve SSE olayı → Carbon parçaları

Spec §2. React ve DOM'a dokunmayan iki modül; bütün akış kuralları burada ve birim testlerle sabitlenir.

**Files:**
- Create: `dashboard/src/asistan/atiflar.ts`
- Create: `dashboard/src/asistan/olayEslemesi.ts`
- Modify: `dashboard/src/types.ts` (`AssistantResponse.mesaj_id?: string`; `meta.denetim?: { durum?: string }`)
- Test: `dashboard/tests/atiflar.test.ts`, `dashboard/tests/olay-eslemesi.test.ts`

**Interfaces:**
- Produces (`atiflar.ts`):
  - `atiflariAyikla(ham: string, kaynaklar: AssistantCitation[]): { metin: string; atiflar: ConversationalSearchItemCitation[]; kimlikler: string[] }` — `kimlikler[i]`, `atiflar[i]`'nin TEDY atıf kimliğidir (`S1`…).
- Produces (`olayEslemesi.ts`):
  - `ARAC_ETIKETI: Record<string, string>`, `VARSAYILAN_ADIM = 'Kaynaklar taranıyor'`
  - `type OzelKart` (birleşim: `alistirma` | `odev_onerisi` | `netlestirme` | `mod_onerisi` | `plan` | `hata`)
  - `interface Adim { arac; baslik; durum: 'processing'|'success'|'failure'; ozet? }`
  - `interface AkisDurumu`, `interface TedyOlayi { ad: string; veri: Record<string, unknown> }`
  - `interface AltbilgiVerisi { mesajId?: string; model?: string; bayraklar: string[]; kaynakSorunlari: string[]; ogretmen?: string; denetim?: string; metin: string; atiflar: AssistantCitation[] }`
  - `interface SonYanitSecenekleri { geriBildirim: boolean; ogrenci: boolean }`
  - `class AkisHatasi extends Error`
  - `taslakMetni(text: string): string`
  - `akisBaslat(yanitId: string): AkisDurumu`
  - `olayIsle(d: AkisDurumu, o: TedyOlayi, sec: SonYanitSecenekleri): { durum: AkisDurumu; parcalar: StreamChunk[]; kaldir?: string[] }`
  - `sonYanit(d: AkisDurumu, payload: AssistantResponse, sec: SonYanitSecenekleri): MessageResponse`
  - `hataYaniti(yanitId: string, mesaj: string): MessageResponse`
  - `ALTBILGI_YUVASI = 'tedy-altbilgi'`, `GERI_BILDIRIM_KATEGORILERI: string[]`

- [ ] **Step 1: Atıf testlerini yaz**

`dashboard/tests/atiflar.test.ts`:
```ts
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { atiflariAyikla } from '../src/asistan/atiflar.ts'
import type { AssistantCitation } from '../src/types.ts'

const k = (id: string, label = `Kaynak ${id}`): AssistantCitation =>
  ({ id, kind: 'mufredat', label, locator: {}, snippet: `${label} parçası`, confidence: 1 })

test('işaret metinden çıkar, cümle aralığı kalır', () => {
  const r = atiflariAyikla('Kesir parçadır [S1]. Payda eşit parçadır [S2].', [k('S1'), k('S2')])
  assert.equal(r.metin, 'Kesir parçadır. Payda eşit parçadır.')
  assert.deepEqual(r.kimlikler, ['S1', 'S2'])
  assert.deepEqual(r.atiflar[0].ranges, [{ start: 0, end: 14 }])
  assert.deepEqual(r.atiflar[1].ranges, [{ start: 16, end: 35 }])
  assert.equal(r.atiflar[0].title, 'Kaynak S1')
  assert.equal(r.atiflar[0].text, 'Kaynak S1 parçası')
})

test('aynı kaynak iki kez: tek atıf, iki aralık', () => {
  const r = atiflariAyikla('A cümlesi [S1]. B cümlesi [S1].', [k('S1')])
  assert.equal(r.atiflar.length, 1)
  assert.equal(r.atiflar[0].ranges?.length, 2)
})

test('metin başı, blok, tablo hücresi ve liste: aralık metnin içinde, işaret kalmaz', () => {
  const ham = '[S1] Giriş.\n:::kavram\nPay üstteki sayıdır [S2].\n:::\n| a [S3] | b |\n|---|---|\n- madde [S1]'
  const r = atiflariAyikla(ham, [k('S1'), k('S2'), k('S3')])
  assert.ok(!/\[S\d/.test(r.metin))
  for (const a of r.atiflar) for (const g of a.ranges ?? []) {
    assert.ok(g.start >= 0 && g.end <= r.metin.length && g.start <= g.end)
  }
  assert.ok((r.atiflar[0].ranges ?? []).every(g => g.end > g.start))
  assert.equal(r.metin.slice(r.atiflar[1].ranges![0].start, r.atiflar[1].ranges![0].end), 'Pay üstteki sayıdır')
  assert.equal(r.metin.slice(r.atiflar[2].ranges![0].start, r.atiflar[2].ranges![0].end), '| a')
})

test('boş aralık atılır ama atıf listede kalır', () => {
  const r = atiflariAyikla('[S1] Metin', [k('S1')])
  assert.equal(r.metin, 'Metin')
  assert.deepEqual(r.atiflar[0].ranges, [])
})

test('çözülemeyen işaret metin olarak kalır', () => {
  const r = atiflariAyikla('Bir şey [S9].', [k('S1')])
  assert.equal(r.metin, 'Bir şey [S9].')
  assert.deepEqual(r.atiflar, [])
})
```

- [ ] **Step 2: Atıf modülünü yaz**

`dashboard/src/asistan/atiflar.ts`:
```ts
import type { AssistantCitation } from '../types'
import type { ConversationalSearchItemCitation } from '@carbon/ai-chat'

const ISARET = /\s?\[(S\d+)\]/g

/** `[S1]` işaretlerinin kapsadığı cümlenin başı: son satır sonu ya da ". ", "! ", "? " sonrası. */
function cumleBasi(metin: string, bitis: number): number {
  let bas = 0
  for (const m of metin.slice(0, Math.max(0, bitis - 1)).matchAll(/[.!?]\s+|\n/g)) bas = (m.index ?? 0) + m[0].length
  while (bas < bitis && /\s/.test(metin[bas])) bas += 1
  return bas
}

/** Sunucunun okuma sırasıyla numaraladığı işaretleri metinden çıkarır, Carbon'un `ranges` biçimine çevirir.
 *  Çözülemeyen işaret metinde kalır (eski arayüzdeki gibi görünür kalır, yutulmaz). */
export function atiflariAyikla(ham: string, kaynaklar: AssistantCitation[]) {
  const byId = new Map(kaynaklar.map(k => [k.id, k]))
  const araliklar = new Map<string, { start: number; end: number }[]>()
  const kimlikler: string[] = []
  let metin = ''
  let son = 0
  for (const m of ham.matchAll(ISARET)) {
    const bas = m.index ?? 0
    metin += ham.slice(son, bas)
    son = bas + m[0].length
    if (metin === '' && ham[son] === ' ') son += 1   // metnin başındaki işaretin ardındaki boşluk da gider
    const id = m[1]
    if (!byId.has(id)) { metin += m[0]; continue }
    if (!araliklar.has(id)) { araliklar.set(id, []); kimlikler.push(id) }
    const bitis = metin.trimEnd().length
    const start = cumleBasi(metin, bitis)
    if (bitis > start) araliklar.get(id)!.push({ start, end: bitis })
  }
  metin += ham.slice(son)
  const atiflar: ConversationalSearchItemCitation[] = kimlikler.map(id => {
    const k = byId.get(id)!
    return { title: k.label, text: k.snippet, ranges: araliklar.get(id) ?? [] }
  })
  return { metin, atiflar, kimlikler }
}
```

- [ ] **Step 3: Atıf testlerini koş**

Run: `cd dashboard && node --test tests/atiflar.test.ts`
Expected: PASS (5 test).

- [ ] **Step 4: Olay eşleme testlerini yaz**

`dashboard/tests/olay-eslemesi.test.ts`:
```ts
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { akisBaslat, olayIsle, sonYanit, hataYaniti, taslakMetni, AkisHatasi, ALTBILGI_YUVASI }
  from '../src/asistan/olayEslemesi.ts'
import type { AkisDurumu, TedyOlayi } from '../src/asistan/olayEslemesi.ts'
import type { AssistantResponse } from '../src/types.ts'

const SEC = { geriBildirim: true, ogrenci: true }
const yuk = (p: Partial<AssistantResponse> = {}): AssistantResponse => ({
  answer: 'Cevap [S1].', citations: [{ id: 'S1', kind: 'mufredat', label: 'Mat 7 · s.5', locator: {}, snippet: 's', confidence: 1 }],
  safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '', meta: { model: 'claude-sonnet-5', degraded: [] },
  mesaj_id: 'a'.repeat(32), ...p,
})
function oynat(olaylar: TedyOlayi[]) {
  let d: AkisDurumu = akisBaslat('y1')
  const tum: unknown[] = []
  for (const o of olaylar) { const r = olayIsle(d, o, SEC); d = r.durum; tum.push(...r.parcalar) }
  return { d, tum: tum as Record<string, any>[] }
}

test('taslak işaretleri gizler, yarım işareti de', () => {
  assert.equal(taslakMetni('Payda [S1] eşit [S'), 'Payda eşit')
})

test('delta parçaları biriktirir, yarım işaret sonra gelmez', () => {
  const { tum } = oynat([{ ad: 'answer_delta', veri: { text: 'Payda [S' } }, { ad: 'answer_delta', veri: { text: '1] eşit' } }])
  const metinler = tum.map(p => p.partial_item?.text)
  assert.deepEqual(metinler, ['Payda', ' eşit'])
  assert.equal(tum[0].partial_item.streaming_metadata.id, 'metin-0')
  assert.equal(tum[0].streaming_metadata.response_id, 'y1')
})

test('answer_reset taslağı boşaltır ve yeni öğeye geçer', () => {
  const { tum } = oynat([{ ad: 'answer_delta', veri: { text: 'Önce bakayım.' } }, { ad: 'answer_reset', veri: {} },
    { ad: 'answer_delta', veri: { text: 'Asıl' } }])
  assert.deepEqual(tum[1].complete_item, { response_type: 'text', text: '', streaming_metadata: { id: 'metin-0' } })
  assert.equal(tum[2].partial_item.streaming_metadata.id, 'metin-1')
})

test('araç adımları sürer ve özetle biter', () => {
  const { d, tum } = oynat([{ ad: 'tool_start', veri: { name: 'kitap_sayfa' } },
    { ad: 'tool_end', veri: { name: 'kitap_sayfa', ok: true, ozet: 'Mat 7 · s.5' } },
    { ad: 'tool_start', veri: { name: 'yeni_arac' } }, { ad: 'tool_end', veri: { name: 'yeni_arac', ok: false } }])
  const adimlar = tum[3].partial_response.message_options.chain_of_thought
  assert.deepEqual(adimlar[0], { title: 'Ders kitabı sayfası okunuyor', description: 'Mat 7 · s.5', tool_name: 'kitap_sayfa', status: 'success' })
  assert.equal(adimlar[1].title, 'Kaynaklar taranıyor')
  assert.equal(adimlar[1].status, 'failure')
  assert.equal(d.adimlar.length, 2)
})

test('answer final_response üretir: atıflı metin, altbilgi, geri bildirim, adımlar, kartlar', () => {
  const { tum } = oynat([{ ad: 'tool_start', veri: { name: 'mufredat_ara' } },
    { ad: 'tool_end', veri: { name: 'mufredat_ara', ok: true, ozet: 'Mat 7 · s.5' } },
    { ad: 'mode_suggestion', veri: { ogretmen: 'matematik', ogretmen_adi: 'Matematik öğretmeni', soru: 'x', gerekce: 'y', renk_ailesi: 'blue' } },
    { ad: 'mode_suggestion', veri: { ogretmen: 'fen' } },
    { ad: 'answer', veri: { payload: yuk() } }])
  const f = tum.at(-1)!.final_response
  assert.equal(f.id, 'y1')
  const [ana, kart] = f.output.generic
  assert.equal(ana.response_type, 'conversational_search')
  assert.equal(ana.text, 'Cevap.')
  assert.equal(ana.citations[0].title, 'Mat 7 · s.5')
  assert.equal(ana.message_item_options.feedback.id, 'a'.repeat(32))
  assert.equal(ana.message_item_options.feedback.placeholder, 'Ailen bunu görebilir.')
  assert.deepEqual(ana.message_item_options.feedback.categories.negative,
    ['Yanlış bilgi', 'Anlamadım', 'Seviyeme uygun değil', 'Kaynak göstermedi', 'Diğer'])
  assert.equal(ana.message_item_options.custom_footer_slot.slot_name, ALTBILGI_YUVASI)
  assert.equal(ana.message_item_options.custom_footer_slot.additional_data.metin, 'Cevap [S1].')
  assert.deepEqual(kart.user_defined.tedy, { tur: 'mod_onerisi', veri: { ogretmen: 'matematik', ogretmen_adi: 'Matematik öğretmeni', soru: 'x', gerekce: 'y', renk_ailesi: 'blue' } })
  assert.equal(f.message_options.chain_of_thought[0].status, 'success')
})

test('atıfsız cevap düz metin; mesaj kimliği yoksa geri bildirim yok; aile için yer tutucu', () => {
  const m = sonYanit(akisBaslat('y2'), yuk({ citations: [], answer: 'Merhaba', mesaj_id: undefined }), { geriBildirim: true, ogrenci: false })
  const ana = m.output.generic![0] as Record<string, any>
  assert.equal(ana.response_type, 'text')
  assert.equal(ana.message_item_options.feedback, undefined)
  const m2 = sonYanit(akisBaslat('y3'), yuk(), { geriBildirim: true, ogrenci: false }).output.generic![0] as Record<string, any>
  assert.equal(m2.message_item_options.feedback.placeholder, 'Yorum ekle')
})

test('boş cevap okura cümleyle; payload kartları akıştakinin önüne geçer; plan blokları kart olur', () => {
  let d = akisBaslat('y4')
  d = olayIsle(d, { ad: 'clarify', veri: { soru: 'akış', secenekler: ['a', 'b'] } }, SEC).durum
  d = olayIsle(d, { ad: 'quiz', veri: { id: 'q1', sorular: [] } }, SEC).durum
  const m = sonYanit(d, yuk({ answer: '  ', citations: [], netlestirme: { soru: 'yük', secenekler: ['c', 'd'] },
    plan_blocks: [{ day: 'Pzt', title: 't', actions: ['a'], estimated_minutes: 20 } as never] }), SEC)
  const g = m.output.generic as Record<string, any>[]
  assert.equal(g[0].text, 'Yanıt üretilemedi.')
  const turler = g.slice(1).map(x => x.user_defined.tedy.tur)
  assert.deepEqual(turler, ['alistirma', 'netlestirme', 'plan'])
  assert.equal(g.find(x => x.user_defined?.tedy.tur === 'netlestirme')!.user_defined.tedy.veri.soru, 'yük')
})

test('quiz akışta hemen kart olarak gelir', () => {
  const { tum } = oynat([{ ad: 'quiz', veri: { id: 'q1', sorular: [] } }])
  assert.deepEqual(tum[0].complete_item.user_defined.tedy, { tur: 'alistirma', veri: { id: 'q1', sorular: [] }, akista: true })
  assert.equal(tum[0].complete_item.streaming_metadata.id, 'kart-alistirma-0')
})

test('akis_dustu: eski mesaj kaldırılır, yeni kimlikle baştan başlanır', () => {
  let d = akisBaslat('y5')
  d = olayIsle(d, { ad: 'answer_delta', veri: { text: 'yarım' } }, SEC).durum
  const r = olayIsle(d, { ad: 'akis_dustu', veri: { yeniId: 'y6' } }, SEC)
  assert.deepEqual(r.kaldir, ['y5'])
  assert.equal(r.durum.yanitId, 'y6')
  assert.equal(r.durum.gorunen, '')
})

test('error olayı AkisHatasi fırlatır; hata yanıtı kart taşır', () => {
  assert.throws(() => olayIsle(akisBaslat('y7'), { ad: 'error', veri: { error: 'Asistan yanıtı alınamadı.' } }, SEC), AkisHatasi)
  const h = hataYaniti('y8', 'Oturumun sona ermiş; sayfayı yenileyip yeniden giriş yap.')
  assert.deepEqual((h.output.generic![0] as Record<string, any>).user_defined.tedy,
    { tur: 'hata', veri: { mesaj: 'Oturumun sona ermiş; sayfayı yenileyip yeniden giriş yap.' } })
})

test('yerel yedek ve kaynak sorunları altbilgiye geçer', () => {
  const m = sonYanit(akisBaslat('y9'), yuk({ citations: [], safety_flags: ['warning:yerel_yedek'],
    meta: { model: 'gemma4-e4b-cpu', degraded: ['maarif-mufredat'], ogretmen: 'fen', denetim: { durum: 'duzeltildi' } } }), SEC)
  const a = (m.output.generic![0] as Record<string, any>).message_item_options.custom_footer_slot.additional_data
  assert.deepEqual([a.bayraklar, a.kaynakSorunlari, a.model, a.ogretmen, a.denetim], [['warning:yerel_yedek'], ['maarif-mufredat'], 'gemma4-e4b-cpu', 'fen', 'duzeltildi'])
})
```

- [ ] **Step 5: Başarısız olduğunu gör**

Run: `cd dashboard && node --test tests/olay-eslemesi.test.ts`
Expected: FAIL — modül bulunamıyor.

- [ ] **Step 6: Olay eşlemesini yaz**

`dashboard/src/types.ts` — `AssistantResponse` içine `mesaj_id?: string` ve `meta` içine `denetim?: { durum?: string }` eklenir.

`dashboard/src/asistan/olayEslemesi.ts`:
```ts
// TEDY SSE olayları → Carbon AI Chat mesaj parçaları (spec §2). Saf: React'e, DOM'a ve
// @carbon/ai-chat'in çalışma zamanına dokunmaz; yalnız türlerini kullanır.
import type { AssistantCitation, AssistantPlanBlock, AssistantResponse, ModOnerisi, Netlestirme } from '../types'
import type { Alistirma } from '../components/AlistirmaKarti'
import type { OdevOnerisi } from '../components/OdevOnayKarti'
import type { ChainOfThoughtStep, GenericItem, MessageResponse, StreamChunk } from '@carbon/ai-chat'
import { atiflariAyikla } from './atiflar.ts'

export const ARAC_ETIKETI: Record<string, string> = {
  ogrenci_verisi_ara: 'Okul verilerin taranıyor', kazanim_ara: 'MEB kazanımları aranıyor',
  kazanim_listele: 'Kazanım listesi alınıyor', mufredat_ara: 'Müfredat aranıyor',
  kitap_listele: 'Ders kitapları listeleniyor', kitap_sayfa: 'Ders kitabı sayfası okunuyor',
  figur_ara: 'Görsel aranıyor', figur_getir: 'Görsel getiriliyor', oer_ara: 'Açık kaynaklar taranıyor',
  oer_kazanima_gore: 'Kazanıma bağlı kaynaklar alınıyor', modul_ara: 'Yayınlanmış modüller aranıyor',
  odev_listesi: 'Ödev listen okunuyor', odev_belgesi: 'Ödev belgesi aranıyor', odev_tamamla: 'Eksik alan kaydediliyor',
  skill_kaynagi: 'Öğretmen notları açılıyor', mod_oner: 'Öğretmen önerisi hazırlanıyor',
  netlestir: 'Seçenekler hazırlanıyor', alistirma_hazirla: 'Alıştırma hazırlanıyor',
  odev_fotograftan: 'Fotoğraftaki ödev okunuyor', yuklenen_dosya_oku: 'Ek okunuyor',
}
export const VARSAYILAN_ADIM = 'Kaynaklar taranıyor'
export const ALTBILGI_YUVASI = 'tedy-altbilgi'
export const GERI_BILDIRIM_KATEGORILERI = ['Yanlış bilgi', 'Anlamadım', 'Seviyeme uygun değil', 'Kaynak göstermedi', 'Diğer']

export type OzelKart =
  | { tur: 'alistirma'; veri: Alistirma; akista?: boolean }
  | { tur: 'odev_onerisi'; veri: OdevOnerisi }
  | { tur: 'netlestirme'; veri: Netlestirme }
  | { tur: 'mod_onerisi'; veri: ModOnerisi }
  | { tur: 'plan'; veri: AssistantPlanBlock[] }
  | { tur: 'hata'; veri: { mesaj: string } }

export interface Adim { arac: string; baslik: string; durum: 'processing' | 'success' | 'failure'; ozet?: string }
export interface TedyOlayi { ad: string; veri: Record<string, unknown> }
export interface SonYanitSecenekleri { geriBildirim: boolean; ogrenci: boolean }
export interface AltbilgiVerisi {
  mesajId?: string; model?: string; bayraklar: string[]; kaynakSorunlari: string[]
  ogretmen?: string; denetim?: string; metin: string; atiflar: AssistantCitation[]
}
export interface AkisDurumu {
  yanitId: string; ogeNo: number; ham: string; gorunen: string; adimlar: Adim[]
  alistirmalar: Alistirma[]; netlestirme: Netlestirme | null; modOnerisi: ModOnerisi | null
  odevOnerisi: OdevOnerisi | null; bitti: boolean
}

export class AkisHatasi extends Error {}

// Carbon'un dize enum'ları çalışma zamanında içe aktarılmaz (node testleri paketi yüklemez).
const tur = <T>(s: string) => s as unknown as T

/** Akan taslakta `[S1]` görünmez; kaynaklar ancak son cevapla gelir (D4). Yarım işaret de gizlenir. */
export function taslakMetni(text: string): string {
  return text.replace(/\s?\[S\d+\]/g, '').replace(/\s?\[(S\d*)?$/, '')
}

export function akisBaslat(yanitId: string): AkisDurumu {
  return { yanitId, ogeNo: 0, ham: '', gorunen: '', adimlar: [], alistirmalar: [], netlestirme: null,
    modOnerisi: null, odevOnerisi: null, bitti: false }
}

const meta = (d: AkisDurumu) => ({ streaming_metadata: { response_id: d.yanitId } })
const metinId = (d: AkisDurumu) => `metin-${d.ogeNo}`
const adimlar = (d: AkisDurumu): ChainOfThoughtStep[] => d.adimlar.map(a => ({
  title: a.baslik, ...(a.ozet ? { description: a.ozet } : {}), tool_name: a.arac, status: tur(a.durum),
}))

function kismi(d: AkisDurumu, text: string, adimlarla = false): StreamChunk {
  return {
    partial_item: { response_type: tur('text'), text, streaming_metadata: { id: metinId(d) } },
    ...(adimlarla ? { partial_response: { message_options: { chain_of_thought: adimlar(d) } } } : {}),
    ...meta(d),
  } as StreamChunk
}
function tam(d: AkisDurumu, item: Record<string, unknown>, id: string): StreamChunk {
  return { complete_item: { ...item, streaming_metadata: { id } }, ...meta(d) } as unknown as StreamChunk
}
const kartOgesi = (kart: OzelKart) => ({ response_type: tur('user_defined'), user_defined: { tedy: kart } })

export function olayIsle(d: AkisDurumu, o: TedyOlayi, sec: SonYanitSecenekleri):
  { durum: AkisDurumu; parcalar: StreamChunk[]; kaldir?: string[] } {
  const v = o.veri
  switch (o.ad) {
    case 'tool_start': {
      const arac = String(v.name ?? '')
      const durum = { ...d, adimlar: [...d.adimlar, { arac, baslik: ARAC_ETIKETI[arac] ?? VARSAYILAN_ADIM, durum: 'processing' as const }] }
      return { durum, parcalar: [kismi(durum, '', true)] }
    }
    case 'tool_end': {
      const arac = String(v.name ?? '')
      const yeni = [...d.adimlar]
      const i = yeni.map(a => a.arac === arac && a.durum === 'processing').lastIndexOf(true)
      if (i >= 0) yeni[i] = { ...yeni[i], durum: v.ok ? 'success' : 'failure', ...(v.ozet ? { ozet: String(v.ozet) } : {}) }
      const durum = { ...d, adimlar: yeni }
      return { durum, parcalar: [kismi(durum, '', true)] }
    }
    case 'answer_delta': {
      const ham = d.ham + String(v.text ?? '')
      const gorunur = taslakMetni(ham)
      const durum = { ...d, ham, gorunen: gorunur }
      if (gorunur.startsWith(d.gorunen)) {
        const parca = gorunur.slice(d.gorunen.length)
        return { durum, parcalar: parca ? [kismi(durum, parca)] : [] }
      }
      return { durum, parcalar: [tam(durum, { response_type: tur('text'), text: gorunur }, metinId(durum))] }
    }
    case 'answer_reset': {
      const bos = tam(d, { response_type: tur('text'), text: '' }, metinId(d))
      return { durum: { ...d, ogeNo: d.ogeNo + 1, ham: '', gorunen: '' }, parcalar: [bos] }
    }
    case 'quiz': {
      const veri = v as unknown as Alistirma
      const durum = { ...d, alistirmalar: [...d.alistirmalar, veri] }
      const kart: OzelKart = { tur: 'alistirma', veri, akista: true }
      return { durum, parcalar: [tam(durum, kartOgesi(kart), `kart-alistirma-${d.alistirmalar.length}`)] }
    }
    case 'mode_suggestion':
      return { durum: d.modOnerisi ? d : { ...d, modOnerisi: v as unknown as ModOnerisi }, parcalar: [] }
    case 'clarify':
      return { durum: { ...d, netlestirme: v as unknown as Netlestirme }, parcalar: [] }
    case 'odev_onerisi':
      return { durum: { ...d, odevOnerisi: v as unknown as OdevOnerisi }, parcalar: [] }
    case 'akis_dustu':
      return { durum: akisBaslat(String(v.yeniId ?? `${d.yanitId}-yedek`)), parcalar: [], kaldir: [d.yanitId] }
    case 'answer': {
      const payload = v.payload as AssistantResponse
      return { durum: { ...d, bitti: true }, parcalar: [{ final_response: sonYanit(d, payload, sec) } as StreamChunk] }
    }
    case 'error':
      throw new AkisHatasi(String(v.error ?? 'akış hatası'))
    default:
      return { durum: d, parcalar: [] }
  }
}

export function sonYanit(d: AkisDurumu, payload: AssistantResponse, sec: SonYanitSecenekleri): MessageResponse {
  const ham = (payload.answer || '').trim() || 'Yanıt üretilemedi.'
  const { metin, atiflar } = atiflariAyikla(ham, payload.citations ?? [])
  const altbilgi: AltbilgiVerisi = {
    mesajId: payload.mesaj_id, model: payload.meta?.model, bayraklar: payload.safety_flags ?? [],
    kaynakSorunlari: payload.meta?.degraded ?? [], ogretmen: payload.meta?.ogretmen,
    denetim: payload.meta?.denetim?.durum, metin: ham, atiflar: payload.citations ?? [],
  }
  const geriBildirim = sec.geriBildirim && payload.mesaj_id ? {
    is_on: true, id: payload.mesaj_id, show_positive_details: false, show_negative_details: true,
    show_text_area: true, show_prompt: true, max_length: 500,
    placeholder: sec.ogrenci ? 'Ailen bunu görebilir.' : 'Yorum ekle',
    categories: { negative: GERI_BILDIRIM_KATEGORILERI },
  } : undefined
  const ana = {
    response_type: tur(atiflar.length ? 'conversational_search' : 'text'), text: metin,
    ...(atiflar.length ? { citations: atiflar } : {}),
    message_item_options: {
      ...(geriBildirim ? { feedback: geriBildirim } : {}),
      custom_footer_slot: { slot_name: ALTBILGI_YUVASI, is_on: true, additional_data: altbilgi as unknown as Record<string, unknown> },
    },
  }
  const alistirmalar = d.alistirmalar.length ? d.alistirmalar : (payload.quiz ? [payload.quiz] : [])
  const kartlar: OzelKart[] = [
    ...alistirmalar.map(veri => ({ tur: 'alistirma' as const, veri })),
    ...((payload.odev_onerisi ?? d.odevOnerisi) ? [{ tur: 'odev_onerisi' as const, veri: (payload.odev_onerisi ?? d.odevOnerisi)! }] : []),
    ...((payload.netlestirme ?? d.netlestirme) ? [{ tur: 'netlestirme' as const, veri: (payload.netlestirme ?? d.netlestirme)! }] : []),
    ...((payload.mode_suggestion ?? d.modOnerisi) ? [{ tur: 'mod_onerisi' as const, veri: (payload.mode_suggestion ?? d.modOnerisi)! }] : []),
    ...(payload.plan_blocks?.length ? [{ tur: 'plan' as const, veri: payload.plan_blocks }] : []),
  ]
  return {
    id: d.yanitId,
    output: { generic: [ana, ...kartlar.map(kartOgesi)] as unknown as GenericItem[] },
    ...(d.adimlar.length ? { message_options: { chain_of_thought: adimlar(d) } } : {}),
  }
}

export function hataYaniti(yanitId: string, mesaj: string): MessageResponse {
  return { id: yanitId, output: { generic: [kartOgesi({ tur: 'hata', veri: { mesaj } })] as unknown as GenericItem[] } }
}
```

- [ ] **Step 7: Geç**

Run: `cd dashboard && node --test tests/atiflar.test.ts tests/olay-eslemesi.test.ts && npx tsc -b`
Expected: PASS, tür hatası yok.

- [ ] **Step 8: Commit**

```bash
git add dashboard/src/asistan/atiflar.ts dashboard/src/asistan/olayEslemesi.ts dashboard/src/types.ts dashboard/tests/atiflar.test.ts dashboard/tests/olay-eslemesi.test.ts
git commit -m "feat(asistan): SSE olaylarını Carbon AI Chat parçalarına çeviren saf eşleme

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Markdown eklentileri — `:::` blokları, KaTeX, taşan bölgeye odak

Spec §1 (`markdownEklentileri.ts`). Bugünkü `renderMarkdown(…, {bicim:'sohbet'})` kuralları: beş kutu (`kavram`, `ornek`, `adimlar`, `sonuc`, `hata`) etiketleriyle; bilinmeyen kutu adının içi düz içerik olarak çizilir (etiketsiz); kapanmayan kutu metnin sonuna kadar sürer; `$$…$$` tek satır ya da `$$` … `$$` çok satır blok formül; `$…$` satır içi; KaTeX hata verirse `<code class="ac-formul__kaynak">` yedeği. Eklenti çıktısı Carbon'un "plugin host" sözleşmesiyle **light DOM'a** konur, bu yüzden bugünkü `utils/markdown.scss` sınıfları (`ac-kutu`, `ac-adimlar`, `ac-formul`) aynen uygulanır.

**Files:**
- Create: `dashboard/src/asistan/markdownEklentileri.ts`
- Create: `dashboard/src/asistan/kaydirmaOdagi.ts`
- Create: `dashboard/src/asistan/markdownKurulumu.ts`
- Modify: `dashboard/package.json` (`markdown-it` doğrudan bağımlılık — `@carbon/ai-chat` zaten getiriyor; sürümü aynı tutulur: `npm i markdown-it@^14.3.0 @types/markdown-it -D` yerine `npm i --save-exact markdown-it@$(node -p "require('markdown-it/package.json').version")` ve `npm i -D @types/markdown-it`)
- Test: `dashboard/tests/markdown-eklentileri.test.ts`

**Interfaces:**
- Produces: `tedyMarkdownEklentisi(md: MarkdownIt, katex?: KatexBenzeri): void` (`markdownEklentileri.ts`); `TEDY_MARKDOWN_EKLENTILERI: MarkdownItPlugin[]` (`markdownKurulumu.ts`, KaTeX'i ve CSS'ini statik yükler); `kaydirmaOdaginiYonet(kok: HTMLElement): () => void` (`kaydirmaOdagi.ts`).

- [ ] **Step 1: Testleri yaz**

`dashboard/tests/markdown-eklentileri.test.ts`:
```ts
import assert from 'node:assert/strict'
import { test } from 'node:test'
import MarkdownIt from 'markdown-it'
import katex from 'katex'
import { tedyMarkdownEklentisi } from '../src/asistan/markdownEklentileri.ts'

const md = () => { const m = new MarkdownIt(); m.use(tedyMarkdownEklentisi, katex); return m }

test('beş kutu etiketiyle, içi markdown', () => {
  const html = md().render(':::kavram\nPay **üstteki** sayıdır.\n:::')
  assert.match(html, /^<div class="ac-kutu ac-kutu--kavram"><span class="ac-kutu__etiket">Kavram<\/span><p>Pay <strong>üstteki<\/strong> sayıdır\.<\/p>\n<\/div>/)
  assert.match(md().render(':::hata\nx\n:::'), /Sık yapılan hata/)
})

test('adımlar kutusu numaralı adım listesi olur', () => {
  const html = md().render(':::adimlar\n1. Paydaları eşitle\n2. Payları topla\n:::')
  assert.match(html, /<ol class="ac-adimlar" aria-label="Adımlar">/)
  assert.match(html, /<li class="ac-adim"><span class="ac-adim__no" aria-hidden="true">2<\/span><div class="ac-adim__govde">Payları topla<\/div><\/li>/)
})

test('bilinmeyen kutu etiketsiz içerik, kapanmayan kutu sona kadar', () => {
  const html = md().render(':::bilinmez\nmetin\n:::')
  assert.ok(!html.includes(':::') && html.includes('<p>metin</p>') && !html.includes('ac-kutu'))
  assert.match(md().render(':::ornek\nyarım'), /ac-kutu--ornek.*yarım/s)
})

test('formüller: satır içi, blok, çok satır, hatalı', () => {
  const r = md().render('Kesir $\\frac{3}{4}$ ve\n\n$$a^2+b^2$$\n\n$$\nx=1\n$$\n\n$\\bozuk{$')
  assert.equal((r.match(/class="katex"/g) ?? []).length, 3)
  assert.match(r, /<div class="ac-formul ac-formul--blok">/)
  assert.match(r, /<code class="ac-formul__kaynak">\\bozuk\{<\/code>/)
})

test('tek dolar ($5 ve $6 gibi para) formül sayılmaz', () => {
  assert.ok(!md().render('Fiyat 5$ ve 6 $ oldu').includes('katex'))
})
```

- [ ] **Step 2: Başarısız olduğunu gör**

Run: `cd dashboard && node --test tests/markdown-eklentileri.test.ts`
Expected: FAIL — modül yok.

- [ ] **Step 3: Eklentiyi yaz**

`dashboard/src/asistan/markdownEklentileri.ts`:
```ts
// Bugünkü sohbet renderer'ının (utils/markdown.tsx, bicim: 'sohbet') kutu ve formül kuralları, markdown-it
// eklentisi olarak. Carbon AI Chat eklenti çıktısını light DOM'a koyar; utils/markdown.scss sınıfları uygulanır.
import type MarkdownIt from 'markdown-it'

type BlokKurali = Parameters<MarkdownIt['block']['ruler']['before']>[2]
type SatirKurali = Parameters<MarkdownIt['inline']['ruler']['before']>[2]
type BlokDurumu = Parameters<BlokKurali>[0]
// Paragrafı kesebilsin: ":::kavram" bir paragrafın hemen altında da kutu açar (eski renderer gibi).
const KESER = { alt: ['paragraph', 'reference', 'blockquote', 'list'] }

export interface KatexBenzeri { renderToString(tex: string, o: Record<string, unknown>): string }

const KUTULAR = { kavram: 'Kavram', ornek: 'Örnek', adimlar: 'Adımlar', sonuc: 'Sonuç', hata: 'Sık yapılan hata' } as const
const ACILIS = /^:::\s*([a-zçğıöşü]+)\s*$/
const KAPANIS = /^:::\s*$/
const KATEX_AYARI = { throwOnError: true, output: 'htmlAndMathml', trust: false, strict: 'ignore', maxSize: 10, maxExpand: 100 }

const kac = (s: string) => s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]!))
const satir = (s: BlokDurumu, n: number) => s.src.slice(s.bMarks[n] + s.tShift[n], s.eMarks[n])

function formulHtml(katex: KatexBenzeri | undefined, tex: string, blok: boolean): string {
  let ic = `<code class="ac-formul__kaynak">${kac(tex)}</code>`
  if (katex) { try { ic = katex.renderToString(tex, { ...KATEX_AYARI, displayMode: blok }) } catch { /* yedek kalır */ } }
  return blok ? `<div class="ac-formul ac-formul--blok">${ic}</div>` : `<span class="ac-formul">${ic}</span>`
}

function adimlarHtml(md: MarkdownIt, icerik: string): string {
  const ogeler = icerik.split('\n').map(s => /^\s*(\d+)[.)]\s+(.+)$/.exec(s))
  if (!ogeler.length || ogeler.some(o => !o)) return md.render(icerik)
  const lis = ogeler.map(o => `<li class="ac-adim"><span class="ac-adim__no" aria-hidden="true">${o![1]}</span><div class="ac-adim__govde">${md.renderInline(o![2])}</div></li>`)
  return `<ol class="ac-adimlar" aria-label="Adımlar">${lis.join('')}</ol>`
}

export function tedyMarkdownEklentisi(md: MarkdownIt, katex?: KatexBenzeri): void {
  const kutu: BlokKurali = (s, bas, son, sessiz) => {
    const m = ACILIS.exec(satir(s, bas).trim())
    if (!m) return false
    if (sessiz) return true
    let n = bas + 1
    while (n < son && !KAPANIS.test(satir(s, n).trim())) n += 1
    const t = s.push('tedy_kutu', 'div', 0)
    t.info = m[1]; t.content = s.getLines(bas + 1, n, s.blkIndent, false).replace(/\n$/, ''); t.block = true
    t.map = [bas, Math.min(n + 1, son)]
    s.line = Math.min(n + 1, son)
    return true
  }
  md.block.ruler.before('fence', 'tedy_kutu', kutu, KESER)
  md.renderer.rules.tedy_kutu = (tokens, i) => {
    const ad = tokens[i].info as keyof typeof KUTULAR
    const icerik = tokens[i].content
    if (!(ad in KUTULAR)) return md.render(icerik)
    if (ad === 'adimlar') return `<div class="ac-kutu--adimlar">${adimlarHtml(md, icerik)}</div>`
    return `<div class="ac-kutu ac-kutu--${ad}"><span class="ac-kutu__etiket">${KUTULAR[ad]}</span>${md.render(icerik)}</div>`
  }

  const blokFormul: BlokKurali = (s, bas, son, sessiz) => {
    const ilk = satir(s, bas).trim()
    const tek = /^\$\$(.+)\$\$$/.exec(ilk)
    if (!tek && ilk !== '$$') return false
    if (sessiz) return true
    let n = bas + 1
    let tex = tek?.[1] ?? ''
    if (!tek) {
      while (n < son && satir(s, n).trim() !== '$$') n += 1
      tex = s.getLines(bas + 1, n, s.blkIndent, false).replace(/\n$/, '')
      n += 1
    }
    const t = s.push('tedy_formul', 'div', 0)
    t.content = tex; t.block = true; t.map = [bas, Math.min(n, son)]
    s.line = Math.min(n, son)
    return true
  }
  md.block.ruler.before('fence', 'tedy_blok_formul', blokFormul, KESER)
  const satirFormul: SatirKurali = (s, sessiz) => {
    if (s.src[s.pos] !== '$' || s.src[s.pos + 1] === '$' || /\s/.test(s.src[s.pos + 1] ?? ' ')) return false
    const kapanis = s.src.indexOf('$', s.pos + 1)
    if (kapanis < 0 || /\s/.test(s.src[kapanis - 1])) return false
    if (!sessiz) { const t = s.push('tedy_formul_satir', 'span', 0); t.content = s.src.slice(s.pos + 1, kapanis) }
    s.pos = kapanis + 1
    return true
  }
  md.inline.ruler.before('escape', 'tedy_satir_formul', satirFormul)
  md.renderer.rules.tedy_formul = (tokens, i) => formulHtml(katex, tokens[i].content, true)
  md.renderer.rules.tedy_formul_satir = (tokens, i) => formulHtml(katex, tokens[i].content, false)
}
```
(“Fiyat 5$ ve 6 $” testi: `5$` açılışı `$` sonrası boşlukla, `6 $` kapanışı yok — kural `false` döner.)

`TEDY_MARKDOWN_EKLENTILERI` sabiti KaTeX'i statik içe aktaran ayrı küçük dosyada durur ki node testi KaTeX CSS'ini yüklemesin — `dashboard/src/asistan/markdownKurulumu.ts`:
```ts
import katex from 'katex'
import 'katex/dist/katex.min.css'
import type { MarkdownItPlugin } from '@carbon/ai-chat'
import { tedyMarkdownEklentisi } from './markdownEklentileri.ts'

/** Carbon'a verilen sabit dizi: her render'da aynı başvuru (paket yeniden kurmasın diye). */
export const TEDY_MARKDOWN_EKLENTILERI: MarkdownItPlugin[] = [[tedyMarkdownEklentisi, katex] as unknown as MarkdownItPlugin]
```

- [ ] **Step 4: Taşan bölge odağı**

`dashboard/src/asistan/kaydirmaOdagi.ts`:
```ts
/** Taşan formül ve tablolar klavyeyle kaydırılabilsin, taşmayanlar sekme sırasına girmesin
 *  (eski Kaydirilabilir bileşeninin kuralı; axe scrollable-region-focusable). Carbon eklenti çıktısını
 *  light DOM'a koyduğu için kökteki MutationObserver bu öğeleri görür. */
const SECICI = '.ac-formul--blok, .ac-md__table-wrap, cds-aichat-table, table'

export function kaydirmaOdaginiYonet(kok: HTMLElement): () => void {
  const ayarla = () => {
    kok.querySelectorAll<HTMLElement>(SECICI).forEach(el => {
      const tasiyor = el.scrollWidth > el.clientWidth + 1
      if (tasiyor && !el.hasAttribute('tabindex')) {
        el.setAttribute('tabindex', '0'); el.setAttribute('role', 'region')
        el.setAttribute('aria-label', el.classList.contains('ac-formul--blok') ? 'Formül' : 'Tablo')
      } else if (!tasiyor && el.getAttribute('tabindex') === '0') {
        el.removeAttribute('tabindex'); el.removeAttribute('role'); el.removeAttribute('aria-label')
      }
    })
  }
  const gozlem = new MutationObserver(() => requestAnimationFrame(ayarla))
  gozlem.observe(kok, { childList: true, subtree: true })
  const boyut = new ResizeObserver(ayarla)
  boyut.observe(kok)
  ayarla()
  return () => { gozlem.disconnect(); boyut.disconnect() }
}
```
(Bu işlevin davranışı Görev 17'deki `asistan-zengin-cevap` e2e testleriyle sınanır.)

- [ ] **Step 5: Geç**

Run: `cd dashboard && node --test tests/markdown-eklentileri.test.ts && npx tsc -b`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add dashboard/src/asistan/markdownEklentileri.ts dashboard/src/asistan/markdownKurulumu.ts dashboard/src/asistan/kaydirmaOdagi.ts dashboard/tests/markdown-eklentileri.test.ts dashboard/package.json dashboard/package-lock.json
git commit -m "feat(asistan): ::: kutuları ve KaTeX için markdown-it eklentileri

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Akış istemcisi — `/stream`, `/chat` yedeği, `/plan`, iptal, okur hatası

**Files:**
- Create: `dashboard/src/asistan/akisIstemcisi.ts`
- Test: `dashboard/tests/akis-istemcisi.test.ts`

**Interfaces:**
- Consumes: `TedyOlayi`, `AkisHatasi` (Görev 7).
- Produces:
  - `sseOku(res: Response, onOlay: (o: TedyOlayi) => void): Promise<void>`
  - `class IstekHatasi extends Error { durum: number }` (constructor `(mesaj: string, durum: number)`)
  - `okurHatasi(e: unknown): string`
  - `soruGonder(govde: Record<string, unknown>, onOlay: (o: TedyOlayi) => void, signal: AbortSignal, f?: typeof fetch): Promise<void>` — akış başarısızsa ve henüz `answer` gelmediyse önce `{ad:'akis_dustu', veri:{yeniId}}`, sonra `/chat` cevabını `{ad:'answer', veri:{payload}}` olarak verir. İptalde `AbortError` fırlatır, yedeğe düşmez.
  - `planGonder(govde: Record<string, unknown>, signal: AbortSignal, f?: typeof fetch): Promise<AssistantResponse>`

- [ ] **Step 1: Testleri yaz**

`dashboard/tests/akis-istemcisi.test.ts`:
```ts
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
```

- [ ] **Step 2: Başarısız olduğunu gör**

Run: `cd dashboard && node --test tests/akis-istemcisi.test.ts` → FAIL (modül yok).

- [ ] **Step 3: Yaz**

`dashboard/src/asistan/akisIstemcisi.ts`:
```ts
import type { AssistantResponse } from '../types'
import { AkisHatasi } from './olayEslemesi.ts'
import type { TedyOlayi } from './olayEslemesi.ts'

export class IstekHatasi extends Error {
  durum: number
  constructor(mesaj: string, durum: number) { super(mesaj); this.durum = durum }
}

const OTURUM = 'Oturumun sona ermiş; sayfayı yenileyip yeniden giriş yap.'
const GENEL = 'Asistan yanıtı alınamadı.'

/** Okura gösterilen cümle: oturum düşmesi ayrı söylenir; sunucunun kendi Türkçe cümlesi korunur;
 *  "HTTP 502", "Failed to fetch" gibi iç metinler okura ulaşmaz (D4). */
export function okurHatasi(e: unknown): string {
  if (e instanceof IstekHatasi) {
    if (e.durum === 401 || e.durum === 403) return OTURUM
    const m = e.message.trim()
    // Sunucunun Türkçe cümlesi korunur; "session_required" gibi tek kelime kodlar ve "HTTP 502" korunmaz.
    if (!/^HTTP \d+/.test(m) && /\s|[çğıöşüÇĞİÖŞÜ]/.test(m)) return m
  }
  return GENEL
}

export async function sseOku(res: Response, onOlay: (o: TedyOlayi) => void): Promise<void> {
  const okuyucu = res.body?.getReader()
  if (!okuyucu) throw new AkisHatasi('akış gövdesi yok')
  const cozucu = new TextDecoder()
  let tampon = ''
  for (;;) {
    const { done, value } = await okuyucu.read()
    if (done) break
    tampon += cozucu.decode(value, { stream: true })
    const cerceveler = tampon.split('\n\n')
    tampon = cerceveler.pop() ?? ''
    for (const c of cerceveler) {
      let ad = 'message'
      let veri = '{}'
      for (const s of c.split('\n')) {
        if (s.startsWith('event: ')) ad = s.slice(7).trim()
        else if (s.startsWith('data: ')) veri = s.slice(6)
      }
      try { onOlay({ ad, veri: JSON.parse(veri) }) } catch (e) { if (e instanceof AkisHatasi) throw e }
    }
  }
}

async function jsonIstek(url: string, govde: unknown, signal: AbortSignal, f: typeof fetch): Promise<AssistantResponse> {
  const res = await f(url, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(govde), signal })
  let veri: Record<string, unknown> = {}
  try { veri = await res.json() } catch { veri = {} }
  if (!res.ok || 'error' in veri) throw new IstekHatasi(String(veri.error ?? `HTTP ${res.status}`), res.status)
  return veri as unknown as AssistantResponse
}

const iptalMi = (e: unknown) => (e as { name?: string })?.name === 'AbortError'

export async function soruGonder(govde: Record<string, unknown>, onOlay: (o: TedyOlayi) => void,
  signal: AbortSignal, f: typeof fetch = fetch): Promise<void> {
  let cevaplandi = false
  try {
    const res = await f('/api/assistant/stream', { method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(govde), signal })
    if (!res.ok || !res.body) throw new IstekHatasi(`HTTP ${res.status}`, res.status)
    await sseOku(res, o => {
      if (cevaplandi) return
      if (o.ad === 'error') throw new AkisHatasi(String(o.veri.error ?? 'akış hatası'))
      if (o.ad === 'answer') cevaplandi = true
      onOlay(o)
    })
    if (!cevaplandi) throw new AkisHatasi('akış yanıtsız kapandı')
  } catch (e) {
    if (cevaplandi) return
    if (iptalMi(e) || signal.aborted) throw e
    // Ara katman SSE'yi tamponluyor, eski işçi ya da akış yarıda koptu: okur cevabını yine alır.
    console.warn('akış başarısız, klasik uca düşülüyor:', e)
    onOlay({ ad: 'akis_dustu', veri: { yeniId: crypto.randomUUID() } })
    const payload = await jsonIstek('/api/assistant/chat', govde, signal, f)
    onOlay({ ad: 'answer', veri: { payload } })
  }
}

export function planGonder(govde: Record<string, unknown>, signal: AbortSignal, f: typeof fetch = fetch) {
  return jsonIstek('/api/assistant/plan', govde, signal, f)
}
```


- [ ] **Step 4: Geç**

Run: `cd dashboard && node --test tests/akis-istemcisi.test.ts && npx tsc -b` → PASS.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/asistan/akisIstemcisi.ts dashboard/tests/akis-istemcisi.test.ts
git commit -m "feat(asistan): akış istemcisi, /chat yedeği ve okura Türkçe hata

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Türkçe dil paketi ve `PublicConfig` üretimi

**Files:**
- Create: `dashboard/src/asistan/dilPaketi.ts` (içeriği **Ek A**, birebir)
- Create: `dashboard/src/asistan/tedyChatConfig.ts`
- Create: `dashboard/tests/dil-paketi.test.ts`
- Create: `dashboard/scripts/carbon-dil-anahtarlari.mjs`

**Interfaces:**
- Produces:
  - `TURKCE: LanguagePack`
  - `interface ConfigGirdisi { okur: 'ogrenci' | 'aile'; karsilama: string; hizliSorular: { metin: string; plan?: boolean }[]; saltOkunur: boolean; altBaslik: string; gonder: PublicConfigMessaging['customSendMessage']; gecmisYukle?: PublicConfigMessaging['customLoadHistory'] }`
  - `tedyChatConfig(g: ConfigGirdisi): Omit<PublicConfig, 'markdown'>`

- [ ] **Step 1: Anahtar dökümü betiği ve test**

`dashboard/scripts/carbon-dil-anahtarlari.mjs`:
```js
// Kurulu @carbon/ai-chat'in enLanguagePack anahtarlarını yazdırır (dil paketi testi bunu kullanır).
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
const yol = createRequire(import.meta.url).resolve('@carbon/ai-chat/package.json').replace('package.json', 'dist/es/chat.languageUtils.js')
const s = readFileSync(yol, 'utf8')
const blok = s.slice(s.indexOf('var enLanguagePackData = {'), s.indexOf('};', s.indexOf('var enLanguagePackData = {')))
console.log(JSON.stringify([...blok.matchAll(/^\s+([A-Za-z0-9_]+),?$/gm)].map(m => m[1])))
```

`dashboard/tests/dil-paketi.test.ts`:
```ts
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { execFileSync } from 'node:child_process'
import { TURKCE } from '../src/asistan/dilPaketi.ts'

test('Carbon dil paketinin her anahtarı Türkçe', () => {
  const anahtarlar: string[] = JSON.parse(execFileSync('node', ['scripts/carbon-dil-anahtarlari.mjs'], { encoding: 'utf8' }))
  assert.ok(anahtarlar.length >= 263)
  const eksik = anahtarlar.filter(k => !(k in TURKCE))
  assert.deepEqual(eksik, [])
  const ingilizce = Object.entries(TURKCE).filter(([, v]) => /\b(the|you|your|Close|Open|Send|Cancel)\b/.test(v as string))
  assert.deepEqual(ingilizce, [])
})
```

- [ ] **Step 2: `dilPaketi.ts`'i Ek A'dan oluştur, testi koş**

Run: `cd dashboard && node --test tests/dil-paketi.test.ts` → PASS.

- [ ] **Step 3: Config üreticisi**

`dashboard/src/asistan/tedyChatConfig.ts`:
```ts
import type { PublicConfig, PublicConfigMessaging } from '@carbon/ai-chat'
import { TURKCE } from './dilPaketi.ts'

export interface ConfigGirdisi {
  okur: 'ogrenci' | 'aile'
  karsilama: string
  hizliSorular: { metin: string; plan?: boolean }[]
  saltOkunur: boolean
  altBaslik: string
  gonder: PublicConfigMessaging['customSendMessage']
  gecmisYukle?: PublicConfigMessaging['customLoadHistory']
}

/** Sayfa ve başlatıcı aynı yapılandırmayı kullanır; farkları bileşen (ChatCustomElement / ChatContainer) yapar. */
export function tedyChatConfig(g: ConfigGirdisi): Omit<PublicConfig, 'markdown'> {
  return {
    locale: 'tr',
    strings: {
      ...TURKCE,
      input_placeholder: g.okur === 'ogrenci' ? 'Bir soru sor veya çalışma planı iste...' : 'Bir soru sorun veya çalışma planı isteyin...',
    },
    aiEnabled: true,
    assistantName: 'TEDY Asistan',
    header: { title: 'TEDY Asistan', name: g.altBaslik, showAiLabel: true, showRestartButton: !g.saltOkunur },
    homescreen: {
      isOn: true, greeting: g.karsilama, disableReturn: false,
      starters: { isOn: !g.saltOkunur, buttons: g.hizliSorular.map(s => ({ label: s.metin })) },
    },
    history: { isOn: true, showMobileMenu: true },
    upload: { isOn: false },   // ekler bugünkü çiplerle giriş üstü yuvada (Görev 16)
    layout: { showFrame: false, hasContentMaxWidth: true },
    messaging: { customSendMessage: g.gonder, ...(g.gecmisYukle ? { customLoadHistory: g.gecmisYukle } : {}),
      messageTimeoutSecs: 180, showStopButtonImmediately: true },
    isReadonly: g.saltOkunur,
    persistFeedback: true,
    injectCarbonTheme: 'g10' as PublicConfig['injectCarbonTheme'],   // panoyla aynı tema (DASHBOARD_THEME)
    keyboardShortcuts: { messageFocusToggle: { isOn: true } },
  }
}
```

- [ ] **Step 4: Tür denetimi ve commit**

Run: `cd dashboard && npx tsc -b && node --test tests/dil-paketi.test.ts`

```bash
git add dashboard/src/asistan/dilPaketi.ts dashboard/src/asistan/tedyChatConfig.ts dashboard/tests/dil-paketi.test.ts dashboard/scripts/carbon-dil-anahtarlari.mjs
git commit -m "feat(asistan): Carbon AI Chat Türkçe dil paketi ve yapılandırma

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 11: Sohbet çekirdeği — depo, gönderme, `/asistan` sayfası, bayrak, temel e2e

Bu görevden sonra yeni `/asistan` (bayrak açıkken) soru alır, akışı gösterir, `/chat` yedeğine düşer, durdurulur, hata kartında Tekrar dene sunar. Kartlar, kaynak paneli, altbilgi, geçmiş, ekler sonraki görevlerde gelir.

Render işlevlerinin (Carbon'un `renderUserDefinedResponse` vb.) React bağlamına erişimi portal davranışına bağlı olduğundan, paylaşılan durum bağlam yerine küçük bir dış depoda (`useSyncExternalStore`) tutulur.

**Files:**
- Create: `dashboard/src/asistan/asistanDeposu.ts`
- Create: `dashboard/src/asistan/gecmis.ts` (kayıtlı mesaj → Carbon `HistoryItem`)
- Create: `dashboard/src/asistan/useAsistanSohbeti.tsx` (config + gönderme + render işlevleri; sayfa ve başlatıcı ortak)
- Create: `dashboard/src/asistan/AsistanSayfasi.tsx`, `dashboard/src/asistan/AsistanSayfasi.scss`
- Modify: `dashboard/src/App.tsx` (bayrakla `AssistantChat` ↔ tembel `AsistanSayfasi`)
- Modify: `dashboard/src/hooks/useSohbetler.ts` (`KayitliMesaj.zaman?: string`, `geri_bildirim?: …`)
- Create: `dashboard/tests/gecmis.test.ts`
- Create: `dashboard/tests/e2e/_asistan-carbon.ts`
- Create: `dashboard/tests/e2e/carbon-asistan-cekirdek.spec.ts`

**Interfaces:**
- Consumes: Görev 7 (`akisBaslat`, `olayIsle`, `sonYanit`, `hataYaniti`), Görev 9 (`soruGonder`, `planGonder`, `okurHatasi`), Görev 10 (`tedyChatConfig`), Görev 8 (`TEDY_MARKDOWN_EKLENTILERI`, `kaydirmaOdaginiYonet`).
- Produces:
  - `asistanDeposu`: `al(): AsistanDurumu`, `ayarla(p: Partial<AsistanDurumu>): void`, `abone(f): () => void`, `useAsistanDurumu<T>(sec: (d) => T): T`
  - `interface AsistanDurumu { okur; email?; ogretmenId; saltOkunur; sohbetId?; odevKey; cipler: Cip[]; sayfa: SayfaIstegi | null; sonrakiIstek: { deep?: boolean; transient?: boolean; plan?: boolean }; dokum: {role: 'user'|'assistant'; content: string}[]; bekleyen: { govde: Record<string, unknown>; plan: boolean } | null; yukleniyor: boolean; ekGoruntuleri: Record<string, Yukleme[]>; acikAtif: { atiflar: AssistantCitation[]; etkin: string | null } | null; sonYanitId?: string; sonModel?: string }`
  - `interface SayfaIstegi { ad: string; oge?: { tur: string; id: string }; etiket: string; ogeEtiketi?: string }`
  - `gecmisOgeleri(mesajlar: KayitliMesaj[], sec: SonYanitSecenekleri): HistoryItem[]`
  - `useAsistanSohbeti(bicim: 'sayfa' | 'panel', sayfa?: string | null): { props: ChatContainerProps; instance: React.RefObject<ChatInstance | null>; ogretmen; sohbet; ses }` (`sayfa` parametresi Görev 18'de kullanılır; bu görevde yok sayılır)
  - `tekrarDene(inst: ChatInstance, hataMesajiId: string): Promise<void>`, `soruyuYeniden(inst: ChatInstance, metin: string, ek: { deep?: boolean; transient?: boolean; plan?: boolean }): Promise<void>` (useAsistanSohbeti modülünden dışa aktarılır)
  - e2e yardımcıları: `sse`, `PAYLOAD`, `cevapla`, `asistanAc`, `soruAlani`, `sor`, `gonderDugmesi`

- [ ] **Step 1: Geçmiş dönüştürücüsü testi**

`dashboard/tests/gecmis.test.ts`:
```ts
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { gecmisOgeleri } from '../src/asistan/gecmis.ts'
import type { KayitliMesaj } from '../src/hooks/useSohbetler.ts'

const M = (p: Partial<KayitliMesaj>): KayitliMesaj => ({ id: 'm', rol: 'user', icerik: '', atiflar_json: '[]', ekler_json: '[]', ...p })

test('kullanıcı ve asistan sırası, zaman, geri bildirim durumu', () => {
  const ogeler = gecmisOgeleri([
    M({ id: 'u1', rol: 'user', icerik: 'Kesir nedir?', zaman: '2026-10-08T09:00:00Z' }),
    M({ id: 'a'.repeat(32), rol: 'assistant', icerik: 'Parça [S1].', zaman: '2026-10-08T09:00:05Z',
      atiflar_json: JSON.stringify([{ id: 'S1', kind: 'mufredat', label: 'Mat', locator: {}, snippet: 's', confidence: 1 }]),
      geri_bildirim: { deger: 'olumsuz', kategori: 'Anlamadım', metin: 'hızlı' } }),
  ], { geriBildirim: true, ogrenci: true })
  assert.equal(ogeler.length, 2)
  assert.deepEqual((ogeler[0].message as Record<string, any>).input, { text: 'Kesir nedir?' })
  assert.equal(ogeler[0].time, '2026-10-08T09:00:00Z')
  const yanit = ogeler[1].message as Record<string, any>
  assert.equal(yanit.output.generic[0].response_type, 'conversational_search')
  assert.deepEqual(yanit.history.feedback['a'.repeat(32)], { is_positive: false, text: 'hızlı', categories: ['Anlamadım'] })
})

test('salt okunur sohbette geri bildirim kapalı; kayıtlı kartlar geri gelir', () => {
  const [o] = gecmisOgeleri([M({ id: 'b'.repeat(32), rol: 'assistant', icerik: 'x',
    netlestirme: { soru: 'Hangisi?', secenekler: ['a', 'b'] } })], { geriBildirim: false, ogrenci: false })
  const g = (o.message as Record<string, any>).output.generic
  assert.equal(g[0].message_item_options.feedback, undefined)
  assert.equal(g[1].user_defined.tedy.tur, 'netlestirme')
})
```

- [ ] **Step 2: `gecmis.ts`**

`dashboard/src/hooks/useSohbetler.ts` `KayitliMesaj` içine:
```ts
  zaman?: string
  geri_bildirim?: { deger: 'olumlu' | 'olumsuz'; kategori: string | null; metin: string } | null
```

`dashboard/src/asistan/gecmis.ts`:
```ts
import type { HistoryItem, MessageResponse } from '@carbon/ai-chat'
import type { AssistantCitation, AssistantResponse } from '../types'
import type { KayitliMesaj } from '../hooks/useSohbetler'
import { akisBaslat, sonYanit } from './olayEslemesi.ts'
import type { SonYanitSecenekleri } from './olayEslemesi.ts'

/** B3 kaydı → Carbon geçmişi. Kayıtlı kartlar (alıştırma, netleştirme, ödev önerisi) geri gelir;
 *  araç adımları kaydedilmediği için eski cevapta adım listesi yoktur (spec §5.1). */
export function gecmisOgeleri(mesajlar: KayitliMesaj[], sec: SonYanitSecenekleri): HistoryItem[] {
  return mesajlar.map(m => {
    const time = m.zaman ?? new Date(0).toISOString()
    if (m.rol === 'user') return { message: { id: m.id, input: { text: m.icerik } }, time }
    const payload: AssistantResponse = {
      answer: m.icerik, citations: JSON.parse(m.atiflar_json || '[]') as AssistantCitation[], safety_flags: [],
      plan_blocks: [], intent: 'qa', session_id: '', meta: { model: '' }, mesaj_id: m.id,
      quiz: m.alistirma?.[0] ?? null, netlestirme: m.netlestirme ?? null, odev_onerisi: m.odev_onerisi ?? null,
    }
    const d = { ...akisBaslat(m.id), alistirmalar: m.alistirma ?? [] }
    const yanit: MessageResponse = sonYanit(d, payload, sec)
    const gb = m.geri_bildirim
    if (gb && sec.geriBildirim) {
      yanit.history = { feedback: { [m.id]: { is_positive: gb.deger === 'olumlu',
        ...(gb.metin ? { text: gb.metin } : {}), ...(gb.kategori ? { categories: [gb.kategori] } : {}) } } }
    }
    return { message: yanit, time }
  })
}
```

Run: `cd dashboard && node --test tests/gecmis.test.ts` → PASS.

- [ ] **Step 3: Paylaşılan depo**

`dashboard/src/asistan/asistanDeposu.ts`:
```ts
import { useSyncExternalStore } from 'react'
import type { AssistantCitation } from '../types'
import type { Yukleme } from '../components/YuklenenEk'

export interface Cip { yerel: string; ad: string; tur?: string; id?: string; hata?: string; yukleniyor?: boolean; baglaniyor?: boolean; baglandi?: boolean }
export interface SayfaIstegi { ad: string; oge?: { tur: string; id: string }; etiket: string; ogeEtiketi?: string }
export interface AsistanDurumu {
  okur: 'ogrenci' | 'aile'; email?: string; ogretmenId: string; saltOkunur: boolean; sohbetId?: string
  odevKey: string; cipler: Cip[]; sayfa: SayfaIstegi | null
  sonrakiIstek: { deep?: boolean; transient?: boolean; plan?: boolean }
  dokum: { role: 'user' | 'assistant'; content: string }[]
  bekleyen: { govde: Record<string, unknown>; plan: boolean } | null
  yukleniyor: boolean; ekGoruntuleri: Record<string, Yukleme[]>
  acikAtif: { atiflar: AssistantCitation[]; etkin: string | null } | null
  /** Son tamamlanan asistan yanıtının Carbon kimliği: netleştirme yalnız son cevapta etkin. */
  sonYanitId?: string
  /** AI açıklamasındaki "Son yanıtı … yazdı" için. */
  sonModel?: string
  /** Tek paylaşılan sesli okuyucu: bir cevabı okumak öncekini durdurur, düğme etiketleri birlikte değişir. */
  ses: { var: boolean; okunan: string | null; oku: (id: string, metin: string) => void } | null
}

const BASLANGIC: AsistanDurumu = { okur: 'aile', ogretmenId: 'genel', saltOkunur: false, odevKey: '', cipler: [], sayfa: null,
  sonrakiIstek: {}, dokum: [], bekleyen: null, yukleniyor: false, ekGoruntuleri: {}, acikAtif: null, ses: null }

let durum = BASLANGIC
const dinleyiciler = new Set<() => void>()

export const asistanDeposu = {
  al: () => durum,
  ayarla(p: Partial<AsistanDurumu>) { durum = { ...durum, ...p }; dinleyiciler.forEach(f => f()) },
  sifirla() { durum = BASLANGIC; dinleyiciler.forEach(f => f()) },
  abone(f: () => void) { dinleyiciler.add(f); return () => { dinleyiciler.delete(f) } },
}

export function useAsistanDurumu<T>(sec: (d: AsistanDurumu) => T): T {
  return useSyncExternalStore(asistanDeposu.abone, () => sec(asistanDeposu.al()))
}
```
(`useSyncExternalStore` seçiciyi her çağrıda yeni nesne döndürmeyecek şekilde kullanın: seçici yalnız ilkel ya da depodaki aynı başvuruyu döndürür.)

- [ ] **Step 4: Ortak sohbet kancası**

`dashboard/src/asistan/useAsistanSohbeti.tsx`:
```tsx
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef } from 'react'
import type { ChatContainerProps, ChatInstance, CustomSendMessageOptions, MessageRequest, StreamChunk } from '@carbon/ai-chat'
import { useSession } from '../contexts/session'
import { GENEL, useOgretmen } from '../hooks/useOgretmen'
import { useSohbetler } from '../hooks/useSohbetler'
import { asistanDeposu } from './asistanDeposu.ts'
import { akisBaslat, hataYaniti, olayIsle, sonYanit } from './olayEslemesi.ts'
import type { SonYanitSecenekleri } from './olayEslemesi.ts'
import { okurHatasi, planGonder, soruGonder } from './akisIstemcisi.ts'
import { tedyChatConfig } from './tedyChatConfig.ts'
import { TEDY_MARKDOWN_EKLENTILERI } from './markdownKurulumu.ts'
import { VOICE } from './ses.ts'
import { useSes } from '../hooks/useSes'

function secenekler(): SonYanitSecenekleri {
  const d = asistanDeposu.al()
  return { geriBildirim: !d.saltOkunur, ogrenci: d.okur === 'ogrenci' }
}

/** Bir isteği çalıştırır ve Carbon'a parça parça verir. Parçalar sırayla eklenir (addMessageChunk asenkron). */
async function calistir(inst: ChatInstance, govde: Record<string, unknown>, plan: boolean, signal: AbortSignal) {
  asistanDeposu.ayarla({ bekleyen: { govde, plan }, yukleniyor: true })
  let d = akisBaslat(crypto.randomUUID())
  let zincir: Promise<unknown> = Promise.resolve()
  const sira = (f: () => Promise<unknown>) => { zincir = zincir.then(f); return zincir }
  try {
    if (plan) {
      const p = await planGonder(govde, signal)
      await inst.messaging.addMessageChunk({ final_response: sonYanit(d, p, secenekler()) } as StreamChunk)
      asistanDeposu.ayarla({ sonYanitId: d.yanitId, sonModel: p.meta?.model })
    } else {
      await soruGonder(govde, o => {
        const r = olayIsle(d, o, secenekler())
        d = r.durum
        if (r.kaldir) sira(() => inst.messaging.removeMessages(r.kaldir!))
        for (const p of r.parcalar) sira(() => inst.messaging.addMessageChunk(p))
        if (o.ad === 'answer') {
          const payload = o.veri.payload as { answer?: string; meta?: { model?: string } }
          const dk = asistanDeposu.al()
          asistanDeposu.ayarla({ dokum: [...dk.dokum, { role: 'assistant', content: payload.answer ?? '' }],
            sonYanitId: d.yanitId, sonModel: payload.meta?.model })
        }
      }, signal)
      await zincir
    }
    asistanDeposu.ayarla({ bekleyen: null })
  } catch (e) {
    await zincir.catch(() => {})
    if ((e as { name?: string })?.name === 'AbortError' || signal.aborted) return
    await inst.messaging.addMessage(hataYaniti(crypto.randomUUID(), okurHatasi(e)))
  } finally {
    asistanDeposu.ayarla({ yukleniyor: false })
  }
}

export async function tekrarDene(inst: ChatInstance, hataMesajiId: string) {
  const b = asistanDeposu.al().bekleyen
  if (!b) return
  await inst.messaging.removeMessages([hataMesajiId])
  await calistir(inst, b.govde, b.plan, new AbortController().signal)
}

export async function soruyuYeniden(inst: ChatInstance, metin: string, ek: { deep?: boolean; transient?: boolean; plan?: boolean }) {
  asistanDeposu.ayarla({ sonrakiIstek: ek })
  await inst.send(metin)
}

export function useAsistanSohbeti(bicim: 'sayfa' | 'panel', _sayfa?: string | null) {
  const user = useSession()
  const ogrenci = user?.student === true
  const okur = ogrenci ? 'ogrenci' : 'aile'
  const ogretmen = useOgretmen(user?.email)
  const sohbet = useSohbetler(user?.email, ogrenci)
  const instance = useRef<ChatInstance | null>(null)
  const sohbetRef = useRef(sohbet)
  sohbetRef.current = sohbet

  const secili = ogretmen.secili
  const karsilama = secili ? secili.karsilama[okur] : VOICE[okur].welcome
  const hizliSorular = secili ? secili.hizli_sorular[okur].map(metin => ({ metin }))
    : VOICE[okur].prompts.map(p => ({ metin: p.text, plan: p.mode === 'plan' }))

  // Render sırasında değil: depo dinleyicileri başka bileşenlerdir.
  useLayoutEffect(() => {
    asistanDeposu.ayarla({ okur, email: user?.email, ogretmenId: ogretmen.id ?? GENEL,
      saltOkunur: sohbet.secili?.salt === true, sohbetId: sohbet.secili?.id })
  }, [okur, user?.email, ogretmen.id, sohbet.secili?.salt, sohbet.secili?.id])

  // Taslak Carbon'un giriş alanındadır; ses kancası onu ihtiyaç anında okur ve yazar.
  const ses = useSes(user?.email, () => instance.current?.getState().input.rawValue ?? '',
    metin => instance.current?.input.updateRawValue(() => metin), () => { instance.current?.requestFocus() },
    sohbet.secili?.salt === true)
  useEffect(() => {
    asistanDeposu.ayarla({ ses: { var: !!ses.ses, okunan: ses.okunan, oku: ses.oku } })
  }, [ses.ses, ses.okunan, ses.oku])

  const gonder = useCallback(async (istek: MessageRequest, sec: CustomSendMessageOptions, inst: ChatInstance) => {
    const metin = String((istek.input as { text?: string }).text ?? '').trim()
    const d = asistanDeposu.al()
    if (!metin || d.saltOkunur) return
    const ek = d.sonrakiIstek
    const plan = !!ek.plan || hizliSorular.some(s => s.plan && s.metin === metin)
    const kaydet = !plan && !ek.deep && !ek.transient
    let sohbetId = kaydet ? d.sohbetId : undefined
    if (kaydet && !sohbetId) {
      try { sohbetId = await sohbetRef.current.yeni(d.ogretmenId) } catch {
        await inst.messaging.addMessage(hataYaniti(crypto.randomUUID(), 'Sohbet kaydedilemedi.')); return
      }
    }
    const ekler = !ek.deep && !ek.transient && !plan ? d.cipler.flatMap(c => c.id ? [c.id] : []) : []
    const kullanici = { role: 'user' as const, content: metin, ...(ekler.length ? { ekler } : {}) }
    const dokum = [...d.dokum, { role: 'user' as const, content: metin }]
    const govde: Record<string, unknown> = {
      session_id: 'dashboard-default', context_filters: {},
      messages: sohbetId ? [kullanici] : dokum, ogretmen: d.ogretmenId,
      ...(sohbetId ? { sohbet_id: sohbetId, request_id: crypto.randomUUID() } : {}),
      ...(d.odevKey ? { odev_anahtari: d.odevKey } : {}),
      ...(ek.deep ? { force_deep: true } : {}),
      ...(d.sayfa ? { sayfa: { ad: d.sayfa.ad, ...(d.sayfa.oge ? { oge: d.sayfa.oge } : {}) } } : {}),
    }
    const goruntu = d.cipler.flatMap(c => c.id ? [{ id: c.id, ad: c.ad, tur: c.tur ?? 'bilinmiyor' }] : [])
    asistanDeposu.ayarla({ sonrakiIstek: {}, dokum, sayfa: null,
      ...(ekler.length ? { cipler: [], ekGoruntuleri: { ...d.ekGoruntuleri, [istek.id ?? '']: goruntu } } : {}) })
    await calistir(inst, govde, plan, sec.signal)
    void sohbetRef.current.yenile()
  }, [hizliSorular])

  const config = useMemo(() => tedyChatConfig({
    okur, karsilama, hizliSorular, saltOkunur: sohbet.secili?.salt === true,
    altBaslik: secili ? `${secili.ogretmen_adi} — konuyu adım adım anlatır` : 'Kaynaklı soru-cevap ve kişisel çalışma planı',
    gonder,
  }), [okur, karsilama, hizliSorular, sohbet.secili?.salt, secili, gonder])

  const props: ChatContainerProps = {
    ...config,
    markdown: { markdownItPlugins: TEDY_MARKDOWN_EKLENTILERI },
    onBeforeRender: inst => { instance.current = inst },
  }
  return { props, instance, ogretmen, sohbet, bicim, ses }
}
```

`dashboard/src/hooks/useSes.ts` — taslak bir işlev de olabilsin (geriye uyumlu, eski bileşen değişmez): imzada `draft: string | (() => string)` ve `basla()` içinde
```ts
    taban.current = typeof draft === 'function' ? draft() : draft
```

`dashboard/src/asistan/ses.ts` — eski bileşendeki `VOICE` metinlerini **değiştirmeden** taşı (yalnız ikonsuz): `export const VOICE = { ogrenci: { welcome, prompts: [{text, mode}], sources, caution, ogretmenHata }, aile: {…} }` — metinler `AssistantChat.tsx:79-104`'tekiyle birebir aynı.

- [ ] **Step 5: Sayfa bileşeni ve bayrak**

`dashboard/src/asistan/AsistanSayfasi.tsx`:
```tsx
import './AsistanSayfasi.scss'
import { useEffect, useRef } from 'react'
import { ChatCustomElement } from '@carbon/ai-chat'
import OgretmenSecici from '../components/OgretmenSecici'
import { subjectClass } from '../utils/subject'
import { useAsistanSohbeti } from './useAsistanSohbeti.tsx'
import { kaydirmaOdaginiYonet } from './kaydirmaOdagi.ts'
import { VOICE } from './ses.ts'
import { useAsistanDurumu } from './asistanDeposu.ts'

export default function AsistanSayfasi() {
  const { props, ogretmen } = useAsistanSohbeti('sayfa')
  const kok = useRef<HTMLElement>(null)
  useEffect(() => (kok.current ? kaydirmaOdaginiYonet(kok.current) : undefined), [])
  const secili = ogretmen.secili
  const okur = useAsistanDurumu(d => d.okur)
  return (
    <section ref={kok} className={['asistan', secili && subjectClass(null, secili.renk_ailesi)].filter(Boolean).join(' ')}
      data-ogretmen={ogretmen.id}>
      <OgretmenSecici liste={ogretmen.liste} secili={ogretmen.id} onSec={id => ogretmen.sec(id)}
        hata={ogretmen.hata ? VOICE[okur].ogretmenHata : null} />
      {okur === 'ogrenci' && <p className="asistan__aile-notu">Sohbetlerini ailen de görebilir.</p>}
      <ChatCustomElement className="asistan__sohbet" {...props} />
    </section>
  )
}
```
(Öğretmen seçimi sohbet varken `sohbet.degistir(id, {ogretmen})` çağırır — Görev 15'te `ogretmenSec` buraya bağlanır; bu görevde yalnız `ogretmen.sec`.)

`dashboard/src/asistan/AsistanSayfasi.scss`:
```scss
@use '@carbon/react/scss/spacing';

.asistan {
  display: flex;
  flex-direction: column;
  gap: spacing.$spacing-05;
  // Sayfa sütununu doldurur; pencere değil sohbet kendi içinde kayar (tasarim-denetimi).
  block-size: calc(100dvh - 12rem);
  min-block-size: 32rem;
}

.asistan__sohbet {
  flex: 1;
  min-block-size: 0;
  inline-size: 100%;
}

.asistan__aile-notu { margin: 0; }
```

`dashboard/src/App.tsx`:
```tsx
import { lazy, Suspense } from 'react'
import { CARBON_AI_ACIK } from './asistan/bayrak'
const AsistanSayfasi = lazy(() => import('./asistan/AsistanSayfasi'))
function AsistanGirisi() {
  return <Suspense fallback={<p className="app-shell-loading__text">Asistan yükleniyor…</p>}><AsistanSayfasi /></Suspense>
}
```
ve `COMPONENTS` içinde `AssistantChat: CARBON_AI_ACIK ? AsistanGirisi : AssistantChat`.

- [ ] **Step 6: e2e yardımcıları ve çekirdek testler**

`dashboard/tests/e2e/_asistan-carbon.ts`:
```ts
import { expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { mockSohbetler } from './_audit-fixtures'

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
export const soruAlani = (page: Page) => page.getByRole('textbox', { name: 'Sorunu yaz' })
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
```

`dashboard/tests/e2e/carbon-asistan-cekirdek.spec.ts` — eski `assistant-chat.spec.ts`'in akış davranışlarını yeni arayüzde sabitler:
```ts
import { test, expect } from '@playwright/test'
import { PAYLOAD, asistanAc, cevapla, sor, sse, soruAlani } from './_asistan-carbon'

test('akış tüketilir: araç adımı görünür, cevap gelir, /chat çağrılmaz', async ({ page }) => {
  const istekler = await cevapla(page, PAYLOAD({ answer: 'Kesir bir bütünün parçasıdır.' }),
    [['tool_start', { name: 'kazanim_ara' }], ['tool_end', { name: 'kazanim_ara', ok: true, ozet: 'M.7.1.1' }]])
  let klasik = 0
  page.on('request', r => { if (r.url().endsWith('/api/assistant/chat')) klasik += 1 })
  await asistanAc(page)
  await sor(page, 'Kesir nedir?')
  await expect(page.getByText('Kesir bir bütünün parçasıdır.')).toBeVisible()
  await expect(page.getByText('MEB kazanımları aranıyor')).toBeVisible()
  expect(klasik).toBe(0)
  expect(istekler[0]).toMatchObject({ ogretmen: 'genel' })
})

test('cevapsız kapanan akış /chat yedeğine düşer, yarım taslak kalmaz', async ({ page }) => {
  await page.route('**/api/assistant/stream', r => r.fulfill({ status: 200, contentType: 'text/event-stream',
    body: sse(['answer_delta', { text: 'YARIM TASLAK' }]) }))
  await page.route('**/api/assistant/chat', r => r.fulfill({ json: PAYLOAD({ answer: 'Yedekten gelen cevap.' }) }))
  await asistanAc(page)
  await sor(page, 'Soru')
  await expect(page.getByText('Yedekten gelen cevap.')).toBeVisible()
  await expect(page.getByText('YARIM TASLAK')).toHaveCount(0)
})

test('answer_reset sonrası ön metin cevap sanılmaz; denetimli son metin taslağın yerine geçer', async ({ page }) => {
  await cevapla(page, PAYLOAD({ answer: 'Denetlenmiş son metin.' }),
    [['answer_delta', { text: 'Önce müfredata bakayım.' }], ['answer_reset', {}], ['answer_delta', { text: 'Taslak metin' }]])
  await asistanAc(page)
  await sor(page, 'Soru')
  await expect(page.getByText('Denetlenmiş son metin.')).toBeVisible()
  await expect(page.getByText('Önce müfredata bakayım.')).toHaveCount(0)
  await expect(page.getByText('Taslak metin')).toHaveCount(0)
})

test('iki uç da 401: okura oturum cümlesi ve Tekrar dene; tekrar aynı gövdeyi yollar', async ({ page }) => {
  let n = 0
  const govdeler: unknown[] = []
  await page.route('**/api/assistant/stream', r => r.fulfill({ status: 401, json: { error: 'session_required' } }))
  await page.route('**/api/assistant/chat', async r => {
    govdeler.push(r.request().postDataJSON()); n += 1
    await r.fulfill(n === 1 ? { status: 401, json: { error: 'session_required' } } : { json: PAYLOAD({ answer: 'İkinci denemede geldi.' }) })
  })
  await asistanAc(page)
  await sor(page, 'Soru')
  await expect(page.getByText('Oturumun sona ermiş; sayfayı yenileyip yeniden giriş yap.')).toBeVisible()
  await expect(page.getByText(/HTTP 401|session_required/)).toHaveCount(0)
  await page.getByRole('button', { name: 'Tekrar dene' }).click()
  await expect(page.getByText('İkinci denemede geldi.')).toBeVisible()
  expect(govdeler[1]).toEqual(govdeler[0])
})

test('durdur isteği keser, hata kartı çıkmaz', async ({ page }) => {
  await page.route('**/api/assistant/stream', () => { /* hiç yanıtlanmaz */ })
  await page.route('**/api/assistant/chat', () => { /* hiç yanıtlanmaz */ })
  await asistanAc(page)
  await sor(page, 'Uzun soru')
  await page.getByRole('button', { name: 'Yanıtı durdur' }).click()
  await expect(page.getByText('Asistan yanıtı alınamadı.')).toHaveCount(0)
  await expect(soruAlani(page)).toBeEditable()
})

test('öğrenciye sen, aileye siz: karşılama ve hızlı sorular', async ({ page }) => {
  await asistanAc(page)
  await expect(page.getByText(/size yardımcı olabilirim/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Işık bugün neye öncelik vermeli?' })).toBeVisible()
})
```
(Öğrenci hitabı Görev 17'de `asistan-ogretmen` geçişiyle sınanır; oyun sunucusunun oturumu ailedir.)

- [ ] **Step 7: Derle, testleri koş**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/carbon-ai/dashboard
npx tsc -b && IBM_TELEMETRY_DISABLED=true npm run build:carbon-ai 2>&1 | tail -3
node --test tests/*.test.ts
env -u ANTHROPIC_API_KEY npx playwright test carbon-asistan-cekirdek --reporter=list
```
Expected: tsc temiz; `paket-telemetri` iki testi de PASS; e2e 6/6 PASS. Bir test kırmızıysa önce ekran görüntüsünü (`test-results/`) Read ile aç.

- [ ] **Step 8: Commit**

```bash
git add dashboard/src/asistan dashboard/src/App.tsx dashboard/src/hooks/useSohbetler.ts dashboard/tests/gecmis.test.ts dashboard/tests/e2e/_asistan-carbon.ts dashboard/tests/e2e/carbon-asistan-cekirdek.spec.ts
git commit -m "feat(asistan): Carbon AI Chat çekirdeği — gönderme, akış, yedek, hata, /asistan

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: TEDY kartları — `user_defined` yanıtlar

**Files:**
- Create: `dashboard/src/asistan/OzelYanitlar.tsx`
- Modify: `dashboard/src/asistan/useAsistanSohbeti.tsx` (`renderUserDefinedResponse` prop'u)
- Create: `dashboard/tests/e2e/carbon-asistan-kartlar.spec.ts`

**Interfaces:**
- Consumes: `OzelKart` (Görev 7), `tekrarDene`, `soruyuYeniden`, `asistanDeposu` (Görev 11); mevcut `AlistirmaKarti`, `OdevOnayKarti`, `NetlestirmeSecenekleri`, `ModOnerisi`.
- Produces: `ozelYanitCizici(ogretmenSec: (id: string) => Promise<void>): (state: RenderUserDefinedState, inst: ChatInstance) => ReactNode`; `useAsistanSohbeti` dönüşüne `ogretmenSec`.

- [ ] **Step 1: e2e testleri yaz** (eski `asistan-alistirma`, `asistan-netlestirme`, `photo-homework`, `asistan-ogretmen` mod önerisi ve `assistant-ai` plan blokları testlerinin davranışları)

`dashboard/tests/e2e/carbon-asistan-kartlar.spec.ts`:
```ts
import { test, expect } from '@playwright/test'
import { PAYLOAD, asistanAc, cevapla, sor } from './_asistan-carbon'
import { OGRETMENLER } from './_gorsel-fixtures'

const QUIZ = { id: 'q1', baslik: 'Kesirler', ders: 'Matematik', konu: 'Kesir', kazanim_kodu: null, zorluk: 'kolay',
  sorular: [{ tur: 'coktan_secmeli', soru: '1/2 + 1/2 kaçtır?', secenekler: ['1', '2', '1/4', '0'] }] }

test('alıştırma akışta görünür, cevap sonra işaretlenir', async ({ page }) => {
  await cevapla(page, PAYLOAD({ answer: 'Alıştırma hazır.' }), [['quiz', QUIZ]])
  await page.route('**/api/assistant/alistirmalar/q1/cevap', r => r.fulfill({ json: { dogru: true, aciklama: 'İki yarım bir bütündür.' } }))
  await asistanAc(page)
  await sor(page, 'Kesirden alıştırma ver')
  await expect(page.getByText('1/2 + 1/2 kaçtır?')).toBeVisible()
  await page.getByRole('radio', { name: '1' }).check()
  await page.getByRole('button', { name: 'Cevabı gönder' }).click()
  await expect(page.getByText('Doğru', { exact: true })).toBeVisible()
})

test('netleştirme seçeneği soruyu gönderir; eski cevapta kapalı', async ({ page }) => {
  const istekler = await cevapla(page, PAYLOAD({ answer: 'Hangisini kastettin?', netlestirme: { soru: 'Hangisi?', secenekler: ['Kesir', 'Ondalık'] } }))
  await asistanAc(page)
  await sor(page, 'Bunu anlat')
  await page.getByRole('button', { name: 'Kesir' }).click()
  await expect.poll(() => istekler.length).toBe(2)
  expect(JSON.stringify(istekler[1])).toContain('Kesir')
  await expect(page.getByRole('button', { name: 'Kesir' }).first()).toBeDisabled()
})

test('ödev fotoğrafı onay kartı adayları gösterir ve kayıt yalnız onayla', async ({ page }) => {
  let kayit = 0
  await page.route('**/api/homework/photo**', r => { kayit += 1; return r.fulfill({ json: { ok: true } }) })
  await cevapla(page, PAYLOAD({ answer: 'Fotoğraftaki ödevler.', odev_onerisi: { ek_id: 'e'.repeat(32),
    adaylar: [{ ders: 'Matematik', baslik: 's.84', teslim: '2026-10-09', aciklama: '1-10', eksik: [] }] } }))
  await asistanAc(page)
  await sor(page, 'Bunu işlere ekle')
  await expect(page.getByLabel('Başlık', { exact: true })).toHaveValue('s.84')
  expect(kayit).toBe(0)
  await page.getByRole('button', { name: 'Ödevlere ekle' }).click()
  await expect.poll(() => kayit).toBe(1)
})

test('mod önerisi yalnız Genel modda, tıklanınca öğretmen değişir', async ({ page }) => {
  await page.route('**/api/assistant/ogretmenler', r => r.fulfill({ json: OGRETMENLER }))
  await cevapla(page, PAYLOAD({ answer: 'Bu bir matematik sorusu.' }), [['mode_suggestion', { ogretmen: 'matematik',
    ogretmen_adi: 'Matematik öğretmeni', soru: 'Matematik öğretmenine geçelim mi?', gerekce: 'Kesir konusu', renk_ailesi: 'blue' }]])
  await asistanAc(page)
  await sor(page, 'Kesir nedir?')
  await page.getByRole('button', { name: 'Matematik öğretmenine geçelim mi?' }).click()
  await expect(page.getByRole('radio', { name: 'Matematik' })).toBeChecked()
  await expect(page.getByRole('button', { name: 'Matematik öğretmenine geçelim mi?' })).toHaveCount(0)
})

test('çalışma planı hızlı sorusu /plan ucuna gider ve plan bloklarını gösterir', async ({ page }) => {
  let plan = 0
  await page.route('**/api/assistant/plan', r => { plan += 1; return r.fulfill({ json: PAYLOAD({ answer: 'Planın hazır.',
    plan_blocks: [{ day: 'Pazartesi', title: 'Kesir tekrarı', actions: ['Örnekleri çöz'], estimated_minutes: 25 }] }) }) })
  await cevapla(page, PAYLOAD())
  await asistanAc(page)
  await page.getByRole('button', { name: 'Işık için çalışma planı hazırla' }).click()
  await expect(page.getByText('Kesir tekrarı')).toBeVisible()
  await expect(page.getByText('25 dk')).toBeVisible()
  expect(plan).toBe(1)
})
```
(Düğme adları mevcut bileşenlerden: `AlistirmaKarti` "Cevabı gönder", `OdevOnayKarti` "Ödevlere ekle", `ModOnerisi` öneri metninin kendisi. Alan etiketleri "Ders", "Başlık", "Teslim", "Açıklama".)

- [ ] **Step 2: Kırmızıyı gör**

Run: `cd dashboard && npm run build:carbon-ai >/dev/null && env -u ANTHROPIC_API_KEY npx playwright test carbon-asistan-kartlar --reporter=list` → FAIL (kartlar çizilmiyor).

- [ ] **Step 3: Kart çizicisi**

`dashboard/src/asistan/OzelYanitlar.tsx`:
```tsx
import type { ReactNode } from 'react'
import { Button, Tag } from '@carbon/react'
import { Renew } from '@carbon/icons-react'
import type { ChatInstance, RenderUserDefinedState } from '@carbon/ai-chat'
import AlistirmaKarti from '../components/AlistirmaKarti'
import OdevOnayKarti from '../components/OdevOnayKarti'
import NetlestirmeSecenekleri from '../components/NetlestirmeSecenekleri'
import ModOnerisi from '../components/ModOnerisi'
import { GENEL } from '../hooks/useOgretmen'
import type { OzelKart } from './olayEslemesi.ts'
import { asistanDeposu, useAsistanDurumu } from './asistanDeposu.ts'
import { soruyuYeniden, tekrarDene } from './useAsistanSohbeti.tsx'

function Kart({ kart, state, inst, ogretmenSec }: { kart: OzelKart; state: RenderUserDefinedState; inst: ChatInstance; ogretmenSec: (id: string) => Promise<void> }) {
  const salt = useAsistanDurumu(d => d.saltOkunur)
  const yukleniyor = useAsistanDurumu(d => d.yukleniyor)
  const ogretmenId = useAsistanDurumu(d => d.ogretmenId)
  const sonYanitId = useAsistanDurumu(d => d.sonYanitId)
  const mesajId = state.fullMessage?.id
  switch (kart.tur) {
    case 'alistirma':
      return <AlistirmaKarti alistirma={kart.veri} saltOkunur={salt} disabled={kart.akista || yukleniyor}
        onYanlislar={metin => void soruyuYeniden(inst, `Yanlış yaptığım bu soruları açıklar mısın?\n${metin}`, {})} />
    case 'odev_onerisi':
      return <OdevOnayKarti oneri={kart.veri} saltOkunur={salt || yukleniyor} />
    case 'netlestirme':
      // Yalnız son cevaptaki seçenekler etkin; eski ya da salt okunur sohbette kapalı (D1).
      return <NetlestirmeSecenekleri secenekler={kart.veri.secenekler}
        etkin={mesajId !== undefined && mesajId === sonYanitId && !yukleniyor && !salt}
        onSec={metin => void inst.send(metin)} onBaska={() => inst.requestFocus()} />
    case 'mod_onerisi':
      if (ogretmenId !== GENEL) return null
      return <ModOnerisi oneri={kart.veri} onGec={() => void ogretmenSec(kart.veri.ogretmen)} />
    case 'plan':
      return <ul className="ac__ref-list">{kart.veri.map((b, i) => (
        <li key={`${b.day}-${i}`} className="ac__plan-item">
          <div className="ac__plan-header"><Tag type="gray" size="sm">{b.day}</Tag><span className="ac__plan-time">{b.estimated_minutes} dk</span></div>
          <span className="ac__plan-title">{b.title}</span>
          <p className="ac__plan-actions">{b.actions.join(' • ')}</p>
        </li>))}</ul>
    case 'hata':
      return <div className="asistan__hata" role="alert">
        <Tag type="red" size="sm">{kart.veri.mesaj}</Tag>
        {asistanDeposu.al().bekleyen && mesajId &&
          <Button kind="ghost" size="sm" renderIcon={Renew} onClick={() => void tekrarDene(inst, mesajId)}>Tekrar dene</Button>}
      </div>
  }
}

export function ozelYanitCizici(ogretmenSec: (id: string) => Promise<void>) {
  return (state: RenderUserDefinedState, inst: ChatInstance): ReactNode => {
    const kart = (state.messageItem?.user_defined as { tedy?: OzelKart } | undefined)?.tedy
    return kart ? <Kart kart={kart} state={state} inst={inst} ogretmenSec={ogretmenSec} /> : null
  }
}
```
`useAsistanSohbeti.tsx` içinde:
```tsx
  const ogretmenSec = useCallback(async (id: string) => {
    const d = asistanDeposu.al()
    if (d.saltOkunur || d.yukleniyor) return
    if (d.sohbetId) await sohbetRef.current.degistir(d.sohbetId, { ogretmen: id })
    ogretmen.sec(id)
    document.querySelector<HTMLInputElement>(`input[name="ac-ogretmen"][value="${CSS.escape(id)}"]`)
      ?.focus({ focusVisible: true } as FocusOptions)
  }, [ogretmen])
  const ozelYanit = useMemo(() => ozelYanitCizici(ogretmenSec), [ogretmenSec])
```
ve `props`'a `renderUserDefinedResponse: ozelYanit`; dönüş nesnesine `ogretmenSec`. `AsistanSayfasi`'nda `OgretmenSecici onSec={id => void ogretmenSec(id)}`.

- [ ] **Step 4: Geç**

Run: `cd dashboard && npx tsc -b && npm run build:carbon-ai >/dev/null && env -u ANTHROPIC_API_KEY npx playwright test carbon-asistan-kartlar carbon-asistan-cekirdek --reporter=list` → PASS.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/asistan dashboard/tests/e2e/carbon-asistan-kartlar.spec.ts
git commit -m "feat(asistan): TEDY kartları Carbon AI Chat user_defined yanıtı olarak

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: Atıflar ve kaynak paneli (workspace)

Carbon atıf kartı başlık + kısa metni gösterir. Figür küçük resmi, modül bağlantısı ve Tedy kitabı grubu bugünkü `SourcePanel`'dedir; atıfa tıklanınca ya da altbilgideki "Kaynaklar" düğmesine basılınca workspace panelinde açılır.

**Files:**
- Create: `dashboard/src/asistan/KaynakPaneli.tsx`
- Modify: `dashboard/src/asistan/useAsistanSohbeti.tsx` (workspace açma işlevi, `renderWriteableElements.customPanelElement`)
- Create: `dashboard/tests/e2e/carbon-asistan-kaynaklar.spec.ts`

**Interfaces:**
- Consumes: `AltbilgiVerisi.atiflar` (Görev 7), mevcut `SourcePanel({ citations, activeId })`.
- Produces: `kaynaklariAc(inst: ChatInstance, atiflar: AssistantCitation[], etkin: string | null): Promise<void>` (useAsistanSohbeti'den dışa aktarılır; Görev 14 altbilgisi kullanır).

- [ ] **Step 1: e2e testleri** (eski `assistant-chat` "sources are grouped by kind…", `asistan-gorsel-kaynak`, `assistant-moduller` davranışları)

`dashboard/tests/e2e/carbon-asistan-kaynaklar.spec.ts`:
```ts
import { test, expect } from '@playwright/test'
import { PAYLOAD, asistanAc, cevapla, sor } from './_asistan-carbon'

const ATIFLAR = [
  { id: 'S1', kind: 'mufredat', label: 'Matematik 7 · s.57', locator: {}, snippet: 'Kesirler bölümü', confidence: 1 },
  { id: 'S2', kind: 'mufredat', label: 'Fen Bilimleri 7 figürü', locator: { figure_id: 42, caption: 'Hücre', corpus_version: '1.6' }, snippet: 'Hücre', confidence: 1 },
  { id: 'S3', kind: 'modul', label: 'Kesir modülü', locator: { slug: 'kesir', version: 2 }, snippet: 'Modül', confidence: 1 },
]

test('atıflar Carbon kaynak listesinde, numaralı ve doğru sırada', async ({ page }) => {
  await cevapla(page, PAYLOAD({ answer: 'Kesir parçadır [S1]. Hücre canlının birimidir [S2]. Modül var [S3].', citations: ATIFLAR }))
  await asistanAc(page)
  await sor(page, 'Soru')
  await expect(page.getByText('Kesir parçadır.')).toBeVisible()
  await expect(page.getByText('[S1]')).toHaveCount(0)
  await page.getByRole('button', { name: 'Kaynak listesini aç veya kapat' }).click()
  await expect(page.getByText('Matematik 7 · s.57')).toBeVisible()
})

test('Kaynaklar paneli figür küçük resmini sürümüyle ve modül bağlantısını gösterir', async ({ page }) => {
  await page.route('**/api/assistant/figure/42?v=1.6', r => r.fulfill({ body: Buffer.from([0x89, 0x50, 0x4e, 0x47]), contentType: 'image/png' }))
  await cevapla(page, PAYLOAD({ answer: 'Bak [S2]. Modül [S3].', citations: ATIFLAR.slice(1) }))
  await asistanAc(page)
  await sor(page, 'Soru')
  await page.getByRole('button', { name: 'Kaynaklar' }).click()
  const panel = page.getByRole('region', { name: 'Çalışma paneli' })
  await expect(panel.getByRole('img', { name: 'Hücre' })).toHaveAttribute('src', /\/api\/assistant\/figure\/42\?v=1\.6/)
  await expect(panel.getByRole('link', { name: /Kesir modülü/ })).toHaveAttribute('href', '/moduller/kesir/v2')
})
```

- [ ] **Step 2: Panel bileşeni ve açma işlevi**

`dashboard/src/asistan/KaynakPaneli.tsx`:
```tsx
import SourcePanel from '../components/SourcePanel'
import { useAsistanDurumu } from './asistanDeposu.ts'

/** Workspace panelinin içeriği: bugünkü kaynak paneli, son açılan cevabın atıflarıyla. */
export default function KaynakPaneli() {
  const acik = useAsistanDurumu(d => d.acikAtif)
  if (!acik) return null
  return <div className="asistan__kaynaklar"><SourcePanel citations={acik.atiflar} activeId={acik.etkin} /></div>
}
```

`useAsistanSohbeti.tsx`:
```tsx
import type { AssistantCitation } from '../types'
import KaynakPaneli from './KaynakPaneli.tsx'

export async function kaynaklariAc(inst: ChatInstance, atiflar: AssistantCitation[], etkin: string | null) {
  asistanDeposu.ayarla({ acikAtif: { atiflar, etkin } })
  await inst.customPanels?.getPanel('workspace' as never).open({ title: 'Kaynaklar', preferredLocation: 'end' } as never)
}
```
`props`'a: `renderWriteableElements: { customPanelElement: <KaynakPaneli /> }`.

Atıf numarası Carbon'un kendi kaynak kartını açar (başlık + kısa metin). Figür, modül ve kitap ayrıntısı olan kaynak paneli altbilgideki "Kaynaklar" düğmesiyle workspace'te açılır (Görev 14). Eski arayüzde de kaynak paneli ayrı bir sütundu; numara yalnız vurguluyordu.

- [ ] **Step 3: Geç** — ilk test şimdi; ikinci test "Kaynaklar" düğmesi gerektirir ve Görev 14 Step 5'te koşulur.

Run: `cd dashboard && npx tsc -b && npm run build:carbon-ai >/dev/null && env -u ANTHROPIC_API_KEY npx playwright test carbon-asistan-kaynaklar -g "numaralı" --reporter=list` → PASS.

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/asistan dashboard/tests/e2e/carbon-asistan-kaynaklar.spec.ts
git commit -m "feat(asistan): atıflar Carbon kaynak listesinde, kaynak paneli workspace'te

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 14: Mesaj altbilgisi, AI açıklaması, geri bildirim, günlükte özet

**Files:**
- Create: `dashboard/src/asistan/MesajAltbilgisi.tsx`
- Create: `dashboard/src/asistan/geriBildirim.ts`
- Modify: `dashboard/src/asistan/useAsistanSohbeti.tsx` (`renderCustomMessageFooter`, `onBeforeRender` içinde geri bildirim dinleyicisi, `explainabilityPopoverContent`)
- Modify: `dashboard/src/components/PlatformProgress.tsx` (Öğrenme günlüğünde geri bildirim özeti)
- Create: `dashboard/tests/e2e/carbon-asistan-altbilgi.spec.ts`

**Interfaces:**
- Consumes: `AltbilgiVerisi`, `ALTBILGI_YUVASI` (Görev 7); `kaynaklariAc`, `soruyuYeniden` (Görev 11/13); `useSes` (mevcut); Görev 6 uçları.
- Produces: `geriBildirimGonder(olay: BusEventFeedback): Promise<void>`; `altbilgiCizici(): RenderCustomMessageFooter`.

- [ ] **Step 1: e2e testleri** (eski `assistant-chat` "degraded", "risk and warning flags", "local fallback", `asistan-ses`, `assistant-ai` model açıklaması; yeni geri bildirim)

`dashboard/tests/e2e/carbon-asistan-altbilgi.spec.ts`:
```ts
import { test, expect } from '@playwright/test'
import { PAYLOAD, asistanAc, cevapla, sor } from './_asistan-carbon'

const MID = 'a'.repeat(32)

test('rozetler: kaynak sorunu, risk kırmızı, uyarı gri, yedek model; ham bayrak yok', async ({ page }) => {
  await cevapla(page, PAYLOAD({ answer: 'Cevap.', safety_flags: ['risk:self_harm', 'warning:yerel_yedek'],
    meta: { model: 'gemma4-e4b-cpu', degraded: ['maarif-mufredat', 'yeni-sunucu'] } }))
  await asistanAc(page)
  await sor(page, 'Soru')
  await expect(page.getByText('Müfredat kaynağına ulaşılamadı')).toBeVisible()
  await expect(page.getByText('Kaynağa ulaşılamadı: yeni-sunucu')).toBeVisible()
  await expect(page.getByText('Yedek modelden')).toBeVisible()
  await expect(page.getByText('warning:yerel_yedek')).toHaveCount(0)
  await expect(page.locator('[data-tedy-altbilgi] .cds--tag--red')).toHaveCount(1)
})

test('Daha derine in force_deep yollar; Yeniden üret eskisini kaldırır; Kopyala', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  const istekler = await cevapla(page, PAYLOAD({ answer: 'İlk cevap.' }))
  await asistanAc(page)
  await sor(page, 'Kesir nedir?')
  await page.getByRole('button', { name: 'Daha derine in' }).click()
  await expect.poll(() => istekler.length).toBe(2)
  expect(istekler[1]).toMatchObject({ force_deep: true })
  await page.getByRole('button', { name: 'Kopyala' }).first().click()
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe('İlk cevap.')
})

test('olumsuz geri bildirim kategorisiyle PUT eder; öğrenciye değil aileye uygun yer tutucu', async ({ page }) => {
  let govde: unknown = null
  await page.route(`**/api/assistant/mesajlar/${MID}/geri-bildirim`, async r => {
    govde = r.request().postDataJSON(); await r.fulfill({ json: govde as object })
  })
  await cevapla(page, PAYLOAD({ answer: 'Cevap.', mesaj_id: MID }))
  await asistanAc(page)
  await sor(page, 'Soru')
  await page.getByRole('button', { name: 'Bu yanıtı beğenmedim' }).click()
  await page.getByRole('button', { name: 'Anlamadım' }).click()
  await page.getByPlaceholder('Yorum ekle').fill('çok hızlı')
  await page.getByRole('button', { name: 'Gönder', exact: true }).last().click()
  await expect.poll(() => govde).toEqual({ deger: 'olumsuz', kategori: 'Anlamadım', metin: 'çok hızlı' })
})

test('mesaj kimliği olmayan cevapta geri bildirim düğmesi yok', async ({ page }) => {
  await cevapla(page, PAYLOAD({ answer: 'Kayıtsız.' }))
  await asistanAc(page)
  await sor(page, 'Soru')
  await expect(page.getByText('Kayıtsız.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Bu yanıtı beğenmedim' })).toHaveCount(0)
})

test('AI etiketi açıklaması modeli ve kaynak notunu söyler', async ({ page }) => {
  await cevapla(page, PAYLOAD({ answer: 'Cevap.', meta: { model: 'claude-sonnet-5', degraded: [] } }))
  await asistanAc(page)
  await sor(page, 'Soru')
  await page.getByRole('button', { name: /Yapay zekâ açıklaması/ }).first().click()
  await expect(page.getByText('Bu yanıtları bir yapay zekâ yazıyor')).toBeVisible()
  await expect(page.getByText(/Son yanıtı .*Sonnet.* yazdı/)).toBeVisible()
})

test('İlerleme sayfası günlüğünde haftalık geri bildirim özeti', async ({ page }) => {
  await page.route('**/api/assistant/ogrenme-gunlugu', r => r.fulfill({ json: { zayif: [], calisilan: [], degerlendirmeler: [],
    hafta: { baslangic: '2026-10-05', sohbet: [], alistirma: 0, puan: { dogru: 0, toplam: 0 } },
    geri_bildirim: { hafta: { olumlu: 3, olumsuz: 1 }, son_olumsuz: [{ kategori: 'Anlamadım', metin: 'çok hızlı', zaman: '2026-10-08T09:00:00Z' }] } } }))
  await page.goto('/ilerleme')
  await expect(page.getByText('Asistan cevapları: 3 beğenildi, 1 beğenilmedi')).toBeVisible()
  await expect(page.getByText('Anlamadım — çok hızlı')).toBeVisible()
})
```

- [ ] **Step 2: Altbilgi bileşeni**

`dashboard/src/asistan/MesajAltbilgisi.tsx`:
```tsx
import { Button, IconButton, Tag } from '@carbon/react'
import { Copy, Renew, Search, Book } from '@carbon/icons-react'
import type { ChatInstance, GenericItem, MessageResponse } from '@carbon/ai-chat'
import { okunacakMetin } from '../utils/ses'
import type { AltbilgiVerisi } from './olayEslemesi.ts'
import { useAsistanDurumu, asistanDeposu } from './asistanDeposu.ts'
import { kaynaklariAc, soruyuYeniden } from './useAsistanSohbeti.tsx'

const BAYRAK: Record<string, string> = {
  'warning:limited_confidence': 'Kaynaksız cevap', 'warning:stale_context': 'Veriler güncel olmayabilir',
  'error:model_unavailable': 'Asistana ulaşılamadı', 'warning:yerel_yedek': 'Yedek modelden',
}
const KAYNAK: Record<string, string> = {
  'maarif-mufredat': 'Müfredat kaynağına ulaşılamadı', 'egitim-kaynak': 'Açık eğitim kaynağına ulaşılamadı',
  'modul-katalogu': 'Modül kataloğu okunamadı',
}

/** Bu cevabı doğuran kullanıcı sorusu: döküm sırasında bu cevaptan önceki son kullanıcı turu. */
function soru(metin: string): string | null {
  const dokum = asistanDeposu.al().dokum
  const i = dokum.map(m => m.role === 'assistant' && m.content === metin).lastIndexOf(true)
  for (let j = (i < 0 ? dokum.length : i) - 1; j >= 0; j -= 1) if (dokum[j].role === 'user') return dokum[j].content
  return null
}

export function MesajAltbilgisi({ veri, mesaj, inst }: { veri: AltbilgiVerisi; mesaj: MessageResponse; inst: ChatInstance }) {
  const salt = useAsistanDurumu(d => d.saltOkunur)
  const yukleniyor = useAsistanDurumu(d => d.yukleniyor)
  const ses = useAsistanDurumu(d => d.ses)
  const kapali = yukleniyor || salt
  return (
    <div className="asistan__altbilgi" data-tedy-altbilgi>
      {(veri.kaynakSorunlari.length > 0 || veri.bayraklar.length > 0) && <div className="asistan__rozetler">
        {veri.kaynakSorunlari.map(s => <Tag key={s} type="gray" size="sm">{KAYNAK[s] ?? `Kaynağa ulaşılamadı: ${s}`}</Tag>)}
        {veri.bayraklar.map(f => <Tag key={f} type={f.startsWith('risk:') ? 'red' : 'gray'} size="sm">{BAYRAK[f] ?? f}</Tag>)}
      </div>}
      <div className="asistan__eylemler">
        {veri.atiflar.length > 0 && <Button kind="ghost" size="sm" renderIcon={Book}
          onClick={() => void kaynaklariAc(inst, veri.atiflar, null)}>Kaynaklar</Button>}
        <IconButton kind="ghost" size="sm" label="Kopyala" onClick={() => void navigator.clipboard.writeText(veri.metin)}><Copy /></IconButton>
        <IconButton kind="ghost" size="sm" label="Yeniden üret" disabled={kapali} onClick={async () => {
          const s = soru(veri.metin); if (!s) return
          await inst.messaging.removeMessages([mesaj.id!]); await soruyuYeniden(inst, s, { transient: true })
        }}><Renew /></IconButton>
        <Button kind="ghost" size="sm" renderIcon={Search} disabled={kapali}
          onClick={() => { const s = soru(veri.metin); if (s) void soruyuYeniden(inst, s, { deep: true }) }}>Daha derine in</Button>
        {ses?.var && okunacakMetin(veri.metin) && <Button kind="ghost" size="sm" aria-pressed={ses.okunan === mesaj.id}
          onClick={() => ses.oku(mesaj.id!, veri.metin)}>{ses.okunan === mesaj.id ? 'Durdur' : 'Sesli oku'}</Button>}
      </div>
    </div>
  )
}

export function altbilgiCizici() {
  return (_slot: string, mesaj: MessageResponse, _oge: GenericItem, inst: ChatInstance, ek?: Record<string, unknown>) =>
    ek ? <MesajAltbilgisi veri={ek as unknown as AltbilgiVerisi} mesaj={mesaj} inst={inst} /> : null
}
```
`soru()` için döküm, `gecmis.ts` ile geçmiş yüklenirken de doldurulur (Görev 15).

- [ ] **Step 3: Geri bildirim ve AI açıklaması**

`dashboard/src/asistan/geriBildirim.ts`:
```ts
import type { BusEventFeedback } from '@carbon/ai-chat'

/** Carbon'un geri bildirim olayı → PUT /api/assistant/mesajlar/<id>/geri-bildirim (spec §5.2). */
export async function geriBildirimGonder(olay: BusEventFeedback): Promise<void> {
  if (String(olay.interactionType) !== 'submitted') return
  const id = (olay.messageItem.message_item_options?.feedback?.id) ?? ''
  if (!/^[0-9a-f]{32}$/.test(id)) return
  const kategori = olay.isPositive ? null : (olay.categories?.[0] ?? null)
  await fetch(`/api/assistant/mesajlar/${id}/geri-bildirim`, {
    method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ deger: olay.isPositive ? 'olumlu' : 'olumsuz', kategori, metin: olay.text ?? '' }),
  })
}
```
`useAsistanSohbeti.tsx` `onBeforeRender`:
```tsx
    onBeforeRender: inst => {
      instance.current = inst
      inst.on({ type: 'feedback' as never, handler: (e: unknown) => void geriBildirimGonder(e as BusEventFeedback) })
    },
    renderCustomMessageFooter: altbilgi,   // const altbilgi = useMemo(() => altbilgiCizici(), [])
```
ve `renderWriteableElements`'a AI açıklaması (eski üst başlık penceresinin metni + son model):
```tsx
      explainabilityPopoverContent: <div className="asistan__ai-acikla">
        <h4>Bu yanıtları bir yapay zekâ yazıyor</h4>
        <p>{VOICE[okur].sources}</p><p>{VOICE[okur].caution}</p>
        <p>{sonModel ? `Son yanıtı ${modelAdi(sonModel)} yazdı.` : 'Henüz yanıt yok.'}</p>
      </div>,
```
(`sonModel`: `calistir` her son yanıtta `asistanDeposu.ayarla({ sonModel: payload.meta?.model })` yazar; `AsistanDurumu`'na `sonModel?: string` ekleyin. `modelAdi` `../utils/formatters`'tan.)

- [ ] **Step 4: Günlükte özet**

`dashboard/src/components/PlatformProgress.tsx` `Gunluk` türüne:
```ts
  geri_bildirim?: { hafta: { olumlu: number; olumsuz: number }; son_olumsuz: { kategori: string | null; metin: string; zaman: string }[] }
```
ve "Öğrenme günlüğü" bölümünün sonuna:
```tsx
    {data?.geri_bildirim && <div className="ogrenme-gunlugu__geri-bildirim">
      <p>Asistan cevapları: {data.geri_bildirim.hafta.olumlu} beğenildi, {data.geri_bildirim.hafta.olumsuz} beğenilmedi</p>
      {data.geri_bildirim.son_olumsuz.length > 0 && <ul>{data.geri_bildirim.son_olumsuz.map(n => (
        <li key={n.zaman}>{[n.kategori, n.metin].filter(Boolean).join(' — ')}</li>))}</ul>}
    </div>}
```

- [ ] **Step 5: Geç (Görev 13'ün ikinci testi dahil)**

Run: `cd dashboard && npx tsc -b && npm run lint && npm run build:carbon-ai >/dev/null && env -u ANTHROPIC_API_KEY npx playwright test carbon-asistan-altbilgi carbon-asistan-kaynaklar ilerleme --reporter=list` → PASS.

- [ ] **Step 6: Commit**

```bash
git add dashboard/src/asistan dashboard/src/components/PlatformProgress.tsx dashboard/tests/e2e/carbon-asistan-altbilgi.spec.ts
git commit -m "feat(asistan): mesaj altbilgisi, AI açıklaması, geri bildirim ve günlük özeti

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 15: Sohbet geçmişi, ortak etkin sohbet, aile salt okur, yeni sohbet

Geçmiş listesinin içeriği Carbon'un geçmiş paneli yuvasına (`historyPanelElement`) konan bugünkü `SohbetListesi`'dir (yeni sohbet, yeniden adlandır, sil, "Işık'ın sohbetleri", "Asistanın notları" aynen). Carbon'un "Yeni sohbet" ve yeniden başlat düğmeleri de yeni sohbet açar.

**Files:**
- Create: `dashboard/src/asistan/useAsistanOturumu.ts`
- Create: `dashboard/src/asistan/GecmisPaneli.tsx`
- Create: `dashboard/src/asistan/odevler.ts` (`acikOdevler`)
- Modify: `dashboard/src/components/SohbetListesi.tsx` (`gomulu?: boolean`)
- Modify: `dashboard/src/asistan/useAsistanSohbeti.tsx` (`gecmisYukle`, `renderWriteableElements.historyPanelElement`, `renderCustomRequestFooter`, `history:newChat` ve `restartConversation` dinleyicileri, salt okunurda giriş kapalı)
- Create: `dashboard/tests/e2e/carbon-asistan-sohbet.spec.ts`

**Interfaces:**
- Consumes: `useSohbetler` (mevcut), `gecmisOgeleri` (Görev 11), `YuklenenEk` (mevcut).
- Produces:
  - `etkinSohbetAnahtari(email?: string): string | null` → `tedy-asistan-etkin::<email>` (sessionStorage; sekme kapanınca biter)
  - `etkinSohbetiOku(email?: string): { id: string; salt: boolean } | null`, `etkinSohbetiYaz(email: string | undefined, d: { id: string; salt: boolean } | null): void`
  - `sohbetiAc(inst: ChatInstance, sohbet: ReturnType<typeof useSohbetler>, ogretmenSec: (id: string) => void, id: string, salt: boolean): Promise<void>`
  - `yeniSohbet(inst: ChatInstance, sohbet: ReturnType<typeof useSohbetler>): Promise<void>`

- [ ] **Step 1: e2e testleri** — eski `asistan-sohbet.spec.ts`'in dokuz testi aynı adlarla, seçici çevirisiyle (bkz. Görev 19 tablosu); ek olarak:

`dashboard/tests/e2e/carbon-asistan-sohbet.spec.ts` (eski dosyadaki `SOHBET`, `MESAJLAR` sabitleri ve dokuz test buraya taşınır; aşağıdaki iki test yeni):
```ts
import { test, expect } from '@playwright/test'
import { sabitAc } from './_gorsel-yardim'
import { json } from './_audit-fixtures'
// SOHBET ve MESAJLAR: eski asistan-sohbet.spec.ts'ten birebir.

test('salt okunur aile sohbetinde giriş kapalı, geri bildirim yok', async ({ page }) => {
  await sabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/sohbetler**', r => r.request().url().includes('kisi=ogrenci')
    ? r.fulfill(json({ sohbetler: [SOHBET] })) : r.fulfill(json({ sohbetler: [] })))
  await page.route(`**/api/assistant/sohbetler/${SOHBET.id}`, r => r.fulfill(json({ sohbet: SOHBET, mesajlar: MESAJLAR, read_only: true })))
  await page.goto('/asistan')
  await page.getByRole('button', { name: 'Payda eşitle' }).click()
  await expect(page.getByText('Paydalar toplanmaz.')).toBeVisible()
  await expect(page.getByRole('textbox', { name: 'Sorunu yaz' })).not.toBeEditable()
  await expect(page.getByRole('button', { name: 'Bu yanıtı beğenmedim' })).toHaveCount(0)
})

test('Carbon yeni sohbet düğmesi yeni kayıt açar ve konuşmayı boşaltır', async ({ page }) => {
  let yeni = 0
  await sabitAc(page, '/asistan', 1440, 900)
  await page.route('**/api/assistant/sohbetler', r => {
    if (r.request().method() === 'POST') { yeni += 1; return r.fulfill(json({ id: 'cd'.repeat(16), ogretmen: 'genel', baslik: '' })) }
    return r.fulfill(json({ sohbetler: [SOHBET] }))
  })
  await page.route(`**/api/assistant/sohbetler/${SOHBET.id}`, r => r.fulfill(json({ sohbet: SOHBET, mesajlar: MESAJLAR })))
  await page.goto('/asistan')
  await page.getByRole('button', { name: 'Payda eşitle' }).click()
  await expect(page.getByText('Paydalar toplanmaz.')).toBeVisible()
  await page.getByRole('button', { name: 'Sohbeti yeniden başlat' }).click()
  await expect(page.getByText('Paydalar toplanmaz.')).toHaveCount(0)
  expect(yeni).toBe(1)
})
```

- [ ] **Step 2: Ortak etkin sohbet**

`dashboard/src/asistan/useAsistanOturumu.ts`:
```ts
import type { ChatInstance } from '@carbon/ai-chat'
import type { useSohbetler } from '../hooks/useSohbetler'
import { gecmisOgeleri } from './gecmis.ts'
import { asistanDeposu } from './asistanDeposu.ts'
import type { Yukleme } from '../components/YuklenenEk'

type Depo = ReturnType<typeof useSohbetler>

/** Sayfa ile başlatıcı aynı sohbeti açar: etkin sohbet sekme oturumunda, kişiye ayrı (localStorage değil). */
export function etkinSohbetAnahtari(email?: string): string | null {
  return email ? `tedy-asistan-etkin::${email.trim().toLocaleLowerCase('tr-TR')}` : null
}
export function etkinSohbetiOku(email?: string): { id: string; salt: boolean } | null {
  const k = etkinSohbetAnahtari(email)
  try { return k ? JSON.parse(sessionStorage.getItem(k) ?? 'null') : null } catch { return null }
}
export function etkinSohbetiYaz(email: string | undefined, d: { id: string; salt: boolean } | null) {
  const k = etkinSohbetAnahtari(email)
  if (!k) return
  try { if (d) sessionStorage.setItem(k, JSON.stringify(d)); else sessionStorage.removeItem(k) } catch { /* yalnız bellek */ }
}

export async function sohbetiAc(inst: ChatInstance, depo: Depo, ogretmenSec: (id: string) => void, id: string, salt: boolean) {
  const sonuc = await depo.ac(id, salt)
  if (!sonuc) return
  const saltMi = sonuc.read_only ?? salt
  etkinSohbetiYaz(asistanDeposu.al().email, { id, salt: saltMi })
  ogretmenSec(sonuc.sohbet.ogretmen)
  const ekGoruntuleri: Record<string, Yukleme[]> = {}
  for (const m of sonuc.mesajlar) if (m.rol === 'user' && m.yuklemeler?.length) ekGoruntuleri[m.id] = m.yuklemeler
  asistanDeposu.ayarla({ saltOkunur: saltMi, sohbetId: id, cipler: [], bekleyen: null, ekGoruntuleri,
    dokum: sonuc.mesajlar.map(m => ({ role: m.rol, content: m.icerik })) })
  await inst.messaging.clearConversation()
  await inst.messaging.insertHistory(gecmisOgeleri(sonuc.mesajlar, { geriBildirim: !saltMi, ogrenci: asistanDeposu.al().okur === 'ogrenci' }))
  inst.updateInputIsDisabled(saltMi)
}

export async function yeniSohbet(inst: ChatInstance, depo: Depo) {
  const d = asistanDeposu.al()
  const id = await depo.yeni(d.ogretmenId)
  etkinSohbetiYaz(d.email, { id, salt: false })
  asistanDeposu.ayarla({ saltOkunur: false, sohbetId: id, dokum: [], cipler: [], bekleyen: null, ekGoruntuleri: {} })
  await inst.messaging.clearConversation()
  inst.updateInputIsDisabled(false)
}
```

`useSohbetler.ts`'de `secili` başlangıç değeri etkin sohbetten okunur (sayfa ↔ başlatıcı geçişinde kaybolmasın):
```ts
  const [secili, setSecili] = useState<{ id: string; salt: boolean } | null>(() => etkinSohbetiOku(email ?? undefined))
```
(`etkinSohbetiOku` `../asistan/useAsistanOturumu`'dan içe aktarılır; eski bileşen için de zararsızdır: etkin anahtar yalnız yeni arayüz yazar.)

- [ ] **Step 3: Geçmiş paneli ve istek altbilgisi**

`dashboard/src/asistan/GecmisPaneli.tsx`:
```tsx
import type { ChatInstance } from '@carbon/ai-chat'
import SohbetListesi from '../components/SohbetListesi'
import type { useSohbetler } from '../hooks/useSohbetler'
import { useAsistanDurumu } from './asistanDeposu.ts'
import { sohbetiAc, yeniSohbet, etkinSohbetiYaz } from './useAsistanOturumu.ts'

export default function GecmisPaneli({ depo, ogrenci, inst, ogretmenSec }: {
  depo: ReturnType<typeof useSohbetler>; ogrenci: boolean; inst: () => ChatInstance | null; ogretmenSec: (id: string) => void
}) {
  const yukleniyor = useAsistanDurumu(d => d.yukleniyor)
  return <SohbetListesi depo={depo} student={ogrenci} disabled={yukleniyor || depo.bekliyor}
    onAc={(id, salt) => { const i = inst(); if (i) void sohbetiAc(i, depo, ogretmenSec, id, salt) }}
    onYeni={() => { const i = inst(); if (i) void yeniSohbet(i, depo).catch(() => depo.setHata('Sohbet kaydedilemedi.')) }}
    onSil={id => void depo.sil(id).then(async () => {
      if (depo.secili?.id === id) { etkinSohbetiYaz(undefined, null); const i = inst(); if (i) await i.messaging.clearConversation() }
    }).catch(() => depo.setHata('Sohbet kaydedilemedi.'))} />
}
```
(`SohbetListesi`'nin telefondaki kendi "Sohbetler" aç/kapat düğmesi Carbon panelinde gereksizdir; panel Carbon'un mobil menüsüyle açılır. `SohbetListesi`'ye `gomulu?: boolean` prop'u eklenir: `true` iken `telefon` dalı (düğme ve `hidden`) devre dışı kalır. Eski bileşen prop'u vermez, davranışı değişmez.)

`useAsistanSohbeti.tsx`:
```tsx
  const gecmisYukle = useCallback(async () => {
    const etkin = etkinSohbetiOku(user?.email)
    if (!etkin) return []
    const sonuc = await sohbetRef.current.ac(etkin.id, etkin.salt)
    if (!sonuc) { etkinSohbetiYaz(user?.email, null); return [] }
    asistanDeposu.ayarla({ sohbetId: etkin.id, saltOkunur: sonuc.read_only ?? etkin.salt,
      dokum: sonuc.mesajlar.map(m => ({ role: m.rol, content: m.icerik })) })
    return gecmisOgeleri(sonuc.mesajlar, { geriBildirim: !(sonuc.read_only ?? etkin.salt), ogrenci })
  }, [user?.email, ogrenci])
```
`tedyChatConfig`'e `gecmisYukle` verilir. `gonder` yeni sohbet açtığında `etkinSohbetiYaz(user?.email, { id: sohbetId, salt: false })` çağırır.

`props`'a:
```tsx
    renderWriteableElements: {
      ...oncekiYuvalar,
      historyPanelElement: <GecmisPaneli depo={sohbet} ogrenci={ogrenci} inst={() => instance.current} ogretmenSec={ogretmen.sec} />,
    },
    renderCustomRequestFooter: (_slot, mesaj) => <IstekEkleri mesajId={mesaj.id} />,
```
`IstekEkleri` (aynı dosyada):
```tsx
function IstekEkleri({ mesajId }: { mesajId?: string }) {
  const ekler = useAsistanDurumu(d => (mesajId ? d.ekGoruntuleri[mesajId] : undefined))
  const salt = useAsistanDurumu(d => d.saltOkunur)
  const yukleniyor = useAsistanDurumu(d => d.yukleniyor)
  const { data } = useApi<{ homework: HomeworkItem[] }>('/api/homework', { homework: [] })
  if (!ekler?.length) return null
  return <>{ekler.map(ek => <YuklenenEk key={ek.id} ek={ek} odevler={acikOdevler(data.homework)} saltOkunur={salt} disabled={yukleniyor} />)}</>
}
```
`acikOdevler` eski bileşendeki `odevSecenekleri` süzgecinin aynısıdır; `dashboard/src/asistan/odevler.ts`'e taşınır ve Görev 16'da ödev seçici de onu kullanır:
```ts
import type { HomeworkItem } from '../types'
const KAPALI = new Set(['yaptı', 'yapti', 'yapmadı', 'yapmadi', 'eksik'])
export function acikOdevler(liste: HomeworkItem[]): HomeworkItem[] {
  return (liste || []).filter(hw => hw.homework_key && !KAPALI.has((hw['Ödev Durumu'] || '').toLocaleLowerCase('tr-TR'))).slice(0, 20)
}
```

`onBeforeRender` içinde:
```tsx
      inst.on([
        { type: 'history:newChat' as never, handler: () => void yeniSohbet(inst, sohbetRef.current) },
        { type: 'restartConversation' as never, handler: () => void yeniSohbet(inst, sohbetRef.current) },
      ])
      if (asistanDeposu.al().saltOkunur) inst.updateInputIsDisabled(true)
```

- [ ] **Step 4: Geç ve commit**

Run: `cd dashboard && npx tsc -b && npm run build:carbon-ai >/dev/null && env -u ANTHROPIC_API_KEY npx playwright test carbon-asistan-sohbet carbon-asistan-cekirdek --reporter=list` → PASS (11 test).

```bash
git add dashboard/src/asistan dashboard/src/hooks/useSohbetler.ts dashboard/src/components/SohbetListesi.tsx dashboard/tests/e2e/carbon-asistan-sohbet.spec.ts
git commit -m "feat(asistan): Carbon geçmiş paneli, ortak etkin sohbet, salt okunur aile

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 16: Giriş çevresi — ek çipleri, ödev seçici, mikrofon, çalışma planı, sürükle/yapıştır

Carbon'un yükleme düğmesi kapalıdır (`upload.isOn: false`, spec güncellemesi): çipteki Türkçe hata cümleleri, 4 dosya sınırı, "Bu ödeve bağla" ve kamera seçimi bugünkü davranışıyla giriş üstü yuvada kalır.

**Files:**
- Create: `dashboard/src/asistan/ekler.ts` (yükleme, ekleme, ödeve bağlama — eski `yukleBir`/`ekle`/`odeveBagla`'nın depo üzerinde çalışan hâli)
- Create: `dashboard/src/asistan/GirisEkleri.tsx` (`beforeInputElement`)
- Create: `dashboard/src/asistan/GirisDugmeleri.tsx` (`promptLineSendButtonStart`: mikrofon, Çalışma Planı)
- Create: `dashboard/src/asistan/SesOnayi.tsx` (aile notu, mikrofon onayı, ses hatası — sayfa ve panel ortak)
- Modify: `dashboard/src/asistan/useAsistanSohbeti.tsx` (yuvalar, sürükle/yapıştır dinleyicisi, mikrofon onay modalı)
- Create: `dashboard/tests/e2e/carbon-asistan-giris.spec.ts`

**Interfaces:**
- Consumes: `asistanDeposu` (`cipler`, `odevKey`), `acikOdevler` (Görev 15), `YuklemeAlani`, `soruyuYeniden`.
- Produces: `dosyalariEkle(files: File[]): void`, `cipKaldir(yerel: string): void`, `odeveBagla(yerel: string): Promise<void>` (`ekler.ts`).

- [ ] **Step 1: e2e testleri** — eski `asistan-yukleme.spec.ts` (10), `asistan-ses.spec.ts` (5), `homework-docs.spec.ts` "the assistant can be aimed at one homework", `photo-homework.spec.ts` "an uploaded document binds to the selected homework explicitly" aynı adlarla taşınır (Görev 19 seçici tablosu). `#ac-input` yerine `soruAlani(page)`; `fill` Carbon'un düzenleyicisinde çalışır. "chat sends ekler and the plan button does not" testi plan düğmesini `page.getByRole('button', { name: 'Çalışma Planı' })` ile bulur.

- [ ] **Step 2: Ek mantığı**

`dashboard/src/asistan/ekler.ts`:
```ts
import { asistanDeposu } from './asistanDeposu.ts'
import type { Cip } from './asistanDeposu.ts'

const guncelle = (yerel: string, p: Partial<Cip>) =>
  asistanDeposu.ayarla({ cipler: asistanDeposu.al().cipler.map(c => (c.yerel === yerel ? { ...c, ...p } : c)) })

async function yukleBir(yerel: string, file: File) {
  const body = new FormData()
  body.append('dosya', file)
  try {
    const res = await fetch('/api/assistant/uploads', { method: 'POST', credentials: 'include', body })
    let p: { error?: unknown; id?: unknown; ad?: unknown; tur?: unknown } = {}
    try { p = await res.json() } catch { p = {} }
    if (!res.ok || typeof p.id !== 'string') {
      guncelle(yerel, { yukleniyor: false, hata: typeof p.error === 'string' ? p.error : 'Dosya yüklenemedi.' }); return
    }
    guncelle(yerel, { yukleniyor: false, id: p.id, ad: typeof p.ad === 'string' ? p.ad : undefined, tur: typeof p.tur === 'string' ? p.tur : undefined })
  } catch { guncelle(yerel, { yukleniyor: false, hata: 'Dosya yüklenemedi.' }) }
}

export function dosyalariEkle(files: File[]) {
  const d = asistanDeposu.al()
  if (!files.length || d.saltOkunur || d.yukleniyor) return
  let yer = 4 - d.cipler.filter(c => c.yukleniyor || c.id).length
  const yeni: Cip[] = []
  const yuklenecek: [string, File][] = []
  for (const file of files) {
    const yerel = crypto.randomUUID()
    if (yer > 0) { yer -= 1; yeni.push({ yerel, ad: file.name, yukleniyor: true }); yuklenecek.push([yerel, file]) }
    else yeni.push({ yerel, ad: file.name, hata: 'Bir mesaja en fazla 4 dosya eklenebilir.' })
  }
  asistanDeposu.ayarla({ cipler: [...d.cipler, ...yeni] })
  for (const [yerel, file] of yuklenecek) void yukleBir(yerel, file)
}

export const cipKaldir = (yerel: string) =>
  asistanDeposu.ayarla({ cipler: asistanDeposu.al().cipler.filter(c => c.yerel !== yerel) })

export async function odeveBagla(yerel: string) {
  const d = asistanDeposu.al()
  const cip = d.cipler.find(c => c.yerel === yerel)
  if (!cip?.id || !d.odevKey || cip.baglaniyor || cip.baglandi) return
  guncelle(yerel, { baglaniyor: true, hata: undefined })
  try {
    const res = await fetch(`/api/assistant/uploads/${cip.id}/odeve-bagla`, { method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ anahtar: d.odevKey }) })
    const p = await res.json()
    if (!res.ok) throw new Error(p.error || 'Belge ödeve bağlanamadı.')
    guncelle(yerel, { baglaniyor: false, baglandi: true })
    window.dispatchEvent(new CustomEvent('tedy:homework-updated'))
  } catch (e) { guncelle(yerel, { baglaniyor: false, hata: e instanceof Error ? e.message : 'Belge ödeve bağlanamadı.' }) }
}
```

- [ ] **Step 3: Yuva bileşenleri**

`dashboard/src/asistan/GirisEkleri.tsx` — eski `AssistantChat.tsx`'in çip listesi (`<ul className="ac__ekler">` … ) ve `Select id="ac-odev"` bloğunun **aynısı**, durumu depodan okuyarak:
```tsx
import { Button, Select, SelectItem } from '@carbon/react'
import { Close } from '@carbon/icons-react'
import YuklemeAlani from '../components/YuklemeAlani'
import { useApi } from '../hooks/useApi'
import type { HomeworkItem } from '../types'
import { asistanDeposu, useAsistanDurumu } from './asistanDeposu.ts'
import { cipKaldir, dosyalariEkle, odeveBagla } from './ekler.ts'
import { acikOdevler } from './odevler.ts'

const TUR: Record<string, string> = { gorsel: 'Görsel', pdf: 'PDF', docx: 'Word', txt: 'Metin' }

export default function GirisEkleri() {
  const cipler = useAsistanDurumu(d => d.cipler)
  const odevKey = useAsistanDurumu(d => d.odevKey)
  const salt = useAsistanDurumu(d => d.saltOkunur)
  const yukleniyor = useAsistanDurumu(d => d.yukleniyor)
  const { data } = useApi<{ homework: HomeworkItem[] }>('/api/homework', { homework: [] })
  if (salt) return <p className="ac__aile-notu">Bu sohbet salt okunur.</p>
  return <div className="asistan__giris-ekleri">
    {cipler.length > 0 && <ul className="ac__ekler">{cipler.map(c => <li key={c.yerel} className="ac__ek">
      {c.id && c.tur === 'gorsel' && <img className="ac__ek-onizleme" src={`/api/assistant/uploads/${c.id}`} alt="Yüklenen görsel" />}
      <span>{c.ad}</span>{c.tur && TUR[c.tur] ? <span>{TUR[c.tur]}</span> : null}{c.yukleniyor ? <span>Yükleniyor</span> : null}
      {c.id && c.tur !== 'gorsel' && <Button kind="ghost" size="sm" disabled={yukleniyor || !odevKey || c.baglaniyor || c.baglandi}
        onClick={() => void odeveBagla(c.yerel)}>{c.baglandi ? 'Ödeve bağlandı' : c.baglaniyor ? 'Bağlanıyor…' : 'Bu ödeve bağla'}</Button>}
      {c.hata ? <p role="alert" className="ac__ek-hata">{c.hata}</p> : null}
      <button type="button" className="ac__ek-kaldir" aria-label={`Kaldır: ${c.ad}`} disabled={yukleniyor}
        onClick={() => cipKaldir(c.yerel)}><Close size={16} aria-hidden /></button>
    </li>)}</ul>}
    <div className="asistan__giris-satir">
      <YuklemeAlani onDosyalar={dosyalariEkle} disabled={yukleniyor} />
      <Select id="ac-odev" className="ac__odev" labelText="Ödev" value={odevKey} disabled={yukleniyor}
        onChange={e => asistanDeposu.ayarla({ odevKey: e.target.value })}>
        <SelectItem value="" text="Seçilmedi — genel soru" />
        {acikOdevler(data.homework).map(hw => {
          const ad = `${hw.normalized_course || hw['Ders Adı']} — ${hw['Ödev Başlığı']}`
          return <SelectItem key={hw.homework_key} value={hw.homework_key || ''} text={ad.length > 80 ? `${ad.slice(0, 79)}…` : ad} />
        })}
      </Select>
    </div>
  </div>
}
```

`dashboard/src/asistan/GirisDugmeleri.tsx`:
```tsx
import { IconButton } from '@carbon/react'
import { CalendarHeatMap, Microphone } from '@carbon/icons-react'
import type { ChatInstance } from '@carbon/ai-chat'
import { useAsistanDurumu } from './asistanDeposu.ts'
import { soruyuYeniden } from './useAsistanSohbeti.tsx'

export default function GirisDugmeleri({ inst, mikrofon }: { inst: () => ChatInstance | null; mikrofon: { var: boolean; dinliyor: boolean; bas: () => void } }) {
  const salt = useAsistanDurumu(d => d.saltOkunur)
  const yukleniyor = useAsistanDurumu(d => d.yukleniyor)
  if (salt) return null
  return <>
    {mikrofon.var && <IconButton kind="ghost" size="sm" label={mikrofon.dinliyor ? 'Dinlemeyi bitir' : 'Sesle sor'}
      disabled={yukleniyor} onClick={mikrofon.bas}><Microphone /></IconButton>}
    <IconButton kind="ghost" size="sm" label="Çalışma Planı" disabled={yukleniyor} onClick={() => {
      const i = inst(); const metin = i?.getState().input.rawValue.trim() ?? ''
      if (i && metin) { i.input.updateRawValue(() => ''); void soruyuYeniden(i, metin, { plan: true }) }
    }}><CalendarHeatMap /></IconButton>
  </>
}
```

`useAsistanSohbeti.tsx` `renderWriteableElements`'a:
```tsx
      beforeInputElement: <GirisEkleri />,
      promptLineSendButtonStart: <GirisDugmeleri inst={() => instance.current}
        mikrofon={{ var: ses.mikrofonVar, dinliyor: ses.dinliyor, bas: ses.mikrofon }} />,
```
ve kancanın döndürdüğü `sesOnay = { acik: ses.onayAcik, onayla: ses.onayla, vazgec: ses.vazgec, hata: ses.hata }`. Sayfa ve panel aynı bileşeni çizer — `dashboard/src/asistan/SesOnayi.tsx`:
```tsx
import { Modal } from '@carbon/react'
import { useAsistanDurumu } from './asistanDeposu.ts'

export default function SesOnayi({ onay }: { onay: { acik: boolean; onayla: () => void; vazgec: () => void; hata: string | null } }) {
  const ogrenci = useAsistanDurumu(d => d.okur === 'ogrenci')
  return <>
    {ogrenci && <p className="asistan__aile-notu">Sohbetlerini ailen de görebilir.</p>}
    {onay.hata && <p role="alert" className="ac__ses-hata">{onay.hata}</p>}
    <Modal open={onay.acik} modalHeading="Mikrofon" primaryButtonText="Onayla" secondaryButtonText="Vazgeç"
      onRequestSubmit={onay.onayla} onRequestClose={onay.vazgec} onSecondarySubmit={onay.vazgec}>
      <p>Chrome ve Android'de konuşma tanıma sesi Google'a gönderir.</p>
    </Modal>
  </>
}
```
`AsistanSayfasi.tsx`'teki `{okur === 'ogrenci' && <p className="asistan__aile-notu">…}` satırı `<SesOnayi onay={sesOnay} />` ile değiştirilir (`const { props, ogretmen, ogretmenSec, sesOnay } = useAsistanSohbeti(…)`).

Sürükle/yapıştır (eski `onDrop` ve `paste` dinleyicisi): `AsistanSayfasi`'nın kökünde
```tsx
  useEffect(() => {
    const el = kok.current
    if (!el) return
    const yapistir = (e: ClipboardEvent) => { const f = e.clipboardData?.files; if (f?.length) { e.preventDefault(); dosyalariEkle([...f]) } }
    const birak = (e: DragEvent) => { if (e.dataTransfer?.files.length) { e.preventDefault(); dosyalariEkle([...e.dataTransfer.files]) } }
    const uzerinde = (e: DragEvent) => e.preventDefault()
    el.addEventListener('paste', yapistir, true); el.addEventListener('drop', birak, true); el.addEventListener('dragover', uzerinde)
    return () => { el.removeEventListener('paste', yapistir, true); el.removeEventListener('drop', birak, true); el.removeEventListener('dragover', uzerinde) }
  }, [])
```
(Yakalama evresi: Carbon'un düzenleyicisi olayı gölge kökte işlemeden önce dosyalar alınır; düz metin yapıştırma dokunulmadan geçer.)

- [ ] **Step 4: Geç ve commit**

Run: `cd dashboard && npx tsc -b && npm run lint && npm run build:carbon-ai >/dev/null && env -u ANTHROPIC_API_KEY npx playwright test carbon-asistan-giris --reporter=list` → PASS.

```bash
git add dashboard/src/asistan dashboard/tests/e2e/carbon-asistan-giris.spec.ts
git commit -m "feat(asistan): ek çipleri, ödev seçici, mikrofon ve plan düğmesi Carbon girişinde

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 17: Öğretmen modu renkleri, zengin cevap görünümü, görsel referanslar

**Files:**
- Create: `dashboard/src/asistan/ogretmenRenkleri.ts`
- Modify: `dashboard/src/asistan/AsistanSayfasi.scss`, `AsistanSayfasi.tsx`
- Create: `dashboard/tests/e2e/carbon-asistan-ogretmen.spec.ts`, `carbon-asistan-ogretmen-gorsel.spec.ts`, `carbon-asistan-zengin-cevap.spec.ts`, `carbon-asistan-cevap-bicimi.spec.ts` (eski dosyalardan, aynı test adları)

**Interfaces:**
- Produces: `ogretmenDegiskenleri(aile: SubjectFamily | null): Record<string, string>` — Carbon AI Chat köküne yazılacak CSS özel özellikleri.

- [ ] **Step 1: Renk eşlemesi testi**

`dashboard/tests/ogretmen-renkleri.test.ts`:
```ts
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { ogretmenDegiskenleri } from '../src/asistan/ogretmenRenkleri.ts'

test('Genel modda hiçbir değişken yazılmaz', () => assert.deepEqual(ogretmenDegiskenleri(null), {}))
test('öğretmen modunda düğme, kenar ve balon aile rol token’larına bağlanır', () => {
  assert.deepEqual(ogretmenDegiskenleri('blue'), {
    '--cds-button-primary': 'var(--ted-subject-accent)',
    '--cds-button-primary-hover': 'var(--ted-subject-text)',
    '--cds-chat-bubble-user': 'var(--ted-subject-panel)',
    '--cds-chat-bubble-user-text': 'var(--ted-subject-text)',
  })
})
```
(Adlar `@carbon/ai-chat-components` 1.12.0 stillerinde geçen adlardır: gönder düğmesi `--cds-button-primary(-hover)`, okurun balonu `--cds-chat-bubble-user(-text)`. Gölge köke geçtikleri Görev 1'in 3. ölçümüyle doğrulanır. `--ted-subject-*` token'ları `theme/_subjects.scss`'ten gelir, eski `.ac[data-ogretmen]` kuralının rolleri.)

- [ ] **Step 2: Uygula**

`dashboard/src/asistan/ogretmenRenkleri.ts`:
```ts
import type { SubjectFamily } from '../theme/subjects'

/** Öğretmen modunda ders rengi Carbon AI Chat'e CSS özel özellikleriyle geçer; marka bandı değişmez.
 *  Değerler aile sınıfının (`ted-subject--<aile>`) tanımladığı rol token'larıdır, el yazması renk yok. */
export function ogretmenDegiskenleri(aile: SubjectFamily | null): Record<string, string> {
  if (!aile) return {}
  return {
    '--cds-button-primary': 'var(--ted-subject-accent)',
    '--cds-button-primary-hover': 'var(--ted-subject-text)',
    '--cds-chat-bubble-user': 'var(--ted-subject-panel)',
    '--cds-chat-bubble-user-text': 'var(--ted-subject-text)',
  }
}
```
`AsistanSayfasi.tsx`'te `<ChatCustomElement … style={ogretmenDegiskenleri(secili?.renk_ailesi ?? null) as CSSProperties} />` ve `AsistanSayfasi.scss` sonuna:
```scss
// Öğretmen modunda panelin üst kenarı ders rengiyle (eski .ac[data-ogretmen] kuralı).
.asistan[data-ogretmen]:not([data-ogretmen='genel']) .asistan__sohbet {
  border-block-start: 0.25rem solid var(--ted-subject-accent);
}

@media (prefers-reduced-motion: reduce) {
  .asistan__sohbet, .asistan__sohbet * { animation: none !important; transition: none !important; }
}

@media (forced-colors: active) {
  .asistan__sohbet { border: 1px solid CanvasText; }
}
```

- [ ] **Step 3: Görsel ve davranış testlerini taşı**

Eski `asistan-ogretmen.spec.ts` (11), `asistan-ogretmen-gorsel.spec.ts` (4 test: her mod × 1440/390 ekran görüntüsü + axe + IBM), `asistan-zengin-cevap.spec.ts` (5), `asistan-cevap-bicimi.spec.ts` (3) aynı adlarla `carbon-asistan-*.spec.ts` dosyalarına taşınır (Görev 19 seçici tablosu). Ekran görüntüsü referansları **yeniden çekilir**:
```bash
cd dashboard && npm run build:carbon-ai >/dev/null
env -u ANTHROPIC_API_KEY npx playwright test carbon-asistan-ogretmen-gorsel carbon-asistan-zengin-cevap carbon-asistan-cevap-bicimi --update-snapshots
```
Sonra her yeni PNG Read ile açılır ve şu sorulara bakılır: ders rengi gönder düğmesinde mi, bant lacivert mi, kutular etiketli mi, formül çizili mi, tablo sütun dışına taşıyor mu. Bakılmadan referans commit'lenmez.

- [ ] **Step 4: Geç ve commit**

Run: `cd dashboard && node --test tests/ogretmen-renkleri.test.ts && env -u ANTHROPIC_API_KEY npx playwright test carbon-asistan-ogretmen carbon-asistan-zengin-cevap carbon-asistan-cevap-bicimi --reporter=list` → PASS.

```bash
git add dashboard/src/asistan dashboard/tests/ogretmen-renkleri.test.ts dashboard/tests/e2e/carbon-asistan-ogretmen*.ts dashboard/tests/e2e/carbon-asistan-zengin-cevap* dashboard/tests/e2e/carbon-asistan-cevap-bicimi*
git commit -m "feat(asistan): öğretmen modu ders rengi Carbon AI Chat'te; görsel referanslar

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 18: Başlatıcı, sayfa bağlamı, sayfaya özel hızlı sorular, telefon sekmesi, tam ekran

Spec §4.

**Files:**
- Create: `dashboard/src/asistan/sayfaBaglami.ts` (yol → sayfa adı; öğe bağlamı deposu)
- Create: `dashboard/src/asistan/sayfaSorulari.ts`
- Create: `dashboard/src/asistan/AsistanBaslatici.tsx` (küçük; Carbon'u tembel yükler)
- Create: `dashboard/src/asistan/AsistanPaneli.tsx` (tembel parça: `ChatContainer`)
- Modify: `dashboard/src/App.tsx` (başlatıcıyı kabuğa ekle), `dashboard/src/components/BottomNav.tsx` (Asistan sekmesi `?sayfa=`)
- Modify: `dashboard/src/components/HomeworkTracker.tsx`, `CalendarEvents.tsx`, `ExamTimeline.tsx`, `CourseContent.tsx` (açık öğeyi bildir)
- Modify: `dashboard/src/asistan/AsistanSayfasi.tsx` (`?sayfa=` okuma, çip)
- Modify: `dashboard/src/asistan/useAsistanSohbeti.tsx` (`sayfa` parametresi → depo `sayfa`, sayfa soruları)
- Create: `dashboard/src/asistan/BaglamCipi.tsx`, `dashboard/src/asistan/AsistanBaslatici.scss`
- Create: `dashboard/tests/sayfa-baglami.test.ts`, `dashboard/tests/e2e/carbon-asistan-baslatici.spec.ts`

**Interfaces:**
- Produces:
  - `SAYFA_YOLLARI: Record<string, string>` (yol → ad: `'/'`→`bugun`, `'/isler'`→`isler`, `'/dersler'`→`dersler`, `'/notlar'`→`notlar`, `'/takvim'`→`takvim`, `'/takimlar'`→`takimlar`, `'/ilerleme'`→`ilerleme`, `'/duyurular'`→`duyurular`, `'/profil'`→`profil`, `'/moduller'`→`moduller`, `'/kitaplar'`→`kitaplar`, `'/sinavlar'`→`sinavlar`)
  - `SAYFA_ETIKETLERI: Record<string, string>` (arka uçtaki `SAYFA_ADLARI` ile aynı)
  - `sayfaAdi(yol: string): string | null`
  - `baslaticiGorunur(yol: string, rol: UserRole, odak: boolean, genis: boolean): boolean`
  - `acikOgeyiBildir(oge: { tur: 'odev' | 'sinav' | 'etkinlik' | 'ders_haftasi'; id: string; etiket: string } | null): void` ve `useAcikOge()`
  - `sayfaSorulari(ad: string, okur: 'ogrenci' | 'aile'): string[]`

- [ ] **Step 1: Saf testler**

`dashboard/tests/sayfa-baglami.test.ts`:
```ts
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { sayfaAdi, baslaticiGorunur, SAYFA_ETIKETLERI } from '../src/asistan/sayfaBaglami.ts'
import { sayfaSorulari } from '../src/asistan/sayfaSorulari.ts'

test('yoldan sayfa adı; ayrıntı yolları ve bilinmeyenler', () => {
  assert.equal(sayfaAdi('/'), 'bugun')
  assert.equal(sayfaAdi('/isler'), 'isler')
  assert.equal(sayfaAdi('/kitaplar/lotr'), 'kitaplar')
  assert.equal(sayfaAdi('/asistan'), null)
  assert.equal(sayfaAdi('/xyz'), null)
  assert.equal(SAYFA_ETIKETLERI.kitaplar, 'Tedy Books')
})

test('başlatıcı nerede görünür', () => {
  assert.equal(baslaticiGorunur('/isler', 'full', false, true), true)
  for (const yol of ['/asistan', '/moduller/kesir/v2', '/moduller/taslak/abc', '/kitaplar/lotr/b01'])
    assert.equal(baslaticiGorunur(yol, 'full', false, true), false, yol)
  assert.equal(baslaticiGorunur('/isler', 'reader', false, true), false)
  assert.equal(baslaticiGorunur('/isler', 'full', true, true), false)
  assert.equal(baslaticiGorunur('/isler', 'full', false, false), false)
  assert.equal(baslaticiGorunur('/moduller', 'full', false, true), true)
})

test('her sayfanın iki hitapta 2-3 sorusu var', () => {
  for (const ad of Object.keys(SAYFA_ETIKETLERI)) for (const okur of ['ogrenci', 'aile'] as const) {
    const s = sayfaSorulari(ad, okur)
    assert.ok(s.length >= 2 && s.length <= 3, `${ad}/${okur}`)
  }
  assert.ok(sayfaSorulari('isler', 'aile').every(s => !/\b(başlayayım|yapayım)\b/.test(s)))
})
```

- [ ] **Step 2: Saf modüller**

`dashboard/src/asistan/sayfaBaglami.ts`:
```ts
import { useSyncExternalStore } from 'react'
import type { UserRole } from '../hooks/useAuth'

export const SAYFA_YOLLARI: Record<string, string> = {
  '/': 'bugun', '/isler': 'isler', '/dersler': 'dersler', '/notlar': 'notlar', '/takvim': 'takvim',
  '/takimlar': 'takimlar', '/ilerleme': 'ilerleme', '/duyurular': 'duyurular', '/profil': 'profil',
  '/moduller': 'moduller', '/kitaplar': 'kitaplar', '/sinavlar': 'sinavlar',
}
export const SAYFA_ETIKETLERI: Record<string, string> = {
  bugun: 'Bugün', isler: 'İşler', dersler: 'Dersler', notlar: 'Notlar', takvim: 'Takvim', takimlar: 'Takımlar',
  ilerleme: 'İlerleme', duyurular: 'Duyurular', profil: 'Profil', moduller: 'Modüller', kitaplar: 'Tedy Books', sinavlar: 'Sınavlar',
}
const GIZLI = [/^\/asistan(\/|$)/, /^\/moduller\/taslak\//, /^\/moduller\/[^/]+\/[^/]+$/, /^\/kitaplar\/[^/]+\/[^/]+$/]

export function sayfaAdi(yol: string): string | null {
  if (SAYFA_YOLLARI[yol]) return SAYFA_YOLLARI[yol]
  const kok = `/${yol.split('/')[1] ?? ''}`
  return kok !== '/' && SAYFA_YOLLARI[kok] ? SAYFA_YOLLARI[kok] : null
}

export function baslaticiGorunur(yol: string, rol: UserRole, odak: boolean, genis: boolean): boolean {
  return rol === 'full' && !odak && genis && !GIZLI.some(r => r.test(yol)) && sayfaAdi(yol) !== null
}

export interface AcikOge { tur: 'odev' | 'sinav' | 'etkinlik' | 'ders_haftasi'; id: string; etiket: string }
let acik: AcikOge | null = null
const dinleyenler = new Set<() => void>()
/** Sayfalar açık öğeyi buraya bildirir (ödev penceresi, seçili sınav/etkinlik, ders içeriği haftası). */
export function acikOgeyiBildir(oge: AcikOge | null) { acik = oge; dinleyenler.forEach(f => f()) }
export function useAcikOge(): AcikOge | null {
  return useSyncExternalStore(f => { dinleyenler.add(f); return () => { dinleyenler.delete(f) } }, () => acik)
}
```

`dashboard/src/asistan/sayfaSorulari.ts`:
```ts
const S: Record<string, { ogrenci: string[]; aile: string[] }> = {
  bugun: { ogrenci: ['Bugün neye öncelik vermeliyim?', 'Yarın için ne hazırlamalıyım?'], aile: ['Işık bugün neye öncelik vermeli?', 'Işık yarın için ne hazırlamalı?'] },
  isler: { ogrenci: ['Bugün hangisinden başlayayım?', 'Teslimi en yakın ödev hangisi?', 'Bu ödeve nasıl başlarım?'], aile: ['Işık bugün hangi işten başlamalı?', 'Teslimi en yakın ödev hangisi?', 'Bu ödevde Işık’a nasıl yardım edebilirim?'] },
  dersler: { ogrenci: ['Bu haftaki konuyu kısaca anlat', 'Bu hafta hangi derslerde yeni konu var?'], aile: ['Bu haftaki konuları kısaca özetler misiniz?', 'Işık bu hafta hangi derslerde yeni konuya geçiyor?'] },
  notlar: { ogrenci: ['Hangi derste zorlanıyorum?', 'Notlarımı nasıl yükseltebilirim?'], aile: ['Işık hangi derste zorlanıyor?', 'Işık’ın notları için neye odaklanmalıyız?'] },
  takvim: { ogrenci: ['Bu haftam nasıl görünüyor?', 'Yaklaşan bir sınav var mı?'], aile: ['Işık’ın bu haftası nasıl görünüyor?', 'Yaklaşan bir sınav var mı?'] },
  takimlar: { ogrenci: ['Takım etkinliklerim ne zaman?', 'Bu hafta takımda ne var?'], aile: ['Işık’ın takım etkinlikleri ne zaman?', 'Bu hafta takımda ne var?'] },
  ilerleme: { ogrenci: ['Bu hafta neler çalıştım?', 'Zayıf olduğum konular hangileri?'], aile: ['Işık bu hafta neler çalıştı?', 'Işık’ın zayıf konuları hangileri?'] },
  duyurular: { ogrenci: ['Beni ilgilendiren bir duyuru var mı?', 'Son duyuruları özetle'], aile: ['Bizi ilgilendiren bir duyuru var mı?', 'Son duyuruları özetler misiniz?'] },
  profil: { ogrenci: ['Ders programımı özetle', 'Bu dönem hangi derslerim var?'], aile: ['Işık’ın ders programını özetler misiniz?', 'Bu dönem hangi dersleri var?'] },
  moduller: { ogrenci: ['Hangi modülle çalışmalıyım?', 'Yarım kalan bir modülüm var mı?'], aile: ['Işık hangi modülle çalışmalı?', 'Yarım kalan bir modülü var mı?'] },
  kitaplar: { ogrenci: ['Okuduğum bölümü özetle', 'Bu bölümdeki zor kelimeler neler?'], aile: ['Işık’ın okuduğu bölümü özetler misiniz?', 'Bu bölümde konuşabileceğimiz sorular neler?'] },
  sinavlar: { ogrenci: ['Yaklaşan sınavım için plan yap', 'Bu sınavın konuları neler?'], aile: ['Yaklaşan sınav için Işık’a plan yapar mısınız?', 'Bu sınavın konuları neler?'] },
}
export function sayfaSorulari(ad: string, okur: 'ogrenci' | 'aile'): string[] { return S[ad]?.[okur] ?? [] }
```

Run: `cd dashboard && node --test tests/sayfa-baglami.test.ts` → PASS.

- [ ] **Step 3: e2e testleri**

`dashboard/tests/e2e/carbon-asistan-baslatici.spec.ts`:
```ts
import { test, expect } from '@playwright/test'
import { PAYLOAD, cevapla, gonderDugmesi } from './_asistan-carbon'
import { mock, FULL } from './_audit-fixtures'

const baslatici = (page: import('@playwright/test').Page) => page.getByRole('button', { name: 'Sohbet penceresini aç' })

test('İşler sayfasında başlatıcı, çip ve sayfa soruları; istek sayfa bağlamını taşır, çip bir kez', async ({ page }) => {
  await mock(page, FULL)
  const istekler = await cevapla(page, PAYLOAD({ answer: 'Önce matematikten başla.' }))
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/isler')
  await baslatici(page).click()
  await expect(page.getByText('Bu sayfa: İşler')).toBeVisible()
  await page.getByRole('button', { name: 'Işık bugün hangi işten başlamalı?' }).click()
  await expect(page.getByText('Önce matematikten başla.')).toBeVisible()
  expect(istekler[0]).toMatchObject({ sayfa: { ad: 'isler' } })
  await expect(page.getByText('Bu sayfa: İşler')).toHaveCount(0)
  await page.getByRole('textbox', { name: 'Sorunu yaz' }).fill('Başka soru')
  await gonderDugmesi(page).click()
  await expect.poll(() => istekler.length).toBe(2)
  expect(istekler[1]).not.toHaveProperty('sayfa')
})

test('çip kaldırılınca istek bağlamsız, sorular mod sorularına döner', async ({ page }) => {
  await mock(page, FULL)
  const istekler = await cevapla(page, PAYLOAD())
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/takvim')
  await baslatici(page).click()
  await page.getByRole('button', { name: 'Bağlamı kaldır: Takvim' }).click()
  await expect(page.getByRole('button', { name: 'Işık bugün neye öncelik vermeli?' })).toBeVisible()
  await page.getByRole('textbox', { name: 'Sorunu yaz' }).fill('Soru')
  await gonderDugmesi(page).click()
  await expect.poll(() => istekler.length).toBe(1)
  expect(istekler[0]).not.toHaveProperty('sayfa')
})

test('başlatıcının gizli olduğu yerler: asistan, odak modu, telefon', async ({ page }) => {
  await mock(page, FULL)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/asistan')
  await expect(baslatici(page)).toHaveCount(0)
  await page.goto('/isler')
  await expect(baslatici(page)).toBeVisible()
  await page.evaluate(() => localStorage.setItem('tedy-focus-mode', 'true'))
  await page.reload()
  await expect(baslatici(page)).toHaveCount(0)
  await page.evaluate(() => localStorage.removeItem('tedy-focus-mode'))
  await page.setViewportSize({ width: 390, height: 844 })
  await page.reload()
  await expect(baslatici(page)).toHaveCount(0)
})

test('telefonda Asistan sekmesi sayfa bağlamını taşır; bilinmeyen ad sessizce yok sayılır', async ({ page }) => {
  await mock(page, FULL)
  const istekler = await cevapla(page, PAYLOAD())
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/notlar')
  await page.getByRole('navigation', { name: 'Ana gezinme' }).getByRole('link', { name: 'Asistan' }).click()
  await expect(page).toHaveURL(/\/asistan\?sayfa=notlar$/)
  await expect(page.getByText('Bu sayfa: Notlar')).toBeVisible()
  await page.goto('/asistan?sayfa=xyz')
  await expect(page.getByText(/Bu sayfa:/)).toHaveCount(0)
  await page.getByRole('textbox', { name: 'Sorunu yaz' }).fill('Soru')
  await page.getByRole('button', { name: 'Gönder', exact: true }).click()
  await expect.poll(() => istekler.length).toBe(1)
  expect(istekler[0]).not.toHaveProperty('sayfa')
})

test('başlatıcıda sorulan soru sayfaya geçince bir kez görünür', async ({ page }) => {
  await mock(page, FULL)
  let kayitli: unknown[] = []
  await page.route('**/api/assistant/sohbetler', r => r.request().method() === 'POST'
    ? r.fulfill({ json: { id: 'ab'.repeat(16), ogretmen: 'genel', baslik: '' } }) : r.fulfill({ json: { sohbetler: [] } }))
  await page.route(`**/api/assistant/sohbetler/${'ab'.repeat(16)}`, r => r.fulfill({ json: {
    sohbet: { id: 'ab'.repeat(16), baslik: 'Tek soru', ogretmen: 'genel' }, mesajlar: kayitli } }))
  await cevapla(page, PAYLOAD({ answer: 'Tek cevap.', mesaj_id: 'c'.repeat(32) }))
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/isler')
  await baslatici(page).click()
  await page.getByRole('textbox', { name: 'Sorunu yaz' }).fill('Tek soru')
  await gonderDugmesi(page).click()
  await expect(page.getByText('Tek cevap.')).toBeVisible()
  kayitli = [
    { id: 'd'.repeat(32), rol: 'user', icerik: 'Tek soru', atiflar_json: '[]', ekler_json: '[]', zaman: '2026-10-08T09:00:00Z' },
    { id: 'c'.repeat(32), rol: 'assistant', icerik: 'Tek cevap.', atiflar_json: '[]', ekler_json: '[]', zaman: '2026-10-08T09:00:02Z' },
  ]
  await page.goto('/asistan')
  await expect(page.getByText('Tek cevap.')).toHaveCount(1)
  await expect(page.getByText('Tek soru', { exact: true })).toHaveCount(1)   // liste bu testte boş: yalnız mesaj balonu
})

test('Tam ekran paneli pencereyi kaplatır, Küçült geri alır', async ({ page }) => {
  await mock(page, FULL)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/isler')
  await baslatici(page).click()
  await page.getByRole('button', { name: 'Tam ekran' }).click()
  const kutu = await page.locator('.asistan-paneli').boundingBox()
  expect(kutu!.width).toBeGreaterThan(1400)
  await page.getByRole('button', { name: 'Küçült' }).click()
  expect((await page.locator('.asistan-paneli').boundingBox())!.width).toBeLessThan(800)
})

test('başlatıcı düğmesi Bugün’ün ilk yüklemesine Carbon AI Chat getirmez', async ({ page }) => {
  await mock(page, FULL)
  const yuklenen: string[] = []
  page.on('response', r => { if (r.url().includes('/assets/') && r.url().endsWith('.js')) yuklenen.push(r.url()) })
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/')
  await expect(baslatici(page)).toBeVisible()
  const govdeler = await Promise.all(yuklenen.map(u => page.request.get(u).then(r => r.text())))
  expect(govdeler.some(g => g.includes('cds-aichat-container'))).toBe(false)
})
```

- [ ] **Step 4: Başlatıcı ve panel**

`dashboard/src/asistan/AsistanBaslatici.tsx` (ilk yükleme parçasında; Carbon'u içe aktarmaz):
```tsx
import { lazy, Suspense, useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Button } from '@carbon/react'
import { Chat } from '@carbon/icons-react'
import { useFocusMode } from '../contexts/focusMode'
import type { UserRole } from '../hooks/useAuth'
import { baslaticiGorunur } from './sayfaBaglami.ts'

const AsistanPaneli = lazy(() => import('./AsistanPaneli.tsx'))
const GENIS = '(min-width: 42rem)'   // Carbon md, 672 px

export default function AsistanBaslatici({ rol }: { rol: UserRole }) {
  const { pathname } = useLocation()
  const { focusMode } = useFocusMode()
  const [genis, setGenis] = useState(() => window.matchMedia(GENIS).matches)
  const [acildi, setAcildi] = useState(false)
  useEffect(() => {
    const mq = window.matchMedia(GENIS); const f = () => setGenis(mq.matches)
    mq.addEventListener('change', f); return () => mq.removeEventListener('change', f)
  }, [])
  if (!baslaticiGorunur(pathname, rol, focusMode, genis)) return null
  if (!acildi) {
    return <Button className="asistan-baslatici" kind="primary" size="lg" hasIconOnly renderIcon={Chat}
      iconDescription="Sohbet penceresini aç" tooltipPosition="left" onClick={() => setAcildi(true)} />
  }
  return <Suspense fallback={null}><AsistanPaneli /></Suspense>
}
```
(İlk tıklamadan sonra Carbon'un kendi başlatıcısı devralır: `AsistanPaneli` `openChatByDefault: true` ile açılır; kapatılınca Carbon'un başlatıcısı aynı yerde kalır. Erişilebilir ad iki durumda da "Sohbet penceresini aç" — `TURKCE.launcher_isClosed`.)

`dashboard/src/asistan/AsistanPaneli.tsx`:
```tsx
import { useState, type CSSProperties } from 'react'
import { useLocation } from 'react-router-dom'
import { ChatContainer } from '@carbon/ai-chat'
import { Maximize, Minimize } from '@carbon/icons-react'
import { useAsistanSohbeti } from './useAsistanSohbeti.tsx'
import { ogretmenDegiskenleri } from './ogretmenRenkleri.ts'
import { sayfaAdi } from './sayfaBaglami.ts'
import BaglamCipi from './BaglamCipi.tsx'
import SesOnayi from './SesOnayi.tsx'

export default function AsistanPaneli() {
  const { pathname } = useLocation()
  const ad = sayfaAdi(pathname)
  const { props, ogretmen, sesOnay } = useAsistanSohbeti('panel', ad)
  const [tam, setTam] = useState(false)
  const boyut = tam ? { width: '100vw', height: '100dvh', 'max-width': '100vw', 'max-height': '100dvh' } : {}
  return <div className={`asistan-paneli${tam ? ' asistan-paneli--tam' : ''}`}
    style={ogretmenDegiskenleri(ogretmen.secili?.renk_ailesi ?? null) as CSSProperties}>
    <ChatContainer {...props} openChatByDefault
      layout={{ ...props.layout, customProperties: boyut }}
      header={{ ...props.header, actions: [{ text: tam ? 'Küçült' : 'Tam ekran', icon: tam ? Minimize : Maximize, onClick: () => setTam(!tam) }] } as typeof props.header}
      renderWriteableElements={{ ...props.renderWriteableElements, beforeInputElement: <><BaglamCipi />{props.renderWriteableElements?.beforeInputElement}</> }} />
    {/* Sayfadaki gibi: öğrenciye aile notu, mikrofon onayı, ses hatası (Görev 16'daki blok). */}
    <SesOnayi onay={sesOnay} />
  </div>
}
```

`useAsistanSohbeti(bicim, sayfa)` (Görev 11'de `_sayfa` olarak yok sayılan parametre artık kullanılır): `sayfa` verilmişse açılışta (bir `useEffect` içinde) `asistanDeposu.ayarla({ sayfa: { ad, etiket: SAYFA_ETIKETLERI[ad], ...(oge ? { oge: { tur: oge.tur, id: oge.id }, ogeEtiketi: oge.etiket } : {}) } })` (`oge = useAcikOge()`; öğe değişince yeniden yazılır) ve hızlı sorular `sayfa` doluyken `sayfaSorulari(ad, okur)`'dur. `gonder` istekten sonra `sayfa: null` yazar (çip bir kez — Görev 11 kodunda var). Homescreen soruları depo `sayfa`'ya göre yeniden hesaplanır (`useAsistanDurumu(d => d.sayfa)` bağımlılığı).

`dashboard/src/asistan/BaglamCipi.tsx`:
```tsx
import { DismissibleTag } from '@carbon/react'
import { asistanDeposu, useAsistanDurumu } from './asistanDeposu.ts'

export default function BaglamCipi() {
  const sayfa = useAsistanDurumu(d => d.sayfa)
  if (!sayfa) return null
  const metin = `Bu sayfa: ${sayfa.etiket}${sayfa.ogeEtiketi ? ` — ${sayfa.ogeEtiketi}` : ''}`
  return <DismissibleTag type="gray" size="sm" text={metin} dismissTooltipLabel={`Bağlamı kaldır: ${sayfa.etiket}`}
    onClose={() => asistanDeposu.ayarla({ sayfa: null })} />
}
```

`AsistanSayfasi.tsx`: `useSearchParams()` ile `sayfa` okunur; `SAYFA_ETIKETLERI[ad]` yoksa yok sayılır (Review Focus 1); varsa `useAsistanSohbeti('sayfa', ad)` ve `beforeInputElement`'e `<BaglamCipi />`.

`App.tsx` — `<BottomNav …/>` satırının yanına (yalnız bayrak açıkken):
```tsx
      {CARBON_AI_ACIK && !isReader && <AsistanBaslatici rol={user.role} />}
```
`BottomNav.tsx` — Asistan sekmesinin `to`'su:
```tsx
const hedef = (yol: string) => (yol === '/asistan' && CARBON_AI_ACIK && sayfaAdi(pathname) ? `/asistan?sayfa=${sayfaAdi(pathname)}` : yol)
```
ve `<Link to={hedef(r.path)} …>`.

Açık öğe bildirimi (her biri tek satır `useEffect`):
- `HomeworkTracker.tsx`: `useEffect(() => { acikOgeyiBildir(selectedHw?.homework_key ? { tur: 'odev', id: selectedHw.homework_key, etiket: `${selectedHw.normalized_course || selectedHw['Ders Adı']} — ${selectedHw['Ödev Başlığı']}` } : null); return () => acikOgeyiBildir(null) }, [selectedHw])`
- `CalendarEvents.tsx`: `selectedEvent` → `{ tur: 'etkinlik', id: selectedEvent.id, etiket: selectedEvent.title }`
- `ExamTimeline.tsx`: genişletilmiş sınav satırı → `{ tur: 'sinav', id: exam.id, etiket: exam.title }`
- `CourseContent.tsx`: `secilenHafta` → `{ tur: 'ders_haftasi', id: secilenHafta, etiket: secilenHafta }`

`.asistan-baslatici` ve `.asistan-paneli` stilleri (`AsistanSayfasi.scss` değil, kabuk için `dashboard/src/asistan/AsistanBaslatici.scss`): sabit konum `inset-block-end: spacing.$spacing-07; inset-inline-end: spacing.$spacing-07; z-index: 8000`; `.asistan-paneli--tam` `position: fixed; inset: 0; z-index: 9000`.

- [ ] **Step 5: Geç ve commit**

Run: `cd dashboard && npx tsc -b && npm run lint && node --test tests/*.test.ts && npm run build:carbon-ai >/dev/null && env -u ANTHROPIC_API_KEY npx playwright test carbon-asistan-baslatici alt-gezinme odak --reporter=list` → PASS.

```bash
git add dashboard/src dashboard/tests/sayfa-baglami.test.ts dashboard/tests/e2e/carbon-asistan-baslatici.spec.ts
git commit -m "feat(asistan): her sayfada başlatıcı, sayfa bağlamı çipi ve sayfa soruları

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 19: Eski testlerin taşınması ve sayfa bütünlüğü denetimleri

Spec §3'ün bağlayıcı tablosu burada kapanır: eski asistan spec'lerinin **her testi** yeni arayüze karşı aynı adla vardır ya da aşağıda gerekçesiyle değiştirilmiştir. Bu görev bittiğinde eski `asistan-*.spec.ts` / `assistant-*.spec.ts` dosyaları silinir (eski bileşen Görev 21'e kadar kodda kalır ama bayrak açık pakette çizilmez).

**Files:**
- Create: `dashboard/tests/e2e/carbon-asistan-*.spec.ts` (aşağıdaki tablodaki hedefler)
- Delete: `dashboard/tests/e2e/asistan-*.spec.ts`, `assistant-ai.spec.ts`, `assistant-chat.spec.ts`, `assistant-moduller.spec.ts` ve bunların `-snapshots/` dizinleri
- Modify: `photo-homework.spec.ts`, `homework-docs.spec.ts`, `tasarim-denetimi.spec.ts`, `ibm-erisilebilirlik.spec.ts`, `aria-yapisi.spec.ts` (+ `.aria.yml`), `ekran-4k.spec.ts`, `gorunum-kipleri.spec.ts`, `gorsel-regresyon.spec.ts` (+ PNG), `capraz-tarayici.spec.ts`, `dashboard.spec.ts`, `polish.spec.ts`, `d3b-dokunma.spec.ts` — yalnız asistanla ilgili seçiciler
- Modify: `tests/test_pano_tasarim_sistemi.py` (yeni `dashboard/src/asistan/*.scss` dosyalarını kapsasın)

**Seçici çeviri tablosu (her taşınan testte):**

| Eski | Yeni |
|---|---|
| `page.fill('#ac-input', x)` / `getByRole('textbox', { name: 'Sorun' })` | `soruAlani(page).fill(x)` |
| `.ac-msg--assistant … .ac-msg__content` | `page.getByText(<beklenen metin>)` ya da `page.locator('[data-tedy-altbilgi]')` |
| `ThinkingIndicator` metni (`'Müfredat aranıyor'`) | Carbon araç adımı başlığı, aynı metin (`getByText`) |
| `CitationChip` (`button` "1") | Carbon atıf düğmesi + "Kaynak listesini aç veya kapat" |
| `aside[aria-label="Kaynaklar ve çalışma planı"]` | `getByRole('region', { name: 'Çalışma paneli' })` (Kaynaklar düğmesinden sonra) |
| `heading 'Sohbetler'` | Carbon geçmiş paneli içindeki aynı başlık (`SohbetListesi`) |
| telefonda `button 'Sohbetler'` | `button 'Sohbetleri gör'` (Carbon mobil menüsü) |
| `.ac[data-ogretmen]` | `.asistan[data-ogretmen]` |
| `input[name="ac-ogretmen"]` | aynı (OgretmenSecici değişmedi) |

**Test bazında karar (eşdeğer olmayanlar):**

| Eski test | Karar |
|---|---|
| `assistant-chat` "citation chips render inside every markdown block type" ve "…inside bold and italic emphasis, but not inside code spans" | `carbon-asistan-kaynaklar`'da tek test: kutu, liste, tablo hücresi ve vurgu içindeki işaretler metinden çıkar ve her atıf kaynak listesinde görünür; kod aralığındaki `[S1]` metin olarak kalır (Görev 7 `atiflar.test.ts` aralık doğruluğunu sabitler). |
| `assistant-chat` "a citation chip is described by the snippet" | Carbon atıf kartında `text` = snippet; `carbon-asistan-kaynaklar`'da kart metni doğrulanır. |
| `assistant-ai` "the AI aura marks what the model wrote, not what Işık wrote" / "stays off the sources" / "keeps its AI treatment" | Carbon `aiEnabled` gradyanı yalnız asistan tarafında; test aynı adla, Görev 1 Step 4'teki ekran görüntüsünde belirlenen AI sınıfının kullanıcı balonunda olmadığını, cevapta olduğunu doğrular. |
| `assistant-ai` "the assistant stylesheet names no colour of its own" | `dashboard/src/asistan/*.scss` için aynı kural (hex/rgb yok) — `test_pano_tasarim_sistemi.py` kapsamına alınır. |
| `assistant-moduller` "while modul_ara runs, the thinking indicator names it" | Araç adımı "Yayınlanmış modüller aranıyor" görünür. |
| `asistan-ses` "family can read aloud but cannot dictate into a student conversation" | Salt okunur sohbette mikrofon yok (`GirisDugmeleri` `null`), "Sesli oku" var. |
| Diğer bütün testler | Aynı adla, aynı iddialarla; yalnız seçici tablosu uygulanır. |

- [ ] **Step 1: Kalan testleri taşı** — Görev 11–18'de yazılmamış her test için yeni dosyaya aynı adla yaz (`carbon-asistan-<eski ad>.spec.ts`). Her dosyanın başında `import { asistanAc, soruAlani, sor, cevapla, PAYLOAD, sse } from './_asistan-carbon'`.

- [ ] **Step 2: Eşdeğerlik denetimi** — eski ve yeni test adlarını karşılaştır:
```bash
cd dashboard/tests/e2e
eski=$(for f in asistan-*.spec.ts assistant-*.spec.ts; do grep -oE "^test\('[^']+'" $f; done | sort -u)
yeni=$(for f in carbon-asistan-*.spec.ts; do grep -oE "^test\('[^']+'" $f; done | sort -u)
comm -23 <(echo "$eski") <(echo "$yeni")
```
Expected: çıktı yalnız yukarıdaki "Test bazında karar" tablosunda adı geçen testler. Başka bir ad çıkarsa taşınmamış testtir — Step 1'e dön.

- [ ] **Step 3: Eski spec'leri sil**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/carbon-ai/dashboard/tests/e2e
git rm -r -q asistan-*.spec.ts asistan-*-snapshots assistant-ai.spec.ts assistant-chat.spec.ts assistant-moduller.spec.ts
```

- [ ] **Step 4: Sayfa bütünlüğü** — `tasarim-denetimi`, `ibm-erisilebilirlik`, `aria-yapisi`, `ekran-4k`, `gorunum-kipleri`, `gorsel-regresyon`, `capraz-tarayici` yeni pakete karşı koşulur. `/asistan` satırları ve başlatıcı düğmesi yüzünden değişen referanslar yenilenir, **her fark okunur**:
```bash
cd dashboard && npm run build:carbon-ai >/dev/null
env -u ANTHROPIC_API_KEY npx playwright test tasarim-denetimi ibm-erisilebilirlik aria-yapisi ekran-4k gorunum-kipleri gorsel-regresyon --reporter=list
# kırmızıların farkını oku (test-results/*-diff.png), yalnız beklenen değişikliklerse:
env -u ANTHROPIC_API_KEY npx playwright test aria-yapisi gorunum-kipleri gorsel-regresyon --update-snapshots
env -u ANTHROPIC_API_KEY npx playwright test capraz-tarayici --project=webkit --project=firefox --reporter=list
```
Beklenen değişiklik: `/asistan` ekranı (yeni arayüz) ve diğer sayfalarda sağ altta başlatıcı düğmesi. Başka bir sayfada başka bir değişiklik varsa durup nedenini bul.

`ekran-4k`: test ikonları `document.querySelectorAll('svg')` ile toplar; gölge kökteki Carbon AI Chat ikonları bu sorgunun dışında kalır ve test olduğu gibi geçer. Carbon AI Chat'in kendi ölçülerinin 3840 px'te büyüyüp büyümediğine `/asistan` ekran görüntüsüyle bakılır; büyümüyorsa bu, spec'e bilinen boşluk olarak yazılır (Step 6).

- [ ] **Step 5: Lint, Lighthouse, Python**

```bash
cd dashboard && npm run lint && node --test tests/*.test.ts && npm run lhci
cd .. && unshare -rn .venv/bin/python -m pytest -q
```
Expected: lint temiz; Lighthouse erişilebilirlik ≥ 0.95, CLS ≤ 0.1 (performans uyarıdır); bütün pytest yeşil.

- [ ] **Step 6: Spec'e bilinen boşlukları yaz ve commit**

Görev 1 raporunun 5. satırı ve Step 4'teki 4K ikon sınırı spec'in sonuna "## Bilinen boşluklar" başlığıyla yazılır.

```bash
git add -A dashboard/tests tests/test_pano_tasarim_sistemi.py docs/superpowers/specs/2026-10-08-asistan-carbon-ai-chat-design.md
git commit -m "test(asistan): eski asistan testleri yeni arayüze taşındı; sayfa denetimleri ve referanslar

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 20: Yayın — bayrağı canlıda aç (kullanıcı onayıyla)

**Kapı:** Bu görev `main`'e birleştirir ve canlıyı değiştirir. Başlamadan önce kullanıcıya Görev 19'un yeşil özetini (test sayıları, ekran görüntüleri) ver ve **açık onay iste**. Onay yoksa dur.

**Files:**
- Create: `dashboard/.env.production` (`VITE_ASISTAN_CARBON_AI=1`)
- Modify: `CLAUDE.md` (Dashboard bölümüne "Asistan arayüzü (Carbon AI Chat, 2026-10-08)" maddesi)

- [ ] **Step 1: Bayrak commit'i (tek commit, geri dönüş bu commit'in revert'i)**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/carbon-ai
printf 'VITE_ASISTAN_CARBON_AI=1\n' > dashboard/.env.production
git add dashboard/.env.production
git commit -m "feat(asistan): Carbon AI Chat arayüzü canlıda açık

Geri dönüş: bu commit'in revert'i + npm run build + ted-dashboard restart.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 2: CLAUDE.md maddesi** — kısa: arayüzün `dashboard/src/asistan/`'da olduğu, olay eşlemesinin saf ve testli olduğu, `npm run test:birim`, telemetri, bayrak, eski bileşenin Görev 21'e kadar durduğu, ölçülen paket boyutu. Commit.

- [ ] **Step 3: `main`'e birleştir (ana checkout paylaşılır — ataların denetimiyle)**

```bash
cd /mnt/thunderbolt/workspaces/TED
git fetch -q origin
git -C .claude/worktrees/carbon-ai rebase origin/main
cd .claude/worktrees/carbon-ai && unshare -rn ../../../.venv/bin/python -m pytest -q && cd dashboard && npm run build && node --test tests/*.test.ts && cd ..
git push origin HEAD:main   # yalnız fast-forward; reddedilirse yeniden rebase, asla --force
```

- [ ] **Step 4: Canlı derleme ve yeniden başlatma**

```bash
cd /mnt/thunderbolt/workspaces/TED
test "$(git branch --show-current)" = main && git pull --ff-only origin main
cd dashboard && IBM_TELEMETRY_DISABLED=true npm ci && npm run build && cd ..
systemctl --user restart ted-dashboard.service ted-mcp.service
sleep 5; systemctl --user is-active ted-dashboard ted-mcp
curl -s -o /dev/null -w '%{http_code}\n' https://tedy.online/
curl -s http://127.0.0.1:8090/health
```
Expected: `active` ×2, `200`, `{"status":"ok",…}`.

- [ ] **Step 5: Canlı duman testi** — Playwright yerel Chrome kanalıyla `https://tedy.online/asistan` açılır (oturum gerektirir; kullanıcının tarayıcısında yapılmıyorsa bu adım kullanıcıya bırakılır ve böyle söylenir). Bir soru-cevap, başlatıcı İşler'de açılıyor, `journalctl --user -u ted-dashboard --since '-5 min' | grep -iE 'error|traceback'` boş.

- [ ] **Step 6: Kullanıcıya teslim** — ne değişti, nasıl geri alınır (Step 1 commit'inin revert'i), telefonda denemesi istenir; ekran görüntüsü beklenir. Hafızadaki `tedy-asistan-plan-durumu` güncellenir.

---

### Task 21: Eski bileşeni kaldır (birkaç gün sorunsuz kullanımdan sonra, kullanıcının sözüyle)

**Kapı:** Kullanıcı yeni arayüzün birkaç gün sorunsuz çalıştığını onaylamadan başlanmaz.

**Files:**
- Delete: `dashboard/src/components/AssistantChat.tsx`, `AssistantChat.scss`, `CitationChip.tsx`, `ThinkingIndicator` (AssistantChat içinde), artık kullanılmayan `utils/markdown.tsx` sohbet dalı yalnız Books kullanmıyorsa
- Modify: `dashboard/src/App.tsx` (bayrak dalı kalkar), `dashboard/src/asistan/bayrak.ts` ve `.env.*` (silinir), `dashboard/package.json` (`build:carbon-ai` kalkar)

- [ ] **Step 1:** `grep -rn "AssistantChat\|CitationChip\|CARBON_AI_ACIK" dashboard/src` ile kullanımları bul, kaldır.
- [ ] **Step 2:** `npx tsc -b && npm run lint && npm run build && node --test tests/*.test.ts && env -u ANTHROPIC_API_KEY npx playwright test` → hepsi yeşil.
- [ ] **Step 3:** Commit: `refactor(asistan): eski AssistantChat kaldırıldı`; Görev 20 Step 3–4'teki gibi birleştir ve yayınla.

---

## Ek A — `dashboard/src/asistan/dilPaketi.ts` (birebir)

```ts
// Carbon AI Chat'in arayüz metinleri, Türkçe (@carbon/ai-chat 1.22.0 enLanguagePack'in 263 anahtarı).
// Paket güncellenince `node --test tests/dil-paketi.test.ts` eksik anahtarı adıyla söyler.
import type { LanguagePack } from '@carbon/ai-chat'

export const TURKCE: LanguagePack = {
  ai_slug_label: 'Yapay zekâ açıklaması',
  ai_slug_title: 'Bu yanıtları bir yapay zekâ yazıyor',
  ai_slug_description: 'TEDY Asistanı yanıtlarını Claude ile yazar; okul verisi, MEB müfredatı ve ders kitapları kaynak olarak numaralanır. Yapay zekâ yanılabilir — bir şey tuhaf geldiyse kaynağa bak.',
  components_overflow_ariaLabel: 'Seçenek listesini aç veya kapat',
  components_swiper_currentLabel: '{currentSlideNumber}/{totalSlideCount}',
  errors_communicating: '{assistantName} şu an yanıt veremiyor. Bağlı bir sistemdeki sorun verinin gelmesini engelliyor.',
  errors_imageSource: 'Görsel kullanılamıyor.',
  errors_videoSource: 'Video kullanılamıyor.',
  errors_audioSource: 'Ses kullanılamıyor.',
  media_audioPlayer_loading: 'Ses oynatıcı yükleniyor',
  media_audioPlayer_ready: 'Ses oynatıcı hazır',
  media_audioPlayer_loadingLabel: 'Yükleniyor',
  media_audioPlayer_readyLabel: 'Hazır',
  media_audioPlayer_errorLabel: 'Hata',
  media_videoPlayer_loading: 'Video oynatıcı yükleniyor',
  media_videoPlayer_ready: 'Video oynatıcı hazır',
  media_videoPlayer_loadingLabel: 'Yükleniyor',
  media_videoPlayer_readyLabel: 'Hazır',
  media_videoPlayer_errorLabel: 'Hata',
  errors_iframeSource: 'Web sayfası kullanılamıyor.',
  errors_singleMessage: 'Gönderdiğin mesajda bir sorun oldu; başka bir şey sorabilirsin.',
  errors_ariaMessageRetrying: 'Mesaj gönderilirken sorun yaşanıyor, yeniden deneniyor',
  errors_ariaMessageFailed: 'Mesaj gönderilemedi',
  errors_noHumanAgentsAvailable: 'Şu an destek kişisi yok.',
  errors_noHumanAgentsJoined: 'Sohbete katılan destek kişisi olmadı',
  errors_connectingToHumanAgent: 'Bir sorun oldu; şu an bir destek kişisine bağlanılamıyor.',
  errors_busy: 'Şu an çok yoğunuz; biraz sonra yeniden dene.',
  errors_agentAppSessionExpired: 'Sohbet geçmişine erişimin süresi doldu.',
  errors_generalContent: 'Bu içerik gösterilirken bir hata oldu',
  errors_somethingWrong: 'Bir şeyler ters gitti',
  input_ariaLabel: 'Sorunu yaz',
  input_placeholder: 'Bir soru sor...',
  input_buttonLabel: 'Gönder',
  input_uploadButtonLabel: 'Dosya ekle',
  input_actionsMenuLabel: 'Dosya ve daha fazlası',
  input_actionsOverflowLabel: 'Diğer eylemler',
  input_sendingMessage: 'Mesaj gönderiliyor...',
  input_keyboardShortcutAnnouncement: 'Mesaj listesi ile giriş alanı arasında geçmek için {key} tuşuna bas.',
  input_maxCharCountExceeded: 'En çok {max} karakter yazılabilir. Şu an {current} karakter.',
  input_maxCharCountExceededTitle: 'Hata: karakter sınırı aşıldı',
  window_title: 'Sohbet penceresi',
  window_ariaChatRegion: 'Sohbet',
  window_ariaChatRegionNamespace: 'Sohbet {namespace}',
  window_ariaWindowOpened: 'Sohbet penceresi açıldı',
  window_ariaWindowClosed: 'Sohbet penceresi kapandı',
  window_ariaWindowLoading: 'Sohbet yükleniyor.',
  launcher_isOpen: 'Sohbet penceresini kapat',
  launcher_isClosed: 'Sohbet penceresini aç',
  launcher_desktopGreeting: 'Merhaba! Bugün nasıl yardımcı olabilirim?',
  launcher_mobileGreeting: 'Merhaba! Bugün nasıl yardımcı olabilirim?',
  launcher_ariaIsExpanded: 'Başlatıcı bildirimini kapat',
  launcher_closeButton: 'Kapat',
  media_transcript_label: 'Döküm',
  media_transcript_show: 'Göster',
  media_transcript_hide: 'Gizle',
  messages_youSaid: 'Sen yazdın',
  messages_attachmentsLabel: 'Ekler',
  messages_unnamedAttachment: 'Ek',
  messages_assistantSaid: '{assistantName} yazdı',
  messages_agentSaid: 'Destek kişisi yazdı',
  messages_searchResults: 'Arama sonuçları',
  messages_searchResultsLink: 'Bu sonucu yeni pencerede aç',
  messages_searchResultsOpenDocument: 'Belgeyi aç',
  messages_searchResultsOpenDocumentWithLabel: '"{documentName}" belgesini aç',
  messages_searchResultsExpand: 'Genişlet',
  messages_searchResultsCollapse: 'Daralt',
  messages_assistantIsLoading: '{assistantName} düşünüyor',
  messages_agentIsTyping: 'Destek kişisi yazıyor',
  messages_focusHandle: 'Mesajı seç',
  messages_processingLabel: 'İşleniyor',
  messages_scrollHandle: 'Sohbetin başı',
  messages_scrollHandleDetailed: 'Sohbetin başı. İlk mesaja gitmek için bu düğmeyi seç, mesajlar arasında ok tuşlarıyla gezin. Listeden çıkmak için Esc\'ye bas. Mesaj listesi ile giriş alanı arasında geçmek için {shortcut} tuşuna bas.',
  messages_scrollHandleDetailedNoShortcut: 'Sohbetin başı. İlk mesaja gitmek için bu düğmeyi seç, mesajlar arasında ok tuşlarıyla gezin. Listeden çıkmak için Esc\'ye bas.',
  messages_scrollHandleEnd: 'Sohbetin sonu',
  messages_scrollHandleEndDetailed: 'Sohbetin sonu. Son mesaja gitmek için bu düğmeyi seç, mesajlar arasında ok tuşlarıyla gezin. Listeden çıkmak için Esc\'ye bas. Mesaj listesi ile giriş alanı arasında geçmek için {shortcut} tuşuna bas.',
  messages_scrollHandleEndDetailedNoShortcut: 'Sohbetin sonu. Son mesaja gitmek için bu düğmeyi seç, mesajlar arasında ok tuşlarıyla gezin. Listeden çıkmak için Esc\'ye bas.',
  messages_scrollMoreButton: 'En alta in',
  messages_reasoningStart: '{sender} kaynaklara bakıyor...',
  messages_streamingStart: '{sender} yazıyor...',
  message_labelAssistant: '{actorName} {timestamp}',
  message_labelYou: 'Sen {timestamp}',
  buttons_restart: 'Sohbeti yeniden başlat',
  buttons_cancel: 'Vazgeç',
  buttons_retry: 'Tekrar dene',
  options_select: 'Bir seçenek seç',
  options_ariaOptionsDisabled: 'Bu seçenekler kapalı, seçilemez',
  header_previewLinkTitle: 'Asistan önizlemesi',
  header_ariaAssistantAvatar: '{assistantName} simgesi',
  header_overflowMenu_options: 'Seçenekler',
  history_view_chats: 'Sohbetleri gör',
  history_new_chat: 'Yeni sohbet',
  homeScreen_returnToAssistant: 'Sohbete dön',
  homeScreen_returnToHome: 'Başlangıç ekranına dön',
  homeScreen_overflowMenuHomeScreen: 'Başlangıç ekranı',
  homeScreen_ariaQuickStartListButton: 'Hızlı başlangıç menüsü',
  homeScreen_ariaQuickStartListOpened: 'Hızlı başlangıç menüsü açıldı.',
  homeScreen_ariaQuickStartListClosed: 'Hızlı başlangıç menüsü kapandı.',
  homeScreen_ariaHomeScreenContent: 'Başlangıç ekranı',
  homeScreen_shown: 'Başlangıç ekranı görünüyor',
  homeScreen_hidden: 'Sohbete dönüldü',
  default_agent_availableMessage: 'Destek kişisi iste; hazır olduğunda haber veririm.',
  default_agent_unavailableMessage: 'Şu an destek kişisi yok.',
  agent_reason_error: 'Bir sorun yaşıyorum; sohbete bir destek kişisinin devam etmesi gerekiyor.',
  agent_sdMissingWarning: 'Destek masası yapılandırılmamış.',
  agent_noName: 'Destek kişisi',
  agent_chatTitle: 'Canlı destek',
  agent_startChat: 'Destek kişisine bağlan',
  agent_connecting: 'İstek gönderildi...',
  agent_agentNoNameTitle: 'Destek',
  agent_agentJoinedName: '{personName} bağlandı.',
  agent_agentJoinedNoName: 'Bir destek kişisi bağlandı.',
  agent_youConnectedWarning: 'Sayfadan ayrılırsan yeniden destek istemen gerekir.',
  agent_connectingMinutes: 'Bekleme süresi <b>{time, number} dakika</b>.',
  agent_connectingQueue: 'Sırada <b>{position, number}.</b> sıradasın.',
  agent_ariaHumanAgentAvatar: 'Destek kişisinin simgesi',
  agent_ariaGenericAvatar: 'Simge',
  agent_ariaGenericAssistantAvatar: 'Simge',
  agent_youEndedChat: 'Destek kişisiyle bağlantıyı kestin.',
  agent_conversationWasEnded: 'Destek kişisiyle bağlantıyı kestin.',
  agent_disconnected: 'Bir sorun oldu, destek kişisiyle bağlantı koptu. İnternet bağlantını kontrol edip yeniden dene.',
  agent_reconnected: 'Destek kişisi yeniden bağlandı.',
  agent_agentLeftChat: '{personName} ayrıldı.',
  agent_agentLeftChatNoName: 'Destek kişisi ayrıldı.',
  agent_agentEndedChat: '{personName} sohbeti bitirdi.',
  agent_agentEndedChatNoName: 'Destek kişisi sohbeti bitirdi.',
  agent_transferring: 'Aktarılıyorsun.',
  agent_transferringNoName: 'Aktarılıyorsun.',
  agent_endChat: 'Destek kişisiyle bağlantı kesilsin mi?',
  agent_confirmSuspendedEndChatTitle: 'Önceki destek kişisiyle bağlantı kesilsin mi?',
  agent_confirmSuspendedEndChatMessage: 'Şu an bir destek kişisine bağlısın. Devam edersen bağlantı kesilip yenisine bağlanırsın. Devam edilsin mi?',
  agent_confirmCancelRequestTitle: 'İstek iptal edilsin mi?',
  agent_confirmCancelRequestMessage: 'Devam edersen destek isteğin iptal edilir.',
  agent_confirmCancelRequestNo: 'Geri dön',
  agent_confirmCancelRequestYes: 'İsteği iptal et',
  agent_confirmEndChat: 'Bağlantıyı kesersen yeniden destek istemen gerekir.',
  agent_confirmEndChatNo: 'Geri dön',
  agent_confirmEndChatYes: 'Bağlantıyı kes',
  agent_confirmEndSuspendedYes: 'Devam et',
  agent_assistantReturned: 'Başka bir konuda yardımcı olabilir miyim?',
  agent_newMessage: 'Yeni mesaj',
  agent_cardButtonChatRequested: 'Bağlanıyor...',
  agent_cardButtonConnected: 'Bağlandı',
  agent_cardButtonChatEnded: 'Bağlantı kesildi',
  agent_cardMessageChatEnded: 'Destek kişisiyle bağlantıyı kestin.',
  agent_cardMessageConnected: 'Artık bağlısın.',
  agent_connectButtonCancel: 'Vazgeç',
  agent_connectedButtonEndChat: 'Bağlantıyı kes',
  agent_connectWaiting: 'Bekleniyor...',
  agent_defaultMessageToHumanAgent: 'Sohbeti başlat',
  agent_inputPlaceholderConnecting: 'Destek kişisi bekleniyor...',
  agent_inputPlaceholderReconnecting: 'Yeniden bağlanılıyor...',
  agent_sharingStopSharingButton: 'Ekran paylaşımını durdur',
  agent_sharingRequestTitle: 'Ekran paylaşımı',
  agent_sharingRequestMessage: 'Destek kişisi ekranını paylaşmanı istedi. İstediğin zaman durdurabilirsin.',
  agent_sharingAcceptButton: 'Ekranı paylaş',
  agent_sharingDeclineButton: 'Reddet',
  agent_sharingRequested: 'Ekranını paylaşman istendi.',
  agent_sharingAccepted: 'Ekranını paylaştın.',
  agent_sharingDeclined: 'Ekran paylaşımını reddettin.',
  agent_sharingCancelled: 'Ekran paylaşım isteği iptal edildi.',
  agent_sharingEnded: 'Ekran paylaşımını durdurdun.',
  agent_suspendedWarning: 'Şu an bir destek kişisine bağlısın.',
  icon_ariaUnreadMessages: '{count, number} okunmamış mesaj var',
  showMore: 'Devamını gör',
  showMoreResults: 'Devamını gör',
  disclaimer_title: 'Uyarı',
  disclaimer_accept: 'Kabul ediyorum',
  disclaimer_icon_label: 'Uyarı simgesi',
  disclaimer_acceptance_label: 'Uyarı onayı',
  general_ariaCloseInformationOverlay: 'Bilgi panelini kapat.',
  general_ariaAnnounceOpenedInformationOverlay: 'Bir bilgi paneli açıldı.',
  general_ariaAnnounceClosedInformationOverlay: 'Bilgi paneli kapandı.',
  general_ariaAnnounceEscapeOverlay: 'Kapatmak için Esc\'ye bas ya da kapat düğmesini seç.',
  general_returnToAssistant: 'Sohbete dön',
  conversationalSearch_streamingIncomplete: 'Bu mesaj tamamlanamadı. Yeniden dene.',
  conversationalSearch_viewSourceDocument: 'Kaynağı gör',
  conversationalSearch_citationsLabel: 'Kaynaklar',
  conversationalSearch_toggleCitations: 'Kaynak listesini aç veya kapat',
  conversationalSearch_responseStopped: 'Yanıt durduruldu',
  iframe_ariaSourceLoaded: 'Web sayfası yüklendi.',
  iframe_ariaImageAltText: 'Web sayfası panelinin önizleme görseli.',
  iframe_ariaClosePanel: 'Web sayfası panelini kapat.',
  iframe_ariaOpenedPanel: 'Web sayfası paneli açıldı.',
  iframe_ariaClosedPanel: 'Web sayfası paneli kapandı.',
  iframe_ariaClickPreviewCard: '{source} sayfasını panelde açmak için tıkla.',
  datePicker_chooseDate: 'Tarih seç ({format})',
  datePicker_confirmDate: 'Tarihi onayla',
  fileSharing_fileTooLarge: 'Dosya en çok {maxSize} olabilir.',
  fileSharing_ariaAnnounceSuccess: 'Dosya yüklendi.',
  fileSharing_fileIcon: 'Dosya simgesi',
  fileSharing_removeButtonTitle: 'Dosyayı kaldır',
  fileSharing_removeButtonTitleWithName: 'Kaldır: {filename}',
  fileSharing_statusUploading: 'Dosya yükleniyor',
  fileSharing_uploadFailed: 'Dosya yüklenemedi.',
  fileSharing_uploadErrorTitle: 'Yükleme hatası',
  fileSharing_uploadErrorRecovery: 'Eki kaldırıp yeniden dene.',
  fileSharing_agentMessageText: 'Dosya yükleme',
  fileSharing_request: 'Destek kişisi bir dosya yüklemeni istedi.',
  fileSharing_ariaAnnounceFilesAdded: '{count, plural, one {Dosya eklendi.} other {{count, number} dosya eklendi.}}',
  fileSharing_ariaAnnounceFilesUploading: '{count, plural, one {Dosya yükleniyor.} other {{count, number} dosya yükleniyor.}}',
  fileSharing_ariaAnnounceFileRemoved: 'Dosya kaldırıldı.',
  fileSharing_unsupportedType: '{filename} desteklenen bir dosya türü değil.',
  fileSharing_tooManyFiles: 'Bir mesaja en fazla {maxFiles} dosya eklenebilir.',
  carousel_prevNavButton: 'Önceki slayt.',
  carousel_nextNavButton: 'Sonraki slayt.',
  input_completionsTagApp: 'Uygulama',
  input_completionsTagAssistant: 'Asistan',
  table_filterPlaceholder: 'Tabloyu süz',
  table_previousPage: 'Önceki sayfa',
  table_nextPage: 'Sonraki sayfa',
  table_itemsPerPage: 'Sayfa başına:',
  table_paginationSupplementalText: '/ {pagesCount, number} sayfa',
  table_paginationStatus: '{start, number}–{end, number} / {count, number} öğe',
  codeSnippet_feedback: 'Kopyalandı!',
  codeSnippet_showLessText: 'Daha az göster',
  codeSnippet_showMoreText: 'Daha fazla göster',
  codeSnippet_tooltipContent: 'Panoya kopyala',
  codeSnippet_lineCount: '{count, number} satır',
  codeSnippet_foldCollapse: 'Kod bloğunu daralt',
  codeSnippet_foldExpand: 'Kod bloğunu genişlet',
  codeSnippet_ariaLabelReadOnly: 'Kod parçası',
  codeSnippet_ariaLabelReadOnlyWithLanguage: '{language} kod parçası',
  codeSnippet_ariaLabelEditable: 'Kod düzenleyici',
  codeSnippet_ariaLabelEditableWithLanguage: '{language} kod düzenleyici',
  table_downloadButton: 'Tablo verisini indir',
  feedback_positiveLabel: 'Bu yanıtı beğendim',
  feedback_negativeLabel: 'Bu yanıtı beğenmedim',
  feedback_defaultTitle: 'Geri bildirim',
  feedback_defaultPrompt: 'Neden bu değerlendirmeyi seçtin?',
  feedback_defaultPlaceholder: 'Yorum ekle',
  feedback_categoriesLabel: 'Geri bildirim türü',
  feedback_submitLabel: 'Gönder',
  feedback_cancelLabel: 'Vazgeç',
  input_stopResponse: 'Yanıtı durdur',
  messages_responseStopped: 'Yanıt durduruldu',
  messages_requestCancelled: 'İstek iptal edildi',
  chainOfThought_stepTitle: '{stepNumber, number}: {stepTitle}',
  chainOfThought_inputLabel: 'Girdi',
  chainOfThought_outputLabel: 'Çıktı',
  chainOfThought_toolLabel: 'Araç',
  chainOfThought_statusSucceededLabel: 'Tamamlandı',
  chainOfThought_statusFailedLabel: 'Başarısız',
  chainOfThought_statusProcessingLabel: 'Sürüyor',
  chainOfThought_explainabilityLabel: 'Bu cevaba nasıl ulaştım?',
  reasoningSteps_mainLabelOpen: 'Adımları gizle',
  reasoningSteps_mainLabelClosed: 'Adımları göster',
  workspace_opened: 'Panel açıldı: {title}',
  workspace_opened_no_title: 'Panel açıldı',
  workspace_closed: 'Panel kapandı, sohbete dönüldü',
  panel_opened: 'Panel açıldı',
  panel_closed: 'Panel kapandı',
  history_shown: 'Sohbet geçmişi görünüyor',
  history_hidden: 'Sohbet geçmişi gizlendi',
  aria_workspaceRegion: 'Çalışma paneli',
  aria_historyRegion: 'Sohbet geçmişi',
  aria_messagesRegion: 'Sohbet mesajları',
  aria_catastrophicErrorPanel: 'Hata paneli',
  aria_hydrationPanel: 'Yükleme paneli',
  aria_customPanel: 'Panel',
  aria_disclaimerPanel: 'Uyarı paneli',
  aria_responsePanel: 'Yanıt paneli',
  aria_iframePanel: 'İçerik paneli',
  aria_viewSourcePanel: 'Kaynak paneli',
}
```
