import { defineConfig } from "@playwright/test";

const python = process.env.POISONTRACE_TEST_PYTHON ||
  (process.platform === "win32" ? "..\\.venv\\Scripts\\python.exe" : "../.venv/bin/python");
const hosted = process.env.POISONTRACE_TEST_CONTENT_PROFILE === 'hosted';
const origin = `${hosted ? 'https' : 'http'}://127.0.0.1:4176`;

export default defineConfig({
  testDir: "./e2e/production",
  globalTeardown: './e2e/production/teardown.mjs',
  workers: 1,
  use: { baseURL: origin, ignoreHTTPSErrors: hosted, extraHTTPHeaders: {Origin: origin} },
  webServer: {
    command: `"${python}" ../backend/tests/production_browser_api.py`,
    url: `${origin}/health/ready`,
    ignoreHTTPSErrors: hosted,
    reuseExistingServer: false,
  },
});
