"""add indexes for Phase 4 parser engine

Revision ID: phase4_001
Revises: phase3_001
Create Date: 2026-02-18

"""
from typing import Sequence, Union

from alembic import op

revision: str = "phase4_001"
down_revision: Union[str, Sequence[str], None] = "phase3_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_accounts_label", "accounts", ["label"], unique=True)
    op.create_index("ix_journal_splits_account_id", "journal_splits", ["account_id"])
    op.create_index("ix_journal_entries_entity_timestamp", "journal_entries", ["entity_id", "timestamp"])
    op.create_index("ix_parse_error_records_error_type", "parse_error_records", ["error_type"])


def downgrade() -> None:
    op.drop_index("ix_parse_error_records_error_type", table_name="parse_error_records")
    op.drop_index("ix_journal_entries_entity_timestamp", table_name="journal_entries")
    op.drop_index("ix_journal_splits_account_id", table_name="journal_splits")
    op.drop_index("ix_accounts_label", table_name="accounts")
