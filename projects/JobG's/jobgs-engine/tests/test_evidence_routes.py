import contextlib
import io
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from starlette.requests import Request

import app
import database
import evidence


def make_request(path="/evidence", query_string=b""):
    return Request({
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": query_string,
        "headers": [],
    })


class EvidenceRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.db_path = str(Path(self.temp_dir.name) / "test_evidence_routes.db")
        self.database_path_patch = patch.object(database, "DB_FILE", self.db_path)
        self.evidence_path_patch = patch.object(evidence, "DB_FILE", self.db_path)
        self.database_path_patch.start()
        self.evidence_path_patch.start()
        with contextlib.redirect_stdout(io.StringIO()):
            database.init_db()
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute("""INSERT INTO master_profile
                (full_name, title, years_experience, location, notice_period_days,
                 min_ctc_lpa, core_domains, core_tech_stack)
                VALUES ('Test Candidate', 'Test Role', 1, 'Test City', 0, 0, '[]', '{}')""")

    def tearDown(self):
        self.evidence_path_patch.stop()
        self.database_path_patch.stop()
        self.temp_dir.cleanup()

    def test_get_evidence_page_renders_empty_state(self):
        response = app.get_evidence_dossier(make_request())

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Evidence-Backed Profile Dossier", response.body)
        self.assertIn(b"No evidence claims recorded yet", response.body)

    def test_home_page_has_prominent_evidence_navigation(self):
        response = app.home(make_request(path="/"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'href="/evidence"', response.body)
        self.assertIn(b"Evidence Dossier", response.body)

    def test_valid_claim_post_saves_and_redirects(self):
        response = app.post_evidence_claim(
            competency="Example capability",
            claim="I completed an example project activity.",
            context="",
            evidence_summary="A private note describes the supporting example.",
            impact_metric="",
            source_reference="",
            evidence_status="self_reported",
            confidentiality="private",
            target_persona="Architect",
        )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/evidence")
        claims = evidence.list_evidence_claims()
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0]["competency"], "Example capability")
        self.assertEqual(claims[0]["target_persona"], "Architect")
        self.assertEqual(len(evidence.list_evidence_claims("Director")), 0)

    def test_invalid_claim_redirect_shows_actionable_error(self):
        response = app.post_evidence_claim(
            competency="Example capability",
            claim="I completed an example project activity.",
            context="",
            evidence_summary="A private note describes the supporting example.",
            impact_metric="",
            source_reference="",
            evidence_status="not-a-supported-status",
            confidentiality="private",
            target_persona="All",
        )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/evidence?error=invalid_claim")
        page = app.get_evidence_dossier(
            make_request(query_string=b"error=invalid_claim")
        )
        self.assertIn(b"Please check the claim fields", page.body)

    def test_claim_content_is_autoescaped_in_html(self):
        app.post_evidence_claim(
            competency="Example capability",
            claim="<script>alert('x')</script>",
            context="",
            evidence_summary="A private note describes the supporting example.",
            impact_metric="",
            source_reference="",
            evidence_status="self_reported",
            confidentiality="private",
            target_persona="All",
        )

        page = app.get_evidence_dossier(make_request())
        self.assertIn(b"&lt;script&gt;", page.body)
        self.assertNotIn(b"<script>alert", page.body)

    def test_database_failure_redirects_without_exposing_details(self):
        broken_db = sqlite3.connect(self.db_path)
        broken_db.execute("DROP TABLE profile_evidence")
        broken_db.commit()
        broken_db.close()

        response = app.post_evidence_claim(
            competency="Example capability",
            claim="I completed an example project activity.",
            context="",
            evidence_summary="A private note describes the supporting example.",
            impact_metric="",
            source_reference="",
            evidence_status="self_reported",
            confidentiality="private",
            target_persona="All",
        )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/evidence?error=save_failed")


if __name__ == "__main__":
    unittest.main()
