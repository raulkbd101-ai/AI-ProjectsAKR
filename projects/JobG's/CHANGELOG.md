# Changelog

All notable JobG's changes are recorded here. Published tags are preserved; release notes identify the commit each release represents.

## [Unreleased] — proposed v1.6

### Added — Week 4 dashboard and tracker

- Local SQLite-backed tracker page with persona, domain, status, keyword, profile-coverage, and RAG-relevance filters.
- Human-governed lifecycle transitions using `DISCOVERED`, `USER_REVIEWED`, `APPLIED`, `INTERVIEWING`, `OFFER`, `REJECTED`, `WITHDRAWN`, and terminal `ARCHIVED` states.
- Dashboard analytics for tracked roles, active outreach drafts, current status counts, current-status snapshot ratios, and progress against the 10-role daily logging cap.
- Markdown and JSON offline exports for tracked roles, saved evidence matches, bridge drafts, and outreach drafts. Confidential evidence claim text is redacted.
- Additive SQLite migration preserves tracked roles, adds nullable profile-term coverage, and maps older `REVIEWED`/`INTERVIEW` states to `USER_REVIEWED`/`INTERVIEWING`.
- Automated tracker tests cover lifecycle guards, filters, reporting, exports, and legacy database migration.

### Governance notes

- Daily cap measures roles the user logged after review; it does not verify external application submission.
- RAG relevance and profile keyword coverage are separate retrieval indicators, not a calibrated job-fit or hiring-probability score.
- Stage ratios are based on current status snapshots. Historical funnel conversion requires a status-history table.
- JobG's stores outreach drafts but does not send messages or submit applications.

## [Unreleased] — proposed v1.5

### Added

- Persona-weighted evidence ranking for Director, Architect, and TPM, with the original retrieval score retained and persona signals exposed for review.
- Evidence-grounded transferable technology bridges for cloud, data-platform, and legacy modernization concepts. Drafts include supporting SQLite claim provenance and explicit conceptual-adjacency disclaimers.
- Bridge coverage for 26 unit tests across persona ranking, evidence requirements, persona scope, expanded technology mappings, and existing workflows.

### Guardrails

- Bridge drafts are emitted only when eligible, non-confidential profile evidence explicitly supports the mapped source technology.
- No bridge claims direct hands-on production use of a target technology; human review remains required.

### Verification

- Local Windows unit test suite: 26 tests passed.

## [1.3.0] — local hybrid retrieval

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
