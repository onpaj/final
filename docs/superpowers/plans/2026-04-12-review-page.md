# Review Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/review` page that surfaces all uncategorized transactions with a reason badge (no rule, LLM rejected, LLM error) and lets the user assign categories via the existing drag-to-sidebar mechanic.

**Architecture:** Extend `GET /api/transactions` with an optional `include_llm_status=true` param that performs a second DB query for LLM classifications and merges the result in Python. The frontend reuses `CategorySidebar`, `TransactionDragOverlay`, and `DndContext` from the Analytics page; `TransactionTable` gains a `showReasonColumn` prop.

**Tech Stack:** Python / FastAPI / SQLAlchemy async; React / TypeScript / TanStack Query / @dnd-kit/core / i18next

---

## File Map

**Backend — modified:**
- `backend/app/services/categorization_service.py` — log LLM errors as `LlmClassification` rows
- `backend/app/api/transactions.py` — add `include_llm_status` param + optional fields on `TransactionOut`
- `backend/tests/test_categorization_service.py` — test LLM error logging
- `backend/tests/test_transactions_api.py` — test `include_llm_status` param

**Frontend — modified:**
- `frontend/src/api/transactions.ts` — add `llm_status` / `llm_confidence` to `Transaction` type + param to `listTransactions`
- `frontend/src/pages/Analytics/TransactionTable.tsx` — add `showReasonColumn` prop
- `frontend/src/components/NavBar.tsx` — add Review link with count badge
- `frontend/src/App.tsx` — add `/review` route
- `frontend/public/locales/cs/translation.json` — add `review.*` and `nav.review` keys
- `frontend/public/locales/en/translation.json` — same keys in English

**Frontend — created:**
- `frontend/src/pages/Review/index.tsx` — the new page

---

## Task 1: Log LLM errors in categorization_service

**Files:**
- Modify: `backend/app/services/categorization_service.py`
- Modify: `backend/tests/test_categorization_service.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_categorization_service.py`:

```python
async def test_llm_error_writes_classification_row():
    """When AnthropicClassificationError is raised, an LlmClassification row with reasoning='error' must be saved."""
    from app.services.anthropic_client import AnthropicClassificationError

    tx = MagicMock()
    tx.id = uuid.uuid4()
    tx.counterparty_name = "UNKNOWN"
    tx.description = ""
    tx.amount = Decimal("-100.00")
    tx.category_id = None
    tx.booking_date = date(2026, 1, 1)
    tx.value_date = None
    tx.currency = "CZK"
    tx.counterparty_account = None
    tx.raw_reference = None

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [])))
    added_rows = []
    mock_db.add = MagicMock(side_effect=added_rows.append)

    with patch("app.services.categorization_service.AnthropicClient") as MockLLM:
        MockLLM.return_value.classify.side_effect = AnthropicClassificationError("timeout")
        service = CategorizationService(mock_db)
        await service._categorize_one(tx, [], [])

    assert tx.category_id is None
    assert len(added_rows) == 1
    row = added_rows[0]
    assert row.transaction_id == tx.id
    assert row.accepted is False
    assert row.reasoning == "error"
    assert row.confidence is None
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd backend && python -m pytest tests/test_categorization_service.py::test_llm_error_writes_classification_row -v
```

Expected: `FAILED` — no row is added in the current implementation.

- [ ] **Step 3: Update `_categorize_one` to log the error**

In `backend/app/services/categorization_service.py`, replace the `except AnthropicClassificationError` block:

```python
        except AnthropicClassificationError:
            # Log error so Review page can distinguish from "never tried"
            error_log = LlmClassification(
                transaction_id=tx.id,
                model="unknown",
                suggested_category_id=None,
                accepted=False,
                confidence=None,
                reasoning="error",
                prompt_tokens=None,
                completion_tokens=None,
            )
            self._db.add(error_log)
            return
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_categorization_service.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
cd backend && git add app/services/categorization_service.py tests/test_categorization_service.py
git commit -m "feat: log LLM errors as LlmClassification rows with reasoning='error'"
```

---

## Task 2: Extend transactions endpoint with `include_llm_status`

**Files:**
- Modify: `backend/app/api/transactions.py`
- Modify: `backend/tests/test_transactions_api.py`

- [ ] **Step 1: Write failing tests**

Add to `backend/tests/test_transactions_api.py`:

```python
async def test_include_llm_status_no_classification(client, mock_db):
    """Transaction with no LlmClassification row → llm_status='no_rule_no_llm'."""
    tx = _make_transaction()
    # First execute call → transaction list; second → llm classifications (empty)
    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []
    tx_result = MagicMock()
    tx_result.scalars.return_value.all.return_value = [tx]
    mock_db.execute.side_effect = [tx_result, empty_result]

    async with client as c:
        resp = await c.get("/api/transactions?needs_review=true&include_llm_status=true")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["llm_status"] == "no_rule_no_llm"
    assert data[0]["llm_confidence"] is None


async def test_include_llm_status_llm_error(client, mock_db):
    """Transaction with LlmClassification reasoning='error' → llm_status='llm_error'."""
    from datetime import datetime
    tx = _make_transaction()
    cls = MagicMock()
    cls.transaction_id = tx.id
    cls.accepted = False
    cls.confidence = None
    cls.reasoning = "error"

    tx_result = MagicMock()
    tx_result.scalars.return_value.all.return_value = [tx]
    cls_result = MagicMock()
    cls_result.scalars.return_value.all.return_value = [cls]
    mock_db.execute.side_effect = [tx_result, cls_result]

    async with client as c:
        resp = await c.get("/api/transactions?needs_review=true&include_llm_status=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["llm_status"] == "llm_error"


async def test_include_llm_status_llm_rejected(client, mock_db):
    """Transaction with LlmClassification accepted=False, confidence set → llm_status='llm_rejected'."""
    tx = _make_transaction()
    cls = MagicMock()
    cls.transaction_id = tx.id
    cls.accepted = False
    cls.confidence = Decimal("0.38")
    cls.reasoning = "Low confidence"

    tx_result = MagicMock()
    tx_result.scalars.return_value.all.return_value = [tx]
    cls_result = MagicMock()
    cls_result.scalars.return_value.all.return_value = [cls]
    mock_db.execute.side_effect = [tx_result, cls_result]

    async with client as c:
        resp = await c.get("/api/transactions?needs_review=true&include_llm_status=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["llm_status"] == "llm_rejected"
    assert abs(float(data[0]["llm_confidence"]) - 0.38) < 0.01


async def test_include_llm_status_false_by_default(client, mock_db):
    """Without include_llm_status, only one DB execute call is made and llm_status is None."""
    tx = _make_transaction()
    tx_result = MagicMock()
    tx_result.scalars.return_value.all.return_value = [tx]
    mock_db.execute.return_value = tx_result

    async with client as c:
        resp = await c.get("/api/transactions")
    assert resp.status_code == 200
    assert mock_db.execute.call_count == 1
    assert resp.json()[0]["llm_status"] is None
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && python -m pytest tests/test_transactions_api.py::test_include_llm_status_no_classification tests/test_transactions_api.py::test_include_llm_status_llm_error tests/test_transactions_api.py::test_include_llm_status_llm_rejected tests/test_transactions_api.py::test_include_llm_status_false_by_default -v
```

Expected: all FAIL.

- [ ] **Step 3: Update `TransactionOut` and `list_transactions` in `backend/app/api/transactions.py`**

Replace the `TransactionOut` class and `list_transactions` function. The imports at the top need `LlmClassification` added:

```python
import csv
import io
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LlmClassification, Transaction
from app.db.session import get_db

router = APIRouter()


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
    is_transfer: bool
    notes: str | None
    created_at: datetime
    llm_status: str | None = None
    llm_confidence: Decimal | None = None
    model_config = {"from_attributes": True}
```

Replace the `list_transactions` function:

```python
@router.get("", response_model=list[TransactionOut])
async def list_transactions(
    account_id: uuid.UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    needs_review: bool | None = Query(None),
    is_transfer: bool | None = Query(None),
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
        query = query.where(Transaction.is_transfer.is_(False))
    if is_transfer is not None:
        query = query.where(Transaction.is_transfer.is_(is_transfer))

    query = query.order_by(Transaction.booking_date.desc(), Transaction.id.desc())
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    transactions = result.scalars().all()

    if not include_llm_status:
        return transactions  # type: ignore[return-value]

    # Fetch the most recent LlmClassification per transaction (second query, merged in Python)
    tx_ids = [tx.id for tx in transactions]
    classifications: dict[uuid.UUID, LlmClassification] = {}
    if tx_ids:
        cls_result = await db.execute(
            select(LlmClassification)
            .where(LlmClassification.transaction_id.in_(tx_ids))
            .order_by(LlmClassification.transaction_id, LlmClassification.created_at.desc())
            .distinct(LlmClassification.transaction_id)
        )
        for cls in cls_result.scalars().all():
            classifications[cls.transaction_id] = cls

    out: list[TransactionOut] = []
    for tx in transactions:
        tx_out = TransactionOut.model_validate(tx)
        cls = classifications.get(tx.id)
        if cls is None:
            tx_out.llm_status = "no_rule_no_llm"
        elif cls.reasoning == "error":
            tx_out.llm_status = "llm_error"
        else:
            tx_out.llm_status = "llm_rejected"
            tx_out.llm_confidence = cls.confidence
        out.append(tx_out)

    return out
```

- [ ] **Step 4: Run all backend tests**

```bash
cd backend && python -m pytest tests/test_transactions_api.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
cd backend && git add app/api/transactions.py tests/test_transactions_api.py
git commit -m "feat: add include_llm_status param to GET /api/transactions"
```

---

## Task 3: Update frontend Transaction type and TransactionTable

**Files:**
- Modify: `frontend/src/api/transactions.ts`
- Modify: `frontend/src/pages/Analytics/TransactionTable.tsx`

- [ ] **Step 1: Update `Transaction` type and `listTransactions` in `frontend/src/api/transactions.ts`**

Replace the entire file:

```typescript
import client from "./client";

export interface Transaction {
  id: string;
  account_id: string;
  booking_date: string;
  amount: number;
  currency: string;
  counterparty_name: string | null;
  description: string | null;
  category_id: string | null;
  categorization_source: string | null;
  is_transfer: boolean;
  llm_status?: "no_rule_no_llm" | "llm_rejected" | "llm_error";
  llm_confidence?: number | null;
}

export async function listTransactions(params: {
  account_id?: string;
  date_from?: string;
  date_to?: string;
  category_id?: string;
  needs_review?: boolean;
  include_llm_status?: boolean;
  limit?: number;
  offset?: number;
}): Promise<Transaction[]> {
  const { data } = await client.get<Transaction[]>("/api/transactions", { params });
  return data;
}

export async function bulkCategorize(
  transaction_ids: string[],
  category_id: string | null,
): Promise<void> {
  await client.patch("/api/transactions/bulk-categorize", {
    transaction_ids,
    category_id,
  });
}
```

- [ ] **Step 2: Add `showReasonColumn` prop to `TransactionTable`**

Replace the entire `frontend/src/pages/Analytics/TransactionTable.tsx`:

```typescript
import { useDraggable } from "@dnd-kit/core";
import { useTranslation } from "react-i18next";
import type { Transaction } from "../../api/transactions";

function ReasonBadge({ tx }: { tx: Transaction }) {
  if (!tx.llm_status) return null;

  if (tx.llm_status === "no_rule_no_llm") {
    return (
      <span className="inline-block px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-500">
        no rule
      </span>
    );
  }
  if (tx.llm_status === "llm_error") {
    return (
      <span className="inline-block px-2 py-0.5 rounded text-xs bg-red-100 text-red-600">
        LLM error
      </span>
    );
  }
  // llm_rejected
  const conf = tx.llm_confidence != null ? ` (${Number(tx.llm_confidence).toFixed(2)})` : "";
  return (
    <span className="inline-block px-2 py-0.5 rounded text-xs bg-yellow-100 text-yellow-700">
      LLM rejected{conf}
    </span>
  );
}

interface DraggableRowProps {
  transaction: Transaction;
  isChecked: boolean;
  isDragActive: boolean;
  showReasonColumn: boolean;
  onToggle: () => void;
}

function DraggableRow({ transaction: tx, isChecked, isDragActive, showReasonColumn, onToggle }: DraggableRowProps) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: tx.id });

  return (
    <tr
      ref={setNodeRef}
      className={[
        "border-t border-gray-100",
        isDragging ? "opacity-40" : "hover:bg-gray-50",
        isChecked && !isDragging ? "bg-blue-50" : "",
      ].join(" ")}
      style={{ cursor: isDragActive ? "grabbing" : "grab" }}
      {...attributes}
      {...listeners}
    >
      <td className="px-4 py-2.5" onPointerDown={(e) => e.stopPropagation()}>
        <input
          type="checkbox"
          checked={isChecked}
          onChange={onToggle}
          className="cursor-pointer"
        />
      </td>
      <td className="px-4 py-2.5 text-gray-500">{tx.booking_date}</td>
      <td className="px-4 py-2.5 font-medium">{tx.counterparty_name || "—"}</td>
      <td className="px-4 py-2.5 text-gray-500 text-xs">{tx.description || "—"}</td>
      <td className={`px-4 py-2.5 font-medium ${tx.amount < 0 ? "text-red-500" : "text-green-600"}`}>
        {Number(tx.amount).toLocaleString("cs-CZ")} CZK
      </td>
      {showReasonColumn && (
        <td className="px-4 py-2.5">
          <ReasonBadge tx={tx} />
        </td>
      )}
    </tr>
  );
}

interface Props {
  transactions: Transaction[];
  selected: Set<string>;
  activeId: string | null;
  showReasonColumn?: boolean;
  onToggleRow: (id: string) => void;
  onToggleAll: () => void;
}

export default function TransactionTable({ transactions, selected, activeId, showReasonColumn = false, onToggleRow, onToggleAll }: Props) {
  const { t } = useTranslation();
  const allSelected = transactions.length > 0 && selected.size === transactions.length;
  const someSelected = selected.size > 0 && !allSelected;

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
          <tr>
            <th className="px-4 py-2 w-8">
              <input
                type="checkbox"
                checked={allSelected}
                ref={(el) => { if (el) el.indeterminate = someSelected; }}
                onChange={onToggleAll}
                className="cursor-pointer"
              />
            </th>
            {[t("analytics.txDate"), t("analytics.txCounterparty"), t("analytics.txDescription"), t("analytics.txAmount")].map((h) => (
              <th key={h} className="px-4 py-2 text-left">{h}</th>
            ))}
            {showReasonColumn && (
              <th className="px-4 py-2 text-left">{t("review.colReason")}</th>
            )}
          </tr>
        </thead>
        <tbody>
          {transactions.map((tx) => (
            <DraggableRow
              key={tx.id}
              transaction={tx}
              isChecked={selected.has(tx.id)}
              isDragActive={activeId !== null}
              showReasonColumn={showReasonColumn}
              onToggle={() => onToggleRow(tx.id)}
            />
          ))}
        </tbody>
      </table>
      {transactions.length === 0 && (
        <p className="px-4 py-8 text-center text-gray-400 text-sm">{t("analytics.noTransactions")}</p>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify the Analytics page still compiles** (CategoryDetail passes no `showReasonColumn` → defaults to `false` → no change in render)

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
cd frontend && git add src/api/transactions.ts src/pages/Analytics/TransactionTable.tsx
git commit -m "feat: add llm_status fields to Transaction type and showReasonColumn to TransactionTable"
```

---

## Task 4: Add i18n strings

**Files:**
- Modify: `frontend/public/locales/cs/translation.json`
- Modify: `frontend/public/locales/en/translation.json`

- [ ] **Step 1: Add Czech strings**

In `frontend/public/locales/cs/translation.json`, add under `"nav"`:

```json
"review": "Ke kontrole"
```

And add a new top-level `"review"` section after `"settings"`:

```json
"review": {
  "title": "Ke kontrole",
  "empty": "Všechny transakce mají kategorii.",
  "colReason": "Důvod",
  "countBadge": "{{count}}"
}
```

- [ ] **Step 2: Add English strings**

In `frontend/public/locales/en/translation.json`, add under `"nav"`:

```json
"review": "Needs Review"
```

And add a new top-level `"review"` section after `"settings"`:

```json
"review": {
  "title": "Needs Review",
  "empty": "All transactions are categorized.",
  "colReason": "Reason",
  "countBadge": "{{count}}"
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/public/locales/cs/translation.json frontend/public/locales/en/translation.json
git commit -m "feat: add review page i18n strings"
```

---

## Task 5: Create the Review page

**Files:**
- Create: `frontend/src/pages/Review/index.tsx`

- [ ] **Step 1: Create `frontend/src/pages/Review/index.tsx`**

```typescript
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { DndContext, type DragEndEvent, type DragOverEvent, type DragStartEvent } from "@dnd-kit/core";
import { listTransactions, bulkCategorize } from "../../api/transactions";
import { listCategoryGroups } from "../../api/categories";
import TransactionTable from "../Analytics/TransactionTable";
import CategorySidebar from "../Analytics/CategorySidebar";
import TransactionDragOverlay from "../Analytics/TransactionDragOverlay";

export default function ReviewPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [activeId, setActiveId] = useState<string | null>(null);
  const [overId, setOverId] = useState<string | null>(null);

  const { data: transactions = [], isLoading } = useQuery({
    queryKey: ["transactions", "needs_review"],
    queryFn: () => listTransactions({ needs_review: true, include_llm_status: true, limit: 500 }),
  });

  const { data: categoryGroups = [] } = useQuery({
    queryKey: ["categoryGroups"],
    queryFn: listCategoryGroups,
  });

  function invalidateAndClear() {
    setSelected(new Set());
    queryClient.invalidateQueries({ queryKey: ["transactions", "needs_review"] });
  }

  const assignMutation = useMutation({
    mutationFn: (category_id: string) =>
      bulkCategorize(Array.from(selected), category_id),
    onSuccess: invalidateAndClear,
  });

  function toggleRow(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    const allSelected = transactions.length > 0 && selected.size === transactions.length;
    setSelected(allSelected ? new Set() : new Set(transactions.map((tx) => tx.id)));
  }

  function handleDragStart(event: DragStartEvent) {
    const draggedId = event.active.id as string;
    setActiveId(draggedId);
    if (!selected.has(draggedId)) {
      setSelected(new Set([draggedId]));
    }
  }

  function handleDragOver(event: DragOverEvent) {
    setOverId(event.over ? (event.over.id as string) : null);
  }

  function handleDragEnd(event: DragEndEvent) {
    const targetId = event.over ? (event.over.id as string) : null;
    if (targetId) {
      assignMutation.mutate(targetId);
    }
    setActiveId(null);
    setOverId(null);
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{t("review.title")}</h1>
        {!isLoading && transactions.length > 0 && (
          <span className="inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-sm font-medium bg-red-100 text-red-700">
            {transactions.length}
          </span>
        )}
      </div>

      {isLoading ? (
        <p className="text-gray-400 text-sm">{t("common.loading")}</p>
      ) : transactions.length === 0 ? (
        <p className="text-gray-500 text-sm">{t("review.empty")}</p>
      ) : (
        <DndContext onDragStart={handleDragStart} onDragOver={handleDragOver} onDragEnd={handleDragEnd}>
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1 min-w-0">
              <TransactionTable
                transactions={transactions}
                selected={selected}
                activeId={activeId}
                showReasonColumn={true}
                onToggleRow={toggleRow}
                onToggleAll={toggleAll}
              />
            </div>
            <div className="lg:w-72 flex-shrink-0 lg:sticky lg:top-4 lg:self-start">
              <CategorySidebar
                categoryGroups={categoryGroups}
                currentCategoryId=""
                overId={overId}
              />
            </div>
          </div>
          <TransactionDragOverlay activeId={activeId} count={selected.size} />
        </DndContext>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Review/index.tsx
git commit -m "feat: add Review page with drag-to-categorize and reason badges"
```

---

## Task 6: Wire up routing and NavBar

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/NavBar.tsx`

- [ ] **Step 1: Add route to `App.tsx`**

In `frontend/src/App.tsx`, add the import after the existing page imports:

```typescript
import ReviewPage from "./pages/Review";
```

And add the route inside `<Routes>` after the `/imports` route:

```typescript
<Route path="/review" element={<ReviewPage />} />
```

The full `App.tsx` after the changes:

```typescript
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import AnalyticsPage from "./pages/Analytics";
import ImportsPage from "./pages/Imports";
import ReviewPage from "./pages/Review";
import RulesPage from "./pages/Rules";
import SettingsPage from "./pages/Settings";
import CategoriesPage from "./pages/Categories";
import { DataFreshnessProvider } from "./context/DataFreshness";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <DataFreshnessProvider>
        <BrowserRouter>
          <div className="min-h-screen bg-gray-50">
            <NavBar />
            <main className="p-6">
              <Routes>
                <Route path="/" element={<AnalyticsPage />} />
                <Route path="/imports" element={<ImportsPage />} />
                <Route path="/review" element={<ReviewPage />} />
                <Route path="/rules" element={<RulesPage />} />
                <Route path="/categories" element={<CategoriesPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
            </main>
          </div>
        </BrowserRouter>
      </DataFreshnessProvider>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 2: Add Review link with count badge to `NavBar.tsx`**

Replace the entire `frontend/src/components/NavBar.tsx`:

```typescript
import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import ProcessingStatus from "./ProcessingStatus";
import { useDataFreshness } from "../context/DataFreshness";
import { listTransactions } from "../api/transactions";

export default function NavBar() {
  const { markStale } = useDataFreshness();
  const { t } = useTranslation();

  const { data: reviewTxs = [] } = useQuery({
    queryKey: ["transactions", "needs_review"],
    queryFn: () => listTransactions({ needs_review: true, limit: 500 }),
    staleTime: 30_000,
  });
  const reviewCount = reviewTxs.length;

  const links = [
    { to: "/", label: t("nav.analytics") },
    { to: "/imports", label: t("nav.imports") },
    { to: "/rules", label: t("nav.rules") },
    { to: "/categories", label: t("nav.categories") },
    { to: "/settings", label: t("nav.settings") },
  ];

  return (
    <nav className="flex items-center gap-1 px-6 py-3 border-b border-gray-200 bg-white">
      {links.map((l) => (
        <NavLink
          key={l.to}
          to={l.to}
          end={l.to === "/"}
          className={({ isActive }) =>
            `px-4 py-2 rounded text-sm font-medium transition-colors ` +
            (isActive ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-100")
          }
        >
          {l.label}
        </NavLink>
      ))}
      <NavLink
        to="/review"
        className={({ isActive }) =>
          `flex items-center gap-2 px-4 py-2 rounded text-sm font-medium transition-colors ` +
          (isActive ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-100")
        }
      >
        {t("nav.review")}
        {reviewCount > 0 && (
          <span className="inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 rounded-full text-xs font-bold bg-red-500 text-white">
            {reviewCount}
          </span>
        )}
      </NavLink>
      <div className="ml-auto">
        <ProcessingStatus onJobCompleted={markStale} />
      </div>
    </nav>
  );
}
```

- [ ] **Step 3: Build to verify no TypeScript errors**

```bash
cd frontend && npm run build 2>&1 | tail -30
```

Expected: build succeeds with no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/NavBar.tsx
git commit -m "feat: add /review route and nav link with needs-review count badge"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered in |
|---|---|
| Log LLM errors as `LlmClassification` rows with `reasoning="error"` | Task 1 |
| `include_llm_status` param on `GET /api/transactions` | Task 2 |
| `llm_status` values: `no_rule_no_llm`, `llm_rejected`, `llm_error` | Task 2 |
| `llm_confidence` returned for `llm_rejected` | Task 2 |
| `TransactionOut` backwards compatible (new fields optional, default None) | Task 2 |
| Frontend `Transaction` type updated | Task 3 |
| `TransactionTable` `showReasonColumn` prop (backwards compat, default false) | Task 3 |
| Reason badges (gray/yellow/red) | Task 3 |
| i18n strings for both locales | Task 4 |
| Review page with transaction list + count in header | Task 5 |
| Drag-to-category mechanic (reuses CategorySidebar + DndContext) | Task 5 |
| Empty state when all categorized | Task 5 |
| `/review` route in App.tsx | Task 6 |
| Nav link with count badge | Task 6 |

**Type consistency check:**
- `llm_status` is `str | None` in Python, `"no_rule_no_llm" | "llm_rejected" | "llm_error" | undefined` in TypeScript — consistent with actual values produced in Task 2
- `listTransactions` param `include_llm_status?: boolean` added in Task 3 Step 1, used in Task 5 — consistent
- Query key `["transactions", "needs_review"]` used in Task 5 (Review page) and Task 6 (NavBar) — shared TanStack Query cache, so NavBar benefits from Review page data fetch automatically

**No placeholders found.**
