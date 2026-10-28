# JobG's Product Overview

**Release baseline:** v1.6  
**Owner:** Amith Kumar Raul  
**Product form:** Personal, local-first job-search assistant  
**MVP milestone:** Weeks 1–4 completed

## The problem this project addresses

The candidate's manual application workflow can take roughly 50 minutes per role: locate and understand a vacancy, decide which of several executive resume tracks fits, find relevant experience evidence, adapt the application narrative, prepare outreach, and record the outcome. Repeating these steps across vacancies creates substantial administrative effort and makes it easy to miss relevant experience or overstate a match.

JobG's is a practical personal tool for reducing that repeated preparation and tracking work. It centralizes candidate-authored evidence, retrieves potentially relevant claims, suggests a resume persona, drafts conceptual technology bridges and outreach, and keeps a reviewable opportunity tracker. It supports more deliberate, evidence-aware applications while leaving the decision and external submission with the candidate.

The 50-minute figure describes the motivating manual process; it is not yet a measured JobG's time-savings result. A future evaluation should compare the same application tasks with and without the tool before making a quantified productivity claim.

## Product promise and limits

The MVP aims to:

- reduce repetitive role-to-profile comparison and status tracking;
- show which saved claims were retrieved and why;
- keep candidate facts traceable to the source notes the candidate entered;
- organize work across Director, Architect, and TPM resume personas;
- produce editable drafts and let the candidate decide what is accurate and useful.

It does **not** guarantee ATS passage, prevent rejection, or “bypass” screening systems. It does not claim that semantic similarity proves qualification. It does not crawl career sites, log in to external accounts, send outreach, or submit applications. It is not a standalone public service, multi-user product, or production-hardened SaaS release.

## End-to-end workflow

```text
1. Candidate manually finds a role
                 ↓
2. Candidate supplies URL, job description, and optional company facts
                 ↓
3. FastAPI validates the submission and suggests persona, domain, and work model
                 ↓
4. Persona-aware local retrieval ranks candidate-authored SQLite evidence
                 ↓
5. Evidence-supported bridge drafts and a three-sentence outreach draft are prepared
                 ↓
6. Candidate reviews the output and saves the opportunity as DISCOVERED
                 ↓
7. Candidate manually advances lifecycle status and submits externally if desired
                 ↓
8. Dashboard filters, activity summaries, and Markdown/JSON exports support follow-up
```

`/api/triage-job` performs a preview without saving the role. `/api/add-job` performs triage and stores the role and on-demand company record. Duplicate job URLs are handled idempotently. No external action follows automatically.

## Architecture at v1.6

| Concern | Implementation | Source of truth / boundary |
|---|---|---|
| Web UI and API | FastAPI, Uvicorn, Jinja2 | Binds to loopback for local use; no login |
| Candidate profile and evidence | SQLite tables including `master_profile` and `profile_evidence` | Candidate-entered statements; evidence status is self-reported |
| Company and role data | SQLite `companies_inventory` and `application_tracker` | Company rows are upserted on demand; no global company crawl |
| Evidence retrieval | `rag_matcher.py`: lexical overlap plus local Ollama embeddings, persona weighting | `profile_evidence` is authoritative; `evidence_embeddings` is a rebuildable cache |
| Transferable technology drafts | `matcher.py` allowlisted source/target mappings and evidence checks | Only eligible, non-confidential supporting claims may ground a draft |
| Job triage | `job_copilot.py` rule-based persona/domain/location suggestions and retrieval orchestration | Suggestions only; hybrid retrieval is required on its API path |
| Tracker and exports | `tracker.py`, Jinja2 templates, Markdown/JSON response | Current lifecycle state and saved draft data; no status-event history |
| Quality checks | Python `unittest`, GitHub Actions | Unit checks do not verify model quality or candidate claims |

## Search and scores

Hybrid retrieval combines 65% semantic similarity from the local `nomic-embed-text` embedding model and 35% lexical overlap. Persona weighting then adjusts ranking using persona-relevant terms and evidence scope. The original retrieval score remains visible alongside persona-adjusted ranking data.

These are **evidence retrieval relevance measures**, not calibrated job-fit percentages, qualification or proficiency ratings, claim verification, ATS outcomes, or hiring probabilities. Literal profile coverage is a separate indicator that reports saved terms found in the job description.

The app uses deterministic rules for persona/domain/location suggestions; the embedding model supports search, not generative prose. JobG's does not currently call ChatGPT or Gemini APIs, and no hosted LLM is configured to write a resume. Bridge and outreach text are drafts/templates, not autonomous model-generated communications.

## Governance, privacy, and operational boundaries

- Candidate review is required before logging a selected role, changing its lifecycle, reusing a claim, or taking any external action.
- Lifecycle states include `DISCOVERED`, `USER_REVIEWED`, `APPLIED`, `INTERVIEWING`, `OFFER`, `REJECTED`, `WITHDRAWN`, and `ARCHIVED`, with guarded transitions.
- The daily cap tracks locally logged roles, not successful external submissions.
- Data is stored locally by default. Embedding requests use a local Ollama service when configured; this avoids hosted inference charges for those requests but does not mean the software is free of all operating costs.
- The local SQLite file is not encrypted, the app has no authentication, and there is no multi-user isolation. Keep the app on loopback and do not store secrets, confidential employer material, or others' personal data in it.
- A confidentiality label is metadata, not an access-control or encryption mechanism.
- Ollama session cleanup depends on a PowerShell lifecycle wrapper. That wrapper is missing from the current repository checkout, although `job_copilot.py` requires it for `/api/triage-job` and `/api/add-job`; this is a release-readiness gap to resolve before claiming those managed API paths work in a fresh clone.

## MVP completion and next evidence to gather

The v1.6 milestone closes the first four-week implementation: evidence storage and retrieval, role intake and triage, persona-aware ranking and bridges, tracker lifecycle, filters, dashboard metrics, and offline export. The broader AI upskilling roadmap continues with structured AI workflows, supervised tools/agents, MCP, deployment governance, and evaluation.

Before expanding the product claim, prioritize:

1. Restore and test the managed Ollama lifecycle script in the repository; prove startup, correct model, hybrid output, teardown, and port release in a clean clone.
2. Add a measured before/after study of time per application, while checking draft factuality and human correction rate.
3. Evaluate retrieval with a small labeled, sanitized set and report retrieval quality separately from job-fit judgments.
4. Improve privacy controls before storing sensitive data or using the app outside a trusted single-user PC.

See [README.md](README.md) for setup, [CHANGELOG.md](CHANGELOG.md) for versions, and the [Week 1–4 milestone notes](docs/).
