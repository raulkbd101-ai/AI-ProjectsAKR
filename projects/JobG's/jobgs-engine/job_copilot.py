"""Human-governed Week 2 intake and triage for JobG's.

This module classifies supplied job information with transparent rules, retrieves
local evidence, drafts (but never sends) outreach, and records discovered roles.
It does not scrape pages, submit applications, or make hiring/fit decisions.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import shutil
import subprocess
import threading
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import database
import matcher
import rag_matcher
from pydantic import BaseModel, ConfigDict, Field, field_validator


PERSONAS = ("Director", "Architect", "TPM")
ROLE_SIGNALS = {
    "Director": (
        "director", "senior director", "head of", "vice president", "vp",
        "executive director", "organizational leadership", "engineering leader",
    ),
    "Architect": (
        "architect", "architecture", "solution design", "platform design",
        "technical direction", "target state",
    ),
    "TPM": (
        "technical program manager", "principal tpm", "tpm", "program manager",
        "delivery manager", "program delivery", "project delivery",
        "engineering manager",
    ),
}
DOMAIN_SIGNALS = {
    "Fintech": ("fintech", "financial technology", "payments", "digital banking"),
    "Banking": ("bank", "banking", "financial institution", "model risk"),
    "Data/AI": ("data", "analytics", "artificial intelligence", " ai ", "machine learning", "agentic"),
    "Startups": ("startup", "start-up", "scale-up", "venture-backed"),
}
PUNE_AREAS = ("pune", "balewadi", "baner", "hinjewadi", "aundh")
MAX_RAG_QUERY_CHARS = 8_000
_RAG_SESSION_LOCK = threading.Lock()


class ManagedRagError(RuntimeError):
    """Raised when the managed Ollama session cannot return hybrid results."""


class JobSubmission(BaseModel):
    """Validated job and optional company facts supplied by the user."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    company_name: str = Field(min_length=2, max_length=160)
    role_title: str = Field(min_length=2, max_length=200)
    job_url: str = Field(min_length=10, max_length=2048)
    raw_description: str = Field(min_length=20, max_length=50_000)
    location: str = Field(default="", max_length=240)
    company_domain: str = Field(default="", max_length=253)
    company_hq: str = Field(default="", max_length=240)
    company_vertical: str = Field(default="", max_length=120)
    company_size: str = Field(default="", max_length=120)
    company_tech_stack: list[str] = Field(default_factory=list, max_length=100)
    careers_url: str = Field(default="", max_length=2048)

    @field_validator("job_url", "careers_url")
    @classmethod
    def validate_web_url(cls, value: str, info):
        if not value and info.field_name == "careers_url":
            return value
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("URL must be an absolute http or https address.")
        return value

    @field_validator("company_tech_stack")
    @classmethod
    def clean_tech_stack(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value and value.strip()]
        if any(len(value) > 100 for value in cleaned):
            raise ValueError("Each technology name must be 100 characters or fewer.")
        return list(dict.fromkeys(cleaned))


def _persona_triage(role_title: str, raw_description: str) -> dict:
    """Return explainable role-title/JD signal counts, never a fit decision."""
    title = role_title.casefold()
    text = f"{role_title}\n{raw_description}".casefold()
    scores = {}
    reasons = {}
    for persona, signals in ROLE_SIGNALS.items():
        title_hits = [signal for signal in signals if _has_phrase(title, signal)]
        jd_hits = [signal for signal in signals if _has_phrase(text, signal) and signal not in title_hits]
        scores[persona] = len(title_hits) * 3 + len(jd_hits)
        reasons[persona] = {"title_signals": title_hits, "description_signals": jd_hits}

    highest = max(scores.values(), default=0)
    winners = [persona for persona, score in scores.items() if score == highest and score > 0]
    selected = winners[0] if len(winners) == 1 else "Unclear"
    return {
        "assigned_persona": selected,
        "persona_confidence": "needs_human_review" if selected == "Unclear" else "rule_based_suggestion",
        "persona_scores": scores,
        "persona_reasons": reasons,
    }


def _has_phrase(text: str, phrase: str) -> bool:
    """Find a phrase on word boundaries to avoid matches inside larger words."""
    return re.search(rf"(?<!\w){re.escape(phrase.strip())}(?!\w)", text, re.IGNORECASE) is not None


def _domain_triage(company_vertical: str, role_title: str, raw_description: str) -> list[str]:
    text = f" {company_vertical} {role_title} {raw_description} ".casefold()
    tags = [
        domain for domain, signals in DOMAIN_SIGNALS.items()
        if any(_has_phrase(text, signal) for signal in signals)
    ]
    if company_vertical.strip() and not tags:
        tags.append(company_vertical.strip()[:120])
    return tags or ["Unclassified"]


def _location_triage(location: str) -> dict:
    """Classify only the location supplied by the user; don't infer from JD text."""
    value = location.casefold().strip()
    if not value:
        return {"status": "unknown", "work_model": "Unknown", "reason": "No location was supplied."}

    is_remote = any(term in value for term in ("remote", "work from anywhere", "distributed"))
    is_hybrid = "hybrid" in value
    is_onsite = any(term in value for term in ("on-site", "onsite", "on site", "office-based"))
    work_model = "Remote" if is_remote else "Hybrid" if is_hybrid else "On-site" if is_onsite else "Unknown"
    is_pune = any(_has_phrase(value, area) for area in PUNE_AREAS)
    is_india = any(term in value for term in ("india", "pune", "maharashtra"))
    mentions_overseas = any(
        _has_phrase(value, term)
        for term in ("overseas", "global", "worldwide", "uk", "united kingdom", "europe", "uae", "dubai", "us", "usa", "canada", "australia")
    )

    if is_pune:
        return {"status": "preferred", "work_model": work_model, "reason": "Pune or a named preferred Pune area is listed."}
    if is_remote and is_india:
        return {"status": "preferred", "work_model": "Remote", "reason": "Remote work in India is listed."}
    if is_remote and mentions_overseas:
        return {"status": "preferred", "work_model": "Remote", "reason": "Remote work outside India or globally is listed."}
    if is_remote:
        return {"status": "needs_review", "work_model": "Remote", "reason": "Remote is listed, but the eligible country/region is unspecified."}
    if is_hybrid or is_onsite:
        return {"status": "outside_preferences", "work_model": work_model, "reason": "The supplied location is not a preferred Pune area or remote role."}
    return {"status": "needs_review", "work_model": "Unknown", "reason": "Location text could not be confidently classified."}


def _outreach_draft(company_name: str, role_title: str, rag_result: dict) -> str:
    matches = rag_result.get("matches") or []
    competencies = list(dict.fromkeys(
        match.get("competency", "").strip()
        for match in matches
        if match.get("competency", "").strip()
    ))[:2]
    if competencies:
        evidence_phrase = " and ".join(competencies)
        second_sentence = (
            f"My profile includes candidate-provided evidence related to {evidence_phrase}, "
            "which I would be glad to discuss against the team's priorities."
        )
    else:
        second_sentence = (
            "I would welcome the opportunity to discuss the role's priorities and share "
            "relevant examples from my background."
        )
    return (
        f"Hello, I am interested in the {role_title} opportunity at {company_name}. "
        f"{second_sentence} "
        "Would you be open to a brief conversation or able to direct me to the appropriate hiring contact?"
    )


def _rag_query(role_title: str, raw_description: str) -> str:
    text = f"{role_title}\n{raw_description}"
    if len(text) <= MAX_RAG_QUERY_CHARS:
        return text
    return text[:6_000] + "\n[description middle omitted for local embedding query]\n" + text[-2_000:]


def _search_with_managed_ollama(query: str, persona: str) -> dict:
    """Run the matcher through the lifecycle wrapper and require hybrid results.

    The lock prevents concurrent requests in this local single-process server
    from stopping or replacing each other's Ollama session.
    """
    powershell = shutil.which("pwsh") or shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell:
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        fallback = Path(system_root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        if fallback.is_file():
            powershell = str(fallback)
    if not powershell:
        raise ManagedRagError("PowerShell was not found; the managed Ollama session cannot start.")

    wrapper = Path(__file__).resolve().parent / "run_rag_session.ps1"
    if not wrapper.is_file():
        raise ManagedRagError(f"Ollama lifecycle wrapper is missing: {wrapper.name}")

    persona_arg = persona if persona in PERSONAS else "All"
    command = [
        powershell,
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(wrapper),
        "-Query",
        query,
        "-Persona",
        persona_arg,
        "-JsonOnly",
    ]

    with _RAG_SESSION_LOCK:
        try:
            completed = subprocess.run(
                command,
                cwd=Path(__file__).resolve().parent,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            # A killed parent shell may not execute its own finally block, so
            # make a best-effort cleanup-only wrapper call before reporting.
            cleanup_command = [
                powershell,
                "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                "-File", str(wrapper), "-CleanupOnly", "-JsonOnly",
            ]
            try:
                subprocess.run(
                    cleanup_command,
                    cwd=Path(__file__).resolve().parent,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                pass
            raise ManagedRagError("Managed Ollama retrieval timed out; cleanup recovery was attempted.") from exc
        except OSError as exc:
            raise ManagedRagError(f"Could not launch the Ollama lifecycle wrapper: {exc}") from exc

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "No wrapper diagnostic was returned.").strip()
        raise ManagedRagError(f"Managed Ollama session failed: {detail[-1200:]}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ManagedRagError("Lifecycle wrapper did not return valid matcher JSON.") from exc

    if result.get("retrieval_mode") != "hybrid":
        raise ManagedRagError(
            "Hybrid retrieval is required for this API workflow; the local model did not return hybrid results."
        )
    if result.get("model_name") != rag_matcher.DEFAULT_EMBEDDING_MODEL:
        raise ManagedRagError("Hybrid retrieval returned an unexpected embedding model.")
    return result


def triage_job(job: JobSubmission) -> dict:
    """Analyze a supplied vacancy and return a human-reviewable result."""
    persona = _persona_triage(job.role_title, job.raw_description)
    location = _location_triage(job.location)
    domains = _domain_triage(job.company_vertical, job.role_title, job.raw_description)

    rag_result = _search_with_managed_ollama(
        _rag_query(job.role_title, job.raw_description),
        persona["assigned_persona"],
    )
    try:
        lexical_evaluation = matcher.evaluate_job_match(
            job.role_title,
            job.company_name,
            job.raw_description,
            target_persona=persona["assigned_persona"] if persona["assigned_persona"] in PERSONAS else "All",
        )
    except (sqlite3.Error, ValueError) as exc:
        lexical_evaluation = {"warning": f"Technology bridge evaluation unavailable: {exc}"}

    bridges = lexical_evaluation.get("transferable_bridges", [])
    return {
        "company_name": job.company_name,
        "role_title": job.role_title,
        "job_url": job.job_url,
        "triage": {
            **persona,
            "domain_tags": domains,
            "location": location,
            "decision_policy": "Suggestions only; candidate review is required.",
        },
        "evidence_retrieval": rag_result,
        "transferable_bridges": bridges,
        "bridge_notice": (
            "Bridge drafts are conceptual adjacency only and are returned only with a matching "
            "candidate-provided SQLite evidence claim and its provenance. They do not establish "
            "direct hands-on production use of the target technology. Review every cited claim "
            "before reusing a draft."
        ),
        "outreach_draft": _outreach_draft(job.company_name, job.role_title, rag_result),
        "outreach_policy": "Draft only. JobG's does not send messages.",
        "status": "DISCOVERED",
    }


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(database.DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def add_job(job: JobSubmission) -> dict:
    """Triage and idempotently save a discovered role and company inventory row."""
    with closing(_connect()) as conn:
        existing = conn.execute(
            "SELECT id, status FROM application_tracker WHERE job_url = ?",
            (job.job_url,),
        ).fetchone()
    if existing:
        return {
            "saved": True,
            "duplicate": True,
            "tracking_id": existing["id"],
            "status": existing["status"],
            "message": "This job URL is already in the tracker; the existing record was left unchanged.",
        }

    result = triage_job(job)
    triage = result["triage"]
    company_vertical = job.company_vertical or (
        ", ".join(triage["domain_tags"])
        if triage["domain_tags"] != ["Unclassified"] else ""
    )
    now = datetime.now(timezone.utc).isoformat()

    with closing(_connect()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            "SELECT id, status FROM application_tracker WHERE job_url = ?",
            (job.job_url,),
        ).fetchone()
        if existing:
            return {
                "saved": True,
                "duplicate": True,
                "tracking_id": existing["id"],
                "status": existing["status"],
                "message": "This job URL is already in the tracker; the existing record was left unchanged.",
            }

        conn.execute(
            """INSERT INTO companies_inventory
                   (company_name, domain, hq, vertical, company_size,
                    tech_stack_json, careers_url, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(company_name) DO UPDATE SET
                   domain = CASE WHEN excluded.domain <> '' THEN excluded.domain ELSE companies_inventory.domain END,
                   hq = CASE WHEN excluded.hq <> '' THEN excluded.hq ELSE companies_inventory.hq END,
                   vertical = CASE WHEN excluded.vertical <> '' THEN excluded.vertical ELSE companies_inventory.vertical END,
                   company_size = CASE WHEN excluded.company_size <> '' THEN excluded.company_size ELSE companies_inventory.company_size END,
                   tech_stack_json = CASE WHEN excluded.tech_stack_json <> '[]' THEN excluded.tech_stack_json ELSE companies_inventory.tech_stack_json END,
                   careers_url = CASE WHEN excluded.careers_url <> '' THEN excluded.careers_url ELSE companies_inventory.careers_url END,
                   updated_at = excluded.updated_at""",
            (
                job.company_name,
                job.company_domain,
                job.company_hq,
                company_vertical,
                job.company_size,
                json.dumps(job.company_tech_stack, ensure_ascii=False),
                job.careers_url,
                now,
            ),
        )
        company = conn.execute(
            "SELECT id FROM companies_inventory WHERE company_name = ? COLLATE NOCASE",
            (job.company_name,),
        ).fetchone()
        cursor = conn.execute(
            """INSERT INTO application_tracker
                   (company_id, company_name, role_title, job_url, location,
                    work_model, raw_description, assigned_persona, domain_tags_json,
                    triage_json, rag_results_json, transferable_bridges_json,
                    outreach_draft, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DISCOVERED', ?, ?)""",
            (
                company["id"], job.company_name, job.role_title, job.job_url,
                job.location, triage["location"]["work_model"], job.raw_description,
                triage["assigned_persona"], json.dumps(triage["domain_tags"]),
                json.dumps(triage, ensure_ascii=False),
                json.dumps(result["evidence_retrieval"], ensure_ascii=False),
                json.dumps(result["transferable_bridges"], ensure_ascii=False),
                result["outreach_draft"], now, now,
            ),
        )

    return {
        "saved": True,
        "duplicate": False,
        "tracking_id": cursor.lastrowid,
        "status": "DISCOVERED",
        "message": "Role saved for human review. No application was submitted and no outreach was sent.",
        **result,
    }
