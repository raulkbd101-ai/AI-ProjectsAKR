import unittest

from analytics import available_periods, compare_periods, portfolio_summary, program_detail


class AnalyticsTests(unittest.TestCase):
    def test_september_portfolio_totals(self):
        result = portfolio_summary("2026-09")
        self.assertEqual(result["spend_usd"], 342000)
        self.assertEqual(result["modeled_value_usd"], 506000)
        self.assertEqual(result["modeled_net_value_usd"], 164000)
        self.assertEqual(result["open_risks"], 5)

    def test_adoption_is_weighted_by_eligible_users(self):
        self.assertEqual(portfolio_summary("2026-09")["weighted_adoption_pct"], 73.8)

    def test_period_comparison_uses_to_minus_from(self):
        result = compare_periods("2026-07", "2026-09")
        self.assertEqual(result["change"]["spend_usd"], 42000)
        self.assertEqual(result["change"]["open_risks"], -2)

    def test_period_validation(self):
        with self.assertRaisesRegex(ValueError, "Unknown period"):
            portfolio_summary("2026-10")

    def test_program_validation(self):
        with self.assertRaisesRegex(ValueError, "Unknown program_id"):
            program_detail("unknown")

    def test_program_detail_contains_all_sample_periods(self):
        result = program_detail("service-assist")
        self.assertEqual(result["program_name"], "Customer Service Assist")
        self.assertEqual([row["period"] for row in result["observations"]], ["2026-07", "2026-08", "2026-09"])

    def test_available_data_is_discoverable(self):
        self.assertEqual(available_periods()["periods"], ["2026-07", "2026-08", "2026-09"])


if __name__ == "__main__":
    unittest.main()
