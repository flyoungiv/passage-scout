# Observability

The app creates `rag.request`, `rag.search`, `rag.extract`, `rag.rank`, `rag.generate`, and input-processing spans. Logs carry trace/span IDs. Metrics:

| Instrument | Kind | Meaning |
|---|---|---|
| `scout.stage.duration` | Histogram, seconds | Stage latency with stage/outcome labels |
| `scout.stage.errors` | Counter | Failed stages |
| `scout.provider.tokens` | Counter | Groq-reported total tokens |
| `scout.retrieval.passages` | Counter | Ranked passages supplied to context construction |

No document text, question text, selections, full URLs, exception bodies, or keys are logged by the application. Export is disabled without an OTLP endpoint. The standard SDK batches telemetry; allow time for export. SDK shutdown flushes on normal process exit. Hard kills can lose the last batch.

## Local Grafana (optional, free software)

If Docker is already installed:

```sh
docker run --rm --name passage-scout-otel \
  -p 127.0.0.1:3000:3000 -p 127.0.0.1:4318:4318 \
  grafana/otel-lgtm:latest
```

This follows Grafana's development image; `latest` is intentionally not a production pin. For a repeatable infrastructure environment, select and record an image digest after testing on your machine. Add `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318` to `.env`, restart Passage Scout, then generate requests. Open http://localhost:3000 (development credentials `admin` / `admin`). Keep these ports loopback-only.

Import `docs/grafana-dashboard.json` and choose the Prometheus/Mimir data source. Use Explore with Tempo to search the response trace ID, and Loki to inspect correlated sanitized logs. Depending on the collector's translation strategy, metric names may have unit suffixes; inspect the metric browser if a panel is empty.

## Grafana Cloud Free (optional)

Use an existing Free stack's OpenTelemetry setup page to obtain its OTLP endpoint and auth headers. Put them only in local `.env` as `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS`. Use HTTP/protobuf; the Python exporters append signal paths. Do not commit headers or enable a paid plan. Cloud quotas and retention are account-specific. No cloud account or paid plan is created by this repository.

Traces, metrics, and sanitized application logs all use the configured endpoint. Avoid turning on broad third-party debug logging in a deployment; it can capture information outside the app's privacy controls.
