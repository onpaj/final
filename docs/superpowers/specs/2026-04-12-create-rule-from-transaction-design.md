# Design: Create Rule from Transaction

**Date:** 2026-04-12  
**Status:** Approved

## Summary

Add a right-click context menu on transaction rows that opens the existing `RuleForm` pre-filled with data from the clicked transaction. The user picks the match type, edits fields as needed, and saves — creating a categorization rule without leaving the Analytics view.

## Scope

- Right-click context menu on transaction rows in `TransactionTable`
- `RuleForm` extended with an optional `prefill` prop
- No backend changes required
- No immediate re-categorization after rule save (same behavior as creating a rule from the Rules page)

## Components

### 1. `ContextMenu` (new — `frontend/src/components/ContextMenu.tsx`)

A portal-based floating menu rendered into `document.body`.

**Props:**
```ts
interface ContextMenuProps {
  x: number;
  y: number;
  items: { label: string; onClick: () => void }[];
  onClose: () => void;
}
```

**Behavior:**
- Positioned at `(x, y)` from the `contextmenu` event, clamped to viewport bounds
- Closes on `mousedown` outside the menu or `Escape` keypress
- Styled with Tailwind to match existing app design (white card, shadow, small text)

### 2. `TransactionTable` changes (`frontend/src/pages/Analytics/TransactionTable.tsx`)

`DraggableRow` receives a new prop:
```ts
onContextMenu: (e: React.MouseEvent, tx: Transaction) => void;
```

Handler calls `e.preventDefault()` and passes coordinates + transaction up to the parent. Drag initiation is suppressed when right-click triggers.

### 3. `CategoryDetail` changes (`frontend/src/pages/Analytics/CategoryDetail.tsx`)

New state:
```ts
const [contextMenu, setContextMenu] = useState<{
  x: number;
  y: number;
  transaction: Transaction;
} | null>(null);

const [rulePanel, setRulePanel] = useState<{ prefill?: RulePrefill } | null>(null);
```

Context menu renders one item: **"Create rule from transaction"**. Clicking it:
1. Closes the context menu
2. Opens `SlideOverPanel` with `RuleForm` and `prefill` built from the transaction

`SlideOverPanel` + `RuleForm` are the same components used in `RulesPage` — no duplication.

### 4. `RuleForm` changes (`frontend/src/pages/Rules/RuleForm.tsx`)

New optional prop:
```ts
interface RulePrefill {
  name: string;                    // counterparty_name ?? description ?? ""
  counterpartyAccount: string | null;
  counterpartyName: string | null;
  description: string | null;
}
```

**Behavior when `prefill` is provided:**
- `name` field initializes to `prefill.name` (user-editable)
- `matchType` starts empty — user must select one (add a placeholder `<option value="">— select type —</option>`)
- `matchValue` updates reactively when match type changes:
  - `counterparty_account_equals` → `prefill.counterpartyAccount ?? ""`
  - `counterparty_contains` → `prefill.counterpartyName ?? ""`
  - `description_contains` → `prefill.description ?? ""`

When `prefill` is absent (existing behavior), form initializes as before with `counterparty_account_equals` default.

## i18n Keys

```json
"rules": {
  "createFromTransaction": "Create rule from transaction",
  "matchType.placeholder": "— select type —"
}
```

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/components/ContextMenu.tsx` | New component |
| `frontend/src/pages/Analytics/TransactionTable.tsx` | Add `onContextMenu` prop |
| `frontend/src/pages/Analytics/CategoryDetail.tsx` | Context menu state + rule panel wiring |
| `frontend/src/pages/Rules/RuleForm.tsx` | Add `prefill` prop |
| i18n locale files | 2 new keys |

## Non-goals

- Mobile / touch support
- Keyboard navigation in the context menu
- Auto re-categorization after rule save
- More than one item in the context menu (for now)
