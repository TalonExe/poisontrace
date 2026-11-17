import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e/connected",
  workers: 1,
  use: { baseURL: "http://127.0.0.1:4174" },
  webServer: [
    {
      command:
        '"..\\.venv\\Scripts\\python.exe" ..\\backend\\tests\\mcp_browser_api.py',
      url: "http://127.0.0.1:4175/openapi.json",
      reuseExistingServer: false,
    },
    {
      command: "node e2e/connected/preview.mjs",
      url: "http://127.0.0.1:4174",
      reuseExistingServer: false,
    },
  ],
});
