import unittest

from cost_model import ALL_TEAMS, PERIODS, TEAMS, dashboard_data


class DashboardDataTests(unittest.TestCase):
    def test_portfolio_total_and_budget_variance(self):
        result = dashboard_data("2026-09")
        self.assertEqual(result["total_spend"], 28_000)
        self.assertEqual(result["total_budget"], 27_700)
        self.assertEqual(result["budget_variance"], 300)
        self.assertEqual(result["budget_utilization_pct"], 101.1)

    def test_team_filter_limits_summary_and_service_rows(self):
        result = dashboard_data("2026-09", "AI Platform")
        self.assertEqual(result["total_spend"], 13_500)
        self.assertEqual(result["total_budget"], 12_500)
        self.assertEqual([row["team"] for row in result["team_summaries"]], ["AI Platform"])
        self.assertEqual({row["team"] for row in result["service_rows"]}, {"AI Platform"})

    def test_unallocated_shared_spend_reduces_coverage(self):
        result = dashboard_data("2026-09")
        self.assertEqual(result["unallocated_spend"], 2_100)
        self.assertEqual(result["allocation_coverage_pct"], 92.5)

    def test_anomaly_rule_flags_only_model_serving_in_september(self):
        result = dashboard_data("2026-09")
        self.assertEqual(len(result["anomalies"]), 1)
        anomaly = result["anomalies"][0]
        self.assertEqual(anomaly["service"], "Model Serving")
        self.assertEqual(anomaly["team"], "AI Platform")
        self.assertEqual(anomaly["increase"], 5_333.33)
        self.assertEqual(anomaly["increase_pct"], 65.3)

    def test_prior_month_with_no_threshold_crossing_has_no_anomaly(self):
        result = dashboard_data("2026-08")
        self.assertEqual(result["anomalies"], [])

    def test_trend_contains_all_sample_periods(self):
        result = dashboard_data("2026-09")
        self.assertEqual([row["month"] for row in result["trend"]], list(PERIODS))
        self.assertEqual(result["trend"][-1]["spend"], result["total_spend"])

    def test_invalid_month_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "month"):
            dashboard_data("2026-10")

    def test_invalid_team_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "team"):
            dashboard_data("2026-09", "Executive")

    def test_team_budgets_sum_to_all_teams_budget(self):
        all_teams = dashboard_data("2026-09", ALL_TEAMS)
        team_total = sum(dashboard_data("2026-09", team)["total_budget"] for team in TEAMS)
        self.assertEqual(team_total, all_teams["total_budget"])


if __name__ == "__main__":
    unittest.main()
