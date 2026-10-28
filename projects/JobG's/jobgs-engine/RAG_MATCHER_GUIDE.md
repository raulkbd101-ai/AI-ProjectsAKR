# Local hybrid evidence search and Week 1 learning guide

`rag_matcher.py` retrieves candidate-authored claims from `profile_evidence`. When Ollama is available it combines lexical overlap (35%) with semantic similarity (65%) from the local `nomic-embed-text` model. Persona weighting can adjust result ordering after the base retrieval score is calculated. It does not call a hosted AI API, generate resume prose, verify claims, or make an application decision.

## Architecture

```text
Pasted JD/query
      |
      +--> lexical token overlap ------------------+
      |                                            |
      +--> local Ollama embedding --> cosine ------+--> ranked evidence IDs
                                                   |
SQLite profile_evidence --> local vector cache ---+
```

- `profile_evidence` remains the authoritative record.
- `evidence_embeddings` is a derived cache stored in the same local SQLite database. It stores vectors keyed by evidence row and model name, and refreshes only new or edited eligible claims.
- Confidential claims are excluded by default. Persona filtering is applied when searching; indexing is global across eligible claims so switching personas cannot erase another persona's vectors.
- `retrieval_score` ranks search relevance only. It does not represent job fit, proficiency, truth, or chance of an interview.
- The standalone CLI can return lexical-only results with a warning if Ollama is unavailable; `--keywords-only` explicitly selects that mode.
- The `/api/triage-job` and `/api/add-job` paths require managed hybrid output and should return an error rather than accept lexical fallback.

The default model is `nomic-embed-text`. Sentence Transformers can also generate embeddings locally, but the first slice uses Ollama's loopback HTTP API to avoid adding a large Python/PyTorch dependency to the existing Python 3.14 environment. The model must be downloaded to the PC once; that is a model download, not a paid inference API call. Embeddings and search requests stay local when Ollama is running locally. The official [Ollama model page](https://ollama.com/library/nomic-embed-text) documents the model pull command and local `/api/embed` endpoint.

## Windows setup

From PowerShell, with the current virtual environment active:

```powershell
ollama pull nomic-embed-text
```

Start the Ollama application/service, then from `projects\JobG's\jobgs-engine` run:

```powershell
python rag_matcher.py "cloud data platform architecture and BI modernization" --persona Architect
```

### Managed session wrapper status

The Week 1 exercise developed a PowerShell wrapper concept to start Ollama on demand and verify that port `11434` is released after the query. **However, `run_rag_session.ps1` is absent from this repository checkout.** The job-copilot API expects this file, so API triage/add must not be described as verified in a fresh clone until the script is restored and reviewed.

For now, the standalone CLI commands above require Ollama to be started separately. If using a manually started server, stop the Ollama app/service with its own controls after finishing. Avoid terminating processes by name unless you have confirmed they belong to this query, since other local applications can share the service.

If the reviewed lifecycle wrapper is restored later, its intended invocation is:

```powershell
.\run_rag_session.ps1 "cloud data platform architecture" -Persona Architect
```

Do not use this command until the script exists in the current project folder.

To try lexical retrieval without Ollama:

```powershell
python rag_matcher.py "cloud data platform architecture and BI modernization" --persona Architect --keywords-only
```

The script assumes `database.py` has already initialized the database and the current directory is `jobgs-engine`, matching the existing app's `DB_FILE` behavior. Use synthetic or non-confidential job text for initial experiments. Do not add the SQLite database, vectors, candidate resumes, or sensitive job descriptions to Git.

## Python use

```python
from rag_matcher import refresh_evidence_index, search_evidence

index_status = refresh_evidence_index()
results = search_evidence(
    "Lead secure multi-cloud data platform modernization",
    target_persona="Architect",
    top_k=5,
)
```

Each result includes the supporting evidence ID and claim, persona, evidence status, confidentiality label, lexical score, semantic score (when local embeddings are available), and combined retrieval score. A later RAG service can pass only these selected evidence records to a model, then require the model to cite their IDs. The current module only retrieves evidence; it does not generate prose.
