# Transaction History Filters — Design Spec

**Date:** 2026-04-17  
**Status:** Approved

## Summary

Extend the existing Review page (`/review`) with an "All Transactions" mode that allows browsing the full transaction history with filters. The current "Needs Review" mode is unchanged.

## Mode Toggle

A segmented control at the top of the Review page switches between two modes:

- **Needs Review** — existing behavior: uncategorized non-transfer transactions, with run-classification controls visible.
- **All Transactions** — full transaction history with filter bar. Run-classification controls and step checkboxes are hidden.

## Filter Bar (All Transactions mode only)

Three filters, all optional, applied together:

| Filter | UI | API param |
|--------|----|-----------|
| Account | Single-select dropdown, default "All accounts" | `account_id` |
| Date range | Two date inputs: From / To | `date_from`, `date_to` |
| Categorization source | Single-select dropdown: All / None / Rule / LLM / Transfer / Manual | `categorization_source` |

"None" maps to `categorization_source IS NULL` in the DB. Because the existing backend param only supports equality (`WHERE categorization_source = ?`), a small backend addition is needed: when `categorization_source=none` is received, the query filters `WHERE categorization_source IS NULL` instead. All other source values (rule, llm, transfer, manual) pass through as-is.

Changing any filter resets the list to page 1.

## Data Loading

- Uses `useInfiniteQuery` (TanStack Query v5) with `limit=50`, `offset` incremented per page.
- Next page triggered by an `IntersectionObserver` sentinel div at the bottom of the table.
- Query key includes all active filter values so filter changes invalidate and restart the infinite query.
- The existing `listTransactions` API function is extended to accept `offset` (already supported by the backend).

## Table

- Reuses `TransactionTable` from `pages/Analytics/TransactionTable.tsx`.
- `showReasonColumn` is `false` in All Transactions mode (LLM rejection reasons not relevant).
- Row selection and bulk categorize remain available so users can categorize transactions directly from history.
- Drag-to-categorize sidebar (`CategorySidebar`) is shown, same as Needs Review mode.

## State Management

All filter state is local React state in `ReviewPage`. No URL persistence for filters (keep it simple for now).

## What Is Not Changing

- The Needs Review mode is functionally unchanged.
- No new backend endpoints are needed — the existing `GET /api/transactions` supports all required filters.
- No new routes are added — this extends `/review`.
