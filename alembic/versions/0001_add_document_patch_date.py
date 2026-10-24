"""Add patch dates to existing documents tables."""

from alembic import op

revision = "0001_document_patch_date"
down_revision = "0000_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS patch_date DATE")


def downgrade():
    op.drop_column("documents", "patch_date")
