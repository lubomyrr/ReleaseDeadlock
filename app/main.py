from datetime import date
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from ollama import ResponseError
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.ingestion import ingest_document
from app.rag import answer_question
from app.retrieval import search_chunks
from app.schemas import AskRequest, AskResponse, DocumentCreate, DocumentResponse

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
        patch_date=saved_document.patch_date,
    )


@app.get("/search")
async def search(
    question: Annotated[str, Query(min_length=1, pattern=r"\S")],
    session: Annotated[AsyncSession, Depends(get_session)],
    patch_date: date | None = None,
):
    results = await search_chunks(
        question=question,
        session=session,
        top_k=3,
        patch_date=patch_date,
    )

    return [
        {
            "chunk_id": str(item.chunk.id),
            "filename": item.filename,
            "content": item.chunk.content,
            "distance": item.distance,
        }
        for item in results
    ]


@app.post("/ask", response_model=AskResponse)
async def ask(
    request: AskRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        return await answer_question(
            question=request.question,
            session=session,
            top_k=3,
        )
    except (httpx.TimeoutException, TimeoutError) as exc:
        raise HTTPException(status_code=504, detail="Ollama request timed out") from exc
    except (ConnectionError, httpx.RequestError) as exc:
        raise HTTPException(status_code=503, detail="Ollama unavailable") from exc
    except ResponseError as exc:
        detail = "Ollama model unavailable" if exc.status_code == 404 else "Ollama generation failed"
        raise HTTPException(status_code=503, detail=detail) from exc
