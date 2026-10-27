# JobG's AI Engineering & Upskilling Roadmap

## Purpose

Use JobG's as a personal, local-first project for learning applied AI engineering while improving an executive job-search workflow. Each phase should produce a working, reviewable deliverable and a short learning note that explains the design, trade-offs, limitations, and how to discuss the work in an interview.

This is a 24-week learning roadmap, not a commitment to ship a public autonomous job-application service. The user remains the decision maker: generated assessments and application materials require review, and the app does not submit applications automatically.

## Starting point

The current engine is a local FastAPI application backed by SQLite. It has a manually entered job-description workflow, a transparent literal profile-term scan, a daily role-log limit, and a candidate-authored evidence dossier. The current scan is not an AI fit score. Evidence is self-reported and is not independently verified. Local-first reduces unnecessary data sharing but does not itself encrypt the database or protect it from other users of the PC.

The existing [MVP build plan](MVP_BUILD_PLAN.md) remains the short-term baseline. This roadmap layers a longer learning path on top without replacing that plan.

The Week 1 local retrieval prototype is documented in [RAG_MATCHER_GUIDE.md](jobgs-engine/RAG_MATCHER_GUIDE.md); it is a standalone module and has not yet been wired into the FastAPI screen.

## 24-week outline

| Phase | Weeks | Learning focus | JobG's deliverable |
|---|---:|---|---|
| 1. Local retrieval & RAG | 1–4 | Text preparation, chunking, embeddings, vector search, retrieval evaluation, grounded generation | Search profile evidence by meaning and return evidence-linked, human-reviewed role analysis |
| 2. Structured AI workflows | 5–8 | Model API boundaries, structured output, prompt design, validation, retries, cost and latency measurement | Provider-independent analysis service producing validated strengths, gaps, unknowns, and evidence references |
| 3. Agentic workflows | 9–12 | Tool calling, workflow state, bounded agents, approvals, idempotency, auditability | A supervised workflow that can organize imported roles and prepare drafts, with explicit user approval gates |
| 4. MCP and interoperability | 13–16 | MCP concepts, tool/resource boundaries, authentication, least privilege, threat modeling | A local, read-limited MCP interface for approved JobG's data, initially disabled by default |
| 5. Cloud, governance & FinOps | 17–20 | Containerization, cloud deployment patterns across GCP/AWS/Azure, secrets, observability, privacy, cost controls | A deployment rehearsal and architecture decision record; retain local mode as the default |
| 6. Autonomous execution & portfolio | 21–24 | Permitted discovery sources, queueing, evaluations, reliability, governance, release communication | A controlled discovery and preparation workflow; all external actions remain explicitly reviewed |

## Weeks 1–4 curriculum

### Week 1 — Retrieval foundations and data boundaries

**Learn:** lexical search versus semantic search; what an embedding represents; why retrieved context can be incomplete or irrelevant; local data and privacy boundaries.

**Build:** document the retrieval contract. Identify which candidate-authored evidence fields may be indexed, which must be excluded (for example secrets or confidential source documents), and what each search result must return (claim ID, persona, claim text, evidence summary, and source reference).

**Deliverable:** `docs/adr/0001-local-rag-data-boundaries.md` or an equivalent short decision record, plus a small, synthetic evaluation set. Do not put real resume or confidential profile text in Git.

**Acceptance:** the user can explain what is indexed, where it is stored, how it can be rebuilt, and why retrieval is not proof that a claim is true.

### Week 2 — Local vector index prototype

**Learn:** chunking, embedding models, similarity search, metadata filters, and the difference between an embedding index and the source-of-truth database.

**Build:** prototype indexing only approved `profile_evidence` claims. Start with one claim per chunk rather than splitting short claims arbitrarily. Store each vector's evidence row ID, persona, and index/model version as metadata. Keep the vector index local and disposable.

**Deliverable:** a small retrieval module behind an interface such as `search_evidence(query, persona, limit)`. Compare one local vector-store option with SQLite full-text search (FTS5) as a simpler baseline before selecting the implementation.

**Acceptance:** exact and paraphrased queries return relevant claims; persona filters work; changing or deleting a source claim does not leave stale results after index rebuild.

### Week 3 — Retrieval evaluation and grounding

**Learn:** retrieval precision/recall, top-k selection, metadata filtering, evidence provenance, and common failure modes (missed evidence, unrelated matches, duplicate claims).

**Build:** label a small set of synthetic or sanitized queries with expected evidence IDs. Evaluate retrieval before adding a language model. Show retrieved claims and their provenance in the UI, and make an empty or weak retrieval result explicit.

**Deliverable:** a repeatable retrieval evaluation note and a retrieval panel or internal prototype. Keep the existing lexical scan available for comparison.

**Acceptance:** reviewers can see why each claim was retrieved; irrelevant claims can be rejected; no result is presented as a candidate fact unless it comes from a saved claim.

### Week 4 — Grounded RAG analysis slice

**Learn:** retrieval-augmented generation (RAG), context construction, structured responses, prompt injection in pasted job descriptions, and human review.

**Build:** add a narrow RAG path that retrieves evidence for a pasted job description and produces a structured draft: `strengths`, `gaps`, `unknowns`, and `evidence_ids`. Require evidence IDs for candidate-specific strengths. Treat the JD as untrusted input, never as instructions to the system. Do not generate or save a resume rewrite in this first slice.

**Deliverable:** a local, evidence-linked analysis preview with an explicit human-review step and a note comparing its output to the Week 3 retrieval results.

**Acceptance:** output validates against a schema; every claimed strength points to an existing evidence ID; unsupported details are marked unknown; the user can reject or edit the draft; the baseline remains available if the model or index is unavailable.

## Proposed integration architecture

```text
FastAPI routes and templates
        |
        +-- Existing lexical matcher (baseline and fallback)
        |
        +-- RAG service (orchestrates retrieval and optional model call)
                 |
                 +-- Evidence repository: SQLite profile_evidence (source of truth)
                 +-- Retrieval interface: SQLite FTS5 baseline / local vector index
                 +-- Optional model provider adapter (added after evaluation)
```

SQLite remains authoritative for evidence claims, roles, and application state. The vector index is a derived cache that can be deleted and rebuilt from eligible SQLite rows; it must not become the only copy of a profile fact. Index records should retain source row IDs and metadata needed to filter by persona. Changes to source claims should trigger an update or mark the index stale. Version the embedding model and chunking strategy so index rebuilds are reproducible.

Keep route handlers thin. Put data access in a repository layer, retrieval in a dedicated service, and model-specific calls behind a provider interface. The RAG service should return typed data rather than HTML. The UI should display supporting evidence, unknowns, and a review action. Avoid adding a public endpoint or cloud service until local behavior, privacy decisions, and evaluation quality are understood.

### Suggested incremental project structure

Add modules only when their phase begins; this is the target shape, not a requirement to create empty files now:

```text
JobG's/
├── AI_UPSKILLING_ROADMAP.md
├── docs/
│   ├── adr/                    # Architecture decisions and learning notes
│   └── evaluations/            # Sanitized retrieval and output evaluations
└── jobgs-engine/
    ├── app.py                  # FastAPI routes and human-review workflow
    ├── database.py             # SQLite schema and migrations
    ├── evidence.py             # Evidence validation and persistence
    ├── matcher.py              # Explainable lexical baseline
    ├── retrieval/              # Local search interface and implementations
    ├── rag/                    # Grounded analysis orchestration and schemas
    ├── templates/              # User interface
    └── tests/                  # Unit and integration checks
```

Do not place a real vector database or candidate dossier in the repository. Ignore local index directories, databases, resumes, model caches, and secrets in Git. Keep any test fixtures synthetic or sanitized.

## Learning log template

For each weekly deliverable, record:

1. **What changed:** the user-visible and technical result.
2. **Concept learned:** explain it in plain language.
3. **Design choice:** alternatives considered and why this one was selected.
4. **Evidence:** commands, evaluation examples, or screenshots that show behavior.
5. **Limitations:** known failure cases and privacy/cost implications.
6. **Interview explanation:** a concise account of the problem, design, and trade-off.

## Guardrails for the roadmap

- A similarity score is retrieval relevance, not job fit, qualification, or hiring probability.
- Model-generated statements must be traceable to candidate-provided evidence or labeled unknown.
- Do not claim a technology, metric, certification, or outcome based only on semantic similarity.
- Keep job-site ingestion within the source's permitted access and terms; begin with manual input or user-provided URLs.
- Keep application submission, messages, and other external actions under explicit user control.
- Measure usefulness and failure cases before adding agents, more providers, or cloud infrastructure.
