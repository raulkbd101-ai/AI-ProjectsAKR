import contextlib
import io
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

import database
import evidence


class EvidenceProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.db_path = str(Path(self.temp_dir.name) / "test_evidence.db")
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

    def test_valid_claim_is_saved_and_listed(self):
        claim = evidence.EvidenceClaim(
            competency="Example capability",
            claim="I completed an example project activity.",
            evidence_summary="A private note describes the supporting example.",
        )

        claim_id = evidence.add_evidence_claim(claim)
        saved_claims = evidence.list_evidence_claims()

        self.assertEqual(len(saved_claims), 1)
        self.assertEqual(saved_claims[0]["id"], claim_id)
        self.assertEqual(saved_claims[0]["evidence_status"], "self_reported")
        self.assertEqual(saved_claims[0]["confidentiality"], "private")

    def test_claim_requires_a_supporting_evidence_note(self):
        with self.assertRaises(ValidationError):
            evidence.EvidenceClaim(
                competency="Example capability",
                claim="I completed an example project activity.",
            )

    def test_evidence_status_does_not_claim_independent_verification(self):
        with self.assertRaises(ValidationError):
            evidence.EvidenceClaim(
                competency="Example capability",
                claim="I completed an example project activity.",
                evidence_summary="A private note describes the supporting example.",
                evidence_status="independently_verified",
            )

    def test_persona_is_strict_and_claims_are_filterable(self):
        shared = evidence.EvidenceClaim(
            competency="Cloud platform",
            claim="I designed a cloud platform architecture.",
            evidence_summary="Architecture decision records support this work.",
            target_persona="All",
        )
        director = evidence.EvidenceClaim(
            competency="Executive delivery",
            claim="I led a portfolio delivery program.",
            evidence_summary="The program plan and outcome summary support it.",
            target_persona="Director",
        )
        evidence.add_evidence_claim(shared)
        evidence.add_evidence_claim(director)

        self.assertEqual(len(evidence.list_evidence_claims("Director")), 2)
        self.assertEqual(len(evidence.list_evidence_claims("Architect")), 1)
        with self.assertRaises(ValidationError):
            evidence.EvidenceClaim(
                competency="Cloud platform",
                claim="I designed a cloud platform architecture.",
                evidence_summary="Architecture decision records support this work.",
                target_persona="Executive",
            )

    def test_init_migrates_existing_evidence_table_without_losing_claims(self):
        legacy_path = str(Path(self.temp_dir.name) / "legacy.db")
        with closing(sqlite3.connect(legacy_path)) as conn, conn:
            conn.execute("""CREATE TABLE master_profile (
                id INTEGER PRIMARY KEY, full_name TEXT NOT NULL, title TEXT NOT NULL,
                years_experience INTEGER NOT NULL, location TEXT NOT NULL,
                notice_period_days INTEGER NOT NULL, min_ctc_lpa REAL NOT NULL,
                video_pitch_url TEXT, core_domains TEXT, core_tech_stack TEXT)""")
            conn.execute("INSERT INTO master_profile VALUES (1,'Example','Role',1,'City',0,0,'','[]','{}')")
            conn.execute("""CREATE TABLE profile_evidence (
                id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL,
                competency TEXT NOT NULL, claim TEXT NOT NULL, context TEXT NOT NULL DEFAULT '',
                evidence_summary TEXT NOT NULL, impact_metric TEXT NOT NULL DEFAULT '',
                source_reference TEXT NOT NULL DEFAULT '',
                evidence_status TEXT NOT NULL DEFAULT 'self_reported',
                confidentiality TEXT NOT NULL DEFAULT 'private', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
            conn.execute("""INSERT INTO profile_evidence
                (profile_id, competency, claim, evidence_summary)
                VALUES (1, 'Cloud architecture', 'I designed cloud architecture.', 'Architecture notes support this claim.')""")

        with patch.object(database, "DB_FILE", legacy_path):
            with contextlib.redirect_stdout(io.StringIO()):
                database.init_db()

        with closing(sqlite3.connect(legacy_path)) as conn:
            claim = conn.execute(
                "SELECT competency, target_persona FROM profile_evidence"
            ).fetchone()
            mapping_count = conn.execute(
                "SELECT COUNT(*) FROM transferable_tech_mapping"
            ).fetchone()[0]
        self.assertEqual(claim, ("Cloud architecture", "All"))
        self.assertGreaterEqual(mapping_count, 1)

    def test_multicloud_profile_seed_is_idempotent(self):
        with contextlib.redirect_stdout(io.StringIO()):
            database.seed_master_profile()
            database.seed_multicloud_profile()
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            stack = conn.execute("SELECT core_tech_stack FROM master_profile").fetchone()[0]
            claims = conn.execute(
                "SELECT competency, evidence_status FROM profile_evidence"
            ).fetchall()
        parsed_stack = __import__("json").loads(stack)
        self.assertTrue({"GCP", "AWS", "Azure"}.issubset(parsed_stack["cloud"]))
        self.assertTrue({"Multi-cloud Architecture", "Cloud Transformation", "Data Engineering"}.issubset(parsed_stack["core"]))
        self.assertEqual(len(claims), 3)
        self.assertTrue(all(status == "self_reported" for _, status in claims))


if __name__ == "__main__":
    unittest.main()
