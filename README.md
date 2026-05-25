# Cardiac Matchmaker

## Start

```bash
cp .env.example .env
make up
```

## Stop

```bash
make down
```

## Backend

FastAPI + Peewee + cookie JWT auth. `POST /api/v1/auth/login` sets `access_token`. All `/api/v1/*` routes except `/api/v1/health`, `/api/v1/auth/login`, and `/api/v1/auth/logout` need that cookie.

Create a backend user from inside the running backend container:

```bash
docker compose exec backend python -m app.cmd.create_user user@example.com
```

If you do not pass `--password`, the command prompts for it securely.

Common examples:

```bash
docker compose exec backend python -m app.cmd.create_user admin@example.com --superuser
docker compose exec backend python -m app.cmd.create_user doctor@example.com --password 'change-me'
docker compose exec backend python -m app.cmd.create_user reviewer@example.com --inactive
docker compose exec backend python -m app.cmd.create_user admin@example.com --superuser --json
```

Available flags:

- `--password`: provide the password inline instead of using the secure prompt
- `--superuser`: create the user with superuser access
- `--inactive`: create the user as inactive
- `--json`: print the created user as JSON

Database migrations run automatically when the backend container starts. You can also run them manually:

```bash
docker compose exec backend python -m app.cmd.migrate check
docker compose exec backend python -m app.cmd.migrate apply
```

## Demo data

Create the development storage layout and seed a demo research project:

```bash
docker compose exec backend python -m app.cmd.seed_demo
```

The seed command creates `data/raw`, `data/processed`, `data/pdfs`, `data/logs`, and `data/reports`.

## .env

```env
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
POSTGRES_HOST=
POSTGRES_PORT=
JWT_SECRET_KEY=
JWT_ALGORITHM=
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=
```

## Analysis pipeline

Cardiac Matchmaker recommends which placental tissue (Amnion, Basal tissue, Chorion, Umbilical Cord — native or decellularized) best matches a target heart structure, and grounds every driver protein in the literature or UniProt.

Flow:

1. **Ingest** the placenta+heart proteomics TSV into a dataset version. The parser fills `Sample`/`Measurement` and a `FeatureAnnotation` row per protein (matrisome class, UniProt accession, `match_in_heart`).

   ```bash
   docker compose exec backend python -m app.cmd.ingest_dataset <dataset_version_id> /data/raw/placenta_annotated_forAnalysis.txt
   ```

2. **Create a run** (`POST /api/v1/projects/{project_id}/runs`) with a `target_application`, `target_tissue`, and `query`. The structure is taken from `constraints.structure` (one of `SL-Valves`, `AV-Valves`, `Ventricle`, `Atrium`, `coronaryArtery`, `largeAtery`) if given, otherwise inferred from the target text; if still unresolved, all structures are reported. Creating a run enqueues a `ProcessingJob`.

3. The **worker** claims the job and runs the deterministic engine (`backend/app/services/analysis`):
   - **alignment** (`alignment.py`) — CCA (default) or Procrustes domain adaptation aligns the differently-scaled placental and cardiac proteomes, then scores prep↔structure matches as cosine in the shared space;
   - **literature RAG** (`rag.py` + `rag_store.py`) — project documents are chunked into `DocumentChunk` rows, embedded (MiniLM), and stored in **Qdrant**; drivers are grounded with dense/BM25/hybrid retrieval and page citations;
   - **UniProt** (`uniprot.py`) — fallback function lookup + ECM-vs-contaminant classification;
   - **report** (`report.py`) — the deterministic, cited Decision Report.

   Results are persisted as `AnalysisStep`s, ranked `CandidateMatch`es, `EvidenceItem`s (one per grounded driver), `ContradictionWarning`s (caveats), and a `Report` (`json_body` + `markdown_body`).

Read results back:

```text
GET /api/v1/runs/{run_id}             # status
GET /api/v1/runs/{run_id}/steps       # per-stage progress
GET /api/v1/runs/{run_id}/candidates  # ranked prep matches per structure
GET /api/v1/runs/{run_id}/evidence    # grounded driver evidence
GET /api/v1/runs/{run_id}/report      # the Decision Report (markdown + JSON)
```

**Design invariant:** the recommendation, rankings, and citations are produced entirely by the deterministic engine — there is no LLM in this path.

To index a project document into Qdrant from a shell (the worker mounts the backend at `/app/backend`):

```bash
docker compose exec -e PYTHONPATH=/app/backend worker python -c \
  "from app.services.analysis.rag_store import LiteratureIndexer; \
   from app.models.document.document_model import Document; \
   print(LiteratureIndexer().index_document(Document.get_by_id('<document_id>')))"
```

The analysis dependencies (numpy/pandas/scipy/scikit-learn, qdrant-client/pypdf/rank-bm25) ship with the backend; the worker additionally installs sentence-transformers/torch. Qdrant runs as the `vector-db` service; override its address with `QDRANT_URL` (default `http://vector-db:6333`).

## Testing

```bash
cd backend && pytest
cd frontend && npm run lint && npm run build
```

The analysis engine's pure logic (alignment, RAG retrieval, report assembly, UniProt classification) is unit-tested without external services; the database- and Qdrant-backed paths are exercised by the Postgres-backed suite.
