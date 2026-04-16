"""add_applied_rule_id_to_transactions

Revision ID: b1c2d3e4f5a6
Revises: a9b8c7d6e5f4
Create Date: 2026-04-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'a9b8c7d6e5f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'transactions',
        sa.Column('applied_rule_id', UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_transactions_applied_rule_id', 'transactions', 'rules',
        ['applied_rule_id'], ['id'], ondelete='SET NULL'
    )
    op.create_index('ix_transactions_applied_rule_id', 'transactions', ['applied_rule_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_transactions_applied_rule_id', table_name='transactions')
    op.drop_constraint('fk_transactions_applied_rule_id', 'transactions', type_='foreignkey')
    op.drop_column('transactions', 'applied_rule_id')
