"""Store recent conversation turns separately from agent execution state."""

import sqlalchemy as sa
from alembic import op

revision = "0002_chat_turns"
down_revision = "0001_document_patch_date"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "chat_turns",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
    )
    op.create_index("ix_chat_turns_session_id", "chat_turns", ["session_id"])


def downgrade():
    op.drop_table("chat_turns")
