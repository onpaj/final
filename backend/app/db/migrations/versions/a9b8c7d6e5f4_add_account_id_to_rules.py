"""add_account_id_to_rules

Revision ID: a9b8c7d6e5f4
Revises: 020befd00102
Create Date: 2026-04-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'a9b8c7d6e5f4'
down_revision: Union[str, None] = '020befd00102'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'rules',
        sa.Column('account_id', UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_rules_account_id', 'rules', 'accounts', ['account_id'], ['id']
    )
    op.create_index('ix_rules_account_id', 'rules', ['account_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_rules_account_id', table_name='rules')
    op.drop_constraint('fk_rules_account_id', 'rules', type_='foreignkey')
    op.drop_column('rules', 'account_id')
