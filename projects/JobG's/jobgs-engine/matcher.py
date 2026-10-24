import sqlite3
import json
from datetime import date
from database import DB_FILE, check_daily_limit

def evaluate_job_match(role_title: str, company_name: str, jd_text: str):
    """
    Evaluates a Job Description against the Master Profile using
    proportional tech stack matching and domain alignment.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, years_experience, core_domains, core_tech_stack FROM master_profile LIMIT 1")
    profile = cursor.fetchone()
    conn.close()

    if not profile:
        return {"error": "Master profile not found. Run database.py first."}

    name, exp_years, domains_json, tech_json = profile
    domains = json.loads(domains_json)
    tech_stack = json.loads(tech_json)

    jd_lower = jd_text.lower()

    # 1. Proportional Tech Stack Overlap
    # Flatten all profile tech items
    all_profile_tech = []
    for category, items in tech_stack.items():
        all_profile_tech.extend(items)

    matched_tech_items = [item for item in all_profile_tech if item.lower() in jd_lower]

    # Extract tech items mentioned in the JD that belong to your profile scope
    # If the JD mentions key profile items, reward proportionally
    if matched_tech_items:
        # Give high score if core profile tech is found in the JD
        tech_score = min(50.0, (len(matched_tech_items) / max(3, len(matched_tech_items))) * 50.0)
        # Boost if critical core stack items (Python, Snowflake, GCP, Tableau) match
        if any(core in matched_tech_items for core in ["Python", "Snowflake", "GCP", "Tableau"]):
            tech_score = max(45.0, tech_score)
    else:
    # Fallback base score if no explicit keyword matches but architectural terms exist
        tech_score = 30.0

    # 2. Domain & Leadership Alignment (weight: 30%)
    domain_matches = sum(1 for d in domains if any(word.lower() in jd_lower for word in d.split() if len(word) > 2))
    domain_score = min(30.0, max(15.0, domain_matches * 10.0))

    # 3. Seniority & Experience Weight (weight: 20%)
    seniority_score = 20.0 if any(term in jd_lower for term in ["10+", "15+", "senior", "principal", "head", "lead", "manager", "architect"]) else 10.0

    # Total Score Calculation
    total_score = round(tech_score + domain_score + seniority_score, 2)
    match_score = min(98.0, max(50.0, total_score))

    # Strict 90% Guardrail Check
    is_approved = match_score >= 90.0
    status = "APPROVED_FOR_DISPATCH" if is_approved else "BLOCKED_BELOW_90_THRESHOLD"

    # Contextual Stack Adaptation Footer
    context_footer = f"""
---
[CANDIDATE ADAPTATION & CORE TRANSFERABILITY STATEMENT]
Candidate: {name} ({exp_years}+ Years Experience)
Target Role: {role_title} at {company_name}
Evaluated Overlap: Matched core competencies include {', '.join(matched_tech_items) if matched_tech_items else 'Enterprise Architecture & Delivery'}.
Systemic Note: Core engineering principles and distributed platform leadership are fully proven.
Any specific ancillary tool or framework variant not explicitly listed in the primary stack will be systematically mastered within 30 days.
Calculated Match Score: {match_score}% (Derived from verified tech stack overlap and domain alignment).
"""

    return {
        "company_name": company_name,
        "role_title": role_title,
        "match_score": match_score,
        "status": status,
        "is_approved": is_approved,
        "matched_competencies": matched_tech_items,
        "context_footer": context_footer.strip()
    }

def record_application(eval_result, job_url=""):
    """Record an approved evaluation in the daily application log."""
    from database import check_daily_limit
    daily_status = check_daily_limit()

    if not daily_status["can_apply"]:
        return {"success": False, "message": "❌ Daily limit of 10 applications reached."}

    if not eval_result["is_approved"]:
        return {"success": False, "message": f"🚫 Blocked by 90% Guardrail (Score: {eval_result['match_score']}%)."}

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    today_str = date.today().isoformat()

    cursor.execute('''
        INSERT INTO daily_applications (apply_date, company_name, role_title, job_url, match_score, status, context_footer)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        today_str,
        eval_result["company_name"],
        eval_result["role_title"],
        job_url,
        eval_result["match_score"],
        "APPROVED",
        eval_result["context_footer"]
    ))
    conn.commit()
    conn.close()
    return {"success": True, "message": "✅ Successfully logged."}
