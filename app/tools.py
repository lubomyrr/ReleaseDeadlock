import re
from datetime import date

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.embeddings import generate_embeddings
from app.models import Chunk, Document


async def search_patch_notes(
    query: str,
    hero: str | None = None,
    date_from: str | date | None = None,
    date_to: str | date | None = None,
) -> dict:
    """Search up to three chunks. Dates are inclusive and accept ISO dates.

    Hero matching includes the section headings preserved during ingestion.
    Existing documents must be reindexed after changing the chunking strategy.
    """
    result = {
        "data": [],
        "sources": [],
        "coverage": {
            "limit": 3,
            "truncated": False,
            "hero_matching": "section headings and chunk text",
            "undated_documents_excluded_when_filtering_dates": True,
        },
        "errors": [],
    }

    if not isinstance(query, str) or not query.strip():
        result["errors"].append({"code": "invalid_query", "message": "query must not be empty"})
        return result
    if hero is not None and (not isinstance(hero, str) or not hero.strip()):
        result["errors"].append({"code": "invalid_hero", "message": "hero must be a non-empty string or None"})
        return result

    try:
        def parse_date(value):
            if value is None:
                return None
            if isinstance(value, str):
                return date.fromisoformat(value)
            if type(value) is date:
                return value
            raise ValueError("expected an ISO date or date object")

        start, end = parse_date(date_from), parse_date(date_to)
        if start and end and start > end:
            raise ValueError("date_from must not be later than date_to")
    except ValueError as exc:
        result["errors"].append({"code": "invalid_date", "message": str(exc)})
        return result

    try:
        embedding = (await run_in_threadpool(generate_embeddings, [query.strip()]))[0]
    except Exception:
        result["errors"].append({"code": "embedding_unavailable", "message": "Could not generate query embedding"})
        return result

    try:
        # Import lazily so invalid inputs do not require database configuration.
        from app.database import SessionLocal

        distance = Chunk.embedding.cosine_distance(embedding).label("distance")
        stmt = select(Chunk, Document, distance).join(Document, Chunk.document_id == Document.id)
        if hero:
            # PostgreSQL regex word boundaries prevent partial-name matches.
            pattern = r"(^|[^[:alnum:]_])" + re.escape(hero.strip()) + r"([^[:alnum:]_]|$)"
            stmt = stmt.where(Chunk.content.op("~*")(pattern))
        if start:
            stmt = stmt.where(Document.patch_date >= start)
        if end:
            stmt = stmt.where(Document.patch_date <= end)
        stmt = stmt.order_by(distance, Chunk.id).limit(4)

        async with SessionLocal() as session:
            rows = (await session.execute(stmt)).all()

        result["coverage"]["truncated"] = len(rows) > 3
        for chunk, document, score in rows[:3]:
            source = {
                "chunk_id": str(chunk.id),
                "document_id": str(document.id),
                "filename": document.filename,
                "patch_date": document.patch_date.isoformat() if document.patch_date else None,
                "chunk_index": chunk.chunk_index,
            }
            result["sources"].append(source)
            result["data"].append({"content": chunk.content, "distance": float(score), "source": source})
    except (SQLAlchemyError, OSError, TimeoutError, KeyError):
        result["errors"].append({"code": "database_unavailable", "message": "Database is unavailable or not configured"})

    return result


async def get_latest_patch() -> dict:
    """Return all loaded documents on the latest known patch date."""
    result = {"data": [], "sources": [], "coverage": {"freshness": "unknown"}, "errors": []}
    try:
        from app.database import SessionLocal

        async with SessionLocal() as session:
            latest = await session.scalar(select(Document.patch_date).where(
                Document.patch_date.is_not(None)
            ).order_by(Document.patch_date.desc()).limit(1))
            if latest is not None:
                documents = (await session.scalars(select(Document).where(
                    Document.patch_date == latest
                ).order_by(Document.filename, Document.id))).all()
                result["data"] = [
                    {"document_id": str(doc.id), "filename": doc.filename, "patch_date": latest.isoformat()}
                    for doc in documents
                ]
                result["sources"] = result["data"].copy()
    except (SQLAlchemyError, OSError, TimeoutError, KeyError):
        result["errors"].append({"code": "database_unavailable", "message": "Database is unavailable or not configured"})
    return result


async def compare_versions(hero: str, date_from: str, date_to: str) -> dict:
    """Collect matching excerpts in an inclusive interval, not hero snapshots."""
    result = {
        "data": [], "sources": [],
        "coverage": {
            "truncated": False,
            "complete_history": "unknown",
            "undated_documents_excluded": True,
            "matching": "hero name in chunk text or section heading",
        },
        "errors": [],
    }
    if not isinstance(hero, str) or not hero.strip():
        result["errors"].append({"code": "invalid_hero", "message": "hero must not be empty"})
        return result
    try:
        start, end = date.fromisoformat(date_from), date.fromisoformat(date_to)
        if start > end:
            raise ValueError("date_from must not be later than date_to")
    except (TypeError, ValueError) as exc:
        result["errors"].append({"code": "invalid_date", "message": str(exc)})
        return result

    try:
        from app.database import SessionLocal

        pattern = r"(^|[^[:alnum:]_])" + re.escape(hero.strip()) + r"([^[:alnum:]_]|$)"
        stmt = (
            select(Chunk, Document).join(Document, Chunk.document_id == Document.id)
            .where(Document.patch_date >= start, Document.patch_date <= end, Chunk.content.op("~*")(pattern))
            .order_by(Document.patch_date, Document.filename, Document.id, Chunk.chunk_index)
        )
        async with SessionLocal() as session:
            rows = (await session.execute(stmt)).all()
        for chunk, document in rows:
            source = {
                "chunk_id": str(chunk.id), "document_id": str(document.id),
                "filename": document.filename, "patch_date": document.patch_date.isoformat(),
                "chunk_index": chunk.chunk_index,
            }
            result["sources"].append(source)
            result["data"].append({"content": chunk.content, "source": source})
    except (SQLAlchemyError, OSError, TimeoutError, KeyError):
        result["errors"].append({"code": "database_unavailable", "message": "Database is unavailable or not configured"})
    return result
