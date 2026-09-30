# Provider references

Official docs checked September 29, 2026. Recheck account-specific limits before using Live.

- [Tavily Search](https://docs.tavily.com/documentation/api-reference/endpoint/search): `POST https://api.tavily.com/search`, bearer token, basic search with five results and automatic parameter selection disabled.
- [Tavily Extract](https://docs.tavily.com/documentation/api-reference/endpoint/extract): `POST https://api.tavily.com/extract`, basic extraction, Markdown output, up to five URLs.
- [Tavily credits](https://docs.tavily.com/documentation/api-credits): published free monthly credit allowance and per-operation accounting. The app conservatively reserves two credits even when fewer extractions succeed.
- [Groq API](https://console.groq.com/docs/api-reference): OpenAI-compatible chat completions endpoint, bearer token, `max_completion_tokens`, messages, choices and usage.
- [Groq model](https://console.groq.com/docs/model/openai/gpt-oss-20b): model ID `openai/gpt-oss-20b`.
- [Groq rate limits](https://console.groq.com/docs/rate-limits): free-plan example limits and header semantics. `x-ratelimit-remaining-requests` refers to requests/day; `x-ratelimit-remaining-tokens` refers to tokens/minute. Headers are snapshots, not a monthly unified meter.
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/instrumentation/): explicit tracer and meter providers and manual spans.
- [Grafana OTLP](https://grafana.com/docs/grafana-cloud/send-data/otlp/otlp-format-considerations/): HTTP/protobuf export and metric-name conversion.
- [Grafana local LGTM](https://grafana.com/docs/opentelemetry/docker-lgtm/): optional local backend for development.
- [EPA trees and vegetation](https://www.epa.gov/heatislands/benefits-trees-and-vegetation): source for the prepared trees example. The bundled sample and evidence are original explanatory paraphrases, not copied page text.
