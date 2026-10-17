"""Deterministic FinOps calculations over invented monthly cloud costs."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


PERIODS = ("2026-06", "2026-07", "2026-08", "2026-09")
LATEST_PERIOD = PERIODS[-1]
TEAMS = ("AI Platform", "Data Platform", "Analytics", "Shared Services")
ALL_TEAMS = "All teams"

TEAM_BUDGETS = {
    "AI Platform": 12_500,
    "Data Platform": 5_500,
    "Analytics": 7_500,
    "Shared Services": 2_200,
}

# Invented data only. Shared Network has no owner tag to demonstrate allocation gaps.
COST_ROWS = (
    ("2026-06", "AI Platform", "Model Serving", 8_000, True),
    ("2026-06", "Data Platform", "Object Storage", 5_000, True),
    ("2026-06", "Analytics", "Cloud Warehouse", 6_500, True),
    ("2026-06", "Shared Services", "Shared Network", 2_000, False),
    ("2026-07", "AI Platform", "Model Serving", 8_200, True),
    ("2026-07", "Data Platform", "Object Storage", 5_100, True),
    ("2026-07", "Analytics", "Cloud Warehouse", 6_400, True),
    ("2026-07", "Shared Services", "Shared Network", 2_100, False),
    ("2026-08", "AI Platform", "Model Serving", 8_300, True),
    ("2026-08", "Data Platform", "Object Storage", 5_200, True),
    ("2026-08", "Analytics", "Cloud Warehouse", 6_600, True),
    ("2026-08", "Shared Services", "Shared Network", 2_050, False),
    ("2026-09", "AI Platform", "Model Serving", 13_500, True),
    ("2026-09", "Data Platform", "Object Storage", 5_400, True),
    ("2026-09", "Analytics", "Cloud Warehouse", 7_000, True),
    ("2026-09", "Shared Services", "Shared Network", 2_100, False),
)

ANOMALY_MIN_INCREASE_PCT = 25.0
ANOMALY_MIN_DOLLARS = 1_000


def _validate_filters(month: str, team: str) -> None:
    if month not in PERIODS:
        raise ValueError("month must be one of the available sample periods")
    if team != ALL_TEAMS and team not in TEAMS:
        raise ValueError("team must be All teams or one of the available teams")


def _selected(rows: tuple[tuple[str, str, str, int, bool], ...], team: str):
    return [row for row in rows if team == ALL_TEAMS or row[1] == team]


def _anomalies(month: str, team: str) -> list[dict[str, Any]]:
    month_index = PERIODS.index(month)
    prior_periods = PERIODS[max(0, month_index - 3):month_index]
    if not prior_periods:
        return []

    selected_rows = _selected(COST_ROWS, team)
    current_by_service: dict[tuple[str, str], int] = {}
    history_by_service: dict[tuple[str, str], list[int]] = defaultdict(list)

    for period, row_team, service, cost, _tagged in selected_rows:
        key = (row_team, service)
        if period == month:
            current_by_service[key] = cost
        elif period in prior_periods:
            history_by_service[key].append(cost)

    result = []
    for (row_team, service), current_cost in current_by_service.items():
        history = history_by_service.get((row_team, service), [])
        if not history:
            continue
        baseline = sum(history) / len(history)
        increase = current_cost - baseline
        increase_pct = (increase / baseline * 100) if baseline else 0.0
        if increase >= ANOMALY_MIN_DOLLARS and increase_pct >= ANOMALY_MIN_INCREASE_PCT:
            result.append({
                "team": row_team,
                "service": service,
                "current_cost": current_cost,
                "baseline": round(baseline, 2),
                "increase": round(increase, 2),
                "increase_pct": round(increase_pct, 1),
            })
    return sorted(result, key=lambda item: item["increase"], reverse=True)


def dashboard_data(month: str, team: str = ALL_TEAMS) -> dict[str, Any]:
    """Return dashboard metrics for a valid sample month and optional team."""
    _validate_filters(month, team)
    chosen_rows = _selected(COST_ROWS, team)
    current_rows = [row for row in chosen_rows if row[0] == month]
    budgets = {team_name: amount for team_name, amount in TEAM_BUDGETS.items()
               if team == ALL_TEAMS or team_name == team}

    total_spend = sum(row[3] for row in current_rows)
    total_budget = sum(budgets.values())
    unallocated = sum(row[3] for row in current_rows if not row[4])
    utilization = total_spend / total_budget * 100 if total_budget else 0.0
    allocation_coverage = (total_spend - unallocated) / total_spend * 100 if total_spend else 100.0

    team_summaries = []
    for team_name, budget in budgets.items():
        spend = sum(row[3] for row in current_rows if row[1] == team_name)
        team_summaries.append({
            "team": team_name,
            "spend": spend,
            "budget": budget,
            "variance": spend - budget,
            "utilization_pct": round(spend / budget * 100, 1) if budget else 0.0,
        })

    service_rows = [
        {"team": row_team, "service": service, "cost": cost, "owner_tagged": tagged}
        for period, row_team, service, cost, tagged in current_rows
    ]

    trend = []
    for period in PERIODS:
        period_rows = [row for row in chosen_rows if row[0] == period]
        period_budget = total_budget
        trend.append({
            "month": period,
            "spend": sum(row[3] for row in period_rows),
            "budget": period_budget,
        })

    return {
        "month": month,
        "team_filter": team,
        "total_spend": total_spend,
        "total_budget": total_budget,
        "budget_variance": total_spend - total_budget,
        "budget_utilization_pct": round(utilization, 1),
        "unallocated_spend": unallocated,
        "allocation_coverage_pct": round(allocation_coverage, 1),
        "team_summaries": team_summaries,
        "service_rows": service_rows,
        "trend": trend,
        "anomalies": _anomalies(month, team),
        "anomaly_rule": {
            "minimum_increase_pct": ANOMALY_MIN_INCREASE_PCT,
            "minimum_increase_dollars": ANOMALY_MIN_DOLLARS,
            "baseline": "average of available prior months, up to three",
        },
        "data_note": "Invented sample data; no cloud provider is connected.",
    }
