import contextlib
import io
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import database
import rag_matcher


class RagMatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.db_path = str(Path(self.temp_dir.name) / "rag_matcher_test.db")
        self.database_patch = patch.object(database, "DB_FILE", self.db_path)
        self.matcher_patch = patch.object(rag_matcher, "DB_FILE", self.db_path)
        self.database_patch.start()
        self.matcher_patch.start()
        with contextlib.redirect_stdout(io.StringIO()):
            database.init_db()
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute(
                """INSERT INTO master_profile
                   (full_name, title, years_experience, location, notice_period_days,
                    min_ctc_lpa, core_domains, core_tech_stack)
                   VALUES ('Test Candidate', 'Test Architect', 1, 'Test City', 0, 0, '[]', '{}')"""
            )

    def tearDown(self):
        self.matcher_patch.stop()
        self.database_patch.stop()
        self.temp_dir.cleanup()

    def add_claim(self, competency, claim, persona="All", confidentiality="private"):
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            profile_id = conn.execute(
                "SELECT id FROM master_profile ORDER BY id LIMIT 1"
            ).fetchone()[0]
            cursor = conn.execute(
                """INSERT INTO profile_evidence
                   (profile_id, competency, claim, evidence_summary,
                    target_persona, confidentiality)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    profile_id,
                    competency,
                    claim,
                    "A sanitized project note supports this candidate-provided claim.",
                    persona,
                    confidentiality,
                ),
            )
            return cursor.lastrowid

    def test_keyword_mode_filters_persona_and_excludes_confidential_claims(self):
        shared_id = self.add_claim(
            "Cloud architecture", "I designed a cloud platform.", "All"
        )
        self.add_claim("Cloud delivery", "I led cloud delivery.", "Director")
        self.add_claim(
            "Cloud security", "I designed cloud security controls.", "Architect", "confidential"
        )

        result = rag_matcher.search_evidence(
            "cloud platform", target_persona="Architect", use_embeddings=False
        )

        self.assertEqual(result["retrieval_mode"], "lexical_fallback")
        self.assertEqual([match["evidence_id"] for match in result["matches"]], [shared_id])
        self.assertIsNone(result["matches"][0]["semantic_score"])

    def test_hybrid_score_uses_configured_semantic_and_lexical_weights(self):
        evidence_id = self.add_claim(
            "Cloud architecture", "I designed a multi-region GCP workload."
        )
        # First response embeds the evidence passage; second embeds the query.
        with patch.object(
            rag_matcher,
            "_embed",
            side_effect=[[[0.8, 0.6]], [[1.0, 0.0]]],
        ):
            result = rag_matcher.search_evidence("cloud security", target_persona="Architect")

        match = result["matches"][0]
        self.assertEqual(result["retrieval_mode"], "hybrid")
        self.assertEqual(match["evidence_id"], evidence_id)
        self.assertAlmostEqual(match["semantic_score"], 0.8, places=4)
        self.assertAlmostEqual(match["lexical_score"], 0.5, places=4)
        self.assertAlmostEqual(match["retrieval_score"], 0.695, places=4)

        with closing(sqlite3.connect(self.db_path)) as conn:
            cached = conn.execute(
                "SELECT vector_json FROM evidence_embeddings WHERE evidence_id = ?",
                (evidence_id,),
            ).fetchone()
        self.assertIsNotNone(cached)

    def test_local_model_unavailable_returns_clear_keyword_fallback(self):
        self.add_claim("Cloud architecture", "I designed a cloud platform.")
        with patch.object(
            rag_matcher, "_embed", side_effect=RuntimeError("Local Ollama is unavailable.")
        ):
            result = rag_matcher.search_evidence("cloud platform", target_persona="Architect")

        self.assertEqual(result["retrieval_mode"], "lexical_fallback")
        self.assertEqual(len(result["matches"]), 1)
        self.assertIn("Ollama is unavailable", result["warning"])


if __name__ == "__main__":
    unittest.main()
