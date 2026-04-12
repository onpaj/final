# Transaction Context Menu — Change Category Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a right-click context menu to transaction rows that lets the user reassign one or many transactions to a different category via a grouped submenu.

**Architecture:** Extend the existing generic `ContextMenu` component with one-level submenu support (hover-triggered), then wire it into `TransactionTable` via new props, and plumb those props through `CategoryDetail` and `ReviewPage`. No backend changes needed — the existing `PATCH /api/transactions/bulk-categorize` endpoint handles the write.

**Tech Stack:** React 19, TypeScript, TanStack Query v5, i18next, ReactDOM portals (already used in ContextMenu), dnd-kit (already on rows — no conflict with `onContextMenu`).

---

## File Map

| File | Change |
|------|--------|
| `frontend/src/components/ContextMenu.tsx` | Add submenu support: `children` field on items, hover-triggered sub-panel |
| `frontend/src/pages/Analytics/TransactionTable.tsx` | Add `categoryGroups`+`onCategorize` props, context menu state, right-click handler |
| `frontend/src/pages/Analytics/CategoryDetail.tsx` | Pass `categoryGroups` + `onCategorize` to `TransactionTable` |
| `frontend/src/pages/Review/index.tsx` | Pass `categoryGroups` + `onCategorize` to `TransactionTable` |
| `frontend/public/locales/en/translation.json` | Add `analytics.changeCategory` key |
| `frontend/public/locales/cs/translation.json` | Add `analytics.changeCategory` key |

---

## Task 1: Extend ContextMenu with submenu support

**Files:**
- Modify: `frontend/src/components/ContextMenu.tsx`

- [ ] **Step 1: Replace the file with the extended implementation**

```tsx
import { useEffect, useRef, useState } from "react";
import ReactDOM from "react-dom";

interface ContextMenuItem {
  label: string;
  onClick?: () => void;
  children?: ContextMenuItem[];
}

interface Props {
  x: number;
  y: number;
  items: ContextMenuItem[];
  onClose: () => void;
}

export default function ContextMenu({ x, y, items, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const submenuRef = useRef<HTMLDivElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [submenu, setSubmenu] = useState<{ label: string; top: number; left: number } | null>(null);

  const menuWidth = 220;
  const submenuWidth = 220;
  const menuHeight = items.length * 36;
  const left = Math.min(x, window.innerWidth - menuWidth - 8);
  const top = Math.min(y, window.innerHeight - menuHeight - 8);

  useEffect(() => {
    function handleMouseDown(e: MouseEvent) {
      const target = e.target as Node;
      const inMain = ref.current?.contains(target);
      const inSub = submenuRef.current?.contains(target);
      if (!inMain && !inSub) onClose();
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("mousedown", handleMouseDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleMouseDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  function openSubmenu(label: string, itemEl: HTMLElement) {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    const rect = itemEl.getBoundingClientRect();
    const subLeft =
      rect.right + submenuWidth <= window.innerWidth - 8
        ? rect.right
        : rect.left - submenuWidth;
    setSubmenu({ label, top: rect.top, left: subLeft });
  }

  function scheduleClose() {
    closeTimer.current = setTimeout(() => setSubmenu(null), 100);
  }

  function cancelClose() {
    if (closeTimer.current) clearTimeout(closeTimer.current);
  }

  const activeItem = submenu ? items.find((i) => i.label === submenu.label) : null;

  return (
    <>
      {ReactDOM.createPortal(
        <div
          ref={ref}
          style={{ position: "fixed", top, left, zIndex: 9999 }}
          className="bg-white border border-gray-200 rounded shadow-lg py-1 min-w-[180px]"
        >
          {items.map((item) =>
            item.children ? (
              <div
                key={item.label}
                onMouseEnter={(e) => openSubmenu(item.label, e.currentTarget)}
                onMouseLeave={scheduleClose}
                className="px-4 py-2 text-sm hover:bg-gray-100 flex items-center justify-between cursor-default select-none"
              >
                <span>{item.label}</span>
                <span className="text-gray-400 ml-2 text-xs">▶</span>
              </div>
            ) : (
              <button
                key={item.label}
                onClick={() => {
                  item.onClick?.();
                  onClose();
                }}
                className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100"
              >
                {item.label}
              </button>
            )
          )}
        </div>,
        document.body
      )}
      {submenu && activeItem?.children &&
        ReactDOM.createPortal(
          <div
            ref={submenuRef}
            style={{ position: "fixed", top: submenu.top, left: submenu.left, zIndex: 10000 }}
            className="bg-white border border-gray-200 rounded shadow-lg py-1 min-w-[180px] max-h-96 overflow-y-auto"
            onMouseEnter={cancelClose}
            onMouseLeave={scheduleClose}
          >
            {activeItem.children.map((child) =>
              child.label.startsWith("__header__") ? (
                <div
                  key={child.label}
                  className="px-4 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wide"
                >
                  {child.label.slice("__header__".length)}
                </div>
              ) : (
                <button
                  key={child.label}
                  onClick={() => {
                    child.onClick?.();
                    onClose();
                  }}
                  className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100"
                >
                  {child.label}
                </button>
              )
            )}
          </div>,
          document.body
        )}
    </>
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
git add frontend/src/components/ContextMenu.tsx
git commit -m "feat: extend ContextMenu with hover submenu support"
```

---

## Task 2: Add translation key

**Files:**
- Modify: `frontend/public/locales/en/translation.json`
- Modify: `frontend/public/locales/cs/translation.json`

- [ ] **Step 1: Add key to English translation**

In `frontend/public/locales/en/translation.json`, inside the `"analytics"` object, add after `"unclassified": "Unclassified"`:

```json
"changeCategory": "Change category"
```

The end of the `analytics` block should look like:

```json
    "clearFailed": "Failed to clear. Please try again.",
    "unclassified": "Unclassified",
    "changeCategory": "Change category"
  },
```

- [ ] **Step 2: Add key to Czech translation**

In `frontend/public/locales/cs/translation.json`, inside the `"analytics"` object, find the `"unclassified"` key and add after it:

```json
"changeCategory": "Změnit kategorii"
```

- [ ] **Step 3: Commit**

```bash
git add frontend/public/locales/en/translation.json frontend/public/locales/cs/translation.json
git commit -m "i18n: add analytics.changeCategory translation key"
```

---

## Task 3: Wire context menu into TransactionTable

**Files:**
- Modify: `frontend/src/pages/Analytics/TransactionTable.tsx`

- [ ] **Step 1: Replace the file with the wired implementation**

```tsx
import { useState } from "react";
import { useDraggable } from "@dnd-kit/core";
import { useTranslation } from "react-i18next";
import type { Transaction } from "../../api/transactions";
import type { CategoryGroup } from "../../api/categories";
import ContextMenu from "../../components/ContextMenu";

function ReasonBadge({ tx }: { tx: Transaction }) {
  const { t } = useTranslation();
  if (!tx.llm_status) return null;

  if (tx.llm_status === "no_rule_no_llm") {
    return (
      <span className="inline-block px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-500">
        {t("review.reasonNoRule")}
      </span>
    );
  }
  if (tx.llm_status === "llm_error") {
    return (
      <span className="inline-block px-2 py-0.5 rounded text-xs bg-red-100 text-red-600">
        {t("review.reasonLlmError")}
      </span>
    );
  }
  const conf = tx.llm_confidence != null ? ` (${Number(tx.llm_confidence).toFixed(2)})` : "";
  return (
    <span className="inline-block px-2 py-0.5 rounded text-xs bg-yellow-100 text-yellow-700">
      {t("review.reasonLlmRejected")}{conf}
    </span>
  );
}

interface DraggableRowProps {
  transaction: Transaction;
  isChecked: boolean;
  isDragActive: boolean;
  showReasonColumn: boolean;
  accountMap?: Record<string, string>;
  onToggle: () => void;
  onContextMenu: (e: React.MouseEvent, txId: string) => void;
}

function DraggableRow({ transaction: tx, isChecked, isDragActive, showReasonColumn, accountMap, onToggle, onContextMenu }: DraggableRowProps) {
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
      onContextMenu={(e) => {
        e.preventDefault();
        onContextMenu(e, tx.id);
      }}
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
      {accountMap && (
        <td className="px-4 py-2.5 text-gray-500 text-xs">{accountMap[tx.account_id] ?? "—"}</td>
      )}
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
  accountMap?: Record<string, string>;
  categoryGroups?: CategoryGroup[];
  onToggleRow: (id: string) => void;
  onToggleAll: () => void;
  onCategorize?: (transactionIds: string[], categoryId: string) => void;
}

export default function TransactionTable({
  transactions,
  selected,
  activeId,
  showReasonColumn = false,
  accountMap,
  categoryGroups,
  onToggleRow,
  onToggleAll,
  onCategorize,
}: Props) {
  const { t } = useTranslation();
  const allSelected = transactions.length > 0 && selected.size === transactions.length;
  const someSelected = selected.size > 0 && !allSelected;
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; txId: string } | null>(null);

  function handleContextMenu(e: React.MouseEvent, txId: string) {
    setContextMenu({ x: e.clientX, y: e.clientY, txId });
  }

  const categoryMenuItems = categoryGroups
    ? categoryGroups.flatMap((group) => [
        { label: `__header__${group.name}` },
        ...(group.categories ?? []).map((cat) => ({
          label: cat.name,
          onClick: () => {
            if (!contextMenu) return;
            const ids = selected.size > 0 ? Array.from(selected) : [contextMenu.txId];
            onCategorize?.(ids, cat.id);
            setContextMenu(null);
          },
        })),
      ])
    : [];

  return (
    <>
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
              {accountMap && (
                <th className="px-4 py-2 text-left">{t("analytics.txAccount")}</th>
              )}
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
                accountMap={accountMap}
                onToggle={() => onToggleRow(tx.id)}
                onContextMenu={handleContextMenu}
              />
            ))}
          </tbody>
        </table>
        {transactions.length === 0 && (
          <p className="px-4 py-8 text-center text-gray-400 text-sm">{t("analytics.noTransactions")}</p>
        )}
      </div>
      {contextMenu && categoryGroups && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          items={[{ label: t("analytics.changeCategory"), children: categoryMenuItems }]}
          onClose={() => setContextMenu(null)}
        />
      )}
    </>
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
git add frontend/src/pages/Analytics/TransactionTable.tsx
git commit -m "feat: add right-click context menu to transaction rows"
```

---

## Task 4: Wire CategoryDetail

**Files:**
- Modify: `frontend/src/pages/Analytics/CategoryDetail.tsx`

- [ ] **Step 1: Add `categorizeMutation` and pass new props to `TransactionTable`**

Add a new mutation after the existing `clearMutation` block (around line 68):

```tsx
const categorizeMutation = useMutation({
  mutationFn: ({ ids, categoryId }: { ids: string[]; categoryId: string }) =>
    bulkCategorize(ids, categoryId),
  onSuccess: invalidateAndClear,
});
```

- [ ] **Step 2: Pass `categoryGroups` and `onCategorize` to `TransactionTable`**

Find the `<TransactionTable` usage in `CategoryDetail.tsx` (around line 167) and add two props:

```tsx
<TransactionTable
  transactions={transactions}
  selected={selected}
  activeId={activeId}
  accountMap={accountMap}
  categoryGroups={categoryGroups}
  onToggleRow={toggleRow}
  onToggleAll={toggleAll}
  onCategorize={(ids, categoryId) => categorizeMutation.mutate({ ids, categoryId })}
/>
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Analytics/CategoryDetail.tsx
git commit -m "feat: wire context menu categorize in CategoryDetail"
```

---

## Task 5: Wire ReviewPage

**Files:**
- Modify: `frontend/src/pages/Review/index.tsx`

- [ ] **Step 1: Add `categorizeMutation` after the existing `assignMutation` block (around line 53)**

```tsx
const categorizeMutation = useMutation({
  mutationFn: ({ ids, categoryId }: { ids: string[]; categoryId: string }) =>
    bulkCategorize(ids, categoryId),
  onSuccess: invalidateAndClear,
});
```

- [ ] **Step 2: Pass `categoryGroups` and `onCategorize` to `TransactionTable`**

Find the `<TransactionTable` usage in `Review/index.tsx` (around line 161) and add two props:

```tsx
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
/>
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Review/index.tsx
git commit -m "feat: wire context menu categorize in ReviewPage"
```

---

## Manual Smoke Test

After all tasks complete, run the dev server and verify:

```bash
cd frontend && npm run dev
```

Check the following in the browser:

1. **Right-click a transaction row** in Analytics (Category Detail view) → menu appears with "Change category" and a `▶`.
2. **Hover "Change category"** → submenu appears with groups as grey uppercase headers and categories below each.
3. **Click a category** → transaction is reassigned, table refreshes, menu closes.
4. **Check multiple rows**, then right-click one → submenu shows → click a category → all checked transactions are reassigned.
5. **Right-click outside a selection** (no rows checked) → only the right-clicked row is reassigned.
6. **Press Escape** while menu is open → menu closes.
7. **Click elsewhere** while menu is open → menu closes.
8. **Repeat steps 1–7 on the Review page** — same behavior expected.
9. **Near right viewport edge**: right-click a row on the far right → submenu should flip to the left to stay in view.
