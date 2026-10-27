# Changelog

All notable JobG's changes are recorded here. This project follows Semantic Versioning for tagged releases.

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

## Planned: 1.2.0

- AI-assisted semantic job/profile analysis.
- Evidence-linked resume and cover-note draft suggestions for human review.
- No automatic application submission.
