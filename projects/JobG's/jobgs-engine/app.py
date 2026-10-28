from pathlib import Path
import json
import sqlite3
import uuid
from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import Body, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from jinja2 import Environment, FileSystemLoader, Template, select_autoescape
from pydantic import ValidationError

from database import DB_FILE, get_dashboard_analytics
from matcher import evaluate_job_match
from evidence import list_evidence_claims, add_evidence_claim, EvidenceClaim
from job_copilot import JobSubmission, ManagedRagError, add_job, triage_job
from ingest_companies import CompanyRecord, ingest_company_records
from tracker import router as tracker_router

app = FastAPI(title="JobG's - Personal Job Search Assistant")
app.include_router(tracker_router)
TEMPLATE_ENV = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parent / "templates"),
    autoescape=select_autoescape(("html", "xml")),
)

# In-memory secure state store for pending evaluations (Prevents tampering between review and logging)
PENDING_EVALUATIONS = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JobG's - Personal Executive Career Engine</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
        h1 { color: #38bdf8; margin-top: 0; font-size: 24px; }
        .stats-card { display: flex; justify-content: space-between; background: #334155; padding: 15px 20px; border-radius: 8px; margin-bottom: 25px; }
        .stat-item { text-align: center; }
        .stat-num { font-size: 22px; font-weight: bold; color: #38bdf8; }
        form { display: flex; flex-direction: column; gap: 15px; }
        label { font-weight: 600; font-size: 14px; color: #cbd5e1; }
        input, textarea { padding: 12px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; font-size: 14px; }
        textarea { height: 120px; resize: vertical; }
        button { background: #0284c7; color: white; border: none; padding: 14px; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 16px; transition: background 0.2s; }
        button:hover { background: #0369a1; }
        .result-box { margin-top: 25px; background: #0f172a; padding: 20px; border-radius: 8px; border: 1px solid #475569; }
        .success { color: #4ade80; font-weight: bold; }
        .blocked { color: #f87171; font-weight: bold; }
        pre { background: #1e293b; padding: 12px; border-radius: 6px; overflow-x: auto; color: #e2e8f0; font-size: 13px; }
        .msg { margin-top: 20px; padding: 12px; background: #334155; border-radius: 6px; text-align: center; font-weight: bold; }
        .nav-links { display: flex; gap: 10px; margin-bottom: 20px; }
        .nav-links a { display: inline-block; padding: 10px 14px; border-radius: 6px; background: #334155; color: #f8fafc; text-decoration: none; font-weight: bold; }
        .nav-links a[aria-current="page"] { background: #0284c7; }
        .nav-links a:hover { background: #0369a1; }
        .metric-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 18px 0; }
        .metric-card { background: #334155; border: 1px solid #475569; border-radius: 8px; padding: 14px; }
        .metric-label { color: #cbd5e1; font-size: 13px; }
        .metric-value { color: #38bdf8; font-size: 23px; font-weight: 700; }
        .progress-track { height: 12px; overflow: hidden; border-radius: 999px; background: #0f172a; border: 1px solid #475569; }
        .progress-fill { height: 100%; background: #38bdf8; }
        @media (max-width: 650px) { .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
        @media (max-width: 420px) { .metric-grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <nav class="nav-links" aria-label="Main navigation">
            <a href="/" aria-current="page">Dashboard</a>
            <a href="/tracker">Application Tracker</a>
            <a href="/evidence">Evidence Dossier</a>
        </nav>
        <h1>JobG's: Personal Job Search Assistant</h1>
        <p>Local MVP: scan a pasted job description for terms already present in your profile, then review the result yourself.</p>

        <div class="stats-card">
            <div class="stat-item">
                <div>Today's Logged Roles</div>
                <div class="stat-num">{{ stats.today_count }} / 10</div>
            </div>
            <div class="stat-item">
                <div>Remaining Daily Slots</div>
                <div class="stat-num">{{ stats.remaining_slots }}</div>
            </div>
            <div class="stat-item">
                <div>Review Policy</div>
                <div class="stat-num" style="color: #4ade80;">You decide</div>
            </div>
        </div>

        <section class="result-box" aria-labelledby="activity-heading">
            <h2 id="activity-heading">Activity &amp; Daily Cap</h2>
            <div class="metric-grid">
                <div class="metric-card"><div class="metric-label">Roles logged today</div><div class="metric-value">{{ stats.today_count }} / {{ stats.daily_cap }}</div></div>
                <div class="metric-card"><div class="metric-label">Daily slots remaining</div><div class="metric-value">{{ stats.remaining_slots }}</div></div>
                <div class="metric-card"><div class="metric-label">Total tracked roles</div><div class="metric-value">{{ stats.total_tracked_roles }}</div></div>
                <div class="metric-card"><div class="metric-label">Active outreach drafts</div><div class="metric-value">{{ stats.active_outreach_drafts }}</div></div>
                <div class="metric-card"><div class="metric-label">Applied</div><div class="metric-value">{{ stats.status_breakdown.applied }}</div></div>
                <div class="metric-card"><div class="metric-label">Interviewing</div><div class="metric-value">{{ stats.status_breakdown.interviewing }}</div></div>
            </div>
            <p class="metric-label">Daily cap usage: {{ stats.daily_progress_percent }}%</p>
            <div class="progress-track" role="progressbar" aria-label="Roles logged toward today's cap" aria-valuemin="0" aria-valuemax="{{ stats.daily_cap }}" aria-valuenow="{{ stats.today_count }}">
                <div class="progress-fill" style="width: {{ stats.daily_progress_percent }}%;"></div>
            </div>
            <p class="metric-label">Current status snapshot — Discovered: {{ stats.status_breakdown.discovered }} · Reviewed: {{ stats.status_breakdown.reviewed }} · Applied: {{ stats.status_breakdown.applied }} · Interview: {{ stats.status_breakdown.interviewing }} · Offers: {{ stats.status_breakdown.offers }} · Closed: {{ stats.status_breakdown.closed }}</p>
            <p class="metric-label">Snapshot ratios (not historical funnel conversion): Applied / tracked {{ stats.applied_share_percent }}% · Interview / applied {{ stats.interview_to_applied_percent }}% · Offer / applied {{ stats.offer_to_applied_percent }}%.</p>
        </section>

        <form action="/evaluate" method="post">
            <label>Company Name:</label>
            <input type="text" name="company_name" value="{{ company_name | default('') }}" placeholder="e.g. Global Tech GCC Pune" required>

            <label>Role / Title:</label>
            <input type="text" name="role_title" value="{{ role_title | default('') }}" placeholder="e.g. BI Platform Delivery Manager" required>

            <label>Job URL (Optional):</label>
            <input type="url" name="job_url" value="{{ job_url | default('') }}" placeholder="https://company.com/careers/job-123">

            <label>Job Description (Paste JD text here):</label>
            <textarea name="jd_text" placeholder="Paste requirements here..." required>{{ jd_text | default('') }}</textarea>

            <button type="submit">Scan profile evidence in this JD</button>
        </form>

        {% if result %}
        <div class="result-box">
            <h3>Evaluation Result</h3>
            <p><strong>Company:</strong> {{ result.company_name }} | <strong>Role:</strong> {{ result.role_title }}</p>
            <p><strong>Profile skill terms found in the JD:</strong> {{ result.profile_coverage }}% of the skills listed in your saved profile.</p>
            <p>This is a literal keyword scan. It is not a job-fit score, a measure of your proficiency, or a prediction of hiring success.</p>
            <p><strong>Found:</strong> {{ result.matched_competencies | join(', ') if result.matched_competencies else 'No listed skills found' }}</p>
            <p><strong>Not mentioned:</strong> {{ result.missing_profile_skills | join(', ') if result.missing_profile_skills else 'All listed skills were mentioned' }}</p>
            <p><strong>Profile domains explicitly mentioned:</strong> {{ result.matched_domains | join(', ') if result.matched_domains else 'None' }}</p>

            {% if result.transferable_bridges %}
            <h4>Transferable technology bridge drafts — review before reuse</h4>
            <p>These describe adjacent experience only; they do not claim hands-on use of the target technology.</p>
            {% for bridge in result.transferable_bridges %}
            <div class="result-box">
                <p><strong>{{ bridge.source_technology }} → {{ bridge.target_technology }}</strong> (based on: {{ bridge.supporting_competency }})</p>
                <p><strong>Saved evidence claim:</strong> {{ bridge.supporting_claim }}</p>
                <p>{{ bridge.statement }}</p>
            </div>
            {% endfor %}
            {% endif %}

            <label>Review notes:</label>
            <pre>{{ result.context_footer }}</pre>

            {% if stats.can_apply %}
            <form action="/confirm-log" method="post" style="margin-top: 15px;">
                <input type="hidden" name="evaluation_token" value="{{ evaluation_token }}">
                <button type="submit" style="background: #16a34a;">I reviewed this role — log it</button>
            </form>
            {% endif %}
        </div>
        {% endif %}

        {% if message %}
        <div class="msg">{{ message }}</div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    stats = get_dashboard_analytics()
    template = Template(HTML_TEMPLATE, autoescape=True)
    return HTMLResponse(content=template.render(stats=stats))

@app.post("/evaluate", response_class=HTMLResponse)
async def evaluate(company_name: str = Form(...), role_title: str = Form(...), job_url: str = Form(""), jd_text: str = Form(...)):
    stats = get_dashboard_analytics()

    try:
        result = evaluate_job_match(role_title, company_name, jd_text)
        if "error" in result:
            template = Template(HTML_TEMPLATE, autoescape=True)
            return HTMLResponse(content=template.render(stats=stats, message=f"❌ Error: {result['error']}", company_name=company_name, role_title=role_title, job_url=job_url, jd_text=jd_text))
    except Exception as e:
        template = Template(HTML_TEMPLATE, autoescape=True)
        return HTMLResponse(content=template.render(stats=stats, message=f"❌ System Error: {str(e)}", company_name=company_name, role_title=role_title, job_url=job_url, jd_text=jd_text))

    eval_token = str(uuid.uuid4())
    PENDING_EVALUATIONS[eval_token] = {
        "company_name": company_name,
        "role_title": role_title,
        "job_url": job_url,
        "profile_coverage": result["profile_coverage"],
        "context_footer": result["context_footer"],
        "matched_competencies": result.get("matched_competencies", []),
        "missing_profile_skills": result.get("missing_profile_skills", []),
        "matched_domains": result.get("matched_domains", []),
        "status": result["status"],
        "evaluation_method": result["evaluation_method"],
    }

    template = Template(HTML_TEMPLATE, autoescape=True)
    return HTMLResponse(content=template.render(
        stats=stats,
        result=result,
        company_name=company_name,
        role_title=role_title,
        job_url=job_url,
        jd_text=jd_text,
        evaluation_token=eval_token
    ))

@app.post("/confirm-log", response_class=HTMLResponse)
async def confirm_log(evaluation_token: str = Form(...)):
    stats = get_dashboard_analytics()
    template = Template(HTML_TEMPLATE, autoescape=True)

    if evaluation_token not in PENDING_EVALUATIONS:
        return HTMLResponse(content=template.render(stats=stats, message="🚫 Security Error: Invalid or expired evaluation token. Please re-evaluate."))

    eval_res = PENDING_EVALUATIONS.pop(evaluation_token)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    today_str = date.today().isoformat()

    try:
        cursor.execute("BEGIN EXCLUSIVE;")

        cursor.execute("SELECT COUNT(*) FROM daily_applications WHERE apply_date = ?", (today_str,))
        count = cursor.fetchone()[0]

        if count >= 10:
            conn.rollback()
            conn.close()
            return HTMLResponse(content=template.render(stats=stats, message="❌ Daily limit of 10 applications reached. Protect your energy!"))

        cursor.execute('''
            INSERT INTO daily_applications (apply_date, company_name, role_title, job_url, match_score, status, context_footer)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            today_str,
            eval_res["company_name"],
            eval_res["role_title"],
            eval_res["job_url"],
            eval_res["profile_coverage"],
            "USER_REVIEWED",
            eval_res["context_footer"]
        ))
        conn.commit()

        remaining_after = max(0, 9 - count)
        success_msg = f"✅ Successfully logged securely! Remaining slots today: {remaining_after}/10."
    except Exception as e:
        conn.rollback()
        success_msg = f"❌ Database transaction failed: {str(e)}"
    finally:
        conn.close()

    new_stats = get_dashboard_analytics()
    return HTMLResponse(content=template.render(stats=new_stats, message=success_msg))


# --- EVIDENCE DOSSIER ROUTES ---

@app.get("/evidence", response_class=HTMLResponse)
def get_evidence_dossier(request: Request):
    error_messages = {
        "invalid_claim": "Please check the claim fields and choose a supported status and confidentiality value.",
        "save_failed": "The claim could not be saved. Confirm the local database has been initialized, then try again.",
        "database_unavailable": "The evidence database is unavailable. Run database.py from the jobgs-engine folder first.",
    }
    error = error_messages.get(request.query_params.get("error"))
    try:
        claims = list_evidence_claims()
    except sqlite3.Error:
        claims = []
        error = error_messages["database_unavailable"]

    evidence_template = TEMPLATE_ENV.get_template("evidence.html")
    return HTMLResponse(content=evidence_template.render(claims=claims, error=error))

@app.post("/evidence/add", response_class=HTMLResponse)
def post_evidence_claim(
    competency: str = Form(...),
    claim: str = Form(...),
    context: str = Form(""),
    evidence_summary: str = Form(...),
    impact_metric: str = Form(""),
    source_reference: str = Form(""),
    evidence_status: str = Form("self_reported"),
    confidentiality: str = Form("private"),
    target_persona: str = Form("All"),
):
    try:
        new_claim = EvidenceClaim(
            competency=competency,
            claim=claim,
            context=context,
            evidence_summary=evidence_summary,
            impact_metric=impact_metric,
            source_reference=source_reference,
            evidence_status=evidence_status,
            confidentiality=confidentiality,
            target_persona=target_persona,
        )
        add_evidence_claim(new_claim)
        return RedirectResponse(url="/evidence", status_code=303)
    except ValidationError:
        return RedirectResponse(url="/evidence?error=invalid_claim", status_code=303)
    except (sqlite3.Error, ValueError):
        return RedirectResponse(url="/evidence?error=save_failed", status_code=303)


# --- WEEK 2 EXECUTIVE DECISION CO-PILOT API ---

@app.post("/api/triage-job")
def api_triage_job(job: JobSubmission):
    """Analyze a user-supplied role without saving it or submitting an application."""
    try:
        return triage_job(job)
    except ManagedRagError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (sqlite3.Error, OSError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Local job/evidence data could not be read. Confirm the database is initialized.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/add-job")
def api_add_job(job: JobSubmission):
    """Triage and save a discovered job for human review; does not apply or message."""
    try:
        return add_job(job)
    except ManagedRagError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="The job could not be saved because it conflicts with an existing record.",
        ) from exc
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="The local database is unavailable. Confirm it is initialized and writable.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/ingest-companies")
def api_ingest_companies(
    companies: Annotated[
        list[CompanyRecord],
        Body(min_length=1, max_length=250),
    ],
):
    """Bulk-upsert company records; this does not submit applications or messages."""
    try:
        count = ingest_company_records(companies)
        return {
            "success": True,
            "records_upserted": count,
            "message": f"Processed {count} company record(s).",
        }
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="The local company inventory database is unavailable.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
