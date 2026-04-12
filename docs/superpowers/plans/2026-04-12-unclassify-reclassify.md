# Unclassify & Re-classify Transactions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to clear a transaction's category and trigger LLM re-classification on all unclassified transactions.

**Architecture:** Extend the existing `PATCH /transactions/bulk-categorize` endpoint to accept `null` as `category_id`, add a "Clear category" button to the Analytics selection toolbar, and add a "Re-classify unclassified" button to the Settings page.

**Tech Stack:** FastAPI, SQLAlchemy, React, TypeScript, TanStack Query, react-i18next, Tailwind CSS

---

## File Map

| File | Change |
|------|--------|
| `backend/app/api/transactions.py` | Allow `category_id: uuid.UUID \| None` in `BulkCategorizeRequest`; handle null clearing |
| `backend/tests/test_bulk_categorize.py` | Add tests for null `category_id` (unclassify path) |
| `frontend/public/locales/en/translation.json` | Add new i18n keys |
| `frontend/public/locales/cs/translation.json` | Add new i18n keys |
| `frontend/src/api/transactions.ts` | Add `bulkCategorize()` function |
| `frontend/src/api/categorization.ts` | New file — `runBatchClassification()` |
| `frontend/src/pages/Analytics/CategoryDetail.tsx` | Add selection toolbar with "Clear category" button |
| `frontend/src/pages/Settings/index.tsx` | Add `CategorizationSection` component |

---

## Task 1: Extend backend bulk-categorize to accept null

**Files:**
- Modify: `backend/app/api/transactions.py:115-131`
- Modify: `backend/tests/test_bulk_categorize.py`

- [ ] **Step 1: Add failing tests for null category_id**

Add to `backend/tests/test_bulk_categorize.py` (keep all existing tests, add these at the end):

```python
async def test_bulk_unclassify_happy_path(client, mock_db):
    mock_result = MagicMock()
    mock_db.execute.return_value = mock_result

    transaction_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

    resp = await client.patch(
        "/api/transactions/bulk-categorize",
        json={"transaction_ids": transaction_ids, "category_id": None},
    )

    assert resp.status_code == 204
    assert mock_db.execute.called
    assert mock_db.commit.called


async def test_bulk_unclassify_omitting_category_id_still_rejected(client, mock_db):
    """category_id must be explicitly present (even if null); omitting it is a 422."""
    transaction_ids = [str(uuid.uuid4())]

    resp = await client.patch(
        "/api/transactions/bulk-categorize",
        json={"transaction_ids": transaction_ids},
    )

    assert resp.status_code == 422
    assert not mock_db.commit.called
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_bulk_categorize.py -v
```

Expected: `test_bulk_unclassify_happy_path` FAILS with 422 (current model rejects null).

- [ ] **Step 3: Update BulkCategorizeRequest and endpoint**

In `backend/app/api/transactions.py`, replace lines 115–131:

```python
class BulkCategorizeRequest(BaseModel):
    transaction_ids: Annotated[list[uuid.UUID], Field(min_length=1)]
    category_id: uuid.UUID | None


@router.patch("/bulk-categorize", status_code=204)
async def bulk_categorize(body: BulkCategorizeRequest, db: AsyncSession = Depends(get_db)):
    if body.category_id is not None:
        values = dict(
            category_id=body.category_id,
            categorization_source="manual",
            confidence=None,
        )
    else:
        values = dict(
            category_id=None,
            categorization_source=None,
            confidence=None,
        )
    await db.execute(
        Transaction.__table__.update()
        .where(Transaction.id.in_(body.transaction_ids))
        .values(**values)
    )
    await db.commit()
```

- [ ] **Step 4: Run all bulk-categorize tests**

```bash
cd backend && python -m pytest tests/test_bulk_categorize.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/transactions.py backend/tests/test_bulk_categorize.py
git commit -m "feat: allow null category_id in bulk-categorize to unclassify transactions"
```

---

## Task 2: Add i18n keys

**Files:**
- Modify: `frontend/public/locales/en/translation.json`
- Modify: `frontend/public/locales/cs/translation.json`

- [ ] **Step 1: Add English keys**

In `frontend/public/locales/en/translation.json`, add to the `"analytics"` object (after `"loadingTrends"`):

```json
"clearCategory": "Clear category",
"clearingCategory": "Clearing…",
"clearFailed": "Failed to clear. Please try again."
```

And add to the `"settings"` object (after `"llmColCost"`):

```json
"categorizationTitle": "Categorization",
"categorizationDesc": "Run LLM classification on all transactions without a category.",
"reclassifyBtn": "Re-classify unclassified",
"reclassifyRunning": "Running…",
"reclassifyDone": "Done — {{categorized}} categorized, {{needs_review}} need review",
"reclassifyFailed": "Classification failed. Please try again."
```

- [ ] **Step 2: Add Czech keys**

In `frontend/public/locales/cs/translation.json`, add to the `"analytics"` object (after `"loadingTrends"`):

```json
"clearCategory": "Zrušit kategorii",
"clearingCategory": "Mazání…",
"clearFailed": "Zrušení selhalo. Zkuste to znovu."
```

And add to the `"settings"` object (after `"llmColCost"`):

```json
"categorizationTitle": "Kategorizace",
"categorizationDesc": "Spustit LLM klasifikaci na všech transakcích bez kategorie.",
"reclassifyBtn": "Překlasifikovat nekategorizované",
"reclassifyRunning": "Probíhá…",
"reclassifyDone": "Hotovo — {{categorized}} kategorizováno, {{needs_review}} ke kontrole",
"reclassifyFailed": "Klasifikace selhala. Zkuste to znovu."
```

- [ ] **Step 3: Commit**

```bash
git add frontend/public/locales/en/translation.json frontend/public/locales/cs/translation.json
git commit -m "feat: add i18n keys for unclassify and re-classify features"
```

---

## Task 3: Frontend API layer

**Files:**
- Modify: `frontend/src/api/transactions.ts`
- Create: `frontend/src/api/categorization.ts`

- [ ] **Step 1: Add bulkCategorize to transactions.ts**

In `frontend/src/api/transactions.ts`, add after the `listTransactions` function:

```typescript
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

- [ ] **Step 2: Create categorization.ts**

Create `frontend/src/api/categorization.ts`:

```typescript
import client from "./client";

export interface BatchClassificationResult {
  categorized: number;
  needs_review: number;
}

export async function runBatchClassification(): Promise<BatchClassificationResult> {
  const { data } = await client.post<BatchClassificationResult>(
    "/api/categorization/batch",
    {},
  );
  return data;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/transactions.ts frontend/src/api/categorization.ts
git commit -m "feat: add bulkCategorize and runBatchClassification API functions"
```

---

## Task 4: Analytics — selection toolbar with "Clear category" button

**Files:**
- Modify: `frontend/src/pages/Analytics/CategoryDetail.tsx`

The current `CategoryDetail.tsx` has `selected` state and a `bulkMutation` wired only to drag-and-drop. The translation keys for the selection toolbar (`selectedCount`, `assignTo`, `pickCategory`, `apply`, `applying`, `applyFailed`) exist but the toolbar UI is not yet rendered. This task adds the toolbar with both assign and clear actions.

- [ ] **Step 1: Update CategoryDetail.tsx**

Replace the full contents of `frontend/src/pages/Analytics/CategoryDetail.tsx` with:

```typescript
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { DndContext, type DragEndEvent, type DragOverEvent, type DragStartEvent } from "@dnd-kit/core";
import { listTransactions, bulkCategorize } from "../../api/transactions";
import { listCategoryGroups } from "../../api/categories";
import TransactionTable from "./TransactionTable";
import CategorySidebar from "./CategorySidebar";
import TransactionDragOverlay from "./TransactionDragOverlay";

interface Props {
  categoryId: string;
  categoryName: string;
  year: number;
  month: number;
  onBack: () => void;
}

export default function CategoryDetail({ categoryId, categoryName, year, month, onBack }: Props) {
  const { t } = useTranslation();
  const dateFrom = `${year}-${String(month).padStart(2, "0")}-01`;
  const dateTo = `${year}-${String(month).padStart(2, "0")}-31`;

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [activeId, setActiveId] = useState<string | null>(null);
  const [overId, setOverId] = useState<string | null>(null);
  const [assignTarget, setAssignTarget] = useState<string>("");

  const queryClient = useQueryClient();

  const { data: transactions = [], isLoading } = useQuery({
    queryKey: ["transactions", categoryId, year, month],
    queryFn: () => listTransactions({ date_from: dateFrom, date_to: dateTo, category_id: categoryId, limit: 500 }),
  });

  const { data: categoryGroups = [] } = useQuery({
    queryKey: ["categoryGroups"],
    queryFn: listCategoryGroups,
  });

  const allCategories = categoryGroups.flatMap((g: any) => g.categories ?? []);

  function invalidateAndClear() {
    setSelected(new Set());
    setAssignTarget("");
    queryClient.invalidateQueries({ queryKey: ["transactions"] });
  }

  const assignMutation = useMutation({
    mutationFn: (category_id: string) =>
      bulkCategorize(Array.from(selected), category_id),
    onSuccess: invalidateAndClear,
  });

  const clearMutation = useMutation({
    mutationFn: () => bulkCategorize(Array.from(selected), null),
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
    if (targetId && targetId !== categoryId) {
      assignMutation.mutate(targetId);
    }
    setActiveId(null);
    setOverId(null);
  }

  const exportUrl = `/api/transactions/export?date_from=${dateFrom}&date_to=${dateTo}&category_id=${categoryId}`;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <button className="text-blue-600 text-sm hover:underline" onClick={onBack}>
          {t("analytics.backToGroup")}
        </button>
        <a href={exportUrl} className="text-blue-600 text-sm hover:underline" download>
          {t("analytics.exportCsv")}
        </a>
      </div>
      <h2 className="text-xl font-bold mb-4">{categoryName}</h2>

      {selected.size > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-3 bg-blue-50 border border-blue-200 rounded-lg px-4 py-2.5 text-sm">
          <span className="text-blue-700 font-medium">
            {t("analytics.selectedCount", { count: selected.size })}
          </span>
          <span className="text-gray-500">{t("analytics.assignTo")}</span>
          <select
            className="border border-gray-300 rounded px-2 py-1 text-sm"
            value={assignTarget}
            onChange={(e) => setAssignTarget(e.target.value)}
          >
            <option value="">{t("analytics.pickCategory")}</option>
            {allCategories.map((c: any) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <button
            className="bg-blue-600 text-white px-3 py-1 rounded text-sm font-medium disabled:opacity-50"
            disabled={!assignTarget || assignMutation.isPending}
            onClick={() => assignMutation.mutate(assignTarget)}
          >
            {assignMutation.isPending ? t("analytics.applying") : t("analytics.apply")}
          </button>
          <button
            className="bg-white border border-gray-300 text-gray-700 px-3 py-1 rounded text-sm font-medium disabled:opacity-50 hover:bg-gray-50"
            disabled={clearMutation.isPending}
            onClick={() => clearMutation.mutate()}
          >
            {clearMutation.isPending ? t("analytics.clearingCategory") : t("analytics.clearCategory")}
          </button>
          {(assignMutation.isError || clearMutation.isError) && (
            <span className="text-red-500">
              {assignMutation.isError ? t("analytics.applyFailed") : t("analytics.clearFailed")}
            </span>
          )}
        </div>
      )}

      {isLoading ? (
        <p className="text-gray-400 text-sm">{t("common.loading")}</p>
      ) : (
        <DndContext onDragStart={handleDragStart} onDragOver={handleDragOver} onDragEnd={handleDragEnd}>
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1 min-w-0">
              <TransactionTable
                transactions={transactions}
                selected={selected}
                activeId={activeId}
                onToggleRow={toggleRow}
                onToggleAll={toggleAll}
              />
            </div>
            <div className="lg:w-72 flex-shrink-0 lg:sticky lg:top-4 lg:self-start">
              <CategorySidebar
                categoryGroups={categoryGroups}
                currentCategoryId={categoryId}
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
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Analytics/CategoryDetail.tsx
git commit -m "feat: add selection toolbar with assign and clear category actions"
```

---

## Task 5: Settings — Re-classify section

**Files:**
- Modify: `frontend/src/pages/Settings/index.tsx`

- [ ] **Step 1: Add CategorizationSection to Settings**

In `frontend/src/pages/Settings/index.tsx`:

1. Add import at the top (after existing imports):

```typescript
import { runBatchClassification, type BatchClassificationResult } from "../../api/categorization";
```

2. Add the `CategorizationSection` component before the `SettingsPage` function:

```typescript
function CategorizationSection() {
  const { t } = useTranslation();
  const [result, setResult] = useState<BatchClassificationResult | null>(null);

  const classify = useMutation({
    mutationFn: runBatchClassification,
    onMutate: () => setResult(null),
    onSuccess: (data) => setResult(data),
  });

  return (
    <section className="bg-white border border-gray-200 rounded-lg overflow-hidden mt-6">
      <h2 className="text-lg font-semibold px-6 py-4 border-b">{t("settings.categorizationTitle")}</h2>
      <div className="px-6 py-4">
        <p className="text-sm text-gray-500 mb-4">{t("settings.categorizationDesc")}</p>
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium disabled:opacity-50"
          disabled={classify.isPending}
          onClick={() => classify.mutate()}
        >
          {classify.isPending ? t("settings.reclassifyRunning") : t("settings.reclassifyBtn")}
        </button>
        {result && (
          <p className="mt-3 text-sm text-green-700">
            {t("settings.reclassifyDone", { categorized: result.categorized, needs_review: result.needs_review })}
          </p>
        )}
        {classify.isError && (
          <p className="mt-3 text-sm text-red-500">{t("settings.reclassifyFailed")}</p>
        )}
      </div>
    </section>
  );
}
```

3. Add `<CategorizationSection />` at the bottom of the JSX returned by `SettingsPage`, after `<LlmCostSection />`:

```tsx
      <LlmCostSection />
      <CategorizationSection />
    </div>
  );
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Settings/index.tsx
git commit -m "feat: add re-classify unclassified button to Settings page"
```
