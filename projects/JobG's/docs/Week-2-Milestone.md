# Week 2 Milestone: Executive Job Intake and SQLite Inventory

## Goal

Reduce repeated intake and tracking work after the candidate manually finds a role. JobG's accepts role facts the candidate supplies, triages them, retrieves relevant local evidence, prepares reviewable drafts, and records the opportunity for follow-up.

## Delivered

- SQLite `companies_inventory` with on-demand company upserts and `application_tracker` for discovered roles.
- `/api/triage-job` to preview triage without persisting a role.
- `/api/add-job` to triage and save a new role with status `DISCOVERED`; duplicate job URLs are treated idempotently.
- `/api/ingest-companies` and `ingest_companies.py` for validated company-record batch upserts.
- Rule-based persona, domain, and work-model/location suggestions.
- Hybrid evidence retrieval, evidence-supported conceptual bridge drafts, and a LinkedIn outreach draft template.
- Explicit API notices that no application was submitted and no outreach was sent.

## Data flow

```text
Candidate supplies company details, job URL, location, and raw JD
        ↓
Pydantic validates size, required fields, and URL shape
        ↓
Rule-based triage suggests persona, domain, and work model
        ↓
Persona-filtered local hybrid retrieval ranks eligible evidence
        ↓
Evidence-gated bridge drafts and outreach text are prepared
        ↓
/api/triage-job returns preview OR /api/add-job persists company + role
        ↓
Role remains DISCOVERED until the candidate reviews it
```

The API's persona/location/domain classifications are suggestions, not definitive judgments. Company facts are supplied by the user; the application does not crawl directories or infer a verified company tech stack from a domain.

## API routes

| Route | Behavior |
|---|---|
| `POST /api/triage-job` | Validates and returns a non-persisting preview with triage, evidence retrieval, bridges, and outreach draft |
| `POST /api/add-job` | Performs the same workflow and writes company/role records to SQLite for human review |
| `POST /api/ingest-companies` | Validates a bounded batch and upserts company inventory records |
| `GET /docs` | Local OpenAPI/Swagger interface for API requests |

All job intake endpoints require a successful hybrid response using the configured local embedding model. They do not accept lexical fallback as a successful API result.

## Operational caveat in the current checkout

`job_copilot.py` invokes `jobgs-engine/run_rag_session.ps1` to own Ollama startup and teardown, but that script is absent from the current repository checkout. Therefore, API triage/add cannot complete their required managed Ollama flow in a fresh clone until the wrapper is restored and tested. The standalone `rag_matcher.py` command is separate and can use a manually started local Ollama process. Do not mark managed lifecycle verification successful based only on the CLI output.

## Governance

- Intake is user-initiated and the raw job text is supplied by the candidate.
- No crawling, portal login, application submission, or message sending occurs.
- Outreach and bridge statements are drafts requiring review.
- A role starts at `DISCOVERED`; later status movement is a human action.
- Local SQLite is not encrypted and the application has no login; avoid secrets and confidential source documents.

## Learning outcomes

This milestone practices request validation, relational schemas, SQLite conflict handling, idempotency, structured triage, local-service orchestration, provenance, and human approval gates.

## Release reference

The merged inventory and triage implementation is tagged `v1.4.1`. See [Week 3](Week-3-Milestone.md), [Week 4](Week-4-Milestone.md), and the [changelog](../CHANGELOG.md).
