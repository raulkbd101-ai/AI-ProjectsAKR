# JobG's Changelog

Release notes for the personal JobG's MVP. The tags listed below are historical references and should not be moved or overwritten. The current completed MVP release is `v1.6`.

## [v1.6] — Week 4 dashboard, lifecycle, analytics, and exports

### Added

- SQLite-backed tracker with guarded lifecycle transitions through `DISCOVERED`, `USER_REVIEWED`, `APPLIED`, `INTERVIEWING`, `OFFER`, `REJECTED`, `WITHDRAWN`, and `ARCHIVED`.
- Filters for persona, domain, status, search term, literal profile coverage, and best saved RAG relevance, plus supported sort orders.
- Dashboard summaries for tracked roles, active outreach drafts, status counts, and progress toward the 10-role daily logging cap.
- Markdown and JSON offline exports containing role details, evidence matches, bridge drafts, and outreach drafts; confidential evidence claim text is redacted.
- Additive SQLite migration for tracker coverage and lifecycle state compatibility.

### Interpretation and boundaries

- The daily cap counts roles logged in JobG's; it does not establish that an external application was submitted.
- Profile-term coverage and evidence retrieval relevance are separate indicators, not job-fit, ATS passage, proficiency, or hiring-probability scores.
- Dashboard ratios reflect current status snapshots. The application does not maintain a historical status-transition event log, so these are not cohort conversion rates.
- JobG's prepares drafts and exports but does not submit applications or send messages.
- **Current-checkout issue:** `job_copilot.py` expects `run_rag_session.ps1` for managed Ollama startup and teardown, but the script is absent from this repository checkout. The API's triage/add routes cannot complete their required hybrid-RAG path until that dependency is restored and verified.

### Verification

- The local suite was recorded as 34 passing test methods at the Week 4 milestone. Re-run `python -m unittest discover -s tests -v` in the current checkout for a fresh verification.
- GitHub tag `v1.6` points to the merged Week 4 release commit.

## [v1.5] — Week 3 persona weighting and evidence-grounded bridges

### Added

- Persona-adjusted evidence ordering for Director, Architect, and TPM while preserving the base retrieval score and exposing ranking signals.
- Allowlisted conceptual technology bridges across cloud, data, and legacy modernization domains.
- Bridge eligibility checks requiring a non-confidential, persona-compatible SQLite claim that explicitly supports the mapped source technology.
- Bridge results carry evidence provenance and a clear conceptual-adjacency disclaimer.

### Verification

- Week 3 milestone record: 26 local unit tests passed.

## [v1.4.1] — Week 2 executive triage and SQLite inventory

### Added

- `companies_inventory` for on-demand company facts and `application_tracker` for supplied job opportunities.
- `/api/triage-job` for a non-persisting preview and `/api/add-job` for human-review intake with a `DISCOVERED` state.
- Rule-based suggestions for persona, domain, and work model/location, plus evidence retrieval, conceptual bridge drafts, and outreach drafts.
- Validated batch company upserts through the `ingest_companies.py` module and `/api/ingest-companies` endpoint.

### Boundaries

- Job URLs and descriptions are supplied by the candidate; this is not a career-site crawler.
- API intake does not apply or message. The candidate must review the result and act externally.
- `/api/triage-job` and `/api/add-job` require successful managed hybrid retrieval; lexical fallback is not accepted for these endpoints.

## [v1.3.0] — local hybrid evidence retrieval

### Added

- Standalone `rag_matcher.py` using 65% local embedding similarity and 35% lexical overlap when semantic retrieval is available.
- Local Ollama `nomic-embed-text` embedding requests and a rebuildable SQLite `evidence_embeddings` cache; `profile_evidence` remains the source of truth.
- Persona filtering, confidentiality exclusion by default, and explicit lexical fallback behavior for the standalone retrieval command.

### Boundaries

- Retrieval results rank evidence relevance only; they do not establish truth, proficiency, fit, or hiring probability.
- The module retrieves evidence; it is not a generative RAG resume writer.

## [v1.2] — evidence dossier and persona-tagged bridge foundation

- Added structured candidate-authored evidence claims with persona tags, source notes, evidence status, and confidentiality metadata.
- Added initial reviewable transferable technology bridge support.
- Claims remain self-reported; confidentiality labels do not encrypt or restrict access to local SQLite data.

## [v1.1.0] — explainable profile-term workflow

- Added validated evidence-profile storage and a guide for entering supportable candidate claims.
- Replaced the arbitrary heuristic 90% approval gate with a transparent profile-term scan and user-selected role logging.
- Clarified that literal keyword coverage does not estimate job fit, ATS success, or interview likelihood.

## [v1.0.0] — local single-user foundation

- Added a FastAPI form to enter a company, role, optional job URL, and job description.
- Added a SQLite profile and local role log with a 10-entry daily cap and a review-before-log flow.
- Added a generic starter profile and initial CI checks.

## Version and release note

The repository also contains an earlier `v1.4` tag associated with release preparation. `v1.4.1` is the release tag associated with the merged Week 2 executive triage and inventory implementation. Tags are immutable historical references; do not retarget an existing tag to make the numbering appear linear.
