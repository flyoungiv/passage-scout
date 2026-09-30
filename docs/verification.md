# Verification record

Verified locally during implementation on macOS, Python 3.13.2 and Node 20.7.0:

- 24 Python tests passed: demo isolation, illustrative labels, input validation, safe errors, token/host/origin guards, private/mixed DNS rejection, redirect validation, successful/blank/invalid/oversized-page PDF parsing, bounded request bodies, retrieval, citations, quota settlement, provider contracts, and trace/log privacy.
- 5 Chromium end-to-end tests passed: prepared demo and source links, arbitrary Markdown with unsafe HTML removed, selection and explicit missing-key failure, 390px mobile layout, and PDF upload/original-view fallback.
- Three fixed public-source paraphrase cases passed top-1 retrieval and citation mapping. These are regression examples, not a statistically meaningful quality score.
- Production TypeScript/Vite build passed.
- Ruff lint and formatting passed.
- Real EPA article fetch through the DNS-pinned worker succeeded (6,313 extracted characters).
- OTLP/HTTP transport delivered traces, metrics, and logs to a local test receiver.
- Clean archived checkout: locked Python install, 24 tests, 3 evaluation cases, `npm ci`, and production build all passed.
- Desktop reader visually inspected in the Codex browser.

## Pending external validation

Rechecked September 30, 2026: the private `.env` exists and is git-ignored, but both provider keys are empty and effective application settings are not live-ready. Real search/extraction/generation and the real Live browser flow have **not** been exercised. Fill `TAVILY_API_KEY` and `GROQ_API_KEY` in the existing local `.env`, then run `.venv/bin/python scripts/live_smoke.py`. Restart the interactive server and verify a Live RAG answer and its clickable evidence in the browser. Contract fixtures do not validate real account limits, auth, provider availability, or answer quality.

No Grafana Cloud credentials were present. Local trace creation, error status, correlation, content redaction, and all three OTLP signal transports are tested; delivery to a live Grafana backend and dashboard metric-name compatibility require the optional setup in `observability.md`. No hosted deployment was attempted and no paid plan was enabled.

On September 30, Docker was installed but its daemon was unavailable, so the optional real local Grafana check was not run.

The current Starlette version emits a TestClient/httpx deprecation warning; tests pass. This is a test-adapter migration concern, not a runtime failure.

GitHub workflow authorization is configured. The active workflow is `.github/workflows/ci.yml`; it runs the offline verification suite on pushes and pull requests. Live provider checks remain opt-in and require local credentials.

CI now uses Node 24 action releases (checkout 7.0.1, setup-python 7.0.0, setup-node 7.0.0), Node 24 for the frontend build, and Ubuntu 24.04 to avoid an implicit runner-image migration. Checkout does not retain credentials. Playwright owns a separate offline server on port 8001 and explicitly clears provider credentials and telemetry export settings; it never reuses the interactive server.
