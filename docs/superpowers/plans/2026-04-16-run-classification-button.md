# Run Classification Button Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the two separate "Run rules" / "Classify with LLM" buttons on the Review page with a single "Run classification" button driven by three checkboxes (transfers, rules, LLM).

**Architecture:** The backend `POST /api/categorize/batch` endpoint replaces its `mode` string with a `steps` list. `CategorizationService.run_batch` runs transfer detection first (via `TransferMatcher`), then rules/LLM, based on which steps are requested. The frontend shows a permanent toolbar with three checkboxes and one button; no selection runs on all uncategorized transactions.

**Tech Stack:** FastAPI + SQLAlchemy (backend), React 19 + TanStack Query + i18next (frontend)

---

### Task 1: Update backend tests to use `steps` (they will fail — that's expected)

**Files:**
- Modify: `backend/tests/test_categorization_service.py`

- [ ] **Step 1: Update `test_run_batch_rules_mode_does_not_call_llm` to use `steps`**

In `backend/tests/test_categorization_service.py`, find the line:
```python
        result = await service.run_batch([tx.id], mode="rules")
```
Replace with:
```python
        result = await service.run_batch([tx.id], steps=["rules"])
```

- [ ] **Step 2: Add new test for transfers step**

Append to `backend/tests/test_categorization_service.py`:

```python
async def test_run_batch_transfers_step_calls_transfer_matcher():
    """run_batch with steps=['transfers'] calls TransferMatcher.match_batch and skips categorization."""
    tx_id = uuid.uuid4()
    tx = MagicMock()
    tx.id = tx_id
    tx.category_id = None

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [tx]))
    )
    mock_db.commit = AsyncMock()

    with patch("app.services.categorization_service.TransferMatcher") as MockMatcher, \
         patch("app.services.categorization_service.AnthropicClient"):
        MockMatcher.return_value.match_batch = AsyncMock(return_value=0)
        service = CategorizationService(mock_db)
        await service.run_batch([tx_id], steps=["transfers"])
        MockMatcher.assert_called_once_with(mock_db)
        MockMatcher.return_value.match_batch.assert_called_once_with([tx_id])
```

- [ ] **Step 3: Run the tests — expect failures**

```bash
cd backend && python -m pytest tests/test_categorization_service.py -v 2>&1 | tail -20
```

Expected: `test_run_batch_rules_mode_does_not_call_llm` FAILS (unexpected keyword `steps`), `test_run_batch_transfers_step_calls_transfer_matcher` FAILS (same reason).

---

### Task 2: Implement backend changes

**Files:**
- Modify: `backend/app/services/categorization_service.py`
- Modify: `backend/app/api/categorization.py`

- [ ] **Step 1: Add `TransferMatcher` import to `categorization_service.py`**

In `backend/app/services/categorization_service.py`, add to the existing imports block (after the `RulesEngine` import):

```python
from app.services.transfer_matcher import TransferMatcher
```

- [ ] **Step 2: Replace `run_batch` in `categorization_service.py`**

Replace the entire `run_batch` method (lines 173–199):

```python
    async def run_batch(self, transaction_ids: list, steps: list[str] | None = None) -> dict:
        if steps is None:
            steps = ["transfers", "rules", "llm"]

        if "transfers" in steps:
            await TransferMatcher(self._db).match_batch(transaction_ids)

        result = await self._db.execute(
            select(Transaction).where(Transaction.id.in_(transaction_ids))
        )
        transactions = result.scalars().all()

        do_rules = "rules" in steps
        do_llm = "llm" in steps

        if do_rules or do_llm:
            rules = await self._load_rules() if do_rules else []
            categories = await self._load_categories() if do_llm else []

            for tx in transactions:
                if tx.category_id is not None:
                    continue
                if do_rules and do_llm:
                    await self._categorize_one(tx, rules, categories)
                elif do_rules:
                    await self._categorize_one_rules_only(tx, rules)
                else:
                    await self._categorize_one_llm_only(tx, categories)

            await self._db.commit()

        categorized = sum(1 for tx in transactions if tx.category_id is not None)
        needs_review = sum(1 for tx in transactions if tx.category_id is None)
        return {"categorized": categorized, "needs_review": needs_review}
```

- [ ] **Step 3: Update `RecategorizeRequest` in `categorization.py`**

In `backend/app/api/categorization.py`, replace:

```python
class RecategorizeRequest(BaseModel):
    transaction_ids: list[uuid.UUID] | None = None
    mode: Literal["rules", "llm", "full"] = "full"
```

With:

```python
class RecategorizeRequest(BaseModel):
    transaction_ids: list[uuid.UUID] | None = None
    steps: list[Literal["transfers", "rules", "llm"]] = ["transfers", "rules", "llm"]
```

Also remove the unused `Literal` import if `mode` was the only use — it's still needed for `steps`, so keep it.

- [ ] **Step 4: Update the endpoint to pass `steps`**

In `backend/app/api/categorization.py`, replace:

```python
    return await service.run_batch(ids, mode=body.mode)
```

With:

```python
    return await service.run_batch(ids, steps=body.steps)
```

- [ ] **Step 5: Run the tests — all should pass**

```bash
cd backend && python -m pytest tests/test_categorization_service.py -v 2>&1 | tail -20
```

Expected: all tests PASS, including `test_run_batch_transfers_step_calls_transfer_matcher`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/categorization.py backend/app/services/categorization_service.py backend/tests/test_categorization_service.py
git commit -m "feat: replace mode with steps list in categorize/batch endpoint"
```

---

### Task 3: Update frontend API layer

**Files:**
- Modify: `frontend/src/api/categorization.ts`

- [ ] **Step 1: Update `recategorizeBatch` signature**

Replace the entire contents of `frontend/src/api/categorization.ts` with:

```ts
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
  steps: string[],
): Promise<BatchClassificationResult> {
  const { data } = await client.post<BatchClassificationResult>(
    "/api/categorize/batch",
    { transaction_ids, steps },
  );
  return data;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/categorization.ts
git commit -m "feat: update recategorizeBatch to accept steps array"
```

---

### Task 4: Update i18n translation files

**Files:**
- Modify: `frontend/public/locales/en/translation.json`
- Modify: `frontend/public/locales/cs/translation.json`

- [ ] **Step 1: Update English translations**

In `frontend/public/locales/en/translation.json`, replace the `"review"` block (lines 198–210):

```json
  "review": {
    "title": "Needs Review",
    "empty": "All transactions are categorized.",
    "colReason": "Reason",
    "countBadge": "{{count}}",
    "reasonNoRule": "no rule",
    "reasonLlmError": "LLM error",
    "reasonLlmRejected": "LLM rejected",
    "runClassification": "Run classification",
    "stepTransfers": "Transfers",
    "stepRules": "Rules",
    "stepLlm": "LLM",
    "selectedCount": "{{count}} selected",
    "runError": "Action failed"
  }
```

- [ ] **Step 2: Update Czech translations**

In `frontend/public/locales/cs/translation.json`, replace the `"review"` block (lines 198–210):

```json
  "review": {
    "title": "Ke kontrole",
    "empty": "Všechny transakce mají kategorii.",
    "colReason": "Důvod",
    "countBadge": "{{count}}",
    "reasonNoRule": "bez pravidla",
    "reasonLlmError": "chyba LLM",
    "reasonLlmRejected": "LLM zamítlo",
    "runClassification": "Spustit klasifikaci",
    "stepTransfers": "Přesuny",
    "stepRules": "Pravidla",
    "stepLlm": "LLM",
    "selectedCount": "{{count}} vybráno",
    "runError": "Akce selhala"
  }
```

- [ ] **Step 3: Commit**

```bash
git add frontend/public/locales/en/translation.json frontend/public/locales/cs/translation.json
git commit -m "feat: update i18n keys for run classification button"
```

---

### Task 5: Refactor Review page

**Files:**
- Modify: `frontend/src/pages/Review/index.tsx`

- [ ] **Step 1: Replace the entire file**

Replace `frontend/src/pages/Review/index.tsx` with:

```tsx
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { DndContext, type DragEndEvent, type DragOverEvent, type DragStartEvent } from "@dnd-kit/core";
import { listTransactions, bulkCategorize } from "../../api/transactions";
import { listCategoryGroups } from "../../api/categories";
import { listAccounts } from "../../api/accounts";
import { recategorizeBatch } from "../../api/categorization";
import TransactionTable from "../Analytics/TransactionTable";
import CategorySidebar from "../Analytics/CategorySidebar";
import TransactionDragOverlay from "../Analytics/TransactionDragOverlay";
import SlideOverPanel from "../../components/SlideOverPanel";
import RuleForm, { type RulePrefill } from "../Rules/RuleForm";

export default function ReviewPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [activeId, setActiveId] = useState<string | null>(null);
  const [overId, setOverId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [rulePrefill, setRulePrefill] = useState<RulePrefill | null>(null);
  const [steps, setSteps] = useState({ transfers: true, rules: true, llm: false });

  const { data: transactions = [], isLoading } = useQuery({
    queryKey: ["transactions", "needs_review", { include_llm_status: true }],
    queryFn: () => listTransactions({ needs_review: true, include_llm_status: true, limit: 500 }),
  });

  const { data: categoryGroups = [] } = useQuery({
    queryKey: ["categoryGroups"],
    queryFn: listCategoryGroups,
  });

  const { data: accounts = [] } = useQuery({
    queryKey: ["accounts"],
    queryFn: listAccounts,
  });

  const accountMap = Object.fromEntries(accounts.map((a) => [a.id, a.name]));

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

  const activeSteps = (["transfers", "rules", "llm"] as const).filter((s) => steps[s]);

  const runClassificationMutation = useMutation({
    mutationFn: () => recategorizeBatch(Array.from(selected), activeSteps),
    onSuccess: invalidateAndClear,
    onError: () => setActionError(t("review.runError")),
  });

  const categorizeMutation = useMutation({
    mutationFn: ({ ids, categoryId }: { ids: string[]; categoryId: string | null }) =>
      bulkCategorize(ids, categoryId),
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
    <div className="max-w-7xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{t("review.title")}</h1>
        {!isLoading && transactions.length > 0 && (
          <span className="inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-sm font-medium bg-red-100 text-red-700">
            {transactions.length}
          </span>
        )}
      </div>

      <div className="mb-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            {(["transfers", "rules", "llm"] as const).map((step) => (
              <label key={step} className="flex items-center gap-1.5 text-sm text-gray-700 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={steps[step]}
                  onChange={(e) => setSteps((prev) => ({ ...prev, [step]: e.target.checked }))}
                  className="rounded border-gray-300 text-blue-600"
                />
                {t(`review.step${step.charAt(0).toUpperCase() + step.slice(1)}`)}
              </label>
            ))}
          </div>
          <button
            onClick={() => runClassificationMutation.mutate()}
            disabled={activeSteps.length === 0 || runClassificationMutation.isPending}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {runClassificationMutation.isPending && (
              <svg className="animate-spin h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            )}
            {t("review.runClassification")}
          </button>
          {selected.size > 0 && (
            <span className="text-sm text-gray-500">
              {t("review.selectedCount", { count: selected.size })}
            </span>
          )}
        </div>
        {actionError && (
          <p className="mt-1 text-sm text-red-600">{actionError}</p>
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
                accountMap={accountMap}
                categoryGroups={categoryGroups}
                onToggleRow={toggleRow}
                onToggleAll={toggleAll}
                onCategorize={(ids, categoryId) => categorizeMutation.mutate({ ids, categoryId })}
                onCreateRule={setRulePrefill}
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

      <SlideOverPanel
        open={rulePrefill !== null}
        onClose={() => setRulePrefill(null)}
        title={t("rules.newRule")}
      >
        {rulePrefill && (
          <RuleForm prefill={rulePrefill} onClose={() => setRulePrefill(null)} />
        )}
      </SlideOverPanel>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Review/index.tsx
git commit -m "feat: combine run buttons into single run classification with step checkboxes"
```
