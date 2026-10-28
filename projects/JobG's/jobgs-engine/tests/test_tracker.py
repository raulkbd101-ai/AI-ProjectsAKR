import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from starlette.requests import Request

import database
import tracker


def make_request(query=""):
    return Request({
        "type": "http", "method": "GET", "path": "/tracker",
        "query_string": query.encode(), "headers": [],
    })


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.db_path = str(Path(self.temp_dir.name) / "tracker_test.db")
        self.db_patch = patch.object(database, "DB_FILE", self.db_path)
        self.db_patch.start()
        with contextlib.redirect_stdout(io.StringIO()):
            database.init_db()
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute("INSERT INTO companies_inventory (company_name) VALUES ('Example Co')")
            conn.execute("""
                INSERT INTO application_tracker
                    (company_id, company_name, role_title, job_url, location, work_model,
                     raw_description, assigned_persona, domain_tags_json, rag_results_json,
                     transferable_bridges_json, outreach_draft, profile_coverage, status)
                VALUES (1, 'Example Co', 'Director of Data', 'https://example.com/role',
                    'Remote India', 'Remote', 'Data and AI leadership role', 'Director',
                    '["Data/AI"]', ?, '[]', 'Draft only.', 62.5, 'DISCOVERED')
            """, (json.dumps({"retrieval_mode": "hybrid", "matches": [
                {"competency": "Data leadership", "claim": "Candidate claim", "retrieval_score": 0.61,
                 "source_reference": "Candidate notes", "confidentiality": "private"}
            ]}),))
        self.role_id = 1

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_tracker_page_filters_by_persona_domain_and_relevance(self):
        response = tracker.tracker_page(make_request("persona=Director&domain=Data%2FAI&min_relevance=0.5"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Example Co", response.body)
        self.assertIn(b"0.610", response.body)

    def test_invalid_relevance_filter_is_rejected(self):
        with self.assertRaises(Exception) as captured:
            tracker.tracker_page(make_request("min_relevance=1.2"))
        self.assertEqual(captured.exception.status_code, 400)

    def test_status_transition_is_guarded_and_updates_timestamp(self):
        response = tracker.update_tracker_status(self.role_id, "USER_REVIEWED")
        self.assertEqual(response.status_code, 303)
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn, conn:
            self.assertEqual(conn.execute(
                "SELECT status, human_reviewed_at FROM application_tracker WHERE id = ?",
                (self.role_id,),
            ).fetchone()[0], "USER_REVIEWED")
        with self.assertRaises(Exception) as captured:
            tracker.update_tracker_status(self.role_id, "OFFER")
        self.assertEqual(captured.exception.status_code, 409)

    def test_archived_is_terminal(self):
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute("UPDATE application_tracker SET status = 'ARCHIVED' WHERE id = ?", (self.role_id,))
        with self.assertRaises(Exception) as captured:
            tracker.update_tracker_status(self.role_id, "USER_REVIEWED")
        self.assertEqual(captured.exception.status_code, 409)

    def test_export_json_contains_evidence_and_draft(self):
        response = tracker.export_applications("json")
        payload = json.loads(response.body)
        role = payload["roles"][0]
        self.assertEqual(role["evidence_retrieval"]["matches"][0]["claim"], "Candidate claim")
        self.assertEqual(role["outreach_draft"], "Draft only.")
        self.assertIn("attachment;", response.headers["content-disposition"])

    def test_export_redacts_confidential_claim(self):
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute("""UPDATE application_tracker SET rag_results_json = ? WHERE id = ?""", (
                json.dumps({"matches": [{"competency": "Secret", "claim": "Secret text", "confidentiality": "confidential"}]}),
                self.role_id,
            ))
        response = tracker.export_applications("json")
        match = json.loads(response.body)["roles"][0]["evidence_retrieval"]["matches"][0]
        self.assertTrue(match["redacted"])
        self.assertNotIn("claim", match)

    def test_dashboard_counts_and_ratios(self):
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute("UPDATE application_tracker SET status='APPLIED' WHERE id=?", (self.role_id,))
            conn.execute("INSERT INTO daily_applications (apply_date, company_name, role_title, match_score) VALUES (date('now'), 'Example Co', 'Role', 50)")
        analytics = database.get_dashboard_analytics()
        self.assertEqual(analytics["total_tracked_roles"], 1)
        self.assertEqual(analytics["today_count"], 1)
        self.assertEqual(analytics["daily_progress_percent"], 10)
        self.assertEqual(analytics["applied_share_percent"], 100.0)

    def test_legacy_tracker_migration_preserves_role_and_adds_archive(self):
        legacy_path = str(Path(self.temp_dir.name) / "legacy_tracker.db")
        with contextlib.closing(sqlite3.connect(legacy_path)) as conn, conn:
            conn.execute("CREATE TABLE companies_inventory (id INTEGER PRIMARY KEY, company_name TEXT NOT NULL UNIQUE)")
            conn.execute("INSERT INTO companies_inventory VALUES (1, 'Legacy Co')")
            conn.execute("""
                CREATE TABLE application_tracker (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER NOT NULL REFERENCES companies_inventory(id),
                    company_name TEXT NOT NULL, role_title TEXT NOT NULL,
                    job_url TEXT NOT NULL UNIQUE, location TEXT NOT NULL DEFAULT '',
                    work_model TEXT NOT NULL DEFAULT 'Unknown', raw_description TEXT NOT NULL,
                    assigned_persona TEXT NOT NULL DEFAULT 'Unclear',
                    domain_tags_json TEXT NOT NULL DEFAULT '[]', triage_json TEXT NOT NULL DEFAULT '{}',
                    rag_results_json TEXT NOT NULL DEFAULT '{}', transferable_bridges_json TEXT NOT NULL DEFAULT '[]',
                    outreach_draft TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'DISCOVERED'
                      CHECK(status IN ('DISCOVERED','REVIEWED','APPLIED','INTERVIEW','OFFER','REJECTED','WITHDRAWN')),
                    human_reviewed_at TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("INSERT INTO application_tracker (company_id, company_name, role_title, job_url, raw_description, status) VALUES (1, 'Legacy Co', 'Architect', 'https://legacy.example/job', 'Description', 'REVIEWED')")

        with patch.object(database, "DB_FILE", legacy_path):
            database.init_job_tables()

        with contextlib.closing(sqlite3.connect(legacy_path)) as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(application_tracker)")}
            table_sql = conn.execute("SELECT sql FROM sqlite_master WHERE name='application_tracker'").fetchone()[0]
            saved = conn.execute("SELECT company_name, status, profile_coverage FROM application_tracker").fetchone()
        self.assertIn("profile_coverage", columns)
        self.assertIn("ARCHIVED", table_sql)
        self.assertEqual(saved, ("Legacy Co", "USER_REVIEWED", None))


if __name__ == "__main__":
    unittest.main()
