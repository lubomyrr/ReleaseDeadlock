import hashlib
import re
from datetime import date, datetime
from pathlib import Path

from fastapi.concurrency import run_in_threadpool
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings import generate_embeddings
from app.models import Chunk, Document


def extract_patch_date(filename: str) -> date | None:
    stem = Path(filename).stem
    if not re.fullmatch(r"patch_\d{4}_\d{2}_\d{2}", stem):
        return None
    try:
        return datetime.strptime(stem, "patch_%Y_%m_%d").date()
    except ValueError:
        return None


def hash_document(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def split_document(content: str) -> list[str]:
    # Older wiki exports use a plain-text table of contents instead of Markdown.
    heroes = re.findall(r"^\d+\.\d+\t(.+)$", content, re.MULTILINE)
    if heroes and "\nGeneral\n" in content:
        content = "## General\n" + content.split("\nGeneral\n", 1)[1]
        for heading in ["Heroes", *heroes]:
            level = "##" if heading == "Heroes" else "###"
            content = re.sub(rf"(?m)^[ \t]*{re.escape(heading)}[ \t]*$", f"{level} {heading}", content)

    sections = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "title"), ("##", "section"), ("###", "subject"), ("####", "ability")],
    ).split_text(content)
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=75)
    return [
        "\n\n".join(filter(None, (" > ".join(section.metadata.values()), chunk)))
        for section in sections
        for chunk in splitter.split_text(section.page_content)
    ]


async def ingest_document(
    filename: str,
    content: str,
    session: AsyncSession,
    *,
    reindex: bool = False,
) -> tuple[Document, int]:
    content_hash = hash_document(content)
    statement = select(Document).where(
        Document.filename == filename if reindex else Document.content_hash == content_hash
    )
    try:
        existing_document = await session.scalar(statement)
        if existing_document is not None and not reindex:
            return existing_document, 0

        chunks = split_document(content)
        embeddings = await run_in_threadpool(generate_embeddings, chunks)
        if len(embeddings) != len(chunks) or any(len(vector) != 384 for vector in embeddings):
            raise ValueError("Expected one 384-dimensional embedding per chunk")

        document = existing_document or Document(
            filename=filename,
            content_hash=content_hash,
            patch_date=extract_patch_date(filename),
        )
        if existing_document is not None:
            document.content_hash = content_hash
            document.patch_date = extract_patch_date(filename)
            await session.execute(delete(Chunk).where(Chunk.document_id == document.id))
            await session.refresh(document, ["chunks"])
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
        if reindex:
            raise
        existing_document = await session.scalar(statement)
        if existing_document is not None:
            return existing_document, 0
        raise
    except Exception:
        await session.rollback()
        raise
