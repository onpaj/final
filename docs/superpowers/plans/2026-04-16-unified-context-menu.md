# Unified Transaction Context Menu Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract shared context menu item builder used by both `TransactionTable` and `BatchHistory`, and add "Change category" / "Unassign category" to the Batch History transaction context menu.

**Architecture:** A pure utility function `buildTransactionContextMenuItems` lives in `frontend/src/utils/transactionContextMenu.ts`. `TransactionTable` is refactored to call it. `BatchHistory.BatchTransactions` gains a `listCategoryGroups` query and a `bulkCategorize` mutation, then calls the same function to build its context menu.

**Tech Stack:** React 19, TypeScript, TanStack Query v5, i18next, existing `ContextMenu` component

---

## File Map

| Action | File | What changes |
|--------|------|--------------|
| **Create** | `frontend/src/utils/transactionContextMenu.ts` | New pure function that builds `ContextMenuItem[]` |
| **Modify** | `frontend/src/pages/Analytics/TransactionTable.tsx` | Replace inline menu-building with shared function call |
| **Modify** | `frontend/src/pages/Imports/BatchHistory.tsx` | Add `listCategoryGroups` query, `bulkCategorize` mutation, use shared function |

---

## Task 1: Create shared `buildTransactionContextMenuItems` utility

**Files:**
- Create: `frontend/src/utils/transactionContextMenu.ts`

- [ ] **Step 1: Create the utility file**

Create `frontend/src/utils/transactionContextMenu.ts` with the following content. This is the menu logic extracted verbatim from `TransactionTable.tsx` lines 126–170, generalised to accept any object with the needed fields.

```typescript
import type { TFunction } from "i18next";
import type { CategoryGroup } from "../api/categories";
import type { RulePrefill } from "../pages/Rules/RuleForm";

interface TransactionLike {
  id: string;
  category_id: string | null;
  counterparty_name: string | null;
  counterparty_account: string | null;
  description: string | null;
}

interface ContextMenuItem {
  label: string;
  onClick?: () => void;
  children?: ContextMenuItem[];
}

interface BuildMenuOptions {
  tx: TransactionLike;
  selectedIds: string[];
  categoryGroups: CategoryGroup[];
  onCategorize: (ids: string[], categoryId: string | null) => void;
  onCreateRule: (prefill: RulePrefill) => void;
  t: TFunction;
}

export function buildTransactionContextMenuItems({
  tx,
  selectedIds,
  categoryGroups,
  onCategorize,
  onCreateRule,
  t,
}: BuildMenuOptions): ContextMenuItem[] {
  const categoryMenuItems: ContextMenuItem[] = categoryGroups.flatMap((group) => [
    { label: `__header__${group.name}` },
    ...(group.categories ?? []).map((cat) => ({
      label: cat.name,
      onClick: () => onCategorize(selectedIds, cat.id),
    })),
  ]);

  return [
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
}
```

- [ ] **Step 2: Verify TypeScript compiles cleanly**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors from the new file.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/utils/transactionContextMenu.ts
git commit -m "feat: extract buildTransactionContextMenuItems utility"
```

---

## Task 2: Refactor `TransactionTable` to use the shared function

**Files:**
- Modify: `frontend/src/pages/Analytics/TransactionTable.tsx`

- [ ] **Step 1: Add the import**

At the top of `frontend/src/pages/Analytics/TransactionTable.tsx`, after the existing imports, add:

```typescript
import { buildTransactionContextMenuItems } from "../../utils/transactionContextMenu";
```

- [ ] **Step 2: Replace the inline `contextMenuItems` construction**

Find the block starting at line 143 (`const contextMenuItems = [`). Replace everything from that line through the closing `];` with:

```typescript
  const contextTx = contextMenu ? transactions.find((tx) => tx.id === contextMenu.txId) : null;

  const contextMenuItems = contextTx && categoryGroups && onCategorize && onCreateRule
    ? buildTransactionContextMenuItems({
        tx: contextTx,
        selectedIds: selected.size > 0 ? Array.from(selected) : [contextMenu!.txId],
        categoryGroups,
        onCategorize,
        onCreateRule,
        t,
      })
    : [];
```

Note: remove the now-redundant `const contextTx = ...` line that was already in the file just above the old `contextMenuItems` block (line 141). The new block above includes it.

- [ ] **Step 3: Verify no TypeScript errors and behaviour is unchanged**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors.

Open the Analytics page in the browser (`http://localhost:5173`), drill into any category, right-click a transaction. Confirm the context menu still shows "Change category" submenu, "Unassign category" (if categorized), and "Create rule".

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Analytics/TransactionTable.tsx
git commit -m "refactor: use shared buildTransactionContextMenuItems in TransactionTable"
```

---

## Task 3: Add category change to `BatchHistory` context menu

**Files:**
- Modify: `frontend/src/pages/Imports/BatchHistory.tsx`

- [ ] **Step 1: Update imports in `BatchHistory.tsx`**

Replace the existing import line:
```typescript
import { listCategories, type Category } from "../../api/categories";
```
with:
```typescript
import { listCategoryGroups } from "../../api/categories";
import type { CategoryGroup } from "../../api/categories";
```

Also add the following imports (after existing ones at the top):
```typescript
import { bulkCategorize } from "../../api/transactions";
import { buildTransactionContextMenuItems } from "../../utils/transactionContextMenu";
```

- [ ] **Step 2: Update `BatchTransactions` — replace `listCategories` query with `listCategoryGroups`**

Inside the `BatchTransactions` function component, find:
```typescript
  const { data: categories = [] } = useQuery<Category[]>({ queryKey: ["categories"], queryFn: listCategories });
  const categoryName = (id: string | null) => categories.find((c) => c.id === id)?.name ?? null;
```

Replace with:
```typescript
  const queryClient = useQueryClient();
  const { data: categoryGroups = [] } = useQuery<CategoryGroup[]>({
    queryKey: ["categoryGroups"],
    queryFn: listCategoryGroups,
  });
  const allCategories = categoryGroups.flatMap((g) => g.categories ?? []);
  const categoryName = (id: string | null) => allCategories.find((c) => c.id === id)?.name ?? null;

  const categorizeMutation = useMutation({
    mutationFn: ({ ids, categoryId }: { ids: string[]; categoryId: string | null }) =>
      bulkCategorize(ids, categoryId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["batch-transactions", batchId] }),
  });
```

Note: `useQueryClient` is already imported via `@tanstack/react-query` at the top of the file. Make sure `useMutation` is also imported — add it to the existing import if not present:
```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
```

- [ ] **Step 3: Update the context menu items in `BatchTransactions`**

Find the `{contextMenu && (` block (around line 126) and replace the entire `<ContextMenu ... />` with:

```typescript
      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          items={buildTransactionContextMenuItems({
            tx: contextMenu.tx,
            selectedIds: [contextMenu.tx.id],
            categoryGroups,
            onCategorize: (ids, categoryId) => categorizeMutation.mutate({ ids, categoryId }),
            onCreateRule: onCreateRule,
            t,
          })}
          onClose={() => setContextMenu(null)}
        />
      )}
```

- [ ] **Step 4: Verify no TypeScript errors**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors.

- [ ] **Step 5: Manual verification**

1. Start the dev server (`npm run dev` in `frontend/`).
2. Go to the Imports page.
3. Expand any completed batch.
4. Right-click a transaction row.
5. Confirm the context menu now shows:
   - "Change category" with a submenu of all categories grouped by group
   - "Unassign category" (only if the transaction already has a category)
   - "Create rule"
6. Select a category from the submenu and confirm the row's category badge updates on re-expand.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Imports/BatchHistory.tsx
git commit -m "feat: add change category to BatchHistory transaction context menu"
```
