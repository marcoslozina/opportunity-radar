"""add_index_briefings_niche_generated

Revision ID: fde41ad10e32
Revises: c8159f408a34
Create Date: 2026-05-05 23:02:51.134161

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'fde41ad10e32'
down_revision: str | Sequence[str] | None = 'c8159f408a34'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_briefings_niche_generated",
        "briefings",
        ["niche_id", "generated_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_briefings_niche_generated", table_name="briefings")
