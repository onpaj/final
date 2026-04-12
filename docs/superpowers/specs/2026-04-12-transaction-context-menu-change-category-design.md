# Transaction Context Menu — Change Category

**Date:** 2026-04-12
**Status:** Approved

## Overview

Add a right-click context menu to transaction rows in `TransactionTable`. The menu has a single item — "Change Category" — which opens a submenu showing all categories grouped by their group. Selecting a category applies it to all checked transactions (or just the right-clicked one if none are checked).

The context menu appears on both the Analytics/CategoryDetail view and the Review page, since both use `TransactionTable`.

## Components

### `ContextMenu` — extended

**File:** `frontend/src/components/ContextMenu.tsx`

Extend `ContextMenuItem` to support optional children:

```ts
interface ContextMenuItem {
  label: string;
  onClick?: () => void;
  children?: ContextMenuItem[];  // presence triggers submenu panel
}
```

- Items with `children` render a `▶` indicator on the right; their `onClick` is ignored.
- On **hover** (`onMouseEnter`) of such an item, a submenu panel is rendered via portal at `fixed` position derived from the item's `getBoundingClientRect`. Positioned to the right of the parent panel; clamped to the left if near the right viewport edge.
- The submenu panel uses the same styling as the parent (white bg, `border-gray-200`, shadow, `rounded`).
- Only one level of nesting is implemented. The type is recursive for future use.
- Items whose label starts with `__header__` are rendered as non-clickable group headers (muted text, no hover highlight, no `onClick`). This is how group names are injected into the flat category list.

### `TransactionTable` — wired for context menu

**File:** `frontend/src/pages/Analytics/TransactionTable.tsx`

Two new optional props:

```ts
categoryGroups?: CategoryGroup[]
onCategorize?: (transactionIds: string[], categoryId: string) => void
```

- `DraggableRow` receives an `onContextMenu?: (e: React.MouseEvent, txId: string) => void` prop.
- `DraggableRow.onContextMenu` calls `e.preventDefault()` then invokes the prop callback.
- `TransactionTable` holds local state `contextMenu: { x: number; y: number; txId: string } | null`.
- On right-click: set state. On menu close: clear state.
- When a category is selected from the submenu:
  - If `selected` (checked rows) is non-empty → use all selected IDs.
  - Otherwise → use just `contextMenu.txId`.
  - Call `onCategorize(ids, categoryId)`, then close menu.
- The "Change Category" submenu is built from `categoryGroups`: for each group, push a `__header__<GroupName>` item (non-clickable), then each category in the group as a leaf item `{ label: category.name, onClick: () => handleCategorize(category.id) }`.

## Parent page changes

Both `CategoryDetail` (`frontend/src/pages/Analytics/CategoryDetail.tsx`) and the Review page (`frontend/src/pages/Review/index.tsx`) need to:

1. Fetch `categoryGroups` via `listCategoryGroups()` (React Query, reuse existing query if already present).
2. Pass `categoryGroups` and `onCategorize` to `TransactionTable`.
3. `onCategorize` implementation: call `PATCH /api/transactions/bulk-categorize` with `{ transaction_ids, category_id }`, then invalidate relevant React Query cache keys.

## Data flow

```
right-click on row
  → TransactionTable sets contextMenu state
  → ContextMenu rendered at (x, y)
  → hover "Change Category" → submenu panel appears
  → click category leaf
  → TransactionTable.onCategorize(ids, categoryId)
  → parent calls bulk-categorize API
  → React Query cache invalidated
  → ContextMenu closed
```

## Out of scope

- Additional context menu items (deferred).
- Keyboard navigation within the context menu.
- Multi-level submenus beyond one level.
