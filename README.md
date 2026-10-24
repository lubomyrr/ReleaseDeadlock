# ReleaseNotes RAG

RAG API for **Deadlock** patch notes. Ask about updates and get answers with source references.

**Stack:** Python · FastAPI · SQLAlchemy + Alembic · PostgreSQL + pgvector · MiniLM · Ollama (`qwen3.5:4b`)

## Architecture

```text
Patch notes (.md) → chunking → MiniLM embeddings → PostgreSQL + pgvector
                                                        ↑
Question → MiniLM embedding → cosine search (top 3 chunks)
                                                        ↓
                                                Context + sources
                                                        ↓
                                                Ollama → answer
```

## Run locally

Requires **Python 3.11+**, **Docker**, and **Ollama**.
Start Ollama locally on `http://localhost:11434`. MiniLM downloads on first use.

Install Python dependencies from `requirements.txt`:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
ollama pull qwen3.5:4b
```

Create `.env` in the project root:

```dotenv
POSTGRES_PASSWORD=change-me
```

```bash
docker compose up -d
python -m app.init_db
uvicorn app.main:app --reload
```

`app.init_db` applies Alembic migrations and backfills document dates.

In another terminal, upload patch notes:

```bash
python -m scripts.upload_patch
```

API docs: http://127.0.0.1:8000/docs

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Check database connectivity |
| `POST /documents` | Index a document; skip duplicates |
| `GET /search?question=...` | Retrieve relevant chunks |
| `POST /ask` | Generate an answer with sources |

```json
{"question": "What changed about Scrap Grenade damage?"}
```

## Evaluation

**15 labeled questions · Recall@3: 1.00 · MRR@3: 0.889** (locally reported results)

```bash
python -m eval.evaluate
python -m unittest discover -s tests -v
```

## Trade-offs

- **pgvector** stores embeddings and document metadata in PostgreSQL.
- **Local models** avoid paid inference APIs but require local compute.
- Semantic retrieval alone cannot guarantee the latest game-stat value across patches.
