"""replace is_transfer with categorization_source

Revision ID: f5a6b7c8d9e0
Revises: d2e3f4a5b6c7
Create Date: 2026-04-16

"""
from alembic import op
import sqlalchemy as sa


revision = 'f5a6b7c8d9e0'
down_revision = 'd2e3f4a5b6c7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backfill: existing transfers become categorization_source = 'transfer'
    op.execute(
        "UPDATE transactions SET categorization_source = 'transfer' WHERE is_transfer = true"
    )
    op.drop_index('ix_transactions_is_transfer', table_name='transactions')
    op.drop_column('transactions', 'is_transfer')
    op.create_index(
        'ix_transactions_categorization_source',
        'transactions',
        ['categorization_source'],
    )


def downgrade() -> None:
    op.drop_index('ix_transactions_categorization_source', table_name='transactions')
    op.add_column('transactions', sa.Column('is_transfer', sa.Boolean(), nullable=False, server_default='false'))
    op.execute(
        "UPDATE transactions SET is_transfer = true WHERE categorization_source = 'transfer'"
    )
    op.create_index('ix_transactions_is_transfer', 'transactions', ['is_transfer'])
