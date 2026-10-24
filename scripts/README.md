# Download patch notes as Markdown

Run from the project root with Python 3.10+:

```powershell
python -m pip install -r scripts/requirements-patch.txt
python scripts/fetch_patch.py "https://deadlock.wiki/Update:October_20,_2026"
```

The default output is `data/raw/patch_2026_10_20.md`. The date comes from the URL.
The script preserves article headings, paragraphs, tables, nested lists,
and Unicode symbols. Site navigation, the table of contents, edit controls,
categories, decorative icons, and Wiki/Source metadata are removed. Links are
converted to their visible text without URLs. No LLM or database is required.

Choose a different output path or explicitly replace a saved file:

```powershell
python scripts/fetch_patch.py "https://deadlock.wiki/Update:October_20,_2026" -o data/raw/october_20.md
python scripts/fetch_patch.py "https://deadlock.wiki/Update:October_20,_2026" --overwrite
```

The command only downloads Markdown; it does not upload it into the RAG database.

To upload all `data/raw/patch_*.md` files in filename order, start the API in one terminal
and run the uploader in another:

```powershell
python -m uvicorn app.main:app --reload
# In another terminal:
python -m scripts.upload_patch
```

The uploader prints one line per file: `filename | HTTP status | chunks_created=N`.
An existing document returns `200` and zero new chunks; a new document returns `201`.
Duplicate detection uses document content, not the filename.

Before using the API with patch dates, initialize or update the database:

```powershell
python -m app.init_db
```

This adds the nullable `documents.patch_date` column if needed and fills missing
dates from existing filenames. New documents extract dates automatically:
`patch_2026_10_20.md` becomes `2026-10-20`. Invalid names or dates produce `null`.
The `POST /documents` response includes `patch_date`.

`init_db` runs versioned Alembic migrations and backfills missing document dates.
For schema changes only, run `python -m alembic upgrade head` from the project root.
Both commands support a new database and existing pre-Alembic tables.

Run the automated tests without running Ollama or PostgreSQL
(Python dependencies and `.env` must be configured):

```powershell
python -m unittest discover -s tests -v
```
