# Transaction Detail Modal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Show details" context menu option that opens a centered modal with full transaction details — own account, counterparty, transfer pair both sides, categorization metadata, and all core fields.

**Architecture:** New `GET /api/transactions/{id}/details` backend endpoint resolves joined data (account, category, rule, transfer pair + its account) in sequential async queries. Frontend adds a generic `Modal` component, a `TransactionDetailModal` that fetches on open via TanStack Query, and wires it into `TransactionTable` via the existing `buildTransactionContextMenuItems` utility.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic v2; React 19, TanStack Query v5, i18next, Tailwind CSS, ReactDOM.createPortal

---

## File Map

| Action | File |
|--------|------|
| Modify | `backend/app/api/transactions.py` — add Pydantic models + `GET /{transaction_id}/details` endpoint |
| Modify | `backend/tests/test_transactions_api.py` — add tests for the new endpoint |
| Modify | `frontend/src/api/transactions.ts` — add `TransactionDetail` type + `getTransactionDetails` |
| Create | `frontend/src/components/Modal.tsx` — generic centered modal |
| Create | `frontend/src/components/TransactionDetailModal.tsx` — detail view using Modal |
| Modify | `frontend/src/utils/transactionContextMenu.ts` — add `onShowDetails` option |
| Modify | `frontend/src/pages/Analytics/TransactionTable.tsx` — wire up modal state |
| Modify | `frontend/public/locales/en/translation.json` — English i18n keys |
| Modify | `frontend/public/locales/cs/translation.json` — Czech i18n keys |

---

## Task 1: Backend — Pydantic models for the details endpoint

**Files:**
- Modify: `backend/app/api/transactions.py`

- [ ] **Step 1: Add the response models** after the existing `TransactionOut` class (after line 39):

```python
class AccountRef(BaseModel):
    id: uuid.UUID
    name: str
    iban: str | None
    model_config = {"from_attributes": True}


class CategoryRef(BaseModel):
    id: uuid.UUID
    name: str
    model_config = {"from_attributes": True}


class RuleRef(BaseModel):
    id: uuid.UUID
    name: str
    model_config = {"from_attributes": True}


class TransferPairOut(BaseModel):
    id: uuid.UUID
    amount: Decimal
    booking_date: date
    account: AccountRef


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
    is_transfer: bool
    transfer_pair_id: uuid.UUID | None
    categorization_source: str | None
    confidence: Decimal | None
    created_at: datetime
    import_batch_id: uuid.UUID
    account: AccountRef
    category: CategoryRef | None
    applied_rule: RuleRef | None
    transfer_pair: TransferPairOut | None
```

- [ ] **Step 2: Add missing imports** — `Account`, `Category`, `Rule` are needed from `app.db.models`. The existing import is:
```python
from app.db.models import LlmClassification, Transaction
```
Change it to:
```python
from app.db.models import Account, Category, LlmClassification, Rule, Transaction
```
Also add `HTTPException` to the FastAPI imports line:
```python
from fastapi import APIRouter, Depends, HTTPException, Query
```

- [ ] **Step 3: Commit**

```bash
cd backend
git add app/api/transactions.py
git commit -m "feat: add Pydantic models for transaction details endpoint"
```

---

## Task 2: Backend — `GET /{transaction_id}/details` endpoint

**Files:**
- Modify: `backend/app/api/transactions.py`

- [ ] **Step 1: Write the failing test first** (in `backend/tests/test_transactions_api.py`):

Add a `_make_account` helper and two tests after the existing tests at the bottom of the file:

```python
def _make_account(account_id: uuid.UUID | None = None) -> MagicMock:
    from app.db.models import Account as AccountModel
    acc = MagicMock(spec=AccountModel)
    acc.id = account_id or uuid.uuid4()
    acc.name = "My Account"
    acc.iban = "CZ6508000000192000145399"
    return acc


async def test_get_transaction_details_not_found(client, mock_db):
    empty_result = MagicMock()
    empty_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = empty_result
    async with client as c:
        resp = await c.get(f"/api/transactions/{uuid.uuid4()}/details")
    assert resp.status_code == 404


async def test_get_transaction_details_basic(client, mock_db):
    tx = _make_transaction()
    tx.value_date = None
    tx.raw_reference = None
    tx.is_transfer = False
    tx.transfer_pair_id = None
    tx.category_id = None
    tx.applied_rule_id = None
    acc = _make_account(tx.account_id)

    tx_result = MagicMock()
    tx_result.scalars.return_value.first.return_value = tx
    acc_result = MagicMock()
    acc_result.scalars.return_value.first.return_value = acc

    mock_db.execute.side_effect = [tx_result, acc_result]

    async with client as c:
        resp = await c.get(f"/api/transactions/{tx.id}/details")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(tx.id)
    assert data["account"]["name"] == "My Account"
    assert data["category"] is None
    assert data["applied_rule"] is None
    assert data["transfer_pair"] is None
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd backend
pytest tests/test_transactions_api.py::test_get_transaction_details_not_found tests/test_transactions_api.py::test_get_transaction_details_basic -v
```
Expected: FAIL with `404` or route not found errors.

- [ ] **Step 3: Implement the endpoint** — add after `bulk_categorize` at the bottom of `backend/app/api/transactions.py`:

```python
@router.get("/{transaction_id}/details", response_model=TransactionDetailOut)
async def get_transaction_details(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TransactionDetailOut:
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    tx = result.scalars().first()
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    result = await db.execute(select(Account).where(Account.id == tx.account_id))
    account = result.scalars().first()

    category = None
    if tx.category_id is not None:
        result = await db.execute(select(Category).where(Category.id == tx.category_id))
        category = result.scalars().first()

    applied_rule = None
    if tx.applied_rule_id is not None:
        result = await db.execute(select(Rule).where(Rule.id == tx.applied_rule_id))
        applied_rule = result.scalars().first()

    transfer_pair = None
    if tx.is_transfer and tx.transfer_pair_id is not None:
        result = await db.execute(select(Transaction).where(Transaction.id == tx.transfer_pair_id))
        pair_tx = result.scalars().first()
        if pair_tx is not None:
            result = await db.execute(select(Account).where(Account.id == pair_tx.account_id))
            pair_account = result.scalars().first()
            transfer_pair = TransferPairOut(
                id=pair_tx.id,
                amount=pair_tx.amount,
                booking_date=pair_tx.booking_date,
                account=AccountRef(
                    id=pair_account.id,
                    name=pair_account.name,
                    iban=pair_account.iban,
                ),
            )

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
        is_transfer=tx.is_transfer,
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

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd backend
pytest tests/test_transactions_api.py::test_get_transaction_details_not_found tests/test_transactions_api.py::test_get_transaction_details_basic -v
```
Expected: 2 PASSED.

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
cd backend
pytest tests/ -v
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/api/transactions.py tests/test_transactions_api.py
git commit -m "feat: add GET /api/transactions/{id}/details endpoint"
```

---

## Task 3: Frontend — i18n keys

**Files:**
- Modify: `frontend/public/locales/en/translation.json`
- Modify: `frontend/public/locales/cs/translation.json`

- [ ] **Step 1: Add the `transaction` namespace to `en/translation.json`** — insert before the closing `}` on the last line (after the `review` block):

```json
  "transaction": {
    "showDetails": "Show details",
    "detailTitle": "Transaction Details",
    "loadError": "Failed to load transaction details.",
    "sectionTransaction": "Transaction",
    "sectionCategorization": "Categorization",
    "ownAccount": "Own account",
    "valueDate": "Value date",
    "rawReference": "Reference",
    "transferPair": "Transfer pair",
    "uncategorized": "Uncategorized",
    "categorizationSource": "Source",
    "source_rule": "Rule",
    "source_llm": "LLM",
    "source_manual": "Manual",
    "appliedRule": "Applied rule",
    "confidence": "Confidence",
    "txAccount": "Account"
  }
```

- [ ] **Step 2: Add the `transaction` namespace to `cs/translation.json`** — same position:

```json
  "transaction": {
    "showDetails": "Zobrazit detail",
    "detailTitle": "Detail transakce",
    "loadError": "Nepodařilo se načíst detail transakce.",
    "sectionTransaction": "Transakce",
    "sectionCategorization": "Kategorizace",
    "ownAccount": "Vlastní účet",
    "valueDate": "Datum valuty",
    "rawReference": "Reference",
    "transferPair": "Párová transakce",
    "uncategorized": "Bez kategorie",
    "categorizationSource": "Zdroj",
    "source_rule": "Pravidlo",
    "source_llm": "LLM",
    "source_manual": "Ručně",
    "appliedRule": "Použité pravidlo",
    "confidence": "Spolehlivost",
    "txAccount": "Účet"
  }
```

- [ ] **Step 3: Commit**

```bash
git add frontend/public/locales/en/translation.json frontend/public/locales/cs/translation.json
git commit -m "feat: add i18n keys for transaction detail modal"
```

---

## Task 4: Frontend — `getTransactionDetails` API function

**Files:**
- Modify: `frontend/src/api/transactions.ts`

- [ ] **Step 1: Add the `TransactionDetail` type and `getTransactionDetails` function** — append to the end of `frontend/src/api/transactions.ts`:

```typescript
export interface AccountRef {
  id: string;
  name: string;
  iban: string | null;
}

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
  is_transfer: boolean;
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

export async function getTransactionDetails(id: string): Promise<TransactionDetail> {
  const { data } = await client.get<TransactionDetail>(`/api/transactions/${id}/details`);
  return data;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/transactions.ts
git commit -m "feat: add getTransactionDetails API function"
```

---

## Task 5: Frontend — generic `Modal` component

**Files:**
- Create: `frontend/src/components/Modal.tsx`

- [ ] **Step 1: Create `frontend/src/components/Modal.tsx`**:

```tsx
import { useEffect } from "react";
import ReactDOM from "react-dom";

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export default function Modal({ open, onClose, title, children }: Props) {
  useEffect(() => {
    if (!open) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return ReactDOM.createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/40" onClick={onClose} />
      <div className="relative z-10 bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] flex flex-col mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >
            ✕
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-4">{children}</div>
      </div>
    </div>,
    document.body
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Modal.tsx
git commit -m "feat: add generic Modal component"
```

---

## Task 6: Frontend — `TransactionDetailModal` component

**Files:**
- Create: `frontend/src/components/TransactionDetailModal.tsx`

- [ ] **Step 1: Create `frontend/src/components/TransactionDetailModal.tsx`**:

```tsx
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import Modal from "./Modal";
import { getTransactionDetails } from "../api/transactions";
import { formatCzechIban } from "../utils/formatIban";

interface Props {
  txId: string | null;
  onClose: () => void;
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex gap-2 text-sm">
      <dt className="w-40 flex-shrink-0 text-gray-500">{label}</dt>
      <dd className="text-gray-900 break-all">{value}</dd>
    </div>
  );
}

export default function TransactionDetailModal({ txId, onClose }: Props) {
  const { t } = useTranslation();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["transaction", "details", txId],
    queryFn: () => getTransactionDetails(txId!),
    enabled: txId !== null,
  });

  return (
    <Modal open={txId !== null} onClose={onClose} title={t("transaction.detailTitle")}>
      {isLoading && (
        <p className="text-sm text-gray-400 text-center py-8">{t("common.loading")}</p>
      )}
      {isError && (
        <p className="text-sm text-red-500 text-center py-8">{t("transaction.loadError")}</p>
      )}
      {data && (
        <div className="space-y-6">
          <section>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
              {t("transaction.sectionTransaction")}
            </h3>
            <dl className="space-y-2">
              <Row label="ID" value={<span className="font-mono text-xs">{data.id}</span>} />
              <Row label={t("analytics.txDate")} value={data.booking_date} />
              {data.value_date && (
                <Row label={t("transaction.valueDate")} value={data.value_date} />
              )}
              <Row
                label={t("analytics.txAmount")}
                value={`${Number(data.amount).toLocaleString("cs-CZ")} ${data.currency}`}
              />
              <Row
                label={t("transaction.ownAccount")}
                value={
                  data.account.iban
                    ? `${data.account.name} · ${formatCzechIban(data.account.iban)}`
                    : data.account.name
                }
              />
              {data.counterparty_name && (
                <Row label={t("analytics.txCounterparty")} value={data.counterparty_name} />
              )}
              {data.counterparty_account && (
                <Row
                  label={t("analytics.txCounterpartyAccount")}
                  value={formatCzechIban(data.counterparty_account)}
                />
              )}
              {data.description && (
                <Row label={t("analytics.txDescription")} value={data.description} />
              )}
              {data.raw_reference && (
                <Row label={t("transaction.rawReference")} value={data.raw_reference} />
              )}
            </dl>
          </section>

          {data.transfer_pair && (
            <section>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
                {t("transaction.transferPair")}
              </h3>
              <dl className="space-y-2">
                <Row
                  label="ID"
                  value={<span className="font-mono text-xs">{data.transfer_pair.id}</span>}
                />
                <Row label={t("analytics.txDate")} value={data.transfer_pair.booking_date} />
                <Row
                  label={t("analytics.txAmount")}
                  value={`${Number(data.transfer_pair.amount).toLocaleString("cs-CZ")} ${data.currency}`}
                />
                <Row
                  label={t("transaction.ownAccount")}
                  value={
                    data.transfer_pair.account.iban
                      ? `${data.transfer_pair.account.name} · ${formatCzechIban(data.transfer_pair.account.iban)}`
                      : data.transfer_pair.account.name
                  }
                />
              </dl>
            </section>
          )}

          <section>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
              {t("transaction.sectionCategorization")}
            </h3>
            <dl className="space-y-2">
              <Row
                label={t("analytics.category")}
                value={data.category?.name ?? t("transaction.uncategorized")}
              />
              {data.categorization_source && (
                <Row
                  label={t("transaction.categorizationSource")}
                  value={t(`transaction.source_${data.categorization_source}`)}
                />
              )}
              {data.applied_rule && (
                <Row label={t("transaction.appliedRule")} value={data.applied_rule.name} />
              )}
              {data.confidence != null && (
                <Row
                  label={t("transaction.confidence")}
                  value={`${(Number(data.confidence) * 100).toFixed(0)}%`}
                />
              )}
            </dl>
          </section>
        </div>
      )}
    </Modal>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/TransactionDetailModal.tsx
git commit -m "feat: add TransactionDetailModal component"
```

---

## Task 7: Frontend — wire into context menu and `TransactionTable`

**Files:**
- Modify: `frontend/src/utils/transactionContextMenu.ts`
- Modify: `frontend/src/pages/Analytics/TransactionTable.tsx`

- [ ] **Step 1: Update `BuildMenuOptions` in `frontend/src/utils/transactionContextMenu.ts`** — add `onShowDetails` to the interface and prepend the menu item:

Replace the `BuildMenuOptions` interface (lines 15–22):
```typescript
export interface BuildMenuOptions {
  tx: TransactionLike;
  selectedIds: string[];
  categoryGroups: CategoryGroup[];
  onCategorize: (ids: string[], categoryId: string | null) => void;
  onCreateRule: (prefill: RulePrefill) => void;
  onShowDetails?: (txId: string) => void;
  t: TFunction;
}
```

Replace the `return [` at the start of the return array in `buildTransactionContextMenuItems` (the full return statement becomes):
```typescript
  return [
    ...(onShowDetails
      ? [{ label: t("transaction.showDetails"), onClick: () => onShowDetails(tx.id) }]
      : []),
    { label: t("analytics.changeCategory"), children: categoryMenuItems },
    ...(tx.category_id
      ? [{
          label: t("analytics.unassignCategory"),
          onClick: () => onCategorize(selectedIds, null),
        }]
      : []),
    {
      label: t("analytics.createRule"),
      onClick: () =>
        onCreateRule({
          name: tx.counterparty_name ?? tx.description ?? "",
          counterpartyAccount: tx.counterparty_account,
          counterpartyName: tx.counterparty_name,
          description: tx.description,
        }),
    },
  ];
```

- [ ] **Step 2: Update `TransactionTable`** — add `detailTxId` state, pass `onShowDetails` to the menu builder, and render the modal.

At the top of `frontend/src/pages/Analytics/TransactionTable.tsx`, add the import:
```typescript
import TransactionDetailModal from "../../components/TransactionDetailModal";
```

Inside the `TransactionTable` component, add the state declaration after the existing `contextMenu` state (line 121):
```typescript
const [detailTxId, setDetailTxId] = useState<string | null>(null);
```

Update the `contextMenuItems` block to pass `onShowDetails` (replace lines 129–139):
```typescript
  const contextMenuItems =
    contextTx && categoryGroups && onCategorize && onCreateRule
      ? buildTransactionContextMenuItems({
          tx: contextTx,
          selectedIds: selected.size > 0 ? Array.from(selected) : [contextMenu!.txId],
          categoryGroups,
          onCategorize,
          onCreateRule,
          onShowDetails: (id) => setDetailTxId(id),
          t,
        })
      : [];
```

At the bottom of the return statement, after the existing `{contextMenu && ...}` block (before the closing `</>`), add:
```tsx
      <TransactionDetailModal txId={detailTxId} onClose={() => setDetailTxId(null)} />
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/utils/transactionContextMenu.ts frontend/src/pages/Analytics/TransactionTable.tsx
git commit -m "feat: wire transaction detail modal into context menu and TransactionTable"
```

---

## Task 8: Manual verification

- [ ] **Step 1: Start backend**

```bash
cd backend
uvicorn app.main:app --reload --port 8300
```

- [ ] **Step 2: Start frontend**

```bash
cd frontend
npm run dev
```

- [ ] **Step 3: Verify the happy path**

1. Open `http://localhost:5173`, navigate to Analytics or Needs Review
2. Right-click any transaction row
3. Confirm "Show details" appears as the first menu item
4. Click it — modal opens with transaction data, own account name/IBAN, counterparty info
5. If the transaction has `is_transfer=true`, confirm the "Transfer pair" section appears with the paired account

- [ ] **Step 4: Verify the transfer pair section**

Query the DB or find a known transfer transaction. Right-click it. Confirm the modal shows both accounts.

- [ ] **Step 5: Verify close behaviour**

- Click backdrop → modal closes
- Press ESC → modal closes
- Click ✕ → modal closes
