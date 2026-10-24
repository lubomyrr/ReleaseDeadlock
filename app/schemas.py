from datetime import date
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DocumentCreate(BaseModel):
    filename: NonEmptyText = Field(max_length=255)
    content: NonEmptyText


class DocumentResponse(BaseModel):
    document_id: UUID
    chunks_created: int
    status: str
    patch_date: date | None = None


class AskRequest(BaseModel):
    question: NonEmptyText


class SourceResponse(BaseModel):
    filename: str
    chunk_id: UUID


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]
