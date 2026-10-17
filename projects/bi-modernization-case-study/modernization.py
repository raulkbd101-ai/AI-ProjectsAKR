"""Synthetic BI modernization portfolio and deterministic case-study metrics."""

from __future__ import annotations

from copy import deepcopy


DOMAINS = ("Finance", "Sales", "Operations", "Customer")
STATES = ("Ready", "Needs remediation", "Blocked")

ASSETS = [
    {"id": "BI-001", "report": "Executive revenue pack", "domain": "Finance", "owner": "Finance Analytics", "legacy_source": "Oracle warehouse", "target_model": "fct_revenue_monthly", "wave": 1, "state": "Ready", "quality": 98, "legacy_latency_s": 42, "target_latency_s": 8, "legacy_cost_usd": 1850, "target_cost_usd": 1260, "usage_monthly": 420, "blocker": "None; KPI reconciliation passed."},
    {"id": "BI-002", "report": "Margin and discount analysis", "domain": "Finance", "owner": "Finance Analytics", "legacy_source": "Oracle warehouse", "target_model": "mart_margin", "wave": 1, "state": "Needs remediation", "quality": 91, "legacy_latency_s": 55, "target_latency_s": 12, "legacy_cost_usd": 1420, "target_cost_usd": 1030, "usage_monthly": 190, "blocker": "Discount definitions differ across two source systems."},
    {"id": "BI-003", "report": "Accounts receivable aging", "domain": "Finance", "owner": "Finance Operations", "legacy_source": "SQL Server DW", "target_model": "mart_receivables", "wave": 2, "state": "Blocked", "quality": 76, "legacy_latency_s": 68, "target_latency_s": 15, "legacy_cost_usd": 980, "target_cost_usd": 840, "usage_monthly": 110, "blocker": "Customer key mapping is incomplete for acquired entities."},
    {"id": "BI-004", "report": "Pipeline coverage", "domain": "Sales", "owner": "Revenue Operations", "legacy_source": "Salesforce extracts", "target_model": "mart_pipeline", "wave": 1, "state": "Ready", "quality": 96, "legacy_latency_s": 35, "target_latency_s": 7, "legacy_cost_usd": 1340, "target_cost_usd": 990, "usage_monthly": 510, "blocker": "None; stage and currency rules reconciled."},
    {"id": "BI-005", "report": "Territory attainment", "domain": "Sales", "owner": "Revenue Operations", "legacy_source": "SQL Server DW", "target_model": "mart_sales_performance", "wave": 2, "state": "Needs remediation", "quality": 88, "legacy_latency_s": 49, "target_latency_s": 10, "legacy_cost_usd": 1120, "target_cost_usd": 910, "usage_monthly": 260, "blocker": "Territory hierarchy requires a named business steward."},
    {"id": "BI-006", "report": "Service-level performance", "domain": "Operations", "owner": "Platform Operations", "legacy_source": "PostgreSQL reporting", "target_model": "mart_service_health", "wave": 1, "state": "Ready", "quality": 97, "legacy_latency_s": 31, "target_latency_s": 6, "legacy_cost_usd": 920, "target_cost_usd": 710, "usage_monthly": 680, "blocker": "None; source freshness and metric owner confirmed."},
    {"id": "BI-007", "report": "Supply and inventory outlook", "domain": "Operations", "owner": "Supply Chain Analytics", "legacy_source": "Oracle warehouse", "target_model": "mart_inventory", "wave": 3, "state": "Blocked", "quality": 72, "legacy_latency_s": 74, "target_latency_s": 18, "legacy_cost_usd": 1580, "target_cost_usd": 1390, "usage_monthly": 145, "blocker": "Two source feeds have no agreed freshness SLA."},
    {"id": "BI-008", "report": "Customer retention cohort", "domain": "Customer", "owner": "Customer Insights", "legacy_source": "Snowflake legacy", "target_model": "mart_retention", "wave": 2, "state": "Needs remediation", "quality": 84, "legacy_latency_s": 61, "target_latency_s": 13, "legacy_cost_usd": 1260, "target_cost_usd": 970, "usage_monthly": 330, "blocker": "Retention window and consent exclusions need product sign-off."},
    {"id": "BI-009", "report": "Support demand trends", "domain": "Customer", "owner": "Customer Experience", "legacy_source": "PostgreSQL reporting", "target_model": "mart_support_demand", "wave": 3, "state": "Ready", "quality": 95, "legacy_latency_s": 39, "target_latency_s": 9, "legacy_cost_usd": 790, "target_cost_usd": 650, "usage_monthly": 390, "blocker": "None; event taxonomy mapped to shared definitions."},
]


def case_study(domain: str = "All domains", state: str = "All states") -> dict:
    """Return an isolated portfolio view and derived scenario metrics."""
    if domain != "All domains" and domain not in DOMAINS:
        raise ValueError("Unknown domain")
    if state != "All states" and state not in STATES:
        raise ValueError("Unknown migration state")
    rows = [row for row in ASSETS if (domain == "All domains" or row["domain"] == domain) and (state == "All states" or row["state"] == state)]
    count = len(rows)
    legacy_cost = sum(row["legacy_cost_usd"] for row in rows)
    target_cost = sum(row["target_cost_usd"] for row in rows)
    legacy_latency = round(sum(row["legacy_latency_s"] for row in rows) / count, 1) if count else 0
    target_latency = round(sum(row["target_latency_s"] for row in rows) / count, 1) if count else 0
    return {
        "filters": {"domains": ["All domains", *DOMAINS], "states": ["All states", *STATES], "selected_domain": domain, "selected_state": state},
        "summary": {
            "asset_count": count,
            "ready_count": sum(row["state"] == "Ready" for row in rows),
            "remediation_count": sum(row["state"] == "Needs remediation" for row in rows),
            "blocked_count": sum(row["state"] == "Blocked" for row in rows),
            "readiness_pct": round(100 * sum(row["state"] == "Ready" for row in rows) / count, 1) if count else 0,
            "legacy_monthly_cost_usd": legacy_cost,
            "target_monthly_cost_usd": target_cost,
            "modeled_monthly_delta_usd": legacy_cost - target_cost,
            "legacy_avg_latency_s": legacy_latency,
            "target_avg_latency_s": target_latency,
            "modeled_latency_reduction_pct": round(100 * (legacy_latency - target_latency) / legacy_latency, 1) if legacy_latency else 0,
        },
        "assets": deepcopy(rows),
        "domains": _domain_comparison(rows),
        "waves": _wave_plan(),
        "gates": [
            "Business owner signs off on the KPI definition and semantic contract.",
            "Reconciliation checks pass against an agreed legacy period and tolerance.",
            "Data quality and freshness meet the report's documented acceptance criteria.",
            "Access controls, lineage, support ownership, and rollback are reviewed before cutover.",
        ],
        "prototype_note": "Illustrative synthetic case study. Modeled deltas are scenario estimates, not measured migration outcomes.",
    }


def _domain_comparison(rows: list[dict]) -> list[dict]:
    result = []
    for domain in DOMAINS:
        group = [row for row in rows if row["domain"] == domain]
        if group:
            legacy = sum(row["legacy_cost_usd"] for row in group)
            target = sum(row["target_cost_usd"] for row in group)
            result.append({"domain": domain, "asset_count": len(group), "legacy_cost_usd": legacy, "target_cost_usd": target, "modeled_delta_usd": legacy - target})
    return result


def _wave_plan() -> list[dict]:
    plan = []
    for wave in (1, 2, 3):
        rows = [row for row in ASSETS if row["wave"] == wave]
        plan.append({"wave": wave, "asset_count": len(rows), "ready_count": sum(row["state"] == "Ready" for row in rows), "blocked_count": sum(row["state"] == "Blocked" for row in rows), "focus": {1: "Prove shared KPI and reconciliation patterns", 2: "Resolve domain definitions and steward ownership", 3: "Complete source SLAs and lower-priority migrations"}[wave]})
    return plan

