import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  use: { baseURL: "http://127.0.0.1:8000" },
  webServer: {
    command:
      "../.venv/bin/uvicorn passage_scout.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers",
    url: "http://127.0.0.1:8000/api/health",
    reuseExistingServer: !process.env.CI,
  },
});
