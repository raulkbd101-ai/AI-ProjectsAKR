# JobG's — Personal Job Search Engine

Copyright (c) 2026 Amith Raul. All rights reserved. Reuse of this project's original code and materials is not granted without separate written permission. See [LICENSE](LICENSE). Public GitHub availability does not automatically detect or prevent copying.

**Latest JobG tag:** v1.4.1 (Week 2 job intake and human-governed triage; corrective tag for the PR #9 merge)

**Tag note:** The pre-existing v1.4 tag is preserved and still points to an earlier commit; v1.4.1 points to merge commit a04bcbc. No tag was force-moved.

**Next release:** Not scheduled. Weeks 3–4 remain roadmap work.

**Status:** Local, single-user MVP

JobG's is a local, single-user job-search assistant. It helps a candidate review manually supplied job descriptions against a locally stored profile and track roles they choose to pursue. It is designed to make job-search decisions deliberate and to track a daily limit of 10 logged entries.

## Product context

JobG's is a local, single-user career workflow. The candidate supplies job details manually; the app does not scrape career websites or job boards.

The current workflow has two layers:

1. The dashboard's original profile-term scan reports literal skill mentions and does not estimate job fit, interview likelihood, or ATS success.
2. The Week 2 API accepts a company, role, job URL, description, and optional location/company details. POST /api/triage-job returns rule-based persona/domain/location suggestions, local evidence retrieval, bridge drafts, and a draft outreach message. POST /api/add-job saves a discovered role with DISCOVERED status; it does not submit an application or send a message. POST /api/ingest-companies upserts a bounded company batch into SQLite.

The standalone rag_matcher.py combines 65% semantic similarity with 35% lexical keyword overlap, using local Ollama embeddings (nomic-embed-text). A retrieval score indicates evidence relevance only; it is not a fit, proficiency, or truth score. Managed job triage requires hybrid retrieval and reports an error if the local service is unavailable; the CLI also supports keyword-only operation. Evidence and bridges are candidate-provided drafts and require human review. The local SQLite database is not encrypted by the application; keep private data and database files out of Git.

See [Week 1 — Local Vector Index & Hybrid RAG Search](https://github.com/raulkbd101-ai/AI-ProjectsAKR/wiki/Week-1-Milestone) and [Week 2 — Executive Decision Co-Pilot & SQLite Ingestion](https://github.com/raulkbd101-ai/AI-ProjectsAKR/wiki/Week-2-Milestone:-Executive-Decision-Co%E2%80%90Pilot-&-SQLite-Ingestion) in the GitHub Wiki for implementation details.

## Technology

- Python 3.10 or newer
- FastAPI for the local web application and JSON API
- Pydantic for validating evidence, job, and company payloads
- SQLite for the profile evidence dossier, company inventory, and application tracker
- Jinja2 for server-rendered HTML with autoescaping
- Uvicorn as the local development server
- Ollama with nomic-embed-text for local semantic evidence retrieval
- PowerShell for the optional Ollama session wrapper on Windows
- GitHub Actions for automated syntax, build, and unit checks

## Project structure

```text
JobG's/
├── README.md
├── AI_UPSKILLING_ROADMAP.md
├── docs/
│   ├── adr/                    # Architecture decisions and learning notes
│   └── evaluations/            # Sanitized retrieval evaluations
└── jobgs-engine/
    ├── app.py                 # FastAPI UI and job/evidence/company API routes
    ├── database.py            # SQLite schema and additive initialization
    ├── matcher.py             # Explainable term scan and evidence-supported bridges
    ├── evidence.py            # Typed claim model and local evidence storage
    ├── job_copilot.py         # Rule-based triage, retrieval, drafts, and job logging
    ├── ingest_companies.py   # Validated company inventory upsert utility
    ├── run_rag_session.ps1   # Optional managed Ollama query session on Windows
    ├── rag_matcher.py         # Local hybrid evidence retrieval CLI and SQLite cache
    ├── RAG_MATCHER_GUIDE.md   # Local model setup and usage
    ├── templates/
    │   └── evidence.html      # Evidence dossier page and navigation
    ├── requirements.txt       # Runtime dependencies
    ├── .gitignore             # Excludes local data and environment files
    └── tests/                 # Automated unit checks
```

The SQLite database, Python virtual environment, and bytecode are local files and are excluded from Git. The checked-in seed profile is generic sample data. Edit the seed values before initializing a fresh database, or update your existing local database using your own trusted workflow. Do not commit personal profile data or the generated database.

## Run locally on Windows

Open PowerShell at the repository root, then run:

```powershell
Set-Location "projects\JobG's\jobgs-engine"
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python database.py
python app.py
```

Open <http://127.0.0.1:8000/> in your browser. Keep the terminal open while using the app; press **Ctrl+C** to stop the server.

`database.py` creates the tables and seeds a generic profile only when the profile table is empty. Changing the seed values later will not overwrite an existing database. The SQLite database path is resolved beside database.py inside jobgs-engine. Run commands from that folder so templates and other relative project resources resolve consistently.

## Verify locally

From `jobgs-engine` with the virtual environment active:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app.py database.py matcher.py evidence.py evidence_profile.py rag_matcher.py job_copilot.py ingest_companies.py
```

GitHub Actions runs these checks for pull requests and pushes that change this project. The Ollama retrieval smoke test is optional because it requires Ollama and a local model to be installed.

To try local retrieval from `jobgs-engine`, install Ollama separately, pull its embedding model, and run:

```powershell
ollama pull nomic-embed-text
python rag_matcher.py "cloud data platform architecture and BI modernization" --persona Architect
```

The first command downloads model files to your PC. The Python code sends embedding requests to Ollama on loopback; it does not call a hosted inference API. The vector cache is derived from SQLite evidence and can be rebuilt. See the [retrieval guide](jobgs-engine/RAG_MATCHER_GUIDE.md).

## Git and release workflow

Use a short-lived branch for each change, then open a pull request into main. Review the diff and wait for the JobG's CI workflow to pass before merging. For a release tag, tag the verified merge commit on main; do not move an existing published tag.

The Week 2 implementation was merged by PR #9. The five checks on merge commit a04bcbc passed (build, Python 3.12, Python 3.14, deploy workflow, and report-build-status). The corrective tag v1.4.1 points to that merge commit; the earlier v1.4 tag remains unchanged and is not the Week 2 release target.

See CHANGELOG.md for release scope and verification notes. A Git tag is distinct from a published GitHub Release entry. Generative resume rewriting, job-site scraping, autonomous agents, and form automation are not included in this release.

For the learning plan, see the 24-week AI engineering roadmap, including the Week 1 retrieval and Week 2 co-pilot milestones.
