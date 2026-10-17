"""Local HTTP server for the AI Observability and Evaluation Starter."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from observability import ALL_OUTCOMES, ALL_VERSIONS, OUTCOMES, VERSIONS, dashboard_data


BASE_DIR = Path(__file__).resolve().parent
HOST = os.environ.get("DEMO_HOST", "127.0.0.1")
PORT = int(os.environ.get("DEMO_PORT", "8002"))


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self._send(status, "application/json; charset=utf-8", body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send(200, "text/html; charset=utf-8", (BASE_DIR / "index.html").read_bytes())
            return
        if parsed.path == "/healthz":
            self._send_json(200, {"status": "ok"})
            return
        if parsed.path != "/api/dashboard":
            self._send_json(404, {"error": "not_found"})
            return

        params = parse_qs(parsed.query)
        version = params.get("version", [ALL_VERSIONS])[0]
        outcome = params.get("outcome", [ALL_OUTCOMES])[0]
        try:
            self._send_json(200, dashboard_data(version, outcome))
        except ValueError as exc:
            self._send_json(400, {"error": str(exc), "versions": (ALL_VERSIONS, *VERSIONS), "outcomes": OUTCOMES})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.log_date_time_string()} {self.address_string()} {fmt % args}")


if __name__ == "__main__":
    print(f"AI Observability and Evaluation Starter: http://{HOST}:{PORT}")
    print("Synthetic local demo only; do not expose this server to a network.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
