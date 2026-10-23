import datetime
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
    DateTime(timezone=True),
    server_default=func.now()
)
    chunks: Mapped[list["Chunk"]] = relationship(
    back_populates="document",
    cascade="all, delete-orphan"
)

class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    chunk_index: Mapped[int] = mapped_column()
    content: Mapped[str] = mapped_column(Text)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"))
    document: Mapped["Document"] = relationship(
    back_populates="chunks"
)
    embedding: Mapped[list[float]] = mapped_column(Vector(384))
    __table_args__ = (
    UniqueConstraint(
        "document_id",
        "chunk_index",
        name="uq_document_chunk_index"
    ),
)