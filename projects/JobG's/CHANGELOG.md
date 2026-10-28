# Changelog

All notable JobG's changes are recorded here. Published tags are preserved; release notes identify the commit each release represents.

## [Unreleased]

No release scope has been committed for the next version. Weeks 3–4 items remain planned.

## [1.4.1] — Week 2 job intake and human-governed triage

Corrective release tag for the PR #9 merge. The pre-existing v1.4 tag was not moved; it points to an earlier commit and does not represent the Week 2 merge. Tag v1.4.1 points to merge commit a04bcbc2434c8fe95c9e319086fc012c5b6804ff.

### Added

- SQLite companies_inventory records for lightweight company metadata and application_tracker records for manually supplied job discoveries.
- Additive database initialization that creates or upgrades the Week 2 tables without replacing existing inventory rows.
- POST /api/triage-job for rule-based persona, domain, and location suggestions, local evidence retrieval, technology bridge drafts, and outreach drafts without saving a tracker row.
- POST /api/add-job for the same review workflow with a SQLite DISCOVERED record; duplicate job URLs are rejected as conflicts.
- POST /api/ingest-companies for validated, bounded company batches.
- Job Copilot integration with local hybrid retrieval using Ollama nomic-embed-text. Managed job triage requires hybrid retrieval and reports service failure rather than representing fallback as successful hybrid matching.
- Optional Windows PowerShell session wrapper for a managed Ollama query, including process and port cleanup checks.

### Governance and limitations

- Job inputs are supplied manually. This release does not scrape job boards or career sites.
- Persona, domain, and location outputs are rule-based suggestions, not definitive classification or job-fit decisions.
- Retrieval scores measure evidence relevance only; they do not measure candidate qualification, claim truth, or hiring probability.
- Bridge statements and LinkedIn outreach are drafts for human review. No application or message is submitted or sent automatically.
- This is a rule-based co-pilot, not a multi-agent autonomous system. Local SQLite data is not encrypted by the application.

### Verification

- PR #9 merged to main on 2026-10-28.
- All five checks on merge commit a04bcbc passed: build, Python 3.12 checks, Python 3.14 checks, deploy workflow, and report-build-status.
- Earlier retrieval and evidence test results are recorded in the v1.3.0 section below.

### Commit note

Suggested commit message: feat(v1.4): add human-governed job triage workflow

## [1.3.0] — local hybrid evidence retrieval

### Added

- Standalone `rag_matcher.py` prototype that retrieves candidate-authored evidence by combining lexical overlap with local Ollama embeddings.
- Rebuildable `evidence_embeddings` cache in SQLite, keyed by evidence row and model; `profile_evidence` remains the source of truth.
- Persona-aware retrieval, confidential-claim exclusion by default, and a keyword-only fallback when local embeddings are unavailable.
- Retrieval guide, 24-week AI learning roadmap, and documentation spaces for architecture decisions and sanitized evaluations.
- Unit coverage for persona filtering, confidential-claim exclusion, hybrid-score composition, vector-cache persistence, and model-unavailable fallback.

### Scope and limitations

- At the v1.3.0 milestone, retrieval was a CLI module and was not integrated into the FastAPI dashboard. Week 2 later added managed retrieval to job intake.
- It does not generate a RAG narrative, assess job fit, rewrite resumes, scrape job boards, or submit applications.
- Ollama model files must be downloaded once. Runtime embedding requests use the local loopback service; no hosted inference API is configured.
- Retrieval scores indicate evidence-search relevance only, not claim truth, candidate proficiency, hiring likelihood, or job fit.
- The v1.2 tag remains the evidence dossier and persona-aware transferable bridge milestone. Existing tags are preserved.

### Verification

- Local Python 3.14 checks: all 23 unit tests pass; the retrieval tests use a temporary SQLite database and mocked embedding responses.
- The CI syntax step now includes `rag_matcher.py` and the evidence modules.
- Keep the Ollama-dependent smoke command optional; CI does not download model weights or call Ollama.

### Commit note

```text
feat(jobgs): add local hybrid evidence retrieval prototype
```

## [1.2] — tagged evidence and bridge foundation

- Added persona-specific evidence claims and reviewable, evidence-supported transferable technology bridge drafts.
- Kept claims candidate-provided and human-reviewed; the bridge drafts do not claim direct experience with an adjacent target technology.

## [1.1.0] — 2026-10-27

First learning-focused update after the local v1.0 release. This is still a personal, local MVP; it is not an autonomous or public job application service.

### Added

- Pydantic `EvidenceClaim` model with required-field, length, and allowed-value validation.
- Local SQLite `profile_evidence` table linked to the master profile, plus helpers for saving and listing claims.
- Evidence profile guide, two-week MVP learning plan, and release notes for future maintainers and the learner.

### Changed

- Replaced the arbitrary heuristic fit percentage and 90% approval gate with a transparent count of profile skill terms explicitly mentioned in the JD.
- Showed matched skills, profile skills not mentioned, and explicitly matched domains.
- Removed unsupported claims about ATS outcomes and automatic mastery of missing tools; role logging now follows the candidate's own review.
- Clarified in the UI that term coverage is not job fit, proficiency, or hiring probability.
- Documented that evidence labels are self-reported and do not constitute independent verification; no personal claims or sample metrics were seeded.

### Verification

- Local Windows run: database initialized and reported the existing master profile without replacing it.
- Final local workflow checks: 7 tests passed, including evidence-claim validation, save/list behavior, profile-term reporting, and candidate-selected role logging.
- The first evidence-test run surfaced a Windows console encoding issue in test setup output; the setup output was captured, then all 7 checks passed.
- Syntax compilation completed for the app, database, matcher, evidence model, and test files.

### Commit note

Suggested commit message:

```text
feat(jobgs): add evidence profile foundation for v1.1.0
```

## [1.0.0] — 2026-10-25

First local MVP release.

### Added

- FastAPI form for entering a company, role, job URL, and job description.
- Rule-based profile matching with a reviewable score and matched competencies.
- Server-side, one-time evaluation tokens so the confirmation form refers to the evaluation shown to the user.
- SQLite profile and approved-opportunity log, with a daily maximum of 10 entries.
- Generic starter profile, setup instructions, and GitHub Actions CI checks.

### Scope

- Job descriptions are entered manually.
- Confirmation logs an opportunity locally; it does not submit an application.
- Match scores are heuristic and should not be interpreted as calibrated fit or ATS success probabilities.
- The app is intended for local, single-user use.

### Commit summary

Suggested release commit message:

```text
feat(jobgs): release local job-search workflow v1.0.0
```

Release contents: local FastAPI UI, SQLite persistence, heuristic matcher, review-and-confirm flow, dependency manifest, automated CI checks, and user/developer documentation.
