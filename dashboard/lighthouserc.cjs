// Lighthouse CI for the built dashboard: accessibility, best practices, layout
// shift and performance, measured on this machine against the auth-bypass
// test server. Reports stay on disk (.lighthouseci/); nothing is uploaded —
// the "temporary-public-storage" target would publish every report.
//
// Mobile, Lighthouse's default profile: the family reads TEDY on phones.
// Performance only warns: a local Flask dev server under simulated 4G is not
// the tunnel-fronted production, so its score is a trend, not a gate.
const { chromium } = require('@playwright/test')

const PORT = Number(process.env.TEDY_LHCI_PORT ?? 8287)
const SAYFALAR = ['/', '/isler', '/dersler', '/asistan', '/kitaplar']

module.exports = {
  ci: {
    collect: {
      startServerCommand: `cd .. && TEST_AUTH_BYPASS=1 .venv/bin/python -c "from src.dashboard_api import app; app.run(host='127.0.0.1', port=${PORT})"`,
      startServerReadyPattern: 'Running on',
      startServerReadyTimeout: 30000,
      url: SAYFALAR.map(p => `http://127.0.0.1:${PORT}${p}`),
      numberOfRuns: 1,
      chromePath: process.env.CHROME_PATH || chromium.executablePath(),
      settings: { chromeFlags: '--headless=new --no-sandbox' },
    },
    assert: {
      assertions: {
        'categories:accessibility': ['error', { minScore: 0.95 }],
        'categories:best-practices': ['error', { minScore: 0.9 }],
        'cumulative-layout-shift': ['error', { maxNumericValue: 0.1 }],
        'categories:performance': ['warn', { minScore: 0.8 }],
      },
    },
    upload: { target: 'filesystem', outputDir: '.lighthouseci' },
  },
}
