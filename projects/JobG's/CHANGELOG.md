# Changelog

All notable JobG's changes are recorded here. This project follows Semantic Versioning for tagged releases.

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

## Planned: 1.1.0

- AI-assisted semantic job/profile analysis.
- Evidence-linked resume and cover-note draft suggestions for human review.
- No automatic application submission.
