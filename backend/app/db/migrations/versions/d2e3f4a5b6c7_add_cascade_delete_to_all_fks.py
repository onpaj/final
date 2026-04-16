"""add_cascade_delete_to_all_fks

Revision ID: d2e3f4a5b6c7
Revises: b1c2d3e4f5a6
Create Date: 2026-04-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'd2e3f4a5b6c7'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # import_batches.account_id -> accounts.id
    op.drop_constraint('import_batches_account_id_fkey', 'import_batches', type_='foreignkey')
    op.create_foreign_key(
        'import_batches_account_id_fkey', 'import_batches', 'accounts',
        ['account_id'], ['id'], ondelete='CASCADE'
    )

    # transactions.account_id -> accounts.id
    op.drop_constraint('transactions_account_id_fkey', 'transactions', type_='foreignkey')
    op.create_foreign_key(
        'transactions_account_id_fkey', 'transactions', 'accounts',
        ['account_id'], ['id'], ondelete='CASCADE'
    )

    # transactions.import_batch_id -> import_batches.id
    op.drop_constraint('transactions_import_batch_id_fkey', 'transactions', type_='foreignkey')
    op.create_foreign_key(
        'transactions_import_batch_id_fkey', 'transactions', 'import_batches',
        ['import_batch_id'], ['id'], ondelete='CASCADE'
    )

    # transactions.category_id -> categories.id
    op.drop_constraint('fk_transactions_category_id', 'transactions', type_='foreignkey')
    op.create_foreign_key(
        'fk_transactions_category_id', 'transactions', 'categories',
        ['category_id'], ['id'], ondelete='CASCADE'
    )

    # transactions.applied_rule_id -> rules.id (was SET NULL)
    op.drop_constraint('fk_transactions_applied_rule_id', 'transactions', type_='foreignkey')
    op.create_foreign_key(
        'fk_transactions_applied_rule_id', 'transactions', 'rules',
        ['applied_rule_id'], ['id'], ondelete='CASCADE'
    )

    # categories.group_id -> category_groups.id
    op.drop_constraint('categories_group_id_fkey', 'categories', type_='foreignkey')
    op.create_foreign_key(
        'categories_group_id_fkey', 'categories', 'category_groups',
        ['group_id'], ['id'], ondelete='CASCADE'
    )

    # rules.category_id -> categories.id
    op.drop_constraint('rules_category_id_fkey', 'rules', type_='foreignkey')
    op.create_foreign_key(
        'rules_category_id_fkey', 'rules', 'categories',
        ['category_id'], ['id'], ondelete='CASCADE'
    )

    # rules.account_id -> accounts.id
    op.drop_constraint('fk_rules_account_id', 'rules', type_='foreignkey')
    op.create_foreign_key(
        'fk_rules_account_id', 'rules', 'accounts',
        ['account_id'], ['id'], ondelete='CASCADE'
    )

    # llm_classifications.transaction_id -> transactions.id
    op.drop_constraint('llm_classifications_transaction_id_fkey', 'llm_classifications', type_='foreignkey')
    op.create_foreign_key(
        'llm_classifications_transaction_id_fkey', 'llm_classifications', 'transactions',
        ['transaction_id'], ['id'], ondelete='CASCADE'
    )

    # llm_classifications.suggested_category_id -> categories.id
    op.drop_constraint('llm_classifications_suggested_category_id_fkey', 'llm_classifications', type_='foreignkey')
    op.create_foreign_key(
        'llm_classifications_suggested_category_id_fkey', 'llm_classifications', 'categories',
        ['suggested_category_id'], ['id'], ondelete='CASCADE'
    )


def downgrade() -> None:
    op.drop_constraint('llm_classifications_suggested_category_id_fkey', 'llm_classifications', type_='foreignkey')
    op.create_foreign_key(
        'llm_classifications_suggested_category_id_fkey', 'llm_classifications', 'categories',
        ['suggested_category_id'], ['id']
    )

    op.drop_constraint('llm_classifications_transaction_id_fkey', 'llm_classifications', type_='foreignkey')
    op.create_foreign_key(
        'llm_classifications_transaction_id_fkey', 'llm_classifications', 'transactions',
        ['transaction_id'], ['id']
    )

    op.drop_constraint('fk_rules_account_id', 'rules', type_='foreignkey')
    op.create_foreign_key(
        'fk_rules_account_id', 'rules', 'accounts',
        ['account_id'], ['id']
    )

    op.drop_constraint('rules_category_id_fkey', 'rules', type_='foreignkey')
    op.create_foreign_key(
        'rules_category_id_fkey', 'rules', 'categories',
        ['category_id'], ['id']
    )

    op.drop_constraint('categories_group_id_fkey', 'categories', type_='foreignkey')
    op.create_foreign_key(
        'categories_group_id_fkey', 'categories', 'category_groups',
        ['group_id'], ['id']
    )

    op.drop_constraint('fk_transactions_applied_rule_id', 'transactions', type_='foreignkey')
    op.create_foreign_key(
        'fk_transactions_applied_rule_id', 'transactions', 'rules',
        ['applied_rule_id'], ['id'], ondelete='SET NULL'
    )

    op.drop_constraint('fk_transactions_category_id', 'transactions', type_='foreignkey')
    op.create_foreign_key(
        'fk_transactions_category_id', 'transactions', 'categories',
        ['category_id'], ['id']
    )

    op.drop_constraint('transactions_import_batch_id_fkey', 'transactions', type_='foreignkey')
    op.create_foreign_key(
        'transactions_import_batch_id_fkey', 'transactions', 'import_batches',
        ['import_batch_id'], ['id']
    )

    op.drop_constraint('transactions_account_id_fkey', 'transactions', type_='foreignkey')
    op.create_foreign_key(
        'transactions_account_id_fkey', 'transactions', 'accounts',
        ['account_id'], ['id']
    )

    op.drop_constraint('import_batches_account_id_fkey', 'import_batches', type_='foreignkey')
    op.create_foreign_key(
        'import_batches_account_id_fkey', 'import_batches', 'accounts',
        ['account_id'], ['id']
    )
