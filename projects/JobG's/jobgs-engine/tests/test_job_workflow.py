import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
import matcher


class JobWorkflowTests(unittest.TestCase):
    def setUp(self):
        # Keep temporary databases inside the writable project workspace.
        self.temp_dir = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.db_path = str(Path(self.temp_dir.name) / "test_jobgs.db")
        self.database_path_patch = patch.object(database, "DB_FILE", self.db_path)
        self.matcher_path_patch = patch.object(matcher, "DB_FILE", self.db_path)
        self.database_path_patch.start()
        self.matcher_path_patch.start()

        with contextlib.redirect_stdout(io.StringIO()):
            database.init_db()
            database.seed_master_profile()

    def tearDown(self):
        self.matcher_path_patch.stop()
        self.database_path_patch.stop()
        self.temp_dir.cleanup()

    def test_profile_terms_are_reported_without_claiming_job_fit(self):
        result = matcher.evaluate_job_match(
            "BI Platform Delivery Manager",
            "Example GCC",
            "Looking for a BI Platform Delivery Manager with expertise in Python, "
            "Snowflake, Tableau, and enterprise cloud transformations.",
        )

        self.assertEqual(result["profile_coverage"], 30.0)
        self.assertEqual(result["status"], "HUMAN_REVIEW_REQUIRED")
        self.assertIn("Python", result["matched_competencies"])
        self.assertIn("AWS", result["missing_profile_skills"])

    def test_low_profile_term_coverage_is_reported_but_not_blocked(self):
        result = matcher.evaluate_job_match(
            "Junior Support Associate",
            "Example Company",
            "Entry-level support role. No architecture or analytics experience required.",
        )

        self.assertEqual(result["profile_coverage"], 0.0)
        self.assertEqual(result["status"], "HUMAN_REVIEW_REQUIRED")

    def test_user_selected_role_is_recorded(self):
        result = matcher.evaluate_job_match(
            "BI Platform Delivery Manager",
            "Example GCC",
            "Looking for a BI Platform Delivery Manager with expertise in Python, "
            "Snowflake, Tableau, and enterprise cloud transformations.",
        )

        response = matcher.record_application(result, "https://example.com/jobs/123")

        self.assertTrue(response["success"])
        self.assertEqual(database.check_daily_limit()["today_count"], 1)

    def test_user_can_record_role_even_with_low_profile_term_coverage(self):
        result = matcher.evaluate_job_match(
            "Junior Support Associate",
            "Example Company",
            "Entry-level support role. No architecture or analytics experience required.",
        )

        response = matcher.record_application(result)

        self.assertTrue(response["success"])
        self.assertEqual(database.check_daily_limit()["today_count"], 1)


if __name__ == "__main__":
    unittest.main()
