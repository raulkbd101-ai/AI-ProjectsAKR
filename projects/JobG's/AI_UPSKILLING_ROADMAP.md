# JobG's AI Engineering & Upskilling Roadmap

## Purpose

Use JobG's as a personal, local-first project for learning applied AI and platform engineering while improving a demanding executive job-search workflow. Each milestone should produce a reviewable deliverable and a learning note explaining what changed, how it works, its trade-offs, and what remains unproven.

The initial four-week MVP is complete and tagged `v1.6`. The remaining roadmap is a learning plan, not a promise to launch a public autonomous job-application service. The candidate remains responsible for decisions, application content, and every external submission or message.

## Starting point at v1.6

The local FastAPI app uses SQLite for profile evidence, company inventory, and tracked roles. It supports manually supplied job details, rule-based triage suggestions, local hybrid evidence retrieval, persona-weighted ranking, evidence-gated bridge drafts, a reviewable tracker, activity summaries, and offline exports.

The 50-minute-per-application estimate motivates the product but has not yet been evaluated as a measured baseline or validated time saving. The app cannot promise ATS passage or prevent rejection. Its scores are retrieval relevance and literal keyword coverage, not job-fit probabilities.

**Known implementation gap:** the current checkout's job intake API calls `run_rag_session.ps1`, but this wrapper is absent from the repository. Restore and test it before claiming the API-managed Ollama workflow works in a fresh clone. See the [product overview](PRODUCT_OVERVIEW.md).

## 24-week outline

| Phase | Weeks | Status | Learning focus | Potential deliverable |
|---|---:|---|---|---|
| 1. Local retrieval foundation | 1–4 | **Completed — v1.6 MVP** | Evidence modeling, lexical search, embeddings, retrieval ranking, personas, human review | Local retrieval, triage, tracker, and exports |
| 2. Structured AI workflows | 5–8 | Planned | Model boundaries, structured output, prompt design, validation, retries, cost and latency | Optional evidence-grounded analysis service with schema validation |
| 3. Supervised agentic workflows | 9–12 | Planned | Tool calling, bounded workflows, approvals, idempotency, auditability | Supervised preparation workflow; no unattended external actions |
| 4. MCP and interoperability | 13–16 | Planned | MCP tools/resources, least privilege, authentication, threat modeling | Local read-limited MCP interface, disabled by default |
| 5. Cloud, governance, and FinOps | 17–20 | Planned | Containers, deployment patterns, secrets, observability, privacy, cost controls | Deployment rehearsal and architecture decision record; local mode stays available |
| 6. Evaluation and portfolio | 21–24 | Planned | Permitted discovery, evaluation, reliability, governance, release communication | Measured, bounded preparation workflow and portfolio walkthrough |

## Completed learning record: Weeks 1–4

### Week 1 — Evidence store and local retrieval

**Delivered:** SQLite candidate evidence with persona scope, an Ollama `nomic-embed-text` embedding path, a derived vector cache, lexical-only fallback for the CLI, and a hybrid relevance rank when embeddings are available.

**Learned:** embeddings encode text for similarity search; the vector cache is derived and rebuildable; retrieval finds potentially relevant claims but does not verify them or generate a narrative.

### Week 2 — Intake and triage

**Delivered:** company inventory and job tracker tables, `/api/triage-job` preview, `/api/add-job` save-for-review flow, rule-based persona/domain/location suggestions, and company record upserts based on user-supplied facts.

**Learned:** request validation, parameterized SQLite operations, upsert/idempotency patterns, lifecycle status, and human approval boundaries.

### Week 3 — Dynamic personas and evidence-grounded bridges

**Delivered:** persona-adjusted ranking for Director, Architect, and TPM; allowlisted conceptual technology mappings; bridge generation gated by a supporting, eligible, non-confidential SQLite claim; provenance and caveats in results.

**Learned:** ranking features, evidence provenance, and how to prevent semantic adjacency from being misrepresented as direct hands-on experience.

### Week 4 — Dashboard and workflow tracking

**Delivered:** tracker status transitions, filters, current-state analytics, daily role-logging cap visualizer, and Markdown/JSON exports.

**Learned:** state transitions, query parameters, SQLite reporting, snapshot metrics versus historical conversion, and data minimization in exports.

## Weeks 5–8 — Structured AI workflows (planned)

- **Learn:** model-provider boundaries, structured outputs, prompt injection, retries, evaluation, token/cost/latency measurement.
- **Build:** only after an explicit privacy and cost decision, add an optional provider adapter that accepts retrieved evidence and returns typed `strengths`, `gaps`, `unknowns`, and evidence IDs.
- **Acceptance:** every candidate-specific strength cites a saved evidence ID; unsupported statements are marked unknown; malformed output fails closed; the candidate can edit or reject drafts.
- **Do not claim:** an AI-generated fit score is calibrated unless it has a labeled evaluation set and documented methodology.

## Weeks 9–12 — Supervised agentic workflows (planned)

Explore bounded internal tool orchestration for organizing user-supplied roles and preparing drafts. Require explicit approval before any action that changes external systems. Design for retries, idempotency, cancellation, audit events, and a cost budget before adding tools.

## Weeks 13–16 — MCP and interoperability (planned)

Prototype read-only tools/resources for approved local data. Start disabled by default, scope each operation, and document authentication, authorization, data exposure, and prompt-injection boundaries before connection to an external agent.

## Weeks 17–20 — Deployment, governance, and FinOps (planned)

Rehearse containerization and a cloud deployment design without moving candidate data by default. Document secrets handling, encryption, access controls, backups, deletion, observability, resource limits, model costs, and rollback. Keep local operation as a viable mode.

## Weeks 21–24 — Evaluation and portfolio (planned)

Measure whether the tool reduces preparation time on a small, consented set of candidate-owned roles. Record baseline and assisted minutes, persona corrections, retrieval relevance judgments, draft edits, and unsupported-claim detections. Publish sanitized results with sample size and limitations. No ATS or rejection reduction claim without valid evidence.

## Learning routine

For each change, predict behavior before running it; explain the concept in plain language; inspect code and output; record what changed, why, failure modes, privacy/cost implications, and an interview-ready design trade-off. Use synthetic or sanitized test material. Do not paste credentials or confidential documents into external AI services.

## Standing guardrails

- Candidate evidence remains self-reported unless independently verified by the candidate; labels alone are not verification.
- Similarity is not truth, competence, job fit, ATS success, or interview probability.
- Preserve source evidence and provenance; never invent metrics, credentials, responsibilities, or tool experience.
- Use permitted sources for job information; begin with user-supplied URLs and descriptions.
- Keep external submissions and outreach under the candidate's direct control.
- Do not commit the local SQLite database, resumes, sensitive descriptions, embedding cache, model files, or secrets.

See [PRODUCT_OVERVIEW.md](PRODUCT_OVERVIEW.md), [MVP_BUILD_PLAN.md](MVP_BUILD_PLAN.md), and the [Week 1–4 milestone notes](docs/).
