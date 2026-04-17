# Transaction History Filters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Review page with an "All Transactions" mode showing the full transaction history with account, date range, and categorization source filters and infinite scroll.

**Architecture:** Add a mode toggle to the existing `ReviewPage`. "Needs Review" mode is unchanged. "All Transactions" mode uses `useInfiniteQuery` (TanStack Query v5) with an `IntersectionObserver` sentinel for infinite scroll, and a filter bar that passes `account_id`, `date_from`, `date_to`, and `categorization_source` to the existing API. A small backend change handles `categorization_source=none` as IS NULL.

**Tech Stack:** FastAPI (Python), React 19, TypeScript, TanStack Query v5, i18next, Tailwind CSS

---

### Task 1: Backend — support `categorization_source=none` as IS NULL filter

**Files:**
- Modify: `backend/app/api/transactions.py:165-167`
- Modify: `backend/tests/test_transactions_api.py`

- [ ] **Step 1: Write the failing test**

Add at the end of `backend/tests/test_transactions_api.py`:

```python
async def test_list_transactions_categorization_source_none_filters_null(client, mock_db):
    """categorization_source=none returns transactions WHERE categorization_source IS NULL."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    async with client as c:
        resp = await c.get("/api/transactions?categorization_source=none")
    assert resp.status_code == 200
    call_arg = mock_db.execute.call_args[0][0]
    query_str = str(call_arg).lower()
    # IS NULL, not equality
    assert "is null" in query_str or "isnull" in query_str or "is_(none)" in query_str.replace(" ", "")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_transactions_api.py::test_list_transactions_categorization_source_none_filters_null -v
```

Expected: FAIL — the test passes `categorization_source=none` but the backend currently does an equality filter (`WHERE categorization_source = 'none'`), not IS NULL.

- [ ] **Step 3: Implement the fix**

In `backend/app/api/transactions.py`, replace the existing `categorization_source` filter block (around line 165):

```python
    if categorization_source is not None:
        if categorization_source == "none":
            query = query.where(Transaction.categorization_source.is_(None))
        else:
            query = query.where(Transaction.categorization_source == categorization_source)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_transactions_api.py::test_list_transactions_categorization_source_none_filters_null -v
```

Expected: PASS

- [ ] **Step 5: Run full backend test suite**

```bash
cd backend && python -m pytest tests/test_transactions_api.py -v
```

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/transactions.py backend/tests/test_transactions_api.py
git commit -m "feat: handle categorization_source=none as IS NULL filter"
```

---

### Task 2: i18n — add translation keys for mode toggle and filter bar

**Files:**
- Modify: `frontend/public/locales/en/translation.json`
- Modify: `frontend/public/locales/cs/translation.json`

- [ ] **Step 1: Add English keys to `review` section**

In `frontend/public/locales/en/translation.json`, add these keys inside the `"review"` object (after `"runError": "Action failed"`):

```json
    "modeNeedsReview": "Needs Review",
    "modeAll": "All Transactions",
    "filterAllAccounts": "All accounts",
    "filterFrom": "From",
    "filterTo": "To",
    "filterSource": "Source",
    "filterAllSources": "All sources",
    "sourceNone": "None (uncategorized)",
    "sourceRule": "Rule",
    "sourceLlm": "LLM",
    "sourceTransfer": "Transfer",
    "sourceManual": "Manual",
    "loadingMore": "Loading more…",
    "emptyAll": "No transactions match the selected filters."
```

- [ ] **Step 2: Add Czech keys to `review` section**

In `frontend/public/locales/cs/translation.json`, add these keys inside the `"review"` object (after `"runError": "Akce selhala"`):

```json
    "modeNeedsReview": "Ke kontrole",
    "modeAll": "Všechny transakce",
    "filterAllAccounts": "Všechny účty",
    "filterFrom": "Od",
    "filterTo": "Do",
    "filterSource": "Zdroj",
    "filterAllSources": "Všechny zdroje",
    "sourceNone": "Bez zdroje (nekategorizované)",
    "sourceRule": "Pravidlo",
    "sourceLlm": "LLM",
    "sourceTransfer": "Přesun",
    "sourceManual": "Ručně",
    "loadingMore": "Načítám další…",
    "emptyAll": "Žádné transakce neodpovídají zvoleným filtrům."
```

- [ ] **Step 3: Commit**

```bash
git add frontend/public/locales/en/translation.json frontend/public/locales/cs/translation.json
git commit -m "feat: add i18n keys for transaction history mode toggle and filters"
```

---

### Task 3: Review page — mode toggle, filter bar, and infinite scroll

**Files:**
- Modify: `frontend/src/pages/Review/index.tsx`

This is a full rewrite of `ReviewPage`. The existing `useQuery` for needs_review is preserved unchanged. A new `useInfiniteQuery` is added for the "all" mode.

- [ ] **Step 1: Replace the full content of `frontend/src/pages/Review/index.tsx`**

```tsx
import { useState, useRef, useEffect } from "react";
import { useMutation, useQuery, useInfiniteQuery, useQueryClient } from "@tanstack/react-query";
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

type Mode = "needs_review" | "all";

const SOURCE_OPTIONS = ["none", "rule", "llm", "transfer", "manual"] as const;

export default function ReviewPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [mode, setMode] = useState<Mode>("needs_review");

  // All-transactions filters
  const [filterAccountId, setFilterAccountId] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");
  const [filterSource, setFilterSource] = useState("");

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [activeId, setActiveId] = useState<string | null>(null);
  const [overId, setOverId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [rulePrefill, setRulePrefill] = useState<RulePrefill | null>(null);
  const [steps, setSteps] = useState({ transfers: true, rules: true, llm: false });

  // Needs-review query (unchanged)
  const { data: reviewTransactions = [], isLoading: reviewLoading } = useQuery({
    queryKey: ["transactions", "needs_review", { include_llm_status: true }],
    queryFn: () => listTransactions({ needs_review: true, include_llm_status: true, limit: 500 }),
    enabled: mode === "needs_review",
  });

  // All-transactions infinite query
  const {
    data: allPages,
    isLoading: allLoading,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ["transactions", "all", { filterAccountId, filterDateFrom, filterDateTo, filterSource }],
    queryFn: ({ pageParam }) =>
      listTransactions({
        account_id: filterAccountId || undefined,
        date_from: filterDateFrom || undefined,
        date_to: filterDateTo || undefined,
        categorization_source: filterSource || undefined,
        limit: 50,
        offset: pageParam as number,
      }),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPagesArr) =>
      lastPage.length === 50 ? allPagesArr.length * 50 : undefined,
    enabled: mode === "all",
  });

  const allTransactions = allPages?.pages.flat() ?? [];
  const transactions = mode === "needs_review" ? reviewTransactions : allTransactions;
  const isLoading = mode === "needs_review" ? reviewLoading : allLoading;

  // IntersectionObserver sentinel for infinite scroll
  const sentinelRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel || !hasNextPage) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !isFetchingNextPage) fetchNextPage();
      },
      { threshold: 0.1 }
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasNextPage, fetchNextPage, isFetchingNextPage]);

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
    queryClient.invalidateQueries({ queryKey: ["transactions"] });
  }

  const assignMutation = useMutation({
    mutationFn: (category_id: string) => bulkCategorize(Array.from(selected), category_id),
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
      if (next.has(id)) next.delete(id);
      else next.add(id);
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
    if (!selected.has(draggedId)) setSelected(new Set([draggedId]));
  }

  function handleDragOver(event: DragOverEvent) {
    setOverId(event.over ? (event.over.id as string) : null);
  }

  function handleDragEnd(event: DragEndEvent) {
    const targetId = event.over ? (event.over.id as string) : null;
    if (targetId) assignMutation.mutate(targetId);
    setActiveId(null);
    setOverId(null);
  }

  function handleModeChange(next: Mode) {
    setMode(next);
    setSelected(new Set());
    setActionError(null);
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header + mode toggle */}
      <div className="flex items-center gap-4 mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{t("review.title")}</h1>
        {mode === "needs_review" && !isLoading && transactions.length > 0 && (
          <span className="inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-sm font-medium bg-red-100 text-red-700">
            {transactions.length}
          </span>
        )}
        <div className="ml-auto inline-flex rounded-md border border-gray-200 overflow-hidden text-sm">
          {(["needs_review", "all"] as const).map((m) => (
            <button
              key={m}
              onClick={() => handleModeChange(m)}
              className={[
                "px-3 py-1.5 font-medium",
                mode === m
                  ? "bg-blue-600 text-white"
                  : "bg-white text-gray-700 hover:bg-gray-50",
              ].join(" ")}
            >
              {m === "needs_review" ? t("review.modeNeedsReview") : t("review.modeAll")}
            </button>
          ))}
        </div>
      </div>

      {/* Needs-review toolbar */}
      {mode === "needs_review" && (
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
              <span className="text-sm text-gray-500">{t("review.selectedCount", { count: selected.size })}</span>
            )}
          </div>
          {actionError && <p className="mt-1 text-sm text-red-600">{actionError}</p>}
        </div>
      )}

      {/* All-transactions filter bar */}
      {mode === "all" && (
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500 font-medium uppercase tracking-wide">
              {t("rules.colAccount")}
            </label>
            <select
              value={filterAccountId}
              onChange={(e) => { setFilterAccountId(e.target.value); setSelected(new Set()); }}
              className="rounded-md border border-gray-300 text-sm px-2 py-1.5 bg-white"
            >
              <option value="">{t("review.filterAllAccounts")}</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500 font-medium uppercase tracking-wide">
              {t("review.filterFrom")}
            </label>
            <input
              type="date"
              value={filterDateFrom}
              onChange={(e) => { setFilterDateFrom(e.target.value); setSelected(new Set()); }}
              className="rounded-md border border-gray-300 text-sm px-2 py-1.5"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500 font-medium uppercase tracking-wide">
              {t("review.filterTo")}
            </label>
            <input
              type="date"
              value={filterDateTo}
              onChange={(e) => { setFilterDateTo(e.target.value); setSelected(new Set()); }}
              className="rounded-md border border-gray-300 text-sm px-2 py-1.5"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500 font-medium uppercase tracking-wide">
              {t("review.filterSource")}
            </label>
            <select
              value={filterSource}
              onChange={(e) => { setFilterSource(e.target.value); setSelected(new Set()); }}
              className="rounded-md border border-gray-300 text-sm px-2 py-1.5 bg-white"
            >
              <option value="">{t("review.filterAllSources")}</option>
              {SOURCE_OPTIONS.map((s) => (
                <option key={s} value={s}>{t(`review.source${s.charAt(0).toUpperCase() + s.slice(1)}`)}</option>
              ))}
            </select>
          </div>

          {selected.size > 0 && (
            <span className="text-sm text-gray-500 self-center">{t("review.selectedCount", { count: selected.size })}</span>
          )}
        </div>
      )}

      {isLoading ? (
        <p className="text-gray-400 text-sm">{t("common.loading")}</p>
      ) : transactions.length === 0 && mode === "needs_review" ? (
        <p className="text-gray-500 text-sm">{t("review.empty")}</p>
      ) : transactions.length === 0 && mode === "all" ? (
        <p className="text-gray-500 text-sm">{t("review.emptyAll")}</p>
      ) : (
        <DndContext onDragStart={handleDragStart} onDragOver={handleDragOver} onDragEnd={handleDragEnd}>
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1 min-w-0">
              <TransactionTable
                transactions={transactions}
                selected={selected}
                activeId={activeId}
                showReasonColumn={mode === "needs_review"}
                accountMap={accountMap}
                categoryGroups={categoryGroups}
                onToggleRow={toggleRow}
                onToggleAll={toggleAll}
                onCategorize={(ids, categoryId) => categorizeMutation.mutate({ ids, categoryId })}
                onCreateRule={setRulePrefill}
              />
              {/* Infinite scroll sentinel */}
              {mode === "all" && (
                <div ref={sentinelRef} className="py-4 text-center text-sm text-gray-400">
                  {isFetchingNextPage ? t("review.loadingMore") : null}
                </div>
              )}
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
        {rulePrefill && <RuleForm prefill={rulePrefill} onClose={() => setRulePrefill(null)} />}
      </SlideOverPanel>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Verify the dev server starts**

```bash
cd frontend && npm run dev -- --port 5173
```

Open `http://localhost:5173/review` and verify:
- Mode toggle appears top-right
- "Needs Review" mode looks and behaves identically to before
- Switching to "All Transactions" shows the filter bar and loads transactions

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Review/index.tsx
git commit -m "feat: add All Transactions mode with filters and infinite scroll to Review page"
```
