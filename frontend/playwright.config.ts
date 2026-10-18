import { defineConfig } from "@playwright/test";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { mkdtempSync } from "node:fs";
const stateDir = mkdtempSync(join(tmpdir(), "izvor-e2e-state-"));

export default defineConfig({
  testDir: "./e2e",
  outputDir: join(tmpdir(), "izvor-playwright-results"),
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
  use: {
    baseURL: "http://127.0.0.1:8768",
    viewport: { width: 1505, height: 1045 },
    trace: "retain-on-failure",
  },
  webServer: {
    command: `cd .. && .venv/bin/python -m src.web --port 8768 --state-dir '${stateDir}'`,
    url: "http://127.0.0.1:8768",
    reuseExistingServer: false,
  },
});
