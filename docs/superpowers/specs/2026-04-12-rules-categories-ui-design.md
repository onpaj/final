# Rules & Categories UI — Design Spec

**Date:** 2026-04-12
**Status:** Approved

## Overview

Two separate management pages: `/rules` and `/categories`. Both use a slide-over panel pattern for create/edit, keeping the list visible while editing.

---

## Rules Page (`/rules`)

### Layout

Full-width table with a right-side slide-over panel for create/edit. The existing table is extended — not replaced.

### Table Columns

| Column | Notes |
|--------|-------|
| Priority | Numeric; higher = evaluated first |
| Name | User-defined label |
| Match type | "Account number" / "Counterparty name" / "Description" |
| Match value preview | Truncated display of the match value |
| Category | Name of the assigned category |
| Hits | `hit_count` from DB |
| Enabled | Toggle; fires `PATCH` immediately on change |
| Edit | Opens slide-over pre-filled |
| Delete | Inline confirmation (no modal) |

### Slide-Over Panel Fields

- **Name** — text input
- **Match type** — select: "Account number" | "Counterparty name" | "Description"
- **Match value** — text input; label adapts to match type:
  - Account number → "IBAN / account number (exact match)"
  - Counterparty name → "Name contains"
  - Description → "Description contains"
- **Category** — grouped dropdown; group names as headings, categories as options
- **Priority** — number input, default 100
- **Enabled** — toggle, default on

### Behavior

- "New rule" button (top-right) opens blank panel
- Edit icon on a row opens panel pre-filled with that rule's data
- Save calls `POST /api/rules` (create) or `PATCH /api/rules/:id` (update)
- Enable/disable toggle calls `PATCH /api/rules/:id` immediately, no Save needed
- Delete requires inline confirmation before calling `DELETE /api/rules/:id`

### Backend Changes

- Add `counterparty_account_equals` match type to `rules_engine.py`:
  - Exact match on `tx.counterparty_account` (case-insensitive or normalized)
- `PATCH /api/rules/:id` already exists on the backend; frontend API client needs `updateRule(id, body)` added to `frontend/src/api/rules.ts`

---

## Categories Page (`/categories`)

### Layout

Two-column layout:
- **Left column:** list of category groups (reorderable)
- **Right column:** categories within the selected group (reorderable)

### Group Management (Left Column)

- Each row: color swatch · name · edit icon · delete icon
- "New group" button at bottom of list
- Clicking a group selects it and loads its categories on the right
- Edit icon triggers inline rename (text input replaces name in-place; blur or Enter saves)
- Reorder via drag-and-drop; fires `PATCH /api/categories/groups/reorder` on drop
- Delete calls `DELETE /api/categories/groups/:id` (backend should reject if group has categories)

### Category Management (Right Column)

- Each row: color swatch · name · income badge (if `is_income = true`) · edit icon · delete icon
- "New category" button at bottom of list
- Edit/create opens slide-over panel with fields:
  - **Name** — text input
  - **Color** — color picker
  - **Is income** — toggle
  - Sort order managed via drag-and-drop, not manual input
- System categories (`is_system = true`) show a lock icon — name and color are editable, delete is disabled
- Reorder via drag-and-drop; fires `PATCH /api/categories/reorder` on drop

### Backend Changes Required

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/categories` | Create category |
| `PATCH` | `/api/categories/:id` | Update category (name, color, is_income) |
| `DELETE` | `/api/categories/:id` | Delete category |
| `PATCH` | `/api/categories/reorder` | Bulk update sort_order for categories |
| `POST` | `/api/categories/groups` | Create group |
| `PATCH` | `/api/categories/groups/:id` | Update group (name, color) |
| `DELETE` | `/api/categories/groups/:id` | Delete group |
| `PATCH` | `/api/categories/groups/reorder` | Bulk update sort_order for groups |

---

## Shared Patterns

- **Slide-over panel:** right-anchored, ~400px wide, overlays content without blocking the list
- **Drag-and-drop:** use `@dnd-kit/core` (already installed) with `@dnd-kit/sortable` for reordering
- **No routing changes** beyond adding `/categories` as a new page with a nav link
- **No composite rules** in scope — each rule has exactly one condition
