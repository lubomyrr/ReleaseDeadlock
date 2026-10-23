from uuid import UUID

from pydantic import BaseModel, Field, field_validator

class DocumentCreate(BaseModel):
    filename: str = Field(min_length=1)
    content: str = Field(min_length=1)
    @field_validator("filename", "content", mode="before")
    @classmethod
    def check_min_length(cls, value: str) -> str:
        if isinstance(value, str) and len(value.strip()) >= 1:
            value = value.strip()
        else:
            raise ValueError("Value must be a non-empty string.")
        return value

class DocumentResponse(BaseModel):
    document_id: UUID
    chunks_created: int
    status: str

class AskRequest(BaseModel):
    question: str

class SourceResponse(BaseModel):
    filename: str
    chunk_id: UUID

class AskResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]
    @field_validator("sources", mode="before")
    @classmethod
    def validate_sources(cls, value: list) -> list:
        if not isinstance(value, list):
            raise ValueError("Sources must be a list.")
        for item in value:
            if not isinstance(item, dict):
                raise ValueError("Each source must be a dictionary.")
            if "filename" not in item or "chunk_id" not in item:
                raise ValueError("Each source must contain 'filename' and 'chunk_id'.")
        return value