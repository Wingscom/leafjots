"""add last_synced_at to wallets

Revision ID: phase2_001
Revises: 0964d9636ae2
Create Date: 2026-02-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "phase2_001"
down_revision: Union[str, Sequence[str], None] = "0964d9636ae2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("wallets", sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("wallets", "last_synced_at")
