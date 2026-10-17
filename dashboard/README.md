# TEDY panosu (`dashboard/`)

Işık'ın okul panosu: `tedy.online`'da açılan, Google ile giriş yapılan, React +
Carbon tek sayfa uygulaması. Bugün, İşler, Asistan, Dersler, Tedy Books ve
"Daha fazla" altındaki ikincil sayfalar buradadır; veriyi Flask API
(`src/dashboard_api.py`, `:8085`) verir, derlenen demet `../dashboard-dist/`'e
yazılır ve aynı Flask/Gunicorn süreci onu sunar. Projenin geneli için kökteki
`README.md`, `AGENTS.md` ve `CLAUDE.md`.

## Yığın (kurulu sürümler, 2026-10-10)

| Paket | Sürüm | Not |
|---|---|---|
| React / React DOM | 19.2 | |
| Vite | 7.3 | `@vitejs/plugin-react`; Carbon, router ve React ayrı parçalarda |
| `@carbon/react` | 1.114 | g10 teması; ikonlar `@carbon/icons-react` 11.86 |
| `@carbon/ai-chat` | 1.22.0 (sabit) | Asistan arayüzü, yalnız asistan açılınca yüklenen ayrı parça |
| `@carbon/web-components` | 2.65 | yalnız AI Chat'in eş bağımlılığı |
| react-router-dom | 7.13 | rotalar `src/routes.ts` |
| TypeScript | 5.9 | `tsc -b` derlemenin parçası |
| KaTeX, markdown-it | 0.16, 14.3 | asistan cevaplarında formül ve Markdown |

IBM Plex Sans/Mono/Serif Google Fonts'tan gelir; Carbon'un kendi `@font-face`'i
kapalıdır (`$css--font-face: false`, Vite'ta `~@ibm/plex` yolu 404 veriyordu).

## Komutlar

```bash
IBM_TELEMETRY_DISABLED=true npm ci   # kurulum; IBM telemetrisi kapalı kalmak zorunda
npm run dev                          # :3000, /api → http://localhost:8085
npm run build                        # tsc -b + vite build → ../dashboard-dist/
npm run lint                         # ESLint + stylelint (stylelint-plugin-carbon-tokens); ikisi de temiz olmalı
npm run lint:css                     # yalnız stylelint
npm run test:birim                   # node:test birim testleri (tests/*.test.ts); dashboard-dist'te Carbon AI'lı demet ister
env -u ANTHROPIC_API_KEY npx playwright test   # e2e; test sunucusu :8286 (TEDY_E2E_PORT)
npm run lhci                         # Lighthouse CI, :8287; sonuç .lighthouseci/ (yüklenmez)
npm run analyze                      # derleme + paket-analizi.html (gitignored)
```

- Playwright'ı **her zaman** `env -u ANTHROPIC_API_KEY` ile çalıştır: yanıtlanmamış
  bir akış `/chat`'e düşer ve test sunucusunda gerçek modele gider.
- `capraz-tarayici` webkit ve firefox projelerinde koşar:
  `npx playwright install chromium webkit firefox`.
- Asistan tek arayüzdür (Carbon AI Chat, `src/asistan/`); eski `AssistantChat` ve
  `VITE_ASISTAN_CARBON_AI` bayrağı Görev 21'de (2026-10-11) kaldırıldı. Geri dönüş: o commit'in revert'i.

## Derleme canlıdır

Gunicorn (`ted-dashboard.service`, `WorkingDirectory` ana checkout) `dashboard-dist/`'i
diskten sunar. **Ana checkout'ta `npm run build` çalıştırmak tedy.online'ı o anda
değiştirir.** Deneme ve test derlemelerini bir worktree'de yap; yayın adımı
`CLAUDE.md` → Deployment'tadır (`npm run build` + `systemctl --user restart ted-dashboard`).

## Tasarım: nereden başlanır

Arayüze dokunan her iş `docs/tedy-ui-ux-talimatnamesi.md` **§0**'la başlar (giriş
yolu, öncelik sırası, belge haritası). Sonra ihtiyaca göre: §4 bileşen seçimi,
§10 Carbon MCP protokolü, §11 Carbon'dan bilinçli sapmalar, §12 kapılar, §13
bilinen borçlar. Arkasındaki belgeler: anayasa `docs/frontend-design-principles.md`
(D1–D4, İ1–İ9), `docs/frontend-surface-designs.md`, bileşen kartları
`docs/carbon-bilesen-rehberi.md`. Claude Code için `.claude/skills/carbon-builder/`
(IBM, değiştirilmez) ve TEDY katmanı `.claude/skills/tedy-carbon/SKILL.md`.
Carbon bileşen, prop ya da ikon adı ezberden yazılmaz; `carbon` MCP'si ya da
`node_modules` ile doğrulanır.

## Token'lar nerede

- `src/theme/ted-theme.scss` — Carbon g10 teması `:root`'ta ve Tedy katmanı
  (`--ted-*`: marka, zemin, köşe, gölge, durum). Stil dosyasında elle hex yazılmaz:
  rol token'ı ya da adıyla `colors.$…`. Aralık, hareket ve tipografi Carbon
  token'ıdır (`spacing.$spacing-NN`, `motion.$duration-*`,
  `@include type.type-style(...)`); stylelint bunu zorlar.
- `src/theme/_subjects.scss` ve `src/theme/subjects.ts` — ders renk sistemi;
  **elle düzenlenmez**, `scripts/gen_subject_themes.py` üretir. Kaynak:
  `src/mcp_server/vendor/assets/carbon-v11-authority.json` (`tedyLayer.subjectThemes`).
- `src/main.tsx` — `<Theme theme="g10">`; `:root`'taki tema ile birlikte bilinçli
  (talimatname §11, S7).

## Kalite kapıları (talimatname §12)

```bash
npm run lint && npm run test:birim
(cd .. && .venv/bin/python -m pytest tests/test_pano_tasarim_sistemi.py tests/test_tedy_tasarim_tutarliligi.py tests/test_ders_renkleri.py)
env -u ANTHROPIC_API_KEY npx playwright test tasarim-denetimi ibm-erisilebilirlik gorsel-regresyon aria-yapisi gorunum-kipleri
```

- `tasarim-denetimi` axe (WCAG 2.2 AA) ve yatay kaydırma, `ibm-erisilebilirlik`
  IBM Equal Access, `gorsel-regresyon` ve `aria-yapisi` piksel ve erişilebilirlik
  ağacı tabanları, `gorunum-kipleri` azaltılmış hareket ve zorlanmış renk;
  `ekran-4k`, `d3b-dokunma` (telefonda ≥ 44 px) ve `capraz-tarayici` de takımdadır.
- Kasıtlı bir görsel değişiklikten sonra farkı oku, sonra tabanları güncelle
  (`--update-snapshots`; komut `CLAUDE.md` → Commands).
- `code_audit` (Carbon MCP) danışma amaçlıdır, CI kapısı değildir.
