"""In-memory agent registry, deterministic policy checks, and approval audit."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from math import isfinite
from threading import RLock
from typing import Any


CLASSIFICATIONS = ("public", "internal", "customer", "restricted")
APPROVAL_ACTIONS = {"issue_refund", "restart_service"}

AGENT_REGISTRY: dict[str, dict[str, Any]] = {
    "knowledge-assistant": {
        "display_name": "Knowledge Assistant",
        "owner": "Customer Experience",
        "allowed_tools": ["search_knowledge", "draft_response"],
        "data_scopes": ["public", "internal"],
        "per_request_budget_usd": 0.05,
        "description": "Retrieves approved help content and drafts responses for review.",
    },
    "service-agent": {
        "display_name": "Service Workflow Agent",
        "owner": "Customer Operations",
        "allowed_tools": ["search_order", "create_support_ticket", "issue_refund"],
        "data_scopes": ["public", "customer"],
        "per_request_budget_usd": 0.25,
        "description": "Supports order and service workflows with an approval gate for refunds.",
    },
    "operations-agent": {
        "display_name": "Platform Operations Agent",
        "owner": "Platform Engineering",
        "allowed_tools": ["read_metrics", "restart_service"],
        "data_scopes": ["internal", "restricted"],
        "per_request_budget_usd": 0.10,
        "description": "Reads synthetic operational metrics; service restart requires human approval.",
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class ControlPlane:
    """A local-only, in-memory policy demo. It records decisions and never runs tools."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._agents = deepcopy(AGENT_REGISTRY)
        self._requests: list[dict[str, Any]] = []
        self._events: list[dict[str, Any]] = []
        self._seed_examples()

    def _seed_examples(self) -> None:
        examples = (
            ("knowledge-assistant", "search_knowledge", "public", 0.02, "Find the return policy", "allowed", "Policy matched: tool, data scope, and budget are within limits."),
            ("service-agent", "issue_refund", "customer", 0.12, "Refund request needs review", "pending_approval", "Human approval required before this action could proceed."),
            ("service-agent", "export_customers", "customer", 0.10, "Bulk export request", "denied", "Tool is not on this agent's allowlist."),
        )
        for index, (agent, action, data_class, cost, rationale, decision, reason) in enumerate(examples, start=1):
            request_id = f"REQ-DEMO-{index:03d}"
            created_at = _now()
            request = {
                "request_id": request_id,
                "agent_id": agent,
                "action": action,
                "data_classification": data_class,
                "estimated_cost_usd": cost,
                "rationale": rationale,
                "decision": decision,
                "reason": reason,
                "created_at": created_at,
                "reviewer": None,
                "execution_status": "Not executed — control-plane demo only",
                "is_example": True,
            }
            self._requests.append(request)
            self._append_event(request, "Policy engine", decision, reason, created_at)

    def _append_event(self, request: dict[str, Any], actor: str, event_type: str, detail: str, timestamp: str | None = None) -> None:
        self._events.insert(0, {
            "event_id": f"EVT-{len(self._events) + 1:04d}",
            "request_id": request["request_id"],
            "timestamp": timestamp or _now(),
            "actor": actor,
            "event_type": event_type,
            "agent_id": request["agent_id"],
            "action": request["action"],
            "detail": detail,
        })

    def _policy_decision(self, agent_id: str, action: str, data_classification: str, cost: float) -> tuple[str, str]:
        agent = self._agents.get(agent_id)
        if agent is None:
            return "denied", "Agent is not registered in the control plane."
        if action not in agent["allowed_tools"]:
            return "denied", "Tool is not on this agent's allowlist."
        if data_classification not in agent["data_scopes"]:
            return "denied", "Data classification is outside this agent's approved scope."
        if cost > agent["per_request_budget_usd"]:
            return "denied", f"Estimated cost exceeds this agent's ${agent['per_request_budget_usd']:.2f} per-request budget."
        if action in APPROVAL_ACTIONS or data_classification == "restricted":
            return "pending_approval", "Human approval required before this action could proceed."
        return "allowed", "Policy matched: tool, data scope, and budget are within limits."

    def submit_request(
        self,
        agent_id: str,
        action: str,
        data_classification: str,
        estimated_cost_usd: float,
        rationale: str = "",
    ) -> dict[str, Any]:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id is required")
        if not isinstance(action, str) or not action.strip():
            raise ValueError("action is required")
        if data_classification not in CLASSIFICATIONS:
            raise ValueError(f"data_classification must be one of: {', '.join(CLASSIFICATIONS)}")
        if isinstance(estimated_cost_usd, bool) or not isinstance(estimated_cost_usd, (int, float)) or not isfinite(estimated_cost_usd) or estimated_cost_usd < 0:
            raise ValueError("estimated_cost_usd must be a finite non-negative number")
        if not isinstance(rationale, str) or len(rationale) > 300:
            raise ValueError("rationale must be text no longer than 300 characters")

        agent_id = agent_id.strip()
        action = action.strip()
        with self._lock:
            decision, reason = self._policy_decision(agent_id, action, data_classification, float(estimated_cost_usd))
            request_id = f"REQ-{len(self._requests) + 1:04d}"
            request = {
                "request_id": request_id,
                "agent_id": agent_id,
                "action": action,
                "data_classification": data_classification,
                "estimated_cost_usd": round(float(estimated_cost_usd), 4),
                "rationale": rationale.strip(),
                "decision": decision,
                "reason": reason,
                "created_at": _now(),
                "reviewer": None,
                "execution_status": "Not executed — control-plane demo only",
                "is_example": False,
            }
            self._requests.insert(0, request)
            self._append_event(request, "Policy engine", decision, reason, request["created_at"])
            return deepcopy(request)

    def decide(self, request_id: str, decision: str, reviewer: str = "Local demo reviewer") -> dict[str, Any]:
        if decision not in ("approve", "reject"):
            raise ValueError("decision must be approve or reject")
        with self._lock:
            request = next((item for item in self._requests if item["request_id"] == request_id), None)
            if request is None:
                raise ValueError("request_id was not found")
            if request["decision"] != "pending_approval":
                raise ValueError("only pending requests can be approved or rejected")
            request["decision"] = "approved" if decision == "approve" else "rejected"
            request["reviewer"] = reviewer
            verb = "approved" if decision == "approve" else "rejected"
            request["reason"] = f"Human reviewer {verb} the request. No action was executed."
            request["execution_status"] = "Not executed — control-plane demo only"
            self._append_event(request, reviewer, request["decision"], request["reason"])
            return deepcopy(request)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            requests = deepcopy(self._requests)
            events = deepcopy(self._events)
            counts = {decision: sum(item["decision"] == decision for item in requests) for decision in ("allowed", "pending_approval", "approved", "rejected", "denied")}
            return {
                "agents": deepcopy(list(self._agents.values())),
                "agent_registry": deepcopy(self._agents),
                "classifications": list(CLASSIFICATIONS),
                "approval_actions": sorted(APPROVAL_ACTIONS),
                "summary": {"request_count": len(requests), "event_count": len(events), **counts},
                "requests": requests,
                "events": events,
                "policy_notes": [
                    "Unregistered agents and non-allowlisted tools are denied.",
                    "Data access must fit the agent's declared scope.",
                    "Per-request estimated spend is checked against the agent's demo budget.",
                    "Configured sensitive actions and restricted data require human approval.",
                ],
                "prototype_note": "All records are synthetic. Decisions are recorded for demonstration only; no agent tool is executed.",
            }
