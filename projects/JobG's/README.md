# JobG's — Personal Job Search Engine

Copyright (c) 2026 Amith Raul. All rights reserved. Reuse of this project's original code and materials is not granted without separate written permission. See [LICENSE](LICENSE). Public GitHub availability does not automatically detect or prevent copying.

**Latest tag:** `v1.2` (evidence dossier, persona tags, and reviewable tech bridges)

**Next release target:** `v1.3.0` (local hybrid evidence retrieval; proposed, not yet released)

**Status:** Local, single-user MVP

JobG's is a local, single-user job-search assistant. It helps a candidate review manually supplied job descriptions against a locally stored profile and track roles they choose to pursue. It is designed to make job-search decisions deliberate and to track a daily limit of 10 logged entries.

## Product context

Version 1.0 establishes the first governed workflow:

1. Enter a company, role, optional job URL, and job description.
2. Compare the description with the candidate profile using transparent, rule-based keyword scanning.
3. Review which profile skill terms are present and absent in the description.
4. Decide whether to log the role yourself, subject to the daily cap.

The candidate remains in control. Job descriptions are supplied manually; the app does not crawl job sites, rewrite a resume, or submit applications. The dashboard's profile-term scan reports literal skill mentions and does not estimate job fit or interview likelihood. Evidence claims are candidate-authored and not independently verified. The current `rag_matcher.py` prototype separately ranks saved evidence using keyword overlap and embeddings from local Ollama. It is a command-line retrieval tool, not a generative RAG assessment, and is not wired into the dashboard. See [EVIDENCE_PROFILE_GUIDE.md](EVIDENCE_PROFILE_GUIDE.md), [RAG_MATCHER_GUIDE.md](jobgs-engine/RAG_MATCHER_GUIDE.md), and [MVP_BUILD_PLAN.md](MVP_BUILD_PLAN.md) for details.

## Technology

- Python 3.10 or newer
- FastAPI for the local web application and form endpoints
- Jinja2 for HTML rendering with autoescaping
- Pydantic for validating structured evidence claims
- SQLite for the local profile and application log
- Uvicorn as the development server
- Ollama with `nomic-embed-text` for optional, local-only embeddings in the retrieval prototype
- GitHub Actions for automated syntax and unit checks on pull requests

## Project structure

```text
JobG's/
├── README.md
├── AI_UPSKILLING_ROADMAP.md
├── docs/
│   ├── adr/                    # Architecture decisions and learning notes
│   └── evaluations/            # Sanitized retrieval evaluations
└── jobgs-engine/
    ├── app.py                 # FastAPI interface and review/confirm flow
    ├── database.py            # SQLite setup, sample profile, daily count
    ├── matcher.py             # Explainable term scan and evidence-supported bridges
    ├── evidence.py            # Typed claim model and local evidence storage
    ├── rag_matcher.py         # Standalone local hybrid evidence retrieval prototype
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

`database.py` creates the tables and seeds a generic profile only when the profile table is empty. Changing the seed values later will not overwrite an existing database. The database file is created in the current working directory, so start the app from `jobgs-engine` as shown above.

## Verify locally

From `jobgs-engine` with the virtual environment active:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app.py database.py matcher.py evidence.py evidence_profile.py rag_matcher.py
```

GitHub Actions runs these checks for pull requests and pushes that change this project. The Ollama retrieval smoke test is optional because it requires Ollama and a local model to be installed.

To try local retrieval from `jobgs-engine`, install Ollama separately, pull its embedding model, and run:

```powershell
ollama pull nomic-embed-text
python rag_matcher.py "cloud data platform architecture and BI modernization" --persona Architect
```

The first command downloads model files to your PC. The Python code sends embedding requests to Ollama on loopback; it does not call a hosted inference API. The vector cache is derived from SQLite evidence and can be rebuilt. See the [retrieval guide](jobgs-engine/RAG_MATCHER_GUIDE.md).

## Git and release workflow

Use a short-lived branch for each change, then open a pull request into `main`. Review the diff and wait for the **JobG's CI** workflow to pass before merging.

```powershell
git switch -c feature/short-description
git add ".github/workflows/jobgs-engine.yml" "projects/JobG's"
git commit -m "feat(jobgs): describe the change"
git push -u origin feature/short-description
```

For the proposed `v1.3.0` release, first merge the reviewed pull request into `main` and wait for CI to pass. Then create the tag from the updated `main`:

```powershell
git switch main
git pull
git tag -a v1.3.0 -m "JobG's v1.3.0 — local hybrid evidence retrieval"
git push origin v1.3.0
```

See [CHANGELOG.md](CHANGELOG.md) for the release history and commit notes. Generative RAG analysis and resume-draft suggestions remain future work and must be grounded in evidence and reviewed by the candidate.

For the longer learning and delivery plan, see the [24-week AI engineering roadmap](AI_UPSKILLING_ROADMAP.md), including the first four weeks on local retrieval, vector search, and evidence-grounded RAG.
