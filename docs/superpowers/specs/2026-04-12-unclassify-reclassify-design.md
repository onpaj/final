# Unclassify & Re-classify Transactions

**Date:** 2026-04-12

## Summary

Two related features that close the manual categorization loop:

1. **Unclassify** — clear the category on selected transactions so they can be re-processed
2. **Re-classify** — trigger LLM classification on all unclassified transactions from the Settings page

## Backend

### Extend `PATCH /transactions/bulk-categorize`

Change `category_id` in `BulkCategorizeRequest` from required `uuid.UUID` to `uuid.UUID | None`.

When `category_id` is `null`:
- Set `category_id = null`
- Set `categorization_source = null`
- Set `confidence = null`

No new endpoints needed.

## Frontend — Unclassify

### `frontend/src/api/transactions.ts`

Add `bulkCategorize(transaction_ids: string[], category_id: string | null)` function calling `PATCH /api/transactions/bulk-categorize`.

### `frontend/src/pages/Analytics/CategoryDetail.tsx`

In the selection toolbar (shown when rows are checked), add a "Clear category" button alongside the existing "Assign to:" dropdown. Clicking it calls `bulkCategorize` with `category_id: null` for all selected transaction IDs, then invalidates the relevant queries.

Button states:
- Default: "Clear category"
- Pending: "Clearing…" + disabled
- Error: inline error message below toolbar

## Frontend — Re-classify

### `frontend/src/api/categorization.ts` (new file)

```ts
export async function runBatchClassification(): Promise<{ categorized: number; needs_review: number }>
```

Calls `POST /api/categorization/batch` with empty body.

### `frontend/src/pages/Settings/index.tsx`

New `CategorizationSection` component added below `LlmCostSection`. Contains:
- Section heading
- Short description: "Run LLM classification on all transactions without a category."
- Button: "Re-classify unclassified"
- While pending: "Running…" + disabled
- On success: "Done — {categorized} categorized, {needs_review} need review"
- On error: "Classification failed. Please try again."

Result and error messages are cleared on next button click.

## i18n

New keys added to both `en/translation.json` and `cs/translation.json`:

```
analytics.clearCategory       — "Clear category"
analytics.clearingCategory    — "Clearing…"
analytics.clearFailed         — "Failed to clear. Please try again."
settings.categorizationTitle  — "Categorization"
settings.categorizationDesc   — "Run LLM classification on all transactions without a category."
settings.reclassifyBtn        — "Re-classify unclassified"
settings.reclassifyRunning    — "Running…"
settings.reclassifyDone       — "Done — {{categorized}} categorized, {{needs_review}} need review"
settings.reclassifyFailed     — "Classification failed. Please try again."
```

## Error Handling

- Network/API errors shown inline near the triggering button
- No toast or global notification — keeps it simple and consistent with existing patterns
- Result message is cleared when the button is clicked again

## Out of Scope

- Per-transaction unclassify (bulk only)
- Re-classify specific transactions (all-unclassified only)
- Progress indicator for long-running batch (fire-and-wait is fine for now)
