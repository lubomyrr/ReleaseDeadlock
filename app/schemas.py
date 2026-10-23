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