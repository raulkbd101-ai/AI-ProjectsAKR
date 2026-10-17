import unittest

from modernization import DOMAINS, STATES, case_study


class ModernizationTests(unittest.TestCase):
    def test_portfolio_summary_is_consistent(self):
        result = case_study()
        summary = result["summary"]
        self.assertEqual(summary["asset_count"], 9)
        self.assertEqual(summary["ready_count"], 4)
        self.assertEqual(summary["remediation_count"], 3)
        self.assertEqual(summary["blocked_count"], 2)
        self.assertEqual(summary["legacy_monthly_cost_usd"], 11260)
        self.assertEqual(summary["target_monthly_cost_usd"], 8750)
        self.assertEqual(summary["modeled_monthly_delta_usd"], 2510)

    def test_readiness_and_latency_are_computed(self):
        summary = case_study()["summary"]
        self.assertAlmostEqual(summary["readiness_pct"], 44.4)
        self.assertEqual(summary["legacy_avg_latency_s"], 50.4)
        self.assertEqual(summary["target_avg_latency_s"], 10.9)
        self.assertEqual(summary["modeled_latency_reduction_pct"], 78.4)

    def test_domain_filter_returns_only_matching_assets(self):
        result = case_study(domain="Finance")
        self.assertEqual(result["summary"]["asset_count"], 3)
        self.assertTrue(all(row["domain"] == "Finance" for row in result["assets"]))

    def test_state_filter_returns_only_matching_assets(self):
        result = case_study(state="Blocked")
        self.assertEqual(result["summary"]["blocked_count"], 2)
        self.assertTrue(all(row["state"] == "Blocked" for row in result["assets"]))

    def test_combined_filters_work(self):
        result = case_study(domain="Finance", state="Blocked")
        self.assertEqual([row["id"] for row in result["assets"]], ["BI-003"])
        self.assertEqual(result["summary"]["asset_count"], 1)

    def test_unmatched_combined_filter_has_zero_metrics(self):
        summary = case_study(domain="Sales", state="Blocked")["summary"]
        self.assertEqual(summary["asset_count"], 0)
        self.assertEqual(summary["readiness_pct"], 0)
        self.assertEqual(summary["legacy_avg_latency_s"], 0)
        self.assertEqual(summary["modeled_latency_reduction_pct"], 0)

    def test_unknown_domain_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown domain"):
            case_study(domain="Engineering")

    def test_unknown_state_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown migration state"):
            case_study(state="Done")

    def test_domain_comparison_reconciles_to_filtered_costs(self):
        result = case_study()
        self.assertEqual(sum(row["legacy_cost_usd"] for row in result["domains"]), result["summary"]["legacy_monthly_cost_usd"])
        self.assertEqual(sum(row["target_cost_usd"] for row in result["domains"]), result["summary"]["target_monthly_cost_usd"])

    def test_wave_plan_covers_all_assets(self):
        self.assertEqual(sum(wave["asset_count"] for wave in case_study()["waves"]), len(case_study()["assets"]))

    def test_gate_and_prototype_disclosure_are_returned(self):
        result = case_study()
        self.assertGreaterEqual(len(result["gates"]), 4)
        self.assertIn("synthetic", result["prototype_note"])

    def test_results_do_not_mutate_source_dataset(self):
        result = case_study()
        result["assets"].clear()
        self.assertEqual(case_study()["summary"]["asset_count"], 9)


if __name__ == "__main__":
    unittest.main()
