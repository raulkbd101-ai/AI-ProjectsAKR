from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from jinja2 import Template
import sqlite3
import uuid
from datetime import date
from database import DB_FILE, check_daily_limit
from matcher import evaluate_job_match

app = FastAPI(title="JobG's - Personal Job Search Assistant")

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
    </style>
</head>
<body>
    <div class="container">
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
async def home(request: Request):
    stats = check_daily_limit()
    template = Template(HTML_TEMPLATE, autoescape=True)
    return HTMLResponse(content=template.render(stats=stats))

@app.post("/evaluate", response_class=HTMLResponse)
async def evaluate(company_name: str = Form(...), role_title: str = Form(...), job_url: str = Form(""), jd_text: str = Form(...)):
    stats = check_daily_limit()

    try:
        result = evaluate_job_match(role_title, company_name, jd_text)
        if "error" in result:
            template = Template(HTML_TEMPLATE, autoescape=True)
            return HTMLResponse(content=template.render(stats=stats, message=f"❌ Error: {result['error']}", company_name=company_name, role_title=role_title, job_url=job_url, jd_text=jd_text))
    except Exception as e:
        template = Template(HTML_TEMPLATE, autoescape=True)
        return HTMLResponse(content=template.render(stats=stats, message=f"❌ System Error: {str(e)}", company_name=company_name, role_title=role_title, job_url=job_url, jd_text=jd_text))

    # Generate secure server-side evaluation token to prevent tampering
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
    stats = check_daily_limit()
    template = Template(HTML_TEMPLATE, autoescape=True)

    # 1. Verify token exists in server memory (prevents payload tampering)
    if evaluation_token not in PENDING_EVALUATIONS:
        return HTMLResponse(content=template.render(stats=stats, message="🚫 Security Error: Invalid or expired evaluation token. Please re-evaluate."))

    eval_res = PENDING_EVALUATIONS.pop(evaluation_token)

    # 2. Atomic Database Transaction (Strict Concurrency & Daily Cap Enforcement)
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
        success_msg = f"✅ Successfully logged securely! Remaining slots today: {9 - count}/10."
    except Exception as e:
        conn.rollback()
        success_msg = f"❌ Database transaction failed: {str(e)}"
    finally:
      conn.close()

    new_stats = check_daily_limit()
    return HTMLResponse(content=template.render(stats=new_stats, message=success_msg))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
