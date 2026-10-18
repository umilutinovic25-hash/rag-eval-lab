import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
  use: {
    baseURL: "http://127.0.0.1:8767",
    viewport: { width: 1505, height: 1045 },
    trace: "retain-on-failure",
  },
  webServer: {
    command: "cd .. && .venv/bin/python -m src.web",
    url: "http://127.0.0.1:8767",
    reuseExistingServer: !process.env.CI,
  },
});
