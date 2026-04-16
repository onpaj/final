# Unified Transaction Context Menu

**Date:** 2026-04-16  
**Status:** Approved

## Problem

The context menu on the Batch History transaction list only offers "Create rule". The Analytics/Review pages offer "Change category", "Unassign category", and "Create rule" via `TransactionTable`. The menu-building logic is duplicated inline in `TransactionTable.tsx` with nothing equivalent in `BatchHistory.tsx`.

## Goal

- Add "Change category" and "Unassign category" to the Batch History transaction context menu.
- Ensure the context menu is identical everywhere by extracting the menu-building logic into a shared pure utility.

## Design

### New file: `frontend/src/utils/transactionContextMenu.ts`

A single pure function:

```ts
buildTransactionContextMenuItems(options: {
  tx: Pick<Transaction, "id" | "category_id" | "counterparty_name" | "counterparty_account" | "description">;
  selectedIds: string[];         // ids to act on; pass [tx.id] when no bulk selection
  categoryGroups: CategoryGroup[];
  onCategorize: (ids: string[], categoryId: string | null) => void;
  onCreateRule: (prefill: RulePrefill) => void;
  t: TFunction;
}): ContextMenuItem[]
```

Returns an array of `ContextMenuItem` objects (same type used by `ContextMenu.tsx`):

1. **"Change category"** — submenu grouped by category group, with `__header__` entries; calls `onCategorize(selectedIds, cat.id)`.
2. **"Unassign category"** — only when `tx.category_id` is set; calls `onCategorize(selectedIds, null)`.
3. **"Create rule"** — calls `onCreateRule({ name, counterpartyAccount, counterpartyName, description })`.

This is the logic currently inlined in `TransactionTable.tsx`, extracted verbatim.

### `frontend/src/pages/Analytics/TransactionTable.tsx`

Replace the inline `contextMenuItems` array construction with a call to `buildTransactionContextMenuItems`. Pass `selected.size > 0 ? Array.from(selected) : [contextMenu.txId]` as `selectedIds`. No behavior change.

### `frontend/src/pages/Imports/BatchHistory.tsx` (`BatchTransactions`)

1. Replace `useQuery(listCategories)` with `useQuery(listCategoryGroups)` — used for both display (category name lookup via `.flatMap`) and menu building.
2. Add `useMutation({ mutationFn: (ids, catId) => bulkCategorize(ids, catId) })` with `queryClient.invalidateQueries(["batch-transactions", batchId])` on success.
3. Build the context menu via `buildTransactionContextMenuItems`, passing `[contextMenu.tx.id]` as `selectedIds` (no bulk selection).

## Out of scope

- Bulk selection / multi-row categorization in Batch History.
- Any other context menu items (e.g. "mark as transfer").
