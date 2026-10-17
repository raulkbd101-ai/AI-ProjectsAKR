"""Loopback-only web app for the synthetic BI modernization case study."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from modernization import case_study


BASE_DIR = Path(__file__).resolve().parent
HOST = os.environ.get("DEMO_HOST", "127.0.0.1")
PORT = int(os.environ.get("DEMO_PORT", "8004"))


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict) -> None:
        self._send(status, "application/json; charset=utf-8", json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send(200, "text/html; charset=utf-8", (BASE_DIR / "index.html").read_bytes())
        elif parsed.path == "/healthz":
            self._json(200, {"status": "ok"})
        elif parsed.path == "/api/case-study":
            query = parse_qs(parsed.query)
            try:
                self._json(200, case_study(query.get("domain", ["All domains"])[0], query.get("state", ["All states"])[0]))
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
        else:
            self._json(404, {"error": "not_found"})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.log_date_time_string()} {self.address_string()} {fmt % args}")


if __name__ == "__main__":
    print(f"BI Modernization Case Study: http://{HOST}:{PORT}")
    print("Synthetic local scenario only; no BI platform or source system is connected.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
