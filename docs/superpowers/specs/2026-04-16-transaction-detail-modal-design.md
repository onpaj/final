# Transaction Detail Modal

**Date:** 2026-04-16
**Status:** Approved

## Summary

Add a "Show details" option to the transaction context menu that opens a centered modal window displaying everything known about a transaction: all core fields, own account info, counterparty, transfer pair (both accounts with names and IBANs), categorization metadata (source, rule, LLM confidence), and the transaction ID.

## Backend

### New endpoint: `GET /api/transactions/{id}/details`

Returns a rich response resolved server-side via targeted selects. The list endpoint is unchanged.

**Response shape (`TransactionDetailOut`):**

```python
class AccountRef(BaseModel):
    id: UUID
    name: str
    iban: str | None

class CategoryRef(BaseModel):
    id: UUID
    name: str

class RuleRef(BaseModel):
    id: UUID
    name: str

class TransferPairOut(BaseModel):
    id: UUID
    amount: Decimal
    booking_date: date
    account: AccountRef

class TransactionDetailOut(BaseModel):
    # Core fields
    id: UUID
    booking_date: date
    value_date: date | None
    amount: Decimal
    currency: str
    counterparty_name: str | None
    counterparty_account: str | None
    description: str | None
    raw_reference: str | None
    is_transfer: bool
    transfer_pair_id: UUID | None
    categorization_source: str | None  # rule | llm | manual
    confidence: Decimal | None
    created_at: datetime
    import_batch_id: UUID

    # Resolved joins
    account: AccountRef
    category: CategoryRef | None
    applied_rule: RuleRef | None

    # Transfer pair (present only if is_transfer=True and pair found)
    transfer_pair: TransferPairOut | None
```

**Implementation:** 4 queries max — fetch transaction (404 if not found), join account, optionally join category + rule in parallel, optionally fetch transfer pair + its account. All async.

**Location:** `backend/app/api/transactions.py`, registered on the existing `router` as `GET /{transaction_id}/details`.

## Frontend

### `api/transactions.ts`

Add `TransactionDetail` type mirroring `TransactionDetailOut` and `getTransactionDetails(id: string): Promise<TransactionDetail>` calling `GET /api/transactions/{id}/details`.

### `components/Modal.tsx` (new)

Generic centered modal component:

- Props: `open`, `onClose`, `title`, `children`
- Fixed full-screen backdrop (`bg-black/40`), centered white card, max-width `max-w-lg`, scrollable body
- Close on backdrop click and ESC key
- Rendered via `ReactDOM.createPortal` into `document.body`

### `components/TransactionDetailModal.tsx` (new)

Consumes `useQuery` with key `["transaction", "details", txId]` to fetch `getTransactionDetails`. Renders three sections:

**Transaction section:**
- Transaction ID (monospace, copyable label)
- Booking date + value date
- Amount + currency
- Own account: name + IBAN (formatted with `formatCzechIban`)
- Counterparty: name + account number (formatted)
- Description + raw reference

**Transfer pair section** (shown only when `is_transfer = true`):
- Paired transaction ID
- Paired amount + date
- Paired account: name + IBAN

**Categorization section:**
- Category name (or "Uncategorized")
- Source: rule / llm / manual (translated label)
- Applied rule name (if source = rule)
- Confidence score (if source = llm, formatted as percentage)

Loading state: spinner inside the modal body. Error state: simple error message.

### `utils/transactionContextMenu.ts`

Add `onShowDetails?: (txId: string) => void` to `BuildMenuOptions`. When provided, prepend a "Show details" item to the returned menu array (before the category submenu).

### `pages/Analytics/TransactionTable.tsx`

- Add `detailTxId` state (`string | null`)
- Pass `onShowDetails: (id) => setDetailTxId(id)` to `buildTransactionContextMenuItems`
- Render `<TransactionDetailModal txId={detailTxId} onClose={() => setDetailTxId(null)} />` at the bottom of the component (alongside the existing `<ContextMenu>`)

No changes needed to `ReviewPage`, `CategoryDetail`, or other callers — the feature is fully self-contained within `TransactionTable`.

## i18n

New keys needed (Czech + English):

```
transaction.showDetails
transaction.detailTitle
transaction.ownAccount
transaction.transferPair
transaction.categorizationSource
transaction.sourceRule
transaction.sourceLlm
transaction.sourceManual
transaction.appliedRule
transaction.confidence
transaction.valueDate
transaction.rawReference
transaction.importBatch
```

## Testing

No new backend tests needed beyond manual verification — the endpoint is a straightforward read with joins, and the existing test patterns don't cover individual GET-by-ID endpoints. Frontend: no new tests (no test infrastructure for components in this project).
