# Week 1 Milestone: Local Evidence Search Foundation

## Goal

Create a local source of candidate evidence and a retrieval prototype that can find potentially relevant claims from a query without sending profile text to a hosted embedding API.

## Delivered

- SQLite `profile_evidence` table and typed evidence-claim validation, with persona and confidentiality metadata.
- `rag_matcher.py` for lexical overlap and semantic retrieval using local Ollama `nomic-embed-text` embeddings.
- A rebuildable `evidence_embeddings` cache; SQLite claims remain authoritative.
- Persona filtering and exclusion of confidential claims by default.
- CLI keyword-only mode and explicit lexical fallback when Ollama is not reachable.
- A guide for local model setup, query examples, data boundaries, and limitations.

## Data flow

```text
Evidence claim saved in SQLite
        ↓
Eligible claim text is embedded locally by Ollama
        ↓
Vector and model metadata saved in derived SQLite cache
        ↓
Candidate query is compared lexically and semantically
        ↓
Persona/confidentiality filters applied; evidence IDs and scores returned
```

The `retrieval_score` is evidence-search relevance only. It is not a job-fit score, qualification rating, truth verification, or hiring prediction. The module retrieves claims; it does not generate a resume or RAG narrative.

## Local commands

Run from `jobgs-engine` after initializing the database and installing Ollama/model:

```powershell
ollama pull nomic-embed-text
python rag_matcher.py "cloud data platform architecture" --persona Architect
python rag_matcher.py "multi-cloud transformation" --keywords-only
```

When local embeddings are unavailable, the CLI may report `lexical_fallback`. That behavior is useful for standalone search diagnostics. The Week 2 job intake API requires hybrid results and should fail closed when the local model cannot be used.

## Learning outcomes

- Embeddings make semantic similarity search possible; they do not know whether a claim is true.
- A vector index is derived data and should be rebuildable from its source rows.
- Local processing can reduce external data transfer and hosted inference charges, but still uses local compute and downloaded model storage.
- Search metrics need a labeled evaluation before they can support claims about matching quality.

## Release reference

The initial hybrid retrieval feature was released under `v1.3.0`. See [RAG_MATCHER_GUIDE.md](../jobgs-engine/RAG_MATCHER_GUIDE.md) and [CHANGELOG.md](../CHANGELOG.md).
