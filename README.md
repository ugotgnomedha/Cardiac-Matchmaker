# Cardiac Matchmaker

Agentic Research System for matching placental materials to cardiac surgical applications. Aligns proteomics data across different measurement scales, retrieves supporting literature via RAG, and produces explainable Decision Reports through a LangGraph reasoning agent.

## Quick Start

```bash
cp .env.example .env
make up
```

Wait for all 6 services to become healthy: `backend`, `worker`, `db`, `vector-db`, `ollama`, `frontend`.

## Architecture

```
┌──────────┐    ┌────────┐    ┌──────────┐
│ Frontend │───▶│Backend │───▶│PostgreSQL│
│ :3000    │    │ :8000  │    │ :5432    │
└──────────┘    └────────┘    └──────────┘
                     │
              ┌──────┼──────┐
              ▼      ▼      ▼
         ┌──────┐ ┌────┐ ┌──────┐
         │Worker│ │RAG │ │Ollama│
         │      │ │Qdr.│ │:11434│
         └──────┘ └────┘ └──────┘
```

- **Backend**: FastAPI + Peewee ORM + JWT cookie auth
- **Worker**: Background job processor (analysis runs, document indexing)
- **RAG**: Qdrant vector database for literature retrieval
- **Ollama**: Local LLM for the reasoning agent
- **Frontend**: React + TypeScript + HeroUI + SWR

## First Launch

### 1. Create a user

```bash
docker compose exec backend python -m app.cmd.create_user doctor@example.com --password 'change-me'
```

Open `http://localhost:3000` and log in.

### 2. Pull the LLM model

On the main page, click **Pull** in the **Available Models** section, select a model tag (e.g., `qwen2.5:7b`), and click **Pull**. The model downloads in the background and appears in the table with a progress bar.

You can also pull via CLI:
```bash
docker compose exec ollama ollama pull qwen2.5:7b
```

### 3. Set up data directory

```bash
mkdir -p data/pdfs
cp datasets/placenta_annotated_forAnalysis.txt data/placenta.tsv
# Place the Heart Map paper (Doll et al.) as data/pdfs/heart-map.pdf
```

## Workflow

### Create a Project

On the main page `/`, fill in the project name and description, click **Create Project**.

### Register a Dataset

Inside a project, click **Register Dataset**:

| Field | Value |
|-------|-------|
| Dataset name | `Placenta proteomics` |
| Dataset type | `placenta` |
| Original filename | `placenta.tsv` |
| Storage path | `/data/placenta.tsv` |

The backend validates that the file exists before accepting the registration.

Click the **edit** (✏️) icon to modify dataset metadata later, or **delete** (🗑) to remove it.

### Ingest the Dataset

After registration, run the ingestion command to parse the TSV into the database:

```bash
docker compose exec backend python -c "
from uuid import uuid4
from app.models.base.base_model import db
from app.models.dataset.dataset_model import Dataset, DatasetVersion
import datetime

db.connect(reuse_if_open=True)
now = datetime.datetime.now(datetime.timezone.utc)
placenta = Dataset.get(Dataset.name == 'Placenta proteomics')
v = DatasetVersion.create(id=uuid4(), dataset=placenta, version_number='v1', status='raw', storage_path='/data/placenta.tsv', created_at=now)
print(f'Version ID: {v.id}')
db.close()
"
```

```bash
docker compose exec backend python -m app.cmd.ingest_dataset <VERSION_ID> /data/placenta.tsv
```

### Register a Document

Inside a project, click **Register Document**:

| Field | Value |
|-------|-------|
| Document title | `Heart Map — Doll et al.` |
| Original filename | `heart-map.pdf` |
| Storage path | `/data/pdfs/heart-map.pdf` |

### Index the Document

Click the **reload** (🔄) icon next to the document. This enqueues a background job that:
1. Extracts text from the PDF
2. Chunks it into ~500-token segments
3. Embeds with MiniLM and stores in Qdrant
4. Updates status to `indexed`

The main page shows real-time status between runs.

### Create a Run

Inside a project, click **New Run**:

| Field | Value |
|-------|-------|
| Target application | `myocardial patch` |
| Target tissue | `left ventricle` |
| Research query | `Find the best placental material for myocardial patch support.` |
| Constraints JSON | `{"structure": "Ventricle"}` |
| Model | Select from dropdown |

The Model dropdown shows all registered models. If only one is configured, it's auto-selected as readonly. If none, a warning guides you to add one first.

Click **Create Run**. The worker picks up the job and runs the pipeline:

1. **load_proteomics** — parses measurements from the ingested dataset
2. **align** — CCA (default) or Procrustes domain adaptation
3. **retrieve_and_ground** — builds the Decision Report with ranked candidates, driver proteins, and literature citations
4. **agent_reasoning** — LangGraph Planner→Executor→Critic→Reporter loop with the selected LLM

### View Results

The Run Detail page shows:

- **Status** badge (queued → running → completed / failed)
- **Error banner** (red, with full error message if failed)
- **Model** used for this run
- **Trace Steps** — each pipeline stage with timing and status
- **Evidence** — grounded driver proteins with citations
- **Rerun** button — creates a new run with the same parameters and model

Click **Report** to view the Decision Report with recommendations, drivers, and literature-backed justifications.

### Rerun

The **Rerun** button on any run creates a new run preserving:
- Target application, tissue, query, constraints
- The same LLM model (`selected_config`)
- Redirects to the new run

## Model Management

The main page (`/`) shows an **Available Models** table below the project list.

### Quick Pull

Click **Pull** next to the table header. An inline form opens with a model tag select:
- Downloaded models shown first (marked as `downloaded`)
- Popular models follow for auto-pull
- Select a tag, click **Pull** — the model downloads in background and appears in the table with a progress bar

### Add a model (advanced)

Click **Add Model** for full configuration. Two tabs:

**Local (Ollama):**
1. Model tag dropdown: downloaded models shown first (with size), then popular models for auto-pull
2. Display name: auto-fills from model tag
3. **Pull & Add**: downloads the model from Ollama registry, saves to DB, redirects to main page
4. The model shows as `pulling` with an animated progress bar until ready

**API (LiteLLM):**
1. Provider: OpenAI / Anthropic / DeepSeek / Groq / Mistral
2. Model ID: auto-prefilled (e.g., `openai/gpt-4o`)
3. API Key: with show/hide toggle
4. **Test Key**: validates the key with a minimal API call
5. Display name
6. **Add Model**: saves to DB (no pull needed for API models)

### Delete a model

Click 🗑 on any model in the table. For Ollama models, this also runs `ollama rm` to free disk space.

## Supported LLM Providers

The system uses **LiteLLM** for unified model access. Supported providers:

| Provider | Model ID format | Env variable |
|----------|----------------|-------------|
| Ollama (local) | `ollama/qwen2.5:7b` | `OLLAMA_BASE_URL` |
| OpenAI | `openai/gpt-4o` | `OPENAI_API_KEY` |
| Anthropic | `anthropic/claude-3-haiku-20240307` | `ANTHROPIC_API_KEY` |
| DeepSeek | `deepseek/deepseek-chat` | `DEEPSEEK_API_KEY` |
| Groq | `groq/llama-3.3-70b-versatile` | `GROQ_API_KEY` |
| Mistral | `mistral/mistral-large-latest` | `MISTRAL_API_KEY` |

API keys for non-Ollama models are stored in the database and passed to LiteLLM at runtime.

## Agent Evaluation

Run the Level 2 agent output quality evaluation on synthetic data:

```bash
docker compose exec backend python -m tests.model_evaluation
```

With specific model and multiple runs:

```bash
docker compose exec backend python -m tests.model_evaluation --model ollama/qwen2.5:7b --n-runs 3
```

Measures 7 quality metrics:
- **Plan validity** — agent produces ≥2 actionable steps
- **Critic JSON parse** — critic returns valid JSON
- **Contradiction recall** — critic flags planted contaminants (FGB)
- **Report structure** — all required sections present
- **Hallucination score** — 0 mismatches between narrative and ground truth
- **Round count** — agent loop iterations
- **Latency** — wall time in seconds

## Testing

```bash
# Backend tests (73 tests)
docker compose exec backend python -m pytest --tb=short

# Frontend lint + build
cd frontend && npm run lint && npm run build
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | postgres | Database user |
| `POSTGRES_PASSWORD` | postgres | Database password |
| `POSTGRES_DB` | postgres | Database name |
| `POSTGRES_HOST` | db (Docker) / localhost | Database host |
| `POSTGRES_PORT` | 5432 | Database port |
| `JWT_SECRET_KEY` | — | JWT signing key |
| `JWT_ALGORITHM` | HS256 | JWT algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 180 | Token expiry |
| `MATCHMAKER_LLM` | ollama/qwen2.5:7b | Default LLM model |
| `OLLAMA_BASE_URL` | http://ollama:11434 | Ollama API URL |
| `QDRANT_URL` | http://vector-db:6333 | Qdrant URL |
| `FRONTEND_ORIGIN` | http://localhost:3000 | CORS origin |

## Troubleshooting

**Run fails with "no dataset version found"** — register the dataset, then run the ingestion command. The dataset must have a `DatasetVersion` with status `normalized`.

**Index document doesn't work** — ensure `storage_path` starts with `/` (e.g., `/data/pdfs/heart-map.pdf` not `data/pdfs/...`). Indexing runs in the worker container which has `sentence-transformers`.

**Ollama connection refused** — check `OLLAMA_BASE_URL` is set in the service's environment (compose.yml). The backend container needs this env var to proxy Ollama API calls and for the evaluation script.

**LiteLLM authentication fails** — for DeepSeek, the error `governor` means region-locked API key. Ensure the key is from `platform.deepseek.com` (international), not the China-specific platform.

**CORS errors in browser** — restart the backend container after any `main.py` changes. The auth middleware now includes CORS headers on 401/500 responses.
