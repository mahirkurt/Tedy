import { defineConfig } from '@playwright/test'

// Port 8086 was squatted by an unrelated Docker container on the dev machine.
// With `reuseExistingServer: true` Playwright took that container for its own
// test server and ran the whole suite against it — every request came back
// "API Key Required", so 30 of 32 tests failed for a reason that had nothing to
// do with the code under test. Two changes stop that from recurring:
//   * the port is overridable, and defaults off the crowded 808x range;
//   * the server is never reused, so a collision fails loudly at startup
//     instead of quietly producing meaningless results.
const PORT = Number(process.env.TEDY_E2E_PORT ?? 8286)

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  retries: 1,
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    screenshot: 'only-on-failure',
  },
  // The whole suite runs in Chromium (the unnamed project, so snapshot file
  // names carry no project suffix). WebKit — Safari, and every iPhone browser —
  // and Firefox run the cross-browser smoke spec only; screenshots and the
  // design audits stay in one engine because engines set type differently.
  projects: [
    {},
    { name: 'webkit', use: { browserName: 'webkit' }, testMatch: /capraz-tarayici\.spec\.ts/ },
    { name: 'firefox', use: { browserName: 'firefox' }, testMatch: /capraz-tarayici\.spec\.ts/ },
  ],
  webServer: {
    command: `cd .. && TEST_AUTH_BYPASS=1 .venv/bin/python -c "from src.dashboard_api import app; app.run(host='127.0.0.1', port=${PORT})"`,
    port: PORT,
    reuseExistingServer: false,
    timeout: 15000,
  },
})
