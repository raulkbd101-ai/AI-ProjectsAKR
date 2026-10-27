import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

import database
import evidence_profile


class EvidenceProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.db_path = str(Path(self.temp_dir.name) / "test_evidence.db")
        self.database_path_patch = patch.object(database, "DB_FILE", self.db_path)
        self.evidence_path_patch = patch.object(evidence_profile, "DB_FILE", self.db_path)
        self.database_path_patch.start()
        self.evidence_path_patch.start()
        with contextlib.redirect_stdout(io.StringIO()):
            database.init_db()
            database.seed_master_profile()

    def tearDown(self):
        self.evidence_path_patch.stop()
        self.database_path_patch.stop()
        self.temp_dir.cleanup()

    def test_valid_claim_is_saved_and_listed(self):
        claim = evidence_profile.EvidenceClaim(
            competency="Example capability",
            claim="I completed an example project activity.",
            evidence_summary="A private note describes the supporting example.",
        )

        claim_id = evidence_profile.add_evidence_claim(claim)
        saved_claims = evidence_profile.list_evidence_claims()

        self.assertEqual(len(saved_claims), 1)
        self.assertEqual(saved_claims[0]["id"], claim_id)
        self.assertEqual(saved_claims[0]["evidence_status"], "self_reported")
        self.assertEqual(saved_claims[0]["confidentiality"], "private")

    def test_claim_requires_a_supporting_evidence_note(self):
        with self.assertRaises(ValidationError):
            evidence_profile.EvidenceClaim(
                competency="Example capability",
                claim="I completed an example project activity.",
            )

    def test_evidence_status_does_not_claim_independent_verification(self):
        with self.assertRaises(ValidationError):
            evidence_profile.EvidenceClaim(
                competency="Example capability",
                claim="I completed an example project activity.",
                evidence_summary="A private note describes the supporting example.",
                evidence_status="independently_verified",
            )


if __name__ == "__main__":
    unittest.main()
