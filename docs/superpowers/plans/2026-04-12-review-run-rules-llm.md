# Review Page: Run Rules / Run LLM on Selected Items

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add "Spustit pravidla" and "Klasifikovat LLM" action buttons to the Review page that run rules-only or LLM-only classification on selected transactions.

**Architecture:** Extend the existing `POST /api/categorize/batch` endpoint with a `mode` field (`"rules"`, `"llm"`, `"full"`). Add two new service methods for each independent path. Frontend adds a toolbar in `Review/index.tsx` that appears when rows are selected.

**Tech Stack:** Python/FastAPI, SQLAlchemy async, Anthropic SDK, React/TypeScript, TanStack Query, react-i18next.

---

## File Map

| File | Change |
|------|--------|
| `backend/app/services/categorization_service.py` | Add `_categorize_one_rules_only`, `_categorize_one_llm_only`; update `run_batch` to accept `mode` |
| `backend/app/api/categorization.py` | Add `mode` field to `RecategorizeRequest`; pass to `run_batch` |
| `backend/tests/test_categorization_service.py` | Add tests for new methods and mode dispatch |
| `frontend/src/api/categorization.ts` | Add `recategorizeBatch` function |
| `frontend/public/locales/cs/translation.json` | Add 4 new `review.*` keys |
| `frontend/public/locales/en/translation.json` | Add 4 new `review.*` keys |
| `frontend/src/pages/Review/index.tsx` | Add toolbar with two mutations |

---

### Task 1: Add `_categorize_one_rules_only` to the service

**Files:**
- Modify: `backend/app/services/categorization_service.py`
- Test: `backend/tests/test_categorization_service.py`

- [ ] **Step 1: Write two failing tests**

Append to `backend/tests/test_categorization_service.py`:

```python
async def test_rules_only_categorizes_on_match():
    """_categorize_one_rules_only sets category when a rule matches."""
    groceries_id = uuid.uuid4()
    rule = {
        "id": uuid.uuid4(),
        "match_type": "counterparty_contains",
        "match_value": {"value": "ALBERT"},
        "category_id": groceries_id,
        "priority": 100,
        "enabled": True,
    }
    tx = MagicMock()
    tx.counterparty_name = "ALBERT SUPERMARKET"
    tx.description = ""
    tx.amount = Decimal("-250.00")
    tx.category_id = None
    tx.booking_date = date(2026, 1, 1)
    tx.value_date = None
    tx.currency = "CZK"
    tx.counterparty_account = None
    tx.raw_reference = None

    mock_db = AsyncMock()
    mock_rule_obj = MagicMock()
    mock_rule_obj.hit_count = 0
    mock_db.get = AsyncMock(return_value=mock_rule_obj)

    with patch("app.services.categorization_service.AnthropicClient") as MockLLM:
        service = CategorizationService(mock_db)
        await service._categorize_one_rules_only(tx, [rule])
        MockLLM.return_value.classify.assert_not_called()

    assert tx.category_id == groceries_id
    assert tx.categorization_source == "rule"
    assert tx.confidence == Decimal("1.0")


async def test_rules_only_leaves_uncategorized_when_no_match():
    """_categorize_one_rules_only does nothing when no rule matches."""
    tx = MagicMock()
    tx.counterparty_name = "UNKNOWN SHOP"
    tx.description = ""
    tx.amount = Decimal("-100.00")
    tx.category_id = None
    tx.booking_date = date(2026, 1, 1)
    tx.value_date = None
    tx.currency = "CZK"
    tx.counterparty_account = None
    tx.raw_reference = None

    mock_db = AsyncMock()

    with patch("app.services.categorization_service.AnthropicClient") as MockLLM:
        service = CategorizationService(mock_db)
        await service._categorize_one_rules_only(tx, [])
        MockLLM.return_value.classify.assert_not_called()

    assert tx.category_id is None
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && source .venv/bin/activate
pytest tests/test_categorization_service.py::test_rules_only_categorizes_on_match tests/test_categorization_service.py::test_rules_only_leaves_uncategorized_when_no_match -v
```

Expected: FAIL — `AttributeError: 'CategorizationService' object has no attribute '_categorize_one_rules_only'`

- [ ] **Step 3: Add `_categorize_one_rules_only` to the service**

In `backend/app/services/categorization_service.py`, add this method after `_categorize_one`:

```python
async def _categorize_one_rules_only(self, tx: Transaction, rules: list[dict]) -> None:
    row = TransactionRow(
        booking_date=tx.booking_date,
        value_date=tx.value_date,
        amount=tx.amount,
        currency=tx.currency,
        counterparty_name=tx.counterparty_name,
        counterparty_account=tx.counterparty_account,
        description=tx.description,
        raw_reference=tx.raw_reference,
    )
    match = RulesEngine.apply(row, rules)
    if match:
        tx.category_id = match.category_id
        tx.categorization_source = "rule"
        tx.confidence = Decimal("1.0")
        rule_obj = await self._db.get(Rule, match.rule_id)
        if rule_obj:
            rule_obj.hit_count += 1
            rule_obj.last_hit_at = datetime.now(timezone.utc)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_categorization_service.py::test_rules_only_categorizes_on_match tests/test_categorization_service.py::test_rules_only_leaves_uncategorized_when_no_match -v
```

Expected: both PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/categorization_service.py backend/tests/test_categorization_service.py
git commit -m "feat: add _categorize_one_rules_only to CategorizationService"
```

---

### Task 2: Add `_categorize_one_llm_only` to the service

**Files:**
- Modify: `backend/app/services/categorization_service.py`
- Test: `backend/tests/test_categorization_service.py`

- [ ] **Step 1: Write two failing tests**

Append to `backend/tests/test_categorization_service.py`:

```python
async def test_llm_only_skips_rules_and_categorizes():
    """_categorize_one_llm_only calls LLM and sets category when confidence is high."""
    from app.services.anthropic_client import CONFIDENCE_THRESHOLD
    from unittest.mock import AsyncMock as AM, patch

    groceries_id = uuid.uuid4()

    tx = MagicMock()
    tx.id = uuid.uuid4()
    tx.counterparty_name = "ALBERT SUPERMARKET"
    tx.description = ""
    tx.amount = Decimal("-250.00")
    tx.category_id = None
    tx.booking_date = date(2026, 1, 1)
    tx.value_date = None
    tx.currency = "CZK"
    tx.counterparty_account = None
    tx.raw_reference = None

    mock_category = MagicMock()
    mock_category.id = groceries_id

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=lambda: mock_category)
    )
    added_rows = []
    mock_db.add = MagicMock(side_effect=added_rows.append)

    llm_result = MagicMock()
    llm_result.category_name = "Groceries"
    llm_result.confidence = CONFIDENCE_THRESHOLD  # exactly at threshold = accepted
    llm_result.reasoning = "supermarket"
    llm_result.model = "claude-haiku-4-5"
    llm_result.prompt_tokens = 100
    llm_result.completion_tokens = 50

    with patch("app.services.categorization_service.AnthropicClient") as MockLLM:
        MockLLM.return_value.classify.return_value = llm_result
        service = CategorizationService(mock_db)
        await service._categorize_one_llm_only(tx, [("Groceries", None)])

    assert tx.category_id == groceries_id
    assert tx.categorization_source == "llm"
    assert len(added_rows) == 1  # LlmClassification log written


async def test_llm_only_error_writes_classification_row():
    """_categorize_one_llm_only on LLM error writes error log, leaves uncategorized."""
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
    added_rows = []
    mock_db.add = MagicMock(side_effect=added_rows.append)

    with patch("app.services.categorization_service.AnthropicClient") as MockLLM:
        MockLLM.return_value.classify.side_effect = AnthropicClassificationError("timeout")
        service = CategorizationService(mock_db)
        await service._categorize_one_llm_only(tx, [("Groceries", None)])

    assert tx.category_id is None
    assert len(added_rows) == 1
    assert added_rows[0].reasoning == "error"
    assert added_rows[0].accepted is False
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_categorization_service.py::test_llm_only_skips_rules_and_categorizes tests/test_categorization_service.py::test_llm_only_error_writes_classification_row -v
```

Expected: FAIL — `AttributeError: 'CategorizationService' object has no attribute '_categorize_one_llm_only'`

- [ ] **Step 3: Add `_categorize_one_llm_only` to the service**

In `backend/app/services/categorization_service.py`, add this method after `_categorize_one_rules_only`:

```python
async def _categorize_one_llm_only(self, tx: Transaction, categories: list[tuple[str, str | None]]) -> None:
    try:
        result = await asyncio.to_thread(
            self._llm.classify,
            counterparty=tx.counterparty_name,
            description=tx.description,
            amount=tx.amount,
            categories=categories,
        )
    except AnthropicClassificationError:
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

    cat_result = await self._db.execute(
        select(Category).where(Category.name == result.category_name)
    )
    category = cat_result.scalar_one_or_none()

    accepted = result.confidence >= CONFIDENCE_THRESHOLD and category is not None
    log = LlmClassification(
        transaction_id=tx.id,
        model=result.model,
        suggested_category_id=category.id if category else None,
        accepted=accepted,
        confidence=result.confidence,
        reasoning=result.reasoning,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
    )
    self._db.add(log)

    if accepted:
        tx.category_id = category.id
        tx.categorization_source = "llm"
        tx.confidence = result.confidence
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_categorization_service.py::test_llm_only_skips_rules_and_categorizes tests/test_categorization_service.py::test_llm_only_error_writes_classification_row -v
```

Expected: both PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/categorization_service.py backend/tests/test_categorization_service.py
git commit -m "feat: add _categorize_one_llm_only to CategorizationService"
```

---

### Task 3: Update `run_batch` to dispatch by mode

**Files:**
- Modify: `backend/app/services/categorization_service.py`
- Test: `backend/tests/test_categorization_service.py`

- [ ] **Step 1: Write a failing test**

Append to `backend/tests/test_categorization_service.py`:

```python
async def test_run_batch_rules_mode_does_not_call_llm():
    """run_batch with mode='rules' never calls LLM even when no rule matches."""
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
    # execute returns transactions list
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [tx]))
    )
    mock_db.commit = AsyncMock()

    with patch("app.services.categorization_service.AnthropicClient") as MockLLM:
        service = CategorizationService(mock_db)
        # patch internal loaders to return empty lists
        service._load_rules = AsyncMock(return_value=[])
        service._load_categories = AsyncMock(return_value=[])
        result = await service.run_batch([tx.id], mode="rules")
        MockLLM.return_value.classify.assert_not_called()

    assert result["needs_review"] == 1
    assert result["categorized"] == 0
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest tests/test_categorization_service.py::test_run_batch_rules_mode_does_not_call_llm -v
```

Expected: FAIL — `TypeError: run_batch() got an unexpected keyword argument 'mode'`

- [ ] **Step 3: Update `run_batch` signature and dispatch**

Replace the `run_batch` method in `backend/app/services/categorization_service.py`:

```python
async def run_batch(self, transaction_ids: list, mode: str = "full") -> dict:
    result = await self._db.execute(
        select(Transaction).where(Transaction.id.in_(transaction_ids))
    )
    transactions = result.scalars().all()

    rules = await self._load_rules() if mode in ("rules", "full") else []
    categories = await self._load_categories() if mode in ("llm", "full") else []

    categorized = 0
    needs_review = 0
    for tx in transactions:
        if tx.category_id is not None:
            continue
        if mode == "rules":
            await self._categorize_one_rules_only(tx, rules)
        elif mode == "llm":
            await self._categorize_one_llm_only(tx, categories)
        else:
            await self._categorize_one(tx, rules, categories)
        if tx.category_id is not None:
            categorized += 1
        else:
            needs_review += 1

    await self._db.commit()
    return {"categorized": categorized, "needs_review": needs_review}
```

- [ ] **Step 4: Run all service tests to confirm they pass**

```bash
pytest tests/test_categorization_service.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/categorization_service.py backend/tests/test_categorization_service.py
git commit -m "feat: run_batch dispatches by mode (rules/llm/full)"
```

---

### Task 4: Update the API endpoint

**Files:**
- Modify: `backend/app/api/categorization.py`

- [ ] **Step 1: Update `RecategorizeRequest` and the endpoint**

Replace the entire contents of `backend/app/api/categorization.py`:

```python
import uuid
from typing import Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import Transaction
from app.services.categorization_service import CategorizationService

router = APIRouter()

class RecategorizeRequest(BaseModel):
    transaction_ids: list[uuid.UUID] | None = None
    mode: Literal["rules", "llm", "full"] = "full"

class RecategorizeResult(BaseModel):
    categorized: int
    needs_review: int

@router.post("/batch", response_model=RecategorizeResult)
async def recategorize_batch(body: RecategorizeRequest, db: AsyncSession = Depends(get_db)):
    if body.transaction_ids:
        ids = body.transaction_ids
    else:
        result = await db.execute(
            select(Transaction.id).where(Transaction.category_id == None)
        )
        ids = [r[0] for r in result.all()]
    service = CategorizationService(db)
    return await service.run_batch(ids, mode=body.mode)
```

- [ ] **Step 2: Run the full backend test suite**

```bash
pytest -v
```

Expected: all existing tests PASS (Settings page uses `POST /batch` without `mode` — defaults to `"full"`, backward-compatible)

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/categorization.py
git commit -m "feat: add mode param to POST /api/categorize/batch"
```

---

### Task 5: Add `recategorizeBatch` to the frontend API layer

**Files:**
- Modify: `frontend/src/api/categorization.ts`

- [ ] **Step 1: Add the function**

Replace the contents of `frontend/src/api/categorization.ts`:

```typescript
import client from "./client";

export interface BatchClassificationResult {
  categorized: number;
  needs_review: number;
}

export async function runBatchClassification(): Promise<BatchClassificationResult> {
  const { data } = await client.post<BatchClassificationResult>(
    "/api/categorize/batch",
    {},
  );
  return data;
}

export async function recategorizeBatch(
  transaction_ids: string[],
  mode: "rules" | "llm" | "full",
): Promise<BatchClassificationResult> {
  const { data } = await client.post<BatchClassificationResult>(
    "/api/categorize/batch",
    { transaction_ids, mode },
  );
  return data;
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npm run build 2>&1 | tail -5
```

Expected: no TypeScript errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/categorization.ts
git commit -m "feat: add recategorizeBatch to categorization API client"
```

---

### Task 6: Add i18n keys

**Files:**
- Modify: `frontend/public/locales/cs/translation.json`
- Modify: `frontend/public/locales/en/translation.json`

- [ ] **Step 1: Add keys to Czech locale**

In `frontend/public/locales/cs/translation.json`, replace the `"review"` block:

```json
"review": {
  "title": "Ke kontrole",
  "empty": "Všechny transakce mají kategorii.",
  "colReason": "Důvod",
  "countBadge": "{{count}}",
  "reasonNoRule": "bez pravidla",
  "reasonLlmError": "chyba LLM",
  "reasonLlmRejected": "LLM zamítlo",
  "runRules": "Spustit pravidla",
  "runLlm": "Klasifikovat LLM",
  "selectedCount": "{{count}} vybráno",
  "runError": "Akce selhala"
}
```

- [ ] **Step 2: Add keys to English locale**

In `frontend/public/locales/en/translation.json`, replace the `"review"` block:

```json
"review": {
  "title": "Needs Review",
  "empty": "All transactions are categorized.",
  "colReason": "Reason",
  "countBadge": "{{count}}",
  "reasonNoRule": "no rule",
  "reasonLlmError": "LLM error",
  "reasonLlmRejected": "LLM rejected",
  "runRules": "Run rules",
  "runLlm": "Classify with LLM",
  "selectedCount": "{{count}} selected",
  "runError": "Action failed"
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/public/locales/cs/translation.json frontend/public/locales/en/translation.json
git commit -m "feat: add i18n keys for review page action toolbar"
```

---

### Task 7: Add action toolbar to the Review page

**Files:**
- Modify: `frontend/src/pages/Review/index.tsx`

- [ ] **Step 1: Update the Review page**

Replace the entire contents of `frontend/src/pages/Review/index.tsx`:

```typescript
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { DndContext, type DragEndEvent, type DragOverEvent, type DragStartEvent } from "@dnd-kit/core";
import { listTransactions, bulkCategorize } from "../../api/transactions";
import { listCategoryGroups } from "../../api/categories";
import { recategorizeBatch } from "../../api/categorization";
import TransactionTable from "../Analytics/TransactionTable";
import CategorySidebar from "../Analytics/CategorySidebar";
import TransactionDragOverlay from "../Analytics/TransactionDragOverlay";

export default function ReviewPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [activeId, setActiveId] = useState<string | null>(null);
  const [overId, setOverId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const { data: transactions = [], isLoading } = useQuery({
    queryKey: ["transactions", "needs_review", { include_llm_status: true }],
    queryFn: () => listTransactions({ needs_review: true, include_llm_status: true, limit: 500 }),
  });

  const { data: categoryGroups = [] } = useQuery({
    queryKey: ["categoryGroups"],
    queryFn: listCategoryGroups,
  });

  function invalidateAndClear() {
    setSelected(new Set());
    setActionError(null);
    queryClient.invalidateQueries({ queryKey: ["transactions", "needs_review"] });
  }

  const assignMutation = useMutation({
    mutationFn: (category_id: string) =>
      bulkCategorize(Array.from(selected), category_id),
    onSuccess: invalidateAndClear,
    onError: () => {
      setActiveId(null);
      setOverId(null);
    },
  });

  const runRulesMutation = useMutation({
    mutationFn: () => recategorizeBatch(Array.from(selected), "rules"),
    onSuccess: invalidateAndClear,
    onError: () => setActionError(t("review.runError")),
  });

  const runLlmMutation = useMutation({
    mutationFn: () => recategorizeBatch(Array.from(selected), "llm"),
    onSuccess: invalidateAndClear,
    onError: () => setActionError(t("review.runError")),
  });

  const isActing = runRulesMutation.isPending || runLlmMutation.isPending;

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

      {selected.size > 0 && (
        <div className="mb-4">
          <div className="flex items-center gap-2">
            <button
              onClick={() => runRulesMutation.mutate()}
              disabled={isActing}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {runRulesMutation.isPending && (
                <svg className="animate-spin h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
              )}
              {t("review.runRules")}
            </button>
            <button
              onClick={() => runLlmMutation.mutate()}
              disabled={isActing}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {runLlmMutation.isPending && (
                <svg className="animate-spin h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
              )}
              {t("review.runLlm")}
            </button>
            <span className="text-sm text-gray-500">
              {t("review.selectedCount", { count: selected.size })}
            </span>
          </div>
          {actionError && (
            <p className="mt-1 text-sm text-red-600">{actionError}</p>
          )}
        </div>
      )}

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

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: no TypeScript errors

- [ ] **Step 3: Smoke-test in browser**

```bash
# Terminal 1
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload

# Terminal 2
cd frontend && npm run dev
```

Open `http://localhost:5173`, go to "Ke kontrole", select one or more rows — confirm the toolbar appears with "Spustit pravidla" and "Klasifikovat LLM" buttons.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Review/index.tsx
git commit -m "feat: add run-rules / run-LLM toolbar to Review page"
```
