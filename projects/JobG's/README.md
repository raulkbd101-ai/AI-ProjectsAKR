# JobG's — Personal Job Search Engine

**Version:** 1.0.0

**Status:** Local, single-user MVP

JobG's is a local job-search workflow sandbox. It helps a candidate compare a manually supplied job description with a locally stored profile, review a match summary, and log approved opportunities. It is designed to make the review process deliberate and to track a daily limit of 10 logged entries.

## Product context

Version 1.0 establishes the first governed workflow:

1. Enter a company, role, optional job URL, and job description.
2. Compare the description with the candidate profile using transparent, rule-based keyword heuristics.
3. Review the score, matched competencies, and generated context statement.
4. Confirm and log an approved opportunity, subject to the daily cap.

The candidate remains in control. JobG's does **not** search or scrape career sites, call an AI model, rewrite a resume, or submit applications to employers. The score is a prototype heuristic, not a calibrated probability or a prediction of ATS outcomes. Review each result and generated statement for accuracy before using it.

## Technology

- Python 3.10 or newer
- FastAPI for the local web application and form endpoints
- Jinja2 for HTML rendering with autoescaping
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
    ├── matcher.py             # Rule-based job/profile matching
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
python -m compileall -q app.py database.py matcher.py
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

After the v1.0 pull request is merged, create the release tag from `main`:

```powershell
git switch main
git pull
git tag -a v1.0.0 -m "JobG's v1.0.0"
git push origin v1.0.0
```

See [CHANGELOG.md](CHANGELOG.md) for the v1.0 release notes and commit summary. Version 1.1 is planned for AI-assisted semantic matching and evidence-based resume draft suggestions, always subject to human review.
