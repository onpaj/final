# Finance Analyzer — Application Workflow Design

**Date:** 2026-04-10  
**Status:** Draft — pending open question resolution (see §7)

---

## 1. Purpose

This document defines the end-to-end user workflow for Finance Analyzer: how the user interacts with the application day-to-day, how pages relate to each other, and what happens at each stage of the import → classify → analyze loop.

Existing docs (`architecture.md`, `pipelines.md`, `data-model.md`) describe *what the system does*. This document describes *how the user experiences it*.

---

## 2. Core User Loop

```
Upload CSV export
       │
       ▼
App parses + deduplicates + classifies in background
       │
       ▼
Analytics page shows updated spending data
(with drilldown: Month → Group → Category → Transactions)
```

Import and analytics are **independent pages** with independent lifecycles. The analytics page always shows the last fully-processed stable snapshot. It never shows half-ingested data.

---

## 3. Navigation Structure

```
┌──────────────────────────────────────────────────────────────────┐
│  📊 Analytics   📥 Imports   🏷️ Rules   ⚙️ Settings      [●]   │
└──────────────────────────────────────────────────────────────────┘
                                                              │
                                        Global processing status indicator
                                        (idle / processing / error)
```

| Tab | Purpose |
|-----|---------|
| **Analytics** | Main page. Spending drilldown, income/expenses/savings. Default route (`/`). |
| **Imports** | Upload new exports. View import history with per-batch stats. |
| **Rules** | Create and manage categorization rules. |
| **Settings** | Accounts, category taxonomy, LLM usage/cost, preferences. |

**Global status indicator** (top-right corner of nav):

- 🟢 Idle — no background jobs running
- 🟡 Processing — 1+ import jobs in progress; click for job detail
- 🔴 Error — last job failed; click to see error

---

## 4. Analytics Page (main page)

Analytics is the default landing page. It is read-only relative to import processing: it always renders the last committed data snapshot.

### 4.1 Top-level controls

| Control | Behavior |
|---------|----------|
| **Month selector** | Defaults to the previous month (more useful than current month early in a billing cycle). Navigates backward/forward by month. |
| **Account filter** | Defaults to "All accounts" (consolidated). Can be narrowed to a single account. |

### 4.2 Drilldown levels

The page presents spending top-down. Each level is clickable to go one level deeper. Breadcrumbs allow navigation back up.

```
Level 1: Month summary
  ├─ Total income
  ├─ Total expenses
  ├─ Savings rate (%)
  └─ Expense breakdown by Group (donut/bar chart + table)
        │
        ▼ click a Group
Level 2: Group detail
  ├─ Group total for the month
  ├─ Breakdown by Category (bar chart + table)
  └─ Month-over-month delta vs. previous month
        │
        ▼ click a Category
Level 3: Category detail
  ├─ Category total for the month
  ├─ Trend sparkline (last 6 months)
  └─ Transaction list for this category in this month
        │
        ▼ click a Transaction
Level 4: Transaction detail
  ├─ Full transaction fields (date, counterparty, amount, description)
  ├─ Current category + source (rule / llm / manual)
  └─ Actions: re-categorize, add note, create rule from this transaction
```

### 4.3 Account dimension

The account filter is available at every drilldown level. It affects all charts and totals on the current screen. Transfers between own accounts are always excluded (`is_transfer = false` filter applied globally).

### 4.4 "New data available" behavior

When a background import job completes and the result would affect the currently-displayed analytics slice, a non-intrusive banner appears at the top of the analytics page:

> **New data available** — [Refresh]

The user decides when to load the new data. Clicking "Refresh" reloads the current analytics view with the updated snapshot. No automatic page mutations occur.

### 4.5 "Needs Review" transactions

Transactions that remain uncategorized after the full pipeline (rules + LLM escalation) surface via a **"Needs Review" chip** on the analytics page. Clicking it opens a filtered transaction list showing only uncategorized transactions for the selected month/account. From there the user can:

- Manually assign a category
- Create a rule based on the transaction
- Dismiss (mark as intentionally uncategorized)

---

## 5. Imports Page

A two-section page: upload at the top, history below.

### 5.1 Upload section

- Account selector (which account does this file belong to?)
- File picker (CSV)
- For first-time generic-CSV accounts: column mapping wizard before upload proceeds
- Submit button → fires upload, creates batch record with `status = processing`, returns immediately

### 5.2 Import history table

| Column | Notes |
|--------|-------|
| Filename | Original file name |
| Account | Which account |
| Date range covered | `min(booking_date)` – `max(booking_date)` from parsed rows |
| Rows parsed / imported / duplicates | Per-batch stats |
| Categorized / needs review | How many were auto-categorized vs. left uncategorized |
| Imported at | Timestamp |
| Status | `processing` / `completed` / `failed` |

Rows with `status = processing` show a spinner. On completion, the row updates in place (via polling or server-sent event).

Clicking a batch row opens a side panel with per-batch transaction breakdown.

---

## 6. Background Processing Model

When a file is uploaded:

1. `POST /api/imports` accepts the file, creates `import_batches` row with `status = processing`, and returns a batch ID synchronously.
2. A background task runs the full pipeline:
   - Parse → deduplicate → insert
   - `RulesEngine` pass
   - `AnthropicClient` pass for rule-misses
   - `TransferMatcher` pass
3. On success: `status = completed`, analytics snapshot is now updated.
4. On failure: `status = failed`, error message stored; user can retry.

The UI polls the batch status (or uses a WebSocket/SSE) to update the Imports table and nav bar indicator in real time.

Analytics **does not poll for new data**. It renders a snapshot on page load. The "new data available" banner is the only mechanism that signals an update is ready.

---

## 7. Open Questions

These are not blocking the workflow design but should be resolved before M1 implementation begins.

| # | Question | Options | Default assumption |
|---|----------|---------|-------------------|
| 1 | Multi-month trends view | Sub-tab inside Analytics, or separate Trends tab? | Sub-tab ("Trends" toggle within Analytics) |
| 2 | Flat transactions browser | Needed as a standalone page, or is the analytics drilldown sufficient? | Drilldown is sufficient for v1; standalone added in M5 if needed |
| 3 | Polling vs. SSE for background job status | Polling (simpler, HTTP only) vs. SSE (cleaner, real-time) | Polling (30s interval) in M1; upgrade later |
| 4 | "New data available" detection | Server pushes a notification vs. client polls a `latest_batch_completed_at` endpoint | Client polls `GET /api/imports/status` on the analytics page (60s interval) |
| 5 | Import retry UX | Re-upload same file, or a "Retry" button on a failed batch row? | "Retry" button on failed batch row |

---

## 8. Relationship to Existing Docs

| Doc | How this spec relates |
|-----|-----------------------|
| `docs/architecture.md` | Add a "User Workflow" section that references this spec |
| `docs/pipelines.md` | The import pipeline now runs as a background job; update the pipeline doc to reflect async execution and `status` field |
| `docs/roadmap.md` | M1 scope must include basic Analytics skeleton + Imports tab (not just the import API). Verify milestone scope is consistent. |
| `docs/data-model.md` | `import_batches` needs a `status` column (`processing` / `completed` / `failed`) and `error_message` column — not currently in the data model. |

---

## 9. Implementation Milestone Mapping

| Workflow piece | Milestone |
|----------------|-----------|
| Imports tab: upload + history table | M1 |
| Analytics page: month summary + group breakdown (level 1–2) | M1 skeleton, completed in M4 |
| Background processing (async job) | M1 |
| Categorization drilldown (level 3) + Needs Review | M2 |
| Multi-account consolidation + account filter | M3 |
| Full transaction drilldown (level 4), trends sub-tab | M4 |
| "New data available" banner | M4 |
| Bulk operations, import retry UX | M5 |
