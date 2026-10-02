# D3a — Tasarım dili ve kabuk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tasarım anayasasındaki İ8'i C yönüne göre yeniden yazmak, ders renk otoritesine geniş yüzeyler için iki rol (`panel`, `panelBorder`) eklemek ve telefonda hamburger menünün yerine alt sekme çubuğu ile "Daha fazla" sayfasını getirmek.

**Architecture:** Renk kararları tek kaynaktan (`carbon-v11-authority.json` → `tedyLayer.subjectThemes`) türer; `scripts/gen_subject_themes.py` panonun `_subjects.scss`/`subjects.ts` dosyalarını üretir. Modül şablonunun bölgeleri yeni rolleri taşımaz, yani şablon değişmez. Kabukta `BottomNav` yalnız CSS ile `< 672px`'te görünür; aynı genişlikte `SideNav` ve menü düğmesi gizlenir. Böylece erişilebilirlik ağacında tek bir gezinme olur. "Daha fazla" (`/daha-fazla`) ikincil rotaları `navRoutesFor(role)`'den listeler.

**Tech Stack:** Python 3.12 (üretici, pytest), React 19 + Vite + Carbon v11 (`@carbon/react`, `@carbon/icons-react`), SCSS (Carbon token'ları), Playwright.

**Spec:** `docs/superpowers/specs/2026-10-02-asistan-zengin-cevap-yukleme-onyuz-design.md` — bölüm "D3a — Tasarım dili ve kabuk".

## Global Constraints

- Çalışma ağacı: yalnız `/mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-zengin`, dal `feat/asistan-zengin`. Her commit'ten önce `test "$(git branch --show-current)" = feat/asistan-zengin && echo dal-dogru` → `dal-dogru`.
- Ana checkout (`/mnt/thunderbolt/workspaces/TED`) paylaşımlıdır ve başka bir oturumun dalındadır: oraya yazma, orada git komutu koşma.
- Python testleri: `DASHBOARD_SECRET_KEY=yerel-test .venv/bin/python -m pytest -q -p no:cacheprovider …`. Çalışma ağacında `.env` yok; oluşturma.
- Tam Python paketi 600 s'yi aşabilir: arkadan, log sonuna `EXIT=$?` yazarak başlat ve önde `timeout 590 bash -c 'until grep -q "^EXIT=" LOG; do sleep 15; done'` ile bekle; bekleyen koşu varken tur bitirme.
- Pano: `dashboard/node_modules` yoksa `cd dashboard && npm ci`. `npm run lint` temiz; `npm run build; echo "build çıkış: $?"` (borusuz). Her Playwright koşusundan önce build. Playwright: `env -u ANTHROPIC_API_KEY TEDY_E2E_PORT=8301 DASHBOARD_SECRET_KEY=yerel-test npx playwright test …`.
- Görsel taban çizgisi yalnız fark okunduktan sonra: önce güncellemesiz koş; kırmızıysa `test-results/**/*-actual.png`, `*-expected.png`, `*-diff.png`'yi Read ile aç, değişimin yalnız beklenen bölgede olduğunu raporla, sonra `--update-snapshots`.
- Carbon token kuralları: boşluk/tip/hareket Carbon token'ı; renk rol token'ı ya da `--ted-subject-*`; el yazısı hex, alfa, gradyan, `filter`, `color-mix` yok. Bir istisna gerekiyorsa `stylelint-disable-next-line` ve gerekçe.
- Kullanıcıya dönük metin Türkçe; kod yorumları İngilizce, çevredeki "measured …" gerekçeli üslupta. Ders adı metni nötr kalır.
- `\u`/`\x` kaçışı yazma; gerekirse `chr()` / `bytes.fromhex()`.
- Staging adla (`git add <yol> …`); `git add -A`/`.` yok; çıplak `git stash` yok; `git push` yok.
- Commit mesajları Türkçe, son satır `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Testler ağa ve ücretli API'ye çıkmaz.

## Dosya haritası

| Dosya | Değişim | Sorumluluk |
|---|---|---|
| `src/mcp_server/vendor/assets/carbon-v11-authority.json` | değişir | `panel`/`panelBorder` rolleri ve tanımları |
| `src/mcp_server/vendor/PROVENANCE.json` | değişir | `vendor_sync --pin` ile yeni karma |
| `scripts/gen_subject_themes.py` | değişir | iki yeni CSS değişkeni, İ8 yorumu |
| `dashboard/src/theme/_subjects.scss`, `subjects.ts` | üretilir | — |
| `tests/test_ders_renkleri.py` | değişir | panel kontrast sözleri |
| `docs/frontend-design-principles.md` | değişir | İ8'in yeni metni |
| `dashboard/src/components/BottomNav.tsx` | yeni | telefon alt sekme çubuğu |
| `dashboard/src/components/DahaFazla.tsx` | yeni | `/daha-fazla` sayfası |
| `dashboard/src/routes.ts` | değişir | `/daha-fazla` rotası, `primaryNavRoutes()` |
| `dashboard/src/App.tsx` | değişir | `BottomNav`'ı ve yeni sayfayı bağlar |
| `dashboard/src/theme/ted-theme.scss` | değişir | alt çubuk, telefonda menü düğmesi/yan menü gizleme, içerik alt boşluğu |
| `dashboard/tests/e2e/alt-gezinme.spec.ts` | yeni | kabuk davranışı |
| `dashboard/tests/e2e/books.spec.ts` | değişir | 320 px testi menü yerine alt çubuğu sınar |
| `dashboard/tests/e2e/gorsel-regresyon.spec.ts-snapshots/*-telefon-linux.png` | yeniden üretilir | — |
| `CLAUDE.md` | değişir | tasarım ve kabuk maddeleri |

---

### Task 1: İ8'in yeni hâli ve ders paneli rolleri

**Files:**
- Modify: `src/mcp_server/vendor/assets/carbon-v11-authority.json` (`tedyLayer.subjectThemes.roles` ve her `families.<aile>.light|dark`)
- Modify: `src/mcp_server/vendor/PROVENANCE.json` (komutla)
- Modify: `scripts/gen_subject_themes.py:26-28` (`ROLE_VARS`), `:41-46` (yorum)
- Regenerate: `dashboard/src/theme/_subjects.scss`, `dashboard/src/theme/subjects.ts`
- Modify: `tests/test_ders_renkleri.py` (kontrast testi)
- Modify: `docs/frontend-design-principles.md` (İ8 bölümü, ~satır 204-216)

**Interfaces:**
- Produces:
  - `--ted-subject-panel` ve `--ted-subject-panel-border` CSS değişkenleri. Her `.ted-subject--<aile>` ve varsayılan `.ted-subject` altında tanımlanır.
  - Otoritede `families.<aile>.<mod>.panel` ve `.panelBorder` (`[adım-adı, "#hex"]`).
  - Rol anlamları:

    | Rol | Açık mod | Koyu mod |
    |---|---|---|
    | `panel` | aile-10 | aile-90 |
    | `panelBorder` | aile-30 | aile-70 |

  - Panel üstündeki metin mevcut `text` rolüdür.

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_ders_renkleri.py` içinde `test_contrast_promises_hold_on_every_ground` fonksiyonunun sonuna (son `assert`'ten sonra) ekle:

```python
    # Geniş ders yüzeyi (İ8, 2026-10-02): panel açık modda aile-10, koyu modda aile-90; üstündeki
    # metin `text` rolüdür, vurgu `accent`. Panel bir sayfadaki tek büyük renkli yüzeydir.
    for mode, roles in (("light", light), ("dark", dark)):
        assert contrast(roles["text"][1], roles["panel"][1]) >= 4.5, (family, mode)
        assert contrast(roles["accent"][1], roles["panel"][1]) >= 3.0, (family, mode)
```

Dosyanın sonuna ekle:

```python
@pytest.mark.parametrize("family", sorted(ST["families"]))
def test_panel_roles_are_the_named_light_and_dark_steps(family):
    light, dark = ST["families"][family]["light"], ST["families"][family]["dark"]
    assert light["panel"][0] == f"{family}-10"
    assert light["panelBorder"][0] == f"{family}-30"
    assert dark["panel"][0] == f"{family}-90"
    assert dark["panelBorder"][0] == f"{family}-70"


def test_dashboard_carries_panel_variables():
    scss = (ROOT / "dashboard" / "src" / "theme" / "_subjects.scss").read_text(encoding="utf-8")
    for family in ST["families"]:
        block = scss.split(f".ted-subject--{family} {{", 1)[1].split("}", 1)[0]
        assert "--ted-subject-panel: #{colors.$" + f"{family}-10}};" in block
        assert "--ted-subject-panel-border: #{colors.$" + f"{family}-30}};" in block
```

- [ ] **Step 2: Başarısız olduğunu gör**

Run: `DASHBOARD_SECRET_KEY=yerel-test .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_ders_renkleri.py`
Expected: FAIL. `KeyError: 'panel'` ve `test_dashboard_carries_panel_variables` başarısız.

- [ ] **Step 3: Otoriteye rolleri ekle**

Tek seferlik betikle (JSON'u elle düzenleme; sıra ve biçim korunur):

```bash
.venv/bin/python - <<'EOF'
import json
from pathlib import Path
p = Path("src/mcp_server/vendor/assets/carbon-v11-authority.json")
raw = p.read_text(encoding="utf-8")
d = json.loads(raw)
pal = d["palette"]
st = d["tedyLayer"]["subjectThemes"]
st["roles"]["panel"] = ("geniş ders yüzeyi (İ8, 2026-10-02): bir görünümün tek büyük renkli yüzeyi; "
                        "açık modda aile-10, koyu modda aile-90; üstündeki metin `text`, vurgu `accent`")
st["roles"]["panelBorder"] = "panel çerçevesi: açık modda aile-30, koyu modda aile-70"
for fam, modes in st["families"].items():
    for mode, (pg, bg) in (("light", ("10", "30")), ("dark", ("90", "70"))):
        modes[mode]["panel"] = [f"{fam}-{pg}", pal[fam][pg]]
        modes[mode]["panelBorder"] = [f"{fam}-{bg}", pal[fam][bg]]
indent = 2 if '\n  "' in raw[:200] else None
p.write_text(json.dumps(d, ensure_ascii=False, indent=indent) + ("\n" if raw.endswith("\n") else ""),
             encoding="utf-8")
EOF
git diff --stat src/mcp_server/vendor/assets/carbon-v11-authority.json
```

Beklenen: yalnız bu dosya değişir ve diff yalnız ekleme satırları içerir. Diff'te başka satırların yeniden biçimlendiğini görürsen, dosyanın özgün girintisini ve ayırıcılarını koruyacak biçimde betiği düzelt ve yeniden çalıştır. Hedef: diff'te yalnız `+` satırları.

- [ ] **Step 4: Üreticiye iki değişkeni ve yeni İ8 yorumunu ekle**

`scripts/gen_subject_themes.py` içinde `ROLE_VARS`'ı şöyle değiştir:

```python
ROLE_VARS = (("accent", "--ted-subject-accent"), ("text", "--ted-subject-text"),
             ("surface", "--ted-subject-surface"), ("onSurface", "--ted-subject-on-surface"),
             ("surfaceHover", "--ted-subject-surface-hover"), ("border", "--ted-subject-border"),
             ("panel", "--ted-subject-panel"), ("panelBorder", "--ted-subject-panel-border"))
```

`render_scss()` içindeki iki yorum satırını şunlarla değiştir:

```python
        "// Ders kimliği (Tedy İ8, 2026-10-02): durum renkleri (kırmızı/sarı/yeşil/turuncu) ders rengi",
        "// olmaz; ders rengi yüzeye ölçüyle çıkar — bir görünümde tek büyük panel (--ted-subject-panel),",
        "// listelerde şerit/kenar/nokta. Değerler Carbon Tag token'larının g10 karşılıkları ve",
        "// @carbon/colors adımlarıdır.",
```

Ardından:

```bash
.venv/bin/python scripts/gen_subject_themes.py
.venv/bin/python src/mcp_server/vendor/scripts/sync_carbon_tokens.py --check
.venv/bin/python -m src.mcp_server.vendor_sync --pin
.venv/bin/python -m src.mcp_server.vendor_sync --check
git status --short
```

Beklenenler:
- Üretici `yazıldı: dashboard/src/theme/_subjects.scss` yazar. `subjects.ts` değişmeyebilir.
- `sync_carbon_tokens --check` sapma göstermez, çünkü şablon yeni rolleri taşımaz.
- `vendor_sync --check` temiz çıkar.
- `git status` yalnız şu dosyaları gösterir: otorite, `PROVENANCE.json`, `_subjects.scss`, üretici, test.

- [ ] **Step 5: İ8'in metnini değiştir**

`docs/frontend-design-principles.md`'de `### İ8 — Renk durumu kodlar, taksonomiyi değil` başlığından bir sonraki `### ` başlığına kadar olan bölümü şununla değiştir:

```markdown
### İ8 — Renk önce durumu söyler; ders rengi yüzeye ölçüyle çıkar

1. **Durum renkleri ayrıdır.** Kırmızı, sarı, yeşil ve turuncu aciliyeti ve sonucu taşır
   (`subjectThemes.reserved`); hiçbir ders bu ailelerden renk almaz.
2. **Ders rengi yüzeye çıkabilir.** Carbon Tag ailesinin açık zemini, kendi koyu metni ve orta ton
   kenarı (`--ted-subject-panel`, `--ted-subject-text`, `--ted-subject-panel-border`,
   `--ted-subject-accent`). Gradyan, saydamlık, `filter`, `color-mix` yasağı sürer.
3. **Bir görünümde en çok bir büyük renkli yüzey.** O ekranın "tek şey"i: Bugün'de sıradaki ders ya
   da iş, asistanda öğretmen paneli. Listeler ders rengini şerit, kenar ya da noktayla taşır. Küçük
   kartlar (ör. iki sütunlu ödev kartları) açık zemin ve üst şerit kullanabilir.
4. **Gri tonlama testi geçer.** Aciliyet renk olmadan da (konum, etiket, ikon) anlaşılır.

*Neden:* 2026-10-02'de kullanıcı Bugün ekranının üç taslağından "ders renkleri yüzeyde" yönünü seçti.
Eski İ8'in asıl derdi yedi kategori renginin "bu önemli"yi boğmasıydı. Bu dert, durum renklerinin
ayrı tutulması ve tek büyük yüzey kuralıyla korunur.

*Test:* Ekranı gri tonlamaya çevir: neyin acil olduğu hâlâ anlaşılıyor mu? Bir görünümde ders
zemininde (`--ted-subject-panel`) duran ve yüksekliği 120 px'i aşan birden fazla yüzey var mı?
Varsa İ8 ihlali.
```

Aynı dosyada İ8'e atıf yapan kontrol listesi satırları (`grep -n "İ8" docs/frontend-design-principles.md`) yeni metinle çelişiyorsa ("ders rengi yalnız kenarda" gibi) aynı anlama getir. Değiştirdiğin satırları raporda listele.

- [ ] **Step 6: Testleri koş**

Run: `DASHBOARD_SECRET_KEY=yerel-test .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_ders_renkleri.py tests/test_pano_tasarim_sistemi.py tests/test_tedy_tasarim_tutarliligi.py`
Expected: PASS (hepsi).

- [ ] **Step 7: Commit**

```bash
test "$(git branch --show-current)" = feat/asistan-zengin && echo dal-dogru
git add src/mcp_server/vendor/assets/carbon-v11-authority.json src/mcp_server/vendor/PROVENANCE.json \
  scripts/gen_subject_themes.py dashboard/src/theme/_subjects.scss tests/test_ders_renkleri.py \
  docs/frontend-design-principles.md
git status --short   # subjects.ts değiştiyse onu da adıyla ekle
git commit -m "D3a: İ8'in yeni hâli ve ders paneli rolleri

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Telefonda alt sekme çubuğu ve "Daha fazla" sayfası

**Files:**
- Create: `dashboard/src/components/BottomNav.tsx`
- Create: `dashboard/src/components/DahaFazla.tsx`
- Modify: `dashboard/src/routes.ts`
- Modify: `dashboard/src/App.tsx` (`COMPONENTS` haritası, kabuk)
- Modify: `dashboard/src/theme/ted-theme.scss` ("Responsive" bölümü, `@media (max-width: 671px)`)
- Create: `dashboard/tests/e2e/alt-gezinme.spec.ts`
- Modify: `dashboard/tests/e2e/books.spec.ts` (320 px menü testi)

**Interfaces:**
- Consumes: `navRoutesFor(role)`, `RouteConfig` (`routes.ts`), `useFocusMode()`, `SessionContext`.
- Produces:
  - `routes.ts`:
    - `primaryNavRoutes(role: UserRole): RouteConfig[]`, `navRoutesFor(role)` içinden `!secondary` olanlar.
    - `secondaryNavRoutes(role: UserRole): RouteConfig[]`.
    - `/daha-fazla` rotası (`showInNav: false`, `componentName: 'DahaFazla'`, `offPortal: true`).
  - `BottomNav`: `default function BottomNav({ role }: { role: UserRole })`. Kökü `nav.bottom-nav[aria-label="Ana gezinme"]`.
  - `DahaFazla`: `default function DahaFazla()`. Kökü `section.daha-fazla` ve bir başlık `h2` "Daha fazla".

- [ ] **Step 1: Başarısız e2e testini yaz**

`dashboard/tests/e2e/alt-gezinme.spec.ts`:

```ts
import { test, expect } from '@playwright/test'
import { sabitAc } from './_gorsel-yardim'

// The phone shell (D3a, 2026-10-02): five tabs at the bottom instead of a menu
// button behind the brand band. One navigation in the accessibility tree at a
// time — the side nav and its button are hidden on a phone, the bar on a desktop.

test.use({ timezoneId: 'Europe/Istanbul', locale: 'tr-TR' })

const SEKMELER = ['Bugün', 'İşler', 'Asistan', 'Dersler', 'Daha fazla']

test('a phone gets the bottom bar and no menu button', async ({ page }) => {
  await sabitAc(page, '/', 390, 844)
  const bar = page.getByRole('navigation', { name: 'Ana gezinme' })
  await expect(bar).toBeVisible()
  await expect(bar.getByRole('link')).toHaveText(SEKMELER)
  await expect(page.getByRole('button', { name: 'Menü' })).toBeHidden()
  await expect(page.getByRole('navigation', { name: 'Navigasyon' })).toBeHidden()
  await expect(bar.getByRole('link', { name: 'Bugün' })).toHaveAttribute('aria-current', 'page')
  for (const link of await bar.getByRole('link').all()) {
    const box = await link.boundingBox()
    expect(box!.height).toBeGreaterThanOrEqual(48)
  }
})

test('a tab goes where it says and marks itself', async ({ page }) => {
  await sabitAc(page, '/', 390, 844)
  const bar = page.getByRole('navigation', { name: 'Ana gezinme' })
  await bar.getByRole('link', { name: 'İşler' }).click()
  await expect(page).toHaveURL(/\/isler$/)
  await expect(bar.getByRole('link', { name: 'İşler' })).toHaveAttribute('aria-current', 'page')
  await expect(bar.getByRole('link', { name: 'Bugün' })).not.toHaveAttribute('aria-current', 'page')
})

test('Daha fazla lists every secondary page and marks itself on one of them', async ({ page }) => {
  await sabitAc(page, '/', 390, 844)
  const bar = page.getByRole('navigation', { name: 'Ana gezinme' })
  await bar.getByRole('link', { name: 'Daha fazla' }).click()
  await expect(page).toHaveURL(/\/daha-fazla$/)
  const liste = page.locator('section.daha-fazla')
  for (const ad of ['Tedy Books', 'Notlar', 'Takvim', 'Takımlar', 'İlerleme', 'Duyurular', 'Profil', 'Modüller']) {
    await expect(liste.getByRole('link', { name: ad })).toBeVisible()
  }
  await liste.getByRole('link', { name: 'Notlar' }).click()
  await expect(page).toHaveURL(/\/notlar$/)
  await expect(bar.getByRole('link', { name: 'Daha fazla' })).toHaveAttribute('aria-current', 'page')
})

test('the bar never covers the end of a page', async ({ page }) => {
  await sabitAc(page, '/isler', 390, 844)
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight))
  const bar = await page.getByRole('navigation', { name: 'Ana gezinme' }).boundingBox()
  const footer = await page.locator('.dashboard-footer').boundingBox()
  expect(footer!.y + footer!.height).toBeLessThanOrEqual(bar!.y + 1)
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
})

test('a desktop keeps the side nav and shows no bar', async ({ page }) => {
  await sabitAc(page, '/', 1440, 900)
  await expect(page.getByRole('navigation', { name: 'Ana gezinme' })).toBeHidden()
  await expect(page.getByRole('navigation', { name: 'Navigasyon' })).toBeVisible()
})

test('focus mode keeps the four daily tabs and drops Daha fazla', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('tedy-focus-mode', 'true'))
  await sabitAc(page, '/', 390, 844)
  const bar = page.getByRole('navigation', { name: 'Ana gezinme' })
  await expect(bar.getByRole('link')).toHaveText(SEKMELER.slice(0, 4))
})
```

(`FocusModeContext.tsx` değeri `localStorage.getItem('tedy-focus-mode') === 'true'` diye okur.)

- [ ] **Step 2: Başarısız olduğunu gör**

```bash
cd dashboard && npm run build; echo "build çıkış: $?"
env -u ANTHROPIC_API_KEY TEDY_E2E_PORT=8301 DASHBOARD_SECRET_KEY=yerel-test npx playwright test alt-gezinme
```

Expected: FAIL ("Ana gezinme" adlı gezinme yok).

- [ ] **Step 3: Rotaları ekle**

`dashboard/src/routes.ts`:

`routes` dizisinde `/moduller` satırından sonra ekle:

```ts
  // The phone's fifth tab (D3a): every secondary page on one screen. Off the
  // side nav — on a desktop the nav already lists them under "Daha fazla".
  { path: '/daha-fazla', label: 'Daha fazla', icon: OverflowMenuHorizontal, componentName: 'DahaFazla', showInNav: false, offPortal: true },
```

`import` satırına `OverflowMenuHorizontal` ekle. Dosyanın sonuna ekle:

```ts
/** The pages worth a tab of their own (bottom bar on a phone, top of the side nav). */
export function primaryNavRoutes(role: UserRole): RouteConfig[] {
  return navRoutesFor(role).filter(r => !r.secondary)
}

/** Everything reachable but one level down (İ1). */
export function secondaryNavRoutes(role: UserRole): RouteConfig[] {
  return navRoutesFor(role).filter(r => r.secondary)
}
```

Not: `Tedy Books` (`/kitaplar`) bugün `secondary` değil. Alt çubukta dört günlük sekme olacak (kullanıcı kararı: Bugün · İşler · Asistan · Dersler · Daha fazla), bu yüzden Tedy Books'u yan menüde birincil bırakıp alt çubukta "Daha fazla"ya düşür. Bunun için alt çubuk kendi sabit listesini kullanır (Step 4). `secondaryNavRoutes` ise "Daha fazla" sayfasına Tedy Books'u ayrıca ekler (Step 5).

- [ ] **Step 4: `BottomNav` bileşenini yaz**

`dashboard/src/components/BottomNav.tsx`:

```tsx
import { NavLink, useLocation } from 'react-router-dom'
import { OverflowMenuHorizontal } from '@carbon/icons-react'
import type { UserRole } from '../hooks/useAuth'
import { primaryNavRoutes } from '../routes'
import { useFocusMode } from '../contexts/focusMode'

// The phone's navigation (D3a, 2026-10-02). Four daily places and "Daha fazla",
// always one tap away — the menu button behind the brand band asked for two taps
// and a scan of twelve items before anything happened (İ1). Shown only below
// Carbon's md breakpoint by CSS, so the desktop side nav and this bar are never
// both in the accessibility tree.
const GUNLUK = ['/', '/isler', '/asistan', '/dersler']

export default function BottomNav({ role }: { role: UserRole }) {
  const { focusMode } = useFocusMode()
  const { pathname } = useLocation()
  const sekmeler = primaryNavRoutes(role).filter(r => GUNLUK.includes(r.path))
  const birincilde = sekmeler.some(r =>
    r.path === '/' ? pathname === '/' : pathname === r.path || pathname.startsWith(`${r.path}/`))

  return (
    <nav className="bottom-nav" aria-label="Ana gezinme">
      <ul className="bottom-nav__list">
        {sekmeler.map(r => {
          const Icon = r.icon
          return (
            <li key={r.path}>
              <NavLink to={r.path} end={r.path === '/'} className="bottom-nav__link">
                <Icon aria-hidden="true" />
                <span>{r.label}</span>
              </NavLink>
            </li>
          )
        })}
        {!focusMode && (
          <li>
            <NavLink
              to="/daha-fazla"
              className={() => 'bottom-nav__link' + (birincilde ? '' : ' active')}
              aria-current={birincilde ? undefined : 'page'}
            >
              <OverflowMenuHorizontal aria-hidden="true" />
              <span>Daha fazla</span>
            </NavLink>
          </li>
        )}
      </ul>
    </nav>
  )
}
```

`useFocusMode` `contexts/focusMode.ts`'ten gelir (App.tsx de oradan alır). `NavLink` etkin sekmede `aria-current="page"` ve `active` sınıfını kendisi koyar.

- [ ] **Step 5: `DahaFazla` sayfasını yaz**

`dashboard/src/components/DahaFazla.tsx`:

```tsx
import { useContext } from 'react'
import { Link } from 'react-router-dom'
import { SessionContext } from '../contexts/session'
import { routes, secondaryNavRoutes } from '../routes'

// "Daha fazla" (D3a): the phone's fifth tab lands here. The list is derived from
// the same route table as the side nav, so a page added there appears here
// without a second edit. Tedy Books joins it: on a phone the four daily tabs
// are Bugün, İşler, Asistan, Dersler (user's choice, 2026-10-02).
export default function DahaFazla() {
  // App renders pages only inside SessionContext.Provider with a signed-in user.
  const user = useContext(SessionContext)!
  const kitaplar = routes.find(r => r.path === '/kitaplar')
  const liste = [...(kitaplar ? [kitaplar] : []), ...secondaryNavRoutes(user.role)]
  return (
    <section className="daha-fazla" aria-labelledby="daha-fazla-baslik">
      <h2 id="daha-fazla-baslik" className="daha-fazla__baslik">Daha fazla</h2>
      <ul className="daha-fazla__liste">
        {liste.map(r => {
          const Icon = r.icon
          return (
            <li key={r.path}>
              <Link to={r.path} className="daha-fazla__oge">
                <Icon aria-hidden="true" />
                <span>{r.label}</span>
              </Link>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
```

`SessionContext` (`contexts/session.ts`) `User | null` taşır; sayfalar yalnız oturum açıkken çizilir, bu yüzden `!` güvenlidir.

- [ ] **Step 6: Kabuğa bağla**

`dashboard/src/App.tsx`:
- `import BottomNav from './components/BottomNav'` ve `import DahaFazla from './components/DahaFazla'`.
- `COMPONENTS` haritasına `DahaFazla` ekle.
- `<Content …>…</Content>` kapanışından hemen sonra, footer'dan önce ekle:

```tsx
      {!isReader && navItems.length > 1 && <BottomNav role={user.role} />}
```

- [ ] **Step 7: Stilleri ekle**

`dashboard/src/theme/ted-theme.scss`'in "Responsive" bölümünde, `@media (max-width: 671px) {` bloğunun **dışına**, onun hemen öncesine ekle:

```scss
// ─── Phone shell (D3a, 2026-10-02) ───────────────────────────────────────────
// The bottom bar exists in the DOM everywhere and is shown only below md; the
// side nav and its menu button are hidden there. One navigation at a time.
.bottom-nav {
  display: none;
}

.daha-fazla__baslik {
  @include type.type-style('heading-03');
  margin-block-end: spacing.$spacing-05;
}

.daha-fazla__liste {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: spacing.$spacing-03;
}

.daha-fazla__oge {
  display: flex;
  align-items: center;
  gap: spacing.$spacing-03;
  min-block-size: spacing.$spacing-10;
  padding: spacing.$spacing-04;
  border: 1px solid var(--cds-border-subtle-01);
  border-radius: var(--ted-radius-card);
  background: var(--cds-layer-01);
  color: var(--cds-text-primary);
  text-decoration: none;
  @include type.type-style('body-compact-02');

  &:focus-visible {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }
}
```

`@media (max-width: 671px) {` bloğunun **içine**, sonuna ekle:

```scss
  .bottom-nav {
    position: fixed;
    z-index: 8000;
    inset-inline: 0;
    inset-block-end: 0;
    display: block;
    padding-block-end: env(safe-area-inset-bottom);
    border-block-start: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
  }

  .bottom-nav__list {
    display: grid;
    grid-auto-flow: column;
    grid-auto-columns: minmax(0, 1fr);
  }

  .bottom-nav__link {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: spacing.$spacing-01;
    min-block-size: spacing.$spacing-09;
    padding-block: spacing.$spacing-02;
    color: var(--cds-text-secondary);
    text-decoration: none;
    @include type.type-style('label-01');

    &.active {
      color: var(--cds-link-primary);
      box-shadow: inset 0 2px 0 var(--cds-link-primary);
    }

    &:focus-visible {
      outline: 2px solid var(--cds-focus);
      outline-offset: -2px;
    }
  }

  // The bar replaces the menu: hide the button and the side nav it opened.
  .cds--header__menu-toggle,
  .cds--side-nav,
  .app-shell-nav-scrim {
    display: none !important;
  }

  // Content and footer end above the bar (bar height + the device's inset).
  .app-root {
    padding-block-end: calc(#{spacing.$spacing-09} + env(safe-area-inset-bottom));
  }
}
```

`.app-root`, `main.tsx`'te Carbon `Theme`'e verilen ve içerikle footer'ı saran kök sınıftır (`ted-theme.scss` ~5106'da bir sütun olarak kurulur). Ölçüt: Step 1'deki "the bar never covers the end of a page" testi; tutmazsa boşluğu footer'a (`.dashboard-footer`) taşı ve nedenini raporla.

`box-shadow` burada gölge değil, 2 px'lik etkin sekme çizgisidir. Stylelint itiraz ederse aynı görünümü `border-block-start: 2px solid` ile kur; satıra disable yorumu yazma.

- [ ] **Step 8: `books.spec.ts`'deki menü testini uyarla**

`dashboard/tests/e2e/books.spec.ts` (~satır 10-40) 320 px'te menü düğmesine tıklayıp yan menünün açıldığını sınıyor; o düğme artık telefonda yok. Testi şunu sınayacak biçimde yeniden yaz: 320 px'te içerik kutusu `x === 0`, `width === 320`; "Ana gezinme" görünür; `scrollWidth === 320`; "Menü" düğmesi gizli. Testin adını davranışa göre güncelle. Eski açılır menü ölçümünü 800 px'e (tablet: menü düğmesi hâlâ var) taşı, ama yalnız o genişlikte menü gerçekten açılıyorsa. Açılmıyorsa sil ve nedenini raporla.

- [ ] **Step 9: Testleri koş**

```bash
cd dashboard && npm run lint; echo "lint: $?"; npm run build; echo "build çıkış: $?"
env -u ANTHROPIC_API_KEY TEDY_E2E_PORT=8301 DASHBOARD_SECRET_KEY=yerel-test npx playwright test alt-gezinme books dashboard tasarim-denetimi ibm-erisilebilirlik
```

Expected: `alt-gezinme`, `books` ve `dashboard` PASS. `tasarim-denetimi`/`ibm-erisilebilirlik` yeni bir ihlal göstermemeli. Gösterirse (ör. alt çubukta kontrast, dokunma alanı) stili düzelt; testi gevşetme.

`tasarim-denetimi` içindeki "telefonda sayfa üst boşluğu" gibi ölçümler değişirse, değişimin alt çubukla açıklanıp açıklanmadığını raporla.

- [ ] **Step 10: Commit**

```bash
test "$(git branch --show-current)" = feat/asistan-zengin && echo dal-dogru
git add dashboard/src/components/BottomNav.tsx dashboard/src/components/DahaFazla.tsx \
  dashboard/src/routes.ts dashboard/src/App.tsx dashboard/src/theme/ted-theme.scss \
  dashboard/tests/e2e/alt-gezinme.spec.ts dashboard/tests/e2e/books.spec.ts
git commit -m "D3a: telefonda alt sekme çubuğu ve Daha fazla sayfası

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Taban çizgileri, belgeler ve son kapı

**Files:**
- Regenerate: `dashboard/tests/e2e/gorsel-regresyon.spec.ts-snapshots/*-telefon-linux.png` (13 sayfa)
- Regenerate (gerekirse): `dashboard/tests/e2e/aria-yapisi.spec.ts-snapshots/*.aria.yml`, diğer spec'lerin telefon görüntüleri (`asistan-ogretmen-gorsel`, `asistan-cevap-bicimi`)
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: Task 1 ve 2'nin tamamı.
- Produces: yeşil tam paket ve güncel taban çizgileri.

- [ ] **Step 1: Görsel testleri güncellemesiz koş**

```bash
cd dashboard && npm run build; echo "build çıkış: $?"
env -u ANTHROPIC_API_KEY TEDY_E2E_PORT=8301 DASHBOARD_SECRET_KEY=yerel-test npx playwright test gorsel-regresyon aria-yapisi asistan-ogretmen-gorsel asistan-cevap-bicimi gorunum-kipleri capraz-tarayici
```

Beklenen: telefon (390 px) görüntüleri kırmızı. Masaüstü görüntüleri ve ARIA anlık görüntüleri yeşil kalmalı. Alt çubuk masaüstünde `display: none` olduğu için ağaçta yoktur; masaüstünde kırmızı görürsen bu bir hatadır, düzelt.

- [ ] **Step 2: Her farkı oku**

Kırmızı her telefon görüntüsü için `test-results/**/*-diff.png`'yi Read ile aç. Raporda bir satırda şunları yaz: sayfa adı, değişen bölge, beklenen mi. Beklenen değişimler:
- (a) üst bantta menü düğmesinin kaybolması ve logonun sola kayması;
- (b) en altta alt çubuk;
- (c) sayfanın alt boşluğunun alt çubuk kadar uzaması.

Başka bir bölge değiştiyse durup nedenini bul.

- [ ] **Step 3: Güncelle ve tekrar koş**

```bash
env -u ANTHROPIC_API_KEY TEDY_E2E_PORT=8301 DASHBOARD_SECRET_KEY=yerel-test npx playwright test gorsel-regresyon asistan-ogretmen-gorsel asistan-cevap-bicimi --update-snapshots
env -u ANTHROPIC_API_KEY TEDY_E2E_PORT=8301 DASHBOARD_SECRET_KEY=yerel-test npx playwright test
```

Beklenen: tam Playwright paketi yeşil. Yeni telefon görüntülerinden üçünü Read ile aç (`bugun-telefon`, `isler-telefon`, `asistan-telefon`) ve alt çubuğun içeriği örtmediğini gözle doğrula.

- [ ] **Step 4: CLAUDE.md'yi güncelle**

`CLAUDE.md`'de iki madde değişir.

**(1) "Multi-page routing" maddesine** şu cümleyi ekle: "Below Carbon's md breakpoint (`< 672px`) the side nav and its menu button are hidden and `BottomNav` takes their place: Bugün · İşler · Asistan · Dersler · Daha fazla (`/daha-fazla`, `DahaFazla.tsx`, listing Tedy Books plus every `secondary` route from `navRoutesFor(role)`); focus mode drops the fifth tab. Chosen 2026-10-02 (plan `docs/superpowers/plans/2026-10-02-d3a-tasarim-dili-kabuk.md`)."

**(2) "Tedy Tasarım Sistemi v3 on the dashboard" maddesinde** "A course is marked only by `SubjectLabel`'s 10 px swatch, an edge or a dot (İ8)" cümlesini şununla değiştir: "Since 2026-10-02 İ8 lets a course's colour reach a surface: at most one large panel per view (`--ted-subject-panel` + `--ted-subject-panel-border`, text `--ted-subject-text`; Carbon step 10/30 light, 90/70 dark, generated from `subjectThemes`), small cards may use the light ground with a top stripe, lists keep the swatch, edge or dot; red/yellow/green/orange stay meaning colours and never a course's."

- [ ] **Step 5: Tam Python paketi**

```bash
(DASHBOARD_SECRET_KEY=yerel-test .venv/bin/python -m pytest -q -p no:cacheprovider > /tmp/d3a-py.log 2>&1; echo "EXIT=$?" >> /tmp/d3a-py.log) &
timeout 590 bash -c 'until grep -q "^EXIT=" /tmp/d3a-py.log; do sleep 15; done'; tail -3 /tmp/d3a-py.log
```

Beklenen: `EXIT=0`. Başarısız test yok. Atlanan sayısı main ile aynı.

- [ ] **Step 6: Commit**

```bash
test "$(git branch --show-current)" = feat/asistan-zengin && echo dal-dogru
git add CLAUDE.md
git add dashboard/tests/e2e/gorsel-regresyon.spec.ts-snapshots/*-telefon-linux.png
git status --short   # başka güncellenen taban çizgisi varsa adlarıyla ekle
git commit -m "D3a: telefon taban çizgileri ve CLAUDE.md

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

## Controller notu (dağıtım bu planın görevi değil)

- `carbon-v11-authority.json`'ın bayt-özdeş kopyası CureoHub'da `services/edupedia_site/app/static/` altındadır. Birleştirmeden sonra bu kopya ayrı bir CureoHub commit'iyle eşlenir ve `tools/gen_carbon_css.py` yeniden çalıştırılır.
- Canlı dizin `/mnt/thunderbolt/workspaces/TED` başka bir dalda olabilir. Dağıtımdan önce kullanıcıya sorulur (spec "Dağıtım notu").
