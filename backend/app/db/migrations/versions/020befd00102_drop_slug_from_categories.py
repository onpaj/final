"""drop_slug_from_categories

Revision ID: 020befd00102
Revises: e5f6a7b8c9d0
Create Date: 2026-04-16 09:26:46.216491

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '020befd00102'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE category_groups DROP COLUMN IF EXISTS slug")
    op.create_index('ix_llm_classifications_transaction_id', 'llm_classifications', ['transaction_id'], unique=False, if_not_exists=True)


def downgrade() -> None:
    op.drop_index('ix_llm_classifications_transaction_id', table_name='llm_classifications')
    op.add_column('category_groups', sa.Column('slug', sa.VARCHAR(), autoincrement=False, nullable=True))
