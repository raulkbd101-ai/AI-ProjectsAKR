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

    def test_strong_job_match_is_approved(self):
        result = matcher.evaluate_job_match(
            "BI Platform Delivery Manager",
            "Example GCC",
            "Looking for a BI Platform Delivery Manager with expertise in Python, "
            "Snowflake, Tableau, and enterprise cloud transformations.",
        )

        self.assertGreaterEqual(result["match_score"], 90)
        self.assertTrue(result["is_approved"])
        self.assertIn("Python", result["matched_competencies"])

    def test_low_overlap_job_is_blocked(self):
        result = matcher.evaluate_job_match(
            "Junior Support Associate",
            "Example Company",
            "Entry-level support role. No architecture or analytics experience required.",
        )

        self.assertLess(result["match_score"], 90)
        self.assertFalse(result["is_approved"])

    def test_approved_evaluation_is_recorded(self):
        result = matcher.evaluate_job_match(
            "BI Platform Delivery Manager",
            "Example GCC",
            "Looking for a BI Platform Delivery Manager with expertise in Python, "
            "Snowflake, Tableau, and enterprise cloud transformations.",
        )

        response = matcher.record_application(result, "https://example.com/jobs/123")

        self.assertTrue(response["success"])
        self.assertEqual(database.check_daily_limit()["today_count"], 1)

    def test_blocked_evaluation_is_not_recorded(self):
        result = matcher.evaluate_job_match(
            "Junior Support Associate",
            "Example Company",
            "Entry-level support role. No architecture or analytics experience required.",
        )

        response = matcher.record_application(result)

        self.assertFalse(response["success"])
        self.assertEqual(database.check_daily_limit()["today_count"], 0)


if __name__ == "__main__":
    unittest.main()
