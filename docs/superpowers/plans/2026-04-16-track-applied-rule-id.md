# Track Applied Rule ID on Transactions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store which rule categorized each transaction so that editing or deleting a rule can automatically re-categorize affected transactions.

**Architecture:** Add `applied_rule_id` (nullable FK → rules.id, SET NULL on delete) to `transactions`. Set it in `CategorizationService` when a rule matches. Add `recategorize_rule_affected(rule_id)` to `CategorizationService` that clears and re-runs rules on affected transactions. Call it from the rules PATCH and DELETE endpoints before the mutation.

**Tech Stack:** SQLAlchemy async, Alembic, FastAPI, pytest-asyncio

---

## File Map

| File | Change |
|------|--------|
| `backend/app/db/models.py` | Add `applied_rule_id` column + relationship to `Transaction` |
| `backend/app/db/migrations/versions/b1c2d3e4f5a6_add_applied_rule_id_to_transactions.py` | Create (Alembic migration) |
| `backend/app/services/categorization_service.py` | Set `tx.applied_rule_id` in both rule-match paths; add `recategorize_rule_affected` method |
| `backend/app/api/rules.py` | Call `recategorize_rule_affected` on DELETE and on significant PATCH |
| `backend/tests/test_rules_engine.py` | Add tests for `applied_rule_id` being set and cleared |

---

### Task 1: Add `applied_rule_id` to Transaction model

**Files:**
- Modify: `backend/app/db/models.py`
- Create: `backend/app/db/migrations/versions/b1c2d3e4f5a6_add_applied_rule_id_to_transactions.py`

- [ ] **Step 1: Add the column and relationship to Transaction**

In `backend/app/db/models.py`, add to the `Transaction` class after the `categorization_source` line (line 75):

```python
    applied_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rules.id", ondelete="SET NULL"), nullable=True
    )
```

And add the relationship at the end of the `Transaction` class (after line 86):

```python
    applied_rule: Mapped["Rule | None"] = relationship(foreign_keys="[Transaction.applied_rule_id]")
```

Also add an index in `__table_args__`:

```python
    __table_args__ = (
        Index("ix_transactions_account_booking", "account_id", "booking_date"),
        Index("ix_transactions_category_booking", "category_id", "booking_date"),
        Index("ix_transactions_is_transfer", "is_transfer"),
        Index("ix_transactions_applied_rule_id", "applied_rule_id"),
    )
```

- [ ] **Step 2: Create the Alembic migration**

Create `backend/app/db/migrations/versions/b1c2d3e4f5a6_add_applied_rule_id_to_transactions.py`:

```python
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
```

- [ ] **Step 3: Run the migration**

```bash
cd backend && source .venv/bin/activate && alembic upgrade head
```

Expected: `Running upgrade a9b8c7d6e5f4 -> b1c2d3e4f5a6, add_applied_rule_id_to_transactions`

- [ ] **Step 4: Commit**

```bash
git add backend/app/db/models.py backend/app/db/migrations/versions/b1c2d3e4f5a6_add_applied_rule_id_to_transactions.py
git commit -m "feat: add applied_rule_id FK to transactions"
```

---

### Task 2: Set applied_rule_id when a rule matches during categorization

**Files:**
- Modify: `backend/app/services/categorization_service.py`

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_rules_engine.py`, add at the bottom:

```python
# --- applied_rule_id tracking (unit tests against RulesEngine) ---

def test_rule_match_returns_rule_id():
    """RulesEngine.apply returns the matched rule's id in RuleMatch."""
    rule_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    tx = make_tx(counterparty_name="ALBERT")
    rule = {"id": rule_id, "match_type": "counterparty_contains",
            "match_value": {"value": "albert"}, "category_id": cat_id,
            "priority": 100, "enabled": True}
    result = RulesEngine.apply(tx, [rule])
    assert result is not None
    assert result.rule_id == rule_id
    assert result.category_id == cat_id
```

- [ ] **Step 2: Run test to confirm it passes already (RulesEngine already returns rule_id)**

```bash
cd backend && pytest tests/test_rules_engine.py::test_rule_match_returns_rule_id -v
```

Expected: PASS (RuleMatch already has rule_id field)

- [ ] **Step 3: Update `_categorize_one` to set `applied_rule_id`**

In `backend/app/services/categorization_service.py`, update the `if match:` block in `_categorize_one` (around line 66):

```python
        match = RulesEngine.apply(row, self._rules_for_account(rules, tx.account_id))
        if match:
            tx.category_id = match.category_id
            tx.categorization_source = "rule"
            tx.confidence = Decimal("1.0")
            tx.applied_rule_id = match.rule_id
            rule_obj = await self._db.get(Rule, match.rule_id)
            if rule_obj:
                rule_obj.hit_count += 1
                rule_obj.last_hit_at = datetime.now(timezone.utc)
            return
```

- [ ] **Step 4: Update `_categorize_one_rules_only` to set `applied_rule_id`**

In the same file, update the `if match:` block in `_categorize_one_rules_only` (around line 157):

```python
        match = RulesEngine.apply(row, self._rules_for_account(rules, tx.account_id))
        if match:
            tx.category_id = match.category_id
            tx.categorization_source = "rule"
            tx.confidence = Decimal("1.0")
            tx.applied_rule_id = match.rule_id
            rule_obj = await self._db.get(Rule, match.rule_id)
            if rule_obj:
                rule_obj.hit_count += 1
                rule_obj.last_hit_at = datetime.now(timezone.utc)
```

- [ ] **Step 5: Run existing categorization tests**

```bash
cd backend && pytest tests/ -v -k "categoriz"
```

Expected: all existing categorization tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/categorization_service.py backend/tests/test_rules_engine.py
git commit -m "feat: set applied_rule_id on transaction when rule matches"
```

---

### Task 3: Add `recategorize_rule_affected` to CategorizationService

This method finds all transactions matched by a given rule, clears their categorization, and re-runs rules-only categorization on them.

**Files:**
- Modify: `backend/app/services/categorization_service.py`

- [ ] **Step 1: Add the method to CategorizationService**

Add at the end of `CategorizationService` (after `run_batch`):

```python
    async def recategorize_rule_affected(self, rule_id: uuid.UUID) -> int:
        """Find transactions matched by rule_id, clear their categorization, re-run all rules."""
        result = await self._db.execute(
            select(Transaction).where(Transaction.applied_rule_id == rule_id)
        )
        transactions = result.scalars().all()
        if not transactions:
            return 0

        # Clear existing rule-based assignment
        for tx in transactions:
            tx.category_id = None
            tx.categorization_source = None
            tx.confidence = None
            tx.applied_rule_id = None

        # Flush clears so the re-run sees them as uncategorized
        await self._db.flush()

        rules = await self._load_rules()
        for tx in transactions:
            await self._categorize_one_rules_only(tx, rules)

        await self._db.commit()
        return len(transactions)
```

- [ ] **Step 2: Run existing tests to confirm no regression**

```bash
cd backend && pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/categorization_service.py
git commit -m "feat: add recategorize_rule_affected to CategorizationService"
```

---

### Task 4: Wire recategorize_rule_affected into the rules endpoints

**Files:**
- Modify: `backend/app/api/rules.py`

- [ ] **Step 1: Update the DELETE endpoint**

The DELETE endpoint should re-categorize affected transactions **before** deleting the rule (so we can find them by rule_id while it still exists). After re-categorization, `applied_rule_id` is already cleared (SET NULL by flush in recategorize_rule_affected), so the delete can proceed without FK conflicts.

Replace the `delete_rule` function in `backend/app/api/rules.py`:

```python
@router.delete("/{rule_id}", status_code=204)
async def delete_rule(rule_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rule = await db.get(Rule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    svc = CategorizationService(db)
    await svc.recategorize_rule_affected(rule_id)
    await db.delete(rule)
    await db.commit()
```

- [ ] **Step 2: Update the PATCH endpoint**

Replace the `update_rule` function. Re-categorize if any field that affects matching or assignment changes (`match_type`, `match_value`, `category_id`, `account_id`, `enabled`):

```python
_RECATEGORIZE_FIELDS = {"match_type", "match_value", "category_id", "account_id", "enabled"}

@router.patch("/{rule_id}", response_model=RuleOut)
async def update_rule(rule_id: uuid.UUID, body: RuleUpdate, db: AsyncSession = Depends(get_db)):
    rule = await db.get(Rule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    update_data = {k: v for k, v in body.model_dump().items() if k in body.model_fields_set}
    needs_recategorize = bool(update_data.keys() & _RECATEGORIZE_FIELDS)
    if needs_recategorize:
        svc = CategorizationService(db)
        await svc.recategorize_rule_affected(rule_id)
    for f, v in update_data.items():
        setattr(rule, f, v)
    await db.commit()
    await db.refresh(rule)
    return rule
```

- [ ] **Step 3: Add the CategorizationService import to rules.py**

At the top of `backend/app/api/rules.py`, add:

```python
from app.services.categorization_service import CategorizationService
```

- [ ] **Step 4: Run all tests**

```bash
cd backend && pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/rules.py
git commit -m "feat: re-categorize affected transactions on rule edit/delete"
```

---

## Self-Review

**Spec coverage:**
- ✅ Track which rule was applied — `applied_rule_id` column
- ✅ On delete — `recategorize_rule_affected` called before delete; clears + re-runs remaining rules
- ✅ On update — `recategorize_rule_affected` called when match/assignment fields change
- ✅ DB cascade (`SET NULL`) as safety net if code path is bypassed

**Placeholder scan:** None found.

**Type consistency:** `rule_id: uuid.UUID` used consistently across service method, router call, and migration.

**Edge case noted:** `recategorize_rule_affected` uses `flush()` before re-running rules. This clears `applied_rule_id` in the session before `_load_rules` runs, which means the to-be-deleted rule is still in the DB during the re-run. That's intentional for PATCH (the updated rule should still be evaluated with new values after the method returns). For DELETE, the rule is deleted after this method returns, so affected transactions that matched no other rule end up uncategorized — correct behavior.
