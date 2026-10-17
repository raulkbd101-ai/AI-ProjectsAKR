"""Deterministic analytics over an intentionally small synthetic dataset."""

from __future__ import annotations

from typing import Any


PERIODS = ("2026-07", "2026-08", "2026-09")
PROGRAMS = {
    "service-assist": "Customer Service Assist",
    "knowledge-search": "Enterprise Knowledge Search",
    "claims-triage": "Claims Triage",
}

# All values below are invented examples, in USD, and are not business results.
RECORDS = (
    {"period": "2026-07", "program_id": "service-assist", "eligible_users": 5000, "active_users": 3400, "spend_usd": 120000, "modeled_value_usd": 195000, "open_risks": 2},
    {"period": "2026-07", "program_id": "knowledge-search", "eligible_users": 3000, "active_users": 1800, "spend_usd": 70000, "modeled_value_usd": 95000, "open_risks": 1},
    {"period": "2026-07", "program_id": "claims-triage", "eligible_users": 4000, "active_users": 2600, "spend_usd": 110000, "modeled_value_usd": 145000, "open_risks": 4},
    {"period": "2026-08", "program_id": "service-assist", "eligible_users": 5000, "active_users": 3600, "spend_usd": 130000, "modeled_value_usd": 205000, "open_risks": 2},
    {"period": "2026-08", "program_id": "knowledge-search", "eligible_users": 3000, "active_users": 1950, "spend_usd": 75000, "modeled_value_usd": 105000, "open_risks": 1},
    {"period": "2026-08", "program_id": "claims-triage", "eligible_users": 4000, "active_users": 2750, "spend_usd": 115000, "modeled_value_usd": 160000, "open_risks": 3},
    {"period": "2026-09", "program_id": "service-assist", "eligible_users": 5000, "active_users": 3850, "spend_usd": 138000, "modeled_value_usd": 222000, "open_risks": 1},
    {"period": "2026-09", "program_id": "knowledge-search", "eligible_users": 3000, "active_users": 2100, "spend_usd": 82000, "modeled_value_usd": 116000, "open_risks": 1},
    {"period": "2026-09", "program_id": "claims-triage", "eligible_users": 4000, "active_users": 2900, "spend_usd": 122000, "modeled_value_usd": 168000, "open_risks": 3},
)


def _validate_period(period: str) -> None:
    if period not in PERIODS:
        raise ValueError(f"Unknown period {period!r}. Choose one of: {', '.join(PERIODS)}.")


def _validate_program(program_id: str) -> None:
    if program_id not in PROGRAMS:
        raise ValueError(f"Unknown program_id {program_id!r}. Choose one of: {', '.join(PROGRAMS)}.")


def _summary(rows: list[dict[str, Any]], period: str) -> dict[str, Any]:
    spend = sum(row["spend_usd"] for row in rows)
    modeled_value = sum(row["modeled_value_usd"] for row in rows)
    eligible = sum(row["eligible_users"] for row in rows)
    active = sum(row["active_users"] for row in rows)
    return {
        "period": period,
        "program_count": len(rows),
        "spend_usd": spend,
        "modeled_value_usd": modeled_value,
        "modeled_net_value_usd": modeled_value - spend,
        "weighted_adoption_pct": round(active / eligible * 100, 1) if eligible else 0.0,
        "open_risks": sum(row["open_risks"] for row in rows),
        "value_note": "Modeled illustrative value; not measured or validated business benefit.",
    }


def portfolio_summary(period: str) -> dict[str, Any]:
    """Summarize spend, modeled value, adoption, and open risks for one month."""
    _validate_period(period)
    rows = [row for row in RECORDS if row["period"] == period]
    return _summary(rows, period)


def compare_periods(from_period: str, to_period: str) -> dict[str, Any]:
    """Compare portfolio totals across two periods and report absolute changes."""
    _validate_period(from_period)
    _validate_period(to_period)
    before = portfolio_summary(from_period)
    after = portfolio_summary(to_period)
    fields = ("spend_usd", "modeled_value_usd", "modeled_net_value_usd", "weighted_adoption_pct", "open_risks")
    return {
        "from_period": from_period,
        "to_period": to_period,
        "from": before,
        "to": after,
        "change": {field: round(after[field] - before[field], 1) for field in fields},
        "interpretation": "Changes are descriptive comparisons of synthetic samples; they do not establish causation.",
    }


def program_detail(program_id: str) -> dict[str, Any]:
    """Return synthetic monthly observations for one named AI program."""
    _validate_program(program_id)
    monthly = [row for row in RECORDS if row["program_id"] == program_id]
    return {"program_id": program_id, "program_name": PROGRAMS[program_id], "observations": monthly}


def available_periods() -> dict[str, Any]:
    """List the periods and program identifiers available in this demo."""
    return {"periods": list(PERIODS), "programs": [{"program_id": key, "name": name} for key, name in PROGRAMS.items()]}
