# Changes

## Feedback Resolution Table

| Feedback                                     | Done?   | What was done / Why not                                                                                                         |
| -------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Medical verification/validation              | No      | Requires domain expert + clinical trial data. System is a research prototype.                                                   |
| Architecture diagram focusing on agents      | Yes     | Added Agent Loop (LangGraph) and Data Flow diagrams to README.                                                                  |
| How agents differ from traditional algorithm | Yes     | Documented design invariant: numbers/citations = deterministic; LLM = plan/critique/narrate only.                               |
| Real clinical scenario                       | Yes     | README sections "Workflow" and "Create a Run" describe end-to-end surgical research scenario.                                   |
| Can it be used on patients / emergency?      | No      | Population-level proteomics, not patient-specific. No regulatory approval. Research tool.                                       |
| Add accuracy / model prediction quality      | Partial | Evaluation script (`tests/model_evaluation.py`) measures 7 quality metrics. No ground-truth accuracy — open research question.  |
| Evaluation in the system                     | Yes     | `docker compose exec backend python -m tests.model_evaluation --model X --n-runs N`                                             |
| Caution with results (sensitive domain)      | Yes     | Hallucination score = 0 in evaluation (narrative vs JSON ground truth). LLM cannot change numbers.                              |
| Precision/recall of literature retrieval     | No      | Requires manually annotated ground-truth (protein → PDF page). No labeled dataset exists.                                       |
| Describe problem better for non-biologists   | Yes     | Architecture section in README explains scale mismatch (log2 2-7 vs 20-30) and alignment approach.                              |
| Data flow not clearly explained              | Yes     | Data Flow diagram: placenta.tsv → ingest → alignment → RAG → agent → report.                                                    |
| Trustworthiness of Evidence Agent            | Yes     | Architecture doc: deterministic engine produces all facts; LLM only wraps them. Hallucination impossible for numbers/citations. |
| Bigger dataset / more data                   | No      | `placenta_annotated_forAnalysis.txt` is the complete dataset. New data requires lab experiments.                                |
| Increase data or add more citations          | Yes     | RAG via Qdrant; users can upload multiple PDFs via Document Upload → Index button.                                              |

## Minor Changes

- Dataset auto-ingest on registration (no CLI needed)
- Dataset edit form with full field CRUD
- Delete buttons for datasets + documents with confirmation modal + cascade cleanup
- Document re-index button (enqueues background job)
- LiteLLM integration (Ollama + OpenAI + Anthropic + DeepSeek + Groq + Mistral)
- Model management UI (Pull, Add, Delete with `ollama rm`)
- Per-run model selection + rerun preserves model
- Run error display (red banner with full error message)
- Project-scope validation on all destructive operations (delete/update/index)
- CORS fix: `Origin` header echoed, no `*` with credentials
- HTTP status codes: "not found" → 404, "file not found" → 422
- `api_key_encrypted` → `api_key` (misleading name)
- Pydantic validation on all model routes (replaces raw `dict` params)
- Worker DB connection fix (`POSTGRES_HOST` handling)
- `OLLAMA_BASE_URL` added to backend service
- `langchain-community==0.3.19` pinned
- Pyrefly type errors fixed
- ESLint `react-hooks/set-state-in-effect` resolved
