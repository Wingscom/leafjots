"""initial_phase1_tables

Revision ID: 0964d9636ae2
Revises:
Create Date: 2026-02-18 02:31:13.790202

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0964d9636ae2"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "entities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("base_currency", sa.String(10), server_default="VND"),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_entities")),
    )

    op.create_table(
        "wallets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("entity_id", sa.Uuid(), sa.ForeignKey("entities.id", name=op.f("fk_wallets_entity_id_entities")), nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("wallet_type", sa.String(50), nullable=False),
        sa.Column("sync_status", sa.String(20), server_default="IDLE"),
        sa.Column("chain", sa.String(20), nullable=True),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column("last_block_loaded", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_wallets")),
    )
    op.create_index(op.f("ix_address"), "wallets", ["address"])

    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("wallet_id", sa.Uuid(), sa.ForeignKey("wallets.id", name=op.f("fk_accounts_wallet_id_wallets")), nullable=False),
        sa.Column("account_type", sa.String(20), nullable=False),
        sa.Column("subtype", sa.String(50), nullable=False),
        sa.Column("symbol", sa.String(50), nullable=True),
        sa.Column("token_address", sa.String(255), nullable=True),
        sa.Column("protocol", sa.String(50), nullable=True),
        sa.Column("balance_type", sa.String(20), nullable=True),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_accounts")),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("wallet_id", sa.Uuid(), sa.ForeignKey("wallets.id", name=op.f("fk_transactions_wallet_id_wallets")), nullable=False),
        sa.Column("chain", sa.String(20), nullable=False),
        sa.Column("tx_hash", sa.String(66), nullable=False),
        sa.Column("block_number", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(20), server_default="LOADED"),
        sa.Column("tx_data", sa.Text(), nullable=True),
        sa.Column("entry_type", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transactions")),
    )
    op.create_index(op.f("ix_tx_hash"), "transactions", ["tx_hash"])

    op.create_table(
        "journal_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("entity_id", sa.Uuid(), sa.ForeignKey("entities.id", name=op.f("fk_journal_entries_entity_id_entities")), nullable=False),
        sa.Column("transaction_id", sa.BigInteger(), sa.ForeignKey("transactions.id", name=op.f("fk_journal_entries_transaction_id_transactions")), nullable=True),
        sa.Column("entry_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journal_entries")),
    )

    op.create_table(
        "journal_splits",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("journal_entry_id", sa.Uuid(), sa.ForeignKey("journal_entries.id", name=op.f("fk_journal_splits_journal_entry_id_journal_entries")), nullable=False),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("accounts.id", name=op.f("fk_journal_splits_account_id_accounts")), nullable=False),
        sa.Column("quantity", sa.Numeric(38, 18), nullable=False),
        sa.Column("value_usd", sa.Numeric(20, 4), nullable=True),
        sa.Column("value_vnd", sa.Numeric(24, 0), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journal_splits")),
    )

    op.create_table(
        "parse_error_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("transaction_id", sa.BigInteger(), sa.ForeignKey("transactions.id", name=op.f("fk_parse_error_records_transaction_id_transactions")), nullable=True),
        sa.Column("wallet_id", sa.Uuid(), sa.ForeignKey("wallets.id", name=op.f("fk_parse_error_records_wallet_id_wallets")), nullable=True),
        sa.Column("error_type", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("stack_trace", sa.Text(), nullable=True),
        sa.Column("resolved", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_parse_error_records")),
    )


def downgrade() -> None:
    op.drop_table("parse_error_records")
    op.drop_table("journal_splits")
    op.drop_table("journal_entries")
    op.drop_index(op.f("ix_tx_hash"), table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("accounts")
    op.drop_index(op.f("ix_address"), table_name="wallets")
    op.drop_table("wallets")
    op.drop_table("entities")
