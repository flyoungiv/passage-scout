"""Content-free stage telemetry. No automatic HTTP instrumentation or exception payloads."""

import json
import logging
import os
import time
from contextlib import contextmanager

from dotenv import load_dotenv
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Status, StatusCode

load_dotenv()
resource = Resource.create({"service.name": "passage-scout"})
trace_provider = TracerProvider(resource=resource)
readers = []
if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    trace_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    readers.append(PeriodicExportingMetricReader(OTLPMetricExporter()))
trace.set_tracer_provider(trace_provider)
metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=readers))
tracer = trace.get_tracer("passage-scout")
meter = metrics.get_meter("passage-scout")
latency = meter.create_histogram("scout.stage.duration", unit="s")
errors = meter.create_counter("scout.stage.errors")
tokens = meter.create_counter("scout.provider.tokens", unit="{token}")
retrieved = meter.create_counter("scout.retrieval.passages", unit="{passage}")
logger = logging.getLogger("passage_scout")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())


@contextmanager
def stage(name: str):
    start = time.perf_counter()
    with tracer.start_as_current_span(
        name, record_exception=False, set_status_on_exception=False
    ) as span:
        outcome = "ok"
        try:
            yield span
        except Exception:
            outcome = "error"
            span.set_status(Status(StatusCode.ERROR))
            errors.add(1, {"stage": name})
            raise
        finally:
            elapsed = time.perf_counter() - start
            latency.record(elapsed, {"stage": name, "outcome": outcome})
            context = span.get_span_context()
            logger.info(
                json.dumps(
                    {
                        "stage": name,
                        "outcome": outcome,
                        "duration_ms": round(elapsed * 1000, 2),
                        "trace_id": f"{context.trace_id:032x}",
                        "span_id": f"{context.span_id:016x}",
                    }
                )
            )


if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

    log_provider = LoggerProvider(resource=resource)
    log_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    # Attach only our sanitized logger, never all third-party/provider logs.
    logger.addHandler(LoggingHandler(logger_provider=log_provider))
