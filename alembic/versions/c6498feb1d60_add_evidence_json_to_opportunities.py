"""add evidence_json to opportunities

Revision ID: c6498feb1d60
Revises: 7a6f2063731a
Create Date: 2026-05-05 23:03:23.523710

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c6498feb1d60'
down_revision: str | Sequence[str] | None = '7a6f2063731a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "opportunities",
        sa.Column("evidence_json", sa.Text(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("opportunities", "evidence_json")
