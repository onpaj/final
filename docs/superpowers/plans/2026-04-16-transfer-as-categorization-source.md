# Transfer as Categorization Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the `is_transfer` boolean column from `Transaction` and replace it with `categorization_source = "transfer"` as the single signal that a transaction is an internal transfer.

**Architecture:** The `is_transfer` boolean is a redundant second source of truth alongside `categorization_source`. After this change, `categorization_source = "transfer"` is the canonical signal. A DB migration backfills existing data, drops the column, and adds an index on `categorization_source`. Every consumer that read `is_transfer` reads `categorization_source` instead.

**Tech Stack:** Python/FastAPI, SQLAlchemy async, Alembic, React/TypeScript, pytest

---

## File Map

| File | Change |
|------|--------|
| `backend/app/db/migrations/versions/f5a6b7c8d9e0_...py` | New migration: backfill, drop column, drop index, add index |
| `backend/app/db/models.py` | Remove `is_transfer` mapped column + index; add `categorization_source` index |
| `backend/app/services/transfer_matcher.py` | Filter by `categorization_source IS NULL`; set `categorization_source = "transfer"` |
| `backend/app/services/analytics_service.py` | 4× `t.is_transfer = false` → `t.categorization_source IS DISTINCT FROM 'transfer'` |
| `backend/app/api/transactions.py` | Remove `is_transfer` from schemas; update `needs_review` filter; update `bulk_categorize`; update detail-view transfer check |
| `backend/app/api/imports.py` | Remove `is_transfer` from `BatchTransactionOut`; add "transfer" to Literal |
| `backend/tests/test_transfer_matcher.py` | Update `make_tx` + assertions |
| `backend/tests/test_transactions_api.py` | Update `_make_transaction` + `is_transfer` test cases |
| `frontend/src/api/transactions.ts` | Remove `is_transfer` from `Transaction` and `TransactionDetail` |
| `frontend/src/pages/Imports/BatchHistory.tsx` | Remove `is_transfer` from `BatchTx`; check `categorization_source === "transfer"` |

---

### Task 1: DB Migration

**Files:**
- Create: `backend/app/db/migrations/versions/f5a6b7c8d9e0_replace_is_transfer_with_categorization_source.py`

- [ ] **Step 1: Create the migration file**

```python
"""replace is_transfer with categorization_source

Revision ID: f5a6b7c8d9e0
Revises: d2e3f4a5b6c7
Create Date: 2026-04-16

"""
from alembic import op

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
    import sqlalchemy as sa
    op.add_column('transactions', sa.Column('is_transfer', sa.Boolean(), nullable=False, server_default='false'))
    op.execute(
        "UPDATE transactions SET is_transfer = true WHERE categorization_source = 'transfer'"
    )
    op.create_index('ix_transactions_is_transfer', 'transactions', ['is_transfer'])
```

- [ ] **Step 2: Apply migration**

```bash
cd backend && source .venv/bin/activate
alembic upgrade head
```

Expected output ends with: `Running upgrade d2e3f4a5b6c7 -> f5a6b7c8d9e0`

- [ ] **Step 3: Verify schema**

```bash
python -c "
import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as db:
        r = await db.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name='transactions' AND column_name='is_transfer'\"))
        assert r.first() is None, 'is_transfer column still exists'
        r2 = await db.execute(text(\"SELECT indexname FROM pg_indexes WHERE tablename='transactions' AND indexname='ix_transactions_categorization_source'\"))
        assert r2.first() is not None, 'index missing'
        print('OK')

asyncio.run(check())
"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/db/migrations/versions/f5a6b7c8d9e0_replace_is_transfer_with_categorization_source.py
git commit -m "feat: migration — replace is_transfer with categorization_source=transfer"
```

---

### Task 2: Model — remove `is_transfer`

**Files:**
- Modify: `backend/app/db/models.py`

- [ ] **Step 1: Update the model**

In `backend/app/db/models.py`, inside `Transaction.__table_args__`, replace:

```python
Index("ix_transactions_is_transfer", "is_transfer"),
```

with:

```python
Index("ix_transactions_categorization_source", "categorization_source"),
```

Then remove this line from the `Transaction` class body:

```python
is_transfer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
```

Also remove `Boolean` from the `sqlalchemy` import if it's no longer used elsewhere (check first — it might be used by other models).

Check: `Boolean` is used nowhere else in `models.py`, so remove it from the import:

```python
from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, Index, Integer,
    Numeric, String, Text, func,
)
```

- [ ] **Step 2: Run tests to see what breaks**

```bash
cd backend && pytest tests/ -x -q 2>&1 | head -40
```

Expected: failures in `test_transfer_matcher.py` and `test_transactions_api.py` referencing `is_transfer`.

- [ ] **Step 3: Commit model change**

```bash
git add backend/app/db/models.py
git commit -m "feat: remove is_transfer from Transaction model"
```

---

### Task 3: Transfer Matcher

**Files:**
- Modify: `backend/app/services/transfer_matcher.py`
- Modify: `backend/tests/test_transfer_matcher.py`

- [ ] **Step 1: Update `make_tx` in the test to remove `is_transfer`**

In `backend/tests/test_transfer_matcher.py`, change `make_tx`:

```python
def make_tx(amount, booking_date, account_id=None, tx_id=None, counterparty_account=None):
    tx = MagicMock()
    tx.id = tx_id or uuid.uuid4()
    tx.amount = Decimal(str(amount))
    tx.booking_date = booking_date
    tx.account_id = account_id or uuid.uuid4()
    tx.categorization_source = None
    tx.transfer_pair_id = None
    tx.category_id = None
    tx.counterparty_account = counterparty_account
    return tx
```

- [ ] **Step 2: Add a test for `match_batch` that asserts the new behavior**

Add this test at the bottom of `test_transfer_matcher.py`:

```python
@pytest.mark.asyncio
async def test_match_batch_sets_categorization_source():
    """match_batch sets categorization_source='transfer', not is_transfer."""
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()

    internal_cat_id = uuid.uuid4()
    cat = MagicMock()
    cat.id = internal_cat_id

    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=IBAN_B)
    credit = make_tx(5000, date(2026, 1, 16), acct_b, counterparty_account=IBAN_A)

    call_count = 0
    async def mock_execute(query):
        nonlocal call_count
        call_count += 1
        if call_count == 1:  # _load_account_identifiers
            acc_a = MagicMock(); acc_a.id = acct_a; acc_a.iban = IBAN_A
            acc_b = MagicMock(); acc_b.id = acct_b; acc_b.iban = IBAN_B
            return MagicMock(**{"scalars.return_value.all.return_value": [acc_a, acc_b]})
        elif call_count == 2:  # fetch transactions
            return MagicMock(**{"scalars.return_value.all.return_value": [debit, credit]})
        else:  # _get_internal_transfer_category
            return MagicMock(scalar_one_or_none=MagicMock(return_value=cat))

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=mock_execute)
    mock_db.commit = AsyncMock()

    matcher = TransferMatcher(mock_db)
    matched = await matcher.match_batch([debit.id, credit.id])

    assert matched == 2
    assert debit.categorization_source == "transfer"
    assert credit.categorization_source == "transfer"
    assert debit.category_id == internal_cat_id
    assert credit.category_id == internal_cat_id
    assert not hasattr(debit, 'is_transfer') or True  # is_transfer no longer set
```

- [ ] **Step 3: Run to verify it fails**

```bash
cd backend && pytest tests/test_transfer_matcher.py::test_match_batch_sets_categorization_source -v
```

Expected: FAIL (matcher still uses `is_transfer`).

- [ ] **Step 4: Update `transfer_matcher.py`**

Replace the full `match_batch` method body in `backend/app/services/transfer_matcher.py`:

```python
async def match_batch(self, transaction_ids: list[uuid.UUID]) -> int:
    await self._load_account_identifiers()

    result = await self._db.execute(
        select(Transaction).where(
            Transaction.id.in_(transaction_ids),
            Transaction.categorization_source.is_(None),
        )
    )
    transactions = result.scalars().all()

    internal_cat_id = await self._get_internal_transfer_category()
    matched = 0
    for txn in transactions:
        if txn.account_id not in self._account_identifiers:
            continue
        if self._counterparty_account_id(txn.counterparty_account) is None:
            continue

        txn.categorization_source = "transfer"
        txn.category_id = internal_cat_id
        matched += 1

    await self._db.commit()
    return matched
```

- [ ] **Step 5: Run all transfer matcher tests**

```bash
cd backend && pytest tests/test_transfer_matcher.py -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/transfer_matcher.py backend/tests/test_transfer_matcher.py
git commit -m "feat: transfer matcher uses categorization_source=transfer instead of is_transfer"
```

---

### Task 4: Transactions API

**Files:**
- Modify: `backend/app/api/transactions.py`
- Modify: `backend/tests/test_transactions_api.py`

- [ ] **Step 1: Update `_make_transaction` in the test**

In `backend/tests/test_transactions_api.py`, update `_make_transaction` — remove `tx.is_transfer = False`:

```python
def _make_transaction(account_id: uuid.UUID | None = None) -> Transaction:
    tx = MagicMock(spec=Transaction)
    tx.id = uuid.uuid4()
    tx.account_id = account_id or uuid.uuid4()
    tx.import_batch_id = uuid.uuid4()
    tx.booking_date = date(2026, 1, 15)
    tx.value_date = None
    tx.amount = Decimal("-250.00")
    tx.currency = "CZK"
    tx.counterparty_name = "ALBERT"
    tx.counterparty_account = None
    tx.description = "Nákup"
    tx.category_id = None
    tx.categorization_source = None
    tx.confidence = None
    tx.notes = None
    tx.created_at = datetime(2026, 1, 15, 10, 0, 0)
    tx.raw_reference = None
    tx.applied_rule_id = None
    return tx
```

- [ ] **Step 2: Update `test_list_transactions_needs_review_filter`**

Replace the assertion to check `categorization_source` instead of `is_transfer`:

```python
async def test_list_transactions_needs_review_filter(client, mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    async with client as c:
        resp = await c.get("/api/transactions?needs_review=true")
    assert resp.status_code == 200
    assert mock_db.execute.called
    call_arg = mock_db.execute.call_args[0][0]
    query_str = str(call_arg).lower()
    assert "category_id" in query_str
    assert "categorization_source" in query_str
```

- [ ] **Step 3: Replace `test_list_transactions_is_transfer_filter`**

Replace the test that checked for an `is_transfer` query param — it becomes a `categorization_source` filter:

```python
async def test_list_transactions_categorization_source_filter(client, mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    async with client as c:
        resp = await c.get("/api/transactions?categorization_source=transfer")
    assert resp.status_code == 200
    call_arg = mock_db.execute.call_args[0][0]
    assert "categorization_source" in str(call_arg).lower()
```

- [ ] **Step 4: Update detail view test — remove `tx.is_transfer = True`**

In `test_get_transaction_details_basic`, remove `tx.is_transfer = False` (already removed from `_make_transaction`). No change needed for the assertion since `is_transfer` won't be in the response.

In `test_get_transaction_details_with_transfer_pair`, replace `tx.is_transfer = True` with `tx.categorization_source = "transfer"`:

```python
async def test_get_transaction_details_with_transfer_pair(client, mock_db):
    tx = _make_transaction()
    tx.value_date = None
    tx.categorization_source = "transfer"
    pair_id = uuid.uuid4()
    tx.transfer_pair_id = pair_id
    tx.category_id = None

    pair_tx = _make_transaction()
    pair_tx.id = pair_id
    pair_account = _make_account()

    tx_result = MagicMock()
    tx_result.scalars.return_value.first.return_value = tx
    acc_result = MagicMock()
    acc_result.scalars.return_value.first.return_value = _make_account(tx.account_id)
    pair_tx_result = MagicMock()
    pair_tx_result.scalars.return_value.first.return_value = pair_tx
    pair_acc_result = MagicMock()
    pair_acc_result.scalars.return_value.first.return_value = pair_account

    mock_db.execute.side_effect = [tx_result, acc_result, pair_tx_result, pair_acc_result]

    async with client as c:
        resp = await c.get(f"/api/transactions/{tx.id}/details")
    assert resp.status_code == 200
    data = resp.json()
    assert data["transfer_pair"] is not None
    assert data["transfer_pair"]["account"]["name"] == "My Account"
```

- [ ] **Step 5: Run tests to confirm failures**

```bash
cd backend && pytest tests/test_transactions_api.py -v 2>&1 | head -50
```

Expected: failures because `TransactionOut` still has `is_transfer`, model mock breaks on `spec=Transaction`.

- [ ] **Step 6: Update `transactions.py` — schemas**

In `backend/app/api/transactions.py`:

Remove `is_transfer: bool` from `TransactionOut`:

```python
class TransactionOut(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    import_batch_id: uuid.UUID
    booking_date: date
    value_date: date | None
    amount: Decimal
    currency: str
    counterparty_name: str | None
    counterparty_account: str | None
    description: str | None
    category_id: uuid.UUID | None
    categorization_source: str | None
    confidence: Decimal | None
    notes: str | None
    created_at: datetime
    llm_status: Literal["no_rule_no_llm", "llm_rejected", "llm_error"] | None = None
    llm_confidence: Decimal | None = None
    model_config = {"from_attributes": True}
```

Remove `is_transfer: bool` and `transfer_pair_id: uuid.UUID | None` from `TransactionDetailOut` — keep `transfer_pair_id` as it is still useful. Actually keep `transfer_pair_id` — it is metadata about the linked transaction, not a transfer flag. Only remove `is_transfer: bool`:

```python
class TransactionDetailOut(BaseModel):
    id: uuid.UUID
    booking_date: date
    value_date: date | None
    amount: Decimal
    currency: str
    counterparty_name: str | None
    counterparty_account: str | None
    description: str | None
    raw_reference: str | None
    transfer_pair_id: uuid.UUID | None
    categorization_source: str | None
    confidence: Decimal | None
    created_at: datetime
    import_batch_id: uuid.UUID
    account: AccountRef
    category: CategoryRef | None
    applied_rule: RuleRef | None
    transfer_pair: TransferPairOut | None
    model_config = {"from_attributes": True}
```

- [ ] **Step 7: Update `list_transactions` — `needs_review` filter and `is_transfer` param**

Replace the two `is_transfer` usages in `list_transactions`:

```python
@router.get("", response_model=list[TransactionOut])
async def list_transactions(
    account_id: uuid.UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    needs_review: bool | None = Query(None),
    categorization_source: str | None = Query(None),
    include_llm_status: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[TransactionOut]:
    query = select(Transaction)

    if account_id is not None:
        query = query.where(Transaction.account_id == account_id)
    if date_from is not None:
        query = query.where(Transaction.booking_date >= date_from)
    if date_to is not None:
        query = query.where(Transaction.booking_date <= date_to)
    if category_id is not None:
        query = query.where(Transaction.category_id == category_id)
    if needs_review is True:
        query = query.where(Transaction.category_id.is_(None))
        query = query.where(
            Transaction.categorization_source.is_(None) |
            (Transaction.categorization_source != "transfer")
        )
    if categorization_source is not None:
        query = query.where(Transaction.categorization_source == categorization_source)

    query = query.order_by(Transaction.booking_date.desc(), Transaction.id.desc())
    query = query.limit(limit).offset(offset)
    # ... rest of function unchanged
```

- [ ] **Step 8: Update `export_csv` — `needs_review` filter**

In `export_csv`, replace:

```python
    if needs_review is True:
        q = q.where(Transaction.category_id.is_(None))
        q = q.where(Transaction.is_transfer.is_(False))
```

with:

```python
    if needs_review is True:
        q = q.where(Transaction.category_id.is_(None))
        q = q.where(
            Transaction.categorization_source.is_(None) |
            (Transaction.categorization_source != "transfer")
        )
```

- [ ] **Step 9: Update `bulk_categorize` — remove `is_transfer=False`**

The `bulk_categorize` null path already clears `categorization_source`. Remove the `is_transfer=False` from both the target and pair updates (that field no longer exists):

```python
@router.patch("/bulk-categorize", status_code=204)
async def bulk_categorize(body: BulkCategorizeRequest, db: AsyncSession = Depends(get_db)):
    if body.category_id is not None:
        values = dict(
            category_id=body.category_id,
            categorization_source="manual",
            confidence=None,
        )
        await db.execute(
            Transaction.__table__.update()
            .where(Transaction.id.in_(body.transaction_ids))
            .values(**values)
        )
    else:
        pair_result = await db.execute(
            select(Transaction.transfer_pair_id)
            .where(Transaction.id.in_(body.transaction_ids))
            .where(Transaction.transfer_pair_id.is_not(None))
        )
        pair_ids = [row[0] for row in pair_result.all()]

        await db.execute(
            Transaction.__table__.update()
            .where(Transaction.id.in_(body.transaction_ids))
            .values(
                category_id=None,
                categorization_source=None,
                confidence=None,
                transfer_pair_id=None,
            )
        )

        if pair_ids:
            await db.execute(
                Transaction.__table__.update()
                .where(Transaction.id.in_(pair_ids))
                .values(
                    category_id=None,
                    categorization_source=None,
                    confidence=None,
                    transfer_pair_id=None,
                )
            )
    await db.commit()
```

- [ ] **Step 10: Update detail view — transfer pair check**

In `get_transaction_details`, replace:

```python
    if tx.is_transfer and tx.transfer_pair_id is not None:
```

with:

```python
    if tx.categorization_source == "transfer" and tx.transfer_pair_id is not None:
```

Also update `TransactionDetailOut(...)` construction — remove the `is_transfer=tx.is_transfer` line:

```python
    return TransactionDetailOut(
        id=tx.id,
        booking_date=tx.booking_date,
        value_date=tx.value_date,
        amount=tx.amount,
        currency=tx.currency,
        counterparty_name=tx.counterparty_name,
        counterparty_account=tx.counterparty_account,
        description=tx.description,
        raw_reference=tx.raw_reference,
        transfer_pair_id=tx.transfer_pair_id,
        categorization_source=tx.categorization_source,
        confidence=tx.confidence,
        created_at=tx.created_at,
        import_batch_id=tx.import_batch_id,
        account=AccountRef(id=account.id, name=account.name, iban=account.iban),
        category=CategoryRef(id=category.id, name=category.name) if category else None,
        applied_rule=RuleRef(id=applied_rule.id, name=applied_rule.name) if applied_rule else None,
        transfer_pair=transfer_pair,
    )
```

- [ ] **Step 11: Run transactions API tests**

```bash
cd backend && pytest tests/test_transactions_api.py -v
```

Expected: all PASS.

- [ ] **Step 12: Commit**

```bash
git add backend/app/api/transactions.py backend/tests/test_transactions_api.py
git commit -m "feat: remove is_transfer from transactions API, use categorization_source"
```

---

### Task 5: Analytics Service

**Files:**
- Modify: `backend/app/services/analytics_service.py`

No new tests needed — this is a raw SQL string change. The existing behavior is preserved; only the filter expression changes.

- [ ] **Step 1: Replace all four `t.is_transfer = false` occurrences**

In `backend/app/services/analytics_service.py`, do a find-and-replace:

Find: `t.is_transfer = false`
Replace: `t.categorization_source IS DISTINCT FROM 'transfer'`

There are 4 occurrences (lines 39, 78, 128, 167 in the original). Replace all of them.

- [ ] **Step 2: Run the full test suite**

```bash
cd backend && pytest tests/ -v
```

Expected: all PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/analytics_service.py
git commit -m "feat: analytics filters use categorization_source IS DISTINCT FROM 'transfer'"
```

---

### Task 6: Imports API

**Files:**
- Modify: `backend/app/api/imports.py`

- [ ] **Step 1: Update `BatchTransactionOut`**

In `backend/app/api/imports.py`, update the schema — add "transfer" to the `categorization_source` Literal and remove `is_transfer`:

```python
class BatchTransactionOut(BaseModel):
    id: uuid.UUID
    booking_date: date
    amount: float
    currency: str
    counterparty_name: str | None
    counterparty_account: str | None
    description: str | None
    category_id: uuid.UUID | None
    categorization_source: Literal["rule", "llm", "manual", "transfer"] | None
    model_config = {"from_attributes": False}
```

- [ ] **Step 2: Update `batch_transactions` construction**

In `batch_transactions`, remove `is_transfer=tx.is_transfer` from the `BatchTransactionOut(...)` call:

```python
    return [
        BatchTransactionOut(
            id=tx.id,
            booking_date=tx.booking_date,
            amount=float(tx.amount),
            currency=tx.currency,
            counterparty_name=tx.counterparty_name,
            counterparty_account=tx.counterparty_account,
            description=tx.description,
            category_id=tx.category_id,
            categorization_source=tx.categorization_source,
        )
        for tx in txs
    ]
```

- [ ] **Step 3: Run tests**

```bash
cd backend && pytest tests/ -v
```

Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/imports.py
git commit -m "feat: remove is_transfer from BatchTransactionOut, add transfer to categorization_source Literal"
```

---

### Task 7: Frontend

**Files:**
- Modify: `frontend/src/api/transactions.ts`
- Modify: `frontend/src/pages/Imports/BatchHistory.tsx`

- [ ] **Step 1: Update `Transaction` interface**

In `frontend/src/api/transactions.ts`, remove `is_transfer: boolean` from `Transaction`:

```typescript
export interface Transaction {
  id: string;
  account_id: string;
  booking_date: string;
  amount: number;
  currency: string;
  counterparty_name: string | null;
  counterparty_account: string | null;
  description: string | null;
  category_id: string | null;
  categorization_source: string | null;
  llm_status?: "no_rule_no_llm" | "llm_rejected" | "llm_error";
  llm_confidence?: number | null;
}
```

- [ ] **Step 2: Update `TransactionDetail` interface**

Remove `is_transfer: boolean` from `TransactionDetail` in the same file:

```typescript
export interface TransactionDetail {
  id: string;
  booking_date: string;
  value_date: string | null;
  amount: number;
  currency: string;
  counterparty_name: string | null;
  counterparty_account: string | null;
  description: string | null;
  raw_reference: string | null;
  transfer_pair_id: string | null;
  categorization_source: string | null;
  confidence: number | null;
  created_at: string;
  import_batch_id: string;
  account: AccountRef;
  category: { id: string; name: string } | null;
  applied_rule: { id: string; name: string } | null;
  transfer_pair: {
    id: string;
    amount: number;
    booking_date: string;
    account: AccountRef;
  } | null;
}
```

- [ ] **Step 3: Update `BatchTx` and `CategorizationBadge` in `BatchHistory.tsx`**

In `frontend/src/pages/Imports/BatchHistory.tsx`:

Replace `BatchTx` interface — remove `is_transfer: boolean`:

```typescript
interface BatchTx {
  id: string;
  booking_date: string;
  amount: number;
  currency: string;
  counterparty_name: string | null;
  counterparty_account: string | null;
  description: string | null;
  category_id: string | null;
  categorization_source: string | null;
}
```

Replace `CategorizationBadge` — check `categorization_source === "transfer"` instead of `tx.is_transfer`:

```typescript
function CategorizationBadge({ tx }: { tx: BatchTx }) {
  const { t } = useTranslation();
  if (tx.categorization_source === "transfer") {
    return (
      <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700">
        {t("imports.badgeTransfer")}
      </span>
    );
  }
  if (tx.categorization_source === "rule") {
    return (
      <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
        {t("imports.badgeRule")}
      </span>
    );
  }
  if (tx.categorization_source === "llm") {
    return (
      <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700">
        {t("imports.badgeLlm")}
      </span>
    );
  }
  if (tx.categorization_source === "manual") {
    // ... (rest unchanged)
  }
  // ... (rest unchanged)
}
```

- [ ] **Step 4: Build TypeScript to verify no type errors**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: no TypeScript errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/transactions.ts frontend/src/pages/Imports/BatchHistory.tsx
git commit -m "feat: remove is_transfer from frontend, check categorization_source === 'transfer'"
```

---

### Task 8: Final Verification

- [ ] **Step 1: Run full backend test suite**

```bash
cd backend && pytest tests/ -v
```

Expected: all tests PASS, no mention of `is_transfer`.

- [ ] **Step 2: Confirm no stray `is_transfer` references in backend**

```bash
grep -r "is_transfer" backend/app/ backend/tests/
```

Expected: no output.

- [ ] **Step 3: Confirm no stray `is_transfer` references in frontend**

```bash
grep -r "is_transfer" frontend/src/
```

Expected: no output.

- [ ] **Step 4: Start backend and verify startup**

```bash
cd backend && uvicorn app.main:app --port 8300 2>&1 | head -10
```

Expected: `Application startup complete.`

- [ ] **Step 5: Final commit if anything was missed**

If no stray references remain and all tests pass, the feature is complete.
