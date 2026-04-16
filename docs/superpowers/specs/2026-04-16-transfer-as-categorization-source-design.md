# Transfer as Categorization Source

**Date:** 2026-04-16  
**Status:** Approved

## Problem

`is_transfer` is a separate boolean column on `Transaction`, redundant with `categorization_source`. A transfer is just another way a transaction gets classified — it should be represented as `categorization_source = "transfer"` rather than a parallel flag. Having both creates two sources of truth and requires keeping them in sync.

## Goal

Remove the `is_transfer` boolean column entirely. Use `categorization_source = "transfer"` as the single signal that a transaction is an internal transfer. Transfer matching remains the first step in the categorization pipeline (no change to order — it already runs first).

## Design

### Database Migration

1. `UPDATE transactions SET categorization_source = 'transfer' WHERE is_transfer = true`
2. Drop `is_transfer` column
3. Drop index `ix_transactions_is_transfer`
4. Add index on `categorization_source` (now used in hot filter paths)

### Model (`db/models.py`)

- Remove `is_transfer: Mapped[bool]` column
- Remove `Index("ix_transactions_is_transfer", "is_transfer")`
- Add `Index("ix_transactions_categorization_source", "categorization_source")`

### Transfer Matcher (`services/transfer_matcher.py`)

- Filter candidates: `Transaction.categorization_source.is_(None)` instead of `Transaction.is_transfer == False`
- On match: set `categorization_source = "transfer"` instead of `is_transfer = True`

### Analytics Service (`services/analytics_service.py`)

Replace all four `t.is_transfer = false` filters with:

```sql
t.categorization_source IS DISTINCT FROM 'transfer'
```

`IS DISTINCT FROM` handles NULLs correctly (unclassified transactions pass through).

### Transactions API (`api/transactions.py`)

- Remove `is_transfer: bool` from `TransactionOut` and `TransactionDetailOut`
- Remove `is_transfer: bool | None` query parameter from `list_transactions`; callers can filter by `categorization_source` if needed
- `needs_review` filter: `category_id IS NULL AND categorization_source IS DISTINCT FROM 'transfer'`
- `bulk_categorize` null path (remove classification): clear `categorization_source`, `category_id`, `confidence`, and `transfer_pair_id` on both the target transactions and their paired transactions. The special `is_transfer=False` field clearing added previously is removed — clearing `categorization_source` is sufficient.
- Transfer pair loading in detail view: `if tx.categorization_source == "transfer" and tx.transfer_pair_id is not None:`

### Imports API (`api/imports.py`)

- Remove `is_transfer: bool` from `BatchTransactionOut`

### Frontend

- Remove `is_transfer: boolean` from all TypeScript transaction interfaces (`transactions.ts`, `BatchHistory.tsx`, `transactionContextMenu.ts`)
- Replace `tx.is_transfer` checks with `tx.categorization_source === "transfer"`
- Remove `is_transfer` from any API call query params

### Tests

- Update `test_transfer_matcher.py`: assert `categorization_source == "transfer"` instead of `is_transfer == True`
- Update `test_categorization_service.py`: same
- Update `test_transactions_api.py`: remove `is_transfer` fixture fields, update needs_review and filter tests

## What Does Not Change

- `transfer_pair_id` column — kept as metadata linking the two sides of a transfer pair
- Pipeline order — transfer matching already runs first
- "Internal Transfer" category assignment — transfer matcher continues to assign it

## Invariant

A transaction is a transfer if and only if `categorization_source = "transfer"`. No other field encodes this information.
