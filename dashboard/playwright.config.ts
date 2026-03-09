import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  retries: 1,
  use: {
    baseURL: 'http://localhost:8086',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'cd .. && TEST_AUTH_BYPASS=1 python -c "from src.dashboard_api import app; app.run(host=\'0.0.0.0\', port=8086)"',
    port: 8086,
    reuseExistingServer: true,
    timeout: 15000,
  },
})
