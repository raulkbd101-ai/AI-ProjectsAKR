"""Typed, evidence-linked candidate claims for JobG's local profile."""

import sqlite3
from contextlib import closing
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from database import DB_FILE


class EvidenceClaim(BaseModel):
    """A candidate-authored claim and a concise note explaining its support.

    This model stores summaries and references only. It is not a place to paste
    confidential employer documents or personal data about other people.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    competency: str = Field(min_length=2, max_length=120)
    claim: str = Field(min_length=8, max_length=600)
    context: str = Field(default="", max_length=300)
    evidence_summary: str = Field(min_length=8, max_length=1000)
    impact_metric: str = Field(default="", max_length=300)
    source_reference: str = Field(default="", max_length=300)
    # These describe what the candidate recorded, not independent validation.
    evidence_status: Literal[
        "self_reported",
        "reference_added",
        "supporting_material_noted",
    ] = "self_reported"
    confidentiality: Literal["public", "private", "confidential"] = "private"


def add_evidence_claim(claim: EvidenceClaim) -> int:
    """Save a claim for the single local master profile and return its ID."""
    with closing(sqlite3.connect(DB_FILE)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        with conn:
            profile = conn.execute(
                "SELECT id FROM master_profile ORDER BY id LIMIT 1"
            ).fetchone()
            if profile is None:
                raise ValueError("Master profile not found. Run database.py first.")

            cursor = conn.execute(
                """INSERT INTO profile_evidence (
                       profile_id, competency, claim, context, evidence_summary,
                       impact_metric, source_reference, evidence_status, confidentiality
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    profile[0],
                    claim.competency,
                    claim.claim,
                    claim.context,
                    claim.evidence_summary,
                    claim.impact_metric,
                    claim.source_reference,
                    claim.evidence_status,
                    claim.confidentiality,
                ),
            )
            return cursor.lastrowid


def list_evidence_claims() -> list[dict]:
    """Return the local profile's claims in creation order."""
    with closing(sqlite3.connect(DB_FILE)) as conn:
        rows = conn.execute(
            """SELECT id, competency, claim, context, evidence_summary,
                      impact_metric, source_reference, evidence_status,
                      confidentiality, created_at
               FROM profile_evidence ORDER BY id"""
        ).fetchall()

    columns = (
        "id",
        "competency",
        "claim",
        "context",
        "evidence_summary",
        "impact_metric",
        "source_reference",
        "evidence_status",
        "confidentiality",
        "created_at",
    )
    return [dict(zip(columns, row)) for row in rows]
