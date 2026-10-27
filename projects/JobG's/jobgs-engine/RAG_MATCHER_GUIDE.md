# Local hybrid evidence search: Day 1

`rag_matcher.py` adds local hybrid retrieval over the existing `profile_evidence` table. It combines exact word overlap with semantic similarity from an embedding model served by Ollama on the same PC. It does not call a hosted API and does not make an application decision.

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
- If Ollama is unavailable, the code reports a warning and returns lexical-only results.

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
