# JobG's — Personal Job Search Engine

Copyright (c) 2026 Amith Raul. All rights reserved. Reuse of this project's original code and materials is not granted without separate written permission. See [LICENSE](LICENSE). Public GitHub availability does not automatically detect or prevent copying.

**Version:** 1.1.0 (personal, local MVP)

**Status:** Local, single-user MVP

JobG's is a local, single-user job-search assistant. It helps a candidate review manually supplied job descriptions against a locally stored profile and track roles they choose to pursue. It is designed to make job-search decisions deliberate and to track a daily limit of 10 logged entries.

## Product context

Version 1.0 establishes the first governed workflow:

1. Enter a company, role, optional job URL, and job description.
2. Compare the description with the candidate profile using transparent, rule-based keyword scanning.
3. Review which profile skill terms are present and absent in the description.
4. Decide whether to log the role yourself, subject to the daily cap.

The candidate remains in control. This release does **not** search career sites, call an AI model, rewrite a resume, or submit applications. Its profile-term scan reports only whether saved skill terms literally appear in a pasted JD; it does not evaluate skill depth, transferable experience, or interview likelihood. The evidence profile provides a structured place for candidate-authored claims and support notes, but does not independently verify them. See [EVIDENCE_PROFILE_GUIDE.md](EVIDENCE_PROFILE_GUIDE.md) for the claim structure and [MVP_BUILD_PLAN.md](MVP_BUILD_PLAN.md) for the learning path.

## Technology

- Python 3.10 or newer
- FastAPI for the local web application and form endpoints
- Jinja2 for HTML rendering with autoescaping
- Pydantic for validating structured evidence claims
- SQLite for the local profile and application log
- Uvicorn as the development server
- GitHub Actions for automated syntax and unit checks on pull requests

## Project structure

```text
JobG's/
├── README.md
└── jobgs-engine/
    ├── app.py                 # FastAPI interface and review/confirm flow
    ├── database.py            # SQLite setup, sample profile, daily count
    ├── matcher.py             # Explainable profile-term scan (1.1 baseline)
    ├── evidence_profile.py    # Typed claim model and local evidence storage
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
python -m compileall -q app.py database.py matcher.py evidence_profile.py
```

GitHub Actions runs these checks for pull requests and pushes that change this project.

## Git and release workflow

Use a short-lived branch for each change, then open a pull request into `main`. Review the diff and wait for the **JobG's CI** workflow to pass before merging.

```powershell
git switch -c feature/short-description
git add ".github/workflows/jobgs-engine.yml" "projects/JobG's"
git commit -m "feat(jobgs): describe the change"
git push -u origin feature/short-description
```

After the 1.1 pull request is reviewed, merged into `main`, and CI passes, create the release tag from the updated `main`:

```powershell
git switch main
git pull
git tag -a v1.1.0 -m "JobG's v1.1.0"
git push origin v1.1.0
```

See [CHANGELOG.md](CHANGELOG.md) for the release history and commit notes. AI-assisted semantic matching and evidence-linked resume draft suggestions are future work, subject to human review.
