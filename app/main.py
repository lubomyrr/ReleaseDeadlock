from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.ingestion import ingest_document
from app.schemas import DocumentCreate, DocumentResponse
from app.retrieval import search_chunks

app = FastAPI()

class HealthCheck(BaseModel):
    status: str = "ok"

@app.get("/health", status_code=200, response_model=HealthCheck)
async def health_check(session: Annotated[AsyncSession, Depends(get_session)]):
    try:
        await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail="PostgreSQL unavailable") from exc
    return HealthCheck(status="ok")

@app.post("/documents", status_code=201, response_model=DocumentResponse)
async def create_document(
    document: DocumentCreate,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    saved_document, chunks_created = await ingest_document(
        filename=document.filename,
        content=document.content,
        session=session,
    )
    if chunks_created == 0:
        response.status_code = 200
    return DocumentResponse(
        document_id=saved_document.id,
        chunks_created=chunks_created,
        status="indexed" if chunks_created else "already_exists",
    )


@app.get("/search")
async def search(
    question: str,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    chunks = await search_chunks(
        question=question,
        session=session,
        top_k=3,
    )

    return [
        {
            "chunk_id": str(result.chunk.id),
            "content": result.chunk.content,
            "filename": result.filename,
            "distance": result.distance,
        }
        for result in chunks
    ]
