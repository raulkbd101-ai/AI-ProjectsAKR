# Week 3 Milestone: Persona Switcher & Advanced Tech Bridges

## Overview

Week 3 adds persona-aware evidence retrieval and evidence-grounded transferable technology bridge drafts to JobG's. SQLite remains the source of candidate evidence. The system ranks and presents saved claims for human review; it does not independently verify claims or make application decisions.

## Dynamic Persona Switcher

When a job is triaged, the selected persona—**Director**, **Architect**, or **TPM**—guides evidence ranking:

- **Director:** Leadership, global teams, budget management, organizational transformation, operating models, and FinOps.
- **Architect:** Cloud migration, multi-cloud architecture, system design, scalability, reliability, disaster recovery, and platform modernization.
- **TPM:** Cross-functional and program delivery, stakeholder management, risk, milestones, dependencies, governance, and execution tracking.

For a selected persona, the matcher considers claims tagged for that persona and shared claims tagged `All`. Confidential claims remain excluded by default.

The persona-adjusted ordering score is:

```text
0.70 × base retrieval score
+ 0.25 × persona keyword score
+ 0.05 × persona scope score
```

The original `retrieval_score` is preserved. Results also expose `persona_score`, `persona_signals`, and `persona_adjusted_score` so the ranking is inspectable. Selecting `All` leaves the original ranking unchanged.

These values describe retrieval ranking only. They are not job-fit, proficiency, truth, or hiring-probability scores.

## Advanced Tech Bridge Mapping

The bridge generator uses an allowlisted mapping of conceptual adjacencies, including:

- **Cloud:** GCP or Azure evidence to AWS concepts, and related multi-cloud architecture.
- **Data platforms:** BigQuery or Redshift evidence to Snowflake and Databricks concepts.
- **Data pipelines:** Relevant data engineering or pipeline evidence to Kafka concepts.
- **Modernization:** C++, MFC, or legacy-systems evidence to Python, Go, cloud microservices, or modern distributed-architecture concepts.

These mappings describe conceptual adjacency; they do not mean products are interchangeable.

## Evidence and compliance guardrails

A bridge is generated only when:

1. The requested target technology is in the supported mapping list.
2. A non-confidential SQLite evidence claim explicitly contains the mapped source technology in its competency or claim.
3. The claim is eligible for the selected persona: tagged `All` or with that persona.
4. A non-rejected bridge template exists in `transferable_tech_mapping`.

Each result carries the supporting evidence ID, claim, competency, evidence status, evidence summary, and source reference. Each draft explicitly says that conceptual adjacency does not establish hands-on production use of the target technology. Candidate review is required before reuse.

## Data flow

1. JobG's identifies target technologies in the job description.
2. The matcher checks the supported source-to-target mappings.
3. It searches eligible SQLite evidence claims for an explicit source-technology match.
4. If supporting evidence exists, JobG's selects a non-rejected template and returns the draft with its evidence provenance and disclaimer.
5. If no supporting claim exists, no bridge is returned for that target.

## Components

- `rag_matcher.py` — Hybrid or lexical evidence retrieval and persona-aware ranking.
- `matcher.py` — Evidence-gated transferable bridge generation.
- `database.py` — SQLite schema and idempotent bridge-template seeding.
- `job_copilot.py` — Triage response and human-review notices.
- `tests/test_rag_matcher.py` and `tests/test_transferable_bridges.py` — Persona-ranking and evidence-guardrail coverage.

## Verification

The local unit test suite passed **26 tests**. Run it from the `jobgs-engine` directory:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Scope and limitations

This milestone improves evidence retrieval and drafts explanations of conceptual adjacency. It does not verify candidate claims, assert direct production experience with target technologies, calculate hiring probability, or submit applications.
