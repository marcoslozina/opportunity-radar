"""add_tier_quota_to_api_keys

Revision ID: a1b2c3d4e5f6
Revises: 7a6f2063731a
Create Date: 2026-05-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "7a6f2063731a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tier, monthly_quota_used, and quota_reset_at to api_keys."""
    op.add_column(
        "api_keys",
        sa.Column("tier", sa.String(50), nullable=False, server_default="starter"),
    )
    op.add_column(
        "api_keys",
        sa.Column("monthly_quota_used", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "api_keys",
        sa.Column("quota_reset_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    """Remove tier, monthly_quota_used, and quota_reset_at from api_keys."""
    op.drop_column("api_keys", "quota_reset_at")
    op.drop_column("api_keys", "monthly_quota_used")
    op.drop_column("api_keys", "tier")
