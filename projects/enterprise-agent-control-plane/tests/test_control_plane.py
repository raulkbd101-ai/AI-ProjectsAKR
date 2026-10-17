import unittest

from control_plane import ControlPlane


class ControlPlaneTests(unittest.TestCase):
    def setUp(self):
        self.plane = ControlPlane()

    def submit(self, **overrides):
        payload = {
            "agent_id": "knowledge-assistant",
            "action": "search_knowledge",
            "data_classification": "public",
            "estimated_cost_usd": 0.02,
            "rationale": "Find an approved answer",
        }
        payload.update(overrides)
        return self.plane.submit_request(**payload)

    def test_seeded_snapshot_has_three_examples_and_audit_events(self):
        state = self.plane.snapshot()
        self.assertEqual(state["summary"]["request_count"], 3)
        self.assertEqual(state["summary"]["event_count"], 3)
        self.assertEqual(state["summary"]["allowed"], 1)
        self.assertEqual(state["summary"]["pending_approval"], 1)
        self.assertEqual(state["summary"]["denied"], 1)

    def test_in_scope_allowlisted_action_within_budget_is_allowed(self):
        self.assertEqual(self.submit()["decision"], "allowed")

    def test_sensitive_action_is_held_for_approval(self):
        result = self.submit(agent_id="service-agent", action="issue_refund", data_classification="customer", estimated_cost_usd=0.12)
        self.assertEqual(result["decision"], "pending_approval")

    def test_restricted_classification_requires_approval(self):
        result = self.submit(agent_id="operations-agent", action="read_metrics", data_classification="restricted", estimated_cost_usd=0.02)
        self.assertEqual(result["decision"], "pending_approval")

    def test_non_allowlisted_tool_is_denied(self):
        result = self.submit(agent_id="service-agent", action="export_customers", data_classification="customer")
        self.assertEqual(result["decision"], "denied")
        self.assertIn("allowlist", result["reason"])

    def test_out_of_scope_data_is_denied(self):
        result = self.submit(data_classification="customer")
        self.assertEqual(result["decision"], "denied")
        self.assertIn("scope", result["reason"])

    def test_cost_over_agent_budget_is_denied(self):
        result = self.submit(estimated_cost_usd=0.06)
        self.assertEqual(result["decision"], "denied")
        self.assertIn("budget", result["reason"])

    def test_unknown_agent_is_denied(self):
        result = self.submit(agent_id="unregistered-agent")
        self.assertEqual(result["decision"], "denied")

    def test_invalid_classification_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "data_classification"):
            self.submit(data_classification="secret")

    def test_negative_cost_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "finite non-negative"):
            self.submit(estimated_cost_usd=-0.01)

    def test_non_finite_cost_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "finite non-negative"):
            self.submit(estimated_cost_usd=float("inf"))

    def test_approval_changes_state_and_adds_reviewer_audit_event_without_execution(self):
        result = self.plane.decide("REQ-DEMO-002", "approve", "Portfolio reviewer")
        self.assertEqual(result["decision"], "approved")
        self.assertEqual(result["reviewer"], "Portfolio reviewer")
        self.assertIn("approved", result["reason"])
        self.assertIn("Not executed", result["execution_status"])
        event = self.plane.snapshot()["events"][0]
        self.assertEqual(event["actor"], "Portfolio reviewer")
        self.assertEqual(event["event_type"], "approved")

    def test_rejection_records_rejected_state(self):
        result = self.plane.decide("REQ-DEMO-002", "reject")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("rejected", result["reason"])

    def test_only_pending_requests_can_be_decided(self):
        with self.assertRaisesRegex(ValueError, "only pending"):
            self.plane.decide("REQ-DEMO-001", "approve")

    def test_unknown_request_cannot_be_decided(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            self.plane.decide("REQ-MISSING", "approve")

    def test_snapshot_is_a_defensive_copy(self):
        state = self.plane.snapshot()
        state["requests"].clear()
        self.assertEqual(self.plane.snapshot()["summary"]["request_count"], 3)


if __name__ == "__main__":
    unittest.main()
