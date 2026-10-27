import json
import re
import sqlite3
from datetime import date
from contextlib import closing

from database import DB_FILE, check_daily_limit


def evaluate_job_match(role_title: str, company_name: str, jd_text: str):
    """Find profile terms explicitly mentioned in a job description.

    This is a transparent lexical baseline, not an AI judgment or a measure
    of the candidate's probability of getting an interview.
    """
    with closing(sqlite3.connect(DB_FILE)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT full_name, years_experience, core_domains, core_tech_stack "
            "FROM master_profile LIMIT 1"
        )
        profile = cursor.fetchone()

    if not profile:
        return {"error": "Master profile not found. Run database.py first."}

    name, exp_years, domains_json, tech_json = profile
    domains = json.loads(domains_json or "[]")
    tech_stack = json.loads(tech_json or "{}")
    jd_lower = jd_text.casefold()

    def phrase_present(phrase: str) -> bool:
        # Match whole terms so, for example, "R" does not match "manager".
        escaped = re.escape(phrase.strip())
        return bool(escaped) and re.search(rf"(?<!\w){escaped}(?!\w)", jd_lower, re.IGNORECASE) is not None

    profile_skills = list(dict.fromkeys(
        skill
        for items in tech_stack.values()
        if isinstance(items, list)
        for skill in items
        if isinstance(skill, str) and skill.strip()
    ))
    matched_skills = [skill for skill in profile_skills if phrase_present(skill)]
    missing_skills = [skill for skill in profile_skills if skill not in matched_skills]
    matched_domains = [domain for domain in domains if isinstance(domain, str) and phrase_present(domain)]

    # This measures only how many known profile terms appear in the JD.
    # It is deliberately not called a job-fit or success-probability score.
    coverage = round(100 * len(matched_skills) / len(profile_skills), 1) if profile_skills else 0.0
    context_summary = (
        f"Profile evidence found in JD: {', '.join(matched_skills) if matched_skills else 'No listed technical skills found'}.\n"
        f"Profile skills not mentioned in JD: {', '.join(missing_skills) if missing_skills else 'None'}.\n"
        f"Profile domains explicitly mentioned: {', '.join(matched_domains) if matched_domains else 'None'}.\n"
        "This keyword scan does not assess skill depth, transferable experience, or hiring likelihood. "
        "Review the JD and your evidence before deciding whether to apply."
    )

    return {
        "company_name": company_name,
        "role_title": role_title,
        "profile_coverage": coverage,
        "status": "HUMAN_REVIEW_REQUIRED",
        "matched_competencies": matched_skills,
        "missing_profile_skills": missing_skills,
        "matched_domains": matched_domains,
        "context_footer": context_summary,
        "candidate_name": name,
        "years_experience": exp_years,
        "evaluation_method": "profile_term_scan",
    }


def record_application(eval_result, job_url=""):
    """Log a role the user has chosen to review, subject to the daily cap."""
    daily_status = check_daily_limit()
    if not daily_status["can_apply"]:
        return {"success": False, "message": "❌ Daily limit of 10 logged roles reached."}

    if "error" in eval_result:
        return {"success": False, "message": eval_result["error"]}

    with closing(sqlite3.connect(DB_FILE)) as conn:
        with conn:
            conn.execute(
                """INSERT INTO daily_applications
                   (apply_date, company_name, role_title, job_url, match_score, status, context_footer)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    date.today().isoformat(),
                    eval_result["company_name"],
                    eval_result["role_title"],
                    job_url,
                    eval_result["profile_coverage"],
                    "USER_REVIEWED",
                    eval_result["context_footer"],
                ),
            )

    new_status = check_daily_limit()
    return {
        "success": True,
        "message": f"✅ Role logged for your review. Remaining daily slots: {new_status['remaining_slots']}/10.",
    }
