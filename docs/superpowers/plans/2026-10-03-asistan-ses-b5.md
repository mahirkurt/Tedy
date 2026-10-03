# Asistan ses — B5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Her bitmiş asistan cevabında `Sesli oku` / `Durdur` düğmesi `speechSynthesis` ile `tr-TR` ses okur. Markdown işaretleri ve `[S1]` atıfı okunmaz. Türkçe ses yoksa bu düğme yoktur. Yazma alanının yanında mikrofon düğmesi `SpeechRecognition` (`webkit` öneki dahil) ile `tr-TR` tanır; ara metin alana düşer, gönderim elle yapılır. İlk basışta spec'in cümlesi onaylanmadan mikrofon açılmaz. Onay `localStorage`'da kişi başınadır. Desteklemeyen tarayıcıda mikrofon düğmesi yoktur. Sunucuya ses gitmez.

**Architecture:** Okunacak metin, ses seçimi, birleştirme ve onay anahtarı `dashboard/src/utils/ses.ts` içindedir. React'a ve ağa import etmez. Düğmeler `AssistantChat` içindedir. Konuşma ve tanıma yalnız tarayıcı API'sidir. Yeni Flask ucu yoktur. Ses baytı, tanıma gövdesi ve onay kaydı sunucuya yazılmaz. Tanınan metin, kullanıcı `Gönder`'e basınca bugünkü sohbet isteğinin metni olur. B6 yok.

**Tech Stack:** TypeScript (React 19 + Carbon), tarayıcı `speechSynthesis` ve `SpeechRecognition`, Node 24 `node:test` (yeni paket yok), Playwright + `@axe-core/playwright` + IBM Equal Access.

**Spec:** `docs/superpowers/specs/2026-09-28-asistan-ogretmen-modlari-design.md` — **§5**, karar tablosundaki **Mikrofon** satırı, "Test"teki "ses düğmelerinin desteklenmediğinde gizlenmesi", "Kapsam dışı"ndaki sunucu tarafı konuşma tanıma / metin okuma. **B5'e eklenenler** diye bir ek yoktur. B6 yok. B2, B3 ve B4 plan dosyaları değişmez.

Bu worktree'nin kodu `d002ea5` üzerindedir. B2, B3 ve B4 planları uygulanmadan B5 uygulanmaz. Görevler onların adlandırdığı yüzeyi tüketir: `#ac-input`, cevap eylem satırı, salt okunur sohbet.

## Global Constraints

- **Worktree:** `/mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan`, dal `cursor/asistan-b2-plan-a843`. Ana checkout'a, `feat/asistan-ogretmen` worktree'sine, `feat/asistan-zengin`'e ve portal dallarına dokunma. `docs/superpowers/plans/2026-10-03-asistan-dosya-yukleme-b2.md`, `docs/superpowers/plans/2026-10-03-asistan-sohbet-gecmisi-b3.md` ve `docs/superpowers/plans/2026-10-03-asistan-degerlendirme-sinav-hazirligi-b4.md` değişmez.
- **Git:** dosyaları adıyla stage et. `git add -A` / `git add .` yok. Push yok.
- **Testler ücretli bir API'ye ya da ağa hiç gitmez.** Playwright: `TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python DASHBOARD_SECRET_KEY=yalniz-test env -u ANTHROPIC_API_KEY npx playwright test <spec>`. Soru gönderen her e2e hem `**/api/assistant/stream` hem `**/api/assistant/chat` rotasını kendisi cevaplar. Konuşma tanıma stub'ı Google'a gitmez.
- **Pano:** `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan/dashboard`. `node_modules` yoksa `npm ci`. Playwright'dan önce `npm run build`.
- **Node birim testi:** `node --experimental-strip-types --test tests/ses.test.ts` aynı dizinde. Yeni bağımlılık yok.
- **Renk:** elle hex yok, alfa yok, gradyan yok, `color-mix` yok. Yalnız mevcut `--cds-*` ve `--ted-*`.
- **Dil:** okura giden her yeni cümle Türkçe. Yol, istisna adı ve e-posta okura gitmez.
- **Dağıtım bir plan görevi değildir.**
- **Sunucu konuşmaz.** Yeni uç, ses dosyası, üçüncü taraf TTS/STT istemcisi yok. `/v1` ve `/plan` değişmez.

## Kilitlenen seçimler

Spec bu davranışları ister, sayı ya da düğme adı vermez. Görevler aşağıdaki değeri kullanır.

| Seçim | Değer |
|---|---|
| Türkçe ses | `lang` içindeki `_` `-` olur, küçük harfe iner. Tam `tr-tr` olan ilk ses. Yoksa `tr` ile başlayan ilk ses. İkisi de yoksa okuma düğmesi yoktur. |
| Utterance | `lang` `tr-TR`. `rate` `1`, `pitch` `1`, `volume` `1`. Hız ayarı yoktur. `voice` seçilen sestir. |
| Tek okuma | Yeni `speak` öncesi `cancel`. Yalnız okunan cevabın düğmesi `Durdur` olur. |
| Okuma düğmesi | Bitmiş asistan cevabında, karşılama (`id === 'welcome'`) ve akan taslak hariç. Görünen metin `Sesli oku` ya da `Durdur`. `speechSynthesis` ya da `SpeechSynthesisUtterance` yoksa, Türkçe ses yoksa, ya da okunacak metin boşsa düğme DOM'da yoktur. |
| Kaynak | `okunacakMetin(msg.content)`. Ekran metni ya da çip adı okunmaz. `Kopyala` ham `msg.content` yazar. |
| İşaretler | Aşağıdaki sıra. `1/2` durur. Yalnız `[S` + rakam + `]` atıfı silinir. |
| Mikrofon | `window.SpeechRecognition ?? window.webkitSpeechRecognition`. `lang` `tr-TR`, `interimResults` true, `continuous` false, `maxAlternatives` 1. |
| Mikrofon düğmesi | Boşta `Sesle sor`, dinlerken `Dinlemeyi bitir`. `stop()`, `abort()` değil. Bitince metin durur, istek gitmez, odak `#ac-input`'a döner. |
| Onay anahtarı | `tedy-ses-onay::` + e-postanın trim ve küçük hali. Değer `1`. Boş e-posta anahtar yazmaz ve mikrofonu açmaz. `localStorage` yazılamazsa bu ziyarette açılır, anahtar kalmaz. |
| Not | İlk basışta Carbon `Modal`. Başlık `Mikrofon`. Gövde spec cümlesidir. `Onayla` yazar ve tanımayı başlatır. `Vazgeç` ve kapatma yazmaz, başlatmaz. Cümle her tarayıcıda aynıdır. |
| Ara metin | Tek model. Tanıma `results[0][0].transcript` okur; düz `transcript` alanı yoktur. Bu dizgi o ana kadarki bütün sözcedir. Son alternatif ara hipotezin yerine geçer, üstüne eklenmez. `taban` bir ref'tir (başlangıçtaki taslak). Her `onresult` `setDraft(birlestir(taban.current, results[0][0].transcript))` çağırır. `Gönder` `draft` boşken kapalıdır; yalnız ref yazmak düğmeyi açmaz. |
| Hata | `not-allowed` → `Mikrofon açılamadı.` `aborted` sessizdir. Diğerleri → `Ses anlaşılamadı.` Sohbet hatasının `Tekrar dene` düğmesine yazılmaz. |
| Salt okunur | B3: `#ac-input` kapalı ve `Bu sohbet salt okunur.` Mikrofon düğmesi yoktur. `Sesli oku` durur. |
| Yükleniyor | Mikrofon `disabled`, gizli değil. Okuma düğmesi durur. |
| Alıştırma kartı | Quiz kartında ve kullanıcı balonunda okuma düğmesi yoktur. |

İşaret sırası:

1. `\r\n` → `\n`.
2. Üç ters tırnaklı çit: bilgi satırı düşer, gövde kalır. Kapanmamış çit üç karakter olarak silinir.
3. `![alt](url)` → `alt`.
4. `[yazı](url)` → `yazı`.
5. `\s?\[S\d+\]` silinir.
6. Tek ters tırnak çifti düşer, içi kalır.
7. `**` ve `__` silinir.
8. Satır başı: `#{1,6}` ve sonraki boşluk, `>` ve bir isteğe bağlı boşluk, liste imi (`-`, `+`, `*` ya da `rakam.`) ve sonraki boşluk. Yalnız `---`, `***` ya da `___` (üç ya da daha çok) olan satır silinir.
9. Kalan `*` ya da `_`: iki komşusu da harf ya da rakamsa kalır (`MAT_7`). Bir komşusu boşluksa kalır (`a * b`). Değilse silinir (`*kalın*`, `_vurgu_`).
10. Satır sonları tek boşluk olur, boşluk dizisi teke iner, trim.

## Kilitlenen adlar

| Ad | Değer | Neden |
|---|---|---|
| Modül | `dashboard/src/utils/ses.ts` | Arayüz kuralı. Flask yok. |
| `okunacakMetin` | `(text: string) => string` | İşaret sırası. |
| `turkceSes` | `({ lang: string }[]) => { lang: string } \| null` | Seçim kuralı. |
| `birlestir` | `(taban: string, ek: string) => string` | Trim sonrası tek boşluk. İkisi boşsa `""`. |
| `onayAnahtari` | `(email: string \| null) => string \| null` | Boşta `null`. |
| Okuma düğmesi | `Sesli oku` / `Durdur` | §5. `aria-pressed` okunan cevapta true. |
| Mikrofon | `Sesle sor` / `Dinlemeyi bitir` | Carbon `Microphone` ikonu, `IconButton`. |
| Onay | `Mikrofon`, `Onayla`, `Vazgeç` | Spec düğme adı yazmaz. |
| Not | `Chrome ve Android'de konuşma tanıma sesi Google'a gönderir.` | §5, birebir. |
| Hata | `Mikrofon açılamadı.` / `Ses anlaşılamadı.` | Sessiz arıza yok. Yol ve istisna adı yok. |
| Anahtar | `tedy-ses-onay::<email>` | `ogretmenAnahtari` ile aynı kişi ayrımı. |
| E2E | `dashboard/tests/e2e/asistan-ses.spec.ts` | Spec: düğme gizlenir, axe, IBM. |
| Birim | `dashboard/tests/ses.test.ts` | `node:test`. `src` dışındadır; `tsc -b` onu derlemez. |

Okur cümleleri:

| Durum | Metin |
|---|---|
| Okuma | `Sesli oku` |
| Okurken | `Durdur` |
| Mikrofon | `Sesle sor` |
| Dinlerken | `Dinlemeyi bitir` |
| Not başlığı | `Mikrofon` |
| Not | `Chrome ve Android'de konuşma tanıma sesi Google'a gönderir.` |
| Onay | `Onayla` |
| Vazgeç | `Vazgeç` |
| İzin yok | `Mikrofon açılamadı.` |
| Tanıma olmadı | `Ses anlaşılamadı.` |
| Salt okunur | `Bu sohbet salt okunur.` (B3) |

## File Structure

| Dosya | Durum | Sorumluluk |
|---|---|---|
| `dashboard/src/utils/ses.ts` | yeni | Metin, ses, birleştirme, anahtar |
| `dashboard/tests/ses.test.ts` | yeni | Bu dördü |
| `dashboard/src/components/AssistantChat.tsx` | değişir | İki düğme, modal, tanıma |
| `dashboard/src/components/AssistantChat.scss` | değişir | Yalnız yerleşim. Yeni renk yok. |
| `dashboard/tests/e2e/asistan-ses.spec.ts` | yeni | Oku, gizle, onay, ara metin, axe |
| `CLAUDE.md` | değişir | B5 maddesi, B4 maddesinin altı |

---

### Task 1: Okunacak metin, ses, anahtar

**Files:**
- Create: `dashboard/src/utils/ses.ts`
- Test: `dashboard/tests/ses.test.ts`

**Interfaces:**
- Produces: `okunacakMetin`, `turkceSes`, `birlestir`, `onayAnahtari`.

- [ ] **Step 1: Test**

`dashboard/tests/ses.test.ts`. `node:test` ve `node:assert/strict`. İçe aktarma `../src/utils/ses.ts`.

```ts
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { birlestir, okunacakMetin, onayAnahtari, turkceSes } from '../src/utils/ses.ts'

test('markdown ve atıf okunmaz, kesir durur', () => {
  assert.equal(okunacakMetin('Payda **eşitlenir** [S1].'), 'Payda eşitlenir.')
  assert.equal(okunacakMetin('# Başlık\n\n1/2'), 'Başlık 1/2')
  assert.equal(okunacakMetin('[kitap](https://ornek.test/a)'), 'kitap')
  assert.equal(okunacakMetin('![şekil](https://ornek.test/a.png)'), 'şekil')
  assert.equal(okunacakMetin('```py\n1/2\n```'), '1/2')
  assert.equal(okunacakMetin('> alıntı\n- madde'), 'alıntı madde')
  assert.equal(okunacakMetin('a * b ve MAT_7 ve *kalın* ve _vurgu_'), 'a * b ve MAT_7 ve kalın ve vurgu')
  assert.equal(okunacakMetin('[S1]'), '')
})

test('tr-TR once, sonra tr, yoksa null', () => {
  assert.equal(turkceSes([{ lang: 'en-US' }, { lang: 'tr' }, { lang: 'tr-TR' }])?.lang, 'tr-TR')
  assert.equal(turkceSes([{ lang: 'tr_TR' }])?.lang, 'tr_TR')
  assert.equal(turkceSes([{ lang: 'en-US' }]), null)
  assert.equal(turkceSes([]), null)
})

test('birlestir ve kisi anahtari', () => {
  assert.equal(birlestir('1/2', 'kaçtır'), '1/2 kaçtır')
  assert.equal(birlestir('', 'kesir'), 'kesir')
  assert.equal(birlestir('kesir ', ' nedir'), 'kesir nedir')
  assert.equal(birlestir('  ', '  '), '')
  assert.equal(onayAnahtari('Test@TEDY.online'), 'tedy-ses-onay::test@tedy.online')
  assert.equal(onayAnahtari('  a@b.c '), 'tedy-ses-onay::a@b.c')
  assert.equal(onayAnahtari(''), null)
  assert.equal(onayAnahtari(null), null)
})
```

- [ ] **Step 2: FAIL**

`cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan/dashboard && node --experimental-strip-types --test tests/ses.test.ts`

Expected: FAIL, modül yok.

- [ ] **Step 3: Uygula**

Kilitlenen işaret sırası, ses sırası ve `birlestir`. `onayAnahtari` trim + `toLowerCase` sonrası boşsa `null`. Harf, Türkçe harfler dahil: `A-Za-zÇĞİÖŞÜçğıöşü` ve `0-9`.

- [ ] **Step 4: PASS**

Aynı `node --experimental-strip-types --test`. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/utils/ses.ts dashboard/tests/ses.test.ts
git commit -m "feat: sesli okuma metnini ve onay anahtarını ekle"
```

---

### Task 2: Sesli oku

**Files:**
- Modify: `dashboard/src/components/AssistantChat.tsx`
- Modify: `dashboard/src/components/AssistantChat.scss`
- Create: `dashboard/tests/e2e/asistan-ses.spec.ts`

**Interfaces:**
- Consumes: `okunacakMetin`, `turkceSes`, cevap eylem satırı (`Kopyala` ile aynı balon).
- Produces: `Sesli oku` / `Durdur`.

- [ ] **Step 1: e2e**

`dashboard/tests/e2e/asistan-ses.spec.ts`. `sabitAc` akışı keser. `page.addInitScript` uygulama açılmadan `window.speechSynthesis` stub'ı koyar: `getVoices` bir `tr-TR` ses döner, `speak` utterance'ı `window.__spoken` dizisine iter, `cancel` aynı diziye `'CANCEL'` iter. `voiceschanged` dinleyicisi saklanır ve stub hemen olayı da gönderebilir. Montaj `getVoices` ile de bakar. Headless Chromium'da Türkçe ses yoktur; stub yoksa düğme gizlenir.

Canlı yol `**/api/assistant/stream` rotasını `abort` eder ve `**/api/assistant/chat`'e düşer. İkisi de cevaplanır. `/chat` gövdesi `appendAssistantMessage`'ın okuduğu nesnedir. Akış yolunda aynı nesne `answer` olayının `data.payload` alanıdır (`appendAssistantMessage(data.payload)`). Düz dizgi bu zarf değildir.

```ts
{
  answer: 'Payda **eşitlenir** [S1].',
  citations: [{
    id: 'S1', kind: 'mufredat', label: 'Payda', locator: {},
    snippet: 'Paydalar eşitlenir.', confidence: 0.9,
  }],
  safety_flags: [], plan_blocks: [], intent: 'qa', session_id: '',
  meta: { model: 'claude-sonnet-5', degraded: [] },
}
```

`AnswerBody` `[S1]` için `token.slice(1, -1)` ile `S1` arar. `id` eşleşmezse işaret düz metin kalır, çip olmaz. Test çipi görür, düz `[S1]` dizgisini görmez. `Sesli oku` görünür. Basılınca konuşulan metin `Payda eşitlenir.` olur. Utterance `lang` `tr-TR`, `rate` `1`, `pitch` `1`, `volume` `1`, `voice.lang` `tr-TR`. Düğme `Durdur` olur, `aria-pressed` true. İkinci cevapta `Sesli oku`'ya basılınca dizi `CANCEL` görür ve birinci düğme yeniden `Sesli oku` olur. `Durdur` `cancel` çağırır. Karşılama balonunda düğme yoktur.

Ayrı test: `getVoices` yalnız `en-US` döner. `Sesli oku` sayısı 0.

Ayrı test: `speechSynthesis` yoktur (`speak` fonksiyon değil). `Sesli oku` sayısı 0.

`Kopyala` bu planda değişmez; konuşulan dizi ham `**` ve `[S1]` içermez.

- [ ] **Step 2: FAIL**

`cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan/dashboard && npm run build && TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python DASHBOARD_SECRET_KEY=yalniz-test env -u ANTHROPIC_API_KEY npx playwright test asistan-ses.spec.ts`

Expected: FAIL, `Sesli oku` yok.

- [ ] **Step 3: Arayüz**

Eylem satırına Carbon `Button` `kind="ghost"` `size="sm"`. Metin `Sesli oku` / `Durdur`. `okunacakMetin` boşsa o balonda düğme yok. `turkceSes` null ise hiçbir balonda yok. `speak` öncesi `cancel`. `onend` etiketi `Sesli oku`'ya çevirir. Yeni hex yok.

- [ ] **Step 4: PASS**

Aynı build ve Playwright. Expected: 0.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/components/AssistantChat.tsx dashboard/src/components/AssistantChat.scss \
  dashboard/tests/e2e/asistan-ses.spec.ts
git commit -m "feat: cevapta sesli okumayı ekle"
```

---

### Task 3: Sesle soru

**Files:**
- Modify: `dashboard/src/components/AssistantChat.tsx`
- Modify: `dashboard/src/components/AssistantChat.scss`
- Modify: `dashboard/tests/e2e/asistan-ses.spec.ts`

**Interfaces:**
- Consumes: `birlestir`, `onayAnahtari`, `useSession` e-postası, `#ac-input`.
- Produces: mikrofon, modal, ara metin.

- [ ] **Step 1: e2e**

Aynı spec dosyasına eklenir. Init script `SpeechRecognition`'ı siler, `webkitSpeechRecognition` sahte sınıf koyar. `start` sayacı, kurulan örneğin `lang` / `interimResults` / `continuous` / `maxAlternatives` alanları okunur. `onresult` testten çağrılır.

İlk `Sesle sor`: modalda spec cümlesi birebir durur. `start` sayacı 0. `Vazgeç` modalı kapatır, `localStorage` anahtarı yoktur, sayaç 0.

Yeniden bas, `Onayla`: anahtar `tedy-ses-onay::test@tedy.online` ve değer `1` (fixture e-postası `test@tedy.online`). Sayaç 1. `lang` `tr-TR`, `interimResults` true, `continuous` false, `maxAlternatives` 1. `onresult` düz `transcript` taşımaz. İlk olay `results[0][0].transcript === 'kesir'`, `results[0].isFinal === false`. `setDraft` alanı `kesir` yapar. `Gönder` bu metinle açılır; `draft` boş kalsaydı kapalı kalırdı. İkinci olay aynı sözcenin tamamıdır: `results[0][0].transcript === 'kesir kaçtır'`, `isFinal === true`. Alan `kesir kaçtır` olur. `kesir` ile `kaçtır` yapıştırılmaz. `**/api/assistant/chat` ve `**/api/assistant/stream` sayacı 0 kalır. `Dinlemeyi bitir` `stop` çağırır, etiket `Sesle sor` olur, alan durur. Ancak o zaman `Gönder` bir istek yapar.

Sayfa `tedy-ses-onay::test@tedy.online` = `1` ile açılırsa modal yoktur, basış `start` eder. Anahtar başka e-postadaysa (`baska@tedy.online`) modal yine gelir.

`webkitSpeechRecognition` da yoksa `Sesle sor` sayısı 0. `Sesli oku` bu testte durur.

Salt okunur: B3'ün Işık sohbeti. Açılıştan önce Görev 2'nin `tr-TR` `getVoices` stub'ı kurulur. `#ac-input` `disabled`, sayfada `Bu sohbet salt okunur.` `Sesle sor` sayısı 0. GET satırı `rol` ve `icerik` taşır; `icerik` `Payda **eşitlenir** [S1].` olur. Sayfa bunu `content` yapar. `Sesli oku` `content` okur ve görünür. `icerik` `content`'e yazılmazsa okunacak metin boştur, düğme yoktur.

`not-allowed` olayı `Mikrofon açılamadı.` yazar ve `Tekrar dene` bu satırda yoktur. `aborted` satır yazmaz.

Axe + IBM, B3 `asistan-sohbet.spec.ts` süzgeci: `aria_id_unique` ve `cds--ai-label|cds--toggletip` ihlal sayılmaz. Bir geçiş düğmeler görünürken, bir geçiş modal açıkken.

- [ ] **Step 2: FAIL**

Aynı Playwright komutu. Expected: FAIL, `Sesle sor` yok.

- [ ] **Step 3: Arayüz**

`IconButton` `Microphone`, gönder grubunda, `Gönder`'den önce. Etiket `Sesle sor` / `Dinlemeyi bitir`. Kurucu `webkit` yedeğiyle. Modal kilitlenen üç metinle. `taban` bir ref'tir; tanıma başlarken o anki `draft`'ı tutar. Her `onresult` yalnız `results[0][0].transcript` okur ve `setDraft(birlestir(taban.current, o))` çağırır. Önceki hipotez yeni dizgiye eklenmez. Hata `ac__error` sohbet hatasına yazılmaz; kendi satırı `ac__ses-hata` olur. Yüklenirken `disabled`. Salt okunurda düğme yok. Yüklenen satırda `content`, `icerik`'tir. E-posta boşsa düğme yok. Yeni hex yok.

- [ ] **Step 4: PASS**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan/dashboard
npm run lint
npm run build
node --experimental-strip-types --test tests/ses.test.ts
TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python DASHBOARD_SECRET_KEY=yalniz-test env -u ANTHROPIC_API_KEY npx playwright test asistan-ses.spec.ts
```

Expected: lint, build, node testi ve Playwright 0.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/components/AssistantChat.tsx dashboard/src/components/AssistantChat.scss \
  dashboard/tests/e2e/asistan-ses.spec.ts
git commit -m "feat: sesle soruyu ve mikrofon onayını ekle"
```

---

### Task 4: CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`, B4 maddesinin hemen altı. B4 maddesi `- **Asistan değerlendirme ve sınav hazırlığı (B4)**` ile başlar.

- [ ] **Step 1: Madde**

```markdown
- **Asistan ses (B5)** (spec §5, plan `docs/superpowers/plans/2026-10-03-asistan-ses-b5.md`): each finished assistant answer has `Sesli oku` / `Durdur` via `speechSynthesis` and a `tr-TR` voice (`rate`/`pitch`/`volume` 1). `okunacakMetin` drops Markdown marks and `[S1]` citations; `1/2` stays. No Turkish voice, or no `speechSynthesis`, hides the button. A mic button uses `SpeechRecognition` or `webkitSpeechRecognition` (`tr-TR`, interim results, one utterance). Interim text lands in `#ac-input`; send stays manual. The first press shows `Chrome ve Android'de konuşma tanıma sesi Google'a gönderir.` and does not start until `Onayla`. Consent is `tedy-ses-onay::<email>` = `1`. An unsupported browser hides the mic. A read-only chat keeps read-aloud and hides the mic. No server speech route and no audio upload.
```

- [ ] **Step 2: Son kapı**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan/dashboard
npm run lint && npm run build
node --experimental-strip-types --test tests/ses.test.ts
TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python DASHBOARD_SECRET_KEY=yalniz-test env -u ANTHROPIC_API_KEY npx playwright test asistan-ses.spec.ts
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan
git diff --check -- CLAUDE.md docs/superpowers/plans/2026-10-03-asistan-ses-b5.md
```

Expected: lint, build, node testi ve Playwright 0. `git diff --check` boş.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: asistan ses planını CLAUDE.md'ye yaz"
```

## Kapsam denetimi

| Spec | Görev |
|---|---|
| Her cevapta `Sesli oku` / `Durdur`, `speechSynthesis`, `tr-TR` | 2 |
| Hangi `tr` sesi, hız 1 | 1, 2 |
| Markdown işaretleri ve atıf numarası okunmaz | 1, 2 |
| `1/2` durur | 1 |
| Türkçe ses yoksa okuma düğmesi gizlenir | 2 |
| Mikrofon, `webkit` öneki, `lang=tr-TR` | 3 |
| Ara metin alana düşer, gönderim elle | 1, 3 |
| İlk kullanım notu, onaylanmadan açılmaz, kişi başına `localStorage` | 1, 3 |
| Desteklemeyen tarayıcıda mikrofon gizlenir | 3 |
| Salt okunur sohbette mikrofon yok, okuma durur | 3 |
| Tanıma hatası Türkçe cümle, yol yok | 3 |
| Axe + IBM + ARIA | 3 |
| Sunucu tarafı TTS/STT | yok |
| B6 | yok |
