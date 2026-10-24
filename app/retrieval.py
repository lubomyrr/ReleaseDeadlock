from datetime import date
from typing import NamedTuple

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings import generate_embeddings
from app.models import Chunk, Document


class SearchResult(NamedTuple):
    chunk: Chunk
    filename: str
    distance: float


async def search_chunks(
    question: str,
    session: AsyncSession,
    top_k: int = 3,
    patch_date: date | None = None,
) -> list[SearchResult]:
    if not question.strip():
        raise ValueError("Question must not be empty")
    if top_k < 1:
        raise ValueError("top_k must be positive")

    embeddings = await run_in_threadpool(generate_embeddings, [question])
    question_embedding = embeddings[0]
    stmt = (
        select(
            Chunk,
            Document.filename,
            Chunk.embedding.cosine_distance(question_embedding).label("distance"),
        )
        .join(Document, Chunk.document_id == Document.id)
    )
    if patch_date is not None:
        stmt = stmt.where(Document.patch_date == patch_date)

    stmt = stmt.order_by("distance").limit(top_k)
    result = await session.execute(stmt)
    return [SearchResult(chunk, filename, float(distance)) for chunk, filename, distance in result.all()]
