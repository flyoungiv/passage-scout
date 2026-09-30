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

Tavily and Groq credentials are not present in the local environment. Real search/extraction/generation has **not** been exercised. Add `TAVILY_API_KEY` and `GROQ_API_KEY` to a local `.env`, then run `.venv/bin/python scripts/live_smoke.py`. Contract fixtures do not validate real account limits, auth, provider availability, or answer quality.

No Grafana Cloud credentials were present. Local trace creation, error status, correlation, content redaction, and all three OTLP signal transports are tested; delivery to a live Grafana backend and dashboard metric-name compatibility require the optional setup in `observability.md`. No hosted deployment was attempted and no paid plan was enabled.

The current Starlette version emits a TestClient/httpx deprecation warning; tests pass. This is a test-adapter migration concern, not a runtime failure.

GitHub workflow authorization is configured. The active workflow is `.github/workflows/ci.yml`; it runs the offline verification suite on pushes and pull requests. Live provider checks remain opt-in and require local credentials.
