import unittest

from observability import (
    ALL_OUTCOMES,
    ALL_VERSIONS,
    RUNS,
    VERSIONS,
    dashboard_data,
    evaluate_run,
    release_comparison,
    summarize_runs,
)


class EvaluationTests(unittest.TestCase):
    def test_quality_score_uses_documented_weighting(self):
        result = evaluate_run(RUNS[0])
        self.assertEqual(result["quality_score"], 94.4)
        self.assertTrue(result["passed"])

    def test_failed_safety_gate_fails_even_with_other_high_scores(self):
        result = evaluate_run(RUNS[-1])
        self.assertFalse(result["passed"])
        self.assertIn("Safety evaluation failed", result["gate_reasons"])

    def test_policy_gate_reason_is_explained(self):
        result = evaluate_run(RUNS[-1])
        self.assertTrue(any("Policy adherence" in reason for reason in result["gate_reasons"]))

    def test_all_runs_summary(self):
        result = dashboard_data()
        self.assertEqual(result["summary"]["run_count"], 8)
        self.assertEqual(result["summary"]["pass_count"], 7)
        self.assertEqual(result["summary"]["pass_rate_pct"], 87.5)
        self.assertEqual(result["summary"]["total_cost_usd"], 0.132)

    def test_release_summary_reports_latency_percentile(self):
        result = summarize_runs(list(RUNS), "all")
        self.assertEqual(result["average_latency_ms"], 1040)
        self.assertEqual(result["p95_latency_ms"], 1450)

    def test_release_comparison_highlights_quality_regression_and_latency_gain(self):
        result = release_comparison()
        self.assertEqual(result["change"]["pass_rate_percentage_points"], -25.0)
        self.assertEqual(result["change"]["average_latency_ms"], -205)

    def test_version_filter_limits_runs_and_metrics(self):
        result = dashboard_data("v1.5.0")
        self.assertEqual(result["summary"]["run_count"], 4)
        self.assertEqual(result["summary"]["pass_rate_pct"], 75.0)
        self.assertTrue(all(run["version"] == "v1.5.0" for run in result["runs"]))

    def test_outcome_filter_selects_only_failed_trace(self):
        result = dashboard_data(ALL_VERSIONS, "Failed")
        self.assertEqual(len(result["runs"]), 1)
        self.assertEqual(result["runs"][0]["run_id"], "run-008")

    def test_trace_spans_add_up_to_end_to_end_latency(self):
        for run in RUNS:
            self.assertEqual(sum(span["duration_ms"] for span in run["spans"]), run["latency_ms"])

    def test_versions_and_outcomes_are_discoverable(self):
        data = dashboard_data()
        self.assertEqual(data["versions"], list(VERSIONS))
        self.assertEqual(data["selection"], {"version": ALL_VERSIONS, "outcome": ALL_OUTCOMES})

    def test_invalid_version_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "version must be"):
            dashboard_data("v9.9.9")

    def test_invalid_outcome_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "outcome must be"):
            dashboard_data(ALL_VERSIONS, "Unknown")


if __name__ == "__main__":
    unittest.main()
