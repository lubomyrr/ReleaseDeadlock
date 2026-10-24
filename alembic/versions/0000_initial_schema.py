"""Create the initial schema, also accepting existing pre-Alembic tables."""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0000_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        if_not_exists=True,
    )
    op.create_table(
        "chunks",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("document_id", sa.UUID(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
        if_not_exists=True,
    )


def downgrade():
    op.drop_table("chunks")
    op.drop_table("documents")
