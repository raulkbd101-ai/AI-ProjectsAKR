"""Local hybrid retrieval over JobG's candidate-authored SQLite evidence.

SQLite remains the source of truth. Vectors are a rebuildable local cache and
are generated through Ollama's loopback-only embedding API; this module makes
no hosted model/API calls.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from database import DB_FILE

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"
DEFAULT_TOP_K = 5
DEFAULT_SEMANTIC_WEIGHT = 0.65
TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9+#.-]*", re.IGNORECASE)
ALLOWED_PERSONAS = {"All", "Director", "Architect", "TPM"}

# Persona signals are used only to prioritize relevant evidence for review.
# They do not represent job-fit, proficiency, or truth scores.
PERSONA_KEYWORD_WEIGHTS = {
    "Director": {
        "leadership": 3,
        "team leadership": 3,
        "global team": 3,
        "budget management": 3,
        "budget": 2,
        "organizational transformation": 3,
        "transformation": 2,
        "operating model": 2,
        "executive strategy": 2,
        "finops": 2,
        "delivery": 1,
    },
    "Architect": {
        "cloud migration": 3,
        "multi-cloud": 3,
        "multi cloud": 3,
        "system design": 3,
        "architecture": 2,
        "scalability": 3,
        "scalable": 2,
        "cloud architecture": 3,
        "reliability": 2,
        "disaster recovery": 2,
        "iam": 2,
        "platform modernization": 2,
    },
    "TPM": {
        "cross-functional": 3,
        "program delivery": 3,
        "program management": 3,
        "stakeholder management": 3,
        "stakeholder": 2,
        "risk mitigation": 3,
        "risk": 2,
        "execution tracking": 3,
        "milestone": 2,
        "dependency": 2,
        "governance": 2,
        "delivery": 1,
    },
}

_PERSONA_TERM_PATTERNS = {
    persona: [
        (re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE), weight, term)
        for term, weight in terms.items()
    ]
    for persona, terms in PERSONA_KEYWORD_WEIGHTS.items()
}


def _local_ollama_url() -> str:
    """Return a loopback Ollama URL and reject remote hosts by design."""
    import os

    base_url = os.environ.get("JOBGS_OLLAMA_URL", DEFAULT_OLLAMA_URL).rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Ollama must use a local loopback URL (http://127.0.0.1:11434).")
    if parsed.path not in {"", "/"} or parsed.username or parsed.password:
        raise ValueError("JOBGS_OLLAMA_URL must contain only the local server origin.")
    return base_url


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_vector_table(conn: sqlite3.Connection) -> None:
    """Create the disposable vector cache without changing profile tables."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS evidence_embeddings (
               evidence_id INTEGER NOT NULL REFERENCES profile_evidence(id) ON DELETE CASCADE,
               model_name TEXT NOT NULL,
               content_hash TEXT NOT NULL,
               vector_json TEXT NOT NULL,
               updated_at TEXT NOT NULL,
               PRIMARY KEY (evidence_id, model_name)
           )"""
    )


def _claim_text(claim: sqlite3.Row) -> str:
    """Build an indexable passage; deliberately omit private source paths."""
    fields = (
        claim["competency"],
        claim["claim"],
        claim["context"],
        claim["evidence_summary"],
        claim["impact_metric"],
    )
    return "\n".join(str(value).strip() for value in fields if value and str(value).strip())


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _embed(texts: list[str], model_name: str, timeout_seconds: int = 120) -> list[list[float]]:
    """Call Ollama locally to generate embeddings for one or more passages."""
    if not texts:
        return []

    payload = json.dumps({"model": model_name, "input": texts}).encode("utf-8")
    request = Request(
        f"{_local_ollama_url()}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"Ollama embedding request failed ({exc.code}): {detail}") from exc
    except URLError as exc:
        raise RuntimeError(
            "Cannot reach local Ollama. Start Ollama and pull the embedding model first."
        ) from exc

    vectors = body.get("embeddings")
    if not isinstance(vectors, list) or len(vectors) != len(texts):
        raise RuntimeError("Ollama returned an unexpected embeddings response.")
    if any(not isinstance(vector, list) or not vector for vector in vectors):
        raise RuntimeError("Ollama returned an empty or invalid embedding vector.")
    return [[float(value) for value in vector] for vector in vectors]


def refresh_evidence_index(
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    include_confidential: bool = False,
) -> dict:
    """Embed new or changed evidence passages and persist vectors in SQLite.

    This is safe to rerun: unchanged passages are not re-embedded. Claims are
    still authoritative in profile_evidence; the vector rows can be rebuilt.
    """
    with closing(_connect()) as conn:
        _ensure_vector_table(conn)
        query = """SELECT id, competency, claim, context, evidence_summary,
                          impact_metric, target_persona, confidentiality
                   FROM profile_evidence"""
        filters = []
        params: list[str] = []
        if not include_confidential:
            filters.append("confidentiality != 'confidential'")
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY id"
        claims = conn.execute(query, params).fetchall()

        changed = []
        for claim in claims:
            text = _claim_text(claim)
            digest = _content_hash(text)
            saved = conn.execute(
                """SELECT content_hash FROM evidence_embeddings
                   WHERE evidence_id = ? AND model_name = ?""",
                (claim["id"], model_name),
            ).fetchone()
            if saved is None or saved["content_hash"] != digest:
                changed.append((claim["id"], digest, text))

        vectors = _embed([text for _, _, text in changed], model_name)
        timestamp = datetime.now(timezone.utc).isoformat()
        with conn:
            for (evidence_id, digest, _), vector in zip(changed, vectors):
                conn.execute(
                    """INSERT INTO evidence_embeddings
                           (evidence_id, model_name, content_hash, vector_json, updated_at)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(evidence_id, model_name) DO UPDATE SET
                           content_hash = excluded.content_hash,
                           vector_json = excluded.vector_json,
                           updated_at = excluded.updated_at""",
                    (evidence_id, model_name, digest, json.dumps(vector), timestamp),
                )

            current_ids = [claim["id"] for claim in claims]
            if current_ids:
                placeholders = ",".join("?" for _ in current_ids)
                conn.execute(
                    f"DELETE FROM evidence_embeddings WHERE model_name = ? "
                    f"AND evidence_id NOT IN ({placeholders})",
                    [model_name, *current_ids],
                )
            else:
                conn.execute(
                    "DELETE FROM evidence_embeddings WHERE model_name = ?", (model_name,)
                )

        return {
            "model_name": model_name,
            "persona": "All eligible claims (persona filtering happens at search time)",
            "eligible_claims": len(claims),
            "embedded_or_updated": len(changed),
            "index_location": "local SQLite evidence_embeddings table",
        }


def _tokens(text: str) -> set[str]:
    return {token.casefold() for token in TOKEN_PATTERN.findall(text)}


def _persona_evidence_signals(match: dict, persona: str) -> tuple[float, list[str]]:
    """Return normalized persona-keyword coverage and the matched signals."""
    if persona not in PERSONA_KEYWORD_WEIGHTS:
        return 0.0, []

    searchable_text = " ".join(
        str(match.get(field) or "")
        for field in (
            "competency",
            "claim",
            "context",
            "evidence_summary",
            "impact_metric",
        )
    )

    matched_terms = []
    matched_weight = 0
    for pattern, weight, term in _PERSONA_TERM_PATTERNS[persona]:
        if pattern.search(searchable_text):
            matched_terms.append(term)
            matched_weight += weight

    total_weight = sum(PERSONA_KEYWORD_WEIGHTS[persona].values())
    score = matched_weight / total_weight if total_weight else 0.0
    return score, matched_terms


def _apply_persona_weighting(matches: list[dict], persona: str) -> list[dict]:
    """Blend persona alignment into evidence retrieval scores for review."""
    if persona == "All":
        return matches

    ranked = []
    for match in matches:
        base_score = float(match.get("retrieval_score") or 0.0)
        persona_score, matched_terms = _persona_evidence_signals(match, persona)

        # search_evidence already limits explicit claims to this persona plus
        # shared "All" claims. Prefer an explicit persona tag slightly.
        scope_score = 1.0 if match.get("target_persona") == persona else 0.5
        final_score = (
            0.70 * base_score
            + 0.25 * persona_score
            + 0.05 * scope_score
        )

        ranked_match = dict(match)
        ranked_match["base_retrieval_score"] = round(base_score, 4)
        ranked_match["persona_score"] = round(persona_score, 4)
        ranked_match["persona_signals"] = matched_terms
        # Preserve retrieval_score as the original hybrid/lexical metric for
        # backward compatibility; use the adjusted score only for ordering.
        ranked_match["persona_adjusted_score"] = round(final_score, 4)
        ranked.append(ranked_match)

    ranked.sort(
        key=lambda item: (
            item["persona_adjusted_score"],
            item["base_retrieval_score"],
            item.get("lexical_score", 0.0),
        ),
        reverse=True,
    )
    return ranked


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return max(0.0, sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm))


def search_evidence(
    query: str,
    target_persona: str = "All",
    top_k: int = DEFAULT_TOP_K,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    semantic_weight: float = DEFAULT_SEMANTIC_WEIGHT,
    include_confidential: bool = False,
    use_embeddings: bool = True,
) -> dict:
    """Return hybrid lexical/semantic evidence matches with provenance.

    If Ollama is unavailable, the function reports and uses lexical-only
    retrieval so the workflow can still be explored without model setup.
    Similarity is relevance for retrieval, never a job-fit or truth score.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Search query must not be empty.")
    if target_persona not in ALLOWED_PERSONAS:
        raise ValueError("Unsupported target persona.")
    if top_k < 1:
        raise ValueError("top_k must be at least 1.")
    if not 0.0 <= semantic_weight <= 1.0:
        raise ValueError("semantic_weight must be between 0 and 1.")

    with closing(_connect()) as conn:
        _ensure_vector_table(conn)
        sql = """SELECT id, competency, claim, context, evidence_summary,
                        impact_metric, source_reference, target_persona,
                        evidence_status, confidentiality
                 FROM profile_evidence"""
        clauses = []
        params: list[str] = []
        if target_persona != "All":
            clauses.append("target_persona IN ('All', ?)")
            params.append(target_persona)
        if not include_confidential:
            clauses.append("confidentiality != 'confidential'")
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id"
        claims = conn.execute(sql, params).fetchall()
        saved_vectors = {
            row["evidence_id"]: json.loads(row["vector_json"])
            for row in conn.execute(
                "SELECT evidence_id, vector_json FROM evidence_embeddings WHERE model_name = ?",
                (model_name,),
            ).fetchall()
        }

    if not claims:
        return {"retrieval_mode": "empty", "matches": [], "warning": None}

    warning = None
    query_vector = None
    if use_embeddings:
        try:
            # Refresh the derived cache so edited/new evidence is included.
            refresh_evidence_index(model_name, include_confidential)
            with closing(_connect()) as conn:
                saved_vectors = {
                    row["evidence_id"]: json.loads(row["vector_json"])
                    for row in conn.execute(
                        "SELECT evidence_id, vector_json FROM evidence_embeddings WHERE model_name = ?",
                        (model_name,),
                    ).fetchall()
                }
            query_vector = _embed([query], model_name)[0]
        except (RuntimeError, ValueError) as exc:
            warning = str(exc)

    query_tokens = _tokens(query)
    semantic_available = query_vector is not None
    matches = []
    for claim in claims:
        passage = _claim_text(claim)
        passage_tokens = _tokens(passage)
        lexical_score = (
            len(query_tokens & passage_tokens) / len(query_tokens) if query_tokens else 0.0
        )
        semantic_score = None
        if semantic_available:
            vector = saved_vectors.get(claim["id"])
            if vector is not None:
                semantic_score = _cosine(query_vector, vector)
                combined_score = (
                    semantic_weight * semantic_score
                    + (1.0 - semantic_weight) * lexical_score
                )
            else:
                combined_score = lexical_score
        else:
            combined_score = lexical_score

        matches.append({
            "evidence_id": claim["id"],
            "competency": claim["competency"],
            "claim": claim["claim"],
            "context": claim["context"],
            "evidence_summary": claim["evidence_summary"],
            "impact_metric": claim["impact_metric"],
            "source_reference": claim["source_reference"],
            "target_persona": claim["target_persona"],
            "evidence_status": claim["evidence_status"],
            "confidentiality": claim["confidentiality"],
            "lexical_score": round(lexical_score, 4),
            "semantic_score": round(semantic_score, 4) if semantic_score is not None else None,
            "retrieval_score": round(combined_score, 4),
        })

    matches = _apply_persona_weighting(matches, target_persona)
    return {
        "retrieval_mode": "hybrid" if semantic_available else "lexical_fallback",
        "model_name": model_name if semantic_available else None,
        "matches": matches[:top_k],
        "warning": warning,
        "score_notice": "Retrieval relevance only; not a job-fit, proficiency, or truth score.",
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Search JobG's local evidence dossier.")
    parser.add_argument("query", help="A job-description excerpt or skill need")
    parser.add_argument("--persona", choices=sorted(ALLOWED_PERSONAS), default="All")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--keywords-only", action="store_true", help="Skip local embeddings")
    args = parser.parse_args()
    print(json.dumps(search_evidence(
        args.query,
        target_persona=args.persona,
        top_k=args.top_k,
        use_embeddings=not args.keywords_only,
    ), indent=2))
