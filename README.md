# ReleaseDeadlock

[![CI](https://github.com/lubomyrr/ReleaseDeadlock/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/lubomyrr/ReleaseDeadlock/actions)

A local AI chat for Deadlock patch notes: ask about changes, dates and hero history, with source references and tool traces.

**Stack:** Python 3.11+ · FastAPI · Pydantic · LangGraph · Ollama (`qwen3.5:4b`) · Sentence Transformers (`all-MiniLM-L6-v2`) · LangChain text splitters · PostgreSQL + pgvector · SQLAlchemy · Alembic · HTML/CSS/JavaScript · Docker Compose · GitHub Actions.

## How it works

```text
Markdown patches → heading-aware chunks → MiniLM embeddings → PostgreSQL/pgvector
Question + recent chat history → LangGraph/Ollama → tools → excerpts + sources → answer
```

The model chooses tools automatically, with up to 3 calls and a shared 120-second deadline per question:

| Tool | Purpose |
| --- | --- |
| `search_patch_notes` | Semantic search, up to 3 chunks; optional hero and inclusive date bounds |
| `get_latest_patch` | Date and filenames of the latest loaded patch; no patch body |
| `compare_versions` | Chronological hero excerpts within inclusive dates; not state snapshots |

Tools query the database; Ollama selects calls and writes the answer. Loaded history can be incomplete, and the latest loaded patch does not guarantee current game data.

Chat history is stored in PostgreSQL. Omit `session_id` on the first `/ask` request, then reuse the returned UUID. Each question receives up to 6 previous question/answer pairs, capped at 8,000 characters of complete pairs. A new question has its own 4,000-character limit. Tool results and traces are not retained in history; patch facts must be checked again. **New chat** or a page reload starts a fresh session in the web UI.

## Run locally

Requires Python, Docker Desktop and Ollama. Docker Compose runs PostgreSQL only; Ollama and the API run on the host.

```bash
python -m venv .venv
# PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
ollama pull qwen3.5:4b
```

Set `POSTGRES_PASSWORD` in a local `.env` file, start Ollama on `localhost:11434`, then:

```bash
docker compose up -d db
python -m app.init_db
python -m uvicorn app.main:app --reload
# In another terminal, using the same environment:
python -m scripts.upload_patch
```

`app.init_db` applies migrations. MiniLM downloads on first use. Open the chat at `http://127.0.0.1:8000` or API docs at `/docs`.

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Database connectivity |
| `POST /documents` | Index a document; skip identical content |
| `GET /search?question=...` | Retrieve chunks |
| `POST /ask` | Answer with `sources`, `session_id`, `trace` and `stop_reason` |