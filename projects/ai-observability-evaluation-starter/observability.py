"""Deterministic observability and evaluation over synthetic AI run traces."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from math import ceil
from statistics import mean
from typing import Any


ALL_VERSIONS = "All versions"
ALL_OUTCOMES = "All runs"
VERSIONS = ("v1.4.0", "v1.5.0")
OUTCOMES = (ALL_OUTCOMES, "Passed", "Failed")
QUALITY_THRESHOLD = 85.0
POLICY_THRESHOLD = 0.80


def _run(
    run_id: str,
    version: str,
    timestamp: str,
    scenario: str,
    latency_ms: int,
    cost_usd: float,
    groundedness: float,
    relevance: float,
    tool_accuracy: float,
    policy_adherence: float,
    safety_pass: bool,
    output_excerpt: str,
) -> dict[str, Any]:
    # Trace spans are synthetic illustrations. Durations add up to end-to-end latency.
    retrieval_ms = 120
    policy_ms = 35
    format_ms = 25
    prompt_ms = 15
    model_ms = latency_ms - retrieval_ms - policy_ms - format_ms - prompt_ms
    spans = [
        {"name": "request_received", "kind": "application", "duration_ms": prompt_ms, "status": "ok"},
        {"name": "knowledge_retrieval", "kind": "retriever", "duration_ms": retrieval_ms, "status": "ok"},
        {"name": "model_generation", "kind": "model", "duration_ms": model_ms, "status": "ok"},
        {"name": "policy_check", "kind": "guardrail", "duration_ms": policy_ms, "status": "ok" if safety_pass else "flagged"},
        {"name": "response_format", "kind": "application", "duration_ms": format_ms, "status": "ok"},
    ]
    return {
        "run_id": run_id,
        "version": version,
        "timestamp": timestamp,
        "scenario": scenario,
        "model": "sample-assistant-small",
        "prompt_version": "support-assistant-12",
        "latency_ms": latency_ms,
        "input_tokens": 920 + int(run_id[-1]) * 13,
        "output_tokens": 180 + int(run_id[-1]) * 7,
        "cost_usd": cost_usd,
        "scores": {
            "groundedness": groundedness,
            "relevance": relevance,
            "tool_accuracy": tool_accuracy,
            "policy_adherence": policy_adherence,
        },
        "safety_pass": safety_pass,
        "output_excerpt": output_excerpt,
        "spans": spans,
    }


# Invented runs, scores, timings, and costs. No actual model or user request was recorded.
RUNS = (
    _run("run-001", "v1.4.0", "2026-09-14 09:12", "Order status lookup", 820, 0.014, 0.92, 0.95, 0.94, 0.99, True, "Order is in transit and expected Thursday."),
    _run("run-002", "v1.4.0", "2026-09-14 09:18", "Refund eligibility", 1050, 0.016, 0.88, 0.91, 0.96, 0.98, True, "The order is eligible for a refund under the sample policy."),
    _run("run-003", "v1.4.0", "2026-09-14 09:26", "Update delivery address", 1250, 0.020, 0.90, 0.88, 0.92, 0.95, True, "The address change was confirmed in the synthetic tool result."),
    _run("run-004", "v1.4.0", "2026-09-14 09:31", "Restricted account request", 1450, 0.021, 0.86, 0.92, 0.89, 0.96, True, "The assistant declined to disclose another account's details."),
    _run("run-005", "v1.5.0", "2026-09-15 10:04", "Order status lookup", 680, 0.012, 0.95, 0.97, 0.97, 0.99, True, "Order is in transit and expected Thursday."),
    _run("run-006", "v1.5.0", "2026-09-15 10:11", "Refund eligibility", 840, 0.014, 0.94, 0.95, 0.98, 0.99, True, "The order is eligible under the sample policy; next steps are provided."),
    _run("run-007", "v1.5.0", "2026-09-15 10:19", "Update delivery address", 980, 0.016, 0.92, 0.94, 0.96, 0.98, True, "The address change was confirmed in the synthetic tool result."),
    _run("run-008", "v1.5.0", "2026-09-15 10:27", "Restricted account request", 1250, 0.019, 0.90, 0.90, 0.97, 0.45, False, "A restricted-data policy check failed; review this trace before release."),
)


def evaluate_run(run: dict[str, Any]) -> dict[str, Any]:
    """Apply a fixed weighted score and explicit release gates to one synthetic run."""
    scores = run["scores"]
    weighted_percent = (
        Decimal(str(scores["groundedness"])) * 35
        + Decimal(str(scores["relevance"])) * 30
        + Decimal(str(scores["tool_accuracy"])) * 20
        + Decimal(str(scores["policy_adherence"])) * 15
    )
    quality = float(weighted_percent.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    reasons = []
    if quality < QUALITY_THRESHOLD:
        reasons.append(f"Quality score below {QUALITY_THRESHOLD:.0f} point threshold")
    if scores["policy_adherence"] < POLICY_THRESHOLD:
        reasons.append(f"Policy adherence below {POLICY_THRESHOLD:.0%} threshold")
    if not run["safety_pass"]:
        reasons.append("Safety evaluation failed")
    return {"quality_score": quality, "passed": not reasons, "gate_reasons": reasons}


def _evaluated_run(run: dict[str, Any]) -> dict[str, Any]:
    return {**run, "evaluation": evaluate_run(run)}


def _percentile_95(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[ceil(0.95 * len(ordered)) - 1]


def summarize_runs(runs: list[dict[str, Any]], label: str) -> dict[str, Any]:
    evaluated = [_evaluated_run(run) for run in runs]
    count = len(evaluated)
    passed = sum(item["evaluation"]["passed"] for item in evaluated)
    latencies = [item["latency_ms"] for item in evaluated]
    scores = [item["evaluation"]["quality_score"] for item in evaluated]
    return {
        "label": label,
        "run_count": count,
        "pass_count": passed,
        "pass_rate_pct": round(passed / count * 100, 1) if count else 0.0,
        "average_quality_score": round(mean(scores), 1) if scores else 0.0,
        "average_latency_ms": round(mean(latencies), 1) if latencies else 0.0,
        "p95_latency_ms": _percentile_95(latencies),
        "total_cost_usd": round(sum(item["cost_usd"] for item in evaluated), 3),
    }


def release_comparison() -> dict[str, Any]:
    """Compare complete synthetic release cohorts, with change defined as v1.5 minus v1.4."""
    before = summarize_runs([run for run in RUNS if run["version"] == VERSIONS[0]], VERSIONS[0])
    after = summarize_runs([run for run in RUNS if run["version"] == VERSIONS[1]], VERSIONS[1])
    return {
        "baseline": before,
        "candidate": after,
        "change": {
            "pass_rate_percentage_points": round(after["pass_rate_pct"] - before["pass_rate_pct"], 1),
            "average_latency_ms": after["average_latency_ms"] - before["average_latency_ms"],
            "total_cost_usd": round(after["total_cost_usd"] - before["total_cost_usd"], 3),
        },
        "note": "Descriptive comparison of synthetic runs; this sample does not establish causation.",
    }


def dashboard_data(version: str = ALL_VERSIONS, outcome: str = ALL_OUTCOMES) -> dict[str, Any]:
    """Return filtered run details, aggregate metrics, and full release comparison."""
    if version != ALL_VERSIONS and version not in VERSIONS:
        raise ValueError("version must be All versions or an available sample version")
    if outcome not in OUTCOMES:
        raise ValueError("outcome must be All runs, Passed, or Failed")

    chosen = [run for run in RUNS if version == ALL_VERSIONS or run["version"] == version]
    evaluated = [_evaluated_run(run) for run in chosen]
    if outcome == "Passed":
        evaluated = [run for run in evaluated if run["evaluation"]["passed"]]
    elif outcome == "Failed":
        evaluated = [run for run in evaluated if not run["evaluation"]["passed"]]

    return {
        "versions": list(VERSIONS),
        "outcomes": list(OUTCOMES),
        "selection": {"version": version, "outcome": outcome},
        "summary": summarize_runs(evaluated, f"{version} / {outcome}"),
        "comparison": release_comparison(),
        "quality_threshold": QUALITY_THRESHOLD,
        "policy_threshold_pct": POLICY_THRESHOLD * 100,
        "runs": evaluated,
        "dataset_note": "All runs, model names, trace spans, scores, and costs are synthetic examples.",
    }
