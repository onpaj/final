# Create Rule from Transaction — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a right-click context menu on transaction rows that opens a pre-filled RuleForm so the user can create a categorization rule directly from a transaction.

**Architecture:** A new portal-based `ContextMenu` component is wired into `TransactionTable` via a prop. `CategoryDetail` owns context-menu state and opens the existing `SlideOverPanel` + `RuleForm`. `RuleForm` gains an optional `prefill` prop that initializes fields from the transaction without changing the existing create/edit flows.

**Tech Stack:** React, TypeScript, TanStack Query, Tailwind CSS, react-i18next, ReactDOM.createPortal

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/components/ContextMenu.tsx` | **Create** | Portal-based floating menu, closes on outside click / Escape |
| `frontend/src/pages/Analytics/TransactionTable.tsx` | **Modify** | Accept `onContextMenu` prop, call it from `DraggableRow` |
| `frontend/src/pages/Analytics/CategoryDetail.tsx` | **Modify** | Context menu state + rule panel state + wiring |
| `frontend/src/pages/Rules/RuleForm.tsx` | **Modify** | Add optional `prefill` prop; reactive match-value pre-fill |
| `frontend/public/locales/en/translation.json` | **Modify** | Add 2 new i18n keys under `rules` |
| `frontend/public/locales/cs/translation.json` | **Modify** | Same 2 keys in Czech |

---

## Task 1: Add i18n keys

**Files:**
- Modify: `frontend/public/locales/en/translation.json`
- Modify: `frontend/public/locales/cs/translation.json`

- [ ] **Step 1: Add English keys**

In `frontend/public/locales/en/translation.json`, inside the `"rules"` object, add after `"fieldEnabled": "Enabled"`:

```json
"createFromTransaction": "Create rule from transaction",
"matchTypePlaceholder": "— select type —"
```

The `"rules"` section should end like:
```json
    "fieldPriority": "Priority",
    "fieldEnabled": "Enabled",
    "createFromTransaction": "Create rule from transaction",
    "matchTypePlaceholder": "— select type —"
  },
```

- [ ] **Step 2: Add Czech keys**

In `frontend/public/locales/cs/translation.json`, find the `"rules"` object and add the same two keys translated:

```json
"createFromTransaction": "Vytvořit pravidlo z transakce",
"matchTypePlaceholder": "— vyberte typ —"
```

- [ ] **Step 3: Commit**

```bash
git add frontend/public/locales/en/translation.json frontend/public/locales/cs/translation.json
git commit -m "feat: add i18n keys for create-rule-from-transaction"
```

---

## Task 2: Create the `ContextMenu` component

**Files:**
- Create: `frontend/src/components/ContextMenu.tsx`

- [ ] **Step 1: Create the file**

```tsx
import { useEffect, useRef } from "react";
import ReactDOM from "react-dom";

interface ContextMenuItem {
  label: string;
  onClick: () => void;
}

interface Props {
  x: number;
  y: number;
  items: ContextMenuItem[];
  onClose: () => void;
}

export default function ContextMenu({ x, y, items, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  // Clamp position so menu never overflows viewport
  const menuWidth = 220;
  const menuHeight = items.length * 36;
  const left = Math.min(x, window.innerWidth - menuWidth - 8);
  const top = Math.min(y, window.innerHeight - menuHeight - 8);

  useEffect(() => {
    function handleMouseDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
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

  return ReactDOM.createPortal(
    <div
      ref={ref}
      style={{ position: "fixed", top, left, zIndex: 9999 }}
      className="bg-white border border-gray-200 rounded shadow-lg py-1 min-w-[180px]"
    >
      {items.map((item) => (
        <button
          key={item.label}
          onClick={() => {
            item.onClick();
            onClose();
          }}
          className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100"
        >
          {item.label}
        </button>
      ))}
    </div>,
    document.body
  );
}
```

- [ ] **Step 2: Verify the file compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors related to `ContextMenu.tsx`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ContextMenu.tsx
git commit -m "feat: add portal-based ContextMenu component"
```

---

## Task 3: Add `onContextMenu` prop to `TransactionTable`

**Files:**
- Modify: `frontend/src/pages/Analytics/TransactionTable.tsx`

- [ ] **Step 1: Update `DraggableRowProps` and `Props` interfaces**

In `TransactionTable.tsx`, update `DraggableRowProps`:

```tsx
interface DraggableRowProps {
  transaction: Transaction;
  isChecked: boolean;
  isDragActive: boolean;
  onToggle: () => void;
  onContextMenu: (e: React.MouseEvent, tx: Transaction) => void;
}
```

Update the outer `Props` interface:

```tsx
interface Props {
  transactions: Transaction[];
  selected: Set<string>;
  activeId: string | null;
  onToggleRow: (id: string) => void;
  onToggleAll: () => void;
  onContextMenu: (e: React.MouseEvent, tx: Transaction) => void;
}
```

- [ ] **Step 2: Wire `onContextMenu` through `DraggableRow`**

Add `onContextMenu` to the `DraggableRow` function signature and attach it to the `<tr>`:

```tsx
function DraggableRow({ transaction: tx, isChecked, isDragActive, onToggle, onContextMenu }: DraggableRowProps) {
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
      onContextMenu={(e) => onContextMenu(e, tx)}
      {...attributes}
      {...listeners}
    >
```

- [ ] **Step 3: Pass `onContextMenu` from `TransactionTable` to `DraggableRow`**

In the `TransactionTable` function body, update the `DraggableRow` usage:

```tsx
export default function TransactionTable({ transactions, selected, activeId, onToggleRow, onToggleAll, onContextMenu }: Props) {
  // ...existing code...
  return (
    // ...existing JSX...
    {transactions.map((tx) => (
      <DraggableRow
        key={tx.id}
        transaction={tx}
        isChecked={selected.has(tx.id)}
        isDragActive={activeId !== null}
        onToggle={() => onToggleRow(tx.id)}
        onContextMenu={onContextMenu}
      />
    ))}
```

- [ ] **Step 4: Verify no TS errors**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: errors only in `CategoryDetail.tsx` (missing the new prop — fixed in Task 4).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Analytics/TransactionTable.tsx
git commit -m "feat: add onContextMenu prop to TransactionTable"
```

---

## Task 4: Add `prefill` prop to `RuleForm`

**Files:**
- Modify: `frontend/src/pages/Rules/RuleForm.tsx`

- [ ] **Step 1: Add `RulePrefill` type and update `Props`**

At the top of `RuleForm.tsx`, after the imports, add:

```tsx
export interface RulePrefill {
  name: string;
  counterpartyAccount: string | null;
  counterpartyName: string | null;
  description: string | null;
}
```

Update the `Props` interface:

```tsx
interface Props {
  rule?: Rule;
  prefill?: RulePrefill;
  onClose: () => void;
}
```

- [ ] **Step 2: Update initial state to use `prefill`**

Update `getInitialMatchValue` — it is no longer needed when `prefill` is used; match value is reactive. Leave the existing function untouched (still used for edit mode).

Update the `RuleForm` function signature and initial state:

```tsx
export default function RuleForm({ rule, prefill, onClose }: Props) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [name, setName] = useState(rule?.name ?? prefill?.name ?? "");
  const [matchType, setMatchType] = useState<MatchType | "">(
    prefill ? "" : ((rule?.match_type as MatchType) ?? "counterparty_account_equals")
  );
  const [matchValue, setMatchValue] = useState(() => getInitialMatchValue(rule));
  const [categoryId, setCategoryId] = useState(rule?.category_id ?? "");
  const [priority, setPriority] = useState(rule?.priority ?? 100);
  const [enabled, setEnabled] = useState(rule?.enabled ?? true);
```

Note: `matchType` is now `MatchType | ""` to allow the empty placeholder when `prefill` is present.

- [ ] **Step 3: Make match value reactive to match type when prefill is set**

Replace the existing `matchType` select `onChange` handler to also reactively pre-fill `matchValue` from prefill:

```tsx
onChange={(e) => {
  const newType = e.target.value as MatchType | "";
  setMatchType(newType);
  if (prefill && newType !== "") {
    if (newType === "counterparty_account_equals") {
      setMatchValue(prefill.counterpartyAccount ?? "");
    } else if (newType === "counterparty_contains") {
      setMatchValue(prefill.counterpartyName ?? "");
    } else if (newType === "description_contains") {
      setMatchValue(prefill.description ?? "");
    }
  } else if (!prefill) {
    setMatchValue("");
  }
}}
```

- [ ] **Step 4: Add the placeholder option to the match type `<select>`**

```tsx
<select
  value={matchType}
  onChange={...} // from step 3
  className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
>
  {prefill && (
    <option value="" disabled>
      {t("rules.matchTypePlaceholder")}
    </option>
  )}
  <option value="counterparty_account_equals">{t("rules.matchType.counterparty_account_equals")}</option>
  <option value="counterparty_contains">{t("rules.matchType.counterparty_contains")}</option>
  <option value="description_contains">{t("rules.matchType.description_contains")}</option>
</select>
```

- [ ] **Step 5: Fix the `save` mutationFn to handle `matchType | ""`**

The `buildMatchValue` call uses `matchType`. Since `matchType` can now be `""`, guard the save:

```tsx
const save = useMutation({
  mutationFn: () => {
    if (matchType === "") return Promise.reject(new Error("Select a match type"));
    const body = {
      name,
      match_type: matchType,
      match_value: buildMatchValue(matchType, matchValue),
      category_id: categoryId,
      priority,
      enabled,
    };
    return rule ? updateRule(rule.id, body) : createRule(body);
  },
  onSuccess: () => {
    qc.invalidateQueries({ queryKey: ["rules"] });
    onClose();
  },
});
```

Also add `required` to the match type `<select>` so the browser prevents form submit with empty value:

```tsx
<select required value={matchType} onChange={...}>
```

- [ ] **Step 6: Verify no TS errors**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: clean (or only errors in `CategoryDetail.tsx` if not yet updated).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Rules/RuleForm.tsx
git commit -m "feat: add prefill prop to RuleForm for pre-populating from transaction"
```

---

## Task 5: Wire context menu and rule panel into `CategoryDetail`

**Files:**
- Modify: `frontend/src/pages/Analytics/CategoryDetail.tsx`

- [ ] **Step 1: Add imports**

At the top of `CategoryDetail.tsx`, add:

```tsx
import ContextMenu from "../../components/ContextMenu";
import SlideOverPanel from "../../components/SlideOverPanel";
import RuleForm, { type RulePrefill } from "../Rules/RuleForm";
import type { Transaction } from "../../api/transactions";
```

(Note: `Transaction` type may already be imported — check and avoid duplicate.)

- [ ] **Step 2: Add context menu and rule panel state**

Inside `CategoryDetail`, alongside the existing `selected`/`activeId` state:

```tsx
const [contextMenu, setContextMenu] = useState<{
  x: number;
  y: number;
  transaction: Transaction;
} | null>(null);

const [rulePanel, setRulePanel] = useState<{ prefill: RulePrefill } | null>(null);
```

- [ ] **Step 3: Add the `handleContextMenu` callback**

```tsx
function handleContextMenu(e: React.MouseEvent, tx: Transaction) {
  e.preventDefault();
  setContextMenu({ x: e.clientX, y: e.clientY, transaction: tx });
}
```

- [ ] **Step 4: Pass `onContextMenu` to `TransactionTable`**

Find the `<TransactionTable ... />` JSX and add the new prop:

```tsx
<TransactionTable
  transactions={transactions}
  selected={selected}
  activeId={activeId}
  onToggleRow={toggleRow}
  onToggleAll={toggleAll}
  onContextMenu={handleContextMenu}
/>
```

- [ ] **Step 5: Render `ContextMenu` and `SlideOverPanel` with `RuleForm`**

At the bottom of the `CategoryDetail` return statement, before the closing tag, add:

```tsx
{contextMenu && (
  <ContextMenu
    x={contextMenu.x}
    y={contextMenu.y}
    onClose={() => setContextMenu(null)}
    items={[
      {
        label: t("rules.createFromTransaction"),
        onClick: () => {
          const tx = contextMenu.transaction;
          setRulePanel({
            prefill: {
              name: tx.counterparty_name ?? tx.description ?? "",
              counterpartyAccount: tx.counterparty_account,
              counterpartyName: tx.counterparty_name,
              description: tx.description,
            },
          });
        },
      },
    ]}
  />
)}

<SlideOverPanel
  open={rulePanel !== null}
  onClose={() => setRulePanel(null)}
  title={t("rules.newRule")}
>
  {rulePanel !== null && (
    <RuleForm prefill={rulePanel.prefill} onClose={() => setRulePanel(null)} />
  )}
</SlideOverPanel>
```

- [ ] **Step 6: Verify no TS errors**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: clean (0 errors).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Analytics/CategoryDetail.tsx
git commit -m "feat: wire context menu and rule panel into CategoryDetail"
```

---

## Task 6: Manual smoke test

- [ ] **Step 1: Start the app**

```bash
# Terminal 1
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload

# Terminal 2
cd frontend && npm run dev
```

Open `http://localhost:5173`.

- [ ] **Step 2: Right-click a transaction row**

Navigate to Analytics → click a category that has transactions → right-click any transaction row.

Expected: A small floating menu appears with **"Create rule from transaction"** (or Czech equivalent).

- [ ] **Step 3: Click "Create rule from transaction"**

Expected: The context menu closes and a SlideOverPanel opens titled **"New Rule"**, with:
- Name field pre-filled (counterparty name or description)
- Match type showing the placeholder "— select type —"
- Match value field empty

- [ ] **Step 4: Select a match type**

Pick "Account Number" (counterparty_account_equals).

Expected: Match value field auto-fills with the transaction's counterparty account number (or empty if none).

Switch to "Counterparty Name".

Expected: Match value updates to the counterparty name.

Switch to "Description".

Expected: Match value updates to the description text.

- [ ] **Step 5: Save a rule**

Select a match type, pick a category, click Save.

Expected: Panel closes. Navigate to Rules page — the new rule appears in the list.

- [ ] **Step 6: Test dismissal**

Right-click a transaction, then click elsewhere on the page.

Expected: Context menu closes without opening the panel.

Right-click again, then press Escape.

Expected: Context menu closes.

- [ ] **Step 7: Verify existing rule create/edit flow is unchanged**

Go to Rules page → click "+ New Rule".

Expected: Form opens with "Account Number" pre-selected as match type (old default behavior, no placeholder).

- [ ] **Step 8: Final commit if any tweaks were needed**

```bash
git add -p
git commit -m "fix: smoke test tweaks for create-rule-from-transaction"
```
