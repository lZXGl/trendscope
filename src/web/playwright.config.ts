import { defineConfig } from "@playwright/test";
const previewPort = process.env.PREVIEW_PORT || "4273";
const jobPort = process.env.JOB_PORT || "4274";
process.env.PREVIEW_PORT = previewPort;
process.env.JOB_PORT = jobPort;
export default defineConfig({
  testDir: "tests/browser",
  workers: 1,
  timeout: 30000,
  use: {
    baseURL: `http://127.0.0.1:${previewPort}`,
    headless: false,
    launchOptions: { executablePath: process.env.CHROMIUM_PATH || "/usr/bin/chromium-browser" },
  },
  webServer: [{ command: `npm run preview -- --host 127.0.0.1 --port ${previewPort} --strictPort`, url: `http://127.0.0.1:${previewPort}`, reuseExistingServer: false },
    { command: `VITE_JOB_API_BASE_URL=/api npm run dev -- --host 127.0.0.1 --port ${jobPort} --strictPort`, url: `http://127.0.0.1:${jobPort}`, reuseExistingServer: false }],
});
