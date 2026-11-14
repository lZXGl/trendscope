import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "tests/browser",
  workers: 1,
  timeout: 30000,
  use: {
    baseURL: "http://127.0.0.1:4173",
    headless: false,
    launchOptions: { executablePath: process.env.CHROMIUM_PATH || "/usr/bin/chromium-browser" },
  },
  webServer: [{ command: "npm run preview -- --host 127.0.0.1 --port 4173 --strictPort", url: "http://127.0.0.1:4173", reuseExistingServer: !process.env.CI },
    { command: "VITE_JOB_API_BASE_URL=/api npm run dev -- --host 127.0.0.1 --port 4174 --strictPort", url: "http://127.0.0.1:4174", reuseExistingServer: !process.env.CI }],
});
