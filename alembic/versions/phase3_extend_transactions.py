"""extend transactions with new columns and constraints

Revision ID: phase3_001
Revises: phase2_001
Create Date: 2026-02-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "phase3_001"
down_revision: Union[str, Sequence[str], None] = "phase2_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("timestamp", sa.BigInteger(), nullable=True))
    op.add_column("transactions", sa.Column("from_addr", sa.String(42), nullable=True))
    op.add_column("transactions", sa.Column("to_addr", sa.String(42), nullable=True))
    op.add_column("transactions", sa.Column("value_wei", sa.BigInteger(), nullable=True))
    op.add_column("transactions", sa.Column("gas_used", sa.Integer(), nullable=True))
    op.create_unique_constraint("uq_wallet_tx_hash", "transactions", ["wallet_id", "tx_hash"])
    op.create_index("ix_chain_block_number", "transactions", ["chain", "block_number"])


def downgrade() -> None:
    op.drop_index("ix_chain_block_number", table_name="transactions")
    op.drop_constraint("uq_wallet_tx_hash", "transactions", type_="unique")
    op.drop_column("transactions", "gas_used")
    op.drop_column("transactions", "value_wei")
    op.drop_column("transactions", "to_addr")
    op.drop_column("transactions", "from_addr")
    op.drop_column("transactions", "timestamp")
