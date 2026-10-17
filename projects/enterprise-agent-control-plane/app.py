"""Loopback-only HTTP interface for the enterprise agent control-plane demo."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from control_plane import ControlPlane


BASE_DIR = Path(__file__).resolve().parent
HOST = os.environ.get("DEMO_HOST", "127.0.0.1")
PORT = int(os.environ.get("DEMO_PORT", "8003"))
CONTROL_PLANE = ControlPlane()


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict) -> None:
        self._send(status, "application/json; charset=utf-8", json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Content-Length must be an integer") from exc
        if length < 1 or length > 16_384:
            raise ValueError("Request body must be between 1 and 16384 bytes")
        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("Request body must contain valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object")
        return payload

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, "text/html; charset=utf-8", (BASE_DIR / "index.html").read_bytes())
        elif path == "/healthz":
            self._send_json(200, {"status": "ok"})
        elif path == "/api/control-plane":
            self._send_json(200, CONTROL_PLANE.snapshot())
        else:
            self._send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/requests":
                result = CONTROL_PLANE.submit_request(
                    agent_id=payload.get("agent_id"),
                    action=payload.get("action"),
                    data_classification=payload.get("data_classification"),
                    estimated_cost_usd=payload.get("estimated_cost_usd"),
                    rationale=payload.get("rationale", ""),
                )
                self._send_json(201, result)
                return

            parts = path.strip("/").split("/")
            if len(parts) == 4 and parts[:2] == ["api", "requests"] and parts[3] == "decision":
                result = CONTROL_PLANE.decide(unquote(parts[2]), payload.get("decision"), "Local demo reviewer")
                self._send_json(200, result)
                return
            self._send_json(404, {"error": "not_found"})
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.log_date_time_string()} {self.address_string()} {fmt % args}")


if __name__ == "__main__":
    print(f"Enterprise Agent Control Plane: http://{HOST}:{PORT}")
    print("Synthetic local simulation only; requests are never executed. Do not expose this server to a network.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
