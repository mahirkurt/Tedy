---
name: tedy-carbon
description: TEDY overlay on carbon-builder. Use for any TEDY UI work — dashboard/ (React + Carbon, incl. Carbon AI Chat in dashboard/src/asistan), edupedia modules, styles, tokens, icons, layout, accessibility — and whenever the carbon-builder skill or the carbon MCP is used in this repo. Where they disagree, this overlay wins.
---

# tedy-carbon

**Precedence:** constitution D1–D4 / İ1–İ9 (`docs/frontend-design-principles.md`) > on module surfaces the Module Design Law > `docs/tedy-ui-ux-talimatnamesi.md` (deviations §11) > surface designs > component guide > this overlay > edupedia vendor (modules) > carbon-builder (IBM 1.3.1, vendored, never edited) > generic Carbon guidance. Measured beats assumed; a conflict is written down, never silently "fixed".

**Start with talimatname §0** (pathway, priority, doc map); §4 components, §10 MCP protocol, §12 "done".

**Never write a Carbon import, icon name or prop from memory.** Confirm it with the `carbon` MCP — `code_search` with `filters.component_type: "React"` (icons: `filters.asset_type: "icon"`, shortest name), no framework word in the query — or in `dashboard/node_modules` (@carbon/react 1.114, @carbon/ai-chat 1.22.0). Labs, IBM Products, Charts: not in this repo.

## Where TEDY overrides carbon-builder (talimatname §11)
- **Modules:** `docs/tedy-modul-tasarim-kanunu.md` (M1–M5, KS-1…KS-12) overrides this overlay and the vendored edupedia guide.
- **S1** One 60rem column; no page-level Grid. Multi-column inside a page is fine, gap = gutter token.
- **S2** IBM Plex from Google Fonts under Vite (`$css--font-face: false`; `~@ibm/plex` 404s).
- **S3** `.cds--` selectors: existing ones stay; a new one needs a measurement comment, MCP proof no prop/variant does it, and a baseline update.
- **S4** Status Tags with text stay; new status indicators carry icon + text. No preview APIs.
- **S5** Inline `style` only for runtime-computed values (percent, position, CSS custom property).
- **S6** "No tests, stop after files" is void: every change ships with tests and read visual diffs. "Don't restate tool output" stands.
- **S7** `<Theme theme="g10">` + `:root` theme is deliberate (don't dedupe); never pass `injectCarbonTheme` to AI Chat.
- **S9** Typography via `@include type.type-style('…')` in SCSS, never a `cds--*` class in TSX.
- **S10** Radii: cards 8px (`--ted-radius-card`), chips `--ted-radius-pill`, all else 0 (controls, marks, bars). Lint-pinned.
- **S11** No static shadows; depth = layer token + 1px border. Shadows only on transient surfaces.
- **S13** Carbon AI Chat a11y repairs (`asistan/carbonOnarimi.ts`, `Tablo.tsx`, `AiAciklama.tsx`) stay; re-run the IBM test on every `@carbon/ai-chat` bump.
- **S35–S45** (Carbon-aligned): primary always `$button-primary`; sentence case, no all-caps; heading weight from its token; skeleton for content, one `InlineLoading` per action; grey never marks a failure; grades not colour-banded. Open code: §13 B68–B75.

## Acceptance (talimatname §12)
```bash
cd dashboard && npm run lint            # ESLint + stylelint carbon-tokens
cd dashboard && npm run test:birim      # needs a Carbon-AI build in dashboard-dist
.venv/bin/python -m pytest tests/test_pano_tasarim_sistemi.py tests/test_tedy_tasarim_tutarliligi.py tests/test_ders_renkleri.py
cd dashboard && env -u ANTHROPIC_API_KEY npx playwright test tasarim-denetimi ibm-erisilebilirlik gorsel-regresyon
```
More gates (kontrast, d3b-dokunma, aria-yapisi, ekran-4k, lhci …): §12.
After an intended visual change, read the diff, then `--update-snapshots` (gorsel-regresyon, aria-yapisi, gorunum-kipleri, carbon-asistan-*). Build in a worktree: `dashboard-dist/` of the main checkout is what tedy.online serves.

**`code_audit`** (advisory, one batch of changed .tsx/.scss): `framework: "react"`, `ibmProducts: "no"`. Report findings by `name`, not rule id. Known false positives: `var(--ted-*)`, `var(--status-*)`, `--ted-radius-card: 8px`, Grid/Stack suggestions (S1), runtime inline style (S5), documented `.cds--` (S3), status Tag with text (S4).
