# Review Page — Design Spec

**Date:** 2026-04-12  
**Status:** Approved

## Problem

After a CSV import and batch categorization run, some transactions remain uncategorized. There is currently no UI to see which transactions need manual attention or why they failed to categorize. Users must infer this from the Analytics page by filtering for uncategorized items — a clunky workaround.

## Goal

A dedicated `/review` page that surfaces all uncategorized, non-transfer transactions, shows why each one wasn't classified, and lets the user assign categories using the same drag-to-sidebar mechanic already present in Analytics.

---

## Backend Changes

### 1. Log LLM errors to `llm_classifications`

In `categorization_service.py`, the `except AnthropicClassificationError` block currently silently returns, leaving the transaction uncategorized with no record. Change it to write an `LlmClassification` row with:

- `accepted = False`
- `confidence = None`
- `reasoning = "error"`

This enables the join to distinguish error cases from "no LLM attempt made" cases.

### 2. Extend `GET /api/transactions`

Add an optional query param `include_llm_status: bool = False`.

When `True`, the endpoint LEFT JOINs the most recent `llm_classifications` row per transaction (ordered by `created_at DESC`) and appends an `llm_status` string to each `TransactionOut`.

**`llm_status` values:**

| Value | Condition |
|---|---|
| `"no_rule_no_llm"` | No matching rule, no `LlmClassification` row exists |
| `"llm_rejected"` | `LlmClassification` row exists, `accepted=False`, `confidence` is a number |
| `"llm_error"` | `LlmClassification` row exists, `accepted=False`, `reasoning="error"` |

**Updated `TransactionOut`** gains two optional fields:

```python
llm_status: str | None = None      # only populated when include_llm_status=True
llm_confidence: Decimal | None = None
```

The existing `needs_review=True` filter (`category_id IS NULL AND is_transfer = False`) is unchanged and composable with `include_llm_status`.

---

## Frontend Changes

### 1. `api/transactions.ts`

Add optional fields to the `Transaction` interface:

```ts
llm_status?: "no_rule_no_llm" | "llm_rejected" | "llm_error";
llm_confidence?: number;
```

Add `include_llm_status?: boolean` to `listTransactions` params.

### 2. `TransactionTable.tsx`

Add a `showReasonColumn?: boolean` prop (default `false`). When `true`, renders an extra "Reason" column after "Amount" with a badge:

| `llm_status` | Badge text |
|---|---|
| `"no_rule_no_llm"` | `no rule` (gray) |
| `"llm_rejected"` | `LLM rejected (0.42)` (yellow, confidence inline) |
| `"llm_error"` | `LLM error` (red) |

Existing Analytics usage passes no prop → no column rendered → fully backwards-compatible.

### 3. New `pages/Review/index.tsx`

Layout mirrors Analytics: full-width left panel + right `CategorySidebar`.

**Left panel:**
- Page heading: "Needs Review" with a count badge (e.g. "14 transactions")
- `TransactionTable` with `showReasonColumn={true}`
- Rows are draggable via existing `@dnd-kit/core` setup
- Data: `listTransactions({ needs_review: true, include_llm_status: true })`

**Right panel:**
- `CategorySidebar` reused as-is
- On drop: calls `bulkCategorize([tx.id], category_id)` then invalidates the query
- Dropped transaction disappears from the list immediately (optimistic or on refetch)

**Empty state:** When count reaches 0, show a success message: "All transactions categorized."

### 4. `App.tsx` + `NavBar.tsx`

- Add `<Route path="/review" element={<ReviewPage />} />` 
- Add "Review" nav link with a count badge that shows the number of uncategorized transactions (reuse the same `needs_review=true` query, count only)

---

## Data Flow

```
ReviewPage mounts
  → GET /api/transactions?needs_review=true&include_llm_status=true
  → renders TransactionTable with reason badges
  
User drags row onto CategorySidebar category
  → PATCH /api/transactions/bulk-categorize { transaction_ids: [id], category_id }
  → TanStack Query invalidates → row disappears
```

---

## What Is Not In Scope

- Pagination (uncategorized counts are expected to be small — dozens, not thousands)
- Sorting/filtering by reason on the Review page
- Re-running LLM categorization from the Review page (handled separately via Imports page batch button)
- Any changes to the `LlmClassification` table schema
