"""Add csv_imports and csv_import_rows tables

Revision ID: v3_001
Revises: v2_001
Create Date: 2026-02-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'v3_001'
down_revision: Union[str, Sequence[str], None] = 'v2_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'csv_imports',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('entity_id', sa.Uuid(), nullable=False),
        sa.Column('exchange', sa.String(50), nullable=False, server_default='binance'),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('row_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('parsed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(20), nullable=False, server_default='uploaded'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], name='fk_csv_imports_entity_id_entities'),
        sa.PrimaryKeyConstraint('id', name='pk_csv_imports'),
    )
    op.create_index('ix_csv_imports_entity_id', 'csv_imports', ['entity_id'])

    op.create_table(
        'csv_import_rows',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('import_id', sa.Uuid(), nullable=False),
        sa.Column('row_number', sa.Integer(), nullable=False),
        sa.Column('utc_time', sa.String(30), nullable=False),
        sa.Column('account', sa.String(50), nullable=False),
        sa.Column('operation', sa.String(100), nullable=False),
        sa.Column('coin', sa.String(20), nullable=False),
        sa.Column('change', sa.String(50), nullable=False),
        sa.Column('remark', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('journal_entry_id', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['import_id'], ['csv_imports.id'], name='fk_csv_import_rows_import_id_csv_imports'),
        sa.ForeignKeyConstraint(['journal_entry_id'], ['journal_entries.id'], name='fk_csv_import_rows_journal_entry_id_journal_entries'),
        sa.PrimaryKeyConstraint('id', name='pk_csv_import_rows'),
    )
    op.create_index('ix_csv_import_rows_import_id', 'csv_import_rows', ['import_id'])
    op.create_index('ix_csv_import_rows_operation', 'csv_import_rows', ['operation'])


def downgrade() -> None:
    op.drop_index('ix_csv_import_rows_operation', 'csv_import_rows')
    op.drop_index('ix_csv_import_rows_import_id', 'csv_import_rows')
    op.drop_table('csv_import_rows')
    op.drop_index('ix_csv_imports_entity_id', 'csv_imports')
    op.drop_table('csv_imports')
