"""Governed Agentic BI demo using only the Python standard library.

This is an educational prototype. The selected demo role is not authentication.
Production deployments must derive identity and roles from a trusted identity provider.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "demo.sqlite3"
AUDIT_PATH = BASE_DIR / "audit.jsonl"
HOST = os.environ.get("DEMO_HOST", "127.0.0.1")
PORT = int(os.environ.get("DEMO_PORT", "8000"))

# Every record is invented for this demo. No employer or customer data is used.
SAMPLE_ROWS = [
    ("North", "Platform", 184000, 14),
    ("North", "Analytics", 126000, 9),
    ("South", "Platform", 151000, 11),
    ("South", "Analytics", 98000, 7),
    ("West", "Platform", 213000, 16),
    ("West", "Analytics", 142000, 10),
    ("East", "Platform", 167000, 12),
    ("East", "Analytics", 119000, 8),
]

# Demo policy: the manager sees only West, the analyst sees all regions, and the
# viewer sees only totals (no region/segment breakdown). Enforced on the server.
ROLE_POLICY = {
    "analyst": {"region": None, "detail": True},
    "regional_manager": {"region": "West", "detail": True},
    "executive_viewer": {"region": None, "detail": False},
}

INTENT_PATTERNS = [
    ("revenue_by_region", re.compile(r"\b(revenue|sales|amount)\b.*\b(region|regional)\b|\b(region|regional)\b.*\b(revenue|sales|amount)\b", re.I)),
    ("headcount_by_region", re.compile(r"\b(headcount|people|employees|staff)\b.*\b(region|regional)\b|\b(region|regional)\b.*\b(headcount|people|employees|staff)\b", re.I)),
    ("total_revenue", re.compile(r"\b(total|overall|all)\b.*\b(revenue|sales|amount)\b|\b(revenue|sales|amount)\b", re.I)),
]


def initialize_database() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS performance (region TEXT, segment TEXT, revenue INTEGER, headcount INTEGER)")
        count = conn.execute("SELECT COUNT(*) FROM performance").fetchone()[0]
        if count == 0:
            conn.executemany("INSERT INTO performance VALUES (?, ?, ?, ?)", SAMPLE_ROWS)


def record_audit(role: str, intent: str, outcome: str, reason: str | None = None) -> str:
    request_id = str(uuid.uuid4())
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "role": role,
        "intent": intent,
        "outcome": outcome,
    }
    if reason:
        entry["reason"] = reason
    with AUDIT_PATH.open("a", encoding="utf-8") as audit:
        audit.write(json.dumps(entry, separators=(",", ":")) + "\n")
    return request_id


def classify_intent(question: str) -> str | None:
    for intent, pattern in INTENT_PATTERNS:
        if pattern.search(question):
            return intent
    return None


def run_approved_query(intent: str, role: str) -> dict:
    policy = ROLE_POLICY[role]
    if intent == "total_revenue":
        sql = "SELECT SUM(revenue) FROM performance"
        params: tuple = ()
        if policy["region"]:
            sql += " WHERE region = ?"
            params = (policy["region"],)
        with sqlite3.connect(DB_PATH) as conn:
            total = conn.execute(sql, params).fetchone()[0] or 0
        return {"intent": intent, "data": [{"metric": "revenue", "value": total}], "scope": policy["region"] or "all regions"}

    if not policy["detail"]:
        raise PermissionError("This role can view organization-wide totals only.")

    metric = "revenue" if intent == "revenue_by_region" else "headcount"
    sql = f"SELECT region, SUM({metric}) FROM performance"
    params = ()
    if policy["region"]:
        sql += " WHERE region = ?"
        params = (policy["region"],)
    sql += " GROUP BY region ORDER BY region"
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(sql, params).fetchall()
    return {"intent": intent, "data": [{"region": row[0], "value": row[1]} for row in rows], "scope": policy["region"] or "all regions"}


class Handler(BaseHTTPRequestHandler):
    server_version = "GovernedAgenticBI/1.0"

    def send_json(self, status: int, body: dict) -> None:
        raw = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            page = (BASE_DIR / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return

        if parsed.path != "/api/ask":
            self.send_json(404, {"error": "not_found"})
            return

        params = parse_qs(parsed.query)
        question = params.get("q", [""])[0].strip()
        role = params.get("role", [""])[0]
        if role not in ROLE_POLICY:
            request_id = record_audit("unknown", "unclassified", "denied", "invalid_role")
            self.send_json(400, {"error": "invalid_role", "request_id": request_id})
            return
        if not question or len(question) > 240:
            request_id = record_audit(role, "unclassified", "denied", "invalid_question")
            self.send_json(400, {"error": "question_must_be_1_to_240_characters", "request_id": request_id})
            return

        intent = classify_intent(question)
        if intent is None:
            request_id = record_audit(role, "unclassified", "denied", "intent_not_allowlisted")
            self.send_json(422, {"error": "I could not map that to an approved demo metric. Try revenue by region, total revenue, or headcount by region.", "request_id": request_id})
            return
        try:
            result = run_approved_query(intent, role)
        except PermissionError as exc:
            request_id = record_audit(role, intent, "denied", "role_scope")
            self.send_json(403, {"error": str(exc), "request_id": request_id})
            return
        request_id = record_audit(role, intent, "allowed")
        self.send_json(200, {**result, "request_id": request_id, "note": "Deterministic demo router; no external LLM is called."})

    def log_message(self, fmt: str, *args: object) -> None:
        # Keep console output concise; audit details go to audit.jsonl.
        print(f"{self.log_date_time_string()} {self.address_string()} {fmt % args}")


if __name__ == "__main__":
    initialize_database()
    print(f"Governed Agentic BI demo: http://{HOST}:{PORT}")
    print("Demo roles are for illustration only; do not expose this server to a network.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
