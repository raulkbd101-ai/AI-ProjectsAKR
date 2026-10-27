"""Backward-compatible imports; new code should import from evidence."""

from evidence import EvidenceClaim, add_evidence_claim, list_evidence_claims

__all__ = ["EvidenceClaim", "add_evidence_claim", "list_evidence_claims"]
