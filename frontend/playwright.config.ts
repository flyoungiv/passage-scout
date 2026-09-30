import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  use: { baseURL: "http://127.0.0.1:8001" },
  webServer: {
    cwd: "..",
    command:
      ".venv/bin/uvicorn passage_scout.main:app --host 127.0.0.1 --port 8001 --no-proxy-headers",
    url: "http://127.0.0.1:8001/api/health",
    // Always own an offline server, even when the developer has live keys in .env.
    reuseExistingServer: false,
    env: {
      TAVILY_API_KEY: "",
      GROQ_API_KEY: "",
      LIVE_ACCESS_TOKEN: "",
      OTEL_EXPORTER_OTLP_ENDPOINT: "",
      OTEL_EXPORTER_OTLP_HEADERS: "",
      ALLOWED_HOSTS: '["localhost", "127.0.0.1", "[::1]"]',
    },
  },
});
