# JobG's MVP Scope and Delivery Record

## Product problem

The motivating workflow is a candidate's repeated, manual effort to research a role, compare it with a selected resume persona, locate supportable evidence, prepare application notes, submit through an external portal, and update a tracker. The candidate estimates this can take about 50 minutes per application. JobG's was built to reduce duplicated preparation and recordkeeping—not to automate the external application or guarantee an ATS outcome.

The 50-minute estimate is a problem statement, not an independently measured baseline or a proven time-saving result. Measuring task time and candidate corrections is a future evaluation item.

## Intended MVP outcome

Deliver a personal, local-first tool that helps one candidate:

1. Maintain a structured, candidate-authored evidence dossier across Director, Architect, and TPM resume tracks.
2. Supply role details and job-description text manually, then receive explainable persona, domain, and location suggestions.
3. Retrieve related evidence locally, see evidence-supported conceptual technology bridges, and review an outreach draft.
4. Save a role for human review, track its lifecycle, filter and prioritize the backlog, review activity, and export records offline.
5. Submit applications and contact people manually outside JobG's.

## Delivered in v1.6 (Weeks 1–4)

| Week | Delivered capability | Learning concepts practiced |
|---|---|---|
| 1 | SQLite evidence foundation and local lexical/embedding retrieval prototype | Data modeling, embeddings, vector similarity, local inference, retrieval versus generation |
| 2 | Company inventory, job intake APIs, rule-based triage, role persistence, evidence/bridge/outreach drafts | API validation, upserts, idempotency, relational data, human approval boundary |
| 3 | Persona-weighted evidence ranking and claim-gated transferable technology bridges | Ranking, evidence provenance, relevance weighting, factuality guardrails |
| 4 | Tracker lifecycle, filters, dashboard metrics, daily logging cap, Markdown/JSON export | State machines, SQL filters, analytics, privacy-aware export, CI/release workflow |

Release `v1.6` closes the initial four-week MVP milestone. This is not a standalone public SaaS product, multi-user service, or autonomous job-submission bot. The 24-week learning roadmap continues beyond the MVP.

## Product and safety boundaries

- Personal/single-user local use. SQLite is not encrypted and the app has no login; run only on a trusted PC and keep the server on loopback.
- Candidate facts are self-reported. A source reference or status label does not independently verify the claim.
- Similarity and keyword measures describe retrieval/coverage only. They are not fit probabilities or hiring predictions.
- The application receives manually supplied role information. It does not scrape company portals or bypass access controls.
- Bridge drafts describe conceptual adjacency and are returned only with eligible source evidence; they never imply direct experience with a target tool unless the dossier supports that exact claim.
- No application submission, external account action, or outreach delivery is automated.
- Local embeddings avoid sending profile text to a hosted embedding service, but Ollama model downloads, local compute, disk, and electricity still have costs.
- Never commit personal resumes, sensitive job descriptions, SQLite files, embedding caches, secrets, or confidential company material.

## Run and verify

From the project root in PowerShell:

```powershell
Set-Location "jobgs-engine"
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python database.py
python -m unittest discover -s tests -v
python app.py
```

Open <http://127.0.0.1:8000/>. Local hybrid RAG CLI usage and Ollama setup are described in [RAG_MATCHER_GUIDE.md](jobgs-engine/RAG_MATCHER_GUIDE.md).

### Current checkout limitation

The job-copilot API imports and invokes `jobgs-engine/run_rag_session.ps1` to manage Ollama and requires `retrieval_mode="hybrid"`. That PowerShell script is absent from this checkout. Consequently, the intake API cannot complete as documented until the wrapper is restored and verified. This is a known implementation/release-readiness gap, not a documentation-only issue.

## Suggested measurement plan

For a future, privacy-safe evaluation, use a small set of manually selected roles and record:

- minutes spent on role review and application preparation with and without JobG's;
- whether the suggested persona was accepted or changed;
- whether retrieved evidence was relevant, missed, or misleading;
- the number of candidate edits required to bridge/outreach drafts;
- whether the candidate found an unsupported claim (target: zero unsupported claims reused).

Do not publish a productivity or ATS-rejection improvement claim until there is a repeatable comparison with a documented sample and method.
