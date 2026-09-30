"""Verify OTLP/HTTP transport for all signals against a local sink; not Grafana."""

import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

received = {}


class Sink(BaseHTTPRequestHandler):
    def do_POST(self):
        payload = self.rfile.read(int(self.headers["Content-Length"]))
        received[self.path] = received.get(self.path, 0) + len(payload)
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


server = HTTPServer(("127.0.0.1", 0), Sink)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
env = {
    **os.environ,
    "OTEL_EXPORTER_OTLP_ENDPOINT": f"http://127.0.0.1:{server.server_port}",
    "OTEL_EXPORTER_OTLP_HEADERS": "",
}
for signal in ("TRACES", "METRICS", "LOGS"):
    env[f"OTEL_EXPORTER_OTLP_{signal}_ENDPOINT"] = (
        f"http://127.0.0.1:{server.server_port}/v1/{signal.lower()}"
    )
    env[f"OTEL_EXPORTER_OTLP_{signal}_HEADERS"] = ""
code = """
from passage_scout.telemetry import stage, tokens, retrieved
with stage('smoke.transport'):
    tokens.add(1, {'provider': 'smoke'})
    retrieved.add(1)
"""
try:
    result = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, timeout=20, check=False
    )
    assert result.returncode == 0, "Telemetry subprocess failed"
    assert {"/v1/traces", "/v1/metrics", "/v1/logs"} <= received.keys(), received
    print("OTLP/HTTP local sink received traces, metrics, and logs.")
finally:
    server.shutdown()
    server.server_close()
