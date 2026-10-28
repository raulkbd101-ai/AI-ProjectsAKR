import contextlib
import io
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import database
import evidence
import matcher


class TransferableBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.db_path = str(Path(self.temp_dir.name) / "bridge_test.db")
        self.patches = [
            patch.object(database, "DB_FILE", self.db_path),
            patch.object(evidence, "DB_FILE", self.db_path),
            patch.object(matcher, "DB_FILE", self.db_path),
        ]
        for active_patch in self.patches:
            active_patch.start()
        with contextlib.redirect_stdout(io.StringIO()):
            database.init_db()
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute("""INSERT INTO master_profile
                (full_name, title, years_experience, location, notice_period_days,
                 min_ctc_lpa, core_domains, core_tech_stack)
                VALUES ('Test Candidate', 'Test Role', 1, 'Test City', 0, 0, '[]', '{}')""")

    def tearDown(self):
        for active_patch in reversed(self.patches):
            active_patch.stop()
        self.temp_dir.cleanup()

    def add_claim(self, competency, claim, persona="All"):
        return evidence.add_evidence_claim(evidence.EvidenceClaim(
            competency=competency,
            claim=claim,
            evidence_summary="A project summary supports this candidate-authored claim.",
            source_reference="Candidate profile evidence record",
            target_persona=persona,
        ))

    def test_bridge_requires_explicit_matching_evidence(self):
        claim_id = self.add_claim("Cloud architecture", "I designed a GCP cloud architecture.", "Architect")

        bridges = matcher.generate_transferable_bridges(["AWS"], "Architect")
        self.assertEqual(len(bridges), 1)
        self.assertEqual(bridges[0]["source_technology"], "GCP")
        self.assertEqual(bridges[0]["supporting_evidence_id"], claim_id)
        self.assertEqual(bridges[0]["supporting_claim"], "I designed a GCP cloud architecture.")
        self.assertEqual(bridges[0]["supporting_evidence_status"], "self_reported")
        self.assertEqual(bridges[0]["supporting_source_reference"], "Candidate profile evidence record")
        self.assertTrue(bridges[0]["review_required"])
        self.assertIn("does not establish hands-on AWS use", bridges[0]["statement"])
        self.assertIn("Conceptual adjacency only", bridges[0]["disclaimer"])

    def test_expanded_data_and_legacy_mappings_still_require_evidence(self):
        self.add_claim("Data warehouse", "I designed a BigQuery data warehouse.")
        self.add_claim("Legacy modernization", "I modernized an MFC legacy system.")

        warehouse_bridges = matcher.generate_transferable_bridges(
            ["Snowflake", "Databricks"], "All"
        )
        legacy_bridges = matcher.generate_transferable_bridges(
            ["Go", "Cloud Microservices", "Modern Distributed Architectures"], "All"
        )

        self.assertEqual(
            {bridge["target_technology"] for bridge in warehouse_bridges},
            {"Snowflake", "Databricks"},
        )
        self.assertEqual(
            {bridge["target_technology"] for bridge in legacy_bridges},
            {"Go", "Cloud Microservices", "Modern Distributed Architectures"},
        )
        self.assertTrue(all(bridge["supporting_evidence_id"] for bridge in warehouse_bridges + legacy_bridges))
        self.assertTrue(all("does not establish hands-on" in bridge["statement"] for bridge in warehouse_bridges + legacy_bridges))

    def test_data_engineering_evidence_can_support_kafka_conceptual_bridge(self):
        claim_id = self.add_claim(
            "Data engineering",
            "I led enterprise data engineering and data pipelines across cloud platforms.",
        )
        bridges = matcher.generate_transferable_bridges(["Kafka"], "All")
        self.assertEqual(len(bridges), 1)
        self.assertEqual(bridges[0]["supporting_evidence_id"], claim_id)
        self.assertEqual(bridges[0]["source_technology"], "data engineering")

    def test_bridge_omitted_without_support_or_for_another_persona(self):
        self.add_claim("Cloud architecture", "I designed a GCP cloud architecture.", "Director")
        self.assertEqual(matcher.generate_transferable_bridges(["AWS"], "Architect"), [])
        self.assertEqual(matcher.generate_transferable_bridges(["Snowflake"], "Director"), [])

    def test_only_known_mapping_keywords_are_considered(self):
        self.add_claim("Cloud architecture", "I designed a GCP cloud architecture.")
        self.assertEqual(matcher.generate_transferable_bridges(["Kubernetes"], "All"), [])

    def test_all_cloud_sources_can_generate_persona_supported_bridges(self):
        with contextlib.redirect_stdout(io.StringIO()):
            database.seed_multicloud_profile()
        bridges = matcher.generate_transferable_bridges(["AWS", "Azure", "GCP"], "Architect")
        self.assertEqual({bridge["target_technology"] for bridge in bridges}, {"AWS", "Azure", "GCP"})
        self.assertTrue(all(bridge["review_required"] for bridge in bridges))
        self.assertTrue(all(bridge["target_persona"] == "Architect" for bridge in bridges))


if __name__ == "__main__":
    unittest.main()
