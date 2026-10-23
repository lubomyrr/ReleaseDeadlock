import hashlib

from fastapi.concurrency import run_in_threadpool
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings import generate_embeddings
from app.models import Chunk, Document


def hash_document(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def split_document(content: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=75)
    return splitter.split_text(content)


async def ingest_document(
    filename: str,
    content: str,
    session: AsyncSession,
) -> tuple[Document, int]:
    content_hash = hash_document(content)
    statement = select(Document).where(Document.content_hash == content_hash)
    try:
        existing_document = await session.scalar(statement)
        if existing_document is not None:
            return existing_document, 0

        chunks = split_document(content)
        embeddings = await run_in_threadpool(generate_embeddings, chunks)
        if len(embeddings) != len(chunks) or any(len(vector) != 384 for vector in embeddings):
            raise ValueError("Expected one 384-dimensional embedding per chunk")

        document = Document(filename=filename, content_hash=content_hash)
        document.chunks = [
            Chunk(chunk_index=index, content=chunk, embedding=embedding)
            for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
        ]
        session.add(document)
        await session.commit()
        return document, len(chunks)
    except IntegrityError:
        # A concurrent request may have committed the same content first.
        await session.rollback()
        existing_document = await session.scalar(statement)
        if existing_document is not None:
            return existing_document, 0
        raise
    except Exception:
        await session.rollback()
        raise
