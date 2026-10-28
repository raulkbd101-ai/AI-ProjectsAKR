# Week 4 Milestone: Executive Dashboard, Lifecycle & FinOps Analytics

## Overview

Week 4 adds a local dashboard and human-managed tracker for opportunities ingested by JobG's. The operator can review saved role details, filter and prioritize the list, update lifecycle state, inspect activity against the daily role-logging cap, and export an offline report.

## Architecture

- **FastAPI** serves the dashboard, tracker, lifecycle update, and export routes.
- **SQLite** remains the source of truth for roles, current lifecycle status, profile-term coverage, evidence retrieval results, bridge drafts, and outreach drafts.
- **Jinja2** renders the dark-mode, responsive tracker interface.
- **Local evidence retrieval** may supply matched profile claims; it does not decide whether a person should apply.
- **Human review** controls all lifecycle transitions and any external application or outreach action.

## Lifecycle states

`DISCOVERED → USER_REVIEWED → APPLIED → INTERVIEWING → OFFER`

Roles may also move to `REJECTED`, `WITHDRAWN`, or `ARCHIVED` according to guarded transition rules. `ARCHIVED` is terminal. The application records current status; it does not yet maintain a full status-change event history.

## Tracker filters

The tracker supports filtering by:

- Persona: Director, Architect, TPM, or Unclear.
- Domain: Fintech, Banking, Data/AI, or Startups.
- Current lifecycle status.
- Search text across company, role, and location.
- Minimum and maximum profile keyword coverage.
- Minimum and maximum best RAG relevance.
- Sorting by newest, RAG relevance, profile keyword coverage, or company name.

Profile keyword coverage reports literal saved profile skill terms found in the JD. Best RAG relevance is the highest evidence retrieval score among the role's stored matches. Neither metric is a job-fit probability, proficiency score, or hiring prediction.

## Dashboard and FinOps metrics

The dashboard summarizes total tracked roles, active outreach drafts, current lifecycle counts, and the daily logging cap. The progress visual shows roles entered into the daily reviewed-role log against the 10-role limit. It does not confirm that an external application was submitted.

The applied share, interview-to-applied, and offer-to-applied numbers are current-status snapshot ratios. They should not be interpreted as historical cohort conversion rates because the system does not yet store every status transition.

## Offline exports

- `GET /export/applications?format=markdown`
- `GET /export/applications?format=json`

Exports include job details, saved evidence matches, transferable bridge drafts, and outreach drafts. Confidential evidence claim text is redacted. Treat the downloaded file as sensitive career information.

## Human-in-the-loop and privacy

- JobG's does not submit applications or send outreach messages.
- Lifecycle updates are checked against an allowed-transition map.
- Outreach content is a draft for candidate review.
- Keep the development server bound to `127.0.0.1`; the local app does not provide user authentication.

## Release

**Released:** `v1.6` — Executive Dashboard, Lifecycle & FinOps Analytics. The Week 4 PR was merged before the annotated release tag was published.

Week 4 closes the first four-week personal MVP milestone. The overall JobG's product vision and 24-week learning plan continue. This release does not deliver a public service, automatic job-site discovery, or automatic application submission.
