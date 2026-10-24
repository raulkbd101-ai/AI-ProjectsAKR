# AI Observability & Evaluation Starter

Copyright (c) 2026 Amith Raul. All rights reserved. Reuse of this project's original code and materials is not granted without separate written permission. See [LICENSE](LICENSE).

A local dashboard for inspecting synthetic AI assistant traces and applying transparent, deterministic quality gates. Compare two sample releases across evaluation pass rate, latency, and illustrative cost; select a failed run to inspect its trace spans and gate reasons.

This project makes the observability and evaluation workflow concrete without calling an LLM, cloud service, or external API. Every run, score, trace span, model label, timestamp, token count, and cost is invented for the demo.

## What it demonstrates

- Trace-style run records with retrieval, model, policy, and response-format spans.
- Quality scoring with an explicit weighted rubric for groundedness, relevance, tool accuracy, and policy adherence.
- Release gates for minimum quality, policy adherence, and a safety pass.
- Filtering by model release and pass/fail result.
- Release comparison that surfaces a quality regression alongside changes in latency and cost.
- A local dashboard backed by a small JSON API, with standard-library unit tests.

## Run locally

Requirements: Python 3.10 or newer. No install step or third-party package is required.

From the repository root in PowerShell:

```powershell
Set-Location "C:\Users\Rina\OneDrive\Documents\ChatGPT\Job Portal-AI\projects\ai-observability-evaluation-starter"
python app.py
```

Open <http://127.0.0.1:8002>. Select `v1.5.0`, or choose the failed-run filter to inspect the restricted account request and its failed safety and policy gates. The server binds to loopback by default; do not expose it to a network.

For the unfiltered sample, expect 8 runs, 7 passes (87.5%), 1,450 ms p95 latency, and $0.132 illustrative total cost. In the full release comparison, `v1.4.0` passes 4/4 runs while `v1.5.0` passes 3/4. The candidate is 205 ms faster on average but has a 25 percentage-point lower pass rate. This intentionally demonstrates why latency or cost improvements do not establish release quality.

## Run checks

From the project directory:

```powershell
python -m unittest discover -s tests -v
```

The tests exercise the weighted score, quality and safety gates, summaries, latency percentile, release comparison, filters, validation, and trace duration accounting. The initial 12-test run is captured in [`evidence/test-results.txt`](evidence/test-results.txt).

To reproduce the local demo evidence, capture the dashboard with **All versions** selected and the failed run detail visible, then capture the **v1.5.0 / Failed** filter. These views show both the release regression and the gate reason at trace level.

## Local demo evidence

These screenshots show the dashboard running on the author's laptop at `127.0.0.1:8002`. They use the bundled synthetic runs; they do not show real model traffic or customer data.

**All releases:** 8 sample runs, 7 passes (87.5%), 1,450 ms p95 latency, and $0.132 illustrative cost. The release comparison shows the `v1.5.0` pass-rate regression alongside its lower average latency and cost.

![Local observability dashboard with all releases, run metrics, release comparison, and failed trace selected](evidence/dashboard-all-releases.png)

**Failed run detail:** selecting `v1.5.0` and **Failed** isolates the restricted-account trace. Its quality score is 84.7, policy adherence is 45%, and the safety gate fails. The 0% pass rate in this filtered view describes this single failed run; the full `v1.5.0` cohort passes 3 of 4 runs.

![Local dashboard filtered to the failed v1.5.0 restricted-account trace and its gate reasons](evidence/dashboard-v1.5.0-failed-run.png)

**Local test run:** all 12 unit tests passed on the author's laptop.

![PowerShell output showing all 12 AI observability and evaluation tests passing](evidence/test-run-local.png)

## How the evaluation works

`observability.py` contains the synthetic run records and trace spans. `evaluate_run()` computes a weighted score:

| Dimension | Weight |
| --- | ---: |
| Groundedness | 35% |
| Relevance | 30% |
| Tool accuracy | 20% |
| Policy adherence | 15% |

A run passes only when its score is at least 85/100, policy adherence is at least 80%, and the safety check passes. Scores are rounded half-up to one decimal. These fixed demo thresholds are examples, not validated production criteria. P95 latency uses the nearest-rank method. Release deltas are calculated as `v1.5.0 - v1.4.0`.

## Governance boundaries

This is a learning prototype, not a production observability or evaluation platform. It uses hard-coded synthetic examples, a fixed rubric, and no real prompts, model calls, customer content, telemetry, authentication, retention controls, or alerting. The “model” name and costs are illustrative. A production setup needs approved evaluation datasets and criteria, privacy controls, trace access policy, calibrated thresholds, provenance, monitoring, and human review for failed evaluations.

## License

MIT. See [LICENSE](LICENSE).
