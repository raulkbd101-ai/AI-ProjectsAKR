# JobG's personal MVP build plan

## Goal

Build a private, local-first job-search assistant that helps one candidate discover or import roles, understand how their experience maps to each role, prepare truthful application materials, and track decisions. The candidate reviews every recommendation and submits every application manually.

This is a focused two-week learning sprint, not a promise to cover every current AI technology or to launch a public multi-user service. ChatGPT and Gemini can explain concepts, review design choices, and quiz the learner. Using either chat product does not by itself connect the JobG app to a model; an app integration would require choosing a model API and handling its key, cost, privacy, and data-sharing behavior separately.

## Product boundaries

- Personal, single-user use first; local profile and job data stay on the PC by default.
- Support jobs globally by letting the user paste or import a job description and record its country, location, currency, source, and date. Global scraping is out of the first working slice.
- No automatic applications, messages, or account actions.
- Never invent candidate qualifications, employment history, metrics, or evidence.
- A numeric score is only useful if its meaning and limitations are visible. The current baseline reports exact profile terms found in a JD; it is not a fit probability.
- Review each job source's permitted access and data terms before adding automated collection.

## Current starting point

Version 1.0 is a local FastAPI and SQLite application. This 1.1 development branch has started replacing its misleading 90% keyword gate with a transparent profile-term scan. This baseline gives us something understandable to compare with later AI-assisted results.

## Two-week learning path

| Sprint | Build outcome | Concepts to learn and explain back |
|---|---|---|
| Days 1–2 | Clean local setup, branch, README, baseline scan, and review workflow | Python modules, virtual environments, SQLite, Git branches, commits, pull requests, HTTP forms |
| Days 3–4 | A provider-independent AI analysis interface that accepts a JD and profile evidence | API requests, secrets, JSON schemas/structured output, latency, token/cost estimates |
| Days 5–6 | Evidence-linked role analysis with strengths, gaps, and unknowns | Retrieval, embeddings vs. keyword search, grounding, prompt injection, privacy boundaries |
| Day 7 | Small labeled examples for checking matcher quality and regressions | Evaluation sets, precision/recall tradeoffs, human review, reproducibility |
| Days 8–9 | Candidate-approved resume summary and cover-note drafts tied to supplied facts | Constrained generation, provenance, factuality checks, document export |
| Day 10 | Role records with country, location, currency, source, and status | Data modeling, validation, migrations, internationalization basics |
| Days 11–12 | CI checks and a repeatable container or deployment rehearsal | GitHub Actions, dependency pinning, Docker concepts, environment configuration |
| Days 13–14 | End-to-end review, cost/privacy notes, version 1.1 notes, and interview walkthrough | Threat modeling, observability, tradeoffs, release/tagging, explaining architecture |

## Build order and acceptance checks

1. **Explainable baseline** (started): the screen calls its number profile-term coverage, lists exact terms found and absent, never blocks a candidate based on an arbitrary percentage, and asks the user to review before logging.
2. **Profile evidence**: store editable candidate facts and optional source references privately. An AI answer must point back to supplied evidence or mark the item unknown.
3. **AI analysis**: define a provider interface and strict response schema; call one chosen model only after checking cost, API-key handling, retention, and consent. Keep provider-specific code behind the interface.
4. **Evaluation**: compare baseline and AI analysis on a small, manually reviewed set of representative jobs. Do not claim a calibrated score without enough labeled data.
5. **Drafts and tracking**: make drafts editable, preserve original text, and require the user to confirm before saving application status.
6. **CI and release**: run checks on pull requests, review the diff, document known limits, then publish a tagged release. No secrets, personal profile, resume, or SQLite database in Git.

## Learning routine

For each change, ask ChatGPT and Gemini to explain one concept in plain language, predict the behavior before running it, and then compare their explanation with the code and observed output. Keep a short note of: **what changed, why, how it works, what could fail, and how to explain the tradeoff in an interview**. Do not paste private profile data or API keys into either service.

## Explicitly out of scope for this sprint

- A public SaaS launch, multi-user accounts, or storing other people's resumes.
- Blind scraping or bypassing job-site access controls.
- Automatic application submission or fabricated resume content.
- Trying to implement every AI trend (agents, fine-tuning, multimodal models, and vector databases are not all required for this MVP).
