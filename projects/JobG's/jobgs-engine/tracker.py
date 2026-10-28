"""Week 4 local tracker views, guarded lifecycle updates, and offline exports."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape

import database

router = APIRouter()
TEMPLATE_ENV = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parent / "templates"),
    autoescape=select_autoescape(("html", "xml")),
)

STATUSES = (
    "DISCOVERED", "USER_REVIEWED", "APPLIED", "INTERVIEWING", "OFFER",
    "REJECTED", "WITHDRAWN", "ARCHIVED",
)
PERSONAS = ("Director", "Architect", "TPM", "Unclear")
DOMAINS = ("Fintech", "Banking", "Data/AI", "Startups")
SORTS = {
    "newest": "created_at DESC, id DESC",
    "rag_desc": "best_rag_relevance DESC, created_at DESC",
    "coverage_desc": "profile_coverage DESC, created_at DESC",
    "company_asc": "company_name COLLATE NOCASE ASC, created_at DESC",
}
TRANSITIONS = {
    "DISCOVERED": {"USER_REVIEWED", "REJECTED", "WITHDRAWN", "ARCHIVED"},
    "USER_REVIEWED": {"APPLIED", "REJECTED", "WITHDRAWN", "ARCHIVED"},
    "APPLIED": {"INTERVIEWING", "OFFER", "REJECTED", "WITHDRAWN", "ARCHIVED"},
    "INTERVIEWING": {"OFFER", "REJECTED", "WITHDRAWN", "ARCHIVED"},
    "OFFER": {"WITHDRAWN", "ARCHIVED"},
    "REJECTED": {"ARCHIVED"},
    "WITHDRAWN": {"ARCHIVED"},
    "ARCHIVED": set(),
}


def _numeric_filter(request: Request, name: str, maximum: float):
    raw = request.query_params.get(name, "").strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{name} must be numeric.") from exc
    if not 0 <= value <= maximum:
        raise HTTPException(status_code=400, detail=f"{name} must be between 0 and {maximum:g}.")
    return value


@router.get("/tracker", response_class=HTMLResponse)
def tracker_page(request: Request):
    persona = request.query_params.get("persona", "").strip()
    domain = request.query_params.get("domain", "").strip()
    status = request.query_params.get("status", "").strip()
    sort = request.query_params.get("sort", "newest").strip()
    keyword = request.query_params.get("q", "").strip()[:160]
    if persona and persona not in PERSONAS:
        raise HTTPException(status_code=400, detail="Unsupported persona filter.")
    if domain and domain not in DOMAINS:
        raise HTTPException(status_code=400, detail="Unsupported domain filter.")
    if status and status not in STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported status filter.")
    if sort not in SORTS:
        raise HTTPException(status_code=400, detail="Unsupported sort option.")

    min_coverage = _numeric_filter(request, "min_coverage", 100)
    max_coverage = _numeric_filter(request, "max_coverage", 100)
    min_relevance = _numeric_filter(request, "min_relevance", 1)
    max_relevance = _numeric_filter(request, "max_relevance", 1)
    if min_coverage is not None and max_coverage is not None and min_coverage > max_coverage:
        raise HTTPException(status_code=400, detail="Minimum coverage cannot exceed maximum coverage.")
    if min_relevance is not None and max_relevance is not None and min_relevance > max_relevance:
        raise HTTPException(status_code=400, detail="Minimum RAG relevance cannot exceed maximum relevance.")

    clauses = ["1 = 1"]
    params: list[object] = []
    for column, value in (("assigned_persona", persona), ("status", status)):
        if value:
            clauses.append(f"{column} = ?")
            params.append(value)
    if domain:
        clauses.append("""
            EXISTS (
                SELECT 1 FROM json_each(
                    CASE WHEN json_valid(t.domain_tags_json) THEN t.domain_tags_json ELSE '[]' END
                ) AS tag WHERE tag.value = ?
            )
        """)
        params.append(domain)
    if keyword:
        clauses.append("(company_name LIKE ? OR role_title LIKE ? OR location LIKE ?)")
        like = f"%{keyword}%"
        params.extend((like, like, like))
    for expression, value in (
        ("profile_coverage >= ?", min_coverage), ("profile_coverage <= ?", max_coverage),
        ("best_rag_relevance >= ?", min_relevance), ("best_rag_relevance <= ?", max_relevance),
    ):
        if value is not None:
            clauses.append(expression)
            params.append(value)

    sql = f"""
        WITH scored AS (
            SELECT t.*,
                (SELECT MAX(CAST(json_extract(m.value, '$.retrieval_score') AS REAL))
                 FROM json_each(
                    CASE WHEN json_valid(t.rag_results_json) THEN t.rag_results_json ELSE '{{}}' END,
                    '$.matches'
                 ) AS m) AS best_rag_relevance
            FROM application_tracker AS t
        )
        SELECT * FROM scored AS t WHERE {' AND '.join(clauses)}
        ORDER BY {SORTS[sort]}
    """
    conn = sqlite3.connect(database.DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        roles = [dict(row) for row in conn.execute(sql, params).fetchall()]
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Tracker data is unavailable. Initialize the database first.") from exc
    finally:
        conn.close()

    for role in roles:
        try:
            tags = json.loads(role.get("domain_tags_json") or "[]")
            role["domain_tags"] = tags if isinstance(tags, list) else []
        except (TypeError, json.JSONDecodeError):
            role["domain_tags"] = []

    return HTMLResponse(content=TEMPLATE_ENV.get_template("tracker.html").render(
        roles=roles, personas=PERSONAS, domains=DOMAINS, statuses=STATUSES,
        transitions=TRANSITIONS,
        selected_persona=persona, selected_domain=domain, selected_status=status,
        selected_sort=sort, keyword=keyword,
        min_coverage="" if min_coverage is None else min_coverage,
        max_coverage="" if max_coverage is None else max_coverage,
        min_relevance="" if min_relevance is None else min_relevance,
        max_relevance="" if max_relevance is None else max_relevance,
        notice=request.query_params.get("notice", ""),
    ))


@router.post("/tracker/{tracking_id}/status")
def update_tracker_status(tracking_id: int, status: str = Form(...)):
    """Apply an explicitly permitted human lifecycle transition."""
    if status not in STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported lifecycle status.")
    conn = sqlite3.connect(database.DB_FILE, timeout=10)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT status FROM application_tracker WHERE id = ?", (tracking_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Tracked role not found.")
        current = row[0]
        if status not in TRANSITIONS.get(current, set()):
            raise HTTPException(status_code=409, detail=f"Transition from {current} to {status} is not allowed.")
        reviewed_at = datetime.now(timezone.utc).isoformat() if status == "USER_REVIEWED" else None
        conn.execute(
            "UPDATE application_tracker SET status = ?, human_reviewed_at = COALESCE(?, human_reviewed_at), updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, reviewed_at, tracking_id),
        )
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.Error as exc:
        conn.rollback()
        raise HTTPException(status_code=503, detail="Could not update tracker status.") from exc
    finally:
        conn.close()
    return RedirectResponse(url="/tracker?notice=Status+updated", status_code=303)


def _safe_json(value, fallback):
    try:
        return json.loads(value) if value else fallback
    except (TypeError, json.JSONDecodeError):
        return fallback


def _md(value):
    return str(value or "").replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace("\n", " ")


@router.get("/export/applications")
def export_applications(format: str = "markdown"):
    """Download tracked roles and their saved evidence/outreach for offline review."""
    if format not in {"markdown", "json"}:
        raise HTTPException(status_code=400, detail="format must be 'markdown' or 'json'.")
    conn = sqlite3.connect(database.DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
            SELECT id, company_name, role_title, job_url, location, work_model,
                   assigned_persona, domain_tags_json, status, raw_description,
                   rag_results_json, transferable_bridges_json, outreach_draft,
                   profile_coverage, created_at, updated_at
            FROM application_tracker ORDER BY created_at DESC, id DESC
        """).fetchall()
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Could not read application tracker.") from exc
    finally:
        conn.close()

    roles = []
    for row in rows:
        rag = _safe_json(row["rag_results_json"], {})
        matches = rag.get("matches", []) if isinstance(rag, dict) else []
        safe_matches = []
        for match in matches if isinstance(matches, list) else []:
            if not isinstance(match, dict):
                continue
            if str(match.get("confidentiality", "")).casefold() == "confidential":
                safe_matches.append({"evidence_id": match.get("evidence_id"), "competency": match.get("competency"), "redacted": True})
            else:
                safe_matches.append(match)
        roles.append({
            "tracking_id": row["id"], "company_name": row["company_name"],
            "role_title": row["role_title"], "job_url": row["job_url"],
            "location": row["location"], "work_model": row["work_model"],
            "assigned_persona": row["assigned_persona"],
            "domain_tags": _safe_json(row["domain_tags_json"], []), "status": row["status"],
            "profile_coverage": row["profile_coverage"], "created_at": row["created_at"],
            "updated_at": row["updated_at"], "job_description": row["raw_description"],
            "evidence_retrieval": {
                "retrieval_mode": rag.get("retrieval_mode") if isinstance(rag, dict) else None,
                "model_name": rag.get("model_name") if isinstance(rag, dict) else None,
                "matches": safe_matches,
                "score_notice": rag.get("score_notice") if isinstance(rag, dict) else None,
            },
            "transferable_bridges": _safe_json(row["transferable_bridges_json"], []),
            "outreach_draft": row["outreach_draft"],
        })

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if format == "json":
        body = json.dumps({"exported_at_utc": datetime.now(timezone.utc).isoformat(), "record_count": len(roles), "roles": roles}, indent=2, ensure_ascii=False)
        return Response(content=body, media_type="application/json; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="jobgs-applications-{stamp}.json"'})

    lines = ["# JobG's — Offline Application Review", "", f"Exported at (UTC): {datetime.now(timezone.utc).isoformat()}", f"Roles included: {len(roles)}", "", "> Evidence retrieval relevance is not a job-fit, proficiency, or hiring-probability score. Outreach drafts have not been sent.", ""]
    for role in roles:
        lines += [f"## {_md(role['company_name'])} — {_md(role['role_title'])}", "", f"- Status: {_md(role['status'])}", f"- Persona: {_md(role['assigned_persona'])}", f"- Location / work model: {_md(role['location'])} / {_md(role['work_model'])}", f"- Job URL: {_md(role['job_url'])}", f"- Domain tags: {_md(', '.join(role['domain_tags']) if isinstance(role['domain_tags'], list) else '')}", f"- Profile keyword coverage: {_md(role['profile_coverage'])}%", "", "### Matched evidence", ""]
        matches = role["evidence_retrieval"]["matches"]
        if not matches:
            lines.append("_No evidence matches saved._")
        for match in matches:
            if match.get("redacted"):
                lines.append(f"- **{_md(match.get('competency'))}:** confidential claim omitted")
            else:
                lines.append(f"- **{_md(match.get('competency'))}:** {_md(match.get('claim'))} (source: {_md(match.get('source_reference'))})")
        lines += ["", "### Transferable bridge drafts", ""]
        bridges = role["transferable_bridges"]
        if isinstance(bridges, list) and bridges:
            for bridge in bridges:
                lines.append(f"- {_md(bridge.get('statement', bridge) if isinstance(bridge, dict) else bridge)}")
        else:
            lines.append("_No bridge drafts saved._")
        lines += ["", "### Outreach draft", "", _md(role["outreach_draft"]) or "_No outreach draft saved._", "", "### Job description", "", _md(role["job_description"]), "", "---", ""]
    return Response(content="\n".join(lines), media_type="text/markdown; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="jobgs-applications-{stamp}.md"'})
